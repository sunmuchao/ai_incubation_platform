"""
玫瑰表达系统模型

参考 Hinge 的 "Standout" 和玫瑰机制：
- 每位用户每月获得有限玫瑰（免费 1 个，会员更多）
- 玫瑰用于表达特别的喜欢，对方会优先看到
- 发送玫瑰后，用户资料会出现在对方的 "Standout" 列表中
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid


class RoseSource(str, Enum):
    """玫瑰来源"""
    FREE_MONTHLY = "free_monthly"  # 每月免费赠送
    MEMBERSHIP_STANDARD = "membership_standard"  # 标准会员赠送
    MEMBERSHIP_PREMIUM = "membership_premium"  # 高级会员赠送
    PURCHASED = "purchased"  # 单独购买
    GIFT = "gift"  # 系统赠送（活动等）


class RoseStatus(str, Enum):
    """玫瑰状态"""
    AVAILABLE = "available"  # 可用
    SENT = "sent"  # 已发送
    EXPIRED = "expired"  # 已过期


# 玫瑰分配配置（参考 Hinge：免费用户每月 1 个）
ROSE_ALLOCATION = {
    "free": {
        "monthly_roses": 1,  # 每月 1 个玫瑰
        "purchase_price": 30,  # 单个购买价格（元）
    },
    "standard": {
        "monthly_roses": 3,  # 每月 3 个玫瑰
        "purchase_price": 20,
    },
    "premium": {
        "monthly_roses": 5,  # 每月 5 个玫瑰
        "purchase_price": 15,
    },
}

# 玫瑰购买套餐
ROSE_PACKAGES = {
    "single": {
        "count": 1,
        "price": 30,
        "original_price": 30,
    },
    "bundle_3": {
        "count": 3,
        "price": 78,  # 相当于 26/个
        "original_price": 90,
        "discount": "省 12 元",
    },
    "bundle_5": {
        "count": 5,
        "price": 120,  # 相当于 24/个
        "original_price": 150,
        "discount": "省 30 元",
    },
}


class RoseBalance(BaseModel):
    """用户玫瑰余额"""
    user_id: str
    available_count: int  # 可用玫瑰数
    sent_count: int  # 本月已发送数
    monthly_allocation: int  # 本月分配总数
    next_refresh_date: datetime  # 下次刷新日期（月初）
    purchase_available: bool = True  # 是否可以购买额外玫瑰


class RoseTransaction(BaseModel):
    """玫瑰交易记录"""
    id: str = str(uuid.uuid4())
    sender_id: str  # 发送者 ID
    receiver_id: str  # 接收者 ID

    # 玫瑰信息
    rose_source: RoseSource  # 玫瑰来源
    rose_id: Optional[str] = None  # 使用的玫瑰 ID

    # 状态
    status: RoseStatus = RoseStatus.SENT
    is_seen: bool = False  # 接收者是否已查看

    # 附加信息
    message: Optional[str] = None  # 附带消息（可选）
    compatibility_score: Optional[float] = None  # 发送时的匹配度

    # 时间戳
    sent_at: datetime = datetime.now()
    seen_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None  # 过期时间（如果对方未查看）

    # Standout 状态
    in_standout: bool = True  # 是否在 Standout 列表中
    standout_expires_at: Optional[datetime] = None  # Standout 展示过期时间


class RoseSendRequest(BaseModel):
    """发送玫瑰请求"""
    target_user_id: str
    message: Optional[str] = None  # 附带消息（最多 100 字）
    rose_source: Optional[RoseSource] = None  # 指定使用的玫瑰来源


class RoseSendResponse(BaseModel):
    """发送玫瑰响应"""
    success: bool
    message: str
    roses_remaining: int  # 剩余玫瑰数
    transaction_id: Optional[str] = None
    is_match: bool = False  # 如果对方也发送过玫瑰，则匹配


class StandoutProfile(BaseModel):
    """Standout 用户资料（收到玫瑰的用户）"""
    user_id: str
    user_data: dict  # 用户基本信息

    # 玫瑰信息
    rose_received_at: datetime
    rose_count: int = 1  # 收到的玫瑰数（可能多人发送）
    latest_message: Optional[str] = None  # 最新附带消息

    # 匹配度
    compatibility_score: float

    # 时间戳
    standout_expires_at: datetime  # Standout 展示过期时间（24 小时）

    # 用户操作状态
    is_liked: bool = False  # 用户是否已喜欢
    is_passed: bool = False  # 用户是否已无感


class StandoutListResponse(BaseModel):
    """Standout 列表响应"""
    profiles: List[StandoutProfile]
    total_count: int
    unread_count: int  # 未查看的玫瑰数


# ============================================
# SQLAlchemy 模型定义
# ============================================
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, Float, Text
from sqlalchemy.sql import func
from db.database import Base


class UserRoseBalanceDB(Base):
    """用户玫瑰余额"""
    __tablename__ = "user_rose_balances"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 余额信息
    available_count = Column(Integer, default=1)  # 可用玫瑰数
    total_received_this_month = Column(Integer, default=1)  # 本月获得总数

    # 来源记录
    free_allocation = Column(Integer, default=1)  # 免费赠送
    membership_allocation = Column(Integer, default=0)  # 会员赠送
    purchased_count = Column(Integer, default=0)  # 购买数量
    gifted_count = Column(Integer, default=0)  # 系统赠送

    # 本月统计
    sent_this_month = Column(Integer, default=0)  # 本月已发送数

    # 时间戳
    last_refresh_at = Column(DateTime(timezone=True), server_default=func.now())  # 上次刷新时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class RoseTransactionDB(Base):
    """玫瑰交易记录"""
    __tablename__ = "rose_transactions"

    id = Column(String(36), primary_key=True, index=True)
    sender_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    receiver_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 玫瑰来源
    rose_source = Column(String(30), nullable=False)  # free_monthly, membership_standard, purchased, etc.

    # 状态
    status = Column(String(20), default="sent")  # sent, seen, expired, matched
    is_seen = Column(Boolean, default=False)

    # 附带信息
    message = Column(Text, nullable=True)
    compatibility_score = Column(Float, nullable=True)

    # Standout 状态
    in_standout = Column(Boolean, default=True)  # 是否在 Standout 列表
    standout_priority = Column(Integer, default=0)  # Standout 排序优先级

    # 时间戳
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    seen_at = Column(DateTime(timezone=True), nullable=True)
    standout_expires_at = Column(DateTime(timezone=True), nullable=True)  # Standout 过期时间（24小时）
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RosePurchaseDB(Base):
    """玫瑰购买记录"""
    __tablename__ = "rose_purchases"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # 购买信息
    package_type = Column(String(20), nullable=False)  # single, bundle_3, bundle_5
    rose_count = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)  # 支付金额

    # 支付信息
    payment_method = Column(String(20), default="wechat")
    payment_status = Column(String(20), default="pending")  # pending, paid, failed
    payment_time = Column(DateTime(timezone=True), nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())