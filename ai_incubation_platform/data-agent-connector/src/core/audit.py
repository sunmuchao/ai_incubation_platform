"""
审计日志模块
记录所有查询操作，支持事后审计和追踪
"""
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
from utils.logger import logger, request_id_var, user_id_var
from config.settings import settings


class AuditLogEntry:
    """审计日志条目"""

    def __init__(
        self,
        operation_type: str,
        connector_name: str,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        error_code: str = "",
        execution_time_ms: float = 0,
        rows_returned: int = 0,
        user_id: Optional[str] = None,
        role: str = "read_only"
    ):
        self.timestamp = datetime.utcnow()
        self.request_id = request_id_var.get()
        self.user_id = user_id or user_id_var.get()
        self.operation_type = operation_type
        self.connector_name = connector_name
        self.query = query if settings.audit.log_sensitive_data else self._mask_sensitive_data(query)
        self.params = params if settings.audit.log_sensitive_data else None
        self.success = success
        self.error_message = error_message
        self.error_code = error_code
        self.execution_time_ms = execution_time_ms
        self.rows_returned = rows_returned
        self.role = role

    def _mask_sensitive_data(self, query: str) -> str:
        """掩码敏感数据"""
        # 简单实现，实际可根据需要扩展
        import re
        # 掩码密码相关字段
        query = re.sub(r"\b(password|passwd|secret|token)\s*=\s*'[^']*'", r"\1='***'", query, flags=re.IGNORECASE)
        query = re.sub(r'\b(password|passwd|secret|token)\s*=\s*"[^"]*"', r'\1="***"', query, flags=re.IGNORECASE)
        return query

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "request_id": self.request_id,
            "user_id": self.user_id,
            "operation_type": self.operation_type,
            "connector_name": self.connector_name,
            "query": self.query,
            "params": self.params,
            "success": self.success,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "execution_time_ms": self.execution_time_ms,
            "rows_returned": self.rows_returned,
            "role": self.role
        }


class AuditLogger:
    """审计日志记录器"""

    def __init__(self):
        self._enabled = settings.audit.enabled
        self._log_queue: Optional[asyncio.Queue] = None
        self._worker_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """启动审计日志工作线程"""
        if self._enabled and self._worker_task is None:
            # 延迟到启动时创建队列，确保使用正确的事件循环
            self._log_queue = asyncio.Queue()
            self._worker_task = asyncio.create_task(self._worker())
            logger.info("Audit logger started")

    async def stop(self) -> None:
        """停止审计日志工作线程"""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
            logger.info("Audit logger stopped")

    async def log(self, entry: AuditLogEntry) -> None:
        """记录审计日志"""
        if not self._enabled or not settings.audit.log_all_queries or self._log_queue is None:
            return

        await self._log_queue.put(entry)

    async def _worker(self) -> None:
        """后台工作线程处理日志队列"""
        while True:
            try:
                entry = await self._log_queue.get()
                # 记录到日志系统
                logger.info(
                    "AUDIT: " + entry.operation_type,
                    extra=entry.to_dict()
                )
                self._log_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in audit logger worker: {e}")
                await asyncio.sleep(1)


# 全局审计日志实例
audit_logger = AuditLogger()
