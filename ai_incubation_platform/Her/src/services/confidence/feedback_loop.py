"""
置信度反馈闭环系统

功能：
- 用户反馈收集API
- 规则优化器（基于反馈调整验证规则）
- 权重自适应调整
- 误报补偿机制
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
import json

from utils.logger import logger
from utils.db_session_manager import db_session
from db.models import UserDB
from models.profile_confidence_models import (
    ProfileConfidenceDetailDB,
    CrossValidationRuleDB,
    ConfidenceEvaluationLogDB,
)


# ============================================
# 反馈数据模型
# ============================================

FEEDBACK_TYPES = {
    "accurate": {
        "description": "置信度判断准确",
        "actual_trustworthiness_adjustment": 0,  # 实际与预测相同
        "severity": "positive",
    },
    "inaccurate_high": {
        "description": "高估了可信度（实际不可信）",
        "actual_trustworthiness_adjustment": -0.3,
        "severity": "negative",
    },
    "inaccurate_low": {
        "description": "低估了可信度（实际可信）",
        "actual_trustworthiness_adjustment": +0.2,
        "severity": "positive",
    },
    "fake_info": {
        "description": "发现虚假信息",
        "actual_trustworthiness_adjustment": -0.8,
        "severity": "critical",
    },
    "scam_behavior": {
        "description": "发现诈骗行为",
        "actual_trustworthiness_adjustment": -0.9,
        "severity": "critical",
    },
    "false_flag": {
        "description": "误报标记（系统标记异常但实际正常）",
        "actual_trustworthiness_adjustment": +0.1,
        "severity": "correction",
    },
    "real_issue": {
        "description": "漏报问题（系统未标记但实际有问题）",
        "actual_trustworthiness_adjustment": -0.2,
        "severity": "correction",
    },
}


# ============================================
# 反馈收集服务
# ============================================

class ConfidenceFeedbackService:
    """置信度反馈收集和处理服务"""

    # 反馈历史存储（用于优化）
    _feedback_history: List[Dict] = []

    async def collect_match_feedback(
        self,
        reporter_id: str,
        target_user_id: str,
        feedback_type: str,
        detail: str = "",
        evidence: Dict = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        收集用户对匹配对象置信度判断的反馈

        Args:
            reporter_id: 反馈者ID
            target_user_id: 被反馈的用户ID
            feedback_type: 反馈类型
            detail: 详细描述
            evidence: 证据信息
            db: 数据库会话

        Returns:
            处理结果
        """
        feedback_config = FEEDBACK_TYPES.get(feedback_type)
        if not feedback_config:
            return {"success": False, "error": "unknown_feedback_type"}

        logger.info(f"收到反馈: {feedback_type} from {reporter_id} about {target_user_id}")

        # 获取目标用户的置信度记录
        with db_session() as session:
            confidence_detail = session.query(ProfileConfidenceDetailDB).filter(
                ProfileConfidenceDetailDB.user_id == target_user_id
            ).first()

            if not confidence_detail:
                # 如果没有记录，先创建基础记录
                from services.profile_confidence_service import profile_confidence_service
                profile_confidence_service.evaluate_user_confidence(target_user_id, trigger_source="feedback_triggered")
                confidence_detail = session.query(ProfileConfidenceDetailDB).filter(
                    ProfileConfidenceDetailDB.user_id == target_user_id
                ).first()

            predicted_confidence = confidence_detail.overall_confidence if confidence_detail else 0.3

            # 计算实际可信度
            adjustment = feedback_config["actual_trustworthiness_adjustment"]
            actual_trustworthiness = predicted_confidence + adjustment
            actual_trustworthiness = max(0.05, min(1.0, actual_trustworthiness))

            # 记录反馈
            feedback_record = {
                "reporter_id": reporter_id,
                "target_user_id": target_user_id,
                "feedback_type": feedback_type,
                "detail": detail,
                "evidence": evidence,
                "predicted": predicted_confidence,
                "actual": actual_trustworthiness,
                "error": abs(predicted_confidence - actual_trustworthiness),
                "timestamp": datetime.now().isoformat(),
                "processed": False,
            }

            self._feedback_history.append(feedback_record)

            # 处理严重反馈
            if feedback_config["severity"] in ["critical", "negative"]:
                await self._handle_negative_feedback(
                    target_user_id, feedback_type, detail, evidence, session
                )

            # 处理纠正反馈
            elif feedback_config["severity"] == "correction":
                await self._handle_correction_feedback(
                    target_user_id, feedback_type, detail, session
                )

            # 记录评估日志
            log = ConfidenceEvaluationLogDB(
                id=str(__import__('uuid').uuid4()),
                user_id=target_user_id,
                trigger_source=f"feedback_{feedback_type}",
                confidence_before=predicted_confidence,
                confidence_after=actual_trustworthiness,
                confidence_change=actual_trustworthiness - predicted_confidence,
                evaluation_details=json.dumps(feedback_record),
            )
            session.add(log)
            session.commit()

            # 触发权重优化器
            await self._trigger_weight_optimization(target_user_id, predicted_confidence, actual_trustworthiness)

        return {
            "success": True,
            "feedback_type": feedback_type,
            "predicted": predicted_confidence,
            "actual": actual_trustworthiness,
            "processed": True,
        }

    async def _handle_negative_feedback(
        self,
        user_id: str,
        feedback_type: str,
        detail: str,
        evidence: Dict,
        db: Session
    ):
        """处理负面反馈（虚假信息/诈骗）"""
        confidence_detail = db.query(ProfileConfidenceDetailDB).filter(
            ProfileConfidenceDetailDB.user_id == user_id
        ).first()

        if confidence_detail:
            # 降级置信度
            if feedback_type == "fake_info":
                confidence_detail.overall_confidence = 0.15
            elif feedback_type == "scam_behavior":
                confidence_detail.overall_confidence = 0.05
            elif feedback_type == "inaccurate_high":
                # 适度降级
                confidence_detail.overall_confidence = max(0.2, confidence_detail.overall_confidence - 0.3)

            confidence_detail.confidence_level = self._get_level_from_confidence(confidence_detail.overall_confidence)

            # 添加反馈标记
            existing_flags = json.loads(confidence_detail.cross_validation_flags or "{}")
            existing_flags[f"user_feedback_{feedback_type}"] = {
                "severity": "high",
                "detail": detail or f"用户反馈：{feedback_type}",
                "reported_at": datetime.now().isoformat(),
                "evidence": evidence,
            }
            confidence_detail.cross_validation_flags = json.dumps(existing_flags)

            # 更新用户表
            user = db.query(UserDB).filter(UserDB.id == user_id).first()
            if user:
                user.profile_confidence = confidence_detail.overall_confidence

            db.commit()

            logger.warning(f"负面反馈处理完成: user={user_id}, confidence降至{confidence_detail.overall_confidence}")

    async def _handle_correction_feedback(
        self,
        user_id: str,
        feedback_type: str,
        detail: str,
        db: Session
    ):
        """处理纠正反馈（误报/漏报）"""
        confidence_detail = db.query(ProfileConfidenceDetailDB).filter(
            ProfileConfidenceDetailDB.user_id == user_id
        ).first()

        if confidence_detail:
            if feedback_type == "false_flag":
                # 移除误报标记
                existing_flags = json.loads(confidence_detail.cross_validation_flags or "{}")

                # 尝试找出误报的标记
                for flag_key in list(existing_flags.keys()):
                    if detail and detail in existing_flags[flag_key].get("detail", ""):
                        del existing_flags[flag_key]
                        logger.info(f"移除误报标记: {flag_key}")
                        break

                confidence_detail.cross_validation_flags = json.dumps(existing_flags)

                # 略微提升置信度
                confidence_detail.overall_confidence = min(1.0, confidence_detail.overall_confidence + 0.05)

            elif feedback_type == "real_issue":
                # 添加漏报标记
                existing_flags = json.loads(confidence_detail.cross_validation_flags or "{}")
                existing_flags["user_reported_issue"] = {
                    "severity": "medium",
                    "detail": detail,
                    "reported_at": datetime.now().isoformat(),
                }
                confidence_detail.cross_validation_flags = json.dumps(existing_flags)

                confidence_detail.overall_confidence = max(0.2, confidence_detail.overall_confidence - 0.15)

            confidence_detail.confidence_level = self._get_level_from_confidence(confidence_detail.overall_confidence)
            db.commit()

            logger.info(f"纠正反馈处理完成: user={user_id}, feedback={feedback_type}")

    async def _trigger_weight_optimization(
        self,
        user_id: str,
        predicted: float,
        actual: float
    ):
        """触发权重优化器记录反馈"""
        from services.confidence.dynamic_weights import weight_optimizer

        with db_session() as session:
            confidence_detail = session.query(ProfileConfidenceDetailDB).filter(
                ProfileConfidenceDetailDB.user_id == user_id
            ).first()

            dimensions = {}
            if confidence_detail:
                dimensions = {
                    "identity": confidence_detail.identity_confidence,
                    "cross_validation": confidence_detail.cross_validation_confidence,
                    "behavior": confidence_detail.behavior_consistency,
                    "social": confidence_detail.social_endorsement,
                    "time": confidence_detail.time_accumulation,
                }

            weight_optimizer.record_feedback(
                user_id=user_id,
                predicted_confidence=predicted,
                actual_trustworthiness=actual,
                dimensions=dimensions,
            )

    def _get_level_from_confidence(self, confidence: float) -> str:
        """从置信度数值获取等级"""
        if confidence >= 0.8:
            return "very_high"
        elif confidence >= 0.6:
            return "high"
        elif confidence >= 0.4:
            return "medium"
        else:
            return "low"

    def get_feedback_stats(self, days: int = 30) -> Dict[str, Any]:
        """获取反馈统计"""
        recent_feedback = [
            f for f in self._feedback_history
            if datetime.fromisoformat(f["timestamp"]) > datetime.now() - timedelta(days=days)
        ]

        stats = {
            "total": len(recent_feedback),
            "by_type": {},
            "accuracy_rate": 0,
            "false_positive_rate": 0,
            "false_negative_rate": 0,
        }

        # 按类型统计
        for feedback in recent_feedback:
            type_name = feedback["feedback_type"]
            stats["by_type"][type_name] = stats["by_type"].get(type_name, 0) + 1

        # 计算准确率
        accurate_count = stats["by_type"].get("accurate", 0)
        total = len(recent_feedback) or 1
        stats["accuracy_rate"] = accurate_count / total

        # 计算误报率
        false_positive_count = stats["by_type"].get("false_flag", 0) + stats["by_type"].get("inaccurate_high", 0)
        stats["false_positive_rate"] = false_positive_count / total

        # 计算漏报率
        false_negative_count = stats["by_type"].get("real_issue", 0) + stats["by_type"].get("inaccurate_low", 0)
        stats["false_negative_rate"] = false_negative_count / total

        return stats


