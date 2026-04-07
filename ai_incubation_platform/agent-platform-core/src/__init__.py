"""
Agent Platform Core

AI Incubation Platform 的核心框架层，提供统一的 Agent 基础设施和 DeerFlow 2.0 集成能力。

核心组件:
- deerflow: DeerFlow 2.0 客户端封装、工作流编排引擎、降级模式
- tools: 工具基类、注册表、装饰器
- audit: 审计日志记录器、数据模型
- config: 统一配置管理、密钥管理
- utils: 统一日志、异常处理
"""

__version__ = "3.0.0"
__author__ = "AI Incubation Platform Team"

# DeerFlow 组件
from deerflow import (
    DeerFlowClient,
    WorkflowEngine,
    FallbackMode,
    FallbackStrategy,
)

# Tools 组件
from tools import (
    BaseTool,
    ToolContext,
    ToolResult,
    ToolsRegistry,
    tool,
    validate_input,
    rate_limit,
    require_auth,
)

# Audit 组件
from audit import (
    AuditLog,
    AuditLogStatus,
    AuditQuery,
    AuditLogger,
)

# Config 组件
from config import (
    Settings,
    ConfigLoader,
    SecretsManager,
    SecretType,
    SecretStoreType,
)

# Utils 组件
from utils import (
    setup_logging,
    get_logger,
    AgentPlatformError,
    ToolError,
    WorkflowError,
    ConfigurationError,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    NotFoundError,
    RateLimitError,
    TimeoutError,
)

__all__ = [
    # 版本
    "__version__",
    "__author__",
    # DeerFlow
    "DeerFlowClient",
    "WorkflowEngine",
    "FallbackMode",
    "FallbackStrategy",
    # Tools
    "BaseTool",
    "ToolContext",
    "ToolResult",
    "ToolsRegistry",
    "tool",
    "validate_input",
    "rate_limit",
    "require_auth",
    # Audit
    "AuditLog",
    "AuditLogStatus",
    "AuditQuery",
    "AuditLogger",
    # Config
    "Settings",
    "ConfigLoader",
    "SecretsManager",
    "SecretType",
    "SecretStoreType",
    # Utils
    "setup_logging",
    "get_logger",
    "AgentPlatformError",
    "ToolError",
    "WorkflowError",
    "ConfigurationError",
    "AuthenticationError",
    "AuthorizationError",
    "ValidationError",
    "NotFoundError",
    "RateLimitError",
    "TimeoutError",
]
