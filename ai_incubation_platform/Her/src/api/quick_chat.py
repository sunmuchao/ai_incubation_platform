"""
悬浮球快速对话 API

提供:
- 快速对话入口（用户问 Her 问题）
- 聊天回复建议生成
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional

from services.quick_chat_service import QuickChatService
from auth.jwt import get_current_user
from db.models import UserDB

router = APIRouter(prefix="/api/quick_chat", tags=["QuickChat"])


class QuickChatRequest(BaseModel):
    """快速对话请求"""
    question: str
    partnerId: str
    partnerName: str = "TA"
    recentMessages: List[Dict] = []


class QuickChatResponse(BaseModel):
    """快速对话响应"""
    answer: str
    suggestions: List[str] = []
    analysis: Dict = {}


class SuggestReplyRequest(BaseModel):
    """回复建议请求"""
    partnerId: str
    lastMessage: Dict
    recentMessages: List[Dict] = []
    relationshipStage: str = "初识"


class SuggestionItem(BaseModel):
    """回复建议项"""
    style: str
    content: str


class SuggestReplyResponse(BaseModel):
    """回复建议响应"""
    suggestions: List[SuggestionItem]


class FeedbackRequest(BaseModel):
    """反馈记录请求"""
    partnerId: str
    suggestionId: str
    feedbackType: str  # adopted/ignored/modified
    suggestionContent: str
    suggestionStyle: str
    userActualReply: Optional[str] = None


@router.post("", response_model=QuickChatResponse)
async def quick_chat(
    request: QuickChatRequest,
    current_user: UserDB = Depends(get_current_user),
):
    """
    悬浮球快速对话

    用户可以向 Her 提问关于匹配对象的问题，例如:
    - "她为什么不回我消息？"
    - "我该怎么回复她？"
    - "她对我有意思吗？"

    Her 会分析聊天上下文给出建议
    """
    try:
        service = QuickChatService()
        result = service.get_ai_advice(
            current_user_id=current_user.id,
            partner_id=request.partnerId,
            question=request.question,
            recent_messages=request.recentMessages,
        )

        return QuickChatResponse(
            answer=result.get("answer", ""),
            suggestions=result.get("suggestions", []),
            analysis=result.get("analysis", {}),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 思考失败：{str(e)}")


@router.post("/suggest_reply", response_model=SuggestReplyResponse)
async def suggest_reply(
    request: SuggestReplyRequest,
    current_user: UserDB = Depends(get_current_user),
):
    """
    生成回复建议

    当用户收到消息但不知道如何回复时，可以调用此接口
    AI 会生成 3 种不同风格的回复建议
    """
    try:
        service = QuickChatService()
        result = service.suggest_reply(
            current_user_id=current_user.id,
            partner_id=request.partnerId,
            last_message=request.lastMessage,
            recent_messages=request.recentMessages,
            relationship_stage=request.relationshipStage,
        )

        if not result.get("success", False):
            raise HTTPException(status_code=500, detail="生成建议失败")

        suggestions = [
            SuggestionItem(**s) for s in result.get("suggestions", [])
        ]

        return SuggestReplyResponse(suggestions=suggestions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成建议失败：{str(e)}")


@router.post("/feedback")
async def record_feedback(
    request: FeedbackRequest,
    current_user: UserDB = Depends(get_current_user),
):
    """
    记录用户对 AI 建议的反馈

    用于追踪 AI 建议的采纳情况和效果，持续优化 AI 策略
    """
    try:
        service = QuickChatService()
        feedback_id = service.record_suggestion_feedback(
            current_user_id=current_user.id,
            partner_id=request.partnerId,
            suggestion_id=request.suggestionId,
            feedback_type=request.feedbackType,
            suggestion_content=request.suggestionContent,
            suggestion_style=request.suggestionStyle,
            user_actual_reply=request.userActualReply,
        )

        return {"success": True, "feedback_id": feedback_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"记录反馈失败：{str(e)}")
