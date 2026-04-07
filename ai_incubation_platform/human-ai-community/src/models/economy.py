"""
创作者经济系统 - 领域模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


# ==================== 钱包系统 ====================

class WalletStatus(str, Enum):
    """钱包状态"""
    ACTIVE = "active"           # 正常
    FROZEN = "frozen"           # 冻结
    CLOSED = "closed"           # 已关闭


class Wallet(BaseModel):
    """用户钱包"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    owner_id: str               # 所有者 ID（用户/AI 运营者）
    owner_type: str = "member"  # 所有者类型：member, ai_agent
    status: WalletStatus = WalletStatus.ACTIVE

    # 余额（单位：分，避免浮点数精度问题）
    balance: int = 0            # 可用余额
    pending_balance: int = 0    # 待结算余额（打赏/订阅收入待分成）
    total_income: int = 0       # 累计收入
    total_spent: int = 0        # 累计支出

    # 创作者基金相关
    creator_fund_balance: int = 0  # 创作者基金累计收益

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    def is_active(self) -> bool:
        return self.status == WalletStatus.ACTIVE


class WalletTransactionType(str, Enum):
    """交易类型"""
    # 收入类
    DEPOSIT = "deposit"                 # 充值
    TIP_RECEIVED = "tip_received"       # 收到打赏
    SUBSCRIPTION_RECEIVED = "subscription_received"  # 收到订阅
    CREATOR_FUND = "creator_fund"       # 创作者基金收益
    REFUND = "refund"                   # 退款收入

    # 支出类
    WITHDRAW = "withdraw"               # 提现
    TIP_SENT = "tip_sent"               # 发送打赏
    SUBSCRIPTION_PAID = "subscription_paid"  # 订阅支付
    PURCHASE = "purchase"               # 购买付费内容

    # 调整类
    ADJUSTMENT = "adjustment"           # 系统调整
    FEE = "fee"                         # 手续费
    SPLIT = "split"                     # 分成结算


class TransactionStatus(str, Enum):
    """交易状态"""
    PENDING = "pending"     # 待处理
    COMPLETED = "completed" # 已完成
    FAILED = "failed"       # 失败
    REFUNDED = "refunded"   # 已退款


class WalletTransaction(BaseModel):
    """钱包交易记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    wallet_id: str          # 钱包 ID
    transaction_type: WalletTransactionType
    amount: int             # 金额（分），正数表示收入，负数表示支出

    # 关联信息
    related_user_id: Optional[str] = None  # 相关用户 ID（打赏者/被打赏者等）
    related_content_id: Optional[str] = None  # 相关内容 ID（帖子/评论 ID）
    related_subscription_id: Optional[str] = None  # 相关订阅 ID

    # 状态
    status: TransactionStatus = TransactionStatus.PENDING
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


# ==================== 打赏系统 ====================

class TipTier(str, Enum):
    """打赏等级"""
    SMALL = "small"         # 小额：1-10 元
    MEDIUM = "medium"       # 中额：11-50 元
    LARGE = "large"         # 大额：51-200 元
    WHALE = "whale"         # 鲸鱼：200 元以上


class TipMessage(BaseModel):
    """打赏留言"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tip_id: str
    sender_id: str
    sender_name: str
    message: str
    is_public: bool = True  # 是否公开显示
    created_at: datetime = Field(default_factory=datetime.now)


