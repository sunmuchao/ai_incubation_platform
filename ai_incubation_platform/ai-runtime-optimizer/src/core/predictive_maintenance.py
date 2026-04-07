"""
预测性维护 v1 模块：LSTM 时序预测、容量预测、故障预测
对标 Dynatrace Davis 预测能力和 New Relic 预测性分析
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

try:
    from sklearn.preprocessing import MinMaxScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)


class PredictionType(str, Enum):
    """预测类型"""
    CAPACITY = "capacity"  # 容量预测
    FAILURE = "failure"  # 故障预测
    TREND = "trend"  # 趋势预测
    ANOMALY = "anomaly"  # 异常预测


class AlertLevel(str, Enum):
    """预警级别"""
    CRITICAL = "critical"  # 紧急预警
    WARNING = "warning"  # 警告
    INFO = "info"  # 信息


@dataclass
class PredictionResult:
    """预测结果"""
    prediction_type: PredictionType
    service_name: str
    metric_name: str
    current_value: float
    predicted_values: List[float]  # 预测值序列
    prediction_timestamps: List[datetime]  # 预测时间点
    confidence_interval_lower: List[float]  # 置信区间下界
    confidence_interval_upper: List[float]  # 置信区间上界
    confidence_level: float  # 置信度 (0-1)
    trend: str  # "increasing", "decreasing", "stable"
    alert_level: Optional[AlertLevel] = None
    alert_message: Optional[str] = None
    time_to_threshold: Optional[timedelta] = None  # 到达阈值的时间
    recommended_actions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_type": self.prediction_type.value,
            "service_name": self.service_name,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "predicted_values": self.predicted_values,
            "prediction_timestamps": [ts.isoformat() for ts in self.prediction_timestamps],
            "confidence_interval_lower": self.confidence_interval_lower,
            "confidence_interval_upper": self.confidence_interval_upper,
            "confidence_level": self.confidence_level,
            "trend": self.trend,
            "alert_level": self.alert_level.value if self.alert_level else None,
            "alert_message": self.alert_message,
            "time_to_threshold_hours": self.time_to_threshold.total_seconds() / 3600 if self.time_to_threshold else None,
            "recommended_actions": self.recommended_actions
        }


@dataclass
class CapacityForecast:
    """容量预测"""
    resource_type: str  # cpu, memory, storage, etc.
    current_usage: float
    predicted_usage: float
    capacity_limit: float
    usage_percentage: float
    predicted_usage_percentage: float
    days_until_capacity: Optional[int] = None
    alert_level: Optional[AlertLevel] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_type": self.resource_type,
            "current_usage": self.current_usage,
            "predicted_usage": self.predicted_usage,
            "capacity_limit": self.capacity_limit,
            "usage_percentage": self.usage_percentage,
            "predicted_usage_percentage": self.predicted_usage_percentage,
            "days_until_capacity": self.days_until_capacity,
            "alert_level": self.alert_level.value if self.alert_level else None
        }


@dataclass
class FailurePrediction:
    """故障预测"""
    service_name: str
    failure_probability: float  # 故障概率 (0-1)
    failure_risk_level: str  # "low", "medium", "high", "critical"
    predicted_failure_time: Optional[datetime] = None
    failure_mode: Optional[str] = None  # 故障模式
    contributing_factors: List[str] = field(default_factory=list)
    preventive_actions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "failure_probability": self.failure_probability,
            "failure_risk_level": self.failure_risk_level,
            "predicted_failure_time": self.predicted_failure_time.isoformat() if self.predicted_failure_time else None,
            "failure_mode": self.failure_mode,
            "contributing_factors": self.contributing_factors,
            "preventive_actions": self.preventive_actions
        }


class SimpleLSTMPredictor:
    """
    简化版 LSTM 预测器
    使用指数加权移动平均 (EWMA) 和线性回归模拟 LSTM 行为
    在没有 TensorFlow/PyTorch 时提供基础预测能力
    """

    def __init__(self, lookback_days: int = 7, prediction_horizon_hours: int = 24):
        self.lookback_days = lookback_days
        self.prediction_horizon_hours = prediction_horizon_hours
        self._history: List[Tuple[datetime, float]] = []
        self._ewma_value: Optional[float] = None
        self._ewma_alpha: float = 0.3  # EWMA 平滑系数
        self._trend_slope: float = 0.0
        self._seasonal_factors: Dict[int, float] = {}  # 小时 -> 季节因子

    def add_sample(self, timestamp: datetime, value: float):
        """添加训练样本"""
        self._history.append((timestamp, value))

        # 限制历史数据大小
        cutoff = datetime.utcnow() - timedelta(days=self.lookback_days * 2)
        self._history = [(t, v) for t, v in self._history if t > cutoff]

        # 更新 EWMA
        if self._ewma_value is None:
            self._ewma_value = value
        else:
            self._ewma_value = self._ewma_alpha * value + (1 - self._ewma_alpha) * self._ewma_value

        # 更新趋势
        self._update_trend()

        # 更新季节因子
        self._update_seasonal_factors()

    def _update_trend(self):
        """使用线性回归更新趋势"""
        if len(self._history) < 10:
            return

        # 简单线性回归
        n = len(self._history)
        sorted_history = sorted(self._history, key=lambda x: x[0])

        # 归一化时间戳
        base_time = sorted_history[0][0]
        x_values = [(t - base_time).total_seconds() / 3600 for t, _ in sorted_history]  # 小时
        y_values = [v for _, v in sorted_history]

        # 计算斜率
        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n

        numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))

        if denominator > 0:
            self._trend_slope = numerator / denominator

    def _update_seasonal_factors(self):
        """更新小时季节因子"""
        hourly_values: Dict[int, List[float]] = defaultdict(list)

        for timestamp, value in self._history:
            hour = timestamp.hour
            hourly_values[hour].append(value)

        if self._ewma_value is None:
            return

        for hour, values in hourly_values.items():
            if len(values) >= 3:
                hourly_mean = sum(values) / len(values)
                self._seasonal_factors[hour] = hourly_mean / self._ewma_value if self._ewma_value > 0 else 1.0

    def predict(
        self,
        horizon_hours: int = None,
        confidence_level: float = 0.95
    ) -> Tuple[List[float], List[datetime], List[float], List[float]]:
        """
        预测未来值

        Returns:
            (predicted_values, timestamps, lower_bound, upper_bound)
        """
        if horizon_hours is None:
            horizon_hours = self.prediction_horizon_hours

        if self._ewma_value is None or len(self._history) < 10:
            # 数据不足，返回恒定值
            base_value = self._ewma_value if self._ewma_value else 0
            timestamps = [datetime.utcnow() + timedelta(hours=i) for i in range(horizon_hours)]
            return (
                [base_value] * horizon_hours,
                timestamps,
                [base_value * 0.8] * horizon_hours,
                [base_value * 1.2] * horizon_hours
            )

        # 计算残差标准差
        residuals = []
        for i in range(1, len(self._history)):
            predicted = self._ewma_value + self._trend_slope * ((self._history[i][0] - self._history[0][0]).total_seconds() / 3600)
            residuals.append(self._history[i][1] - predicted)

        if residuals:
            residual_std = math.sqrt(sum(r ** 2 for r in residuals) / len(residuals))
        else:
            residual_std = self._ewma_value * 0.1

        # Z-score 用于置信区间
        z_score = 1.96 if confidence_level == 0.95 else 2.58

        # 生成预测
        predicted_values = []
        timestamps = []
        lower_bounds = []
        upper_bounds = []

        base_time = datetime.utcnow()
        current_value = self._ewma_value

        for i in range(horizon_hours):
            future_time = base_time + timedelta(hours=i)

            # 基础预测 = EWMA + 趋势
            base_prediction = current_value + self._trend_slope * i

            # 应用季节因子
            hour = future_time.hour
            seasonal_factor = self._seasonal_factors.get(hour, 1.0)
            prediction = base_prediction * seasonal_factor

            # 置信区间随时间扩大
            time_factor = math.sqrt(i + 1)
            margin = z_score * residual_std * time_factor

            predicted_values.append(max(0, prediction))
            timestamps.append(future_time)
            lower_bounds.append(max(0, prediction - margin))
            upper_bounds.append(prediction + margin)

        return predicted_values, timestamps, lower_bounds, upper_bounds

    def get_trend(self) -> str:
        """获取趋势方向"""
        if abs(self._trend_slope) < 0.001:
            return "stable"
        elif self._trend_slope > 0:
            return "increasing"
        else:
            return "decreasing"

    def get_days_until_threshold(self, threshold: float) -> Optional[int]:
        """计算到达阈值的天数"""
        if self._ewma_value is None:
            return None

        if self._trend_slope <= 0 and self._ewma_value < threshold:
            return None  # 递减趋势且当前值低于阈值

        if self._ewma_value >= threshold:
            return 0

        # 计算到达阈值的时间
        hours_until = (threshold - self._ewma_value) / self._trend_slope if self._trend_slope > 0 else float('inf')
        return max(0, int(hours_until / 24))


class FailurePredictor:
    """
    故障预测器
    基于多指标融合和资源耗尽趋势预测故障
    """

    def __init__(self):
        self._service_predictors: Dict[str, Dict[str, SimpleLSTMPredictor]] = defaultdict(dict)
        self._failure_thresholds = {
            "cpu_percent": 95.0,
            "memory_percent": 95.0,
            "disk_percent": 98.0,
            "error_rate": 0.1,
            "latency_p99_ms": 5000
        }
        self._failure_history: List[FailurePrediction] = []

    def record_metric(self, service_name: str, metric_name: str, value: float, timestamp: datetime = None):
        """记录指标"""
        if timestamp is None:
            timestamp = datetime.utcnow()

        if metric_name not in self._service_predictors[service_name]:
            self._service_predictors[service_name][metric_name] = SimpleLSTMPredictor()

        self._service_predictors[service_name][metric_name].add_sample(timestamp, value)

    def predict_failure(self, service_name: str) -> Optional[FailurePrediction]:
        """预测服务故障"""
        if service_name not in self._service_predictors:
            return None

        predictors = self._service_predictors[service_name]
        if not predictors:
            return None

        failure_signals = []
        contributing_factors = []
        max_failure_probability = 0.0
        predicted_failure_time = None

        for metric_name, predictor in predictors.items():
            threshold = self._failure_thresholds.get(metric_name, float('inf'))

            # 获取当前 EWMA 值
            current_value = predictor._ewma_value
            if current_value is None:
                continue

            # 计算当前使用率
            current_ratio = current_value / threshold if threshold > 0 else 0

            # 获取预测
            predicted_values, timestamps, _, _ = predictor.predict(horizon_hours=24)

            if not predicted_values:
                continue

            # 检查是否会超过阈值
            for i, pred_value in enumerate(predicted_values):
                if pred_value >= threshold:
                    time_to_threshold = timestamps[i] - datetime.utcnow()
                    failure_probability = min(1.0, current_ratio * 0.5 + 0.5)

                    if failure_probability > max_failure_probability:
                        max_failure_probability = failure_probability
                        predicted_failure_time = timestamps[i]

                    failure_signals.append({
                        "metric": metric_name,
                        "current_value": current_value,
                        "threshold": threshold,
                        "predicted_value": pred_value,
                        "time_to_threshold": time_to_threshold
                    })
                    contributing_factors.append(
                        f"{metric_name} 预计在 {time_to_threshold.total_seconds() / 3600:.1f} 小时后达到阈值 ({pred_value:.1f} >= {threshold})"
                    )
                    break

        if not failure_signals:
            # 没有明显的故障信号，但基于当前状态评估风险
            avg_ratio = 0
            count = 0
            for metric_name, predictor in predictors.items():
                if predictor._ewma_value:
                    threshold = self._failure_thresholds.get(metric_name, float('inf'))
                    avg_ratio += predictor._ewma_value / threshold
                    count += 1

            if count > 0:
                avg_ratio /= count
                max_failure_probability = avg_ratio * 0.5

        # 确定风险级别
        if max_failure_probability >= 0.8:
            risk_level = "critical"
        elif max_failure_probability >= 0.6:
            risk_level = "high"
        elif max_failure_probability >= 0.4:
            risk_level = "medium"
        else:
            risk_level = "low"

        # 生成预防建议
        preventive_actions = self._generate_preventive_actions(failure_signals, service_name)

        prediction = FailurePrediction(
            service_name=service_name,
            failure_probability=max_failure_probability,
            failure_risk_level=risk_level,
            predicted_failure_time=predicted_failure_time,
            failure_mode=self._infer_failure_mode(failure_signals),
            contributing_factors=contributing_factors,
            preventive_actions=preventive_actions
        )

        self._failure_history.append(prediction)
        return prediction

    def _infer_failure_mode(self, failure_signals: List[Dict]) -> Optional[str]:
        """推断故障模式"""
        if not failure_signals:
            return None

        metrics = [s["metric"] for s in failure_signals]

        if "cpu_percent" in metrics:
            return "resource_exhaustion_cpu"
        elif "memory_percent" in metrics:
            return "resource_exhaustion_memory"
        elif "disk_percent" in metrics:
            return "resource_exhaustion_storage"
        elif "error_rate" in metrics:
            return "cascading_failure"
        elif "latency_p99_ms" in metrics:
            return "performance_degradation"

        return "unknown"

    def _generate_preventive_actions(self, failure_signals: List[Dict], service_name: str) -> List[str]:
        """生成预防建议"""
        actions = []

        metrics = [s["metric"] for s in failure_signals]

        if "cpu_percent" in metrics:
            actions.append(f"考虑为 {service_name} 增加 CPU 资源或进行水平扩展")
            actions.append("检查是否有低效的 CPU 密集型操作")

        if "memory_percent" in metrics:
            actions.append(f"检查 {service_name} 是否有内存泄漏")
            actions.append("考虑增加内存限制或优化内存使用")

        if "disk_percent" in metrics:
            actions.append("清理不必要的文件或日志")
            actions.append("考虑扩展存储或启用数据归档")

        if "error_rate" in metrics:
            actions.append("检查依赖服务的健康状态")
            actions.append("查看错误日志以识别根本原因")

        if "latency_p99_ms" in metrics:
            actions.append("分析慢查询和性能瓶颈")
            actions.append("考虑优化数据库查询或增加缓存")

        if not actions:
            actions.append("持续监控服务健康状态")
            actions.append("准备应急预案")

        return actions


class PredictiveMaintenanceEngine:
    """
    预测性维护引擎
    整合 LSTM 预测、容量预测和故障预测
    """

    def __init__(self):
        self._lstm_predictors: Dict[str, Dict[str, SimpleLSTMPredictor]] = defaultdict(dict)
        self._failure_predictor = FailurePredictor()
        self._capacity_limits: Dict[str, Dict[str, float]] = {}  # service -> metric -> limit
        self._predictions_history: List[PredictionResult] = []

        # 默认容量限制
        self._default_limits = {
            "cpu_percent": 100.0,
            "memory_percent": 100.0,
            "memory_mb": 16384,  # 16GB
            "disk_percent": 100.0,
            "disk_gb": 1000,  # 1TB
            "error_rate": 1.0,  # 100%
            "latency_p99_ms": 10000,  # 10 秒
            "requests_per_second": 10000
        }

    def set_capacity_limit(self, service_name: str, metric_name: str, limit: float):
        """设置容量限制"""
        if service_name not in self._capacity_limits:
            self._capacity_limits[service_name] = {}
        self._capacity_limits[service_name][metric_name] = limit

    def record_metric(
        self,
        service_name: str,
        metric_name: str,
        value: float,
        timestamp: datetime = None
    ):
        """记录指标用于预测"""
        if timestamp is None:
            timestamp = datetime.utcnow()

        # 初始化预测器
        if metric_name not in self._lstm_predictors[service_name]:
            self._lstm_predictors[service_name][metric_name] = SimpleLSTMPredictor()

        self._lstm_predictors[service_name][metric_name].add_sample(timestamp, value)

        # 同时记录到故障预测器
        self._failure_predictor.record_metric(service_name, metric_name, value, timestamp)

    def predict_capacity(
        self,
        service_name: str,
        metric_name: str = None,
        horizon_hours: int = 168  # 7 天
    ) -> List[CapacityForecast]:
        """
        容量预测

        Args:
            service_name: 服务名称
            metric_name: 指标名称（可选，不传则预测所有容量指标）
            horizon_hours: 预测视野（小时）

        Returns:
            容量预测列表
        """
        forecasts = []

        if service_name not in self._lstm_predictors:
            return forecasts

        metrics_to_predict = [metric_name] if metric_name else list(self._lstm_predictors[service_name].keys())

        for metric in metrics_to_predict:
            if metric not in self._lstm_predictors[service_name]:
                continue

            predictor = self._lstm_predictors[service_name][metric]
            limit = self._get_capacity_limit(service_name, metric)

            current_value = predictor._ewma_value
            if current_value is None:
                continue

            predicted_values, timestamps, _, _ = predictor.predict(horizon_hours=horizon_hours)

            if not predicted_values:
                continue

            # 取最后一个预测值作为代表性预测
            final_predicted = predicted_values[-1]

            # 计算使用率
            current_usage_pct = (current_value / limit) * 100 if limit > 0 else 0
            predicted_usage_pct = (final_predicted / limit) * 100 if limit > 0 else 0

            # 计算到达容量的天数
            days_until = predictor.get_days_until_threshold(limit)

            # 确定预警级别
            if predicted_usage_pct >= 95:
                alert_level = AlertLevel.CRITICAL
            elif predicted_usage_pct >= 85:
                alert_level = AlertLevel.WARNING
            elif predicted_usage_pct >= 70:
                alert_level = AlertLevel.INFO
            else:
                alert_level = None

            forecast = CapacityForecast(
                resource_type=metric,
                current_usage=current_value,
                predicted_usage=final_predicted,
                capacity_limit=limit,
                usage_percentage=current_usage_pct,
                predicted_usage_percentage=predicted_usage_pct,
                days_until_capacity=days_until,
                alert_level=alert_level
            )
            forecasts.append(forecast)

        return forecasts

    def predict_failure(self, service_name: str) -> Optional[FailurePrediction]:
        """
        故障预测

        Args:
            service_name: 服务名称

        Returns:
            故障预测结果
        """
        return self._failure_predictor.predict_failure(service_name)

    def predict_trend(
        self,
        service_name: str,
        metric_name: str,
        horizon_hours: int = 24
    ) -> Optional[PredictionResult]:
        """
        趋势预测

        Args:
            service_name: 服务名称
            metric_name: 指标名称
            horizon_hours: 预测视野（小时）

        Returns:
            趋势预测结果
        """
        if service_name not in self._lstm_predictors:
            return None

        if metric_name not in self._lstm_predictors[service_name]:
            return None

        predictor = self._lstm_predictors[service_name][metric_name]
        current_value = predictor._ewma_value

        if current_value is None:
            return None

        predicted_values, timestamps, lower_bounds, upper_bounds = predictor.predict(horizon_hours=horizon_hours)

        # 计算趋势
        trend = predictor.get_trend()

        # 计算置信度
        if len(predictor._history) >= 100:
            confidence_level = 0.9
        elif len(predictor._history) >= 50:
            confidence_level = 0.75
        elif len(predictor._history) >= 20:
            confidence_level = 0.6
        else:
            confidence_level = 0.4

        # 检查是否需要预警
        limit = self._get_capacity_limit(service_name, metric_name)
        alert_level = None
        alert_message = None
        time_to_threshold = None

        for i, pred_value in enumerate(predicted_values):
            if pred_value >= limit * 0.9:
                alert_level = AlertLevel.CRITICAL
                alert_message = f"{metric_name} 预计在 {i} 小时后达到容量的 90%"
                time_to_threshold = timedelta(hours=i)
                break
            elif pred_value >= limit * 0.75:
                alert_level = AlertLevel.WARNING
                alert_message = f"{metric_name} 预计在 {i} 小时后达到容量的 75%"
                time_to_threshold = timedelta(hours=i)

        # 生成建议
        recommended_actions = self._generate_recommendations(service_name, metric_name, trend, current_value, limit)

        result = PredictionResult(
            prediction_type=PredictionType.TREND,
            service_name=service_name,
            metric_name=metric_name,
            current_value=current_value,
            predicted_values=predicted_values,
            prediction_timestamps=timestamps,
            confidence_interval_lower=lower_bounds,
            confidence_interval_upper=upper_bounds,
            confidence_level=confidence_level,
            trend=trend,
            alert_level=alert_level,
            alert_message=alert_message,
            time_to_threshold=time_to_threshold,
            recommended_actions=recommended_actions
        )

        self._predictions_history.append(result)
        return result

    def _get_capacity_limit(self, service_name: str, metric_name: str) -> float:
        """获取容量限制"""
        # 优先使用自定义限制
        if service_name in self._capacity_limits:
            if metric_name in self._capacity_limits[service_name]:
                return self._capacity_limits[service_name][metric_name]

        # 使用默认限制
        return self._default_limits.get(metric_name, float('inf'))

    def _generate_recommendations(
        self,
        service_name: str,
        metric_name: str,
        trend: str,
        current_value: float,
        limit: float
    ) -> List[str]:
        """生成建议操作"""
        recommendations = []

        usage_pct = (current_value / limit) * 100 if limit > 0 else 0

        if trend == "increasing":
            if usage_pct >= 80:
                recommendations.append(f"立即扩展 {service_name} 的 {metric_name} 资源")
                recommendations.append("分析资源消耗增长的原因")
            elif usage_pct >= 60:
                recommendations.append("规划容量扩展方案")
                recommendations.append("设置自动扩展策略")
            else:
                recommendations.append("持续监控资源使用趋势")

        elif trend == "decreasing":
            recommendations.append("分析资源使用下降的原因（可能是流量下降或优化生效）")
            if usage_pct < 30:
                recommendations.append("考虑缩减资源以节省成本")

        else:  # stable
            if usage_pct >= 70:
                recommendations.append("当前使用率较高，建议规划扩容")
            else:
                recommendations.append("资源使用稳定，保持当前配置")

        # 基于指标类型的特定建议
        if "cpu" in metric_name.lower():
            recommendations.append("考虑使用 CPU 性能分析工具识别热点代码")
        elif "memory" in metric_name.lower():
            recommendations.append("检查内存泄漏和 GC 频率")
        elif "disk" in metric_name.lower() or "storage" in metric_name.lower():
            recommendations.append("实施日志轮转和数据归档策略")

        return recommendations

    def get_prediction_history(
        self,
        service_name: str = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取预测历史"""
        results = self._predictions_history

        if service_name:
            results = [r for r in results if r.service_name == service_name]

        return [r.to_dict() for r in results[-limit:]]

    def get_all_capacity_forecasts(self) -> List[Dict[str, Any]]:
        """获取所有容量预测"""
        all_forecasts = []

        for service_name in self._lstm_predictors:
            forecasts = self.predict_capacity(service_name)
            for forecast in forecasts:
                forecast_dict = forecast.to_dict()
                forecast_dict["service_name"] = service_name
                all_forecasts.append(forecast_dict)

        return all_forecasts

    def get_all_failure_predictions(self) -> List[Dict[str, Any]]:
        """获取所有故障预测"""
        all_predictions = []

        for service_name in self._lstm_predictors:
            prediction = self.predict_failure(service_name)
            if prediction:
                prediction_dict = prediction.to_dict()
                all_predictions.append(prediction_dict)

        return all_predictions


# 全局实例
_predictive_maintenance_engine: Optional[PredictiveMaintenanceEngine] = None


def get_predictive_maintenance_engine() -> PredictiveMaintenanceEngine:
    """获取预测性维护引擎实例"""
    global _predictive_maintenance_engine
    if _predictive_maintenance_engine is None:
        _predictive_maintenance_engine = PredictiveMaintenanceEngine()
    return _predictive_maintenance_engine
