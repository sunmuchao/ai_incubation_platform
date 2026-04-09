"""
P18 关系进阶服务 - v1.18 关系进阶功能

服务列表:
- RelationshipStateService: 关系状态管理服务
- DatingAdviceService: 约会建议生成服务
- LoveGuidanceService: 恋爱指导服务
- GiftRecommendationService: 礼物推荐服务
- ChatSuggestionService: 聊天建议服务
- RelationshipHealthService: 关系健康度分析服务
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
import uuid
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.orm import Session

from db.database import SessionLocal
from models.p18_models import (
    RelationshipStateDB, RelationshipStateTransitionDB,
    DatingAdviceDB, DatingVenueDB,
    LoveGuidanceDB, ChatSuggestionDB, GiftRecommendationDB,
    RelationshipHealthDB, RelationshipCheckInDB,
    RelationshipAnniversaryDB, RelationshipGoalDB,
    RelationshipPatternDB, RelationshipNotificationDB
)
from db.models import UserDB, MatchHistoryDB, ChatMessageDB, ChatConversationDB
from utils.logger import logger
from utils.db_session_manager import db_session, db_session_readonly


# ============= 关系状态定义 =============

RELATIONSHIP_STATES = {
    "matched": {"order": 1, "label": "已匹配", "description": "系统匹配成功"},
    "chatting": {"order": 2, "label": "聊天中", "description": "开始互动交流"},
    "ambiguity": {"order": 3, "label": "暧昧期", "description": "互有好感但未明确关系"},
    "dating": {"order": 4, "label": "约会中", "description": "定期约会阶段"},
    "exclusive": {"order": 5, "label": "确定关系", "description": "确立排他性关系"},
    "in_relationship": {"order": 6, "label": "恋爱中", "description": "稳定恋爱关系"},
    "engaged": {"order": 7, "label": "已订婚", "description": "已订婚"},
    "married": {"order": 8, "label": "已结婚", "description": "步入婚姻殿堂"},
    "separated": {"order": 9, "label": "已分居", "description": "暂时分居"},
    "broken_up": {"order": 10, "label": "已分手", "description": "结束关系"}
}

TRANSITION_TYPES = {
    "manual": "用户手动设置",
    "ai_detected": "AI 自动识别",
    "mutual_agreement": "双方共同确认"
}


class RelationshipStateService:
    """关系状态管理服务"""

    def __init__(self) -> None:
        self._state_transition_rules = {
            "matched": ["chatting", "rejected"],
            "chatting": ["ambiguity", "dating", "rejected"],
            "ambiguity": ["dating", "exclusive", "chatting", "rejected"],
            "dating": ["exclusive", "in_relationship", "ambiguity", "broken_up"],
            "exclusive": ["in_relationship", "dating", "broken_up"],
            "in_relationship": ["engaged", "exclusive", "broken_up"],
            "engaged": ["married", "in_relationship", "broken_up"],
            "married": ["separated", "divorced"],
            "separated": ["married", "broken_up"],
            "broken_up": ["chatting", "matched"]  # 复合
        }

    def get_relationship_state(
        self,
        user_id_1: str,
        user_id_2: str
    ) -> Optional[Dict[str, Any]]:
        """获取关系状态"""
        with db_session_readonly() as db:
            state = db.query(RelationshipStateDB).filter(
                and_(
                    or_(
                        and_(RelationshipStateDB.user_id_1 == user_id_1, RelationshipStateDB.user_id_2 == user_id_2),
                        and_(RelationshipStateDB.user_id_1 == user_id_2, RelationshipStateDB.user_id_2 == user_id_1)
                    )
                )
            ).first()

            if not state:
                return None

            return {
                "id": state.id,
                "state": state.state,
                "state_label": state.state_label or RELATIONSHIP_STATES.get(state.state, {}).get("label", state.state),
                "state_description": state.state_description,
                "confirmed_by_user1": state.confirmed_by_user1,
                "confirmed_by_user2": state.confirmed_by_user2,
                "state_changed_at": state.state_changed_at.isoformat() if state.state_changed_at else None,
                "ai_confidence": state.ai_confidence,
                "created_at": state.created_at.isoformat()
            }

    def set_relationship_state(
        self,
        user_id_1: str,
        user_id_2: str,
        new_state: str,
        transition_type: str = "manual",
        transition_reason: Optional[str] = None,
        trigger_event: Optional[str] = None,
        user_id_setting: Optional[str] = None
    ) -> str:
        """设置关系状态"""
        if new_state not in RELATIONSHIP_STATES:
            raise ValueError(f"Invalid state: {new_state}")

        with db_session() as db:
            # 获取或创建关系状态记录
            state = db.query(RelationshipStateDB).filter(
                and_(
                    or_(
                        and_(RelationshipStateDB.user_id_1 == user_id_1, RelationshipStateDB.user_id_2 == user_id_2),
                        and_(RelationshipStateDB.user_id_1 == user_id_2, RelationshipStateDB.user_id_2 == user_id_1)
                    )
                )
            ).first()

            old_state = None
            if state:
                old_state = state.state
                # 检查状态转换是否合法
                if old_state and old_state in self._state_transition_rules:
                    allowed_transitions = self._state_transition_rules.get(old_state, [])
                    # 允许任何转换,但记录警告
                    if new_state not in allowed_transitions:
                        logger.warning(f"Unusual state transition from {old_state} to {new_state}")
            else:
                # 创建新记录
                state_id = str(uuid.uuid4())
                state = RelationshipStateDB(
                    id=state_id,
                    user_id_1=user_id_1,
                    user_id_2=user_id_2,
                    state=new_state,
                    state_label=RELATIONSHIP_STATES.get(new_state, {}).get("label", new_state),
                    state_description=RELATIONSHIP_STATES.get(new_state, {}).get("description", "")
                )
                db.add(state)

            # 记录状态变更历史
            if old_state != new_state:
                self._record_state_transition(
                    db, user_id_1, user_id_2, old_state, new_state,
                    transition_type, transition_reason, trigger_event
                )

                # 更新状态
                previous_state = state.state
                state.state = new_state
                state.state_label = RELATIONSHIP_STATES.get(new_state, {}).get("label", new_state)
                state.state_description = RELATIONSHIP_STATES.get(new_state, {}).get("description", "")
                state.previous_state = previous_state
                state.state_changed_at = datetime.now()
                state.state_change_reason = transition_reason

                # 如果是用户主动设置,标记为已确认
                if user_id_setting == user_id_1:
                    state.confirmed_by_user1 = True
                elif user_id_setting == user_id_2:
                    state.confirmed_by_user2 = True

                # 如果双方都确认,设置确认时间
                if state.confirmed_by_user1 and state.confirmed_by_user2 and not state.confirmed_at:
                    state.confirmed_at = datetime.now()

            db.commit()
            db.refresh(state)

            logger.info(f"Relationship state updated: {old_state} -> {new_state} for {user_id_1} & {user_id_2}")
            return state.id

    def _record_state_transition(
        self,
        db,
        user_id_1: str,
        user_id_2: str,
        from_state: Optional[str],
        to_state: str,
        transition_type: str,
        transition_reason: Optional[str],
        trigger_event: Optional[str]
    ):
        """记录状态变更历史"""
        transition_id = str(uuid.uuid4())
        transition = RelationshipStateTransitionDB(
            id=transition_id,
            user_id_1=user_id_1,
            user_id_2=user_id_2,
            from_state=from_state,
            to_state=to_state,
            to_state_label=RELATIONSHIP_STATES.get(to_state, {}).get("label", to_state),
            transition_type=transition_type,
            transition_reason=transition_reason,
            trigger_event=trigger_event,
            ai_comment=self._generate_ai_comment(from_state, to_state),
            next_stage_suggestions=json.dumps(self._get_next_stage_suggestions(to_state))
        )
        db.add(transition)

    def _generate_ai_comment(self, from_state: Optional[str], to_state: str) -> str:
        """生成 AI 评论"""
        comments = {
            (None, "matched"): "美好的相遇从这里开始！",
            ("matched", "chatting"): "开始交流是了解彼此的第一步！",
            ("chatting", "ambiguity"): "心动的感觉,也许就是暧昧的美好～",
            ("ambiguity", "dating"): "从暧昧到约会,关系更进一步！",
            ("dating", "exclusive"): "确定排他性关系,这是重要的承诺！",
            ("exclusive", "in_relationship"): "稳定的恋爱关系,愿你们携手成长！",
            ("in_relationship", "engaged"): "订婚是通往婚姻的承诺,祝福你们！",
            ("engaged", "married"): "步入婚姻殿堂,开始人生的新篇章！",
        }
        return comments.get((from_state, to_state), f"恭喜你们的关系进入新阶段：{RELATIONSHIP_STATES.get(to_state, {}).get('label', to_state)}！")

    def _get_next_stage_suggestions(self, current_state: str) -> List[Dict[str, str]]:
        """获取下一阶段建议"""
        suggestions = {
            "matched": [
                {"action": "发起对话", "description": "用破冰话题开始交流"},
                {"action": "了解兴趣", "description": "探索共同的兴趣爱好"}
            ],
            "chatting": [
                {"action": "深入交流", "description": "分享更多个人信息和价值观"},
                {"action": "安排见面", "description": "考虑安排第一次线下约会"}
            ],
            "ambiguity": [
                {"action": "明确心意", "description": "坦诚交流彼此的感受"},
                {"action": "增加互动", "description": "创造更多独处机会"}
            ],
            "dating": [
                {"action": "定义关系", "description": "讨论彼此的关系期待"},
                {"action": "融入生活", "description": "逐渐融入彼此的社交圈"}
            ],
            "exclusive": [
                {"action": "稳定发展", "description": "建立健康的相处模式"},
                {"action": "规划未来", "description": "讨论长期关系目标"}
            ],
            "in_relationship": [
                {"action": "深化关系", "description": "一起规划未来"},
                {"action": "见家长", "description": "考虑见双方家长"}
            ]
        }
        return suggestions.get(current_state, [{"action": "继续经营", "description": "用心经营你们的关系"}])

    def get_state_history(
        self,
        user_id_1: str,
        user_id_2: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取关系状态变更历史"""
        with db_session_readonly() as db:
            transitions = db.query(RelationshipStateTransitionDB).filter(
                and_(
                    or_(
                        and_(RelationshipStateTransitionDB.user_id_1 == user_id_1, RelationshipStateTransitionDB.user_id_2 == user_id_2),
                        and_(RelationshipStateTransitionDB.user_id_1 == user_id_2, RelationshipStateTransitionDB.user_id_2 == user_id_1)
                    )
                )
            ).order_by(desc(RelationshipStateTransitionDB.created_at)).limit(limit).all()

            history = []
            for t in transitions:
                history.append({
                    "id": t.id,
                    "from_state": t.from_state,
                    "from_state_label": RELATIONSHIP_STATES.get(t.from_state, {}).get("label", t.from_state) if t.from_state else None,
                    "to_state": t.to_state,
                    "to_state_label": t.to_state_label,
                    "transition_type": t.transition_type,
                    "transition_reason": t.transition_reason,
                    "trigger_event": t.trigger_event,
                    "ai_comment": t.ai_comment,
                    "next_stage_suggestions": json.loads(t.next_stage_suggestions) if t.next_stage_suggestions else None,
                    "created_at": t.created_at.isoformat()
                })
            return history

    def confirm_relationship_state(
        self,
        user_id_1: str,
        user_id_2: str,
        confirming_user_id: str
    ) -> bool:
        """确认关系状态"""
        with db_session() as db:
            state = db.query(RelationshipStateDB).filter(
                and_(
                    or_(
                        and_(RelationshipStateDB.user_id_1 == user_id_1, RelationshipStateDB.user_id_2 == user_id_2),
                        and_(RelationshipStateDB.user_id_1 == user_id_2, RelationshipStateDB.user_id_2 == user_id_1)
                    )
                )
            ).first()

            if not state:
                return False

            # 根据确认用户设置对应的确认标记
            if confirming_user_id == user_id_1:
                state.confirmed_by_user1 = True
            elif confirming_user_id == user_id_2:
                state.confirmed_by_user2 = True
            else:
                return False

            # 如果双方都确认,设置确认时间
            if state.confirmed_by_user1 and state.confirmed_by_user2:
                state.confirmed_at = datetime.now()

            db.commit()
            return True


