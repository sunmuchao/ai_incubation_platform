"""
提案/投标系统 API
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel, Field

from models.p4_models import JobPostingDB, ProposalDB, ProposalStatusEnum, ProposalTypeEnum
from services.proposal_service import JobPostingService, ProposalService


router = APIRouter(prefix="/api", tags=["proposals"])


# ==================== Pydantic 模型 ====================

class JobPostingCreate(BaseModel):
    """创建职位发布请求"""
    title: str = Field(..., description="职位标题", min_length=1, max_length=200)
    description: str = Field(..., description="职位描述")
    job_type: ProposalTypeEnum = Field(default=ProposalTypeEnum.HOURLY, description="工作类型")
    budget_min: Optional[float] = Field(default=None, description="预算范围 - 最低")
    budget_max: Optional[float] = Field(default=None, description="预算范围 - 最高")
    hourly_rate_min: Optional[float] = Field(default=None, description="小时费率 - 最低")
    hourly_rate_max: Optional[float] = Field(default=None, description="小时费率 - 最高")
    duration_hours: Optional[int] = Field(default=None, description="预计工时")
    required_skills: List[str] = Field(default_factory=list, description="所需技能标签")
    required_experience: Optional[str] = Field(default=None, description="经验要求")
    deadline: Optional[datetime] = Field(default=None, description="截止日期")


class JobPostingResponse(BaseModel):
    """职位发布响应"""
    id: str
    tenant_id: str
    hirer_id: str
    title: str
    description: str
    job_type: str
    budget_min: Optional[float]
    budget_max: Optional[float]
    hourly_rate_min: Optional[float]
    hourly_rate_max: Optional[float]
    duration_hours: Optional[int]
    required_skills: List[str]
    required_experience: Optional[str]
    deadline: Optional[datetime]
    status: str
    proposal_count: int
    views: int
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]
    filled_at: Optional[datetime]

    class Config:
        from_attributes = True


class ProposalCreate(BaseModel):
    """创建提案请求"""
    job_posting_id: str = Field(..., description="职位发布 ID")
    employee_id: str = Field(..., description="员工 ID")
    cover_letter: str = Field(..., description="求职信", min_length=10)
    proposed_rate: float = Field(..., description="报价", gt=0)
    proposed_duration_hours: Optional[int] = Field(default=None, description="预计工时")
    proposal_type: ProposalTypeEnum = Field(default=ProposalTypeEnum.FIXED_PRICE, description="提案类型")
    delivery_date: Optional[datetime] = Field(default=None, description="预计交付日期")
    attachments: List[str] = Field(default_factory=list, description="附件列表")


class ProposalResponse(BaseModel):
    """提案响应"""
    id: str
    tenant_id: str
    job_posting_id: str
    employee_id: str
    owner_id: str
    cover_letter: str
    proposed_rate: float
    proposed_duration_hours: Optional[int]
    proposal_type: str
    delivery_date: Optional[datetime]
    attachments: List[str]
    status: str
    hirer_message: Optional[str]
    viewed_at: Optional[datetime]
    responded_at: Optional[datetime]
    expires_at: Optional[datetime]
    order_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProposalAction(BaseModel):
    """提案操作请求"""
    hirer_message: Optional[str] = Field(default=None, description="回复消息")


# ==================== 职位发布 API ====================

@router.post("/job-postings", response_model=JobPostingResponse, summary="创建职位发布")
async def create_job_posting(
    request: JobPostingCreate,
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """创建新的职位发布"""
    job_posting_service = JobPostingService()

    job_posting = job_posting_service.create_job_posting(
        tenant_id=x_tenant_id,
        hirer_id=x_user_id,
        title=request.title,
        description=request.description,
        job_type=request.job_type,
        budget_min=request.budget_min,
        budget_max=request.budget_max,
        hourly_rate_min=request.hourly_rate_min,
        hourly_rate_max=request.hourly_rate_max,
        duration_hours=request.duration_hours,
        required_skills=request.required_skills,
        required_experience=request.required_experience,
        deadline=request.deadline
    )

    return job_posting


@router.get("/job-postings", response_model=List[JobPostingResponse], summary="获取职位发布列表")
async def list_job_postings(
    hirer_id: Optional[str] = Query(default=None, description="发布者 ID"),
    status: Optional[str] = Query(default="open", description="状态"),
    skills: Optional[str] = Query(default=None, description="技能标签（逗号分隔）"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """获取职位发布列表"""
    job_posting_service = JobPostingService()

    skills_list = skills.split(",") if skills else None
    job_postings = job_posting_service.list_job_postings(
        tenant_id=x_tenant_id,
        hirer_id=hirer_id,
        status=status,
        skills=skills_list,
        limit=limit,
        offset=offset
    )

    return job_postings


@router.get("/job-postings/{job_posting_id}", response_model=JobPostingResponse, summary="获取职位发布详情")
async def get_job_posting(
    job_posting_id: str,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """获取职位发布详情"""
    job_posting_service = JobPostingService()

    job_posting = job_posting_service.get_job_posting(job_posting_id)
    if not job_posting:
        raise HTTPException(status_code=404, detail="Job posting not found")

    return job_posting


@router.post("/job-postings/{job_posting_id}/close", summary="关闭职位发布")
async def close_job_posting(
    job_posting_id: str,
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """关闭职位发布"""
    job_posting_service = JobPostingService()

    success = job_posting_service.close_job_posting(job_posting_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to close job posting")

    return {"message": "Job posting closed", "job_posting_id": job_posting_id}


# ==================== 提案 API ====================

@router.post("/proposals", response_model=ProposalResponse, summary="创建提案")
async def create_proposal(
    request: ProposalCreate,
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """创建新的提案"""
    proposal_service = ProposalService()

    proposal = proposal_service.create_proposal(
        tenant_id=x_tenant_id,
        job_posting_id=request.job_posting_id,
        employee_id=request.employee_id,
        owner_id=x_user_id,
        cover_letter=request.cover_letter,
        proposed_rate=request.proposed_rate,
        proposed_duration_hours=request.proposed_duration_hours,
        proposal_type=request.proposal_type,
        delivery_date=request.delivery_date,
        attachments=request.attachments
    )

    if not proposal:
        raise HTTPException(status_code=400, detail="Failed to create proposal")

    return proposal


@router.get("/proposals", response_model=List[ProposalResponse], summary="获取提案列表")
async def list_proposals(
    job_posting_id: Optional[str] = Query(default=None, description="职位发布 ID"),
    employee_id: Optional[str] = Query(default=None, description="员工 ID"),
    status: Optional[str] = Query(default=None, description="状态"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """获取提案列表"""
    proposal_service = ProposalService()

    status_enum = ProposalStatusEnum(status) if status else None
    proposals = proposal_service.list_proposals(
        tenant_id=x_tenant_id,
        job_posting_id=job_posting_id,
        employee_id=employee_id,
        status=status_enum,
        limit=limit,
        offset=offset
    )

    return proposals


@router.get("/proposals/{proposal_id}", response_model=ProposalResponse, summary="获取提案详情")
async def get_proposal(
    proposal_id: str,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """获取提案详情"""
    proposal_service = ProposalService()

    proposal = proposal_service.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    return proposal


@router.post("/proposals/{proposal_id}/accept", summary="接受提案")
async def accept_proposal(
    proposal_id: str,
    request: ProposalAction,
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """接受提案"""
    proposal_service = ProposalService()

    success = proposal_service.accept_proposal(
        proposal_id=proposal_id,
        hirer_id=x_user_id,
        hirer_message=request.hirer_message
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to accept proposal")

    return {"message": "Proposal accepted", "proposal_id": proposal_id}


@router.post("/proposals/{proposal_id}/reject", summary="拒绝提案")
async def reject_proposal(
    proposal_id: str,
    request: ProposalAction,
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """拒绝提案"""
    proposal_service = ProposalService()

    success = proposal_service.reject_proposal(
        proposal_id=proposal_id,
        hirer_id=x_user_id,
        hirer_message=request.hirer_message
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to reject proposal")

    return {"message": "Proposal rejected", "proposal_id": proposal_id}


@router.post("/proposals/{proposal_id}/cancel", summary="取消提案")
async def cancel_proposal(
    proposal_id: str,
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """取消提案"""
    proposal_service = ProposalService()

    success = proposal_service.cancel_proposal(
        proposal_id=proposal_id,
        owner_id=x_user_id
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to cancel proposal")

    return {"message": "Proposal cancelled", "proposal_id": proposal_id}
