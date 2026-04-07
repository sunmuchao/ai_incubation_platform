"""
创作者经济系统 - 数据库模型
"""
from sqlalchemy import Column, String, Integer, BigInteger, ForeignKey, DateTime, func, Enum as SQLAlchemyEnum, Boolean, Float, Text
from sqlalchemy.orm import relationship, declarative_base
from .base import BaseModel
from enum import Enum


# ==================== 钱包系统 ====================

class WalletStatusEnum(str, Enum):
    """钱包状态枚举"""
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"


class DBWallet(BaseModel):
    """用户钱包表"""
    __tablename__ = "wallets"

    id = Column(String(36), primary_key=True, index=True, comment="钱包 ID")
    owner_id = Column(String(36), nullable=False, index=True, comment="所有者 ID")
    owner_type = Column(String(20), nullable=False, default="member", comment="所有者类型")
    status = Column(SQLAlchemyEnum(WalletStatusEnum), nullable=False, default=WalletStatusEnum.ACTIVE, comment="状态")

    # 余额（单位：分）
    balance = Column(BigInteger, nullable=False, default=0, comment="可用余额（分）")
    pending_balance = Column(BigInteger, nullable=False, default=0, comment="待结算余额（分）")
    total_income = Column(BigInteger, nullable=False, default=0, comment="累计收入（分）")
    total_spent = Column(BigInteger, nullable=False, default=0, comment="累计支出（分）")
    creator_fund_balance = Column(BigInteger, nullable=False, default=0, comment="创作者基金累计收益（分）")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")


class TransactionTypeEnum(str, Enum):
    """交易类型枚举"""
    # 收入类
    DEPOSIT = "deposit"
    TIP_RECEIVED = "tip_received"
    SUBSCRIPTION_RECEIVED = "subscription_received"
    CREATOR_FUND = "creator_fund"
    REFUND = "refund"

    # 支出类
    WITHDRAW = "withdraw"
    TIP_SENT = "tip_sent"
    SUBSCRIPTION_PAID = "subscription_paid"
    PURCHASE = "purchase"

    # 调整类
    ADJUSTMENT = "adjustment"
    FEE = "fee"
    SPLIT = "split"


class TransactionStatusEnum(str, Enum):
    """交易状态枚举"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class DBWalletTransaction(BaseModel):
    """钱包交易记录表"""
    __tablename__ = "wallet_transactions"

    id = Column(String(36), primary_key=True, index=True, comment="交易 ID")
    wallet_id = Column(String(36), ForeignKey("wallets.id"), nullable=False, index=True, comment="钱包 ID")

    transaction_type = Column(SQLAlchemyEnum(TransactionTypeEnum), nullable=False, comment="交易类型")
    amount = Column(BigInteger, nullable=False, comment="金额（分），正数收入负数支出")

    # 关联信息
    related_user_id = Column(String(36), comment="相关用户 ID")
    related_content_id = Column(String(36), comment="相关内容 ID")
    related_subscription_id = Column(String(36), comment="相关订阅 ID")

    # 状态
    status = Column(SQLAlchemyEnum(TransactionStatusEnum), nullable=False, default=TransactionStatusEnum.PENDING, comment="状态")
    description = Column(String(500), comment="描述")
    extra_data = Column(Text, comment="元数据（JSON）")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    completed_at = Column(DateTime(timezone=True), comment="完成时间")


# ==================== 打赏系统 ====================

class TipTierEnum(str, Enum):
    """打赏等级枚举"""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    WHALE = "whale"


class DBTip(BaseModel):
    """打赏记录表"""
    __tablename__ = "tips"

    id = Column(String(36), primary_key=True, index=True, comment="打赏 ID")

    # 打赏双方
    sender_id = Column(String(36), nullable=False, index=True, comment="打赏者 ID")
    sender_type = Column(String(20), nullable=False, default="member", comment="打赏者类型")
    receiver_id = Column(String(36), nullable=False, index=True, comment="接收者 ID")
    receiver_type = Column(String(20), nullable=False, default="member", comment="接收者类型")

    # 打赏内容
    amount = Column(BigInteger, nullable=False, comment="金额（分）")
    tip_tier = Column(SQLAlchemyEnum(TipTierEnum), comment="打赏等级")

    # 关联内容
    content_id = Column(String(36), nullable=False, index=True, comment="被打赏内容 ID")
    content_type = Column(String(20), nullable=False, comment="内容类型")

    # 留言
    message = Column(String(1000), comment="留言内容")
    is_anonymous = Column(Boolean, nullable=False, default=False, comment="是否匿名")
    is_public_message = Column(Boolean, nullable=False, default=True, comment="留言是否公开")

    # 状态
    status = Column(SQLAlchemyEnum(TransactionStatusEnum), nullable=False, default=TransactionStatusEnum.PENDING, comment="状态")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    processed_at = Column(DateTime(timezone=True), comment="处理时间")


# ==================== 订阅系统 ====================

class SubscriptionTierEnum(str, Enum):
    """订阅等级枚举"""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    VIP = "vip"
    EXCLUSIVE = "exclusive"


class SubscriptionPeriodEnum(str, Enum):
    """订阅周期枚举"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class SubscriptionStatusEnum(str, Enum):
    """订阅状态枚举"""
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING = "pending"


