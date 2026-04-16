"""
Her Tools - User Tools Module

用户数据相关工具：获取用户画像、获取目标用户画像、获取对话历史
"""
import logging
import json
from datetime import datetime
from typing import Type, List, Dict

from langchain.tools import BaseTool
from pydantic import BaseModel

from .schemas import (
    ToolResult,
    HerGetUserInput,
    HerGetTargetUserInput,
    HerGetConversationHistoryInput,
    HerInitiateChatInput,
)
from .helpers import (
    ensure_her_in_path,
    run_async,
    get_current_user_id,
    get_db_user,
)

logger = logging.getLogger(__name__)


# ==================== Her Get User Tool ====================

class HerGetUserTool(BaseTool):
    """
    Her 用户画像查询工具 - 纯数据查询

    【Agent Native 设计】
    返回用户的完整画像数据，不做任何解读。
    Agent 根据返回数据自主分析用户特点。
    """

    name: str = "her_get_user"
    description: str = """
获取用户画像数据。返回用户的完整资料信息。

此工具只返回原始数据，不做解读。Agent 需要根据数据自主分析用户特点。

参数：
- user_id: 用户 ID（可选，默认使用当前用户）

返回：{ user_profile: {...} }

Agent 应该：
- 根据用户的兴趣、性格等数据，理解用户的特点
- 用于话题推荐、开场白生成、约会策划等场景
"""
    args_schema: Type[BaseModel] = HerGetUserInput

    def _run(self, user_id: str) -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, user_id: str) -> ToolResult:
        """返回用户画像数据"""
        user = get_db_user(user_id)

        if not user:
            return ToolResult(
                success=False,
                error="用户不存在",
                summary="无法获取用户信息"
            )

        return ToolResult(
            success=True,
            data={"user_profile": user},
            summary=f"获取用户 {user.get('name', user_id)} 的画像"
        )


# ==================== Her Get Target User Tool ====================

class HerGetTargetUserTool(BaseTool):
    """
    Her 目标用户画像查询工具 - 纯数据查询

    【Agent Native 设计】
    返回目标用户的完整画像数据，不做任何解读。
    Agent 根据返回数据自主分析目标用户特点，找到匹配点。
    """

    name: str = "her_get_target_user"
    description: str = """
【触发条件】用户说"介绍一下TA"、"TA是谁"、"TA的详情"、"TA怎么样"、"看看王芳的详情"时调用。

【禁止场景】
- 用户说"聊什么"、"怎么开场"时 → 调用 her_get_icebreaker（不是本工具）
- 用户说"找对象"时 → 调用 her_find_matches（不是本工具）

【参数】target_user_id: 目标用户 ID（如果只有名字，先调用 her_find_user_by_name 获取 ID）

【返回】目标用户完整画像 JSON（年龄、职业、兴趣等）。
"""
    args_schema: Type[BaseModel] = HerGetTargetUserInput

    def _run(self, target_user_id: str) -> str:
        try:
            result = run_async(self._arun(target_user_id))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, target_user_id: str) -> ToolResult:
        """返回目标用户画像数据 + 自动构建 UserProfileCard"""
        target_user = get_db_user(target_user_id)

        if not target_user:
            return ToolResult(
                success=False,
                error="目标用户不存在",
                summary="无法获取目标用户信息"
            )

        # 🔧 [修复] 使用 selected_user 字段名，触发 UserProfileCard 自动构建
        # build_generative_ui_from_tool_result 会检测 selected_user 并生成可点击的卡片
        user_id = target_user.get("user_id") or target_user.get("id") or target_user_id

        return ToolResult(
            success=True,
            data={
                "selected_user": target_user,  # 🔧 [关键] 使用 selected_user 触发 UserProfileCard
                "user_profile": target_user,   # 同时设置 user_profile 作为备用
            },
            summary=f"获取目标用户 {target_user.get('name', target_user_id)} 的画像"
        )


# ==================== Her Get Conversation History Tool ====================

