"""
AI 画像推断器 - 渐进式智能收集架构核心组件

功能：
1. 从对话中推断用户画像维度
2. 从行为中推断隐性偏好
3. 从第三方数据中补充画像
4. 管理推断置信度和来源追溯
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json

from models.profile_vector_models import (
    UserVectorProfile,
    DimensionValue,
    ProfileInferenceResult,
    ThirdPartyDataInference,
    DataSource,
    DimensionCategory,
    DIMENSION_DEFINITIONS,
)
from utils.logger import logger


class AIProfileInferencer:
    """
    AI Native 用户画像推断器

    核心理念：
    - 用户不需要"填写"信息
    - AI从自然对话中"推断"信息
    - 推断结果通过行为验证
    - 渐进式提升画像完整度
    """

    # 从对话中可推断的维度配置
    INFERRABLE_FROM_CHAT = {
        # 沟通风格维度 [120-135] - 直接从聊天内容推断
        "communication_style": {
            "dimensions": list(range(120, 136)),
            "min_messages": 20,
            "confidence_base": 0.7,
        },
        # 大五人格 - 从语言风格推断
        "personality": {
            "dimensions": list(range(32, 48)),
            "min_messages": 50,
            "confidence_base": 0.6,
        },
        # 价值观 - 从话题偏好推断
        "values": {
            "dimensions": list(range(16, 32)),
            "min_messages": 30,
            "confidence_base": 0.5,
        },
        # 依恋类型 - 从情感表达推断
        "attachment": {
            "dimensions": list(range(48, 64)),
            "min_messages": 100,
            "confidence_base": 0.5,
        },
        # 兴趣爱好 - 从话题推断
        "interests": {
            "dimensions": list(range(72, 88)),
            "min_messages": 10,
            "confidence_base": 0.8,
        },
        # 生活方式 - 从对话推断
        "lifestyle": {
            "dimensions": list(range(88, 104)),
            "min_messages": 30,
            "confidence_base": 0.6,
        },
    }

    # 从行为中可推断的维度
    INFERRABLE_FROM_BEHAVIOR = {
        # 行为模式 [104-119]
        "behavior_pattern": {
            "dimensions": list(range(104, 120)),
            "min_interactions": 50,
            "confidence_base": 0.7,
        },
        # 隐性特征 [136-143]
        "implicit_preferences": {
            "dimensions": list(range(136, 144)),
            "min_swipes": 100,
            "confidence_base": 0.5,
        },
    }

    def __init__(self, llm_service=None):
        """
        初始化推断器

        Args:
            llm_service: LLM 服务实例
        """
        self.llm_service = llm_service
        self._profile_cache: Dict[str, UserVectorProfile] = {}

    async def infer_from_conversation(
        self,
        user_id: str,
        messages: List[Dict[str, Any]],
        existing_profile: Optional[UserVectorProfile] = None
    ) -> ProfileInferenceResult:
        """
        从对话中推断用户画像

        Args:
            user_id: 用户ID
            messages: 对话消息列表 [{"role": "user/assistant", "content": "..."}]
            existing_profile: 已有的画像（用于增量更新）

        Returns:
            推断结果
        """
        logger.info(f"AIProfileInferencer: Inferring profile from {len(messages)} messages for user {user_id}")

        # 提取用户消息
        user_messages = [
            msg for msg in messages
            if msg.get("role") == "user"
        ]

        if not user_messages:
            return ProfileInferenceResult(
                user_id=user_id,
                inference_source=DataSource.CHAT_INFERENCE,
                inference_method="no_user_messages",
                overall_confidence=0.0,
                sample_size=0
            )

        # 获取或创建画像
        profile = existing_profile or UserVectorProfile(user_id=user_id)

        # 如果消息数量不足 LLM 分析，使用关键词推断
        if len(user_messages) < 10:
            logger.debug(f"AIProfileInferencer: Using keyword inference for {len(user_messages)} messages")
            return self._fallback_analysis(user_messages, profile)

        # 调用 LLM 进行分析
        inference_result = await self._llm_analyze_conversation(
            user_messages=user_messages,
            profile=profile
        )

        # 更新画像
        for dim_index, dim_value in inference_result.inferred_dimensions.items():
            profile.set_dimension(
                index=dim_index,
                value=dim_value.value,
                confidence=dim_value.confidence,
                source=DataSource.CHAT_INFERENCE,
                evidence=dim_value.evidence
            )

        # 计算完整度
        profile.calculate_completeness()

        # 缓存
        self._profile_cache[user_id] = profile

        return inference_result

    async def _llm_analyze_conversation(
        self,
        user_messages: List[Dict[str, Any]],
        profile: UserVectorProfile
    ) -> ProfileInferenceResult:
        """
        使用 LLM 分析对话内容，推断用户画像

        Args:
            user_messages: 用户消息列表
            profile: 当前画像

        Returns:
            推断结果
        """
        # 构建分析 prompt
        messages_text = "\n".join([
            f"用户: {msg.get('content', '')[:200]}"
            for msg in user_messages[-50:]  # 最近50条
        ])

        prompt = f'''你是一位专业的心理学家和婚恋顾问，请分析以下对话内容，推断用户的性格特点、价值观倾向、沟通风格等。

对话内容：
{messages_text}

请返回 JSON 格式的推断结果（只返回 JSON，不要其他内容）：
{{
    "personality": {{
        "openness": 0.0-1.0,
        "conscientiousness": 0.0-1.0,
        "extraversion": 0.0-1.0,
        "agreeableness": 0.0-1.0,
        "neuroticism": 0.0-1.0,
        "confidence": 0.0-1.0
    }},
    "communication_style": {{
        "formality": 0.0-1.0,
        "humor": 0.0-1.0,
        "directness": 0.0-1.0,
        "conflict_style": "proactive/passive/avoidant",
        "cold_war_tendency": 0.0-1.0,
        "repair_willingness": 0.0-1.0,
        "confidence": 0.0-1.0
    }},
    "values_hints": {{
        "family_oriented": true/false,
        "career_oriented": true/false,
        "want_children": true/false/null,
        "spending_style": "thrifty/balanced/spendthrift",
        "confidence": 0.0-1.0
    }},
    "attachment_hints": {{
        "secure": 0.0-1.0,
        "anxious": 0.0-1.0,
        "avoidant": 0.0-1.0,
        "confidence": 0.0-1.0
    }},
    "interests": ["推断的兴趣1", "推断的兴趣2", ...],
    "lifestyle": {{
        "social_preference": "introvert/ambivert/extrovert",
        "routine_preference": "planned/flexible/spontaneous",
        "confidence": 0.0-1.0
    }},
    "analysis_notes": "简要分析说明"
}}
'''

        try:
            # 调用 LLM
            from services.llm_semantic_service import get_llm_semantic_service, call_llm_sync

            llm_service = get_llm_semantic_service()
            if not llm_service.enabled:
                return self._fallback_analysis(user_messages, profile)

            response = call_llm_sync(prompt, timeout=30)

            if not response or response.startswith('{"fallback"'):
                return self._fallback_analysis(user_messages, profile)

            # 解析结果
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()

            data = json.loads(response)

            # 转换为维度值
            inferred_dimensions: Dict[int, DimensionValue] = {}

            # 大五人格 [32-47]
            if "personality" in data:
                p = data["personality"]
                personality_mapping = [
                    ("openness", 32),
                    ("conscientiousness", 33),
                    ("extraversion", 34),
                    ("agreeableness", 35),
                    ("neuroticism", 36),
                ]
                base_conf = p.get("confidence", 0.6)
                for key, idx in personality_mapping:
                    if key in p:
                        inferred_dimensions[idx] = DimensionValue(
                            value=float(p[key]),
                            confidence=base_conf,
                            source=DataSource.CHAT_INFERENCE,
                            inferred_at=datetime.now(),
                            evidence=f"从对话推断: {key}"
                        )

            # 沟通风格 [120-135]
            if "communication_style" in data:
                c = data["communication_style"]
                comm_mapping = [
                    ("formality", 120),
                    ("humor", 121),
                    ("directness", 122),
                    ("cold_war_tendency", 133),
                    ("repair_willingness", 134),
                ]
                base_conf = c.get("confidence", 0.7)
                for key, idx in comm_mapping:
                    if key in c:
                        value = c[key]
                        if isinstance(value, str):
                            value = {"proactive": 0.8, "passive": 0.4, "avoidant": 0.2}.get(value, 0.5)
                        inferred_dimensions[idx] = DimensionValue(
                            value=float(value),
                            confidence=base_conf,
                            source=DataSource.CHAT_INFERENCE,
                            inferred_at=datetime.now(),
                            evidence=f"从对话推断: {key}"
                        )

            # 价值观 [16-31]
            if "values_hints" in data:
                v = data["values_hints"]
                values_mapping = [
                    ("family_oriented", 16),
                    ("want_children", 17),
                    ("career_oriented", 22),
                    ("spending_style", 27),
                ]
                base_conf = v.get("confidence", 0.5)
                for key, idx in values_mapping:
                    if key in v:
                        value = v[key]
                        if isinstance(value, bool):
                            value = 1.0 if value else 0.0
                        elif isinstance(value, str):
                            value = {"thrifty": 0.2, "balanced": 0.5, "spendthrift": 0.8}.get(value, 0.5)
                        inferred_dimensions[idx] = DimensionValue(
                            value=float(value),
                            confidence=base_conf,
                            source=DataSource.CHAT_INFERENCE,
                            inferred_at=datetime.now(),
                            evidence=f"从对话推断: {key}"
                        )

            # 依恋类型 [48-63]
            if "attachment_hints" in data:
                a = data["attachment_hints"]
                attachment_mapping = [
                    ("secure", 48),
                    ("anxious", 49),
                    ("avoidant", 50),
                ]
                base_conf = a.get("confidence", 0.5)
                for key, idx in attachment_mapping:
                    if key in a:
                        inferred_dimensions[idx] = DimensionValue(
                            value=float(a[key]),
                            confidence=base_conf,
                            source=DataSource.CHAT_INFERENCE,
                            inferred_at=datetime.now(),
                            evidence=f"从对话推断: {key}"
                        )

            # 计算总体置信度
            overall_conf = sum(d.confidence for d in inferred_dimensions.values()) / len(inferred_dimensions) if inferred_dimensions else 0.0

            return ProfileInferenceResult(
                user_id=profile.user_id,
                inferred_dimensions=inferred_dimensions,
                inference_source=DataSource.CHAT_INFERENCE,
                inference_method="llm_analysis",
                evidence=messages_text[:500],
                sample_size=len(user_messages),
                overall_confidence=overall_conf,
                llm_model="claude"  # 或其他模型
            )

        except Exception as e:
            logger.error(f"AIProfileInferencer: LLM analysis failed: {e}")
            return self._fallback_analysis(user_messages, profile)

    def _fallback_analysis(
        self,
        user_messages: List[Dict[str, Any]],
        profile: UserVectorProfile
    ) -> ProfileInferenceResult:
        """
        降级分析（当 LLM 不可用时）

        基于规则的关键词分析
        """
        inferred_dimensions: Dict[int, DimensionValue] = {}

        # 合并所有消息
        all_text = " ".join([msg.get("content", "") for msg in user_messages])

        # 简单的关键词推断
        # 外向性推断
        extraversion_keywords = ["喜欢", "朋友", "聚会", "热闹", "社交", "开心", "分享"]
        extraversion_score = sum(1 for kw in extraversion_keywords if kw in all_text) / len(extraversion_keywords)
        inferred_dimensions[34] = DimensionValue(
            value=min(1.0, extraversion_score * 1.5),
            confidence=0.4,
            source=DataSource.CHAT_INFERENCE,
            inferred_at=datetime.now(),
            evidence="关键词推断: 外向性"
        )

        # 家庭导向
        family_keywords = ["家庭", "家人", "父母", "孩子", "结婚", "婚姻"]
        family_score = sum(1 for kw in family_keywords if kw in all_text) / len(family_keywords)
        inferred_dimensions[16] = DimensionValue(
            value=min(1.0, family_score * 1.5),
            confidence=0.4,
            source=DataSource.CHAT_INFERENCE,
            inferred_at=datetime.now(),
            evidence="关键词推断: 家庭导向"
        )

        return ProfileInferenceResult(
            user_id=profile.user_id,
            inferred_dimensions=inferred_dimensions,
            inference_source=DataSource.CHAT_INFERENCE,
            inference_method="keyword_fallback",
            evidence=all_text[:200],
            sample_size=len(user_messages),
            overall_confidence=0.4
        )

    async def infer_from_behavior(
        self,
        user_id: str,
        swipe_actions: List[Dict[str, Any]],
        interaction_history: List[Dict[str, Any]],
        existing_profile: Optional[UserVectorProfile] = None
    ) -> ProfileInferenceResult:
        """
        从行为中推断隐性偏好

        Args:
            user_id: 用户ID
            swipe_actions: 滑动行为列表
            interaction_history: 互动历史
            existing_profile: 已有画像

        Returns:
            推断结果
        """
        logger.info(f"AIProfileInferencer: Inferring from behavior for user {user_id}")

        profile = existing_profile or UserVectorProfile(user_id=user_id)
        inferred_dimensions: Dict[int, DimensionValue] = {}

        # 分析滑动偏好
        if swipe_actions:
            liked_profiles = [
                action for action in swipe_actions
                if action.get("action") == "like"
            ]

            if len(liked_profiles) >= 10:
                # 分析喜欢的人群特征
                # 这里可以调用 LLM 分析喜欢的用户画像特征
                pass

        # 分析互动模式
        if interaction_history:
            # 分析互动深度、频率等
            pass

        return ProfileInferenceResult(
            user_id=user_id,
            inferred_dimensions=inferred_dimensions,
            inference_source=DataSource.BEHAVIOR_INFERENCE,
            inference_method="behavior_analysis",
            sample_size=len(swipe_actions) + len(interaction_history),
            overall_confidence=0.5
        )

    async def infer_from_third_party(
        self,
        user_id: str,
        source: DataSource,
        raw_data: Dict[str, Any],
        existing_profile: Optional[UserVectorProfile] = None
    ) -> ThirdPartyDataInference:
        """
        从第三方数据推断用户画像

        Args:
            user_id: 用户ID
            source: 数据来源（微信等）
            raw_data: 原始数据（已脱敏）
            existing_profile: 已有画像

        Returns:
            第三方数据推断结果
        """
        logger.info(f"AIProfileInferencer: Inferring from {source} for user {user_id}")

        profile = existing_profile or UserVectorProfile(user_id=user_id)
        dimension_inferences: Dict[int, DimensionValue] = {}

        if source == DataSource.WECHAT_BASIC:
            # 微信基础信息推断
            dimension_inferences.update(
                self._infer_from_wechat_basic(raw_data)
            )

        elif source == DataSource.WECHAT_MOMENTS:
            # 微信朋友圈分析
            dimension_inferences.update(
                await self._infer_from_wechat_moments(raw_data)
            )

        return ThirdPartyDataInference(
            user_id=user_id,
            source=source,
            dimension_inferences=dimension_inferences,
            data_summary=json.dumps(raw_data, ensure_ascii=False)[:500],
            user_consent=True  # 假设已授权
        )

    def _infer_from_wechat_basic(
        self,
        data: Dict[str, Any]
    ) -> Dict[int, DimensionValue]:
        """
        从微信基础信息推断

        Args:
            data: 微信基础数据

        Returns:
            推断的维度
        """
        inferred: Dict[int, DimensionValue] = {}

        # 昵称分析（可推断性格倾向）
        nickname = data.get("nickname", "")
        if nickname:
            # 简单的表情符号分析
            emoji_count = sum(1 for c in nickname if ord(c) > 0x1F000)
            if emoji_count > 0:
                inferred[34] = DimensionValue(  # 外向性
                    value=0.7,
                    confidence=0.3,
                    source=DataSource.WECHAT_BASIC,
                    inferred_at=datetime.now(),
                    evidence=f"昵称包含表情符号"
                )

        # 地区推断
        province = data.get("province", "")
        city = data.get("city", "")
        if province or city:
            # 城市层级推断
            tier1_cities = ["北京", "上海", "广州", "深圳"]
            if any(c in city for c in tier1_cities):
                inferred[6] = DimensionValue(  # 城市层级
                    value=1.0,
                    confidence=0.9,
                    source=DataSource.WECHAT_BASIC,
                    inferred_at=datetime.now(),
                    evidence=f"一线城市: {city}"
                )

        return inferred

    async def _infer_from_wechat_moments(
        self,
        data: Dict[str, Any]
    ) -> Dict[int, DimensionValue]:
        """
        从微信朋友圈推断

        Args:
            data: 朋友圈数据（已脱敏）

        Returns:
            推断的维度
        """
        inferred: Dict[int, DimensionValue] = {}

        posts = data.get("posts", [])
        if not posts:
            return inferred

        # 分析朋友圈内容
        # 这里可以调用 LLM 进行深度分析
        # 示例：简单的关键词分析

        all_text = " ".join([p.get("content", "") for p in posts])

        # 兴趣推断
        interest_keywords = {
            "旅行": ["旅行", "旅游", "度假", "风景"],
            "美食": ["美食", "吃货", "餐厅"],
            "运动": ["运动", "健身", "跑步"],
            "阅读": ["读书", "阅读", "书"],
        }

        interests = []
        for interest, keywords in interest_keywords.items():
            if any(kw in all_text for kw in keywords):
                interests.append(interest)

        if interests:
            # 更新兴趣向量 [72-87]
            for i, interest in enumerate(interests[:8]):
                inferred[72 + i] = DimensionValue(
                    value=1.0,
                    confidence=0.6,
                    source=DataSource.WECHAT_MOMENTS,
                    inferred_at=datetime.now(),
                    evidence=f"朋友圈推断: {interest}"
                )

        return inferred

    def get_profile(self, user_id: str) -> Optional[UserVectorProfile]:
        """获取缓存的画像"""
        return self._profile_cache.get(user_id)

    def calculate_profile_completeness(
        self,
        profile: UserVectorProfile
    ) -> Tuple[float, str]:
        """
        计算画像完整度并返回推荐的匹配策略

        Args:
            profile: 用户画像

        Returns:
            (完整度比例, 推荐策略)
        """
        completeness = profile.calculate_completeness()
        ratio = completeness.completeness_ratio

        if ratio < 0.2:
            strategy = "cold_start"
            reason = "画像信息不足，使用冷启动策略"
        elif ratio < 0.5:
            strategy = "basic"
            reason = "基础画像，使用规则匹配"
        elif ratio < 0.8:
            strategy = "vector"
            reason = "画像较完整，使用向量匹配"
        else:
            strategy = "precise"
            reason = "画像完整，使用精准匹配"

        return ratio, strategy


# 全局实例
_profile_inferencer: Optional[AIProfileInferencer] = None


def get_profile_inferencer(llm_service=None) -> AIProfileInferencer:
    """获取推断器单例"""
    global _profile_inferencer
    if _profile_inferencer is None:
        _profile_inferencer = AIProfileInferencer(llm_service)
    return _profile_inferencer