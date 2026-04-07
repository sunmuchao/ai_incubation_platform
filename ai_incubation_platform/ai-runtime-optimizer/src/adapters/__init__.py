"""
适配器包
提供Prometheus、OpenTelemetry、网关日志等外部系统的适配能力
"""

from .metrics.prometheus import PrometheusAdapter, PrometheusAdapterConfig
from .metrics.opentelemetry import OpenTelemetryAdapter, OpenTelemetryAdapterConfig
from .logs.gateway_log import GatewayLogAdapter, GatewayLogConfig, GatewayLogEntry

__all__ = [
    "PrometheusAdapter",
    "PrometheusAdapterConfig",
    "OpenTelemetryAdapter",
    "OpenTelemetryAdapterConfig",
    "GatewayLogAdapter",
    "GatewayLogConfig",
    "GatewayLogEntry"
]
