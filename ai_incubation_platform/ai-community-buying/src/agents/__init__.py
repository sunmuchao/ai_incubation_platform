"""
AI Agent 层 - DeerFlow 2.0 集成

团购智能体及其协作框架，实现自主决策和对话式交互。
"""

from agents.deerflow_client import DeerFlowClient, DeerFlowConfig
from agents.groupbuy_agent import GroupBuyAgent, AgentState

__all__ = [
    # 客户端
    "DeerFlowClient",
    "DeerFlowConfig",
    # Agent
    "GroupBuyAgent",
    "AgentState",
]
