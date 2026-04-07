"""
AI Optimizer SDK 客户端
"""
import requests
from typing import Any, Dict, List, Optional
from datetime import datetime

from .models import (
    MetricsSnapshot,
    UsageSummary,
    AnalysisResult,
    CodeProposalsResult,
    AnomalyResult,
    RootCauseResult
)
from .exceptions import (
    AIOptimizerError,
    AuthenticationError,
    RateLimitError,
    NotFoundError,
    ServerError,
    ValidationError
)


class AIOptimizerClient:
    """AI Runtime Optimizer API 客户端

    使用示例:
        client = AIOptimizerClient(
            base_url="http://localhost:8012",
            api_key="your-api-key"  # 可选
        )

        # 上报指标
        client.record_metrics(MetricsSnapshot(
            service="my-service",
            latency_p99_ms=150.5,
            error_rate=0.01,
            cpu_percent=65.0
        ))

        # 执行分析
        result = client.analyze(service="my-service")
        print(result.suggestions)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8012",
        api_key: str = None,
        timeout: int = 30,
        debug: bool = False
    ):
        """初始化客户端

        Args:
            base_url: API 基础 URL
            api_key: API 密钥（可选，如果服务端启用了认证）
            timeout: 请求超时时间（秒）
            debug: 是否开启调试模式
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.debug = debug

        self._session = requests.Session()
        if api_key:
            self._session.headers["X-API-Key"] = api_key

        self._session.headers["Content-Type"] = "application/json"
        self._session.headers["User-Agent"] = "ai-optimizer-sdk/0.1.0"

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """发送 HTTP 请求"""
        url = f"{self.base_url}{path}"

        if self.debug:
            print(f"[SDK] {method} {url}")

        try:
            response = self._session.request(
                method,
                url,
                timeout=self.timeout,
                **kwargs
            )
        except requests.exceptions.Timeout:
            raise ServerError("Request timed out")
        except requests.exceptions.ConnectionError as e:
            raise ServerError(f"Connection failed: {e}")

        return self._handle_response(response)

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """处理 HTTP 响应"""
        if response.status_code == 200:
            return response.json() if response.content else {}
        elif response.status_code == 201:
            return response.json() if response.content else {}
        elif response.status_code == 401:
            raise AuthenticationError("Invalid API key or authentication required")
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                "Rate limit exceeded",
                retry_after=int(retry_after) if retry_after else None
            )
        elif response.status_code == 404:
            raise NotFoundError(response.json().get("message", "Resource not found"))
        elif response.status_code == 400:
            data = response.json()
            raise ValidationError(
                data.get("message", "Invalid request"),
                field=data.get("field")
            )
        elif response.status_code >= 500:
            raise ServerError(f"Server error: {response.status_code}")
        else:
            raise AIOptimizerError(
                f"Unexpected status code: {response.status_code}",
                status_code=response.status_code
            )

    # ==================== 指标上报 ====================

    def record_metrics(self, snapshot: MetricsSnapshot) -> Dict[str, Any]:
        """上报指标快照

        Args:
            snapshot: 指标快照对象

        Returns:
            {"status": "recorded", "service": "xxx"}
        """
        return self._request("POST", "/api/runtime/metrics", json=snapshot.to_dict())

    def record_usage(self, usage: UsageSummary) -> Dict[str, Any]:
        """上报用户使用情况

        Args:
            usage: 使用情况汇总对象

        Returns:
            {"status": "recorded", "service": "xxx"}
        """
        return self._request("POST", "/api/runtime/usage", json=usage.to_dict())

    # ==================== 分析功能 ====================

    def analyze(self, snapshot: MetricsSnapshot, config_hint: str = None) -> AnalysisResult:
        """仅根据指标进行分析（不含用户行为数据）

        Args:
            snapshot: 指标快照
            config_hint: 配置提示（可选）

        Returns:
            AnalysisResult 对象
        """
        payload = {"snapshot": snapshot.to_dict()}
        if config_hint:
            payload["config_hint"] = config_hint

        data = self._request("POST", "/api/runtime/analyze", json=payload)
        return AnalysisResult.from_dict(data)

    def holistic_analyze(
        self,
        snapshot: MetricsSnapshot,
        usage: UsageSummary = None,
        config_hint: str = None
    ) -> AnalysisResult:
        """综合分析：指标 + 用户行为数据

        Args:
            snapshot: 指标快照
            usage: 用户使用情况（可选）
            config_hint: 配置提示（可选）

        Returns:
            AnalysisResult 对象
        """
        payload = {"snapshot": snapshot.to_dict()}
        if usage:
            payload["usage"] = usage.to_dict()
        if config_hint:
            payload["config_hint"] = config_hint

        data = self._request("POST", "/api/runtime/holistic-analyze", json=payload)
        return AnalysisResult.from_dict(data)

    def code_proposals(
        self,
        snapshot: MetricsSnapshot,
        usage: UsageSummary = None,
        config_hint: str = None,
        language: str = "python"
    ) -> CodeProposalsResult:
        """生成代码变更提案

        Args:
            snapshot: 指标快照
            usage: 用户使用情况（可选）
            config_hint: 配置提示（可选）
            language: 主语言

        Returns:
            CodeProposalsResult 对象
        """
        payload = {
            "snapshot": snapshot.to_dict(),
            "language": language
        }
        if usage:
            payload["usage"] = usage.to_dict()
        if config_hint:
            payload["config_hint"] = config_hint

        data = self._request("POST", "/api/runtime/code-proposals", json=payload)
        return CodeProposalsResult.from_dict(data)

    # ==================== 查询功能 ====================

    def get_recommendations(self, service_name: str = None) -> List[Dict[str, Any]]:
        """获取最新的建议列表

        Args:
            service_name: 服务名（可选）

        Returns:
            建议列表
        """
        params = {}
        if service_name:
            params["service_name"] = service_name

        data = self._request("GET", "/api/runtime/recommendations", params=params)
        return data.get("recommendations", [])

    # ==================== 异常检测 ====================

    def detect_anomaly(
        self,
        service_name: str,
        metric_name: str,
        value: float
    ) -> AnomalyResult:
        """检测指标异常

        Args:
            service_name: 服务名
            metric_name: 指标名
            value: 指标值

        Returns:
            AnomalyResult 对象
        """
        data = self._request("POST", "/api/runtime/anomaly/detect", json={
            "service_name": service_name,
            "metric_name": metric_name,
            "value": value
        })
        return AnomalyResult.from_dict(data)

    def get_anomaly_history(
        self,
        service_name: str = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取异常历史

        Args:
            service_name: 服务名（可选）
            limit: 返回数量限制

        Returns:
            异常历史记录
        """
        params = {}
        if service_name:
            params["service_name"] = service_name
        params["limit"] = limit

        data = self._request("GET", "/api/runtime/anomaly/history", params=params)
        return data.get("anomalies", [])

    # ==================== 根因分析 ====================

    def analyze_root_cause(
        self,
        target_service: str = None,
        lookback_minutes: int = 30
    ) -> RootCauseResult:
        """执行根因分析

        Args:
            target_service: 目标服务（可选）
            lookback_minutes: 回溯时间（分钟）

        Returns:
            RootCauseResult 对象
        """
        data = self._request("POST", "/api/runtime/root-cause/analyze", json={
            "target_service": target_service,
            "lookback_minutes": lookback_minutes
        })
        return RootCauseResult.from_dict(data)

    # ==================== 服务映射 ====================

    def get_service_map(self) -> Dict[str, Any]:
        """获取服务映射数据"""
        return self._request("GET", "/api/runtime/service-map")

    def get_services(self) -> List[Dict[str, Any]]:
        """获取所有服务列表"""
        data = self._request("GET", "/api/runtime/service-map/services")
        return data.get("services", [])

    def get_service(self, service_id: str) -> Dict[str, Any]:
        """获取服务详情"""
        return self._request("GET", f"/api/runtime/service-map/services/{service_id}")

    # ==================== 告警功能 ====================

    def get_alerts(
        self,
        service_name: str = None,
        severity: str = None,
        status: str = None
    ) -> List[Dict[str, Any]]:
        """获取活跃告警列表"""
        params = {}
        if service_name:
            params["service_name"] = service_name
        if severity:
            params["severity"] = severity
        if status:
            params["status"] = status

        data = self._request("GET", "/api/runtime/alerts", params=params)
        return data.get("alerts", [])

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "sdk") -> bool:
        """确认告警"""
        data = self._request("POST", f"/api/runtime/alerts/{alert_id}/acknowledge", params={
            "acknowledged_by": acknowledged_by
        })
        return data.get("status") == "acknowledged"

    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        data = self._request("POST", f"/api/runtime/alerts/{alert_id}/resolve")
        return data.get("status") == "resolved"

    # ==================== 追踪功能 ====================

    def get_trace(self, trace_id: str) -> Dict[str, Any]:
        """获取追踪详情"""
        return self._request("GET", f"/api/runtime/tracing/{trace_id}")

    def search_traces(
        self,
        service_name: str = None,
        operation_name: str = None,
        status: str = None,
        min_duration_ms: float = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """搜索追踪"""
        params = {"limit": limit}
        if service_name:
            params["service_name"] = service_name
        if operation_name:
            params["operation_name"] = operation_name
        if status:
            params["status"] = status
        if min_duration_ms:
            params["min_duration_ms"] = min_duration_ms

        data = self._request("GET", "/api/runtime/tracing/search", params=params)
        return data.get("traces", [])

    # ==================== 健康检查 ====================

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return self._request("GET", "/health")

    def close(self):
        """关闭客户端连接"""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
