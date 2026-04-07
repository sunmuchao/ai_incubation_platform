"""
P6 - 智能推荐引擎

基于多策略的商机推荐系统：
1. 基于内容的推荐 - 匹配用户关注的行业/关键词
2. 协同过滤推荐 - 基于相似用户的行为
3. 知识图谱推荐 - 基于实体关系发现
4. 趋势驱动推荐 - 基于上升趋势的领域
"""
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging
import numpy as np
from collections import defaultdict

logger = logging.getLogger(__name__)


class RecommendationType(Enum):
    """推荐类型"""
    CONTENT_BASED = "content_based"  # 基于内容
    COLLABORATIVE = "collaborative"  # 协同过滤
    KNOWLEDGE_GRAPH = "knowledge_graph"  # 知识图谱
    TREND_DRIVEN = "trend_driven"  # 趋势驱动
    HOT_SPOT = "hot_spot"  # 热点推荐


class UserPreference:
    """用户画像模型"""

    def __init__(
        self,
        user_id: str,
        preferred_industries: Optional[List[str]] = None,
        preferred_keywords: Optional[List[str]] = None,
        preferred_opportunity_types: Optional[List[str]] = None,
        min_confidence: float = 0.5,
        min_value: float = 0,
        risk_tolerance: float = 0.5,  # 风险承受能力 0-1
        investment_range: Tuple[float, float] = (0, float('inf')),
        geographic_preference: Optional[List[str]] = None,
        past_interactions: Optional[List[Dict]] = None
    ):
        self.user_id = user_id
        self.preferred_industries = preferred_industries or []
        self.preferred_keywords = preferred_keywords or []
        self.preferred_opportunity_types = preferred_opportunity_types or []
        self.min_confidence = min_confidence
        self.min_value = min_value
        self.risk_tolerance = risk_tolerance
        self.investment_range = investment_range
        self.geographic_preference = geographic_preference or []
        self.past_interactions = past_interactions or []
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "preferred_industries": self.preferred_industries,
            "preferred_keywords": self.preferred_keywords,
            "preferred_opportunity_types": self.preferred_opportunity_types,
            "min_confidence": self.min_confidence,
            "min_value": self.min_value,
            "risk_tolerance": self.risk_tolerance,
            "investment_range": self.investment_range,
            "geographic_preference": self.geographic_preference,
        }


class Recommendation:
    """推荐结果模型"""

    def __init__(
        self,
        opportunity_id: str,
        user_id: str,
        recommendation_type: RecommendationType,
        score: float,
        reason: str,
        opportunity_data: Dict[str, Any],
        explained_factors: Optional[List[str]] = None
    ):
        self.id = f"rec_{opportunity_id}_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.opportunity_id = opportunity_id
        self.user_id = user_id
        self.recommendation_type = recommendation_type
        self.score = score
        self.reason = reason
        self.opportunity_data = opportunity_data
        self.explained_factors = explained_factors or []
        self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "opportunity_id": self.opportunity_id,
            "user_id": self.user_id,
            "recommendation_type": self.recommendation_type.value,
            "score": round(self.score, 4),
            "reason": self.reason,
            "explained_factors": self.explained_factors,
            "opportunity_summary": {
                "title": self.opportunity_data.get("title", ""),
                "type": self.opportunity_data.get("type", ""),
                "confidence_score": self.opportunity_data.get("confidence_score", 0),
                "potential_value": self.opportunity_data.get("potential_value", 0),
            },
            "created_at": self.created_at.isoformat()
        }


