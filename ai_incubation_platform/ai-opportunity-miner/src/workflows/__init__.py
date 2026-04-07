"""
Workflows 模块
DeerFlow 2.0 工作流编排
"""
from workflows.opportunity_workflows import (
    OpportunityDiscoveryWorkflow,
    opportunity_discovery_workflow,
)
from workflows.evaluation_workflows import (
    OpportunityEvaluationWorkflow,
    opportunity_evaluation_workflow,
)
from workflows.push_workflows import (
    AlertPushWorkflow,
    alert_push_workflow,
)

__all__ = [
    "OpportunityDiscoveryWorkflow",
    "opportunity_discovery_workflow",
    "OpportunityEvaluationWorkflow",
    "opportunity_evaluation_workflow",
    "AlertPushWorkflow",
    "alert_push_workflow",
]
