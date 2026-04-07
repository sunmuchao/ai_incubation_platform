"""
法律服务支持 API。

v1.21.0 新增：法律法规支持功能
- 合同模板库（劳务/保密/知识产权）
- 法务咨询（在线咨询/文书审核）
- 权益保护（维权援助/投诉举报）
- 税务规划（个税计算/发票管理）
- 合规检查（任务合规性自动检查）
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.legal_services import (
    ContractType,
    ContractParty,
    LegalConsultationType,
    ConsultationStatus,
    RightsViolationType,
    ComplaintStatus,
    ComplianceCategory,
    TaxCalculationRequest,
)
from services.legal_services_service import legal_services_service

router = APIRouter(prefix="/api/legal", tags=["legal_services"])


# ========== 合同模板库相关 API ==========

class ContractTemplateListItem(BaseModel):
    """合同模板列表项。"""
    template_id: str
    name: str
    contract_type: str
    description: str
    applicable_scenarios: List[str]
    usage_count: int
    version: str


class ContractTemplateListResponse(BaseModel):
    """合同模板列表响应。"""
    templates: List[ContractTemplateListItem]
    total: int
    skip: int
    limit: int


class ContractTemplateDetailResponse(BaseModel):
    """合同模板详情响应。"""
    template_id: str
    name: str
    contract_type: str
    description: str
    content: str
    applicable_scenarios: List[str]
    required_variables: List[str]
    optional_variables: List[str]
    jurisdictions: List[str]
    version: str
    usage_count: int


class GenerateContractRequest(BaseModel):
    """生成合同请求。"""
    template_id: str
    employer_id: str
    worker_id: str
    variables: Dict[str, str]
    task_id: Optional[str] = None
    contract_value: float = 0.0
    jurisdiction: str = "CN"


class GeneratedContractResponse(BaseModel):
    """生成合同响应。"""
    contract_id: str
    template_id: str
    contract_type: str
    employer_id: str
    worker_id: str
    task_id: Optional[str]
    contract_value: float
    currency: str
    status: str
    jurisdiction: str
    created_at: Optional[str] = None


class SignContractRequest(BaseModel):
    """签署合同请求。"""
    party: str  # employer or worker


class ContractListItem(BaseModel):
    """合同列表项。"""
    contract_id: str
    template_id: str
    contract_type: str
    employer_id: str
    worker_id: str
    contract_value: float
    status: str
    created_at: Optional[str] = None


@router.get("/templates", response_model=ContractTemplateListResponse)
async def list_contract_templates(
    contract_type: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
):
    """获取合同模板列表。"""
    ct = ContractType(contract_type) if contract_type else None
    result = legal_services_service.list_templates(
        contract_type=ct,
        jurisdiction=jurisdiction,
        skip=skip,
        limit=limit,
    )

    items = [
        ContractTemplateListItem(
            template_id=t.template_id,
            name=t.name,
            contract_type=t.contract_type.value,
            description=t.description,
            applicable_scenarios=t.applicable_scenarios,
            usage_count=t.usage_count,
            version=t.version,
        )
        for t in result.templates
    ]

    return ContractTemplateListResponse(
        templates=items,
        total=result.total,
        skip=result.skip,
        limit=result.limit,
    )


@router.get("/templates/{template_id}", response_model=ContractTemplateDetailResponse)
async def get_contract_template(template_id: str):
    """获取合同模板详情。"""
    template = legal_services_service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"合同模板不存在：{template_id}")

    return ContractTemplateDetailResponse(
        template_id=template.template_id,
        name=template.name,
        contract_type=template.contract_type.value,
        description=template.description,
        content=template.content,
        applicable_scenarios=template.applicable_scenarios,
        required_variables=template.required_variables,
        optional_variables=template.optional_variables,
        jurisdictions=template.jurisdictions,
        version=template.version,
        usage_count=template.usage_count,
    )


@router.post("/contracts/generate", response_model=GeneratedContractResponse)
async def generate_contract(request: GenerateContractRequest):
    """根据模板生成合同。"""
    try:
        contract = legal_services_service.generate_contract(
            template_id=request.template_id,
            employer_id=request.employer_id,
            worker_id=request.worker_id,
            variables=request.variables,
            task_id=request.task_id,
            contract_value=request.contract_value,
            jurisdiction=request.jurisdiction,
        )

        return GeneratedContractResponse(
            contract_id=contract.contract_id,
            template_id=contract.template_id,
            contract_type=contract.contract_type.value,
            employer_id=contract.employer_id,
            worker_id=contract.worker_id,
            task_id=contract.task_id,
            contract_value=contract.contract_value,
            currency=contract.currency,
            status=contract.status,
            jurisdiction=contract.jurisdiction,
            created_at=contract.created_at.isoformat() if contract.created_at else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/contracts/{contract_id}", response_model=GeneratedContractResponse)
async def get_contract(contract_id: str):
    """获取合同详情。"""
    contract = legal_services_service.get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail=f"合同不存在：{contract_id}")

    return GeneratedContractResponse(
        contract_id=contract.contract_id,
        template_id=contract.template_id,
        contract_type=contract.contract_type.value,
        employer_id=contract.employer_id,
        worker_id=contract.worker_id,
        task_id=contract.task_id,
        contract_value=contract.contract_value,
        currency=contract.currency,
        status=contract.status,
        jurisdiction=contract.jurisdiction,
        created_at=contract.created_at.isoformat() if contract.created_at else None,
    )


@router.post("/contracts/{contract_id}/sign")
async def sign_contract(contract_id: str, request: SignContractRequest):
    """签署合同。"""
    try:
        party = ContractParty(request.party)
        legal_services_service.sign_contract(contract_id, party)
        return {"status": "success", "message": "合同签署成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/users/{user_id}/contracts", response_model=List[ContractListItem])
async def get_user_contracts(
    user_id: str,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
):
    """获取用户的合同列表。"""
    contracts = legal_services_service.get_user_contracts(
        user_id=user_id,
        status=status,
        skip=skip,
        limit=limit,
    )

    return [
        ContractListItem(
            contract_id=c.contract_id,
            template_id=c.template_id,
            contract_type=c.contract_type.value,
            employer_id=c.employer_id,
            worker_id=c.worker_id,
            contract_value=c.contract_value,
            status=c.status,
            created_at=c.created_at.isoformat() if c.created_at else None,
        )
        for c in contracts
    ]


# ========== 法务咨询相关 API ==========

class LegalConsultationCreateRequest(BaseModel):
    """创建法律咨询请求。"""
    consultation_type: str
    title: str
    description: str
    attachments: Optional[List[str]] = None
    related_task_id: Optional[str] = None
    related_contract_id: Optional[str] = None
    priority: str = "normal"


class LegalConsultationItem(BaseModel):
    """法律咨询项。"""
    consultation_id: str
    user_id: str
    user_type: str
    consultation_type: str
    title: str
    status: str
    priority: str
    assigned_lawyer_name: Optional[str]
    created_at: Optional[str] = None


class LegalConsultationDetail(BaseModel):
    """法律咨询详情。"""
    consultation_id: str
    user_id: str
    user_type: str
    consultation_type: str
    title: str
    description: str
    attachments: List[str]
    status: str
    priority: str
    assigned_lawyer_id: Optional[str]
    assigned_lawyer_name: Optional[str]
    lawyer_response: Optional[str]
    response_at: Optional[str] = None
    satisfaction_score: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConsultationMessageRequest(BaseModel):
    """咨询消息请求。"""
    sender_id: str
    sender_type: str
    content: str
    attachments: Optional[List[str]] = None


class ConsultationMessageItem(BaseModel):
    """咨询消息项。"""
    message_id: str
    sender_id: str
    sender_type: str
    content: str
    attachments: List[str]
    is_read: bool
    created_at: Optional[str] = None


class LawyerProfileItem(BaseModel):
    """律师档案项。"""
    lawyer_id: str
    name: str
    title: str
    law_firm: Optional[str]
    practice_areas: List[str]
    years_of_experience: int
    rating: float
    consultation_fee_per_hour: float
    is_available: bool


@router.post("/consultations", response_model=LegalConsultationItem)
async def create_consultation(request: LegalConsultationCreateRequest, user_id: str = "user_001"):
    """创建法律咨询。"""
    try:
        consultation_type = LegalConsultationType(request.consultation_type)
        consultation = legal_services_service.create_consultation(
            user_id=user_id,
            user_type="worker",  # 简化处理，实际应从用户服务获取
            consultation_type=consultation_type,
            title=request.title,
            description=request.description,
            attachments=request.attachments,
            related_task_id=request.related_task_id,
            related_contract_id=request.related_contract_id,
            priority=request.priority,
        )

        return LegalConsultationItem(
            consultation_id=consultation.consultation_id,
            user_id=consultation.user_id,
            user_type=consultation.user_type,
            consultation_type=consultation.consultation_type.value,
            title=consultation.title,
            status=consultation.status.value,
            priority=consultation.priority,
            assigned_lawyer_name=consultation.assigned_lawyer_name,
            created_at=consultation.created_at.isoformat() if consultation.created_at else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/consultations/{consultation_id}", response_model=LegalConsultationDetail)
async def get_consultation(consultation_id: str):
    """获取咨询详情。"""
    consultation = legal_services_service.get_consultation(consultation_id)
    if not consultation:
        raise HTTPException(status_code=404, detail=f"咨询不存在：{consultation_id}")

    return LegalConsultationDetail(
        consultation_id=consultation.consultation_id,
        user_id=consultation.user_id,
        user_type=consultation.user_type,
        consultation_type=consultation.consultation_type.value,
        title=consultation.title,
        description=consultation.description,
        attachments=consultation.attachments,
        status=consultation.status.value,
        priority=consultation.priority,
        assigned_lawyer_id=consultation.assigned_lawyer_id,
        assigned_lawyer_name=consultation.assigned_lawyer_name,
        lawyer_response=consultation.lawyer_response,
        response_at=consultation.response_at.isoformat() if consultation.response_at else None,
        satisfaction_score=consultation.satisfaction_score,
        created_at=consultation.created_at.isoformat() if consultation.created_at else None,
        updated_at=consultation.updated_at.isoformat() if consultation.updated_at else None,
    )


@router.post("/consultations/{consultation_id}/messages")
async def add_consultation_message(consultation_id: str, request: ConsultationMessageRequest):
    """添加咨询消息。"""
    try:
        message = legal_services_service.add_consultation_message(
            consultation_id=consultation_id,
            sender_id=request.sender_id,
            sender_type=request.sender_type,
            content=request.content,
            attachments=request.attachments,
        )

        return {
            "status": "success",
            "message_id": message.message_id,
            "created_at": message.created_at.isoformat() if message.created_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/consultations/{consultation_id}/messages", response_model=List[ConsultationMessageItem])
async def get_consultation_messages(consultation_id: str):
    """获取咨询消息列表。"""
    messages = legal_services_service.get_consultation_messages(consultation_id)

    return [
        ConsultationMessageItem(
            message_id=m.message_id,
            sender_id=m.sender_id,
            sender_type=m.sender_type,
            content=m.content,
            attachments=m.attachments,
            is_read=m.is_read,
            created_at=m.created_at.isoformat() if m.created_at else None,
        )
        for m in messages
    ]


@router.get("/users/{user_id}/consultations", response_model=List[LegalConsultationItem])
async def get_user_consultations(
    user_id: str,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
):
    """获取用户的咨询列表。"""
    st = ConsultationStatus(status) if status else None
    consultations = legal_services_service.get_user_consultations(
        user_id=user_id,
        status=st,
        skip=skip,
        limit=limit,
    )

    return [
        LegalConsultationItem(
            consultation_id=c.consultation_id,
            user_id=c.user_id,
            user_type=c.user_type,
            consultation_type=c.consultation_type.value,
            title=c.title,
            status=c.status.value,
            priority=c.priority,
            assigned_lawyer_name=c.assigned_lawyer_name,
            created_at=c.created_at.isoformat() if c.created_at else None,
        )
        for c in consultations
    ]


@router.get("/lawyers", response_model=List[LawyerProfileItem])
async def list_lawyers(
    practice_area: Optional[str] = None,
    jurisdiction: Optional[str] = None,
):
    """获取律师列表。"""
    lawyers = legal_services_service.list_lawyers(
        practice_area=practice_area,
        jurisdiction=jurisdiction,
    )

    return [
        LawyerProfileItem(
            lawyer_id=l.lawyer_id,
            name=l.name,
            title=l.title,
            law_firm=l.law_firm,
            practice_areas=l.practice_areas,
            years_of_experience=l.years_of_experience,
            rating=l.rating,
            consultation_fee_per_hour=l.consultation_fee_per_hour,
            is_available=l.is_available_for_consultation,
        )
        for l in lawyers
    ]


@router.get("/lawyers/{lawyer_id}", response_model=LawyerProfileItem)
async def get_lawyer_profile(lawyer_id: str):
    """获取律师档案。"""
    lawyer = legal_services_service.get_lawyer_profile(lawyer_id)
    if not lawyer:
        raise HTTPException(status_code=404, detail=f"律师不存在：{lawyer_id}")

    return LawyerProfileItem(
        lawyer_id=lawyer.lawyer_id,
        name=lawyer.name,
        title=lawyer.title,
        law_firm=lawyer.law_firm,
        practice_areas=lawyer.practice_areas,
        years_of_experience=lawyer.years_of_experience,
        rating=lawyer.rating,
        consultation_fee_per_hour=lawyer.consultation_fee_per_hour,
        is_available=lawyer.is_available_for_consultation,
    )


# ========== 权益保护相关 API ==========

class RightsComplaintCreateRequest(BaseModel):
    """创建权益投诉请求。"""
    respondent_id: str
    respondent_type: str
    violation_type: str
    title: str
    description: str
    detailed_statement: str = ""
    demands: Optional[List[str]] = None
    involved_amount: Optional[float] = None
    related_task_id: Optional[str] = None
    related_contract_id: Optional[str] = None


class RightsComplaintItem(BaseModel):
    """权益投诉项。"""
    complaint_id: str
    complainant_id: str
    respondent_id: str
    violation_type: str
    title: str
    status: str
    progress: int
    current_stage: str
    assigned_mediator_name: Optional[str]
    created_at: Optional[str] = None


class RightsComplaintDetail(BaseModel):
    """权益投诉详情。"""
    complaint_id: str
    complainant_id: str
    complainant_type: str
    respondent_id: str
    respondent_type: str
    violation_type: str
    title: str
    description: str
    detailed_statement: str
    evidence: List[Dict]
    demands: List[str]
    involved_amount: Optional[float]
    currency: str
    status: str
    progress: int
    current_stage: str
    assigned_mediator_id: Optional[str]
    assigned_mediator_name: Optional[str]
    resolution_summary: Optional[str]
    resolution_date: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ComplaintEvidenceRequest(BaseModel):
    """添加证据请求。"""
    evidence_type: str
    file_url: str
    file_name: str
    description: str = ""


@router.post("/complaints", response_model=RightsComplaintItem)
async def create_complaint(request: RightsComplaintCreateRequest, user_id: str = "user_001"):
    """创建权益投诉。"""
    try:
        violation_type = RightsViolationType(request.violation_type)
        complaint = legal_services_service.create_complaint(
            complainant_id=user_id,
            complainant_type="worker",  # 简化处理
            respondent_id=request.respondent_id,
            respondent_type=request.respondent_type,
            violation_type=violation_type,
            title=request.title,
            description=request.description,
            detailed_statement=request.detailed_statement,
            demands=request.demands,
            involved_amount=request.involved_amount,
            related_task_id=request.related_task_id,
            related_contract_id=request.related_contract_id,
        )

        return RightsComplaintItem(
            complaint_id=complaint.complaint_id,
            complainant_id=complaint.complainant_id,
            respondent_id=complaint.respondent_id,
            violation_type=complaint.violation_type.value,
            title=complaint.title,
            status=complaint.status.value,
            progress=complaint.progress,
            current_stage=complaint.current_stage,
            assigned_mediator_name=complaint.assigned_mediator_name,
            created_at=complaint.created_at.isoformat() if complaint.created_at else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/complaints/{complaint_id}", response_model=RightsComplaintDetail)
async def get_complaint(complaint_id: str):
    """获取投诉详情。"""
    complaint = legal_services_service.get_complaint(complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail=f"投诉不存在：{complaint_id}")

    return RightsComplaintDetail(
        complaint_id=complaint.complaint_id,
        complainant_id=complaint.complainant_id,
        complainant_type=complaint.complainant_type,
        respondent_id=complaint.respondent_id,
        respondent_type=complaint.respondent_type,
        violation_type=complaint.violation_type.value,
        title=complaint.title,
        description=complaint.description,
        detailed_statement=complaint.detailed_statement,
        evidence=complaint.evidence,
        demands=complaint.demands,
        involved_amount=complaint.involved_amount,
        currency=complaint.currency,
        status=complaint.status.value,
        progress=complaint.progress,
        current_stage=complaint.current_stage,
        assigned_mediator_id=complaint.assigned_mediator_id,
        assigned_mediator_name=complaint.assigned_mediator_name,
        resolution_summary=complaint.resolution_summary,
        resolution_date=complaint.resolution_date.isoformat() if complaint.resolution_date else None,
        created_at=complaint.created_at.isoformat() if complaint.created_at else None,
        updated_at=complaint.updated_at.isoformat() if complaint.updated_at else None,
    )


@router.post("/complaints/{complaint_id}/evidence")
async def add_complaint_evidence(complaint_id: str, request: ComplaintEvidenceRequest, submitted_by: str = "user_001"):
    """添加投诉证据。"""
    try:
        evidence = legal_services_service.add_complaint_evidence(
            complaint_id=complaint_id,
            evidence_type=request.evidence_type,
            file_url=request.file_url,
            file_name=request.file_name,
            description=request.description,
            submitted_by=submitted_by,
        )

        return {
            "status": "success",
            "evidence_id": evidence.evidence_id,
            "created_at": evidence.submitted_at.isoformat() if evidence.submitted_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/users/{user_id}/complaints", response_model=List[RightsComplaintItem])
async def get_user_complaints(
    user_id: str,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
):
    """获取用户的投诉列表。"""
    st = ComplaintStatus(status) if status else None
    complaints = legal_services_service.get_user_complaints(
        user_id=user_id,
        status=st,
        skip=skip,
        limit=limit,
    )

    return [
        RightsComplaintItem(
            complaint_id=c.complaint_id,
            complainant_id=c.complainant_id,
            respondent_id=c.respondent_id,
            violation_type=c.violation_type.value,
            title=c.title,
            status=c.status.value,
            progress=c.progress,
            current_stage=c.current_stage,
            assigned_mediator_name=c.assigned_mediator_name,
            created_at=c.created_at.isoformat() if c.created_at else None,
        )
        for c in complaints
    ]


# ========== 税务规划相关 API ==========

class TaxCalculationApiRequest(BaseModel):
    """税务计算请求。"""
    income: float
    income_type: str = "labor"
    region: str = "CN"
    deductions: Optional[List[Dict]] = None


class TaxCalculationApiResponse(BaseModel):
    """税务计算响应。"""
    gross_income: float
    taxable_income: float
    tax_amount: float
    net_income: float
    effective_tax_rate: float
    breakdown: List[Dict]
    calculation_details: Dict


class InvoiceCreateRequest(BaseModel):
    """创建发票请求。"""
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
    item_name: str
    amount: float
    tax_rate: float = 0.03
    invoice_type: str = "electronic"
    related_task_id: Optional[str] = None
    related_contract_id: Optional[str] = None


class InvoiceItem(BaseModel):
    """发票项。"""
    invoice_id: str
    invoice_number: str
    invoice_code: str
    seller_name: str
    buyer_name: str
    item_name: str
    amount: float
    tax_amount: float
    total_amount: float
    status: str
    issue_date: Optional[str] = None


@router.post("/tax/calculate", response_model=TaxCalculationApiResponse)
async def calculate_tax(request: TaxCalculationApiRequest):
    """计算个人所得税。"""
    calc_request = TaxCalculationRequest(
        income=request.income,
        income_type=request.income_type,
        region=request.region,
        deductions=request.deductions or [],
    )

    result = legal_services_service.calculate_tax(calc_request)

    return TaxCalculationApiResponse(
        gross_income=result.gross_income,
        taxable_income=result.taxable_income,
        tax_amount=result.tax_amount,
        net_income=result.net_income,
        effective_tax_rate=result.effective_tax_rate,
        breakdown=result.tax_breakdown,
        calculation_details=result.calculation_details,
    )


@router.post("/invoices", response_model=InvoiceItem)
async def create_invoice(request: InvoiceCreateRequest):
    """创建发票。"""
    invoice = legal_services_service.create_invoice(
        seller_name=request.seller_name,
        seller_tax_id=request.seller_tax_id,
        seller_address=request.seller_address,
        seller_phone=request.seller_phone,
        seller_bank_account=request.seller_bank_account,
        buyer_name=request.buyer_name,
        buyer_tax_id=request.buyer_tax_id,
        buyer_address=request.buyer_address,
        buyer_phone=request.buyer_phone,
        buyer_bank_account=request.buyer_bank_account,
        item_name=request.item_name,
        amount=request.amount,
        tax_rate=request.tax_rate,
        invoice_type=request.invoice_type,
        related_task_id=request.related_task_id,
        related_contract_id=request.related_contract_id,
    )

    return InvoiceItem(
        invoice_id=invoice.invoice_id,
        invoice_number=invoice.invoice_number,
        invoice_code=invoice.invoice_code,
        seller_name=invoice.seller_name,
        buyer_name=invoice.buyer_name,
        item_name=invoice.item_name,
        amount=invoice.amount,
        tax_amount=invoice.tax_amount,
        total_amount=invoice.total_amount,
        status=invoice.status,
        issue_date=invoice.issue_date.isoformat() if invoice.issue_date else None,
    )


@router.get("/invoices/{invoice_id}", response_model=InvoiceItem)
async def get_invoice(invoice_id: str):
    """获取发票详情。"""
    invoice = legal_services_service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail=f"发票不存在：{invoice_id}")

    return InvoiceItem(
        invoice_id=invoice.invoice_id,
        invoice_number=invoice.invoice_number,
        invoice_code=invoice.invoice_code,
        seller_name=invoice.seller_name,
        buyer_name=invoice.buyer_name,
        item_name=invoice.item_name,
        amount=invoice.amount,
        tax_amount=invoice.tax_amount,
        total_amount=invoice.total_amount,
        status=invoice.status,
        issue_date=invoice.issue_date.isoformat() if invoice.issue_date else None,
    )


@router.post("/invoices/{invoice_id}/issue")
async def issue_invoice(invoice_id: str):
    """开具发票。"""
    try:
        legal_services_service.issue_invoice(invoice_id)
        return {"status": "success", "message": "发票开具成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========== 合规检查相关 API ==========

class ComplianceCheckRequest(BaseModel):
    """合规检查请求。"""
    object_type: str  # task, contract, user
    object_id: str
    object_data: Dict


class ComplianceIssueItem(BaseModel):
    """合规问题项。"""
    category: str
    severity: str
    risk_level: str
    description: str
    suggestion: str
    regulation_reference: str


class ComplianceCheckResponse(BaseModel):
    """合规检查响应。"""
    check_id: str
    object_type: str
    object_id: str
    overall_status: str
    overall_risk_level: str
    issues: List[ComplianceIssueItem]
    recommendations: List[str]
    regulations_referenced: List[str]
    summary: str
    checked_at: Optional[str] = None


class ComplianceHistoryItem(BaseModel):
    """合规检查历史项。"""
    check_id: str
    object_type: str
    object_id: str
    overall_status: str
    overall_risk_level: str
    issues_count: int
    checked_at: Optional[str] = None


@router.post("/compliance/check", response_model=ComplianceCheckResponse)
async def check_compliance(request: ComplianceCheckRequest):
    """执行合规检查。"""
    result = legal_services_service.check_compliance(
        object_type=request.object_type,
        object_id=request.object_id,
        object_data=request.object_data,
    )

    issues = [
        ComplianceIssueItem(
            category=i.get("category", ""),
            severity=i.get("severity", ""),
            risk_level=i.get("risk_level", ""),
            description=i.get("description", ""),
            suggestion=i.get("suggestion", ""),
            regulation_reference=i.get("regulation_reference", ""),
        )
        for i in result.issues
    ]

    return ComplianceCheckResponse(
        check_id=result.check_id,
        object_type=result.object_type,
        object_id=result.object_id,
        overall_status=result.overall_status,
        overall_risk_level=result.overall_risk_level.value,
        issues=issues,
        recommendations=result.recommendations,
        regulations_referenced=result.regulations_referenced,
        summary=result.summary,
        checked_at=result.checked_at.isoformat() if result.checked_at else None,
    )


@router.get("/compliance/{object_type}/{object_id}/history", response_model=List[ComplianceHistoryItem])
async def get_compliance_history(object_type: str, object_id: str):
    """获取对象的合规检查历史。"""
    checks = legal_services_service.get_object_compliance_checks(
        object_type=object_type,
        object_id=object_id,
    )

    return [
        ComplianceHistoryItem(
            check_id=c.check_id,
            object_type=c.object_type,
            object_id=c.object_id,
            overall_status=c.overall_status,
            overall_risk_level=c.overall_risk_level.value,
            issues_count=len(c.issues),
            checked_at=c.checked_at.isoformat() if c.checked_at else None,
        )
        for c in checks
    ]


# ========== 用户摘要 API ==========

class LegalServicesSummaryResponse(BaseModel):
    """法律服务摘要响应。"""
    user_id: str
    active_contracts: int
    active_consultations: int
    active_complaints: int
    total_tax_paid: float
    pending_invoices: int
    compliance_issues: int


@router.get("/users/{user_id}/summary", response_model=LegalServicesSummaryResponse)
async def get_user_legal_summary(user_id: str):
    """获取用户法律服务摘要。"""
    summary = legal_services_service.get_user_summary(user_id)

    return LegalServicesSummaryResponse(
        user_id=summary.user_id,
        active_contracts=summary.active_contracts,
        active_consultations=summary.active_consultations,
        active_complaints=summary.active_complaints,
        total_tax_paid=summary.total_tax_paid,
        pending_invoices=summary.pending_invoices,
        compliance_issues=summary.compliance_issues,
    )
