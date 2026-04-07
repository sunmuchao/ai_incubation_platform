"""
Grafana 集成模块

提供：
1. Prometheus 格式指标导出增强
2. Grafana 仪表板配置生成
3. Grafana 告警规则配置
"""
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import defaultdict

from models.monitoring import MetricModel
from config.database import db_manager
from utils.logger import logger


class GrafanaDashboardGenerator:
    """Grafana 仪表板生成器"""

    def __init__(self):
        self.dashboard_uid = "data-agent-connector"
        self.dashboard_title = "Data-Agent Connector Monitoring"

    def generate_dashboard_config(self) -> Dict[str, Any]:
        """生成 Grafana 仪表板配置"""
        dashboard = {
            "dashboard": {
                "id": None,
                "uid": self.dashboard_uid,
                "title": self.dashboard_title,
                "tags": ["data-agent-connector", "monitoring"],
                "timezone": "browser",
                "schemaVersion": 38,
                "version": 1,
                "refresh": "30s",
                "time": {
                    "from": "now-1h",
                    "to": "now"
                },
                "templating": {
                    "list": [
                        {
                            "name": "datasource",
                            "type": "datasource",
                            "query": "prometheus",
                            "current": {},
                            "hide": 0,
                            "label": "数据源",
                            "iconColor": "rgba(0, 211, 255, 1)"
                        },
                        {
                            "name": "connector",
                            "type": "query",
                            "datasource": "${datasource}",
                            "query": "label_values(query_total, datasource)",
                            "refresh": 2,
                            "regex": "",
                            "sort": 1,
                            "label": "连接器"
                        }
                    ]
                },
                "panels": self._generate_panels()
            },
            "overwrite": True,
            "folderId": 0,
            "message": "Updated by Data-Agent Connector"
        }

        return dashboard

    def _generate_panels(self) -> List[Dict[str, Any]]:
        """生成仪表板面板"""
        panels = []
        row_height = 8
        panel_width = 12

        # 第 1 行：系统概览
        panels.append(self._create_stat_panel(
            title="总查询数",
            targets=[{
                "expr": "sum(query_total)",
                "legendFormat": "Total Queries",
                "refId": "A"
            }],
            gridPos={"h": row_height, "w": panel_width, "x": 0, "y": 0}
        ))

        panels.append(self._create_stat_panel(
            title="平均延迟",
            targets=[{
                "expr": "avg(query_latency_ms_avg)",
                "legendFormat": "Avg Latency (ms)",
                "refId": "A"
            }],
            gridPos={"h": row_height, "w": panel_width, "x": panel_width, "y": 0},
            unit="ms"
        ))

        panels.append(self._create_stat_panel(
            title="活跃连接数",
            targets=[{
                "expr": "sum(connection_pool_active)",
                "legendFormat": "Active Connections",
                "refId": "A"
            }],
            gridPos={"h": row_height, "w": panel_width, "x": panel_width * 2, "y": 0}
        ))

        panels.append(self._create_stat_panel(
            title="连接池使用率",
            targets=[{
                "expr": "avg(connection_pool_usage) * 100",
                "legendFormat": "Pool Usage (%)",
                "refId": "A"
            }],
            gridPos={"h": row_height, "w": panel_width, "x": panel_width * 3, "y": 0},
            unit="percent"
        ))

        # 第 2 行：查询延迟趋势
        panels.append(self._create_graph_panel(
            title="查询延迟趋势",
            targets=[
                {
                    "expr": "query_latency_ms_avg{datasource=~\"$connector\"}",
                    "legendFormat": "{{datasource}} - Avg",
                    "refId": "A"
                },
                {
                    "expr": "query_latency_ms_p99{datasource=~\"$connector\"}",
                    "legendFormat": "{{datasource}} - P99",
                    "refId": "B"
                }
            ],
            gridPos={"h": row_height * 2, "w": panel_width * 2, "x": 0, "y": row_height},
            yAxes=[{"format": "ms", "label": "延迟 (ms)"}]
        ))

        # 第 3 行：QPS 趋势
        panels.append(self._create_graph_panel(
            title="QPS 趋势",
            targets=[
                {
                    "expr": "rate(query_total{datasource=~\"$connector\"}[5m])",
                    "legendFormat": "{{datasource}} QPS",
                    "refId": "A"
                }
            ],
            gridPos={"h": row_height * 2, "w": panel_width * 2, "x": panel_width * 2, "y": row_height},
            yAxes=[{"format": "qps", "label": "查询/秒"}]
        ))

        # 第 4 行：连接池监控
        panels.append(self._create_graph_panel(
            title="连接池状态",
            targets=[
                {
                    "expr": "connection_pool_active{datasource=~\"$connector\"}",
                    "legendFormat": "{{datasource}} - Active",
                    "refId": "A"
                },
                {
                    "expr": "connection_pool_max{datasource=~\"$connector\"}",
                    "legendFormat": "{{datasource}} - Max",
                    "refId": "B"
                },
                {
                    "expr": "connection_pool_usage{datasource=~\"$connector\"} * 100",
                    "legendFormat": "{{datasource}} - Usage %",
                    "refId": "C"
                }
            ],
            gridPos={"h": row_height * 2, "w": panel_width * 2, "x": 0, "y": row_height * 3},
            yAxes=[{"format": "short", "label": "连接数"}]
        ))

        # 第 5 行：限流监控
        panels.append(self._create_graph_panel(
            title="限流监控",
            targets=[
                {
                    "expr": "rate_limit_triggered_total",
                    "legendFormat": "Triggered Count",
                    "refId": "A"
                },
                {
                    "expr": "concurrent_queries",
                    "legendFormat": "Concurrent Queries",
                    "refId": "B"
                }
            ],
            gridPos={"h": row_height * 2, "w": panel_width * 2, "x": panel_width * 2, "y": row_height * 3}
        ))

        # 第 6 行：血缘统计
        panels.append(self._create_graph_panel(
            title="数据血缘统计",
            targets=[
                {
                    "expr": "lineage_nodes_total",
                    "legendFormat": "Total Nodes",
                    "refId": "A"
                },
                {
                    "expr": "lineage_edges_total",
                    "legendFormat": "Total Edges",
                    "refId": "B"
                }
            ],
            gridPos={"h": row_height * 2, "w": panel_width * 2, "x": 0, "y": row_height * 5}
        ))

        # 第 7 行：系统健康
        panels.append(self._create_stat_panel(
            title="系统健康状态",
            targets=[{
                "expr": "system_health_status",
                "legendFormat": "Status",
                "refId": "A"
            }],
            gridPos={"h": row_height, "w": panel_width, "x": 0, "y": row_height * 7},
            thresholds=[
                {"value": 0, "color": "red", "state": "alert"},
                {"value": 1, "color": "green", "state": "ok"}
            ]
        ))

        panels.append(self._create_stat_panel(
            title="错误率",
            targets=[{
                "expr": "error_rate * 100",
                "legendFormat": "Error Rate (%)",
                "refId": "A"
            }],
            gridPos={"h": row_height, "w": panel_width, "x": panel_width, "y": row_height * 7},
            unit="percent",
            thresholds=[
                {"value": 0, "color": "green"},
                {"value": 1, "color": "yellow"},
                {"value": 5, "color": "red"}
            ]
        ))

        panels.append(self._create_stat_panel(
            title="当前并发数",
            targets=[{
                "expr": "concurrent_queries",
                "legendFormat": "Concurrent",
                "refId": "A"
            }],
            gridPos={"h": row_height, "w": panel_width, "x": panel_width * 2, "y": row_height * 7}
        ))

        return panels

    def _create_stat_panel(self, title: str, targets: List[Dict],
                           gridPos: Dict, unit: str = "short",
                           thresholds: List[Dict] = None) -> Dict[str, Any]:
        """创建统计面板"""
        return {
            "id": None,
            "type": "stat",
            "title": title,
            "gridPos": gridPos,
            "targets": targets,
            "datasource": "${datasource}",
            "fieldConfig": {
                "defaults": {
                    "unit": unit,
                    "thresholds": {
                        "mode": "absolute",
                        "steps": thresholds or [
                            {"value": 0, "color": "green"},
                            {"value": 80, "color": "yellow"},
                            {"value": 100, "color": "red"}
                        ]
                    },
                    "color": {
                        "mode": "thresholds"
                    }
                }
            },
            "options": {
                "colorMode": "value",
                "graphMode": "area",
                "justifyMode": "auto",
                "textMode": "auto"
            }
        }

    def _create_graph_panel(self, title: str, targets: List[Dict],
                            gridPos: Dict, yAxes: List[Dict] = None) -> Dict[str, Any]:
        """创建图表面板"""
        return {
            "id": None,
            "type": "timeseries",
            "title": title,
            "gridPos": gridPos,
            "targets": targets,
            "datasource": "${datasource}",
            "options": {
                "legend": {
                    "displayMode": "table",
                    "placement": "bottom",
                    "showLegend": True
                },
                "tooltip": {
                    "mode": "multi",
                    "sort": "desc"
                }
            },
            "yAxes": yAxes or [{"format": "short"}]
        }

    def export_dashboard_json(self, filepath: str = None) -> str:
        """导出仪表板配置为 JSON"""
        dashboard = self.generate_dashboard_config()
        json_str = json.dumps(dashboard, indent=2, ensure_ascii=False)

        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(json_str)
            logger.info(f"Exported Grafana dashboard to {filepath}")

        return json_str

    def generate_alert_rules(self) -> List[Dict[str, Any]]:
        """生成 Grafana 告警规则配置"""
        return [
            {
                "name": "High Query Latency",
                "condition": {
                    "evaluator": {"params": [500], "type": "gt"},
                    "operator": {"type": "and"},
                    "query": {"params": ["A", "5m", "now"]},
                    "reducer": {"params": [], "type": "avg"},
                    "type": "query"
                },
                "executionErrorState": "alerting",
                "frequency": "1m",
                "handler": 1,
                "message": "查询平均延迟超过 500ms",
                "noDataState": "no_data",
                "notifications": []
            },
            {
                "name": "High Connection Pool Usage",
                "condition": {
                    "evaluator": {"params": [80], "type": "gt"},
                    "operator": {"type": "and"},
                    "query": {"params": ["A", "5m", "now"]},
                    "reducer": {"params": [], "type": "avg"},
                    "type": "query"
                },
                "executionErrorState": "alerting",
                "frequency": "1m",
                "handler": 1,
                "message": "连接池使用率超过 80%",
                "noDataState": "no_data",
                "notifications": []
            },
            {
                "name": "High Error Rate",
                "condition": {
                    "evaluator": {"params": [5], "type": "gt"},
                    "operator": {"type": "and"},
                    "query": {"params": ["A", "5m", "now"]},
                    "reducer": {"params": [], "type": "avg"},
                    "type": "query"
                },
                "executionErrorState": "alerting",
                "frequency": "1m",
                "handler": 1,
                "message": "错误率超过 5%",
                "noDataState": "no_data",
                "notifications": []
            }
        ]


