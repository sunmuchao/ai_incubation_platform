"""
法律服务支持数据模型。

v1.21.0 新增：法律法规支持功能
- 合同模板库（劳务/保密/知识产权）
- 法务咨询（在线咨询/文书审核）
- 权益保护（维权援助/投诉举报）
- 税务规划（个税计算/发票管理）
- 合规检查（任务合规性自动检查）
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ========== 合同模板库相关模型 ==========

class ContractType(str, Enum):
    """合同类型。"""
    LABOR = "labor"  # 劳务合同
    NDA = "nda"  # 保密协议
    IP_ASSIGNMENT = "ip_assignment"  # 知识产权转让协议
    SERVICE = "service"  # 服务协议
    FREELANCE = "freelance"  # 自由职业者合同
    CONSULTING = "consulting"  # 咨询合同


class ContractParty(str, Enum):
    """合同当事方。"""
    EMPLOYER = "employer"  # 雇主
    WORKER = "worker"  # 工人
    PLATFORM = "platform"  # 平台


class ContractTemplate(BaseModel):
    """合同模板。"""
    template_id: str
    name: str
    contract_type: ContractType
    description: str

    # 模板内容（支持变量替换）
    content: str  # HTML 或 Markdown 格式，包含 {variable} 占位符

    # 适用场景
    applicable_scenarios: List[str] = Field(default_factory=list)

    # 必填变量列表
    required_variables: List[str] = Field(default_factory=list)

    # 可选变量列表
    optional_variables: List[str] = Field(default_factory=list)

    # 法律管辖区
    jurisdictions: List[str] = Field(default_factory=list)  # 如 ["CN-BJ", "CN-SH", "US-CA"]

    # 版本
    version: str = "1.0"

    # 状态
    is_active: bool = True

    # 使用次数统计
    usage_count: int = 0

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class GeneratedContract(BaseModel):
    """生成的合同实例。"""
    contract_id: str
    template_id: str
    contract_type: ContractType

    # 当事方
    employer_id: str
    worker_id: str
    task_id: Optional[str] = None  # 关联的任务 ID

    # 生成的合同内容（变量已替换）
    content: str

    # 合同金额
    contract_value: float = 0.0
    currency: str = "CNY"

    # 合同期限
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # 状态
    status: str = "draft"  # draft, pending_signature, signed, active, completed, terminated

    # 签署信息
    employer_signed_at: Optional[datetime] = None
    worker_signed_at: Optional[datetime] = None

    # 管辖区
    jurisdiction: str = ""

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ContractSignRequest(BaseModel):
    """合同签署请求。"""
    contract_id: str
    party: ContractParty  # 哪一方签署


# ========== 法务咨询相关模型 ==========

class LegalConsultationType(str, Enum):
    """法律咨询类型。"""
    CONTRACT_REVIEW = "contract_review"  # 合同审核
    DISPUTE_ADVICE = "dispute_advice"  # 争议咨询
    COMPLIANCE_CHECK = "compliance_check"  # 合规检查
    IP_ADVICE = "ip_advice"  # 知识产权咨询
    TAX_ADVICE = "tax_advice"  # 税务咨询
    LABOR_LAW = "labor_law"  # 劳动法咨询
    OTHER = "other"  # 其他


class ConsultationStatus(str, Enum):
    """咨询状态。"""
    PENDING = "pending"  # 待处理
    IN_PROGRESS = "in_progress"  # 处理中
    WAITING_CUSTOMER = "waiting_customer"  # 等待客户补充信息
    COMPLETED = "completed"  # 已完成
    CLOSED = "closed"  # 已关闭


class LegalConsultation(BaseModel):
    """法律咨询。"""
    consultation_id: str
    user_id: str
    user_type: str  # employer or worker

    # 咨询类型
    consultation_type: LegalConsultationType

    # 标题和描述
    title: str
    description: str

    # 相关附件（合同、证据等）
    attachments: List[str] = Field(default_factory=list)  # 文件 URL 列表

    # 关联的业务对象
    related_task_id: Optional[str] = None
    related_contract_id: Optional[str] = None
    related_dispute_id: Optional[str] = None

    # 指派的律师
    assigned_lawyer_id: Optional[str] = None
    assigned_lawyer_name: Optional[str] = None

    # 状态
    status: ConsultationStatus = ConsultationStatus.PENDING

    # 优先级
    priority: str = "normal"  # low, normal, high, urgent

    # 咨询回复
    lawyer_response: Optional[str] = None
    response_at: Optional[datetime] = None

    # 用户补充信息
    customer_additional_info: List[Dict] = Field(default_factory=list)

    # 满意度评分
    satisfaction_score: Optional[int] = None  # 1-5
    satisfaction_comment: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ConsultationMessage(BaseModel):
    """咨询消息（对话）。"""
    message_id: str
    consultation_id: str
    sender_id: str
    sender_type: str  # user, lawyer, system

    # 消息内容
    content: str
    attachments: List[str] = Field(default_factory=list)

    # 是否已读
    is_read: bool = False

    created_at: Optional[datetime] = None


# ========== 权益保护相关模型 ==========

class RightsViolationType(str, Enum):
    """权益侵害类型。"""
    UNPAID_WORK = "unpaid_work"  # 拖欠工资
    CONTRACT_VIOLATION = "contract_violation"  # 违约
    IP_INFRINGEMENT = "ip_infringement"  # 知识产权侵权
    HARASSMENT = "harassment"  # 骚扰
    DISCRIMINATION = "discrimination"  # 歧视
    FRAUD = "fraud"  # 诈骗
    PRIVACY_VIOLATION = "privacy_violation"  # 隐私侵犯
    OTHER = "other"  # 其他


class ComplaintStatus(str, Enum):
    """投诉状态。"""
    SUBMITTED = "submitted"  # 已提交
    UNDER_REVIEW = "under_review"  # 审核中
    ACCEPTED = "accepted"  # 已受理
    INVESTIGATING = "investigating"  # 调查取证中
    MEDIATION = "mediation"  # 调解中
    ARBITRATION = "arbitration"  # 仲裁中
    LITIGATION = "litigation"  # 诉讼中
    RESOLVED = "resolved"  # 已解决
    REJECTED = "rejected"  # 已驳回
    WITHDRAWN = "withdrawn"  # 已撤回


class RightsComplaint(BaseModel):
    """权益保护投诉。"""
    complaint_id: str
    complainant_id: str  # 投诉人
    complainant_type: str  # employer or worker

    # 被投诉方
    respondent_id: str
    respondent_type: str

    # 投诉类型
    violation_type: RightsViolationType

    # 标题和描述
    title: str
    description: str

    # 详细说明
    detailed_statement: str = ""

    # 证据材料
    evidence: List[Dict] = Field(default_factory=list)
    # [{"type": "document", "url": "...", "description": "..."}]

    # 诉求
    demands: List[str] = Field(default_factory=list)

    # 涉及金额
    involved_amount: Optional[float] = None
    currency: str = "CNY"

    # 关联的业务对象
    related_task_id: Optional[str] = None
    related_contract_id: Optional[str] = None

    # 状态
    status: ComplaintStatus = ComplaintStatus.SUBMITTED

    # 处理进度
    progress: int = 0  # 0-100
    current_stage: str = "submitted"

    # 处理人员
    assigned_mediator_id: Optional[str] = None
    assigned_mediator_name: Optional[str] = None

    # 处理结果
    resolution_summary: Optional[str] = None
    resolution_date: Optional[datetime] = None

    # 赔偿/处罚
    compensation_amount: Optional[float] = None
    penalty_amount: Optional[float] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ComplaintEvidence(BaseModel):
    """投诉证据。"""
    evidence_id: str
    complaint_id: str
    evidence_type: str  # document, image, video, audio, chat_log, email, etc.

    # 文件信息
    file_url: str
    file_name: str
    file_size: Optional[int] = None

    # 描述
    description: str = ""

    # 提交人
    submitted_by: str
    submitted_at: Optional[datetime] = None

    # 验证状态
    is_verified: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None


# ========== 税务规划相关模型 ==========

class TaxType(str, Enum):
    """税种。"""
    INDIVIDUAL_INCOME_TAX = "individual_income_tax"  # 个人所得税
    VAT = "vat"  # 增值税
    BUSINESS_TAX = "business_tax"  # 营业税
    OTHER = "other"  # 其他


class TaxBracket(BaseModel):
    """税率档位。"""
    min_amount: float
    max_amount: Optional[float]  # None 表示无上限
    rate: float  # 税率
    quick_deduction: float  # 速算扣除数


class TaxCalculationRequest(BaseModel):
    """税务计算请求。"""
    income: float  # 收入金额
    income_type: str = "labor"  # labor, salary, bonus, royalty, etc.
    region: str = "CN"  # 管辖区
    deductions: List[Dict] = Field(default_factory=list)
    # [{"type": "social_insurance", "amount": 1000}, ...]


class TaxCalculationResult(BaseModel):
    """税务计算结果。"""
    gross_income: float  # 总收入
    taxable_income: float  # 应纳税所得额
    tax_amount: float  # 应纳税额
    net_income: float  # 税后收入
    effective_tax_rate: float  # 实际税率

    # 各税种明细
    tax_breakdown: List[Dict] = Field(default_factory=list)

    # 计算详情
    calculation_details: Dict = Field(default_factory=dict)

    # 减免信息
    deductions_applied: List[Dict] = Field(default_factory=list)


class Invoice(BaseModel):
    """发票。"""
    invoice_id: str
    invoice_number: str  # 发票号码
    invoice_code: str  # 发票代码

    # 开票信息
    seller_name: str
    seller_tax_id: str
    seller_address: str
    seller_phone: str
    seller_bank_account: str

    buyer_name: str
    buyer_tax_id: str
    buyer_address: str
    buyer_phone: str
    buyer_bank_account: str

    # 发票内容
    invoice_type: str  # electronic, paper, special, normal
    item_name: str
    amount: float
    tax_amount: float
    total_amount: float

    # 状态
    status: str = "draft"  # draft, issued, delivered, reimbursed

    # 关联
    related_task_id: Optional[str] = None
    related_contract_id: Optional[str] = None

    # 时间
    issue_date: Optional[datetime] = None

    created_at: Optional[datetime] = None


class TaxFiling(BaseModel):
    """税务申报。"""
    filing_id: str
    taxpayer_id: str
    taxpayer_type: str  # individual, enterprise

    # 申报期间
    period_start: datetime
    period_end: datetime

    # 申报内容
    total_income: float
    taxable_income: float
    tax_payable: float
    tax_paid: float
    tax_refund: float

    # 申报状态
    status: str = "draft"  # draft, submitted, accepted, rejected

    # 申报结果
    submission_date: Optional[datetime] = None
    acceptance_date: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ========== 合规检查相关模型 ==========

class ComplianceCategory(str, Enum):
    """合规类别。"""
    LABOR_LAW = "labor_law"  # 劳动法合规
    TAX_LAW = "tax_law"  # 税法合规
    IP_LAW = "ip_law"  # 知识产权合规
    DATA_PRIVACY = "data_privacy"  # 数据隐私合规
    CONSUMER_PROTECTION = "consumer_protection"  # 消费者保护
    ANTI_FRAUD = "anti_fraud"  # 反欺诈
    INDUSTRY_SPECIFIC = "industry_specific"  # 行业特定合规


class ComplianceRiskLevel(str, Enum):
    """合规风险等级。"""
    LOW = "low"  # 低风险
    MEDIUM = "medium"  # 中风险
    HIGH = "high"  # 高风险
    CRITICAL = "critical"  # 严重风险


class ComplianceCheckResult(BaseModel):
    """合规检查结果。"""
    check_id: str

    # 检查对象
    object_type: str  # task, contract, user, etc.
    object_id: str

    # 检查类别
    categories_checked: List[ComplianceCategory] = Field(default_factory=list)

    # 总体结果
    overall_status: str = "compliant"  # compliant, non_compliant, needs_review
    overall_risk_level: ComplianceRiskLevel = ComplianceRiskLevel.LOW

    # 各问题
    issues: List[Dict] = Field(default_factory=list)
    # [{
    #   "category": "labor_law",
    #   "severity": "high",
    #   "description": "任务报酬低于最低工资标准",
    #   "suggestion": "建议将报酬调整为不低于每小时 XX 元",
    #   "regulation_reference": "《劳动法》第 XX 条"
    # }]

    # 合规建议
    recommendations: List[str] = Field(default_factory=list)

    # 法规引用
    regulations_referenced: List[str] = Field(default_factory=list)

    # 检查结果摘要
    summary: str = ""

    checked_at: Optional[datetime] = None
    checked_by: Optional[str] = None


class ComplianceRule(BaseModel):
    """合规规则。"""
    rule_id: str
    name: str
    description: str

    # 规则类型
    category: ComplianceCategory

    # 适用管辖区
    jurisdictions: List[str] = Field(default_factory=list)

    # 规则内容（可以是正则、表达式或代码）
    rule_expression: str

    # 违规判定条件
    violation_condition: str

    # 风险等级
    default_risk_level: ComplianceRiskLevel

    # 建议模板
    suggestion_template: str = ""

    # 法规引用
    regulation_reference: str = ""

    # 状态
    is_active: bool = True

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ========== 律师/法务专家相关模型 ==========

class LawyerProfile(BaseModel):
    """律师档案。"""
    lawyer_id: str
    name: str
    title: str  # 职称
    law_firm: Optional[str] = None  # 律所

    # 专业领域
    practice_areas: List[str] = Field(default_factory=list)
    # ["劳动法", "知识产权", "合同法", "税法", ...]

    # 执业信息
    license_number: str
    license_jurisdiction: str
    years_of_experience: int = 0

    # 简介
    bio: str = ""

    # 评分
    rating: float = 5.0
    total_consultations: int = 0
    total_cases: int = 0

    # 收费标准
    consultation_fee_per_hour: float = 0.0
    is_available_for_consultation: bool = True

    # 可服务管辖区
    served_jurisdictions: List[str] = Field(default_factory=list)

    created_at: Optional[datetime] = None


# ========== 响应模型 ==========

class ContractTemplateList(BaseModel):
    """合同模板列表。"""
    templates: List[ContractTemplate]
    total: int
    skip: int
    limit: int


class GeneratedContractResponse(BaseModel):
    """生成合同响应。"""
    contract_id: str
    template_id: str
    contract_type: str
    status: str
    employer_id: str
    worker_id: str
    task_id: Optional[str]
    contract_value: float
    currency: str
    created_at: Optional[datetime]


class LegalConsultationResponse(BaseModel):
    """法律咨询响应。"""
    consultation_id: str
    user_id: str
    consultation_type: str
    title: str
    status: str
    priority: str
    assigned_lawyer_name: Optional[str]
    created_at: Optional[datetime]


class RightsComplaintResponse(BaseModel):
    """权益投诉响应。"""
    complaint_id: str
    complainant_id: str
    respondent_id: str
    violation_type: str
    title: str
    status: str
    progress: int
    assigned_mediator_name: Optional[str]
    created_at: Optional[datetime]


class TaxCalculationResponse(BaseModel):
    """税务计算响应。"""
    gross_income: float
    taxable_income: float
    tax_amount: float
    net_income: float
    effective_tax_rate: float
    breakdown: List[Dict]


class ComplianceCheckResponse(BaseModel):
    """合规检查响应。"""
    check_id: str
    object_type: str
    object_id: str
    overall_status: str
    overall_risk_level: str
    issues_count: int
    recommendations_count: int
    summary: str
    checked_at: Optional[datetime]


class LegalServicesSummary(BaseModel):
    """法律服务摘要。"""
    user_id: str
    active_contracts: int
    active_consultations: int
    active_complaints: int
    total_tax_paid: float
    pending_invoices: int
    compliance_issues: int
