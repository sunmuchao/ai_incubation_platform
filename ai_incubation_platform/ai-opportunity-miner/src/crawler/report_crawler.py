"""
行业报告数据爬虫
支持模拟行业报告数据
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
from models.opportunity import SourceType

logger = logging.getLogger(__name__)

class ReportCrawler:
    """行业报告爬虫"""

    def __init__(self):
        # 目前使用模拟数据，真实场景可接入各类行业报告API
        self.use_mock = True

    async def fetch_reports(self, keywords: List[str], limit: int = 10) -> List[Dict]:
        """获取行业报告数据"""
        return self._generate_mock_reports(keywords, limit)

    def _generate_mock_reports(self, keywords: List[str], limit: int) -> List[Dict]:
        """生成模拟行业报告数据"""
        report_templates = [
            {
                "title": "2026年{keyword}行业发展白皮书",
                "publisher": "中国行业研究中心",
                "publish_date": "2026-03-15",
                "summary": "本报告全面分析了{keyword}行业的发展现状、市场规模、竞争格局和未来趋势。数据显示，2025年{keyword}市场规模达到850亿元，预计2028年将突破3000亿元，年复合增长率达到45%。",
                "key_findings": [
                    "政策支持力度持续加大，十四五期间相关补贴金额超过200亿元",
                    "技术迭代加速，核心元器件成本三年下降65%",
                    "下游应用场景不断拓展，工业领域占比达到42%",
                    "市场集中度逐步提升，头部企业占据60%以上市场份额"
                ],
                "market_size": 850,
                "growth_rate": 0.45,
                "forecast_period": "2026-2030",
                "url": "https://example.com/reports/2026-{keyword}-whitepaper"
            },
            {
                "title": "{keyword}产业链深度研究报告",
                "publisher": "领先产业研究院",
                "publish_date": "2026-02-28",
                "summary": "本报告深入剖析了{keyword}产业链上下游的价值分布、核心玩家和发展瓶颈。上游核心技术壁垒较高，毛利率达到55%；中游制造环节竞争激烈，毛利率约25%；下游应用端定制化需求旺盛，毛利率可达40%。",
                "key_findings": [
                    "上游核心零部件国产化率仅为30%，替代空间巨大",
                    "中游产能扩张迅速，2026年预计新增产能超过120GW",
                    "下游新兴应用场景不断涌现，储能、新能源汽车等领域需求旺盛",
                    "产业链一体化趋势明显，头部企业纷纷垂直整合"
                ],
                "market_size": 850,
                "growth_rate": 0.45,
                "forecast_period": "2026-2030",
                "url": "https://example.com/reports/{keyword}-industry-chain-2026"
            },
            {
                "title": "{keyword}技术专利分析报告",
                "publisher": "知识产权研究中心",
                "publish_date": "2026-01-20",
                "summary": "报告统计了全球{keyword}相关专利申请情况，中国企业申请量占比达到48%，位居全球第一。技术创新主要集中在材料科学、制造工艺和系统集成三个领域。",
                "key_findings": [
                    "中国企业专利申请量全球领先，占比48%",
                    "核心技术专利主要掌握在少数头部企业手中",
                    "技术迭代周期缩短至18个月，研发投入持续增加",
                    "专利布局正在从国内向全球拓展"
                ],
                "market_size": 850,
                "growth_rate": 0.45,
                "forecast_period": "2026-2030",
                "url": "https://example.com/reports/{keyword}-patent-analysis-2026"
            },
            {
                "title": "{keyword}市场竞争格局分析报告",
                "publisher": "市场研究咨询公司",
                "publish_date": "2026-03-05",
                "summary": "报告分析了{keyword}市场的竞争格局，CR5市场集中度达到62%，头部企业优势明显。价格战和技术创新是主要竞争手段，行业正在经历快速洗牌期。",
                "key_findings": [
                    "CR5市场集中度62%，头部效应显著",
                    "头部企业研发投入占比普遍超过15%",
                    "中小企业生存空间被挤压，并购重组加速",
                    "差异化竞争成为突围关键"
                ],
                "market_size": 850,
                "growth_rate": 0.45,
                "forecast_period": "2026-2030",
                "url": "https://example.com/reports/{keyword}-competition-2026"
            },
            {
                "title": "{keyword}投资前景分析报告",
                "publisher": "证券研究所",
                "publish_date": "2026-03-20",
                "summary": "报告认为{keyword}行业正处于高速增长期，具备较高的投资价值。建议重点关注拥有核心技术、产能优势和渠道资源的龙头企业，以及在细分领域具备差异化优势的创新型企业。",
                "key_findings": [
                    "行业处于高速增长期，投资窗口期良好",
                    "一级市场估值水平持续上升，平均市盈率达到45倍",
                    "科创板和创业板相关上市公司平均涨幅超过80%",
                    "长期看好具备技术壁垒和规模优势的头部企业"
                ],
                "market_size": 850,
                "growth_rate": 0.45,
                "forecast_period": "2026-2030",
                "url": "https://example.com/reports/{keyword}-investment-2026"
            }
        ]

        mock_reports = []
        for i in range(limit):
            keyword = keywords[i % len(keywords)]
            template = report_templates[i % len(report_templates)]

            publish_date = datetime.now() - timedelta(days=30 + i * 10)

            report_item = {
                "title": template["title"].format(keyword=keyword),
                "publisher": template["publisher"],
                "publish_date": publish_date,
                "summary": template["summary"].format(keyword=keyword),
                "key_findings": template["key_findings"],
                "market_size": template["market_size"],
                "growth_rate": template["growth_rate"],
                "forecast_period": template["forecast_period"],
                "url": template["url"].format(keyword=keyword.lower().replace(" ", "-")),
                "source_type": SourceType.INDUSTRY_REPORT.value,
                "pages": 80 + i * 10,
                "price": 5000 + i * 1000
            }
            mock_reports.append(report_item)

        return mock_reports

    async def fetch_industry_reports(self, industry: str) -> List[Dict]:
        """获取行业报告"""
        keywords = [industry]
        return await self.fetch_reports(keywords)

report_crawler = ReportCrawler()
