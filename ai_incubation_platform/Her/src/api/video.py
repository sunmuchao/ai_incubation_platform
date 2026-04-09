"""
P6 视频通话 API

提供 WebRTC 视频通话的信令交换和通话管理功能。
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

from db.database import get_db
from auth.jwt import get_current_user
from db.models import UserDB
from services.video_call_service import VideoCallService


router = APIRouter(prefix="/api/video", tags=["video"])


# WebSocket 连接管理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(message)

    async def broadcast_to_room(self, message: dict, room_id: str,
                                 caller_id: str, receiver_id: str):
        """发送消息给通话双方"""
        await self.send_personal_message(message, caller_id)
        await self.send_personal_message(message, receiver_id)


manager = ConnectionManager()


@router.websocket("/ws/{user_id}")
async def video_websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket 视频信令连接"""
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_json()

            # 处理信令消息
            message_type = data.get("type")
            call_id = data.get("call_id")
            payload = data.get("payload", {})

            if message_type == "offer":
                # 发送 SDP Offer
                await handle_offer(user_id, call_id, payload, manager)
            elif message_type == "answer":
                # 发送 SDP Answer
                await handle_answer(user_id, call_id, payload, manager)
            elif message_type == "ice_candidate":
                # 交换 ICE Candidate
                await handle_ice_candidate(user_id, call_id, payload, manager)
            elif message_type == "end_call":
                # 结束通话
                await handle_end_signal(user_id, call_id, manager)

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


async def handle_offer(caller_id: str, call_id: str, payload: dict, manager: ConnectionManager):
    """处理 SDP Offer"""
    # 获取通话信息
    db = next(get_db())
    call_service = VideoCallService(db)

    call_info = call_service.get_call_info(call_id)
    if not call_info:
        return

    # 转发 Offer 给接收方
    await manager.broadcast_to_room(
        {"type": "offer", "caller_id": caller_id, "sdp": payload.get("sdp")},
        call_info["room_id"],
        call_info["caller_id"],
        call_info["receiver_id"]
    )


async def handle_answer(receiver_id: str, call_id: str, payload: dict, manager: ConnectionManager):
    """处理 SDP Answer"""
    db = next(get_db())
    call_service = VideoCallService(db)

    call_info = call_service.get_call_info(call_id)
    if not call_info:
        return

    # 转发 Answer 给呼叫方
    await manager.broadcast_to_room(
        {"type": "answer", "receiver_id": receiver_id, "sdp": payload.get("sdp")},
        call_info["room_id"],
        call_info["caller_id"],
        call_info["receiver_id"]
    )


async def handle_ice_candidate(user_id: str, call_id: str, payload: dict, manager: ConnectionManager):
    """处理 ICE Candidate"""
    db = next(get_db())
    call_service = VideoCallService(db)

    call_info = call_service.get_call_info(call_id)
    if not call_info:
        return

    # 转发 ICE Candidate 给对方
    await manager.broadcast_to_room(
        {"type": "ice_candidate", "from_user_id": user_id, "candidate": payload.get("candidate")},
        call_info["room_id"],
        call_info["caller_id"],
        call_info["receiver_id"]
    )


async def handle_end_signal(user_id: str, call_id: str, manager: ConnectionManager):
    """处理结束通话信号"""
    db = next(get_db())
    call_service = VideoCallService(db)

    call_info = call_service.get_call_info(call_id)
    if call_info:
        await manager.broadcast_to_room(
            {"type": "call_ended", "ended_by": user_id},
            call_info["room_id"],
            call_info["caller_id"],
            call_info["receiver_id"]
        )


@router.post("/call/create")
async def create_video_call(
    receiver_id: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """创建视频通话"""
    call_service = VideoCallService(db)

    try:
        call_data = call_service.create_call(current_user.id, receiver_id)
        return {
            "success": True,
            "data": call_data
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/call/{call_id}/accept")
async def accept_video_call(
    call_id: str,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """接受视频通话"""
    call_service = VideoCallService(db)

    try:
        call_data = call_service.accept_call(call_id, current_user.id)
        return {
            "success": True,
            "data": call_data
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/call/{call_id}/reject")
async def reject_video_call(
    call_id: str,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """拒绝视频通话"""
    call_service = VideoCallService(db)

    try:
        call_service.reject_call(call_id, current_user.id)
        return {
            "success": True,
            "message": "通话已拒绝"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/call/{call_id}/end")
async def end_video_call(
    call_id: str,
    duration_seconds: Optional[int] = Body(default=None),
    quality_score: Optional[float] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """结束视频通话"""
    call_service = VideoCallService(db)

    try:
        call_service.end_call(call_id, current_user.id, duration_seconds, quality_score)
        return {
            "success": True,
            "message": "通话已结束"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/call/{call_id}")
async def get_call_info(
    call_id: str,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取通话信息"""
    call_service = VideoCallService(db)
    call_info = call_service.get_call_info(call_id)

    if not call_info:
        raise HTTPException(status_code=404, detail="通话不存在")

    return {
        "success": True,
        "data": call_info
    }


@router.get("/call/history")
async def get_call_history(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取通话历史"""
    call_service = VideoCallService(db)
    history = call_service.get_user_call_history(current_user.id, limit, offset)

    return {
        "success": True,
        "data": history
    }


@router.get("/call/active")
async def get_active_calls(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取活跃的通话"""
    call_service = VideoCallService(db)
    active_calls = call_service.get_active_calls(current_user.id)

    return {
        "success": True,
        "data": active_calls
    }


@router.get("/call/stats")
async def get_call_stats(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取通话统计"""
    call_service = VideoCallService(db)
    stats = call_service.get_call_stats(current_user.id)

    return {
        "success": True,
        "data": stats
    }