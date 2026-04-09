"""
AI 预沟通 API

提供 AI 替身代聊功能的 HTTP 接口
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from db.database import get_db
from auth.jwt import get_current_user
from services.ai_interlocutor_service import AIInterlocutorService, get_ai_interlocutor_service
from db.models import AIPreCommunicationSessionDB, AIPreCommunicationMessageDB
from utils.logger import logger


router = APIRouter(prefix="/api/ai/interlocutor", tags=["AI 预沟通"])


# ============= Pydantic 模型 =============

class PreCommunicationStartRequest(BaseModel):
    """启动预沟通请求"""
    target_user_id: str = Field(..., description="目标用户 ID")
    target_rounds: int = Field(default=50, description="目标对话轮数")


class PreCommunicationResponse(BaseModel):
    """预沟通响应"""
    session_id: str
    status: str
    hard_check_passed: bool
    values_check_passed: bool
    conversation_rounds: int
    compatibility_score: Optional[float]
    recommendation: Optional[str]
    created_at: str


class PreCommunicationStatusResponse(BaseModel):
    """预沟通状态响应"""
    session_id: str
    status: str
    user_id_1: str
    user_id_2: str
    hard_check_result: Optional[dict]
    values_check_result: Optional[dict]
    conversation_rounds: int
    target_rounds: int
    compatibility_score: Optional[float]
    compatibility_report: Optional[dict]
    extracted_insights: Optional[dict]
    recommendation: Optional[str]
    recommendation_reason: Optional[str]
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]


class PreCommunicationMessageResponse(BaseModel):
    """对话消息响应"""
    id: str
    session_id: str
    sender_agent: str
    content: str
    message_type: str
    topic_tag: Optional[str]
    round_number: int
    created_at: str


# ============= API 端点 =============

@router.post("/start", response_model=PreCommunicationResponse, summary="启动 AI 预沟通")
async def start_pre_communication(
    request: PreCommunicationStartRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    启动 AI 预沟通会话

    AI 替身将代替用户与对方进行深度对话，提取关键信息并生成匹配度报告。

    - **target_user_id**: 目标用户 ID
    - **target_rounds**: 目标对话轮数（默认 50 轮）

    返回：
    - session_id: 会话 ID
    - status: 会话状态
    - hard_check_passed: 硬指标校验结果
    - values_check_passed: 价值观底线探测结果
    - recommendation: 推送建议（recommend/silent/wait）
    """
    user_id = current_user.get("user_id")
    logger.info(f"Start pre-communication: {user_id} -> {request.target_user_id}")

    # 检查是否已存在进行中的会话
    existing = db.query(AIPreCommunicationSessionDB).filter(
        ((AIPreCommunicationSessionDB.user_id_1 == user_id) &
         (AIPreCommunicationSessionDB.user_id_2 == request.target_user_id)) |
        ((AIPreCommunicationSessionDB.user_id_1 == request.target_user_id) &
         (AIPreCommunicationSessionDB.user_id_2 == user_id))
    ).filter(
        AIPreCommunicationSessionDB.status.in_(["pending", "chatting"])
    ).first()

    if existing:
        return PreCommunicationResponse(
            session_id=existing.id,
            status=existing.status,
            hard_check_passed=existing.hard_check_passed,
            values_check_passed=existing.values_check_passed,
            conversation_rounds=existing.conversation_rounds,
            compatibility_score=existing.compatibility_score,
            recommendation=existing.recommendation,
            created_at=str(existing.created_at)
        )

    # 启动预沟通
    service = AIInterlocutorService(db)
    session = await service.start_pre_communication(
        user_id_1=user_id,
        user_id_2=request.target_user_id,
        target_rounds=request.target_rounds
    )

    return PreCommunicationResponse(
        session_id=session.id,
        status=session.status,
        hard_check_passed=session.hard_check_passed,
        values_check_passed=session.values_check_passed,
        conversation_rounds=session.conversation_rounds,
        compatibility_score=session.compatibility_score,
        recommendation=session.recommendation,
        created_at=str(session.created_at)
    )


