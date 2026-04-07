"""
历史数据查询服务 - P0 数据持久化增强

功能:
1. 多维度历史数据查询
2. 时间序列数据聚合
3. 查询结果缓存
4. 分页和游标支持
"""
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_, or_, desc, select
from sqlalchemy.orm import Session, joinedload
from dataclasses import dataclass, asdict
import logging
import hashlib
import json

from .postgresql_models import (
    EventModel, EventTypeEnum, DeviceTypeEnum,
    FunnelModel, FunnelStepModel, FunnelResultModel,
    SegmentModel, SegmentResultModel,
    TrafficDataEnhancedModel,
    KeywordRankingModel,
    CompetitorModel, CompetitorMetricsModel,
)
from .postgresql_config import db_manager

logger = logging.getLogger(__name__)


@dataclass
class QueryOptions:
    """查询选项"""
    page: int = 1
    page_size: int = 100
    order_by: str = "timestamp"
    order_direction: str = "desc"  # asc or desc
    include_raw: bool = False


@dataclass
class QueryResult:
    """查询结果"""
    data: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class HistoricalDataQueryService:
    """
    历史数据查询服务

    功能:
    - 事件数据查询
    - 流量数据聚合
    - 转化漏斗分析
    - 用户分群查询
    - 竞品数据查询
    - 关键词排名历史
    """

    def __init__(self, session_factory=None):
        self.session_factory = session_factory

    def _get_session(self) -> Session:
        """获取数据库会话"""
        return db_manager.get_session(read_only=True)

    # ==================== 事件数据查询 ====================

    def query_events(
        self,
        start_date: datetime,
        end_date: datetime,
        event_type: Optional[str] = None,
        event_name: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        page_url: Optional[str] = None,
        country: Optional[str] = None,
        device_type: Optional[str] = None,
        options: Optional[QueryOptions] = None,
    ) -> QueryResult:
        """
        查询事件数据

        Args:
            start_date: 开始时间
            end_date: 结束时间
            event_type: 事件类型筛选
            event_name: 事件名称筛选
            user_id: 用户 ID 筛选
            session_id: 会话 ID 筛选
            page_url: 页面 URL 筛选
            country: 国家筛选
            device_type: 设备类型筛选
            options: 查询选项

        Returns:
            查询结果
        """
        options = options or QueryOptions()

        with self._get_session() as session:
            # 构建基础查询
            query = select(EventModel).where(
                and_(
                    EventModel.timestamp >= start_date,
                    EventModel.timestamp <= end_date,
                )
            )

            # 添加筛选条件
            if event_type:
                query = query.where(EventModel.event_type == EventTypeEnum(event_type))
            if event_name:
                query = query.where(EventModel.event_name == event_name)
            if user_id:
                query = query.where(EventModel.user_id == user_id)
            if session_id:
                query = query.where(EventModel.session_id == session_id)
            if page_url:
                query = query.where(EventModel.page_url.like(f"%{page_url}%"))
            if country:
                query = query.where(EventModel.country == country)
            if device_type:
                query = query.where(EventModel.device_type == DeviceTypeEnum(device_type))

            # 获取总数
            count_query = select(func.count()).select_from(query.subquery())
            total = session.execute(count_query).scalar()

            # 排序
            if options.order_direction == "desc":
                query = query.order_by(desc(getattr(EventModel, options.order_by)))
            else:
                query = query.order_by(getattr(EventModel, options.order_by))

            # 分页
            offset = (options.page - 1) * options.page_size
            query = query.offset(offset).limit(options.page_size)

            # 执行查询
            results = session.execute(query).scalars().all()

            # 转换为字典
            data = [self._event_to_dict(event, options.include_raw) for event in results]

            return QueryResult(
                data=data,
                total=total,
                page=options.page,
                page_size=options.page_size,
                has_next=offset + len(results) < total,
                has_prev=options.page > 1,
            )

    def _event_to_dict(self, event: EventModel, include_raw: bool = False) -> Dict[str, Any]:
        """将事件模型转为字典"""
        result = {
            "id": event.id,
            "event_id": event.event_id,
            "event_type": event.event_type.value if event.event_type else None,
            "event_name": event.event_name,
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
            "user_id": event.user_id,
            "device_id": event.device_id,
            "session_id": event.session_id,
            "anonymous_id": event.anonymous_id,
            "page_url": event.page_url,
            "page_title": event.page_title,
            "referrer": event.referrer,
            "device_type": event.device_type.value if event.device_type else None,
            "os": event.os,
            "browser": event.browser,
            "country": event.country,
            "city": event.city,
            "value": event.value,
            "currency": event.currency,
        }
        if include_raw and event.properties:
            result["properties"] = event.properties
        return result

    # ==================== 流量数据聚合 ====================

    def aggregate_traffic(
        self,
        start_date: date,
        end_date: date,
        group_by: str = "day",  # hour, day, week, month
        domain: Optional[str] = None,
        source: Optional[str] = None,
        country: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        聚合流量数据

        Args:
            start_date: 开始日期
            end_date: 结束日期
            group_by: 聚合维度 (hour, day, week, month)
            domain: 域名筛选
            source: 流量来源筛选
            country: 国家筛选

        Returns:
            聚合结果列表
        """
        with self._get_session() as session:
            # 构建基础查询
            query = select(
                TrafficDataEnhancedModel.date,
                func.sum(TrafficDataEnhancedModel.visitors).label("total_visitors"),
                func.sum(TrafficDataEnhancedModel.page_views).label("total_page_views"),
                func.sum(TrafficDataEnhancedModel.sessions).label("total_sessions"),
                func.avg(TrafficDataEnhancedModel.avg_session_duration).label("avg_session_duration"),
                func.avg(TrafficDataEnhancedModel.bounce_rate).label("avg_bounce_rate"),
                func.sum(TrafficDataEnhancedModel.conversions).label("total_conversions"),
                func.sum(TrafficDataEnhancedModel.revenue).label("total_revenue"),
            ).where(
                and_(
                    TrafficDataEnhancedModel.date >= start_date,
                    TrafficDataEnhancedModel.date <= end_date,
                )
            )

            # 添加筛选条件
            if domain:
                query = query.where(TrafficDataEnhancedModel.domain == domain)
            if source:
                query = query.where(TrafficDataEnhancedModel.source == source)
            if country:
                query = query.where(TrafficDataEnhancedModel.country == country)

            # 按日期分组
            query = query.group_by(TrafficDataEnhancedModel.date).order_by(TrafficDataEnhancedModel.date)

            results = session.execute(query).all()

            return [
                {
                    "date": row.date.isoformat() if row.date else None,
                    "visitors": row.total_visitors or 0,
                    "page_views": row.total_page_views or 0,
                    "sessions": row.total_sessions or 0,
                    "avg_session_duration": round(row.avg_session_duration or 0, 2),
                    "bounce_rate": round(row.avg_bounce_rate or 0, 4),
                    "conversions": row.total_conversions or 0,
                    "revenue": round(row.total_revenue or 0, 2),
                }
                for row in results
            ]

    def get_traffic_summary(
        self,
        start_date: date,
        end_date: date,
        domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取流量汇总数据

        Args:
            start_date: 开始日期
            end_date: 结束日期
            domain: 域名筛选

        Returns:
            汇总数据
        """
        with self._get_session() as session:
            query = select(
                func.sum(TrafficDataEnhancedModel.visitors).label("total_visitors"),
                func.sum(TrafficDataEnhancedModel.page_views).label("total_page_views"),
                func.sum(TrafficDataEnhancedModel.sessions).label("total_sessions"),
                func.avg(TrafficDataEnhancedModel.avg_session_duration).label("avg_session_duration"),
                func.avg(TrafficDataEnhancedModel.bounce_rate).label("avg_bounce_rate"),
                func.sum(TrafficDataEnhancedModel.conversions).label("total_conversions"),
                func.avg(TrafficDataEnhancedModel.conversion_rate).label("avg_conversion_rate"),
            ).where(
                and_(
                    TrafficDataEnhancedModel.date >= start_date,
                    TrafficDataEnhancedModel.date <= end_date,
                )
            )

            if domain:
                query = query.where(TrafficDataEnhancedModel.domain == domain)

            result = session.execute(query).first()

            return {
                "total_visitors": result.total_visitors or 0,
                "total_page_views": result.total_page_views or 0,
                "total_sessions": result.total_sessions or 0,
                "avg_session_duration": round(result.avg_session_duration or 0, 2),
                "bounce_rate": round(result.avg_bounce_rate or 0, 4),
                "total_conversions": result.total_conversions or 0,
                "conversion_rate": round(result.avg_conversion_rate or 0, 4),
            }

    # ==================== 转化漏斗查询 ====================

    def get_funnel_results(
        self,
        funnel_id: str,
        start_date: date,
        end_date: date,
    ) -> Optional[Dict[str, Any]]:
        """获取漏斗分析结果"""
        with self._get_session() as session:
            result = session.execute(
                select(FunnelResultModel).where(
                    and_(
                        FunnelResultModel.funnel_id == funnel_id,
                        FunnelResultModel.start_date >= start_date,
                        FunnelResultModel.end_date <= end_date,
                    )
                ).order_by(desc(FunnelResultModel.analyzed_at))
            ).scalar()

            if result:
                return {
                    "funnel_id": result.funnel_id,
                    "total_entries": result.total_entries,
                    "total_completions": result.total_completions,
                    "overall_conversion_rate": result.overall_conversion_rate,
                    "step_results": result.step_results,
                    "drop_off_points": result.drop_off_points,
                    "recommendations": result.recommendations,
                    "analyzed_at": result.analyzed_at.isoformat(),
                }
            return None

    # ==================== 用户分群查询 ====================

    def get_segment_results(
        self,
        segment_id: str,
    ) -> Optional[Dict[str, Any]]:
        """获取用户分群结果"""
        with self._get_session() as session:
            result = session.execute(
                select(SegmentResultModel)
                .where(SegmentResultModel.segment_id == segment_id)
                .order_by(desc(SegmentResultModel.analyzed_at))
            ).scalar()

            if result:
                return {
                    "segment_id": result.segment_id,
                    "user_count": result.user_count,
                    "demographics": result.demographics,
                    "top_pages": result.top_pages,
                    "top_events": result.top_events,
                    "avg_session_duration": result.avg_session_duration,
                    "avg_sessions_per_user": result.avg_sessions_per_user,
                    "retention_rates": result.retention_rates,
                    "analyzed_at": result.analyzed_at.isoformat(),
                }
            return None

    # ==================== 竞品数据查询 ====================

    def get_competitor_metrics(
        self,
        competitor_id: str,
        start_date: date,
        end_date: date,
    ) -> List[Dict[str, Any]]:
        """获取竞品指标历史"""
        with self._get_session() as session:
            results = session.execute(
                select(CompetitorMetricsModel)
                .where(
                    and_(
                        CompetitorMetricsModel.competitor_id == competitor_id,
                        CompetitorMetricsModel.date >= start_date,
                        CompetitorMetricsModel.date <= end_date,
                    )
                )
                .order_by(CompetitorMetricsModel.date)
            ).scalars().all()

            return [
                {
                    "date": row.date.isoformat(),
                    "visitors": row.visitors,
                    "page_views": row.page_views,
                    "avg_visit_duration": row.avg_visit_duration,
                    "bounce_rate": row.bounce_rate,
                    "traffic_sources": row.traffic_sources,
                    "device_distribution": row.device_distribution,
                }
                for row in results
            ]

    def compare_competitors(
        self,
        competitor_ids: List[str],
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """
        对比多个竞品的指标

        Args:
            competitor_ids: 竞品 ID 列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            对比结果
        """
        result = {}
        for cid in competitor_ids:
            metrics = self.get_competitor_metrics(cid, start_date, end_date)
            if metrics:
                # 获取竞品信息
                with self._get_session() as session:
                    competitor = session.get(CompetitorModel, cid)
                    result[cid] = {
                        "name": competitor.domain if competitor else cid,
                        "metrics": metrics,
                        "summary": self._summarize_metrics(metrics),
                    }
        return result

    def _summarize_metrics(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """汇总指标"""
        if not metrics:
            return {}

        total_visitors = sum(m.get("visitors", 0) for m in metrics)
        avg_bounce_rate = sum(m.get("bounce_rate", 0) for m in metrics) / len(metrics)

        return {
            "total_visitors": total_visitors,
            "avg_bounce_rate": round(avg_bounce_rate, 4),
            "data_points": len(metrics),
        }

    # ==================== 关键词排名查询 ====================

    def get_keyword_ranking_history(
        self,
        keyword: str,
        start_date: date,
        end_date: date,
        domain: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """获取关键词排名历史"""
        with self._get_session() as session:
            query = select(KeywordRankingModel).where(
                and_(
                    KeywordRankingModel.keyword == keyword,
                    KeywordRankingModel.tracked_at >= start_date,
                    KeywordRankingModel.tracked_at <= end_date,
                )
            )

            if domain:
                query = query.where(KeywordRankingModel.domain == domain)

            query = query.order_by(KeywordRankingModel.tracked_at)

            results = session.execute(query).scalars().all()

            return [
                {
                    "keyword": row.keyword,
                    "position": row.position,
                    "previous_position": row.previous_position,
                    "position_change": row.position_change,
                    "search_volume": row.search_volume,
                    "ctr": row.ctr,
                    "traffic_share": row.traffic_share,
                    "tracked_at": row.tracked_at.isoformat(),
                }
                for row in results
            ]

    def get_top_keywords(
        self,
        start_date: date,
        end_date: date,
        limit: int = 50,
        order_by: str = "search_volume",
    ) -> List[Dict[str, Any]]:
        """获取 Top 关键词"""
        with self._get_session() as session:
            # 获取最近的排名数据
            subquery = session.execute(
                select(
                    KeywordRankingModel.keyword,
                    func.max(KeywordRankingModel.tracked_at).label("max_date")
                ).where(
                    and_(
                        KeywordRankingModel.tracked_at >= start_date,
                        KeywordRankingModel.tracked_at <= end_date,
                    )
                ).group_by(KeywordRankingModel.keyword)
            ).all()

            keyword_dates = [(row.keyword, row.max_date) for row in subquery]

            # 获取这些关键词的详情
            results = []
            for keyword, max_date in keyword_dates[:limit]:
                row = session.execute(
                    select(KeywordRankingModel).where(
                        KeywordRankingModel.keyword == keyword,
                        KeywordRankingModel.tracked_at == max_date,
                    )
                ).scalar()

                if row:
                    results.append({
                        "keyword": row.keyword,
                        "position": row.position,
                        "search_volume": row.search_volume,
                        "ctr": row.ctr,
                        "traffic_share": row.traffic_share,
                    })

            # 排序
            results.sort(key=lambda x: x.get(order_by, 0), reverse=True)

            return results[:limit]


# ==================== 全局实例 ====================

historical_query_service = HistoricalDataQueryService()


def get_historical_query_service() -> HistoricalDataQueryService:
    """获取历史数据查询服务实例"""
    return historical_query_service
