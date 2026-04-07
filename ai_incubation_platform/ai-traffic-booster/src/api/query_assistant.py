"""
AI 查询助手 API 路由 - v1.8

提供自然语言查询、查询历史、收藏管理、智能报告生成等 API 端点
"""
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from schemas.common import Response, ErrorCode
from services.query_assistant_service import (
    query_assistant_service,
    QueryResult,
    QueryHistory,
    QueryFavorite,
    SavedReport,
    QueryTemplate
)
from models.query_assistant import QueryIntent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/query", tags=["AI 查询助手"])


# ========== 自然语言查询 API ==========

@router.post("/ask", response_model=Response)
async def ask_ai(
    query_text: str = Body(..., embed=True, description="自然语言查询文本"),
    user_id: Optional[str] = Body(None, embed=True, description="用户 ID（可选）"),
    session_id: Optional[str] = Body(None, embed=True, description="会话 ID（用于多轮对话）")
):
    """
    AI 查询助手 - 自然语言查询

    使用自然语言向 AI 助手提问，例如：
    - "上周哪个页面流量最高？"
    - "最近 30 天的流量趋势如何？"
    - "为什么流量下跌了？"
    - "我该如何提升流量？"

    Args:
        query_text: 自然语言查询文本
        user_id: 用户 ID（可选）
        session_id: 会话 ID（可选，用于保持对话上下文）

    Returns:
        查询结果，包括数据、AI 解读和建议
    """
    try:
        result = query_assistant_service.ask(
            query_text=query_text,
            user_id=user_id,
            session_id=session_id
        )

        return Response(
            code=ErrorCode.SUCCESS,
            message="查询成功",
            data={
                "query_id": result.query.query_id,
                "session_id": result.query.session_id,
                "query_text": result.query.query_text,
                "intent": result.query.query_intent.value,
                "confidence": result.query.query_entities,
                "data": result.data,
                "interpretation": result.interpretation,
                "suggestions": result.suggestions,
                "execution_time_ms": result.query.execution_time_ms
            }
        )

    except Exception as e:
        logger.error(f"Error in ask_ai: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"查询失败：{str(e)}"
        )


# ========== 查询历史 API ==========

@router.get("/history/session/{session_id}", response_model=Response)
async def get_session_history(
    session_id: str,
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制")
):
    """
    获取会话查询历史

    Args:
        session_id: 会话 ID
        limit: 返回数量限制

    Returns:
        查询历史列表
    """
    try:
        history = query_assistant_service.get_history(session_id, limit)

        return Response(
            code=ErrorCode.SUCCESS,
            message="Success",
            data={
                "session_id": session_id,
                "queries": [q.to_dict() for q in history],
                "count": len(history)
            }
        )

    except Exception as e:
        logger.error(f"Error getting session history: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"获取历史失败：{str(e)}"
        )


@router.get("/history/user/{user_id}", response_model=Response)
async def get_user_history(
    user_id: str,
    limit: int = Query(default=100, ge=1, le=500, description="返回数量限制")
):
    """
    获取用户查询历史

    Args:
        user_id: 用户 ID
        limit: 返回数量限制

    Returns:
        查询历史列表
    """
    try:
        history = query_assistant_service.get_user_history(user_id, limit)

        return Response(
            code=ErrorCode.SUCCESS,
            message="Success",
            data={
                "user_id": user_id,
                "queries": [q.to_dict() for q in history],
                "count": len(history)
            }
        )

    except Exception as e:
        logger.error(f"Error getting user history: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"获取历史失败：{str(e)}"
        )


@router.get("/history/{query_id}", response_model=Response)
async def get_query_detail(query_id: str):
    """
    获取单个查询详情

    Args:
        query_id: 查询 ID

    Returns:
        查询详情
    """
    try:
        from repositories.query_repository import QueryAssistantRepository
        repo = QueryAssistantRepository()
        query = repo.get_query(query_id)

        if not query:
            return Response(
                code=ErrorCode.NOT_FOUND,
                message="查询不存在"
            )

        return Response(
            code=ErrorCode.SUCCESS,
            message="Success",
            data=query.to_dict()
        )

    except Exception as e:
        logger.error(f"Error getting query detail: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"获取查询详情失败：{str(e)}"
        )


# ========== 收藏管理 API ==========

