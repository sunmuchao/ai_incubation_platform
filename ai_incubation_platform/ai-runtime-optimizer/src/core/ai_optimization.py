"""
AI 优化建议引擎 v2.5
基于 AI 的性能瓶颈分析、资源优化建议和成本优化
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading

logger = logging.getLogger(__name__)


# ============================================================================
# 数据模型
# ============================================================================

class OptimizationCategory(str, Enum):
    """优化类别"""
    PERFORMANCE = "performance"  # 性能优化
    RESOURCE = "resource"  # 资源优化
    COST = "cost"  # 成本优化
    RELIABILITY = "reliability"  # 可靠性优化


class OptimizationPriority(str, Enum):
    """优化优先级"""
    CRITICAL = "critical"  # 关键
    HIGH = "high"  # 高
    MEDIUM = "medium"  # 中
    LOW = "low"  # 低


class OptimizationType(str, Enum):
    """优化类型"""
    CODE_CHANGE = "code_change"  # 代码改动
    CONFIG_CHANGE = "config_change"  # 配置改动
    INFRASTRUCTURE = "infrastructure"  # 基础设施改动
    ARCHITECTURE = "architecture"  # 架构改动


@dataclass
class OptimizationRecommendation:
    """优化建议"""
    id: str
    category: OptimizationCategory
    priority: OptimizationPriority
    type: OptimizationType
    title: str
    description: str
    service_name: str
    current_state: Dict[str, Any]
    proposed_change: Dict[str, Any]
    expected_impact: Dict[str, Any]
    implementation_effort: str  # low/medium/high
    confidence_score: float  # 0-1
    evidence: List[str] = field(default_factory=list)
    code_snippet: Optional[str] = None
    config_snippet: Optional[str] = None
    references: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "category": self.category.value,
            "priority": self.priority.value,
            "type": self.type.value,
            "title": self.title,
            "description": self.description,
            "service_name": self.service_name,
            "current_state": self.current_state,
            "proposed_change": self.proposed_change,
            "expected_impact": self.expected_impact,
            "implementation_effort": self.implementation_effort,
            "confidence_score": self.confidence_score,
            "evidence": self.evidence,
            "code_snippet": self.code_snippet,
            "config_snippet": self.config_snippet,
            "references": self.references,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class PerformanceBottleneck:
    """性能瓶颈"""
    id: str
    service_name: str
    component: str  # cpu/memory/io/network/database/cache
    severity: str  # critical/high/medium/low
    description: str
    metrics: Dict[str, Any]
    root_cause: Optional[str]
    impact: Dict[str, Any]
    detected_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "service_name": self.service_name,
            "component": self.component,
            "severity": self.severity,
            "description": self.description,
            "metrics": self.metrics,
            "root_cause": self.root_cause,
            "impact": self.impact,
            "detected_at": self.detected_at.isoformat()
        }


@dataclass
class CostAnalysis:
    """成本分析"""
    service_name: str
    current_cost_estimate: float  # 预估当前成本（每月）
    optimized_cost_estimate: float  # 优化后预估成本
    savings_potential: float  # 节省潜力
    cost_breakdown: Dict[str, float]  # 成本细分
    recommendations: List[str]  # 成本优化建议
    analyzed_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "service_name": self.service_name,
            "current_cost_estimate": self.current_cost_estimate,
            "optimized_cost_estimate": self.optimized_cost_estimate,
            "savings_potential": self.savings_potential,
            "savings_percentage": round((self.savings_potential / self.current_cost_estimate) * 100, 2) if self.current_cost_estimate > 0 else 0,
            "cost_breakdown": self.cost_breakdown,
            "recommendations": self.recommendations,
            "analyzed_at": self.analyzed_at.isoformat()
        }


# ============================================================================
# 性能瓶颈分析器
# ============================================================================

class PerformanceBottleneckAnalyzer:
    """性能瓶颈分析器"""

    def __init__(self):
        self._bottlenecks: Dict[str, PerformanceBottleneck] = {}
        self._lock = threading.Lock()

        # 阈值配置
        self._thresholds = {
            "cpu_critical": 90,
            "cpu_high": 75,
            "memory_critical": 90,
            "memory_high": 80,
            "latency_critical": 1000,  # ms
            "latency_high": 500,  # ms
            "error_rate_critical": 5,  # %
            "error_rate_high": 1,  # %
            "gc_overhead_critical": 30,  # %
            "gc_overhead_high": 15,  # %
        }

    def analyze(self, service_name: str, metrics: Dict[str, Any]) -> List[PerformanceBottleneck]:
        """分析性能瓶颈"""
        bottlenecks = []

        # CPU 分析
        cpu_bottleneck = self._analyze_cpu(service_name, metrics)
        if cpu_bottleneck:
            bottlenecks.append(cpu_bottleneck)

        # 内存分析
        memory_bottleneck = self._analyze_memory(service_name, metrics)
        if memory_bottleneck:
            bottlenecks.append(memory_bottleneck)

        # 延迟分析
        latency_bottleneck = self._analyze_latency(service_name, metrics)
        if latency_bottleneck:
            bottlenecks.append(latency_bottleneck)

        # 错误率分析
        error_bottleneck = self._analyze_error_rate(service_name, metrics)
        if error_bottleneck:
            bottlenecks.append(error_bottleneck)

        # GC 分析（JVM 应用）
        gc_bottleneck = self._analyze_gc(service_name, metrics)
        if gc_bottleneck:
            bottlenecks.append(gc_bottleneck)

        # 存储瓶颈
        with self._lock:
            for bottleneck in bottlenecks:
                self._bottlenecks[bottleneck.id] = bottleneck

        return bottlenecks

    def _analyze_cpu(self, service_name: str, metrics: Dict[str, Any]) -> Optional[PerformanceBottleneck]:
        """CPU 瓶颈分析"""
        cpu_percent = metrics.get("cpu_percent", 0)

        if cpu_percent >= self._thresholds["cpu_critical"]:
            severity = "critical"
        elif cpu_percent >= self._thresholds["cpu_high"]:
            severity = "high"
        else:
            return None

        return PerformanceBottleneck(
            id=f"bottleneck_cpu_{service_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            service_name=service_name,
            component="cpu",
            severity=severity,
            description=f"CPU 使用率持续处于{severity}水平 ({cpu_percent:.1f}%)",
            metrics={
                "cpu_percent": cpu_percent,
                "threshold_critical": self._thresholds["cpu_critical"],
                "threshold_high": self._thresholds["cpu_high"]
            },
            root_cause=self._diagnose_cpu_cause(metrics),
            impact={
                "response_time": "增加",
                "throughput": "可能下降",
                "user_experience": "受影响"
            }
        )

    def _analyze_memory(self, service_name: str, metrics: Dict[str, Any]) -> Optional[PerformanceBottleneck]:
        """内存瓶颈分析"""
        memory_percent = metrics.get("memory_percent", 0)
        memory_mb = metrics.get("memory_mb", 0)

        if memory_percent >= self._thresholds["memory_critical"]:
            severity = "critical"
        elif memory_percent >= self._thresholds["memory_high"]:
            severity = "high"
        else:
            return None

        return PerformanceBottleneck(
            id=f"bottleneck_memory_{service_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            service_name=service_name,
            component="memory",
            severity=severity,
            description=f"内存使用率持续处于{severity}水平 ({memory_percent:.1f}%)",
            metrics={
                "memory_percent": memory_percent,
                "memory_mb": memory_mb,
                "threshold_critical": self._thresholds["memory_critical"],
                "threshold_high": self._thresholds["memory_high"]
            },
            root_cause=self._diagnose_memory_cause(metrics),
            impact={
                "gc_pressure": "增加",
                "oom_risk": "高" if memory_percent > 95 else "中",
                "performance": "可能下降"
            }
        )

    def _analyze_latency(self, service_name: str, metrics: Dict[str, Any]) -> Optional[PerformanceBottleneck]:
        """延迟瓶颈分析"""
        latency_p99 = metrics.get("latency_p99_ms", 0)
        latency_p95 = metrics.get("latency_p95_ms", 0)
        latency_avg = metrics.get("latency_avg_ms", 0)

        if latency_p99 >= self._thresholds["latency_critical"]:
            severity = "critical"
        elif latency_p99 >= self._thresholds["latency_high"]:
            severity = "high"
        else:
            return None

        return PerformanceBottleneck(
            id=f"bottleneck_latency_{service_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            service_name=service_name,
            component="latency",
            severity=severity,
            description=f"请求延迟达到{severity}水平 (P99: {latency_p99:.0f}ms)",
            metrics={
                "latency_p99_ms": latency_p99,
                "latency_p95_ms": latency_p95,
                "latency_avg_ms": latency_avg,
                "threshold_critical": self._thresholds["latency_critical"],
                "threshold_high": self._thresholds["latency_high"]
            },
            root_cause=self._diagnose_latency_cause(metrics),
            impact={
                "user_experience": "显著下降",
                "conversion_rate": "可能下降",
                "sla_compliance": "风险"
            }
        )

    def _analyze_error_rate(self, service_name: str, metrics: Dict[str, Any]) -> Optional[PerformanceBottleneck]:
        """错误率瓶颈分析"""
        error_rate = metrics.get("error_rate", 0)

        if error_rate >= self._thresholds["error_rate_critical"]:
            severity = "critical"
        elif error_rate >= self._thresholds["error_rate_high"]:
            severity = "high"
        else:
            return None

        return PerformanceBottleneck(
            id=f"bottleneck_error_{service_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            service_name=service_name,
            component="error_rate",
            severity=severity,
            description=f"错误率达到{severity}水平 ({error_rate:.2f}%)",
            metrics={
                "error_rate": error_rate,
                "threshold_critical": self._thresholds["error_rate_critical"],
                "threshold_high": self._thresholds["error_rate_high"]
            },
            root_cause="需要进一步分析日志确定具体原因",
            impact={
                "user_experience": "严重受影响",
                "data_integrity": "可能受影响",
                "system_reliability": "下降"
            }
        )

    def _analyze_gc(self, service_name: str, metrics: Dict[str, Any]) -> Optional[PerformanceBottleneck]:
        """GC 瓶颈分析（JVM 应用）"""
        gc_overhead = metrics.get("gc_overhead_percent", 0)
        gc_pause_ms = metrics.get("gc_pause_ms", 0)

        if gc_overhead >= self._thresholds["gc_overhead_critical"]:
            severity = "critical"
        elif gc_overhead >= self._thresholds["gc_overhead_high"]:
            severity = "high"
        else:
            return None

        return PerformanceBottleneck(
            id=f"bottleneck_gc_{service_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            service_name=service_name,
            component="gc",
            severity=severity,
            description=f"GC 开销达到{severity}水平 (开销：{gc_overhead:.1f}%, 暂停：{gc_pause_ms:.0f}ms)",
            metrics={
                "gc_overhead_percent": gc_overhead,
                "gc_pause_ms": gc_pause_ms,
                "threshold_critical": self._thresholds["gc_overhead_critical"],
                "threshold_high": self._thresholds["gc_overhead_high"]
            },
            root_cause="可能是堆内存不足或 GC 配置不当",
            impact={
                "throughput": f"下降约{gc_overhead:.0f}%",
                "latency": f"GC 暂停导致延迟增加 {gc_pause_ms:.0f}ms",
                "user_experience": "卡顿"
            }
        )

    def _diagnose_cpu_cause(self, metrics: Dict[str, Any]) -> str:
        """诊断 CPU 问题原因"""
        # 简化实现，实际需要更复杂的分析
        if metrics.get("thread_count", 0) > 100:
            return "可能是线程过多导致上下文切换频繁"
        if metrics.get("load_average", 0) > metrics.get("cpu_cores", 1) * 2:
            return "系统负载过高，可能存在计算密集型操作"
        return "需要进一步分析确定具体原因"

    def _diagnose_memory_cause(self, metrics: Dict[str, Any]) -> str:
        """诊断内存问题原因"""
        if metrics.get("heap_usage_percent", 0) > 90:
            return "堆内存使用率过高，可能存在内存泄漏"
        if metrics.get("non_heap_usage_percent", 0) > 80:
            return "非堆内存使用率过高，可能是元空间或直接缓冲区问题"
        return "需要进一步分析确定具体原因"

    def _diagnose_latency_cause(self, metrics: Dict[str, Any]) -> str:
        """诊断延迟问题原因"""
        if metrics.get("db_query_time_ms", 0) > 100:
            return "数据库查询耗时较长"
        if metrics.get("external_api_time_ms", 0) > 200:
            return "外部 API 调用耗时较长"
        if metrics.get("cache_hit_rate", 100) < 50:
            return "缓存命中率低"
        return "需要进一步分析确定具体原因"

    def get_bottlenecks(self, service_name: Optional[str] = None, severity: Optional[str] = None) -> List[PerformanceBottleneck]:
        """获取瓶颈列表"""
        with self._lock:
            bottlenecks = list(self._bottlenecks.values())

        if service_name:
            bottlenecks = [b for b in bottlenecks if b.service_name == service_name]
        if severity:
            bottlenecks = [b for b in bottlenecks if b.severity == severity]

        return sorted(bottlenecks, key=lambda b: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(b.severity, 4))


# ============================================================================
# AI 优化建议引擎
# ============================================================================

class AIOptimizationEngine:
    """AI 优化建议引擎"""

    def __init__(self, llm_enabled: bool = False):
        self._bottleneck_analyzer = PerformanceBottleneckAnalyzer()
        self._recommendations: Dict[str, OptimizationRecommendation] = {}
        self._cost_analyses: Dict[str, CostAnalysis] = {}
        self._llm_enabled = llm_enabled
        self._lock = threading.Lock()

        # 优化规则库
        self._optimization_rules = self._init_optimization_rules()

    def _init_optimization_rules(self) -> List[Dict[str, Any]]:
        """初始化优化规则库"""
        return [
            # CPU 优化规则
            {
                "id": "cpu-001",
                "category": OptimizationCategory.PERFORMANCE,
                "condition": lambda m: m.get("cpu_percent", 0) > 75,
                "recommendation": self._generate_cpu_optimization,
                "priority": OptimizationPriority.HIGH
            },
            # 内存优化规则
            {
                "id": "memory-001",
                "category": OptimizationCategory.RESOURCE,
                "condition": lambda m: m.get("memory_percent", 0) > 80,
                "recommendation": self._generate_memory_optimization,
                "priority": OptimizationPriority.HIGH
            },
            # 缓存优化规则
            {
                "id": "cache-001",
                "category": OptimizationCategory.PERFORMANCE,
                "condition": lambda m: m.get("cache_hit_rate", 100) < 70,
                "recommendation": self._generate_cache_optimization,
                "priority": OptimizationPriority.MEDIUM
            },
            # 数据库优化规则
            {
                "id": "db-001",
                "category": OptimizationCategory.PERFORMANCE,
                "condition": lambda m: m.get("db_query_time_ms", 0) > 100,
                "recommendation": self._generate_db_optimization,
                "priority": OptimizationPriority.HIGH
            },
            # 成本优化规则
            {
                "id": "cost-001",
                "category": OptimizationCategory.COST,
                "condition": lambda m: m.get("cpu_percent", 0) < 30 and m.get("memory_percent", 0) < 30,
                "recommendation": self._generate_cost_optimization,
                "priority": OptimizationPriority.LOW
            }
        ]

    def analyze(self, service_name: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """综合分析并生成优化建议"""
        results = {
            "service_name": service_name,
            "analyzed_at": datetime.utcnow().isoformat(),
            "bottlenecks": [],
            "recommendations": [],
            "cost_analysis": None
        }

        # 1. 性能瓶颈分析
        bottlenecks = self._bottleneck_analyzer.analyze(service_name, metrics)
        results["bottlenecks"] = [b.to_dict() for b in bottlenecks]

        # 2. 基于规则生成优化建议
        recommendations = self._generate_recommendations(service_name, metrics, bottlenecks)
        results["recommendations"] = [r.to_dict() for r in recommendations]

        # 3. 成本分析
        cost_analysis = self._analyze_cost(service_name, metrics)
        results["cost_analysis"] = cost_analysis.to_dict()

        return results

    def _generate_recommendations(
        self,
        service_name: str,
        metrics: Dict[str, Any],
        bottlenecks: List[PerformanceBottleneck]
    ) -> List[OptimizationRecommendation]:
        """生成优化建议"""
        recommendations = []

        # 基于瓶颈生成建议
        for bottleneck in bottlenecks:
            rec = self._create_recommendation_for_bottleneck(service_name, bottleneck, metrics)
            if rec:
                recommendations.append(rec)
                # 存储建议
                with self._lock:
                    self._recommendations[rec.id] = rec

        # 基于规则生成建议
        for rule in self._optimization_rules:
            try:
                if rule["condition"](metrics):
                    rec_func = rule["recommendation"]
                    rec = rec_func(service_name, metrics)
                    if rec:
                        recommendations.append(rec)
                        # 存储建议
                        with self._lock:
                            self._recommendations[rec.id] = rec
            except Exception as e:
                logger.debug(f"Rule evaluation failed: {e}")

        # 去重（基于标题）
        seen_titles = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec.title not in seen_titles:
                seen_titles.add(rec.title)
                unique_recommendations.append(rec)

        return unique_recommendations

    def _create_recommendation_for_bottleneck(
        self,
        service_name: str,
        bottleneck: PerformanceBottleneck,
        metrics: Dict[str, Any]
    ) -> Optional[OptimizationRecommendation]:
        """为瓶颈创建优化建议"""
        rec_map = {
            "cpu": self._generate_cpu_optimization,
            "memory": self._generate_memory_optimization,
            "latency": self._generate_latency_optimization,
            "error_rate": self._generate_error_rate_optimization,
            "gc": self._generate_gc_optimization
        }

        generator = rec_map.get(bottleneck.component)
        if generator:
            return generator(service_name, metrics, bottleneck)
        return None

    def _generate_cpu_optimization(
        self,
        service_name: str,
        metrics: Dict[str, Any],
        bottleneck: Optional[PerformanceBottleneck] = None
    ) -> OptimizationRecommendation:
        """生成 CPU 优化建议"""
        cpu_percent = metrics.get("cpu_percent", 0)

        return OptimizationRecommendation(
            id=f"opt_cpu_{service_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            category=OptimizationCategory.PERFORMANCE,
            priority=OptimizationPriority.HIGH if cpu_percent > 85 else OptimizationPriority.MEDIUM,
            type=OptimizationType.CODE_CHANGE,
            title="CPU 使用率优化",
            description=f"当前 CPU 使用率为{cpu_percent:.1f}%，建议进行优化",
            service_name=service_name,
            current_state={"cpu_percent": cpu_percent},
            proposed_change={
                "actions": [
                    "使用性能分析工具（如 async-profiler）定位 CPU 热点",
                    "优化计算密集型代码路径",
                    "考虑使用并发处理",
                    "评估是否需要水平扩展"
                ]
            },
            expected_impact={
                "cpu_reduction": "20-40%",
                "response_time": "降低 15-30%",
                "throughput": "提升 20-50%"
            },
            implementation_effort="medium",
            confidence_score=0.85,
            evidence=[f"CPU 使用率：{cpu_percent:.1f}%"],
            code_snippet="""// 优化示例：使用并行流处理
