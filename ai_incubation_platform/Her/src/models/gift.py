"""
虚拟礼物模型

参考 Soul/探探的礼物系统：
- 多种礼物类型（表情、动画、实物）
- 礼物价格分层（免费、小额、大额）
- 礼物打赏记录
- 礼物收入统计
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid


class GiftType(str, Enum):
    """礼物类型"""
    FREE = "free"  # 免费礼物
    BASIC = "basic"  # 基础礼物（1-5 元）
    STANDARD = "standard"  # 标准礼物（5-20 元）
    PREMIUM = "premium"  # 高级礼物（20-50 元）
    SPECIAL = "special"  # 特殊礼物（50+ 元）
    ANIMATED = "animated"  # 动画礼物
    PHYSICAL = "physical"  # 实物礼物（配送）


class GiftCategory(str, Enum):
    """礼物分类"""
    LOVE = "love"  # 爱情/浪漫
    BIRTHDAY = "birthday"  # 生日/庆祝
    FUNNY = "funny"  # 搞怪/趣味
    FOOD = "food"  # 餐饮/美食
    FLOWER = "flower"  # 花卉/植物
    ANIMAL = "animal"  # 动物/宠物
    TRAVEL = "travel"  # 旅游/出行
    FESTIVAL = "festival"  # 节日/庆典


# 礼物配置（参考 Soul 的礼物商店）
GIFT_CONFIG = {
    # 免费礼物
    "free_heart": {
        "name": "小心心",
        "type": GiftType.FREE,
        "category": GiftCategory.LOVE,
        "price": 0,
        "icon": "❤️",
        "animation": None,
        "description": "表达喜欢",
    },
    "free_smile": {
        "name": "微笑",
        "type": GiftType.FREE,
        "category": GiftCategory.LOVE,
        "price": 0,
        "icon": "😊",
        "animation": None,
        "description": "友好问候",
    },
    "free_star": {
        "name": "星星",
        "type": GiftType.FREE,
        "category": GiftCategory.LOVE,
        "price": 0,
        "icon": "⭐",
        "animation": None,
        "description": "闪耀的你",
    },

    # 基础礼物（1-5 元）
    "rose_single": {
        "name": "一朵玫瑰",
        "type": GiftType.BASIC,
        "category": GiftCategory.LOVE,
        "price": 1,
        "icon": "🌹",
        "animation": "rose_bloom",
        "description": "浪漫开始",
    },
    "coffee": {
        "name": "咖啡",
        "type": GiftType.BASIC,
        "category": GiftCategory.FOOD,
        "price": 3,
        "icon": "☕",
        "animation": None,
        "description": "请TA喝杯咖啡",
    },
    "cake_slice": {
        "name": "小蛋糕",
        "type": GiftType.BASIC,
        "category": GiftCategory.FOOD,
        "price": 5,
        "icon": "🍰",
        "animation": "cake_spin",
        "description": "甜蜜时刻",
    },

    # 标准礼物（5-20 元）
    "rose_bouquet": {
        "name": "玫瑰花束",
        "type": GiftType.STANDARD,
        "category": GiftCategory.LOVE,
        "price": 15,
        "icon": "💐",
        "animation": "bouquet_show",
        "description": "浪漫告白",
    },
    "chocolate": {
        "name": "巧克力礼盒",
        "type": GiftType.STANDARD,
        "category": GiftCategory.LOVE,
        "price": 18,
        "icon": "🍫",
        "animation": "box_open",
        "description": "甜蜜心意",
    },
    "teddy_bear": {
        "name": "泰迪熊",
        "type": GiftType.STANDARD,
        "category": GiftCategory.ANIMAL,
        "price": 20,
        "icon": "🧸",
        "animation": "bear_wave",
        "description": "可爱的陪伴",
    },

    # 高级礼物（20-50 元）
    "rose_99": {
        "name": "99朵玫瑰",
        "type": GiftType.PREMIUM,
        "category": GiftCategory.LOVE,
        "price": 30,
        "icon": "🌹",
        "animation": "rose_99_animation",
        "description": "长长久久",
    },
    "diamond_ring": {
        "name": "钻戒",
        "type": GiftType.PREMIUM,
        "category": GiftCategory.LOVE,
        "price": 50,
        "icon": "💍",
        "animation": "ring_shine",
        "description": "永恒承诺",
    },

    # 特殊礼物
    "firework": {
        "name": "烟花",
        "type": GiftType.SPECIAL,
        "category": GiftCategory.FESTIVAL,
        "price": 68,
        "icon": "🎆",
        "animation": "firework_fullscreen",
        "description": "璀璨夜空",
        "fullscreen": True,
    },
    "love_balloon": {
        "name": "爱心气球",
        "type": GiftType.SPECIAL,
        "category": GiftCategory.LOVE,
        "price": 88,
        "icon": "🎈",
        "animation": "balloon_float_fullscreen",
        "description": "爱的告白",
        "fullscreen": True,
    },
}


class Gift(BaseModel):
    """礼物"""
    id: str
    name: str
    type: GiftType
    category: GiftCategory
    price: float
    icon: str
    animation: Optional[str] = None
    description: str
    fullscreen: bool = False
    is_popular: bool = False
    is_new: bool = False


class GiftSendRequest(BaseModel):
    """发送礼物请求"""
    target_user_id: str
    gift_id: str
    count: int = 1  # 礼物数量
    message: Optional[str] = None  # 附带消息


class GiftSendResponse(BaseModel):
    """发送礼物响应"""
    success: bool
    message: str
    gift_id: str
    gift_name: str
    total_price: float
    transaction_id: Optional[str] = None


class GiftTransaction(BaseModel):
    """礼物交易记录"""
    id: str = str(uuid.uuid4())
    sender_id: str
    receiver_id: str
    gift_id: str
    gift_name: str
    gift_icon: str
    gift_type: GiftType
    count: int = 1
    price: float
    total_amount: float
    message: Optional[str] = None
    sent_at: datetime = datetime.now()
    is_seen: bool = False
    seen_at: Optional[datetime] = None


class GiftStoreResponse(BaseModel):
    """礼物商店响应"""
    categories: List[dict]
    gifts: List[Gift]
    popular_gifts: List[Gift]
    new_gifts: List[Gift]


class UserGiftStats(BaseModel):
    """用户礼物统计"""
    user_id: str
    total_received: int  # 收到的礼物总数
    total_received_amount: float  # 收到的礼物总价值
    total_sent: int  # 发送的礼物总数
    total_sent_amount: float  # 发送的礼物总价值
    most_received_gift: Optional[str]  # 收到最多的礼物
    most_sent_gift: Optional[str]  # 发送最多的礼物
    top_sender: Optional[str]  # 送礼物最多的人
    top_receiver: Optional[str]  # 收礼物最多的人


# ============================================
# SQLAlchemy 模型定义
# ============================================
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, Float, Text
from sqlalchemy.sql import func
from db.database import Base


class GiftTransactionDB(Base):
    """礼物交易记录"""
    __tablename__ = "gift_transactions"

    id = Column(String(36), primary_key=True, index=True)
    sender_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    receiver_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 礼物信息
    gift_id = Column(String(50), nullable=False)
    gift_name = Column(String(100), nullable=False)
    gift_icon = Column(String(50), nullable=False)
    gift_type = Column(String(20), nullable=False)
    gift_category = Column(String(20), nullable=False)

    # 数量和金额
    count = Column(Integer, default=1)
    price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)

    # 附带消息
    message = Column(Text, nullable=True)

    # 状态
    is_seen = Column(Boolean, default=False)
    is_animation_played = Column(Boolean, default=False)

    # 时间戳
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    seen_at = Column(DateTime(timezone=True), nullable=True)
    animation_played_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserGiftStatsDB(Base):
    """用户礼物统计"""
    __tablename__ = "user_gift_stats"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 收到的统计
    total_received_count = Column(Integer, default=0)
    total_received_amount = Column(Float, default=0)
    most_received_gift_id = Column(String(50), nullable=True)
    most_received_gift_count = Column(Integer, default=0)

    # 发送的统计
    total_sent_count = Column(Integer, default=0)
    total_sent_amount = Column(Float, default=0)
    most_sent_gift_id = Column(String(50), nullable=True)
    most_sent_gift_count = Column(Integer, default=0)

    # Top 送礼物/收礼物的人
    top_sender_id = Column(String(36), nullable=True)
    top_sender_amount = Column(Float, default=0)
    top_receiver_id = Column(String(36), nullable=True)
    top_receiver_amount = Column(Float, default=0)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())