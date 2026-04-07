"""
SLA (Service Level Agreement) 服务等级协议管理。

提供 SLA 定义、监控和合规性检查功能。
"""
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

from sqlalchemy import DateTime, Float, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import Base


class SLATier(str, Enum):
    """SLA 等级。"""
    FREE = "free"  # 免费层
    BASIC = "basic"  # 基础层
    PROFESSIONAL = "professional"  # 专业层
    ENTERPRISE = "enterprise"  # 企业层


# SLA 等级配置
SLA_CONFIG = {
    SLATier.FREE: {
        "name": "免费版",
        "name_en": "Free",
        "availability": 95.0,  # 可用性承诺 (%)
        "response_time_hours": 72,  # 响应时间 (小时)
        "resolution_time_hours": 168,  # 解决时间 (小时)
        "support_channels": ["email"],  # 支持渠道
        "api_rate_limit": 100,  # API 限流 (次/分钟)
        "max_tasks_per_month": 100,  # 月度任务限额
        "price_cny": 0,  # 价格 (元/月)
    },
    SLATier.BASIC: {
        "name": "基础版",
        "name_en": "Basic",
        "availability": 99.0,
        "response_time_hours": 24,
        "resolution_time_hours": 72,
        "support_channels": ["email", "chat"],
        "api_rate_limit": 500,
        "max_tasks_per_month": 1000,
        "price_cny": 299,
    },
    SLATier.PROFESSIONAL: {
        "name": "专业版",
        "name_en": "Professional",
        "availability": 99.5,
        "response_time_hours": 12,
        "resolution_time_hours": 48,
        "support_channels": ["email", "chat", "phone"],
        "api_rate_limit": 2000,
        "max_tasks_per_month": 10000,
        "price_cny": 999,
    },
    SLATier.ENTERPRISE: {
        "name": "企业版",
        "name_en": "Enterprise",
        "availability": 99.9,
        "response_time_hours": 4,
        "resolution_time_hours": 24,
        "support_channels": ["email", "chat", "phone", "dedicated_manager"],
        "api_rate_limit": 10000,
        "max_tasks_per_month": -1,  # 无限制
        "price_cny": 4999,
    },
}


class SLACommitmentDB(Base):
    """SLA 承诺表 - 定义各等级的 SLA 承诺。"""
    __tablename__ = "sla_commitments"

    commitment_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tier: Mapped[str] = mapped_column(String(50), index=True)  # SLA 等级

    # 可用性承诺
    availability_target: Mapped[float] = mapped_column(Float)  # 可用性目标 (%)

    # 响应时间承诺
    response_time_hours: Mapped[int] = mapped_column(Integer)  # 首次响应时间 (小时)
    resolution_time_hours: Mapped[int] = mapped_column(Integer)  # 解决时间 (小时)

    # 服务限制
    api_rate_limit: Mapped[int] = mapped_column(Integer)  # API 限流
    max_tasks_per_month: Mapped[int] = mapped_column(Integer)  # 月度任务限额

    # 支持渠道 (JSON)
    support_channels: Mapped[List[str]] = mapped_column(JSON, default="[]")

    # 价格
    price_cny: Mapped[float] = mapped_column(Float)  # 价格 (元/月)

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # 审计
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)


class OrganizationSLADDB(Base):
    """组织 SLA 订阅表 - 记录各组织的 SLA 订阅状态。"""
    __tablename__ = "organization_sla"

    org_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # SLA 等级
    tier: Mapped[str] = mapped_column(String(50), default=SLATier.FREE.value)

    # 订阅信息
    subscription_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    subscription_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)  # 自动续费

    # 使用情况
    tasks_this_month: Mapped[int] = mapped_column(Integer, default=0)  # 本月任务数
    api_calls_this_minute: Mapped[int] = mapped_column(Integer, default=0)  # 本分钟 API 调用数

    # SLA 合规性
    availability_actual: Mapped[float] = mapped_column(Float, default=100.0)  # 实际可用性
    incidents_this_month: Mapped[int] = mapped_column(Integer, default=0)  # 本月事件数
    sla_breaches_this_month: Mapped[int] = mapped_column(Integer, default=0)  # 本月 SLA 违约次数

    # 状态
    status: Mapped[str] = mapped_column(String(20), default="active")  # active/suspended/expired

    # 审计
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)


