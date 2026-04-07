"""
运行态优化 API：指标、用户使用行为、综合分析、代码变更提案。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, HTTPException, Depends, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from core.config import config
from models.analysis import MetricsSnapshot, RouteUsageStat, UsageSummary
from services.optimizer_service import optimizer_service
from models.strategy import RuntimeStrategyExecutionPlan
from core.alert_engine import alert_engine, AlertRule, AlertSeverity, AlertStatus, AlertCondition, AlertOperator, AlertConditionType, NotificationConfig, NotificationChannelType
from core.service_map import service_map, DependencyType
from core.anomaly_detector import anomaly_detector
from core.root_cause_analysis import root_cause_analyzer

router = APIRouter(prefix="/api/runtime", tags=["runtime"])


async def check_production_mode_write_access():
    """生产模式下禁止写入操作的依赖检查"""
    if config.production_insight_mode:
        raise HTTPException(
            status_code=403,
            detail="Production insight mode is enabled: write operations are not allowed"
        )
    if not config.allow_data_modification:
        raise HTTPException(
            status_code=403,
            detail="Data modification is disabled: write operations are not allowed"
        )


def _error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    """统一的错误返回结构：方便前端/调用方按 error_code 做分支处理。"""
    content: Dict[str, Any] = {
        "status": "error",
        "error_code": error_code,
        "message": message,
    }
    if details:
        content["details"] = details
    return JSONResponse(status_code=status_code, content=content)


def _map_value_error_to_code(e: ValueError) -> str:
    msg = str(e)
    if msg.startswith("Unknown strategy_id:"):
        return "UNKNOWN_STRATEGY_ID"
    if msg.startswith("Disabled strategy_id:"):
        return "DISABLED_STRATEGY_ID"
    return "INVALID_REQUEST"


class AnalyzeRequest(BaseModel):

    snapshot: MetricsSnapshot

    config_hint: Optional[str] = Field(

        None, description="当前关键配置摘要，如连接池大小、worker 数"

    )



class HolisticRequest(BaseModel):

    """指标 + 用户使用情况，一起做优化分析。"""


    snapshot: MetricsSnapshot

    usage: Optional[UsageSummary] = None

    config_hint: Optional[str] = None

    strategy_plan: Optional[RuntimeStrategyExecutionPlan] = Field(
        default=None,
        description="可选：本次运行态策略执行计划（策略选择/trace_id/可选LLM）",
    )



class CodeProposalsRequest(BaseModel):

    """与 HolisticRequest 相同输入，用于生成代码级变更草案。"""


    snapshot: MetricsSnapshot

    usage: Optional[UsageSummary] = None

    config_hint: Optional[str] = None

    strategy_plan: Optional[RuntimeStrategyExecutionPlan] = Field(
        default=None,
        description="可选：本次运行态策略执行计划（策略选择/trace_id/可选LLM）",
    )

    language: str = Field("python", description="主语言，便于生成片段风格")



@router.post("/metrics", dependencies=[Depends(check_production_mode_write_access)])
async def ingest_metrics(body: MetricsSnapshot) -> Dict[str, Any]:
    """上报一次指标快照（可批量扩展为时序存储）。"""
    return optimizer_service.record_metrics(body.model_dump())




@router.post("/usage", dependencies=[Depends(check_production_mode_write_access)])
async def ingest_usage(body: UsageSummary) -> Dict[str, Any]:
    """上报用户使用情况聚合（路由热度、功能采纳等）。"""
    return optimizer_service.record_usage(body.model_dump())




@router.post("/analyze")

async def analyze_runtime(body: AnalyzeRequest) -> Dict[str, Any]:

    """仅根据指标与配置生成建议（不含行为数据）。"""

    return optimizer_service.analyze(

        body.snapshot.model_dump(), body.config_hint

    )




@router.post("/holistic-analyze")

async def holistic_analyze(body: HolisticRequest) -> Dict[str, Any]:

    """

    综合分析：CPU/内存/延迟/错误率 **与** 用户使用情况一起推理，

    例如：热点路由慢、低采纳功能、错误与路由关联等。

    """

    usage_dict = body.usage.model_dump() if body.usage else None

    try:
        return optimizer_service.holistic_analyze(
            body.snapshot.model_dump(),
            body.config_hint,
            usage_dict,
            strategy_plan=body.strategy_plan,
        )
    except ValueError as e:
        return _error_response(
            status_code=400,
            error_code=_map_value_error_to_code(e),
            message=str(e),
        )




@router.post("/code-proposals")

async def code_proposals(body: CodeProposalsRequest) -> Dict[str, Any]:

    """

    在综合分析基础上输出 **代码变更草案**（示例片段 / 占位 diff）。

    生产环境应替换为：LLM + 仓库上下文生成 unified diff，再经 CI 与人工审核后合并。

    """

    usage_dict = body.usage.model_dump() if body.usage else None

    try:
        return optimizer_service.code_proposals(
            body.snapshot.model_dump(),
            usage_dict,
            body.config_hint,
            language=body.language,
            strategy_plan=body.strategy_plan,
        )
    except ValueError as e:
        return _error_response(
            status_code=400,
            error_code=_map_value_error_to_code(e),
            message=str(e),
        )




@router.get("/recommendations")
async def list_recommendations(service_name: Optional[str] = None) -> Dict[str, Any]:
    """最近一次 holistic 或纯指标分析的建议列表。"""
    return optimizer_service.latest_recommendations(service_name)


# 策略管理API
from models.strategy import StrategyCreateRequest, StrategyUpdateRequest, AnalysisStrategy
from typing import Optional


@router.get("/strategies")
async def list_strategies(type: Optional[str] = None, enabled_only: bool = True) -> Dict[str, Any]:
    """获取所有分析策略"""
    return optimizer_service.get_strategies(type_filter=type, enabled_only=enabled_only)


@router.post("/strategies", dependencies=[Depends(check_production_mode_write_access)])
async def create_strategy(strategy: StrategyCreateRequest) -> Dict[str, Any]:
    """创建新的分析策略"""
    return optimizer_service.add_strategy(strategy.model_dump())


@router.get("/strategies/{strategy_id}")
async def get_strategy(strategy_id: str) -> Dict[str, Any]:
    """获取指定策略详情"""
    from core import strategy_engine
    strategy = strategy_engine.get_strategy(strategy_id)
    if not strategy:
        return _error_response(
            status_code=404,
            error_code="STRATEGY_NOT_FOUND",
            message=f"Strategy {strategy_id} not found",
        )
    return strategy.model_dump()


@router.put("/strategies/{strategy_id}", dependencies=[Depends(check_production_mode_write_access)])
async def update_strategy(strategy_id: str, update: StrategyUpdateRequest) -> Dict[str, Any]:
    """更新策略配置"""
    update_data = update.model_dump(exclude_unset=True)
    result = optimizer_service.update_strategy(strategy_id, update_data)
    if result.get("status") == "error":
        return _error_response(
            status_code=404,
            error_code="STRATEGY_NOT_FOUND",
            message=result.get("message", f"Strategy {strategy_id} not found"),
        )
    return result


@router.delete("/strategies/{strategy_id}", dependencies=[Depends(check_production_mode_write_access)])
async def delete_strategy(strategy_id: str) -> Dict[str, Any]:
    """删除指定策略"""
    result = optimizer_service.delete_strategy(strategy_id)
    if result.get("status") == "error":
        return _error_response(
            status_code=404,
            error_code="STRATEGY_NOT_FOUND",
            message=result.get("message", f"Strategy {strategy_id} not found"),
        )
    return result


# ==================== 告警系统 API ====================

class AlertRuleCreateRequest(BaseModel):
    """告警规则创建请求"""
    name: str
    description: str
    service_name: Optional[str] = None
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    severity: AlertSeverity = AlertSeverity.WARNING
    notification_configs: List[Dict[str, Any]] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    cooldown_seconds: int = 300
    enabled: bool = True


class AlertRuleUpdateRequest(BaseModel):
    """告警规则更新请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    service_name: Optional[str] = None
    severity: Optional[AlertSeverity] = None
    tags: Optional[List[str]] = None
    cooldown_seconds: Optional[int] = None
    enabled: Optional[bool] = None


