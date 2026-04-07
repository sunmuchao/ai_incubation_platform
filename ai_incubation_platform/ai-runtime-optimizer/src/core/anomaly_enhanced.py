"""
AI 异常检测增强模块：多算法融合、自适应阈值、季节性模式识别
对标 Datadog Watchdog 和 Dynatrace Davis AI 能力
"""
import logging
import statistics
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict

try:
    import numpy as np
    from sklearn.ensemble import IsolationForest
    from sklearn.svm import OneClassSVM
    from sklearn.preprocessing import StandardScaler
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

from core.anomaly_detector import AnomalyDetector, AnomalyEvent, AnomalyType, AnomalySeverity

logger = logging.getLogger(__name__)


class AlgorithmType(str, Enum):
    """算法类型"""
    ISOLATION_FOREST = "isolation_forest"
    ONE_CLASS_SVM = "one_class_svm"
    AUTOENCODER = "autoencoder"
    EMA = "ema"
    SEASONAL = "seasonal"
    FUSION = "fusion"


@dataclass
class MLModelConfig:
    """ML 模型配置"""
    algorithm: AlgorithmType
    service_name: Optional[str] = None
    metric_name: Optional[str] = None

    # Isolation Forest 配置
    n_estimators: int = 100
    contamination: float = 0.01
    max_samples: int = 256

    # One-Class SVM 配置
    kernel: str = "rbf"
    nu: float = 0.05
    gamma: str = "scale"

    # Autoencoder 配置 (占位)
    encoding_dim: int = 8
    epochs: int = 50
    batch_size: int = 32

    # 通用配置
    window_size: int = 100  # 滑动窗口大小
    stride: int = 1  # 步长
    min_training_samples: int = 50  # 最小训练样本

    enabled: bool = True
    tags: List[str] = field(default_factory=list)


@dataclass
class MLModelResult:
    """ML 模型检测结果"""
    algorithm: AlgorithmType
    is_anomaly: bool
    score: float  # 异常分数
    confidence: float  # 置信度
    threshold: float  # 使用的阈值
    explanation: str  # 解释
    model_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnomalyExplanation:
    """异常解释"""
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    algorithm_scores: Dict[str, MLModelResult]
    fusion_score: float
    fusion_decision: bool
    contributing_factors: List[str]
    suggested_actions: List[str]
    similar_historical_patterns: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SeasonalPattern:
    """季节性模式"""
    period_hours: int
    pattern_type: str  # "hourly", "daily", "weekly"
    hourly_profiles: Dict[int, Dict[str, float]]  # hour -> {mean, std}
    confidence: float
    data_points: int
    last_updated: datetime


class IsolationForestDetector:
    """孤立森林异常检测器"""

    def __init__(self, config: MLModelConfig):
        self.config = config
        self._model = None
        self._scaler = None
        self._training_data: List[float] = []
        self._is_trained = False

    def add_sample(self, value: float):
        """添加训练样本"""
        self._training_data.append(value)

        # 自动训练
        if len(self._training_data) >= self.config.min_training_samples:
            self._train()

    def _train(self):
        """训练模型"""
        if not ML_AVAILABLE:
            logger.warning("ML libraries not available, skipping Isolation Forest training")
            return

        if len(self._training_data) < self.config.min_training_samples:
            return

        try:
            # 准备数据
            data = np.array(self._training_data[-self.config.window_size:]).reshape(-1, 1)

            # 标准化
            self._scaler = StandardScaler()
            data_scaled = self._scaler.fit_transform(data)

            # 训练孤立森林
            self._model = IsolationForest(
                n_estimators=self.config.n_estimators,
                contamination=self.config.contamination,
                max_samples=min(self.config.max_samples, len(data)),
                random_state=42,
                n_jobs=-1
            )
            self._model.fit(data_scaled)
            self._is_trained = True

            logger.debug(f"Isolation Forest trained with {len(data)} samples")
        except Exception as e:
            logger.error(f"Isolation Forest training failed: {e}")

    def predict(self, value: float) -> MLModelResult:
        """预测是否为异常"""
        if not self._is_trained or self._model is None:
            return MLModelResult(
                algorithm=AlgorithmType.ISOLATION_FOREST,
                is_anomaly=False,
                score=0.0,
                confidence=0.0,
                threshold=0.0,
                explanation="Model not trained yet"
            )

        try:
            data = np.array([[value]])
            data_scaled = self._scaler.transform(data)

            # 获取异常分数（负数表示正常，正数表示异常）
            prediction = self._model.predict(data_scaled)[0]
            score = -self._model.score_samples(data_scaled)[0]

            is_anomaly = prediction == -1

            # 计算置信度
            confidence = min(1.0, abs(score) / 3.0)

            explanation = f"Isolation Forest: score={score:.3f}, threshold=0"
            if is_anomaly:
                explanation += f", ANOMALY detected with confidence {confidence:.2f}"

            return MLModelResult(
                algorithm=AlgorithmType.ISOLATION_FOREST,
                is_anomaly=is_anomaly,
                score=score,
                confidence=confidence,
                threshold=0.0,
                explanation=explanation,
                model_metadata={"n_estimators": self.config.n_estimators}
            )
        except Exception as e:
            logger.error(f"Isolation Forest prediction failed: {e}")
            return MLModelResult(
                algorithm=AlgorithmType.ISOLATION_FOREST,
                is_anomaly=False,
                score=0.0,
                confidence=0.0,
                threshold=0.0,
                explanation=f"Prediction failed: {e}"
            )


