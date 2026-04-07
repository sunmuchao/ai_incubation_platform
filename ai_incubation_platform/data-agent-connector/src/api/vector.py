"""
向量索引 API

提供向量嵌入和索引管理的 HTTP 接口
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from services.vector_index_service import vector_index_service
from utils.logger import logger

router = APIRouter(prefix="/api/vector", tags=["Vector Index"])


# ==================== 请求/响应模型 ====================

class EmbedRequest(BaseModel):
    """嵌入生成请求"""
    text: str = Field(..., description="输入文本")


class EmbedResponse(BaseModel):
    """嵌入生成响应"""
    embedding: List[float] = Field(..., description="向量嵌入")
    dimension: int = Field(..., description="向量维度")


class IndexDocumentRequest(BaseModel):
    """索引文档请求"""
    collection: str = Field(..., description="集合名称")
    content: str = Field(..., description="文档内容")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    datasource: Optional[str] = Field(None, description="数据源名称")
    table_name: Optional[str] = Field(None, description="表名")


class IndexDocumentResponse(BaseModel):
    """索引文档响应"""
    id: str = Field(..., description="索引 ID")
    collection: str = Field(..., description="集合名称")
    success: bool = Field(..., description="是否成功")


class IndexSchemaRequest(BaseModel):
    """索引 Schema 请求"""
    datasource: str = Field(..., description="数据源名称")
    table_name: str = Field(..., description="表名")
    schema_info: Dict[str, Any] = Field(..., description="Schema 信息")


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., description="查询文本")
    collection: str = Field(..., description="集合名称")
    limit: int = Field(default=10, ge=1, le=100, description="返回数量")
    filters: Dict[str, Any] = Field(default_factory=dict, description="过滤条件")


class SearchResult(BaseModel):
    """搜索结果项"""
    id: str
    content: str
    metadata: Dict[str, Any]
    similarity: float
    datasource: Optional[str]
    table_name: Optional[str]


class SearchResponse(BaseModel):
    """搜索响应"""
    results: List[SearchResult]
    total: int
    query: str


class CollectionInfo(BaseModel):
    """集合信息"""
    name: str
    count: int
    metadata: Dict[str, Any]


class CollectionListResponse(BaseModel):
    """集合列表响应"""
    collections: List[CollectionInfo]


# ==================== 端点 ====================

@router.post("/embed", response_model=EmbedResponse)
async def create_embed(request: EmbedRequest):
    """生成文本向量嵌入"""
    try:
        embedding = await vector_index_service.embed_text(request.text)
        return EmbedResponse(
            embedding=embedding,
            dimension=len(embedding)
        )
    except Exception as e:
        logger.error(f"Embed failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index", response_model=IndexDocumentResponse)
async def create_index(request: IndexDocumentRequest):
    """创建文档索引"""
    try:
        doc_id = await vector_index_service.index_document(
            collection=request.collection,
            content=request.content,
            metadata=request.metadata,
            datasource=request.datasource,
            table_name=request.table_name
        )
        return IndexDocumentResponse(
            id=doc_id,
            collection=request.collection,
            success=True
        )
    except Exception as e:
        logger.error(f"Index creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index/schema", response_model=IndexDocumentResponse)
async def index_schema(request: IndexSchemaRequest):
    """索引表 Schema 信息"""
    try:
        doc_id = await vector_index_service.index_table_schema(
            datasource=request.datasource,
            table_name=request.table_name,
            schema_info=request.schema_info
        )
        return IndexDocumentResponse(
            id=doc_id,
            collection="schema_tables",
            success=True
        )
    except Exception as e:
        logger.error(f"Schema indexing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index/query-history", response_model=IndexDocumentResponse)
async def index_query_history(
    request: IndexDocumentRequest,
    user_id: Optional[str] = None
):
    """索引查询历史"""
    try:
        doc_id = await vector_index_service.index_query_history(
            query=request.content,
            result_summary=request.metadata.get("result_summary", ""),
            metadata=request.metadata,
            user_id=user_id
        )
        return IndexDocumentResponse(
            id=doc_id,
            collection="query_history",
            success=True
        )
    except Exception as e:
        logger.error(f"Query history indexing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/index/{collection}/{id}")
async def delete_index(collection: str, id: str):
    """删除索引"""
    try:
        success = await vector_index_service.delete_index(collection, id)
        return {"success": success, "collection": collection, "id": id}
    except Exception as e:
        logger.error(f"Index deletion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SearchResponse)
async def search_similar(request: SearchRequest):
    """搜索相似文档"""
    try:
        results = await vector_index_service.search_similar(
            collection=request.collection,
            query=request.query,
            limit=request.limit,
            filters=request.filters
        )

        formatted_results = [
            SearchResult(
                id=r["id"],
                content=r.get("content", ""),
                metadata=r.get("metadata", {}),
                similarity=r.get("similarity", 0),
                datasource=r.get("metadata", {}).get("datasource"),
                table_name=r.get("metadata", {}).get("table_name")
            )
            for r in results
        ]

        return SearchResponse(
            results=formatted_results,
            total=len(formatted_results),
            query=request.query
        )
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections", response_model=CollectionListResponse)
async def list_collections():
    """列出所有集合"""
    try:
        collections = await vector_index_service.list_collections()
        formatted = [
            CollectionInfo(
                name=c.get("name", ""),
                count=c.get("count", 0),
                metadata=c.get("metadata", {})
            )
            for c in collections
        ]
        return CollectionListResponse(collections=formatted)
    except Exception as e:
        logger.error(f"List collections failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/stats")
async def get_cache_stats():
    """获取嵌入缓存统计"""
    try:
        stats = await vector_index_service.get_embedding_cache_stats()
        return stats
    except Exception as e:
        logger.error(f"Get cache stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/clear")
async def clear_cache():
    """清除嵌入缓存"""
    try:
        await vector_index_service.clear_embedding_cache()
        return {"success": True, "message": "Cache cleared"}
    except Exception as e:
        logger.error(f"Clear cache failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def vector_index_info():
    """获取向量索引服务信息"""
    return {
        "service": "Vector Index Service",
        "status": "running" if vector_index_service._initialized else "not initialized",
        "endpoints": {
            "embed": "/api/vector/embed",
            "index": "/api/vector/index",
            "search": "/api/vector/search",
            "collections": "/api/vector/collections"
        }
    }
