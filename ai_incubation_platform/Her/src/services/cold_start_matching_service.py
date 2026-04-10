"""
冷启动匹配策略 - 渐进式智能收集架构

根据用户画像完整度选择不同的匹配策略：
- cold_start: 画像完整度 < 20%，使用冷启动策略
- basic: 画像完整度 20-50%，使用基础规则匹配
- vector: 画像完整度 50-80%，使用向量匹配
- precise: 画像完整度 > 80%，使用精准匹配
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import random

from models.profile_vector_models import (
    UserVectorProfile,
    ProfileCompleteness,
    DataSource,
    DimensionCategory,
    DIMENSION_DEFINITIONS,
)
from utils.logger import logger


class MatchStrategy(str, Enum):
    """匹配策略"""
    COLD_START = "cold_start"  # 冷启动
    BASIC = "basic"  # 基础规则匹配
    VECTOR = "vector"  # 向量匹配
    PRECISE = "precise"  # 精准匹配


@dataclass
class MatchCandidate:
    """匹配候选人"""
    user_id: str
    score: float
    match_type: str  # similar, complementary, random, popular
    reasoning: str
    confidence: float

    # 用于调试的详细信息
    debug_info: Optional[Dict[str, Any]] = None


@dataclass
class MatchResult:
    """匹配结果"""
    strategy: MatchStrategy
    strategy_reason: str
    profile_completeness: float
    candidates: List[MatchCandidate]

    # 匹配区域信息
    regions_count: int = 0

    # 时间
    matched_at: datetime = None

    def __post_init__(self):
        if self.matched_at is None:
            self.matched_at = datetime.now()


class ColdStartMatcher:
    """
    冷启动匹配器

    当用户画像不完整时，使用以下策略：
    1. 基础信息过滤（年龄、城市）
    2. 高兼容类型推荐（经验规则）
    3. 热门用户推荐
    4. 随机探索
    """

    def __init__(self):
        # 高兼容类型规则（经验规则）
        self.compatibility_rules = [
            # 内向者适合外向者
            {
                "trigger": {"category": "personality", "trait": "extraversion", "operator": "<", "value": 0.3},
                "recommend": {"trait": "extraversion", "range": [0.6, 1.0]},
                "reason": "性格互补，外向者能带动内向者"
            },
            # 焦虑型适合安全型
            {
                "trigger": {"category": "attachment", "trait": "anxious", "operator": ">", "value": 0.6},
                "recommend": {"trait": "secure", "range": [0.7, 1.0]},
                "reason": "安全型伴侣能帮助焦虑型建立安全感"
            },
        ]

    async def get_recommendations(
        self,
        user_id: str,
        profile: UserVectorProfile,
        candidate_pool: List[Dict[str, Any]],
        limit: int = 10
    ) -> MatchResult:
        """
        获取冷启动推荐

        Args:
            user_id: 用户ID
            profile: 用户画像
            candidate_pool: 候选池
            limit: 返回数量

        Returns:
            匹配结果
        """
        logger.info(f"ColdStartMatcher: Getting recommendations for user {user_id}")

        completeness = profile.calculate_completeness()
        ratio = completeness.completeness_ratio

        # 确定策略
        if ratio < 0.2:
            strategy = MatchStrategy.COLD_START
        elif ratio < 0.5:
            strategy = MatchStrategy.BASIC
        elif ratio < 0.8:
            strategy = MatchStrategy.VECTOR
        else:
            strategy = MatchStrategy.PRECISE

        # 根据策略选择匹配方法
        if strategy == MatchStrategy.COLD_START:
            candidates = await self._cold_start_match(user_id, profile, candidate_pool, limit)
        elif strategy == MatchStrategy.BASIC:
            candidates = await self._basic_match(user_id, profile, candidate_pool, limit)
        elif strategy == MatchStrategy.VECTOR:
            candidates = await self._vector_match(user_id, profile, candidate_pool, limit)
        else:
            candidates = await self._precise_match(user_id, profile, candidate_pool, limit)

        return MatchResult(
            strategy=strategy,
            strategy_reason=f"画像完整度 {ratio:.1%}，使用{strategy.value}策略",
            profile_completeness=ratio,
            candidates=candidates,
            regions_count=len(candidates)
        )

    async def _cold_start_match(
        self,
        user_id: str,
        profile: UserVectorProfile,
        candidate_pool: List[Dict[str, Any]],
        limit: int
    ) -> List[MatchCandidate]:
        """
        冷启动匹配策略

        混合策略：
        1. 基础信息过滤（40%）
        2. 高兼容类型（30%）
        3. 热门用户（20%）
        4. 随机探索（10%）
        """
        candidates = []

        # 1. 基础信息过滤
        basic_filtered = self._filter_by_basic_info(user_id, profile, candidate_pool)
        for candidate in basic_filtered[:int(limit * 0.4)]:
            candidates.append(MatchCandidate(
                user_id=candidate["user_id"],
                score=0.7,
                match_type="basic_filtered",
                reasoning="基础条件匹配",
                confidence=0.6,
                debug_info={"source": "basic_filter"}
            ))

        # 2. 高兼容类型
        compatible = self._get_compatible_types(user_id, profile, candidate_pool)
        for candidate in compatible[:int(limit * 0.3)]:
            candidates.append(MatchCandidate(
                user_id=candidate["user_id"],
                score=0.8,
                match_type="compatible",
                reasoning="性格互补推荐",
                confidence=0.5,
                debug_info={"source": "compatible_type"}
            ))

        # 3. 热门用户
        popular = self._get_popular_users(candidate_pool)
        for candidate in popular[:int(limit * 0.2)]:
            candidates.append(MatchCandidate(
                user_id=candidate["user_id"],
                score=0.6,
                match_type="popular",
                reasoning="热门用户推荐",
                confidence=0.4,
                debug_info={"source": "popular"}
            ))

        # 4. 随机探索
        random_candidates = self._get_random_candidates(user_id, candidate_pool, exclude_ids=[c.user_id for c in candidates])
        for candidate in random_candidates[:int(limit * 0.1)]:
            candidates.append(MatchCandidate(
                user_id=candidate["user_id"],
                score=0.5,
                match_type="random",
                reasoning="探索推荐",
                confidence=0.3,
                debug_info={"source": "random"}
            ))

        # 打乱顺序，避免用户发现规律
        random.shuffle(candidates)

        return candidates[:limit]

    async def _basic_match(
        self,
        user_id: str,
        profile: UserVectorProfile,
        candidate_pool: List[Dict[str, Any]],
        limit: int
    ) -> List[MatchCandidate]:
        """
        基础规则匹配

        使用已有的画像维度进行规则匹配
        """
        candidates = []

        # 获取已填充的维度
        filled_dims = profile.dimensions

        # 基础过滤
        basic_filtered = self._filter_by_basic_info(user_id, profile, candidate_pool)

        # 对每个候选计算规则匹配分
        for candidate_data in basic_filtered:
            score = 0.0
            reasons = []

            # 检查价值观匹配（如果已填写）
            if 16 in filled_dims and 17 in filled_dims:
                # 家庭导向检查
                candidate_family = candidate_data.get("profile", {}).get("family_oriented")
                if candidate_family is not None:
                    user_family = profile.get_dimension(16).value
                    if abs(user_family - (1.0 if candidate_family else 0.0)) < 0.3:
                        score += 0.3
                        reasons.append("家庭观相似")

            # 检查年龄偏好
            if 0 in filled_dims:
                user_age = profile.get_dimension(0).value * 100  # 假设归一化时除以了100
                candidate_age = candidate_data.get("age", 0)
                # 检查是否在偏好范围内
                if 1 in filled_dims and 2 in filled_dims:
                    min_age = profile.get_dimension(1).value * 100
                    max_age = profile.get_dimension(2).value * 100
                    if min_age <= candidate_age <= max_age:
                        score += 0.2
                        reasons.append("年龄符合偏好")

            if score > 0:
                candidates.append(MatchCandidate(
                    user_id=candidate_data["user_id"],
                    score=score,
                    match_type="basic_rule",
                    reasoning="、".join(reasons) if reasons else "基础匹配",
                    confidence=0.6
                ))

        # 按分数排序
        candidates.sort(key=lambda x: x.score, reverse=True)

        # 如果候选不够，补充冷启动推荐
        if len(candidates) < limit:
            cold_candidates = await self._cold_start_match(user_id, profile, candidate_pool, limit - len(candidates))
            candidates.extend(cold_candidates)

        return candidates[:limit]

    async def _vector_match(
        self,
        user_id: str,
        profile: UserVectorProfile,
        candidate_pool: List[Dict[str, Any]],
        limit: int
    ) -> List[MatchCandidate]:
        """
        向量匹配

        使用用户向量进行相似度/互补度计算
        """
        candidates = []

        user_vector = profile.vector

        for candidate_data in candidate_pool:
            candidate_id = candidate_data["user_id"]

            # 获取候选向量
            candidate_vector = candidate_data.get("vector", None)
            if candidate_vector is None:
                continue

            # 计算相似度
            similarity = self._cosine_similarity(user_vector, candidate_vector)

            # 计算互补度
            complementarity = self._calculate_complementarity(user_vector, candidate_vector)

            # 综合分数
            score = similarity * 0.6 + complementarity * 0.4

            if score > 0.3:
                candidates.append(MatchCandidate(
                    user_id=candidate_id,
                    score=score,
                    match_type="similar" if similarity > complementarity else "complementary",
                    reasoning="性格相似" if similarity > complementarity else "性格互补",
                    confidence=0.8,
                    debug_info={
                        "similarity": similarity,
                        "complementarity": complementarity
                    }
                ))

        # 按分数排序
        candidates.sort(key=lambda x: x.score, reverse=True)

        return candidates[:limit]

    async def _precise_match(
        self,
        user_id: str,
        profile: UserVectorProfile,
        candidate_pool: List[Dict[str, Any]],
        limit: int
    ) -> List[MatchCandidate]:
        """
        精准匹配

        使用完整的向量匹配 + 规则约束
        """
        candidates = []

        user_vector = profile.vector

        for candidate_data in candidate_pool:
            candidate_id = candidate_data["user_id"]
            candidate_vector = candidate_data.get("vector", None)

            if candidate_vector is None:
                continue

            # 1. 检查一票否决维度
            veto, veto_reason = self._check_veto_dimensions(profile, candidate_data)
            if veto:
                logger.debug(f"Veto match: {veto_reason}")
                continue

            # 2. 计算向量匹配
            similarity = self._cosine_similarity(user_vector, candidate_vector)
            complementarity = self._calculate_complementarity(user_vector, candidate_vector)

            # 3. 检查黑名单区域
            in_blacklist, blacklist_reason = self._check_blacklist_regions(user_vector, candidate_vector)
            if in_blacklist:
                logger.debug(f"Blacklist match: {blacklist_reason}")
                continue

            # 4. 综合评分
            score = similarity * 0.5 + complementarity * 0.5

            # 生成推荐理由
            reasoning = self._generate_reasoning(profile, candidate_data, similarity, complementarity)

            candidates.append(MatchCandidate(
                user_id=candidate_id,
                score=score,
                match_type="precise",
                reasoning=reasoning,
                confidence=0.9,
                debug_info={
                    "similarity": similarity,
                    "complementarity": complementarity
                }
            ))

        # 按分数排序
        candidates.sort(key=lambda x: x.score, reverse=True)

        return candidates[:limit]

    def _filter_by_basic_info(
        self,
        user_id: str,
        profile: UserVectorProfile,
        candidate_pool: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """基础信息过滤"""
        filtered = []

        # 获取用户基础信息
        user_age = profile.get_dimension(0)
        user_gender = profile.get_dimension(3)
        user_location = profile.get_dimension(6)

        for candidate in candidate_pool:
            if candidate.get("user_id") == user_id:
                continue

            # 年龄过滤
            if user_age:
                candidate_age = candidate.get("age", 0)
                # 简单的年龄范围检查
                if abs(candidate_age - user_age.value * 100) > 20:
                    continue

            # 性别过滤（异性恋假设）
            if user_gender:
                candidate_gender = candidate.get("gender", "")
                user_gender_val = user_gender.value
                # 如果用户是男性（0），候选应该是女性（1）
                if user_gender_val < 0.5 and candidate_gender != "female":
                    continue
                if user_gender_val >= 0.5 and candidate_gender != "male":
                    continue

            filtered.append(candidate)

        return filtered

    def _get_compatible_types(
        self,
        user_id: str,
        profile: UserVectorProfile,
        candidate_pool: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """获取高兼容类型候选"""
        compatible = []

        # 检查用户性格特征
        extraversion = profile.get_dimension(34)
        anxious = profile.get_dimension(49)

        for candidate in candidate_pool:
            if candidate.get("user_id") == user_id:
                continue

            candidate_profile = candidate.get("profile", {})

            # 内向者推荐外向者
            if extraversion and extraversion.value < 0.3:
                candidate_extraversion = candidate_profile.get("extraversion", 0.5)
                if candidate_extraversion > 0.6:
                    compatible.append(candidate)
                    continue

            # 焦虑型推荐安全型
            if anxious and anxious.value > 0.6:
                candidate_secure = candidate_profile.get("attachment_secure", 0.5)
                if candidate_secure > 0.7:
                    compatible.append(candidate)
                    continue

        return compatible

    def _get_popular_users(
        self,
        candidate_pool: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """获取热门用户"""
        # 按互动量排序
        sorted_pool = sorted(
            candidate_pool,
            key=lambda x: x.get("interaction_count", 0),
            reverse=True
        )
        return sorted_pool[:20]

    def _get_random_candidates(
        self,
        user_id: str,
        candidate_pool: List[Dict[str, Any]],
        exclude_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """获取随机候选"""
        available = [
            c for c in candidate_pool
            if c.get("user_id") != user_id and c.get("user_id") not in exclude_ids
        ]
        return random.sample(available, min(10, len(available)))

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """计算余弦相似度"""
        import math

        if len(vec_a) != len(vec_b):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def _calculate_complementarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """
        计算互补度

        在某些维度上，差异越大越好
        """
        # 互补维度索引
        complementary_dims = [
            (34, 0.3),  # 外向性：差异大互补
            (40, 0.2),  # 社交活跃度
            (44, 0.2),  # 信任程度
        ]

        total_complementarity = 0.0
        total_weight = 0.0

        for dim_idx, weight in complementary_dims:
            if dim_idx < len(vec_a) and dim_idx < len(vec_b):
                # 差异越大，互补度越高
                diff = abs(vec_a[dim_idx] - vec_b[dim_idx])
                complementarity = diff * weight
                total_complementarity += complementarity
                total_weight += weight

        return total_complementarity / total_weight if total_weight > 0 else 0.5

    def _check_veto_dimensions(
        self,
        profile: UserVectorProfile,
        candidate_data: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        检查一票否决维度

        Returns:
            (是否否决, 原因)
        """
        candidate_profile = candidate_data.get("profile", {})

        # 生育意愿检查
        user_want_children = profile.get_dimension(17)
        if user_want_children:
            candidate_want_children = candidate_profile.get("want_children")
            if candidate_want_children is not None:
                user_val = user_want_children.value > 0.5
                if user_val != candidate_want_children:
                    return True, "生育意愿不一致"

        # 金钱观检查
        user_spending = profile.get_dimension(27)
        if user_spending:
            candidate_spending = candidate_profile.get("spending_style")
            if candidate_spending is not None:
                spending_map = {"thrifty": 0.2, "balanced": 0.5, "spendthrift": 0.8}
                candidate_val = spending_map.get(candidate_spending, 0.5)
                if abs(user_spending.value - candidate_val) > 0.7:
                    return True, "金钱观差异过大"

        return False, ""

    def _check_blacklist_regions(
        self,
        vec_a: List[float],
        vec_b: List[float]
    ) -> Tuple[bool, str]:
        """
        检查黑名单区域

        某些组合是一票否决的
        """
        # 焦虑型 + 回避型
        if len(vec_a) > 50 and len(vec_b) > 50:
            a_anxious = vec_a[49]
            a_avoidant = vec_a[50]
            b_anxious = vec_b[49]
            b_avoidant = vec_b[50]

            # 一方焦虑，一方回避
            if (a_anxious > 0.6 and b_avoidant > 0.6) or (a_avoidant > 0.6 and b_anxious > 0.6):
                return True, "焦虑型与回避型组合"

        return False, ""

    def _generate_reasoning(
        self,
        profile: UserVectorProfile,
        candidate_data: Dict[str, Any],
        similarity: float,
        complementarity: float
    ) -> str:
        """生成推荐理由"""
        reasons = []

        if similarity > 0.7:
            reasons.append("价值观和性格相似")

        if complementarity > 0.5:
            reasons.append("性格互补")

        # 添加具体匹配点
        candidate_profile = candidate_data.get("profile", {})

        # 家庭观匹配
        user_family = profile.get_dimension(16)
        if user_family and user_family.value > 0.7:
            if candidate_profile.get("family_oriented"):
                reasons.append("都重视家庭")

        # 兴趣匹配
        user_interests = profile.get_dimension(72)
        if user_interests:
            reasons.append("有共同兴趣")

        if not reasons:
            reasons.append("系统推荐")

        return "、".join(reasons[:3])


# 全局实例
_cold_start_matcher: Optional[ColdStartMatcher] = None


def get_cold_start_matcher() -> ColdStartMatcher:
    """获取冷启动匹配器单例"""
    global _cold_start_matcher
    if _cold_start_matcher is None:
        _cold_start_matcher = ColdStartMatcher()
    return _cold_start_matcher