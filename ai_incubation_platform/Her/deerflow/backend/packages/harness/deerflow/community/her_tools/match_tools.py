"""
Her Tools - Match Tools Module

匹配相关工具：查找匹配对象、每日推荐
"""
import logging
import json
from typing import Type

from langchain.tools import BaseTool
from pydantic import BaseModel

from .schemas import (
    ToolResult,
    HerFindMatchesInput,
    HerDailyRecommendInput,
)
from .helpers import (
    ensure_her_in_path,
    run_async,
    get_current_user_id,
    get_db_user,
    get_user_confidence,
)

logger = logging.getLogger(__name__)


# ==================== Her Find Matches Tool ====================

class HerFindMatchesTool(BaseTool):
    """Her 匹配工具 - 直接查询数据库"""

    name: str = "her_find_matches"
    description: str = """
【触发条件】用户说"找对象"、"推荐"、"相亲"、"匹配"、"给我找人"时调用。

【禁止场景】用户说"介绍某人的详情"、"TA是谁"、"TA怎么样"时 → 调用 her_get_target_user（不是本工具）。

【参数】
- user_id: 用户 ID（可选，默认当前用户）
- limit: 返回数量（默认 5）

【返回】候选用户列表 JSON。
"""
    args_schema: Type[BaseModel] = HerFindMatchesInput

    def _run(self, user_id: str, intent: str = "", limit: int = 5) -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id, intent, limit))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, user_id: str, intent: str = "", limit: int = 5) -> ToolResult:
        """
        查询数据库匹配对象，使用用户偏好进行筛选

        筛选逻辑：
        1. 年龄范围：preferred_age_min ~ preferred_age_max
        2. 地点：preferred_location（同城优先）
        3. 异地：accept_remote（是否接受异地）
        4. 性别：异性
        5. 关系目标：匹配
        """
        ensure_her_in_path()
        from utils.db_session_manager import db_session
        from db.models import UserDB

        # ===== 第一步：获取用户偏好 =====
        user_prefs = get_db_user(user_id)
        if not user_prefs:
            return ToolResult(
                success=False,
                error="用户不存在",
                summary="无法获取用户信息"
            )

        # 提取关键偏好
        preferred_age_min = user_prefs.get("preferred_age_min") or 18
        preferred_age_max = user_prefs.get("preferred_age_max") or 60
        preferred_location = user_prefs.get("preferred_location") or user_prefs.get("location")

        # 🔧 [修复] accept_remote 值映射：英文 -> 中文
        # 数据库可能存储英文值（no/yes/conditional）或中文值
        raw_accept_remote = user_prefs.get("accept_remote")
        accept_remote_mapping = {
            "no": "只找同城",
            "yes": "接受异地",
            "conditional": "同城优先",  # 可接受异地，但优先同城
            "只找同城": "只找同城",
            "接受异地": "接受异地",
            "同城优先": "同城优先",
        }
        accept_remote = accept_remote_mapping.get(raw_accept_remote, raw_accept_remote) if raw_accept_remote else None

        user_gender = user_prefs.get("gender")
        user_relationship_goal = user_prefs.get("relationship_goal")

        logger.info(f"[her_find_matches] 用户偏好: age={preferred_age_min}-{preferred_age_max}, "
                    f"location={preferred_location}, accept_remote={accept_remote}, "
                    f"gender={user_gender}, goal={user_relationship_goal}")

        # ===== 第二步：构建查询条件 =====
        matches = []
        with db_session() as db:
            query = db.query(UserDB).filter(
                UserDB.id != user_id,
                UserDB.is_active == True,
                UserDB.is_permanently_banned == False
            )

            # 年龄范围筛选
            if preferred_age_min and preferred_age_max:
                query = query.filter(
                    UserDB.age >= preferred_age_min,
                    UserDB.age <= preferred_age_max
                )

            # 性别筛选（异性）
            if user_gender:
                opposite_gender = "female" if user_gender == "male" else "male"
                query = query.filter(UserDB.gender == opposite_gender)

            # ===== 第三步：执行查询 =====
            candidates = query.order_by(UserDB.created_at.desc()).limit(limit * 3).all()

            # ===== 第四步：地点筛选（分两轮）=====
            same_city_matches = []
            remote_matches = []

            for u in candidates:
                interests = u.interests.split(",")[:5] if u.interests else []

                # ===== 获取置信度信息 =====
                confidence_info = get_user_confidence(u.id)

                match_data = {
                    "user_id": u.id,
                    "name": u.name or "匿名用户",
                    "age": u.age or 0,
                    "gender": u.gender or "",
                    "location": u.location or "",
                    "interests": interests,
                    "bio": u.bio or "",
                    "relationship_goal": getattr(u, 'relationship_goal', '') or "",
                    "want_children": getattr(u, 'want_children', None),
                    # ===== 置信度字段 =====
                    "confidence_level": confidence_info["confidence_level"],
                    "confidence_score": confidence_info["confidence_score"],
                    "confidence_icon": confidence_info["confidence_icon"],
                }

                # 判断是否同城
                is_same_city = False
                if preferred_location and u.location:
                    is_same_city = preferred_location == u.location or \
                                   preferred_location in u.location or \
                                   u.location in preferred_location

                if is_same_city:
                    same_city_matches.append(match_data)
                else:
                    remote_matches.append(match_data)

            # ===== 第五步：根据异地偏好组合结果 =====
            if accept_remote == "只找同城":
                matches = same_city_matches[:limit]
            elif accept_remote == "接受异地":
                matches = same_city_matches + remote_matches[:limit - len(same_city_matches)]
            else:
                matches = same_city_matches[:limit]
                if len(matches) < limit:
                    matches.extend(remote_matches[:limit - len(matches)])

            if len(matches) == 0 and len(remote_matches) > 0 and accept_remote != "只找同城":
                matches = remote_matches[:limit]

        # ===== 第六步：返回结果 =====
        # 🔧 [关键] 添加 component_type，让 API 能构建 generative_ui
        result_data = {
            "component_type": "MatchCardList",  # 🔧 [新增] 指定 UI 类型
            "matches": matches,
            "total": len(matches),
            "filter_applied": {
                "age_range": f"{preferred_age_min}-{preferred_age_max}",
                "preferred_location": preferred_location,
                "accept_remote": accept_remote,
                "same_city_count": len(same_city_matches),
                "remote_count": len(remote_matches),
            },
            "user_preferences": {
                "preferred_age_min": preferred_age_min,
                "preferred_age_max": preferred_age_max,
                "preferred_location": preferred_location,
                "accept_remote": accept_remote,
                "relationship_goal": user_relationship_goal,
            }
        }

        summary = f"找到 {len(matches)} 位候选对象"
        if len(same_city_matches) == 0 and len(remote_matches) > 0:
            summary += "（均为异地，请确认是否接受）"

        return ToolResult(
            success=True,
            data=result_data,
            summary=summary
        )


