"""
对话匹配 API - 对话为唯一入口

替换之前的 IntentRouter + DeerFlow + 双引擎架构
统一为 ConversationMatchService

核心端点：
- POST /api/her/chat: 对话匹配（唯一入口）
- POST /api/her/analyze-bias: 认知偏差分析
- POST /api/her/match-advice: 获取匹配建议
- GET /api/her/profile: 获取用户画像

设计原则：
- 对话为唯一入口：所有匹配请求通过对话完成
- Her 专业判断：认知偏差识别 + 匹配建议
- 主动建议：搜索时给出专业意见
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

from utils.logger import logger


router = APIRouter(prefix="/api/her", tags=["her-advisor"])


# ========== 请求/响应模型 ==========

class HerChatRequest(BaseModel):
    """对话匹配请求"""
    message: str
    user_id: Optional[str] = None
    thread_id: Optional[str] = None
    message_history: Optional[List[Dict[str, Any]]] = None


class HerChatResponse(BaseModel):
    """对话匹配响应"""
    ai_message: str
    intent_type: str

    # 匹配结果
    matches: Optional[List[Dict[str, Any]]] = None

    # 认知偏差分析
    bias_analysis: Optional[Dict[str, Any]] = None

    # 主动建议
    proactive_suggestion: Optional[Dict[str, Any]] = None

    # Generative UI
    generative_ui: Optional[Dict[str, Any]] = None

    # 建议操作
    suggested_actions: Optional[List[Dict[str, str]]] = None


class AnalyzeBiasRequest(BaseModel):
    """认知偏差分析请求"""
    user_id: str


class AnalyzeBiasResponse(BaseModel):
    """认知偏差分析响应"""
    has_bias: bool
    bias_type: Optional[str] = None
    bias_description: Optional[str] = None
    actual_suitable_type: Optional[str] = None
    potential_risks: Optional[List[str]] = None
    adjustment_suggestion: Optional[str] = None
    confidence: float


class MatchAdviceRequest(BaseModel):
    """匹配建议请求"""
    user_id_a: str
    user_id_b: str


class MatchAdviceResponse(BaseModel):
    """匹配建议响应"""
    advice_type: str
    advice_content: str
    reasoning: Optional[str] = None
    suggestions_for_user: Optional[List[str]] = None
    potential_issues: Optional[List[str]] = None
    compatibility_score: float


class UserProfileResponse(BaseModel):
    """用户画像响应"""
    user_id: str
    self_profile: Dict[str, Any]
    desire_profile: Dict[str, Any]
    self_profile_confidence: float
    desire_profile_confidence: float
    self_profile_completeness: float
    desire_profile_completeness: float


class RecordBehaviorEventRequest(BaseModel):
    """记录行为事件请求"""
    user_id: str
    event_type: str
    event_data: Optional[Dict[str, Any]] = None
    target_user_id: Optional[str] = None


class RecordBehaviorEventResponse(BaseModel):
    """记录行为事件响应"""
    success: bool
    updated_dimensions: Optional[List[str]] = None


# ========== API 端点 ==========

@router.post("/chat")
async def her_chat(
    request: HerChatRequest,
    authorization: Optional[str] = Header(None)
) -> HerChatResponse:
    """
    Her 对话匹配 - 唯一入口

    所有匹配请求都通过对话完成：
    1. 用户自然语言描述需求
    2. Her 理解意图并执行匹配
    3. Her 分析认知偏差
    4. Her 给出专业建议
    5. Her 输出主动建议

    这是替换之前 IntentRouter + DeerFlow + 双引擎的统一入口

    Args:
        request: 对话请求（消息、用户ID、历史）
        authorization: JWT token

    Returns:
        HerChatResponse: AI消息 + 匹配结果 + 认知偏差 + 主动建议
    """
    try:
        # 获取用户 ID
        user_id = request.user_id
        if not user_id and authorization:
            user_id = _extract_user_id_from_token(authorization)

        if not user_id:
            user_id = "user-anonymous-dev"

        logger.info(f"[HerAPI] 用户 {user_id} 发送消息: {request.message[:50]}...")

        # 调用对话匹配服务
        from services.conversation_match_service import get_conversation_match_service

        service = get_conversation_match_service()
        result = await service.process_message(
            user_id=user_id,
            message=request.message,
            conversation_history=request.message_history,
        )

        # 构建响应
        return HerChatResponse(
            ai_message=result.ai_message,
            intent_type=result.intent_type,
            matches=[
                {
                    "id": m.candidate_id,
                    "name": m.candidate_name,
                    "score": m.compatibility_score,
                    "reasoning": m.match_reasoning,
                    "her_advice": m.her_advice.to_dict() if m.her_advice else None,
                    "risk_warnings": m.risk_warnings,
                }
                for m in result.matches
            ] if result.matches else None,
            bias_analysis=result.bias_analysis.to_dict() if result.bias_analysis else None,
            proactive_suggestion=result.proactive_suggestion.to_dict() if result.proactive_suggestion else None,
            generative_ui=result.generative_ui,
            suggested_actions=result.suggested_actions,
        )

    except Exception as e:
        logger.error(f"[HerAPI] 对话匹配失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-bias")
async def analyze_bias(
    request: AnalyzeBiasRequest,
    authorization: Optional[str] = Header(None)
) -> AnalyzeBiasResponse:
    """
    认知偏差分析

    让 Her 分析用户的认知偏差：
    - 用户想要的 ≠ 用户适合的

    注意：认知偏差识别由 LLM 自主判断，不硬编码规则

    Args:
        request: 分析请求（用户ID）
        authorization: JWT token

    Returns:
        AnalyzeBiasResponse: 认知偏差分析结果
    """
    try:
        user_id = request.user_id
        if not user_id and authorization:
            user_id = _extract_user_id_from_token(authorization)

        if not user_id:
            raise HTTPException(status_code=400, detail="需要提供用户ID")

        logger.info(f"[HerAPI] 分析用户 {user_id} 的认知偏差")

        # 获取用户画像
        from services.user_profile_service import get_user_profile_service
        from services.her_advisor_service import get_her_advisor_service

        profile_service = get_user_profile_service()
        her_advisor = get_her_advisor_service()

        self_profile, desire_profile = await profile_service.get_or_create_profile(user_id)

        # 分析认知偏差
        bias_analysis = await her_advisor.analyze_user_bias(
            user_id, self_profile, desire_profile
        )

        return AnalyzeBiasResponse(
            has_bias=bias_analysis.has_bias,
            bias_type=bias_analysis.bias_type,
            bias_description=bias_analysis.bias_description,
            actual_suitable_type=bias_analysis.actual_suitable_type,
            potential_risks=bias_analysis.potential_risks,
            adjustment_suggestion=bias_analysis.adjustment_suggestion,
            confidence=bias_analysis.confidence,
        )

    except Exception as e:
        logger.error(f"[HerAPI] 认知偏差分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/match-advice")
async def get_match_advice(
    request: MatchAdviceRequest,
    authorization: Optional[str] = Header(None)
) -> MatchAdviceResponse:
    """
    获取匹配建议

    让 Her 分析两个用户的匹配度并给出专业建议

    Args:
        request: 建议请求（用户A ID、用户B ID）
        authorization: JWT token

    Returns:
        MatchAdviceResponse: Her 专业匹配建议
    """
    try:
        logger.info(f"[HerAPI] 分析 {request.user_id_a} 和 {request.user_id_b} 的匹配建议")

        from services.user_profile_service import get_user_profile_service
        from services.her_advisor_service import get_her_advisor_service
        # 注：matchmaker 已废弃，使用 AI 判断匹配度

        profile_service = get_user_profile_service()
        her_advisor = get_her_advisor_service()

        # 获取两个用户的画像
        self_a, desire_a = await profile_service.get_or_create_profile(request.user_id_a)
        self_b, desire_b = await profile_service.get_or_create_profile(request.user_id_b)

        # 使用 AI 判断匹配度（不再使用数值计算）
        score = 0.5  # 默认分数，实际由 AI 在 generate_match_advice 中判断

        # 生成 Her 建议
        advice = await her_advisor.generate_match_advice(
            request.user_id_a,
            (self_a, desire_a),
            request.user_id_b,
            (self_b, desire_b),
            score,
        )

        return MatchAdviceResponse(
            advice_type=advice.advice_type,
            advice_content=advice.advice_content,
            reasoning=advice.reasoning,
            suggestions_for_user=advice.suggestions_for_user,
            potential_issues=advice.potential_issues,
            compatibility_score=advice.compatibility_score,
        )

    except Exception as e:
        logger.error(f"[HerAPI] 匹配建议生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/{user_id}")
async def get_user_profile(
    user_id: str,
    authorization: Optional[str] = Header(None)
) -> UserProfileResponse:
    """
    获取用户画像

    返回双向画像：SelfProfile + DesireProfile

    Args:
        user_id: 用户ID
        authorization: JWT token

    Returns:
        UserProfileResponse: 完整用户画像
    """
    try:
        logger.info(f"[HerAPI] 获取用户 {user_id} 的画像")

        from services.user_profile_service import get_user_profile_service

        profile_service = get_user_profile_service()
        self_profile, desire_profile = await profile_service.get_or_create_profile(user_id)

        return UserProfileResponse(
            user_id=user_id,
            self_profile=self_profile.to_dict(),
            desire_profile=desire_profile.to_dict(),
            self_profile_confidence=self_profile.profile_confidence,
            desire_profile_confidence=desire_profile.preference_confidence,
            self_profile_completeness=profile_service._calculate_self_profile_completeness(self_profile),
            desire_profile_completeness=profile_service._calculate_desire_profile_completeness(desire_profile),
        )

    except Exception as e:
        logger.error(f"[HerAPI] 获取用户画像失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/behavior-event")
async def record_behavior_event(
    request: RecordBehaviorEventRequest,
    authorization: Optional[str] = Header(None)
) -> RecordBehaviorEventResponse:
    """
    记录行为事件

    行为事件用于更新用户画像：
    - 搜索行为 → 更新 DesireProfile
    - 点击行为 → 更新 DesireProfile
    - 消息行为 → 更新 SelfProfile
    - 反馈行为 → 更新双向画像

    Args:
        request: 行为事件请求
        authorization: JWT token

    Returns:
        RecordBehaviorEventResponse: 更新结果
    """
    try:
        user_id = request.user_id
        if not user_id and authorization:
            user_id = _extract_user_id_from_token(authorization)

        if not user_id:
            raise HTTPException(status_code=400, detail="需要提供用户ID")

        logger.info(f"[HerAPI] 用户 {user_id} 行为事件: {request.event_type}")

        from services.user_profile_service import get_profile_update_engine

        update_engine = get_profile_update_engine()

        success = await update_engine.process_behavior_event(
            user_id=user_id,
            event_type=request.event_type,
            event_data=request.event_data or {},
            target_user_id=request.target_user_id,
        )

        return RecordBehaviorEventResponse(
            success=success,
            updated_dimensions=[],  # 可以扩展返回更新的维度
        )

    except Exception as e:
        logger.error(f"[HerAPI] 记录行为事件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-cases")
async def get_knowledge_cases(
    case_type: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    获取 Her 知识库案例

    用于展示 Her 的专业知识能力

    Args:
        case_type: 案例类型过滤（warning_case, success_case, typical_pattern）
        limit: 返回数量限制

    Returns:
        案例列表
    """
    try:
        from utils.db_session_manager import db_session_readonly
        from models.her_advisor_models import HerKnowledgeCaseDB

        with db_session_readonly() as db:
            query = db.query(HerKnowledgeCaseDB).filter(HerKnowledgeCaseDB.is_active == True)

            if case_type:
                query = query.filter(HerKnowledgeCaseDB.case_type == case_type)

            cases = query.order_by(HerKnowledgeCaseDB.usage_count.desc()).limit(limit).all()

            return [
                {
                    "id": case.id,
                    "case_type": case.case_type,
                    "tags": json.loads(case.tags) if case.tags else [],
                    "case_description": case.case_description,
                    "her_analysis": case.her_analysis,
                    "her_suggestion": case.her_suggestion,
                    "key_insights": json.loads(case.key_insights) if case.key_insights else [],
                }
                for case in cases
            ]

    except Exception as e:
        logger.error(f"[HerAPI] 获取知识库案例失败: {e}")
        return []


