"""
推荐服务 API 路由
"""
from fastapi import APIRouter, Depends, Query
from typing import List
from sqlalchemy.orm import Session
from config.database import get_db
from services.recommendation_service import recommendation_service

router = APIRouter(prefix="/api/recommendation", tags=["recommendation"])


@router.get("/products/{community_id}", summary="获取社区推荐商品")
async def get_recommended_products(
    community_id: str,
    limit: int = Query(10, description="返回数量"),
    db: Session = Depends(get_db)
):
    """获取指定社区的推荐商品列表"""
    recommendations = recommendation_service.get_recommended_products(db, community_id, limit)
    return {
        "community_id": community_id,
        "total": len(recommendations),
        "products": [
            {
                **rec["product"].model_dump(),
                "recommendation_score": rec["score"],
                "recommendation_reason": rec["reason"]
            }
            for rec in recommendations
        ]
    }


@router.get("/dynamic-price/{product_id}", summary="计算动态价格")
async def calculate_dynamic_price(
    product_id: str,
    current_participants: int = Query(..., description="当前参与人数"),
    target_size: int = Query(..., description="目标成团人数"),
    db: Session = Depends(get_db)
):
    """计算商品的动态价格"""
    from services.groupbuy_service_db import GroupBuyServiceDB
    gb_service = GroupBuyServiceDB(db)
    product = gb_service.get_product(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    dynamic_price = recommendation_service.calculate_dynamic_price(
        product, current_participants, target_size
    )

    return {
        "product_id": product_id,
        "base_price": product.price,
        "dynamic_price": dynamic_price,
        "discount_rate": round(dynamic_price / product.price, 2),
        "current_participants": current_participants,
        "target_size": target_size
    }
