"""
流量分析服务实现
"""
from typing import List, Dict, Optional
from datetime import datetime, date, timedelta
import random
import hashlib
from schemas.analytics import (
    TrafficOverviewRequest,
    TrafficOverviewResponse,
    TrafficMetrics,
    TrafficSourceItem,
    TrafficSource,
    DeviceType,
    PagePerformanceResponse,
    PagePerformanceItem,
    KeywordRankingResponse,
    KeywordRankingItem
)
import logging

logger = logging.getLogger(__name__)


class AnalyticsService:
    """流量分析服务"""

    def __init__(self):
        self._sample_domains = [
            "example.com",
            "blog.example.com",
            "shop.example.com"
        ]
        self._sample_pages = [
            {"url": "/", "title": "首页"},
            {"url": "/blog", "title": "博客首页"},
            {"url": "/blog/seo-guide", "title": "SEO完全指南"},
            {"url": "/blog/content-optimization", "title": "内容优化技巧"},
            {"url": "/products", "title": "产品列表"},
            {"url": "/products/ai-tool", "title": "AI工具产品页"},
            {"url": "/about", "title": "关于我们"},
            {"url": "/contact", "title": "联系我们"}
        ]
        self._sample_keywords = [
            "SEO优化",
            "内容营销",
            "流量增长",
            "AI写作工具",
            "关键词排名",
            "网站优化",
            "内容生成",
            "用户增长",
            "转化率优化",
            "社交媒体营销"
        ]

    def get_traffic_overview(self, request: TrafficOverviewRequest) -> TrafficOverviewResponse:
        """获取流量概览"""
        # 计算日期范围
        start_date = request.start_date
        end_date = request.end_date
        days_diff = (end_date - start_date).days + 1

        # 生成总体指标
        total_visitors = random.randint(5000, 50000)
        # 域名筛选（mock）：让不同 domain 返回的量级不同，但不引入外部依赖
        if request.domain:
            domain_seed = int(hashlib.sha256(request.domain.encode("utf-8")).hexdigest(), 16)
            domain_factor = 0.85 + (domain_seed % 1000) / 1000 * 0.3  # [0.85, 1.15]
            total_visitors = int(total_visitors * domain_factor)
        total_page_views = int(total_visitors * random.uniform(1.5, 3.5))

        total_metrics = TrafficMetrics(
            visitors=total_visitors,
            page_views=total_page_views,
            avg_session_duration=random.uniform(60, 300),
            bounce_rate=random.uniform(0.3, 0.7),
            conversion_rate=random.uniform(0.01, 0.08),
            ctr=random.uniform(0.02, 0.15),
            avg_position=random.uniform(3.5, 15.0)
        )

        # 生成对比数据（与上个周期）
        comparison = {
            "visitors": random.uniform(-0.2, 0.5),
            "page_views": random.uniform(-0.15, 0.6),
            "avg_session_duration": random.uniform(-0.1, 0.3),
            "bounce_rate": random.uniform(-0.15, 0.15),
            "conversion_rate": random.uniform(-0.2, 0.4),
            "ctr": random.uniform(-0.1, 0.3),
            "avg_position": random.uniform(-0.2, 0.2)
        }

        # 生成流量来源分布
        sources = self._generate_traffic_sources(total_visitors, sources_filter=request.sources)

        # 生成每日趋势
        daily_trend = self._generate_daily_trend(start_date, end_date, total_visitors)

        # 生成设备分布
        device_distribution = {
            DeviceType.MOBILE: random.uniform(0.4, 0.7),
            DeviceType.DESKTOP: random.uniform(0.25, 0.5),
            DeviceType.TABLET: random.uniform(0.05, 0.15),
            DeviceType.OTHER: random.uniform(0.01, 0.05)
        }
        # 归一化
        total = sum(device_distribution.values())
        for device in device_distribution:
            device_distribution[device] = round(device_distribution[device] / total, 2)

        return TrafficOverviewResponse(
            period={"start": start_date, "end": end_date},
            total=total_metrics,
            comparison=comparison,
            sources=sources,
            daily_trend=daily_trend,
            device_distribution=device_distribution
        )

    def get_page_performance(self, start_date: date, end_date: date, domain: Optional[str] = None) -> PagePerformanceResponse:
        """获取页面性能数据"""
        pages = []
        for page in self._sample_pages:
            page_views = random.randint(100, 10000)
            unique_visitors = int(page_views * random.uniform(0.6, 0.9))
            full_url = f"https://{domain}{page['url']}" if domain else page["url"]
            pages.append(PagePerformanceItem(
                url=full_url,
                title=page["title"],
                page_views=page_views,
                unique_visitors=unique_visitors,
                avg_time_on_page=random.uniform(30, 300),
                exit_rate=random.uniform(0.2, 0.8),
                seo_score=random.uniform(40, 95)
            ))

        # 按浏览量排序
        pages_sorted = sorted(pages, key=lambda x: x.page_views, reverse=True)

        # 找出表现最好和最差的页面
        top_performing = sorted(pages, key=lambda x: (x.seo_score, -x.page_views), reverse=True)[:3]
        underperforming = sorted(pages, key=lambda x: (x.seo_score, x.page_views))[:3]

        return PagePerformanceResponse(
            pages=pages_sorted,
            total=len(pages),
            top_performing=top_performing,
            underperforming=underperforming
        )

    def get_keyword_ranking(self, start_date: date, end_date: date) -> KeywordRankingResponse:
        """获取关键词排名数据"""
        keywords = []
        for kw in self._sample_keywords:
            current_pos = random.randint(1, 30)
            previous_pos = current_pos + random.randint(-5, 5)
            if previous_pos < 1:
                previous_pos = None
            elif previous_pos > 50:
                previous_pos = None

            keywords.append(KeywordRankingItem(
                keyword=kw,
                current_position=current_pos,
                previous_position=previous_pos,
                search_volume=random.randint(100, 10000),
                ctr=random.uniform(0.01, 0.2),
                traffic_share=random.uniform(0.01, 0.15)
            ))

        # 分类
        improved = []
        declined = []
        new_entries = []
        dropped = []

        for kw in keywords:
            if kw.previous_position is None:
                if kw.current_position <= 30:
                    new_entries.append(kw)
                else:
                    dropped.append(kw)
            else:
                if kw.current_position < kw.previous_position:
                    improved.append(kw)
                elif kw.current_position > kw.previous_position:
                    declined.append(kw)

        return KeywordRankingResponse(
            keywords=keywords,
            improved=improved,
            declined=declined,
            new_entries=new_entries,
            dropped=dropped
        )

    def _generate_traffic_sources(
        self,
        total_visitors: int,
        sources_filter: Optional[List[TrafficSource]] = None,
    ) -> List[TrafficSourceItem]:
        """生成流量来源数据"""
        source_distribution = {
            TrafficSource.ORGANIC_SEARCH: random.uniform(0.3, 0.6),
            TrafficSource.DIRECT: random.uniform(0.1, 0.25),
            TrafficSource.SOCIAL_MEDIA: random.uniform(0.1, 0.2),
            TrafficSource.REFERRAL: random.uniform(0.05, 0.15),
            TrafficSource.PAID_AD: random.uniform(0.05, 0.2),
            TrafficSource.EMAIL: random.uniform(0.02, 0.1),
            TrafficSource.OTHER: random.uniform(0.01, 0.05)
        }

        # sources 筛选（mock）：严格只返回请求指定的来源，并重新归一化比例
        if sources_filter:
            allowed = set(sources_filter)
            source_distribution = {k: v for k, v in source_distribution.items() if k in allowed}
            # 兜底：如果传入空列表或过滤后为空，退回全量
            if not source_distribution:
                source_distribution = {
                    TrafficSource.ORGANIC_SEARCH: random.uniform(0.3, 0.6),
                    TrafficSource.DIRECT: random.uniform(0.1, 0.25),
                    TrafficSource.SOCIAL_MEDIA: random.uniform(0.1, 0.2),
                    TrafficSource.REFERRAL: random.uniform(0.05, 0.15),
                    TrafficSource.PAID_AD: random.uniform(0.05, 0.2),
                    TrafficSource.EMAIL: random.uniform(0.02, 0.1),
                    TrafficSource.OTHER: random.uniform(0.01, 0.05),
                }

        # 归一化
        total_ratio = sum(source_distribution.values())
        sources = []
        for source, ratio in source_distribution.items():
            normalized_ratio = ratio / total_ratio
            visitors = int(total_visitors * normalized_ratio)
            sources.append(TrafficSourceItem(
                source=source,
                visitors=visitors,
                percentage=round(normalized_ratio, 2),
                conversion_rate=random.uniform(0.01, 0.1)
            ))

        # 按访问量排序
        return sorted(sources, key=lambda x: x.visitors, reverse=True)

    def _generate_daily_trend(self, start_date: date, end_date: date, total_visitors: int) -> List[Dict[str, any]]:
        """生成每日趋势数据"""
        days_diff = (end_date - start_date).days + 1
        daily_avg = total_visitors / days_diff
        trend = []

        current_date = start_date
        for i in range(days_diff):
            # 添加一些波动
            daily_visitors = int(daily_avg * random.uniform(0.7, 1.5))
            daily_page_views = int(daily_visitors * random.uniform(1.5, 3.5))

            trend.append({
                "date": current_date,
                "visitors": daily_visitors,
                "page_views": daily_page_views,
                "conversion_rate": random.uniform(0.01, 0.08),
                "bounce_rate": random.uniform(0.3, 0.7)
            })

            current_date += timedelta(days=1)

        return trend

    def import_traffic_data(self, data: List[Dict]) -> int:
        """
        批量导入流量数据

        Args:
            data: 标准化的流量数据列表

        Returns:
            成功导入的数据条数
        """
        # 这里可以实现实际的数据持久化逻辑
        # 当前版本暂时只是模拟导入成功
        imported_count = len(data)

        # 简单验证数据格式
        valid_count = 0
        for item in data:
            if isinstance(item, dict) and "date" in item and "path" in item:
                valid_count += 1

        # 可以在这里添加数据存储逻辑，例如保存到数据库
        # 目前仅返回有效数据条数
        return valid_count


# 全局服务实例
analytics_service = AnalyticsService()
