"""
AI Tools 层 - Human-AI Community

本模块包含所有可供 AI Agent 调用的工具。
工具是 AI 与系统交互的标准接口，基于 DeerFlow 2.0 工具注册表模式。

每个工具必须定义：
- name: 工具名称
- description: 供 AI 理解的用途描述
- input_schema: JSON Schema 格式的输入定义
- handler: 处理函数
"""

from tools.community_tools import (
    TOOLS_REGISTRY,
    register_tool,
    get_tool,
    list_tools,
    execute_tool,
)

__all__ = [
    "TOOLS_REGISTRY",
    "register_tool",
    "get_tool",
    "list_tools",
    "execute_tool",
]
