"""
监控告警服务

实现：
1. 指标采集和存储
2. 告警规则检查
3. 告警通知发送（邮件、钉钉、企业微信、Slack）
4. Prometheus 指标导出
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from collections import defaultdict
import aiohttp
import json

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.monitoring import MetricModel, AlertRuleModel, AlertModel, SystemHealthModel
from config.database import db_manager
from utils.logger import logger
from config.settings import settings


class MetricsCollector:
    """指标采集器"""

    def __init__(self):
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def inc_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None, datasource: str = None):
        """增加计数器"""
        async with self._lock:
            key = self._make_key(name, labels)
            self._counters[key] += value

            # 持久化到数据库
            await self._persist_metric(
                name=name,
                value=self._counters[key],
                metric_type="counter",
                labels=labels,
                datasource=datasource
            )

    async def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None, datasource: str = None):
        """设置仪表盘值"""
        async with self._lock:
            key = self._make_key(name, labels)
            self._gauges[key] = value

            # 持久化到数据库
            await self._persist_metric(
                name=name,
                value=value,
                metric_type="gauge",
                labels=labels,
                datasource=datasource
            )

    async def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None, datasource: str = None):
        """观察直方图值"""
        async with self._lock:
            key = self._make_key(name, labels)
            self._histograms[key].append(value)

            # 保留最近 1000 个值
            if len(self._histograms[key]) > 1000:
                self._histograms[key] = self._histograms[key][-1000:]

            # 计算百分位数并持久化
            values = self._histograms[key]
            await self._persist_metric(
                name=f"{name}_count",
                value=len(values),
                metric_type="gauge",
                labels=labels,
                datasource=datasource
            )
            await self._persist_metric(
                name=f"{name}_sum",
                value=sum(values),
                metric_type="gauge",
                labels=labels,
                datasource=datasource
            )
            await self._persist_metric(
                name=f"{name}_avg",
                value=sum(values) / len(values) if values else 0,
                metric_type="gauge",
                labels=labels,
                datasource=datasource
            )

    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """生成指标键"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    async def _persist_metric(self, name: str, value: float, metric_type: str, labels: Dict[str, str] = None, datasource: str = None):
        """持久化指标到数据库"""
        try:
            async with db_manager.get_async_session() as session:
                metric = MetricModel(
                    name=name,
                    value=value,
                    metric_type=metric_type,
                    labels=labels or {},
                    datasource=datasource
                )
                session.add(metric)
                await session.flush()
        except Exception as e:
            logger.debug(f"Failed to persist metric {name}: {e}")

    async def get_metrics(self, name: Optional[str] = None, hours: int = 1) -> List[Dict[str, Any]]:
        """获取指标数据"""
        async with db_manager.get_async_session() as session:
            query = select(MetricModel).where(
                MetricModel.timestamp >= datetime.utcnow() - timedelta(hours=hours)
            )
            if name:
                query = query.where(MetricModel.name == name)
            query = query.order_by(desc(MetricModel.timestamp))

            result = await session.execute(query)
            metrics = result.scalars().all()
            return [m.to_dict() for m in metrics]

    async def get_latest_metrics(self, name: str) -> Dict[str, Any]:
        """获取最新指标值"""
        async with db_manager.get_async_session() as session:
            result = await session.execute(
                select(MetricModel)
                .where(MetricModel.name == name)
                .order_by(desc(MetricModel.timestamp))
                .limit(1)
            )
            metric = result.scalar_one_or_none()
            return metric.to_dict() if metric else None


