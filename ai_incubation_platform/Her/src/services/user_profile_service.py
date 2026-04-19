"""
用户画像服务 - 双向动态画像管理

核心职责：
1. SelfProfile 管理：这个人是什么样的（别人匹配你时使用）
2. DesireProfile 管理：这个人想要什么（给你推荐对象时使用）
3. 画像获取、更新、持久化（单一数据源：UserDB）
4. 画像完整度计算

架构优化（v2.0）：
- 单一数据源：所有画像数据存储在 UserDB，无需同步
- UserDB.self_profile_json 存储动态画像（行为推断）
- UserDB.desire_profile_json 存储偏好画像
- 基础信息（age, gender, location 等）直接从 UserDB 字段读取
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json
from collections import OrderedDict

from utils.logger import logger
from utils.db_session_manager import db_session, db_session_readonly
from db.models import UserDB
from services.her_advisor_service import SelfProfile, DesireProfile


# 性能优化：内存缓存配置
PROFILE_CACHE_MAX_SIZE = 500  # 最大缓存条目数


# ============= 事件 → 维度映射 =============

EVENT_TO_SELF_PROFILE_DIMENSION = {
    # 消息行为 → 沟通风格
    "message_sent": "communication_style",
    "response_time": "response_pattern",
    "emoji_usage": "communication_style",
    "message_length": "communication_style",

    # 话题发起 → 权力动态
    "topic_initiation": "power_dynamic",
    "decision_making": "decision_style",

    # 冲突处理 → 决策风格
    "conflict_handling": "decision_style",
    "compromise_behavior": "power_dynamic",

    # 收到的反馈 → 社会反馈维度
    "received_like": "social_feedback",
    "received_dislike": "social_feedback",
    "received_feedback": "social_feedback",
    "chat_initiated": "social_feedback",

    # 情感表达 → 情感需求
    "emotional_expression": "emotional_needs",
    "attachment_behavior": "attachment_style",
}

EVENT_TO_DESIRE_PROFILE_DIMENSION = {
    # 搜索行为 → 搜索偏好
    "search_query": "search_patterns",
    "search_filter_change": "search_patterns",

    # 查看行为 → 点击偏好
    "profile_view": "clicked_types",
    "profile_view_duration": "clicked_types",

    # 滑动行为 → 滑动偏好
    "swipe_like": "swipe_patterns",
    "swipe_pass": "swipe_patterns",
    "swipe_super_like": "swipe_patterns",

    # 匹配反馈 → 偏好反馈
    "match_like": "like_feedback",
    "match_dislike": "dislike_feedback",
    "match_skip": "dislike_feedback",

    # 对话内容 → 实际偏好
    "conversation_topic": "actual_preference",
    "ideal_type_mentioned": "surface_preference",
}


# ============= UserProfileService =============

class UserProfileService:
    """
    用户画像服务

    管理双向动态画像（单一数据源：UserDB）：
    - SelfProfile: 这个用户是什么样的（基础信息 + 行为推断）
    - DesireProfile: 这个用户想要什么

    架构优化（v2.0）：
    - 单一数据源：所有数据存储在 UserDB
    - 基础信息直接从 UserDB 字段读取
    - 动态画像存储在 UserDB.self_profile_json / desire_profile_json
    """

    def __init__(self):
        self._profile_cache: OrderedDict = OrderedDict()

    def _evict_if_needed(self) -> None:
        """LRU 淘汰：超过容量时删除最旧的条目"""
        while len(self._profile_cache) > PROFILE_CACHE_MAX_SIZE:
            oldest_key, _ = self._profile_cache.popitem(last=False)
            logger.debug(f"[UserProfileService] LRU evicted profile: {oldest_key}")

    async def get_or_create_profile(self, user_id: str) -> Tuple[SelfProfile, DesireProfile]:
        """
        获取或创建用户画像

        单一数据源：从 UserDB 读取基础信息 + 动态画像 JSON

        特殊处理：
        - 匿名用户（user-anonymous-dev, anonymous_user 等）：返回默认画像，不查询数据库
        """
        # 特殊处理：匿名用户返回默认画像
        anonymous_user_ids = [
            "user-anonymous-dev",
            "anonymous_user",
            "anonymous",
            "dev-user",
            "guest",
        ]
        if user_id in anonymous_user_ids or user_id.startswith("anonymous"):
            logger.info(f"[UserProfileService] 匿名用户 {user_id}，返回默认画像")
            return SelfProfile(profile_confidence=0.1), DesireProfile(preference_confidence=0.1)

        # 先检查缓存
        if user_id in self._profile_cache:
            self._profile_cache.move_to_end(user_id)
            return self._profile_cache[user_id]

        # 从 UserDB 获取用户（单一数据源）
        user = await self._get_user_from_db(user_id)

        if not user:
            logger.warning(f"[UserProfileService] 用户 {user_id} 不存在")
            return SelfProfile(), DesireProfile()

        # 构建画像：基础信息（UserDB字段）+ 动态画像（JSON）
        self_profile = self._build_self_profile(user)
        desire_profile = self._build_desire_profile(user)

        # 缓存
        self._profile_cache[user_id] = (self_profile, desire_profile)
        self._profile_cache.move_to_end(user_id)
        self._evict_if_needed()

        return self_profile, desire_profile

    async def _get_user_from_db(self, user_id: str) -> Optional[UserDB]:
        """从 UserDB 获取用户"""
        try:
            with db_session_readonly() as db:
                user = db.query(UserDB).filter(UserDB.id == user_id).first()
                return user
        except Exception as e:
            logger.error(f"[UserProfileService] 获取用户失败: {e}")
            return None

    def _build_self_profile(self, user: UserDB) -> SelfProfile:
        """
        构建 SelfProfile

        基础信息：直接从 UserDB 字段读取（单一数据源）
        动态画像：从 self_profile_json 解析
        """
        # 解析动态画像 JSON
        dynamic_data = {}
        if user.self_profile_json:
            try:
                dynamic_data = json.loads(user.self_profile_json)
            except json.JSONDecodeError:
                dynamic_data = {}

        return SelfProfile(
            # 基础信息（来自 UserDB 字段，单一数据源）
            age=user.age or 0,
            gender=user.gender or "",
            location=user.location or "",
            occupation=user.occupation or "",
            education=user.education or "",
            relationship_goal=user.relationship_goal or "",
            interests=json.loads(user.interests) if user.interests else [],
            # 动态画像（来自 JSON，行为推断）
            actual_personality=dynamic_data.get("actual_personality", ""),
            communication_style=dynamic_data.get("communication_style", ""),
            response_pattern=dynamic_data.get("response_pattern", ""),
            power_dynamic=dynamic_data.get("power_dynamic", ""),
            decision_style=dynamic_data.get("decision_style", ""),
            emotional_needs=dynamic_data.get("emotional_needs", []),
            attachment_style=dynamic_data.get("attachment_style", ""),
            reputation_score=dynamic_data.get("reputation_score", 0.5),
            like_rate=dynamic_data.get("like_rate", 0.5),
            # 置信度
            profile_confidence=user.profile_confidence or 0.3,
            dimension_confidences=dynamic_data.get("dimension_confidences", {
                "basic": 1.0,  # 基础属性来自用户填写，置信度高
                "personality": 0.0,
                "communication": 0.0,
                "emotional_needs": 0.0,
            }),
        )

    def _build_desire_profile(self, user: UserDB) -> DesireProfile:
        """
        构建 DesireProfile

        表面偏好：来自 UserDB.ideal_type, deal_breakers 字段
        动态偏好：从 desire_profile_json 解析（行为推断）
        """
        # 解析表面偏好
        ideal_type_data = {}
        if user.ideal_type:
            try:
                ideal_type_data = json.loads(user.ideal_type)
            except json.JSONDecodeError:
                ideal_type_data = {"description": user.ideal_type}

        deal_breakers = []
        if user.deal_breakers:
            try:
                deal_breakers = json.loads(user.deal_breakers)
            except json.JSONDecodeError:
                deal_breakers = []

        # 解析动态偏好 JSON
        dynamic_data = {}
        if user.desire_profile_json:
            try:
                dynamic_data = json.loads(user.desire_profile_json)
            except json.JSONDecodeError:
                dynamic_data = {}

        return DesireProfile(
            # 表面偏好（来自 UserDB 字段）
            surface_preference=ideal_type_data.get("description", ""),
            ideal_type_description=ideal_type_data.get("description", ""),
            deal_breakers=deal_breakers,
            # 动态偏好（来自 JSON，行为推断）
            actual_preference=dynamic_data.get("actual_preference", ""),
            search_patterns=dynamic_data.get("search_patterns", []),
            clicked_types=dynamic_data.get("clicked_types", []),
            swipe_patterns=dynamic_data.get("swipe_patterns", {}),
            like_feedback=dynamic_data.get("like_feedback", []),
            dislike_feedback=dynamic_data.get("dislike_feedback", []),
            # 置信度
            preference_confidence=user.profile_confidence or 0.3,
        )

    async def get_profiles_batch(
        self,
        user_ids: List[str]
    ) -> Dict[str, Tuple[SelfProfile, DesireProfile]]:
        """
        批量获取用户画像（优化 N+1 查询）
        """
        results = {}
        uncached_ids = []

        # 先从缓存获取
        for user_id in user_ids:
            if user_id in self._profile_cache:
                results[user_id] = self._profile_cache[user_id]
            else:
                uncached_ids.append(user_id)

        # 批量查询 UserDB
        if uncached_ids:
            users = await self._get_users_batch_from_db(uncached_ids)

            for user_id in uncached_ids:
                user = users.get(user_id)

                if user:
                    self_profile = self._build_self_profile(user)
                    desire_profile = self._build_desire_profile(user)
                else:
                    self_profile, desire_profile = SelfProfile(), DesireProfile()

                # 缓存
                self._profile_cache[user_id] = (self_profile, desire_profile)
                results[user_id] = (self_profile, desire_profile)

        return results

    async def _get_users_batch_from_db(self, user_ids: List[str]) -> Dict[str, UserDB]:
        """批量从 UserDB 获取用户"""
        if not user_ids:
            return {}

        try:
            with db_session_readonly() as db:
                users = db.query(UserDB).filter(UserDB.id.in_(user_ids)).all()
                return {u.id: u for u in users}
        except Exception as e:
            logger.error(f"[UserProfileService] 批量获取用户失败: {e}")
            return {}

    async def update_self_profile(
        self,
        user_id: str,
        dimension: str,
        new_value: Any,
        source: str,
        confidence: float = 1.0,
    ) -> bool:
        """
        更新 SelfProfile 的某个维度（动态画像部分）

        Args:
            user_id: 用户ID
            dimension: 要更新的维度（仅动态画像维度，如 communication_style）
            new_value: 新值
            source: 更新来源
            confidence: 更新置信度

        Returns:
            是否成功更新

        注意：基础信息（age, gender, location 等）应直接更新 UserDB 字段，
        此方法仅更新动态画像维度（存储在 self_profile_json）

        🔧 [缓存一致性] 更新后同时失效 cache_manager 缓存
        """
        try:
            self_profile, desire_profile = await self.get_or_create_profile(user_id)

            # 更新动态画像维度
            old_value = self._get_self_profile_dimension_value(self_profile, dimension)
            self._set_self_profile_dimension_value(self_profile, dimension, new_value)

            # 更新置信度
            self_profile.dimension_confidences[dimension] = confidence
            self_profile.profile_confidence = self._calculate_overall_confidence(
                self_profile.dimension_confidences
            )

            # 持久化到 UserDB
            await self._save_profile_to_db(user_id, self_profile, desire_profile)

            # 🔧 [缓存一致性] 更新本地缓存 + 失效外部缓存
            self._profile_cache[user_id] = (self_profile, desire_profile)

            # 失效 cache_manager 的用户画像缓存（确保其他模块读取最新数据）
            from cache import cache_manager
            cache_manager.invalidate_profile(user_id)
            # 同时失效匹配结果缓存（画像变更可能导致匹配结果变化）
            cache_manager.invalidate_match_result(user_id)

            logger.info(f"[UserProfileService] 更新用户 {user_id} SelfProfile.{dimension}，缓存已失效")
            return True

        except Exception as e:
            logger.error(f"[UserProfileService] 更新 SelfProfile 失败: {e}")
            return False

    async def update_desire_profile(
        self,
        user_id: str,
        dimension: str,
        new_value: Any,
        source: str,
        confidence: float = 1.0,
    ) -> bool:
        """
        更新 DesireProfile 的某个维度（动态偏好部分）

        Args:
            user_id: 用户ID
            dimension: 要更新的维度（如 actual_preference, search_patterns）
            new_value: 新值
            source: 更新来源
            confidence: 更新置信度

        Returns:
            是否成功更新

        注意：表面偏好（surface_preference, deal_breakers）应直接更新 UserDB 字段，
        此方法仅更新动态偏好维度（存储在 desire_profile_json）

        🔧 [缓存一致性] 更新后同时失效 cache_manager 缓存
        """
        try:
            self_profile, desire_profile = await self.get_or_create_profile(user_id)

            old_value = self._get_desire_profile_dimension_value(desire_profile, dimension)
            self._set_desire_profile_dimension_value(desire_profile, dimension, new_value)

            # 更新置信度
            desire_profile.preference_confidence = confidence

            # 持久化到 UserDB
            await self._save_profile_to_db(user_id, self_profile, desire_profile)

            # 🔧 [缓存一致性] 更新本地缓存 + 失效外部缓存
            self._profile_cache[user_id] = (self_profile, desire_profile)

            # 失效 cache_manager 的用户画像缓存
            from cache import cache_manager
            cache_manager.invalidate_profile(user_id)
            # 同时失效匹配结果缓存（偏好变更可能导致匹配结果变化）
            cache_manager.invalidate_match_result(user_id)

            logger.info(f"[UserProfileService] 更新用户 {user_id} DesireProfile.{dimension}，缓存已失效")
            return True

        except Exception as e:
            logger.error(f"[UserProfileService] 更新 DesireProfile 失败: {e}")
            return False

    def _get_self_profile_dimension_value(
        self,
        profile: SelfProfile,
        dimension: str
    ) -> Any:
        """获取 SelfProfile 维度的当前值"""
        dimension_mapping = {
            "communication_style": profile.communication_style,
            "response_pattern": profile.response_pattern,
            "power_dynamic": profile.power_dynamic,
            "decision_style": profile.decision_style,
            "actual_personality": profile.actual_personality,
            "emotional_needs": profile.emotional_needs,
            "attachment_style": profile.attachment_style,
            "social_feedback": {
                "reputation_score": profile.reputation_score,
                "like_rate": profile.like_rate,
            },
        }
        return dimension_mapping.get(dimension, "")

    def _set_self_profile_dimension_value(
        self,
        profile: SelfProfile,
        dimension: str,
        value: Any
    ) -> None:
        """设置 SelfProfile 维度的值"""
        dimension_mapping = {
            "communication_style": lambda v: setattr(profile, "communication_style", v),
            "response_pattern": lambda v: setattr(profile, "response_pattern", v),
            "power_dynamic": lambda v: setattr(profile, "power_dynamic", v),
            "decision_style": lambda v: setattr(profile, "decision_style", v),
            "actual_personality": lambda v: setattr(profile, "actual_personality", v),
            "emotional_needs": lambda v: setattr(profile, "emotional_needs", v if isinstance(v, list) else [v]),
            "attachment_style": lambda v: setattr(profile, "attachment_style", v),
        }

        if dimension in dimension_mapping:
            dimension_mapping[dimension](value)

        # 社会反馈特殊处理
        if dimension == "social_feedback" and isinstance(value, dict):
            if "reputation_score" in value:
                profile.reputation_score = value["reputation_score"]
            if "like_rate" in value:
                profile.like_rate = value["like_rate"]

    def _get_desire_profile_dimension_value(
        self,
        profile: DesireProfile,
        dimension: str
    ) -> Any:
        """获取 DesireProfile 维度的当前值"""
        dimension_mapping = {
            "surface_preference": profile.surface_preference,
            "actual_preference": profile.actual_preference,
            "search_patterns": profile.search_patterns,
            "clicked_types": profile.clicked_types,
            "swipe_patterns": profile.swipe_patterns,
            "like_feedback": profile.like_feedback,
            "dislike_feedback": profile.dislike_feedback,
        }
        return dimension_mapping.get(dimension, "")

    def _set_desire_profile_dimension_value(
        self,
        profile: DesireProfile,
        dimension: str,
        value: Any
    ) -> None:
        """设置 DesireProfile 维度的值"""
        dimension_mapping = {
            "surface_preference": lambda v: setattr(profile, "surface_preference", v),
            "actual_preference": lambda v: setattr(profile, "actual_preference", v),
            "search_patterns": lambda v: setattr(profile, "search_patterns", v if isinstance(v, list) else [v]),
            "clicked_types": lambda v: setattr(profile, "clicked_types", v if isinstance(v, list) else [v]),
            "swipe_patterns": lambda v: setattr(profile, "swipe_patterns", v if isinstance(v, dict) else {}),
            "like_feedback": lambda v: setattr(profile, "like_feedback", v if isinstance(v, list) else [v]),
            "dislike_feedback": lambda v: setattr(profile, "dislike_feedback", v if isinstance(v, list) else [v]),
        }

        if dimension in dimension_mapping:
            dimension_mapping[dimension](value)

    def _calculate_overall_confidence(
        self,
        dimension_confidences: Dict[str, float]
    ) -> float:
        """计算整体置信度"""
        if not dimension_confidences:
            return 0.0

        # 加权平均：基础属性权重最高
        weights = {
            "basic": 0.4,
            "personality": 0.2,
            "communication": 0.1,
            "emotional_needs": 0.15,
            "power_dynamic": 0.1,
            "social_feedback": 0.05,
        }

        total_confidence = 0.0
        total_weight = 0.0

        for dim, conf in dimension_confidences.items():
            weight = weights.get(dim, 0.1)
            total_confidence += conf * weight
            total_weight += weight

        return total_confidence / total_weight if total_weight > 0 else 0.0

    async def _save_profile_to_db(
        self,
        user_id: str,
        self_profile: SelfProfile,
        desire_profile: DesireProfile,
    ) -> None:
        """
        保存动态画像到 UserDB（单一数据源）

        只保存动态画像部分（self_profile_json, desire_profile_json），
        基础信息（age, gender, location 等）应通过其他接口更新 UserDB 字段
        """
        try:
            with db_session() as db:
                user = db.query(UserDB).filter(UserDB.id == user_id).first()

                if not user:
                    logger.warning(f"[UserProfileService] 用户 {user_id} 不存在，无法保存画像")
                    return

                # 构建动态画像 JSON（不包含基础信息）
                dynamic_self_profile = {
                    "actual_personality": self_profile.actual_personality,
                    "communication_style": self_profile.communication_style,
                    "response_pattern": self_profile.response_pattern,
                    "power_dynamic": self_profile.power_dynamic,
                    "decision_style": self_profile.decision_style,
                    "emotional_needs": self_profile.emotional_needs,
                    "attachment_style": self_profile.attachment_style,
                    "reputation_score": self_profile.reputation_score,
                    "like_rate": self_profile.like_rate,
                    "dimension_confidences": self_profile.dimension_confidences,
                }

                dynamic_desire_profile = {
                    "actual_preference": desire_profile.actual_preference,
                    "search_patterns": desire_profile.search_patterns,
                    "clicked_types": desire_profile.clicked_types,
                    "swipe_patterns": desire_profile.swipe_patterns,
                    "like_feedback": desire_profile.like_feedback,
                    "dislike_feedback": desire_profile.dislike_feedback,
                }

                # 更新 UserDB 的 JSON 字段
                user.self_profile_json = json.dumps(dynamic_self_profile)
                user.desire_profile_json = json.dumps(dynamic_desire_profile)
                user.profile_confidence = self_profile.profile_confidence
                user.profile_completeness = self._calculate_profile_completeness(self_profile, desire_profile)
                user.profile_updated_at = datetime.now()

                db.commit()
                logger.info(f"[UserProfileService] 保存用户 {user_id} 动态画像完成")

        except Exception as e:
            logger.error(f"[UserProfileService] 保存画像失败: {e}")

    def _calculate_profile_completeness(
        self,
        self_profile: SelfProfile,
        desire_profile: DesireProfile
    ) -> float:
        """计算画像完整度"""
        # SelfProfile 动态维度完整度
        self_complete_count = sum([
            1 if self_profile.actual_personality else 0,
            1 if self_profile.communication_style else 0,
            1 if self_profile.emotional_needs else 0,
            1 if self_profile.attachment_style else 0,
            1 if self_profile.power_dynamic else 0,
        ])
        self_score = self_complete_count / 5 * 0.6  # 60%

        # DesireProfile 动态维度完整度
        desire_complete_count = sum([
            1 if desire_profile.actual_preference else 0,
            1 if desire_profile.search_patterns else 0,
            1 if desire_profile.clicked_types else 0,
            1 if desire_profile.like_feedback else 0,
        ])
        desire_score = desire_complete_count / 4 * 0.4  # 40%

        return self_score + desire_score

    def _calculate_self_profile_completeness(self, self_profile: SelfProfile) -> float:
        """计算 SelfProfile 完整度"""
        self_complete_count = sum([
            1 if self_profile.actual_personality else 0,
            1 if self_profile.communication_style else 0,
            1 if self_profile.emotional_needs else 0,
            1 if self_profile.attachment_style else 0,
            1 if self_profile.power_dynamic else 0,
        ])
        return self_complete_count / 5

    def _calculate_desire_profile_completeness(self, desire_profile: DesireProfile) -> float:
        """计算 DesireProfile 完整度"""
        desire_complete_count = sum([
            1 if desire_profile.actual_preference else 0,
            1 if desire_profile.search_patterns else 0,
            1 if desire_profile.clicked_types else 0,
            1 if desire_profile.like_feedback else 0,
        ])
        return desire_complete_count / 4

    def clear_cache(self, user_id: Optional[str] = None) -> None:
        """
        清除缓存

        🔧 [缓存一致性] 同时清除本地缓存和外部 cache_manager 缓存

        Args:
            user_id: 指定用户ID则只清除该用户缓存，否则清除全部
        """
        from cache import cache_manager

        if user_id:
            # 清除本地缓存
            if user_id in self._profile_cache:
                del self._profile_cache[user_id]
            # 清除外部缓存
            cache_manager.invalidate_profile(user_id)
            cache_manager.invalidate_match_result(user_id)
            logger.info(f"[UserProfileService] 清除用户 {user_id} 缓存")
        else:
            # 清除全部本地缓存
            self._profile_cache.clear()
            # 清除全部外部缓存（谨慎操作）
            logger.info("[UserProfileService] 清除全部本地画像缓存（外部缓存由 cache_manager 管理）")


# ============= ProfileUpdateEngine =============

class ProfileUpdateEngine:
    """
    画像更新引擎

    核心职责：
    - 行为事件 → 画像维度更新
    - 对话分析 → DesireProfile 更新
    - 别人反馈 → SelfProfile 更新
    - 持续学习，动态调整
    """

    def __init__(self):
        self._profile_service: Optional[UserProfileService] = None

    def _get_profile_service(self) -> UserProfileService:
        """获取画像服务"""
        if self._profile_service is None:
            self._profile_service = UserProfileService()
        return self._profile_service

    async def process_behavior_event(
        self,
        user_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        target_user_id: Optional[str] = None,
    ) -> bool:
        """
        处理行为事件，更新画像

        Args:
            user_id: 用户ID
            event_type: 事件类型
            event_data: 事件数据
            target_user_id: 目标用户ID（如果有）

        Returns:
            是否成功更新
        """
        logger.info(f"[ProfileUpdateEngine] 处理事件 {event_type} for user {user_id}")

        profile_service = self._get_profile_service()

        # 确定事件影响的画像维度
        self_dimension = EVENT_TO_SELF_PROFILE_DIMENSION.get(event_type)
        desire_dimension = EVENT_TO_DESIRE_PROFILE_DIMENSION.get(event_type)

        updated = False

        # 更新 SelfProfile
        if self_dimension:
            update_value = self._calculate_self_profile_update(
                event_type, event_data, user_id, target_user_id
            )
            if update_value:
                success = await profile_service.update_self_profile(
                    user_id,
                    self_dimension,
                    update_value,
                    source="behavior_event",
                    confidence=self._calculate_event_confidence(event_type, event_data),
                )
                if success:
                    updated = True

        # 更新 DesireProfile
        if desire_dimension:
            update_value = self._calculate_desire_profile_update(
                event_type, event_data, user_id, target_user_id
            )
            if update_value:
                success = await profile_service.update_desire_profile(
                    user_id,
                    desire_dimension,
                    update_value,
                    source="behavior_event",
                    confidence=self._calculate_event_confidence(event_type, event_data),
                )
                if success:
                    updated = True

        return updated

    def _calculate_self_profile_update(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        user_id: str,
        target_user_id: Optional[str],
    ) -> Any:
        """计算 SelfProfile 更新值"""

        # 消息行为 → 沟通风格推断
        if event_type in ["message_sent", "message_length"]:
            return self._infer_communication_style(event_data)

        # 响应时间 → 回复模式
        if event_type == "response_time":
            response_time = event_data.get("response_time_seconds", 0)
            if response_time < 60:
                return "即时回复"
            elif response_time < 3600:
                return "较快回复"
            elif response_time < 86400:
                return "正常回复"
            else:
                return "慢速回复"

        # 表情使用 → 沟通风格
        if event_type == "emoji_usage":
            emoji_count = event_data.get("emoji_count", 0)
            total_messages = event_data.get("total_messages", 1)
            ratio = emoji_count / total_messages
            if ratio > 0.5:
                return "情感表达丰富"
            elif ratio > 0.2:
                return "适度情感表达"
            else:
                return "理性表达"

        # 话题发起 → 权力动态
        if event_type == "topic_initiation":
            is_initiator = event_data.get("is_initiator", False)
            if is_initiator:
                return "主导型"
            else:
                return "跟随型"

        # 收到喜欢 → 社会反馈
        if event_type == "received_like":
            return {"like_rate_increment": 0.01}

        return None

    def _calculate_desire_profile_update(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        user_id: str,
        target_user_id: Optional[str],
    ) -> Any:
        """计算 DesireProfile 更新值"""

        # 搜索查询 → 搜索偏好
        if event_type == "search_query":
            query = event_data.get("query", "")
            filters = event_data.get("filters", {})
            return {
                "query": query,
                "filters": filters,
                "timestamp": datetime.now().isoformat(),
            }

        # 查看资料 → 点击偏好
        if event_type == "profile_view":
            target_type = event_data.get("target_type", "")
            return target_type

        # 滑动喜欢 → 滑动偏好
        if event_type == "swipe_like":
            target_type = event_data.get("target_type", "")
            return {
                "action": "like",
                "target_type": target_type,
                "timestamp": datetime.now().isoformat(),
            }

        # 匹配反馈
        if event_type in ["match_like", "match_dislike"]:
            feedback = {
                "target_id": target_user_id,
                "action": "like" if event_type == "match_like" else "dislike",
                "reason": event_data.get("reason", ""),
                "timestamp": datetime.now().isoformat(),
            }
            return feedback

        return None

    def _infer_communication_style(self, event_data: Dict[str, Any]) -> str:
        """推断沟通风格"""
        message_length = event_data.get("message_length", 0)

        if message_length > 100:
            return "详细表达型"
        elif message_length > 50:
            return "适度表达型"
        elif message_length > 20:
            return "简洁表达型"
        else:
            return "极简表达型"

    def _calculate_event_confidence(
        self,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> float:
        """计算事件对画像推断的置信度"""

        # 高置信度事件（明确信号）
        high_confidence_events = [
            "match_like", "match_dislike",  # 明确反馈
            "swipe_like", "swipe_pass",  # 明确选择
            "received_like", "received_dislike",  # 社会反馈
        ]

        # 中置信度事件
        medium_confidence_events = [
            "profile_view", "search_query",
            "message_sent", "topic_initiation",
        ]

        # 低置信度事件
        low_confidence_events = [
            "response_time", "emoji_usage",  # 需要多次观察
        ]

        if event_type in high_confidence_events:
            return 0.9
        elif event_type in medium_confidence_events:
            return 0.6
        elif event_type in low_confidence_events:
            return 0.3
        else:
            return 0.5

    async def process_conversation_analysis(
        self,
        user_id: str,
        message: str,
        extracted_preference: Dict[str, Any],
    ) -> bool:
        """
        处理对话分析结果，更新 DesireProfile

        Args:
            user_id: 用户ID
            message: 用户消息
            extracted_preference: 从对话中提取的偏好信息

        Returns:
            是否成功更新
        """
        logger.info(f"[ProfileUpdateEngine] 处理对话分析 for user {user_id}")

        profile_service = self._get_profile_service()

        # 更新表面偏好（如果用户明确表达了）
        if extracted_preference.get("stated_preference"):
            await profile_service.update_desire_profile(
                user_id,
                "surface_preference",
                extracted_preference["stated_preference"],
                source="conversation_analysis",
                confidence=extracted_preference.get("stated_confidence", 0.7),
            )

        # 更新实际偏好（Her 推断的）
        if extracted_preference.get("inferred_preference"):
            await profile_service.update_desire_profile(
                user_id,
                "actual_preference",
                extracted_preference["inferred_preference"],
                source="conversation_analysis",
                confidence=extracted_preference.get("inferred_confidence", 0.6),
            )

        return True

    async def batch_process_events(
        self,
        user_id: str,
        events: List[Dict[str, Any]],
    ) -> int:
        """
        批量处理行为事件

        Returns:
            成功更新的事件数量
        """
        updated_count = 0

        for event in events:
            success = await self.process_behavior_event(
                user_id,
                event.get("event_type"),
                event.get("event_data", {}),
                event.get("target_user_id"),
            )
            if success:
                updated_count += 1

        return updated_count


# ============= 全局服务实例 =============

_user_profile_service: Optional[UserProfileService] = None
_profile_update_engine: Optional[ProfileUpdateEngine] = None


def get_user_profile_service() -> UserProfileService:
    """获取用户画像服务单例"""
    global _user_profile_service
    if _user_profile_service is None:
        _user_profile_service = UserProfileService()
        logger.info("UserProfileService initialized")
    return _user_profile_service


def get_profile_update_engine() -> ProfileUpdateEngine:
    """获取画像更新引擎单例"""
    global _profile_update_engine
    if _profile_update_engine is None:
        _profile_update_engine = ProfileUpdateEngine()
        logger.info("ProfileUpdateEngine initialized")
    return _profile_update_engine