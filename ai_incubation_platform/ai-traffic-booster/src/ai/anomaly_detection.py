"""
AI 异常检测服务

功能:
- 统计显著性异常识别 (Z-score, Grubbs 检验)
- 多维度异常检测 (流量、转化率、跳出率等)
- 异常自动告警推送
- 异常严重度分级
"""
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from enum import Enum
import logging
import math

from schemas.analytics import TrafficOverviewRequest
from analytics.service import analytics_service

logger = logging.getLogger(__name__)


class AnomalySeverity(str, Enum):
    """异常严重度分级"""
    CRITICAL = "critical"  # 严重异常，需要立即处理
    WARNING = "warning"    # 警告级别，需要关注
    INFO = "info"          # 信息级别，可供参考


class AnomalyType(str, Enum):
    """异常类型枚举"""
    TRAFFIC_DROP = "traffic_drop"           # 流量下跌
    TRAFFIC_SPIKE = "traffic_spike"         # 流量激增
    CONVERSION_DROP = "conversion_drop"     # 转化率下跌
    CONVERSION_SPIKE = "conversion_spike"   # 转化率激增
    BOUNCE_RATE_SPIKE = "bounce_rate_spike" # 跳出率激增
    RANKING_DROP = "ranking_drop"           # 排名下跌


class AnomalyDetectionResult:
    """异常检测结果"""
    def __init__(
        self,
        is_anomaly: bool,
        anomaly_type: Optional[AnomalyType],
        severity: Optional[AnomalySeverity],
        metric_name: str,
        current_value: float,
        expected_value: float,
        deviation: float,  # 偏离程度（百分比）
        z_score: float,
        confidence: float,  # 置信度
        description: str,
        detected_at: datetime = None
    ):
        self.is_anomaly = is_anomaly
        self.anomaly_type = anomaly_type
        self.severity = severity
        self.metric_name = metric_name
        self.current_value = current_value
        self.expected_value = expected_value
        self.deviation = deviation
        self.z_score = z_score
        self.confidence = confidence
        self.description = description
        self.detected_at = detected_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_anomaly": self.is_anomaly,
            "anomaly_type": self.anomaly_type.value if self.anomaly_type else None,
            "severity": self.severity.value if self.severity else None,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "expected_value": self.expected_value,
            "deviation": round(self.deviation, 4),
            "z_score": round(self.z_score, 2),
            "confidence": round(self.confidence, 4),
            "description": self.description,
            "detected_at": self.detected_at.isoformat()
        }