class DBSubscription(BaseModel):
    """订阅记录表"""
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, index=True, comment="订阅 ID")

    # 订阅双方
    subscriber_id = Column(String(36), nullable=False, index=True, comment="订阅者 ID")
    creator_id = Column(String(36), nullable=False, index=True, comment="创作者 ID")

    # 订阅信息
    tier = Column(SQLAlchemyEnum(SubscriptionTierEnum), nullable=False, comment="订阅等级")
    period = Column(SQLAlchemyEnum(SubscriptionPeriodEnum), nullable=False, comment="订阅周期")
    price = Column(BigInteger, nullable=False, comment="价格（分/周期）")

    # 状态
    status = Column(SQLAlchemyEnum(SubscriptionStatusEnum), nullable=False, default=SubscriptionStatusEnum.PENDING, comment="状态")

    # 时间
    start_date = Column(DateTime(timezone=True), nullable=False, comment="开始日期")
    next_billing_date = Column(DateTime(timezone=True), comment="下次扣费日期")
    cancelled_at = Column(DateTime(timezone=True), comment="取消时间")
    expired_at = Column(DateTime(timezone=True), comment="过期时间")

    # 统计
    total_paid = Column(BigInteger, nullable=False, default=0, comment="累计支付金额（分）")
    billing_count = Column(Integer, nullable=False, default=0, comment="已扣费次数")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")


class DBSubscriptionBenefit(BaseModel):
    """订阅权益配置表"""
    __tablename__ = "subscription_benefits"

    id = Column(String(36), primary_key=True, index=True, comment="权益 ID")
    tier = Column(SQLAlchemyEnum(SubscriptionTierEnum), nullable=False, index=True, comment="订阅等级")
    name = Column(String(100), nullable=False, comment="权益名称")
    description = Column(String(500), comment="权益描述")
    icon = Column(String(200), comment="图标 URL")

    # 权益内容
    can_view_exclusive_content = Column(Boolean, nullable=False, default=False, comment="查看专属内容")
    can_view_early_access = Column(Boolean, nullable=False, default=False, comment="提前观看")
    ad_free = Column(Boolean, nullable=False, default=False, comment="免广告")
    custom_badge = Column(Boolean, nullable=False, default=False, comment="专属徽章")
    priority_support = Column(Boolean, nullable=False, default=False, comment="优先支持")
    discount_rate = Column(Float, nullable=False, default=0.0, comment="打赏折扣率")
    max_monthly_tips = Column(Integer, comment="每月打赏上限")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")


# ==================== 付费内容 ====================

class PaidContentTypeEnum(str, Enum):
    """付费内容类型枚举"""
    POST = "post"
    SERIES = "series"
    DOWNLOAD = "download"


