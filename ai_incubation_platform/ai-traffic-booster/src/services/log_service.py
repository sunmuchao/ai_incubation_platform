"""
日志持久化服务 - P0 日志持久化

功能:
1. 将关键日志写入数据库
2. 支持日志查询和过滤
3. 支持日志统计和分析
4. 为告警系统提供数据源
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import desc, and_, or_
from sqlalchemy.orm import Session

from db.postgresql_models import SystemLogModel, LogLevelEnum
from db.postgresql_config import get_db_session


class LogService:
    """日志持久化服务"""

    def __init__(self, db_session: Optional[Session] = None):
        """
        初始化日志服务

        Args:
            db_session: 数据库会话，不指定则自动创建
        """
        self._db_session = db_session
        self._logger = logging.getLogger(__name__)

    @property
    def db_session(self) -> Session:
        """获取数据库会话"""
        if self._db_session is None:
            return next(get_db_session())
        return self._db_session

    def log(
        self,
        level: str,
        message: str,
        logger_name: Optional[str] = None,
        trace_id: Optional[str] = None,
        module: Optional[str] = None,
        function: Optional[str] = None,
        line_number: Optional[int] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        exception_type: Optional[str] = None,
        exception_message: Optional[str] = None,
        exception_traceback: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> Optional[SystemLogModel]:
        """
        记录日志到数据库

        Args:
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: 日志消息
            logger_name: 日志器名称
            trace_id: 追踪 ID
            module: 模块名
            function: 函数名
            line_number: 行号
            extra_data: 额外结构化数据
            request_id: 请求 ID
            exception_type: 异常类型
            exception_message: 异常消息
            exception_traceback: 异常堆栈
            duration_ms: 操作耗时 (毫秒)

        Returns:
            SystemLogModel: 创建的日志记录，失败返回 None
        """
        try:
            # 日志级别转换
            level_enum = LogLevelEnum(level.upper()) if level else LogLevelEnum.INFO

            # 创建日志记录
            log_entry = SystemLogModel(
                level=level_enum,
                message=message,
                logger_name=logger_name,
                trace_id=trace_id,
                module=module,
                function=function,
                line_number=line_number,
                extra_data=extra_data or {},
                request_id=request_id,
                exception_type=exception_type,
                exception_message=exception_message,
                exception_traceback=exception_traceback,
                duration_ms=duration_ms,
            )

            self.db_session.add(log_entry)
            self.db_session.commit()
            self.db_session.refresh(log_entry)

            return log_entry

        except Exception as e:
            # 日志记录失败不应影响主流程
            self._logger.error(f"Failed to persist log: {e}")
            return None
        finally:
            if self._db_session is None:
                self.db_session.close()

    def log_error(
        self,
        message: str,
        exception: Exception,
        **kwargs
    ) -> Optional[SystemLogModel]:
        """快捷记录错误日志"""
        return self.log(
            level="ERROR",
            message=message,
            exception_type=type(exception).__name__,
            exception_message=str(exception),
            exception_traceback=self._get_traceback(exception),
            **kwargs
        )

    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        request_id: str,
        trace_id: Optional[str] = None,
        **kwargs
    ) -> Optional[SystemLogModel]:
        """快捷记录请求日志"""
        return self.log(
            level="INFO",
            message=f"{method} {path} - {status_code}",
            logger_name="http.request",
            trace_id=trace_id,
            request_id=request_id,
            duration_ms=duration_ms,
            extra_data={"method": method, "path": path, "status_code": status_code, **kwargs},
        )

    def log_ai_analysis(
        self,
        analysis_type: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        model_name: str,
        duration_ms: float,
        trace_id: Optional[str] = None,
        **kwargs
    ) -> Optional[SystemLogModel]:
        """快捷记录 AI 分析日志"""
        return self.log(
            level="INFO",
            message=f"AI Analysis: {analysis_type}",
            logger_name="ai.analysis",
            trace_id=trace_id,
            module=analysis_type,
            extra_data={
                "analysis_type": analysis_type,
                "input_summary": self._summarize_dict(input_data),
                "output_summary": self._summarize_dict(output_data),
                "model_name": model_name,
            },
            duration_ms=duration_ms,
            **kwargs
        )

    def log_alert_trigger(
        self,
        alert_name: str,
        alert_type: str,
        trigger_value: float,
        threshold: float,
        severity: str,
        trace_id: Optional[str] = None,
        **kwargs
    ) -> Optional[SystemLogModel]:
        """快捷记录告警触发日志"""
        return self.log(
            level="WARNING" if severity in ["warning", "error"] else "INFO",
            message=f"Alert triggered: {alert_name} ({alert_type})",
            logger_name="alert.trigger",
            trace_id=trace_id,
            extra_data={
                "alert_name": alert_name,
                "alert_type": alert_type,
                "trigger_value": trigger_value,
                "threshold": threshold,
                "severity": severity,
            },
            **kwargs
        )

    def get_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        level: Optional[str] = None,
        logger_name: Optional[str] = None,
        trace_id: Optional[str] = None,
        request_id: Optional[str] = None,
        search_keyword: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> List[SystemLogModel]:
        """
        查询日志

        Args:
            start_time: 开始时间
            end_time: 结束时间
            level: 日志级别过滤
            logger_name: 日志器名称过滤
            trace_id: 追踪 ID 过滤
            request_id: 请求 ID 过滤
            search_keyword: 关键词搜索
            offset: 偏移量
            limit: 限制数量

        Returns:
            List[SystemLogModel]: 日志列表
        """
        query = self.db_session.query(SystemLogModel)

        # 时间范围过滤
        if start_time:
            query = query.filter(SystemLogModel.created_at >= start_time)
        if end_time:
            query = query.filter(SystemLogModel.created_at <= end_time)

        # 级别过滤
        if level:
            level_enum = LogLevelEnum(level.upper())
            query = query.filter(SystemLogModel.level == level_enum)

        # 其他过滤
        if logger_name:
            query = query.filter(SystemLogModel.logger_name == logger_name)
        if trace_id:
            query = query.filter(SystemLogModel.trace_id == trace_id)
        if request_id:
            query = query.filter(SystemLogModel.request_id == request_id)

        # 关键词搜索
        if search_keyword:
            query = query.filter(
                or_(
                    SystemLogModel.message.ilike(f"%{search_keyword}%"),
                    SystemLogModel.module.ilike(f"%{search_keyword}%"),
                )
            )

        # 排序和分页
        query = query.order_by(desc(SystemLogModel.created_at))
        query = query.offset(offset).limit(limit)

        return query.all()

    def get_error_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[SystemLogModel]:
        """获取错误日志"""
        if start_time is None:
            start_time = datetime.utcnow() - timedelta(hours=24)

        return self.get_logs(
            start_time=start_time,
            end_time=end_time,
            level="ERROR",
            limit=limit,
        )

    def get_log_stats(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        group_by: str = "level",
    ) -> Dict[str, Any]:
        """
        获取日志统计

        Args:
            start_time: 开始时间
            end_time: 结束时间
            group_by: 分组维度 (level, logger_name, module)

        Returns:
            Dict[str, Any]: 统计数据
        """
        if start_time is None:
            start_time = datetime.utcnow() - timedelta(hours=24)

        query = self.db_session.query(SystemLogModel)
        query = query.filter(SystemLogModel.created_at >= start_time)
        if end_time:
            query = query.filter(SystemLogModel.created_at <= end_time)

        logs = query.all()

        stats = {
            "total_count": len(logs),
            "by_level": {},
            "by_module": {},
            "error_rate": 0.0,
            "avg_duration_ms": 0.0,
        }

        # 按级别统计
        for log in logs:
            level_key = log.level.value if hasattr(log.level, 'value') else str(log.level)
            stats["by_level"][level_key] = stats["by_level"].get(level_key, 0) + 1

        # 按模块统计
        for log in logs:
            module_key = log.module or "unknown"
            stats["by_module"][module_key] = stats["by_module"].get(module_key, 0) + 1

        # 计算错误率
        error_count = stats["by_level"].get("ERROR", 0) + stats["by_level"].get("CRITICAL", 0)
        if stats["total_count"] > 0:
            stats["error_rate"] = error_count / stats["total_count"]

        # 计算平均耗时
        durations = [log.duration_ms for log in logs if log.duration_ms is not None]
        if durations:
            stats["avg_duration_ms"] = sum(durations) / len(durations)

        return stats

    def get_trace_logs(self, trace_id: str) -> List[SystemLogModel]:
        """获取指定追踪 ID 的完整日志链"""
        return self.get_logs(trace_id=trace_id, limit=1000)

    def cleanup_old_logs(
        self,
        retention_days: int = 30,
        batch_size: int = 1000,
    ) -> int:
        """
        清理过期日志

        Args:
            retention_days: 保留天数
            batch_size: 批量删除数量

        Returns:
            int: 删除的日志数量
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        deleted_count = 0
        while True:
            # 批量查询
            old_logs = (
                self.db_session.query(SystemLogModel)
                .filter(SystemLogModel.created_at < cutoff_date)
                .limit(batch_size)
                .all()
            )

            if not old_logs:
                break

            # 批量删除
            for log in old_logs:
                self.db_session.delete(log)
            self.db_session.commit()

            deleted_count += len(old_logs)

            # 如果少于 batch_size，说明已清理完成
            if len(old_logs) < batch_size:
                break

        return deleted_count

    @staticmethod
    def _get_traceback(exception: Exception) -> str:
        """获取异常堆栈"""
        import traceback
        return "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))

    @staticmethod
    def _summarize_dict(data: Dict[str, Any], max_length: int = 500) -> str:
        """简化字典数据用于日志摘要"""
        import json
        try:
            serialized = json.dumps(data, default=str, ensure_ascii=False)
            return serialized[:max_length] + ("..." if len(serialized) > max_length else "")
        except:
            return str(data)[:max_length]


# 全局日志服务实例
_log_service: Optional[LogService] = None


def get_log_service() -> LogService:
    """获取全局日志服务实例"""
    global _log_service
    if _log_service is None:
        _log_service = LogService()
    return _log_service


def init_log_service(db_session: Optional[Session] = None) -> LogService:
    """初始化日志服务"""
    global _log_service
    _log_service = LogService(db_session)
    return _log_service
