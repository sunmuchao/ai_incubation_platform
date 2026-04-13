"""
用户画像置信度评估服务

核心功能：
- 多维置信度计算（身份、交叉验证、行为一致性、社交背书、时间积累）
- 交叉验证引擎
- 行为一致性检测
- 验证建议生成
- 置信度变化追踪

置信度计算公式：
overall_confidence = base_score (0.3)
  + identity_verified × 0.25
  + cross_validation_score × 0.20
  + behavior_consistency × 0.15
  + social_endorsement × 0.10

评估触发时机：
- 用户注册后首次评估
- 画像更新后重新评估
- 定期评估（每日/每周）
- 行为变化触发评估
"""
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
import json
import uuid
from enum import Enum

from utils.db_session_manager import db_session, db_session_readonly
from utils.logger import logger
from services.base_service import BaseService
from models.profile_confidence_models import (
    ProfileConfidenceDetailDB,
    CrossValidationRuleDB,
    ConfidenceEvaluationLogDB,
    VerificationSuggestionDB,
    ConfidenceLevel,
    ValidationFlagType,
)
from db.models import UserDB, IdentityVerificationDB, VerificationBadgeDB


# ============================================
# 置信度权重配置
# ============================================

CONFIDENCE_WEIGHTS = {
    "base_score": 0.3,          # 基础分（注册即有）
    "identity": 0.25,           # 身份验证
    "cross_validation": 0.20,   # 交叉验证
    "behavior": 0.15,           # 行为一致性
    "social": 0.10,             # 社交背书
}

# 置信度等级阈值
CONFIDENCE_LEVEL_THRESHOLDS = {
    ConfidenceLevel.LOW: (0.0, 0.4, "需谨慎"),
    ConfidenceLevel.MEDIUM: (0.4, 0.6, "普通用户"),
    ConfidenceLevel.HIGH: (0.6, 0.8, "较可信"),
    ConfidenceLevel.VERY_HIGH: (0.8, 1.0, "极可信"),
}


# ============================================
# 交叉验证规则配置
# ============================================

# 年龄与学历匹配规则
# 假设：本科毕业年龄约22-23岁，硕士约25-26岁，博士约28-30岁
AGE_EDUCATION_EXPECTED_GRADUATION = {
    "high_school": 18,      # 高中毕业约18岁
    "college": 20,          # 专科毕业约20岁
    "bachelor": 22,         # 本科毕业约22岁
    "bachelor_student": 20, # 本科在读约20岁
    "master": 25,           # 硕士毕业约25岁
    "master_student": 23,   # 硕士在读约23岁
    "phd": 28,              # 博士毕业约28岁
    "phd_student": 25,      # 博士在读约25岁
}

# 职业与收入合理范围（月薪，单位：千元）
OCCUPATION_INCOME_RANGES = {
    "student": (0, 10),         # 学生收入较低
    "tech": (10, 100),          # 技术岗收入范围宽
    "finance": (15, 200),       # 金融岗收入较高
    "education": (5, 30),       # 教育岗中等
    "medical": (10, 80),        # 医疗岗中等偏高
    "government": (8, 40),      # 公务员中等
    "entrepreneur": (0, 500),   # 创业者范围极宽
    "freelancer": (5, 100),     # 自由职业者范围宽
    "other": (5, 100),          # 其他默认范围
}

# 收入区间映射（字符串 -> 数值范围）
INCOME_RANGE_VALUES = {
    "no_income": (0, 0),
    "under_10": (0, 10),
    "10_20": (10, 20),
    "20_30": (20, 30),
    "30_50": (30, 50),
    "50_100": (50, 100),
    "over_100": (100, 500),
    "private": None,  # 不公开，不参与验证
}


