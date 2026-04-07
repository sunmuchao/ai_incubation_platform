"""
职业发展支持 API。

v1.20.0 新增：职业发展支持功能
- 职业规划（长期目标/里程碑）
- 技能提升（学习资源/培训推荐）
- 就业指导（简历优化/面试辅导）
- 创业支持（商业计划/融资建议）
- 人脉拓展（引荐/内推）
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.career_development import (
    CareerGoalCreate,
    CareerGoalUpdate,
    GoalStatus,
    GoalType,
    SkillLevel,
    LearningResourceType,
    ConnectionType,
    FundingType,
    StartupStage,
)
from services.career_development_service import career_development_service

router = APIRouter(prefix="/api/career", tags=["career_development"])


# ========== 请求/响应模型 ==========

class CareerGoalCreateRequest(BaseModel):
    """创建职业目标请求。"""
    title: str
    description: str
    goal_type: GoalType
    target_date: Optional[str] = None
    related_skills: List[str] = Field(default_factory=list)
    milestones: List[Dict] = Field(default_factory=list)


class CareerGoalResponse(BaseModel):
    """职业目标响应。"""
    goal_id: str
    worker_id: str
    title: str
    description: str
    goal_type: GoalType
    status: GoalStatus
    target_date: Optional[str] = None
    progress: float
    milestones_count: int
    completed_milestones: int
    related_skills: List[str]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class MilestoneUpdateRequest(BaseModel):
    """更新里程碑状态请求。"""
    status: GoalStatus


class SkillAssessmentRequest(BaseModel):
    """技能评估请求。"""
    skill_name: str
    current_level: SkillLevel
    target_level: SkillLevel


class SkillImprovementPlanRequest(BaseModel):
    """技能提升计划请求。"""
    skill_name: str
    target_level: SkillLevel
    target_date: Optional[str] = None


class LearningProgressUpdateRequest(BaseModel):
    """更新学习进度请求。"""
    progress_percent: float
    resource_id: Optional[str] = None


class ResumeAnalysisRequest(BaseModel):
    """简历分析请求。"""
    resume_content: str


class InterviewPreparationRequest(BaseModel):
    """面试准备请求。"""
    job_title: str
    company_name: Optional[str] = None
    interview_type: str = "general"


class JobApplicationRequest(BaseModel):
    """求职申请请求。"""
    job_title: str
    company_name: str
    job_description: Optional[str] = None
    application_url: Optional[str] = None


class JobApplicationStatusUpdate(BaseModel):
    """更新求职申请状态请求。"""
    status: str


class BusinessIdeaRequest(BaseModel):
    """商业创意请求。"""
    title: str
    description: str
    target_market: str = ""
    value_proposition: str = ""


class BusinessPlanRequest(BaseModel):
    """商业计划书请求。"""
    title: str


class ConnectionRequest(BaseModel):
    """添加人脉连接请求。"""
    connected_worker_id: str
    connection_type: ConnectionType


class ReferralOpportunityRequest(BaseModel):
    """内推机会请求。"""
    job_title: str
    company_name: str
    job_description: str = ""
    referral_bonus: Optional[str] = None


class EventRegistrationRequest(BaseModel):
    """活动注册请求。"""
    worker_id: str


# ========== 职业规划 API ==========

@router.post("/goals", response_model=CareerGoalResponse)
async def create_career_goal(worker_id: str, request: CareerGoalCreateRequest):
    """
    创建职业目标。

    职业目标帮助工人设定清晰的发展方向，包括：
    - 短期目标（1-3 个月）
    - 中期目标（3-12 个月）
    - 长期目标（1-3 年）

    每个目标可以包含多个里程碑，用于跟踪进度。
    """
    data = CareerGoalCreate(
        worker_id=worker_id,
        title=request.title,
        description=request.description,
        goal_type=request.goal_type,
        target_date=datetime.fromisoformat(request.target_date) if request.target_date else None,
        related_skills=request.related_skills,
        milestones=request.milestones
    )

    goal = career_development_service.create_career_goal(data)

    return CareerGoalResponse(
        goal_id=goal.goal_id,
        worker_id=goal.worker_id,
        title=goal.title,
        description=goal.description,
        goal_type=goal.goal_type,
        status=goal.status,
        target_date=goal.target_date.isoformat() if goal.target_date else None,
        progress=goal.progress,
        milestones_count=len(goal.milestones),
        completed_milestones=sum(1 for m in goal.milestones if m.status == GoalStatus.COMPLETED),
        related_skills=goal.related_skills,
        created_at=goal.created_at.isoformat() if goal.created_at else None,
        updated_at=goal.updated_at.isoformat() if goal.updated_at else None
    )


@router.get("/goals/{goal_id}", response_model=CareerGoalResponse)
async def get_career_goal(goal_id: str):
    """获取职业目标详情。"""
    goal = career_development_service.get_career_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    return CareerGoalResponse(
        goal_id=goal.goal_id,
        worker_id=goal.worker_id,
        title=goal.title,
        description=goal.description,
        goal_type=goal.goal_type,
        status=goal.status,
        target_date=goal.target_date.isoformat() if goal.target_date else None,
        progress=goal.progress,
        milestones_count=len(goal.milestones),
        completed_milestones=sum(1 for m in goal.milestones if m.status == GoalStatus.COMPLETED),
        related_skills=goal.related_skills,
        created_at=goal.created_at.isoformat() if goal.created_at else None,
        updated_at=goal.updated_at.isoformat() if goal.updated_at else None
    )


@router.patch("/goals/{goal_id}", response_model=CareerGoalResponse)
async def update_career_goal(goal_id: str, request: CareerGoalUpdate):
    """更新职业目标。"""
    data = CareerGoalUpdate(**request.model_dump(exclude_unset=True))
    goal = career_development_service.update_career_goal(goal_id, data)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    return CareerGoalResponse(
        goal_id=goal.goal_id,
        worker_id=goal.worker_id,
        title=goal.title,
        description=goal.description,
        goal_type=goal.goal_type,
        status=goal.status,
        target_date=goal.target_date.isoformat() if goal.target_date else None,
        progress=goal.progress,
        milestones_count=len(goal.milestones),
        completed_milestones=sum(1 for m in goal.milestones if m.status == GoalStatus.COMPLETED),
        related_skills=goal.related_skills,
        created_at=goal.created_at.isoformat() if goal.created_at else None,
        updated_at=goal.updated_at.isoformat() if goal.updated_at else None
    )


@router.delete("/goals/{goal_id}")
async def delete_career_goal(goal_id: str):
    """删除职业目标。"""
    success = career_development_service.delete_career_goal(goal_id)
    if not success:
        raise HTTPException(status_code=404, detail="Goal not found")

    return {"message": "Goal deleted", "goal_id": goal_id}


@router.get("/workers/{worker_id}/goals")
async def list_worker_goals(
    worker_id: str,
    goal_type: Optional[GoalType] = None,
    status: Optional[GoalStatus] = None,
    skip: int = 0,
    limit: int = 100
):
    """列出工人的职业目标。"""
    goals = career_development_service.list_worker_goals(
        worker_id=worker_id,
        goal_type=goal_type,
        status=status,
        skip=skip,
        limit=limit
    )

    return {
        "worker_id": worker_id,
        "goals": [
            CareerGoalResponse(
                goal_id=g.goal_id,
                worker_id=g.worker_id,
                title=g.title,
                description=g.description,
                goal_type=g.goal_type,
                status=g.status,
                target_date=g.target_date.isoformat() if g.target_date else None,
                progress=g.progress,
                milestones_count=len(g.milestones),
                completed_milestones=sum(1 for m in g.milestones if m.status == GoalStatus.COMPLETED),
                related_skills=g.related_skills,
                created_at=g.created_at.isoformat() if g.created_at else None,
                updated_at=g.updated_at.isoformat() if g.updated_at else None
            )
            for g in goals
        ],
        "total": len(goals)
    }


@router.post("/goals/{goal_id}/milestones/{milestone_id}")
async def update_milestone_status(
    goal_id: str,
    milestone_id: str,
    request: MilestoneUpdateRequest
):
    """更新里程碑状态。"""
    goal = career_development_service.update_milestone_status(
        goal_id=goal_id,
        milestone_id=milestone_id,
        status=request.status
    )
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    return {
        "message": "Milestone updated",
        "goal_id": goal_id,
        "milestone_id": milestone_id,
        "new_status": request.status,
        "goal_progress": goal.progress
    }


# ========== 技能提升 API ==========

@router.post("/skills/assess")
async def assess_skill(worker_id: str, request: SkillAssessmentRequest):
    """
    评估技能水平。

    分析工人当前技能水平，识别优势和不足，并推荐学习资源。
    """
    assessment = career_development_service.assess_skill(
        worker_id=worker_id,
        skill_name=request.skill_name,
        current_level=request.current_level,
        target_level=request.target_level
    )

    return {
        "assessment_id": assessment.assessment_id,
        "worker_id": worker_id,
        "skill_name": assessment.skill_name,
        "current_level": assessment.current_level.value,
        "target_level": assessment.target_level.value,
        "score": assessment.score,
        "strengths": assessment.strengths,
        "weaknesses": assessment.weaknesses,
        "recommended_resources": assessment.recommended_resources
    }


@router.post("/skills/plan", response_model=Dict)
async def create_learning_plan(worker_id: str, request: SkillImprovementPlanRequest):
    """
    创建技能提升计划。

    基于工人当前水平和目标水平，制定个性化的学习计划，
    包括推荐的学习资源、预计完成时间等。
    """
    plan = career_development_service.create_learning_plan(
        worker_id=worker_id,
        skill_name=request.skill_name,
        target_level=request.target_level,
        target_date=datetime.fromisoformat(request.target_date) if request.target_date else None
    )

    return {
        "plan_id": plan.plan_id,
        "worker_id": plan.worker_id,
        "skill_name": plan.skill_name,
        "current_level": plan.current_level.value,
        "target_level": plan.target_level.value,
        "target_date": plan.target_date.isoformat() if plan.target_date else None,
        "status": plan.status.value,
        "resource_ids": plan.resource_ids,
        "weekly_hours": plan.weekly_hours,
        "progress": plan.progress
    }


@router.get("/skills/resources")
async def list_learning_resources(
    skill_name: Optional[str] = None,
    resource_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """列出学习资源。"""
    resources = career_development_service.list_learning_resources(
        skill_name=skill_name,
        resource_type=LearningResourceType(resource_type) if resource_type else None,
        difficulty=SkillLevel(difficulty) if difficulty else None,
        skip=skip,
        limit=limit
    )

    return {
        "resources": [
            {
                "resource_id": r.resource_id,
                "title": r.title,
                "description": r.description,
                "resource_type": r.resource_type.value,
                "skill_name": r.skill_name,
                "provider": r.provider,
                "url": r.url,
                "duration_hours": r.duration_hours,
                "difficulty": r.difficulty.value,
                "rating": r.rating,
                "is_free": r.is_free
            }
            for r in resources
        ],
        "total": len(resources)
    }


@router.get("/skills/resources/{resource_id}")
async def get_learning_resource(resource_id: str):
    """获取学习资源详情。"""
    resource = career_development_service.get_learning_resource(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    return {
        "resource_id": resource.resource_id,
        "title": resource.title,
        "description": resource.description,
        "resource_type": resource.resource_type.value,
        "skill_name": resource.skill_name,
        "provider": resource.provider,
        "url": resource.url,
        "duration_hours": resource.duration_hours,
        "difficulty": resource.difficulty.value,
        "rating": resource.rating,
        "is_free": resource.is_free,
        "prerequisites": resource.prerequisites
    }


@router.get("/skills/plans/{plan_id}")
async def get_learning_plan(plan_id: str):
    """获取学习计划详情。"""
    plan = career_development_service.get_learning_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    return {
        "plan_id": plan.plan_id,
        "worker_id": plan.worker_id,
        "skill_name": plan.skill_name,
        "current_level": plan.current_level.value,
        "target_level": plan.target_level.value,
        "status": plan.status.value,
        "progress": plan.progress,
        "resource_ids": plan.resource_ids
    }


@router.patch("/skills/plans/{plan_id}/progress")
async def update_learning_progress(plan_id: str, request: LearningProgressUpdateRequest):
    """更新学习进度。"""
    plan = career_development_service.update_learning_progress(
        plan_id=plan_id,
        progress_percent=request.progress_percent,
        resource_id=request.resource_id
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    return {
        "message": "Progress updated",
        "plan_id": plan_id,
        "new_progress": plan.progress,
        "status": plan.status.value
    }


# ========== 就业指导 API ==========

@router.post("/resume/analyze")
async def analyze_resume(worker_id: str, request: ResumeAnalysisRequest):
    """
    分析简历并提供反馈。

    分析简历的完整性、ATS 兼容性，并提供改进建议。
    """
    feedback = career_development_service.analyze_resume(
        worker_id=worker_id,
        resume_content=request.resume_content
    )

    return {
        "feedback_id": feedback.feedback_id,
        "worker_id": worker_id,
        "overall_score": feedback.overall_score,
        "section_scores": feedback.section_scores,
        "section_feedback": feedback.section_feedback,
        "suggestions": feedback.overall_suggestions,
        "ats_score": feedback.ats_score
    }


@router.post("/interview/prepare")
async def prepare_interview(worker_id: str, request: InterviewPreparationRequest):
    """
    准备面试。

    生成面试常见问题、提供面试技巧建议。
    支持通用面试、技术面试、行为面试等类型。
    """
    prep = career_development_service.prepare_interview(
        worker_id=worker_id,
        job_title=request.job_title,
        company_name=request.company_name,
        interview_type=request.interview_type
    )

    return {
        "prep_id": prep.prep_id,
        "worker_id": worker_id,
        "job_title": prep.job_title,
        "company_name": prep.company_name,
        "interview_type": prep.interview_type,
        "common_questions": prep.common_questions,
        "tips": prep.tips,
        "status": prep.preparation_status.value
    }


@router.post("/jobs/apply", response_model=Dict)
async def create_job_application(worker_id: str, request: JobApplicationRequest):
    """
    创建求职申请。

    跟踪求职申请状态，包括已申请、面试中、已 offer、已拒绝等。
    """
    application = career_development_service.create_job_application(
        worker_id=worker_id,
        job_title=request.job_title,
        company_name=request.company_name,
        job_description=request.job_description,
        application_url=request.application_url
    )

    return {
        "application_id": application.application_id,
        "worker_id": application.worker_id,
        "job_title": application.job_title,
        "company_name": application.company_name,
        "status": application.status,
        "applied_at": application.applied_at.isoformat() if application.applied_at else None
    }


@router.patch("/jobs/applications/{application_id}/status")
async def update_job_application_status(
    application_id: str,
    request: JobApplicationStatusUpdate
):
    """更新求职申请状态。"""
    application = career_development_service.update_job_application_status(
        application_id=application_id,
        status=request.status
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    return {
        "message": "Status updated",
        "application_id": application_id,
        "new_status": request.status
    }


@router.get("/workers/{worker_id}/applications")
async def list_job_applications(
    worker_id: str,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """列出求职申请。"""
    applications = career_development_service.list_job_applications(
        worker_id=worker_id,
        status=status,
        skip=skip,
        limit=limit
    )

    return {
        "worker_id": worker_id,
        "applications": [
            {
                "application_id": a.application_id,
                "job_title": a.job_title,
                "company_name": a.company_name,
                "status": a.status,
                "applied_at": a.applied_at.isoformat() if a.applied_at else None,
                "interview_rounds": a.interview_rounds,
                "notes": a.notes
            }
            for a in applications
        ],
        "total": len(applications)
    }


# ========== 创业支持 API ==========

@router.post("/startup/idea", response_model=Dict)
async def create_business_idea(worker_id: str, request: BusinessIdeaRequest):
    """
    创建商业创意。

    记录创业想法，包括目标市场、价值主张、竞争优势等。
    """
    idea = career_development_service.create_business_idea(
        worker_id=worker_id,
        title=request.title,
        description=request.description,
        target_market=request.target_market,
        value_proposition=request.value_proposition
    )

    return {
        "idea_id": idea.idea_id,
        "worker_id": idea.worker_id,
        "title": idea.title,
        "description": idea.description,
        "target_market": idea.target_market,
        "value_proposition": idea.value_proposition,
        "status": idea.status.value,
        "created_at": idea.created_at.isoformat() if idea.created_at else None
    }


@router.get("/startup/ideas/{idea_id}")
async def get_business_idea(idea_id: str):
    """获取商业创意详情。"""
    idea = career_development_service.get_business_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    return {
        "idea_id": idea.idea_id,
        "worker_id": idea.worker_id,
        "title": idea.title,
        "description": idea.description,
        "target_market": idea.target_market,
        "value_proposition": idea.value_proposition,
        "competitive_advantages": idea.competitive_advantages,
        "business_model": idea.business_model,
        "risks": idea.risks,
        "status": idea.status.value
    }


@router.post("/startup/ideas/{idea_id}/plan", response_model=Dict)
async def create_business_plan(idea_id: str, worker_id: str, request: BusinessPlanRequest):
    """创建商业计划书。"""
    plan = career_development_service.create_business_plan(
        idea_id=idea_id,
        worker_id=worker_id,
        title=request.title
    )

    return {
        "plan_id": plan.plan_id,
        "idea_id": plan.idea_id,
        "worker_id": plan.worker_id,
        "title": plan.title,
        "status": plan.status.value
    }


@router.get("/startup/funding-opportunities")
async def list_funding_opportunities(
    funding_type: Optional[str] = None,
    limit: int = 10
):
    """获取融资机会列表。"""
    opportunities = career_development_service.get_funding_opportunities(
        funding_type=FundingType(funding_type) if funding_type else None,
        limit=limit
    )

    return {
        "opportunities": [
            {
                "opportunity_id": o.opportunity_id,
                "title": o.title,
                "description": o.description,
                "funding_type": o.funding_type.value,
                "amount_range": o.amount_range,
                "investor_name": o.investor_name,
                "investor_type": o.investor_type,
                "requirements": o.requirements,
                "deadline": o.deadline.isoformat() if o.deadline else None,
                "application_url": o.application_url
            }
            for o in opportunities
        ],
        "total": len(opportunities)
    }


@router.post("/startup/mentor-match", response_model=Dict)
async def match_mentor(worker_id: str, mentor_areas: List[str]):
    """
    匹配导师。

    基于工人需求匹配合适的导师。
    """
    match = career_development_service.match_mentor(
        mentee_worker_id=worker_id,
        mentor_areas=mentor_areas
    )
    if not match:
        raise HTTPException(status_code=404, detail="Worker not found")

    return {
        "match_id": match.match_id,
        "mentee_worker_id": match.mentee_worker_id,
        "mentor_areas": match.mentorship_areas,
        "match_reasons": match.match_reasons,
        "match_score": match.match_score,
        "status": match.status.value
    }


# ========== 人脉拓展 API ==========

@router.post("/connections", response_model=Dict)
async def add_connection(worker_id: str, request: ConnectionRequest):
    """
    添加人脉连接。

    建立职业人脉关系，包括同事、导师、客户、合作伙伴等。
    """
    connection = career_development_service.add_connection(
        worker_id=worker_id,
        connected_worker_id=request.connected_worker_id,
        connection_type=request.connection_type
    )

    return {
        "connection_id": connection.connection_id,
        "worker_id": connection.worker_id,
        "connected_worker_id": connection.connected_worker_id,
        "connection_type": connection.connection_type.value,
        "common_skills": connection.common_skills,
        "common_interests": connection.common_interests,
        "status": connection.status
    }


@router.get("/workers/{worker_id}/connections")
async def list_connections(
    worker_id: str,
    connection_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """列出人脉连接。"""
    connections = career_development_service.list_connections(
        worker_id=worker_id,
        connection_type=ConnectionType(connection_type) if connection_type else None,
        skip=skip,
        limit=limit
    )

    return {
        "worker_id": worker_id,
        "connections": [
            {
                "connection_id": c.connection_id,
                "connected_worker_id": c.connected_worker_id,
                "connection_type": c.connection_type.value,
                "common_skills": c.common_skills,
                "common_interests": c.common_interests,
                "relationship_description": c.relationship_description,
                "status": c.status
            }
            for c in connections
        ],
        "total": len(connections)
    }


@router.post("/referrals", response_model=Dict)
async def create_referral_opportunity(worker_id: str, request: ReferralOpportunityRequest):
    """
    创建内推机会。

    发布内推职位，帮助他人获得工作机会。
    """
    referral = career_development_service.create_referral_opportunity(
        worker_id=worker_id,
        job_title=request.job_title,
        company_name=request.company_name,
        job_description=request.job_description,
        referral_bonus=request.referral_bonus
    )

    return {
        "referral_id": referral.referral_id,
        "worker_id": referral.worker_id,
        "job_title": referral.job_title,
        "company_name": referral.company_name,
        "status": referral.status,
        "referral_bonus": referral.referral_bonus
    }


@router.get("/referrals")
async def list_referral_opportunities(skip: int = 0, limit: int = 100):
    """列出内推机会。"""
    opportunities = career_development_service.list_referral_opportunities(
        skip=skip,
        limit=limit
    )

    return {
        "opportunities": [
            {
                "referral_id": o.referral_id,
                "job_title": o.job_title,
                "company_name": o.company_name,
                "job_description": o.job_description,
                "referral_bonus": o.referral_bonus,
                "status": o.status,
                "created_at": o.created_at.isoformat() if o.created_at else None
            }
            for o in opportunities
        ],
        "total": len(opportunities)
    }


@router.get("/networking-events")
async def list_networking_events(
    event_type: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """列出人脉活动。"""
    events = career_development_service.list_networking_events(
        event_type=event_type,
        status=status,
        skip=skip,
        limit=limit
    )

    return {
        "events": [
            {
                "event_id": e.event_id,
                "title": e.title,
                "description": e.description,
                "event_type": e.event_type,
                "start_date": e.start_date.isoformat(),
                "end_date": e.end_date.isoformat() if e.end_date else None,
                "location": e.location,
                "virtual_url": e.virtual_url,
                "organizer": e.organizer,
                "attendee_count": e.attendee_count,
                "status": e.status
            }
            for e in events
        ],
        "total": len(events)
    }


@router.post("/networking-events/{event_id}/register")
async def register_for_event(event_id: str, worker_id: str):
    """注册参加活动。"""
    event = career_development_service.register_for_event(
        event_id=event_id,
        worker_id=worker_id
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return {
        "message": "Registration successful",
        "event_id": event_id,
        "worker_id": worker_id,
        "attendee_count": event.attendee_count
    }


# ========== 综合分析 API ==========

@router.get("/workers/{worker_id}/summary")
async def get_career_summary(worker_id: str):
    """
    获取职业发展摘要。

    综合展示工人的职业发展状况，包括：
    - 目标完成情况
    - 技能提升进度
    - 学习时长统计
    - 人脉连接数
    - 求职申请状态
    - 内推机会数
    """
    summary = career_development_service.get_career_summary(worker_id)

    return {
        "worker_id": summary.worker_id,
        "active_goals": summary.active_goals,
        "completed_goals": summary.completed_goals,
        "skills_in_progress": summary.skills_in_progress,
        "learning_hours_total": summary.learning_hours_total,
        "resume_score": summary.resume_score,
        "connections_count": summary.connections_count,
        "upcoming_interviews": summary.upcoming_interviews,
        "referral_opportunities": summary.referral_opportunities
    }
