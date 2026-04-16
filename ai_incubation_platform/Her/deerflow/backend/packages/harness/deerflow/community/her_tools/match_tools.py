"""
Her Tools - Match Tools Module

匹配相关工具：查找匹配对象、每日推荐
"""
import logging
import json
import uuid
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
    normalize_user_interests_field,
    should_exclude_demo_candidate_name,
)

logger = logging.getLogger(__name__)
# 🔧 [P1性能优化] 减少扫描上限
# 原值 100 导致查询耗时 3-5 秒，减少到 30 可显著提升性能
# 30 位候选足够覆盖大部分匹配需求（用户通常选择前 5 位）
MAX_CANDIDATES_SCAN = 30


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
        # 未填写时：有偏好城市则默认「只找同城」，避免把异地候选混入列表（数据校验 / 契约默认值）
        if accept_remote is None:
            accept_remote = "只找同城" if preferred_location else "接受异地"

        user_gender = user_prefs.get("gender")
        user_relationship_goal = user_prefs.get("relationship_goal")

        logger.info(f"[her_find_matches] 用户偏好: age={preferred_age_min}-{preferred_age_max}, "
                    f"location={preferred_location}, accept_remote={accept_remote}, "
                    f"gender={user_gender}, goal={user_relationship_goal}")

        # ===== 第二步：构建基础查询条件（硬约束）=====
        matches: list = []
        candidates_scanned = 0
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

            # 关系目标筛选（硬约束：有值时尽量同目标）
            if user_relationship_goal:
                query = query.filter(UserDB.relationship_goal == user_relationship_goal)

            # ===== 第三步：执行查询 =====
            # 关键修复：不再使用 limit*3 采样，先取完整候选池（带安全上限）再按偏好分层求解。
            candidates = query.order_by(UserDB.created_at.desc()).limit(MAX_CANDIDATES_SCAN).all()
            candidates_scanned = len(candidates)

            # ===== 第四步：地点筛选（分两轮）=====
            same_city_matches = []
            remote_matches = []

            for u in candidates:
                if should_exclude_demo_candidate_name(getattr(u, "name", None)):
                    continue
                interests = normalize_user_interests_field(getattr(u, "interests", None))[:5]

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

            # ===== 第五步：严格按用户约束组合结果（不自动放宽）=====
            relaxation_trace = []
            if accept_remote == "只找同城":
                matches = same_city_matches[:limit]
                if len(matches) < limit and len(remote_matches) > 0:
                    relaxation_trace.append({
                        "step": "strict_same_city_only",
                        "changed_constraint": None,
                        "reason": "用户设置为只找同城，未自动放宽异地条件",
                        "same_city_available": len(same_city_matches),
                        "remote_available": len(remote_matches),
                    })
            elif accept_remote == "接受异地":
                # 这是用户显式约束：可异地，不属于自动放宽
                matches = same_city_matches + remote_matches[:limit - len(same_city_matches)]
            else:
                # 同城优先：这是用户显式约束，允许异地补充
                matches = same_city_matches[:limit]
                if len(matches) < limit:
                    need_remote = limit - len(matches)
                    matches.extend(remote_matches[: limit - len(matches)])

            # 查无结果时，仅提供放宽建议，不自动调整
            relaxation_suggestions = []
            if len(matches) == 0:
                if preferred_location and len(remote_matches) > 0 and accept_remote == "只找同城":
                    relaxation_suggestions.append({
                        "dimension": "accept_remote",
                        "current": accept_remote,
                        "suggestion": "同城优先",
                        "reason": f"当前同城命中 0，但异地有 {len(remote_matches)} 位候选",
                    })
                if candidates_scanned == 0:
                    relaxation_suggestions.append({
                        "dimension": "age_range",
                        "current": f"{preferred_age_min}-{preferred_age_max}",
                        "suggestion": "扩大年龄范围",
                        "reason": "当前年龄范围下无候选命中",
                    })
                if user_relationship_goal:
                    relaxation_suggestions.append({
                        "dimension": "relationship_goal",
                        "current": user_relationship_goal,
                        "suggestion": "放宽关系目标匹配",
                        "reason": "严格关系目标可能导致候选不足",
                    })

        query_request_id = str(uuid.uuid4())

        # ===== 第六步：返回结果 =====
        # 🔧 [关键] 添加 component_type，让 API 能构建 generative_ui
        result_data = {
            "component_type": "MatchCardList",  # 🔧 [新增] 指定 UI 类型
            "intent_type": "match_request",  # 🔧 [新增] 指定意图类型
            "matches": matches,
            "total": len(matches),
            "query_request_id": query_request_id,
            "matched_count": len(matches),
            "filter_applied": {
                "age_range": f"{preferred_age_min}-{preferred_age_max}",
                "preferred_location": preferred_location,
                "accept_remote": accept_remote,
                "same_city_count": len(same_city_matches),
                "remote_count": len(remote_matches),
                "candidates_scanned": candidates_scanned,
            },
            "satisfaction_report": {
                "hard_constraints": {
                    "age_range": True,
                    "gender": True if user_gender else False,
                    "relationship_goal": True if user_relationship_goal else False,
                },
                "soft_constraints": {
                    "preferred_location": len(same_city_matches) > 0 if preferred_location else None,
                },
                "selected_breakdown": {
                    "same_city_selected": len([m for m in matches if preferred_location and m.get("location") and (preferred_location == m.get("location") or preferred_location in m.get("location") or m.get("location") in preferred_location)]),
                    "remote_selected": len(matches) - len([m for m in matches if preferred_location and m.get("location") and (preferred_location == m.get("location") or preferred_location in m.get("location") or m.get("location") in preferred_location)]),
                },
            },
            "relaxation_trace": relaxation_trace,
            "relaxation_suggestions": relaxation_suggestions if 'relaxation_suggestions' in locals() else [],
            "user_preferences": {
                "preferred_age_min": preferred_age_min,
                "preferred_age_max": preferred_age_max,
                "preferred_location": preferred_location,
                "accept_remote": accept_remote,
                "relationship_goal": user_relationship_goal,
            }
        }

        # 🔧 [根治] 使用 instruction + output_hint
        instruction = f"找到 {len(matches)} 位候选对象，请向用户展示匹配结果。"
        output_hint = f"为你找到 {len(matches)} 位合适的候选人~"
        if accept_remote != "只找同城" and len(same_city_matches) == 0 and len(remote_matches) > 0:
            output_hint += "（均为异地，请确认是否接受）"

        return ToolResult(
            success=True,
            data=result_data,
            instruction=instruction,
            output_hint=output_hint,
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
                UserDB.is_permanently_banned == False,
            ).order_by(UserDB.last_login.desc() if hasattr(UserDB, 'last_login') else UserDB.created_at.desc())

            users = query.limit(12).all()

            for u in users:
                if should_exclude_demo_candidate_name(getattr(u, "name", None)):
                    continue
                recommendations.append({
                    "user_id": u.id,
                    "name": u.name or "匿名",
                    "age": u.age or 0,
                    "location": u.location or "",
                    "interests": normalize_user_interests_field(getattr(u, "interests", None))[:3],
                })
                if len(recommendations) >= 3:
                    break

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