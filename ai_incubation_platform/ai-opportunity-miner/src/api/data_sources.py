"""
数据源 API
提供统一的数据源访问接口，支持企业数据、专利数据、社交媒体等

P5 增强:
- 集成 RealDataAdapter 支持多数据源配置和降级策略
- 添加数据源状态监控和配置 API
- 支持缓存管理
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Dict, Optional
from pydantic import BaseModel
from crawler.enterprise_crawler import enterprise_crawler
from crawler.patent_crawler import patent_crawler
from crawler.social_media_crawler import social_media_crawler

# 引入新的数据适配器 (P5 新增)
from data_sources.real_api_adapter import (
    data_adapter,
    DataSourceType,
    DataSourceStatus
)

router = APIRouter(prefix="/api/data", tags=["数据源"])


# === 请求/响应模型 ===

class KeywordQuery(BaseModel):
    """关键词查询"""
    keyword: str
    limit: int = 20


class IndustryQuery(BaseModel):
    """行业查询"""
    industry: str
    limit: int = 50


class DateRangeQuery(BaseModel):
    """日期范围查询"""
    days: int = 30
    limit: int = 20


class PlatformQuery(BaseModel):
    """平台查询"""
    platform: str = Query("weibo", description="平台类型：weibo, twitter")
    keyword: str
    limit: int = 20


class DataSourceInfo(BaseModel):
    """数据源信息"""
    name: str
    description: str
    type: str
    status: str
    use_mock: bool


# === 企业数据 API ===

@router.get("/enterprise/search", response_model=List[Dict])
async def search_enterprise(
    keyword: str = Query(..., description="搜索关键词"),
    limit: int = Query(20, description="返回数量限制", ge=1, le=100)
):
    """搜索企业信息"""
    try:
        companies = await enterprise_crawler.search_company(keyword, limit)
        return {
            "success": True,
            "data": companies,
            "total": len(companies),
            "source": "enterprise"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/enterprise/{company_id}", response_model=Dict)
async def get_enterprise_detail(company_id: str):
    """获取企业详情"""
    try:
        detail = await enterprise_crawler.get_company_detail(company_id)
        if detail:
            return {"success": True, "data": detail}
        raise HTTPException(status_code=404, detail="企业不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/enterprise/industry/{industry}", response_model=List[Dict])
async def get_enterprises_by_industry(
    industry: str,
    limit: int = Query(50, description="返回数量限制", ge=1, le=200)
):
    """按行业获取企业列表"""
    try:
        companies = await enterprise_crawler.get_companies_by_industry(industry, limit)
        return {
            "success": True,
            "data": companies,
            "total": len(companies),
            "source": "enterprise"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/enterprise/recent", response_model=List[Dict])
async def get_recent_enterprises(
    days: int = Query(30, description="天数", ge=1, le=365),
    limit: int = Query(20, description="返回数量限制", ge=1, le=100)
):
    """获取最近注册的企业"""
    try:
        companies = await enterprise_crawler.get_recent_registered_companies(days, limit)
        return {
            "success": True,
            "data": companies,
            "total": len(companies),
            "source": "enterprise"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === 专利数据 API ===

@router.get("/patent/search", response_model=List[Dict])
async def search_patent(
    keyword: str = Query(..., description="搜索关键词"),
    limit: int = Query(20, description="返回数量限制", ge=1, le=100)
):
    """搜索专利数据"""
    try:
        patents = await patent_crawler.search_patent(keyword, limit)
        return {
            "success": True,
            "data": patents,
            "total": len(patents),
            "source": "patent"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patent/{patent_id}", response_model=Dict)
async def get_patent_detail(patent_id: str):
    """获取专利详情"""
    try:
        detail = await patent_crawler.get_patent_detail(patent_id)
        if detail:
            return {"success": True, "data": detail}
        raise HTTPException(status_code=404, detail="专利不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patent/recent", response_model=List[Dict])
async def get_recent_patents(
    days: int = Query(30, description="天数", ge=1, le=365),
    keyword: Optional[str] = Query(None, description="关键词"),
    limit: int = Query(20, description="返回数量限制", ge=1, le=100)
):
    """获取最近公开的专利"""
    try:
        patents = await patent_crawler.get_recent_patents(days, keyword, limit)
        return {
            "success": True,
            "data": patents,
            "total": len(patents),
            "source": "patent"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patent/trend/{keyword}", response_model=Dict)
async def analyze_patent_trend(
    keyword: str,
    years: int = Query(5, description="分析年数", ge=1, le=20)
):
    """分析专利技术趋势"""
    try:
        trend = await patent_crawler.analyze_patent_trend(keyword, years)
        return {"success": True, "data": trend}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === 社交媒体 API ===

@router.get("/social/search", response_model=List[Dict])
async def search_social_posts(
    keyword: str = Query(..., description="搜索关键词"),
    platform: str = Query("weibo", description="平台类型：weibo, twitter"),
    limit: int = Query(20, description="返回数量限制", ge=1, le=100)
):
    """搜索社交媒体帖子"""
    try:
        posts = await social_media_crawler.search_posts(keyword, platform, limit)
        return {
            "success": True,
            "data": posts,
            "total": len(posts),
            "source": "social_media",
            "platform": platform
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/social/hot-topics", response_model=List[Dict])
async def get_hot_topics(
    platform: str = Query("weibo", description="平台类型：weibo, twitter")
):
    """获取热门话题"""
    try:
        topics = await social_media_crawler.get_hot_topics(platform)
        return {
            "success": True,
            "data": topics,
            "source": "social_media",
            "platform": platform
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/social/sentiment/{keyword}", response_model=Dict)
async def analyze_sentiment(
    keyword: str,
    days: int = Query(7, description="分析天数", ge=1, le=90)
):
    """分析社交媒体情感趋势"""
    try:
        sentiment = await social_media_crawler.analyze_sentiment(keyword, days)
        return {"success": True, "data": sentiment}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === 数据源状态 API ===

@router.get("/sources", response_model=List[Dict])
async def get_data_sources():
    """获取所有可用数据源信息"""
    sources = [
        {
            "name": "企业数据",
            "description": "企业信息、融资历史、专利商标等",
            "type": "enterprise",
            "status": "active",
            "use_mock": enterprise_crawler.use_mock
        },
        {
            "name": "专利数据",
            "description": "专利申请、授权、法律状态等",
            "type": "patent",
            "status": "active",
            "use_mock": patent_crawler.use_mock
        },
        {
            "name": "社交媒体",
            "description": "微博、Twitter 等社交媒体帖子",
            "type": "social_media",
            "status": "active",
            "use_mock": social_media_crawler.use_mock
        }
    ]
    return {"success": True, "data": sources}


# ========== P5 新增：数据源管理 API ==========

@router.get("/sources/status")
async def get_data_sources_status() -> Dict[str, str]:
    """获取所有数据源状态（支持真实 API 适配器）"""
    return data_adapter.get_all_status()


@router.get("/sources/{data_type}")
async def get_data_source_info(data_type: str) -> Dict:
    """获取单个数据源详细信息"""
    try:
        dtype = DataSourceType(data_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的数据源类型：{data_type}")

    status = data_adapter.get_status(dtype)
    config = data_adapter._configs.get(dtype)

    return {
        "name": dtype.value,
        "type": dtype.value,
        "status": status.value,
        "configured": bool(config and config.api_key),
        "api_url": config.api_url if config else "",
        "cache_ttl": config.cache_ttl if config else 3600,
        "timeout": config.timeout if config else 30
    }


class DataSourceConfigRequest(BaseModel):
    """数据源配置请求"""
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    timeout: Optional[int] = 30
    cache_ttl: Optional[int] = 3600


@router.post("/sources/{data_type}/configure")
async def configure_data_source(
    data_type: str,
    config: DataSourceConfigRequest
) -> Dict[str, str]:
    """配置数据源"""
    try:
        dtype = DataSourceType(data_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的数据源类型：{data_type}")

    data_adapter.configure(
        dtype,
        api_key=config.api_key,
        api_url=config.api_url or "",
        timeout=config.timeout,
        cache_ttl=config.cache_ttl
    )

    return {
        "status": "success",
        "message": f"数据源 {data_type} 配置成功",
        "new_status": data_adapter.get_status(dtype).value
    }


@router.post("/sources/cache/clear")
async def clear_cache(data_type: Optional[str] = None) -> Dict[str, str]:
    """清除缓存"""
    if data_type:
        try:
            dtype = DataSourceType(data_type)
            data_adapter.clear_cache(dtype)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的数据源类型：{data_type}")
    else:
        data_adapter.clear_cache()

    return {"status": "success", "message": "缓存已清除"}


@router.get("/sources/cache/stats")
async def get_cache_stats() -> Dict:
    """获取缓存统计信息"""
    cache_dir = data_adapter.cache_dir
    if not cache_dir.exists():
        return {"cache_size": 0, "cache_files": 0}

    cache_files = list(cache_dir.glob("*.json"))
    total_size = sum(f.stat().st_size for f in cache_files)

    return {
        "cache_dir": str(cache_dir),
        "cache_size": total_size,
        "cache_size_mb": round(total_size / 1024 / 1024, 2),
        "cache_files": len(cache_files)
    }


# ========== P5 新增：统一数据查询 API（支持降级） ==========

@router.get("/query/enterprise")
async def query_enterprise_api(
    keyword: str = Query(..., description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100),
    use_cache: bool = Query(True, description="是否使用缓存")
) -> Dict:
    """
    查询企业信息（支持真实 API 和降级策略）

    降级策略:
    1. 真实 API 可用 -> 使用真实数据
    2. API 不可用 -> 使用缓存数据
    3. 缓存过期 -> 使用模拟数据 + 提示
    """
    results = await data_adapter.query_enterprise(keyword, limit, use_cache)
    is_mock = any(r.get("_mock") for r in results) if results else False

    return {
        "data": results,
        "count": len(results),
        "is_mock": is_mock,
        "warning": "当前使用模拟数据，请配置真实 API 密钥以获取真实数据" if is_mock else None
    }


@router.get("/query/financing")
async def query_financing_api(
    company_name: Optional[str] = Query(None, description="公司名称"),
    industry: Optional[str] = Query(None, description="行业"),
    limit: int = Query(50, ge=1, le=200),
    use_cache: bool = Query(True, description="是否使用缓存")
) -> Dict:
    """查询融资事件（支持真实 API 和降级策略）"""
    results = await data_adapter.query_financing(
        company_name, industry, None, None, limit, use_cache
    )
    is_mock = any(r.get("_mock") for r in results) if results else False

    return {
        "data": results,
        "count": len(results),
        "is_mock": is_mock,
        "warning": "当前使用模拟数据" if is_mock else None
    }


@router.get("/query/patent")
async def query_patent_api(
    keyword: str = Query(..., description="搜索关键词"),
    patent_type: Optional[str] = Query(None, description="专利类型"),
    limit: int = Query(20, ge=1, le=100),
    use_cache: bool = Query(True, description="是否使用缓存")
) -> Dict:
    """查询专利信息（支持真实 API 和降级策略）"""
    results = await data_adapter.query_patent(keyword, patent_type, limit, use_cache)
    is_mock = any(r.get("_mock") for r in results) if results else False

    return {
        "data": results,
        "count": len(results),
        "is_mock": is_mock,
        "warning": "当前使用模拟数据" if is_mock else None
    }


@router.get("/query/news")
async def query_news_api(
    keyword: str = Query(..., description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100),
    use_cache: bool = Query(True, description="是否使用缓存")
) -> Dict:
    """查询新闻（支持真实 API 和降级策略）"""
    results = await data_adapter.query_news(keyword, None, None, limit, use_cache)
    is_mock = any(r.get("_mock") for r in results) if results else False

    return {
        "data": results,
        "count": len(results),
        "is_mock": is_mock,
        "warning": "当前使用模拟数据" if is_mock else None
    }
