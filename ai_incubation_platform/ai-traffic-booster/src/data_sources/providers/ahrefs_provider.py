"""
Ahrefs数据源
集成Ahrefs SEO工具API
"""
from typing import List, Dict, Optional
from datetime import date, timedelta
import requests
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


class AhrefsKeywordProvider(BaseKeywordDataSource):
    """Ahrefs关键词数据源"""

    source_name = "ahrefs"
    supported_regions = ["US", "GB", "CA", "AU", "DE", "FR", "JP", "CN", "BR", "IN"]
    supported_languages = ["en", "es", "fr", "de", "ja", "zh", "pt", "hi"]

    API_BASE_URL = "https://api.ahrefs.com/v3"

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.api_key = self.config.get('api_key', settings.AHREFS_API_KEY)

        if not self.api_key:
            raise DataSourceConfigError(
                "Ahrefs API key is required. "
                "Please set AHREFS_API_KEY in environment variables or provide it in config."
            )

        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        })
        self._rate_limit_remaining = 1000
        self._rate_limit_reset = 0

    def _make_request(self, endpoint: str, params: Optional[Dict] = None, method: str = "GET") -> Dict:
        """发送API请求"""
        url = f"{self.API_BASE_URL}/{endpoint.lstrip('/')}"

        try:
            response = self._session.request(method, url, params=params)

            # 更新限流信息
            if 'X-RateLimit-Remaining' in response.headers:
                self._rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
            if 'X-RateLimit-Reset' in response.headers:
                self._rate_limit_reset = int(response.headers['X-RateLimit-Reset'])

            if response.status_code == 429:
                reset_in = self._rate_limit_reset - date.today().timestamp()
                raise DataSourceRateLimitError(
                    f"Ahrefs API rate limit exceeded. Resets in {reset_in} seconds. "
                    f"Remaining requests: {self._rate_limit_remaining}"
                )

            if response.status_code != 200:
                raise DataSourceAPIError(
                    f"Ahrefs API request failed with status {response.status_code}: {response.text}"
                )

            return response.json()

        except requests.exceptions.RequestException as e:
            raise DataSourceAPIError(f"Ahrefs API request failed: {str(e)}")

    def get_keyword_suggestions(self, seed_keywords: List[str], **kwargs) -> List[Dict]:
        """获取关键词建议"""
        country = kwargs.get('country', 'US')
        language = kwargs.get('language', 'en')
        limit = kwargs.get('limit', 100)

        params = {
            "keywords": ",".join(seed_keywords),
            "country": country,
            "language": language,
            "limit": limit,
            "select": "keyword,volume,keyword_difficulty,cpc,clicks,return_rate"
        }

        data = self._make_request("/keywords-explorer/keywords-suggestions", params)

        suggestions = []
        for item in data.get('keywords', []):
            suggestions.append({
                "keyword": item['keyword'],
                "search_volume": item['volume'],
                "competition": item.get('competition', 0.5),
                "difficulty": item['keyword_difficulty'],
                "relevance": item.get('relevance', 0.8),
                "cpc": item.get('cpc', 0),
                "clicks_per_search": item.get('clicks', 0),
                "return_rate": item.get('return_rate', 0)
            })

        return sorted(suggestions, key=lambda x: x['search_volume'], reverse=True)

    def get_keyword_metrics(self, keywords: List[str], **kwargs) -> List[Dict]:
        """获取关键词详细指标"""
        country = kwargs.get('country', 'US')
        language = kwargs.get('language', 'en')

        params = {
            "keywords": ",".join(keywords),
            "country": country,
            "language": language,
            "select": "volume,keyword_difficulty,cpc,clicks,trends,serp_features"
        }

        data = self._make_request("/keywords-explorer/metrics", params)

        metrics = []
        for keyword, item in data.get('metrics', {}).items():
            metrics.append({
                "keyword": keyword,
                "search_volume": item['volume'],
                "competition": item.get('competition', 0.5),
                "difficulty": item['keyword_difficulty'],
                "cpc": item.get('cpc', 0),
                "clicks_per_search": item.get('clicks', 0),
                "trend": item.get('trends', []),
                "serp_features": item.get('serp_features', []),
                "parent_topic": item.get('parent_topic', keyword)
            })

        return metrics

    def get_competitor_keywords(self, domain: str, **kwargs) -> List[Dict]:
        """获取竞争对手排名关键词"""
        country = kwargs.get('country', 'US')
        limit = kwargs.get('limit', 1000)

        params = {
            "target": domain,
            "country": country,
            "limit": limit,
            "select": "keyword,position,volume,keyword_difficulty,url,traffic_share,position_history"
        }

        data = self._make_request("/site-explorer/organic-keywords", params)

        keywords = []
        for item in data.get('keywords', []):
            keywords.append({
                "keyword": item['keyword'],
                "position": item['position'],
                "search_volume": item['volume'],
                "difficulty": item['keyword_difficulty'],
                "url": item['url'],
                "traffic_share": item.get('traffic_share', 0),
                "position_change": item.get('position_change', 0)
            })

        return sorted(keywords, key=lambda x: x['search_volume'], reverse=True)

    def get_keyword_ranking(self, domain: str, keywords: List[str], **kwargs) -> List[Dict]:
        """获取域名在特定关键词上的排名"""
        country = kwargs.get('country', 'US')

        params = {
            "target": domain,
            "keywords": ",".join(keywords),
            "country": country,
            "select": "keyword,position,volume,url,position_history"
        }

        data = self._make_request("/site-explorer/rank", params)

        rankings = []
        for item in data.get('rankings', []):
            rankings.append({
                "keyword": item['keyword'],
                "domain": domain,
                "current_position": item['position'],
                "previous_position": item.get('previous_position', None),
                "best_position": item.get('best_position', None),
                "url": item['url'],
                "search_volume": item.get('volume', 0),
                "last_updated": date.today().isoformat()
            })

        return rankings


