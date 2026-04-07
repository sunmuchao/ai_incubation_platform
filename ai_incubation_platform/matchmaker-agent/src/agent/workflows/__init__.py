"""
红娘 Agent 工作流模块

包含所有预定义的工作流：
- 匹配工作流
- 约会工作流
- 自主匹配工作流
- 关系健康度工作流
- 破冰助手工作流
"""
from agent.workflows.match_workflow import MatchWorkflow
from agent.workflows.date_workflow import DateWorkflow
from agent.workflows.autonomous_workflows import (
    AutoMatchRecommendWorkflow,
    RelationshipHealthCheckWorkflow,
    AutoIcebreakerWorkflow,
    register_autonomous_workflows,
    run_workflow
)

__all__ = [
    "MatchWorkflow",
    "DateWorkflow",
    "AutoMatchRecommendWorkflow",
    "RelationshipHealthCheckWorkflow",
    "AutoIcebreakerWorkflow",
    "register_autonomous_workflows",
    "run_workflow",
]
