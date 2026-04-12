"""
匹配 API 路由

Identity 优化：
- 集成缓存层（匹配结果缓存）
- 集成限流保护
- 优化数据库查询

Values 新增（竞品分析优化）:
- 破冰问题生成 (参考 Tinder/Guide)
- 地理位置距离计算 (参考 Tinder 附近的人)
- 性格兼容性分析 (参考 OkCupid 大五人格)

DigitalTwin 新增（竞品分析优化）:
- 安全机制 (参考 Bumble 举报/封禁系统)
- 兴趣社交 (参考 Soul 灵魂匹配/兴趣社区)
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import json
import uuid

from models.user import MatchResult, User
from models.membership import MembershipTier
from matching.matcher import matchmaker
from db.database import get_db
from db.repositories import UserRepository
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
    获取推荐匹配对象

    优化：
    - 缓存匹配结果（10 分钟）
    - 限流保护（50 次/秒突发）
    - limit 验证：1-100 范围
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

    from api.users import _from_db

    # 确保用户已在匹配系统中注册
    if user_id not in matchmaker._users:
        matchmaker.register_user(_from_db(db_user).model_dump())
        logger.info(f"📡 [MATCH:FIND] User {user_id} registered to matching system on demand")

    matches = matchmaker.find_matches(user_id, limit=limit)
    logger.info(f"📡 [MATCH:FIND] Found {len(matches)} matches for user: {user_id}")

    results = []
    current_user = _from_db(db_user)
    for match in matches:
        matched_db_user = service.get_by_id(match['user_id'])
        # 冷启动/测试环境下可能出现：算法候选存在，但数据库读取返回 None。
        # 为保证核心匹配链路可用，这里回退到 matchmaker 内存数据构造 User。
        if matched_db_user:
            matched_user = _from_db(matched_db_user)
        else:
            candidate_data = matchmaker._users.get(match["user_id"])
            if not candidate_data:
                continue
            matched_user = User(**candidate_data)

        # 生成匹配解释
        reasoning = matchmaker.generate_match_reasoning(
            current_user.model_dump(),
            matched_user.model_dump(),
            match['score'],
            match['breakdown']
        )
        common_interests = list(set(matched_user.interests) & set(current_user.interests))
        results.append({
            'user': matched_user,
            'compatibility_score': match['score'],
            'score_breakdown': match['breakdown'],
            'common_interests': common_interests,
            'reasoning': reasoning
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
    """获取双向匹配对象"""
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

    from api.users import _from_db

    # 确保用户已在匹配系统中注册
    if user_id not in matchmaker._users:
        matchmaker.register_user(_from_db(db_user).model_dump())
        logger.info(f"User {user_id} registered to matching system on demand")

    mutuals = matchmaker.get_mutual_matches(user_id)
    logger.info(f"Found {len(mutuals)} mutual matches for user: {user_id}")

    results = []
    for match in mutuals:
        matched_db_user = service.get_by_id(match['user_id'])
        if matched_db_user:
            matched_user = _from_db(matched_db_user)
            results.append({
                'user': matched_user,
                'compatibility_score': match['score'],
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
    """计算两人之间的匹配度"""
    logger.info(f"Calculating compatibility between {user_id} and {target_user_id}")

    # 检查用户是否存在
    db_user = service.get_by_id(user_id)
    db_target = service.get_by_id(target_user_id)

    if not db_user or not db_target:
        logger.warning(f"Calculate compatibility failed: user not found")
        raise HTTPException(status_code=404, detail="User not found")

    from api.users import _from_db
    user = _from_db(db_user)
    target = _from_db(db_target)

    score, breakdown = matchmaker._calculate_compatibility(
        user.model_dump(),
        target.model_dump()
    )

    common_interests = list(set(user.interests) & set(target.interests))

    # 使用算法模块的统一匹配解释生成
    reasoning = matchmaker.generate_match_reasoning(
        user.model_dump(),
        target.model_dump(),
        score,
        breakdown
    )

    logger.info(f"Compatibility score between {user_id} and {target_user_id}: {score:.3f}")

    return MatchResult(
        user_id=user_id,
        matched_user_id=target_user_id,
        compatibility_score=score,
        score_breakdown=breakdown,
        reasoning=reasoning,
        common_interests=common_interests,
        potential_issues=[]
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

    # 获取所有用户并筛选
    all_users = service.list_all()
    nearby_users = []

    for user in all_users:
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

    from api.users import _from_db
    current_user_obj = _from_db(db_user)

    # 获取所有用户进行筛选
    all_users = service.list_all()
    recommendations = []

    for user in all_users:
        if user.id == user_id:
            continue

        user_obj = _from_db(user)

        # 年龄筛选
        if age_min and user_obj.age < age_min:
            continue
        if age_max and user_obj.age > age_max:
            continue

        # 距离筛选
        if distance:
            user_distance = GeoService.calculate_distance(db_user.location, user_obj.location)
            if user_distance is None or user_distance > distance:
                continue

        # 基本兼容性检查（性取向、性别偏好等）
        if not matchmaker._check_basic_compatibility(current_user_obj.model_dump(), user_obj.model_dump()):
            logger.debug(f"User {user_id} skipped {user.id} due to basic incompatibility")
            continue

        # 计算匹配度
        try:
            score, breakdown = matchmaker._calculate_compatibility(
                current_user_obj.model_dump(),
                user_obj.model_dump()
            )
        except Exception as e:
            logger.warning(f"Compatibility calculation failed for {user_id} -> {user.id}: {e}")
            score = 0.5
            breakdown = {}

        # 生成匹配原因
        reasoning = matchmaker.generate_match_reasoning(
            current_user_obj.model_dump(),
            user_obj.model_dump(),
            score,
            breakdown
        )

        # 检查认证状态
        from sqlalchemy import text
        identity_db = db.execute(
            text("SELECT * FROM identity_verifications WHERE user_id = :user_id AND verification_status = 'verified'"),
            {"user_id": user.id}
        ).fetchone()
        is_verified = identity_db is not None

        recommendations.append({
            "id": user.id,
            "name": user.name,
            "username": user.name,
            "age": user.age,
            "gender": user.gender,
            "location": user.location,
            "avatar_url": user.avatar_url,
            "bio": user.bio,
            "interests": json.loads(user.interests) if user.interests and user.interests != "" else [],
            "goal": user.goal if hasattr(user, 'goal') else "serious",
            "verified": is_verified,
            "compatibility_score": round(score, 2),
            "match_reason": reasoning,
            "compatibility_reason": reasoning,
        })

    # 按匹配度排序
    recommendations.sort(key=lambda x: x["compatibility_score"], reverse=True)

    return recommendations[:limit]


@router.post("/swipe")
async def swipe(
    request: SwipeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    滑动操作（喜欢/无感/超级喜欢）

    Args:
        target_user_id: 目标用户 ID
        action: 操作类型 (like, pass, super_like)
    """
    user_id = current_user["user_id"]
    logger.info(f"Swipe: {user_id} -> {request.target_user_id}, action={request.action}")

    # 检查会员权限
    db = get_db()
    membership_svc = get_membership_service(db)
    allowed, message = membership_svc.check_action_limit(user_id, request.action)
    if not allowed:
        raise HTTPException(status_code=403, detail=message)

    service = UserRepository(get_db())

    # 检查目标用户是否存在
    target_user = service.get_by_id(request.target_user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="目标用户不存在")

    # 记录滑动行为到数据库
    db = get_db()
    cursor = db.cursor()

    # 检查是否已经滑动过
    cursor.execute("""
        SELECT * FROM swipe_actions
        WHERE user_id = %s AND target_user_id = %s
    """, (user_id, request.target_user_id))

    existing = cursor.fetchone()
    if existing:
        # 已经滑动过，更新记录
        cursor.execute("""
            UPDATE swipe_actions
            SET action = %s, created_at = %s
            WHERE user_id = %s AND target_user_id = %s
        """, (request.action, datetime.now(), user_id, request.target_user_id))
    else:
        # 新记录
        cursor.execute("""
            INSERT INTO swipe_actions (id, user_id, target_user_id, action, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (str(uuid.uuid4()), user_id, request.target_user_id, request.action, datetime.now()))

    db.commit()

    # 检查是否匹配（双向喜欢）
    is_match = False
    if request.action in ["like", "super_like"]:
        # 检查对方是否也喜欢当前用户
        cursor.execute("""
            SELECT * FROM swipe_actions
            WHERE user_id = %s AND target_user_id = %s AND action IN ('like', 'super_like')
        """, (request.target_user_id, user_id))

        if cursor.fetchone():
            is_match = True
            match_id = str(uuid.uuid4())
            logger.info(f"Match! {user_id} <-> {request.target_user_id}")

            # 创建匹配记录
            cursor.execute("""
                INSERT INTO match_history (id, user_id_1, user_id_2, compatibility_score, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (match_id, user_id, request.target_user_id, 0.8, "matched", datetime.now()))
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

    cursor.close()
    db.close()

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
    current_user: dict = Depends(get_current_user)
):
    """
    撤销滑动操作（会员功能）

    Args:
        swipe_id: 滑动记录 ID
    """
    user_id = current_user["user_id"]

    # 检查是否有回退权限
    db = get_db()
    membership_svc = get_membership_service(db)
    allowed, message = membership_svc.check_action_limit(user_id, "rewind")
    if not allowed:
        raise HTTPException(status_code=403, detail=message)

    db = get_db()
    cursor = db.cursor()

    # 删除滑动记录
    cursor.execute("""
        DELETE FROM swipe_actions
        WHERE id = %s AND user_id = %s
    """, (swipe_id, user_id))

    affected = cursor.rowcount
    db.commit()
    cursor.close()
    db.close()

    if affected == 0:
        raise HTTPException(status_code=404, detail="未找到滑动记录")

    return {"success": True, "message": "已撤销滑动"}
