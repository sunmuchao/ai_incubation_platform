"""
内容优化模块 schema 定义
"""
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ContentType(str, Enum):
    """内容类型枚举"""
    ARTICLE = "article"
    BLOG_POST = "blog_post"
    PRODUCT_DESCRIPTION = "product_description"
    SOCIAL_MEDIA = "social_media"
    NEWS = "news"
    AD_COPY = "ad_copy"


class ContentTone(str, Enum):
    """内容语气枚举"""
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    CASUAL = "casual"
    AUTHORITATIVE = "authoritative"
    PERSUASIVE = "persuasive"
    INFORMATIVE = "informative"


class ContentOptimizationRequest(BaseModel):
    """内容优化请求"""
    # 让路由层可以抛出模块化错误码；schema 层不强校验 min_length
    content: str = Field(description="原始内容")
    target_keywords: List[str] = Field(description="目标关键词列表")
    content_type: ContentType = Field(default=ContentType.ARTICLE, description="内容类型")
    target_audience: Optional[str] = Field(default=None, description="目标受众")
    tone: ContentTone = Field(default=ContentTone.INFORMATIVE, description="内容语气")
    max_length: Optional[int] = Field(default=None, description="最大内容长度")
    min_length: Optional[int] = Field(default=None, description="最小内容长度")


class ContentOptimizationResult(BaseModel):
    """内容优化结果"""
    original_score: float = Field(description="原始内容分数 0-100")
    optimized_score: float = Field(description="优化后内容分数 0-100")
    optimized_content: str = Field(description="优化后的内容")
    changes: List[Dict[str, str]] = Field(description="修改说明列表")
    suggestions: List[str] = Field(description="进一步优化建议")
    keyword_improvements: Dict[str, float] = Field(description="关键词密度改进")


class ContentGenerationRequest(BaseModel):
    """内容生成请求"""
    topic: str = Field(description="内容主题", min_length=1)
    target_keywords: List[str] = Field(description="目标关键词列表", min_length=1)
    content_type: ContentType = Field(default=ContentType.ARTICLE, description="内容类型")
    target_audience: Optional[str] = Field(default=None, description="目标受众")
    tone: ContentTone = Field(default=ContentTone.INFORMATIVE, description="内容语气")
    # 这里不在 schema 层做 ge/le 强校验，让路由侧返回模块化错误码
    length: int = Field(default=1000, description="期望内容长度")
    outline: Optional[List[str]] = Field(default=None, description="内容大纲")


class ContentGenerationResult(BaseModel):
    """内容生成结果"""
    content: str = Field(description="生成的内容")
    title: str = Field(description="生成的标题")
    meta_description: str = Field(description="生成的Meta描述")
    outline: List[str] = Field(description="内容大纲")
    seo_score: float = Field(description="SEO分数 0-100")
    keyword_density: Dict[str, float] = Field(description="关键词密度")
    suggestions: List[str] = Field(description="优化建议")
