"""
任务模型 — 围绕「AI 能力边界 → 雇佣真人完成真实世界/高判断任务」设计。
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    PUBLISHED = "published"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    MANUAL_REVIEW = "manual_review"  # 人工复核中
    DISPUTE = "dispute"  # 争议仲裁中
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class InteractionType(str, Enum):
    """任务与真实世界/人类的交互形态。"""

    DIGITAL = "digital"  # 线上即可完成（标注、审核、文案判断等）
    PHYSICAL = "physical"  # 需要真人在物理世界在场（跑腿、现场拍照、线下核实等）
    HYBRID = "hybrid"  # 线上交付 + 可能需要线下采集


class Task(BaseModel):
    """AI 因能力边界而发布的任务（对外雇佣真人）。"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ai_employer_id: str

    title: str
    description: str
    requirements: List[str] = Field(default_factory=list)

    # 愿景核心：为何必须由真人 / 真实世界完成
    interaction_type: InteractionType = InteractionType.DIGITAL
    capability_gap: str = ""
    """AI 无法独立完成的原因（例如：需线下到场、需肉身操作、需合规人工签核）。"""

    acceptance_criteria: List[str] = Field(default_factory=list)
    """供 AI 或规则验收时对照的检查项。"""

    location_hint: Optional[str] = None
    """线下/混合任务的可选地点提示（城市、地标级描述，勿放敏感隐私）。"""

    required_skills: Dict[str, str] = Field(default_factory=dict)

    priority: TaskPriority = TaskPriority.MEDIUM

    # 发布后真人可见；创建时默认直接进入 published，避免「建了却接不了单」
    status: TaskStatus = TaskStatus.PUBLISHED

    reward_amount: float = 0.0
    reward_currency: str = "CNY"

    deadline: Optional[datetime] = None

    worker_id: Optional[str] = None

    delivery_content: Optional[str] = None
    delivery_attachments: List[str] = Field(default_factory=list)
    submitted_at: Optional[datetime] = None

    callback_url: Optional[str] = None
    """任务终态（尤其验收通过）后，可通知上游 Agent 的 URL（可选）。"""

    # 人工兜底相关字段
    review_reason: Optional[str] = None
    """审核/复核/取消原因。"""
    reviewer_id: Optional[str] = None
    """人工审核人ID。"""
    appeal_count: int = 0
    """申诉次数。"""
    is_disputed: bool = False
    """是否处于争议状态。"""

    # 反作弊相关字段
    submission_count: int = 0
    """提交次数，用于检测频繁提交作弊。"""
    last_submitted_at: Optional[datetime] = None
    """上次提交时间，用于检测提交频率。"""
    delivery_content_hash: Optional[str] = None
    """交付内容哈希，用于检测重复交付。"""
    cheating_flag: bool = False
    """是否被标记为作弊。"""
    cheating_reason: Optional[str] = None
    """作弊原因说明。"""

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class TaskCreate(BaseModel):
    """AI / Agent 创建任务（即「因能力缺口而雇佣真人」）。"""

    ai_employer_id: str
    title: str
    description: str
    requirements: List[str] = Field(default_factory=list)
    interaction_type: InteractionType = InteractionType.DIGITAL
    capability_gap: str = ""
    acceptance_criteria: List[str] = Field(default_factory=list)
    location_hint: Optional[str] = None
    required_skills: Dict[str, str] = Field(default_factory=dict)
    priority: TaskPriority = TaskPriority.MEDIUM
    reward_amount: float = 0.0
    reward_currency: str = "CNY"
    deadline: Optional[datetime] = None
    publish_immediately: bool = True
    """为 True 时创建后状态为 published；False 时保留 pending 供内部审核后再发布。"""
    callback_url: Optional[str] = None


class TaskAcceptBody(BaseModel):
    worker_id: str


class TaskSubmitBody(BaseModel):
    worker_id: str
    content: str
    attachments: List[str] = Field(default_factory=list)


class TaskCompleteBody(BaseModel):
    ai_employer_id: str
    approved: bool


class TaskCancelBody(BaseModel):
    """任务取消请求体。"""
    operator_id: str
    reason: Optional[str] = None


class TaskManualReviewBody(BaseModel):
    """人工复核请求体。"""
    reviewer_id: str
    approved: bool
    reason: str
    override_ai_decision: bool = False


class TaskAppealBody(BaseModel):
    """争议申诉请求体。"""
    appealer_id: str
    appeal_reason: str
    evidence: List[str] = Field(default_factory=list)


class WorkSubmission(BaseModel):
    """兼容旧文档的工作提交结构（详情以 Task 上字段为准）。"""

    task_id: str
    worker_id: str
    content: str
    attachments: List[str] = Field(default_factory=list)
