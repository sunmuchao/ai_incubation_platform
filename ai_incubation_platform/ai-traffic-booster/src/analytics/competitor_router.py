"""
竞争情报 API 路由 (P4)
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import date
import random

from core.response import Response, success, error
from core.exceptions import AppException, ErrorCode
from schemas.competitor import (
    CompetitorCreateRequest,
    CompetitorAnalysisRequest,
    CompetitorTrackingRequest,
    CompetitorReportConfig
)
from analytics.competitor_service import competitor_service

# BusinessException 别名
BusinessException = AppException

router = APIRouter(prefix="/api/competitor", tags=["竞争情报"])


@router.post("/add", response_model=Response)
def add_competitor(request: CompetitorCreateRequest):
    """添加竞品"""
    try:
        competitor = competitor_service.add_competitor(request)
        return success(
            data={
                "competitor_id": competitor.competitor_id,
                "domain": competitor.domain,
                "name": competitor.name,
                "message": "竞品添加成功"
            },
            message="竞品添加成功"
        )
    except Exception as e:
        raise BusinessException(ErrorCode.INTERNAL_ERROR, str(e))


@router.get("/list", response_model=Response)
def list_competitors():
    """获取竞品列表"""
    try:
        competitors = competitor_service.list_competitors()
        return success(
            data={
                "competitors": [
                    {
                        "competitor_id": c.competitor_id,
                        "domain": c.domain,
                        "name": c.name,
                        "industry": c.industry,
                        "tags": c.tags,
                        "added_at": c.added_at.isoformat() if c.added_at else None
                    }
                    for c in competitors
                ],
                "total": len(competitors)
            },
            message="获取成功"
        )
    except Exception as e:
        raise BusinessException(ErrorCode.INTERNAL_ERROR, str(e))


@router.delete("/{competitor_id}", response_model=Response)
def remove_competitor(competitor_id: str):
    """移除竞品"""
    try:
        result = competitor_service.remove_competitor(competitor_id)
        if result:
            return success(data={"message": "竞品已移除"}, message="操作成功")
        else:
            raise BusinessException(ErrorCode.NOT_FOUND, "竞品不存在")
    except BusinessException:
        raise
    except Exception as e:
        raise BusinessException(ErrorCode.INTERNAL_ERROR, str(e))


@router.get("/{domain}/metrics", response_model=Response)
def get_competitor_metrics(domain: str):
    """获取竞品流量指标"""
    try:
        metrics = competitor_service.get_competitor_metrics(domain)
        return success(
            data=metrics.model_dump(),
            message="获取成功"
        )
    except Exception as e:
        raise BusinessException(ErrorCode.INTERNAL_ERROR, str(e))


@router.get("/{domain}/traffic-sources", response_model=Response)
def get_competitor_traffic_sources(domain: str):
    """获取竞品流量来源分布"""
    try:
        sources = competitor_service.get_competitor_traffic_sources(domain)
        return success(
            data=sources.model_dump(),
            message="获取成功"
        )
    except Exception as e:
        raise BusinessException(ErrorCode.INTERNAL_ERROR, str(e))


@router.get("/{domain}/keywords", response_model=Response)
def get_competitor_keywords(
    domain: str,
    limit: int = Query(default=20, ge=1, le=100, description="返回数量限制")
):
    """获取竞品关键词列表"""
    try:
        keywords = competitor_service.get_competitor_keywords(domain, limit)
        return success(
            data={
                "keywords": [kw.model_dump() for kw in keywords],
                "total": len(keywords)
            },
            message="获取成功"
        )
    except Exception as e:
        raise BusinessException(ErrorCode.INTERNAL_ERROR, str(e))


@router.get("/{domain}/top-pages", response_model=Response)
def get_competitor_top_pages(
    domain: str,
    limit: int = Query(default=10, ge=1, le=50, description="返回数量限制")
):
    """获取竞品热门页面"""
    try:
        pages = competitor_service.get_competitor_top_pages(domain, limit)
        return success(
            data={
                "pages": [p.model_dump() for p in pages],
                "total": len(pages)
            },
            message="获取成功"
        )
    except Exception as e:
        raise BusinessException(ErrorCode.INTERNAL_ERROR, str(e))


@router.post("/analyze", response_model=Response)
def analyze_competitors(request: CompetitorAnalysisRequest):
    """竞品对比分析"""
    try:
        if not request.domains:
            raise BusinessException(ErrorCode.BAD_REQUEST, "域名列表不能为空")

        result = competitor_service.analyze_competitors(request)
        return success(
            data=result.model_dump(),
            message="分析完成"
        )
    except BusinessException:
        raise
    except Exception as e:
        raise BusinessException(ErrorCode.INTERNAL_ERROR, str(e))


@router.get("/gap/keywords", response_model=Response)
def analyze_keyword_gap(
    your_domain: str = Query(..., description="你的域名"),
    competitor_domains: List[str] = Query(..., description="竞品域名列表")
):
    """关键词差距分析"""
    try:
        if not your_domain:
            raise BusinessException(ErrorCode.BAD_REQUEST, "你的域名不能为空")
        if not competitor_domains:
            raise BusinessException(ErrorCode.BAD_REQUEST, "竞品域名列表不能为空")

        result = competitor_service.analyze_keyword_gap(your_domain, competitor_domains)
        return success(
            data=result.model_dump(),
            message="分析完成"
        )
    except BusinessException:
        raise
    except Exception as e:
        raise BusinessException(ErrorCode.INTERNAL_ERROR, str(e))


@router.get("/gap/content", response_model=Response)
def analyze_content_gap(
    your_domain: str = Query(..., description="你的域名"),
    competitor_domains: List[str] = Query(..., description="竞品域名列表")
):
    """内容差距分析"""
    try:
        if not your_domain:
            raise BusinessException(ErrorCode.BAD_REQUEST, "你的域名不能为空")
        if not competitor_domains:
            raise BusinessException(ErrorCode.BAD_REQUEST, "竞品域名列表不能为空")

        result = competitor_service.analyze_content_gap(your_domain, competitor_domains)
        return success(
            data=result.model_dump(),
            message="分析完成"
        )
    except BusinessException:
        raise
    except Exception as e:
        raise BusinessException(ErrorCode.INTERNAL_ERROR, str(e))


@router.get("/gap/backlinks", response_model=Response)
def analyze_backlink_gap(
    your_domain: str = Query(..., description="你的域名"),
    competitor_domains: List[str] = Query(..., description="竞品域名列表")
):
    """反向链接差距分析"""
    try:
        if not your_domain:
            raise BusinessException(ErrorCode.BAD_REQUEST, "你的域名不能为空")
        if not competitor_domains:
            raise BusinessException(ErrorCode.BAD_REQUEST, "竞品域名列表不能为空")

        result = competitor_service.analyze_backlink_gap(your_domain, competitor_domains)
        return success(
            data=result.model_dump(),
            message="分析完成"
        )
    except BusinessException:
        raise
    except Exception as e:
        raise BusinessException(ErrorCode.INTERNAL_ERROR, str(e))


@router.get("/market-position", response_model=Response)
def get_market_position(
    your_domain: str = Query(..., description="你的域名"),
    competitor_domains: List[str] = Query(..., description="竞品域名列表")
):
    """市场定位分析"""
    try:
        if not your_domain:
            raise BusinessException(ErrorCode.BAD_REQUEST, "你的域名不能为空")
        if not competitor_domains:
            raise BusinessException(ErrorCode.BAD_REQUEST, "竞品域名列表不能为空")

        result = competitor_service.get_market_position(your_domain, competitor_domains)
        return success(
            data=result.model_dump(),
            message="分析完成"
        )
    except BusinessException:
        raise
    except Exception as e:
        raise BusinessException(ErrorCode.INTERNAL_ERROR, str(e))


@router.get("/benchmarks/{industry}", response_model=Response)
def get_industry_benchmarks(industry: str):
    """获取行业基准数据"""
    try:
        benchmarks = competitor_service.get_industry_benchmarks(industry)
        return success(
            data={
                "industry": industry,
                "benchmarks": [b.model_dump() for b in benchmarks]
            },
            message="获取成功"
        )
    except Exception as e:
        raise BusinessException(ErrorCode.INTERNAL_ERROR, str(e))


@router.post("/swot", response_model=Response)
def generate_swot(
    your_domain: str = Query(..., description="你的域名"),
    competitor_domains: List[str] = Query(..., description="竞品域名列表")
):
    """生成 SWOT 分析"""
    try:
        if not your_domain:
            raise BusinessException(ErrorCode.BAD_REQUEST, "你的域名不能为空")
        if not competitor_domains:
            raise BusinessException(ErrorCode.BAD_REQUEST, "竞品域名列表不能为空")

        result = competitor_service.generate_swot_analysis(your_domain, competitor_domains)
        return success(
            data=result.model_dump(),
            message="SWOT 分析完成"
        )
    except BusinessException:
        raise
    except Exception as e:
        raise BusinessException(ErrorCode.INTERNAL_ERROR, str(e))


@router.get("/alerts", response_model=Response)
def get_alerts(
    severity_threshold: str = Query(default="low", description="告警级别阈值"),
    limit: int = Query(default=20, ge=1, le=100, description="返回数量限制")
):
    """获取竞品告警列表"""
    try:
        alerts = competitor_service.get_alerts(severity_threshold, limit)
        return success(
            data={
                "alerts": [a.model_dump() for a in alerts],
                "total": len(alerts)
            },
            message="获取成功"
        )
    except Exception as e:
        raise BusinessException(ErrorCode.INTERNAL_ERROR, str(e))


@router.post("/alerts/create", response_model=Response)
def create_alert(
    competitor_domain: str = Query(..., description="竞品域名"),
    alert_type: str = Query(..., description="告警类型"),
    severity: str = Query(default="medium", description="告警级别")
):
    """创建竞品告警"""
    try:
        alert = competitor_service.create_alert(competitor_domain, alert_type, severity)
        return success(
            data=alert.model_dump(),
            message="告警创建成功"
        )
    except Exception as e:
        raise BusinessException(ErrorCode.INTERNAL_ERROR, str(e))


@router.get("/trends", response_model=Response)
def get_market_trends(
    category: Optional[str] = Query(default=None, description="趋势类别"),
    limit: int = Query(default=10, ge=1, le=50, description="返回数量限制")
):
    """获取市场趋势"""
    try:
        # 模拟市场趋势数据
        trends = []
        for i in range(limit):
            trends.append({
                "trend_id": f"trend_{i+1}",
                "trend_name": f"趋势主题 {i+1}",
                "category": category or "digital_marketing",
                "growth_rate": round(random.uniform(0.1, 2.0), 2),
                "confidence_score": round(random.uniform(0.6, 0.95), 2)
            })

        return success(
            data={
                "trends": trends,
                "total": len(trends)
            },
            message="获取成功"
        )
    except Exception as e:
        raise BusinessException(ErrorCode.INTERNAL_ERROR, str(e))
