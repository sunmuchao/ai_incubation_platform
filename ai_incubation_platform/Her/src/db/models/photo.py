"""
SQLAlchemy 数据模型 - 照片领域

包含：用户照片管理等
"""
from db.models.base import *

class PhotoDB(Base):
    """用户照片管理"""
    __tablename__ = "photos"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    photo_url = Column(String(500), nullable=False)
    photo_type = Column(String(20), default="profile")
    display_order = Column(Integer, default=0)

    moderation_status = Column(String(20), default="pending")
    moderation_reason = Column(Text, nullable=True)
    moderated_at = Column(DateTime(timezone=True), nullable=True)
    moderated_by = Column(String(36), nullable=True)

    ai_tags = Column(Text, default="")
    ai_quality_score = Column(Float, nullable=True)

    is_verified = Column(Boolean, default=False)
    verification_pose = Column(String(50), nullable=True)

    like_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)

__all__ = ["PhotoDB"]