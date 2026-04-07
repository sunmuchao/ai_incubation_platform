"""
P6 预测性监控服务

实现：
1. 基于时序分析的查询性能预测
2. 容量规划和资源预测
3. 异常检测和自动诊断
4. 自愈建议和自动修复
"""
import asyncio
import uuid
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import db_manager
from utils.logger import logger
from models.monitoring import MetricModel, AlertModel, SystemHealthModel


class AnomalyType(str, Enum):
    """异常类型"""
    VALUE_SPIKE = "value_spike"  # 值突增
    VALUE_DROP = "value_drop"  # 值突降
    TREND_CHANGE = "trend_change"  # 趋势变化
    SEASONALITY_BREAK = "seasonality_break"  # 周期性异常
    OUT_OF_BOUNDS = "out_of_bounds"  # 超出边界


class PredictionConfidence(str, Enum):
    """预测置信度"""
    HIGH = "high"  # > 80%
    MEDIUM = "medium"  # 50-80%
    LOW = "low"  # < 50%


class SelfHealingAction(str, Enum):
    """自愈动作类型"""
    SCALE_UP = "scale_up"  # 扩容
    RATE_LIMIT = "rate_limit"  # 限流
    CACHE_WARM = "cache_warm"  # 缓存预热
    QUERY_OPTIMIZE = "query_optimize"  # 查询优化
    CONNECTION_POOL_ADJUST = "connection_pool_adjust"  # 连接池调整


@dataclass
class Anomaly:
    """异常检测结果"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    metric_name: str = ""
    anomaly_type: str = ""
    anomaly_score: float = 0.0  # 0-1, 越高越异常
    expected_value: float = 0.0
    actual_value: float = 0.0
    detected_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "metric_name": self.metric_name,
            "anomaly_type": self.anomaly_type,
            "anomaly_score": self.anomaly_score,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "metadata": self.metadata
        }


@dataclass
class Prediction:
    """预测结果"""
    metric_name: str = ""
    current_value: float = 0.0
    predicted_value: float = 0.0
    prediction_horizon: int = 0  # 预测时间范围（分钟）
    confidence: str = ""
    trend: str = ""  # increasing, decreasing, stable
    risk_level: str = ""  # low, medium, high, critical
    predicted_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "predicted_value": self.predicted_value,
            "prediction_horizon": self.prediction_horizon,
            "confidence": self.confidence,
            "trend": self.trend,
            "risk_level": self.risk_level,
            "predicted_at": self.predicted_at.isoformat() if self.predicted_at else None,
            "metadata": self.metadata
        }


@dataclass
class SelfHealingRecommendation:
    """自愈建议"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    anomaly_id: str = ""
    action_type: str = ""
    description: str = ""
    expected_impact: str = ""
    confidence: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    dry_run: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "anomaly_id": self.anomaly_id,
            "action_type": self.action_type,
            "description": self.description,
            "expected_impact": self.expected_impact,
            "confidence": self.confidence,
            "parameters": self.parameters,
            "dry_run": self.dry_run,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class TimeSeriesAnalyzer:
    """时序分析器"""

    def __init__(self):
        self._cache: Dict[str, List[Tuple[datetime, float]]] = {}

    def calculate_moving_average(self, values: List[float], window: int = 5) -> List[float]:
        """计算移动平均"""
        if len(values) < window:
            return values
        result = []
        for i in range(len(values)):
            start = max(0, i - window + 1)
            result.append(sum(values[start:i + 1]) / (i - start + 1))
        return result

    def calculate_std(self, values: List[float]) -> float:
        """计算标准差"""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return np.sqrt(variance)

    def detect_trend(self, values: List[float], timestamps: List[datetime] = None) -> str:
        """检测趋势"""
        if len(values) < 3:
            return "stable"

        # 使用线性回归检测趋势
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "stable"

        slope = numerator / denominator

        # 根据斜率判断趋势
        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable"

    def forecast_simple(self, values: List[float], horizon: int = 1) -> float:
        """简单预测（基于线性回归外推）"""
        if len(values) < 3:
            return values[-1] if values else 0.0

        # 使用线性回归进行预测
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return values[-1]

        slope = numerator / denominator
        intercept = y_mean - slope * x_mean

        # 外推预测
        predicted = slope * (n + horizon - 1) + intercept
        return predicted

    def detect_anomaly_3sigma(self, values: List[float], current_value: float) -> Tuple[bool, float, float]:
        """3-sigma 异常检测"""
        if len(values) < 3:
            return False, 0.0, 0.0

        mean = sum(values) / len(values)
        std = self.calculate_std(values)

        if std == 0:
            return False, mean, mean

        # 3-sigma 边界
        lower_bound = mean - 3 * std
        upper_bound = mean + 3 * std

        is_anomaly = current_value < lower_bound or current_value > upper_bound

        # 计算预期值（均值）
        expected_value = mean

        return is_anomaly, expected_value, std


