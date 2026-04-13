"""
SQLAlchemy 数据模型 - 灰度发布领域

包含：功能开关、A/B实验、用户分组等
"""
from db.models.base import *

class FeatureFlagDB(Base):
    """功能开关配置"""
    __tablename__ = "feature_flags"

    id = Column(String(36), primary_key=True, index=True)
    flag_key = Column(String(100), unique=True, nullable=False, index=True)

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    is_enabled = Column(Boolean, default=False)
    rollout_percentage = Column(Integer, default=0)

    target_user_groups = Column(JSON, default=list)
    target_cities = Column(JSON, default=list)

    config_data = Column(JSON, default=dict)

    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ABExperimentDB(Base):
    """A/B 实验配置"""
    __tablename__ = "ab_experiments"

    id = Column(String(36), primary_key=True, index=True)
    experiment_key = Column(String(100), unique=True, nullable=False, index=True)

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    status = Column(String(20), default="draft")

    variants = Column(JSON, default=list)

    primary_metric = Column(String(100), nullable=True)
    secondary_metrics = Column(JSON, default=list)

    traffic_allocation = Column(Integer, default=100)

    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UserExperimentAssignmentDB(Base):
    """用户实验分组记录"""
    __tablename__ = "user_experiment_assignments"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    experiment_key = Column(String(100), nullable=False, index=True)

    variant_name = Column(String(50), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

__all__ = ["FeatureFlagDB", "ABExperimentDB", "UserExperimentAssignmentDB"]