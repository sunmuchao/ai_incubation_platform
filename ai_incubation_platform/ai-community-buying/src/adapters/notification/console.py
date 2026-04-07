"""
控制台通知适配器 - 用于演示和调试

将通知输出到控制台，适用于本地开发和演示。
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid
import json

from adapters.notification.base import (
    NotificationAdapter,
    NotificationConfig,
    NotificationMessage,
    NotificationResult
)


class ConsoleNotificationAdapter(NotificationAdapter):
    """控制台通知适配器"""

    def __init__(self, config: Optional[NotificationConfig] = None):
        super().__init__(config)
        self._sent_count = 0

    def send(self, message: NotificationMessage) -> NotificationResult:
        """发送单条通知到控制台"""
        if not self.enabled:
            return NotificationResult(
                success=False,
                error="适配器未启用"
            )

        message_id = str(uuid.uuid4())
        self._sent_count += 1

        # 构建输出
        priority_emoji = {
            "low": "📝",
            "normal": "📬",
            "high": "📢",
            "urgent": "🚨"
        }
        emoji = priority_emoji.get(message.priority, "📬")

        output = f"""
{emoji} [{message.type}] {message.title}
   接收者：{message.user_id}
   内容：{message.content}
   时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
   优先级：{message.priority}
"""
        if message.related_id:
            output += f"   关联 ID: {message.related_id}\n"

        print(output)

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
        """获取用户通知列表（控制台适配器不支持）"""
        self.logger.warning("控制台适配器不支持获取通知列表")
        return []

    def mark_as_read(self, user_id: str, message_id: str) -> bool:
        """标记通知为已读（控制台适配器不支持）"""
        self.logger.warning("控制台适配器不支持标记已读")
        return False

    def mark_all_as_read(self, user_id: str) -> int:
        """标记所有通知为已读（控制台适配器不支持）"""
        self.logger.warning("控制台适配器不支持标记已读")
        return 0

    def get_stats(self) -> Dict[str, Any]:
        """获取发送统计"""
        return {
            "total_sent": self._sent_count,
            "enabled": self.enabled,
            "adapter_name": "ConsoleNotificationAdapter"
        }
