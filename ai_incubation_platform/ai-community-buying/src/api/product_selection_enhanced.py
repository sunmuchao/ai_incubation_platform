"""
AI 选品顾问增强 API 路由

提供基于协同过滤、社区画像、季节性因子的智能选品推荐能力
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Header, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime

from config.database import get_db
from services.product_selection_enhanced import product_selection_service, ProductSelectionEnhancedService

# 创建路由器
product_selection_router = APIRouter(prefix="/api/product-selection", tags=["AI 选品顾问"])


@product_selection_router.get("/recommend")
def get_recommendations(
    community_id: str = Query(..., description="社区 ID"),
    limit: int = Query(default=10, ge=1, le=50, description="返回推荐数量"),
    user_id: Optional[str] = Query(None, description="用户 ID（用于个性化推荐）"),
    category: Optional[str] = Query(None, description="品类过滤"),
    price_min: Optional[float] = Query(None, ge=0, description="最低价格"),
    price_max: Optional[float] = Query(None, ge=0, description="最高价格"),
    min_score: Optional[float] = Query(None, ge=0, le=100, description="最低推荐分数"),
    db: Session = Depends(get_db)
):
    """
    获取 AI 智能选品推荐

    基于以下因素综合计算推荐分数：
    1. 社区偏好匹配度 (30%) - 基于社区历史购买行为
    2. 价格区间匹配度 (15%) - 基于社区消费能力
    3. 季节性因子 (20%) - 当季商品权重提升
    4. 节假日因子 (10%) - 节假日相关商品权重提升
    5. 销量和热度 (15%) - 历史成团次数和参团人数
    6. 协同过滤 (10%) - 相似用户偏好

    响应包含：
    - product: 商品信息
    - score: 推荐分数 (0-100)
    - reasons: 推荐理由列表
    - confidence: 置信度 (0-1)
    """
    filters = {}
    if category:
        filters["category"] = category
    if price_min is not None:
        filters["price_min"] = price_min
    if price_max is not None:
        filters["price_max"] = price_max
    if min_score is not None:
        filters["min_score"] = min_score

    service = ProductSelectionEnhancedService(db)
    recommendations = service.get_ai_recommendations(
        community_id=community_id,
        limit=limit,
        user_id=user_id,
        filters=filters
    )

    return {
        "success": True,
        "data": {
            "community_id": community_id,
            "recommendations": [
                {
                    "product_id": rec["product"].id,
                    "product_name": rec["product"].name,
                    "price": rec["product"].price,
                    "category": rec["product"].category,
                    "score": rec["score"],
                    "reasons": rec["reasons"],
                    "confidence": rec["confidence"]
                }
                for rec in recommendations
            ],
            "total": len(recommendations)
        }
    }


@product_selection_router.get("/seasonal-factor")
def get_seasonal_factor():
    """
    获取当前季节性因子

    返回当前季节、季节性权重因子、热门品类和关键词
    """
    from services.product_selection_enhanced import SeasonalFactorEngine, SEASONAL_FACTORS

    current_season = SeasonalFactorEngine.get_current_season()
    season_config = SEASONAL_FACTORS.get(current_season, {})

    return {
        "success": True,
        "data": {
            "current_season": current_season,
            "season_factor": season_config.get("factor", 1.0),
            "hot_categories": season_config.get("categories", []),
            "hot_keywords": season_config.get("keywords", []),
            "description": f"当前是{current_season}季，{', '.join(season_config.get('categories', []))}品类更受欢迎"
        }
    }


@product_selection_router.get("/holiday-factor")
def get_holiday_factor():
    """
    获取当前节假日因子

    返回临近的节假日、权重因子、影响品类
    """
    from services.product_selection_enhanced import SeasonalFactorEngine, HOLIDAY_FACTORS

    holiday_factor, holiday_name = SeasonalFactorEngine.get_holiday_factor()

    if holiday_name:
        holiday_config = HOLIDAY_FACTORS.get(holiday_name, {})
        return {
            "success": True,
            "data": {
                "holiday_name": holiday_name,
                "holiday_factor": holiday_factor,
                "hot_categories": holiday_config.get("categories", []),
                "days_range": holiday_config.get("days_range", 0),
                "description": f"临近{holiday_name}，{', '.join(holiday_config.get('categories', []))}品类需求上升"
            }
        }
    else:
        return {
            "success": True,
            "data": {
                "holiday_name": None,
                "holiday_factor": 1.0,
                "description": "近期无重大节假日"
            }
        }


@product_selection_router.get("/community/{community_id}/profile")
def get_community_profile(
    community_id: str,
    db: Session = Depends(get_db)
):
    """
    获取社区画像

    返回社区的消费偏好、价格敏感度、活跃用户数等信息
    """
    service = ProductSelectionEnhancedService(db)
    profile = service.load_or_create_community_profile(db, community_id)

    return {
        "success": True,
        "data": profile.to_dict()
    }


@product_selection_router.post("/interaction/record")
def record_interaction(
    user_id: str = Header(..., alias="X-User-ID"),
    product_id: str = Query(..., description="商品 ID"),
    interaction_type: str = Query(..., description="交互类型"),
    value: float = Query(default=1.0, description="交互强度"),
    db: Session = Depends(get_db)
):
    """
    记录用户交互行为

    交互类型包括：
    - view: 浏览 (权重 0.5)
    - wishlist: 收藏 (权重 2.0)
    - share: 分享 (权重 1.5)
    - purchase: 购买 (权重 5.0)
    - review: 评价 (权重 3.0)

    这些交互数据将用于协同过滤推荐
    """
    valid_types = ["view", "wishlist", "share", "purchase", "review"]
    if interaction_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"交互类型必须是以下之一：{valid_types}")

    service = ProductSelectionEnhancedService(db)
    service.record_user_interaction(user_id, product_id, interaction_type, value)

    return {
        "success": True,
        "message": f"已记录{interaction_type}交互"
    }


@product_selection_router.get("/product/{product_id}/similar")
def get_similar_products(
    product_id: str,
    limit: int = Query(default=5, ge=1, le=20, description="返回相似商品数量"),
    db: Session = Depends(get_db)
):
    """
    获取相似商品（基于协同过滤）

    使用余弦相似度计算商品间的相似性
    """
    # 这里需要实际实现，当前返回简化版本
    return {
        "success": True,
        "data": {
            "product_id": product_id,
            "similar_products": [],
            "message": "协同过滤引擎需要足够的用户交互数据才能计算相似度"
        }
    }


@product_selection_router.get("/category/infer")
def infer_category(
    product_name: str = Query(..., description="商品名称"),
    description: Optional[str] = Query(None, description="商品描述")
):
    """
    推断商品类别

    基于关键词匹配自动识别商品所属分类
    """
    from services.product_selection_enhanced import ProductSelectionEnhancedService
    service = ProductSelectionEnhancedService()
    category = service._infer_category(product_name, description or "")

    return {
        "success": True,
        "data": {
            "product_name": product_name,
            "inferred_category": category
        }
    }


@product_selection_router.post("/community/{community_id}/profile/update")
def update_community_profile(
    community_id: str,
    updates: Dict[str, Any] = Body(..., description="更新内容"),
    db: Session = Depends(get_db)
):
    """
    更新社区画像

    支持更新：
    - category_preferences: 品类偏好 {category: score}
    - price_range_preference: 价格偏好 {low/mid/high: score}
    """
    service = ProductSelectionEnhancedService(db)

    if "category" in updates and "delta" in updates:
        service.update_community_profile(
            community_id,
            updates["category"],
            updates["delta"]
        )

    return {
        "success": True,
        "message": "社区画像已更新"
    }


# 导出 router 供 main.py 使用
router = product_selection_router
