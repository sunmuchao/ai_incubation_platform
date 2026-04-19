"""
场景检测 API 路由

从 services/scene_detection_service.py 迁移而来，符合分层架构规范。
"""

from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from typing import Dict, Any

from db.database import get_db
from auth.jwt import get_current_user
from services.scene_detection_service import get_scene_service, SceneDetectionService

router = APIRouter(prefix="/api/scene", tags=["场景检测"])


@router.post("/detect")
async def detect_scene_endpoint(
    trigger: str = Body(..., embed=True),
    context: Dict[str, Any] = Body(default={}, embed=True),
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    检测场景并返回推送建议

    前端调用示例：
    - 用户注册完成时：trigger='user_registered', context={}
    - 匹配成功时：trigger='match_created', context={'match_count': 1, 'compatibility_score': 85}
    - 聊天时长变化：trigger='chat_duration', context={'days': 7}
    """
    user_id = current_user
    service = get_scene_service()

    results = service.detect_scene(user_id, trigger, context)

    return {
        "success": True,
        "user_id": user_id,
        "trigger": trigger,
        "push_actions": results or []
    }


@router.get("/history/{user_id}")
async def get_scene_history(
    user_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户场景历史"""
    service = get_scene_service()
    history = service.get_user_scene_history(user_id)

    return {
        "success": True,
        "user_id": user_id,
        "history": [
            {
                "scene_type": h.scene_type,
                "trigger_data": h.trigger_data,
                "timestamp": h.timestamp.isoformat() if h.timestamp else None
            }
            for h in history[-20:]  # 最近 20 条
        ]
    }


@router.get("/rules")
async def get_scene_rules():
    """获取所有场景规则（用于调试）"""
    return {
        "success": True,
        "rules": [
            {
                "name": name,
                "description": rule.get('description', ''),
                "trigger": rule.get('trigger'),
            }
            for name, rule in SceneDetectionService.SCENE_RULES.items()
        ]
    }