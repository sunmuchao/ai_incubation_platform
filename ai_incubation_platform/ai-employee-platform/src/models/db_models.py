"""
SQLAlchemy 数据库模型定义
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid

from config.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


# ==================== 枚举类型 ====================

class SkillLevelEnum(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class EmployeeStatusEnum(str, enum.Enum):
    AVAILABLE = "available"
    HIRED = "hired"
    TRAINING = "training"
    OFFLINE = "offline"


class TrainingDataTypeEnum(str, enum.Enum):
    PROMPT = "prompt"
    KNOWLEDGE = "knowledge"
    EXAMPLE = "example"
    FINE_TUNE = "fine_tune"
    TOOL_CONFIG = "tool_config"


class TrainingStatusEnum(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RiskLevelEnum(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKED = "blocked"


class TenantStatusEnum(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    TRIAL = "trial"


class UserRoleEnum(str, enum.Enum):
    ADMIN = "admin"
    OWNER = "owner"
    HIRER = "hirer"
    FINANCE = "finance"


class BillingCycleEnum(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class InvoiceStatusEnum(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PaymentStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethodEnum(str, enum.Enum):
    ALIPAY = "alipay"
    WECHAT = "wechat"
    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"
    BALANCE = "balance"


class OrderStatusEnum(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class ReviewTypeEnum(str, enum.Enum):
    """评价类型"""
    HIRER_TO_EMPLOYEE = "hirer_to_employee"
    OWNER_TO_HIRER = "owner_to_hirer"


class EmployerStatusEnum(str, enum.Enum):
    """雇主状态"""
    ACTIVE = "active"
    OFFLINE = "offline"
    SUSPENDED = "suspended"
    VERIFIED = "verified"


class SkillCategoryEnum(str, enum.Enum):
    """技能分类"""
    TECHNICAL = "technical"
    DESIGN = "design"
    WRITING = "writing"
    MARKETING = "marketing"
    BUSINESS = "business"
    SUPPORT = "support"
    AI_SPECIALIZED = "ai_specialized"


# ==================== 核心模型 ====================

class TenantDB(Base):
    """租户表"""
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    contact_name = Column(String, nullable=False)
    contact_email = Column(String, nullable=False)
    contact_phone = Column(String, nullable=True)
    status = Column(SQLEnum(TenantStatusEnum), default=TenantStatusEnum.TRIAL)
    billing_cycle = Column(SQLEnum(BillingCycleEnum), default=BillingCycleEnum.MONTHLY)
    max_employees = Column(Integer, default=10)
    max_concurrent_jobs = Column(Integer, default=5)
    storage_quota_gb = Column(Integer, default=10)
    used_storage_gb = Column(Float, default=0.0)
    trial_end_at = Column(DateTime, nullable=True)
    metadata_ = Column(JSON, default=dict)  # 避免与 metadata 保留字冲突
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    users = relationship("UserDB", back_populates="tenant", cascade="all, delete-orphan")
    employees = relationship("AIEmployeeDB", back_populates="tenant", cascade="all, delete-orphan")
    orders = relationship("OrderDB", back_populates="tenant", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecordDB", back_populates="tenant", cascade="all, delete-orphan")
    invoices = relationship("InvoiceDB", back_populates="tenant", cascade="all, delete-orphan")
    payments = relationship("PaymentTransactionDB", back_populates="tenant", cascade="all, delete-orphan")
    wallet = relationship("WalletDB", back_populates="tenant", uselist=False, cascade="all, delete-orphan")
    # files 关系由 file_models.add_file_relationships() 动态添加，避免循环依赖


class UserDB(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    avatar = Column(String, nullable=True)
    role = Column(SQLEnum(UserRoleEnum), default=UserRoleEnum.HIRER)
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    tenant = relationship("TenantDB", back_populates="users")
    # files 关系由 file_models.add_file_relationships() 动态添加，避免循环依赖


class AIEmployeeDB(Base):
    """AI 员工表"""
    __tablename__ = "ai_employees"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    owner_id = Column(String, nullable=False)  # 所有者用户 ID
    avatar = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    skills = Column(JSON, default=dict)  # 存储为 JSON {"skill_name": "level"}
    status = Column(SQLEnum(EmployeeStatusEnum), default=EmployeeStatusEnum.AVAILABLE)
    hourly_rate = Column(Float, default=10.0)
    total_jobs = Column(Integer, default=0)
    total_earnings = Column(Float, default=0.0)
    rating = Column(Float, default=5.0)
    review_count = Column(Integer, default=0)
    current_training_version = Column(String, nullable=True)
    training_versions = Column(JSON, default=list)  # 版本 ID 列表
    agent_config = Column(JSON, default=dict)
    deerflow_agent_id = Column(String, nullable=True)
    risk_level = Column(SQLEnum(RiskLevelEnum), default=RiskLevelEnum.LOW)
    risk_score = Column(Float, default=0.0)
    violation_count = Column(Integer, default=0)
    last_risk_check = Column(DateTime, nullable=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    tenant = relationship("TenantDB", back_populates="employees")
    orders = relationship("OrderDB", back_populates="employee", foreign_keys="OrderDB.employee_id")
    # escrows 关系由 p4_models.add_p4_relationships() 动态添加，避免循环依赖
    # training_data 和 training_tasks 关系由 p4_training_models.add_training_relationships() 动态添加
    # 可观测性关联 (v1.1 新增) - 由 observability_models.add_observability_relationships() 动态添加，避免循环依赖


class OrderDB(Base):
    """订单表"""
    __tablename__ = "orders"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    employee_id = Column(String, ForeignKey("ai_employees.id"), nullable=False)
    owner_id = Column(String, nullable=False)
    hirer_id = Column(String, nullable=False)
    duration_hours = Column(Integer, nullable=False)
    task_description = Column(Text, nullable=False)
    hourly_rate = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    platform_fee_rate = Column(Float, default=0.1)
    platform_fee = Column(Float, nullable=False)
    owner_earning = Column(Float, nullable=False)
    status = Column(SQLEnum(OrderStatusEnum), default=OrderStatusEnum.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    confirmed_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    rating = Column(Float, nullable=True)
    review = Column(Text, nullable=True)
    review_tags = Column(JSON, default=list)
    review_likes = Column(Integer, default=0)
    is_review_hidden = Column(Boolean, default=False)
    risk_check_passed = Column(Boolean, default=True)
    risk_factors = Column(JSON, default=list)

    # 关系
    tenant = relationship("TenantDB", back_populates="orders")
    employee = relationship("AIEmployeeDB", back_populates="orders", foreign_keys=[employee_id])
    # disputes 和 escrows、milestones 关系由 p4_models.add_p4_relationships() 动态添加，避免循环依赖
    # files 关系由 file_models.add_file_relationships() 动态添加，避免循环依赖
    # training_data 和 training_tasks 关系由 p4_training_models 动态添加


class UsageRecordDB(Base):
    """用量记录表"""
    __tablename__ = "usage_records"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    user_id = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=True)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    tenant = relationship("TenantDB", back_populates="usage_records")


class InvoiceDB(Base):
    """账单发票表"""
    __tablename__ = "invoices"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    invoice_number = Column(String, unique=True, nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    total_amount = Column(Float, nullable=False)
    paid_amount = Column(Float, default=0.0)
    due_date = Column(DateTime, nullable=False)
    status = Column(SQLEnum(InvoiceStatusEnum), default=InvoiceStatusEnum.DRAFT)
    items = Column(JSON, default=list)
    payment_status = Column(SQLEnum(PaymentStatusEnum), default=PaymentStatusEnum.PENDING)
    issued_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    tenant = relationship("TenantDB", back_populates="invoices")


class PaymentTransactionDB(Base):
    """支付交易表"""
    __tablename__ = "payment_transactions"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    user_id = Column(String, nullable=False)
    invoice_id = Column(String, nullable=True)
    order_id = Column(String, nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="CNY")
    payment_method = Column(SQLEnum(PaymentMethodEnum), nullable=False)
    status = Column(SQLEnum(PaymentStatusEnum), default=PaymentStatusEnum.PENDING)
    third_party_transaction_id = Column(String, nullable=True)
    payment_data = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    tenant = relationship("TenantDB", back_populates="payments")


class WalletDB(Base):
    """租户钱包表"""
    __tablename__ = "wallets"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), unique=True, nullable=False)
    balance = Column(Float, default=0.0)
    frozen_balance = Column(Float, default=0.0)
    total_recharge = Column(Float, default=0.0)
    total_consumption = Column(Float, default=0.0)
    currency = Column(String, default="CNY")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    tenant = relationship("TenantDB", back_populates="wallet")


# ======================================
# P3 新增模型：双向评价、雇主档案、技能体系
# ======================================

class ReviewDB(Base):
    """评价表 - 支持双向评价"""
    __tablename__ = "reviews"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    employee_id = Column(String, ForeignKey("ai_employees.id"), nullable=False)
    reviewer_id = Column(String, nullable=False)  # 评价者 ID
    reviewee_id = Column(String, nullable=False)  # 被评价者 ID
    review_type = Column(SQLEnum(ReviewTypeEnum), nullable=False)
    rating = Column(Float, nullable=False)
    review_text = Column(Text, nullable=True)
    review_tags = Column(JSON, default=list)
    # 维度评分
    communication = Column(Float, default=5.0)
    quality = Column(Float, default=5.0)
    timeliness = Column(Float, default=5.0)
    professionalism = Column(Float, default=5.0)
    # 可见性
    is_public = Column(Boolean, default=True)
    is_hidden = Column(Boolean, default=False)
    # 互动
    likes = Column(Integer, default=0)
    response = Column(Text, nullable=True)  # 被评价者回复
    response_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    tenant = relationship("TenantDB", backref="reviews")
    order = relationship("OrderDB", backref="reviews")
    employee = relationship("AIEmployeeDB", backref="reviews")


class EmployerProfileDB(Base):
    """雇主（租赁者）档案表"""
    __tablename__ = "employer_profiles"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    user_id = Column(String, unique=True, nullable=False)  # 关联的用户 ID
    company_name = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    company_size = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    # 统计数据
    total_hires = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)
    active_jobs = Column(Integer, default=0)
    # 评价相关
    rating = Column(Float, default=5.0)
    review_count = Column(Integer, default=0)
    # 行为指标
    avg_response_time_hours = Column(Float, nullable=True)
    rehire_rate = Column(Float, default=0.0)
    # 状态
    status = Column(SQLEnum(EmployerStatusEnum), default=EmployerStatusEnum.ACTIVE)
    is_verified = Column(Boolean, default=False)
    verification_badges = Column(JSON, default=list)
    # 风控
    risk_score = Column(Float, default=0.0)
    violation_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    tenant = relationship("TenantDB", backref="employer_profiles")


class SkillTagDB(Base):
    """标准化技能标签表"""
    __tablename__ = "skill_tags"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, nullable=False, index=True)
    category = Column(SQLEnum(SkillCategoryEnum), nullable=False)
    parent_skill_id = Column(String, ForeignKey("skill_tags.id"), nullable=True)  # 父技能 ID
    description = Column(Text, nullable=True)
    # 使用统计
    usage_count = Column(Integer, default=0)
    avg_hourly_rate = Column(Float, default=0.0)
    # 认证要求
    has_certification = Column(Boolean, default=False)
    certification_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    parent_skill = relationship("SkillTagDB", remote_side=[id], backref="child_skills")
    employee_skills = relationship("EmployeeSkillDB", back_populates="skill_tag")


class EmployeeSkillDB(Base):
    """员工技能关联表"""
    __tablename__ = "employee_skills"

    id = Column(String, primary_key=True, default=generate_uuid)
    employee_id = Column(String, ForeignKey("ai_employees.id"), nullable=False)
    skill_tag_id = Column(String, ForeignKey("skill_tags.id"), nullable=False)
    skill_name = Column(String, nullable=False)  # 冗余字段，便于查询
    level = Column(SQLEnum(SkillLevelEnum), nullable=False)
    years_of_experience = Column(Float, nullable=True)
    certified = Column(Boolean, default=False)
    certification_id = Column(String, nullable=True)
    portfolio_items = Column(JSON, default=list)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    employee = relationship("AIEmployeeDB", backref="employee_skills")
    skill_tag = relationship("SkillTagDB", back_populates="employee_skills")
