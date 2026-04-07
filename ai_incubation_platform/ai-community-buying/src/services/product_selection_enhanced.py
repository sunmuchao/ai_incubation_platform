"""
AI 选品顾问增强服务

基于协同过滤、社区画像、季节性因子的智能选品推荐系统
"""
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict
import math
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from models.entities import (
    ProductEntity, GroupBuyEntity, ProductRecommendationEntity
)

logger = logging.getLogger(__name__)


# ========== 季节性因子配置 ==========

SEASONAL_FACTORS = {
    # 春季 (3-5 月)
    "spring": {
        "categories": ["水果", "蔬菜", "鲜花", "茶饮料"],
        "keywords": ["草莓", "樱花", "春笋", "青团", "春茶"],
        "factor": 1.2  # 推荐权重提升 20%
    },
    # 夏季 (6-8 月)
    "summer": {
        "categories": ["冷饮", "水果", "防晒", "凉席"],
        "keywords": ["西瓜", "冰淇淋", "遮阳", "空调", "凉面"],
        "factor": 1.2
    },
    # 秋季 (9-11 月)
    "autumn": {
        "categories": ["坚果", "大闸蟹", "月饼", "火锅"],
        "keywords": ["螃蟹", "月饼", "栗子", "火锅", "枸杞"],
        "factor": 1.2
    },
    # 冬季 (12-2 月)
    "winter": {
        "categories": ["火锅", "暖宝宝", "热饮", "保暖"],
        "keywords": ["火锅", "暖宝宝", "热巧克力", "围巾", "手套"],
        "factor": 1.2
    }
}

# 节假日因子
HOLIDAY_FACTORS = {
    "春节": {"days_range": 15, "categories": ["年货", "零食", "酒水"], "factor": 1.5},
    "元宵": {"days_range": 3, "categories": ["汤圆", "零食"], "factor": 1.3},
    "清明": {"days_range": 3, "categories": ["鲜花", "祭品"], "factor": 1.2},
    "端午": {"days_range": 3, "categories": ["粽子", "酒水"], "factor": 1.3},
    "中秋": {"days_range": 5, "categories": ["月饼", "酒水", "水果"], "factor": 1.4},
    "国庆": {"days_range": 7, "categories": ["零食", "酒水", "旅游用品"], "factor": 1.3},
    "双 11": {"days_range": 5, "categories": ["全品类"], "factor": 1.2},
    "圣诞": {"days_range": 5, "categories": ["零食", "礼品", "苹果"], "factor": 1.2},
}


class CommunityProfile:
    """社区画像数据"""

    def __init__(self, community_id: str):
        self.community_id = community_id
        self.category_preferences: Dict[str, float] = defaultdict(float)  # 品类偏好
        self.price_range_preference: Dict[str, float] = {
            "low": 0.0,    # 0-30 元
            "mid": 0.0,    # 30-80 元
            "high": 0.0    # 80 元+
        }
        self.brand_preferences: Dict[str, float] = defaultdict(float)
        self.avg_order_value: float = 0.0
        self.purchase_frequency: float = 0.0  # 周均购买次数
        self.active_user_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "community_id": self.community_id,
            "category_preferences": dict(self.category_preferences),
            "price_range_preference": self.price_range_preference,
            "brand_preferences": dict(self.brand_preferences),
            "avg_order_value": self.avg_order_value,
            "purchase_frequency": self.purchase_frequency,
            "active_user_count": self.active_user_count
        }


