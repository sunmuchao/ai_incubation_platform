"""
P4 训练数据版本化模型

注意：这些模型使用 extend_existing 以兼容 training_service.py 中的现有设计
"""

from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, Float, JSON, func
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum

from config.database import Base


class TrainingStatus(str, Enum):
    """训练状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TrainingDataSource(str, Enum):
    """训练数据来源"""
    MANUAL_UPLOAD = "manual_upload"
    FEEDBACK_LOOP = "feedback_loop"
    FINE_TUNING = "fine_tuning"
    TRANSFER_LEARNING = "transfer_learning"


class TrainingDataVersionDB(Base):
    """训练数据版本"""
    __tablename__ = "training_data_versions"
    __table_args__ = {'extend_existing': True}

    id = Column(String(64), primary_key=True)
    employee_id = Column(String(64), ForeignKey("ai_employees.id"), nullable=False)
    tenant_id = Column(String(64), ForeignKey("tenants.id"), nullable=False)

    # 版本信息
    version_number = Column(Integer, nullable=False)
    version_name = Column(String(128), nullable=True)
    parent_version_id = Column(String(64), ForeignKey("training_data_versions.id"), nullable=True)

    # 训练数据
    training_data_hash = Column(String(64), nullable=True)
    training_data_path = Column(String(512), nullable=True)
    training_data_size = Column(Integer, default=0)
    training_data_count = Column(Integer, default=0)

    # 训练配置
    training_config = Column(JSON, nullable=True)
    base_model = Column(String(128), nullable=True)
    model_artifact_path = Column(String(512), nullable=True)

    # 训练状态
    training_status = Column(SQLEnum(TrainingStatus), default=TrainingStatus.PENDING)
    data_source = Column(SQLEnum(TrainingDataSource), default=TrainingDataSource.MANUAL_UPLOAD)

    # 训练指标
    training_metrics = Column(JSON, nullable=True)
    validation_metrics = Column(JSON, nullable=True)
    test_metrics = Column(JSON, nullable=True)

    # 训练时间
    training_started_at = Column(DateTime, nullable=True)
    training_completed_at = Column(DateTime, nullable=True)
    training_duration_seconds = Column(Integer, nullable=True)

    # 版本说明
    description = Column(Text, nullable=True)
    changes = Column(JSON, nullable=True)

    # 标记
    is_active = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(64), nullable=True)


class TrainingDatasetDB(Base):
    """训练数据集"""
    __tablename__ = "training_datasets"
    __table_args__ = {'extend_existing': True}

    id = Column(String(64), primary_key=True)
    version_id = Column(String(64), ForeignKey("training_data_versions.id"), nullable=False)
    tenant_id = Column(String(64), ForeignKey("tenants.id"), nullable=False)

    # 数据集信息
    dataset_name = Column(String(128), nullable=False)
    dataset_type = Column(String(50), nullable=False)

    # 数据存储
    file_path = Column(String(512), nullable=False)
    file_hash = Column(String(64), nullable=True)
    file_size = Column(Integer, default=0)
    record_count = Column(Integer, default=0)

    # 数据格式
    data_format = Column(String(50), default="jsonl")
    schema = Column(JSON, nullable=True)

    # 数据统计
    statistics = Column(JSON, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(64), nullable=True)


class TrainingJobDB(Base):
    """训练任务"""
    __tablename__ = "training_jobs"
    __table_args__ = {'extend_existing': True}

    id = Column(String(64), primary_key=True)
    version_id = Column(String(64), ForeignKey("training_data_versions.id"), nullable=False)
    employee_id = Column(String(64), ForeignKey("ai_employees.id"), nullable=False)
    tenant_id = Column(String(64), ForeignKey("tenants.id"), nullable=False)

    # 任务信息
    job_name = Column(String(128), nullable=False)
    job_type = Column(String(50), nullable=False)

    # 训练配置
    training_config = Column(JSON, nullable=False)
    resource_config = Column(JSON, nullable=True)

    # 任务状态
    status = Column(SQLEnum(TrainingStatus), default=TrainingStatus.PENDING)
    progress_percent = Column(Integer, default=0)
    current_step = Column(String(128), nullable=True)

    # 训练结果
    model_artifact_path = Column(String(512), nullable=True)
    training_metrics = Column(JSON, nullable=True)
    final_metrics = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    error_stack = Column(Text, nullable=True)

    # 资源使用
    gpu_hours = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_by = Column(String(64), nullable=True)


class TrainingTaskDB(Base):
    """训练任务"""
    __tablename__ = "training_tasks"
    __table_args__ = {'extend_existing': True}

    id = Column(String(64), primary_key=True)
    employee_id = Column(String(64), ForeignKey("ai_employees.id"), nullable=False)
    tenant_id = Column(String(64), ForeignKey("tenants.id"), nullable=False)
    version_id = Column(String(64), ForeignKey("training_data_versions.id"), nullable=False)

    # 任务信息
    task_name = Column(String(128), nullable=True)
    task_type = Column(String(50), nullable=True)  # full_training/fine_tuning/incremental

    # 训练配置
    training_config = Column(JSON, nullable=True)

    # 任务状态
    status = Column(SQLEnum(TrainingStatus), default=TrainingStatus.PENDING)
    progress_percent = Column(Integer, default=0)
    current_step = Column(String(128), nullable=True)

    # 训练结果
    model_version = Column(String, nullable=True)
    metrics = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_by = Column(String(64), nullable=True)


def add_training_relationships():
    """添加训练相关的关联关系到现有模型"""
    from .db_models import AIEmployeeDB

    # 添加 training_data 关系
    if not hasattr(AIEmployeeDB, 'training_data'):
        AIEmployeeDB.training_data = relationship(
            "TrainingDataVersionDB",
            back_populates="employee",
            cascade="all, delete-orphan"
        )

    # 添加 training_tasks 关系
    if not hasattr(AIEmployeeDB, 'training_tasks'):
        AIEmployeeDB.training_tasks = relationship(
            "TrainingTaskDB",
            back_populates="employee",
            cascade="all, delete-orphan"
        )

    # 添加 TrainingDataVersionDB.employee 关系
    if not hasattr(TrainingDataVersionDB, 'employee'):
        TrainingDataVersionDB.employee = relationship("AIEmployeeDB", back_populates="training_data")

    # 添加 TrainingTaskDB.employee 关系
    if not hasattr(TrainingTaskDB, 'employee'):
        TrainingTaskDB.employee = relationship("AIEmployeeDB", back_populates="training_tasks")


class ABTestDB(Base):
    """A/B 测试"""
    __tablename__ = "ab_tests"
    __table_args__ = {'extend_existing': True}

    id = Column(String(64), primary_key=True)
    employee_id = Column(String(64), ForeignKey("ai_employees.id"), nullable=False)
    tenant_id = Column(String(64), ForeignKey("tenants.id"), nullable=False)

    # 测试信息
    test_name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)

    # 测试版本
    control_version_id = Column(String(64), ForeignKey("training_data_versions.id"), nullable=False)
    treatment_version_id = Column(String(64), ForeignKey("training_data_versions.id"), nullable=False)

    # 测试配置
    traffic_split_percent = Column(Integer, default=50)  # 流量分配比例
    min_sample_size = Column(Integer, default=100)  # 最小样本量

    # 测试状态
    status = Column(String(50), default="running")  # running, completed, stopped

    # 测试结果
    control_metrics = Column(JSON, nullable=True)
    treatment_metrics = Column(JSON, nullable=True)
    statistical_significance = Column(Float, nullable=True)

    # 时间戳
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    created_by = Column(String(64), nullable=True)
