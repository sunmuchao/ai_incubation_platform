"""
LLM API 路由 - P7

提供 AI 对话、智能洞察、报告叙述等 API 端点
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, List, Dict, Any
import logging
import uuid
from datetime import datetime

from schemas.common import Response, ErrorCode
from services.llm_service import llm_service, AIInsight, ReportNarrative

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai-llm"])


@router.post("/chat", response_model=Response)
async def chat_with_ai(
    message: str = Body(..., embed=True, description="用户消息"),
    session_id: Optional[str] = Body(None, embed=True, description="会话 ID（用于多轮对话）"),
    context: Optional[Dict[str, Any]] = Body(None, embed=True, description="上下文信息")
):
    """
    AI 对话助手

    与 AI 助手进行自然语言对话，可以：
    - 询问流量数据相关问题
    - 请求分析建议
    - 解释数据趋势
    - 获取优化方案

    Args:
        message: 用户消息
        session_id: 会话 ID（可选，用于保持对话上下文）
        context: 上下文信息（如当前查看的数据）

    Returns:
        AI 响应
    """
    try:
        result = llm_service.chat(
            message=message,
            session_id=session_id,
            context=context
        )

        return Response(
            code=ErrorCode.SUCCESS,
            message="Success",
            data=result
        )

    except Exception as e:
        logger.error(f"Error in chat: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Chat failed: {str(e)}"
        )


@router.get("/chat/history/{session_id}", response_model=Response)
async def get_chat_history(session_id: str):
    """
    获取聊天历史

    Args:
        session_id: 会话 ID

    Returns:
        聊天历史消息列表
    """
    try:
        history = llm_service.get_chat_history(session_id)

        return Response(
            code=ErrorCode.SUCCESS,
            message="Success",
            data={
                "session_id": session_id,
                "messages": history,
                "count": len(history)
            }
        )

    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get chat history: {str(e)}"
        )


@router.delete("/chat/session/{session_id}", response_model=Response)
async def delete_chat_session(session_id: str):
    """
    删除聊天会话

    Args:
        session_id: 会话 ID

    Returns:
        删除结果
    """
    try:
        success = llm_service._session_manager.delete_session(session_id)

        if success:
            return Response(
                code=ErrorCode.SUCCESS,
                message="Session deleted successfully"
            )
        else:
            return Response(
                code=ErrorCode.NOT_FOUND,
                message="Session not found"
            )

    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to delete session: {str(e)}"
        )


@router.post("/insights/generate", response_model=Response)
async def generate_insights(
    data: Dict[str, Any] = Body(..., description="分析数据"),
    insight_type: str = Body(default="general", description="洞察类型：anomaly/opportunity/trend/recommendation")
):
    """
    生成深度 AI 洞察

    基于提供的数据生成深刻的业务洞察，包括：
    - 异常检测分析
    - 机会识别
    - 趋势预测
    - 优化建议

    Args:
        data: 分析数据
        insight_type: 洞察类型

    Returns:
        AI 洞察
    """
    try:
        insight = llm_service.generate_insight(
            data=data,
            insight_type=insight_type
        )

        return Response(
            code=ErrorCode.SUCCESS,
            message="Insight generated successfully",
            data={
                "insight_id": insight.insight_id,
                "title": insight.title,
                "content": insight.content,
                "category": insight.category,
                "confidence": insight.confidence,
                "data_points": insight.data_points,
                "created_at": insight.created_at.isoformat()
            }
        )

    except Exception as e:
        logger.error(f"Error generating insight: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to generate insight: {str(e)}"
        )


@router.post("/report/narrative", response_model=Response)
async def generate_report_narrative(
    report_data: Dict[str, Any] = Body(..., description="报告数据"),
    section: str = Body(default="overview", description="报告章节：overview/traffic/conversion/user_behavior/recommendations")
):
    """
    生成报告叙述

    将数据转化为引人入胜的自然语言叙述，用于：
    - 自动化报告生成
    - 数据解读说明
    - 洞察总结

    Args:
        report_data: 报告数据
        section: 报告章节

    Returns:
        报告叙述
    """
    try:
        narrative = llm_service.generate_report_narrative(
            report_data=report_data,
            section=section
        )

        return Response(
            code=ErrorCode.SUCCESS,
            message="Report narrative generated successfully",
            data={
                "section": narrative.section,
                "title": narrative.title,
                "narrative": narrative.narrative,
                "key_findings": narrative.key_findings,
                "recommendations": narrative.recommendations
            }
        )

    except Exception as e:
        logger.error(f"Error generating report narrative: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to generate report narrative: {str(e)}"
        )


@router.post("/insights/batch", response_model=Response)
async def generate_batch_insights(
    data: Dict[str, Any] = Body(..., description="分析数据")
):
    """
    批量生成多维度洞察

    一次性生成多种类型的洞察（异常、机会、趋势、建议）

    Args:
        data: 分析数据

    Returns:
        多种洞察列表
    """
    try:
        insights = []
        insight_types = ["anomaly", "opportunity", "trend", "recommendation"]

        for insight_type in insight_types:
            try:
                insight = llm_service.generate_insight(
                    data=data,
                    insight_type=insight_type
                )
                insights.append({
                    "insight_id": insight.insight_id,
                    "title": insight.title,
                    "category": insight.category,
                    "confidence": insight.confidence,
                    "preview": insight.content[:200] + "..." if len(insight.content) > 200 else insight.content
                })
            except Exception as e:
                logger.warning(f"Failed to generate {insight_type} insight: {e}")

        return Response(
            code=ErrorCode.SUCCESS,
            message="Batch insights generated",
            data={
                "insights": insights,
                "count": len(insights)
            }
        )

    except Exception as e:
        logger.error(f"Error generating batch insights: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to generate batch insights: {str(e)}"
        )


@router.get("/chat/sessions", response_model=Response)
async def list_chat_sessions(
    limit: int = Query(default=20, ge=1, le=100, description="返回数量限制")
):
    """
    列出最近的聊天会话

    Args:
        limit: 返回数量限制

    Returns:
        会话列表
    """
    try:
        # 获取所有会话
        sessions = llm_service._session_manager._sessions

        # 按更新时间排序
        sorted_sessions = sorted(
            sessions.values(),
            key=lambda s: s.updated_at,
            reverse=True
        )[:limit]

        return Response(
            code=ErrorCode.SUCCESS,
            message="Success",
            data={
                "sessions": [
                    {
                        "session_id": s.session_id,
                        "message_count": len(s.messages),
                        "created_at": s.created_at.isoformat(),
                        "updated_at": s.updated_at.isoformat(),
                        "last_message": s.messages[-1].content if s.messages else None
                    }
                    for s in sorted_sessions
                ],
                "total": len(sorted_sessions)
            }
        )

    except Exception as e:
        logger.error(f"Error listing chat sessions: {e}")
        return Response(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to list chat sessions: {str(e)}"
        )
