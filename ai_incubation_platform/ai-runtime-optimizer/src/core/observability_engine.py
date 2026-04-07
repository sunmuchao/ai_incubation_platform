"""
可观测性引擎 v2.4
统一指标 (Metrics)、日志 (Logs)、追踪 (Traces) 的可观测性平台
"""
import logging
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import hashlib
import json

logger = logging.getLogger(__name__)


# ============================================================================
# 日志聚合引擎
# ============================================================================

class LogLevel(str, Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: datetime
    level: LogLevel
    service_name: str
    message: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    logger_name: str = ""
    thread_name: str = ""
    exception: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "service_name": self.service_name,
            "message": self.message,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "logger_name": self.logger_name,
            "thread_name": self.thread_name,
            "exception": self.exception,
            "attributes": self.attributes,
            "tags": self.tags
        }


@dataclass
class LogPattern:
    """日志模式（用于聚类分析）"""
    pattern_id: str
    pattern_template: str  # 参数化后的模板，如 "User {user_id} login {status}"
    count: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    severity: LogLevel = LogLevel.INFO
    sample_messages: List[str] = field(default_factory=list)
    attributes_template: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "pattern_id": self.pattern_id,
            "pattern_template": self.pattern_template,
            "count": self.count,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "severity": self.severity.value,
            "sample_count": len(self.sample_messages),
            "attributes_template": self.attributes_template
        }


