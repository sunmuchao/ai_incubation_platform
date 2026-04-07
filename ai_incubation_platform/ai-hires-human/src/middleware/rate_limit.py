"""
API 限流中间件。

使用滑动窗口计数器算法实现 API 限流，保护系统免受过载影响。
支持全局限流、用户级别限流、IP 级别限流。
"""
import time
from typing import Dict, Optional, Tuple

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimiter:
    """
    滑动窗口计数器限流器。

    使用内存存储实现，生产环境建议使用 Redis。
    """

    def __init__(self):
        # 存储结构：{key: [(timestamp, count), ...]}
        self._windows: Dict[str, list] = {}
        self._cleanup_interval = 60  # 清理间隔（秒）
        self._last_cleanup = time.time()

    def _cleanup(self):
        """清理过期的窗口数据。"""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        cutoff = current_time - 300  # 保留 5 分钟数据
        for key in list(self._windows.keys()):
            self._windows[key] = [
                (ts, count) for ts, count in self._windows[key]
                if ts > cutoff
            ]
            if not self._windows[key]:
                del self._windows[key]

        self._last_cleanup = current_time

    def _get_window_key(
        self,
        key_type: str,
        identifier: str,
        window_seconds: int
    ) -> str:
        """获取窗口键。"""
        current_window = int(time.time() / window_seconds)
        return f"{key_type}:{identifier}:{window_seconds}:{current_window}"

    def is_allowed(
        self,
        key_type: str,
        identifier: str,
        limit: int,
        window_seconds: int
    ) -> Tuple[bool, Dict]:
        """
        检查请求是否允许。

        Args:
            key_type: 限流类型 (global/user/ip)
            identifier: 标识符 (用户 ID、IP 等)
            limit: 窗口期内最大请求数
            window_seconds: 窗口大小（秒）

        Returns:
            (是否允许，附加信息)
        """
        self._cleanup()

        key = self._get_window_key(key_type, identifier, window_seconds)
        current_time = time.time()

        # 获取或创建窗口
        if key not in self._windows:
            self._windows[key] = []

        # 清理窗口内的过期数据
        window_start = current_time - window_seconds
        self._windows[key] = [
            (ts, count) for ts, count in self._windows[key]
            if ts > window_start
        ]

        # 计算当前窗口内的请求数
        current_count = sum(count for _, count in self._windows[key])

        # 计算重置时间
        reset_time = window_start + window_seconds

        if current_count >= limit:
            return False, {
                "limit": limit,
                "remaining": 0,
                "reset": int(reset_time),
                "retry_after": int(reset_time - current_time),
            }

        # 记录本次请求
        self._windows[key].append((current_time, 1))

        return True, {
            "limit": limit,
            "remaining": limit - current_count - 1,
            "reset": int(reset_time),
        }


# 全局限流器实例
_rate_limiter = RateLimiter()


