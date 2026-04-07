"""
P5 AI 可观测性服务

提供:
- Agent 执行日志记录
- Token 消耗统计
- API 调用追踪
- 性能指标监控
- 工作日志自动生成
"""

import uuid
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from models.observability_models import (
    AgentExecutionDB, AgentLogDB, AgentMetricDB, AgentWorkLogDB,
    AgentExecutionStatus, LogLevel, StreamEventType, StreamEventDB
)
from models.db_models import AIEmployeeDB, OrderDB
from models.file_models import FileDB


class ObservabilityService:
    """AI 可观测性服务"""

    def __init__(self, db: Session):
        self.db = db

    # ============== Agent 执行追踪 ==============

    def create_execution(
        self,
        employee_id: str,
        task_description: str,
        tenant_id: str,
        user_id: str,
        order_id: Optional[str] = None,
        deerflow_task_id: Optional[str] = None
    ) -> AgentExecutionDB:
        """创建 Agent 执行记录"""
        execution_id = str(uuid.uuid4())

        execution = AgentExecutionDB(
            id=execution_id,
            employee_id=employee_id,
            order_id=order_id,
            tenant_id=tenant_id,
            user_id=user_id,
            task_description=task_description,
            execution_status=AgentExecutionStatus.PENDING,
            deerflow_task_id=deerflow_task_id
        )

        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)

        # 自动创建开始日志
        self.log_execution_event(
            execution_id=execution_id,
            tenant_id=tenant_id,
            level=LogLevel.INFO,
            message=f"开始执行任务：{task_description[:100]}...",
            category="execution"
        )

        return execution

    def start_execution(self, execution_id: str) -> AgentExecutionDB:
        """标记执行开始"""
        execution = self.db.query(AgentExecutionDB).filter(
            AgentExecutionDB.id == execution_id
        ).first()

        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        execution.execution_status = AgentExecutionStatus.RUNNING
        execution.start_time = datetime.utcnow()
        self.db.commit()
        self.db.refresh(execution)

        return execution

    def complete_execution(
        self,
        execution_id: str,
        result_summary: Optional[str] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        api_call_count: int = 0,
        external_api_calls: Optional[List[Dict]] = None,
        decision_tree: Optional[List[Dict]] = None,
        tool_calls: Optional[List[Dict]] = None,
        token_details: Optional[List[Dict]] = None
    ) -> AgentExecutionDB:
        """标记执行完成"""
        execution = self.db.query(AgentExecutionDB).filter(
            AgentExecutionDB.id == execution_id
        ).first()

        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        execution.execution_status = AgentExecutionStatus.COMPLETED
        execution.end_time = datetime.utcnow()
        execution.result_summary = result_summary
        execution.prompt_tokens = prompt_tokens
        execution.completion_tokens = completion_tokens
        execution.total_tokens = prompt_tokens + completion_tokens
        execution.api_call_count = api_call_count
        execution.external_api_calls = external_api_calls
        execution.decision_tree = decision_tree
        execution.tool_calls = tool_calls
        execution.token_details = token_details  # v1.1 新增：Token 明细

        # 计算耗时
        if execution.start_time:
            execution.duration_ms = int((execution.end_time - execution.start_time).total_seconds() * 1000)

        # 计算 Token 成本 (使用平均价格估算)
        execution.token_cost = (prompt_tokens * 0.000001 + completion_tokens * 0.000002)  # 假设价格

        # 更新进度为 100%
        execution.progress_percent = 100

        # 记录完成流式事件
        self.record_stream_event(
            execution_id=execution_id,
            tenant_id=execution.tenant_id,
            event_type=StreamEventType.EXECUTION_COMPLETE,
            event_data={
                "result_summary": result_summary,
                "total_tokens": execution.total_tokens,
                "duration_ms": execution.duration_ms
            },
            token_delta=completion_tokens,
            cumulative_tokens=execution.total_tokens
        )

        self.db.commit()
        self.db.refresh(execution)

        # 自动创建工作日志
        self._auto_create_work_log(execution)

        return execution

    def fail_execution(
        self,
        execution_id: str,
        error_message: str,
        error_stack: Optional[str] = None
    ) -> AgentExecutionDB:
        """标记执行失败"""
        execution = self.db.query(AgentExecutionDB).filter(
            AgentExecutionDB.id == execution_id
        ).first()

        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        execution.execution_status = AgentExecutionStatus.FAILED
        execution.end_time = datetime.utcnow()
        execution.error_message = error_message
        execution.error_stack = error_stack

        # 计算耗时
        if execution.start_time:
            execution.duration_ms = int((execution.end_time - execution.start_time).total_seconds() * 1000)

        self.db.commit()
        self.db.refresh(execution)

        # 记录错误日志
        self.log_execution_event(
            execution_id=execution_id,
            tenant_id=execution.tenant_id,
            level=LogLevel.ERROR,
            message=f"执行失败：{error_message}",
            category="error"
        )

        return execution

    def log_execution_event(
        self,
        execution_id: str,
        tenant_id: str,
        level: LogLevel,
        message: str,
        category: Optional[str] = None,
        round_id: Optional[str] = None,
        step_number: Optional[int] = None,
        context_data: Optional[Dict] = None
    ) -> AgentLogDB:
        """记录执行日志"""
        log = AgentLogDB(
            id=str(uuid.uuid4()),
            execution_id=execution_id,
            tenant_id=tenant_id,
            log_level=level,
            log_message=message,
            log_category=category,
            round_id=round_id,
            step_number=step_number,
            context_data=context_data
        )

        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    # ============== 流式事件追踪 (v1.1 新增) ==============

    def record_stream_event(
        self,
        execution_id: str,
        tenant_id: str,
        event_type: StreamEventType,
        event_data: Optional[Dict] = None,
        token_delta: int = 0,
        cumulative_tokens: int = 0
    ) -> StreamEventDB:
        """记录流式事件"""
        # 获取当前执行的事件数量
        event_count = self.db.query(StreamEventDB).filter(
            StreamEventDB.execution_id == execution_id
        ).count()

        stream_event = StreamEventDB(
            id=str(uuid.uuid4()),
            event_sequence=event_count + 1,
            execution_id=execution_id,
            tenant_id=tenant_id,
            event_type=event_type,
            event_data=event_data,
            token_delta=token_delta,
            cumulative_tokens=cumulative_tokens
        )

        self.db.add(stream_event)

        # 更新执行记录的 stream_events 字段（冗余存储，便于查询）
        execution = self.db.query(AgentExecutionDB).filter(
            AgentExecutionDB.id == execution_id
        ).first()
        if execution:
            if execution.stream_events is None:
                execution.stream_events = []
            execution.stream_events.append(stream_event.to_dict())

        self.db.commit()
        self.db.refresh(stream_event)
        return stream_event

    def update_execution_progress(
        self,
        execution_id: str,
        progress_percent: int,
        progress_message: Optional[str] = None
    ) -> AgentExecutionDB:
        """更新执行进度"""
        execution = self.db.query(AgentExecutionDB).filter(
            AgentExecutionDB.id == execution_id
        ).first()

        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        execution.progress_percent = min(100, max(0, progress_percent))

        # 记录进度更新事件
        self.record_stream_event(
            execution_id=execution_id,
            tenant_id=execution.tenant_id,
            event_type=StreamEventType.PROGRESS_UPDATE,
            event_data={
                "progress_percent": progress_percent,
                "message": progress_message
            }
        )

        self.db.commit()
        self.db.refresh(execution)
        return execution

    def record_token_usage(
        self,
        execution_id: str,
        tenant_id: str,
        step_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        model: Optional[str] = None,
        cost: float = 0.0
    ) -> Dict:
        """记录 Token 使用明细（v1.1 新增）"""
        execution = self.db.query(AgentExecutionDB).filter(
            AgentExecutionDB.id == execution_id
        ).first()

        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        # 创建 Token 明细记录
        token_detail = {
            "step": step_name,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "model": model,
            "cost": cost,
            "timestamp": datetime.utcnow().isoformat()
        }

        # 更新执行的 token_details
        if execution.token_details is None:
            execution.token_details = []
        execution.token_details.append(token_detail)

        # 更新总计
        execution.prompt_tokens += prompt_tokens
        execution.completion_tokens += completion_tokens
        execution.total_tokens += prompt_tokens + completion_tokens
        execution.token_cost += cost

        # 记录 Token 生成事件
        self.record_stream_event(
            execution_id=execution_id,
            tenant_id=tenant_id,
            event_type=StreamEventType.TOKEN_GENERATED,
            event_data=token_detail,
            token_delta=prompt_tokens + completion_tokens,
            cumulative_tokens=execution.total_tokens
        )

        self.db.commit()
        self.db.refresh(execution)
        return token_detail

    def start_execution_streaming(
        self,
        execution_id: str
    ) -> AgentExecutionDB:
        """标记执行开始并记录流式事件（v1.1 新增）"""
        execution = self.start_execution(execution_id)

        # 记录执行开始事件
        self.record_stream_event(
            execution_id=execution_id,
            tenant_id=execution.tenant_id,
            event_type=StreamEventType.EXECUTION_START,
            event_data={
                "task_description": execution.task_description
            }
        )

        return execution

    def get_stream_events(
        self,
        execution_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[StreamEventDB]:
        """获取流式事件列表"""
        return self.db.query(StreamEventDB).filter(
            StreamEventDB.execution_id == execution_id
        ).order_by(StreamEventDB.event_sequence.asc()).offset(offset).limit(limit).all()

    def record_metric(
        self,
        execution_id: str,
        tenant_id: str,
        metric_type: str,
        metric_name: str,
        metric_value: float,
        metric_unit: Optional[str] = None,
        dimensions: Optional[Dict] = None
    ) -> AgentMetricDB:
        """记录性能指标"""
        metric = AgentMetricDB(
            id=str(uuid.uuid4()),
            execution_id=execution_id,
            tenant_id=tenant_id,
            metric_type=metric_type,
            metric_name=metric_name,
            metric_value=metric_value,
            metric_unit=metric_unit,
            dimensions=dimensions
        )

        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)
        return metric

    # ============== 工作日志自动生成 ==============

    def _auto_create_work_log(self, execution: AgentExecutionDB) -> Optional[AgentWorkLogDB]:
        """根据执行记录自动创建工作日志"""
        if execution.execution_status != AgentExecutionStatus.COMPLETED:
            return None

        # 检查工作日志是否已存在
        existing_log = self.db.query(AgentWorkLogDB).filter(
            AgentWorkLogDB.execution_id == execution.id
        ).first()

        if existing_log:
            return existing_log

        # 获取关联订单
        order = None
        if execution.order_id:
            order = self.db.query(OrderDB).filter(OrderDB.id == execution.order_id).first()

        work_log = AgentWorkLogDB(
            id=str(uuid.uuid4()),
            employee_id=execution.employee_id,
            order_id=execution.order_id,
            execution_id=execution.id,
            tenant_id=execution.tenant_id,
            user_id=execution.user_id,
            session_id=execution.id,
            session_start_time=execution.start_time,
            session_end_time=execution.end_time,
            work_description=execution.result_summary or execution.task_description,
            work_type="task_execution",
            deliverables=execution.tool_calls,  # 将工具调用结果作为交付物
            time_spent_minutes=int(execution.duration_ms / 60000) if execution.duration_ms else 0,
            billable_time_minutes=int(execution.duration_ms / 60000) if execution.duration_ms else 0,
            is_submitted=True,  # 自动提交的日志
            is_auto_generated=True,
            auto_generate_source="execution_log"
        )

        self.db.add(work_log)
        self.db.commit()
        self.db.refresh(work_log)

        return work_log

    # ============== 查询统计 ==============

    def get_execution(self, execution_id: str) -> Optional[AgentExecutionDB]:
        """获取执行记录详情"""
        return self.db.query(AgentExecutionDB).filter(
            AgentExecutionDB.id == execution_id
        ).first()

    def list_executions(
        self,
        tenant_id: str,
        employee_id: Optional[str] = None,
        order_id: Optional[str] = None,
        status: Optional[AgentExecutionStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[AgentExecutionDB]:
        """列出执行记录"""
        query = self.db.query(AgentExecutionDB).filter(
            AgentExecutionDB.tenant_id == tenant_id
        )

        if employee_id:
            query = query.filter(AgentExecutionDB.employee_id == employee_id)
        if order_id:
            query = query.filter(AgentExecutionDB.order_id == order_id)
        if status:
            query = query.filter(AgentExecutionDB.execution_status == status)
        if start_date:
            query = query.filter(AgentExecutionDB.created_at >= start_date)
        if end_date:
            query = query.filter(AgentExecutionDB.created_at <= end_date)

        return query.order_by(
            AgentExecutionDB.created_at.desc()
        ).offset(offset).limit(limit).all()

    def get_execution_logs(
        self,
        execution_id: str,
        level: Optional[LogLevel] = None,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[AgentLogDB]:
        """获取执行日志"""
        query = self.db.query(AgentLogDB).filter(
            AgentLogDB.execution_id == execution_id
        )

        if level:
            query = query.filter(AgentLogDB.log_level == level)
        if category:
            query = query.filter(AgentLogDB.log_category == category)

        return query.order_by(AgentLogDB.created_at.asc()).limit(limit).all()

    def get_employee_stats(
        self,
        employee_id: str,
        tenant_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """获取员工统计信息"""
        start_date = datetime.utcnow() - timedelta(days=days)

        # 执行统计
        executions = self.db.query(AgentExecutionDB).filter(
            AgentExecutionDB.employee_id == employee_id,
            AgentExecutionDB.tenant_id == tenant_id,
            AgentExecutionDB.created_at >= start_date
        ).all()

        # 成功/失败统计
        completed_count = sum(1 for e in executions if e.execution_status == AgentExecutionStatus.COMPLETED)
        failed_count = sum(1 for e in executions if e.execution_status == AgentExecutionStatus.FAILED)

        # Token 统计
        total_tokens = sum(e.total_tokens for e in executions if e.total_tokens)
        total_prompt_tokens = sum(e.prompt_tokens for e in executions if e.prompt_tokens)
        total_completion_tokens = sum(e.completion_tokens for e in executions if e.completion_tokens)

        # 耗时统计
        durations = [e.duration_ms for e in executions if e.duration_ms]
        avg_duration = sum(durations) / len(durations) if durations else 0

        # 成本统计
        total_token_cost = sum(e.token_cost for e in executions if e.token_cost)

        return {
            "employee_id": employee_id,
            "period_days": days,
            "total_executions": len(executions),
            "completed_count": completed_count,
            "failed_count": failed_count,
            "success_rate": completed_count / len(executions) * 100 if executions else 0,
            "total_tokens": total_tokens,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "avg_duration_ms": avg_duration,
            "total_token_cost": total_token_cost,
        }

    def get_tenant_observability_dashboard(
        self,
        tenant_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """获取租户可观测性面板数据"""
        start_date = datetime.utcnow() - timedelta(days=days)

        # 获取所有执行
        executions = self.db.query(AgentExecutionDB).filter(
            AgentExecutionDB.tenant_id == tenant_id,
            AgentExecutionDB.created_at >= start_date
        ).all()

        # 按状态分组
        status_counts = defaultdict(int)
        for e in executions:
            status_counts[e.execution_status.value] += 1

        # 按员工分组统计
        employee_stats = defaultdict(lambda: {
            "executions": 0, "total_tokens": 0, "total_cost": 0, "avg_duration": 0
        })

        for e in executions:
            employee_stats[e.employee_id]["executions"] += 1
            employee_stats[e.employee_id]["total_tokens"] += e.total_tokens or 0
            employee_stats[e.employee_id]["total_cost"] += e.token_cost or 0
            if e.duration_ms:
                employee_stats[e.employee_id]["avg_duration"] += e.duration_ms

        # 计算平均耗时
        for emp_id in employee_stats:
            if employee_stats[emp_id]["executions"] > 0:
                employee_stats[emp_id]["avg_duration"] /= employee_stats[emp_id]["executions"]

        # Token 使用趋势 (按天)
        daily_tokens = defaultdict(int)
        for e in executions:
            if e.created_at:
                day_key = e.created_at.strftime("%Y-%m-%d")
                daily_tokens[day_key] += e.total_tokens or 0

        return {
            "tenant_id": tenant_id,
            "period_days": days,
            "total_executions": len(executions),
            "status_breakdown": dict(status_counts),
            "employee_stats": dict(employee_stats),
            "daily_token_usage": dict(daily_tokens),
            "total_tokens": sum(e.total_tokens or 0 for e in executions),
            "total_cost": sum(e.token_cost or 0 for e in executions),
        }

    def list_work_logs(
        self,
        tenant_id: str,
        employee_id: Optional[str] = None,
        order_id: Optional[str] = None,
        is_submitted: Optional[bool] = None,
        review_status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[AgentWorkLogDB]:
        """列出工作日志"""
        query = self.db.query(AgentWorkLogDB).filter(
            AgentWorkLogDB.tenant_id == tenant_id
        )

        if employee_id:
            query = query.filter(AgentWorkLogDB.employee_id == employee_id)
        if order_id:
            query = query.filter(AgentWorkLogDB.order_id == order_id)
        if is_submitted is not None:
            query = query.filter(AgentWorkLogDB.is_submitted == is_submitted)
        if review_status:
            query = query.filter(AgentWorkLogDB.review_status == review_status)

        return query.order_by(
            AgentWorkLogDB.created_at.desc()
        ).offset(offset).limit(limit).all()

    def submit_work_log(self, log_id: str, user_id: str) -> AgentWorkLogDB:
        """提交工作日志"""
        work_log = self.db.query(AgentWorkLogDB).filter(
            AgentWorkLogDB.id == log_id
        ).first()

        if not work_log:
            raise ValueError(f"Work log {log_id} not found")

        work_log.is_submitted = True
        work_log.submitted_at = datetime.utcnow()
        work_log.review_status = "pending"

        self.db.commit()
        self.db.refresh(work_log)

        return work_log

    def review_work_log(
        self,
        log_id: str,
        user_id: str,
        approved: bool,
        comments: Optional[str] = None
    ) -> AgentWorkLogDB:
        """审核工作日志"""
        work_log = self.db.query(AgentWorkLogDB).filter(
            AgentWorkLogDB.id == log_id
        ).first()

        if not work_log:
            raise ValueError(f"Work log {log_id} not found")

        work_log.is_reviewed = True
        work_log.review_status = "approved" if approved else "rejected"
        work_log.review_comments = comments
        work_log.reviewed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(work_log)

        return work_log


# 依赖注入
from config.database import get_db
from fastapi import Depends

def get_observability_service(db: Session):
    """获取可观测性服务实例"""
    return ObservabilityService(db)
