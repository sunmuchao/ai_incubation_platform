"""
Webhook 通知服务

提供 Discord 风格的 Webhook 集成：
- Webhook 配置管理
- 事件订阅
- HMAC 签名验证
- 异步 HTTP 调用
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import hashlib
import hmac
import json
import logging
import uuid

logger = logging.getLogger(__name__)


class WebhookEvent(str, Enum):
    """Webhook 事件类型"""
    # 内容相关
    POST_CREATED = "post.created"
    POST_UPDATED = "post.updated"
    POST_DELETED = "post.deleted"
    POST_PINNED = "post.pinned"

    COMMENT_CREATED = "comment.created"
    COMMENT_UPDATED = "comment.updated"
    COMMENT_DELETED = "comment.deleted"

    # 审核相关
    CONTENT_REVIEWED = "content.reviewed"
    CONTENT_APPROVED = "content.approved"
    CONTENT_REJECTED = "content.rejected"
    CONTENT_FLAGGED = "content.flagged"

    # 举报相关
    REPORT_CREATED = "report.created"
    REPORT_PROCESSED = "report.processed"

    # 治理相关
    USER_BANNED = "user.banned"
    USER_UNBANNED = "user.unbanned"
    USER_WARNED = "user.warned"
    CONTENT_REMOVED = "content.removed"

    # 系统相关
    USER_ANNOTATION_ADDED = "user.annotation_added"
    RATE_LIMIT_EXCEEDED = "rate_limit.exceeded"


class WebhookStatus(str, Enum):
    """Webhook 状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"  # 连续失败多次后标记


class WebhookDeliveryRecord:
    """Webhook 投递记录"""

    def __init__(
        self,
        webhook_id: str,
        event: WebhookEvent,
        payload: Dict[str, Any],
        status: str = "pending",
        response_code: int = None,
        response_body: str = None,
        error_message: str = None
    ):
        self.id = str(uuid.uuid4())
        self.webhook_id = webhook_id
        self.event = event
        self.payload = payload
        self.status = status
        self.response_code = response_code
        self.response_body = response_body
        self.error_message = error_message
        self.created_at = datetime.now()
        self.retry_count = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "webhook_id": self.webhook_id,
            "event": self.event.value,
            "payload": self.payload,
            "status": self.status,
            "response_code": self.response_code,
            "response_body": self.response_body,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "retry_count": self.retry_count
        }


class WebhookConfig:
    """Webhook 配置"""

    def __init__(
        self,
        name: str,
        url: str,
        events: List[WebhookEvent],
        is_active: bool = True,
        secret: str = None,
        custom_headers: Dict[str, str] = None,
        timeout_seconds: int = 30,
        max_retries: int = 3,
        content_type: str = "application/json"
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.url = url
        self.events = events
        self.is_active = is_active
        self.secret = secret or str(uuid.uuid4())
        self.custom_headers = custom_headers or {}
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.content_type = content_type
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.success_count = 0
        self.failure_count = 0
        self.last_delivery_at: datetime = None
        self.status = WebhookStatus.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "events": [e.value for e in self.events],
            "is_active": self.is_active,
            "secret_masked": self._mask_secret(),
            "custom_headers": self.custom_headers,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "content_type": self.content_type,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_delivery_at": self.last_delivery_at.isoformat() if self.last_delivery_at else None,
            "status": self.status.value
        }

    def _mask_secret(self) -> str:
        """掩码显示 secret"""
        if not self.secret:
            return ""
        if len(self.secret) <= 8:
            return "****"
        return self.secret[:4] + "****" + self.secret[-4:]

    def should_retry(self, retry_count: int) -> bool:
        """是否应该重试"""
        return retry_count < self.max_retries


