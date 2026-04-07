"""
CSV格式的A/B测试结果报告模板
"""
from typing import Any
import csv
from io import StringIO
from .base import BaseReportTemplate


class CSVReportTemplate(BaseReportTemplate):
    """CSV报告模板"""

    def render(self, format: str = "csv", **kwargs) -> Any:
        """渲染CSV报告"""
        if format.lower() == "csv":
            return self.render_csv(**kwargs)
        elif format.lower() == "json":
            return self.render_json()
        else:
            raise ValueError(f"Unsupported format: {format}")

    def render_csv(self, include_summary: bool = True, include_daily: bool = False) -> str:
        """
        渲染为CSV格式

        Args:
            include_summary: 是否包含汇总信息
            include_daily: 是否包含每日数据（如果有）

        Returns:
            CSV格式字符串
        """
        output = StringIO()
        writer = csv.writer(output)

        if include_summary:
            # 写入测试基本信息
            writer.writerow(["测试基本信息"])
            basic = self.get_basic_info()
            writer.writerow(["测试ID", basic['test_id']])
            writer.writerow(["测试名称", basic['test_name']])
            writer.writerow(["测试页面", basic['page_url']])
            writer.writerow(["状态", basic['status']])
            writer.writerow(["置信水平", f"{basic['confidence_level'] * 100:.0f}%"])
            writer.writerow(["最小样本量", basic['minimum_sample_size']])
            writer.writerow(["创建时间", basic['created_at']])
            writer.writerow(["开始时间", basic['start_time'] or ''])
            writer.writerow(["结束时间", basic['end_time'] or ''])
            writer.writerow([])

            # 写入统计摘要
            writer.writerow(["统计摘要"])
            stats = self.get_statistical_summary()
            writer.writerow(["当前样本量", stats['current_sample_size']])
            writer.writerow(["剩余需要样本量", stats['remaining_sample_size']])
            writer.writerow(["是否有显著获胜者", '是' if stats['has_winner'] else '否'])
            writer.writerow(["是否可以终止测试", '是' if stats['can_terminate'] else '否'])
            writer.writerow([])

        # 写入变体指标表
        writer.writerow(["变体指标详情"])
        writer.writerow([
            "变体ID", "变体名称", "是否对照组", "流量占比(%)", "访客数", "转化数", "转化率(%)",
            "相对提升(%)", "统计显著性(%)", "是否显著", "是否获胜"
        ])

        # 对照组
        control = self.get_basic_info()['control_variant']
        control_metric = next(m for m in self.result.metrics if m.variant_id == control['id'])
        writer.writerow([
            control['id'],
            control['name'],
            "是",
            f"{control['traffic_percentage'] * 100:.0f}",
            control_metric.visitors,
            control_metric.conversions,
            f"{control_metric.conversion_rate * 100:.2f}",
            "0.0",
            f"{control_metric.statistical_significance * 100:.1f}",
            "是",
            "否"
        ])

        # 测试组
        stats = self.get_statistical_summary()
        for metric in stats['test_metrics']:
            variant = next(v for v in self.test.variants if v.id == metric['variant_id'])
            writer.writerow([
                metric['variant_id'],
                metric['variant_name'],
                "否",
                f"{variant.traffic_percentage * 100:.0f}",
                metric['visitors'],
                metric['conversions'],
                f"{metric['conversion_rate'] * 100:.2f}",
                f"{metric['improvement'] * 100:.1f}",
                f"{metric['statistical_significance'] * 100:.1f}",
                "是" if metric['is_significant'] else "否",
                "是" if metric['is_winner'] else "否"
            ])

        if include_summary:
            writer.writerow([])
            writer.writerow(["结论与建议"])
            conclusion = self.get_conclusion_recommendations()
            writer.writerow(["结论", conclusion['conclusion'] or ''])
            writer.writerow([])
            writer.writerow(["建议"])
            for i, rec in enumerate(conclusion['recommendations'], 1):
                writer.writerow([f"建议{i}", rec])
            writer.writerow([])
            writer.writerow(["下一步行动"])
            for i, step in enumerate(conclusion['next_steps'], 1):
                writer.writerow([f"行动{i}", step])

        return output.getvalue()
