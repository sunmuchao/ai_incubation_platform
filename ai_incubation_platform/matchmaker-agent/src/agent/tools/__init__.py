"""
红娘 Agent 工具集

所有工具按功能分类，每个工具实现：
- name: 工具名称
- description: 工具描述
- input_schema: JSONSchema 输入定义
- handler: 处理函数
"""
from agent.tools.registry import ToolRegistry
from agent.tools.profile_tool import ProfileTool
from agent.tools.match_tool import MatchTool
from agent.tools.reasoning_tool import ReasoningTool
from agent.tools.logging_tool import LoggingTool
from agent.tools.autonomous_tools import (
    CompatibilityAnalysisTool,
    TopicSuggestionTool,
    RelationshipTrackingTool,
    register_autonomous_tools
)

__all__ = [
    "ToolRegistry",
    "ProfileTool",
    "MatchTool",
    "ReasoningTool",
    "LoggingTool",
    "CompatibilityAnalysisTool",
    "TopicSuggestionTool",
    "RelationshipTrackingTool",
    "register_autonomous_tools",
]
