"""
内存通知适配器 - 用于开发测试

将通知存储在内存中，不支持持久化。
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid

from adapters.notification.base import (
    NotificationAdapter,
    NotificationConfig,
    NotificationMessage,
    NotificationResult
)


class InMemoryNotificationAdapter(NotificationAdapter):
    """内存通知适配器"""

    def __init__(self, config: Optional[NotificationConfig] = None):
        super().__init__(config)
        # 内存存储：user_id -> [notifications]
        self._notifications: Dict[str, List[Dict[str, Any]]] = {}

    def send(self, message: NotificationMessage) -> NotificationResult:
        """发送单条通知"""
        if not self.enabled:
            return NotificationResult(
                success=False,
                error="适配器未启用"
            )

        message_id = str(uuid.uuid4())
        notification = {
            "id": message_id,
            "user_id": message.user_id,
            "type": message.type,
            "title": message.title,
            "content": message.content,
            "related_id": message.related_id,
            "data": message.data,
            "priority": message.priority,
            "is_read": False,
            "created_at": datetime.now(),
            "read_at": None
        }

        # 存储到内存
        if message.user_id not in self._notifications:
            self._notifications[message.user_id] = []
        self._notifications[message.user_id].append(notification)

        self.logger.info(f"通知已发送 (内存): {message_id} -> {message.user_id}")

        return NotificationResult(
            success=True,
            message_id=message_id
        )

    def send_batch(self, messages: List[NotificationMessage]) -> List[NotificationResult]:
        """批量发送通知"""
        results = []
        for message in messages:
            result = self.send(message)
            results.append(result)
        return results

    def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取用户通知列表"""
        notifications = self._notifications.get(user_id, [])

        if unread_only:
            notifications = [n for n in notifications if not n["is_read"]]

        # 按时间倒序排序
        notifications.sort(key=lambda x: x["created_at"], reverse=True)

        return notifications[:limit]

    def mark_as_read(self, user_id: str, message_id: str) -> bool:
        """标记通知为已读"""
        notifications = self._notifications.get(user_id, [])
        for notification in notifications:
            if notification["id"] == message_id:
                notification["is_read"] = True
                notification["read_at"] = datetime.now()
                return True
        return False

    def mark_all_as_read(self, user_id: str) -> int:
        """标记所有通知为已读"""
        notifications = self._notifications.get(user_id, [])
        count = 0
        for notification in notifications:
            if not notification["is_read"]:
                notification["is_read"] = True
                notification["read_at"] = datetime.now()
                count += 1
        return count

    def clear(self, user_id: Optional[str] = None) -> None:
        """清除通知（测试用）"""
        if user_id:
            self._notifications[user_id] = []
        else:
            self._notifications = {}
