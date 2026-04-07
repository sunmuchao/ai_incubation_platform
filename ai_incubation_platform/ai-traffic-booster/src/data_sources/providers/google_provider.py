"""
Google数据源
集成Google Search Console和Google Keyword Planner API
"""
from typing import List, Dict, Optional
from datetime import date
import json
import time
from ..base import (
    BaseKeywordDataSource,
    BaseCompetitorDataSource,
    DataSourceConfigError,
    DataSourceAPIError,
    DataSourceRateLimitError
)
from core.config import settings
import logging

logger = logging.getLogger(__name__)

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_PACKAGES_AVAILABLE = True
except ImportError:
    GOOGLE_PACKAGES_AVAILABLE = False
    logger.warning("Google API packages not installed. Google data sources will not be available.")


class GoogleSearchConsoleKeywordProvider(BaseKeywordDataSource):
    """Google Search Console关键词数据源"""

    source_name = "google_search_console"
    supported_regions = ["CN", "US", "JP", "EU", "GB", "AU", "CA"]
    supported_languages = ["zh-CN", "en-US", "ja-JP", "en-GB", "en-AU", "en-CA"]

    SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
    API_SERVICE_NAME = 'searchconsole'
    API_VERSION = 'v1'

    def __init__(self, config: Optional[Dict] = None):
        if not GOOGLE_PACKAGES_AVAILABLE:
            raise DataSourceConfigError(
                "Google API packages are not installed. "
                "Install them with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )

        self.config = config or {}
        self.credentials_path = self.config.get(
            'credentials_path',
            settings.GOOGLE_SERVICE_ACCOUNT_KEY_PATH
        )
        self.site_url = self.config.get('site_url', settings.GOOGLE_SEARCH_CONSOLE_SITE_URL)

        if not self.credentials_path or not self.site_url:
            raise DataSourceConfigError(
                "Google Search Console configuration missing. "
                "Please provide credentials_path and site_url."
            )

        self._service = None
        self._last_request_time = 0
        self._request_interval = 1  # 1秒请求间隔，避免限流

    def _get_service(self):
        """获取API服务实例"""
        if self._service is None:
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path, scopes=self.SCOPES
                )
                self._service = build(
                    self.API_SERVICE_NAME,
                    self.API_VERSION,
                    credentials=credentials
                )
            except Exception as e:
                raise DataSourceConfigError(f"Failed to initialize Google Search Console API: {str(e)}")
        return self._service

    def _rate_limit(self):
        """请求限流"""
        now = time.time()
        time_since_last = now - self._last_request_time
        if time_since_last < self._request_interval:
            time.sleep(self._request_interval - time_since_last)
        self._last_request_time = time.time()

    def get_keyword_suggestions(self, seed_keywords: List[str], **kwargs) -> List[Dict]:
        """
        获取关键词建议
        注意：GSC本身不提供关键词建议，这里需要结合Keyword Planner API
        """
        raise DataSourceAPIError(
            "Google Search Console does not provide keyword suggestions. "
            "Use Google Keyword Planner API instead."
        )

    def get_keyword_metrics(self, keywords: List[str], **kwargs) -> List[Dict]:
        """获取关键词指标"""
        try:
            self._rate_limit()
            service = self._get_service()

            # 构建请求
            start_date = kwargs.get('start_date', (date.today().replace(day=1) - date.timedelta(days=90)).isoformat())
            end_date = kwargs.get('end_date', date.today().isoformat())

            request = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': ['query'],
                'searchType': 'web',
                'dimensionFilterGroups': [{
                    'filters': [{
                        'dimension': 'query',
                        'operator': 'equals',
                        'expression': kw
                    } for kw in keywords]
                }],
                'rowLimit': len(keywords)
            }

            response = service.searchanalytics().query(
                siteUrl=self.site_url,
                body=request
            ).execute()

            # 处理响应
            metrics = []
            for row in response.get('rows', []):
                query = row['keys'][0]
                metrics.append({
                    "keyword": query,
                    "impressions": row['impressions'],
                    "clicks": row['clicks'],
                    "ctr": row['ctr'],
                    "average_position": row['position'],
                    "search_volume": row['impressions'],  # 用展示量近似搜索量
                    "competition": None,  # GSC不提供竞争度
                    "difficulty": None,  # GSC不提供难度
                    "relevance": 1.0
                })

            return metrics

        except HttpError as e:
            if e.resp.status == 429:
                raise DataSourceRateLimitError(f"Google API rate limit exceeded: {str(e)}")
            raise DataSourceAPIError(f"Google API request failed: {str(e)}")
        except Exception as e:
            raise DataSourceAPIError(f"Failed to get keyword metrics: {str(e)}")

    def get_competitor_keywords(self, domain: str, **kwargs) -> List[Dict]:
        """
        获取竞争对手排名关键词
        GSC只能获取自己站点的数据，无法获取竞争对手数据
        """
        raise DataSourceAPIError(
            "Google Search Console can only retrieve data for verified sites. "
            "Use third-party SEO tools for competitor keyword data."
        )

    def get_keyword_ranking(self, domain: str, keywords: List[str], **kwargs) -> List[Dict]:
        """获取域名在特定关键词上的排名"""
        if domain != self.site_url:
            raise DataSourceAPIError(
                f"Google Search Console can only retrieve data for verified site: {self.site_url}"
            )

        return self.get_keyword_metrics(keywords, **kwargs)


