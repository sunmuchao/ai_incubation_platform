"""
SEO 模块 schema 定义
"""
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class SEOAnalysisRequest(BaseModel):
    """SEO 分析请求"""
    # 这里不在 schema 层做强校验（让路由侧可以抛出模块化错误码）
    content: str = Field(description="待分析的内容")
    target_keywords: List[str] = Field(description="目标关键词列表")
    url: Optional[str] = Field(default=None, description="页面URL（可选）")
    title: Optional[str] = Field(default=None, description="页面标题（可选）")
    meta_description: Optional[str] = Field(default=None, description="Meta描述（可选）")


class SEOAnalysisResult(BaseModel):
    """SEO 分析结果"""
    overall_score: float = Field(description="整体SEO分数 0-100")
    keyword_density: Dict[str, float] = Field(description="关键词密度（百分比）")
    content_length: int = Field(description="内容长度（字数）")
    readability_score: float = Field(description="可读性分数 0-100")
    suggestions: List[str] = Field(description="优化建议列表")
    # 实现层目前返回的是字符串问题列表（不是 {title, detail} 结构）
    issues: List[str] = Field(description="发现的问题列表")
    strengths: List[str] = Field(description="内容优点列表")


class SEOKeywordSuggestion(BaseModel):
    """关键词建议"""
    keyword: str = Field(description="关键词")
    search_volume: int = Field(description="搜索量")
    competition: float = Field(description="竞争度 0-1")
    difficulty: float = Field(description="排名难度 0-100")
    relevance: float = Field(description="与内容相关度 0-1")


class SEOTipsResponse(BaseModel):
    """SEO 建议列表响应"""
    tips: List[str] = Field(description="SEO优化建议列表")
    categories: Dict[str, List[str]] = Field(description="分类的SEO建议")
