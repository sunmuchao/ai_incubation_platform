"""
报表 API - 提供平台各类报表数据接口。
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from typing import Optional, List, Any

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import PlainTextResponse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.report_service import report_service

router = APIRouter(prefix="/api/reports", tags=["reports"])


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """解析日期字符串为 datetime 对象。"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format: {date_str}. Expected YYYY-MM-DD"
        )


@router.get("/task-completion")
async def get_task_completion_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = "day",
    format: str = "json",
):
    """
    任务完成情况报表。

    - start_date: 开始日期 (YYYY-MM-DD)
    - end_date: 结束日期 (YYYY-MM-DD)
    - group_by: 分组方式 (day, week, month, status, priority, interaction_type)
    - format: 返回格式 (json, csv)
    """
    if group_by not in ("day", "week", "month", "status", "priority", "interaction_type"):
        raise HTTPException(
            status_code=400,
            detail="Invalid group_by. Must be one of: day, week, month, status, priority, interaction_type"
        )

    start_dt = parse_date(start_date)
    end_dt = parse_date(end_date)

    # 默认查询最近 30 天
    if not start_dt:
        start_dt = datetime.now() - timedelta(days=30)
    if not end_dt:
        end_dt = datetime.now()

    data = report_service.get_task_completion_report(
        start_date=start_dt,
        end_date=end_dt,
        group_by=group_by,
    )

    if format == "csv":
        csv_content = report_service.export_to_csv(data)
        return PlainTextResponse(
            csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=task_completion_report.csv"},
        )

    return data


@router.get("/worker-performance")
async def get_worker_performance_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_tasks: int = 0,
    format: str = "json",
):
    """
    工人绩效报表。

    - start_date: 开始日期 (YYYY-MM-DD)
    - end_date: 结束日期 (YYYY-MM-DD)
    - min_tasks: 最少任务数筛选
    - format: 返回格式 (json, csv)
    """
    start_dt = parse_date(start_date)
    end_dt = parse_date(end_date)

    # 默认查询最近 30 天
    if not start_dt:
        start_dt = datetime.now() - timedelta(days=30)
    if not end_dt:
        end_dt = datetime.now()

    data = report_service.get_worker_performance_report(
        start_date=start_dt,
        end_date=end_dt,
        min_tasks=min_tasks,
    )

    if format == "csv":
        csv_content = report_service.export_to_csv(data)
        return PlainTextResponse(
            csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=worker_performance_report.csv"},
        )

    return data


@router.get("/payment-flow")
async def get_payment_flow_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    transaction_type: Optional[str] = None,
    group_by: str = "day",
    format: str = "json",
):
    """
    支付流水报表。

    - start_date: 开始日期 (YYYY-MM-DD)
    - end_date: 结束日期 (YYYY-MM-DD)
    - transaction_type: 交易类型筛选 (deposit, payout, task_payment, platform_fee, task_refund)
    - group_by: 分组方式 (day, type)
    - format: 返回格式 (json, csv)
    """
    if group_by not in ("day", "type"):
        raise HTTPException(
            status_code=400,
            detail="Invalid group_by. Must be one of: day, type"
        )

    start_dt = parse_date(start_date)
    end_dt = parse_date(end_date)

    # 默认查询最近 30 天
    if not start_dt:
        start_dt = datetime.now() - timedelta(days=30)
    if not end_dt:
        end_dt = datetime.now()

    data = report_service.get_payment_flow_report(
        start_date=start_dt,
        end_date=end_dt,
        transaction_type=transaction_type,
        group_by=group_by,
    )

    if format == "csv":
        csv_content = report_service.export_to_csv(data)
        return PlainTextResponse(
            csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=payment_flow_report.csv"},
        )

    return data


@router.get("/summary")
async def get_report_summary():
    """
    获取报表摘要（快速概览）。
    """
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    # 获取各类报表的核心数据
    today_completion = report_service.get_task_completion_report(
        start_date=today_start,
        end_date=now,
        group_by="status",
    )
    week_completion = report_service.get_task_completion_report(
        start_date=week_start,
        end_date=now,
        group_by="status",
    )
    month_completion = report_service.get_task_completion_report(
        start_date=month_start,
        end_date=now,
        group_by="status",
    )

    # 计算总数
    def sum_tasks(reports):
        return sum(r.get('count', r.get('total', 0)) for r in reports)

    return {
        "generated_at": now.isoformat(),
        "task_summary": {
            "today": sum_tasks(today_completion),
            "week": sum_tasks(week_completion),
            "month": sum_tasks(month_completion),
        },
        "available_reports": [
            {"name": "task-completion", "description": "任务完成情况报表"},
            {"name": "worker-performance", "description": "工人绩效报表"},
            {"name": "payment-flow", "description": "支付流水报表"},
        ],
    }


@router.get("/export/{report_name}")
async def export_report(
    report_name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    format: str = "json",
    **kwargs,
):
    """
    导出报表。

    - report_name: 报表名称 (task-completion, worker-performance, payment-flow)
    - start_date: 开始日期 (YYYY-MM-DD)
    - end_date: 结束日期 (YYYY-MM-DD)
    - format: 返回格式 (json, csv)
    """
    start_dt = parse_date(start_date)
    end_dt = parse_date(end_date)

    if not start_dt:
        start_dt = datetime.now() - timedelta(days=30)
    if not end_dt:
        end_dt = datetime.now()

    data = None

    if report_name == "task-completion":
        data = report_service.get_task_completion_report(
            start_date=start_dt,
            end_date=end_dt,
            group_by=kwargs.get('group_by', 'day'),
        )
    elif report_name == "worker-performance":
        data = report_service.get_worker_performance_report(
            start_date=start_dt,
            end_date=end_dt,
            min_tasks=int(kwargs.get('min_tasks', 0)),
        )
    elif report_name == "payment-flow":
        data = report_service.get_payment_flow_report(
            start_date=start_dt,
            end_date=end_dt,
            transaction_type=kwargs.get('transaction_type'),
            group_by=kwargs.get('group_by', 'day'),
        )
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown report: {report_name}"
        )

    filename = f"{report_name}_report_{start_dt.strftime('%Y%m%d')}_{end_dt.strftime('%Y%m%d')}"

    if format == "csv":
        csv_content = report_service.export_to_csv(data)
        return PlainTextResponse(
            csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
        )
    else:
        json_content = report_service.export_to_json(data)
        return PlainTextResponse(
            json_content,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}.json"},
        )
