"""
对话分析 API 路由 - P3

提供对话历史、话题分析相关接口
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, Any, List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import get_db
from db.repositories import UserRepository
from services.conversation_analysis_service import conversation_analyzer
from utils.logger import logger

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def get_user_service(db=Depends(get_db)):
    """获取用户服务依赖注入"""
    return UserRepository(db)


@router.post("/analyze")
async def analyze_message(
    message: str,
    sender_id: str,
    receiver_id: str
):
    """
    分析单条消息

    Args:
        message: 消息内容
        sender_id: 发送者 ID
        receiver_id: 接收者 ID
    """
    result = conversation_analyzer.analyze_message(
        message=message,
        sender_id=sender_id,
        receiver_id=receiver_id
    )

    return {
        "analysis": result
    }


@router.post("/save")
async def save_conversation(
    sender_id: str,
    receiver_id: str,
    message: str,
    message_type: str = "text"
):
    """
    保存对话记录（带分析）

    Args:
        sender_id: 发送者 ID
        receiver_id: 接收者 ID
        message: 消息内容
        message_type: 消息类型
    """
    conversation_id = conversation_analyzer.save_conversation(
        sender_id=sender_id,
        receiver_id=receiver_id,
        message=message,
        message_type=message_type
    )

    return {
        "conversation_id": conversation_id,
        "status": "saved"
    }


@router.get("/history/{user_id_1}/{user_id_2}")
async def get_conversation_history(
    user_id_1: str,
    user_id_2: str,
    limit: int = 50
):
    """
    获取两人之间的对话历史

    Args:
        user_id_1: 用户 ID 1
        user_id_2: 用户 ID 2
        limit: 返回数量
    """
    history = conversation_analyzer.get_conversation_history(
        user_id_1=user_id_1,
        user_id_2=user_id_2,
        limit=limit
    )

    return {
        "conversations": history,
        "total": len(history)
    }


@router.get("/topic-profile/{user_id}")
async def get_topic_profile(
    user_id: str,
    days: int = 30
):
    """
    获取用户的话题画像

    Args:
        user_id: 用户 ID
        days: 分析天数
    """
    profile = conversation_analyzer.get_user_topic_profile(user_id, days=days)

    return {
        "user_id": user_id,
        "period_days": days,
        "topic_profile": profile
    }


@router.get("/suggestions/{user_id}")
async def get_profile_update_suggestions(
    user_id: str,
    days: int = 30
):
    """
    获取画像更新建议（基于对话分析）

    Args:
        user_id: 用户 ID
        days: 分析天数
    """
    suggestions = conversation_analyzer.generate_profile_update_suggestions(
        user_id=user_id,
        days=days
    )

    return {
        "user_id": user_id,
        "suggestions": suggestions
    }
