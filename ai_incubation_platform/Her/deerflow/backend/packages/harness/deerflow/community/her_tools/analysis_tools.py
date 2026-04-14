"""
Her Tools - Analysis Tools Module

分析相关工具：兼容性分析、关系分析
"""
import logging
import json
from typing import Type

from langchain.tools import BaseTool
from pydantic import BaseModel

from .schemas import (
    ToolResult,
    HerAnalyzeCompatibilityInput,
    HerAnalyzeRelationshipInput,
)
from .helpers import (
    ensure_her_in_path,
    run_async,
    get_current_user_id,
    get_db_user,
)

logger = logging.getLogger(__name__)


# ==================== Her Analyze Compatibility Tool ====================

class HerAnalyzeCompatibilityTool(BaseTool):
    """Her 兼容性分析工具 - 查询用户画像对比"""

    name: str = "her_analyze_compatibility"
    description: str = """
分析两个用户的兼容性。查询双方画像数据。

参数：user_id（可选）, target_user_id
返回：{ user_a: {...}, user_b: {...}, comparison_factors: [...] }
"""
    args_schema: Type[BaseModel] = HerAnalyzeCompatibilityInput

    def _run(self, user_id: str, target_user_id: str) -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id, target_user_id))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, user_id: str, target_user_id: str) -> ToolResult:
        """查询双方画像"""
        user_a = get_db_user(user_id)
        user_b = get_db_user(target_user_id)

        if not user_a or not user_b:
            return ToolResult(success=False, error="用户不存在", summary="查询失败")

        # 简单的对比因素（让 Agent 自己解读）
        comparison_factors = []

        # 年龄差距
        if user_a.get("age") and user_b.get("age"):
            age_diff = abs(user_a["age"] - user_b["age"])
            comparison_factors.append({
                "factor": "年龄差距",
                "value": f"{age_diff}岁",
                "user_a": user_a["age"],
                "user_b": user_b["age"],
            })

        # 地点
        comparison_factors.append({
            "factor": "所在地",
            "user_a": user_a.get("location", "未知"),
            "user_b": user_b.get("location", "未知"),
            "same_city": user_a.get("location") == user_b.get("location"),
        })

        # 共同兴趣
        interests_a = set(user_a.get("interests", []))
        interests_b = set(user_b.get("interests", []))
        common_interests = list(interests_a & interests_b)
        comparison_factors.append({
            "factor": "兴趣爱好",
            "user_a": user_a.get("interests", []),
            "user_b": user_b.get("interests", []),
            "common": common_interests,
        })

        # 关系目标
        comparison_factors.append({
            "factor": "关系目标",
            "user_a": user_a.get("relationship_goal", "未设置"),
            "user_b": user_b.get("relationship_goal", "未设置"),
        })

        return ToolResult(
            success=True,
            data={
                "user_a": user_a,
                "user_b": user_b,
                "comparison_factors": comparison_factors,
            },
            summary=f"对比 {user_a.get('name')} 和 {user_b.get('name')} 的画像"
        )


# ==================== Her Analyze Relationship Tool ====================

class HerAnalyzeRelationshipTool(BaseTool):
    """Her 关系分析工具 - 查询关系数据"""

    name: str = "her_analyze_relationship"
    description: str = """
分析关系健康度。查询匹配记录和互动数据。

参数：user_id（可选）, match_id（对方用户 ID）
返回：{ match_info: {...}, interactions: [...] }
"""
    args_schema: Type[BaseModel] = HerAnalyzeRelationshipInput

    def _run(self, user_id: str, match_id: str) -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id, match_id))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, user_id: str, match_id: str) -> ToolResult:
        """查询关系数据"""
        user_a = get_db_user(user_id)
        user_b = get_db_user(match_id)

        if not user_a or not user_b:
            return ToolResult(success=False, error="用户不存在", summary="查询失败")

        # 查询匹配记录（如果有）
        ensure_her_in_path()
        from utils.db_session_manager import db_session
        try:
            from db.models import MatchDB
            with db_session() as db:
                match_record = db.query(MatchDB).filter(
                    (MatchDB.user_id_a == user_id) | (MatchDB.user_id_a == match_id),
                    (MatchDB.user_id_b == match_id) | (MatchDB.user_id_b == user_id),
                ).first()

                match_info = {
                    "status": match_record.status if match_record else "pending",
                    "created_at": str(match_record.created_at) if match_record else None,
                    "compatibility_score": match_record.compatibility_score if match_record else 0.5,
                }
        except:
            match_info = {"status": "unknown", "compatibility_score": 0.5}

        return ToolResult(
            success=True,
            data={
                "user_a": user_a,
                "user_b": user_b,
                "match_info": match_info,
            },
            summary=f"分析 {user_a.get('name')} 和 {user_b.get('name')} 的关系"
        )


# ==================== Exports ====================

__all__ = [
    "HerAnalyzeCompatibilityTool",
    "HerAnalyzeRelationshipTool",
]

# Tool instances for registration
her_analyze_compatibility_tool = HerAnalyzeCompatibilityTool()
her_analyze_relationship_tool = HerAnalyzeRelationshipTool()