"""
AI 智能成团预测 API 路由

提供团购成团概率预测、预测历史查询、模型准确率统计等功能。
"""
from fastapi import APIRouter, Depends, Query, HTTPException, Path
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from config.database import get_db
from services.group_prediction_service import GroupPredictionService, get_prediction_service
from models.entities import GroupBuyEntity
from models.product import GroupBuyStatus

router = APIRouter(prefix="/api/ai", tags=["AI 智能成团预测"])


@router.get("/group-prediction/{group_buy_id}", summary="预测团购成团概率")
def predict_group_success(
    group_buy_id: str = Path(..., description="团购 ID"),
    db: Session = Depends(get_db)
):
    """
    预测指定团购的成团概率

    基于以下特征进行预测:
    - 进度特征：当前进度、剩余时间
    - 时间特征：截止时刻、星期几、是否周末
    - 历史特征：团长历史成团率、商品历史成团率
    - 热度特征：商品浏览人数、收藏人数、每小时加入率
    - 环境特征：是否节假日

    返回:
    - success_probability: 成团概率 (0-1)
    - predicted_final_size: 预测最终参团人数
    - confidence_level: 置信度等级 (low/medium/high)
    - prediction_category: 预测分类 (highly_likely/likely/uncertain/unlikely)
    - advice: 优化建议
    """
    service = get_prediction_service(db)

    # 检查团购是否存在
    group_buy = db.query(GroupBuyEntity).filter(GroupBuyEntity.id == group_buy_id).first()
    if not group_buy:
        raise HTTPException(status_code=404, detail=f"团购 {group_buy_id} 不存在")

    result = service.predict_group_success(group_buy_id)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/group-predictions", summary="批量预测活跃团购")
def predict_active_groups(
    organizer_id: Optional[str] = Query(None, description="团长 ID（可选，不传则预测所有）"),
    db: Session = Depends(get_db)
):
    """
    批量预测所有活跃团购的成团概率

    适用于团长仪表盘、运营后台等场景。
    """
    service = get_prediction_service(db)
    predictions = service.predict_active_groups(organizer_id)
    return {
        "success": True,
        "count": len(predictions),
        "predictions": predictions
    }


@router.get("/group-prediction/{group_buy_id}/history", summary="获取预测历史记录")
def get_prediction_history(
    group_buy_id: str = Path(..., description="团购 ID"),
    db: Session = Depends(get_db)
):
    """
    获取团购的预测历史记录

    返回该团购的所有预测记录，包括预测时间、预测结果、实际结果等。
    """
    service = get_prediction_service(db)
    history = service.get_prediction_history(group_buy_id)
    return {
        "success": True,
        "group_buy_id": group_buy_id,
        "history": history
    }


@router.get("/prediction/accuracy-stats", summary="获取模型准确率统计")
def get_model_accuracy_stats(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: Session = Depends(get_db)
):
    """
    获取预测模型的准确率统计

    统计指标包括:
    - 总预测数
    - 平均准确率
    - 按置信度分组的准确率（高/中/低）
    """
    service = get_prediction_service(db)
    stats = service.get_model_accuracy_stats(days)
    return {
        "success": True,
        "period_days": days,
        "stats": stats
    }


@router.post("/group-prediction/{group_buy_id}/result", summary="更新预测实际结果")
def update_prediction_result(
    group_buy_id: str = Path(..., description="团购 ID"),
    actual_result: str = Query(..., description="实际结果 (success/failed/expired/cancelled)"),
    actual_final_size: int = Query(..., ge=1, description="实际最终参团人数"),
    db: Session = Depends(get_db)
):
    """
    更新预测的实际结果

    当团购结束时调用此接口，用于:
    1. 回填实际结果供后续分析
    2. 计算预测准确率
    3. 为模型优化提供训练数据
    """
    service = get_prediction_service(db)

    # 验证实际结果
    valid_results = ["success", "failed", "expired", "cancelled"]
    if actual_result not in valid_results:
        raise HTTPException(
            status_code=400,
            detail=f"实际结果必须是以下值之一：{valid_results}"
        )

    success = service.update_prediction_result(group_buy_id, actual_result, actual_final_size)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"团购 {group_buy_id} 没有预测记录"
        )

    return {
        "success": True,
        "message": "预测结果已更新",
        "group_buy_id": group_buy_id,
        "actual_result": actual_result,
        "actual_final_size": actual_final_size
    }


