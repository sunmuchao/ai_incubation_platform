"""
工具注册表 - 统一注册所有门户工具
"""
from typing import Any, Dict, Callable
import logging

logger = logging.getLogger(__name__)

# 工具注册表
TOOLS_REGISTRY: Dict[str, Dict[str, Any]] = {}


def register_tool(name: str, description: str, input_schema: Dict[str, Any], handler: Callable):
    """
    注册工具到注册表

    Args:
        name: 工具名称
        description: 工具描述
        input_schema: 输入参数 JSON Schema
        handler: 工具处理函数
    """
    TOOLS_REGISTRY[name] = {
        "name": name,
        "description": description,
        "input_schema": input_schema,
        "handler": handler,
    }
    logger.info(f"Tool registered: {name}")


def get_tool(name: str) -> Dict[str, Any]:
    """获取工具定义"""
    if name not in TOOLS_REGISTRY:
        raise ValueError(f"Tool '{name}' not found")
    return TOOLS_REGISTRY[name]


def list_tools() -> list:
    """列出所有可用工具"""
    return [
        {"name": v["name"], "description": v["description"]}
        for v in TOOLS_REGISTRY.values()
    ]
