"""
告警通知服务 - P0 告警通知

功能:
1. 多渠道通知（邮件、Slack、Webhook）
2. 告警规则配置和触发
3. 告警频率限制（防骚扰）
4. 告警历史记录
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass
import asyncio

import httpx
from sqlalchemy.orm import Session
from sqlalchemy import desc

from db.postgresql_models import AlertModel, AlertHistoryModel, SystemLogModel
from db.postgresql_config import get_db_session
from services.log_service import get_log_service


logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """告警严重级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationChannel(str, Enum):
    """通知渠道"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    DINGTALK = "dingtalk"


@dataclass
class AlertNotification:
    """告警通知数据"""
    alert_name: str
    alert_type: str
    severity: str
    message: str
    trigger_value: float
    threshold: float
    triggered_at: datetime
    trace_id: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


class AlertNotificationService:
    """告警通知服务"""

    def __init__(self, db_session: Optional[Session] = None):
        self._db_session = db_session
        self._log_service = get_log_service()
        self._cooldown_periods = {
            AlertSeverity.INFO: timedelta(minutes=30),
            AlertSeverity.WARNING: timedelta(minutes=15),
            AlertSeverity.ERROR: timedelta(minutes=10),
            AlertSeverity.CRITICAL: timedelta(minutes=5),
        }

    @property
    def db_session(self) -> Session:
        if self._db_session is None:
            return next(get_db_session())
        return self._db_session

    async def send_notification(
        self,
        notification: AlertNotification,
        channels: List[str],
        recipients: List[str],
    ) -> Dict[str, Any]:
        """
        发送告警通知

        Args:
            notification: 告警通知数据
            channels: 通知渠道列表
            recipients: 接收者列表

        Returns:
            Dict: 发送结果
        """
        results = {
            "success": [],
            "failed": [],
            "details": {},
        }

        for channel in channels:
            try:
                if channel == NotificationChannel.EMAIL:
                    result = await self._send_email(notification, recipients)
                elif channel == NotificationChannel.SLACK:
                    result = await self._send_slack(notification, recipients)
                elif channel == NotificationChannel.WEBHOOK:
                    result = await self._send_webhook(notification, recipients)
                elif channel == NotificationChannel.DINGTALK:
                    result = await self._send_dingtalk(notification, recipients)
                else:
                    result = {"success": False, "error": f"Unknown channel: {channel}"}

                if result.get("success"):
                    results["success"].append(channel)
                else:
                    results["failed"].append(channel)

                results["details"][channel] = result

            except Exception as e:
                logger.error(f"Failed to send notification via {channel}: {e}")
                results["failed"].append(channel)
                results["details"][channel] = {"success": False, "error": str(e)}

        return results

    async def _send_email(
        self,
        notification: AlertNotification,
        recipients: List[str],
    ) -> Dict[str, Any]:
        """发送邮件通知"""
        # TODO: 集成实际邮件服务
        subject = f"[{notification.severity.upper()}] {notification.alert_name}"
        body = self._format_email_body(notification)

        logger.info(f"Would send email to {recipients}: {subject}")
        logger.debug(f"Email body: {body}")

        return {
            "success": True,
            "recipients": recipients,
            "subject": subject,
        }

    def _format_email_body(self, notification: AlertNotification) -> str:
        """格式化邮件正文"""
        return f"""
告警通知

告警名称：{notification.alert_name}
告警类型：{notification.alert_type}
严重级别：{notification.severity.upper()}
触发时间：{notification.triggered_at.isoformat()}

触发详情:
- 当前值：{notification.trigger_value}
- 阈值：{notification.threshold}

{notification.message}

{json.dumps(notification.extra_data or {}, indent=2, ensure_ascii=False)}

