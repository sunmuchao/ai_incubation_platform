"""
SDK 数据模型
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class MetricsSnapshot:
    """指标快照"""
    service: str
    timestamp: str = None
    latency_p50_ms: float = None
    latency_p99_ms: float = None
    error_rate: float = None
    requests_per_second: float = None
    cpu_percent: float = None
    memory_mb: float = None
    instance_count: int = None
    custom_metrics: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "service": self.service,
        }
        if self.timestamp:
            data["timestamp"] = self.timestamp
        if self.latency_p50_ms is not None:
            data["latency_p50_ms"] = self.latency_p50_ms
        if self.latency_p99_ms is not None:
            data["latency_p99_ms"] = self.latency_p99_ms
        if self.error_rate is not None:
            data["error_rate"] = self.error_rate
        if self.requests_per_second is not None:
            data["requests_per_second"] = self.requests_per_second
        if self.cpu_percent is not None:
            data["cpu_percent"] = self.cpu_percent
        if self.memory_mb is not None:
            data["memory_mb"] = self.memory_mb
        if self.instance_count is not None:
            data["instance_count"] = self.instance_count
        if self.custom_metrics:
            data["custom_metrics"] = self.custom_metrics
        return data


@dataclass
class RouteUsageStat:
    """路由使用统计"""
    route: str
    request_count: int
    avg_latency_ms: float
    error_count: int = 0
    feature_flags: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "route": self.route,
            "request_count": self.request_count,
            "avg_latency_ms": self.avg_latency_ms,
            "error_count": self.error_count,
            "feature_flags": self.feature_flags
        }


@dataclass
class UsageSummary:
    """使用情况汇总"""
    service: str
    route_stats: List[RouteUsageStat] = field(default_factory=list)
    feature_adoption: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service": self.service,
            "route_stats": [r.to_dict() for r in self.route_stats],
            "feature_adoption": self.feature_adoption
        }


@dataclass
class Suggestion:
    """优化建议"""
    id: str
    strategy_id: str
    type: str
    action: str
    confidence: float
    priority: str
    evidence: str
    tags: List[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """分析结果"""
    service: str
    created_at: str
    suggestions: List[Suggestion]
    usage_informed: bool = False
    analysis_id: str = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisResult":
        suggestions = [
            Suggestion(
                id=s.get("id", ""),
                strategy_id=s.get("strategy_id", ""),
                type=s.get("type", ""),
                action=s.get("action", ""),
                confidence=s.get("confidence", 0),
                priority=s.get("priority", ""),
                evidence=s.get("evidence", ""),
                tags=s.get("tags", [])
            )
            for s in data.get("suggestions", [])
        ]
        return cls(
            service=data.get("service", ""),
            created_at=data.get("created_at", ""),
            suggestions=suggestions,
            usage_informed=data.get("usage_informed", False),
            analysis_id=data.get("analysis_id")
        )


@dataclass
class CodeProposal:
    """代码变更提案"""
    id: str
    file_path: str
    description: str
    diff: str
    confidence: float
    related_suggestion_id: str = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CodeProposal":
        return cls(
            id=data.get("id", ""),
            file_path=data.get("file_path", ""),
            description=data.get("description", ""),
            diff=data.get("diff", ""),
            confidence=data.get("confidence", 0),
            related_suggestion_id=data.get("related_suggestion_id")
        )


@dataclass
class CodeProposalsResult:
    """代码提案结果"""
    service: str
    created_at: str
    proposals: List[CodeProposal]
    proposals_id: str = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CodeProposalsResult":
        proposals = [
            CodeProposal.from_dict(p)
            for p in data.get("proposals", [])
        ]
        return cls(
            service=data.get("service", ""),
            created_at=data.get("created_at", ""),
            proposals=proposals,
            proposals_id=data.get("proposals_id")
        )


@dataclass
class AnomalyResult:
    """异常检测结果"""
    anomaly_detected: bool
    anomaly_type: str = None
    severity: str = None
    current_value: float = None
    expected_value: float = None
    confidence: float = None
    message: str = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnomalyResult":
        anomaly = data.get("anomaly", {})
        return cls(
            anomaly_detected=data.get("anomaly_detected", False),
            anomaly_type=anomaly.get("type") if anomaly else None,
            severity=anomaly.get("severity") if anomaly else None,
            current_value=anomaly.get("current_value") if anomaly else None,
            expected_value=anomaly.get("expected_value") if anomaly else None,
            confidence=anomaly.get("confidence") if anomaly else None,
            message=anomaly.get("message") if anomaly else None
        )


@dataclass
class RootCauseResult:
    """根因分析结果"""
    inference_id: str
    timestamp: str
    confidence_level: str
    root_causes: List[Dict[str, Any]]
    recommendations: List[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RootCauseResult":
        return cls(
            inference_id=data.get("inference_id", ""),
            timestamp=data.get("timestamp", ""),
            confidence_level=data.get("confidence_level", ""),
            root_causes=data.get("root_causes", []),
            recommendations=data.get("recommendations", [])
        )