class SLAIncidentDB(Base):
    """SLA 事件表 - 记录服务中断事件。"""
    __tablename__ = "sla_incidents"

    incident_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 事件信息
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20))  # critical/major/minor

    # 时间线
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 影响范围
    affected_orgs: Mapped[List[str]] = mapped_column(JSON, default="[]")  # 受影响的组织
    affected_services: Mapped[List[str]] = mapped_column(JSON, default="[]")  # 受影响的服务

    # 状态
    status: Mapped[str] = mapped_column(String(20), default="investigating")  # investigating/identified/monitoring/resolved

    # 根本原因
    root_cause: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preventive_measures: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 审计
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class SLAComplianceLogDB(Base):
    """SLA 合规性日志表 - 记录合规性检查结果。"""
    __tablename__ = "sla_compliance_logs"

    log_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 关联
    org_id: Mapped[str] = mapped_column(String(36), index=True)

    # 检查信息
    check_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    check_period: Mapped[str] = mapped_column(String(20))  # daily/weekly/monthly

    # 合规性指标
    availability_actual: Mapped[float] = mapped_column(Float)
    availability_target: Mapped[float] = mapped_column(Float)
    is_compliant: Mapped[bool] = mapped_column(Boolean)

    # 违约详情
    breach_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    breach_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 补偿
    compensation_applied: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    compensation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 审计
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)


