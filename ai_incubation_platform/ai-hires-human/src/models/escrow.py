"""
Escrow 资金托管模型。
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class EscrowStatus(str, Enum):
    """Escrow 状态。"""
    PENDING = "pending"  # 待冻结
    FUNDED = "funded"  # 已冻结（资金托管中）
    RELEASED = "released"  # 已释放（给工人）
    REFUNDED = "refunded"  # 已退款（给雇主）
    DISPUTED = "disputed"  # 争议中（资金冻结）
    CANCELLED = "cancelled"  # 已取消


class EscrowTransaction(BaseModel):
    """Escrow 托管交易记录。"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    ai_employer_id: str
    worker_id: Optional[str] = None

    # 金额信息
    principal_amount: float  # 本金（任务报酬）
    platform_fee: float = 0.0  # 平台服务费
    total_amount: float  # 总金额（本金 + 服务费）
    currency: str = "CNY"

    # 状态
    status: EscrowStatus = EscrowStatus.PENDING

    # 资金流向
    funded_at: Optional[datetime] = None  # 资金冻结时间
    released_at: Optional[datetime] = None  # 资金释放时间
    refunded_at: Optional[datetime] = None  # 资金退款时间

    # 争议相关
    dispute_reason: Optional[str] = None
    dispute_resolution: Optional[str] = None  # 争议解决结果：employer_full, worker_full, split
    split_ratio: Optional[float] = None  # 争议_split 时的分配比例（给工人的比例）

    # 审计字段
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    released_by: Optional[str] = None  # 释放操作人
    refunded_by: Optional[str] = None  # 退款操作人
    resolved_by: Optional[str] = None  # 争议仲裁人


class EscrowCreate(BaseModel):
    """创建 Escrow 托管。"""
    task_id: str
    ai_employer_id: str
    principal_amount: float
    platform_fee_rate: float = 0.1  # 平台服务费率，默认 10%


class EscrowReleaseRequest(BaseModel):
    """释放 Escrow 资金请求。"""
    task_id: str
    operator_id: str
    release_to_worker: bool  # True=释放给工人，False=退款给雇主


class EscrowDisputeRequest(BaseModel):
    """Escrow 争议请求。"""
    task_id: str
    requester_id: str
    reason: str
    evidence: List[str] = Field(default_factory=list)


class EscrowResolutionRequest(BaseModel):
    """Escrow 争议解决请求。"""
    task_id: str
    resolver_id: str
    resolution: str  # "employer_full", "worker_full", "split"
    split_ratio: Optional[float] = None  # split 时给工人的比例 (0-1)
    reason: str
