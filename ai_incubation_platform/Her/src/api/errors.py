"""
API 统一错误处理

提供标准化的错误响应格式，减少 API 层重复代码。

使用示例:
    from api.errors import NotFoundError, ValidationError, raise_not_found

    # 方式 1: 直接抛出
    raise NotFoundError("用户")

    # 方式 2: 条件抛出
    raise_not_found(user is None, "用户")

    # 方式 3: 响应格式
    return error_response("操作失败", details={"reason": "xxx"})
"""
from fastapi import HTTPException, status
from typing import Optional, Dict, Any


class APIError(HTTPException):
    """
    API 错误基类

    所有自定义 API 错误都应继承此类。
    """

    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        初始化 API 错误

        Args:
            status_code: HTTP 状态码
            detail: 错误描述
            error_code: 业务错误码（可选）
            details: 详细信息（可选）
        """
        self.error_code = error_code
        self.details = details
        super().__init__(status_code=status_code, detail=detail)


# ==================== 常用错误类 ====================

class NotFoundError(APIError):
    """资源未找到错误"""

    def __init__(self, resource: str = "资源", resource_id: Any = None):
        message = f"{resource}不存在"
        if resource_id:
            message = f"{resource}(ID: {resource_id})不存在"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
            error_code="NOT_FOUND"
        )


class ValidationError(APIError):
    """验证错误"""

    def __init__(self, message: str = "参数验证失败", field: str = None):
        details = {"field": field} if field else None
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
            error_code="VALIDATION_ERROR",
            details=details
        )


class AuthError(APIError):
    """认证错误"""

    def __init__(self, message: str = "认证失败"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message,
            error_code="AUTH_ERROR"
        )


class ForbiddenError(APIError):
    """权限错误"""

    def __init__(self, message: str = "无权访问"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message,
            error_code="FORBIDDEN"
        )


class ConflictError(APIError):
    """冲突错误（如重复创建）"""

    def __init__(self, message: str = "资源冲突"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
            error_code="CONFLICT"
        )


class RateLimitError(APIError):
    """限流错误"""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"请求过于频繁，请 {retry_after} 秒后重试",
            error_code="RATE_LIMIT",
            details={"retry_after": retry_after}
        )


# ==================== 辅助函数 ====================

def raise_not_found(condition: bool, resource: str = "资源", resource_id: Any = None):
    """
    条件抛出 NotFoundError

    Args:
        condition: 条件（True 时抛出错误）
        resource: 资源名称
        resource_id: 资源 ID

    Raises:
        NotFoundError: 当 condition 为 True 时

    使用示例:
        user = db.query(UserDB).filter(UserDB.id == user_id).first()
        raise_not_found(user is None, "用户", user_id)
    """
    if condition:
        raise NotFoundError(resource, resource_id)


def raise_validation(condition: bool, message: str, field: str = None):
    """
    条件抛出 ValidationError

    Args:
        condition: 条件（True 时抛出错误）
        message: 错误信息
        field: 字段名

    Raises:
        ValidationError: 当 condition 为 True 时
    """
    if condition:
        raise ValidationError(message, field)


def raise_forbidden(condition: bool, message: str = "无权访问"):
    """
    条件抛出 ForbiddenError

    Args:
        condition: 条件（True 时抛出错误）
        message: 错误信息

    Raises:
        ForbiddenError: 当 condition 为 True 时
    """
    if condition:
        raise ForbiddenError(message)


def error_response(
    message: str,
    error_code: str = "ERROR",
    status_code: int = status.HTTP_400_BAD_REQUEST,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    生成标准错误响应

    Args:
        message: 错误信息
        error_code: 错误码
        status_code: HTTP 状态码
        details: 详细信息

    Returns:
        标准格式的错误响应字典

    使用示例:
        return error_response("操作失败", details={"reason": "xxx"})
    """
    response = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
        }
    }
    if details:
        response["error"]["details"] = details
    return response


def success_response(
    data: Any = None,
    message: str = "操作成功",
    **extra
) -> Dict[str, Any]:
    """
    生成标准成功响应

    Args:
        data: 返回数据
        message: 成功信息
        **extra: 额外字段

    Returns:
        标准格式的成功响应字典

    使用示例:
        return success_response(user.to_dict(), "获取用户成功")
    """
    response = {
        "success": True,
        "message": message,
    }
    if data is not None:
        response["data"] = data
    response.update(extra)
    return response