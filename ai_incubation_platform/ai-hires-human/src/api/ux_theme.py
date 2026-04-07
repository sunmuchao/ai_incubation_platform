"""
主题设置 API 路由 - v1.22 用户体验优化

提供个性化主题/皮肤功能的 API 端点
"""
from fastapi import APIRouter, HTTPException, Query, Body, Depends, Header
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from services.theme_service import get_theme_service

router = APIRouter(prefix="/api/ux/theme", tags=["ux-theme"])


# ==================== 依赖注入 ====================

async def get_db() -> AsyncSession:
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user_id(x_user_id: str = Header(..., description="用户 ID")) -> str:
    """获取当前用户 ID（从请求头）"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="未授权")
    return x_user_id


# ==================== 请求/响应模型 ====================

class ThemeUpdateRequest(BaseModel):
    """主题更新请求"""
    theme_mode: Optional[str] = Field(None, description="主题模式：light/dark/system")
    accent_color: Optional[str] = Field(None, description="强调色：blue/purple/green/orange/pink/teal/coral")
    font_size: Optional[str] = Field(None, description="字体大小：small/medium/large")
    density: Optional[str] = Field(None, description="布局密度：compact/comfortable/spacious")
    custom_background: Optional[str] = Field(None, description="自定义背景图片 URL")
    theme_preset: Optional[str] = Field(None, description="预设主题包名称")


class ThemeResponse(BaseModel):
    """主题设置响应"""
    success: bool
    theme: Dict[str, Any]
    message: str = ""


class ThemeOptionsResponse(BaseModel):
    """主题选项响应"""
    success: bool
    options: Dict[str, Any]


# ==================== API 端点 ====================

@router.get("", response_model=ThemeResponse)
async def get_user_theme(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户主题设置

    返回当前用户的主题配置，包括主题模式、强调色、字体大小、布局密度等。
    如果用户尚未设置主题，将返回默认配置。
    """
    service = get_theme_service(db)

    theme = await service.get_or_create_theme(user_id)

    return {
        "success": True,
        "theme": theme.to_dict(),
        "message": "获取主题设置成功"
    }


@router.put("", response_model=ThemeResponse)
async def update_user_theme(
    request: ThemeUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    更新用户主题设置

    允许用户自定义主题模式、强调色、字体大小、布局密度等。
    所有字段均为可选，仅更新提供的字段。
    """
    service = get_theme_service(db)

    # 过滤空值
    update_data = {k: v for k, v in request.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="至少需要提供一个更新字段")

    try:
        theme = await service.update_theme(user_id, update_data)

        return {
            "success": True,
            "theme": theme.to_dict(),
            "message": "主题设置更新成功"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/options", response_model=ThemeOptionsResponse)
async def get_theme_options(db: AsyncSession = Depends(get_db)):
    """
    获取可用主题选项

    返回所有可用的主题模式、强调色、字体大小、布局密度以及预设主题包。
    此接口用于前端展示主题设置选项。
    """
    service = get_theme_service(db)

    options = await service.get_available_themes()

    return {
        "success": True,
        "options": options
    }


@router.post("/preset/{preset_id}/apply", response_model=ThemeResponse)
async def apply_theme_preset(
    preset_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    应用预设主题

    一键应用预设主题包的配置。
    预设主题由平台 predefined，用户可以选择应用。
    """
    service = get_theme_service(db)

    try:
        theme = await service.apply_preset_theme(user_id, preset_id)

        return {
            "success": True,
            "theme": theme.to_dict(),
            "message": f"主题 {preset_id} 应用成功"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reset", response_model=ThemeResponse)
async def reset_user_theme(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    重置为主题默认设置

    将用户的主题设置恢复为默认值：
    - 主题模式：system（跟随系统）
    - 强调色：blue（海洋蓝）
    - 字体大小：medium（中）
    - 布局密度：comfortable（舒适）
    """
    service = get_theme_service(db)

    theme = await service.reset_theme(user_id)

    return {
        "success": True,
        "theme": theme.to_dict(),
        "message": "主题设置已重置为默认值"
    }


@router.post("/preview", response_model=ThemeResponse)
async def preview_theme(
    request: ThemeUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    预览主题效果

    临时应用主题设置用于预览，不保存到数据库。
    返回预览配置供前端展示效果。
    """
    # 获取当前主题
    service = get_theme_service(db)
    current_theme = await service.get_or_create_theme(user_id)

    # 构建预览主题（合并当前设置和请求设置）
    preview_data = current_theme.to_dict()
    for k, v in request.model_dump().items():
        if v is not None:
            preview_data[k] = v

    return {
        "success": True,
        "theme": preview_data,
        "message": "预览配置已生成（未保存）"
    }
