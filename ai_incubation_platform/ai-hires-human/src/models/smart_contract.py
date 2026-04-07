"""
智能合约支付模型。
支持多种合约模板：固定价格、小时计费、里程碑支付。
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ContractType(str, Enum):
    """智能合约类型。"""
    FIXED_PRICE = "fixed_price"  # 固定价格
    HOURLY = "hourly"  # 小时计费
    MILESTONE = "milestone"  # 里程碑支付


class ContractStatus(str, Enum):
    """智能合约状态。"""
    DRAFT = "draft"  # 草稿
    ACTIVE = "active"  # 生效中
    EXECUTING = "executing"  # 执行中
    COMPLETED = "completed"  # 已完成
    DISPUTED = "disputed"  # 争议中
    TERMINATED = "terminated"  # 已终止
    PAUSED = "paused"  # 已暂停


class CurrencyType(str, Enum):
    """支持的币种。"""
    # 法币
    CNY = "CNY"  # 人民币
    USD = "USD"  # 美元
    EUR = "EUR"  # 欧元
    JPY = "JPY"  # 日元

    # 加密货币
    USDT = "USDT"  # Tether
    USDC = "USDC"  # USD Coin
    ETH = "ETH"  # Ethereum
    BTC = "BTC"  # Bitcoin


class PaymentConditionType(str, Enum):
    """支付条件类型。"""
    MANUAL = "manual"  # 手动确认支付
    AUTO_ON_DELIVERY = "auto_on_delivery"  # 交付后自动支付
    AUTO_ON_TIME = "auto_on_time"  # 超时自动支付
    AUTO_ON_MILESTONE = "auto_on_milestone"  # 里程碑达成自动支付
    ESCROW_RELEASE = "escrow_release"  # Escrow 释放


class SmartContractTemplate(BaseModel):
    """智能合约模板。"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str

    # 合约类型
    contract_type: ContractType

    # 默认配置
    default_currency: CurrencyType = CurrencyType.CNY
    default_platform_fee_rate: float = 0.1  # 平台服务费率 10%
    default_payment_condition: PaymentConditionType = PaymentConditionType.MANUAL
    default_auto_release_hours: Optional[int] = None  # 自动释放时间（小时）

    # 模板条款
    terms_and_conditions: str = ""

    # 是否启用
    is_active: bool = True

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Milestone(BaseModel):
    """里程碑定义。"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    amount: float  # 里程碑金额
    currency: CurrencyType = CurrencyType.CNY

    # 验收标准
    acceptance_criteria: str = ""

    # 状态
    status: str = "pending"  # pending, completed, verified, paid

    # 时间
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None


class HourlyLog(BaseModel):
    """工时记录。"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    contract_id: str

    # 工作记录
    worker_id: str
    start_time: datetime
    end_time: datetime
    hours_worked: float  # 工作时长（小时）

    # 工作内容
    description: str = ""
    work_screenshot: Optional[str] = None  # 工作截图 URL
    work_description: Optional[str] = None  # 工作描述

    # 审批状态
    status: str = "pending"  # pending, approved, rejected
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    # 金额
    hourly_rate: float  # 时薪
    total_amount: float  # 总金额 = hours_worked * hourly_rate

    created_at: datetime = Field(default_factory=datetime.now)


class SmartContract(BaseModel):
    """智能合约实例。"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    contract_number: str  # 合约编号

    # 合约信息
    template_id: Optional[str] = None  # 使用的模板 ID
    contract_type: ContractType

    # 合同双方
    ai_employer_id: str
    worker_id: str

    # 关联任务
    task_id: Optional[str] = None
    batch_id: Optional[str] = None

    # 金额信息
    currency: CurrencyType = CurrencyType.CNY
    total_amount: float = 0.0  # 总金额
    paid_amount: float = 0.0  # 已支付金额
    remaining_amount: float = 0.0  # 剩余金额

    # 费率
    platform_fee_rate: float = 0.1
    platform_fee: float = 0.0

    # 支付条件
    payment_condition: PaymentConditionType = PaymentConditionType.MANUAL
    auto_release_hours: Optional[int] = None  # 自动释放时间（小时）

    # 针对不同合约类型的特定字段
    # 固定价格：直接使用 total_amount
    # 小时计费：hourly_rate + max_hours
    hourly_rate: Optional[float] = None
    max_hours: Optional[float] = None

    # 里程碑：milestones 列表
    milestones: List[Milestone] = Field(default_factory=list)

    # 状态
    status: ContractStatus = ContractStatus.DRAFT

    # 交付物
    deliverables: List[str] = Field(default_factory=list)  # 交付物描述
    delivery_files: List[str] = Field(default_factory=list)  # 交付文件 URL

    # 时间
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    deadline: Optional[datetime] = None

    # 争议相关
    dispute_reason: Optional[str] = None
    dispute_resolution: Optional[str] = None

    # 区块链存证
    blockchain_proof_id: Optional[str] = None
    contract_hash: Optional[str] = None

    # 审计字段
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by: str = "system"

    # 条款
    terms_and_conditions: str = ""


class SmartContractCreate(BaseModel):
    """创建智能合约请求。"""

    ai_employer_id: str
    worker_id: str
    task_id: Optional[str] = None

    # 合约类型
    contract_type: ContractType

    # 金额
    currency: CurrencyType = CurrencyType.CNY
    total_amount: Optional[float] = None  # 固定价格/里程碑用
    hourly_rate: Optional[float] = None  # 小时计费用
    max_hours: Optional[float] = None  # 小时计费用

    # 里程碑（里程碑类型用）
    milestones: Optional[List[Dict[str, Any]]] = None

    # 支付条件
    payment_condition: PaymentConditionType = PaymentConditionType.MANUAL
    auto_release_hours: Optional[int] = 72  # 默认 72 小时自动释放

    # 其他
    description: Optional[str] = None
    deliverables: List[str] = Field(default_factory=list)
    deadline: Optional[datetime] = None
    terms_and_conditions: Optional[str] = None


class SmartContractUpdate(BaseModel):
    """更新智能合约请求。"""

    status: Optional[ContractStatus] = None
    deliverables: Optional[List[str]] = None
    delivery_files: Optional[List[str]] = None
    dispute_reason: Optional[str] = None


class ContractDisputeRequest(BaseModel):
    """合约争议请求。"""

    contract_id: str
    requester_id: str
    reason: str
    evidence: List[str] = Field(default_factory=list)
    resolution_request: str  # 期望的解决方案


class ContractDisputeResolution(BaseModel):
    """合约争议解决方案。"""

    contract_id: str
    resolver_id: str
    resolution: str  # employer_full, worker_full, split, custom
    split_ratio: Optional[float] = None  # 给工人的比例 (0-1)
    custom_distribution: Optional[Dict[str, float]] = None  # 自定义分配方案
    reason: str


class ContractPaymentTrigger(BaseModel):
    """合约支付触发请求。"""

    contract_id: str
    trigger_type: str  # manual, auto_on_delivery, auto_on_time, milestone_completed
    operator_id: str
    milestone_id: Optional[str] = None  # 里程碑 ID（如果是里程碑支付）


class SmartContractSummary(BaseModel):
    """智能合约汇总统计。"""

    total_contracts: int
    active_contracts: int
    completed_contracts: int
    disputed_contracts: int

    total_value: float  # 总价值
    total_paid: float  # 已支付总额

    by_type: Dict[str, int]  # 按类型统计
    by_currency: Dict[str, int]  # 按币种统计
    by_status: Dict[str, int]  # 按状态统计
