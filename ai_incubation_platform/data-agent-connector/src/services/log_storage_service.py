"""
日志持久化与审计服务

提供审计日志、查询日志、访问日志的存储、查询和清理功能
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import select, delete, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from models.audit_log import (
    AuditLogEntry, QueryLogEntry, AccessLogEntry,
    LogRetentionPolicy, LogExportJob, UserActivityReport,
    LogAnomaly, ComplianceReport
)
from config.database import db_manager, get_sync_db_session
from utils.logger import logger


class LogStorageService:
    """日志存储服务"""

    def __init__(self):
        self._buffer_size = 100
        self._audit_buffer: List[AuditLogEntry] = []
        self._query_buffer: List[QueryLogEntry] = []
        self._access_buffer: List[AccessLogEntry] = []
        self._flush_task: Optional[asyncio.Task] = None
        self._flush_interval = 5  # 秒
        self._default_retention_days = {
            "audit": 365,
            "query": 90,
            "access": 180
        }

    async def initialize(self):
        """初始化服务"""
        logger.info("Initializing log storage service")
        await self._ensure_retention_policies()
        # 启动定期刷新任务
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info("Log storage service initialized")

    async def close(self):
        """关闭服务"""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        # 刷新剩余日志
        await self._flush_logs()
        logger.info("Log storage service closed")

    async def _ensure_retention_policies(self):
        """确保默认保留策略存在"""
        with db_manager.get_sync_session() as session:
            for log_type, days in self._default_retention_days.items():
                result = session.execute(
                    text("SELECT id FROM log_retention_policies WHERE log_type = :log_type"),
                    {"log_type": log_type}
                )
                if not result.fetchone():
                    session.execute(
                        text("""
                            INSERT INTO log_retention_policies
                            (id, log_type, retention_days, storage_backend, compression_enabled, created_at, updated_at)
                            VALUES (:id, :log_type, :days, 'database', 1, :now, :now)
                        """),
                        {
                            "id": f"policy_{log_type}",
                            "log_type": log_type,
                            "days": days,
                            "now": datetime.utcnow().isoformat()
                        }
                    )
                    session.commit()

    async def _flush_loop(self):
        """定期刷新日志缓冲"""
        while True:
            try:
                await asyncio.sleep(self._flush_interval)
                await self._flush_logs()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error flushing logs: {e}")

    async def _flush_logs(self):
        """刷新缓冲区日志到数据库"""
        if not self._audit_buffer and not self._query_buffer and not self._access_buffer:
            return

        with db_manager.get_sync_session() as session:
            try:
                # 批量插入审计日志
                if self._audit_buffer:
                    for entry in self._audit_buffer:
                        session.execute(
                            text("""
                                INSERT INTO audit_logs
                                (id, timestamp, tenant_id, user_id, action_type, resource_type, resource_id,
                                 request_method, request_path, request_body, response_status, response_body,
                                 ip_address, user_agent, connector_name, query_id, metadata, created_at)
                                VALUES (:id, :timestamp, :tenant_id, :user_id, :action_type, :resource_type,
                                        :resource_id, :request_method, :request_path, :request_body,
                                        :response_status, :response_body, :ip_address, :user_agent,
                                        :connector_name, :query_id, :metadata, :created_at)
                            """),
                            entry.to_dict()
                        )
                    logger.info(f"Flushed {len(self._audit_buffer)} audit logs")
                    self._audit_buffer.clear()

                # 批量插入查询日志
                if self._query_buffer:
                    for entry in self._query_buffer:
                        session.execute(
                            text("""
                                INSERT INTO query_logs
                                (id, query_id, datasource, sql, connector_name, tenant_id, user_id,
                                 duration_ms, result_rows, status, error_message, rows_returned,
                                 bytes_processed, metadata, timestamp, created_at)
                                VALUES (:id, :query_id, :datasource, :sql, :connector_name, :tenant_id,
                                        :user_id, :duration_ms, :result_rows, :status, :error_message,
                                        :rows_returned, :bytes_processed, :metadata, :timestamp, :created_at)
                            """),
                            entry.to_dict()
                        )
                    logger.info(f"Flushed {len(self._query_buffer)} query logs")
                    self._query_buffer.clear()

                # 批量插入访问日志
                if self._access_buffer:
                    for entry in self._access_buffer:
                        session.execute(
                            text("""
                                INSERT INTO access_logs
                                (id, timestamp, tenant_id, user_id, resource, action, granted,
                                 reason, ip_address, metadata, created_at)
                                VALUES (:id, :timestamp, :tenant_id, :user_id, :resource, :action,
                                        :granted, :reason, :ip_address, :metadata, :created_at)
                            """),
                            entry.to_dict()
                        )
                    logger.info(f"Flushed {len(self._access_buffer)} access logs")
                    self._access_buffer.clear()

                session.commit()
            except Exception as e:
                logger.error(f"Failed to flush logs: {e}")
                session.rollback()
                raise

    async def store_audit_log(self, entry: AuditLogEntry):
        """存储审计日志"""
        self._audit_buffer.append(entry)
        if len(self._audit_buffer) >= self._buffer_size:
            await self._flush_logs()

    async def store_query_log(self, entry: QueryLogEntry):
        """存储查询日志"""
        self._query_buffer.append(entry)
        if len(self._query_buffer) >= self._buffer_size:
            await self._flush_logs()

    async def store_access_log(self, entry: AccessLogEntry):
        """存储访问日志"""
        self._access_buffer.append(entry)
        if len(self._access_buffer) >= self._buffer_size:
            await self._flush_logs()

    async def query_audit_logs(
        self,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        action_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[AuditLogEntry], int]:
        """查询审计日志"""
        with db_manager.get_sync_session() as session:
            conditions = ["1=1"]
            params = {}

            if tenant_id:
                conditions.append("tenant_id = :tenant_id")
                params["tenant_id"] = tenant_id
            if user_id:
                conditions.append("user_id = :user_id")
                params["user_id"] = user_id
            if action_type:
                conditions.append("action_type = :action_type")
                params["action_type"] = action_type
            if resource_type:
                conditions.append("resource_type = :resource_type")
                params["resource_type"] = resource_type
            if resource_id:
                conditions.append("resource_id = :resource_id")
                params["resource_id"] = resource_id
            if start_date:
                conditions.append("timestamp >= :start_date")
                params["start_date"] = start_date.isoformat()
            if end_date:
                conditions.append("timestamp <= :end_date")
                params["end_date"] = end_date.isoformat()

            where_clause = " AND ".join(conditions)

            # 获取总数
            count_query = text(f"SELECT COUNT(*) FROM audit_logs WHERE {where_clause}")
            total = session.execute(count_query, params).scalar()

            # 获取数据
            offset = (page - 1) * page_size
            data_query = text(f"""
                SELECT * FROM audit_logs
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT :limit OFFSET :offset
            """)
            params["limit"] = page_size
            params["offset"] = offset

            result = session.execute(data_query, params)
            rows = result.fetchall()

            logs = [AuditLogEntry.from_dict(dict(row._mapping)) for row in rows]
            return logs, total

    async def query_query_logs(
        self,
        datasource: Optional[str] = None,
        connector_name: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[QueryLogEntry], int]:
        """查询查询日志"""
        with db_manager.get_sync_session() as session:
            conditions = ["1=1"]
            params = {}

            if datasource:
                conditions.append("datasource = :datasource")
                params["datasource"] = datasource
            if connector_name:
                conditions.append("connector_name = :connector_name")
                params["connector_name"] = connector_name
            if status:
                conditions.append("status = :status")
                params["status"] = status
            if start_date:
                conditions.append("timestamp >= :start_date")
                params["start_date"] = start_date.isoformat()
            if end_date:
                conditions.append("timestamp <= :end_date")
                params["end_date"] = end_date.isoformat()

            where_clause = " AND ".join(conditions)

            # 获取总数
            count_query = text(f"SELECT COUNT(*) FROM query_logs WHERE {where_clause}")
            total = session.execute(count_query, params).scalar()

            # 获取数据
            offset = (page - 1) * page_size
            data_query = text(f"""
                SELECT * FROM query_logs
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT :limit OFFSET :offset
            """)
            params["limit"] = page_size
            params["offset"] = offset

            result = session.execute(data_query, params)
            rows = result.fetchall()

            logs = [QueryLogEntry.from_dict(dict(row._mapping)) for row in rows]
            return logs, total

    async def query_access_logs(
        self,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        granted: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[AccessLogEntry], int]:
        """查询访问日志"""
        with db_manager.get_sync_session() as session:
            conditions = ["1=1"]
            params = {}

            if tenant_id:
                conditions.append("tenant_id = :tenant_id")
                params["tenant_id"] = tenant_id
            if user_id:
                conditions.append("user_id = :user_id")
                params["user_id"] = user_id
            if granted is not None:
                conditions.append("granted = :granted")
                params["granted"] = 1 if granted else 0
            if start_date:
                conditions.append("timestamp >= :start_date")
                params["start_date"] = start_date.isoformat()
            if end_date:
                conditions.append("timestamp <= :end_date")
                params["end_date"] = end_date.isoformat()

            where_clause = " AND ".join(conditions)

            # 获取总数
            count_query = text(f"SELECT COUNT(*) FROM access_logs WHERE {where_clause}")
            total = session.execute(count_query, params).scalar()

            # 获取数据
            offset = (page - 1) * page_size
            data_query = text(f"""
                SELECT * FROM access_logs
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT :limit OFFSET :offset
            """)
            params["limit"] = page_size
            params["offset"] = offset

            result = session.execute(data_query, params)
            rows = result.fetchall()

            logs = [AccessLogEntry.from_dict(dict(row._mapping)) for row in rows]
            return logs, total

    async def get_retention_policies(self) -> List[LogRetentionPolicy]:
        """获取所有保留策略"""
        with db_manager.get_sync_session() as session:
            result = session.execute(text("SELECT * FROM log_retention_policies"))
            rows = result.fetchall()
            return [LogRetentionPolicy.from_dict(dict(row._mapping)) for row in rows]

    async def update_retention_policy(self, policy: LogRetentionPolicy):
        """更新保留策略"""
        with db_manager.get_sync_session() as session:
            session.execute(
                text("""
                    INSERT OR REPLACE INTO log_retention_policies
                    (id, log_type, retention_days, storage_backend, compression_enabled,
                     export_enabled, export_destination, created_at, updated_at)
                    VALUES (:id, :log_type, :retention_days, :storage_backend, :compression_enabled,
                            :export_enabled, :export_destination, :created_at, :updated_at)
                """),
                policy.to_dict()
            )
            session.commit()


# 全局服务实例
log_storage_service = LogStorageService()
