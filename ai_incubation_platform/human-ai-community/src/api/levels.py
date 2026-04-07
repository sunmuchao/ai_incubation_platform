"""
用户等级系统 API 路由
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.level_service import LevelService, ExperienceSourceType, get_level_service
from db.manager import db_manager

router = APIRouter(prefix="/api/levels", tags=["levels"])


class LevelInfo(BaseModel):
    """等级信息响应"""
    user_id: str
    level: int
    experience: int
    next_level: Optional[int]
    experience_to_next_level: int
    progress_percent: float
    title: str
    badge_color: str


class ExperienceHistoryItem(BaseModel):
    """经验历史项"""
    id: str
    source_type: str
    points: int
    description: str
    related_content_id: Optional[str]
    created_at: str


class LeaderboardItem(BaseModel):
    """排行榜项"""
    user_id: str
    name: str
    member_type: str
    level: int
    experience: int
    title: str


class CheckInResponse(BaseModel):
    """签到响应"""
    success: bool
    message: str
    points: int
    streak_days: int
    total_experience: Optional[int]
    leveled_up: Optional[bool]


@router.get("/{user_id}", response_model=LevelInfo)
async def get_user_level(user_id: str):
    """
    获取用户等级信息

    返回用户的当前等级、经验值、升级进度等信息。
    """
    async with db_manager.get_session() as db:
        level_service = get_level_service(db)
        level_info = await level_service.get_user_level(user_id)

        if not level_info:
            raise HTTPException(status_code=404, detail="User not found")

        return level_info


@router.get("/{user_id}/experience")
async def get_user_experience_history(
    user_id: str,
    days: int = Query(default=30, ge=1, le=365, description="查询天数"),
    limit: int = Query(default=100, ge=1, le=500, description="返回数量限制")
):
    """
    获取用户经验获取历史

    返回指定天数内的经验值获取记录。
    """
    async with db_manager.get_session() as db:
        level_service = get_level_service(db)
        try:
            history = await level_service.get_experience_history(
                user_id=user_id,
                days=days,
                limit=limit
            )
            return {
                "user_id": user_id,
                "days": days,
                "total_records": len(history),
                "history": history
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/{user_id}/checkin", response_model=CheckInResponse)
async def user_daily_checkin(user_id: str):
    """
    每日签到

    用户每日签到获取经验值奖励。
    """
    async with db_manager.get_session() as db:
        level_service = get_level_service(db)
        try:
            result = await level_service.daily_checkin(user_id)
            return result
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/leaderboard")
async def get_leaderboard(
    limit: int = Query(default=50, ge=1, le=100, description="返回数量"),
    level_filter: Optional[int] = Query(None, ge=1, le=18, description="等级筛选")
):
    """
    获取等级排行榜

    返回经验值排行榜，可选按等级筛选。
    """
    async with db_manager.get_session() as db:
        level_service = get_level_service(db)
        try:
            leaderboard = await level_service.get_leaderboard(
                limit=limit,
                level_filter=level_filter
            )
            return {
                "total": len(leaderboard),
                "leaderboard": leaderboard
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_level_config():
    """
    获取等级配置信息

    返回所有等级的配置信息，包括升级所需经验值和特权。
    """
    async with db_manager.get_session() as db:
        level_service = get_level_service(db)
        try:
            levels = await level_service.get_all_levels()
            return {
                "total_levels": len(levels),
                "levels": levels
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/privileges/{level}")
async def get_level_privileges(level: int):
    """
    获取指定等级的特权配置

    返回指定等级的所有特权配置信息。
    """
    if level < 1 or level > 18:
        raise HTTPException(status_code=400, detail="等级必须在 1-18 之间")

    async with db_manager.get_session() as db:
        level_service = get_level_service(db)
        try:
            privileges = await level_service.get_level_privileges(level)
            return {
                "level": level,
                "privileges": privileges
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/{user_id}/add-experience")
async def add_experience(
    user_id: str,
    source_type: str = Body(..., description="经验来源类型"),
    points: int = Body(..., description="经验值"),
    description: Optional[str] = Body(None, description="描述"),
    related_content_id: Optional[str] = Body(None, description="关联内容 ID")
):
    """
    手动添加经验值（管理员操作）

    用于手动奖励用户经验值，如活动奖励、补偿等。
    """
    valid_source_types = [e.value for e in ExperienceSourceType]
    if source_type not in valid_source_types:
        raise HTTPException(
            status_code=400,
            detail=f"无效的经验来源类型，必须是：{', '.join(valid_source_types)}"
        )

    async with db_manager.get_session() as db:
        level_service = get_level_service(db)
        try:
            result = await level_service.add_experience(
                user_id=user_id,
                source_type=ExperienceSourceType(source_type),
                points=points,
                description=description,
                related_content_id=related_content_id
            )
            return result
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/privilege/{privilege_type}")
async def check_user_privilege(
    user_id: str,
    privilege_type: str
):
    """
    检查用户是否拥有指定特权

    特权类型示例：
    - can_use_custom_title: 自定义头衔
    - priority_review: 优先审核
    - can_create_channels: 创建频道
    """
    async with db_manager.get_session() as db:
        level_service = get_level_service(db)
        try:
            has_privilege = await level_service.check_user_privilege(
                user_id=user_id,
                privilege_type=privilege_type
            )
            return {
                "user_id": user_id,
                "privilege_type": privilege_type,
                "has_privilege": has_privilege
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