class AlertManager:
    """告警管理器"""

    def __init__(self, metrics_collector: MetricsCollector):
        self._metrics_collector = metrics_collector
        self._alert_start_times: Dict[str, datetime] = {}  # 告警开始时间
        self._notification_cooldown: Dict[str, datetime] = {}  # 通知冷却时间
        self._cooldown_seconds = 300  # 5 分钟冷却时间

    async def check_rules(self) -> List[AlertModel]:
        """检查所有告警规则"""
        async with db_manager.get_async_session() as session:
            # 获取所有启用的规则
            result = await session.execute(
                select(AlertRuleModel).where(
                    and_(
                        AlertRuleModel.enabled == True,
                        AlertRuleModel.silenced == False
                    )
                )
            )
            rules = result.scalars().all()

            fired_alerts = []

            for rule in rules:
                # 获取当前指标值
                current_value = await self._get_current_metric_value(rule.metric_name)

                if current_value is None:
                    continue

                # 检查是否触发告警
                is_firing = self._evaluate_rule(rule, current_value)

                if is_firing:
                    # 检查持续时间
                    should_alert = await self._check_duration(rule, current_value)

                    if should_alert:
                        # 创建或更新告警
                        alert = await self._create_or_update_alert(rule, current_value)
                        fired_alerts.append(alert)

                        # 发送通知
                        await self._send_notifications(rule, alert)
                else:
                    # 告警恢复
                    await self._resolve_alert(rule, current_value)

            return fired_alerts

    async def _get_current_metric_value(self, metric_name: str) -> Optional[float]:
        """获取当前指标值"""
        try:
            metric = await self._metrics_collector.get_latest_metrics(metric_name)
            return metric.get("value") if metric else None
        except Exception as e:
            logger.error(f"Failed to get metric value for {metric_name}: {e}")
            return None

    def _evaluate_rule(self, rule: AlertRuleModel, value: float) -> bool:
        """评估告警规则"""
        operators = {
            ">": lambda x, y: x > y,
            "<": lambda x, y: x < y,
            ">=": lambda x, y: x >= y,
            "<=": lambda x, y: x <= y,
            "==": lambda x, y: x == y,
            "!=": lambda x, y: x != y,
        }
        op_func = operators.get(rule.operator)
        if op_func:
            return op_func(value, rule.threshold)
        return False

    async def _check_duration(self, rule: AlertRuleModel, value: float) -> bool:
        """检查告警持续时间"""
        key = f"{rule.id}:{rule.metric_name}"

        if value >= rule.threshold if rule.operator in [">", ">="] else value <= rule.threshold:
            if key not in self._alert_start_times:
                self._alert_start_times[key] = datetime.utcnow()

            duration = (datetime.utcnow() - self._alert_start_times[key]).total_seconds()
            return duration >= rule.duration_seconds
        else:
            if key in self._alert_start_times:
                del self._alert_start_times[key]
            return False

    async def _create_or_update_alert(self, rule: AlertRuleModel, value: float) -> AlertModel:
        """创建或更新告警"""
        async with db_manager.get_async_session() as session:
            # 检查是否有未解决的告警
            result = await session.execute(
                select(AlertModel).where(
                    and_(
                        AlertModel.rule_id == rule.id,
                        AlertModel.status == "firing"
                    )
                ).order_by(desc(AlertModel.fired_at)).limit(1)
            )
            existing = result.scalar_one_or_none()

            if existing:
                # 更新现有告警
                existing.metric_value = value
                existing.last_notification_at = datetime.utcnow()
                await session.flush()
                return existing
            else:
                # 创建新告警
                alert = AlertModel(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    metric_name=rule.metric_name,
                    metric_value=value,
                    threshold=rule.threshold,
                    operator=rule.operator,
                    severity=rule.severity,
                    status="firing",
                    message=f"告警：{rule.name} - 当前值 {value} {rule.operator} {rule.threshold}"
                )
                session.add(alert)
                await session.flush()
                return alert

    async def _resolve_alert(self, rule: AlertRuleModel, value: float):
        """恢复告警"""
        async with db_manager.get_async_session() as session:
            result = await session.execute(
                select(AlertModel).where(
                    and_(
                        AlertModel.rule_id == rule.id,
                        AlertModel.status == "firing"
                    )
                )
            )
            alerts = result.scalars().all()

            for alert in alerts:
                alert.status = "resolved"
                alert.resolved_at = datetime.utcnow()
                alert.message = f"告警已恢复：{rule.name} - 当前值 {value}"

            await session.flush()

        # 清理告警开始时间
        key = f"{rule.id}:{rule.metric_name}"
        if key in self._alert_start_times:
            del self._alert_start_times[key]

    async def _send_notifications(self, rule: AlertRuleModel, alert: AlertModel):
        """发送告警通知"""
        # 检查冷却时间
        cooldown_key = f"{rule.id}:{alert.id}"
        if cooldown_key in self._notification_cooldown:
            if datetime.utcnow() - self._notification_cooldown[cooldown_key] < timedelta(seconds=self._cooldown_seconds):
                return

        # 更新冷却时间
        self._notification_cooldown[cooldown_key] = datetime.utcnow()

        # 发送通知
        for channel in rule.notify_channels or []:
            try:
                if channel == "dingtalk":
                    await self._send_dingtalk_notification(rule, alert)
                elif channel == "wechat":
                    await self._send_wechat_notification(rule, alert)
                elif channel == "slack":
                    await self._send_slack_notification(rule, alert)
                elif channel == "email":
                    await self._send_email_notification(rule, alert)
            except Exception as e:
                logger.error(f"Failed to send notification via {channel}: {e}")

        # 更新通知计数
        async with db_manager.get_async_session() as session:
            alert.notifications_sent += 1
            alert.last_notification_at = datetime.utcnow()
            await session.flush()

    async def _send_dingtalk_notification(self, rule: AlertRuleModel, alert: AlertModel):
        """发送钉钉通知"""
        webhook_url = settings.lineage.db_host  # 从配置获取，需要更新
        if not webhook_url:
            logger.warning("DingTalk webhook URL not configured")
            return

        message = {
            "msgtype": "markdown",
            "markdown": {
                "title": f"告警通知 - {rule.name}",
                "text": f"""## 告警通知
- **告警名称**: {rule.name}
- **告警级别**: {alert.severity}
- **指标名称**: {alert.metric_name}
- **当前值**: {alert.metric_value}
- **阈值**: {rule.threshold} {rule.operator}
- **触发时间**: {alert.fired_at.strftime('%Y-%m-%d %H:%M:%S')}
- **告警状态**: {alert.status}
"""
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=message) as response:
                if response.status == 200:
                    logger.info("DingTalk notification sent successfully")
                else:
                    logger.error(f"DingTalk notification failed: {response.status}")

    async def _send_wechat_notification(self, rule: AlertRuleModel, alert: AlertModel):
        """发送企业微信通知"""
        webhook_url = settings.lineage.db_path  # 从配置获取，需要更新
        if not webhook_url:
            logger.warning("WeChat webhook URL not configured")
            return

        message = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"""## 告警通知
- **告警名称**: {rule.name}
- **告警级别**: {alert.severity}
- **指标名称**: {alert.metric_name}
- **当前值**: {alert.metric_value}
- **阈值**: {rule.threshold} {rule.operator}
- **触发时间**: {alert.fired_at.strftime('%Y-%m-%d %H:%M:%S')}
- **告警状态**: {alert.status}
"""
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=message) as response:
                if response.status == 200:
                    logger.info("WeChat notification sent successfully")
                else:
                    logger.error(f"WeChat notification failed: {response.status}")

    async def _send_slack_notification(self, rule: AlertRuleModel, alert: AlertModel):
        """发送 Slack 通知"""
        webhook_url = settings.lineage.db_host  # 从配置获取，需要更新
        if not webhook_url:
            logger.warning("Slack webhook URL not configured")
            return

        color_map = {
            "info": "#36a64f",
            "warning": "#ffcc00",
            "error": "#ff6600",
            "critical": "#ff0000"
        }

        message = {
            "attachments": [
                {
                    "color": color_map.get(alert.severity, "#ffcc00"),
                    "title": f"告警通知 - {rule.name}",
                    "fields": [
                        {"title": "告警级别", "value": alert.severity, "short": True},
                        {"title": "指标名称", "value": alert.metric_name, "short": True},
                        {"title": "当前值", "value": str(alert.metric_value), "short": True},
                        {"title": "阈值", "value": f"{rule.threshold} {rule.operator}", "short": True},
                        {"title": "触发时间", "value": alert.fired_at.strftime('%Y-%m-%d %H:%M:%S'), "short": True},
                        {"title": "告警状态", "value": alert.status, "short": True},
                    ],
                    "footer": "Data-Agent Connector Monitoring",
                    "ts": int(alert.fired_at.timestamp())
                }
            ]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=message) as response:
                if response.status == 200:
                    logger.info("Slack notification sent successfully")
                else:
                    logger.error(f"Slack notification failed: {response.status}")

    async def _send_email_notification(self, rule: AlertRuleModel, alert: AlertModel):
        """发送邮件通知"""
        # 这里需要集成邮件发送服务
        logger.info(f"Email notification would be sent for alert: {alert.message}")


