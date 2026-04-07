"""
数据库实体模型
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from config.database import Base
from models.product import ProductStatus, GroupBuyStatus, OrderStatus


def generate_uuid():
    return str(uuid.uuid4())


class ProductEntity(Base):
    """商品数据库实体"""
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, index=True, nullable=False)
    description = Column(String)
    category = Column(String, index=True)  # 商品品类（用于推荐系统）
    price = Column(Float, nullable=False)
    original_price = Column(Float, nullable=False)
    image_url = Column(String)
    stock = Column(Integer, default=0)
    locked_stock = Column(Integer, default=0)
    sold_stock = Column(Integer, default=0)
    min_group_size = Column(Integer, default=2)
    max_group_size = Column(Integer, default=10)
    status = Column(Enum(ProductStatus), default=ProductStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    group_buys = relationship("GroupBuyEntity", back_populates="product")


class GroupBuyEntity(Base):
    """团购数据库实体"""
    __tablename__ = "group_buys"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    organizer_id = Column(String, nullable=False)
    target_size = Column(Integer, nullable=False)
    current_size = Column(Integer, default=1)
    status = Column(Enum(GroupBuyStatus), default=GroupBuyStatus.OPEN)
    deadline = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    product = relationship("ProductEntity", back_populates="group_buys")
    members = relationship("GroupMemberEntity", back_populates="group_buy", cascade="all, delete-orphan")
    orders = relationship("OrderEntity", back_populates="group_buy")


class GroupMemberEntity(Base):
    """团购成员数据库实体"""
    __tablename__ = "group_members"

    id = Column(String, primary_key=True, default=generate_uuid)
    group_buy_id = Column(String, ForeignKey("group_buys.id"), nullable=False)
    user_id = Column(String, nullable=False)
    join_time = Column(DateTime, default=datetime.now)
    order_id = Column(String, ForeignKey("orders.id"))

    # 关联
    group_buy = relationship("GroupBuyEntity", back_populates="members")
    order = relationship("OrderEntity", back_populates="group_member", uselist=False)


class OrderEntity(Base):
    """订单数据库实体"""
    __tablename__ = "orders"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, nullable=False)
    group_buy_id = Column(String, ForeignKey("group_buys.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    payment_time = Column(DateTime)
    delivery_time = Column(DateTime)
    completed_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    group_buy = relationship("GroupBuyEntity", back_populates="orders")
    group_member = relationship("GroupMemberEntity", back_populates="order", uselist=False)


class NotificationEntity(Base):
    """通知数据库实体"""
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False)  # stock_alert, group_progress, group_success, group_failed
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    related_id = Column(String)  # 关联ID（商品ID、团购ID等）
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    read_at = Column(DateTime)


class ProductRecommendationEntity(Base):
    """商品推荐数据库实体"""
    __tablename__ = "product_recommendations"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    community_id = Column(String, nullable=False, index=True)
    score = Column(Float, default=0.0)  # 推荐分数
    reason = Column(String)  # 推荐理由
    created_at = Column(DateTime, default=datetime.now)
    expired_at = Column(DateTime)


# ========== 佣金系统实体 ==========

class CommissionRuleEntity(Base):
    """佣金规则数据库实体"""
    __tablename__ = "commission_rules"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)  # 规则名称，如"普通团长"、"金牌团长"
    commission_rate = Column(Float, nullable=False, default=0.10)  # 佣金比例 (0-1)
    min_order_amount = Column(Float, default=0.0)  # 最低订单金额要求
    max_commission = Column(Float)  # 单笔佣金上限 (可选)
    description = Column(String)  # 规则描述
    is_active = Column(Boolean, default=True)  # 是否启用
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CommissionRecordEntity(Base):
    """佣金记录数据库实体"""
    __tablename__ = "commission_records"

    id = Column(String, primary_key=True, default=generate_uuid)
    organizer_id = Column(String, nullable=False, index=True)  # 团长 ID
    group_buy_id = Column(String, ForeignKey("group_buys.id"), nullable=False)  # 团购 ID
    order_ids = Column(String)  # 关联订单 ID 列表 (JSON 字符串)
    total_amount = Column(Float, nullable=False)  # 订单总金额
    commission_rate = Column(Float, nullable=False)  # 佣金比例
    commission_amount = Column(Float, nullable=False)  # 佣金金额
    status = Column(String, default="pending")  # pending:待结算，settled:已结算，withdrawn:已提现
    rule_id = Column(String, ForeignKey("commission_rules.id"))  # 使用的佣金规则 ID
    settled_at = Column(DateTime)  # 结算时间
    withdrawn_at = Column(DateTime)  # 提现时间
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class OrganizerProfileEntity(Base):
    """团长档案数据库实体"""
    __tablename__ = "organizer_profiles"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, nullable=False, unique=True, index=True)  # 用户 ID
    level = Column(String, default="normal")  # normal:普通，gold:金牌，diamond:钻石
    total_commission = Column(Float, default=0.0)  # 累计佣金
    available_commission = Column(Float, default=0.0)  # 可提现佣金
    total_orders = Column(Integer, default=0)  # 累计订单数
    total_sales = Column(Float, default=0.0)  # 累计销售额
    rating = Column(Float, default=5.0)  # 团长评分 (0-5)
    joined_at = Column(DateTime, default=datetime.now)
    last_active_at = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ========== 优惠券系统实体 ==========

class CouponTemplateEntity(Base):
    """优惠券模板数据库实体"""
    __tablename__ = "coupon_templates"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)  # 优惠券名称
    type = Column(String, nullable=False, default="discount")  # discount:折扣券，fixed:满减券
    value = Column(Float, nullable=False)  # 优惠额度 (折扣券为折扣比例，满减券为金额)
    min_purchase = Column(Float, default=0.0)  # 最低消费金额
    max_discount = Column(Float)  # 最大优惠金额 (折扣券专用)
    total_quantity = Column(Integer, default=1000)  # 发放总量
    issued_quantity = Column(Integer, default=0)  # 已发放数量
    used_quantity = Column(Integer, default=0)  # 已使用数量
    valid_from = Column(DateTime, nullable=False)  # 有效期开始
    valid_to = Column(DateTime, nullable=False)  # 有效期结束
    applicable_products = Column(String)  # 适用商品 ID 列表 (JSON 字符串，空表示通用)
    applicable_categories = Column(String)  # 适用品类列表 (JSON 字符串)
    user_limit = Column(Integer, default=1)  # 每人限领数量 (0 表示不限)
    is_active = Column(Boolean, default=True)  # 是否启用
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CouponEntity(Base):
    """用户优惠券数据库实体"""
    __tablename__ = "coupons"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, nullable=False, index=True)  # 用户 ID
    template_id = Column(String, ForeignKey("coupon_templates.id"), nullable=False)  # 模板 ID
    code = Column(String, unique=True, index=True)  # 优惠券码
    status = Column(String, default="available")  # available:可用，used:已使用，expired:已过期
    order_id = Column(String)  # 使用的订单 ID
    valid_from = Column(DateTime, nullable=False)  # 有效期开始
    valid_to = Column(DateTime, nullable=False)  # 有效期结束
    used_at = Column(DateTime)  # 使用时间
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ========== 分享裂变系统实体 ==========

class ShareInviteEntity(Base):
    """分享邀请记录数据库实体"""
    __tablename__ = "share_invites"

    id = Column(String, primary_key=True, default=generate_uuid)
    inviter_id = Column(String, nullable=False, index=True)  # 邀请人 ID
    invitee_id = Column(String, nullable=False, index=True)  # 被邀请人 ID
    invite_code = Column(String, nullable=False, index=True)  # 邀请码
    share_type = Column(String, default="app")  # app:APP 下载，group:团购分享，coupon:优惠券分享
    related_id = Column(String)  # 关联 ID(团购 ID/优惠券 ID 等)
    status = Column(String, default="pending")  # pending:待转化，converted:已转化
    reward_amount = Column(Float, default=0.0)  # 奖励金额
    reward_status = Column(String, default="pending")  # pending:待发放，granted:已发放
    converted_at = Column(DateTime)  # 转化时间
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ShareRewardRuleEntity(Base):
    """分享奖励规则数据库实体"""
    __tablename__ = "share_reward_rules"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)  # 规则名称
    share_type = Column(String, nullable=False)  # app/group/coupon
    reward_type = Column(String, nullable=False, default="cash")  # cash:现金，coupon:优惠券，point:积分
    reward_value = Column(Float, nullable=False)  # 奖励额度
    min_order_amount = Column(Float, default=0.0)  # 被邀请人最低订单金额
    max_reward_per_day = Column(Float, default=100.0)  # 每日奖励上限
    is_active = Column(Boolean, default=True)  # 是否启用
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ========== P4 履约追踪系统实体 ==========

class FulfillmentEntity(Base):
    """履约记录数据库实体"""
    __tablename__ = "fulfillments"

    id = Column(String, primary_key=True, default=generate_uuid)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)  # 订单 ID
    group_buy_id = Column(String, ForeignKey("group_buys.id"), nullable=False)  # 团购 ID
    status = Column(String, nullable=False, default="pending")  # pending:待发货，shipping:配送中，delivered:待自提，completed:已完成，cancelled:已取消
    tracking_number = Column(String)  # 物流单号
    carrier = Column(String)  # 物流公司
    warehouse_id = Column(String)  # 仓库 ID
    shipped_at = Column(DateTime)  # 发货时间
    delivered_at = Column(DateTime)  # 送达时间
    completed_at = Column(DateTime)  # 完成时间
    cancelled_at = Column(DateTime)  # 取消时间
    cancel_reason = Column(String)  # 取消原因
    notes = Column(String)  # 备注信息
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class FulfillmentEventEntity(Base):
    """履约事件记录数据库实体"""
    __tablename__ = "fulfillment_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    fulfillment_id = Column(String, ForeignKey("fulfillments.id"), nullable=False)  # 履约记录 ID
    event_type = Column(String, nullable=False)  # order_created:订单创建，paid:已支付，shipped:已发货，in_transit:运输中，arrived:到达自提点，picked_up:已自提，completed:已完成
    event_time = Column(DateTime, nullable=False, default=datetime.now)  # 事件时间
    location = Column(String)  # 事件地点
    description = Column(String, nullable=False)  # 事件描述
    operator = Column(String)  # 操作人（系统/快递员/团长）
    extra_data = Column(String)  # 额外数据（JSON 字符串）
    created_at = Column(DateTime, default=datetime.now)


# ========== P4 团长管理后台实体 ==========

class OrganizerDashboardEntity(Base):
    """团长仪表盘数据缓存实体"""
    __tablename__ = "organizer_dashboards"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, nullable=False, unique=True, index=True)  # 团长用户 ID
    total_sales = Column(Float, default=0.0)  # 总销售额
    total_orders = Column(Integer, default=0)  # 总订单数
    total_customers = Column(Integer, default=0)  # 总客户数
    total_commission = Column(Float, default=0.0)  # 总佣金
    today_sales = Column(Float, default=0.0)  # 今日销售额
    today_orders = Column(Integer, default=0)  # 今日订单数
    pending_orders = Column(Integer, default=0)  # 待处理订单
    pending_delivery = Column(Integer, default=0)  # 待配送订单
    completed_orders = Column(Integer, default=0)  # 已完成订单
    refund_orders = Column(Integer, default=0)  # 退款订单
    customer_satisfaction = Column(Float, default=5.0)  # 客户满意度 (0-5)
    data_date = Column(DateTime, nullable=False)  # 数据日期
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ========== P4 AI 需求预测实体 ==========

class DemandForecastEntity(Base):
    """需求预测记录数据库实体"""
    __tablename__ = "demand_forecasts"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)  # 商品 ID
    community_id = Column(String, nullable=False, index=True)  # 社区 ID
    forecast_date = Column(DateTime, nullable=False)  # 预测日期
    forecast_quantity = Column(Integer, nullable=False)  # 预测销量
    actual_quantity = Column(Integer)  # 实际销量（事后回填）
    accuracy = Column(Float)  # 预测准确率 (0-1)
    confidence = Column(Float, default=0.0)  # 置信度 (0-1)
    features = Column(String)  # 特征数据（JSON 字符串）
    model_version = Column(String, default="v1")  # 模型版本
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CommunityPreferenceEntity(Base):
    """社区偏好记录数据库实体"""
    __tablename__ = "community_preferences"

    id = Column(String, primary_key=True, default=generate_uuid)
    community_id = Column(String, nullable=False, index=True)  # 社区 ID
    category = Column(String, nullable=False)  # 商品品类
    preference_score = Column(Float, default=0.0)  # 偏好分数 (0-1)
    avg_order_value = Column(Float, default=0.0)  # 平均客单价
    purchase_frequency = Column(Float, default=0.0)  # 购买频率（次/月）
    favorite_brands = Column(String)  # 偏好品牌（JSON 字符串）
    favorite_price_range = Column(String)  # 偏好价格区间（JSON 字符串）
    sample_size = Column(Integer, default=0)  # 样本数量
    last_purchase_at = Column(DateTime)  # 最近购买时间
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
