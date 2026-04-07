"""
Mock数据源
用于开发测试和演示，返回模拟数据
"""
from typing import List, Dict, Optional
from datetime import date, timedelta
import random
from ..base import (
    BaseKeywordDataSource,
    BaseCompetitorDataSource,
    DataSourceConfigError
)


class MockKeywordProvider(BaseKeywordDataSource):
    """Mock关键词数据源"""

    source_name = "mock"
    supported_regions = ["CN", "US", "JP", "EU"]
    supported_languages = ["zh-CN", "en-US", "ja-JP"]

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        # 模拟数据池
        self._keyword_pool = [
            "SEO优化", "内容营销", "流量增长", "用户增长", "转化率优化",
            "关键词排名", "网站优化", "内容生成", "AI写作", "智能客服",
            "数据分析", "数据可视化", "商业智能", "营销自动化", "客户关系管理",
            "电商运营", "社交媒体营销", "搜索引擎营销", "品牌推广", "用户体验"
        ]
        self._domain_keywords = {}

    def get_keyword_suggestions(self, seed_keywords: List[str], **kwargs) -> List[Dict]:
        """获取关键词建议"""
        suggestions = []
        used_keywords = set()

        for seed in seed_keywords:
            # 生成相关关键词
            related_formats = [
                f"{seed} 教程", f"{seed} 怎么用", f"{seed} 推荐", f"{seed} 评测",
                f"{seed} 2024", f"最好的 {seed}", f"{seed} 购买指南", f"{seed} 优缺点",
                f"{seed} 技巧", f"{seed} 最佳实践", f"{seed} 案例", f"{seed} 解决方案"
            ]

            for i, fmt in enumerate(related_formats):
                kw = fmt.format(seed=seed)
                if kw not in used_keywords:
                    used_keywords.add(kw)
                    search_volume = random.randint(100, 10000)
                    competition = random.uniform(0.1, 0.9)
                    difficulty = random.uniform(20, 90)
                    relevance = random.uniform(0.6, 1.0)

                    suggestions.append({
                        "keyword": kw,
                        "search_volume": search_volume,
                        "competition": round(competition, 2),
                        "difficulty": round(difficulty, 1),
                        "relevance": round(relevance, 2),
                        "cpc": round(random.uniform(0.5, 20.0), 2),
                        "trend": [
                            random.randint(int(search_volume * 0.7), int(search_volume * 1.3))
                            for _ in range(12)
                        ]
                    })

        # 按搜索量排序
        suggestions.sort(key=lambda x: x["search_volume"], reverse=True)
        return suggestions[:20]

    def get_keyword_metrics(self, keywords: List[str], **kwargs) -> List[Dict]:
        """获取关键词详细指标"""
        metrics = []
        for kw in keywords:
            search_volume = random.randint(100, 10000)
            metrics.append({
                "keyword": kw,
                "search_volume": search_volume,
                "competition": round(random.uniform(0.1, 0.9), 2),
                "difficulty": round(random.uniform(20, 90), 1),
                "cpc": round(random.uniform(0.5, 20.0), 2),
                "trend_30d": round(random.uniform(-0.3, 0.5), 2),
                "trend_90d": round(random.uniform(-0.2, 0.6), 2),
                "serp_features": random.sample(
                    ["featured_snippet", "people_also_ask", "image_pack", "video", "local_pack"],
                    k=random.randint(0, 3)
                )
            })
        return metrics

    def get_competitor_keywords(self, domain: str, **kwargs) -> List[Dict]:
        """获取竞争对手排名关键词"""
        if domain not in self._domain_keywords:
            # 为域名生成随机关键词
            keyword_count = random.randint(50, 500)
            self._domain_keywords[domain] = random.sample(self._keyword_pool, min(keyword_count, len(self._keyword_pool)))

        keywords = []
        for kw in self._domain_keywords[domain]:
            position = random.randint(1, 50)
            keywords.append({
                "keyword": kw,
                "position": position,
                "search_volume": random.randint(100, 10000),
                "traffic_share": round(random.uniform(0.01, 0.2), 2),
                "url": f"/{kw.replace(' ', '-')}",
                "position_change": random.randint(-10, 10)
            })

        return sorted(keywords, key=lambda x: x["search_volume"], reverse=True)[:100]

    def get_keyword_ranking(self, domain: str, keywords: List[str], **kwargs) -> List[Dict]:
        """获取域名在特定关键词上的排名"""
        rankings = []
        for kw in keywords:
            base_pos = random.randint(1, 30)
            rankings.append({
                "keyword": kw,
                "domain": domain,
                "current_position": base_pos,
                "previous_position": base_pos + random.randint(-5, 5),
                "best_position": random.randint(1, base_pos),
                "url": f"/{kw.replace(' ', '-')}",
                "search_volume": random.randint(100, 10000),
                "ctr": round(random.uniform(0.01, 0.3), 2),
                "last_updated": date.today().isoformat()
            })
        return rankings


