"""
多语言支持 API - 提供国际化功能。

功能端点:
1. 语言偏好管理：获取/设置用户语言偏好
2. 任务翻译：获取/保存任务的多语言翻译
3. 消息模板：获取/保存多语言消息模板
4. 翻译工具：文本翻译、语言检测
"""
from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.i18n_service import I18nService
from database import AsyncSessionLocal
from i18n import get_supported_languages, detect_language

router = APIRouter(prefix="/api/i18n", tags=["i18n"])


# ========== 请求/响应模型 ==========

class LanguagePreferenceUpdate(BaseModel):
    """更新语言偏好请求模型。"""
    language: str = Field(..., description="语言代码，如 zh_CN, en_US")
    auto_detect: bool = Field(True, description="是否自动检测语言")


class TaskTranslationRequest(BaseModel):
    """任务翻译请求模型。"""
    language: str
    title: str
    description: str
    requirements: List[Dict] = Field(default_factory=list)
    acceptance_criteria: List[Dict] = Field(default_factory=list)


class MessageTemplateRequest(BaseModel):
    """消息模板请求模型。"""
    language: str
    subject: str
    body: str
    variables: List[str] = Field(default_factory=list)


class TranslateRequest(BaseModel):
    """文本翻译请求模型。"""
    text: str
    source_language: str = "zh_CN"
    target_language: str = "en_US"


# ========== 辅助函数 ==========

def create_service() -> I18nService:
    """创建服务实例。"""
    return I18nService(AsyncSessionLocal())


# ========== 语言偏好端点 ==========

@router.get("/languages", response_model=Dict)
async def get_supported_languages_endpoint():
    """
    获取支持的语言列表。

    返回所有支持的语言代码和名称。
    """
    languages = get_supported_languages()
    return {
        "languages": languages,
        "default_language": "zh_CN"
    }


@router.get("/user/language", response_model=Dict)
async def get_user_language(
    user_id: str = Query(..., description="用户 ID"),
    accept_language: Optional[str] = Header(None, description="HTTP Accept-Language 头")
):
    """
    获取用户的语言偏好。

    如果用户未设置偏好，则根据 Accept-Language 头自动检测。
    """
    db = AsyncSessionLocal()
    try:
        service = create_service()

        # 首先尝试获取用户设置的偏好
        preferred = await service.get_user_language(user_id)

        # 如果没有设置，使用 Accept-Language 头检测
        if preferred == "zh_CN" and accept_language:
            detected = detect_language(accept_language)
            if detected != "zh_CN":
                preferred = detected

        return {
            "user_id": user_id,
            "preferred_language": preferred,
            "supported_languages": get_supported_languages()
        }
    finally:
        await db.close()


@router.put("/user/language", response_model=Dict)
async def set_user_language(
    user_id: str = Query(..., description="用户 ID"),
    update: LanguagePreferenceUpdate = None
):
    """
    设置用户的语言偏好。

    设置后，API 响应将使用用户偏好的语言。
    """
    db = AsyncSessionLocal()
    try:
        service = create_service()

        # 验证语言代码
        supported = get_supported_languages()
        if update.language not in supported:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language: {update.language}. Supported: {list(supported.keys())}"
            )

        pref = await service.set_user_language(
            user_id,
            update.language,
            update.auto_detect
        )

        return {
            "message": "Language preference updated",
            "preference": {
                "user_id": pref.user_id,
                "preferred_language": pref.preferred_language,
                "auto_detect": pref.auto_detect_language,
                "updated_at": pref.updated_at.isoformat()
            }
        }
    finally:
        await db.close()


# ========== 任务翻译端点 ==========

@router.get("/tasks/{task_id}/translations", response_model=Dict)
async def get_task_translations(task_id: str):
    """
    获取任务的所有翻译。

    返回任务的所有可用语言翻译版本。
    """
    db = AsyncSessionLocal()
    try:
        service = create_service()
        translations = await service.get_all_task_translations(task_id)

        return {
            "task_id": task_id,
            "translations": [
                {
                    "language": t.language_code,
                    "title": t.translated_title,
                    "description": t.translated_description,
                    "is_machine_translated": t.is_machine_translated,
                    "is_reviewed": t.is_reviewed,
                    "updated_at": t.updated_at.isoformat()
                }
                for t in translations
            ]
        }
    finally:
        await db.close()


