"""
Chat API - 对话式流量优化 API

提供自然语言对话接口，替代传统手动配置
"""
from fastapi import APIRouter, HTTPException, Body, Query, Header
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import uuid

from agents.traffic_agent import TrafficAgent, get_traffic_agent, AgentContext, AgentResponse
from agents.deerflow_client import get_deerflow_client
from workflows.traffic_workflows import get_traffic_workflows
from workflows.strategy_workflows import get_strategy_workflows

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["AI 对话助手"])


# ========== 请求/响应模型 ==========

class ChatMessage(BaseModel):
    """聊天消息"""
    message: str = Field(..., description="用户消息内容")
    session_id: Optional[str] = Field(None, description="会话 ID")
    user_id: Optional[str] = Field(None, description="用户 ID")


class ChatResponse(BaseModel):
    """聊天响应"""
    message: str = Field(..., description="AI 回复消息")
    action_taken: Optional[str] = Field(None, description="执行的操作")
    confidence: float = Field(0.0, description="置信度")
    requires_approval: bool = Field(False, description="是否需要批准")
    data: Dict[str, Any] = Field(default_factory=dict, description="附加数据")
    suggestions: List[str] = Field(default_factory=list, description="建议操作")
    session_id: str = Field(..., description="会话 ID")
    timestamp: str = Field(..., description="时间戳")


class InsightPush(BaseModel):
    """主动推送的洞察"""
    insight_type: str = Field(..., description="洞察类型：anomaly/opportunity/report")
    title: str = Field(..., description="洞察标题")
    content: str = Field(..., description="洞察内容")
    priority: str = Field("normal", description="优先级：low/normal/high/critical")
    data: Dict[str, Any] = Field(default_factory=dict, description="附加数据")


# ========== 会话管理 ==========

# 内存会话存储（生产环境应使用 Redis）
_sessions: Dict[str, Dict[str, Any]] = {}


def get_or_create_session(session_id: Optional[str], user_id: Optional[str]) -> tuple[str, Dict]:
    """获取或创建会话"""
    if not session_id or session_id not in _sessions:
        session_id = session_id or str(uuid.uuid4())
        _sessions[session_id] = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "messages": [],
            "context": {}
        }
    return session_id, _sessions[session_id]


def add_message_to_session(session_id: str, role: str, content: str, data: Optional[Dict] = None):
    """添加消息到会话"""
    if session_id in _sessions:
        _sessions[session_id]["messages"].append({
            "role": role,
            "content": content,
            "data": data or {},
            "timestamp": datetime.now().isoformat()
        })


# ========== API 端点 ==========

@router.post("/message", response_model=ChatResponse, summary="发送消息", description="发送自然语言消息与 AI 助手对话")
async def send_message(
    request: ChatMessage,
    x_trace_id: Optional[str] = Header(None, description="追踪 ID")
) -> ChatResponse:
    """
    对话式交互入口

    用户可以通过自然语言与 AI 助手交流，例如：
    - "分析上周流量为什么下跌"
    - "帮我发现增长机会"
    - "执行 SEO 优化策略"

    AI 将理解意图并执行相应操作
    """
    trace_id = x_trace_id or f"trace_{datetime.now().timestamp()}"
    logger.info(f"[{trace_id}] Processing chat message: {request.message}")

    # 获取或创建会话
    session_id, session = get_or_create_session(request.session_id, request.user_id)

    # 记录用户消息
    add_message_to_session(session_id, "user", request.message)

    try:
        # 创建 Agent 上下文
        context = AgentContext(
            user_id=request.user_id,
            session_id=session_id,
            trace_id=trace_id,
            preferences=session.get("preferences", {})
        )

        # 获取 Agent 实例
        agent = get_traffic_agent()
        agent.set_context(context)

        # 处理消息
        response = await agent.chat(request.message)

        # 记录 AI 回复
        add_message_to_session(
            session_id,
            "assistant",
            response.message,
            {
                "action_taken": response.action_taken,
                "confidence": response.confidence,
                "data": response.data
            }
        )

        return ChatResponse(
            message=response.message,
            action_taken=response.action_taken,
            confidence=response.confidence,
            requires_approval=response.requires_approval,
            data=response.data,
            suggestions=response.suggestions,
            session_id=session_id,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"[{trace_id}] Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights", response_model=List[Dict[str, Any]], summary="获取洞察", description="获取 AI 主动发现的洞察")
