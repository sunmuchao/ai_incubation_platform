"""
AI Workflows 层 - Human-AI Community

本模块包含所有 AI 工作流定义，基于 DeerFlow 2.0 声明式工作流模式。
工作流用于编排多步任务，支持 AI 自主决策和执行。
"""

from workflows.community_workflows import (
    CommunityWorkflows,
    ModerationWorkflow,
    MatchingWorkflow,
    RecommendationWorkflow,
    get_workflow,
    list_workflows,
)

__all__ = [
    "CommunityWorkflows",
    "ModerationWorkflow",
    "MatchingWorkflow",
    "RecommendationWorkflow",
    "get_workflow",
    "list_workflows",
]
