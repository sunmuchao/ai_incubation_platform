"""
通知服务 - 可插拔适配器模式

支持多种通知方式：
- 站内信通知（默认）
- 邮件通知
- Webhook 通知
- 自定义通知器
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Protocol
from datetime import datetime
from enum import Enum
import uuid
import logging

# 配置日志记录
logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """通知类型"""
    EMAIL = "email"
    IN_APP = "in_app"  # 站内信
    WEBHOOK = "webhook"
    WEBSOCKET = "websocket"  # WebSocket 实时推送
    CUSTOM = "custom"


class NotificationPriority(str, Enum):
    """通知优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(str, Enum):
    """通知状态"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    READ = "read"  # 仅站内信


class NotificationEvent(str, Enum):
    """通知事件类型"""
    # 内容相关
    CONTENT_APPROVED = "content_approved"  # 内容审核通过
    CONTENT_REJECTED = "content_rejected"  # 内容审核拒绝
    CONTENT_FLAGGED = "content_flagged"    # 内容被标记
    POST_PUBLISHED = "post_published"      # 帖子发布
    COMMENT_ADDED = "comment_added"        # 评论添加
    REPLY_ADDED = "reply_added"            # 回复添加

    # 治理相关
    REPORT_CREATED = "report_created"      # 举报创建
    REPORT_PROCESSED = "report_processed"  # 举报处理
    USER_BANNED = "user_banned"            # 用户被封禁
    USER_UNBANNED = "user_unbanned"        # 用户解封

    # 系统相关
    RATE_LIMIT_WARNING = "rate_limit_warning"  # 速率限制警告
    SYSTEM_MAINTENANCE = "system_maintenance"  # 系统维护通知

    # AI 相关
    AI_ACTION_COMPLETED = "ai_action_completed"  # AI 动作完成
    AI_REVIEW_COMPLETED = "ai_review_completed"  # AI 审核完成


class NotificationMessage:
    """通知消息模型"""
    def __init__(
        self,
        event_type: NotificationEvent,
        title: str,
        content: str,
        recipient_id: str,
        sender_id: Optional[str] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = str(uuid.uuid4())
        self.event_type = event_type
        self.title = title
        self.content = content
        self.recipient_id = recipient_id
        self.sender_id = sender_id
        self.priority = priority
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.status = NotificationStatus.PENDING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "title": self.title,
            "content": self.content,
            "recipient_id": self.recipient_id,
            "sender_id": self.sender_id,
            "priority": self.priority.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value
        }


class NotificationAdapter(ABC):
    """通知适配器基类"""

    @abstractmethod
    def send(self, message: NotificationMessage) -> bool:
        """发送通知"""
        pass

    @abstractmethod
    def get_adapter_type(self) -> NotificationType:
        """获取适配器类型"""
        pass


class InAppNotificationAdapter(NotificationAdapter):
    """站内信通知适配器"""

    def __init__(self):
        self._notifications: Dict[str, List[NotificationMessage]] = {}

    def send(self, message: NotificationMessage) -> bool:
        """发送站内信"""
        try:
            recipient_id = message.recipient_id
            if recipient_id not in self._notifications:
                self._notifications[recipient_id] = []
            message.status = NotificationStatus.SENT
            self._notifications[recipient_id].append(message)
            logger.info(f"站内信发送成功：{message.id} -> {recipient_id}")
            return True
        except Exception as e:
            logger.error(f"站内信发送失败：{e}")
            message.status = NotificationStatus.FAILED
            return False

    def get_adapter_type(self) -> NotificationType:
        return NotificationType.IN_APP

    def get_unread_count(self, user_id: str) -> int:
        """获取未读消息数量"""
        notifications = self._notifications.get(user_id, [])
        return sum(1 for n in notifications if n.status == NotificationStatus.SENT)

    def get_user_notifications(
        self,
        user_id: str,
        limit: int = 50,
        status: Optional[NotificationStatus] = None
    ) -> List[NotificationMessage]:
        """获取用户通知列表"""
        notifications = self._notifications.get(user_id, [])
        if status:
            notifications = [n for n in notifications if n.status == status]
        return sorted(notifications, key=lambda n: n.created_at, reverse=True)[:limit]

    def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """标记为已读"""
        notifications = self._notifications.get(user_id, [])
        for notification in notifications:
            if notification.id == notification_id:
                notification.status = NotificationStatus.READ
                return True
        return False

    def mark_all_as_read(self, user_id: str) -> int:
        """标记所有为已读"""
        notifications = self._notifications.get(user_id, [])
        count = 0
        for notification in notifications:
            if notification.status == NotificationStatus.SENT:
                notification.status = NotificationStatus.READ
                count += 1
        return count


class EmailNotificationAdapter(NotificationAdapter):
    """邮件通知适配器"""

    def __init__(
        self,
        smtp_host: str = "localhost",
        smtp_port: int = 25,
        sender_email: str = "noreply@example.com",
        use_tls: bool = False
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.use_tls = use_tls
        self._email_cache: List[Dict[str, Any]] = []  # 用于测试，存储发送记录

    def send(self, message: NotificationMessage) -> bool:
        """发送邮件通知"""
        try:
            # 这里应该使用 smtplib 发送真实邮件
            # 当前为模拟实现，仅记录日志
            logger.info(
                f"[模拟邮件发送] 收件人：{message.recipient_id}, "
                f"标题：{message.title}, 优先级：{message.priority.value}"
            )

            # 记录发送历史（用于测试）
            self._email_cache.append({
                "message": message.to_dict(),
                "sent_at": datetime.now()
            })

            message.status = NotificationStatus.SENT
            return True
        except Exception as e:
            logger.error(f"邮件发送失败：{e}")
            message.status = NotificationStatus.FAILED
            return False

    def get_adapter_type(self) -> NotificationType:
        return NotificationType.EMAIL

    def get_send_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取发送历史"""
        return self._email_cache[-limit:]


