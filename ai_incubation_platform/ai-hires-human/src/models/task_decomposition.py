"""
AI 任务分解功能数据模型。

用于将复杂任务自动拆分为多个子任务，支持：
1. 任务分解策略配置
2. 子任务依赖关系管理
3. 批量分发和聚合
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DecompositionStrategy(str, Enum):
    """任务分解策略。"""
    SEQUENTIAL = "sequential"  # 顺序分解，子任务按顺序执行
    PARALLEL = "parallel"  # 并行分解，子任务可并行执行
    DEPENDENCY_BASED = "dependency_based"  # 基于依赖关系的分解
    HIERARCHICAL = "hierarchical"  # 分层分解，多级子任务


class SubTaskStatus(str, Enum):
    """子任务状态。"""
    PENDING = "pending"
    WAITING_DEPENDENCY = "waiting_dependency"  # 等待依赖任务完成
    PUBLISHED = "published"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SubTask(BaseModel):
    """子任务模型。"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_task_id: str  # 父任务 ID
    root_task_id: str  # 根任务 ID（用于多级分解）

    title: str
    description: str
    requirements: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)

    # 依赖关系
    depends_on: List[str] = Field(default_factory=list)  # 依赖的子任务 ID 列表
    dependency_type: str = "finish_to_start"  # 依赖类型：finish_to_start, start_to_start, finish_to_finish

    # 任务属性
    skill_requirements: Dict[str, str] = Field(default_factory=dict)
    estimated_duration_minutes: int = 30  # 预估完成时间（分钟）
    priority: int = 0  # 优先级，数字越大优先级越高

    # 执行信息
    status: SubTaskStatus = SubTaskStatus.PENDING
    worker_id: Optional[str] = None
    assigned_worker_id: Optional[str] = None  # 指派的工人 ID（可选）

    # 交付物
    delivery_content: Optional[str] = None
    delivery_attachments: List[str] = Field(default_factory=list)
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 结果聚合
    aggregation_weight: float = 1.0  # 聚合权重
    aggregation_role: str = "default"  # 聚合角色（用于区分不同类型的子任务结果）

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None


class TaskDecomposition(BaseModel):
    """任务分解记录模型。"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    root_task_id: str  # 原始任务 ID

    # 分解策略
    strategy: DecompositionStrategy
    strategy_config: Dict[str, Any] = Field(default_factory=dict)  # 策略配置

    # 分解结果
    sub_task_ids: List[str] = Field(default_factory=list)
    total_sub_tasks: int = 0

    # 执行状态
    status: str = "pending"  # pending, in_progress, completed, failed
    completed_count: int = 0
    failed_count: int = 0

    # 聚合结果
    aggregated_result: Optional[str] = None
    aggregated_attachments: List[str] = Field(default_factory=list)

    # 分解元数据
    decomposition_metadata: Dict[str, Any] = Field(default_factory=dict)
    ai_model_used: Optional[str] = None  # 使用的 AI 模型
    decomposition_confidence: float = 0.0  # 分解置信度

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class DecompositionRequest(BaseModel):
    """任务分解请求。"""

    task_id: str
    strategy: DecompositionStrategy = DecompositionStrategy.SEQUENTIAL
    max_sub_tasks: int = 10  # 最大子任务数
    strategy_config: Dict[str, Any] = Field(default_factory=dict)


class DecompositionResponse(BaseModel):
    """任务分解响应。"""

    success: bool
    decomposition_id: Optional[str] = None
    sub_tasks: List[SubTask] = Field(default_factory=list)
    message: str = ""
    estimated_total_duration_minutes: int = 0
    critical_path: List[str] = Field(default_factory=list)  # 关键路径（最长依赖链）


class SubTaskAcceptBody(BaseModel):
    """子任务接单请求体。"""
    worker_id: str


class SubTaskSubmitBody(BaseModel):
    """子任务提交请求体。"""
    worker_id: str
    content: str
    attachments: List[str] = Field(default_factory=list)


class SubTaskCompleteBody(BaseModel):
    """子任务验收请求体。"""
    approved: bool
    reason: Optional[str] = None