class OneClassSVMDetector:
    """One-Class SVM 异常检测器"""

    def __init__(self, config: MLModelConfig):
        self.config = config
        self._model = None
        self._scaler = None
        self._training_data: List[float] = []
        self._is_trained = False

    def add_sample(self, value: float):
        """添加训练样本"""
        self._training_data.append(value)

        # 自动训练
        if len(self._training_data) >= self.config.min_training_samples:
            self._train()

    def _train(self):
        """训练模型"""
        if not ML_AVAILABLE:
            logger.warning("ML libraries not available, skipping One-Class SVM training")
            return

        if len(self._training_data) < self.config.min_training_samples:
            return

        try:
            # 准备数据
            data = np.array(self._training_data[-self.config.window_size:]).reshape(-1, 1)

            # 标准化
            self._scaler = StandardScaler()
            data_scaled = self._scaler.fit_transform(data)

            # 训练 One-Class SVM
            self._model = OneClassSVM(
                kernel=self.config.kernel,
                nu=self.config.nu,
                gamma=self.config.gamma
            )
            self._model.fit(data_scaled)
            self._is_trained = True

            logger.debug(f"One-Class SVM trained with {len(data)} samples")
        except Exception as e:
            logger.error(f"One-Class SVM training failed: {e}")

    def predict(self, value: float) -> MLModelResult:
        """预测是否为异常"""
        if not self._is_trained or self._model is None:
            return MLModelResult(
                algorithm=AlgorithmType.ONE_CLASS_SVM,
                is_anomaly=False,
                score=0.0,
                confidence=0.0,
                threshold=0.0,
                explanation="Model not trained yet"
            )

        try:
            data = np.array([[value]])
            data_scaled = self._scaler.transform(data)

            # 获取预测结果
            prediction = self._model.predict(data_scaled)[0]
            score = self._model.decision_function(data_scaled)[0]

            is_anomaly = prediction == -1

            # 计算置信度
            confidence = min(1.0, abs(score) / 3.0)

            explanation = f"One-Class SVM: score={score:.3f}"
            if is_anomaly:
                explanation += f", ANOMALY detected with confidence {confidence:.2f}"

            return MLModelResult(
                algorithm=AlgorithmType.ONE_CLASS_SVM,
                is_anomaly=is_anomaly,
                score=score,
                confidence=confidence,
                threshold=0.0,
                explanation=explanation,
                model_metadata={"kernel": self.config.kernel, "nu": self.config.nu}
            )
        except Exception as e:
            logger.error(f"One-Class SVM prediction failed: {e}")
            return MLModelResult(
                algorithm=AlgorithmType.ONE_CLASS_SVM,
                is_anomaly=False,
                score=0.0,
                confidence=0.0,
                threshold=0.0,
                explanation=f"Prediction failed: {e}"
            )