class Tip(BaseModel):
    """打赏记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # 打赏双方
    sender_id: str          # 打赏者 ID
    sender_type: str = "member"  # 打赏者类型
    receiver_id: str        # 接收者 ID
    receiver_type: str = "member"  # 接收者类型

    # 打赏内容
    amount: int             # 金额（分）
    tip_tier: Optional[TipTier] = None  # 打赏等级（自动计算）

    # 关联内容
    content_id: str         # 被打赏内容 ID（帖子/评论）
    content_type: str       # 内容类型：post, comment

    # 留言
    message: Optional[str] = None
    is_anonymous: bool = False  # 是否匿名打赏
    is_public_message: bool = True  # 留言是否公开

    # 状态
    status: TransactionStatus = TransactionStatus.PENDING

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None

    def calculate_tier(self) -> TipTier:
        """根据金额计算打赏等级"""
        if self.amount <= 1000:  # 10 元以下
            return TipTier.SMALL
        elif self.amount <= 5000:  # 50 元以下
            return TipTier.MEDIUM
        elif self.amount <= 20000:  # 200 元以下
            return TipTier.LARGE
        else:
            return TipTier.WHALE


# ==================== 订阅系统 ====================

class SubscriptionTier(str, Enum):
    """订阅等级"""
    FREE = "free"           # 免费
    BASIC = "basic"         # 基础版
    PREMIUM = "premium"     # 高级版
    VIP = "vip"             # VIP
    EXCLUSIVE = "exclusive" # 专属


class SubscriptionPeriod(str, Enum):
    """订阅周期"""
    MONTHLY = "monthly"     # 月付
    QUARTERLY = "quarterly" # 季付
    YEARLY = "yearly"       # 年付


class SubscriptionStatus(str, Enum):
    """订阅状态"""
    ACTIVE = "active"       # 有效
    EXPIRED = "expired"     # 已过期
    CANCELLED = "cancelled" # 已取消
    PENDING = "pending"     # 待生效


class Subscription(BaseModel):
    """订阅记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # 订阅双方
    subscriber_id: str      # 订阅者 ID
    creator_id: str         # 创作者 ID

    # 订阅信息
    tier: SubscriptionTier
    period: SubscriptionPeriod
    price: int              # 价格（分/周期）

    # 状态
    status: SubscriptionStatus = SubscriptionStatus.PENDING

    # 时间
    start_date: datetime
    next_billing_date: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None

    # 统计
    total_paid: int = 0     # 累计支付金额
    billing_count: int = 0  # 已扣费次数

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    def is_active(self) -> bool:
        return self.status == SubscriptionStatus.ACTIVE


class SubscriptionBenefit(BaseModel):
    """订阅权益"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tier: SubscriptionTier
    name: str
    description: str
    icon: Optional[str] = None

    # 权益内容
    can_view_exclusive_content: bool = False  # 查看专属内容
    can_view_early_access: bool = False       # 提前观看
    ad_free: bool = False                      # 免广告
    custom_badge: bool = False                 # 专属徽章
    priority_support: bool = False             # 优先支持
    discount_rate: float = 0.0                 # 打赏折扣率
    max_monthly_tips: Optional[int] = None    # 每月打赏上限


# ==================== 付费内容 ====================

class PaidContentType(str, Enum):
    """付费内容类型"""
    POST = "post"           # 付费帖子
    SERIES = "series"       # 付费系列
    DOWNLOAD = "download"   # 付费下载


class PaidContent(BaseModel):
    """付费内容"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    creator_id: str         # 创作者 ID

    # 内容信息
    content_type: PaidContentType
    title: str
    description: str        # 公开描述（预览）
    preview_content: Optional[str] = None  # 预览内容

    # 价格
    price: int              # 价格（分）
    currency: str = "CNY"

    # 订阅解锁
    require_subscription: Optional[SubscriptionTier] = None  # 需要订阅等级
    allow_one_time_purchase: bool = True  # 允许单独购买

    # 统计
    purchase_count: int = 0
    total_revenue: int = 0

    # 状态
    is_published: bool = False

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class ContentPurchase(BaseModel):
    """内容购买记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    buyer_id: str           # 购买者 ID
    creator_id: str         # 创作者 ID
    content_id: str         # 内容 ID

    # 价格
    price_paid: int         # 实际支付金额
    platform_fee: int = 0   # 平台手续费

    # 状态
    status: TransactionStatus = TransactionStatus.PENDING
    refund_reason: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.now)
    refunded_at: Optional[datetime] = None


# ==================== 收入分成 ====================

class SplitType(str, Enum):
    """分成类型"""
    PLATFORM_creator = "platform_creator"  # 平台与创作者
    CREATOR_COLLAB = "creator_collab"      # 创作者之间协作分成


class RevenueSplit(BaseModel):
    """收入分成记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # 原始收入
    source_transaction_id: str  # 原始交易 ID
    source_type: str            # 来源类型：tip, subscription, purchase

    # 分成配置
    total_amount: int           # 总金额
    platform_rate: float = 0.1  # 平台费率（默认 10%）
    creator_rate: float = 0.9   # 创作者费率（默认 90%）

    # 分成明细
    platform_share: int = 0     # 平台分成
    creator_share: int = 0      # 创作者分成
    collab_shares: List[Dict[str, Any]] = Field(default_factory=list)  # 协作分成

    # 状态
    status: TransactionStatus = TransactionStatus.PENDING

    created_at: datetime = Field(default_factory=datetime.now)
    distributed_at: Optional[datetime] = None

    def calculate_shares(self):
        """计算分成金额"""
        self.platform_share = int(self.total_amount * self.platform_rate)
        self.creator_share = self.total_amount - self.platform_share


