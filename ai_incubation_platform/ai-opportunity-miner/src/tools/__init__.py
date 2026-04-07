"""
Agent 工具包
封装可被 DeerFlow 2.0 调用的业务工具
"""
from tools.opportunity_tools import (
    OPPORTUNITY_TOOLS,
    get_opportunity_tools,
    get_tool_by_name as get_opportunity_tool_by_name,
)
from tools.analysis_tools import (
    ANALYSIS_TOOLS,
    get_analysis_tools,
    get_tool_by_name as get_analysis_tool_by_name,
)

__all__ = [
    "OPPORTUNITY_TOOLS",
    "ANALYSIS_TOOLS",
    "get_opportunity_tools",
    "get_analysis_tools",
    "get_opportunity_tool_by_name",
    "get_analysis_tool_by_name",
]

# 合并所有工具
ALL_TOOLS = OPPORTUNITY_TOOLS + ANALYSIS_TOOLS


def get_all_tools() -> list:
    """获取所有可用工具"""
    return ALL_TOOLS


def get_tool_by_name(name: str):
    """根据名称获取工具"""
    for tool in ALL_TOOLS:
        if tool["name"] == name:
            return tool
    return None
