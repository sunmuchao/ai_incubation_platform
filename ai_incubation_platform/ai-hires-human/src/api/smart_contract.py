"""
智能合约支付 API。
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.smart_contract import (
    ContractDisputeRequest,
    ContractDisputeResolution,
    ContractPaymentTrigger,
    ContractStatus,
    ContractType,
    CurrencyType,
    HourlyLog,
    Milestone,
    PaymentConditionType,
    SmartContract,
    SmartContractCreate,
    SmartContractSummary,
    SmartContractTemplate,
    SmartContractUpdate,
)
from services.smart_contract_service import smart_contract_service

router = APIRouter(prefix="/api/smart-contracts", tags=["smart-contracts"])


# ========== 响应模型 ==========

class ContractResponse(BaseModel):
    """合约响应。"""
    id: str
    contract_number: str
    contract_type: str
    ai_employer_id: str
    worker_id: str
    task_id: Optional[str]
    currency: str
    total_amount: float
    paid_amount: float
    remaining_amount: float
    platform_fee_rate: float
    platform_fee: float
    payment_condition: str
    auto_release_hours: Optional[int]
    hourly_rate: Optional[float]
    max_hours: Optional[float]
    milestones: List[Dict[str, Any]]
    status: str
    deliverables: List[str]
    delivery_files: List[str]
    start_date: Optional[str]
    end_date: Optional[str]
    deadline: Optional[str]
    dispute_reason: Optional[str]
    dispute_resolution: Optional[str]
    blockchain_proof_id: Optional[str]
    contract_hash: Optional[str]
    created_at: str
    updated_at: str


class TemplateResponse(BaseModel):
    """模板响应。"""
    id: str
    name: str
    description: str
    contract_type: str
    default_currency: str
    default_platform_fee_rate: float
    default_payment_condition: str
    default_auto_release_hours: Optional[int]
    terms_and_conditions: str
    is_active: bool


class HourlyLogResponse(BaseModel):
    """工时记录响应。"""
    id: str
    contract_id: str
    worker_id: str
    start_time: str
    end_time: str
    hours_worked: float
    description: str
    work_screenshot: Optional[str]
    status: str
    hourly_rate: float
    total_amount: float
    approved_by: Optional[str]
    approved_at: Optional[str]
    created_at: str


class ContractListResponse(BaseModel):
    """合约列表响应。"""
    contracts: List[ContractResponse]
    total: int


class ContractSummaryResponse(BaseModel):
    """合约汇总响应。"""
    total_contracts: int
    active_contracts: int
    completed_contracts: int
    disputed_contracts: int
    total_value: float
    total_paid: float
    by_type: Dict[str, int]
    by_currency: Dict[str, int]
    by_status: Dict[str, int]


# ========== 转换函数 ==========

def _contract_to_response(contract: SmartContract) -> ContractResponse:
    """转换合约为响应格式。"""
    return ContractResponse(
        id=contract.id,
        contract_number=contract.contract_number,
        contract_type=contract.contract_type.value,
        ai_employer_id=contract.ai_employer_id,
        worker_id=contract.worker_id,
        task_id=contract.task_id,
        currency=contract.currency.value,
        total_amount=contract.total_amount,
        paid_amount=contract.paid_amount,
        remaining_amount=contract.remaining_amount,
        platform_fee_rate=contract.platform_fee_rate,
        platform_fee=contract.platform_fee,
        payment_condition=contract.payment_condition.value,
        auto_release_hours=contract.auto_release_hours,
        hourly_rate=contract.hourly_rate,
        max_hours=contract.max_hours,
        milestones=[
            {
                "id": m.id,
                "title": m.title,
                "description": m.description,
                "amount": m.amount,
                "currency": m.currency.value,
                "status": m.status,
                "due_date": m.due_date.isoformat() if m.due_date else None,
                "completed_at": m.completed_at.isoformat() if m.completed_at else None,
                "verified_at": m.verified_at.isoformat() if m.verified_at else None,
                "paid_at": m.paid_at.isoformat() if m.paid_at else None,
            }
            for m in contract.milestones
        ],
        status=contract.status.value,
        deliverables=contract.deliverables,
        delivery_files=contract.delivery_files,
        start_date=contract.start_date.isoformat() if contract.start_date else None,
        end_date=contract.end_date.isoformat() if contract.end_date else None,
        deadline=contract.deadline.isoformat() if contract.deadline else None,
        dispute_reason=contract.dispute_reason,
        dispute_resolution=contract.dispute_resolution,
        blockchain_proof_id=contract.blockchain_proof_id,
        contract_hash=contract.contract_hash,
        created_at=contract.created_at.isoformat(),
        updated_at=contract.updated_at.isoformat(),
    )


def _template_to_response(template: SmartContractTemplate) -> TemplateResponse:
    """转换模板为响应格式。"""
    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        contract_type=template.contract_type.value,
        default_currency=template.default_currency.value,
        default_platform_fee_rate=template.default_platform_fee_rate,
        default_payment_condition=template.default_payment_condition.value,
        default_auto_release_hours=template.default_auto_release_hours,
        terms_and_conditions=template.terms_and_conditions,
        is_active=template.is_active,
    )


def _hourly_log_to_response(log: HourlyLog) -> HourlyLogResponse:
    """转换工时记录为响应格式。"""
    return HourlyLogResponse(
        id=log.id,
        contract_id=log.contract_id,
        worker_id=log.worker_id,
        start_time=log.start_time.isoformat(),
        end_time=log.end_time.isoformat(),
        hours_worked=log.hours_worked,
        description=log.description,
        work_screenshot=log.work_screenshot,
        status=log.status,
        hourly_rate=log.hourly_rate,
        total_amount=log.total_amount,
        approved_by=log.approved_by,
        approved_at=log.approved_at.isoformat() if log.approved_at else None,
        created_at=log.created_at.isoformat(),
    )


# ========== 模板管理 ==========

@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates():
    """
    列出所有可用的智能合约模板。

    返回系统预置的合约模板，包括：
    - 固定价格合约
    - 小时计费合约
    - 里程碑合约
    """
    templates = smart_contract_service.list_templates()
    return [_template_to_response(t) for t in templates]


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: str):
    """获取指定模板详情。"""
    template = smart_contract_service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return _template_to_response(template)


# ========== 合约创建与管理 ==========

@router.post("/create", response_model=ContractResponse)
async def create_contract(request: SmartContractCreate):
    """
    创建智能合约。

    根据选择的合约类型，提供不同的参数：
    - 固定价格：需要 total_amount
    - 小时计费：需要 hourly_rate 和 max_hours
    - 里程碑：需要 milestones 数组

    支持多币种（CNY/USD/USDT 等）。
    """
    try:
        contract = smart_contract_service.create_contract(request)
        return _contract_to_response(contract)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(contract_id: str):
    """获取合约详情。"""
    contract = smart_contract_service.get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return _contract_to_response(contract)


@router.get("/number/{contract_number}", response_model=ContractResponse)
async def get_contract_by_number(contract_number: str):
    """通过合约编号获取合约。"""
    contract = smart_contract_service.get_contract_by_number(contract_number)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return _contract_to_response(contract)


@router.get("/employer/{employer_id}", response_model=ContractListResponse)
async def list_employer_contracts(employer_id: str, limit: int = 20):
    """获取雇主的所有合约。"""
    contracts = smart_contract_service.get_employer_contracts(employer_id)
    contracts = contracts[:limit]
    return {
        "contracts": [_contract_to_response(c) for c in contracts],
        "total": len(contracts)
    }


@router.get("/worker/{worker_id}", response_model=ContractListResponse)
async def list_worker_contracts(worker_id: str, limit: int = 20):
    """获取工人的所有合约。"""
    contracts = smart_contract_service.get_worker_contracts(worker_id)
    contracts = contracts[:limit]
    return {
        "contracts": [_contract_to_response(c) for c in contracts],
        "total": len(contracts)
    }


@router.get("/status/{status}", response_model=ContractListResponse)
async def list_contracts_by_status(status: ContractStatus, limit: int = 20):
    """按状态列出合约。"""
    contracts = smart_contract_service.list_contracts_by_status(status)
    contracts = contracts[:limit]
    return {
        "contracts": [_contract_to_response(c) for c in contracts],
        "total": len(contracts)
    }


# ========== 合约执行 ==========

@router.post("/{contract_id}/start", response_model=ContractResponse)
async def start_contract(contract_id: str, worker_id: str):
    """
    开始合约执行。

    工人接受合约后调用此接口开始执行。
    """
    try:
        contract = smart_contract_service.start_contract_execution(contract_id, worker_id)
        return _contract_to_response(contract)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{contract_id}/deliverables", response_model=ContractResponse)
async def submit_deliverables(
    contract_id: str,
    worker_id: str,
    deliverables: List[str],
    delivery_files: List[str] = None,
):
    """
    提交交付物。

    工人完成工作后提交交付物，可触发自动支付。
    """
    try:
        contract = smart_contract_service.submit_deliverables(
            contract_id=contract_id,
            worker_id=worker_id,
            deliverables=deliverables,
            delivery_files=delivery_files or [],
        )
        return _contract_to_response(contract)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 工时管理（小时计费合约）==========

@router.post("/{contract_id}/hourly-log", response_model=HourlyLogResponse)
async def log_work_hours(
    contract_id: str,
    worker_id: str,
    start_time: datetime,
    end_time: datetime,
    description: str = "",
    work_screenshot: Optional[str] = None,
):
    """
    记录工时。

    小时计费合约的工人使用，记录工作时长。
    """
    try:
        log = smart_contract_service.log_work_hours(
            contract_id=contract_id,
            worker_id=worker_id,
            start_time=start_time,
            end_time=end_time,
            description=description,
            work_screenshot=work_screenshot,
        )
        return _hourly_log_to_response(log)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hourly-log/{log_id}/approve", response_model=HourlyLogResponse)
async def approve_hourly_log(log_id: str, approver_id: str):
    """
    审批工时记录。

    雇主审批工人的工时记录，审批后触发支付。
    """
    try:
        log = smart_contract_service.approve_hourly_log(log_id, approver_id)
        return _hourly_log_to_response(log)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hourly-log/{log_id}/reject", response_model=HourlyLogResponse)
async def reject_hourly_log(log_id: str, approver_id: str, reason: str):
    """
    拒绝工时记录。

    雇主拒绝工人的工时记录，需说明原因。
    """
    try:
        log = smart_contract_service.reject_hourly_log(log_id, approver_id, reason)
        return _hourly_log_to_response(log)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 里程碑管理 ==========

@router.post("/{contract_id}/milestone/{milestone_id}/complete", response_model=Dict[str, Any])
async def complete_milestone(contract_id: str, milestone_id: str, worker_id: str):
    """
    完成里程碑。

    工人完成里程碑后调用，可触发里程碑自动支付。
    """
    try:
        milestone = smart_contract_service.complete_milestone(contract_id, milestone_id, worker_id)
        return {
            "message": "Milestone completed successfully",
            "milestone": {
                "id": milestone.id,
                "title": milestone.title,
                "status": milestone.status,
                "amount": milestone.amount,
                "completed_at": milestone.completed_at.isoformat() if milestone.completed_at else None,
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{contract_id}/milestone/{milestone_id}/verify", response_model=Dict[str, Any])
async def verify_milestone(contract_id: str, milestone_id: str, verifier_id: str):
    """
    验收里程碑。

    雇主验收里程碑。
    """
    try:
        milestone = smart_contract_service.verify_milestone(contract_id, milestone_id, verifier_id)
        return {
            "message": "Milestone verified successfully",
            "milestone": {
                "id": milestone.id,
                "title": milestone.title,
                "status": milestone.status,
                "verified_at": milestone.verified_at.isoformat() if milestone.verified_at else None,
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 支付触发 ==========

@router.post("/{contract_id}/trigger-payment", response_model=ContractResponse)
async def trigger_payment(contract_id: str, request: ContractPaymentTrigger):
    """
    触发合约支付。

    触发类型：
    - manual: 手动触发支付
    - auto_on_time: 超时自动支付
    - milestone_completed: 里程碑完成支付
    """
    try:
        contract = smart_contract_service.trigger_payment(request)
        return _contract_to_response(contract)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 争议处理 ==========

@router.post("/{contract_id}/dispute", response_model=ContractResponse)
async def dispute_contract(contract_id: str, request: ContractDisputeRequest):
    """
    对合约提出争议。

    雇主或工人都可以提出争议，争议期间资金冻结。
    """
    try:
        contract = smart_contract_service.dispute_contract(request)
        return _contract_to_response(contract)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{contract_id}/resolve-dispute", response_model=ContractResponse)
async def resolve_dispute(contract_id: str, request: ContractDisputeResolution):
    """
    解决合约争议。

    解决方案：
    - employer_full: 全额退款给雇主
    - worker_full: 全额支付给工人
    - split: 按比例分配
    - custom: 自定义分配
    """
    try:
        contract = smart_contract_service.resolve_dispute(request)
        return _contract_to_response(contract)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 合约控制 ==========

@router.post("/{contract_id}/terminate", response_model=ContractResponse)
async def terminate_contract(contract_id: str, operator_id: str, reason: str):
    """
    终止合约。

    管理员或双方协商终止合约，剩余资金退还雇主。
    """
    try:
        contract = smart_contract_service.terminate_contract(contract_id, operator_id, reason)
        return _contract_to_response(contract)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{contract_id}/pause", response_model=ContractResponse)
async def pause_contract(contract_id: str, operator_id: str, reason: str = ""):
    """暂停合约。"""
    try:
        contract = smart_contract_service.pause_contract(contract_id, operator_id, reason)
        return _contract_to_response(contract)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{contract_id}/resume", response_model=ContractResponse)
async def resume_contract(contract_id: str, operator_id: str):
    """恢复合约。"""
    try:
        contract = smart_contract_service.resume_contract(contract_id, operator_id)
        return _contract_to_response(contract)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 统计汇总 ==========

@router.get("/summary", response_model=ContractSummaryResponse)
async def get_summary():
    """获取智能合约汇总统计。"""
    return smart_contract_service.get_summary()
