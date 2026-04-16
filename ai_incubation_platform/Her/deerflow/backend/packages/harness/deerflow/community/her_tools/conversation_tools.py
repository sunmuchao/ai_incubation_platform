"""
Her Tools - Conversation Tools Module

对话相关工具：话题推荐、破冰建议、约会策划
"""
import logging
import json
from typing import Type, List, Dict

from langchain.tools import BaseTool
from pydantic import BaseModel

from .schemas import (
    ToolResult,
    HerSuggestTopicsInput,
    HerGetIcebreakerInput,
    HerPlanDateInput,
)
from .helpers import (
    ensure_her_in_path,
    run_async,
    get_current_user_id,
    get_db_user,
)

logger = logging.getLogger(__name__)


# ==================== Her Suggest Topics Tool ====================

class HerSuggestTopicsTool(BaseTool):
    """
    Her 话题推荐工具 - 纯数据查询

    【Agent Native 设计】
    此工具只返回原始数据，不生成话题模板。
    Agent（LLM）根据返回的用户画像自主生成个性化话题。
    """

    name: str = "her_suggest_topics"
    description: str = """
【触发条件】用户说"话题"、"说什么"、"有什么可以聊"、"聊天内容"时调用。

【禁止场景】用户说"介绍某人的详情"时 → 调用 her_get_target_user（不是本工具）。

【参数】
- user_id: 用户 ID（可选）
- match_id: 匹配对象 ID（可选）

【返回】双方画像和已聊话题 JSON，Agent 根据此生成新话题。
"""
    args_schema: Type[BaseModel] = HerSuggestTopicsInput

    def _run(self, user_id: str, match_id: str = "", context: str = "") -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id, match_id, context))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, user_id: str, match_id: str = "", context: str = "") -> ToolResult:
        """返回用户画像数据（不生成话题模板）"""
        user = get_db_user(user_id) or {}
        target_user = get_db_user(match_id) if match_id else None

        # 获取对话历史（已聊话题）
        conversation_history = []
        if match_id:
            conversation_history = await self._get_conversation_history(user_id, match_id)

        # 分析共同兴趣
        user_interests = set(user.get("interests", []))
        target_interests = set(target_user.get("interests", []) if target_user else [])
        common_interests = list(user_interests & target_interests)

        # 分析兴趣差异
        unique_user_interests = list(user_interests - target_interests)
        unique_target_interests = list(target_interests - user_interests)

        result_data = {
            "user_profile": {
                "interests": user.get("interests", []),
                "location": user.get("location", ""),
                "age": user.get("age", 0),
                "bio": user.get("bio", ""),
            },
            "target_profile": target_user if target_user else None,
            "conversation_history": conversation_history,
            "analysis": {
                "common_interests": common_interests,
                "unique_user_interests": unique_user_interests,
                "unique_target_interests": unique_target_interests,
                "history_count": len(conversation_history),
            },
            "hint": "Agent 应根据数据自主生成话题，考虑：共同点、关系阶段、避免重复",
        }

        return ToolResult(
            success=True,
            data=result_data,
            summary=f"用户有 {len(user_interests)} 个兴趣，共同兴趣 {len(common_interests)} 个"
        )

    async def _get_conversation_history(self, user_id: str, match_id: str) -> List[Dict]:
        """获取对话历史（已聊话题）"""
        ensure_her_in_path()
        try:
            from utils.db_session_manager import db_session
            from db.models import MessageDB

            with db_session() as db:
                messages = db.query(MessageDB).filter(
                    ((MessageDB.sender_id == user_id) & (MessageDB.receiver_id == match_id)) |
                    ((MessageDB.sender_id == match_id) & (MessageDB.receiver_id == user_id))
                ).order_by(MessageDB.created_at.desc()).limit(20).all()

                return [
                    {
                        "content": m.content,
                        "sender": m.sender_id,
                        "created_at": str(m.created_at),
                    }
                    for m in messages
                ]
        except Exception as e:
            logger.warning(f"[her_suggest_topics] 获取对话历史失败: {e}")
            return []


# ==================== Her Get Icebreaker Tool ====================

