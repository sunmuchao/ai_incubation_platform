"""
AI Native 注册对话 API

提供 AI 红娘与注册用户的自然对话接口。
AI 主导对话流程，通过自然对话了解用户，而非机械化问答。

优化：
- 支持流式响应（SSE），提升用户体验
- 正确处理同步 LLM 调用在异步环境中的运行
"""
import asyncio
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import Dict, Optional, AsyncGenerator
from pydantic import BaseModel
from datetime import datetime

from db.database import get_db
from db.repositories import UserRepository
from services.ai_native_conversation_service import ai_native_conversation_service
from utils.logger import logger

router = APIRouter(prefix="/api/registration-conversation", tags=["registration-conversation"])


# ============= 请求/响应模型 =============

class StartConversationRequest(BaseModel):
    """开始对话请求"""
    user_id: str
    user_name: str


class StartConversationResponse(BaseModel):
    """开始对话响应"""
    success: bool
    session_id: str
    ai_message: str
    current_stage: str
    understanding_level: float
    collected_dimensions: list[str]


class SendMessageRequest(BaseModel):
    """发送消息请求"""
    user_id: str
    message: str


class SendMessageResponse(BaseModel):
    """发送消息响应"""
    success: bool
    ai_message: str
    current_stage: str
    is_completed: bool
    understanding_level: float
    collected_dimensions: list[str]
    conversation_count: int


class GetSessionResponse(BaseModel):
    """获取会话响应"""
    exists: bool
    user_id: Optional[str]
    user_name: Optional[str]
    is_completed: bool
    understanding_level: float
    collected_dimensions: list
    conversation_count: int


# ============= API 接口 =============

