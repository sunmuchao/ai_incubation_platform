"""
渐进式智能收集 API

提供以下接口：
1. 用户画像查询/更新
2. 画像完整度查询
3. 第三方授权
4. 游戏化测试
5. 冷启动匹配推荐
"""

from fastapi import APIRouter, HTTPException, Depends, Header, Query, Body
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import json

from utils.logger import logger
from utils.db_session_manager import db_session
from db.models import UserDB, UserVectorProfileDB, ProfileInferenceRecordDB, GameTestRecordDB

router = APIRouter(prefix="/api/progressive-profile", tags=["progressive-profile"])


# ========== 请求/响应模型 ==========

class ProfileStatusResponse(BaseModel):
    """画像状态响应"""
    user_id: str
    completeness_ratio: float
    recommended_strategy: str
    strategy_reason: str
    critical_dimensions_filled: bool
    missing_critical: List[str]
    category_completeness: Dict[str, float]
    can_use_precise_match: bool
    suggested_actions: List[str]


class WechatAuthRequest(BaseModel):
    """微信授权请求"""
    auth_code: str


class GameTestStartResponse(BaseModel):
    """游戏测试开始响应"""
    test_type: str
    test_name: str
    description: str
    total_questions: int
    estimated_minutes: int
    reward: str
    current_question: int
    question: Optional[Dict[str, Any]]


class GameTestAnswerRequest(BaseModel):
    """游戏测试答案请求"""
    test_type: str
    question_id: str
    answer: str


class ColdStartMatchRequest(BaseModel):
    """冷启动匹配请求"""
    limit: int = 10


# ========== API 端点 ==========

