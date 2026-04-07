"""
自动数据采集器
实现 Prometheus/OpenTelemetry 指标的自动拉取和批量采集
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import threading
import time

from .prometheus import PrometheusAdapter, PrometheusAdapterConfig
from .opentelemetry import OpenTelemetryAdapter, OpenTelemetryAdapterConfig
from models.analysis import MetricsSnapshot

logger = logging.getLogger(__name__)


class CollectorSource(str, Enum):
    """数据源类型"""
    PROMETHEUS = "prometheus"
    OPENTELEMETRY = "opentelemetry"
    MANUAL = "manual"


@dataclass
class ServiceDiscoveryConfig:
    """服务发现配置"""
    enabled: bool = True
    prometheus_label: str = "job"
    allow_list: Optional[List[str]] = None  # 允许的服务列表，None 表示全部
    deny_list: Optional[List[str]] = None  # 拒绝的服务列表
    refresh_interval_seconds: int = 300  # 服务列表刷新间隔


@dataclass
class AutoCollectorConfig:
    """自动采集器配置"""
    # Prometheus 配置
    prometheus_url: str = "http://localhost:9090"
    prometheus_enabled: bool = True

    # OpenTelemetry 配置
    otel_collector_url: str = "http://localhost:4318"
    otel_enabled: bool = False

    # 采集配置
    scrape_interval_seconds: int = 15  # 采集间隔
    lookback_minutes: int = 5  # 回溯时间
    batch_size: int = 100  # 批量大小

    # 服务发现配置
    service_discovery: ServiceDiscoveryConfig = field(default_factory=ServiceDiscoveryConfig)

    # 指标过滤
    metrics_to_collect: List[str] = field(default_factory=lambda: [
        "cpu_percent",
        "memory_mb",
        "latency_p99_ms",
        "error_rate",
        "requests_per_second"
    ])


@dataclass
class CollectedMetrics:
    """采集的指标数据"""
    service_name: str
    timestamp: datetime
    metrics: Dict[str, Any]
    source: CollectorSource
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ServiceDiscovery:
    """服务发现组件"""

    def __init__(self, config: ServiceDiscoveryConfig, prometheus_adapter: PrometheusAdapter):
        self.config = config
        self.prometheus_adapter = prometheus_adapter
        self._discovered_services: Set[str] = set()
        self._last_refresh: Optional[datetime] = None
        self._lock = threading.Lock()

    def discover_services(self) -> Set[str]:
        """发现服务列表"""
        now = datetime.utcnow()

        # 检查是否需要刷新
        if self._last_refresh:
            elapsed = (now - self._last_refresh).total_seconds()
            if elapsed < self.config.refresh_interval_seconds:
                with self._lock:
                    return self._discovered_services.copy()

        try:
            # 查询 Prometheus 获取服务列表
            query = f'label_values({self.config.prometheus_label})'
            result = self.prometheus_adapter._query_prometheus(query)

            services = set()
            for data in result.get("data", {}).get("result", []):
                service = data.get("metric", {}).get(self.config.prometheus_label, "")
                if service:
                    # 应用允许/拒绝列表
                    if self.config.allow_list and service not in self.config.allow_list:
                        continue
                    if self.config.deny_list and service in self.config.deny_list:
                        continue
                    services.add(service)

            with self._lock:
                self._discovered_services = services
                self._last_refresh = now

            logger.info(f"Service discovery completed: found {len(services)} services")
            return services

        except Exception as e:
            logger.error(f"Service discovery failed: {e}")
            with self._lock:
                return self._discovered_services.copy()

    def get_services(self) -> Set[str]:
        """获取已发现的服务列表"""
        with self._lock:
            return self._discovered_services.copy()


class AutoCollector:
    """自动采集器"""

    def __init__(self, config: Optional[AutoCollectorConfig] = None):
        self.config = config or AutoCollectorConfig()

        # 初始化适配器
        self._prometheus_adapter = None
        self._otel_adapter = None
        self._service_discovery = None

        if self.config.prometheus_enabled:
            prom_config = PrometheusAdapterConfig(url=self.config.prometheus_url)
            self._prometheus_adapter = PrometheusAdapter(prom_config)

            if self.config.service_discovery.enabled:
                self._service_discovery = ServiceDiscovery(
                    self.config.service_discovery,
                    self._prometheus_adapter
                )

        if self.config.otel_enabled and self.config.otel_collector_url:
            otel_config = OpenTelemetryAdapterConfig(
                otel_collector_url=self.config.otel_collector_url,
                prometheus_backend_url=self.config.prometheus_url if self.config.prometheus_enabled else None
            )
            self._otel_adapter = OpenTelemetryAdapter(otel_config)

        # 采集状态
        self._running = False
        self._last_scrape: Optional[datetime] = None
        self._scrape_count = 0
        self._error_count = 0
        self._collected_metrics: List[CollectedMetrics] = []
        self._max_collected_history = 1000

        # 回调函数
        self._on_metrics_collected_callbacks: List[callable] = []

        # 后台线程
        self._scrape_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def on_metrics_collected(self, callback: callable):
        """注册指标采集完成回调"""
        self._on_metrics_collected_callbacks.append(callback)

    def _notify_callbacks(self, collected: CollectedMetrics):
        """通知回调"""
        for callback in self._on_metrics_collected_callbacks:
            try:
                callback(collected)
            except Exception as e:
                logger.error(f"Callback execution failed: {e}")

    def scrape_service(self, service_name: str) -> Optional[CollectedMetrics]:
        """采集单个服务的指标"""
        try:
            if self._prometheus_adapter:
                metrics = self._prometheus_adapter.get_service_metrics(
                    service_name=service_name,
                    lookback_minutes=self.config.lookback_minutes
                )

                collected = CollectedMetrics(
                    service_name=service_name,
                    timestamp=datetime.utcnow(),
                    metrics={
                        "cpu_percent": metrics.cpu_percent,
                        "memory_mb": metrics.memory_mb,
                        "latency_p99_ms": metrics.latency_p99_ms,
                        "error_rate": metrics.error_rate
                    },
                    source=CollectorSource.PROMETHEUS,
                    tags={"service": service_name}
                )

                self._store_collected_metrics(collected)
                self._notify_callbacks(collected)
                return collected

        except Exception as e:
            logger.error(f"Failed to scrape service {service_name}: {e}")
            self._error_count += 1

        return None

    def scrape_all_services(self) -> List[CollectedMetrics]:
        """采集所有发现的服务指标"""
        results = []

        # 获取服务列表
        if self._service_discovery:
            services = self._service_discovery.discover_services()
        else:
            # 如果没有服务发现，使用空集合
            services = set()

        logger.info(f"Starting scrape for {len(services)} services: {services}")

        for service_name in services:
            result = self.scrape_service(service_name)
            if result:
                results.append(result)

        self._last_scrape = datetime.utcnow()
        self._scrape_count += 1

        logger.info(f"Scrape completed: collected {len(results)} metrics")
        return results

    def _store_collected_metrics(self, collected: CollectedMetrics):
        """存储采集的指标"""
        self._collected_metrics.append(collected)

        # 清理过期数据
        if len(self._collected_metrics) > self._max_collected_history:
            self._collected_metrics = self._collected_metrics[-self._max_collected_history:]

    def _scrape_loop(self):
        """后台采集循环"""
        while not self._stop_event.is_set():
            try:
                self.scrape_all_services()
            except Exception as e:
                logger.error(f"Scrape loop error: {e}")
                self._error_count += 1

            # 等待下一次采集
            self._stop_event.wait(self.config.scrape_interval_seconds)

    def start(self):
        """启动自动采集"""
        if self._running:
            logger.warning("AutoCollector already running")
            return

        self._running = True
        self._stop_event.clear()

        # 启动后台线程
        self._scrape_thread = threading.Thread(target=self._scrape_loop, daemon=True)
        self._scrape_thread.start()

        logger.info(f"AutoCollector started with interval {self.config.scrape_interval_seconds}s")

    def stop(self):
        """停止自动采集"""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        if self._scrape_thread:
            self._scrape_thread.join(timeout=5)

        logger.info("AutoCollector stopped")

    def get_status(self) -> Dict[str, Any]:
        """获取采集器状态"""
        return {
            "running": self._running,
            "last_scrape": self._last_scrape.isoformat() if self._last_scrape else None,
            "scrape_count": self._scrape_count,
            "error_count": self._error_count,
            "services_discovered": len(self._service_discovery.get_services()) if self._service_discovery else 0,
            "collected_metrics_count": len(self._collected_metrics)
        }

    def get_recent_metrics(self, service_name: Optional[str] = None, limit: int = 100) -> List[CollectedMetrics]:
        """获取最近采集的指标"""
        metrics = self._collected_metrics

        if service_name:
            metrics = [m for m in metrics if m.service_name == service_name]

        return metrics[-limit:]

    def to_metrics_snapshot(self, collected: CollectedMetrics) -> MetricsSnapshot:
        """将采集的指标转换为 MetricsSnapshot 格式"""
        return MetricsSnapshot(
            service_name=collected.service_name,
            cpu_percent=collected.metrics.get("cpu_percent"),
            memory_mb=collected.metrics.get("memory_mb"),
            latency_p99_ms=collected.metrics.get("latency_p99_ms"),
            error_rate=collected.metrics.get("error_rate"),
            extra={
                "source": collected.source.value,
                "tags": collected.tags,
                "timestamp": collected.timestamp.isoformat()
            }
        )


# 全局自动采集器实例
auto_collector: Optional[AutoCollector] = None


def get_auto_collector(config: Optional[AutoCollectorConfig] = None) -> AutoCollector:
    """获取或创建自动采集器实例"""
    global auto_collector
    if auto_collector is None:
        auto_collector = AutoCollector(config)
    return auto_collector