---
此邮件由 AI Traffic Booster 系统自动发送
"""

    async def _send_slack(
        self,
        notification: AlertNotification,
        recipients: List[str],
    ) -> Dict[str, Any]:
        """发送 Slack 通知"""
        # Slack webhook URL 应从配置获取
        slack_webhook = self._get_slack_webhook()
        if not slack_webhook:
            return {"success": False, "error": "Slack webhook not configured"}

        color_map = {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ffcc00",
            AlertSeverity.ERROR: "#ff0000",
            AlertSeverity.CRITICAL: "#8b0000",
        }

        payload = {
            "attachments": [
                {
                    "color": color_map.get(notification.severity, "#8b0000"),
                    "title": f"{notification.alert_name}",
                    "text": notification.message,
                    "fields": [
                        {"title": "类型", "value": notification.alert_type, "short": True},
                        {"title": "级别", "value": notification.severity.upper(), "short": True},
                        {"title": "当前值", "value": str(notification.trigger_value), "short": True},
                        {"title": "阈值", "value": str(notification.threshold), "short": True},
                    ],
                    "footer": "AI Traffic Booster",
                    "ts": int(notification.triggered_at.timestamp()),
                }
            ]
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(slack_webhook, json=payload, timeout=10)
                response.raise_for_status()

            return {"success": True, "webhook": slack_webhook}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _send_webhook(
        self,
        notification: AlertNotification,
        recipients: List[str],
    ) -> Dict[str, Any]:
        """发送 Webhook 通知"""
        # recipients 中应包含 webhook URL
        results = []
        for webhook_url in recipients:
            try:
                payload = {
                    "alert_name": notification.alert_name,
                    "alert_type": notification.alert_type,
                    "severity": notification.severity,
                    "message": notification.message,
                    "trigger_value": notification.trigger_value,
                    "threshold": notification.threshold,
                    "triggered_at": notification.triggered_at.isoformat(),
                    "trace_id": notification.trace_id,
                    "extra_data": notification.extra_data,
                }

                async with httpx.AsyncClient() as client:
                    response = await client.post(webhook_url, json=payload, timeout=10)
                    response.raise_for_status()

                results.append({"url": webhook_url, "success": True})
            except Exception as e:
                results.append({"url": webhook_url, "success": False, "error": str(e)})

        return {"results": results}

    async def _send_dingtalk(
        self,
        notification: AlertNotification,
        recipients: List[str],
    ) -> Dict[str, Any]:
        """发送钉钉通知"""
        # 钉钉 webhook URL
        results = []
        for webhook_url in recipients:
            try:
                markdown_content = f"""## {notification.alert_name}
**告警类型**: {notification.alert_type}
**严重级别**: {notification.severity.upper()}
**触发时间**: {notification.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}

### 触发详情
- 当前值：{notification.trigger_value}
- 阈值：{notification.threshold}

