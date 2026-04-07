"""
P5 阶段 API：预测性维护、知识图谱、代码优化增强
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from core.predictive_maintenance import (
    get_predictive_maintenance_engine,
    PredictiveMaintenanceEngine,
    PredictionType
)
from core.knowledge_graph import (
    get_knowledge_graph,
    KnowledgeGraph,
    NodeType,
    EdgeType,
    KnowledgeNode,
    KnowledgeEdge,
    ChangeEvent
)

router = APIRouter(prefix="/api/p5", tags=["p5-features"])


# ==================== 数据模型 ====================

class RecordMetricRequest(BaseModel):
    """记录指标请求"""
    service_name: str = Field(..., description="服务名称")
    metric_name: str = Field(..., description="指标名称")
    value: float = Field(..., description="指标值")
    timestamp: Optional[str] = Field(None, description="时间戳 (ISO 格式)")


class PredictTrendRequest(BaseModel):
    """趋势预测请求"""
    service_name: str = Field(..., description="服务名称")
    metric_name: str = Field(..., description="指标名称")
    horizon_hours: int = Field(default=24, description="预测视野 (小时)")


class PredictCapacityRequest(BaseModel):
    """容量预测请求"""
    service_name: str = Field(..., description="服务名称")
    metric_name: Optional[str] = Field(None, description="指标名称 (可选，不传则预测所有)")
    horizon_hours: int = Field(default=168, description="预测视野 (小时)，默认 7 天")


class PredictFailureRequest(BaseModel):
    """故障预测请求"""
    service_name: str = Field(..., description="服务名称")


class AddNodeRequest(BaseModel):
    """添加图谱节点请求"""
    node_id: str = Field(..., description="节点 ID")
    node_type: str = Field(..., description="节点类型")
    name: str = Field(..., description="节点名称")
    description: str = Field(default="", description="节点描述")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    tags: List[str] = Field(default_factory=list, description="标签")


class AddEdgeRequest(BaseModel):
    """添加图谱边请求"""
    edge_id: str = Field(..., description="边 ID")
    source_id: str = Field(..., description="源节点 ID")
    target_id: str = Field(..., description="目标节点 ID")
    edge_type: str = Field(..., description="边类型")
    weight: float = Field(default=1.0, description="权重")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class AddChangeEventRequest(BaseModel):
    """添加变更事件请求"""
    event_id: str = Field(..., description="事件 ID")
    event_type: str = Field(..., description="事件类型")
    service_id: str = Field(..., description="服务 ID")
    timestamp: str = Field(..., description="时间戳")
    description: str = Field(default="", description="事件描述")
    actor: str = Field(default="", description="执行者")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    related_nodes: List[str] = Field(default_factory=list, description="相关节点")
    impact_score: float = Field(default=0.0, description="影响分数")


class SetCapacityLimitRequest(BaseModel):
    """设置容量限制请求"""
    service_name: str = Field(..., description="服务名称")
    metric_name: str = Field(..., description="指标名称")
    limit: float = Field(..., description="容量限制值")


# ==================== 预测性维护 API ====================

@router.post("/predictive-maintenance/record-metric")
async def record_metric(request: RecordMetricRequest):
    """
    记录指标用于预测性维护

    该接口用于持续记录服务指标，以便进行趋势预测和故障预测。
    建议每分钟调用一次。
    """
    engine = get_predictive_maintenance_engine()

    timestamp = None
    if request.timestamp:
        try:
            timestamp = datetime.fromisoformat(request.timestamp)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid timestamp format. Use ISO format.")

    engine.record_metric(
        service_name=request.service_name,
        metric_name=request.metric_name,
        value=request.value,
        timestamp=timestamp or datetime.utcnow()
    )

    return {
        "status": "success",
        "message": f"Metric recorded for {request.service_name}/{request.metric_name}",
        "data": {
            "service_name": request.service_name,
            "metric_name": request.metric_name,
            "value": request.value,
            "timestamp": (timestamp or datetime.utcnow()).isoformat()
        }
    }


@router.post("/predictive-maintenance/predict-trend")
async def predict_trend(request: PredictTrendRequest):
    """
    趋势预测

    预测指定指标的未来趋势，包括:
    - 预测值序列
    - 置信区间
    - 趋势方向 (上升/下降/稳定)
    - 到达阈值的时间
    - 推荐操作
    """
    engine = get_predictive_maintenance_engine()

    result = engine.predict_trend(
        service_name=request.service_name,
        metric_name=request.metric_name,
        horizon_hours=request.horizon_hours
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No prediction available for {request.service_name}/{request.metric_name}. "
                   f"Insufficient historical data."
        )

    return {
        "status": "success",
        "data": result.to_dict()
    }


@router.post("/predictive-maintenance/predict-capacity")
async def predict_capacity(request: PredictCapacityRequest):
    """
    容量预测

    预测服务资源容量使用情况，包括:
    - 当前使用率
    - 预测使用率
    - 到达容量的天数
    - 预警级别
    """
    engine = get_predictive_maintenance_engine()

    forecasts = engine.predict_capacity(
        service_name=request.service_name,
        metric_name=request.metric_name,
        horizon_hours=request.horizon_hours
    )

    return {
        "status": "success",
        "data": {
            "service_name": request.service_name,
            "forecasts": [f.to_dict() for f in forecasts],
            "total_resources": len(forecasts)
        }
    }


@router.post("/predictive-maintenance/predict-failure")
async def predict_failure(request: PredictFailureRequest):
    """
    故障预测

    预测服务故障风险，包括:
    - 故障概率
    - 风险级别
    - 预计故障时间
    - 故障模式
    -  contributing factors
    - 预防建议
    """
    engine = get_predictive_maintenance_engine()

    prediction = engine.predict_failure(request.service_name)

    if not prediction:
        return {
            "status": "success",
            "data": {
                "service_name": request.service_name,
                "failure_probability": 0,
                "failure_risk_level": "low",
                "message": "No failure risk detected"
            }
        }

    return {
        "status": "success",
        "data": prediction.to_dict()
    }


@router.get("/predictive-maintenance/history")
async def get_prediction_history(
    service_name: Optional[str] = None,
    limit: int = 50
):
    """获取预测历史"""
    engine = get_predictive_maintenance_engine()
    history = engine.get_prediction_history(service_name=service_name, limit=limit)

    return {
        "status": "success",
        "data": history
    }


@router.get("/predictive-maintenance/all-forecasts")
async def get_all_capacity_forecasts():
    """获取所有容量预测"""
    engine = get_predictive_maintenance_engine()
    forecasts = engine.get_all_capacity_forecasts()

    return {
        "status": "success",
        "data": forecasts
    }


@router.get("/predictive-maintenance/all-failure-predictions")
async def get_all_failure_predictions():
    """获取所有故障预测"""
    engine = get_predictive_maintenance_engine()
    predictions = engine.get_all_failure_predictions()

    return {
        "status": "success",
        "data": predictions
    }


@router.post("/predictive-maintenance/set-capacity-limit")
async def set_capacity_limit(request: SetCapacityLimitRequest):
    """设置容量限制"""
    engine = get_predictive_maintenance_engine()
    engine.set_capacity_limit(
        service_name=request.service_name,
        metric_name=request.metric_name,
        limit=request.limit
    )

    return {
        "status": "success",
        "message": f"Capacity limit set for {request.service_name}/{request.metric_name}: {request.limit}"
    }


# ==================== 知识图谱 API ====================

@router.post("/knowledge-graph/node")
async def add_node(request: AddNodeRequest):
    """添加知识图谱节点"""
    graph = get_knowledge_graph()

    try:
        node_type = NodeType(request.node_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid node_type. Valid types: {[t.value for t in NodeType]}"
        )

    node = KnowledgeNode(
        node_id=request.node_id,
        node_type=node_type,
        name=request.name,
        description=request.description,
        metadata=request.metadata,
        tags=request.tags
    )

    node_id = graph.add_node(node)

    return {
        "status": "success",
        "message": f"Node added: {node_id}",
        "data": node.to_dict()
    }


@router.get("/knowledge-graph/node/{node_id}")
async def get_node(node_id: str):
    """获取节点详情"""
    graph = get_knowledge_graph()
    node = graph.get_node(node_id)

    if not node:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")

    return {
        "status": "success",
        "data": node.to_dict()
    }


@router.delete("/knowledge-graph/node/{node_id}")
async def remove_node(node_id: str):
    """删除节点"""
    graph = get_knowledge_graph()
    success = graph.remove_node(node_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")

    return {
        "status": "success",
        "message": f"Node removed: {node_id}"
    }


@router.post("/knowledge-graph/edge")
async def add_edge(request: AddEdgeRequest):
    """添加知识图谱边"""
    graph = get_knowledge_graph()

    try:
        edge_type = EdgeType(request.edge_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid edge_type. Valid types: {[t.value for t in EdgeType]}"
        )

    # 验证节点存在
    if not graph.get_node(request.source_id):
        raise HTTPException(status_code=404, detail=f"Source node not found: {request.source_id}")
    if not graph.get_node(request.target_id):
        raise HTTPException(status_code=404, detail=f"Target node not found: {request.target_id}")

    edge = KnowledgeEdge(
        edge_id=request.edge_id,
        source_id=request.source_id,
        target_id=request.target_id,
        edge_type=edge_type,
        weight=request.weight,
        metadata=request.metadata
    )

    edge_id = graph.add_edge(edge)

    return {
        "status": "success",
        "message": f"Edge added: {edge_id}",
        "data": edge.to_dict()
    }


@router.delete("/knowledge-graph/edge/{edge_id}")
async def remove_edge(edge_id: str):
    """删除边"""
    graph = get_knowledge_graph()
    success = graph.remove_edge(edge_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Edge not found: {edge_id}")

    return {
        "status": "success",
        "message": f"Edge removed: {edge_id}"
    }


@router.get("/knowledge-graph/node/{node_id}/upstream")
async def get_upstream_nodes(node_id: str):
    """获取上游节点"""
    graph = get_knowledge_graph()

    if not graph.get_node(node_id):
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")

    upstream = graph.get_upstream(node_id)

    return {
        "status": "success",
        "data": {
            "node_id": node_id,
            "upstream_nodes": [n.to_dict() for n in upstream]
        }
    }


@router.get("/knowledge-graph/node/{node_id}/downstream")
async def get_downstream_nodes(node_id: str):
    """获取下游节点"""
    graph = get_knowledge_graph()

    if not graph.get_node(node_id):
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")

    downstream = graph.get_downstream(node_id)

    return {
        "status": "success",
        "data": {
            "node_id": node_id,
            "downstream_nodes": [n.to_dict() for n in downstream]
        }
    }


@router.get("/knowledge-graph/node/{node_id}/paths/{target_id}")
async def find_paths(node_id: str, target_id: str, max_depth: int = 10):
    """查找节点间的路径"""
    graph = get_knowledge_graph()

    if not graph.get_node(node_id):
        raise HTTPException(status_code=404, detail=f"Source node not found: {node_id}")
    if not graph.get_node(target_id):
        raise HTTPException(status_code=404, detail=f"Target node not found: {target_id}")

    paths = graph.find_path(node_id, target_id, max_depth=max_depth)

    return {
        "status": "success",
        "data": {
            "source": node_id,
            "target": target_id,
            "paths": paths
        }
    }


@router.post("/knowledge-graph/change-event")
async def add_change_event(request: AddChangeEventRequest):
    """添加变更事件"""
    graph = get_knowledge_graph()

    try:
        timestamp = datetime.fromisoformat(request.timestamp)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid timestamp format. Use ISO format.")

    event = ChangeEvent(
        event_id=request.event_id,
        event_type=request.event_type,
        service_id=request.service_id,
        timestamp=timestamp,
        description=request.description,
        actor=request.actor,
        metadata=request.metadata,
        related_nodes=request.related_nodes,
        impact_score=request.impact_score
    )

    graph.add_change_event(event)

    return {
        "status": "success",
        "message": f"Change event added: {request.event_id}",
        "data": event.to_dict()
    }


@router.get("/knowledge-graph/change-events/recent")
async def get_recent_change_events(hours: int = 24):
    """获取最近的变更事件"""
    graph = get_knowledge_graph()
    events = graph.get_recent_changes(hours=hours)

    return {
        "status": "success",
        "data": {
            "hours": hours,
            "events": [e.to_dict() for e in events]
        }
    }


@router.get("/knowledge-graph/search")
async def search_nodes(query: str):
    """搜索节点"""
    graph = get_knowledge_graph()
    nodes = graph.search_nodes(query)

    return {
        "status": "success",
        "data": {
            "query": query,
            "results": [n.to_dict() for n in nodes]
        }
    }


@router.get("/knowledge-graph/stats")
async def get_graph_stats():
    """获取图谱统计信息"""
    graph = get_knowledge_graph()
    stats = graph.get_stats()

    return {
        "status": "success",
        "data": stats
    }


@router.get("/knowledge-graph/critical-nodes")
async def get_critical_nodes(top_k: int = 10):
    """获取最关键的节点"""
    graph = get_knowledge_graph()
    nodes = graph.get_critical_nodes(top_k=top_k)

    return {
        "status": "success",
        "data": {
            "critical_nodes": [
                {"node_id": node_id, "centrality": centrality}
                for node_id, centrality in nodes
            ]
        }
    }


@router.get("/knowledge-graph/export")
async def export_graph():
    """导出图谱数据"""
    graph = get_knowledge_graph()
    data = graph.to_dict()

    return {
        "status": "success",
        "data": data
    }


@router.post("/knowledge-graph/build-from-service-map")
async def build_graph_from_service_map(service_map_data: Dict[str, Any]):
    """从服务映射数据构建图谱"""
    graph = get_knowledge_graph()

    if "services" not in service_map_data:
        raise HTTPException(status_code=400, detail="Missing 'services' field in request")

    added_count = graph.build_from_service_map(service_map_data)

    return {
        "status": "success",
        "message": f"Graph built with {added_count} nodes",
        "data": {
            "nodes_added": added_count,
            "total_nodes": len(graph.nodes),
            "total_edges": len(graph.edges)
        }
    }


# ==================== 健康检查 API ====================

@router.get("/health")
async def health_check():
    """P5 功能健康检查"""
    engine = get_predictive_maintenance_engine()
    graph = get_knowledge_graph()

    return {
        "status": "healthy",
        "components": {
            "predictive_maintenance": "healthy",
            "knowledge_graph": "healthy"
        },
        "stats": {
            "prediction_history_size": len(engine._predictions_history),
            "graph_nodes": len(graph.nodes),
            "graph_edges": len(graph.edges)
        }
    }
