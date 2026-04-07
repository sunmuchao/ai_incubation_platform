"""
智能推荐 API - 提供任务推荐和匹配服务。

v1.16.0 新增：
- 雇主端推荐 API：为任务推荐合适的工人
- 详细推荐解释报告
"""
from __future__ import annotations

import os
import sys
from typing import List, Optional

from fastapi import APIRouter, HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.worker_profile import (
    WorkerPreferenceUpdate,
    RecommendationRequest,
    RecommendationResponse,
    TaskRecommendation,
    WorkerRecommendation,
    EmployerRecommendationRequest,
    EmployerRecommendationResponse,
    RecommendationExplanation,
)
from models.task import TaskStatus
from services.worker_profile_service import worker_profile_service
from services.task_service import task_service
from services.recommendation_service import recommendation_service

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.post("/tasks", response_model=RecommendationResponse)
async def recommend_tasks_for_worker(request: RecommendationRequest):
    """
    为工人推荐任务。

    推荐算法基于：
    1. 技能匹配 (40%): 工人技能与任务需求的匹配度
    2. 偏好匹配 (30%): 交互类型、报酬、时长偏好
    3. 质量匹配 (20%): 工人可信度和质量等级
    4. 时效匹配 (10%): 活跃时段和任务紧急度

    返回匹配度>20 分的任务，按匹配分数降序排列
    """
    # 获取工人画像
    worker = worker_profile_service.get_profile(request.worker_id)
    if not worker:
        raise HTTPException(
            status_code=404,
            detail=f"Worker not found: {request.worker_id}"
        )

    # 获取所有已发布的任务
    all_tasks = list(task_service.list_tasks(status=TaskStatus.PUBLISHED))

    # 生成推荐
    recommendations = recommendation_service.recommend_tasks_for_worker(
        worker=worker,
        available_tasks=all_tasks,
        limit=request.limit
    )

    return RecommendationResponse(
        worker_id=request.worker_id,
        recommendations=recommendations,
        total_available=len(recommendations)
    )


@router.get("/tasks/{worker_id}", response_model=List[TaskRecommendation])
async def get_recommendations_for_worker(
    worker_id: str,
    limit: int = 10
):
    """简化的推荐接口，直接返回推荐任务列表。"""
    worker = worker_profile_service.get_profile(worker_id)
    if not worker:
        raise HTTPException(
            status_code=404,
            detail=f"Worker not found: {worker_id}"
        )

    all_tasks = list(task_service.list_tasks(status=TaskStatus.PUBLISHED))

    recommendations = recommendation_service.recommend_tasks_for_worker(
        worker=worker,
        available_tasks=all_tasks,
        limit=limit
    )

    return recommendations


@router.get("/tasks/{worker_id}/{task_id}/explain")
async def get_recommendation_explanation(
    worker_id: str,
    task_id: str
):
    """获取特定任务的推荐解释。"""
    worker = worker_profile_service.get_profile(worker_id)
    if not worker:
        raise HTTPException(
            status_code=404,
            detail=f"Worker not found: {worker_id}"
        )

    task = task_service.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )

    score, dimension_scores, reasons = recommendation_service.calculate_match_score(
        worker, task
    )

    return {
        "worker_id": worker_id,
        "task_id": task_id,
        "match_score": round(score, 2),
        "dimension_scores": {k: round(v, 2) for k, v in dimension_scores.items()},
        "match_reasons": reasons,
        "recommendation_level": (
            "强烈推荐" if score >= 80 else
            "推荐" if score >= 60 else
            "可以考虑" if score >= 40 else
            "匹配度较低"
        )
    }


@router.patch("/workers/{worker_id}/preferences")
async def update_worker_preferences(
    worker_id: str,
    preferences: WorkerPreferenceUpdate
):
    """更新工人任务偏好设置。"""
    worker = worker_profile_service.get_profile(worker_id)
    if not worker:
        raise HTTPException(
            status_code=404,
            detail=f"Worker not found: {worker_id}"
        )

    # 更新偏好字段
    update_data = preferences.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(worker, field, value)

    worker.updated_at = __import__("datetime").datetime.now()

    return {
        "message": "Preferences updated",
        "worker_id": worker_id,
        "preferences": {
            "preferred_interaction_types": worker.preferred_interaction_types,
            "min_reward_preference": worker.min_reward_preference,
            "max_task_duration_hours": worker.max_task_duration_hours,
            "active_hours": worker.active_hours
        }
    }


@router.get("/workers/{worker_id}/preferences")
async def get_worker_preferences(worker_id: str):
    """获取工人任务偏好设置。"""
    worker = worker_profile_service.get_profile(worker_id)
    if not worker:
        raise HTTPException(
            status_code=404,
            detail=f"Worker not found: {worker_id}"
        )

    return {
        "worker_id": worker_id,
        "preferences": {
            "preferred_interaction_types": worker.preferred_interaction_types,
            "min_reward_preference": worker.min_reward_preference,
            "max_task_duration_hours": worker.max_task_duration_hours,
            "active_hours": worker.active_hours
        }
    }


# ===== v1.16.0 新增：雇主端推荐 API =====

@router.post("/workers", response_model=EmployerRecommendationResponse)
async def recommend_workers_for_task(request: EmployerRecommendationRequest):
    """
    为任务推荐合适的工人。

    推荐算法基于：
    1. 技能匹配 (40%): 工人技能与任务需求的匹配度
    2. 偏好匹配 (30%): 交互类型、报酬、时长偏好
    3. 质量匹配 (20%): 工人可信度和质量等级
    4. 时效匹配 (10%): 活跃时段和任务紧急度
    5. 历史表现 (15%): 工人历史任务表现
    6. 薪资匹配 (10%): 工人期望报酬与任务报酬匹配

    返回匹配度>20 分的工人，按匹配分数降序排列
    """
    # 获取任务
    task = task_service.get_task(request.task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {request.task_id}"
        )

    # 获取所有工人
    all_workers = worker_profile_service.list_all_workers()

    # 生成推荐
    recommendations = recommendation_service.recommend_workers_for_task(
        task=task,
        available_workers=all_workers,
        limit=request.limit
    )

    return EmployerRecommendationResponse(
        task_id=request.task_id,
        recommendations=recommendations,
        total_available=len(recommendations)
    )


@router.get("/tasks/{task_id}/workers", response_model=List[WorkerRecommendation])
async def get_worker_recommendations_for_task(
    task_id: str,
    limit: int = 10
):
    """简化的推荐接口，为任务推荐工人。"""
    task = task_service.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )

    all_workers = worker_profile_service.list_all_workers()

    recommendations = recommendation_service.recommend_workers_for_task(
        task=task,
        available_workers=all_workers,
        limit=limit
    )

    return recommendations


@router.get("/explanation/{task_id}/{worker_id}", response_model=RecommendationExplanation)
async def get_detailed_recommendation_explanation(
    task_id: str,
    worker_id: str
):
    """
    获取详细的推荐解释报告。

    返回：
    - overall_score: 综合匹配分数
    - dimension_scores: 各维度分数
    - match_reasons: 匹配原因列表
    - recommendation_level: 推荐等级
    - skill_match_details: 技能匹配详情
    - historical_performance_details: 历史表现详情
    """
    task = task_service.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )

    worker = worker_profile_service.get_profile(worker_id)
    if not worker:
        raise HTTPException(
            status_code=404,
            detail=f"Worker not found: {worker_id}"
        )

    explanation = recommendation_service.get_detailed_recommendation_explanation(
        worker=worker,
        task=task
    )

    return RecommendationExplanation(**explanation)
