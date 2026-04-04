"""
P5 通知推送 API

提供:
- 发送通知
- 通知模板管理
- 通知历史记录
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from config.database import get_db
from middleware.auth import get_current_user_id, get_current_tenant_id
from services.websocket_service import WebSocketService
from models.websocket_models import MessageType
from models.p4_models import NotificationDB

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


def get_websocket_service(db: Session) -> WebSocketService:
    """获取 WebSocket 服务实例"""
    from services.websocket_service import _manager
    return WebSocketService(db, _manager)


@router.post("/send", summary="发送通知", response_model=dict)
async def send_notification(
    recipient_id: str = Body(..., description="接收者 ID"),
    message_type: str = Body("text", description="消息类型"),
    title: str = Body(..., description="消息标题"),
    content: str = Body(..., description="消息内容"),
    data: Optional[dict] = Body(None, description="附加数据"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """发送通知消息"""
    websocket_service = get_websocket_service(db)

    # 验证接收者属于同一租户
    from models.db_models import UserDB
    recipient = db.query(UserDB).filter(
        UserDB.id == recipient_id,
        UserDB.tenant_id == tenant_id
    ).first()

    if not recipient:
        raise HTTPException(status_code=404, detail="接收者不存在或不属于同一租户")

    # 映射消息类型
    try:
        msg_type = MessageType(message_type)
    except ValueError:
        msg_type = MessageType.TEXT

    result = await websocket_service.send_message(
        recipient_id=recipient_id,
        message_type=msg_type,
        content=content,
        sender_id=user_id,
        title=title,
        data=data
    )

    # 同时创建通知记录
    notification = NotificationDB(
        id=str(hash(content) & 0xFFFFFFFF),
        user_id=recipient_id,
        tenant_id=tenant_id,
        notification_type=msg_type.value,
        title=title,
        content=content,
        is_read=False
    )
    db.add(notification)
    db.commit()

    return {
        "message": "通知发送成功",
        "delivery_status": result
    }


@router.post("/send-order-update", summary="发送订单更新通知", response_model=dict)
async def send_order_update_notification(
    recipient_id: str = Body(..., description="接收者 ID"),
    order_id: str = Body(..., description="订单 ID"),
    update_type: str = Body(..., description="更新类型"),
    content: str = Body(..., description="通知内容"),
    data: Optional[dict] = Body(None, description="附加数据"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """发送订单更新通知"""
    websocket_service = get_websocket_service(db)
    result = await websocket_service.send_order_update(
        recipient_id=recipient_id,
        order_id=order_id,
        update_type=update_type,
        content=content,
        data=data
    )
    return {"delivery_status": result}


@router.post("/send-dispute-update", summary="发送争议更新通知", response_model=dict)
async def send_dispute_update_notification(
    recipient_id: str = Body(..., description="接收者 ID"),
    dispute_id: str = Body(..., description="争议 ID"),
    update_type: str = Body(..., description="更新类型"),
    content: str = Body(..., description="通知内容"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """发送争议更新通知"""
    websocket_service = get_websocket_service(db)
    result = await websocket_service.send_dispute_update(
        recipient_id=recipient_id,
        dispute_id=dispute_id,
        update_type=update_type,
        content=content
    )
    return {"delivery_status": result}


@router.post("/send-proposal-update", summary="发送提案更新通知", response_model=dict)
async def send_proposal_update_notification(
    recipient_id: str = Body(..., description="接收者 ID"),
    proposal_id: str = Body(..., description="提案 ID"),
    update_type: str = Body(..., description="更新类型"),
    content: str = Body(..., description="通知内容"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """发送提案更新通知"""
    websocket_service = get_websocket_service(db)
    result = await websocket_service.send_proposal_update(
        recipient_id=recipient_id,
        proposal_id=proposal_id,
        update_type=update_type,
        content=content
    )
    return {"delivery_status": result}


@router.get("/history", summary="获取通知历史", response_model=dict)
async def get_notification_history(
    limit: int = Body(50, ge=1, le=100, description="返回数量限制"),
    offset: int = Body(0, ge=0, description="偏移量"),
    unread_only: bool = Body(False, description="是否仅返回未读"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """获取用户的通知历史记录"""
    query = db.query(NotificationDB).filter(
        NotificationDB.user_id == user_id,
        NotificationDB.tenant_id == tenant_id
    )

    if unread_only:
        query = query.filter(NotificationDB.is_read == False)

    notifications = query.order_by(
        NotificationDB.created_at.desc()
    ).offset(offset).limit(limit).all()

    return {
        "notifications": [n.to_dict() for n in notifications],
        "total": len(notifications),
        "limit": limit,
        "offset": offset
    }


@router.post("/{notification_id}/read", summary="标记通知已读", response_model=dict)
async def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """标记通知为已读"""
    notification = db.query(NotificationDB).filter(
        NotificationDB.id == notification_id,
        NotificationDB.user_id == user_id
    ).first()

    if not notification:
        raise HTTPException(status_code=404, detail="通知不存在")

    notification.is_read = True
    db.commit()

    return {"message": "通知已标记为已读"}


@router.post("/read-all", summary="标记所有通知已读", response_model=dict)
async def mark_all_notifications_read(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """标记所有通知为已读"""
    count = db.query(NotificationDB).filter(
        NotificationDB.user_id == user_id,
        NotificationDB.is_read == False
    ).update({"is_read": True})

    db.commit()

    return {"message": f"已标记 {count} 条通知为已读"}


@router.get("/unread-count", summary="获取未读通知数", response_model=dict)
async def get_unread_count(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """获取未读通知数量"""
    count = db.query(NotificationDB).filter(
        NotificationDB.user_id == user_id,
        NotificationDB.is_read == False
    ).count()

    return {"unread_count": count}
