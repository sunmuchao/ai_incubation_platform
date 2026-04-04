"""
通知服务 API 路由
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List
from sqlalchemy.orm import Session
from config.database import get_db
from services.notification_service import notification_service
from models.entities import NotificationEntity

router = APIRouter(prefix="/api/notifications", tags=["notification"])


@router.get("/{user_id}", summary="获取用户通知列表")
async def get_user_notifications(
    user_id: str,
    unread_only: bool = Query(False, description="仅获取未读通知"),
    limit: int = Query(20, description="返回数量"),
    db: Session = Depends(get_db)
):
    """获取用户的通知列表"""
    notifications = notification_service.get_user_notifications(db, user_id, unread_only, limit)
    return {
        "user_id": user_id,
        "unread_count": sum(1 for n in notifications if not n.is_read),
        "total": len(notifications),
        "notifications": [
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "content": n.content,
                "related_id": n.related_id,
                "is_read": n.is_read,
                "created_at": n.created_at,
                "read_at": n.read_at
            }
            for n in notifications
        ]
    }


@router.patch("/{notification_id}/read", summary="标记通知为已读")
async def mark_notification_as_read(
    notification_id: str,
    user_id: str = Query(..., description="用户ID"),
    db: Session = Depends(get_db)
):
    """标记单个通知为已读"""
    notification = notification_service.mark_notification_as_read(db, notification_id, user_id)
    if not notification:
        raise HTTPException(status_code=404, detail="通知不存在")

    return {
        "message": "通知已标记为已读",
        "notification_id": notification_id
    }


@router.patch("/read-all/{user_id}", summary="标记所有通知为已读")
async def mark_all_notifications_as_read(
    user_id: str,
    db: Session = Depends(get_db)
):
    """标记用户的所有通知为已读"""
    count = notification_service.mark_all_as_read(db, user_id)
    return {
        "message": f"已标记 {count} 条通知为已读",
        "marked_count": count
    }


@router.post("/stock-alerts/check", summary="检查并发送库存预警")
async def check_stock_alerts(
    db: Session = Depends(get_db)
):
    """检查所有商品库存并发送预警通知（管理接口）"""
    alert_count = notification_service.check_and_send_stock_alerts(db)
    return {
        "message": f"已发送 {alert_count} 条库存预警通知",
        "alert_count": alert_count
    }
