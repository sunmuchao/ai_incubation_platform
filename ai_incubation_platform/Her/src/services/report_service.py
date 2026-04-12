"""
举报系统服务

提供用户举报、安全审核、违规处理等功能
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.models import UserReportDB
from utils.logger import logger
from services.base_service import BaseService
import enum
import uuid


class ReportStatus(enum.Enum):
    """举报状态"""
    PENDING = "pending"  # 待审核
    UNDER_REVIEW = "under_review"  # 审核中
    APPROVED = "approved"  # 已确认
    REJECTED = "rejected"  # 已拒绝
    PROCESSED = "processed"  # 已处理


class ReportType(enum.Enum):
    """举报类型"""
    INAPPROPRIATE_CONTENT = "inappropriate_content"  # 不当内容
    HARASSMENT = "harassment"  # 骚扰
    FAKE_PROFILE = "fake_profile"  # 虚假资料
    SPAM = "spam"  # 垃圾信息
    UNDERAGE = "underage"  # 未成年
    OTHER = "other"  # 其他


class ReportService(BaseService):
    """举报服务"""

    def __init__(self, db: Session):
        super().__init__(db)

    def create_report(
        self,
        reporter_id: str,
        reported_user_id: str,
        report_type: str,
        reason: Optional[str] = None,
        description: Optional[str] = None,
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        date_id: Optional[str] = None,
        evidence_urls: Optional[List[str]] = None
    ) -> str:
        """
        创建举报记录

        Args:
            reporter_id: 举报人 ID
            reported_user_id: 被举报人 ID
            report_type: 举报类型
            reason: 举报原因
            description: 详细描述
            conversation_id: 相关对话 ID
            message_id: 相关消息 ID
            date_id: 相关约会 ID
            evidence_urls: 证据 URL 列表

        Returns:
            举报记录 ID
        """
        report_id = f"rpt-{uuid.uuid4().hex[:8]}"

        # 计算优先级
        priority = self._calculate_priority(report_type, reported_user_id)

        report = UserReportDB(
            id=report_id,
            reporter_id=reporter_id,
            reported_user_id=reported_user_id,
            report_type=report_type,
            reason=reason,
            description=description,
            conversation_id=conversation_id,
            message_id=message_id,
            date_id=date_id,
            evidence_urls=evidence_urls,
            status=ReportStatus.PENDING.value,
            priority=priority
        )

        self.db.add(report)
        self.db.commit()

        logger.warning(f"Report created: id={report_id}, reporter={reporter_id}, reported={reported_user_id}, type={report_type}")

        # 如果是高优先级举报，发送通知给管理员
        if priority >= 4:
            self._notify_admin(report)

        return report_id

    def _calculate_priority(self, report_type: str, reported_user_id: str) -> int:
        """
        计算举报优先级

        基于：
        - 举报类型严重程度
        - 被举报人历史违规次数
        """
        # 类型基础优先级
        type_priority = {
            ReportType.UNDERAGE.value: 5,
            ReportType.HARASSMENT.value: 4,
            ReportType.INAPPROPRIATE_CONTENT.value: 3,
            ReportType.FAKE_PROFILE.value: 3,
            ReportType.SPAM.value: 2,
            ReportType.OTHER.value: 1
        }

        priority = type_priority.get(report_type, 1)

        # 检查被举报人历史违规
        try:
            from db.models import UserDB
            user = self.db.query(UserDB).filter(UserDB.id == reported_user_id).first()
            if user:
                violation_count = getattr(user, "violation_count", 0)
                if violation_count >= 3:
                    priority = min(priority + 1, 5)
                elif violation_count >= 5:
                    priority = 5
        except Exception as e:
            logger.error(f"ReportService: Error checking violation history: {e}")

        return priority

    def _notify_admin(self, report: UserReportDB):
        """通知管理员高优先级举报"""
        logger.warning(f"ReportService: High priority report {report.id} requires admin attention")

        # 异步发送通知（不阻塞主流程）
        import asyncio
        from integration.jpush_client import get_jpush_client
        from config import settings

        admin_emails = settings.admin_emails

        async def send_async():
            if admin_emails:
                jpush = get_jpush_client()
                try:
                    await jpush.push(
                        target=admin_emails,
                        title="高优先级举报提醒",
                        content=f"举报 ID: {report.id}, 类型：{report.report_type}, 优先级：{report.priority}",
                        extras={
                            "type": "high_priority_report",
                            "report_id": report.id,
                            "report_type": report.report_type,
                            "priority": report.priority
                        }
                    )
                    logger.info(f"Admin alert sent for report {report.id}")
                except Exception as e:
                    logger.error(f"Failed to send admin alert: {e}")
            else:
                logger.warning("No admin emails configured for high priority report alerts")

        # 在新线程中运行异步函数
        asyncio.create_task(send_async())

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """获取举报详情"""
        report = self.db.query(UserReportDB).filter(UserReportDB.id == report_id).first()

        if not report:
            return None

        return {
            "id": report.id,
            "reporter_id": report.reporter_id,
            "reported_user_id": report.reported_user_id,
            "report_type": report.report_type,
            "reason": report.reason,
            "description": report.description,
            "status": report.status,
            "priority": report.priority,
            "evidence_urls": report.evidence_urls,
            "review_notes": report.review_notes,
            "action_taken": report.action_taken,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "reviewed_at": report.reviewed_at.isoformat() if report.reviewed_at else None
        }

    def get_user_reports(
        self,
        user_id: str,
        as_reporter: bool = True,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取用户的举报记录（作为举报人或被举报人）"""
        if as_reporter:
            reports = self.db.query(UserReportDB).filter(
                UserReportDB.reporter_id == user_id
            ).order_by(UserReportDB.created_at.desc()).limit(limit).all()
        else:
            reports = self.db.query(UserReportDB).filter(
                UserReportDB.reported_user_id == user_id
            ).order_by(UserReportDB.created_at.desc()).limit(limit).all()

        return [
            {
                "id": r.id,
                "report_type": r.report_type,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in reports
        ]

    def update_status(
        self,
        report_id: str,
        status: str,
        reviewed_by: Optional[str] = None,
        review_notes: Optional[str] = None
    ) -> bool:
        """更新举报状态"""
        report = self.db.query(UserReportDB).filter(UserReportDB.id == report_id).first()

        if not report:
            return False

        report.status = status
        if reviewed_by:
            report.reviewed_by = reviewed_by
        if review_notes:
            report.review_notes = review_notes
        if status in [ReportStatus.APPROVED.value, ReportStatus.REJECTED.value, ReportStatus.PROCESSED.value]:
            report.reviewed_at = datetime.now()

        self.db.commit()
        logger.info(f"Report {report_id} status updated to {status}")

        return True

    def take_action(
        self,
        report_id: str,
        action: str,
        action_details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        对举报采取行动

        Actions:
        - warning: 警告
        - temporary_ban: 临时封禁
        - permanent_ban: 永久封禁
        - content_removal: 删除内容
        - no_action: 无需处理
        """
        report = self.db.query(UserReportDB).filter(UserReportDB.id == report_id).first()

        if not report:
            return False

        report.action_taken = action
        report.action_details = action_details
        report.status = ReportStatus.PROCESSED.value

        # 如果采取行动针对被举报人
        if action in ["warning", "temporary_ban", "permanent_ban"]:
            self._apply_user_action(report.reported_user_id, action, action_details)

        self.db.commit()
        logger.info(f"Report {report_id} action taken: {action}")

        return True

    def _apply_user_action(
        self,
        user_id: str,
        action: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """对用户采取行动"""
        try:
            from db.models import UserDB

            user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
            if not user:
                return

            if action == "warning":
                # 增加违规计数
                user.violation_count = getattr(user, "violation_count", 0) + 1
                logger.warning(f"User {user_id} received warning, violation_count={user.violation_count}")

            elif action == "temporary_ban":
                user.is_active = False
                user.ban_reason = details.get("reason") if details else "违反社区准则"
                logger.warning(f"User {user_id} temporarily banned")

            elif action == "permanent_ban":
                user.is_active = False
                user.is_permanently_banned = True
                logger.critical(f"User {user_id} permanently banned")

            self.db.commit()

        except Exception as e:
            logger.error(f"ReportService: Error applying user action: {e}")
            self.db.rollback()

    def get_pending_reports(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取待审核的举报"""
        reports = self.db.query(UserReportDB).filter(
            UserReportDB.status == ReportStatus.PENDING.value
        ).order_by(
            UserReportDB.priority.desc(),
            UserReportDB.created_at.asc()
        ).limit(limit).all()

        return [
            {
                "id": r.id,
                "reporter_id": r.reporter_id,
                "reported_user_id": r.reported_user_id,
                "report_type": r.report_type,
                "reason": r.reason,
                "priority": r.priority,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in reports
        ]

    def get_report_stats(self, days: int = 30) -> Dict[str, Any]:
        """获取举报统计"""
        start_date = datetime.now() - timedelta(days=days)

        reports = self.db.query(UserReportDB).filter(
            UserReportDB.created_at >= start_date
        ).all()

        stats = {
            "total": len(reports),
            "by_status": {},
            "by_type": {},
            "avg_review_time_hours": 0
        }

        # 按状态统计
        for report in reports:
            stats["by_status"][report.status] = stats["by_status"].get(report.status, 0) + 1
            stats["by_type"][report.report_type] = stats["by_type"].get(report.report_type, 0) + 1

        return stats


# 便捷函数
def get_report_service(db: Session) -> ReportService:
    """获取举报服务实例"""
    return ReportService(db)