# ============================================
# 规则优化器
# ============================================

class RuleOptimizer:
    """基于反馈优化交叉验证规则"""

    # 规则优化历史
    _optimization_history: List[Dict] = []

    def optimize_rules(self, min_samples: int = 50) -> Dict[str, Any]:
        """
        基于反馈优化所有规则

        Returns:
            优化结果
        """
        feedback_service = ConfidenceFeedbackService()
        feedback_stats = feedback_service.get_feedback_stats(30)

        if feedback_stats["total"] < min_samples:
            logger.info(f"反馈样本不足（{feedback_stats['total']}条），暂不优化规则")
            return {"optimized": False, "reason": "insufficient_samples"}

        optimizations = {}

        # 优化年龄-学历规则
        age_edu_result = self._optimize_age_education_rule(feedback_stats)
        if age_edu_result:
            optimizations["age_education_match"] = age_edu_result

        # 优化职业-收入规则
        occ_income_result = self._optimize_occupation_income_rule(feedback_stats)
        if occ_income_result:
            optimizations["occupation_income_match"] = occ_income_result

        # 记录优化历史
        if optimizations:
            self._optimization_history.append({
                "timestamp": datetime.now().isoformat(),
                "feedback_stats": feedback_stats,
                "optimizations": optimizations,
            })

        return {
            "optimized": True,
            "optimizations": optimizations,
            "feedback_samples": feedback_stats["total"],
        }

    def _optimize_age_education_rule(self, feedback_stats: Dict) -> Optional[Dict]:
        """优化年龄-学历验证规则"""
        # 检查误报率
        false_flag_count = feedback_stats["by_type"].get("false_flag", 0)
        total = feedback_stats["total"] or 1

        # 如果误报率超过20%，放宽规则
        if false_flag_count / total > 0.2:
            with db_session() as session:
                rule = session.query(CrossValidationRuleDB).filter(
                    CrossValidationRuleDB.rule_key == "age_education_match"
                ).first()

                if rule:
                    current_config = json.loads(rule.rule_config or "{}")
                    current_tolerance = current_config.get("tolerance_years", 2)

                    # 放宽容忍度
                    new_tolerance = current_tolerance + 1
                    current_config["tolerance_years"] = new_tolerance

                    # 降低异常阈值
                    new_threshold = rule.anomaly_threshold * 0.9

                    rule.rule_config = json.dumps(current_config)
                    rule.anomaly_threshold = new_threshold
                    rule.updated_at = datetime.now()

                    session.commit()

                    logger.info(f"年龄-学历规则优化: tolerance从{current_tolerance}放宽到{new_tolerance}")

                    return {
                        "before": {"tolerance_years": current_tolerance, "threshold": rule.anomaly_threshold / 0.9},
                        "after": {"tolerance_years": new_tolerance, "threshold": new_threshold},
                        "reason": "false_positive_rate_high",
                    }

        return None

    def _optimize_occupation_income_rule(self, feedback_stats: Dict) -> Optional[Dict]:
        """优化职业-收入验证规则"""
        # 检查漏报率（实际有问题但未标记）
        real_issue_count = feedback_stats["by_type"].get("real_issue", 0)
        total = feedback_stats["total"] or 1

        # 如果漏报率超过15%，收紧规则
        if real_issue_count / total > 0.15:
            with db_session() as session:
                rule = session.query(CrossValidationRuleDB).filter(
                    CrossValidationRuleDB.rule_key == "occupation_income_match"
                ).first()

                if rule:
                    current_config = json.loads(rule.rule_config or "{}")

                    # 收紧收入范围（减少宽容度）
                    current_tolerance = current_config.get("income_tolerance_k", 5)
                    new_tolerance = current_tolerance - 2
                    current_config["income_tolerance_k"] = new_tolerance

                    # 提高异常阈值
                    new_threshold = rule.anomaly_threshold * 1.1

                    rule.rule_config = json.dumps(current_config)
                    rule.anomaly_threshold = min(0.9, new_threshold)
                    rule.updated_at = datetime.now()

                    session.commit()

                    logger.info(f"职业-收入规则优化: tolerance从{current_tolerance}收紧到{new_tolerance}")

                    return {
                        "before": {"income_tolerance_k": current_tolerance, "threshold": rule.anomaly_threshold / 1.1},
                        "after": {"income_tolerance_k": new_tolerance, "threshold": new_threshold},
                        "reason": "false_negative_rate_high",
                    }

        return None


