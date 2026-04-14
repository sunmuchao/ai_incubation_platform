"""
个人信息收集 API - AI Native 设计

通过对话式交互收集用户偏好和资料
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from utils.logger import logger
from utils.db_session_manager import db_session
from db.models import UserDB
import json

router = APIRouter(prefix="/api/profile", tags=["profile"])


# ========== 请求/响应模型 ==========

class ProfileQuestionRequest(BaseModel):
    """请求问题卡片"""
    user_id: Optional[str] = None
    conversation_context: Optional[List[Dict[str, Any]]] = None
    trigger_reason: str = "user_intent"


class ProfileAnswerRequest(BaseModel):
    """提交回答"""
    user_id: Optional[str] = None
    dimension: str
    answer: Any
    depth: int = 0
    previous_context: Optional[List[Dict[str, Any]]] = None


# ========== API 端点 ==========

@router.post("/question")
async def get_profile_question(
    request: ProfileQuestionRequest,
    authorization: Optional[str] = Header(None)
):
    """
    获取下一个问题卡片

    AI 分析用户画像缺口，动态生成问题和选项。

    Args:
        request: 包含用户 ID、对话上下文、触发原因

    Returns:
        问题卡片数据，包含问题、选项、类型等
    """
    try:
        # 获取用户 ID
        user_id = request.user_id
        if not user_id and authorization:
            # 从 token 解析用户 ID
            user_id = _extract_user_id_from_token(authorization)

        if not user_id:
            user_id = "user-anonymous-dev"

        # 获取当前用户画像
        profile = await _get_user_profile(user_id)

        # 调用 Skill
        from agent.skills.profile_collection_skill import get_profile_collection_skill

        skill = get_profile_collection_skill()
        result = await skill.execute(
            user_id=user_id,
            conversation_context=request.conversation_context,
            current_profile=profile,
            trigger_reason=request.trigger_reason
        )

        return result

    except Exception as e:
        logger.error(f"ProfileQuestion API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/answer")
async def submit_profile_answer(
    request: ProfileAnswerRequest,
    authorization: Optional[str] = Header(None)
):
    """
    提交用户回答

    处理用户选择，更新画像，并返回下一个问题或确认消息。

    Args:
        request: 包含维度、回答内容、深度等

    Returns:
        AI 确认回复和下一个问题（如果有）
    """
    try:
        # 获取用户 ID
        user_id = request.user_id
        if not user_id and authorization:
            user_id = _extract_user_id_from_token(authorization)

        if not user_id:
            user_id = "user-anonymous-dev"

        # 获取当前用户画像
        profile = await _get_user_profile(user_id)

        # 调用 Skill 处理回答（包含深度参数用于追问判断）
        from agent.skills.profile_collection_skill import get_profile_collection_skill

        skill = get_profile_collection_skill()
        result = await skill.process_user_answer(
            user_id=user_id,
            dimension=request.dimension,
            answer=request.answer,
            profile=profile,
            current_depth=request.depth or 0,  # 追问深度
            context=request.previous_context
        )

        # 保存到数据库
        if result.get("updated_profile"):
            await _update_user_profile(user_id, result["updated_profile"])

        return result

    except Exception as e:
        logger.error(f"ProfileAnswer API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/follow-up")
async def get_follow_up_question(
    request: ProfileAnswerRequest,
    authorization: Optional[str] = Header(None)
):
    """
    获取追问问题

    当用户回答不够深入时，AI 生成追问。

    Args:
        request: 包含上一个回答的信息

    Returns:
        追问问题卡片
    """
    try:
        user_id = request.user_id or "user-anonymous-dev"
        if not request.user_id and authorization:
            user_id = _extract_user_id_from_token(authorization) or user_id

        profile = await _get_user_profile(user_id)

        # 调用 Skill 生成追问
        from agent.skills.profile_collection_skill import get_profile_collection_skill

        skill = get_profile_collection_skill()
        result = await skill.execute(
            user_id=user_id,
            conversation_context=request.previous_context,
            current_profile=profile,
            trigger_reason="follow_up",
            previous_answer={
                "dimension": request.dimension,
                "answer": request.answer,
                "depth": request.depth
            }
        )

        return result

    except Exception as e:
        logger.error(f"FollowUp API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gaps/{user_id}")
async def get_profile_gaps(user_id: str):
    """
    获取用户画像缺口分析

    返回用户还缺少哪些信息维度。

    Args:
        user_id: 用户 ID

    Returns:
        缺失的信息维度列表
    """
    try:
        profile = await _get_user_profile(user_id)

        from agent.skills.profile_collection_skill import get_profile_collection_skill

        skill = get_profile_collection_skill()
        gaps = skill._analyze_profile_gaps(profile)

        return {
            "success": True,
            "gaps": gaps,
            "total_dimensions": len(skill.PROFILE_DIMENSIONS),
            "filled_dimensions": len(skill.PROFILE_DIMENSIONS) - len(gaps)
        }

    except Exception as e:
        logger.error(f"ProfileGaps API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 辅助函数 ==========

def _extract_user_id_from_token(authorization: str) -> Optional[str]:
    """从 token 中提取用户 ID"""
    try:
        from auth.jwt import decode_access_token
        if authorization.startswith("Bearer "):
            token = authorization[7:]
            return decode_access_token(token)
    except Exception:
        pass
    return None


async def _get_user_profile(user_id: str) -> Dict[str, Any]:
    """获取用户画像"""
    try:
        with db_session() as db:
            user = db.query(UserDB).filter(UserDB.id == user_id).first()
            if user:
                return {
                    "relationship_goal": getattr(user, "goal", None) or getattr(user, "relationship_goal", None),
                    "age_preference": {
                        "min": getattr(user, "preferred_age_min", None),
                        "max": getattr(user, "preferred_age_max", None),
                    } if getattr(user, "preferred_age_min", None) else None,
                    "location_preference": getattr(user, "preferred_location", None),  # 用户的地域偏好
                    "interests": getattr(user, "interests", None),
                    "personality": json.loads(getattr(user, "personality", "{}") or "{}"),
                    "lifestyle": json.loads(getattr(user, "lifestyle", "{}") or "{}"),
                    "values": json.loads(getattr(user, "values", "{}") or "{}"),
                    "deal_breakers": json.loads(getattr(user, "deal_breakers", "{}") or "{}"),
                    # QuickStart 核心字段
                    "age": getattr(user, "age", None),
                    "gender": getattr(user, "gender", None),
                    "location": getattr(user, "location", None),
                    # QuickStart 可选字段
                    "education": getattr(user, "education", None),
                    "occupation": getattr(user, "occupation", None),
                    "income": getattr(user, "income", None),

                    # QuickStart 扩展字段
                    "height": getattr(user, "height", None),
                    "has_car": getattr(user, "has_car", None),
                    "housing": getattr(user, "housing", None),

                    # 一票否决维度
                    "want_children": getattr(user, "want_children", None),
                    "spending_style": getattr(user, "spending_style", None),

                    # 核心价值观维度
                    "family_importance": getattr(user, "family_importance", None),
                    "work_life_balance": getattr(user, "work_life_balance", None),

                    # 迁移能力维度
                    "migration_willingness": getattr(user, "migration_willingness", None),
                    "accept_remote": getattr(user, "accept_remote", None),  # ✨ 是否接受异地

                    # 生活方式维度
                    "sleep_type": getattr(user, "sleep_type", None),
                }
    except Exception as e:
        logger.debug(f"Failed to get user profile: {e}")

    return {}


async def _update_user_profile(user_id: str, profile: Dict[str, Any]) -> bool:
    """更新用户画像"""
    try:
        with db_session() as db:
            user = db.query(UserDB).filter(UserDB.id == user_id).first()
            if user:
                # ===== QuickStart 基础字段（用户本身的属性）=====
                # 这些字段不能通过行为推断，必须用户填写
                if "age" in profile:
                    user.age = profile["age"]

                if "gender" in profile:
                    user.gender = profile["gender"]

                if "location" in profile:
                    user.location = profile["location"]

                if "relationship_goal" in profile:
                    user.relationship_goal = profile["relationship_goal"]

                # ===== 偏好字段（用户想要什么）=====
                if "interests" in profile:
                    user.interests = profile["interests"]

                # 地域偏好 -> preferred_location
                if "location_preference" in profile:
                    # 如果是列表，取第一个或拼接
                    loc_value = profile["location_preference"]
                    if isinstance(loc_value, list):
                        user.preferred_location = loc_value[0] if loc_value else None
                    else:
                        user.preferred_location = loc_value

                # 年龄偏好
                if "age_preference" in profile:
                    age_pref = profile["age_preference"]
                    if isinstance(age_pref, dict):
                        user.preferred_age_min = age_pref.get("min", 18)
                        user.preferred_age_max = age_pref.get("max", 60)
                    elif isinstance(age_pref, str) and "-" in age_pref:
                        # 解析 "25-35" 格式
                        parts = age_pref.split("-")
                        if len(parts) == 2:
                            user.preferred_age_min = int(parts[0])
                            user.preferred_age_max = int(parts[1])

                # ===== 动态画像字段（从行为推断）=====
                # 性格特点
                if "personality" in profile:
                    user.personality = json.dumps(profile["personality"]) if isinstance(profile["personality"], (dict, list)) else profile["personality"]

                # 生活方式
                if "lifestyle" in profile:
                    user.lifestyle = json.dumps(profile["lifestyle"]) if isinstance(profile["lifestyle"], (dict, list)) else profile["lifestyle"]

                # 价值观
                if "values" in profile:
                    user.values = json.dumps(profile["values"]) if isinstance(profile["values"], (dict, list)) else profile["values"]

                # 底线禁忌
                if "deal_breakers" in profile:
                    user.deal_breakers = json.dumps(profile["deal_breakers"]) if isinstance(profile["deal_breakers"], (dict, list)) else profile["deal_breakers"]

                # ===== QuickStart 可选字段 =====
                if "education" in profile:
                    user.education = profile["education"]

                if "occupation" in profile:
                    user.occupation = profile["occupation"]

                if "income" in profile:
                    user.income = profile["income"]

                # ===== QuickStart 扩展字段 =====
                if "height" in profile:
                    user.height = profile["height"]

                if "has_car" in profile:
                    user.has_car = profile["has_car"]

                if "housing" in profile:
                    user.housing = profile["housing"]

                # ===== 一票否决维度 =====
                if "want_children" in profile:
                    user.want_children = profile["want_children"]

                if "spending_style" in profile:
                    user.spending_style = profile["spending_style"]

                # ===== 核心价值观维度 =====
                if "family_importance" in profile:
                    user.family_importance = profile["family_importance"]

                if "work_life_balance" in profile:
                    user.work_life_balance = profile["work_life_balance"]

                # ===== 迁移能力维度 =====
                if "migration_willingness" in profile:
                    user.migration_willingness = profile["migration_willingness"]

                if "accept_remote" in profile:
                    user.accept_remote = profile["accept_remote"]

                # ===== 生活方式维度 =====
                if "sleep_type" in profile:
                    user.sleep_type = profile["sleep_type"]

                db.commit()
                logger.info(f"Profile updated for user={user_id}: {list(profile.keys())}")
                return True
    except Exception as e:
        logger.error(f"Failed to update user profile: {e}")

    return False


# ========== QuickStart 批量提交 API ==========

class QuickStartSubmitRequest(BaseModel):
    """QuickStart 批量提交请求 - 一次性提交所有问卷答案"""
    user_id: str
    answers: Dict[str, Any]  # 所有维度的答案，key 为维度名


@router.post("/quickstart/submit")
async def quickstart_submit(
    request: QuickStartSubmitRequest,
    authorization: Optional[str] = Header(None)
):
    """
    QuickStart 批量提交 - 一次性保存所有问卷答案

    🔧 [性能优化] 避免逐个维度调用 API，前端一次性提交所有答案

    流程：
    1. 直接写入数据库（不触发 LLM 分析）
    2. 评估 profile_confidence
    3. 返回完成状态

    Args:
        request: 包含 user_id 和所有维度的答案字典

    Returns:
        {
            "success": true,
            "updated_fields": ["field1", "field2", ...],
            "profile_completeness": 0.85,
            "message": "太棒了！可以开始你的配对旅程了 🎉"
        }
    """
    import time
    start_time = time.time()

    logger.info(f"[QuickStart] Batch submit for user={request.user_id}, fields={list(request.answers.keys())}")

    # 验证 user_id
    with db_session() as db:
        user = db.query(UserDB).filter(UserDB.id == request.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

    # 批量更新用户画像（直接写入数据库，不触发 LLM）
    success = await _update_user_profile(request.user_id, request.answers)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update profile")

    # 计算画像完整度
    required_fields = [
        "age", "gender", "location", "relationship_goal",
        "education", "occupation", "income",
        "height", "has_car", "housing",
        "want_children", "spending_style",
        "family_importance", "work_life_balance",
        "migration_willingness", "accept_remote", "sleep_type"
    ]

    filled_count = sum(1 for f in required_fields if request.answers.get(f))
    completeness = filled_count / len(required_fields)

    # 异步触发置信度评估（不阻塞响应）
    try:
        from api.profile_confidence import evaluate_on_register
        import asyncio
        asyncio.create_task(evaluate_on_register(request.user_id))
        logger.info(f"[QuickStart] Triggered async confidence evaluation")
    except Exception as e:
        logger.warning(f"[QuickStart] Failed to trigger confidence evaluation: {e}")

    total_time = time.time() - start_time
    logger.info(f"[QuickStart] COMPLETE in {total_time:.3f}s for user={request.user_id}")

    return {
        "success": True,
        "updated_fields": list(request.answers.keys()),
        "profile_completeness": completeness,
        "message": "太棒了！可以开始你的配对旅程了 🎉" if completeness >= 0.7 else "信息已保存，继续完善可以获得更好的匹配~",
        "response_time_ms": int(total_time * 1000)
    }