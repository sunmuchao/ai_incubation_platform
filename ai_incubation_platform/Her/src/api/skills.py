"""
Agent Skill API

提供 Agent Skill 的 HTTP 接口

P0 增强：
- 流式 Skill 执行 (SSE) - 降低用户感知延迟
- 敏感信息过滤 - 隐私保护
"""
from fastapi import APIRouter, HTTPException, Depends, Body, Request
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Dict, Any, Optional, List, AsyncGenerator
from pydantic import BaseModel
import json
import time
import asyncio
from utils.logger import logger
from auth.jwt import get_current_user_optional
from agent.skills import get_skill_registry, get_skill_info, list_all_skills

router = APIRouter(prefix="/api/skills", tags=["skills"])


# ============= 请求/响应模型 =============

class SkillExecuteRequest(BaseModel):
    """Skill 执行请求"""
    skill_name: str
    params: Dict[str, Any] = {}
    context: Optional[Dict[str, Any]] = None


class SkillExecuteStreamRequest(BaseModel):
    """Skill 流式执行请求"""
    skill_name: str
    params: Dict[str, Any] = {}
    context: Optional[Dict[str, Any]] = None
    enable_sensitive_filter: bool = True  # 是否启用敏感信息过滤


class SkillInfo(BaseModel):
    """Skill 信息"""
    name: str
    description: str
    version: str
    priority: str
    category: str
    available: bool


class SkillListResponse(BaseModel):
    """Skill 列表响应"""
    success: bool
    skills: List[SkillInfo]
    total: int


class SkillExecuteResponse(BaseModel):
    """Skill 执行响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    ai_message: Optional[str] = None


# ============= SSE 流式执行端点 =============

@router.post("/{skill_name}/execute/stream")
async def execute_skill_stream(
    skill_name: str,
    request: SkillExecuteStreamRequest,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    流式执行 Skill（Server-Sent Events）

    降低用户感知延迟，边执行边返回进度

    流程：
    1. 意图理解中
    2. 执行 Skill
    3. 生成响应
    4. 选择 UI 组件
    5. 完成
    """
    user_id = current_user.get("user_id") if current_user else None
    is_anonymous = current_user.get("is_anonymous", True) if current_user else True

    logger.info(f"Skill SSE: Starting stream execution of {skill_name} for user={user_id}")

    # 获取注册表
    registry = get_skill_registry()

    # 检查 Skill 是否存在
    skill = registry.get(skill_name)
    if not skill:
        return StreamingResponse(
            _sse_event("error", json.dumps({"error": f"Skill not found: {skill_name}"})),
            media_type="text/event-stream"
        )

    # 添加用户上下文
    params = request.params or {}
    if "user_id" not in params and user_id:
        params["user_id"] = user_id

    context = request.context or {}
    if "user_id" not in context and user_id:
        context["user_id"] = user_id

    async def generate_stream() -> AsyncGenerator[str, None]:
        """生成 SSE 事件流"""
        try:
            # 阶段 1: 意图理解中
            yield _sse_event("status", json.dumps({
                "stage": "intent_parsing",
                "message": "正在理解您的需求..."
            }))
            await asyncio.sleep(0.1)  # 给用户感知的时间

            # 阶段 2: 执行 Skill
            yield _sse_event("status", json.dumps({
                "stage": "executing",
                "message": f"正在执行{skill_name}..."
            }))

            start_time = time.time()
            result = await registry.execute(skill_name, **params, context=context)
            exec_time = time.time() - start_time

            logger.info(f"Skill SSE: Execution completed in {exec_time:.2f}s")

            # 阶段 3: 敏感信息过滤（如果启用）
            if request.enable_sensitive_filter and result.get("data"):
                from services.sensitive_filter_service import sensitive_filter_service
                filtered_data = sensitive_filter_service.filter_response(
                    result.get("data", {}),
                    context.get("relationship_stage", "initial")
                )
                result["data"] = filtered_data
                yield _sse_event("filter", json.dumps({
                    "applied": True,
                    "filtered_fields": list(filtered_data.get("_filtered_fields", []))
                }))

            # 阶段 4: 生成响应
            yield _sse_event("status", json.dumps({
                "stage": "generating_response",
                "message": "正在生成建议..."
            }))

            ai_message = result.get("ai_message", "")
            if ai_message:
                yield _sse_event("response", json.dumps({
                    "text": ai_message,
                    "confidence": result.get("confidence", 0.8)
                }))

            # 阶段 5: UI 组件选择
            ui_config = _select_ui_component(skill_name, result)
            yield _sse_event("ui", json.dumps(ui_config))

            # 完成
            yield _sse_event("done", json.dumps({
                "success": result.get("success", False),
                "exec_time_ms": int(exec_time * 1000)
            }))

        except Exception as e:
            logger.error(f"Skill SSE stream error: {e}")
            yield _sse_event("error", json.dumps({
                "error": str(e),
                "message": "技能执行失败，请稍后再试"
            }))

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Nginx 禁用缓冲
        }
    )


