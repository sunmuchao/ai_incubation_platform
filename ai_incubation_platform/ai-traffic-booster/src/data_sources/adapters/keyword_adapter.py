"""
关键词数据适配器
为业务模块提供统一的关键词数据访问接口，自动适配不同数据源
"""
from typing import List, Dict, Optional
from datetime import date
from ..factory import data_source_factory
from ..base import BaseKeywordDataSource
from core.config import settings
import logging

logger = logging.getLogger(__name__)


class KeywordDataAdapter:
    """关键词数据适配器"""

    def __init__(self, default_source: Optional[str] = None):
        """
        初始化关键词数据适配器

        Args:
            default_source: 默认数据源名称，不指定则使用配置中的DEFAULT_KEYWORD_SOURCE
        """
        self.default_source = default_source or settings.DEFAULT_KEYWORD_SOURCE or "mock"
        self._source_instances: Dict[str, BaseKeywordDataSource] = {}

    def _get_source(self, source_name: Optional[str] = None) -> BaseKeywordDataSource:
        """获取数据源实例"""
        source = source_name or self.default_source

        if source not in self._source_instances:
            self._source_instances[source] = data_source_factory.get_keyword_source(source)

        return self._source_instances[source]

    def get_keyword_suggestions(
        self,
        seed_keywords: List[str],
        source_name: Optional[str] = None,
        **kwargs
    ) -> List[Dict]:
        """
        获取关键词建议

        Args:
            seed_keywords: 种子关键词列表
            source_name: 数据源名称，不指定则使用默认
            **kwargs: 其他参数，如地区、语言等

        Returns:
            标准化的关键词建议列表
        """
        try:
            source = self._get_source(source_name)
            suggestions = source.get_keyword_suggestions(seed_keywords, **kwargs)
            return self._standardize_keyword_suggestions(suggestions)
        except Exception as e:
            logger.error(f"Failed to get keyword suggestions from {source_name}: {e}")
            # 降级到Mock数据源
            if source_name != "mock":
                logger.info("Falling back to mock data source")
                return self.get_keyword_suggestions(seed_keywords, source_name="mock", **kwargs)
            raise

    def get_keyword_metrics(
        self,
        keywords: List[str],
        source_name: Optional[str] = None,
        **kwargs
    ) -> List[Dict]:
        """
        获取关键词详细指标

        Args:
            keywords: 关键词列表
            source_name: 数据源名称，不指定则使用默认
            **kwargs: 其他参数

        Returns:
            标准化的关键词指标列表
        """
        try:
            source = self._get_source(source_name)
            metrics = source.get_keyword_metrics(keywords, **kwargs)
            return self._standardize_keyword_metrics(metrics)
        except Exception as e:
            logger.error(f"Failed to get keyword metrics from {source_name}: {e}")
            if source_name != "mock":
                logger.info("Falling back to mock data source")
                return self.get_keyword_metrics(keywords, source_name="mock", **kwargs)
            raise

    def get_competitor_keywords(
        self,
        domain: str,
        source_name: Optional[str] = None,
        **kwargs
    ) -> List[Dict]:
        """
        获取竞争对手排名关键词

        Args:
            domain: 竞争对手域名
            source_name: 数据源名称，不指定则使用默认
            **kwargs: 其他参数

        Returns:
            标准化的竞争对手关键词列表
        """
        try:
            source = self._get_source(source_name)
            keywords = source.get_competitor_keywords(domain, **kwargs)
            return self._standardize_competitor_keywords(keywords)
        except Exception as e:
            logger.error(f"Failed to get competitor keywords from {source_name}: {e}")
            if source_name != "mock":
                logger.info("Falling back to mock data source")
                return self.get_competitor_keywords(domain, source_name="mock", **kwargs)
            raise

    def get_keyword_ranking(
        self,
        domain: str,
        keywords: List[str],
        source_name: Optional[str] = None,
        **kwargs
    ) -> List[Dict]:
        """
        获取域名在特定关键词上的排名

        Args:
            domain: 要查询的域名
            keywords: 关键词列表
            source_name: 数据源名称，不指定则使用默认
            **kwargs: 其他参数

        Returns:
            标准化的关键词排名数据
        """
        try:
            source = self._get_source(source_name)
            rankings = source.get_keyword_ranking(domain, keywords, **kwargs)
            return self._standardize_keyword_rankings(rankings)
        except Exception as e:
            logger.error(f"Failed to get keyword rankings from {source_name}: {e}")
            if source_name != "mock":
                logger.info("Falling back to mock data source")
                return self.get_keyword_ranking(domain, keywords, source_name="mock", **kwargs)
            raise

    def batch_get_keyword_data(
        self,
        keyword_groups: Dict[str, List[str]],
        source_name: Optional[str] = None,
        **kwargs
    ) -> Dict[str, List[Dict]]:
        """
        批量获取多组关键词的数据

        Args:
            keyword_groups: 关键词组字典，key为组名，value为关键词列表
            source_name: 数据源名称
            **kwargs: 其他参数

        Returns:
            分组的关键词数据
        """
        results = {}
        for group_name, keywords in keyword_groups.items():
            results[group_name] = self.get_keyword_metrics(keywords, source_name, **kwargs)
        return results

    def get_available_sources(self) -> List[str]:
        """获取可用的关键词数据源列表"""
        return data_source_factory.list_keyword_sources()

    def _standardize_keyword_suggestions(self, suggestions: List[Dict]) -> List[Dict]:
        """标准化关键词建议格式"""
        standardized = []
        for sug in suggestions:
            standardized.append({
                "keyword": sug.get("keyword", ""),
                "search_volume": sug.get("search_volume", 0),
                "competition": round(float(sug.get("competition", 0.5)), 2),
                "difficulty": round(float(sug.get("difficulty", 50)), 1),
                "relevance": round(float(sug.get("relevance", 0.5)), 2),
                "cpc": round(float(sug.get("cpc", 0)), 2),
                "trend": sug.get("trend", []),
                "source": sug.get("source", "unknown")
            })
        return standardized

    def _standardize_keyword_metrics(self, metrics: List[Dict]) -> List[Dict]:
        """标准化关键词指标格式"""
        standardized = []
        for metric in metrics:
            standardized.append({
                "keyword": metric.get("keyword", ""),
                "search_volume": metric.get("search_volume", 0),
                "competition": round(float(metric.get("competition", 0.5)), 2),
                "difficulty": round(float(metric.get("difficulty", 50)), 1),
                "cpc": round(float(metric.get("cpc", 0)), 2),
                "ctr": round(float(metric.get("ctr", 0)), 3),
                "average_position": round(float(metric.get("average_position", 0)), 1),
                "impressions": metric.get("impressions", 0),
                "clicks": metric.get("clicks", 0),
                "trend_30d": round(float(metric.get("trend_30d", 0)), 2),
                "trend_90d": round(float(metric.get("trend_90d", 0)), 2),
                "serp_features": metric.get("serp_features", []),
                "source": metric.get("source", "unknown")
            })
        return standardized

    def _standardize_competitor_keywords(self, keywords: List[Dict]) -> List[Dict]:
        """标准化竞争对手关键词格式"""
        standardized = []
        for kw in keywords:
            standardized.append({
                "keyword": kw.get("keyword", ""),
                "position": int(kw.get("position", 0)),
                "search_volume": kw.get("search_volume", 0),
                "traffic_share": round(float(kw.get("traffic_share", 0)), 2),
                "url": kw.get("url", ""),
                "position_change": int(kw.get("position_change", 0)),
                "difficulty": round(float(kw.get("difficulty", 50)), 1),
                "source": kw.get("source", "unknown")
            })
        return standardized

    def _standardize_keyword_rankings(self, rankings: List[Dict]) -> List[Dict]:
        """标准化关键词排名格式"""
        standardized = []
        for rank in rankings:
            standardized.append({
                "keyword": rank.get("keyword", ""),
                "domain": rank.get("domain", ""),
                "current_position": int(rank.get("current_position", 0)),
                "previous_position": rank.get("previous_position"),
                "best_position": rank.get("best_position"),
                "url": rank.get("url", ""),
                "search_volume": rank.get("search_volume", 0),
                "ctr": round(float(rank.get("ctr", 0)), 3),
                "last_updated": rank.get("last_updated", date.today().isoformat()),
                "source": rank.get("source", "unknown")
            })
        return standardized


# 全局适配器实例
keyword_adapter = KeywordDataAdapter()
