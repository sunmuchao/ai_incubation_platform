"""
LLM 增强的匹配引擎

将深度语义分析能力集成到匹配算法中，实现：
1. 基于价值观契合度的深度匹配
2. 沟通风格兼容性分析
3. 情感需求互补性匹配
4. 可解释的匹配理由生成

架构原则：
- 语义优先：基于语义理解而非关键词匹配
- 多维度匹配：价值观、沟通、情感多层面分析
- 可解释性：每个匹配都有详细的理由
- 性能优化：LLM 分析结果缓存，避免重复计算
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc
import json
import uuid

from db.database import SessionLocal
from utils.db_session_manager import db_session, db_session_readonly, optional_db_session
from db.models import (
    UserDB, MatchHistoryDB,
    SwipeActionDB, UserPreferenceDB, ConversationDB
)
from utils.logger import logger
from config import settings
from services.llm_semantic_service import get_llm_semantic_service
from cache.cache_manager import cache_manager
from services.base_service import BaseService


class LLMMatchingEngine(BaseService):
    """
    LLM 增强的匹配引擎

    传统匹配算法 + LLM 深度语义分析相结合：
    1. 初筛：基于基础条件（年龄、地点、性别偏好）
    2. 粗排：基于兴趣标签、行为特征
    3. 精排：LLM 深度语义匹配分析
    """

    def __init__(self, db: Session):
        super().__init__(db)
        self.semantic_service = get_llm_semantic_service()
        self.cache = cache_manager.get_instance()

        # 匹配配置
        self.config = {
            "max_candidates": 100,  # 初筛最大候选数
            "llm_analysis_limit": 20,  # LLM 深度分析数量
            "final_recommendations": 10,  # 最终推荐数量
            "cache_ttl_hours": 24,  # 匹配结果缓存时间
            "min_basic_compatibility": 0.3,  # 最小基础兼容性
        }

    def _generate_cache_key(self, user_id: str, limit: int) -> str:
        """
        生成缓存键（考虑关键参数）

        Args:
            user_id: 用户 ID
            limit: 返回数量限制

        Returns:
            缓存键字符串
        """
        import hashlib
        # 使用哈希避免缓存键过长
        params = f"{user_id}:{limit}"
        params_hash = hashlib.md5(params.encode()).hexdigest()[:16]
        return f"deep_matches:{params_hash}"

    async def get_deep_matches(
        self,
        user_id: str,
        limit: int = 10,
        force_refresh: bool = False
    ) -> List[Dict[str, Any]]:
        """
        获取深度匹配推荐

        流程：
        1. 检查缓存
        2. 基础条件筛选
        3. 兴趣和行为粗排
        4. LLM 深度语义分析
        5. 综合排序返回

        Args:
            user_id: 用户 ID
            limit: 返回数量
            force_refresh: 是否强制刷新

        Returns:
            匹配推荐列表，每个包含：
            - user: 候选用户信息
            - compatibility_score: 综合匹配度
            - match_reasons: 匹配理由
            - value_alignment: 价值观契合分析
            - communication_tips: 沟通建议
        """
        # 1. 检查缓存（使用改进的缓存键）
        cache_key = self._generate_cache_key(user_id, limit)
        if not force_refresh:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.info(f"Cache hit for deep matches: {user_id}")
                return cached

        # 2. 获取用户画像
        user_profile = await self._get_user_profile(user_id)
        if not user_profile:
            logger.warning(f"User profile not found: {user_id}")
            return []

        # 3. 基础条件筛选
        candidates = await self._basic_filtering(user_id, user_profile)
        if not candidates:
            return []

        logger.info(f"Basic filtering produced {len(candidates)} candidates for user {user_id}")

        # 4. 兴趣和行为粗排
        ranked_candidates = await self._rough_ranking(user_id, candidates)
        logger.info(f"Rough ranking produced {len(ranked_candidates)} candidates for user {user_id}")

        # 5. LLM 深度语义分析（Top N）
        deep_analyzed = await self._deep_semantic_analysis(
            user_id,
            user_profile,
            ranked_candidates[:self.config["llm_analysis_limit"]]
        )
        logger.info(f"Deep analysis completed for {len(deep_analyzed)} candidates for user {user_id}")

        # 6. 综合排序
        final_matches = await self._final_ranking(deep_analyzed, limit)

        # 7. 缓存结果
        await self.cache.set(
            cache_key,
            final_matches,
            ttl=self.config["cache_ttl_hours"] * 3600
        )

        return final_matches

    async def _get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户完整画像"""
        user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user:
            return None

        # 获取用户偏好
        preferences = self.db.query(UserPreferenceDB).filter(
            UserPreferenceDB.user_id == user_id
        ).first()

        # 构建完整画像
        profile = {
            "user_id": user_id,
            "age": user.age,
            "gender": user.gender,
            "location": user.location,
            "interests": user.interests or [],
            "bio": user.bio or "",
            "occupation": user.occupation or "",
            "education": user.education or "",
            "preferences": {
                "age_range": preferences.preferred_age_range if preferences else [user.age - 5, user.age + 5],
                "location_range": preferences.preferred_location_range if preferences else 50,
            }
        }

        # 获取对话样本（用于语义分析）
        conversation_samples = self.db.query(ConversationDB).filter(
            or_(
                and_(ConversationDB.user_id_1 == user_id, ConversationDB.sender_id == user_id),
                and_(ConversationDB.user_id_2 == user_id, ConversationDB.sender_id == user_id)
            )
        ).order_by(desc(ConversationDB.created_at)).limit(10).all()

        profile["conversation_samples"] = [c.message_content for c in conversation_samples[:5]]

        # 获取行为特征（如果有）
        from services.behavior_learning_service import BehaviorLearningService
        behavior_service = BehaviorLearningService(self.db)
        behavior_features = behavior_service.get_user_features(user_id)
        if behavior_features:
            profile["behavior_features"] = behavior_features

        return profile

    async def _basic_filtering(
        self,
        user_id: str,
        user_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """基础条件筛选"""
        # 获取用户偏好
        preferences = user_profile.get("preferences", {})
        age_min, age_max = preferences.get("age_range", [18, 100])
        location_range = preferences.get("location_range", 50)

        # 构建查询条件
        query = self.db.query(UserDB).filter(
            UserDB.id != user_id,
            UserDB.is_active == True,
            UserDB.age >= age_min,
            UserDB.age <= age_max,
        )

        # 性别偏好筛选
        user_gender = user_profile.get("gender")
        if user_gender == "male":
            query = query.filter(UserDB.gender == "female")
        elif user_gender == "female":
            query = query.filter(UserDB.gender == "male")
        # 如果用户是其他性别或偏好其他性别，这里可以扩展

        # 地点筛选（简化版，实际应该用地理距离计算）
        user_location = user_profile.get("location")
        if user_location:
            # 简化：假设地点格式为 "城市，其他"
            city = user_location.split(",")[0]
            query = query.filter(UserDB.location.like(f"%{city}%"))

        # 执行查询
        candidates = query.limit(self.config["max_candidates"]).all()

        return [
            {
                "user_id": c.id,
                "age": c.age,
                "gender": c.gender,
                "location": c.location,
                "interests": c.interests or [],
                "bio": c.bio or "",
                "occupation": c.occupation or "",
                "education": c.education or "",
                "avatar_url": c.avatar_url
            }
            for c in candidates
        ]

    async def _rough_ranking(
        self,
        user_id: str,
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        粗排：基于兴趣和行为特征

        计算维度：
        1. 兴趣重叠度（Jaccard 相似度）
        2. 教育背景相似度
        3. 职业相关性
        4. 历史互动偏好
        """
        user_profile = await self._get_user_profile(user_id)
        user_interests = set(user_profile.get("interests", []))

        ranked = []
        for candidate in candidates:
            score = 0.5  # 基础分

            # 兴趣重叠度
            candidate_interests = set(candidate.get("interests", []))
            if user_interests and candidate_interests:
                intersection = len(user_interests & candidate_interests)
                union = len(user_interests | candidate_interests)
                if union > 0:
                    jaccard = intersection / union
                    score += jaccard * 0.3  # 兴趣权重 30%

            # 教育背景相似度
            if user_profile.get("education") and candidate.get("education"):
                if user_profile["education"] == candidate["education"]:
                    score += 0.1

            # 职业相关性（简化：相同行业）
            if user_profile.get("occupation") and candidate.get("occupation"):
                if user_profile["occupation"][:2] == candidate["occupation"][:2]:
                    score += 0.1

            candidate["rough_score"] = min(1.0, score)
            ranked.append(candidate)

        # 按分数排序
        ranked.sort(key=lambda x: x.get("rough_score", 0), reverse=True)

        return ranked

    async def _deep_semantic_analysis(
        self,
        user_id: str,
        user_profile: Dict[str, Any],
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        LLM 深度语义分析

        对每个候选者进行：
        1. 价值观契合度分析
        2. 沟通风格兼容性
        3. 情感需求匹配
        """
        analyzed = []

        for candidate in candidates:
            try:
                # 获取候选者对话样本
                candidate_profile = await self._get_user_profile(candidate["user_id"])

                # LLM 语义匹配分析
                compatibility = await self.semantic_service.calculate_semantic_compatibility(
                    user1_profile=user_profile,
                    user2_profile=candidate_profile or candidate,
                    user1_conversation_samples=user_profile.get("conversation_samples", []),
                    user2_conversation_samples=candidate_profile.get("conversation_samples", []) if candidate_profile else []
                )

                # 整合结果
                candidate["deep_analysis"] = compatibility
                candidate["semantic_score"] = compatibility.get("overall_compatibility", 0.5)

                analyzed.append(candidate)

            except Exception as e:
                logger.error(f"Deep analysis failed for candidate {candidate['user_id']}: {e}")
                # 降级处理：使用粗排分数
                candidate["deep_analysis"] = {}
                candidate["semantic_score"] = candidate.get("rough_score", 0.5)
                analyzed.append(candidate)

        return analyzed

    async def _final_ranking(
        self,
        candidates: List[Dict[str, Any]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        综合排序

        综合分数 = 粗排分数 × 0.3 + 语义匹配分数 × 0.7
        """
        for candidate in candidates:
            rough_score = candidate.get("rough_score", 0.5)
            semantic_score = candidate.get("semantic_score", 0.5)

            # 加权综合
            final_score = rough_score * 0.3 + semantic_score * 0.7
            candidate["final_score"] = final_score

        # 排序
        candidates.sort(key=lambda x: x.get("final_score", 0), reverse=True)

        # 构建返回结果
        result = []
        for candidate in candidates[:limit]:
            deep_analysis = candidate.get("deep_analysis", {})

            result.append({
                "user_id": candidate["user_id"],
                "name": candidate.get("name", ""),
                "age": candidate.get("age"),
                "location": candidate.get("location", ""),
                "avatar_url": candidate.get("avatar_url", ""),
                "interests": candidate.get("interests", []),
                "bio": candidate.get("bio", ""),
                "compatibility_score": round(candidate.get("final_score", 0) * 100, 1),
                "match_reasons": self._generate_match_reasons(candidate),
                "value_alignment": deep_analysis.get("value_alignment", {}),
                "communication_tips": deep_analysis.get("communication_compatibility", {}).get("tips", []),
                "relationship_strengths": deep_analysis.get("relationship_strengths", []),
                "semantic_analysis": deep_analysis
            })

        return result

    def _generate_match_reasons(self, candidate: Dict[str, Any]) -> List[str]:
        """生成匹配理由"""
        reasons = []

        deep_analysis = candidate.get("deep_analysis", {})

        # LLM 生成的匹配理由
        if deep_analysis.get("match_reasoning"):
            reasons.append(deep_analysis["match_reasoning"])

        # 共同兴趣
        user_interests = set(candidate.get("user_interests", []))
        candidate_interests = set(candidate.get("interests", []))
        common = user_interests & candidate_interests
        if common:
            reasons.append(f"你们有 {len(common)} 个共同兴趣：{', '.join(list(common)[:3])}")

        # 价值观契合
        value_alignment = deep_analysis.get("value_alignment", {})
        if value_alignment.get("aligned_values"):
            aligned = value_alignment["aligned_values"][:2]
            reasons.append(f"价值观契合：{', '.join(aligned)}")

        # 沟通兼容
        comm_compat = deep_analysis.get("communication_compatibility", {})
        if comm_compat.get("strengths"):
            reasons.append(f"沟通互补：{comm_compat['strengths'][0]}")

        return reasons[:4]  # 最多 4 条理由

    async def refresh_user_matches(self, user_id: str):
        """刷新用户匹配缓存"""
        await self.cache.delete(f"deep_matches:{user_id}")


# 工厂函数
def get_llm_matching_engine(db: Session) -> LLMMatchingEngine:
    """获取 LLM 匹配引擎实例"""
    return LLMMatchingEngine(db)
