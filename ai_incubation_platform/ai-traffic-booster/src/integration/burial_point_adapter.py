"""
AI Traffic Booster 与运行态优化项目的埋点模型对齐

本模块提供与 ai-runtime-optimizer 统一的埋点数据模型，
支持跨项目 Agent 联合决策输入。
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from pydantic import BaseModel, Field, validator
import uuid


# ==================== 统一埋点数据模型 ====================
# 与 ai-runtime-optimizer 的 MetricsSnapshot 对齐

class TrafficMetricsSnapshot(BaseModel):
    """流量指标快照 - 与运行态优化项目对齐"""
    service_name: str = Field(..., description="服务名")

    # 流量指标
    visitors: Optional[int] = Field(None, description="访客数")
    page_views: Optional[int] = Field(None, description="页面浏览量")
    requests: Optional[int] = Field(None, description="请求数")

    # 性能指标
    avg_session_duration: Optional[float] = Field(None, description="平均会话时长（秒）")
    bounce_rate: Optional[float] = Field(None, description="跳出率 0-1")
    latency_p99_ms: Optional[float] = Field(None, description="P99 延迟（毫秒）")

    # 转化指标
    conversion_rate: Optional[float] = Field(None, description="转化率 0-1")
    ctr: Optional[float] = Field(None, description="点击率 0-1")

    # SEO 指标
    avg_position: Optional[float] = Field(None, description="平均搜索排名")
    seo_score: Optional[float] = Field(None, description="SEO 评分 0-100")

    # 扩展字段
    extra: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @validator("bounce_rate", "conversion_rate", "ctr")
    def validate_rate(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        if not 0 <= v <= 1:
            raise ValueError(f"Rate must be between 0 and 1, got {v}")
        return v

    @validator("seo_score")
    def validate_seo_score(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        if not 0 <= v <= 100:
            raise ValueError(f"SEO score must be between 0 and 100, got {v}")
        return v


class RouteTrafficStat(BaseModel):
    """页面/路由流量统计 - 与 RouteUsageStat 对齐"""
    path: str = Field(..., description="页面路径")
    title: Optional[str] = Field(None, description="页面标题")

    # 流量数据
    page_views: int = Field(0, description="页面浏览量")
    unique_visitors: int = Field(0, description="独立访客数")

    # 性能数据
    avg_time_on_page: Optional[float] = Field(None, description="平均停留时间（秒）")
    exit_rate: Optional[float] = Field(None, description="退出率 0-1")

    # SEO 数据
    seo_score: Optional[float] = Field(None, description="SEO 评分")

    # 扩展数据
    extra: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @validator("exit_rate")
    def validate_exit_rate(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        if not 0 <= v <= 1:
            raise ValueError(f"Exit rate must be between 0 and 1, got {v}")
        return v


class TrafficUsageSummary(BaseModel):
    """流量使用汇总 - 与 UsageSummary 对齐"""
    service_name: str = Field(..., description="服务名")
    period: str = Field("7d", description="统计周期，如 7d、24h")

    # 路由统计
    top_pages: List[RouteTrafficStat] = Field(default_factory=list)

    # 功能采用率（用于跨项目分析）
    feature_adoption: Optional[Dict[str, float]] = Field(
        None, description="功能标识 -> 活跃用户占比，0-1"
    )

    # 备注
    notes: Optional[str] = Field(None, description="备注信息")


# ==================== Agent 联合决策输入模型 ====================

@dataclass
class JointDecisionInput:
    """
    跨项目 Agent 联合决策输入

    整合 ai-traffic-booster 和 ai-runtime-optimizer 的数据，
    为统一决策提供输入。
    """
    # 流量曝光数据
    traffic_metrics: TrafficMetricsSnapshot
    traffic_summary: Optional[TrafficUsageSummary] = None

    # 运行态数据（来自 ai-runtime-optimizer）
    runtime_metrics: Optional[Dict[str, Any]] = None

    # 上下文信息
    trace_id: str = field(default_factory=lambda: f"trace-{uuid.uuid4().hex[:12]}")
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # 扩展字段
    extra_context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "trace_id": self.trace_id,
            "timestamp": self.timestamp.isoformat(),
            "traffic_metrics": self.traffic_metrics.model_dump(),
            "traffic_summary": self.traffic_summary.model_dump() if self.traffic_summary else None,
            "runtime_metrics": self.runtime_metrics,
            "extra_context": self.extra_context
        }


# ==================== 联合决策建议模型 ====================

class JointSuggestion(BaseModel):
    """跨项目联合决策建议"""
    id: str = Field(default_factory=lambda: f"suggestion-{uuid.uuid4().hex[:8]}")
    trace_id: str = Field(..., description="关联的追踪 ID")

    # 建议内容
    type: str = Field(..., description="建议类型：traffic/runtime/joint")
    action: str = Field(..., description="建议的操作")
    description: str = Field(..., description="详细描述")

    # 优先级
    priority: str = Field("medium", description="优先级：critical/high/medium/low")
    confidence: float = Field(..., ge=0, le=1, description="置信度")

    # 证据
    evidence: Dict[str, Any] = Field(default_factory=dict, description="证据数据")

    # 标签（用于分类和过滤）
    tags: List[str] = Field(default_factory=list)

    # 时间
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @validator("priority")
    def validate_priority(cls, v: str) -> str:
        allowed = {"critical", "high", "medium", "low"}
        if v not in allowed:
            raise ValueError(f"Priority must be one of {allowed}")
        return v


# ==================== 数据转换器 ====================

class TrafficToRuntimeAdapter:
    """
    流量数据到运行态数据的适配器

    将 ai-traffic-booster 的流量指标转换为
    ai-runtime-optimizer 可理解的格式
    """

    @staticmethod
    def convert_metrics(traffic: TrafficMetricsSnapshot) -> Dict[str, Any]:
        """转换流量指标为运行态指标格式"""
        return {
            "service_name": traffic.service_name,
            "cpu_percent": None,  # 流量数据不包含 CPU
            "memory_mb": None,    # 流量数据不包含内存
            "latency_p99_ms": traffic.latency_p99_ms,
            "error_rate": traffic.bounce_rate,  # 用跳出率近似错误率
            "extra": {
                "visitors": traffic.visitors,
                "page_views": traffic.page_views,
                "conversion_rate": traffic.conversion_rate,
                "ctr": traffic.ctr,
                "seo_score": traffic.seo_score
            }
        }

    @staticmethod
    def convert_route_stats(
        pages: List[RouteTrafficStat]
    ) -> List[Dict[str, Any]]:
        """转换页面统计为路由统计格式"""
        result = []
        for page in pages:
            result.append({
                "path": page.path,
                "requests": page.page_views,
                "p99_ms": page.avg_time_on_page,  # 用停留时间近似
                "error_rate": page.exit_rate
            })
        return result


class JointDecisionAnalyzer:
    """
    联合决策分析器

    综合流量数据和运行态数据，生成联合决策建议
    """

    def __init__(self):
        self.adapter = TrafficToRuntimeAdapter()

    def analyze(
        self,
        decision_input: JointDecisionInput
    ) -> List[JointSuggestion]:
        """
        分析联合决策输入，生成建议

        Args:
            decision_input: 联合决策输入

        Returns:
            联合决策建议列表
        """
        suggestions = []

        # 规则 1: 高流量 + 低性能 -> 优先优化性能
        if self._is_high_traffic_low_performance(decision_input):
            suggestions.append(JointSuggestion(
                trace_id=decision_input.trace_id,
                type="joint",
                action="optimize_performance",
                description="检测到高流量但性能较低，建议优先进行性能优化",
                priority="high",
                confidence=0.8,
                evidence={
                    "traffic_metrics": decision_input.traffic_metrics.model_dump(),
                    "rule": "high_traffic_low_performance"
                },
                tags=["performance", "optimization", "joint"]
            ))

        # 规则 2: 低流量 + 低 SEO -> 优先优化内容
        if self._is_low_traffic_low_seo(decision_input):
            suggestions.append(JointSuggestion(
                trace_id=decision_input.trace_id,
                type="traffic",
                action="optimize_content_seo",
                description="检测到流量低且 SEO 评分低，建议优先优化内容和 SEO",
                priority="medium",
                confidence=0.75,
                evidence={
                    "seo_score": decision_input.traffic_metrics.seo_score,
                    "visitors": decision_input.traffic_metrics.visitors,
                    "rule": "low_traffic_low_seo"
                },
                tags=["seo", "content", "traffic"]
            ))

        # 规则 3: 高跳出率 -> 优化用户体验
        if decision_input.traffic_metrics.bounce_rate and \
           decision_input.traffic_metrics.bounce_rate > 0.6:
            suggestions.append(JointSuggestion(
                trace_id=decision_input.trace_id,
                type="traffic",
                action="optimize_user_experience",
                description="检测到高跳出率，建议优化用户体验",
                priority="high",
                confidence=0.85,
                evidence={
                    "bounce_rate": decision_input.traffic_metrics.bounce_rate,
                    "threshold": 0.6
                },
                tags=["ux", "bounce_rate"]
            ))

        return suggestions

    def _is_high_traffic_low_performance(
        self,
        input: JointDecisionInput
    ) -> bool:
        """判断是否高流量低性能"""
        metrics = input.traffic_metrics
        if not metrics.visitors or not metrics.latency_p99_ms:
            return False
        return metrics.visitors > 10000 and metrics.latency_p99_ms > 1000

    def _is_low_traffic_low_seo(
        self,
        input: JointDecisionInput
    ) -> bool:
        """判断是否低流量低 SEO"""
        metrics = input.traffic_metrics
        if not metrics.visitors or not metrics.seo_score:
            return False
        return metrics.visitors < 5000 and metrics.seo_score < 50


# ==================== 工具函数 ====================

def create_joint_decision_input(
    traffic_metrics: TrafficMetricsSnapshot,
    traffic_summary: Optional[TrafficUsageSummary] = None,
    runtime_metrics: Optional[Dict[str, Any]] = None,
    extra_context: Optional[Dict[str, Any]] = None
) -> JointDecisionInput:
    """创建联合决策输入的快捷函数"""
    return JointDecisionInput(
        traffic_metrics=traffic_metrics,
        traffic_summary=traffic_summary,
        runtime_metrics=runtime_metrics,
        extra_context=extra_context or {}
    )