class WebhookNotificationAdapter(NotificationAdapter):
    """Webhook 通知适配器"""

    def __init__(self, webhook_urls: Optional[List[str]] = None):
        self.webhook_urls = webhook_urls or []
        self._call_history: List[Dict[str, Any]] = []

    def send(self, message: NotificationMessage) -> bool:
        """发送 Webhook 通知"""
        if not self.webhook_urls:
            logger.warning("没有配置 Webhook URL")
            return False

        success_count = 0
        payload = message.to_dict()

        for url in self.webhook_urls:
            try:
                # 这里应该使用 requests 库发送 HTTP 请求
                # 当前为模拟实现
                logger.info(f"[模拟 Webhook] POST {url}, payload: {payload}")

                self._call_history.append({
                    "url": url,
                    "payload": payload,
                    "sent_at": datetime.now(),
                    "status": "success"
                })
                success_count += 1
            except Exception as e:
                logger.error(f"Webhook 发送失败 {url}: {e}")
                self._call_history.append({
                    "url": url,
                    "payload": payload,
                    "sent_at": datetime.now(),
                    "status": "failed",
                    "error": str(e)
                })

        message.status = NotificationStatus.SENT if success_count > 0 else NotificationStatus.FAILED
        return success_count > 0

    def get_adapter_type(self) -> NotificationType:
        return NotificationType.WEBHOOK

    def add_webhook_url(self, url: str) -> None:
        """添加 Webhook URL"""
        if url not in self.webhook_urls:
            self.webhook_urls.append(url)

    def remove_webhook_url(self, url: str) -> None:
        """移除 Webhook URL"""
        if url in self.webhook_urls:
            self.webhook_urls.remove(url)