class CollaborativeFilteringEngine:
    """协同过滤推荐引擎"""

    def __init__(self):
        # 用户 - 商品评分矩阵：user_id -> {product_id: score}
        self.user_item_matrix: Dict[str, Dict[str, float]] = defaultdict(dict)
        # 商品相似度矩阵：product_id -> {product_id: similarity}
        self.item_similarity: Dict[str, Dict[str, float]] = defaultdict(dict)
        # 用户相似度矩阵：user_id -> {user_id: similarity}
        self.user_similarity: Dict[str, Dict[str, float]] = defaultdict(dict)

    def add_user_interaction(self, user_id: str, product_id: str, interaction_type: str, value: float = 1.0):
        """添加用户交互数据"""
        # 交互类型权重
        interaction_weights = {
            "purchase": 5.0,      # 购买权重最高
            "wishlist": 2.0,       # 收藏
            "view": 0.5,           # 浏览
            "share": 1.5,          # 分享
            "review": 3.0          # 评价
        }

        weight = interaction_weights.get(interaction_type, 1.0)
        score = self.user_item_matrix[user_id].get(product_id, 0.0)
        self.user_item_matrix[user_id][product_id] = score + (weight * value)

    def calculate_item_similarity(self):
        """计算商品间的余弦相似度"""
        # 获取所有商品 ID
        all_items = set()
        for user_items in self.user_item_matrix.values():
            all_items.update(user_items.keys())

        items = list(all_items)
        for i, item1 in enumerate(items):
            for item2 in items[i+1:]:
                # 计算共同评分的用户集合
                common_users = []
                for user_id, user_items in self.user_item_matrix.items():
                    if item1 in user_items and item2 in user_items:
                        common_users.append(user_id)

                if len(common_users) < 2:
                    continue

                # 余弦相似度计算
                vec1 = [self.user_item_matrix[uid][item1] for uid in common_users]
                vec2 = [self.user_item_matrix[uid][item2] for uid in common_users]

                dot_product = sum(a * b for a, b in zip(vec1, vec2))
                norm1 = math.sqrt(sum(a * a for a in vec1))
                norm2 = math.sqrt(sum(b * b for b in vec2))

                if norm1 > 0 and norm2 > 0:
                    similarity = dot_product / (norm1 * norm2)
                    self.item_similarity[item1][item2] = similarity
                    self.item_similarity[item2][item1] = similarity

    def recommend_by_item_cf(self, user_id: str, product_id: str, limit: int = 5) -> List[Tuple[str, float]]:
        """基于商品的协同过滤推荐"""
        if product_id not in self.item_similarity:
            return []

        recommendations = []
        for similar_item, similarity in self.item_similarity[product_id].items():
            # 排除用户已经交互过的商品
            if similar_item in self.user_item_matrix.get(user_id, {}):
                continue
            recommendations.append((similar_item, similarity))

        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:limit]

    def recommend_by_user_cf(self, user_id: str, limit: int = 5) -> List[Tuple[str, float]]:
        """基于用户的协同过滤推荐"""
        if user_id not in self.user_similarity:
            return []

        # 找到相似用户喜欢的商品
        item_scores = defaultdict(float)
        for similar_user, similarity in self.user_similarity[user_id].items():
            if similar_user == user_id:
                continue
            for item_id, score in self.user_item_matrix[similar_user].items():
                if item_id not in self.user_item_matrix.get(user_id, {}):
                    item_scores[item_id] += similarity * score

        recommendations = [(item_id, score) for item_id, score in item_scores.items()]
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:limit]


class SeasonalFactorEngine:
    """季节性和节假日因子引擎"""

    @staticmethod
    def get_current_season() -> str:
        """获取当前季节"""
        month = datetime.now().month
        if month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        elif month in [9, 10, 11]:
            return "autumn"
        else:
            return "winter"

    @staticmethod
    def get_seasonal_factor(category: str = None, keywords: List[str] = None) -> float:
        """获取季节性因子"""
        current_season = SeasonalFactorEngine.get_current_season()
        season_config = SEASONAL_FACTORS.get(current_season, {})

        factor = 1.0

        # 检查品类匹配
        if category and category in season_config.get("categories", []):
            factor = max(factor, season_config["factor"])

        # 检查关键词匹配
        if keywords:
            for keyword in keywords:
                if keyword in season_config.get("keywords", []):
                    factor = max(factor, season_config["factor"])

        return factor

    @staticmethod
    def get_holiday_factor() -> Tuple[float, Optional[str]]:
        """获取节假日因子"""
        today = datetime.now()

        # 简化的节假日计算（实际应该使用节假日库）
        holidays = [
            ("春节", 1, 1),
            ("元宵", 1, 15),
            ("端午", 5, 5),
            ("中秋", 8, 15),
            ("国庆", 10, 1),
            ("双 11", 11, 11),
            ("圣诞", 12, 25),
        ]

        for holiday_name, month, day in holidays:
            holiday_date = datetime(today.year, month, day)
            days_diff = abs((today - holiday_date).days)

            if days_diff <= HOLIDAY_FACTORS[holiday_name]["days_range"]:
                return HOLIDAY_FACTORS[holiday_name]["factor"], holiday_name

        return 1.0, None


