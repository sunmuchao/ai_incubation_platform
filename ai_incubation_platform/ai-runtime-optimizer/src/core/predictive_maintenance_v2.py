"""
预测性维护 v2.3 增强模块：健康度评分、剩余寿命预测、预测性告警、维护计划优化
基于 v1 版本的 LSTM 时序预测能力，增加：
1. 健康度评分系统 - 多维度综合评估服务健康状态
2. 剩余寿命预测 (RUL) - 预测服务/组件的剩余正常运行时间
3. 预测性告警引擎 - 提前 7 天预警，智能优先级排序
4. 维护计划优化器 - 最优维护窗口推荐和资源调度

对标 Datadog PredictiveOps 和 New Relic Predictive AI 能力
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import math

try:
    import numpy as np
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    np = None

from .predictive_maintenance import (
    PredictiveMaintenanceEngine,
    SimpleLSTMPredictor,
    FailurePredictor,
    PredictionResult,
    FailurePrediction,
    AlertLevel,
    get_predictive_maintenance_engine
)

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """健康状态等级"""
    EXCELLENT = "excellent"  # 优秀 (90-100)
    GOOD = "good"  # 良好 (70-89)
    FAIR = "fair"  # 一般 (50-69)
    POOR = "poor"  # 较差 (30-49)
    CRITICAL = "critical"  # 危急 (0-29)


class MaintenancePriority(str, Enum):
    """维护优先级"""
    URGENT = "urgent"  # 紧急 - 立即处理
    HIGH = "high"  # 高 - 24 小时内
    MEDIUM = "medium"  # 中 - 7 天内
    LOW = "low"  # 低 - 30 天内
    SCHEDULED = "scheduled"  # 计划内 - 按计划执行


@dataclass
class HealthDimension:
    """健康度维度"""
    name: str  # 维度名称 (cpu, memory, error_rate, latency, throughput)
    score: float  # 维度得分 (0-100)
    weight: float  # 权重 (0-1)
    trend: str  # 趋势："improving", "stable", "degrading"
    metrics: Dict[str, float] = field(default_factory=dict)  # 详细指标
    threshold_status: str = "normal"  # "normal", "warning", "critical"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "score": self.score,
            "weight": self.weight,
            "trend": self.trend,
            "metrics": self.metrics,
            "threshold_status": self.threshold_status
        }


@dataclass
class HealthScore:
    """健康度评分"""
    service_name: str
    overall_score: float  # 综合健康度 (0-100)
    status: HealthStatus
    dimensions: List[HealthDimension]
    timestamp: datetime
    historical_scores: List[float] = field(default_factory=list)  # 历史分数
    trend: str = "stable"  # 整体趋势
    risk_factors: List[str] = field(default_factory=list)  # 风险因素
    recommendations: List[str] = field(default_factory=list)  # 建议

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "overall_score": round(self.overall_score, 2),
            "status": self.status.value,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "timestamp": self.timestamp.isoformat(),
            "trend": self.trend,
            "risk_factors": self.risk_factors,
            "recommendations": self.recommendations,
            "historical_avg": sum(self.historical_scores) / len(self.historical_scores) if self.historical_scores else None,
            "historical_trend": self._calculate_historical_trend()
        }

    def _calculate_historical_trend(self) -> str:
        """计算历史趋势"""
        if len(self.historical_scores) < 3:
            return "insufficient_data"

        recent = self.historical_scores[-3:]
        if recent[-1] > recent[0] + 5:
            return "improving"
        elif recent[-1] < recent[0] - 5:
            return "degrading"
        return "stable"


@dataclass
class RULPrediction:
    """剩余寿命预测 (Remaining Useful Life)"""
    service_name: str
    component_name: str  # 组件名称，如 "database", "cache", "api"

    # 预测结果
    current_rul_hours: float  # 当前剩余寿命 (小时)
    confidence_interval_lower: float  # 置信区间下界
    confidence_interval_upper: float  # 置信区间上界
    confidence_level: float  # 置信度 (0-1)

    # 故障预测
    predicted_failure_time: datetime
    failure_probability: float  # 故障概率

    # 诊断信息
    degradation_rate: float  # 退化速率 (每小时分数下降)
    critical_threshold: float  # 临界阈值 (健康度低于此值视为故障)
    degradation_factors: List[str] = field(default_factory=list)  # 退化因素

    # 建议
    recommended_actions: List[str] = field(default_factory=list)
    maintenance_urgency: MaintenancePriority = MaintenancePriority.LOW

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "component_name": self.component_name,
            "current_rul_hours": round(self.current_rul_hours, 2),
            "current_rul_days": round(self.current_rul_hours / 24, 2),
            "confidence_interval": [
                round(self.confidence_interval_lower, 2),
                round(self.confidence_interval_upper, 2)
            ],
            "confidence_level": round(self.confidence_level, 3),
            "predicted_failure_time": self.predicted_failure_time.isoformat(),
            "failure_probability": round(self.failure_probability, 3),
            "degradation_rate": round(self.degradation_rate, 4),
            "critical_threshold": self.critical_threshold,
            "degradation_factors": self.degradation_factors,
            "recommended_actions": self.recommended_actions,
            "maintenance_urgency": self.maintenance_urgency.value
        }


@dataclass
class PredictiveAlert:
    """预测性告警"""
    alert_id: str
    service_name: str
    alert_type: str  # "capacity", "failure", "degradation", "anomaly"

    # 预测信息
    predicted_event: str  # 预测事件描述
    predicted_time: datetime  # 预测发生时间
    time_until_event: timedelta  # 距离事件的时间
    probability: float  # 发生概率

    # 告警详情
    severity: AlertLevel
    priority: MaintenancePriority
    title: str
    description: str

    # 影响分析
    affected_services: List[str] = field(default_factory=list)
    business_impact: str = ""  # 业务影响描述

    # 建议操作
    recommended_actions: List[str] = field(default_factory=list)

    # 元数据
    created_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    dismissed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "service_name": self.service_name,
            "alert_type": self.alert_type,
            "predicted_event": self.predicted_event,
            "predicted_time": self.predicted_time.isoformat(),
            "hours_until_event": self.time_until_event.total_seconds() / 3600,
            "probability": round(self.probability, 3),
            "severity": self.severity.value,
            "priority": self.priority.value,
            "title": self.title,
            "description": self.description,
            "affected_services": self.affected_services,
            "business_impact": self.business_impact,
            "recommended_actions": self.recommended_actions,
            "created_at": self.created_at.isoformat(),
            "acknowledged": self.acknowledged,
            "dismissed": self.dismissed
        }


@dataclass
class MaintenanceWindow:
    """维护窗口"""
    window_id: str
    service_name: str
    start_time: datetime
    end_time: datetime
    duration_hours: float

    # 维护内容
    maintenance_type: str  # "preventive", "corrective", "upgrade", "patch"
    priority: MaintenancePriority
    tasks: List[str] = field(default_factory=list)

    # 影响评估
    requires_downtime: bool = False
    estimated_downtime_minutes: int = 0
    affected_services: List[str] = field(default_factory=list)
    risk_level: str = "low"  # "low", "medium", "high", "critical"

    # 资源需求
    required_resources: Dict[str, Any] = field(default_factory=dict)
    estimated_cost: float = 0.0  # 估算成本

    # 调度信息
    is_optimal: bool = True  # 是否为最优窗口
    alternative_windows: List[datetime] = field(default_factory=list)

    # 状态
    status: str = "proposed"  # "proposed", "scheduled", "in_progress", "completed", "cancelled"
    scheduled_by: Optional[str] = None
    scheduled_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "window_id": self.window_id,
            "service_name": self.service_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_hours": self.duration_hours,
            "maintenance_type": self.maintenance_type,
            "priority": self.priority.value,
            "tasks": self.tasks,
            "requires_downtime": self.requires_downtime,
            "estimated_downtime_minutes": self.estimated_downtime_minutes,
            "affected_services": self.affected_services,
            "risk_level": self.risk_level,
            "required_resources": self.required_resources,
            "estimated_cost": self.estimated_cost,
            "is_optimal": self.is_optimal,
            "alternative_windows": [t.isoformat() for t in self.alternative_windows],
            "status": self.status,
            "scheduled_by": self.scheduled_by,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None
        }


@dataclass
class MaintenancePlan:
    """维护计划"""
    plan_id: str
    service_name: str
    created_at: datetime

    # 维护项目
    maintenance_items: List[MaintenanceWindow] = field(default_factory=list)

    # 总体评估
    total_estimated_cost: float = 0.0
    total_downtime_hours: float = 0.0
    overall_risk: str = "low"

    # 调度建议
    recommended_schedule: List[MaintenanceWindow] = field(default_factory=list)
    optimization_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "service_name": self.service_name,
            "created_at": self.created_at.isoformat(),
            "maintenance_items": [item.to_dict() for item in self.maintenance_items],
            "total_estimated_cost": self.total_estimated_cost,
            "total_downtime_hours": self.total_downtime_hours,
            "overall_risk": self.overall_risk,
            "recommended_schedule": [item.to_dict() for item in self.recommended_schedule],
            "optimization_notes": self.optimization_notes
        }


class HealthScoreService:
    """
    健康度评分服务

    多维度健康评估模型：
    - CPU 健康度：基于使用率、温度、负载
    - 内存健康度：基于使用率、GC 频率、OOM 风险
    - 错误率健康度：基于错误率、错误类型分布
    - 延迟健康度：基于 P50/P95/P99 延迟
    - 吞吐量健康度：基于请求量、处理容量比

    综合评分 = Σ(维度得分 × 权重)
    """

    def __init__(self):
        self._service_dimensions: Dict[str, Dict[str, HealthDimension]] = defaultdict(dict)
        self._service_history: Dict[str, List[HealthScore]] = defaultdict(list)

        # 默认维度权重 (可根据服务类型调整)
        self._default_weights = {
            "cpu": 0.20,
            "memory": 0.20,
            "error_rate": 0.25,
            "latency": 0.20,
            "throughput": 0.15
        }

        # 健康度阈值
        self._thresholds = {
            "cpu": {"warning": 70, "critical": 90},
            "memory": {"warning": 75, "critical": 95},
            "error_rate": {"warning": 0.01, "critical": 0.05},  # 1%, 5%
            "latency": {"warning": 500, "critical": 1000},  # ms
            "throughput": {"warning": 0.7, "critical": 0.9}  # 容量利用率
        }

    def set_dimension_weights(self, service_name: str, weights: Dict[str, float]):
        """设置服务特定维度权重"""
        # 归一化权重
        total = sum(weights.values())
        if total > 0:
            self._default_weights[service_name] = {k: v / total for k, v in weights.items()}

    def record_dimension_score(
        self,
        service_name: str,
        dimension_name: str,
        score: float,
        trend: str = "stable",
        metrics: Dict[str, float] = None,
        weight: float = None
    ):
        """记录维度得分"""
        # 确定阈值状态
        threshold_status = self._evaluate_threshold_status(dimension_name, score, metrics)

        dimension = HealthDimension(
            name=dimension_name,
            score=max(0, min(100, score)),  # 限制在 0-100
            weight=weight if weight is not None else self._default_weights.get(dimension_name, 0.2),
            trend=trend,
            metrics=metrics or {},
            threshold_status=threshold_status
        )

        self._service_dimensions[service_name][dimension_name] = dimension

    def _evaluate_threshold_status(
        self,
        dimension_name: str,
        score: float,
        metrics: Dict[str, float] = None
    ) -> str:
        """评估阈值状态"""
        if dimension_name not in self._thresholds:
            return "normal"

        thresholds = self._thresholds[dimension_name]

        # 基于分数评估 (分数越低越危险)
        if score < 30:
            return "critical"
        elif score < 60:
            return "warning"

        # 基于具体指标评估
        if metrics:
            # 对于 CPU/memory，高值表示危险
            if dimension_name in ["cpu", "memory"]:
                if "usage_percent" in metrics:
                    usage = metrics["usage_percent"]
                    if usage >= thresholds["critical"]:
                        return "critical"
                    elif usage >= thresholds["warning"]:
                        return "warning"

        return "normal"

    def calculate_health_score(
        self,
        service_name: str,
        dimensions: List[str] = None
    ) -> Optional[HealthScore]:
        """
        计算综合健康度

        Args:
            service_name: 服务名称
            dimensions: 要包含的维度列表 (可选)

        Returns:
            健康度评分结果
        """
        if service_name not in self._service_dimensions:
            return None

        service_dims = self._service_dimensions[service_name]

        if dimensions:
            service_dims = {k: v for k, v in service_dims.items() if k in dimensions}

        if not service_dims:
            return None

        # 计算加权平均分数
        total_weight = sum(d.weight for d in service_dims.values())
        if total_weight == 0:
            return None

        overall_score = sum(d.score * d.weight for d in service_dims.values()) / total_weight

        # 确定健康状态
        status = self._score_to_status(overall_score)

        # 识别风险因素
        risk_factors = self._identify_risk_factors(service_dims)

        # 生成建议
        recommendations = self._generate_recommendations(service_dims, risk_factors)

        # 获取历史分数
        historical_scores = [
            h.overall_score for h in self._service_history[service_name][-24:]  # 最近 24 条
        ]

        # 确定趋势
        trend = self._calculate_trend(historical_scores, overall_score)

        health_score = HealthScore(
            service_name=service_name,
            overall_score=overall_score,
            status=status,
            dimensions=list(service_dims.values()),
            timestamp=datetime.utcnow(),
            historical_scores=historical_scores,
            trend=trend,
            risk_factors=risk_factors,
            recommendations=recommendations
        )

        # 保存到历史
        self._service_history[service_name].append(health_score)
        # 限制历史大小
        if len(self._service_history[service_name]) > 100:
            self._service_history[service_name] = self._service_history[service_name][-100:]

        return health_score

    def _score_to_status(self, score: float) -> HealthStatus:
        """将分数转换为状态"""
        if score >= 90:
            return HealthStatus.EXCELLENT
        elif score >= 70:
            return HealthStatus.GOOD
        elif score >= 50:
            return HealthStatus.FAIR
        elif score >= 30:
            return HealthStatus.POOR
        else:
            return HealthStatus.CRITICAL

    def _identify_risk_factors(self, dimensions: Dict[str, HealthDimension]) -> List[str]:
        """识别风险因素"""
        risk_factors = []

        for dim in dimensions.values():
            if dim.threshold_status == "critical":
                risk_factors.append(f"{dim.name} 处于危急状态 (得分：{dim.score:.1f})")
            elif dim.threshold_status == "warning":
                risk_factors.append(f"{dim.name} 处于警告状态 (得分：{dim.score:.1f})")

            if dim.trend == "degrading":
                risk_factors.append(f"{dim.name} 正在恶化")

        return risk_factors

    def _generate_recommendations(
        self,
        dimensions: Dict[str, HealthDimension],
        risk_factors: List[str]
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []

        for dim in dimensions.values():
            if dim.score < 50:
                if dim.name == "cpu":
                    recommendations.append("检查 CPU 密集型操作，考虑优化算法或增加资源")
                elif dim.name == "memory":
                    recommendations.append("检查内存泄漏，优化内存使用或增加容量")
                elif dim.name == "error_rate":
                    recommendations.append("分析错误日志，修复高频错误")
                elif dim.name == "latency":
                    recommendations.append("分析慢查询，优化性能瓶颈")
                elif dim.name == "throughput":
                    recommendations.append("评估容量规划，考虑水平扩展")

        if not recommendations:
            recommendations.append("系统健康状态良好，保持当前监控")

        return recommendations

    def _calculate_trend(
        self,
        historical_scores: List[float],
        current_score: float
    ) -> str:
        """计算趋势"""
        if len(historical_scores) < 3:
            return "stable"

        recent_avg = sum(historical_scores[-3:]) / 3

        if current_score > recent_avg + 5:
            return "improving"
        elif current_score < recent_avg - 5:
            return "degrading"
        return "stable"

    def get_health_history(
        self,
        service_name: str,
        limit: int = 24
    ) -> List[Dict[str, Any]]:
        """获取健康历史"""
        history = self._service_history.get(service_name, [])[-limit:]
        return [h.to_dict() for h in history]

    def get_all_health_scores(self) -> List[Dict[str, Any]]:
        """获取所有服务的健康评分"""
        scores = []
        for service_name in self._service_dimensions:
            score = self.calculate_health_score(service_name)
            if score:
                scores.append(score.to_dict())
        return scores


class RULPredictor:
    """
    剩余寿命预测器 (Remaining Useful Life Predictor)

    基于健康度退化和时间序列预测服务的 RUL：
    1. 收集历史健康度分数
    2. 拟合退化曲线 (线性/指数)
    3. 预测到达临界阈值的时间
    4. 计算置信区间
    """

    def __init__(self, critical_threshold: float = 30.0):
        self._service_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self._component_predictors: Dict[str, SimpleLSTMPredictor] = {}
        self._critical_threshold = critical_threshold
        self._predictions_history: List[RULPrediction] = []

    def record_health_score(
        self,
        service_name: str,
        component_name: str,
        health_score: float,
        timestamp: datetime = None
    ):
        """记录健康度分数"""
        if timestamp is None:
            timestamp = datetime.utcnow()

        key = f"{service_name}:{component_name}"
        self._service_history[key].append((timestamp, health_score))

        # 限制历史数据大小
        if len(self._service_history[key]) > 1000:
            self._service_history[key] = self._service_history[key][-1000:]

        # 更新预测器
        if key not in self._component_predictors:
            self._component_predictors[key] = SimpleLSTMPredictor(
                lookback_days=7,
                prediction_horizon_hours=168  # 7 天
            )

        self._component_predictors[key].add_sample(timestamp, health_score)

    def predict_rul(
        self,
        service_name: str,
        component_name: str
    ) -> Optional[RULPrediction]:
        """
        预测剩余寿命

        Args:
            service_name: 服务名称
            component_name: 组件名称

        Returns:
            RUL 预测结果
        """
        key = f"{service_name}:{component_name}"

        if key not in self._service_history:
            return None

        history = self._service_history[key]
        if len(history) < 10:
            return None  # 数据不足

        # 获取当前健康度
        current_score = history[-1][1]

        # 计算退化速率
        degradation_rate = self._calculate_degradation_rate(history)

        # 如果没有退化或正在改善
        if degradation_rate >= 0:
            # 预测一个很大的 RUL
            return RULPrediction(
                service_name=service_name,
                component_name=component_name,
                current_rul_hours=720,  # 30 天
                confidence_interval_lower=500,
                confidence_interval_upper=1000,
                confidence_level=0.5,
                predicted_failure_time=datetime.utcnow() + timedelta(hours=720),
                failure_probability=0.1,
                degradation_rate=0,
                critical_threshold=self._critical_threshold,
                degradation_factors=["无明显退化"],
                recommended_actions=["持续监控健康状态"],
                maintenance_urgency=MaintenancePriority.LOW
            )

        # 计算到达临界阈值的时间
        hours_to_critical = (current_score - self._critical_threshold) / abs(degradation_rate)

        if hours_to_critical <= 0:
            # 已经低于临界阈值
            return RULPrediction(
                service_name=service_name,
                component_name=component_name,
                current_rul_hours=0,
                confidence_interval_lower=0,
                confidence_interval_upper=24,
                confidence_level=0.95,
                predicted_failure_time=datetime.utcnow(),
                failure_probability=0.95,
                degradation_rate=degradation_rate,
                critical_threshold=self._critical_threshold,
                degradation_factors=self._identify_degradation_factors(history),
                recommended_actions=self._generate_urgent_actions(service_name, component_name),
                maintenance_urgency=MaintenancePriority.URGENT
            )

        # 使用 LSTM 预测器进行更精确的预测
        if key in self._component_predictors:
            predictor = self._component_predictors[key]
            predicted_values, timestamps, lower_bounds, upper_bounds = predictor.predict(horizon_hours=int(hours_to_critical * 1.5))

            # 找到预测值首次低于阈值的时间
            predicted_failure_time = None
            for i, (pred, lower, upper) in enumerate(zip(predicted_values, lower_bounds, upper_bounds)):
                if pred <= self._critical_threshold:
                    predicted_failure_time = timestamps[i]
                    break

            # 计算置信区间
            if predicted_failure_time:
                confidence_lower = hours_to_critical * 0.7
                confidence_upper = hours_to_critical * 1.3
            else:
                confidence_lower = hours_to_critical * 0.8
                confidence_upper = hours_to_critical * 1.2
                predicted_failure_time = timestamps[-1] if timestamps else datetime.utcnow() + timedelta(hours=hours_to_critical)
        else:
            confidence_lower = hours_to_critical * 0.7
            confidence_upper = hours_to_critical * 1.3
            predicted_failure_time = datetime.utcnow() + timedelta(hours=hours_to_critical)

        # 计算故障概率
        failure_probability = self._calculate_failure_probability(current_score, degradation_rate, hours_to_critical)

        # 确定维护优先级
        if hours_to_critical < 24:
            urgency = MaintenancePriority.URGENT
        elif hours_to_critical < 168:  # 7 天
            urgency = MaintenancePriority.HIGH
        elif hours_to_critical < 720:  # 30 天
            urgency = MaintenancePriority.MEDIUM
        else:
            urgency = MaintenancePriority.LOW

        # 生成建议
        recommended_actions = self._generate_rul_recommendations(
            service_name, component_name, hours_to_critical, current_score
        )

        prediction = RULPrediction(
            service_name=service_name,
            component_name=component_name,
            current_rul_hours=hours_to_critical,
            confidence_interval_lower=confidence_lower,
            confidence_interval_upper=confidence_upper,
            confidence_level=min(0.95, 0.5 + len(history) / 200),  # 数据越多置信度越高
            predicted_failure_time=predicted_failure_time,
            failure_probability=failure_probability,
            degradation_rate=degradation_rate,
            critical_threshold=self._critical_threshold,
            degradation_factors=self._identify_degradation_factors(history),
            recommended_actions=recommended_actions,
            maintenance_urgency=urgency
        )

        self._predictions_history.append(prediction)
        return prediction

    def _calculate_degradation_rate(self, history: List[Tuple[datetime, float]]) -> float:
        """
        计算退化速率 (每小时分数下降)

        使用线性回归拟合健康度趋势
        """
        if len(history) < 2:
            return 0.0

        # 转换为小时单位
        base_time = history[0][0]
        points = [
            ((t - base_time).total_seconds() / 3600, score)
            for t, score in history
        ]

        # 线性回归
        n = len(points)
        sum_x = sum(p[0] for p in points)
        sum_y = sum(p[1] for p in points)
        sum_xy = sum(p[0] * p[1] for p in points)
        sum_x2 = sum(p[0] ** 2 for p in points)

        denominator = n * sum_x2 - sum_x ** 2
        if abs(denominator) < 1e-10:
            return 0.0

        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return slope  # 负值表示退化

    def _identify_degradation_factors(
        self,
        history: List[Tuple[datetime, float]]
    ) -> List[str]:
        """识别退化因素"""
        factors = []

        if len(history) < 10:
            return ["数据不足，无法准确分析"]

        recent = [h[1] for h in history[-10:]]
        older = [h[1] for h in history[-20:-10]] if len(history) >= 20 else [h[1] for h in history[:10]]

        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)

        if recent_avg < older_avg - 10:
            factors.append("近期健康度显著下降")

        # 检查下降速率是否加快
        if len(history) >= 30:
            very_recent = [h[1] for h in history[-5:]]
            recent_old = [h[1] for h in history[-15:-10]]
            recent_slope = (very_recent[-1] - very_recent[0]) / 5
            old_slope = (recent_old[-1] - recent_old[0]) / 5

            if abs(recent_slope) > abs(old_slope) * 1.5:
                factors.append("退化速率加快")

        return factors if factors else ["健康度缓慢下降"]

    def _calculate_failure_probability(
        self,
        current_score: float,
        degradation_rate: float,
        hours_to_critical: float
    ) -> float:
        """计算故障概率"""
        # 基础概率：当前分数越低概率越高
        base_prob = 1.0 - (current_score / 100.0)

        # 时间因子：越接近临界时间概率越高
        time_factor = 1.0 / (1.0 + hours_to_critical / 168)  # 168 小时=7 天

        # 退化速率因子
        rate_factor = min(1.0, abs(degradation_rate) * 10)

        # 综合概率
        probability = 0.5 * base_prob + 0.3 * time_factor + 0.2 * rate_factor
        return min(0.99, max(0.01, probability))

    def _generate_urgent_actions(self, service_name: str, component_name: str) -> List[str]:
        """生成紧急操作建议"""
        return [
            f"立即检查 {service_name}/{component_name} 的健康状态",
            "准备执行紧急维护或切换至备用系统",
            "通知相关团队进入应急响应状态",
            "审查最近的变更和事件以识别根因"
        ]

    def _generate_rul_recommendations(
        self,
        service_name: str,
        component_name: str,
        hours_to_critical: float,
        current_score: float
    ) -> List[str]:
        """生成 RUL 建议"""
        actions = []

        if hours_to_critical < 24:
            actions.append(f"紧急：{service_name}/{component_name} 预计在{hours_to_critical:.1f}小时内达到临界状态")
            actions.append("立即安排维护窗口")
        elif hours_to_critical < 168:
            actions.append(f"警告：{service_name}/{component_name} 预计在未来 7 天内需要维护")
            actions.append("本周内安排预防性维护")
        elif hours_to_critical < 720:
            actions.append(f"注意：{service_name}/{component_name} 预计在未来 30 天内需要维护")
            actions.append("规划下月维护计划")
        else:
            actions.append(f"{service_name}/{component_name} 健康状态良好")
            actions.append("保持常规监控")

        if current_score < 50:
            actions.append("当前健康度较低，建议增加监控频率")

        return actions

    def get_all_rul_predictions(self) -> List[Dict[str, Any]]:
        """获取所有 RUL 预测"""
        return [p.to_dict() for p in self._predictions_history[-50:]]


class PredictiveAlertEngine:
    """
    预测性告警引擎

    基于预测模型提前发出告警：
    - 容量预测告警：提前 7 天预警资源耗尽
    - 故障预测告警：基于 RUL 预测
    - 退化告警：健康度持续下降
    - 异常预测告警：基于时序异常检测

    告警优先级评分模型：
    Priority = f(概率，影响，紧急度，业务价值)
    """

    def __init__(self):
        self._alerts: Dict[str, PredictiveAlert] = {}
        self._alert_history: List[PredictiveAlert] = []
        self._suppression_rules: Dict[str, Any] = {}
        self._service_dependencies: Dict[str, List[str]] = defaultdict(list)

        # 告警阈值
        self._alert_thresholds = {
            "probability_threshold": 0.6,  # 最低告警概率
            "time_horizon_hours": 168,  # 7 天预测窗口
            "min_hours_until_event": 1,  # 最短提前时间
        }

        self._alert_counter = 0

    def set_service_dependencies(self, service_name: str, dependencies: List[str]):
        """设置服务依赖关系"""
        self._service_dependencies[service_name] = dependencies

    def _generate_alert_id(self) -> str:
        """生成告警 ID"""
        self._alert_counter += 1
        return f"PALERT-{datetime.utcnow().strftime('%Y%m%d')}-{self._alert_counter:04d}"

    def create_capacity_alert(
        self,
        service_name: str,
        resource_type: str,
        current_usage: float,
        predicted_usage: float,
        capacity_limit: float,
        hours_until_capacity: float,
        probability: float
    ) -> Optional[PredictiveAlert]:
        """创建容量告警"""
        if hours_until_capacity < self._alert_thresholds["min_hours_until_event"]:
            return None

        if probability < self._alert_thresholds["probability_threshold"]:
            return None

        # 确定严重程度
        usage_ratio = predicted_usage / capacity_limit
        if usage_ratio >= 0.95:
            severity = AlertLevel.CRITICAL
        elif usage_ratio >= 0.85:
            severity = AlertLevel.WARNING
        else:
            severity = AlertLevel.INFO

        # 确定优先级
        if hours_until_capacity < 24:
            priority = MaintenancePriority.URGENT
        elif hours_until_capacity < 72:
            priority = MaintenancePriority.HIGH
        elif hours_until_capacity < 168:
            priority = MaintenancePriority.MEDIUM
        else:
            priority = MaintenancePriority.LOW

        # 生成告警标题和描述
        title = f"容量预警：{service_name} 的 {resource_type} 即将耗尽"
        description = (
            f"当前使用率：{current_usage/capacity_limit*100:.1f}%\n"
            f"预测使用率：{predicted_usage/capacity_limit*100:.1f}%\n"
            f"预计耗尽时间：{hours_until_capacity/24:.1f}天后"
        )

        # 生成建议
        recommended_actions = self._generate_capacity_actions(resource_type, hours_until_capacity)

        # 找出受影响的服务
        affected_services = self._get_dependent_services(service_name)

        alert = PredictiveAlert(
            alert_id=self._generate_alert_id(),
            service_name=service_name,
            alert_type="capacity",
            predicted_event=f"{resource_type} 使用率达到{usage_ratio*100:.1f}%",
            predicted_time=datetime.utcnow() + timedelta(hours=hours_until_capacity),
            time_until_event=timedelta(hours=hours_until_capacity),
            probability=probability,
            severity=severity,
            priority=priority,
            title=title,
            description=description,
            affected_services=affected_services,
            business_impact=self._assess_business_impact(service_name, affected_services),
            recommended_actions=recommended_actions
        )

        self._alerts[alert.alert_id] = alert
        self._alert_history.append(alert)

        return alert

    def create_failure_alert(
        self,
        service_name: str,
        rul_prediction: RULPrediction
    ) -> Optional[PredictiveAlert]:
        """创建故障预测告警"""
        if rul_prediction.failure_probability < self._alert_thresholds["probability_threshold"]:
            return None

        hours_until_failure = rul_prediction.current_rul_hours
        if hours_until_failure < self._alert_thresholds["min_hours_until_event"]:
            return None

        # 确定严重程度
        if rul_prediction.failure_probability >= 0.8:
            severity = AlertLevel.CRITICAL
        elif rul_prediction.failure_probability >= 0.6:
            severity = AlertLevel.WARNING
        else:
            severity = AlertLevel.INFO

        # 生成告警
        title = f"故障预警：{service_name}/{rul_prediction.component_name} 可能发生故障"
        description = (
            f"当前健康度：临界阈值 {rul_prediction.critical_threshold}\n"
            f"故障概率：{rul_prediction.failure_probability*100:.1f}%\n"
            f"预计故障时间：{rul_prediction.predicted_failure_time.strftime('%Y-%m-%d %H:%M')}\n"
            f"退化因素：{', '.join(rul_prediction.degradation_factors)}"
        )

        affected_services = self._get_dependent_services(service_name)

        alert = PredictiveAlert(
            alert_id=self._generate_alert_id(),
            service_name=service_name,
            alert_type="failure",
            predicted_event=f"{rul_prediction.component_name} 可能发生故障",
            predicted_time=rul_prediction.predicted_failure_time,
            time_until_event=timedelta(hours=hours_until_failure),
            probability=rul_prediction.failure_probability,
            severity=severity,
            priority=rul_prediction.maintenance_urgency,
            title=title,
            description=description,
            affected_services=affected_services,
            business_impact=self._assess_business_impact(service_name, affected_services),
            recommended_actions=rul_prediction.recommended_actions
        )

        self._alerts[alert.alert_id] = alert
        self._alert_history.append(alert)

        return alert

    def create_degradation_alert(
        self,
        service_name: str,
        health_score: HealthScore
    ) -> Optional[PredictiveAlert]:
        """创建退化告警"""
        if health_score.trend != "degrading":
            return None

        # 计算退化速率
        if len(health_score.historical_scores) < 3:
            return None

        recent = health_score.historical_scores[-3:]
        degradation_rate = (recent[-1] - recent[0]) / len(recent)

        if degradation_rate > -2:  # 退化不明显
            return None

        # 预测到达不良状态的时间
        current_score = health_score.overall_score
        if current_score > 50:
            hours_to_poor = (50 - current_score) / degradation_rate if degradation_rate < 0 else float('inf')
        else:
            hours_to_poor = 168  # 已经在不良状态

        probability = min(0.9, 0.5 + abs(degradation_rate) / 10)

        title = f"退化警告：{service_name} 健康度持续下降"
        description = (
            f"当前健康度：{current_score:.1f}\n"
            f"健康趋势：{health_score.trend}\n"
            f"风险因素：{', '.join(health_score.risk_factors)}"
        )

        alert = PredictiveAlert(
            alert_id=self._generate_alert_id(),
            service_name=service_name,
            alert_type="degradation",
            predicted_event="健康度可能降至不良水平",
            predicted_time=datetime.utcnow() + timedelta(hours=hours_to_poor),
            time_until_event=timedelta(hours=hours_to_poor),
            probability=probability,
            severity=AlertLevel.WARNING,
            priority=MaintenancePriority.MEDIUM,
            title=title,
            description=description,
            affected_services=self._get_dependent_services(service_name),
            recommended_actions=health_score.recommendations
        )

        self._alerts[alert.alert_id] = alert
        self._alert_history.append(alert)

        return alert

    def _generate_capacity_actions(self, resource_type: str, hours_until: float) -> List[str]:
        """生成容量相关建议"""
        actions = []

        if "cpu" in resource_type.lower():
            actions.append("分析 CPU 使用趋势，识别增长原因")
            actions.append("优化 CPU 密集型操作")
            actions.append("考虑水平扩展或增加 CPU 资源")
        elif "memory" in resource_type.lower():
            actions.append("检查内存泄漏")
            actions.append("优化内存使用或增加容量")
            actions.append("考虑启用内存交换或增加实例")
        elif "disk" in resource_type.lower() or "storage" in resource_type.lower():
            actions.append("清理不必要的文件和日志")
            actions.append("实施数据归档策略")
            actions.append("扩展存储容量")

        if hours_until < 48:
            actions.insert(0, "紧急：立即采取行动避免服务中断")

        return actions

    def _get_dependent_services(self, service_name: str) -> List[str]:
        """获取依赖该服务的其他服务"""
        dependents = []
        for svc, deps in self._service_dependencies.items():
            if service_name in deps:
                dependents.append(svc)
        return dependents

    def _assess_business_impact(
        self,
        service_name: str,
        affected_services: List[str]
    ) -> str:
        """评估业务影响"""
        impact_parts = []

        if len(affected_services) >= 3:
            impact_parts.append(f"将影响{len(affected_services)}个下游服务")

        # 根据服务名判断业务重要性
        critical_keywords = ["payment", "order", "user", "auth"]
        if any(kw in service_name.lower() for kw in critical_keywords):
            impact_parts.append("核心业务服务可能受影响")

        if not impact_parts:
            return "影响范围有限"

        return ". ".join(impact_parts)

    def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """确认告警"""
        if alert_id in self._alerts:
            self._alerts[alert_id].acknowledged = True
            return True
        return False

    def dismiss_alert(self, alert_id: str, reason: str = "") -> bool:
        """解除告警"""
        if alert_id in self._alerts:
            self._alerts[alert_id].dismissed = True
            return True
        return False

    def get_active_alerts(
        self,
        service_name: str = None,
        priority: MaintenancePriority = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取活跃告警"""
        alerts = [
            a for a in self._alerts.values()
            if not a.dismissed and not a.acknowledged
        ]

        if service_name:
            alerts = [a for a in alerts if a.service_name == service_name]

        if priority:
            alerts = [a for a in alerts if a.priority == priority]

        # 按优先级排序
        priority_order = {
            MaintenancePriority.URGENT: 0,
            MaintenancePriority.HIGH: 1,
            MaintenancePriority.MEDIUM: 2,
            MaintenancePriority.LOW: 3
        }
        alerts.sort(key=lambda a: priority_order.get(a.priority, 4))

        return [a.to_dict() for a in alerts[:limit]]

    def get_alert_stats(self) -> Dict[str, Any]:
        """获取告警统计"""
        active = [a for a in self._alerts.values() if not a.dismissed]
        acknowledged = [a for a in active if a.acknowledged]

        by_type = defaultdict(int)
        by_severity = defaultdict(int)
        by_priority = defaultdict(int)

        for alert in active:
            by_type[alert.alert_type] += 1
            by_severity[alert.severity.value] += 1
            by_priority[alert.priority.value] += 1

        return {
            "total_active": len(active),
            "acknowledged": len(acknowledged),
            "unacknowledged": len(active) - len(acknowledged),
            "by_type": dict(by_type),
            "by_severity": dict(by_severity),
            "by_priority": dict(by_priority),
            "total_history": len(self._alert_history)
        }


