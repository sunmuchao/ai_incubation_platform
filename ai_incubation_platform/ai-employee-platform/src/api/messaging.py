"""
消息系统 API
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Header, Query, WebSocket
from pydantic import BaseModel, Field

from models.p4_models import MessageTypeEnum
from services.messaging_service import ConversationService, MessageService, NotificationService


router = APIRouter(prefix="/api", tags=["messaging"])


# ==================== Pydantic 模型 ====================

class ConversationCreate(BaseModel):
    """创建会话请求"""
    participant_ids: List[str] = Field(..., description="参与者 ID 列表", min_items=2)
    order_id: Optional[str] = Field(default=None, description="关联订单 ID")
    proposal_id: Optional[str] = Field(default=None, description="关联提案 ID")


class ConversationResponse(BaseModel):
    """会话响应"""
    id: str
    tenant_id: str
    order_id: Optional[str]
    proposal_id: Optional[str]
    participant_ids: List[str]
    last_message_at: Optional[datetime]
    last_message_preview: Optional[str]
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    """发送消息请求"""
    conversation_id: str = Field(..., description="会话 ID")
    content: str = Field(..., description="消息内容", min_length=1)
    message_type: MessageTypeEnum = Field(default=MessageTypeEnum.TEXT, description="消息类型")
    attachments: List[str] = Field(default_factory=list, description="附件列表")


class MessageResponse(BaseModel):
    """消息响应"""
    id: str
    tenant_id: str
    conversation_id: str
    sender_id: str
    message_type: str
    content: str
    attachments: List[str]
    is_read: bool
    read_at: Optional[datetime]
    edited_at: Optional[datetime]
    is_deleted: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MessageEdit(BaseModel):
    """编辑消息请求"""
    content: str = Field(..., description="新的消息内容", min_length=1)


class NotificationResponse(BaseModel):
    """通知响应"""
    id: str
    tenant_id: str
    user_id: str
    title: str
    content: str
    notification_type: str
    related_type: Optional[str]
    related_id: Optional[str]
    is_read: bool
    read_at: Optional[datetime]
    action_url: Optional[str]
    priority: str
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationCreate(BaseModel):
    """创建通知请求"""
    user_id: str = Field(..., description="用户 ID")
    title: str = Field(..., description="通知标题")
    content: str = Field(..., description="通知内容")
    notification_type: str = Field(..., description="通知类型")
    related_type: Optional[str] = Field(default=None, description="关联类型")
    related_id: Optional[str] = Field(default=None, description="关联 ID")
    action_url: Optional[str] = Field(default=None, description="操作链接")
    priority: str = Field(default="normal", description="优先级")


# ==================== 会话 API ====================

@router.post("/conversations", response_model=ConversationResponse, summary="创建会话")
async def create_conversation(
    request: ConversationCreate,
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """创建新会话"""
    # 确保当前用户是参与者之一
    if x_user_id not in request.participant_ids:
        request.participant_ids.append(x_user_id)

    conversation_service = ConversationService()

    conversation = conversation_service.create_conversation(
        tenant_id=x_tenant_id,
        participant_ids=request.participant_ids,
        order_id=request.order_id,
        proposal_id=request.proposal_id
    )

    if not conversation:
        raise HTTPException(status_code=400, detail="Failed to create conversation")

    return conversation


@router.get("/conversations", response_model=List[ConversationResponse], summary="获取会话列表")
async def list_conversations(
    is_archived: bool = Query(default=False, description="是否归档"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """获取会话列表"""
    conversation_service = ConversationService()

    conversations = conversation_service.list_conversations(
        tenant_id=x_tenant_id,
        participant_id=x_user_id,
        is_archived=is_archived,
        limit=limit,
        offset=offset
    )

    return conversations


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse, summary="获取会话详情")
async def get_conversation(
    conversation_id: str,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """获取会话详情"""
    conversation_service = ConversationService()

    conversation = conversation_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation


@router.post("/conversations/{conversation_id}/archive", summary="归档会话")
async def archive_conversation(
    conversation_id: str,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """归档会话"""
    conversation_service = ConversationService()

    success = conversation_service.archive_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to archive conversation")

    return {"message": "Conversation archived", "conversation_id": conversation_id}


# ==================== 消息 API ====================

@router.post("/messages", response_model=MessageResponse, summary="发送消息")
async def send_message(
    request: MessageCreate,
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """发送消息"""
    message_service = MessageService()

    message = message_service.send_message(
        tenant_id=x_tenant_id,
        conversation_id=request.conversation_id,
        sender_id=x_user_id,
        content=request.content,
        message_type=request.message_type,
        attachments=request.attachments
    )

    if not message:
        raise HTTPException(status_code=400, detail="Failed to send message")

    return message


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse], summary="获取消息列表")
async def list_messages(
    conversation_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """获取消息列表"""
    message_service = MessageService()

    messages = message_service.list_messages(
        conversation_id=conversation_id,
        limit=limit,
        offset=offset
    )

    return messages


@router.post("/messages/{message_id}/read", summary="标记消息已读")
async def mark_message_read(
    message_id: str,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """标记消息已读"""
    message_service = MessageService()

    success = message_service.mark_message_read(message_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to mark message as read")

    return {"message": "Message marked as read", "message_id": message_id}


@router.post("/conversations/{conversation_id}/read", summary="标记会话已读")
async def mark_conversation_read(
    conversation_id: str,
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """标记会话中所有消息已读"""
    message_service = MessageService()

    count = message_service.mark_conversation_read(conversation_id, x_user_id)
    return {"message": f"{count} messages marked as read", "conversation_id": conversation_id}


@router.put("/messages/{message_id}", summary="编辑消息")
async def edit_message(
    message_id: str,
    request: MessageEdit,
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """编辑消息"""
    message_service = MessageService()

    success = message_service.edit_message(
        message_id=message_id,
        new_content=request.content,
        sender_id=x_user_id
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to edit message")

    return {"message": "Message edited", "message_id": message_id}


@router.delete("/messages/{message_id}", summary="删除消息")
async def delete_message(
    message_id: str,
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """删除消息"""
    message_service = MessageService()

    success = message_service.delete_message(
        message_id=message_id,
        sender_id=x_user_id
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete message")

    return {"message": "Message deleted", "message_id": message_id}


# ==================== 通知 API ====================

@router.post("/notifications", response_model=NotificationResponse, summary="创建通知")
async def create_notification(
    request: NotificationCreate,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """创建通知"""
    notification_service = NotificationService()

    notification = notification_service.create_notification(
        tenant_id=x_tenant_id,
        user_id=request.user_id,
        title=request.title,
        content=request.content,
        notification_type=request.notification_type,
        related_type=request.related_type,
        related_id=request.related_id,
        action_url=request.action_url,
        priority=request.priority
    )

    if not notification:
        raise HTTPException(status_code=400, detail="Failed to create notification")

    return notification


@router.get("/notifications", response_model=List[NotificationResponse], summary="获取通知列表")
async def list_notifications(
    is_read: Optional[bool] = Query(default=None, description="是否已读"),
    notification_type: Optional[str] = Query(default=None, description="通知类型"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """获取通知列表"""
    notification_service = NotificationService()

    notifications = notification_service.list_notifications(
        tenant_id=x_tenant_id,
        user_id=x_user_id,
        is_read=is_read,
        notification_type=notification_type,
        limit=limit,
        offset=offset
    )

    return notifications


@router.get("/notifications/unread-count", summary="获取未读通知数量")
async def get_unread_count(
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """获取未读通知数量"""
    notification_service = NotificationService()

    count = notification_service.get_unread_count(user_id=x_user_id, tenant_id=x_tenant_id)
    return {"unread_count": count}


@router.post("/notifications/{notification_id}/read", summary="标记通知已读")
async def mark_notification_read(
    notification_id: str,
    x_tenant_id: str = Header(..., description="租户 ID")
):
    """标记通知已读"""
    notification_service = NotificationService()

    success = notification_service.mark_notification_read(notification_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to mark notification as read")

    return {"message": "Notification marked as read", "notification_id": notification_id}


@router.post("/notifications/read-all", summary="标记所有通知已读")
async def mark_all_notifications_read(
    x_tenant_id: str = Header(..., description="租户 ID"),
    x_user_id: str = Header(..., description="用户 ID")
):
    """标记所有通知已读"""
    notification_service = NotificationService()

    count = notification_service.mark_all_notifications_read(user_id=x_user_id, tenant_id=x_tenant_id)
    return {"message": f"{count} notifications marked as read"}
