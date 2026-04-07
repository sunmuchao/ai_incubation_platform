"""
P4 供应链与履约优化 - Pydantic 模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import uuid
from enum import Enum


# ========== 枚举类型 ==========

class AlertLevel(str, Enum):
    """预警等级"""
    LOW = "low"           # 低库存
    CRITICAL = "critical" # 严重缺货


class AlertType(str, Enum):
    """预警类型"""
    STOCK_LOW = "stock_low"           # 库存不足
    STOCK_OUT = "stock_out"           # 缺货
    EXPIRY_WARNING = "expiry_warning" # 临期预警


class AlertStatus(str, Enum):
    """预警状态"""
    ACTIVE = "active"     # 活跃
    HANDLED = "handled"   # 已处理
    IGNORED = "ignored"   # 已忽略


class ActionType(str, Enum):
    """行动类型"""
    RESTOCK = "restock"    # 补货
    TRANSFER = "transfer"  # 调拨
    DISCOUNT = "discount"  # 打折促销
    REMOVE = "remove"      # 下架


class ActionStatus(str, Enum):
    """行动状态"""
    PENDING = "pending"       # 待执行
    IN_PROGRESS = "in_progress" # 执行中
    COMPLETED = "completed"   # 已完成
    CANCELLED = "cancelled"   # 已取消


class Priority(str, Enum):
    """优先级"""
    LOW = "low"       # 低
    NORMAL = "normal" # 普通
    HIGH = "high"     # 高
    URGENT = "urgent" # 紧急


class ReplenishmentStatus(str, Enum):
    """补货建议状态"""
    PENDING = "pending"      # 待处理
    CONVERTED = "converted"  # 已转为采购单
    REJECTED = "rejected"    # 已拒绝


class PurchaseOrderStatus(str, Enum):
    """采购订单状态"""
    DRAFT = "draft"        # 草稿
    SUBMITTED = "submitted" # 已提交
    CONFIRMED = "confirmed" # 已确认
    SHIPPING = "shipping"  # 配送中
    RECEIVED = "received"  # 已收货
    CANCELLED = "cancelled" # 已取消


class OrderLineStatus(str, Enum):
    """订单明细状态"""
    PENDING = "pending"     # 待收货
    PARTIAL = "partial"     # 部分收货
    COMPLETED = "completed" # 已完成


class TransactionType(str, Enum):
    """库存变动类型"""
    PURCHASE = "purchase"  # 采购入库
    SALES = "sales"        # 销售出库
    RETURN = "return"      # 退货入库
    ADJUST = "adjust"      # 库存调整
    TRANSFER = "transfer"  # 调拨


# ========== 库存预警模型 ==========

class InventoryAlert(BaseModel):
    """库存预警模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    community_id: str
    current_stock: int
    threshold: int
    alert_level: AlertLevel
    alert_type: AlertType
    message: Optional[str] = None
    status: AlertStatus = AlertStatus.ACTIVE
    suggested_quantity: Optional[int] = None
    handler_id: Optional[str] = None
    handled_at: Optional[datetime] = None
    handled_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class InventoryAlertCreate(BaseModel):
    """创建库存预警请求"""
    product_id: str
    community_id: str
    alert_type: AlertType
    message: Optional[str] = None
    suggested_quantity: Optional[int] = None


class InventoryAlertUpdate(BaseModel):
    """更新库存预警请求"""
    status: Optional[AlertStatus] = None
    handler_id: Optional[str] = None
    handled_notes: Optional[str] = None


class InventoryAlertAction(BaseModel):
    """库存预警行动模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    alert_id: str
    action_type: ActionType
    action_quantity: Optional[int] = None
    action_cost: float = 0.0
    expected_effect_date: Optional[datetime] = None
    status: ActionStatus = ActionStatus.PENDING
    executor_id: Optional[str] = None
    executed_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class InventoryAlertActionCreate(BaseModel):
    """创建库存预警行动请求"""
    action_type: ActionType
    action_quantity: Optional[int] = None
    action_cost: float = 0.0
    expected_effect_date: Optional[datetime] = None
    notes: Optional[str] = None


# ========== 智能补货模型 ==========

class ReplenishmentSuggestion(BaseModel):
    """智能补货建议模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    community_id: str
    current_stock: int
    predicted_demand: int
    predicted_days: int = 7
    suggested_quantity: int
    suggested_order_date: Optional[datetime] = None
    expected_delivery_date: Optional[datetime] = None
    priority: Priority = Priority.NORMAL
    confidence: float = 0.0
    reason: Optional[str] = None
    model_version: str = "v1"
    status: ReplenishmentStatus = ReplenishmentStatus.PENDING
    converted_to_order_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ReplenishmentSuggestionCreate(BaseModel):
    """创建补货建议请求"""
    product_id: str
    community_id: str
    current_stock: int
    predicted_demand: int
    suggested_quantity: int
    priority: Optional[Priority] = Priority.NORMAL
    confidence: float = 0.0
    reason: Optional[str] = None