class GoogleKeywordPlannerProvider(BaseKeywordDataSource):
    """Google Keyword Planner关键词数据源"""

    source_name = "google_keyword_planner"
    supported_regions = ["US", "CA", "GB", "AU", "DE", "FR", "JP", "CN"]
    supported_languages = ["en", "es", "fr", "de", "ja", "zh-CN", "zh-TW"]

    def __init__(self, config: Optional[Dict] = None):
        if not GOOGLE_PACKAGES_AVAILABLE:
            raise DataSourceConfigError(
                "Google API packages are not installed. "
                "Install them with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )

        self.config = config or {}
        self.credentials_path = self.config.get(
            'credentials_path',
            settings.GOOGLE_ADS_CREDENTIALS_PATH
        )
        self.customer_id = self.config.get('customer_id', settings.GOOGLE_ADS_CUSTOMER_ID)
        self.developer_token = self.config.get('developer_token', settings.GOOGLE_ADS_DEVELOPER_TOKEN)

        if not all([self.credentials_path, self.customer_id, self.developer_token]):
            raise DataSourceConfigError(
                "Google Ads configuration missing. "
                "Please provide credentials_path, customer_id, and developer_token."
            )

        self._service = None
        self._location_ids = {'US': '2840', 'CN': '2158', 'JP': '2392', 'GB': '2826'}
        self._language_ids = {'en': '1000', 'zh-CN': '2052', 'ja': '1005'}

    def _get_service(self):
        """获取Google Ads服务实例"""
        if self._service is None:
            # 这里需要实际的Google Ads API实现
            # 简化实现，实际项目中需要完整的Google Ads API集成
            raise NotImplementedError(
                "Google Keyword Planner integration requires full Google Ads API setup. "
                "Please refer to Google Ads API documentation for implementation details."
            )
        return self._service

    def get_keyword_suggestions(self, seed_keywords: List[str], **kwargs) -> List[Dict]:
        """获取关键词建议"""
        raise NotImplementedError("Google Keyword Planner integration not yet implemented")

    def get_keyword_metrics(self, keywords: List[str], **kwargs) -> List[Dict]:
        """获取关键词详细指标"""
        raise NotImplementedError("Google Keyword Planner integration not yet implemented")

    def get_competitor_keywords(self, domain: str, **kwargs) -> List[Dict]:
        """获取竞争对手排名关键词"""
        raise NotImplementedError("Google Keyword Planner integration not yet implemented")

    def get_keyword_ranking(self, domain: str, keywords: List[str], **kwargs) -> List[Dict]:
        """获取域名在特定关键词上的排名"""
        raise DataSourceAPIError(
            "Google Keyword Planner does not provide ranking data. "
            "Use Google Search Console API instead."
        )