async def get_insights(
    session_id: Optional[str] = Query(None, description="会话 ID"),
    limit: int = Query(10, description="返回数量限制"),
    insight_type: Optional[str] = Query(None, description="洞察类型过滤")
) -> List[Dict[str, Any]]:
    """
    获取 AI 主动发现的洞察

    包括：
    - 异常检测
    - 增长机会
    - 效果报告
    """
    trace_id = f"trace_{datetime.now().timestamp()}"
    logger.info(f"[{trace_id}] Getting insights, type={insight_type}, limit={limit}")

    # TODO: 从洞察服务获取
    insights = [
        {
            "id": "insight_1",
            "type": "anomaly",
            "title": "流量异常下跌 15%",
            "content": "检测到自然搜索流量较昨日下跌 15%，主要影响页面：/blog/seo-tips",
            "priority": "high",
            "data": {
                "metric": "organic_traffic",
                "change_percent": -15,
                "affected_pages": ["/blog/seo-tips"]
            },
            "timestamp": datetime.now().isoformat(),
            "actions": [
                {"action": "analyze", "label": "分析原因"},
                {"action": "fix", "label": "一键修复"}
            ]
        },
        {
            "id": "insight_2",
            "type": "opportunity",
            "title": "3 个关键词有上升空间",
            "content": "发现 3 个关键词排名在第 4-10 位，优化后有望进入前 3",
            "priority": "normal",
            "data": {
                "keywords": [
                    {"keyword": "seo tools", "current_rank": 7, "potential": 3},
                    {"keyword": "traffic analysis", "current_rank": 4, "potential": 2}
                ]
            },
            "timestamp": datetime.now().isoformat(),
            "actions": [
                {"action": "optimize", "label": "开始优化"}
            ]
        }
    ]

    if insight_type:
        insights = [i for i in insights if i["type"] == insight_type]

    return insights[:limit]


@router.post("/insights/approve", response_model=Dict[str, Any], summary="批准洞察操作", description="批准 AI 建议的操作")
async def approve_insight(
    insight_id: str = Body(..., description="洞察 ID"),
    action: str = Body(..., description="要执行的操作"),
    session_id: Optional[str] = Body(None, description="会话 ID")
) -> Dict[str, Any]:
    """
    批准 AI 建议的操作

    当 AI 发现需要批准的操作时，用户可通过此接口批准执行
    """
    trace_id = f"trace_{datetime.now().timestamp()}"
    logger.info(f"[{trace_id}] Approving insight {insight_id} action {action}")

    # TODO: 执行批准的操作
    return {
        "status": "success",
        "message": f"已批准执行操作：{action}",
        "insight_id": insight_id,
        "execution_id": f"exec_{datetime.now().timestamp()}"
    }


