"""
Her Tools - User Tools Module (精简版 v4.1)

用户数据相关工具：获取对话历史

【Agent Native 设计】
- 只返回原始数据，Agent 自行分析对话状态

【Anthropic 建议】
- 返回高信号信息（sender_name > sender_id）
- 错误提示给修正方向
- 截断提示给具体建议
"""
import logging
import json
from datetime import datetime
from typing import Type, List, Dict

from langchain.tools import BaseTool
from pydantic import BaseModel

from .schemas import (
    ToolResult,
    HerGetConversationHistoryInput,
)
from .helpers import (
    ensure_her_in_path,
    run_async,
    get_current_user_id,
    get_db_user,
)

logger = logging.getLogger(__name__)

# 默认消息数量上限（Agent 上下文保护）
DEFAULT_LIMIT = 20
MAX_LIMIT = 50


# ==================== Her Get Conversation History Tool ====================

class HerGetConversationHistoryTool(BaseTool):
    """
    Her 对话历史查询工具 - 获取对话记录（Agent Native 设计）

    只返回原始数据，Agent 自行分析对话状态、沉默情况等。
    """

    name: str = "her_get_conversation_history"
    description: str = """
获取对话历史记录。

【能力】
返回用户和匹配对象的对话历史原始数据。

【参数】
- user_id: 用户 ID（可选，默认当前用户）
- target_id: 对话对象 ID
- limit: 返回消息数量（默认 20，最大 50）

【返回】
- messages: 对话消息列表（content、sender_name、is_from_user、created_at）
- total: 消息总数
- silence_info: 沉默时间信息（silence_seconds、silence_hours、last_sender_name）

【使用场景】
- 分析对话状态
- 避免重复话题
- 了解沉默情况（多久没聊了？谁最后发的消息？）

【重要】
此工具只返回原始数据，你需要：
1. 自主分析已聊话题、沉默状态
2. 使用 sender_name 来标识发送者（不要用 sender_id）
"""
    args_schema: Type[BaseModel] = HerGetConversationHistoryInput

    def _run(self, user_id: str = "me", target_id: str = "", limit: int = 20) -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id, target_id, limit))
        except Exception as e:
            # Anthropic 建议：错误提示给修正方向
            error_msg = self._format_error(str(e), target_id, limit)
            return json.dumps(ToolResult(success=False, error=error_msg).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    def _format_error(self, error: str, target_id: str, limit: int) -> str:
        """格式化错误信息（Anthropic 建议：给修正方向）"""
        if not target_id:
            return """缺少对话对象 ID。

参数 target_id 未传入。

建议：
1. 如果你想查询与某个候选人的对话，请先调用 her_find_candidates 获取候选人列表
2. 从候选人中选择一位，获取其 user_id
3. 将该 user_id 作为 target_id 传入

示例：
- her_find_candidates() → 选择 candidate_001
- her_get_conversation_history(target_id='candidate_001 的 user_id')"""
        if limit > MAX_LIMIT:
            return f"""limit 参数超出上限。

传入的 limit: {limit}
最大允许值: {MAX_LIMIT}

建议：请减少 limit 值，避免占用过多上下文。

示例：her_get_conversation_history(target_id='xxx', limit=20)"""
        return error

    async def _arun(self, user_id: str, target_id: str, limit: int = 20) -> ToolResult:
        """返回对话历史数据"""
        # 参数校验
        if not target_id:
            return ToolResult(
                success=False,
                error=self._format_error("缺少 target_id", target_id, limit)
            )

        # Anthropic 建议：limit 上限保护
        actual_limit = min(limit, MAX_LIMIT)
        truncated = limit > MAX_LIMIT

        ensure_her_in_path()
        try:
            from utils.db_session_manager import db_session
            from db.models import MessageDB

            # Anthropic 建议：获取用户名（高信号信息）
            user_profile = get_db_user(user_id)
            target_profile = get_db_user(target_id)
            user_name = user_profile.get("name", "我") if user_profile else "我"
            target_name = target_profile.get("name", "TA") if target_profile else "TA"

            with db_session() as db:
                messages = db.query(MessageDB).filter(
                    ((MessageDB.sender_id == user_id) & (MessageDB.receiver_id == target_id)) |
                    ((MessageDB.sender_id == target_id) & (MessageDB.receiver_id == user_id))
                ).order_by(MessageDB.created_at.desc()).limit(actual_limit).all()

                # Anthropic 建议：使用 sender_name 代替 sender_id（高信号）
                message_list = [
                    {
                        "content": m.content,
                        "sender_name": user_name if m.sender_id == user_id else target_name,  # 语义化名称
                        "sender_id": m.sender_id,  # 保留 ID（用于后续操作）
                        "is_from_user": m.sender_id == user_id,
                        "created_at": str(m.created_at),
                    }
                    for m in messages
                ]

                # 计算沉默信息（Anthropic 建议：语义化时间）
                silence_info = {}
                if messages:
                    last_message = messages[0]
                    last_time = last_message.created_at
                    if isinstance(last_time, str):
                        last_time = datetime.fromisoformat(last_time.replace('Z', '+00:00'))
                    silence_seconds = (datetime.now() - last_time.replace(tzinfo=None)).total_seconds()

                    # 语义化时间（高信号）
                    silence_hours = silence_seconds / 3600
                    if silence_hours < 1:
                        silence_readable = f"{int(silence_seconds / 60)} 分钟"
                    elif silence_hours < 24:
                        silence_readable = f"{int(silence_hours)} 小时"
                    else:
                        silence_readable = f"{int(silence_hours / 24)} 天"

                    silence_info = {
                        "silence_seconds": int(silence_seconds),
                        "silence_hours": round(silence_hours, 1),
                        "silence_readable": silence_readable,  # 语义化时间
                        "last_sender_name": user_name if last_message.sender_id == user_id else target_name,
                        "last_message_time": str(last_message.created_at),
                    }

                result_data = {
                    "messages": message_list,
                    "total": len(message_list),
                    "silence_info": silence_info,
                    "user_name": user_name,
                    "target_name": target_name,
                }

                # Anthropic 建议：截断提示
                if truncated:
                    result_data["truncated"] = True
                    result_data["truncation_hint"] = f"""结果已截断（显示前 {actual_limit} 条）。

如需更多消息，请：
1. 分批查询（先看最近 20 条，再查询更早的消息）
2. 只关注关键对话内容（开头、结尾、重要话题）

建议：优先分析最近 10-20 条消息，了解对话状态。"""

                return ToolResult(
                    success=True,
                    data=result_data
                )
        except Exception as e:
            logger.warning(f"[her_get_conversation_history] 查询失败: {e}")
            return ToolResult(
                success=True,
                data={"messages": [], "total": 0, "silence_info": {}}
            )


# ==================== Exports ====================

__all__ = [
    "HerGetConversationHistoryTool",
]

# Tool instance for registration
her_get_conversation_history_tool = HerGetConversationHistoryTool()