class ContentBasedRecommender:
    """基于内容的推荐器"""

    def __init__(self):
        self.keyword_weights = {
            "industry_match": 0.35,
            "keyword_match": 0.30,
            "type_match": 0.15,
            "confidence_bonus": 0.10,
            "value_bonus": 0.10,
        }

    def calculate_similarity(
        self,
        opportunity: Dict[str, Any],
        user_preference: UserPreference
    ) -> Tuple[float, List[str]]:
        """
        计算商机与用户偏好的相似度

        Returns:
            (相似度分数 0-1, 匹配因素列表)
        """
        factors = []
        scores = {}

        # 行业匹配
        opp_industry = opportunity.get("industry", "")
        industry_match = 0.0
        if opp_industry in user_preference.preferred_industries:
            industry_match = 1.0
            factors.append(f"行业匹配：{opp_industry}")
        elif any(ind in opp_industry for ind in user_preference.preferred_industries):
            industry_match = 0.6
            factors.append(f"行业相关：{opp_industry}")

        scores["industry_match"] = industry_match

        # 关键词匹配
        opp_keywords = opportunity.get("tags", [])
        opp_text = f"{opportunity.get('title', '')} {opportunity.get('description', '')}".lower()

        keyword_matches = sum(
            1 for kw in user_preference.preferred_keywords
            if kw.lower() in opp_text or kw.lower() in [k.lower() for k in opp_keywords]
        )
        keyword_match = min(1.0, keyword_matches / max(1, len(user_preference.preferred_keywords)))
        if keyword_matches > 0:
            factors.append(f"关键词匹配：{keyword_matches} 个")

        scores["keyword_match"] = keyword_match

        # 类型匹配
        opp_type = opportunity.get("type", "")
        type_match = 1.0 if opp_type in user_preference.preferred_opportunity_types else 0.5
        if opp_type in user_preference.preferred_opportunity_types:
            factors.append(f"类型匹配：{opp_type}")

        scores["type_match"] = type_match

        # 置信度加成
        confidence = opportunity.get("confidence_score", 0.5)
        confidence_bonus = confidence
        if confidence >= user_preference.min_confidence:
            factors.append(f"置信度达标：{confidence:.2f}")

        scores["confidence_bonus"] = confidence_bonus

        # 价值加成
        value = opportunity.get("potential_value", 0)
        value_bonus = min(1.0, value / max(1, user_preference.min_value)) if user_preference.min_value > 0 else 0.5
        if value >= user_preference.min_value:
            factors.append(f"价值达标：{value:.0f}")

        scores["value_bonus"] = value_bonus

        # 加权计算总分
        total_score = sum(
            scores[k] * self.keyword_weights[k]
            for k in self.keyword_weights
        )

        return total_score, factors

    def recommend(
        self,
        opportunities: List[Dict[str, Any]],
        user_preference: UserPreference,
        limit: int = 10
    ) -> List[Tuple[Dict, float, List[str]]]:
        """
        推荐商机

        Returns:
            [(商机数据，分数，匹配因素)]
        """
        scored = []

        for opp in opportunities:
            score, factors = self.calculate_similarity(opp, user_preference)
            if score > 0.3:  # 阈值过滤
                scored.append((opp, score, factors))

        # 按分数排序
        scored.sort(key=lambda x: x[1], reverse=True)

        return scored[:limit]


class CollaborativeFilterRecommender:
    """协同过滤推荐器"""

    def __init__(self):
        # 用户 - 商机交互矩阵（简化版）
        self.user_interactions: Dict[str, Set[str]] = defaultdict(set)
        # 用户相似度缓存
        self.user_similarity_cache: Dict[Tuple[str, str], float] = {}

    def add_interaction(self, user_id: str, opportunity_id: str):
        """记录用户交互"""
        self.user_interactions[user_id].add(opportunity_id)

    def calculate_user_similarity(
        self,
        user1_id: str,
        user2_id: str
    ) -> float:
        """计算用户相似度（Jaccard 相似度）"""
        if (user1_id, user2_id) in self.user_similarity_cache:
            return self.user_similarity_cache[(user1_id, user2_id)]

        set1 = self.user_interactions[user1_id]
        set2 = self.user_interactions[user2_id]

        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        similarity = intersection / union if union > 0 else 0.0
        self.user_similarity_cache[(user1_id, user2_id)] = similarity

        return similarity

    def find_similar_users(
        self,
        target_user_id: str,
        limit: int = 10
    ) -> List[Tuple[str, float]]:
        """找到相似用户"""
        similarities = []

        for other_user_id in self.user_interactions:
            if other_user_id != target_user_id:
                sim = self.calculate_user_similarity(target_user_id, other_user_id)
                if sim > 0.1:  # 相似度阈值
                    similarities.append((other_user_id, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:limit]

    def recommend(
        self,
        target_user_id: str,
        opportunities: List[Dict[str, Any]],
        limit: int = 10
    ) -> List[Tuple[Dict, float, str]]:
        """
        基于协同过滤推荐

        Returns:
            [(商机数据，分数，推荐理由)]
        """
        # 获取目标用户已交互的商机
        user_history = self.user_interactions[target_user_id]

        # 找到相似用户
        similar_users = self.find_similar_users(target_user_id, limit=20)

        if not similar_users:
            # 冷启动：返回热门商机
            return self._recommend_hot(opportunities, limit)

        # 收集相似用户喜欢的商机
        opportunity_scores = defaultdict(float)
        opportunity_sources = defaultdict(list)

        for other_user_id, similarity in similar_users:
            other_history = self.user_interactions[other_user_id]
            # 找出目标用户未交互的商机
            new_opportunities = other_history - user_history

            for opp_id in new_opportunities:
                opportunity_scores[opp_id] += similarity
                opportunity_sources[opp_id].append(other_user_id)

        # 转换为推荐列表
        opp_map = {opp["id"]: opp for opp in opportunities}
        recommendations = []

        for opp_id, score in sorted(opportunity_scores.items(), key=lambda x: x[1], reverse=True):
            if opp_id in opp_map:
                sources = opportunity_sources[opp_id]
                reason = f"与 {len(sources)} 位相似用户感兴趣"
                recommendations.append((opp_map[opp_id], score, reason))

        return recommendations[:limit]

    def _recommend_hot(
        self,
        opportunities: List[Dict[str, Any]],
        limit: int
    ) -> List[Tuple[Dict, float, str]]:
        """热门推荐（冷启动）"""
        # 按置信度和价值排序
        scored = []
        for opp in opportunities:
            score = opp.get("confidence_score", 0.5) * 0.5 + \
                    min(1.0, opp.get("potential_value", 0) / 10000000) * 0.5
            scored.append((opp, score, "热门商机"))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]