@router.post("/favorites", response_model=Response)
async def add_favorite(
    query_id: str = Body(..., embed=True, description="查询 ID"),
    query_text: str = Body(..., embed=True, description="查询文本"),
    user_id: str = Body(..., embed=True, description="用户 ID"),
    custom_name: Optional[str] = Body(None, embed=True, description="自定义名称")
):
    """
    添加查询收藏

    Args:
        query_id: 查询 ID
        query_text: 查询文本
        user_id: 用户 ID
        custom_name: 自定义名称（可选）

    Returns:
        收藏结果
    """
    try:
        favorite = query_assistant_service.add_favorite(
            query_id=query_id,
            query_text=query_text,
            user_id=user_id,
            custom_name=custom_name
        )

        return Response(
            code=ErrorCode.SUCCESS,
            message="收藏成功",
            data=favorite.to_dict()
        )

    except Exception as e:
        logger.error(f"Error adding favorite: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"添加收藏失败：{str(e)}"
        )


@router.get("/favorites/{user_id}", response_model=Response)
async def get_favorites(user_id: str):
    """
    获取用户收藏列表

    Args:
        user_id: 用户 ID

    Returns:
        收藏列表
    """
    try:
        favorites = query_assistant_service.get_favorites(user_id)

        return Response(
            code=ErrorCode.SUCCESS,
            message="Success",
            data={
                "user_id": user_id,
                "favorites": [f.to_dict() for f in favorites],
                "count": len(favorites)
            }
        )

    except Exception as e:
        logger.error(f"Error getting favorites: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"获取收藏失败：{str(e)}"
        )


@router.delete("/favorites/{favorite_id}", response_model=Response)
async def remove_favorite(
    favorite_id: str,
    user_id: str = Query(..., description="用户 ID")
):
    """
    删除收藏

    Args:
        favorite_id: 收藏 ID
        user_id: 用户 ID

    Returns:
        删除结果
    """
    try:
        success = query_assistant_service.remove_favorite(favorite_id, user_id)

        if success:
            return Response(
                code=ErrorCode.SUCCESS,
                message="删除成功"
            )
        else:
            return Response(
                code=ErrorCode.NOT_FOUND,
                message="收藏不存在"
            )

    except Exception as e:
        logger.error(f"Error removing favorite: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"删除收藏失败：{str(e)}"
        )


# ========== 查询模板 API ==========

@router.get("/templates", response_model=Response)
async def get_templates(
    category: Optional[str] = Query(default=None, description="分类：traffic/page/conversion/anomaly/recommendation")
):
    """
    获取查询模板

    Args:
        category: 分类（可选）

    Returns:
        模板列表
    """
    try:
        templates = query_assistant_service.get_templates(category)

        return Response(
            code=ErrorCode.SUCCESS,
            message="Success",
            data={
                "templates": [t.to_dict() for t in templates],
                "count": len(templates)
            }
        )

    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"获取模板失败：{str(e)}"
        )


@router.get("/suggestions", response_model=Response)
async def get_suggested_queries(
    context: Optional[str] = Query(default=None, description="上下文信息（JSON 字符串）")
):
    """
    获取推荐查询

    Args:
        context: 上下文信息（可选）

    Returns:
        推荐查询列表
    """
    try:
        import json
        ctx = json.loads(context) if context else None
        suggestions = query_assistant_service.get_suggested_queries(ctx)

        return Response(
            code=ErrorCode.SUCCESS,
            message="Success",
            data={
                "suggestions": suggestions,
                "count": len(suggestions)
            }
        )

    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"获取推荐失败：{str(e)}"
        )


# ========== 智能报告 API ==========

@router.post("/report/generate", response_model=Response)
async def generate_report(
    report_title: str = Body(..., embed=True, description="报告标题"),
    report_type: str = Body(default="custom", embed=True, description="报告类型：weekly/monthly/custom/anomaly"),
    query_ids: Optional[List[str]] = Body(None, embed=True, description="关联的查询 ID 列表"),
    user_id: str = Body(..., embed=True, description="用户 ID")
):
    """
    生成智能报告

    基于查询历史生成完整的分析报告

    Args:
        report_title: 报告标题
        report_type: 报告类型
        query_ids: 关联的查询 ID 列表（可选）
        user_id: 用户 ID

    Returns:
        生成的报告
    """
    try:
        from repositories.query_repository import QueryAssistantRepository

        # 获取相关查询数据
        repo = QueryAssistantRepository()
        queries_data = []
        if query_ids:
            for qid in query_ids:
                query = repo.get_query(qid)
                if query:
                    queries_data.append(query.to_dict())

        # 构建报告内容
        report_content = {
            "title": report_title,
            "type": report_type,
            "generated_at": datetime.now().isoformat(),
            "queries": queries_data,
            "summary": {
                "total_queries": len(queries_data),
                "key_insights": []
            }
        }

        # 保存报告
        report = query_assistant_service.save_report(
            report_title=report_title,
            report_type=report_type,
            report_content=report_content,
            user_id=user_id,
            query_ids=query_ids
        )

        return Response(
            code=ErrorCode.SUCCESS,
            message="报告生成成功",
            data=report.to_dict()
        )

    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"生成报告失败：{str(e)}"
        )


