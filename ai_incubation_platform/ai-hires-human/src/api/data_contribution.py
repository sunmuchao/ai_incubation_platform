"""
用户贡献数据 API 路由。
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db_session
from services.data_contribution_service import (
    DataContributionService,
    TaskTemplateService,
    GoldenStandardTemplateService,
    ContributorAchievementService,
    ContributionRewardService,
)
from api.open_api import verify_api_key
from models.api_key import APIKeyDB

router = APIRouter(prefix="/api/contributions", tags=["contributions"])


# ==================== Pydantic 模型 ====================

class ContributionCreateRequest(BaseModel):
    """创建贡献请求。"""
    contribution_type: str = Field(..., description="贡献类型")
    title: str = Field(..., description="标题")
    description: str = Field(..., description="描述")
    content: dict = Field(..., description="贡献内容")
    related_task_id: Optional[str] = Field(None, description="关联任务 ID")


class ContributionResponse(BaseModel):
    """贡献响应。"""
    contribution_id: str
    contributor_id: str
    contribution_type: str
    title: str
    description: str
    status: str
    quality_score: Optional[float]
    reward_amount: Optional[float]
    usage_count: int
    upvotes: int
    downvotes: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContributionListResponse(BaseModel):
    """贡献列表响应。"""
    contributions: List[ContributionResponse]
    total: int


class VoteRequest(BaseModel):
    """投票请求。"""
    vote_type: str = Field(..., description="投票类型", pattern="^(upvote|downvote)$")


class TaskTemplateCreateRequest(BaseModel):
    """创建任务模板请求。"""
    template_name: str
    category: str
    title_template: str
    description_template: str
    acceptance_criteria_template: List = Field(default_factory=list)
    requirements_template: List = Field(default_factory=list)
    required_skills_template: dict = Field(default_factory=dict)


class TaskTemplateResponse(BaseModel):
    """任务模板响应。"""
    template_id: str
    template_name: str
    category: str
    title_template: str
    description_template: str
    usage_count: int
    success_rate: float
    created_at: datetime

    class Config:
        from_attributes = True


class GoldenStandardTemplateCreateRequest(BaseModel):
    """创建黄金标准测试模板请求。"""
    test_name: str
    category: str
    questions_template: List = Field(default_factory=list)
    passing_score_template: float = Field(default=80.0)


class GoldenStandardTemplateResponse(BaseModel):
    """黄金标准测试模板响应。"""
    gs_template_id: str
    test_name: str
    category: str
    usage_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class ContributorStatsResponse(BaseModel):
    """贡献者统计响应。"""
    total_contributions: int
    approved_contributions: int
    approval_rate: float
    total_rewards: float
    total_upvotes: int


class AchievementResponse(BaseModel):
    """成就响应。"""
    achievement_id: str
    achievement_type: str
    achievement_name: str
    achievement_description: str
    achievement_level: str
    progress: int
    target: int
    is_unlocked: bool
    unlocked_at: Optional[datetime]

    class Config:
        from_attributes = True


# ==================== 数据贡献管理 ====================

@router.post("", response_model=ContributionResponse)
async def create_contribution(
    request: ContributionCreateRequest,
    api_key: APIKeyDB = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    提交新的数据贡献。

    贡献类型包括：
    - task_template: 任务模板
    - golden_standard: 黄金标准测试题
    - training_data: 训练数据
    - feedback: 产品反馈
    - bug_report: Bug 报告
    """
    service = DataContributionService(db)

    contribution = await service.create_contribution(
        contributor_id=api_key.owner_id,
        contribution_type=request.contribution_type,
        title=request.title,
        description=request.description,
        content=request.content,
        related_task_id=request.related_task_id,
    )

    # 检查成就
    achievement_service = ContributorAchievementService(db)
    unlocked = await achievement_service.check_and_award_achievements(api_key.owner_id)

    return ContributionResponse(
        contribution_id=contribution.contribution_id,
        contributor_id=contribution.contributor_id,
        contribution_type=contribution.contribution_type,
        title=contribution.title,
        description=contribution.description,
        status=contribution.status,
        quality_score=contribution.quality_score,
        reward_amount=contribution.reward_amount,
        usage_count=contribution.usage_count,
        upvotes=contribution.upvotes,
        downvotes=contribution.downvotes,
        created_at=contribution.created_at,
        updated_at=contribution.updated_at,
    )


