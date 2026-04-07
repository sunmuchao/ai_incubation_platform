"""
P9 内容标注与身份标识服务

负责:
1. 内容标签管理（创建、更新、查询）
2. AI 辅助记录管理
3. AI 参与度计算
4. 透明度报告生成
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, and_
import logging
import uuid
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import DBContentLabel, DBAIAssistRecord
from models.p9_entities import (
    AuthorType, AIAssistLevel, AIAssistType,
    ContentLabel, AIAssistRecord,
    ContentLabelCreate, ContentLabelUpdate, AIAssistCreate,
    ContentTransparencyReport, AIModelInfo,
    AIAssistStats, AuthorTypeStats
)

logger = logging.getLogger(__name__)


# AI 辅助程度阈值配置
AI_ASSIST_THRESHOLDS = {
    AIAssistLevel.NONE: (0, 0),
    AIAssistLevel.MINIMAL: (1, 25),
    AIAssistLevel.MODERATE: (26, 50),
    AIAssistLevel.SUBSTANTIAL: (51, 75),
    AIAssistLevel.HIGH: (76, 99),
    AIAssistLevel.FULL: (100, 100),
}


class ContentLabelingService:
    """内容标注服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_content_label(
        self,
        label_data: ContentLabelCreate
    ) -> ContentLabel:
        """
        创建内容标签

        Args:
            label_data: 标签创建数据

        Returns:
            ContentLabel: 创建的标签
        """
        # 计算 AI 辅助程度
        ai_assist_level = self._calculate_assist_level(
            label_data.ai_participation_rate
        )

        # 生成徽章文本
        badge_text = self._generate_badge_text(
            label_data.author_type,
            ai_assist_level,
            label_data.ai_assist_types
        )

        # 创建数据库记录
        db_label = DBContentLabel(
            content_id=label_data.content_id,
            content_type=label_data.content_type,
            author_type=label_data.author_type.value,
            ai_assist_level=ai_assist_level.value,
            ai_assist_types=[t.value for t in label_data.ai_assist_types] if label_data.ai_assist_types else [],
            ai_participation_rate=label_data.ai_participation_rate,
            ai_models=label_data.ai_models,
            assist_record_ids=label_data.assist_record_ids or [],
            badge_text=badge_text,
        )

        self.db.add(db_label)
        await self.db.flush()
        await self.db.refresh(db_label)

        logger.info(
            f"创建内容标签：content_id={label_data.content_id}, "
            f"author_type={label_data.author_type.value}, "
            f"ai_level={ai_assist_level.value}"
        )

        return self._to_entity(db_label)

    async def get_content_label(self, content_id: str) -> Optional[ContentLabel]:
        """
        获取内容标签

        Args:
            content_id: 内容 ID

        Returns:
            Optional[ContentLabel]: 标签实体
        """
        from sqlalchemy import select
        stmt = select(DBContentLabel).where(
            DBContentLabel.content_id == content_id
        )
        result = await self.db.execute(stmt)
        db_label = result.scalar_one_or_none()

        if db_label:
            return self._to_entity(db_label)
        return None

    async def update_content_label(
        self,
        content_id: str,
        update_data: ContentLabelUpdate
    ) -> Optional[ContentLabel]:
        """
        更新内容标签

        Args:
            content_id: 内容 ID
            update_data: 更新数据

        Returns:
            Optional[ContentLabel]: 更新后的标签
        """
        from sqlalchemy import select
        stmt = select(DBContentLabel).where(
            DBContentLabel.content_id == content_id
        )
        result = await self.db.execute(stmt)
        db_label = result.scalar_one_or_none()

        if not db_label:
            return None

        # 更新字段
        if update_data.author_type:
            db_label.author_type = update_data.author_type.value
        if update_data.ai_assist_level:
            db_label.ai_assist_level = update_data.ai_assist_level.value
        if update_data.ai_assist_types:
            db_label.ai_assist_types = [t.value for t in update_data.ai_assist_types]
        if update_data.ai_participation_rate is not None:
            db_label.ai_participation_rate = update_data.ai_participation_rate
            # 重新计算辅助程度
            db_label.ai_assist_level = self._calculate_assist_level(
                update_data.ai_participation_rate
            ).value
        if update_data.is_verified is not None:
            db_label.is_verified = update_data.is_verified
            if update_data.is_verified:
                db_label.verified_at = datetime.now()

        # 重新生成徽章文本
        db_label.badge_text = self._generate_badge_text(
            AuthorType(db_label.author_type),
            AIAssistLevel(db_label.ai_assist_level),
            [AIAssistType(t) for t in db_label.ai_assist_types] if db_label.ai_assist_types else []
        )

        await self.db.flush()
        await self.db.refresh(db_label)

        logger.info(f"更新内容标签：content_id={content_id}")
        return self._to_entity(db_label)

    async def create_ai_assist_record(
        self,
        record_data: AIAssistCreate
    ) -> AIAssistRecord:
        """
        创建 AI 辅助记录

        Args:
            record_data: 记录创建数据

        Returns:
            AIAssistRecord: 创建的记录
        """
        record_id = str(uuid.uuid4())

        db_record = DBAIAssistRecord(
            record_id=record_id,
            content_id=record_data.content_id,
            content_type=record_data.content_type,
            author_id=record_data.author_id,
            assist_type=record_data.assist_type.value,
            original_content=record_data.original_content,
            assisted_content=record_data.assisted_content,
            model_provider=record_data.model_provider,
            model_name=record_data.model_name,
            model_version=record_data.model_version,
            assist_details=record_data.assist_details or {},
            changes_made=record_data.changes_made or [],
            confidence_score=record_data.confidence_score,
            duration_ms=record_data.duration_ms,
        )

        self.db.add(db_record)
        await self.db.flush()
        await self.db.refresh(db_record)

        logger.info(
            f"创建 AI 辅助记录：record_id={record_id}, "
            f"assist_type={record_data.assist_type.value}"
        )

        return self._record_to_entity(db_record)

    async def get_assist_records_by_content(
        self,
        content_id: str
    ) -> List[AIAssistRecord]:
        """
        获取内容的 AI 辅助记录

        Args:
            content_id: 内容 ID

        Returns:
            List[AIAssistRecord]: 辅助记录列表
        """
        from sqlalchemy import select
        stmt = select(DBAIAssistRecord).where(
            DBAIAssistRecord.content_id == content_id
        ).order_by(DBAIAssistRecord.created_at)
        result = await self.db.execute(stmt)
        db_records = result.scalars().all()

        return [self._record_to_entity(r) for r in db_records]

    async def get_transparency_report(
        self,
        content_id: str
    ) -> Optional[ContentTransparencyReport]:
        """
        获取内容透明度报告

        Args:
            content_id: 内容 ID

        Returns:
            Optional[ContentTransparencyReport]: 透明度报告
        """
        label = await self.get_content_label(content_id)
        if not label:
            return None

        # 获取辅助记录
        assist_records = await self.get_assist_records_by_content(content_id)

        # 计算透明度评分
        transparency_score = self._calculate_transparency_score(label, assist_records)

        # 生成徽章显示
        badge_display = self._generate_badge_display(label)

        # 解析 AI 模型信息
        ai_models = []
        if label.ai_models:
            for model in label.ai_models:
                ai_models.append(AIModelInfo(
                    provider=model.get("provider", ""),
                    model=model.get("model", ""),
                    version=model.get("version")
                ))

        return ContentTransparencyReport(
            content_id=content_id,
            content_type=label.content_type,
            author_type=label.author_type,
            ai_participation_rate=label.ai_participation_rate,
            ai_assist_level=label.ai_assist_level,
            ai_assist_types=label.ai_assist_types,
            ai_models_used=ai_models,
            assist_history=assist_records,
            transparency_score=transparency_score,
            verification_status=label.is_verified,
            badge_display=badge_display,
        )

    async def get_stats_overview(self) -> AIAssistStats:
        """
        获取 AI 辅助统计概览

        Returns:
            AIAssistStats: 统计数据
        """
        from sqlalchemy import select, func

        # 总辅助内容数
        stmt = select(func.count(DBContentLabel.id)).where(
            DBContentLabel.ai_assist_level != AIAssistLevel.NONE.value
        )
        result = await self.db.execute(stmt)
        total_assisted = result.scalar() or 0

        # 按辅助程度统计
        by_level = {}
        for level in AIAssistLevel:
            stmt = select(func.count(DBContentLabel.id)).where(
                DBContentLabel.ai_assist_level == level.value
            )
            result = await self.db.execute(stmt)
            count = result.scalar() or 0
            by_level[level.value] = count

        # 按辅助类型统计
        by_type_stmt = select(
            DBContentLabel.ai_assist_types,
            func.count(DBContentLabel.id)
        ).group_by(DBContentLabel.ai_assist_types)
        result = await self.db.execute(by_type_stmt)
        by_type = {}
        for row in result.all():
            types = row[0] or []
            count = row[1]
            for t in types:
                by_type[t] = by_type.get(t, 0) + count

        # 平均 AI 参与度
        avg_stmt = select(func.avg(DBContentLabel.ai_participation_rate))
        result = await self.db.execute(avg_stmt)
        avg_participation = result.scalar() or 0.0

        # 透明标注率
        total_stmt = select(func.count(DBContentLabel.id))
        result = await self.db.execute(total_stmt)
        total = result.scalar() or 1
        transparency_rate = total_assisted / total if total > 0 else 0.0

        # 常用 AI 模型排行
        top_models = await self._get_top_ai_models()

        return AIAssistStats(
            total_assisted_content=total_assisted,
            by_level=by_level,
            by_type=by_type,
            avg_ai_participation=round(avg_participation, 2),
            top_ai_models=top_models,
            transparency_rate=round(transparency_rate, 4),
        )

    async def get_author_type_stats(self) -> AuthorTypeStats:
        """
        获取作者类型统计

        Returns:
            AuthorTypeStats: 统计数据
        """
        from sqlalchemy import select, func

        # 总数
        total_stmt = select(func.count(DBContentLabel.id))
        result = await self.db.execute(total_stmt)
        total = result.scalar() or 0

        # 按作者类型统计
        by_type = {}
        for author_type in AuthorType:
            stmt = select(func.count(DBContentLabel.id)).where(
                DBContentLabel.author_type == author_type.value
            )
            result = await self.db.execute(stmt)
            count = result.scalar() or 0
            by_type[author_type.value] = count

        return AuthorTypeStats(
            total_content=total,
            human_created=by_type.get(AuthorType.HUMAN.value, 0),
            ai_generated=by_type.get(AuthorType.AI.value, 0),
            hybrid_created=by_type.get(AuthorType.HYBRID.value, 0),
            human_percentage=round(by_type.get(AuthorType.HUMAN.value, 0) / total * 100, 2) if total > 0 else 0,
            ai_percentage=round(by_type.get(AuthorType.AI.value, 0) / total * 100, 2) if total > 0 else 0,
            hybrid_percentage=round(by_type.get(AuthorType.HYBRID.value, 0) / total * 100, 2) if total > 0 else 0,
        )

    def _calculate_assist_level(self, participation_rate: float) -> AIAssistLevel:
        """
        根据 AI 参与度计算辅助程度

        Args:
            participation_rate: AI 参与度 (0-100)

        Returns:
            AIAssistLevel: 辅助程度
        """
        for level, (min_val, max_val) in AI_ASSIST_THRESHOLDS.items():
            if min_val <= participation_rate <= max_val:
                return level
        return AIAssistLevel.NONE

    def _generate_badge_text(
        self,
        author_type: AuthorType,
        ai_assist_level: AIAssistLevel,
        ai_assist_types: List[AIAssistType]
    ) -> str:
        """
        生成徽章文本

        Args:
            author_type: 作者类型
            ai_assist_level: AI 辅助程度
            ai_assist_types: AI 辅助类型列表

        Returns:
            str: 徽章文本
        """
        if author_type == AuthorType.HUMAN:
            return "人类创作"
        elif author_type == AuthorType.AI:
            return "AI 生成"
        else:  # HYBRID
            type_badges = {
                AIAssistType.POLISH: "润色",
                AIAssistType.EXPAND: "扩写",
                AIAssistType.TRANSLATE: "翻译",
                AIAssistType.SUMMARIZE: "摘要",
                AIAssistType.GENERATE: "生成",
                AIAssistType.SUGGEST: "建议",
            }
            assist_str = "+".join([type_badges.get(t, "") for t in ai_assist_types if t != AIAssistType.NONE])
            if assist_str:
                return f"人机协作 ({assist_str})"
            else:
                return f"人机协作 ({ai_assist_level.value})"

    def _generate_badge_display(self, label: ContentLabel) -> str:
        """
        生成前端显示的徽章 HTML

        Args:
            label: 内容标签

        Returns:
            str: 徽章显示文本
        """
        emoji_map = {
            AuthorType.HUMAN: "👤",
            AuthorType.AI: "🤖",
            AuthorType.HYBRID: "🤝",
        }
        emoji = emoji_map.get(label.author_type, "❓")
        return f"{emoji} {label.badge_text}"

    def _calculate_transparency_score(
        self,
        label: ContentLabel,
        assist_records: List[AIAssistRecord]
    ) -> float:
        """
        计算透明度评分

        Args:
            label: 内容标签
            assist_records: 辅助记录列表

        Returns:
            float: 透明度评分 (0-1)
        """
        score = 0.0

        # 有标签基础分 0.3
        score += 0.3

        # AI 模型信息完整度 0.2
        if label.ai_models and len(label.ai_models) > 0:
            score += 0.2

        # 辅助记录完整度 0.3
        if assist_records:
            record_score = min(len(assist_records) * 0.1, 0.3)
            score += record_score

        # 已验证 0.2
        if label.is_verified:
            score += 0.2

        return round(score, 2)

    async def _get_top_ai_models(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取常用 AI 模型排行

        Args:
            limit: 返回数量

        Returns:
            List[Dict]: 模型排行
        """
        from sqlalchemy import select, func

        # 从辅助记录中统计
        stmt = select(
            DBAIAssistRecord.model_provider,
            DBAIAssistRecord.model_name,
            func.count(DBAIAssistRecord.id).label("count")
        ).group_by(
            DBAIAssistRecord.model_provider,
            DBAIAssistRecord.model_name
        ).order_by(
            func.count(DBAIAssistRecord.id).desc()
        ).limit(limit)

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "provider": row[0],
                "model": row[1],
                "usage_count": row[2]
            }
            for row in rows
        ]

    def _to_entity(self, db_model: DBContentLabel) -> ContentLabel:
        """数据库模型转实体"""
        return ContentLabel(
            id=db_model.id,
            content_id=db_model.content_id,
            content_type=db_model.content_type,
            author_type=AuthorType(db_model.author_type),
            ai_assist_level=AIAssistLevel(db_model.ai_assist_level),
            ai_assist_types=[AIAssistType(t) for t in db_model.ai_assist_types] if db_model.ai_assist_types else [],
            ai_participation_rate=db_model.ai_participation_rate,
            ai_models=db_model.ai_models,
            assist_record_ids=db_model.assist_record_ids,
            is_verified=db_model.is_verified,
            verified_at=db_model.verified_at,
            verified_by=db_model.verified_by,
            badge_text=db_model.badge_text,
            created_at=db_model.created_at or datetime.now(),
            updated_at=db_model.updated_at or datetime.now(),
        )

    def _record_to_entity(self, db_model: DBAIAssistRecord) -> AIAssistRecord:
        """数据库模型转实体"""
        return AIAssistRecord(
            id=db_model.id,
            record_id=db_model.record_id,
            content_id=db_model.content_id,
            content_type=db_model.content_type,
            author_id=db_model.author_id,
            assist_type=AIAssistType(db_model.assist_type),
            original_content=db_model.original_content,
            assisted_content=db_model.assisted_content,
            model_provider=db_model.model_provider,
            model_name=db_model.model_name,
            model_version=db_model.model_version,
            assist_details=db_model.assist_details,
            changes_made=db_model.changes_made,
            confidence_score=db_model.confidence_score,
            duration_ms=db_model.duration_ms,
            created_at=db_model.created_at,
        )


# 全局服务实例
_content_labeling_service: Optional[ContentLabelingService] = None


def get_content_labeling_service(db: AsyncSession) -> ContentLabelingService:
    """获取内容标注服务实例"""
    global _content_labeling_service
    if _content_labeling_service is None:
        _content_labeling_service = ContentLabelingService(db)
    return _content_labeling_service
