"""
通知 API 路由 - 事件驱动主动通知

功能：
- GET /pending: 获取待推送通知
- POST /{id}/mark_read: 标记通知已读
- POST /preference: 创建通知偏好订阅
- DELETE /preference: 取消订阅

架构说明：
- 新用户注册时自动触发检查，写入通知队列
- Agent 对话开始时检查队列，主动推送
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from services.notification_service import (
    get_pending_notifications,
    mark_notification_read,
    mark_notification_delivered,
    create_notification_preference,
)
from utils.logger import logger

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# ========== Request/Response Models ==========

class NotificationResponse(BaseModel):
    """通知响应"""
    notifications: List[Dict[str, Any]]
    total: int
    has_unread: bool


class NotificationPreferenceRequest(BaseModel):
    """创建偏好订阅请求"""
    user_id: str
    trigger_type: str  # new_user_match, mutual_like, message_reply
    conditions: Dict[str, Any]  # {"location": "深圳", "gender": "female"}


class NotificationPreferenceResponse(BaseModel):
    """偏好订阅响应"""
    success: bool
    action: str  # created, updated
    id: Optional[int] = None


class MarkReadResponse(BaseModel):
    """标记已读响应"""
    success: bool


# ========== Routes ==========

@router.get("/pending", response_model=NotificationResponse)
async def get_pending(user_id: str):
    """
    获取待推送通知

    用户打开 App 或 Agent 对话开始时调用。

    Args:
        user_id: 用户 ID

    Returns:
        通知列表 + 未读标记
    """
    logger.info(f"[NOTIFICATION_API] 获取待推送通知: user_id={user_id}")

    result = get_pending_notifications(user_id)

    return NotificationResponse(
        notifications=result["notifications"],
        total=result["total"],
        has_unread=result["has_unread"],
    )


@router.post("/{notification_id}/mark_delivered", response_model=MarkReadResponse)
async def mark_delivered(notification_id: int):
    """
    标记通知已推送

    Agent 推送通知后调用。

    Args:
        notification_id: 通知 ID

    Returns:
        成功标记
    """
    logger.info(f"[NOTIFICATION_API] 标记已推送: notification_id={notification_id}")

    success = mark_notification_delivered(notification_id)

    return MarkReadResponse(success=success)


@router.post("/{notification_id}/mark_read", response_model=MarkReadResponse)
async def mark_read(notification_id: int):
    """
    标记通知已读

    用户点击通知后调用。

    Args:
        notification_id: 通知 ID

    Returns:
        成功标记
    """
    logger.info(f"[NOTIFICATION_API] 标记已读: notification_id={notification_id}")

    success = mark_notification_read(notification_id)

    return MarkReadResponse(success=success)


@router.post("/preference", response_model=NotificationPreferenceResponse)
async def create_preference(request: NotificationPreferenceRequest):
    """
    创建通知偏好订阅

    用户在对话中说"有深圳新人通知我"时，Agent 调用此接口。

    Args:
        request: 偏好订阅请求

    Returns:
        创建结果
    """
    logger.info(f"[NOTIFICATION_API] 创建偏好订阅: user_id={request.user_id}, "
                f"trigger_type={request.trigger_type}, conditions={request.conditions}")

    result = create_notification_preference(
        user_id=request.user_id,
        trigger_type=request.trigger_type,
        conditions=request.conditions,
    )

    return NotificationPreferenceResponse(
        success=result["success"],
        action=result["action"],
        id=result.get("id"),
    )


@router.delete("/preference")
async def cancel_preference(user_id: str, trigger_type: str):
    """
    取消通知偏好订阅

    用户说"取消新人通知"时调用。

    Args:
        user_id: 用户 ID
        trigger_type: 触发类型

    Returns:
        成功取消
    """
    from db.database import get_db_context
    from db.models import UserNotificationPreferenceDB

    logger.info(f"[NOTIFICATION_API] 取消偏好订阅: user_id={user_id}, trigger_type={trigger_type}")

    with get_db_context() as db:
        preference = db.query(UserNotificationPreferenceDB).filter(
            UserNotificationPreferenceDB.user_id == user_id,
            UserNotificationPreferenceDB.trigger_type == trigger_type,
        ).first()

        if preference:
            preference.is_active = False
            db.commit()
            return {"success": True, "action": "cancelled"}

        return {"success": False, "error": "订阅不存在"}