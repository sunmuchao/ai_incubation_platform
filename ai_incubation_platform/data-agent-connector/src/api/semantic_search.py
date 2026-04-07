"""
语义搜索 API

提供语义搜索功能的 HTTP 接口
"""
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from services.semantic_search_service import semantic_search_service
from utils.logger import logger

router = APIRouter(prefix="/api/search", tags=["Semantic Search"])


# ==================== 请求/响应模型 ====================

class TableSearchRequest(BaseModel):
    """表搜索请求"""
    query: str = Field(..., description="查询文本")
    datasource: Optional[str] = Field(None, description="数据源过滤")
    limit: int = Field(default=10, ge=1, le=50, description="返回数量")


class ColumnSearchRequest(BaseModel):
    """列搜索请求"""
    query: str = Field(..., description="查询文本")
    table_name: Optional[str] = Field(None, description="表名过滤")
    datasource: Optional[str] = Field(None, description="数据源过滤")
    limit: int = Field(default=20, ge=1, le=100, description="返回数量")


class HistorySearchRequest(BaseModel):
    """历史查询搜索请求"""
    query: str = Field(..., description="查询文本")
    limit: int = Field(default=10, ge=1, le=50, description="返回数量")
    user_id: Optional[str] = Field(None, description="用户 ID 过滤")


class HybridSearchRequest(BaseModel):
    """混合搜索请求"""
    query: str = Field(..., description="查询文本")
    collections: Optional[List[str]] = Field(
        default=["schema_tables", "schema_columns", "query_history"],
        description="集合列表"
    )
    filters: Dict[str, Any] = Field(default_factory=dict, description="过滤条件")
    limit: int = Field(default=10, ge=1, le=50, description="返回数量")
    use_ai_rerank: bool = Field(default=True, description="是否使用 AI 重排序")


class SearchSuggestionRequest(BaseModel):
    """搜索建议请求"""
    partial_query: str = Field(..., description="部分查询文本")
    limit: int = Field(default=5, ge=1, le=20, description="返回数量")


class SearchItem(BaseModel):
    """搜索结果项"""
    id: str
    datasource: Optional[str]
    table_name: Optional[str]
    column_name: Optional[str]
    description: str
    similarity: float
    content: str


class SearchResponse(BaseModel):
    """搜索响应"""
    results: List[SearchItem]
    total: int
    query: str


class TableSearchResponse(BaseModel):
    """表搜索响应"""
    tables: List[Dict[str, Any]]
    total: int
    query: str


class ColumnSearchResponse(BaseModel):
    """列搜索响应"""
    columns: List[Dict[str, Any]]
    total: int
    query: str


class HistorySearchResponse(BaseModel):
    """历史查询搜索响应"""
    queries: List[Dict[str, Any]]
    total: int
    query: str


class SuggestionResponse(BaseModel):
    """建议响应"""
    suggestions: List[str]
    partial_query: str


# ==================== 端点 ====================

@router.post("/tables", response_model=TableSearchResponse)
async def search_tables(request: TableSearchRequest):
    """搜索相关表"""
    try:
        results = await semantic_search_service.search_tables(
            query=request.query,
            datasource=request.datasource,
            limit=request.limit
        )
        return TableSearchResponse(
            tables=results,
            total=len(results),
            query=request.query
        )
    except Exception as e:
        logger.error(f"Table search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/columns", response_model=ColumnSearchResponse)
async def search_columns(request: ColumnSearchRequest):
    """搜索相关列"""
    try:
        results = await semantic_search_service.search_columns(
            query=request.query,
            table_name=request.table_name,
            datasource=request.datasource,
            limit=request.limit
        )
        return ColumnSearchResponse(
            columns=results,
            total=len(results),
            query=request.query
        )
    except Exception as e:
        logger.error(f"Column search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/history", response_model=HistorySearchResponse)
async def search_history(request: HistorySearchRequest):
    """搜索历史查询"""
    try:
        results = await semantic_search_service.search_query_history(
            query=request.query,
            limit=request.limit,
            user_id=request.user_id
        )
        return HistorySearchResponse(
            queries=results,
            total=len(results),
            query=request.query
        )
    except Exception as e:
        logger.error(f"History search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hybrid", response_model=SearchResponse)
async def hybrid_search(request: HybridSearchRequest):
    """混合搜索（跨多个集合）"""
    try:
        results = await semantic_search_service.hybrid_search(
            query=request.query,
            collections=request.collections,
            filters=request.filters,
            limit=request.limit,
            use_ai_rerank=request.use_ai_rerank
        )

        formatted_results = [
            SearchItem(
                id=r["id"],
                datasource=r.get("metadata", {}).get("datasource"),
                table_name=r.get("metadata", {}).get("table_name"),
                column_name=r.get("metadata", {}).get("column_name"),
                description=r.get("content", "")[:500],
                similarity=r.get("similarity", 0),
                content=r.get("content", "")
            )
            for r in results
        ]

        return SearchResponse(
            results=formatted_results,
            total=len(formatted_results),
            query=request.query
        )
    except Exception as e:
        logger.error(f"Hybrid search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suggestions", response_model=SuggestionResponse)
async def get_suggestions(request: SearchSuggestionRequest):
    """获取搜索建议"""
    try:
        suggestions = await semantic_search_service.get_search_suggestions(
            partial_query=request.partial_query,
            limit=request.limit
        )
        return SuggestionResponse(
            suggestions=suggestions,
            partial_query=request.partial_query
        )
    except Exception as e:
        logger.error(f"Get suggestions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def semantic_search_info():
    """获取语义搜索服务信息"""
    return {
        "service": "Semantic Search Service",
        "status": "running" if semantic_search_service._initialized else "not initialized",
        "endpoints": {
            "tables": "/api/search/tables",
            "columns": "/api/search/columns",
            "history": "/api/search/history",
            "hybrid": "/api/search/hybrid",
            "suggestions": "/api/search/suggestions"
        }
    }
