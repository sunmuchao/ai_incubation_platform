"""
from pydantic import BaseModel, Field
AI 优化建议 API - P2 可执行建议生成

提供优化建议生成、查询和管理功能
"""
from pydantic import BaseModel, Field
from datetime import date
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from ai.anomaly_detection import anomaly_detection_service
from ai.root_cause_analysis import root_cause_analysis_service
from ai.recommendation_engine import recommendation_engine, OptimizationSuggestion, SuggestionPriority


router = APIRouter(prefix="/ai/suggestions", tags=["AI Optimization Suggestions"])


# ==================== Schema 定义 ====================

class SuggestionResponse(BaseModel):
    """优化建议响应"""
    suggestion_id: str
    title: str
    description: str
    suggestion_type: str
    priority: str
    effort: str
    expected_impact: float
    confidence: float
    action_steps: List[str]
    related_metrics: List[str]
    estimated_timeline: str
    data_evidence: List[str]
    created_at: str


class GenerateSuggestionsRequest(BaseModel):
    """生成建议请求"""
    metric_name: Optional[str] = None
    current_value: Optional[float] = None
    historical_values: Optional[List[float]] = None
    domain: Optional[str] = None
    check_date: Optional[date] = None


# ==================== API 端点 ====================

@router.post("/generate", response_model=List[SuggestionResponse])
async def generate_suggestions(
    request: GenerateSuggestionsRequest,
):
    """
    生成优化建议

    基于异常检测和根因分析，生成可执行的优化建议

    - **metric_name**: 指标名称（可选）
    - **current_value**: 当前值（可选）
    - **historical_values**: 历史值列表（可选）
    - **domain**: 域名（可选）
    - **check_date**: 检查日期（可选）

    如果提供了指标数据，将基于异常检测生成针对性建议；
    否则将生成常规的主动优化建议。
    """
    # 如果有指标数据，先进行异常检测和根因分析
    if request.metric_name and request.current_value and request.historical_values:
        # 异常检测
        anomaly_result = anomaly_detection_service.detect_anomalies(
            metric_name=request.metric_name,
            current_value=request.current_value,
            historical_values=request.historical_values,
        )

        if anomaly_result.is_anomaly:
            # 根因分析
            analysis_result = root_cause_analysis_service.analyze(
                anomaly=anomaly_result,
                domain=request.domain,
                check_date=request.check_date,
            )

            # 生成建议
            suggestions = recommendation_engine.generate_suggestions(analysis_result)
            return [s.to_dict() for s in suggestions]

    # 生成主动优化建议
    suggestions = recommendation_engine.generate_proactive_suggestions(
        domain=request.domain,
        check_date=request.check_date,
    )
    return [s.to_dict() for s in suggestions]


@router.get("/traffic", response_model=List[SuggestionResponse])
async def generate_traffic_suggestions(
    domain: Optional[str] = Query(None, description="域名"),
    check_date: Optional[date] = Query(None, description="检查日期"),
):
    """
    生成流量优化建议

    基于昨日流量数据自动生成优化建议
    """
    if check_date is None:
        check_date = date.today() - timedelta(days=1)

    # 检测流量异常
    anomaly_results = anomaly_detection_service.detect_traffic_anomaly(
        domain=domain,
        check_date=check_date,
    )

    all_suggestions = []

    if anomaly_results:
        for anomaly in anomaly_results:
            if anomaly.is_anomaly:
                # 根因分析
                analysis_result = root_cause_analysis_service.analyze(
                    anomaly=anomaly,
                    domain=domain,
                    check_date=check_date,
                )
                # 生成建议
                suggestions = recommendation_engine.generate_suggestions(analysis_result)
                all_suggestions.extend(suggestions)

    # 去重
    seen_titles = set()
    unique_suggestions = []
    for s in all_suggestions:
        if s.title not in seen_titles:
            seen_titles.add(s.title)
            unique_suggestions.append(s)

    return [s.to_dict() for s in unique_suggestions]


@router.get("/proactive", response_model=List[SuggestionResponse])
async def generate_proactive_suggestions(
    domain: Optional[str] = Query(None, description="域名"),
):
    """
    生成主动优化建议

    在无异常情况下，提供常规的 SEO 和内容优化建议
    """
    suggestions = recommendation_engine.generate_proactive_suggestions(domain=domain)
    return [s.to_dict() for s in suggestions]


@router.get("/priority/{priority}")
async def get_suggestions_by_priority(
    priority: str,
    domain: Optional[str] = Query(None, description="域名"),
):
    """
    按优先级获取优化建议

    优先级：critical, high, medium, low
    """
    all_suggestions = await generate_proactive_suggestions(domain=domain)

    filtered = [s for s in all_suggestions if s["priority"] == priority]
    return {"priority": priority, "suggestions": filtered, "total": len(filtered)}


