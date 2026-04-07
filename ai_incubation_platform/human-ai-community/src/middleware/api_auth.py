"""
API 认证中间件

提供 API Key 验证和认证功能
"""
import logging
import time
import uuid
from datetime import datetime
from typing import Optional, Callable, Awaitable

from fastapi import Request, Response, HTTPException
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware

from services.api_key_service import api_key_service
from models.api_key import APIKey, APIKeyStatus

logger = logging.getLogger(__name__)


# API Key Header
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIAuthMiddleware(BaseHTTPMiddleware):
    """API 认证中间件"""

    def __init__(self, app, excluded_paths: list = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            "/",
            "/health",
            "/health/db",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/members",  # 公开注册
            "/api/auth",     # 认证相关
        ]

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """处理请求"""
        # 检查是否需要认证
        if self._is_excluded_path(request.url.path):
            return await call_next(request)

        # 获取 API Key
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            # 如果没有 API Key，检查是否是浏览器访问 docs
            if request.url.path in ["/docs", "/redoc"]:
                return await call_next(request)
            raise HTTPException(
                status_code=401,
                detail="Missing API key. Please provide X-API-Key header."
            )

        # 验证 API Key
        is_valid, key_info, error_msg = await api_key_service.validate_api_key(api_key)

        if not is_valid:
            logger.warning(f"API Key 验证失败：{error_msg}")
            raise HTTPException(
                status_code=401 if "Invalid" in error_msg else 403,
                detail=error_msg
            )

        # 检查速率限制
        rate_limit_ok, rate_info = await api_key_service.check_rate_limit(key_info)

        if not rate_limit_ok:
            logger.warning(f"API Key 触发速率限制：{key_info.id}")
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(key_info.rate_limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(rate_info.get("retry_after", 1)),
                }
            )

        # 将 API Key 信息存入请求状态
        request.state.api_key = key_info
        request.state.request_id = str(uuid.uuid4())
        request.state.start_time = time.time()

        # 执行请求
        response = await call_next(request)

        # 记录请求日志
        await self._log_request(request, response, key_info, rate_info)

        # 添加速率限制响应头
        response.headers["X-RateLimit-Limit"] = str(key_info.rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(rate_info.get("remaining", 0))
        response.headers["X-RateLimit-Reset"] = str(rate_info.get("reset", 1))

        return response

    def _is_excluded_path(self, path: str) -> bool:
        """检查路径是否需要排除认证"""
        for excluded in self.excluded_paths:
            if path.startswith(excluded):
                return True
        return False

    async def _log_request(
        self,
        request: Request,
        response: Response,
        api_key: APIKey,
        rate_info: dict
    ):
        """记录请求日志"""
        try:
            # 计算响应时间
            response_time_ms = (time.time() - request.state.start_time) * 1000

            # 提取端点名称
            endpoint = self._extract_endpoint(request.url.path)

            # 获取客户端信息
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("User-Agent", "")[:500]

            # 记录日志
            await api_key_service.log_request(
                api_key_id=api_key.id,
                request_id=request.state.request_id,
                method=request.method,
                path=request.url.path,
                endpoint=endpoint,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                ip_address=ip_address,
                user_agent=user_agent,
                is_rate_limited=response.status_code == 429,
                rate_limit_remaining=rate_info.get("remaining", 0),
            )

            logger.debug(
                f"API 请求：{request.method} {request.url.path} "
                f"[{response.status_code}] [{response_time_ms:.2f}ms] "
                f"API Key: {api_key.id}"
            )

        except Exception as e:
            logger.error(f"记录 API 请求日志失败：{e}")

    def _extract_endpoint(self, path: str) -> str:
        """从路径提取端点名称"""
        # 移除查询参数
        path = path.split("?")[0]
        # 移除 /api 前缀
        if path.startswith("/api"):
            path = path[4:]
        # 移除动态参数
        parts = path.split("/")
        cleaned_parts = []
        for part in parts:
            if part and not part.isdigit() and not part.startswith("{"):
                cleaned_parts.append(part)
        return "/".join(cleaned_parts[:5])  # 限制长度


async def get_api_key(request: Request) -> Optional[APIKey]:
    """获取当前请求的 API Key"""
    return getattr(request.state, "api_key", None)


async def verify_api_key(request: Request) -> APIKey:
    """验证并获取 API Key，如果不存在则抛出异常"""
    api_key = getattr(request.state, "api_key", None)
    if not api_key:
        raise HTTPException(status_code=401, detail="Authentication required")
    return api_key


def require_scope(required_scope: str):
    """装饰器：要求 API Key 拥有指定权限"""
    async def scope_checker(request: Request) -> APIKey:
        api_key = await verify_api_key(request)
        if not api_key.has_scope(required_scope):
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required scope: {required_scope}"
            )
        return api_key
    return scope_checker
