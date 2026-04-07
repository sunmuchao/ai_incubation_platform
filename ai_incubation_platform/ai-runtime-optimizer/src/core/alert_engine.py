"""
告警引擎：多维度告警规则配置、通知、聚合与降噪
对标 Datadog 告警系统核心能力
"""
import uuid
import time
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Set
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
import asyncio

from core.audit import audit_logger, AuditEventType, AuditStatus


logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """告警严重程度"""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class AlertStatus(str, Enum):
    """告警状态"""
    FIRING = "firing"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class AlertOperator(str, Enum):
    """告警条件操作符"""
    GT = "gt"  # >
    GTE = "gte"  # >=
    LT = "lt"  # <
    LTE = "lte"  # <=
    EQ = "eq"  # ==
    NE = "ne"  # !=
    CONTAINS = "contains"
    MATCHES = "matches"  # 正则匹配


class AlertConditionType(str, Enum):
    """告警条件类型"""
    THRESHOLD = "threshold"  # 静态阈值
    RATE_OF_CHANGE = "rate_of_change"  # 变化率
    ABSENT = "absent"  # 数据缺失
    ANOMALY = "anomaly"  # 异常检测


class NotificationChannelType(str, Enum):
    """通知渠道类型"""
    WEBHOOK = "webhook"
    EMAIL = "email"
    DINGTALK = "dingtalk"
    SLACK = "slack"
    PAGERDUTY = "pagerduty"


@dataclass
class AlertCondition:
    """告警条件"""
    field: str  # 指标字段路径，支持点号嵌套
    operator: AlertOperator
    value: Any
    condition_type: AlertConditionType = AlertConditionType.THRESHOLD
    window_seconds: int = 60  # 时间窗口（秒）
    min_occurrences: int = 3  # 最小触发次数（用于降噪）
    negate: bool = False


@dataclass
class NotificationConfig:
    """通知配置"""
    channel_type: NotificationChannelType
    target: str  # webhook URL / 邮箱 / 群组 ID
    template: Optional[str] = None  # 通知模板
    retry_count: int = 3  # 重试次数
    retry_interval_seconds: int = 30  # 重试间隔
    enabled: bool = True