class PrometheusMetricsExporter:
    """Prometheus 指标导出器（增强版）"""

    def __init__(self):
        self.metric_families = defaultdict(list)

    async def generate_prometheus_metrics(self) -> str:
        """生成 Prometheus 格式的指标"""
        lines = []
        async with db_manager.get_async_session() as session:
            from sqlalchemy import select, desc
            from datetime import timedelta

            # 获取最近 1 小时的指标
            cutoff_time = datetime.utcnow() - timedelta(hours=1)

            # 获取所有唯一的指标名称
            result = await session.execute(
                select(MetricModel.name).distinct()
            )
            metric_names = [row[0] for row in result.scalars().all()]

            for metric_name in metric_names:
                # 获取该指标的最新数据
                result = await session.execute(
                    select(MetricModel)
                    .where(MetricModel.name == metric_name)
                    .where(MetricModel.timestamp >= cutoff_time)
                    .order_by(desc(MetricModel.timestamp))
                    .limit(100)
                )
                metrics = result.scalars().all()

                if not metrics:
                    continue

                # 确定指标类型
                metric_type = self._infer_metric_type(metric_name)

                # 生成 HELP 和 TYPE 注释
                lines.append(f"# HELP {metric_name} Data-Agent Connector metric")
                lines.append(f"# TYPE {metric_name} {metric_type}")

                # 按标签分组
                metrics_by_labels = defaultdict(list)
                for m in metrics:
                    label_key = tuple(sorted((m.labels or {}).items()))
                    metrics_by_labels[label_key].append(m)

                # 为每组标签生成指标
                for labels, group in metrics_by_labels.items():
                    label_str = self._format_labels(labels)

                    # 对于 counter 类型，使用最新值
                    # 对于 gauge 类型，使用最新值
                    latest = max(group, key=lambda x: x.timestamp)
                    value = latest.value
                    timestamp_ms = int(latest.timestamp.timestamp() * 1000)

                    lines.append(f"{metric_name}{label_str} {value} {timestamp_ms}")

        return "\n".join(lines)

    def _infer_metric_type(self, metric_name: str) -> str:
        """根据指标名称推断指标类型"""
        counter_keywords = ["total", "count", "sum"]
        histogram_keywords = ["bucket", "histogram"]

        if any(kw in metric_name for kw in histogram_keywords):
            return "histogram"
        elif any(kw in metric_name for kw in counter_keywords):
            return "counter"
        else:
            return "gauge"

    def _format_labels(self, labels: tuple) -> str:
        """格式化标签字符串"""
        if not labels:
            return ""

        label_parts = []
        for key, value in labels:
            # 转义标签值
            escaped_value = str(value).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            label_parts.append(f'{key}="{escaped_value}"')

        return "{" + ",".join(label_parts) + "}"

    async def get_metrics_for_prometheus(self) -> Dict[str, Any]:
        """获取用于 Prometheus 的指标数据"""
        async with db_manager.get_async_session() as session:
            from sqlalchemy import select, desc, func
            from datetime import timedelta

            cutoff_time = datetime.utcnow() - timedelta(hours=1)

            result = await session.execute(
                select(
                    MetricModel.name,
                    MetricModel.metric_type,
                    func.avg(MetricModel.value).label('avg_value'),
                    func.max(MetricModel.value).label('max_value'),
                    func.min(MetricModel.value).label('min_value'),
                    func.count(MetricModel.id).label('sample_count')
                )
                .where(MetricModel.timestamp >= cutoff_time)
                .group_by(MetricModel.name, MetricModel.metric_type)
            )

            metrics_summary = []
            for row in result.all():
                metrics_summary.append({
                    "name": row.name,
                    "type": row.metric_type,
                    "avg_value": row.avg_value,
                    "max_value": row.max_value,
                    "min_value": row.min_value,
                    "sample_count": row.sample_count
                })

            return {"metrics": metrics_summary}


# 全局实例
grafana_generator = GrafanaDashboardGenerator()
prometheus_exporter = PrometheusMetricsExporter()


def export_grafana_dashboard(filepath: str = "grafana_dashboard.json"):
    """导出 Grafana 仪表板配置"""
    return grafana_generator.export_dashboard_json(filepath)


def generate_grafana_alert_rules() -> List[Dict[str, Any]]:
    """生成 Grafana 告警规则"""
    return grafana_generator.generate_alert_rules()
