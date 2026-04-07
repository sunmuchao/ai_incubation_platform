"""
AI 员工平台 - Tools 层

基于 DeerFlow 2.0 的工具注册表模式

所有业务操作封装为 AI 可调用的工具，供 Agent 使用:
- talent_tools: 人才分析/匹配工具
- career_tools: 职业发展工具
- performance_tools: 绩效管理工具
"""

from .talent_tools import TOOLS_REGISTRY as TALENT_TOOLS
from .career_tools import TOOLS_REGISTRY as CAREER_TOOLS

# 合并所有工具注册表
ALL_TOOLS = {**TALENT_TOOLS, **CAREER_TOOLS}

__all__ = [
    "TALENT_TOOLS",
    "CAREER_TOOLS",
    "ALL_TOOLS",
]
