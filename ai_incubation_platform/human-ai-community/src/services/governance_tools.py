"""
社区治理工具模块

提供社区治理相关的工具函数，包括：
- 内容下架
- 用户警告
- 批量处理举报
- 审计日志导出
- 治理统计分析
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json

from models.member import (
    MemberType, ContentType, ReportStatus, BanStatus, MemberRole,
    OperationType, AuditLog, Report, BanRecord, ReviewResult, ReviewStatus
)
from services.notification_service import notification_service, NotificationEvent, NotificationPriority, NotificationMessage


class GovernanceTools:
    """社区治理工具集"""

    def __init__(self, community_service):
        self.community_service = community_service

    # ==================== 内容下架工具 ====================
    def remove_content(
        self,
        content_type: ContentType,
        content_id: str,
        operator_id: str,
        reason: str,
        notify_author: bool = True
    ) -> Dict[str, Any]:
        """
        下架内容（帖子或评论）

        Args:
            content_type: 内容类型
            content_id: 内容 ID
            operator_id: 操作人 ID
            reason: 下架原因
            notify_author: 是否通知作者

        Returns:
            操作结果
        """
        operator = self.community_service.get_member(operator_id)
        if not operator or operator.role not in [MemberRole.MODERATOR, MemberRole.ADMIN]:
            return {"success": False, "error": "权限不足"}

        if content_type == ContentType.POST:
            post = self.community_service.get_post_any(content_id)
            if not post:
                return {"success": False, "error": "帖子不存在"}

            # 创建审核拒绝记录
            review = self.community_service.submit_content_for_review(
                content_id=content_id,
                content_type=ContentType.POST,
                content=f"{post.title}\n{post.content}",
                author_id=post.author_id,
                author_type=post.author_type
            )
            review.status = ReviewStatus.REJECTED
            review.review_result = ReviewResult(
                status=ReviewStatus.REJECTED,
                reason=reason,
                reviewer=operator_id,
                risk_score=1.0
            )

            # 通知作者
            if notify_author:
                message = NotificationMessage(
                    event_type=NotificationEvent.CONTENT_REJECTED,
                    title="内容下架通知",
                    content=f"您的帖子因以下原因被下架：{reason}",
                    recipient_id=post.author_id,
                    priority=NotificationPriority.HIGH
                )
                notification_service.send_notification(message)

            # 记录审计日志
            self.community_service.log_audit(
                operator_id=operator_id,
                operator_type=operator.member_type,
                operation_type=OperationType.DELETE_POST,
                resource_type="post",
                resource_id=content_id,
                after={"action": "removed", "reason": reason}
            )

            return {"success": True, "action": "removed", "content_type": "post"}

        elif content_type == ContentType.COMMENT:
            comment = self.community_service.get_comment_any(content_id)
            if not comment:
                return {"success": False, "error": "评论不存在"}

            # 创建审核拒绝记录
            review = self.community_service.submit_content_for_review(
                content_id=content_id,
                content_type=ContentType.COMMENT,
                content=comment.content,
                author_id=comment.author_id,
                author_type=comment.author_type
            )
            review.status = ReviewStatus.REJECTED
            review.review_result = ReviewResult(
                status=ReviewStatus.REJECTED,
                reason=reason,
                reviewer=operator_id,
                risk_score=1.0
            )

            # 通知作者
            if notify_author:
                message = NotificationMessage(
                    event_type=NotificationEvent.CONTENT_REJECTED,
                    title="内容下架通知",
                    content=f"您的评论因以下原因被下架：{reason}",
                    recipient_id=comment.author_id,
                    priority=NotificationPriority.HIGH
                )
                notification_service.send_notification(message)

            # 记录审计日志
            self.community_service.log_audit(
                operator_id=operator_id,
                operator_type=operator.member_type,
                operation_type=OperationType.DELETE_COMMENT,
                resource_type="comment",
                resource_id=content_id,
                after={"action": "removed", "reason": reason}
            )

            return {"success": True, "action": "removed", "content_type": "comment"}

        return {"success": False, "error": "未知内容类型"}

    # ==================== 用户警告工具 ====================
    def warn_user(
        self,
        user_id: str,
        operator_id: str,
        reason: str,
        warning_level: str = "normal"  # normal, severe
    ) -> Dict[str, Any]:
        """
        警告用户

        Args:
            user_id: 被警告用户 ID
            operator_id: 操作人 ID
            reason: 警告原因
            warning_level: 警告级别

        Returns:
            操作结果
        """
        operator = self.community_service.get_member(operator_id)
        if not operator or operator.role not in [MemberRole.MODERATOR, MemberRole.ADMIN]:
            return {"success": False, "error": "权限不足"}

        user = self.community_service.get_member(user_id)
        if not user:
            return {"success": False, "error": "用户不存在"}

        # 发送警告通知
        message = NotificationMessage(
            event_type=NotificationEvent.SYSTEM_MAINTENANCE,
            title=f"社区警告 - {warning_level}",
            content=f"您因以下原因收到社区警告：{reason}",
            recipient_id=user_id,
            priority=NotificationPriority.HIGH if warning_level == "severe" else NotificationPriority.NORMAL
        )
        notification_service.send_notification(message)

        # 记录审计日志
        self.community_service.log_audit(
            operator_id=operator_id,
            operator_type=operator.member_type,
            operation_type=OperationType.UPDATE_MEMBER,
            resource_type="user",
            resource_id=user_id,
            after={"action": "warned", "level": warning_level, "reason": reason}
        )

        return {
            "success": True,
            "action": "warned",
            "user_id": user_id,
            "level": warning_level
        }

    # ==================== 批量处理举报工具 ====================
    def batch_process_reports(
        self,
        report_ids: List[str],
        handler_id: str,
        status: ReportStatus,
        handler_note: str = ""
    ) -> Dict[str, Any]:
        """
        批量处理举报

        Args:
            report_ids: 举报 ID 列表
            handler_id: 处理人 ID
            status: 处理状态
            handler_note: 处理备注

        Returns:
            处理结果统计
        """
        results = {
            "total": len(report_ids),
            "success": 0,
            "failed": 0,
            "details": []
        }

        for report_id in report_ids:
            try:
                report = self.community_service.process_report(
                    report_id=report_id,
                    handler_id=handler_id,
                    status=status,
                    handler_note=handler_note
                )
                if report:
                    results["success"] += 1
                    results["details"].append({"report_id": report_id, "status": "processed"})
                else:
                    results["failed"] += 1
                    results["details"].append({"report_id": report_id, "status": "not_found"})
            except Exception as e:
                results["failed"] += 1
                results["details"].append({"report_id": report_id, "status": "error", "error": str(e)})

        return results

    # ==================== 审计日志导出工具 ====================
    def export_audit_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        operator_id: Optional[str] = None,
        operation_type: Optional[OperationType] = None,
        format: str = "json"
    ) -> str:
        """
        导出审计日志

        Args:
            start_time: 开始时间
            end_time: 结束时间
            operator_id: 操作人 ID（可选）
            operation_type: 操作类型（可选）
            format: 导出格式（json, csv）

        Returns:
            导出的日志内容
        """
        logs = self.community_service.list_audit_logs(
            operator_id=operator_id,
            operation_type=operation_type,
            limit=10000
        )

        # 时间过滤
        filtered_logs = [
            log for log in logs
            if start_time <= log.created_at <= end_time
        ]

        if format == "json":
            return json.dumps([log.model_dump() for log in filtered_logs], indent=2, default=str)
        elif format == "csv":
            # CSV 导出
            lines = ["id,operator_id,operator_type,operation_type,resource_type,resource_id,created_at,status"]
            for log in filtered_logs:
                lines.append(
                    f"{log.id},{log.operator_id},{log.operator_type.value},{log.operation_type.value},"
                    f"{log.resource_type},{log.resource_id},{log.created_at.isoformat()},{log.status}"
                )
            return "\n".join(lines)

        return ""

    # ==================== 治理统计分析工具 ====================
    def get_governance_stats(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取治理统计数据

        Args:
            days: 统计天数

        Returns:
            统计数据
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        # 获取审计日志
        logs = self.community_service.list_audit_logs(limit=10000)
        filtered_logs = [log for log in logs if start_time <= log.created_at <= end_time]

        # 按操作类型统计
        operation_counts = defaultdict(int)
        for log in filtered_logs:
            operation_counts[log.operation_type.value] += 1

        # 获取举报统计
        reports = list(self.community_service._reports.values())
        report_counts = defaultdict(int)
        for report in reports:
            if start_time <= report.created_at <= end_time:
                report_counts[report.status.value] += 1

        # 获取封禁统计
        bans = list(self.community_service._ban_records.values())
        ban_counts = defaultdict(int)
        for ban in bans:
            if start_time <= ban.created_at <= end_time:
                ban_counts[ban.status.value] += 1

        # 获取审核统计
        reviews = list(self.community_service._content_reviews.values())
        review_counts = defaultdict(int)
        for review in reviews:
            if start_time <= review.submit_time <= end_time:
                review_counts[review.status.value] += 1

        return {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "days": days
            },
            "operations": dict(operation_counts),
            "reports": dict(report_counts),
            "bans": dict(ban_counts),
            "reviews": dict(review_counts),
            "total_logs": len(filtered_logs)
        }

    # ==================== 用户行为分析工具 ====================
    def get_user_behavior_stats(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取用户行为统计

        Args:
            user_id: 用户 ID
            days: 统计天数

        Returns:
            用户行为统计
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        # 获取用户相关审计日志
        logs = self.community_service.list_audit_logs(operator_id=user_id, limit=1000)
        user_logs = [log for log in logs if start_time <= log.created_at <= end_time]

        # 按操作类型统计
        operation_counts = defaultdict(int)
        for log in user_logs:
            operation_counts[log.operation_type.value] += 1

        # 获取用户举报记录
        reports = [
            r for r in self.community_service._reports.values()
            if r.reporter_id == user_id and start_time <= r.created_at <= end_time
        ]

        # 获取用户被举报记录
        reported_count = 0
        # 注：这里需要遍历所有内容来检查被举报情况，简化处理

        return {
            "user_id": user_id,
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "days": days
            },
            "operations": dict(operation_counts),
            "reports_made": len(reports),
            "total_actions": len(user_logs)
        }


# 创建全局工具实例（在 community_service 初始化后使用）
def create_governance_tools(community_service) -> GovernanceTools:
    """创建治理工具实例"""
    return GovernanceTools(community_service)
