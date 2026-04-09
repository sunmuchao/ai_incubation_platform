"""
AI 感知 API - Omniscient AI Awareness Endpoints

提供 AI 红娘全知感知能力的 API 端点：
1. GET /api/ai/awareness - 获取 AI 全知感知数据
2. GET /api/ai/awareness/insights - 获取主动洞察
3. GET /api/ai/awareness/patterns - 获取行为模式分析
4. POST /api/ai/awareness/track - 手动追踪行为事件
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Any

from db.database import get_db
from db.models import UserDB
from utils.logger import logger
from services.ai_awareness_service import get_ai_awareness_service, AIAwarenessService
from services.behavior_event_emitter import event_emitter, EVENT_PROFILE_VIEWED

router = APIRouter(prefix="/api/ai/awareness", tags=["ai-awareness"])


@router.get("")
async def get_omniscient_awareness(
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db)
):
    """
    获取 AI 全知感知数据

    返回 AI 对用户的全面感知，包括：
    - 当前状态（情绪、活跃、社交、匹配）
    - 行为模式（聊天时间、回复速度、滑动偏好）
    - 主动洞察（AI 主动提供的建议）
    - 潜在机会（AI 识别的机会）
    - AI 旁白（自然语言的总结）

    这是 AI 红娘作为"底层操作系统"的核心接口
    """
    # 验证用户存在
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        awareness_service = get_ai_awareness_service(db)
        awareness = await awareness_service.get_omniscient_awareness(user_id)

        logger.info(f"Omniscient awareness generated for user {user_id}")
        return {
            "success": True,
            "data": awareness
        }
    except Exception as e:
        logger.error(f"Error getting omniscient awareness: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights")
async def get_active_insights(
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db)
):
    """
    获取 AI 主动洞察

    返回 AI 基于用户行为主动生成的洞察和建议
    """
    # 验证用户存在
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        awareness_service = get_ai_awareness_service(db)
        awareness = await awareness_service.get_omniscient_awareness(user_id)
        insights = awareness.get("active_insights", [])

        return {
            "success": True,
            "data": {
                "insights": insights,
                "count": len(insights)
            }
        }
    except Exception as e:
        logger.error(f"Error getting active insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestion")
async def get_proactive_suggestion(
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db)
):
    """
    获取 AI 主动建议

    返回当前最相关的一条 AI 建议
    """
    # 验证用户存在
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        awareness_service = get_ai_awareness_service(db)
        suggestion = await awareness_service.get_proactive_suggestion(user_id)

        return {
            "success": True,
            "data": suggestion
        }
    except Exception as e:
        logger.error(f"Error getting proactive suggestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns")
async def get_behavior_patterns(
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db)
):
    """
    获取用户行为模式分析
    """
    # 验证用户存在
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        awareness_service = get_ai_awareness_service(db)
        awareness = await awareness_service.get_omniscient_awareness(user_id)
        patterns = awareness.get("behavior_patterns", [])

        return {
            "success": True,
            "data": {
                "patterns": patterns,
                "count": len(patterns)
            }
        }
    except Exception as e:
        logger.error(f"Error getting behavior patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/commentary")
async def get_ai_commentary(
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db)
):
    """
    获取 AI 旁白

    AI 以自然语言生成的用户状态总结和观察
    """
    # 验证用户存在
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        awareness_service = get_ai_awareness_service(db)
        awareness = await awareness_service.get_omniscient_awareness(user_id)
        commentary = awareness.get("ai_commentary", "")

        return {
            "success": True,
            "data": {
                "commentary": commentary
            }
        }
    except Exception as e:
        logger.error(f"Error getting AI commentary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/track")
async def track_behavior_event(
    user_id: str = Query(..., description="用户 ID"),
    event_type: str = Query(..., description="事件类型"),
    target_id: Optional[str] = Query(None, description="目标用户 ID"),
    event_data: Optional[dict] = None,
    db: Session = Depends(get_db)
):
    """
    手动追踪行为事件

    用于前端主动上报行为
    """
    # 验证用户存在
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        event_id = event_emitter.emit(
            user_id=user_id,
            event_type=event_type,
            target_id=target_id,
            event_data=event_data
        )

        logger.info(f"Tracked behavior event: {event_type} for user {user_id}")
        return {
            "success": True,
            "data": {
                "event_id": event_id
            }
        }
    except Exception as e:
        logger.error(f"Error tracking behavior event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= 快捷追踪端点 =============

@router.post("/track/profile-view")
async def track_profile_view(
    user_id: str = Query(..., description="查看者用户 ID"),
    profile_id: str = Query(..., description="被查看的用户 ID"),
    db: Session = Depends(get_db)
):
    """追踪查看资料行为"""
    event_emitter.emit(
        user_id=user_id,
        event_type="profile_viewed",
        target_id=profile_id,
        event_data={"source": "api"}
    )
    return {"success": True}


@router.post("/track/swipe")
async def track_swipe(
    user_id: str = Query(..., description="用户 ID"),
    target_id: str = Query(..., description="目标用户 ID"),
    action: str = Query(..., description="动作：like, pass, super_like"),
    db: Session = Depends(get_db)
):
    """追踪滑动行为"""
    event_emitter.emit(
        user_id=user_id,
        event_type=f"swipe_{action}",
        target_id=target_id,
        event_data={"action": action}
    )
    return {"success": True}


@router.post("/track/chat-message")
async def track_chat_message(
    sender_id: str = Query(..., description="发送者用户 ID"),
    receiver_id: str = Query(..., description="接收者用户 ID"),
    content_length: int = Query(0, description="消息内容长度"),
    db: Session = Depends(get_db)
):
    """追踪聊天消息行为"""
    event_emitter.emit(
        user_id=sender_id,
        event_type="chat_message_sent",
        target_id=receiver_id,
        event_data={"content_length": content_length}
    )
    return {"success": True}