class HerGetIcebreakerTool(BaseTool):
    """
    Her 破冰建议工具 - 纯数据查询

    【Agent Native 设计】
    此工具只返回原始数据，不生成破冰模板。
    Agent（LLM）根据返回的用户画像自主生成个性化开场白。
    """

    name: str = "her_get_icebreaker"
    description: str = """
【触发条件】用户说"聊什么"、"怎么开场"、"破冰"、"怎么开口"、"我和匹配的对象聊什么"时调用。

【禁止场景】
- 用户说"介绍某人的详情"时 → 调用 her_get_target_user（不是本工具）
- 用户说"联系他"时 → 调用 her_initiate_chat（不是本工具）

【参数】
- user_id: 用户 ID（可选）
- match_id: 目标用户 ID（可选，如果缺失，Agent 应先调用 her_find_matches 获取最近匹配）

【返回】双方画像和匹配点 JSON，Agent 根据此生成个性化开场白。
"""
    args_schema: Type[BaseModel] = HerGetIcebreakerInput

    def _run(self, user_id: str, match_id: str = "", target_name: str = "TA") -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id, match_id, target_name))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, user_id: str, match_id: str = "", target_name: str = "TA") -> ToolResult:
        """返回用户画像数据（不生成破冰模板）"""
        user = get_db_user(user_id) or {}
        target_user = get_db_user(match_id) if match_id else None

        if not target_user:
            return ToolResult(
                success=True,
                data={
                    "user_profile": user,
                    "target_profile": None,
                    "match_points": [],
                    "hint": "缺少目标用户信息，Agent 可以询问用户想和谁破冰",
                },
                summary="缺少目标用户信息"
            )

        # 分析匹配点
        user_interests = set(user.get("interests", []))
        target_interests = set(target_user.get("interests", []))
        common_interests = list(user_interests & target_interests)

        # 地点匹配
        same_location = user.get("location") == target_user.get("location")

        # 构建匹配点列表
        match_points = []
        if common_interests:
            match_points.append({
                "type": "interest",
                "content": common_interests,
                "hint": "可以围绕共同兴趣开场",
            })
        if same_location:
            match_points.append({
                "type": "location",
                "content": user.get("location"),
                "hint": "可以围绕同城开场",
            })

        # 目标用户独特特点
        unique_target_interests = list(target_interests - user_interests)
        if unique_target_interests:
            match_points.append({
                "type": "target_unique",
                "content": unique_target_interests,
                "hint": "可以围绕对方的独特兴趣开场（显示你看了对方资料）",
            })

        result_data = {
            "user_profile": {
                "interests": user.get("interests", []),
                "location": user.get("location", ""),
                "bio": user.get("bio", ""),
            },
            "target_profile": {
                "name": target_user.get("name", target_name),
                "interests": target_user.get("interests", []),
                "location": target_user.get("location", ""),
                "bio": target_user.get("bio", ""),
                "age": target_user.get("age", 0),
            },
            "match_points": match_points,
            "hint": "Agent 应根据匹配点创造个性化开场白，避免'Hi你好'等通用模板",
        }

        return ToolResult(
            success=True,
            data=result_data,
            summary=f"目标用户 {target_user.get('name', target_name)} 有 {len(target_interests)} 个兴趣，共同兴趣 {len(common_interests)} 个"
        )


# ==================== Her Plan Date Tool ====================

class HerPlanDateTool(BaseTool):
    """
    Her 约会策划工具 - 纯数据查询

    【Agent Native 设计】
    此工具只返回原始数据，不生成约会模板。
    Agent（LLM）根据返回的用户画像和地点信息自主生成约会方案。
    """

    name: str = "her_plan_date"
    description: str = """
【触发条件】用户说"约会去哪"、"见面地点"、"约会方案"、"约会推荐"时调用。

【参数】
- user_id: 用户 ID（可选）
- match_id: 约会对象 ID（可选）
- location: 约会地点范围（可选）

【返回】双方画像和活动选项 JSON，Agent 根据此生成具体约会方案。
"""
    args_schema: Type[BaseModel] = HerPlanDateInput

    def _run(self, user_id: str, match_id: str = "", target_name: str = "TA", location: str = "", preferences: str = "") -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id, match_id, target_name, location, preferences))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, user_id: str, match_id: str = "", target_name: str = "TA", location: str = "", preferences: str = "") -> ToolResult:
        """返回用户画像数据（不生成约会模板）"""
        user = get_db_user(user_id) or {}
        target_user = get_db_user(match_id) if match_id else None

        # 分析共同兴趣
        user_interests = set(user.get("interests", []))
        target_interests = set(target_user.get("interests", []) if target_user else [])
        common_interests = list(user_interests & target_interests)

        # 地点信息
        user_location = user.get("location", "")
        target_location = target_user.get("location", "") if target_user else ""
        date_location = location or user_location or target_location

        # 常见约会活动类型（供 Agent 参考）
        activity_categories = {
            "美食": ["餐厅", "咖啡厅", "甜品店", "酒吧"],
            "娱乐": ["电影院", "演出", "展览", "游乐园"],
            "运动": ["健身房", "攀岩", "保龄球", "户外徒步"],
            "文化": ["书店", "博物馆", "图书馆", "艺术展"],
            "自然": ["公园", "植物园", "海滩", "山景"],
            "休闲": ["SPA", "按摩", "茶馆", "棋牌"],
        }

        # 根据共同兴趣筛选可能的活动类型
        relevant_categories = []
        for interest in common_interests:
            if interest in activity_categories:
                relevant_categories.append({
                    "interest": interest,
                    "activities": activity_categories[interest],
                })

        if not relevant_categories:
            relevant_categories = [
                {"interest": cat, "activities": activities}
                for cat, activities in activity_categories.items()
            ]

        result_data = {
            "user_profile": {
                "interests": user.get("interests", []),
                "location": user_location,
                "spending_style": user.get("spending_style", ""),
            },
            "target_profile": target_user if target_user else None,
            "date_context": {
                "location": date_location,
                "common_interests": common_interests,
                "user_preferences": preferences,
            },
            "activity_options": relevant_categories,
            "hint": "Agent 应根据数据创造具体约会方案，避免'附近咖啡厅'等模糊建议，给出具体的地点和安排",
        }

        return ToolResult(
            success=True,
            data=result_data,
            summary=f"双方共同兴趣 {len(common_interests)} 个，约会地点范围 {date_location}"
        )


# ==================== Exports ====================

__all__ = [
    "HerSuggestTopicsTool",
    "HerGetIcebreakerTool",
    "HerPlanDateTool",
]

# Tool instances for registration
her_suggest_topics_tool = HerSuggestTopicsTool()
her_get_icebreaker_tool = HerGetIcebreakerTool()
her_plan_date_tool = HerPlanDateTool()