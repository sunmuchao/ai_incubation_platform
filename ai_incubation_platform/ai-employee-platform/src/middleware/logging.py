"""
日志中间件
记录所有 HTTP 请求的日志
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from config.logging_config import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """HTTP 请求日志中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 记录请求开始时间
        start_time = time.time()

        # 获取请求信息
        method = request.method
        path = request.url.path
        query = request.url.query
        client_host = request.client.host if request.client else "unknown"

        # 记录请求
        request_log = f"Request: {method} {path}"
        if query:
            request_log += f"?{query}"
        request_log += f" from {client_host}"
        logger.info(request_log)

        # 执行请求
        try:
            response = await call_next(request)
        except Exception as e:
            # 记录异常
            process_time = time.time() - start_time
            logger.error(f"Exception in {method} {path}: {str(e)}")
            raise

        # 记录响应时间
        process_time = time.time() - start_time

        # 记录响应信息
        response_log = (
            f"Response: {method} {path} "
            f"status={response.status_code} "
            f"duration={process_time:.3f}s"
        )
        logger.info(response_log)

        # 添加响应头，显示请求处理时间
        response.headers["X-Process-Time"] = str(process_time)

        return response


def setup_middleware(app) -> None:
    """
    设置应用中间件

    Args:
        app: FastAPI 应用实例
    """
    # 添加日志中间件
    app.add_middleware(LoggingMiddleware)

    # 添加 CORS 中间件（如果需要）
    from fastapi.middleware.cors import CORSMiddleware
    from config.settings import settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
