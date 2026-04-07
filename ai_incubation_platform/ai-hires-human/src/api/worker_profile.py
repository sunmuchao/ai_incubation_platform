"""
工人能力画像 API。
"""
from __future__ import annotations

import os
import sys
from typing import List, Optional

from fastapi import APIRouter, HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.worker_profile import (
    WorkerProfile,
    WorkerProfileCreate,
    WorkerProfileUpdate,
    WorkerStats,
    WorkerListResponse,
)
from services.worker_profile_service import worker_profile_service

router = APIRouter(prefix="/api/workers", tags=["workers"])


@router.get("", response_model=WorkerListResponse)
async def list_workers(
    skip: int = 0,
    limit: int = 100,
):
    """列出所有工人画像（分页）。"""
    profiles = worker_profile_service.list_profiles(skip=skip, limit=limit)
    return WorkerListResponse(
        workers=profiles,
        total=len(worker_profile_service._profiles),
        skip=skip,
        limit=limit,
    )


@router.get("/search", response_model=List[WorkerProfile])
async def search_workers(
    skills: Optional[str] = None,
    location: Optional[str] = None,
    min_level: int = 0,
    min_rating: float = 0.0,
    min_success_rate: float = 0.0,
    skip: int = 0,
    limit: int = 100,
):
    """
    搜索工人画像。

    - skills: 技能标签，逗号分隔（如：线下采集，数据标注）
    - location: 地点模糊匹配
    - min_level: 最低等级
    - min_rating: 最低评分
    - min_success_rate: 最低成功率
    """
    skills_list = [s.strip() for s in skills.split(",")] if skills else None
    profiles = worker_profile_service.search_profiles(
        skills=skills_list,
        location=location,
        min_level=min_level,
        min_rating=min_rating,
        min_success_rate=min_success_rate,
        skip=skip,
        limit=limit,
    )
    return profiles


@router.get("/{worker_id}", response_model=WorkerProfile)
async def get_worker_profile(worker_id: str):
    """获取工人画像详情。"""
    profile = worker_profile_service.get_profile(worker_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Worker profile not found")
    return profile


@router.post("/{worker_id}", response_model=WorkerProfile)
async def create_or_update_worker_profile(
    worker_id: str,
    profile_data: WorkerProfileCreate,
):
    """创建或更新工人画像。"""
    # 如果已存在则更新，否则创建
    existing = worker_profile_service.get_profile(worker_id)
    if existing:
        update_data = WorkerProfileUpdate(
            name=profile_data.name,
            avatar=profile_data.avatar,
            phone=profile_data.phone,
            email=profile_data.email,
            location=profile_data.location,
            skills=profile_data.skills,
            level=profile_data.level,
            tags=profile_data.tags,
            external_profile_id=profile_data.external_profile_id,
        )
        profile = worker_profile_service.update_profile(worker_id, update_data)
    else:
        profile = worker_profile_service.create_profile(profile_data)
    return profile


@router.patch("/{worker_id}", response_model=WorkerProfile)
async def update_worker_profile(
    worker_id: str,
    profile_data: WorkerProfileUpdate,
):
    """部分更新工人画像。"""
    profile = worker_profile_service.update_profile(worker_id, profile_data)
    if not profile:
        raise HTTPException(status_code=404, detail="Worker profile not found")
    return profile


@router.delete("/{worker_id}")
async def delete_worker_profile(worker_id: str):
    """删除工人画像。"""
    success = worker_profile_service.delete_profile(worker_id)
    if not success:
        raise HTTPException(status_code=404, detail="Worker profile not found")
    return {"message": "Worker profile deleted", "worker_id": worker_id}


@router.get("/{worker_id}/stats", response_model=WorkerStats)
async def get_worker_stats(worker_id: str):
    """获取工人统计数据。"""
    profile = worker_profile_service.get_profile(worker_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Worker profile not found")
    return worker_profile_service.get_worker_stats(worker_id)


@router.post("/{worker_id}/task-complete")
async def record_task_completion(
    worker_id: str,
    task_id: str,
    reward: float,
    rating: Optional[float] = None,
    success: bool = True,
):
    """记录任务完成，更新工人画像统计。"""
    profile = worker_profile_service.record_task_completion(
        worker_id=worker_id,
        task_id=task_id,
        reward=reward,
        rating=rating,
        success=success,
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Worker profile not found")
    return {
        "message": "Task completion recorded",
        "worker_id": worker_id,
        "task_id": task_id,
        "updated_profile": profile,
    }


@router.post("/sync-external")
async def sync_external_profile(
    worker_id: str,
    external_data: dict,
):
    """从外部系统同步工人画像数据。"""
    profile = worker_profile_service.sync_from_external(worker_id, external_data)
    return {
        "message": "Worker profile synced",
        "worker_id": worker_id,
        "profile": profile,
    }
