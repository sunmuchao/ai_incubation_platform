"""
智能文档问答 API
提供文档语义搜索、QA 问答、代码导航等功能
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from services.doc_qa_service import (
    create_doc_qa_service,
    search_documents,
    ask_codebase_question,
    DocQAService
)

router = APIRouter(prefix="/api/doc-qa", tags=["document-qa"])


# ==================== 请求模型 ====================

class SearchDocumentsRequest(BaseModel):
    """搜索文档请求"""
    query: str = Field(..., description="搜索查询")
    project_name: str = Field(..., description="项目名称")
    top_k: int = Field(10, description="返回结果数量")
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件")


class AskQuestionRequest(BaseModel):
    """问答请求"""
    question: str = Field(..., description="问题")
    project_name: str = Field(..., description="项目名称")
    scope_paths: Optional[List[str]] = Field(None, description="限定搜索范围的路径")
    max_context_chunks: int = Field(5, description="最大上下文块数量")


class ExplainCodeRequest(BaseModel):
    """代码解释请求"""
    code: str = Field(..., description="代码片段")
    language: str = Field("python", description="语言标识")
    context: Optional[str] = Field(None, description="额外上下文")


class CodeNavigationRequest(BaseModel):
    """代码导航请求"""
    file_path: str = Field(..., description="文件路径")
    symbol_name: Optional[str] = Field(None, description="符号名称")
    project_name: Optional[str] = Field(None, description="项目名称")


# ==================== API 端点 ====================

@router.post("/search")
async def search_documents_endpoint(request: SearchDocumentsRequest):
    """
    语义搜索文档

    基于向量检索搜索相关文档，支持过滤条件。
    """
    try:
        service = create_doc_qa_service(request.project_name)
        result = service.search_documents(
            query=request.query,
            project_name=request.project_name,
            top_k=request.top_k,
            filters=request.filters
        )

        return {
            "success": True,
            "data": {
                "query": result.query,
                "results": [
                    {
                        "content": r.content,
                        "file_path": r.file_path,
                        "start_line": r.start_line,
                        "end_line": r.end_line,
                        "similarity": r.similarity,
                        "chunk_type": r.chunk_type,
                        "symbols": r.symbols,
                        "metadata": r.metadata
                    }
                    for r in result.results
                ],
                "total_found": result.total_found,
                "search_time_ms": result.search_time_ms,
                "suggestions": result.suggestions
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {
                "query": request.query,
                "results": [],
                "total_found": 0,
                "search_time_ms": 0,
                "suggestions": []
            }
        }


@router.post("/ask")
async def ask_question_endpoint(request: AskQuestionRequest):
    """
    回答关于代码库的问题

    基于文档检索和 LLM 生成答案，提供答案溯源引用。
    """
    try:
        service = create_doc_qa_service(request.project_name)
        answer = service.ask_question(
            question=request.question,
            project_name=request.project_name,
            scope_paths=request.scope_paths,
            max_context_chunks=request.max_context_chunks
        )

        return {
            "success": True,
            "data": {
                "answer": answer.answer,
                "confidence": answer.confidence,
                "sources": [
                    {
                        "content": s.content[:500],  # 限制长度
                        "file_path": s.file_path,
                        "start_line": s.start_line,
                        "end_line": s.end_line,
                        "similarity": s.similarity,
                        "chunk_type": s.chunk_type
                    }
                    for s in answer.sources
                ],
                "code_references": answer.code_references,
                "follow_up_questions": answer.follow_up_questions
            }
        }
    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.exception("Failed to answer question")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/explain")
async def explain_code_endpoint(request: ExplainCodeRequest):
    """
    智能解释代码

    分析代码结构、功能和关键概念。
    """
    try:
        service = create_doc_qa_service()
        result = service.explain_code(
            code=request.code,
            language=request.language,
            context=request.context
        )

        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.exception("Failed to explain code")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/navigate")
async def code_navigation_endpoint(request: CodeNavigationRequest):
    """
    代码导航辅助

    获取文件中的符号定义、跳转信息。
    """
    try:
        service = create_doc_qa_service(request.project_name or "default")
        result = service.get_code_navigation(
            file_path=request.file_path,
            symbol_name=request.symbol_name,
            project_name=request.project_name
        )

        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.exception("Failed to get code navigation")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_collection_stats(
    project_name: str = Query(..., description="项目名称")
):
    """
    获取文档集合统计信息
    """
    try:
        service = create_doc_qa_service(project_name)
        stats = service.get_collection_stats()

        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.exception("Failed to get stats")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "doc-qa",
        "version": "1.7.0"
    }
