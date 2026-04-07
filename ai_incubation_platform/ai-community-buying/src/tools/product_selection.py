"""
选品工具 - 基于社区需求的商品推荐

根据社区历史销售数据、季节性因素等，推荐适合的商品。
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from tools.base import BaseTool, ToolMetadata, ToolResponse


class ProductSelectionTool(BaseTool):
    """选品工具 - 基于规则的商品推荐"""

    def __init__(self, db_session: Optional[Session] = None):
        super().__init__()
        self.db = db_session

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="product_selection",
            description="基于社区需求和历史数据推荐适合的商品",
            version="1.0.0",
            tags=["recommendation", "product", "selection"],
            author="ai-community-buying"
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "community_id": {
                    "type": "string",
                    "description": "社区 ID"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回推荐数量",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50
                },
                "category": {
                    "type": "string",
                    "description": "商品类别过滤（可选）"
                },
                "price_range": {
                    "type": "object",
                    "properties": {
                        "min": {"type": "number", "description": "最低价格"},
                        "max": {"type": "number", "description": "最高价格"}
                    },
                    "description": "价格范围过滤（可选）"
                },
                "seasonal": {
                    "type": "boolean",
                    "description": "是否考虑季节性因素",
                    "default": True
                }
            },
            "required": ["community_id"]
        }

    def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResponse:
        """执行选品推荐"""
        request_id = context.get("request_id") if context else None

        community_id = params.get("community_id")
        limit = params.get("limit", 10)
        category = params.get("category")
        price_range = params.get("price_range")
        seasonal = params.get("seasonal", True)

        # 如果没有数据库连接，返回模拟数据
        if self.db is None:
            return self._get_mock_recommendations(
                community_id=community_id,
                limit=limit,
                category=category,
                price_range=price_range,
                seasonal=seasonal,
                request_id=request_id
            )

        # 从数据库获取推荐
        return self._get_db_recommendations(
            community_id=community_id,
            limit=limit,
            category=category,
            price_range=price_range,
            seasonal=seasonal,
            request_id=request_id
        )

    def _get_mock_recommendations(
        self,
        community_id: str,
        limit: int,
        category: Optional[str],
        price_range: Optional[Dict],
        seasonal: bool,
        request_id: Optional[str]
    ) -> ToolResponse:
        """生成模拟推荐数据"""
        # 模拟推荐逻辑
        current_month = datetime.now().month

        # 季节性商品映射
        seasonal_products = {
            "spring": ["春季蔬菜", "水果拼盘", "鲜花"],
            "summer": ["冷饮", "西瓜", "防晒用品"],
            "autumn": ["坚果", "大闸蟹", "月饼"],
            "winter": ["火锅食材", "暖宝宝", "热饮"]
        }

        # 根据当前月份确定季节
        if current_month in [3, 4, 5]:
            season = "spring"
        elif current_month in [6, 7, 8]:
            season = "summer"
        elif current_month in [9, 10, 11]:
            season = "autumn"
        else:
            season = "winter"

        # 基础推荐商品池
        base_products = [
            {"name": "新鲜鸡蛋", "price": 15.9, "category": "生鲜", "score": 0.95},
            {"name": "有机牛奶", "price": 59.9, "category": "乳品", "score": 0.92},
            {"name": "进口水果", "price": 39.9, "category": "生鲜", "score": 0.88},
            {"name": "精选肉类", "price": 89.9, "category": "生鲜", "score": 0.85},
        ]

        # 添加季节性商品
        if seasonal:
            for product_name in seasonal_products.get(season, []):
                base_products.append({
                    "name": product_name,
                    "price": 29.9,
                    "category": "季节性",
                    "score": 0.80
                })

        # 应用过滤
        filtered = base_products
        if category:
            filtered = [p for p in filtered if p.get("category") == category]
        if price_range:
            min_price = price_range.get("min", 0)
            max_price = price_range.get("max", float("inf"))
            filtered = [p for p in filtered if min_price <= p["price"] <= max_price]

        # 按分数排序并截取
        filtered.sort(key=lambda x: x["score"], reverse=True)
        recommendations = filtered[:limit]

        # 生成推荐理由
        for item in recommendations:
            reasons = []
            if seasonal and item.get("category") == "季节性":
                reasons.append(f"当季热门（{season}）")
            if item["score"] > 0.9:
                reasons.append("高评分商品")
            if item["price"] < 30:
                reasons.append("性价比高")
            item["reason"] = ", ".join(reasons) if reasons else "综合推荐"

        return ToolResponse.ok(
            data={
                "community_id": community_id,
                "season": season,
                "recommendations": recommendations,
                "total": len(recommendations)
            },
            request_id=request_id
        )

    def _get_db_recommendations(
        self,
        community_id: str,
        limit: int,
        category: Optional[str],
        price_range: Optional[Dict],
        seasonal: bool,
        request_id: Optional[str]
    ) -> ToolResponse:
        """从数据库获取推荐"""
        from models.entities import ProductRecommendationEntity, ProductEntity

        # 查询预计算的推荐
        recommendations = self.db.query(ProductRecommendationEntity).filter(
            ProductRecommendationEntity.community_id == community_id
        ).order_by(
            ProductRecommendationEntity.score.desc()
        ).limit(limit).all()

        if not recommendations:
            # 如果没有预计算推荐，返回模拟数据
            return self._get_mock_recommendations(
                community_id=community_id,
                limit=limit,
                category=category,
                price_range=price_range,
                seasonal=seasonal,
                request_id=request_id
            )

        result = []
        for rec in recommendations:
            product = self.db.query(ProductEntity).filter(
                ProductEntity.id == rec.product_id
            ).first()
            if product:
                result.append({
                    "product_id": rec.product_id,
                    "product_name": product.name,
                    "price": product.price,
                    "score": rec.score,
                    "reason": rec.reason or "综合推荐"
                })

        return ToolResponse.ok(
            data={
                "community_id": community_id,
                "recommendations": result,
                "total": len(result)
            },
            request_id=request_id
        )
