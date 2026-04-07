"""
安全中间件
提供 API 限流、安全头、HTTPS 重定向等安全功能
"""
import time
import re
from typing import Dict, List, Callable
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
import hashlib


class RateLimiter:
    """
    简单的内存限流器

    使用滑动窗口算法实现限流
    生产环境建议使用 Redis
    """

    def __init__(self):
        # 存储每个请求者的请求时间戳列表
        # {identifier: [timestamp1, timestamp2, ...]}
        self._requests: Dict[str, List[float]] = defaultdict(list)
        # 限流规则：{path_pattern: (max_requests, window_seconds)}
        self._rules: Dict[str, tuple] = {}

    def register_rule(self, path_pattern: str, max_requests: int, window_seconds: int):
        """
        注册限流规则

        Args:
            path_pattern: URL 路径正则表达式
            max_requests: 窗口期内最大请求数
            window_seconds: 窗口期大小 (秒)
        """
        self._rules[path_pattern] = (max_requests, window_seconds)

    def is_allowed(self, identifier: str, path: str) -> tuple[bool, dict]:
        """
        检查请求是否允许

        Args:
            identifier: 请求标识符 (通常是 IP 地址或用户 ID)
            path: 请求路径

        Returns:
            (是否允许，限流信息)
        """
        now = time.time()

        # 查找匹配的规则
        matched_rule = None
        for pattern, rule in self._rules.items():
            if re.match(pattern, path):
                matched_rule = rule
                break

        if not matched_rule:
            # 默认规则：100 次/分钟
            max_requests, window_seconds = 100, 60
        else:
            max_requests, window_seconds = matched_rule

        # 清理过期请求
        key = f"{identifier}:{path}"
        window_start = now - window_seconds
        self._requests[key] = [ts for ts in self._requests[key] if ts > window_start]

        # 检查是否超限
        current_count = len(self._requests[key])
        remaining = max(0, max_requests - current_count)
        reset_time = int(window_seconds - (now - (self._requests[key][0] if self._requests[key] else now)))

        if current_count >= max_requests:
            return False, {
                "limit": max_requests,
                "remaining": 0,
                "reset": reset_time,
                "retry_after": reset_time
            }

        # 记录请求
        self._requests[key].append(now)

        return True, {
            "limit": max_requests,
            "remaining": remaining - 1,
            "reset": reset_time
        }

    def cleanup(self):
        """清理过期数据 (建议定期调用)"""
        now = time.time()
        max_window = max(rule[1] for rule in self._rules.values()) if self._rules else 60
        cutoff = now - max_window

        for key in list(self._requests.keys()):
            self._requests[key] = [ts for ts in self._requests[key] if ts > cutoff]
            if not self._requests[key]:
                del self._requests[key]


# 全局限流器实例
rate_limiter = RateLimiter()

# 注册限流规则
rate_limiter.register_rule(r"^/api/login", 5, 60)  # 登录：5 次/分钟
rate_limiter.register_rule(r"^/api/register", 3, 60)  # 注册：3 次/分钟
rate_limiter.register_rule(r"^/api/password", 3, 60)  # 密码相关：3 次/分钟
rate_limiter.register_rule(r"^/api/.*", 100, 60)  # 其他 API:100 次/分钟


async def rate_limit_middleware(request: Request, call_next: Callable):
    """
    限流中间件
    """
    # 获取请求标识符 (IP 地址 + 用户 ID)
    client_ip = request.client.host if request.client else "unknown"

    # 尝试从 token 获取用户 ID
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token_hash = hashlib.md5(auth_header.encode()).hexdigest()[:16]
        identifier = f"{client_ip}:{token_hash}"
    else:
        identifier = client_ip

    # 检查限流
    allowed, info = rate_limiter.is_allowed(identifier, request.url.path)

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Too many requests",
                "error_code": "RATE_LIMIT_EXCEEDED",
                "retry_after": info.get("retry_after", 60)
            },
            headers={
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(info["reset"]),
                "Retry-After": str(info.get("retry_after", 60))
            }
        )

    # 执行请求
    response = await call_next(request)

    # 添加限流头
    response.headers["X-RateLimit-Limit"] = str(info["limit"])
    response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
    response.headers["X-RateLimit-Reset"] = str(info["reset"])

    return response


