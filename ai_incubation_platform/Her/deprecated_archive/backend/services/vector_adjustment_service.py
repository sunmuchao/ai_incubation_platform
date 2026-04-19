"""
向量调整服务 - 反馈学习向量化

@deprecated
此服务已废弃，原因：
1. 只被 quick_start_service 引用，后者本身也是废弃服务
2. 形成逻辑孤岛链：vector_adjustment_service → quick_start_service → 无入口
3. 功能已被 DeerFlow her_tools 替代

替代方案：
- DeerFlow Agent 通过 her_feedback_learning_tool 处理反馈学习
- 向量调整逻辑整合到匹配算法中

归档日期：2026-04-15
预计删除：确认无影响后删除

---

核心功能：
- 将反馈学习结果映射到向量维度
- 渐进式向量更新
- 置信度管理
- 冷启动到精准匹配的过渡

设计参考：docs/PROGRESSIVE_SMART_MATCHING_SYSTEM.md
"""
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
import numpy as np

from sqlalchemy.orm import Session
from services.base_service import BaseService
from db.models import UserDB, UserFeedbackLearningDB, UserVectorProfileDB, ImplicitInferenceDB
from utils.logger import logger
from utils.db_session_manager import db_session


# ==================== 维度映射 ====================

# 反馈原因 -> 向量维度索引映射
FEEDBACK_TO_VECTOR_MAPPING = {
    "age_not_match": {
        "primary_dims": [1, 2],  # v1: 年龄偏好下限, v2: 年龄偏好上限
        "secondary_dims": [0],    # v0: 年龄归一化
        "adjustment_strategy": "adjust_age_range",
        "description": "年龄偏好调整"
    },
    "location_far": {
        "primary_dims": [7],      # v7: 是否接受异地
        "secondary_dims": [6],    # v6: 城市层级
        "adjustment_strategy": "tighten_location",
        "description": "地域偏好收紧"
    },
    "not_my_type": {
        "primary_dims": [32, 33, 34, 35],  # 大五人格：开放性
        "secondary_dims": [40, 41, 42, 43],  # 外向性
        "adjustment_strategy": "infer_personality_preference",
        "description": "性格偏好推断"
    },
    "photo_concern": {
        "primary_dims": [137],    # v137: 实际偏好的性格类型（隐性）
        "adjustment_strategy": "infer_visual_preference",
        "description": "视觉偏好推断"
    },
    "bio_issue": {
        "primary_dims": [136],    # v136: 声明偏好 vs 实际行为差异度
        "adjustment_strategy": "infer_content_preference",
        "description": "内容偏好推断"
    },
}

# 隐性行为信号 -> 向量维度映射
BEHAVIOR_TO_VECTOR_MAPPING = {
    "browse_duration": {
        "target_dim": 139,        # v139: 决策风格
        "long_signal_value": 0.8, # 深思熟虑型
        "short_signal_value": 0.3, # 快速判断型
        "confidence_weight": 0.6
    },
    "photo_view_count": {
        "target_dim": 137,        # v137: 视觉偏好
        "high_signal_value": 0.8, # 高视觉偏好
        "low_signal_value": 0.3,  # 低视觉偏好
        "confidence_weight": 0.7
    },
    "bio_read_duration": {
        "target_dim": 136,        # v136: 内容偏好
        "long_signal_value": 0.8, # 重视内容
        "short_signal_value": 0.4, # 快速筛选
        "confidence_weight": 0.5
    },
    "emoji_warm_ratio": {
        "target_dim": 138,        # v138: 性格偏好
        "high_signal_value": "gentle", # 偏好温和型
        "low_signal_value": "playful",  # 偏好活泼型
        "confidence_weight": 0.5
    },
    "scroll_speed": {
        "target_dim": 139,        # v139: 决策风格（补充）
        "fast_signal_value": 0.7, # 果断型
        "slow_signal_value": 0.4, # 犹豫型
        "confidence_weight": 0.4
    },
}


# ==================== 数据结构 ====================

@dataclass
class VectorAdjustment:
    """向量调整结果"""
    dimension_index: int
    old_value: float
    new_value: float
    adjustment_reason: str
    confidence: float
    source: str  # feedback, behavior_inference, etc.


@dataclass
class LearningResult:
    """学习结果"""
    adjustments: List[VectorAdjustment]
    vector_before: np.ndarray
    vector_after: np.ndarray
    completeness_before: float
    completeness_after: float
    learned_dimensions: List[str]


# ==================== 向量调整服务 ====================

