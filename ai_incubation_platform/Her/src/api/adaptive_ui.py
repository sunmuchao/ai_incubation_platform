"""
情境感知渲染 API

P1 功能：基于对话情境动态选择 UI 组件
"""
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from db.database import get_db
from services.adaptive_ui_service import (
    adaptive_ui_renderer,
    AdaptiveUIContext,
    AdaptiveUIRenderer,
)
from utils.logger import logger
from auth.jwt import get_current_user

router = APIRouter(prefix="/api/adaptive-ui", tags=["P1-情境感知渲染"])


# ============= 请求/响应模型 =============

class UIContextRequest(BaseModel):
    """UI 上下文请求"""
    conversation_id: Optional[str] = Field(None, description="对话 ID")
    partner_id: Optional[str] = Field(None, description="对方 ID")
    relationship_stage: str = Field(default="initial", description="关系阶段")
    silence_duration: int = Field(default=0, ge=0, description="沉默时长（秒）")
    conflict_detected: bool = Field(default=False, description="是否检测到冲突")
    mood: str = Field(default="neutral", description="情绪状态")
    energy_level: str = Field(default="medium", description="能量水平")
    time_of_day: str = Field(default="day", description="时间段")
    day_of_week: str = Field(default="weekday", description="星期")


class UIComponentResponse(BaseModel):
    """UI 组件响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class ContextDetectionResponse(BaseModel):
    """情境检测响应"""
    success: bool
    context_type: str
    description: str
    suggested_components: List[str]


# ============= 辅助函数 =============

def get_ui_renderer() -> AdaptiveUIRenderer:
    """获取 UI 渲染器实例"""
    return adaptive_ui_renderer


# ============= 情境感知 API =============

@router.post("/select-component", response_model=UIComponentResponse)
async def select_ui_component(
    context: UIContextRequest,
    data_type: Optional[str] = Query(None, description="数据类型"),
    current_user: dict = Depends(get_current_user),
    renderer: AdaptiveUIRenderer = Depends(get_ui_renderer)
):
    """
    根据情境选择 UI 组件

    基于当前对话情境、用户状态、关系阶段等因素，
    动态选择最适合的 UI 组件
    """
    user_id = current_user.get("user_id")

    # 创建情境上下文
    ui_context = AdaptiveUIContext(
        user_id=user_id,
        conversation_id=context.conversation_id,
        partner_id=context.partner_id,
        relationship_stage=context.relationship_stage,
        silence_duration=context.silence_duration,
        conflict_detected=context.conflict_detected,
        mood=context.mood,
        energy_level=context.energy_level,
        time_of_day=context.time_of_day,
        day_of_week=context.day_of_week,
    )

    # 选择组件
    component_config = renderer.select_component(ui_context, data_type)

    return UIComponentResponse(
        success=True,
        data=component_config,
        message=f"已根据情境选择 UI 组件：{component_config.get('component_type')}"
    )


@router.post("/render")
async def render_ui(
    context: UIContextRequest,
    data: Optional[Dict[str, Any]] = Body(None, description="渲染数据"),
    current_user: dict = Depends(get_current_user),
    renderer: AdaptiveUIRenderer = Depends(get_ui_renderer)
):
    """
    渲染完整 UI

    基于情境和数据渲染完整的 UI 配置
    """
    user_id = current_user.get("user_id")

    # 创建情境上下文
    ui_context = AdaptiveUIContext(
        user_id=user_id,
        conversation_id=context.conversation_id,
        partner_id=context.partner_id,
        relationship_stage=context.relationship_stage,
        silence_duration=context.silence_duration,
        conflict_detected=context.conflict_detected,
        mood=context.mood,
        energy_level=context.energy_level,
        time_of_day=context.time_of_day,
        day_of_week=context.day_of_week,
    )

    # 渲染 UI
    ui_config = renderer.render(ui_context, data)

    return {
        "success": True,
        "ui_config": ui_config,
    }


@router.post("/detect-context")
async def detect_context(
    context: UIContextRequest,
    current_user: dict = Depends(get_current_user),
    renderer: AdaptiveUIRenderer = Depends(get_ui_renderer)
):
    """
    检测当前情境类型

    分析当前对话情境并返回情境类型
    """
    user_id = current_user.get("user_id")

    # 创建情境上下文
    ui_context = AdaptiveUIContext(
        user_id=user_id,
        conversation_id=context.conversation_id,
        partner_id=context.partner_id,
        relationship_stage=context.relationship_stage,
        silence_duration=context.silence_duration,
        conflict_detected=context.conflict_detected,
        mood=context.mood,
        energy_level=context.energy_level,
        time_of_day=context.time_of_day,
        day_of_week=context.day_of_week,
    )

    # 检测情境类型
    context_type = renderer.detect_context_type(ui_context)

    # 获取情境描述
    context_description = renderer.CONTEXT_TYPES.get(context_type, "未知情境")

    # 获取建议的组件
    suggested_components = []
    if context_type == "silence":
        suggested_components = ["silence_breaker", "icebreaker_game", "topic_list"]
    elif context_type == "conflict":
        suggested_components = ["conflict_mediator", "meditation_card", "chat_input"]
    elif context_type == "first_contact":
        suggested_components = ["chat_input_with_suggestions", "match_card_list"]
    elif context_type == "pre_date":
        suggested_components = ["ai_translator_input", "date_spot_list"]
    elif context_type == "breakthrough":
        suggested_components = ["insight_card", "celebration_card"]
    elif context_type == "deep_conversation":
        suggested_components = ["chat_input", "topic_list"]
    else:
        suggested_components = ["chat_input", "ai_response_card"]

    return {
        "success": True,
        "context_type": context_type,
        "context_description": context_description,
        "suggested_components": suggested_components,
    }


# ============= 情境预设 API =============

@router.get("/presets")
async def get_context_presets():
    """
    获取情境预设

    返回所有支持的情境类型和配置
    """
    return {
        "success": True,
        "presets": {
            context_key: {
                "name": name,
                "description": f"情境类型：{context_key}",
            }
            for context_key, name in adaptive_ui_renderer.CONTEXT_TYPES.items()
        }
    }


@router.get("/components")
async def get_available_components():
    """
    获取可用 UI 组件列表

    返回所有可用的 UI 组件及其配置
    """
    return {
        "success": True,
        "components": {
            comp_key: {
                "name": comp["name"],
                "type": comp["type"],
                "default_props": comp["props"],
            }
            for comp_key, comp in adaptive_ui_renderer.UI_COMPONENTS.items()
        }
    }


# ============= 情境测试 API =============

@router.post("/test/silence")
async def test_silence_scenario(
    silence_duration: int = Body(default=45, ge=0, description="沉默时长"),
    current_user: dict = Depends(get_current_user),
    renderer: AdaptiveUIRenderer = Depends(get_ui_renderer)
):
    """
    测试沉默情境

    模拟沉默场景，测试 UI 响应
    """
    user_id = current_user.get("user_id")

    ui_context = AdaptiveUIContext(
        user_id=user_id,
        relationship_stage="chatting",
        silence_duration=silence_duration,
    )

    component = renderer.select_component(ui_context)

    return {
        "success": True,
        "scenario": "silence",
        "silence_duration": silence_duration,
        "selected_component": component,
    }


@router.post("/test/conflict")
async def test_conflict_scenario(
    current_user: dict = Depends(get_current_user),
    renderer: AdaptiveUIRenderer = Depends(get_ui_renderer)
):
    """
    测试冲突情境

    模拟冲突场景，测试 UI 响应
    """
    user_id = current_user.get("user_id")

    ui_context = AdaptiveUIContext(
        user_id=user_id,
        relationship_stage="dating",
        conflict_detected=True,
    )

    component = renderer.select_component(ui_context)

    return {
        "success": True,
        "scenario": "conflict",
        "selected_component": component,
    }


@router.post("/test/first-contact")
async def test_first_contact_scenario(
    current_user: dict = Depends(get_current_user),
    renderer: AdaptiveUIRenderer = Depends(get_ui_renderer)
):
    """
    测试首次接触情境

    模拟首次接触场景，测试 UI 响应
    """
    user_id = current_user.get("user_id")

    ui_context = AdaptiveUIContext(
        user_id=user_id,
        relationship_stage="initial",
    )

    component = renderer.select_component(ui_context)

    return {
        "success": True,
        "scenario": "first_contact",
        "selected_component": component,
    }
