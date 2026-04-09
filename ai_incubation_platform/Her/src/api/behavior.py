"""
用户行为与画像 API 路由 - P3

提供行为追踪、动态画像相关接口
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, Any, List

from db.database import get_db
from db.repositories import UserRepository
from services.behavior_tracking_service import behavior_service
from services.dynamic_profile_service import dynamic_profile_service
from utils.logger import logger

router = APIRouter(prefix="/api/behavior", tags=["behavior"])


def get_user_service(db=Depends(get_db)):
    """获取用户服务依赖注入"""
    return UserRepository(db)


@router.post("/track")
async def track_behavior_event(
    user_id: str,
    event_type: str,
    target_id: Optional[str] = None,
    event_data: Optional[Dict[str, Any]] = None
):
    """
    追踪用户行为事件

    Args:
        user_id: 用户 ID
        event_type: 事件类型 (profile_view, like, pass, search, etc.)
        target_id: 目标用户 ID（可选）
        event_data: 事件详情数据
    """
    logger.info(f"Tracking behavior: {event_type} for user {user_id}")

    event_id = behavior_service.record_event(
        user_id=user_id,
        event_type=event_type,
        target_id=target_id,
        event_data=event_data
    )

    return {
        "event_id": event_id,
        "status": "recorded"
    }


@router.get("/summary/{user_id}")
async def get_behavior_summary(
    user_id: str,
    days: int = 7
):
    """
    获取用户行为摘要

    Args:
        user_id: 用户 ID
        days: 统计天数
    """
    summary = behavior_service.get_user_behavior_summary(user_id, days=days)

    return {
        "user_id": user_id,
        "period_days": days,
        "summary": summary
    }


@router.get("/preference-shift/{user_id}")
async def get_preference_shift(
    user_id: str,
    days: int = 14
):
    """
    分析用户偏好变化趋势

    Args:
        user_id: 用户 ID
        days: 分析天数
    """
    analysis = behavior_service.analyze_preference_shift(user_id, days=days)

    return {
        "user_id": user_id,
        "period_days": days,
        "analysis": analysis
    }


@router.post("/profile/update/{user_id}")
async def update_user_profile(
    user_id: str,
    service=Depends(get_user_service)
):
    """
    分析并更新用户画像

    基于近期行为和对话数据，动态更新用户画像

    Args:
        user_id: 用户 ID
    """
    # 检查用户是否存在
    db_user = service.get_by_id(user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    result = dynamic_profile_service.analyze_and_update_profile(user_id)

    return {
        "user_id": user_id,
        "update_result": result
    }


@router.get("/profile/{user_id}")
async def get_enhanced_profile(
    user_id: str,
    service=Depends(get_user_service)
):
    """
    获取增强版用户画像（静态 + 动态）

    Args:
        user_id: 用户 ID
    """
    # 检查用户是否存在
    db_user = service.get_by_id(user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    profile = dynamic_profile_service.get_enhanced_user_profile(user_id)

    return profile


@router.get("/profile/evolution/{user_id}")
async def get_profile_evolution(
    user_id: str,
    days: int = 30
):
    """
    获取用户画像演化历史

    Args:
        user_id: 用户 ID
        days: 天数
    """
    evolution = dynamic_profile_service.get_profile_evolution(user_id, days=days)

    return evolution


@router.post("/profile/export/{user_id}")
async def export_user_data(
    user_id: str,
    service=Depends(get_user_service)
):
    """
    导出用户数据（隐私合规）

    Args:
        user_id: 用户 ID
    """
    # 检查用户是否存在
    db_user = service.get_by_id(user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    data = dynamic_profile_service.export_user_data(user_id)

    return data
