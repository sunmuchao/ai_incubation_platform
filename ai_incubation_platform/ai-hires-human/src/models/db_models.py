"""
数据库 ORM 模型。
"""
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class TaskDB(Base):
    """任务表。"""
    __tablename__ = "tasks"

    ai_employer_id: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    requirements: Mapped[str] = mapped_column(JSON, default="[]")
    interaction_type: Mapped[str] = mapped_column(String(20), default="digital")
    capability_gap: Mapped[str] = mapped_column(Text, default="")
    acceptance_criteria: Mapped[str] = mapped_column(JSON, default="[]")
    location_hint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    required_skills: Mapped[Dict] = mapped_column(JSON, default=dict)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    status: Mapped[str] = mapped_column(String(20), default="published", index=True)
    reward_amount: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    reward_currency: Mapped[str] = mapped_column(String(3), default="CNY")
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    worker_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    delivery_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    delivery_attachments: Mapped[str] = mapped_column(JSON, default="[]")
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    callback_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 人工兜底字段
    review_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    appeal_count: Mapped[int] = mapped_column(Integer, default=0)
    is_disputed: Mapped[bool] = mapped_column(Boolean, default=False)

    # 反作弊字段
    submission_count: Mapped[int] = mapped_column(Integer, default=0)
    last_submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    cheating_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    cheating_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class PaymentTransactionDB(Base):
    """支付交易表。"""
    __tablename__ = "payment_transactions"

    transaction_type: Mapped[str] = mapped_column(String(50))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="CNY")
    payer_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    payee_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    task_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    payment_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    external_transaction_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fee_amount: Mapped[float] = mapped_column(Float, default=0.0)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class WalletDB(Base):
    """用户钱包表。"""
    __tablename__ = "wallets"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    frozen_balance: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="CNY")


class AntiCheatHashDB(Base):
    """反作弊全局哈希表。"""
    __tablename__ = "anti_cheat_hashes"

    content_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), index=True)
    worker_id: Mapped[str] = mapped_column(String(255), index=True)


class WorkerSubmissionDB(Base):
    """工人提交记录表。"""
    __tablename__ = "worker_submissions"

    worker_id: Mapped[str] = mapped_column(String(255), index=True)
    task_id: Mapped[str] = mapped_column(String(36), index=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class WorkerProfileDB(Base):
    """工人能力画像表（与孵化器其他项目联动）。"""
    __tablename__ = "worker_profiles"

    worker_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    skills: Mapped[Dict] = mapped_column(JSON, default=dict)  # 技能标签与等级
    completed_tasks: Mapped[int] = mapped_column(Integer, default=0)  # 完成任务数
    success_rate: Mapped[float] = mapped_column(Float, default=1.0)  # 任务成功率
    average_rating: Mapped[float] = mapped_column(Float, default=5.0)  # 平均评分
    total_earnings: Mapped[float] = mapped_column(Float, default=0.0)  # 总收入
    level: Mapped[int] = mapped_column(Integer, default=1)  # 用户等级
    tags: Mapped[str] = mapped_column(JSON, default="[]")  # 自定义标签
    external_profile_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # 外部系统画像 ID
    extra_data: Mapped[Dict] = mapped_column(JSON, default=dict)  # 扩展字段（避免使用 metadata 保留字）


class EscrowTransactionDB(Base):
    """Escrow 资金托管交易表。"""
    __tablename__ = "escrow_transactions"

    escrow_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), index=True)
    ai_employer_id: Mapped[str] = mapped_column(String(255), index=True)
    worker_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)

    # 金额信息
    principal_amount: Mapped[float] = mapped_column(Float)  # 本金
    platform_fee: Mapped[float] = mapped_column(Float, default=0.0)  # 平台服务费
    total_amount: Mapped[float] = mapped_column(Float)  # 总金额
    currency: Mapped[str] = mapped_column(String(3), default="CNY")

    # 状态
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)

    # 时间戳
    funded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 争议相关
    dispute_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dispute_resolution: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    split_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)
    released_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    refunded_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class DeviceFingerprintDB(Base):
    """设备指纹表。"""
    __tablename__ = "device_fingerprints"

    fingerprint: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)

    # 设备信息
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 max length
    screen_resolution: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    canvas_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    webgl_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # 时间戳
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)


class IPRecordDB(Base):
    """IP 地址记录表。"""
    __tablename__ = "ip_records"

    ip_address: Mapped[str] = mapped_column(String(45), primary_key=True)

    # 地理位置信息
    country: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    isp: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # 风险标记
    is_proxy: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    is_vpn: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    is_tor: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    is_datacenter: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False)
    blacklist_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 统计信息
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)


class BehavioralEventDB(Base):
    """用户行为事件表。"""
    __tablename__ = "behavioral_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    task_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # 事件元数据（JSON）
    event_metadata: Mapped[Dict] = mapped_column(JSON, default=dict)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, index=True)