@router.get("/reports/{user_id}", response_model=Response)
async def get_user_reports(user_id: str):
    """
    获取用户报告列表

    Args:
        user_id: 用户 ID

    Returns:
        报告列表
    """
    try:
        reports = query_assistant_service.get_user_reports(user_id)

        return Response(
            code=ErrorCode.SUCCESS,
            message="Success",
            data={
                "user_id": user_id,
                "reports": [r.to_dict() for r in reports],
                "count": len(reports)
            }
        )

    except Exception as e:
        logger.error(f"Error getting user reports: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"获取报告失败：{str(e)}"
        )


@router.get("/report/{report_id}", response_model=Response)
async def get_report_detail(report_id: str):
    """
    获取报告详情

    Args:
        report_id: 报告 ID

    Returns:
        报告详情
    """
    try:
        from repositories.query_repository import QueryAssistantRepository
        repo = QueryAssistantRepository()
        report = repo.get_report(report_id)

        if not report:
            return Response(
                code=ErrorCode.NOT_FOUND,
                message="报告不存在"
            )

        return Response(
            code=ErrorCode.SUCCESS,
            message="Success",
            data=report.to_dict()
        )

    except Exception as e:
        logger.error(f"Error getting report detail: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"获取报告详情失败：{str(e)}"
        )


@router.delete("/report/{report_id}", response_model=Response)
async def delete_report(
    report_id: str,
    user_id: str = Query(..., description="用户 ID")
):
    """
    删除报告

    Args:
        report_id: 报告 ID
        user_id: 用户 ID

    Returns:
        删除结果
    """
    try:
        from repositories.query_repository import QueryAssistantRepository
        repo = QueryAssistantRepository()
        success = repo.delete_report(report_id, user_id)

        if success:
            return Response(
                code=ErrorCode.SUCCESS,
                message="删除成功"
            )
        else:
            return Response(
                code=ErrorCode.NOT_FOUND,
                message="报告不存在或无权限"
            )

    except Exception as e:
        logger.error(f"Error deleting report: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"删除报告失败：{str(e)}"
        )


# ========== 统计 API ==========

@router.get("/stats", response_model=Response)
async def get_stats(
    user_id: Optional[str] = Query(default=None, description="用户 ID（可选）")
):
    """
    获取查询统计

    Args:
        user_id: 用户 ID（可选）

    Returns:
        统计信息
    """
    try:
        stats = query_assistant_service.get_stats(user_id)

        return Response(
            code=ErrorCode.SUCCESS,
            message="Success",
            data=stats
        )

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"获取统计失败：{str(e)}"
        )


@router.get("/stats/intent-distribution", response_model=Response)
async def get_intent_distribution(
    days: int = Query(default=7, ge=1, le=90, description="统计天数")
):
    """
    获取查询意图分布

    Args:
        days: 统计天数

    Returns:
        意图分布数据
    """
    try:
        from repositories.query_repository import QueryAssistantRepository
        repo = QueryAssistantRepository()
        distribution = repo.get_intent_distribution(days)

        return Response(
            code=ErrorCode.SUCCESS,
            message="Success",
            data={
                "days": days,
                "distribution": distribution
            }
        )

    except Exception as e:
        logger.error(f"Error getting intent distribution: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"获取意图分布失败：{str(e)}"
        )


# ========== 入口 API ==========

@router.get("/", response_model=Response)
async def query_assistant_root():
    """AI 查询助手 API 入口"""
    return Response(
        code=ErrorCode.SUCCESS,
        message="欢迎使用 AI 查询助手",
        data={
            "service": "AI Traffic Booster - Query Assistant",
            "version": "1.8.0",
            "capabilities": {
                "natural_language_query": "/api/ai/query/ask",
                "query_history": "/api/ai/query/history/{session_id}",
                "favorites": "/api/ai/query/favorites/{user_id}",
                "templates": "/api/ai/query/templates",
                "report_generation": "/api/ai/query/report/generate",
                "suggestions": "/api/ai/query/suggestions"
            },
            "example_queries": [
                "上周哪个页面流量最高？",
                "最近 30 天的流量趋势如何？",
                "为什么流量下跌了？",
                "我该如何提升流量？",
                "这个月和上个月比怎么样？",
                "用户留存率如何？"
            ]
        }
    )
