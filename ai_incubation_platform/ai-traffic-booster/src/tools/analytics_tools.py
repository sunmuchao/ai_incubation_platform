"""
流量分析工具集 - 封装流量分析能力为 DeerFlow 可调用工具
"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import date, timedelta
import sys
from pathlib import Path

# 添加 src 到路径以便导入
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from analytics.service import analytics_service
from schemas.analytics import (
    TrafficOverviewRequest,
    TrafficSource
)


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any
    message: str = ""
    error: Optional[str] = None


class AnalyticsTools:
    """
    流量分析工具集

    提供流量概览、页面性能分析、关键词排名追踪等能力，
    可作为 DeerFlow 2.0 的工具节点被调用。
    """

    def __init__(self):
        self._service = analytics_service

    def get_traffic_overview(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        domain: Optional[str] = None,
        sources: Optional[List[str]] = None
    ) -> ToolResult:
        """
        获取流量概览数据

        Args:
            start_date: 开始日期 (YYYY-MM-DD 格式)，默认最近 30 天
            end_date: 结束日期 (YYYY-MM-DD 格式)，默认为今天
            domain: 域名筛选（可选）
            sources: 流量来源筛选列表（可选）

        Returns:
            ToolResult: 包含流量概览数据
        """
        try:
            # 默认最近 30 天
            if not start_date:
                start_date = (date.today() - timedelta(days=30)).isoformat()
            if not end_date:
                end_date = date.today().isoformat()

            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)

            # 转换来源枚举
            source_enums = None
            if sources:
                source_enums = []
                for s in sources:
                    try:
                        source_enums.append(TrafficSource(s))
                    except ValueError:
                        pass

            request = TrafficOverviewRequest(
                start_date=start,
                end_date=end,
                domain=domain,
                sources=source_enums
            )

            result = self._service.get_traffic_overview(request)

            return ToolResult(
                success=True,
                data={
                    "period": {"start": result.period["start"].isoformat(), "end": result.period["end"].isoformat()},
                    "total": {
                        "visitors": result.total.visitors,
                        "page_views": result.total.page_views,
                        "avg_session_duration": round(result.total.avg_session_duration, 1),
                        "bounce_rate": round(result.total.bounce_rate, 3),
                        "conversion_rate": round(result.total.conversion_rate, 4)
                    },
                    "comparison": result.comparison,
                    "sources": [{"source": s.source.value, "visitors": s.visitors, "percentage": s.percentage}
                               for s in result.sources],
                    "daily_trend": result.daily_trend[:7],  # 只返回最近 7 天
                    "device_distribution": {k.value: v for k, v in result.device_distribution.items()}
                },
                message=f"获取流量概览成功，总访客数：{result.total.visitors}"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )

    def get_page_performance(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        domain: Optional[str] = None
    ) -> ToolResult:
        """
        获取页面性能数据

        Args:
            start_date: 开始日期 (YYYY-MM-DD 格式)
            end_date: 结束日期 (YYYY-MM-DD 格式)
            domain: 域名筛选（可选）

        Returns:
            ToolResult: 包含页面性能数据
        """
        try:
            if not start_date:
                start_date = (date.today() - timedelta(days=30)).isoformat()
            if not end_date:
                end_date = date.today().isoformat()

            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)

            result = self._service.get_page_performance(start, end, domain)

            return ToolResult(
                success=True,
                data={
                    "pages": [{"url": p.url, "title": p.title, "page_views": p.page_views,
                               "unique_visitors": p.unique_visitors, "seo_score": round(p.seo_score, 1)}
                              for p in result.pages],
                    "top_performing": [{"url": p.url, "title": p.title, "seo_score": round(p.seo_score, 1)}
                                       for p in result.top_performing],
                    "underperforming": [{"url": p.url, "title": p.title, "seo_score": round(p.seo_score, 1)}
                                        for p in result.underperforming]
                },
                message=f"获取页面性能成功，共 {result.total} 个页面"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )

    def get_keyword_ranking(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> ToolResult:
        """
        获取关键词排名数据

        Args:
            start_date: 开始日期 (YYYY-MM-DD 格式)
            end_date: 结束日期 (YYYY-MM-DD 格式)

        Returns:
            ToolResult: 包含关键词排名数据
        """
        try:
            if not start_date:
                start_date = (date.today() - timedelta(days=30)).isoformat()
            if not end_date:
                end_date = date.today().isoformat()

            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)

            result = self._service.get_keyword_ranking(start, end)

            return ToolResult(
                success=True,
                data={
                    "keywords": [{"keyword": k.keyword, "current_position": k.current_position,
                                  "search_volume": k.search_volume, "ctr": round(k.ctr, 3)}
                                 for k in result.keywords],
                    "improved": [{"keyword": k.keyword, "current_position": k.current_position}
                                 for k in result.improved],
                    "declined": [{"keyword": k.keyword, "current_position": k.current_position}
                                 for k in result.declined],
                    "new_entries": [{"keyword": k.keyword, "current_position": k.current_position}
                                    for k in result.new_entries]
                },
                message=f"获取关键词排名成功，共 {len(result.keywords)} 个关键词"
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )
