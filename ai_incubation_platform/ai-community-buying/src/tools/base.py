"""
工具基类 - 定义标准化工具接口

所有业务工具必须继承 BaseTool，实现统一的输入输出规范。
工具注册中心支持 DeerFlow 2.0 的工具发现和调用。
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T', bound='BaseTool')


class ToolMetadata(BaseModel):
    """工具元数据"""
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    version: str = Field(default="1.0.0", description="工具版本")
    tags: List[str] = Field(default_factory=list, description="工具标签")
    author: Optional[str] = Field(default=None, description="工具作者")


class ToolRequest(BaseModel):
    """工具请求基类"""
    context: Dict[str, Any] = Field(default_factory=dict, description="调用上下文")
    request_id: Optional[str] = Field(default=None, description="请求 ID，用于日志追踪")


class ToolResponse(BaseModel):
    """工具响应基类"""
    success: bool = Field(..., description="是否成功")
    data: Optional[Any] = Field(default=None, description="返回数据")
    error: Optional[str] = Field(default=None, description="错误信息")
    request_id: Optional[str] = Field(default=None, description="请求 ID，用于日志追踪")

    @classmethod
    def ok(cls, data: Any = None, request_id: Optional[str] = None) -> "ToolResponse":
        """创建成功响应"""
        return cls(success=True, data=data, request_id=request_id)

    @classmethod
    def fail(cls, error: str, request_id: Optional[str] = None) -> "ToolResponse":
        """创建失败响应"""
        return cls(success=False, error=error, request_id=request_id)


class BaseTool(ABC):
    """
    工具基类

    所有业务工具必须继承此类，并实现:
    - get_metadata(): 返回工具元数据
    - get_input_schema(): 返回输入参数的 JSON Schema
    - execute(): 执行工具逻辑
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def get_metadata(self) -> ToolMetadata:
        """返回工具元数据"""
        pass

    @abstractmethod
    def get_input_schema(self) -> Dict[str, Any]:
        """
        返回输入参数的 JSON Schema

        用于 DeerFlow 2.0 的工具注册和参数验证。
        返回格式应符合 JSON Schema Draft 7 规范。
        """
        pass

    @abstractmethod
    def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResponse:
        """
        执行工具逻辑

        Args:
            params: 工具输入参数，已通过 input_schema 验证
            context: 可选的调用上下文，包含 request_id 等追踪信息

        Returns:
            ToolResponse: 工具执行结果
        """
        pass

    def __call__(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResponse:
        """工具调用入口，统一处理异常和日志"""
        request_id = context.get("request_id") if context else None

        try:
            self.logger.info(f"[{request_id}] 工具调用开始：{self.get_metadata().name}, params: {params}")
            result = self.execute(params, context)
            self.logger.info(f"[{request_id}] 工具调用完成：{self.get_metadata().name}, success: {result.success}")
            return result
        except Exception as e:
            self.logger.error(f"[{request_id}] 工具调用异常：{self.get_metadata().name}, error: {str(e)}")
            return ToolResponse.fail(error=str(e), request_id=request_id)


class ToolRegistry:
    """工具注册中心"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """注册工具实例"""
        metadata = tool.get_metadata()
        self._tools[metadata.name] = tool
        logger.info(f"工具注册成功：{metadata.name} v{metadata.version}")

    def get(self, name: str) -> Optional[BaseTool]:
        """获取工具实例"""
        return self._tools.get(name)

    def list_tools(self) -> List[ToolMetadata]:
        """获取所有已注册工具的元数据"""
        return [tool.get_metadata() for tool in self._tools.values()]

    def get_all_tools(self) -> Dict[str, BaseTool]:
        """获取所有工具实例"""
        return self._tools.copy()


# 全局工具注册中心
tool_registry = ToolRegistry()


def register_tool(tool_class: Type[BaseTool]) -> Type[BaseTool]:
    """
    工具注册装饰器

    使用方式:
    @register_tool
    class MyTool(BaseTool):
        ...
    """
    tool = tool_class()
    tool_registry.register(tool)
    return tool_class


def get_tool(name: str) -> Optional[BaseTool]:
    """获取已注册的工具"""
    return tool_registry.get(name)
