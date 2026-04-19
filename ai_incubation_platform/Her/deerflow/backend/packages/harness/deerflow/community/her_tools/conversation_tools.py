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
    Her 话题推荐工具 - 纯数据查询（Agent Native 设计）

    只返回原始数据，Agent 自行生成个性化话题。
    """

    name: str = "her_suggest_topics"
    description: str = """
获取聊天话题推荐所需的用户画像数据。

【能力】
返回双方兴趣、对话历史等原始数据，供你自主生成话题建议。

【参数】
- user_id: 用户 ID（可选）
- match_id: 匹配对象 ID（可选）

【返回】
- user_profile: 用户画像
- target_profile: 目标用户画像
- analysis: 共同兴趣、独特兴趣分析
- conversation_history: 已聊话题（避免重复）

【使用场景】
当用户想获取聊天话题、说什么时调用此工具。

【注意】
此工具只返回原始数据，你需要根据数据自主生成话题建议。
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
            "component_type": "ConversationGuideCard",
            "intent_type": "topic_request",
            "user_profile": {
                "interests": user.get("interests", []),
                "location": user.get("location", ""),
                "age": user.get("age", 0),
                "bio": user.get("bio", ""),
            },
            "target_profile": target_user if target_user else None,
            "selected_user": target_user if target_user else None,
            "conversation_history": conversation_history,
            "analysis": {
                "common_interests": common_interests,
                "unique_user_interests": unique_user_interests,
                "unique_target_interests": unique_target_interests,
                "history_count": len(conversation_history),
            },
        }

        return ToolResult(
            success=True,
            data=result_data
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
    Her 破冰建议工具 - 纯数据查询（Agent Native 设计）

    只返回原始数据，Agent 自行生成个性化开场白。
    """

    name: str = "her_get_icebreaker"
    description: str = """
获取破冰开场白所需的匹配点数据。

【能力】
返回双方共同兴趣、地点匹配等原始数据，供你自主生成开场白建议。

【参数】
- user_id: 用户 ID（可选）
- match_id: 目标用户 ID（可选）

【返回】
- user_profile: 用户画像
- target_profile: 目标用户画像
- match_points: 匹配点分析（共同兴趣、同城等）

【使用场景】
当用户想获取开场白建议、怎么破冰时调用此工具。

【注意】
此工具只返回原始数据，你需要根据匹配点自主生成个性化开场白，避免"Hi你好"等通用模板。
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
                }
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
            })
        if same_location:
            match_points.append({
                "type": "location",
                "content": user.get("location"),
            })

        # 目标用户独特特点
        unique_target_interests = list(target_interests - user_interests)
        if unique_target_interests:
            match_points.append({
                "type": "target_unique",
                "content": unique_target_interests,
            })

        result_data = {
            "component_type": "ConversationGuideCard",
            "intent_type": "icebreaker_request",
            "user_profile": {
                "interests": user.get("interests", []),
                "location": user.get("location", ""),
                "bio": user.get("bio", ""),
            },
            "target_profile": {
                "user_id": match_id,
                "name": target_user.get("name", target_name),
                "interests": target_user.get("interests", []),
                "location": target_user.get("location", ""),
                "bio": target_user.get("bio", ""),
                "age": target_user.get("age", 0),
            },
            "selected_user": {
                "user_id": match_id,
                "name": target_user.get("name", target_name),
                "interests": target_user.get("interests", []),
                "location": target_user.get("location", ""),
                "bio": target_user.get("bio", ""),
                "age": target_user.get("age", 0),
            },
            "match_points": match_points,
        }

        return ToolResult(
            success=True,
            data=result_data
        )


# ==================== Her Plan Date Tool ====================

class HerPlanDateTool(BaseTool):
    """
    Her 约会策划工具 - 纯数据查询（Agent Native 设计）

    只返回原始数据，Agent 自行生成约会方案。
    """

    name: str = "her_plan_date"
    description: str = """
获取约会策划所需的用户画像和活动数据。

【能力】
返回双方兴趣、地点、活动类型等原始数据，供你自主生成约会方案。

【参数】
- user_id: 用户 ID（可选）
- match_id: 约会对象 ID（可选）
- location: 约会地点范围（可选）

【返回】
- user_profile: 用户画像（兴趣、消费偏好等）
- target_profile: 目标用户画像
- date_context: 约会地点、共同兴趣
- activity_options: 活动类型参考

【使用场景】
当用户想获取约会地点、见面方案时调用此工具。

【注意】
此工具只返回原始数据，你需要自主生成具体约会方案，给出具体的地点和安排。
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
        }

        return ToolResult(
            success=True,
            data=result_data
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