// 优化前
list.stream().map(this::process).collect(Collectors.toList());

// 优化后（如果处理是 CPU 密集型且无状态）
list.parallelStream().map(this::process).collect(Collectors.toList());""",
            references=[
                "https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/stream/Stream.html#parallel-streams",
            ]
        )

    def _generate_memory_optimization(
        self,
        service_name: str,
        metrics: Dict[str, Any],
        bottleneck: Optional[PerformanceBottleneck] = None
    ) -> OptimizationRecommendation:
        """生成内存优化建议"""
        memory_percent = metrics.get("memory_percent", 0)

        return OptimizationRecommendation(
            id=f"opt_memory_{service_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            category=OptimizationCategory.RESOURCE,
            priority=OptimizationPriority.HIGH if memory_percent > 90 else OptimizationPriority.MEDIUM,
            type=OptimizationType.CODE_CHANGE,
            title="内存使用优化",
            description=f"当前内存使用率为{memory_percent:.1f}%，建议进行优化",
            service_name=service_name,
            current_state={"memory_percent": memory_percent},
            proposed_change={
                "actions": [
                    "使用内存分析工具（如 JProfiler）检测内存泄漏",
                    "优化大数据对象的生命周期",
                    "使用对象池减少分配",
                    "调整 JVM 堆大小参数"
                ]
            },
            expected_impact={
                "memory_reduction": "20-30%",
                "gc_pause": "减少 30-50%",
                "stability": "提升"
            },
            implementation_effort="medium",
            confidence_score=0.8,
            evidence=[f"内存使用率：{memory_percent:.1f}%"],
            config_snippet="""# JVM 内存配置优化
