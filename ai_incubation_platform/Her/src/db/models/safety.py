"""
SQLAlchemy 数据模型 - 安全领域

包含：安全区域、可信联系人、用户黑名单、举报记录等
"""
from db.models.base import *

class SafetyZoneDB(Base):
    """安全区域/危险区域配置"""
    __tablename__ = "safety_zones"

    id = Column(String(36), primary_key=True, index=True)

    zone_type = Column(String(20), nullable=False)
    name = Column(String(200), nullable=False)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    radius = Column(Integer, nullable=False)

    description = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class TrustedContactDB(Base):
    """可信联系人/紧急联系人"""
    __tablename__ = "trusted_contacts"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    relationship = Column(String(50), nullable=True)

    can_view_location = Column(Boolean, default=True)
    can_receive_emergency = Column(Boolean, default=True)

    display_order = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UserBlockDB(Base):
    """用户黑名单"""
    __tablename__ = "user_blocks"

    id = Column(String(36), primary_key=True, index=True)
    blocker_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    blocked_user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    reason = Column(String(50), nullable=True)

    block_scope = Column(Text, default="")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)


class UserReportDB(Base):
    """用户举报记录表"""
    __tablename__ = "user_reports"

    id = Column(String(36), primary_key=True, index=True)

    reporter_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    reported_user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    report_type = Column(String(50), nullable=False, index=True)
    reason = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    conversation_id = Column(String(36), nullable=True, index=True)
    message_id = Column(String(36), nullable=True)
    date_id = Column(String(36), nullable=True)

    evidence_urls = Column(JSON, nullable=True)

    status = Column(String(20), default="pending", index=True)
    priority = Column(Integer, default=1, index=True)

    reviewed_by = Column(String(36), nullable=True, index=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)

    action_taken = Column(String(100), nullable=True)
    action_details = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

__all__ = ["SafetyZoneDB", "TrustedContactDB", "UserBlockDB", "UserReportDB"]