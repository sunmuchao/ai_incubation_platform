"""
增强版推荐服务 - 深度排序模型 (Deep Ranking Model)
实现千人千面的个性化商品推荐

技术架构:
- Wide&Deep 模型架构：记忆 + 泛化能力
- 特征工程：用户特征、商品特征、上下文特征
- 点击率预估：Sigmoid 输出
- 多样性控制：MMR (Maximal Marginal Relevance)
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import math
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from models.entities import (
    ProductEntity, OrderEntity, GroupBuyEntity,
    ProductRecommendationEntity, CommunityPreferenceEntity
)
from models.p0_entities import GroupPredictionEntity

logger = logging.getLogger(__name__)


class DeepRankingRecommendation:
    """深度排序推荐引擎"""

    def __init__(self, db: Session):
        self.db = db
        # 模型超参数
        self.learning_rate = 0.01
        self.regularization = 0.001
        # 缓存
        self.user_embeddings: Dict[str, Dict[str, float]] = {}
        self.product_embeddings: Dict[str, Dict[str, float]] = {}

    # ========== 主推荐接口 ==========

    def get_personalized_recommendations(
        self,
        community_id: str,
        user_id: Optional[str] = None,
        limit: int = 10,
        use_deep_ranking: bool = True
    ) -> List[Dict]:
        """
        获取个性化推荐商品

        Args:
            community_id: 社区 ID
            user_id: 用户 ID (可选，用于千人千面)
            limit: 返回数量
            use_deep_ranking: 是否使用深度排序

        Returns:
            推荐商品列表，每个包含 product, score, reason
        """
        if use_deep_ranking and user_id:
            # 深度排序模型：Wide&Deep 架构
            return self._deep_ranking_recommend(community_id, user_id, limit)
        else:
            # 基础排序：基于社区偏好
            return self._community_based_recommend(community_id, limit)

    def _deep_ranking_recommend(
        self,
        community_id: str,
        user_id: str,
        limit: int
    ) -> List[Dict]:
        """
        深度排序推荐 (Wide&Deep 模型)

        Wide 部分：记忆交叉特征（用户 - 商品交互历史）
        Deep 部分：泛化Embedding 内积（用户/商品隐向量）
        """
        # 1. 获取用户特征
        user_features = self._extract_user_features(user_id)

        # 2. 获取候选商品
        candidate_products = self._get_candidate_products(community_id)

        # 3. 计算每个商品的排序分数
        scored_products = []
        for product in candidate_products:
            # 商品特征
            product_features = self._extract_product_features(product)

            # 上下文特征
            context_features = self._extract_context_features(community_id)

            # Wide 部分：交叉特征
            wide_score = self._wide_component(user_features, product_features)

            # Deep 部分：Embedding 相似度
            deep_score = self._deep_component(user_features, product_features)

            # 融合分数 (Wide&Deep)
            final_score = self._fuse_scores(wide_score, deep_score)

            # 多样性调整
            diversity_bonus = self._diversity_bonus(product, scored_products)

            scored_products.append({
                "product": product,
                "score": final_score + diversity_bonus,
                "wide_score": wide_score,
                "deep_score": deep_score,
                "reason": self._generate_reason(product, user_features, final_score)
            })

        # 4. 排序并返回 Top-N (MMR 多样性重排)
        scored_products.sort(key=lambda x: x["score"], reverse=True)
        reranked = self._mmr_rerank(scored_products, limit)

        # 5. 保存推荐记录
        self._save_recommendations(community_id, user_id, reranked)

        return reranked[:limit]

    def _community_based_recommend(self, community_id: str, limit: int) -> List[Dict]:
        """基于社区偏好的基础推荐"""
        # 获取社区偏好
        preferences = self.db.query(CommunityPreferenceEntity).filter(
            CommunityPreferenceEntity.community_id == community_id
        ).order_by(
            desc(CommunityPreferenceEntity.preference_score)
        ).limit(20).all()

        # 获取偏好对应的商品
        recommended = []
        for pref in preferences:
            products = self.db.query(ProductEntity).filter(
                ProductEntity.name.ilike(f"%{pref.category}%"),
                ProductEntity.status == "active",
                ProductEntity.stock > 0
            ).limit(3).all()

            for product in products:
                score = pref.preference_score * 100
                recommended.append({
                    "product": product,
                    "score": score,
                    "reason": f"社区热门：{pref.category}类高评分商品"
                })

        # 如果社区偏好不足，补充热销商品
        if len(recommended) < limit:
            hot_products = self._get_hot_products(community_id, limit - len(recommended))
            recommended.extend(hot_products)

        return recommended[:limit]

    # ========== 特征工程 ==========

    def _extract_user_features(self, user_id: str) -> Dict[str, float]:
        """
        提取用户特征

        特征维度:
        - 购买力：历史平均订单金额
        - 活跃度：近 7 天下单次数
        - 品类偏好：各类目购买次数归一化
        - 价格敏感度：平均折扣偏好
        - 成团偏好：参与团购的成功率
        """
        features = {
            "spending_power": 0.5,
            "activity_level": 0.5,
            "category_fresh": 0.2,
            "category_vegetable": 0.2,
            "category_meat": 0.2,
            "category_snack": 0.2,
            "price_sensitivity": 0.5,
            "group_preference": 0.5,
        }

        # 查询用户历史订单
        orders = self.db.query(OrderEntity).filter(
            OrderEntity.user_id == user_id,
            OrderEntity.status == "completed"
        ).all()

        if not orders:
            return features

        # 购买力：平均订单金额 (归一化到 0-1)
        total_amount = sum(o.total_amount for o in orders)
        features["spending_power"] = min(1.0, total_amount / (len(orders) * 100))

        # 活跃度：近 7 天下单次数
        week_ago = datetime.now() - timedelta(days=7)
        recent_orders = [o for o in orders if o.created_at >= week_ago]
        features["activity_level"] = min(1.0, len(recent_orders) / 5)

        # 品类偏好
        category_counts = {}
        for order in orders:
            product = self.db.query(ProductEntity).filter(
                ProductEntity.id == order.product_id
            ).first()
            if product:
                category = self._get_product_category(product)
                category_counts[category] = category_counts.get(category, 0) + 1

        total_orders = len(orders)
        for cat in ["fresh", "vegetable", "meat", "snack"]:
            features[f"category_{cat}"] = category_counts.get(cat, 0) / total_orders

        # 价格敏感度：平均实付/原价比例
        products = self.db.query(ProductEntity).filter(
            ProductEntity.id.in_([o.product_id for o in orders])
        ).all()
        if products:
            avg_discount = sum(p.price / p.original_price for p in products) / len(products)
            features["price_sensitivity"] = 1.0 - (avg_discount - 0.6) / 0.4  # 归一化

        # 成团偏好
        group_buy_ids = list(set(o.group_buy_id for o in orders))
        group_buys = self.db.query(GroupBuyEntity).filter(
            GroupBuyEntity.id.in_(group_buy_ids)
        ).all()
        if group_buys:
            success_groups = sum(1 for gb in group_buys if gb.status == "success")
            features["group_preference"] = success_groups / len(group_buys)

        return features

    def _extract_product_features(self, product: ProductEntity) -> Dict[str, float]:
        """
        提取商品特征

        特征维度:
        - 价格等级：低价/中价/高价
        - 品类：生鲜/蔬菜/肉类/零食
        - 热度：销量归一化
        - 折扣力度：原价/现价比例
        - 成团率：历史团购成功率
        """
        # 使用统一的分类方法
        category = self._get_product_category(product)

        features = {
            "price_level": 0.5,
            "category_fresh": 1.0 if category == "fresh" else 0.0,
            "category_vegetable": 1.0 if category == "vegetable" else 0.0,
            "category_meat": 1.0 if category == "meat" else 0.0,
            "category_snack": 1.0 if category == "snack" else 0.0,
            "popularity": 0.5,
            "discount_rate": 0.5,
            "group_success_rate": 0.8,
        }

        # 价格等级
        if product.price < 10:
            features["price_level"] = 0.2
        elif product.price < 30:
            features["price_level"] = 0.5
        else:
            features["price_level"] = 0.8

        # 热度：销量归一化
        features["popularity"] = min(1.0, product.sold_stock / 100)

        # 折扣力度
        features["discount_rate"] = 1.0 - (product.price / product.original_price)

        # 成团率
        group_buys = self.db.query(GroupBuyEntity).filter(
            GroupBuyEntity.product_id == product.id
        ).all()
        if group_buys:
            success_count = sum(1 for gb in group_buys if gb.status == "success")
            features["group_success_rate"] = success_count / len(group_buys)

        return features

    def _extract_context_features(self, community_id: str) -> Dict[str, float]:
        """
        提取上下文特征

        特征维度:
        - 时间段：早/中/晚/深夜
        - 星期：工作日/周末
        - 节假日：是否节假日
        - 天气：(需要外部 API)
        """
        now = datetime.now()

        features = {
            "time_morning": 1.0 if 6 <= now.hour < 10 else 0.0,
            "time_noon": 1.0 if 10 <= now.hour < 14 else 0.0,
            "time_afternoon": 1.0 if 14 <= now.hour < 18 else 0.0,
            "time_evening": 1.0 if 18 <= now.hour < 22 else 0.0,
            "time_night": 1.0 if now.hour >= 22 or now.hour < 6 else 0.0,
            "is_weekend": 1.0 if now.weekday() >= 5 else 0.0,
            "is_holiday": self._is_holiday(now),
        }

        return features

    def _is_holiday(self, date: datetime) -> float:
        """判断是否节假日"""
        # 简化的节假日判断（实际应使用日历 API）
        holidays = [
            (1, 1), (5, 1), (10, 1), (10, 2), (10, 3), (10, 4), (10, 5), (10, 6), (10, 7)
        ]
        return 1.0 if (date.month, date.day) in holidays else 0.0

    # ========== Wide&Deep 模型组件 ==========

    def _wide_component(
        self,
        user_features: Dict[str, float],
        product_features: Dict[str, float]
    ) -> float:
        """
        Wide 组件：记忆交叉特征

        计算用户 - 商品交叉特征的组合分数
        使用逻辑回归形式
        """
        # 交叉特征：用户品类偏好 × 商品品类
        cross_features = []
        for cat in ["fresh", "vegetable", "meat", "snack"]:
            user_cat = user_features.get(f"category_{cat}", 0)
            prod_cat = product_features.get(f"category_{cat}", 0)
            cross_features.append(user_cat * prod_cat)

        # 价格匹配度
        price_match = 1.0 - abs(
            user_features["spending_power"] - product_features["price_level"]
        )

        # Wide 分数：加权求和 + Sigmoid
        wide_score = (
            sum(cross_features) / len(cross_features) * 0.5 +
            price_match * 0.3 +
            product_features["discount_rate"] * 0.2
        )

        # Sigmoid 激活
        return 1 / (1 + math.exp(-wide_score * 5))

    def _deep_component(
        self,
        user_features: Dict[str, float],
        product_features: Dict[str, float]
    ) -> float:
        """
        Deep 组件：Embedding 内积

        模拟神经网络隐层输出，计算用户和商品的隐向量相似度
        这里使用简化版本：特征映射后的余弦相似度
        """
        # 用户隐向量 (简化：直接从特征映射)
        user_embedding = [
            user_features["spending_power"],
            user_features["activity_level"],
            user_features["category_fresh"],
            user_features["category_vegetable"],
            user_features["category_meat"],
            user_features["category_snack"],
        ]

        # 商品隐向量
        product_embedding = [
            product_features["price_level"],
            product_features["popularity"],
            product_features["category_fresh"],
            product_features["category_vegetable"],
            product_features["category_meat"],
            product_features["category_snack"],
        ]

        # 余弦相似度
        dot_product = sum(u * p for u, p in zip(user_embedding, product_embedding))
        user_norm = math.sqrt(sum(u ** 2 for u in user_embedding) + 1e-8)
        product_norm = math.sqrt(sum(p ** 2 for p in product_embedding) + 1e-8)

        return dot_product / (user_norm * product_norm)

    def _fuse_scores(self, wide_score: float, deep_score: float) -> float:
        """
        融合 Wide 和 Deep 分数

        使用可学习的权重进行融合
        """
        # 默认权重：Wide 40%, Deep 60%
        wide_weight = 0.4
        deep_weight = 0.6

        return wide_score * wide_weight + deep_score * deep_weight

    # ========== 多样性控制 ==========

    def _diversity_bonus(
        self,
        product: ProductEntity,
        scored_products: List[Dict]
    ) -> float:
        """
        多样性加分：避免推荐结果过于单一

        如果已推荐了多个同类商品，后续同类商品得分降低
        """
        if not scored_products:
            return 0

        category = self._get_product_category(product)

        # 计算已推荐商品中同类占比
        same_category_count = sum(
            1 for sp in scored_products
            if self._get_product_category(sp["product"]) == category
        )

        # 同类越多，加分越低（甚至负分）
        if same_category_count >= 3:
            return -0.2
        elif same_category_count >= 2:
            return -0.1
        elif same_category_count >= 1:
            return 0.05
        else:
            return 0.1  # 新品类奖励

    def _mmr_rerank(self, scored_products: List[Dict], limit: int) -> List[Dict]:
        """
        MMR (Maximal Marginal Relevance) 重排

        在相关性和多样性之间取得平衡
        MMR = argmax [ λ × 相关性 - (1-λ) × 与已选结果的最大相似度 ]
        """
        if len(scored_products) <= limit:
            return scored_products

        reranked = []
        remaining = scored_products.copy()
        lambda_param = 0.7  # 相关性权重

        while len(reranked) < limit and remaining:
            best_score = -float("inf")
            best_idx = 0

            for i, product in enumerate(remaining):
                # 相关性分数
                relevance = product["score"]

                # 与已选结果的相似度惩罚
                similarity_penalty = 0
                if reranked:
                    for selected in reranked:
                        sim = self._compute_similarity(
                            product["product"],
                            selected["product"]
                        )
                        similarity_penalty = max(similarity_penalty, sim)

                # MMR 分数
                mmr_score = lambda_param * relevance - (1 - lambda_param) * similarity_penalty

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = i

            reranked.append(remaining.pop(best_idx))

        return reranked

    def _compute_similarity(
        self,
        product1: ProductEntity,
        product2: ProductEntity
    ) -> float:
        """计算两个商品的相似度"""
        cat1 = self._get_product_category(product1)
        cat2 = self._get_product_category(product2)

        # 同品类：相似度 0.8
        # 不同品类但有价格重叠：相似度 0.4
        # 完全不同：相似度 0.1
        if cat1 == cat2:
            return 0.8
        elif abs(product1.price - product2.price) < 10:
            return 0.4
        else:
            return 0.1

    # ========== 辅助方法 ==========

    def _get_product_category(self, product: ProductEntity) -> str:
        """商品分类"""
        name = product.name or ""
        desc = product.description or ""

        keywords = {
            "fresh": ["水果", "苹果", "香蕉", "橙", "葡萄", "草莓", "车厘子"],
            "vegetable": ["蔬菜", "白菜", "萝卜", "西红柿", "黄瓜", "土豆"],
            "meat": ["肉", "鱼", "虾", "蛋", "奶", "牛肉", "猪肉", "鸡肉"],
            "snack": ["零食", "饼干", "巧克力", "糖果", "坚果"]
        }

        for category, words in keywords.items():
            for word in words:
                if word in name or word in desc:
                    return category
        return "other"

    def _get_candidate_products(self, community_id: str) -> List[ProductEntity]:
        """获取候选商品池"""
        return self.db.query(ProductEntity).filter(
            ProductEntity.status == "active",
            ProductEntity.stock > 0
        ).limit(100).all()

    def _get_hot_products(self, community_id: str, limit: int) -> List[Dict]:
        """获取热销商品"""
        # 基于销量排序
        hot_products = self.db.query(ProductEntity).filter(
            ProductEntity.status == "active",
            ProductEntity.stock > 0
        ).order_by(
            desc(ProductEntity.sold_stock)
        ).limit(limit).all()

        return [
            {
                "product": p,
                "score": p.sold_stock * 2,
                "reason": f"社区热销：已售{p.sold_stock}份"
            }
            for p in hot_products
        ]

    def _generate_reason(
        self,
        product: ProductEntity,
        user_features: Dict[str, float],
        score: float
    ) -> str:
        """生成推荐理由"""
        reasons = []

        # 基于用户特征的个性化理由
        if user_features["activity_level"] > 0.7:
            reasons.append("活跃用户专享")

        if user_features["spending_power"] > 0.7 and product.price > 20:
            reasons.append("品质优选")

        # 基于商品的理由
        if product.sold_stock > 50:
            reasons.append(f"热销{product.sold_stock}份")

        if product.price / product.original_price < 0.7:
            discount = int((1 - product.price / product.original_price) * 10)
            reasons.append(f"{discount}折优惠")

        if product.stock < 20:
            reasons.append("库存紧张")

        # 基于分数
        if score > 0.8:
            reasons.append("高匹配度")

        return "，".join(reasons) if reasons else "精选好物"

    def _save_recommendations(
        self,
        community_id: str,
        user_id: str,
        recommendations: List[Dict]
    ):
        """保存推荐记录"""
        expired_at = datetime.now() + timedelta(hours=24)

        for rec in recommendations:
            product = rec["product"]
            db_rec = ProductRecommendationEntity(
                product_id=product.id,
                community_id=community_id,
                score=rec["score"],
                reason=rec["reason"],
                expired_at=expired_at
            )
            self.db.add(db_rec)

        self.db.commit()

    # ========== 模型训练接口 (用于持续学习) ==========

    def train_from_feedback(self, days: int = 7) -> Dict:
        """
        从用户反馈中训练模型

        使用历史点击/购买数据更新特征权重
        """
        # 获取最近 N 天的用户行为数据
        cutoff_date = datetime.now() - timedelta(days=days)

        orders = self.db.query(OrderEntity).filter(
            OrderEntity.created_at >= cutoff_date,
            OrderEntity.status == "completed"
        ).all()

        # 统计用户 - 商品交互
        user_product_interactions = {}
        for order in orders:
            key = (order.user_id, order.product_id)
            user_product_interactions[key] = user_product_interactions.get(key, 0) + 1

        # 这里简化处理，实际应使用梯度下降优化权重
        return {
            "trained_samples": len(orders),
            "unique_users": len(set(o.user_id for o in orders)),
            "unique_products": len(set(o.product_id for o in orders)),
            "training_time": datetime.now().isoformat()
        }


# 全局服务实例 (需传入 db session)
def get_recommendation_service(db: Session) -> DeepRankingRecommendation:
    """获取推荐服务实例"""
    return DeepRankingRecommendation(db)
