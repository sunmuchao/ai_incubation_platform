"""
置信度评估系统 - 服务包

包含：
- 扩展验证规则
- 动态权重系统
- LLM 深度分析
- 实时更新机制
- 反馈闭环系统
"""

from typing import Dict, Any
from sqlalchemy.orm import Session
from models.user import User as UserDB

from services.confidence.extended_validation_rules import (
    validate_interest_browse_consistency,
    validate_age_self_declared_consistency,
    validate_photo_personality_consistency,
    validate_location_trajectory_consistency,
    run_all_extended_validations,
)

from services.confidence.dynamic_weights import (
    user_group_classifier,
    weight_optimizer,
    feedback_collector,
    ab_testing,
    USER_GROUP_WEIGHTS,
    DEFAULT_WEIGHTS,
)

from services.confidence.llm_confidence_analyzer import (
    text_analyzer,
    age_inferrer,
    value_inferrer,
    llm_confidence_analyzer,
    LLMConfidenceAnalyzer,
)

from services.confidence.realtime_update import (
    confidence_trigger,
    behavior_detector,
    confidence_scheduler,
    UPDATE_TRIGGERS,
)

from services.confidence.feedback_loop import (
    confidence_feedback_service,
    rule_optimizer,
    false_positive_compensator,
    FEEDBACK_TYPES,
)


# ============================================
# 综合评估服务
# ============================================

class IntegratedConfidenceEvaluator:
    """综合置信度评估器 - 整合所有服务"""

    async def evaluate_comprehensive(
        self,
        user_id: str,
        db: Session,
        trigger_source: str = "comprehensive"
    ) -> Dict[str, Any]:
        """
        执行综合置信度评估

        整合：
        - 基础验证规则
        - 扩展验证规则
        - LLM 深度分析
        - 动态权重计算
        """
        from services.profile_confidence_service import profile_confidence_service

        # 1. 基础置信度评估
        base_result = profile_confidence_service.evaluate_user_confidence(
            user_id=user_id,
            trigger_source=trigger_source
        )

        if not base_result.get("success"):
            return base_result

        # 2. 执行扩展验证规则
        user = db.query(UserDB).filter(UserDB.id == user_id).first()
        extended_score, extended_flags = run_all_extended_validations(user, db)

        # 3. 执行 LLM 深度分析
        llm_result = await llm_confidence_analyzer.analyze_user_confidence_deep(user, db)

        # 4. 应用动态权重
        user_group = user_group_classifier.classify_user(user, db)
        group_weights = user_group_classifier.get_weights_for_group(user_group)

        # 5. 综合计算
        dimensions = base_result.get("dimensions", {})

        overall_confidence = group_weights["base_score"]
        overall_confidence += dimensions.get("identity", 0) * group_weights["identity"]
        overall_confidence += dimensions.get("cross_validation", 0) * group_weights["cross_validation"]
        overall_confidence += dimensions.get("behavior", 0) * group_weights["behavior"]
        overall_confidence += dimensions.get("social", 0) * group_weights["social"]
        overall_confidence += dimensions.get("time", 0) * group_weights["time"]

        # 应用扩展验证结果
        overall_confidence *= extended_score

        # 应用 LLM 分析结果
        llm_confidence = llm_result.get("overall_llm_confidence", 0.6)
        overall_confidence = overall_confidence * 0.7 + llm_confidence * 0.3

        # 确保范围
        overall_confidence = max(0.05, min(1.0, overall_confidence))

        # 6. 确定等级
        level = self._get_level(overall_confidence)

        # 7. 合并所有异常标记
        all_flags = {}
        all_flags.update(base_result.get("cross_validation_flags", {}))
        all_flags.update(extended_flags)
        if llm_result.get("red_flags"):
            all_flags["llm_detected"] = llm_result["red_flags"]

        return {
            "success": True,
            "user_id": user_id,
            "overall_confidence": overall_confidence,
            "confidence_level": level,
            "dimensions": dimensions,
            "extended_validation_score": extended_score,
            "llm_confidence": llm_confidence,
            "all_flags": all_flags,
            "user_group": user_group,
            "group_weights": group_weights,
            "llm_details": llm_result,
        }

    def _get_level(self, confidence: float) -> str:
        """获取置信度等级"""
        if confidence >= 0.8:
            return "very_high"
        elif confidence >= 0.6:
            return "high"
        elif confidence >= 0.4:
            return "medium"
        else:
            return "low"


# 全局综合评估器
integrated_evaluator = IntegratedConfidenceEvaluator()


__all__ = [
    # 扩展验证
    "validate_interest_browse_consistency",
    "validate_age_self_declared_consistency",
    "validate_photo_personality_consistency",
    "validate_location_trajectory_consistency",
    "run_all_extended_validations",

    # 动态权重
    "user_group_classifier",
    "weight_optimizer",
    "feedback_collector",
    "ab_testing",
    "USER_GROUP_WEIGHTS",
    "DEFAULT_WEIGHTS",

    # LLM 分析
    "text_analyzer",
    "age_inferrer",
    "value_inferrer",
    "llm_confidence_analyzer",
    "LLMConfidenceAnalyzer",

    # 实时更新
    "confidence_trigger",
    "behavior_detector",
    "confidence_scheduler",
    "UPDATE_TRIGGERS",

    # 反馈闭环
    "confidence_feedback_service",
    "rule_optimizer",
    "false_positive_compensator",
    "FEEDBACK_TYPES",

    # 综合评估
    "integrated_evaluator",
    "IntegratedConfidenceEvaluator",
]