"""
付费功能闭环数据库模型
- 优惠券/折扣码
- 退款订单
- 发票信息
- 免费试用
- 订阅管理
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from db.database import Base


# ==================== 优惠券/折扣码 ====================

class CouponDB(Base):
    """优惠券定义"""
    __tablename__ = "coupons"

    id = Column(String(36), primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)  # 优惠码
    name = Column(String(100), nullable=False)  # 优惠券名称
    description = Column(Text, default="")  # 描述

    # 折扣类型和值
    type = Column(String(20), nullable=False)  # percentage, fixed_amount, free_trial
    value = Column(Float, nullable=False)  # 折扣值

    # 使用条件
    min_amount = Column(Float, default=0.0)  # 最低消费金额
    max_discount = Column(Float, nullable=True)  # 最大折扣金额

    # 适用范围
    applicable_tiers = Column(Text, default="all")  # JSON 字符串
    applicable_products = Column(Text, default="")  # JSON 字符串

    # 限制
    usage_limit = Column(Integer, nullable=True)  # 总使用次数限制
    usage_count = Column(Integer, default=0)  # 已使用次数
    per_user_limit = Column(Integer, default=1)  # 每用户限用次数
    new_user_only = Column(Boolean, default=False)  # 仅限新用户

    # 有效期
    valid_from = Column(DateTime(timezone=True), server_default=func.now())
    valid_until = Column(DateTime(timezone=True), nullable=True)

    # 状态
    status = Column(String(20), default="active")  # active, used, expired, disabled

    # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(36), nullable=True)  # 创建者 ID


class UserCouponDB(Base):
    """用户领取的优惠券"""
    __tablename__ = "user_coupons"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    coupon_id = Column(String(36), ForeignKey("coupons.id"), nullable=False, index=True)
    coupon_code = Column(String(50), nullable=False, index=True)

    # 状态
    status = Column(String(20), default="active")  # active, used, expired

    # 使用信息
    used_at = Column(DateTime(timezone=True), nullable=True)
    used_on_order_id = Column(String(36), nullable=True)  # 使用的订单 ID

    # 领取信息
    claimed_at = Column(DateTime(timezone=True), server_default=func.now())
    claim_source = Column(String(20), default="manual")  # manual, auto, promotion

    # 过期时间
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ==================== 退款 ====================

class RefundDB(Base):
    """退款申请"""
    __tablename__ = "refunds"

    id = Column(String(36), primary_key=True, index=True)
    order_id = Column(String(36), ForeignKey("membership_orders.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 退款信息
    refund_amount = Column(Float, nullable=False)  # 退款金额
    reason = Column(String(50), nullable=False)  # 退款原因
    description = Column(Text, default="")  # 详细描述

    # 状态
    status = Column(String(20), default="pending")  # pending, approved, rejected, processing, completed, failed

    # 审核信息
    reviewed_by = Column(String(36), nullable=True)  # 审核人 ID
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_note = Column(Text, default="")  # 审核备注

    # 退款执行
    refund_transaction_id = Column(String(100), nullable=True)  # 退款交易 ID
    refunded_at = Column(DateTime(timezone=True), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ==================== 发票 ====================

class InvoiceDB(Base):
    """发票信息"""
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, index=True)
    order_id = Column(String(36), ForeignKey("membership_orders.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 发票信息
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)  # 发票号码
    invoice_code = Column(String(50), nullable=False)  # 发票代码
    invoice_type = Column(String(20), default="electronic")  # electronic, paper

    # 金额
    amount = Column(Float, nullable=False)  # 开票金额
    tax_rate = Column(Float, default=0.06)  # 税率 6%
    tax_amount = Column(Float, default=0.0)  # 税额

    # 购买方信息
    buyer_name = Column(String(200), nullable=False)  # 购买方名称
    buyer_tax_id = Column(String(50), nullable=False)  # 购买方税号
    buyer_address = Column(String(500), default="")  # 地址
    buyer_phone = Column(String(50), default="")  # 电话
    buyer_bank = Column(String(200), default="")  # 开户行及账号

    # 商品信息
    product_name = Column(String(100), default="会员服务")  # 商品名称
    product_spec = Column(String(100), default="")  # 规格型号
    unit = Column(String(20), default="个")  # 单位
    quantity = Column(Integer, default=1)  # 数量

    # 状态
    status = Column(String(20), default="pending")  # pending, issued, sent, cancelled

    # 发送信息
    invoice_url = Column(String(500), nullable=True)  # 电子发票 URL
    sent_at = Column(DateTime(timezone=True), nullable=True)
    sent_to_email = Column(String(255), nullable=True)

    # 邮寄信息 (纸质发票)
    mailing_address = Column(String(500), nullable=True)
    mailing_no = Column(String(100), nullable=True)  # 快递单号
    mailed_at = Column(DateTime(timezone=True), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    issued_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ==================== 免费试用 ====================

class FreeTrialDB(Base):
    """免费试用记录"""
    __tablename__ = "free_trials"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 试用信息
    tier = Column(String(20), default="premium")  # 试用的会员等级
    duration_days = Column(Integer, default=7)  # 试用天数

    # 有效期
    started_at = Column(DateTime(timezone=True), nullable=True)
    ends_at = Column(DateTime(timezone=True), nullable=True)

    # 状态
    status = Column(String(20), default="available")  # available, in_progress, completed, expired

    # 转化信息
    converted_to_paid = Column(Boolean, default=False)  # 是否转化为付费用户
    converted_order_id = Column(String(36), nullable=True)  # 转化订单 ID
    converted_at = Column(DateTime(timezone=True), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ==================== 订阅管理 ====================

class SubscriptionDB(Base):
    """订阅记录 (自动续费)"""
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 订阅信息
    tier = Column(String(20), nullable=False)
    interval = Column(String(20), default="month")  # month, quarter, year
    amount = Column(Float, nullable=False)  # 每期金额

    # 第三方订阅 ID
    provider = Column(String(20), default="")  # wechat, alipay, apple_pay
    provider_subscription_id = Column(String(100), nullable=True)

    # 状态
    status = Column(String(20), default="active")  # active, trialing, past_due, cancelled, expired, paused

    # 周期信息
    current_period_start = Column(DateTime(timezone=True), nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=False)

    # 试用信息
    trial_start = Column(DateTime(timezone=True), nullable=True)
    trial_end = Column(DateTime(timezone=True), nullable=True)

    # 取消信息
    cancel_at_period_end = Column(Boolean, default=False)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(Text, default="")

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