class AnomalyDetectionService:
    """
    AI 异常检测服务

    使用统计学方法进行异常检测:
    - Z-score: 检测偏离均值的标准差数
    - Grubbs 检验: 检测单个异常值
    - 移动平均: 检测趋势异常
    """

    def __init__(self):
        # 异常检测阈值配置
        self.z_score_warning_threshold = 2.0    # Z 分数超过 2 为警告
        self.z_score_critical_threshold = 3.0   # Z 分数超过 3 为严重
        self.min_sample_size = 7                # 最小样本量（至少 7 天数据）
        self.significance_level = 0.05          # 显著性水平

    def detect_anomalies(
        self,
        metric_name: str,
        current_value: float,
        historical_values: List[float],
        context: Optional[Dict[str, Any]] = None
    ) -> AnomalyDetectionResult:
        """
        检测单个指标的异常

        Args:
            metric_name: 指标名称
            current_value: 当前值
            historical_values: 历史值列表（用于建立基线）
            context: 上下文信息（可选）

        Returns:
            AnomalyDetectionResult: 异常检测结果
        """
        if len(historical_values) < self.min_sample_size:
            logger.warning(f"样本量不足 ({len(historical_values)} < {self.min_sample_size}), 无法进行可靠的异常检测")
            return self._create_normal_result(
                metric_name, current_value,
                "样本量不足，无法进行可靠的异常检测"
            )

        # 计算统计量
        mean, std = self._calculate_statistics(historical_values)

        if std == 0 or mean == 0:
            return self._create_normal_result(
                metric_name, current_value,
                "数据方差为 0，无法进行异常检测"
            )

        # 计算 Z-score
        z_score = (current_value - mean) / std

        # 计算偏离程度
        deviation = (current_value - mean) / mean

        # 判断是否异常
        is_anomaly = abs(z_score) > self.z_score_warning_threshold

        if not is_anomaly:
            return self._create_normal_result(
                metric_name, current_value,
                f"Z-score ({z_score:.2f}) 在正常范围内",
                mean, z_score
            )

        # 确定异常类型和严重度
        severity = self._determine_severity(z_score)
        anomaly_type = self._determine_anomaly_type(metric_name, z_score, deviation)

        # 生成描述
        description = self._generate_description(
            metric_name, current_value, mean, std, z_score, deviation, severity
        )

        # 计算置信度
        confidence = self._calculate_confidence(z_score, len(historical_values))

        return AnomalyDetectionResult(
            is_anomaly=True,
            anomaly_type=anomaly_type,
            severity=severity,
            metric_name=metric_name,
            current_value=current_value,
            expected_value=mean,
            deviation=deviation,
            z_score=z_score,
            confidence=confidence,
            description=description
        )

    def detect_traffic_anomaly(
        self,
        domain: Optional[str] = None,
        check_date: Optional[date] = None
    ) -> List[AnomalyDetectionResult]:
        """
        检测流量相关指标的异常

        Args:
            domain: 域名（可选）
            check_date: 检查日期（默认为昨天）

        Returns:
            异常检测结果列表
        """
        if check_date is None:
            check_date = date.today() - timedelta(days=1)

        # 获取历史数据（过去 30 天）
        end_date = check_date - timedelta(days=1)
        start_date = end_date - timedelta(days=30)

        results = []

        # 获取流量概览数据
        request = TrafficOverviewRequest(
            start_date=start_date,
            end_date=end_date,
            domain=domain
        )

        try:
            overview = analytics_service.get_traffic_overview(request)

            # 获取每日趋势数据
            daily_trend = overview.daily_trend

            if len(daily_trend) < self.min_sample_size:
                logger.warning("历史数据不足，无法进行异常检测")
                return results

            # 提取各指标的日度数据
            visitors_history = [d["visitors"] for d in daily_trend]
            page_views_history = [d["page_views"] for d in daily_trend]
            conversion_rate_history = [d["conversion_rate"] for d in daily_trend]
            bounce_rate_history = [d["bounce_rate"] for d in daily_trend]

            # 获取今天的_mock_数据（实际应该从实时数据获取）
            today_request = TrafficOverviewRequest(
                start_date=check_date,
                end_date=check_date,
                domain=domain
            )
            today_overview = analytics_service.get_traffic_overview(today_request)
            today_metrics = today_overview.total

            # 检测各指标异常
            metrics_to_check = [
                ("visitors", today_metrics.visitors, visitors_history),
                ("page_views", today_metrics.page_views, page_views_history),
                ("conversion_rate", today_metrics.conversion_rate, conversion_rate_history),
                ("bounce_rate", today_metrics.bounce_rate, bounce_rate_history),
            ]

            for metric_name, current_value, history in metrics_to_check:
                result = self.detect_anomalies(metric_name, current_value, history)
                if result.is_anomaly:
                    results.append(result)

        except Exception as e:
            logger.error(f"流量异常检测失败：{e}")

        return results

    def detect_keyword_ranking_anomaly(
        self,
        keyword: str,
        current_position: int,
        historical_positions: List[int]
    ) -> AnomalyDetectionResult:
        """
        检测关键词排名异常

        Args:
            keyword: 关键词
            current_position: 当前排名
            historical_positions: 历史排名列表

        Returns:
            异常检测结果
        """
        # 排名是反向指标（数值越小越好），需要特殊处理
        return self.detect_anomalies(
            f"keyword_ranking_{keyword}",
            current_position,
            historical_positions,
            context={"keyword": keyword}
        )

    def grubbs_test(self, values: List[float]) -> Tuple[bool, float, int]:
        """
        Grubbs 检验 - 检测单个异常值

        Args:
            values: 数据列表

        Returns:
            (is_outlier, G_critical, outlier_index)
        """
        n = len(values)
        if n < 3:
            return False, 0, -1

        mean = sum(values) / n
        std = math.sqrt(sum((x - mean) ** 2 for x in values) / (n - 1))

        if std == 0:
            return False, 0, -1

        # 找到偏离最大的值
        deviations = [abs(x - mean) / std for x in values]
        max_g = max(deviations)
        outlier_idx = deviations.index(max_g)

        # 计算临界值（α=0.05）
        # 使用近似公式
        t_critical = 2.0  # 简化处理
        g_critical = ((n - 1) / math.sqrt(n)) * math.sqrt(t_critical ** 2 / (n - 2 + t_critical ** 2))

        is_outlier = max_g > g_critical

        return is_outlier, g_critical, outlier_idx if is_outlier else -1

    def _calculate_statistics(self, values: List[float]) -> Tuple[float, float]:
        """计算均值和标准差"""
        n = len(values)
        mean = sum(values) / n
        variance = sum((x - mean) ** 2 for x in values) / (n - 1)
        std = math.sqrt(variance)
        return mean, std

    def _determine_severity(self, z_score: float) -> AnomalySeverity:
        """根据 Z 分数确定严重度"""
        abs_z = abs(z_score)
        if abs_z >= self.z_score_critical_threshold:
            return AnomalySeverity.CRITICAL
        elif abs_z >= self.z_score_warning_threshold:
            return AnomalySeverity.WARNING
        else:
            return AnomalySeverity.INFO

    def _determine_anomaly_type(
        self,
        metric_name: str,
        z_score: float,
        deviation: float
    ) -> AnomalyType:
        """确定异常类型"""
        is_positive = z_score > 0  # 正值表示高于预期

        if "visitors" in metric_name or "page_views" in metric_name or "traffic" in metric_name:
            return AnomalyType.TRAFFIC_SPIKE if is_positive else AnomalyType.TRAFFIC_DROP
        elif "conversion" in metric_name:
            return AnomalyType.CONVERSION_SPIKE if is_positive else AnomalyType.CONVERSION_DROP
        elif "bounce" in metric_name:
            return AnomalyType.BOUNCE_RATE_SPIKE if is_positive else AnomalySeverity.INFO
        elif "ranking" in metric_name:
            return AnomalyType.RANKING_DROP if is_positive else AnomalyType.TRAFFIC_SPIKE

        return AnomalyType.TRAFFIC_DROP if not is_positive else AnomalyType.TRAFFIC_SPIKE

    def _generate_description(
        self,
        metric_name: str,
        current_value: float,
        mean: float,
        std: float,
        z_score: float,
        deviation: float,
        severity: AnomalySeverity
    ) -> str:
        """生成异常描述"""
        direction = "高于" if z_score > 0 else "低于"
        pct = abs(deviation) * 100

        if severity == AnomalySeverity.CRITICAL:
            level = "严重"
        elif severity == AnomalySeverity.WARNING:
            level = "显著"
        else:
            level = "轻微"

        return (
            f"[{level}异常] {metric_name} {direction}预期值{pct:.1f}% "
            f"(当前值：{current_value:.2f}, 预期值：{mean:.2f}, "
            f"Z-score: {z_score:.2f})"
        )

    def _calculate_confidence(self, z_score: float, sample_size: int) -> float:
        """
        计算检测置信度

        考虑因素:
        - Z 分数大小
        - 样本量
        """
        # 基于 Z 分数的基础置信度
        base_confidence = min(1.0, abs(z_score) / 4.0)

        # 样本量修正
        sample_factor = min(1.0, sample_size / 30.0)

        return base_confidence * (0.5 + 0.5 * sample_factor)

    def _create_normal_result(
        self,
        metric_name: str,
        current_value: float,
        description: str,
        expected_value: float = None,
        z_score: float = 0
    ) -> AnomalyDetectionResult:
        """创建正常状态结果"""
        return AnomalyDetectionResult(
            is_anomaly=False,
            anomaly_type=None,
            severity=None,
            metric_name=metric_name,
            current_value=current_value,
            expected_value=expected_value if expected_value else current_value,
            deviation=0,
            z_score=z_score,
            confidence=1.0,
            description=description
        )


# 全局服务实例
anomaly_detection_service = AnomalyDetectionService()