class PredictiveMonitoringService:
    """预测性监控服务"""

    def __init__(self):
        self._analyzer = TimeSeriesAnalyzer()
        self._anomaly_history: Dict[str, List[Anomaly]] = {}
        self._prediction_cache: Dict[str, Prediction] = {}
        self._cache_ttl_seconds = 300  # 5 分钟缓存

    async def get_historical_metrics(
        self,
        metric_name: str,
        hours: int = 24,
        datasource: Optional[str] = None
    ) -> List[Tuple[datetime, float]]:
        """获取历史指标数据"""
        async with db_manager.get_async_session() as session:
            query = select(MetricModel).where(
                and_(
                    MetricModel.name == metric_name,
                    MetricModel.timestamp >= datetime.utcnow() - timedelta(hours=hours)
                )
            )
            if datasource:
                query = query.where(MetricModel.datasource == datasource)

            query = query.order_by(MetricModel.timestamp)
            result = await session.execute(query)
            metrics = result.scalars().all()

            return [(m.timestamp, m.value) for m in metrics]

    async def predict_metric(
        self,
        metric_name: str,
        horizon_minutes: int = 30,
        datasource: Optional[str] = None
    ) -> Prediction:
        """预测指标值"""
        # 检查缓存
        cache_key = f"{metric_name}:{datasource}:{horizon_minutes}"
        if cache_key in self._prediction_cache:
            cached = self._prediction_cache[cache_key]
            if (datetime.utcnow() - cached.predicted_at).total_seconds() < self._cache_ttl_seconds:
                return cached

        # 获取历史数据
        historical_data = await self.get_historical_metrics(
            metric_name,
            hours=24,
            datasource=datasource
        )

        if not historical_data:
            return Prediction(
                metric_name=metric_name,
                confidence=PredictionConfidence.LOW.value,
                risk_level="unknown",
                metadata={"error": "No historical data"}
            )

        timestamps, values = zip(*historical_data)
        values = list(values)

        # 当前值
        current_value = values[-1] if values else 0.0

        # 简单预测
        predicted_value = self._analyzer.forecast_simple(values, horizon=1)

        # 计算置信度
        std = self._analyzer.calculate_std(values)
        mean = sum(values) / len(values) if values else 1.0

        # 变异系数（标准差/均值）越小，置信度越高
        cv = std / mean if mean != 0 else 1.0
        if cv < 0.1:
            confidence = PredictionConfidence.HIGH.value
        elif cv < 0.3:
            confidence = PredictionConfidence.MEDIUM.value
        else:
            confidence = PredictionConfidence.LOW.value

        # 检测趋势
        trend = self._analyzer.detect_trend(values)

        # 评估风险等级
        change_rate = abs(predicted_value - current_value) / current_value if current_value != 0 else 0
        if change_rate > 0.5:
            risk_level = "critical"
        elif change_rate > 0.3:
            risk_level = "high"
        elif change_rate > 0.1:
            risk_level = "medium"
        else:
            risk_level = "low"

        prediction = Prediction(
            metric_name=metric_name,
            current_value=current_value,
            predicted_value=predicted_value,
            prediction_horizon=horizon_minutes,
            confidence=confidence,
            trend=trend,
            risk_level=risk_level,
            metadata={
                "data_points": len(values),
                "std": std,
                "mean": mean,
                "change_rate": change_rate
            }
        )

        # 更新缓存
        self._prediction_cache[cache_key] = prediction

        return prediction

    async def detect_anomalies(
        self,
        metric_name: str,
        threshold_multiplier: float = 3.0,
        datasource: Optional[str] = None
    ) -> List[Anomaly]:
        """检测异常"""
        # 获取历史数据
        historical_data = await self.get_historical_metrics(
            metric_name,
            hours=24,
            datasource=datasource
        )

        if len(historical_data) < 10:
            return []

        timestamps, values = zip(*historical_data)
        values = list(values)

        # 使用最新值进行检测
        current_value = values[-1]
        historical_values = values[:-1]

        anomalies = []

        # 3-sigma 检测
        is_anomaly, expected_value, std = self._analyzer.detect_3sigma(
            historical_values,
            current_value
        )

        if is_anomaly:
            # 判断异常类型
            if current_value > expected_value + threshold_multiplier * std:
                anomaly_type = AnomalyType.VALUE_SPIKE.value
            else:
                anomaly_type = AnomalyType.VALUE_DROP.value

            # 计算异常分数
            anomaly_score = abs(current_value - expected_value) / std if std > 0 else 1.0
            anomaly_score = min(1.0, anomaly_score / 5.0)  # 归一化到 0-1

            anomaly = Anomaly(
                metric_name=metric_name,
                anomaly_type=anomaly_type,
                anomaly_score=anomaly_score,
                expected_value=expected_value,
                actual_value=current_value,
                metadata={
                    "std": std,
                    "threshold_multiplier": threshold_multiplier,
                    "datasource": datasource
                }
            )
            anomalies.append(anomaly)

            # 记录到历史
            if metric_name not in self._anomaly_history:
                self._anomaly_history[metric_name] = []
            self._anomaly_history[metric_name].append(anomaly)

        # 趋势变化检测
        if len(values) >= 10:
            recent_trend = self._analyzer.detect_trend(values[-5:])
            old_trend = self._analyzer.detect_trend(values[-10:-5])

            if recent_trend != old_trend and recent_trend != "stable":
                anomaly = Anomaly(
                    metric_name=metric_name,
                    anomaly_type=AnomalyType.TREND_CHANGE.value,
                    anomaly_score=0.7,
                    expected_value=values[-10],
                    actual_value=current_value,
                    metadata={
                        "old_trend": old_trend,
                        "new_trend": recent_trend
                    }
                )
                anomalies.append(anomaly)

        return anomalies

    async def generate_self_healing_recommendation(
        self,
        anomaly: Anomaly
    ) -> SelfHealingRecommendation:
        """生成自愈建议"""
        recommendations = []

        # 根据异常类型生成建议
        if anomaly.anomaly_type == AnomalyType.VALUE_SPIKE.value:
            # 值突增 - 可能是负载过高
            if "query_latency" in anomaly.metric_name:
                recommendations.append(SelfHealingRecommendation(
                    anomaly_id=anomaly.id,
                    action_type=SelfHealingAction.CACHE_WARM.value,
                    description="检测到查询延迟突增，建议预热缓存",
                    expected_impact="降低查询延迟 30-50%",
                    confidence=PredictionConfidence.MEDIUM.value,
                    parameters={
                        "cache_type": "query_result",
                        "warmup_queries": ["top_10_frequent"]
                    }
                ))

            if "connection" in anomaly.metric_name:
                recommendations.append(SelfHealingRecommendation(
                    anomaly_id=anomaly.id,
                    action_type=SelfHealingAction.CONNECTION_POOL_ADJUST.value,
                    description="检测到连接池使用率突增，建议扩容连接池",
                    expected_impact="提升并发处理能力",
                    confidence=PredictionConfidence.HIGH.value,
                    parameters={
                        "action": "increase",
                        "adjustment_factor": 1.5
                    }
                ))

        elif anomaly.anomaly_type == AnomalyType.VALUE_DROP.value:
            # 值突降 - 可能是服务异常
            if "qps" in anomaly.metric_name or "query" in anomaly.metric_name:
                recommendations.append(SelfHealingRecommendation(
                    anomaly_id=anomaly.id,
                    action_type=SelfHealingAction.RATE_LIMIT.value,
                    description="检测到查询量突降，可能存在服务异常，建议检查并临时限流保护",
                    expected_impact="防止问题扩大",
                    confidence=PredictionConfidence.LOW.value,
                    parameters={
                        "action": "check_health",
                        "fallback": "enable_rate_limit"
                    }
                ))

        # 根据异常分数生成通用建议
        if anomaly.anomaly_score > 0.8:
            recommendations.append(SelfHealingRecommendation(
                anomaly_id=anomaly.id,
                action_type=SelfHealingAction.QUERY_OPTIMIZE.value,
                description="检测到严重异常，建议分析慢查询日志并优化",
                expected_impact="提升系统稳定性",
                confidence=PredictionConfidence.MEDIUM.value,
                parameters={
                    "action": "analyze_slow_queries",
                    "threshold_ms": 1000
                }
            ))

        return recommendations[0] if recommendations else None

    async def get_capacity_forecast(
        self,
        days_ahead: int = 7
    ) -> Dict[str, Any]:
        """容量预测"""
        # 获取关键容量指标
        capacity_metrics = [
            "connection_pool_usage",
            "query_latency_ms_avg",
            "concurrent_queries"
        ]

        forecasts = {}

        for metric_name in capacity_metrics:
            prediction = await self.predict_metric(
                metric_name,
                horizon_minutes=days_ahead * 24 * 60
            )

            forecasts[metric_name] = prediction.to_dict()

        # 容量风险评估
        overall_risk = "low"
        risk_factors = []

        for metric_name, pred in forecasts.items():
            if pred.get("risk_level") in ["high", "critical"]:
                risk_factors.append(metric_name)

        if len(risk_factors) >= 2:
            overall_risk = "critical"
        elif len(risk_factors) >= 1:
            overall_risk = "high"
        elif any(p.get("risk_level") == "medium" for p in forecasts.values()):
            overall_risk = "medium"

        return {
            "forecasts": forecasts,
            "overall_risk": overall_risk,
            "risk_factors": risk_factors,
            "forecast_horizon_days": days_ahead,
            "generated_at": datetime.utcnow().isoformat()
        }

    async def analyze_query_performance(
        self,
        datasource: Optional[str] = None
    ) -> Dict[str, Any]:
        """分析查询性能趋势"""
        metrics = [
            "query_latency_ms",
            "query_total",
            "concurrent_queries"
        ]

        analysis = {}

        for metric_name in metrics:
            # 获取历史数据
            historical_data = await self.get_historical_metrics(
                metric_name,
                hours=24,
                datasource=datasource
            )

            if not historical_data:
                continue

            timestamps, values = zip(*historical_data)
            values = list(values)

            # 计算统计信息
            mean = sum(values) / len(values)
            std = self._analyzer.calculate_std(values)
            p50 = sorted(values)[len(values) // 2]
            p95 = sorted(values)[int(len(values) * 0.95)]
            p99 = sorted(values)[int(len(values) * 0.99)]

            analysis[metric_name] = {
                "mean": mean,
                "std": std,
                "p50": p50,
                "p95": p95,
                "p99": p99,
                "min": min(values),
                "max": max(values),
                "data_points": len(values)
            }

        return analysis

    async def get_anomaly_history(
        self,
        metric_name: Optional[str] = None,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """获取异常历史"""
        if metric_name:
            anomalies = self._anomaly_history.get(metric_name, [])
        else:
            anomalies = []
            for metric_anomalies in self._anomaly_history.values():
                anomalies.extend(metric_anomalies)

        # 按时间过滤
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        filtered = [a for a in anomalies if a.detected_at >= cutoff]

        return [a.to_dict() for a in filtered]


# 全局服务实例
predictive_monitoring_service = PredictiveMonitoringService()