def _sse_event(event_type: str, data: str) -> str:
    """
    生成 SSE 事件格式

    格式:
    event: {event_type}
    data: {data}\n\n
    """
    return f"event: {event_type}\ndata: {data}\n\n"


def _select_ui_component(skill_name: str, result: dict) -> dict:
    """
    根据 Skill 类型和执行结果选择 UI 组件
    """
    ui_mapping = {
        "matchmaking_assistant": {
            "component": "MatchCardList",
            "props": {"matches": result.get("data", {}).get("matches", [])}
        },
        "pre_communication": {
            "component": "CommunicationPanel",
            "props": {"session": result.get("data", {}).get("session", {})}
        },
        "gift_ordering": {
            "component": "GiftGrid",
            "props": {"gifts": result.get("data", {}).get("gifts", [])}
        },
        "date_planning": {
            "component": "DateSpotList",
            "props": {"dates": result.get("data", {}).get("date_spots", [])}
        },
        "bill_analysis": {
            "component": "ConsumptionProfile",
            "props": {"profile": result.get("data", {}).get("consumption_profile", {})}
        },
        "omniscient_insight": {
            "component": "InsightCard",
            "props": {"insight": result.get("data", {}).get("insight", {})}
        },
    }

    default_ui = {
        "component": "AIResponseCard",
        "props": {"data": result.get("data", {})}
    }

    return ui_mapping.get(skill_name, default_ui)


# ============= 敏感信息过滤服务 =============

@router.post("/filter/sensitive")
async def filter_sensitive_info(
    content: str = Body(..., embed=True),
    relationship_stage: str = Body(default="initial", embed=True),
    current_user: dict = Depends(get_current_user_optional)
):
    """
    敏感信息过滤端点

    根据关系阶段过滤敏感信息：
    - initial: 完全屏蔽联系方式、地址等
    - contact_exchanged: 可透露部分信息
    - meeting_confirmed: 完全开放
    """
    from services.sensitive_filter_service import sensitive_filter_service

    filtered = sensitive_filter_service.filter_message(content, relationship_stage)

    return {
        "success": True,
        "original": content,
        "filtered": filtered,
        "relationship_stage": relationship_stage,
        "filter_applied": filtered != content
    }


# ============= API 端点 =============

@router.get("/list", response_model=SkillListResponse)
async def list_skills():
    """
    获取所有可用 Skill 列表

    返回已注册的所有 Agent Skill 信息
    """
    skills = list_all_skills()

    return SkillListResponse(
        success=True,
        skills=[SkillInfo(**skill) for skill in skills],
        total=len(skills)
    )


@router.get("/{skill_name}/info")
async def get_skill_info_endpoint(skill_name: str):
    """
    获取 Skill 详细信息

    Args:
        skill_name: Skill 名称
    """
    info = get_skill_info(skill_name)

    if not info.get("available"):
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_name}")

    return {
        "success": True,
        "skill": info
    }


