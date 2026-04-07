"""
时间追踪 API
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel, Field

from models.p4_models import WorkLogStatusEnum, VerificationMethodEnum, MilestoneStatusEnum
from services.time_tracking_service import WorkSessionService, WorkLogService, MilestoneService


router = APIRouter(prefix="/api", tags=["time-tracking"])


# ==================== Pydantic 模型 ====================

class WorkSessionCreate(BaseModel):
    """开始工作会议请求"""
    order_id: str = Field(..., description="订单 ID")
    employee_id: str = Field(..., description="员工 ID")
    activity_description: Optional[str] = Field(default=None, description="活动描述")
    automatic: bool = Field(default=False, description="是否自动追踪")


class WorkSessionResponse(BaseModel):
    """工作会议响应"""
    id: str
    tenant_id: str
    order_id: str
    employee_id: str
    hirer_id: str
    started_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: int
    billable_seconds: int
    status: str
    activity_description: Optional[str]
    automatic: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkLogCreate(BaseModel):
    """创建工作日志请求"""
    order_id: str = Field(..., description="订单 ID")
    employee_id: str = Field(..., description="员工 ID")
    description: str = Field(..., description="工作描述", min_length=10)
    duration_minutes: int = Field(..., description="工作时长（分钟）", gt=0)
    work_type: str = Field(default="development", description="工作类型")
    verification_method: VerificationMethodEnum = Field(default=VerificationMethodEnum.MANUAL, description="验证方式")
    verification_data: dict = Field(default_factory=dict, description="验证数据")
    session_id: Optional[str] = Field(default=None, description="会话 ID")


class WorkLogResponse(BaseModel):
    """工作日志响应"""
    id: str
    tenant_id: str
    order_id: str
    session_id: Optional[str]
    employee_id: str
    logged_at: datetime
    duration_minutes: int
    description: str
    work_type: str
    verification_method: str
    verification_data: dict
    status: str
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    rejection_reason: Optional[str]
    billable: bool
    hourly_rate: float
    amount: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MilestoneCreate(BaseModel):
    """创建里程碑请求"""
    order_id: str = Field(..., description="订单 ID")
    title: str = Field(..., description="里程碑标题", min_length=1, max_length=200)
    description: str = Field(..., description="里程碑描述")
    amount: float = Field(..., description="里程碑金额", gt=0)
    deliverables: List[str] = Field(default_factory=list, description="交付物列表")
    due_date: Optional[datetime] = Field(default=None, description="截止日期")


class MilestoneResponse(BaseModel):
    """里程碑响应"""
    id: str
    tenant_id: str
    order_id: str
    title: str
    description: str
    deliverables: List[str]
    amount: float
    due_date: Optional[datetime]
    status: str
    submitted_at: Optional[datetime]
    approved_at: Optional[datetime]
    rejected_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkLogAction(BaseModel):
    """工作日志操作请求"""
    rejection_reason: Optional[str] = Field(default=None, description="拒绝原因")


class MilestoneAction(BaseModel):
    """里程碑操作请求"""
    deliverables: Optional[List[str]] = Field(default=None, description="交付物列表")
    rejection_reason: Optional[str] = Field(default=None, description="拒绝原因")


# ==================== 工作会议 API ====================

@router.post("/work-sessions/start", response_model=WorkSessionResponse, summary="开始工作会议")
async def start_work_session(
    request: WorkSessionCreate,
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """开始工作会议"""
    session_service = WorkSessionService()

    # 检查是否有进行中的会话
    existing = session_service.get_active_session(
        order_id=request.order_id,
        employee_id=request.employee_id
    )
    if existing:
        raise HTTPException(status_code=400, detail="Work session already in progress")

    session = session_service.start_session(
        tenant_id=x_tenant_id,
        order_id=request.order_id,
        employee_id=request.employee_id,
        hirer_id=x_user_id,
        activity_description=request.activity_description,
        automatic=request.automatic
    )

    if not session:
        raise HTTPException(status_code=400, detail="Failed to start work session")

    return session


@router.post("/work-sessions/{session_id}/pause", summary="暂停工作会议")
async def pause_work_session(
    session_id: str,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """暂停工作会议"""
    session_service = WorkSessionService()

    success = session_service.pause_session(session_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to pause work session")

    return {"message": "Work session paused", "session_id": session_id}


@router.post("/work-sessions/{session_id}/resume", summary="恢复工作会议")
async def resume_work_session(
    session_id: str,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """恢复工作会议"""
    session_service = WorkSessionService()

    success = session_service.resume_session(session_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to resume work session")

    return {"message": "Work session resumed", "session_id": session_id}


@router.post("/work-sessions/{session_id}/end", summary="结束工作会议")
async def end_work_session(
    session_id: str,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """结束工作会议"""
    session_service = WorkSessionService()

    success = session_service.end_session(session_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to end work session")

    return {"message": "Work session ended", "session_id": session_id}


@router.get("/work-sessions", response_model=List[WorkSessionResponse], summary="获取工作会议列表")
async def list_work_sessions(
    order_id: Optional[str] = Query(default=None, description="订单 ID"),
    employee_id: Optional[str] = Query(default=None, description="员工 ID"),
    status: Optional[str] = Query(default=None, description="状态"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """获取工作会议列表"""
    session_service = WorkSessionService()

    status_enum = WorkLogStatusEnum(status) if status else None
    sessions = session_service.list_sessions(
        tenant_id=x_tenant_id,
        order_id=order_id,
        employee_id=employee_id,
        status=status_enum,
        limit=limit,
        offset=offset
    )

    return sessions


@router.get("/work-sessions/{session_id}", response_model=WorkSessionResponse, summary="获取工作会议详情")
async def get_work_session(
    session_id: str,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """获取工作会议详情"""
    session_service = WorkSessionService()

    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Work session not found")

    return session


# ==================== 工作日志 API ====================

@router.post("/work-logs", response_model=WorkLogResponse, summary="创建工作日志")
async def create_work_log(
    request: WorkLogCreate,
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """创建工作日志"""
    log_service = WorkLogService()

    log = log_service.create_work_log(
        tenant_id=x_tenant_id,
        order_id=request.order_id,
        employee_id=request.employee_id,
        description=request.description,
        duration_minutes=request.duration_minutes,
        work_type=request.work_type,
        verification_method=request.verification_method,
        verification_data=request.verification_data,
        session_id=request.session_id
    )

    if not log:
        raise HTTPException(status_code=400, detail="Failed to create work log")

    return log


@router.post("/work-logs/{log_id}/submit", summary="提交工作日志审核")
async def submit_work_log(
    log_id: str,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """提交工作日志审核"""
    log_service = WorkLogService()

    success = log_service.submit_work_log(log_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to submit work log")

    return {"message": "Work log submitted", "log_id": log_id}


@router.post("/work-logs/{log_id}/approve", summary="批准工作日志")
async def approve_work_log(
    log_id: str,
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """批准工作日志"""
    log_service = WorkLogService()

    success = log_service.approve_work_log(log_id, approved_by=x_user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to approve work log")

    return {"message": "Work log approved", "log_id": log_id}


@router.post("/work-logs/{log_id}/reject", summary="拒绝工作日志")
async def reject_work_log(
    log_id: str,
    request: WorkLogAction,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """拒绝工作日志"""
    log_service = WorkLogService()

    success = log_service.reject_work_log(log_id, rejection_reason=request.rejection_reason)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to reject work log")

    return {"message": "Work log rejected", "log_id": log_id}


@router.get("/work-logs", response_model=List[WorkLogResponse], summary="获取工作日志列表")
async def list_work_logs(
    order_id: Optional[str] = Query(default=None, description="订单 ID"),
    employee_id: Optional[str] = Query(default=None, description="员工 ID"),
    session_id: Optional[str] = Query(default=None, description="会话 ID"),
    status: Optional[str] = Query(default=None, description="状态"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """获取工作日志列表"""
    log_service = WorkLogService()

    status_enum = WorkLogStatusEnum(status) if status else None
    logs = log_service.list_work_logs(
        tenant_id=x_tenant_id,
        order_id=order_id,
        employee_id=employee_id,
        session_id=session_id,
        status=status_enum,
        limit=limit,
        offset=offset
    )

    return logs


@router.get("/work-logs/{log_id}", response_model=WorkLogResponse, summary="获取工作日志详情")
async def get_work_log(
    log_id: str,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """获取工作日志详情"""
    log_service = WorkLogService()

    log = log_service.get_work_log(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Work log not found")

    return log


@router.get("/orders/{order_id}/work-stats", summary="获取订单工时统计")
async def get_order_work_stats(
    order_id: str,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """获取订单工时统计"""
    log_service = WorkLogService()

    stats = log_service.get_total_hours(order_id)
    return stats


# ==================== 里程碑 API ====================

@router.post("/milestones", response_model=MilestoneResponse, summary="创建里程碑")
async def create_milestone(
    request: MilestoneCreate,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """创建里程碑"""
    milestone_service = MilestoneService()

    milestone = milestone_service.create_milestone(
        tenant_id=x_tenant_id,
        order_id=request.order_id,
        title=request.title,
        description=request.description,
        amount=request.amount,
        deliverables=request.deliverables,
        due_date=request.due_date
    )

    if not milestone:
        raise HTTPException(status_code=400, detail="Failed to create milestone")

    return milestone


@router.post("/milestones/{milestone_id}/submit", summary="提交里程碑")
async def submit_milestone(
    milestone_id: str,
    request: MilestoneAction,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """提交里程碑"""
    milestone_service = MilestoneService()

    success = milestone_service.submit_milestone(
        milestone_id=milestone_id,
        deliverables=request.deliverables
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to submit milestone")

    return {"message": "Milestone submitted", "milestone_id": milestone_id}


@router.post("/milestones/{milestone_id}/approve", summary="批准里程碑")
async def approve_milestone(
    milestone_id: str,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """批准里程碑"""
    milestone_service = MilestoneService()

    success = milestone_service.approve_milestone(milestone_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to approve milestone")

    return {"message": "Milestone approved", "milestone_id": milestone_id}


@router.post("/milestones/{milestone_id}/reject", summary="拒绝里程碑")
async def reject_milestone(
    milestone_id: str,
    request: MilestoneAction,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """拒绝里程碑"""
    milestone_service = MilestoneService()

    success = milestone_service.reject_milestone(
        milestone_id=milestone_id,
        rejection_reason=request.rejection_reason
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to reject milestone")

    return {"message": "Milestone rejected", "milestone_id": milestone_id}


@router.get("/milestones", response_model=List[MilestoneResponse], summary="获取里程碑列表")
async def list_milestones(
    order_id: Optional[str] = Query(default=None, description="订单 ID"),
    status: Optional[str] = Query(default=None, description="状态"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """获取里程碑列表"""
    milestone_service = MilestoneService()

    status_enum = MilestoneStatusEnum(status) if status else None
    milestones = milestone_service.list_milestones(
        tenant_id=x_tenant_id,
        order_id=order_id,
        status=status_enum,
        limit=limit,
        offset=offset
    )

    return milestones


@router.get("/milestones/{milestone_id}", response_model=MilestoneResponse, summary="获取里程碑详情")
async def get_milestone(
    milestone_id: str,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """获取里程碑详情"""
    milestone_service = MilestoneService()

    milestone = milestone_service.get_milestone(milestone_id)
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    return milestone
