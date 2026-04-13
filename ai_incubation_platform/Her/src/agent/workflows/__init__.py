"""
红娘 Agent 工作流模块

包含预定义的工作流：
- 约会工作流

注：MatchWorkflow 和 autonomous_workflows 已废弃。
匹配功能使用 ConversationMatchService + DeerFlow her_tools。
"""
from agent.workflows.date_workflow import DateWorkflow

__all__ = [
    "DateWorkflow",
]
