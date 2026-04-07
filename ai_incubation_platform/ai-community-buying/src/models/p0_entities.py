"""
P0 优先级功能数据库实体模型

包含：
1. 限时秒杀功能 (任务#13)
2. 新人专享体系 (任务#14)
3. 拼单返现机制 (任务#30)
4. 库存紧张提示 (任务#56)
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Enum, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from config.database import Base


def generate_uuid():
    return str(uuid.uuid4())


# ========== 任务#13: 限时秒杀功能实体 ==========

class FlashSaleStatus:
    """秒杀活动状态枚举"""
    UPCOMING = "upcoming"      # 即将开始
    ONGOING = "ongoing"        # 进行中
    ENDED = "ended"           # 已结束
    EXPIRED = "expired"       # 已过期


class FlashSaleEntity(Base):
    """限时秒杀活动数据库实体"""
    __tablename__ = "flash_sales"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)  # 商品 ID
    title = Column(String, nullable=False)  # 秒杀活动标题
    flash_price = Column(Float, nullable=False)  # 秒杀价格
    flash_stock = Column(Integer, nullable=False, default=0)  # 秒杀库存
    total_stock = Column(Integer, nullable=False, default=0)  # 秒杀总库存
    min_group_size = Column(Integer, default=1)  # 最小成团人数
    max_group_size = Column(Integer, default=10)  # 最大成团人数
    start_time = Column(DateTime, nullable=False)  # 开始时间
    end_time = Column(DateTime, nullable=False)  # 结束时间
    status = Column(String, default="upcoming")  # upcoming/ongoing/ended/expired
    per_user_limit = Column(Integer, default=1)  # 每人限购数量
    purchased_count = Column(Integer, default=0)  # 已购买数量
    view_count = Column(Integer, default=0)  # 浏览人数
    created_by = Column(String, nullable=False)  # 创建人（团长 ID）
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    orders = relationship("FlashSaleOrderEntity", back_populates="flash_sale", cascade="all, delete-orphan")


class FlashSaleOrderEntity(Base):
    """秒杀订单数据库实体"""
    __tablename__ = "flash_sale_orders"

    id = Column(String, primary_key=True, default=generate_uuid)
    flash_sale_id = Column(String, ForeignKey("flash_sales.id"), nullable=False)  # 秒杀活动 ID
    user_id = Column(String, nullable=False, index=True)  # 用户 ID
    product_id = Column(String, ForeignKey("products.id"), nullable=False)  # 商品 ID
    quantity = Column(Integer, default=1, nullable=False)  # 购买数量
    unit_price = Column(Float, nullable=False)  # 秒杀单价
    total_amount = Column(Float, nullable=False)  # 订单总额
    status = Column(String, default="pending")  # pending/paid/shipped/completed/cancelled
    payment_time = Column(DateTime)  # 支付时间
    order_number = Column(String, unique=True, index=True)  # 订单号
    device_fingerprint = Column(String)  # 设备指纹（防刷）
    ip_address = Column(String)  # IP 地址（防刷）
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    flash_sale = relationship("FlashSaleEntity", back_populates="orders")


# ========== 任务#14: 新人专享体系实体 ==========

class NewbieStatus:
    """新人状态枚举"""
    ELIGIBLE = "eligible"          # 符合新人资格
    CLAIMED = "claimed"            # 已领取权益
    FIRST_ORDER = "first_order"    # 已完成首单
    EXPIRED = "expired"            # 新人权益已过期


class NewbieProfileEntity(Base):
    """新人档案数据库实体"""
    __tablename__ = "newbie_profiles"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, nullable=False, unique=True, index=True)  # 用户 ID
    status = Column(String, default="eligible")  # eligible/claimed/first_order/expired
    registered_at = Column(DateTime, nullable=False)  # 注册时间
    first_order_at = Column(DateTime)  # 首单时间
    coupon_claimed_at = Column(DateTime)  # 券包领取时间
    benefits_claimed = Column(Boolean, default=False)  # 是否已领取权益
    newbie_products_viewed = Column(Integer, default=0)  # 浏览新人专享商品次数
    tasks_completed = Column(String, default="[]")  # 已完成任务列表（JSON）
    expires_at = Column(DateTime)  # 新人权益过期时间
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class NewbieProductEntity(Base):
    """新人专享商品数据库实体"""
    __tablename__ = "newbie_products"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, unique=True)  # 商品 ID
    newbie_price = Column(Float, nullable=False)  # 新人专享价
    original_price = Column(Float, nullable=False)  # 原价
    stock_limit = Column(Integer, default=100)  # 新人专享库存
    purchased_count = Column(Integer, default=0)  # 已购买数量
    per_user_limit = Column(Integer, default=1)  # 每人限购
    is_active = Column(Boolean, default=True)  # 是否启用
    start_time = Column(DateTime)  # 活动开始时间
    end_time = Column(DateTime)  # 活动结束时间
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class NewbieCouponTemplateEntity(Base):
    """新人券包模板数据库实体"""
    __tablename__ = "newbie_coupon_templates"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)  # 券包名称，如"新人 100 元券包"
    description = Column(String)  # 券包描述
    coupon_config = Column(Text, nullable=False)  # 券包配置（JSON 字符串，包含多张优惠券信息）
    total_quantity = Column(Integer, default=10000)  # 总发放量
    claimed_quantity = Column(Integer, default=0)  # 已领取数量
    is_active = Column(Boolean, default=True)  # 是否启用
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class NewbieTaskEntity(Base):
    """新人任务数据库实体"""
    __tablename__ = "newbie_tasks"

    id = Column(String, primary_key=True, default=generate_uuid)
    task_name = Column(String, nullable=False)  # 任务名称，如"完成首单"
    task_type = Column(String, nullable=False)  # register/first_order/share/perfect_info
    description = Column(String)  # 任务描述
    reward_type = Column(String, nullable=False)  # coupon/point/cash
    reward_value = Column(Float, nullable=False)  # 奖励额度
    reward_desc = Column(String)  # 奖励描述，如"满 10 减 5 优惠券"
    sort_order = Column(Integer, default=0)  # 排序顺序
    is_active = Column(Boolean, default=True)  # 是否启用
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class NewbieTaskProgressEntity(Base):
    """新人任务进度数据库实体"""
    __tablename__ = "newbie_task_progress"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, nullable=False, index=True)  # 用户 ID
    task_id = Column(String, ForeignKey("newbie_tasks.id"), nullable=False)  # 任务 ID
    status = Column(String, default="in_progress")  # in_progress/completed/claimed
    progress = Column(Integer, default=0)  # 当前进度
    target = Column(Integer, default=1)  # 目标进度
    reward_claimed = Column(Boolean, default=False)  # 奖励是否已领取
    claimed_at = Column(DateTime)  # 领取时间
    completed_at = Column(DateTime)  # 完成时间
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ========== 任务#30: 拼单返现机制实体 ==========

class GroupBuyCashbackStatus:
    """拼单返现状态枚举"""
    ACTIVE = "active"           # 进行中
    COMPLETED = "completed"     # 已完成（达成目标人数）
    EXPIRED = "expired"         # 已过期（未达成目标）


class GroupBuyCashbackEntity(Base):
    """拼单返现活动数据库实体"""
    __tablename__ = "group_buy_cashbacks"

    id = Column(String, primary_key=True, default=generate_uuid)
    creator_user_id = Column(String, nullable=False, index=True)  # 创建人用户 ID
    groupbuy_id = Column(String, ForeignKey("group_buys.id"), nullable=False)  # 关联团购 ID
    product_id = Column(String, ForeignKey("products.id"), nullable=False)  # 商品 ID
    target_participants = Column(Integer, nullable=False, default=3)  # 目标参团人数
    cashback_percentage = Column(Float, nullable=False, default=0.2)  # 返现比例 (0-1)，如 0.2=20%
    max_cashback_amount = Column(Float)  # 最高返现金额上限（可选）
    current_participants = Column(Integer, default=1)  # 当前参团人数
    status = Column(String, default="active")  # active/completed/expired
    deadline = Column(DateTime, nullable=False)  # 拼单截止时间
    cashback_total = Column(Float, default=0.0)  # 返现总额
    cashback_per_person = Column(Float, default=0.0)  # 人均返现金额
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    participants = relationship("GroupBuyCashbackParticipantEntity", back_populates="cashback", cascade="all, delete-orphan")
    cashback_records = relationship("GroupBuyCashbackRecordEntity", back_populates="cashback", cascade="all, delete-orphan")


class GroupBuyCashbackParticipantEntity(Base):
    """拼单返现参与者数据库实体"""
    __tablename__ = "group_buy_cashback_participants"

    id = Column(String, primary_key=True, default=generate_uuid)
    cashback_id = Column(String, ForeignKey("group_buy_cashbacks.id"), nullable=False)  # 拼单返现 ID
    user_id = Column(String, nullable=False, index=True)  # 用户 ID
    order_id = Column(String)  # 关联订单 ID
    join_time = Column(DateTime, default=datetime.now)  # 参团时间
    payment_amount = Column(Float, default=0.0)  # 支付金额
    cashback_amount = Column(Float, default=0.0)  # 返现金额
    cashback_status = Column(String, default="pending")  # pending/granted/withdrawn
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    cashback = relationship("GroupBuyCashbackEntity", back_populates="participants")


class GroupBuyCashbackRecordEntity(Base):
    """拼单返现记录数据库实体"""
    __tablename__ = "group_buy_cashback_records"

    id = Column(String, primary_key=True, default=generate_uuid)
    cashback_id = Column(String, ForeignKey("group_buy_cashbacks.id"), nullable=False)  # 拼单返现 ID
    participant_id = Column(String, ForeignKey("group_buy_cashback_participants.id"), nullable=False)  # 参与者 ID
    user_id = Column(String, nullable=False, index=True)  # 用户 ID
    cashback_amount = Column(Float, nullable=False)  # 返现金额
    status = Column(String, default="pending")  # pending/granted/withdrawn
    granted_at = Column(DateTime)  # 发放时间
    withdrawn_at = Column(DateTime)  # 提现时间
    notes = Column(String)  # 备注
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    cashback = relationship("GroupBuyCashbackEntity", back_populates="cashback_records")


# ========== 任务#56: 库存紧张提示实体 ==========

class ProductViewTrackerEntity(Base):
    """商品浏览追踪数据库实体"""
    __tablename__ = "product_view_trackers"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)  # 商品 ID
    user_id = Column(String, index=True)  # 用户 ID（可选，匿名浏览可为空）
    session_id = Column(String, nullable=False, index=True)  # 会话 ID
    view_time = Column(DateTime, default=datetime.now)  # 浏览时间
    ip_address = Column(String)  # IP 地址
    device_type = Column(String)  # 设备类型（mobile/desktop）
    dwell_time = Column(Integer, default=0)  # 停留时长（秒）
    created_at = Column(DateTime, default=datetime.now)


class StockAlertConfigEntity(Base):
    """库存警报配置数据库实体"""
    __tablename__ = "stock_alert_configs"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, unique=True)  # 商品 ID
    alert_threshold = Column(Integer, default=10)  # 库存警报阈值
    urgent_threshold = Column(Integer, default=5)  # 库存紧急阈值
    is_active = Column(Boolean, default=True)  # 是否启用
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ProductHeatmapEntity(Base):
    """商品热度数据库实体（用于"X 人在看"）"""
    __tablename__ = "product_heatmaps"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, unique=True, index=True)  # 商品 ID
    current_viewers = Column(Integer, default=0)  # 当前浏览人数
    peak_viewers = Column(Integer, default=0)  #  peak 浏览人数
    total_views_today = Column(Integer, default=0)  # 今日总浏览量
    total_views_week = Column(Integer, default=0)  # 本周总浏览量
    total_views_month = Column(Integer, default=0)  # 本月总浏览量
    wishlist_count = Column(Integer, default=0)  # 收藏人数
    share_count = Column(Integer, default=0)  # 分享次数
    heat_score = Column(Float, default=0.0)  # 热度分数（综合计算）
    last_updated = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ========== P0 AI 智能成团预测实体 ==========

class GroupPredictionEntity(Base):
    """智能成团预测记录数据库实体"""
    __tablename__ = "group_predictions"

    id = Column(String, primary_key=True, default=generate_uuid)
    group_buy_id = Column(String, ForeignKey("group_buys.id"), nullable=False, unique=True, index=True)  # 团购 ID
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)  # 商品 ID
    organizer_id = Column(String, nullable=False, index=True)  # 团长 ID

    # 预测结果
    success_probability = Column(Float, nullable=False)  # 成团概率 (0-1)
    predicted_final_size = Column(Integer)  # 预测最终参团人数
    confidence_level = Column(String, default="medium")  # 置信度等级：low/medium/high

    # 特征数据（JSON 字符串）
    features = Column(Text)  # 特征快照，用于追溯和模型优化

    # 预测结果分类
    prediction_category = Column(String, default="pending")  # pending/highly_likely/likely/uncertain/unlikely

    # 模型元数据
    model_version = Column(String, default="v1.0")  # 模型版本
    prediction_time = Column(DateTime, nullable=False)  # 预测时间

    # 实际结果（成团后回填）
    actual_result = Column(String)  # success/failed/expired/cancelled
    actual_final_size = Column(Integer)  # 实际最终人数
    accuracy = Column(Float)  # 预测准确率

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class PredictionFeatureEntity(Base):
    """预测特征历史数据库实体（用于模型训练）"""
    __tablename__ = "prediction_features"

    id = Column(String, primary_key=True, default=generate_uuid)

    # 团购基本信息
    group_buy_id = Column(String, ForeignKey("group_buys.id"), nullable=False, index=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    organizer_id = Column(String, nullable=False, index=True)

    # 进度特征
    progress_ratio = Column(Float)  # 当前进度 (current/target)
    current_size = Column(Integer)  # 当前人数
    target_size = Column(Integer)  # 目标人数

    # 时间特征
    time_remaining_hours = Column(Float)  # 剩余时间（小时）
    time_elapsed_hours = Column(Float)  # 已过去时间（小时）
    deadline_hour_of_day = Column(Integer)  # 截止时刻是几点

    # 历史特征
    organizer_historical_success_rate = Column(Float)  # 团长历史成团率
    product_historical_success_rate = Column(Float)  # 商品历史成团率
    organizer_total_groups = Column(Integer)  # 团长历史开团总数

    # 热度特征
    product_view_count = Column(Integer)  # 商品浏览人数
    product_wishlist_count = Column(Integer)  # 商品收藏人数
    hourly_join_rate = Column(Float)  # 当前每小时加入率

    # 社区/环境特征
    day_of_week = Column(Integer)  # 星期几 (0-6)
    hour_of_day = Column(Integer)  # 当前时刻 (0-23)
    is_weekend = Column(Boolean)  # 是否周末
    is_holiday_season = Column(Boolean)  # 是否节假日

    # 预测结果
    actual_success = Column(Boolean)  # 是否成团成功
    actual_final_size = Column(Integer)  # 实际最终人数

    created_at = Column(DateTime, default=datetime.now)