-Xms4g -Xmx4g              # 设置固定堆大小避免动态扩展
-XX:MetaspaceSize=256m     # 设置元空间初始大小
-XX:MaxMetaspaceSize=512m  # 设置元空间上限
-XX:+UseG1GC               # 使用 G1 垃圾收集器""",
            references=[
                "https://docs.oracle.com/en/java/javase/17/gctuning/introduction-garbage-collection-tuning.html"
            ]
        )

    def _generate_latency_optimization(
        self,
        service_name: str,
        metrics: Dict[str, Any],
        bottleneck: Optional[PerformanceBottleneck] = None
    ) -> OptimizationRecommendation:
        """生成延迟优化建议"""
        latency_p99 = metrics.get("latency_p99_ms", 0)

        return OptimizationRecommendation(
            id=f"opt_latency_{service_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            category=OptimizationCategory.PERFORMANCE,
            priority=OptimizationPriority.HIGH,
            type=OptimizationType.ARCHITECTURE,
            title="请求延迟优化",
            description=f"当前 P99 延迟为{latency_p99:.0f}ms，建议进行优化",
            service_name=service_name,
            current_state={"latency_p99_ms": latency_p99},
            proposed_change={
                "actions": [
                    "分析慢调用链，定位延迟来源",
                    "优化数据库查询（添加索引、优化 SQL）",
                    "引入/优化缓存策略",
                    "考虑异步处理非关键路径"
                ]
            },
            expected_impact={
                "latency_reduction": "30-50%",
                "user_experience": "显著改善",
                "conversion_rate": "可能提升"
            },
            implementation_effort="medium",
            confidence_score=0.75,
            evidence=[f"P99 延迟：{latency_p99:.0f}ms"]
        )

    def _generate_error_rate_optimization(
        self,
        service_name: str,
        metrics: Dict[str, Any],
        bottleneck: Optional[PerformanceBottleneck] = None
    ) -> OptimizationRecommendation:
        """生成错误率优化建议"""
        error_rate = metrics.get("error_rate", 0)

        return OptimizationRecommendation(
            id=f"opt_error_{service_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            category=OptimizationCategory.RELIABILITY,
            priority=OptimizationPriority.CRITICAL,
            type=OptimizationType.CODE_CHANGE,
            title="错误率优化",
            description=f"当前错误率为{error_rate:.2f}%，需要立即处理",
            service_name=service_name,
            current_state={"error_rate": error_rate},
            proposed_change={
                "actions": [
                    "分析错误日志，确定错误类型和来源",
                    "添加/完善异常处理",
                    "实现重试机制（对于 transient errors）",
                    "添加熔断器保护"
                ]
            },
            expected_impact={
                "error_reduction": "50-80%",
                "reliability": "显著提升",
                "user_satisfaction": "提升"
            },
            implementation_effort="medium",
            confidence_score=0.9,
            evidence=[f"错误率：{error_rate:.2f}%"],
            code_snippet="""// 添加熔断器保护
@CircuitBreaker(name = "externalService", fallbackMethod = "fallback")
public Response callExternalService() {
    return externalService.call();
}

public Response fallback(Exception e) {
    return Response.cached();
}""",
            references=[
                "https://resilience4j.readme.io/docs/circuitbreaker"
            ]
        )

    def _generate_gc_optimization(
        self,
        service_name: str,
        metrics: Dict[str, Any],
        bottleneck: Optional[PerformanceBottleneck] = None
    ) -> OptimizationRecommendation:
        """生成 GC 优化建议"""
        gc_overhead = metrics.get("gc_overhead_percent", 0)
        gc_pause_ms = metrics.get("gc_pause_ms", 0)

        return OptimizationRecommendation(
            id=f"opt_gc_{service_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            category=OptimizationCategory.PERFORMANCE,
            priority=OptimizationPriority.HIGH,
            type=OptimizationType.CONFIG_CHANGE,
            title="GC 优化",
            description=f"GC 开销{gc_overhead:.1f}%，暂停{gc_pause_ms:.0f}ms，建议优化",
            service_name=service_name,
            current_state={"gc_overhead_percent": gc_overhead, "gc_pause_ms": gc_pause_ms},
            proposed_change={
                "actions": [
                    "调整堆内存大小",
                    "选择合适的垃圾收集器（G1/ZGC）",
                    "优化 GC 参数",
                    "减少对象分配速率"
                ]
            },
            expected_impact={
                "gc_overhead_reduction": "50-70%",
                "pause_time_reduction": "60-80%",
                "throughput": "提升 10-20%"
            },
            implementation_effort="low",
            confidence_score=0.85,
            config_snippet="""# G1 GC 优化配置
-XX:+UseG1GC
-XX:MaxGCPauseMillis=200
-XX:G1HeapRegionSize=16m
-XX:InitiatingHeapOccupancyPercent=45
-XX:G1ReservePercent=10""",
            references=[
                "https://docs.oracle.com/en/java/javase/17/gctuning/garbage-first-g1-garbage-collector.html"
            ]
        )

    def _generate_cache_optimization(
        self,
        service_name: str,
        metrics: Dict[str, Any]
    ) -> OptimizationRecommendation:
        """生成缓存优化建议"""
        cache_hit_rate = metrics.get("cache_hit_rate", 100)

        return OptimizationRecommendation(
            id=f"opt_cache_{service_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            category=OptimizationCategory.PERFORMANCE,
            priority=OptimizationPriority.MEDIUM,
            type=OptimizationType.ARCHITECTURE,
            title="缓存优化",
            description=f"当前缓存命中率为{cache_hit_rate:.1f}%，建议提升",
            service_name=service_name,
            current_state={"cache_hit_rate": cache_hit_rate},
            proposed_change={
                "actions": [
                    "分析缓存未命中的 key 模式",
                    "优化缓存过期策略",
                    "增加热点数据预加载",
                    "考虑多级缓存架构"
                ]
            },
            expected_impact={
                "hit_rate_improvement": "提升至 85%+",
                "database_load": "减少 30-50%",
                "response_time": "降低 20-40%"
            },
            implementation_effort="medium",
            confidence_score=0.8,
            evidence=[f"缓存命中率：{cache_hit_rate:.1f}%"]
        )

    def _generate_db_optimization(
        self,
        service_name: str,
        metrics: Dict[str, Any]
    ) -> OptimizationRecommendation:
        """生成数据库优化建议"""
        db_query_time = metrics.get("db_query_time_ms", 0)

        return OptimizationRecommendation(
            id=f"opt_db_{service_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            category=OptimizationCategory.PERFORMANCE,
            priority=OptimizationPriority.HIGH,
            type=OptimizationType.CODE_CHANGE,
            title="数据库查询优化",
            description=f"平均查询耗时{db_query_time:.0f}ms，建议优化",
            service_name=service_name,
            current_state={"db_query_time_ms": db_query_time},
            proposed_change={
                "actions": [
                    "使用慢查询日志定位问题 SQL",
                    "添加/优化索引",
                    "优化 SQL 语句（避免 N+1 查询）",
                    "考虑读写分离"
                ]
            },
            expected_impact={
                "query_time_reduction": "50-80%",
                "database_load": "减少 30-50%",
                "response_time": "降低 20-40%"
            },
            implementation_effort="medium",
            confidence_score=0.85,
            code_snippet="""-- 添加索引示例
CREATE INDEX idx_orders_user_status ON orders(user_id, status);

-- 优化查询，避免 N+1
-- 优化前：在循环中查询
SELECT * FROM orders WHERE user_id = ?;

-- 优化后：批量查询
SELECT * FROM orders WHERE user_id IN (?, ?, ?);""",
            references=[
                "https://use-the-index-luke.com/"
            ]
        )

    def _generate_cost_optimization(
        self,
        service_name: str,
        metrics: Dict[str, Any]
    ) -> OptimizationRecommendation:
        """生成成本优化建议"""
        cpu_percent = metrics.get("cpu_percent", 0)
        memory_percent = metrics.get("memory_percent", 0)

        return OptimizationRecommendation(
            id=f"opt_cost_{service_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            category=OptimizationCategory.COST,
            priority=OptimizationPriority.LOW,
            type=OptimizationType.INFRASTRUCTURE,
            title="资源成本优化",
            description=f"资源使用率较低（CPU: {cpu_percent:.1f}%, Memory: {memory_percent:.1f}%）",
            service_name=service_name,
            current_state={"cpu_percent": cpu_percent, "memory_percent": memory_percent},
            proposed_change={
                "actions": [
                    "缩减实例规格（rightsizing）",
                    "启用自动扩缩容",
                    "考虑使用 Spot 实例",
                    "合并低负载服务"
                ]
            },
            expected_impact={
                "cost_savings": "30-50%",
                "resource_efficiency": "提升"
            },
            implementation_effort="low",
            confidence_score=0.9,
            evidence=[
                f"CPU 使用率：{cpu_percent:.1f}%",
                f"内存使用率：{memory_percent:.1f}%"
            ]
        )

    def _analyze_cost(self, service_name: str, metrics: Dict[str, Any]) -> CostAnalysis:
        """成本分析（简化实现）"""
        # 简化成本计算（实际需要云厂商 API 集成）
        cpu_percent = metrics.get("cpu_percent", 50)
        memory_percent = metrics.get("memory_percent", 50)

        # 假设基础成本
        base_cost = 1000  # 每月 USD

        # 根据资源使用估算
        estimated_cost = base_cost * (0.3 + 0.35 * cpu_percent / 100 + 0.35 * memory_percent / 100)

        # 优化后成本（如果资源利用率低，可以缩减）
        if cpu_percent < 30 and memory_percent < 30:
            optimized_cost = estimated_cost * 0.6  # 可以缩减 40%
        elif cpu_percent < 50 and memory_percent < 50:
            optimized_cost = estimated_cost * 0.8  # 可以缩减 20%
        else:
            optimized_cost = estimated_cost

        return CostAnalysis(
            service_name=service_name,
            current_cost_estimate=round(estimated_cost, 2),
            optimized_cost_estimate=round(optimized_cost, 2),
            savings_potential=round(estimated_cost - optimized_cost, 2),
            cost_breakdown={
                "compute": round(estimated_cost * 0.6, 2),
                "memory": round(estimated_cost * 0.3, 2),
                "storage": round(estimated_cost * 0.1, 2)
            },
            recommendations=self._generate_cost_recommendations(cpu_percent, memory_percent)
        )

    def _generate_cost_recommendations(self, cpu_percent: float, memory_percent: float) -> List[str]:
        """生成成本优化建议"""
        recommendations = []

        if cpu_percent < 30:
            recommendations.append("考虑缩减 CPU 配置（当前使用率低于 30%）")
        if memory_percent < 30:
            recommendations.append("考虑缩减内存配置（当前使用率低于 30%）")
        if cpu_percent < 50 and memory_percent < 50:
            recommendations.append("考虑合并服务实例")
        if cpu_percent > 80 or memory_percent > 80:
            recommendations.append("资源使用率高，不建议缩减")

        return recommendations if recommendations else ["当前资源配置合理"]

    def get_recommendations(
        self,
        service_name: Optional[str] = None,
        category: Optional[OptimizationCategory] = None,
        priority: Optional[OptimizationPriority] = None,
        limit: int = 50
    ) -> List[OptimizationRecommendation]:
        """获取优化建议"""
        with self._lock:
            recs = list(self._recommendations.values())

        if service_name:
            recs = [r for r in recs if r.service_name == service_name]
        if category:
            recs = [r for r in recs if r.category == category]
        if priority:
            recs = [r for r in recs if r.priority == priority]

        return sorted(recs, key=lambda r: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(r.priority.value, 4))[:limit]


# 全局优化引擎实例
global_optimization_engine: Optional[AIOptimizationEngine] = None


def get_optimization_engine(llm_enabled: bool = False) -> AIOptimizationEngine:
    """获取或创建优化引擎实例"""
    global global_optimization_engine
    if global_optimization_engine is None:
        global_optimization_engine = AIOptimizationEngine(llm_enabled=llm_enabled)
    return global_optimization_engine
