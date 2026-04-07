"""
可视化仪表板 API 端点 - P0 可视化仪表板

提供仪表板所需的数据接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
from datetime import date, timedelta, datetime
from pydantic import BaseModel, Field

from db import get_db
from core.response import Response, ErrorCode
from core.config import settings
import logging
import random

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["可视化仪表板"])


# ==================== 请求/响应模型 ====================

class TrafficSummaryRequest(BaseModel):
    """流量汇总请求"""
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    domain: Optional[str] = Field(default=None, description="域名筛选")


class TrafficTrendData(BaseModel):
    """流量趋势数据"""
    date: str
    visitors: int
    page_views: int
    sessions: int


class SourceDistribution(BaseModel):
    """来源分布"""
    source: str
    visitors: int
    percentage: float


class DeviceDistribution(BaseModel):
    """设备分布"""
    device_type: str
    visitors: int
    percentage: float


class TopPageData(BaseModel):
    """Top 页面数据"""
    url: str
    title: str
    page_views: int
    unique_visitors: int
    avg_time_on_page: float
    bounce_rate: float


class KeywordRankingData(BaseModel):
    """关键词排名数据"""
    keyword: str
    position: int
    previous_position: Optional[int]
    search_volume: int
    difficulty: int
    url: str


class CompetitorData(BaseModel):
    """竞品数据"""
    domain: str
    similarity: float
    common_keywords: int
    estimated_traffic: int


# ==================== 流量分析端点 ====================

@router.post("/traffic/summary", summary="流量汇总数据", description="获取指定时间范围内的流量汇总数据")
async def get_traffic_summary(request: TrafficSummaryRequest) -> Response:
    """获取流量汇总数据"""
    try:
        # 模拟数据 - 实际应连接数据库
        total_visitors = random.randint(30000, 60000)
        total_page_views = total_visitors * random.randint(2, 4)
        avg_session_duration = random.randint(120, 300)
        bounce_rate = round(random.uniform(0.25, 0.5), 4)
        conversion_rate = round(random.uniform(0.02, 0.05), 4)

        data = {
            "period": {
                "start_date": request.start_date.isoformat(),
                "end_date": request.end_date.isoformat()
            },
            "total_visitors": total_visitors,
            "total_page_views": total_page_views,
            "avg_session_duration": avg_session_duration,
            "bounce_rate": bounce_rate,
            "conversion_rate": conversion_rate,
            "comparison": {
                "visitors_change": round(random.uniform(-0.15, 0.25), 4),
                "page_views_change": round(random.uniform(-0.1, 0.2), 4),
                "session_change": round(random.uniform(-0.05, 0.1), 4)
            }
        }

        return Response(code=0, message="success", data=data)

    except Exception as e:
        logger.error(f"Failed to get traffic summary: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get traffic summary: {str(e)}",
            data={}
        )


@router.get("/traffic/trend", summary="流量趋势数据", description="获取流量趋势数据（按天）")
async def get_traffic_trend(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
) -> Response:
    """获取流量趋势数据"""
    try:
        # 生成模拟趋势数据
        trend_data = []
        current_date = start_date
        base_visitors = random.randint(1000, 2000)

        while current_date <= end_date:
            # 周末流量较低
            is_weekend = current_date.weekday() >= 5
            multiplier = random.uniform(0.6, 0.8) if is_weekend else random.uniform(0.9, 1.2)

            visitors = int(base_visitors * multiplier)
            page_views = int(visitors * random.uniform(2.5, 4))
            sessions = int(visitors * random.uniform(1.1, 1.5))

            trend_data.append({
                "date": current_date.isoformat(),
                "visitors": visitors,
                "page_views": page_views,
                "sessions": sessions
            })

            current_date += timedelta(days=1)

        return Response(code=0, message="success", data={"trend": trend_data})

    except Exception as e:
        logger.error(f"Failed to get traffic trend: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get traffic trend: {str(e)}",
            data={}
        )


@router.get("/traffic/sources", summary="流量来源分布", description="获取流量来源分布数据")
async def get_traffic_sources(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
) -> Response:
    """获取流量来源分布"""
    try:
        sources = [
            {"source": "organic_search", "label": "自然搜索", "visitors": random.randint(15000, 25000)},
            {"source": "direct", "label": "直接访问", "visitors": random.randint(8000, 15000)},
            {"source": "social", "label": "社交媒体", "visitors": random.randint(3000, 8000)},
            {"source": "referral", "label": "引荐", "visitors": random.randint(2000, 6000)},
            {"source": "paid", "label": "付费广告", "visitors": random.randint(1000, 4000)},
        ]

        total = sum(s["visitors"] for s in sources)
        for s in sources:
            s["percentage"] = round(s["visitors"] / total, 4) if total > 0 else 0

        return Response(code=0, message="success", data={"sources": sources})

    except Exception as e:
        logger.error(f"Failed to get traffic sources: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get traffic sources: {str(e)}",
            data={}
        )


@router.get("/traffic/devices", summary="设备分布", description="获取设备分布数据")
async def get_traffic_devices(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
) -> Response:
    """获取设备分布"""
    try:
        devices = [
            {"device_type": "desktop", "label": "桌面端", "visitors": random.randint(15000, 25000)},
            {"device_type": "mobile", "label": "移动端", "visitors": random.randint(15000, 25000)},
            {"device_type": "tablet", "label": "平板", "visitors": random.randint(2000, 5000)},
        ]

        total = sum(d["visitors"] for d in devices)
        for d in devices:
            d["percentage"] = round(d["visitors"] / total, 4) if total > 0 else 0

        return Response(code=0, message="success", data={"devices": devices})

    except Exception as e:
        logger.error(f"Failed to get traffic devices: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get traffic devices: {str(e)}",
            data={}
        )


@router.get("/traffic/top-pages", summary="Top 页面", description="获取热门页面列表")
async def get_top_pages(
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    limit: int = Query(default=10, ge=1, le=50, description="返回数量限制")
) -> Response:
    """获取热门页面"""
    try:
        pages = [
            {"url": "/home", "title": "首页", "page_views": random.randint(8000, 15000)},
            {"url": "/products/seo-tool", "title": "SEO 工具", "page_views": random.randint(5000, 10000)},
            {"url": "/products/keyword-research", "title": "关键词研究", "page_views": random.randint(4000, 8000)},
            {"url": "/blog", "title": "博客", "page_views": random.randint(3000, 6000)},
            {"url": "/about", "title": "关于我们", "page_views": random.randint(2000, 4000)},
            {"url": "/pricing", "title": "价格", "page_views": random.randint(1500, 3500)},
            {"url": "/contact", "title": "联系我们", "page_views": random.randint(1000, 2500)},
            {"url": "/docs", "title": "文档", "page_views": random.randint(800, 2000)},
        ]

        # 计算额外指标
        for page in pages:
            page["unique_visitors"] = int(page["page_views"] * random.uniform(0.6, 0.8))
            page["avg_time_on_page"] = round(random.uniform(60, 300), 1)
            page["bounce_rate"] = round(random.uniform(0.2, 0.5), 4)

        pages = sorted(pages, key=lambda x: x["page_views"], reverse=True)[:limit]

        return Response(code=0, message="success", data={"pages": pages})

    except Exception as e:
        logger.error(f"Failed to get top pages: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get top pages: {str(e)}",
            data={}
        )


# ==================== SEO 指标端点 ====================

@router.get("/seo/summary", summary="SEO 汇总数据", description="获取 SEO 汇总指标")
async def get_seo_summary() -> Response:
    """获取 SEO 汇总数据"""
    try:
        data = {
            "avg_position": round(random.uniform(10, 20), 1),
            "seo_score": random.randint(75, 95),
            "indexed_pages": random.randint(1000, 2000),
            "backlinks": random.randint(2000, 5000),
            "domain_authority": random.randint(40, 70),
            "position_change": random.randint(-3, 5),
            "score_change": random.randint(-2, 5)
        }
        return Response(code=0, message="success", data=data)

    except Exception as e:
        logger.error(f"Failed to get SEO summary: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get SEO summary: {str(e)}",
            data={}
        )


@router.get("/seo/ranking-distribution", summary="关键词排名分布", description="获取关键词排名分布数据")
async def get_ranking_distribution() -> Response:
    """获取关键词排名分布"""
    try:
        distribution = [
            {"range": "1-3", "count": random.randint(20, 50), "label": "前 3 名"},
            {"range": "4-10", "count": random.randint(60, 100), "label": "前 10 名"},
            {"range": "11-20", "count": random.randint(100, 200), "label": "前 20 名"},
            {"range": "21-50", "count": random.randint(150, 250), "label": "前 50 名"},
            {"range": "51-100", "count": random.randint(100, 200), "label": "前 100 名"},
        ]
        return Response(code=0, message="success", data={"distribution": distribution})

    except Exception as e:
        logger.error(f"Failed to get ranking distribution: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get ranking distribution: {str(e)}",
            data={}
        )


@router.get("/seo/top-keywords", summary="Top 关键词", description="获取表现最好的关键词列表")
async def get_top_keywords(
    limit: int = Query(default=10, ge=1, le=50, description="返回数量限制")
) -> Response:
    """获取 Top 关键词"""
    try:
        keywords_pool = [
            "SEO tools", "keyword research", "analytics platform",
            "digital marketing", "traffic analysis", "competitor analysis",
            "backlink checker", "rank tracker", "content optimization",
            "search console", "google analytics", "website audit"
        ]

        keywords = []
        for kw in random.sample(keywords_pool, min(limit, len(keywords_pool))):
            keywords.append({
                "keyword": kw,
                "position": random.randint(1, 30),
                "previous_position": random.randint(1, 35),
                "search_volume": random.randint(1000, 20000),
                "difficulty": random.randint(20, 80),
                "url": f"/products/{kw.lower().replace(' ', '-')}"
            })

        keywords = sorted(keywords, key=lambda x: x["search_volume"], reverse=True)

        return Response(code=0, message="success", data={"keywords": keywords})

    except Exception as e:
        logger.error(f"Failed to get top keywords: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get top keywords: {str(e)}",
            data={}
        )


# ==================== 竞品分析端点 ====================

@router.get("/competitors/list", summary="竞争对手列表", description="获取竞争对手列表")
async def get_competitors(
    limit: int = Query(default=10, ge=1, le=50, description="返回数量限制")
) -> Response:
    """获取竞争对手列表"""
    try:
        competitors = [
            {"domain": "semrush.com", "similarity": 0.85, "common_keywords": 1250, "estimated_traffic": 500000},
            {"domain": "ahrefs.com", "similarity": 0.78, "common_keywords": 980, "estimated_traffic": 400000},
            {"domain": "moz.com", "similarity": 0.72, "common_keywords": 750, "estimated_traffic": 250000},
            {"domain": "spyfu.com", "similarity": 0.65, "common_keywords": 520, "estimated_traffic": 150000},
            {"domain": "serpstat.com", "similarity": 0.58, "common_keywords": 380, "estimated_traffic": 100000},
        ]

        return Response(code=0, message="success", data={"competitors": competitors[:limit]})

    except Exception as e:
        logger.error(f"Failed to get competitors: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get competitors: {str(e)}",
            data={}
        )


@router.get("/competitors/compare", summary="竞品对比", description="获取竞品对比数据")
async def get_competitor_compare(
    domains: str = Query(..., description="要对比的域名列表，逗号分隔"),
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
) -> Response:
    """获取竞品对比数据"""
    try:
        domain_list = [d.strip() for d in domains.split(",")]

        comparison = []
        for domain in domain_list:
            comparison.append({
                "domain": domain,
                "total_visitors": random.randint(100000, 600000),
                "avg_session_duration": random.randint(120, 300),
                "bounce_rate": round(random.uniform(0.25, 0.5), 4),
                "domain_authority": random.randint(40, 80)
            })

        return Response(code=0, message="success", data={"comparison": comparison})

    except Exception as e:
        logger.error(f"Failed to get competitor compare: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get competitor compare: {str(e)}",
            data={}
        )


# ==================== 仪表板配置端点 ====================

@router.get("/config", summary="仪表板配置", description="获取仪表板配置信息")
async def get_dashboard_config() -> Response:
    """获取仪表板配置"""
    try:
        config = {
            "available_metrics": [
                "visitors", "page_views", "sessions", "bounce_rate",
                "conversion_rate", "avg_session_duration"
            ],
            "available_charts": [
                "traffic_trend", "traffic_sources", "device_distribution",
                "top_pages", "ranking_distribution", "top_keywords"
            ],
            "default_date_range": 30,
            "refresh_interval": 300,  # 5 分钟
        }
        return Response(code=0, message="success", data={"config": config})

    except Exception as e:
        logger.error(f"Failed to get dashboard config: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get dashboard config: {str(e)}",
            data={}
        )