# 限流配置
class RateLimitConfig:
    """限流配置。"""

    # 全局限流
    GLOBAL_LIMIT = 1000  # 次
    GLOBAL_WINDOW = 60  # 秒

    # 用户限流
    USER_LIMIT = 100  # 次
    USER_WINDOW = 60  # 秒

    # IP 限流
    IP_LIMIT = 60  # 次
    IP_WINDOW = 60  # 秒

    # 特定路径的限流配置
    PATH_LIMITS = {
        "/api/tasks": {"limit": 50, "window": 60},  # 任务 API
        "/api/batch-tasks": {"limit": 10, "window": 60},  # 批量任务（更严格）
        "/api/payment": {"limit": 20, "window": 60},  # 支付 API（更严格）
        "/api/admin": {"limit": 30, "window": 60},  # 管理 API
    }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    API 限流中间件。

    限流级别：
    1. 全局限流：保护系统整体过载
    2. 用户限流：防止单用户滥用
    3. IP 限流：防止恶意攻击

    限流响应头：
    - X-RateLimit-Limit: 最大请求数
    - X-RateLimit-Remaining: 剩余请求数
    - X-RateLimit-Reset: 重置时间戳
    - Retry-After: 建议重试时间（秒）
    """

    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.enabled = True
        self.bypass_paths = [
            "/health",
            "/docs",
            "/openapi.json",
        ]

    async def dispatch(self, request: Request, call_next):
        # 检查是否启用限流
        if not self.enabled:
            return await call_next(request)

        # 检查是否 bypass
        path = request.url.path
        for bypass_path in self.bypass_paths:
            if path.startswith(bypass_path):
                return await call_next(request)

        # 获取请求标识
        client_ip = self._get_client_ip(request)
        user_id = self._get_user_id(request)

        # 1. 检查全局限流
        allowed, info = _rate_limiter.is_allowed(
            "global",
            "all",
            RateLimitConfig.GLOBAL_LIMIT,
            RateLimitConfig.GLOBAL_WINDOW,
        )
        if not allowed:
            return self._rate_limit_response(info, "global")

        # 2. 检查用户限流
        if user_id:
            allowed, info = _rate_limiter.is_allowed(
                "user",
                user_id,
                RateLimitConfig.USER_LIMIT,
                RateLimitConfig.USER_WINDOW,
            )
            if not allowed:
                return self._rate_limit_response(info, "user")

        # 3. 检查 IP 限流
        allowed, info = _rate_limiter.is_allowed(
            "ip",
            client_ip,
            RateLimitConfig.IP_LIMIT,
            RateLimitConfig.IP_WINDOW,
        )
        if not allowed:
            return self._rate_limit_response(info, "ip")

        # 4. 检查特定路径限流
        for path_prefix, config in RateLimitConfig.PATH_LIMITS.items():
            if path.startswith(path_prefix):
                limit_key = f"path:{path_prefix}"
                allowed, info = _rate_limiter.is_allowed(
                    "path",
                    limit_key,
                    config["limit"],
                    config["window"],
                )
                if not allowed:
                    return self._rate_limit_response(info, "path")

        # 执行请求
        response = await call_next(request)

        # 添加限流响应头
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])

        return response

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端 IP 地址。"""
        # 检查代理头部
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # 检查真实 IP 头部
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # 使用直接连接的 IP
        if request.client:
            return request.client.host

        return "unknown"

    def _get_user_id(self, request: Request) -> Optional[str]:
        """获取用户 ID。"""
        # 从查询参数获取
        user_id = request.query_params.get("user_id")
        if user_id:
            return user_id

        # 从请求头获取（如果有认证）
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # 这里简化处理，实际应该解析 JWT
            token = auth_header[7:]
            return f"token:{token[:16]}"

        return None

    def _rate_limit_response(
        self,
        info: Dict,
        limit_type: str
    ) -> JSONResponse:
        """返回限流响应。"""
        response = JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": "Too many requests",
                "error_code": "RATE_LIMIT_EXCEEDED",
                "limit_type": limit_type,
                "message": f"Rate limit exceeded for {limit_type}",
            },
        )
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = "0"
        response.headers["X-RateLimit-Reset"] = str(info["reset"])
        response.headers["Retry-After"] = str(info.get("retry_after", 60))
        return response


# ==================== 依赖注入 ====================

def get_rate_limiter() -> RateLimiter:
    """获取限流器实例（用于依赖注入）。"""
    return _rate_limiter


def check_rate_limit(
    key_type: str = "default",
    identifier: Optional[str] = None,
    limit: int = 100,
    window_seconds: int = 60,
):
    """
    限流检查装饰器（用于特定端点）。

    用法:
        @router.get("/special")
        @check_rate_limit(key_type="special", limit=10, window_seconds=60)
        async def special_endpoint():
            ...
    """
    from functools import wraps

    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # 获取标识符
            if identifier is None:
                if request.client:
                    id_value = request.client.host
                else:
                    id_value = "unknown"
            else:
                id_value = identifier

            # 检查限流
            allowed, info = _rate_limiter.is_allowed(
                key_type,
                id_value,
                limit,
                window_seconds,
            )

            if not allowed:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Too many requests",
                        "error_code": "RATE_LIMIT_EXCEEDED",
                    },
                    headers={
                        "Retry-After": str(info.get("retry_after", 60)),
                    },
                )

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


# ==================== 配置 API ====================

async def update_rate_limit_config(
    global_limit: Optional[int] = None,
    user_limit: Optional[int] = None,
    ip_limit: Optional[int] = None,
    enabled: Optional[bool] = None,
):
    """更新限流配置。"""
    if global_limit is not None:
        RateLimitConfig.GLOBAL_LIMIT = global_limit
    if user_limit is not None:
        RateLimitConfig.USER_LIMIT = user_limit
    if ip_limit is not None:
        RateLimitConfig.IP_LIMIT = ip_limit
    if enabled is not None:
        # 注意：需要在中间件实例上设置
        pass


def get_rate_limit_status() -> Dict:
    """获取限流状态。"""
    return {
        "enabled": True,
        "global_limit": {
            "limit": RateLimitConfig.GLOBAL_LIMIT,
            "window_seconds": RateLimitConfig.GLOBAL_WINDOW,
        },
        "user_limit": {
            "limit": RateLimitConfig.USER_LIMIT,
            "window_seconds": RateLimitConfig.USER_WINDOW,
        },
        "ip_limit": {
            "limit": RateLimitConfig.IP_LIMIT,
            "window_seconds": RateLimitConfig.IP_WINDOW,
        },
        "path_limits": RateLimitConfig.PATH_LIMITS,
    }
