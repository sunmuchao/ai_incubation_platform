"""
内容优化工具集 - 封装内容优化和生成能力为 DeerFlow 可调用工具
"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import sys
from pathlib import Path

# 添加 src 到路径以便导入
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from content.service import content_service
from schemas.content import (
    ContentOptimizationRequest,
    ContentGenerationRequest,
    ContentType,
    ContentTone
)


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any
    message: str = ""
    error: Optional[str] = None


class ContentTools:
    """
    内容优化工具集

    提供内容优化、内容生成等能力，
    可作为 DeerFlow 2.0 的工具节点被调用。
    """

    def __init__(self):
        self._service = content_service

    def optimize_content(
        self,
        content: str,
        target_keywords: List[str],
        content_type: str = "article",
        tone: str = "informative",
        target_audience: Optional[str] = None,
        max_length: Optional[int] = None,
        min_length: Optional[int] = None
    ) -> ToolResult:
        """
        优化内容 SEO 和可读性

        Args:
            content: 原始内容文本
            target_keywords: 目标关键词列表
            content_type: 内容类型 (article, blog_post, product_description, social_media, news, ad_copy)
            tone: 内容语气 (professional, friendly, casual, authoritative, persuasive, informative)
            target_audience: 目标受众描述（可选）
            max_length: 最大内容长度（可选）
            min_length: 最小内容长度（可选）

        Returns:
            ToolResult: 包含优化后的内容和改进说明
        """
        try:
            if not content or not content.strip():
                return ToolResult(
                    success=False,
                    data=None,
                    error="内容为空"
                )

            if not target_keywords:
                return ToolResult(
                    success=False,
                    data=None,
                    error="目标关键词不能为空"
                )

            # 转换枚举
            try:
                ct = ContentType(content_type)
            except ValueError:
                ct = ContentType.ARTICLE

            try:
                tone_enum = ContentTone(tone)
            except ValueError:
                tone_enum = ContentTone.INFORMATIVE

            request = ContentOptimizationRequest(
                content=content,
                target_keywords=target_keywords,
                content_type=ct,
                target_audience=target_audience,
                tone=tone_enum,
                max_length=max_length,
                min_length=min_length
            )

            result = self._service.optimize_content(request)

            return ToolResult(
                success=True,
                data={
                    "original_score": result.original_score,
                    "optimized_score": result.optimized_score,
                    "optimized_content": result.optimized_content,
                    "changes": result.changes,
                    "suggestions": result.suggestions,
                    "keyword_improvements": result.keyword_improvements
                },
                message=f"内容优化完成，分数从 {result.original_score} 提升到 {result.optimized_score}"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )

    def generate_content(
        self,
        topic: str,
        target_keywords: List[str],
        content_type: str = "article",
        tone: str = "informative",
        target_audience: Optional[str] = None,
        length: int = 1000,
        outline: Optional[List[str]] = None
    ) -> ToolResult:
        """
        AI 生成 SEO 友好的内容

        Args:
            topic: 内容主题
            target_keywords: 目标关键词列表
            content_type: 内容类型
            tone: 内容语气
            target_audience: 目标受众描述（可选）
            length: 期望内容长度
            outline: 内容大纲列表（可选）

        Returns:
            ToolResult: 包含生成的内容和元数据
        """
        try:
            if not topic or not topic.strip():
                return ToolResult(
                    success=False,
                    data=None,
                    error="主题不能为空"
                )

            if not target_keywords:
                return ToolResult(
                    success=False,
                    data=None,
                    error="目标关键词不能为空"
                )

            # 转换枚举
            try:
                ct = ContentType(content_type)
            except ValueError:
                ct = ContentType.ARTICLE

            try:
                tone_enum = ContentTone(tone)
            except ValueError:
                tone_enum = ContentTone.INFORMATIVE

            request = ContentGenerationRequest(
                topic=topic,
                target_keywords=target_keywords,
                content_type=ct,
                target_audience=target_audience,
                tone=tone_enum,
                length=length,
                outline=outline
            )

            result = self._service.generate_content(request)

            return ToolResult(
                success=True,
                data={
                    "content": result.content,
                    "title": result.title,
                    "meta_description": result.meta_description,
                    "outline": result.outline,
                    "seo_score": result.seo_score,
                    "keyword_density": result.keyword_density,
                    "suggestions": result.suggestions
                },
                message=f"内容生成完成，SEO 评分：{result.seo_score}"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )
