"""
Prometheus 指标适配器
从Prometheus查询并转换为优化器统一的指标格式
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import requests
from datetime import datetime, timedelta
from models.analysis import MetricsSnapshot


class PrometheusAdapterConfig(BaseModel):
    """Prometheus适配器配置"""
    url: str = Field("http://localhost:9090", description="Prometheus服务地址")
    timeout: int = Field(10, description="查询超时时间(秒)")
    job_label: str = Field("job", description="服务名对应的标签名")
    cpu_metric: str = Field("process_cpu_usage", description="CPU使用率指标名")
    memory_metric: str = Field("process_resident_memory_bytes", description="内存使用指标名")
    latency_p99_metric: str = Field("http_request_duration_seconds_bucket", description="延迟P99指标名")
    error_rate_metric: str = Field("http_requests_total", description="请求错误率指标名")


class PrometheusAdapter:
    """Prometheus指标采集适配器"""

    def __init__(self, config: Optional[PrometheusAdapterConfig] = None):
        self.config = config or PrometheusAdapterConfig()

    def _query_prometheus(self, query: str, time: Optional[datetime] = None) -> Dict[str, Any]:
        """执行PromQL查询"""
        params = {"query": query}
        if time:
            params["time"] = time.timestamp()

        try:
            response = requests.get(
                f"{self.config.url.rstrip('/')}/api/v1/query",
                params=params,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "success":
                raise ValueError(f"Prometheus query failed: {data.get('error', 'Unknown error')}")

            return data

        except Exception as e:
            raise RuntimeError(f"Failed to query Prometheus: {str(e)}") from e

    def get_service_metrics(
        self,
        service_name: str,
        lookback_minutes: int = 5
    ) -> MetricsSnapshot:
        """获取指定服务的指标快照"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=lookback_minutes)

        # 查询CPU使用率
        cpu_query = f'avg_over_time({self.config.cpu_metric}{{{self.config.job_label}="{service_name}"}}[{lookback_minutes}m])'
        cpu_result = self._query_prometheus(cpu_query, end_time)
        cpu_percent = self._extract_scalar_value(cpu_result)

        # 查询内存使用(MB)
        memory_query = f'avg_over_time({self.config.memory_metric}{{{self.config.job_label}="{service_name}"}}[{lookback_minutes}m])'
        memory_result = self._query_prometheus(memory_query, end_time)
        memory_bytes = self._extract_scalar_value(memory_result)
        memory_mb = memory_bytes / (1024 * 1024) if memory_bytes else None

        # 查询P99延迟(ms)
        latency_query = (
            f'histogram_quantile(0.99, sum by(le) (rate({self.config.latency_p99_metric}'
            f'{{{self.config.job_label}="{service_name}"}}[{lookback_minutes}m])))'
        )
        latency_result = self._query_prometheus(latency_query, end_time)
        latency_seconds = self._extract_scalar_value(latency_result)
        latency_p99_ms = latency_seconds * 1000 if latency_seconds else None

        # 查询错误率
        total_requests_query = f'sum(rate({self.config.error_rate_metric}{{{self.config.job_label}="{service_name}"}}[{lookback_minutes}m]))'
        error_requests_query = f'sum(rate({self.config.error_rate_metric}{{{self.config.job_label}="{service_name}", status_code=~"5..|4.."}}[{lookback_minutes}m]))'

        total_result = self._query_prometheus(total_requests_query, end_time)
        total_requests = self._extract_scalar_value(total_result)

        error_result = self._query_prometheus(error_requests_query, end_time)
        error_requests = self._extract_scalar_value(error_result)

        error_rate = None
        if total_requests and total_requests > 0:
            error_rate = error_requests / total_requests if error_requests else 0.0

        return MetricsSnapshot(
            service_name=service_name,
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            latency_p99_ms=latency_p99_ms,
            error_rate=error_rate,
            extra={
                "lookback_minutes": lookback_minutes,
                "query_time": end_time.isoformat(),
                "source": "prometheus"
            }
        )

    def _extract_scalar_value(self, result: Dict[str, Any]) -> Optional[float]:
        """从Prometheus查询结果中提取标量值"""
        try:
            results = result.get("data", {}).get("result", [])
            if not results:
                return None

            value_list = results[0].get("value", [])
            if len(value_list) >= 2:
                return float(value_list[1])

            return None
        except (IndexError, ValueError, TypeError):
            return None
