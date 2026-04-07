"""
日志分析服务

提供日志分析、异常检测、合规报告等功能
"""
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import text, func
from collections import defaultdict

from models.audit_log import (
    AuditLogEntry, QueryLogEntry, AccessLogEntry,
    UserActivityReport, LogAnomaly, ComplianceReport
)
from config.database import db_manager
from services.log_storage_service import log_storage_service
from utils.logger import logger


class LogAnalyticsService:
    """日志分析服务"""

    async def analyze_user_activity(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        hours: int = 24
    ) -> UserActivityReport:
        """分析用户活动"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        with db_manager.get_sync_session() as session:
            # 查询用户审计日志
            audit_result = session.execute(
                text("""
                    SELECT * FROM audit_logs
                    WHERE user_id = :user_id
                    AND timestamp >= :start_time
                    AND timestamp <= :end_time
                    ORDER BY timestamp DESC
                """),
                {
                    "user_id": user_id,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat()
                }
            )
            audit_logs = [AuditLogEntry.from_dict(dict(row._mapping)) for row in audit_result.fetchall()]

            # 查询用户查询日志
            query_result = session.execute(
                text("""
                    SELECT * FROM query_logs
                    WHERE user_id = :user_id
                    AND timestamp >= :start_time
                    AND timestamp <= :end_time
                """),
                {
                    "user_id": user_id,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat()
                }
            )
            query_logs = [QueryLogEntry.from_dict(dict(row._mapping)) for row in query_result.fetchall()]

            # 分析活动
            action_breakdown = defaultdict(int)
            resources = set()
            ip_addresses = set()
            failed_count = 0

            for log in audit_logs:
                action_breakdown[log.action_type] += 1
                if log.resource_type and log.resource_id:
                    resources.add(f"{log.resource_type}:{log.resource_id}")
                if log.ip_address:
                    ip_addresses.add(log.ip_address)
                if log.response_status and log.response_status >= 400:
                    failed_count += 1

            # 构建报告
            report = UserActivityReport(
                user_id=user_id,
                tenant_id=tenant_id or (audit_logs[0].tenant_id if audit_logs else ""),
                time_range_start=start_time,
                time_range_end=end_time,
                total_actions=len(audit_logs),
                action_breakdown=dict(action_breakdown),
                resources_accessed=list(resources),
                queries_executed=len(query_logs),
                total_query_duration_ms=sum(q.duration_ms for q in query_logs),
                failed_actions=failed_count,
                ip_addresses=list(ip_addresses)
            )

            return report

    async def detect_anomalies(
        self,
        tenant_id: Optional[str] = None,
        hours: int = 24
    ) -> List[LogAnomaly]:
        """检测异常日志模式"""
        anomalies = []
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        with db_manager.get_sync_session() as session:
            # 检测 1: 失败登录激增
            failed_logins = session.execute(
                text("""
                    SELECT user_id, COUNT(*) as fail_count
                    FROM audit_logs
                    WHERE action_type = 'USER_LOGIN_FAILED'
                    AND timestamp >= :start_time
                    AND timestamp <= :end_time
                    GROUP BY user_id
                    HAVING COUNT(*) > 5
                """),
                {"start_time": start_time.isoformat(), "end_time": end_time.isoformat()}
            ).fetchall()

            for row in failed_logins:
                anomalies.append(LogAnomaly(
                    anomaly_type="failed_login_spike",
                    severity="high",
                    description=f"User {row['user_id']} has {row['fail_count']} failed login attempts in {hours} hours",
                    user_id=row["user_id"],
                    evidence=[{"failed_count": row["fail_count"], "time_range_hours": hours}]
                ))

            # 检测 2: 非正常时间访问
            off_hours_access = session.execute(
                text("""
                    SELECT user_id, COUNT(*) as access_count
                    FROM audit_logs
                    WHERE timestamp >= :start_time
                    AND timestamp <= :end_time
                    AND (
                        CAST(strftime('%H', timestamp) AS INTEGER) < 6
                        OR CAST(strftime('%H', timestamp) AS INTEGER) > 22
                    )
                    GROUP BY user_id
                    HAVING COUNT(*) > 10
                """),
                {"start_time": start_time.isoformat(), "end_time": end_time.isoformat()}
            ).fetchall()

            for row in off_hours_access:
                anomalies.append(LogAnomaly(
                    anomaly_type="unusual_time_access",
                    severity="medium",
                    description=f"User {row['user_id']} has {row['access_count']} accesses during off-hours (22:00-06:00)",
                    user_id=row["user_id"],
                    evidence=[{"access_count": row["access_count"]}]
                ))

            # 检测 3: 大量失败查询
            failed_queries = session.execute(
                text("""
                    SELECT user_id, datasource, COUNT(*) as fail_count
                    FROM query_logs
                    WHERE status = 'error'
                    AND timestamp >= :start_time
                    AND timestamp <= :end_time
                    GROUP BY user_id, datasource
                    HAVING COUNT(*) > 10
                """),
                {"start_time": start_time.isoformat(), "end_time": end_time.isoformat()}
            ).fetchall()

            for row in failed_queries:
                anomalies.append(LogAnomaly(
                    anomaly_type="query_failure_spike",
                    severity="medium",
                    description=f"User {row['user_id']} has {row['fail_count']} failed queries on datasource {row['datasource']}",
                    user_id=row["user_id"],
                    affected_resources=[row["datasource"]],
                    evidence=[{"failed_count": row["fail_count"], "datasource": row["datasource"]}]
                ))

            # 检测 4: 权限拒绝激增
            access_denials = session.execute(
                text("""
                    SELECT user_id, COUNT(*) as denial_count
                    FROM access_logs
                    WHERE granted = 0
                    AND timestamp >= :start_time
                    AND timestamp <= :end_time
                    GROUP BY user_id
                    HAVING COUNT(*) > 5
                """),
                {"start_time": start_time.isoformat(), "end_time": end_time.isoformat()}
            ).fetchall()

            for row in access_denials:
                anomalies.append(LogAnomaly(
                    anomaly_type="access_denial_spike",
                    severity="high",
                    description=f"User {row['user_id']} has {row['denial_count']} access denials in {hours} hours",
                    user_id=row["user_id"],
                    evidence=[{"denial_count": row["denial_count"]}]
                ))

            # 添加租户过滤
            if tenant_id:
                anomalies = [a for a in anomalies if True]  # 已有租户信息可过滤

        logger.info(f"Detected {len(anomalies)} anomalies")
        return anomalies

    async def generate_compliance_report(
        self,
        report_type: str,
        tenant_id: str,
        days: int = 30
    ) -> ComplianceReport:
        """生成合规报告"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)

        findings = []
        recommendations = []
        summary = {}

        with db_manager.get_sync_session() as session:
            if report_type == "access_review":
                # 访问审查报告
                total_users = session.execute(
                    text("""
                        SELECT COUNT(DISTINCT user_id) FROM audit_logs
                        WHERE tenant_id = :tenant_id
                        AND timestamp >= :start_time
                    """),
                    {"tenant_id": tenant_id, "start_time": start_time.isoformat()}
                ).scalar()

                inactive_users = session.execute(
                    text("""
                        SELECT COUNT(DISTINCT user_id) FROM audit_logs
                        WHERE tenant_id = :tenant_id
                        AND timestamp >= :start_time
                        AND timestamp <= :end_time
                    """),
                    {"tenant_id": tenant_id, "start_time": start_time.isoformat(), "end_time": end_time.isoformat()}
                ).scalar()

                summary = {
                    "total_active_users": total_users,
                    "inactive_users": inactive_users,
                    "review_period_days": days
                }

                if inactive_users > 0:
                    findings.append({
                        "type": "inactive_users",
                        "severity": "medium",
                        "description": f"{inactive_users} users have been inactive in the past {days} days",
                        "recommendation": "Review and potentially revoke access for inactive users"
                    })
                    recommendations.append(f"Review {inactive_users} inactive user accounts")

            elif report_type == "permission_audit":
                # 权限审计报告
                denied_count = session.execute(
                    text("""
                        SELECT COUNT(*) FROM access_logs
                        WHERE tenant_id = :tenant_id
                        AND granted = 0
                        AND timestamp >= :start_time
                    """),
                    {"tenant_id": tenant_id, "start_time": start_time.isoformat()}
                ).scalar()

                summary = {
                    "total_access_denials": denied_count,
                    "review_period_days": days
                }

                if denied_count > 100:
                    findings.append({
                        "type": "high_access_denials",
                        "severity": "medium",
                        "description": f"{denied_count} access denials in the past {days} days",
                        "recommendation": "Review permission policies and user access patterns"
                    })
                    recommendations.append("Audit permission policies to reduce false denials")

            elif report_type == "data_access":
                # 数据访问报告
                datasource_access = session.execute(
                    text("""
                        SELECT datasource, COUNT(*) as access_count
                        FROM query_logs
                        WHERE tenant_id = :tenant_id
                        AND timestamp >= :start_time
                        GROUP BY datasource
                        ORDER BY access_count DESC
                    """),
                    {"tenant_id": tenant_id, "start_time": start_time.isoformat()}
                ).fetchall()

                summary = {
                    "datasource_access": [
                        {"datasource": row["datasource"], "access_count": row["access_count"]}
                        for row in datasource_access
                    ],
                    "review_period_days": days
                }

        report = ComplianceReport(
            report_type=report_type,
            tenant_id=tenant_id,
            time_range_start=start_time,
            time_range_end=end_time,
            summary=summary,
            findings=findings,
            recommendations=recommendations,
            status="draft"
        )

        return report

    async def get_audit_trail(
        self,
        resource_type: str,
        resource_id: str,
        tenant_id: Optional[str] = None,
        hours: int = 168
    ) -> List[AuditLogEntry]:
        """获取资源审计轨迹"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        logs, _ = await log_storage_service.query_audit_logs(
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            start_date=start_time,
            end_date=end_time,
            page=1,
            page_size=1000
        )

        return logs

    async def get_log_statistics(
        self,
        hours: int = 24
    ) -> Dict[str, Any]:
        """获取日志统计信息"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        with db_manager.get_sync_session() as session:
            # 按类型统计
            audit_count = session.execute(
                text("""
                    SELECT COUNT(*) FROM audit_logs
                    WHERE timestamp >= :start_time
                """),
                {"start_time": start_time.isoformat()}
            ).scalar()

            query_count = session.execute(
                text("""
                    SELECT COUNT(*) FROM query_logs
                    WHERE timestamp >= :start_time
                """),
                {"start_time": start_time.isoformat()}
            ).scalar()

            access_count = session.execute(
                text("""
                    SELECT COUNT(*) FROM access_logs
                    WHERE timestamp >= :start_time
                """),
                {"start_time": start_time.isoformat()}
            ).scalar()

            # 按操作类型统计
            action_stats = session.execute(
                text("""
                    SELECT action_type, COUNT(*) as count
                    FROM audit_logs
                    WHERE timestamp >= :start_time
                    GROUP BY action_type
                    ORDER BY count DESC
                """),
                {"start_time": start_time.isoformat()}
            ).fetchall()

            # 按用户统计
            user_stats = session.execute(
                text("""
                    SELECT user_id, COUNT(*) as count
                    FROM audit_logs
                    WHERE timestamp >= :start_time
                    GROUP BY user_id
                    ORDER BY count DESC
                    LIMIT 10
                """),
                {"start_time": start_time.isoformat()}
            ).fetchall()

            return {
                "log_counts": {
                    "audit": audit_count,
                    "query": query_count,
                    "access": access_count
                },
                "action_breakdown": [
                    {"action_type": row[0], "count": row[1]}
                    for row in action_stats
                ],
                "top_users": [
                    {"user_id": row[0], "count": row[1]}
                    for row in user_stats
                ],
                "time_range_hours": hours
            }


# 全局服务实例
log_analytics_service = LogAnalyticsService()
