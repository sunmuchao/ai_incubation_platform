"""
Markdown 报告模板
"""
from typing import Dict, Any
from .base import BaseReportTemplate


class MarkdownReportTemplate(BaseReportTemplate):
    """Markdown 报告模板"""

    def render(self, format: str = "json", **kwargs) -> str:
        """
        渲染 Markdown 格式报告

        Args:
            format: 输出格式
            **kwargs: 其他渲染参数

        Returns:
            渲染后的 Markdown 报告内容
        """
        return self.render_markdown(**kwargs)
