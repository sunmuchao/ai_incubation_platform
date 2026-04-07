"""
路由工作流 - 意图识别与路由分发
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from agents.portal_agent import PortalAgent

logger = logging.getLogger(__name__)


async def routing_workflow(
    user_input: str,
    user_id: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    意图识别与路由工作流

    这是 PortalAgent 的核心工作流：
    1. 接收用户请求
    2. LLM 意图分析
    3. 匹配子项目
    4. 路由请求
    5. 聚合结果
    6. 返回响应

    Args:
        user_input: 用户自然语言输入
        user_id: 用户 ID
        session_id: 会话 ID

    Returns:
        工作流执行结果
    """
    logger.info(f"[Routing Workflow] User {user_id}: {user_input[:100]}...")

    start_time = datetime.now()
    agent = PortalAgent()

    # 执行对话式交互
    result = await agent.chat(
        message=user_input,
        user_id=user_id,
        session_id=session_id,
    )

    latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)

    return {
        "workflow_name": "routing",
        "success": True,
        "result": result,
        "latency_ms": latency_ms,
        "timestamp": datetime.now().isoformat(),
    }


async def cross_project_workflow(
    workflow_name: str,
    user_id: str,
    input_data: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    跨项目编排工作流

    协调多个子项目完成复杂任务。

    Args:
        workflow_name: 工作流名称
        user_id: 用户 ID
        input_data: 输入数据
        session_id: 会话 ID

    Returns:
        工作流执行结果
    """
    logger.info(f"[Cross-Project Workflow] {workflow_name} for user {user_id}")

    start_time = datetime.now()
    agent = PortalAgent()

    # 执行工作流
    result = await agent.execute_workflow(
        workflow_name=workflow_name,
        user_id=user_id,
        input_data=input_data,
    )

    latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)

    return {
        "workflow_name": workflow_name,
        "success": result.get("success", False),
        "result": result,
        "latency_ms": latency_ms,
        "timestamp": datetime.now().isoformat(),
    }