class MaintenanceOptimizer:
    """
    维护计划优化器

    基于以下因素优化维护计划：
    1. 服务依赖关系
    2. 业务低峰期
    3. 资源可用性
    4. 维护窗口约束
    5. 成本优化

    输出最优维护时间窗口和任务排序
    """

    def __init__(self):
        self._service_windows: Dict[str, Dict[str, Any]] = {}
        self._business_hours: Dict[str, Tuple[int, int]] = {}  # service -> (low_traffic_hour, high_traffic_hour)
        self._resource_pools: Dict[str, int] = {}  # resource -> available count
        self._maintenance_history: List[MaintenanceWindow] = []

    def set_business_hours(
        self,
        service_name: str,
        low_traffic_hour: int,
        high_traffic_hour: int
    ):
        """设置业务低峰/高峰时段"""
        self._business_hours[service_name] = (low_traffic_hour, high_traffic_hour)

    def set_resource_pool(self, resource_type: str, count: int):
        """设置资源池"""
        self._resource_pools[resource_type] = count

    def set_service_window(
        self,
        service_name: str,
        window_config: Dict[str, Any]
    ):
        """设置服务维护窗口配置"""
        self._service_windows[service_name] = window_config

    def find_optimal_window(
        self,
        service_name: str,
        maintenance_type: str,
        estimated_duration_hours: float,
        urgency: MaintenancePriority,
        requires_downtime: bool = False,
        days_ahead: int = 7
    ) -> Optional[MaintenanceWindow]:
        """
        寻找最优维护窗口

        Args:
            service_name: 服务名称
            maintenance_type: 维护类型
            estimated_duration_hours: 预计持续时间
            urgency: 紧急程度
            requires_downtime: 是否需要停机
            days_ahead: 搜索范围 (天)

        Returns:
            最优维护窗口
        """
        now = datetime.utcnow()

        # 获取业务低峰时段
        low_hour, high_hour = self._business_hours.get(service_name, (2, 10))  # 默认凌晨 2-10 点为低峰

        # 根据紧急程度确定搜索范围
        if urgency == MaintenancePriority.URGENT:
            search_days = 1
            preferred_start = now + timedelta(hours=2)
        elif urgency == MaintenancePriority.HIGH:
            search_days = 2
            preferred_start = now + timedelta(hours=12)
        elif urgency == MaintenancePriority.MEDIUM:
            search_days = days_ahead
            preferred_start = now + timedelta(hours=24)
        else:
            search_days = 30
            preferred_start = now + timedelta(days=3)

        # 搜索最优窗口
        best_window = None
        best_score = -1

        for day in range(search_days):
            base_date = (preferred_start + timedelta(days=day)).date()

            # 在低峰时段创建候选窗口
            candidate_start = datetime.combine(base_date, datetime.min.time().replace(hour=low_hour))
            if candidate_start < now:
                candidate_start = datetime.combine((base_date + timedelta(days=1)), datetime.min.time().replace(hour=low_hour))

            candidate_end = candidate_start + timedelta(hours=estimated_duration_hours)

            # 计算窗口得分
            score = self._calculate_window_score(
                service_name=service_name,
                start_time=candidate_start,
                duration=estimated_duration_hours,
                requires_downtime=requires_downtime,
                urgency=urgency
            )

            if score > best_score:
                best_score = score
                best_window = MaintenanceWindow(
                    window_id=f"MW-{service_name}-{candidate_start.strftime('%Y%m%d%H')}",
                    service_name=service_name,
                    start_time=candidate_start,
                    end_time=candidate_end,
                    duration_hours=estimated_duration_hours,
                    maintenance_type=maintenance_type,
                    priority=urgency,
                    requires_downtime=requires_downtime,
                    estimated_downtime_minutes=int(estimated_duration_hours * 60) if requires_downtime else 0,
                    risk_level=self._assess_risk(service_name, candidate_start, urgency),
                    is_optimal=True
                )

        return best_window

    def _calculate_window_score(
        self,
        service_name: str,
        start_time: datetime,
        duration: float,
        requires_downtime: bool,
        urgency: MaintenancePriority
    ) -> float:
        """计算窗口得分"""
        score = 100.0

        # 时间偏好得分
        hour = start_time.hour
        low_hour, high_hour = self._business_hours.get(service_name, (2, 10))

        if low_hour <= hour <= low_hour + 6:
            score += 30  # 低峰时段加分
        elif high_hour - 2 <= hour <= high_hour + 2:
            score -= 30  # 高峰时段减分

        # 工作日偏好
        if start_time.weekday() >= 5:  # 周末
            score += 15  # 周末维护通常影响较小
        else:
            # 周二到周四是较好的维护时间
            if start_time.weekday() in [1, 2, 3]:
                score += 10
            # 周一和周五避免维护
            elif start_time.weekday() in [0, 4]:
                score -= 10

        # 紧急程度调整
        if urgency == MaintenancePriority.URGENT:
            # 紧急情况下，尽早执行最重要
            hours_from_now = (start_time - datetime.utcnow()).total_seconds() / 3600
            score += max(0, 50 - hours_from_now)

        # 停机要求
        if requires_downtime:
            # 需要停机的维护更应该安排在低峰
            if low_hour <= hour <= low_hour + 4:
                score += 20

        return score

    def _assess_risk(
        self,
        service_name: str,
        start_time: datetime,
        urgency: MaintenancePriority
    ) -> str:
        """评估维护风险"""
        risk_score = 0

        # 紧急维护风险更高
        if urgency == MaintenancePriority.URGENT:
            risk_score += 3
        elif urgency == MaintenancePriority.HIGH:
            risk_score += 2

        # 周末风险较低
        if start_time.weekday() >= 5:
            risk_score -= 1

        # 高峰时段风险高
        low_hour, high_hour = self._business_hours.get(service_name, (2, 10))
        if high_hour - 2 <= start_time.hour <= high_hour + 2:
            risk_score += 2

        if risk_score >= 4:
            return "critical"
        elif risk_score >= 2:
            return "high"
        elif risk_score >= 0:
            return "medium"
        else:
            return "low"

    def create_maintenance_plan(
        self,
        service_name: str,
        maintenance_items: List[Dict[str, Any]]
    ) -> MaintenancePlan:
        """
        创建维护计划

        Args:
            service_name: 服务名称
            maintenance_items: 维护项目列表，每项包含：
                - type: 维护类型
                - duration_hours: 预计时长
                - requires_downtime: 是否需要停机
                - urgency: 紧急程度
                - tasks: 任务列表

        Returns:
            维护计划
        """
        plan_id = f"MP-{service_name}-{datetime.utcnow().strftime('%Y%m%d%H%M')}"

        windows = []
        total_cost = 0.0
        total_downtime = 0.0

        for item in maintenance_items:
            window = self.find_optimal_window(
                service_name=service_name,
                maintenance_type=item.get("type", "preventive"),
                estimated_duration_hours=item.get("duration_hours", 1),
                urgency=item.get("urgency", MaintenancePriority.MEDIUM),
                requires_downtime=item.get("requires_downtime", False)
            )

            if window:
                window.tasks = item.get("tasks", [])
                window.estimated_cost = self._estimate_cost(window, item)
                windows.append(window)
                total_cost += window.estimated_cost
                if window.requires_downtime:
                    total_downtime += window.duration_hours

        # 优化窗口排序 (避免冲突)
        optimized_windows = self._optimize_window_schedule(windows)

        # 确定总体风险
        max_risk = max((w.risk_level for w in windows), default="low")

        plan = MaintenancePlan(
            plan_id=plan_id,
            service_name=service_name,
            created_at=datetime.utcnow(),
            maintenance_items=windows,
            total_estimated_cost=total_cost,
            total_downtime_hours=total_downtime,
            overall_risk=max_risk,
            recommended_schedule=optimized_windows,
            optimization_notes=self._generate_optimization_notes(windows)
        )

        self._maintenance_history.extend(windows)
        return plan

    def _estimate_cost(
        self,
        window: MaintenanceWindow,
        item: Dict[str, Any]
    ) -> float:
        """估算维护成本"""
        base_cost = 100  # 基础成本

        # 紧急程度系数
        urgency_multiplier = {
            MaintenancePriority.URGENT: 3.0,
            MaintenancePriority.HIGH: 2.0,
            MaintenancePriority.MEDIUM: 1.5,
            MaintenancePriority.LOW: 1.0
        }.get(window.priority, 1.0)

        # 停机成本
        downtime_cost = 0
        if window.requires_downtime:
            downtime_cost = window.estimated_downtime_minutes * 10  # 每分钟$10

        # 资源成本
        resource_cost = sum(
            self._resource_pools.get(r, 1) * 50
            for r in item.get("required_resources", [])
        )

        return base_cost * urgency_multiplier + downtime_cost + resource_cost

    def _optimize_window_schedule(
        self,
        windows: List[MaintenanceWindow]
    ) -> List[MaintenanceWindow]:
        """优化窗口调度"""
        if not windows:
            return []

        # 按优先级和时间排序
        priority_order = {
            MaintenancePriority.URGENT: 0,
            MaintenancePriority.HIGH: 1,
            MaintenancePriority.MEDIUM: 2,
            MaintenancePriority.LOW: 3
        }

        sorted_windows = sorted(
            windows,
            key=lambda w: (priority_order.get(w.priority, 4), w.start_time)
        )

        # 标记最优窗口
        for i, window in enumerate(sorted_windows):
            window.is_optimal = (i == 0)

        return sorted_windows

    def _generate_optimization_notes(self, windows: List[MaintenanceWindow]) -> List[str]:
        """生成优化说明"""
        notes = []

        if not windows:
            return ["无维护项目"]

        # 检查时间冲突
        for i, w1 in enumerate(windows):
            for w2 in windows[i+1:]:
                if w1.start_time < w2.end_time and w2.start_time < w1.end_time:
                    notes.append(f"警告：{w1.window_id} 和 {w2.window_id} 时间冲突")

        # 总体建议
        urgent_count = sum(1 for w in windows if w.priority == MaintenancePriority.URGENT)
        if urgent_count > 0:
            notes.append(f"有{urgent_count}个紧急维护项目，建议优先处理")

        total_downtime = sum(w.estimated_downtime_minutes for w in windows if w.requires_downtime)
        if total_downtime > 60:
            notes.append(f"总停机时间{total_downtime}分钟，建议分批次执行")

        return notes

    def get_maintenance_history(
        self,
        service_name: str = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取维护历史"""
        history = self._maintenance_history

        if service_name:
            history = [w for w in history if w.service_name == service_name]

        return [w.to_dict() for w in history[-limit:]]


class PredictiveMaintenanceEngineV2:
    """
    预测性维护引擎 V2 (集成)

    整合健康度评分、RUL 预测、预测性告警和维护计划优化
    """

    def __init__(self):
        self._health_service = HealthScoreService()
        self._rul_predictor = RULPredictor()
        self._alert_engine = PredictiveAlertEngine()
        self._maintenance_optimizer = MaintenanceOptimizer()

        # 引用 v1 引擎
        self._v1_engine = get_predictive_maintenance_engine()

    def record_health_dimension(
        self,
        service_name: str,
        dimension: str,
        score: float,
        trend: str = "stable",
        metrics: Dict[str, float] = None
    ):
        """记录健康维度得分"""
        self._health_service.record_dimension_score(
            service_name, dimension, score, trend, metrics
        )

    def calculate_health_score(
        self,
        service_name: str
    ) -> Optional[HealthScore]:
        """计算服务健康度"""
        return self._health_service.calculate_health_score(service_name)

    def predict_rul(
        self,
        service_name: str,
        component_name: str
    ) -> Optional[RULPrediction]:
        """预测剩余寿命"""
        return self._rul_predictor.predict_rul(service_name, component_name)

    def generate_predictive_alerts(
        self,
        service_name: str = None
    ) -> List[Dict[str, Any]]:
        """生成预测性告警"""
        # 为所有服务生成告警
        services_to_check = [service_name] if service_name else list(self._health_service._service_dimensions.keys())

        for svc in services_to_check:
            # 基于健康度生成退化告警
            health = self._health_service.calculate_health_score(svc)
            if health:
                self._alert_engine.create_degradation_alert(svc, health)

            # 基于 RUL 生成故障告警
            for dim in self._health_service._service_dimensions.get(svc, {}).keys():
                rul = self._rul_predictor.predict_rul(svc, dim)
                if rul:
                    self._alert_engine.create_failure_alert(svc, rul)

        return self._alert_engine.get_active_alerts()

    def create_maintenance_plan(
        self,
        service_name: str,
        maintenance_items: List[Dict[str, Any]]
    ) -> MaintenancePlan:
        """创建维护计划"""
        return self._maintenance_optimizer.create_maintenance_plan(
            service_name, maintenance_items
        )

    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表盘数据"""
        all_health = self._health_service.get_all_health_scores()
        all_alerts = self._alert_engine.get_active_alerts()
        all_rul = self._rul_predictor.get_all_rul_predictions()

        # 汇总统计
        avg_health = sum(h["overall_score"] for h in all_health) / len(all_health) if all_health else 0
        critical_alerts = sum(1 for a in all_alerts if a["severity"] == "critical")
        urgent_maintenance = sum(1 for r in all_rul if r["maintenance_urgency"] == "urgent")

        return {
            "summary": {
                "total_services": len(all_health),
                "average_health_score": round(avg_health, 2),
                "critical_alerts": critical_alerts,
                "urgent_maintenance_needed": urgent_maintenance
            },
            "health_scores": all_health,
            "active_alerts": all_alerts[:20],
            "rul_predictions": all_rul[:20],
            "alert_stats": self._alert_engine.get_alert_stats()
        }


# 全局实例
_predictive_maintenance_v2_engine: Optional[PredictiveMaintenanceEngineV2] = None


def get_predictive_maintenance_v2_engine() -> PredictiveMaintenanceEngineV2:
    """获取预测性维护 V2 引擎实例"""
    global _predictive_maintenance_v2_engine
    if _predictive_maintenance_v2_engine is None:
        _predictive_maintenance_v2_engine = PredictiveMaintenanceEngineV2()
    return _predictive_maintenance_v2_engine
