"""
P5 WebSocket 实时消息 API

提供:
- WebSocket 连接端点
- 在线状态管理
- 离线消息查询
"""

from typing import Optional
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query, HTTPException
from sqlalchemy.orm import Session
import uuid

from config.database import get_db
from middleware.auth import get_current_user_id, get_current_tenant_id
from services.websocket_service import WebSocketService, ConnectionManager
from models.websocket_models import ConnectionStatus, MessageType

router = APIRouter(prefix="/api/ws", tags=["WebSocket"])


def get_websocket_service(db: Session) -> WebSocketService:
    """获取 WebSocket 服务实例"""
    from services.websocket_service import _manager
    return WebSocketService(db, _manager)


@router.websocket("/connect")
async def websocket_connect(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="认证 token"),
    db: Session = Depends(get_db),
    # 注意：WebSocket 不支持 Depends(get_current_user_id)，需要在连接内验证
):
    """
    WebSocket 连接端点

    连接后会自动接收:
    - 实时消息推送
    - 通知更新
    - 在线状态更新
    """
    # 生成连接 ID
    connection_id = str(uuid.uuid4())

    # TODO: 在这里实现 token 验证获取 user_id 和 tenant_id
    # 当前暂时接受连接，实际使用需要验证
    await websocket.accept()

    # 发送欢迎消息
    await websocket.send_json({
        "type": "connection_established",
        "connection_id": connection_id,
        "message": "WebSocket 连接成功"
    })

    # 保持连接
    try:
        while True:
            # 接收心跳或其他消息
            data = await websocket.receive_json()

            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.get("type") == "update_status":
                # 更新状态
                status = data.get("status")
                if status in ["online", "away", "busy", "do_not_disturb"]:
                    await websocket.send_json({
                        "type": "status_updated",
                        "status": status
                    })

    except WebSocketDisconnect:
        # 连接断开
        pass


@router.get("/presence/me", summary="获取我的在线状态", response_model=dict)
async def get_my_presence(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """获取当前用户的在线状态"""
    websocket_service = get_websocket_service(db)
    presence = websocket_service.get_user_presence(user_id)

    if presence:
        return {"presence": presence.to_dict()}
    else:
        return {"presence": None}


@router.post("/presence/set", summary="设置在线状态", response_model=dict)
async def set_presence(
    status: ConnectionStatus,
    custom_status: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """设置当前用户的在线状态"""
    websocket_service = get_websocket_service(db)
    presence = websocket_service.set_user_status(
        user_id=user_id,
        tenant_id=tenant_id,
        status=status,
        custom_status=custom_status
    )
    return {"presence": presence.to_dict()}


@router.get("/presence/users", summary="获取在线用户列表", response_model=dict)
async def get_online_users(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """获取租户内所有在线用户"""
    websocket_service = get_websocket_service(db)
    users = websocket_service.get_tenant_online_users(tenant_id)
    return {
        "online_users": [u.to_dict() for u in users],
        "total": len(users)
    }


@router.get("/messages/offline", summary="获取离线消息", response_model=dict)
async def get_offline_messages(
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """获取用户的离线消息"""
    websocket_service = get_websocket_service(db)
    messages = websocket_service.get_offline_messages(user_id, limit)
    return {
        "messages": [m.to_dict() for m in messages],
        "total": len(messages)
    }


@router.post("/messages/{message_id}/read", summary="标记消息已读", response_model=dict)
async def mark_message_read(
    message_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """标记消息为已读"""
    websocket_service = get_websocket_service(db)
    websocket_service.mark_message_read(message_id)
    return {"message": "消息已标记为已读", "message_id": message_id}


@router.post("/messages/read-all", summary="标记所有消息已读", response_model=dict)
async def mark_all_messages_read(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """标记所有消息为已读"""
    websocket_service = get_websocket_service(db)
    count = websocket_service.mark_all_messages_read(user_id)
    return {"message": f"已标记 {count} 条消息为已读"}


@router.get("/connections", summary="获取我的连接", response_model=dict)
async def get_my_connections(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """获取当前用户的所有 WebSocket 连接"""
    websocket_service = get_websocket_service(db)

    # 从连接管理器获取活跃连接数
    connection_count = websocket_service.connection_manager.get_user_connection_count(user_id)
    is_online = websocket_service.connection_manager.is_user_online(user_id)

    return {
        "active_connections": connection_count,
        "is_online": is_online
    }
