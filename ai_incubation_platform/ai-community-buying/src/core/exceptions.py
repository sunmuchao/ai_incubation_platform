"""
统一异常处理模块

定义自定义异常类和全局异常处理器，提供统一的错误响应格式。
"""
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ========== 业务异常基类 ==========
class AppException(Exception):
    """应用异常基类"""

    def __init__(
        self,
        message: str,
        error_code: str = "APP_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        data: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.data = data
        super().__init__(self.message)


# ========== 库存相关异常 ==========
class InsufficientStockError(AppException):
    """库存不足异常"""

    def __init__(self, message: str = "库存不足", product_id: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="INSUFFICIENT_STOCK",
            status_code=status.HTTP_400_BAD_REQUEST,
            data={"product_id": product_id} if product_id else None
        )


class StockLockedError(AppException):
    """库存已锁定异常"""

    def __init__(self, message: str = "库存已被锁定"):
        super().__init__(
            message=message,
            error_code="STOCK_LOCKED",
            status_code=status.HTTP_409_CONFLICT
        )


# ========== 团购相关异常 ==========
class GroupBuyError(AppException):
    """团购异常基类"""

    def __init__(
        self,
        message: str,
        error_code: str = "GROUP_BUY_ERROR",
        status_code: int = status.HTTP_400_BAD_REQUEST
    ):
        super().__init__(message=message, error_code=error_code, status_code=status_code)


class GroupBuyNotOpenError(GroupBuyError):
    """团购未开启异常"""

    def __init__(self, message: str = "团购已关闭"):
        super().__init__(message=message, error_code="GROUP_NOT_OPEN")


class GroupBuyFullError(GroupBuyError):
    """团购已满异常"""

    def __init__(self, message: str = "团购已满员"):
        super().__init__(message=message, error_code="GROUP_FULL")


class GroupBuyExpiredError(GroupBuyError):
    """团购已过期异常"""

    def __init__(self, message: str = "团购已过期"):
        super().__init__(message=message, error_code="GROUP_EXPIRED")


class UserAlreadyJoinedError(GroupBuyError):
    """用户已参团异常"""

    def __init__(self, message: str = "用户已加入该团购"):
        super().__init__(message=message, error_code="USER_ALREADY_JOINED")


class GroupBuyNotFoundError(GroupBuyError):
    """团购不存在异常"""

    def __init__(self, group_id: Optional[str] = None):
        message = f"团购不存在" + (f": {group_id}" if group_id else "")
        super().__init__(
            message=message,
            error_code="GROUP_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )


# ========== 商品相关异常 ==========
class ProductError(AppException):
    """商品异常基类"""

    def __init__(
        self,
        message: str,
        error_code: str = "PRODUCT_ERROR",
        status_code: int = status.HTTP_400_BAD_REQUEST
    ):
        super().__init__(message=message, error_code=error_code, status_code=status_code)


class ProductNotFoundError(ProductError):
    """商品不存在异常"""

    def __init__(self, product_id: Optional[str] = None):
        message = f"商品不存在" + (f": {product_id}" if product_id else "")
        super().__init__(
            message=message,
            error_code="PRODUCT_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )


class ProductUnavailableError(ProductError):
    """商品不可用异常"""

    def __init__(self, message: str = "商品不可用"):
        super().__init__(message=message, error_code="PRODUCT_UNAVAILABLE")


# ========== 订单相关异常 ==========
class OrderError(AppException):
    """订单异常基类"""

    def __init__(
        self,
        message: str,
        error_code: str = "ORDER_ERROR",
        status_code: int = status.HTTP_400_BAD_REQUEST
    ):
        super().__init__(message=message, error_code=error_code, status_code=status_code)


class OrderNotFoundError(OrderError):
    """订单不存在异常"""

    def __init__(self, order_id: Optional[str] = None):
        message = f"订单不存在" + (f": {order_id}" if order_id else "")
        super().__init__(
            message=message,
            error_code="ORDER_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )


# ========== 权限相关异常 ==========
class PermissionError(AppException):
    """权限异常"""

    def __init__(self, message: str = "无权限操作"):
        super().__init__(
            message=message,
            error_code="PERMISSION_DENIED",
            status_code=status.HTTP_403_FORBIDDEN
        )


# ========== 验证相关异常 ==========
class DataValidationError(AppException):
    """数据验证异常"""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            data={"field": field} if field else None
        )


# ========== 全局异常处理器 ==========
def register_exception_handlers(app: FastAPI):
    """注册全局异常处理器"""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """处理自定义应用异常"""
        logger.warning(
            f"业务异常：{exc.error_code} - {exc.message}",
            extra={
                "path": request.url.path,
                "method": request.method,
            }
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "data": exc.data
                }
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """处理请求参数验证异常"""
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(x) for x in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })

        logger.warning(
            f"参数验证失败：{errors}",
            extra={
                "path": request.url.path,
                "method": request.method,
            }
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "请求参数验证失败",
                    "details": errors
                }
            }
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        """处理数据库完整性约束错误"""
        error_msg = str(exc.orig) if hasattr(exc, 'orig') else str(exc)

        logger.error(
            f"数据库完整性错误：{error_msg}",
            extra={
                "path": request.url.path,
                "method": request.method,
            },
            exc_info=True
        )

        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "success": False,
                "error": {
                    "code": "INTEGRITY_ERROR",
                    "message": "数据冲突或违反约束"
                }
            }
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
        """处理 SQLAlchemy 数据库错误"""
        logger.error(
            f"数据库错误：{str(exc)}",
            extra={
                "path": request.url.path,
                "method": request.method,
            },
            exc_info=True
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "数据库操作失败"
                }
            }
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """处理 FastAPI HTTP 异常"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": exc.detail
                }
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """处理未预料的通用异常"""
        logger.error(
            f"未处理异常：{str(exc)}",
            extra={
                "path": request.url.path,
                "method": request.method,
            },
            exc_info=True
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "服务器内部错误"
                }
            }
        )
