"""
治理报告服务

实现 AI 版主自动生成治理报告、透明度报告、数据分析等功能
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
import logging
import uuid
import json

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import (
    DBGovernanceReport, DBBehaviorTrace, DBReport, DBPost, DBComment,
    DBAuditLog, DBCommunityMember, DBAgentReputation
)
from db.manager import db_manager
from models.member import ReportStatus, ReviewStatus, ContentType, OperationType
from models.p6_entities import (
    GovernanceReportType, GovernanceReportStatus, GovernanceReportVisibility,
    GovernanceReportMetrics
)

logger = logging.getLogger(__name__)


class GovernanceReportService:
    """治理报告服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_daily_report(
        self,
        date: Optional[datetime] = None,
        generated_by: str = "ai_moderator",
        agent_id: str = "ai_moderator"
    ) -> DBGovernanceReport:
        """
        生成每日治理报告

        Args:
            date: 报告日期（默认昨天）
            generated_by: 生成者
            agent_id: AI Agent ID

        Returns:
            生成的治理报告
        """
        if date is None:
            date = datetime.now() - timedelta(days=1)

        start_time = datetime(date.year, date.month, date.day)
        end_time = start_time + timedelta(days=1)

        # 收集统计数据
        metrics = await self._collect_metrics(start_time, end_time)

        # 生成报告内容
        content = await self._generate_report_content(start_time, end_time, metrics)

        # 创建报告
        report = DBGovernanceReport(
            id=str(uuid.uuid4()),
            report_type=GovernanceReportType.DAILY.value,
            report_title=f"每日治理报告 - {start_time.strftime('%Y-%m-%d')}",
            start_time=start_time,
            end_time=end_time,
            generated_by=generated_by,
            agent_id=agent_id,
            summary=content.get("summary", ""),
            content=content,
            metrics=metrics,
            total_posts=metrics.get("total_posts", 0),
            total_comments=metrics.get("total_comments", 0),
            total_reports=metrics.get("total_reports", 0),
            auto_processed=metrics.get("auto_processed", 0),
            manual_reviewed=metrics.get("manual_reviewed", 0),
            violation_rate=metrics.get("violation_rate", 0),
            auto_resolution_rate=metrics.get("auto_resolution_rate", 0),
            avg_response_time=metrics.get("avg_response_time", 0),
            user_satisfaction=metrics.get("user_satisfaction", 0),
            status=GovernanceReportStatus.DRAFT.value,
            visibility=GovernanceReportVisibility.MODERATOR.value
        )

        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)

        logger.info(f"生成每日治理报告：{report.id}")
        return report

    async def generate_weekly_report(
        self,
        end_date: Optional[datetime] = None,
        generated_by: str = "ai_moderator",
        agent_id: str = "ai_moderator"
    ) -> DBGovernanceReport:
        """
        生成每周治理报告

        Args:
            end_date: 结束日期（默认今天）
            generated_by: 生成者
            agent_id: AI Agent ID

        Returns:
            生成的治理报告
        """
        if end_date is None:
            end_date = datetime.now()

        # 找到最近的周一
        start_date = end_date - timedelta(days=end_date.weekday())
        start_time = datetime(start_date.year, start_date.month, start_date.day)
        end_time = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)

        # 收集统计数据
        metrics = await self._collect_metrics(start_time, end_time)

        # 生成报告内容
        content = await self._generate_report_content(start_time, end_time, metrics)

        # 添加周趋势分析
        content["weekly_trend"] = await self._analyze_weekly_trend(start_time, end_time)

        # 创建报告
        report = DBGovernanceReport(
            id=str(uuid.uuid4()),
            report_type=GovernanceReportType.WEEKLY.value,
            report_title=f"每周治理报告 - {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}",
            start_time=start_time,
            end_time=end_time,
            generated_by=generated_by,
            agent_id=agent_id,
            summary=content.get("summary", ""),
            content=content,
            metrics=metrics,
            total_posts=metrics.get("total_posts", 0),
            total_comments=metrics.get("total_comments", 0),
            total_reports=metrics.get("total_reports", 0),
            auto_processed=metrics.get("auto_processed", 0),
            manual_reviewed=metrics.get("manual_reviewed", 0),
            violation_rate=metrics.get("violation_rate", 0),
            auto_resolution_rate=metrics.get("auto_resolution_rate", 0),
            avg_response_time=metrics.get("avg_response_time", 0),
            user_satisfaction=metrics.get("user_satisfaction", 0),
            status=GovernanceReportStatus.DRAFT.value,
            visibility=GovernanceReportVisibility.MODERATOR.value
        )

        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)

        logger.info(f"生成每周治理报告：{report.id}")
        return report

    async def generate_monthly_report(
        self,
        end_date: Optional[datetime] = None,
        generated_by: str = "ai_moderator",
        agent_id: str = "ai_moderator"
    ) -> DBGovernanceReport:
        """
        生成每月治理报告

        Args:
            end_date: 结束日期（默认今天）
            generated_by: 生成者
            agent_id: AI Agent ID

        Returns:
            生成的治理报告
        """
        if end_date is None:
            end_date = datetime.now()

        # 找到月初
        start_date = end_date.replace(day=1)
        start_time = datetime(start_date.year, start_date.month, start_date.day)
        end_time = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)

        # 收集统计数据
        metrics = await self._collect_metrics(start_time, end_time)

        # 生成报告内容
        content = await self._generate_report_content(start_time, end_time, metrics)

        # 添加月度趋势分析
        content["monthly_trend"] = await self._analyze_monthly_trend(start_time, end_time)

        # 添加月度对比分析
        content["month_over_month_comparison"] = await self._analyze_month_over_month(start_time, end_time)

        # 添加版主表现排行榜
        content["moderator_leaderboard"] = await self._get_moderator_leaderboard(start_time, end_time)

        # 创建报告
        report = DBGovernanceReport(
            id=str(uuid.uuid4()),
            report_type=GovernanceReportType.MONTHLY.value,
            report_title=f"每月治理报告 - {start_time.strftime('%Y年%m月')}",
            start_time=start_time,
            end_time=end_time,
            generated_by=generated_by,
            agent_id=agent_id,
            summary=content.get("summary", ""),
            content=content,
            metrics=metrics,
            total_posts=metrics.get("total_posts", 0),
            total_comments=metrics.get("total_comments", 0),
            total_reports=metrics.get("total_reports", 0),
            auto_processed=metrics.get("auto_processed", 0),
            manual_reviewed=metrics.get("manual_reviewed", 0),
            violation_rate=metrics.get("violation_rate", 0),
            auto_resolution_rate=metrics.get("auto_resolution_rate", 0),
            avg_response_time=metrics.get("avg_response_time", 0),
            user_satisfaction=metrics.get("user_satisfaction", 0),
            status=GovernanceReportStatus.DRAFT.value,
            visibility=GovernanceReportVisibility.PUBLIC.value
        )

        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)

        logger.info(f"生成每月治理报告：{report.id}")
        return report

    async def generate_special_report(
        self,
        title: str,
        description: str,
        start_time: datetime,
        end_time: datetime,
        generated_by: str = "ai_moderator",
        agent_id: str = "ai_moderator"
    ) -> DBGovernanceReport:
        """
        生成特殊事件治理报告

        Args:
            title: 报告标题
            description: 事件描述
            start_time: 事件开始时间
            end_time: 事件结束时间
            generated_by: 生成者
            agent_id: AI Agent ID

        Returns:
            生成的治理报告
        """
        # 收集统计数据
        metrics = await self._collect_metrics(start_time, end_time)

        # 生成报告内容
        content = await self._generate_report_content(start_time, end_time, metrics)

        # 添加特殊事件描述
        content["event_description"] = description
        content["event_type"] = "special"

        # 获取事件期间的高热度帖子
        content["hot_posts"] = await self._get_hot_posts_during_event(start_time, end_time)

        # 获取事件期间的主要违规类型
        content["major_violations"] = await self._get_major_violations(start_time, end_time)

        # 创建报告
        report = DBGovernanceReport(
            id=str(uuid.uuid4()),
            report_type=GovernanceReportType.SPECIAL.value,
            report_title=title,
            start_time=start_time,
            end_time=end_time,
            generated_by=generated_by,
            agent_id=agent_id,
            summary=content.get("summary", ""),
            content=content,
            metrics=metrics,
            total_posts=metrics.get("total_posts", 0),
            total_comments=metrics.get("total_comments", 0),
            total_reports=metrics.get("total_reports", 0),
            auto_processed=metrics.get("auto_processed", 0),
            manual_reviewed=metrics.get("manual_reviewed", 0),
            violation_rate=metrics.get("violation_rate", 0),
            auto_resolution_rate=metrics.get("auto_resolution_rate", 0),
            avg_response_time=metrics.get("avg_response_time", 0),
            user_satisfaction=metrics.get("user_satisfaction", 0),
            status=GovernanceReportStatus.DRAFT.value,
            visibility=GovernanceReportVisibility.MODERATOR.value
        )

        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)

        logger.info(f"生成特殊事件治理报告：{report.id}")
        return report

    async def _analyze_monthly_trend(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """分析月度趋势"""
        weekly_stats = []
        current = start_time
        while current < end_time:
            next_week = current + timedelta(days=7)
            if next_week > end_time:
                next_week = end_time
            metrics = await self._collect_metrics(current, next_week)
            weekly_stats.append({
                "week_start": current.strftime("%Y-%m-%d"),
                "metrics": metrics
            })
            current = next_week

        return {
            "weekly_stats": weekly_stats,
            "trend_analysis": self._calculate_trend(weekly_stats)
        }

    async def _analyze_month_over_month(
        self,
        current_start: datetime,
        current_end: datetime
    ) -> Dict[str, Any]:
        """分析月度环比"""
        # 获取上月时间范围
        if current_start.month == 1:
            prev_start = current_start.replace(year=current_start.year - 1, month=12)
        else:
            prev_start = current_start.replace(month=current_start.month - 1)
        prev_end = current_start - timedelta(seconds=1)

        # 收集上月数据
        prev_metrics = await self._collect_metrics(prev_start, prev_end)
        curr_metrics = await self._collect_metrics(current_start, current_end)

        def calc_change(curr: float, prev: float) -> Dict[str, Any]:
            if prev == 0:
                return {"current": curr, "previous": prev, "change": 0, "change_rate": 0}
            change = curr - prev
            rate = (change / prev) * 100
            return {
                "current": curr,
                "previous": prev,
                "change": round(change, 2),
                "change_rate": round(rate, 2)
            }

        return {
            "period": f"{prev_start.strftime('%Y-%m')} vs {current_start.strftime('%Y-%m')}",
            "posts": calc_change(curr_metrics.get("total_posts", 0), prev_metrics.get("total_posts", 0)),
            "comments": calc_change(curr_metrics.get("total_comments", 0), prev_metrics.get("total_comments", 0)),
            "reports": calc_change(curr_metrics.get("total_reports", 0), prev_metrics.get("total_reports", 0)),
            "violation_rate": calc_change(curr_metrics.get("violation_rate", 0), prev_metrics.get("violation_rate", 0)),
            "auto_resolution_rate": calc_change(curr_metrics.get("auto_resolution_rate", 0), prev_metrics.get("auto_resolution_rate", 0))
        }

    async def _get_moderator_leaderboard(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """获取版主表现排行榜"""
        # 查询 AI Agent 版主的表现
        result = await self.db.execute(
            select(
                DBAgentReputation.agent_id,
                DBAgentReputation.agent_name,
                DBAgentReputation.reputation_score,
                DBAgentReputation.total_actions,
                DBAgentReputation.accuracy_score,
                DBAgentReputation.fairness_score,
                DBAgentReputation.transparency_score
            ).where(
                DBAgentReputation.agent_type == "moderator",
                DBAgentReputation.last_action_time >= start_time,
                DBAgentReputation.last_action_time <= end_time,
                DBAgentReputation.is_active == True
            ).order_by(desc(DBAgentReputation.reputation_score))
        )

        leaderboard = []
        for idx, row in enumerate(result.all(), 1):
            leaderboard.append({
                "rank": idx,
                "agent_id": row[0],
                "agent_name": row[1],
                "reputation_score": row[2],
                "total_actions": row[3],
                "accuracy_score": row[4],
                "fairness_score": row[5],
                "transparency_score": row[6]
            })

        return leaderboard

    async def _get_hot_posts_during_event(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """获取事件期间的高热度帖子"""
        # 获取评论最多的帖子
        result = await self.db.execute(
            select(
                DBPost.id,
                DBPost.title,
                DBPost.author_id,
                func.count(DBComment.id).label("comment_count")
            )
            .join(DBComment, DBComment.post_id == DBPost.id, isouter=True)
            .where(
                DBPost.created_at >= start_time,
                DBPost.created_at <= end_time
            )
            .group_by(DBPost.id, DBPost.title, DBPost.author_id)
            .order_by(desc("comment_count"))
            .limit(10)
        )

        hot_posts = []
        for row in result.all():
            hot_posts.append({
                "post_id": row[0],
                "title": row[1],
                "author_id": row[2],
                "engagement": row[3]
            })

        return hot_posts

    async def _get_major_violations(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """获取主要违规类型统计"""
        result = await self.db.execute(
            select(
                DBReport.report_type,
                func.count(DBReport.id).label("count")
            ).where(
                DBReport.created_at >= start_time,
                DBReport.created_at <= end_time,
                DBReport.status == ReportStatus.RESOLVED.value
            ).group_by(DBReport.report_type)
            .order_by(desc("count"))
        )

        violations = []
        for row in result.all():
            violations.append({
                "type": row[0],
                "count": row[1]
            })

        return violations

    async def _collect_metrics(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """收集治理指标数据"""
        metrics = {}

        # 帖子统计
        result = await self.db.execute(
            select(func.count(DBPost.id)).where(
                DBPost.created_at >= start_time,
                DBPost.created_at <= end_time
            )
        )
        metrics["total_posts"] = result.scalar() or 0

        # 评论统计
        result = await self.db.execute(
            select(func.count(DBComment.id)).where(
                DBComment.created_at >= start_time,
                DBComment.created_at <= end_time
            )
        )
        metrics["total_comments"] = result.scalar() or 0

        # 举报统计
        result = await self.db.execute(
            select(func.count(DBReport.id)).where(
                DBReport.created_at >= start_time,
                DBReport.created_at <= end_time
            )
        )
        metrics["total_reports"] = result.scalar() or 0

        # AI 自动处理统计
        result = await self.db.execute(
            select(func.count(DBReport.id)).where(
                DBReport.created_at >= start_time,
                DBReport.created_at <= end_time,
                DBReport.handler_id == "ai_moderator"
            )
        )
        metrics["auto_processed"] = result.scalar() or 0

        # 人工审核统计
        result = await self.db.execute(
            select(func.count(DBReport.id)).where(
                DBReport.created_at >= start_time,
                DBReport.created_at <= end_time,
                DBReport.handler_id != "ai_moderator",
                DBReport.handler_id is not None
            )
        )
        metrics["manual_reviewed"] = result.scalar() or 0

        # 违规统计
        result = await self.db.execute(
            select(func.count(DBReport.id)).where(
                DBReport.created_at >= start_time,
                DBReport.created_at <= end_time,
                DBReport.status == ReportStatus.RESOLVED.value
            )
        )
        confirmed_violations = result.scalar() or 0

        # 计算违规率
        total_content = metrics["total_posts"] + metrics["total_comments"]
        metrics["violation_rate"] = (
            round(confirmed_violations / total_content * 100, 2)
            if total_content > 0 else 0
        )

        # 计算 AI 解决率
        total_handled = metrics["auto_processed"] + metrics["manual_reviewed"]
        metrics["auto_resolution_rate"] = (
            round(metrics["auto_processed"] / total_handled * 100, 2)
            if total_handled > 0 else 0
        )

        # AI 行为追溯统计（平均响应时间）
        result = await self.db.execute(
            select(func.avg(DBBehaviorTrace.duration_ms)).where(
                DBBehaviorTrace.started_at >= start_time,
                DBBehaviorTrace.started_at <= end_time
            )
        )
        metrics["avg_response_time"] = round(result.scalar() or 0, 2)

        # 用户满意度（基于反馈）
        metrics["user_satisfaction"] = await self._calculate_user_satisfaction(start_time, end_time)

        return metrics

    async def _calculate_user_satisfaction(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> float:
        """计算用户满意度"""
        # 从行为追溯中获取用户反馈
        result = await self.db.execute(
            select(DBBehaviorTrace.user_feedback).where(
                DBBehaviorTrace.started_at >= start_time,
                DBBehaviorTrace.started_at <= end_time,
                DBBehaviorTrace.user_feedback is not None
            )
        )
        feedbacks = result.scalars().all()

        if not feedbacks:
            return 0.75  # 默认满意度

        # 解析反馈并计算平均分
        total_rating = 0
        count = 0
        for feedback in feedbacks:
            if isinstance(feedback, dict) and "rating" in feedback:
                total_rating += feedback["rating"]
                count += 1
            elif isinstance(feedback, dict) and "ratings" in feedback:
                for rating_item in feedback.get("ratings", []):
                    if isinstance(rating_item, dict) and "rating" in rating_item:
                        total_rating += rating_item["rating"]
                        count += 1

        if count == 0:
            return 0.75

        # 转换为 0-1 的分数（假设评分是 1-5）
        avg_rating = total_rating / count
        return round(avg_rating / 5, 3)

    async def _generate_report_content(
        self,
        start_time: datetime,
        end_time: datetime,
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成报告内容"""
        content = {
            "summary": self._generate_summary(metrics),
            "highlights": [],
            "concerns": [],
            "recommendations": []
        }

        # 生成亮点
        if metrics["auto_resolution_rate"] >= 70:
            content["highlights"].append(
                f"AI 自动处理率达到 {metrics['auto_resolution_rate']}%，显著减轻人工审核负担"
            )

        if metrics["violation_rate"] < 5:
            content["highlights"].append(
                f"违规率仅 {metrics['violation_rate']}%，社区氛围良好"
            )

        # 生成关注点
        if metrics["violation_rate"] >= 10:
            content["concerns"].append(
                f"违规率偏高 ({metrics['violation_rate']}%)，建议加强内容审核"
            )

        if metrics["avg_response_time"] > 500:
            content["concerns"].append(
                f"AI 平均响应时间 {metrics['avg_response_time']}ms，建议优化性能"
            )

        # 生成建议
        if metrics["auto_resolution_rate"] < 50:
            content["recommendations"].append(
                "考虑优化 AI 审核规则，提高自动处理率"
            )

        if metrics["user_satisfaction"] < 0.6:
            content["recommendations"].append(
                "用户满意度较低，建议收集更多反馈并改进 AI 决策质量"
            )

        # 违规类型分布
        content["violation_type_distribution"] = await self._get_violation_type_distribution(
            start_time, end_time
        )

        # AI Agent 表现
        content["agent_performance"] = await self._get_agent_performance(start_time, end_time)

        return content

    def _generate_summary(self, metrics: Dict[str, Any]) -> str:
        """生成报告摘要"""
        summary_parts = []

        summary_parts.append(
            f"本周期内共发布 {metrics['total_posts']} 个帖子和 {metrics['total_comments']} 条评论。"
        )

        summary_parts.append(
            f"收到 {metrics['total_reports']} 个举报，其中 AI 自动处理 {metrics['auto_processed']} 个，"
            f"人工审核 {metrics['manual_reviewed']} 个。"
        )

        summary_parts.append(
            f"违规率为 {metrics['violation_rate']}%，AI 解决率为 {metrics['auto_resolution_rate']}%。"
        )

        return " ".join(summary_parts)

    async def _get_violation_type_distribution(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, int]:
        """获取违规类型分布"""
        result = await self.db.execute(
            select(
                DBReport.report_type,
                func.count(DBReport.id)
            ).where(
                DBReport.created_at >= start_time,
                DBReport.created_at <= end_time,
                DBReport.status == ReportStatus.RESOLVED.value
            ).group_by(DBReport.report_type)
        )
        return dict(result.all())

    async def _get_agent_performance(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """获取 AI Agent 表现"""
        result = await self.db.execute(
            select(
                DBAgentReputation.agent_id,
                DBAgentReputation.agent_name,
                DBAgentReputation.agent_type,
                DBAgentReputation.reputation_score,
                DBAgentReputation.total_actions,
                DBAgentReputation.accuracy_score
            ).where(
                DBAgentReputation.last_action_time >= start_time,
                DBAgentReputation.last_action_time <= end_time
            ).order_by(desc(DBAgentReputation.reputation_score))
        )

        performances = []
        for row in result.all():
            performances.append({
                "agent_id": row[0],
                "agent_name": row[1],
                "agent_type": row[2],
                "reputation_score": row[3],
                "total_actions": row[4],
                "accuracy_score": row[5]
            })

        return performances

    async def _analyze_weekly_trend(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """分析周趋势"""
        daily_stats = []
        current = start_time
        while current < end_time:
            next_day = current + timedelta(days=1)
            metrics = await self._collect_metrics(current, next_day)
            daily_stats.append({
                "date": current.strftime("%Y-%m-%d"),
                "metrics": metrics
            })
            current = next_day

        return {
            "daily_stats": daily_stats,
            "trend_analysis": self._calculate_trend(daily_stats)
        }

    def _calculate_trend(self, daily_stats: List[Dict[str, Any]]) -> Dict[str, str]:
        """计算趋势"""
        if len(daily_stats) < 2:
            return {"posts": "stable", "reports": "stable"}

        # 简单趋势分析
        first_half_posts = sum(d["metrics"]["total_posts"] for d in daily_stats[:len(daily_stats)//2])
        second_half_posts = sum(d["metrics"]["total_posts"] for d in daily_stats[len(daily_stats)//2:])

        first_half_reports = sum(d["metrics"]["total_reports"] for d in daily_stats[:len(daily_stats)//2])
        second_half_reports = sum(d["metrics"]["total_reports"] for d in daily_stats[len(daily_stats)//2:])

        def get_trend(first: int, second: int) -> str:
            if second > first * 1.2:
                return "increasing"
            elif second < first * 0.8:
                return "decreasing"
            else:
                return "stable"

        return {
            "posts": get_trend(first_half_posts, second_half_posts),
            "reports": get_trend(first_half_reports, second_half_reports)
        }

    async def get_report(self, report_id: str) -> Optional[DBGovernanceReport]:
        """获取治理报告"""
        result = await self.db.execute(
            select(DBGovernanceReport).where(DBGovernanceReport.id == report_id)
        )
        return result.scalar_one_or_none()

    async def list_reports(
        self,
        report_type: Optional[GovernanceReportType] = None,
        status: Optional[GovernanceReportStatus] = None,
        visibility: Optional[GovernanceReportVisibility] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[DBGovernanceReport]:
        """查询治理报告列表"""
        query = select(DBGovernanceReport)

        conditions = []
        if report_type:
            conditions.append(DBGovernanceReport.report_type == report_type.value)
        if status:
            conditions.append(DBGovernanceReport.status == status.value)
        if visibility:
            conditions.append(DBGovernanceReport.visibility == visibility.value)
        if start_time:
            conditions.append(DBGovernanceReport.end_time >= start_time)
        if end_time:
            conditions.append(DBGovernanceReport.start_time <= end_time)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(desc(DBGovernanceReport.generated_at))
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def publish_report(
        self,
        report_id: str,
        visibility: GovernanceReportVisibility
    ) -> DBGovernanceReport:
        """发布治理报告"""
        report = await self.get_report(report_id)
        if not report:
            raise ValueError(f"治理报告 {report_id} 不存在")

        report.status = GovernanceReportStatus.PUBLISHED.value
        report.visibility = visibility.value

        await self.db.commit()
        await self.db.refresh(report)

        logger.info(f"发布治理报告：{report_id}, 可见性：{visibility.value}")
        return report

    async def get_transparency_report(self, agent_id: str) -> Dict[str, Any]:
        """
        生成 AI Agent 透明度报告

        Args:
            agent_id: Agent ID

        Returns:
            透明度报告字典
        """
        # 获取 Agent 信誉
        result = await self.db.execute(
            select(DBAgentReputation).where(DBAgentReputation.agent_id == agent_id)
        )
        reputation = result.scalar_one_or_none()

        if not reputation:
            raise ValueError(f"Agent {agent_id} 不存在")

        # 获取最近的行为追溯
        result = await self.db.execute(
            select(DBBehaviorTrace)
            .where(DBBehaviorTrace.agent_id == agent_id)
            .order_by(desc(DBBehaviorTrace.started_at))
            .limit(100)
        )
        traces = result.scalars().all()

        # 计算透明度指标
        transparency_metrics = self._calculate_transparency_metrics(traces)

        return {
            "agent_id": agent_id,
            "agent_name": reputation.agent_name,
            "agent_type": reputation.agent_type,
            "reputation_score": reputation.reputation_score,
            "transparency_score": transparency_metrics["overall_score"],
            "transparency_factors": transparency_metrics["factors"],
            "sample_traces": [
                {
                    "trace_id": t.trace_id,
                    "action_type": t.action_type,
                    "has_decision_process": bool(t.decision_process),
                    "has_rules_applied": bool(t.rules_applied),
                    "confidence_score": t.confidence_score
                }
                for t in traces[:10]
            ],
            "recommendations": transparency_metrics["recommendations"]
        }

    def _calculate_transparency_metrics(
        self,
        traces: List[DBBehaviorTrace]
    ) -> Dict[str, Any]:
        """计算透明度指标"""
        if not traces:
            return {
                "overall_score": 0,
                "factors": {},
                "recommendations": ["暂无足够数据进行透明度评估"]
            }

        factors = {
            "decision_process_rate": sum(1 for t in traces if t.decision_process) / len(traces),
            "rules_applied_rate": sum(1 for t in traces if t.rules_applied) / len(traces),
            "confidence_score_rate": sum(1 for t in traces if t.confidence_score is not None) / len(traces),
            "risk_assessment_rate": sum(1 for t in traces if t.risk_assessment) / len(traces),
            "model_info_rate": sum(1 for t in traces if t.model_name or t.model_provider) / len(traces)
        }

        overall_score = sum(factors.values()) / len(factors)

        recommendations = []
        if factors["decision_process_rate"] < 0.8:
            recommendations.append("建议记录更多决策过程详情")
        if factors["rules_applied_rate"] < 0.8:
            recommendations.append("建议记录应用的具体规则")
        if factors["confidence_score_rate"] < 0.8:
            recommendations.append("建议提供置信度评分")

        return {
            "overall_score": round(overall_score, 3),
            "factors": {k: round(v, 3) for k, v in factors.items()},
            "recommendations": recommendations
        }


# 全局服务实例
_governance_report_service: Optional[GovernanceReportService] = None


def get_governance_report_service(db: AsyncSession) -> GovernanceReportService:
    """获取治理报告服务实例"""
    global _governance_report_service
    if _governance_report_service is None or _governance_report_service.db is not db:
        _governance_report_service = GovernanceReportService(db)
    return _governance_report_service
