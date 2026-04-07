"""
SEO API 路由
"""
from fastapi import APIRouter, Query
from typing import List
from schemas.seo import SEOAnalysisRequest, SEOAnalysisResult, SEOTipsResponse, SEOKeywordSuggestion
from schemas.common import Response
from core.response import success
from .service import seo_service
from core.exceptions import SEOContentEmptyException, SEOKeywordsEmptyException

router = APIRouter(prefix="/seo", tags=["SEO优化"])


@router.post("/analyze", response_model=Response[SEOAnalysisResult])
async def analyze_seo(request: SEOAnalysisRequest):
    """
    分析内容SEO质量
    - 关键词密度分析
    - 内容长度评估
    - 可读性评分
    - 优化建议和问题诊断
    - 标题和Meta描述检查
    """
    if len(request.content.strip()) == 0:
        raise SEOContentEmptyException("SEO分析内容不能为空")

    if not request.target_keywords or len(request.target_keywords) == 0:
        raise SEOKeywordsEmptyException("SEO分析关键词不能为空")

    result = seo_service.analyze_content(request)
    return success(data=result)


@router.get("/tips", response_model=Response[SEOTipsResponse])
async def get_seo_tips():
    """
    获取SEO优化建议列表
    - 内容优化建议
    - 结构优化建议
    - Meta标签优化建议
    - 技术SEO建议
    - 用户体验优化建议
    """
    result = seo_service.get_seo_tips()
    return success(data=result)


@router.get("/keyword-suggestions", response_model=Response[List[SEOKeywordSuggestion]])
async def get_keyword_suggestions(
    keywords: List[str] = Query(..., description="种子关键词列表", min_length=1)
):
    """
    获取关键词建议
    - 相关关键词推荐
    - 搜索量、竞争度、难度评估
    - 按相关度排序
    """
    if not keywords:
        raise SEOKeywordsEmptyException("种子关键词不能为空")

    result = seo_service.get_keyword_suggestions(keywords)
    return success(data=result)