# ==================== 创作者基金 ====================

class CreatorFundPool(BaseModel):
    """创作者基金池"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None

    # 资金池
    total_pool: int = 0         # 总资金池（分）
    distributed: int = 0        # 已分配
    remaining: int = 0          # 剩余

    # 分配周期
    period: SubscriptionPeriod
    start_date: datetime
    end_date: datetime

    # 状态
    status: str = "active"  # active, completed, cancelled

    created_at: datetime = Field(default_factory=datetime.now)


class CreatorFundDistribution(BaseModel):
    """创作者基金分配记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pool_id: str              # 基金池 ID
    creator_id: str           # 创作者 ID

    # 分配计算
    score: float              # 创作者得分（基于内容质量、互动等）
    total_score: float        # 所有创作者总分
    allocation_ratio: float   # 分配比例
    amount: int               # 分配金额（分）

    # 状态
    status: TransactionStatus = TransactionStatus.PENDING

    # 时间
    distribution_date: datetime
    paid_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.now)


# ==================== 粉丝等级与权益 ====================

class FanLevel(BaseModel):
    """粉丝等级"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    creator_id: str           # 创作者 ID
    level: int                # 等级（1-10）
    name: str                 # 等级名称

    # 升级条件
    min_support_amount: int   # 最小支持金额（分）
    min_interaction_days: int = 0  # 最小互动天数

    # 专属权益
    benefits: List[str] = Field(default_factory=list)
    custom_badge: Optional[str] = None  # 专属徽章
    color: Optional[str] = None  # 粉丝牌颜色

    created_at: datetime = Field(default_factory=datetime.now)


class FanMembership(BaseModel):
    """粉丝会员记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    fan_id: str               # 粉丝 ID
    creator_id: str           # 创作者 ID

    # 当前等级
    current_level: int = 1
    current_level_name: str = "新粉丝"

    # 累计支持
    total_support_amount: int = 0  # 累计支持金额
    total_tips: int = 0           # 打赏次数
    subscription_months: int = 0  # 订阅月数

    # 互动统计
    interaction_days: int = 0     # 互动天数
    last_interaction_date: Optional[datetime] = None

    # 状态
    is_active: bool = True

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    last_level_up_at: Optional[datetime] = None


# ==================== 请求/响应模型 ====================

class CreateWalletRequest(BaseModel):
    """创建钱包请求"""
    owner_id: str
    owner_type: str = "member"


class WalletBalanceResponse(BaseModel):
    """钱包余额响应"""
    wallet_id: str
    owner_id: str
    balance: int
    balance_yuan: float  # 元为单位
    pending_balance: int
    total_income: int
    total_spent: int


class SendTipRequest(BaseModel):
    """发送打赏请求"""
    sender_id: str
    receiver_id: str
    amount: int = Field(..., gt=0, description="金额（分）")
    content_id: str
    content_type: str
    message: Optional[str] = None
    is_anonymous: bool = False


class TipResponse(BaseModel):
    """打赏响应"""
    tip_id: str
    sender_id: str
    receiver_id: str
    amount: int
    tier: str
    status: str
    created_at: datetime


class CreateSubscriptionRequest(BaseModel):
    """创建订阅请求"""
    subscriber_id: str
    creator_id: str
    tier: SubscriptionTier
    period: SubscriptionPeriod


class SubscriptionResponse(BaseModel):
    """订阅响应"""
    subscription_id: str
    subscriber_id: str
    creator_id: str
    tier: str
    status: str
    start_date: datetime
    next_billing_date: Optional[datetime]


class CreatorDashboardResponse(BaseModel):
    """创作者仪表板响应"""
    creator_id: str

    # 收入统计
    today_income: int
    week_income: int
    month_income: int
    total_income: int

    # 订阅统计
    total_subscribers: int
    active_subscribers: int
    new_subscribers_this_month: int

    # 打赏统计
    total_tips_received: int
    tips_this_month: int

    # 粉丝统计
    total_fans: int
    fan_level_distribution: Dict[int, int]
