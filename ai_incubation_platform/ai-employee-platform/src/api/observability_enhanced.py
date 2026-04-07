"""
P5 AI 可观测性面板增强 API

提供:
- 实时执行追踪 (WebSocket 支持)
- Token 消耗分析面板
- 决策树可视化
- 性能指标监控
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from config.database import get_db
from middleware.auth import get_current_user_id, get_current_tenant_id
from services.observability_enhanced_service import ObservabilityEnhancedService

router = APIRouter(prefix="/api/observability-enhanced", tags=["Observability Enhanced"])


def get_observability_enhanced_service(db: Session) -> ObservabilityEnhancedService:
    """获取可观测性增强服务实例"""
    return ObservabilityEnhancedService(db)


# ============== 实时执行追踪 ==============

@router.get("/executions/{execution_id}/realtime", summary="获取实时执行状态", response_model=dict)
async def get_realtime_execution(
    execution_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """获取 AI 执行的实时状态信息"""
    service = get_observability_enhanced_service(db)
    result = service.get_realtime_execution_status(execution_id, tenant_id)

    if not result:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    return {"execution": result}


@router.post("/executions/{execution_id}/subscribe", summary="订阅执行更新", response_model=dict)
async def subscribe_execution_updates(
    execution_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """订阅执行更新事件"""
    # 验证执行是否存在
    service = get_observability_enhanced_service(db)
    execution = service.db.query(service.__class__.__module__.replace('services.observability_enhanced_service', 'models.observability_models').split('.')[-1] if hasattr(service, 'db') else 'AgentExecutionDB')

    service = get_observability_enhanced_service(db)
    subscription = service.subscribe_execution_updates(execution_id)

    return {
        "subscription": subscription,
        "websocket_endpoint": f"/api/ws/observability/{execution_id}"
    }


# ============== Token 消耗分析 ==============

@router.get("/analysis/token-usage", summary="Token 使用分析", response_model=dict)
async def analyze_token_usage(
    employee_id: Optional[str] = Query(None, description="AI 员工 ID"),
    days: int = Query(30, ge=1, le=90, description="分析天数"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """分析 Token 使用情况，包括按天/模型/步骤的统计"""
    service = get_observability_enhanced_service(db)
    analysis = service.analyze_token_usage(
        employee_id=employee_id,
        tenant_id=tenant_id,
        days=days
    )

    return {"analysis": analysis}


@router.get("/analysis/token-usage/top-steps", summary="Top Token 消耗步骤", response_model=dict)
async def get_top_token_steps(
    days: int = Query(30, ge=1, le=90, description="分析天数"),
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """获取 Token 消耗最多的步骤"""
    service = get_observability_enhanced_service(db)
    analysis = service.analyze_token_usage(tenant_id=tenant_id, days=days)

    top_steps = analysis.get("top_steps", [])[:limit]

    return {
        "top_steps": top_steps,
        "period_days": days
    }


# ============== 决策树可视化 ==============

@router.get("/executions/{execution_id}/decision-tree", summary="获取决策树", response_model=dict)
async def get_decision_tree(
    execution_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """获取 AI 执行的决策树可视化数据"""
    service = get_observability_enhanced_service(db)
    tree = service.get_decision_tree(execution_id, tenant_id)

    if not tree:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    return {"decision_tree": tree}


# ============== 性能指标监控 ==============

@router.get("/metrics/performance", summary="性能指标聚合", response_model=dict)
async def get_performance_metrics(
    employee_id: Optional[str] = Query(None, description="AI 员工 ID"),
    days: int = Query(30, ge=1, le=90, description="分析天数"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """获取性能指标聚合数据"""
    service = get_observability_enhanced_service(db)
    metrics = service.get_performance_metrics(
        employee_id=employee_id,
        tenant_id=tenant_id,
        days=days
    )

    return {"metrics": metrics}


@router.get("/metrics/errors", summary="错误分析", response_model=dict)
async def analyze_errors(
    employee_id: Optional[str] = Query(None, description="AI 员工 ID"),
    days: int = Query(30, ge=1, le=90, description="分析天数"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """分析错误情况，包括错误模式和趋势"""
    service = get_observability_enhanced_service(db)
    errors = service.analyze_errors(
        employee_id=employee_id,
        tenant_id=tenant_id,
        days=days
    )

    return {"errors": errors}


# ============== 增强型可观测性面板 ==============

@router.get("/dashboard-enhanced", summary="增强型可观测性面板", response_model=dict)
async def get_enhanced_dashboard(
    days: int = Query(30, ge=1, le=90, description="分析天数"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """获取增强型可观测性面板数据"""
    service = get_observability_enhanced_service(db)
    dashboard = service.get_enhanced_dashboard(tenant_id, days)

    return {"dashboard": dashboard}


# ============== 流式事件 ==============

@router.get("/executions/{execution_id}/event-stream", summary="获取事件流", response_model=dict)
async def get_event_stream(
    execution_id: str,
    since_sequence: int = Query(0, ge=0, description="起始事件序号"),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """获取执行事件流 (用于轮询或 WebSocket 推送)"""
    service = get_observability_enhanced_service(db)
    events = service.get_execution_event_stream(execution_id, tenant_id, since_sequence)

    return {
        "events": events,
        "total": len(events)
    }
