"""
P7 阶段 - 游戏化运营和砍价玩法数据库实体模型

包含:
1. 成就系统 (Achievement System)
2. 排行榜 (Leaderboard)
3. 砍价玩法 (Bargain System)
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Enum, Boolean, Index, Float, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
from decimal import Decimal
import enum

from config.database import Base


# ====================  Enums  ====================

class AchievementType(enum.Enum):
    """成就类型"""
    ORDER = "order"              # 订单相关
    PURCHASE = "purchase"        # 消费相关
    SHARE = "share"              # 分享相关
    SIGNIN = "signin"            # 签到相关
    SOCIAL = "social"            # 社交相关
    SPECIAL = "special"          # 特殊成就


class AchievementTier(enum.Enum):
    """成就等级"""
    BRONZE = "bronze"      # 铜牌
    SILVER = "silver"      # 银牌
    GOLD = "gold"          # 金牌
    PLATINUM = "platinum"  # 铂金
    DIAMOND = "diamond"    # 钻石


class AchievementStatus(enum.Enum):
    """成就状态"""
    LOCKED = "locked"        # 未解锁
    IN_PROGRESS = "in_progress"  # 进行中
    UNLOCKED = "unlocked"    # 已解锁
    CLAIMED = "claimed"      # 已领取奖励


class LeaderboardType(enum.Enum):
    """排行榜类型"""
    ORDER_COUNT = "order_count"      # 订单榜
    PURCHASE_AMOUNT = "purchase_amount"  # 消费榜
    POINTS = "points"          # 积分榜
    SHARE_COUNT = "share_count"    # 分享榜
    ORGANIZER_GMV = "organizer_gmv"  # 团长 GMV 榜
    ORGANIZER_ORDER = "organizer_order"  # 团长订单榜


class LeaderboardPeriod(enum.Enum):
    """排行榜周期"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ALL_TIME = "all_time"


class BargainStatus(enum.Enum):
    """砍价状态"""
    IN_PROGRESS = "in_progress"  # 砍价中
    SUCCESS = "success"        # 砍价成功
    FAILED = "failed"          # 砍价失败
    EXPIRED = "expired"        # 已过期
    CANCELLED = "cancelled"    # 已取消


# ====================  成就系统  ====================

class AchievementDefinitionEntity(Base):
    """成就定义实体 - 定义成就的元数据"""
    __tablename__ = "achievement_definitions"

    id = Column(String(64), primary_key=True)
    achievement_code = Column(String(64), nullable=False, unique=True)  # 成就代码 如 FIRST_ORDER
    achievement_name = Column(String(128), nullable=False)  # 成就名称
    achievement_type = Column(Enum(AchievementType), nullable=False)
    tier = Column(Enum(AchievementTier), default=AchievementTier.BRONZE)

    # 达成条件
    condition_type = Column(String(32), nullable=False)  # count/amount/reach
    condition_target = Column(Integer, nullable=False)  # 目标值
    condition_description = Column(String(256))  # 条件描述

    # 奖励
    reward_type = Column(String(32))  # points/coupon/badge
    reward_value = Column(Integer)  # 奖励值 (积分数量/优惠券 ID 等)
    reward_description = Column(String(256))

    # 展示
    icon_url = Column(String(256))
    description = Column(Text)
    sort_order = Column(Integer, default=0)

    # 状态
    is_active = Column(Boolean, default=True)
    is_hidden = Column(Boolean, default=False)  # 是否隐藏成就

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_type_tier", "achievement_type", "tier"),
    )


class UserAchievementEntity(Base):
    """用户成就实体 - 记录用户成就进度"""
    __tablename__ = "user_achievements"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    achievement_id = Column(String(64), nullable=False)  # 关联成就定义 ID

    # 进度
    current_progress = Column(Integer, default=0)  # 当前进度
    target_progress = Column(Integer, nullable=False)  # 目标进度

    # 状态
    status = Column(Enum(AchievementStatus), default=AchievementStatus.LOCKED)

    # 时间
    unlocked_at = Column(DateTime)  # 解锁时间
    claimed_at = Column(DateTime)  # 奖励领取时间

    # 元数据
    progress_data = Column(Text)  # 进度详情 (JSON)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_user_achievement", "user_id", "achievement_id", unique=True),
        Index("idx_user_status", "user_id", "status"),
    )


class AchievementBadgeEntity(Base):
    """成就徽章实体 - 用户获得的徽章"""
    __tablename__ = "achievement_badges"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    achievement_id = Column(String(64), nullable=False)

    # 徽章信息
    badge_name = Column(String(128), nullable=False)
    badge_icon = Column(String(256))
    tier = Column(Enum(AchievementTier), default=AchievementTier.BRONZE)

    # 展示
    is_equipped = Column(Boolean, default=False)  # 是否装备 (展示)
    equipped_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_user_equipped", "user_id", "is_equipped"),
    )


# ====================  排行榜  ====================