class HerGetConversationHistoryTool(BaseTool):
    """
    Her 对话历史查询工具 - 纯数据查询

    【Agent Native 设计】
    返回用户和匹配对象的对话历史，不做任何解读。
    Agent 根据对话历史自主分析：已聊话题、沉默状态、回复模式等。
    """

    name: str = "her_get_conversation_history"
    description: str = """
获取对话历史记录。返回用户和匹配对象的对话历史。

此工具只返回原始数据，不做解读。Agent 需要根据对话历史自主分析。

参数：
- user_id: 用户 ID（可选，默认使用当前用户）
- match_id: 匹配对象 ID
- limit: 返回消息数量（默认 20）

返回：{ messages: [...], total: N, silence_info: {...} }

Agent 应该：
- 分析已聊过的话题，避免推荐重复话题
- 分析对话频率，判断沉默时长
- 分析回复模式，判断对方意向
"""
    args_schema: Type[BaseModel] = HerGetConversationHistoryInput

    def _run(self, user_id: str, match_id: str, limit: int = 20) -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id, match_id, limit))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, user_id: str, match_id: str, limit: int = 20) -> ToolResult:
        """返回对话历史数据"""
        ensure_her_in_path()
        try:
            from utils.db_session_manager import db_session
            from db.models import MessageDB

            with db_session() as db:
                messages = db.query(MessageDB).filter(
                    ((MessageDB.sender_id == user_id) & (MessageDB.receiver_id == match_id)) |
                    ((MessageDB.sender_id == match_id) & (MessageDB.receiver_id == user_id))
                ).order_by(MessageDB.created_at.desc()).limit(limit).all()

                message_list = [
                    {
                        "content": m.content,
                        "sender_id": m.sender_id,
                        "is_from_user": m.sender_id == user_id,
                        "created_at": str(m.created_at),
                    }
                    for m in messages
                ]

                # 计算沉默信息（Agent 自己解读）
                silence_info = {}
                if messages:
                    last_message = messages[0]
                    last_time = last_message.created_at
                    if isinstance(last_time, str):
                        last_time = datetime.fromisoformat(last_time.replace('Z', '+00:00'))
                    silence_seconds = (datetime.now() - last_time.replace(tzinfo=None)).total_seconds()
                    silence_info = {
                        "last_message_time": str(last_message.created_at),
                        "silence_seconds": int(silence_seconds),
                        "last_sender": last_message.sender_id,
                        "hint": "Agent 应根据沉默时长判断是否需要打破沉默",
                    }

                return ToolResult(
                    success=True,
                    data={
                        "messages": message_list,
                        "total": len(message_list),
                        "silence_info": silence_info,
                    },
                    summary=f"获取 {len(message_list)} 条对话记录"
                )
        except Exception as e:
            logger.warning(f"[her_get_conversation_history] 查询失败: {e}")
            return ToolResult(
                success=True,
                data={"messages": [], "total": 0, "silence_info": {}},
                summary="暂无对话历史"
            )


# ==================== Her Initiate Chat Tool ====================

class HerInitiateChatTool(BaseTool):
    """
    Her 发起聊天工具 - 纯数据查询

    【Agent Native 设计】
    返回目标用户的基本信息，用于生成 ChatInitiationCard。
    Agent 根据上下文（如匹配度分析结果）组织回复。

    触发场景：
    - 用户说 "联系他"、"怎么联系他"、"发起聊天"、"能帮我发起聊天吗"
    - 注意：不要触发 her_get_icebreaker（那是推荐开场白话题）
    """

    name: str = "her_initiate_chat"
    description: str = """
【触发条件】用户说"联系他"、"怎么联系他"、"发起聊天"、"能帮我发起聊天吗"时调用。

【禁止场景】用户说"聊什么"、"怎么开场"、"破冰"时 → 调用 her_get_icebreaker（不是本工具）。

【参数】
- target_user_id: 目标用户 ID
- context: 上下文（可选）

【返回】目标用户基本信息，用于显示"发起聊天"按钮。
"""
    args_schema: Type[BaseModel] = HerInitiateChatInput

    def _run(self, target_user_id: str, context: str = "", compatibility_score: int = 0) -> str:
        try:
            result = run_async(self._arun(target_user_id, context, compatibility_score))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, target_user_id: str, context: str = "", compatibility_score: int = 0) -> ToolResult:
        """返回目标用户信息，用于发起聊天卡片"""
        target_user = get_db_user(target_user_id)

        if not target_user:
            return ToolResult(
                success=False,
                error="目标用户不存在",
                summary="无法获取目标用户信息"
            )

        # 返回精简的用户信息，用于 ChatInitiationCard
        return ToolResult(
            success=True,
            data={
                "target_user_id": target_user_id,
                "target_user_name": target_user.get("name", "TA"),
                "target_user_avatar": target_user.get("avatar_url", ""),
                "context": context,
                "compatibility_score": compatibility_score,
            },
            summary=f"准备发起聊天：{target_user.get('name', target_user_id)}"
        )


# ==================== Exports ====================

__all__ = [
    "HerGetUserTool",
    "HerGetTargetUserTool",
    "HerGetConversationHistoryTool",
    "HerInitiateChatTool",
]

# Tool instances for registration
her_get_user_tool = HerGetUserTool()
her_get_target_user_tool = HerGetTargetUserTool()
her_get_conversation_history_tool = HerGetConversationHistoryTool()
her_initiate_chat_tool = HerInitiateChatTool()