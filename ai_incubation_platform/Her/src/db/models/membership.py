"""
SQLAlchemy 数据模型 - 会员订阅领域

包含：会员状态、会员订单、功能使用记录等
"""
from db.models.base import *

class UserMembershipDB(Base):
    """用户会员状态"""
    __tablename__ = "user_memberships"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    tier = Column(String(20), default="free")
    status = Column(String(20), default="inactive")

    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)

    auto_renew = Column(Boolean, default=False)

    payment_method = Column(String(20), nullable=True)
    subscription_id = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class MembershipOrderDB(Base):
    """会员订单"""
    __tablename__ = "membership_orders"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    tier = Column(String(20), nullable=False)
    duration_months = Column(Integer, nullable=False)

    amount = Column(Float, nullable=False)
    original_amount = Column(Float, nullable=False)
    discount_code = Column(String(50), nullable=True)

    status = Column(String(20), default="pending")

    payment_method = Column(String(20), nullable=True)
    payment_time = Column(DateTime(timezone=True), nullable=True)
    transaction_id = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class MemberFeatureUsageDB(Base):
    """会员功能使用记录"""
    __tablename__ = "member_feature_usage"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    feature = Column(String(50), nullable=False)
    usage_count = Column(Integer, default=1)
    usage_date = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

__all__ = ["UserMembershipDB", "MembershipOrderDB", "MemberFeatureUsageDB"]