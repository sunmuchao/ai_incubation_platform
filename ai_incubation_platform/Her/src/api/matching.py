"""
匹配 API 路由

Identity 优化：
- 集成缓存层（匹配结果缓存）
- 集成限流保护
- 优化数据库查询

架构说明：新架构使用 ConversationMatchService + HerAdvisorService (AI Native)，
详见 HER_ADVISOR_ARCHITECTURE.md
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session
import json
import uuid

from models.user import MatchResult, User
from models.membership import MembershipTier
from db.database import get_db
from db.repositories import UserRepository
from db.models import SwipeActionDB, MatchHistoryDB
from utils.logger import logger, get_trace_id
from cache import cache_manager
from middleware.rate_limiter import rate_limit_match
from auth.jwt import get_current_user
from agent.tools.icebreaker_tool import IcebreakerTool
from agent.tools.geo_tool import GeoTool, GeoService
from agent.tools.personality_tool import PersonalityTool
from agent.tools.safety_tool import SafetyTool
from agent.tools.interest_tool import InterestTool
from services.membership_service import get_membership_service

router = APIRouter(prefix="/api/matching", tags=["matching"])


# ==================== 常量配置 ====================
MIN_LIMIT = 1  # 最小 limit
MAX_LIMIT = 100  # 最大 limit（防止超大数据量查询）


def validate_limit(limit: int) -> int:
    """
    验证并调整 limit 参数

    Args:
        limit: 用户传入的 limit

    Returns:
        有效范围内的 limit

    Raises:
        HTTPException: limit 无效时抛出
    """
    if limit <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"limit 必须大于 0，当前值：{limit}"
        )
    if limit > MAX_LIMIT:
        logger.warning(f"limit 超过上限 {MAX_LIMIT}，将被限制为 {MAX_LIMIT}")
        return MAX_LIMIT
    return limit


def get_user_service(db=Depends(get_db)):
    """获取用户服务依赖注入"""
    return UserRepository(db)


@router.get("/{user_id}/matches")
async def get_matches(
    user_id: str,
    limit: int = 10,
    service=Depends(get_user_service)
):
    """
    获取推荐匹配对象（使用 AI Native 匹配）

    新架构：
    - ConversationMatchService 从数据库查询候选人
    - HerAdvisorService (AI) 判断匹配度
    - 缓存匹配结果（10 分钟）
    - 限流保护
    """
    trace_id = get_trace_id()

    # 验证 limit 参数
    limit = validate_limit(limit)

    logger.info(f"📡 [MATCH:FIND] START trace_id={trace_id} user={user_id}, limit={limit}")

    # 尝试从缓存读取
    cache_key = f"{user_id}:{limit}"
    cached_matches = cache_manager.get_match_result(user_id, limit)
    if cached_matches is not None:
        logger.info(f"📡 [MATCH:FIND] CACHE HIT trace_id={trace_id} user={user_id}")
        return {"matches": cached_matches, "total": len(cached_matches), "cached": True}

    # 检查用户是否存在
    db_user = service.get_by_id(user_id)
    if not db_user:
        logger.warning(f"📡 [MATCH:FIND] FAILED trace_id={trace_id} user not found: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")

    # 使用 ConversationMatchService 执行匹配（AI Native）
    from services.conversation_match_service import get_conversation_match_service
    match_service = get_conversation_match_service()

    result = await match_service.execute_matching(user_id, limit=limit)

    if not result.get("success"):
        logger.warning(f"📡 [MATCH:FIND] FAILED trace_id={trace_id} error={result.get('error')}")
        raise HTTPException(status_code=500, detail=result.get("error", "Matching failed"))

    candidates = result.get("candidates", [])
    logger.info(f"📡 [MATCH:FIND] Found {len(candidates)} matches for user: {user_id}")

    # 格式化结果
    results = []
    for candidate in candidates:
        results.append({
            'user': User(
                id=candidate.get("user_id"),
                name=candidate.get("name"),
                age=candidate.get("age"),
                gender=candidate.get("gender"),
                location=candidate.get("location"),
                bio=candidate.get("bio"),
                avatar=candidate.get("avatar_url"),
                interests=candidate.get("interests", []),
            ),
            'compatibility_score': candidate.get("compatibility_score"),
            'score_breakdown': candidate.get("score_breakdown", {}),
            'common_interests': candidate.get("common_interests", []),
            'reasoning': candidate.get("reasoning", "AI 综合评估推荐")
        })

    # 写入缓存
    cache_manager.set_match_result(user_id, results, limit)
    logger.info(f"📡 [MATCH:FIND] SUCCESS trace_id={trace_id} found {len(results)} matches, cached")

    return {"matches": results, "total": len(results), "cached": False}


@router.get("/{user_id}/mutual-matches")
async def get_mutual_matches(
    user_id: str,
    service=Depends(get_user_service)
):
    """获取双向匹配对象（从数据库查询）"""
    logger.info(f"Getting mutual matches for user: {user_id}")

    # 尝试从缓存读取
    cached_mutuals = cache_manager.get_mutual_match(user_id)
    if cached_mutuals is not None:
        logger.info(f"Mutual match cache hit for user: {user_id}")
        return {"mutual_matches": cached_mutuals, "total": len(cached_mutuals), "cached": True}

    # 检查用户是否存在
    db_user = service.get_by_id(user_id)
    if not db_user:
        logger.warning(f"Get mutual matches failed: user not found: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")

    # 从数据库查询双向匹配记录
    from sqlalchemy import text
    db = next(get_db())
    mutual_records = db.execute(
        text("""
            SELECT m.user_id_1, m.user_id_2, m.compatibility_score
            FROM match_history m
            WHERE (m.user_id_1 = :user_id OR m.user_id_2 = :user_id)
            AND m.status = 'matched'
        """),
        {"user_id": user_id}
    ).fetchall()

    # 🔧 [性能优化] 批量查询：先收集所有 matched_id，再一次性查询所有用户
    matched_ids = []
    score_map = {}  # user_id -> compatibility_score
    for record in mutual_records:
        matched_id = record[0] if record[0] != user_id else record[1]
        matched_ids.append(matched_id)
        score_map[matched_id] = record[2] or 0.5

    # 批量查询所有匹配用户（消除 N+1 问题）
    matched_users_map = service.get_by_ids(matched_ids) if matched_ids else {}

    results = []
    from api.users import _from_db
    for matched_id in matched_ids:
        matched_db_user = matched_users_map.get(matched_id)
        if matched_db_user:
            matched_user = _from_db(matched_db_user)
            results.append({
                'user': matched_user,
                'compatibility_score': score_map.get(matched_id, 0.5),
            })

    # 写入缓存
    cache_manager.set_mutual_match(user_id, results)

    return {"mutual_matches": results, "total": len(results), "cached": False}


@router.post("/calculate", response_model=MatchResult)
async def calculate_compatibility(
    user_id: str,
    target_user_id: str,
    service=Depends(get_user_service)
):
    """计算两人之间的匹配度（使用 AI 判断）"""
    logger.info(f"Calculating compatibility between {user_id} and {target_user_id}")

    # 检查用户是否存在
    db_user = service.get_by_id(user_id)
    db_target = service.get_by_id(target_user_id)

    if not db_user or not db_target:
        logger.warning(f"Calculate compatibility failed: user not found")
        raise HTTPException(status_code=404, detail="User not found")

    # 注：matchmaker._calculate_compatibility 已废弃
    # 使用 HerAdvisorService (AI) 判断匹配度
    from services.her_advisor_service import get_her_advisor_service
    from services.user_profile_service import get_user_profile_service

    profile_service = get_user_profile_service()
    her_advisor = get_her_advisor_service()

    # 获取用户画像
    self_a, desire_a = await profile_service.get_or_create_profile(user_id)
    self_b, desire_b = await profile_service.get_or_create_profile(target_user_id)

    # AI 判断匹配度
    advice = await her_advisor.generate_match_advice(
        user_id, (self_a, desire_a),
        target_user_id, (self_b, desire_b)
    )

    score = advice.compatibility_score
    breakdown = {
        "interests": advice.interest_alignment,
        "values": advice.value_alignment,
        "lifestyle": advice.lifestyle_fit,
    }

    # 从画像获取共同兴趣
    common_interests = list(set(self_a.interests or []) & set(self_b.interests or []))

    # AI 生成的匹配解释
    reasoning = advice.match_reasoning or "AI 综合评估"

    logger.info(f"Compatibility score between {user_id} and {target_user_id}: {score:.3f}")

    return MatchResult(
        user_id=user_id,
        matched_user_id=target_user_id,
        compatibility_score=score,
        score_breakdown=breakdown,
        reasoning=reasoning,
        common_interests=common_interests,
        potential_issues=advice.potential_challenges or []
    )


# ============= Values 新增 API 端点（竞品分析优化）============

@router.post("/icebreaker")
async def get_icebreaker(
    user_id: str,
    target_user_id: str,
    style: str = "casual",
    count: int = 3,
    service=Depends(get_user_service)
):
    """
    获取破冰问题建议

    参考 Tinder 的"GIF + 预设问题"机制，采用 AI 生成更个性化的破冰内容

    Args:
        user_id: 发起对话的用户 ID
        target_user_id: 目标用户 ID
        style: 问题风格 (casual/humorous/deep/interest_based)
        count: 生成问题数量
    """
    logger.info(f"Generating icebreaker for {user_id} -> {target_user_id}, style={style}, count={count}")

    # 检查用户是否存在
    db_user = service.get_by_id(user_id)
    db_target = service.get_by_id(target_user_id)

    if not db_user or not db_target:
        raise HTTPException(status_code=404, detail="User not found")

    result = IcebreakerTool.handle(user_id, target_user_id, style, count)

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@router.get("/distance/{user_id}/{target_user_id}")
async def get_distance(
    user_id: str,
    target_user_id: str,
    service=Depends(get_user_service)
):
    """
    获取两个用户之间的地理距离

    参考 Tinder 的地理位置匹配功能，支持距离计算和显示

    Args:
        user_id: 用户 ID
        target_user_id: 目标用户 ID
    """
    logger.info(f"Calculating distance between {user_id} and {target_user_id}")

    # 检查用户是否存在
    db_user = service.get_by_id(user_id)
    db_target = service.get_by_id(target_user_id)

    if not db_user or not db_target:
        raise HTTPException(status_code=404, detail="User not found")

    result = GeoTool.handle(action="calculate_distance", user_id=user_id, target_user_id=target_user_id)

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@router.post("/personality/questions")
async def get_personality_questions():
    """
    获取大五人格测试题目

    参考 OkCupid 的详细问卷机制，提供性格评估功能
    """
    result = PersonalityTool.handle(action="get_questions")

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@router.post("/personality/submit")
async def submit_personality_answers(
    answers: Dict[int, int],
    service=Depends(get_user_service)
):
    """
    提交人格测试答案并获取分析结果

    Args:
        answers: 题目答案 {题目 ID: 答案 (1-5)}
    """
    logger.info(f"Submitting personality assessment with {len(answers)} answers")

    result = PersonalityTool.handle(action="submit_answers", answers=answers)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/personality/compatibility/{user_id}/{target_user_id}")
async def get_personality_compatibility(
    user_id: str,
    target_user_id: str,
    service=Depends(get_user_service)
):
    """
    获取两人的性格兼容性分析

    参考 OkCupid 的性格兼容性算法

    Args:
        user_id: 用户 ID
        target_user_id: 目标用户 ID
    """
    logger.info(f"Analyzing personality compatibility between {user_id} and {target_user_id}")

    # 检查用户是否存在
    db_user = service.get_by_id(user_id)
    db_target = service.get_by_id(target_user_id)

    if not db_user or not db_target:
        raise HTTPException(status_code=404, detail="User not found")

    result = PersonalityTool.handle(action="analyze_compatibility", user_id=user_id, target_user_id=target_user_id)

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@router.get("/nearby/{user_id}")
async def get_nearby_users(
    user_id: str,
    max_distance_km: float = 50,
    limit: int = 20,
    service=Depends(get_user_service)
):
    """
    获取附近的用户

    性能优化版本：
    - 使用数据库筛选候选用户（减少计算量）
    - 限制最大候选数量（防止全量计算）

    参考 Tinder 的附近的人功能

    Args:
        user_id: 用户 ID
        max_distance_km: 最大距离（公里）
        limit: 返回数量上限
    """
    logger.info(f"Finding nearby users for {user_id}, max_distance={max_distance_km}km")

    db_user = service.get_by_id(user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    from api.users import _from_db

    # 性能优化：只获取活跃用户，且限制候选数量
    # 实际生产环境应使用 Geo 数据库索引（如 PostGIS）
    all_users = service.list_all(is_active=True)

    # 限制候选数量，防止全量计算
    max_candidates = min(len(all_users), 200)
    candidate_users = all_users[:max_candidates]

    nearby_users = []

    # 批量计算距离
    for user in candidate_users:
        if user.id == user_id:
            continue

        distance = GeoService.calculate_distance(db_user.location, user.location)
        if distance is not None and distance <= max_distance_km:
            user_data = _from_db(user)
            nearby_users.append({
                "user": user_data,
                "distance_km": round(distance, 2),
                "distance_display": GeoTool._generate_distance_message(distance)
            })

    # 按距离排序
    nearby_users.sort(key=lambda x: x["distance_km"])

    return {
        "nearby_users": nearby_users[:limit],
        "total": len(nearby_users),
        "search_radius_km": max_distance_km
    }


# ============= DigitalTwin 新增 API 端点（竞品分析优化 - Bumble/Soul）============

@router.post("/safety/report")
async def report_user(
    reporter_id: str,
    reported_user_id: str,
    reason: str,
    description: Optional[str] = ""
):
    """
    举报用户

    参考 Bumble 的安全举报机制

    Args:
        reporter_id: 举报人用户 ID
        reported_user_id: 被举报用户 ID
        reason: 举报原因 (fake_profile/harassment/inappropriate_content/spam/underage/scam/other)
        description: 举报详细描述
    """
    logger.info(f"Safety report: {reporter_id} -> {reported_user_id}, reason={reason}")

    result = SafetyTool.handle(
        action="report_user",
        reporter_id=reporter_id,
        reported_user_id=reported_user_id,
        reason=reason,
        description=description
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/safety/score/{user_id}")
async def get_safety_score(user_id: str):
    """
    获取用户安全评分

    参考 Bumble 的用户评分系统

    Args:
        user_id: 用户 ID
    """
    logger.info(f"Getting safety score for user: {user_id}")

    result = SafetyTool.handle(action="get_safety_score", user_id=user_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.post("/safety/detect-content")
async def detect_content(content: str):
    """
    检测敏感内容

    Args:
        content: 待检测内容
    """
    result = SafetyTool.handle(action="detect_content", content=content)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/safety/status/{user_id}")
async def get_user_safety_status(user_id: str):
    """
    获取用户安全状态

    Args:
        user_id: 用户 ID
    """
    result = SafetyTool.handle(action="get_user_status", user_id=user_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/interest/match/{user_id}/{target_user_id}")
async def match_by_interest(
    user_id: str,
    target_user_id: str
):
    """
    兴趣匹配分析

    参考 Soul 的灵魂匹配机制，基于兴趣爱好进行匹配

    Args:
        user_id: 用户 ID
        target_user_id: 目标用户 ID
    """
    logger.info(f"Interest match: {user_id} -> {target_user_id}")

    result = InterestTool.handle(
        action="match_by_interest",
        user_id=user_id,
        target_user_id=target_user_id
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/interest/communities/{user_id}")
async def get_community_recommendations(
    user_id: str,
    limit: int = 5
):
    """
    推荐兴趣社区

    参考 Soul 的兴趣社区功能

    Args:
        user_id: 用户 ID
        limit: 推荐数量
    """
    logger.info(f"Recommending communities for user: {user_id}, limit={limit}")

    result = InterestTool.handle(
        action="get_communities",
        user_id=user_id,
        limit=limit
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.post("/interest/topics")
async def generate_conversation_topics(
    user_id: Optional[str] = None,
    target_user_id: Optional[str] = None,
    common_interests: Optional[List[str]] = None
):
    """
    生成对话话题

    基于共同兴趣生成对话话题建议

    Args:
        user_id: 用户 ID
        target_user_id: 目标用户 ID
        common_interests: 共同兴趣列表
    """
    params = {"action": "get_topics"}
    if user_id:
        params["user_id"] = user_id
    if target_user_id:
        params["target_user_id"] = target_user_id
    if common_interests:
        params["common_interests"] = common_interests

    result = InterestTool.handle(**params)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/interest/tags/{user_id}")
async def analyze_interest_tags(user_id: str):
    """
    分析用户兴趣标签

    参考 Soul 的标签系统，分析用户的兴趣特征

    Args:
        user_id: 用户 ID
    """
    logger.info(f"Analyzing interest tags for user: {user_id}")

    result = InterestTool.handle(
        action="analyze_tags",
        user_id=user_id
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


# ============= P5 新增 API 端点（滑动交互与会员体系）============

class SwipeRequest(BaseModel):
    """滑动请求模型"""
    target_user_id: str
    action: str  # like, pass, super_like


class SwipeResponse(BaseModel):
    """滑动响应模型"""
    success: bool
    match: bool = False
    message: str = ""
    remaining_likes: int = -1  # -1 表示无限制


@router.get("/recommend")
async def get_recommendations(
    limit: int = 15,
    age_min: Optional[int] = None,
    age_max: Optional[int] = None,
    distance: Optional[int] = None,
    current_user_id: str = Depends(get_current_user)
):
    """
    获取推荐用户列表（用于滑动交互）

    新架构（AI Native）：
    - ConversationMatchService 从数据库查询候选人
    - HerAdvisorService (AI) 判断匹配度

    Args:
        limit: 返回数量上限
        age_min: 最小年龄
        age_max: 最大年龄
        distance: 最大距离 (km)
    """
    user_id = current_user_id
    logger.info(f"Getting recommendations for user: {user_id}, limit={limit}")

    db = next(get_db())
    service = UserRepository(db)
    db_user = service.get_by_id(user_id)

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # 使用 MatchExecutor 执行匹配（AI Native）
    from services.conversation_match.match_executor import get_match_executor
    from services.user_profile_service import get_user_profile_service

    match_executor = get_match_executor()
    profile_service = get_user_profile_service()

    # 获取用户画像
    self_profile, desire_profile = await profile_service.get_or_create_profile(user_id)

    # 构建提取条件
    extracted_conditions = {}
    if age_min or age_max:
        extracted_conditions["age_range"] = [age_min or 18, age_max or 100]
    if distance:
        extracted_conditions["max_distance_km"] = distance

    # 执行匹配
    candidates = await match_executor.execute_matching(
        user_id,
        self_profile,
        desire_profile,
        extracted_conditions,
        limit=limit
    )

    if not candidates:
        logger.warning(f"No candidates found for user {user_id}")
        return []

    # 批量查询认证状态（优化 N+1 查询）
    candidate_ids = [c.get("user_id") for c in candidates]
    from sqlalchemy import text
    # 🔧 [修复] SQL 参数绑定：SQLite 不支持 IN :param 绑定 tuple，需展开
    placeholders = ",".join([f":id_{i}" for i in range(len(candidate_ids))])
    params = {f"id_{i}": id for i, id in enumerate(candidate_ids)}
    verified_users = db.execute(
        text(f"SELECT user_id FROM identity_verifications WHERE user_id IN ({placeholders}) AND verification_status = 'verified'"),
        params
    ).fetchall()
    verified_user_ids = {row[0] for row in verified_users}

    recommendations = []
    for candidate in candidates:
        profile = candidate.get("candidate_profile", {})
        advice = candidate.get("her_advice")

        # 🔧 [修复] profile 现在是扁平结构（match_executor 已合并原始数据）
        # 但保留 basic 字段兼容性检查
        basic = profile.get("basic", profile)  # 如果有 basic 则用它，否则用整个 profile

        # 从 her_advice 获取 reasoning
        reasoning = "AI 综合评估推荐"
        if advice and hasattr(advice, 'reasoning'):
            reasoning = advice.reasoning
        elif advice and isinstance(advice, dict):
            reasoning = advice.get("reasoning", reasoning)

        recommendations.append({
            "id": candidate.get("user_id"),
            "name": profile.get("name") or basic.get("name"),
            "username": profile.get("name") or basic.get("name"),
            "age": profile.get("age") or basic.get("age"),
            "gender": profile.get("gender") or basic.get("gender"),
            "location": profile.get("location") or basic.get("location"),
            "avatar_url": profile.get("avatar_url") or basic.get("avatar_url"),
            "bio": profile.get("bio") or basic.get("bio"),
            "interests": profile.get("interests") or basic.get("interests", []),
            "goal": profile.get("relationship_goal") or basic.get("relationship_goal", "serious"),
            "verified": candidate.get("user_id") in verified_user_ids,
            "compatibility_score": round(candidate.get("score", 0.5), 2),
            "match_reason": reasoning,
            "compatibility_reason": reasoning,
            "vector_match_highlights": candidate.get("vector_match_highlights", {}) or profile.get("vector_match_highlights", {}),
        })

    # 按匹配度排序
    recommendations.sort(key=lambda x: x["compatibility_score"], reverse=True)

    return recommendations[:limit]


@router.post("/swipe")
async def swipe(
    request: SwipeRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    滑动操作（喜欢/无感/超级喜欢）

    Args:
        target_user_id: 目标用户 ID
        action: 操作类型 (like, pass, super_like)
    """
    user_id = current_user
    logger.info(f"Swipe: {user_id} -> {request.target_user_id}, action={request.action}")

    # 检查会员权限
    membership_svc = get_membership_service(db)
    allowed, message = membership_svc.check_action_limit(user_id, request.action)
    if not allowed:
        raise HTTPException(status_code=403, detail=message)

    service = UserRepository(db)

    # 检查目标用户是否存在
    target_user = service.get_by_id(request.target_user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="目标用户不存在")

    # 检查是否已经滑动过
    existing = db.query(SwipeActionDB).filter(
        SwipeActionDB.user_id == user_id,
        SwipeActionDB.target_user_id == request.target_user_id
    ).first()

    if existing:
        # 已经滑动过，更新记录
        existing.action = request.action
        existing.created_at = datetime.now()
    else:
        # 新记录
        swipe_action = SwipeActionDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            target_user_id=request.target_user_id,
            action=request.action,
            is_matched=False,
            created_at=datetime.now()
        )
        db.add(swipe_action)

    db.commit()

    # 检查是否匹配（双向喜欢）
    is_match = False
    match_id = None
    if request.action in ["like", "super_like"]:
        # 检查对方是否也喜欢当前用户
        reverse_like = db.query(SwipeActionDB).filter(
            SwipeActionDB.user_id == request.target_user_id,
            SwipeActionDB.target_user_id == user_id,
            SwipeActionDB.action.in_(["like", "super_like"])
        ).first()

        if reverse_like:
            is_match = True
            match_id = str(uuid.uuid4())
            logger.info(f"Match! {user_id} <-> {request.target_user_id}")

            # 创建匹配记录
            match_history = MatchHistoryDB(
                id=match_id,
                user_id_1=user_id,
                user_id_2=request.target_user_id,
                compatibility_score=0.8,
                status="matched",
                created_at=datetime.now()
            )
            db.add(match_history)

            # 更新滑动记录为匹配状态
            if existing:
                existing.is_matched = True
            else:
                # 获取刚创建的滑动记录
                new_swipe = db.query(SwipeActionDB).filter(
                    SwipeActionDB.user_id == user_id,
                    SwipeActionDB.target_user_id == request.target_user_id
                ).first()
                if new_swipe:
                    new_swipe.is_matched = True

            db.commit()

            # AI Native: 触发匹配事件，引发破冰心跳
            try:
                from agent.autonomous.event_listener import emit_event
                emit_event(
                    event_type="match_created",
                    event_data={
                        "match_id": match_id,
                        "user_id_1": user_id,
                        "user_id_2": request.target_user_id,
                        "compatibility_score": 0.8,
                    },
                    event_source=user_id
                )
                logger.info(f"📡 [MATCH] Event 'match_created' emitted for match {match_id}")
            except Exception as e:
                logger.warning(f"Failed to emit match_created event: {e}")

    # 获取剩余喜欢次数
    remaining = membership_svc.get_user_limit(user_id, "daily_likes")
    if remaining == -1:
        remaining = -1  # 无限制
    else:
        # 减去今日已使用的次数
        used_count = membership_svc.get_daily_usage_count(user_id, "like")
        remaining = max(0, remaining - used_count)

    return SwipeResponse(
        success=True,
        match=is_match,
        message="超级喜欢!" if request.action == "super_like" else "",
        remaining_likes=remaining
    )


@router.post("/swipe/{swipe_id}/undo")
async def undo_swipe(
    swipe_id: str,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    撤销滑动操作（会员功能）

    Args:
        swipe_id: 滑动记录 ID
    """
    user_id = current_user

    # 检查是否有回退权限
    membership_svc = get_membership_service(db)
    allowed, message = membership_svc.check_action_limit(user_id, "rewind")
    if not allowed:
        raise HTTPException(status_code=403, detail=message)

    # 删除滑动记录（使用 SQLAlchemy ORM）
    swipe_record = db.query(SwipeActionDB).filter(
        SwipeActionDB.id == swipe_id,
        SwipeActionDB.user_id == user_id
    ).first()

    if not swipe_record:
        raise HTTPException(status_code=404, detail="未找到滑动记录")

    db.delete(swipe_record)
    db.commit()

    return {"success": True, "message": "已撤销滑动"}
