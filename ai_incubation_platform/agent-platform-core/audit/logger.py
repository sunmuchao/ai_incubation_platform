"""
审计日志记录器

提供审计日志的记录、查询和报告功能
"""

import asyncio
import logging
import json
import hashlib
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict
import time
import os

from .models import (
    AuditLog,
    AuditLogStatus,
    AuditResourceType,
    AuditQuery,
    AuditReport
)

logger = logging.getLogger(__name__)


@dataclass
class AuditConfig:
    """审计配置"""
    # 存储配置
    storage_type: str = "memory"  # memory/file/database
    storage_path: Optional[str] = None

    # 保留策略
    retention_days: int = 30
    max_entries: int = 100000

    # 日志级别
    log_level: str = "INFO"

    # 敏感字段
    sensitive_fields: List[str] = field(default_factory=lambda: [
        "password", "secret", "token", "api_key", "authorization"
    ])

    # 异步写入
    async_write: bool = True
    batch_size: int = 100
    flush_interval: float = 5.0

    # 项目标识
    project_id: Optional[str] = None


class AuditLogger:
    """
    统一审计日志记录器

    功能:
    - 自动记录敏感操作
    - 支持多项目隔离
    - 支持追溯查询
    - 支持报告生成
    """

    def __init__(self, config: Optional[AuditConfig] = None):
        """
        初始化审计日志记录器

        Args:
            config: 审计配置
        """
        self.config = config or AuditConfig()
        self.config.project_id = self.config.project_id or self._generate_project_id()

        # 内存存储
        self._logs: List[AuditLog] = []
        self._logs_by_id: Dict[str, AuditLog] = {}
        self._logs_by_trace: Dict[str, List[str]] = defaultdict(list)

        # 写入队列
        self._write_queue: asyncio.Queue = asyncio.Queue()
        self._flush_task: Optional[asyncio.Task] = None
        self._is_running = True

        # 回调
        self._on_write_callbacks: List[Callable[[AuditLog], None]] = []

        # 启动后台刷新任务
        if self.config.async_write:
            self._start_flush_task()

        logger.info(f"AuditLogger initialized (project_id={self.config.project_id})")

    def _generate_project_id(self) -> str:
        """生成项目 ID"""
        hostname = os.uname().nodename if hasattr(os, 'uname') else "localhost"
        return hashlib.md5(f"{hostname}_{time.time()}".encode()).hexdigest()[:12]

    def _start_flush_task(self) -> None:
        """启动后台刷新任务"""
        try:
            loop = asyncio.get_event_loop()
            self._flush_task = loop.create_task(self._flush_loop())
        except RuntimeError:
            # 没有事件循环时跳过
            pass

    async def _flush_loop(self) -> None:
        """后台刷新循环"""
        while self._is_running:
            await asyncio.sleep(self.config.flush_interval)
            await self._flush_logs()

    async def _flush_logs(self) -> None:
        """刷新日志"""
        while not self._write_queue.empty():
            try:
                log = await asyncio.wait_for(
                    self._write_queue.get(),
                    timeout=0.1
                )
                await self._write_log_internal(log)
            except asyncio.TimeoutError:
                break
            except Exception as e:
                logger.error(f"Failed to flush audit log: {e}")

    def _mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """脱敏敏感数据"""
        masked = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in self.config.sensitive_fields):
                masked[key] = "***REDACTED***"
            elif isinstance(value, dict):
                masked[key] = self._mask_sensitive_data(value)
            else:
                masked[key] = value
        return masked

    async def log(
        self,
        actor: str,
        action: str,
        resource: str,
        request: Optional[Dict] = None,
        response: Optional[Dict] = None,
        status: str = "success",
        trace_id: Optional[str] = None,
        resource_type: AuditResourceType = AuditResourceType.OTHER,
        actor_type: str = "user",
        actor_ip: Optional[str] = None,
        tenant_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None
    ) -> AuditLog:
        """
        记录审计日志

        Args:
            actor: 执行者 ID
            action: 操作类型
            resource: 资源标识
            request: 请求数据
            response: 响应数据
            status: 状态
            trace_id: 追踪 ID
            resource_type: 资源类型
            actor_type: 执行者类型
            actor_ip: 执行者 IP
            tenant_id: 租户 ID
            session_id: 会话 ID
            request_id: 请求 ID
            metadata: 元数据
            tags: 标签
            error_message: 错误消息
            error_code: 错误代码

        Returns:
            AuditLog: 审计日志记录
        """
        # 创建审计日志
        log = AuditLog(
            actor=actor,
            actor_type=actor_type,
            actor_ip=actor_ip,
            action=action,
            resource_type=resource_type,
            resource=resource,
            request=self._mask_sensitive_data(request or {}),
            response=self._mask_sensitive_data(response or {}),
            status=AuditLogStatus(status),
            trace_id=trace_id,
            tenant_id=tenant_id,
            session_id=session_id,
            request_id=request_id,
            metadata=metadata or {},
            tags=tags or [],
            error_message=error_message,
            error_code=error_code
        )

        # 计算请求哈希（用于大请求）
        if request:
            log.request_hash = hashlib.md5(
                json.dumps(log.request, sort_keys=True).encode()
            ).hexdigest()

        # 计算响应大小
        if response:
            log.response_size = len(str(response))

        # 存储
        self._logs.append(log)
        self._logs_by_id[log.id] = log
        if trace_id:
            self._logs_by_trace[trace_id].append(log.id)

        # 应用保留策略
        self._apply_retention()

        # 异步写入
        if self.config.async_write:
            await self._write_queue.put(log)
        else:
            await self._write_log_internal(log)

        # 触发回调
        for callback in self._on_write_callbacks:
            try:
                callback(log)
            except Exception as e:
                logger.error(f"Error in audit callback: {e}")

        return log

    async def _write_log_internal(self, log: AuditLog) -> None:
        """内部写入日志"""
        if self.config.storage_type == "file" and self.config.storage_path:
            await self._write_to_file(log)
        elif self.config.storage_type == "database":
            await self._write_to_database(log)
        else:
            # 内存存储已在上一步完成
            pass

    async def _write_to_file(self, log: AuditLog) -> None:
        """写入文件"""
        try:
            os.makedirs(self.config.storage_path, exist_ok=True)
            date_str = time.strftime("%Y-%m-%d", time.localtime(log.start_time))
            file_path = os.path.join(
                self.config.storage_path,
                f"audit_{date_str}.jsonl"
            )

            with open(file_path, "a") as f:
                f.write(json.dumps(log.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log to file: {e}")

    async def _write_to_database(self, log: AuditLog) -> None:
        """写入数据库"""
        # 由子类实现数据库写入
        logger.debug(f"Would write to database: {log.id}")

    def _apply_retention(self) -> None:
        """应用保留策略"""
        # 检查条目数量
        if len(self._logs) > self.config.max_entries:
            old_logs = self._logs[:len(self._logs) - self.config.max_entries]
            self._logs = self._logs[-self.config.max_entries:]
            for log in old_logs:
                if log.id in self._logs_by_id:
                    del self._logs_by_id[log.id]

        # 检查时间
        cutoff_time = time.time() - (self.config.retention_days * 86400)
        self._logs = [log for log in self._logs if log.start_time >= cutoff_time]

    async def query(self, query: Optional[AuditQuery] = None, **kwargs) -> List[AuditLog]:
        """
        查询审计日志

        Args:
            query: 查询条件
            **kwargs: 查询参数（直接传递）

        Returns:
            List[AuditLog]: 审计日志列表
        """
        if query is None:
            query = AuditQuery(**kwargs)

        # 过滤日志
        results = [log for log in self._logs if query.matches(log)]

        # 排序
        reverse = query.sort_desc
        if query.sort_by == "start_time":
            results.sort(key=lambda x: x.start_time, reverse=reverse)
        elif query.sort_by == "duration_ms":
            results.sort(key=lambda x: x.execution_time_ms, reverse=reverse)

        # 分页
        start = query.offset
        end = start + query.limit
        return results[start:end]

    async def get_by_id(self, log_id: str) -> Optional[AuditLog]:
        """根据 ID 获取日志"""
        return self._logs_by_id.get(log_id)

    async def get_by_trace(self, trace_id: str) -> List[AuditLog]:
        """根据追踪 ID 获取日志列表"""
        log_ids = self._logs_by_trace.get(trace_id, [])
        return [
            log for log_id in log_ids
            if (log := self._logs_by_id.get(log_id))
        ]

    async def generate_report(
        self,
        start_time: float,
        end_time: float,
        query: Optional[AuditQuery] = None
    ) -> AuditReport:
        """
        生成审计报告

        Args:
            start_time: 开始时间
            end_time: 结束时间
            query: 额外查询条件

        Returns:
            AuditReport: 审计报告
        """
        report = AuditReport(start_time=start_time, end_time=end_time)

        for log in self._logs:
            if start_time <= log.start_time <= end_time:
                if query is None or query.matches(log):
                    report.add_log(log)

        report.finalize()
        return report

    async def get_stats(
        self,
        time_range: Optional[tuple] = None
    ) -> Dict[str, Any]:
        """
        获取统计信息

        Args:
            time_range: 时间范围 (start, end)

        Returns:
            统计信息字典
        """
        logs = self._logs
        if time_range:
            logs = [log for log in logs if time_range[0] <= log.start_time <= time_range[1]]

        if not logs:
            return {"count": 0}

        success_count = sum(1 for log in logs if log.status == AuditLogStatus.SUCCESS)
        durations = [log.execution_time_ms for log in logs]

        return {
            "count": len(logs),
            "success_count": success_count,
            "failure_count": len(logs) - success_count,
            "success_rate": success_count / len(logs),
            "avg_duration_ms": sum(durations) / len(durations),
            "total_duration_ms": sum(durations)
        }

    def on_write(self, callback: Callable[[AuditLog], None]) -> None:
        """注册写入回调"""
        self._on_write_callbacks.append(callback)

    async def close(self) -> None:
        """关闭审计日志记录器"""
        self._is_running = False

        # 刷新剩余日志
        await self._flush_logs()

        # 取消后台任务
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        logger.info("AuditLogger closed")

    def clear(self) -> None:
        """清空所有日志"""
        self._logs.clear()
        self._logs_by_id.clear()
        self._logs_by_trace.clear()
        logger.info("Audit logs cleared")

    async def export_logs(
        self,
        format: str = "json",
        query: Optional[AuditQuery] = None
    ) -> str:
        """
        导出日志

        Args:
            format: 导出格式 (json/csv)
            query: 查询条件

        Returns:
            导出的内容
        """
        logs = await self.query(query) if query else self._logs

        if format == "json":
            return json.dumps([log.to_dict() for log in logs], indent=2)
        elif format == "csv":
            import csv
            import io

            output = io.StringIO()
            fieldnames = [
                "id", "actor", "action", "resource", "status",
                "start_time", "duration_ms", "trace_id"
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for log in logs:
                writer.writerow({
                    "id": log.id,
                    "actor": log.actor,
                    "action": log.action,
                    "resource": log.resource,
                    "status": log.status.value,
                    "start_time": log.start_time,
                    "duration_ms": log.execution_time_ms,
                    "trace_id": log.trace_id
                })
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")


# 全局默认实例
_default_audit_logger: Optional[AuditLogger] = None


def get_default_audit_logger() -> AuditLogger:
    """获取默认审计日志记录器"""
    global _default_audit_logger
    if _default_audit_logger is None:
        _default_audit_logger = AuditLogger()
    return _default_audit_logger


def set_default_audit_logger(logger: AuditLogger) -> None:
    """设置默认审计日志记录器"""
    global _default_audit_logger
    _default_audit_logger = logger
