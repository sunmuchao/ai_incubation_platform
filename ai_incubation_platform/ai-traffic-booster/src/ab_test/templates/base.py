"""
A/B测试结果统计模板基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from schemas.ab_test import ABTestResponse, ABTestResultResponse
import json


class BaseReportTemplate(ABC):
    """报告模板基类"""

    def __init__(self, test: ABTestResponse, result: ABTestResultResponse):
        self.test = test
        self.result = result
        self.generated_at = datetime.now()

    @abstractmethod
    def render(self, format: str = "json", **kwargs) -> Any:
        """
        渲染报告

        Args:
            format: 输出格式：json, markdown, html, csv
            **kwargs: 其他渲染参数

        Returns:
            渲染后的报告内容
        """
        pass

    def get_basic_info(self) -> Dict[str, Any]:
        """获取测试基本信息"""
        control_variant = next(v for v in self.test.variants if v.is_control)
        test_variants = [v for v in self.test.variants if not v.is_control]

        return {
            "test_id": self.test.id,
            "test_name": self.test.name,
            "test_description": self.test.description,
            "page_url": self.test.page_url,
            "status": self.test.status,
            "created_at": self.test.created_at.isoformat(),
            "start_time": self.test.start_time.isoformat() if self.test.start_time else None,
            "end_time": self.test.end_time.isoformat() if self.test.end_time else None,
            "created_by": self.test.created_by,
            "confidence_level": self.test.confidence_level,
            "minimum_sample_size": self.test.minimum_sample_size,
            "control_variant": {
                "id": control_variant.id,
                "name": control_variant.name,
                "description": control_variant.description,
                "traffic_percentage": control_variant.traffic_percentage
            },
            "test_variants": [
                {
                    "id": v.id,
                    "name": v.name,
                    "description": v.description,
                    "traffic_percentage": v.traffic_percentage
                } for v in test_variants
            ],
            "goals": [g.model_dump() for g in self.test.goals],
            "generated_at": self.generated_at.isoformat()
        }

    def get_statistical_summary(self) -> Dict[str, Any]:
        """获取统计摘要"""
        control_metric = next(m for m in self.result.metrics if m.is_winner is False and any(v.id == m.variant_id for v in self.test.variants if v.is_control))
        test_metrics = [m for m in self.result.metrics if not any(v.id == m.variant_id for v in self.test.variants if v.is_control)]

        # 计算统计显著性
        significant_improvements = [
            m for m in test_metrics
            if m.statistical_significance >= self.test.confidence_level and m.improvement > 0
        ]
        significant_drops = [
            m for m in test_metrics
            if m.statistical_significance >= self.test.confidence_level and m.improvement < 0
        ]

        return {
            "current_sample_size": self.result.current_sample_size,
            "remaining_sample_size": self.result.remaining_sample_size,
            "has_winner": self.result.has_winner,
            "can_terminate": self.result.can_terminate,
            "confidence_level": self.result.confidence_level,
            "control_metrics": {
                "variant_id": control_metric.variant_id,
                "variant_name": control_metric.variant_name,
                "visitors": control_metric.visitors,
                "conversions": control_metric.conversions,
                "conversion_rate": control_metric.conversion_rate,
                "statistical_significance": control_metric.statistical_significance
            },
            "test_metrics": [
                {
                    "variant_id": m.variant_id,
                    "variant_name": m.variant_name,
                    "visitors": m.visitors,
                    "conversions": m.conversions,
                    "conversion_rate": m.conversion_rate,
                    "improvement": m.improvement,
                    "improvement_percent": f"{m.improvement * 100:.1f}%",
                    "statistical_significance": m.statistical_significance,
                    "is_significant": m.statistical_significance >= self.test.confidence_level,
                    "is_winner": m.is_winner
                } for m in test_metrics
            ],
            "statistical_summary": {
                "total_variants": len(self.test.variants),
                "significant_improvements": len(significant_improvements),
                "significant_drops": len(significant_drops),
                "no_significant_difference": len(test_metrics) - len(significant_improvements) - len(significant_drops),
                "winner_id": next((m.variant_id for m in self.result.metrics if m.is_winner), None),
                "winner_name": next((m.variant_name for m in self.result.metrics if m.is_winner), None)
            }
        }

    def get_conclusion_recommendations(self) -> Dict[str, Any]:
        """获取结论和建议"""
        return {
            "conclusion": self.result.conclusion,
            "recommendations": self.result.recommendations,
            "next_steps": self._generate_next_steps()
        }

    def _generate_next_steps(self) -> List[str]:
        """生成下一步建议"""
        steps = []

        if self.result.has_winner:
            winner = next(m for m in self.result.metrics if m.is_winner)
            steps.append(f"全量部署获胜变体 '{winner.variant_name}'")
            steps.append("监控全量部署后的实际效果")
            steps.append("记录本次测试结果作为后续测试参考")
        elif self.result.can_terminate:
            steps.append("结束当前测试，没有显著更优的变体")
            steps.append("考虑设计新的测试方案，尝试不同的变量")
            steps.append("分析测试数据，找出可能的优化方向")
        else:
            steps.append(f"继续运行测试，还需要 {self.result.remaining_sample_size} 个样本")
            steps.append("定期监控测试数据变化，避免外部因素干扰")
            steps.append("如长时间无显著差异，可考虑终止测试")

        steps.append("持续跟踪核心业务指标变化")
        return steps

    def render_json(self) -> Dict[str, Any]:
        """渲染为JSON格式"""
        return {
            "basic_info": self.get_basic_info(),
            "statistical_summary": self.get_statistical_summary(),
            "conclusion_recommendations": self.get_conclusion_recommendations()
        }

    def render_markdown(self, **kwargs) -> str:
        """渲染为Markdown格式"""
        basic = self.get_basic_info()
        stats = self.get_statistical_summary()
        conclusion = self.get_conclusion_recommendations()

        lines = [
            f"# A/B测试报告: {basic['test_name']}",
            "",
            f"**测试ID**: {basic['test_id']}",
            f"**状态**: {basic['status']}",
            f"**测试页面**: [{basic['page_url']}]({basic['page_url']})",
            f"**置信水平**: {basic['confidence_level'] * 100:.0f}%",
            f"**最小样本量**: {basic['minimum_sample_size']}",
            "",
            "## 测试基本信息",
            "",
            f"- **创建时间**: {basic['created_at']}",
            f"- **开始时间**: {basic['start_time'] or '未开始'}",
            f"- **结束时间**: {basic['end_time'] or '未结束'}",
            f"- **创建人**: {basic['created_by']}",
            "",
            "### 测试变体",
            "",
            f"- **对照组**: {basic['control_variant']['name']} (流量: {basic['control_variant']['traffic_percentage'] * 100:.0f}%)",
            f"  - {basic['control_variant']['description']}",
        ]

        for variant in basic['test_variants']:
            lines.append(f"- **测试组 {variant['name']}**: {variant['name']} (流量: {variant['traffic_percentage'] * 100:.0f}%)")
            lines.append(f"  - {variant['description']}")

        lines.extend([
            "",
            "### 测试目标",
            "",
        ])

        for goal in basic['goals']:
            op = "提升" if goal['operator'] == 'increase' else "降低"
            lines.append(f"- **{goal['name']}**: {op} {goal['metric']} 到 {goal['target_value']}")

        lines.extend([
            "",
            "## 统计结果",
            "",
            f"- **当前样本量**: {stats['current_sample_size']}",
            f"- **剩余需要样本量**: {stats['remaining_sample_size']}",
            f"- **是否有显著获胜者**: {'是' if stats['has_winner'] else '否'}",
            f"- **是否可以终止测试**: {'是' if stats['can_terminate'] else '否'}",
            "",
            "### 对照组表现",
            "",
            f"- **访客数**: {stats['control_metrics']['visitors']}",
            f"- **转化数**: {stats['control_metrics']['conversions']}",
            f"- **转化率**: {stats['control_metrics']['conversion_rate'] * 100:.2f}%",
            "",
            "### 测试组表现",
            "",
            "| 变体名称 | 访客数 | 转化数 | 转化率 | 相对提升 | 统计显著性 | 显著 | 获胜 |",
            "|----------|--------|--------|--------|----------|------------|------|------|",
        ])

        for metric in stats['test_metrics']:
            improvement = metric['improvement_percent']
            if metric['improvement'] > 0:
                improvement = f"+{improvement}"
            significant = "✅" if metric['is_significant'] else "❌"
            winner = "🏆" if metric['is_winner'] else ""
            lines.append(
                f"| {metric['variant_name']} | {metric['visitors']} | {metric['conversions']} | "
                f"{metric['conversion_rate'] * 100:.2f}% | {improvement} | "
                f"{metric['statistical_significance'] * 100:.1f}% | {significant} | {winner} |"
            )

        lines.extend([
            "",
            "## 结论与建议",
            "",
            f"### 结论",
            "",
            conclusion['conclusion'] or "暂无法得出明确结论",
            "",
            "### 建议",
            "",
        ])

        for rec in conclusion['recommendations']:
            lines.append(f"- {rec}")

        lines.extend([
            "",
            "### 下一步行动",
            "",
        ])

        for step in conclusion['next_steps']:
            lines.append(f"- [ ] {step}")

        lines.extend([
            "",
            f"---",
            f"*报告生成时间: {basic['generated_at']}*",
        ])

        return "\n".join(lines)
