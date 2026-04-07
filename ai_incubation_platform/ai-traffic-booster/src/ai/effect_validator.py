"""
AI 效果验证服务

功能:
- 追踪建议执行状态
- 验证优化效果
- 计算 ROI
- 形成反馈闭环
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, date, timedelta
from enum import Enum
import logging
import uuid

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """执行状态"""
    PENDING = "pending"      # 待执行
    IN_PROGRESS = "in_progress"  # 执行中
    COMPLETED = "completed"  # 已完成
    REJECTED = "rejected"    # 已拒绝
    FAILED = "failed"        # 执行失败


class EffectSignificance(str, Enum):
    """效果显著性"""
    SIGNIFICANT_POSITIVE = "significant_positive"  # 显著正向
    MODERATE_POSITIVE = "moderate_positive"        # 中等正向
    SLIGHT_POSITIVE = "slight_positive"            # 轻微正向
    NO_EFFECT = "no_effect"                        # 无明显效果
    SLIGHT_NEGATIVE = "slight_negative"            # 轻微负向
    MODERATE_NEGATIVE = "moderate_negative"        # 中等负向
    SIGNIFICANT_NEGATIVE = "significant_negative"  # 显著负向


class SuggestionExecution:
    """建议执行记录"""
    def __init__(
        self,
        suggestion_id: str,
        user_id: Optional[str] = None,
        status: ExecutionStatus = ExecutionStatus.PENDING,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        execution_notes: Optional[str] = None,
        execution_code: Optional[str] = None  # 执行的代码/配置改动
    ):
        self.execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        self.suggestion_id = suggestion_id
        self.user_id = user_id
        self.status = status
        self.started_at = started_at
        self.completed_at = completed_at
        self.execution_notes = execution_notes
        self.execution_code = execution_code
        self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "suggestion_id": self.suggestion_id,
            "user_id": self.user_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_notes": self.execution_notes,
            "execution_code": self.execution_code,
            "created_at": self.created_at.isoformat()
        }


class EffectValidation:
    """效果验证结果"""
    def __init__(
        self,
        execution_id: str,
        metric_name: str,
        baseline_value: float,
        current_value: float,
        change_percentage: float,
        statistical_significance: float,  # p-value
        is_significant: bool,
        confidence_interval: tuple,
        validation_period_days: int,
        conclusion: str,
        validated_at: datetime = None
    ):
        self.validation_id = f"valid_{uuid.uuid4().hex[:12]}"
        self.execution_id = execution_id
        self.metric_name = metric_name
        self.baseline_value = baseline_value
        self.current_value = current_value
        self.change_percentage = change_percentage
        self.statistical_significance = statistical_significance
        self.is_significant = is_significant
        self.confidence_interval = confidence_interval
        self.validation_period_days = validation_period_days
        self.conclusion = conclusion
        self.validated_at = validated_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validation_id": self.validation_id,
            "execution_id": self.execution_id,
            "metric_name": self.metric_name,
            "baseline_value": self.baseline_value,
            "current_value": self.current_value,
            "change_percentage": round(self.change_percentage, 4),
            "statistical_significance": round(self.statistical_significance, 4),
            "is_significant": self.is_significant,
            "confidence_interval": [round(x, 2) for x in self.confidence_interval],
            "validation_period_days": self.validation_period_days,
            "conclusion": self.conclusion,
            "validated_at": self.validated_at.isoformat()
        }


class EffectValidator:
    """
    效果验证服务

    负责:
    - 追踪建议执行状态
    - 验证优化效果
    - 计算统计显著性
    - 形成学习反馈
    """

    def __init__(self):
        # 内存存储（生产环境应使用数据库）
        self._executions: Dict[str, SuggestionExecution] = {}
        self._validations: Dict[str, EffectValidation] = {}
        self._suggestion_history: Dict[str, List[EffectValidation]] = {}

        # 验证配置
        self.significance_level = 0.05  # 显著性水平α
        self.min_validation_days = 7    # 最小验证天数
        self.min_sample_size = 30       # 最小样本量

    def track_execution(
        self,
        suggestion_id: str,
        user_id: Optional[str] = None
    ) -> SuggestionExecution:
        """
        追踪建议执行

        Args:
            suggestion_id: 建议 ID
            user_id: 用户 ID

        Returns:
            执行记录
        """
        execution = SuggestionExecution(
            suggestion_id=suggestion_id,
            user_id=user_id,
            status=ExecutionStatus.IN_PROGRESS,
            started_at=datetime.now()
        )
        self._executions[execution.execution_id] = execution
        logger.info(f"开始追踪建议执行：{execution.execution_id}, suggestion={suggestion_id}")
        return execution

    def complete_execution(
        self,
        execution_id: str,
        notes: Optional[str] = None,
        code_changes: Optional[str] = None
    ) -> Optional[SuggestionExecution]:
        """
        标记执行为完成

        Args:
            execution_id: 执行 ID
            notes: 执行备注
            code_changes: 代码改动

        Returns:
            更新后的执行记录
        """
        if execution_id not in self._executions:
            logger.error(f"执行记录不存在：{execution_id}")
            return None

        execution = self._executions[execution_id]
        execution.status = ExecutionStatus.COMPLETED
        execution.completed_at = datetime.now()
        execution.execution_notes = notes
        execution.execution_code = code_changes

        logger.info(f"执行完成：{execution_id}")
        return execution

    def validate_effect(
        self,
        execution_id: str,
        metric_name: str,
        baseline_data: List[float],
        current_data: List[float],
        validation_days: Optional[int] = None
    ) -> Optional[EffectValidation]:
        """
        验证优化效果

        Args:
            execution_id: 执行 ID
            metric_name: 验证指标
            baseline_data: 基线数据（优化前）
            current_data: 当前数据（优化后）
            validation_days: 验证天数

        Returns:
            效果验证结果
        """
        if execution_id not in self._executions:
            logger.error(f"执行记录不存在：{execution_id}")
            return None

        if len(baseline_data) < self.min_sample_size or len(current_data) < self.min_sample_size:
            logger.warning(f"样本量不足，无法进行可靠的统计验证")
            return self._create_invalid_validation(
                execution_id, metric_name,
                "样本量不足，需要更多数据"
            )

        # 计算统计量
        baseline_mean = sum(baseline_data) / len(baseline_data)
        current_mean = sum(current_data) / len(current_data)

        if baseline_mean == 0:
            change_pct = 0
        else:
            change_pct = (current_mean - baseline_mean) / baseline_mean

        # 计算统计显著性 (t 检验简化版)
        t_stat, p_value = self._two_sample_t_test(baseline_data, current_data)
        is_significant = p_value < self.significance_level

        # 计算置信区间
        ci = self._calculate_confidence_interval(current_data)

        # 确定效果显著性级别
        significance = self._determine_significance(change_pct, is_significant)

        # 生成结论
        conclusion = self._generate_conclusion(
            metric_name, change_pct, is_significant, significance
        )

        validation = EffectValidation(
            execution_id=execution_id,
            metric_name=metric_name,
            baseline_value=baseline_mean,
            current_value=current_mean,
            change_percentage=change_pct,
            statistical_significance=p_value,
            is_significant=is_significant,
            confidence_interval=ci,
            validation_period_days=validation_days or len(current_data),
            conclusion=conclusion
        )

        self._validations[validation.validation_id] = validation

        # 记录到建议历史
        suggestion_id = self._executions[execution_id].suggestion_id
        if suggestion_id not in self._suggestion_history:
            self._suggestion_history[suggestion_id] = []
        self._suggestion_history[suggestion_id].append(validation)

        logger.info(
            f"效果验证完成：{validation.validation_id}, "
            f"metric={metric_name}, change={change_pct:.2%}, "
            f"significant={is_significant}"
        )

        return validation

    def get_suggestion_effectiveness(
        self,
        suggestion_id: str
    ) -> Dict[str, Any]:
        """
        获取建议的整体有效性

        Args:
            suggestion_id: 建议 ID

        Returns:
            有效性统计
        """
        validations = self._suggestion_history.get(suggestion_id, [])

        if not validations:
            return {
                "suggestion_id": suggestion_id,
                "total_validations": 0,
                "success_rate": 0,
                "avg_impact": 0,
                "confidence": 0
            }

        positive_count = sum(
            1 for v in validations
            if v.change_percentage > 0 and v.is_significant
        )
        avg_impact = sum(v.change_percentage for v in validations) / len(validations)

        return {
            "suggestion_id": suggestion_id,
            "total_validations": len(validations),
            "success_rate": positive_count / len(validations),
            "avg_impact": avg_impact,
            "confidence": self._calculate_suggestion_confidence(validations)
        }

    def get_learning_insights(self) -> List[Dict[str, Any]]:
        """
        获取学习洞察（哪些类型的建议最有效）

        Returns:
            学习洞察列表
        """
        insights = []

        # 按建议类型聚合效果
        type_performance: Dict[str, List[float]] = {}

        for suggestion_id, validations in self._suggestion_history.items():
            # 从 execution 反查 suggestion_type（简化处理）
            for validation in validations:
                # 这里可以根据 suggestion_id 提取类型信息
                # 简化处理：直接使用 metric_name 作为分类
                metric_type = validation.metric_name.split("_")[0]
                if metric_type not in type_performance:
                    type_performance[metric_type] = []
                type_performance[metric_type].append(validation.change_percentage)

        # 生成洞察
        for metric_type, impacts in type_performance.items():
            if len(impacts) >= 3:  # 至少 3 次验证
                avg_impact = sum(impacts) / len(impacts)
                success_rate = sum(1 for i in impacts if i > 0) / len(impacts)

                insights.append({
                    "type": metric_type,
                    "avg_impact": avg_impact,
                    "success_rate": success_rate,
                    "sample_size": len(impacts),
                    "recommendation": "推荐" if success_rate > 0.7 else "谨慎使用"
                })

        insights.sort(key=lambda x: x["success_rate"], reverse=True)
        return insights

    def _two_sample_t_test(
        self,
        sample1: List[float],
        sample2: List[float]
    ) -> tuple:
        """
        双样本 t 检验（简化实现）

        Returns:
            (t_statistic, p_value)
        """
        n1, n2 = len(sample1), len(sample2)
        mean1 = sum(sample1) / n1
        mean2 = sum(sample2) / n2

        var1 = sum((x - mean1) ** 2 for x in sample1) / (n1 - 1)
        var2 = sum((x - mean2) ** 2 for x in sample2) / (n2 - 1)

        # 合并标准误
        se = ((var1 / n1) + (var2 / n2)) ** 0.5

        if se == 0:
            return 0, 1.0

        t_stat = (mean1 - mean2) / se
        df = n1 + n2 - 2

        # 简化 p 值计算（使用近似）
        # 实际应使用 t 分布表
        abs_t = abs(t_stat)
        if abs_t > 3:
            p_value = 0.001
        elif abs_t > 2.5:
            p_value = 0.01
        elif abs_t > 2:
            p_value = 0.05
        elif abs_t > 1.5:
            p_value = 0.1
        else:
            p_value = 0.2

        return t_stat, p_value

    def _calculate_confidence_interval(
        self,
        data: List[float],
        confidence: float = 0.95
    ) -> tuple:
        """计算置信区间"""
        n = len(data)
        mean = sum(data) / n
        std = (sum((x - mean) ** 2 for x in data) / (n - 1)) ** 0.5
        se = std / (n ** 0.5)

        # z 值（95% 置信度）
        z = 1.96

        margin = z * se
        return (mean - margin, mean + margin)

    def _determine_significance(
        self,
        change_pct: float,
        is_stat_significant: bool
    ) -> EffectSignificance:
        """确定效果显著性级别"""
        if not is_stat_significant:
            if abs(change_pct) < 0.05:
                return EffectSignificance.NO_EFFECT
            elif change_pct > 0:
                return EffectSignificance.SLIGHT_POSITIVE
            else:
                return EffectSignificance.SLIGHT_NEGATIVE

        abs_change = abs(change_pct)
        if change_pct > 0:
            if abs_change > 0.3:
                return EffectSignificance.SIGNIFICANT_POSITIVE
            elif abs_change > 0.1:
                return EffectSignificance.MODERATE_POSITIVE
            else:
                return EffectSignificance.SLIGHT_POSITIVE
        else:
            if abs_change > 0.3:
                return EffectSignificance.SIGNIFICANT_NEGATIVE
            elif abs_change > 0.1:
                return EffectSignificance.MODERATE_NEGATIVE
            else:
                return EffectSignificance.SLIGHT_NEGATIVE

    def _generate_conclusion(
        self,
        metric_name: str,
        change_pct: float,
        is_significant: bool,
        significance: EffectSignificance
    ) -> str:
        """生成验证结论"""
        direction = "提升" if change_pct > 0 else "下降"
        pct = abs(change_pct) * 100

        if significance == EffectSignificance.SIGNIFICANT_POSITIVE:
            return f"{metric_name}显著{direction}{pct:.1f}%，效果非常明显，建议推广"
        elif significance == EffectSignificance.MODERATE_POSITIVE:
            return f"{metric_name}{direction}{pct:.1f}%，效果良好，建议继续优化"
        elif significance == EffectSignificance.SLIGHT_POSITIVE:
            return f"{metric_name}轻微{direction}{pct:.1f}%，效果有限，可考虑其他方案"
        elif significance == EffectSignificance.NO_EFFECT:
            return f"{metric_name}无明显变化，建议重新评估方案"
        elif significance == EffectSignificance.SLIGHT_NEGATIVE:
            return f"{metric_name}轻微{direction}{pct:.1f}%，建议调整方案"
        elif significance == EffectSignificance.MODERATE_NEGATIVE:
            return f"{metric_name}明显{direction}{pct:.1f}%，建议停止此方案"
        else:
            return f"{metric_name}显著{direction}{pct:.1f}%，建议立即停止并回滚"

    def _calculate_suggestion_confidence(
        self,
        validations: List[EffectValidation]
    ) -> float:
        """计算建议的整体置信度"""
        if not validations:
            return 0

        # 基于成功率和样本量计算
        positive_count = sum(1 for v in validations if v.change_percentage > 0)
        success_rate = positive_count / len(validations)

        # 样本量修正
        sample_factor = min(1.0, len(validations) / 10.0)

        return success_rate * (0.5 + 0.5 * sample_factor)

    def _create_invalid_validation(
        self,
        execution_id: str,
        metric_name: str,
        reason: str
    ) -> EffectValidation:
        """创建无效验证结果"""
        return EffectValidation(
            execution_id=execution_id,
            metric_name=metric_name,
            baseline_value=0,
            current_value=0,
            change_percentage=0,
            statistical_significance=1.0,
            is_significant=False,
            confidence_interval=(0, 0),
            validation_period_days=0,
            conclusion=reason
        )


# 全局服务实例
effect_validator = EffectValidator()
