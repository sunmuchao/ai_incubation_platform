"""
A/B测试报告工厂
根据需求创建不同格式的测试报告
"""
from typing import Dict, Type, Any, Optional
from .base import BaseReportTemplate
from .json_template import JSONReportTemplate
from .markdown_template import MarkdownReportTemplate
from .csv_template import CSVReportTemplate
from .html_template import HTMLReportTemplate
from schemas.ab_test import ABTestResponse, ABTestResultResponse


class ReportFactory:
    """报告工厂类"""

    _templates: Dict[str, Type[BaseReportTemplate]] = {
        "json": JSONReportTemplate,
        "markdown": MarkdownReportTemplate,
        "csv": CSVReportTemplate,
        "html": HTMLReportTemplate
    }

    @classmethod
    def register_template(cls, format: str, template_class: Type[BaseReportTemplate]) -> None:
        """注册新的报告模板"""
        cls._templates[format.lower()] = template_class

    @classmethod
    def create_report(
        cls,
        test: ABTestResponse,
        result: ABTestResultResponse,
        format: str = "json",
        **kwargs
    ) -> Any:
        """
        创建A/B测试报告

        Args:
            test: A/B测试对象
            result: 测试结果对象
            format: 报告格式：json, markdown, html, csv
            **kwargs: 传递给模板的渲染参数

        Returns:
            渲染后的报告内容
        """
        format_lower = format.lower()
        if format_lower not in cls._templates:
            raise ValueError(
                f"Unsupported report format: {format}. "
                f"Available formats: {list(cls._templates.keys())}"
            )

        template_class = cls._templates[format_lower]
        template = template_class(test, result)
        return template.render(format=format, **kwargs)

    @classmethod
    def get_supported_formats(cls) -> list[str]:
        """获取支持的报告格式"""
        return list(cls._templates.keys())


# 全局工厂实例
report_factory = ReportFactory()
