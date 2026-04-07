"""
预警系统
基于事件检测和规则引擎，实现商业事件预警
参考 CB Insights 的警报系统
"""
from typing import List, Dict, Optional, Callable, Any
from datetime import datetime, timedelta
from enum import Enum
import logging
import json
from collections import defaultdict
import asyncio

from nlp.event_detector import event_detector, BusinessEvent, EventType, EventSeverity

logger = logging.getLogger(__name__)


class AlertPriority(str, Enum):
    """预警优先级"""
    LOW = "low"  # 低优先级
    MEDIUM = "medium"  # 中优先级
    HIGH = "high"  # 高优先级
    CRITICAL = "critical"  # 紧急


class AlertStatus(str, Enum):
    """预警状态"""
    NEW = "new"  # 新建
    ACKNOWLEDGED = "acknowledged"  # 已确认
    RESOLVED = "resolved"  # 已解决
    DISMISSED = "dismissed"  # 已忽略


class AlertRule:
    """预警规则"""

    def __init__(
        self,
        rule_id: str,
        name: str,
        description: str = "",
        event_types: Optional[List[EventType]] = None,
        keywords: Optional[List[str]] = None,
        min_severity: EventSeverity = EventSeverity.LOW,
        companies: Optional[List[str]] = None,
        min_amount: Optional[float] = None,
        enabled: bool = True,
        notification_channels: Optional[List[str]] = None
    ):
        self.rule_id = rule_id
        self.name = name
        self.description = description
        self.event_types = event_types or []
        self.keywords = keywords or []
        self.min_severity = min_severity
        self.companies = companies or []
        self.min_amount = min_amount
        self.enabled = enabled
        self.notification_channels = notification_channels or []

        # 统计
        self.triggered_count = 0
        self.last_triggered_at: Optional[datetime] = None

    def match(self, event: BusinessEvent) -> bool:
        """检查事件是否匹配规则"""
        if not self.enabled:
            return False

        # 事件类型匹配
        if self.event_types and event.event_type not in self.event_types:
            return False

        # 严重性匹配
        severity_order = {
            EventSeverity.LOW: 0,
            EventSeverity.MEDIUM: 1,
            EventSeverity.HIGH: 2,
            EventSeverity.CRITICAL: 3
        }
        if severity_order.get(event.severity, 0) < severity_order.get(self.min_severity, 0):
            return False

        # 关键词匹配
        if self.keywords:
            text = f"{event.title} {event.summary}".lower()
            if not any(kw.lower() in text for kw in self.keywords):
                return False

        # 公司匹配
        if self.companies:
            if not any(company in event.companies for company in self.companies):
                return False

        # 金额匹配
        if self.min_amount and event.amount:
            if event.amount < self.min_amount:
                return False

        return True

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "event_types": [et.value for et in self.event_types] if self.event_types else [],
            "keywords": self.keywords,
            "min_severity": self.min_severity.value,
            "companies": self.companies,
            "min_amount": self.min_amount,
            "enabled": self.enabled,
            "notification_channels": self.notification_channels,
            "triggered_count": self.triggered_count,
            "last_triggered_at": self.last_triggered_at.isoformat() if self.last_triggered_at else None
        }


class Alert:
    """预警实例"""

    def __init__(
        self,
        alert_id: str,
        rule_id: str,
        rule_name: str,
        event: BusinessEvent,
        priority: AlertPriority,
        message: str,
        created_at: Optional[datetime] = None
    ):
        self.alert_id = alert_id
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.event = event
        self.priority = priority
        self.message = message
        self.status = AlertStatus.NEW
        self.created_at = created_at or datetime.now()
        self.acknowledged_at: Optional[datetime] = None
        self.resolved_at: Optional[datetime] = None
        self.acknowledged_by: Optional[str] = None
        self.notes: str = ""

    def acknowledge(self, user: str = "system"):
        """确认预警"""
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = datetime.now()
        self.acknowledged_by = user

    def resolve(self, notes: str = ""):
        """解决预警"""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.now()
        self.notes = notes

    def dismiss(self, notes: str = ""):
        """忽略预警"""
        self.status = AlertStatus.DISMISSED
        self.notes = notes

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "alert_id": self.alert_id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "priority": self.priority.value,
            "message": self.message,
            "status": self.status.value,
            "event": self.event.to_dict() if self.event else None,
            "created_at": self.created_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "acknowledged_by": self.acknowledged_by,
            "notes": self.notes
        }