# ============================================
# 误报补偿机制
# ============================================

class FalsePositiveCompensator:
    """误报补偿机制"""

    async def compensate_false_positive(
        self,
        user_id: str,
        false_flag_type: str,
        detail: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        补偿误报用户

        当系统误判用户置信度后，给予补偿：
        - 恢复置信度
        - 给予信用积分补偿
        - 记录补偿日志

        Returns:
            补偿结果
        """
        with db_session() as session:
            confidence_detail = session.query(ProfileConfidenceDetailDB).filter(
                ProfileConfidenceDetailDB.user_id == user_id
            ).first()

            if not confidence_detail:
                return {"compensated": False, "reason": "no_confidence_record"}

            # 记录补偿前状态
            before_confidence = confidence_detail.overall_confidence

            # 恢复置信度（补偿误报扣分）
            compensation_amount = self._calculate_compensation(false_flag_type)
            after_confidence = min(1.0, before_confidence + compensation_amount)

            confidence_detail.overall_confidence = after_confidence
            confidence_detail.confidence_level = self._get_level_from_confidence(after_confidence)

            # 更新置信度历史
            history = json.loads(confidence_detail.confidence_history or "[]")
            history.append({
                "at": datetime.now().isoformat(),
                "confidence_before": before_confidence,
                "confidence_after": after_confidence,
                "change": compensation_amount,
                "trigger": "false_positive_compensation",
                "detail": f"误报补偿: {false_flag_type}",
            })
            confidence_detail.confidence_history = json.dumps(history)

            # 移除误报标记
            flags = json.loads(confidence_detail.cross_validation_flags or "{}")
            for flag_key in list(flags.keys()):
                if flag_key.startswith(false_flag_type):
                    del flags[flag_key]
            confidence_detail.cross_validation_flags = json.dumps(flags)

            # 更新用户表
            user = session.query(UserDB).filter(UserDB.id == user_id).first()
            if user:
                user.profile_confidence = after_confidence

            session.commit()

            logger.info(f"误报补偿完成: user={user_id}, 补偿{compensation_amount:.2f}, 置信度从{before_confidence:.2f}恢复到{after_confidence:.2f}")

            return {
                "compensated": True,
                "before_confidence": before_confidence,
                "after_confidence": after_confidence,
                "compensation_amount": compensation_amount,
            }

    def _calculate_compensation(self, false_flag_type: str) -> float:
        """计算补偿量"""
        # 根据误报类型决定补偿量
        compensation_rates = {
            "age_education_mismatch": 0.15,
            "occupation_income_mismatch": 0.10,
            "location_activity_mismatch": 0.05,
            "interest_browse_mismatch": 0.08,
            "age_self_declared_mismatch": 0.12,
            "photo_personality_mismatch": 0.03,
        }

        return compensation_rates.get(false_flag_type, 0.10)

    def _get_level_from_confidence(self, confidence: float) -> str:
        """从置信度数值获取等级"""
        if confidence >= 0.8:
            return "very_high"
        elif confidence >= 0.6:
            return "high"
        elif confidence >= 0.4:
            return "medium"
        else:
            return "low"


# ============================================
# 反馈API端点
# ============================================

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

router = APIRouter(prefix="/api/confidence/feedback", tags=["confidence_feedback"])


class MatchFeedbackRequest(BaseModel):
    """匹配反馈请求"""
    target_user_id: str
    feedback_type: str  # accurate, inaccurate_high, inaccurate_low, fake_info, scam_behavior, false_flag, real_issue
    detail: Optional[str] = None
    evidence: Optional[Dict] = None


class RuleOptimizationRequest(BaseModel):
    """规则优化请求"""
    force: bool = False


@router.post("/match")
async def submit_match_feedback(
    request: MatchFeedbackRequest,
    current_user_id: str = Depends(lambda: __import__('auth.jwt', fromlist=['get_current_user']).get_current_user())
):
    """提交匹配对象置信度反馈"""
    feedback_service = ConfidenceFeedbackService()

    result = await feedback_service.collect_match_feedback(
        reporter_id=current_user_id,
        target_user_id=request.target_user_id,
        feedback_type=request.feedback_type,
        detail=request.detail or "",
        evidence=request.evidence,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@router.get("/stats")
async def get_feedback_stats():
    """获取反馈统计"""
    feedback_service = ConfidenceFeedbackService()
    return feedback_service.get_feedback_stats()


@router.post("/optimize-rules")
async def optimize_rules(
    request: RuleOptimizationRequest,
    admin_user_id: str = Depends(lambda: __import__('auth.jwt', fromlist=['get_admin_user']).get_admin_user())
):
    """优化验证规则（管理员接口）"""
    rule_optimizer = RuleOptimizer()
    result = rule_optimizer.optimize_rules(min_samples=20 if request.force else 50)
    return result


@router.post("/compensate")
async def compensate_false_positive(
    user_id: str,
    false_flag_type: str,
    detail: str,
    admin_user_id: str = Depends(lambda: __import__('auth.jwt', fromlist=['get_admin_user']).get_admin_user())
):
    """补偿误报用户（管理员接口）"""
    compensator = FalsePositiveCompensator()

    with db_session() as session:
        result = await compensator.compensate_false_positive(
            user_id=user_id,
            false_flag_type=false_flag_type,
            detail=detail,
            db=session
        )

    if not result.get("compensated"):
        raise HTTPException(status_code=400, detail=result.get("reason"))

    return result


# ============================================
# 导出
# ============================================

# 全局服务实例
confidence_feedback_service = ConfidenceFeedbackService()
rule_optimizer = RuleOptimizer()
false_positive_compensator = FalsePositiveCompensator()