class LogAggregator:
    """日志聚合器"""

    def __init__(self, max_entries: int = 100000, pattern_ttl_hours: int = 24):
        self._entries: List[LogEntry] = []
        self._max_entries = max_entries
        self._pattern_ttl_hours = pattern_ttl_hours

        # 模式聚类
        self._patterns: Dict[str, LogPattern] = {}
        self._pattern_hashes: Dict[str, str] = {}  # message_hash -> pattern_id

        # 索引
        self._by_trace_id: Dict[str, List[int]] = defaultdict(list)  # trace_id -> entry indices
        self._by_service: Dict[str, List[int]] = defaultdict(list)  # service_name -> entry indices
        self._by_level: Dict[LogLevel, List[int]] = defaultdict(list)  # level -> entry indices
        self._by_time: Dict[str, List[int]] = defaultdict(list)  # hour_bucket -> entry indices

        # 统计
        self._stats = {
            "total_received": 0,
            "total_stored": 0,
            "patterns_discovered": 0,
            "errors_count": 0,
            "warnings_count": 0
        }

        self._lock = threading.Lock()

    def add_log(self, entry: LogEntry):
        """添加日志条目"""
        with self._lock:
            self._stats["total_received"] += 1

            # 存储日志
            index = len(self._entries)
            self._entries.append(entry)
            self._stats["total_stored"] += 1

            # 更新索引
            if entry.trace_id:
                self._by_trace_id[entry.trace_id].append(index)
            self._by_service[entry.service_name].append(index)
            self._by_level[entry.level].append(index)

            hour_bucket = entry.timestamp.strftime("%Y-%m-%d-%H")
            self._by_time[hour_bucket].append(index)

            # 更新统计
            if entry.level == LogLevel.ERROR:
                self._stats["errors_count"] += 1
            elif entry.level == LogLevel.WARNING:
                self._stats["warnings_count"] += 1

            # 模式聚类
            self._cluster_pattern(entry)

            # 清理过期数据
            if len(self._entries) > self._max_entries:
                self._cleanup_old_entries()

    def _cluster_pattern(self, entry: LogEntry):
        """将日志聚类到模式"""
        # 参数化日志消息
        template, params = self._parameterize_message(entry.message)
        pattern_hash = hashlib.md5(template.encode()).hexdigest()[:16]

        if pattern_hash in self._pattern_hashes:
            pattern_id = self._pattern_hashes[pattern_hash]
            pattern = self._patterns[pattern_id]
            pattern.count += 1
            pattern.last_seen = entry.timestamp
            if len(pattern.sample_messages) < 5:
                pattern.sample_messages.append(entry.message)
            # 更新严重程度
            if entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
                pattern.severity = entry.level
        else:
            # 创建新模式
            pattern_id = f"pattern_{pattern_hash}"
            self._patterns[pattern_id] = LogPattern(
                pattern_id=pattern_id,
                pattern_template=template,
                count=1,
                first_seen=entry.timestamp,
                last_seen=entry.timestamp,
                severity=entry.level,
                sample_messages=[entry.message],
                attributes_template={k: type(v).__name__ for k, v in params.items()}
            )
            self._pattern_hashes[pattern_hash] = pattern_id
            self._stats["patterns_discovered"] += 1

    def _parameterize_message(self, message: str) -> tuple:
        """参数化日志消息，提取模板"""
        import re

        # 替换常见的变量模式
        template = message

        # 1. UUID 模式（先替换 UUID，避免其中的数字被后续替换）
        template = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '{uuid}', template, flags=re.I)

        # 2. IP 地址模式
        template = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '{ip}', template)

        # 3. 时间戳模式（在数字之前替换）
        template = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', '{timestamp}', template)

        # 4. 数字模式（独立数字，最后替换）
        template = re.sub(r'\b\d+\b', '{num}', template)

        # 提取参数
        params = {}
        for i, match in enumerate(re.finditer(r'\{(\w+)\}', template)):
            params[f"param_{i}"] = match.group(0)

        return template, params

    def _cleanup_old_entries(self):
        """清理旧日志"""
        cutoff = datetime.utcnow() - timedelta(hours=self._pattern_ttl_hours)
        old_count = 0

        # 找出需要保留的索引
        keep_indices = set()
        for i, entry in enumerate(self._entries):
            if entry.timestamp >= cutoff:
                keep_indices.add(i)

        if len(keep_indices) < len(self._entries):
            # 重建 entries
            new_entries = []
            for i, entry in enumerate(self._entries):
                if i in keep_indices:
                    new_entries.append(entry)
            self._entries = new_entries

    def search_logs(
        self,
        service_name: Optional[str] = None,
        level: Optional[LogLevel] = None,
        trace_id: Optional[str] = None,
        query: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[LogEntry]:
        """搜索日志"""
        with self._lock:
            results = []

            # 使用索引加速查询
            candidate_indices = None

            if trace_id and trace_id in self._by_trace_id:
                candidate_indices = set(self._by_trace_id[trace_id])

            if service_name and service_name in self._by_service:
                service_indices = set(self._by_service[service_name])
                if candidate_indices is not None:
                    candidate_indices &= service_indices
                else:
                    candidate_indices = service_indices

            if level and level in self._by_level:
                level_indices = set(self._by_level[level])
                if candidate_indices is not None:
                    candidate_indices &= level_indices
                else:
                    candidate_indices = level_indices

            # 如果没有使用索引，遍历所有
            if candidate_indices is None:
                candidate_indices = set(range(len(self._entries)))

            # 过滤
            for i in sorted(candidate_indices, reverse=True):
                if len(results) >= limit:
                    break

                entry = self._entries[i]

                if start_time and entry.timestamp < start_time:
                    continue
                if end_time and entry.timestamp > end_time:
                    continue
                if query and query.lower() not in entry.message.lower():
                    continue

                results.append(entry)

            return list(reversed(results))

    def get_patterns(
        self,
        min_count: int = 1,
        severity: Optional[LogLevel] = None,
        limit: int = 50
    ) -> List[LogPattern]:
        """获取日志模式"""
        with self._lock:
            patterns = list(self._patterns.values())

            # 过滤
            patterns = [p for p in patterns if p.count >= min_count]
            if severity:
                patterns = [p for p in patterns if p.severity == severity]

            # 排序（按出现次数）
            patterns.sort(key=lambda p: p.count, reverse=True)

            return patterns[:limit]

    def get_error_patterns(self, limit: int = 20) -> List[LogPattern]:
        """获取错误模式"""
        return [
            p for p in self.get_patterns(min_count=1, limit=limit)
            if p.severity in [LogLevel.ERROR, LogLevel.CRITICAL]
        ]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                **self._stats,
                "current_entries": len(self._entries),
                "total_patterns": len(self._patterns),
                "error_patterns": len([p for p in self._patterns.values() if p.severity in [LogLevel.ERROR, LogLevel.CRITICAL]])
            }

    def get_logs_for_trace(self, trace_id: str) -> List[LogEntry]:
        """获取与追踪关联的日志"""
        with self._lock:
            indices = self._by_trace_id.get(trace_id, [])
            return [self._entries[i] for i in indices if i < len(self._entries)]


# ============================================================================
# 统一可观测性引擎
# ============================================================================

@dataclass
class ObservabilityContext:
    """可观测性上下文"""
    trace_id: str
    service_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "unknown"
    metrics: Dict[str, Any] = field(default_factory=dict)
    logs: List[LogEntry] = field(default_factory=list)
    span_count: int = 0
    error_count: int = 0