class SLAService:
    """SLA 服务。"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_sla_tier(self, tier: str) -> Dict[str, Any]:
        """获取 SLA 等级配置。"""
        try:
            tier_enum = SLATier(tier)
            return SLA_CONFIG.get(tier_enum, SLA_CONFIG[SLATier.FREE])
        except ValueError:
            return SLA_CONFIG[SLATier.FREE]

    async def get_organization_sla(self, org_id: str) -> Optional[OrganizationSLADDB]:
        """获取组织的 SLA 订阅信息。"""
        query = select(OrganizationSLADDB).where(OrganizationSLADDB.org_id == org_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def subscribe_sla(
        self,
        org_id: str,
        tier: str,
        subscription_start: datetime,
        subscription_end: Optional[datetime] = None,
        auto_renew: bool = False
    ) -> OrganizationSLADDB:
        """订阅或更新 SLA。"""
        existing = await self.get_organization_sla(org_id)

        if existing:
            existing.tier = tier
            existing.subscription_start = subscription_start
            existing.subscription_end = subscription_end
            existing.auto_renew = auto_renew
            existing.status = "active"
            return existing
        else:
            sla = OrganizationSLADDB(
                org_id=org_id,
                tier=tier,
                subscription_start=subscription_start,
                subscription_end=subscription_end,
                auto_renew=auto_renew,
            )
            self.db.add(sla)
            return sla

    async def check_rate_limit(self, org_id: str) -> bool:
        """检查 API 限流。"""
        sla = await self.get_organization_sla(org_id)
        if not sla:
            tier_config = SLA_CONFIG[SLATier.FREE]
        else:
            tier_enum = SLATier(sla.tier) if sla.tier in [t.value for t in SLATier] else SLATier.FREE
            tier_config = SLA_CONFIG[tier_enum]

        # 简化实现：实际应该使用 Redis 计数器
        return sla.api_calls_this_minute < tier_config["api_rate_limit"]

    async def check_task_limit(self, org_id: str) -> tuple:
        """
        检查任务限额。

        Returns:
            (是否允许，当前使用量，限额)
        """
        sla = await self.get_organization_sla(org_id)
        if not sla:
            tier_config = SLA_CONFIG[SLATier.FREE]
        else:
            tier_enum = SLATier(sla.tier) if sla.tier in [t.value for t in SLATier] else SLATier.FREE
            tier_config = SLA_CONFIG[tier_enum]

        max_tasks = tier_config["max_tasks_per_month"]
        if max_tasks < 0:  # 无限制
            return True, sla.tasks_this_month if sla else 0, -1

        current = sla.tasks_this_month if sla else 0
        return current < max_tasks, current, max_tasks

    async def record_task_usage(self, org_id: str):
        """记录任务使用量。"""
        sla = await self.get_organization_sla(org_id)
        if sla:
            sla.tasks_this_month += 1

    async def create_incident(
        self,
        title: str,
        description: str,
        severity: str,
        affected_orgs: List[str],
        affected_services: List[str]
    ) -> SLAIncidentDB:
        """创建 SLA 事件。"""
        incident = SLAIncidentDB(
            incident_id=str(uuid.uuid4()),
            title=title,
            description=description,
            severity=severity,
            started_at=datetime.now(),
            detected_at=datetime.now(),
            affected_orgs=affected_orgs,
            affected_services=affected_services,
        )
        self.db.add(incident)
        return incident

    async def resolve_incident(
        self,
        incident_id: str,
        root_cause: str,
        preventive_measures: str
    ):
        """解决 SLA 事件。"""
        query = select(SLAIncidentDB).where(SLAIncidentDB.incident_id == incident_id)
        result = await self.db.execute(query)
        incident = result.scalar_one()

        incident.status = "resolved"
        incident.resolved_at = datetime.now()
        incident.root_cause = root_cause
        incident.preventive_measures = preventive_measures

    async def calculate_availability(
        self,
        org_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> float:
        """计算指定时间段内的可用性。"""
        # 查询该时间段内的事件总时长
        query = select(
            func.sum(
                func.extract('epoch', SLAIncidentDB.resolved_at) -
                func.extract('epoch', SLAIncidentDB.started_at)
            )
        ).where(
            SLAIncidentDB.started_at >= start_time,
            SLAIncidentDB.started_at <= end_time,
            SLAIncidentDB.status == "resolved",
        )
        result = await self.db.execute(query)
        downtime_seconds = result.scalar() or 0

        total_seconds = (end_time - start_time).total_seconds()
        if total_seconds <= 0:
            return 100.0

        availability = (1 - downtime_seconds / total_seconds) * 100
        return round(availability, 4)

    async def check_compliance(
        self,
        org_id: str,
        period: str = "monthly"
    ) -> Dict[str, Any]:
        """检查 SLA 合规性。"""
        sla = await self.get_organization_sla(org_id)
        if not sla:
            return {"compliant": True, "tier": "free"}

        tier_config = self.get_sla_tier(sla.tier)

        # 计算可用性
        end_time = datetime.now()
        if period == "monthly":
            start_time = end_time - timedelta(days=30)
        elif period == "weekly":
            start_time = end_time - timedelta(weeks=1)
        else:
            start_time = end_time - timedelta(days=1)

        availability = await self.calculate_availability(org_id, start_time, end_time)
        target = tier_config["availability"]

        is_compliant = availability >= target

        return {
            "compliant": is_compliant,
            "tier": sla.tier,
            "availability_actual": availability,
            "availability_target": target,
            "period": period,
        }

    async def calculate_compensation(
        self,
        org_id: str,
        breach_duration_minutes: int
    ) -> float:
        """
        计算 SLA 违约补偿。

        补偿规则：
        - 可用性 < 99% 但 >= 95%: 补偿 10% 月费
        - 可用性 < 95% 但 >= 90%: 补偿 25% 月费
        - 可用性 < 90%: 补偿 50% 月费
        """
        sla = await self.get_organization_sla(org_id)
        if not sla:
            return 0.0

        tier_config = self.get_sla_tier(sla.tier)
        monthly_price = tier_config["price_cny"]

        # 简化补偿计算
        if breach_duration_minutes < 60:
            return monthly_price * 0.05
        elif breach_duration_minutes < 240:
            return monthly_price * 0.10
        elif breach_duration_minutes < 1440:
            return monthly_price * 0.25
        else:
            return monthly_price * 0.50


async def initialize_sla_commitments(db: AsyncSession):
    """初始化 SLA 承诺配置。"""
    from sqlalchemy import select

    # 检查是否已存在
    query = select(func.count(SLACommitmentDB.commitment_id))
    result = await db.execute(query)
    if result.scalar() > 0:
        return

    # 插入各等级配置
    for tier, config in SLA_CONFIG.items():
        commitment = SLACommitmentDB(
            commitment_id=str(uuid.uuid4()),
            tier=tier.value,
            availability_target=config["availability"],
            response_time_hours=config["response_time_hours"],
            resolution_time_hours=config["resolution_time_hours"],
            api_rate_limit=config["api_rate_limit"],
            max_tasks_per_month=config["max_tasks_per_month"],
            support_channels=config["support_channels"],
            price_cny=config["price_cny"],
        )
        db.add(commitment)

    await db.commit()
