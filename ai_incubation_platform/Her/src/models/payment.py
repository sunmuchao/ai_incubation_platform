"""
付费功能闭环模型
- 优惠券/折扣码
- 退款订单
- 发票信息
- 免费试用
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum
import uuid


# ==================== 优惠券/折扣码 ====================

class CouponType(str, Enum):
    """优惠券类型"""
    PERCENTAGE = "percentage"  # 百分比折扣 (如 8 折)
    FIXED_AMOUNT = "fixed_amount"  # 固定金额减免 (如减 10 元)
    FREE_TRIAL = "free_trial"  # 免费试用


class CouponStatus(str, Enum):
    """优惠券状态"""
    ACTIVE = "active"  # 可用
    USED = "used"  # 已使用
    EXPIRED = "expired"  # 已过期
    DISABLED = "disabled"  # 已禁用


class CouponTier(str, Enum):
    """优惠券适用会员等级"""
    ALL = "all"  # 所有等级
    STANDARD = "standard"  # 仅标准版
    PREMIUM = "premium"  # 仅高级版


class Coupon(BaseModel):
    """优惠券定义"""
    id: str = str(uuid.uuid4())
    code: str  # 优惠码 (用户输入)
    name: str  # 优惠券名称
    description: str = ""  # 描述

    # 折扣类型和值
    type: CouponType
    value: float  # 折扣值 (百分比 0-100 或固定金额)

    # 使用条件
    min_amount: float = 0.0  # 最低消费金额
    max_discount: Optional[float] = None  # 最大折扣金额 (百分比折扣时用)

    # 适用范围
    applicable_tiers: List[CouponTier] = [CouponTier.ALL]  # 适用会员等级
    applicable_products: List[str] = []  # 适用产品 ID 列表 (空表示所有)

    # 限制
    usage_limit: Optional[int] = None  # 总使用次数限制 (None 表示无限制)
    per_user_limit: int = 1  # 每用户限用次数
    new_user_only: bool = False  # 仅限新用户

    # 有效期
    valid_from: datetime = datetime.now()
    valid_until: Optional[datetime] = None  # None 表示永久有效

    # 状态
    status: CouponStatus = CouponStatus.ACTIVE

    # 元数据
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    created_by: Optional[str] = None  # 创建者 ID (管理员)

    def is_valid(self) -> bool:
        """检查优惠券是否有效"""
        if self.status != CouponStatus.ACTIVE:
            return False
        if self.valid_until and datetime.now() > self.valid_until:
            return False
        if self.valid_from and datetime.now() < self.valid_from:
            return False
        return True

    def calculate_discount(self, amount: float) -> float:
        """计算折扣金额"""
        if not self.is_valid():
            return 0.0

        if self.type == CouponType.PERCENTAGE:
            discount = amount * (self.value / 100)
            if self.max_discount:
                discount = min(discount, self.max_discount)
            return round(discount, 2)
        elif self.type == CouponType.FIXED_AMOUNT:
            return min(self.value, amount)
        elif self.type == CouponType.FREE_TRIAL:
            return amount  # 全额减免

        return 0.0

    def can_apply_to_tier(self, tier: str) -> bool:
        """检查是否适用于某个会员等级"""
        if CouponTier.ALL in self.applicable_tiers:
            return True
        return CouponTier(tier) in self.applicable_tiers


class UserCoupon(BaseModel):
    """用户领取的优惠券"""
    id: str = str(uuid.uuid4())
    user_id: str
    coupon_id: str
    coupon_code: str

    # 状态
    status: CouponStatus = CouponStatus.ACTIVE

    # 使用信息
    used_at: Optional[datetime] = None
    used_on_order_id: Optional[str] = None  # 使用的订单 ID

    # 领取信息
    claimed_at: datetime = datetime.now()
    claim_source: str = "manual"  # manual, auto, promotion

    # 过期时间 (继承自优惠券，但可能有特殊过期时间)
    expires_at: Optional[datetime] = None


# ==================== 退款 ====================

class RefundStatus(str, Enum):
    """退款状态"""
    PENDING = "pending"  # 待处理
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 已拒绝
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


class RefundReason(str, Enum):
    """退款原因"""
    USER_REQUEST = "user_request"  # 用户主动申请
    PAYMENT_FAILED = "payment_failed"  # 支付失败
    DUPLICATE_ORDER = "duplicate_order"  # 重复下单
    SYSTEM_ERROR = "system_error"  # 系统错误
    OTHER = "other"  # 其他


class RefundRequest(BaseModel):
    """退款申请"""
    id: str = str(uuid.uuid4())
    order_id: str
    user_id: str

    # 退款信息
    refund_amount: float  # 退款金额
    reason: RefundReason
    description: str = ""  # 详细描述

    # 状态
    status: RefundStatus = RefundStatus.PENDING

    # 审核信息
    reviewed_by: Optional[str] = None  # 审核人 ID
    reviewed_at: Optional[datetime] = None
    review_note: str = ""  # 审核备注

    # 退款执行
    refund_transaction_id: Optional[str] = None  # 退款交易 ID
    refunded_at: Optional[datetime] = None

    # 时间戳
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()


# ==================== 发票 ====================

class InvoiceType(str, Enum):
    """发票类型"""
    ELECTRONIC = "electronic"  # 电子发票
    PAPER = "paper"  # 纸质发票


class InvoiceStatus(str, Enum):
    """发票状态"""
    PENDING = "pending"  # 待开具
    ISSUED = "issued"  # 已开具
    SENT = "sent"  # 已发送
    CANCELLED = "cancelled"  # 已取消


class Invoice(BaseModel):
    """发票信息"""
    id: str = str(uuid.uuid4())
    order_id: str
    user_id: str

    # 发票信息
    invoice_number: str  # 发票号码
    invoice_code: str  # 发票代码
    invoice_type: InvoiceType = InvoiceType.ELECTRONIC

    # 金额
    amount: float  # 开票金额
    tax_rate: float = 0.06  # 税率 6%
    tax_amount: float = 0.0  # 税额

    # 购买方信息
    buyer_name: str  # 购买方名称
    buyer_tax_id: str  # 购买方税号
    buyer_address: str = ""  # 地址
    buyer_phone: str = ""  # 电话
    buyer_bank: str = ""  # 开户行及账号

    # 商品信息
    product_name: str = "会员服务"  # 商品名称
    product_spec: str = ""  # 规格型号
    unit: str = "个"  # 单位
    quantity: int = 1  # 数量

    # 状态
    status: InvoiceStatus = InvoiceStatus.PENDING

    # 发送信息
    invoice_url: Optional[str] = None  # 电子发票 URL
    sent_at: Optional[datetime] = None
    sent_to_email: Optional[str] = None

    # 邮寄信息 (纸质发票)
    mailing_address: Optional[str] = None
    mailing_no: Optional[str] = None  # 快递单号
    mailed_at: Optional[datetime] = None

    # 时间戳
    created_at: datetime = datetime.now()
    issued_at: Optional[datetime] = None
    updated_at: datetime = datetime.now()


# ==================== 免费试用 ====================

class TrialStatus(str, Enum):
    """试用状态"""
    AVAILABLE = "available"  # 可用
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"  # 已完成
    EXPIRED = "expired"  # 已过期


class FreeTrial(BaseModel):
    """免费试用记录"""
    id: str = str(uuid.uuid4())
    user_id: str

    # 试用信息
    tier: str = "premium"  # 试用的会员等级
    duration_days: int = 7  # 试用天数

    # 有效期
    started_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None

    # 状态
    status: TrialStatus = TrialStatus.AVAILABLE

    # 转化信息
    converted_to_paid: bool = False  # 是否转化为付费用户
    converted_order_id: Optional[str] = None  # 转化订单 ID
    converted_at: Optional[datetime] = None

    # 时间戳
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    def is_active(self) -> bool:
        """检查试用是否有效"""
        if self.status != TrialStatus.IN_PROGRESS:
            return False
        if self.ends_at and datetime.now() > self.ends_at:
            return False
        return True


# ==================== 订阅管理 ====================

class SubscriptionStatus(str, Enum):
    """订阅状态"""
    ACTIVE = "active"  # 活跃
    TRIALING = "trialing"  # 试用中
    PAST_DUE = "past_due"  # 逾期未付
    CANCELLED = "cancelled"  # 已取消
    EXPIRED = "expired"  # 已过期
    PAUSED = "paused"  # 暂停


class Subscription(BaseModel):
    """订阅记录 (自动续费)"""
    id: str = str(uuid.uuid4())
    user_id: str

    # 订阅信息
    tier: str
    interval: str = "month"  # month, quarter, year
    amount: float  # 每期金额

    # 第三方订阅 ID (如微信支付订阅 ID)
    provider: str = ""  # wechat, alipay, apple_pay
    provider_subscription_id: Optional[str] = None

    # 状态
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE

    # 周期信息
    current_period_start: datetime
    current_period_end: datetime

    # 试用信息
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None

    # 取消信息
    cancel_at_period_end: bool = False  # 是否在周期结束时取消
    cancelled_at: Optional[datetime] = None
    cancel_reason: str = ""

    # 时间戳
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()


# ==================== 请求/响应模型 ====================

class CouponCreate(BaseModel):
    """创建优惠券请求"""
    code: str
    name: str
    description: str = ""
    type: CouponType
    value: float
    min_amount: float = 0.0
    max_discount: Optional[float] = None
    applicable_tiers: List[CouponTier] = [CouponTier.ALL]
    usage_limit: Optional[int] = None
    per_user_limit: int = 1
    new_user_only: bool = False
    valid_days: int = 30  # 有效期天数


class CouponClaimRequest(BaseModel):
    """领取优惠券请求"""
    coupon_code: str


class ApplyCouponRequest(BaseModel):
    """应用优惠券请求"""
    coupon_code: str
    tier: str
    duration_months: int
    amount: float


class ApplyCouponResponse(BaseModel):
    """应用优惠券响应"""
    valid: bool
    message: str
    original_amount: float
    discount_amount: float
    final_amount: float


class RefundCreateRequest(BaseModel):
    """创建退款申请请求"""
    order_id: str
    reason: RefundReason
    description: str = ""


class RefundApproveRequest(BaseModel):
    """批准退款请求"""
    refund_id: str
    note: str = ""


class RefundRejectRequest(BaseModel):
    """拒绝退款请求"""
    refund_id: str
    note: str = ""


class InvoiceCreateRequest(BaseModel):
    """创建发票请求"""
    order_id: str
    invoice_type: InvoiceType = InvoiceType.ELECTRONIC
    buyer_name: str
    buyer_tax_id: str
    buyer_address: str = ""
    buyer_phone: str = ""
    buyer_bank: str = ""
    sent_to_email: Optional[str] = None
    mailing_address: Optional[str] = None


class TrialStartRequest(BaseModel):
    """开始试用请求"""
    tier: str = "premium"
    duration_days: int = 7


class SubscriptionCreateRequest(BaseModel):
    """创建订阅请求"""
    tier: str
    interval: str = "month"
    payment_method: str = "wechat"
    auto_renew: bool = True


# ==================== 统计模型 ====================

class PaymentStats(BaseModel):
    """支付统计"""
    total_orders: int
    paid_orders: int
    total_revenue: float
    refunded_amount: float
    net_revenue: float
    new_paying_users: int
    converted_from_trial: int


class CouponStats(BaseModel):
    """优惠券统计"""
    total_coupons: int
    active_coupons: int
    total_claimed: int
    total_used: int
    total_discount_amount: float


class TrialStats(BaseModel):
    """试用统计"""
    total_trials: int
    active_trials: int
    expired_trials: int
    converted_trials: int
    conversion_rate: float  # 转化率
