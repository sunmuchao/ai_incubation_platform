"""
数据库通知适配器 - 持久化通知到数据库

将通知存储到 PostgreSQL 数据库，支持完整的通知管理功能。
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid

from sqlalchemy.orm import Session

from adapters.notification.base import (
    NotificationAdapter,
    NotificationConfig,
    NotificationMessage,
    NotificationResult
)


class DatabaseNotificationAdapter(NotificationAdapter):
    """数据库通知适配器"""

    def __init__(self, db_session: Session, config: Optional[NotificationConfig] = None):
        super().__init__(config)
        self.db = db_session

    def send(self, message: NotificationMessage) -> NotificationResult:
        """发送单条通知到数据库"""
        if not self.enabled:
            return NotificationResult(
                success=False,
                error="适配器未启用"
            )

        try:
            from models.entities import NotificationEntity

            message_id = str(uuid.uuid4())
            notification = NotificationEntity(
                id=message_id,
                user_id=message.user_id,
                type=message.type,
                title=message.title,
                content=message.content,
                related_id=message.related_id,
                is_read=False,
                created_at=datetime.now(),
                read_at=None
            )

            self.db.add(notification)
            self.db.commit()
            self.db.refresh(notification)

            self.logger.info(f"通知已保存：{message_id} -> {message.user_id}")

            return NotificationResult(
                success=True,
                message_id=message_id
            )

        except Exception as e:
            self.db.rollback()
            self.logger.error(f"通知保存失败：{str(e)}")
            return NotificationResult(
                success=False,
                error=str(e)
            )

    def send_batch(self, messages: List[NotificationMessage]) -> List[NotificationResult]:
        """批量发送通知"""
        results = []
        try:
            from models.entities import NotificationEntity

            for message in messages:
                message_id = str(uuid.uuid4())
                notification = NotificationEntity(
                    id=message_id,
                    user_id=message.user_id,
                    type=message.type,
                    title=message.title,
                    content=message.content,
                    related_id=message.related_id,
                    is_read=False,
                    created_at=datetime.now(),
                    read_at=None
                )
                self.db.add(notification)

                results.append(NotificationResult(
                    success=True,
                    message_id=message_id
                ))

            self.db.commit()
            self.logger.info(f"批量发送通知成功：{len(messages)} 条")

        except Exception as e:
            self.db.rollback()
            self.logger.error(f"批量发送通知失败：{str(e)}")
            # 对于失败的批量发送，返回失败结果
            results = [NotificationResult(success=False, error=str(e)) for _ in messages]

        return results

    def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取用户通知列表"""
        try:
            from models.entities import NotificationEntity

            query = self.db.query(NotificationEntity).filter(
                NotificationEntity.user_id == user_id
            )

            if unread_only:
                query = query.filter(NotificationEntity.is_read == False)

            notifications = query.order_by(
                NotificationEntity.created_at.desc()
            ).limit(limit).all()

            return [
                {
                    "id": n.id,
                    "user_id": n.user_id,
                    "type": n.type,
                    "title": n.title,
                    "content": n.content,
                    "related_id": n.related_id,
                    "is_read": n.is_read,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                    "read_at": n.read_at.isoformat() if n.read_at else None
                }
                for n in notifications
            ]

        except Exception as e:
            self.logger.error(f"获取通知列表失败：{str(e)}")
            return []

    def mark_as_read(self, user_id: str, message_id: str) -> bool:
        """标记通知为已读"""
        try:
            from models.entities import NotificationEntity

            notification = self.db.query(NotificationEntity).filter(
                NotificationEntity.id == message_id,
                NotificationEntity.user_id == user_id
            ).first()

            if not notification:
                return False

            notification.is_read = True
            notification.read_at = datetime.now()
            self.db.commit()

            return True

        except Exception as e:
            self.db.rollback()
            self.logger.error(f"标记已读失败：{str(e)}")
            return False

    def mark_all_as_read(self, user_id: str) -> int:
        """标记所有通知为已读"""
        try:
            from models.entities import NotificationEntity

            result = self.db.query(NotificationEntity).filter(
                NotificationEntity.user_id == user_id,
                NotificationEntity.is_read == False
            ).update({
                "is_read": True,
                "read_at": datetime.now()
            })

            self.db.commit()
            return result

        except Exception as e:
            self.db.rollback()
            self.logger.error(f"标记全部已读失败：{str(e)}")
            return 0
