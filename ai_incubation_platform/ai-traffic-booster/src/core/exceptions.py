"""
统一异常定义和处理
"""
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from typing import Callable
from .response import Response
from schemas.common import ErrorCode
import uuid
import logging

logger = logging.getLogger(__name__)


class AppException(Exception):
    """应用基础异常类"""

    def __init__(
        self,
        code: ErrorCode,
        message: str = None,
        data: any = None,
        status_code: int = 200
    ):
        self.code = code
        self.message = message or code.name
        self.data = data
        self.status_code = status_code
        super().__init__(self.message)


class BadRequestException(AppException):
    """请求参数错误"""
    def __init__(self, message: str = "请求参数错误", data: any = None):
        super().__init__(ErrorCode.BAD_REQUEST, message, data, status_code=400)


class UnauthorizedException(AppException):
    """未授权"""
    def __init__(self, message: str = "未授权访问", data: any = None):
        super().__init__(ErrorCode.UNAUTHORIZED, message, data, status_code=401)


class ForbiddenException(AppException):
    """禁止访问"""
    def __init__(self, message: str = "禁止访问", data: any = None):
        super().__init__(ErrorCode.FORBIDDEN, message, data, status_code=403)


class NotFoundException(AppException):
    """资源不存在"""
    def __init__(self, message: str = "资源不存在", data: any = None):
        super().__init__(ErrorCode.NOT_FOUND, message, data, status_code=404)


class ValidationException(AppException):
    """参数验证失败"""
    def __init__(self, message: str = "参数验证失败", data: any = None):
        super().__init__(ErrorCode.VALIDATION_ERROR, message, data, status_code=400)


class InternalErrorException(AppException):
    """内部服务器错误"""
    def __init__(self, message: str = "服务器内部错误", data: any = None):
        super().__init__(ErrorCode.INTERNAL_ERROR, message, data, status_code=500)


# -----------------------------
# 模块化错误码（P0 统一错误码）
# -----------------------------

class SEOAnalysisException(AppException):
    """SEO 分析失败"""

    def __init__(self, message: str = "SEO分析失败", data: any = None):
        super().__init__(ErrorCode.SEO_ANALYSIS_FAILED, message, data, status_code=400)


class SEOContentEmptyException(AppException):
    """SEO 分析内容为空"""

    def __init__(self, message: str = "SEO分析内容不能为空", data: any = None):
        super().__init__(ErrorCode.SEO_CONTENT_EMPTY, message, data, status_code=400)


class SEOKeywordsEmptyException(AppException):
    """SEO 关键词为空"""

    def __init__(self, message: str = "SEO分析关键词不能为空", data: any = None):
        super().__init__(ErrorCode.SEO_KEYWORDS_EMPTY, message, data, status_code=400)


class ContentGenerationException(AppException):
    """内容生成失败"""

    def __init__(self, message: str = "内容生成失败", data: any = None):
        super().__init__(ErrorCode.CONTENT_GENERATION_FAILED, message, data, status_code=400)


class ContentTooShortException(AppException):
    """内容长度过短"""

    def __init__(self, message: str = "内容长度过短", data: any = None):
        super().__init__(ErrorCode.CONTENT_TOO_SHORT, message, data, status_code=400)


class ContentTooLongException(AppException):
    """内容长度过长"""

    def __init__(self, message: str = "内容长度过长", data: any = None):
        super().__init__(ErrorCode.CONTENT_TOO_LONG, message, data, status_code=400)


class AnalyticsQueryFailedException(AppException):
    """流量分析查询失败"""

    def __init__(self, message: str = "流量分析查询失败", data: any = None):
        super().__init__(ErrorCode.ANALYTICS_QUERY_FAILED, message, data, status_code=400)


class AnalyticsDataNotFoundException(AppException):
    """分析数据不存在"""

    def __init__(self, message: str = "分析数据未找到", data: any = None):
        super().__init__(ErrorCode.ANALYTICS_DATA_NOT_FOUND, message, data, status_code=404)


class ABTestNotFoundException(AppException):
    """A/B 测试不存在"""

    def __init__(self, message: str = "A/B测试不存在", data: any = None):
        super().__init__(ErrorCode.AB_TEST_NOT_FOUND, message, data, status_code=404)


class ABTestStatusInvalidException(AppException):
    """A/B 测试状态不允许"""

    def __init__(self, message: str = "A/B测试状态不允许当前操作", data: any = None):
        super().__init__(ErrorCode.AB_TEST_STATUS_INVALID, message, data, status_code=400)


class ABTestStatisticsFailedException(AppException):
    """A/B 测试统计失败"""

    def __init__(self, message: str = "A/B测试统计失败", data: any = None):
        super().__init__(ErrorCode.AB_TEST_STATISTICS_FAILED, message, data, status_code=500)


class ABTestTrafficAllocationInvalidException(AppException):
    """A/B 测试流量分配不合法"""

    def __init__(self, message: str = "A/B 测试流量分配不合法", data: any = None):
        super().__init__(ErrorCode.AB_TEST_TRAFFIC_ALLOCATION_INVALID, message, data, status_code=400)


class ABTestControlVariantInvalidException(AppException):
    """A/B 测试对照组配置不合法"""

    def __init__(self, message: str = "A/B 测试对照组配置不合法", data: any = None):
        super().__init__(ErrorCode.AB_TEST_CONTROL_VARIANT_INVALID, message, data, status_code=400)


async def exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """统一异常处理器"""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    if exc.code >= ErrorCode.INTERNAL_ERROR:
        logger.error(
            f"Request {request_id} failed: {exc.message}",
            exc_info=exc,
            extra={"request_id": request_id, "code": exc.code.value}
        )
    else:
        logger.warning(
            f"Request {request_id} failed: {exc.message}",
            extra={"request_id": request_id, "code": exc.code.value}
        )

    response = Response(
        code=exc.code,
        message=exc.message,
        data=exc.data,
        request_id=request_id
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump()
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """通用异常处理器，捕获所有未处理的异常"""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    logger.error(
        f"Request {request_id} unhandled exception: {str(exc)}",
        exc_info=exc,
        extra={"request_id": request_id}
    )

    response = Response(
        code=ErrorCode.INTERNAL_ERROR,
        message="服务器内部错误",
        request_id=request_id
    )

    return JSONResponse(
        status_code=500,
        content=response.model_dump()
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """统一请求参数校验错误（P0：统一错误码/响应 schema）"""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    response = Response(
        code=ErrorCode.VALIDATION_ERROR,
        message="参数验证失败",
        data={"errors": exc.errors()},
        request_id=request_id,
    )

    return JSONResponse(
        status_code=422,
        content=response.model_dump(),
    )


def register_exception_handlers(app) -> None:
    """注册异常处理器到FastAPI应用"""
    app.add_exception_handler(AppException, exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
