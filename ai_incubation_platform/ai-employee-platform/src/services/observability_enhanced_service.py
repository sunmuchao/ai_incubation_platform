"""
P5 AI 可观测性服务增强 - 实时追踪与性能监控

提供:
- WebSocket 实时执行追踪
- Token 消耗分析
- 决策树可视化数据
- 性能指标聚合
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from collections import defaultdict
import json

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from models.observability_models import (
    AgentExecutionDB, AgentLogDB, AgentMetricDB, StreamEventDB,
    AgentExecutionStatus, LogLevel, StreamEventType
)


class ObservabilityEnhancedService:
    """AI 可观测性增强服务"""

    def __init__(self, db: Session):
        self.db = db

    # ============== 实时执行追踪 (WebSocket 支持) ==============

    def get_realtime_execution_status(self, execution_id: str, tenant_id: str) -> Dict[str, Any]:
        """获取实时执行状态"""
        execution = self.db.query(AgentExecutionDB).filter(
            AgentExecutionDB.id == execution_id,
            AgentExecutionDB.tenant_id == tenant_id
        ).first()

        if not execution:
            return None

        # 获取最近的流式事件
        recent_events = self.db.query(StreamEventDB).filter(
            StreamEventDB.execution_id == execution_id
        ).order_by(desc(StreamEventDB.created_at)).limit(5).all()

        return {
            "execution_id": execution.id,
            "employee_id": execution.employee_id,
            "status": execution.execution_status.value,
            "progress_percent": execution.progress_percent,
            "start_time": execution.start_time.isoformat() if execution.start_time else None,
            "duration_ms": execution.duration_ms,
            "token_usage": {
                "prompt_tokens": execution.prompt_tokens,
                "completion_tokens": execution.completion_tokens,
                "total_tokens": execution.total_tokens,
                "cost": execution.token_cost
            },
            "recent_events": [e.to_dict() for e in recent_events]
        }

    def subscribe_execution_updates(self, execution_id: str) -> Dict[str, Any]:
        """订阅执行更新 (返回订阅信息)"""
        return {
            "subscription_id": str(uuid.uuid4()),
            "execution_id": execution_id,
            "channels": [
                f"execution:{execution_id}:status",
                f"execution:{execution_id}:progress",
                f"execution:{execution_id}:events"
            ]
        }

    # ============== Token 消耗分析 ==============

    def analyze_token_usage(
        self,
        employee_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """分析 Token 使用情况"""
        start_date = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(AgentExecutionDB).filter(
            AgentExecutionDB.created_at >= start_date
        )

        if employee_id:
            query = query.filter(AgentExecutionDB.employee_id == employee_id)
        if tenant_id:
            query = query.filter(AgentExecutionDB.tenant_id == tenant_id)

        executions = query.all()

        # 按天统计 Token 使用
        daily_stats = defaultdict(lambda: {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost": 0.0,
            "executions": 0
        })

        # 按模型统计 (从 token_details 中提取)
        model_stats = defaultdict(lambda: {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost": 0.0
        })

        # 按步骤统计
        step_stats = defaultdict(lambda: {
            "count": 0,
            "total_tokens": 0,
            "avg_tokens": 0,
            "cost": 0.0
        })

        total_tokens = 0
        total_cost = 0.0

        for e in executions:
            if e.created_at:
                day_key = e.created_at.strftime("%Y-%m-%d")
                daily_stats[day_key]["prompt_tokens"] += e.prompt_tokens or 0
                daily_stats[day_key]["completion_tokens"] += e.completion_tokens or 0
                daily_stats[day_key]["total_tokens"] += e.total_tokens or 0
                daily_stats[day_key]["cost"] += e.token_cost or 0.0
                daily_stats[day_key]["executions"] += 1

                total_tokens += e.total_tokens or 0
                total_cost += e.token_cost or 0.0

                # 解析 token_details
                if e.token_details:
                    for detail in e.token_details:
                        model = detail.get("model", "unknown")
                        step = detail.get("step", "unknown")
                        tokens = detail.get("total_tokens", 0)
                        cost = detail.get("cost", 0.0)

                        model_stats[model]["prompt_tokens"] += detail.get("prompt_tokens", 0)
                        model_stats[model]["completion_tokens"] += detail.get("completion_tokens", 0)
                        model_stats[model]["total_tokens"] += tokens
                        model_stats[model]["cost"] += cost

                        step_stats[step]["count"] += 1
                        step_stats[step]["total_tokens"] += tokens
                        step_stats[step]["cost"] += cost

        # 计算步骤平均值
        for step in step_stats:
            if step_stats[step]["count"] > 0:
                step_stats[step]["avg_tokens"] = step_stats[step]["total_tokens"] / step_stats[step]["count"]

        # Token 使用趋势
        token_trend = [
            {
                "date": date,
                "total_tokens": stats["total_tokens"],
                "cost": stats["cost"],
                "executions": stats["executions"]
            }
            for date, stats in sorted(daily_stats.items())
        ]

        # Top 消耗步骤
        top_steps = sorted(
            [
                {"step": step, **stats}
                for step, stats in step_stats.items()
            ],
            key=lambda x: x["total_tokens"],
            reverse=True
        )[:10]

        return {
            "period_days": days,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "total_executions": len(executions),
            "daily_usage": token_trend,
            "model_breakdown": dict(model_stats),
            "step_breakdown": step_stats,
            "top_steps": top_steps
        }

    # ============== 决策树可视化 ==============

    def get_decision_tree(self, execution_id: str, tenant_id: str) -> Dict[str, Any]:
        """获取决策树可视化数据"""
        execution = self.db.query(AgentExecutionDB).filter(
            AgentExecutionDB.id == execution_id,
            AgentExecutionDB.tenant_id == tenant_id
        ).first()

        if not execution:
            return None

        # 从执行记录中获取决策树
        decision_tree = execution.decision_tree
        if not decision_tree:
            # 如果没有决策树，尝试从日志中构建
            decision_tree = self._build_decision_tree_from_logs(execution_id)

        return {
            "execution_id": execution_id,
            "employee_id": execution.employee_id,
            "task_description": execution.task_description,
            "decision_tree": decision_tree,
            "tool_calls": execution.tool_calls,
            "total_decisions": len(decision_tree) if decision_tree else 0
        }

    def _build_decision_tree_from_logs(self, execution_id: str) -> List[Dict]:
        """从日志构建决策树"""
        logs = self.db.query(AgentLogDB).filter(
            AgentLogDB.execution_id == execution_id,
            AgentLogDB.log_category == "decision"
        ).order_by(AgentLogDB.created_at).all()

        decision_tree = []
        for log in logs:
            decision_tree.append({
                "step": log.step_number or 0,
                "decision": log.log_message,
                "context": log.context_data,
                "timestamp": log.created_at.isoformat() if log.created_at else None
            })

        return decision_tree

    # ============== 性能指标聚合 ==============

    def get_performance_metrics(
        self,
        employee_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """获取性能指标聚合数据"""
        start_date = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(AgentExecutionDB).filter(
            AgentExecutionDB.created_at >= start_date
        )

        if employee_id:
            query = query.filter(AgentExecutionDB.employee_id == employee_id)
        if tenant_id:
            query = query.filter(AgentExecutionDB.tenant_id == tenant_id)

        executions = query.all()

        # 性能指标统计
        total_count = len(executions)
        completed_count = sum(1 for e in executions if e.execution_status == AgentExecutionStatus.COMPLETED)
        failed_count = sum(1 for e in executions if e.execution_status == AgentExecutionStatus.FAILED)

        # 耗时统计
        durations = [e.duration_ms for e in executions if e.duration_ms]
        avg_duration = sum(durations) / len(durations) if durations else 0
        min_duration = min(durations) if durations else 0
        max_duration = max(durations) if durations else 0

        # 成功率
        success_rate = (completed_count / total_count * 100) if total_count > 0 else 0

        # 按状态分组
        status_breakdown = defaultdict(int)
        for e in executions:
            status_breakdown[e.execution_status.value] += 1

        # 按天统计性能
        daily_metrics = defaultdict(lambda: {
            "executions": 0,
            "success_count": 0,
            "failed_count": 0,
            "total_duration": 0,
            "total_tokens": 0
        })

        for e in executions:
            if e.created_at:
                day_key = e.created_at.strftime("%Y-%m-%d")
                daily_metrics[day_key]["executions"] += 1
                if e.execution_status == AgentExecutionStatus.COMPLETED:
                    daily_metrics[day_key]["success_count"] += 1
                elif e.execution_status == AgentExecutionStatus.FAILED:
                    daily_metrics[day_key]["failed_count"] += 1
                daily_metrics[day_key]["total_duration"] += e.duration_ms or 0
                daily_metrics[day_key]["total_tokens"] += e.total_tokens or 0

        # 计算每日平均耗时
        for day, metrics in daily_metrics.items():
            if metrics["executions"] > 0:
                metrics["avg_duration"] = metrics["total_duration"] / metrics["executions"]
            else:
                metrics["avg_duration"] = 0

        return {
            "period_days": days,
            "total_executions": total_count,
            "completed_count": completed_count,
            "failed_count": failed_count,
            "success_rate": success_rate,
            "duration_stats": {
                "avg_ms": avg_duration,
                "min_ms": min_duration,
                "max_ms": max_duration
            },
            "status_breakdown": dict(status_breakdown),
            "daily_metrics": dict(daily_metrics)
        }

    # ============== 错误分析 ==============

    def analyze_errors(
        self,
        employee_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """分析错误情况"""
        start_date = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(AgentExecutionDB).filter(
            AgentExecutionDB.created_at >= start_date,
            AgentExecutionDB.execution_status == AgentExecutionStatus.FAILED
        )

        if employee_id:
            query = query.filter(AgentExecutionDB.employee_id == employee_id)
        if tenant_id:
            query = query.filter(AgentExecutionDB.tenant_id == tenant_id)

        failed_executions = query.all()

        # 按错误类型分组
        error_patterns = defaultdict(list)
        for e in failed_executions:
            error_key = e.error_message[:100] if e.error_message else "Unknown Error"
            error_patterns[error_key].append({
                "execution_id": e.id,
                "employee_id": e.employee_id,
                "timestamp": e.created_at.isoformat() if e.created_at else None,
                "error_message": e.error_message,
                "error_stack": e.error_stack
            })

        # 错误趋势
        error_trend = defaultdict(int)
        for e in failed_executions:
            if e.created_at:
                day_key = e.created_at.strftime("%Y-%m-%d")
                error_trend[day_key] += 1

        return {
            "period_days": days,
            "total_errors": len(failed_executions),
            "error_patterns": {
                k: {
                    "count": len(v),
                    "latest": v[0] if v else None,
                    "sample_message": v[0]["error_message"] if v else None
                }
                for k, v in error_patterns.items()
            },
            "error_trend": dict(error_trend)
        }

    # ============== 实时事件推送辅助 ==============

    def get_execution_event_stream(
        self,
        execution_id: str,
        tenant_id: str,
        since_sequence: int = 0
    ) -> List[Dict]:
        """获取执行事件流 (用于 WebSocket 推送)"""
        events = self.db.query(StreamEventDB).filter(
            StreamEventDB.execution_id == execution_id,
            StreamEventDB.event_sequence > since_sequence
        ).order_by(StreamEventDB.event_sequence.asc()).all()

        return [e.to_dict() for e in events]

    # ============== 可观测性面板数据 ==============

    def get_enhanced_dashboard(
        self,
        tenant_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """获取增强型可观测性面板数据"""
        # 基础统计
        base_stats = self._get_base_stats(tenant_id, days)

        # Token 分析
        token_analysis = self.analyze_token_usage(tenant_id=tenant_id, days=days)

        # 性能指标
        performance = self.get_performance_metrics(tenant_id=tenant_id, days=days)

        # 错误分析
        errors = self.analyze_errors(tenant_id=tenant_id, days=days)

        # 实时执行
        running_executions = self.db.query(AgentExecutionDB).filter(
            AgentExecutionDB.tenant_id == tenant_id,
            AgentExecutionDB.execution_status == AgentExecutionStatus.RUNNING
        ).limit(10).all()

        # Top AI 员工
        top_employees = self._get_top_employees(tenant_id, days)

        return {
            "tenant_id": tenant_id,
            "period_days": days,
            "overview": base_stats,
            "token_analysis": token_analysis,
            "performance": performance,
            "errors": errors,
            "running_executions": [
                {
                    "id": e.id,
                    "employee_id": e.employee_id,
                    "task_description": e.task_description[:100],
                    "progress_percent": e.progress_percent,
                    "start_time": e.start_time.isoformat() if e.start_time else None
                }
                for e in running_executions
            ],
            "top_employees": top_employees
        }

    def _get_base_stats(self, tenant_id: str, days: int) -> Dict[str, Any]:
        """获取基础统计"""
        start_date = datetime.utcnow() - timedelta(days=days)

        executions = self.db.query(AgentExecutionDB).filter(
            AgentExecutionDB.tenant_id == tenant_id,
            AgentExecutionDB.created_at >= start_date
        ).all()

        completed = sum(1 for e in executions if e.execution_status == AgentExecutionStatus.COMPLETED)
        failed = sum(1 for e in executions if e.execution_status == AgentExecutionStatus.FAILED)
        running = sum(1 for e in executions if e.execution_status == AgentExecutionStatus.RUNNING)

        return {
            "total_executions": len(executions),
            "completed": completed,
            "failed": failed,
            "running": running,
            "success_rate": (completed / len(executions) * 100) if executions else 0
        }

    def _get_top_employees(self, tenant_id: str, days: int) -> List[Dict]:
        """获取 Top AI 员工"""
        start_date = datetime.utcnow() - timedelta(days=days)

        # 按员工分组统计
        employee_stats = defaultdict(lambda: {
            "executions": 0,
            "total_tokens": 0,
            "total_cost": 0,
            "success_count": 0,
            "avg_duration": 0
        })

        executions = self.db.query(AgentExecutionDB).filter(
            AgentExecutionDB.tenant_id == tenant_id,
            AgentExecutionDB.created_at >= start_date
        ).all()

        for e in executions:
            emp_id = e.employee_id
            employee_stats[emp_id]["executions"] += 1
            employee_stats[emp_id]["total_tokens"] += e.total_tokens or 0
            employee_stats[emp_id]["total_cost"] += e.token_cost or 0.0
            if e.execution_status == AgentExecutionStatus.COMPLETED:
                employee_stats[emp_id]["success_count"] += 1
            if e.duration_ms:
                employee_stats[emp_id]["avg_duration"] += e.duration_ms

        # 计算平均耗时
        for emp_id in employee_stats:
            if employee_stats[emp_id]["executions"] > 0:
                employee_stats[emp_id]["avg_duration"] /= employee_stats[emp_id]["executions"]

        # 排序
        sorted_employees = sorted(
            [
                {"employee_id": emp_id, **stats}
                for emp_id, stats in employee_stats.items()
            ],
            key=lambda x: x["executions"],
            reverse=True
        )[:10]

        return sorted_employees
