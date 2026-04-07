"""
支付托管 (Escrow) API
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel, Field

from models.p4_models import EscrowStatusEnum
from services.escrow_service import EscrowService


router = APIRouter(prefix="/api", tags=["escrow"])


# ==================== Pydantic 模型 ====================

class EscrowCreate(BaseModel):
    """创建托管请求"""
    order_id: str = Field(..., description="订单 ID")
    amount: float = Field(..., description="托管金额", gt=0)
    currency: str = Field(default="CNY", description="货币类型")
    milestone_id: Optional[str] = Field(default=None, description="里程碑 ID（可选）")
    funding_deadline_hours: int = Field(default=24, description="充值截止时间（小时）")


class EscrowFund(BaseModel):
    """充值托管请求"""
    payment_method: str = Field(default="balance", description="支付方式")
    transaction_id: Optional[str] = Field(default=None, description="第三方交易 ID")


class EscrowRelease(BaseModel):
    """释放托管请求"""
    release_amount: Optional[float] = Field(default=None, description="释放金额（不填则全额释放）")
    reason: Optional[str] = Field(default=None, description="释放原因")


class EscrowRefund(BaseModel):
    """退款托管请求"""
    refund_amount: Optional[float] = Field(default=None, description="退款金额（不填则全额退款）")
    reason: Optional[str] = Field(default=None, description="退款原因")


class EscrowResponse(BaseModel):
    """托管响应"""
    id: str
    tenant_id: str
    order_id: str
    milestone_id: Optional[str]
    hirer_id: str
    employee_id: str
    owner_id: str
    amount: float
    currency: str
    status: str
    funding_deadline: Optional[datetime]
    funded_at: Optional[datetime]
    released_at: Optional[datetime]
    refunded_at: Optional[datetime]
    released_amount: float
    refunded_amount: float
    platform_fee: float
    owner_earning: float
    payment_method: Optional[str]
    transaction_id: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EscrowStatsResponse(BaseModel):
    """托管统计响应"""
    escrow_id: str
    total_amount: float
    released_amount: float
    refunded_amount: float
    remaining_amount: float
    platform_fee: float
    owner_earning: float
    status: str
    transaction_count: int


# ==================== 托管 API ====================

@router.post("/escrows", response_model=EscrowResponse, summary="创建托管")
async def create_escrow(
    request: EscrowCreate,
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """创建支付托管"""
    escrow_service = EscrowService()

    escrow = escrow_service.create_escrow(
        tenant_id=x_tenant_id,
        order_id=request.order_id,
        hirer_id=x_user_id,
        employee_id=request.employee_id if hasattr(request, 'employee_id') else "",
        owner_id=request.owner_id if hasattr(request, 'owner_id') else "",
        amount=request.amount,
        currency=request.currency,
        milestone_id=request.milestone_id,
        funding_deadline_hours=request.funding_deadline_hours
    )

    # 由于创建时 employee_id 和 owner_id 需要从订单获取，这里简化处理
    # 实际应该从订单中获取这些信息
    if not escrow:
        raise HTTPException(status_code=400, detail="Failed to create escrow")

    return escrow


@router.post("/escrows/{escrow_id}/fund", summary="充值托管")
async def fund_escrow(
    escrow_id: str,
    request: EscrowFund,
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """充值托管"""
    escrow_service = EscrowService()

    success = escrow_service.fund_escrow(
        escrow_id=escrow_id,
        payment_method=request.payment_method,
        transaction_id=request.transaction_id
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to fund escrow")

    return {"message": "Escrow funded", "escrow_id": escrow_id}


@router.post("/escrows/{escrow_id}/release", summary="释放托管")
async def release_escrow(
    escrow_id: str,
    request: EscrowRelease,
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """释放托管"""
    escrow_service = EscrowService()

    success = escrow_service.release_escrow(
        escrow_id=escrow_id,
        release_amount=request.release_amount,
        reason=request.reason
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to release escrow")

    return {"message": "Escrow released", "escrow_id": escrow_id}


@router.post("/escrows/{escrow_id}/refund", summary="退款托管")
async def refund_escrow(
    escrow_id: str,
    request: EscrowRefund,
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """退款托管"""
    escrow_service = EscrowService()

    success = escrow_service.refund_escrow(
        escrow_id=escrow_id,
        refund_amount=request.refund_amount,
        reason=request.reason
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to refund escrow")

    return {"message": "Escrow refunded", "escrow_id": escrow_id}


@router.post("/escrows/{escrow_id}/dispute", summary="争议托管")
async def dispute_escrow(
    escrow_id: str,
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """标记托管为争议状态"""
    escrow_service = EscrowService()

    success = escrow_service.dispute_escrow(escrow_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to dispute escrow")

    return {"message": "Escrow marked as disputed", "escrow_id": escrow_id}


@router.get("/escrows", response_model=List[EscrowResponse], summary="获取托管列表")
async def list_escrows(
    order_id: Optional[str] = Query(default=None, description="订单 ID"),
    hirer_id: Optional[str] = Query(default=None, description="租赁者 ID"),
    employee_id: Optional[str] = Query(default=None, description="员工 ID"),
    owner_id: Optional[str] = Query(default=None, description="所有者 ID"),
    status: Optional[str] = Query(default=None, description="状态"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """获取托管列表"""
    escrow_service = EscrowService()

    status_enum = EscrowStatusEnum(status) if status else None
    escrows = escrow_service.list_escrows(
        tenant_id=x_tenant_id,
        order_id=order_id,
        hirer_id=hirer_id,
        employee_id=employee_id,
        owner_id=owner_id,
        status=status_enum,
        limit=limit,
        offset=offset
    )

    return escrows


@router.get("/escrows/{escrow_id}", response_model=EscrowResponse, summary="获取托管详情")
async def get_escrow(
    escrow_id: str,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """获取托管详情"""
    escrow_service = EscrowService()

    escrow = escrow_service.get_escrow(escrow_id)
    if not escrow:
        raise HTTPException(status_code=404, detail="Escrow not found")

    return escrow


@router.get("/escrows/{escrow_id}/stats", response_model=EscrowStatsResponse, summary="获取托管统计")
async def get_escrow_stats(
    escrow_id: str,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """获取托管统计信息"""
    escrow_service = EscrowService()

    stats = escrow_service.get_escrow_stats(escrow_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Escrow not found")

    return stats
