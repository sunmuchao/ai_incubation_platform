"""
AI 根因分析 API - P1 AI 根因分析

提供流量异常根因分析、归因分析等功能
"""
from datetime import date
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field

from ai.anomaly_detection import anomaly_detection_service, AnomalyDetectionResult
from ai.root_cause_analysis import (
    root_cause_analysis_service,
    RootCauseAnalysisResult,
    RootCauseCategory,
    RootCauseConfidence,
)


router = APIRouter(prefix="/ai/root-cause", tags=["AI Root Cause Analysis"])


# ==================== Schema 定义 ====================

class RootCauseAnalysisRequest(BaseModel):
    """根因分析请求"""
    metric_name: str
    current_value: float
    historical_values: List[float]
    domain: Optional[str] = None
    check_date: Optional[date] = None


class RootCauseResponse(BaseModel):
    """根因响应"""
    category: str
    description: str
    confidence: str
    evidence: List[str]
    impact_score: float
    contributing_factors: List[Dict[str, Any]]
    recommended_actions: List[str]


class RootCauseAnalysisResponse(BaseModel):
    """根因分析完整响应"""
    anomaly: Dict[str, Any]
    root_causes: List[RootCauseResponse]
    primary_cause: Optional[RootCauseResponse]
    analysis_summary: str
    analyzed_at: str


# ==================== API 端点 ====================

@router.post("/analyze", response_model=RootCauseAnalysisResponse)
async def analyze_root_cause(
    request: RootCauseAnalysisRequest,
):
    """
    执行根因分析

    1. 首先检测指标异常
    2. 对检测到的异常进行多维度根因分析
    3. 返回分析结果和建议行动

    - **metric_name**: 指标名称
    - **current_value**: 当前值
    - **historical_values**: 历史值列表（用于建立基线）
    - **domain**: 域名（可选）
    - **check_date**: 检查日期（可选）
    """
    # 步骤 1: 异常检测
    anomaly_result = anomaly_detection_service.detect_anomalies(
        metric_name=request.metric_name,
        current_value=request.current_value,
        historical_values=request.historical_values,
    )

    if not anomaly_result.is_anomaly:
        return {
            "anomaly": anomaly_result.to_dict(),
            "root_causes": [],
            "primary_cause": None,
            "analysis_summary": "未检测到异常，指标在正常范围内",
            "analyzed_at": anomaly_result.detected_at.isoformat(),
        }

    # 步骤 2: 根因分析
    analysis_result = root_cause_analysis_service.analyze(
        anomaly=anomaly_result,
        domain=request.domain,
        check_date=request.check_date,
    )

    return analysis_result.to_dict()


@router.get("/analyze/traffic")
async def analyze_traffic_root_cause(
    domain: Optional[str] = Query(None, description="域名"),
    check_date: Optional[date] = Query(None, description="检查日期"),
):
    """
    分析流量异常的根因

    自动检测昨日流量异常并进行根因分析
    """
    if check_date is None:
        check_date = date.today() - timedelta(days=1)

    # 检测流量异常
    anomaly_results = anomaly_detection_service.detect_traffic_anomaly(
        domain=domain,
        check_date=check_date,
    )

    if not anomaly_results:
        return {
            "status": "no_anomaly",
            "message": "未检测到流量异常",
            "check_date": check_date.isoformat(),
        }

    # 对每个异常进行根因分析
    analyses = []
    for anomaly in anomaly_results:
        if anomaly.is_anomaly:
            analysis = root_cause_analysis_service.analyze(
                anomaly=anomaly,
                domain=domain,
                check_date=check_date,
            )
            analyses.append(analysis.to_dict())

    return {
        "status": "completed",
        "anomalies_detected": len(anomaly_results),
        "analyses": analyses,
        "check_date": check_date.isoformat(),
    }


