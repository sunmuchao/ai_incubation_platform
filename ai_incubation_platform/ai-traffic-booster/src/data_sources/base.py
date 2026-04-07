"""
数据源适配器基类
定义统一的数据源接口，所有具体数据源实现都需要继承此基类
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import date
import time


class DataSourceHealthStatus:
    """数据源健康状态"""
    def __init__(
        self,
        available: bool = False,
        last_checked: Optional[str] = None,
        error_message: Optional[str] = None,
        quota_remaining: Optional[int] = None,
        quota_limit: Optional[int] = None,
        quota_reset_time: Optional[str] = None,
        latency_ms: Optional[float] = None
    ):
        self.available = available
        self.last_checked = last_checked
        self.error_message = error_message
        self.quota_remaining = quota_remaining
        self.quota_limit = quota_limit
        self.quota_reset_time = quota_reset_time
        self.latency_ms = latency_ms

    def to_dict(self) -> Dict:
        return {
            "available": self.available,
            "last_checked": self.last_checked,
            "error_message": self.error_message,
            "quota": {
                "remaining": self.quota_remaining,
                "limit": self.quota_limit,
                "reset_time": self.quota_reset_time
            } if self.quota_limit else None,
            "latency_ms": self.latency_ms
        }


class BaseKeywordDataSource(ABC):
    """关键词数据源基类"""

    @abstractmethod
    def get_keyword_suggestions(self, seed_keywords: List[str], **kwargs) -> List[Dict]:
        """
        获取关键词建议

        Args:
            seed_keywords: 种子关键词列表
            **kwargs: 其他参数，如语言、地区、搜索引擎等

        Returns:
            关键词建议列表，每个元素包含：
            - keyword: 关键词文本
            - search_volume: 搜索量
            - competition: 竞争度 (0-1)
            - difficulty: 排名难度 (0-100)
            - relevance: 相关度 (0-1)
            - cpc: 点击成本（可选）
            - trend: 趋势数据（可选）
        """
        pass

    @abstractmethod
    def get_keyword_metrics(self, keywords: List[str], **kwargs) -> List[Dict]:
        """
        获取关键词详细指标

        Args:
            keywords: 关键词列表
            **kwargs: 其他参数

        Returns:
            关键词指标列表
        """
        pass

    @abstractmethod
    def get_competitor_keywords(self, domain: str, **kwargs) -> List[Dict]:
        """
        获取竞争对手排名关键词

        Args:
            domain: 竞争对手域名
            **kwargs: 其他参数，如排名范围、时间范围等

        Returns:
            竞争对手关键词列表
        """
        pass

    @abstractmethod
    def get_keyword_ranking(self, domain: str, keywords: List[str], **kwargs) -> List[Dict]:
        """
        获取域名在特定关键词上的排名

        Args:
            domain: 要查询的域名
            keywords: 关键词列表
            **kwargs: 其他参数

        Returns:
            关键词排名数据
        """
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        """数据源名称"""
        pass

    @property
    @abstractmethod
    def supported_regions(self) -> List[str]:
        """支持的地区列表"""
        pass

    @property
    @abstractmethod
    def supported_languages(self) -> List[str]:
        """支持的语言列表"""
        pass

    def check_health(self) -> DataSourceHealthStatus:
        """
        检查数据源健康状态

        Returns:
            DataSourceHealthStatus 健康状态对象
        """
        start_time = time.time()
        try:
            # 尝试执行一个简单的 API 调用
            self.get_keyword_suggestions(["test"], limit=1)
            latency = (time.time() - start_time) * 1000
            return DataSourceHealthStatus(
                available=True,
                latency_ms=latency,
                last_checked=time.strftime("%Y-%m-%dT%H:%M:%SZ")
            )
        except Exception as e:
            return DataSourceHealthStatus(
                available=False,
                error_message=str(e),
                last_checked=time.strftime("%Y-%m-%dT%H:%M:%SZ")
            )

    def get_quota_info(self) -> Optional[Dict]:
        """
        获取配额信息

        Returns:
            配额信息字典，或 None（如果不支持）
        """
        return None


class BaseCompetitorDataSource(ABC):
    """竞品数据源基类"""

    @abstractmethod
    def get_competitor_list(self, domain: str, **kwargs) -> List[Dict]:
        """
        获取竞争对手列表

        Args:
            domain: 自己的域名
            **kwargs: 其他参数，如行业、地区等

        Returns:
            竞争对手列表，包含域名、相似度、流量估算等
        """
        pass

    @abstractmethod
    def get_competitor_traffic(self, domain: str, start_date: date, end_date: date, **kwargs) -> Dict:
        """
        获取竞争对手流量数据

        Args:
            domain: 竞争对手域名
            start_date: 开始日期
            end_date: 结束日期
            **kwargs: 其他参数

        Returns:
            流量数据，包括总流量、来源分布、趋势等
        """
        pass

    @abstractmethod
    def get_competitor_top_pages(self, domain: str, **kwargs) -> List[Dict]:
        """
        获取竞争对手 Top 页面

        Args:
            domain: 竞争对手域名
            **kwargs: 其他参数

        Returns:
            Top 页面列表，包含 URL、流量、关键词等
        """
        pass

    @abstractmethod
    def get_competitor_backlinks(self, domain: str, **kwargs) -> List[Dict]:
        """
        获取竞争对手反向链接

        Args:
            domain: 竞争对手域名
            **kwargs: 其他参数

        Returns:
            反向链接列表
        """
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        """数据源名称"""
        pass

    def check_health(self) -> DataSourceHealthStatus:
        """
        检查数据源健康状态

        Returns:
            DataSourceHealthStatus 健康状态对象
        """
        start_time = time.time()
        try:
            # 尝试执行一个简单的 API 调用
            self.get_competitor_list("example.com", limit=1)
            latency = (time.time() - start_time) * 1000
            return DataSourceHealthStatus(
                available=True,
                latency_ms=latency,
                last_checked=time.strftime("%Y-%m-%dT%H:%M:%SZ")
            )
        except Exception as e:
            return DataSourceHealthStatus(
                available=False,
                error_message=str(e),
                last_checked=time.strftime("%Y-%m-%dT%H:%M:%SZ")
            )

    def get_quota_info(self) -> Optional[Dict]:
        """
        获取配额信息

        Returns:
            配额信息字典，或 None（如果不支持）
        """
        return None


class DataSourceError(Exception):
    """数据源异常基类"""
    pass


class DataSourceConfigError(DataSourceError):
    """数据源配置错误"""
    pass


class DataSourceAPIError(DataSourceError):
    """数据源 API 调用错误"""
    pass


class DataSourceRateLimitError(DataSourceAPIError):
    """数据源调用限流"""
    pass
