"""
对话式 API

提供 Chat-first 的交互接口，支持流式输出和动态响应
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import asyncio
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.code_agent import get_code_agent
from agent.workflows.code_workflows import (
    CodeUnderstandingWorkflow,
    CodeExplorationWorkflow,
    ImpactAnalysisWorkflow,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    project: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """聊天响应"""
    type: str  # thinking, discovery, explanation, visualization, suggestion, error
    content: Any
    metadata: Optional[Dict[str, Any]] = None


async def stream_response_generator(
    message: str,
    project: str,
    context: Optional[Dict] = None
):
    """流式响应生成器"""
    agent = get_code_agent(project_name=project)

    try:
        # 发送思考开始事件
        yield f"data: {json.dumps({'type': 'thinking', 'content': '正在理解您的问题...'})}\n\n"
        await asyncio.sleep(0.1)

        # 执行 Agent
        yield f"data: {json.dumps({'type': 'thinking', 'content': '正在检索相关代码...'})}\n\n"

        # 根据消息类型选择工作流
        if any(kw in message.lower() for kw in ["探索", "explore", "全局", "overview", "架构"]):
            workflow = CodeExplorationWorkflow()
            workflow_name = "code_exploration"
        elif any(kw in message.lower() for kw in ["影响", "impact", "修改", "change"]):
            workflow = ImpactAnalysisWorkflow()
            workflow_name = "impact_analysis"
        else:
            workflow = CodeUnderstandingWorkflow()
            workflow_name = "code_understanding"

        yield f"data: {json.dumps({'type': 'thinking', 'content': f'执行工作流：{workflow_name}'})}\n\n"

        # 执行工作流
        input_data = {
            "message": message,
            "context": context or {},
            "project_name": project,
            "file_path": context.get("file_path") if context else None,
            "repo_hint": context.get("repo_path", ".") if context else ".",
        }

        result = await workflow.execute(input_data)

        # 发送发现事件
        if result.get("citations"):
            discovery_msg = json.dumps({
                'type': 'discovery',
                'content': f'找到 {len(result["citations"])} 个相关代码片段'
            })
            yield f"data: {discovery_msg}\n\n"

        # 发送解释内容
        explanation_msg = json.dumps({
            'type': 'explanation',
            'content': result.get('explanation', ''),
            'metadata': {
                'confidence': result.get('confidence', 0.5),
                'citations': result.get('citations', []),
            }
        })
        yield f"data: {explanation_msg}\n\n"

        # 发送建议
        if result.get('suggestions'):
            suggestion_msg = json.dumps({
                'type': 'suggestion',
                'content': result['suggestions']
            })
            yield f"data: {suggestion_msg}\n\n"

        # 完成
        yield f"data: {json.dumps({'type': 'done', 'content': '回答完成'})}\n\n"

    except Exception as e:
        logger.error(f"流式响应生成失败：{e}")
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"


@router.post("/")
async def chat(request: ChatRequest):
    """
    对话式 API 入口

    支持流式输出，返回类型包括：
    - thinking: 思考过程
    - discovery: 发现的相关信息
    - explanation: 主要解释内容
    - visualization: 可视化数据
    - suggestion: 下一步建议
    """
    return StreamingResponse(
        stream_response_generator(
            message=request.message,
            project=request.project or "default",
            context=request.context
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/sync")
async def chat_sync(request: ChatRequest):
    """
    同步对话接口（不使用流式）

    适用于不支持 SSE 的客户端
    """
    agent = get_code_agent(project_name=request.project or "default")

    try:
        context = request.context or {}
        result = await agent.run(request.message, context)

        return {
            "success": True,
            "response": result.get("content", {}),
            "thinking": result.get("thinking", []),
            "intent": result.get("intent", "general"),
            "confidence": result.get("confidence", 0.5),
            "suggestions": result.get("suggestions", []),
        }
    except Exception as e:
        logger.error(f"同步对话失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_chat_history(project: Optional[str] = None):
    """获取聊天历史"""
    # TODO: 实现聊天历史存储和检索
    return {
        "success": True,
        "history": [],
        "message": "聊天历史功能待实现"
    }


@router.post("/clear")
async def clear_chat_history(project: Optional[str] = None):
    """清除聊天历史"""
    # TODO: 实现聊天历史清除
    return {
        "success": True,
        "message": "聊天历史已清除"
    }
