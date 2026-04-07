"""
统一异常处理

提供统一的异常基类和具体异常类型
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field as dc_field
import time


@dataclass
class ErrorDetails:
    """错误详情"""
    code: str
    message: str
    field_name: Optional[str] = None
    value: Optional[Any] = None
    metadata: Dict[str, Any] = dc_field(default_factory=dict)


class AgentPlatformError(Exception):
    """
    Agent 平台基础异常类

    所有自定义异常都应继承此类
    """

    def __init__(
        self,
        message: str,
        code: str = "AGENT_PLATFORM_ERROR",
        status_code: int = 500,
        details: Optional[List[ErrorDetails]] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        初始化异常

        Args:
            message: 错误消息
            code: 错误代码
            status_code: HTTP 状态码
            details: 错误详情列表
            context: 上下文信息
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or []
        self.context = context or {}
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "status_code": self.status_code,
                "details": [
                    {
                        "code": d.code,
                        "message": d.message,
                        "field": d.field,
                        "metadata": d.metadata
                    }
                    for d in self.details
                ],
                "context": self.context,
                "timestamp": self.timestamp
            }
        }

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class ToolError(AgentPlatformError):
    """
    工具执行错误

    当工具执行失败时抛出
    """

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        tool_error: Optional[Exception] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=kwargs.pop("code", "TOOL_ERROR"),
            status_code=kwargs.pop("status_code", 500),
            **kwargs
        )
        self.tool_name = tool_name
        self.tool_error = tool_error
        self.context["tool_name"] = tool_name


class WorkflowError(AgentPlatformError):
    """
    工作流执行错误

    当工作流执行失败时抛出
    """

    def __init__(
        self,
        message: str,
        workflow_name: Optional[str] = None,
        node_name: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=kwargs.pop("code", "WORKFLOW_ERROR"),
            status_code=kwargs.pop("status_code", 500),
            **kwargs
        )
        self.workflow_name = workflow_name
        self.node_name = node_name
        self.context["workflow_name"] = workflow_name
        self.context["node_name"] = node_name


class ConfigurationError(AgentPlatformError):
    """
    配置错误

    当配置无效或丢失时抛出
    """

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=kwargs.pop("code", "CONFIGURATION_ERROR"),
            status_code=kwargs.pop("status_code", 500),
            **kwargs
        )
        self.config_key = config_key
        self.context["config_key"] = config_key


class AuthenticationError(AgentPlatformError):
    """
    认证错误

    当认证失败时抛出
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        auth_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=kwargs.pop("code", "AUTHENTICATION_ERROR"),
            status_code=kwargs.pop("status_code", 401),
            **kwargs
        )
        self.auth_type = auth_type
        self.context["auth_type"] = auth_type


class AuthorizationError(AgentPlatformError):
    """
    授权错误

    当权限不足时抛出
    """

    def __init__(
        self,
        message: str = "Permission denied",
        required_permission: Optional[str] = None,
        resource: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=kwargs.pop("code", "AUTHORIZATION_ERROR"),
            status_code=kwargs.pop("status_code", 403),
            **kwargs
        )
        self.required_permission = required_permission
        self.resource = resource
        self.context["required_permission"] = required_permission
        self.context["resource"] = resource


class ValidationError(AgentPlatformError):
    """
    验证错误

    当输入验证失败时抛出
    """

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=kwargs.pop("code", "VALIDATION_ERROR"),
            status_code=kwargs.pop("status_code", 400),
            **kwargs
        )
        self.field = field_name
        self.value = value

        if field_name:
            self.details.append(ErrorDetails(
                code="INVALID_FIELD",
                message=message,
                field_name=field_name,
                value=value
            ))


class NotFoundError(AgentPlatformError):
    """
    资源未找到错误

    当请求的资源不存在时抛出
    """

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=kwargs.pop("code", "NOT_FOUND"),
            status_code=kwargs.pop("status_code", 404),
            **kwargs
        )
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.context["resource_type"] = resource_type
        self.context["resource_id"] = resource_id