async def security_headers_middleware(request: Request, call_next: Callable):
    """
    安全头中间件
    """
    response = await call_next(request)

    # OWASP 推荐安全头
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Content Security Policy
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "frame-ancestors 'none'"
    )

    # HTTP Strict Transport Security (HSTS)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

    # Permissions Policy (原 Feature Policy)
    response.headers["Permissions-Policy"] = (
        "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
        "magnetometer=(), microphone=(), payment=(), usb=()"
    )

    return response


async def https_redirect_middleware(request: Request, call_next: Callable):
    """
    HTTPS 重定向中间件
    生产环境应在负载均衡层或反向代理层实现
    """
    # 检查是否是 HTTPS (通过代理头判断)
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
    forwarded_ssl = request.headers.get("X-Forwarded-SSL", "")

    # 如果是 HTTP 且不是本地环境，重定向到 HTTPS
    if (forwarded_proto == "http" or forwarded_ssl != "on") and \
       request.url.hostname not in ["localhost", "127.0.0.1"]:
        # 构建 HTTPS URL
        https_url = str(request.url).replace("http://", "https://", 1)
        return Response(
            status_code=301,
            headers={"Location": https_url},
            content=""
        )

    return await call_next(request)


async def request_logging_middleware(request: Request, call_next: Callable):
    """
    请求日志中间件 (带敏感信息脱敏)
    """
    import logging
    from config.logging_config import get_logger

    logger = get_logger(__name__)

    # 记录请求开始
    start_time = datetime.now()

    # 脱敏敏感信息
    def mask_sensitive(value: str) -> str:
        """脱敏敏感信息"""
        if not value:
            return value

        # 手机号脱敏：138****1234
        if re.match(r"^1[3-9]\d{9}$", value):
            return value[:3] + "****" + value[-4:]

        # 邮箱脱敏：test****@example.com
        if "@" in value:
            parts = value.split("@")
            if len(parts[0]) > 2:
                return parts[0][:2] + "****@" + parts[1]

        # 身份证脱敏：110101********1234
        if len(value) == 18 and value[:6].isdigit():
            return value[:6] + "********" + value[-4:]

        return value

    # 记录请求信息 (脱敏后)
    logger.info(
        f"Request: {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else "unknown",
        }
    )

    # 执行请求
    response = await call_next(request)

    # 记录响应信息
    duration = (datetime.now() - start_time).total_seconds() * 1000
    logger.info(
        f"Response: {response.status_code} in {duration:.2f}ms",
        extra={
            "status_code": response.status_code,
            "duration_ms": duration
        }
    )

    return response


def setup_security_middleware(app):
    """
    设置所有安全中间件

    使用示例:
    ```python
    from fastapi import FastAPI
    from middleware.security import setup_security_middleware

    app = FastAPI()
    setup_security_middleware(app)
    ```
    """
    from starlette.middleware.cors import CORSMiddleware
    import os

    # 1. HTTPS 重定向 (最外层)
    # app.add_middleware(https_redirect_middleware)  # 建议在 Nginx/负载均衡层实现

    # 2. CORS 配置
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    )

    # 3. 限流中间件 - 使用 http 中间件装饰器
    @app.middleware("http")
    async def rate_limit_wrapper(request, call_next):
        return await rate_limit_middleware(request, call_next)

    # 4. 安全头中间件
    @app.middleware("http")
    async def security_headers_wrapper(request, call_next):
        return await security_headers_middleware(request, call_next)

    # 5. 请求日志中间件 (最内层)
    @app.middleware("http")
    async def request_logging_wrapper(request, call_next):
        return await request_logging_middleware(request, call_next)

    return app
