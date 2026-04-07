"""
通知偏好设置 API 路由 - v1.22 用户体验优化

提供通知偏好设置功能的 API 端点
"""
from fastapi import APIRouter, HTTPException, Query, Body, Depends, Header
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from services.notification_preference_service import get_notification_preference_service

router = APIRouter(prefix="/api/ux/notifications", tags=["ux-notifications"])


# ==================== 依赖注入 ====================

async def get_db() -> AsyncSession:
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user_id(x_user_id: str = Header(..., description="用户 ID")) -> str:
    """获取当前用户 ID（从请求头）"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="未授权")
    return x_user_id


# ==================== 请求/响应模型 ====================

class NotificationPreferencesRequest(BaseModel):
    """通知偏好更新请求"""
    push_notifications: Optional[Dict[str, bool]] = Field(None, description="推送通知设置")
    email_notifications: Optional[Dict[str, bool]] = Field(None, description="邮件通知设置")
    sms_notifications: Optional[Dict[str, bool]] = Field(None, description="短信通知设置")
    do_not_disturb: Optional[Dict[str, Any]] = Field(None, description="免打扰设置")
    digest: Optional[Dict[str, Any]] = Field(None, description="通知摘要设置")


class NotificationPreferencesResponse(BaseModel):
    """通知偏好响应"""
    success: bool
    preferences: Dict[str, Any]
    message: str = ""


class NotificationHistoryResponse(BaseModel):
    """通知历史响应"""
    success: bool
    notifications: List[Dict[str, Any]]
    total: int
    unread_count: int


class MarkReadRequest(BaseModel):
    """标记已读请求"""
    notification_ids: List[str] = Field(..., description="通知 ID 列表")


class TestNotificationRequest(BaseModel):
    """测试通知请求"""
    notification_type: str = Field(..., description="通知类型：task/message/payment/system")
    channel: str = Field(..., description="通知渠道：push/email/sms")


# ==================== API 端点 ====================

@router.get("", response_model=NotificationPreferencesResponse)
async def get_user_preferences(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户通知偏好设置

    返回当前用户的通知偏好配置，包括推送/邮件/短信通知开关、免打扰时段、通知摘要等。
    如果用户尚未设置偏好，将返回默认配置。
    """
    service = get_notification_preference_service(db)

    preferences = await service.get_or_create_preferences(user_id)

    return {
        "success": True,
        "preferences": preferences.to_dict(),
        "message": "获取通知偏好设置成功"
    }


@router.put("", response_model=NotificationPreferencesResponse)
async def update_user_preferences(
    request: NotificationPreferencesRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    更新用户通知偏好设置

    允许用户自定义各类通知的接收方式和渠道。
    所有字段均为可选，仅更新提供的字段。
    """
    service = get_notification_preference_service(db)

    # 过滤空值
    update_data = {k: v for k, v in request.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="至少需要提供一个更新字段")

    try:
        preferences = await service.update_preferences(user_id, update_data)

        return {
            "success": True,
            "preferences": preferences.to_dict(),
            "message": "通知偏好设置更新成功"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history", response_model=NotificationHistoryResponse)
async def get_notification_history(
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    notification_type: Optional[str] = Query(None, description="通知类型过滤"),
    is_read: Optional[bool] = Query(None, description="已读状态过滤"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户通知历史

    返回当前用户的通知历史记录，支持分页和过滤。
    """
    service = get_notification_preference_service(db)

    notifications = await service.get_notification_history(
        user_id=user_id,
        limit=limit,
        offset=offset,
        notification_type=notification_type,
        is_read=is_read
    )

    unread_count = await service.get_unread_count(user_id)

    return {
        "success": True,
        "notifications": [n.to_dict() for n in notifications],
        "total": len(notifications),
        "unread_count": unread_count
    }


@router.get("/unread-count")
async def get_unread_count(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    获取未读通知数量

    快速返回当前用户的未读通知数量，用于角标展示。
    """
    service = get_notification_preference_service(db)

    count = await service.get_unread_count(user_id)

    return {
        "success": True,
        "unread_count": count
    }


@router.put("/read", response_model=Dict[str, Any])
async def mark_notifications_as_read(
    request: MarkReadRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    标记通知为已读

    批量标记指定的通知为已读。
    """
    service = get_notification_preference_service(db)

    count = await service.mark_notifications_as_read(user_id, request.notification_ids)

    return {
        "success": True,
        "marked_count": count,
        "message": f"已标记 {count} 条通知为已读"
    }


@router.put("/read-all", response_model=Dict[str, Any])
async def mark_all_as_read(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    标记所有通知为已读

    一键标记当前用户的所有通知为已读。
    """
    service = get_notification_preference_service(db)

    count = await service.mark_all_as_read(user_id)

    return {
        "success": True,
        "marked_count": count,
        "message": f"已标记 {count} 条通知为已读"
    }


@router.delete("/{notification_id}", response_model=Dict[str, Any])
async def delete_notification(
    notification_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    删除通知

    删除指定的通知记录。
    """
    service = get_notification_preference_service(db)

    success = await service.delete_notification(user_id, notification_id)

    if not success:
        raise HTTPException(status_code=404, detail="通知不存在")

    return {
        "success": True,
        "message": "通知已删除"
    }


@router.post("/test", response_model=Dict[str, Any])
async def send_test_notification(
    request: TestNotificationRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    发送测试通知

    向用户发送一条测试通知，用于验证通知配置是否正确。
    仅在开发/测试环境可用。
    """
    # 检查是否在免打扰时段
    service = get_notification_preference_service(db)

    should_send = await service.should_send_notification(
        user_id=user_id,
        notification_type=request.notification_type,
        channel=request.channel
    )

    return {
        "success": True,
        "should_send": should_send,
        "message": "测试通知配置检查完成",
        "config": {
            "notification_type": request.notification_type,
            "channel": request.channel,
            "will_deliver": should_send
        }
    }


@router.get("/check-delivery")
async def check_notification_delivery(
    notification_type: str = Query(..., description="通知类型"),
    channel: str = Query(..., description="通知渠道"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    检查通知是否会发送

    根据用户当前偏好设置，检查指定类型和渠道的通知是否会被发送。
    """
    service = get_notification_preference_service(db)

    should_send = await service.should_send_notification(
        user_id=user_id,
        notification_type=notification_type,
        channel=channel
    )

    in_dnd = await service.is_in_dnd_period(user_id)

    return {
        "success": True,
        "should_send": should_send,
        "in_dnd_period": in_dnd,
        "will_deliver": should_send and not in_dnd
    }
