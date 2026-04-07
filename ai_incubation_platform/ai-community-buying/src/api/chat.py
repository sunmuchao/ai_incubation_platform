"""
对话式 API - AI Native 交互接口

提供自然语言对话接口，支持用户通过对话发起团购、查询商品、跟踪进度等。
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["AI 对话"])


# ==================== 请求/响应模型 ====================

class ChatMessage(BaseModel):
    """对话消息"""
    role: str = Field(..., description="角色类型", enum=["user", "assistant", "system"])
    content: str = Field(..., description="消息内容")
    timestamp: Optional[str] = Field(None, description="时间戳")


class ChatRequest(BaseModel):
    """对话请求"""
    user_id: str = Field(..., description="用户 ID")
    message: str = Field(..., description="用户输入消息")
    session_id: Optional[str] = Field(None, description="会话 ID（不传则新建）")
    community_id: Optional[str] = Field(None, description="社区 ID")
    conversation_history: Optional[List[ChatMessage]] = Field(None, description="对话历史")


class ChatSuggestion(BaseModel):
    """对话建议"""
    text: str = Field(..., description="建议文本")
    action: Optional[str] = Field(None, description="关联操作", enum=["create_group", "find_product", "check_status", "view_detail", "invite"])
    params: Optional[Dict[str, Any]] = Field(None, description="操作参数")


class ChatResponse(BaseModel):
    """对话响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="AI 回复内容")
    session_id: str = Field(..., description="会话 ID")
    suggestions: List[ChatSuggestion] = Field(default_factory=list, description="建议操作")
    action: Optional[str] = Field(None, description="执行的操作类型")
    data: Optional[Dict[str, Any]] = Field(None, description="附加数据")
    confidence: float = Field(default=0.0, description="置信度")
    trace_id: Optional[str] = Field(None, description="追踪 ID")


class SessionInfo(BaseModel):
    """会话信息"""
    session_id: str
    user_id: str
    created_at: str
    last_active_at: str
    message_count: int
    current_intent: Optional[str] = None
    slot_values: Dict[str, Any] = Field(default_factory=dict)


# ==================== 会话管理 ====================

# 内存会话存储（生产环境应使用 Redis）
_sessions: Dict[str, Dict[str, Any]] = {}


def get_or_create_session(
    user_id: str,
    session_id: Optional[str] = None,
    community_id: Optional[str] = None
) -> Dict[str, Any]:
    """获取或创建会话"""
    if session_id and session_id in _sessions:
        session = _sessions[session_id]
        session["last_active_at"] = datetime.now().isoformat()
        return session

    # 创建新会话
    new_session_id = session_id or f"sess_{datetime.now().strftime('%Y%m%d%H%M%S')}_{user_id}"
    session = {
        "session_id": new_session_id,
        "user_id": user_id,
        "community_id": community_id,
        "created_at": datetime.now().isoformat(),
        "last_active_at": datetime.now().isoformat(),
        "messages": [],
        "current_intent": None,
        "slot_values": {},
        "message_count": 0
    }
    _sessions[new_session_id] = session
    return session


def save_message(session: Dict[str, Any], role: str, content: str) -> None:
    """保存对话消息"""
    session["messages"].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })
    session["message_count"] += 1
    session["last_active_at"] = datetime.now().isoformat()


# ==================== API 接口 ====================