# ==================== Her Daily Recommend Tool ====================

class HerDailyRecommendTool(BaseTool):
    """Her 每日推荐工具 - 查询数据库"""

    name: str = "her_daily_recommend"
    description: str = """
【触发条件】用户说"每日推荐"、"今日推荐"、"每天推荐"时调用。

【禁止场景】用户说"找对象"时 → 调用 her_find_matches（不是本工具）。

【参数】user_id: 用户 ID（可选，默认当前用户）

【返回】今日活跃用户列表 JSON。
"""
    args_schema: Type[BaseModel] = HerDailyRecommendInput

    def _run(self, user_id: str) -> str:
        if user_id in ["current_user", "current", "user", "me", ""]:
            user_id = get_current_user_id()

        try:
            result = run_async(self._arun(user_id))
        except Exception as e:
            return json.dumps(ToolResult(success=False, error=str(e)).model_dump(), ensure_ascii=False)
        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, user_id: str) -> ToolResult:
        """查询数据库"""
        ensure_her_in_path()
        from utils.db_session_manager import db_session
        from db.models import UserDB

        recommendations = []
        with db_session() as db:
            query = db.query(UserDB).filter(
                UserDB.id != user_id,
                UserDB.is_active == True,
            ).order_by(UserDB.last_login.desc() if hasattr(UserDB, 'last_login') else UserDB.created_at.desc())

            users = query.limit(3).all()

            for u in users:
                recommendations.append({
                    "user_id": u.id,
                    "name": u.name or "匿名",
                    "age": u.age or 0,
                    "location": u.location or "",
                    "interests": u.interests.split(",")[:3] if u.interests else [],
                })

        return ToolResult(
            success=True,
            data={"recommendations": recommendations, "total": len(recommendations)},
            summary=f"今日精选 {len(recommendations)} 位"
        )


# ==================== Exports ====================

__all__ = [
    "HerFindMatchesTool",
    "HerDailyRecommendTool",
]

# Tool instances for registration
her_find_matches_tool = HerFindMatchesTool()
her_daily_recommend_tool = HerDailyRecommendTool()