@router.get("/status/{user_id}", response_model=ProfileStatusResponse)
async def get_profile_status(
    user_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    获取用户画像状态

    返回画像完整度、推荐策略、建议行动等
    """
    try:
        with db_session() as db:
            # 查询用户画像
            profile = db.query(UserVectorProfileDB).filter(
                UserVectorProfileDB.user_id == user_id
            ).first()

            if not profile:
                # 创建默认画像
                return ProfileStatusResponse(
                    user_id=user_id,
                    completeness_ratio=0.0,
                    recommended_strategy="cold_start",
                    strategy_reason="画像信息为空，使用冷启动策略",
                    critical_dimensions_filled=False,
                    missing_critical=["生育意愿", "金钱观"],
                    category_completeness={},
                    can_use_precise_match=False,
                    suggested_actions=[
                        "完成基本信息填写",
                        "进行人格测试",
                        "授权微信信息"
                    ]
                )

            # 解析完整度信息
            category_completeness = json.loads(profile.category_completeness) if profile.category_completeness else {}
            missing_critical = json.loads(profile.missing_critical_dimensions) if profile.missing_critical_dimensions else []

            # 构建建议行动
            suggested_actions = []
            if not profile.critical_dimensions_filled:
                suggested_actions.append("填写关键偏好信息（生育意愿、金钱观）")
            if profile.completeness_ratio < 0.3:
                suggested_actions.append("进行人格测试，解锁精准匹配")
            if profile.completeness_ratio < 0.5:
                suggested_actions.append("授权微信信息，补充画像")

            return ProfileStatusResponse(
                user_id=user_id,
                completeness_ratio=profile.completeness_ratio,
                recommended_strategy=profile.recommended_strategy,
                strategy_reason=_get_strategy_reason(profile.recommended_strategy, profile.completeness_ratio),
                critical_dimensions_filled=profile.critical_dimensions_filled,
                missing_critical=missing_critical,
                category_completeness=category_completeness,
                can_use_precise_match=profile.completeness_ratio >= 0.5,
                suggested_actions=suggested_actions
            )

    except Exception as e:
        logger.error(f"Get profile status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vector/{user_id}")
async def get_user_vector(
    user_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    获取用户向量画像

    返回144维向量及详情
    """
    try:
        with db_session() as db:
            profile = db.query(UserVectorProfileDB).filter(
                UserVectorProfileDB.user_id == user_id
            ).first()

            if not profile:
                return {
                    "success": False,
                    "error": "profile_not_found",
                    "message": "用户画像不存在"
                }

            vector = json.loads(profile.vector) if profile.vector else [0.0] * 144
            dimensions_detail = json.loads(profile.dimensions_detail) if profile.dimensions_detail else {}

            return {
                "success": True,
                "data": {
                    "user_id": user_id,
                    "vector": vector,
                    "dimensions_detail": dimensions_detail,
                    "completeness_ratio": profile.completeness_ratio,
                    "recommended_strategy": profile.recommended_strategy,
                    "updated_at": profile.updated_at.isoformat() if profile.updated_at else None
                }
            }

    except Exception as e:
        logger.error(f"Get user vector error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wechat-auth/{user_id}")
async def process_wechat_auth(
    user_id: str,
    request: WechatAuthRequest,
    authorization: Optional[str] = Header(None)
):
    """
    处理微信授权

    从微信数据推断用户画像
    """
    try:
        from services.third_party_auth_service import get_third_party_auth_service

        auth_service = get_third_party_auth_service()
        result = await auth_service.process_wechat_auth(
            user_id=user_id,
            auth_code=request.auth_code
        )

        # 更新用户画像
        if result.dimension_inferences:
            await _update_profile_from_inference(user_id, result.dimension_inferences)

        return {
            "success": True,
            "data": {
                "inferred_profile": result.inferred_profile,
                "dimensions_inferred": len(result.dimension_inferences),
                "data_summary": result.data_summary
            }
        }

    except Exception as e:
        logger.error(f"WeChat auth error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/game-test/start")
async def start_game_test(
    user_id: str = Query(..., description="用户ID"),
    test_type: str = Query(..., description="测试类型: personality, attachment, values"),
    authorization: Optional[str] = Header(None)
):
    """
    开始游戏化测试
    """
    try:
        from services.gamified_test_service import get_gamified_test_service, TestType

        test_service = get_gamified_test_service()
        result = test_service.start_test(
            user_id=user_id,
            test_type=TestType(test_type)
        )

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"Start game test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/game-test/answer")
async def submit_game_test_answer(
    user_id: str = Query(..., description="用户ID"),
    authorization: Optional[str] = Header(None),
    request: GameTestAnswerRequest = Body(...)
):
    """
    提交游戏测试答案
    """
    try:
        from services.gamified_test_service import get_gamified_test_service, TestType

        test_service = get_gamified_test_service()
        result = test_service.submit_answer(
            user_id=user_id,
            test_type=TestType(request.test_type),
            question_id=request.question_id,
            answer=request.answer
        )

        # 如果测试完成，更新画像
        if result.get("status") == "completed":
            await _save_game_test_result(user_id, request.test_type, result)
            await _update_profile_from_test(user_id, request.test_type, result.get("dimension_scores", {}))

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"Submit game test answer error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/game-test/skip")
async def skip_game_test(
    user_id: str = Query(..., description="用户ID"),
    test_type: str = Query(..., description="测试类型"),
    authorization: Optional[str] = Header(None)
):
    """
    跳过游戏测试
    """
    try:
        from services.gamified_test_service import get_gamified_test_service, TestType

        test_service = get_gamified_test_service()
        result = test_service.skip_test(
            user_id=user_id,
            test_type=TestType(test_type)
        )

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"Skip game test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/match/cold-start/{user_id}")
async def get_cold_start_recommendations(
    user_id: str,
    request: ColdStartMatchRequest,
    authorization: Optional[str] = Header(None)
):
    """
    获取冷启动匹配推荐

    根据画像完整度自动选择匹配策略
    """
    try:
        from services.cold_start_matching_service import get_cold_start_matcher
        from models.profile_vector_models import UserVectorProfile

        # 获取用户画像
        profile = await _get_or_create_profile(user_id)

        # 获取候选池（实际实现中从数据库获取）
        candidate_pool = await _get_candidate_pool(user_id, limit=100)

        # 执行匹配
        matcher = get_cold_start_matcher()
        result = await matcher.get_recommendations(
            user_id=user_id,
            profile=profile,
            candidate_pool=candidate_pool,
            limit=request.limit
        )

        return {
            "success": True,
            "data": {
                "strategy": result.strategy.value,
                "strategy_reason": result.strategy_reason,
                "profile_completeness": result.profile_completeness,
                "candidates": [
                    {
                        "user_id": c.user_id,
                        "score": c.score,
                        "match_type": c.match_type,
                        "reasoning": c.reasoning,
                        "confidence": c.confidence
                    }
                    for c in result.candidates
                ],
                "regions_count": result.regions_count
            }
        }

    except Exception as e:
        logger.error(f"Cold start match error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/infer-from-chat/{user_id}")
