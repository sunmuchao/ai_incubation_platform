"""
竞争情报 DeerFlow 工具集 (P4)
"""
from typing import List, Dict, Optional
from schemas.competitor import CompetitorAnalysisRequest
from analytics.competitor_service import competitor_service


class CompetitorTools:
    """竞争情报 DeerFlow 工具集"""

    def __init__(self):
        self.service = competitor_service

    def add_competitor(self, domain: str, name: Optional[str] = None,
                       industry: Optional[str] = None,
                       description: Optional[str] = None,
                       tags: Optional[List[str]] = None) -> Dict:
        """
        添加竞品到追踪列表

        Args:
            domain: 竞品域名
            name: 竞品名称（可选）
            industry: 所属行业（可选）
            description: 竞品描述（可选）
            tags: 标签列表（可选）

        Returns:
            添加结果
        """
        from schemas.competitor import CompetitorCreateRequest
        request = CompetitorCreateRequest(
            domain=domain,
            name=name,
            description=description,
            industry=industry,
            tags=tags
        )
        competitor = self.service.add_competitor(request)
        return {
            "competitor_id": competitor.competitor_id,
            "domain": competitor.domain,
            "name": competitor.name,
            "message": "竞品添加成功"
        }

    def list_competitors(self) -> Dict:
        """
        获取竞品列表

        Returns:
            竞品列表
        """
        competitors = self.service.list_competitors()
        return {
            "competitors": [
                {
                    "competitor_id": c.competitor_id,
                    "domain": c.domain,
                    "name": c.name,
                    "industry": c.industry
                }
                for c in competitors
            ],
            "total": len(competitors)
        }

    def get_metrics(self, domain: str) -> Dict:
        """
        获取竞品流量指标

        Args:
            domain: 竞品域名

        Returns:
            流量指标数据
        """
        metrics = self.service.get_competitor_metrics(domain)
        return metrics.model_dump()

    def get_traffic_sources(self, domain: str) -> Dict:
        """
        获取竞品流量来源分布

        Args:
            domain: 竞品域名

        Returns:
            流量来源分布数据
        """
        sources = self.service.get_competitor_traffic_sources(domain)
        return sources.model_dump()

    def get_keywords(self, domain: str, limit: int = 20) -> Dict:
        """
        获取竞品关键词列表

        Args:
            domain: 竞品域名
            limit: 返回数量限制

        Returns:
            关键词列表
        """
        keywords = self.service.get_competitor_keywords(domain, limit)
        return {
            "keywords": [kw.model_dump() for kw in keywords],
            "total": len(keywords)
        }

    def analyze_competitors(self, domains: List[str]) -> Dict:
        """
        竞品对比分析

        Args:
            domains: 域名列表（第一个为你的域名，其余为竞品）

        Returns:
            对比分析结果
        """
        request = CompetitorAnalysisRequest(domains=domains)
        result = self.service.analyze_competitors(request)
        return result.model_dump()

    def analyze_keyword_gap(self, your_domain: str,
                            competitor_domains: List[str]) -> Dict:
        """
        关键词差距分析

        Args:
            your_domain: 你的域名
            competitor_domains: 竞品域名列表

        Returns:
            关键词差距分析结果
        """
        result = self.service.analyze_keyword_gap(your_domain, competitor_domains)
        return result.model_dump()

    def analyze_content_gap(self, your_domain: str,
                            competitor_domains: List[str]) -> Dict:
        """
        内容差距分析

        Args:
            your_domain: 你的域名
            competitor_domains: 竞品域名列表

        Returns:
            内容差距分析结果
        """
        result = self.service.analyze_content_gap(your_domain, competitor_domains)
        return result.model_dump()

    def analyze_backlink_gap(self, your_domain: str,
                             competitor_domains: List[str]) -> Dict:
        """
        反向链接差距分析

        Args:
            your_domain: 你的域名
            competitor_domains: 竞品域名列表

        Returns:
            反向链接差距分析结果
        """
        result = self.service.analyze_backlink_gap(your_domain, competitor_domains)
        return result.model_dump()

    def get_market_position(self, your_domain: str,
                           competitor_domains: List[str]) -> Dict:
        """
        市场定位分析

        Args:
            your_domain: 你的域名
            competitor_domains: 竞品域名列表

        Returns:
            市场定位分析结果
        """
        result = self.service.get_market_position(your_domain, competitor_domains)
        return result.model_dump()

    def generate_swot(self, your_domain: str,
                     competitor_domains: List[str]) -> Dict:
        """
        生成 SWOT 分析

        Args:
            your_domain: 你的域名
            competitor_domains: 竞品域名列表

        Returns:
            SWOT 分析结果
        """
        result = self.service.generate_swot_analysis(your_domain, competitor_domains)
        return result.model_dump()

    def get_industry_benchmarks(self, industry: str = "saas") -> Dict:
        """
        获取行业基准数据

        Args:
            industry: 行业名称

        Returns:
            行业基准数据
        """
        benchmarks = self.service.get_industry_benchmarks(industry)
        return {
            "industry": industry,
            "benchmarks": [b.model_dump() for b in benchmarks]
        }

    def get_alerts(self, severity_threshold: str = "low",
                   limit: int = 20) -> Dict:
        """
        获取竞品告警列表

        Args:
            severity_threshold: 告警级别阈值 (low/medium/high/critical)
            limit: 返回数量限制

        Returns:
            告警列表
        """
        alerts = self.service.get_alerts(severity_threshold, limit)
        return {
            "alerts": [a.model_dump() for a in alerts],
            "total": len(alerts)
        }


# 导出工具实例
competitor_tools = CompetitorTools()
