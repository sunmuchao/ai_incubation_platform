"""
SLA (Service Level Agreement) API 接口。

提供 SLA 订阅、合规性检查、事件管理等功能。
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session
from services.sla_service import SLAService, SLA_CONFIG, SLATier, initialize_sla_commitments, OrganizationSLADDB

router = APIRouter(prefix="/api/sla", tags=["sla"])


# ==================== 请求/响应模型 ====================

class SLATierInfo(BaseModel):
    """SLA 等级信息。"""
    tier: str
    name: str
    name_en: str
    availability: float
    response_time_hours: int
    resolution_time_hours: int
    support_channels: List[str]
    api_rate_limit: int
    max_tasks_per_month: int
    price_cny: float


class OrganizationSLAResponse(BaseModel):
    """组织 SLA 响应。"""
    org_id: str
    tier: str
    tier_name: str
    subscription_start: str
    subscription_end: Optional[str]
    auto_renew: bool
    status: str
    tasks_this_month: int
    api_calls_this_minute: int
    availability_actual: float


class SLASubscribeRequest(BaseModel):
    """SLA 订阅请求。"""
    tier: str = Field(..., description="SLA 等级 (free/basic/professional/enterprise)")
    auto_renew: bool = Field(default=False, description="是否自动续费")
    subscription_months: int = Field(default=1, ge=1, description="订阅月数")


class SLAComplianceResponse(BaseModel):
    """SLA 合规性响应。"""
    compliant: bool
    tier: str
    availability_actual: float
    availability_target: float
    period: str


class SLAIncidentCreateRequest(BaseModel):
    """创建 SLA 事件请求。"""
    title: str
    description: str
    severity: str = Field(..., description="严重程度 (critical/major/minor)")
    affected_orgs: List[str] = Field(default_factory=list)
    affected_services: List[str] = Field(default_factory=list)


class SLAIncidentResponse(BaseModel):
    """SLA 事件响应。"""
    incident_id: str
    title: str
    description: str
    severity: str
    status: str
    started_at: str
    detected_at: str
    resolved_at: Optional[str]
    affected_orgs: List[str]
    affected_services: List[str]


class CompensationResponse(BaseModel):
    """补偿响应。"""
    org_id: str
    breach_duration_minutes: int
    compensation_amount: float
    compensation_reason: str


# ==================== SLA 等级查询 ====================

@router.get("/tiers", response_model=List[SLATierInfo], summary="获取 SLA 等级列表")
async def get_sla_tiers():
    """获取所有可用的 SLA 等级及配置。"""
    tiers = []
    for tier, config in SLA_CONFIG.items():
        tiers.append(
            SLATierInfo(
                tier=tier.value,
                name=config["name"],
                name_en=config["name_en"],
                availability=config["availability"],
                response_time_hours=config["response_time_hours"],
                resolution_time_hours=config["resolution_time_hours"],
                support_channels=config["support_channels"],
                api_rate_limit=config["api_rate_limit"],
                max_tasks_per_month=config["max_tasks_per_month"],
                price_cny=config["price_cny"],
            )
        )
    return tiers


@router.get("/tiers/{tier}", response_model=SLATierInfo, summary="获取指定 SLA 等级详情")
async def get_sla_tier(tier: str):
    """获取指定 SLA 等级的详细配置。"""
    try:
        tier_enum = SLATier(tier)
        config = SLA_CONFIG[tier_enum]
        return SLATierInfo(
            tier=tier,
            name=config["name"],
            name_en=config["name_en"],
            availability=config["availability"],
            response_time_hours=config["response_time_hours"],
            resolution_time_hours=config["resolution_time_hours"],
            support_channels=config["support_channels"],
            api_rate_limit=config["api_rate_limit"],
            max_tasks_per_month=config["max_tasks_per_month"],
            price_cny=config["price_cny"],
        )
    except ValueError:
        raise HTTPException(status_code=404, detail=f"SLA tier '{tier}' not found")


# ==================== 组织 SLA 管理 ====================

@router.get("/organizations/{org_id}", response_model=OrganizationSLAResponse, summary="获取组织 SLA 状态")
async def get_organization_sla(
    org_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """获取组织的 SLA 订阅状态。"""
    service = SLAService(db)
    sla = await service.get_organization_sla(org_id)

    if not sla:
        # 返回默认的免费版配置
        return OrganizationSLAResponse(
            org_id=org_id,
            tier="free",
            tier_name="免费版",
            subscription_start=datetime.now().isoformat(),
            subscription_end=None,
            auto_renew=False,
            status="active",
            tasks_this_month=0,
            api_calls_this_minute=0,
            availability_actual=100.0,
        )

    tier_config = SLA_CONFIG.get(SLATier(sla.tier) if sla.tier in [t.value for t in SLATier] else SLATier.FREE, {})

    return OrganizationSLAResponse(
        org_id=org_id,
        tier=sla.tier,
        tier_name=tier_config.get("name", "免费版"),
        subscription_start=sla.subscription_start.isoformat(),
        subscription_end=sla.subscription_end.isoformat() if sla.subscription_end else None,
        auto_renew=sla.auto_renew,
        status=sla.status,
        tasks_this_month=sla.tasks_this_month,
        api_calls_this_minute=sla.api_calls_this_minute,
        availability_actual=sla.availability_actual,
    )


@router.post("/organizations/{org_id}/subscribe", response_model=OrganizationSLAResponse, summary="订阅/升级 SLA")
async def subscribe_sla(
    org_id: str,
    request: SLASubscribeRequest,
    current_user_id: str = Query(..., description="当前用户 ID"),
    db: AsyncSession = Depends(get_db_session)
):
    """订阅或升级 SLA 服务等级。"""
    # 验证 SLA 等级
    if request.tier not in [t.value for t in SLATier]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid SLA tier. Must be one of: {[t.value for t in SLATier]}"
        )

    service = SLAService(db)

    subscription_start = datetime.now()
    if request.subscription_months > 0:
        subscription_end = subscription_start + timedelta(days=30 * request.subscription_months)
    else:
        subscription_end = None

    sla = await service.subscribe_sla(
        org_id=org_id,
        tier=request.tier,
        subscription_start=subscription_start,
        subscription_end=subscription_end,
        auto_renew=request.auto_renew,
    )

    tier_config = SLA_CONFIG.get(SLATier(request.tier), {})

    return OrganizationSLAResponse(
        org_id=org_id,
        tier=sla.tier,
        tier_name=tier_config.get("name", "免费版"),
        subscription_start=sla.subscription_start.isoformat(),
        subscription_end=sla.subscription_end.isoformat() if sla.subscription_end else None,
        auto_renew=sla.auto_renew,
        status=sla.status,
        tasks_this_month=sla.tasks_this_month,
        api_calls_this_minute=sla.api_calls_this_minute,
        availability_actual=sla.availability_actual,
    )


@router.get("/organizations/{org_id}/compliance", response_model=SLAComplianceResponse, summary="检查 SLA 合规性")
async def check_sla_compliance(
    org_id: str,
    period: str = Query(default="monthly", description="检查周期 (daily/weekly/monthly)"),
    db: AsyncSession = Depends(get_db_session)
):
    """检查组织的 SLA 合规性。"""
    service = SLAService(db)
    compliance = await service.check_compliance(org_id, period)

    return SLAComplianceResponse(**compliance)


@router.get("/organizations/{org_id}/rate-limit-check", summary="检查 API 限流状态")
async def check_rate_limit(
    org_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """检查组织的 API 限流状态。"""
    service = SLAService(db)
    allowed = await service.check_rate_limit(org_id)

    sla = await service.get_organization_sla(org_id)
    if sla:
        tier_config = SLA_CONFIG.get(SLATier(sla.tier) if sla.tier in [t.value for t in SLATier] else SLATier.FREE, {})
        current = sla.api_calls_this_minute
        limit = tier_config.get("api_rate_limit", 100)
    else:
        tier_config = SLA_CONFIG[SLATier.FREE]
        current = 0
        limit = tier_config["api_rate_limit"]

    return {
        "allowed": allowed,
        "current": current,
        "limit": limit,
        "remaining": max(0, limit - current),
    }


@router.get("/organizations/{org_id}/task-limit-check", summary="检查任务限额状态")
async def check_task_limit(
    org_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """检查组织的任务限额状态。"""
    service = SLAService(db)
    allowed, current, limit = await service.check_task_limit(org_id)

    return {
        "allowed": allowed,
        "current": current,
        "limit": limit,
        "remaining": max(0, limit - current) if limit >= 0 else -1,  # -1 表示无限制
    }


# ==================== SLA 事件管理 ====================

@router.post("/incidents", response_model=SLAIncidentResponse, summary="创建 SLA 事件")
async def create_incident(
    request: SLAIncidentCreateRequest,
    current_user_id: str = Query(..., description="当前用户 ID"),
    db: AsyncSession = Depends(get_db_session)
):
    """创建 SLA 事件（服务中断事件）。"""
    service = SLAService(db)

    incident = await service.create_incident(
        title=request.title,
        description=request.description,
        severity=request.severity,
        affected_orgs=request.affected_orgs,
        affected_services=request.affected_services,
    )

    return SLAIncidentResponse(
        incident_id=incident.incident_id,
        title=incident.title,
        description=incident.description,
        severity=incident.severity,
        status=incident.status,
        started_at=incident.started_at.isoformat(),
        detected_at=incident.detected_at.isoformat(),
        resolved_at=None,
        affected_orgs=incident.affected_orgs,
        affected_services=incident.affected_services,
    )


@router.get("/incidents", response_model=List[SLAIncidentResponse], summary="获取 SLA 事件列表")
async def list_incidents(
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session)
):
    """获取 SLA 事件列表。"""
    from sqlalchemy import select, desc
    from services.sla_service import SLAIncidentDB

    query = select(SLAIncidentDB).order_by(desc(SLAIncidentDB.created_at)).limit(limit)
    if status:
        query = query.where(SLAIncidentDB.status == status)

    result = await db.execute(query)
    incidents = result.scalars().all()

    return [
        SLAIncidentResponse(
            incident_id=i.incident_id,
            title=i.title,
            description=i.description,
            severity=i.severity,
            status=i.status,
            started_at=i.started_at.isoformat(),
            detected_at=i.detected_at.isoformat(),
            resolved_at=i.resolved_at.isoformat() if i.resolved_at else None,
            affected_orgs=i.affected_orgs,
            affected_services=i.affected_services,
        )
        for i in incidents
    ]


@router.post("/incidents/{incident_id}/resolve", summary="解决 SLA 事件")
async def resolve_incident(
    incident_id: str,
    root_cause: str = Query(..., description="根本原因"),
    preventive_measures: str = Query(..., description="预防措施"),
    current_user_id: str = Query(..., description="当前用户 ID"),
    db: AsyncSession = Depends(get_db_session)
):
    """解决 SLA 事件。"""
    service = SLAService(db)
    await service.resolve_incident(incident_id, root_cause, preventive_measures)
    return {"message": "Incident resolved successfully"}


# ==================== 补偿管理 ====================

@router.post("/organizations/{org_id}/calculate-compensation", response_model=CompensationResponse, summary="计算 SLA 补偿")
async def calculate_compensation(
    org_id: str,
    breach_duration_minutes: int = Query(..., ge=1, description="违约持续时间 (分钟)"),
    db: AsyncSession = Depends(get_db_session)
):
    """计算 SLA 违约补偿金额。"""
    service = SLAService(db)
    compensation = await service.calculate_compensation(org_id, breach_duration_minutes)

    sla = await service.get_organization_sla(org_id)
    tier_config = SLA_CONFIG.get(SLATier(sla.tier) if sla and sla.tier in [t.value for t in SLATier] else SLATier.FREE, {})

    return CompensationResponse(
        org_id=org_id,
        breach_duration_minutes=breach_duration_minutes,
        compensation_amount=compensation,
        compensation_reason=f"SLA breach for {breach_duration_minutes} minutes ({tier_config.get('name', '免费版')})",
    )


# ==================== 系统初始化 ====================

@router.post("/init", summary="初始化 SLA 配置")
async def init_sla_config(db: AsyncSession = Depends(get_db_session)):
    """初始化 SLA 承诺配置。"""
    await initialize_sla_commitments(db)
    return {"message": "SLA configurations initialized successfully"}
