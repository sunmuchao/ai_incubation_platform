"""
实时聊天服务

P4 新增:
- WebSocket 消息管理
- 聊天消息发送/接收
- 消息历史记录
- 消息状态管理 (已读/未读)
"""
import json
import uuid
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload

from db.models import ChatMessageDB, ChatConversationDB, UserDB
from utils.logger import logger, get_trace_id
from services.base_service import BaseService


class ChatService(BaseService):
    """实时聊天服务"""

    # 消息类型
    TYPE_TEXT = "text"
    TYPE_IMAGE = "image"
    TYPE_EMOJI = "emoji"
    TYPE_VOICE = "voice"
    TYPE_SYSTEM = "system"

    # 消息状态
    STATUS_SENT = "sent"
    STATUS_DELIVERED = "delivered"
    STATUS_READ = "read"
    STATUS_RECALLED = "recalled"

    def __init__(self, db: Session):
        super().__init__(db)

    def get_or_create_conversation(self, user_id_1: str, user_id_2: str) -> ChatConversationDB:
        """
        获取或创建聊天会话

        Args:
            user_id_1: 用户 ID 1
            user_id_2: 用户 ID 2

        Returns:
            ChatConversationDB: 聊天会话
        """
        trace_id = get_trace_id()
        logger.debug(f"💬 [CHAT_SERVICE:CONV] GET_OR_CREATE trace_id={trace_id} users={user_id_1},{user_id_2}")

        # 查找现有会话 (不考虑用户顺序)
        conversation = self.db.query(ChatConversationDB).filter(
            or_(
                and_(
                    ChatConversationDB.user_id_1 == user_id_1,
                    ChatConversationDB.user_id_2 == user_id_2
                ),
                and_(
                    ChatConversationDB.user_id_1 == user_id_2,
                    ChatConversationDB.user_id_2 == user_id_1
                )
            )
        ).first()

        if conversation:
            logger.debug(f"💬 [CHAT_SERVICE:CONV] Found existing conversation id={conversation.id}")
            return conversation

        # 创建新会话
        conversation = ChatConversationDB(
            id=str(uuid.uuid4()),
            user_id_1=user_id_1,
            user_id_2=user_id_2,
            status="active"
        )

        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)

        logger.info(f"💬 [CHAT_SERVICE:CONV] Created new conversation id={conversation.id}")

        return conversation

    def send_message(
        self,
        sender_id: str,
        receiver_id: str,
        content: str,
        message_type: str = TYPE_TEXT,
        message_metadata: Optional[Dict[str, Any]] = None
    ) -> ChatMessageDB:
        """
        发送消息

        Args:
            sender_id: 发送者 ID
            receiver_id: 接收者 ID
            content: 消息内容
            message_type: 消息类型
            message_metadata: 元数据

        Returns:
            ChatMessageDB: 消息记录
        """
        trace_id = get_trace_id()
        start_time = time.time()
        logger.info(f"💬 [CHAT_SERVICE:SEND] START trace_id={trace_id} sender={sender_id} receiver={receiver_id} type={message_type}")

        try:
            # 获取或创建会话
            conversation = self.get_or_create_conversation(sender_id, receiver_id)
            logger.debug(f"💬 [CHAT_SERVICE:SEND] Conversation id={conversation.id}")

            # 创建消息
            message = ChatMessageDB(
                id=str(uuid.uuid4()),
                conversation_id=conversation.id,
                sender_id=sender_id,
                receiver_id=receiver_id,
                message_type=message_type,
                content=content,
                status=self.STATUS_SENT,
                is_read=False,
                message_metadata=message_metadata
            )

            self.db.add(message)

            # 更新会话
            conversation.last_message_at = datetime.utcnow()
            conversation.last_message_preview = self._generate_preview(content, message_type)

            # 更新未读计数
            if conversation.user_id_2 == receiver_id:
                conversation.unread_count_user2 += 1
            else:
                conversation.unread_count_user1 += 1

            self.db.commit()
            self.db.refresh(message)

            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(f"💬 [CHAT_SERVICE:SEND] SUCCESS trace_id={trace_id} message_id={message.id} elapsed={elapsed_ms:.2f}ms")

            return message

        except Exception as e:
            self.db.rollback()
            logger.error(f"💬 [CHAT_SERVICE:SEND] FAILED trace_id={trace_id} error={str(e)}", exc_info=True)
            raise

    def _generate_preview(self, content: str, message_type: str) -> str:
        """生成消息预览"""
        if message_type == self.TYPE_IMAGE:
            return "[图片]"
        elif message_type == self.TYPE_EMOJI:
            return "[表情]"
        elif message_type == self.TYPE_VOICE:
            return "[语音]"
        elif message_type == self.TYPE_SYSTEM:
            return "[系统消息]"
        else:
            # 文本消息截取前 50 字
            return content[:50] if len(content) > 50 else content

    def get_conversation_messages(
        self,
        user_id_1: str,
        user_id_2: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[ChatMessageDB]:
        """
        获取聊天消息历史

        Args:
            user_id_1: 用户 ID 1
            user_id_2: 用户 ID 2
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            List[ChatMessageDB]: 消息列表
        """
        conversation = self.get_or_create_conversation(user_id_1, user_id_2)

        messages = self.db.query(ChatMessageDB).filter(
            ChatMessageDB.conversation_id == conversation.id
        ).order_by(
            ChatMessageDB.created_at.desc()
        ).offset(offset).limit(limit).all()

        # 反转顺序 (从旧到新)
        return list(reversed(messages))

    def get_user_conversations(self, user_id: str) -> List[ChatConversationDB]:
        """
        获取用户的聊天会话列表

        Args:
            user_id: 用户 ID

        Returns:
            List[ChatConversationDB]: 会话列表
        """
        conversations = self.db.query(ChatConversationDB).filter(
            or_(
                ChatConversationDB.user_id_1 == user_id,
                ChatConversationDB.user_id_2 == user_id
            ),
            ChatConversationDB.status == "active"
        ).order_by(
            ChatConversationDB.last_message_at.desc()
        ).all()

        return conversations

    def mark_message_read(self, message_id: str, user_id: str) -> bool:
        """
        标记消息为已读

        Args:
            message_id: 消息 ID
            user_id: 用户 ID (接收者)

        Returns:
            bool: 是否成功
        """
        message = self.db.query(ChatMessageDB).filter(
            and_(
                ChatMessageDB.id == message_id,
                ChatMessageDB.receiver_id == user_id
            )
        ).first()

        if not message:
            return False

        message.is_read = True
        message.read_at = datetime.utcnow()
        message.status = self.STATUS_READ

        # 更新会话未读计数
        conversation = self.db.query(ChatConversationDB).filter(
            ChatConversationDB.id == message.conversation_id
        ).first()

        if conversation:
            if conversation.user_id_2 == user_id:
                conversation.unread_count_user2 = max(0, conversation.unread_count_user2 - 1)
            else:
                conversation.unread_count_user1 = max(0, conversation.unread_count_user1 - 1)

        self.db.commit()
        return True

    def mark_conversation_read(self, user_id_1: str, user_id_2: str) -> bool:
        """
        标记整个会话为已读

        Args:
            user_id_1: 用户 ID 1
            user_id_2: 用户 ID 2

        Returns:
            bool: 是否成功
        """
        conversation = self.get_or_create_conversation(user_id_1, user_id_2)

        if conversation.user_id_2 == user_id_2:
            conversation.unread_count_user2 = 0
        else:
            conversation.unread_count_user1 = 0

        # 标记所有未读消息为已读
        unread_messages = self.db.query(ChatMessageDB).filter(
            and_(
                ChatMessageDB.conversation_id == conversation.id,
                ChatMessageDB.receiver_id == user_id_2,
                ChatMessageDB.is_read == False
            )
        ).all()

        for message in unread_messages:
            message.is_read = True
            message.read_at = datetime.utcnow()
            message.status = self.STATUS_READ

        self.db.commit()
        return True

    def recall_message(self, message_id: str, user_id: str) -> bool:
        """
        撤回消息

        Args:
            message_id: 消息 ID
            user_id: 用户 ID (发送者)

        Returns:
            bool: 是否成功
        """
        message = self.db.query(ChatMessageDB).filter(
            and_(
                ChatMessageDB.id == message_id,
                ChatMessageDB.sender_id == user_id
            )
        ).first()

        if not message:
            return False

        # 只能撤回 2 分钟内的消息
        if (datetime.utcnow() - message.created_at).total_seconds() > 120:
            return False

        message.status = self.STATUS_RECALLED
        message.content = "消息已撤回"
        self.db.commit()

        return True

    def delete_message(self, message_id: str, user_id: str) -> bool:
        """
        删除消息

        Args:
            message_id: 消息 ID
            user_id: 用户 ID

        Returns:
            bool: 是否成功
        """
        message = self.db.query(ChatMessageDB).filter(
            ChatMessageDB.id == message_id
        ).first()

        if not message:
            return False

        # 只有发送者或接收者可以删除
        if message.sender_id != user_id and message.receiver_id != user_id:
            return False

        self.db.delete(message)
        self.db.commit()

        return True

    def archive_conversation(self, user_id: str, other_user_id: str) -> bool:
        """
        归档聊天会话

        Args:
            user_id: 用户 ID
            other_user_id: 对方用户 ID

        Returns:
            bool: 是否成功
        """
        conversation = self.get_or_create_conversation(user_id, other_user_id)
        conversation.status = "archived"
        self.db.commit()
        return True

    def block_user(self, user_id: str, blocked_user_id: str) -> bool:
        """
        屏蔽用户

        Args:
            user_id: 用户 ID
            blocked_user_id: 被屏蔽的用户 ID

        Returns:
            bool: 是否成功
        """
        conversation = self.get_or_create_conversation(user_id, blocked_user_id)
        conversation.status = "blocked"
        self.db.commit()
        return True

    def get_unread_count(self, user_id: str) -> int:
        """获取用户的未读消息总数"""
        conversations = self.db.query(ChatConversationDB).filter(
            or_(
                ChatConversationDB.user_id_1 == user_id,
                ChatConversationDB.user_id_2 == user_id
            )
        ).all()

        total = 0
        for conv in conversations:
            if conv.user_id_1 == user_id:
                total += conv.unread_count_user1
            else:
                total += conv.unread_count_user2

        return total

    def get_message(self, message_id: str) -> Optional[ChatMessageDB]:
        """获取消息详情"""
        return self.db.query(ChatMessageDB).filter(
            ChatMessageDB.id == message_id
        ).first()

    def search_messages(
        self,
        user_id: str,
        keyword: str,
        limit: int = 20
    ) -> List[ChatMessageDB]:
        """
        搜索消息

        Args:
            user_id: 用户 ID
            keyword: 搜索关键词
            limit: 返回数量限制

        Returns:
            List[ChatMessageDB]: 消息列表
        """
        conversations = self.get_user_conversations(user_id)
        conversation_ids = [c.id for c in conversations]

        messages = self.db.query(ChatMessageDB).filter(
            and_(
                ChatMessageDB.conversation_id.in_(conversation_ids),
                ChatMessageDB.content.like(f"%{keyword}%"),
                ChatMessageDB.message_type == self.TYPE_TEXT
            )
        ).order_by(
            ChatMessageDB.created_at.desc()
        ).limit(limit).all()

        return messages