@router.get("/alerts")
async def list_alerts(
    service_name: Optional[str] = None,
    severity: Optional[AlertSeverity] = None,
    status: Optional[AlertStatus] = None
) -> Dict[str, Any]:
    """获取活跃告警列表"""
    alerts = alert_engine.get_active_alerts(service_name, severity, status)
    return {
        "alerts": [
            {
                "id": a.id,
                "rule_id": a.rule_id,
                "rule_name": a.rule_name,
                "service_name": a.service_name,
                "severity": a.severity.value,
                "status": a.status.value,
                "title": a.title,
                "message": a.message,
                "evidence": a.evidence,
                "triggered_at": a.triggered_at.isoformat(),
                "tags": a.tags
            }
            for a in alerts
        ],
        "total": len(alerts)
    }


@router.get("/alerts/history")
async def list_alert_history(
    service_name: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """获取告警历史"""
    history = alert_engine.get_alert_history(service_name, limit)
    return {
        "history": [
            {
                "id": h.id,
                "rule_id": h.rule_id,
                "rule_name": h.rule_name,
                "service_name": h.service_name,
                "severity": h.severity.value,
                "status": h.status.value,
                "title": h.title,
                "message": h.message,
                "triggered_at": h.triggered_at.isoformat(),
                "resolved_at": h.resolved_at.isoformat() if h.resolved_at else None
            }
            for h in history
        ],
        "total": len(history)
    }


@router.post("/alerts/{alert_id}/acknowledge", dependencies=[Depends(check_production_mode_write_access)])
async def acknowledge_alert(alert_id: str, acknowledged_by: str = "admin") -> Dict[str, Any]:
    """确认告警"""
    success = alert_engine.acknowledge_alert(alert_id, acknowledged_by)
    if success:
        return {"status": "acknowledged", "alert_id": alert_id}
    return {"status": "error", "message": f"Alert {alert_id} not found"}


@router.post("/alerts/{alert_id}/resolve", dependencies=[Depends(check_production_mode_write_access)])
async def resolve_alert(alert_id: str) -> Dict[str, Any]:
    """解决告警"""
    success = alert_engine.resolve_alert(alert_id)
    if success:
        return {"status": "resolved", "alert_id": alert_id}
    return {"status": "error", "message": f"Alert {alert_id} not found"}


@router.get("/alerts/rules")
async def list_alert_rules(
    service_name: Optional[str] = None,
    enabled_only: bool = True
) -> Dict[str, Any]:
    """获取告警规则列表"""
    rules = alert_engine.list_rules(service_name, enabled_only)
    return {
        "rules": [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "service_name": r.service_name,
                "severity": r.severity.value,
                "conditions": [
                    {"field": c.field, "operator": c.operator.value, "value": c.value}
                    for c in r.conditions
                ],
                "tags": r.tags,
                "enabled": r.enabled,
                "cooldown_seconds": r.cooldown_seconds
            }
            for r in rules
        ],
        "total": len(rules)
    }


