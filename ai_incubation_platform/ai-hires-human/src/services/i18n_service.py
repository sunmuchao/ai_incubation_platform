"""
多语言支持服务。

功能：
1. 用户语言偏好管理
2. 任务翻译管理
3. 消息模板翻译
4. 机器翻译集成
"""
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db_models import UserLanguagePreferenceDB, TaskTranslationDB, MessageTemplateDB
from i18n import get_i18n_service, DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)


class I18nService:
    """
    多语言支持服务。

    核心功能：
    1. 用户语言偏好 CRUD
    2. 任务翻译管理
    3. 消息模板管理
    4. 机器翻译集成（可选）
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.translator = get_i18n_service()

    # ========== 用户语言偏好 ==========

    async def get_user_language(self, user_id: str) -> str:
        """获取用户的语言偏好。"""
        result = await self.db.execute(
            select(UserLanguagePreferenceDB).where(UserLanguagePreferenceDB.user_id == user_id)
        )
        pref = result.scalar_one_or_none()

        if pref:
            return pref.preferred_language
        return DEFAULT_LANGUAGE

    async def set_user_language(
        self,
        user_id: str,
        language: str,
        auto_detect: bool = True
    ) -> UserLanguagePreferenceDB:
        """设置用户的语言偏好。"""
        # 检查是否已存在
        result = await self.db.execute(
            select(UserLanguagePreferenceDB).where(UserLanguagePreferenceDB.user_id == user_id)
        )
        pref = result.scalar_one_or_none()

        if pref:
            pref.preferred_language = language
            pref.auto_detect_language = auto_detect
        else:
            pref = UserLanguagePreferenceDB(
                id=f"ulp_{uuid.uuid4().hex[:20]}",
                user_id=user_id,
                preferred_language=language,
                auto_detect_language=auto_detect
            )
            self.db.add(pref)

        await self.db.commit()
        await self.db.refresh(pref)

        logger.info("Set language preference for user %s: %s", user_id, language)
        return pref

    # ========== 任务翻译 ==========

    async def get_task_translation(
        self,
        task_id: str,
        language: str
    ) -> Optional[TaskTranslationDB]:
        """获取任务的翻译。"""
        result = await self.db.execute(
            select(TaskTranslationDB).where(
                TaskTranslationDB.task_id == task_id,
                TaskTranslationDB.language_code == language
            )
        )
        return result.scalar_one_or_none()

    async def save_task_translation(
        self,
        task_id: str,
        language: str,
        title: str,
        description: str,
        requirements: List[Dict],
        acceptance_criteria: List[Dict],
        is_machine_translated: bool = True
    ) -> TaskTranslationDB:
        """保存任务翻译。"""
        # 检查是否已存在
        result = await self.db.execute(
            select(TaskTranslationDB).where(
                TaskTranslationDB.task_id == task_id,
                TaskTranslationDB.language_code == language
            )
        )
        translation = result.scalar_one_or_none()

        if translation:
            translation.translated_title = title
            translation.translated_description = description
            translation.translated_requirements = requirements
            translation.translated_acceptance_criteria = acceptance_criteria
            translation.is_machine_translated = is_machine_translated
        else:
            translation = TaskTranslationDB(
                id=f"tt_{uuid.uuid4().hex[:20]}",
                task_id=task_id,
                language_code=language,
                translated_title=title,
                translated_description=description,
                translated_requirements=requirements,
                translated_acceptance_criteria=acceptance_criteria,
                is_machine_translated=is_machine_translated
            )
            self.db.add(translation)

        await self.db.commit()
        await self.db.refresh(translation)

        logger.info(
            "Saved task translation: task=%s, language=%s, machine_translated=%s",
            task_id, language, is_machine_translated
        )
        return translation

    async def get_all_task_translations(self, task_id: str) -> List[TaskTranslationDB]:
        """获取任务的所有翻译。"""
        result = await self.db.execute(
            select(TaskTranslationDB).where(TaskTranslationDB.task_id == task_id)
        )
        return list(result.scalars().all())

    # ========== 消息模板 ==========

    async def get_message_template(
        self,
        template_key: str,
        language: str
    ) -> Optional[MessageTemplateDB]:
        """获取消息模板。"""
        result = await self.db.execute(
            select(MessageTemplateDB).where(
                MessageTemplateDB.template_key == template_key,
                MessageTemplateDB.language_code == language
            )
        )
        return result.scalar_one_or_none()

    async def save_message_template(
        self,
        template_key: str,
        language: str,
        subject: str,
        body: str,
        variables: List[str]
    ) -> MessageTemplateDB:
        """保存消息模板。"""
        # 检查是否已存在
        result = await self.db.execute(
            select(MessageTemplateDB).where(
                MessageTemplateDB.template_key == template_key,
                MessageTemplateDB.language_code == language
            )
        )
        template = result.scalar_one_or_none()

        if template:
            template.subject_template = subject
            template.body_template = body
            template.available_variables = variables
        else:
            template = MessageTemplateDB(
                id=f"mt_{uuid.uuid4().hex[:20]}",
                template_key=template_key,
                language_code=language,
                subject_template=subject,
                body_template=body,
                available_variables=variables
            )
            self.db.add(template)

        await self.db.commit()
        await self.db.refresh(template)

        logger.info(
            "Saved message template: key=%s, language=%s",
            template_key, language
        )
        return template

    # ========== 翻译工具方法 ==========

    def translate_text(self, key: str, language: str = DEFAULT_LANGUAGE, **kwargs) -> str:
        """翻译文本（使用预定义翻译）。"""
        return self.translator.t(key, language, **kwargs)

    def get_supported_languages(self) -> Dict[str, str]:
        """获取支持的语言列表。"""
        return self.translator.get_supported_languages()

    async def reset_state(self) -> None:
        """重置状态（用于测试）。"""
        logger.info("I18nService state reset (test mode only)")
