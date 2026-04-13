"""
SQLAlchemy 数据模型 - 验证认证领域

包含：实名认证、信任徽章、学历认证、职业认证等
"""
from db.models.base import *

class IdentityVerificationDB(Base):
    """用户实名认证信息"""
    __tablename__ = "identity_verifications"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    real_name = Column(String(100), nullable=False)
    id_number = Column(String(18), nullable=False)
    id_number_hash = Column(String(64), nullable=False, index=True)

    verification_status = Column(String(20), default="pending")
    rejection_reason = Column(Text, nullable=True)

    ocr_data = Column(Text, default="")
    id_front_url = Column(String(500), nullable=True)
    id_back_url = Column(String(500), nullable=True)

    face_verify_url = Column(String(500), nullable=True)
    face_similarity_score = Column(Float, nullable=True)

    verification_type = Column(String(20), default="basic")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    verified_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    verification_badge = Column(String(20), nullable=True)


class VerificationBadgeDB(Base):
    """用户信任徽章/认证标识"""
    __tablename__ = "verification_badges"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    badge_type = Column(String(50), nullable=False, index=True)
    status = Column(String(20), default="active")

    verification_data = Column(Text, default="")

    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    display_order = Column(Integer, default=10)

    icon_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class EducationVerificationDB(Base):
    """学历认证信息"""
    __tablename__ = "education_verifications"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    school_name = Column(String(200), nullable=False)
    school_type = Column(String(50), nullable=True)
    degree = Column(String(50), nullable=True)
    major = Column(String(100), nullable=True)
    graduation_year = Column(Integer, nullable=True)

    verification_status = Column(String(20), default="pending")
    verification_method = Column(String(50), default="manual")

    certificate_url = Column(String(500), nullable=True)
    student_id_url = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    verified_at = Column(DateTime(timezone=True), nullable=True)


class CareerVerificationDB(Base):
    """职业认证信息"""
    __tablename__ = "career_verifications"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    company_name = Column(String(200), nullable=True)
    company_type = Column(String(50), nullable=True)
    position = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)

    verification_status = Column(String(20), default="pending")
    verification_method = Column(String(50), default="manual")

    work_email = Column(String(255), nullable=True)
    work_certificate_url = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    verified_at = Column(DateTime(timezone=True), nullable=True)

__all__ = [
    "IdentityVerificationDB", "VerificationBadgeDB",
    "EducationVerificationDB", "CareerVerificationDB"
]