class DBPaidContent(BaseModel):
    """付费内容表"""
    __tablename__ = "paid_contents"

    id = Column(String(36), primary_key=True, index=True, comment="内容 ID")
    creator_id = Column(String(36), nullable=False, index=True, comment="创作者 ID")

    content_type = Column(SQLAlchemyEnum(PaidContentTypeEnum), nullable=False, comment="内容类型")
    title = Column(String(200), nullable=False, comment="标题")
    description = Column(String(1000), comment="公开描述")
    preview_content = Column(Text, comment="预览内容")

    # 价格
    price = Column(BigInteger, nullable=False, comment="价格（分）")
    currency = Column(String(10), nullable=False, default="CNY", comment="货币")

    # 订阅解锁
    require_subscription = Column(String(20), comment="需要订阅等级")
    allow_one_time_purchase = Column(Boolean, nullable=False, default=True, comment="允许单独购买")

    # 统计
    purchase_count = Column(Integer, nullable=False, default=0, comment="购买次数")
    total_revenue = Column(BigInteger, nullable=False, default=0, comment="累计收入（分）")

    # 状态
    is_published = Column(Boolean, nullable=False, default=False, comment="是否发布")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")


class DBContentPurchase(BaseModel):
    """内容购买记录表"""
    __tablename__ = "content_purchases"

    id = Column(String(36), primary_key=True, index=True, comment="购买 ID")
    buyer_id = Column(String(36), nullable=False, index=True, comment="购买者 ID")
    creator_id = Column(String(36), nullable=False, index=True, comment="创作者 ID")
    content_id = Column(String(36), nullable=False, index=True, comment="内容 ID")

    # 价格
    price_paid = Column(BigInteger, nullable=False, comment="实际支付金额（分）")
    platform_fee = Column(BigInteger, nullable=False, default=0, comment="平台手续费（分）")

    # 状态
    status = Column(SQLAlchemyEnum(TransactionStatusEnum), nullable=False, default=TransactionStatusEnum.PENDING, comment="状态")
    refund_reason = Column(String(500), comment="退款原因")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    refunded_at = Column(DateTime(timezone=True), comment="退款时间")


# ==================== 收入分成 ====================

class SplitTypeEnum(str, Enum):
    """分成类型枚举"""
    PLATFORM_CREATOR = "platform_creator"
    CREATOR_COLLAB = "creator_collab"


class DBRevenueSplit(BaseModel):
    """收入分成记录表"""
    __tablename__ = "revenue_splits"

    id = Column(String(36), primary_key=True, index=True, comment="分成 ID")

    # 原始收入
    source_transaction_id = Column(String(36), nullable=False, comment="原始交易 ID")
    source_type = Column(String(50), nullable=False, comment="来源类型")

    # 分成配置
    total_amount = Column(BigInteger, nullable=False, comment="总金额（分）")
    platform_rate = Column(Float, nullable=False, default=0.1, comment="平台费率")
    creator_rate = Column(Float, nullable=False, default=0.9, comment="创作者费率")

    # 分成明细
    platform_share = Column(BigInteger, nullable=False, default=0, comment="平台分成（分）")
    creator_share = Column(BigInteger, nullable=False, default=0, comment="创作者分成（分）")
    collab_shares = Column(Text, comment="协作分成明细（JSON）")

    # 状态
    status = Column(SQLAlchemyEnum(TransactionStatusEnum), nullable=False, default=TransactionStatusEnum.PENDING, comment="状态")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    distributed_at = Column(DateTime(timezone=True), comment="分配时间")


# ==================== 创作者基金 ====================