class AhrefsCompetitorProvider(BaseCompetitorDataSource):
    """Ahrefs竞品数据源"""

    source_name = "ahrefs"

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.api_key = self.config.get('api_key', settings.AHREFS_API_KEY)

        if not self.api_key:
            raise DataSourceConfigError(
                "Ahrefs API key is required. "
                "Please set AHREFS_API_KEY in environment variables or provide it in config."
            )

        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        })

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """发送API请求"""
        url = f"https://api.ahrefs.com/v3/{endpoint.lstrip('/')}"

        try:
            response = self._session.get(url, params=params)

            if response.status_code == 429:
                raise DataSourceRateLimitError("Ahrefs API rate limit exceeded")

            if response.status_code != 200:
                raise DataSourceAPIError(
                    f"Ahrefs API request failed with status {response.status_code}: {response.text}"
                )

            return response.json()

        except requests.exceptions.RequestException as e:
            raise DataSourceAPIError(f"Ahrefs API request failed: {str(e)}")

    def get_competitor_list(self, domain: str, **kwargs) -> List[Dict]:
        """获取竞争对手列表"""
        country = kwargs.get('country', 'US')
        limit = kwargs.get('limit', 50)

        params = {
            "target": domain,
            "country": country,
            "limit": limit,
            "select": "domain,common_keywords,traffic,similarity"
        }

        data = self._make_request("/site-explorer/competitors", params)

        competitors = []
        for item in data.get('competitors', []):
            competitors.append({
                "domain": item['domain'],
                "similarity": item.get('similarity', 0),
                "common_keywords": item.get('common_keywords', 0),
                "estimated_traffic": item.get('traffic', 0),
                "domain_rating": item.get('domain_rating', 0),
                "url_rating": item.get('url_rating', 0)
            })

        return sorted(competitors, key=lambda x: x['similarity'], reverse=True)

    def get_competitor_traffic(self, domain: str, start_date: date, end_date: date, **kwargs) -> Dict:
        """获取竞争对手流量数据"""
        country = kwargs.get('country', 'US')

        params = {
            "target": domain,
            "country": country,
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
            "select": "date,organic_traffic,paid_traffic,keywords,backlinks"
        }

        data = self._make_request("/site-explorer/traffic-history", params)

        daily_trend = []
        total_organic = 0
        total_paid = 0

        for item in data.get('history', []):
            organic = item.get('organic_traffic', 0)
            paid = item.get('paid_traffic', 0)
            total_organic += organic
            total_paid += paid
            daily_trend.append({
                "date": item['date'],
                "visitors": organic + paid,
                "organic_visitors": organic,
                "paid_visitors": paid,
                "keywords": item.get('keywords', 0),
                "backlinks": item.get('backlinks', 0)
            })

        sources = {
            "organic_search": round(total_organic / max(total_organic + total_paid, 1), 2),
            "paid_ad": round(total_paid / max(total_organic + total_paid, 1), 2),
            "direct": 0.15,
            "social_media": 0.1,
            "referral": 0.08
        }

        # 归一化
        total = sum(sources.values())
        for k in sources:
            sources[k] = round(sources[k] / total, 2)

        return {
            "domain": domain,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "total_visitors": total_organic + total_paid,
            "organic_visitors": total_organic,
            "paid_visitors": total_paid,
            "sources": sources,
            "daily_trend": daily_trend,
            "domain_rating": data.get('domain_rating', 0),
            "backlinks_total": data.get('backlinks', 0)
        }

    def get_competitor_top_pages(self, domain: str, **kwargs) -> List[Dict]:
        """获取竞争对手Top页面"""
        country = kwargs.get('country', 'US')
        limit = kwargs.get('limit', 50)

        params = {
            "target": domain,
            "country": country,
            "limit": limit,
            "select": "url,title,traffic,keywords,value"
        }

        data = self._make_request("/site-explorer/top-pages", params)

        pages = []
        for item in data.get('pages', []):
            pages.append({
                "url": item['url'],
                "title": item.get('title', ''),
                "traffic": item['traffic'],
                "traffic_value": item.get('value', 0),
                "keywords_count": item.get('keywords', 0),
                "top_keyword": item.get('top_keyword', ''),
                "avg_position": item.get('avg_position', 0)
            })

        return sorted(pages, key=lambda x: x['traffic'], reverse=True)

    def get_competitor_backlinks(self, domain: str, **kwargs) -> List[Dict]:
        """获取竞争对手反向链接"""
        limit = kwargs.get('limit', 1000)

        params = {
            "target": domain,
            "limit": limit,
            "select": "domain_from,url_from,url_to,anchor,domain_rating,traffic,is_dofollow"
        }

        data = self._make_request("/site-explorer/backlinks", params)

        backlinks = []
        for item in data.get('backlinks', []):
            backlinks.append({
                "source_domain": item['domain_from'],
                "source_url": item['url_from'],
                "target_url": item['url_to'],
                "anchor_text": item.get('anchor', ''),
                "domain_authority": item.get('domain_rating', 0),
                "is_follow": item.get('is_dofollow', True),
                "source_traffic": item.get('traffic', 0),
                "first_seen": item.get('first_seen', None),
                "last_seen": item.get('last_seen', None)
            })

        return backlinks
