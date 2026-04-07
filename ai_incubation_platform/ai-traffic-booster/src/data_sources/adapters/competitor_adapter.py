"""
竞品数据适配器
为业务模块提供统一的竞品数据访问接口，自动适配不同数据源
"""
from typing import List, Dict, Optional
from datetime import date
from ..factory import data_source_factory
from ..base import BaseCompetitorDataSource
from core.config import settings
import logging

logger = logging.getLogger(__name__)


class CompetitorDataAdapter:
    """竞品数据适配器"""

    def __init__(self, default_source: Optional[str] = None):
        """
        初始化竞品数据适配器

        Args:
            default_source: 默认数据源名称，不指定则使用配置中的DEFAULT_COMPETITOR_SOURCE
        """
        self.default_source = default_source or settings.DEFAULT_COMPETITOR_SOURCE or "mock"
        self._source_instances: Dict[str, BaseCompetitorDataSource] = {}

    def _get_source(self, source_name: Optional[str] = None) -> BaseCompetitorDataSource:
        """获取数据源实例"""
        source = source_name or self.default_source

        if source not in self._source_instances:
            self._source_instances[source] = data_source_factory.get_competitor_source(source)

        return self._source_instances[source]

    def get_competitor_list(
        self,
        domain: str,
        source_name: Optional[str] = None,
        **kwargs
    ) -> List[Dict]:
        """
        获取竞争对手列表

        Args:
            domain: 自己的域名
            source_name: 数据源名称，不指定则使用默认
            **kwargs: 其他参数，如行业、地区等

        Returns:
            标准化的竞争对手列表
        """
        try:
            source = self._get_source(source_name)
            competitors = source.get_competitor_list(domain, **kwargs)
            return self._standardize_competitor_list(competitors)
        except Exception as e:
            logger.error(f"Failed to get competitor list from {source_name}: {e}")
            # 降级到Mock数据源
            if source_name != "mock":
                logger.info("Falling back to mock data source")
                return self.get_competitor_list(domain, source_name="mock", **kwargs)
            raise

    def get_competitor_traffic(
        self,
        domain: str,
        start_date: date,
        end_date: date,
        source_name: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        获取竞争对手流量数据

        Args:
            domain: 竞争对手域名
            start_date: 开始日期
            end_date: 结束日期
            source_name: 数据源名称，不指定则使用默认
            **kwargs: 其他参数

        Returns:
            标准化的流量数据
        """
        try:
            source = self._get_source(source_name)
            traffic_data = source.get_competitor_traffic(domain, start_date, end_date, **kwargs)
            return self._standardize_traffic_data(traffic_data, start_date, end_date)
        except Exception as e:
            logger.error(f"Failed to get competitor traffic from {source_name}: {e}")
            if source_name != "mock":
                logger.info("Falling back to mock data source")
                return self.get_competitor_traffic(domain, start_date, end_date, source_name="mock", **kwargs)
            raise

    def get_competitor_top_pages(
        self,
        domain: str,
        source_name: Optional[str] = None,
        **kwargs
    ) -> List[Dict]:
        """
        获取竞争对手Top页面

        Args:
            domain: 竞争对手域名
            source_name: 数据源名称，不指定则使用默认
            **kwargs: 其他参数

        Returns:
            标准化的Top页面列表
        """
        try:
            source = self._get_source(source_name)
            pages = source.get_competitor_top_pages(domain, **kwargs)
            return self._standardize_top_pages(pages)
        except Exception as e:
            logger.error(f"Failed to get competitor top pages from {source_name}: {e}")
            if source_name != "mock":
                logger.info("Falling back to mock data source")
                return self.get_competitor_top_pages(domain, source_name="mock", **kwargs)
            raise

    def get_competitor_backlinks(
        self,
        domain: str,
        source_name: Optional[str] = None,
        **kwargs
    ) -> List[Dict]:
        """
        获取竞争对手反向链接

        Args:
            domain: 竞争对手域名
            source_name: 数据源名称，不指定则使用默认
            **kwargs: 其他参数

        Returns:
            标准化的反向链接列表
        """
        try:
            source = self._get_source(source_name)
            backlinks = source.get_competitor_backlinks(domain, **kwargs)
            return self._standardize_backlinks(backlinks)
        except Exception as e:
            logger.error(f"Failed to get competitor backlinks from {source_name}: {e}")
            if source_name != "mock":
                logger.info("Falling back to mock data source")
                return self.get_competitor_backlinks(domain, source_name="mock", **kwargs)
            raise

    def get_competitor_comparison(
        self,
        domain: str,
        competitor_domains: List[str],
        start_date: date,
        end_date: date,
        source_name: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        获取多个竞争对手的对比数据

        Args:
            domain: 自己的域名
            competitor_domains: 竞争对手域名列表
            start_date: 开始日期
            end_date: 结束日期
            source_name: 数据源名称
            **kwargs: 其他参数

        Returns:
            标准化的对比数据
        """
        all_domains = [domain] + competitor_domains
        traffic_data = {}

        for comp_domain in all_domains:
            traffic_data[comp_domain] = self.get_competitor_traffic(
                comp_domain, start_date, end_date, source_name, **kwargs
            )

        # 计算对比指标
        comparison = {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "domains": all_domains,
            "traffic_comparison": [],
            "key_metrics": {}
        }

        # 整理流量对比
        for comp_domain, data in traffic_data.items():
            comparison["traffic_comparison"].append({
                "domain": comp_domain,
                "total_visitors": data["total_visitors"],
                "avg_conversion_rate": data["avg_conversion_rate"],
                "organic_share": data["sources"].get("organic_search", 0),
                "paid_share": data["sources"].get("paid_ad", 0),
                "is_own": comp_domain == domain
            })

        # 计算关键指标对比
        metrics = ["total_visitors", "avg_conversion_rate", "organic_share", "paid_share"]
        for metric in metrics:
            values = []
            for item in comparison["traffic_comparison"]:
                values.append(item[metric])
            comparison["key_metrics"][metric] = {
                "max": max(values),
                "min": min(values),
                "average": sum(values) / len(values) if values else 0,
                "our_value": next((item[metric] for item in comparison["traffic_comparison"] if item["is_own"]), 0),
                "our_rank": sorted(values, reverse=True).index(next((item[metric] for item in comparison["traffic_comparison"] if item["is_own"]), 0)) + 1
            }

        return comparison

    def get_available_sources(self) -> List[str]:
        """获取可用的竞品数据源列表"""
        return data_source_factory.list_competitor_sources()

    def _standardize_competitor_list(self, competitors: List[Dict]) -> List[Dict]:
        """标准化竞争对手列表格式"""
        standardized = []
        for comp in competitors:
            standardized.append({
                "domain": comp.get("domain", ""),
                "name": comp.get("name", comp.get("domain", "").split(".")[0].capitalize()),
                "similarity": round(float(comp.get("similarity", 0)), 2),
                "estimated_traffic": int(comp.get("estimated_traffic", 0)),
                "traffic_rank": int(comp.get("traffic_rank", 0)),
                "market_share": round(float(comp.get("market_share", 0)), 4),
                "domain_authority": round(float(comp.get("domain_authority", comp.get("domain_rating", 0))), 1),
                "main_products": comp.get("main_products", []),
                "strengths": comp.get("strengths", []),
                "source": comp.get("source", "unknown")
            })
        return standardized

    def _standardize_traffic_data(self, traffic_data: Dict, start_date: date, end_date: date) -> Dict:
        """标准化流量数据格式"""
        return {
            "domain": traffic_data.get("domain", ""),
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_visitors": int(traffic_data.get("total_visitors", 0)),
            "total_page_views": int(traffic_data.get("total_page_views", traffic_data.get("total_visitors", 0) * 2)),
            "avg_session_duration": round(float(traffic_data.get("avg_session_duration", 120)), 1),
            "avg_bounce_rate": round(float(traffic_data.get("avg_bounce_rate", 0.5)), 2),
            "avg_conversion_rate": round(float(traffic_data.get("avg_conversion_rate", 0.03)), 3),
            "sources": self._standardize_source_distribution(traffic_data.get("sources", {})),
            "daily_trend": traffic_data.get("daily_trend", []),
            "year_over_year_growth": round(float(traffic_data.get("year_over_year_growth", 0)), 2),
            "domain_authority": round(float(traffic_data.get("domain_authority", traffic_data.get("domain_rating", 0))), 1),
            "backlinks_total": int(traffic_data.get("backlinks_total", traffic_data.get("backlinks", 0))),
            "source": traffic_data.get("source", "unknown")
        }

    def _standardize_source_distribution(self, sources: Dict) -> Dict:
        """标准化流量来源分布"""
        default_sources = {
            "organic_search": 0.0,
            "direct": 0.0,
            "social_media": 0.0,
            "referral": 0.0,
            "paid_ad": 0.0,
            "email": 0.0,
            "other": 0.0
        }

        # 映射不同数据源的来源名称
        source_mapping = {
            "organic": "organic_search",
            "paid": "paid_ad",
            "social": "social_media",
            "refer": "referral"
        }

        normalized = default_sources.copy()
        for key, value in sources.items():
            mapped_key = source_mapping.get(key, key)
            if mapped_key in normalized:
                normalized[mapped_key] = round(float(value), 2)

        # 确保总和为1
        total = sum(normalized.values())
        if total > 0:
            for key in normalized:
                normalized[key] = round(normalized[key] / total, 2)

        return normalized

    def _standardize_top_pages(self, pages: List[Dict]) -> List[Dict]:
        """标准化Top页面格式"""
        standardized = []
        for page in pages:
            standardized.append({
                "url": page.get("url", ""),
                "title": page.get("title", ""),
                "traffic": int(page.get("traffic", 0)),
                "traffic_share": round(float(page.get("traffic_share", 0)), 4),
                "traffic_value": round(float(page.get("traffic_value", page.get("value", 0))), 2),
                "keywords_count": int(page.get("keywords_count", page.get("keywords", 0))),
                "top_keyword": page.get("top_keyword", ""),
                "avg_position": round(float(page.get("avg_position", 0)), 1),
                "published_at": page.get("published_at", None),
                "source": page.get("source", "unknown")
            })
        return standardized

    def _standardize_backlinks(self, backlinks: List[Dict]) -> List[Dict]:
        """标准化反向链接格式"""
        standardized = []
        for link in backlinks:
            standardized.append({
                "source_domain": link.get("source_domain", link.get("domain_from", "")),
                "source_url": link.get("source_url", link.get("url_from", "")),
                "target_url": link.get("target_url", link.get("url_to", "")),
                "anchor_text": link.get("anchor_text", link.get("anchor", "")),
                "domain_authority": round(float(link.get("domain_authority", link.get("domain_rating", 0))), 1),
                "is_follow": bool(link.get("is_follow", link.get("is_dofollow", True))),
                "source_traffic": int(link.get("source_traffic", 0)),
                "first_seen": link.get("first_seen", None),
                "last_seen": link.get("last_seen", None),
                "source": link.get("source", "unknown")
            })
        return standardized


# 全局适配器实例
competitor_adapter = CompetitorDataAdapter()
