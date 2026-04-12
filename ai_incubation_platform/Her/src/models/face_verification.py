"""
人脸认证模型

参考 Tinder Blue Star 认证徽章：
- 人脸照片与身份证照片比对
- 活体检测（防止照片攻击）
- 认证状态和徽章展示
- 认证历史记录
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid


class FaceVerificationStatus(str, Enum):
    """人脸认证状态"""
    NOT_STARTED = "not_started"  # 未开始
    IN_PROGRESS = "in_progress"  # 进行中
    SUBMITTED = "submitted"  # 已提交待审核
    VERIFIED = "verified"  # 已认证
    FAILED = "failed"  # 认证失败
    EXPIRED = "expired"  # 已过期


class FaceVerificationMethod(str, Enum):
    """人脸认证方式"""
    ID_CARD_COMPARE = "id_card_compare"  # 与身份证照片比对
    SELF_PHOTO = "self_photo"  # 自拍照片认证
    VIDEO_LIVENESS = "video_liveness"  # 视频活体检测
    AI_GESTURE = "ai_gesture"  # AI 动作活体检测


class VerificationBadgeType(str, Enum):
    """认证徽章类型"""
    BLUE_STAR = "blue_star"  # Tinder Blue Star - 基础人脸认证
    GOLD_STAR = "gold_star"  # 金星 - 高级认证（身份证+人脸）
    PLATINUM_STAR = "platinum_star"  # 铂金星 - 全认证
    DIAMOND_STAR = "diamond_star"  # 钻石星 - 最高认证


# 认证徽章配置（参考 Tinder）
VERIFICATION_BADGE_CONFIG = {
    VerificationBadgeType.BLUE_STAR: {
        "name": "蓝星认证",
        "icon": "⭐",
        "color": "#1890ff",
        "description": "已完成人脸认证",
        "requirements": ["face_verification"],
        "trust_weight": 20,
    },
    VerificationBadgeType.GOLD_STAR: {
        "name": "金星认证",
        "icon": "🌟",
        "color": "#faad14",
        "description": "身份证+人脸双重认证",
        "requirements": ["id_verification", "face_verification"],
        "trust_weight": 40,
    },
    VerificationBadgeType.PLATINUM_STAR: {
        "name": "铂金星认证",
        "icon": "✨",
        "color": "#95de64",
        "description": "实名+人脸+学历认证",
        "requirements": ["id_verification", "face_verification", "education_verification"],
        "trust_weight": 60,
    },
    VerificationBadgeType.DIAMOND_STAR: {
        "name": "钻石星认证",
        "icon": "💎",
        "color": "#D4A59A",
        "description": "全方位身份认证",
        "requirements": ["id_verification", "face_verification", "education_verification", "occupation_verification"],
        "trust_weight": 80,
    },
}


class FaceVerificationRequest(BaseModel):
    """人脸认证请求"""
    method: FaceVerificationMethod
    photo_base64: str  # 人脸照片（Base64）
    video_base64: Optional[str] = None  # 活体检测视频（可选）
    gesture_sequence: Optional[List[str]] = None  # 动作序列（眨眼、张嘴等）


class FaceVerificationResponse(BaseModel):
    """人脸认证响应"""
    success: bool
    message: str
    verification_id: Optional[str] = None
    status: FaceVerificationStatus
    similarity_score: Optional[float] = None  # 相似度分数（0-100）
    liveness_score: Optional[float] = None  # 活体分数（0-100）
    badge_type: Optional[VerificationBadgeType] = None


class VerificationBadge(BaseModel):
    """认证徽章"""
    id: str = str(uuid.uuid4())
    user_id: str
    badge_type: VerificationBadgeType
    status: str = "active"  # active, expired
    verification_id: str  # 关联的认证记录 ID

    # 徽章展示信息
    display_name: str
    display_icon: str
    display_color: str

    # 时间戳
    issued_at: datetime = datetime.now()
    expires_at: Optional[datetime] = None  # 徽章过期时间
    created_at: datetime = datetime.now()


class FaceVerificationRecord(BaseModel):
    """人脸认证记录"""
    id: str = str(uuid.uuid4())
    user_id: str

    # 认证方式
    method: FaceVerificationMethod

    # 认证状态
    status: FaceVerificationStatus

    # 认证结果
    similarity_score: Optional[float] = None
    liveness_score: Optional[float] = None
    is_passed: bool = False

    # 照片信息（脱敏）
    photo_hash: Optional[str] = None  # 照片哈希（用于去重）
    photo_url: Optional[str] = None  # 照片存储 URL（用于审核）

    # 失败原因
    failure_reason: Optional[str] = None
    retry_count: int = 0

    # 审核信息
    reviewed_by: Optional[str] = None  # 审核人
    reviewed_at: Optional[datetime] = None

    # 时间戳
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()


class UserVerificationStatus(BaseModel):
    """用户认证状态汇总"""
    user_id: str

    # 人脸认证
    face_verified: bool = False
    face_verification_id: Optional[str] = None
    face_verification_date: Optional[datetime] = None

    # 身份认证
    id_verified: bool = False
    id_verification_id: Optional[str] = None

    # 学历认证
    education_verified: bool = False

    # 职业认证
    occupation_verified: bool = False

    # 当前徽章
    current_badge: Optional[VerificationBadgeType] = None
    badge_display_name: Optional[str] = None
    badge_display_icon: Optional[str] = None
    badge_display_color: Optional[str] = None

    # 信任分
    trust_score: int = 0


# ============================================
# SQLAlchemy 模型定义
# ============================================
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, Float, Text
from sqlalchemy.sql import func
from db.database import Base

# 从 db.models 导入 VerificationBadgeDB，避免重复定义
from db.models import VerificationBadgeDB


class FaceVerificationDB(Base):
    """人脸认证记录"""
    __tablename__ = "face_verifications"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # 认证方式
    method = Column(String(30), default="id_card_compare")

    # 认证状态
    status = Column(String(20), default="not_started")

    # 认证结果
    similarity_score = Column(Float, nullable=True)
    liveness_score = Column(Float, nullable=True)
    is_passed = Column(Boolean, default=False)

    # 照片信息
    photo_hash = Column(String(64), nullable=True)
    photo_url = Column(String(500), nullable=True)

    # 失败信息
    failure_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # 审核信息
    reviewed_by = Column(String(36), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # 时间戳
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# VerificationBadgeDB 已从 db.models 导入，不再在此定义