class AlertEngine:
    """预警引擎"""

    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.alerts: Dict[str, Alert] = {}
        self.notification_handlers: Dict[str, Callable] = {}
        self.alert_callbacks: List[Callable[[Alert], None]] = []

        # 注册默认通知处理器
        self._register_default_handlers()

        # 预定义规则
        self._create_default_rules()

    def _register_default_handlers(self):
        """注册默认通知处理器"""
        # 控制台输出（用于开发）
        self.notification_handlers["console"] = lambda alert: logger.info(
            f"[ALERT] {alert.priority.value.upper()}: {alert.message}"
        )

        # 内存队列（用于测试）
        self.notification_handlers["memory"] = lambda alert: None  # 占位符

    def _create_default_rules(self):
        """创建默认规则"""
        # 大额融资预警
        self.add_rule(AlertRule(
            rule_id="funding_large",
            name="大额融资预警",
            description="监测金额超过 1 亿元的融资事件",
            event_types=[EventType.FUNDING, EventType.INVESTMENT],
            min_severity=EventSeverity.HIGH,
            min_amount=100000000,
            notification_channels=["console"]
        ))

        # 并购事件预警
        self.add_rule(AlertRule(
            rule_id="acquisition_alert",
            name="并购事件预警",
            description="监测企业并购事件",
            event_types=[EventType.ACQUISITION],
            min_severity=EventSeverity.MEDIUM,
            notification_channels=["console"]
        ))

        # IPO 预警
        self.add_rule(AlertRule(
            rule_id="ipo_alert",
            name="IPO 预警",
            description="监测企业 IPO/上市事件",
            event_types=[EventType.IPO],
            min_severity=EventSeverity.HIGH,
            notification_channels=["console"]
        ))

        # 高管变动预警
        self.add_rule(AlertRule(
            rule_id="executive_change",
            name="高管变动预警",
            description="监测企业高管变动（CEO/董事长等）",
            event_types=[EventType.EXECUTIVE_CHANGE],
            min_severity=EventSeverity.HIGH,
            keywords=["CEO", "董事长", "创始人", "总裁"],
            notification_channels=["console"]
        ))

        # 政策变化预警
        self.add_rule(AlertRule(
            rule_id="policy_change",
            name="政策变化预警",
            description="监测行业政策变化",
            event_types=[EventType.POLICY_CHANGE],
            min_severity=EventSeverity.MEDIUM,
            notification_channels=["console"]
        ))

        # 裁员预警
        self.add_rule(AlertRule(
            rule_id="layoff_alert",
            name="裁员预警",
            description="监测企业裁员事件",
            event_types=[EventType.LAYOFF],
            min_severity=EventSeverity.MEDIUM,
            notification_channels=["console"]
        ))

    def add_rule(self, rule: AlertRule):
        """添加预警规则"""
        self.rules[rule.rule_id] = rule
        logger.info(f"Added alert rule: {rule.name}")

    def remove_rule(self, rule_id: str):
        """移除预警规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Removed alert rule: {rule_id}")

    def enable_rule(self, rule_id: str):
        """启用规则"""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True

    def disable_rule(self, rule_id: str):
        """禁用规则"""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False

    def process_event(self, event: BusinessEvent) -> List[Alert]:
        """处理事件，触发匹配的预警"""
        triggered_alerts = []

        for rule in self.rules.values():
            if rule.match(event):
                alert = self._create_alert(rule, event)
                triggered_alerts.append(alert)
                self._trigger_alert(alert)

        return triggered_alerts

    def process_events(self, events: List[BusinessEvent]) -> List[Alert]:
        """批量处理事件"""
        all_alerts = []
        for event in events:
            alerts = self.process_event(event)
            all_alerts.extend(alerts)
        return all_alerts

    def _create_alert(self, rule: AlertRule, event: BusinessEvent) -> Alert:
        """创建预警实例"""
        import uuid

        # 确定优先级
        if event.severity == EventSeverity.CRITICAL:
            priority = AlertPriority.CRITICAL
        elif event.severity == EventSeverity.HIGH:
            priority = AlertPriority.HIGH
        elif event.severity == EventSeverity.MEDIUM:
            priority = AlertPriority.MEDIUM
        else:
            priority = AlertPriority.LOW

        # 生成消息
        message = f"[{rule.name}] {event.title}"
        if event.amount:
            amount_str = f"{event.amount/100000000:.2f}亿{event.currency}"
            message += f" - 金额：{amount_str}"
        if event.companies:
            message += f" - 涉及企业：{', '.join(event.companies[:3])}"

        alert = Alert(
            alert_id=str(uuid.uuid4()),
            rule_id=rule.rule_id,
            rule_name=rule.name,
            event=event,
            priority=priority,
            message=message
        )

        return alert

    def _trigger_alert(self, alert: Alert):
        """触发预警"""
        # 存储预警
        self.alerts[alert.alert_id] = alert

        # 更新规则统计
        if alert.rule_id in self.rules:
            rule = self.rules[alert.rule_id]
            rule.triggered_count += 1
            rule.last_triggered_at = datetime.now()

        # 发送通知
        self._send_notifications(alert)

        # 调用回调
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

        logger.info(f"Alert triggered: {alert.alert_id} - {alert.message}")

    def _send_notifications(self, alert: Alert):
        """发送通知"""
        # 获取规则
        rule = self.rules.get(alert.rule_id)
        if not rule:
            return

        # 发送到配置的渠道
        for channel in rule.notification_channels:
            handler = self.notification_handlers.get(channel)
            if handler:
                try:
                    handler(alert)
                except Exception as e:
                    logger.error(f"Notification handler error ({channel}): {e}")

    def register_notification_handler(self, channel: str, handler: Callable[[Alert], None]):
        """注册通知处理器"""
        self.notification_handlers[channel] = handler
        logger.info(f"Registered notification handler: {channel}")

    def register_alert_callback(self, callback: Callable[[Alert], None]):
        """注册预警回调"""
        self.alert_callbacks.append(callback)

    def get_alerts(
        self,
        status: Optional[AlertStatus] = None,
        priority: Optional[AlertPriority] = None,
        limit: int = 50
    ) -> List[Dict]:
        """获取预警列表"""
        results = []

        for alert in self.alerts.values():
            # 状态过滤
            if status and alert.status != status:
                continue

            # 优先级过滤
            if priority and alert.priority != priority:
                continue

            results.append(alert.to_dict())

            if len(results) >= limit:
                break

        return results

    def acknowledge_alert(self, alert_id: str, user: str = "system") -> bool:
        """确认预警"""
        if alert_id in self.alerts:
            self.alerts[alert_id].acknowledge(user)
            return True
        return False

    def resolve_alert(self, alert_id: str, notes: str = "") -> bool:
        """解决预警"""
        if alert_id in self.alerts:
            self.alerts[alert_id].resolve(notes)
            return True
        return False

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        # 按状态统计
        status_counts = defaultdict(int)
        for alert in self.alerts.values():
            status_counts[alert.status.value] += 1

        # 按优先级统计
        priority_counts = defaultdict(int)
        for alert in self.alerts.values():
            priority_counts[alert.priority.value] += 1

        # 按规则统计
        rule_counts = defaultdict(int)
        for alert in self.alerts.values():
            rule_counts[alert.rule_id] += 1

        return {
            "total_alerts": len(self.alerts),
            "by_status": dict(status_counts),
            "by_priority": dict(priority_counts),
            "by_rule": dict(rule_counts),
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules.values() if r.enabled)
        }

    def get_recent_alerts(self, hours: int = 24) -> List[Dict]:
        """获取最近的预警"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [
            alert.to_dict() for alert in self.alerts.values()
            if alert.created_at >= cutoff
        ]
        return recent[:50]


# 全局单例
alert_engine = AlertEngine()
