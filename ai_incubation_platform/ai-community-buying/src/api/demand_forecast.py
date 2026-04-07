"""
AI 需求预测 API 路由
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from config.database import get_db
from services.demand_forecast_service import DemandForecastService
from models.product import DemandForecast, CommunityPreference
from models.entities import DemandForecastEntity, CommunityPreferenceEntity
from core.exceptions import AppException

router = APIRouter(prefix="/api/ai", tags=["AI 需求预测"])


def _convert_forecast_entity_to_model(entity: DemandForecastEntity) -> DemandForecast:
    """将预测实体转换为模型"""
    import json
    return DemandForecast(
        id=entity.id,
        product_id=entity.product_id,
        community_id=entity.community_id,
        forecast_date=entity.forecast_date,
        forecast_quantity=entity.forecast_quantity,
        actual_quantity=entity.actual_quantity,
        accuracy=entity.accuracy,
        confidence=entity.confidence,
        features=json.loads(entity.features) if entity.features else None,
        model_version=entity.model_version,
        created_at=entity.created_at,
        updated_at=entity.updated_at
    )


def _convert_preference_entity_to_model(entity: CommunityPreferenceEntity) -> CommunityPreference:
    """将偏好实体转换为模型"""
    import json
    return CommunityPreference(
        id=entity.id,
        community_id=entity.community_id,
        category=entity.category,
        preference_score=entity.preference_score,
        avg_order_value=entity.avg_order_value,
        purchase_frequency=entity.purchase_frequency,
        favorite_brands=json.loads(entity.favorite_brands) if entity.favorite_brands else None,
        favorite_price_range=json.loads(entity.favorite_price_range) if entity.favorite_price_range else None,
        sample_size=entity.sample_size,
        last_purchase_at=entity.last_purchase_at,
        created_at=entity.created_at,
        updated_at=entity.updated_at
    )


@router.post("/forecast", response_model=DemandForecast, summary="创建需求预测")
def create_forecast(
    product_id: str = Query(..., description="商品 ID"),
    community_id: str = Query(..., description="社区 ID"),
    forecast_date: datetime = Query(..., description="预测日期"),
    forecast_quantity: int = Query(..., description="预测销量"),
    confidence: float = Query(0.0, ge=0, le=1, description="置信度"),
    model_version: str = Query("v1", description="模型版本"),
    db: Session = Depends(get_db)
):
    """创建需求预测记录"""
    service = DemandForecastService(db)

    data = {
        "product_id": product_id,
        "community_id": community_id,
        "forecast_date": forecast_date,
        "forecast_quantity": forecast_quantity,
        "confidence": confidence,
        "model_version": model_version
    }

    forecast, success = service.create_forecast(data)

    if not success:
        raise AppException(
            code="FORECAST_CREATE_FAILED",
            message="创建需求预测失败"
        )

    return _convert_forecast_entity_to_model(forecast)


@router.get("/forecast/{forecast_id}", response_model=DemandForecast, summary="获取预测记录详情")
def get_forecast(forecast_id: str, db: Session = Depends(get_db)):
    """获取预测记录详细信息"""
    service = DemandForecastService(db)
    forecast = service.get_forecast(forecast_id)

    if not forecast:
        raise AppException(
            code="FORECAST_NOT_FOUND",
            message="预测记录不存在",
            status=404
        )

    return _convert_forecast_entity_to_model(forecast)


@router.put("/forecast/{forecast_id}/actual", response_model=DemandForecast, summary="更新预测实际值")
def update_forecast_actual(
    forecast_id: str,
    actual_quantity: int = Query(..., description="实际销量"),
    accuracy: float = Query(..., ge=0, le=1, description="预测准确率"),
    db: Session = Depends(get_db)
):
    """更新预测的实际销量和准确率"""
    service = DemandForecastService(db)
    forecast, success = service.update_forecast_actual(forecast_id, actual_quantity, accuracy)

    if not success:
        raise AppException(
            code="FORECAST_UPDATE_FAILED",
            message="更新预测实际值失败"
        )

    return _convert_forecast_entity_to_model(forecast)


@router.get("/forecasts", response_model=List[DemandForecast], summary="获取预测记录列表")
def list_forecasts(
    product_id: Optional[str] = Query(None, description="商品 ID"),
    community_id: Optional[str] = Query(None, description="社区 ID"),
    date_from: Optional[datetime] = Query(None, description="开始日期"),
    date_to: Optional[datetime] = Query(None, description="结束日期"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量上限"),
    db: Session = Depends(get_db)
):
    """获取预测记录列表"""
    service = DemandForecastService(db)
    forecasts = service.list_forecasts(
        product_id=product_id,
        community_id=community_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit
    )
    return [_convert_forecast_entity_to_model(f) for f in forecasts]


@router.get("/forecast/accuracy-stats", summary="获取预测准确率统计")
def get_forecast_accuracy_stats(
    product_id: Optional[str] = Query(None, description="商品 ID"),
    community_id: Optional[str] = Query(None, description="社区 ID"),
    db: Session = Depends(get_db)
):
    """获取预测准确率统计信息"""
    service = DemandForecastService(db)
    return service.get_forecast_accuracy_stats(product_id, community_id)


@router.get("/forecast/sma/{product_id}", summary="简单移动平均预测")
def simple_moving_average_forecast(
    product_id: str,
    community_id: str = Query(..., description="社区 ID"),
    days: int = Query(7, ge=1, le=30, description="历史天数"),
    future_days: int = Query(1, ge=1, le=7, description="预测未来天数"),
    db: Session = Depends(get_db)
):
    """
    使用简单移动平均法预测销量

    基于过去 N 天的平均销量预测未来销量
    """
    service = DemandForecastService(db)
    result = service.simple_moving_average_forecast(
        product_id=product_id,
        community_id=community_id,
        days=days,
        future_days=future_days
    )
    return result


@router.get("/community/{community_id}/preferences", response_model=List[CommunityPreference], summary="获取社区偏好")
def get_community_preferences(
    community_id: str,
    db: Session = Depends(get_db)
):
    """获取社区偏好分析结果"""
    service = DemandForecastService(db)
    preferences = service.get_community_preferences(community_id)
    return [_convert_preference_entity_to_model(p) for p in preferences]


@router.post("/community/{community_id}/preferences/analyze", summary="分析社区偏好")
def analyze_community_preference(
    community_id: str,
    db: Session = Depends(get_db)
):
    """分析社区偏好并保存结果"""
    service = DemandForecastService(db)

    # 分析偏好
    preferences = service.analyze_community_preference(community_id)

    # 保存前 N 个品类的偏好
    saved_count = 0
    for pref in preferences[:20]:  # 保存前 20 个
        pref_data = {
            "preference_score": pref["preference_score"],
            "avg_order_value": float(pref["avg_order_value"]) if pref["avg_order_value"] else 0.0,
            "purchase_frequency": pref["order_count"] / 30.0,  # 假设 30 天周期
            "sample_size": pref["order_count"]
        }
        service.save_community_preference(
            community_id=community_id,
            category=pref["product_name"],
            preference_data=pref_data
        )
        saved_count += 1

    return {
        "success": True,
        "analyzed_count": len(preferences),
        "saved_count": saved_count,
        "top_preferences": preferences[:10]
    }


@router.get("/community/{community_id}/recommendations", summary="社区商品推荐")
def recommend_products_for_community(
    community_id: str,
    limit: int = Query(10, ge=1, le=50, description="返回数量上限"),
    db: Session = Depends(get_db)
):
    """为社区推荐商品"""
    service = DemandForecastService(db)
    recommendations = service.recommend_products_for_community(community_id, limit)
    return {
        "success": True,
        "community_id": community_id,
        "recommendations": recommendations
    }


@router.get("/products/{product_id}/demand-trend", summary="商品需求趋势")
def get_product_demand_trend(
    product_id: str,
    community_id: Optional[str] = Query(None, description="社区 ID"),
    days: int = Query(30, ge=1, le=90, description="天数"),
    db: Session = Depends(get_db)
):
    """获取商品需求趋势"""
    from sqlalchemy import func
    from models.entities import OrderEntity, GroupBuyEntity
    from models.product import OrderStatus

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    query = db.query(
        func.date(OrderEntity.created_at).label("date"),
        func.sum(OrderEntity.quantity).label("quantity")
    ).filter(
        OrderEntity.product_id == product_id,
        OrderEntity.status == OrderStatus.COMPLETED,
        OrderEntity.created_at >= start_date
    )

    if community_id:
        query = query.join(
            GroupBuyEntity, OrderEntity.group_buy_id == GroupBuyEntity.id
        ).filter(GroupBuyEntity.organizer_id == community_id)

    results = query.group_by(
        func.date(OrderEntity.created_at)
    ).order_by(
        func.date(OrderEntity.created_at)
    ).all()

    trend_data = [
        {"date": r.date.isoformat(), "quantity": r.quantity}
        for r in results
    ]

    return {
        "success": True,
        "product_id": product_id,
        "days": days,
        "trend": trend_data
    }
