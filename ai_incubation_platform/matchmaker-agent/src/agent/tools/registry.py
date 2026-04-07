"""
工具注册表

统一管理所有 Agent 工具的注册和调用。
"""
from typing import Dict, List, Optional, Any, Callable
from utils.logger import logger


class ToolRegistry:
    """
    工具注册表单例类

    用法:
        registry = ToolRegistry.get_instance()
        registry.register(tool)
        result = registry.execute("tool_name", arg1=1, arg2=2)
    """

    _instance: Optional["ToolRegistry"] = None

    def __new__(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
            cls._instance._metadata = {}
        return cls._instance

    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        """获取单例实例"""
        return cls()

    def register(
        self,
        name: str,
        handler: Callable,
        description: str,
        input_schema: dict,
        tags: Optional[List[str]] = None
    ) -> None:
        """
        注册工具

        Args:
            name: 工具名称（唯一标识）
            handler: 处理函数（支持异步）
            description: 工具描述
            input_schema: JSONSchema 格式的输入参数定义
            tags: 工具标签列表
        """
        if name in self._tools:
            logger.warning(f"Tool already registered, overwriting: {name}")

        self._tools[name] = handler
        self._metadata[name] = {
            "description": description,
            "input_schema": input_schema,
            "tags": tags or []
        }
        logger.info(f"Tool registered: {name}")

    def get(self, name: str) -> Optional[Callable]:
        """获取工具处理函数"""
        return self._tools.get(name)

    def get_metadata(self, name: str) -> Optional[dict]:
        """获取工具元数据"""
        return self._metadata.get(name)

    def list_tools(self, tag: Optional[str] = None) -> List[dict]:
        """
        获取工具列表

        Args:
            tag: 按标签过滤

        Returns:
            工具信息列表
        """
        result = []
        for name, metadata in self._metadata.items():
            if tag and tag not in metadata.get("tags", []):
                continue
            result.append({
                "name": name,
                "description": metadata["description"],
                "input_schema": metadata["input_schema"],
                "tags": metadata["tags"]
            })
        return result

    async def execute(self, name: str, **kwargs) -> dict:
        """
        执行工具

        Args:
            name: 工具名称
            **kwargs: 工具参数

        Returns:
            执行结果 {"success": bool, "data/error": any}
        """
        handler = self.get(name)
        if not handler:
            return {"success": False, "error": f"Tool not found: {name}"}

        try:
            logger.info(f"Executing tool: {name}, params: {kwargs}")

            # 判断是否为异步函数
            import inspect
            if inspect.iscoroutinefunction(handler):
                result = await handler(**kwargs)
            else:
                result = handler(**kwargs)

            logger.info(f"Tool execution completed: {name}")
            return {"success": True, "data": result}

        except Exception as e:
            logger.error(f"Tool execution failed: {name}, error: {e}")
            return {"success": False, "error": str(e)}

    def clear(self) -> None:
        """清空所有注册的工具（用于测试）"""
        self._tools.clear()
        self._metadata.clear()
        logger.info("Tool registry cleared")
