"""
社区治理工具 API 路由
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.member import MemberType, ContentType, ReportStatus, OperationType
from services.community_service import community_service
from services.governance_tools import create_governance_tools

router = APIRouter(prefix="/api/governance", tags=["governance"])

# 创建治理工具实例
governance_tools = create_governance_tools(community_service)


class RemoveContentRequest(BaseModel):
    """下架内容请求"""
    content_type: str = Field(..., description="内容类型：post 或 comment")
    content_id: str = Field(..., description="内容 ID")
    reason: str = Field(..., description="下架原因")
    notify_author: bool = Field(default=True, description="是否通知作者")


class WarnUserRequest(BaseModel):
    """警告用户请求"""
    user_id: str = Field(..., description="被警告用户 ID")
    reason: str = Field(..., description="警告原因")
    warning_level: str = Field(default="normal", description="警告级别：normal 或 severe")


class BatchProcessReportsRequest(BaseModel):
    """批量处理举报请求"""
    report_ids: List[str] = Field(..., description="举报 ID 列表")
    status: str = Field(..., description="处理状态")
    handler_note: str = Field(default="", description="处理备注")


class ExportLogsRequest(BaseModel):
    """导出审计日志请求"""
    start_time: str = Field(..., description="开始时间 (ISO 格式)")
    end_time: str = Field(..., description="结束时间 (ISO 格式)")
    operator_id: Optional[str] = Field(default=None, description="操作人 ID")
    operation_type: Optional[str] = Field(default=None, description="操作类型")
    format: str = Field(default="json", description="导出格式：json 或 csv")


@router.post("/remove-content")
async def remove_content(request: RemoveContentRequest, operator_id: str = Query(...)):
    """下架内容"""
    try:
        content_type = ContentType(request.content_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid content_type")

    result = governance_tools.remove_content(
        content_type=content_type,
        content_id=request.content_id,
        operator_id=operator_id,
        reason=request.reason,
        notify_author=request.notify_author
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "操作失败"))

    return result


@router.post("/warn-user")
async def warn_user(request: WarnUserRequest, operator_id: str = Query(...)):
    """警告用户"""
    result = governance_tools.warn_user(
        user_id=request.user_id,
        operator_id=operator_id,
        reason=request.reason,
        warning_level=request.warning_level
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "操作失败"))

    return result


@router.post("/reports/batch-process")
async def batch_process_reports(request: BatchProcessReportsRequest, handler_id: str = Query(...)):
    """批量处理举报"""
    try:
        status = ReportStatus(request.status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")

    result = governance_tools.batch_process_reports(
        report_ids=request.report_ids,
        handler_id=handler_id,
        status=status,
        handler_note=request.handler_note
    )

    return result


@router.post("/audit-logs/export")
async def export_audit_logs(request: ExportLogsRequest):
    """导出审计日志"""
    try:
        start_time = datetime.fromisoformat(request.start_time)
        end_time = datetime.fromisoformat(request.end_time)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid time format")

    operation_type = None
    if request.operation_type:
        try:
            operation_type = OperationType(request.operation_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid operation_type")

    content = governance_tools.export_audit_logs(
        start_time=start_time,
        end_time=end_time,
        operator_id=request.operator_id,
        operation_type=operation_type,
        format=request.format
    )

    return {
        "content": content,
        "format": request.format
    }


@router.get("/stats")
async def get_governance_stats(days: int = Query(default=30, ge=1, le=365)):
    """获取治理统计数据"""
    return governance_tools.get_governance_stats(days=days)


@router.get("/stats/user/{user_id}")
async def get_user_behavior_stats(user_id: str, days: int = Query(default=30, ge=1, le=365)):
    """获取用户行为统计"""
    return governance_tools.get_user_behavior_stats(user_id=user_id, days=days)
