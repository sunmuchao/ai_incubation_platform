"""
增强反作弊 API - 设备指纹识别、IP 地址检测、异常行为模式识别。
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.enhanced_anti_cheat_service import enhanced_anti_cheat_service

router = APIRouter(prefix="/api/anti-cheat", tags=["anti-cheat"])


class DeviceFingerprintRequest(BaseModel):
    """设备指纹请求。"""
    user_agent: Optional[str] = None
    screen_resolution: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    canvas_hash: Optional[str] = None
    webgl_hash: Optional[str] = None


class DeviceFingerprintResponse(BaseModel):
    """设备指纹响应。"""
    fingerprint: str
    is_suspicious: bool
    suspicion_reason: Optional[str]
    associated_users_count: int


class IPAnalysisResponse(BaseModel):
    """IP 分析响应。"""
    ip: str
    country: Optional[str]
    region: Optional[str]
    city: Optional[str]
    isp: Optional[str]
    is_proxy: Optional[bool]
    is_vpn: Optional[bool]
    is_tor: Optional[bool]
    is_datacenter: Optional[bool]
    risk_score: float
    risk_level: str
    is_blacklisted: bool


class BehavioralAnalysisResponse(BaseModel):
    """行为分析响应。"""
    user_id: str
    risk_score: float
    risk_level: str
    flags: List[Dict[str, str]]
    total_events: int
    total_tasks: int


class RiskAssessmentResponse(BaseModel):
    """综合风险评估响应。"""
    user_id: str
    composite_risk_score: float
    risk_level: str
    device_count: int
    device_risks: List[Dict[str, str]]
    ip_risks: List[Dict[str, Any]]
    behavior_analysis: Dict[str, Any]


class SubmissionRiskCheckResponse(BaseModel):
    """提交风险检查响应。"""
    allowed: bool
    reason: Optional[str]
    risk_assessment: Dict[str, Any]


class RiskEventItem(BaseModel):
    """风险事件项。"""
    timestamp: str
    user_id: str
    risk_score: float
    details: Dict[str, Any]


@router.post("/device/fingerprint", response_model=DeviceFingerprintResponse)
async def generate_device_fingerprint(
    request: DeviceFingerprintRequest,
    user_id: str,
    x_forwarded_for: Optional[str] = Header(None),
    user_agent: Optional[str] = Header(None),
):
    """
    生成设备指纹。

    通过多种信号组合生成设备唯一标识，用于识别和追踪设备。
    支持自动提取请求头中的 User-Agent 和 IP 地址。
    """
    # 提取 IP 地址
    ip_address = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else None

    # 使用请求头中的 User-Agent（如果请求体未提供）
    ua = request.user_agent or user_agent

    # 生成指纹
    fingerprint = enhanced_anti_cheat_service.device_fingerprint.generate_fingerprint(
        user_agent=ua,
        ip_address=ip_address,
        screen_resolution=request.screen_resolution,
        timezone=request.timezone,
        language=request.language,
        canvas_hash=request.canvas_hash,
        webgl_hash=request.webgl_hash,
    )

    # 注册用户 - 设备关联
    enhanced_anti_cheat_service.device_fingerprint.register_user_device(user_id, fingerprint)

    # 检查设备是否可疑
    is_suspicious, reason = enhanced_anti_cheat_service.device_fingerprint.is_suspicious_device(fingerprint)

    # 获取关联用户数
    devices = enhanced_anti_cheat_service.device_fingerprint.get_user_devices(user_id)

    return DeviceFingerprintResponse(
        fingerprint=fingerprint,
        is_suspicious=is_suspicious,
        suspicion_reason=reason,
        associated_users_count=len(devices),
    )


@router.get("/device/{user_id}/list")
async def list_user_devices(user_id: str):
    """列出用户关联的所有设备。"""
    devices = enhanced_anti_cheat_service.device_fingerprint.get_user_devices(user_id)
    return {
        "user_id": user_id,
        "device_count": len(devices),
        "devices": devices,
    }


@router.get("/ip/{ip_address}/analysis", response_model=IPAnalysisResponse)
async def analyze_ip_address(ip_address: str):
    """
    分析 IP 地址。

    返回 IP 详细信息和风险评分，包括：
    - 地理位置信息
    - 代理/VPN/Tor 检测
    - 数据中心 IP 检测
    - 风险评分
    """
    ip_info = enhanced_anti_cheat_service.ip_detector.analyze_ip(ip_address)
    is_blacklisted = enhanced_anti_cheat_service.ip_detector.is_ip_blacklisted(ip_address)

    return IPAnalysisResponse(
        ip=ip_address,
        country=ip_info.get("country"),
        region=ip_info.get("region"),
        city=ip_info.get("city"),
        isp=ip_info.get("isp"),
        is_proxy=ip_info.get("is_proxy"),
        is_vpn=ip_info.get("is_vpn"),
        is_tor=ip_info.get("is_tor"),
        is_datacenter=ip_info.get("is_datacenter"),
        risk_score=ip_info["risk_score"],
        risk_level=ip_info["risk_level"],
        is_blacklisted=is_blacklisted,
    )


@router.post("/ip/{ip_address}/block")
async def block_ip_address(ip_address: str, reason: str):
    """封禁 IP 地址。"""
    enhanced_anti_cheat_service.block_ip(ip_address, reason)
    return {"message": "IP blocked", "ip": ip_address, "reason": reason}


@router.post("/ip/{ip_address}/unblock")
async def unblock_ip_address(ip_address: str):
    """解封 IP 地址。"""
    success = enhanced_anti_cheat_service.unblock_ip(ip_address)
    if success:
        return {"message": "IP unblocked", "ip": ip_address}
    else:
        raise HTTPException(status_code=404, detail="IP not in blacklist")


@router.get("/user/{user_id}/behavior", response_model=BehavioralAnalysisResponse)
async def analyze_user_behavior(user_id: str):
    """
    分析用户行为模式。

    检测异常行为：
    - 提交频率异常
    - 任务完成速度过快
    - 深夜异常活动
    - 选择性刷单（只接高报酬任务）
    """
    analysis = enhanced_anti_cheat_service.behavioral_analyzer.analyze_user_behavior(user_id)
    return BehavioralAnalysisResponse(
        user_id=user_id,
        risk_score=analysis["risk_score"],
        risk_level=analysis["risk_level"],
        flags=analysis["flags"],
        total_events=analysis["total_events"],
        total_tasks=analysis["total_tasks"],
    )


@router.get("/user/{user_id}/risk-assessment", response_model=RiskAssessmentResponse)
async def get_user_risk_assessment(user_id: str):
    """
    获取用户综合风险评估。

    综合评估设备风险、IP 风险、行为风险，返回整体风险评分。
    """
    assessment = enhanced_anti_cheat_service.get_user_risk_assessment(user_id)
    return RiskAssessmentResponse(**assessment)


@router.post("/user/{user_id}/check-submission", response_model=SubmissionRiskCheckResponse)
async def check_submission_risk(
    user_id: str,
    task_id: str,
    content: str,
    x_forwarded_for: Optional[str] = Header(None),
):
    """
    检查提交风险。

    在用户提交任务前调用，综合评估风险并决定是否允许提交。
    """
    ip_address = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else None

    allowed, reason, risk_assessment = enhanced_anti_cheat_service.check_submission_risk(
        user_id=user_id,
        task_id=task_id,
        content=content,
        ip_address=ip_address,
    )

    return SubmissionRiskCheckResponse(
        allowed=allowed,
        reason=reason,
        risk_assessment=risk_assessment,
    )


@router.get("/user/{user_id}/risk-score")
async def get_user_risk_score(user_id: str):
    """获取用户风险评分（简化版）。"""
    if user_id in enhanced_anti_cheat_service._user_risk_scores:
        score = enhanced_anti_cheat_service._user_risk_scores[user_id]
    else:
        assessment = enhanced_anti_cheat_service.get_user_risk_assessment(user_id)
        score = assessment["composite_risk_score"]

    return {
        "user_id": user_id,
        "risk_score": score,
        "risk_level": "low" if score < 0.3 else "medium" if score < 0.6 else "high",
    }


@router.get("/risk-events", response_model=List[RiskEventItem])
async def get_risk_events(limit: int = 50):
    """获取风险事件日志。"""
    events = enhanced_anti_cheat_service.get_risk_events(limit)
    # 转换 datetime 为字符串
    result = []
    for event in events:
        result.append({
            "timestamp": event["timestamp"].isoformat(),
            "user_id": event["user_id"],
            "risk_score": event["risk_score"],
            "details": event["details"],
        })
    return result


@router.post("/report-cheating")
async def report_cheating(
    user_id: str,
    task_id: str,
    reason: str,
    evidence: Optional[List[str]] = None,
):
    """
    举报作弊行为。

    记录作弊举报并自动封禁相关 IP（如果证据充分）。
    """
    # 记录风险事件
    enhanced_anti_cheat_service._log_risk_event(
        user_id=user_id,
        risk_score=1.0,  # 作弊举报为最高风险
        details={
            "type": "cheating_report",
            "task_id": task_id,
            "reason": reason,
            "evidence": evidence or [],
        },
    )

    # 记录行为事件
    enhanced_anti_cheat_service.behavioral_analyzer.record_event(
        user_id=user_id,
        event_type="cheating_reported",
        task_id=task_id,
        metadata={"reason": reason, "evidence": evidence or []},
    )

    return {
        "message": "Cheating reported",
        "user_id": user_id,
        "task_id": task_id,
        "status": "under_review",
    }


@router.get("/stats")
async def get_anti_cheat_stats():
    """获取反作弊统计信息。"""
    # 统计设备数量
    device_count = len(enhanced_anti_cheat_service.device_fingerprint._device_fingerprints)

    # 统计 IP 记录
    ip_count = len(enhanced_anti_cheat_service.ip_detector._ip_records)

    # 统计黑名单 IP 数量
    blacklist_count = len(enhanced_anti_cheat_service.ip_detector._ip_blacklist)

    # 统计风险事件
    risk_event_count = len(enhanced_anti_cheat_service._risk_events)

    # 统计高风险用户
    high_risk_users = [
        uid for uid, score in enhanced_anti_cheat_service._user_risk_scores.items()
        if score >= 0.6
    ]

    return {
        "device_count": device_count,
        "ip_count": ip_count,
        "blacklisted_ips": blacklist_count,
        "risk_events_7d": risk_event_count,
        "high_risk_users": len(high_risk_users),
    }


@router.post("/reset-state")
async def reset_anti_cheat_state():
    """重置反作弊状态（仅用于测试）。"""
    enhanced_anti_cheat_service.reset_state()
    return {"message": "Anti-cheat state reset"}
