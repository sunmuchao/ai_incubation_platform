"""
会员订阅模型

P20 增强：
- 使用次数追踪（每日限制计数）
"""
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import uuid
from enum import Enum


class MembershipTier(str, Enum):
    """会员等级"""
    FREE = "free"  # 免费版
    STANDARD = "standard"  # 标准版 (¥30/月)
    PREMIUM = "premium"  # 高级版 (¥68/月)


class MembershipFeature(str, Enum):
    """会员权益"""
    UNLIMITED_LIKES = "unlimited_likes"  # 无限喜欢
    SEE_WHO_LIKED = "see_who_liked"  # 查看谁喜欢我
    READ_RECEIPT = "read_receipt"  # 消息已读回执
    SUPER_LIKES = "super_likes"  # 超级喜欢
    CHANGE_LOCATION = "change_location"  # 位置修改
    PRIORITY_SHOW = "priority_show"  # 优先推荐
    AI_COMPANION = "ai_companion"  # AI 陪伴助手
    ADVANCED_FILTERS = "advanced_filters"  # 高级筛选
    NO_ADS = "no_ads"  # 无广告
    REWIND = "rewind"  # 回退功能
    BOOST = "boost"  # 加速曝光


# 各等级会员权益配置
MEMBERSHIP_FEATURES = {
    MembershipTier.FREE: [
        # 免费版：每日 8 次喜欢，基础匹配推荐，基础破冰建议
    ],
    MembershipTier.STANDARD: [
        MembershipFeature.UNLIMITED_LIKES,
        MembershipFeature.SEE_WHO_LIKED,
        MembershipFeature.READ_RECEIPT,
        MembershipFeature.ADVANCED_FILTERS,
        MembershipFeature.REWIND,
    ],
    MembershipTier.PREMIUM: [
        MembershipFeature.UNLIMITED_LIKES,
        MembershipFeature.SEE_WHO_LIKED,
        MembershipFeature.READ_RECEIPT,
        MembershipFeature.SUPER_LIKES,
        MembershipFeature.CHANGE_LOCATION,
        MembershipFeature.PRIORITY_SHOW,
        MembershipFeature.AI_COMPANION,
        MembershipFeature.ADVANCED_FILTERS,
        MembershipFeature.REWIND,
        MembershipFeature.BOOST,
        MembershipFeature.NO_ADS,
    ],
}

# 各等级每日限制
MEMBERSHIP_LIMITS = {
    MembershipTier.FREE: {
        "daily_likes": 8,
        "daily_super_likes": 0,
        "daily_rewinds": 0,
        "daily_boosts": 0,
    },
    MembershipTier.STANDARD: {
        "daily_likes": -1,  # -1 表示无限制
        "daily_super_likes": 1,
        "daily_rewinds": 3,
        "daily_boosts": 0,
    },
    MembershipTier.PREMIUM: {
        "daily_likes": -1,
        "daily_super_likes": 5,
        "daily_rewinds": -1,
        "daily_boosts": 1,
    },
}

# 会员价格配置 (人民币)
MEMBERSHIP_PRICES = {
    MembershipTier.STANDARD: {
        "monthly": 30,
        "quarterly": 78,  # 相当于 26/月
        "yearly": 288,  # 相当于 24/月
    },
    MembershipTier.PREMIUM: {
        "monthly": 68,
        "quarterly": 178,  # 相当于 59/月
        "yearly": 688,  # 相当于 57/月
    },
}


class MembershipPlan(BaseModel):
    """会员订阅计划"""
    id: str = str(uuid.uuid4())
    tier: MembershipTier
    duration_months: int  # 订阅时长 (月)
    price: float  # 价格 (元)
    original_price: float  # 原价
    discount_rate: float = 0.0  # 折扣率
    features: List[MembershipFeature] = []
    is_active: bool = True
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()


class UserMembership(BaseModel):
    """用户会员状态"""
    id: str = str(uuid.uuid4())
    user_id: str
    tier: MembershipTier = MembershipTier.FREE
    status: str = "inactive"  # inactive, active, expired, cancelled
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    auto_renew: bool = False
    payment_method: Optional[str] = None  # wechat, alipay, apple_pay
    subscription_id: Optional[str] = None  # 第三方订阅 ID
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    def is_active(self) -> bool:
        """检查会员是否有效"""
        if self.status != "active":
            return False
        if self.end_date and datetime.now() > self.end_date:
            return False
        return True

    def has_feature(self, feature: MembershipFeature) -> bool:
        """检查是否有某个会员权益"""
        if not self.is_active():
            return False
        tier_features = MEMBERSHIP_FEATURES.get(self.tier, [])
        return feature in tier_features

    def get_limit(self, limit_type: str) -> int:
        """获取某个限制的值 (-1 表示无限制)"""
        if not self.is_active():
            return MEMBERSHIP_LIMITS[MembershipTier.FREE].get(limit_type, 0)
        return MEMBERSHIP_LIMITS.get(self.tier, {}).get(limit_type, 0)


