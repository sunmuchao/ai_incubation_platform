"""
AI 异常检测 API - P1 AI 异常检测

提供流量异常检测、关键词排名异常检测等功能
"""
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from pydantic import BaseModel, Field

from ai.anomaly_detection import (
    anomaly_detection_service,
    AnomalyDetectionResult,
    AnomalySeverity,
    AnomalyType,
)


router = APIRouter(prefix="/ai/anomaly", tags=["AI Anomaly Detection"])


# ==================== Schema 定义 ====================

class AnomalyCheckRequest(BaseModel):
    """异常检测请求"""
    metric_name: str
    current_value: float
    historical_values: List[float]
    context: Optional[Dict[str, Any]] = None


class AnomalyCheckResponse(BaseModel):
    """异常检测响应"""
    is_anomaly: bool
    anomaly_type: Optional[str]
    severity: Optional[str]
    metric_name: str
    current_value: float
    expected_value: float
    deviation: float
    z_score: float
    confidence: float
    description: str
    detected_at: str


class TrafficAnomalyCheckRequest(BaseModel):
    """流量异常检测请求"""
    domain: Optional[str] = None
    check_date: Optional[date] = None


# ==================== API 端点 ====================

@router.post("/detect", response_model=AnomalyCheckResponse)
async def detect_anomaly(
    request: AnomalyCheckRequest,
):
    """
    检测单个指标的异常

    - **metric_name**: 指标名称（如 visitors, page_views, conversion_rate）
    - **current_value**: 当前值
    - **historical_values**: 历史值列表（用于建立基线）
    - **context**: 上下文信息（可选）

    返回异常检测结果，包括：
    - is_anomaly: 是否异常
    - anomaly_type: 异常类型
    - severity: 严重级别
    - z_score: Z 分数
    - confidence: 置信度
    """
    result = anomaly_detection_service.detect_anomalies(
        metric_name=request.metric_name,
        current_value=request.current_value,
        historical_values=request.historical_values,
        context=request.context,
    )
    return result.to_dict()


@router.post("/traffic", response_model=List[AnomalyCheckResponse])
async def detect_traffic_anomaly(
    request: TrafficAnomalyCheckRequest = None,
    domain: Optional[str] = Query(None, description="域名"),
    check_date: Optional[date] = Query(None, description="检查日期"),
):
    """
    检测流量相关指标的异常

    自动检测以下指标的异常：
    - 访客数 (visitors)
    - 页面浏览量 (page_views)
    - 转化率 (conversion_rate)
    - 跳出率 (bounce_rate)

    返回所有检测到的异常列表
    """
    if request is None:
        request = TrafficAnomalyCheckRequest(domain=domain, check_date=check_date)

    results = anomaly_detection_service.detect_traffic_anomaly(
        domain=request.domain,
        check_date=request.check_date,
    )

    return [r.to_dict() for r in results]


@router.get("/traffic/summary")
async def get_traffic_anomaly_summary(
    days: int = Query(7, ge=1, le=30, description="天数"),
    domain: Optional[str] = Query(None, description="域名"),
):
    """
    获取流量异常摘要

    返回指定天数内的异常统计信息
    """
    from datetime import timedelta

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    summary = {
        "total_anomalies": 0,
        "by_severity": {"critical": 0, "warning": 0, "info": 0},
        "by_type": {},
        "by_metric": {},
        "recent_anomalies": [],
    }

    # 逐日检测异常
    current_date = start_date
    while current_date <= end_date:
        try:
            results = anomaly_detection_service.detect_traffic_anomaly(
                domain=domain,
                check_date=current_date,
            )

            for result in results:
                if result.is_anomaly:
                    summary["total_anomalies"] += 1

                    severity = result.severity.value if result.severity else "info"
                    anomaly_type = result.anomaly_type.value if result.anomaly_type else "unknown"

                    summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
                    summary["by_type"][anomaly_type] = summary["by_type"].get(anomaly_type, 0) + 1
                    summary["by_metric"][result.metric_name] = summary["by_metric"].get(result.metric_name, 0) + 1

                    if len(summary["recent_anomalies"]) < 10:
                        summary["recent_anomalies"].append(result.to_dict())

        except Exception as e:
            pass

        current_date += timedelta(days=1)

    return summary


@router.post("/keyword-ranking", response_model=AnomalyCheckResponse)
async def detect_keyword_ranking_anomaly(
    keyword: str = Query(..., description="关键词"),
    current_position: int = Query(..., description="当前排名"),
    historical_positions: List[int] = Body(..., description="历史排名列表"),
):
    """
    检测关键词排名异常

    - **keyword**: 关键词
    - **current_position**: 当前排名
    - **historical_positions**: 历史排名列表

    排名是反向指标（数值越小越好），服务会自动处理
    """
    result = anomaly_detection_service.detect_keyword_ranking_anomaly(
        keyword=keyword,
        current_position=current_position,
        historical_positions=historical_positions,
    )
    return result.to_dict()


@router.get("/methods")
async def get_detection_methods():
    """
    获取异常检测方法说明

    返回支持的统计方法和阈值配置
    """
    return {
        "methods": [
            {
                "name": "Z-score",
                "description": "检测偏离均值的标准差数",
                "warning_threshold": anomaly_detection_service.z_score_warning_threshold,
                "critical_threshold": anomaly_detection_service.z_score_critical_threshold,
            },
            {
                "name": "Grubbs 检验",
                "description": "检测单个异常值",
                "significance_level": anomaly_detection_service.significance_level,
            },
            {
                "name": "移动平均",
                "description": "检测趋势异常",
                "min_sample_size": anomaly_detection_service.min_sample_size,
            },
        ],
        "severity_levels": [
            {"level": "critical", "description": "严重异常，需要立即处理"},
            {"level": "warning", "description": "警告级别，需要关注"},
            {"level": "info", "description": "信息级别，可供参考"},
        ],
        "anomaly_types": [
            {"type": "traffic_drop", "description": "流量下跌"},
            {"type": "traffic_spike", "description": "流量激增"},
            {"type": "conversion_drop", "description": "转化率下跌"},
            {"type": "conversion_spike", "description": "转化率激增"},
            {"type": "bounce_rate_spike", "description": "跳出率激增"},
            {"type": "ranking_drop", "description": "排名下跌"},
        ],
    }


@router.post("/grubbs-test")
async def grubbs_test(
    values: List[float] = Body(..., description="数据列表"),
):
    """
    执行 Grubbs 检验

    用于检测数据中的单个异常值

    返回：
    - is_outlier: 是否存在异常值
    - G_critical: 临界值
    - outlier_index: 异常值索引（如果存在）
    """
    is_outlier, g_critical, outlier_idx = anomaly_detection_service.grubbs_test(values)

    return {
        "is_outlier": is_outlier,
        "G_critical": round(g_critical, 4),
        "outlier_index": outlier_idx,
        "outlier_value": values[outlier_idx] if outlier_idx >= 0 else None,
        "data_count": len(values),
    }
