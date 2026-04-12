"""
AI 持续学习服务

L4 功能：基于用户历史行为的偏好学习和记忆系统
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
import json

from db.database import SessionLocal
from utils.db_session_manager import db_session, db_session_readonly, optional_db_session
from models.l4_learning_models import (
    UserPreferenceMemory,
    BehaviorLearningPattern,
    MatchingWeightAdjustment,
    UserLearningProfile,
)
from utils.logger import logger
from services.base_service import BaseService


class AILearningService(BaseService):
    """AI 持续学习服务"""

    def __init__(self, db: Optional[Session] = None):
        super().__init__(db)
        self._should_close_db: bool = db is None

    def _get_db(self) -> Session:
        """
        获取数据库会话

        注意：推荐在构造函数中传入 db session，避免延迟创建。
        """
        if self._db is None:
            self._db = SessionLocal()
            self._should_close_db = True
        return self._db

    def close_db(self):
        """关闭数据库会话（仅关闭自己创建的）"""
        if self._should_close_db and self._db is not None:
            try:
                self._db.commit()
                self._db.close()
            except Exception as e:
                logger.error(f"Error closing database session: {e}")
            finally:
                self._db = None
                self._should_close_db = False

    # ========== 用户偏好记忆管理 ==========

    def add_preference(
        self,
        user_id: str,
        category: str,
        preference_key: str,
        preference_value: Any,
        preference_type: str = "like",
        subcategory: str = None,
        confidence_score: float = 0.5,
        source_events: List[str] = None,
        inference_method: str = "rule_based",
    ) -> Tuple[bool, str, Optional[UserPreferenceMemory]]:
        """
        添加用户偏好

        Args:
            user_id: 用户 ID
            category: 偏好类别 (matching/date/gift/communication/topic)
            preference_key: 偏好键
            preference_value: 偏好值
            preference_type: 偏好类型 (like/dislike/neutral)
            subcategory: 子类别
            confidence_score: 置信度 0-1
            source_events: 来源事件 ID 列表
            inference_method: 推断方法

        Returns:
            (success, message, preference)
        """
        try:
            db = self._get_db()

            # 检查是否已存在类似偏好
            existing = db.query(UserPreferenceMemory).filter(
                UserPreferenceMemory.user_id == user_id,
                UserPreferenceMemory.category == category,
                UserPreferenceMemory.preference_key == preference_key,
                UserPreferenceMemory.is_active == True,
            ).first()

            if existing:
                # 更新现有偏好
                existing.preference_value = preference_value
                existing.confidence_score = max(existing.confidence_score, confidence_score)
                if source_events:
                    existing.source_events = list(set(existing.source_events + source_events))
                existing.updated_at = datetime.now()
                db.commit()
                db.refresh(existing)
                logger.info(f"Updated preference for user {user_id}: {preference_key}")
                return True, "偏好已更新", existing
            else:
                # 创建新偏好
                preference = UserPreferenceMemory(
                    user_id=user_id,
                    category=category,
                    subcategory=subcategory,
                    preference_type=preference_type,
                    preference_key=preference_key,
                    preference_value=preference_value,
                    confidence_score=confidence_score,
                    source_events=source_events or [],
                    inference_method=inference_method,
                )
                db.add(preference)
                db.commit()
                db.refresh(preference)
                logger.info(f"Added preference for user {user_id}: {preference_key}")
                return True, "偏好已添加", preference

        except Exception as e:
            logger.error(f"Failed to add preference: {e}")
            return False, str(e), None

    def get_user_preferences(
        self,
        user_id: str,
        category: str = None,
        min_confidence: float = 0.0,
    ) -> List[UserPreferenceMemory]:
        """
        获取用户偏好列表

        Args:
            user_id: 用户 ID
            category: 过滤类别（可选）
            min_confidence: 最小置信度

        Returns:
            偏好列表
        """
        db = self._get_db()
        query = db.query(UserPreferenceMemory).filter(
            UserPreferenceMemory.user_id == user_id,
            UserPreferenceMemory.is_active == True,
            UserPreferenceMemory.confidence_score >= min_confidence,
        )

        if category:
            query = query.filter(UserPreferenceMemory.category == category)

        return query.order_by(
            desc(UserPreferenceMemory.confidence_score),
            desc(UserPreferenceMemory.created_at)
        ).all()

    def get_preference(
        self,
        user_id: str,
        category: str,
        preference_key: str,
    ) -> Optional[UserPreferenceMemory]:
        """获取特定偏好"""
        db = self._get_db()
        return db.query(UserPreferenceMemory).filter(
            UserPreferenceMemory.user_id == user_id,
            UserPreferenceMemory.category == category,
            UserPreferenceMemory.preference_key == preference_key,
            UserPreferenceMemory.is_active == True,
        ).first()

    def remove_preference(
        self,
        user_id: str,
        category: str,
        preference_key: str,
    ) -> Tuple[bool, str]:
        """移除偏好"""
        try:
            db = self._get_db()
            preference = self.get_preference(user_id, category, preference_key)

            if preference:
                preference.is_active = False
                db.commit()
                logger.info(f"Removed preference for user {user_id}: {preference_key}")
                return True, "偏好已移除"
            else:
                return False, "偏好不存在"

        except Exception as e:
            logger.error(f"Failed to remove preference: {e}")
            return False, str(e)

    # ========== 行为模式学习 ==========

    def learn_pattern(
        self,
        user_id: str,
        pattern_type: str,
        pattern_data: Dict,
        pattern_strength: float = 0.5,
        is_validated: bool = False,
        validation_source: str = "implicit",
    ) -> Tuple[bool, str, Optional[BehaviorLearningPattern]]:
        """
        学习行为模式

        Args:
            user_id: 用户 ID
            pattern_type: 模式类型
            pattern_data: 模式数据
            pattern_strength: 模式强度
            is_validated: 是否已验证
            validation_source: 验证来源

        Returns:
            (success, message, pattern)
        """
        try:
            db = self._get_db()

            # 检查是否已存在类似模式
            existing = db.query(BehaviorLearningPattern).filter(
                BehaviorLearningPattern.user_id == user_id,
                BehaviorLearningPattern.pattern_type == pattern_type,
            ).first()

            if existing:
                # 更新现有模式
                existing.pattern_data = {**existing.pattern_data, **pattern_data}
                existing.pattern_strength = max(existing.pattern_strength, pattern_strength)
                existing.observation_count += 1
                existing.last_observed_at = datetime.now()
                existing.is_validated = is_validated or existing.is_validated
                existing.updated_at = datetime.now()
                db.commit()
                db.refresh(existing)
                logger.info(f"Updated pattern for user {user_id}: {pattern_type}")
                return True, "模式已更新", existing
            else:
                # 创建新模式
                pattern = BehaviorLearningPattern(
                    user_id=user_id,
                    pattern_type=pattern_type,
                    pattern_data=pattern_data,
                    pattern_strength=pattern_strength,
                    observation_count=1,
                    last_observed_at=datetime.now(),
                    is_validated=is_validated,
                    validation_source=validation_source,
                )
                db.add(pattern)
                db.commit()
                db.refresh(pattern)
                logger.info(f"Learned pattern for user {user_id}: {pattern_type}")
                return True, "模式已学习", pattern

        except Exception as e:
            logger.error(f"Failed to learn pattern: {e}")
            return False, str(e), None

    def get_user_patterns(
        self,
        user_id: str,
        pattern_type: str = None,
        min_strength: float = 0.0,
        validated_only: bool = False,
    ) -> List[BehaviorLearningPattern]:
        """获取用户行为模式"""
        db = self._get_db()
        query = db.query(BehaviorLearningPattern).filter(
            BehaviorLearningPattern.user_id == user_id,
            BehaviorLearningPattern.pattern_strength >= min_strength,
        )

        if pattern_type:
            query = query.filter(BehaviorLearningPattern.pattern_type == pattern_type)

        if validated_only:
            query = query.filter(BehaviorLearningPattern.is_validated == True)

        return query.order_by(
            desc(BehaviorLearningPattern.pattern_strength),
            desc(BehaviorLearningPattern.observation_count)
        ).all()

    def validate_pattern(
        self,
        user_id: str,
        pattern_type: str,
        validation_source: str = "explicit",
    ) -> Tuple[bool, str]:
        """验证行为模式"""
        try:
            db = self._get_db()
            pattern = db.query(BehaviorLearningPattern).filter(
                BehaviorLearningPattern.user_id == user_id,
                BehaviorLearningPattern.pattern_type == pattern_type,
            ).first()

            if pattern:
                pattern.is_validated = True
                pattern.validation_source = validation_source
                pattern.updated_at = datetime.now()
                db.commit()
                logger.info(f"Validated pattern for user {user_id}: {pattern_type}")
                return True, "模式已验证"
            else:
                return False, "模式不存在"

        except Exception as e:
            logger.error(f"Failed to validate pattern: {e}")
            return False, str(e)

    # ========== 匹配权重调整 ==========

    def adjust_matching_weights(
        self,
        user_id: str,
        before_weights: Dict,
        after_weights: Dict,
        adjustment_reason: str,
        trigger_event_id: str = None,
        trigger_event_type: str = None,
        ai_reasoning: str = None,
        confidence_score: float = 0.5,
    ) -> Tuple[bool, str, Optional[MatchingWeightAdjustment]]:
        """
        调整匹配权重

        Args:
            user_id: 用户 ID
            before_weights: 调整前权重
            after_weights: 调整后权重
            adjustment_reason: 调整原因
            trigger_event_id: 触发事件 ID
            trigger_event_type: 触发事件类型
            ai_reasoning: AI 推理说明
            confidence_score: 置信度

        Returns:
            (success, message, adjustment)
        """
        try:
            db = self._get_db()

            # 计算调整幅度
            adjustment_magnitude = self._calculate_adjustment_magnitude(
                before_weights, after_weights
            )

            adjustment = MatchingWeightAdjustment(
                user_id=user_id,
                before_weights=before_weights,
                after_weights=after_weights,
                adjustment_reason=adjustment_reason,
                adjustment_magnitude=adjustment_magnitude,
                trigger_event_id=trigger_event_id,
                trigger_event_type=trigger_event_type,
                ai_reasoning=ai_reasoning,
                confidence_score=confidence_score,
            )
            db.add(adjustment)
            db.commit()
            db.refresh(adjustment)

            logger.info(
                f"Adjusted matching weights for user {user_id}: "
                f"reason={adjustment_reason}, magnitude={adjustment_magnitude:.2f}"
            )
            return True, "权重已调整", adjustment

        except Exception as e:
            logger.error(f"Failed to adjust weights: {e}")
            return False, str(e), None

    def _calculate_adjustment_magnitude(
        self,
        before: Dict,
        after: Dict,
    ) -> float:
        """计算调整幅度"""
        all_keys = set(before.keys()) | set(after.keys())
        if not all_keys:
            return 0.0

        total_diff = 0.0
        for key in all_keys:
            before_val = before.get(key, 0)
            after_val = after.get(key, 0)
            total_diff += abs(after_val - before_val)

        return total_diff / len(all_keys)

    def get_weight_adjustment_history(
        self,
        user_id: str,
        limit: int = 20,
    ) -> List[MatchingWeightAdjustment]:
        """获取权重调整历史"""
        db = self._get_db()
        return db.query(MatchingWeightAdjustment).filter(
            MatchingWeightAdjustment.user_id == user_id
        ).order_by(
            desc(MatchingWeightAdjustment.created_at)
        ).limit(limit).all()

    def approve_weight_adjustment(
        self,
        adjustment_id: int,
    ) -> Tuple[bool, str]:
        """用户批准权重调整"""
        try:
            db = self._get_db()
            adjustment = db.query(MatchingWeightAdjustment).filter(
                MatchingWeightAdjustment.id == adjustment_id
            ).first()

            if adjustment:
                adjustment.user_feedback = "approved"
                adjustment.user_feedback_at = datetime.now()
                db.commit()
                logger.info(f"Approved weight adjustment {adjustment_id}")
                return True, "已批准"
            else:
                return False, "调整不存在"

        except Exception as e:
            logger.error(f"Failed to approve adjustment: {e}")
            return False, str(e)

    # ========== 用户学习画像 ==========

    def get_or_create_learning_profile(
        self,
        user_id: str,
    ) -> UserLearningProfile:
        """获取或创建学习画像"""
        db = self._get_db()
        profile = db.query(UserLearningProfile).filter(
            UserLearningProfile.user_id == user_id
        ).first()

        if not profile:
            profile = UserLearningProfile(user_id=user_id)
            db.add(profile)
            db.commit()
            db.refresh(profile)

        return profile

    def update_learning_progress(
        self,
        user_id: str,
        progress_delta: int = 0,
        learned_preferences_delta: int = 0,
        validated_patterns_delta: int = 0,
        ai_understanding_delta: float = 0.0,
    ) -> UserLearningProfile:
        """更新学习进度"""
        db = self._get_db()
        profile = self.get_or_create_learning_profile(user_id)

        profile.learning_progress = min(100, max(0, profile.learning_progress + progress_delta))
        profile.learned_preferences_count += learned_preferences_delta
        profile.validated_patterns_count += validated_patterns_delta
        profile.ai_understanding_score = min(
            100, max(0, profile.ai_understanding_score + ai_understanding_delta)
        )
        profile.last_learning_at = datetime.now()

        # 更新学习阶段
        profile.learning_stage = self._calculate_learning_stage(profile)

        db.commit()
        db.refresh(profile)
        return profile

    def _calculate_learning_stage(self, profile: UserLearningProfile) -> str:
        """计算学习阶段"""
        progress = profile.learning_progress

        if progress >= 80:
            return "mastered"
        elif progress >= 60:
            return "personalized"
        elif progress >= 40:
            return "learning"
        elif progress >= 20:
            return "exploring"
        else:
            return "initial"

    def update_preference_summary(
        self,
        user_id: str,
        preference_summary: Dict,
    ) -> UserLearningProfile:
        """更新偏好摘要"""
        db = self._get_db()
        profile = self.get_or_create_learning_profile(user_id)
        profile.preference_summary = preference_summary
        profile.updated_at = datetime.now()
        db.commit()
        db.refresh(profile)
        return profile

    def get_learning_profile(self, user_id: str) -> Optional[UserLearningProfile]:
        """获取学习画像"""
        db = self._get_db()
        return db.query(UserLearningProfile).filter(
            UserLearningProfile.user_id == user_id
        ).first()

    # ========== 学习建议生成 ==========

    def generate_learning_suggestions(
        self,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """
        生成学习建议

        基于当前学习状态，生成改进建议
        """
        profile = self.get_learning_profile(user_id)
        if not profile:
            return []

        suggestions = []

        # 基于学习阶段的建议
        if profile.learning_stage == "initial":
            suggestions.append({
                "type": "stage_hint",
                "message": "开始探索吧！AI 将通过您的行为了解您的偏好",
                "action": "explore",
            })
        elif profile.learning_stage == "exploring":
            suggestions.append({
                "type": "feedback_request",
                "message": "给匹配结果一些反馈，帮助 AI 更好地理解您",
                "action": "provide_feedback",
            })
        elif profile.learning_stage == "learning":
            suggestions.append({
                "type": "validation",
                "message": "AI 已经学习到一些模式，确认一下是否准确？",
                "action": "validate_patterns",
            })

        # 基于 AI 理解度的建议
        if profile.ai_understanding_score < 50:
            suggestions.append({
                "type": "improve_understanding",
                "message": "完善您的资料，让 AI 更了解您",
                "action": "complete_profile",
            })

        return suggestions


# 全局单例
ai_learning_service = AILearningService()
