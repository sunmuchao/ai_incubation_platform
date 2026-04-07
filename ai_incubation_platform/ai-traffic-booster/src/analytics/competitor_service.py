"""
竞争情报与竞品分析服务 (P4)
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, date, timedelta
import random
import hashlib
import uuid
from collections import defaultdict

from schemas.competitor import (
    Competitor,
    CompetitorCreateRequest,
    CompetitorMetrics,
    CompetitorTrafficSources,
    CompetitorKeywords,
    CompetitorTopPages,
    CompetitorBacklinks,
    CompetitorAnalysisRequest,
    CompetitorComparisonResponse,
    KeywordGapAnalysis,
    ContentGapAnalysis,
    BacklinkGapAnalysis,
    MarketPositionAnalysis,
    CompetitorAlert,
    CompetitorTrackingRequest,
    MarketTrend,
    IndustryBenchmark,
    SWOTAnalysis
)


class CompetitorService:
    """竞争情报服务"""

    def __init__(self):
        # 模拟竞品数据库
        self._competitors: Dict[str, Competitor] = {}
        self._alerts: Dict[str, CompetitorAlert] = {}
        self._tracking_configs: Dict[str, CompetitorTrackingRequest] = {}

        # 模拟竞品域名池
        self._sample_competitor_domains = [
            "competitor1.com",
            "rival-site.com",
            "industry-leader.com",
            "market-challenger.com",
            "emerging-player.com",
            "niche-expert.com",
            "global-giant.com",
            "local-winner.com"
        ]

        # 模拟行业基准数据
        self._industry_benchmarks = {
            "ecommerce": {
                "bounce_rate": {"p25": 0.35, "p50": 0.45, "p75": 0.55, "p90": 0.65},
                "conversion_rate": {"p25": 0.015, "p50": 0.025, "p75": 0.035, "p90": 0.05},
                "avg_session_duration": {"p25": 120, "p50": 180, "p75": 240, "p90": 320},
                "pages_per_session": {"p25": 2.5, "p50": 3.5, "p75": 4.5, "p90": 6.0}
            },
            "saas": {
                "bounce_rate": {"p25": 0.25, "p50": 0.35, "p75": 0.45, "p90": 0.55},
                "conversion_rate": {"p25": 0.02, "p50": 0.04, "p75": 0.06, "p90": 0.1},
                "avg_session_duration": {"p25": 180, "p50": 300, "p75": 420, "p90": 600},
                "pages_per_session": {"p25": 3.0, "p50": 4.5, "p75": 6.0, "p90": 8.0}
            },
            "content": {
                "bounce_rate": {"p25": 0.45, "p50": 0.55, "p75": 0.65, "p90": 0.75},
                "conversion_rate": {"p25": 0.005, "p50": 0.01, "p75": 0.02, "p90": 0.03},
                "avg_session_duration": {"p25": 60, "p50": 120, "p75": 180, "p90": 240},
                "pages_per_session": {"p25": 1.5, "p50": 2.5, "p75": 3.5, "p90": 5.0}
            }
        }

    def add_competitor(self, request: CompetitorCreateRequest) -> Competitor:
        """添加竞品"""
        competitor_id = str(uuid.uuid4())[:8]
        competitor = Competitor(
            competitor_id=competitor_id,
            domain=request.domain,
            name=request.name or request.domain.split('.')[0],
            description=request.description,
            industry=request.industry,
            tags=request.tags or [],
            added_at=datetime.now()
        )
        self._competitors[competitor_id] = competitor
        return competitor

    def list_competitors(self) -> List[Competitor]:
        """获取竞品列表"""
        return list(self._competitors.values())

    def remove_competitor(self, competitor_id: str) -> bool:
        """移除竞品"""
        if competitor_id in self._competitors:
            del self._competitors[competitor_id]
            return True
        return False

    def get_competitor_metrics(self, domain: str) -> CompetitorMetrics:
        """获取竞品流量指标"""
        # 使用域名生成确定性随机数
        seed = int(hashlib.sha256(domain.encode()).hexdigest()[:8], 16)
        random.seed(seed)

        return CompetitorMetrics(
            domain=domain,
            total_visits=random.randint(100000, 10000000),
            unique_visitors=random.randint(50000, 5000000),
            avg_visit_duration=random.uniform(60, 600),
            pages_per_visit=random.uniform(1.5, 8.0),
            bounce_rate=random.uniform(0.25, 0.65),
            traffic_rank=random.randint(1000, 100000),
            country_rank=random.randint(10, 5000),
            rank_change=random.uniform(-0.3, 0.5)
        )

    def get_competitor_traffic_sources(self, domain: str) -> CompetitorTrafficSources:
        """获取竞品流量来源分布"""
        seed = int(hashlib.sha256(f"{domain}_traffic".encode()).hexdigest()[:8], 16)
        random.seed(seed)

        # 生成并归一化
        direct = random.uniform(0.1, 0.4)
        referral = random.uniform(0.05, 0.2)
        search = random.uniform(0.2, 0.5)
        social = random.uniform(0.05, 0.2)
        mail = random.uniform(0.01, 0.1)
        ads = random.uniform(0.05, 0.2)
        display_ads = random.uniform(0.01, 0.1)

        total = direct + referral + search + social + mail + ads + display_ads

        return CompetitorTrafficSources(
            domain=domain,
            direct=round(direct / total, 3),
            referral=round(referral / total, 3),
            search=round(search / total, 3),
            social=round(social / total, 3),
            mail=round(mail / total, 3),
            ads=round(ads / total, 3),
            display_ads=round(display_ads / total, 3)
        )

    def get_competitor_keywords(self, domain: str, limit: int = 20) -> List[CompetitorKeywords]:
        """获取竞品关键词列表"""
        seed = int(hashlib.sha256(f"{domain}_keywords".encode()).hexdigest()[:8], 16)
        random.seed(seed)

        sample_keywords = [
            "SEO 优化", "内容营销", "流量增长", "AI 写作", "关键词工具",
            "网站分析", "竞品分析", "市场研究", "数字营销", "社交媒体",
            "转化率优化", "用户体验", "landing page", "A/B 测试", "营销自动化",
            "邮件营销", "付费广告", "Google Ads", "Facebook 广告", "网红营销"
        ]

        keywords = []
        for kw in random.sample(sample_keywords, min(limit, len(sample_keywords))):
            keywords.append(CompetitorKeywords(
                domain=domain,
                keyword=kw,
                position=random.randint(1, 50),
                search_volume=random.randint(100, 100000),
                cpc=round(random.uniform(0.5, 50.0), 2),
                competition=random.uniform(0.3, 1.0),
                traffic_share=random.uniform(0.001, 0.05),
                position_change=random.randint(-5, 5)
            ))

        return sorted(keywords, key=lambda x: x.traffic_share, reverse=True)

    def get_competitor_top_pages(self, domain: str, limit: int = 10) -> List[CompetitorTopPages]:
        """获取竞品热门页面"""
        seed = int(hashlib.sha256(f"{domain}_pages".encode()).hexdigest()[:8], 16)
        random.seed(seed)

        sample_pages = [
            {"url": "/", "title": "首页"},
            {"url": "/products", "title": "产品页面"},
            {"url": "/blog", "title": "博客首页"},
            {"url": "/blog/ultimate-guide", "title": "终极指南"},
            {"url": "/pricing", "title": "价格页面"},
            {"url": "/features", "title": "功能介绍"},
            {"url": "/about", "title": "关于我们"},
            {"url": "/contact", "title": "联系我们"},
            {"url": "/resources", "title": "资源中心"},
            {"url": "/case-studies", "title": "案例研究"}
        ]

        pages = []
        for page in random.sample(sample_pages, min(limit, len(sample_pages))):
            pages.append(CompetitorTopPages(
                domain=domain,
                url=f"https://{domain}{page['url']}",
                title=page['title'],
                visits=random.randint(1000, 500000),
                traffic_share=random.uniform(0.01, 0.3),
                avg_time_on_page=random.uniform(30, 300),
                bounce_rate=random.uniform(0.2, 0.7),
                top_keyword=random.choice(["SEO", "营销", "工具", "指南", "教程"])
            ))

        return sorted(pages, key=lambda x: page.visits if (page := pages[pages.index(p)]) else 0, reverse=True)[:limit]

    def analyze_competitors(self, request: CompetitorAnalysisRequest) -> CompetitorComparisonResponse:
        """竞品对比分析"""
        your_domain = request.domains[0] if request.domains else "yoursite.com"
        competitor_domains = request.domains[1:] if len(request.domains) > 1 else self._sample_competitor_domains[:3]

        # 获取各竞品指标
        competitors_metrics = []
        for domain in competitor_domains:
            competitors_metrics.append(self.get_competitor_metrics(domain))

        # 生成对比摘要
        your_metrics = self.get_competitor_metrics(your_domain)
        avg_competitor_visits = sum(c.total_visits for c in competitors_metrics) / len(competitors_metrics)

        comparison_summary = {
            "your_visits": your_metrics.total_visits,
            "avg_competitor_visits": int(avg_competitor_visits),
            "visit_gap": your_metrics.total_visits - int(avg_competitor_visits),
            "visit_gap_percentage": round((your_metrics.total_visits - avg_competitor_visits) / avg_competitor_visits * 100, 2),
            "your_rank": your_metrics.traffic_rank,
            "best_competitor_rank": min(c.traffic_rank for c in competitors_metrics)
        }

        # 差距分析
        gap_analysis = []
        if your_metrics.bounce_rate > avg_competitor_visits * 0.00001:
            gap_analysis.append({
                "metric": "bounce_rate",
                "your_value": your_metrics.bounce_rate,
                "competitor_avg": 0.45,
                "gap": "high",
                "recommendation": "优化页面加载速度和内容相关性"
            })

        # 机会和威胁
        opportunities = [
            "竞品 A 在移动端流量占比较低，可加强移动优化",
            "某些长尾关键词竞品尚未覆盖",
            "社交媒体渠道存在增长空间"
        ]

        threats = [
            "竞品 B 近期流量增长迅速",
            "主要竞品在核心关键词排名领先",
            "竞品 C 获得了大量高质量外链"
        ]

        return CompetitorComparisonResponse(
            your_domain=your_domain,
            competitors=competitors_metrics,
            comparison_summary=comparison_summary,
            gap_analysis=gap_analysis,
            opportunities=opportunities,
            threats=threats
        )

    def analyze_keyword_gap(self, your_domain: str, competitor_domains: List[str]) -> KeywordGapAnalysis:
        """关键词差距分析"""
        # 获取你的关键词
        your_keywords = self.get_competitor_keywords(your_domain, limit=15)

        # 获取竞品关键词
        all_competitor_keywords = []
        for domain in competitor_domains:
            all_competitor_keywords.extend(self.get_competitor_keywords(domain, limit=10))

        # 去重
        your_kw_set = {k.keyword for k in your_keywords}
        competitor_kw_set = {k.keyword for k in all_competitor_keywords}

        shared = [k for k in your_keywords if k.keyword in competitor_kw_set]
        your_unique = [k for k in your_keywords if k.keyword not in competitor_kw_set]
        competitor_unique = [k for k in all_competitor_keywords if k.keyword not in your_kw_set]

        # 去重 competitor_unique
        seen = set()
        unique_competitor = []
        for k in competitor_unique:
            if k.keyword not in seen:
                seen.add(k.keyword)
                unique_competitor.append(k)

        # 缺失机会（竞品有但你没有的高价值词）
        missing_opportunities = [
            k for k in unique_competitor
            if k.search_volume > 1000 and k.competition < 0.7
        ][:10]

        return KeywordGapAnalysis(
            your_keywords=[{"keyword": k.keyword, "position": k.position, "volume": k.search_volume} for k in your_keywords],
            competitor_keywords=[{"keyword": k.keyword, "domain": k.domain, "position": k.position} for k in all_competitor_keywords[:20]],
            shared_keywords=[{"keyword": k.keyword, "your_position": k.position} for k in shared],
            your_unique=[{"keyword": k.keyword, "position": k.position} for k in your_unique],
            competitor_unique=[{"keyword": k.keyword, "domain": k.domain} for k in unique_competitor[:10]],
            missing_opportunities=[{"keyword": k.keyword, "volume": k.search_volume, "competition": k.competition} for k in missing_opportunities]
        )

    def analyze_content_gap(self, your_domain: str, competitor_domains: List[str]) -> ContentGapAnalysis:
        """内容差距分析"""
        # 模拟你的热门内容
        your_top_content = [
            {"url": f"https://{your_domain}/blog/seo-guide", "title": "SEO 完全指南", "visits": 5000},
            {"url": f"https://{your_domain}/blog/content-tips", "title": "内容优化技巧", "visits": 3000},
            {"url": f"https://{your_domain}/products/ai-tool", "title": "AI 工具产品页", "visits": 2000}
        ]

        # 模拟竞品热门内容
        competitor_content = []
        for domain in competitor_domains[:3]:
            competitor_content.extend([
                {"url": f"https://{domain}/blog/marketing-guide", "title": "营销完全指南", "visits": random.randint(3000, 10000)},
                {"url": f"https://{domain}/resources/templates", "title": "免费模板下载", "visits": random.randint(2000, 8000)},
                {"url": f"https://{domain}/case-studies/success", "title": "成功案例研究", "visits": random.randint(1000, 5000)}
            ])

        # 内容机会主题
        content_opportunities = [
            "视频教程系列（竞品普遍缺少）",
            "互动式工具和计算器",
            "行业报告和白皮书",
            "播客内容",
            "信息图表和可视化内容"
        ]

        # 内容形式差距
        content_format_gaps = [
            {"format": "视频", "your_count": 2, "competitor_avg": 15, "gap": "high"},
            {"format": "信息图", "your_count": 5, "competitor_avg": 20, "gap": "medium"},
            {"format": "案例研究", "your_count": 3, "competitor_avg": 10, "gap": "medium"},
            {"format": "白皮书", "your_count": 1, "competitor_avg": 5, "gap": "low"}
        ]

        return ContentGapAnalysis(
            your_top_content=your_top_content,
            competitor_top_content=competitor_content[:10],
            content_opportunities=content_opportunities,
            content_format_gaps=content_format_gaps
        )

    def analyze_backlink_gap(self, your_domain: str, competitor_domains: List[str]) -> BacklinkGapAnalysis:
        """反向链接差距分析"""
        seed = int(hashlib.sha256(your_domain.encode()).hexdigest()[:8], 16)
        random.seed(seed)

        your_count = random.randint(100, 5000)
        competitor_count = random.randint(500, 20000)

        # 模拟共同引用域名
        shared_domains = ["github.com", "medium.com", "linkedin.com", "twitter.com"]

        # 模拟竞品独有的引用域名
        competitor_exclusive = [
            "forbes.com", "techcrunch.com", "searchengineland.com",
            "moz.com", "ahrefs.com", "semrush.com"
        ]

        # 外链建设机会
        link_opportunities = [
            {"domain": "industry-blog.com", "authority": 65, "competitor_links": 3, "opportunity_type": "guest_post"},
            {"domain": "news-site.com", "authority": 80, "competitor_links": 5, "opportunity_type": "pr"},
            {"domain": "resource-directory.com", "authority": 45, "competitor_links": 8, "opportunity_type": "directory"}
        ]

        return BacklinkGapAnalysis(
            your_backlinks_count=your_count,
            competitor_backlinks_count=competitor_count,
            shared_domains=shared_domains,
            competitor_exclusive_domains=competitor_exclusive,
            link_building_opportunities=link_opportunities
        )

    def get_market_position(self, your_domain: str, competitor_domains: List[str]) -> MarketPositionAnalysis:
        """市场定位分析"""
        all_domains = [your_domain] + competitor_domains

        # 生成市场份额
        total_visits = sum(int(hashlib.sha256(d.encode()).hexdigest()[:8], 16) % 1000000 + 100000 for d in all_domains)
        market_share = {}
        for d in all_domains:
            visits = int(hashlib.sha256(d.encode()).hexdigest()[:8], 16) % 1000000 + 100000
            market_share[d] = round(visits / total_visits, 3)

        # 增长趋势
        growth_trend = {
            d: round(random.uniform(-0.2, 0.5), 3) for d in all_domains
        }

        # 受众重叠度
        audience_overlap = {
            f"{your_domain} vs {d}": round(random.uniform(0.1, 0.6), 2)
            for d in competitor_domains
        }

        # 定位图谱
        positioning_map = [
            {"domain": d, "price_level": random.uniform(1, 5), "quality_score": random.uniform(1, 5)}
            for d in all_domains
        ]

        return MarketPositionAnalysis(
            market_share=market_share,
            growth_trend=growth_trend,
            audience_overlap=audience_overlap,
            positioning_map=positioning_map
        )

    def get_industry_benchmarks(self, industry: str = "saas") -> List[IndustryBenchmark]:
        """获取行业基准数据"""
        if industry not in self._industry_benchmarks:
            industry = "saas"  # 默认

        benchmarks_data = self._industry_benchmarks[industry]
        benchmarks = []

        for metric_name, values in benchmarks_data.items():
            benchmarks.append(IndustryBenchmark(
                industry=industry,
                metric_name=metric_name,
                percentile_25=values["p25"],
                percentile_50=values["p50"],
                percentile_75=values["p75"],
                percentile_90=values["p90"],
                sample_size=random.randint(100, 1000)
            ))

        return benchmarks

    def generate_swot_analysis(self, your_domain: str, competitor_domains: List[str]) -> SWOTAnalysis:
        """生成 SWOT 分析"""
        # 获取对比数据
        comparison = self.analyze_competitors(CompetitorAnalysisRequest(
            domains=[your_domain] + competitor_domains
        ))

        strengths = [
            "产品在特定细分市场有较高知名度",
            "用户留存率高于行业平均水平",
            "内容质量获得用户认可"
        ]

        weaknesses = [
            "品牌知名度相比头部竞品较低",
            "营销预算有限导致获客成本高",
            "技术团队规模较小"
        ]

        opportunities = [
            "新兴市场的流量红利",
            "AI 技术带来的效率提升机会",
            "合作伙伴渠道拓展"
        ]

        threats = [
            "头部竞品加大市场投入",
            "新进入者带来的价格战风险",
            "搜索算法更新影响自然流量"
        ]

        strategic_recommendations = [
            "聚焦细分市场，建立差异化优势",
            "加大内容营销投入，降低获客成本",
            "探索 AI 驱动的个性化用户体验",
            "建立战略合作伙伴关系，拓展获客渠道"
        ]

        return SWOTAnalysis(
            strengths=strengths,
            weaknesses=weaknesses,
            opportunities=opportunities,
            threats=threats,
            strategic_recommendations=strategic_recommendations
        )

    def create_alert(self, competitor_domain: str, alert_type: str, severity: str = "medium") -> CompetitorAlert:
        """创建竞品告警"""
        alert_id = str(uuid.uuid4())[:8]

        alert_messages = {
            "ranking_change": "竞品关键词排名显著变化",
            "traffic_spike": "竞品流量异常增长",
            "new_backlink": "竞品获得重要外链",
            "content_publish": "竞品发布新内容",
            "price_change": "竞品价格调整"
        }

        alert = CompetitorAlert(
            alert_id=alert_id,
            competitor_domain=competitor_domain,
            alert_type=alert_type,
            title=alert_messages.get(alert_type, "竞品动态更新"),
            description=f"检测到 {competitor_domain} 发生 {alert_type} 事件",
            severity=severity,
            detected_at=datetime.now(),
            impact_score=random.uniform(30, 90)
        )

        self._alerts[alert_id] = alert
        return alert

    def get_alerts(self, severity_threshold: str = "low", limit: int = 20) -> List[CompetitorAlert]:
        """获取告警列表"""
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        threshold_level = severity_order.get(severity_threshold, 0)

        filtered = [
            a for a in self._alerts.values()
            if severity_order.get(a.severity, 0) >= threshold_level
        ]

        return sorted(filtered, key=lambda x: x.detected_at, reverse=True)[:limit]


# 全局服务实例
competitor_service = CompetitorService()
