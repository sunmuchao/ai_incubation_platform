"""
AI 优化闭环学习服务

功能:
- 建立优化历史知识库
- 基于历史效果优化建议排序
- 计算建议类型的有效性评分
- 持续改进推荐算法
- 形成"建议→执行→验证→学习→优化"的闭环
"""
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from enum import Enum
import logging
import uuid
import json
from collections import defaultdict

from ai.anomaly_detection import AnomalyDetectionResult
from ai.root_cause_analysis import RootCauseAnalysisResult, RootCauseCategory
from ai.recommendation_engine import OptimizationSuggestion, SuggestionType, SuggestionPriority
from ai.effect_validator import EffectValidation, EffectSignificance, ExecutionStatus

logger = logging.getLogger(__name__)


class SuggestionOutcome(str, Enum):
    """建议结果类型"""
    SIGNIFICANT_POSITIVE = "significant_positive"  # 显著正向效果
    MODERATE_POSITIVE = "moderate_positive"        # 中等正向效果
    SLIGHT_POSITIVE = "slight_positive"            # 轻微正向效果
    NO_EFFECT = "no_effect"                        # 无明显效果
    SLIGHT_NEGATIVE = "slight_negative"            # 轻微负向效果
    MODERATE_NEGATIVE = "moderate_negative"        # 中等负向效果
    SIGNIFICANT_NEGATIVE = "significant_negative"  # 显著负向效果


class OptimizationLearning:
    """优化学习记录"""
    def __init__(
        self,
        learning_id: str,
        suggestion_id: str,
        suggestion_type: str,
        root_cause_category: str,
        anomaly_type: str,
        outcome: SuggestionOutcome,
        actual_impact: float,
        predicted_impact: float,
        prediction_accuracy: float,
        confidence: float,
        execution_context: Dict[str, Any],
        lessons_learned: List[str],
        recommendation: str,
        learned_at: datetime = None
    ):
        self.learning_id = learning_id
        self.suggestion_id = suggestion_id
        self.suggestion_type = suggestion_type
        self.root_cause_category = root_cause_category
        self.anomaly_type = anomaly_type
        self.outcome = outcome
        self.actual_impact = actual_impact
        self.predicted_impact = predicted_impact
        self.prediction_accuracy = prediction_accuracy
        self.confidence = confidence
        self.execution_context = execution_context
        self.lessons_learned = lessons_learned
        self.recommendation = recommendation
        self.learned_at = learned_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "learning_id": self.learning_id,
            "suggestion_id": self.suggestion_id,
            "suggestion_type": self.suggestion_type,
            "root_cause_category": self.root_cause_category,
            "anomaly_type": self.anomaly_type,
            "outcome": self.outcome.value,
            "actual_impact": round(self.actual_impact, 4),
            "predicted_impact": round(self.predicted_impact, 4),
            "prediction_accuracy": round(self.prediction_accuracy, 4),
            "confidence": round(self.confidence, 2),
            "execution_context": self.execution_context,
            "lessons_learned": self.lessons_learned,
            "recommendation": self.recommendation,
            "learned_at": self.learned_at.isoformat()
        }


class SuggestionTypePerformance:
    """建议类型性能统计"""
    def __init__(self, suggestion_type: str):
        self.suggestion_type = suggestion_type
        self.total_attempts = 0
        self.positive_count = 0
        self.negative_count = 0
        self.no_effect_count = 0
        self.total_impact = 0.0
        self.avg_impact = 0.0
        self.success_rate = 0.0
        self.avg_prediction_accuracy = 0.0
        self.confidence_score = 0.0

    def update(self, learning: OptimizationLearning):
        """用学习记录更新统计"""
        self.total_attempts += 1
        self.total_impact += learning.actual_impact

        if learning.outcome in [SuggestionOutcome.SIGNIFICANT_POSITIVE,
                                SuggestionOutcome.MODERATE_POSITIVE,
                                SuggestionOutcome.SLIGHT_POSITIVE]:
            self.positive_count += 1
        elif learning.outcome in [SuggestionOutcome.SIGNIFICANT_NEGATIVE,
                                  SuggestionOutcome.MODERATE_NEGATIVE,
                                  SuggestionOutcome.SLIGHT_NEGATIVE]:
            self.negative_count += 1
        else:
            self.no_effect_count += 1

        self.avg_impact = self.total_impact / self.total_attempts
        self.success_rate = self.positive_count / self.total_attempts

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggestion_type": self.suggestion_type,
            "total_attempts": self.total_attempts,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "no_effect_count": self.no_effect_count,
            "avg_impact": round(self.avg_impact, 4),
            "success_rate": round(self.success_rate, 4),
            "recommendation": self._get_recommendation()
        }

    def _get_recommendation(self) -> str:
        """获取推荐建议"""
        if self.success_rate >= 0.7 and self.avg_impact > 0.1:
            return "强烈推荐"
        elif self.success_rate >= 0.5 and self.avg_impact > 0.05:
            return "推荐"
        elif self.success_rate >= 0.3:
            return "谨慎使用"
        else:
            return "不推荐"