@router.get("/categories")
async def get_root_cause_categories():
    """
    获取根因类别说明

    返回所有支持的根因类别及其含义
    """
    return {
        "categories": [
            {
                "category": RootCauseCategory.TRAFFIC_SOURCE.value,
                "name": "流量来源问题",
                "description": "某个流量来源渠道出现显著变化"
            },
            {
                "category": RootCauseCategory.KEYWORD_RANKING.value,
                "name": "关键词排名问题",
                "description": "核心关键词排名下滑或掉出排名"
            },
            {
                "category": RootCauseCategory.PAGE_PERFORMANCE.value,
                "name": "页面性能问题",
                "description": "页面 SEO 分数偏低或退出率过高"
            },
            {
                "category": RootCauseCategory.DEVICE_ISSUE.value,
                "name": "设备兼容问题",
                "description": "某个设备端流量显著变化"
            },
            {
                "category": RootCauseCategory.GEO_ISSUE.value,
                "name": "地域问题",
                "description": "某个地区流量显著变化"
            },
            {
                "category": RootCauseCategory.CONTENT_ISSUE.value,
                "name": "内容问题",
                "description": "内容质量或用户意图匹配度问题"
            },
            {
                "category": RootCauseCategory.TECHNICAL_ISSUE.value,
                "name": "技术问题",
                "description": "网站技术故障或性能问题"
            },
            {
                "category": RootCauseCategory.SEASONAL.value,
                "name": "季节性波动",
                "description": "正常的季节性或周期性波动"
            },
            {
                "category": RootCauseCategory.COMPETITOR.value,
                "name": "竞品影响",
                "description": "竞争对手动作导致的影响"
            },
        ],
        "confidence_levels": [
            {
                "level": RootCauseConfidence.HIGH.value,
                "description": "高置信度 (>80%)",
                "action": "建议优先处理"
            },
            {
                "level": RootCauseConfidence.MEDIUM.value,
                "description": "中置信度 (50-80%)",
                "action": "建议关注"
            },
            {
                "level": RootCauseConfidence.LOW.value,
                "description": "低置信度 (<50%)",
                "action": "仅供参考"
            },
        ],
    }


@router.get("/methodology")
async def get_analysis_methodology():
    """
    获取根因分析方法论说明

    返回分析流程、维度和技术说明
    """
    return {
        "methodology": {
            "name": "多维度归因分析框架",
            "description": "通过多个维度交叉分析，定位流量异常的根本原因",
            "analysis_dimensions": [
                {
                    "dimension": "流量来源维度",
                    "metrics": ["organic_search", "direct", "social_media", "referral", "paid_ad", "email"],
                    "analysis": "对比各来源占比变化，识别显著波动的渠道"
                },
                {
                    "dimension": "关键词排名维度",
                    "metrics": ["position", "search_volume", "ctr"],
                    "analysis": "分析核心关键词排名变化，识别排名下滑的关键词"
                },
                {
                    "dimension": "页面性能维度",
                    "metrics": ["seo_score", "exit_rate", "bounce_rate"],
                    "analysis": "识别 SEO 分数偏低或退出率过高的页面"
                },
                {
                    "dimension": "设备分布维度",
                    "metrics": ["desktop", "mobile", "tablet"],
                    "analysis": "对比各设备端流量变化，识别设备兼容性问题"
                },
                {
                    "dimension": "地域分布维度",
                    "metrics": ["country", "region", "city"],
                    "analysis": "分析各地区流量变化，识别地域性问题"
                },
                {
                    "dimension": "流量质量维度",
                    "metrics": ["bounce_rate", "session_duration", "conversion_rate"],
                    "analysis": "评估流量质量变化，识别低质流量"
                },
            ],
            "decision_tree": {
                "step1": "检测指标异常（Z-score > 2）",
                "step2": "根据异常类型选择分析维度",
                "step3": "多维度归因分析",
                "step4": "按影响分数排序根因",
                "step5": "生成可执行建议"
            },
            "confidence_calculation": {
                "factors": [
                    "数据变化幅度（越大越可信）",
                    "样本量大小（越多越可信）",
                    "维度一致性（多个维度指向同一原因越可信）",
                    "历史模式匹配（与历史模式一致越可信）"
                ]
            }
        }
    }


@router.get("/recent/{domain}")
async def get_recent_analyses(
    domain: str,
    limit: int = Query(10, ge=1, le=50, description="限制数量"),
):
    """
    获取指定域名最近的根因分析记录

    从日志系统中检索历史分析记录
    """
    from services.log_service import get_log_service

    log_service = get_log_service()

    # 查询 AI 分析日志
    logs = log_service.get_logs(
        logger_name="ai.analysis",
        search_keyword="root_cause",
        limit=limit,
    )

    analyses = []
    for log in logs:
        if log.extra_data:
            analyses.append({
                "analyzed_at": log.created_at.isoformat(),
                "analysis_type": log.extra_data.get("analysis_type"),
                "metric_name": log.extra_data.get("metric_name"),
                "summary": log.message,
            })

    return {
        "domain": domain,
        "analyses": analyses,
        "total": len(analyses),
    }