@router.post("/alerts/rules", dependencies=[Depends(check_production_mode_write_access)])
async def create_alert_rule(rule_data: AlertRuleCreateRequest) -> Dict[str, Any]:
    """创建告警规则"""
    import uuid
    rule_id = f"alert-rule-{uuid.uuid4().hex[:8]}"

    conditions = []
    for c in rule_data.conditions:
        conditions.append(AlertCondition(
            field=c.get("field", ""),
            operator=AlertOperator(c.get("operator", "gt")),
            value=c.get("value"),
            condition_type=AlertConditionType(c.get("condition_type", "threshold")),
            window_seconds=c.get("window_seconds", 60),
            min_occurrences=c.get("min_occurrences", 3)
        ))

    notification_configs = []
    for n in rule_data.notification_configs:
        notification_configs.append(NotificationConfig(
            channel_type=NotificationChannelType(n.get("channel_type", "webhook")),
            target=n.get("target", ""),
            template=n.get("template"),
            enabled=n.get("enabled", True)
        ))

    rule = AlertRule(
        id=rule_id,
        name=rule_data.name,
        description=rule_data.description,
        service_name=rule_data.service_name,
        conditions=conditions,
        severity=rule_data.severity,
        notification_configs=notification_configs,
        tags=rule_data.tags,
        enabled=rule_data.enabled,
        cooldown_seconds=rule_data.cooldown_seconds
    )

    alert_engine.add_rule(rule)
    return {"status": "created", "rule_id": rule_id}


@router.get("/alerts/stats")
async def get_alert_stats() -> Dict[str, Any]:
    """获取告警统计"""
    return alert_engine.get_alert_stats()


# ==================== 服务映射 API ====================

@router.get("/service-map")
async def get_service_map() -> Dict[str, Any]:
    """获取服务映射数据（用于可视化）"""
    return service_map.get_service_map_data()


@router.get("/service-map/services")
async def list_services() -> Dict[str, Any]:
    """获取所有服务列表"""
    services = []
    for service_id, service in service_map._services.items():
        services.append({
            "id": service.id,
            "name": service.name,
            "type": service.type,
            "health_status": service.health_status.value,
            "tags": service.tags,
            "metrics": {
                "latency_p50_ms": service.latency_p50_ms,
                "latency_p99_ms": service.latency_p99_ms,
                "error_rate": service.error_rate,
                "requests_per_second": service.requests_per_second,
                "cpu_percent": service.cpu_percent,
                "memory_mb": service.memory_mb
            }
        })
    return {"services": services, "total": len(services)}


@router.get("/service-map/services/{service_id}")
async def get_service(service_id: str) -> Dict[str, Any]:
    """获取服务详情"""
    service = service_map.get_service(service_id)
    if not service:
        return _error_response(
            status_code=404,
            error_code="SERVICE_NOT_FOUND",
            message=f"Service {service_id} not found"
        )

    dependencies = service_map.get_dependencies(service_id)
    upstream = service_map.get_upstream_services(service_id)
    downstream = service_map.get_downstream_services(service_id)

    return {
        "service": {
            "id": service.id,
            "name": service.name,
            "type": service.type,
            "health_status": service.health_status.value,
            "tags": service.tags,
            "metrics": {
                "latency_p50_ms": service.latency_p50_ms,
                "latency_p99_ms": service.latency_p99_ms,
                "error_rate": service.error_rate,
                "requests_per_second": service.requests_per_second,
                "cpu_percent": service.cpu_percent,
                "memory_mb": service.memory_mb,
                "instance_count": service.instance_count
            }
        },
        "dependencies": {
            "upstream": upstream,
            "downstream": downstream,
            "edges": [
                {
                    "id": e.id,
                    "source": e.source_service,
                    "target": e.target_service,
                    "type": e.dependency_type.value,
                    "latency_p99_ms": e.latency_p99_ms,
                    "error_rate": e.error_rate
                }
                for e in dependencies
            ]
        }
    }


@router.get("/service-map/bottlenecks")
async def get_bottlenecks(top_n: int = 5) -> Dict[str, Any]:
    """识别瓶颈服务"""
    bottlenecks = service_map.get_bottleneck_services(top_n)
    return {"bottlenecks": bottlenecks}


@router.get("/service-map/critical-paths")
async def get_critical_paths(max_latency_ms: float = 1000) -> Dict[str, Any]:
    """获取关键路径"""
    paths = service_map.find_critical_paths(max_latency_ms)
    return {
        "critical_paths": [
            {
                "path": p.path,
                "total_latency_ms": p.total_latency_ms,
                "total_error_rate": p.total_error_rate,
                "is_critical": p.is_critical
            }
            for p in paths
        ]
    }


@router.get("/service-map/stats")
async def get_service_map_stats() -> Dict[str, Any]:
    """获取服务映射统计"""
    return service_map.get_stats()


@router.post("/service-map/dependency", dependencies=[Depends(check_production_mode_write_access)])
async def record_dependency(
    source_service: str,
    target_service: str,
    dependency_type: DependencyType = DependencyType.UNKNOWN,
    protocol: Optional[str] = None,
    endpoint: Optional[str] = None,
    latency_ms: Optional[float] = None,
    is_error: bool = False
) -> Dict[str, Any]:
    """记录服务间调用依赖"""
    edge = service_map.record_dependency(
        source_service=source_service,
        target_service=target_service,
        dependency_type=dependency_type,
        protocol=protocol,
        endpoint=endpoint,
        latency_ms=latency_ms,
        is_error=is_error
    )
    return {
        "status": "recorded",
        "edge_id": edge.id,
        "call_count": edge.call_count,
        "error_rate": edge.error_rate
    }


@router.post("/service-map/metrics", dependencies=[Depends(check_production_mode_write_access)])
async def record_service_metrics(
    service_id: str,
    metrics: Dict[str, Any]
) -> Dict[str, Any]:
    """记录服务指标"""
    service_map.record_service_metrics(service_id, metrics)
    return {"status": "recorded", "service_id": service_id}