class AdaptiveThresholdCalculator:
    """自适应阈值计算器"""

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self._values: List[float] = []
        self._thresholds: Dict[str, float] = {}

    def add_value(self, value: float):
        """添加值"""
        self._values.append(value)
        if len(self._values) > self.window_size:
            self._values = self._values[-self.window_size:]

    def calculate_thresholds(self, std_multiplier: float = 3.0) -> Dict[str, float]:
        """计算自适应阈值"""
        if len(self._values) < 10:
            return {}

        mean_val = statistics.mean(self._values)
        std_val = statistics.stdev(self._values)

        # 使用 IQR 方法计算稳健阈值
        sorted_vals = sorted(self._values)
        q1_idx = len(sorted_vals) // 4
        q3_idx = 3 * len(sorted_vals) // 4
        q1 = sorted_vals[q1_idx]
        q3 = sorted_vals[q3_idx]
        iqr = q3 - q1

        # 动态阈值
        upper_threshold_iqr = q3 + 1.5 * iqr
        lower_threshold_iqr = q1 - 1.5 * iqr

        # 标准差阈值
        upper_threshold_std = mean_val + std_multiplier * std_val
        lower_threshold_std = mean_val - std_multiplier * std_val

        # 融合阈值（取更保守的）
        upper_threshold = min(upper_threshold_iqr, upper_threshold_std)
        lower_threshold = max(lower_threshold_iqr, lower_threshold_std)

        self._thresholds = {
            "mean": mean_val,
            "std": std_val,
            "q1": q1,
            "q3": q3,
            "iqr": iqr,
            "upper": upper_threshold,
            "lower": lower_threshold,
            "upper_std": upper_threshold_std,
            "lower_std": lower_threshold_std
        }

        return self._thresholds

    def is_anomaly(self, value: float) -> Tuple[bool, Dict[str, Any]]:
        """判断是否为异常"""
        if not self._thresholds:
            self.calculate_thresholds()

        if not self._thresholds:
            return False, {}

        upper = self._thresholds.get("upper", float('inf'))
        lower = self._thresholds.get("lower", float('-inf'))
        mean = self._thresholds.get("mean", 0)
        std = self._thresholds.get("std", 1)

        is_anomaly = value > upper or value < lower

        z_score = (value - mean) / std if std > 0 else 0

        return is_anomaly, {
            "z_score": z_score,
            "upper_threshold": upper,
            "lower_threshold": lower,
            "mean": mean,
            "std": std
        }


class SeasonalPatternDetector:
    """季节性模式检测器"""

    def __init__(self, period_hours: int = 24, min_samples_per_hour: int = 5):
        self.period_hours = period_hours
        self.min_samples_per_hour = min_samples_per_hour
        self._hourly_data: Dict[int, List[float]] = defaultdict(list)
        self._pattern: Optional[SeasonalPattern] = None

    def add_value(self, value: float, timestamp: Optional[datetime] = None):
        """添加值"""
        if timestamp is None:
            timestamp = datetime.utcnow()

        hour = timestamp.hour
        self._hourly_data[hour].append(value)

        # 更新模式
        self._update_pattern()

    def _update_pattern(self):
        """更新季节性模式"""
        hourly_profiles = {}

        for hour, values in self._hourly_data.items():
            if len(values) >= self.min_samples_per_hour:
                hourly_profiles[hour] = {
                    "mean": statistics.mean(values),
                    "std": statistics.stdev(values) if len(values) > 1 else 0,
                    "min": min(values),
                    "max": max(values),
                    "count": len(values)
                }

        if hourly_profiles:
            # 计算模式置信度
            total_samples = sum(p["count"] for p in hourly_profiles.values())
            confidence = min(1.0, total_samples / (self.period_hours * self.min_samples_per_hour))

            self._pattern = SeasonalPattern(
                period_hours=self.period_hours,
                pattern_type="hourly",
                hourly_profiles=hourly_profiles,
                confidence=confidence,
                data_points=total_samples,
                last_updated=datetime.utcnow()
            )

    def get_expected(self, timestamp: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """获取期望值"""
        if timestamp is None:
            timestamp = datetime.utcnow()

        if not self._pattern:
            return None

        hour = timestamp.hour
        if hour not in self._pattern.hourly_profiles:
            return None

        profile = self._pattern.hourly_profiles[hour]
        return {
            "expected_mean": profile["mean"],
            "expected_std": profile["std"],
            "expected_range": [profile["min"], profile["max"]],
            "confidence": self._pattern.confidence,
            "data_points": profile["count"]
        }

    def is_seasonal_anomaly(self, value: float, timestamp: Optional[datetime] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """判断是否为季节性异常"""
        expected = self.get_expected(timestamp)

        if not expected:
            return False, None

        z_score = (value - expected["expected_mean"]) / expected["expected_std"] if expected["expected_std"] > 0 else 0

        is_anomaly = abs(z_score) > 3.0

        return is_anomaly, {
            "value": value,
            "expected": expected["expected_mean"],
            "z_score": z_score,
            "is_anomaly": is_anomaly
        }


class EnhancedAnomalyDetector:
    """增强型异常检测器"""

    def __init__(self):
        self._base_detector = AnomalyDetector()

        # ML 检测器配置
        self._ml_configs: Dict[str, MLModelConfig] = {}
        self._if_detectors: Dict[str, IsolationForestDetector] = {}
        self._svm_detectors: Dict[str, OneClassSVMDetector] = {}

        # 自适应阈值
        self._threshold_calculators: Dict[str, AdaptiveThresholdCalculator] = {}

        # 季节性模式
        self._seasonal_detectors: Dict[str, SeasonalPatternDetector] = {}

        # 异常历史
        self._anomaly_history: List[AnomalyEvent] = []
        self._feedback_history: List[Dict[str, Any]] = []

        # 融合配置
        self.fusion_weights = {
            AlgorithmType.ISOLATION_FOREST: 0.3,
            AlgorithmType.ONE_CLASS_SVM: 0.3,
            AlgorithmType.EMA: 0.2,
            AlgorithmType.SEASONAL: 0.2
        }
        self.fusion_threshold = 0.5  # 融合分数阈值

    def configure_ml_model(self, config: MLModelConfig) -> str:
        """配置 ML 模型"""
        key = f"{config.service_name or 'global'}:{config.metric_name or 'default'}"
        self._ml_configs[key] = config

        if config.algorithm == AlgorithmType.ISOLATION_FOREST:
            self._if_detectors[key] = IsolationForestDetector(config)
        elif config.algorithm == AlgorithmType.ONE_CLASS_SVM:
            self._svm_detectors[key] = OneClassSVMDetector(config)

        logger.info(f"ML model configured: {key} - {config.algorithm.value}")
        return key

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

        key = f"{service_name}:{metric_name}"

        # 初始化组件
        if key not in self._threshold_calculators:
            self._threshold_calculators[key] = AdaptiveThresholdCalculator()
            self._seasonal_detectors[key] = SeasonalPatternDetector()

        # 记录到基础检测器
        base_anomaly = self._base_detector.record_metric(service_name, metric_name, value, timestamp)

        # 更新自适应阈值
        self._threshold_calculators[key].add_value(value)

        # 更新季节性模式
        self._seasonal_detectors[key].add_value(value, timestamp)

        # 更新 ML 检测器
        self._update_ml_detectors(key, value)

        # 多算法融合检测
        fusion_result = self._fusion_detect(service_name, metric_name, value, timestamp)

        if fusion_result and fusion_result.fusion_decision:
            # 创建增强异常事件
            enhanced_anomaly = self._create_enhanced_anomaly(
                service_name, metric_name, value, timestamp, fusion_result
            )
            self._anomaly_history.append(enhanced_anomaly)
            return enhanced_anomaly

        return base_anomaly

    def _update_ml_detectors(self, key: str, value: float):
        """更新 ML 检测器"""
        if key in self._if_detectors:
            self._if_detectors[key].add_sample(value)

        if key in self._svm_detectors:
            self._svm_detectors[key].add_sample(value)

    def _fusion_detect(
        self,
        service_name: str,
        metric_name: str,
        value: float,
        timestamp: datetime
    ) -> Optional[AnomalyExplanation]:
        """多算法融合检测"""
        key = f"{service_name}:{metric_name}"

        results: Dict[str, MLModelResult] = {}

        # Isolation Forest
        if key in self._if_detectors:
            results[AlgorithmType.ISOLATION_FOREST.value] = self._if_detectors[key].predict(value)

        # One-Class SVM
        if key in self._svm_detectors:
            results[AlgorithmType.ONE_CLASS_SVM.value] = self._svm_detectors[key].predict(value)

        # 自适应阈值
        threshold_calc = self._threshold_calculators.get(key)
        if threshold_calc:
            is_anomaly, threshold_info = threshold_calc.is_anomaly(value)
            results["adaptive_threshold"] = MLModelResult(
                algorithm="adaptive_threshold",
                is_anomaly=is_anomaly,
                score=threshold_info.get("z_score", 0),
                confidence=abs(threshold_info.get("z_score", 0)) / 3.0,
                threshold=threshold_info.get("upper", 0),
                explanation=f"Adaptive threshold: z_score={threshold_info.get('z_score', 0):.2f}"
            )

        # 季节性检测
        seasonal_calc = self._seasonal_detectors.get(key)
        if seasonal_calc:
            is_anomaly, seasonal_info = seasonal_calc.is_seasonal_anomaly(value, timestamp)
            if seasonal_info:
                results["seasonal"] = MLModelResult(
                    algorithm="seasonal",
                    is_anomaly=is_anomaly,
                    score=seasonal_info.get("z_score", 0),
                    confidence=seasonal_info.get("confidence", 0),
                    threshold=3.0,
                    explanation=f"Seasonal anomaly: expected={seasonal_info.get('expected', 0):.2f}"
                )

        # 融合决策
        fusion_score = 0.0
        total_weight = 0.0

        for algo, result in results.items():
            weight = self.fusion_weights.get(algo, 0.1)
            if result.is_anomaly:
                fusion_score += weight * result.confidence
            total_weight += weight

        if total_weight > 0:
            fusion_score /= total_weight

        fusion_decision = fusion_score >= self.fusion_threshold

        # 生成解释
        contributing_factors = []
        for algo, result in results.items():
            if result.is_anomaly:
                contributing_factors.append(f"{algo}: {result.explanation}")

        suggested_actions = self._generate_suggested_actions(service_name, metric_name, value, results)

        return AnomalyExplanation(
            anomaly_type=self._infer_anomaly_type(value, results),
            severity=self._infer_severity(fusion_score, results),
            algorithm_scores=results,
            fusion_score=fusion_score,
            fusion_decision=fusion_decision,
            contributing_factors=contributing_factors,
            suggested_actions=suggested_actions
        )

    def _infer_anomaly_type(self, value: float, results: Dict) -> AnomalyType:
        """推断异常类型"""
        # 基于各算法结果推断异常类型
        for algo, result in results.items():
            if "spike" in result.explanation.lower() or result.score > 2:
                return AnomalyType.SPIKE
            elif "drop" in result.explanation.lower() or result.score < -2:
                return AnomalyType.DROP

        return AnomalyType.OUTLIER

    def _infer_severity(self, fusion_score: float, results: Dict) -> AnomalySeverity:
        """推断严重程度"""
        if fusion_score >= 0.8:
            return AnomalySeverity.CRITICAL
        elif fusion_score >= 0.6:
            return AnomalySeverity.HIGH
        elif fusion_score >= 0.4:
            return AnomalySeverity.MEDIUM
        else:
            return AnomalySeverity.LOW

    def _generate_suggested_actions(
        self,
        service_name: str,
        metric_name: str,
        value: float,
        results: Dict
    ) -> List[str]:
        """生成建议操作"""
        actions = []

        # 基于异常类型生成建议
        if any(r.is_anomaly for r in results.values()):
            if "cpu" in metric_name.lower():
                actions.append("检查 CPU 使用率突增的进程")
                actions.append("考虑水平扩展或增加资源")
            elif "memory" in metric_name.lower():
                actions.append("检查内存泄漏")
                actions.append("分析 GC 日志")
            elif "latency" in metric_name.lower() or "p99" in metric_name.lower():
                actions.append("检查依赖服务响应时间")
                actions.append("分析慢查询日志")
            elif "error" in metric_name.lower():
                actions.append("检查错误日志和堆栈跟踪")
                actions.append("回滚最近的部署变更")

        return actions

    def _create_enhanced_anomaly(
        self,
        service_name: str,
        metric_name: str,
        value: float,
        timestamp: datetime,
        explanation: AnomalyExplanation
    ) -> AnomalyEvent:
        """创建增强异常事件"""
        import uuid

        return AnomalyEvent(
            id=f"enhanced-anomaly-{uuid.uuid4().hex[:12]}",
            service_name=service_name,
            metric_name=metric_name,
            anomaly_type=explanation.anomaly_type,
            severity=explanation.severity,
            current_value=value,
            expected_value=0,
            deviation=0,
            confidence=explanation.fusion_score,
            message=" | ".join(explanation.contributing_factors),
            timestamp=timestamp,
            context={
                "fusion_score": explanation.fusion_score,
                "algorithm_scores": {k: v.score for k, v in explanation.algorithm_scores.items()},
                "suggested_actions": explanation.suggested_actions
            }
        )

    def submit_feedback(self, anomaly_id: str, is_true_positive: bool, feedback_type: str = "manual"):
        """提交反馈用于模型改进"""
        self._feedback_history.append({
            "anomaly_id": anomaly_id,
            "is_true_positive": is_true_positive,
            "feedback_type": feedback_type,
            "timestamp": datetime.utcnow()
        })

        # 基于反馈调整模型
        self._adjust_model_based_on_feedback(anomaly_id, is_true_positive)

    def _adjust_model_based_on_feedback(self, anomaly_id: str, is_true_positive: bool):
        """基于反馈调整模型"""
        # 找到对应的异常
        anomaly = next((a for a in self._anomaly_history if a.id == anomaly_id), None)
        if not anomaly:
            return

        # 如果是误报，降低灵敏度
        if not is_true_positive:
            self.fusion_threshold += 0.05  # 提高阈值
            logger.info(f"Adjusted fusion threshold to {self.fusion_threshold:.2f} due to false positive")
        else:
            # 如果是漏报，提高灵敏度
            self.fusion_threshold = max(0.3, self.fusion_threshold - 0.05)
            logger.info(f"Adjusted fusion threshold to {self.fusion_threshold:.2f} due to true positive")

    def get_anomaly_explanation(self, anomaly_id: str) -> Optional[Dict[str, Any]]:
        """获取异常详细解释"""
        anomaly = next((a for a in self._anomaly_history if a.id == anomaly_id), None)
        if not anomaly:
            return None

        return {
            "anomaly_id": anomaly.id,
            "service_name": anomaly.service_name,
            "metric_name": anomaly.metric_name,
            "anomaly_type": anomaly.anomaly_type.value,
            "severity": anomaly.severity.value,
            "current_value": anomaly.current_value,
            "confidence": anomaly.confidence,
            "timestamp": anomaly.timestamp.isoformat(),
            "message": anomaly.message,
            "context": anomaly.context,
            "suggested_actions": anomaly.context.get("suggested_actions", [])
        }

    def get_model_performance(self) -> Dict[str, Any]:
        """获取模型性能指标"""
        total_feedback = len(self._feedback_history)
        true_positives = sum(1 for f in self._feedback_history if f["is_true_positive"])

        return {
            "total_anomalies_detected": len(self._anomaly_history),
            "total_feedback": total_feedback,
            "true_positives": true_positives,
            "false_positives": total_feedback - true_positives,
            "precision": true_positives / total_feedback if total_feedback > 0 else 0,
            "fusion_threshold": self.fusion_threshold,
            "ml_models_configured": len(self._ml_configs),
            "ml_models_trained": len(self._if_detectors) + len(self._svm_detectors)
        }


# 全局实例
enhanced_anomaly_detector = EnhancedAnomalyDetector()