@router.post("/", response_model=ChatResponse, summary="对话式交互")
@router.post("", response_model=ChatResponse, summary="对话式交互")
async def chat(request: ChatRequest, background_tasks: BackgroundTasks) -> ChatResponse:
    """
    ### AI 对话式交互接口

    用户通过自然语言与 AI 团购助手交互，支持：
    - 发起团购："我想买点水果"、"帮我找个牛奶团购"
    - 查询商品："有什么好吃的推荐"、"看看今日特价"
    - 跟踪进度："我的团购怎么样了"、"成团了吗"
    - 通用对话："你好"、"谢谢"

    ### 示例请求
    ```json
    {
        "user_id": "user_001",
        "message": "我想买点新鲜的水果，家里有两个小孩",
        "community_id": "comm_001"
    }
    ```

    ### 返回示例
    ```json
    {
        "success": true,
        "message": "好的！我为您推荐几款适合小朋友的新鲜水果...",
        "suggestions": [
            {"text": "发起【有机草莓】团购", "action": "create_group"},
            {"text": "看看其他水果", "action": "find_product"}
        ],
        "confidence": 0.9
    }
    ```
    """
    trace_id = f"chat_{datetime.now().strftime('%Y%m%d%H%M%S')}_{request.user_id}"
    logger.info(f"[{trace_id}] 对话请求：{request.message}")

    try:
        # 获取或创建会话
        session = get_or_create_session(
            user_id=request.user_id,
            session_id=request.session_id,
            community_id=request.community_id
        )

        # 保存用户消息
        save_message(session, "user", request.message)

        # 调用 AI Agent 处理对话
        agent_response = await process_with_agent(
            user_input=request.message,
            user_id=request.user_id,
            session_id=session["session_id"],
            community_id=session.get("community_id"),
            conversation_history=request.conversation_history,
            trace_id=trace_id
        )

        # 保存 AI 回复
        save_message(session, "assistant", agent_response["message"])

        # 更新会话状态
        if "intent" in agent_response:
            session["current_intent"] = agent_response["intent"]
        if "slots" in agent_response:
            session["slot_values"].update(agent_response["slots"])

        # 构建响应
        suggestions = [
            ChatSuggestion(text=s.get("text", ""), action=s.get("action"), params=s.get("params"))
            for s in agent_response.get("suggestions", [])
        ]

        return ChatResponse(
            success=True,
            message=agent_response["message"],
            session_id=session["session_id"],
            suggestions=suggestions,
            action=agent_response.get("action"),
            data=agent_response.get("data"),
            confidence=agent_response.get("confidence", 0.0),
            trace_id=trace_id
        )

    except Exception as e:
        logger.error(f"[{trace_id}] 对话处理异常：{str(e)}")
        return ChatResponse(
            success=False,
            message="抱歉，处理您的请求时出现了问题，请稍后重试",
            session_id=request.session_id or "",
            confidence=0.0,
            trace_id=trace_id
        )


@router.get("/sessions/{session_id}", response_model=SessionInfo, summary="获取会话信息")
async def get_session(session_id: str) -> SessionInfo:
    """获取会话详细信息"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="会话不存在")

    session = _sessions[session_id]
    return SessionInfo(
        session_id=session["session_id"],
        user_id=session["user_id"],
        created_at=session["created_at"],
        last_active_at=session["last_active_at"],
        message_count=session["message_count"],
        current_intent=session.get("current_intent"),
        slot_values=session.get("slot_values", {})
    )


@router.delete("/sessions/{session_id}", summary="删除会话")
async def delete_session(session_id: str):
    """删除指定会话"""
    if session_id in _sessions:
        del _sessions[session_id]
        return {"success": True, "message": "会话已删除"}
    raise HTTPException(status_code=404, detail="会话不存在")


@router.get("/history/{user_id}", response_model=List[Dict], summary="获取用户对话历史")
async def get_user_history(user_id: str, limit: int = 10) -> List[Dict]:
    """获取用户最近的对话会话"""
    user_sessions = [
        s for s in _sessions.values()
        if s["user_id"] == user_id
    ]
    user_sessions.sort(key=lambda x: x["last_active_at"], reverse=True)

    return [
        {
            "session_id": s["session_id"],
            "created_at": s["created_at"],
            "message_count": s["message_count"],
            "last_message": s["messages"][-1]["content"] if s["messages"] else None
        }
        for s in user_sessions[:limit]
    ]


@router.post("/sessions/{session_id}/clear", summary="清空会话历史")
async def clear_session_history(session_id: str) -> Dict[str, bool]:
    """清空指定会话的对话历史"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="会话不存在")

    _sessions[session_id]["messages"] = []
    _sessions[session_id]["current_intent"] = None
    _sessions[session_id]["slot_values"] = {}

    return {"success": True}


