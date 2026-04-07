"""
速率限制中间件 - 防止 API 滥用

基于令牌桶算法实现速率限制，支持按 IP、用户 ID 等维度限流。
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta
import time
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    令牌桶速率限制器

    支持配置:
    - calls: 允许的请求次数
    - period: 时间窗口（秒）
    """

    def __init__(self, calls: int = 100, period: float = 60.0):
        self.calls = calls  # 允许的请求次数
        self.period = period  # 时间窗口（秒）
        # 存储：key -> {"tokens": float, "last_update": datetime}
        self._buckets: Dict[str, Dict[str, Any]] = {}

    def _get_bucket(self, key: str) -> Dict[str, Any]:
        """获取或创建令牌桶"""
        if key not in self._buckets:
            self._buckets[key] = {
                "tokens": self.calls,
                "last_update": datetime.now()
            }
        return self._buckets[key]

    def _refill_tokens(self, bucket: Dict[str, Any]) -> None:
        """补充令牌"""
        now = datetime.now()
        elapsed = (now - bucket["last_update"]).total_seconds()

        # 按时间比例补充令牌
        tokens_to_add = (elapsed / self.period) * self.calls
        bucket["tokens"] = min(self.calls, bucket["tokens"] + tokens_to_add)
        bucket["last_update"] = now

    def is_allowed(self, key: str) -> bool:
        """
        检查请求是否允许

        Args:
            key: 限流键（如 IP 地址、用户 ID）

        Returns:
            是否允许请求
        """
        bucket = self._get_bucket(key)
        self._refill_tokens(bucket)

        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True
        return False

    def get_remaining(self, key: str) -> int:
        """获取剩余请求次数"""
        bucket = self._get_bucket(key)
        self._refill_tokens(bucket)
        return int(bucket["tokens"])

    def get_retry_after(self, key: str) -> float:
        """获取重试等待时间（秒）"""
        bucket = self._get_bucket(key)
        # 计算补充 1 个令牌需要的时间
        tokens_needed = 1 - bucket["tokens"]
        if tokens_needed <= 0:
            return 0
        return (tokens_needed / self.calls) * self.period

    def reset(self, key: str) -> None:
        """重置指定键的限流状态"""
        if key in self._buckets:
            del self._buckets[key]

    def clear(self) -> None:
        """清空所有限流状态"""
        self._buckets.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    速率限制中间件

    使用方式:
    app.add_middleware(
        RateLimitMiddleware,
        limiter=RateLimiter(calls=100, period=60),
        key_func=lambda request: request.client.host
    )
    """

    def __init__(
        self,
        app,
        limiter: RateLimiter,
        key_func: Callable[[Request], str] = None,
        excluded_paths: list = None,
        include_headers: bool = True
    ):
        super().__init__(app)
        self.limiter = limiter
        self.key_func = key_func or (lambda r: r.client.host)
        self.excluded_paths = excluded_paths or ["/health", "/docs", "/openapi.json"]
        self.include_headers = include_headers

    async def dispatch(self, request: Request, call_next):
        # 检查是否在排除路径中
        for path in self.excluded_paths:
            if request.url.path.startswith(path):
                return await call_next(request)

        # 获取限流键
        limit_key = self.key_func(request)

        # 检查是否允许请求
        if not self.limiter.is_allowed(limit_key):
            retry_after = self.limiter.get_retry_after(limit_key)

            logger.warning(
                f"速率限制触发：key={limit_key}, path={request.url.path}, "
                f"retry_after={retry_after:.2f}s"
            )

            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Too Many Requests",
                    "detail": "请求频率过高，请稍后重试",
                    "retry_after": retry_after
                }
            )

            if self.include_headers:
                response.headers["Retry-After"] = str(int(retry_after) + 1)

            return response

        # 执行请求
        response = await call_next(request)

        # 添加限流头信息
        if self.include_headers:
            remaining = self.limiter.get_remaining(limit_key)
            response.headers["X-RateLimit-Limit"] = str(self.limiter.calls)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(
                int(time.time() + self.limiter.period)
            )

        return response


def create_rate_limiter(
    calls: int = 100,
    period: float = 60.0,
    key_func: Callable[[Request], str] = None,
    excluded_paths: list = None
) -> RateLimitMiddleware:
    """
    创建速率限制中间件

    Args:
        calls: 允许的请求次数
        period: 时间窗口（秒）
        key_func: 限流键提取函数
        excluded_paths: 排除的路径列表

    Returns:
        速率限制中间件
    """
    limiter = RateLimiter(calls=calls, period=period)
    return lambda app: RateLimitMiddleware(
        app,
        limiter=limiter,
        key_func=key_func,
        excluded_paths=excluded_paths
    )


# 预定义的限流键提取函数
def get_ip_key(request: Request) -> str:
    """按 IP 地址限流"""
    return f"ip:{request.client.host}"


def get_user_key(request: Request) -> str:
    """按用户 ID 限流（从 header 获取）"""
    user_id = request.headers.get("X-User-ID", "anonymous")
    return f"user:{user_id}"


def get_combined_key(request: Request) -> str:
    """按 IP+ 用户 ID 组合限流"""
    user_id = request.headers.get("X-User-ID", request.client.host)
    return f"combined:{request.client.host}:{user_id}"
