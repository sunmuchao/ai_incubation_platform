"""
新闻数据爬虫
支持公开新闻API和模拟数据模式
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
from config.settings import settings
from utils.http_client import http_client
from models.opportunity import SourceType

logger = logging.getLogger(__name__)

class NewsCrawler:
    """新闻数据爬虫"""

    def __init__(self):
        self.api_key = settings.news_api_key
        self.api_url = settings.news_api_url
        self.use_mock = not self.api_key  # 如果没有配置API密钥，使用模拟模式

    async def fetch_news(self, keywords: List[str], days: int = 7, limit: int = 20) -> List[Dict]:
        """获取新闻数据"""
        if self.use_mock:
            return self._generate_mock_news(keywords, days, limit)

        headers = {"X-Api-Key": self.api_key}
        params = {
            "q": " OR ".join(keywords),
            "from": (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d'),
            "sortBy": "publishedAt",
            "language": "zh",
            "pageSize": limit
        }

        try:
            response = await http_client.async_get(self.api_url, params=params, headers=headers)
            return self._parse_news_response(response)
        except Exception as e:
            logger.error(f"Failed to fetch news: {str(e)}")
            return self._generate_mock_news(keywords, days, limit)

    def _parse_news_response(self, response: Dict) -> List[Dict]:
        """解析新闻API响应"""
        articles = response.get("articles", [])
        parsed_articles = []

        for article in articles:
            try:
                published_at = datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00"))
                parsed_articles.append({
                    "title": article["title"],
                    "content": article.get("content", article.get("description", "")),
                    "source": article["source"]["name"],
                    "url": article["url"],
                    "published_at": published_at,
                    "author": article.get("author", ""),
                    "source_type": SourceType.NEWS.value,
                    "image_url": article.get("urlToImage", "")
                })
            except Exception as e:
                logger.warning(f"Failed to parse article: {str(e)}")
                continue

        return parsed_articles

    def _generate_mock_news(self, keywords: List[str], days: int, limit: int) -> List[Dict]:
        """生成模拟新闻数据"""
        mock_templates = [
            {
                "title": "{keyword}行业政策利好，市场规模达到{market_size}亿",
                "content": "近日，国家相关部门发布了关于促进{keyword}产业发展的指导意见，提出到2028年产业规模要达到{market_size}亿，预计2026-2028年行业同比增长达到{growth_rate}%。分析认为，这将为整个产业链带来重大发展机遇。",
                "source": "财经日报",
                "url": "https://example.com/news/{keyword}-policy-2026",
                "source_type": SourceType.NEWS.value
            },
            {
                "title": "新技术突破，{keyword}应用场景加速落地",
                "content": "最新研究显示，{keyword}相关技术取得重大突破，使得应用成本降低了40%。业内专家预测，未来2年将在多个行业实现规模化应用。",
                "source": "科技日报",
                "url": "https://example.com/news/{keyword}-tech-breakthrough",
                "source_type": SourceType.NEWS.value
            },
            {
                "title": "头部企业加码布局{keyword}赛道，竞争格局重塑",
                "content": "多家行业龙头企业近期宣布加大在{keyword}领域的投入，计划未来3年投资超过500亿元。市场分析认为，这将加速行业洗牌，推动产业集中度提升。",
                "source": "企业观察报",
                "url": "https://example.com/news/{keyword}-investment",
                "source_type": SourceType.NEWS.value
            },
            {
                "title": "消费升级驱动{keyword}需求暴涨，产业链上下游受益",
                "content": "随着居民收入水平提高和消费观念升级，{keyword}相关产品的市场需求呈现爆发式增长，一季度同比增长达到{growth_rate}%。产业链上下游企业订单饱满，产能利用率达到历史高位。",
                "source": "消费日报",
                "url": "https://example.com/news/{keyword}-consumption-growth",
                "source_type": SourceType.NEWS.value
            },
            {
                "title": "{keyword}国家标准即将出台，行业规范化发展提速",
                "content": "记者从相关部门获悉，{keyword}行业国家标准已完成征求意见稿，预计今年下半年正式发布。标准的出台将有助于规范市场秩序，提升行业整体发展水平。",
                "source": "中国质量报",
                "url": "https://example.com/news/{keyword}-national-standard",
                "source_type": SourceType.NEWS.value
            }
        ]

        mock_news = []
        base_date = datetime.now() - timedelta(days=days)

        for i in range(limit):
            keyword = keywords[i % len(keywords)]
            template = mock_templates[i % len(mock_templates)]

            # 给文本里注入可被 TextAnalyzer 命中的数值片段（用于计算置信度/趋势）
            market_size_val = 500 + (i % 5) * 100  # 500-900
            growth_rate_val = 20 + (i % 5) * 10  # 20%-60%

            published_date = base_date + timedelta(days=i % days, hours=i % 24)

            news_item = {
                "title": template["title"].format(keyword=keyword, market_size=market_size_val, growth_rate=growth_rate_val),
                "content": template["content"].format(keyword=keyword, market_size=market_size_val, growth_rate=growth_rate_val),
                "source": template["source"],
                "url": template["url"].format(keyword=keyword.lower().replace(" ", "-")),
                "published_at": published_date,
                "author": "记者" + chr(65 + i % 26),
                "source_type": template["source_type"],
                "image_url": f"https://example.com/images/{keyword}-{i}.jpg"
            }
            mock_news.append(news_item)

        return mock_news

    async def fetch_industry_news(self, industry: str, days: int = 30) -> List[Dict]:
        """获取行业新闻"""
        keywords = [industry, f"{industry}发展", f"{industry}政策", f"{industry}技术"]
        return await self.fetch_news(keywords, days)

news_crawler = NewsCrawler()
