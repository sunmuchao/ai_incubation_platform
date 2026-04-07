"""
HTML格式的A/B测试结果报告模板
"""
from typing import Any
from .base import BaseReportTemplate


class HTMLReportTemplate(BaseReportTemplate):
    """HTML报告模板"""

    def render(self, format: str = "html", **kwargs) -> Any:
        """渲染HTML报告"""
        if format.lower() == "html":
            return self.render_html(**kwargs)
        elif format.lower() == "json":
            return self.render_json()
        elif format.lower() == "markdown":
            return self.render_markdown()
        else:
            raise ValueError(f"Unsupported format: {format}")

    def render_html(self, include_charts: bool = True, full_page: bool = True) -> str:
        """
        渲染为HTML格式

        Args:
            include_charts: 是否包含图表（使用Chart.js）
            full_page: 是否生成完整的HTML页面，否则只生成内容部分

        Returns:
            HTML格式字符串
        """
        basic = self.get_basic_info()
        stats = self.get_statistical_summary()
        conclusion = self.get_conclusion_recommendations()

        # 状态样式
        status_styles = {
            "draft": "background-color: #f3f4f6; color: #1f2937;",
            "running": "background-color: #dbeafe; color: #1e40af;",
            "completed": "background-color: #d1fae5; color: #065f46;",
            "paused": "background-color: #fef3c7; color: #92400e;",
            "cancelled": "background-color: #fee2e2; color: #991b1b;"
        }
        status_style = status_styles.get(basic['status'], "background-color: #f3f4f6; color: #1f2937;")

        # 构建内容
        content = []

        # 标题栏
        content.append(f"""
        <div style="max-width: 1200px; margin: 0 auto; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; border-radius: 8px; margin-bottom: 2rem;">
                <h1 style="margin: 0 0 1rem 0; font-size: 2rem;">A/B测试报告</h1>
                <h2 style="margin: 0; font-size: 1.5rem; opacity: 0.9;">{basic['test_name']}</h2>
                <div style="margin-top: 1rem; display: flex; gap: 1rem; flex-wrap: wrap;">
                    <span style="padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.875rem; font-weight: 500; {status_style}">
                        {basic['status']}
                    </span>
                    <span style="font-size: 0.875rem; opacity: 0.9;">ID: {basic['test_id']}</span>
                    <span style="font-size: 0.875rem; opacity: 0.9;">置信水平: {basic['confidence_level'] * 100:.0f}%</span>
                </div>
            </div>
        """)

        # 基本信息卡片
        content.append("""
            <div style="background: white; border-radius: 8px; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1); padding: 1.5rem; margin-bottom: 2rem;">
                <h3 style="margin-top: 0; color: #1f2937; font-size: 1.25rem;">📋 基本信息</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin-top: 1rem;">
        """)

        info_items = [
            ("测试页面", f"<a href=\"{basic['page_url']}\" target=\"_blank\" style=\"color: #667eea; text-decoration: none;\">{basic['page_url']}</a>"),
            ("创建人", basic['created_by']),
            ("创建时间", basic['created_at']),
            ("开始时间", basic['start_time'] or '未开始'),
            ("结束时间", basic['end_time'] or '未结束'),
            ("最小样本量", str(basic['minimum_sample_size']))
        ]

        for label, value in info_items:
            content.append(f"""
                    <div>
                        <div style="font-size: 0.875rem; color: #6b7280; margin-bottom: 0.25rem;">{label}</div>
                        <div style="font-weight: 500; color: #1f2937;">{value}</div>
                    </div>
            """)

        content.append("""
                </div>
            </div>
        """)

        # 统计摘要卡片
        content.append(f"""
            <div style="background: white; border-radius: 8px; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1); padding: 1.5rem; margin-bottom: 2rem;">
                <h3 style="margin-top: 0; color: #1f2937; font-size: 1.25rem;">📊 统计结果</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1rem 0;">
                    <div style="background: #f9fafb; padding: 1rem; border-radius: 6px;">
                        <div style="font-size: 0.875rem; color: #6b7280; margin-bottom: 0.25rem;">当前样本量</div>
                        <div style="font-size: 1.5rem; font-weight: 600; color: #1f2937;">{stats['current_sample_size']:,}</div>
                    </div>
                    <div style="background: #f9fafb; padding: 1rem; border-radius: 6px;">
                        <div style="font-size: 0.875rem; color: #6b7280; margin-bottom: 0.25rem;">剩余需要样本量</div>
                        <div style="font-size: 1.5rem; font-weight: 600; color: #1f2937;">{stats['remaining_sample_size']:,}</div>
                    </div>
                    <div style="background: {'#d1fae5' if stats['has_winner'] else '#fef3c7'}; padding: 1rem; border-radius: 6px;">
                        <div style="font-size: 0.875rem; color: #6b7280; margin-bottom: 0.25rem;">是否有获胜者</div>
                        <div style="font-size: 1.5rem; font-weight: 600; color: {'#065f46' if stats['has_winner'] else '#92400e'};">{'✅ 是' if stats['has_winner'] else '❌ 否'}</div>
                    </div>
                    <div style="background: {'#d1fae5' if stats['can_terminate'] else '#fee2e2'}; padding: 1rem; border-radius: 6px;">
                        <div style="font-size: 0.875rem; color: #6b7280; margin-bottom: 0.25rem;">是否可以终止</div>
                        <div style="font-size: 1.5rem; font-weight: 600; color: {'#065f46' if stats['can_terminate'] else '#991b1b'};">{'✅ 是' if stats['can_terminate'] else '❌ 否'}</div>
                    </div>
                </div>
        """)

        # 变体对比表格
        content.append("""
                <h4 style="margin: 1.5rem 0 0.5rem 0; color: #1f2937;">变体表现对比</h4>
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background: #f9fafb;">
                                <th style="padding: 0.75rem; text-align: left; border-bottom: 2px solid #e5e7eb; font-weight: 600;">变体</th>
                                <th style="padding: 0.75rem; text-align: right; border-bottom: 2px solid #e5e7eb; font-weight: 600;">访客数</th>
                                <th style="padding: 0.75rem; text-align: right; border-bottom: 2px solid #e5e7eb; font-weight: 600;">转化数</th>
                                <th style="padding: 0.75rem; text-align: right; border-bottom: 2px solid #e5e7eb; font-weight: 600;">转化率</th>
                                <th style="padding: 0.75rem; text-align: right; border-bottom: 2px solid #e5e7eb; font-weight: 600;">相对提升</th>
                                <th style="padding: 0.75rem; text-align: right; border-bottom: 2px solid #e5e7eb; font-weight: 600;">统计显著性</th>
                                <th style="padding: 0.75rem; text-align: center; border-bottom: 2px solid #e5e7eb; font-weight: 600;">状态</th>
                            </tr>
                        </thead>
                        <tbody>
        """)

        # 对照组行
        control = stats['control_metrics']
        content.append(f"""
                            <tr style="border-bottom: 1px solid #e5e7eb; background: #f9fafb;">
                                <td style="padding: 0.75rem; font-weight: 500;">{control['variant_name']} (对照组)</td>
                                <td style="padding: 0.75rem; text-align: right;">{control['visitors']:,}</td>
                                <td style="padding: 0.75rem; text-align: right;">{control['conversions']:,}</td>
                                <td style="padding: 0.75rem; text-align: right;">{control['conversion_rate'] * 100:.2f}%</td>
                                <td style="padding: 0.75rem; text-align: right;">-</td>
                                <td style="padding: 0.75rem; text-align: right;">-</td>
                                <td style="padding: 0.75rem; text-align: center;"></td>
                            </tr>
        """)

        # 测试组行
        for metric in stats['test_metrics']:
            improvement = f"{metric['improvement'] * 100:.1f}%"
            if metric['improvement'] > 0:
                improvement = f"<span style=\"color: #059669;\">+{improvement}</span>"
            elif metric['improvement'] < 0:
                improvement = f"<span style=\"color: #dc2626;\">{improvement}</span>"

            significance_style = "color: #059669;" if metric['is_significant'] else "color: #6b7280;"
            status = "🏆 获胜" if metric['is_winner'] else ("✅ 显著" if metric['is_significant'] else "❌ 不显著")

            content.append(f"""
                            <tr style="border-bottom: 1px solid #e5e7eb;">
                                <td style="padding: 0.75rem; font-weight: 500;">{metric['variant_name']}</td>
                                <td style="padding: 0.75rem; text-align: right;">{metric['visitors']:,}</td>
                                <td style="padding: 0.75rem; text-align: right;">{metric['conversions']:,}</td>
                                <td style="padding: 0.75rem; text-align: right;">{metric['conversion_rate'] * 100:.2f}%</td>
                                <td style="padding: 0.75rem; text-align: right;">{improvement}</td>
                                <td style="padding: 0.75rem; text-align: right; {significance_style}">{metric['statistical_significance'] * 100:.1f}%</td>
                                <td style="padding: 0.75rem; text-align: center;">{status}</td>
                            </tr>
            """)

        content.append("""
                        </tbody>
                    </table>
                </div>
            </div>
        """)

        # 结论与建议
        content.append(f"""
            <div style="background: white; border-radius: 8px; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1); padding: 1.5rem; margin-bottom: 2rem;">
                <h3 style="margin-top: 0; color: #1f2937; font-size: 1.25rem;">💡 结论与建议</h3>
                <div style="background: #f0f9ff; border-left: 4px solid #3b82f6; padding: 1rem; margin: 1rem 0; border-radius: 0 6px 6px 0;">
                    <h4 style="margin: 0 0 0.5rem 0; color: #1e40af;">结论</h4>
                    <p style="margin: 0; color: #1e40af; line-height: 1.6;">{conclusion['conclusion'] or '暂无法得出明确结论，需要更多数据支持。'}</p>
                </div>

                <h4 style="margin: 1.5rem 0 0.5rem 0; color: #1f2937;">建议</h4>
                <ul style="margin: 0; padding-left: 1.5rem;">
        """)

        for rec in conclusion['recommendations']:
            content.append(f"<li style=\"margin-bottom: 0.5rem; line-height: 1.6;\">{rec}</li>")

        content.append("""
                </ul>

                <h4 style="margin: 1.5rem 0 0.5rem 0; color: #1f2937;">下一步行动</h4>
                <div style="display: flex; flex-direction: column; gap: 0.5rem;">
        """)

        for step in conclusion['next_steps']:
            content.append(f"""
                    <div style="display: flex; align-items: flex-start; gap: 0.5rem;">
                        <input type="checkbox" style="margin-top: 0.25rem;">
                        <span style="line-height: 1.6;">{step}</span>
                    </div>
            """)

        content.append(f"""
                </div>
            </div>

            <div style="text-align: center; color: #6b7280; font-size: 0.875rem; padding-top: 2rem; border-top: 1px solid #e5e7eb;">
                报告生成时间: {basic['generated_at']}
            </div>
        </div>
        """)

        if full_page:
            html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>A/B测试报告 - {basic['test_name']}</title>
    <style>
        body {{
            margin: 0;
            padding: 2rem;
            background-color: #f9fafb;
        }}
    </style>
    {'<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>' if include_charts else ''}
</head>
<body>
    {''.join(content)}
</body>
</html>
            """
            return html
        else:
            return ''.join(content)