@router.get("/tasks/{task_id}/translations/{language}", response_model=Dict)
async def get_task_translation(task_id: str, language: str):
    """
    获取任务的特定语言翻译。
    """
    db = AsyncSessionLocal()
    try:
        service = create_service()
        translation = await service.get_task_translation(task_id, language)

        if not translation:
            raise HTTPException(
                status_code=404,
                detail=f"Translation not found for task {task_id} in language {language}"
            )

        return {
            "task_id": task_id,
            "language": language,
            "translation": {
                "title": translation.translated_title,
                "description": translation.translated_description,
                "requirements": translation.translated_requirements,
                "acceptance_criteria": translation.translated_acceptance_criteria,
                "is_machine_translated": translation.is_machine_translated,
                "is_reviewed": translation.is_reviewed
            }
        }
    finally:
        await db.close()


@router.post("/tasks/{task_id}/translations", response_model=Dict)
async def save_task_translation(task_id: str, request: TaskTranslationRequest):
    """
    保存任务的翻译。

    支持机器翻译和人工翻译两种方式。
    """
    db = AsyncSessionLocal()
    try:
        service = create_service()

        translation = await service.save_task_translation(
            task_id,
            request.language,
            request.title,
            request.description,
            request.requirements,
            request.acceptance_criteria,
            is_machine_translated=False  # 手动提交的翻译标记为非机器翻译
        )

        return {
            "message": "Task translation saved",
            "translation": {
                "task_id": task_id,
                "language": translation.language_code,
                "title": translation.translated_title,
                "updated_at": translation.updated_at.isoformat()
            }
        }
    finally:
        await db.close()


# ========== 消息模板端点 ==========

@router.get("/templates/{template_key}", response_model=Dict)
async def get_message_template(template_key: str, language: str = Query(...)):
    """
    获取消息模板。

    模板用于发送多语言通知（邮件、站内信等）。
    """
    db = AsyncSessionLocal()
    try:
        service = create_service()
        template = await service.get_message_template(template_key, language)

        if not template:
            raise HTTPException(
                status_code=404,
                detail=f"Template not found: {template_key} in {language}"
            )

        return {
            "template_key": template_key,
            "language": language,
            "template": {
                "subject": template.subject_template,
                "body": template.body_template,
                "variables": template.available_variables
            }
        }
    finally:
        await db.close()


@router.post("/templates", response_model=Dict)
async def save_message_template(
    template_key: str = Query(...),
    language: str = Query(...),
    request: MessageTemplateRequest = None
):
    """
    保存消息模板。
    """
    db = AsyncSessionLocal()
    try:
        service = create_service()

        template = await service.save_message_template(
            template_key,
            request.language,
            request.subject,
            request.body,
            request.variables
        )

        return {
            "message": "Message template saved",
            "template": {
                "template_key": template.template_key,
                "language": template.language_code,
                "subject": template.subject_template,
                "updated_at": template.updated_at.isoformat()
            }
        }
    finally:
        await db.close()


# ========== 翻译工具端点 ==========

@router.post("/translate", response_model=Dict)
async def translate_text(
    text: str = Query(..., description="要翻译的文本"),
    source: str = Query("zh_CN", description="源语言"),
    target: str = Query("en_US", description="目标语言")
):
    """
    翻译文本。

    注意：当前版本仅支持预定义键的翻译。
    完整机器翻译功能需要集成外部 API（如 DeepL、Google Translate）。
    """
    db = AsyncSessionLocal()
    try:
        service = create_service()

        # 当前版本仅支持预定义键的翻译
        # 实际使用时应集成外部翻译 API
        translated = service.translate_text(text, target)

        # 如果翻译结果与原文相同，说明没有找到翻译
        if translated == text:
            return {
                "original_text": text,
                "translated_text": text,
                "source_language": source,
                "target_language": target,
                "note": "Translation not found, returning original text"
            }

        return {
            "original_text": text,
            "translated_text": translated,
            "source_language": source,
            "target_language": target
        }
    finally:
        await db.close()


@router.get("/detect-language", response_model=Dict)
async def detect_user_language(accept_language: Optional[str] = Header(None)):
    """
    根据 HTTP 头检测用户语言偏好。
    """
    detected = detect_language(accept_language)
    return {
        "detected_language": detected,
        "language_name": get_supported_languages().get(detected, "Unknown"),
        "accept_language_header": accept_language
    }
