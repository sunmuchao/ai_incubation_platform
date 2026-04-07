"""
隐私安全中心 API 路由 - v1.21 隐私安全中心

提供登录设备管理、登录日志、用户举报、安全知识点、隐私设置增强等 API 端点
"""
from fastapi import APIRouter, HTTPException, Query, Body, Depends, Header
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from services.privacy_security_service import (
    get_login_device_service,
    get_login_log_service,
    get_user_report_service,
    get_safety_tip_service,
    get_privacy_settings_extension_service
)

router = APIRouter(prefix="/api/privacy-security", tags=["privacy-security"])


# ==================== 依赖注入 ====================

async def get_db() -> AsyncSession:
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user_id(x_user_id: str = Header(..., description="用户 ID")) -> str:
    """获取当前用户 ID（从请求头）"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="未授权")
    return x_user_id


# ==================== 登录设备管理 API ====================

@router.get("/devices")
async def get_login_devices(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    获取登录设备列表

    返回当前用户所有登录过的设备信息，包括设备类型、操作系统、浏览器、登录时间等。
    """
    service = get_login_device_service(db)

    devices = await service.get_user_devices(user_id)

    return {
        "success": True,
        "devices": [
            {
                "device_id": d.device_id,
                "device_name": d.device_name,
                "device_type": d.device_type,
                "os_info": d.os_info,
                "browser_info": d.browser_info,
                "ip_address": d.ip_address,
                "location_info": d.location_info,
                "is_current": d.is_current,
                "is_trusted": d.is_trusted,
                "first_login_at": d.first_login_at.isoformat(),
                "last_login_at": d.last_login_at.isoformat()
            }
            for d in devices
        ],
        "total": len(devices)
    }