class VectorAdjustmentService(BaseService[UserVectorProfileDB]):
    """
    向量调整服务

    核心能力：
    - 将反馈学习映射到向量维度
    - 渐进式向量更新
    - 置信度管理
    - 向量完整度跟踪
    """

    def __init__(self, db: Session = None):
        super().__init__(db, UserVectorProfileDB)

    async def apply_feedback_adjustment(
        self,
        user_id: str,
        feedback_type: str,
        reason: str,
        target_profile: Dict,
        current_vector: Optional[np.ndarray] = None
    ) -> LearningResult:
        """
        应用反馈学习到向量

        Args:
            user_id: 用户ID
            feedback_type: like/dislike/skip
            reason: 反馈原因（dislike时）
            target_profile: 被反馈对象的画像
            current_vector: 当前向量（可选，会自动获取）

        Returns:
            LearningResult: 学习结果
        """
        self.log_info(f"VectorAdjustment: Applying feedback for user={user_id}, type={feedback_type}")

        # 1. 获取当前向量
        if current_vector is None:
            current_vector = await self._get_user_vector(user_id)

        if current_vector is None:
            # 创建基础向量
            current_vector = np.zeros(144)

        vector_before = current_vector.copy()
        adjustments = []

        # 2. 根据反馈类型调整
        if feedback_type == "like":
            adjustments = self._apply_like_adjustment(current_vector, target_profile)
        elif feedback_type == "dislike":
            adjustments = self._apply_dislike_adjustment(current_vector, reason, target_profile)

        # 3. 应用调整
        for adj in adjustments:
            current_vector[adj.dimension_index] = adj.new_value

        # 4. 计算完整度变化
        completeness_before = self._calculate_completeness(vector_before)
        completeness_after = self._calculate_completeness(current_vector)

        # 5. 持久化更新
        await self._save_vector_update(user_id, current_vector, adjustments)

        return LearningResult(
            adjustments=adjustments,
            vector_before=vector_before,
            vector_after=current_vector,
            completeness_before=completeness_before,
            completeness_after=completeness_after,
            learned_dimensions=[adj.adjustment_reason for adj in adjustments]
        )

    def _apply_like_adjustment(
        self,
        vector: np.ndarray,
        liked_profile: Dict
    ) -> List[VectorAdjustment]:
        """应用喜欢反馈的向量调整"""

        adjustments = []

        # 喜欢某个年龄的人 → 强化年龄偏好
        liked_age = liked_profile.get("age")
        if liked_age:
            # v1: 年龄偏好下限
            old_v1 = vector[1]
            new_v1 = min(old_v1, liked_age / 100 - 0.05) if old_v1 > 0 else liked_age / 100 - 0.05
            if abs(new_v1 - old_v1) > 0.01:
                adjustments.append(VectorAdjustment(
                    dimension_index=1,
                    old_value=old_v1,
                    new_value=new_v1,
                    adjustment_reason="age_preference_lower",
                    confidence=0.7,
                    source="like_feedback"
                ))

            # v2: 年龄偏好上限
            old_v2 = vector[2]
            new_v2 = max(old_v2, liked_age / 100 + 0.05) if old_v2 > 0 else liked_age / 100 + 0.05
            if abs(new_v2 - old_v2) > 0.01:
                adjustments.append(VectorAdjustment(
                    dimension_index=2,
                    old_value=old_v2,
                    new_value=new_v2,
                    adjustment_reason="age_preference_upper",
                    confidence=0.7,
                    source="like_feedback"
                ))

        # 喜欢同城的人 → 强化地域偏好
        liked_location = liked_profile.get("location")
        if liked_location:
            # v6: 城市层级（保持当前值）
            # v7: 是否接受异地（强化同城偏好）
            old_v7 = vector[7]
            new_v7 = max(0.0, old_v7 - 0.1)  # 降低异地接受度
            if abs(new_v7 - old_v7) > 0.05:
                adjustments.append(VectorAdjustment(
                    dimension_index=7,
                    old_value=old_v7,
                    new_value=new_v7,
                    adjustment_reason="location_preference_tighten",
                    confidence=0.6,
                    source="like_feedback"
                ))

        return adjustments

    def _apply_dislike_adjustment(
        self,
        vector: np.ndarray,
        reason: str,
        disliked_profile: Dict
    ) -> List[VectorAdjustment]:
        """应用不喜欢反馈的向量调整"""

        adjustments = []

        mapping = FEEDBACK_TO_VECTOR_MAPPING.get(reason)
        if not mapping:
            return adjustments

        strategy = mapping["adjustment_strategy"]

        if strategy == "adjust_age_range":
            # 不喜欢某个年龄的人 → 调整年龄偏好范围
            disliked_age = disliked_profile.get("age")
            if disliked_age:
                # 根据被拒绝年龄调整偏好范围（排除该年龄附近）
                current_age_center = vector[0] * 100  # 用户自己年龄

                if disliked_age > current_age_center + 3:
                    # 拒绝了比自己大的人 → 调低上限
                    old_v2 = vector[2]
                    new_v2 = min(old_v2, disliked_age / 100 - 0.03)
                    adjustments.append(VectorAdjustment(
                        dimension_index=2,
                        old_value=old_v2,
                        new_value=new_v2,
                        adjustment_reason="age_preference_upper_reduce",
                        confidence=0.8,
                        source="dislike_feedback"
                    ))
                elif disliked_age < current_age_center - 3:
                    # 拒绝了比自己小的人 → 调高下限
                    old_v1 = vector[1]
                    new_v1 = max(old_v1, disliked_age / 100 + 0.03)
                    adjustments.append(VectorAdjustment(
                        dimension_index=1,
                        old_value=old_v1,
                        new_value=new_v1,
                        adjustment_reason="age_preference_lower_raise",
                        confidence=0.8,
                        source="dislike_feedback"
                    ))

        elif strategy == "tighten_location":
            # 不喜欢异地的人 → 强化同城偏好
            old_v7 = vector[7]
            new_v7 = max(0.0, old_v7 - 0.2)  # 大幅降低异地接受度
            adjustments.append(VectorAdjustment(
                dimension_index=7,
                old_value=old_v7,
                new_value=new_v7,
                adjustment_reason="location_preference_strict",
                confidence=0.9,
                source="dislike_feedback"
            ))

        elif strategy == "infer_personality_preference":
            # 不喜欢某类型 → 推断性格偏好
            # 写入隐性特征维度
            old_v138 = vector[138]
            # 简化处理：标记为"需要更多数据"
            new_v138 = 0.5  # 中等置信度
            adjustments.append(VectorAdjustment(
                dimension_index=138,
                old_value=old_v138,
                new_value=new_v138,
                adjustment_reason="personality_preference_inferred",
                confidence=0.5,
                source="dislike_feedback"
            ))

        elif strategy == "infer_visual_preference":
            # 照片让我犹豫 → 视觉偏好推断
            old_v137 = vector[137]
            # 可能偏好更真实自然的照片
            new_v137 = min(1.0, old_v137 + 0.1)
            adjustments.append(VectorAdjustment(
                dimension_index=137,
                old_value=old_v137,
                new_value=new_v137,
                adjustment_reason="visual_preference_natural",
                confidence=0.6,
                source="dislike_feedback"
            ))

        elif strategy == "infer_content_preference":
            # 简介不吸引 → 内容偏好推断
            old_v136 = vector[136]
            new_v136 = min(1.0, old_v136 + 0.1)
            adjustments.append(VectorAdjustment(
                dimension_index=136,
                old_value=old_v136,
                new_value=new_v136,
                adjustment_reason="content_preference_depth",
                confidence=0.5,
                source="dislike_feedback"
            ))

        return adjustments

    async def apply_behavior_inference(
        self,
        user_id: str,
        behavior_signals: Dict[str, float]
    ) -> LearningResult:
        """
        应用行为推断到向量

        Args:
            user_id: 用户ID
            behavior_signals: 行为信号字典，如 {
                "browse_duration": 12.5,  # 平均浏览时长（秒）
                "photo_view_count": 3.5,  # 平均照片查看次数
                "bio_read_duration": 8.0,  # 平均简介阅读时长（秒）
                "emoji_warm_ratio": 0.68,  # 温暖表情使用比例
                "scroll_speed": 2.5,       # 平均滑动速度
            }

        Returns:
            LearningResult: 学习结果
        """
        self.log_info(f"VectorAdjustment: Applying behavior inference for user={user_id}")

        current_vector = await self._get_user_vector(user_id)
        if current_vector is None:
            current_vector = np.zeros(144)

        vector_before = current_vector.copy()
        adjustments = []

        # 处理每个行为信号
        for signal_name, signal_value in behavior_signals.items():
            mapping = BEHAVIOR_TO_VECTOR_MAPPING.get(signal_name)
            if not mapping:
                continue

            target_dim = mapping["target_dim"]
            confidence_weight = mapping["confidence_weight"]

            # 根据信号值确定新向量值
            if signal_name == "browse_duration":
                if signal_value > 10:  # 长浏览
                    new_value = mapping["long_signal_value"]
                    reason = "decision_style_thoughtful"
                else:
                    new_value = mapping["short_signal_value"]
                    reason = "decision_style_quick"
                adjustments.append(VectorAdjustment(
                    dimension_index=target_dim,
                    old_value=vector_before[target_dim],
                    new_value=new_value,
                    adjustment_reason=reason,
                    confidence=confidence_weight,
                    source="behavior_inference"
                ))

            elif signal_name == "photo_view_count":
                if signal_value > 3:  # 高照片查看
                    new_value = mapping["high_signal_value"]
                    reason = "visual_preference_high"
                else:
                    new_value = mapping["low_signal_value"]
                    reason = "visual_preference_low"
                adjustments.append(VectorAdjustment(
                    dimension_index=target_dim,
                    old_value=vector_before[target_dim],
                    new_value=new_value,
                    adjustment_reason=reason,
                    confidence=confidence_weight,
                    source="behavior_inference"
                ))

            elif signal_name == "bio_read_duration":
                if signal_value > 5:  # 长简介阅读
                    new_value = mapping["long_signal_value"]
                    reason = "content_preference_high"
                else:
                    new_value = mapping["short_signal_value"]
                    reason = "content_preference_low"
                adjustments.append(VectorAdjustment(
                    dimension_index=target_dim,
                    old_value=vector_before[target_dim],
                    new_value=new_value,
                    adjustment_reason=reason,
                    confidence=confidence_weight,
                    source="behavior_inference"
                ))

            elif signal_name == "emoji_warm_ratio":
                # 需要特殊处理：字符串类型偏好
                if signal_value > 0.6:
                    new_value = 0.8  # 编码为温和型
                    reason = "personality_preference_gentle"
                else:
                    new_value = 0.4  # 编码为活泼型
                    reason = "personality_preference_playful"
                adjustments.append(VectorAdjustment(
                    dimension_index=target_dim,
                    old_value=vector_before[target_dim],
                    new_value=new_value,
                    adjustment_reason=reason,
                    confidence=confidence_weight,
                    source="behavior_inference"
                ))

        # 应用调整
        for adj in adjustments:
            current_vector[adj.dimension_index] = adj.new_value

        # 计算完整度
        completeness_before = self._calculate_completeness(vector_before)
        completeness_after = self._calculate_completeness(current_vector)

        # 持久化
        await self._save_vector_update(user_id, current_vector, adjustments)

        # 保存隐性推断记录
        await self._save_implicit_inferences(user_id, adjustments)

        return LearningResult(
            adjustments=adjustments,
            vector_before=vector_before,
            vector_after=current_vector,
            completeness_before=completeness_before,
            completeness_after=completeness_after,
            learned_dimensions=[adj.adjustment_reason for adj in adjustments]
        )

    def _calculate_completeness(self, vector: np.ndarray) -> float:
        """计算向量完整度"""

        # 检查各分类的填充情况
        category_ranges = {
            "demographics": (0, 16),
            "values": (16, 32),
            "personality": (32, 48),
            "attachment": (48, 64),
            "growth": (64, 72),
            "interests": (72, 88),
            "lifestyle": (88, 104),
            "behavior": (104, 120),
            "communication": (120, 136),
            "implicit": (136, 144),
        }

        filled_count = 0
        total_count = 144

        for start, end in category_ranges.values():
            # 非零值视为已填充
            filled_in_range = np.count_nonzero(vector[start:end])
            filled_count += filled_in_range

        return filled_count / total_count

    async def _get_user_vector(self, user_id: str) -> Optional[np.ndarray]:
        """获取用户向量"""

        with db_session() as db:
            profile = db.query(UserVectorProfileDB).filter(
                UserVectorProfileDB.user_id == user_id
            ).first()

            if profile and profile.vector:
                try:
                    return np.array(json.loads(profile.vector))
                except:
                    return None

            return None

    async def _save_vector_update(
        self,
        user_id: str,
        vector: np.ndarray,
        adjustments: List[VectorAdjustment]
    ) -> None:
        """保存向量更新"""

        with db_session() as db:
            profile = db.query(UserVectorProfileDB).filter(
                UserVectorProfileDB.user_id == user_id
            ).first()

            completeness = self._calculate_completeness(vector)

            if profile:
                profile.vector = json.dumps(vector.tolist())
                profile.completeness_ratio = completeness
                profile.updated_at = datetime.now()
            else:
                # 确定推荐策略
                if completeness < 0.2:
                    strategy = "cold_start"
                elif completeness < 0.5:
                    strategy = "basic"
                elif completeness < 0.8:
                    strategy = "vector"
                else:
                    strategy = "precise"

                profile = UserVectorProfileDB(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    vector=json.dumps(vector.tolist()),
                    completeness_ratio=completeness,
                    recommended_strategy=strategy
                )
                db.add(profile)

            db.commit()

    async def _save_implicit_inferences(
        self,
        user_id: str,
        adjustments: List[VectorAdjustment]
    ) -> None:
        """保存隐性推断记录"""

        with db_session() as db:
            for adj in adjustments:
                if adj.source == "behavior_inference":
                    record = ImplicitInferenceDB(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        inference_source=adj.adjustment_reason,
                        inferred_dimension=str(adj.dimension_index),
                        inferred_value={"value": adj.new_value},
                        confidence=adj.confidence,
                        vector_dim_index=adj.dimension_index,
                        inferred_at=datetime.now()
                    )
                    db.add(record)

            db.commit()

    def get_strategy_for_completeness(self, completeness: float) -> str:
        """根据完整度获取推荐策略"""

        if completeness < 0.2:
            return "cold_start"
        elif completeness < 0.5:
            return "basic"
        elif completeness < 0.8:
            return "vector"
        else:
            return "precise"


