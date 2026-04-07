"""
Escrow 资金托管 API。
"""
from __future__ import annotations

import os
import sys
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.escrow import (
    EscrowCreate,
    EscrowDisputeRequest,
    EscrowResolutionRequest,
    EscrowStatus,
    EscrowTransaction,
)
from models.task import TaskStatus
from services.escrow_service import escrow_service
from services.task_service import task_service

router = APIRouter(prefix="/api/escrow", tags=["escrow"])


class EscrowResponse(BaseModel):
    """Escrow 响应。"""
    id: str
    task_id: str
    ai_employer_id: str
    worker_id: Optional[str]
    principal_amount: float
    platform_fee: float
    total_amount: float
    currency: str
    status: str
    funded_at: Optional[str]
    released_at: Optional[str]
    refunded_at: Optional[str]
    dispute_reason: Optional[str]
    created_at: str
    updated_at: str


class EscrowSummary(BaseModel):
    """Escrow 汇总统计。"""
    total_escrows: int
    total_funded: float
    total_released: float
    total_disputed: float
    status_counts: dict


def _escrow_to_response(escrow: EscrowTransaction) -> EscrowResponse:
    """转换 Escrow 为响应格式。"""
    return EscrowResponse(
        id=escrow.id,
        task_id=escrow.task_id,
        ai_employer_id=escrow.ai_employer_id,
        worker_id=escrow.worker_id,
        principal_amount=escrow.principal_amount,
        platform_fee=escrow.platform_fee,
        total_amount=escrow.total_amount,
        currency=escrow.currency,
        status=escrow.status.value,
        funded_at=escrow.funded_at.isoformat() if escrow.funded_at else None,
        released_at=escrow.released_at.isoformat() if escrow.released_at else None,
        refunded_at=escrow.refunded_at.isoformat() if escrow.refunded_at else None,
        dispute_reason=escrow.dispute_reason,
        created_at=escrow.created_at.isoformat(),
        updated_at=escrow.updated_at.isoformat(),
    )


@router.post("/create", response_model=EscrowResponse)
async def create_escrow(request: EscrowCreate):
    """
    创建 Escrow 资金托管。

    任务发布时调用，冻结雇主账户相应资金（任务报酬 + 平台服务费）。
    资金冻结后任务状态变为已发布，工人可以接单。
    """
    # 验证任务存在
    task = task_service.get_task(request.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 验证雇主 ID 匹配
    if task.ai_employer_id != request.ai_employer_id:
        raise HTTPException(status_code=403, detail="Not authorized for this task")

    # 验证任务状态
    if task.status not in [TaskStatus.PENDING, TaskStatus.PUBLISHED]:
        raise HTTPException(
            status_code=400,
            detail=f"Task cannot create escrow in status {task.status.value}"
        )

    # 验证报酬金额
    if request.principal_amount <= 0:
        raise HTTPException(status_code=400, detail="Principal amount must be positive")

    try:
        escrow = escrow_service.create_escrow(request)
        return _escrow_to_response(escrow)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}", response_model=EscrowResponse)
async def get_escrow(task_id: str):
    """获取 Escrow 详情。"""
    escrow = escrow_service.get_escrow(task_id)
    if not escrow:
        raise HTTPException(status_code=404, detail="Escrow not found")
    return _escrow_to_response(escrow)


@router.post("/{task_id}/release")
async def release_escrow(
    task_id: str,
    worker_id: str,
    operator_id: str,
    background_tasks: BackgroundTasks,
):
    """
    释放 Escrow 资金给工人。

    任务验收通过后调用，将托管资金转入工人账户。
    平台服务费自动扣除。
    """
    try:
        escrow, payment_tx = escrow_service.release_escrow(
            task_id=task_id,
            worker_id=worker_id,
            operator_id=operator_id,
        )

        # 更新任务状态为已完成
        task = task_service.get_task(task_id)
        if task:
            task_service.complete_task(task_id, True)

            # 触发回调（如果有）
            if task.callback_url:
                from services.callback_service import notify_task_completed_by_id
                background_tasks.add_task(notify_task_completed_by_id, task_id)

        return {
            "message": "Escrow released successfully",
            "escrow_id": escrow.id,
            "payment_transaction_id": payment_tx.id,
            "worker_amount": escrow.principal_amount,
            "platform_fee": escrow.platform_fee,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/refund")
async def refund_escrow(task_id: str, operator_id: str, reason: Optional[str] = None):
    """
    退款 Escrow 资金给雇主。

    任务取消或验收不通过时调用，将托管资金全额退回雇主账户。
    """
    try:
        escrow, refund_tx = escrow_service.refund_escrow(
            task_id=task_id,
            operator_id=operator_id,
            reason=reason,
        )

        # 更新任务状态为已取消
        task = task_service.get_task(task_id)
        if task:
            task_service.cancel_task(task_id, operator_id, reason or "Escrow refund")

        return {
            "message": "Escrow refunded successfully",
            "escrow_id": escrow.id,
            "refund_transaction_id": refund_tx.id,
            "refund_amount": escrow.total_amount,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/dispute")
async def dispute_escrow(request: EscrowDisputeRequest):
    """
    对 Escrow 提出争议。

    争议期间资金保持冻结状态，等待平台仲裁。
    """
    try:
        escrow = escrow_service.dispute_escrow(request)
        return {
            "message": "Escrow disputed successfully",
            "escrow_id": escrow.id,
            "status": "disputed",
            "reason": escrow.dispute_reason,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/resolve-dispute")
async def resolve_escrow_dispute(request: EscrowResolutionRequest):
    """
    仲裁 Escrow 争议。

    resolution 选项：
    - employer_full: 全额退款给雇主
    - worker_full: 全额支付给工人
    - split: 按比例分配（需指定 split_ratio）
    """
    try:
        escrow = escrow_service.resolve_escrow_dispute(request)
        return {
            "message": "Escrow dispute resolved successfully",
            "escrow_id": escrow.id,
            "resolution": escrow.dispute_resolution,
            "split_ratio": escrow.split_ratio,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/employer/{employer_id}/list", response_model=List[EscrowResponse])
async def list_employer_escrows(employer_id: str):
    """获取雇主的所有 Escrow 记录。"""
    escrows = escrow_service.get_employer_escrows(employer_id)
    return [_escrow_to_response(e) for e in escrows]


@router.get("/worker/{worker_id}/list", response_model=List[EscrowResponse])
async def list_worker_escrows(worker_id: str):
    """获取工人的所有 Escrow 记录。"""
    escrows = escrow_service.get_worker_escrows(worker_id)
    return [_escrow_to_response(e) for e in escrows]


@router.get("/status/{status}", response_model=List[EscrowResponse])
async def list_escrows_by_status(status: EscrowStatus):
    """按状态列出 Escrow 记录。"""
    escrows = escrow_service.list_escrows_by_status(status)
    return [_escrow_to_response(e) for e in escrows]


@router.get("/summary", response_model=EscrowSummary)
async def get_escrow_summary():
    """获取 Escrow 汇总统计。"""
    return escrow_service.get_escrow_summary()
