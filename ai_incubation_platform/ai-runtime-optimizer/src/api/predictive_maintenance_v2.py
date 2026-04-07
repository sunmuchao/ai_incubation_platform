"""
预测性维护 V2.3 API 端点

提供健康度评分、剩余寿命预测、预测性告警和维护计划优化的 HTTP 接口
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from core.predictive_maintenance_v2 import (
    get_predictive_maintenance_v2_engine,
    HealthScore,
    RULPrediction,
    PredictiveAlert,
    MaintenancePlan,
    MaintenancePriority,
    HealthStatus
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/predictive-maintenance/v2.3", tags=["predictive-maintenance-v2.3"])

# ==================== 请求/响应模型 ====================


class HealthDimensionInput(BaseModel):
    """健康维度输入"""
    dimension: str = Field(..., description="维度名称 (cpu, memory, error_rate, latency, throughput)")
    score: float = Field(..., ge=0, le=100, description="维度得分 (0-100)")
    trend: str = Field(default="stable", description="趋势 (improving, stable, degrading)")
    metrics: Dict[str, float] = Field(default_factory=dict, description="详细指标")


class HealthScoreRequest(BaseModel):
    """健康度评分请求"""
    service_name: str = Field(..., description="服务名称")
    dimensions: List[HealthDimensionInput] = Field(default_factory=list, description="维度列表")


class HealthScoreResponse(BaseModel):
    """健康度评分响应"""
    service_name: str
    overall_score: float
    status: str
    dimensions: List[Dict[str, Any]]
    trend: str
    risk_factors: List[str]
    recommendations: List[str]
    timestamp: str


class RULPredictionRequest(BaseModel):
    """RUL 预测请求"""
    service_name: str = Field(..., description="服务名称")
    component_name: str = Field(..., description="组件名称")


class RULPredictionResponse(BaseModel):
    """RUL 预测响应"""
    service_name: str
    component_name: str
    current_rul_hours: float
    current_rul_days: float
    confidence_interval: List[float]
    confidence_level: float
    predicted_failure_time: str
    failure_probability: float
    degradation_rate: float
    degradation_factors: List[str]
    recommended_actions: List[str]
    maintenance_urgency: str


class PredictiveAlertResponse(BaseModel):
    """预测性告警响应"""
    alert_id: str
    service_name: str
    alert_type: str
    predicted_event: str
    predicted_time: str
    hours_until_event: float
    probability: float
    severity: str
    priority: str
    title: str
    description: str
    affected_services: List[str]
    recommended_actions: List[str]


class MaintenanceTaskInput(BaseModel):
    """维护任务输入"""
    type: str = Field(..., description="维护类型 (preventive, corrective, upgrade, patch)")
    duration_hours: float = Field(..., gt=0, description="预计持续时间 (小时)")
    requires_downtime: bool = Field(default=False, description="是否需要停机")
    urgency: str = Field(default="medium", description="紧急程度 (urgent, high, medium, low)")
    tasks: List[str] = Field(default_factory=list, description="任务列表")


class MaintenancePlanRequest(BaseModel):
    """维护计划请求"""
    service_name: str = Field(..., description="服务名称")
    maintenance_items: List[MaintenanceTaskInput] = Field(..., description="维护项目列表")


class MaintenancePlanResponse(BaseModel):
    """维护计划响应"""
    plan_id: str
    service_name: str
    maintenance_items: List[Dict[str, Any]]
    total_estimated_cost: float
    total_downtime_hours: float
    overall_risk: str
    optimization_notes: List[str]


class DashboardResponse(BaseModel):
    """仪表盘响应"""
    summary: Dict[str, Any]
    health_scores: List[Dict[str, Any]]
    active_alerts: List[Dict[str, Any]]
    rul_predictions: List[Dict[str, Any]]
    alert_stats: Dict[str, Any]


# ==================== 健康度评分 API ====================


@router.post("/health/record", response_model=HealthScoreResponse, summary="记录健康维度")
async def record_health_dimension(request: HealthScoreRequest):
    """
    记录服务健康维度得分并计算综合健康度

    - **service_name**: 服务名称
    - **dimensions**: 维度列表，包含：
      - dimension: 维度名称 (cpu, memory, error_rate, latency, throughput)
      - score: 维度得分 (0-100)
      - trend: 趋势 (improving, stable, degrading)
      - metrics: 详细指标数据
    """
    engine = get_predictive_maintenance_v2_engine()

    # 记录所有维度
    for dim in request.dimensions:
        engine.record_health_dimension(
            service_name=request.service_name,
            dimension=dim.dimension,
            score=dim.score,
            trend=dim.trend,
            metrics=dim.metrics
        )

    # 计算综合健康度
    health_score = engine.calculate_health_score(request.service_name)

    if not health_score:
        raise HTTPException(status_code=400, detail="无法计算健康度，请确保已记录足够的维度数据")

    return HealthScoreResponse(
        service_name=health_score.service_name,
        overall_score=health_score.overall_score,
        status=health_score.status.value,
        dimensions=[d.to_dict() for d in health_score.dimensions],
        trend=health_score.trend,
        risk_factors=health_score.risk_factors,
        recommendations=health_score.recommendations,
        timestamp=health_score.timestamp.isoformat()
    )


@router.get("/health/{service_name}", response_model=HealthScoreResponse, summary="获取健康度")
async def get_health_score(service_name: str):
    """
    获取服务当前健康度评分

    - **service_name**: 服务名称
    """
    engine = get_predictive_maintenance_v2_engine()
    health_score = engine.calculate_health_score(service_name)

    if not health_score:
        raise HTTPException(
            status_code=404,
            detail=f"未找到服务 {service_name} 的健康度数据，请先记录维度得分"
        )

    return HealthScoreResponse(
        service_name=health_score.service_name,
        overall_score=health_score.overall_score,
        status=health_score.status.value,
        dimensions=[d.to_dict() for d in health_score.dimensions],
        trend=health_score.trend,
        risk_factors=health_score.risk_factors,
        recommendations=health_score.recommendations,
        timestamp=health_score.timestamp.isoformat()
    )


@router.get("/health/{service_name}/history", response_model=List[Dict[str, Any]], summary="获取健康历史")
async def get_health_history(
    service_name: str,
    limit: int = Query(default=24, ge=1, le=100, description="返回记录数")
):
    """
    获取服务健康度历史记录

    - **service_name**: 服务名称
    - **limit**: 返回记录数 (1-100)
    """
    engine = get_predictive_maintenance_v2_engine()
    return engine._health_service.get_health_history(service_name, limit)


@router.get("/health", response_model=List[HealthScoreResponse], summary="获取所有服务健康度")
async def get_all_health_scores():
    """获取所有服务的健康度评分"""
    engine = get_predictive_maintenance_v2_engine()
    scores = engine._health_service.get_all_health_scores()

    return [
        HealthScoreResponse(
            service_name=s["service_name"],
            overall_score=s["overall_score"],
            status=s["status"],
            dimensions=s["dimensions"],
            trend=s.get("trend", "stable"),
            risk_factors=s.get("risk_factors", []),
            recommendations=s.get("recommendations", []),
            timestamp=s["timestamp"]
        )
        for s in scores
    ]


# ==================== RUL 预测 API ====================


@router.post("/rul/predict", response_model=RULPredictionResponse, summary="预测剩余寿命")
async def predict_rul(request: RULPredictionRequest):
    """
    预测服务/组件的剩余寿命 (RUL)

    - **service_name**: 服务名称
    - **component_name**: 组件名称
    """
    engine = get_predictive_maintenance_v2_engine()

    # 首先需要有一些健康度数据
    # 在实际使用中，这些数据应该由监控系统持续记录
    rul = engine.predict_rul(request.service_name, request.component_name)

    if not rul:
        raise HTTPException(
            status_code=400,
            detail="无法预测 RUL，请确保已记录足够的健康度历史数据"
        )

    return RULPredictionResponse(
        service_name=rul.service_name,
        component_name=rul.component_name,
        current_rul_hours=rul.current_rul_hours,
        current_rul_days=rul.current_rul_days,
        confidence_interval=rul.confidence_interval_lower,
        confidence_level=rul.confidence_level,
        predicted_failure_time=rul.predicted_failure_time.isoformat(),
        failure_probability=rul.failure_probability,
        degradation_rate=rul.degradation_rate,
        degradation_factors=rul.degradation_factors,
        recommended_actions=rul.recommended_actions,
        maintenance_urgency=rul.maintenance_urgency.value
    )


@router.get("/rul/{service_name}/{component_name}", response_model=RULPredictionResponse, summary="获取 RUL 预测")
async def get_rul_prediction(service_name: str, component_name: str):
    """
    获取指定服务组件的 RUL 预测

    - **service_name**: 服务名称
    - **component_name**: 组件名称
    """
    engine = get_predictive_maintenance_v2_engine()
    rul = engine.predict_rul(service_name, component_name)

    if not rul:
        raise HTTPException(
            status_code=404,
            detail=f"未找到 {service_name}/{component_name} 的 RUL 预测数据"
        )

    return RULPredictionResponse(
        service_name=rul.service_name,
        component_name=rul.component_name,
        current_rul_hours=rul.current_rul_hours,
        current_rul_days=rul.current_rul_days,
        confidence_interval=[rul.confidence_interval_lower, rul.confidence_interval_upper],
        confidence_level=rul.confidence_level,
        predicted_failure_time=rul.predicted_failure_time.isoformat(),
        failure_probability=rul.failure_probability,
        degradation_rate=rul.degradation_rate,
        degradation_factors=rul.degradation_factors,
        recommended_actions=rul.recommended_actions,
        maintenance_urgency=rul.maintenance_urgency.value
    )


@router.get("/rul", response_model=List[Dict[str, Any]], summary="获取所有 RUL 预测")
async def get_all_rul_predictions():
    """获取所有服务组件的 RUL 预测"""
    engine = get_predictive_maintenance_v2_engine()
    return engine._rul_predictor.get_all_rul_predictions()


# ==================== 预测性告警 API ====================


@router.post("/alerts/generate", response_model=List[PredictiveAlertResponse], summary="生成预测性告警")
async def generate_predictive_alerts(
    service_name: Optional[str] = Query(default=None, description="服务名称，不传则生成所有服务的告警")
):
    """
    生成预测性告警

    - **service_name**: 可选，指定服务名称
    """
    engine = get_predictive_maintenance_v2_engine()
    alerts = engine.generate_predictive_alerts(service_name)

    return [
        PredictiveAlertResponse(
            alert_id=a["alert_id"],
            service_name=a["service_name"],
            alert_type=a["alert_type"],
            predicted_event=a["predicted_event"],
            predicted_time=a["predicted_time"],
            hours_until_event=a["hours_until_event"],
            probability=a["probability"],
            severity=a["severity"],
            priority=a["priority"],
            title=a["title"],
            description=a["description"],
            affected_services=a.get("affected_services", []),
            recommended_actions=a.get("recommended_actions", [])
        )
        for a in alerts
    ]


@router.get("/alerts", response_model=List[PredictiveAlertResponse], summary="获取活跃告警")
async def get_active_alerts(
    service_name: Optional[str] = Query(default=None, description="服务名称"),
    priority: Optional[str] = Query(default=None, description="优先级 (urgent, high, medium, low)"),
    limit: int = Query(default=50, ge=1, le=200, description="返回记录数")
):
    """
    获取活跃告警列表

    - **service_name**: 可选，按服务过滤
    - **priority**: 可选，按优先级过滤
    - **limit**: 返回记录数 (1-200)
    """
    engine = get_predictive_maintenance_v2_engine()

    priority_enum = None
    if priority:
        try:
            priority_enum = MaintenancePriority(priority)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的优先级：{priority}，有效值：urgent, high, medium, low"
            )

    alerts = engine._alert_engine.get_active_alerts(
        service_name=service_name,
        priority=priority_enum,
        limit=limit
    )

    return [
        PredictiveAlertResponse(
            alert_id=a["alert_id"],
            service_name=a["service_name"],
            alert_type=a["alert_type"],
            predicted_event=a["predicted_event"],
            predicted_time=a["predicted_time"],
            hours_until_event=a["hours_until_event"],
            probability=a["probability"],
            severity=a["severity"],
            priority=a["priority"],
            title=a["title"],
            description=a["description"],
            affected_services=a.get("affected_services", []),
            recommended_actions=a.get("recommended_actions", [])
        )
        for a in alerts
    ]


@router.post("/alerts/{alert_id}/acknowledge", summary="确认告警")
async def acknowledge_alert(alert_id: str, user: str = Query(..., description="确认人")):
    """
    确认告警

    - **alert_id**: 告警 ID
    - **user**: 确认人
    """
    engine = get_predictive_maintenance_v2_engine()

    if not engine._alert_engine.acknowledge_alert(alert_id, user):
        raise HTTPException(status_code=404, detail=f"未找到告警 {alert_id}")

    return {"status": "success", "message": f"告警 {alert_id} 已确认"}


@router.post("/alerts/{alert_id}/dismiss", summary="解除告警")
async def dismiss_alert(alert_id: str, reason: str = Query(default="", description="解除原因")):
    """
    解除告警

    - **alert_id**: 告警 ID
    - **reason**: 解除原因
    """
    engine = get_predictive_maintenance_v2_engine()

    if not engine._alert_engine.dismiss_alert(alert_id, reason):
        raise HTTPException(status_code=404, detail=f"未找到告警 {alert_id}")

    return {"status": "success", "message": f"告警 {alert_id} 已解除"}


@router.get("/alerts/stats", response_model=Dict[str, Any], summary="获取告警统计")
async def get_alert_stats():
    """获取告警统计数据"""
    engine = get_predictive_maintenance_v2_engine()
    return engine._alert_engine.get_alert_stats()


# ==================== 维护计划 API ====================


@router.post("/maintenance/plan", response_model=MaintenancePlanResponse, summary="创建维护计划")
async def create_maintenance_plan(request: MaintenancePlanRequest):
    """
    创建服务维护计划

    - **service_name**: 服务名称
    - **maintenance_items**: 维护项目列表，包含：
      - type: 维护类型 (preventive, corrective, upgrade, patch)
      - duration_hours: 预计持续时间
      - requires_downtime: 是否需要停机
      - urgency: 紧急程度 (urgent, high, medium, low)
      - tasks: 任务列表
    """
    engine = get_predictive_maintenance_v2_engine()

    maintenance_items = [
        {
            "type": item.type,
            "duration_hours": item.duration_hours,
            "requires_downtime": item.requires_downtime,
            "urgency": MaintenancePriority(item.urgency) if item.urgency else MaintenancePriority.MEDIUM,
            "tasks": item.tasks
        }
        for item in request.maintenance_items
    ]

    plan = engine.create_maintenance_plan(request.service_name, maintenance_items)

    return MaintenancePlanResponse(
        plan_id=plan.plan_id,
        service_name=plan.service_name,
        maintenance_items=[item.to_dict() for item in plan.maintenance_items],
        total_estimated_cost=plan.total_estimated_cost,
        total_downtime_hours=plan.total_downtime_hours,
        overall_risk=plan.overall_risk,
        optimization_notes=plan.optimization_notes
    )


@router.get("/maintenance/history", response_model=List[Dict[str, Any]], summary="获取维护历史")
async def get_maintenance_history(
    service_name: Optional[str] = Query(default=None, description="服务名称"),
    limit: int = Query(default=20, ge=1, le=100, description="返回记录数")
):
    """
    获取维护历史记录

    - **service_name**: 可选，按服务过滤
    - **limit**: 返回记录数 (1-100)
    """
    engine = get_predictive_maintenance_v2_engine()
    return engine._maintenance_optimizer.get_maintenance_history(service_name, limit)


# ==================== 仪表盘 API ====================


@router.get("/dashboard", response_model=DashboardResponse, summary="获取仪表盘数据")
async def get_dashboard():
    """
    获取预测性维护仪表盘数据

    包含：
    - 总体摘要 (服务数、平均健康度、紧急告警数)
    - 所有服务健康度
    - 活跃告警
    - RUL 预测
    - 告警统计
    """
    engine = get_predictive_maintenance_v2_engine()
    return engine.get_dashboard_data()


# ==================== 配置 API ====================


@router.post("/config/business-hours", summary="设置业务时段")
async def set_business_hours(
    service_name: str = Query(..., description="服务名称"),
    low_traffic_hour: int = Query(..., ge=0, le=23, description="低峰时段 (小时)"),
    high_traffic_hour: int = Query(..., ge=0, le=23, description="高峰时段 (小时)")
):
    """
    设置服务的业务低峰/高峰时段，用于优化维护窗口调度

    - **service_name**: 服务名称
    - **low_traffic_hour**: 低峰时段 (0-23)
    - **high_traffic_hour**: 高峰时段 (0-23)
    """
    engine = get_predictive_maintenance_v2_engine()
    engine._maintenance_optimizer.set_business_hours(service_name, low_traffic_hour, high_traffic_hour)

    return {
        "status": "success",
        "message": f"已设置 {service_name} 的业务时段：低峰={low_traffic_hour}点，高峰={high_traffic_hour}点"
    }


@router.post("/config/dependencies", summary="设置服务依赖")
async def set_service_dependencies(
    service_name: str = Query(..., description="服务名称"),
    dependencies: List[str] = Body(..., description="依赖服务列表")
):
    """
    设置服务依赖关系，用于影响分析和告警传播

    - **service_name**: 服务名称
    - **dependencies**: 依赖的服务列表
    """
    engine = get_predictive_maintenance_v2_engine()
    engine._alert_engine.set_service_dependencies(service_name, dependencies)

    return {
        "status": "success",
        "message": f"已设置 {service_name} 的依赖服务：{dependencies}"
    }
