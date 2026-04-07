"""
真实数据源集成服务 - P0 真实数据源

功能:
1. 统一数据源接入层
2. 数据源配置管理
3. 数据缓存和同步
4. 数据质量校验
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, date, timedelta
from data_sources.base import (
    BaseKeywordDataSource,
    BaseCompetitorDataSource,
    DataSourceConfigError,
    DataSourceAPIError,
    DataSourceRateLimitError,
    DataSourceHealthStatus
)
from data_sources.providers.google_provider import GoogleSearchConsoleKeywordProvider
from data_sources.providers.ahrefs_provider import AhrefsKeywordProvider, AhrefsCompetitorProvider
from data_sources.providers.semrush_provider import SEMrushKeywordProvider, SEMrushCompetitorProvider, DataSourceFactory
from core.config import settings
import logging
import hashlib
import json
from functools import wraps
import time

logger = logging.getLogger(__name__)


# ==================== 数据源配置管理 ====================

class DataSourceSettings:
    """数据源配置设置"""

    def __init__(self):
        # Google Search Console 配置
        self.gsc_config = {
            'credentials_path': settings.GOOGLE_SERVICE_ACCOUNT_KEY_PATH,
            'site_url': settings.GOOGLE_SEARCH_CONSOLE_SITE_URL,
        }

        # Ahrefs 配置
        self.ahrefs_config = {
            'api_key': settings.AHREFS_API_KEY,
        }

        # SEMrush 配置
        self.semrush_config = {
            'api_key': settings.SEMRUSH_API_KEY,
        }

    def is_gsc_available(self) -> bool:
        """检查 GSC 是否可用"""
        return bool(self.gsc_config.get('credentials_path') and self.gsc_config.get('site_url'))

    def is_ahrefs_available(self) -> bool:
        """检查 Ahrefs 是否可用"""
        return bool(self.ahrefs_config.get('api_key'))

    def is_semrush_available(self) -> bool:
        """检查 SEMrush 是否可用"""
        return bool(self.semrush_config.get('api_key'))

    def get_default_keyword_source(self) -> str:
        """获取默认关键词数据源"""
        if self.is_semrush_available():
            return 'semrush'
        elif self.is_ahrefs_available():
            return 'ahrefs'
        elif self.is_gsc_available():
            return 'google_search_console'
        else:
            return 'mock'

    def get_default_competitor_source(self) -> str:
        """获取默认竞品数据源"""
        if self.is_semrush_available():
            return 'semrush'
        elif self.is_ahrefs_available():
            return 'ahrefs'
        else:
            return 'mock'


# ==================== 缓存装饰器 ====================

def cache_result(ttl_seconds: int = 3600):
    """
    缓存结果的装饰器

    Args:
        ttl_seconds: 缓存过期时间（秒）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # 生成缓存键
            cache_key = self._generate_cache_key(func.__name__, *args, **kwargs)

            # 检查缓存
            if hasattr(self, '_cache') and cache_key in self._cache:
                cached_data, cached_time = self._cache[cache_key]
                if time.time() - cached_time < ttl_seconds:
                    logger.debug(f"Cache hit for {cache_key}")
                    return cached_data

            # 执行实际函数
            result = func(self, *args, **kwargs)

            # 存储缓存
            if hasattr(self, '_cache'):
                self._cache[cache_key] = (result, time.time())
                logger.debug(f"Cache stored for {cache_key}")

            return result
        return wrapper
    return decorator


# ==================== 数据源集成服务 ====================

