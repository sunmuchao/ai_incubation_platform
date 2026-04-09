"""
P6 行为学习推荐 API

基于用户行为数据的个性化推荐系统。
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from db.database import get_db
from auth.jwt import get_current_user
from db.models import UserDB
from services.behavior_learning_service import BehaviorLearningService


router = APIRouter(prefix="/api/recommendation", tags=["recommendation"])


@router.post("/interaction/record")
async def record_interaction(
    target_user_id: str = Body(...),
    interaction_type: str = Body(...),  # viewed, liked, passed, messaged, replied, blocked
    dwell_time_seconds: int = Body(default=0),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """记录用户交互行为"""
    service = BehaviorLearningService(db)

    try:
        interaction = service.record_interaction(
            user_id=current_user.id,
            target_user_id=target_user_id,
            interaction_type=interaction_type,
            dwell_time_seconds=dwell_time_seconds,
        )
        return {
            "success": True,
            "data": {
                "interaction_id": interaction.id,
                "positive_signal": interaction.positive_signal,
                "signal_strength": interaction.signal_strength,
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/personalized")
async def get_personalized_recommendations(
    limit: int = Body(default=20),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取个性化推荐"""
    service = BehaviorLearningService(db)
    recommendations = service.get_recommendations(
        user_id=current_user.id,
        limit=limit,
    )

    return {
        "success": True,
        "data": recommendations
    }


@router.get("/similar-users")
async def get_similar_users(
    limit: int = Body(default=20),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取相似用户（基于行为特征）"""
    service = BehaviorLearningService(db)
    similar = service.get_similar_users(
        user_id=current_user.id,
        limit=limit,
    )

    return {
        "success": True,
        "data": similar
    }


@router.get("/features")
async def get_user_features(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取用户行为特征"""
    service = BehaviorLearningService(db)
    features = service.get_user_features(current_user.id)

    return {
        "success": True,
        "data": features
    }


@router.get("/stats")
async def get_learning_stats(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取学习统计"""
    service = BehaviorLearningService(db)
    stats = service.get_learning_stats(current_user.id)

    return {
        "success": True,
        "data": stats
    }


@router.post("/features/retrain")
async def retrain_user_features(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """手动触发用户特征更新"""
    service = BehaviorLearningService(db)

    try:
        feature_record = service._update_user_features(current_user.id)
        return {
            "success": True,
            "data": {
                "user_id": current_user.id,
                "features_updated": True,
                "updated_at": feature_record.updated_at.isoformat(),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-retrain")
async def batch_retrain_all_features(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """批量重新训练所有用户特征（管理员）"""
    from utils.admin_check import require_admin
    require_admin(current_user)  # 管理员权限检查

    service = BehaviorLearningService(db)

    updated_count = service.retrain_all_features()

    return {
        "success": True,
        "data": {
            "updated_count": updated_count,
        },
        "message": f"已更新 {updated_count} 个用户的特征"
    }