{notification.message}
"""
                payload = {
                    "msgtype": "markdown",
                    "markdown": {
                        "title": notification.alert_name,
                        "text": markdown_content,
                    },
                }

                async with httpx.AsyncClient() as client:
                    response = await client.post(webhook_url, json=payload, timeout=10)
                    response.raise_for_status()

                results.append({"url": webhook_url, "success": True})
            except Exception as e:
                results.append({"url": webhook_url, "success": False, "error": str(e)})

        return {"results": results}

    def _get_slack_webhook(self) -> Optional[str]:
        """获取 Slack Webhook URL"""
        # 从环境变量或配置读取
        import os
        return os.environ.get("SLACK_WEBHOOK_URL")

    def should_suppress_alert(self, alert_id: str, severity: str) -> bool:
        """
        检查告警是否应该被抑制（防骚扰）

        Args:
            alert_id: 告警 ID
            severity: 告警级别

        Returns:
            bool: True 表示应该抑制
        """
        cooldown = self._cooldown_periods.get(
            AlertSeverity(severity.lower()),
            timedelta(minutes=15),
        )
        cutoff_time = datetime.utcnow() - cooldown

        last_alert = (
            self.db_session.query(AlertHistoryModel)
            .filter(
                AlertHistoryModel.alert_id == alert_id,
                AlertHistoryModel.triggered_at >= cutoff_time,
            )
            .order_by(desc(AlertHistoryModel.triggered_at))
            .first()
        )

        return last_alert is not None

    def record_alert_trigger(
        self,
        alert: AlertModel,
        trigger_value: float,
        trigger_reason: str,
    ) -> Optional[AlertHistoryModel]:
        """
        记录告警触发

        Args:
            alert: 告警配置
            trigger_value: 触发值
            trigger_reason: 触发原因

        Returns:
            AlertHistoryModel: 告警历史记录
        """
        try:
            history = AlertHistoryModel(
                alert_id=alert.id,
                trigger_reason=trigger_reason,
                trigger_value=trigger_value,
                threshold=alert.threshold,
                notification_sent=False,
            )

            self.db_session.add(history)
            self.db_session.commit()
            self.db_session.refresh(history)

            # 更新告警最后触发时间
            alert.last_triggered_at = datetime.utcnow()
            self.db_session.add(alert)
            self.db_session.commit()

            return history

        except Exception as e:
            logger.error(f"Failed to record alert trigger: {e}")
            self.db_session.rollback()
            return None

    def update_alert_notification_status(
        self,
        history: AlertHistoryModel,
        sent: bool,
        result: Optional[Dict] = None,
    ):
        """更新告警通知状态"""
        try:
            history.notification_sent = sent
            history.notification_result = result
            self.db_session.commit()
        except Exception as e:
            logger.error(f"Failed to update alert notification status: {e}")
            self.db_session.rollback()


# ==================== 告警规则引擎 ====================

class AlertRuleEngine:
    """告警规则引擎"""

    def __init__(self, db_session: Optional[Session] = None):
        self._db_session = db_session
        self._notification_service = AlertNotificationService(db_session)

    @property
    def db_session(self) -> Session:
        if self._db_session is None:
            return next(get_db_session())
        return self._db_session

    def get_active_alerts(self, alert_type: Optional[str] = None) -> List[AlertModel]:
        """获取活跃的告警配置"""
        query = self.db_session.query(AlertModel).filter(AlertModel.is_active == True)
        if alert_type:
            query = query.filter(AlertModel.alert_type == alert_type)
        return query.all()

    async def check_and_trigger_alerts(
        self,
        alert_type: str,
        metric_value: float,
        extra_data: Optional[Dict] = None,
        trace_id: Optional[str] = None,
    ):
        """
        检查并触发告警

        Args:
            alert_type: 告警类型
            metric_value: 指标值
            extra_data: 额外数据
            trace_id: 追踪 ID
        """
        alerts = self.get_active_alerts(alert_type)

        for alert in alerts:
            should_trigger = self._evaluate_conditions(alert, metric_value, extra_data)

            if should_trigger:
                # 检查是否需要抑制
                if self._notification_service.should_suppress_alert(alert.id, alert.severity):
                    logger.info(f"Alert suppressed due to cooldown: {alert.alert_name}")
                    continue

                # 记录告警触发
                history = self._notification_service.record_alert_trigger(
                    alert,
                    metric_value,
                    f"{alert_type} triggered with value {metric_value}",
                )

                if history:
                    # 发送通知
                    notification = AlertNotification(
                        alert_name=alert.alert_name,
                        alert_type=alert_type,
                        severity=alert.severity,
                        message=f"{alert.alert_name} 被触发",
                        trigger_value=metric_value,
                        threshold=alert.threshold,
                        triggered_at=datetime.utcnow(),
                        trace_id=trace_id,
                        extra_data=extra_data,
                    )

                    channels = alert.notification_channels or []
                    recipients = alert.recipients or []

                    result = await self._notification_service.send_notification(
                        notification, channels, recipients
                    )

                    # 更新通知状态
                    self._notification_service.update_alert_notification_status(
                        history,
                        sent=len(result.get("success", [])) > 0,
                        result=result,
                    )

                    # 记录日志
                    log_service = get_log_service()
                    log_service.log_alert_trigger(
                        alert_name=alert.alert_name,
                        alert_type=alert_type,
                        trigger_value=metric_value,
                        threshold=alert.threshold,
                        severity=alert.severity,
                        trace_id=trace_id,
                    )

    def _evaluate_conditions(
        self,
        alert: AlertModel,
        metric_value: float,
        extra_data: Optional[Dict] = None,
    ) -> bool:
        """
        评估告警条件

        Args:
            alert: 告警配置
            metric_value: 指标值
            extra_data: 额外数据

        Returns:
            bool: 是否触发告警
        """
        conditions = alert.conditions or {}
        threshold = alert.threshold

        if threshold is None:
            return False

        # 支持的条件操作符
        operator = conditions.get("operator", ">=")

        if operator == ">":
            return metric_value > threshold
        elif operator == ">=":
            return metric_value >= threshold
        elif operator == "<":
            return metric_value < threshold
        elif operator == "<=":
            return metric_value <= threshold
        elif operator == "==":
            return metric_value == threshold
        elif operator == "!=":
            return metric_value != threshold
        elif operator == "drop_by_percent":
            # 下跌百分比告警
            baseline = conditions.get("baseline", 0)
            if baseline <= 0:
                return False
            drop_percent = ((baseline - metric_value) / baseline) * 100
            return drop_percent >= threshold

        return False


# ==================== 全局服务实例 ====================

_alert_rule_engine: Optional[AlertRuleEngine] = None


def get_alert_rule_engine() -> AlertRuleEngine:
    """获取全局告警规则引擎实例"""
    global _alert_rule_engine
    if _alert_rule_engine is None:
        _alert_rule_engine = AlertRuleEngine()
    return _alert_rule_engine
