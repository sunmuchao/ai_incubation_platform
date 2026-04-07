"""
真实数据源 API 端点 - P0 真实数据源

提供与真实数据源（Google Search Console, Ahrefs, SEMrush）交互的 API 接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response as FastAPIResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
from datetime import date, timedelta
from pydantic import BaseModel, Field

from db import get_db
from core.response import Response, ErrorCode
from data_sources.data_source_service import (
    get_data_source_service,
    DataSourceIntegrationService,
    FusedKeywordData
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data-sources", tags=["数据源管理"])


# ==================== 请求/响应模型 ====================

class KeywordSuggestionsRequest(BaseModel):
    """关键词建议请求"""
    seed_keywords: List[str] = Field(..., description="种子关键词列表", min_items=1, max_items=10)
    source: Optional[str] = Field(default=None, description="数据源：semrush, ahrefs, google_search_console")
    country: Optional[str] = Field(default="us", description="国家/地区")
    language: Optional[str] = Field(default="en", description="语言")
    limit: Optional[int] = Field(default=100, ge=1, le=1000, description="返回数量限制")


class KeywordMetricsRequest(BaseModel):
    """关键词指标请求"""
    keywords: List[str] = Field(..., description="关键词列表", min_items=1, max_items=100)
    source: Optional[str] = Field(default=None, description="数据源")
    country: Optional[str] = Field(default="us", description="国家/地区")


class KeywordRankingRequest(BaseModel):
    """关键词排名请求"""
    domain: str = Field(..., description="域名")
    keywords: List[str] = Field(..., description="关键词列表", min_items=1, max_items=100)
    source: Optional[str] = Field(default=None, description="数据源")
    country: Optional[str] = Field(default="us", description="国家/地区")


class CompetitorRequest(BaseModel):
    """竞品分析请求"""
    domain: str = Field(..., description="域名")
    source: Optional[str] = Field(default=None, description="数据源：semrush, ahrefs")
    country: Optional[str] = Field(default="us", description="国家/地区")
    limit: Optional[int] = Field(default=50, ge=1, le=500, description="返回数量限制")


class CompetitorTrafficRequest(BaseModel):
    """竞品流量请求"""
    domain: str = Field(..., description="域名")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    source: Optional[str] = Field(default=None, description="数据源")
    country: Optional[str] = Field(default="us", description="国家/地区")


class DataExportRequest(BaseModel):
    """数据导出请求"""
    data_type: str = Field(..., description="数据类型：keywords, suggestions, competitors, rankings")
    format: str = Field(default="csv", description="导出格式：csv, excel")
    params: Dict[str, Any] = Field(default={}, description="查询参数")


class DataFuseRequest(BaseModel):
    """多数据源融合请求"""
    keywords: List[str] = Field(..., description="关键词列表", min_items=1, max_items=100)
    sources: Optional[List[str]] = Field(default=None, description="数据源列表")
    country: Optional[str] = Field(default="us", description="国家/地区")


# ==================== 数据源管理端点 ====================

@router.get("/available", summary="获取可用数据源", description="列出所有可用的数据源")
async def get_available_sources(
    data_service: DataSourceIntegrationService = Depends(get_data_source_service)
) -> Response:
    """获取可用数据源列表"""
    try:
        sources = data_service.get_available_sources()
        return Response(code=0, message="success", data=sources)
    except Exception as e:
        logger.error(f"Failed to get available sources: {e}")
        return Response(code=ErrorCode.INTERNAL_ERROR, message=f"Failed to get available sources: {str(e)}", data={})


@router.post("/cache/clear", summary="清除缓存", description="清除数据源缓存")
async def clear_cache(
    pattern: Optional[str] = Query(default=None, description="缓存键模式"),
    data_service: DataSourceIntegrationService = Depends(get_data_source_service)
) -> Response:
    """清除缓存"""
    try:
        data_service.clear_cache(pattern)
        return Response(code=0, message="Cache cleared successfully", data={})
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        return Response(code=ErrorCode.INTERNAL_ERROR, message=f"Failed to clear cache: {str(e)}", data={})


# ==================== v1.6 新增端点 ====================

@router.get("/health", summary="数据源健康检查", description="检查所有数据源的健康状态和 API 配额")
async def check_data_sources_health(
    data_service: DataSourceIntegrationService = Depends(get_data_source_service)
) -> Response:
    """检查数据源健康状态"""
    try:
        health_report = data_service.check_health()
        return Response(code=0, message="success", data=health_report)
    except Exception as e:
        logger.error(f"Failed to check data sources health: {e}")
        return Response(code=ErrorCode.INTERNAL_ERROR, message=f"Failed to check health: {str(e)}", data={})


@router.get("/quota", summary="API 配额查询", description="查询各数据源的 API 配额使用情况")
async def get_quota(
    source: Optional[str] = Query(default=None, description="指定数据源"),
    data_service: DataSourceIntegrationService = Depends(get_data_source_service)
) -> Response:
    """获取配额信息"""
    try:
        quota_info = data_service.get_quota_info(source)
        return Response(code=0, message="success", data=quota_info)
    except Exception as e:
        logger.error(f"Failed to get quota info: {e}")
        return Response(code=ErrorCode.INTERNAL_ERROR, message=f"Failed to get quota: {str(e)}", data={})


@router.post("/export", summary="数据导出", description="导出数据为 CSV 或 Excel 格式")
async def export_data(
    request: DataExportRequest,
    data_service: DataSourceIntegrationService = Depends(get_data_source_service)
) -> FastAPIResponse:
    """导出数据"""
    try:
        file_bytes = data_service.export_data(
            data_type=request.data_type,
            params=request.params,
            format=request.format
        )
        media_type = "text/csv" if request.format.lower() == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"export_{request.data_type}.{request.format.lower()}"
        return FastAPIResponse(
            content=file_bytes,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError as e:
        logger.error(f"Invalid export request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to export data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fuse", summary="多数据源融合", description="融合多个数据源的关键词数据")
async def fuse_keyword_data(
    request: DataFuseRequest,
    data_service: DataSourceIntegrationService = Depends(get_data_source_service)
) -> Response:
    """融合多数据源数据"""
    try:
        fused_data = data_service.fuse_keyword_data(
            keywords=request.keywords,
            sources=request.sources,
            country=request.country
        )
        return Response(
            code=0,
            message="success",
            data={
                "fused_keywords": [item.to_dict() for item in fused_data],
                "total": len(fused_data),
                "sources_used": list(set(src for item in fused_data for src in item.sources))
            }
        )
    except Exception as e:
        logger.error(f"Failed to fuse keyword data: {e}")
        return Response(code=ErrorCode.INTERNAL_ERROR, message=f"Failed to fuse data: {str(e)}", data={})


# ==================== 关键词数据端点 ====================

@router.post("/keywords/suggestions", summary="获取关键词建议", description="从真实数据源获取关键词建议")
async def get_keyword_suggestions(
    request: KeywordSuggestionsRequest,
    data_service: DataSourceIntegrationService = Depends(get_data_source_service)
) -> Response:
    """获取关键词建议"""
    try:
        suggestions = data_service.get_keyword_suggestions(
            seed_keywords=request.seed_keywords,
            source=request.source,
            country=request.country,
            language=request.language,
            limit=request.limit
        )
        return Response(code=0, message="success", data={"suggestions": suggestions, "total": len(suggestions), "source_used": request.source or "auto"})
    except Exception as e:
        logger.error(f"Failed to get keyword suggestions: {e}")
        return Response(code=ErrorCode.INTERNAL_ERROR, message=f"Failed to get keyword suggestions: {str(e)}", data={})


@router.post("/keywords/metrics", summary="获取关键词指标", description="从真实数据源获取关键词详细指标")
async def get_keyword_metrics(
    request: KeywordMetricsRequest,
    data_service: DataSourceIntegrationService = Depends(get_data_source_service)
) -> Response:
    """获取关键词指标"""
    try:
        metrics = data_service.get_keyword_metrics(
            keywords=request.keywords,
            source=request.source,
            country=request.country
        )
        return Response(code=0, message="success", data={"metrics": metrics, "total": len(metrics), "source_used": request.source or "auto"})
    except Exception as e:
        logger.error(f"Failed to get keyword metrics: {e}")
        return Response(code=ErrorCode.INTERNAL_ERROR, message=f"Failed to get keyword metrics: {str(e)}", data={})


@router.post("/keywords/ranking", summary="获取关键词排名", description="从真实数据源获取域名在特定关键词上的排名")
async def get_keyword_ranking(
    request: KeywordRankingRequest,
    data_service: DataSourceIntegrationService = Depends(get_data_source_service)
) -> Response:
    """获取关键词排名"""
    try:
        rankings = data_service.get_keyword_ranking(
            domain=request.domain,
            keywords=request.keywords,
            source=request.source,
            country=request.country
        )
        return Response(code=0, message="success", data={"rankings": rankings, "total": len(rankings), "source_used": request.source or "auto"})
    except Exception as e:
        logger.error(f"Failed to get keyword ranking: {e}")
        return Response(code=ErrorCode.INTERNAL_ERROR, message=f"Failed to get keyword ranking: {str(e)}", data={})


# ==================== 竞品数据端点 ====================

@router.post("/competitors/list", summary="获取竞争对手列表", description="从真实数据源获取竞争对手列表")
async def get_competitor_list(
    request: CompetitorRequest,
    data_service: DataSourceIntegrationService = Depends(get_data_source_service)
) -> Response:
    """获取竞争对手列表"""
    try:
        competitors = data_service.get_competitor_list(
            domain=request.domain,
            source=request.source,
            country=request.country,
            limit=request.limit
        )
        return Response(code=0, message="success", data={"competitors": competitors, "total": len(competitors), "source_used": request.source or "auto"})
    except Exception as e:
        logger.error(f"Failed to get competitor list: {e}")
        return Response(code=ErrorCode.INTERNAL_ERROR, message=f"Failed to get competitor list: {str(e)}", data={})


@router.post("/competitors/traffic", summary="获取竞争对手流量", description="从真实数据源获取竞争对手流量数据")
async def get_competitor_traffic(
    request: CompetitorTrafficRequest,
    data_service: DataSourceIntegrationService = Depends(get_data_source_service)
) -> Response:
    """获取竞争对手流量数据"""
    try:
        traffic_data = data_service.get_competitor_traffic(
            domain=request.domain,
            start_date=request.start_date,
            end_date=request.end_date,
            source=request.source,
            country=request.country
        )
        return Response(code=0, message="success", data=traffic_data)
    except Exception as e:
        logger.error(f"Failed to get competitor traffic: {e}")
        return Response(code=ErrorCode.INTERNAL_ERROR, message=f"Failed to get competitor traffic: {str(e)}", data={})


@router.post("/competitors/top-pages", summary="获取竞争对手 Top 页面", description="从真实数据源获取竞争对手热门页面")
async def get_competitor_top_pages(
    request: CompetitorRequest,
    data_service: DataSourceIntegrationService = Depends(get_data_source_service)
) -> Response:
    """获取竞争对手 Top 页面"""
    try:
        pages = data_service.get_competitor_top_pages(
            domain=request.domain,
            source=request.source,
            country=request.country,
            limit=request.limit
        )
        return Response(code=0, message="success", data={"pages": pages, "total": len(pages), "source_used": request.source or "auto"})
    except Exception as e:
        logger.error(f"Failed to get competitor top pages: {e}")
        return Response(code=ErrorCode.INTERNAL_ERROR, message=f"Failed to get competitor top pages: {str(e)}", data={})


@router.post("/competitors/backlinks", summary="获取竞争对手反向链接", description="从真实数据源获取竞争对手反向链接")
async def get_competitor_backlinks(
    request: CompetitorRequest,
    data_service: DataSourceIntegrationService = Depends(get_data_source_service)
) -> Response:
    """获取竞争对手反向链接"""
    try:
        backlinks = data_service.get_competitor_backlinks(
            domain=request.domain,
            source=request.source,
            country=request.country,
            limit=request.limit
        )
        return Response(code=0, message="success", data={"backlinks": backlinks, "total": len(backlinks), "source_used": request.source or "auto"})
    except Exception as e:
        logger.error(f"Failed to get competitor backlinks: {e}")
        return Response(code=ErrorCode.INTERNAL_ERROR, message=f"Failed to get competitor backlinks: {str(e)}", data={})


# ==================== 综合竞品分析端点 ====================

@router.post("/competitors/analyze", summary="综合竞品分析", description="获取竞品的全面分析数据")
async def analyze_competitor(
    request: CompetitorRequest,
    data_service: DataSourceIntegrationService = Depends(get_data_source_service)
) -> Response:
    """综合竞品分析"""
    try:
        competitors = data_service.get_competitor_list(domain=request.domain, source=request.source, country=request.country, limit=10)
        top_pages = data_service.get_competitor_top_pages(domain=request.domain, source=request.source, country=request.country, limit=20)
        backlinks = data_service.get_competitor_backlinks(domain=request.domain, source=request.source, country=request.country, limit=50)
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        traffic_data = data_service.get_competitor_traffic(domain=request.domain, start_date=start_date, end_date=end_date, source=request.source, country=request.country)
        return Response(code=0, message="success", data={"domain": request.domain, "competitors": competitors, "top_pages": top_pages, "backlinks": backlinks[:20], "traffic_summary": traffic_data, "analysis_date": end_date.isoformat()})
    except Exception as e:
        logger.error(f"Failed to analyze competitor: {e}")
        return Response(code=ErrorCode.INTERNAL_ERROR, message=f"Failed to analyze competitor: {str(e)}", data={})
