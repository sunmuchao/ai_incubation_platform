"""
智能推荐服务：选品推荐与动态定价
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import math
import logging
from sqlalchemy.orm import Session
from models.product import Product, ProductCreate
from models.entities import ProductEntity, ProductRecommendationEntity
from services.groupbuy_service import group_buy_service

logger = logging.getLogger(__name__)


class RecommendationService:
    """推荐服务"""

    def __init__(self):
        # 历史销量数据缓存
        self.sales_history: Dict[str, List[Dict]] = {}
        # 社区偏好数据
        self.community_preferences: Dict[str, Dict[str, float]] = {}

    def calculate_dynamic_price(self, product: Product, current_participants: int, target_size: int) -> float:
        """
        动态定价算法
        根据成团概率、当前参与人数、历史销量等因素动态调整价格
        """
        base_price = product.price
        original_price = product.original_price

        # 成团进度因子：越接近成团，价格优惠越大
        progress_factor = current_participants / target_size
        # 最低折扣为0.8，最高为原价
        discount_factor = 0.8 + 0.2 * (1 - progress_factor)

        # 历史销量因子：销量越高，价格越低
        sales_factor = 1.0
        if product.sold_stock > 0:
            sales_factor = 1.0 - min(0.1, math.log(product.sold_stock + 1) / 100)

        # 库存因子：库存越低，价格越高
        stock_factor = 1.0
        available_stock = product.stock - product.locked_stock
        if available_stock < target_size * 2:
            stock_factor = 1.0 + 0.1 * (1 - available_stock / (target_size * 2))

        # 计算最终价格
        final_price = base_price * discount_factor * sales_factor * stock_factor

        # 价格限制：不低于成本价（假设成本价为原价的60%），不高于原价
        cost_price = original_price * 0.6
        final_price = max(cost_price, min(final_price, original_price))

        return round(final_price, 2)

    def get_recommended_products(self, db: Session, community_id: str, limit: int = 10) -> List[Dict]:
        """
        获取社区推荐商品
        基于历史销量、成团率、季节因素等综合评分
        """
        # 查询所有活跃商品
        products = db.query(ProductEntity).filter(
            ProductEntity.status == "active",
            ProductEntity.stock > 0
        ).all()

        scored_products = []
        for product_entity in products:
            score = self._calculate_product_score(product_entity, community_id)
            product = Product(
                id=product_entity.id,
                name=product_entity.name,
                description=product_entity.description,
                price=product_entity.price,
                original_price=product_entity.original_price,
                image_url=product_entity.image_url,
                stock=product_entity.stock,
                locked_stock=product_entity.locked_stock,
                sold_stock=product_entity.sold_stock,
                min_group_size=product_entity.min_group_size,
                max_group_size=product_entity.max_group_size,
                status=product_entity.status,
                created_at=product_entity.created_at,
                updated_at=product_entity.updated_at
            )
            scored_products.append({
                "product": product,
                "score": score,
                "reason": self._get_recommendation_reason(score, product_entity)
            })

        # 按分数排序，取前N个
        scored_products.sort(key=lambda x: x["score"], reverse=True)
        recommendations = scored_products[:limit]

        # 保存推荐记录到数据库
        self._save_recommendations(db, community_id, recommendations)

        return recommendations

    def _calculate_product_score(self, product: ProductEntity, community_id: str) -> float:
        """计算商品推荐分数"""
        score = 0.0

        # 1. 销量权重 (40%)
        sales_score = min(1.0, product.sold_stock / 100) * 40
        score += sales_score

        # 2. 成团率权重 (30%)
        # 查询该商品的历史团购成功率
        group_buys = group_buy_service.list_group_buys_by_status("success")
        product_groups = [gb for gb in group_buys if gb.product_id == product.id]
        if product_groups:
            success_rate = len(product_groups) / max(1, len(group_buys))
            success_score = success_rate * 30
            score += success_score

        # 3. 利润率权重 (20%)
        profit_margin = (product.price - product.original_price * 0.6) / product.price
        profit_score = max(0, min(profit_margin, 0.5)) * 20
        score += profit_score

        # 4. 社区偏好权重 (10%)
        preference_score = 0.0
        if community_id in self.community_preferences:
            category = self._get_product_category(product)
            if category in self.community_preferences[community_id]:
                preference_score = self.community_preferences[community_id][category] * 10
        score += preference_score

        return round(score, 2)

    def _get_product_category(self, product: ProductEntity) -> str:
        """简单的商品分类（可扩展）"""
        # 这里可以根据商品名称或描述进行分类
        keywords = {
            "水果": ["草莓", "车厘子", "苹果", "香蕉", "橙", "葡萄"],
            "蔬菜": ["蔬菜", "白菜", "萝卜", "西红柿", "黄瓜"],
            "生鲜": ["肉", "鱼", "虾", "蛋", "奶"],
            "零食": ["零食", "饼干", "巧克力", "糖果"]
        }

        for category, words in keywords.items():
            for word in words:
                if word in product.name or word in product.description:
                    return category
        return "其他"

    def _get_recommendation_reason(self, score: float, product: ProductEntity) -> str:
        """生成推荐理由"""
        reasons = []

        if score >= 80:
            reasons.append("热销爆款")
        elif score >= 60:
            reasons.append("高性价比")

        if product.sold_stock > 50:
            reasons.append(f"已售{product.sold_stock}份")

        if product.price / product.original_price < 0.7:
            discount = int((1 - product.price / product.original_price) * 10)
            reasons.append(f"{discount}折特惠")

        return "，".join(reasons) if reasons else "优质商品"

    def _save_recommendations(self, db: Session, community_id: str, recommendations: List[Dict]):
        """保存推荐记录到数据库"""
        # 删除过期的推荐记录
        db.query(ProductRecommendationEntity).filter(
            ProductRecommendationEntity.community_id == community_id,
            ProductRecommendationEntity.expired_at < datetime.now()
        ).delete()

        # 保存新的推荐
        expired_at = datetime.now() + timedelta(hours=24)  # 推荐24小时有效
        for rec in recommendations:
            product = rec["product"]
            db_rec = ProductRecommendationEntity(
                product_id=product.id,
                community_id=community_id,
                score=rec["score"],
                reason=rec["reason"],
                expired_at=expired_at
            )
            db.add(db_rec)

        db.commit()

    def update_community_preference(self, community_id: str, category: str, score: float):
        """更新社区偏好"""
        if community_id not in self.community_preferences:
            self.community_preferences[community_id] = {}
        self.community_preferences[community_id][category] = score


# 全局服务实例
recommendation_service = RecommendationService()
