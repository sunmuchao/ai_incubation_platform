"""
指标适配器
提供Prometheus、OpenTelemetry等指标源的接入能力
"""

from .prometheus import PrometheusAdapter, PrometheusAdapterConfig
from .opentelemetry import OpenTelemetryAdapter, OpenTelemetryAdapterConfig

__all__ = [
    "PrometheusAdapter",
    "PrometheusAdapterConfig",
    "OpenTelemetryAdapter",
    "OpenTelemetryAdapterConfig"
]
