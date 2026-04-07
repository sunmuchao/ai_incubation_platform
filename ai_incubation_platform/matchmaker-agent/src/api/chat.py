"""
实时聊天 API

P4 新增:
- WebSocket 消息
- 聊天界面
- 消息历史记录
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime

from db.database import get_db
from auth.jwt import get_current_user
from db.models import UserDB
from services.chat_service import ChatService


router = APIRouter(prefix="/api/chat", tags=["实时聊天"])


# ============= Pydantic 模型 =============

class MessageSendRequest(BaseModel):
    """发送消息请求"""
    receiver_id: str = Field(..., description="接收者 ID")
    content: str = Field(..., description="消息内容")
    message_type: str = Field(default="text", description="消息类型：text/image/emoji/voice")
    message_metadata: Optional[dict] = Field(default=None, description="元数据")


class MessageResponse(BaseModel):
    """消息响应"""
    id: str
    conversation_id: str
    sender_id: str
    receiver_id: str
    message_type: str
    content: str
    status: str
    is_read: bool
    created_at: str
    metadata: Optional[dict] = None

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """会话响应"""
    id: str
    user_id_1: str
    user_id_2: str
    status: str
    last_message_at: Optional[str] = None
    last_message_preview: Optional[str] = None
    unread_count: int = 0
    created_at: str

    class Config:
        from_attributes = True


class MarkReadRequest(BaseModel):
    """标记已读请求"""
    user_id_1: str = Field(..., description="用户 ID 1")
    user_id_2: str = Field(..., description="用户 ID 2")


# ============= WebSocket 连接管理 =============

class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # user_id -> WebSocket 连接
        self.active_connections: dict[str, WebSocket] = {}
        # user_id -> set of 连接 (支持多设备)
        self.user_connections: dict[str, set] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """接受 WebSocket 连接"""
        await websocket.accept()
        self.active_connections[user_id] = websocket

        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        """断开 WebSocket 连接"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]

        if user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: str):
        """向特定用户发送消息"""
        if user_id in self.user_connections:
            for websocket in self.user_connections[user_id]:
                try:
                    await websocket.send_json(message)
                except:
                    # 连接已断开，忽略
                    pass

    async def broadcast(self, message: dict):
        """广播消息 (给所有在线用户)"""
        for websocket in self.active_connections.values():
            try:
                await websocket.send_json(message)
            except:
                pass


# 创建连接管理器实例
manager = ConnectionManager()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    token: Optional[str] = Query(default=None)
):
    """
    WebSocket 聊天连接

    客户端连接示例:
    ws://localhost:8001/api/chat/ws/{user_id}?token={jwt_token}
    """
    # TODO: 在这里验证 JWT token
    # 简化处理：直接接受连接
    await manager.connect(websocket, user_id)

    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_json()

            # 消息类型处理
            message_type = data.get("type", "message")

            if message_type == "message":
                # 聊天消息
                await handle_chat_message(websocket, data, user_id)
            elif message_type == "read_receipt":
                # 已读回执
                await handle_read_receipt(websocket, data, user_id)
            elif message_type == "typing":
                # 正在输入
                await handle_typing_indicator(websocket, data, user_id)

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
        # 通知对方用户已离线
        await manager.send_personal_message(
            {"type": "user_offline", "user_id": user_id},
            user_id
        )


async def handle_chat_message(websocket: WebSocket, data: dict, sender_id: str):
    """处理聊天消息"""
    receiver_id = data.get("receiver_id")
    content = data.get("content")
    message_type = data.get("message_type", "text")
    metadata = data.get("metadata")

    if not receiver_id or not content:
        await websocket.send_json({
            "type": "error",
            "message": "缺少必要参数"
        })
        return

    # 这里可以将消息存储到数据库
    # 实际应在完整的依赖注入环境中处理
    # 为简化，这里只做消息转发

    # 转发给接收者
    await manager.send_personal_message({
        "type": "new_message",
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "content": content,
        "message_type": message_type,
        "metadata": metadata,
        "timestamp": datetime.utcnow().isoformat()
    }, receiver_id)

    # 确认发送给发送者
    await websocket.send_json({
        "type": "message_sent",
        "receiver_id": receiver_id,
        "status": "sent"
    })


async def handle_read_receipt(websocket: WebSocket, data: dict, user_id: str):
    """处理已读回执"""
    sender_id = data.get("sender_id")
    message_id = data.get("message_id")

    if sender_id:
        await manager.send_personal_message({
            "type": "read_receipt",
            "message_id": message_id,
            "user_id": user_id
        }, sender_id)


async def handle_typing_indicator(websocket: WebSocket, data: dict, user_id: str):
    """处理正在输入指示"""
    target_user_id = data.get("target_user_id")

    if target_user_id:
        await manager.send_personal_message({
            "type": "typing",
            "user_id": user_id
        }, target_user_id)


# ============= REST API 端点 =============

