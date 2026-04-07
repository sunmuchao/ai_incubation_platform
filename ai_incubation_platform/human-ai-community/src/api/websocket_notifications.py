"""
WebSocket 通知 API 路由
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from typing import Optional
import logging

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.websocket_notification_service import websocket_notification_service
from db.manager import db_manager
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ws", tags=["websocket"])


@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    user_id: str = Query(..., description="用户 ID"),
    token: Optional[str] = Query(None, description="认证 Token"),
):
    """
    WebSocket 通知推送连接

    连接后支持以下消息类型:
    - ping: 心跳检测，返回 pong
    - join_room: 加入房间 {"type": "join_room", "room_id": "xxx"}
    - leave_room: 离开房间 {"type": "leave_room", "room_id": "xxx"}
    - ack: 确认收到消息 {"type": "ack", "notification_id": "xxx"}

    接收的消息类型:
    - connected: 连接成功
    - notification: 新通知推送
    - queued_notifications: 离线消息批量推送
    - room_joined: 加入房间成功
    - room_left: 离开房间成功
    - pong: 心跳响应
    """
    # TODO: 验证 token
    # async with db_manager._session_factory() as session:
    #     user = await verify_user_token(session, token)
    #     if not user:
    #         await websocket.close(code=4001, reason="Invalid token")
    #         return

    await websocket_notification_service.handle_websocket_connection(
        websocket,
        user_id,
    )


@router.get("/notifications/online-users")
async def get_online_users():
    """获取在线用户列表"""
    users = websocket_notification_service.get_online_users()
    return {
        "online_users": users,
        "total": len(users),
    }


@router.get("/notifications/user/{user_id}/online")
async def check_user_online(user_id: str):
    """检查用户是否在线"""
    is_online = websocket_notification_service.is_user_online(user_id)
    return {
        "user_id": user_id,
        "is_online": is_online,
    }


@router.get("/notifications/user/{user_id}/connections")
async def get_user_connections(user_id: str):
    """获取用户连接数"""
    count = websocket_notification_service.get_user_connection_count(user_id)
    return {
        "user_id": user_id,
        "connection_count": count,
    }


@router.post("/notifications/user/{user_id}/join-room")
async def join_room(
    user_id: str,
    room_id: str = Query(..., description="房间 ID"),
):
    """加入房间（用于频道通知等）"""
    websocket_notification_service.join_room(user_id, room_id)
    return {
        "success": True,
        "user_id": user_id,
        "room_id": room_id,
    }


@router.post("/notifications/user/{user_id}/leave-room")
async def leave_room(
    user_id: str,
    room_id: str = Query(..., description="房间 ID"),
):
    """离开房间"""
    websocket_notification_service.leave_room(user_id, room_id)
    return {
        "success": True,
        "user_id": user_id,
        "room_id": room_id,
    }


@router.post("/notifications/channel/{channel_id}/broadcast")
async def broadcast_to_channel(
    channel_id: str,
    notification_type: str = Query(..., description="通知类型"),
    title: str = Query(..., description="通知标题"),
    content: str = Query(..., description="通知内容"),
    sender_id: Optional[str] = Query(None, description="发送者 ID"),
):
    """广播通知到频道所有在线成员"""
    notification = {
        "id": None,  # 由接收方生成
        "type": notification_type,
        "title": title,
        "content": content,
        "sender_id": sender_id,
        "channel_id": channel_id,
    }

    count = await websocket_notification_service.broadcast_to_channel(
        channel_id,
        notification,
    )

    return {
        "success": True,
        "channel_id": channel_id,
        "sent_count": count,
    }
