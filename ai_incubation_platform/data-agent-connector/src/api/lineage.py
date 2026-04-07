"""
血缘可视化 API

提供血缘图查询、影响分析、溯源分析等功能的 HTTP 接口
"""
from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from services.lineage_persistence_service import lineage_persistence_service
from utils.logger import logger

router = APIRouter(prefix="/api/lineage", tags=["Lineage"])


# ==================== 节点管理 ====================

@router.get("/nodes")
async def list_nodes(
    datasource: Optional[str] = Query(None, description="数据源过滤"),
    node_type: Optional[str] = Query(None, description="节点类型过滤 (table/column/view)"),
    search: Optional[str] = Query(None, description="名称搜索"),
    limit: int = Query(default=100, ge=1, le=1000, description="返回数量"),
    offset: int = Query(default=0, ge=0, description="偏移量")
):
    """查询节点列表"""
    try:
        result = await lineage_persistence_service.list_nodes(
            datasource=datasource,
            node_type=node_type,
            search=search,
            limit=limit,
            offset=offset
        )
        return result
    except Exception as e:
        logger.error(f"List nodes failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nodes/{node_id}")
async def get_node(
    node_id: str = Path(..., description="节点 ID"),
    include_history: bool = Query(False, description="是否包含历史版本")
):
    """获取节点详情"""
    try:
        result = await lineage_persistence_service.get_node(
            node_id=node_id,
            include_history=include_history
        )
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=404, detail=result.get("message", "Node not found"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get node failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 血缘图查询 ====================

@router.get("/graph/{node_id}")
async def get_lineage_graph(
    node_id: str = Path(..., description="节点 ID"),
    direction: str = Query(default="both", description="方向 (upstream/downstream/both)"),
    depth: int = Query(default=5, ge=1, le=20, description="查询深度")
):
    """获取血缘关系图"""
    try:
        # 获取节点信息
        node_result = await lineage_persistence_service.get_node(node_id)
        if not node_result.get("success"):
            raise HTTPException(status_code=404, detail="Node not found")

        # 获取相关边
        edges_result = await lineage_persistence_service.get_edges(
            node_id=node_id,
            direction=direction
        )

        # 构建图数据
        nodes = {node_id: node_result.get("node", {})}
        edges = edges_result.get("edges", [])

        # 获取关联节点
        related_node_ids = set()
        for edge in edges:
            related_node_ids.add(edge["source_id"])
            related_node_ids.add(edge["target_id"])

        for related_id in related_node_ids:
            if related_id != node_id:
                related_result = await lineage_persistence_service.get_node(related_id)
                if related_result.get("success"):
                    nodes[related_id] = related_result.get("node", {})

        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "center_node": node_id,
            "direction": direction,
            "depth": depth
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get lineage graph failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph")
async def get_full_lineage_graph(
    datasource: Optional[str] = Query(None, description="数据源过滤")
):
    """获取完整血缘图"""
    try:
        # 获取所有节点
        nodes_result = await lineage_persistence_service.list_nodes(
            datasource=datasource,
            limit=1000
        )
        nodes = nodes_result.get("nodes", [])

        # 获取所有边
        all_edges = []
        for node in nodes:
            edges_result = await lineage_persistence_service.get_edges(
                node_id=node["id"],
                direction="downstream"
            )
            all_edges.extend(edges_result.get("edges", []))

        # 去重边
        seen = set()
        unique_edges = []
        for edge in all_edges:
            edge_key = f"{edge['source_id']}:{edge['target_id']}:{edge['id']}"
            if edge_key not in seen:
                seen.add(edge_key)
                unique_edges.append(edge)

        return {
            "nodes": nodes,
            "edges": unique_edges,
            "total_nodes": len(nodes),
            "total_edges": len(unique_edges)
        }
    except Exception as e:
        logger.error(f"Get full lineage graph failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 影响分析 ====================

@router.get("/impact/{node_id}")
async def analyze_impact(
    node_id: str = Path(..., description="节点 ID"),
    include_details: bool = Query(False, description="是否包含详细信息")
):
    """分析影响范围（下游血缘）"""
    try:
        # 获取节点信息
        node_result = await lineage_persistence_service.get_node(node_id)
        if not node_result.get("success"):
            raise HTTPException(status_code=404, detail="Node not found")

        # 获取下游边（递归）
        impacted_nodes = []
        visited = set()
        await _collect_downstream(node_id, visited, impacted_nodes)

        return {
            "source_node": node_result.get("node"),
            "impacted_nodes": impacted_nodes,
            "impact_count": len(impacted_nodes),
            "impact_level": _calculate_impact_level(len(impacted_nodes))
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analyze impact failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _collect_downstream(
    node_id: str,
    visited: set,
    result: list,
    depth: int = 0
):
    """递归收集下游节点"""
    if node_id in visited or depth > 10:
        return
    visited.add(node_id)

    edges_result = await lineage_persistence_service.get_edges(
        node_id=node_id,
        direction="downstream"
    )

    for edge in edges_result.get("edges", []):
        target_id = edge["target_id"]
        if target_id not in visited:
            node_result = await lineage_persistence_service.get_node(target_id)
            if node_result.get("success"):
                node_info = node_result.get("node", {})
                node_info["depth"] = depth + 1
                node_info["path"] = edge.get("operation", "unknown")
                result.append(node_info)
                await _collect_downstream(target_id, visited, result, depth + 1)


def _calculate_impact_level(count: int) -> str:
    """计算影响级别"""
    if count == 0:
        return "none"
    elif count <= 3:
        return "low"
    elif count <= 10:
        return "medium"
    else:
        return "high"


# ==================== 溯源分析 ====================

@router.get("/lineage/{node_id}")
async def analyze_lineage(
    node_id: str = Path(..., description="节点 ID"),
    include_details: bool = Query(False, description="是否包含详细信息")
):
    """分析数据来源（上游血缘）"""
    try:
        # 获取节点信息
        node_result = await lineage_persistence_service.get_node(node_id)
        if not node_result.get("success"):
            raise HTTPException(status_code=404, detail="Node not found")

        # 获取上游边（递归）
        source_nodes = []
        visited = set()
        await _collect_upstream(node_id, visited, source_nodes)

        return {
            "target_node": node_result.get("node"),
            "source_nodes": source_nodes,
            "source_count": len(source_nodes),
            "has_multiple_sources": len(source_nodes) > 1
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analyze lineage failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _collect_upstream(
    node_id: str,
    visited: set,
    result: list,
    depth: int = 0
):
    """递归收集上游节点"""
    if node_id in visited or depth > 10:
        return
    visited.add(node_id)

    edges_result = await lineage_persistence_service.get_edges(
        node_id=node_id,
        direction="upstream"
    )

    for edge in edges_result.get("edges", []):
        source_id = edge["source_id"]
        if source_id not in visited:
            node_result = await lineage_persistence_service.get_node(source_id)
            if node_result.get("success"):
                node_info = node_result.get("node", {})
                node_info["depth"] = depth + 1
                node_info["operation"] = edge.get("operation", "unknown")
                result.append(node_info)
                await _collect_upstream(source_id, visited, result, depth + 1)


# ==================== 查询历史 ====================

@router.get("/history")
async def get_query_history(
    datasource: Optional[str] = Query(None, description="数据源过滤"),
    user_id: Optional[str] = Query(None, description="用户 ID 过滤"),
    start_time: Optional[str] = Query(None, description="开始时间 (ISO 格式)"),
    end_time: Optional[str] = Query(None, description="结束时间 (ISO 格式)"),
    limit: int = Query(default=100, ge=1, le=500, description="返回数量")
):
    """获取查询历史"""
    try:
        start_dt = datetime.fromisoformat(start_time) if start_time else None
        end_dt = datetime.fromisoformat(end_time) if end_time else None

        result = await lineage_persistence_service.get_query_history(
            datasource=datasource,
            user_id=user_id,
            start_time=start_dt,
            end_time=end_dt,
            limit=limit
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid time format: {e}")
    except Exception as e:
        logger.error(f"Get query history failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 快照管理 ====================

@router.post("/snapshots")
async def create_snapshot(
    snapshot_name: str = Query(..., description="快照名称"),
    description: Optional[str] = Query(None, description="快照描述"),
    user_id: Optional[str] = Query(None, description="创建者 ID")
):
    """创建血缘快照"""
    try:
        result = await lineage_persistence_service.create_snapshot(
            snapshot_name=snapshot_name,
            description=description,
            created_by=user_id
        )
        return result
    except Exception as e:
        logger.error(f"Create snapshot failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshots")
async def list_snapshots(limit: int = Query(default=50, ge=1, le=200)):
    """获取快照列表"""
    try:
        result = await lineage_persistence_service.list_snapshots(limit=limit)
        return result
    except Exception as e:
        logger.error(f"List snapshots failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshots/{snapshot_id}")
async def get_snapshot(snapshot_id: str = Path(..., description="快照 ID")):
    """获取快照详情"""
    try:
        result = await lineage_persistence_service.get_snapshot(snapshot_id)
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=404, detail=result.get("message", "Snapshot not found"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get snapshot failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 统计信息 ====================

@router.get("/statistics")
async def get_statistics(datasource: Optional[str] = Query(None, description="数据源过滤")):
    """获取血缘统计信息"""
    try:
        result = await lineage_persistence_service.get_statistics()
        stats = result.get("statistics", {})

        # 如果有数据源过滤，重新计算
        if datasource:
            nodes_result = await lineage_persistence_service.list_nodes(
                datasource=datasource,
                limit=1000
            )
            stats["filtered_nodes"] = len(nodes_result.get("nodes", []))
            stats["filter_datasource"] = datasource

        return stats
    except Exception as e:
        logger.error(f"Get statistics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info")
async def lineage_info():
    """获取血缘服务信息"""
    return {
        "service": "Lineage Service",
        "endpoints": {
            "nodes": "/api/lineage/nodes",
            "graph": "/api/lineage/graph/{node_id}",
            "impact": "/api/lineage/impact/{node_id}",
            "lineage": "/api/lineage/lineage/{node_id}",
            "history": "/api/lineage/history",
            "snapshots": "/api/lineage/snapshots",
            "statistics": "/api/lineage/statistics"
        }
    }
