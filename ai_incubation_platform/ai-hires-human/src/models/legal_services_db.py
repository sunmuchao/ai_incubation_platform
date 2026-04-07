"""
法律服务 ORM 数据库模型。

v1.21.0 新增：法律法规支持功能
"""
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


# ========== 合同模板库相关模型 ==========

class ContractTemplateDB(Base):
    """合同模板表。"""
    __tablename__ = "contract_templates"

    name: Mapped[str] = mapped_column(String(255))
    contract_type: Mapped[str] = mapped_column(String(50))  # labor, nda, ip_assignment, etc.
    description: Mapped[str] = mapped_column(Text)

    # 模板内容
    content: Mapped[str] = mapped_column(Text)  # HTML 或 Markdown 格式

    # 适用场景
    applicable_scenarios: Mapped[Dict] = mapped_column(JSON, default=list)

    # 必填变量列表
    required_variables: Mapped[Dict] = mapped_column(JSON, default=list)

    # 可选变量列表
    optional_variables: Mapped[Dict] = mapped_column(JSON, default=list)

    # 法律管辖区
    jurisdictions: Mapped[Dict] = mapped_column(JSON, default=list)

    # 版本
    version: Mapped[str] = mapped_column(String(20), default="1.0")

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # 使用次数统计
    usage_count: Mapped[int] = mapped_column(Integer, default=0)


class GeneratedContractDB(Base):
    """生成的合同实例表。"""
    __tablename__ = "generated_contracts"

    template_id: Mapped[str] = mapped_column(String(36), index=True)
    contract_type: Mapped[str] = mapped_column(String(50))

    # 当事方
    employer_id: Mapped[str] = mapped_column(String(255), index=True)
    worker_id: Mapped[str] = mapped_column(String(255), index=True)
    task_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # 生成的合同内容
    content: Mapped[str] = mapped_column(Text)

    # 合同金额
    contract_value: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="CNY")

    # 合同期限
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 状态
    status: Mapped[str] = mapped_column(String(50), default="draft", index=True)

    # 签署信息
    employer_signed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    worker_signed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 管辖区
    jurisdiction: Mapped[str] = mapped_column(String(100), default="")


# ========== 法务咨询相关模型 ==========

class LegalConsultationDB(Base):
    """法律咨询表。"""
    __tablename__ = "legal_consultations"

    user_id: Mapped[str] = mapped_column(String(255), index=True)
    user_type: Mapped[str] = mapped_column(String(20))  # employer or worker

    # 咨询类型
    consultation_type: Mapped[str] = mapped_column(String(50))

    # 标题和描述
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)

    # 相关附件
    attachments: Mapped[Dict] = mapped_column(JSON, default=list)

    # 关联的业务对象
    related_task_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    related_contract_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    related_dispute_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # 指派的律师
    assigned_lawyer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    assigned_lawyer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # 状态
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)

    # 优先级
    priority: Mapped[str] = mapped_column(String(20), default="normal")

    # 咨询回复
    lawyer_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 用户补充信息
    customer_additional_info: Mapped[Dict] = mapped_column(JSON, default=list)

    # 满意度评分
    satisfaction_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    satisfaction_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ConsultationMessageDB(Base):
    """咨询消息表。"""
    __tablename__ = "consultation_messages"

    consultation_id: Mapped[str] = mapped_column(String(36), index=True)
    sender_id: Mapped[str] = mapped_column(String(255), index=True)
    sender_type: Mapped[str] = mapped_column(String(20))  # user, lawyer, system

    # 消息内容
    content: Mapped[str] = mapped_column(Text)
    attachments: Mapped[Dict] = mapped_column(JSON, default=list)

    # 是否已读
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)


# ========== 权益保护相关模型 ==========

class RightsComplaintDB(Base):
    """权益保护投诉表。"""
    __tablename__ = "rights_complaints"

    complainant_id: Mapped[str] = mapped_column(String(255), index=True)
    complainant_type: Mapped[str] = mapped_column(String(20))  # employer or worker

    # 被投诉方
    respondent_id: Mapped[str] = mapped_column(String(255), index=True)
    respondent_type: Mapped[str] = mapped_column(String(20))

    # 投诉类型
    violation_type: Mapped[str] = mapped_column(String(50))

    # 标题和描述
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)

    # 详细说明
    detailed_statement: Mapped[str] = mapped_column(Text, default="")

    # 证据材料
    evidence: Mapped[Dict] = mapped_column(JSON, default=list)

    # 诉求
    demands: Mapped[Dict] = mapped_column(JSON, default=list)

    # 涉及金额
    involved_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="CNY")

    # 关联的业务对象
    related_task_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    related_contract_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # 状态
    status: Mapped[str] = mapped_column(String(50), default="submitted", index=True)

    # 处理进度
    progress: Mapped[int] = mapped_column(Integer, default=0)
    current_stage: Mapped[str] = mapped_column(String(50), default="submitted")

    # 处理人员
    assigned_mediator_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    assigned_mediator_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # 处理结果
    resolution_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolution_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 赔偿/处罚
    compensation_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    penalty_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class ComplaintEvidenceDB(Base):
    """投诉证据表。"""
    __tablename__ = "complaint_evidence"

    complaint_id: Mapped[str] = mapped_column(String(36), index=True)
    evidence_type: Mapped[str] = mapped_column(String(50))  # document, image, video, etc.

    # 文件信息
    file_url: Mapped[str] = mapped_column(Text)
    file_name: Mapped[str] = mapped_column(String(255))
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 描述
    description: Mapped[str] = mapped_column(Text, default="")

    # 提交人
    submitted_by: Mapped[str] = mapped_column(String(255))

    # 验证状态
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