class DataSourceIntegrationService:
    """
    数据源集成服务

    功能:
    - 统一管理多个数据源
    - 自动故障转移
    - 数据缓存
    - 数据质量校验
    """

    def __init__(self, settings: Optional[DataSourceSettings] = None):
        self.settings = settings or DataSourceSettings()
        self._cache: Dict[str, Any] = {}
        self._keyword_providers: Dict[str, BaseKeywordDataSource] = {}
        self._competitor_providers: Dict[str, BaseCompetitorDataSource] = {}
        self._initialized = False

    def initialize(self):
        """初始化数据源"""
        if self._initialized:
            return

        logger.info("Initializing data source integration service...")

        # 初始化关键词数据源
        if self.settings.is_ahrefs_available():
            try:
                self._keyword_providers['ahrefs'] = AhrefsKeywordProvider(self.settings.ahrefs_config)
                logger.info("  - Ahrefs keyword provider initialized")
            except Exception as e:
                logger.warning(f"  - Ahrefs initialization failed: {e}")

        if self.settings.is_semrush_available():
            try:
                self._keyword_providers['semrush'] = SEMrushKeywordProvider(self.settings.semrush_config)
                logger.info("  - SEMrush keyword provider initialized")
            except Exception as e:
                logger.warning(f"  - SEMrush initialization failed: {e}")

        if self.settings.is_gsc_available():
            try:
                self._keyword_providers['google_search_console'] = GoogleSearchConsoleKeywordProvider(self.settings.gsc_config)
                logger.info("  - Google Search Console provider initialized")
            except Exception as e:
                logger.warning(f"  - Google Search Console initialization failed: {e}")

        # 初始化竞品数据源
        if self.settings.is_ahrefs_available():
            try:
                self._competitor_providers['ahrefs'] = AhrefsCompetitorProvider(self.settings.ahrefs_config)
                logger.info("  - Ahrefs competitor provider initialized")
            except Exception as e:
                logger.warning(f"  - Ahrefs competitor initialization failed: {e}")

        if self.settings.is_semrush_available():
            try:
                self._competitor_providers['semrush'] = SEMrushCompetitorProvider(self.settings.semrush_config)
                logger.info("  - SEMrush competitor provider initialized")
            except Exception as e:
                logger.warning(f"  - SEMrush competitor initialization failed: {e}")

        self._initialized = True
        logger.info(f"Data source integration initialized with {len(self._keyword_providers)} keyword providers and {len(self._competitor_providers)} competitor providers")

    def _generate_cache_key(self, method_name: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = json.dumps({
            'method': method_name,
            'args': args,
            'kwargs': kwargs
        }, sort_keys=True, default=str)
        return hashlib.md5(key_data.encode()).hexdigest()

    def _get_available_keyword_source(self, preferred_source: str = None) -> Optional[str]:
        """获取可用的关键词数据源"""
        if preferred_source and preferred_source in self._keyword_providers:
            return preferred_source

        # 按优先级返回
        for source in ['semrush', 'ahrefs', 'google_search_console']:
            if source in self._keyword_providers:
                return source

        return None

    def _get_available_competitor_source(self, preferred_source: str = None) -> Optional[str]:
        """获取可用的竞品数据源"""
        if preferred_source and preferred_source in self._competitor_providers:
            return preferred_source

        # 按优先级返回
        for source in ['semrush', 'ahrefs']:
            if source in self._competitor_providers:
                return source

        return None

    # ==================== 关键词数据方法 ====================

    @cache_result(ttl_seconds=3600)
    def get_keyword_suggestions(
        self,
        seed_keywords: List[str],
        source: Optional[str] = None,
        **kwargs
    ) -> List[Dict]:
        """
        获取关键词建议

        Args:
            seed_keywords: 种子关键词列表
            source: 指定数据源（可选）
            **kwargs: country, language, limit 等

        Returns:
            关键词建议列表
        """
        if not self._initialized:
            self.initialize()

        available_source = self._get_available_keyword_source(source)
        if not available_source:
            logger.warning("No keyword data source available")
            return []

        provider = self._keyword_providers[available_source]
        logger.info(f"Getting keyword suggestions from {available_source}")

        try:
            return provider.get_keyword_suggestions(seed_keywords, **kwargs)
        except DataSourceAPIError as e:
            logger.error(f"Failed to get keyword suggestions: {e}")
            return []

    @cache_result(ttl_seconds=3600)
    def get_keyword_metrics(
        self,
        keywords: List[str],
        source: Optional[str] = None,
        **kwargs
    ) -> List[Dict]:
        """
        获取关键词详细指标

        Args:
            keywords: 关键词列表
            source: 指定数据源（可选）
            **kwargs: country, language 等

        Returns:
            关键词指标列表
        """
        if not self._initialized:
            self.initialize()

        available_source = self._get_available_keyword_source(source)
        if not available_source:
            logger.warning("No keyword data source available")
            return []

        provider = self._keyword_providers[available_source]
        logger.info(f"Getting keyword metrics from {available_source}")

        try:
            return provider.get_keyword_metrics(keywords, **kwargs)
        except DataSourceAPIError as e:
            logger.error(f"Failed to get keyword metrics: {e}")
            return []

    @cache_result(ttl_seconds=3600)
    def get_keyword_ranking(
        self,
        domain: str,
        keywords: List[str],
        source: Optional[str] = None,
        **kwargs
    ) -> List[Dict]:
        """
        获取域名在特定关键词上的排名

        Args:
            domain: 域名
            keywords: 关键词列表
            source: 指定数据源（可选）
            **kwargs: country 等

        Returns:
            关键词排名数据
        """
        if not self._initialized:
            self.initialize()

        available_source = self._get_available_keyword_source(source)
        if not available_source:
            logger.warning("No keyword data source available")
            return []

        provider = self._keyword_providers[available_source]
        logger.info(f"Getting keyword rankings from {available_source}")

        try:
            return provider.get_keyword_ranking(domain, keywords, **kwargs)
        except DataSourceAPIError as e:
            logger.error(f"Failed to get keyword rankings: {e}")
            return []

    # ==================== 竞品数据方法 ====================

    @cache_result(ttl_seconds=3600)
    def get_competitor_list(
        self,
        domain: str,
        source: Optional[str] = None,
        **kwargs
    ) -> List[Dict]:
        """
        获取竞争对手列表

        Args:
            domain: 域名
            source: 指定数据源（可选）
            **kwargs: country, limit 等

        Returns:
            竞争对手列表
        """
        if not self._initialized:
            self.initialize()

        available_source = self._get_available_competitor_source(source)
        if not available_source:
            logger.warning("No competitor data source available")
            return []

        provider = self._competitor_providers[available_source]
        logger.info(f"Getting competitor list from {available_source}")

        try:
            return provider.get_competitor_list(domain, **kwargs)
        except DataSourceAPIError as e:
            logger.error(f"Failed to get competitor list: {e}")
            return []

    @cache_result(ttl_seconds=1800)
    def get_competitor_traffic(
        self,
        domain: str,
        start_date: date,
        end_date: date,
        source: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        获取竞争对手流量数据

        Args:
            domain: 域名
            start_date: 开始日期
            end_date: 结束日期
            source: 指定数据源（可选）
            **kwargs: country 等

        Returns:
            流量数据
        """
        if not self._initialized:
            self.initialize()

        available_source = self._get_available_competitor_source(source)
        if not available_source:
            logger.warning("No competitor data source available")
            return {}

        provider = self._competitor_providers[available_source]
        logger.info(f"Getting competitor traffic from {available_source}")

        try:
            return provider.get_competitor_traffic(domain, start_date, end_date, **kwargs)
        except DataSourceAPIError as e:
            logger.error(f"Failed to get competitor traffic: {e}")
            return {}

    @cache_result(ttl_seconds=3600)
    def get_competitor_top_pages(
        self,
        domain: str,
        source: Optional[str] = None,
        **kwargs
    ) -> List[Dict]:
        """
        获取竞争对手 Top 页面

        Args:
            domain: 域名
            source: 指定数据源（可选）
            **kwargs: country, limit 等

        Returns:
            Top 页面列表
        """
        if not self._initialized:
            self.initialize()

        available_source = self._get_available_competitor_source(source)
        if not available_source:
            logger.warning("No competitor data source available")
            return []

        provider = self._competitor_providers[available_source]
        logger.info(f"Getting competitor top pages from {available_source}")

        try:
            return provider.get_competitor_top_pages(domain, **kwargs)
        except DataSourceAPIError as e:
            logger.error(f"Failed to get competitor top pages: {e}")
            return []

    @cache_result(ttl_seconds=3600)
    def get_competitor_backlinks(
        self,
        domain: str,
        source: Optional[str] = None,
        **kwargs
    ) -> List[Dict]:
        """
        获取竞争对手反向链接

        Args:
            domain: 域名
            source: 指定数据源（可选）
            **kwargs: limit 等

        Returns:
            反向链接列表
        """
        if not self._initialized:
            self.initialize()

        available_source = self._get_available_competitor_source(source)
        if not available_source:
            logger.warning("No competitor data source available")
            return []

        provider = self._competitor_providers[available_source]
        logger.info(f"Getting competitor backlinks from {available_source}")

        try:
            return provider.get_competitor_backlinks(domain, **kwargs)
        except DataSourceAPIError as e:
            logger.error(f"Failed to get competitor backlinks: {e}")
            return []

    def get_available_sources(self) -> Dict[str, List[str]]:
        """获取可用的数据源列表"""
        if not self._initialized:
            self.initialize()

        return {
            "keyword_sources": list(self._keyword_providers.keys()),
            "competitor_sources": list(self._competitor_providers.keys()),
            "default_keyword": self.settings.get_default_keyword_source(),
            "default_competitor": self.settings.get_default_competitor_source(),
        }

    def clear_cache(self, pattern: Optional[str] = None):
        """
        清除缓存

        Args:
            pattern: 缓存键模式（可选，默认为全部清除）
        """
        if pattern:
            keys_to_remove = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self._cache[key]
            logger.info(f"Cleared {len(keys_to_remove)} cache entries matching '{pattern}'")
        else:
            self._cache.clear()
            logger.info("Cleared all cache entries")


# ==================== 全局服务实例 ====================

data_source_service: Optional[DataSourceIntegrationService] = None


def get_data_source_service() -> DataSourceIntegrationService:
    """获取数据源集成服务实例"""
    global data_source_service
    if data_source_service is None:
        data_source_service = DataSourceIntegrationService()
        data_source_service.initialize()
    return data_source_service


def init_data_source_service() -> DataSourceIntegrationService:
    """初始化数据源集成服务"""
    global data_source_service
    data_source_service = DataSourceIntegrationService()
    data_source_service.initialize()
    return data_source_service


# ==================== v1.6 新增功能 ====================

class FusedKeywordData:
    """融合关键词数据"""
    def __init__(
        self,
        keyword: str,
        sources: List[str],
        search_volume: Optional[float] = None,
        competition: Optional[float] = None,
        difficulty: Optional[float] = None,
        cpc: Optional[float] = None,
        confidence_score: float = 0.0,
        raw_data: Optional[Dict] = None
    ):
        self.keyword = keyword
        self.sources = sources
        self.search_volume = search_volume
        self.competition = competition
        self.difficulty = difficulty
        self.cpc = cpc
        self.confidence_score = confidence_score
        self.raw_data = raw_data or {}

    def to_dict(self) -> Dict:
        return {
            "keyword": self.keyword,
            "sources": self.sources,
            "metrics": {
                "search_volume": self.search_volume,
                "competition": self.competition,
                "difficulty": self.difficulty,
                "cpc": self.cpc
            },
            "confidence_score": self.confidence_score,
            "data_sources": self.raw_data
        }


class DataSourceExportService:
    """数据源导出服务"""

    @staticmethod
    def export_to_csv(data: List[Dict], fieldnames: Optional[List[str]] = None) -> str:
        """
        导出数据为 CSV 格式

        Args:
            data: 数据列表
            fieldnames: 字段名列表（可选）

        Returns:
            CSV 字符串
        """
        import csv
        import io

        if not data:
            return ""

        if not fieldnames:
            # 自动获取字段名
            all_keys = set()
            for item in data:
                all_keys.update(item.keys())
            fieldnames = sorted(list(all_keys))

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data)

        return output.getvalue()

    @staticmethod
    def export_to_excel(data: List[Dict], sheet_name: str = "Data") -> bytes:
        """
        导出数据为 Excel 格式

        Args:
            data: 数据列表
            sheet_name: 工作表名称

        Returns:
            Excel 文件字节
        """
        try:
            import pandas as pd
            import io

            df = pd.DataFrame(data)
            output = io.BytesIO()

            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)

            return output.getvalue()
        except ImportError:
            # 如果没有 pandas/openpyxl，回退到 CSV
            return DataSourceExportService.export_to_csv(data).encode('utf-8')


# ==================== DataSourceIntegrationService v1.6 增强 ====================

def _check_source_health(
    self,
    source_name: str,
    provider: Any
) -> Dict:
    """检查单个数据源的健康状态"""
    try:
        health_status = provider.check_health()
        quota_info = provider.get_quota_info()

        result = health_status.to_dict()
        if quota_info:
            result["quota"] = quota_info

        result["source_name"] = source_name
        return result
    except Exception as e:
        return {
            "source_name": source_name,
            "available": False,
            "error_message": str(e),
            "last_checked": datetime.now().isoformat()
        }


def check_health(self) -> Dict[str, Dict]:
    """
    检查所有数据源的健康状态

    Returns:
        健康状态字典，包含所有数据源的状态
    """
    if not self._initialized:
        self.initialize()

    health_report = {
        "keyword_sources": {},
        "competitor_sources": {},
        "checked_at": datetime.now().isoformat()
    }

    # 检查关键词数据源
    for name, provider in self._keyword_providers.items():
        health_report["keyword_sources"][name] = self._check_source_health(name, provider)

    # 检查竞品数据源
    for name, provider in self._competitor_providers.items():
        health_report["competitor_sources"][name] = self._check_source_health(name, provider)

    return health_report


def get_quota_info(self, source: Optional[str] = None) -> Dict[str, Dict]:
    """
    获取数据源配额信息

    Args:
        source: 指定数据源（可选）

    Returns:
        配额信息字典
    """
    if not self._initialized:
        self.initialize()

    quota_report = {}

    sources_to_check = []
    if source:
        if source in self._keyword_providers:
            sources_to_check.append((source, self._keyword_providers[source]))
        elif source in self._competitor_providers:
            sources_to_check.append((source, self._competitor_providers[source]))
    else:
        sources_to_check.extend(self._keyword_providers.items())
        sources_to_check.extend(self._competitor_providers.items())

    for name, provider in sources_to_check:
        quota_info = provider.get_quota_info()
        if quota_info:
            quota_report[name] = quota_info
        else:
            quota_report[name] = {"available": False, "message": "Quota info not available"}

    return quota_report


def fuse_keyword_data(
    self,
    keywords: List[str],
    sources: Optional[List[str]] = None,
    **kwargs
) -> List[FusedKeywordData]:
    """
    多数据源融合关键词数据

    Args:
        keywords: 关键词列表
        sources: 指定数据源列表（可选）

    Returns:
        融合后的关键词数据列表
    """
    if not self._initialized:
        self.initialize()

    # 确定要使用的数据源
    if sources is None:
        sources = list(self._keyword_providers.keys())

    if not sources:
        logger.warning("No keyword sources available for fusion")
        return []

    # 从所有指定源获取数据
    all_data = {}
    source_results = {}

    for source in sources:
        if source not in self._keyword_providers:
            continue

        try:
            provider = self._keyword_providers[source]
            metrics = provider.get_keyword_metrics(keywords, **kwargs)

            for item in metrics:
                kw = item.get('keyword', '').lower()
                if kw not in all_data:
                    all_data[kw] = {}
                all_data[kw][source] = item

            source_results[source] = metrics
        except Exception as e:
            logger.warning(f"Failed to get data from {source}: {e}")

    # 融合数据
    fused_results = []
    for keyword, source_data in all_data.items():
        used_sources = list(source_data.keys())

        if not used_sources:
            continue

        # 计算融合值（取平均或加权平均）
        search_volumes = [d.get('search_volume', 0) for d in source_data.values() if d.get('search_volume')]
        competitions = [d.get('competition', 0.5) for d in source_data.values() if d.get('competition') is not None]
        difficulties = [d.get('difficulty', 50) for d in source_data.values() if d.get('difficulty') is not None]
        cpcs = [d.get('cpc', 0) for d in source_data.values() if d.get('cpc') is not None]

        # 计算置信度（数据源越多，置信度越高）
        confidence = min(1.0, len(used_sources) * 0.3 + 0.4)

        fused = FusedKeywordData(
            keyword=keyword,
            sources=used_sources,
            search_volume=sum(search_volumes) / len(search_volumes) if search_volumes else None,
            competition=sum(competitions) / len(competitions) if competitions else None,
            difficulty=sum(difficulties) / len(difficulties) if difficulties else None,
            cpc=sum(cpcs) / len(cpcs) if cpcs else None,
            confidence_score=confidence,
            raw_data=source_data
        )
        fused_results.append(fused)

    # 按搜索量排序
    return sorted(fused_results, key=lambda x: x.search_volume or 0, reverse=True)


def export_data(
    self,
    data_type: str,
    params: Dict,
    format: str = "csv"
) -> bytes:
    """
    导出数据

    Args:
        data_type: 数据类型 (keywords, competitors, rankings)
        params: 查询参数
        format: 导出格式 (csv, excel)

    Returns:
        导出的文件字节
    """
    if not self._initialized:
        self.initialize()

    # 获取数据
    if data_type == "keywords":
        data = self.get_keyword_metrics(
            keywords=params.get('keywords', []),
            country=params.get('country', 'us')
        )
    elif data_type == "suggestions":
        data = self.get_keyword_suggestions(
            seed_keywords=params.get('seed_keywords', []),
            country=params.get('country', 'us'),
            limit=params.get('limit', 100)
        )
    elif data_type == "competitors":
        data = self.get_competitor_list(
            domain=params.get('domain', ''),
            country=params.get('country', 'us'),
            limit=params.get('limit', 50)
        )
    elif data_type == "rankings":
        data = self.get_keyword_ranking(
            domain=params.get('domain', ''),
            keywords=params.get('keywords', []),
            country=params.get('country', 'us')
        )
    else:
        raise ValueError(f"Unknown data type: {data_type}")

    # 导出
    exporter = DataSourceExportService()
    if format.lower() == "excel":
        return exporter.export_to_excel(data)
    else:
        return exporter.export_to_csv(data).encode('utf-8')


# 将新方法绑定到类
DataSourceIntegrationService.check_health = check_health
DataSourceIntegrationService.get_quota_info = get_quota_info
DataSourceIntegrationService.fuse_keyword_data = fuse_keyword_data
DataSourceIntegrationService.export_data = export_data
DataSourceIntegrationService._check_source_health = _check_source_health
