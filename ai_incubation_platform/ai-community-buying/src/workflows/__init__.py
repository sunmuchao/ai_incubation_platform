"""
工作流层 - DeerFlow 2.0 工作流编排

定义团购领域的核心工作流，支持自主决策和多步编排。
"""

from workflows.auto_create_group import AutoCreateGroupWorkflow
from workflows.auto_select_product import AutoSelectProductWorkflow
from workflows.auto_invite import AutoInviteWorkflow

__all__ = [
    "AutoCreateGroupWorkflow",
    "AutoSelectProductWorkflow",
    "AutoInviteWorkflow",
]