class RootCauseEffectiveness:
    """根因类别有效性统计"""
    def __init__(self, category: str):
        self.category = category
        self.total_attempts = 0
        self.successful_interventions = 0
        self.avg_impact = 0.0
        self.total_impact = 0.0
        self.best_performing_type = None
        self.category_performance: Dict[str, SuggestionTypePerformance] = {}

    def update(self, learning: OptimizationLearning):
        """用学习记录更新统计"""
        self.total_attempts += 1
        self.total_impact += learning.actual_impact

        if learning.actual_impact > 0.05:  # 5% 提升视为成功
            self.successful_interventions += 1

        self.avg_impact = self.total_impact / self.total_attempts

        # 更新该根因类别下各建议类型的性能
        sugg_type = learning.suggestion_type
        if sugg_type not in self.category_performance:
            self.category_performance[sugg_type] = SuggestionTypePerformance(sugg_type)
        self.category_performance[sugg_type].update(learning)

        # 找出最佳建议类型
        best_type = None
        best_impact = 0
        for type_name, perf in self.category_performance.items():
            if perf.avg_impact > best_impact:
                best_impact = perf.avg_impact
                best_type = type_name
        self.best_performing_type = best_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "total_attempts": self.total_attempts,
            "successful_interventions": self.successful_interventions,
            "success_rate": round(self.successful_interventions / max(self.total_attempts, 1), 4),
            "avg_impact": round(self.avg_impact, 4),
            "best_performing_type": self.best_performing_type,
            "type_performance": {k: v.to_dict() for k, v in self.category_performance.items()}
        }