class WebhookService:
    """Webhook 服务"""

    def __init__(self):
        self._webhooks: Dict[str, WebhookConfig] = {}
        self._delivery_records: List[WebhookDeliveryRecord] = []
        self._max_records = 1000  # 最多保留的投递记录数

    def create_webhook(
        self,
        name: str,
        url: str,
        events: List[str],
        is_active: bool = True,
        secret: str = None,
        custom_headers: Dict[str, str] = None,
        creator_id: str = None
    ) -> WebhookConfig:
        """创建 Webhook"""
        # 转换事件字符串为枚举
        webhook_events = []
        for event_str in events:
            try:
                webhook_events.append(WebhookEvent(event_str))
            except ValueError:
                logger.warning(f"未知事件类型：{event_str}")

        if not webhook_events:
            raise ValueError("至少需要订阅一个有效的事件")

        webhook = WebhookConfig(
            name=name,
            url=url,
            events=webhook_events,
            is_active=is_active,
            secret=secret,
            custom_headers=custom_headers
        )

        self._webhooks[webhook.id] = webhook

        logger.info(f"创建 Webhook: {name} ({webhook.id})")
        return webhook

    def get_webhook(self, webhook_id: str) -> Optional[WebhookConfig]:
        """获取 Webhook 配置"""
        return self._webhooks.get(webhook_id)

    def list_webhooks(
        self,
        is_active: bool = None,
        limit: int = 100
    ) -> List[WebhookConfig]:
        """获取 Webhook 列表"""
        webhooks = list(self._webhooks.values())

        if is_active is not None:
            webhooks = [w for w in webhooks if w.is_active == is_active]

        return sorted(webhooks, key=lambda w: w.created_at, reverse=True)[:limit]

    def update_webhook(
        self,
        webhook_id: str,
        name: str = None,
        url: str = None,
        events: List[str] = None,
        is_active: bool = None,
        custom_headers: Dict[str, str] = None
    ) -> Optional[WebhookConfig]:
        """更新 Webhook"""
        webhook = self._webhooks.get(webhook_id)
        if not webhook:
            return None

        if name:
            webhook.name = name
        if url:
            webhook.url = url
        if events:
            webhook_events = []
            for event_str in events:
                try:
                    webhook_events.append(WebhookEvent(event_str))
                except ValueError:
                    continue
            webhook.events = webhook_events
        if is_active is not None:
            webhook.is_active = is_active
        if custom_headers is not None:
            webhook.custom_headers = custom_headers

        webhook.updated_at = datetime.now()
        return webhook

    def delete_webhook(self, webhook_id: str) -> bool:
        """删除 Webhook"""
        if webhook_id in self._webhooks:
            del self._webhooks[webhook_id]
            logger.info(f"删除 Webhook: {webhook_id}")
            return True
        return False

    def _generate_signature(self, payload: str, secret: str) -> str:
        """生成 HMAC 签名"""
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _build_payload(
        self,
        event: WebhookEvent,
        data: Dict[str, Any],
        webhook_id: str
    ) -> Dict[str, Any]:
        """构建 Webhook 载荷"""
        return {
            "id": str(uuid.uuid4()),
            "event": event.value,
            "webhook_id": webhook_id,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }

    async def send_webhook(
        self,
        webhook_id: str,
        event: WebhookEvent,
        data: Dict[str, Any]
    ) -> WebhookDeliveryRecord:
        """
        发送 Webhook 通知

        Args:
            webhook_id: Webhook ID
            event: 事件类型
            data: 事件数据

        Returns:
            投递记录
        """
        webhook = self._webhooks.get(webhook_id)
        if not webhook:
            record = WebhookDeliveryRecord(
                webhook_id=webhook_id,
                event=event,
                payload={},
                status="failed",
                error_message="Webhook not found"
            )
            self._add_delivery_record(record)
            return record

        if not webhook.is_active:
            record = WebhookDeliveryRecord(
                webhook_id=webhook_id,
                event=event,
                payload={},
                status="skipped",
                error_message="Webhook is inactive"
            )
            self._add_delivery_record(record)
            return record

        # 检查事件是否订阅
        if event not in webhook.events:
            record = WebhookDeliveryRecord(
                webhook_id=webhook_id,
                event=event,
                payload={},
                status="skipped",
                error_message=f"Event {event.value} not subscribed"
            )
            self._add_delivery_record(record)
            return record

        # 构建请求
        payload = self._build_payload(event, data, webhook_id)
        payload_str = json.dumps(payload)

        headers = {
            "Content-Type": webhook.content_type,
            "X-Webhook-ID": webhook.id,
            "X-Webhook-Event": event.value,
            "X-Webhook-Timestamp": payload["timestamp"],
        }

        # 添加 HMAC 签名
        if webhook.secret:
            signature = self._generate_signature(payload_str, webhook.secret)
            headers["X-Webhook-Signature"] = f"sha256={signature}"
            headers["X-Webhook-Signature-Algorithm"] = "sha256"

        # 添加自定义请求头
        headers.update(webhook.custom_headers)

        # 发送请求（这里使用占位实现，实际应使用 httpx/aiohttp）
        record = await self._send_http_request(
            url=webhook.url,
            headers=headers,
            payload=payload_str,
            webhook=webhook,
            event=event
        )

        # 更新统计
        if record.status == "success":
            webhook.success_count += 1
        else:
            webhook.failure_count += 1
            # 检查是否需要标记为失败状态
            if webhook.failure_count >= 10:
                webhook.status = WebhookStatus.FAILED
                logger.warning(f"Webhook {webhook_id} marked as failed due to consecutive failures")

        webhook.last_delivery_at = datetime.now()
        self._add_delivery_record(record)

        return record

    async def _send_http_request(
        self,
        url: str,
        headers: Dict[str, str],
        payload: str,
        webhook: WebhookConfig,
        event: WebhookEvent
    ) -> WebhookDeliveryRecord:
        """
        发送 HTTP 请求（占位实现）

        实际项目中应使用 httpx 或 aiohttp 进行异步请求
        """
        record = WebhookDeliveryRecord(
            webhook_id=webhook.id,
            event=event,
            payload=json.loads(payload),
            status="pending"
        )

        try:
            # 占位实现：模拟成功
            # 实际实现应使用：
            # import httpx
            # async with httpx.AsyncClient() as client:
            #     response = await client.post(
            #         url,
            #         headers=headers,
            #         content=payload,
            #         timeout=webhook.timeout_seconds
            #     )
            #     record.status = "success" if response.status_code < 400 else "failed"
            #     record.response_code = response.status_code
            #     record.response_body = response.text

            logger.info(f"[Webhook 模拟] POST {url}, event: {event.value}")
            record.status = "success"
            record.response_code = 200
            record.response_body = '{"status": "ok"}'

        except Exception as e:
            record.status = "failed"
            record.error_message = str(e)
            logger.error(f"Webhook 发送失败：{e}")

        return record

    def _add_delivery_record(self, record: WebhookDeliveryRecord) -> None:
        """添加投递记录"""
        self._delivery_records.append(record)

        # 限制记录数量
        if len(self._delivery_records) > self._max_records:
            self._delivery_records = self._delivery_records[-self._max_records:]

    def get_delivery_records(
        self,
        webhook_id: str = None,
        status: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取投递记录"""
        records = self._delivery_records

        if webhook_id:
            records = [r for r in records if r.webhook_id == webhook_id]
        if status:
            records = [r for r in records if r.status == status]

        return sorted(
            records,
            key=lambda r: r.created_at,
            reverse=True
        )[:limit]

    def get_webhook_stats(self, webhook_id: str) -> Dict[str, Any]:
        """获取 Webhook 统计信息"""
        webhook = self._webhooks.get(webhook_id)
        if not webhook:
            return {"error": "Webhook not found"}

        # 获取该 Webhook 的投递记录
        records = [r for r in self._delivery_records if r.webhook_id == webhook_id]

        # 按状态统计
        status_counts = {}
        for record in records:
            status_counts[record.status] = status_counts.get(record.status, 0) + 1

        # 按事件统计
        event_counts = {}
        for record in records:
            event_value = record.event.value
            event_counts[event_value] = event_counts.get(event_value, 0) + 1

        return {
            "webhook_id": webhook_id,
            "webhook_name": webhook.name,
            "total_deliveries": len(records),
            "success_count": webhook.success_count,
            "failure_count": webhook.failure_count,
            "status": webhook.status.value,
            "delivery_status_breakdown": status_counts,
            "event_breakdown": event_counts,
            "last_delivery": webhook.last_delivery_at.isoformat() if webhook.last_delivery_at else None
        }

    def test_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """测试 Webhook（发送测试事件）"""
        webhook = self._webhooks.get(webhook_id)
        if not webhook:
            return {"success": False, "error": "Webhook not found"}

        test_data = {
            "message": "This is a test webhook",
            "test": True,
            "webhook_name": webhook.name,
            "timestamp": datetime.now().isoformat()
        }

        return {
            "success": True,
            "webhook_id": webhook_id,
            "test_payload": self._build_payload(
                WebhookEvent.POST_CREATED,  # 使用一个测试事件
                test_data,
                webhook_id
            ),
            "signature_hint": "sha256=..." if webhook.secret else "none"
        }

    def subscribe_event(
        self,
        webhook_id: str,
        event: str
    ) -> bool:
        """订阅事件"""
        webhook = self._webhooks.get(webhook_id)
        if not webhook:
            return False

        try:
            webhook_event = WebhookEvent(event)
            if webhook_event not in webhook.events:
                webhook.events.append(webhook_event)
                webhook.updated_at = datetime.now()
                logger.info(f"Webhook {webhook_id} subscribed to event: {event}")
            return True
        except ValueError:
            return False

    def unsubscribe_event(
        self,
        webhook_id: str,
        event: str
    ) -> bool:
        """取消订阅事件"""
        webhook = self._webhooks.get(webhook_id)
        if not webhook:
            return False

        try:
            webhook_event = WebhookEvent(event)
            if webhook_event in webhook.events:
                webhook.events.remove(webhook_event)
                webhook.updated_at = datetime.now()
                logger.info(f"Webhook {webhook_id} unsubscribed from event: {event}")
            return True
        except ValueError:
            return False

    def get_available_events(self) -> List[Dict[str, str]]:
        """获取所有可订阅的事件"""
        return [
            {"value": e.value, "name": e.value.replace(".", "_").upper()}
            for e in WebhookEvent
        ]


# 全局服务实例
webhook_service = WebhookService()