@router.delete("/devices/{device_id}")
async def remove_device(
    device_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    移除登录设备

    从账号中移除指定的设备，移除后该设备再次登录时需要重新验证。
    当前正在使用的设备不能被移除。
    """
    service = get_login_device_service(db)

    success = await service.remove_device(user_id, device_id)
    if not success:
        raise HTTPException(status_code=400, detail="移除设备失败（可能是当前设备）")

    return {"success": True, "message": "设备已移除"}


@router.post("/devices/{device_id}/trust")
async def trust_device(
    device_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    信任设备

    标记指定设备为受信任设备，受信任设备登录时可跳过部分验证。
    """
    service = get_login_device_service(db)

    success = await service.trust_device(user_id, device_id)
    if not success:
        raise HTTPException(status_code=404, detail="设备不存在")

    return {"success": True, "message": "设备已标记为信任"}


@router.get("/login-logs")
async def get_login_logs(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    获取登录日志

    返回用户的登录历史记录，包括登录时间、IP 地址、设备信息、登录结果等。
    """
    service = get_login_log_service(db)

    logs, total = await service.get_user_logs(user_id, skip=skip, limit=limit)

    return {
        "success": True,
        "logs": [
            {
                "log_id": l.log_id,
                "login_type": l.login_type,
                "ip_address": l.ip_address,
                "location_info": l.location_info,
                "user_agent": l.user_agent,
                "risk_level": l.risk_level,
                "risk_reason": l.risk_reason,
                "created_at": l.created_at.isoformat()
            }
            for l in logs
        ],
        "total": total,
        "has_more": total > skip + limit
    }


# ==================== 用户举报 API ====================

@router.post("/reports")
async def submit_report(
    reported_id: str = Body(..., description="被举报人 ID"),
    report_type: str = Body(..., description="举报类型：harassment, fraud, spam, fake_profile, inappropriate_content, other"),
    report_reason: Optional[str] = Body(None, max_length=500, description="举报原因"),
    evidence_urls: List[str] = Body(default_factory=list, description="证据 URL 列表"),
    related_task_id: Optional[str] = Body(None, description="关联任务 ID"),
    related_message_id: Optional[str] = Body(None, description="关联消息 ID"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    提交举报

    提交对其他用户的举报，支持多种举报类型和证据上传。
    """
    service = get_user_report_service(db)

    try:
        report = await service.submit_report(
            reporter_id=user_id,
            reported_id=reported_id,
            report_type=report_type,
            report_reason=report_reason,
            evidence_urls=evidence_urls,
            related_task_id=related_task_id,
            related_message_id=related_message_id
        )

        return {
            "success": True,
            "report": {
                "report_id": report.report_id,
                "reported_id": report.reported_id,
                "report_type": report.report_type,
                "status": report.status,
                "created_at": report.created_at.isoformat()
            },
            "message": "举报已提交，我们会尽快处理"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reports/my-reports")
async def get_my_reports(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    我的举报列表

    返回当前用户提交的所有举报记录及其处理状态。
    """
    service = get_user_report_service(db)

    reports, total = await service.get_user_reports(user_id, skip=skip, limit=limit)

    return {
        "success": True,
        "reports": [
            {
                "report_id": r.report_id,
                "reported_id": r.reported_id,
                "report_type": r.report_type,
                "report_reason": r.report_reason,
                "status": r.status,
                "priority": r.priority,
                "resolution_notes": r.resolution_notes,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat()
            }
            for r in reports
        ],
        "total": total,
        "has_more": total > skip + limit
    }


@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    举报详情

    获取指定举报的详细信息，包括处理进度和处理结果。
    """
    service = get_user_report_service(db)

    report = await service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="举报不存在")

    # 检查权限：只有举报人可以查看举报详情
    if report.reporter_id != user_id:
        raise HTTPException(status_code=403, detail="无权查看此举报")

    return {
        "success": True,
        "report": {
            "report_id": report.report_id,
            "reporter_id": report.reporter_id,
            "reported_id": report.reported_id,
            "report_type": report.report_type,
            "report_reason": report.report_reason,
            "evidence_urls": report.evidence_urls,
            "related_task_id": report.related_task_id,
            "related_message_id": report.related_message_id,
            "status": report.status,
            "priority": report.priority,
            "resolution_notes": report.resolution_notes,
            "processed_at": report.processed_at.isoformat() if report.processed_at else None,
            "processed_by": report.processed_by,
            "created_at": report.created_at.isoformat(),
            "updated_at": report.updated_at.isoformat()
        }
    }


@router.get("/reports/admin/pending")
async def get_pending_reports(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    待处理举报（管理员）

    获取所有待处理的举报记录，仅供管理员使用。
    """
    # TODO: 添加管理员权限检查
    service = get_user_report_service(db)

    reports, total = await service.get_pending_reports(skip=skip, limit=limit)

    return {
        "success": True,
        "reports": [
            {
                "report_id": r.report_id,
                "reporter_id": r.reporter_id,
                "reported_id": r.reported_id,
                "report_type": r.report_type,
                "report_reason": r.report_reason,
                "priority": r.priority,
                "created_at": r.created_at.isoformat()
            }
            for r in reports
        ],
        "total": total,
        "has_more": total > skip + limit
    }


@router.post("/reports/admin/{report_id}/process")
async def process_report(
    report_id: str,
    status: str = Body(..., description="处理结果：resolved, rejected"),
    resolution_notes: str = Body(..., max_length=1000, description="处理说明"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    处理举报（管理员）

    管理员处理举报，设置处理结果和说明。
    """
    # TODO: 添加管理员权限检查
    service = get_user_report_service(db)

    success = await service.process_report(
        report_id=report_id,
        processor_id=user_id,
        status=status,
        resolution_notes=resolution_notes
    )

    if not success:
        raise HTTPException(status_code=404, detail="举报不存在")

    return {
        "success": True,
        "message": f"举报已{ '处理完成' if status == 'resolved' else '驳回' }"
    }


@router.get("/reports/admin/statistics")
async def get_report_statistics(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    举报统计（管理员）

    获取举报相关的统计数据，仅供管理员使用。
    """
    # TODO: 添加管理员权限检查
    service = get_user_report_service(db)

    stats = await service.get_report_statistics()

    return {
        "success": True,
        "statistics": stats
    }


# ==================== 安全课堂 API ====================

@router.get("/safety/tips")
async def get_safety_tips(
    tip_type: Optional[str] = Query(None, description="知识点类型：fraud_prevention, privacy_protection, account_security, payment_security, task_security"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    获取安全知识列表

    返回平台安全知识文章，包括防骗指南、隐私保护、账号安全等内容。
    """
    service = get_safety_tip_service(db)

    tips = await service.get_tips(tip_type=tip_type, limit=limit)

    # 获取用户已读状态
    read_tip_ids = await service.get_user_read_tips(user_id)

    return {
        "success": True,
        "tips": [
            {
                "tip_id": t.tip_id,
                "title": t.title,
                "content": t.content[:200] + "..." if len(t.content) > 200 else t.content,
                "tip_type": t.tip_type,
                "risk_level": t.risk_level,
                "target_audience": t.target_audience,
                "view_count": t.view_count,
                "is_read": t.tip_id in read_tip_ids,
                "created_at": t.created_at.isoformat()
            }
            for t in tips
        ],
        "total": len(tips)
    }


@router.get("/safety/tips/{tip_id}")
async def get_safety_tip(
    tip_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    安全知识详情

    获取指定安全知识点的完整内容。
    """
    service = get_safety_tip_service(db)

    tip = await service.get_tip(tip_id)
    if not tip:
        raise HTTPException(status_code=404, detail="安全知识不存在")

    # 标记为已读
    await service.mark_tip_read(user_id, tip_id)

    return {
        "success": True,
        "tip": {
            "tip_id": tip.tip_id,
            "title": tip.title,
            "content": tip.content,
            "tip_type": tip.tip_type,
            "risk_level": tip.risk_level,
            "target_audience": tip.target_audience,
            "view_count": tip.view_count,
            "created_at": tip.created_at.isoformat(),
            "updated_at": tip.updated_at.isoformat()
        }
    }


@router.post("/safety/tips/mark-read")
async def mark_tip_read(
    tip_id: str = Body(..., description="安全知识 ID"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    标记安全知识已读
    """
    service = get_safety_tip_service(db)

    success = await service.mark_tip_read(user_id, tip_id)

    return {
        "success": True,
        "message": "标记成功"
    }


# ==================== 隐私设置扩展 API ====================

@router.get("/settings")
async def get_privacy_settings(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    获取隐私设置

    返回当前用户的隐私设置，包括在线状态、距离显示、匿名模式、屏蔽关键词等。
    """
    service = get_privacy_settings_extension_service(db)

    settings = await service.get_settings(user_id)
    if not settings:
        # 返回默认设置
        settings = await service.create_settings(user_id)

    return {
        "success": True,
        "settings": {
            "user_id": settings.user_id,
            "hide_online_status": settings.hide_online_status,
            "hide_distance": settings.hide_distance,
            "anonymous_mode": settings.anonymous_mode,
            "block_keywords": settings.block_keywords,
            "message_filter_level": settings.message_filter_level,
            "data_export_requested": settings.data_export_requested,
            "last_data_export_at": settings.last_data_export_at.isoformat() if settings.last_data_export_at else None,
            "account_deletion_requested": settings.account_deletion_requested,
            "deletion_scheduled_at": settings.deletion_scheduled_at.isoformat() if settings.deletion_scheduled_at else None,
            "updated_at": settings.updated_at.isoformat()
        }
    }


@router.put("/settings")
async def update_privacy_settings(
    hide_online_status: Optional[bool] = Body(None, description="隐藏在线状态"),
    hide_distance: Optional[bool] = Body(None, description="隐藏距离"),
    anonymous_mode: Optional[bool] = Body(None, description="匿名模式"),
    block_keywords: Optional[List[str]] = Body(None, description="屏蔽关键词列表"),
    message_filter_level: Optional[str] = Body(None, description="消息过滤级别"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    更新隐私设置

    更新用户的隐私设置，未提供的字段保持不变。
    """
    service = get_privacy_settings_extension_service(db)

    settings = await service.update_settings(
        user_id=user_id,
        hide_online_status=hide_online_status,
        hide_distance=hide_distance,
        anonymous_mode=anonymous_mode,
        block_keywords=block_keywords,
        message_filter_level=message_filter_level
    )

    return {
        "success": True,
        "settings": {
            "user_id": settings.user_id,
            "hide_online_status": settings.hide_online_status,
            "hide_distance": settings.hide_distance,
            "anonymous_mode": settings.anonymous_mode,
            "block_keywords": settings.block_keywords,
            "message_filter_level": settings.message_filter_level,
            "updated_at": settings.updated_at.isoformat()
        },
        "message": "隐私设置已更新"
    }


# ==================== 屏蔽管理 API ====================

@router.get("/blocked-users")
async def get_blocked_users(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    获取拉黑列表

    返回当前用户拉黑的所有用户列表。
    注意：此功能需要与社交服务的拉黑功能集成
    """
    # TODO: 与社交服务集成，获取实际拉黑列表
    return {
        "success": True,
        "blocked_users": [],
        "total": 0
    }


@router.post("/block/{user_id}")
async def block_user(
    user_id: str,
    target_user_id: str = Body(..., description="要拉黑的用户 ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    拉黑用户

    将指定用户加入拉黑列表，拉黑后对方无法发送消息或查看动态。
    """
    # TODO: 与社交服务集成，实现实际拉黑逻辑
    return {
        "success": True,
        "message": f"用户 {target_user_id} 已被拉黑"
    }


@router.delete("/block/{user_id}")
async def unblock_user(
    user_id: str,
    target_user_id: str = Body(..., description="要取消拉黑的用户 ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    取消拉黑用户

    从拉黑列表中移除指定用户。
    """
    # TODO: 与社交服务集成，实现实际取消拉黑逻辑
    return {
        "success": True,
        "message": f"用户 {target_user_id} 已被取消拉黑"
    }


# ==================== 隐身模式 API ====================

@router.post("/invisible-mode")
async def toggle_invisible_mode(
    enable: bool = Body(..., description="是否启用隐身模式"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    开启/关闭隐身模式

    隐身模式下，其他用户无法看到你的在线状态和活动踪迹。
    """
    service = get_privacy_settings_extension_service(db)

    settings = await service.update_settings(
        user_id=user_id,
        anonymous_mode=enable
    )

    return {
        "success": True,
        "invisible_mode": enable,
        "message": f"隐身模式已{'开启' if enable else '关闭'}"
    }
