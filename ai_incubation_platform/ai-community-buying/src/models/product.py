"""
商品模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import uuid
from enum import Enum


class ProductStatus(str, Enum):
    """商品状态"""
    ACTIVE = "active"       # 可售卖
    SOLD_OUT = "sold_out"   # 售罄
    INACTIVE = "inactive"   # 下架


class GroupBuyStatus(str, Enum):
    """团购状态"""
    OPEN = "open"           # 招募中
    SUCCESS = "success"     # 成团成功
    FAILED = "failed"       # 成团失败
    EXPIRED = "expired"     # 已过期
    CANCELLED = "cancelled" # 已取消


class OrderStatus(str, Enum):
    """订单状态"""
    PENDING = "pending"        # 待支付
    PAID = "paid"              # 已支付
    DELIVERING = "delivering"  # 配送中
    COMPLETED = "completed"    # 已完成
    CANCELLED = "cancelled"    # 已取消
    REFUNDED = "refunded"      # 已退款


class Product(BaseModel):
    """商品模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    price: float  # 团购价
    original_price: float  # 原价
    image_url: Optional[str] = None
    stock: int = 0  # 总库存
    locked_stock: int = 0  # 已锁定库存（参与团购但未最终成交）
    sold_stock: int = 0  # 已售出库存
    min_group_size: int = 2  # 最小成团人数
    max_group_size: int = 10  # 最大成团人数
    status: ProductStatus = ProductStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class GroupBuy(BaseModel):
    """团购模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    organizer_id: str  # 团长 ID
    product: Optional[Product] = None  # 关联商品信息
    target_size: int  # 目标成团人数
    current_size: int = 1  # 当前参团人数
    status: GroupBuyStatus = GroupBuyStatus.OPEN
    deadline: datetime  # 团购截止时间
    members: List[str] = Field(default_factory=list)  # 成员 ID 列表
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def is_expired(self) -> bool:
        """检查团购是否已过期"""
        return datetime.now() > self.deadline

    def can_join(self, user_id: str) -> bool:
        """检查用户是否可以加入该团购"""
        if self.status != GroupBuyStatus.OPEN:
            return False
        if self.is_expired():
            return False
        if user_id in self.members:
            return False
        if len(self.members) >= self.target_size:
            return False
        return True


class Order(BaseModel):
    """订单模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    group_buy_id: str
    product_id: str
    quantity: int = 1
    unit_price: float  # 单价
    total_amount: float  # 总金额
    status: OrderStatus = OrderStatus.PENDING
    payment_time: Optional[datetime] = None
    delivery_time: Optional[datetime] = None
    completed_time: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class GroupJoinRecord(BaseModel):
    """参团记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    group_buy_id: str
    user_id: str
    join_time: datetime = Field(default_factory=datetime.now)
    order_id: Optional[str] = None
    # 状态用于“库存解锁/成团”结果回溯
    # joined: 已参团（未成团/未结束）
    # paid: 已生成订单（成团成功）
    # cancelled: 团长取消
    # expired: 团购过期（人数不足）
    # failed: 其他失败原因（预留）
    status: str = "joined"


class ProductCreate(BaseModel):
    """创建商品请求"""
    name: str
    description: str
    price: float
    original_price: float
    stock: int
    min_group_size: int = 2
    max_group_size: int = 10
    image_url: Optional[str] = None


class GroupBuyCreate(BaseModel):
    """发起团购请求"""
    product_id: str
    organizer_id: str
    target_size: int = 2
    duration_hours: int = 24  # 团购持续时长，默认24小时


class GroupBuyJoinRequest(BaseModel):
    """加入团购请求"""
    user_id: str


# ========== 佣金系统模型 ==========

class CommissionRule(BaseModel):
    """佣金规则模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    commission_rate: float  # 佣金比例 (0-1)
    min_order_amount: float = 0.0
    max_commission: Optional[float] = None
    description: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class CommissionRecord(BaseModel):
    """佣金记录模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organizer_id: str
    group_buy_id: str
    order_ids: List[str]
    total_amount: float
    commission_rate: float
    commission_amount: float
    status: str = "pending"  # pending, settled, withdrawn
    rule_id: Optional[str] = None
    settled_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class OrganizerProfile(BaseModel):
    """团长档案模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    level: str = "normal"  # normal, gold, diamond
    total_commission: float = 0.0
    available_commission: float = 0.0
    total_orders: int = 0
    total_sales: float = 0.0
    rating: float = 5.0
    joined_at: datetime = Field(default_factory=datetime.now)
    last_active_at: datetime = Field(default_factory=datetime.now)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ========== 优惠券系统模型 ==========

