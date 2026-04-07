"""
P6 预测性监控 API

提供预测、异常检测、自愈建议等端点
"""
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

from services.predictive_monitoring_service import (
    predictive_monitoring_service,
    Prediction,
    Anomaly,
    SelfHealingRecommendation
)
from utils.logger import logger

router = APIRouter(prefix="/api/predictive", tags=["预测性监控"])


class PredictionRequest(BaseModel):
    """预测请求"""
    metric_name: str = Field(..., description="指标名称")
    horizon_minutes: int = Field(default=30, ge=5, le=1440, description="预测时间范围（分钟）")
    datasource: Optional[str] = Field(default=None, description="数据源名称")


class PredictionResponse(BaseModel):
    """预测响应"""
    metric_name: str
    current_value: float
    predicted_value: float
    prediction_horizon: int
    confidence: str
    trend: str
    risk_level: str
    predicted_at: str
    metadata: Dict[str, Any]


class AnomalyDetectionRequest(BaseModel):
    """异常检测请求"""
    metric_name: str = Field(..., description="指标名称")
    threshold_multiplier: float = Field(default=3.0, ge=1.0, le=5.0, description="阈值倍数")
    datasource: Optional[str] = Field(default=None, description="数据源名称")


class AnomalyResponse(BaseModel):
    """异常响应"""
    id: str
    metric_name: str
    anomaly_type: str
    anomaly_score: float
    expected_value: float
    actual_value: float
    detected_at: str
    metadata: Dict[str, Any]


class SelfHealingRequest(BaseModel):
    """自愈建议请求"""
    anomaly_id: str = Field(..., description="异常 ID")


class SelfHealingResponse(BaseModel):
    """自愈建议响应"""
    id: str
    anomaly_id: str
    action_type: str
    description: str
    expected_impact: str
    confidence: str
    parameters: Dict[str, Any]
    dry_run: bool
    created_at: str


class CapacityForecastRequest(BaseModel):
    """容量预测请求"""
    days_ahead: int = Field(default=7, ge=1, le=30, description="预测天数")


class CapacityForecastResponse(BaseModel):
    """容量预测响应"""
    forecasts: Dict[str, Any]
    overall_risk: str
    risk_factors: List[str]
    forecast_horizon_days: int
    generated_at: str


class QueryPerformanceResponse(BaseModel):
    """查询性能分析响应"""
    metrics: Dict[str, Any]
    analyzed_at: str


@router.post("/predict", response_model=PredictionResponse, summary="预测指标值")
async def predict_metric(request: PredictionRequest):
    """
    预测指定指标的未来值

    - **metric_name**: 指标名称，如 query_latency_ms
    - **horizon_minutes**: 预测时间范围（分钟）
    - **datasource**: 可选的数据源名称
    """
    try:
        prediction = await predictive_monitoring_service.predict_metric(
            metric_name=request.metric_name,
            horizon_minutes=request.horizon_minutes,
            datasource=request.datasource
        )

        if prediction.metadata.get("error"):
            raise HTTPException(status_code=400, detail=prediction.metadata["error"])

        return PredictionResponse(**prediction.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to predict metric: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/anomaly/detect", response_model=List[AnomalyResponse], summary="检测异常")
async def detect_anomalies(request: AnomalyDetectionRequest):
    """
    检测指标异常

    使用 3-sigma 原则和趋势变化检测异常
    """
    try:
        anomalies = await predictive_monitoring_service.detect_anomalies(
            metric_name=request.metric_name,
            threshold_multiplier=request.threshold_multiplier,
            datasource=request.datasource
        )

        return [AnomalyResponse(**a.to_dict()) for a in anomalies]
    except Exception as e:
        logger.error(f"Failed to detect anomalies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/anomaly/{anomaly_id}/self-healing", response_model=SelfHealingResponse, summary="生成自愈建议")
async def generate_self_healing(anomaly_id: str):
    """
    为指定异常生成自愈建议

    - **anomaly_id**: 异常 ID
    """
    # 创建临时 Anomaly 对象
    anomaly = Anomaly(
        id=anomaly_id,
        metric_name="unknown",
        anomaly_type="unknown",
        anomaly_score=0.5
    )

    try:
        recommendation = await predictive_monitoring_service.generate_self_healing_recommendation(
            anomaly
        )

        if not recommendation:
            raise HTTPException(status_code=404, detail="No recommendation available")

        return SelfHealingResponse(**recommendation.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate self-healing recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/capacity/forecast", response_model=CapacityForecastResponse, summary="容量预测")
async def get_capacity_forecast(request: CapacityForecastRequest = None):
    """
    预测未来容量需求

    - **days_ahead**: 预测天数
    """
    days = request.days_ahead if request else 7

    try:
        forecast = await predictive_monitoring_service.get_capacity_forecast(
            days_ahead=days
        )

        return CapacityForecastResponse(**forecast)
    except Exception as e:
        logger.error(f"Failed to get capacity forecast: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/analysis", response_model=Dict[str, Any], summary="查询性能分析")
async def analyze_query_performance(
    datasource: Optional[str] = Query(default=None, description="数据源名称")
):
    """
    分析查询性能趋势

    返回关键性能指标的统计分析
    """
    try:
        analysis = await predictive_monitoring_service.analyze_query_performance(
            datasource=datasource
        )

        return {
            "metrics": analysis,
            "analyzed_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to analyze query performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/anomaly/history", response_model=List[AnomalyResponse], summary="异常历史")
async def get_anomaly_history(
    metric_name: Optional[str] = Query(default=None, description="指标名称"),
    hours: int = Query(default=24, ge=1, le=168, description="时间范围（小时）")
):
    """
    获取异常历史记录
    """
    try:
        anomalies = await predictive_monitoring_service.get_anomaly_history(
            metric_name=metric_name,
            hours=hours
        )

        return anomalies
    except Exception as e:
        logger.error(f"Failed to get anomaly history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=Dict[str, Any], summary="健康检查")
async def health_check():
    """
    预测性监控服务健康检查
    """
    return {
        "status": "healthy",
        "service": "predictive-monitoring",
        "timestamp": datetime.utcnow().isoformat()
    }