class KnowledgeGraphRecommender:
    """基于知识图谱的推荐器"""

    def __init__(self):
        # 实体关系图（简化版）
        self.entities: Dict[str, Dict] = {}
        self.relationships: Dict[str, List[Tuple[str, str]]] = defaultdict(list)

    def add_entity(self, entity_id: str, entity_data: Dict):
        """添加实体"""
        self.entities[entity_id] = entity_data

    def add_relationship(self, from_entity: str, to_entity: str, rel_type: str):
        """添加关系"""
        self.relationships[from_entity].append((to_entity, rel_type))

    def find_related_opportunities(
        self,
        seed_opportunity: Dict[str, Any],
        opportunities: List[Dict[str, Any]],
        depth: int = 2
    ) -> List[Tuple[Dict, float, str]]:
        """
        基于知识图谱发现相关商机

        Args:
            seed_opportunity: 种子商机
            opportunities: 候选商机列表
            depth: 搜索深度

        Returns:
            [(商机数据，分数，推荐理由)]
        """
        # 提取种子商机的实体
        seed_entities = seed_opportunity.get("related_entities", [])
        if not seed_entities:
            # 从标题/描述提取关键词作为实体
            seed_entities = [{"name": seed_opportunity.get("industry", "")}]

        # 查找相关商机
        related = []
        for opp in opportunities:
            if opp["id"] == seed_opportunity["id"]:
                continue

            opp_entities = opp.get("related_entities", [])

            # 计算实体重叠度
            seed_names = {e.get("name", "").lower() for e in seed_entities}
            opp_names = {e.get("name", "").lower() for e in opp_entities}

            overlap = len(seed_names & opp_names)
            if overlap > 0:
                score = min(1.0, overlap / max(1, len(seed_entities)))
                reason = f"与 {overlap} 个相关实体有关联"
                related.append((opp, score, reason))

        # 按分数排序
        related.sort(key=lambda x: x[1], reverse=True)

        return related[:depth * 5]

    def discover_hidden_connections(
        self,
        opportunities: List[Dict[str, Any]]
    ) -> List[Dict]:
        """
        发现隐藏的商业关系
        """
        connections = []

        # 构建行业 - 公司映射
        industry_companies = defaultdict(list)
        for opp in opportunities:
            industry = opp.get("industry", "")
            companies = [e.get("name") for e in opp.get("related_entities", [])
                        if e.get("type") == "company"]
            for company in companies:
                industry_companies[industry].append((company, opp["id"]))

        # 发现跨行业连接
        for industry1, companies1 in industry_companies.items():
            for industry2, companies2 in industry_companies.items():
                if industry1 != industry2:
                    common_companies = set(c[0] for c in companies1) & set(c[0] for c in companies2)
                    if common_companies:
                        connections.append({
                            "type": "cross_industry",
                            "industry1": industry1,
                            "industry2": industry2,
                            "common_companies": list(common_companies),
                            "strength": len(common_companies)
                        })

        return connections


