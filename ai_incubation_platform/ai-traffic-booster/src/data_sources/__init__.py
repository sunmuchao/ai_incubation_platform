"""
数据源模块
提供可替换的关键词和竞品数据源适配层
"""
from .factory import data_source_factory
from .adapters.keyword_adapter import keyword_adapter
from .adapters.competitor_adapter import competitor_adapter
from .base import (
    BaseKeywordDataSource,
    BaseCompetitorDataSource,
    DataSourceError,
    DataSourceConfigError,
    DataSourceAPIError,
    DataSourceRateLimitError
)

# 注册内置数据源
try:
    from .providers.mock_provider import MockKeywordProvider, MockCompetitorProvider
    data_source_factory.register_keyword_source(MockKeywordProvider)
    data_source_factory.register_competitor_source(MockCompetitorProvider)
except ImportError:
    pass

try:
    from .providers.google_provider import (
        GoogleSearchConsoleKeywordProvider,
        GoogleKeywordPlannerProvider
    )
    data_source_factory.register_keyword_source(GoogleSearchConsoleKeywordProvider)
    data_source_factory.register_keyword_source(GoogleKeywordPlannerProvider)
except ImportError:
    pass

try:
    from .providers.ahrefs_provider import AhrefsKeywordProvider, AhrefsCompetitorProvider
    data_source_factory.register_keyword_source(AhrefsKeywordProvider)
    data_source_factory.register_competitor_source(AhrefsCompetitorProvider)
except ImportError:
    pass

__all__ = [
    "data_source_factory",
    "keyword_adapter",
    "competitor_adapter",
    "BaseKeywordDataSource",
    "BaseCompetitorDataSource",
    "DataSourceError",
    "DataSourceConfigError",
    "DataSourceAPIError",
    "DataSourceRateLimitError"
]
