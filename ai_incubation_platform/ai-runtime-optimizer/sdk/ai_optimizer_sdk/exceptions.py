"""
SDK 异常类
"""


class AIOptimizerError(Exception):
    """AI Optimizer 基础异常"""

    def __init__(self, message: str, status_code: int = None, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class AuthenticationError(AIOptimizerError):
    """认证失败异常"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401, error_code="AUTH_FAILED")


class RateLimitError(AIOptimizerError):
    """速率限制异常"""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        super().__init__(message, status_code=429, error_code="RATE_LIMITED")
        self.retry_after = retry_after


class NotFoundError(AIOptimizerError):
    """资源未找到异常"""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404, error_code="NOT_FOUND")


class ServerError(AIOptimizerError):
    """服务器错误"""

    def __init__(self, message: str = "Internal server error"):
        super().__init__(message, status_code=500, error_code="SERVER_ERROR")


class ValidationError(AIOptimizerError):
    """参数验证错误"""

    def __init__(self, message: str, field: str = None):
        super().__init__(message, status_code=400, error_code="VALIDATION_ERROR")
        self.field = field