@router.post("/send", response_model=MessageResponse, summary="发送消息")
async def send_message(
    request: MessageSendRequest,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    发送消息

    - **receiver_id**: 接收者 ID
    - **content**: 消息内容
    - **message_type**: 消息类型 (text/image/emoji/voice)
    - **metadata**: 元数据
    """
    service = ChatService(db)

    message = service.send_message(
        sender_id=current_user.id,
        receiver_id=request.receiver_id,
        content=request.content,
        message_type=request.message_type,
        message_metadata=request.message_metadata
    )

    # 如果接收者在线，通过 WebSocket 推送
    if request.receiver_id in manager.user_connections:
        await manager.send_personal_message({
            "type": "new_message",
            "id": message.id,
            "sender_id": current_user.id,
            "content": message.content,
            "message_type": message.message_type,
            "timestamp": message.created_at.isoformat()
        }, request.receiver_id)

    return message


@router.get("/conversations", response_model=List[ConversationResponse], summary="获取会话列表")
async def get_conversations(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取当前用户的聊天会话列表"""
    service = ChatService(db)
    conversations = service.get_user_conversations(current_user.id)

    # 转换为响应格式
    result = []
    for conv in conversations:
        # 计算当前用户的未读数
        if conv.user_id_1 == current_user.id:
            unread = conv.unread_count_user1
        else:
            unread = conv.unread_count_user2

        result.append({
            "id": conv.id,
            "user_id_1": conv.user_id_1,
            "user_id_2": conv.user_id_2,
            "status": conv.status,
            "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
            "last_message_preview": conv.last_message_preview,
            "unread_count": unread,
            "created_at": conv.created_at.isoformat()
        })

    return result


@router.get("/history/{other_user_id}", response_model=List[MessageResponse], summary="获取聊天历史")
async def get_chat_history(
    other_user_id: str,
    limit: int = Query(default=50, description="返回消息数量"),
    offset: int = Query(default=0, description="偏移量"),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取与指定用户的聊天历史记录"""
    service = ChatService(db)
    messages = service.get_conversation_messages(
        user_id_1=current_user.id,
        user_id_2=other_user_id,
        limit=limit,
        offset=offset
    )

    return [
        {
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "sender_id": msg.sender_id,
            "receiver_id": msg.receiver_id,
            "message_type": msg.message_type,
            "content": msg.content,
            "status": msg.status,
            "is_read": msg.is_read,
            "created_at": msg.created_at.isoformat(),
            "metadata": msg.metadata
        }
        for msg in messages
    ]


@router.post("/read/message/{message_id}", summary="标记消息已读")
async def mark_message_read(
    message_id: str,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """标记指定消息为已读"""
    service = ChatService(db)
    success = service.mark_message_read(message_id, current_user.id)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="标记失败")

    return {"message": "已标记为已读"}


@router.post("/read/conversation", summary="标记会话已读")
async def mark_conversation_read(
    request: MarkReadRequest,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
    ):
    """标记整个会话为已读"""
    service = ChatService(db)
    success = service.mark_conversation_read(request.user_id_1, request.user_id_2)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="标记失败")

    return {"message": "会话已标记为已读"}


@router.post("/recall/{message_id}", summary="撤回消息")
async def recall_message(
    message_id: str,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """撤回已发送的消息（2 分钟内）"""
    service = ChatService(db)
    success = service.recall_message(message_id, current_user.id)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="撤回失败")

    return {"message": "消息已撤回"}


@router.delete("/message/{message_id}", summary="删除消息")
async def delete_message(
    message_id: str,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """删除消息"""
    service = ChatService(db)
    success = service.delete_message(message_id, current_user.id)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="删除失败")

    return {"message": "消息已删除"}


@router.post("/archive/{other_user_id}", summary="归档会话")
async def archive_conversation(
    other_user_id: str,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """归档聊天会话"""
    service = ChatService(db)
    success = service.archive_conversation(current_user.id, other_user_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="归档失败")

    return {"message": "会话已归档"}


@router.post("/block/{other_user_id}", summary="屏蔽用户")
async def block_user(
    other_user_id: str,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """屏蔽指定用户"""
    service = ChatService(db)
    success = service.block_user(current_user.id, other_user_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="屏蔽失败")

    return {"message": "用户已屏蔽"}


@router.get("/unread/count", summary="获取未读消息数")
async def get_unread_count(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """获取当前用户的未读消息总数"""
    service = ChatService(db)
    count = service.get_unread_count(current_user.id)
    return {"unread_count": count}


@router.get("/search", summary="搜索消息")
async def search_messages(
    keyword: str = Query(..., description="搜索关键词"),
    limit: int = Query(default=20, description="返回数量"),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """搜索包含关键词的消息"""
    service = ChatService(db)
    messages = service.search_messages(current_user.id, keyword, limit)

    return [
        {
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "sender_id": msg.sender_id,
            "content": msg.content,
            "created_at": msg.created_at.isoformat()
        }
        for msg in messages
    ]
