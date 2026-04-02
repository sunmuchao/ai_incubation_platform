"""
支付与结算模型。
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class TransactionType(str, Enum):
    DEPOSIT = "deposit"  # 雇主充值
    TASK_PAYMENT = "task_payment"  # 任务支付
    TASK_REFUND = "task_refund"  # 任务退款
    WORKER_PAYOUT = "worker_payout"  # 工人提现
    PLATFORM_FEE = "platform_fee"  # 平台服务费


class PaymentTransaction(BaseModel):
    """支付交易记录。"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    transaction_type: TransactionType
    amount: float
    currency: str = "CNY"

    # 关联方
    payer_id: Optional[str] = None  # 支付方ID（雇主/平台）
    payee_id: Optional[str] = None  # 收款方ID（工人/平台）
    task_id: Optional[str] = None  # 关联任务ID

    status: PaymentStatus = PaymentStatus.PENDING
    payment_method: Optional[str] = None  # 支付方式：alipay, wechat, bank_transfer等
    external_transaction_id: Optional[str] = None  # 外部支付渠道交易号

    description: Optional[str] = None
    fee_amount: float = 0.0  # 平台手续费

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    failed_reason: Optional[str] = None


class Wallet(BaseModel):
    """用户钱包。"""

    user_id: str
    balance: float = 0.0
    frozen_balance: float = 0.0
    currency: str = "CNY"
    updated_at: datetime = Field(default_factory=datetime.now)


class PaymentRequest(BaseModel):
    """创建支付请求。"""

    user_id: str
    amount: float
    payment_method: str
    description: Optional[str] = None


class PayoutRequest(BaseModel):
    """提现请求。"""

    worker_id: str
    amount: float
    payout_method: str
    payout_account: str  # 收款账号信息


class TaskPaymentRequest(BaseModel):
    """任务支付请求（验收通过后触发）。"""

    task_id: str
    ai_employer_id: str
    worker_id: str
    amount: float
    platform_fee_rate: float = 0.1  # 平台服务费比例，默认10%
