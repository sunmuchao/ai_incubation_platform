"""
质量预测模型 API。

提供任务交付质量预测、质量分析、风险预警等功能。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from models.quality_prediction import (
    QualityLevel,
    QualityPrediction,
    QualityPredictionRequest,
    QualityPredictionResponse,
)
from services.quality_prediction_service import quality_prediction_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quality-prediction", tags=["quality_prediction"])


@router.post("/predict", response_model=QualityPredictionResponse)
async def predict_quality(request: QualityPredictionRequest):
    """
    预测任务交付质量。

    基于以下特征进行预测：
    - 工人历史表现
    - 任务复杂度
    - 报酬合理性
    - 期限压力
    - 任务描述质量

    返回质量评分、风险等级和改进建议。
    """
    response = quality_prediction_service.predict_quality(request)
    return response


@router.get("/prediction/{prediction_id}", response_model=QualityPrediction)
async def get_prediction(prediction_id: str):
    """获取质量预测详情。"""
    prediction = quality_prediction_service.get_prediction(prediction_id)
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return prediction


@router.get("/task/{task_id}/prediction")
async def get_prediction_by_task(task_id: str):
    """通过任务 ID 获取质量预测。"""
    prediction = quality_prediction_service.get_prediction_by_task(task_id)
    if not prediction:
        raise HTTPException(status_code=404, detail="No prediction found for this task")
    return prediction


@router.post("/prediction/{prediction_id}/record")
async def record_actual_quality(
    prediction_id: str,
    actual_quality_level: QualityLevel,
    actual_quality_score: float,
):
    """
    记录实际质量结果。

    用于验证预测准确性和模型自学习。
    """
    success = quality_prediction_service.record_actual_quality(
        prediction_id,
        actual_quality_level,
        actual_quality_score,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Prediction not found")

    return {
        "message": "Actual quality recorded successfully",
        "prediction_id": prediction_id,
    }


@router.get("/worker/{worker_id}/stats")
async def get_worker_quality_stats(worker_id: str):
    """获取工人质量统计信息。"""
    stats = quality_prediction_service.get_worker_quality_stats(worker_id)
    return stats


@router.get("/features")
async def list_quality_features():
    """获取所有质量特征说明。"""
    return {
        "features": [
            {
                "name": "worker_history_quality",
                "description": "工人历史平均质量得分",
                "weight": 0.3,
                "range": [0, 1],
            },
            {
                "name": "task_complexity",
                "description": "任务复杂度评估（low/medium/high）",
                "weight": 0.2,
                "range": [0, 1],
            },
            {
                "name": "reward_adequacy",
                "description": "报酬合理性评估（相对于市场均价）",
                "weight": 0.15,
                "range": [0, 1],
            },
            {
                "name": "deadline_pressure",
                "description": "期限压力评估（相对于预期工时）",
                "weight": 0.15,
                "range": [0, 1],
            },
            {
                "name": "description_quality",
                "description": "任务描述质量（长度、结构、清晰度）",
                "weight": 0.2,
                "range": [0, 1],
            },
        ]
    }


@router.get("/levels")
async def list_quality_levels():
    """获取所有质量等级说明。"""
    return {
        "levels": [
            {
                "name": QualityLevel.EXCELLENT.value,
                "description": "优秀 - 预期交付质量非常高，几乎无风险",
                "score_range": [0.8, 1.0],
            },
            {
                "name": QualityLevel.GOOD.value,
                "description": "良好 - 预期交付质量较好，风险较低",
                "score_range": [0.6, 0.8],
            },
            {
                "name": QualityLevel.AVERAGE.value,
                "description": "一般 - 预期交付质量普通，需要正常验收",
                "score_range": [0.4, 0.6],
            },
            {
                "name": QualityLevel.POOR.value,
                "description": "较差 - 预期交付质量不佳，建议加强验收",
                "score_range": [0.2, 0.4],
            },
            {
                "name": QualityLevel.HIGH_RISK.value,
                "description": "高风险 - 存在明显质量风险，建议人工介入",
                "score_range": [0.0, 0.2],
            },
        ]
    }


@router.get("/batch-predict")
async def batch_predict(
    requests: List[QualityPredictionRequest],
):
    """
    批量质量预测。

    适用于同时评估多个任务 - 工人配对的质量风险。
    """
    results = []
    for req in requests:
        try:
            response = quality_prediction_service.predict_quality(req)
            results.append({
                "task_id": req.task_id,
                "worker_id": req.worker_id,
                "success": response.success,
                "predicted_quality": response.predicted_quality.value if response.predicted_quality else None,
                "quality_score": response.quality_score,
                "risk_score": response.risk_score,
                "risk_level": response.risk_level,
            })
        except Exception as e:
            results.append({
                "task_id": req.task_id,
                "worker_id": req.worker_id,
                "success": False,
                "error": str(e),
            })

    return {"results": results, "total": len(requests)}


@router.get("/risk-alerts")
async def get_risk_alerts(
    min_risk_score: float = 0.7,
    limit: int = 50,
):
    """
    获取高风险预警列表。

    返回所有风险得分超过阈值的质量预测。
    """
    # 扫描所有预测，找出高风险的
    high_risk_predictions = []
    for prediction in quality_prediction_service._predictions.values():
        if prediction.risk_score >= min_risk_score:
            high_risk_predictions.append({
                "prediction_id": prediction.id,
                "task_id": prediction.task_id,
                "worker_id": prediction.worker_id,
                "risk_score": prediction.risk_score,
                "quality_level": prediction.predicted_quality_level.value,
                "risk_factors": prediction.risk_factors,
                "created_at": prediction.created_at.isoformat(),
            })

    # 按风险得分排序
    high_risk_predictions.sort(key=lambda x: x["risk_score"], reverse=True)

    return {
        "alerts": high_risk_predictions[:limit],
        "total": len(high_risk_predictions),
        "threshold": min_risk_score,
    }