@router.get("/health")
async def her_health_check():
    """
    Her 顾问服务健康检查

    检查：
    - 服务是否初始化
    - LLM 是否可用
    - 数据表是否创建
    """
    try:
        from services.her_advisor_service import get_her_advisor_service
        from services.user_profile_service import get_user_profile_service
        from services.conversation_match_service import get_conversation_match_service
        from services.llm_semantic_service import get_llm_semantic_service

        # 检查服务初始化
        her_advisor = get_her_advisor_service()
        profile_service = get_user_profile_service()
        conversation_service = get_conversation_match_service()
        llm_service = get_llm_semantic_service()

        return {
            "status": "healthy",
            "services": {
                "her_advisor": "initialized",
                "user_profile": "initialized",
                "conversation_match": "initialized",
                "llm": "enabled" if llm_service.enabled else "disabled",
            },
            "features": [
                "对话为唯一入口",
                "双向动态画像",
                "认知偏差识别（LLM自主判断）",
                "Her专业匹配建议",
                "主动建议系统",
            ],
        }

    except Exception as e:
        logger.error(f"[HerAPI] 健康检查失败: {e}")
        return {
            "status": "degraded",
            "error": str(e),
        }


# ========== 辅助函数 ==========

def _extract_user_id_from_token(authorization: str) -> Optional[str]:
    """从 token 中提取用户 ID"""
    try:
        from auth.jwt import decode_access_token
        if authorization.startswith("Bearer "):
            token = authorization[7:]
            user_id = decode_access_token(token)
            logger.debug(f"[HerAPI] Token 解析结果: user_id={user_id}")
            return user_id
    except Exception as e:
        logger.warning(f"[HerAPI] Token 解析失败: {e}")
        pass
    return None