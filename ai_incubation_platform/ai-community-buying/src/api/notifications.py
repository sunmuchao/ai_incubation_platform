"""
通知服务 API 路由

提供通知相关的 HTTP 接口。
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from config.database import get_db
from services.notification_facade import get_notification_facade

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", summary="获取用户通知列表")
async def get_notifications(
    user_id: str = Query(..., description="用户 ID"),
    unread_only: bool = Query(False, description="是否只获取未读"),
    limit: int = Query(20, description="数量限制"),
    db: Session = Depends(get_db)
):
    """获取用户通知列表"""
    facade = get_notification_facade(db)
    notifications = facade.get_user_notifications(user_id, unread_only, limit)
    return {
        "success": True,
        "user_id": user_id,
        "total": len(notifications),
        "notifications": notifications
    }


@router.post("/mark-read", summary="标记通知为已读")
async def mark_as_read(
    user_id: str = Query(..., description="用户 ID"),
    message_id: str = Query(..., description="消息 ID"),
    db: Session = Depends(get_db)
):
    """标记通知为已读"""
    facade = get_notification_facade(db)
    success = facade.mark_notification_as_read(user_id, message_id)
    if not success:
        raise HTTPException(status_code=404, detail="通知不存在")
    return {"success": True, "message": "已标记为已读"}


@router.post("/mark-all-read", summary="标记所有通知为已读")
async def mark_all_as_read(
    user_id: str = Query(..., description="用户 ID"),
    db: Session = Depends(get_db)
):
    """标记所有通知为已读"""
    facade = get_notification_facade(db)
    count = facade.mark_all_as_read(user_id)
    return {
        "success": True,
        "marked_count": count,
        "user_id": user_id
    }


@router.get("/adapter-info", summary="获取通知适配器信息")
async def get_adapter_info(db: Session = Depends(get_db)):
    """获取通知适配器配置信息"""
    from adapters.notification.registry import get_registry
    registry = get_registry()
    return {
        "success": True,
        "adapter_info": registry.get_adapter_info()
    }