class ProfileConfidenceService(BaseService):
    """用户画像置信度评估服务"""

    def __init__(self, db: Optional[Session] = None):
        super().__init__(db)
        self._should_close_db: bool = db is None

    def _get_db(self) -> Session:
        if self._db is None:
            from db.database import SessionLocal
            self._db = SessionLocal()
            self._should_close_db = True
        return self._db

    def close(self):
        if self._should_close_db and self._db is not None:
            try:
                self._db.commit()
                self._db.close()
            except Exception as e:
                logger.error(f"Error closing database session: {e}")
            finally:
                self._db = None
                self._should_close_db = False

    # ============================================
    # 核心评估方法
    # ============================================

    def evaluate_user_confidence(
        self,
        user_id: str,
        trigger_source: str = "manual",
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        评估用户置信度

        Args:
            user_id: 用户 ID
            trigger_source: 评估触发来源
            force_refresh: 是否强制刷新（跳过缓存）

        Returns:
            评估结果字典
        """
        start_time = datetime.now()
        db = self._get_db()

        try:
            # 获取用户信息
            user = db.query(UserDB).filter(UserDB.id == user_id).first()
            if not user:
                return {"success": False, "error": "User not found"}

            # 获取或创建置信度详情
            confidence_detail = self._get_or_create_confidence_detail(user_id)

            # 记录评估前置信度
            confidence_before = confidence_detail.overall_confidence

            # 计算各维度置信度
            identity_score = self._calculate_identity_confidence(user_id, db)
            cross_validation_score, cross_flags = self._calculate_cross_validation_confidence(user, db)
            behavior_score, behavior_detail = self._calculate_behavior_consistency(user_id, db)
            social_score, social_detail = self._calculate_social_endorsement(user_id, db)
            time_score, time_detail = self._calculate_time_accumulation(user, db)

            # 计算总置信度
            overall_confidence = CONFIDENCE_WEIGHTS["base_score"]
            overall_confidence += identity_score * CONFIDENCE_WEIGHTS["identity"]
            overall_confidence += cross_validation_score * CONFIDENCE_WEIGHTS["cross_validation"]
            overall_confidence += behavior_score * CONFIDENCE_WEIGHTS["behavior"]
            overall_confidence += social_score * CONFIDENCE_WEIGHTS["social"]

            # 确保范围在 0-1
            overall_confidence = max(0.0, min(1.0, overall_confidence))

            # 确定置信度等级
            confidence_level = self._determine_confidence_level(overall_confidence)

            # 更新置信度详情
            confidence_detail.overall_confidence = overall_confidence
            confidence_detail.confidence_level = confidence_level.value
            confidence_detail.identity_confidence = identity_score
            confidence_detail.cross_validation_confidence = cross_validation_score
            confidence_detail.behavior_consistency = behavior_score
            confidence_detail.social_endorsement = social_score
            confidence_detail.time_accumulation = time_score
            confidence_detail.cross_validation_flags = json.dumps(cross_flags)
            confidence_detail.interest_consistency_detail = json.dumps(behavior_detail.get("interest", {}))
            confidence_detail.personality_consistency_detail = json.dumps(behavior_detail.get("personality", {}))
            confidence_detail.account_age_days = time_detail.get("account_age_days", 0)
            confidence_detail.active_days = time_detail.get("active_days", 0)
            confidence_detail.profile_completeness_pct = time_detail.get("profile_completeness", 0.0)
            confidence_detail.positive_feedback_rate = social_detail.get("positive_feedback_rate", 0.5)
            confidence_detail.last_evaluated_at = datetime.now()
            confidence_detail.evaluation_version = "v1.0"

            # 更新置信度历史
            self._update_confidence_history(confidence_detail, confidence_before, overall_confidence, trigger_source)

            # 生成验证建议
            recommendations = self._generate_verification_recommendations(
                user_id, confidence_detail, identity_score, cross_validation_score, behavior_score, social_score
            )
            confidence_detail.recommended_verifications = json.dumps(recommendations)

            db.commit()
            db.refresh(confidence_detail)

            # 记录评估日志
            evaluation_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self._log_evaluation(
                user_id, trigger_source, confidence_before, overall_confidence,
                evaluation_time_ms, cross_flags, db
            )

            # 更新 UserDB 的置信度字段（保持数据一致性）
            user.profile_confidence = overall_confidence
            db.commit()

            logger.info(f"Confidence evaluated for user {user_id}: {overall_confidence:.2f} ({confidence_level.value})")

            return {
                "success": True,
                "user_id": user_id,
                "overall_confidence": overall_confidence,
                "confidence_level": confidence_level.value,
                "confidence_level_name": CONFIDENCE_LEVEL_THRESHOLDS.get(confidence_level, ("", "", ""))[2],
                "dimensions": {
                    "identity": identity_score,
                    "cross_validation": cross_validation_score,
                    "behavior": behavior_score,
                    "social": social_score,
                    "time": time_score,
                },
                "cross_validation_flags": cross_flags,
                "recommendations": recommendations,
                "evaluation_time_ms": evaluation_time_ms,
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Confidence evaluation failed for user {user_id}: {e}")
            return {"success": False, "error": str(e)}

    # ============================================
    # 各维度置信度计算
    # ============================================

    def _calculate_identity_confidence(self, user_id: str, db: Session) -> float:
        """
        计算身份验证置信度

        来源：
        - 实名认证：+0.4
        - 人脸核身：+0.3
        - 手机验证：+0.2
        - 邮箱验证：+0.1
        """
        score = 0.0

        # 检查实名认证
        identity_verification = db.query(IdentityVerificationDB).filter(
            IdentityVerificationDB.user_id == user_id,
            IdentityVerificationDB.verification_status == "verified"
        ).first()
        if identity_verification:
            score += 0.4
            # 人脸核身额外加分
            if identity_verification.verification_type == "advanced":
                score += 0.3

        # 检查信任徽章
        badges = db.query(VerificationBadgeDB).filter(
            VerificationBadgeDB.user_id == user_id,
            VerificationBadgeDB.status == "active"
        ).all()

        badge_types = {b.badge_type for b in badges}

        if "phone_verified" in badge_types:
            score += 0.15
        if "email_verified" in badge_types:
            score += 0.10
        if "education_verified" in badge_types:
            score += 0.15
        if "career_verified" in badge_types:
            score += 0.10

        return min(1.0, score)

    def _calculate_cross_validation_confidence(
        self,
        user: UserDB,
        db: Session
    ) -> Tuple[float, Dict[str, Any]]:
        """
        计算交叉验证置信度

        规则：
        - 年龄-学历匹配
        - 职业-收入匹配
        - 地理-活跃时间匹配
        """
        score = 1.0  # 默认满分，发现异常则扣分
        flags = {}

        # 1. 年龄-学历匹配验证
        age_education_result = self._validate_age_education(user)
        if not age_education_result["valid"]:
            severity = age_education_result.get("severity", "medium")
            penalty = self._severity_to_penalty(severity)
            score -= penalty
            flags["age_education_mismatch"] = {
                "severity": severity,
                "detail": age_education_result.get("detail", ""),
                "claimed_age": user.age,
                "claimed_education": user.education,
            }

        # 2. 职业-收入匹配验证
        occupation_income_result = self._validate_occupation_income(user)
        if not occupation_income_result["valid"]:
            severity = occupation_income_result.get("severity", "medium")
            penalty = self._severity_to_penalty(severity)
            score -= penalty
            flags["occupation_income_mismatch"] = {
                "severity": severity,
                "detail": occupation_income_result.get("detail", ""),
                "claimed_occupation": user.occupation,
                "claimed_income": user.income,
            }

        # 3. 地理-活跃时间匹配验证（如果有行为数据）
        location_activity_result = self._validate_location_activity(user, db)
        if not location_activity_result["valid"]:
            severity = location_activity_result.get("severity", "low")
            penalty = self._severity_to_penalty(severity)
            score -= penalty
            flags["location_activity_mismatch"] = {
                "severity": severity,
                "detail": location_activity_result.get("detail", ""),
            }

        # 确保分数在 0-1 范围
        score = max(0.0, min(1.0, score))

        return score, flags

    def _validate_age_education(self, user: UserDB) -> Dict[str, Any]:
        """验证年龄与学历是否匹配"""
        if not user.education or user.education == "private":
            return {"valid": True}

        expected_graduation_age = AGE_EDUCATION_EXPECTED_GRADUATION.get(user.education)
        if expected_graduation_age is None:
            return {"valid": True}

        # 计算年龄差异
        age_diff = user.age - expected_graduation_age

        # 如果年龄小于预期毕业年龄，异常度高
        if age_diff < -2:  # 宽容度：2年
            return {
                "valid": False,
                "severity": "high",
                "detail": f"年龄 {user.age} 岁但学历为 {user.education}，预期毕业年龄约 {expected_graduation_age} 岁"
            }

        # 如果年龄差异过大（超过15年），中等异常
        if age_diff > 15:
            return {
                "valid": False,
                "severity": "medium",
                "detail": f"年龄 {user.age} 岁与学历 {user.education} 毕业时间差距较大"
            }

        return {"valid": True}

    def _validate_occupation_income(self, user: UserDB) -> Dict[str, Any]:
        """验证职业与收入是否匹配"""
        if not user.occupation or not user.income or user.income == "private":
            return {"valid": True}

        income_range = INCOME_RANGE_VALUES.get(user.income)
        if income_range is None:
            return {"valid": True}

        expected_range = OCCUPATION_INCOME_RANGES.get(user.occupation, (0, 100))
        income_min, income_max = income_range
        expected_min, expected_max = expected_range

        # 检查收入是否在职业预期范围内
        # 如果用户收入区间完全超出职业预期范围
        if income_max < expected_min - 5:  # 宽容度：5k
            return {
                "valid": False,
                "severity": "high",
                "detail": f"职业 {user.occupation} 预期收入 {expected_min}-{expected_max}k，但声称收入 {user.income}"
            }

        if income_min > expected_max + 10:  # 宽容度：10k（高收入可能合理）
            return {
                "valid": False,
                "severity": "low",
                "detail": f"职业 {user.occupation} 收入 {user.income} 高于常见范围，可能是高管/特殊情况"
            }

        return {"valid": True}

    def _validate_location_activity(self, user: UserDB, db: Session) -> Dict[str, Any]:
        """验证地理位置与活跃时间是否匹配"""
        # 简化实现：基于用户注册时间和最后登录时间
        # 如果用户声称在北京，但凌晨3-5点频繁活跃（非北京时区），可能有异常

        # 暂时返回有效（需要更多行为数据支持）
        return {"valid": True}

    def _severity_to_penalty(self, severity: str) -> float:
        """将异常严重等级转换为扣分"""
        penalties = {
            "low": 0.1,
            "medium": 0.25,
            "high": 0.4,
        }
        return penalties.get(severity, 0.2)

    def _calculate_behavior_consistency(
        self,
        user_id: str,
        db: Session
    ) -> Tuple[float, Dict[str, Any]]:
        """
        计算行为一致性置信度

        检查：
        - 声称兴趣 vs 实际浏览行为
        - 声称性格 vs 聊天风格
        """
        score = 0.5  # 默认中等置信度（无足够数据时）
        detail = {"interest": {}, "personality": {}}

        try:
            # 获取用户声称的兴趣
            user = db.query(UserDB).filter(UserDB.id == user_id).first()
            if user and user.interests:
                try:
                    claimed_interests = json.loads(user.interests)
                except:
                    claimed_interests = user.interests.split(",") if user.interests else []

                # 获取用户浏览行为（从 BehaviorEventDB）
                # 简化实现：暂时返回默认值
                # 完整实现需要分析用户浏览过的其他用户画像
                detail["interest"] = {
                    "claimed_interests": claimed_interests,
                    "match_rate": 0.5,  # 待实现
                    "sample_size": 0,
                }

            # 性格一致性分析（从聊天记录分析）
            # 暂时返回默认值
            detail["personality"] = {
                "claimed_personality": "unknown",
                "inferred_personality": "unknown",
                "match": True,
            }

        except Exception as e:
            logger.warning(f"Behavior consistency calculation failed: {e}")

        return score, detail

    def _calculate_social_endorsement(
        self,
        user_id: str,
        db: Session
    ) -> Tuple[float, Dict[str, Any]]:
        """
        计算社交背书置信度

        来源：
        - 邀请码注册：+0.3
        - 朋友推荐：+0.2
        - 好评率：基于 positive_feedback_rate
        """
        score = 0.0
        detail = {}

        try:
            # 检查邀请来源
            confidence_detail = db.query(ProfileConfidenceDetailDB).filter(
                ProfileConfidenceDetailDB.user_id == user_id
            ).first()

            if confidence_detail:
                if confidence_detail.invite_source_type == "invite_code":
                    score += 0.25
                    detail["invite_source"] = "invite_code"
                elif confidence_detail.invite_source_type == "referral":
                    score += 0.30
                    detail["invite_source"] = "referral"

                # 好评率贡献
                positive_rate = confidence_detail.positive_feedback_rate or 0.5
                # 好评率 > 0.7 加分，< 0.3 减分
                if positive_rate > 0.7:
                    score += 0.20
                elif positive_rate > 0.5:
                    score += 0.10
                elif positive_rate < 0.3:
                    score -= 0.10

                detail["positive_feedback_rate"] = positive_rate

            else:
                detail["positive_feedback_rate"] = 0.5

        except Exception as e:
            logger.warning(f"Social endorsement calculation failed: {e}")

        return min(1.0, max(0.0, score)), detail

    def _calculate_time_accumulation(
        self,
        user: UserDB,
        db: Session
    ) -> Tuple[float, Dict[str, Any]]:
        """
        计算时间积累置信度

        来源：
        - 注册时长（每30天 +0.1，最多 +0.3）
        - 活跃天数（每10天活跃 +0.05，最多 +0.2）
        - 画像完善度（0-100% -> 0-0.5）
        """
        score = 0.0
        detail = {}

        try:
            # 注册时长
            if user.created_at:
                account_age_days = (datetime.now() - user.created_at).days
                age_score = min(0.3, account_age_days / 300)  # 每100天 +0.1，最多 +0.3
                score += age_score
                detail["account_age_days"] = account_age_days

            # 活跃天数（从 last_login 推算）
            # 简化实现：使用注册时长的一半作为活跃天数估计
            active_days = detail.get("account_age_days", 0) // 2
            active_score = min(0.2, active_days / 200)  # 每100天 +0.1，最多 +0.2
            score += active_score
            detail["active_days"] = active_days

            # 画像完善度
            completeness = self._calculate_profile_completeness(user)
            completeness_score = completeness / 200  # 100% -> 0.5
            score += completeness_score
            detail["profile_completeness"] = completeness

        except Exception as e:
            logger.warning(f"Time accumulation calculation failed: {e}")

        return min(1.0, score), detail

    def _calculate_profile_completeness(self, user: UserDB) -> float:
        """计算画像完善度百分比"""
        fields_to_check = [
            ("name", 5),
            ("age", 10),
            ("gender", 10),
            ("location", 10),
            ("education", 10),
            ("occupation", 10),
            ("income", 10),
            ("interests", 15),
            ("bio", 10),
            ("avatar_url", 10),
        ]

        completeness = 0.0
        for field, weight in fields_to_check:
            value = getattr(user, field, None)
            if value:
                if isinstance(value, str) and value.strip():
                    completeness += weight
                elif isinstance(value, (int, float)) and value > 0:
                    completeness += weight

        return min(100.0, completeness)

    # ============================================
    # 辅助方法
    # ============================================

    def _get_or_create_confidence_detail(self, user_id: str) -> ProfileConfidenceDetailDB:
        """获取或创建置信度详情"""
        db = self._get_db()
        detail = db.query(ProfileConfidenceDetailDB).filter(
            ProfileConfidenceDetailDB.user_id == user_id
        ).first()

        if not detail:
            detail = ProfileConfidenceDetailDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                overall_confidence=0.3,
                confidence_level="medium",
            )
            db.add(detail)
            db.commit()
            db.refresh(detail)

        return detail

    def _determine_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """根据置信度确定等级"""
        for level, (min_val, max_val, _) in CONFIDENCE_LEVEL_THRESHOLDS.items():
            if min_val <= confidence < max_val:
                return level
        return ConfidenceLevel.LOW

    def _update_confidence_history(
        self,
        detail: ProfileConfidenceDetailDB,
        confidence_before: float,
        confidence_after: float,
        trigger_source: str
    ):
        """更新置信度变化历史"""
        try:
            history = json.loads(detail.confidence_history or "[]")
        except:
            history = []

        history.append({
            "at": datetime.now().isoformat(),
            "confidence_before": confidence_before,
            "confidence_after": confidence_after,
            "change": confidence_after - confidence_before,
            "trigger": trigger_source,
        })

        # 只保留最近 20 条历史
        history = history[-20:]
        detail.confidence_history = json.dumps(history)

    def _generate_verification_recommendations(
        self,
        user_id: str,
        detail: ProfileConfidenceDetailDB,
        identity_score: float,
        cross_validation_score: float,
        behavior_score: float,
        social_score: float
    ) -> List[Dict[str, Any]]:
        """生成验证建议"""
        recommendations = []

        # 身份验证建议
        if identity_score < 0.4:
            recommendations.append({
                "type": "identity_verify",
                "priority": "high",
                "estimated_confidence_boost": 0.25,
                "reason": "完成实名认证可大幅提升可信度",
            })

        if identity_score < 0.7:
            recommendations.append({
                "type": "face_verify",
                "priority": "medium",
                "estimated_confidence_boost": 0.15,
                "reason": "人脸核身认证进一步验证身份真实性",
            })

        # 交叉验证异常修复建议
        try:
            flags = json.loads(detail.cross_validation_flags or "{}")
            if "age_education_mismatch" in flags:
                recommendations.append({
                    "type": "education_verify",
                    "priority": "high",
                    "estimated_confidence_boost": 0.15,
                    "reason": "学历认证可消除年龄-学历异常标记",
                })
            if "occupation_income_mismatch" in flags:
                recommendations.append({
                    "type": "occupation_verify",
                    "priority": "medium",
                    "estimated_confidence_boost": 0.10,
                    "reason": "职业认证可消除职业-收入异常标记",
                })
        except:
            pass

        # 画像完善建议
        if detail.profile_completeness_pct < 70:
            recommendations.append({
                "type": "profile_complete",
                "priority": "low",
                "estimated_confidence_boost": 0.05,
                "reason": "完善个人资料可提升基础置信度",
            })

        # 行为一致性建议
        if behavior_score < 0.5:
            recommendations.append({
                "type": "behavior_confirm",
                "priority": "low",
                "estimated_confidence_boost": 0.10,
                "reason": "通过浏览和互动确认您的兴趣偏好",
            })

        return recommendations

    def _log_evaluation(
        self,
        user_id: str,
        trigger_source: str,
        confidence_before: Optional[float],
        confidence_after: float,
        evaluation_time_ms: int,
        cross_flags: Dict,
        db: Session
    ):
        """记录评估日志"""
        log = ConfidenceEvaluationLogDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            trigger_source=trigger_source,
            confidence_before=confidence_before,
            confidence_after=confidence_after,
            confidence_change=confidence_after - (confidence_before or 0.3),
            dimension_changes=json.dumps({}),
            evaluation_details=json.dumps({"cross_validation_flags": cross_flags}),
            evaluation_time_ms=evaluation_time_ms,
        )
        db.add(log)

    # ============================================
    # 公开查询方法
    # ============================================

    def get_confidence_detail(self, user_id: str) -> Dict[str, Any]:
        """获取用户置信度详情"""
        db = self._get_db()

        detail = db.query(ProfileConfidenceDetailDB).filter(
            ProfileConfidenceDetailDB.user_id == user_id
        ).first()

        if not detail:
            # 尚未评估，执行首次评估
            return self.evaluate_user_confidence(user_id, trigger_source="query")

        return {
            "success": True,
            "user_id": user_id,
            "overall_confidence": detail.overall_confidence,
            "confidence_level": detail.confidence_level,
            "confidence_level_name": CONFIDENCE_LEVEL_THRESHOLDS.get(
                ConfidenceLevel(detail.confidence_level), ("", "", "")
            )[2],
            "dimensions": {
                "identity": detail.identity_confidence,
                "cross_validation": detail.cross_validation_confidence,
                "behavior": detail.behavior_consistency,
                "social": detail.social_endorsement,
                "time": detail.time_accumulation,
            },
            "cross_validation_flags": json.loads(detail.cross_validation_flags or "{}"),
            "recommendations": json.loads(detail.recommended_verifications or "[]"),
            "last_evaluated_at": detail.last_evaluated_at.isoformat() if detail.last_evaluated_at else None,
        }

    def get_confidence_summary(self, user_id: str) -> Dict[str, Any]:
        """获取置信度摘要（用于展示在匹配卡片等场景）"""
        detail = self.get_confidence_detail(user_id)

        if not detail.get("success"):
            return {"confidence": 0.3, "level": "medium", "verified": False}

        return {
            "confidence": detail["overall_confidence"],
            "level": detail["confidence_level"],
            "level_name": detail["confidence_level_name"],
            "verified": detail["dimensions"]["identity"] > 0.4,
            "flags_count": len(detail.get("cross_validation_flags", {})),
        }

    def batch_evaluate_users(
        self,
        user_ids: List[str],
        trigger_source: str = "periodic"
    ) -> Dict[str, Any]:
        """批量评估用户置信度"""
        results = {"success_count": 0, "failed_count": 0, "details": {}}

        for user_id in user_ids:
            try:
                result = self.evaluate_user_confidence(user_id, trigger_source)
                if result.get("success"):
                    results["success_count"] += 1
                    results["details"][user_id] = {
                        "confidence": result["overall_confidence"],
                        "level": result["confidence_level"],
                    }
                else:
                    results["failed_count"] += 1
            except Exception as e:
                results["failed_count"] += 1
                logger.error(f"Batch evaluation failed for user {user_id}: {e}")

        return results


# ============================================
# 全局单例
# ============================================

profile_confidence_service = ProfileConfidenceService()