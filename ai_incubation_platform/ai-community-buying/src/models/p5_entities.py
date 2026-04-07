"""
P5 营销自动化系统 - 数据库实体模型

包含：
1. 用户分群系统 (Customer Segmentation) - 基于 RFM 模型的用户分群
2. 营销自动化引擎 (Marketing Automation) - 自动营销活动配置
3. 营销 ROI 分析 (Marketing ROI) - 营销活动效果追踪
4. A/B 测试框架 (A/B Testing) - 营销活动对比测试
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Boolean, Text, Numeric, Float, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import json
from config.database import Base


def generate_uuid():
    return str(uuid.uuid4())


# ====================  Enums  ====================

class CustomerSegmentType:
    """客户分群类型"""
    HIGH_VALUE = "high_value"         # 高价值客户（R 近 F 高 M 高）
    POTENTIAL = "potential"           # 潜力客户（R 近 F 低 M 低）
    CHURNING = "churning"             # 流失风险客户（R 远）
    DORMANT = "dormant"               # 沉睡客户（长期未购买）
    NEW = "new"                       # 新客户
    BARGAIN_HUNTER = "bargain_hunter" # 价格敏感型


class CampaignAutomationType:
    """自动化营销活动类型"""
    CART_ABANDON = "cart_abandon"     # 购物车放弃挽回
    BROWSE_ABANDON = "browse_abandon" # 浏览未购买挽回
    REACTIVATION = "reactivation"     # 用户召回
    BIRTHDAY = "birthday"             # 生日营销
    ANNIVERSARY = "anniversary"       # 注册周年营销
    UPGRADE = "upgrade"               # 升级推荐
    CROSS_SELL = "cross_sell"         # 交叉销售
    REPLENISHMENT = "replenishment"   # 补货提醒


class AutomationStatus:
    """自动化活动状态"""
    DRAFT = "draft"                   # 草稿
    ACTIVE = "active"                 # 进行中
    PAUSED = "paused"                 # 已暂停
    COMPLETED = "completed"           # 已完成
    CANCELLED = "cancelled"           # 已取消


class ABTestStatus:
    """A/B 测试状态"""
    DRAFT = "draft"                   # 草稿
    RUNNING = "running"               # 进行中
    COMPLETED = "completed"           # 已完成
    ANALYZING = "analyzing"           # 分析中
    CONCLUDED = "concluded"           # 已得出结论


class ConversionType:
    """转化类型"""
    VIEW = "view"                     # 浏览
    CLICK = "click"                   # 点击
    ADD_TO_CART = "add_to_cart"       # 加购
    PURCHASE = "purchase"             # 购买
    SHARE = "share"                   # 分享


# ====================  用户分群系统  ====================

class CustomerSegmentEntity(Base):
    """客户分群定义实体"""
    __tablename__ = "customer_segments"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    segment_name = Column(String(128), nullable=False)  # 分群名称
    segment_type = Column(String(32), nullable=False)   # 分群类型

    # 分群规则（JSON 格式）
    # 示例：{"r_days": 30, "f_min": 3, "m_min": 500}
    rules = Column(Text, nullable=False)

    # 分群描述
    description = Column(String(512))

    # 分群规模
    customer_count = Column(Integer, default=0)

    # 状态
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    customers = relationship("CustomerSegmentMemberEntity", back_populates="segment", cascade="all, delete-orphan")


class CustomerSegmentMemberEntity(Base):
    """客户分群成员实体 - 记录用户所属分群"""
    __tablename__ = "customer_segment_members"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    segment_id = Column(String(64), ForeignKey("customer_segments.id"), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)

    # RFM 评分
    recency_score = Column(Integer, default=5)   # 最近一次消费时间评分 (1-5)
    frequency_score = Column(Integer, default=5) # 消费频率评分 (1-5)
    monetary_score = Column(Integer, default=5)  # 消费金额评分 (1-5)
    rfm_total = Column(Integer, default=15)      # RFM 总分 (5-25)

    # 用户价值标签
    value_tags = Column(String(256))  # 标签列表，逗号分隔

    # 最后更新时间
    last_purchase_at = Column(DateTime)  # 最后购买时间
    total_orders = Column(Integer, default=0)  # 累计订单数
    total_amount = Column(Numeric(14, 2), default=0)  # 累计消费金额

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    segment = relationship("CustomerSegmentEntity", back_populates="customers")

    __table_args__ = (
        Index("idx_segment_user", "segment_id", "user_id", unique=True),
    )


class CustomerBehaviorEntity(Base):
    """客户行为追踪实体 - 用于用户分群分析"""
    __tablename__ = "customer_behaviors"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    user_id = Column(String(64), nullable=False, index=True)

    # 浏览行为
    viewed_products = Column(String(1024))  # 浏览商品 ID 列表，逗号分隔
    viewed_categories = Column(String(256))  # 浏览品类列表，逗号分隔
    total_views = Column(Integer, default=0)

    # 购买行为
    purchased_products = Column(String(1024))  # 购买商品 ID 列表，逗号分隔
    purchased_categories = Column(String(256))  # 购买品类列表，逗号分隔
    avg_order_value = Column(Numeric(10, 2), default=0)  # 平均订单金额

    # 偏好分析
    favorite_price_range = Column(String(32))  # 偏好价格区间
    favorite_category = Column(String(64))     # 偏好品类
    purchase_time_preference = Column(String(32))  # 购买时间偏好（morning/afternoon/evening/night）

    # 活跃状态
    last_active_at = Column(DateTime)
    active_days_count = Column(Integer, default=0)  # 活跃天数

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_user_id", "user_id", unique=True),
    )


# ====================  营销自动化引擎  ====================

class MarketingAutomationEntity(Base):
    """营销自动化活动配置实体"""
    __tablename__ = "marketing_automations"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    campaign_name = Column(String(128), nullable=False)  # 活动名称
    automation_type = Column(String(32), nullable=False)  # 自动化类型

    # 触发条件（JSON 格式）
    # 示例：{"event": "cart_abandon", "delay_hours": 2}
    trigger_config = Column(Text, nullable=False)

    # 目标人群
    target_segment_id = Column(String(64), ForeignKey("customer_segments.id"))  # 目标分群 ID

    # 营销内容（JSON 格式）
    # 示例：{"type": "coupon", "template_id": "xxx", "message": "您有商品即将售罄"}
    content_config = Column(Text, nullable=False)

    # 活动状态
    status = Column(String(32), default=AutomationStatus.DRAFT)

    # 活动指标
    triggered_count = Column(Integer, default=0)  # 触发次数
    converted_count = Column(Integer, default=0)  # 转化次数
    total_revenue = Column(Numeric(14, 2), default=0)  # 总营收

    # 活动排期
    start_time = Column(DateTime)
    end_time = Column(DateTime)

    # 状态
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class AutomationTriggerLogEntity(Base):
    """自动化触发日志实体 - 记录每次触发事件"""
    __tablename__ = "automation_trigger_logs"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    automation_id = Column(String(64), ForeignKey("marketing_automations.id"), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)

    # 触发事件
    trigger_event = Column(String(64), nullable=False)  # 触发事件类型
    trigger_data = Column(Text)  # 触发数据（JSON 格式）

    # 营销执行
    executed_at = Column(DateTime, default=datetime.now)  # 执行时间
    execution_status = Column(String(32), default="pending")  # pending/success/failed

    # 转化追踪
    converted = Column(Boolean, default=False)  # 是否转化
    converted_at = Column(DateTime)  # 转化时间
    conversion_type = Column(String(32))  # 转化类型
    conversion_order_id = Column(String(64))  # 转化订单 ID
    conversion_amount = Column(Numeric(14, 2))  # 转化金额

    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_automation_user", "automation_id", "user_id"),
        Index("idx_trigger_event", "trigger_event"),
    )


# ====================  营销 ROI 分析  ====================

class CampaignROIEntity(Base):
    """营销活动 ROI 分析实体"""
    __tablename__ = "campaign_roi"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    campaign_id = Column(String(64), nullable=False, index=True)  # 活动 ID
    campaign_name = Column(String(128), nullable=False)  # 活动名称
    campaign_type = Column(String(64), nullable=False)  # 活动类型

    # 成本分析
    total_cost = Column(Numeric(14, 2), default=0)  # 总成本
    cost_breakdown = Column(Text)  # 成本明细（JSON 格式）

    # 收益分析
    total_revenue = Column(Numeric(14, 2), default=0)  # 总营收
    order_count = Column(Integer, default=0)  # 订单数
    customer_count = Column(Integer, default=0)  # 参与客户数

    # ROI 指标
    roi = Column(Numeric(10, 4), default=0)  # ROI = (收益 - 成本) / 成本
    roas = Column(Numeric(10, 4), default=0)  # ROAS = 收益 / 成本
    cpac = Column(Numeric(10, 2), default=0)  # CPAC = 成本 / 转化数

    # 周期分析
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)

    # 分析状态
    analysis_status = Column(String(32), default="pending")  # pending/running/completed

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CampaignDailyStatsEntity(Base):
    """营销活动每日统计实体"""
    __tablename__ = "campaign_daily_stats"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    campaign_id = Column(String(64), nullable=False, index=True)
    campaign_name = Column(String(128), nullable=False)

    # 统计日期
    stat_date = Column(DateTime, nullable=False, index=True)

    # 曝光指标
    impressions = Column(Integer, default=0)  # 曝光次数
    reach = Column(Integer, default=0)  # 触达人数

    # 互动指标
    clicks = Column(Integer, default=0)  # 点击次数
    click_rate = Column(Numeric(5, 4), default=0)  # 点击率

    # 转化指标
    conversions = Column(Integer, default=0)  # 转化次数
    conversion_rate = Column(Numeric(5, 4), default=0)  # 转化率
    revenue = Column(Numeric(14, 2), default=0)  # 营收

    # 成本指标
    cost = Column(Numeric(14, 2), default=0)  # 成本

    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_campaign_date", "campaign_id", "stat_date", unique=True),
    )


# ====================  A/B 测试框架  ====================

class ABTestEntity(Base):
    """A/B 测试配置实体"""
    __tablename__ = "ab_tests"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    test_name = Column(String(128), nullable=False)  # 测试名称
    description = Column(String(512))  # 测试描述

    # 测试目标
    goal_type = Column(String(32), nullable=False)  # 测试目标类型
    goal_metric = Column(String(64), nullable=False)  # 核心指标

    # 样本配置
    traffic_percentage = Column(Integer, default=100)  # 流量占比 (%)
    sample_size = Column(Integer, default=1000)  # 目标样本量
    min_detectable_effect = Column(Numeric(5, 4), default=0.05)  # 最小可检测效应

    # 变体配置（JSON 格式）
    # 示例：[{"name": "A", "config": {...}}, {"name": "B", "config": {...}}]
    variants_config = Column(Text, nullable=False)

    # 测试状态
    status = Column(String(32), default=ABTestStatus.DRAFT)

    # 测试结果
    winner_variant = Column(String(32))  # 胜出变体
    confidence_level = Column(Numeric(5, 4))  # 置信度
    lift = Column(Numeric(10, 4))  # 提升幅度

    # 测试周期
    start_time = Column(DateTime)
    end_time = Column(DateTime)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ABTestVariantEntity(Base):
    """A/B 测试变体实体"""
    __tablename__ = "ab_test_variants"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    test_id = Column(String(64), ForeignKey("ab_tests.id"), nullable=False, index=True)
    variant_name = Column(String(32), nullable=False)  # 变体名称（A/B/C）

    # 变体配置
    variant_config = Column(Text, nullable=False)  # 变体配置（JSON 格式）

    # 流量分配
    traffic_weight = Column(Integer, default=50)  # 流量权重 (%)

    # 统计结果
    impressions = Column(Integer, default=0)  # 曝光数
    conversions = Column(Integer, default=0)  # 转化数
    revenue = Column(Numeric(14, 2), default=0)  # 营收
    conversion_rate = Column(Numeric(10, 6), default=0)  # 转化率

    # 统计检验
    p_value = Column(Numeric(10, 6))  # P 值
    is_winner = Column(Boolean, default=False)  # 是否胜出

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_test_variant", "test_id", "variant_name", unique=True),
    )


class ABTestUserAssignmentEntity(Base):
    """A/B 测试用户分配实体 - 记录用户被分配到哪个变体"""
    __tablename__ = "ab_test_user_assignments"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    test_id = Column(String(64), ForeignKey("ab_tests.id"), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    variant_name = Column(String(32), nullable=False)  # 分配的变体

    # 用户行为追踪
    exposed_at = Column(DateTime, default=datetime.now)  # 曝光时间
    converted = Column(Boolean, default=False)  # 是否转化
    converted_at = Column(DateTime)  # 转化时间
    conversion_value = Column(Numeric(14, 2))  # 转化价值

    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_test_user", "test_id", "user_id", unique=True),
    )


# ====================  智能优惠券增强  ====================

class SmartCouponStrategyEntity(Base):
    """智能优惠券策略实体 - 千人千券策略配置"""
    __tablename__ = "smart_coupon_strategies"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    strategy_name = Column(String(128), nullable=False)  # 策略名称
    description = Column(String(512))  # 策略描述

    # 目标人群
    target_segment_id = Column(String(64), ForeignKey("customer_segments.id"), index=True)

    # 优惠券配置规则（JSON 格式）
    # 示例：{"type": "discount", "value_range": [0.1, 0.3], "min_purchase": 50}
    coupon_rules = Column(Text, nullable=False)

    # 发放规则
    trigger_event = Column(String(64))  # 触发事件
    max_coupons_per_user = Column(Integer, default=1)  # 每人限领
    daily_limit = Column(Integer, default=1000)  # 每日发放上限

    # 策略效果
    total_issued = Column(Integer, default=0)  # 总发放数
    total_used = Column(Integer, default=0)  # 总使用数
    total_revenue = Column(Numeric(14, 2), default=0)  # 带动营收

    # 状态
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class UserCouponPreferenceEntity(Base):
    """用户优惠券偏好实体 - 记录用户对优惠券的响应偏好"""
    __tablename__ = "user_coupon_preferences"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    user_id = Column(String(64), nullable=False, unique=True, index=True)

    # 优惠券类型偏好
    preferred_coupon_type = Column(String(32))  # fixed/discount
    preferred_discount_range = Column(String(32))  # 偏好折扣区间

    # 响应行为统计
    total_coupons_received = Column(Integer, default=0)  # 收到优惠券数
    total_coupons_used = Column(Integer, default=0)  # 使用优惠券数
    usage_rate = Column(Numeric(5, 4), default=0)  # 使用率

    # 最佳触达
    best_send_time = Column(String(32))  # 最佳发送时间
    best_channel = Column(String(32))  # 最佳触达渠道

    # 价格敏感度
    price_sensitivity = Column(String(32))  # low/medium/high

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class MarketingEventEntity(Base):
    """营销事件实体 - 记录用户营销相关事件"""
    __tablename__ = "marketing_events"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    user_id = Column(String(64), nullable=False, index=True)

    # 事件信息
    event_type = Column(String(64), nullable=False)  # 事件类型
    event_data = Column(Text)  # 事件数据（JSON 格式）

    # 关联信息
    campaign_id = Column(String(64))  # 关联活动 ID
    coupon_id = Column(String(64))  # 关联优惠券 ID
    order_id = Column(String(64))  # 关联订单 ID

    # 事件时间
    event_time = Column(DateTime, default=datetime.now, index=True)

    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_user_event", "user_id", "event_type"),
        Index("idx_event_time", "event_time"),
    )