# ========== 供应商管理模型 ==========

class Supplier(BaseModel):
    """供应商模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    address: Optional[str] = None
    category: Optional[str] = None
    rating: float = 5.0
    total_orders: int = 0
    total_amount: float = 0.0
    on_time_delivery_rate: float = 1.0
    quality_pass_rate: float = 1.0
    response_time_hours: float = 24.0
    payment_terms_days: int = 7
    min_order_amount: float = 0.0
    delivery_lead_days: int = 3
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class SupplierCreate(BaseModel):
    """创建供应商请求"""
    name: str
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    address: Optional[str] = None
    category: Optional[str] = None
    rating: float = 5.0
    payment_terms_days: int = 7
    min_order_amount: float = 0.0
    delivery_lead_days: int = 3


class SupplierUpdate(BaseModel):
    """更新供应商请求"""
    name: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    address: Optional[str] = None
    category: Optional[str] = None
    rating: Optional[float] = None
    payment_terms_days: Optional[int] = None
    min_order_amount: Optional[float] = None
    delivery_lead_days: Optional[int] = None
    is_active: Optional[bool] = None


class SupplierProduct(BaseModel):
    """供应商商品模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    supplier_id: str
    product_id: str
    supplier_product_name: Optional[str] = None
    supplier_product_code: Optional[str] = None
    cost_price: float
    min_order_quantity: int = 1
    lead_days: int = 3
    is_preferred: bool = False
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class SupplierProductCreate(BaseModel):
    """创建供应商商品请求"""
    supplier_id: str
    product_id: str
    supplier_product_name: Optional[str] = None
    cost_price: float
    min_order_quantity: int = 1
    lead_days: int = 3
    is_preferred: bool = False


# ========== 采购订单模型 ==========

class PurchaseOrder(BaseModel):
    """采购订单模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_no: str
    supplier_id: str
    community_id: str
    total_quantity: int = 0
    total_amount: float = 0.0
    status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT
    expected_delivery_date: Optional[datetime] = None
    actual_delivery_date: Optional[datetime] = None
    delivery_address: Optional[str] = None
    receiver_id: Optional[str] = None
    receiver_name: Optional[str] = None
    receiver_phone: Optional[str] = None
    notes: Optional[str] = None
    submitted_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancel_reason: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class PurchaseOrderCreate(BaseModel):
    """创建采购订单请求"""
    supplier_id: str
    community_id: str
    expected_delivery_date: Optional[datetime] = None
    delivery_address: Optional[str] = None
    receiver_name: Optional[str] = None
    receiver_phone: Optional[str] = None
    notes: Optional[str] = None


class PurchaseOrderLine(BaseModel):
    """采购订单明细模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str
    product_id: str
    supplier_product_id: Optional[str] = None
    quantity: int
    unit_cost: float
    line_total: float
    received_quantity: int = 0
    quality_check_quantity: int = 0
    rejected_quantity: int = 0
    quality_issue_reason: Optional[str] = None
    status: OrderLineStatus = OrderLineStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class PurchaseOrderLineCreate(BaseModel):
    """创建采购订单明细请求"""
    product_id: str
    supplier_product_id: Optional[str] = None
    quantity: int
    unit_cost: float


class PurchaseOrderLineUpdate(BaseModel):
    """更新采购订单明细请求"""
    received_quantity: Optional[int] = None
    quality_check_quantity: Optional[int] = None
    rejected_quantity: Optional[int] = None
    quality_issue_reason: Optional[str] = None


# ========== 库存流水模型 ==========

class InventoryTransaction(BaseModel):
    """库存流水模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    community_id: str
    transaction_type: TransactionType
    quantity: int
    balance_before: int
    balance_after: int
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    operator_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class InventoryTransactionCreate(BaseModel):
    """创建库存流水请求"""
    product_id: str
    community_id: str
    transaction_type: TransactionType
    quantity: int
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    operator_id: Optional[str] = None
    notes: Optional[str] = None


# ========== 统计模型 ==========

class InventoryStats(BaseModel):
    """库存统计模型"""
    total_products: int = 0  # 总商品数
    low_stock_count: int = 0  # 低库存商品数
    out_of_stock_count: int = 0  # 缺货商品数
    total_inventory_value: float = 0.0  # 总库存价值
    alert_count: int = 0  # 活跃预警数


class SupplierStats(BaseModel):
    """供应商统计模型"""
    total_suppliers: int = 0  # 总供应商数
    active_suppliers: int = 0  # 活跃供应商数
    avg_delivery_rate: float = 0.0  # 平均交付率
    avg_quality_rate: float = 0.0  # 平均合格率


class PurchaseOrderStats(BaseModel):
    """采购订单统计模型"""
    total_orders: int = 0  # 总订单数
    draft_count: int = 0  # 草稿数
    submitted_count: int = 0  # 已提交数
    confirmed_count: int = 0  # 已确认数
    shipping_count: int = 0  # 配送中数
    received_count: int = 0  # 已收货数
    total_amount: float = 0.0  # 总金额