class RateLimitError(AgentPlatformError):
    """
    限流错误

    当超过限流阈值时抛出
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        limit: Optional[int] = None,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=kwargs.pop("code", "RATE_LIMIT_EXCEEDED"),
            status_code=kwargs.pop("status_code", 429),
            **kwargs
        )
        self.limit = limit
        self.retry_after = retry_after
        self.context["limit"] = limit
        self.context["retry_after"] = retry_after


class TimeoutError(AgentPlatformError):
    """
    超时错误

    当操作超时时抛出
    """

    def __init__(
        self,
        message: str = "Operation timed out",
        timeout_seconds: Optional[float] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=kwargs.pop("code", "TIMEOUT"),
            status_code=kwargs.pop("status_code", 504),
            **kwargs
        )
        self.timeout_seconds = timeout_seconds
        self.operation = operation
        self.context["timeout_seconds"] = timeout_seconds
        self.context["operation"] = operation


class ConflictError(AgentPlatformError):
    """
    冲突错误

    当操作导致状态冲突时抛出
    """

    def __init__(
        self,
        message: str = "Resource conflict",
        conflict_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=kwargs.pop("code", "CONFLICT"),
            status_code=kwargs.pop("status_code", 409),
            **kwargs
        )
        self.conflict_type = conflict_type
        self.context["conflict_type"] = conflict_type


class ServiceUnavailableError(AgentPlatformError):
    """
    服务不可用错误

    当依赖服务不可用时抛出
    """

    def __init__(
        self,
        message: str = "Service unavailable",
        service_name: Optional[str] = None,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=kwargs.pop("code", "SERVICE_UNAVAILABLE"),
            status_code=kwargs.pop("status_code", 503),
            **kwargs
        )
        self.service_name = service_name
        self.retry_after = retry_after
        self.context["service_name"] = service_name
        self.context["retry_after"] = retry_after


class CircuitBreakerError(AgentPlatformError):
    """
    熔断器错误

    当熔断器打开时抛出
    """

    def __init__(
        self,
        message: str = "Circuit breaker is open",
        service_name: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=kwargs.pop("code", "CIRCUIT_BREAKER_OPEN"),
            status_code=kwargs.pop("status_code", 503),
            **kwargs
        )
        self.service_name = service_name
        self.context["service_name"] = service_name


def create_error_response(error: AgentPlatformError) -> Dict[str, Any]:
    """
    创建错误响应

    Args:
        error: 异常实例

    Returns:
        错误响应字典
    """
    return error.to_dict()


def handle_exception(exc: Exception) -> Dict[str, Any]:
    """
    处理异常并返回标准化响应

    Args:
        exc: 异常实例

    Returns:
        错误响应字典
    """
    if isinstance(exc, AgentPlatformError):
        return exc.to_dict()

    # 未知异常
    return {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": f"An unexpected error occurred: {str(exc)}",
            "status_code": 500
        }
    }


def raise_validation_error(
    field: str,
    message: str,
    value: Optional[Any] = None
) -> None:
    """便捷函数：抛出验证错误"""
    raise ValidationError(message=message, field=field, value=value)


def raise_not_found(
    resource_type: str,
    resource_id: str
) -> None:
    """便捷函数：抛出未找到错误"""
    raise NotFoundError(
        message=f"{resource_type} not found: {resource_id}",
        resource_type=resource_type,
        resource_id=resource_id
    )


def raise_auth_failed(
    message: str = "Authentication failed",
    auth_type: Optional[str] = None
) -> None:
    """便捷函数：抛出认证错误"""
    raise AuthenticationError(message=message, auth_type=auth_type)


def raise_permission_denied(
    resource: Optional[str] = None
) -> None:
    """便捷函数：抛出授权错误"""
    raise AuthorizationError(resource=resource)