@router.get("", response_model=List[ContributionResponse])
async def list_contributions(
    contribution_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    api_key: APIKeyDB = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """列出贡献记录（支持筛选）。"""
    service = DataContributionService(db)
    contributions = await service.list_contributions(
        contributor_id=api_key.owner_id,
        contribution_type=contribution_type,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [
        ContributionResponse(
            contribution_id=c.contribution_id,
            contributor_id=c.contributor_id,
            contribution_type=c.contribution_type,
            title=c.title,
            description=c.description,
            status=c.status,
            quality_score=c.quality_score,
            reward_amount=c.reward_amount,
            usage_count=c.usage_count,
            upvotes=c.upvotes,
            downvotes=c.downvotes,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in contributions
    ]


@router.get("/{contribution_id}", response_model=ContributionResponse)
async def get_contribution(
    contribution_id: str,
    api_key: APIKeyDB = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """获取贡献详情。"""
    service = DataContributionService(db)
    contribution = await service.get_contribution(contribution_id)

    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")

    # 验证所有权或公开贡献
    if contribution.contributor_id != api_key.owner_id and contribution.status != "approved":
        raise HTTPException(status_code=403, detail="Access denied")

    return ContributionResponse(
        contribution_id=contribution.contribution_id,
        contributor_id=contribution.contributor_id,
        contribution_type=contribution.contribution_type,
        title=contribution.title,
        description=contribution.description,
        status=contribution.status,
        quality_score=contribution.quality_score,
        reward_amount=contribution.reward_amount,
        usage_count=contribution.usage_count,
        upvotes=contribution.upvotes,
        downvotes=contribution.downvotes,
        created_at=contribution.created_at,
        updated_at=contribution.updated_at,
    )


@router.post("/{contribution_id}/vote")
async def vote_contribution(
    contribution_id: str,
    request: VoteRequest,
    api_key: APIKeyDB = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """为贡献投票。"""
    service = DataContributionService(db)
    success = await service.add_vote(
        contribution_id=contribution_id,
        voter_id=api_key.owner_id,
        vote_type=request.vote_type,
    )
    if not success:
        raise HTTPException(status_code=400, detail="Already voted or invalid contribution")
    return {"message": "Vote recorded successfully"}


@router.get("/stats/me", response_model=ContributorStatsResponse)
async def get_contributor_stats(
    api_key: APIKeyDB = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """获取当前贡献者的统计信息。"""
    service = DataContributionService(db)
    stats = await service.get_contributor_stats(api_key.owner_id)
    return ContributorStatsResponse(**stats)


# ==================== 任务模板管理 ====================

@router.post("/templates/task", response_model=TaskTemplateResponse)
async def create_task_template(
    request: TaskTemplateCreateRequest,
    contribution_id: Optional[str] = None,
    api_key: APIKeyDB = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    创建任务模板贡献。

    任务模板可被其他用户复用，提高任务发布效率。
    """
    contribution_service = DataContributionService(db)
    template_service = TaskTemplateService(db)

    # 如果没有提供贡献 ID，先创建贡献记录
    if not contribution_id:
        contribution = await contribution_service.create_contribution(
            contributor_id=api_key.owner_id,
            contribution_type="task_template",
            title=f"任务模板：{request.template_name}",
            description=f"任务模板 - {request.category}",
            content={
                "title_template": request.title_template,
                "description_template": request.description_template,
                "acceptance_criteria_template": request.acceptance_criteria_template,
                "requirements_template": request.requirements_template,
                "required_skills_template": request.required_skills_template,
            },
        )
        contribution_id = contribution.contribution_id

    # 创建模板
    template = await template_service.create_template(
        contribution_id=contribution_id,
        template_name=request.template_name,
        category=request.category,
        title_template=request.title_template,
        description_template=request.description_template,
        acceptance_criteria_template=request.acceptance_criteria_template,
        requirements_template=request.requirements_template,
        required_skills_template=request.required_skills_template,
    )

    return TaskTemplateResponse(
        template_id=template.template_id,
        template_name=template.template_name,
        category=template.category,
        title_template=template.title_template,
        description_template=template.description_template,
        usage_count=template.usage_count,
        success_rate=template.success_rate,
        created_at=template.created_at,
    )


@router.get("/templates/task", response_model=List[TaskTemplateResponse])
async def list_task_templates(
    category: Optional[str] = None,
    limit: int = 20,
    api_key: APIKeyDB = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """列出任务模板（公开接口）。"""
    template_service = TaskTemplateService(db)
    templates = await template_service.list_templates(category=category, limit=limit)
    return [
        TaskTemplateResponse(
            template_id=t.template_id,
            template_name=t.template_name,
            category=t.category,
            title_template=t.title_template,
            description_template=t.description_template,
            usage_count=t.usage_count,
            success_rate=t.success_rate,
            created_at=t.created_at,
        )
        for t in templates
    ]


@router.get("/templates/task/{template_id}", response_model=TaskTemplateResponse)
async def get_task_template(
    template_id: str,
    api_key: APIKeyDB = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """获取任务模板详情。"""
    template_service = TaskTemplateService(db)
    template = await template_service.get_template(template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return TaskTemplateResponse(
        template_id=template.template_id,
        template_name=template.template_name,
        category=template.category,
        title_template=template.title_template,
        description_template=template.description_template,
        usage_count=template.usage_count,
        success_rate=template.success_rate,
        created_at=template.created_at,
    )


@router.post("/templates/task/{template_id}/use")
async def use_task_template(
    template_id: str,
    api_key: APIKeyDB = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """使用任务模板（增加使用计数）。"""
    template_service = TaskTemplateService(db)
    success = await template_service.increment_template_usage(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Template usage recorded"}


# ==================== 黄金标准测试模板 ====================

@router.post("/templates/golden-standard", response_model=GoldenStandardTemplateResponse)
async def create_golden_standard_template(
    request: GoldenStandardTemplateCreateRequest,
    contribution_id: Optional[str] = None,
    api_key: APIKeyDB = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    创建黄金标准测试模板贡献。

    黄金标准测试模板可用于批量任务的质量控制。
    """
    contribution_service = DataContributionService(db)
    gs_service = GoldenStandardTemplateService(db)

    # 如果没有提供贡献 ID，先创建贡献记录
    if not contribution_id:
        contribution = await contribution_service.create_contribution(
            contributor_id=api_key.owner_id,
            contribution_type="golden_standard",
            title=f"黄金标准测试：{request.test_name}",
            description=f"黄金标准测试模板 - {request.category}",
            content={
                "questions_template": request.questions_template,
                "passing_score_template": request.passing_score_template,
            },
        )
        contribution_id = contribution.contribution_id

    # 创建模板
    template = await gs_service.create_template(
        contribution_id=contribution_id,
        test_name=request.test_name,
        category=request.category,
        questions_template=request.questions_template,
        passing_score_template=request.passing_score_template,
    )

    return GoldenStandardTemplateResponse(
        gs_template_id=template.gs_template_id,
        test_name=template.test_name,
        category=template.category,
        usage_count=template.usage_count,
        created_at=template.created_at,
    )


@router.get("/templates/golden-standard", response_model=List[GoldenStandardTemplateResponse])
async def list_golden_standard_templates(
    category: Optional[str] = None,
    limit: int = 20,
    api_key: APIKeyDB = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """列出黄金标准测试模板（公开接口）。"""
    gs_service = GoldenStandardTemplateService(db)
    templates = await gs_service.list_templates(category=category, limit=limit)
    return [
        GoldenStandardTemplateResponse(
            gs_template_id=t.gs_template_id,
            test_name=t.test_name,
            category=t.category,
            usage_count=t.usage_count,
            created_at=t.created_at,
        )
        for t in templates
    ]


# ==================== 成就系统 ====================

@router.get("/achievements", response_model=List[AchievementResponse])
async def get_achievements(
    api_key: APIKeyDB = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """获取当前贡献者的所有成就。"""
    service = ContributorAchievementService(db)
    achievements = await service.get_contributor_achievements(api_key.owner_id)
    return [
        AchievementResponse(
            achievement_id=a.achievement_id,
            achievement_type=a.achievement_type,
            achievement_name=a.achievement_name,
            achievement_description=a.achievement_description,
            achievement_level=a.achievement_level,
            progress=a.progress,
            target=a.target,
            is_unlocked=a.is_unlocked,
            unlocked_at=a.unlocked_at,
        )
        for a in achievements
    ]
