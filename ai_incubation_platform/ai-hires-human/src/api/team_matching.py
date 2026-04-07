"""
团队匹配 API - v1.16 新增核心功能。

提供以下 API 端点：
1. 工人画像管理
2. 任务需求定义
3. 团队匹配与组建
4. 批量任务分配
5. 团队绩效查询
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# 支持从 src 目录导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from services.team_matching_service import (
    team_matching_service,
    MemberRole,
    TeamMatchStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/team-matching", tags=["team-matching"])


# ==================== 数据模型 ====================

class WorkerProfileCreate(BaseModel):
    """创建工人画像请求。"""
    worker_id: str = Field(..., description="工人 ID")
    skills: Dict[str, float] = Field(..., description="技能字典：skill_name -> proficiency (0-1)")
    preferred_roles: Optional[List[str]] = Field(default=None, description="偏好角色列表")
    hourly_rate: float = Field(default=0.0, description="期望时薪")
    max_workload: int = Field(default=5, description="最大同时任务数")


class WorkerProfileResponse(BaseModel):
    """工人画像响应。"""
    worker_id: str
    skills: Dict[str, float]
    availability: float
    reputation_score: float
    completed_tasks: int
    success_rate: float
    preferred_roles: List[str]
    hourly_rate: float
    max_workload: int
    current_workload: int
    composite_score: float


class WorkerStatsUpdate(BaseModel):
    """更新工人统计数据请求。"""
    completed_tasks: Optional[int] = None
    success_rate: Optional[float] = None
    reputation_score: Optional[float] = None


class TaskRequirementCreate(BaseModel):
    """创建任务需求请求。"""
    task_id: str = Field(..., description="任务 ID")
    required_skills: Dict[str, float] = Field(..., description="所需技能：skill_name -> min_proficiency")
    preferred_role: Optional[str] = Field(default=None, description="偏好角色")
    estimated_effort: int = Field(default=1, description="预估工作量单位")
    priority: int = Field(default=1, ge=1, le=5, description="优先级 (1-5)")
    deadline: Optional[str] = Field(default=None, description="截止时间 (ISO 8601)")


class TaskRequirementResponse(BaseModel):
    """任务需求响应。"""
    task_id: str
    required_skills: Dict[str, float]
    preferred_role: Optional[str]
    estimated_effort: int
    priority: int
    deadline: Optional[str]


class MatchResultResponse(BaseModel):
    """匹配结果响应。"""
    task_id: str
    matched_workers: List[str]
    match_scores: Dict[str, float]
    match_reason: str
    confidence: float


class TeamCompositionResponse(BaseModel):
    """团队组成响应。"""
    team_id: str
    project_id: str
    members: Dict[str, str]  # worker_id -> role
    created_at: str
    status: str
    total_reputation: float
    skill_coverage: Dict[str, float]


class TeamPerformanceResponse(BaseModel):
    """团队绩效响应。"""
    team_id: str
    completed_projects: int
    success_rate: float
    average_delivery_time: float
    client_satisfaction: float
    member_satisfaction: float
    last_updated: str


class BatchMatchRequest(BaseModel):
    """批量匹配请求。"""
    task_ids: List[str] = Field(..., description="任务 ID 列表")
    match_strategy: str = Field(default="greedy", description="匹配策略：greedy, optimal, round_robin")


class BatchMatchResponse(BaseModel):
    """批量匹配响应。"""
    total_tasks: int
    matched_count: int
    results: Dict[str, MatchResultResponse]


class ProjectTeamMatchRequest(BaseModel):
    """项目团队匹配请求。"""
    project_id: str = Field(..., description="项目 ID")
    task_requirements: List[TaskRequirementCreate] = Field(..., description="任务需求列表")
    max_team_size: int = Field(default=10, description="最大团队规模")


class TeamPerformanceRecord(BaseModel):
    """团队绩效记录请求。"""
    success: bool = Field(..., description="是否成功")
    delivery_time_hours: float = Field(..., description="交付时间（小时）")
    client_rating: float = Field(..., ge=0, le=5, description="客户评分 (0-5)")
    member_ratings: Optional[List[float]] = Field(default=None, description="成员评分列表")


# ==================== 工人画像管理 API ====================

@router.post("/workers/profile", response_model=WorkerProfileResponse, summary="注册/更新工人画像")
async def register_worker_profile(request: WorkerProfileCreate):
    """
    注册或更新工人画像。

    工人画像用于智能匹配，包含：
    - 技能列表及熟练度
    - 偏好角色
    - 工作负载限制
    """
    profile = team_matching_service.register_worker(
        worker_id=request.worker_id,
        skills=request.skills,
        preferred_roles=request.preferred_roles,
        hourly_rate=request.hourly_rate,
        max_workload=request.max_workload,
    )

    return WorkerProfileResponse(
        worker_id=profile.worker_id,
        skills=profile.skills,
        availability=profile.availability,
        reputation_score=profile.reputation_score,
        completed_tasks=profile.completed_tasks,
        success_rate=profile.success_rate,
        preferred_roles=profile.preferred_roles,
        hourly_rate=profile.hourly_rate,
        max_workload=profile.max_workload,
        current_workload=profile.current_workload,
        composite_score=profile.get_composite_score(),
    )


@router.get("/workers/{worker_id}/profile", response_model=WorkerProfileResponse, summary="获取工人画像")
async def get_worker_profile(worker_id: str):
    """获取指定工人的画像信息。"""
    profile = team_matching_service.get_worker_profile(worker_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Worker {worker_id} not found")

    return WorkerProfileResponse(
        worker_id=profile.worker_id,
        skills=profile.skills,
        availability=profile.availability,
        reputation_score=profile.reputation_score,
        completed_tasks=profile.completed_tasks,
        success_rate=profile.success_rate,
        preferred_roles=profile.preferred_roles,
        hourly_rate=profile.hourly_rate,
        max_workload=profile.max_workload,
        current_workload=profile.current_workload,
        composite_score=profile.get_composite_score(),
    )


@router.put("/workers/{worker_id}/stats", response_model=WorkerProfileResponse, summary="更新工人统计")
async def update_worker_stats(worker_id: str, request: WorkerStatsUpdate):
    """更新工人的统计数据（完成数、成功率、信誉分）。"""
    profile = team_matching_service.update_worker_stats(
        worker_id=worker_id,
        completed_tasks=request.completed_tasks,
        success_rate=request.success_rate,
        reputation_score=request.reputation_score,
    )
    if not profile:
        raise HTTPException(status_code=404, detail=f"Worker {worker_id} not found")

    return WorkerProfileResponse(
        worker_id=profile.worker_id,
        skills=profile.skills,
        availability=profile.availability,
        reputation_score=profile.reputation_score,
        completed_tasks=profile.completed_tasks,
        success_rate=profile.success_rate,
        preferred_roles=profile.preferred_roles,
        hourly_rate=profile.hourly_rate,
        max_workload=profile.max_workload,
        current_workload=profile.current_workload,
        composite_score=profile.get_composite_score(),
    )


@router.get("/workers/available", response_model=List[WorkerProfileResponse], summary="获取可用工人列表")
async def list_available_workers(
    min_availability: float = Query(default=0.5, ge=0, le=1),
    limit: int = Query(default=100, ge=1, le=1000),
):
    """获取当前可用的工人列表（按综合评分排序）。"""
    workers = team_matching_service.list_available_workers(
        min_availability=min_availability,
        limit=limit,
    )

    return [
        WorkerProfileResponse(
            worker_id=w.worker_id,
            skills=w.skills,
            availability=w.availability,
            reputation_score=w.reputation_score,
            completed_tasks=w.completed_tasks,
            success_rate=w.success_rate,
            preferred_roles=w.preferred_roles,
            hourly_rate=w.hourly_rate,
            max_workload=w.max_workload,
            current_workload=w.current_workload,
            composite_score=w.get_composite_score(),
        )
        for w in workers
    ]


# ==================== 任务需求管理 API ====================

@router.post("/tasks/requirement", response_model=TaskRequirementResponse, summary="定义任务需求")
async def define_task_requirement(request: TaskRequirementCreate):
    """
    定义任务需求用于智能匹配。

    必需字段：
    - task_id: 任务 ID
    - required_skills: 所需技能及最低熟练度
    """
    requirement = team_matching_service.define_task_requirement(
        task_id=request.task_id,
        required_skills=request.required_skills,
        preferred_role=request.preferred_role,
        estimated_effort=request.estimated_effort,
        priority=request.priority,
        deadline=request.deadline,
    )

    return TaskRequirementResponse(
        task_id=requirement.task_id,
        required_skills=requirement.required_skills,
        preferred_role=requirement.preferred_role,
        estimated_effort=requirement.estimated_effort,
        priority=requirement.priority,
        deadline=requirement.deadline,
    )


@router.get("/tasks/{task_id}/requirement", response_model=TaskRequirementResponse, summary="获取任务需求")
async def get_task_requirement(task_id: str):
    """获取指定任务的需求定义。"""
    requirement = team_matching_service.get_task_requirement(task_id)
    if not requirement:
        raise HTTPException(status_code=404, detail=f"Task requirement for {task_id} not found")

    return TaskRequirementResponse(
        task_id=requirement.task_id,
        required_skills=requirement.required_skills,
        preferred_role=requirement.preferred_role,
        estimated_effort=requirement.estimated_effort,
        priority=requirement.priority,
        deadline=requirement.deadline,
    )


# ==================== 团队匹配 API ====================

@router.post("/match/task", response_model=MatchResultResponse, summary="匹配单个任务")
async def match_task(
    task_id: str,
    candidate_workers: Optional[List[str]] = Query(default=None, description="候选工人列表"),
):
    """
    为单个任务匹配最合适的工人。

    匹配逻辑：
    1. 技能匹配度检查
    2. 角色偏好匹配
    3. 可用性验证
    4. 综合评分排序
    """
    # 如果任务需求未定义，尝试自动创建
    requirement = team_matching_service.get_task_requirement(task_id)
    if not requirement:
        raise HTTPException(
            status_code=400,
            detail=f"Task requirement not defined for {task_id}. Please define requirements first."
        )

    result = team_matching_service.match_worker_to_task(task_id, candidate_workers)
    if not result:
        raise HTTPException(status_code=400, detail="Matching failed")

    if not result.matched_workers:
        return MatchResultResponse(
            task_id=result.task_id,
            matched_workers=result.matched_workers,
            match_scores=result.match_scores,
            match_reason=result.match_reason,
            confidence=result.confidence,
        )

    return MatchResultResponse(
        task_id=result.task_id,
        matched_workers=result.matched_workers,
        match_scores=result.match_scores,
        match_reason=result.match_reason,
        confidence=result.confidence,
    )


@router.post("/match/batch", response_model=BatchMatchResponse, summary="批量匹配任务")
async def batch_match_tasks(request: BatchMatchRequest):
    """
    批量匹配多个任务。

    支持三种策略：
    - greedy: 贪心算法，每个任务选当前最佳
    - optimal: 全局最优，考虑任务间竞争
    - round_robin: 轮询分配，保证负载均衡
    """
    results = team_matching_service.batch_match_tasks(
        task_ids=request.task_ids,
        match_strategy=request.match_strategy,
    )

    matched_results = {}
    for task_id, result in results.items():
        matched_results[task_id] = MatchResultResponse(
            task_id=result.task_id,
            matched_workers=result.matched_workers,
            match_scores=result.match_scores,
            match_reason=result.match_reason,
            confidence=result.confidence,
        )

    return BatchMatchResponse(
        total_tasks=len(request.task_ids),
        matched_count=len(matched_results),
        results=matched_results,
    )


@router.post("/match/project", response_model=TeamCompositionResponse, summary="为项目组建团队")
async def match_project_team(request: ProjectTeamMatchRequest):
    """
    为项目自动组建团队（多角色协同匹配）。

    匹配逻辑：
    1. 分析项目所需的全部技能和角色
    2. 寻找技能互补的工人组合
    3. 确保团队整体能力覆盖所有需求
    4. 优化团队规模和效率
    """
    # 转换任务需求
    requirements = [
        team_matching_service.define_task_requirement(
            task_id=req.task_id,
            required_skills=req.required_skills,
            preferred_role=req.preferred_role,
            estimated_effort=req.estimated_effort,
            priority=req.priority,
            deadline=req.deadline,
        )
        for req in request.task_requirements
    ]

    team = team_matching_service.match_team_to_project(
        project_id=request.project_id,
        task_requirements=requirements,
        max_team_size=request.max_team_size,
    )

    if not team:
        raise HTTPException(status_code=400, detail="Failed to form team for project")

    return TeamCompositionResponse(
        team_id=team.team_id,
        project_id=team.project_id,
        members=team.members,
        created_at=team.created_at.isoformat(),
        status=team.status,
        total_reputation=team.total_reputation,
        skill_coverage=team.skill_coverage,
    )


# ==================== 团队管理 API ====================

@router.get("/teams/{team_id}", response_model=TeamCompositionResponse, summary="获取团队组成")
async def get_team_composition(team_id: str):
    """获取指定团队的组成信息。"""
    team = team_matching_service.get_team_composition(team_id)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found")

    return TeamCompositionResponse(
        team_id=team.team_id,
        project_id=team.project_id,
        members=team.members,
        created_at=team.created_at.isoformat(),
        status=team.status,
        total_reputation=team.total_reputation,
        skill_coverage=team.skill_coverage,
    )


@router.get("/teams/{team_id}/performance", response_model=TeamPerformanceResponse, summary="获取团队绩效")
async def get_team_performance(team_id: str):
    """获取团队的绩效统计。"""
    perf = team_matching_service.get_team_performance(team_id)
    if not perf:
        raise HTTPException(status_code=404, detail=f"Team performance for {team_id} not found")

    return TeamPerformanceResponse(
        team_id=perf.team_id,
        completed_projects=perf.completed_projects,
        success_rate=perf.success_rate,
        average_delivery_time=perf.average_delivery_time,
        client_satisfaction=perf.client_satisfaction,
        member_satisfaction=perf.member_satisfaction,
        last_updated=perf.last_updated.isoformat(),
    )


@router.post("/teams/{team_id}/performance", response_model=TeamPerformanceResponse, summary="记录团队绩效")
async def record_team_performance(team_id: str, request: TeamPerformanceRecord):
    """记录项目完成后的团队绩效。"""
    perf = team_matching_service.record_team_performance(
        team_id=team_id,
        success=request.success,
        delivery_time_hours=request.delivery_time_hours,
        client_rating=request.client_rating,
        member_ratings=request.member_ratings,
    )

    if not perf:
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found")

    return TeamPerformanceResponse(
        team_id=perf.team_id,
        completed_projects=perf.completed_projects,
        success_rate=perf.success_rate,
        average_delivery_time=perf.average_delivery_time,
        client_satisfaction=perf.client_satisfaction,
        member_satisfaction=perf.member_satisfaction,
        last_updated=perf.last_updated.isoformat(),
    )


@router.get("/match/history", summary="获取匹配历史")
async def get_match_history(
    limit: int = Query(default=100, ge=1, le=1000),
    match_type: Optional[str] = Query(default=None, description="匹配类型过滤"),
):
    """获取匹配历史记录。"""
    history = team_matching_service.get_match_history(limit=limit, match_type=match_type)
    return {"history": history, "total": len(history)}
