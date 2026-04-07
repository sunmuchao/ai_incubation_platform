"""
AI 需求预测 API 路由增强版 (P1 迭代)
支持 Prophet+LSTM 融合预测
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from config.database import get_db
from services.demand_forecast_service_enhanced import DemandForecastServiceEnhanced
from models.product import DemandForecast, CommunityPreference
from models.entities import DemandForecastEntity
from core.exceptions import AppException

router = APIRouter(prefix="/api/ai", tags=["AI 需求预测增强"])


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


@router.get("/forecast/advanced/{product_id}", summary="高级需求预测 (Prophet+LSTM 融合)")
def advanced_demand_forecast(
    product_id: str,
    community_id: str = Query(..., description="社区 ID"),
    future_days: int = Query(7, ge=1, le=30, description="预测天数"),
    use_ensemble: bool = Query(True, description="是否使用融合模型"),
    save_record: bool = Query(False, description="是否保存预测记录"),
    db: Session = Depends(get_db)
):
    """
    使用 Prophet+LSTM 融合模型进行需求预测

    **功能特性**:
    - Prophet 风格预测：趋势分解 + 季节性 + 节假日效应
    - LSTM 风格预测：滑动窗口回归 + 趋势捕捉
    - 融合预测：根据数据量动态调整模型权重

    **因子说明**:
    - 节假日因子：春节/国庆 (1.5x), 中秋/五一 (1.3x), 其他 (1.2x)
    - 季节性因子：夏季 (1.2x), 秋季 (1.1x), 春季 (1.0x), 冬季 (0.9x)
    - 周末因子：周末 (1.3x), 周五 (1.1x), 工作日 (1.0x)
    """
    service = DemandForecastServiceEnhanced(db)

    result = service.advanced_forecast(
        product_id=product_id,
        community_id=community_id,
        future_days=future_days,
        use_ensemble=use_ensemble
    )

    # 可选保存预测记录
    if save_record and result.get("forecast"):
        service.create_forecast_record(
            product_id=product_id,
            community_id=community_id,
            forecast_result=result,
            model_version="v2.0-ensemble" if use_ensemble else "v2.0-prophet"
        )

    return {
        "success": True,
        "product_id": product_id,
        "community_id": community_id,
        "prediction": result
    }


@router.get("/forecast/prophet/{product_id}", summary="Prophet 风格预测")
def prophet_demand_forecast(
    product_id: str,
    community_id: str = Query(..., description="社区 ID"),
    future_days: int = Query(7, ge=1, le=30, description="预测天数"),
    db: Session = Depends(get_db)
):
    """
    使用 Prophet 风格进行需求预测

    特点：擅长捕捉季节性、节假日效应、星期几效应
    """
    service = DemandForecastServiceEnhanced(db)
    result = service._prophet_style_forecast(
        service._get_historical_data(product_id, community_id, days=90),
        future_days
    )
    return {
        "success": True,
        "product_id": product_id,
        "community_id": community_id,
        "prediction": result
    }


@router.get("/forecast/lstm/{product_id}", summary="LSTM 风格预测")
def lstm_demand_forecast(
    product_id: str,
    community_id: str = Query(..., description="社区 ID"),
    future_days: int = Query(7, ge=1, le=30, description="预测天数"),
    db: Session = Depends(get_db)
):
    """
    使用 LSTM 风格进行需求预测

    特点：擅长捕捉长期依赖、非线性模式、趋势变化
    """
    service = DemandForecastServiceEnhanced(db)
    result = service._lstm_style_forecast(
        service._get_historical_data(product_id, community_id, days=90),
        future_days
    )
    return {
        "success": True,
        "product_id": product_id,
        "community_id": community_id,
        "prediction": result
    }


@router.post("/forecast/{forecast_id}/actual", summary="更新预测实际值")
def update_forecast_actual(
    forecast_id: str,
    actual_quantity: int = Query(..., description="实际销量"),
    db: Session = Depends(get_db)
):
    """
    更新预测的实际销量，用于计算准确率

    准确率 = 1 - |预测值 - 实际值 | / 实际值
    """
    service = DemandForecastServiceEnhanced(db)

    forecast = service.db.query(DemandForecastEntity).filter(
        DemandForecastEntity.id == forecast_id
    ).first()

    if not forecast:
        raise AppException(
            code="FORECAST_NOT_FOUND",
            message="预测记录不存在",
            status=404
        )

    # 计算准确率
    if actual_quantity == 0:
        mape = 0 if forecast.forecast_quantity == 0 else 1.0
    else:
        mape = abs(forecast.forecast_quantity - actual_quantity) / actual_quantity

    accuracy = 1 - mape

    forecast.actual_quantity = actual_quantity
    forecast.accuracy = accuracy

    try:
        service.db.commit()
        service.db.refresh(forecast)
    except Exception as e:
        service.db.rollback()
        raise AppException(
            code="FORECAST_UPDATE_FAILED",
            message=f"更新失败：{str(e)}"
        )

    return {
        "success": True,
        "forecast_id": forecast_id,
        "predicted_quantity": forecast.forecast_quantity,
        "actual_quantity": actual_quantity,
        "accuracy": accuracy,
        "accuracy_description": "高" if accuracy > 0.8 else "中" if accuracy > 0.6 else "低"
    }


@router.get("/forecast/{forecast_id}/accuracy", summary="获取预测准确率")
def get_forecast_accuracy(
    forecast_id: str,
    db: Session = Depends(get_db)
):
    """获取单条预测记录的准确率"""
    service = DemandForecastServiceEnhanced(db)
    return service.calculate_forecast_accuracy(forecast_id)


@router.get("/forecast/accuracy-stats", summary="获取批量预测准确率统计")
def get_batch_forecast_accuracy(
    product_id: Optional[str] = Query(None, description="商品 ID"),
    community_id: Optional[str] = Query(None, description="社区 ID"),
    db: Session = Depends(get_db)
):
    """
    获取批量预测准确率统计

    返回:
    - 总预测数
    - 平均准确率
    - 平均 MAPE
    - 准确率分布（高/中/低）
    - 按模型版本分类的准确率
    """
    service = DemandForecastServiceEnhanced(db)
    return service.get_batch_forecast_accuracy(product_id, community_id)


@router.get("/forecast/sma/{product_id}", summary="简单移动平均预测 (向后兼容)")
def simple_moving_average_forecast(
    product_id: str,
    community_id: str = Query(..., description="社区 ID"),
    days: int = Query(7, ge=1, le=30, description="历史天数"),
    future_days: int = Query(1, ge=1, le=7, description="预测未来天数"),
    db: Session = Depends(get_db)
):
    """
    使用简单移动平均法预测销量（向后兼容原有 API）
    """
    service = DemandForecastServiceEnhanced(db)
    result = service.simple_moving_average_forecast(
        product_id=product_id,
        community_id=community_id,
        days=days,
        future_days=future_days
    )
    return {
        "success": True,
        "product_id": product_id,
        "community_id": community_id,
        "prediction": result
    }


@router.get("/community/{community_id}/preferences", response_model=List[CommunityPreference], summary="获取社区偏好")
def get_community_preferences(
    community_id: str,
    db: Session = Depends(get_db)
):
    """获取社区偏好分析结果"""
    service = DemandForecastServiceEnhanced(db)
    preferences = service.get_community_preferences(community_id)

    return [
        CommunityPreference(
            id=p.id,
            community_id=p.community_id,
            category=p.category,
            preference_score=p.preference_score,
            avg_order_value=p.avg_order_value,
            purchase_frequency=p.purchase_frequency,
            favorite_brands=json.loads(p.favorite_brands) if p.favorite_brands else None,
            favorite_price_range=json.loads(p.favorite_price_range) if p.favorite_price_range else None,
            sample_size=p.sample_size,
            last_purchase_at=p.last_purchase_at,
            created_at=p.created_at,
            updated_at=p.updated_at
        )
        for p in preferences
    ]


@router.post("/community/{community_id}/preferences/analyze", summary="分析社区偏好")
def analyze_community_preference(
    community_id: str,
    db: Session = Depends(get_db)
):
    """分析社区偏好并保存结果"""
    service = DemandForecastServiceEnhanced(db)

    # 分析偏好
    preferences = service.analyze_community_preference(community_id)

    # 保存前 N 个品类的偏好
    saved_count = 0
    for pref in preferences[:20]:
        pref_data = {
            "preference_score": pref["preference_score"],
            "avg_order_value": float(pref["avg_order_value"]) if pref["avg_order_value"] else 0.0,
            "purchase_frequency": pref["order_count"] / 30.0,
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
    service = DemandForecastServiceEnhanced(db)
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
        {"date": r.date.isoformat(), "quantity": r.quantity or 0}
        for r in results
    ]

    return {
        "success": True,
        "product_id": product_id,
        "days": days,
        "trend": trend_data
    }


# 需要导入 json 用于序列化
import json
