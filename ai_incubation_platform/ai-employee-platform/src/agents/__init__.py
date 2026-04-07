"""
AI 员工平台 - Agent 层

基于 DeerFlow 2.0 框架的人才智能体系统

核心组件:
- DeerFlowClient: DeerFlow 2.0 客户端封装
- TalentAgent: 人才智能体，负责自主人才管理与匹配
"""

from .deerflow_client import DeerFlowClient, is_deerflow_available
from .talent_agent import TalentAgent

__all__ = [
    "DeerFlowClient",
    "is_deerflow_available",
    "TalentAgent",
]