class PrometheusExporter:
    """Prometheus 指标导出器"""

    def __init__(self, metrics_collector: MetricsCollector):
        self._metrics_collector = metrics_collector

    async def generate_prometheus_metrics(self) -> str:
        """生成 Prometheus 格式的指标"""
        lines = []

        # 获取所有指标
        metrics = await self._metrics_collector.get_metrics(hours=1)

        # 按名称分组
        metrics_by_name = defaultdict(list)
        for metric in metrics:
            metrics_by_name[metric["name"]].append(metric)

        for name, metric_list in metrics_by_name.items():
            # 获取最新值
            latest = max(metric_list, key=lambda x: x["timestamp"])

            # 生成 Prometheus 格式
            metric_type = latest.get("metric_type", "gauge")
            prom_type = {
                "counter": "counter",
                "gauge": "gauge",
                "histogram": "histogram"
            }.get(metric_type, "gauge")

            lines.append(f"# HELP {name} Metric exported by Data-Agent Connector")
            lines.append(f"# TYPE {name} {prom_type}")

            value = latest.get("value", 0)
            labels = latest.get("labels", {})
            timestamp = int(datetime.fromisoformat(latest["timestamp"]).timestamp() * 1000)

            if labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
                lines.append(f"{name}{{{label_str}}} {value} {timestamp}")
            else:
                lines.append(f"{name} {value} {timestamp}")

        return "\n".join(lines)