class WebSocketNotificationAdapter(NotificationAdapter):
    """WebSocket 实时通知适配器"""

    def __init__(self, websocket_service=None):
        self._websocket_service = websocket_service
        self._send_history: List[Dict[str, Any]] = []

    def send(self, message: NotificationMessage) -> bool:
        """发送 WebSocket 通知"""
        try:
            if self._websocket_service is None:
                # 如果没有 WebSocket 服务，降级为站内信
                logger.warning("WebSocket 服务未初始化，使用站内信降级")
                return False

            notification_data = {
                "id": message.id,
                "type": message.event_type.value,
                "title": message.title,
                "content": message.content,
                "priority": message.priority.value,
                "metadata": message.metadata,
                "created_at": message.created_at.isoformat(),
            }

            # 异步推送（不阻塞）
            import asyncio
            asyncio.create_task(
                self._websocket_service.push_notification(message.recipient_id, notification_data)
            )

            message.status = NotificationStatus.SENT
            self._send_history.append({
                "message": message.to_dict(),
                "sent_at": datetime.now(),
            })
            return True
        except Exception as e:
            logger.error(f"WebSocket 通知发送失败：{e}")
            message.status = NotificationStatus.FAILED
            return False

    def get_adapter_type(self) -> NotificationType:
        return NotificationType.WEBSOCKET

    def set_websocket_service(self, service) -> None:
        """设置 WebSocket 服务"""
        self._websocket_service = service

    def get_send_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取发送历史"""
        return self._send_history[-limit:]


class NotificationService:
    """通知服务 - 统一入口"""

    def __init__(self):
        self._adapters: Dict[NotificationType, NotificationAdapter] = {}
        self._event_subscriptions: Dict[NotificationEvent, List[NotificationType]] = {}
        self._user_preferences: Dict[str, Dict[NotificationEvent, List[NotificationType]]] = {}
        self._email_digest_preferences: Dict[str, Dict[str, Any]] = {}

        # 注册默认的站内信适配器
        self.register_adapter(InAppNotificationAdapter())

    def register_adapter(self, adapter: NotificationAdapter) -> None:
        """注册通知适配器"""
        adapter_type = adapter.get_adapter_type()
        self._adapters[adapter_type] = adapter
        logger.info(f"注册通知适配器：{adapter_type.value}")

    def get_adapter(self, adapter_type: NotificationType) -> Optional[NotificationAdapter]:
        """获取通知适配器"""
        return self._adapters.get(adapter_type)

    def subscribe_event(
        self,
        event: NotificationEvent,
        adapter_types: List[NotificationType]
    ) -> None:
        """订阅事件通知"""
        self._event_subscriptions[event] = adapter_types
        logger.info(f"订阅事件：{event.value} -> {[a.value for a in adapter_types]}")

    def set_user_preference(
        self,
        user_id: str,
        event: NotificationEvent,
        adapter_types: List[NotificationType]
    ) -> None:
        """设置用户通知偏好"""
        if user_id not in self._user_preferences:
            self._user_preferences[user_id] = {}
        self._user_preferences[user_id][event] = adapter_types
        logger.info(f"设置用户偏好：{user_id}, {event.value} -> {[a.value for a in adapter_types]}")

    def get_user_preference(
        self,
        user_id: str,
        event: NotificationEvent
    ) -> List[NotificationType]:
        """获取用户通知偏好"""
        # 用户自定义偏好优先
        if user_id in self._user_preferences:
            if event in self._user_preferences[user_id]:
                return self._user_preferences[user_id][event]

        # 回退到全局订阅配置
        return self._event_subscriptions.get(event, [NotificationType.IN_APP])

    def set_email_digest_preference(
        self,
        user_id: str,
        frequency: str,
        email: str,
        digest_time: int = 8
    ) -> None:
        """设置用户邮件摘要偏好"""
        if user_id not in self._email_digest_preferences:
            self._email_digest_preferences[user_id] = {}
        self._email_digest_preferences[user_id] = {
            "frequency": frequency,
            "email": email,
            "digest_time": digest_time,
            "enabled": frequency != "never"
        }
        logger.info(f"设置用户邮件摘要偏好：{user_id}, frequency={frequency}, email={email}")

    def get_email_digest_preference(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取用户邮件摘要偏好"""
        return self._email_digest_preferences.get(user_id)

    def send_notification(
        self,
        message: NotificationMessage,
        force_adapter_types: Optional[List[NotificationType]] = None
    ) -> Dict[str, bool]:
        """发送通知"""
        results = {}

        # 确定使用哪些适配器
        if force_adapter_types:
            adapter_types = force_adapter_types
        else:
            adapter_types = self.get_user_preference(
                message.recipient_id,
                message.event_type
            )

        for adapter_type in adapter_types:
            adapter = self._adapters.get(adapter_type)
            if adapter:
                success = adapter.send(message)
                results[adapter_type.value] = success
            else:
                logger.warning(f"适配器未注册：{adapter_type.value}")
                results[adapter_type.value] = False

        return results

    def send_bulk_notifications(
        self,
        messages: List[NotificationMessage]
    ) -> List[Dict[str, Any]]:
        """批量发送通知"""
        results = []
        for message in messages:
            result = self.send_notification(message)
            results.append({
                "message_id": message.id,
                "recipient_id": message.recipient_id,
                "results": result
            })
        return results

    # ==================== 便捷方法 ====================

    def notify_content_approved(
        self,
        recipient_id: str,
        content_type: str,
        content_id: str,
        content_title: str
    ) -> Dict[str, bool]:
        """通知内容审核通过"""
        message = NotificationMessage(
            event_type=NotificationEvent.CONTENT_APPROVED,
            title="内容审核通过",
            content=f"您的{content_type}「{content_title}」已通过审核，现在对所有人可见。",
            recipient_id=recipient_id,
            metadata={"content_type": content_type, "content_id": content_id}
        )
        return self.send_notification(message)

    def notify_content_rejected(
        self,
        recipient_id: str,
        content_type: str,
        content_id: str,
        content_title: str,
        reject_reason: str
    ) -> Dict[str, bool]:
        """通知内容审核拒绝"""
        message = NotificationMessage(
            event_type=NotificationEvent.CONTENT_REJECTED,
            title="内容审核未通过",
            content=f"您的{content_type}「{content_title}」未通过审核，原因：{reject_reason}",
            recipient_id=recipient_id,
            priority=NotificationPriority.HIGH,
            metadata={"content_type": content_type, "content_id": content_id, "reason": reject_reason}
        )
        return self.send_notification(message)

    def notify_new_reply(
        self,
        recipient_id: str,
        post_id: str,
        comment_id: str,
        replier_name: str,
        reply_content: str
    ) -> Dict[str, bool]:
        """通知新回复"""
        message = NotificationMessage(
            event_type=NotificationEvent.REPLY_ADDED,
            title=f"{replier_name} 回复了您",
            content=reply_content[:100],
            recipient_id=recipient_id,
            metadata={"post_id": post_id, "comment_id": comment_id, "replier_name": replier_name}
        )
        return self.send_notification(message)

    def notify_report_processed(
        self,
        reporter_id: str,
        report_id: str,
        status: str,
        handler_note: Optional[str] = None
    ) -> Dict[str, bool]:
        """通知举报处理结果"""
        message = NotificationMessage(
            event_type=NotificationEvent.REPORT_PROCESSED,
            title="举报处理完成",
            content=f"您举报的内容已处理完成，状态：{status}" + (f"，备注：{handler_note}" if handler_note else ""),
            recipient_id=reporter_id,
            metadata={"report_id": report_id, "status": status}
        )
        return self.send_notification(message)

    def notify_rate_limit_warning(
        self,
        user_id: str,
        resource: str,
        remaining: int,
        reset_time: str
    ) -> Dict[str, bool]:
        """通知速率限制警告"""
        message = NotificationMessage(
            event_type=NotificationEvent.RATE_LIMIT_WARNING,
            title="操作频率警告",
            content=f"您的{resource}操作剩余次数：{remaining}，将在 {reset_time} 后重置。",
            recipient_id=user_id,
            priority=NotificationPriority.HIGH,
            metadata={"resource": resource, "remaining": remaining}
        )
        return self.send_notification(message)


# 全局服务实例
notification_service = NotificationService()