class ProductSelectionEnhancedService:
    """AI 选品顾问增强服务"""

    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session
        self.cf_engine = CollaborativeFilteringEngine()
        self.community_profiles: Dict[str, CommunityProfile] = {}

    def load_interaction_data(self, db: Session):
        """从数据库加载用户交互数据"""
        # 加载历史团购数据构建用户 - 商品矩阵
        group_buys = db.query(GroupBuyEntity).all()

        for gb in group_buys:
            # 将参团用户与商品的交互记录加入矩阵
            # 这里简化处理，实际应该从订单表获取
            pass

    def load_or_create_community_profile(self, db: Session, community_id: str) -> CommunityProfile:
        """加载或创建社区画像"""
        if community_id in self.community_profiles:
            return self.community_profiles[community_id]

        profile = CommunityProfile(community_id)

        # 从数据库统计社区偏好
        # 注：GroupBuyEntity 目前没有 community_id 字段，这里简化处理
        # 实际应该从订单或团购记录中按社区统计
        # 暂时使用默认偏好
        profile.category_preferences["水果"] = 5.0
        profile.category_preferences["蔬菜"] = 3.0
        profile.category_preferences["生鲜"] = 4.0
        profile.price_range_preference["mid"] = 0.5
        profile.price_range_preference["low"] = 0.3
        profile.price_range_preference["high"] = 0.2
        profile.active_user_count = 100
        profile.purchase_frequency = 3.5
        profile.avg_order_value = 50.0

        self.community_profiles[community_id] = profile
        return profile

    def get_ai_recommendations(
        self,
        community_id: str,
        limit: int = 10,
        user_id: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        获取 AI 智能选品推荐

        Args:
            community_id: 社区 ID
            limit: 返回数量限制
            user_id: 可选的用户 ID，用于个性化推荐
            filters: 可选的过滤条件 {category, price_range, ...}

        Returns:
            推荐商品列表，包含推荐理由和置信度
        """
        db = self.db

        if not db:
            return self._get_mock_recommendations(community_id, limit)

        # 1. 加载社区画像
        profile = self.load_or_create_community_profile(db, community_id)

        # 2. 获取所有活跃商品
        query = db.query(ProductEntity).filter(
            ProductEntity.status == "active",
            ProductEntity.stock > 0
        )

        # 应用过滤
        if filters:
            if filters.get("category"):
                query = query.filter(ProductEntity.category == filters["category"])
            if filters.get("price_min") is not None:
                query = query.filter(ProductEntity.price >= filters["price_min"])
            if filters.get("price_max") is not None:
                query = query.filter(ProductEntity.price <= filters["price_max"])

        products = query.all()

        # 3. 计算每个商品的推荐分数
        scored_products = []
        for product in products:
            score, reasons, confidence = self._calculate_product_score(
                product, profile, community_id, user_id
            )

            # 应用过滤
            if filters and filters.get("min_score") and score < filters["min_score"]:
                continue

            scored_products.append({
                "product": product,
                "score": score,
                "reasons": reasons,
                "confidence": confidence
            })

        # 4. 排序并返回
        scored_products.sort(key=lambda x: x["score"], reverse=True)

        return scored_products[:limit]

    def _calculate_product_score(
        self,
        product: ProductEntity,
        profile: CommunityProfile,
        community_id: str,
        user_id: Optional[str] = None
    ) -> Tuple[float, List[str], float]:
        """
        计算商品推荐分数

        Returns:
            (总分，推荐理由列表，置信度)
        """
        score = 0.0
        reasons = []
        confidence_factors = []

        # === 1. 社区偏好匹配度 (权重 30%) ===
        category = product.category or self._infer_category(product.name, product.description)
        category_pref = profile.category_preferences.get(category, 0.0)
        total_pref = sum(profile.category_preferences.values()) or 1.0
        category_match = (category_pref / total_pref) * 30
        score += category_match
        if category_match > 15:
            reasons.append(f"{category}品类热门")
        confidence_factors.append(0.8)

        # === 2. 价格区间匹配度 (权重 15%) ===
        price_range = self._get_price_range(product.price)
        price_pref = profile.price_range_preference.get(price_range, 0.33)
        price_match = price_pref * 15
        score += price_match
        confidence_factors.append(0.7)

        # === 3. 季节性因子 (权重 20%) ===
        seasonal_factor = SeasonalFactorEngine.get_seasonal_factor(
            category=category,
            keywords=[product.name, product.description]
        )
        seasonal_score = 20 * (seasonal_factor / 1.2)
        score += seasonal_score
        if seasonal_factor > 1.1:
            reasons.append("当季热销")
        confidence_factors.append(0.9)

        # === 4. 节假日因子 (权重 10%) ===
        holiday_factor, holiday_name = SeasonalFactorEngine.get_holiday_factor()
        if holiday_factor > 1.0:
            holiday_score = 10 * (holiday_factor / 1.5)
            score += holiday_score
            reasons.append(f"{holiday_name}特惠")
        confidence_factors.append(0.85)

        # === 5. 销量和热度 (权重 15%) ===
        # 查询该商品的团购数量和参团人数
        if self.db:
            group_stats = self.db.query(
                func.count(GroupBuyEntity.id),
                func.sum(GroupBuyEntity.current_size)
            ).filter(
                GroupBuyEntity.product_id == product.id,
                GroupBuyEntity.status == "success"
            ).first()

            if group_stats and group_stats[0]:
                sales_score = min(15, math.log(group_stats[0] + 1) * 3)
                score += sales_score
                if group_stats[0] > 10:
                    reasons.append(f"已成团{group_stats[0]}次")
                confidence_factors.append(0.75)

        # === 6. 协同过滤推荐 (权重 10%) ===
        if user_id and user_id in self.cf_engine.user_item_matrix:
            cf_recs = self.cf_engine.recommend_by_item_cf(user_id, product.id)
            if cf_recs:
                cf_score = 10 * cf_recs[0][1]
                score += cf_score
                reasons.append("相似用户也喜欢")
                confidence_factors.append(0.6)

        # 计算置信度
        confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5

        return round(score, 2), reasons, round(confidence, 2)

    def _infer_category(self, name: str, description: str = "") -> str:
        """推断商品类别"""
        text = (name + " " + description).lower()

        category_keywords = {
            "水果": ["草莓", "车厘子", "苹果", "香蕉", "橙", "葡萄", "西瓜", "梨"],
            "蔬菜": ["白菜", "萝卜", "西红柿", "黄瓜", "土豆", "青菜"],
            "生鲜": ["肉", "鱼", "虾", "蛋", "奶", "牛肉", "猪肉"],
            "零食": ["饼干", "巧克力", "糖果", "薯片", "坚果"],
            "酒水": ["啤酒", "白酒", "红酒", "饮料"],
            "日用": ["纸巾", "洗衣液", "洗发水", "沐浴露"],
            "火锅": ["火锅", "底料", "丸子"],
            "冷饮": ["冰淇淋", "雪糕", "冰棒"],
        }

        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return category
        return "其他"

    def _get_price_range(self, price: float) -> str:
        """获取价格区间"""
        if price < 30:
            return "low"
        elif price < 80:
            return "mid"
        else:
            return "high"

    def _get_mock_recommendations(self, community_id: str, limit: int) -> List[Dict]:
        """返回模拟推荐（无数据库时）"""
        current_season = SeasonalFactorEngine.get_current_season()
        holiday_factor, holiday_name = SeasonalFactorEngine.get_holiday_factor()

        mock_products = [
            {"name": "新鲜草莓", "price": 29.9, "category": "水果", "season": "spring"},
            {"name": "冰镇西瓜", "price": 39.9, "category": "水果", "season": "summer"},
            {"name": "阳澄湖大闸蟹", "price": 199.0, "category": "生鲜", "season": "autumn"},
            {"name": "火锅套餐", "price": 89.0, "category": "火锅", "season": "winter"},
            {"name": "有机鸡蛋", "price": 25.9, "category": "生鲜", "season": "all"},
            {"name": "进口牛奶", "price": 59.0, "category": "乳品", "season": "all"},
        ]

        recommendations = []
        for prod in mock_products:
            if prod["season"] in [current_season, "all"]:
                reasons = []
                score = 80.0

                if prod["season"] == current_season:
                    reasons.append(f"当季{current_season}热销")
                    score += 10

                if holiday_name:
                    reasons.append(f"{holiday_name}特惠")
                    score += 5

                recommendations.append({
                    "product": type('obj', (object,), {
                        "id": f"mock_{prod['name']}",
                        "name": prod["name"],
                        "price": prod["price"],
                        "category": prod["category"]
                    })(),
                    "score": score,
                    "reasons": reasons,
                    "confidence": 0.7
                })

        recommendations.sort(key=lambda x: x["score"], reverse=True)
        return recommendations[:limit]

    def record_user_interaction(
        self,
        user_id: str,
        product_id: str,
        interaction_type: str,
        value: float = 1.0
    ):
        """记录用户交互用于协同过滤"""
        self.cf_engine.add_user_interaction(user_id, product_id, interaction_type, value)

    def update_community_profile(self, community_id: str, category: str, delta: float):
        """更新社区品类偏好"""
        if community_id not in self.community_profiles:
            self.community_profiles[community_id] = CommunityProfile(community_id)

        self.community_profiles[community_id].category_preferences[category] += delta


# 全局服务实例
product_selection_service = ProductSelectionEnhancedService()
