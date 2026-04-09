"""
关系进展 API 路由 - P3

提供关系进展追踪、可视化相关接口
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, Any, List

from db.database import get_db
from db.repositories import UserRepository
from services.relationship_progress_service import relationship_progress_service
from utils.logger import logger

router = APIRouter(prefix="/api/relationship", tags=["relationship"])


def get_user_service(db=Depends(get_db)):
    """获取用户服务依赖注入"""
    return UserRepository(db)


@router.post("/progress/record")
async def record_relationship_progress(
    user_id_1: str,
    user_id_2: str,
    progress_type: str,
    description: str,
    progress_score: int = 5,
    related_data: Optional[Dict[str, Any]] = None
):
    """
    记录关系进展里程碑

    Args:
        user_id_1: 用户 ID 1
        user_id_2: 用户 ID 2
        progress_type: 进展类型 (first_message, first_date, relationship_milestone, etc.)
        description: 进展描述
        progress_score: 进展评分 (1-10)
        related_data: 相关数据
    """
    progress_id = relationship_progress_service.record_progress(
        user_id_1=user_id_1,
        user_id_2=user_id_2,
        progress_type=progress_type,
        description=description,
        progress_score=progress_score,
        related_data=related_data
    )

    return {
        "progress_id": progress_id,
        "status": "recorded"
    }


@router.get("/timeline/{user_id_1}/{user_id_2}")
async def get_relationship_timeline(
    user_id_1: str,
    user_id_2: str
):
    """
    获取关系进展时间线

    Args:
        user_id_1: 用户 ID 1
        user_id_2: 用户 ID 2
    """
    timeline = relationship_progress_service.get_progress_timeline(user_id_1, user_id_2)

    return timeline


@router.get("/health-score/{user_id_1}/{user_id_2}")
async def get_relationship_health_score(
    user_id_1: str,
    user_id_2: str
):
    """
    获取关系健康度评分

    Args:
        user_id_1: 用户 ID 1
        user_id_2: 用户 ID 2
    """
    health_score = relationship_progress_service.get_relationship_health_score(user_id_1, user_id_2)

    return health_score


@router.get("/visualization/{user_id_1}/{user_id_2}")
async def get_relationship_visualization(
    user_id_1: str,
    user_id_2: str
):
    """
    获取关系可视化数据（用于前端图表）

    Args:
        user_id_1: 用户 ID 1
        user_id_2: 用户 ID 2
    """
    viz_data = relationship_progress_service.get_visualization_data(user_id_1, user_id_2)

    return viz_data
