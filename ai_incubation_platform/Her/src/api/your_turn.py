"""
Your Turn 提醒 API

参考 Hinge 的 Your Turn 机制：
- 显示待回复的对话列表
- 标记提醒已显示
- 用户主动忽略提醒
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from db.database import get_db
from services.your_turn_service import YourTurnReminderService, get_your_turn_service
from utils.logger import logger

router = APIRouter(prefix="/api/your-turn", tags=["Your Turn"])


class PendingReminderResponse(BaseModel):
    """待处理提醒响应"""
    conversation_id: str
    partner_id: str
    partner_name: Optional[str] = None
    last_message_content: str
    last_message_time: str
    hours_waiting: int
    is_your_turn: bool


class ReminderStatsResponse(BaseModel):
    """提醒统计响应"""
    pending_count: int
    total_waiting_hours: int
    oldest_waiting_hours: int


class DismissReminderRequest(BaseModel):
    """忽略提醒请求"""
    conversation_id: str


@router.get("/pending/{user_id}", response_model=List[PendingReminderResponse])
async def get_pending_reminders(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    获取用户待处理的 Your Turn 提醒

    返回需要回复的对话列表
    """
    try:
        service = get_your_turn_service(db)
        reminders = service.get_pending_reminders(user_id)

        # 补充 partner_name（从 matches_cache 或用户表查询）
        from db.models import UserDB
        for reminder in reminders:
            partner = db.query(UserDB).filter(UserDB.id == reminder["partner_id"]).first()
            if partner:
                reminder["partner_name"] = partner.name

        logger.info(f"User {user_id} has {len(reminders)} pending Your Turn reminders")
        return reminders
    except Exception as e:
        logger.error(f"Failed to get pending reminders for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/{user_id}", response_model=ReminderStatsResponse)
async def get_reminder_stats(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    获取用户提醒统计
    """
    try:
        service = get_your_turn_service(db)
        stats = service.get_reminder_stats(user_id)
        return stats
    except Exception as e:
        logger.error(f"Failed to get reminder stats for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/shown")
async def mark_reminder_shown(
    user_id: str,
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """
    标记提醒已显示

    记录提醒显示历史，避免重复提醒
    """
    try:
        service = get_your_turn_service(db)
        success = service.mark_reminder_shown(user_id, conversation_id)

        if success:
            logger.info(f"Marked reminder shown for user {user_id}, conversation {conversation_id}")
            return {"success": True, "message": "Reminder marked as shown"}
        else:
            return {"success": False, "message": "Failed to mark reminder"}
    except Exception as e:
        logger.error(f"Failed to mark reminder shown: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dismiss")
async def dismiss_reminder(
    request: DismissReminderRequest,
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    用户主动忽略提醒

    用户选择不回复，标记提醒为已忽略
    """
    try:
        service = get_your_turn_service(db)
        success = service.dismiss_reminder(user_id, request.conversation_id)

        if success:
            logger.info(f"User {user_id} dismissed reminder for conversation {request.conversation_id}")
            return {"success": True, "message": "Reminder dismissed"}
        else:
            return {"success": False, "message": "Reminder not found"}
    except Exception as e:
        logger.error(f"Failed to dismiss reminder: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/should-show/{user_id}/{conversation_id}")
async def should_show_reminder(
    user_id: str,
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """
    判断是否应该显示 Your Turn 提醒

    用于在聊天界面判断是否显示提醒标识
    """
    try:
        service = get_your_turn_service(db)
        should_show, reminder = service.should_show_reminder(user_id, conversation_id)

        return {
            "should_show": should_show,
            "reminder": reminder if should_show else None
        }
    except Exception as e:
        logger.error(f"Failed to check should show reminder: {e}")
        raise HTTPException(status_code=500, detail=str(e))