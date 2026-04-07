"""
日志清理服务

负责根据保留策略清理过期日志
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy import text

from config.database import db_manager
from services.log_storage_service import log_storage_service
from utils.logger import logger


class CleanupResult:
    """清理结果"""
    def __init__(self):
        self.audit_logs_deleted = 0
        self.query_logs_deleted = 0
        self.access_logs_deleted = 0
        self.start_time = None
        self.end_time = None
        self.errors: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audit_logs_deleted": self.audit_logs_deleted,
            "query_logs_deleted": self.query_logs_deleted,
            "access_logs_deleted": self.access_logs_deleted,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else None,
            "errors": self.errors
        }


class LogCleanupService:
    """日志清理服务"""

    def __init__(self):
        self._cleanup_task: asyncio.Task = None
        self._cleanup_interval_hours = 24  # 每天清理一次
        self._last_cleanup_time: datetime = None

    async def initialize(self):
        """初始化服务"""
        logger.info("Initializing log cleanup service")
        # 启动定时清理任务
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Log cleanup service initialized")

    async def close(self):
        """关闭服务"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Log cleanup service closed")

    async def _cleanup_loop(self):
        """定时清理循环"""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval_hours * 3600)
                await self.apply_retention_policies()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def apply_retention_policies(self) -> CleanupResult:
        """应用保留策略，清理过期日志"""
        result = CleanupResult()
        result.start_time = datetime.utcnow()

        try:
            policies = await log_storage_service.get_retention_policies()

            with db_manager.get_sync_session() as session:
                for policy in policies:
                    try:
                        cutoff_date = datetime.utcnow() - timedelta(days=policy.retention_days)

                        if policy.log_type == "audit":
                            delete_query = text("""
                                DELETE FROM audit_logs
                                WHERE timestamp < :cutoff_date
                            """)
                            delete_result = session.execute(delete_query, {"cutoff_date": cutoff_date.isoformat()})
                            result.audit_logs_deleted += delete_result.rowcount
                            logger.info(f"Deleted {delete_result.rowcount} audit logs older than {cutoff_date}")

                        elif policy.log_type == "query":
                            delete_query = text("""
                                DELETE FROM query_logs
                                WHERE timestamp < :cutoff_date
                            """)
                            delete_result = session.execute(delete_query, {"cutoff_date": cutoff_date.isoformat()})
                            result.query_logs_deleted += delete_result.rowcount
                            logger.info(f"Deleted {delete_result.rowcount} query logs older than {cutoff_date}")

                        elif policy.log_type == "access":
                            delete_query = text("""
                                DELETE FROM access_logs
                                WHERE timestamp < :cutoff_date
                            """)
                            delete_result = session.execute(delete_query, {"cutoff_date": cutoff_date.isoformat()})
                            result.access_logs_deleted += delete_result.rowcount
                            logger.info(f"Deleted {delete_result.rowcount} access logs older than {cutoff_date}")

                    except Exception as e:
                        error_msg = f"Error cleaning up {policy.log_type} logs: {e}"
                        logger.error(error_msg)
                        result.errors.append(error_msg)

                session.commit()

        except Exception as e:
            error_msg = f"Failed to apply retention policies: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            if hasattr(session, 'rollback'):
                session.rollback()

        result.end_time = datetime.utcnow()
        self._last_cleanup_time = datetime.utcnow()

        logger.info(f"Cleanup completed: {result.to_dict()}")
        return result

    async def cleanup_logs_before(
        self,
        log_type: str,
        before_date: datetime
    ) -> int:
        """清理指定日期之前的日志"""
        with db_manager.get_sync_session() as session:
            if log_type == "audit":
                delete_query = text("""
                    DELETE FROM audit_logs
                    WHERE timestamp < :before_date
                """)
            elif log_type == "query":
                delete_query = text("""
                    DELETE FROM query_logs
                    WHERE timestamp < :before_date
                """)
            elif log_type == "access":
                delete_query = text("""
                    DELETE FROM access_logs
                    WHERE timestamp < :before_date
                """)
            else:
                raise ValueError(f"Unknown log type: {log_type}")

            result = session.execute(delete_query, {"before_date": before_date.isoformat()})
            session.commit()

            deleted_count = result.rowcount
            logger.info(f"Deleted {deleted_count} {log_type} logs before {before_date}")
            return deleted_count

    async def get_cleanup_statistics(self) -> Dict[str, Any]:
        """获取清理统计信息"""
        with db_manager.get_sync_session() as session:
            # 获取各类型日志数量
            audit_count = session.execute(
                text("SELECT COUNT(*) FROM audit_logs")
            ).scalar()
            query_count = session.execute(
                text("SELECT COUNT(*) FROM query_logs")
            ).scalar()
            access_count = session.execute(
                text("SELECT COUNT(*) FROM access_logs")
            ).scalar()

            # 获取最旧日志时间
            oldest_audit = session.execute(
                text("SELECT MIN(timestamp) FROM audit_logs")
            ).scalar()
            oldest_query = session.execute(
                text("SELECT MIN(timestamp) FROM query_logs")
            ).scalar()
            oldest_access = session.execute(
                text("SELECT MIN(timestamp) FROM access_logs")
            ).scalar()

            return {
                "audit_logs": {
                    "count": audit_count,
                    "oldest_timestamp": oldest_audit if oldest_audit else None
                },
                "query_logs": {
                    "count": query_count,
                    "oldest_timestamp": oldest_query if oldest_query else None
                },
                "access_logs": {
                    "count": access_count,
                    "oldest_timestamp": oldest_access if oldest_access else None
                },
                "last_cleanup_time": self._last_cleanup_time.isoformat() if self._last_cleanup_time else None
            }


# 全局服务实例
log_cleanup_service = LogCleanupService()