class TrendDrivenRecommender:
    """趋势驱动推荐器"""

    def __init__(self):
        self.trend_scores: Dict[str, float] = {}
        self.keyword_trends: Dict[str, List[float]] = defaultdict(list)

    def update_trend(
        self,
        keyword: str,
        value: float,
        timestamp: datetime
    ):
        """更新趋势数据"""
        self.keyword_trends[keyword].append(value)
        # 保留最近 30 条数据
        if len(self.keyword_trends[keyword]) > 30:
            self.keyword_trends[keyword] = self.keyword_trends[keyword][-30:]

        # 计算趋势分数
        if len(self.keyword_trends[keyword]) >= 3:
            recent = np.mean(self.keyword_trends[keyword][-3:])
            old = np.mean(self.keyword_trends[keyword][:-3])
            if old > 0:
                self.trend_scores[keyword] = (recent - old) / old
            else:
                self.trend_scores[keyword] = 1.0 if recent > 0 else 0

    def get_trending_keywords(self, limit: int = 10) -> List[Tuple[str, float]]:
        """获取上升最快的关键词"""
        sorted_trends = sorted(
            self.trend_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_trends[:limit]

    def recommend(
        self,
        opportunities: List[Dict[str, Any]],
        limit: int = 10
    ) -> List[Tuple[Dict, float, str]]:
        """
        基于趋势推荐上升领域的商机
        """
        recommendations = []

        for opp in opportunities:
            # 获取商机相关关键词
            keywords = opp.get("tags", []) + [opp.get("industry", "")]

            # 计算最高趋势分数
            max_trend = max(
                (self.trend_scores.get(kw, 0) for kw in keywords),
                default=0
            )

            if max_trend > 0.1:  # 趋势阈值
                trending_kws = [kw for kw in keywords if self.trend_scores.get(kw, 0) > 0.1]
                reason = f"上升趋势领域：{', '.join(trending_kws)}"
                recommendations.append((opp, max_trend, reason))

        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:limit]