@router.get("/sessions/{session_id}/history", response_model=List[Dict[str, Any]], summary="获取会话历史", description="获取会话历史消息")
async def get_session_history(
    session_id: str,
    limit: int = Query(50, description="返回数量限制")
) -> List[Dict[str, Any]]:
    """获取会话历史消息"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _sessions[session_id]
    messages = session.get("messages", [])
    return messages[-limit:]


@router.delete("/sessions/{session_id}", summary="删除会话", description="删除指定会话")
async def delete_session(session_id: str) -> Dict[str, Any]:
    """删除会话"""
    if session_id in _sessions:
        del _sessions[session_id]
        return {"status": "success", "message": "会话已删除"}
    raise HTTPException(status_code=404, detail="Session not found")


@router.post("/workflows/diagnosis", response_model=Dict[str, Any], summary="运行诊断工作流", description="运行自动流量诊断工作流")
async def run_diagnosis_workflow(
    request: Dict[str, Any] = Body(..., description="请求参数"),
    x_trace_id: Optional[str] = Header(None, description="追踪 ID")
) -> Dict[str, Any]:
    """
    运行自动流量诊断工作流

    自动执行：
    1. 获取流量数据
    2. 检测异常
    3. 分析根因
    4. 生成诊断报告
    """
    trace_id = x_trace_id or f"trace_{datetime.now().timestamp()}"
    logger.info(f"[{trace_id}] Running diagnosis workflow")

    try:
        workflows = get_traffic_workflows()
        result = await workflows.run_auto_diagnosis(
            trace_id=trace_id,
            **request
        )
        return result
    except Exception as e:
        logger.error(f"[{trace_id}] Diagnosis workflow error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/opportunities", response_model=Dict[str, Any], summary="运行机会发现工作流", description="运行增长机会发现工作流")
async def run_opportunities_workflow(
    request: Dict[str, Any] = Body(..., description="请求参数"),
    x_trace_id: Optional[str] = Header(None, description="追踪 ID")
) -> Dict[str, Any]:
    """
    运行增长机会发现工作流

    自动执行：
    1. 分析当前流量状况
    2. 分析竞品数据
    3. 识别机会点
    4. 评估机会价值
    """
    trace_id = x_trace_id or f"trace_{datetime.now().timestamp()}"
    logger.info(f"[{trace_id}] Running opportunities workflow")

    try:
        workflows = get_traffic_workflows()
        result = await workflows.run_opportunity_discovery(
            trace_id=trace_id,
            **request
        )
        return result
    except Exception as e:
        logger.error(f"[{trace_id}] Opportunities workflow error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/strategy/create", response_model=Dict[str, Any], summary="创建策略工作流", description="运行策略创建工作流")
async def run_create_strategy_workflow(
    request: Dict[str, Any] = Body(..., description="请求参数"),
    x_trace_id: Optional[str] = Header(None, description="追踪 ID")
) -> Dict[str, Any]:
    """
    运行策略创建工作流

    自动执行：
    1. 分析当前问题
    2. 生成候选策略
    3. 评估策略效果
    4. 选择最优策略
    """
    trace_id = x_trace_id or f"trace_{datetime.now().timestamp()}"
    logger.info(f"[{trace_id}] Running create strategy workflow")

    try:
        workflows = get_strategy_workflows()
        result = await workflows.run_create_strategy(
            trace_id=trace_id,
            **request
        )
        return result
    except Exception as e:
        logger.error(f"[{trace_id}] Create strategy workflow error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 主动推送 ==========

@router.get("/push/subscribe", summary="订阅推送", description="订阅 AI 主动推送的洞察")
async def subscribe_push(
    user_id: str = Query(..., description="用户 ID"),
    insight_types: List[str] = Query(["anomaly", "opportunity"], description="订阅的洞察类型")
) -> Dict[str, Any]:
    """订阅 AI 主动推送的洞察"""
    # TODO: 实现推送订阅（WebSocket/SSE）
    return {
        "status": "success",
        "message": "推送订阅已创建",
        "user_id": user_id,
        "subscribed_types": insight_types
    }


# ========== 系统状态 ==========

@router.get("/status", response_model=Dict[str, Any], summary="AI 助手状态", description="获取 AI 助手运行状态")
async def get_ai_status() -> Dict[str, Any]:
    """获取 AI 助手运行状态"""
    client = get_deerflow_client()
    agent = get_traffic_agent()

    return {
        "status": "running",
        "deerflow_available": client.is_available(),
        "fallback_mode": client.is_fallback(),
        "auto_execute_threshold": agent.auto_execute_threshold,
        "request_approval_threshold": agent.request_approval_threshold,
        "active_sessions": len(_sessions),
        "timestamp": datetime.now().isoformat()
    }