class ObservabilityEngine:
    """统一可观测性引擎"""

    def __init__(
        self,
        log_aggregator: Optional[LogAggregator] = None,
        tracer: Optional[Any] = None  # DistributedTracer
    ):
        self._log_aggregator = log_aggregator or LogAggregator()
        self._tracer = tracer

        # 服务健康状态
        self._service_health: Dict[str, Dict[str, Any]] = {}

        # 告警规则
        self._alert_rules: List[Dict[str, Any]] = []

        self._lock = threading.Lock()

    def ingest_log(
        self,
        level: str,
        service_name: str,
        message: str,
        trace_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """摄入日志"""
        try:
            log_level = LogLevel(level.upper())
        except ValueError:
            log_level = LogLevel.INFO

        entry = LogEntry(
            timestamp=datetime.utcnow(),
            level=log_level,
            service_name=service_name,
            message=message,
            trace_id=trace_id,
            attributes=attributes or {}
        )

        self._log_aggregator.add_log(entry)

        # 更新服务健康状态
        self._update_service_health(service_name, log_level)

    def ingest_metrics(self, service_name: str, metrics: Dict[str, Any]):
        """摄入指标"""
        with self._lock:
            if service_name not in self._service_health:
                self._service_health[service_name] = {
                    "last_seen": datetime.utcnow(),
                    "metrics_history": [],
                    "error_count": 0,
                    "warning_count": 0,
                    "health_score": 100.0
                }

            health = self._service_health[service_name]
            health["last_seen"] = datetime.utcnow()
            health["metrics_history"].append({
                "timestamp": datetime.utcnow(),
                "metrics": metrics
            })

            # 保留最近 100 个数据点
            if len(health["metrics_history"]) > 100:
                health["metrics_history"] = health["metrics_history"][-100:]

            # 计算健康分数
            health["health_score"] = self._calculate_health_score(metrics)

    def _calculate_health_score(self, metrics: Dict[str, Any]) -> float:
        """计算健康分数"""
        score = 100.0

        # CPU 健康
        cpu = metrics.get("cpu_percent", 0)
        if cpu > 90:
            score -= 30
        elif cpu > 70:
            score -= 15

        # 内存健康
        memory = metrics.get("memory_percent", 0)
        if memory > 90:
            score -= 30
        elif memory > 70:
            score -= 15

        # 错误率健康
        error_rate = metrics.get("error_rate", 0)
        if error_rate > 5:
            score -= 25
        elif error_rate > 1:
            score -= 10

        # 延迟健康
        latency_p99 = metrics.get("latency_p99_ms", 0)
        if latency_p99 > 1000:
            score -= 20
        elif latency_p99 > 500:
            score -= 10

        return max(0, min(100, score))

    def _update_service_health(self, service_name: str, level: LogLevel):
        """更新服务健康状态（基于日志）"""
        with self._lock:
            if service_name not in self._service_health:
                self._service_health[service_name] = {
                    "last_seen": datetime.utcnow(),
                    "metrics_history": [],
                    "error_count": 0,
                    "warning_count": 0,
                    "health_score": 100.0
                }

            health = self._service_health[service_name]
            health["last_seen"] = datetime.utcnow()

            if level == LogLevel.ERROR:
                health["error_count"] += 1
            elif level == LogLevel.WARNING:
                health["warning_count"] += 1

            # 根据错误数量扣分
            error_penalty = min(health["error_count"] * 2, 50)
            warning_penalty = min(health["warning_count"] * 0.5, 20)

            health["health_score"] = max(0, 100 - error_penalty - warning_penalty)

    def get_service_health(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """获取服务健康状态"""
        with self._lock:
            if service_name:
                return self._service_health.get(service_name, {})
            return {
                name: {
                    **data,
                    "service_name": name
                }
                for name, data in self._service_health.items()
            }

    def get_observability_overview(self) -> Dict[str, Any]:
        """获取可观测性概览"""
        log_stats = self._log_aggregator.get_stats()
        tracer_stats = self._tracer.get_stats() if self._tracer else {}

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "logs": {
                "total_entries": log_stats.get("total_stored", 0),
                "patterns_discovered": log_stats.get("patterns_discovered", 0),
                "error_patterns": log_stats.get("error_patterns", 0),
                "errors_count": log_stats.get("errors_count", 0)
            },
            "traces": {
                "total_traces": tracer_stats.get("total_traces", 0),
                "total_spans": tracer_stats.get("total_spans", 0)
            },
            "services": {
                "total_services": len(self._service_health),
                "healthy_services": len([s for s, d in self._service_health.items() if d.get("health_score", 0) >= 80]),
                "degraded_services": len([s for s, d in self._service_health.items() if 50 <= d.get("health_score", 0) < 80]),
                "unhealthy_services": len([s for s, d in self._service_health.items() if d.get("health_score", 0) < 50])
            }
        }

    def analyze_service_issues(self, service_name: str) -> Dict[str, Any]:
        """分析服务问题"""
        issues = []
        recommendations = []

        health = self._service_health.get(service_name, {})
        health_score = health.get("health_score", 100)

        # 获取最近的错误日志
        error_logs = self._log_aggregator.search_logs(
            service_name=service_name,
            level=LogLevel.ERROR,
            limit=10
        )

        # 获取错误模式
        error_patterns = self._log_aggregator.get_error_patterns(limit=10)

        if health_score < 50:
            issues.append({
                "type": "critical_health",
                "severity": "critical",
                "description": f"Service health score is critically low: {health_score:.1f}",
                "impact": "Service may be experiencing outages or severe degradation"
            })
            recommendations.append({
                "action": "immediate_investigation",
                "description": "Immediately investigate service logs and metrics"
            })
        elif health_score < 80:
            issues.append({
                "type": "degraded_health",
                "severity": "warning",
                "description": f"Service health score is degraded: {health_score:.1f}",
                "impact": "Service performance may be impacted"
            })
            recommendations.append({
                "action": "monitor_closely",
                "description": "Monitor service closely and prepare remediation"
            })

        if error_logs:
            issues.append({
                "type": "recent_errors",
                "severity": "warning",
                "description": f"Found {len(error_logs)} recent error logs",
                "sample_messages": [log.message[:100] for log in error_logs[:3]]
            })
            recommendations.append({
                "action": "review_error_logs",
                "description": "Review error logs to identify root cause"
            })

        return {
            "service_name": service_name,
            "health_score": health_score,
            "health_status": "healthy" if health_score >= 80 else ("degraded" if health_score >= 50 else "critical"),
            "issues": issues,
            "recommendations": recommendations,
            "error_patterns": [p.to_dict() for p in error_patterns[:5]],
            "recent_errors": [log.to_dict() for log in error_logs[:5]]
        }

    def correlate_trace_with_logs(self, trace_id: str) -> Dict[str, Any]:
        """关联追踪与日志"""
        # 获取追踪
        trace = None
        if self._tracer:
            trace = self._tracer.get_trace(trace_id)

        # 获取关联日志
        logs = self._log_aggregator.get_logs_for_trace(trace_id)

        return {
            "trace_id": trace_id,
            "trace": trace.to_dict() if trace else None,
            "related_logs": [log.to_dict() for log in logs],
            "log_count": len(logs),
            "error_logs": [log.to_dict() for log in logs if log.level in [LogLevel.ERROR, LogLevel.CRITICAL]]
        }

    def get_log_stats(self) -> Dict[str, Any]:
        """获取日志统计"""
        return self._log_aggregator.get_stats()

    def search_logs(
        self,
        service_name: Optional[str] = None,
        level: Optional[str] = None,
        trace_id: Optional[str] = None,
        query: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """搜索日志"""
        log_level = LogLevel(level.upper()) if level else None
        logs = self._log_aggregator.search_logs(
            service_name=service_name,
            level=log_level,
            trace_id=trace_id,
            query=query,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        return [log.to_dict() for log in logs]

    def get_log_patterns(self, min_count: int = 1, severity: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """获取日志模式"""
        log_severity = LogLevel(severity.upper()) if severity else None
        patterns = self._log_aggregator.get_patterns(min_count=min_count, severity=log_severity, limit=limit)
        return [p.to_dict() for p in patterns]


# 全局可观测性引擎实例
global_observability_engine: Optional[ObservabilityEngine] = None


def get_observability_engine(
    log_aggregator: Optional[LogAggregator] = None,
    tracer: Optional[Any] = None
) -> ObservabilityEngine:
    """获取或创建可观测性引擎实例"""
    global global_observability_engine
    if global_observability_engine is None:
        global_observability_engine = ObservabilityEngine(
            log_aggregator=log_aggregator,
            tracer=tracer
        )
    return global_observability_engine
