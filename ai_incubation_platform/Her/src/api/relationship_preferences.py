"""
P6 关系类型标签 API

提供关系类型标签管理、兼容性检查等功能。
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from db.database import get_db
from auth.jwt import get_current_user
from db.models import UserDB
from services.relationship_preference_service import RelationshipPreferenceService


router = APIRouter(prefix="/api/relationship-preferences", tags=["relationship-preferences"])


@router.get("/types")
async def get_relationship_types(db: Session = Depends(get_db)):
    """获取所有可用的关系类型"""
    service = RelationshipPreferenceService(db)
    types = service.get_all_relationship_types()

    return {
        "success": True,
        "data": types
    }


@router.get("/statuses")
async def get_relationship_statuses(db: Session = Depends(get_db)):
    """获取所有可用的关系状态"""
    service = RelationshipPreferenceService(db)
    statuses = service.get_all_relationship_statuses()

    return {
        "success": True,
        "data": statuses
    }


@router.get("/preferences")
async def get_user_preferences(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取用户的关系偏好"""
    service = RelationshipPreferenceService(db)
    preferences = service.get_user_preferences(current_user.id)

    return {
        "success": True,
        "data": preferences
    }


@router.put("/preferences")
async def update_preferences(
    relationship_types: Optional[List[str]] = Body(default=None),
    current_status: Optional[str] = Body(default=None),
    expectation_description: Optional[str] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """更新用户的关系偏好"""
    service = RelationshipPreferenceService(db)

    try:
        preferences = service.update_preferences(
            user_id=current_user.id,
            relationship_types=relationship_types,
            current_status=current_status,
            expectation_description=expectation_description,
        )
        return {
            "success": True,
            "data": preferences,
            "message": "关系偏好已更新"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/compatibility/{target_user_id}")
async def check_relationship_compatibility(
    target_user_id: str,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """检查与目标用户的关系兼容性"""
    service = RelationshipPreferenceService(db)

    compatibility = service.match_relationship_compatibility(
        user_id=current_user.id,
        target_user_id=target_user_id,
    )

    return {
        "success": True,
        "data": compatibility
    }


@router.get("/stats")
async def get_compatibility_stats(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取关系兼容性统计"""
    service = RelationshipPreferenceService(db)
    stats = service.get_compatibility_stats(current_user.id)

    return {
        "success": True,
        "data": stats
    }


@router.post("/batch-check-compatibility")
async def batch_check_compatibility(
    target_user_ids: List[str] = Body(...),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """批量检查与多个用户的兼容性"""
    service = RelationshipPreferenceService(db)

    results = {}
    for target_id in target_user_ids:
        results[target_id] = service.match_relationship_compatibility(
            user_id=current_user.id,
            target_user_id=target_id,
        )

    return {
        "success": True,
        "data": results
    }