class MockCompetitorProvider(BaseCompetitorDataSource):
    """Mock竞品数据源"""

    source_name = "mock"

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._competitor_cache = {}

    def get_competitor_list(self, domain: str, **kwargs) -> List[Dict]:
        """获取竞争对手列表"""
        if domain in self._competitor_cache:
            return self._competitor_cache[domain]

        # 生成模拟竞争对手
        competitors = []
        competitor_domains = [
            f"competitor{i}.com" for i in range(1, random.randint(5, 15))
        ]

        for comp_domain in competitor_domains:
            traffic = random.randint(1000, 100000)
            competitors.append({
                "domain": comp_domain,
                "name": f"Competitor {comp_domain.split('.')[0].capitalize()}",
                "similarity": round(random.uniform(0.3, 0.95), 2),
                "estimated_traffic": traffic,
                "traffic_rank": random.randint(1000, 100000),
                "market_share": round(traffic / 1000000, 4),
                "main_products": random.sample(["SaaS", "E-commerce", "Content", "Services"], k=2),
                "strengths": random.sample(
                    ["SEO", "Social Media", "Paid Ads", "Content Marketing", "Brand"],
                    k=random.randint(1, 3)
                )
            })

        self._competitor_cache[domain] = sorted(
            competitors, key=lambda x: x["similarity"], reverse=True
        )
        return self._competitor_cache[domain]

    def get_competitor_traffic(self, domain: str, start_date: date, end_date: date, **kwargs) -> Dict:
        """获取竞争对手流量数据"""
        days_diff = (end_date - start_date).days + 1
        base_traffic = random.randint(5000, 50000)

        # 生成每日流量
        daily_traffic = []
        current_date = start_date
        for _ in range(days_diff):
            daily = base_traffic * random.uniform(0.8, 1.2)
            daily_traffic.append({
                "date": current_date.isoformat(),
                "visitors": int(daily),
                "page_views": int(daily * random.uniform(1.5, 3.5)),
                "bounce_rate": round(random.uniform(0.3, 0.7), 2),
                "conversion_rate": round(random.uniform(0.01, 0.08), 3)
            })
            current_date += timedelta(days=1)

        # 流量来源分布
        sources = {
            "organic_search": round(random.uniform(0.3, 0.6), 2),
            "direct": round(random.uniform(0.1, 0.25), 2),
            "social_media": round(random.uniform(0.1, 0.2), 2),
            "referral": round(random.uniform(0.05, 0.15), 2),
            "paid_ad": round(random.uniform(0.05, 0.2), 2),
            "email": round(random.uniform(0.02, 0.1), 2)
        }

        # 归一化
        total = sum(sources.values())
        for k in sources:
            sources[k] = round(sources[k] / total, 2)

        return {
            "domain": domain,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "total_visitors": sum(d["visitors"] for d in daily_traffic),
            "total_page_views": sum(d["page_views"] for d in daily_traffic),
            "avg_bounce_rate": round(sum(d["bounce_rate"] for d in daily_traffic) / len(daily_traffic), 2),
            "avg_conversion_rate": round(sum(d["conversion_rate"] for d in daily_traffic) / len(daily_traffic), 3),
            "sources": sources,
            "daily_trend": daily_traffic,
            "year_over_year_growth": round(random.uniform(-0.2, 0.8), 2)
        }

    def get_competitor_top_pages(self, domain: str, **kwargs) -> List[Dict]:
        """获取竞争对手Top页面"""
        pages = []
        page_count = random.randint(10, 50)

        for i in range(page_count):
            traffic = random.randint(100, 10000)
            pages.append({
                "url": f"/page-{i}",
                "title": f"Page {i} Title - {domain}",
                "traffic": traffic,
                "traffic_share": round(traffic / 100000, 4),
                "keywords_count": random.randint(5, 50),
                "top_keyword": f"top keyword for page {i}",
                "avg_position": round(random.uniform(1, 30), 1),
                "published_at": (date.today() - timedelta(days=random.randint(30, 365))).isoformat()
            })

        return sorted(pages, key=lambda x: x["traffic"], reverse=True)[:20]

    def get_competitor_backlinks(self, domain: str, **kwargs) -> List[Dict]:
        """获取竞争对手反向链接"""
        backlinks = []
        backlink_count = random.randint(100, 1000)

        for i in range(min(backlink_count, 100)):
            backlinks.append({
                "source_domain": f"referrer-site-{i}.com",
                "source_url": f"/link/{i}",
                "target_url": f"/target/page/{i}",
                "anchor_text": f"anchor text {i}",
                "domain_authority": random.randint(10, 100),
                "is_follow": random.choice([True, False]),
                "first_seen": (date.today() - timedelta(days=random.randint(30, 730))).isoformat(),
                "last_seen": date.today().isoformat()
            })

        return backlinks
