"""
P6 AI 陪伴助手 API

提供虚拟伙伴聊天、情感支持、聊天教练等功能。
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from db.database import get_db
from auth.jwt import get_current_user
from db.models import UserDB
from services.ai_companion_service import AICompanionService, COMPANION_PERSONAS, SESSION_TYPES


router = APIRouter(prefix="/api/companion", tags=["companion"])


@router.get("/personas")
async def get_companion_personas():
    """获取所有可用的虚拟角色"""
    personas = [
        {
            "key": key,
            "name": info["name"],
            "description": info["description"],
            "greeting": info["greeting"],
            "personality_traits": info["personality_traits"],
            "conversation_style": info["conversation_style"],
        }
        for key, info in COMPANION_PERSONAS.items()
    ]

    return {
        "success": True,
        "data": personas
    }


@router.get("/session-types")
async def get_session_types():
    """获取所有会话类型"""
    types = [
        {
            "key": key,
            "name": info["name"],
            "description": info["description"],
        }
        for key, info in SESSION_TYPES.items()
    ]

    return {
        "success": True,
        "data": types
    }


@router.post("/session/create")
async def create_session(
    session_type: str = Body(default="chat"),
    companion_persona: str = Body(default="gentle_advisor"),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """创建 AI 陪伴会话"""
    service = AICompanionService(db)

    try:
        session_data = service.create_session(
            user_id=current_user,
            session_type=session_type,
            companion_persona=companion_persona,
        )
        return {
            "success": True,
            "data": session_data
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/session/{session_id}/message")
async def send_message(
    session_id: str,
    content: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """发送消息并获取 AI 回复"""
    service = AICompanionService(db)

    try:
        response = service.send_message(
            session_id=session_id,
            user_id=current_user,
            content=content,
        )
        return {
            "success": True,
            "data": response
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/session/{session_id}/end")
async def end_session(
    session_id: str,
    rating: Optional[int] = Body(default=None),
    feedback: Optional[str] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """结束会话"""
    service = AICompanionService(db)

    try:
        result = service.end_session(
            session_id=session_id,
            user_id=current_user,
            rating=rating,
            feedback=feedback,
        )
        return {
            "success": True,
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/session/active")
async def get_active_session(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """获取当前活跃会话"""
    service = AICompanionService(db)
    session = service.get_active_session(current_user)

    return {
        "success": True,
        "data": session
    }


@router.get("/session/history")
async def get_session_history(
    limit: int = Body(default=20),
    offset: int = Body(default=0),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """获取会话历史"""
    service = AICompanionService(db)
    sessions = service.get_session_history(
        user_id=current_user,
        limit=limit,
        offset=offset,
    )

    return {
        "success": True,
        "data": sessions
    }


@router.get("/session/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """获取会话消息历史"""
    service = AICompanionService(db)

    try:
        messages = service.get_session_messages(
            session_id=session_id,
            user_id=current_user,
        )
        return {
            "success": True,
            "data": messages
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats")
async def get_companion_stats(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """获取用户使用统计"""
    service = AICompanionService(db)
    stats = service.get_user_stats(current_user)

    return {
        "success": True,
        "data": stats
    }


@router.post("/chat-coach/analyze")
async def analyze_conversation_for_coaching(
    conversation_text: str = Body(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    聊天教练：分析对话内容并给出建议

    用户可以提供自己与匹配对象的对话内容，AI 陪伴会分析并给出建议
    """
    service = AICompanionService(db)

    # 简单的分析逻辑（生产环境应使用 LLM 进行深度分析）
    analysis = {
        "summary": "对话分析结果",
        "suggestions": [
            "可以尝试多问一些开放式问题，引导对方分享更多",
            "注意回应对方的情绪，表达理解和共鸣",
            "适当分享自己的经历和感受，增进了解",
        ],
        "positive_points": [
            "主动开启话题，展现兴趣",
            "使用表情符号，营造轻松氛围",
        ],
        "improvement_areas": [
            "可以增加一些深度话题的探讨",
            "注意平衡说话和倾听的比例",
        ],
    }

    return {
        "success": True,
        "data": analysis
    }