"""
MatchExecutor - 匹配执行器

职责：
- 从数据库查询候选人池
- 让 AI 判断每个候选人的匹配度
- 返回排序后的匹配结果

性能优化（v2.0）：
- 批量获取候选人画像（消除 N+1 查询）
- 并行化 LLM 调用（asyncio.gather）
- 结果缓存复用

从 ConversationMatchService 提取的方法：
- _execute_matching
- _query_candidate_pool
- _get_compatible_goals
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import asyncio
import json

from utils.logger import logger
from utils.db_session_manager import db_session
from db.models import UserDB
from agent.tools.geo_tool import GeoService
from services.user_profile_service import get_user_profile_service
from services.her_advisor_service import HerAdvisorService
from services.profile_dataclasses import DesireProfile, SelfProfile


@dataclass
class MatchCandidate:
    """匹配候选人结果"""
    user_id: str
    score: float
    candidate_profile: Dict[str, Any]
    her_advice: Any = None


class MatchExecutor:
    """
    匹配执行器

    负责从数据库查询候选人并让 AI 判断匹配度

    性能优化：
    - 批量画像获取：避免 N+1 查询
    - 并行 LLM 调用：使用 asyncio.gather
    """

    def __init__(
        self,
        profile_service=None,
        her_advisor=None,
    ):
        self._profile_service = profile_service or get_user_profile_service()
        self._her_advisor = her_advisor or HerAdvisorService()

    def _extract_vector_highlights(self, profile_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成可直接展示的向量维度摘要，避免前端重复解析完整画像。
        """
        vector_dimensions = profile_dict.get("vector_dimensions", {}) or {}
        values = vector_dimensions.get("values", {}) or {}
        attachment = vector_dimensions.get("attachment", {}) or {}
        communication = vector_dimensions.get("communication", {}) or {}
        implicit = vector_dimensions.get("implicit", {}) or {}

        return {
            "relationship_goal": values.get("relationship_goal"),
            "want_children": values.get("want_children"),
            "spending_style": values.get("spending_style"),
            "attachment_style": attachment.get("primary_style") or profile_dict.get("emotional_needs", {}).get("attachment_style"),
            "conflict_style": communication.get("conflict_style"),
            "repair_willingness": communication.get("repair_willingness"),
            "implicit_preference_confidence": implicit.get("confidence"),
        }

    async def execute_matching(
        self,
        user_id: str,
        self_profile: SelfProfile,
        desire_profile: DesireProfile,
        extracted_conditions: Dict[str, Any],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        执行匹配 - AI 直接判断匹配度

        性能优化版本：
        1. 批量获取候选人画像（消除 N+1）
        2. 并行化 LLM 判断（asyncio.gather）
        """
        logger.info(f"[MatchExecutor] 执行匹配 for user {user_id}")

        # 从数据库查询候选人
        candidates = self._query_candidate_pool(
            user_id=user_id,
            self_profile=self_profile,
            desire_profile=desire_profile,
            extracted_conditions=extracted_conditions,
            limit=limit
        )

        if not candidates:
            logger.info(f"[MatchExecutor] 没有找到候选人")
            return []

        # 🔧 [性能优化] 批量获取所有候选人画像
        candidate_ids = [c.get("id") for c in candidates]
        profiles_map = await self._profile_service.get_profiles_batch(candidate_ids)

        # 🔧 [性能优化] 并行化 LLM 判断
        llm_tasks = []
        for candidate in candidates:
            candidate_id = candidate.get("id")
            candidate_profiles = profiles_map.get(candidate_id)

            if candidate_profiles:
                candidate_self, candidate_desire = candidate_profiles
            else:
                # 降级：使用默认画像
                candidate_self, candidate_desire = SelfProfile(), DesireProfile()

            # 创建 LLM 判断任务
            task = self._her_advisor.generate_match_advice(
                user_a_id=user_id,
                user_b_id=candidate_id,
                user_a_profile=(self_profile, desire_profile),
                user_b_profile=(candidate_self, candidate_desire),
                compatibility_score=0.5
            )
            # 🔧 [修复] 保留原始候选人数据，用于组装最终结果
            llm_tasks.append((candidate_id, candidate_self, task, candidate))

        # 并行执行所有 LLM 调用
        advice_results = await asyncio.gather(
            *[t[2] for t in llm_tasks],
            return_exceptions=True
        )

        # 组装结果
        matches = []
        for i, (candidate_id, candidate_self, _, original_candidate) in enumerate(llm_tasks):
            advice = advice_results[i]

            # 处理异常情况
            if isinstance(advice, Exception):
                logger.warning(f"[MatchExecutor] LLM 判断失败: {candidate_id}, error: {advice}")
                score = 0.5
                advice = None
            else:
                score = advice.compatibility_score if advice else 0.5

            # 🔧 [修复] 合并原始数据和画像数据
            profile_dict = candidate_self.to_dict()
            basic = profile_dict.get("basic", {})
            vector_highlights = self._extract_vector_highlights(profile_dict)
            # 用原始数据填充缺失的字段（name, bio, avatar_url 等）
            merged_profile = {
                **profile_dict,
                "name": original_candidate.get("name"),
                "age": original_candidate.get("age") or basic.get("age"),
                "gender": original_candidate.get("gender") or basic.get("gender"),
                "location": original_candidate.get("location") or basic.get("location"),
                "bio": original_candidate.get("bio"),
                "avatar_url": original_candidate.get("avatar_url"),
                "interests": original_candidate.get("interests") or basic.get("interests", []),
                "relationship_goal": original_candidate.get("relationship_goal") or basic.get("relationship_goal"),
                "vector_dimensions": profile_dict.get("vector_dimensions", {}),
                "vector_match_highlights": vector_highlights,
            }

            matches.append({
                "user_id": candidate_id,
                "score": score,
                "candidate_profile": merged_profile,
                "vector_match_highlights": vector_highlights,
                "her_advice": advice,
            })

        # 按匹配度排序
        matches.sort(key=lambda x: x["score"], reverse=True)

        logger.info(f"[MatchExecutor] AI 并行判断了 {len(matches)} 个候选人")
        return matches[:5]  # 返回前 5 个

    def _query_candidate_pool(
        self,
        user_id: str,
        self_profile: SelfProfile,
        desire_profile: DesireProfile,
        extracted_conditions: Dict[str, Any],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """从数据库查询候选人池"""
        candidates = []

        with db_session() as db:
            # 构建查询
            query = db.query(UserDB).filter(
                UserDB.id != user_id,
                UserDB.is_active == True,
                UserDB.is_permanently_banned == False
            )

            # 关系目标兼容性
            if self_profile.relationship_goal:
                compatible_goals = self._get_compatible_goals(self_profile.relationship_goal)
                query = query.filter(UserDB.relationship_goal.in_(compatible_goals))

            # 年龄范围
            age_range = extracted_conditions.get("age_range")
            if age_range:
                query = query.filter(
                    UserDB.age >= age_range[0],
                    UserDB.age <= age_range[1]
                )
            elif self_profile.age:
                query = query.filter(
                    UserDB.age >= max(18, self_profile.age - 5),
                    UserDB.age <= min(60, self_profile.age + 5)
                )

            # 地点筛选
            location = extracted_conditions.get("location")
            if location:
                query = query.filter(UserDB.location.contains(location))

            # 兴趣筛选（新增）
            # 用户指定兴趣时，优先匹配有相同兴趣的候选人
            interests = extracted_conditions.get("interests")
            if interests and isinstance(interests, list):
                # 使用 LIKE 查询匹配 JSON 数组中的兴趣
                # interests 存储格式为 ["户外运动", "徒步"]
                for interest in interests:
                    query = query.filter(UserDB.interests.contains(interest))

            # 按创建时间排序
            query = query.order_by(UserDB.created_at.desc())

            fetch_limit = max(limit * 12, 60)
            users = query.limit(fetch_limit).all()

            # 距离：API 可传 max_distance_km；未传但本人有常住地时默认约省内/邻近圈，避免只按注册时间取到很远的人
            max_km = extracted_conditions.get("max_distance_km")
            if max_km is None and (self_profile.location or "").strip():
                max_km = 350

            db_self = db.query(UserDB).filter(UserDB.id == user_id).first()
            anchor = ""
            if db_self and getattr(db_self, "location", None):
                anchor = (db_self.location or "").strip()
            elif (self_profile.location or "").strip():
                anchor = self_profile.location.strip()

            if max_km and anchor and users:
                filtered: List[UserDB] = []
                for u in users:
                    bl = (u.location or "").strip()
                    dist = GeoService.calculate_distance(anchor, bl) if bl else None
                    if dist is not None and dist <= float(max_km):
                        filtered.append(u)
                    elif dist is None and bl and (anchor in bl or bl in anchor):
                        filtered.append(u)
                if filtered:
                    users = filtered

            users = users[:limit]

            for u in users:
                candidates.append({
                    "id": u.id,
                    "name": u.name,
                    "age": u.age,
                    "gender": u.gender,
                    "location": u.location,
                    "bio": getattr(u, "bio", None) or "",
                    "avatar_url": getattr(u, "avatar_url", None),
                    "interests": u.interests,  # 新增：返回兴趣字段
                    "relationship_goal": u.relationship_goal,
                    "education": getattr(u, "education", None),
                    "occupation": getattr(u, "occupation", None),
                    "income": getattr(u, "income", None),
                    "self_profile_json": getattr(u, "self_profile_json", "{}") or "{}",
                    "desire_profile_json": getattr(u, "desire_profile_json", "{}") or "{}",
                })

        return candidates

    def _get_compatible_goals(self, goal: str) -> List[str]:
        """获取兼容的关系目标"""
        compatible_groups = {
            "serious": ["serious", "marriage"],
            "marriage": ["marriage", "serious"],
            "dating": ["dating", "casual", "serious"],
            "casual": ["casual", "dating"],
        }
        return compatible_groups.get(goal, [goal])


# 全局实例
_match_executor: Optional[MatchExecutor] = None


def get_match_executor() -> MatchExecutor:
    """获取匹配执行器单例"""
    global _match_executor
    if _match_executor is None:
        _match_executor = MatchExecutor()
        logger.info("MatchExecutor initialized")
    return _match_executor