class LeaderboardEntity(Base):
    """排行榜实体 - 记录排行榜数据"""
    __tablename__ = "leaderboards"

    id = Column(String(64), primary_key=True)
    leaderboard_type = Column(Enum(LeaderboardType), nullable=False)
    period = Column(Enum(LeaderboardPeriod), nullable=False)
    period_key = Column(String(32), nullable=False)  # 周期标识 如 2026-W01/2026-04

    # 排名信息
    user_id = Column(String(64), nullable=False, index=True)
    rank = Column(Integer, nullable=False, index=True)  # 排名
    score = Column(Numeric(15, 2), nullable=False)  # 分数/值

    # 附加信息
    extra_data = Column(Text)  # 额外数据 (JSON)

    # 时间
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_type_period_rank", "leaderboard_type", "period", "period_key", "rank"),
        Index("idx_user_type_period", "user_id", "leaderboard_type", "period"),
    )


class LeaderboardHistoryEntity(Base):
    """排行榜历史实体 - 记录历史排名快照"""
    __tablename__ = "leaderboard_history"

    id = Column(String(64), primary_key=True)
    leaderboard_id = Column(String(64), nullable=False, index=True)
    snapshot_date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD

    user_id = Column(String(64), nullable=False)
    rank = Column(Integer, nullable=False)
    score = Column(Numeric(15, 2), nullable=False)

    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_leaderboard_snapshot", "leaderboard_id", "snapshot_date"),
    )


# ====================  砍价玩法  ====================

class BargainActivityEntity(Base):
    """砍价活动实体 - 定义砍价活动规则"""
    __tablename__ = "bargain_activities"

    id = Column(String(64), primary_key=True)
    activity_name = Column(String(128), nullable=False)
    product_id = Column(String(64), nullable=False)  # 参与砍价的商品 ID

    # 价格信息
    original_price = Column(Numeric(12, 2), nullable=False)  # 原价
    floor_price = Column(Numeric(12, 2), nullable=False)  # 底价 (最低可砍到的价格)
    initial_price = Column(Numeric(12, 2), nullable=False)  # 初始砍价 (通常等于原价)

    # 规则
    min_bargain_amount = Column(Numeric(10, 2), default=0.1)  # 单次最低砍价金额
    max_bargain_amount = Column(Numeric(10, 2), default=50.0)  # 单次最高砍价金额
    max_bargain_count = Column(Integer, default=10)  # 最多砍价次数
    required_bargain_count = Column(Integer, default=5)  # 达成底价所需次数 (用于计算期望)

    # 时间
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    duration_hours = Column(Integer, default=24)  # 活动持续时间 (小时)

    # 库存
    total_stock = Column(Integer, default=0)  # 活动总库存
    used_stock = Column(Integer, default=0)  # 已使用库存

    # 状态
    is_active = Column(Boolean, default=True)
    status = Column(String(32), default="upcoming")  # upcoming/ongoing/ended

    # 描述
    description = Column(Text)
    image_url = Column(String(256))

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_product_status", "product_id", "is_active"),
        Index("idx_time_status", "start_time", "end_time", "status"),
    )


class BargainOrderEntity(Base):
    """砍价订单实体 - 用户发起的砍价"""
    __tablename__ = "bargain_orders"

    id = Column(String(64), primary_key=True)
    bargain_no = Column(String(32), nullable=False, unique=True, index=True)  # 砍价单号
    activity_id = Column(String(64), nullable=False, index=True)  # 关联活动 ID
    product_id = Column(String(64), nullable=False)
    user_id = Column(String(64), nullable=False, index=True)  # 发起人

    # 价格信息
    original_price = Column(Numeric(12, 2), nullable=False)
    current_price = Column(Numeric(12, 2), nullable=False)  # 当前价格
    floor_price = Column(Numeric(12, 2), nullable=False)  # 底价

    # 进度
    bargain_count = Column(Integer, default=0)  # 已砍次数
    max_bargain_count = Column(Integer, default=10)  # 最多砍价次数
    remaining_bargains = Column(Integer, default=10)  # 剩余可砍次数

    # 状态
    status = Column(Enum(BargainStatus), default=BargainStatus.IN_PROGRESS)

    # 时间
    started_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime, nullable=False)  # 过期时间
    completed_at = Column(DateTime)  # 完成时间

    # 成单信息
    order_id = Column(String(64))  # 最终生成的订单 ID
    ordered_at = Column(DateTime)  # 成单时间

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_bargain_user_status", "user_id", "status"),
        Index("idx_bargain_activity_status", "activity_id", "status"),
    )


class BargainHelpEntity(Base):
    """砍价助力实体 - 记录帮砍记录"""
    __tablename__ = "bargain_helps"

    id = Column(String(64), primary_key=True)
    bargain_order_id = Column(String(64), nullable=False, index=True)  # 砍价订单 ID
    helper_user_id = Column(String(64), nullable=False)  # 助力者用户 ID

    # 砍价金额
    bargain_amount = Column(Numeric(10, 2), nullable=False)  # 砍掉的金额
    price_before = Column(Numeric(12, 2), nullable=False)  # 砍前价格
    price_after = Column(Numeric(12, 2), nullable=False)  # 砍后价格

    # 助力者类型
    is_new_user = Column(Boolean, default=False)  # 是否新用户 (新用户砍的更多)

    # 备注
    remark = Column(String(256))

    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_order_helper", "bargain_order_id", "helper_user_id", unique=True),
        Index("idx_helper_time", "helper_user_id", "created_at"),
    )