class MembershipOrder(BaseModel):
    """会员订单"""
    id: str = str(uuid.uuid4())
    user_id: str
    tier: MembershipTier
    duration_months: int
    amount: float  # 实付金额
    original_amount: float  # 原价
    discount_code: Optional[str] = None
    status: str = "pending"  # pending, paid, failed, refunded
    payment_method: Optional[str] = None
    payment_time: Optional[datetime] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()


class MembershipCreate(BaseModel):
    """创建会员订阅请求"""
    tier: MembershipTier
    duration_months: int = 1
    payment_method: str = "wechat"
    auto_renew: bool = False


class MembershipBenefit(BaseModel):
    """会员权益说明"""
    feature: MembershipFeature
    name: str
    description: str
    icon: str


# 会员权益详细说明
MEMBERSHIP_BENEFITS: List[MembershipBenefit] = [
    MembershipBenefit(
        feature=MembershipFeature.UNLIMITED_LIKES,
        name="无限喜欢",
        description="不再受每日喜欢次数限制，遇到更多心仪的人",
        icon="♥"
    ),
    MembershipBenefit(
        feature=MembershipFeature.SEE_WHO_LIKED,
        name="查看喜欢我的人",
        description="第一时间看到谁喜欢了你，不错过任何缘分",
        icon="👀"
    ),
    MembershipBenefit(
        feature=MembershipFeature.READ_RECEIPT,
        name="消息已读回执",
        description="知道对方是否已读你的消息，不再盲目等待",
        icon="✓"
    ),
    MembershipBenefit(
        feature=MembershipFeature.SUPER_LIKES,
        name="超级喜欢",
        description="每月 5 次超级喜欢，让 TA 优先看到你的心意",
        icon="★"
    ),
    MembershipBenefit(
        feature=MembershipFeature.CHANGE_LOCATION,
        name="位置修改",
        description="修改所在位置，探索更多城市的人",
        icon="📍"
    ),
    MembershipBenefit(
        feature=MembershipFeature.PRIORITY_SHOW,
        name="优先推荐",
        description="你的资料会被更多人看到",
        icon="⚡"
    ),
    MembershipBenefit(
        feature=MembershipFeature.AI_COMPANION,
        name="AI 陪伴助手",
        description="专属 AI 情感顾问，随时解答恋爱困惑",
        icon="🤖"
    ),
    MembershipBenefit(
        feature=MembershipFeature.REWIND,
        name="回退功能",
        description="手滑了？可以回退到上一个人",
        icon="↩"
    ),
    MembershipBenefit(
        feature=MembershipFeature.BOOST,
        name="加速曝光",
        description="每日 1 次加速，30 分钟内获得更多曝光",
        icon="🚀"
    ),
    MembershipBenefit(
        feature=MembershipFeature.ADVANCED_FILTERS,
        name="高级筛选",
        description="更精细的筛选条件，精准找到理想型",
        icon="🔍"
    ),
]


class MembershipStats(BaseModel):
    """会员统计信息"""
    total_members: int
    free_members: int
    standard_members: int
    premium_members: int
    new_members_this_month: int
    expired_members_this_month: int
    revenue_this_month: float
    revenue_this_year: float


# ============================================
# SQLAlchemy 模型定义（用于数据库持久化）
# ============================================
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from db.database import Base


class UserUsageTrackerDB(Base):
    """用户使用次数追踪器

    用于记录用户每日使用会员功能的次数，实现会员限制计数。
    """
    __tablename__ = "user_usage_trackers"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 日期（用于每日重置）
    usage_date = Column(String(10), nullable=False, index=True)  # 格式：YYYY-MM-DD

    # 各功能使用次数
    like_count = Column(Integer, default=0)  # 喜欢次数
    super_like_count = Column(Integer, default=0)  # 超级喜欢次数
    rewind_count = Column(Integer, default=0)  # 回退次数
    boost_count = Column(Integer, default=0)  # 加速曝光次数

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
