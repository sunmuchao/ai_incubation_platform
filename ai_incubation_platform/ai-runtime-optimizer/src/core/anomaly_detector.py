"""
AI 异常检测：基于历史数据的动态阈值、趋势预测与异常预警
对标 Datadog Watchdog 和 AI 异常检测能力
"""
import logging
import math
import statistics
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import heapq

logger = logging.getLogger(__name__)


class AnomalyType(str, Enum):
    """异常类型"""
    SPIKE = "spike"  # 突刺
    DROP = "drop"  # 骤降
    TREND_CHANGE = "trend_change"  # 趋势变化
    SEASONAL_ANOMALY = "seasonal_anomaly"  # 季节性异常
    LEVEL_SHIFT = "level_shift"  # 水平偏移
    OUTLIER = "outlier"  # 离群值


class AnomalySeverity(str, Enum):
    """异常严重程度"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class DataPoint:
    """数据点"""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnomalyEvent:
    """异常事件"""
    id: str
    service_name: str
    metric_name: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    current_value: float
    expected_value: float
    deviation: float  # 偏离程度（百分比）
    confidence: float  # 置信度 0-1
    message: str
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimeSeriesStats:
    """时间序列统计"""
    mean: float
    std_dev: float
    min_value: float
    max_value: float
    p50: float
    p95: float
    p99: float
    trend_slope: float  # 趋势斜率
    seasonality_period: Optional[int] = None  # 季节性周期（小时）
    data_points: int = 0


class ExponentialMovingAverage:
    """指数移动平均模型"""

    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha
        self.value: Optional[float] = None
        self.variance: float = 0.0
        self.count: int = 0

    def update(self, value: float) -> Tuple[float, float]:
        """更新 EMA 并返回预测值和标准差"""
        if self.value is None:
            self.value = value
            self.variance = 0.0
        else:
            diff = value - self.value
            self.value = self.alpha * value + (1 - self.alpha) * self.value
            self.variance = (1 - self.alpha) * (self.variance + self.alpha * diff * diff)

        self.count += 1
        std_dev = math.sqrt(self.variance) if self.variance > 0 else 0.01
        return self.value, std_dev

    def predict(self) -> Tuple[float, float]:
        """返回当前预测值和置信区间"""
        if self.value is None:
            return 0.0, float('inf')
        std_dev = math.sqrt(self.variance) if self.variance > 0 else 0.01
        return self.value, std_dev


class SeasonalModel:
    """季节性模型（按小时）"""

    def __init__(self, period_hours: int = 24):
        self.period_hours = period_hours
        self.hourly_means: Dict[int, float] = {}
        self.hourly_counts: Dict[int, int] = {}
        self.global_mean: float = 0.0

    def update(self, timestamp: datetime, value: float):
        """更新季节性模型"""
        hour = timestamp.hour

        if hour not in self.hourly_means:
            self.hourly_means[hour] = value
            self.hourly_counts[hour] = 1
        else:
            # 指数移动平均更新
            alpha = 0.3
            old_mean = self.hourly_means[hour]
            count = self.hourly_counts[hour]
            self.hourly_means[hour] = old_mean + alpha * (value - old_mean)
            self.hourly_counts[hour] = count + 1

        # 更新全局均值（只计算已有数据的小时）
        total_count = sum(self.hourly_counts.values())
        if total_count > 0:
            self.global_mean = sum(
                self.hourly_means[h] * self.hourly_counts.get(h, 0)
                for h in self.hourly_means.keys()
            ) / total_count

    def get_expected(self, timestamp: datetime) -> Tuple[float, float]:
        """获取期望值和标准差"""
        hour = timestamp.hour

        if hour in self.hourly_means:
            seasonal_value = self.hourly_means[hour]
            # 使用季节性值和全局均值的加权平均
            expected = 0.7 * seasonal_value + 0.3 * self.global_mean
            # 标准差估计为均值的 10%
            std_dev = max(abs(expected) * 0.1, 0.01)
            return expected, std_dev
        else:
            return self.global_mean, max(abs(self.global_mean) * 0.2, 0.01)


class AnomalyDetector:
    """异常检测器"""

    def __init__(
        self,
        ema_alpha: float = 0.3,
        spike_threshold_std: float = 3.0,
        min_data_points: int = 30,
        seasonal_period_hours: int = 24
    ):
        self.ema_alpha = ema_alpha
        self.spike_threshold_std = spike_threshold_std
        self.min_data_points = min_data_points

        # 每个服务 - 指标组合的检测器
        self._ema_models: Dict[str, ExponentialMovingAverage] = {}
        self._seasonal_models: Dict[str, SeasonalModel] = {}
        self._data_history: Dict[str, List[DataPoint]] = defaultdict(list)
        self._max_history_size = 1000

        # 异常历史
        self._anomaly_history: List[AnomalyEvent] = []
        self._anomaly_counts: Dict[str, int] = defaultdict(int)

        # 趋势检测
        self._trend_windows: Dict[str, List[float]] = defaultdict(list)
        self._trend_window_size = 10

        # 异常抑制（避免告警风暴）
        self._last_anomaly_time: Dict[str, datetime] = {}
        self._anomaly_cooldown_seconds = 300  # 5 分钟冷却

    def _get_model_key(self, service_name: str, metric_name: str) -> str:
        """生成模型键"""
        return f"{service_name}:{metric_name}"

    def record_metric(
        self,
        service_name: str,
        metric_name: str,
        value: float,
        timestamp: Optional[datetime] = None
    ) -> Optional[AnomalyEvent]:
        """记录指标并检测异常"""
        if timestamp is None:
            timestamp = datetime.utcnow()

        model_key = self._get_model_key(service_name, metric_name)

        # 初始化模型
        if model_key not in self._ema_models:
            self._ema_models[model_key] = ExponentialMovingAverage(self.ema_alpha)
            self._seasonal_models[model_key] = SeasonalModel()

        ema_model = self._ema_models[model_key]
        seasonal_model = self._seasonal_models[model_key]

        # 更新模型
        ema_predicted, ema_std = ema_model.update(value)
        seasonal_model.update(timestamp, value)
        seasonal_expected, seasonal_std = seasonal_model.get_expected(timestamp)

        # 记录历史数据
        data_point = DataPoint(
            timestamp=timestamp,
            value=value,
            metadata={"ema_predicted": ema_predicted, "seasonal_expected": seasonal_expected}
        )
        self._data_history[model_key].append(data_point)
        if len(self._data_history[model_key]) > self._max_history_size:
            self._data_history[model_key] = self._data_history[model_key][-self._max_history_size:]

        # 更新趋势窗口
        self._trend_windows[model_key].append(value)
        if len(self._trend_windows[model_key]) > self._trend_window_size:
            self._trend_windows[model_key] = self._trend_windows[model_key][-self._trend_window_size:]

        # 检查是否有足够的数据进行检测
        if ema_model.count < self.min_data_points:
            return None

        # 检测异常
        anomaly = self._detect_anomaly(
            service_name=service_name,
            metric_name=metric_name,
            current_value=value,
            ema_predicted=ema_predicted,
            ema_std=ema_std,
            seasonal_expected=seasonal_expected,
            seasonal_std=seasonal_std,
            timestamp=timestamp
        )

        if anomaly:
            self._anomaly_history.append(anomaly)
            self._anomaly_counts[model_key] += 1
            self._last_anomaly_time[model_key] = timestamp
            logger.warning(f"Anomaly detected: {anomaly.anomaly_type.value} - {anomaly.message}")

        return anomaly

    def _detect_anomaly(
        self,
        service_name: str,
        metric_name: str,
        current_value: float,
        ema_predicted: float,
        ema_std: float,
        seasonal_expected: float,
        seasonal_std: float,
        timestamp: datetime
    ) -> Optional[AnomalyEvent]:
        """检测异常"""
        model_key = self._get_model_key(service_name, metric_name)

        # 检查冷却时间
        last_anomaly = self._last_anomaly_time.get(model_key)
        if last_anomaly and (timestamp - last_anomaly).total_seconds() < self._anomaly_cooldown_seconds:
            return None

        anomaly_type = None
        severity = None
        expected_value = None
        deviation = 0.0
        confidence = 0.0
        message = ""

        # 1. 检测突刺/骤降（基于 EMA）
        z_score = (current_value - ema_predicted) / ema_std if ema_std > 0 else 0

        if z_score > self.spike_threshold_std:
            anomaly_type = AnomalyType.SPIKE
            severity = self._calculate_severity(abs(z_score), self.spike_threshold_std)
            expected_value = ema_predicted
            deviation = (current_value - ema_predicted) / ema_predicted * 100 if ema_predicted != 0 else float('inf')
            confidence = min(0.99, 0.5 + abs(z_score) * 0.1)
            message = f"指标 {metric_name} 突刺：当前值 {current_value:.2f}，预期值 {ema_predicted:.2f}（+{deviation:.1f}%）"

        elif z_score < -self.spike_threshold_std:
            anomaly_type = AnomalyType.DROP
            severity = self._calculate_severity(abs(z_score), self.spike_threshold_std)
            expected_value = ema_predicted
            deviation = (ema_predicted - current_value) / ema_predicted * 100 if ema_predicted != 0 else float('inf')
            confidence = min(0.99, 0.5 + abs(z_score) * 0.1)
            message = f"指标 {metric_name} 骤降：当前值 {current_value:.2f}，预期值 {ema_predicted:.2f}（-{deviation:.1f}%）"

        # 2. 检测季节性异常
        if anomaly_type is None:
            seasonal_z_score = (current_value - seasonal_expected) / seasonal_std if seasonal_std > 0 else 0
            if abs(seasonal_z_score) > self.spike_threshold_std:
                anomaly_type = AnomalyType.SEASONAL_ANOMALY
                severity = AnomalySeverity.MEDIUM if abs(seasonal_z_score) < 4 else AnomalySeverity.HIGH
                expected_value = seasonal_expected
                deviation = (current_value - seasonal_expected) / seasonal_expected * 100 if seasonal_expected != 0 else float('inf')
                confidence = min(0.95, 0.5 + abs(seasonal_z_score) * 0.1)
                message = f"指标 {metric_name} 季节性异常：当前值 {current_value:.2f}，同期预期值 {seasonal_expected:.2f}"

        # 3. 检测趋势变化
        if anomaly_type is None:
            trend_change = self._detect_trend_change(model_key)
            if trend_change:
                anomaly_type = AnomalyType.TREND_CHANGE
                severity = AnomalySeverity.MEDIUM
                expected_value = trend_change["expected"]
                deviation = trend_change["deviation"] * 100
                confidence = trend_change["confidence"]
                direction = "上升" if trend_change["deviation"] > 0 else "下降"
                message = f"指标 {metric_name} 趋势{direction}：当前趋势偏离预期 {deviation:.1f}%"

        # 4. 检测水平偏移
        if anomaly_type is None:
            level_shift = self._detect_level_shift(model_key)
            if level_shift:
                anomaly_type = AnomalyType.LEVEL_SHIFT
                severity = AnomalySeverity.HIGH
                expected_value = level_shift["old_mean"]
                deviation = level_shift["shift"] / level_shift["old_mean"] * 100 if level_shift["old_mean"] != 0 else float('inf')
                confidence = level_shift["confidence"]
                message = f"指标 {metric_name} 水平偏移：从 {level_shift['old_mean']:.2f} 偏移到 {level_shift['new_mean']:.2f}"

        if anomaly_type:
            return AnomalyEvent(
                id=f"anomaly-{timestamp.strftime('%Y%m%d%H%M%S')}-{model_key[:8]}",
                service_name=service_name,
                metric_name=metric_name,
                anomaly_type=anomaly_type,
                severity=severity,
                current_value=current_value,
                expected_value=expected_value,
                deviation=deviation,
                confidence=confidence,
                message=message,
                timestamp=timestamp,
                context={
                    "ema_predicted": ema_predicted,
                    "ema_std": ema_std,
                    "seasonal_expected": seasonal_expected,
                    "seasonal_std": seasonal_std,
                    "z_score": z_score
                }
            )

        return None

    def _calculate_severity(self, z_score: float, threshold: float) -> AnomalySeverity:
        """根据 Z 分数计算严重程度"""
        if z_score >= threshold * 2:
            return AnomalySeverity.CRITICAL
        elif z_score >= threshold * 1.5:
            return AnomalySeverity.HIGH
        elif z_score >= threshold:
            return AnomalySeverity.MEDIUM
        else:
            return AnomalySeverity.LOW

    def _detect_trend_change(self, model_key: str) -> Optional[Dict[str, Any]]:
        """检测趋势变化"""
        if model_key not in self._trend_windows or len(self._trend_windows[model_key]) < self._trend_window_size:
            return None

        window = self._trend_windows[model_key]
        half = len(window) // 2

        # 比较前后两段的均值
        first_half_mean = statistics.mean(window[:half])
        second_half_mean = statistics.mean(window[half:])

        if first_half_mean == 0:
            return None

        deviation = (second_half_mean - first_half_mean) / first_half_mean

        # 如果变化超过 20%，认为有趋势变化
        if abs(deviation) > 0.2:
            return {
                "expected": first_half_mean,
                "deviation": deviation,
                "confidence": min(0.9, 0.5 + abs(deviation))
            }

        return None

    def _detect_level_shift(self, model_key: str) -> Optional[Dict[str, Any]]:
        """检测水平偏移"""
        if model_key not in self._data_history or len(self._data_history[model_key]) < 50:
            return None

        history = self._data_history[model_key]
        window_size = 10

        # 计算最近窗口和历史窗口
        recent_values = [dp.value for dp in history[-window_size:]]
        old_values = [dp.value for dp in history[-window_size * 3:-window_size]]

        if not old_values:
            return None

        recent_mean = statistics.mean(recent_values)
        old_mean = statistics.mean(old_values)
        old_std = statistics.stdev(old_values) if len(old_values) > 1 else 1

        if old_std == 0:
            old_std = abs(old_mean) * 0.1

        # 如果最近均值偏离历史均值超过 2 个标准差
        shift = recent_mean - old_mean
        if abs(shift) > 2 * old_std:
            return {
                "old_mean": old_mean,
                "new_mean": recent_mean,
                "shift": shift,
                "confidence": min(0.95, 0.5 + abs(shift) / old_std * 0.1)
            }

        return None

    def get_anomaly_stats(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """获取异常统计"""
        anomalies = self._anomaly_history
        if service_name:
            anomalies = [a for a in anomalies if a.service_name == service_name]

        return {
            "total_anomalies": len(anomalies),
            "anomalies_by_type": self._count_anomalies_by_type(anomalies),
            "anomalies_by_severity": self._count_anomalies_by_severity(anomalies),
            "anomalies_by_service": self._count_anomalies_by_service(anomalies),
            "total_anomaly_counts": dict(self._anomaly_counts)
        }

    def _count_anomalies_by_type(self, anomalies: List[AnomalyEvent]) -> Dict[str, int]:
        """按类型统计异常"""
        counts = defaultdict(int)
        for a in anomalies:
            counts[a.anomaly_type.value] += 1
        return dict(counts)

    def _count_anomalies_by_severity(self, anomalies: List[AnomalyEvent]) -> Dict[str, int]:
        """按严重程度统计异常"""
        counts = defaultdict(int)
        for a in anomalies:
            counts[a.severity.value] += 1
        return dict(counts)

    def _count_anomalies_by_service(self, anomalies: List[AnomalyEvent]) -> Dict[str, int]:
        """按服务统计异常"""
        counts = defaultdict(int)
        for a in anomalies:
            counts[a.service_name] += 1
        return dict(counts)

    def get_recent_anomalies(
        self,
        service_name: Optional[str] = None,
        limit: int = 50
    ) -> List[AnomalyEvent]:
        """获取最近的异常"""
        anomalies = self._anomaly_history
        if service_name:
            anomalies = [a for a in anomalies if a.service_name == service_name]
        return sorted(anomalies, key=lambda a: a.timestamp, reverse=True)[:limit]

    def get_time_series_stats(
        self,
        service_name: str,
        metric_name: str
    ) -> Optional[TimeSeriesStats]:
        """获取时间序列统计"""
        model_key = self._get_model_key(service_name, metric_name)

        if model_key not in self._data_history or len(self._data_history[model_key]) < self.min_data_points:
            return None

        values = [dp.value for dp in self._data_history[model_key]]

        # 计算趋势斜率（简单线性回归）
        n = len(values)
        if n < 2:
            trend_slope = 0.0
        else:
            x_mean = (n - 1) / 2
            y_mean = statistics.mean(values)
            numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
            denominator = sum((i - x_mean) ** 2 for i in range(n))
            trend_slope = numerator / denominator if denominator != 0 else 0.0

        return TimeSeriesStats(
            mean=statistics.mean(values),
            std_dev=statistics.stdev(values) if len(values) > 1 else 0.0,
            min_value=min(values),
            max_value=max(values),
            p50=statistics.median(values),
            p95=self._percentile(values, 95),
            p99=self._percentile(values, 99),
            trend_slope=trend_slope,
            data_points=len(values)
        )

    def _percentile(self, data: List[float], percentile: float) -> float:
        """计算百分位数"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * percentile / 100
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_data) else f
        return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])


# 全局异常检测器实例
anomaly_detector = AnomalyDetector()