# ==================== 行为信号收集服务 ====================

class BehaviorSignalCollector:
    """
    行为信号收集器

    从用户行为事件中提取统计信号
    """

    def collect_signals(self, behavior_events: List[Dict]) -> Dict[str, float]:
        """
        从行为事件收集统计信号

        Args:
            behavior_events: 行为事件列表，如 [
                {"event_type": "profile_view", "duration_seconds": 12, "photo_views": 3, "bio_duration": 8},
                {"event_type": "profile_view", "duration_seconds": 15, "photo_views": 4, "bio_duration": 10},
                ...
            ]

        Returns:
            统计信号字典
        """
        if not behavior_events:
            return {}

        # 筛选 profile_view 事件
        profile_views = [e for e in behavior_events if e.get("event_type") == "profile_view"]

        if not profile_views:
            return {}

        signals = {}

        # 计算平均浏览时长
        durations = [e.get("duration_seconds", 0) for e in profile_views]
        signals["browse_duration"] = np.mean(durations) if durations else 5.0

        # 计算平均照片查看次数
        photo_views = [e.get("photo_view_count", 0) for e in profile_views]
        signals["photo_view_count"] = np.mean(photo_views) if photo_views else 1.0

        # 计算平均简介阅读时长
        bio_durations = [e.get("bio_read_duration", 0) for e in profile_views]
        signals["bio_read_duration"] = np.mean(bio_durations) if bio_durations else 2.0

        # 计算表情使用比例（从聊天事件）
        chat_events = [e for e in behavior_events if e.get("event_type") == "chat_message"]
        if chat_events:
            warm_emojis = ["😊", "😄", "🥰", "💕", "❤️"]
            warm_count = 0
            total_emojis = 0

            for e in chat_events:
                emojis = e.get("emojis_used", [])
                total_emojis += len(emojis)
                warm_count += sum(1 for emoji in emojis if emoji in warm_emojis)

            signals["emoji_warm_ratio"] = warm_count / total_emojis if total_emojis > 0 else 0.5
        else:
            signals["emoji_warm_ratio"] = 0.5

        # 计算滑动速度（从 swipe 事件）
        swipe_events = [e for e in behavior_events if e.get("event_type") == "swipe_action"]
        if swipe_events:
            times = [e.get("decision_time_seconds", 2) for e in swipe_events]
            signals["scroll_speed"] = np.mean(times) if times else 2.5
        else:
            signals["scroll_speed"] = 2.5

        return signals


# ==================== 全局单例 ====================

_vector_adjustment_service: Optional[VectorAdjustmentService] = None
_behavior_signal_collector: Optional[BehaviorSignalCollector] = None


def get_vector_adjustment_service() -> VectorAdjustmentService:
    """获取向量调整服务实例"""
    global _vector_adjustment_service
    if _vector_adjustment_service is None:
        _vector_adjustment_service = VectorAdjustmentService()
    return _vector_adjustment_service


def get_behavior_signal_collector() -> BehaviorSignalCollector:
    """获取行为信号收集器实例"""
    global _behavior_signal_collector
    if _behavior_signal_collector is None:
        _behavior_signal_collector = BehaviorSignalCollector()
    return _behavior_signal_collector


# 导入 uuid
import uuid