@dataclass
class AlertRule:
    """告警规则"""
    id: str
    name: str
    description: str
    service_name: Optional[str] = None  # 服务名称过滤，None 表示所有服务
    conditions: List[AlertCondition] = field(default_factory=list)
    severity: AlertSeverity = AlertSeverity.WARNING
    notification_configs: List[NotificationConfig] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
    cooldown_seconds: int = 300  # 冷却时间（避免告警风暴）
    auto_resolve_seconds: int = 600  # 自动恢复时间（数据恢复正常后多久自动关闭）
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertEvent:
    """告警事件"""
    id: str
    rule_id: str
    rule_name: str
    service_name: Optional[str]
    severity: AlertSeverity
    status: AlertStatus
    title: str
    message: str
    evidence: Dict[str, Any]
    tags: List[str]
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    notification_sent_count: int = 0
    last_notification_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertAggregationGroup:
    """告警聚合组 - 用于降噪和关联告警"""
    group_key: str
    rule_ids: Set[str]
    service_name: Optional[str]
    alerts: List[AlertEvent] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class AlertEngine:
    """告警引擎"""

    def __init__(self):
        self._rules: Dict[str, AlertRule] = {}
        self._active_alerts: Dict[str, AlertEvent] = {}
        self._alert_history: List[AlertEvent] = []
        self._alert_counts_by_service: Dict[str, int] = defaultdict(int)
        self._last_alert_time_by_rule: Dict[str, datetime] = {}
        self._notification_handlers: Dict[NotificationChannelType, Callable] = {}
        self._aggregation_groups: Dict[str, AlertAggregationGroup] = {}

        # 注册默认通知处理器
        self._register_default_notification_handlers()

    def _register_default_notification_handlers(self):
        """注册默认通知处理器"""
        # Webhook 处理器
        self._notification_handlers[NotificationChannelType.WEBHOOK] = self._send_webhook
        # 钉钉处理器
        self._notification_handlers[NotificationChannelType.DINGTALK] = self._send_dingtalk
        # Slack 处理器
        self._notification_handlers[NotificationChannelType.SLACK] = self._send_slack
        # 邮件处理器（占位）
        self._notification_handlers[NotificationChannelType.EMAIL] = self._send_email
        # PagerDuty 处理器
        self._notification_handlers[NotificationChannelType.PAGERDUTY] = self._send_pagerduty

    async def _send_webhook(self, config: NotificationConfig, alert: AlertEvent) -> bool:
        """发送 Webhook 通知"""
        import httpx
        try:
            payload = {
                "alert_id": alert.id,
                "rule_id": alert.rule_id,
                "rule_name": alert.rule_name,
                "service_name": alert.service_name,
                "severity": alert.severity.value,
                "status": alert.status.value,
                "title": alert.title,
                "message": alert.message,
                "evidence": alert.evidence,
                "triggered_at": alert.triggered_at.isoformat(),
                "tags": alert.tags
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config.target,
                    json=payload,
                    timeout=10.0
                )
                return response.status_code < 400
        except Exception as e:
            logger.error(f"Webhook notification failed: {e}")
            return False

    async def _send_dingtalk(self, config: NotificationConfig, alert: AlertEvent) -> bool:
        """发送钉钉通知"""
        import httpx
        try:
            # 钉钉机器人消息格式
            markdown_content = f"""## {alert.title}
**告警级别**: {alert.severity.value}
**服务名称**: {alert.service_name or 'N/A'}
**触发时间**: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}

{alert.message}

**证据数据**:
```json
{alert.evidence}
```
"""
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": alert.title,
                    "text": markdown_content
                }
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config.target,
                    json=payload,
                    timeout=10.0
                )
                return response.status_code < 400
        except Exception as e:
            logger.error(f"DingTalk notification failed: {e}")
            return False

    async def _send_slack(self, config: NotificationConfig, alert: AlertEvent) -> bool:
        """发送 Slack 通知"""
        import httpx
        try:
            color_map = {
                AlertSeverity.CRITICAL: "danger",
                AlertSeverity.ERROR: "danger",
                AlertSeverity.WARNING: "warning",
                AlertSeverity.INFO: "good"
            }
            payload = {
                "attachments": [
                    {
                        "color": color_map.get(alert.severity, "warning"),
                        "title": alert.title,
                        "text": alert.message,
                        "fields": [
                            {"title": "Severity", "value": alert.severity.value, "short": True},
                            {"title": "Service", "value": alert.service_name or "N/A", "short": True},
                            {"title": "Status", "value": alert.status.value, "short": True},
                            {"title": "Triggered", "value": alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S'), "short": True}
                        ],
                        "footer": f"Alert ID: {alert.id}"
                    }
                ]
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config.target,
                    json=payload,
                    timeout=10.0
                )
                return response.status_code < 400
        except Exception as e:
            logger.error(f"Slack notification failed: {e}")
            return False

    async def _send_email(self, config: NotificationConfig, alert: AlertEvent) -> bool:
        """发送邮件通知（占位实现）"""
        logger.info(f"[EMAIL] Would send to {config.target}: {alert.title}")
        return True

    async def _send_pagerduty(self, config: NotificationConfig, alert: AlertEvent) -> bool:
        """发送 PagerDuty 通知"""
        import httpx
        try:
            # PagerDuty Events API v2
            routing_key = config.target  # target 存放 routing key
            payload = {
                "routing_key": routing_key,
                "event_action": "trigger" if alert.status == AlertStatus.FIRING else "resolve",
                "dedup_key": alert.id,
                "payload": {
                    "summary": alert.title,
                    "severity": alert.severity.value,
                    "source": alert.service_name or "ai-runtime-optimizer",
                    "timestamp": alert.triggered_at.isoformat(),
                    "custom_details": alert.evidence
                }
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json=payload,
                    timeout=10.0
                )
                return response.status_code < 400
        except Exception as e:
            logger.error(f"PagerDuty notification failed: {e}")
            return False

    def add_rule(self, rule: AlertRule) -> str:
        """添加告警规则"""
        if rule.id in self._rules:
            raise ValueError(f"Alert rule ID {rule.id} already exists")
        self._rules[rule.id] = rule
        logger.info(f"Alert rule added: {rule.id} - {rule.name}")
        return rule.id

    def remove_rule(self, rule_id: str) -> bool:
        """移除告警规则"""
        if rule_id in self._rules:
            del self._rules[rule_id]
            logger.info(f"Alert rule removed: {rule_id}")
            return True
        return False

    def update_rule(self, rule_id: str, **kwargs) -> Optional[AlertRule]:
        """更新告警规则"""
        if rule_id not in self._rules:
            return None

        rule = self._rules[rule_id]
        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)

        logger.info(f"Alert rule updated: {rule_id}")
        return rule

    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """获取告警规则"""
        return self._rules.get(rule_id)

    def list_rules(
        self,
        service_name: Optional[str] = None,
        enabled_only: bool = True
    ) -> List[AlertRule]:
        """列出告警规则"""
        rules = list(self._rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        if service_name:
            rules = [r for r in rules if r.service_name is None or r.service_name == service_name]
        return sorted(rules, key=lambda r: r.severity.value)

    def get_active_alerts(
        self,
        service_name: Optional[str] = None,
        severity: Optional[AlertSeverity] = None,
        status: Optional[AlertStatus] = None
    ) -> List[AlertEvent]:
        """获取活跃告警"""
        alerts = list(self._active_alerts.values())
        if service_name:
            alerts = [a for a in alerts if a.service_name == service_name]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if status:
            alerts = [a for a in alerts if a.status == status]
        return sorted(alerts, key=lambda a: a.triggered_at, reverse=True)

    def get_alert_history(
        self,
        service_name: Optional[str] = None,
        limit: int = 100
    ) -> List[AlertEvent]:
        """获取告警历史"""
        history = self._alert_history
        if service_name:
            history = [a for a in history if a.service_name == service_name]
        return sorted(history, key=lambda a: a.triggered_at, reverse=True)[:limit]

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """确认告警"""
        if alert_id not in self._active_alerts:
            return False

        alert = self._active_alerts[alert_id]
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = acknowledged_by

        logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")

        # 审计日志
        audit_logger.log(
            audit_logger._create_event(
                event_type=AuditEventType.ADAPTER_CALL,
                action=f"acknowledge_alert:{alert_id}",
                input_data={"acknowledged_by": acknowledged_by},
                status=AuditStatus.SUCCESS
            )
        )

        return True

    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        if alert_id not in self._active_alerts:
            return False

        alert = self._active_alerts[alert_id]
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow()

        # 移动到历史记录
        self._alert_history.append(alert)
        del self._active_alerts[alert_id]

        # 更新聚合组
        self._remove_from_aggregation_group(alert)

        # 更新服务告警计数
        if alert.service_name:
            self._alert_counts_by_service[alert.service_name] = max(
                0, self._alert_counts_by_service[alert.service_name] - 1
            )

        logger.info(f"Alert resolved: {alert_id}")

        # 审计日志
        audit_logger.log(
            audit_logger._create_event(
                event_type=AuditEventType.ADAPTER_CALL,
                action=f"resolve_alert:{alert_id}",
                input_data={"alert_id": alert_id},
                status=AuditStatus.SUCCESS
            )
        )

        return True

    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """获取嵌套字段值"""
        current = data
        for part in field_path.split('.'):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def _evaluate_condition(self, data: Dict[str, Any], condition: AlertCondition) -> bool:
        """评估告警条件"""
        value = self._get_nested_value(data, condition.field)
        if value is None:
            return condition.condition_type == AlertConditionType.ABSENT

        target = condition.value
        op = condition.operator

        try:
            if op == AlertOperator.GT:
                result = value > target
            elif op == AlertOperator.GTE:
                result = value >= target
            elif op == AlertOperator.LT:
                result = value < target
            elif op == AlertOperator.LTE:
                result = value <= target
            elif op == AlertOperator.EQ:
                result = value == target
            elif op == AlertOperator.NE:
                result = value != target
            elif op == AlertOperator.CONTAINS:
                result = target in value if isinstance(value, (list, str, dict)) else False
            elif op == AlertOperator.MATCHES:
                import re
                result = bool(re.search(target, str(value)))
            else:
                result = False
        except (TypeError, ValueError):
            result = False

        return not result if condition.negate else result

    def _should_trigger_alert(self, rule: AlertRule, data: Dict[str, Any]) -> bool:
        """判断是否应该触发告警"""
        # 检查规则是否启用
        if not rule.enabled:
            return False

        # 检查服务名称匹配
        if rule.service_name and data.get("service_name") != rule.service_name:
            return False

        # 检查所有条件
        conditions_matched = all(
            self._evaluate_condition(data, cond) for cond in rule.conditions
        )

        return conditions_matched

    def _should_send_notification(self, rule: AlertRule) -> bool:
        """判断是否应该发送通知（冷却时间检查）"""
        now = datetime.utcnow()
        last_alert_time = self._last_alert_time_by_rule.get(rule.id)

        if last_alert_time:
            elapsed = (now - last_alert_time).total_seconds()
            if elapsed < rule.cooldown_seconds:
                return False

        return True

    def _get_aggregation_key(self, rule: AlertRule, data: Dict[str, Any]) -> str:
        """生成告警聚合键"""
        parts = []
        if rule.service_name:
            parts.append(f"service:{rule.service_name}")
        else:
            service = data.get("service_name", "unknown")
            parts.append(f"service:{service}")

        # 按规则 ID 聚合
        parts.append(f"rule:{rule.id}")

        # 按标签聚合
        for tag in rule.tags:
            tag_value = data.get(tag, "unknown")
            parts.append(f"{tag}:{tag_value}")

        return "|".join(parts)

    def _add_to_aggregation_group(self, alert: AlertEvent, group_key: str, rule: AlertRule):
        """将告警添加到聚合组"""
        if group_key not in self._aggregation_groups:
            self._aggregation_groups[group_key] = AlertAggregationGroup(
                group_key=group_key,
                rule_ids={rule.id},
                service_name=alert.service_name
            )

        group = self._aggregation_groups[group_key]
        group.alerts.append(alert)
        group.updated_at = datetime.utcnow()

        # 清理过期聚合组（超过 1 小时无更新）
        self._cleanup_stale_aggregation_groups()

    def _remove_from_aggregation_group(self, alert: AlertEvent):
        """从聚合组移除告警"""
        for group_key, group in list(self._aggregation_groups.items()):
            if alert in group.alerts:
                group.alerts.remove(alert)
                if not group.alerts:
                    del self._aggregation_groups[group_key]
                break

    def _cleanup_stale_aggregation_groups(self):
        """清理过期聚合组"""
        now = datetime.utcnow()
        stale_keys = []

        for group_key, group in self._aggregation_groups.items():
            if (now - group.updated_at).total_seconds() > 3600:
                stale_keys.append(group_key)

        for key in stale_keys:
            del self._aggregation_groups[key]

    async def send_notifications(self, alert: AlertEvent, rule: AlertRule):
        """发送告警通知"""
        if not self._should_send_notification(rule):
            logger.debug(f"Notification suppressed for rule {rule.id} (cooldown)")
            return

        tasks = []
        for config in rule.notification_configs:
            if not config.enabled:
                continue

            handler = self._notification_handlers.get(config.channel_type)
            if handler:
                # 重试逻辑
                for attempt in range(config.retry_count):
                    success = await handler(config, alert)
                    if success:
                        alert.notification_sent_count += 1
                        alert.last_notification_at = datetime.utcnow()
                        break
                    else:
                        await asyncio.sleep(config.retry_interval_seconds)

        # 更新最后告警时间
        self._last_alert_time_by_rule[rule.id] = datetime.utcnow()

    async def evaluate(self, data: Dict[str, Any]) -> List[AlertEvent]:
        """评估数据并触发告警"""
        triggered_alerts = []
        service_name = data.get("service_name")

        for rule in self._rules.values():
            if not self._should_trigger_alert(rule, data):
                continue

            # 创建告警事件
            alert_id = f"alert-{uuid.uuid4().hex[:12]}"
            alert = AlertEvent(
                id=alert_id,
                rule_id=rule.id,
                rule_name=rule.name,
                service_name=service_name,
                severity=rule.severity,
                status=AlertStatus.FIRING,
                title=f"[{rule.severity.value.upper()}] {rule.name}",
                message=rule.description,
                evidence=data,
                tags=rule.tags,
                triggered_at=datetime.utcnow()
            )

            # 添加到活跃告警
            self._active_alerts[alert_id] = alert

            # 更新服务告警计数
            if service_name:
                self._alert_counts_by_service[service_name] += 1

            # 添加到聚合组
            group_key = self._get_aggregation_key(rule, data)
            self._add_to_aggregation_group(alert, group_key, rule)

            # 发送通知
            await self.send_notifications(alert, rule)

            # 审计日志
            audit_logger.log(
                audit_logger._create_event(
                    event_type=AuditEventType.ADAPTER_CALL,
                    action=f"trigger_alert:{alert_id}",
                    input_data={
                        "rule_id": rule.id,
                        "service_name": service_name,
                        "severity": rule.severity.value
                    },
                    status=AuditStatus.SUCCESS
                )
            )

            triggered_alerts.append(alert)
            logger.info(f"Alert triggered: {alert_id} - {rule.name} (severity: {rule.severity.value})")

        return triggered_alerts

    def get_alert_stats(self) -> Dict[str, Any]:
        """获取告警统计"""
        return {
            "active_alerts": len(self._active_alerts),
            "alerts_by_severity": {
                severity.value: len([a for a in self._active_alerts.values() if a.severity == severity])
                for severity in AlertSeverity
            },
            "alerts_by_service": dict(self._alert_counts_by_service),
            "total_rules": len(self._rules),
            "enabled_rules": len([r for r in self._rules.values() if r.enabled]),
            "aggregation_groups": len(self._aggregation_groups),
            "history_count": len(self._alert_history)
        }

    def auto_resolve_check(self, max_age_seconds: int = 3600):
        """自动恢复检查 - 检查长时间未恢复的告警"""
        now = datetime.utcnow()

        for alert_id, alert in list(self._active_alerts.items()):
            if alert.status != AlertStatus.FIRING:
                continue

            # 检查告警是否超过自动恢复时间
            if (now - alert.triggered_at).total_seconds() > max_age_seconds:
                # 这里应该检查最新数据是否已恢复正常
                # 简化实现：直接标记为需要检查
                logger.debug(f"Alert {alert_id} needs auto-resolve check")


# 全局告警引擎实例
alert_engine = AlertEngine()


def create_default_alert_rules():
    """创建默认告警规则"""
    # 高错误率告警
    alert_engine.add_rule(AlertRule(
        id="built-in-high-error-rate",
        name="高错误率告警",
        description="服务错误率超过阈值",
        conditions=[
            AlertCondition(
                field="error_rate",
                operator=AlertOperator.GT,
                value=0.01,
                min_occurrences=3
            )
        ],
        severity=AlertSeverity.CRITICAL,
        tags=["reliability", "error"]
    ))

    # 高延迟告警
    alert_engine.add_rule(AlertRule(
        id="built-in-high-latency",
        name="高延迟告警",
        description="P99 延迟超过阈值",
        conditions=[
            AlertCondition(
                field="latency_p99_ms",
                operator=AlertOperator.GT,
                value=1000,
                min_occurrences=3
            )
        ],
        severity=AlertSeverity.ERROR,
        tags=["performance", "latency"]
    ))

    # 高 CPU 使用率告警
    alert_engine.add_rule(AlertRule(
        id="built-in-high-cpu",
        name="高 CPU 使用率告警",
        description="CPU 使用率超过阈值",
        conditions=[
            AlertCondition(
                field="cpu_percent",
                operator=AlertOperator.GT,
                value=90,
                min_occurrences=3
            )
        ],
        severity=AlertSeverity.WARNING,
        tags=["capacity", "cpu"]
    ))

    # 高内存使用率告警
    alert_engine.add_rule(AlertRule(
        id="built-in-high-memory",
        name="高内存使用率告警",
        description="内存使用率过高（基于 1GB 基准）",
        conditions=[
            AlertCondition(
                field="memory_mb",
                operator=AlertOperator.GT,
                value=900,
                min_occurrences=3
            )
        ],
        severity=AlertSeverity.WARNING,
        tags=["capacity", "memory"]
    ))


# 初始化默认规则
create_default_alert_rules()