class RecommendationEngine:
    """
    智能推荐引擎主类

    整合多种推荐策略，提供统一的推荐接口
    """

    def __init__(self):
        self.content_recommender = ContentBasedRecommender()
        self.collaborative_recommender = CollaborativeFilterRecommender()
        self.kg_recommender = KnowledgeGraphRecommender()
        self.trend_recommender = TrendDrivenRecommender()

        # 推荐策略权重
        self.strategy_weights = {
            RecommendationType.CONTENT_BASED: 0.35,
            RecommendationType.COLLABORATIVE: 0.25,
            RecommendationType.KNOWLEDGE_GRAPH: 0.20,
            RecommendationType.TREND_DRIVEN: 0.20,
        }

        # 推荐历史
        self.recommendation_history: Dict[str, List[Recommendation]] = defaultdict(list)

    def add_user_interaction(
        self,
        user_id: str,
        opportunity_id: str,
        interaction_type: str = "view"
    ):
        """添加用户交互记录"""
        self.collaborative_recommender.add_interaction(user_id, opportunity_id)

    def update_user_preference(
        self,
        user_id: str,
        preferences: Dict[str, Any]
    ) -> UserPreference:
        """更新用户偏好"""
        return UserPreference(
            user_id=user_id,
            preferred_industries=preferences.get("preferred_industries", []),
            preferred_keywords=preferences.get("preferred_keywords", []),
            preferred_opportunity_types=preferences.get("preferred_opportunity_types", []),
            min_confidence=preferences.get("min_confidence", 0.5),
            min_value=preferences.get("min_value", 0),
            risk_tolerance=preferences.get("risk_tolerance", 0.5),
        )

    def recommend(
        self,
        user_preference: UserPreference,
        opportunities: List[Dict[str, Any]],
        limit: int = 10,
        enable_strategies: Optional[List[RecommendationType]] = None
    ) -> List[Recommendation]:
        """
        生成推荐列表

        Args:
            user_preference: 用户偏好
            opportunities: 候选商机池
            limit: 推荐数量
            enable_strategies: 启用的推荐策略（默认全部）

        Returns:
            推荐列表
        """
        if enable_strategies is None:
            enable_strategies = list(self.strategy_weights.keys())

        all_recommendations = []

        # 1. 基于内容的推荐
        if RecommendationType.CONTENT_BASED in enable_strategies:
            content_recs = self.content_recommender.recommend(
                opportunities, user_preference, limit=limit * 2
            )
            for opp, score, factors in content_recs:
                all_recommendations.append(
                    Recommendation(
                        opportunity_id=opp["id"],
                        user_id=user_preference.user_id,
                        recommendation_type=RecommendationType.CONTENT_BASED,
                        score=score,
                        reason="; ".join(factors),
                        opportunity_data=opp,
                        explained_factors=factors
                    )
                )

        # 2. 协同过滤推荐
        if RecommendationType.COLLABORATIVE in enable_strategies:
            collab_recs = self.collaborative_recommender.recommend(
                user_preference.user_id, opportunities, limit=limit * 2
            )
            for opp, score, reason in collab_recs:
                all_recommendations.append(
                    Recommendation(
                        opportunity_id=opp["id"],
                        user_id=user_preference.user_id,
                        recommendation_type=RecommendationType.COLLABORATIVE,
                        score=score,
                        reason=reason,
                        opportunity_data=opp,
                        explained_factors=[reason]
                    )
                )

        # 3. 趋势驱动推荐
        if RecommendationType.TREND_DRIVEN in enable_strategies:
            trend_recs = self.trend_recommender.recommend(
                opportunities, limit=limit * 2
            )
            for opp, score, reason in trend_recs:
                all_recommendations.append(
                    Recommendation(
                        opportunity_id=opp["id"],
                        user_id=user_preference.user_id,
                        recommendation_type=RecommendationType.TREND_DRIVEN,
                        score=score,
                        reason=reason,
                        opportunity_data=opp,
                        explained_factors=[reason]
                    )
                )

        # 去重和融合
        seen_ids = set()
        final_recommendations = []

        for rec in all_recommendations:
            if rec.opportunity_id not in seen_ids:
                # 应用策略权重
                rec.score *= self.strategy_weights.get(rec.recommendation_type, 0.25)
                final_recommendations.append(rec)
                seen_ids.add(rec.opportunity_id)

        # 按分数排序
        final_recommendations.sort(key=lambda x: x.score, reverse=True)

        # 记录历史
        self.recommendation_history[user_preference.user_id].extend(final_recommendations[:limit])

        return final_recommendations[:limit]

    def explain_recommendation(self, recommendation: Recommendation) -> str:
        """生成推荐解释"""
        explanations = []

        if recommendation.recommendation_type == RecommendationType.CONTENT_BASED:
            explanations.append(f"基于您的偏好：{recommendation.reason}")
        elif recommendation.recommendation_type == RecommendationType.COLLABORATIVE:
            explanations.append(f"相似用户也感兴趣：{recommendation.reason}")
        elif recommendation.recommendation_type == RecommendationType.TREND_DRIVEN:
            explanations.append(f"趋势上升：{recommendation.reason}")
        elif recommendation.recommendation_type == RecommendationType.KNOWLEDGE_GRAPH:
            explanations.append(f"关联发现：{recommendation.reason}")

        # 添加商机自身因素
        opp = recommendation.opportunity_data
        if opp.get("confidence_score", 0) > 0.7:
            explanations.append(f"高置信度：{opp['confidence_score']:.0%}")
        if opp.get("potential_value", 0) > 1000000:
            explanations.append(f"高价值：{opp['potential_value']:,.0f}")

        return "; ".join(explanations)

    def get_recommendation_stats(self, user_id: str) -> Dict[str, Any]:
        """获取推荐统计"""
        history = self.recommendation_history.get(user_id, [])

        if not history:
            return {"total": 0}

        type_counts = defaultdict(int)
        for rec in history:
            type_counts[rec.recommendation_type.value] += 1

        return {
            "total": len(history),
            "by_type": dict(type_counts),
            "latest": history[-1].created_at.isoformat() if history else None
        }


# 全局单例
recommendation_engine = RecommendationEngine()