@router.get("/organizer/{organizer_id}/predictions", summary="获取团长预测列表")
def get_organizer_predictions(
    organizer_id: str = Path(..., description="团长 ID"),
    status: Optional[str] = Query(None, description="团购状态过滤"),
    db: Session = Depends(get_db)
):
    """
    获取指定团长的所有团购预测

    可按状态过滤（open/success/failed/expired/cancelled）
    """
    service = get_prediction_service(db)

    # 查询团长的团购
    query = db.query(GroupBuyEntity).filter(GroupBuyEntity.organizer_id == organizer_id)

    if status:
        query = query.filter(GroupBuyEntity.status == GroupBuyStatus(status))

    groups = query.order_by(GroupBuyEntity.created_at.desc()).all()

    predictions = []
    for group in groups:
        # 对于活跃的团购，实时预测
        if group.status == GroupBuyStatus.OPEN:
            pred = service.predict_group_success(group.id)
            predictions.append(pred)
        else:
            # 对于已结束的团购，返回历史记录
            history = service.get_prediction_history(group.id)
            predictions.append({
                "group_buy_id": group.id,
                "product_id": group.product_id,
                "status": group.status.value,
                "final_size": group.current_size,
                "prediction_history": history[:1] if history else []  # 只返回最后一次预测
            })

    return {
        "success": True,
        "organizer_id": organizer_id,
        "count": len(predictions),
        "predictions": predictions
    }


@router.get("/product/{product_id}/predictions", summary="获取商品预测统计")
def get_product_prediction_stats(
    product_id: str = Path(..., description="商品 ID"),
    db: Session = Depends(get_db)
):
    """
    获取商品的成团预测统计

    返回该商品所有团购的预测汇总信息。
    """
    from models.p0_entities import GroupPredictionEntity
    from sqlalchemy import func

    # 查询该商品的所有团购
    groups = db.query(GroupBuyEntity).filter(
        GroupBuyEntity.product_id == product_id
    ).all()

    if not groups:
        raise HTTPException(status_code=404, detail=f"商品 {product_id} 没有团购记录")

    group_ids = [g.id for g in groups]

    # 统计预测数据
    latest_predictions = db.query(
        GroupPredictionEntity.group_buy_id,
        func.max(GroupPredictionEntity.prediction_time).label("latest_time")
    ).filter(
        GroupPredictionEntity.group_buy_id.in_(group_ids)
    ).group_by(
        GroupPredictionEntity.group_buy_id
    ).all()

    # 获取最新预测
    latest_pred_ids = []
    for p in latest_predictions:
        latest = db.query(GroupPredictionEntity).filter(
            GroupPredictionEntity.group_buy_id == p.group_buy_id,
            GroupPredictionEntity.prediction_time == p.latest_time
        ).first()
        if latest:
            latest_pred_ids.append(latest.id)

    all_predictions = db.query(GroupPredictionEntity).filter(
        GroupPredictionEntity.id.in_(latest_pred_ids)
    ).all() if latest_pred_ids else []

    # 计算统计
    if all_predictions:
        avg_probability = sum(p.success_probability for p in all_predictions) / len(all_predictions)
        highly_likely_count = sum(1 for p in all_predictions if p.prediction_category == "highly_likely")
        likely_count = sum(1 for p in all_predictions if p.prediction_category == "likely")
        uncertain_count = sum(1 for p in all_predictions if p.prediction_category == "uncertain")
        unlikely_count = sum(1 for p in all_predictions if p.prediction_category == "unlikely")
    else:
        avg_probability = 0
        highly_likely_count = 0
        likely_count = 0
        uncertain_count = 0
        unlikely_count = 0

    # 统计实际成团情况
    success_count = sum(1 for g in groups if g.status == GroupBuyStatus.SUCCESS)
    failed_count = sum(1 for g in groups if g.status == GroupBuyStatus.FAILED)
    expired_count = sum(1 for g in groups if g.status == GroupBuyStatus.EXPIRED)

    return {
        "success": True,
        "product_id": product_id,
        "total_groups": len(groups),
        "prediction_stats": {
            "avg_success_probability": round(avg_probability, 3),
            "highly_likely": highly_likely_count,
            "likely": likely_count,
            "uncertain": uncertain_count,
            "unlikely": unlikely_count
        },
        "actual_stats": {
            "success": success_count,
            "failed": failed_count,
            "expired": expired_count,
            "success_rate": round(success_count / len(groups), 3) if groups else 0
        }
    }