class LearningFeedbackLoop:
    """
    AI 优化闭环学习服务

    负责:
    - 记录每次优化执行和验证结果
    - 分析建议类型的有效性
    - 计算预测准确度
    - 生成学习洞察
    - 优化后续建议排序
    """

    def __init__(self):
        # 学习记录存储
        self._learnings: Dict[str, OptimizationLearning] = {}
        self._suggestion_learnings: Dict[str, List[str]] = defaultdict(list)  # suggestion_id -> learning_ids

        # 聚合统计
        self._type_performance: Dict[str, SuggestionTypePerformance] = {}
        self._category_effectiveness: Dict[str, RootCauseEffectiveness] = {}

        # 上下文性能追踪
        self._context_performance: Dict[str, Dict[str, Any]] = {}

        # 配置
        self.min_learning_samples = 5  # 最小学习样本数
        self.prediction_accuracy_threshold = 0.7  # 预测准确度阈值

    def record_learning(
        self,
        suggestion: OptimizationSuggestion,
        validation: EffectValidation,
        root_cause_category: Optional[str] = None,
        anomaly_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> OptimizationLearning:
        """
        记录优化学习

        Args:
            suggestion: 原始优化建议
            validation: 效果验证结果
            root_cause_category: 根因类别
            anomaly_type: 异常类型
            context: 执行上下文

        Returns:
            学习记录
        """
        # 确定结果类型
        outcome = self._map_significance_to_outcome(validation)

        # 计算预测准确度
        prediction_accuracy = self._calculate_prediction_accuracy(
            suggestion.expected_impact,
            validation.change_percentage
        )

        # 生成经验教训
        lessons = self._generate_lessons_learned(
            suggestion, validation, outcome, prediction_accuracy
        )

        # 生成推荐
        recommendation = self._generate_recommendation(
            outcome, suggestion.suggestion_type, prediction_accuracy
        )

        learning = OptimizationLearning(
            learning_id=f"learn_{uuid.uuid4().hex[:12]}",
            suggestion_id=suggestion.suggestion_id,
            suggestion_type=suggestion.suggestion_type.value,
            root_cause_category=root_cause_category or "",
            anomaly_type=anomaly_type or "",
            outcome=outcome,
            actual_impact=validation.change_percentage,
            predicted_impact=suggestion.expected_impact,
            prediction_accuracy=prediction_accuracy,
            confidence=suggestion.confidence,
            execution_context=context or {},
            lessons_learned=lessons,
            recommendation=recommendation
        )

        # 存储学习记录
        self._learnings[learning.learning_id] = learning
        self._suggestion_learnings[suggestion.suggestion_id].append(learning.learning_id)

        # 更新聚合统计
        self._update_aggregates(learning)

        logger.info(f"记录优化学习：{learning.learning_id}, outcome={outcome.value}, impact={validation.change_percentage:.2%}")

        return learning

    def get_suggestion_effectiveness(
        self,
        suggestion_type: Optional[SuggestionType] = None,
        root_cause_category: Optional[RootCauseCategory] = None
    ) -> Dict[str, Any]:
        """
        获取建议有效性统计

        Args:
            suggestion_type: 建议类型（可选）
            root_cause_category: 根因类别（可选）

        Returns:
            有效性统计
        """
        if suggestion_type:
            type_name = suggestion_type.value
            if type_name in self._type_performance:
                return self._type_performance[type_name].to_dict()
            return {"suggestion_type": type_name, "total_attempts": 0}

        if root_cause_category:
            cat_name = root_cause_category.value
            if cat_name in self._category_effectiveness:
                return self._category_effectiveness[cat_name].to_dict()
            return {"category": cat_name, "total_attempts": 0}

        # 返回总体统计
        return self._get_overall_stats()

    def get_learning_insights(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取学习洞察

        Args:
            limit: 返回数量限制

        Returns:
            学习洞察列表，按价值排序
        """
        insights = []

        # 1. 最佳表现的建议类型
        best_types = sorted(
            self._type_performance.values(),
            key=lambda x: (x.success_rate, x.avg_impact),
            reverse=True
        )[:3]

        for perf in best_types:
            if perf.total_attempts >= self.min_learning_samples:
                insights.append({
                    "type": "best_performing_type",
                    "suggestion_type": perf.suggestion_type,
                    "success_rate": perf.success_rate,
                    "avg_impact": perf.avg_impact,
                    "recommendation": perf._get_recommendation(),
                    "confidence": "high" if perf.total_attempts >= 10 else "medium"
                })

        # 2. 最有效的根因干预
        best_categories = sorted(
            self._category_effectiveness.values(),
            key=lambda x: (x.avg_impact, x.successful_interventions / max(x.total_attempts, 1)),
            reverse=True
        )[:3]

        for cat in best_categories:
            if cat.total_attempts >= self.min_learning_samples:
                insights.append({
                    "type": "effective_intervention",
                    "root_cause_category": cat.category,
                    "avg_impact": cat.avg_impact,
                    "success_rate": cat.successful_interventions / max(cat.total_attempts, 1),
                    "best_performing_type": cat.best_performing_type,
                    "confidence": "high" if cat.total_attempts >= 10 else "medium"
                })

        # 3. 预测准确度分析
        if self._learnings:
            avg_accuracy = sum(l.prediction_accuracy for l in self._learnings.values()) / len(self._learnings)
            insights.append({
                "type": "prediction_accuracy",
                "average_accuracy": avg_accuracy,
                "reliability": "high" if avg_accuracy >= 0.7 else "medium" if avg_accuracy >= 0.5 else "low",
                "total_samples": len(self._learnings)
            })

        # 4. 高价值学习（显著效果）
        significant_learnings = [
            l for l in self._learnings.values()
            if abs(l.actual_impact) > 0.2  # 20% 以上效果
        ]
        for learning in significant_learnings[:limit]:
            insights.append({
                "type": "significant_outcome",
                "suggestion_id": learning.suggestion_id,
                "suggestion_type": learning.suggestion_type,
                "outcome": learning.outcome.value,
                "actual_impact": learning.actual_impact,
                "lessons": learning.lessons_learned
            })

        return insights[:limit]

    def adjust_suggestion_priority(
        self,
        suggestions: List[OptimizationSuggestion],
        context: Optional[Dict[str, Any]] = None
    ) -> List[OptimizationSuggestion]:
        """
        基于历史学习调整建议优先级

        Args:
            suggestions: 原始建议列表
            context: 上下文信息

        Returns:
            调整优先级后的建议列表
        """
        adjusted = []

        for suggestion in suggestions:
            # 获取该类型的历史性能
            type_perf = self._type_performance.get(suggestion.suggestion_type.value)

            if type_perf and type_perf.total_attempts >= self.min_learning_samples:
                # 根据历史成功率调整预期影响
                adjustment_factor = type_perf.success_rate * (1 + type_perf.avg_impact)

                # 更新建议的预期影响和置信度
                suggestion.expected_impact *= adjustment_factor
                suggestion.confidence = min(1.0, suggestion.confidence * type_perf.success_rate)

                logger.debug(f"调整建议{suggestion.suggestion_id}: impact={suggestion.expected_impact:.4f}, confidence={suggestion.confidence:.2f}")

            adjusted.append(suggestion)

        # 重新排序（使用优先级数值而不是枚举值的负数）
        priority_order = {
            SuggestionPriority.CRITICAL: 0,
            SuggestionPriority.HIGH: 1,
            SuggestionPriority.MEDIUM: 2,
            SuggestionPriority.LOW: 3
        }
        adjusted.sort(key=lambda x: (-x.expected_impact * x.confidence, priority_order.get(x.priority, 2)))

        return adjusted

    def get_recommendation_for_context(
        self,
        root_cause_category: str,
        anomaly_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        基于上下文中获取推荐方案

        Args:
            root_cause_category: 根因类别
            anomaly_type: 异常类型
            context: 上下文信息

        Returns:
            推荐方案
        """
        # 查找该根因类别下最有效的建议类型
        category = self._category_effectiveness.get(root_cause_category)

        if category and category.best_performing_type:
            best_type = category.best_performing_type
            type_perf = self._type_performance.get(best_type)

            return {
                "recommended_type": best_type,
                "expected_success_rate": type_perf.success_rate if type_perf else 0,
                "expected_impact": type_perf.avg_impact if type_perf else 0,
                "confidence": "high" if category.total_attempts >= 10 else "medium",
                "reasoning": f"基于{category.total_attempts}次{root_cause_category}类别的优化经验，{best_type}类型建议平均带来{type_perf.avg_impact*100:.1f}%的提升"
            }

        # 无历史数据时返回默认推荐
        return {
            "recommended_type": None,
            "expected_success_rate": 0,
            "expected_impact": 0,
            "confidence": "low",
            "reasoning": "暂无足够的历史数据，建议从基础优化开始尝试"
        }

    def export_learning_report(self) -> str:
        """
        导出学习报告

        Returns:
            JSON 格式的学习报告
        """
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_learnings": len(self._learnings),
            "overall_stats": self._get_overall_stats(),
            "type_performance": {k: v.to_dict() for k, v in self._type_performance.items()},
            "category_effectiveness": {k: v.to_dict() for k, v in self._category_effectiveness.items()},
            "top_insights": self.get_learning_insights(limit=5)
        }
        return json.dumps(report, indent=2, ensure_ascii=False)

    def _map_significance_to_outcome(
        self,
        validation: EffectValidation
    ) -> SuggestionOutcome:
        """将验证显著性映射到结果类型"""
        # 根据 change_percentage 和 is_significant 计算 EffectSignificance
        change_pct = validation.change_percentage
        is_significant = validation.is_significant

        if not is_significant:
            if abs(change_pct) < 0.05:
                return SuggestionOutcome.NO_EFFECT
            elif change_pct > 0:
                return SuggestionOutcome.SLIGHT_POSITIVE
            else:
                return SuggestionOutcome.SLIGHT_NEGATIVE

        # 显著的情况下，根据变化幅度判断级别
        abs_change = abs(change_pct)
        if change_pct > 0:
            if abs_change > 0.3:
                return SuggestionOutcome.SIGNIFICANT_POSITIVE
            elif abs_change > 0.1:
                return SuggestionOutcome.MODERATE_POSITIVE
            else:
                return SuggestionOutcome.SLIGHT_POSITIVE
        else:
            if abs_change > 0.3:
                return SuggestionOutcome.SIGNIFICANT_NEGATIVE
            elif abs_change > 0.1:
                return SuggestionOutcome.MODERATE_NEGATIVE
            else:
                return SuggestionOutcome.SLIGHT_NEGATIVE

    def _calculate_prediction_accuracy(
        self,
        predicted: float,
        actual: float
    ) -> float:
        """计算预测准确度"""
        if predicted == 0:
            return 0.5 if actual == 0 else 0.0

        # 计算相对误差
        relative_error = abs(actual - predicted) / max(abs(predicted), 0.01)

        # 转换为准确度分数（0-1）
        accuracy = max(0, 1 - relative_error)

        return accuracy

    def _generate_lessons_learned(
        self,
        suggestion: OptimizationSuggestion,
        validation: EffectValidation,
        outcome: SuggestionOutcome,
        prediction_accuracy: float
    ) -> List[str]:
        """生成经验教训"""
        lessons = []

        # 基于结果生成教训
        if outcome in [SuggestionOutcome.SIGNIFICANT_POSITIVE, SuggestionOutcome.MODERATE_POSITIVE]:
            lessons.append(f"成功验证了{suggestion.suggestion_type.value}类型建议的有效性")
            if validation.change_percentage > suggestion.expected_impact:
                lessons.append(f"实际效果 ({validation.change_percentage:.2%}) 超出预期 ({suggestion.expected_impact:.2%})")
            else:
                lessons.append(f"实际效果 ({validation.change_percentage:.2%}) 达到预期 ({suggestion.expected_impact:.2%})")
        elif outcome == SuggestionOutcome.NO_EFFECT:
            lessons.append("未观察到显著效果，建议重新评估方案")
            if prediction_accuracy < 0.5:
                lessons.append("预测模型需要校准")
        else:
            lessons.append(f"观察到负面效果 ({validation.change_percentage:.2%})，建议停止该方案")
            lessons.append("需要分析负面效果的原因")

        # 基于置信度生成教训
        if suggestion.confidence < 0.6:
            lessons.append("低置信度预测，需要更多数据验证")

        return lessons

    def _generate_recommendation(
        self,
        outcome: SuggestionOutcome,
        suggestion_type: str,
        prediction_accuracy: float
    ) -> str:
        """生成推荐"""
        if outcome in [SuggestionOutcome.SIGNIFICANT_POSITIVE, SuggestionOutcome.MODERATE_POSITIVE]:
            return f"推荐继续应用{suggestion_type}类型建议"
        elif outcome == SuggestionOutcome.NO_EFFECT:
            return "建议调整方案或尝试其他优化类型"
        else:
            return f"建议停止使用{suggestion_type}类型方案，考虑替代方案"

    def _update_aggregates(self, learning: OptimizationLearning):
        """更新聚合统计"""
        # 更新建议类型性能
        if learning.suggestion_type not in self._type_performance:
            self._type_performance[learning.suggestion_type] = SuggestionTypePerformance(learning.suggestion_type)
        self._type_performance[learning.suggestion_type].update(learning)

        # 更新根因类别有效性
        if learning.root_cause_category:
            if learning.root_cause_category not in self._category_effectiveness:
                self._category_effectiveness[learning.root_cause_category] = RootCauseEffectiveness(learning.root_cause_category)
            self._category_effectiveness[learning.root_cause_category].update(learning)

    def _get_overall_stats(self) -> Dict[str, Any]:
        """获取总体统计"""
        total = len(self._learnings)
        if total == 0:
            return {"total_learnings": 0, "avg_success_rate": 0, "avg_impact": 0}

        positive_count = sum(1 for l in self._learnings.values() if l.actual_impact > 0.05)
        avg_impact = sum(l.actual_impact for l in self._learnings.values()) / total
        avg_accuracy = sum(l.prediction_accuracy for l in self._learnings.values()) / total

        return {
            "total_learnings": total,
            "positive_count": positive_count,
            "negative_count": sum(1 for l in self._learnings.values() if l.actual_impact < -0.05),
            "no_effect_count": total - positive_count - sum(1 for l in self._learnings.values() if l.actual_impact < -0.05),
            "avg_success_rate": positive_count / total,
            "avg_impact": avg_impact,
            "avg_prediction_accuracy": avg_accuracy
        }


# 全局服务实例
learning_feedback_loop = LearningFeedbackLoop()
