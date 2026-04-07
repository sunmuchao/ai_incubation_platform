"""
数据源工厂
管理所有可用数据源，提供统一的数据源获取接口
"""
from typing import Dict, Type, Optional, List
from .base import BaseKeywordDataSource, BaseCompetitorDataSource
from core.config import settings
import logging

logger = logging.getLogger(__name__)


class DataSourceFactory:
    """数据源工厂类"""

    _keyword_sources: Dict[str, Type[BaseKeywordDataSource]] = {}
    _competitor_sources: Dict[str, Type[BaseCompetitorDataSource]] = {}

    @classmethod
    def register_keyword_source(cls, source_class: Type[BaseKeywordDataSource]) -> None:
        """注册关键词数据源"""
        source_name = source_class.source_name
        cls._keyword_sources[source_name] = source_class
        logger.info(f"Registered keyword data source: {source_name}")

    @classmethod
    def register_competitor_source(cls, source_class: Type[BaseCompetitorDataSource]) -> None:
        """注册竞品数据源"""
        source_name = source_class.source_name
        cls._competitor_sources[source_name] = source_class
        logger.info(f"Registered competitor data source: {source_name}")

    @classmethod
    def get_keyword_source(
        cls,
        source_name: Optional[str] = None,
        config: Optional[Dict] = None
    ) -> BaseKeywordDataSource:
        """
        获取关键词数据源实例

        Args:
            source_name: 数据源名称，不指定则使用默认配置
            config: 数据源配置，不指定则使用全局配置

        Returns:
            关键词数据源实例
        """
        if not source_name:
            source_name = settings.DEFAULT_KEYWORD_SOURCE or "mock"

        if source_name not in cls._keyword_sources:
            raise ValueError(
                f"Unknown keyword data source: {source_name}. "
                f"Available sources: {list(cls._keyword_sources.keys())}"
            )

        source_class = cls._keyword_sources[source_name]
        return source_class(config or {})

    @classmethod
    def get_competitor_source(
        cls,
        source_name: Optional[str] = None,
        config: Optional[Dict] = None
    ) -> BaseCompetitorDataSource:
        """
        获取竞品数据源实例

        Args:
            source_name: 数据源名称，不指定则使用默认配置
            config: 数据源配置，不指定则使用全局配置

        Returns:
            竞品数据源实例
        """
        if not source_name:
            source_name = settings.DEFAULT_COMPETITOR_SOURCE or "mock"

        if source_name not in cls._competitor_sources:
            raise ValueError(
                f"Unknown competitor data source: {source_name}. "
                f"Available sources: {list(cls._competitor_sources.keys())}"
            )

        source_class = cls._competitor_sources[source_name]
        return source_class(config or {})

    @classmethod
    def list_keyword_sources(cls) -> List[str]:
        """列出所有可用的关键词数据源"""
        return list(cls._keyword_sources.keys())

    @classmethod
    def list_competitor_sources(cls) -> List[str]:
        """列出所有可用的竞品数据源"""
        return list(cls._competitor_sources.keys())


# 全局工厂实例
data_source_factory = DataSourceFactory()