class CouponType(str, Enum):
    """优惠券类型"""
    DISCOUNT = "discount"  # 折扣券
    FIXED = "fixed"  # 满减券


class CouponTemplate(BaseModel):
    """优惠券模板模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: CouponType = CouponType.FIXED
    value: float  # 优惠额度
    min_purchase: float = 0.0
    max_discount: Optional[float] = None
    total_quantity: int = 1000
    issued_quantity: int = 0
    used_quantity: int = 0
    valid_from: datetime
    valid_to: datetime
    applicable_products: Optional[List[str]] = None
    applicable_categories: Optional[List[str]] = None
    user_limit: int = 1
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class CouponStatus(str, Enum):
    """优惠券状态"""
    AVAILABLE = "available"
    USED = "used"
    EXPIRED = "expired"


class Coupon(BaseModel):
    """用户优惠券模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    template_id: str
    code: str
    status: CouponStatus = CouponStatus.AVAILABLE
    order_id: Optional[str] = None
    valid_from: datetime
    valid_to: datetime
    used_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ========== 分享裂变系统模型 ==========

class ShareType(str, Enum):
    """分享类型"""
    APP = "app"  # APP 下载
    GROUP = "group"  # 团购分享
    COUPON = "coupon"  # 优惠券分享


class ShareInvite(BaseModel):
    """分享邀请记录模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    inviter_id: str
    invitee_id: str
    invite_code: str
    share_type: ShareType = ShareType.GROUP
    related_id: Optional[str] = None
    status: str = "pending"  # pending, converted
    reward_amount: float = 0.0
    reward_status: str = "pending"  # pending, granted
    converted_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ShareRewardRule(BaseModel):
    """分享奖励规则模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    share_type: ShareType
    reward_type: str = "cash"  # cash, coupon, point
    reward_value: float
    min_order_amount: float = 0.0
    max_reward_per_day: float = 100.0
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ========== 请求/响应模型 ==========

class CommissionRuleCreate(BaseModel):
    """创建佣金规则请求"""
    name: str
    commission_rate: float
    min_order_amount: float = 0.0
    max_commission: Optional[float] = None
    description: Optional[str] = None


class CouponTemplateCreate(BaseModel):
    """创建优惠券模板请求"""
    name: str
    type: CouponType = CouponType.FIXED
    value: float
    min_purchase: float = 0.0
    max_discount: Optional[float] = None
    total_quantity: int = 1000
    valid_from: datetime
    valid_to: datetime
    applicable_products: Optional[List[str]] = None
    applicable_categories: Optional[List[str]] = None
    user_limit: int = 1


class CouponClaimRequest(BaseModel):
    """领取优惠券请求"""
    user_id: str
    template_id: str


class CouponUseRequest(BaseModel):
    """使用优惠券请求"""
    user_id: str
    coupon_id: str
    order_amount: float


class ShareLinkGenerateRequest(BaseModel):
    """生成分享链接请求"""
    user_id: str
    share_type: ShareType
    related_id: Optional[str] = None


class InviteConvertRequest(BaseModel):
    """邀请转化请求"""
    invite_code: str
    invitee_id: str
    order_amount: Optional[float] = 0.0


# ========== P4 履约追踪系统模型 ==========

