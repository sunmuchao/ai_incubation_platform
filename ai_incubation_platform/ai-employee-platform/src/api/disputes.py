"""
争议解决系统 API
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Header, Query, UploadFile, File
from pydantic import BaseModel, Field

from models.p4_models import DisputeStatusEnum, DisputeResolutionEnum
from services.dispute_service import DisputeService


router = APIRouter(prefix="/api", tags=["disputes"])


# ==================== Pydantic 模型 ====================

class DisputeCreate(BaseModel):
    """创建争议请求"""
    order_id: str = Field(..., description="订单 ID")
    title: str = Field(..., description="争议标题", min_length=10, max_length=200)
    description: str = Field(..., description="争议描述", min_length=50)
    dispute_type: str = Field(..., description="争议类型")
    desired_resolution: Optional[str] = Field(default=None, description="期望的解决方案")


class DisputeResponse(BaseModel):
    """争议响应"""
    id: str
    tenant_id: str
    order_id: str
    escrow_id: Optional[str]
    opened_by: str
    opened_by_role: str
    against_user_id: str
    title: str
    description: str
    dispute_type: str
    status: str
    priority: str
    evidence: list
    desired_resolution: Optional[str]
    assigned_mediator_id: Optional[str]
    resolution: Optional[str]
    resolution_details: Optional[str]
    refund_amount: Optional[float]
    release_amount: Optional[float]
    closed_at: Optional[datetime]
    closed_by: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DisputeMessageCreate(BaseModel):
    """创建争议消息请求"""
    content: str = Field(..., description="消息内容", min_length=1)
    attachments: List[str] = Field(default_factory=list, description="附件列表")
    is_internal: bool = Field(default=False, description="是否内部消息")


class DisputeMessageResponse(BaseModel):
    """争议消息响应"""
    id: str
    tenant_id: str
    dispute_id: str
    sender_id: str
    sender_role: str
    content: str
    attachments: List[str]
    is_internal: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DisputeEvidenceResponse(BaseModel):
    """争议证据响应"""
    id: str
    tenant_id: str
    dispute_id: str
    submitted_by: str
    submitted_by_role: str
    evidence_type: str
    file_url: str
    file_name: str
    file_size: Optional[int]
    description: Optional[str]
    is_verified: bool
    verified_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class DisputeResolve(BaseModel):
    """解决争议请求"""
    resolution: DisputeResolutionEnum = Field(..., description="解决方式")
    resolution_details: str = Field(..., description="解决方案详情")
    refund_amount: Optional[float] = Field(default=None, description="退款金额")
    release_amount: Optional[float] = Field(default=None, description="释放金额")


class DisputeAction(BaseModel):
    """争议操作请求"""
    reason: Optional[str] = Field(default=None, description="原因说明")


# ==================== 争议 API ====================

@router.post("/disputes", response_model=DisputeResponse, summary="创建争议")
async def create_dispute(
    request: DisputeCreate,
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID"),
    x_user_role: str = Header(..., description="用户角色")
):
    """创建争议"""
    dispute_service = DisputeService()

    # 需要获取订单信息来确定被投诉方
    # 这里简化处理，实际应该从订单中获取
    dispute = dispute_service.create_dispute(
        tenant_id=x_tenant_id,
        order_id=request.order_id,
        opened_by=x_user_id,
        opened_by_role=x_user_role,
        against_user_id=request.against_user_id if hasattr(request, 'against_user_id') else "",
        title=request.title,
        description=request.description,
        dispute_type=request.dispute_type,
        desired_resolution=request.desired_resolution
    )

    if not dispute:
        raise HTTPException(status_code=400, detail="Failed to create dispute")

    return dispute


@router.get("/disputes", response_model=List[DisputeResponse], summary="获取争议列表")
async def list_disputes(
    order_id: Optional[str] = Query(default=None, description="订单 ID"),
    status: Optional[str] = Query(default=None, description="状态"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """获取争议列表"""
    dispute_service = DisputeService()

    status_enum = DisputeStatusEnum(status) if status else None
    disputes = dispute_service.list_disputes(
        tenant_id=x_tenant_id,
        order_id=order_id,
        status=status_enum,
        limit=limit,
        offset=offset
    )

    return disputes


@router.get("/disputes/{dispute_id}", response_model=DisputeResponse, summary="获取争议详情")
async def get_dispute(
    dispute_id: str,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """获取争议详情"""
    dispute_service = DisputeService()

    dispute = dispute_service.get_dispute(dispute_id)
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    return dispute


@router.post("/disputes/{dispute_id}/assign-mediator", summary="指派调解员")
async def assign_mediator(
    dispute_id: str,
    mediator_id: str = Query(..., description="调解员 ID"),
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """指派调解员"""
    dispute_service = DisputeService()

    success = dispute_service.assign_mediator(dispute_id, mediator_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to assign mediator")

    return {"message": "Mediator assigned", "dispute_id": dispute_id, "mediator_id": mediator_id}


@router.post("/disputes/{dispute_id}/messages", response_model=DisputeMessageResponse, summary="添加争议消息")
async def add_dispute_message(
    dispute_id: str,
    request: DisputeMessageCreate,
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID"),
    x_user_role: str = Header(..., description="用户角色")
):
    """添加争议消息"""
    dispute_service = DisputeService()

    message = dispute_service.add_dispute_message(
        tenant_id=x_tenant_id,
        dispute_id=dispute_id,
        sender_id=x_user_id,
        sender_role=x_user_role,
        content=request.content,
        attachments=request.attachments,
        is_internal=request.is_internal
    )

    if not message:
        raise HTTPException(status_code=400, detail="Failed to add message")

    return message


@router.get("/disputes/{dispute_id}/messages", response_model=List[DisputeMessageResponse], summary="获取争议消息列表")
async def list_dispute_messages(
    dispute_id: str,
    include_internal: bool = Query(default=False, description="是否包含内部消息"),
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """获取争议消息列表"""
    dispute_service = DisputeService()

    messages = dispute_service.get_dispute_messages(
        dispute_id=dispute_id,
        include_internal=include_internal
    )

    return messages


@router.post("/disputes/{dispute_id}/evidence", response_model=DisputeEvidenceResponse, summary="提交证据")
async def submit_evidence(
    dispute_id: str,
    evidence_type: str = Query(..., description="证据类型"),
    description: Optional[str] = Query(default=None, description="证据描述"),
    file: UploadFile = File(..., description="证据文件"),
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID"),
    x_user_role: str = Header(..., description="用户角色")
):
    """提交证据"""
    dispute_service = DisputeService()

    # 简化处理：实际应该上传文件并获取 URL
    file_url = f"/files/{dispute_id}/{file.filename}"

    evidence = dispute_service.submit_evidence(
        tenant_id=x_tenant_id,
        dispute_id=dispute_id,
        submitted_by=x_user_id,
        submitted_by_role=x_user_role,
        evidence_type=evidence_type,
        file_url=file_url,
        file_name=file.filename or "unknown",
        file_size=file.size,
        description=description
    )

    if not evidence:
        raise HTTPException(status_code=400, detail="Failed to submit evidence")

    return evidence


@router.get("/disputes/{dispute_id}/evidence", response_model=List[DisputeEvidenceResponse], summary="获取争议证据列表")
async def list_dispute_evidence(
    dispute_id: str,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """获取争议证据列表"""
    dispute_service = DisputeService()

    evidence = dispute_service.get_dispute_evidence(dispute_id)
    return evidence


@router.post("/disputes/{dispute_id}/resolve", summary="解决争议")
async def resolve_dispute(
    dispute_id: str,
    request: DisputeResolve,
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """解决争议"""
    dispute_service = DisputeService()

    success = dispute_service.resolve_dispute(
        dispute_id=dispute_id,
        resolution=request.resolution,
        resolution_details=request.resolution_details,
        resolved_by=x_user_id,
        refund_amount=request.refund_amount,
        release_amount=request.release_amount
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to resolve dispute")

    return {"message": "Dispute resolved", "dispute_id": dispute_id}


@router.post("/disputes/{dispute_id}/escalate", summary="升级争议")
async def escalate_dispute(
    dispute_id: str,
    request: DisputeAction,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """升级争议"""
    dispute_service = DisputeService()

    success = dispute_service.escalate_dispute(
        dispute_id=dispute_id,
        reason=request.reason or "用户请求升级"
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to escalate dispute")

    return {"message": "Dispute escalated", "dispute_id": dispute_id}


@router.post("/disputes/{dispute_id}/close", summary="关闭争议")
async def close_dispute(
    dispute_id: str,
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """关闭争议"""
    dispute_service = DisputeService()

    success = dispute_service.close_dispute(dispute_id, closed_by=x_user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to close dispute")

    return {"message": "Dispute closed", "dispute_id": dispute_id}


@router.get("/disputes/stats", summary="获取争议统计")
async def get_dispute_stats(
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """获取争议统计信息"""
    dispute_service = DisputeService()

    stats = dispute_service.get_dispute_stats(tenant_id=x_tenant_id)
    return stats
