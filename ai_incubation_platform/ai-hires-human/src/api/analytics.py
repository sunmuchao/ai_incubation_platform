"""
P10 高级分析与预测 - API 层。

提供高级分析与预测功能的 HTTP 接口。
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db_session
from services.advanced_analytics_service import AdvancedAnalyticsService, get_analytics_service
from models.analytics import (
    TaskSuccessPrediction,
    TaskSuccessBatchPrediction,
    WorkerChurnPrediction,
    WorkerChurnBatchPrediction,
    RevenuePrediction,
    AnomalyDetectionReport,
    AdvancedAnalyticsDashboard,
    PredictionQueryParams,
    AnalyticsQueryParams,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# ==================== 请求/响应模型 ====================

class TaskSuccessRequest(BaseModel):
    """任务成功概率预测请求。"""
    task_ids: Optional[List[int]] = None
    forecast_period: str = Field(default="30d", description="预测周期")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class WorkerChurnRequest(BaseModel):
    """工人流失预警请求。"""
    worker_ids: Optional[List[int]] = None
    risk_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class RevenueForecastRequest(BaseModel):
    """收入预测请求。"""
    forecast_period: str = Field(default="30d", description="预测周期 (7d/14d/30d/90d)")
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class AnomalyDetectionRequest(BaseModel):
    """异常检测请求。"""
    detection_period: str = Field(default="7d", description="检测周期")
    severity_threshold: str = Field(default="low", description="严重程度阈值")


# ==================== 任务成功概率预测接口 ====================

@router.get(
    "/task-success/{task_id}",
    response_model=TaskSuccessPrediction,
    summary="预测单个任务成功概率",
)
async def predict_task_success(
    task_id: int,
    confidence_threshold: float = Query(default=0.7, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db_session),
):
    """
    预测单个任务的成功概率。

    基于以下因素进行预测：
    - 任务报酬合理性
    - 工人历史表现
    - 任务复杂度
    - 时间紧迫性
    - 历史相似任务成功率

    **返回字段说明**:
    - `success_probability`: 成功概率 (0-1)
    - `risk_level`: 风险等级 (low/medium/high/critical)
    - `risk_factors`: 风险因素列表
    - `recommendations`: 改进建议
    """
    service = get_analytics_service(db)

    params = PredictionQueryParams(
        confidence_threshold=confidence_threshold,
    )

    try:
        prediction = await service.predict_task_success(task_id, params)
        return prediction
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.post(
    "/task-success/batch",
    response_model=TaskSuccessBatchPrediction,
    summary="批量预测任务成功概率",
)
async def predict_batch_task_success(
    request: TaskSuccessRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    批量预测任务的成功概率。

    可用于：
    - 雇主发布任务前评估成功率
    - 平台识别高风险任务
    - 优先推荐高成功率任务给工人
    """
    service = get_analytics_service(db)

    params = PredictionQueryParams(
        confidence_threshold=request.confidence_threshold,
        forecast_period=request.forecast_period,
    )

    try:
        predictions = await service.predict_batch_task_success(params)
        return predictions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch prediction failed: {str(e)}")


# ==================== 工人流失预警接口 ====================