# ==================== AI Agent 处理 ====================

async def process_with_agent(
    user_input: str,
    user_id: str,
    session_id: str,
    community_id: Optional[str] = None,
    conversation_history: Optional[List[ChatMessage]] = None,
    trace_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    调用 AI Agent 处理用户输入

    返回格式：
    {
        "message": str,  # AI 回复内容
        "intent": str,   # 识别的意图
        "slots": dict,   # 填充的槽位
        "suggestions": list,  # 建议操作
        "action": str,   # 执行的操作
        "data": dict,    # 附加数据
        "confidence": float  # 置信度
    }
    """
    # 导入 Agent
    from agents.groupbuy_agent import GroupBuyAgent, AgentContext
    from agents.deerflow_client import DeerFlowClient

    # 创建 Agent 实例
    client = DeerFlowClient()
    agent = GroupBuyAgent(client=client)

    # 构建上下文
    context = AgentContext(
        user_id=user_id,
        session_id=session_id,
        request_id=trace_id or f"req_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        conversation_history=[
            {"role": m.role, "content": m.content}
            for m in (conversation_history or [])
        ],
        community_id=community_id
    )

    # 调用 Agent 对话
    response = await agent.chat(user_input=user_input, context=context)

    # 转换为 API 响应格式
    return {
        "message": response.message,
        "intent": response.action or "general_chat",
        "slots": {},
        "suggestions": [
            {"text": s, "action": _map_suggestion_to_action(s)}
            for s in response.suggestions
        ],
        "action": response.action if response.success else None,
        "data": response.data,
        "confidence": response.confidence
    }


def _map_suggestion_to_action(suggestion_text: str) -> Optional[str]:
    """将建议文本映射到操作类型"""
    text_lower = suggestion_text.lower()

    if any(kw in text_lower for kw in ["发起", "创建", "开团", "团购"]):
        return "create_group"
    elif any(kw in text_lower for kw in ["看看", "查看", "详情", "介绍"]):
        return "view_detail"
    elif any(kw in text_lower for kw in ["邀请", "分享"]):
        return "invite"
    elif any(kw in text_lower for kw in ["买", "找", "推荐"]):
        return "find_product"

    return None


# ==================== 快捷接口 ====================

@router.post("/quick-start", response_model=ChatResponse, summary="快捷发起团购")
async def quick_start_group(
    request: ChatRequest
) -> ChatResponse:
    """
    快捷发起团购 - 一键创建并邀请

    适用于用户已有明确购买目标时的快速流程。
    """
    trace_id = f"quick_{datetime.now().strftime('%Y%m%d%H%M%S')}_{request.user_id}"
    logger.info(f"[{trace_id}] 快捷发起团购")

    # 调用工作流
    from workflows.auto_create_group import AutoCreateGroupWorkflow

    workflow = AutoCreateGroupWorkflow()
    result = await workflow.execute(
        user_input=f"发起商品团购",
        user_id=request.user_id,
        community_id=request.community_id
    )

    group = result.get("group", {})

    return ChatResponse(
        success=True,
        message=f"团购发起成功！\n\n"
                f"商品：{group.get('product_name', '精选商品')}\n"
                f"成团价：¥{group.get('group_price', 0)}\n"
                f"目标人数：{group.get('min_participants', 10)}人\n\n"
                f"已自动邀请 {result.get('invited_count', 0)} 位邻居，"
                f"预计成团概率 {result.get('success_probability', 80)}%",
        session_id=f"quick_{group.get('id', '')}",
        suggestions=[
            {"text": "查看团购详情", "action": "view_detail"},
            {"text": "分享给好友", "action": "invite"},
            {"text": "再发起一个", "action": "create_group"}
        ],
        action="create_group",
        data=group,
        confidence=1.0,
        trace_id=trace_id
    )
