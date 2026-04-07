"""
根因分析引擎
基于服务拓扑、指标关联分析和异常传播路径进行根因定位
对标 Dynatrace Davis 和 Datadog 根因分析能力
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import heapq

from .service_map import service_map, ServiceNode, DependencyEdge, HealthStatus
from .anomaly_detector import anomaly_detector, AnomalyEvent, AnomalyType, AnomalySeverity

logger = logging.getLogger(__name__)


class RootCauseType(str, Enum):
    """根因类型"""
    SERVICE_EXCEPTION = "service_exception"  # 服务异常
    DEPENDENCY_FAILURE = "dependency_failure"  # 依赖故障
    RESOURCE_EXHAUSTION = "resource_exhaustion"  # 资源耗尽
    NETWORK_ISSUE = "network_issue"  # 网络问题
    DATABASE_ISSUE = "database_issue"  # 数据库问题
    CASCADE_FAILURE = "cascade_failure"  # 级联故障
    CONFIG_CHANGE = "config_change"  # 配置变更
    DEPLOYMENT_ISSUE = "deployment_issue"  # 部署问题


class ConfidenceLevel(str, Enum):
    """置信度等级"""
    VERY_HIGH = "very_high"  # > 0.9
    HIGH = "high"  # > 0.7
    MEDIUM = "medium"  # > 0.5
    LOW = "low"  # > 0.3
    VERY_LOW = "very_low"  # <= 0.3


@dataclass
class RootCauseCandidate:
    """根因候选"""
    id: str
    service_id: str
    service_name: str
    root_cause_type: RootCauseType
    confidence: float
    confidence_level: ConfidenceLevel
    evidence: List[str]
    impact_scope: List[str]  # 受影响的服务列表
    suggested_actions: List[str]
    first_anomaly_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "service_id": self.service_id,
            "service_name": self.service_name,
            "root_cause_type": self.root_cause_type.value,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level.value,
            "evidence": self.evidence,
            "impact_scope": self.impact_scope,
            "suggested_actions": self.suggested_actions,
            "first_anomaly_time": self.first_anomaly_time.isoformat() if self.first_anomaly_time else None,
            "metadata": self.metadata
        }


@dataclass
class PropagationPath:
    """异常传播路径"""
    source_service: str
    target_service: str
    path: List[str]
    propagation_type: str  # cascade, correlated, etc.
    total_latency_impact_ms: float
    total_error_rate_impact: float
    affected_services: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "source_service": self.source_service,
            "target_service": self.target_service,
            "path": self.path,
            "propagation_type": self.propagation_type,
            "total_latency_impact_ms": self.total_latency_impact_ms,
            "total_error_rate_impact": self.total_error_rate_impact,
            "affected_services": self.affected_services
        }


@dataclass
class CorrelationAnalysis:
    """关联分析结果"""
    metric_a_service: str
    metric_a_name: str
    metric_b_service: str
    metric_b_name: str
    correlation_coefficient: float  # -1 to 1
    correlation_type: str  # positive, negative, none
    time_lag_seconds: int  # A 领先 B 的时间（秒），正数表示 A 领先
    is_significant: bool  # 是否显著相关

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "metric_a_service": self.metric_a_service,
            "metric_a_name": self.metric_a_name,
            "metric_b_service": self.metric_b_service,
            "metric_b_name": self.metric_b_name,
            "correlation_coefficient": self.correlation_coefficient,
            "correlation_type": self.correlation_type,
            "time_lag_seconds": self.time_lag_seconds,
            "is_significant": self.is_significant
        }


@dataclass
class RootCauseAnalysisResult:
    """根因分析结果"""
    id: str
    analysis_time: datetime
    symptoms: List[Dict[str, Any]]  # 症状列表
    root_causes: List[RootCauseCandidate]
    propagation_paths: List[PropagationPath]
    correlations: List[CorrelationAnalysis]
    summary: str
    recommended_actions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "analysis_time": self.analysis_time.isoformat(),
            "symptoms": self.symptoms,
            "root_causes": [rc.to_dict() for rc in self.root_causes],
            "propagation_paths": [pp.to_dict() for pp in self.propagation_paths],
            "correlations": [ca.to_dict() for ca in self.correlations],
            "summary": self.summary,
            "recommended_actions": self.recommended_actions
        }


class RootCauseAnalyzer:
    """根因分析器"""

    def __init__(self):
        self._analysis_history: List[RootCauseAnalysisResult] = []
        self._max_history_size = 100

        # 指标相关性缓存
        self._correlation_cache: Dict[str, CorrelationAnalysis] = {}

        # 传播路径缓存
        self._propagation_cache: Dict[str, List[PropagationPath]] = {}

    def analyze(
        self,
        target_service: Optional[str] = None,
        lookback_minutes: int = 30
    ) -> RootCauseAnalysisResult:
        """执行根因分析"""
        analysis_time = datetime.utcnow()
        analysis_id = f"rca-{analysis_time.strftime('%Y%m%d%H%M%S')}"

        # 1. 收集症状
        symptoms = self._collect_symptoms(target_service, lookback_minutes)

        # 2. 识别根因候选
        root_causes = self._identify_root_causes(symptoms, lookback_minutes)

        # 3. 分析传播路径
        propagation_paths = self._analyze_propagation_paths(root_causes)

        # 4. 执行关联分析
        correlations = self._analyze_correlations(symptoms, lookback_minutes)

        # 5. 生成总结和建议
        summary, recommended_actions = self._generate_summary_and_actions(
            root_causes, propagation_paths, correlations
        )

        result = RootCauseAnalysisResult(
            id=analysis_id,
            analysis_time=analysis_time,
            symptoms=symptoms,
            root_causes=root_causes,
            propagation_paths=propagation_paths,
            correlations=correlations,
            summary=summary,
            recommended_actions=recommended_actions
        )

        # 保存历史记录
        self._analysis_history.append(result)
        if len(self._analysis_history) > self._max_history_size:
            self._analysis_history = self._analysis_history[-self._max_history_size:]

        logger.info(f"Root cause analysis completed: {analysis_id}, found {len(root_causes)} root causes")
        return result

    def _collect_symptoms(
        self,
        target_service: Optional[str],
        lookback_minutes: int
    ) -> List[Dict[str, Any]]:
        """收集症状（异常事件、健康状态恶化等）"""
        symptoms = []

        # 1. 收集异常检测器的异常事件
        anomalies = anomaly_detector.get_recent_anomalies(limit=100)
        cutoff_time = datetime.utcnow() - timedelta(minutes=lookback_minutes)

        for anomaly in anomalies:
            if anomaly.timestamp >= cutoff_time:
                if target_service is None or anomaly.service_name == target_service:
                    symptoms.append({
                        "type": "anomaly",
                        "service": anomaly.service_name,
                        "metric": anomaly.metric_name,
                        "anomaly_type": anomaly.anomaly_type.value,
                        "severity": anomaly.severity.value,
                        "current_value": anomaly.current_value,
                        "expected_value": anomaly.expected_value,
                        "deviation": anomaly.deviation,
                        "timestamp": anomaly.timestamp.isoformat()
                    })

        # 2. 收集服务健康状态恶化
        for service_id, service in service_map._services.items():
            if target_service and service_id != target_service:
                continue

            if service.health_status in [HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]:
                symptoms.append({
                    "type": "health_degradation",
                    "service": service_id,
                    "service_name": service.name,
                    "health_status": service.health_status.value,
                    "metrics": {
                        "latency_p99_ms": service.latency_p99_ms,
                        "error_rate": service.error_rate,
                        "cpu_percent": service.cpu_percent
                    }
                })

        # 3. 收集依赖边异常
        for edge_id, edge in service_map._edges.items():
            if edge.error_rate and edge.error_rate > 0.05:  # 错误率超过 5%
                symptoms.append({
                    "type": "dependency_degradation",
                    "edge_id": edge_id,
                    "source": edge.source_service,
                    "target": edge.target_service,
                    "error_rate": edge.error_rate,
                    "latency_p99_ms": edge.latency_p99_ms
                })

        logger.debug(f"Collected {len(symptoms)} symptoms")
        return symptoms

    def _identify_root_causes(
        self,
        symptoms: List[Dict[str, Any]],
        lookback_minutes: int
    ) -> List[RootCauseCandidate]:
        """识别根因候选"""
        root_causes = []
        service_scores: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "score": 0,
            "evidence": [],
            "anomaly_times": [],
            "types": set()
        })

        # 1. 分析每个服务的异常评分
        for symptom in symptoms:
            if symptom["type"] == "anomaly":
                service = symptom["service"]
                score_increase = self._calculate_anomaly_score(symptom)
                service_scores[service]["score"] += score_increase
                service_scores[service]["evidence"].append(
                    f"{symptom['metric']} 发生 {symptom['anomaly_type']} 异常 "
                    f"(当前值：{symptom['current_value']:.2f}, 预期值：{symptom['expected_value']:.2f})"
                )
                service_scores[service]["types"].add(RootCauseType.SERVICE_EXCEPTION)

            elif symptom["type"] == "health_degradation":
                service = symptom["service"]
                score_increase = self._calculate_health_score(symptom)
                service_scores[service]["score"] += score_increase
                service_scores[service]["evidence"].append(
                    f"服务健康状态恶化：{symptom['health_status']}"
                )
                service_scores[service]["types"].add(RootCauseType.SERVICE_EXCEPTION)

            elif symptom["type"] == "dependency_degradation":
                # 依赖边问题，优先归因于目标服务（被调用方）
                target = symptom["target"]
                score_increase = self._calculate_dependency_score(symptom)
                service_scores[target]["score"] += score_increase
                service_scores[target]["evidence"].append(
                    f"依赖 {symptom['source']} -> {symptom['target']} 错误率 {symptom['error_rate']:.2%}"
                )
                service_scores[target]["types"].add(RootCauseType.DEPENDENCY_FAILURE)

        # 2. 分析级联故障
        cascade_root_causes = self._detect_cascade_failures(service_scores)
        for crc in cascade_root_causes:
            root_causes.append(crc)

        # 3. 将高分服务转换为根因候选
        sorted_services = sorted(
            service_scores.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )

        for service_id, score_data in sorted_services[:10]:  # 最多取前 10 个
            if score_data["score"] < 0.3:  # 阈值过滤
                continue

            # 判断根因类型
            root_cause_type = self._determine_root_cause_type(service_id, score_data)

            # 计算置信度
            confidence = min(1.0, score_data["score"] / 3.0)
            confidence_level = self._map_confidence_level(confidence)

            # 确定影响范围
            impact_scope = self._calculate_impact_scope(service_id)

            # 生成建议操作
            suggested_actions = self._generate_suggested_actions(root_cause_type, service_id, score_data)

            root_causes.append(RootCauseCandidate(
                id=f"rc-{service_id}-{int(datetime.utcnow().timestamp())}",
                service_id=service_id,
                service_name=service_map.get_service(service_id).name if service_map.get_service(service_id) else service_id,
                root_cause_type=root_cause_type,
                confidence=confidence,
                confidence_level=confidence_level,
                evidence=score_data["evidence"][:5],  # 最多 5 条证据
                impact_scope=impact_scope,
                suggested_actions=suggested_actions
            ))

        return root_causes

    def _calculate_anomaly_score(self, symptom: Dict[str, Any]) -> float:
        """计算异常评分"""
        base_score = 0.5

        # 根据异常严重程度调整
        severity_scores = {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.5,
            "low": 0.3
        }
        severity_score = severity_scores.get(symptom.get("severity", "medium"), 0.5)

        # 根据偏离程度调整
        deviation = abs(symptom.get("deviation", 0))
        deviation_factor = min(2.0, 1 + deviation / 100)

        return base_score * severity_score * deviation_factor

    def _calculate_health_score(self, symptom: Dict[str, Any]) -> float:
        """计算健康状态评分"""
        health_scores = {
            "unhealthy": 1.0,
            "degraded": 0.6,
            "healthy": 0
        }
        return health_scores.get(symptom.get("health_status", "healthy"), 0)

    def _calculate_dependency_score(self, symptom: Dict[str, Any]) -> float:
        """计算依赖异常评分"""
        error_rate = symptom.get("error_rate", 0)
        # 错误率越高，评分越高
        return min(1.5, error_rate * 10)

    def _detect_cascade_failures(
        self,
        service_scores: Dict[str, Dict[str, Any]]
    ) -> List[RootCauseCandidate]:
        """检测级联故障"""
        cascade_causes = []

        # 查找多个上游服务同时异常的情况
        high_score_services = [
            (sid, data) for sid, data in service_scores.items()
            if data["score"] > 0.5
        ]

        if len(high_score_services) < 2:
            return cascade_causes

        # 检查是否有共同的依赖
        common_dependencies: Dict[str, List[str]] = defaultdict(list)
        for service_id, _ in high_score_services:
            downstream = service_map.get_downstream_services(service_id)
            for dep in downstream:
                common_dependencies[dep].append(service_id)

        # 如果某个依赖被多个异常服务共享，可能是级联故障的根源
        for dep, affected_services in common_dependencies.items():
            if len(affected_services) >= 2:
                dep_service = service_map.get_service(dep)
                if dep_service and dep_service.health_status == HealthStatus.UNHEALTHY:
                    cascade_causes.append(RootCauseCandidate(
                        id=f"cascade-{dep}-{int(datetime.utcnow().timestamp())}",
                        service_id=dep,
                        service_name=dep_service.name,
                        root_cause_type=RootCauseType.CASCADE_FAILURE,
                        confidence=0.8,
                        confidence_level=ConfidenceLevel.HIGH,
                        evidence=[
                            f"下游服务 {', '.join(affected_services)} 同时异常",
                            f"怀疑 {dep} 故障导致级联影响"
                        ],
                        impact_scope=affected_services + [dep],
                        suggested_actions=[
                            f"检查 {dep} 的服务日志和指标",
                            "考虑降级或熔断下游调用",
                            "检查资源使用情况（CPU、内存、连接池）"
                        ]
                    ))

        return cascade_causes

    def _determine_root_cause_type(
        self,
        service_id: str,
        score_data: Dict[str, Any]
    ) -> RootCauseType:
        """确定根因类型"""
        service = service_map.get_service(service_id)
        if not service:
            return RootCauseType.SERVICE_EXCEPTION

        # 检查是否是资源耗尽
        if service.cpu_percent and service.cpu_percent > 90:
            return RootCauseType.RESOURCE_EXHAUSTION
        if service.memory_mb and service.memory_mb > service.memory_mb * 0.9:
            return RootCauseType.RESOURCE_EXHAUSTION

        # 检查是否是数据库问题
        if service.type == "database":
            return RootCauseType.DATABASE_ISSUE

        # 检查是否有依赖故障
        if RootCauseType.DEPENDENCY_FAILURE in score_data["types"]:
            return RootCauseType.DEPENDENCY_FAILURE

        return RootCauseType.SERVICE_EXCEPTION

    def _calculate_impact_scope(self, service_id: str) -> List[str]:
        """计算影响范围"""
        affected = set()

        # 上游服务会受到影响
        upstream = service_map.get_upstream_services(service_id)
        affected.update(upstream)

        # 递归查找所有上游
        to_check = list(upstream)
        while to_check:
            current = to_check.pop(0)
            more_upstream = service_map.get_upstream_services(current)
            for s in more_upstream:
                if s not in affected:
                    affected.add(s)
                    to_check.append(s)

        return list(affected)

    def _generate_suggested_actions(
        self,
        root_cause_type: RootCauseType,
        service_id: str,
        score_data: Dict[str, Any]
    ) -> List[str]:
        """生成建议操作"""
        actions = []

        if root_cause_type == RootCauseType.RESOURCE_EXHAUSTION:
            actions.extend([
                f"检查 {service_id} 的资源使用情况（CPU、内存、磁盘、网络）",
                "考虑扩容或优化资源使用",
                "检查是否有资源泄漏",
                "分析近期流量变化"
            ])
        elif root_cause_type == RootCauseType.DATABASE_ISSUE:
            actions.extend([
                f"检查 {service_id} 数据库的连接数和查询性能",
                "分析慢查询日志",
                "检查锁等待和死锁情况",
                "考虑优化索引或查询语句"
            ])
        elif root_cause_type == RootCauseType.DEPENDENCY_FAILURE:
            actions.extend([
                f"检查 {service_id} 的下游依赖服务状态",
                "实施熔断器模式防止级联故障",
                "考虑增加重试和降级策略",
                "分析依赖调用的错误类型"
            ])
        elif root_cause_type == RootCauseType.CASCADE_FAILURE:
            actions.extend([
                f"优先恢复 {service_id} 服务",
                "检查服务的依赖关系图",
                "实施隔离策略限制故障传播",
                "事后进行故障复盘"
            ])
        else:
            actions.extend([
                f"检查 {service_id} 的应用日志",
                "分析最近的部署或配置变更",
                "查看相关指标趋势",
                "必要时进行服务重启或回滚"
            ])

        return actions

    def _map_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """映射置信度等级"""
        if confidence > 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif confidence > 0.7:
            return ConfidenceLevel.HIGH
        elif confidence > 0.5:
            return ConfidenceLevel.MEDIUM
        elif confidence > 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    def _analyze_propagation_paths(
        self,
        root_causes: List[RootCauseCandidate]
    ) -> List[PropagationPath]:
        """分析异常传播路径"""
        propagation_paths = []

        for rc in root_causes:
            # 从根因服务开始，查找传播路径
            for affected_service in rc.impact_scope:
                if affected_service == rc.service_id:
                    continue

                # 使用 service_map 查找路径
                paths = service_map.find_paths(affected_service, rc.service_id, max_depth=5)

                for path in paths:
                    propagation_paths.append(PropagationPath(
                        source_service=rc.service_id,
                        target_service=affected_service,
                        path=path.path,
                        propagation_type="cascade",
                        total_latency_impact_ms=path.total_latency_ms,
                        total_error_rate_impact=path.total_error_rate,
                        affected_services=path.path
                    ))

        # 去重和排序
        seen = set()
        unique_paths = []
        for pp in propagation_paths:
            key = f"{pp.source_service}->{pp.target_service}"
            if key not in seen:
                seen.add(key)
                unique_paths.append(pp)

        return sorted(unique_paths, key=lambda p: p.total_latency_impact_ms, reverse=True)[:10]

    def _analyze_correlations(
        self,
        symptoms: List[Dict[str, Any]],
        lookback_minutes: int
    ) -> List[CorrelationAnalysis]:
        """执行关联分析"""
        correlations = []

        # 收集所有异常的指标
        metric_services = set()
        for symptom in symptoms:
            if symptom["type"] == "anomaly":
                metric_services.add((symptom["service"], symptom["metric"]))

        # 两两分析关联性（简化实现）
        metric_list = list(metric_services)[:10]  # 限制分析数量
        for i, (service_a, metric_a) in enumerate(metric_list):
            for service_b, metric_b in metric_list[i+1:]:
                # 简化实现：基于启发式规则判断相关性
                correlation = self._estimate_correlation(
                    service_a, metric_a, service_b, metric_b
                )
                if correlation and correlation.is_significant:
                    correlations.append(correlation)

        return correlations

    def _estimate_correlation(
        self,
        service_a: str,
        metric_a: str,
        service_b: str,
        metric_b: str
    ) -> Optional[CorrelationAnalysis]:
        """估算指标相关性（简化实现）"""
        # 获取两个指标的时间序列
        stats_a = anomaly_detector.get_time_series_stats(service_a, metric_a)
        stats_b = anomaly_detector.get_time_series_stats(service_b, metric_b)

        if not stats_a or not stats_b:
            return None

        # 简化相关性估计
        # 如果两个指标的 trend_slope 符号相同且接近，认为正相关
        slope_a = stats_a.trend_slope
        slope_b = stats_b.trend_slope

        if slope_a == 0 and slope_b == 0:
            return None

        # 计算相关系数（简化）
        if (slope_a > 0 and slope_b > 0) or (slope_a < 0 and slope_b < 0):
            correlation_coefficient = min(0.9, abs(slope_a) + abs(slope_b)) / (abs(slope_a) + abs(slope_b) + 0.1)
            correlation_type = "positive"
        else:
            correlation_coefficient = -min(0.9, abs(slope_a) + abs(slope_b)) / (abs(slope_a) + abs(slope_b) + 0.1)
            correlation_type = "negative"

        is_significant = abs(correlation_coefficient) > 0.5

        return CorrelationAnalysis(
            metric_a_service=service_a,
            metric_a_name=metric_a,
            metric_b_service=service_b,
            metric_b_name=metric_b,
            correlation_coefficient=correlation_coefficient,
            correlation_type=correlation_type,
            time_lag_seconds=0,  # 简化实现
            is_significant=is_significant
        )

    def _generate_summary_and_actions(
        self,
        root_causes: List[RootCauseCandidate],
        propagation_paths: List[PropagationPath],
        correlations: List[CorrelationAnalysis]
    ) -> Tuple[str, List[str]]:
        """生成总结和建议"""
        if not root_causes:
            return "未检测到明显的根因", ["继续监控系统指标", "检查是否有未监控的故障点"]

        # 找到最可能的根因
        top_root_cause = max(root_causes, key=lambda rc: rc.confidence)

        # 生成总结
        summary_parts = [
            f"检测到 {len(root_causes)} 个潜在根因",
            f"最可能的根因是 {top_root_cause.service_name} ({top_root_cause.root_cause_type.value})",
            f"置信度：{top_root_cause.confidence:.1%}"
        ]

        if propagation_paths:
            summary_parts.append(
                f"异常通过 {len(propagation_paths)} 条路径传播，影响 {len(set(s for p in propagation_paths for s in p.affected_services))} 个服务"
            )

        if correlations:
            summary_parts.append(
                f"发现 {len(correlations)} 个显著的指标相关性"
            )

        summary = ". ".join(summary_parts) + "."

        # 生成建议操作
        recommended_actions = top_root_cause.suggested_actions[:3]

        # 添加通用建议
        recommended_actions.extend([
            "查看相关服务的日志和监控指标",
            "必要时启动应急预案"
        ])

        return summary, recommended_actions

    def get_analysis_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取分析历史"""
        return [r.to_dict() for r in self._analysis_history[-limit:]]


# 全局根因分析器实例
root_cause_analyzer = RootCauseAnalyzer()