@router.post("/start", response_model=StartConversationResponse)
async def start_conversation(
    request: StartConversationRequest,
    db=Depends(get_db)
):
    """
    开始 AI Native 对话

    用户注册成功后，AI 红娘主动发起自然对话。
    AI 会像朋友一样聊天，逐步了解用户的喜好、期望和价值观。
    """
    logger.info(f"Starting AI Native conversation for user {request.user_id}")

    # 验证用户存在
    user_repo = UserRepository(db)
    db_user = user_repo.get_by_id(request.user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # 开始对话（在线程中运行同步方法，避免阻塞事件循环）
    result = await asyncio.to_thread(
        ai_native_conversation_service.start_conversation,
        request.user_id,
        request.user_name
    )

    logger.info(f"AI Native conversation started for user {request.user_id}")

    return StartConversationResponse(
        success=True,
        session_id=request.user_id,  # 使用 user_id 作为 session_id
        ai_message=result["ai_message"],
        current_stage=result.get("current_stage", "dynamic_conversation"),
        understanding_level=result["understanding_level"],
        collected_dimensions=result["collected_dimensions"],
    )


@router.post("/message", response_model=SendMessageResponse)
async def send_message(
    request: SendMessageRequest,
    db=Depends(get_db)
):
    """
    发送对话消息

    用户与 AI 红娘自然聊天，AI 会在对话中了解用户。
    不需要遵循固定流程，像和朋友聊天一样就好。
    """
    logger.info(f"Received message from user {request.user_id}: {request.message[:50]}...")

    # 处理用户消息（在线程中运行同步方法，避免阻塞事件循环）
    result = await asyncio.to_thread(
        ai_native_conversation_service.process_user_message,
        request.user_id,
        request.message
    )

    # 如果对话完成，更新用户数据到数据库
    if result.get("is_completed"):
        logger.info(f"AI Native conversation completed for user {request.user_id}")

        # 获取会话详情，提取数据
        session_status = ai_native_conversation_service.get_session_status(request.user_id)

        # 将收集的数据保存到用户数据库记录
        # 解析 collected_dimensions 中的数据结构并保存到 UserPreferenceDB
        _save_collected_data_to_db(
            user_id=request.user_id,
            session_status=session_status,
            db=db
        )

    return SendMessageResponse(
        success=True,
        ai_message=result["ai_message"],
        current_stage=result.get("current_stage", "dynamic_conversation"),
        is_completed=result.get("is_completed", False),
        understanding_level=result.get("understanding_level", 0.0),
        collected_dimensions=result.get("collected_dimensions", []),
        conversation_count=result.get("conversation_count", 0),
    )


@router.post("/message/stream")
async def send_message_stream(
    request: SendMessageRequest,
    db=Depends(get_db)
):
    """
    发送对话消息（流式响应）

    使用 SSE (Server-Sent Events) 实现流式输出，
    让用户看到 AI 逐字生成回复，提升体验。
    """
    logger.info(f"Received streaming message from user {request.user_id}")

    async def generate() -> AsyncGenerator[str, None]:
        """生成 SSE 流"""
        try:
            # 流式处理用户消息
            async for chunk in ai_native_conversation_service.process_user_message_stream(
                user_id=request.user_id,
                user_message=request.message
            ):
                # SSE 格式: data: {json}\n\n
                import json
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

            # 对话完成时保存数据
            session_status = ai_native_conversation_service.get_session_status(request.user_id)
            if session_status.get("is_completed"):
                _save_collected_data_to_db(
                    user_id=request.user_id,
                    session_status=session_status,
                    db=db
                )

        except Exception as e:
            logger.error(f"Stream error: {e}")
            import json
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


def _save_collected_data_to_db(user_id: str, session_status: dict, db) -> None:
    """
    将 AI 对话收集的数据保存到数据库

    Args:
        user_id: 用户 ID
        session_status: 会话状态数据
        db: 数据库会话
    """
    try:
        from db.models import UserPreferenceDB
        from datetime import datetime

        # 检查是否已有偏好记录
        preference = db.query(UserPreferenceDB).filter(
            UserPreferenceDB.user_id == user_id
        ).first()

        # 从 collected_dimensions 提取数据
        collected_dims = session_status.get("collected_dimensions", [])
        extracted_data = {}

        for dim in collected_dims:
            dim_name = dim.get("name", "")
            dim_value = dim.get("value", {})
            dim_confidence = dim.get("confidence", 0.5)

            # 只保存高置信度的数据
            if dim_confidence >= 0.7:
                if "age" in dim_name.lower():
                    extracted_data["preferred_age_range"] = dim_value.get("range", [18, 60])
                elif "location" in dim_name.lower():
                    extracted_data["preferred_location_range"] = dim_value.get("distance", 50)
                elif "education" in dim_name.lower():
                    extracted_data["preferred_education"] = dim_value.get("levels", [])

        if not preference and extracted_data:
            # 创建新记录
            preference = UserPreferenceDB(
                id=f"pref-{user_id}-{datetime.now().timestamp()}",
                user_id=user_id,
                preferred_age_range=extracted_data.get("preferred_age_range", [18, 60]),
                preferred_location_range=extracted_data.get("preferred_location_range", 50),
                preferred_education=str(extracted_data.get("preferred_education", []))
            )
            db.add(preference)
            logger.info(f"RegistrationConversation: Created preference for user={user_id}")
        elif preference and extracted_data:
            # 更新现有记录
            if "preferred_age_range" in extracted_data:
                preference.preferred_age_range = extracted_data["preferred_age_range"]
            if "preferred_location_range" in extracted_data:
                preference.preferred_location_range = extracted_data["preferred_location_range"]
            if "preferred_education" in extracted_data:
                preference.preferred_education = str(extracted_data["preferred_education"])
            preference.updated_at = datetime.now()
            logger.info(f"RegistrationConversation: Updated preference for user={user_id}")

        db.commit()

    except Exception as e:
        logger.error(f"RegistrationConversation: Failed to save collected data: {e}")
        db.rollback()


@router.get("/session/{user_id}", response_model=GetSessionResponse)
async def get_session(user_id: str):
    """
    获取用户对话会话状态

    返回 AI 对用户的了解程度和已收集的维度信息。
    """
    result = ai_native_conversation_service.get_session_status(user_id)

    if not result.get("exists"):
        return GetSessionResponse(
            exists=False,
            user_id=None,
            user_name=None,
            is_completed=False,
            understanding_level=0.0,
            collected_dimensions=[],
            conversation_count=0,
        )

    return GetSessionResponse(
        exists=True,
        user_id=result.get("user_id"),
        user_name=result.get("user_name"),
        is_completed=result.get("is_completed", False),
        understanding_level=result.get("understanding_level", 0.0),
        collected_dimensions=result.get("collected_dimensions", []),
        conversation_count=result.get("conversation_count", 0),
    )


@router.post("/complete/{user_id}")
async def complete_conversation(user_id: str):
    """
    完成对话（用户主动结束）

    用户可以随时主动结束对话，AI 会保存已收集的信息。
    """
    result = ai_native_conversation_service.get_session_status(user_id)

    if result.get("exists"):
        ai_native_conversation_service.sessions[user_id].is_completed = True
        logger.info(f"Conversation marked as completed for user {user_id}")

    return {
        "success": True,
        "message": "Conversation completed",
        "understanding_level": result.get("understanding_level", 0.0),
    }