# ============= 约会建议服务 =============

class DatingAdviceService:
    """约会建议生成服务"""

    def __init__(self):
        self._date_templates = {
            "first_date": [
                {"type": "cafe", "duration": 60, "cost_level": 1, "description": "轻松的咖啡厅约会,便于交流"},
                {"type": "museum", "duration": 120, "cost_level": 2, "description": "博物馆参观,边看边聊"},
                {"type": "park", "duration": 90, "cost_level": 0, "description": "公园散步,自然轻松"}
            ],
            "anniversary": [
                {"type": "restaurant", "duration": 120, "cost_level": 3, "description": "浪漫餐厅共进晚餐"},
                {"type": "activity", "duration": 180, "cost_level": 2, "description": "特别体验活动"},
                {"type": "travel", "duration": 480, "cost_level": 3, "description": "短途旅行"}
            ],
            "routine": [
                {"type": "movie", "duration": 150, "cost_level": 2, "description": "看电影 + 讨论"},
                {"type": "cooking", "duration": 180, "cost_level": 1, "description": "一起做饭"},
                {"type": "walk", "duration": 60, "cost_level": 0, "description": "夜晚散步"}
            ]
        }

    def generate_advice(
        self,
        user_id: str,
        target_user_id: Optional[str] = None,
        advice_type: str = "first_date",
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> str:
        """生成约会建议"""
        with db_session() as db:
            advice_id = str(uuid.uuid4())

            # 获取用户信息
            user = db.query(UserDB).filter(UserDB.id == user_id).first()
            if not user:
                raise ValueError(f"User not found: {user_id}")

            # 获取约会对象信息
            target_user = None
            if target_user_id:
                target_user = db.query(UserDB).filter(UserDB.id == target_user_id).first()

            # 生成建议
            templates = self._date_templates.get(advice_type, self._date_templates["routine"])
            template = templates[0]  # 简化：选择第一个模板

            # AI 生成reasoning
            reasoning = self._generate_reasoning(user, target_user, advice_type, template)

            # 获取推荐地点
            venue_suggestions = self._get_venue_suggestions(db, user.location, template["type"])

            advice = DatingAdviceDB(
                id=advice_id,
                user_id=user_id,
                target_user_id=target_user_id,
                advice_type=advice_type,
                title=self._generate_title(advice_type, template),
                description=template["description"],
                activity_type=template["type"],
                venue_suggestions=json.dumps(venue_suggestions),
                estimated_cost=template["cost_level"] * 100,
                estimated_duration=template["duration"],
                best_timing="周末下午或晚上",
                reasoning=reasoning,
                confidence_score=0.8,
                expires_at=datetime.now() + timedelta(days=7)
            )
            db.add(advice)
            db.commit()
            db.refresh(advice)

            logger.info(f"Generated dating advice: {advice_type} for {user_id}")
            return advice_id

    def _generate_title(self, advice_type: str, template: Dict) -> str:
        """生成建议标题"""
        titles = {
            "first_date": f"首次约会建议：{template['description'][:10]}",
            "anniversary": "纪念日特别策划",
            "routine": "日常约会灵感"
        }
        return titles.get(advice_type, "约会建议")

    def _generate_reasoning(self, user, target_user, advice_type: str, template: Dict) -> str:
        """生成reasoning"""
        if target_user:
            return f"基于您和对方的兴趣匹配,{template['type']}类型的活动能让你们在轻松的氛围中加深了解。"
        return f"根据您的偏好,{template['type']}类型的活动是一个不错的选择。"

    def _get_venue_suggestions(self, db, location: str, venue_type: str) -> List[Dict]:
        """获取地点推荐"""
        venues = db.query(DatingVenueDB).filter(
            DatingVenueDB.city == location,
            DatingVenueDB.venue_type == venue_type,
            DatingVenueDB.is_active == True
        ).limit(3).all()

        return [
            {
                "name": v.venue_name,
                "address": v.address,
                "rating": v.rating,
                "price_level": v.price_level
            }
            for v in venues
        ]

    def get_advice(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取用户的约会建议"""
        with db_session_readonly() as db:
            query = db.query(DatingAdviceDB).filter(DatingAdviceDB.user_id == user_id)

            if status:
                query = query.filter(DatingAdviceDB.status == status)

            advices = query.order_by(desc(DatingAdviceDB.created_at)).limit(limit).all()

            return [
                {
                    "id": a.id,
                    "advice_type": a.advice_type,
                    "title": a.title,
                    "description": a.description,
                    "activity_type": a.activity_type,
                    "venue_suggestions": json.loads(a.venue_suggestions) if a.venue_suggestions else [],
                    "estimated_cost": a.estimated_cost,
                    "estimated_duration": a.estimated_duration,
                    "reasoning": a.reasoning,
                    "status": a.status,
                    "confidence_score": a.confidence_score,
                    "created_at": a.created_at.isoformat()
                }
                for a in advices
            ]

    def accept_advice(self, advice_id: str) -> bool:
        """接受约会建议"""
        with db_session() as db:
            advice = db.query(DatingAdviceDB).filter(DatingAdviceDB.id == advice_id).first()
            if not advice:
                return False

            advice.status = "accepted"
            advice.accepted_at = datetime.now()
            db.commit()
            return True


# ============= 恋爱指导服务 =============

class LoveGuidanceService:
    """恋爱指导服务"""

    def generate_guidance(
        self,
        user_id: str,
        guidance_type: str,
        scenario: Optional[str] = None,
        target_user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """生成恋爱指导"""
        with db_session() as db:
            guidance_id = str(uuid.uuid4())

            # 获取用户信息
            user = db.query(UserDB).filter(UserDB.id == user_id).first()
            if not user:
                raise ValueError(f"User not found: {user_id}")

            # 生成指导内容
            title, content, step_by_step = self._generate_guidance_content(guidance_type, scenario, context)

            guidance = LoveGuidanceDB(
                id=guidance_id,
                user_id=user_id,
                target_user_id=target_user_id,
                guidance_type=guidance_type,
                title=title,
                content=content,
                scenario=scenario or "",
                step_by_step_guide=json.dumps(step_by_step),
                dos_and_donts=json.dumps(self._get_dos_and_donts(guidance_type)),
                reasoning=self._generate_reasoning(guidance_type),
                confidence_score=0.75
            )
            db.add(guidance)
            db.commit()
            db.refresh(guidance)

            logger.info(f"Generated love guidance: {guidance_type} for {user_id}")
            return guidance_id

    def _generate_guidance_content(self, guidance_type: str, scenario: Optional[str], context: Optional[Dict]) -> Tuple[str, str, List]:
        """生成指导内容"""
        templates = {
            "chat_advice": (
                "聊天技巧指南",
                "良好的沟通是关系发展的基础。以下是一些实用的聊天技巧。",
                [
                    {"step": 1, "action": "倾听对方", "description": "专注听对方说话,不要急于表达"},
                    {"step": 2, "action": "提问互动", "description": "用开放式问题鼓励对方分享"},
                    {"step": 3, "action": "分享感受", "description": "适当分享自己的想法和感受"},
                    {"step": 4, "action": "保持轻松", "description": "不要给自己太大压力,自然交流"}
                ]
            ),
            "gift_recommendation": (
                "礼物选择指南",
                "选择礼物最重要的是心意和对对方的了解。",
                [
                    {"step": 1, "action": "了解喜好", "description": "回忆对方提到过的兴趣爱好"},
                    {"step": 2, "action": "考虑场合", "description": "根据场合选择合适类型的礼物"},
                    {"step": 3, "action": "个性化定制", "description": "加入个人元素让礼物更有意义"},
                    {"step": 4, "action": "准备惊喜", "description": "包装和赠送方式也很重要"}
                ]
            ),
            "conflict_resolution": (
                "冲突解决指南",
                "冲突是关系中难免的,关键是如何处理。",
                [
                    {"step": 1, "action": "冷静下来", "description": "不要在情绪激动时沟通"},
                    {"step": 2, "action": "倾听对方", "description": "理解对方的立场和感受"},
                    {"step": 3, "action": "表达自己", "description": "用'我感到'而非'你总是'表达"},
                    {"step": 4, "action": "寻求共识", "description": "一起找到双方都能接受的解决方案"}
                ]
            ),
            "date_invitation": (
                "约会邀请指南",
                "发出约会邀请需要真诚和自然。",
                [
                    {"step": 1, "action": "选择时机", "description": "在轻松愉快的对话中提出"},
                    {"step": 2, "action": "具体建议", "description": "提出具体的时间地点活动"},
                    {"step": 3, "action": "留有余地", "description": "给对方拒绝的空间"},
                    {"step": 4, "action": "准备好 B 计划", "description": "如果原计划不行,有备选方案"}
                ]
            )
        }

        default = (
            "恋爱指南",
            "这是一份针对您的情况定制的恋爱指南。",
            [{"step": 1, "action": "了解自己", "description": "明确自己的需求和期待"}]
        )

        return templates.get(guidance_type, default)

    def _get_dos_and_donts(self, guidance_type: str) -> Dict[str, List[str]]:
        """获取应该做和不应该做的事"""
        guidelines = {
            "chat_advice": {
                "dos": ["保持真诚", "积极倾听", "适时赞美", "保持好奇心"],
                "donts": ["打断对方", "过度谈论自己", "查户口式提问", "消极回应"]
            },
            "gift_recommendation": {
                "dos": ["考虑对方喜好", "注重心意", "适当包装", "附上卡片"],
                "donts": ["过于昂贵", "太个人化", "忽略场合", "临时抱佛脚"]
            },
            "conflict_resolution": {
                "dos": ["冷静沟通", "理解对方", "承认错误", "寻求解决"],
                "donts": ["冷战", "人身攻击", "翻旧账", "威胁分手"]
            }
        }
        return guidelines.get(guidance_type, {"dos": ["真诚对待"], "donts": ["勉强自己"]})

    def _generate_reasoning(self, guidance_type: str) -> str:
        """生成建议依据"""
        reasons = {
            "chat_advice": "基于心理学研究和成功关系案例",
            "gift_recommendation": "结合礼物心理学和用户体验研究",
            "conflict_resolution": "基于关系治疗师的专业建议",
            "date_invitation": "基于社交心理学和约会专家建议"
        }
        return reasons.get(guidance_type, "基于专业研究和实践经验")

    def get_guidance(
        self,
        user_id: str,
        guidance_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取用户的恋爱指导"""
        with db_session_readonly() as db:
            query = db.query(LoveGuidanceDB).filter(LoveGuidanceDB.user_id == user_id)

            if guidance_type:
                query = query.filter(LoveGuidanceDB.guidance_type == guidance_type)

            guidances = query.order_by(desc(LoveGuidanceDB.created_at)).limit(limit).all()

            return [
                {
                    "id": g.id,
                    "guidance_type": g.guidance_type,
                    "title": g.title,
                    "content": g.content,
                    "step_by_step_guide": json.loads(g.step_by_step_guide) if g.step_by_step_guide else [],
                    "dos_and_donts": json.loads(g.dos_and_donts) if g.dos_and_donts else {},
                    "is_read": g.is_read,
                    "is_actioned": g.is_actioned,
                    "created_at": g.created_at.isoformat()
                }
                for g in guidances
            ]


# ============= 聊天建议服务 =============

class ChatSuggestionService:
    """聊天建议服务"""

    def __init__(self):
        self._suggestion_templates = {
            "opener": [
                "嗨！看到你也在 [共同兴趣],有什么推荐的吗？",
                "今天过得怎么样？看你照片好像去了很有趣的地方～",
                "刚才看到你的资料,发现我们都喜欢 [共同兴趣],很高兴认识你！"
            ],
            "topic": [
                "聊聊最近看的电影/书籍吧",
                "分享一个最近的开心事",
                "问问对方的周末计划"
            ],
            "compliment": [
                "你的笑容很有感染力,看到心情都变好了",
                "你说话很有深度,和你聊天很愉快",
                "你的 [具体特点] 很特别,让人印象深刻"
            ],
            "date_invitation": [
                "最近发现一家不错的咖啡厅,有空一起去坐坐？",
                "这个展览好像很有趣,有兴趣一起去看看吗？",
                "天气不错,周末要不要一起去公园走走？"
            ]
        }

    def generate_suggestion(
        self,
        user_id: str,
        suggestion_type: str,
        conversation_id: Optional[str] = None,
        target_user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """生成聊天建议"""
        with db_session() as db:
            suggestion_id = str(uuid.uuid4())

            # 获取模板建议
            templates = self._suggestion_templates.get(suggestion_type, self._suggestion_templates["topic"])
            suggested_text = templates[0]  # 简化：选择第一个

            # 如果有上下文,尝试个性化
            if context:
                if "common_interest" in context:
                    suggested_text = suggested_text.replace("[共同兴趣]", context["common_interest"])

            suggestion = ChatSuggestionDB(
                id=suggestion_id,
                user_id=user_id,
                conversation_id=conversation_id,
                target_user_id=target_user_id,
                suggestion_type=suggestion_type,
                suggested_text=suggested_text,
                alternative_texts=json.dumps(templates[1:3] if len(templates) > 1 else []),
                context=context.get("description") if context else None,
                tone=self._get_tone_for_type(suggestion_type),
                confidence_score=0.7
            )
            db.add(suggestion)
            db.commit()
            db.refresh(suggestion)

            logger.info(f"Generated chat suggestion: {suggestion_type} for {user_id}")
            return suggestion_id

    def _get_tone_for_type(self, suggestion_type: str) -> str:
        """根据建议类型获取语气"""
        tones = {
            "opener": "casual",
            "topic": "casual",
            "response": "sincere",
            "compliment": "sincere",
            "date_invitation": "casual",
            "confession": "romantic",
            "comfort": "sincere"
        }
        return tones.get(suggestion_type, "casual")

    def get_suggestions(
        self,
        user_id: str,
        suggestion_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取用户的聊天建议"""
        with db_session_readonly() as db:
            query = db.query(ChatSuggestionDB).filter(ChatSuggestionDB.user_id == user_id)

            if suggestion_type:
                query = query.filter(ChatSuggestionDB.suggestion_type == suggestion_type)

            suggestions = query.order_by(desc(ChatSuggestionDB.created_at)).limit(limit).all()

            return [
                {
                    "id": s.id,
                    "suggestion_type": s.suggestion_type,
                    "suggested_text": s.suggested_text,
                    "alternative_texts": json.loads(s.alternative_texts) if s.alternative_texts else [],
                    "tone": s.tone,
                    "confidence_score": s.confidence_score,
                    "status": s.status,
                    "created_at": s.created_at.isoformat()
                }
                for s in suggestions
            ]

    def mark_used(self, suggestion_id: str) -> bool:
        """标记建议已使用"""
        with db_session() as db:
            suggestion = db.query(ChatSuggestionDB).filter(ChatSuggestionDB.id == suggestion_id).first()
            if not suggestion:
                return False

            suggestion.status = "used"
            suggestion.used_at = datetime.now()
            db.commit()
            return True


# ============= 礼物推荐服务 =============

class GiftRecommendationService:
    """礼物推荐服务"""

    def __init__(self):
        self._gift_templates = {
            "birthday": [
                {"name": "定制相册", "category": "个性化", "price": (100, 300), "description": "收集你们的照片制作成册"},
                {"name": "香薰蜡烛", "category": "生活用品", "price": (50, 200), "description": "营造浪漫氛围"},
                {"name": "手写信件", "category": "个性化", "price": (0, 50), "description": "用心写下你的感受"}
            ],
            "anniversary": [
                {"name": "情侣对戒", "category": "首饰", "price": (200, 1000), "description": "象征你们的爱情"},
                {"name": "纪念视频", "category": "个性化", "price": (0, 200), "description": "记录美好回忆"},
                {"name": "情侣装", "category": "服饰", "price": (200, 500), "description": "穿出自己的风格"}
            ],
            "valentines": [
                {"name": "巧克力礼盒", "category": "食品", "price": (100, 300), "description": "甜蜜的心意"},
                {"name": "玫瑰花束", "category": "鲜花", "price": (200, 500), "description": "经典的浪漫"},
                {"name": "情侣体验", "category": "体验", "price": (300, 1000), "description": "一起创造回忆"}
            ],
            "just_because": [
                {"name": "小零食礼包", "category": "食品", "price": (50, 150), "description": "日常的小惊喜"},
                {"name": "可爱小物", "category": "生活用品", "price": (50, 200), "description": "看到就会想起你"},
                {"name": "手写便签", "category": "个性化", "price": (0, 20), "description": "暖心的小纸条"}
            ]
        }

    def generate_recommendation(
        self,
        user_id: str,
        occasion: str,
        recipient_user_id: Optional[str] = None,
        budget_range: Optional[Tuple[float, float]] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> str:
        """生成礼物推荐"""
        with db_session() as db:
            recommendation_id = str(uuid.uuid4())

            # 获取礼物模板
            templates = self._gift_templates.get(occasion, self._gift_templates["just_because"])

            # 根据预算筛选
            if budget_range:
                templates = [t for t in templates if t["price"][0] <= budget_range[1] and t["price"][1] >= budget_range[0]]

            gift = templates[0] if templates else templates[0]

            recommendation = GiftRecommendationDB(
                id=recommendation_id,
                user_id=user_id,
                recipient_user_id=recipient_user_id,
                occasion=occasion,
                gift_name=gift["name"],
                gift_description=gift["description"],
                gift_category=gift["category"],
                price_range_min=gift["price"][0],
                price_range_max=gift["price"][1],
               reasoning=self._generate_reasoning(gift, occasion),
                confidence_score=0.75,
                personalization_tips=json.dumps(self._get_personalization_tips(gift))
            )
            db.add(recommendation)
            db.commit()
            db.refresh(recommendation)

            logger.info(f"Generated gift recommendation: {gift['name']} for {user_id}")
            return recommendation_id

    def _generate_reasoning(self, gift: Dict, occasion: str) -> str:
        """生成reasoning"""
        return f"{gift['name']}是一个{gift['category']}类型的礼物,{gift['description']}。适合作为{occasion}礼物。"

    def _get_personalization_tips(self, gift: Dict) -> List[str]:
        """获取个性化建议"""
        tips = {
            "个性化": ["加入你们的照片", "写下专属的话", "选择有意义的日期"],
            "首饰": ["注意对方的尺寸", "选择对方喜欢的风格", "可以刻字增加意义"],
            "食品": ["考虑对方的口味偏好", "注意保质期", "选择包装精美的"],
            "鲜花": ["了解对方喜欢的花", "注意花的寓意", "考虑保鲜问题"],
            "体验": ["提前预订", "考虑对方的时间安排", "准备备选方案"]
        }
        return tips.get(gift.get("category", "其他"), ["用心准备最重要"])

    def get_recommendations(
        self,
        user_id: str,
        occasion: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取用户的礼物推荐"""
        with db_session_readonly() as db:
            query = db.query(GiftRecommendationDB).filter(GiftRecommendationDB.user_id == user_id)

            if occasion:
                query = query.filter(GiftRecommendationDB.occasion == occasion)

            recommendations = query.order_by(desc(GiftRecommendationDB.created_at)).limit(limit).all()

            return [
                {
                    "id": r.id,
                    "occasion": r.occasion,
                    "gift_name": r.gift_name,
                    "gift_description": r.gift_description,
                    "gift_category": r.gift_category,
                    "price_range": {"min": r.price_range_min, "max": r.price_range_max},
                    "reasoning": r.reasoning,
                    "personalization_tips": json.loads(r.personalization_tips) if r.personalization_tips else [],
                    "status": r.status,
                    "created_at": r.created_at.isoformat()
                }
                for r in recommendations
            ]


# ============= 关系健康度服务 =============

class RelationshipHealthService:
    """关系健康度分析服务"""

    def assess_relationship_health(
        self,
        user_id_1: str,
        user_id_2: str
    ) -> Dict[str, Any]:
        """评估关系健康度"""
        with db_session() as db:
            # 收集数据
            metrics = self._collect_relationship_metrics(db, user_id_1, user_id_2)

            # 计算各维度得分
            communication_score = self._calculate_communication_score(metrics)
            trust_score = self._calculate_trust_score(metrics)
            intimacy_score = self._calculate_intimacy_score(metrics)
            commitment_score = self._calculate_commitment_score(metrics)
            compatibility_score = self._calculate_compatibility_score(metrics)

            # 综合得分
            overall_score = (
                communication_score * 0.25 +
                trust_score * 0.25 +
                intimacy_score * 0.20 +
                commitment_score * 0.15 +
                compatibility_score * 0.15
            )

            # 健康等级
            health_level = self._get_health_level(overall_score)

            # 生成分析
            strengths, growth_areas = self._analyze_relationship(
                communication_score, trust_score, intimacy_score,
                commitment_score, compatibility_score
            )

            # 保存评估结果
            assessment_id = str(uuid.uuid4())
            assessment = RelationshipHealthDB(
                id=assessment_id,
                user_id_1=user_id_1,
                user_id_2=user_id_2,
                communication_score=communication_score,
                trust_score=trust_score,
                intimacy_score=intimacy_score,
                commitment_score=commitment_score,
                compatibility_score=compatibility_score,
                overall_score=overall_score,
                health_level=health_level,
                strengths=json.dumps(strengths),
                growth_areas=json.dumps(growth_areas),
                suggestions=json.dumps(self._generate_suggestions(growth_areas)),
                assessment_date=datetime.now()
            )
            db.add(assessment)
            db.commit()

            return {
                "assessment_id": assessment_id,
                "overall_score": round(overall_score, 2),
                "health_level": health_level,
                "dimensions": {
                    "communication": round(communication_score, 2),
                    "trust": round(trust_score, 2),
                    "intimacy": round(intimacy_score, 2),
                    "commitment": round(commitment_score, 2),
                    "compatibility": round(compatibility_score, 2)
                },
                "strengths": strengths,
                "growth_areas": growth_areas,
                "suggestions": self._generate_suggestions(growth_areas)
            }

    def _collect_relationship_metrics(self, db, user_id_1: str, user_id_2: str) -> Dict:
        """收集关系指标数据"""
        # 消息数量
        message_count = db.query(ChatMessageDB).filter(
            or_(
                and_(ChatMessageDB.sender_id == user_id_1, ChatMessageDB.receiver_id == user_id_2),
                and_(ChatMessageDB.sender_id == user_id_2, ChatMessageDB.receiver_id == user_id_1)
            )
        ).count()

        # 最近互动时间
        last_interaction = db.query(ChatMessageDB).filter(
            or_(
                and_(ChatMessageDB.sender_id == user_id_1, ChatMessageDB.receiver_id == user_id_2),
                and_(ChatMessageDB.sender_id == user_id_2, ChatMessageDB.receiver_id == user_id_1)
            )
        ).order_by(desc(ChatMessageDB.created_at)).first()

        # 关系天数
        first_message = db.query(ChatMessageDB).filter(
            or_(
                and_(ChatMessageDB.sender_id == user_id_1, ChatMessageDB.receiver_id == user_id_2),
                and_(ChatMessageDB.sender_id == user_id_2, ChatMessageDB.receiver_id == user_id_1)
            )
        ).order_by(ChatMessageDB.created_at).first()

        relationship_days = 1
        if first_message and last_interaction:
            relationship_days = max(1, (last_interaction.created_at - first_message.created_at).days)

        return {
            "message_count": message_count,
            "relationship_days": relationship_days,
            "last_interaction": last_interaction.created_at if last_interaction else None
        }

    def _calculate_communication_score(self, metrics: Dict) -> float:
        """计算沟通质量得分"""
        # 基于消息频率和关系天数的比值
        if metrics["relationship_days"] == 0:
            return 5.0

        msg_per_day = metrics["message_count"] / metrics["relationship_days"]

        # 0-2 条/天：1 分,10+ 条/天：10 分
        score = min(10, msg_per_day)
        return score

    def _calculate_trust_score(self, metrics: Dict) -> float:
        """计算信任度得分"""
        # 简化：基于关系持续时间
        days = metrics["relationship_days"]
        if days >= 180:
            return 8.0
        elif days >= 90:
            return 7.0
        elif days >= 30:
            return 6.0
        elif days >= 7:
            return 5.0
        else:
            return 4.0

    def _calculate_intimacy_score(self, metrics: Dict) -> float:
        """计算亲密度得分"""
        # 简化：基于消息数量
        msg_count = metrics["message_count"]
        if msg_count >= 500:
            return 8.0
        elif msg_count >= 200:
            return 7.0
        elif msg_count >= 100:
            return 6.0
        elif msg_count >= 50:
            return 5.0
        else:
            return 4.0

    def _calculate_commitment_score(self, metrics: Dict) -> float:
        """计算承诺度得分"""
        # 简化：基于关系持续时间和互动稳定性
        days = metrics["relationship_days"]
        base_score = min(10, days / 30)  # 每月 1 分,最多 10 分
        return base_score

    def _calculate_compatibility_score(self, metrics: Dict) -> float:
        """计算兼容性得分"""
        # 简化：返回平均值
        return 7.0

    def _get_health_level(self, score: float) -> str:
        """根据得分返回健康等级"""
        if score >= 8:
            return "excellent"
        elif score >= 6:
            return "good"
        elif score >= 4:
            return "fair"
        else:
            return "needs_attention"

    def _analyze_relationship(self, comm: float, trust: float, intimacy: float,
                             commitment: float, compatibility: float) -> Tuple[List[str], List[str]]:
        """分析关系优势和需改进领域"""
        scores = {
            "沟通质量": comm,
            "信任度": trust,
            "亲密度": intimacy,
            "承诺度": commitment,
            "兼容性": compatibility
        }

        strengths = [name for name, score in scores.items() if score >= 7]
        growth_areas = [name for name, score in scores.items() if score < 6]

        return strengths, growth_areas

    def _generate_suggestions(self, growth_areas: List[str]) -> List[str]:
        """生成改进建议"""
        suggestions_map = {
            "沟通质量": ["增加日常交流频率", "尝试深度话题交流", "学习积极倾听技巧"],
            "信任度": ["保持诚实透明", "履行承诺", "给予对方空间"],
            "亲密度": ["增加独处时间", "分享内心感受", "创造共同回忆"],
            "承诺度": ["讨论未来规划", "明确关系期待", "建立共同目标"],
            "兼容性": ["探索共同兴趣", "尊重差异", "寻找平衡点"]
        }

        suggestions = []
        for area in growth_areas:
            suggestions.extend(suggestions_map.get(area, []))

        return suggestions[:5] if suggestions else ["继续用心经营你们的关系"]


# ============= 全局服务实例 =============

relationship_state_service = RelationshipStateService()
dating_advice_service = DatingAdviceService()
love_guidance_service = LoveGuidanceService()
chat_suggestion_service = ChatSuggestionService()
gift_recommendation_service = GiftRecommendationService()
relationship_health_service = RelationshipHealthService()