@router.get(
    "/worker-churn/{worker_id}",
    response_model=WorkerChurnPrediction,
    summary="预测单个工人流失风险",
)
async def predict_worker_churn(
    worker_id: int,
    risk_threshold: float = Query(default=0.5, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db_session),
):
    """
    预测单个工人的流失风险。

    基于以下因素进行预测：
    - 工人活跃度变化
    - 收入趋势
    - 任务满意度（评分/成功率）
    - 任务获取频率

    **返回字段说明**:
    - `churn_probability`: 流失概率 (0-1)
    - `risk_level`: 风险等级 (low/medium/high/critical)
    - `predicted_churn_date`: 预测流失时间
    - `churn_reasons`: 流失原因分析
    - `retention_suggestions`: 保留建议
    """
    service = get_analytics_service(db)

    params = PredictionQueryParams(
        risk_threshold=risk_threshold,
    )

    try:
        prediction = await service.predict_worker_churn(worker_id, params)
        return prediction
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.post(
    "/worker-churn/batch",
    response_model=WorkerChurnBatchPrediction,
    summary="批量预测工人流失风险",
)
async def predict_batch_worker_churn(
    request: WorkerChurnRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    批量预测工人的流失风险。

    可用于：
    - 平台识别高流失风险工人群体
    - 制定针对性保留策略
    - 评估平台健康度
    """
    service = get_analytics_service(db)

    params = PredictionQueryParams(
        risk_threshold=request.risk_threshold,
    )

    try:
        predictions = await service.predict_batch_worker_churn(params)
        return predictions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch prediction failed: {str(e)}")


# ==================== 收入预测接口 ====================

@router.post(
    "/revenue/forecast",
    response_model=RevenuePrediction,
    summary="收入预测",
)
async def forecast_revenue(
    request: RevenueForecastRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    预测未来收入。

    基于历史数据和时间序列分析，预测未来收入趋势。

    **返回字段说明**:
    - `forecast`: 每日预测数据列表
    - `total_predicted_revenue`: 预测期总收入
    - `growth_rate`: 环比增长率
    - `key_drivers`: 关键驱动因素
    - `risk_warnings`: 风险提示

    **预测周期**:
    - 7d: 7 天预测
    - 14d: 14 天预测
    - 30d: 30 天预测（默认）
    - 90d: 90 天预测
    """
    service = get_analytics_service(db)

    # 解析日期
    start_date = None
    end_date = None
    if request.start_date:
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
    if request.end_date:
        end_date = datetime.strptime(request.end_date, "%Y-%m-%d")

    params = PredictionQueryParams(
        start_date=start_date,
        end_date=end_date,
        forecast_period=request.forecast_period,
    )

    try:
        prediction = await service.predict_revenue(params)
        return prediction
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Revenue forecast failed: {str(e)}")


# ==================== 异常检测接口 ====================

@router.post(
    "/anomaly/detect",
    response_model=AnomalyDetectionReport,
    summary="异常检测",
)
async def detect_anomalies(
    request: AnomalyDetectionRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    检测系统异常。

    检测类型包括：
    - 任务创建量异常
    - 工人活跃度异常
    - 支付异常
    - 质量异常

    **返回字段说明**:
    - `anomalies`: 异常列表
    - `total_anomalies`: 异常总数
    - `critical_count`: 严重异常数
    - `high_count`: 高危异常数
    - `trend`: 异常趋势 (improving/stable/worsening)
    """
    service = get_analytics_service(db)

    params = AnalyticsQueryParams()

    try:
        report = await service.detect_anomalies(params)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anomaly detection failed: {str(e)}")


@router.get(
    "/anomaly/summary",
    summary="异常检测摘要",
)
async def get_anomaly_summary(
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取异常检测摘要（快速概览）。
    """
    service = get_analytics_service(db)

    try:
        report = await service.detect_anomalies()
        return {
            "total_anomalies": report.total_anomalies,
            "critical_count": report.critical_count,
            "high_count": report.high_count,
            "trend": report.trend,
            "generated_at": report.generated_at.isoformat(),
            "top_anomalies": [
                {
                    "type": a.anomaly_type,
                    "severity": a.severity,
                    "deviation": a.deviation_percent,
                }
                for a in report.anomalies[:3]
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get anomaly summary: {str(e)}")


# ==================== 综合分析仪表板接口 ====================

@router.get(
    "/dashboard",
    response_model=AdvancedAnalyticsDashboard,
    summary="高级分析仪表板",
)
async def get_advanced_analytics_dashboard(
    forecast_period: str = Query(default="30d", description="预测周期"),
    confidence_threshold: float = Query(default=0.7, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取高级分析仪表板数据。

    整合所有预测分析功能，提供一站式数据分析视图。

    **包含内容**:
    - 任务成功概率预测摘要
    - 工人流失预警摘要
    - 收入预测摘要
    - 异常检测报告
    """
    service = get_analytics_service(db)

    params = PredictionQueryParams(
        forecast_period=forecast_period,
        confidence_threshold=confidence_threshold,
    )

    try:
        dashboard = await service.get_advanced_analytics_dashboard(params)
        return dashboard
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")


# ==================== 辅助接口 ====================

@router.get("/metrics", summary="获取可用分析指标列表")
async def get_analytics_metrics():
    """获取高级分析功能支持的所有指标定义。"""
    return {
        "task_success_prediction": {
            "description": "任务成功概率预测",
            "factors": ["报酬合理性", "工人表现", "任务复杂度", "时间紧迫性", "历史成功率"],
            "output": "success_probability, risk_level, recommendations",
        },
        "worker_churn_prediction": {
            "description": "工人流失预警",
            "factors": ["活跃度", "收入趋势", "满意度", "任务频率"],
            "output": "churn_probability, risk_level, retention_suggestions",
        },
        "revenue_forecast": {
            "description": "收入预测",
            "periods": ["7d", "14d", "30d", "90d"],
            "output": "daily_forecast, total_revenue, growth_rate",
        },
        "anomaly_detection": {
            "description": "异常检测",
            "types": ["任务量异常", "活跃度异常", "支付异常", "质量异常"],
            "output": "anomalies, severity, recommended_actions",
        },
    }


@router.get("/help/prediction-accuracy", summary="预测准确度说明")
async def get_prediction_accuracy_info():
    """获取预测模型准确度说明。"""
    return {
        "task_success_prediction": {
            "accuracy": "约 75-85%",
            "description": "基于历史任务数据和工人表现的预测准确度",
            "limitations": [
                "新类型任务预测准确度较低",
                "极端情况（如极高/极低报酬）预测可能偏差较大"
            ]
        },
        "worker_churn_prediction": {
            "accuracy": "约 70-80%",
            "description": "基于工人行为和收入数据的流失预测准确度",
            "limitations": [
                "需要至少 30 天历史数据",
                "突发事件（如疫情）可能影响预测准确度"
            ]
        },
        "revenue_forecast": {
            "accuracy": "约 65-75% (7 天预测)",
            "description": "基于时间序列分析的收入预测准确度",
            "limitations": [
                "预测周期越长，准确度越低",
                "市场突变无法预测"
            ]
        },
    }
