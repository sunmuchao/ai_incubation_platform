"""
P4 阶段新增数据库模型：
- 提案/投标系统 (Proposals)
- 时间追踪与工作验证 (Time Tracking & Work Verification)
- 支付托管 (Escrow)
- 消息系统 (Messaging)
- 争议解决 (Dispute Resolution)
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

class ProposalStatusEnum(str, enum.Enum):
    """提案状态"""
    PENDING = "pending"  # 待审核
    ACCEPTED = "accepted"  # 已接受
    REJECTED = "rejected"  # 已拒绝
    CANCELLED = "cancelled"  # 已取消
    EXPIRED = "expired"  # 已过期


class ProposalTypeEnum(str, enum.Enum):
    """提案类型"""
    FIXED_PRICE = "fixed_price"  # 固定价格
    HOURLY = "hourly"  # 按小时计费


class WorkLogStatusEnum(str, enum.Enum):
    """工作日志状态"""
    ACTIVE = "active"  # 进行中
    PAUSED = "paused"  # 已暂停
    COMPLETED = "completed"  # 已完成
    SUBMITTED = "submitted"  # 已提交审核
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 已拒绝


class VerificationMethodEnum(str, enum.Enum):
    """验证方式"""
    MANUAL = "manual"  # 手动确认
    SCREENSHOT = "screenshot"  # 截图
    ACTIVITY_LOG = "activity_log"  # 活动日志
    DELIVERABLE = "deliverable"  # 交付物
    MILESTONE = "milestone"  # 里程碑


class EscrowStatusEnum(str, enum.Enum):
    """托管状态"""
    PENDING = "pending"  # 待充值
    FUNDED = "funded"  # 已充值
    RELEASED = "released"  # 已释放
    REFUNDED = "refunded"  # 已退款
    DISPUTED = "disputed"  # 争议中
    PARTIALLY_RELEASED = "partially_released"  # 部分释放


class MessageTypeEnum(str, enum.Enum):
    """消息类型"""
    TEXT = "text"  # 文本
    FILE = "file"  # 文件
    IMAGE = "image"  # 图片
    SYSTEM = "system"  # 系统消息
    MILESTONE = "milestone"  # 里程碑消息


class DisputeStatusEnum(str, enum.Enum):
    """争议状态"""
    OPEN = "open"  # 开启
    UNDER_REVIEW = "under_review"  # 审核中
    MEDIATION = "mediation"  # 调解中
    RESOLVED = "resolved"  # 已解决
    CLOSED = "closed"  # 已关闭
    ESCALATED = "escalated"  # 已升级


class DisputeResolutionEnum(str, enum.Enum):
    """争议解决方式"""
    MUTUAL_AGREEMENT = "mutual_agreement"  # 双方协商
    PLATFORM_MEDIATION = "platform_mediation"  # 平台调解
    ARBITRATION = "arbitration"  # 仲裁
    REFUND = "refund"  # 退款
    PARTIAL_REFUND = "partial_refund"  # 部分退款


class MilestoneStatusEnum(str, enum.Enum):
    """里程碑状态"""
    PENDING = "pending"  # 待开始
    IN_PROGRESS = "in_progress"  # 进行中
    SUBMITTED = "submitted"  # 已提交
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 已拒绝


# ==================== 提案/投标系统 ====================

class JobPostingDB(Base):
    """职位发布表 - 租赁者发布需求"""
    __tablename__ = "job_postings"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    hirer_id = Column(String, nullable=False)  # 发布者 ID
    title = Column(String, nullable=False)  # 职位标题
    description = Column(Text, nullable=False)  # 职位描述
    job_type = Column(SQLEnum(ProposalTypeEnum), default=ProposalTypeEnum.HOURLY)  # 工作类型
    budget_min = Column(Float, nullable=True)  # 预算范围 - 最低
    budget_max = Column(Float, nullable=True)  # 预算范围 - 最高
    hourly_rate_min = Column(Float, nullable=True)  # 小时费率 - 最低
    hourly_rate_max = Column(Float, nullable=True)  # 小时费率 - 最高
    duration_hours = Column(Integer, nullable=True)  # 预计工时
    required_skills = Column(JSON, default=list)  # 所需技能标签
    required_experience = Column(String, nullable=True)  # 经验要求
    deadline = Column(DateTime, nullable=True)  # 截止日期
    status = Column(String, default="open")  # open, closed, filled
    proposal_count = Column(Integer, default=0)  # 提案数量
    views = Column(Integer, default=0)  # 浏览次数
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    closed_at = Column(DateTime, nullable=True)
    filled_at = Column(DateTime, nullable=True)

    # 关系
    proposals = relationship("ProposalDB", back_populates="job_posting", cascade="all, delete-orphan")


class ProposalDB(Base):
    """提案表 - 员工所有者对职位发布进行投标"""
    __tablename__ = "proposals"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    job_posting_id = Column(String, ForeignKey("job_postings.id"), nullable=False)
    employee_id = Column(String, ForeignKey("ai_employees.id"), nullable=False)
    owner_id = Column(String, nullable=False)  # 提案者（员工所有者）ID
    cover_letter = Column(Text, nullable=False)  # 求职信
    proposed_rate = Column(Float, nullable=False)  # 报价
    proposed_duration_hours = Column(Integer, nullable=True)  # 预计工时
    proposal_type = Column(SQLEnum(ProposalTypeEnum), default=ProposalTypeEnum.FIXED_PRICE)  # 提案类型
    delivery_date = Column(DateTime, nullable=True)  # 预计交付日期
    attachments = Column(JSON, default=list)  # 附件列表
    status = Column(SQLEnum(ProposalStatusEnum), default=ProposalStatusEnum.PENDING)
    hirer_message = Column(Text, nullable=True)  # 租赁者回复消息
    viewed_at = Column(DateTime, nullable=True)  # 被查看时间
    responded_at = Column(DateTime, nullable=True)  # 被回复时间
    expires_at = Column(DateTime, nullable=True)  # 过期时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    job_posting = relationship("JobPostingDB", back_populates="proposals")
    employee = relationship("AIEmployeeDB", backref="proposals")

    # 订单关联（提案被接受后创建订单）
    order_id = Column(String, nullable=True)  # 关联的订单 ID


# ==================== 时间追踪与工作验证 ====================

class WorkSessionDB(Base):
    """工作时间会话表 - 记录工作时间段"""
    __tablename__ = "work_sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    employee_id = Column(String, ForeignKey("ai_employees.id"), nullable=False)
    hirer_id = Column(String, nullable=False)  # 租赁者 ID
    started_at = Column(DateTime, nullable=False)  # 开始时间
    ended_at = Column(DateTime, nullable=True)  # 结束时间
    duration_seconds = Column(Integer, default=0)  # 实际工作时长（秒）
    billable_seconds = Column(Integer, default=0)  # 计费时长（秒）
    status = Column(SQLEnum(WorkLogStatusEnum), default=WorkLogStatusEnum.ACTIVE)
    activity_description = Column(Text, nullable=True)  # 活动描述
    automatic = Column(Boolean, default=False)  # 是否自动追踪
    metadata_ = Column(JSON, default=dict)  # 附加数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    order = relationship("OrderDB", backref="work_sessions")
    employee = relationship("AIEmployeeDB", backref="work_sessions")


class WorkLogDB(Base):
    """工作日志表 - 详细的工作记录"""
    __tablename__ = "work_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    session_id = Column(String, ForeignKey("work_sessions.id"), nullable=True)
    employee_id = Column(String, ForeignKey("ai_employees.id"), nullable=False)
    logged_at = Column(DateTime, nullable=False)  # 记录时间
    duration_minutes = Column(Integer, default=0)  # 工作时长（分钟）
    description = Column(Text, nullable=False)  # 工作描述
    work_type = Column(String, default="development")  # 工作类型
    verification_method = Column(SQLEnum(VerificationMethodEnum), default=VerificationMethodEnum.MANUAL)
    verification_data = Column(JSON, default=dict)  # 验证数据（截图 URL、活动日志等）
    status = Column(SQLEnum(WorkLogStatusEnum), default=WorkLogStatusEnum.SUBMITTED)
    approved_by = Column(String, nullable=True)  # 批准人 ID
    approved_at = Column(DateTime, nullable=True)  # 批准时间
    rejection_reason = Column(Text, nullable=True)  # 拒绝原因
    billable = Column(Boolean, default=True)  # 是否可计费
    hourly_rate = Column(Float, nullable=False)  # 小时费率
    amount = Column(Float, default=0.0)  # 金额
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    order = relationship("OrderDB", backref="work_logs")
    session = relationship("WorkSessionDB", backref="work_logs")
    employee = relationship("AIEmployeeDB", backref="work_logs")


class MilestoneDB(Base):
    """里程碑表 - 用于分阶段交付和付款"""
    __tablename__ = "milestones"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    title = Column(String, nullable=False)  # 里程碑标题
    description = Column(Text, nullable=False)  # 里程碑描述
    deliverables = Column(JSON, default=list)  # 交付物列表
    amount = Column(Float, nullable=False)  # 里程碑金额
    due_date = Column(DateTime, nullable=True)  # 截止日期
    status = Column(SQLEnum(MilestoneStatusEnum), default=MilestoneStatusEnum.PENDING)
    submitted_at = Column(DateTime, nullable=True)  # 提交时间
    approved_at = Column(DateTime, nullable=True)  # 批准时间
    rejected_at = Column(DateTime, nullable=True)  # 拒绝时间
    rejection_reason = Column(Text, nullable=True)  # 拒绝原因
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    order = relationship("OrderDB", back_populates="milestones")
    escrows = relationship("EscrowDB", back_populates="milestone", cascade="all, delete-orphan")


# ==================== 支付托管 (Escrow) ====================

class EscrowDB(Base):
    """支付托管表"""
    __tablename__ = "escrows"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    milestone_id = Column(String, ForeignKey("milestones.id"), nullable=True)  # 关联的里程碑（可选）
    hirer_id = Column(String, nullable=False)  # 租赁者 ID
    employee_id = Column(String, ForeignKey("ai_employees.id"), nullable=False)
    owner_id = Column(String, nullable=False)  # 员工所有者 ID
    amount = Column(Float, nullable=False)  # 托管金额
    currency = Column(String, default="CNY")  # 货币
    status = Column(SQLEnum(EscrowStatusEnum), default=EscrowStatusEnum.PENDING)
    funding_deadline = Column(DateTime, nullable=True)  # 充值截止时间
    funded_at = Column(DateTime, nullable=True)  # 充值完成时间
    released_at = Column(DateTime, nullable=True)  # 释放时间
    refunded_at = Column(DateTime, nullable=True)  # 退款时间
    released_amount = Column(Float, default=0.0)  # 已释放金额
    refunded_amount = Column(Float, default=0.0)  # 已退款金额
    platform_fee = Column(Float, default=0.0)  # 平台费用
    owner_earning = Column(Float, default=0.0)  # 所有者收益
    payment_method = Column(String, nullable=True)  # 支付方式
    transaction_id = Column(String, nullable=True)  # 交易 ID
    notes = Column(Text, nullable=True)  # 备注
    metadata_ = Column(JSON, default=dict)  # 附加数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    order = relationship("OrderDB", back_populates="escrows")
    employee = relationship("AIEmployeeDB", back_populates="escrows")
    milestone = relationship("MilestoneDB", back_populates="escrows")
    disputes = relationship("DisputeDB", back_populates="escrow", cascade="all, delete-orphan")


class EscrowTransactionDB(Base):
    """托管交易记录表"""
    __tablename__ = "escrow_transactions"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    escrow_id = Column(String, ForeignKey("escrows.id"), nullable=False)
    transaction_type = Column(String, nullable=False)  # fund, release, refund
    amount = Column(Float, nullable=False)
    currency = Column(String, default="CNY")
    status = Column(String, default="pending")  # pending, completed, failed
    payment_method = Column(String, nullable=True)
    third_party_id = Column(String, nullable=True)  # 第三方支付 ID
    description = Column(Text, nullable=True)
    metadata_ = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    escrow = relationship("EscrowDB", backref="transactions")


# ==================== 消息系统 ====================

class ConversationDB(Base):
    """会话表"""
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    order_id = Column(String, ForeignKey("orders.id"), nullable=True)  # 关联的订单（可选）
    proposal_id = Column(String, ForeignKey("proposals.id"), nullable=True)  # 关联的提案（可选）
    participant_ids = Column(JSON, default=list)  # 参与者 ID 列表
    last_message_at = Column(DateTime, nullable=True)  # 最后消息时间
    last_message_preview = Column(String, nullable=True)  # 最后消息预览
    is_archived = Column(Boolean, default=False)  # 是否已归档
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    order = relationship("OrderDB", backref="conversations")
    proposal = relationship("ProposalDB", backref="conversations")
    messages = relationship("MessageDB", back_populates="conversation", cascade="all, delete-orphan")


class MessageDB(Base):
    """消息表"""
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    sender_id = Column(String, nullable=False)  # 发送者 ID
    message_type = Column(SQLEnum(MessageTypeEnum), default=MessageTypeEnum.TEXT)
    content = Column(Text, nullable=False)  # 消息内容
    attachments = Column(JSON, default=list)  # 附件列表
    is_read = Column(Boolean, default=False)  # 是否已读
    read_at = Column(DateTime, nullable=True)  # 读取时间
    edited_at = Column(DateTime, nullable=True)  # 编辑时间
    is_deleted = Column(Boolean, default=False)  # 是否已删除
    metadata_ = Column(JSON, default=dict)  # 附加数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    conversation = relationship("ConversationDB", back_populates="messages")


class NotificationDB(Base):
    """通知表"""
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    user_id = Column(String, nullable=False)  # 接收者 ID
    title = Column(String, nullable=False)  # 通知标题
    content = Column(Text, nullable=False)  # 通知内容
    notification_type = Column(String, nullable=False)  # 通知类型
    related_type = Column(String, nullable=True)  # 关联类型（order, proposal, message 等）
    related_id = Column(String, nullable=True)  # 关联 ID
    is_read = Column(Boolean, default=False)  # 是否已读
    read_at = Column(DateTime, nullable=True)  # 读取时间
    action_url = Column(String, nullable=True)  # 操作链接
    priority = Column(String, default="normal")  # normal, high, urgent
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    tenant = relationship("TenantDB", backref="notifications")


# ==================== 争议解决机制 ====================

class DisputeDB(Base):
    """争议表"""
    __tablename__ = "disputes"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    escrow_id = Column(String, ForeignKey("escrows.id"), nullable=True)  # 关联的托管
    opened_by = Column(String, nullable=False)  # 发起者 ID
    opened_by_role = Column(String, nullable=False)  # 发起者角色（hirer, owner）
    against_user_id = Column(String, nullable=False)  # 被投诉方 ID
    title = Column(String, nullable=False)  # 争议标题
    description = Column(Text, nullable=False)  # 争议描述
    dispute_type = Column(String, nullable=False)  # 争议类型
    status = Column(SQLEnum(DisputeStatusEnum), default=DisputeStatusEnum.OPEN)
    priority = Column(String, default="normal")  # normal, high, urgent
    evidence = Column(JSON, default=list)  # 证据列表
    desired_resolution = Column(Text, nullable=True)  # 期望的解决方案
    assigned_mediator_id = Column(String, nullable=True)  # 指派的调解员 ID
    resolution = Column(SQLEnum(DisputeResolutionEnum), nullable=True)  # 解决方式
    resolution_details = Column(Text, nullable=True)  # 解决方案详情
    refund_amount = Column(Float, nullable=True)  # 退款金额
    release_amount = Column(Float, nullable=True)  # 释放给所有者的金额
    closed_at = Column(DateTime, nullable=True)  # 关闭时间
    closed_by = Column(String, nullable=True)  # 关闭者 ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    order = relationship("OrderDB", back_populates="disputes")
    escrow = relationship("EscrowDB", back_populates="disputes")
    evidence_records = relationship("DisputeEvidenceDB", back_populates="dispute", cascade="all, delete-orphan")
    # files 关系由 file_models.add_file_relationships() 动态添加，避免循环依赖


class DisputeMessageDB(Base):
    """争议消息表 - 用于争议沟通"""
    __tablename__ = "dispute_messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    dispute_id = Column(String, ForeignKey("disputes.id"), nullable=False)
    sender_id = Column(String, nullable=False)
    sender_role = Column(String, nullable=False)  # hirer, owner, mediator, admin
    content = Column(Text, nullable=False)
    attachments = Column(JSON, default=list)
    is_internal = Column(Boolean, default=False)  # 是否内部消息（仅调解员可见）
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    dispute = relationship("DisputeDB", backref="messages")


class DisputeEvidenceDB(Base):
    """争议证据表"""
    __tablename__ = "dispute_evidence"

    id = Column(String, primary_key=True, default=generate_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    dispute_id = Column(String, ForeignKey("disputes.id"), nullable=False)
    submitted_by = Column(String, nullable=False)
    submitted_by_role = Column(String, nullable=False)  # hirer, owner
    evidence_type = Column(String, nullable=False)  # document, screenshot, log, etc.
    file_url = Column(String, nullable=False)  # 文件 URL
    file_name = Column(String, nullable=False)  # 文件名
    file_size = Column(Integer, nullable=True)  # 文件大小
    description = Column(Text, nullable=True)  # 描述
    is_verified = Column(Boolean, default=False)  # 是否已验证
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    dispute = relationship("DisputeDB", back_populates="evidence_records")


# 添加到 db_models 的关联关系
def add_p4_relationships():
    """添加 P4 模型关联关系到现有模型"""
    from .db_models import AIEmployeeDB, OrderDB, TenantDB
    from .p4_models import DisputeDB, EscrowDB, MilestoneDB

    # AIEmployeeDB 关联 - escrows
    if not hasattr(AIEmployeeDB, 'escrows'):
        AIEmployeeDB.escrows = relationship("EscrowDB", back_populates="employee", cascade="all, delete-orphan")

    # OrderDB 关联 - disputes, escrows, milestones
    if not hasattr(OrderDB, 'disputes'):
        OrderDB.disputes = relationship("DisputeDB", back_populates="order", cascade="all, delete-orphan")

    if not hasattr(OrderDB, 'escrows'):
        OrderDB.escrows = relationship("EscrowDB", back_populates="order", cascade="all, delete-orphan")

    if not hasattr(OrderDB, 'milestones'):
        OrderDB.milestones = relationship("MilestoneDB", back_populates="order", cascade="all, delete-orphan")

    # TenantDB 关联 - disputes (如果有需要)
    # 注意：DisputeDB 已经通过 tenant_id 外键关联到 TenantDB，但不需要 back_populates