@router.get("/session/{session_id}", response_model=PreCommunicationStatusResponse, summary="获取预沟通状态")
async def get_pre_communication_status(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取 AI 预沟通会话状态

    返回详细的会话信息，包括：
    - 硬指标校验结果
    - 价值观探测结果
    - 对话进度
    - 提取的关键信息
    - 匹配度报告
    - 推送建议
    """
    user_id = current_user.get("user_id")

    session = db.query(AIPreCommunicationSessionDB).filter(
        AIPreCommunicationSessionDB.id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 权限检查：只有会话双方可以查看
    if session.user_id_1 != user_id and session.user_id_2 != user_id:
        raise HTTPException(status_code=403, detail="无权查看此会话")

    return PreCommunicationStatusResponse(
        session_id=session.id,
        status=session.status,
        user_id_1=session.user_id_1,
        user_id_2=session.user_id_2,
        hard_check_result=session.hard_check_result,
        values_check_result=session.values_check_result,
        conversation_rounds=session.conversation_rounds,
        target_rounds=session.target_rounds,
        compatibility_score=session.compatibility_score,
        compatibility_report=session.compatibility_report,
        extracted_insights=session.extracted_insights,
        recommendation=session.recommendation,
        recommendation_reason=session.recommendation_reason,
        created_at=str(session.created_at),
        started_at=str(session.started_at) if session.started_at else None,
        completed_at=str(session.completed_at) if session.completed_at else None
    )


@router.get("/sessions", response_model=List[PreCommunicationStatusResponse], summary="获取我的预沟通会话列表")
async def get_my_pre_communication_sessions(
    status_filter: Optional[str] = Query(default=None, description="状态过滤：pending/chatting/completed/cancelled"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取用户的 AI 预沟通会话列表

    可按状态过滤，返回会话摘要信息
    """
    user_id = current_user.get("user_id")

    query = db.query(AIPreCommunicationSessionDB).filter(
        (AIPreCommunicationSessionDB.user_id_1 == user_id) |
        (AIPreCommunicationSessionDB.user_id_2 == user_id)
    )

    if status_filter:
        query = query.filter(AIPreCommunicationSessionDB.status == status_filter)

    sessions = query.order_by(AIPreCommunicationSessionDB.created_at.desc()).all()

    return [
        PreCommunicationStatusResponse(
            session_id=s.id,
            status=s.status,
            user_id_1=s.user_id_1,
            user_id_2=s.user_id_2,
            hard_check_result=s.hard_check_result,
            values_check_result=s.values_check_result,
            conversation_rounds=s.conversation_rounds,
            target_rounds=s.target_rounds,
            compatibility_score=s.compatibility_score,
            compatibility_report=s.compatibility_report,
            extracted_insights=s.extracted_insights,
            recommendation=s.recommendation,
            recommendation_reason=s.recommendation_reason,
            created_at=str(s.created_at),
            started_at=str(s.started_at) if s.started_at else None,
            completed_at=str(s.completed_at) if s.completed_at else None
        )
        for s in sessions
    ]


@router.get("/session/{session_id}/messages", response_model=List[PreCommunicationMessageResponse], summary="获取对话历史")
async def get_pre_communication_messages(
    session_id: str,
    limit: int = Query(default=100, description="返回消息数量"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取 AI 预沟通对话历史

    返回对话消息列表，用于查看 AI 替身的对话内容
    """
    user_id = current_user.get("user_id")

    session = db.query(AIPreCommunicationSessionDB).filter(
        AIPreCommunicationSessionDB.id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 权限检查
    if session.user_id_1 != user_id and session.user_id_2 != user_id:
        raise HTTPException(status_code=403, detail="无权查看此对话")

    messages = db.query(AIPreCommunicationMessageDB).filter(
        AIPreCommunicationMessageDB.session_id == session_id
    ).order_by(
        AIPreCommunicationMessageDB.round_number.asc()
    ).limit(limit).all()

    return [
        PreCommunicationMessageResponse(
            id=m.id,
            session_id=m.session_id,
            sender_agent=m.sender_agent,
            content=m.content,
            message_type=m.message_type,
            topic_tag=m.topic_tag,
            round_number=m.round_number,
            created_at=str(m.created_at)
        )
        for m in messages
    ]


@router.post("/session/{session_id}/cancel", summary="取消预沟通会话")
async def cancel_pre_communication(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    取消进行中的 AI 预沟通会话

    只能取消 pending 或 chatting 状态的会话
    """
    user_id = current_user.get("user_id")

    session = db.query(AIPreCommunicationSessionDB).filter(
        AIPreCommunicationSessionDB.id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 权限检查
    if session.user_id_1 != user_id and session.user_id_2 != user_id:
        raise HTTPException(status_code=403, detail="无权操作此会话")

    # 状态检查
    if session.status not in ["pending", "chatting"]:
        raise HTTPException(status_code=400, detail=f"无法取消状态为{session.status}的会话")

    session.status = "cancelled"
    db.commit()

    logger.info(f"Pre-communication session cancelled: {session_id} by {user_id}")

    return {"success": True, "message": "会话已取消"}


@router.get("/recommendations", summary="获取推荐开启人工对话的会话")
async def get_recommended_sessions(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取推荐开启人工对话的会话列表

    返回匹配度>=85% 且建议推送的会话
    """
    user_id = current_user.get("user_id")

    sessions = db.query(AIPreCommunicationSessionDB).filter(
        (
            (AIPreCommunicationSessionDB.user_id_1 == user_id) |
            (AIPreCommunicationSessionDB.user_id_2 == user_id)
        ) &
        (AIPreCommunicationSessionDB.status == "completed") &
        (AIPreCommunicationSessionDB.recommendation == "recommend")
    ).order_by(
        AIPreCommunicationSessionDB.compatibility_score.desc()
    ).all()

    result = []
    for session in sessions:
        partner_id = session.user_id_2 if session.user_id_1 == user_id else session.user_id_1

        # 获取对方信息
        from db.repositories import UserRepository
        user_repo = UserRepository(db)
        partner = user_repo.get_by_id(partner_id)

        result.append({
            "session_id": session.id,
            "partner_id": partner_id,
            "partner_name": partner.name if partner else "未知",
            "compatibility_score": session.compatibility_score,
            "recommendation_reason": session.recommendation_reason,
            "completed_at": str(session.completed_at)
        })

    return result
