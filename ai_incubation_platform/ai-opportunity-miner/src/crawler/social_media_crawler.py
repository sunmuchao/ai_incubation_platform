"""
社交媒体数据采集器
支持微博/Twitter 等社交媒体 API 和模拟数据模式
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
from config.settings import settings
from utils.http_client import http_client
from models.opportunity import SourceType

logger = logging.getLogger(__name__)


class SocialMediaCrawler:
    """社交媒体数据采集器"""

    def __init__(self):
        self.weibo_api_key = settings.weibo_api_key
        self.weibo_api_url = settings.weibo_api_url
        self.twitter_api_key = settings.twitter_api_key
        self.twitter_api_url = settings.twitter_api_url
        self.use_mock = not (self.weibo_api_key or self.twitter_api_key)

    async def search_posts(self, keyword: str, platform: str = "weibo", limit: int = 20) -> List[Dict]:
        """搜索社交媒体帖子"""
        if self.use_mock:
            return self._generate_mock_posts(keyword, platform, limit)

        if platform == "weibo":
            return await self._fetch_weibo_posts(keyword, limit)
        elif platform == "twitter":
            return await self._fetch_twitter_posts(keyword, limit)
        else:
            logger.warning(f"Unsupported platform: {platform}")
            return self._generate_mock_posts(keyword, platform, limit)

    async def _fetch_weibo_posts(self, keyword: str, limit: int) -> List[Dict]:
        """获取微博帖子"""
        headers = {"X-Api-Key": self.weibo_api_key}
        params = {"q": keyword, "count": limit}

        try:
            response = await http_client.async_get(self.weibo_api_url, params=params, headers=headers)
            return self._parse_weibo_response(response)
        except Exception as e:
            logger.error(f"Failed to fetch weibo posts: {str(e)}")
            return self._generate_mock_posts(keyword, "weibo", limit)

    async def _fetch_twitter_posts(self, keyword: str, limit: int) -> List[Dict]:
        """获取 Twitter 帖子"""
        headers = {"Authorization": f"Bearer {self.twitter_api_key}"}
        params = {"query": keyword, "max_results": limit}

        try:
            response = await http_client.async_get(self.twitter_api_url, params=params, headers=headers)
            return self._parse_twitter_response(response)
        except Exception as e:
            logger.error(f"Failed to fetch twitter posts: {str(e)}")
            return self._generate_mock_posts(keyword, "twitter", limit)

    def _parse_weibo_response(self, response: Dict) -> List[Dict]:
        """解析微博 API 响应"""
        posts = response.get("statuses", [])
        parsed = []
        for post in posts:
            try:
                parsed.append({
                    "post_id": post["id"],
                    "content": post.get("text", ""),
                    "author": post.get("user", {}).get("screen_name", ""),
                    "author_id": post.get("user", {}).get("id", ""),
                    "created_at": post.get("created_at", ""),
                    "reposts_count": post.get("reposts_count", 0),
                    "comments_count": post.get("comments_count", 0),
                    "attitudes_count": post.get("attitudes_count", 0),
                    "source": post.get("source", ""),
                    "url": post.get("url", ""),
                    "platform": "weibo",
                    "source_type": SourceType.SOCIAL_MEDIA.value
                })
            except Exception as e:
                logger.warning(f"Failed to parse weibo post: {str(e)}")
                continue
        return parsed

    def _parse_twitter_response(self, response: Dict) -> List[Dict]:
        """解析 Twitter API 响应"""
        tweets = response.get("data", [])
        users = {u["id"]: u for u in response.get("includes", {}).get("users", [])}

        parsed = []
        for tweet in tweets:
            user = users.get(tweet.get("author_id"), {})
            try:
                parsed.append({
                    "post_id": tweet["id"],
                    "content": tweet.get("text", ""),
                    "author": user.get("name", ""),
                    "author_id": user.get("id", ""),
                    "created_at": tweet.get("created_at", ""),
                    "reposts_count": tweet.get("public_metrics", {}).get("retweet_count", 0),
                    "comments_count": tweet.get("public_metrics", {}).get("reply_count", 0),
                    "likes_count": tweet.get("public_metrics", {}).get("like_count", 0),
                    "url": f"https://twitter.com/status/{tweet['id']}",
                    "platform": "twitter",
                    "source_type": SourceType.SOCIAL_MEDIA.value
                })
            except Exception as e:
                logger.warning(f"Failed to parse twitter tweet: {str(e)}")
                continue
        return parsed

    def _generate_mock_posts(self, keyword: str, platform: str, limit: int) -> List[Dict]:
        """生成模拟社交媒体帖子"""
        # 模拟用户
        weibo_users = [
            {"name": "科技日报", "type": "媒体", "followers": 5000000},
            {"name": "36 氪", "type": "媒体", "followers": 3000000},
            {"name": "虎嗅 APP", "type": "媒体", "followers": 2500000},
            {"name": "产品经理小课堂", "type": "KOL", "followers": 800000},
            {"name": "投资人张三", "type": "个人", "followers": 150000},
            {"name": "科技观察者", "type": "媒体", "followers": 1200000},
            {"name": "创业邦", "type": "媒体", "followers": 900000},
            {"name": "AI 前沿", "type": "KOL", "followers": 600000},
        ]

        twitter_users = [
            {"name": "TechCrunch", "type": "Media", "followers": 10000000},
            {"name": "VentureBeat", "type": "Media", "followers": 5000000},
            {"name": "a16z", "type": "VC", "followers": 800000},
            {"name": "Y Combinator", "type": "Accelerator", "followers": 1500000},
        ]

        users = weibo_users if platform == "weibo" else twitter_users

        # 帖子内容模板
        post_templates = [
            "{keyword}行业最新动态：市场规模持续增长，预计未来 3 年 CAGR 超过 30%。#行业分析# #市场分析#",
            "重磅！某知名{keyword}企业完成新一轮融资，估值达到 10 亿美元。#融资# #创业#",
            "专家解读：{keyword}技术如何改变我们的生活方式。来看看有哪些应用场景。#技术解读#",
            "行业报告：2026 年{keyword}行业发展趋势预测，这 5 个方向值得关注。#趋势#",
            "热议：{keyword}产品用户体验对比，你更喜欢哪一款？#产品评测#",
            "政策解读：最新{keyword}产业政策对行业的影响分析。#政策#",
            "技术突破：{keyword}领域取得重大进展，性能提升 50%。#技术创新#",
            "投资风向：VC 纷纷布局{keyword}赛道，这些初创公司值得关注。#投资#",
        ]

        mock_posts = []
        base_date = datetime.now() - timedelta(days=7)

        for i in range(limit):
            user = users[i % len(users)]
            template = post_templates[i % len(post_templates)]

            created_at = base_date + timedelta(hours=i*3)

            # 生成互动数据（帖子越新互动越多）
            recency_factor = 1.0 - (i / limit) * 0.5
            base_engagement = (i % 10 + 1) * 100

            if platform == "weibo":
                post = {
                    "post_id": f"WB-{keyword}-{i:04d}",
                    "content": template.format(keyword=keyword),
                    "author": user["name"],
                    "author_id": f"user_{i}",
                    "created_at": created_at.strftime("%a %b %d %H:%M:%S +0800 %Y"),
                    "reposts_count": int(base_engagement * recency_factor * 0.3),
                    "comments_count": int(base_engagement * recency_factor * 0.5),
                    "attitudes_count": int(base_engagement * recency_factor),
                    "source": f"来自{'微博 weibo' if i % 2 == 0 else 'iPhone 客户端'}",
                    "url": f"https://weibo.com/{i}",
                    "platform": "weibo",
                    "source_type": SourceType.SOCIAL_MEDIA.value,
                    "sentiment": "positive" if i % 5 != 4 else "negative"
                }
            else:
                post = {
                    "post_id": f"TW-{keyword}-{i:04d}",
                    "content": template.format(keyword=keyword),
                    "author": user["name"],
                    "author_id": f"user_{i}",
                    "created_at": created_at.isoformat() + "Z",
                    "reposts_count": int(base_engagement * recency_factor * 0.4),
                    "comments_count": int(base_engagement * recency_factor * 0.3),
                    "likes_count": int(base_engagement * recency_factor),
                    "url": f"https://twitter.com/status/{i}",
                    "platform": "twitter",
                    "source_type": SourceType.SOCIAL_MEDIA.value,
                    "sentiment": "positive" if i % 5 != 4 else "negative"
                }

            mock_posts.append(post)

        return mock_posts

    async def get_hot_topics(self, platform: str = "weibo") -> List[Dict]:
        """获取热门话题"""
        if self.use_mock:
            return self._generate_mock_hot_topics(platform)

        # 实际实现需要调用平台的热榜 API
        return self._generate_mock_hot_topics(platform)

    def _generate_mock_hot_topics(self, platform: str) -> List[Dict]:
        """生成模拟热门话题"""
        mock_topics = [
            {"rank": 1, "topic": "#人工智能新突破#", "heat": 5000000, "discussion_count": 150000},
            {"rank": 2, "topic": "#科技创新驱动发展#", "heat": 4500000, "discussion_count": 120000},
            {"rank": 3, "topic": "#数字经济时代#", "heat": 4000000, "discussion_count": 100000},
            {"rank": 4, "topic": "#智能制造 2026#", "heat": 3500000, "discussion_count": 80000},
            {"rank": 5, "topic": "#绿色能源转型#", "heat": 3000000, "discussion_count": 70000},
            {"rank": 6, "topic": "#医疗健康创新#", "heat": 2800000, "discussion_count": 65000},
            {"rank": 7, "topic": "#新能源汽车爆发#", "heat": 2500000, "discussion_count": 60000},
            {"rank": 8, "topic": "#元宇宙应用落地#", "heat": 2200000, "discussion_count": 55000},
            {"rank": 9, "topic": "#跨境电商新政#", "heat": 2000000, "discussion_count": 50000},
            {"rank": 10, "topic": "#区块链技术进展#", "heat": 1800000, "discussion_count": 45000},
        ]

        for topic in mock_topics:
            topic["platform"] = platform
            topic["trend"] = "up" if topic["rank"] <= 5 else ("down" if topic["rank"] >= 8 else "stable")

        return mock_topics

    async def analyze_sentiment(self, keyword: str, days: int = 7) -> Dict:
        """分析社交媒体情感趋势"""
        posts = await self.search_posts(keyword, "weibo", 100)

        # 简单情感分析（模拟）
        positive_count = sum(1 for p in posts if p.get("sentiment") == "positive")
        negative_count = sum(1 for p in posts if p.get("sentiment") == "negative")
        neutral_count = len(posts) - positive_count - negative_count

        total = len(posts) or 1

        return {
            "keyword": keyword,
            "period_days": days,
            "total_posts": total,
            "sentiment_distribution": {
                "positive": {"count": positive_count, "percentage": positive_count / total * 100},
                "negative": {"count": negative_count, "percentage": negative_count / total * 100},
                "neutral": {"count": neutral_count, "percentage": neutral_count / total * 100}
            },
            "overall_sentiment": "positive" if positive_count > negative_count else "negative" if negative_count > positive_count else "neutral",
            "engagement_stats": {
                "total_reposts": sum(p.get("reposts_count", 0) for p in posts),
                "total_comments": sum(p.get("comments_count", 0) for p in posts),
                "total_likes": sum(p.get("attitudes_count", 0) or p.get("likes_count", 0) for p in posts)
            }
        }


social_media_crawler = SocialMediaCrawler()
