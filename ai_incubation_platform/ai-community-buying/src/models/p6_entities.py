"""
P6 运营增强阶段 - 数据库实体模型

包含：
1. 团长考核体系 (Organizer Assessment)
2. 售后流程 (After-Sales Service)
3. 签到积分体系 (Sign-in Points)
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Enum, Boolean, Index, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
from decimal import Decimal
import enum

from config.database import Base


# ====================  enums  ====================

class OrganizerAssessmentStatus(enum.Enum):
    """团长考核状态"""
    PENDING = "pending"       # 待考核
    IN_PROGRESS = "in_progress"  # 考核中
    COMPLETED = "completed"   # 已完成
    APPEALED = "appealed"     # 已申诉


class AssessmentLevel(enum.Enum):
    """考核等级"""
    EXCELLENT = "excellent"   # 优秀 (90-100 分)
    GOOD = "good"            # 良好 (75-89 分)
    PASS = "pass"            # 合格 (60-74 分)
    FAIL = "fail"            # 不合格 (<60 分)


class AfterSalesType(enum.Enum):
    """售后类型"""
    REFUND_ONLY = "refund_only"        # 仅退款
    RETURN_REFUND = "return_refund"    # 退货退款
    EXCHANGE = "exchange"              # 换货
    COMPENSATION = "compensation"      # 补偿


class AfterSalesStatus(enum.Enum):
    """售后状态"""
    PENDING = "pending"           # 待处理
    REVIEWING = "reviewing"       # 审核中
    APPROVED = "approved"         # 已通过
    REJECTED = "rejected"         # 已拒绝
    RETURNING = "returning"       # 退货中
    REFUNDED = "refunded"         # 已退款
    COMPLETED = "completed"       # 已完成
    CANCELLED = "cancelled"       # 已取消


class SigninCalendarEntity(Base):
    """签到日历实体 - 记录用户每日签到"""
    __tablename__ = "signin_calendar"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    signin_date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD 格式
    signin_time = Column(DateTime, default=datetime.now)
    continuous_days = Column(Integer, default=1)  # 连续签到天数
    points_earned = Column(Integer, default=10)  # 获得积分
    bonus_type = Column(String(32), default="normal")  # normal/weekly/monthly
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_user_date", "user_id", "signin_date", unique=True),
    )


class PointsAccountEntity(Base):
    """积分账户实体"""
    __tablename__ = "points_accounts"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, unique=True, index=True)
    total_points = Column(Integer, default=0)  # 累计积分
    available_points = Column(Integer, default=0)  # 可用积分
    used_points = Column(Integer, default=0)  # 已使用积分
    expired_points = Column(Integer, default=0)  # 已过期积分
    level = Column(String(32), default="normal")  # normal/silver/gold/platinum
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class PointsTransactionEntity(Base):
    """积分流水实体"""
    __tablename__ = "points_transactions"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    transaction_type = Column(String(32), nullable=False)  # earn/use/expire/adjust
    points_amount = Column(Integer, nullable=False)  # 正数表示获得，负数表示消费
    balance_after = Column(Integer, nullable=False)  # 变更后余额
    source = Column(String(64), nullable=False)  # signin/order/activity/adjust
    source_id = Column(String(64))  # 关联源 ID(订单 ID/活动 ID 等)
    description = Column(String(256))
    expires_at = Column(DateTime)  # 积分过期时间
    created_at = Column(DateTime, default=datetime.now, index=True)

    __table_args__ = (
        Index("idx_user_type", "user_id", "transaction_type"),
    )


class PointsRuleEntity(Base):
    """积分规则实体"""
    __tablename__ = "points_rules"

    id = Column(String(64), primary_key=True)
    rule_name = Column(String(64), nullable=False, unique=True)  # signin_daily/order_complete 等
    rule_type = Column(String(32), nullable=False)  # earn/use
    points_value = Column(Integer, nullable=False)  # 积分值
    daily_limit = Column(Integer, default=0)  # 每日上限 (0 表示无限制)
    description = Column(String(256))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class OrganizerAssessmentEntity(Base):
    """团长考核实体"""
    __tablename__ = "organizer_assessments"

    id = Column(String(64), primary_key=True)
    organizer_id = Column(String(64), nullable=False, index=True)
    assessment_period = Column(String(32), nullable=False)  # 考核周期 如 2026-W01/2026-01
    assessment_type = Column(String(32), default="monthly")  # weekly/monthly/quarterly

    # 考核指标
    gmv_score = Column(Numeric(5, 2), default=0)  # GMV 得分 (0-100)
    order_score = Column(Numeric(5, 2), default=0)  # 订单量得分 (0-100)
    service_score = Column(Numeric(5, 2), default=0)  # 服务得分 (0-100)
    complaint_score = Column(Numeric(5, 2), default=0)  # 投诉得分 (0-100, 分数越高投诉越少)
    fulfillment_score = Column(Numeric(5, 2), default=0)  # 履约得分 (0-100)

    # 汇总结果
    total_score = Column(Numeric(5, 2), default=0)  # 总分 (0-100)
    assessment_level = Column(Enum(AssessmentLevel), default=AssessmentLevel.PASS)
    status = Column(Enum(OrganizerAssessmentStatus), default=OrganizerAssessmentStatus.PENDING)

    # 考核详情
    gmv_amount = Column(Numeric(12, 2), default=0)  # 周期内 GMV
    order_count = Column(Integer, default=0)  # 周期内订单数
    customer_count = Column(Integer, default=0)  # 服务客户数
    complaint_count = Column(Integer, default=0)  # 投诉次数
    on_time_rate = Column(Numeric(5, 2), default=0)  # 准时履约率

    # 奖惩
    bonus_points = Column(Integer, default=0)  # 奖励积分
    penalty_points = Column(Integer, default=0)  # 扣罚积分
    bonus_amount = Column(Numeric(10, 2), default=0)  # 现金奖励

    # 反馈
    feedback = Column(Text)  # 考核评语
    appeal_reason = Column(Text)  # 申诉理由
    appeal_result = Column(Text)  # 申诉结果

    assessor_id = Column(String(64))  # 考核人 ID
    assessed_at = Column(DateTime)  # 考核时间
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_organizer_period", "organizer_id", "assessment_period", unique=True),
    )


class AfterSalesOrderEntity(Base):
    """售后订单实体"""
    __tablename__ = "after_sales_orders"

    id = Column(String(64), primary_key=True)
    after_sales_no = Column(String(32), nullable=False, unique=True, index=True)  # 售后单号
    order_id = Column(String(64), nullable=False, index=True)  # 原订单 ID
    user_id = Column(String(64), nullable=False, index=True)
    group_buy_id = Column(String(64), nullable=False)  # 团购 ID
    product_id = Column(String(64), nullable=False)
    organizer_id = Column(String(64), nullable=False, index=True)  # 团长 ID

    # 售后信息
    after_sales_type = Column(Enum(AfterSalesType), nullable=False)
    status = Column(Enum(AfterSalesStatus), default=AfterSalesStatus.PENDING)

    # 金额信息
    order_amount = Column(Numeric(12, 2), nullable=False)  # 原订单金额
    refund_amount = Column(Numeric(12, 2), nullable=False)  # 退款金额
    compensation_amount = Column(Numeric(12, 2), default=0)  # 补偿金额

    # 申请信息
    apply_reason = Column(String(512), nullable=False)  # 申请原因
    apply_description = Column(Text)  # 详细描述
    apply_images = Column(Text)  # 凭证图片 (JSON 数组)
    applied_at = Column(DateTime, default=datetime.now)

    # 审核信息
    reviewer_id = Column(String(64))  # 审核人 ID
    review_opinion = Column(String(512))  # 审核意见
    reviewed_at = Column(DateTime)  # 审核时间

    # 退货信息
    return_tracking_no = Column(String(64))  # 退货物流单号
    return_carrier = Column(String(64))  # 退货物流公司
    returned_at = Column(DateTime)  # 退货时间

    # 退款信息
    refund_method = Column(String(32), default="original")  # 退款方式 original/balance
    refund_time = Column(DateTime)  # 退款时间
    refund_transaction_no = Column(String(64))  # 退款流水号

    # 关闭信息
    closed_reason = Column(String(256))
    closed_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_after_sales_user_status", "user_id", "status"),
        Index("idx_after_sales_organizer_status", "organizer_id", "status"),
    )


class AfterSalesLogEntity(Base):
    """售后日志实体 - 记录售后单操作历史"""
    __tablename__ = "after_sales_logs"

    id = Column(String(64), primary_key=True)
    after_sales_id = Column(String(64), nullable=False, index=True)
    operator_id = Column(String(64), nullable=False)  # 操作人 ID
    operator_type = Column(String(32), nullable=False)  # user/organizer/admin/system
    action = Column(String(64), nullable=False)  # apply/review/approve/reject/refund 等
    old_status = Column(String(32))
    new_status = Column(String(32))
    remark = Column(String(512))  # 操作备注
    created_at = Column(DateTime, default=datetime.now, index=True)

    __table_args__ = (
        Index("idx_after_sales_time", "after_sales_id", "created_at"),
    )


class PointsMallItemEntity(Base):
    """积分商城商品实体"""
    __tablename__ = "points_mall_items"

    id = Column(String(64), primary_key=True)
    item_name = Column(String(128), nullable=False)
    item_type = Column(String(32), nullable=False)  # coupon/product/virtual
    item_description = Column(Text)
    points_price = Column(Integer, nullable=False)  # 积分价格
    stock_quantity = Column(Integer, default=0)  # 库存数量
    redeem_limit = Column(Integer, default=0)  # 每人限兑 (0 表示不限)
    redeem_count = Column(Integer, default=0)  # 已兑换数量

    # 关联信息
    ref_id = Column(String(64))  # 关联商品 ID/优惠券 ID
    ref_type = Column(String(32))  # product/coupon

    # 状态
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    image_url = Column(String(256))

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class PointsRedemptionEntity(Base):
    """积分兑换记录实体"""
    __tablename__ = "points_redemptions"

    id = Column(String(64), primary_key=True)
    redemption_no = Column(String(32), nullable=False, unique=True, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    item_id = Column(String(64), nullable=False)
    item_name = Column(String(128), nullable=False)
    points_used = Column(Integer, nullable=False)
    quantity = Column(Integer, default=1)

    # 兑换信息
    ref_id = Column(String(64))  # 关联商品 ID/优惠券 ID
    ref_type = Column(String(32))

    # 状态
    status = Column(String(32), default="pending")  # pending/success/failed
    remark = Column(String(256))

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ====================  关联关系  ====================

# PointsAccount 与 PointsTransaction 一对多
PointsAccountEntity.transactions = relationship(
    "PointsTransactionEntity",
    back_populates="account",
    foreign_keys="PointsTransactionEntity.user_id",
    primaryjoin="PointsAccountEntity.user_id == PointsTransactionEntity.user_id"
)

# 为 PointsTransaction 添加反向关联
PointsTransactionEntity.account = relationship(
    "PointsAccountEntity",
    back_populates="transactions",
    foreign_keys=[PointsTransactionEntity.user_id],
    primaryjoin="PointsAccountEntity.user_id == PointsTransactionEntity.user_id"
)
