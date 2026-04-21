"""
用户双向画像数据结构（与 Her 顾问、用户画像服务共享）。

从 her_advisor_service 拆出，避免 user_profile ↔ her_advisor 仅为类型产生的导入耦合。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SelfProfile:
    """
    自身画像：这个人是什么样的

    用于：别人匹配你时使用
    """

    # 基础属性（主动填写）
    age: int = 0
    gender: str = ""
    location: str = ""
    income_range: Optional[Tuple[int, int]] = None
    occupation: Optional[str] = None
    education: Optional[str] = None
    relationship_goal: str = ""
    interests: List[str] = field(default_factory=list)  # 兴趣爱好

    # 动态画像（行为分析推断）
    actual_personality: str = ""  # 实际性格（基于行为）
    claimed_personality: str = ""  # 自称性格
    personality_gap: str = ""  # 性格认知偏差

    communication_style: str = ""  # 沟通方式
    response_pattern: str = ""  # 回复模式

    emotional_needs: List[str] = field(default_factory=list)  # 情感需求
    attachment_style: str = ""  # 依恋类型

    power_dynamic: str = ""  # 权力倾向
    decision_style: str = ""  # 决策方式

    # 社会反馈
    reputation_score: float = 0.5
    like_rate: float = 0.5
    feedback_summary: str = ""

    # 置信度
    profile_confidence: float = 0.0
    dimension_confidences: Dict[str, float] = field(default_factory=dict)

    # 向量维度化画像（来源：VECTOR_MATCH_SYSTEM_DESIGN.md）
    demographics: Dict[str, Any] = field(default_factory=dict)   # [0-15]
    values_profile: Dict[str, Any] = field(default_factory=dict)  # [16-31]
    big_five_profile: Dict[str, Any] = field(default_factory=dict)  # [32-47]
    attachment_profile: Dict[str, Any] = field(default_factory=dict)  # [48-63]
    growth_profile: Dict[str, Any] = field(default_factory=dict)  # [64-71]
    lifestyle_profile: Dict[str, Any] = field(default_factory=dict)  # [88-103]
    behavior_profile: Dict[str, Any] = field(default_factory=dict)  # [104-119]
    communication_profile: Dict[str, Any] = field(default_factory=dict)  # [120-135]
    implicit_traits: Dict[str, Any] = field(default_factory=dict)  # [136-143]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "basic": {
                "age": self.age,
                "gender": self.gender,
                "location": self.location,
                "income_range": self.income_range,
                "occupation": self.occupation,
                "education": self.education,
                "relationship_goal": self.relationship_goal,
                "interests": self.interests,
            },
            "personality": {
                "actual_personality": self.actual_personality,
                "claimed_personality": self.claimed_personality,
                "personality_gap": self.personality_gap,
            },
            "communication": {
                "style": self.communication_style,
                "response_pattern": self.response_pattern,
            },
            "emotional_needs": {
                "needs_list": self.emotional_needs,
                "attachment_style": self.attachment_style,
            },
            "power_dynamic": {
                "tendency": self.power_dynamic,
                "decision_style": self.decision_style,
            },
            "social_feedback": {
                "reputation_score": self.reputation_score,
                "like_rate": self.like_rate,
                "feedback_summary": self.feedback_summary,
            },
            "confidence": {
                "overall": self.profile_confidence,
                "dimensions": self.dimension_confidences,
            },
            "vector_dimensions": {
                "demographics": self.demographics,
                "values": self.values_profile,
                "big_five": self.big_five_profile,
                "attachment": self.attachment_profile,
                "growth": self.growth_profile,
                "lifestyle": self.lifestyle_profile,
                "behavior": self.behavior_profile,
                "communication": self.communication_profile,
                "implicit": self.implicit_traits,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SelfProfile:
        """从字典创建"""
        basic = data.get("basic", {})
        personality = data.get("personality", {})
        communication = data.get("communication", {})
        emotional = data.get("emotional_needs", {})
        power = data.get("power_dynamic", {})
        social = data.get("social_feedback", {})
        confidence = data.get("confidence", {})
        vector_dimensions = data.get("vector_dimensions", {})

        return cls(
            age=basic.get("age", 0),
            gender=basic.get("gender", ""),
            location=basic.get("location", ""),
            income_range=basic.get("income_range"),
            occupation=basic.get("occupation"),
            education=basic.get("education"),
            relationship_goal=basic.get("relationship_goal", ""),
            interests=basic.get("interests", []),
            actual_personality=personality.get("actual_personality", ""),
            claimed_personality=personality.get("claimed_personality", ""),
            personality_gap=personality.get("personality_gap", ""),
            communication_style=communication.get("style", ""),
            response_pattern=communication.get("response_pattern", ""),
            emotional_needs=emotional.get("needs_list", []),
            attachment_style=emotional.get("attachment_style", ""),
            power_dynamic=power.get("tendency", ""),
            decision_style=power.get("decision_style", ""),
            reputation_score=social.get("reputation_score", 0.5),
            like_rate=social.get("like_rate", 0.5),
            feedback_summary=social.get("feedback_summary", ""),
            profile_confidence=confidence.get("overall", 0.0),
            dimension_confidences=confidence.get("dimensions", {}),
            demographics=vector_dimensions.get("demographics", {}),
            values_profile=vector_dimensions.get("values", {}),
            big_five_profile=vector_dimensions.get("big_five", {}),
            attachment_profile=vector_dimensions.get("attachment", {}),
            growth_profile=vector_dimensions.get("growth", {}),
            lifestyle_profile=vector_dimensions.get("lifestyle", {}),
            behavior_profile=vector_dimensions.get("behavior", {}),
            communication_profile=vector_dimensions.get("communication", {}),
            implicit_traits=vector_dimensions.get("implicit", {}),
        )


@dataclass
class DesireProfile:
    """
    意愿画像：这个人想要什么

    用于：给你推荐对象时使用
    """

    # 表面偏好（用户自称）
    surface_preference: str = ""
    ideal_type_description: str = ""
    deal_breakers: List[str] = field(default_factory=list)

    # 实际偏好（行为推断）
    actual_preference: str = ""

    # 搜索/点击偏好
    search_patterns: List[Dict[str, Any]] = field(default_factory=list)
    clicked_types: List[str] = field(default_factory=list)
    swipe_patterns: Dict[str, Any] = field(default_factory=dict)

    # 匹配反馈
    like_feedback: List[Dict[str, Any]] = field(default_factory=list)
    dislike_feedback: List[Dict[str, Any]] = field(default_factory=list)

    # 偏好差距
    preference_gap: str = ""

    # 置信度
    preference_confidence: float = 0.0

    # 向量维度化偏好画像（来源：VECTOR_MATCH_SYSTEM_DESIGN.md）
    interest_profile: Dict[str, Any] = field(default_factory=dict)  # [72-87]
    value_preferences: Dict[str, Any] = field(default_factory=dict)  # 关键价值观偏好
    communication_preferences: Dict[str, Any] = field(default_factory=dict)  # 沟通偏好
    hard_constraints: Dict[str, Any] = field(default_factory=dict)  # 一票否决/硬约束

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "surface_preference": self.surface_preference,
            "ideal_type_description": self.ideal_type_description,
            "deal_breakers": self.deal_breakers,
            "actual_preference": self.actual_preference,
            "search_patterns": self.search_patterns,
            "clicked_types": self.clicked_types,
            "swipe_patterns": self.swipe_patterns,
            "like_feedback": self.like_feedback,
            "dislike_feedback": self.dislike_feedback,
            "preference_gap": self.preference_gap,
            "confidence": self.preference_confidence,
            "vector_dimensions": {
                "interests": self.interest_profile,
                "value_preferences": self.value_preferences,
                "communication_preferences": self.communication_preferences,
                "hard_constraints": self.hard_constraints,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DesireProfile:
        """从字典创建"""
        vector_dimensions = data.get("vector_dimensions", {})
        return cls(
            surface_preference=data.get("surface_preference", ""),
            ideal_type_description=data.get("ideal_type_description", ""),
            deal_breakers=data.get("deal_breakers", []),
            actual_preference=data.get("actual_preference", ""),
            search_patterns=data.get("search_patterns", []),
            clicked_types=data.get("clicked_types", []),
            swipe_patterns=data.get("swipe_patterns", {}),
            like_feedback=data.get("like_feedback", []),
            dislike_feedback=data.get("dislike_feedback", []),
            preference_gap=data.get("preference_gap", ""),
            preference_confidence=data.get("confidence", 0.0),
            interest_profile=vector_dimensions.get("interests", {}),
            value_preferences=vector_dimensions.get("value_preferences", {}),
            communication_preferences=vector_dimensions.get("communication_preferences", {}),
            hard_constraints=vector_dimensions.get("hard_constraints", {}),
        )
