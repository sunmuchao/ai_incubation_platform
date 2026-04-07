"""
SEO 工具集 - 封装 SEO 分析能力为 DeerFlow 可调用工具
"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import sys
from pathlib import Path

# 添加 src 到路径以便导入
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from seo.service import seo_service
from schemas.seo import SEOAnalysisRequest


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any
    message: str = ""
    error: Optional[str] = None


class SeoTools:
    """
    SEO 工具集

    提供 SEO 分析、关键词建议、优化建议等能力，
    可作为 DeerFlow 2.0 的工具节点被调用。
    """

    def __init__(self):
        self._service = seo_service

    def analyze_seo(
        self,
        content: str,
        target_keywords: List[str],
        title: Optional[str] = None,
        meta_description: Optional[str] = None,
        url: Optional[str] = None
    ) -> ToolResult:
        """
        分析内容 SEO 质量

        Args:
            content: 要分析的内容文本
            target_keywords: 目标关键词列表
            title: 页面标题（可选）
            meta_description: Meta 描述（可选）
            url: 页面 URL（可选）

        Returns:
            ToolResult: 包含 SEO 分析结果

        Example:
            ```python
            tools = SeoTools()
            result = tools.analyze_seo(
                content="这是一篇关于 SEO 优化的文章...",
                target_keywords=["SEO", "优化", "流量"]
            )
            if result.success:
                print(f"SEO 评分：{result.data.overall_score}")
            ```
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

            request = SEOAnalysisRequest(
                content=content,
                target_keywords=target_keywords,
                title=title or "",
                meta_description=meta_description or "",
                url=url or ""
            )

            result = self._service.analyze_content(request)

            return ToolResult(
                success=True,
                data={
                    "overall_score": result.overall_score,
                    "keyword_density": result.keyword_density,
                    "content_length": result.content_length,
                    "readability_score": result.readability_score,
                    "issues": result.issues,  # 字符串列表
                    "suggestions": result.suggestions,
                    "strengths": result.strengths
                },
                message=f"SEO 分析完成，总体评分：{result.overall_score}"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )

    def get_keyword_suggestions(
        self,
        seed_keywords: List[str],
        limit: int = 20
    ) -> ToolResult:
        """
        获取关键词建议

        Args:
            seed_keywords: 种子关键词列表
            limit: 返回结果数量限制

        Returns:
            ToolResult: 包含关键词建议列表
        """
        try:
            if not seed_keywords:
                return ToolResult(
                    success=False,
                    data=None,
                    error="种子关键词不能为空"
                )

            suggestions = self._service.get_keyword_suggestions(seed_keywords)

            # 限制返回数量
            suggestions = suggestions[:limit]

            return ToolResult(
                success=True,
                data=[
                    {
                        "keyword": s.keyword,
                        "search_volume": s.search_volume,
                        "competition": s.competition,
                        "difficulty": s.difficulty,
                        "relevance": s.relevance
                    }
                    for s in suggestions
                ],
                message=f"获取到 {len(suggestions)} 个关键词建议"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )

    def get_seo_tips(self) -> ToolResult:
        """
        获取 SEO 优化建议列表

        Returns:
            ToolResult: 包含 SEO 优化建议
        """
        try:
            tips = self._service.get_seo_tips()

            return ToolResult(
                success=True,
                data={
                    "tips": tips.tips,
                    "categories": tips.categories
                },
                message="获取 SEO 优化建议成功"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )
