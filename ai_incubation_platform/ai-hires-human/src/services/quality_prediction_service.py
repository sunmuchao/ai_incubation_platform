"""
质量预测模型服务。

使用机器学习特征工程预测任务交付质量，提供：
1. 质量风险评分
2. 质量特征分析
3. 预测依据解释
4. 历史质量趋势
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from models.quality_prediction import (
    QualityFeature,
    QualityLevel,
    QualityModelConfig,
    QualityPrediction,
    QualityPredictionRequest,
    QualityPredictionResponse,
)

logger = logging.getLogger(__name__)


class QualityPredictionService:
    """
    质量预测模型服务。

    核心功能：
    1. 基于多特征的质量评分预测
    2. 风险因素识别和解释
    3. 质量改进建议生成
    4. 预测准确率追踪
    """

    def __init__(self, config: Optional[QualityModelConfig] = None):
        self.config = config or QualityModelConfig()
        # 内存存储
        self._predictions: Dict[str, QualityPrediction] = {}
        self._task_predictions: Dict[str, str] = {}  # task_id -> prediction_id

        # 工人历史质量缓存
        self._worker_quality_history: Dict[str, List[float]] = {}
        # 任务类型平均质量缓存
        self._task_type_quality: Dict[str, float] = {}

    def predict_quality(self, request: QualityPredictionRequest) -> QualityPredictionResponse:
        """
        预测任务交付质量。

        Args:
            request: 预测请求

        Returns:
            预测响应，包含质量评分、风险等级和建议
        """
        try:
            # 1. 提取特征
            features = self._extract_features(request)

            # 2. 计算质量得分
            quality_score = self._calculate_quality_score(features)

            # 3. 计算风险得分
            risk_score = self._calculate_risk_score(features, quality_score)

            # 4. 确定质量等级
            quality_level = self._determine_quality_level(quality_score, risk_score)

            # 5. 生成预测解释
            prediction_reason = self._generate_prediction_reason(features, quality_score, risk_score)

            # 6. 识别积极因素和风险因素
            positive_factors, risk_factors = self._analyze_factors(features)

            # 7. 生成建议措施
            recommendations = self._generate_recommendations(
                quality_level, risk_score, risk_factors, features
            )

            # 8. 计算置信度
            confidence = self._calculate_confidence(features, quality_score)

            # 9. 创建预测记录
            prediction = QualityPrediction(
                task_id=request.task_id,
                worker_id=request.worker_id,
                predicted_quality_level=quality_level,
                quality_score=round(quality_score, 3),
                risk_score=round(risk_score, 3),
                confidence=round(confidence, 3),
                prediction_reason=prediction_reason,
                features=features,
                positive_factors=positive_factors,
                risk_factors=risk_factors,
                recommendations=recommendations,
                model_version="rule_based_v1.0",
            )

            # 10. 存储预测结果
            self._predictions[prediction.id] = prediction
            self._task_predictions[request.task_id] = prediction.id

            logger.info(
                "Quality prediction completed: prediction_id=%s, task_id=%s, quality=%s, score=%.3f, risk=%.3f",
                prediction.id,
                request.task_id,
                quality_level.value,
                quality_score,
                risk_score,
            )

            risk_level = "low" if risk_score < 0.3 else "medium" if risk_score < 0.7 else "high"

            return QualityPredictionResponse(
                success=True,
                prediction_id=prediction.id,
                predicted_quality=quality_level,
                quality_score=round(quality_score, 3),
                risk_score=round(risk_score, 3),
                confidence=round(confidence, 3),
                message=f"质量预测完成：{quality_level.value} (得分{quality_score:.1%})",
                risk_level=risk_level,
                recommendations=recommendations,
            )

        except Exception as e:
            logger.exception("Quality prediction failed: %s", e)
            return QualityPredictionResponse(
                success=False,
                message=f"质量预测失败：{str(e)}",
                quality_score=0.5,
                risk_score=0.5,
                confidence=0.0,
            )

    def _extract_features(self, request: QualityPredictionRequest) -> List[QualityFeature]:
        """提取质量预测特征。"""
        features = []

        # 1. 工人历史质量特征
        worker_quality = self._get_worker_history_quality(request.worker_id)
        features.append(QualityFeature(
            name="worker_history_quality",
            value=worker_quality,
            weight=self.config.worker_history_weight,
            description="工人历史平均质量得分",
            risk_contribution=1.0 - worker_quality,
        ))

        # 2. 任务复杂度特征
        complexity_scores = {"low": 0.8, "medium": 0.5, "high": 0.3}
        complexity_score = complexity_scores.get(request.task_complexity, 0.5)
        features.append(QualityFeature(
            name="task_complexity",
            value=complexity_score,
            weight=self.config.task_complexity_weight,
            description=f"任务复杂度：{request.task_complexity}",
            risk_contribution=1.0 - complexity_score,
        ))

        # 3. 报酬合理性特征
        reward_score = self._calculate_reward_adequacy(request)
        features.append(QualityFeature(
            name="reward_adequacy",
            value=reward_score,
            weight=self.config.reward_adequacy_weight,
            description="报酬合理性评估",
            risk_contribution=1.0 - reward_score,
        ))

        # 4. 期限压力特征
        deadline_score = self._calculate_deadline_pressure(request)
        features.append(QualityFeature(
            name="deadline_pressure",
            value=deadline_score,
            weight=self.config.deadline_pressure_weight,
            description="期限压力评估",
            risk_contribution=1.0 - deadline_score,
        ))

        # 5. 描述质量特征
        description_score = self._calculate_description_quality(request.task_description)
        features.append(QualityFeature(
            name="description_quality",
            value=description_score,
            weight=self.config.description_quality_weight,
            description="任务描述质量",
            risk_contribution=1.0 - description_score,
        ))

        return features

    def _get_worker_history_quality(self, worker_id: str) -> float:
        """获取工人历史质量得分。"""
        # 模拟数据：实际应从数据库获取
        if worker_id in self._worker_quality_history:
            history = self._worker_quality_history[worker_id]
            return sum(history) / len(history) if history else 0.5

        # 新工人默认质量得分
        return 0.5

    def _calculate_reward_adequacy(self, request: QualityPredictionRequest) -> float:
        """计算报酬合理性。"""
        if request.reward_amount <= 0:
            return 0.3

        # 基于任务复杂度和市场均价评估报酬合理性
        base_reward = {"low": 10, "medium": 30, "high": 100}
        expected_reward = base_reward.get(request.task_complexity, 30)

        ratio = request.reward_amount / expected_reward
        # 报酬在期望值 80%-150% 之间为合理
        if 0.8 <= ratio <= 1.5:
            return min(1.0, ratio * 0.7)
        elif ratio < 0.8:
            return ratio * 0.5
        else:
            return 0.85

    def _calculate_deadline_pressure(self, request: QualityPredictionRequest) -> float:
        """计算期限压力。"""
        if not request.deadline_hours or request.deadline_hours <= 0:
            return 0.5

        # 基于任务复杂度和期限评估压力
        min_hours = {"low": 2, "medium": 8, "high": 24}
        expected_hours = min_hours.get(request.task_complexity, 8)

        ratio = request.deadline_hours / expected_hours
        if ratio >= 2:
            return 0.9  # 时间充裕
        elif ratio >= 1:
            return 0.7
        elif ratio >= 0.5:
            return 0.5
        else:
            return 0.3  # 时间紧张

    def _calculate_description_quality(self, description: str) -> float:
        """计算任务描述质量。"""
        if not description:
            return 0.2

        score = 0.5

        # 长度评分
        if len(description) >= 100:
            score += 0.2
        elif len(description) >= 50:
            score += 0.1

        # 结构评分（有分段、列表等）
        if "\n" in description:
            score += 0.1
        if any(kw in description for kw in ["要求", "需要", "必须", "should", "must", "need"]):
            score += 0.1
        if any(kw in description for kw in ["步骤", "流程", "step", "process"]):
            score += 0.1

        return min(1.0, score)

    def _calculate_quality_score(self, features: List[QualityFeature]) -> float:
        """计算加权质量得分。"""
        if not features:
            return 0.5

        weighted_sum = sum(f.value * f.weight for f in features)
        total_weight = sum(f.weight for f in features)

        return weighted_sum / total_weight if total_weight > 0 else 0.5

    def _calculate_risk_score(self, features: List[QualityFeature], quality_score: float) -> float:
        """计算风险得分。"""
        # 基础风险 = 1 - 质量得分
        base_risk = 1.0 - quality_score

        # 特征风险贡献
        feature_risk = sum(f.risk_contribution * f.weight for f in features)
        total_weight = sum(f.weight for f in features)

        if total_weight > 0:
            feature_risk /= total_weight
        else:
            feature_risk = 0.5

        # 综合风险（基础风险占 60%，特征风险占 40%）
        risk_score = 0.6 * base_risk + 0.4 * feature_risk

        # 应用非线性调整（高风险情况下更加保守）
        if risk_score > 0.7:
            risk_score = min(1.0, risk_score * 1.1)
        elif risk_score < 0.3:
            risk_score = max(0.0, risk_score * 0.9)

        return min(1.0, max(0.0, risk_score))

    def _determine_quality_level(self, quality_score: float, risk_score: float) -> QualityLevel:
        """确定质量等级。"""
        # 高风险优先
        if risk_score >= self.config.high_risk_threshold:
            return QualityLevel.HIGH_RISK

        if quality_score >= self.config.high_quality_threshold:
            return QualityLevel.EXCELLENT
        elif quality_score >= self.config.acceptable_quality_threshold:
            return QualityLevel.GOOD
        elif quality_score >= 0.4:
            return QualityLevel.AVERAGE
        else:
            return QualityLevel.POOR

    def _generate_prediction_reason(
        self,
        features: List[QualityFeature],
        quality_score: float,
        risk_score: float,
    ) -> str:
        """生成预测依据说明。"""
        reasons = []

        # 找到影响最大的特征
        sorted_features = sorted(features, key=lambda f: f.weight * abs(f.value - 0.5), reverse=True)

        for feature in sorted_features[:3]:
            if feature.value >= 0.7:
                reasons.append(f"{feature.description}较好 ({feature.value:.1%})")
            elif feature.value <= 0.3:
                reasons.append(f"{feature.description}较差 ({feature.value:.1%})")
            else:
                reasons.append(f"{feature.description}一般 ({feature.value:.1%})")

        base_reason = f"质量得分{quality_score:.1%}，风险得分{risk_score:.1%}。"
        return base_reason + "主要依据：" + "；".join(reasons)

    def _analyze_factors(
        self, features: List[QualityFeature]
    ) -> Tuple[List[str], List[str]]:
        """识别积极因素和风险因素。"""
        positive_factors = []
        risk_factors = []

        for feature in features:
            if feature.value >= 0.7:
                positive_factors.append(f"{feature.name}: {feature.description}较好")
            elif feature.value <= 0.4:
                risk_factors.append(f"{feature.name}: {feature.description}较差")

        return positive_factors, risk_factors

    def _generate_recommendations(
        self,
        quality_level: QualityLevel,
        risk_score: float,
        risk_factors: List[str],
        features: List[QualityFeature],
    ) -> List[str]:
        """生成改进建议。"""
        recommendations = []

        # 基于质量等级的通用建议
        if quality_level == QualityLevel.HIGH_RISK:
            recommendations.append("建议增加质量检查点或人工复核")
            recommendations.append("考虑分配给更有经验的工人")
        elif quality_level == QualityLevel.POOR:
            recommendations.append("建议细化任务要求和验收标准")
            recommendations.append("考虑增加中期检查节点")
        elif quality_level == QualityLevel.AVERAGE:
            recommendations.append("建议保持沟通，及时解答工人问题")

        # 基于具体风险因素的建议
        for factor in risk_factors:
            if "worker_history" in factor:
                recommendations.append("该工人历史表现一般，建议加强验收")
            elif "reward" in factor:
                recommendations.append("报酬可能偏低，考虑适当提高以吸引优质工人")
            elif "deadline" in factor:
                recommendations.append("期限较紧张，建议延长或分期交付")
            elif "description" in factor:
                recommendations.append("任务描述不够清晰，建议补充详细说明")
            elif "complexity" in factor:
                recommendations.append("任务复杂度较高，建议分解为多个子任务")

        # 去重
        return list(dict.fromkeys(recommendations))

    def _calculate_confidence(self, features: List[QualityFeature], quality_score: float) -> float:
        """计算预测置信度。"""
        # 基础置信度
        base_confidence = 0.6

        # 特征数量奖励
        quantity_bonus = min(0.1, len(features) * 0.02)

        # 特征一致性奖励
        values = [f.value for f in features]
        if values:
            variance = sum((v - sum(values) / len(values)) ** 2 for v in values) / len(values)
            consistency_bonus = max(0, 0.2 - variance * 0.5)
        else:
            consistency_bonus = 0

        # 极端值惩罚（得分太极端时降低置信度）
        if quality_score > 0.9 or quality_score < 0.1:
            extreme_penalty = 0.1
        else:
            extreme_penalty = 0

        confidence = base_confidence + quantity_bonus + consistency_bonus - extreme_penalty
        return min(1.0, max(0.0, confidence))

    def get_prediction(self, prediction_id: str) -> Optional[QualityPrediction]:
        """获取预测记录。"""
        return self._predictions.get(prediction_id)

    def get_prediction_by_task(self, task_id: str) -> Optional[QualityPrediction]:
        """通过任务 ID 获取预测记录。"""
        prediction_id = self._task_predictions.get(task_id)
        if prediction_id:
            return self._predictions.get(prediction_id)
        return None

    def record_actual_quality(
        self,
        prediction_id: str,
        actual_quality_level: QualityLevel,
        actual_quality_score: float,
    ) -> bool:
        """记录实际质量结果，用于模型验证和学习。"""
        prediction = self._predictions.get(prediction_id)
        if not prediction:
            return False

        prediction.actual_quality_level = actual_quality_level
        prediction.actual_quality_score = actual_quality_score

        # 验证预测准确性
        if abs(prediction.quality_score - actual_quality_score) < 0.2:
            prediction.status = "verified"
        else:
            prediction.status = "incorrect"

        prediction.verified_at = datetime.now()

        # 更新工人历史质量缓存
        worker_id = prediction.worker_id
        if worker_id not in self._worker_quality_history:
            self._worker_quality_history[worker_id] = []
        self._worker_quality_history[worker_id].append(actual_quality_score)

        logger.info(
            "Actual quality recorded: prediction_id=%s, actual_score=%.3f, predicted=%.3f, accuracy=%s",
            prediction_id,
            actual_quality_score,
            prediction.quality_score,
            prediction.status,
        )

        return True

    def get_worker_quality_stats(self, worker_id: str) -> Dict[str, Any]:
        """获取工人质量统计。"""
        history = self._worker_quality_history.get(worker_id, [])
        if not history:
            return {
                "worker_id": worker_id,
                "total_tasks": 0,
                "avg_quality": 0.5,
                "quality_trend": "unknown",
            }

        avg_quality = sum(history) / len(history)
        recent_avg = sum(history[-5:]) / min(5, len(history)) if len(history) >= 5 else avg_quality

        # 计算趋势
        if len(history) >= 5:
            older_avg = sum(history[:5]) / 5
            if recent_avg > older_avg * 1.1:
                trend = "improving"
            elif recent_avg < older_avg * 0.9:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "unknown"

        return {
            "worker_id": worker_id,
            "total_tasks": len(history),
            "avg_quality": round(avg_quality, 3),
            "recent_quality": round(recent_avg, 3),
            "quality_trend": trend,
        }


# 全局单例
quality_prediction_service = QualityPredictionService()