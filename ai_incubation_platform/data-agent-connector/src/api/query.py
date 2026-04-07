"""
查询 API 路由
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nl2sql.converter import nl2sql_converter
from connectors.base import ConnectorConfig
from core.connection_manager import connection_manager
from core.query_engine import query_engine
from core.lineage import lineage_manager
from .deps import verify_api_key, get_user_role
from utils.logger import logger

router = APIRouter(prefix="/api/query", tags=["query"], dependencies=[Depends(verify_api_key)])

def _http_status_for_error_code(error_code: str) -> int:
    """将内部 error_code 映射为 HTTP 状态码（用于文档一致性）。"""
    if error_code == "rate_limited":
        return 429
    if error_code == "connector_not_found":
        return 404
    if error_code == "permission_denied":
        return 403
    if error_code == "sql_unsafe":
        return 400
    if error_code == "query_timeout":
        return 504
    # execution_error 既可能是数据源错误也可能是连接问题，按 400 更友好给调用方处理
    if error_code == "execution_error":
        return 400
    return 400


class QueryRequest(BaseModel):
    """查询请求"""
    connector_name: str
    query: str
    params: Optional[Dict[str, Any]] = None


class NLQueryRequest(BaseModel):
    """自然语言查询请求"""
    connector_name: str
    natural_language: str


@router.post("/execute")
async def execute_query(
    request: QueryRequest,
    role: str = Depends(get_user_role)
):
    """执行 SQL/API 查询"""
    try:
        result = await query_engine.execute_query(
            connector_name=request.connector_name,
            query=request.query,
            params=request.params,
            role=role
        )

        if not result.success:
            raise HTTPException(
                status_code=_http_status_for_error_code(getattr(result, "error_code", "")),
                detail=result.error
            )

        return {
            "success": True,
            "data": result.data,
            "execution_time_ms": result.execution_time_ms,
            "operation_type": result.operation_type,
            "rows_returned": result.rows_returned
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Query execution error", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/nl-query")
async def nl_query(
    request: NLQueryRequest,
    role: str = Depends(get_user_role)
):
    """自然语言查询"""
    try:
        # 使用查询引擎的自然语言查询方法，包含Schema缓存
        result = await query_engine.execute_natural_language_query(
            connector_name=request.connector_name,
            natural_language=request.natural_language,
            role=role
        )

        if not result.success:
            raise HTTPException(
                status_code=_http_status_for_error_code(getattr(result, "error_code", "")),
                detail=result.error
            )

        return {
            "success": True,
            "natural_language": request.natural_language,
            "data": result.data,
            "execution_time_ms": result.execution_time_ms,
            "operation_type": result.operation_type,
            "rows_returned": result.rows_returned
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("NL query error", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/connect")
async def connect_data_source(
    name: str,
    connector_type: str,
    datasource_name: str,
    role: str = Depends(get_user_role)
):
    """连接数据源"""
    try:
        config = ConnectorConfig(
            name=name,
            datasource_name=datasource_name
        )
        await connection_manager.create_connector(
            connector_type=connector_type,
            config=config,
            role=role
        )
        return {"message": f"Connected to {name}", "status": "connected"}
    except Exception as e:
        logger.error(
            "Failed to connect datasource",
            extra={
                "connector_name": name,
                "connector_type": connector_type,
                "error": str(e)
            }
        )
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/disconnect")
async def disconnect_data_source(name: str):
    """断开数据源"""
    try:
        success = await connection_manager.remove_connector(name)
        if not success:
            raise HTTPException(status_code=404, detail="Connector not found")
        return {"message": f"Disconnected from {name}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to disconnect datasource", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/sources")
async def list_data_sources():
    """获取数据源列表"""
    try:
        sources = await connection_manager.list_connectors()
        return {"sources": sources}
    except Exception as e:
        logger.error("Failed to list datasources", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/refresh-schema/{connector_name}")
async def refresh_schema(
    connector_name: str,
    role: str = Depends(get_user_role)
):
    """刷新数据源Schema缓存"""
    try:
        connector = await connection_manager.get_connector(connector_name)
        if not connector:
            raise HTTPException(status_code=404, detail=f"数据源 {connector_name} 不存在")

        # 获取最新Schema并更新缓存
        schema = await connector.get_schema()
        nl2sql_converter.register_schema(connector_name, schema)

        # 失效旧缓存
        nl2sql_converter.schema_cache.invalidate(connector_name)
        # 设置新缓存
        nl2sql_converter.register_schema(connector_name, schema)

        # 注册到数据字典（占位实现）
        lineage_manager.register_data_dictionary(connector_name, schema)

        return {
            "success": True,
            "message": f"数据源 {connector_name} 的Schema已刷新",
            "schema": schema
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to refresh schema", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/lineage/{connector_name}/{table_name}")
async def get_table_lineage(
    connector_name: str,
    table_name: str,
    role: str = Depends(get_user_role)
):
    """获取表的数据血缘关系（占位实现）"""
    try:
        lineage = lineage_manager.get_table_lineage(connector_name, table_name)
        return {
            "success": True,
            "data": lineage,
            "note": "This is a placeholder implementation. Full lineage tracking coming soon."
        }
    except Exception as e:
        logger.error("Failed to get table lineage", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/impact-analysis/{connector_name}/{table_name}")
async def analyze_impact(
    connector_name: str,
    table_name: str,
    proposed_changes: Optional[Dict[str, Any]] = None,
    role: str = Depends(get_user_role)
):
    """分析表变更的影响范围（占位实现）"""
    try:
        result = lineage_manager.analyze_impact(connector_name, table_name, proposed_changes)
        return {
            "success": True,
            "data": {
                "target_node": {
                    "id": result.target_node.id,
                    "name": result.target_node.name,
                    "type": result.target_node.type,
                    "datasource": result.target_node.datasource
                },
                "affected_nodes_count": len(result.affected_nodes),
                "affected_edges_count": len(result.affected_edges),
                "risk_level": result.risk_level,
                "summary": result.summary
            },
            "note": "This is a placeholder implementation. Full impact analysis coming soon."
        }
    except Exception as e:
        logger.error("Failed to perform impact analysis", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/data-dictionary/{connector_name}")
async def get_data_dictionary(
    connector_name: str,
    table_name: Optional[str] = None,
    role: str = Depends(get_user_role)
):
    """获取数据源的数据字典（占位实现）"""
    try:
        dictionary = lineage_manager.get_data_dictionary(connector_name, table_name)
        return {
            "success": True,
            "data": dictionary,
            "note": "This is a placeholder implementation. Data dictionary integration coming soon."
        }
    except Exception as e:
        logger.error("Failed to get data dictionary", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/data-dictionary/search")
async def search_data_dictionary(
    keyword: str,
    datasource: Optional[str] = None,
    role: str = Depends(get_user_role)
):
    """搜索数据字典（占位实现）"""
    try:
        results = lineage_manager.search_data_dictionary(keyword, datasource)
        return {
            "success": True,
            "data": results,
            "note": "This is a placeholder implementation. Data dictionary search coming soon."
        }
    except Exception as e:
        logger.error("Failed to search data dictionary", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="内部服务器错误")
