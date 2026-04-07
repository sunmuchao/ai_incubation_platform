"""
AI 员工平台 - Workflows 层

基于 DeerFlow 2.0 的工作流编排

核心工作流:
- talent_workflows: 人才匹配/绩效评估工作流
- career_workflows: 职业发展/技能差距分析工作流
"""

from .talent_workflows import (
    AutoTalentMatchWorkflow,
    AutoPerformanceReviewWorkflow
)
from .career_workflows import (
    AutoCareerPlanningWorkflow,
    AutoSkillGapAnalysisWorkflow
)

__all__ = [
    "AutoTalentMatchWorkflow",
    "AutoPerformanceReviewWorkflow",
    "AutoCareerPlanningWorkflow",
    "AutoSkillGapAnalysisWorkflow",
]
