"""
通知 API 路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel, Field

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.member import MemberType
from services.notification_service import (
    notification_service,
    NotificationType,
    NotificationPriority,
    NotificationEvent,
    NotificationStatus,
    NotificationMessage
)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationPreferenceUpdate(BaseModel):
    """更新通知偏好请求"""
    event: str = Field(..., description="事件类型")
    adapter_types: List[str] = Field(..., description="通知方式列表")


class BulkNotificationRequest(BaseModel):
    """批量通知请求"""
    event: str
    title: str
    content: str
    recipient_ids: List[str]
    priority: str = "normal"
    metadata: Optional[dict] = None


@router.get("/user/{user_id}")
async def get_user_notifications(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    status: Optional[str] = Query(default=None)
):
    """获取用户通知列表"""
    parsed_status = None
    if status:
        try:
            parsed_status = NotificationStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    adapter = notification_service.get_adapter(NotificationType.IN_APP)
    if not adapter:
        raise HTTPException(status_code=500, detail="In-app notification adapter not available")

    notifications = adapter.get_user_notifications(user_id, limit=limit, status=parsed_status)
    return {
        "user_id": user_id,
        "total": len(notifications),
        "notifications": [n.to_dict() for n in notifications]
    }


@router.get("/user/{user_id}/unread-count")
async def get_user_unread_count(user_id: str):
    """获取用户未读消息数量"""
    adapter = notification_service.get_adapter(NotificationType.IN_APP)
    if not adapter:
        raise HTTPException(status_code=500, detail="In-app notification adapter not available")

    count = adapter.get_unread_count(user_id)
    return {"user_id": user_id, "unread_count": count}


@router.post("/user/{user_id}/mark-as-read/{notification_id}")
async def mark_notification_as_read(user_id: str, notification_id: str):
    """标记通知为已读"""
    adapter = notification_service.get_adapter(NotificationType.IN_APP)
    if not adapter:
        raise HTTPException(status_code=500, detail="In-app notification adapter not available")

    success = adapter.mark_as_read(notification_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"success": True, "notification_id": notification_id}


@router.post("/user/{user_id}/mark-all-as-read")
async def mark_all_as_read(user_id: str):
    """标记所有通知为已读"""
    adapter = notification_service.get_adapter(NotificationType.IN_APP)
    if not adapter:
        raise HTTPException(status_code=500, detail="In-app notification adapter not available")

    count = adapter.mark_all_as_read(user_id)
    return {"success": True, "marked_count": count}


@router.get("/preferences/{user_id}")
async def get_user_preferences(user_id: str):
    """获取用户通知偏好"""
    # 返回所有事件类型的偏好
    events = [e.value for e in NotificationEvent]
    preferences = {}
    for event_value in events:
        try:
            event = NotificationEvent(event_value)
            adapter_types = notification_service.get_user_preference(user_id, event)
            preferences[event_value] = [a.value for a in adapter_types]
        except ValueError:
            continue

    return {"user_id": user_id, "preferences": preferences}


@router.put("/preferences/{user_id}")
async def update_user_preference(user_id: str, preference: NotificationPreferenceUpdate):
    """更新用户通知偏好"""
    try:
        event = NotificationEvent(preference.event)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid event type: {preference.event}")

    adapter_types = []
    for type_value in preference.adapter_types:
        try:
            adapter_types.append(NotificationType(type_value))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid adapter type: {type_value}")

    notification_service.set_user_preference(user_id, event, adapter_types)
    return {
        "success": True,
        "user_id": user_id,
        "event": event.value,
        "adapter_types": [a.value for a in adapter_types]
    }


@router.get("/events")
async def list_notification_events():
    """列出所有通知事件类型"""
    return {
        "events": [
            {"value": e.value, "name": e.name}
            for e in NotificationEvent
        ]
    }


@router.get("/adapters")
async def list_notification_adapters():
    """列出已注册的通知适配器"""
    return {
        "adapters": [
            {"type": t.value, "available": True}
            for t, adapter in notification_service._adapters.items()
        ]
    }


@router.post("/send")
async def send_notification(
    event: str,
    title: str,
    content: str,
    recipient_id: str,
    priority: str = "normal",
    adapter_types: Optional[List[str]] = None,
    metadata: Optional[dict] = None
):
    """发送单条通知"""
    try:
        event_type = NotificationEvent(event)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid event type: {event}")

    try:
        priority_type = NotificationPriority(priority)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid priority: {priority}")

    message = NotificationMessage(
        event_type=event_type,
        title=title,
        content=content,
        recipient_id=recipient_id,
        priority=priority_type,
        metadata=metadata
    )

    force_adapter_types = None
    if adapter_types:
        force_adapter_types = []
        for type_value in adapter_types:
            try:
                force_adapter_types.append(NotificationType(type_value))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid adapter type: {type_value}")

    results = notification_service.send_notification(message, force_adapter_types)
    return {
        "success": True,
        "message_id": message.id,
        "results": results
    }


@router.post("/bulk")
async def send_bulk_notifications(request: BulkNotificationRequest):
    """批量发送通知"""
    try:
        event_type = NotificationEvent(request.event)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid event type: {request.event}")

    try:
        priority_type = NotificationPriority(request.priority)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid priority: {request.priority}")

    messages = []
    for recipient_id in request.recipient_ids:
        message = NotificationMessage(
            event_type=event_type,
            title=request.title,
            content=request.content,
            recipient_id=recipient_id,
            priority=priority_type,
            metadata=request.metadata
        )
        messages.append(message)

    results = notification_service.send_bulk_notifications(messages)
    return {
        "success": True,
        "total": len(results),
        "results": results
    }


@router.post("/event-subscriptions")
async def subscribe_event(
    event: str,
    adapter_types: List[str]
):
    """订阅事件通知（全局配置）"""
    try:
        event_type = NotificationEvent(event)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid event type: {event}")

    types = []
    for type_value in adapter_types:
        try:
            types.append(NotificationType(type_value))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid adapter type: {type_value}")

    notification_service.subscribe_event(event_type, types)
    return {
        "success": True,
        "event": event_type.value,
        "adapter_types": [t.value for t in types]
    }