class TaskTemplateDB(Base):
    """任务模板表。"""
    __tablename__ = "task_templates"

    template_name: Mapped[str] = mapped_column(String(100), primary_key=True)

    # 模板内容
    title_template: Mapped[str] = mapped_column(Text)
    description_template: Mapped[str] = mapped_column(Text)
    capability_gap: Mapped[str] = mapped_column(Text)
    interaction_type: Mapped[str] = mapped_column(String(20), default="digital")
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    reward_amount: Mapped[float] = mapped_column(Float, default=0.0)

    # JSON 字段
    acceptance_criteria: Mapped[Dict] = mapped_column(JSON, default="[]")
    requirements: Mapped[Dict] = mapped_column(JSON, default="[]")
    required_skills: Mapped[Dict] = mapped_column(JSON, default=dict)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class GoldenStandardTestDB(Base):
    """黄金标准测试表（任务级别）。"""
    __tablename__ = "golden_standard_tests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # 重写 Base 的 id
    test_id: Mapped[str] = mapped_column(String(36), index=True, unique=True)
    task_id: Mapped[str] = mapped_column(String(36), index=True)
    ai_employer_id: Mapped[str] = mapped_column(String(255), index=True)

    # 测试配置
    test_name: Mapped[str] = mapped_column(String(255))
    test_description: Mapped[str] = mapped_column(Text)
    test_type: Mapped[str] = mapped_column(String(50), default="multiple_choice")  # multiple_choice, boolean, scale, text_match

    # 测试题目（JSON 格式存储多个题目）
    questions: Mapped[Dict] = mapped_column(JSON, default=list)  # [{"question_id": "q1", "question": "...", "options": [...], "correct_answer": "...", "points": 1}]

    # 通过标准
    passing_score: Mapped[float] = mapped_column(Float, default=80.0)  # 通过分数百分比
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)  # 最大尝试次数

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)


class WorkerTestAttemptDB(Base):
    """工人测试尝试记录表。"""
    __tablename__ = "worker_test_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # 重写 Base 的 id
    attempt_id: Mapped[str] = mapped_column(String(36), index=True, unique=True)
    test_id: Mapped[str] = mapped_column(String(36), index=True)
    task_id: Mapped[str] = mapped_column(String(36), index=True)
    worker_id: Mapped[str] = mapped_column(String(255), index=True)

    # 尝试信息
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)  # 第几次尝试

    # 答题结果（JSON 格式存储每道题的答案）
    answers: Mapped[Dict] = mapped_column(JSON, default=dict)  # {"q1": "answer_a", "q2": "answer_b"}
    score: Mapped[float] = mapped_column(Float, default=0.0)  # 得分
    max_score: Mapped[float] = mapped_column(Float, default=100.0)  # 满分
    percentage: Mapped[float] = mapped_column(Float, default=0.0)  # 得分百分比

    # 判定结果
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 时间戳
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkerCertificationDB(Base):
    """工人资格认证表。"""
    __tablename__ = "worker_certifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # 重写 Base 的 id
    certification_id: Mapped[str] = mapped_column(String(36), index=True, unique=True)
    worker_id: Mapped[str] = mapped_column(String(255), index=True)

    # 认证信息
    certification_type: Mapped[str] = mapped_column(String(100))  # 认证类型（如 data_annotation, translation, survey 等）
    certification_name: Mapped[str] = mapped_column(String(255))
    certification_level: Mapped[str] = mapped_column(String(20), default="bronze")  # bronze, silver, gold, diamond

    # 认证状态
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, expired, revoked
    score: Mapped[float] = mapped_column(Float, default=0.0)  # 认证考试得分

    # 有效期
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 颁发者
    issued_by: Mapped[str] = mapped_column(String(255), default="system")  # system 或具体管理员 ID

    # 扩展信息
    cert_data: Mapped[Dict] = mapped_column(JSON, default=dict)  # 扩展信息（避免使用 metadata 保留字）


# ===== v1.4.0 新增：多语言支持模型 =====
class UserLanguagePreferenceDB(Base):
    """用户语言偏好表。"""
    __tablename__ = "user_language_preferences"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True, unique=True)

    # 语言偏好
    preferred_language: Mapped[str] = mapped_column(String(10), default="zh_CN")
    secondary_language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # 是否自动检测语言
    auto_detect_language: Mapped[bool] = mapped_column(Boolean, default=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)


class TaskTranslationDB(Base):
    """任务翻译表（支持多语言任务内容）。"""
    __tablename__ = "task_translations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), index=True)

    # 语言代码
    language_code: Mapped[str] = mapped_column(String(10), index=True)

    # 翻译内容
    translated_title: Mapped[str] = mapped_column(String(500))
    translated_description: Mapped[str] = mapped_column(Text)
    translated_requirements: Mapped[Dict] = mapped_column(JSON, default=list)
    translated_acceptance_criteria: Mapped[Dict] = mapped_column(JSON, default=list)

    # 翻译状态
    is_machine_translated: Mapped[bool] = mapped_column(Boolean, default=True)
    is_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)


class MessageTemplateDB(Base):
    """多语言消息模板表（通知、邮件等）。"""
    __tablename__ = "message_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    template_key: Mapped[str] = mapped_column(String(100), index=True)  # 如 "task_assigned"

    # 语言代码
    language_code: Mapped[str] = mapped_column(String(10), index=True)

    # 模板内容
    subject_template: Mapped[str] = mapped_column(String(500))
    body_template: Mapped[str] = mapped_column(Text)

    # 可用变量列表（JSON）
    available_variables: Mapped[Dict] = mapped_column(JSON, default=list)  # ["{worker_name}", "{task_title}"]

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)


class EmployerProfileDB(Base):
    """雇主画像表。"""
    __tablename__ = "employer_profiles"

    employer_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # 统计信息
    total_tasks_posted: Mapped[int] = mapped_column(Integer, default=0)
    total_tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    total_amount_paid: Mapped[float] = mapped_column(Float, default=0.0)
    average_worker_rating: Mapped[float] = mapped_column(Float, default=5.0)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)
