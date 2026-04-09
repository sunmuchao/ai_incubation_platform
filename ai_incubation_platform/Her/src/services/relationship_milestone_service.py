"""
P10-001: 关系里程碑追踪增强服务

基于现有关系进展服务，增强以下功能：
- AI 识别关系节点（如第一次约会、确定关系、纪念日等）
- 提供庆祝建议和关系进展分析
- 关系里程碑时间线可视化
- 关系洞察生成
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import json
import uuid
from sqlalchemy.orm import Session
from utils.db_session_manager import db_session, db_session_readonly
from db.database import SessionLocal
from models.p10_models import (
    RelationshipMilestoneDB,
    RelationshipStageHistoryDB,
    RelationshipInsightDB
)
from db.models import (
    RelationshipProgressDB,
    MatchHistoryDB,
    ChatMessageDB,
    ChatConversationDB
)
from utils.logger import logger


# 关系阶段定义（增强版）
RELATIONSHIP_STAGES_P10 = {
    "unknown": {"order": 0, "label": "未知", "description": "关系状态未明"},
    "matched": {"order": 1, "label": "已匹配", "description": "系统匹配成功"},
    "chatting": {"order": 2, "label": "聊天中", "description": "开始互动交流"},
    "exchanged_contact": {"order": 3, "label": "交换联系方式", "description": "交换微信/电话等"},
    "first_date": {"order": 4, "label": "首次约会", "description": "完成第一次线下见面"},
    "dating": {"order": 5, "label": "约会中", "description": "定期约会阶段"},
    "exclusive": {"order": 6, "label": "确定关系", "description": "确立排他性关系"},
    "in_relationship": {"order": 7, "label": "恋爱中", "description": "稳定恋爱关系"},
    "meet_parents": {"order": 8, "label": "见家长", "description": "见过双方家长"},
    "engaged": {"order": 9, "label": "已订婚", "description": "已订婚"},
    "married": {"order": 10, "label": "已结婚", "description": "步入婚姻殿堂"}
}


# 里程碑类型定义
MILESTONE_TYPES_P10 = {
    "first_match": {"label": "首次匹配", "category": "beginning", "celebration": False},
    "first_message": {"label": "第一条消息", "category": "beginning", "celebration": False},
    "first_like": {"label": "第一次点赞", "category": "beginning", "celebration": False},
    "deep_conversation": {"label": "深度对话", "category": "communication", "celebration": False},
    "contact_exchange": {"label": "交换联系方式", "category": "communication", "celebration": True},
    "first_date_proposal": {"label": "首次约会提议", "category": "dating", "celebration": False},
    "first_date_completed": {"label": "完成第一次约会", "category": "dating", "celebration": True},
    "anniversary_1month": {"label": "一月纪念日", "category": "anniversary", "celebration": True},
    "anniversary_3month": {"label": "三月纪念日", "category": "anniversary", "celebration": True},
    "anniversary_6month": {"label": "六月纪念日", "category": "anniversary", "celebration": True},
    "anniversary_1year": {"label": "一周年纪念日", "category": "anniversary", "celebration": True},
    "relationship_exclusive": {"label": "确定关系", "category": "commitment", "celebration": True},
    "meet_parents": {"label": "见家长", "category": "commitment", "celebration": True},
    "engagement": {"label": "订婚", "category": "commitment", "celebration": True},
    "marriage": {"label": "结婚", "category": "commitment", "celebration": True}
}


# 庆祝建议模板
CELEBRATION_SUGGESTIONS = {
    "beginning": {
        "type": "card",
        "description": "发送一张个性化的数字贺卡，记录你们相遇的美好时刻"
    },
    "communication": {
        "type": "activity",
        "description": "安排一次特别的视频通话，分享彼此的心声"
    },
    "dating": {
        "type": "activity",
        "description": "策划一次难忘的约会，尝试新的餐厅或活动"
    },
    "anniversary": {
        "type": "gift",
        "description": "准备一份有意义的纪念日礼物，如定制相册或手写信"
    },
    "commitment": {
        "type": "gift",
        "description": "准备一份特别的礼物庆祝这个重要时刻，如首饰或定制礼品"
    }
}


class RelationshipMilestoneService:
    """关系里程碑追踪服务（增强版）"""

    def __init__(self) -> None:
        self._stage_weights = {
            "message_count": 0.25,
            "conversation_depth": 0.25,
            "interaction_frequency": 0.20,
            "milestone_achievement": 0.30
        }

    def record_milestone(
        self,
        user_id_1: str,
        user_id_2: str,
        milestone_type: str,
        title: str,
        description: str,
        milestone_date: Optional[datetime] = None,
        celebration_suggested: bool = False,
        ai_analysis: Optional[Dict[str, Any]] = None,
        is_private: bool = False,
        db_session_param: Optional[Any] = None
    ) -> str:
        """
        记录关系里程碑

        Args:
            user_id_1: 用户 ID 1
            user_id_2: 用户 ID 2
            milestone_type: 里程碑类型
            title: 里程碑标题
            description: 里程碑描述
            milestone_date: 里程碑发生时间
            celebration_suggested: 是否建议庆祝
            ai_analysis: AI 分析数据
            is_private: 是否私密里程碑
            db_session_param: 可选的数据库会话

        Returns:
            记录 ID
        """
        milestone_id = str(uuid.uuid4())
        milestone_date = milestone_date or datetime.now()

        # 获取庆祝建议
        milestone_info = MILESTONE_TYPES_P10.get(milestone_type, {})
        category = milestone_info.get("category", "beginning")

        if celebration_suggested and category in CELEBRATION_SUGGESTIONS:
            celebration_info = CELEBRATION_SUGGESTIONS[category]
            celebration_type = celebration_info["type"]
            celebration_description = celebration_info["description"]
        else:
            celebration_type = None
            celebration_description = None

        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session() as db:
                    return self._record_milestone_internal(
                        user_id_1, user_id_2, milestone_type, title, description,
                        milestone_date, celebration_suggested, celebration_type,
                        celebration_description, ai_analysis, is_private, db
                    )
            else:
                return self._record_milestone_internal(
                    user_id_1, user_id_2, milestone_type, title, description,
                    milestone_date, celebration_suggested, celebration_type,
                    celebration_description, ai_analysis, is_private, db_session_param
                )
        finally:
            if use_context:
                pass

    def _record_milestone_internal(
        self,
        user_id_1: str,
        user_id_2: str,
        milestone_type: str,
        title: str,
        description: str,
        milestone_date: datetime,
        celebration_suggested: bool,
        celebration_type: Optional[str],
        celebration_description: Optional[str],
        ai_analysis: Optional[Dict[str, Any]],
        is_private: bool,
        db
    ) -> str:
        """记录里程碑内部方法"""
        milestone_id = str(uuid.uuid4())

        milestone = RelationshipMilestoneDB(
            id=milestone_id,
            user_id_1=user_id_1,
            user_id_2=user_id_2,
            milestone_type=milestone_type,
            title=title,
            description=description,
            milestone_date=milestone_date,
            celebration_suggested=celebration_suggested,
            celebration_type=celebration_type,
            celebration_description=celebration_description,
            ai_analysis=json.dumps(ai_analysis) if ai_analysis else "",
            is_private=is_private
        )
        db.add(milestone)

        # 如果是关系阶段相关的里程碑，更新阶段历史
        self._update_stage_history_if_needed(
            user_id_1, user_id_2, milestone_type, milestone_date, db
        )

        db.commit()
        logger.info(f"Recorded milestone: {milestone_type} for {user_id_1} & {user_id_2}")
        return milestone_id

    def _update_stage_history_if_needed(
        self,
        user_id_1: str,
        user_id_2: str,
        milestone_type: str,
        milestone_date: datetime,
        db
    ):
        """如果里程碑涉及关系阶段变化，更新阶段历史"""
        # 定义里程碑到阶段的映射
        milestone_to_stage = {
            "first_match": "matched",
            "first_message": "chatting",
            "contact_exchange": "exchanged_contact",
            "first_date_completed": "first_date",
            "relationship_exclusive": "exclusive",
            "meet_parents": "meet_parents",
            "engagement": "engaged",
            "marriage": "married"
        }

        to_stage = milestone_to_stage.get(milestone_type)
        if not to_stage:
            return

        # 获取当前阶段
        match = db.query(MatchHistoryDB).filter(
            ((MatchHistoryDB.user_id_1 == user_id_1) & (MatchHistoryDB.user_id_2 == user_id_2)) |
            ((MatchHistoryDB.user_id_1 == user_id_2) & (MatchHistoryDB.user_id_2 == user_id_1))
        ).first()

        from_stage = match.relationship_stage if match else "unknown"

        # 如果阶段有变化，记录历史
        if from_stage != to_stage:
            stage_order_from = RELATIONSHIP_STAGES_P10.get(from_stage, {}).get("order", 0)
            stage_order_to = RELATIONSHIP_STAGES_P10.get(to_stage, {}).get("order", 0)

            # 只记录升级，不记录降级
            if stage_order_to > stage_order_from:
                history_id = str(uuid.uuid4())
                history = RelationshipStageHistoryDB(
                    id=history_id,
                    user_id_1=user_id_1,
                    user_id_2=user_id_2,
                    from_stage=from_stage,
                    to_stage=to_stage,
                    stage_label=RELATIONSHIP_STAGES_P10.get(to_stage, {}).get("label", to_stage),
                    change_reason=f"达成里程碑：{milestone_type}",
                    trigger_event=milestone_type,
                    ai_comment=self._generate_stage_ai_comment(from_stage, to_stage),
                    next_stage_suggestions=json.dumps(
                        self._get_next_stage_suggestions(to_stage)
                    )
                )
                db.add(history)

                # 更新匹配历史中的阶段
                if match:
                    match.relationship_stage = to_stage
                    db.commit()

    def _generate_stage_ai_comment(self, from_stage: str, to_stage: str) -> str:
        """生成阶段变更的 AI 评论"""
        comments = {
            ("matched", "chatting"): "美好的开始！每一次交流都是了解彼此的契机。",
            ("chatting", "exchanged_contact"): "关系更进一步！交换联系方式意味着你们开始建立更深层的连接。",
            ("exchanged_contact", "first_date"): "从线上到线下，这是关系中的重要一步。祝你们约会愉快！",
            ("first_date", "exclusive"): "确定关系是两个人共同的承诺，珍惜这份美好。",
            ("exclusive", "in_relationship"): "稳定的恋爱关系需要双方共同经营，愿你们携手成长。",
            ("in_relationship", "meet_parents"): "见家长意味着你们在认真考虑未来，这是非常重要的里程碑。",
            ("meet_parents", "engaged"): "订婚是通往婚姻的承诺，祝福你们！",
            ("engaged", "married"): "步入婚姻殿堂，开始人生的新篇章！"
        }
        return comments.get((from_stage, to_stage), f"恭喜你们的关系从{RELATIONSHIP_STAGES_P10.get(from_stage, {}).get('label', from_stage)}进展到{RELATIONSHIP_STAGES_P10.get(to_stage, {}).get('label', to_stage)}！")

    def _get_next_stage_suggestions(self, current_stage: str) -> List[Dict[str, str]]:
        """获取下一阶段的建议"""
        stage_progression = {
            "matched": [
                {"action": "发起对话", "description": "用破冰话题开始交流"},
                {"action": "了解兴趣", "description": "探索共同的兴趣爱好"}
            ],
            "chatting": [
                {"action": "深入交流", "description": "分享更多个人信息和价值观"},
                {"action": "交换联系方式", "description": "建立更便捷的沟通渠道"}
            ],
            "exchanged_contact": [
                {"action": "规划约会", "description": "安排一次有意义的线下见面"},
                {"action": "保持联系", "description": "保持适当的沟通频率"}
            ],
            "first_date": [
                {"action": "继续了解", "description": "通过更多约会加深了解"},
                {"action": "诚实沟通", "description": "坦诚表达感受和期待"}
            ],
            "dating": [
                {"action": "定义关系", "description": "讨论彼此的关系期待"},
                {"action": "融入生活", "description": "逐渐融入彼此的社交圈"}
            ]
        }
        return stage_progression.get(current_stage, [
            {"action": "继续经营", "description": "用心经营你们的关系"}
        ])

    def get_milestone_timeline(
        self,
        user_id_1: str,
        user_id_2: str,
        include_private: bool = False,
        db_session_param: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        获取关系里程碑时间线

        Args:
            user_id_1: 用户 ID 1
            user_id_2: 用户 ID 2
            include_private: 是否包含私密里程碑
            db_session_param: 可选的数据库会话

        Returns:
            时间线数据
        """
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session_readonly() as db:
                    return self._get_milestone_timeline_internal(user_id_1, user_id_2, include_private, db)
            else:
                return self._get_milestone_timeline_internal(user_id_1, user_id_2, include_private, db_session_param)
        finally:
            if use_context:
                pass

    def _get_milestone_timeline_internal(
        self,
        user_id_1: str,
        user_id_2: str,
        include_private: bool,
        db
    ) -> Dict[str, Any]:
        """获取关系里程碑时间线内部方法"""
        query = db.query(RelationshipMilestoneDB).filter(
            ((RelationshipMilestoneDB.user_id_1 == user_id_1) & (RelationshipMilestoneDB.user_id_2 == user_id_2)) |
            ((RelationshipMilestoneDB.user_id_1 == user_id_2) & (RelationshipMilestoneDB.user_id_2 == user_id_1))
        )

        if not include_private:
            query = query.filter(RelationshipMilestoneDB.is_private == False)

        milestones = query.order_by(RelationshipMilestoneDB.milestone_date).all()

        timeline = []
        for m in milestones:
            milestone_info = MILESTONE_TYPES_P10.get(m.milestone_type, {})
            timeline.append({
                "id": m.id,
                "type": m.milestone_type,
                "label": milestone_info.get("label", m.title),
                "category": milestone_info.get("category", "other"),
                "title": m.title,
                "description": m.description,
                "milestone_date": m.milestone_date.isoformat() if m.milestone_date else None,
                "celebration_suggested": m.celebration_suggested,
                "celebration_type": m.celebration_type,
                "celebration_description": m.celebration_description,
                "ai_analysis": json.loads(m.ai_analysis) if m.ai_analysis else None,
                "user_rating": m.user_rating,
                "user_note": m.user_note,
                "is_private": m.is_private,
                "created_at": m.created_at.isoformat()
            })

        # 获取当前关系阶段
        match = db.query(MatchHistoryDB).filter(
            ((MatchHistoryDB.user_id_1 == user_id_1) & (MatchHistoryDB.user_id_2 == user_id_2)) |
            ((MatchHistoryDB.user_id_1 == user_id_2) & (MatchHistoryDB.user_id_2 == user_id_1))
        ).first()

        current_stage = match.relationship_stage if match else "unknown"

        # 获取阶段历史
        stage_history = self._get_stage_history(user_id_1, user_id_2, db)

        return {
            "user_ids": [user_id_1, user_id_2],
            "current_stage": current_stage,
            "current_stage_label": RELATIONSHIP_STAGES_P10.get(current_stage, {}).get("label", "未知"),
            "milestones": timeline,
            "stage_history": stage_history,
            "total_milestones": len(timeline)
        }

    def _get_stage_history(
        self,
        user_id_1: str,
        user_id_2: str,
        db
    ) -> List[Dict[str, Any]]:
        """获取关系阶段变更历史"""
        history_records = db.query(RelationshipStageHistoryDB).filter(
            ((RelationshipStageHistoryDB.user_id_1 == user_id_1) & (RelationshipStageHistoryDB.user_id_2 == user_id_2)) |
            ((RelationshipStageHistoryDB.user_id_1 == user_id_2) & (RelationshipStageHistoryDB.user_id_2 == user_id_1))
        ).order_by(RelationshipStageHistoryDB.created_at).all()

        history = []
        for h in history_records:
            history.append({
                "id": h.id,
                "from_stage": h.from_stage,
                "from_stage_label": RELATIONSHIP_STAGES_P10.get(h.from_stage, {}).get("label", h.from_stage),
                "to_stage": h.to_stage,
                "to_stage_label": h.stage_label,
                "change_reason": h.change_reason,
                "trigger_event": h.trigger_event,
                "ai_comment": h.ai_comment,
                "next_stage_suggestions": json.loads(h.next_stage_suggestions) if h.next_stage_suggestions else None,
                "created_at": h.created_at.isoformat()
            })
        return history

    def generate_relationship_insight(
        self,
        user_id_1: str,
        user_id_2: str,
        insight_type: str,
        title: str,
        content: str,
        action_suggestion: Optional[str] = None,
        priority: str = "normal",
        expires_hours: Optional[int] = None,
        db_session_param: Optional[Any] = None
    ) -> str:
        """
        生成关系洞察

        Args:
            user_id_1: 用户 ID 1
            user_id_2: 用户 ID 2
            insight_type: 洞察类型
            title: 洞察标题
            content: 洞察内容
            action_suggestion: 行动建议
            priority: 优先级
            expires_hours: 过期时间（小时）
            db_session_param: 可选的数据库会话

        Returns:
            洞察 ID
        """
        insight_id = str(uuid.uuid4())
        expires_at = None
        if expires_hours:
            expires_at = datetime.now() + timedelta(hours=expires_hours)

        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session() as db:
                    return self._generate_relationship_insight_internal(
                        user_id_1, user_id_2, insight_type, title, content,
                        action_suggestion, priority, expires_at, db
                    )
            else:
                return self._generate_relationship_insight_internal(
                    user_id_1, user_id_2, insight_type, title, content,
                    action_suggestion, priority, expires_at, db_session_param
                )
        finally:
            if use_context:
                pass

    def _generate_relationship_insight_internal(
        self,
        user_id_1: str,
        user_id_2: str,
        insight_type: str,
        title: str,
        content: str,
        action_suggestion: Optional[str],
        priority: str,
        expires_at: Optional[datetime],
        db
    ) -> str:
        """生成关系洞察内部方法"""
        insight_id = str(uuid.uuid4())

        insight = RelationshipInsightDB(
            id=insight_id,
            user_id_1=user_id_1,
            user_id_2=user_id_2,
            insight_type=insight_type,
            title=title,
            content=content,
            action_suggestion=action_suggestion,
            priority=priority,
            expires_at=expires_at
        )
        db.add(insight)
        db.commit()

        logger.info(f"Generated relationship insight: {insight_type} for {user_id_1} & {user_id_2}")
        return insight_id

    def get_relationship_insights(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 20,
        db_session_param: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        获取用户的关系洞察

        Args:
            user_id: 用户 ID
            unread_only: 是否只返回未读的
            limit: 返回数量限制
            db_session_param: 可选的数据库会话

        Returns:
            洞察列表
        """
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session_readonly() as db:
                    return self._get_relationship_insights_internal(user_id, unread_only, limit, db)
            else:
                return self._get_relationship_insights_internal(user_id, unread_only, limit, db_session_param)
        finally:
            if use_context:
                pass

    def _get_relationship_insights_internal(
        self,
        user_id: str,
        unread_only: bool,
        limit: int,
        db
    ) -> List[Dict[str, Any]]:
        """获取关系洞察内部方法"""
        query = db.query(RelationshipInsightDB).filter(
            (RelationshipInsightDB.user_id_1 == user_id) |
            (RelationshipInsightDB.user_id_2 == user_id)
        )

        if unread_only:
            query = query.filter(
                (RelationshipInsightDB.is_read_user1 == False) &
                (RelationshipInsightDB.is_read_user2 == False)
            )

        # 过滤未过期的
        query = query.filter(
            (RelationshipInsightDB.expires_at == None) |
            (RelationshipInsightDB.expires_at > datetime.now())
        )

        insights = query.order_by(
            RelationshipInsightDB.created_at.desc()
        ).limit(limit).all()

        result = []
        for i in insights:
            is_read = (i.is_read_user1 and i.is_read_user2)
            result.append({
                "id": i.id,
                "insight_type": i.insight_type,
                "title": i.title,
                "content": i.content,
                "action_suggestion": i.action_suggestion,
                "priority": i.priority,
                "confidence_score": i.confidence_score,
                "is_read": is_read,
                "is_actioned": i.is_actioned,
                "created_at": i.created_at.isoformat(),
                "expires_at": i.expires_at.isoformat() if i.expires_at else None
            })
        return result

    def mark_insight_read(
        self,
        insight_id: str,
        user_id: str,
        db_session_param: Optional[Any] = None
    ) -> bool:
        """
        标记洞察为已读

        Args:
            insight_id: 洞察 ID
            user_id: 用户 ID
            db_session_param: 可选的数据库会话

        Returns:
            是否成功
        """
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session() as db:
                    return self._mark_insight_read_internal(insight_id, user_id, db)
            else:
                return self._mark_insight_read_internal(insight_id, user_id, db_session_param)
        finally:
            if use_context:
                pass

    def _mark_insight_read_internal(
        self,
        insight_id: str,
        user_id: str,
        db
    ) -> bool:
        """标记洞察为已读内部方法"""
        insight = db.query(RelationshipInsightDB).filter(
            RelationshipInsightDB.id == insight_id
        ).first()

        if not insight:
            return False

        # 根据用户 ID 设置对应的已读标记
        if insight.user_id_1 == user_id:
            insight.is_read_user1 = True
        elif insight.user_id_2 == user_id:
            insight.is_read_user2 = True
        else:
            return False

        db.commit()
        return True

    def get_milestone_statistics(
        self,
        user_id_1: str,
        user_id_2: str,
        db_session_param: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        获取里程碑统计数据

        Args:
            user_id_1: 用户 ID 1
            user_id_2: 用户 ID 2
            db_session_param: 可选的数据库会话

        Returns:
            统计数据
        """
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session_readonly() as db:
                    return self._get_milestone_statistics_internal(user_id_1, user_id_2, db)
            else:
                return self._get_milestone_statistics_internal(user_id_1, user_id_2, db_session_param)
        finally:
            if use_context:
                pass

    def _get_milestone_statistics_internal(
        self,
        user_id_1: str,
        user_id_2: str,
        db
    ) -> Dict[str, Any]:
        """获取里程碑统计数据内部方法"""
        milestones = db.query(RelationshipMilestoneDB).filter(
            ((RelationshipMilestoneDB.user_id_1 == user_id_1) & (RelationshipMilestoneDB.user_id_2 == user_id_2)) |
            ((RelationshipMilestoneDB.user_id_1 == user_id_2) & (RelationshipMilestoneDB.user_id_2 == user_id_1))
        ).all()

        # 按类别分组统计
        category_stats = {}
        for m in milestones:
            milestone_info = MILESTONE_TYPES_P10.get(m.milestone_type, {})
            category = milestone_info.get("category", "other")
            if category not in category_stats:
                category_stats[category] = 0
            category_stats[category] += 1

        # 计算关系得分
        relationship_score = self._calculate_relationship_score(milestones)

        # 获取关系天数
        first_milestone = min((m.milestone_date for m in milestones), default=datetime.now())
        relationship_days = (datetime.now() - first_milestone).days if milestones else 0

        return {
            "total_milestones": len(milestones),
            "category_stats": category_stats,
            "relationship_score": relationship_score,
            "relationship_days": relationship_days,
            "first_milestone_date": first_milestone.isoformat() if milestones else None
        }

    def _calculate_relationship_score(self, milestones: List[RelationshipMilestoneDB]) -> float:
        """基于里程碑计算关系得分"""
        if not milestones:
            return 0.0

        # 定义不同类别里程碑的权重
        category_weights = {
            "beginning": 1.0,
            "communication": 1.5,
            "dating": 2.0,
            "anniversary": 1.5,
            "commitment": 3.0
        }

        total_score = 0.0
        for m in milestones:
            milestone_info = MILESTONE_TYPES_P10.get(m.milestone_type, {})
            category = milestone_info.get("category", "beginning")
            weight = category_weights.get(category, 1.0)
            total_score += weight

            # 用户评分加成
            if m.user_rating:
                total_score += m.user_rating * 0.1

        # 归一化到 0-100
        return min(100, total_score * 10)

    def get_milestone_by_id(self, milestone_id: str, db_session_param: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        """根据 ID 获取里程碑详情"""
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session_readonly() as db:
                    return self._get_milestone_by_id_internal(milestone_id, db)
            else:
                return self._get_milestone_by_id_internal(milestone_id, db_session_param)
        finally:
            if use_context:
                pass

    def _get_milestone_by_id_internal(
        self,
        milestone_id: str,
        db
    ) -> Optional[Dict[str, Any]]:
        """根据 ID 获取里程碑详情内部方法"""
        milestone = db.query(RelationshipMilestoneDB).filter(
            RelationshipMilestoneDB.id == milestone_id
        ).first()

        if not milestone:
            return None

        milestone_info = MILESTONE_TYPES_P10.get(milestone.milestone_type, {})
        return {
            "id": milestone.id,
            "user_id_1": milestone.user_id_1,
            "user_id_2": milestone.user_id_2,
            "milestone_type": milestone.milestone_type,
            "milestone_type_label": milestone_info.get("label", milestone.milestone_type),
            "category": milestone_info.get("category", "other"),
            "title": milestone.title,
            "description": milestone.description,
            "milestone_date": milestone.milestone_date.isoformat() if milestone.milestone_date else None,
            "celebration_suggested": milestone.celebration_suggested,
            "celebration_type": milestone.celebration_type,
            "celebration_description": milestone.celebration_description,
            "ai_analysis": json.loads(milestone.ai_analysis) if milestone.ai_analysis else None,
            "relationship_stage_at_milestone": milestone.relationship_stage_at_milestone,
            "user_rating": milestone.user_rating,
            "user_note": milestone.user_note,
            "is_private": milestone.is_private,
            "created_at": milestone.created_at.isoformat() if milestone.created_at else None,
            "updated_at": milestone.updated_at.isoformat() if milestone.updated_at else None
        }

    def update_milestone(
        self,
        milestone_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        user_rating: Optional[int] = None,
        user_note: Optional[str] = None,
        db_session_param: Optional[Any] = None
    ) -> bool:
        """更新里程碑"""
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session() as db:
                    return self._update_milestone_internal(milestone_id, title, description, user_rating, user_note, db)
            else:
                return self._update_milestone_internal(milestone_id, title, description, user_rating, user_note, db_session_param)
        finally:
            if use_context:
                pass

    def _update_milestone_internal(
        self,
        milestone_id: str,
        title: Optional[str],
        description: Optional[str],
        user_rating: Optional[int],
        user_note: Optional[str],
        db
    ) -> bool:
        """更新里程碑内部方法"""
        milestone = db.query(RelationshipMilestoneDB).filter(
            RelationshipMilestoneDB.id == milestone_id
        ).first()

        if not milestone:
            return False

        if title is not None:
            milestone.title = title
        if description is not None:
            milestone.description = description
        if user_rating is not None:
            milestone.user_rating = user_rating
        if user_note is not None:
            milestone.user_note = user_note

        db.commit()
        logger.info(f"Updated milestone: {milestone_id}")
        return True

    def celebrate_milestone(
        self,
        milestone_id: str,
        celebration_type: str = "card",
        user_id: Optional[str] = None,
        db_session_param: Optional[Any] = None
    ) -> bool:
        """庆祝里程碑"""
        if db_session_param:
            db = db_session_param
            use_context = False
        else:
            use_context = True

        try:
            if use_context:
                with db_session() as db:
                    return self._celebrate_milestone_internal(milestone_id, celebration_type, db)
            else:
                return self._celebrate_milestone_internal(milestone_id, celebration_type, db_session_param)
        finally:
            if use_context:
                pass

    def _celebrate_milestone_internal(
        self,
        milestone_id: str,
        celebration_type: str,
        db
    ) -> bool:
        """庆祝里程碑内部方法"""
        milestone = db.query(RelationshipMilestoneDB).filter(
            RelationshipMilestoneDB.id == milestone_id
        ).first()

        if not milestone:
            return False

        # 更新庆祝状态
        milestone.celebration_suggested = True
        milestone.celebration_type = celebration_type

        # 记录庆祝行为（可以扩展到创建庆祝记录）
        celebration_description = CELEBRATION_SUGGESTIONS.get(
            MILESTONE_TYPES_P10.get(milestone.milestone_type, {}).get("category", "beginning"),
            {}
        ).get("description", f"用{celebration_type}庆祝这个特别时刻")

        milestone.celebration_description = celebration_description

        db.commit()
        logger.info(f"Celebrated milestone: {milestone_id} with type: {celebration_type}")
        return True


# 全局服务实例
relationship_milestone_service = RelationshipMilestoneService()