class MonitoringService:
    """监控服务主类"""

    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager(self.metrics_collector)
        self.prometheus_exporter = PrometheusExporter(self.metrics_collector)
        self._check_interval = 30  # 秒
        self._running = False
        self._check_task = None

    async def start(self):
        """启动监控服务"""
        self._running = True
        self._check_task = asyncio.create_task(self._check_loop())
        logger.info("Monitoring service started")

    async def stop(self):
        """停止监控服务"""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        logger.info("Monitoring service stopped")

    async def _check_loop(self):
        """定期检查告警规则"""
        while self._running:
            try:
                await self.alert_manager.check_rules()
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring check loop: {e}")
                await asyncio.sleep(self._check_interval)

    # 快捷方法用于记录指标
    async def record_query(self, datasource: str, latency_ms: float, success: bool = True):
        """记录查询指标"""
        await self.metrics_collector.inc_counter(
            name="query_total",
            labels={"datasource": datasource, "success": str(success)}
        )
        await self.metrics_collector.observe_histogram(
            name="query_latency_ms",
            value=latency_ms,
            labels={"datasource": datasource}
        )

    async def record_connection(self, datasource: str, active: int, max_conn: int):
        """记录连接池指标"""
        usage = active / max_conn if max_conn > 0 else 0
        await self.metrics_collector.set_gauge(
            name="connection_pool_active",
            value=active,
            labels={"datasource": datasource}
        )
        await self.metrics_collector.set_gauge(
            name="connection_pool_usage",
            value=usage,
            labels={"datasource": datasource}
        )

    async def record_rate_limit(self, triggered: bool = False, current_concurrent: int = 0):
        """记录限流指标"""
        if triggered:
            await self.metrics_collector.inc_counter(name="rate_limit_triggered_total")
        await self.metrics_collector.set_gauge(name="concurrent_queries", value=current_concurrent)

    async def record_lineage(self, nodes: int, edges: int):
        """记录血缘指标"""
        await self.metrics_collector.set_gauge(name="lineage_nodes_total", value=nodes)
        await self.metrics_collector.set_gauge(name="lineage_edges_total", value=edges)

    async def record_system_health(self, health_data: Dict[str, Any]):
        """记录系统健康状态"""
        async with db_manager.get_async_session() as session:
            snapshot = SystemHealthModel(
                status=health_data.get("status", "healthy"),
                active_connections=health_data.get("active_connections", 0),
                max_connections=health_data.get("max_connections", 100),
                connection_pool_usage=health_data.get("connection_pool_usage", 0),
                current_qps=health_data.get("current_qps", 0),
                avg_latency_ms=health_data.get("avg_latency_ms", 0),
                p99_latency_ms=health_data.get("p99_latency_ms", 0),
                error_rate=health_data.get("error_rate", 0),
                rate_limit_enabled=health_data.get("rate_limit_enabled", True),
                rate_limit_triggered=health_data.get("rate_limit_triggered", 0),
                current_concurrent=health_data.get("current_concurrent", 0),
                total_lineage_nodes=health_data.get("total_lineage_nodes", 0),
                total_lineage_edges=health_data.get("total_lineage_edges", 0)
            )
            session.add(snapshot)
            await session.flush()

    async def get_metrics_dashboard(self) -> Dict[str, Any]:
        """获取监控大盘数据"""
        # 获取最近的指标
        query_latency = await self.metrics_collector.get_metrics(name="query_latency_ms_avg", hours=1)
        query_total = await self.metrics_collector.get_metrics(name="query_total", hours=1)

        # 计算统计
        latency_values = [m["value"] for m in query_latency]
        avg_latency = sum(latency_values) / len(latency_values) if latency_values else 0
        p99_latency = sorted(latency_values)[int(len(latency_values) * 0.99)] if latency_values else 0

        return {
            "query_metrics": {
                "total_queries": sum(m["value"] for m in query_total) if query_total else 0,
                "avg_latency_ms": avg_latency,
                "p99_latency_ms": p99_latency
            },
            "system_status": "healthy"
        }


# 全局监控服务实例
monitoring_service = MonitoringService()