class FulfillmentStatus(str, Enum):
    """履约状态"""
    PENDING = "pending"       # 待发货
    SHIPPING = "shipping"     # 配送中
    DELIVERED = "delivered"   # 待自提
    COMPLETED = "completed"   # 已完成
    CANCELLED = "cancelled"   # 已取消


class EventType(str, Enum):
    """事件类型"""
    ORDER_CREATED = "order_created"      # 订单创建
    PAID = "paid"                         # 已支付
    SHIPPED = "shipped"                   # 已发货
    IN_TRANSIT = "in_transit"             # 运输中
    ARRIVED = "arrived"                   # 到达自提点
    PICKED_UP = "picked_up"               # 已自提
    COMPLETED = "completed"               # 已完成


class Fulfillment(BaseModel):
    """履约记录模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str
    group_buy_id: str
    status: FulfillmentStatus = FulfillmentStatus.PENDING
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    warehouse_id: Optional[str] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancel_reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class FulfillmentEvent(BaseModel):
    """履约事件模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    fulfillment_id: str
    event_type: EventType
    event_time: datetime = Field(default_factory=datetime.now)
    location: Optional[str] = None
    description: str
    operator: Optional[str] = None  # 系统/快递员/团长
    extra_data: Optional[Dict] = None
    created_at: datetime = Field(default_factory=datetime.now)


# ========== P4 团长管理后台模型 ==========

class OrganizerDashboard(BaseModel):
    """团长仪表盘模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    total_sales: float = 0.0
    total_orders: int = 0
    total_customers: int = 0
    total_commission: float = 0.0
    today_sales: float = 0.0
    today_orders: int = 0
    pending_orders: int = 0
    pending_delivery: int = 0
    completed_orders: int = 0
    refund_orders: int = 0
    customer_satisfaction: float = 5.0
    data_date: datetime
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class DashboardStats(BaseModel):
    """仪表盘统计响应"""
    user_id: str
    total_sales: float
    total_orders: int
    total_customers: int
    total_commission: float
    today_sales: float
    today_orders: int
    pending_orders: int
    pending_delivery: int
    completed_orders: int
    refund_orders: int
    customer_satisfaction: float
    data_date: datetime


# ========== P4 AI 需求预测模型 ==========

class DemandForecast(BaseModel):
    """需求预测模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    community_id: str
    forecast_date: datetime
    forecast_quantity: int
    actual_quantity: Optional[int] = None
    accuracy: Optional[float] = None
    confidence: float = 0.0
    features: Optional[Dict] = None
    model_version: str = "v1"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class CommunityPreference(BaseModel):
    """社区偏好模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    community_id: str
    category: str
    preference_score: float = 0.0
    avg_order_value: float = 0.0
    purchase_frequency: float = 0.0
    favorite_brands: Optional[List[str]] = None
    favorite_price_range: Optional[Dict] = None
    sample_size: int = 0
    last_purchase_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ========== P4 请求/响应模型 ==========

class FulfillmentCreate(BaseModel):
    """创建履约记录请求"""
    order_id: str
    group_buy_id: str
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    warehouse_id: Optional[str] = None


class FulfillmentUpdate(BaseModel):
    """更新履约状态请求"""
    status: FulfillmentStatus
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    notes: Optional[str] = None


class FulfillmentEventCreate(BaseModel):
    """创建履约事件请求"""
    fulfillment_id: str
    event_type: EventType
    location: Optional[str] = None
    description: str
    operator: Optional[str] = None
    extra_data: Optional[Dict] = None


class DemandForecastCreate(BaseModel):
    """创建需求预测请求"""
    product_id: str
    community_id: str
    forecast_date: datetime
    forecast_quantity: int
    confidence: float = 0.0
    features: Optional[Dict] = None
    model_version: str = "v1"


class DemandForecastUpdate(BaseModel):
    """更新需求预测请求"""
    actual_quantity: int
    accuracy: float
