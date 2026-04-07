"""
报告导出工具
支持Markdown和PDF格式
"""
import os
from typing import List, Dict, Optional
from datetime import datetime
import markdown
from models.opportunity import BusinessOpportunity, MarketTrend
from config.settings import settings

try:
    # Lazy optional dependency for PDF export.
    from weasyprint import HTML  # type: ignore
except Exception:  # pragma: no cover
    HTML = None

class ReportExporter:
    """报告导出器"""

    def __init__(self):
        self.export_dir = settings.export_dir
        os.makedirs(self.export_dir, exist_ok=True)

    def export_opportunity_markdown(self, opportunity: BusinessOpportunity) -> str:
        """导出单条商机为Markdown格式"""
        risk_labels_md = ", ".join([label.value for label in opportunity.risk_labels])
        steps_md = "  \n".join([f"- {step}" for step in opportunity.validation_steps])
        entities_md = "  \n".join(
            [f'- {entity["name"]} ({entity["type"]}): {entity["relation"]}' for entity in opportunity.related_entities]
        )
        tags_md = ", ".join(opportunity.tags)

        md_content = f"""# 商机分析报告：{opportunity.title}

## 基本信息
- **商机ID**: {opportunity.id}
- **商机类型**: {opportunity.type.value}
- **置信度**: {opportunity.confidence_score:.1%}
- **潜在价值**: {opportunity.potential_value:,.2f} {opportunity.potential_value_currency}
- **创建时间**: {opportunity.created_at.strftime('%Y-%m-%d %H:%M:%S')}
- **更新时间**: {opportunity.updated_at.strftime('%Y-%m-%d %H:%M:%S')}
- **当前状态**: {opportunity.status.value}

## 商机描述
{opportunity.description}

## 来源信息
- **来源类型**: {opportunity.source_type.value}
- **来源名称**: {opportunity.source_name}
- **来源链接**: [{opportunity.source_url}]({opportunity.source_url})
- **发布时间**: {opportunity.source_publish_date.strftime('%Y-%m-%d') if opportunity.source_publish_date else '未知'}

## 风险评估
- **风险评分**: {opportunity.risk_score:.1%}
- **风险标签**: {risk_labels_md}
- **风险描述**: {opportunity.risk_description}

## 验证步骤
{steps_md}

- **验证状态**: {opportunity.validation_status}
- **验证备注**: {opportunity.validation_notes if opportunity.validation_notes else '无'}

## 关联实体
{entities_md}

## 标签
{tags_md}
"""
        return md_content

    def export_opportunity_pdf(self, opportunity: BusinessOpportunity, output_path: Optional[str] = None) -> str:
        """导出单条商机为PDF格式"""
        if HTML is None:
            raise RuntimeError("PDF导出依赖 weasyprint，但当前环境未安装或初始化失败。")

        md_content = self.export_opportunity_markdown(opportunity)
        html_content = markdown.markdown(md_content)

        # 添加CSS样式
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>商机报告：{opportunity.title}</title>
            <style>
                body {{ font-family: "Microsoft YaHei", Arial, sans-serif; line-height: 1.6; padding: 20px; }}
                h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                h2 {{ color: #34495e; margin-top: 30px; }}
                .info-box {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                .risk-high {{ color: #e74c3c; font-weight: bold; }}
                .risk-medium {{ color: #f39c12; font-weight: bold; }}
                .risk-low {{ color: #27ae60; font-weight: bold; }}
                ul {{ margin: 10px 0; padding-left: 20px; }}
                li {{ margin: 5px 0; }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(self.export_dir, f"opportunity_{opportunity.id}_{timestamp}.pdf")

        HTML(string=html).write_pdf(output_path)
        return output_path

    def export_batch_opportunities_markdown(self, opportunities: List[BusinessOpportunity], title: str = "商机汇总报告") -> str:
        """导出批量商机为Markdown格式"""
        md_content = f"""# {title}

导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 商机概览
共 {len(opportunities)} 条商机记录

| 商机ID | 标题 | 类型 | 置信度 | 潜在价值 | 风险评分 |
|--------|------|------|--------|----------|----------|
"""
        for opp in opportunities:
            md_content += f"| {opp.id[:8]}... | {opp.title[:20]}... | {opp.type.value} | {opp.confidence_score:.1%} | {opp.potential_value:,.0f} | {opp.risk_score:.1%} |\n"

        md_content += "\n## 详细商机信息\n"
        for i, opp in enumerate(opportunities, 1):
            md_content += f"\n### {i}. {opp.title}\n"
            md_content += f"- **类型**: {opp.type.value}\n"
            md_content += f"- **置信度**: {opp.confidence_score:.1%}\n"
            md_content += f"- **潜在价值**: {opp.potential_value:,.2f} {opp.potential_value_currency}\n"
            md_content += f"- **描述**: {opp.description}\n"
            md_content += f"- **查看详情**: [商机链接](/api/opportunities/{opp.id})\n"

        return md_content

    def export_trend_report_markdown(self, trends: List[MarketTrend], title: str = "市场趋势分析报告") -> str:
        """导出市场趋势报告为Markdown格式"""
        md_content = f"""# {title}

导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 趋势概览
共 {len(trends)} 个市场趋势

| 关键词 | 趋势分数 | 增长率 | 相关关键词 |
|--------|----------|--------|------------|
"""
        for trend in trends:
            md_content += f"| {trend.keyword} | {trend.trend_score:.1%} | {trend.growth_rate:.1%} | {', '.join(trend.related_keywords)} |\n"

        md_content += "\n## 趋势详情\n"
        for i, trend in enumerate(trends, 1):
            md_content += f"\n### {i}. {trend.keyword}\n"
            md_content += f"- **趋势分数**: {trend.trend_score:.1%}\n"
            md_content += f"- **增长率**: {trend.growth_rate:.1%}\n"
            md_content += f"- **相关关键词**: {', '.join(trend.related_keywords)}\n"
            md_content += "- **数据点**: \n"
            for dp in trend.data_points:
                md_content += f"  - {dp['month']}: {dp['value']}\n"

        return md_content

    def save_markdown(self, content: str, filename: str) -> str:
        """保存Markdown内容到文件"""
        if not filename.endswith('.md'):
            filename += '.md'
        file_path = os.path.join(self.export_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path

report_exporter = ReportExporter()
