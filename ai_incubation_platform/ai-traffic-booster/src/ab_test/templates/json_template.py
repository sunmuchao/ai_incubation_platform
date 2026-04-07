"""
JSON 报告模板
"""
from typing import Dict, Any
from .base import BaseReportTemplate


class JSONReportTemplate(BaseReportTemplate):
    """JSON 报告模板"""

    def render(self, format: str = "json", **kwargs) -> Dict[str, Any]:
        """
        渲染 JSON 格式报告

        Args:
            format: 输出格式（固定为 json）
            **kwargs: 其他渲染参数

        Returns:
            渲染后的 JSON 报告内容
        """
        return self.render_json()