# ==================== AI 异常检测 API ====================

class AnomalyDetectRequest(BaseModel):
    """异常检测请求"""
    service_name: str
    metric_name: str
    value: float
    timestamp: Optional[str] = None


@router.post("/anomaly/detect", dependencies=[Depends(check_production_mode_write_access)])
async def detect_anomaly(request: AnomalyDetectRequest) -> Dict[str, Any]:
    """检测指标异常"""
    from datetime import datetime

    timestamp = None
    if request.timestamp:
        try:
            timestamp = datetime.fromisoformat(request.timestamp)
        except ValueError:
            pass

    anomaly = anomaly_detector.record_metric(
        service_name=request.service_name,
        metric_name=request.metric_name,
        value=request.value,
        timestamp=timestamp
    )

    if anomaly:
        return {
            "anomaly_detected": True,
            "anomaly": {
                "id": anomaly.id,
                "type": anomaly.anomaly_type.value,
                "severity": anomaly.severity.value,
                "current_value": anomaly.current_value,
                "expected_value": anomaly.expected_value,
                "deviation": anomaly.deviation,
                "confidence": anomaly.confidence,
                "message": anomaly.message
            }
        }
    else:
        return {"anomaly_detected": False, "message": "No anomaly detected"}


@router.get("/anomaly/history")
async def get_anomaly_history(
    service_name: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """获取异常历史"""
    anomalies = anomaly_detector.get_recent_anomalies(service_name, limit)
    return {
        "anomalies": [
            {
                "id": a.id,
                "service_name": a.service_name,
                "metric_name": a.metric_name,
                "anomaly_type": a.anomaly_type.value,
                "severity": a.severity.value,
                "current_value": a.current_value,
                "expected_value": a.expected_value,
                "message": a.message,
                "timestamp": a.timestamp.isoformat(),
                "confidence": a.confidence
            }
            for a in anomalies
        ],
        "total": len(anomalies)
    }


@router.get("/anomaly/stats")
async def get_anomaly_stats(service_name: Optional[str] = None) -> Dict[str, Any]:
    """获取异常统计"""
    return anomaly_detector.get_anomaly_stats(service_name)


@router.get("/anomaly/stats/{service_name}/{metric_name}")
async def get_metric_stats(service_name: str, metric_name: str) -> Dict[str, Any]:
    """获取指标时间序列统计"""
    stats = anomaly_detector.get_time_series_stats(service_name, metric_name)
    if stats:
        return {
            "service_name": service_name,
            "metric_name": metric_name,
            "stats": {
                "mean": stats.mean,
                "std_dev": stats.std_dev,
                "min": stats.min_value,
                "max": stats.max_value,
                "p50": stats.p50,
                "p95": stats.p95,
                "p99": stats.p99,
                "trend_slope": stats.trend_slope,
                "data_points": stats.data_points
            }
        }
    return {"status": "no_data", "message": "Not enough data points for analysis"}


# ==================== 根因分析 API ====================

class RootCauseAnalysisRequest(BaseModel):
    """根因分析请求"""
    target_service: Optional[str] = Field(None, description="目标服务名，不传则分析所有服务")
    lookback_minutes: int = Field(30, description="回溯时间（分钟）")


@router.post("/root-cause/analyze")
async def analyze_root_cause(request: RootCauseAnalysisRequest) -> Dict[str, Any]:
    """执行根因分析"""
    result = root_cause_analyzer.analyze(
        target_service=request.target_service,
        lookback_minutes=request.lookback_minutes
    )
    return result.to_dict()


@router.get("/root-cause/history")
async def get_root_cause_history(limit: int = 10) -> Dict[str, Any]:
    """获取根因分析历史"""
    history = root_cause_analyzer.get_analysis_history(limit)
    return {"history": history, "total": len(history)}


@router.get("/root-cause/propagation-paths")
async def get_propagation_paths(service_id: Optional[str] = None) -> Dict[str, Any]:
    """获取异常传播路径"""
    # 执行一次分析并返回传播路径
    result = root_cause_analyzer.analyze(target_service=service_id)
    return {
        "propagation_paths": [pp.to_dict() for pp in result.propagation_paths],
        "total": len(result.propagation_paths)
    }


@router.get("/root-cause/correlations")
async def get_correlations(service_id: Optional[str] = None) -> Dict[str, Any]:
    """获取指标关联分析结果"""
    # 执行一次分析并返回关联分析
    result = root_cause_analyzer.analyze(target_service=service_id)
    return {
        "correlations": [ca.to_dict() for ca in result.correlations],
        "total": len(result.correlations)
    }


# ==================== 自动采集器 API ====================

@router.get("/collector/status")
async def get_collector_status() -> Dict[str, Any]:
    """获取自动采集器状态"""
    from adapters.metrics.auto_collector import get_auto_collector
    collector = get_auto_collector()
    return collector.get_status()


@router.post("/collector/start")
async def start_collector() -> Dict[str, Any]:
    """启动自动采集"""
    from adapters.metrics.auto_collector import get_auto_collector
    collector = get_auto_collector()
    collector.start()
    return {"status": "started", "message": "Auto collector started"}


@router.post("/collector/stop")
async def stop_collector() -> Dict[str, Any]:
    """停止自动采集"""
    from adapters.metrics.auto_collector import get_auto_collector
    collector = get_auto_collector()
    collector.stop()
    return {"status": "stopped", "message": "Auto collector stopped"}


@router.get("/collector/metrics")
async def get_collected_metrics(
    service_name: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """获取采集的指标数据"""
    from adapters.metrics.auto_collector import get_auto_collector
    collector = get_auto_collector()
    metrics = collector.get_recent_metrics(service_name, limit)
    return {
        "metrics": [
            {
                "service_name": m.service_name,
                "timestamp": m.timestamp.isoformat(),
                "metrics": m.metrics,
                "source": m.source.value,
                "tags": m.tags
            }
            for m in metrics
        ],
        "total": len(metrics)
    }


# ==================== P3 告警系统增强 API ====================

@router.get("/alerts/baselines")
async def list_baselines() -> Dict[str, Any]:
    """获取动态基线列表"""
    from core.alert_enhanced import dynamic_baseline_manager
    baselines = list(dynamic_baseline_manager._baselines.values())
    return {
        "baselines": [
            {
                "metric_name": b.metric_name,
                "service_name": b.service_name,
                "window_hours": b.window_hours,
                "std_multiplier": b.std_multiplier,
                "enabled": b.enabled
            }
            for b in baselines
        ],
        "total": len(baselines)
    }


@router.post("/alerts/baselines", dependencies=[Depends(check_production_mode_write_access)])
async def create_baseline(
    metric_name: str,
    service_name: Optional[str] = None,
    window_hours: int = 24,
    std_multiplier: float = 3.0
) -> Dict[str, Any]:
    """创建动态基线"""
    from core.alert_enhanced import dynamic_baseline_manager, DynamicBaseline
    baseline = DynamicBaseline(
        metric_name=metric_name,
        service_name=service_name,
        window_hours=window_hours,
        std_multiplier=std_multiplier
    )
    key = dynamic_baseline_manager.create_baseline(baseline)
    return {"status": "created", "key": key}


@router.get("/alerts/baselines/check")
async def check_dynamic_threshold(
    service_name: str,
    metric_name: str,
    value: float
) -> Dict[str, Any]:
    """检查动态阈值"""
    from core.alert_enhanced import dynamic_baseline_manager
    result = dynamic_baseline_manager.get_dynamic_thresholds(service_name, metric_name, value)
    if result:
        return {
            "metric_name": metric_name,
            "service_name": service_name,
            "current_value": value,
            "thresholds": result
        }
    return {"status": "no_baseline", "message": "No baseline configured for this metric"}


@router.get("/alerts/suppression/rules")
async def list_suppression_rules() -> Dict[str, Any]:
    """获取告警抑制规则列表"""
    from core.alert_enhanced import suppression_engine
    rules = suppression_engine.list_rules()
    return {
        "rules": [
            {
                "id": r.id,
                "name": r.name,
                "rule_type": r.rule_type.value,
                "enabled": r.enabled,
                "description": r.description
            }
            for r in rules
        ],
        "total": len(rules)
    }


@router.post("/alerts/suppression/rules", dependencies=[Depends(check_production_mode_write_access)])
async def create_suppression_rule(
    name: str,
    rule_type: str,
    enabled: bool = True,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """创建告警抑制规则"""
    from core.alert_enhanced import suppression_engine, SuppressionRule, SuppressionRuleType
    import uuid
    rule = SuppressionRule(
        id=f"suppression-{uuid.uuid4().hex[:8]}",
        name=name,
        rule_type=SuppressionRuleType(rule_type),
        enabled=enabled,
        description=description
    )
    rule_id = suppression_engine.create_suppression_rule(rule)
    return {"status": "created", "rule_id": rule_id}


@router.get("/alerts/escalation/policies")
async def list_escalation_policies() -> Dict[str, Any]:
    """获取告警升级策略列表"""
    from core.alert_enhanced import escalation_manager
    policies = escalation_manager.list_policies()
    return {
        "policies": [
            {
                "id": p.id,
                "name": p.name,
                "policy_type": p.policy_type.value,
                "ack_timeout_minutes": p.ack_timeout_minutes,
                "notify_users": p.notify_users,
                "enabled": p.enabled
            }
            for p in policies
        ],
        "total": len(policies)
    }


@router.get("/alerts/analytics")
async def get_alert_analytics(
    days: int = 7
) -> Dict[str, Any]:
    """获取告警分析"""
    from core.alert_enhanced import analytics_engine
    from datetime import timedelta
    time_range_start = datetime.utcnow() - timedelta(days=days)
    analytics = analytics_engine.analyze(time_range_start=time_range_start)
    return {
        "time_range": {
            "start": analytics.time_range_start.isoformat(),
            "end": analytics.time_range_end.isoformat()
        },
        "total_alerts": analytics.total_alerts,
        "alerts_by_severity": analytics.alerts_by_severity,
        "alerts_by_service": analytics.alerts_by_service,
        "alerts_by_status": analytics.alerts_by_status,
        "mttr_minutes": analytics.mttr_minutes,
        "avg_resolution_time_seconds": analytics.avg_resolution_time_seconds,
        "top_alert_rules": analytics.top_alert_rules
    }


# ==================== P3 AI 异常检测增强 API ====================

@router.post("/anomaly/enhanced/detect")
async def detect_anomaly_enhanced(
    service_name: str,
    metric_name: str,
    value: float
) -> Dict[str, Any]:
    """增强型异常检测（多算法融合）"""
    from core.anomaly_enhanced import enhanced_anomaly_detector
    anomaly = enhanced_anomaly_detector.record_metric(service_name, metric_name, value)
    if anomaly:
        return {
            "anomaly_detected": True,
            "anomaly": {
                "id": anomaly.id,
                "type": anomaly.anomaly_type.value,
                "severity": anomaly.severity.value,
                "current_value": anomaly.current_value,
                "confidence": anomaly.confidence,
                "message": anomaly.message,
                "suggested_actions": anomaly.context.get("suggested_actions", [])
            }
        }
    return {"anomaly_detected": False, "message": "No anomaly detected"}


@router.get("/anomaly/enhanced/explanation/{anomaly_id}")
async def get_anomaly_explanation(anomaly_id: str) -> Dict[str, Any]:
    """获取异常详细解释"""
    from core.anomaly_enhanced import enhanced_anomaly_detector
    explanation = enhanced_anomaly_detector.get_anomaly_explanation(anomaly_id)
    if explanation:
        return {"explanation": explanation}
    return {"status": "not_found", "message": f"Anomaly {anomaly_id} not found"}


@router.post("/anomaly/enhanced/feedback")
async def submit_anomaly_feedback(
    anomaly_id: str,
    is_true_positive: bool
) -> Dict[str, Any]:
    """提交异常检测反馈"""
    from core.anomaly_enhanced import enhanced_anomaly_detector
    enhanced_anomaly_detector.submit_feedback(anomaly_id, is_true_positive)
    return {"status": "submitted", "message": "Feedback recorded"}


@router.get("/anomaly/enhanced/performance")
async def get_model_performance() -> Dict[str, Any]:
    """获取 ML 模型性能指标"""
    from core.anomaly_enhanced import enhanced_anomaly_detector
    return enhanced_anomaly_detector.get_model_performance()


@router.post("/anomaly/enhanced/configure")
async def configure_ml_model(
    algorithm: str,
    service_name: Optional[str] = None,
    metric_name: Optional[str] = None
) -> Dict[str, Any]:
    """配置 ML 异常检测模型"""
    from core.anomaly_enhanced import enhanced_anomaly_detector, MLModelConfig, AlgorithmType
    config = MLModelConfig(
        algorithm=AlgorithmType(algorithm),
        service_name=service_name,
        metric_name=metric_name
    )
    key = enhanced_anomaly_detector.configure_ml_model(config)
    return {"status": "configured", "key": key}


# ==================== P3 分布式追踪 API ====================

@router.post("/tracing/start")
async def start_trace(
    name: str,
    operation_name: str,
    service_name: Optional[str] = None
) -> Dict[str, Any]:
    """开始一个新的追踪"""
    from core.tracing import global_tracer, SpanKind
    span = global_tracer.start_trace(
        name=name,
        operation_name=operation_name,
        kind=SpanKind.SERVER
    )
    return {
        "trace_id": span.trace_id,
        "span_id": span.span_id,
        "service_name": service_name or global_tracer.service_name
    }


@router.post("/tracing/{trace_id}/span")
async def create_span(
    trace_id: str,
    name: str,
    operation_name: str,
    service_name: Optional[str] = None
) -> Dict[str, Any]:
    """创建一个新的 Span"""
    from core.tracing import global_tracer, SpanKind
    span = global_tracer.start_span(
        name=name,
        operation_name=operation_name,
        kind=SpanKind.INTERNAL
    )
    return {
        "trace_id": span.trace_id,
        "span_id": span.span_id,
        "parent_span_id": span.parent_span_id
    }


@router.post("/tracing/span/{span_id}/end")
async def end_span(
    span_id: str,
    status: str = "ok"
) -> Dict[str, Any]:
    """结束 Span"""
    from core.tracing import global_tracer, SpanStatus
    span = global_tracer.get_span(span_id)
    if not span:
        return {"status": "not_found", "message": f"Span {span_id} not found"}

    span_status = SpanStatus(status)
    global_tracer.end_span(span, span_status)
    return {"status": "ended", "duration_ms": span.duration_ms}


@router.get("/tracing/{trace_id}")
async def get_trace(trace_id: str) -> Dict[str, Any]:
    """获取追踪详情"""
    from core.tracing import global_tracer
    trace = global_tracer.get_trace(trace_id)
    if trace:
        return {"trace": trace.to_dict()}
    return {"status": "not_found", "message": f"Trace {trace_id} not found"}


@router.get("/tracing/{trace_id}/waterfall")
async def get_trace_waterfall(trace_id: str) -> Dict[str, Any]:
    """获取追踪瀑布图数据"""
    from core.tracing import global_tracer
    result = global_tracer.get_trace_waterfall(trace_id)
    if result:
        return {"waterfall": result}
    return {"status": "not_found", "message": f"Trace {trace_id} not found"}


@router.get("/tracing/search")
async def search_traces(
    service_name: Optional[str] = None,
    operation_name: Optional[str] = None,
    status: Optional[str] = None,
    min_duration_ms: Optional[float] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """搜索追踪"""
    from core.tracing import global_tracer, SpanStatus
    span_status = SpanStatus(status) if status else None
    traces = global_tracer.search_traces(
        service_name=service_name,
        operation_name=operation_name,
        status=span_status,
        min_duration_ms=min_duration_ms,
        limit=limit
    )
    return {
        "traces": [
            {
                "trace_id": t.trace_id,
                "duration_ms": t.duration_ms,
                "service_names": t.service_names,
                "span_count": len(t.spans),
                "status": t.status.value
            }
            for t in traces
        ],
        "total": len(traces)
    }


@router.get("/tracing/service-map")
async def get_tracing_service_map() -> Dict[str, Any]:
    """获取追踪服务调用图"""
    from core.tracing import global_tracer
    return global_tracer.get_service_map()


@router.get("/tracing/slow-traces")
async def get_slow_traces(
    threshold_ms: float = 1000,
    limit: int = 20
) -> Dict[str, Any]:
    """获取慢追踪列表"""
    from core.tracing import global_tracer
    return {
        "slow_traces": global_tracer.get_slow_traces(threshold_ms, limit)
    }


@router.get("/tracing/cross-service-latency/{service_name}")
async def get_cross_service_latency(service_name: str) -> Dict[str, Any]:
    """获取跨服务延迟分析"""
    from core.tracing import global_tracer
    return global_tracer.get_cross_service_latency(service_name)


@router.get("/tracing/stats")
async def get_tracing_stats() -> Dict[str, Any]:
    """获取追踪统计"""
    from core.tracing import global_tracer
    return global_tracer.get_stats()


# ==================== P4 AI 根因推理 API ====================

@router.post("/ai/root-cause/infer")
async def ai_root_cause_infer(
    target_service: Optional[str] = None,
    lookback_minutes: int = 30
) -> Dict[str, Any]:
    """AI 根因推理 v1

    基于图谱和关联分析的根因推理系统
    """
    from core.ai_root_cause import get_ai_root_cause_inference
    from core.service_map import service_map

    inference_engine = get_ai_root_cause_inference()

    # 从服务映射构建图谱
    service_map_data = service_map.get_service_map_data()
    inference_engine.build_graph_from_service_map(service_map_data)

    # 执行推理
    result = inference_engine.infer_root_cause(
        target_service=target_service,
        lookback_minutes=lookback_minutes
    )

    return result


@router.post("/ai/root-cause/record-metric")
async def ai_root_cause_record_metric(
    service_id: str,
    metric_name: str,
    value: float
) -> Dict[str, Any]:
    """记录指标到根因推理引擎"""
    from core.ai_root_cause import get_ai_root_cause_inference

    inference_engine = get_ai_root_cause_inference()
    inference_engine.record_metric(service_id, metric_name, value)

    return {"status": "recorded", "service_id": service_id, "metric_name": metric_name}


@router.post("/ai/root-cause/record-anomaly")
async def ai_root_cause_record_anomaly(
    anomaly: Dict[str, Any]
) -> Dict[str, Any]:
    """记录异常到根因推理引擎"""
    from core.ai_root_cause import get_ai_root_cause_inference

    inference_engine = get_ai_root_cause_inference()
    inference_engine.record_anomaly(anomaly)

    return {"status": "recorded", "anomaly_id": anomaly.get("id")}


@router.get("/ai/root-cause/history")
async def ai_root_cause_history(
    limit: int = 10
) -> Dict[str, Any]:
    """获取根因推理历史"""
    from core.ai_root_cause import get_ai_root_cause_inference

    inference_engine = get_ai_root_cause_inference()
    history = inference_engine.get_inference_history(limit)

    return {"history": history, "total": len(history)}


# ==================== P4 安全增强 API ====================

@router.get("/security/api-keys")
async def list_api_keys() -> Dict[str, Any]:
    """获取 API Key 列表"""
    from core.security import get_api_key_manager

    manager = get_api_key_manager()
    keys = manager.list_keys()
    stats = manager.get_key_stats()

    return {
        "keys": keys,
        "stats": stats
    }


@router.post("/security/api-keys", dependencies=[Depends(check_production_mode_write_access)])
async def create_api_key(
    role: str = "readonly",
    expires_in_days: int = None
) -> Dict[str, Any]:
    """创建新的 API Key"""
    from core.security import get_api_key_manager
    from datetime import datetime, timedelta

    manager = get_api_key_manager()
    new_key = manager.generate_key()

    expires_at = None
    if expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

    manager.add_key(new_key, role=role, expires_at=expires_at)

    return {
        "api_key": new_key,
        "role": role,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "warning": "Save this key securely. It cannot be retrieved later."
    }


@router.post("/security/api-keys/{key_prefix}/revoke", dependencies=[Depends(check_production_mode_write_access)])
async def revoke_api_key(key_prefix: str) -> Dict[str, Any]:
    """撤销 API Key"""
    from core.security import get_api_key_manager

    manager = get_api_key_manager()

    # 找到匹配的 key
    keys = manager.list_keys()
    for key_info in keys:
        if key_info["key_prefix"].startswith(key_prefix):
            # 需要找到完整的 key
            # 这里简化处理，实际需要更复杂的逻辑
            return {"status": "error", "message": "Key lookup by prefix not fully implemented"}

    return {"status": "error", "message": "Key not found"}


@router.get("/security/rate-limit/stats")
async def get_rate_limit_stats() -> Dict[str, Any]:
    """获取速率限制统计"""
    from core.security import get_rate_limiter

    limiter = get_rate_limiter()
    return limiter.get_stats()


@router.get("/security/audit/events")
async def list_security_events(
    event_type: str = None,
    ip_address: str = None,
    limit: int = 100
) -> Dict[str, Any]:
    """获取安全审计事件"""
    from core.security import get_security_auditor, SecurityEvent

    auditor = get_security_auditor()

    event_enum = None
    if event_type:
        try:
            event_enum = SecurityEvent(event_type)
        except ValueError:
            pass

    events = auditor.get_events(
        event_type=event_enum,
        ip_address=ip_address,
        limit=limit
    )

    return {"events": events, "total": len(events)}


@router.get("/security/audit/stats")
async def get_security_audit_stats() -> Dict[str, Any]:
    """获取安全审计统计"""
    from core.security import get_security_auditor

    auditor = get_security_auditor()
    return auditor.get_stats()


# ==================== P4 时序数据库 API ====================

@router.get("/timeseries/status")
async def get_timeseries_status() -> Dict[str, Any]:
    """获取时序数据库状态"""
    from core.storage_timeseries import get_influxdb_storage, get_hybrid_storage

    try:
        influxdb = get_influxdb_storage()
        health = influxdb.health_check()

        return {
            "enabled": True,
            "type": "influxdb",
            "health": health
        }
    except Exception as e:
        return {
            "enabled": False,
            "error": str(e)
        }


@router.get("/timeseries/metrics")
async def query_timeseries_metrics(
    service_name: str,
    metric_name: str = None,
    start_hours: int = 1,
    aggregation: str = None
) -> Dict[str, Any]:
    """查询时序指标数据"""
    from core.storage_timeseries import get_influxdb_storage
    from datetime import timedelta

    influxdb = get_influxdb_storage()

    start_time = datetime.utcnow() - timedelta(hours=start_hours)

    results = influxdb.query_metrics(
        service_name=service_name,
        metric_name=metric_name,
        start_time=start_time,
        aggregation=aggregation
    )

    return {
        "service_name": service_name,
        "metric_name": metric_name,
        "start_time": start_time.isoformat(),
        "end_time": datetime.utcnow().isoformat(),
        "aggregation": aggregation,
        "data": results
    }


@router.post("/timeseries/metrics", dependencies=[Depends(check_production_mode_write_access)])
async def record_timeseries_metric(
    service_name: str,
    metric_name: str,
    value: float,
    tags: Dict[str, str] = None
) -> Dict[str, Any]:
    """记录时序指标"""
    from core.storage_timeseries import get_influxdb_storage

    influxdb = get_influxdb_storage()
    success = influxdb.record_metric(
        service_name=service_name,
        metric_name=metric_name,
        value=value,
        tags=tags
    )

    return {
        "status": "recorded" if success else "failed",
        "service_name": service_name,
        "metric_name": metric_name
    }


@router.post("/timeseries/downsampling", dependencies=[Depends(check_production_mode_write_access)])
async def create_downsampling_policy(
    aggregation_window: str = "1h",
    retention_policy: str = "90d",
    policy_name: str = "hourly_downsample"
) -> Dict[str, Any]:
    """创建数据降采样策略"""
    from core.storage_timeseries import get_influxdb_storage

    influxdb = get_influxdb_storage()
    success = influxdb.create_downsampling_policy(
        aggregation_window=aggregation_window,
        retention_policy=retention_policy,
        policy_name=policy_name
    )

    return {
        "status": "created" if success else "failed",
        "policy_name": policy_name,
        "aggregation_window": aggregation_window,
        "retention_policy": retention_policy
    }
"""
新增 P2 增强功能：LLM 增强根因推理 API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

router = APIRouter(prefix="/api/runtime", tags=["runtime"])


class LLMEnhancedRootCauseRequest(BaseModel):
    """LLM 增强根因分析请求"""
    target_service: Optional[str] = Field(None, description="目标服务（可选）")
    lookback_minutes: int = Field(default=30, description="回溯时间（分钟）")
    include_llm_analysis: bool = Field(default=True, description="是否包含 LLM 分析")


@router.post("/ai/root-cause/enhanced-infer")
async def ai_root_cause_enhanced_infer(request: LLMEnhancedRootCauseRequest) -> Dict[str, Any]:
    """LLM 增强的 AI 根因推理 v2

    在基础根因分析上增加：
    1. 使用 LLM 生成自然语言的根因分析报告
    2. 将技术指标映射为业务影响说明
    3. 生成更具体的优化建议和代码修复方案
    4. 完整的可解释性追踪

    返回内容包括：
    - technical_summary: 技术指标摘要
    - business_impact: 业务影响分析
    - llm_analysis: LLM 深度分析报告（如果启用）
    - code_fix_suggestions: 代码修复建议
    - explainability: 可解释性追踪
    """
    from core.ai_root_cause import get_ai_enhanced_root_cause_inference, configure_enhanced_inference_with_llm
    from core.llm_integration import llm_integration
    from core.service_map import service_map

    # 获取增强推理引擎
    inference_engine = get_ai_enhanced_root_cause_inference()

    # 如果 LLM 可用，配置 LLM 客户端
    if request.include_llm_analysis and llm_integration.enabled and llm_integration._client:
        configure_enhanced_inference_with_llm(llm_integration._client)

    # 从服务映射构建图谱
    service_map_data = service_map.get_service_map_data()
    inference_engine.build_graph_from_service_map(service_map_data)

    # 执行增强推理
    result = inference_engine.infer_root_cause_with_explanation(
        target_service=request.target_service,
        lookback_minutes=request.lookback_minutes,
        include_llm_analysis=request.include_llm_analysis
    )

    return result


@router.get("/ai/root-cause/enhanced-history")
async def ai_root_cause_enhanced_history(
    limit: int = 10
) -> Dict[str, Any]:
    """获取 LLM 增强根因分析历史"""
    from core.ai_root_cause import get_ai_enhanced_root_cause_inference

    inference_engine = get_ai_enhanced_root_cause_inference()
    history = inference_engine.get_analysis_history(limit)

    return {"history": history, "total": len(history)}


@router.post("/ai/root-cause/configure-llm")
async def configure_root_cause_llm(
    provider: str = Body(default="mock", description="LLM 提供商：mock, openai, claude"),
    api_key: Optional[str] = Body(None, description="API Key"),
    model: Optional[str] = Body(None, description="模型名称")
) -> Dict[str, Any]:
    """配置根因分析的 LLM 客户端"""
    from core.ai_root_cause import configure_enhanced_inference_with_llm
    from core.llm_integration import llm_integration

    # 配置 LLM 集成
    if provider:
        try:
            llm_integration.configure(
                provider=provider,
                api_key=api_key,
                model=model
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"LLM 配置失败：{str(e)}")

    # 配置增强推理引擎
    if llm_integration.enabled and llm_integration._client:
        configure_enhanced_inference_with_llm(llm_integration._client)
        return {
            "status": "success",
            "message": f"LLM 根因分析已配置，提供商：{provider}",
            "model": model or "default"
        }
    else:
        return {
            "status": "partial",
            "message": f"LLM 配置完成但未启用（provider={provider}）",
            "enabled": False
        }
