"""
统一响应包装
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse, JSONResponse
from typing import Callable, Coroutine, Any
from schemas.common import Response, ErrorCode
import uuid
import time
import logging

logger = logging.getLogger(__name__)


class ResponseMiddleware(BaseHTTPMiddleware):
    """统一响应中间件，包装所有响应为统一格式"""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Coroutine[Any, Any, StarletteResponse]]
    ) -> StarletteResponse:
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start_time = time.time()

        try:
            response = await call_next(request)

            # 如果是JSON响应且不是已经包装过的响应，则进行包装
            if (
                isinstance(response, JSONResponse)
                and response.status_code == 200
                and not isinstance(response.background_tasks, bool)
            ):
                try:
                    # 读取原始响应内容
                    body = b""
                    async for chunk in response.body_iterator:
                        body += chunk

                    import json
                    data = json.loads(body.decode("utf-8"))

                    # 检查是否已经是统一响应格式
                    if isinstance(data, dict) and "code" in data and "message" in data and "data" in data:
                        # 已经是统一格式，补充request_id即可
                        data["request_id"] = request_id
                        return JSONResponse(
                            content=data,
                            status_code=response.status_code,
                            headers=dict(response.headers),
                            media_type=response.media_type,
                            background=response.background
                        )
                    else:
                        # 包装为统一响应格式
                        wrapped_response = Response(
                            code=ErrorCode.SUCCESS,
                            message="success",
                            data=data,
                            request_id=request_id
                        )
                        return JSONResponse(
                            content=wrapped_response.model_dump(),
                            status_code=response.status_code,
                            headers=dict(response.headers),
                            media_type=response.media_type,
                            background=response.background
                        )
                except Exception as e:
                    logger.error(f"Failed to wrap response: {str(e)}", exc_info=e)
                    return response
            else:
                # 非JSON响应或错误响应，直接返回，补充X-Request-ID头
                response.headers["X-Request-ID"] = request_id
                return response

        finally:
            # 记录请求日志
            process_time = (time.time() - start_time) * 1000
            logger.info(
                f"Request {request_id} {request.method} {request.url.path} "
                f"completed in {process_time:.2f}ms",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "process_time": process_time,
                    "client_ip": request.client.host if request.client else None
                }
            )


def success(data: any = None, message: str = "success", request_id: str = None) -> Response:
    """成功响应快捷方法"""
    return Response(
        code=ErrorCode.SUCCESS,
        message=message,
        data=data,
        request_id=request_id
    )


def error(code: ErrorCode, message: str = None, data: any = None, request_id: str = None) -> Response:
    """错误响应快捷方法"""
    return Response(
        code=code,
        message=message or code.name,
        data=data,
        request_id=request_id
    )