@router.post("/{skill_name}/execute", response_model=SkillExecuteResponse)
async def execute_skill(
    skill_name: str,
    request: SkillExecuteRequest,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    执行 Skill

    Args:
        skill_name: Skill 名称
        request: 执行请求
    """
    user_id = current_user.get("user_id") if current_user else None
    is_anonymous = current_user.get("is_anonymous", True) if current_user else True

    logger.info(f"Skill API: Executing {skill_name} for user={user_id}")

    # 获取注册表
    registry = get_skill_registry()

    # 检查 Skill 是否存在
    skill = registry.get(skill_name)
    if not skill:
        return SkillExecuteResponse(
            success=False,
            error=f"Skill not found: {skill_name}",
            ai_message=f"抱歉，未找到{skill_name}技能"
        )

    # 添加用户上下文
    params = request.params or {}
    if "user_id" not in params and user_id:
        params["user_id"] = user_id

    context = request.context or {}
    if "user_id" not in context and user_id:
        context["user_id"] = user_id

    # 执行 Skill
    try:
        result = await registry.execute(skill_name, **params, context=context)

        if result.get("success"):
            return SkillExecuteResponse(
                success=True,
                data=result,
                ai_message=result.get("ai_message")
            )
        else:
            return SkillExecuteResponse(
                success=False,
                error=result.get("error", "Unknown error"),
                ai_message=result.get("ai_message", "执行失败")
            )

    except Exception as e:
        logger.error(f"Skill execution failed: {skill_name}, error: {e}")
        return SkillExecuteResponse(
            success=False,
            error=str(e),
            ai_message="技能执行失败，请稍后再试"
        )


@router.post("/execute")
async def execute_skill_by_name(
    request: SkillExecuteRequest,
    current_user: dict = Depends(get_current_user_optional)
):
    """
    根据名称执行 Skill（通用端点）

    Args:
        request: 执行请求
    """
    return await execute_skill(request.skill_name, request, current_user)


# ============= 自主触发端点 =============

@router.post("/autonomous/trigger")
async def trigger_autonomous_skill(
    skill_name: str,
    trigger_type: str,
    user_id: str,
    context: Optional[Dict[str, Any]] = None
):
    """
    触发 Skill 的自主行为

    Args:
        skill_name: Skill 名称
        trigger_type: 触发类型
        user_id: 用户 ID
        context: 上下文数据
    """
    registry = get_skill_registry()
    skill = registry.get(skill_name)

    if not skill:
        return {
            "success": False,
            "error": f"Skill not found: {skill_name}"
        }

    if not hasattr(skill, "autonomous_trigger"):
        return {
            "success": False,
            "error": f"Skill {skill_name} does not support autonomous triggers"
        }

    try:
        # 调用自主触发方法
        import inspect
        trigger_method = getattr(skill, "autonomous_trigger")

        if inspect.iscoroutinefunction(trigger_method):
            result = await trigger_method(user_id, trigger_type, context or {})
        else:
            result = trigger_method(user_id, trigger_type, context or {})

        return result

    except Exception as e:
        logger.error(f"Autonomous trigger failed: {skill_name}, error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============= 情境感知触发端点 =============

@router.post("/context/trigger")
async def trigger_context_skill(
    skill_name: str,
    trigger_type: str,
    user_id: str,
    context: Optional[Dict[str, Any]] = None
):
    """
    触发 Skill 的情境感知行为

    Args:
        skill_name: Skill 名称
        trigger_type: 触发类型
        user_id: 用户 ID
        context: 上下文数据
    """
    registry = get_skill_registry()
    skill = registry.get(skill_name)

    if not skill:
        return {
            "success": False,
            "error": f"Skill not found: {skill_name}"
        }

    if not hasattr(skill, "context_trigger"):
        return {
            "success": False,
            "error": f"Skill {skill_name} does not support context triggers"
        }

    try:
        # 调用情境触发方法
        import inspect
        trigger_method = getattr(skill, "context_trigger")

        if inspect.iscoroutinefunction(trigger_method):
            result = await trigger_method(user_id, trigger_type, context or {})
        else:
            result = trigger_method(user_id, trigger_type, context or {})

        return result

    except Exception as e:
        logger.error(f"Context trigger failed: {skill_name}, error: {e}")
        return {
            "success": False,
            "error": str(e)
        }