@router.get("/type/{suggestion_type}")
async def get_suggestions_by_type(
    suggestion_type: str,
    domain: Optional[str] = Query(None, description="域名"),
):
    """
    按类型获取优化建议

    类型：seo_optimization, content_improvement, traffic_acquisition, etc.
    """
    all_suggestions = await generate_proactive_suggestions(domain=domain)

    filtered = [s for s in all_suggestions if s["suggestion_type"] == suggestion_type]
    return {"type": suggestion_type, "suggestions": filtered, "total": len(filtered)}


@router.get("/categories")
async def get_suggestion_categories():
    """
    获取建议类别说明

    返回所有支持的建议类型和优先级说明
    """
    from ai.recommendation_engine import SuggestionType, SuggestionPriority, SuggestionEffort

    return {
        "suggestion_types": [
            {"type": t.value, "name": t.name.replace("_", " ").title()}
            for t in SuggestionType
        ],
        "priorities": [
            {"priority": p.value, "name": p.name, "description": _get_priority_desc(p)}
            for p in SuggestionPriority
        ],
        "effort_levels": [
            {"effort": e.value, "name": e.name, "description": _get_effort_desc(e)}
            for e in SuggestionEffort
        ],
    }


def _get_priority_desc(priority) -> str:
    """获取优先级描述"""
    descs = {
        SuggestionPriority.CRITICAL: "紧急，需立即处理",
        SuggestionPriority.HIGH: "高优先级，建议优先处理",
        SuggestionPriority.MEDIUM: "中优先级，按计划处理",
        SuggestionPriority.LOW: "低优先级，有空时处理",
    }
    return descs.get(priority, "")


def _get_effort_desc(effort) -> str:
    """获取努力程度描述"""
    descs = {
        SuggestionEffort.LOW: "低难度，可快速实施（1-2 天）",
        SuggestionEffort.MEDIUM: "中等难度，需要一定资源（3-7 天）",
        SuggestionEffort.HIGH: "高难度，需要较多资源（1-2 周）",
    }
    return descs.get(effort, "")


@router.get("/sample")
async def get_sample_suggestions():
    """
    获取示例优化建议

    展示各种类型和优先级的建议示例
    """
    samples = [
        {
            "suggestion_id": "sample_001",
            "title": "优化核心关键词排名",
            "description": "针对排名下滑的核心关键词进行内容优化",
            "suggestion_type": "seo_optimization",
            "priority": "high",
            "effort": "medium",
            "expected_impact": 0.20,
            "confidence": 0.80,
            "action_steps": [
                "分析下滑关键词的搜索意图",
                "对比竞品内容找出差距",
                "更新页面内容增加价值",
                "增加相关内部链接"
            ],
            "related_metrics": ["keyword_rankings", "organic_traffic"],
            "estimated_timeline": "1-2 周",
            "data_evidence": ["5 个核心关键词排名下滑平均 3 位"]
        },
        {
            "suggestion_id": "sample_002",
            "title": "拓展长尾关键词内容",
            "description": "创建针对长尾关键词的专题内容",
            "suggestion_type": "traffic_acquisition",
            "priority": "medium",
            "effort": "medium",
            "expected_impact": 0.15,
            "confidence": 0.75,
            "action_steps": [
                "使用关键词工具发现机会",
                "创建针对性内容页面",
                "在现有内容中融入长尾词",
                "监控排名和流量变化"
            ],
            "related_metrics": ["organic_traffic", "keyword_count"],
            "estimated_timeline": "2-4 周",
            "data_evidence": ["长尾词贡献 40% 的自然流量"]
        },
        {
            "suggestion_id": "sample_003",
            "title": "优化页面加载速度",
            "description": "提升页面加载速度改善用户体验和 SEO",
            "suggestion_type": "technical_fix",
            "priority": "high",
            "effort": "medium",
            "expected_impact": 0.12,
            "confidence": 0.85,
            "action_steps": [
                "压缩图片和静态资源",
                "启用浏览器缓存",
                "优化 JavaScript 执行",
                "考虑使用 CDN 加速"
            ],
            "related_metrics": ["page_load_time", "bounce_rate"],
            "estimated_timeline": "3-5 天",
            "data_evidence": ["当前页面加载时间 4.2 秒，高于行业平均 2.5 秒"]
        }
    ]

    return {
        "samples": samples,
        "total": len(samples),
        "note": "这些是示例建议，实际建议将基于您的数据生成"
    }
