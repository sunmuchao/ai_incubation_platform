"""
告警 API - P0 告警通知

提供告警配置、查询和管理的 HTTP 接口
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from db.postgresql_models import AlertModel, AlertHistoryModel
from db.postgresql_config import get_db_session
from services.alert_service import AlertRuleEngine, get_alert_rule_engine, AlertNotificationService


router = APIRouter(prefix="/alerts", tags=["Alerts"])


# ==================== Schema 定义 ====================

class AlertCreateRequest(BaseModel):
    """创建告警请求"""
    alert_name: str = Field(..., description="告警名称")
    description: Optional[str] = Field(None, description="告警描述")
    alert_type: str = Field(..., description="告警类型")
    severity: str = Field(default="warning", description="严重级别")
    conditions: Dict[str, Any] = Field(..., description="触发条件")
    threshold: float = Field(..., description="阈值")
    notification_channels: List[str] = Field(default=[], description="通知渠道")
    recipients: List[str] = Field(default=[], description="接收者列表")
    is_active: bool = Field(default=True, description="是否启用")


class AlertUpdateRequest(BaseModel):
    """更新告警请求"""
    alert_name: Optional[str] = Field(None, description="告警名称")
    description: Optional[str] = Field(None, description="告警描述")
    severity: Optional[str] = Field(None, description="严重级别")
    conditions: Optional[Dict[str, Any]] = Field(None, description="触发条件")
    threshold: Optional[float] = Field(None, description="阈值")
    notification_channels: Optional[List[str]] = Field(None, description="通知渠道")
    recipients: Optional[List[str]] = Field(None, description="接收者列表")
    is_active: Optional[bool] = Field(None, description="是否启用")


class AlertResponse(BaseModel):
    """告警响应"""
    id: str
    alert_name: str
    description: Optional[str]
    alert_type: str
    severity: str
    conditions: Dict[str, Any]
    threshold: float
    notification_channels: List[str]
    recipients: List[str]
    is_active: bool
    last_triggered_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertHistoryResponse(BaseModel):
    """告警历史响应"""
    id: int
    alert_id: str
    triggered_at: datetime
    trigger_reason: str
    trigger_value: float
    threshold: float
    notification_sent: bool
    notification_result: Optional[Dict]

    class Config:
        from_attributes = True


class AlertTriggerRequest(BaseModel):
    """手动触发告警请求（用于测试）"""
    metric_value: float = Field(..., description="指标值")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="额外数据")


# ==================== 告警配置管理 ====================

@router.post("", response_model=AlertResponse)
async def create_alert(
    request: AlertCreateRequest,
    db_session=Depends(get_db_session),
):
    """
    创建告警配置

    - **alert_name**: 告警名称
    - **alert_type**: 告警类型（traffic_drop, ranking_drop, competitor_change 等）
    - **severity**: 严重级别 (info, warning, error, critical)
    - **conditions**: 触发条件，如 {"operator": ">=", "baseline": 100}
    - **threshold**: 阈值
    - **notification_channels**: 通知渠道 (email, slack, webhook, dingtalk)
    - **recipients**: 接收者列表（邮箱、webhook URL 等）
    """
    alert_id = str(uuid.uuid4())

    alert = AlertModel(
        id=alert_id,
        alert_name=request.alert_name,
        description=request.description,
        alert_type=request.alert_type,
        severity=request.severity,
        conditions=request.conditions,
        threshold=request.threshold,
        notification_channels=request.notification_channels,
        recipients=request.recipients,
        is_active=request.is_active,
    )

    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)

    return alert


@router.get("", response_model=List[AlertResponse])
async def list_alerts(
    alert_type: Optional[str] = Query(None, description="告警类型过滤"),
    is_active: Optional[bool] = Query(None, description="启用状态过滤"),
    db_session=Depends(get_db_session),
):
    """查询告警配置列表"""
    query = db_session.query(AlertModel)

    if alert_type:
        query = query.filter(AlertModel.alert_type == alert_type)
    if is_active is not None:
        query = query.filter(AlertModel.is_active == is_active)

    return query.order_by(AlertModel.created_at.desc()).all()


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    db_session=Depends(get_db_session),
):
    """获取告警配置详情"""
    alert = db_session.query(AlertModel).filter(AlertModel.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: str,
    request: AlertUpdateRequest,
    db_session=Depends(get_db_session),
):
    """更新告警配置"""
    alert = db_session.query(AlertModel).filter(AlertModel.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alert, field, value)

    alert.updated_at = datetime.utcnow()
    db_session.commit()
    db_session.refresh(alert)

    return alert


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: str,
    db_session=Depends(get_db_session),
):
    """删除告警配置"""
    alert = db_session.query(AlertModel).filter(AlertModel.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    db_session.delete(alert)
    db_session.commit()

    return {"message": "Alert deleted successfully"}


@router.post("/{alert_id}/toggle", response_model=AlertResponse)
async def toggle_alert(
    alert_id: str,
    db_session=Depends(get_db_session),
):
    """切换告警启用状态"""
    alert = db_session.query(AlertModel).filter(AlertModel.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_active = not alert.is_active
    alert.updated_at = datetime.utcnow()
    db_session.commit()
    db_session.refresh(alert)

    return alert


# ==================== 告警历史查询 ====================

@router.get("/{alert_id}/history", response_model=List[AlertHistoryResponse])
async def get_alert_history(
    alert_id: str,
    limit: int = Query(50, ge=1, le=500, description="限制数量"),
    db_session=Depends(get_db_session),
):
    """获取告警历史记录"""
    return (
        db_session.query(AlertHistoryModel)
        .filter(AlertHistoryModel.alert_id == alert_id)
        .order_by(AlertHistoryModel.triggered_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/history/recent", response_model=List[AlertHistoryResponse])
async def get_recent_alerts(
    limit: int = Query(50, ge=1, le=500, description="限制数量"),
    severity: Optional[str] = Query(None, description="严重级别过滤"),
    db_session=Depends(get_db_session),
):
    """获取最近的告警"""
    query = db_session.query(AlertHistoryModel)

    if severity:
        # 通过 alert_id 关联查询 severity
        query = (
            query.join(AlertModel)
            .filter(AlertModel.severity == severity)
        )

    return query.order_by(AlertHistoryModel.triggered_at.desc()).limit(limit).all()


# ==================== 告警测试 ====================

@router.post("/{alert_id}/test")
async def test_alert(
    alert_id: str,
    request: AlertTriggerRequest,
    db_session=Depends(get_db_session),
    alert_engine: AlertRuleEngine = Depends(get_alert_rule_engine),
):
    """
    测试告警

    使用给定的指标值触发告警，用于验证配置是否正确
    """
    import asyncio

    alert = db_session.query(AlertModel).filter(AlertModel.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # 异步触发告警检查
    await alert_engine.check_and_trigger_alerts(
        alert_type=alert.alert_type,
        metric_value=request.metric_value,
        extra_data=request.extra_data,
        trace_id=f"test-{uuid.uuid4()}",
    )

    return {"message": "Alert test triggered", "alert_name": alert.alert_name}


# ==================== 预设告警模板 ====================

@router.get("/templates")
async def get_alert_templates():
    """
    获取预设告警模板

    提供常用告警配置模板，用户可基于模板快速创建
    """
    templates = [
        {
            "id": "traffic_drop",
            "name": "流量下跌告警",
            "description": "当流量下跌超过阈值时触发",
            "alert_type": "traffic_drop",
            "default_severity": "warning",
            "default_conditions": {"operator": "drop_by_percent", "baseline": 100},
            "default_threshold": 20.0,  # 下跌 20%
            "recommended_channels": ["email", "slack"],
        },
        {
            "id": "ranking_drop",
            "name": "关键词排名下跌告警",
            "description": "当核心关键词排名下跌时触发",
            "alert_type": "ranking_drop",
            "default_severity": "warning",
            "default_conditions": {"operator": "<"},
            "default_threshold": 5,  # 排名跌出前 5
            "recommended_channels": ["email"],
        },
        {
            "id": "error_rate_spike",
            "name": "错误率飙升告警",
            "description": "当错误率超过阈值时触发",
            "alert_type": "error_rate_spike",
            "default_severity": "error",
            "default_conditions": {"operator": ">="},
            "default_threshold": 5.0,  # 错误率超过 5%
            "recommended_channels": ["slack", "webhook"],
        },
        {
            "id": "slow_response",
            "name": "响应缓慢告警",
            "description": "当平均响应时间超过阈值时触发",
            "alert_type": "slow_response",
            "default_severity": "warning",
            "default_conditions": {"operator": ">="},
            "default_threshold": 2000,  # 2 秒
            "recommended_channels": ["slack"],
        },
        {
            "id": "competitor_change",
            "name": "竞品动态告警",
            "description": "当竞品流量超过我们时触发",
            "alert_type": "competitor_change",
            "default_severity": "info",
            "default_conditions": {"operator": ">"},
            "default_threshold": 1.0,  # 竞品流量超过我们的倍数
            "recommended_channels": ["email"],
        },
    ]

    return {"templates": templates}