class CreatorFundPeriodEnum(str, Enum):
    """创作者基金周期枚举"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class DBCreatorFundPool(BaseModel):
    """创作者基金池表"""
    __tablename__ = "creator_fund_pools"

    id = Column(String(36), primary_key=True, index=True, comment="基金池 ID")
    name = Column(String(100), nullable=False, comment="基金池名称")
    description = Column(String(500), comment="描述")

    # 资金池
    total_pool = Column(BigInteger, nullable=False, default=0, comment="总资金池（分）")
    distributed = Column(BigInteger, nullable=False, default=0, comment="已分配（分）")
    remaining = Column(BigInteger, nullable=False, default=0, comment="剩余（分）")

    # 分配周期
    period = Column(SQLAlchemyEnum(CreatorFundPeriodEnum), nullable=False, comment="分配周期")
    start_date = Column(DateTime(timezone=True), nullable=False, comment="开始日期")
    end_date = Column(DateTime(timezone=True), nullable=False, comment="结束日期")

    # 状态
    status = Column(String(20), nullable=False, default="active", comment="状态")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")


class DBCreatorFundDistribution(BaseModel):
    """创作者基金分配记录表"""
    __tablename__ = "creator_fund_distributions"

    id = Column(String(36), primary_key=True, index=True, comment="分配 ID")
    pool_id = Column(String(36), ForeignKey("creator_fund_pools.id"), nullable=False, index=True, comment="基金池 ID")
    creator_id = Column(String(36), nullable=False, index=True, comment="创作者 ID")

    # 分配计算
    score = Column(Float, nullable=False, comment="创作者得分")
    total_score = Column(Float, nullable=False, comment="所有创作者总分")
    allocation_ratio = Column(Float, nullable=False, comment="分配比例")
    amount = Column(BigInteger, nullable=False, comment="分配金额（分）")

    # 状态
    status = Column(SQLAlchemyEnum(TransactionStatusEnum), nullable=False, default=TransactionStatusEnum.PENDING, comment="状态")

    # 时间
    distribution_date = Column(DateTime(timezone=True), nullable=False, comment="分配日期")
    paid_at = Column(DateTime(timezone=True), comment="支付时间")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")


# ==================== 粉丝等级与权益 ====================

class DBFanLevel(BaseModel):
    """粉丝等级配置表"""
    __tablename__ = "fan_levels"

    id = Column(String(36), primary_key=True, index=True, comment="等级 ID")
    creator_id = Column(String(36), nullable=False, index=True, comment="创作者 ID")
    level = Column(Integer, nullable=False, comment="等级（1-10）")
    name = Column(String(50), nullable=False, comment="等级名称")

    # 升级条件
    min_support_amount = Column(BigInteger, nullable=False, default=0, comment="最小支持金额（分）")
    min_interaction_days = Column(Integer, nullable=False, default=0, comment="最小互动天数")

    # 专属权益
    benefits = Column(Text, comment="权益列表（JSON）")
    custom_badge = Column(String(200), comment="专属徽章 URL")
    color = Column(String(20), comment="粉丝牌颜色")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")


class DBFanMembership(BaseModel):
    """粉丝会员记录表"""
    __tablename__ = "fan_memberships"

    id = Column(String(36), primary_key=True, index=True, comment="会员 ID")
    fan_id = Column(String(36), nullable=False, index=True, comment="粉丝 ID")
    creator_id = Column(String(36), nullable=False, index=True, comment="创作者 ID")

    # 当前等级
    current_level = Column(Integer, nullable=False, default=1, comment="当前等级")
    current_level_name = Column(String(50), nullable=False, default="新粉丝", comment="当前等级名称")

    # 累计支持
    total_support_amount = Column(BigInteger, nullable=False, default=0, comment="累计支持金额（分）")
    total_tips = Column(Integer, nullable=False, default=0, comment="打赏次数")
    subscription_months = Column(Integer, nullable=False, default=0, comment="订阅月数")

    # 互动统计
    interaction_days = Column(Integer, nullable=False, default=0, comment="互动天数")
    last_interaction_date = Column(DateTime(timezone=True), comment="最后互动日期")

    # 状态
    is_active = Column(Boolean, nullable=False, default=True, comment="是否激活")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")
    last_level_up_at = Column(DateTime(timezone=True), comment="最后升级时间")
