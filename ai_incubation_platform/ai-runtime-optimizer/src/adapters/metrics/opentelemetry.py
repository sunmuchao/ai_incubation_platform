"""
OpenTelemetry 指标适配器
从OpenTelemetry Collector查询并转换为优化器统一的指标格式
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import requests
from datetime import datetime, timedelta
from models.analysis import MetricsSnapshot, RouteUsageStat, UsageSummary


class OpenTelemetryAdapterConfig(BaseModel):
    """OpenTelemetry适配器配置"""
    otel_collector_url: str = Field("http://localhost:4318", description="OTel Collector HTTP端点")
    prometheus_backend_url: Optional[str] = Field(None, description="Prometheus查询端点(如果使用Prometheus作为存储)")
    service_name_attr: str = Field("service.name", description="服务名属性名")
    route_attr: str = Field("http.route", description="路由属性名")
    status_code_attr: str = Field("http.status_code", description="状态码属性名")


class OpenTelemetryAdapter:
    """OpenTelemetry指标与追踪适配器"""

    def __init__(self, config: Optional[OpenTelemetryAdapterConfig] = None):
        self.config = config or OpenTelemetryAdapterConfig()
        # 如果配置了Prometheus后端，则复用Prometheus适配器查询指标
        self._prometheus_adapter = None
        if self.config.prometheus_backend_url:
            from .prometheus import PrometheusAdapter, PrometheusAdapterConfig
            self._prometheus_adapter = PrometheusAdapter(
                PrometheusAdapterConfig(url=self.config.prometheus_backend_url)
            )

    def get_service_metrics(
        self,
        service_name: str,
        lookback_minutes: int = 5
    ) -> MetricsSnapshot:
        """获取服务指标快照"""
        if self._prometheus_adapter:
            return self._prometheus_adapter.get_service_metrics(service_name, lookback_minutes)

        # 直接从OTel Collector查询指标的实现
        # 这里简化实现，实际生产环境需要对接OTel的Metrics API
        raise NotImplementedError(
            "Direct OTel Collector query not implemented. "
            "Please configure prometheus_backend_url to use Prometheus as storage backend."
        )

    def get_usage_summary(
        self,
        service_name: str,
        lookback_minutes: int = 60 * 24  # 默认24小时
    ) -> UsageSummary:
        """获取用户使用情况汇总"""
        if not self._prometheus_adapter:
            raise NotImplementedError(
                "Usage summary requires Prometheus backend. "
                "Please configure prometheus_backend_url."
            )

        end_time = datetime.utcnow()

        # 查询路由级指标
        routes_query = (
            f'sum by(http_route) (rate(http_server_duration_count{{service_name="{service_name}"}}[{lookback_minutes}m]))'
        )
        routes_result = self._prometheus_adapter._query_prometheus(routes_query, end_time)

        top_routes = []
        for route_data in routes_result.get("data", {}).get("result", []):
            route = route_data.get("metric", {}).get("http_route")
            if not route or route == "":
                continue

            requests = float(route_data.get("value", [0, 0])[1]) * lookback_minutes * 60

            # 查询路由P99延迟
            latency_query = (
                f'histogram_quantile(0.99, sum by(le) (rate(http_server_duration_bucket'
                f'{{service_name="{service_name}", http_route="{route}"}}[{lookback_minutes}m])))'
            )
            latency_result = self._prometheus_adapter._query_prometheus(latency_query, end_time)
            latency_seconds = self._prometheus_adapter._extract_scalar_value(latency_result)
            p99_ms = latency_seconds * 1000 if latency_seconds else None

            # 查询路由错误率
            total_query = f'sum(rate(http_server_duration_count{{service_name="{service_name}", http_route="{route}"}}[{lookback_minutes}m]))'
            error_query = f'sum(rate(http_server_duration_count{{service_name="{service_name}", http_route="{route}", http_status_code=~"5..|4.."}}[{lookback_minutes}m]))'

            total_result = self._prometheus_adapter._query_prometheus(total_query, end_time)
            total = self._prometheus_adapter._extract_scalar_value(total_result) or 0

            error_result = self._prometheus_adapter._query_prometheus(error_query, end_time)
            errors = self._prometheus_adapter._extract_scalar_value(error_result) or 0

            error_rate = errors / total if total > 0 else 0.0

            top_routes.append(RouteUsageStat(
                path=route,
                requests=int(requests),
                p99_ms=p99_ms,
                error_rate=error_rate
            ))

        # 按请求量排序，取前20个
        top_routes.sort(key=lambda x: x.requests, reverse=True)
        top_routes = top_routes[:20]

        return UsageSummary(
            service_name=service_name,
            period=f"{lookback_minutes//60}h" if lookback_minutes >= 60 else f"{lookback_minutes}m",
            top_routes=top_routes,
            notes="Data collected from OpenTelemetry metrics"
        )

    def get_trace_summaries(
        self,
        service_name: str,
        lookback_minutes: int = 60,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取追踪摘要（用于异常分析）"""
        # 简化实现，实际需要对接OTel Collector的Trace API或Jaeger/zipkin
        return [
            {
                "trace_id": "example-trace-id",
                "span_id": "example-span-id",
                "name": "example-operation",
                "duration_ms": 123,
                "status": "OK",
                "attributes": {}
            }
        ]
