"""
对话式 API - AI Native 统一入口

提供自然语言对话接口，用户通过对话访问所有子项目能力。
"""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from agents.portal_agent import portal_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chat"])


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户自然语言消息", min_length=1, max_length=5000)
    user_id: str = Field(..., description="用户 ID")
    session_id: Optional[str] = Field(None, description="会话 ID，用于上下文连续性")
    context: Optional[Dict[str, Any]] = Field(None, description="额外上下文信息")


class ChatResponse(BaseModel):
    """聊天响应"""
    session_id: str
    user_id: str
    message: str
    response: Dict[str, Any]
    action: str
    project: Optional[str]
    confidence: float
    timestamp: str


class ProjectInfo(BaseModel):
    """项目信息"""
    name: str
    description: str
    capabilities: list


class WorkflowInfo(BaseModel):
    """工作流信息"""
    name: str
    description: str
    projects: list


class WorkflowExecuteRequest(BaseModel):
    """工作流执行请求"""
    workflow_name: str = Field(..., description="工作流名称")
    user_id: str = Field(..., description="用户 ID")
    input_data: Optional[Dict[str, Any]] = Field(None, description="输入数据")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    对话式交互入口

    这是 AI Native 架构的核心接口，用户通过自然语言与门户交互，
    Agent 自主决策如何处理请求：
    - 意图识别：分析用户想去哪个子项目
    - 路由分发：转发请求到对应子项目
    - 跨项目编排：协调多项目完成复杂任务

    示例：
    - "我想发布一个线下数据采集任务" -> 路由到 ai-hires-human
    - "帮我分析一下这个代码仓库" -> 路由到 ai-code-understanding
    - "我想创业，需要帮助" -> 触发 startup_journey 工作流
    """
    logger.info(f"Chat request from user {request.user_id}: {request.message[:100]}...")

    try:
        result = await portal_agent.chat(
            message=request.message,
            user_id=request.user_id,
            session_id=request.session_id,
            context=request.context,
        )

        return ChatResponse(**result)

    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects")
async def list_projects() -> Dict[str, Any]:
    """
    获取所有子项目列表

    返回每个项目的名称、描述和能力清单。
    """
    from tools.intent_tools import SUB_PROJECTS

    projects = [
        {
            "name": name,
            "description": info.get("description", ""),
            "capabilities": info.get("capabilities", []),
            "keywords": info.get("keywords", []),
        }
        for name, info in SUB_PROJECTS.items()
    ]

    return {
        "count": len(projects),
        "projects": projects,
    }


@router.get("/workflows")
async def list_workflows() -> Dict[str, Any]:
    """
    获取所有跨项目工作流列表

    返回每个预定义工作流的名称、描述和参与项目。
    """
    from agents.portal_agent import WORKFLOW_TEMPLATES

    workflows = [
        {
            "name": name,
            "description": template.get("description", ""),
            "projects": template.get("projects", []),
            "workflow": template.get("workflow", []),
        }
        for name, template in WORKFLOW_TEMPLATES.items()
    ]

    return {
        "count": len(workflows),
        "workflows": workflows,
    }


@router.post("/workflow/execute")
async def execute_workflow(request: WorkflowExecuteRequest) -> Dict[str, Any]:
    """
    执行跨项目工作流

    用户可以直接调用预定义的跨项目工作流，如：
    - startup_journey: 创业旅程
    - talent_pipeline: 人才管道
    - full_stack_analysis: 全栈分析
    - community_growth: 社区增长
    """
    logger.info(f"Execute workflow {request.workflow_name} for user {request.user_id}")

    try:
        result = await portal_agent.execute_workflow(
            workflow_name=request.workflow_name,
            user_id=request.user_id,
            input_data=request.input_data,
        )
        return result
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/intent/analyze")
async def analyze_intent(user_input: str = Query(..., description="用户输入")) -> Dict[str, Any]:
    """
    分析用户意图（调试接口）

    用于测试意图识别功能，返回匹配的子项目和置信度。
    """
    from tools.intent_tools import identify_intent

    result = await identify_intent(user_input)
    return result


@router.get("/tools")
async def list_tools() -> Dict[str, Any]:
    """
    获取所有可用工具列表

    返回 PortalAgent 注册的所有工具及其描述。
    """
    from tools.registry import list_tools as registry_list_tools

    tools = registry_list_tools()
    return {
        "count": len(tools),
        "tools": tools,
    }


@router.get("/session/{session_id}/history")
async def get_session_history(session_id: str) -> Dict[str, Any]:
    """
    获取会话历史

    返回指定会话的完整交互历史。
    """
    history = portal_agent.get_session_history(session_id)
    return {
        "session_id": session_id,
        "history": history,
        "count": len(history),
    }