async def infer_profile_from_chat(
    user_id: str,
    conversation_id: str = Query(..., description="对话ID"),
    authorization: Optional[str] = Header(None)
):
    """
    从对话中推断用户画像

    AI分析对话内容，推断性格、价值观等维度
    """
    try:
        from services.profile_inference_service import get_profile_inferencer
        from api.conversations import get_conversation_messages  # 假设存在这个函数

        # 获取对话消息
        messages = await _get_conversation_messages(user_id, conversation_id)

        if not messages:
            return {
                "success": False,
                "error": "no_messages",
                "message": "没有足够的对话内容进行分析"
            }

        # 获取现有画像
        profile = await _get_or_create_profile(user_id)

        # 执行推断
        inferencer = get_profile_inferencer()
        result = await inferencer.infer_from_conversation(
            user_id=user_id,
            messages=messages,
            existing_profile=profile
        )

        # 更新画像
        if result.inferred_dimensions:
            await _update_profile_from_inference(user_id, result.inferred_dimensions)

        return {
            "success": True,
            "data": {
                "dimensions_inferred": len(result.inferred_dimensions),
                "overall_confidence": result.overall_confidence,
                "inference_method": result.inference_method,
                "sample_size": result.sample_size
            }
        }

    except Exception as e:
        logger.error(f"Infer from chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== AI Native 对话 API ==========

@router.post("/ai-opening/{user_id}")
async def generate_ai_opening(
    user_id: str,
    request: Dict[str, Any] = None,
    authorization: Optional[str] = Header(None)
):
    """
    AI 生成开场白

    根据用户画像状态，AI 主动决定如何引导对话
    """
    try:
        from services.profile_inference_service import get_profile_inferencer
        from models.profile_vector_models import UserVectorProfile

        # 获取画像状态
        profile_status = request.get("profile_status") if request else None

        # 获取或创建画像
        profile = await _get_or_create_profile(user_id)

        # 根据画像状态生成开场白
        if not profile_status:
            with db_session() as db:
                profile_db = db.query(UserVectorProfileDB).filter(
                    UserVectorProfileDB.user_id == user_id
                ).first()
                if profile_db:
                    profile_status = {
                        "completeness_ratio": profile_db.completeness_ratio,
                        "recommended_strategy": profile_db.recommended_strategy,
                        "critical_dimensions_filled": profile_db.critical_dimensions_filled,
                    }

        completeness = profile_status.get("completeness_ratio", 0) if profile_status else 0

        # AI 生成开场白
        if completeness < 0.2:
            message = "Hi！我是 Her，很高兴认识你~ 让我先了解一下你吧。你最想找什么样的关系呢？"
            ui_component = {
                "type": "quick_replies",
                "data": {
                    "options": [
                        {"text": "认真恋爱 💕", "value": "serious"},
                        {"text": "轻松约会 ☕", "value": "casual"},
                        {"text": "交朋友 🤝", "value": "friendship"},
                        {"text": "奔着结婚 💍", "value": "marriage"},
                    ]
                }
            }
        elif completeness < 0.5:
            message = "我注意到还有一些重要信息想了解。关于孩子，你是怎么想的呢？"
            ui_component = {
                "type": "quick_replies",
                "data": {
                    "options": [
                        {"text": "想要孩子 👶", "value": "want_children_yes"},
                        {"text": "不想要 🚫", "value": "want_children_no"},
                        {"text": "看情况 🤔", "value": "want_children_maybe"},
                    ]
                }
            }
        elif completeness < 0.8:
            message = "想更精准地帮你找到合适的人吗？玩个小游戏吧，只需要3分钟~"
            ui_component = {
                "type": "game_invite",
                "data": {
                    "game_type": "personality",
                    "reward": "解锁精准匹配"
                }
            }
        else:
            message = "我已经了解你不少了！现在可以给你推荐了，或者继续聊聊让我更懂你？"
            ui_component = {
                "type": "quick_replies",
                "data": {
                    "options": [
                        {"text": "开始匹配 🎯", "value": "start_match"},
                        {"text": "继续聊 💬", "value": "continue_chat"},
                    ]
                }
            }

        return {
            "success": True,
            "message": message,
            "ui_component": ui_component
        }

    except Exception as e:
        logger.error(f"Generate AI opening error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai-chat")
async def ai_chat(
    request: Dict[str, Any],
    authorization: Optional[str] = Header(None)
):
    """
    AI 对话分析

    分析用户消息，推断画像维度，生成回复
    """
    try:
        from services.profile_inference_service import get_profile_inferencer
        from models.profile_vector_models import DataSource

        user_id = request.get("user_id")
        message = request.get("message", "")
        conversation_history = request.get("conversation_history", [])

        if not message:
            return {"success": False, "error": "empty_message"}

        # 获取现有画像
        profile = await _get_or_create_profile(user_id)

        # 分析用户消息，推断维度
        inferred_dimensions = await _infer_from_message(message, profile)

        # 生成 AI 回复
        ai_response = await _generate_ai_response(
            message=message,
            profile=profile,
            conversation_history=conversation_history,
            inferred_dimensions=inferred_dimensions
        )

        # 更新画像
        if inferred_dimensions:
            await _update_profile_from_inference(user_id, inferred_dimensions)

        # 获取更新后的画像状态
        updated_status = await _get_profile_status_internal(user_id)

        return {
            "success": True,
            "message": ai_response["message"],
            "ui_component": ai_response.get("ui_component"),
            "inferred_dimensions": [
                {
                    "index": idx,
                    "name": _get_dimension_name(idx),
                    "value": dim.value,
                    "confidence": dim.confidence,
                    "source": dim.source.value if hasattr(dim.source, 'value') else str(dim.source)
                }
                for idx, dim in inferred_dimensions.items()
            ] if inferred_dimensions else [],
            "profile_status": updated_status
        }

    except Exception as e:
        logger.error(f"AI chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dimension/update")
async def update_dimension(
    request: Dict[str, Any],
    authorization: Optional[str] = Header(None)
):
    """
    用户手动修改维度值
    """
    try:
        user_id = request.get("user_id")
        dimension_index = request.get("dimension_index")
        value = request.get("value")

        if dimension_index is None or value is None:
            return {"success": False, "error": "missing_params"}

        # 更新画像
        with db_session() as db:
            profile_db = db.query(UserVectorProfileDB).filter(
                UserVectorProfileDB.user_id == user_id
            ).first()

            if profile_db:
                vector = json.loads(profile_db.vector) if profile_db.vector else [0.0] * 144
                if 0 <= dimension_index < 144:
                    vector[dimension_index] = value
                    profile_db.vector = json.dumps(vector)
                    db.commit()

        return {"success": True}

    except Exception as e:
        logger.error(f"Update dimension error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 辅助函数 ==========

async def _infer_from_message(message: str, profile) -> Dict:
    """从消息推断画像维度"""
    from models.profile_vector_models import DimensionValue, DataSource

    inferred = {}

    # 简单的关键词推断
    # 关系目标
    if "认真恋爱" in message or "恋爱" in message:
        inferred[0] = DimensionValue(value=0.8, confidence=0.9, source=DataSource.CONVERSATION)
    elif "轻松约会" in message or "约会" in message:
        inferred[0] = DimensionValue(value=0.5, confidence=0.9, source=DataSource.CONVERSATION)
    elif "交朋友" in message or "朋友" in message:
        inferred[0] = DimensionValue(value=0.3, confidence=0.9, source=DataSource.CONVERSATION)
    elif "结婚" in message:
        inferred[0] = DimensionValue(value=1.0, confidence=0.9, source=DataSource.CONVERSATION)

    # 生育意愿
    if "想要孩子" in message or "want_children_yes" in message:
        inferred[17] = DimensionValue(value=0.9, confidence=0.9, source=DataSource.CONVERSATION)
    elif "不想要孩子" in message or "want_children_no" in message:
        inferred[17] = DimensionValue(value=0.1, confidence=0.9, source=DataSource.CONVERSATION)
    elif "看情况" in message or "want_children_maybe" in message:
        inferred[17] = DimensionValue(value=0.5, confidence=0.9, source=DataSource.CONVERSATION)

    return inferred


async def _generate_ai_response(
    message: str,
    profile,
    conversation_history: List,
    inferred_dimensions: Dict
) -> Dict:
    """生成 AI 回复"""
    from models.profile_vector_models import DimensionValue, DataSource

    # 根据推断结果生成回复
    if inferred_dimensions:
        # 确认推断
        dim_names = [_get_dimension_name(idx) for idx in inferred_dimensions.keys()]
        response_message = f"好的，我记下了~"

        # 根据下一个需要收集的维度生成问题
        if 17 not in inferred_dimensions and 17 not in (profile.dimensions or {}):
            response_message += "\n\n关于孩子，你是怎么想的呢？"
            return {
                "message": response_message,
                "ui_component": {
                    "type": "quick_replies",
                    "data": {
                        "options": [
                            {"text": "想要孩子 👶", "value": "want_children_yes"},
                            {"text": "不想要 🚫", "value": "want_children_no"},
                            {"text": "看情况 🤔", "value": "want_children_maybe"},
                        ]
                    }
                }
            }
        else:
            # 显示推断结果卡片
            return {
                "message": response_message,
                "ui_component": {
                    "type": "dimension_card",
                    "data": {
                        "dimensions": [
                            {"index": idx, "name": _get_dimension_name(idx), "value": dim.value}
                            for idx, dim in inferred_dimensions.items()
                        ]
                    }
                }
            }

    # 默认回复
    return {
        "message": "嗯，继续说说看~",
        "ui_component": None
    }


def _get_dimension_name(index: int) -> str:
    """获取维度名称"""
    from models.profile_vector_models import DIMENSION_DEFINITIONS
    if index in DIMENSION_DEFINITIONS:
        return DIMENSION_DEFINITIONS[index].name
    return f"维度{index}"


async def _get_profile_status_internal(user_id: str) -> Dict:
    """获取画像状态（内部函数）"""
    with db_session() as db:
        profile_db = db.query(UserVectorProfileDB).filter(
            UserVectorProfileDB.user_id == user_id
        ).first()

        if not profile_db:
            return {
                "completeness_ratio": 0.0,
                "recommended_strategy": "cold_start",
                "critical_dimensions_filled": False,
            }

        return {
            "completeness_ratio": profile_db.completeness_ratio,
            "recommended_strategy": profile_db.recommended_strategy,
            "critical_dimensions_filled": profile_db.critical_dimensions_filled,
        }


# ========== 原有辅助函数 ==========

def _get_strategy_reason(strategy: str, completeness: float) -> str:
    """获取策略原因说明"""
    reasons = {
        "cold_start": f"画像完整度 {completeness:.0%}，信息不足，使用冷启动策略探索",
        "basic": f"画像完整度 {completeness:.0%}，使用基础规则匹配",
        "vector": f"画像完整度 {completeness:.0%}，使用向量匹配",
        "precise": f"画像完整度 {completeness:.0%}，画像完整，使用精准匹配"
    }
    return reasons.get(strategy, "未知策略")


async def _get_or_create_profile(user_id: str):
    """获取或创建用户画像"""
    from models.profile_vector_models import UserVectorProfile

    with db_session() as db:
        profile_db = db.query(UserVectorProfileDB).filter(
            UserVectorProfileDB.user_id == user_id
        ).first()

        if profile_db:
            # 从数据库加载
            profile = UserVectorProfile(user_id=user_id)
            profile.vector = json.loads(profile_db.vector) if profile_db.vector else [0.0] * 144
            # ... 加载其他字段
            return profile

        # 创建新画像
        profile = UserVectorProfile(user_id=user_id)
        return profile


async def _update_profile_from_inference(
    user_id: str,
    inferred_dimensions: Dict
):
    """从推断结果更新画像"""
    with db_session() as db:
        profile_db = db.query(UserVectorProfileDB).filter(
            UserVectorProfileDB.user_id == user_id
        ).first()

        if not profile_db:
            # 创建新记录
            profile_db = UserVectorProfileDB(
                user_id=user_id,
                vector=json.dumps([0.0] * 144),
                dimensions_detail="{}"
            )
            db.add(profile_db)

        # 更新向量
        vector = json.loads(profile_db.vector) if profile_db.vector else [0.0] * 144
        dimensions_detail = json.loads(profile_db.dimensions_detail) if profile_db.dimensions_detail else {}

        for idx, dim_value in inferred_dimensions.items():
            idx_int = int(idx)
            if 0 <= idx_int < 144:
                vector[idx_int] = dim_value.value
                dimensions_detail[str(idx_int)] = {
                    "value": dim_value.value,
                    "confidence": dim_value.confidence,
                    "source": dim_value.source.value if hasattr(dim_value.source, 'value') else str(dim_value.source),
                    "updated_at": dim_value.updated_at.isoformat() if dim_value.updated_at else None
                }

        profile_db.vector = json.dumps(vector)
        profile_db.dimensions_detail = json.dumps(dimensions_detail)

        # 更新完整度
        filled = len([v for v in vector if v != 0.0])
        profile_db.completeness_ratio = filled / 144

        # 更新策略
        if profile_db.completeness_ratio < 0.2:
            profile_db.recommended_strategy = "cold_start"
        elif profile_db.completeness_ratio < 0.5:
            profile_db.recommended_strategy = "basic"
        elif profile_db.completeness_ratio < 0.8:
            profile_db.recommended_strategy = "vector"
        else:
            profile_db.recommended_strategy = "precise"

        db.commit()


async def _save_game_test_result(user_id: str, test_type: str, result: Dict):
    """保存游戏测试结果"""
    with db_session() as db:
        record = GameTestRecordDB(
            user_id=user_id,
            test_type=test_type,
            dimension_scores=json.dumps(result.get("dimension_scores", {})),
            test_report=result.get("report"),
            reward_given=True,
            reward_type=result.get("reward", {}).get("feature")
        )
        db.add(record)
        db.commit()


async def _update_profile_from_test(user_id: str, test_type: str, dimension_scores: Dict):
    """从测试结果更新画像"""
    from models.profile_vector_models import DataSource

    inferred_dimensions = {}
    for idx, score in dimension_scores.items():
        from models.profile_vector_models import DimensionValue
        inferred_dimensions[idx] = DimensionValue(
            value=score,
            confidence=0.8,
            source=DataSource.GAME_TEST
        )

    await _update_profile_from_inference(user_id, inferred_dimensions)


async def _get_candidate_pool(user_id: str, limit: int = 100) -> List[Dict]:
    """获取候选池（简化实现）"""
    with db_session() as db:
        users = db.query(UserDB).filter(
            UserDB.id != user_id,
            UserDB.is_active == True
        ).limit(limit).all()

        return [
            {
                "user_id": u.id,
                "age": u.age,
                "gender": u.gender,
                "location": u.location,
                "profile": {}
            }
            for u in users
        ]


async def _get_conversation_messages(user_id: str, conversation_id: str) -> List[Dict]:
    """获取对话消息（简化实现）"""
    # 实际实现中从数据库获取
    return []