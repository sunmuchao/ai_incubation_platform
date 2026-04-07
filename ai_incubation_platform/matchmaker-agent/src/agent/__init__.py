"""
红娘 Agent - DeerFlow 2.0 集成

基于孵化器 Agent 标准，所有具备「LLM + 工具 + 多步编排」能力的系统
统一使用 DeerFlow 2.0 作为通用 Agent 运行时。
"""
from agent.deerflow_client import get_matchmaker_agent
from agent.tools.registry import ToolRegistry

__all__ = [
    "get_matchmaker_agent",
    "ToolRegistry",
]
