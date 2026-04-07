"""
消息系统服务
负责会话管理、消息发送和通知
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from models.p4_models import (
    ConversationDB, MessageDB, MessageTypeEnum, NotificationDB
)
from services.base_service import BaseService


class ConversationService(BaseService):
    """会话服务"""

    def create_conversation(
        self,
        tenant_id: str,
        participant_ids: List[str],
        order_id: Optional[str] = None,
        proposal_id: Optional[str] = None
    ) -> Optional[ConversationDB]:
        """创建会话"""
        try:
            # 检查是否已存在会话（相同参与者）
            existing = self.db.query(ConversationDB).filter(
                ConversationDB.tenant_id == tenant_id,
                ConversationDB.participant_ids.cast(str) == str(sorted(participant_ids))
            ).first()

            if existing:
                return existing

            conversation = ConversationDB(
                tenant_id=tenant_id,
                participant_ids=sorted(participant_ids),
                order_id=order_id,
                proposal_id=proposal_id
            )
            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)
            self.logger.info(f"Created conversation: {conversation.id}")
            return conversation
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to create conversation: {str(e)}")
            raise

    def get_conversation(self, conversation_id: str) -> Optional[ConversationDB]:
        """获取会话"""
        return self.db.query(ConversationDB).filter(ConversationDB.id == conversation_id).first()

    def list_conversations(
        self,
        tenant_id: str,
        participant_id: str,
        is_archived: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[ConversationDB]:
        """获取会话列表"""
        query = self.db.query(ConversationDB).filter(
            ConversationDB.tenant_id == tenant_id,
            ConversationDB.participant_ids.cast(str).like(f'%{participant_id}%'),
            ConversationDB.is_archived == is_archived
        )

        return query.order_by(ConversationDB.last_message_at.desc().nullsfirst()).offset(offset).limit(limit).all()

    def archive_conversation(self, conversation_id: str) -> bool:
        """归档会话"""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return False

        try:
            conversation.is_archived = True
            self.db.commit()
            self.logger.info(f"Archived conversation: {conversation_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to archive conversation: {str(e)}")
            raise


class MessageService(BaseService):
    """消息服务"""

    def send_message(
        self,
        tenant_id: str,
        conversation_id: str,
        sender_id: str,
        content: str,
        message_type: MessageTypeEnum = MessageTypeEnum.TEXT,
        attachments: Optional[List[str]] = None
    ) -> Optional[MessageDB]:
        """发送消息"""
        try:
            # 验证会话存在
            conversation = self.db.query(ConversationDB).filter(ConversationDB.id == conversation_id).first()
            if not conversation:
                self.logger.warning(f"Conversation not found: {conversation_id}")
                return None

            # 租户隔离校验
            if conversation.tenant_id != tenant_id:
                self.logger.warning(f"Cross-tenant message: conversation tenant={conversation.tenant_id}, message tenant={tenant_id}")
                return None

            message = MessageDB(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                sender_id=sender_id,
                message_type=message_type,
                content=content,
                attachments=attachments or []
            )
            self.db.add(message)

            # 更新会话最后消息
            conversation.last_message_at = datetime.now()
            conversation.last_message_preview = content[:100] if len(content) > 100 else content
            conversation.updated_at = datetime.now()

            self.db.commit()
            self.db.refresh(message)
            self.logger.info(f"Sent message: {message.id} in conversation: {conversation_id}")
            return message
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to send message: {str(e)}")
            raise

    def send_system_message(
        self,
        tenant_id: str,
        conversation_id: str,
        content: str,
        metadata_: Optional[dict] = None
    ) -> Optional[MessageDB]:
        """发送系统消息"""
        return self.send_message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            sender_id="system",
            content=content,
            message_type=MessageTypeEnum.SYSTEM,
            attachments=None
        )

    def mark_message_read(self, message_id: str) -> bool:
        """标记消息已读"""
        message = self.db.query(MessageDB).filter(MessageDB.id == message_id).first()
        if not message or message.is_read:
            return False

        try:
            message.is_read = True
            message.read_at = datetime.now()
            self.db.commit()
            self.logger.info(f"Marked message as read: {message_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to mark message as read: {str(e)}")
            raise

    def mark_conversation_read(self, conversation_id: str, user_id: str) -> int:
        """标记会话中所有消息已读"""
        try:
            unread_count = self.db.query(MessageDB).filter(
                MessageDB.conversation_id == conversation_id,
                MessageDB.sender_id != user_id,
                MessageDB.is_read == False
            ).update({"is_read": True, "read_at": datetime.now()})

            self.db.commit()
            self.logger.info(f"Marked {unread_count} messages as read in conversation: {conversation_id}")
            return unread_count
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to mark conversation as read: {str(e)}")
            raise

    def edit_message(self, message_id: str, new_content: str, sender_id: str) -> bool:
        """编辑消息"""
        message = self.db.query(MessageDB).filter(MessageDB.id == message_id).first()
        if not message or message.sender_id != sender_id or message.message_type != MessageTypeEnum.TEXT:
            return False

        try:
            message.content = new_content
            message.edited_at = datetime.now()
            self.db.commit()
            self.logger.info(f"Edited message: {message_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to edit message: {str(e)}")
            raise

    def delete_message(self, message_id: str, sender_id: str) -> bool:
        """删除消息"""
        message = self.db.query(MessageDB).filter(MessageDB.id == message_id).first()
        if not message or message.sender_id != sender_id:
            return False

        try:
            message.is_deleted = True
            self.db.commit()
            self.logger.info(f"Deleted message: {message_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to delete message: {str(e)}")
            raise

    def get_message(self, message_id: str) -> Optional[MessageDB]:
        """获取消息"""
        return self.db.query(MessageDB).filter(MessageDB.id == message_id).first()

    def list_messages(
        self,
        conversation_id: str,
        limit: int = 100,
        offset: int = 0,
        before: Optional[datetime] = None
    ) -> List[MessageDB]:
        """获取消息列表（按时间正序）"""
        query = self.db.query(MessageDB).filter(
            MessageDB.conversation_id == conversation_id,
            MessageDB.is_deleted == False
        )

        if before:
            query = query.filter(MessageDB.created_at < before)

        return query.order_by(MessageDB.created_at.asc()).offset(offset).limit(limit).all()

    def list_unread_messages(self, conversation_id: str, user_id: str) -> List[MessageDB]:
        """获取未读消息列表"""
        return self.db.query(MessageDB).filter(
            MessageDB.conversation_id == conversation_id,
            MessageDB.sender_id != user_id,
            MessageDB.is_read == False,
            MessageDB.is_deleted == False
        ).all()


class NotificationService(BaseService):
    """通知服务"""

    def create_notification(
        self,
        tenant_id: str,
        user_id: str,
        title: str,
        content: str,
        notification_type: str,
        related_type: Optional[str] = None,
        related_id: Optional[str] = None,
        action_url: Optional[str] = None,
        priority: str = "normal"
    ) -> Optional[NotificationDB]:
        """创建通知"""
        try:
            notification = NotificationDB(
                tenant_id=tenant_id,
                user_id=user_id,
                title=title,
                content=content,
                notification_type=notification_type,
                related_type=related_type,
                related_id=related_id,
                action_url=action_url,
                priority=priority
            )
            self.db.add(notification)
            self.db.commit()
            self.db.refresh(notification)
            self.logger.info(f"Created notification: {notification.id} for user: {user_id}")
            return notification
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to create notification: {str(e)}")
            raise

    def notify_order_proposal(
        self,
        tenant_id: str,
        user_id: str,
        order_id: str,
        proposal_id: str,
        action: str
    ) -> Optional[NotificationDB]:
        """发送订单/提案相关通知"""
        action_map = {
            "accepted": ("提案被接受", "您的提案已被接受，请开始工作"),
            "rejected": ("提案被拒绝", "很遗憾，您的提案未被接受"),
            "new_proposal": ("收到新提案", "有新的提案等待您查看"),
            "order_confirmed": ("订单已确认", "订单已确认，请开始工作"),
            "order_completed": ("订单已完成", "订单已完成，请确认并评价"),
        }

        title, content = action_map.get(action, (action, f"订单/提案状态更新：{action}"))

        return self.create_notification(
            tenant_id=tenant_id,
            user_id=user_id,
            title=title,
            content=content,
            notification_type="order_proposal",
            related_type="order" if "order" in action else "proposal",
            related_id=order_id if "order" in action else proposal_id,
            action_url=f"/orders/{order_id}" if "order" in action else f"/proposals/{proposal_id}",
            priority="high" if action in ["accepted", "order_confirmed"] else "normal"
        )

    def notify_message(
        self,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
        message_preview: str
    ) -> Optional[NotificationDB]:
        """发送新消息通知"""
        return self.create_notification(
            tenant_id=tenant_id,
            user_id=user_id,
            title="新消息",
            content=f"您收到一条新消息：{message_preview}",
            notification_type="message",
            related_type="conversation",
            related_id=conversation_id,
            action_url=f"/conversations/{conversation_id}",
            priority="normal"
        )

    def notify_escrow(
        self,
        tenant_id: str,
        user_id: str,
        escrow_id: str,
        action: str
    ) -> Optional[NotificationDB]:
        """发送托管相关通知"""
        action_map = {
            "created": ("托管已创建", "请在规定时间内完成充值"),
            "funded": ("托管已充值", "资金已到账，可以开始工作"),
            "released": ("托管已释放", "资金已释放到您的账户"),
            "disputed": ("托管争议", "该订单存在争议，等待处理"),
        }

        title, content = action_map.get(action, (action, f"托管状态更新：{action}"))

        return self.create_notification(
            tenant_id=tenant_id,
            user_id=user_id,
            title=title,
            content=content,
            notification_type="escrow",
            related_type="escrow",
            related_id=escrow_id,
            action_url=f"/escrows/{escrow_id}",
            priority="high"
        )

    def notify_dispute(
        self,
        tenant_id: str,
        user_id: str,
        dispute_id: str,
        action: str
    ) -> Optional[NotificationDB]:
        """发送争议相关通知"""
        action_map = {
            "opened": ("争议已开启", "您涉及的订单存在争议"),
            "resolved": ("争议已解决", "争议已处理完成"),
            "requires_action": ("需要您的操作", "争议处理需要您提供更多信息"),
        }

        title, content = action_map.get(action, (action, f"争议状态更新：{action}"))

        return self.create_notification(
            tenant_id=tenant_id,
            user_id=user_id,
            title=title,
            content=content,
            notification_type="dispute",
            related_type="dispute",
            related_id=dispute_id,
            action_url=f"/disputes/{dispute_id}",
            priority="urgent"
        )

    def mark_notification_read(self, notification_id: str) -> bool:
        """标记通知已读"""
        notification = self.db.query(NotificationDB).filter(NotificationDB.id == notification_id).first()
        if not notification or notification.is_read:
            return False

        try:
            notification.is_read = True
            notification.read_at = datetime.now()
            self.db.commit()
            self.logger.info(f"Marked notification as read: {notification_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to mark notification as read: {str(e)}")
            raise

    def mark_all_notifications_read(self, user_id: str, tenant_id: str) -> int:
        """标记所有通知已读"""
        try:
            read_count = self.db.query(NotificationDB).filter(
                NotificationDB.user_id == user_id,
                NotificationDB.tenant_id == tenant_id,
                NotificationDB.is_read == False
            ).update({"is_read": True, "read_at": datetime.now()})

            self.db.commit()
            self.logger.info(f"Marked {read_count} notifications as read for user: {user_id}")
            return read_count
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to mark all notifications as read: {str(e)}")
            raise

    def get_unread_count(self, user_id: str, tenant_id: str) -> int:
        """获取未读通知数量"""
        return self.db.query(NotificationDB).filter(
            NotificationDB.user_id == user_id,
            NotificationDB.tenant_id == tenant_id,
            NotificationDB.is_read == False
        ).count()

    def list_notifications(
        self,
        tenant_id: str,
        user_id: str,
        is_read: Optional[bool] = None,
        notification_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[NotificationDB]:
        """获取通知列表"""
        query = self.db.query(NotificationDB).filter(
            NotificationDB.tenant_id == tenant_id,
            NotificationDB.user_id == user_id
        )

        if is_read is not None:
            query = query.filter(NotificationDB.is_read == is_read)
        if notification_type:
            query = query.filter(NotificationDB.notification_type == notification_type)

        return query.order_by(NotificationDB.created_at.desc()).offset(offset).limit(limit).all()
