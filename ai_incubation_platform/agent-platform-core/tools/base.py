"""
工具基类

提供所有工具的基类和通用数据模型
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass, field
from enum import Enum
import time
import uuid

logger = logging.getLogger(__name__)


class ToolStatus(Enum):
    """工具执行状态"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    VALIDATION_ERROR = "validation_error"
    PERMISSION_DENIED = "permission_denied"


@dataclass
class ToolContext:
    """
    工具执行上下文

    包含工具执行所需的所有上下文信息
    """
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)

    def elapsed_ms(self) -> float:
        """获取经过时间（毫秒）"""
        return (time.time() - self.start_time) * 1000

    def get(self, key: str, default: Any = None) -> Any:
        """获取上下文值"""
        return self.metadata.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置上下文值"""
        self.metadata[key] = value


@dataclass
class ToolResult:
    """
    工具执行结果

    统一的工具执行结果封装
    """
    success: bool
    data: Any = None
    error: Optional[str] = None
    status: ToolStatus = ToolStatus.SUCCESS
    execution_time_ms: float = 0.0
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(
        cls,
        data: Any = None,
        execution_time_ms: float = 0.0,
        request_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> 'ToolResult':
        """创建成功结果"""
        return cls(
            success=True,
            data=data,
            status=ToolStatus.SUCCESS,
            execution_time_ms=execution_time_ms,
            request_id=request_id,
            metadata=metadata or {}
        )

    @classmethod
    def fail(
        cls,
        error: str,
        status: ToolStatus = ToolStatus.FAILED,
        execution_time_ms: float = 0.0,
        request_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> 'ToolResult':
        """创建失败结果"""
        return cls(
            success=False,
            error=error,
            status=status,
            execution_time_ms=execution_time_ms,
            request_id=request_id,
            metadata=metadata or {}
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "status": self.status.value,
            "execution_time_ms": self.execution_time_ms,
            "request_id": self.request_id,
            "metadata": self.metadata
        }


class BaseTool(ABC):
    """
    工具基类

    所有工具必须继承此类并实现 execute 方法

    示例:
        class MyTool(BaseTool):
            name = "my_tool"
            description = "My custom tool"
            input_schema = {
                "type": "object",
                "properties": {
                    "param1": {"type": "string"}
                },
                "required": ["param1"]
            }

            async def execute(self, context: ToolContext, **kwargs) -> ToolResult:
                # 实现工具逻辑
                return ToolResult.ok(data={"result": "success"})
    """

    # 工具名称（必须覆盖）
    name: str = ""

    # 工具描述（必须覆盖）
    description: str = ""

    # 输入 Schema（JSON Schema 格式）
    input_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": []
    }

    # 输出 Schema（可选）
    output_schema: Optional[Dict[str, Any]] = None

    # 是否需要认证
    requires_auth: bool = False

    # 是否需要审计日志
    requires_audit: bool = True

    # 限流配置（每秒请求数）
    rate_limit: Optional[int] = None

    # 超时时间（秒）
    timeout: float = 30.0

    # 标签（用于分类）
    tags: List[str] = field(default_factory=list)

    def __init__(self):
        """初始化工具"""
        self._execution_count = 0
        self._total_execution_time = 0.0
        self._last_execution_time: Optional[float] = None

        # 验证必填属性
        if not self.name:
            raise ValueError("Tool must have a name")
        if not self.description:
            raise ValueError("Tool must have a description")

    @abstractmethod
    async def execute(self, context: ToolContext, **kwargs) -> ToolResult:
        """
        执行工具

        子类必须实现此方法

        Args:
            context: 工具执行上下文
            **kwargs: 工具参数

        Returns:
            ToolResult: 执行结果
        """
        pass

    async def run(self, context: Optional[ToolContext] = None, **kwargs) -> ToolResult:
        """
        运行工具（带公共处理逻辑）

        此方法执行以下操作：
        1. 验证输入
        2. 执行工具
        3. 记录统计信息

        Args:
            context: 工具执行上下文（可选）
            **kwargs: 工具参数

        Returns:
            ToolResult: 执行结果
        """
        start_time = time.time()
        context = context or ToolContext()

        try:
            # 验证输入
            validation_result = self.validate_input(kwargs)
            if not validation_result[0]:
                return ToolResult.fail(
                    error=validation_result[1],
                    status=ToolStatus.VALIDATION_ERROR,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    request_id=context.request_id
                )

            # 执行工具
            result = await self.execute(context, **kwargs)

            # 更新统计信息
            self._update_stats((time.time() - start_time) * 1000)

            # 确保 request_id 设置
            if result.request_id is None:
                result.request_id = context.request_id

            return result

        except asyncio.TimeoutError:
            execution_time = (time.time() - start_time) * 1000
            self._update_stats(execution_time)
            return ToolResult.fail(
                error=f"Tool execution timed out after {self.timeout}s",
                status=ToolStatus.TIMEOUT,
                execution_time_ms=execution_time,
                request_id=context.request_id
            )

        except PermissionError as e:
            execution_time = (time.time() - start_time) * 1000
            self._update_stats(execution_time)
            return ToolResult.fail(
                error=str(e),
                status=ToolStatus.PERMISSION_DENIED,
                execution_time_ms=execution_time,
                request_id=context.request_id
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self._update_stats(execution_time)
            logger.exception(f"Tool {self.name} execution failed: {e}")
            return ToolResult.fail(
                error=str(e),
                status=ToolStatus.FAILED,
                execution_time_ms=execution_time,
                request_id=context.request_id
            )

    def validate_input(self, kwargs: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        验证输入参数

        Args:
            kwargs: 输入参数

        Returns:
            tuple: (是否有效，错误信息)
        """
        # 检查必填参数
        required = self.input_schema.get("required", [])
        for param in required:
            if param not in kwargs or kwargs[param] is None:
                return False, f"Missing required parameter: {param}"

        # 类型检查（简化版本）
        properties = self.input_schema.get("properties", {})
        for key, value in kwargs.items():
            if key in properties:
                expected_type = properties[key].get("type")
                if expected_type == "string" and not isinstance(value, str):
                    return False, f"Parameter {key} must be a string"
                elif expected_type == "integer" and not isinstance(value, int):
                    return False, f"Parameter {key} must be an integer"
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    return False, f"Parameter {key} must be a number"
                elif expected_type == "boolean" and not isinstance(value, bool):
                    return False, f"Parameter {key} must be a boolean"
                elif expected_type == "array" and not isinstance(value, list):
                    return False, f"Parameter {key} must be an array"
                elif expected_type == "object" and not isinstance(value, dict):
                    return False, f"Parameter {key} must be an object"

        return True, None

    def _update_stats(self, execution_time_ms: float) -> None:
        """更新执行统计"""
        self._execution_count += 1
        self._total_execution_time += execution_time_ms
        self._last_execution_time = execution_time_ms

    @property
    def stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        avg_time = (
            self._total_execution_time / self._execution_count
            if self._execution_count > 0 else 0
        )
        return {
            "name": self.name,
            "execution_count": self._execution_count,
            "total_execution_time_ms": self._total_execution_time,
            "average_execution_time_ms": avg_time,
            "last_execution_time_ms": self._last_execution_time
        }

    def get_info(self) -> Dict[str, Any]:
        """获取工具信息（供 AI 发现）"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "requires_auth": self.requires_auth,
            "rate_limit": self.rate_limit,
            "timeout": self.timeout,
            "tags": self.tags
        }

    def __repr__(self) -> str:
        return f"<Tool name={self.name}>"


def create_tool_class(
    name: str,
    description: str,
    handler: callable,
    input_schema: Optional[Dict] = None,
    **kwargs
) -> Type[BaseTool]:
    """
    动态创建工具类

    Args:
        name: 工具名称
        description: 工具描述
        handler: 处理函数
        input_schema: 输入 schema
        **kwargs: 其他配置

    Returns:
        Type[BaseTool]: 工具类
    """

    class DynamicTool(BaseTool):
        _name = name
        _description = description
        _handler = handler
        _input_schema = input_schema or {}

        def __init__(self):
            super().__init__()
            self.name = self._name
            self.description = self._description
            self.input_schema = self._input_schema
            for key, value in kwargs.items():
                setattr(self, key, value)

        async def execute(self, context: ToolContext, **tool_kwargs) -> ToolResult:
            if asyncio.iscoroutinefunction(self._handler):
                result = await self._handler(**tool_kwargs)
            else:
                result = self._handler(**tool_kwargs)
            return ToolResult.ok(data=result)

    DynamicTool.__name__ = name
    return DynamicTool