# ========== 税务规划相关模型 ==========

class InvoiceDB(Base):
    """发票表。"""
    __tablename__ = "invoices"

    invoice_number: Mapped[str] = mapped_column(String(100), index=True)
    invoice_code: Mapped[str] = mapped_column(String(100))

    # 卖方信息
    seller_name: Mapped[str] = mapped_column(String(255))
    seller_tax_id: Mapped[str] = mapped_column(String(100))
    seller_address: Mapped[str] = mapped_column(Text)
    seller_phone: Mapped[str] = mapped_column(String(50))
    seller_bank_account: Mapped[str] = mapped_column(String(100))

    # 买方信息
    buyer_name: Mapped[str] = mapped_column(String(255))
    buyer_tax_id: Mapped[str] = mapped_column(String(100))
    buyer_address: Mapped[str] = mapped_column(Text)
    buyer_phone: Mapped[str] = mapped_column(String(50))
    buyer_bank_account: Mapped[str] = mapped_column(String(100))

    # 发票内容
    invoice_type: Mapped[str] = mapped_column(String(20))  # electronic, paper, etc.
    item_name: Mapped[str] = mapped_column(String(255))
    amount: Mapped[float] = mapped_column(Float)
    tax_amount: Mapped[float] = mapped_column(Float)
    total_amount: Mapped[float] = mapped_column(Float)

    # 状态
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)

    # 关联
    related_task_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    related_contract_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # 时间
    issue_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class TaxFilingDB(Base):
    """税务申报表。"""
    __tablename__ = "tax_filings"

    taxpayer_id: Mapped[str] = mapped_column(String(255), index=True)
    taxpayer_type: Mapped[str] = mapped_column(String(20))  # individual, enterprise

    # 申报期间
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # 申报内容
    total_income: Mapped[float] = mapped_column(Float)
    taxable_income: Mapped[float] = mapped_column(Float)
    tax_payable: Mapped[float] = mapped_column(Float)
    tax_paid: Mapped[float] = mapped_column(Float)
    tax_refund: Mapped[float] = mapped_column(Float)

    # 申报状态
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)

    # 申报结果
    submission_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    acceptance_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ========== 合规检查相关模型 ==========

class ComplianceCheckDB(Base):
    """合规检查结果表。"""
    __tablename__ = "compliance_checks"

    # 检查对象
    object_type: Mapped[str] = mapped_column(String(50))  # task, contract, user, etc.
    object_id: Mapped[str] = mapped_column(String(255), index=True)

    # 检查类别
    categories_checked: Mapped[Dict] = mapped_column(JSON, default=list)

    # 总体结果
    overall_status: Mapped[str] = mapped_column(String(50), default="compliant", index=True)
    overall_risk_level: Mapped[str] = mapped_column(String(20), default="low")

    # 问题列表
    issues: Mapped[Dict] = mapped_column(JSON, default=list)

    # 合规建议
    recommendations: Mapped[Dict] = mapped_column(JSON, default=list)

    # 法规引用
    regulations_referenced: Mapped[Dict] = mapped_column(JSON, default=list)

    # 检查结果摘要
    summary: Mapped[str] = mapped_column(Text, default="")

    checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    checked_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class ComplianceRuleDB(Base):
    """合规规则表。"""
    __tablename__ = "compliance_rules"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)

    # 规则类型
    category: Mapped[str] = mapped_column(String(50))

    # 适用管辖区
    jurisdictions: Mapped[Dict] = mapped_column(JSON, default=list)

    # 规则内容
    rule_expression: Mapped[str] = mapped_column(Text)

    # 违规判定条件
    violation_condition: Mapped[str] = mapped_column(Text)

    # 风险等级
    default_risk_level: Mapped[str] = mapped_column(String(20), default="medium")

    # 建议模板
    suggestion_template: Mapped[str] = mapped_column(Text, default="")

    # 法规引用
    regulation_reference: Mapped[str] = mapped_column(Text, default="")

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


# ========== 律师/法务专家相关模型 ==========

class LawyerProfileDB(Base):
    """律师档案表。"""
    __tablename__ = "lawyer_profiles"

    name: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(100))  # 职称
    law_firm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # 专业领域
    practice_areas: Mapped[Dict] = mapped_column(JSON, default=list)

    # 执业信息
    license_number: Mapped[str] = mapped_column(String(100))
    license_jurisdiction: Mapped[str] = mapped_column(String(100))
    years_of_experience: Mapped[int] = mapped_column(Integer, default=0)

    # 简介
    bio: Mapped[str] = mapped_column(Text, default="")

    # 评分
    rating: Mapped[float] = mapped_column(Float, default=5.0)
    total_consultations: Mapped[int] = mapped_column(Integer, default=0)
    total_cases: Mapped[int] = mapped_column(Integer, default=0)

    # 收费标准
    consultation_fee_per_hour: Mapped[float] = mapped_column(Float, default=0.0)
    is_available_for_consultation: Mapped[bool] = mapped_column(Boolean, default=True)

    # 可服务管辖区
    served_jurisdictions: Mapped[Dict] = mapped_column(JSON, default=list)
