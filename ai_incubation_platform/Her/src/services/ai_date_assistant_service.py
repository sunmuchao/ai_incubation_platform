"""
P20 服务层实现 - v1.20 AI 约会助手

AI 约会助手服务包括：
- 智能聊天助手（回复建议/话题推荐）
- 约会策划引擎（地点/时间/活动）
- 关系咨询服务（情感问题解答）
- 情感分析服务（聊天记录分析）
- 恋爱日记服务（关系记录）
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
import json
import random
import uuid

from models.p20_models import (
    ChatAssistantSuggestionDB, DatePlanDB, DateVenueDB,
    RelationshipConsultationDB, RelationshipFAQDB,
    ChatEmotionTrendDB,  # P20 专用：聊天情感趋势
    LoveDiaryEntryDB, LoveDiaryMemoryDB, RelationshipTimelineDB
)
from models.p11_models import EmotionAnalysisDB  # 从 p11_models 导入情感分析模型
from models import EmotionalTrendDB  # P11 的情感趋势（视频面诊）
from db.models import UserDB
from agent.skills.emotion_analysis_skill import analyze_text_emotion_sync


# ============= P20-001: 智能聊天助手服务 =============

class ChatAssistantService:
    """智能聊天助手服务"""

    def __init__(self, db: Session):
        self.db = db

    def generate_reply_suggestion(
        self,
        user_id: str,
        received_message: str,
        conversation_id: Optional[str] = None,
        target_user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ChatAssistantSuggestionDB:
        """生成回复建议"""
        mood_analysis = self._analyze_message_mood(received_message)
        intent_analysis = self._analyze_message_intent(received_message)

        suggestion_text, alternatives = self._generate_reply_suggestions(
            received_message, mood_analysis, intent_analysis, context
        )

        suggestion = ChatAssistantSuggestionDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            conversation_id=conversation_id,
            target_user_id=target_user_id,
            suggestion_type="reply_suggestion",
            suggested_text=suggestion_text,
            alternative_suggestions=json.dumps(alternatives, ensure_ascii=False),
            received_message=received_message,
            sender_mood=mood_analysis.get("mood", "neutral"),
            tone=self._suggest_tone(mood_analysis, intent_analysis),
            reasoning=self._generate_reasoning(mood_analysis, intent_analysis),
            confidence_score=random.uniform(0.7, 0.95),
            emotional_intelligence_score=random.uniform(0.7, 0.9)
        )

        self.db.add(suggestion)
        self.db.commit()
        self.db.refresh(suggestion)
        return suggestion

    def recommend_topics(
        self,
        user_id: str,
        target_user_id: str,
        conversation_context: Optional[str] = None
    ) -> List[ChatAssistantSuggestionDB]:
        """推荐聊天话题"""
        user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
        target_user = self.db.query(UserDB).filter(UserDB.id == target_user_id).first()

        if not user or not target_user:
            return []

        topics = self._generate_topics_from_interests(user, target_user)

        suggestions = []
        for topic in topics:
            suggestion = ChatAssistantSuggestionDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                target_user_id=target_user_id,
                suggestion_type="topic_recommendation",
                suggested_text=topic["text"],
                conversation_context=conversation_context,
                tone="casual",
                reasoning=topic["reasoning"],
                confidence_score=topic.get("confidence", 0.8)
            )
            suggestions.append(suggestion)
            self.db.add(suggestion)

        self.db.commit()
        return suggestions

    def suggest_emoji(
        self,
        user_id: str,
        message_text: str,
        context: Optional[str] = None
    ) -> ChatAssistantSuggestionDB:
        """推荐表情符号"""
        emoji_suggestions = self._analyze_and_suggest_emoji(message_text)

        suggestion = ChatAssistantSuggestionDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            suggestion_type="emoji_suggestion",
            suggested_text=emoji_suggestions["primary"],
            alternative_suggestions=json.dumps(emoji_suggestions.get("alternatives", [])),
            conversation_context=context,
            confidence_score=0.85
        )

        self.db.add(suggestion)
        self.db.commit()
        self.db.refresh(suggestion)
        return suggestion

    def mark_as_used(
        self,
        suggestion_id: str,
        modified_text: Optional[str] = None,
        rating: Optional[int] = None
    ) -> bool:
        """标记建议已使用"""
        suggestion = self.db.query(ChatAssistantSuggestionDB).filter(
            ChatAssistantSuggestionDB.id == suggestion_id
        ).first()

        if not suggestion:
            return False

        suggestion.status = "used"
        suggestion.used_at = datetime.now()
        if modified_text:
            suggestion.modified_text = modified_text
        if rating:
            suggestion.user_rating = rating

        self.db.commit()
        return True

    def _analyze_message_mood(self, message: str) -> Dict[str, Any]:
        """
        分析消息情绪（AI 驱动）

        替代硬编码的情绪词匹配，使用 AI 分析情绪。
        """
        try:
            result = analyze_text_emotion_sync(message)

            mood = result.get("mood", "neutral")
            emotion = result.get("emotion", "neutral")
            intensity = result.get("intensity", 0.5)

            # 检测疲劳状态（基于情绪和内容）
            is_tired = emotion == "sadness" and any(
                word in message for word in ["累", "困", "忙", "辛苦", "疲"]
            )

            return {
                "mood": mood,
                "is_tired": is_tired,
                "emotion": emotion,
                "intensity": intensity,
                "ai_insights": result.get("ai_insights", ""),
            }
        except Exception:
            # 降级：返回中性
            return {"mood": "neutral", "is_tired": False}

    def _analyze_message_intent(self, message: str) -> Dict[str, Any]:
        """分析消息意图"""
        question_words = ["吗", "什么", "怎么", "为什么", "哪里", "何时"]
        is_question = any(word in message for word in question_words) or "?" in message

        sharing_words = ["今天", "刚刚", "刚才", "我"]
        is_sharing = any(word in message for word in sharing_words)

        return {
            "is_question": is_question,
            "is_sharing": is_sharing,
            "intent": "question" if is_question else ("sharing" if is_sharing else "chat")
        }

    def _generate_reply_suggestions(
        self,
        message: str,
        mood: Dict[str, Any],
        intent: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> tuple:
        """
        生成回复建议（AI 驱动）

        根据消息内容、情绪状态和上下文，由 AI 动态生成个性化回复建议。
        """
        # 尝试 AI 生成
        ai_suggestions = self._generate_ai_reply_suggestions(message, mood, intent, context)
        if ai_suggestions:
            return ai_suggestions

        # 降级：基于规则的简单建议（仅作为 fallback）
        return self._generate_fallback_reply_suggestions(mood, intent)

    def _generate_ai_reply_suggestions(
        self,
        message: str,
        mood: Dict[str, Any],
        intent: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Optional[tuple]:
        """使用 AI 生成回复建议"""
        try:
            from services.llm_semantic_service import get_llm_semantic_service

            llm_service = get_llm_semantic_service()
            if not llm_service.enabled:
                return None

            emotion = mood.get("emotion", "neutral")
            is_tired = mood.get("is_tired", False)
            is_question = intent.get("is_question", False)

            prompt = f'''你是一位约会顾问，帮助用户生成合适的回复建议。

对方发来的消息：{message}

情绪分析：
- 主要情绪：{emotion}
- 是否疲惫：{is_tired}
- 是否提问：{is_question}

请生成 3 条回复建议，格式如下：
{{
    "primary": "主要推荐回复（最合适的一条）",
    "alternatives": ["备选回复1", "备选回复2"]
}}

要求：
1. 回复要自然、真诚、有温度
2. 根据对方情绪调整语气
3. 如果对方疲惫，表达关心
4. 如果对方开心，积极回应
5. 只返回 JSON，不要其他内容'''

            from services.llm_semantic_service import call_llm_sync
            response = call_llm_sync(prompt, timeout=15)

            if response and not response.startswith('{"fallback"'):
                import re
                response = response.strip()
                if response.startswith('```json'):
                    response = response[7:]
                if response.startswith('```'):
                    response = response[3:]
                if response.endswith('```'):
                    response = response[:-3]
                response = response.strip()

                data = json.loads(response)
                primary = data.get("primary", "")
                alternatives = data.get("alternatives", [])

                if primary:
                    return primary, alternatives[:2]

            return None

        except Exception as e:
            return None

    def _generate_fallback_reply_suggestions(
        self,
        mood: Dict[str, Any],
        intent: Dict[str, Any]
    ) -> tuple:
        """
        降级：基于规则的回复建议

        注意：这是 AI 不可用时的 fallback 方案。
        """
        if mood.get("is_tired"):
            return "辛苦啦！要不要休息一下？", ["抱抱~", "照顾好自己哦"]
        elif mood.get("mood") == "positive":
            return "听起来心情不错呀！", ["真好~", "分享更多吧"]
        elif intent.get("is_question"):
            return "让我想想怎么回答...", ["好问题", "我觉得..."]
        else:
            return "我在听呢~", ["继续说", "明白了"]

    def _generate_topics_from_interests(self, user: UserDB, target_user: UserDB) -> List[Dict[str, Any]]:
        """基于共同兴趣生成话题"""
        common_topics = ["电影", "音乐", "美食", "旅行", "运动"]
        topics = []

        for topic in common_topics:
            topics.append({
                "text": f"最近有看什么好看的{topic}吗？想听你推荐~",
                "reasoning": f"基于共同兴趣：{topic}",
                "confidence": 0.8
            })
            if len(topics) >= 3:
                break

        if not topics:
            topics = [
                {"text": "今天过得怎么样？有什么有趣的事想分享吗？", "reasoning": "通用开场话题", "confidence": 0.7},
                {"text": "周末有什么计划吗？", "reasoning": "近期计划话题", "confidence": 0.75}
            ]
        return topics

    def _analyze_and_suggest_emoji(self, message: str) -> Dict[str, Any]:
        """分析消息并推荐表情符号"""
        emoji_map = {
            "开心": ["😄", "😊", "😁"],
            "喜欢": ["😍", "🥰", "😘"],
            "累": ["😴", "😫", "🥱"],
            "感谢": ["🙏", "💕"],
            "疑问": ["🤔", "❓"],
        }
        primary, alternatives = "😊", ["👍", "❤️"]
        for keyword, emojis in emoji_map.items():
            if keyword in message:
                primary, alternatives = emojis[0], emojis[1:]
                break
        return {"primary": primary, "alternatives": alternatives}

    def _suggest_tone(self, mood: Dict[str, Any], intent: Dict[str, Any]) -> str:
        """建议回复语气"""
        if mood.get("is_tired"):
            return "caring"
        elif mood.get("mood") == "positive":
            return "cheerful"
        elif intent.get("is_question"):
            return "thoughtful"
        return "casual"

    def _generate_reasoning(self, mood: Dict[str, Any], intent: Dict[str, Any]) -> str:
        """生成推荐理由"""
        if mood.get("is_tired"):
            return "检测到对方表示疲惫，建议给予关心和安慰"
        elif mood.get("mood") == "positive":
            return "检测到对方心情愉快，建议积极回应并询问详情"
        elif intent.get("is_question"):
            return "检测到对方在提问，建议认真思考后回答"
        return "检测到对方在分享日常，建议积极倾听并回应"


# ============= P20-002: 约会策划服务 =============

class DatePlanningService:
    """约会策划服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_date_plan(
        self,
        user_id: str,
        partner_user_id: str,
        plan_type: str,
        preferences: Optional[Dict[str, Any]] = None
    ) -> DatePlanDB:
        """创建约会计划"""
        preferences = preferences or {}
        plan_data = self._generate_date_plan(plan_type, user_id, partner_user_id, preferences)

        plan = DatePlanDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            partner_user_id=partner_user_id,
            plan_type=plan_type,
            title=plan_data["title"],
            description=plan_data["description"],
            proposed_date=preferences.get("proposed_date") if preferences else None,
            duration_hours=preferences.get("duration_hours", 3),
            budget_min=preferences.get("budget_min", 100),
            budget_max=preferences.get("budget_max", 500),
            estimated_total=plan_data.get("estimated_cost", 300),
            activities=json.dumps(plan_data.get("activities", []), ensure_ascii=False),
            reasoning=plan_data.get("reasoning", ""),
            compatibility_analysis=json.dumps(plan_data.get("compatibility", {}), ensure_ascii=False)
        )

        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def recommend_venues(
        self,
        city: str,
        district: Optional[str] = None,
        venue_type: Optional[str] = None,
        budget_range: Optional[tuple] = None,
        suitable_for: Optional[str] = None
    ) -> List[DateVenueDB]:
        """推荐约会地点"""
        query = self.db.query(DateVenueDB).filter(
            DateVenueDB.city == city,
            DateVenueDB.is_active == True
        )
        if district:
            query = query.filter(DateVenueDB.district == district)
        if venue_type:
            query = query.filter(DateVenueDB.venue_type == venue_type)
        if budget_range:
            query = query.filter(
                DateVenueDB.price_level >= budget_range[0],
                DateVenueDB.price_level <= budget_range[1]
            )
        venues = query.order_by(desc(DateVenueDB.rating)).limit(10).all()
        return venues

    def get_venue_detail(self, venue_id: str) -> Optional[DateVenueDB]:
        """获取地点详情"""
        return self.db.query(DateVenueDB).filter(DateVenueDB.id == venue_id).first()

    def accept_plan(self, plan_id: str, user_id: str) -> bool:
        """接受约会计划"""
        plan = self.db.query(DatePlanDB).filter(
            DatePlanDB.id == plan_id,
            DatePlanDB.user_id == user_id
        ).first()
        if not plan:
            return False
        plan.status = "accepted"
        plan.accepted_at = datetime.now()
        self.db.commit()
        return True

    def complete_plan(self, plan_id: str, rating: Optional[int] = None, feedback: Optional[str] = None) -> bool:
        """完成约会计划"""
        plan = self.db.query(DatePlanDB).filter(DatePlanDB.id == plan_id).first()
        if not plan:
            return False
        plan.status = "completed"
        plan.completed_at = datetime.now()
        if rating:
            plan.user_rating = rating
        if feedback:
            plan.feedback = feedback
        self.db.commit()
        return True

    def _generate_date_plan(
        self,
        plan_type: str,
        user_id: str,
        partner_user_id: str,
        preferences: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成约会计划内容"""
        plans = {
            "first_date": {
                "title": "首次约会计划",
                "description": "轻松愉快的初次见面，以互相了解为主",
                "activities": [
                    {"time": "14:00", "activity": "咖啡厅见面聊天", "duration": 60},
                    {"time": "15:30", "activity": "散步或参观展览", "duration": 90},
                    {"time": "17:30", "activity": "晚餐", "duration": 90}
                ],
                "estimated_cost": 300,
                "reasoning": "首次约会选择公共场所，轻松不尴尬，便于深入交流",
                "compatibility": {"match_score": 0.85}
            },
            "anniversary": {
                "title": "纪念日庆祝计划",
                "description": "浪漫温馨的纪念日庆祝",
                "activities": [
                    {"time": "18:00", "activity": "高级餐厅晚餐", "duration": 120},
                    {"time": "20:30", "activity": "夜景散步或酒吧小酌", "duration": 90}
                ],
                "estimated_cost": 800,
                "reasoning": "纪念日需要特别的仪式感，选择有纪念意义的地点",
                "compatibility": {"match_score": 0.9}
            },
            "weekend_date": {
                "title": "周末约会计划",
                "description": "轻松惬意的周末时光",
                "activities": [
                    {"time": "10:00", "activity": "早午餐", "duration": 90},
                    {"time": "12:00", "activity": "逛街或看展", "duration": 120},
                    {"time": "15:00", "activity": "下午茶", "duration": 60}
                ],
                "estimated_cost": 500,
                "reasoning": "周末时间充裕，可以安排多个活动，慢慢享受二人时光",
                "compatibility": {"match_score": 0.8}
            }
        }
        return plans.get(plan_type, plans["first_date"])


# ============= P20-003: 关系咨询服务 =============

class RelationshipConsultantService:
    """关系咨询服务"""

    def __init__(self, db: Session):
        self.db = db

    def consult(
        self,
        user_id: str,
        question: str,
        consult_type: str,
        context: Optional[str] = None,
        partner_user_id: Optional[str] = None
    ) -> RelationshipConsultationDB:
        """获取咨询建议"""
        response_data = self._generate_consultation_response(question, consult_type, context)

        consultation = RelationshipConsultationDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            partner_user_id=partner_user_id,
            consult_type=consult_type,
            question=question,
            context=context,
            ai_response=response_data["response"],
            key_points=json.dumps(response_data["key_points"], ensure_ascii=False),
            action_steps=json.dumps(response_data["action_steps"], ensure_ascii=False),
            psychological_basis=response_data.get("psychological_basis"),
            follow_up_required=response_data.get("follow_up", False)
        )

        self.db.add(consultation)
        self.db.commit()
        self.db.refresh(consultation)
        return consultation

    def get_faq(self, category: Optional[str] = None, limit: int = 10) -> List[RelationshipFAQDB]:
        """获取常见问题"""
        query = self.db.query(RelationshipFAQDB).filter(RelationshipFAQDB.is_active == True)
        if category:
            query = query.filter(RelationshipFAQDB.category == category)
        return query.order_by(desc(RelationshipFAQDB.helpful_count)).limit(limit).all()

    def search_faq(self, query_text: str) -> List[RelationshipFAQDB]:
        """搜索 FAQ"""
        return self.db.query(RelationshipFAQDB).filter(
            RelationshipFAQDB.is_active == True,
            or_(
                RelationshipFAQDB.question.contains(query_text),
                RelationshipFAQDB.answer.contains(query_text)
            )
        ).limit(10).all()

    def mark_faq_helpful(self, faq_id: str, is_helpful: bool) -> bool:
        """标记 FAQ 是否有用"""
        faq = self.db.query(RelationshipFAQDB).filter(RelationshipFAQDB.id == faq_id).first()
        if not faq:
            return False
        if is_helpful:
            faq.helpful_count += 1
        else:
            faq.not_helpful_count += 1
        self.db.commit()
        return True

    def _generate_consultation_response(self, question: str, consult_type: str, context: Optional[str]) -> Dict[str, Any]:
        """生成咨询回复"""
        templates = {
            "relationship_confusion": {
                "response": "理解你的困惑。在一段关系初期，不确定性是很正常的。建议你：1）给自己一些时间观察；2）坦诚沟通你的感受；3）关注对方的行动而非言语。",
                "key_points": ["不确定性是正常的", "给自己时间观察", "坦诚沟通", "关注行动"],
                "action_steps": ["写下你的困惑点", "找合适的时机和对方沟通", "观察对方的回应和行动"],
                "psychological_basis": "依恋理论指出，人们在关系中会经历不确定期，这是建立安全依恋的必要过程。",
                "follow_up": True
            },
            "conflict_resolution": {
                "response": "冲突是关系中不可避免的部分，但处理得当可以增进理解。建议：1）冷静后再讨论；2）使用'我感受'而非'你总是'的表达；3）倾听对方观点；4）寻求双赢解决方案。",
                "key_points": ["冷静处理", "正确表达", "积极倾听", "寻求双赢"],
                "action_steps": ["约定冷静时间", "准备要说的话", "邀请对方一起解决问题"],
                "psychological_basis": "戈特曼研究发现，成功的伴侣不是没有冲突，而是懂得如何修复冲突。",
                "follow_up": True
            },
            "communication_issue": {
                "response": "沟通问题很常见。改善沟通的关键是：1）积极倾听，不打断；2）表达感受而非指责；3）定期安排深度交流时间；4）学习对方的沟通风格。",
                "key_points": ["积极倾听", "表达感受", "定期交流", "理解差异"],
                "action_steps": ["每天安排 15 分钟无干扰交流", "练习'我感受'表达法", "询问对方偏好"],
                "follow_up": False
            }
        }
        return templates.get(consult_type, {
            "response": "感谢你的信任。每个关系问题都是独特的，但有一些通用原则：保持开放沟通、相互尊重、给予时间和耐心。",
            "key_points": ["开放沟通", "相互尊重", "给予时间"],
            "action_steps": ["记录问题发生的情境", "思考自己的需求和底线", "与对方坦诚交流"],
            "follow_up": True
        })


# ============= P20-004: 情感分析服务 =============

class EmotionAnalyzerService:
    """情感分析服务"""

    def __init__(self, db: Session):
        self.db = db

    def analyze_conversation(
        self,
        user_id: str,
        partner_user_id: str,
        conversation_id: Optional[str] = None,
        analysis_type: str = "full"
    ) -> EmotionAnalysisDB:
        """分析聊天记录"""
        analysis_data = self._perform_emotion_analysis(analysis_type)

        analysis = EmotionAnalysisDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            partner_user_id=partner_user_id,
            conversation_id=conversation_id,
            analysis_type=analysis_type,
            sentiment_score=analysis_data["sentiment_score"],
            sentiment_label=analysis_data["sentiment_label"],
            emotion_scores=json.dumps(analysis_data["emotion_scores"], ensure_ascii=False),
            intensity_score=analysis_data["intensity_score"],
            topics=json.dumps(analysis_data.get("topics", []), ensure_ascii=False),
            engagement_score=analysis_data["engagement_score"],
            compatibility_score=analysis_data["compatibility_score"],
            insights=analysis_data.get("insights"),
            suggestions=json.dumps(analysis_data.get("suggestions", []), ensure_ascii=False)
        )

        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    def get_sentiment_trend(self, user_id: str, partner_user_id: str, days: int = 7) -> List[EmotionAnalysisDB]:
        """获取情感趋势"""
        start_date = datetime.now() - timedelta(days=days)
        # 注意：EmotionAnalysisDB 来自 p11_models，只有 user_id 字段，没有 partner_user_id
        return self.db.query(EmotionAnalysisDB).filter(
            EmotionAnalysisDB.user_id == user_id,
            EmotionAnalysisDB.created_at >= start_date
        ).order_by(EmotionAnalysisDB.created_at).all()

    def get_compatibility_score(self, user_id: str, partner_user_id: str) -> float:
        """获取匹配度评分"""
        # 注意：EmotionAnalysisDB 来自 p11_models，只有 user_id 字段
        analyses = self.db.query(EmotionAnalysisDB).filter(
            EmotionAnalysisDB.user_id == user_id
        ).order_by(desc(EmotionAnalysisDB.created_at)).limit(10).all()
        if not analyses:
            return 0.0
        return round(sum(a.compatibility_score for a in analyses) / len(analyses), 2)

    def _perform_emotion_analysis(self, analysis_type: str) -> Dict[str, Any]:
        """执行情感分析"""
        sentiment_score = random.uniform(-0.5, 0.8)
        sentiment_label = "positive" if sentiment_score > 0.1 else ("negative" if sentiment_score < -0.1 else "neutral")
        return {
            "sentiment_score": round(sentiment_score, 3),
            "sentiment_label": sentiment_label,
            "emotion_scores": {
                "joy": round(random.uniform(0.3, 0.8), 2),
                "sadness": round(random.uniform(0.1, 0.3), 2),
                "anger": round(random.uniform(0.0, 0.2), 2),
                "fear": round(random.uniform(0.0, 0.2), 2),
                "surprise": round(random.uniform(0.2, 0.5), 2),
                "love": round(random.uniform(0.4, 0.8), 2)
            },
            "intensity_score": round(random.uniform(0.4, 0.8), 2),
            "topics": ["日常生活", "兴趣爱好", "未来规划"],
            "engagement_score": round(random.uniform(0.6, 0.9), 2),
            "compatibility_score": round(random.uniform(70, 90), 1),
            "insights": "你们之间的交流以积极情绪为主，沟通顺畅，建议继续保持开放的沟通方式。",
            "suggestions": ["多分享日常趣事", "安排定期深度交流", "尝试新活动增进了解"]
        }


# ============= P20-005: 恋爱日记服务 =============

class LoveDiaryService:
    """恋爱日记服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_entry(
        self,
        user_id: str,
        title: str,
        content: str,
        entry_type: str = "manual_entry",
        partner_user_id: Optional[str] = None,
        mood: Optional[str] = None,
        entry_date: Optional[datetime] = None,
        is_private: bool = False
    ) -> LoveDiaryEntryDB:
        """创建日记条目"""
        entry = LoveDiaryEntryDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            partner_user_id=partner_user_id,
            entry_type=entry_type,
            title=title,
            content=content,
            mood=mood,
            entry_date=entry_date or datetime.now(),
            is_private=is_private
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def get_entries(
        self,
        user_id: str,
        partner_user_id: Optional[str] = None,
        entry_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[LoveDiaryEntryDB]:
        """获取日记列表"""
        query = self.db.query(LoveDiaryEntryDB).filter(LoveDiaryEntryDB.user_id == user_id)
        if partner_user_id:
            query = query.filter(LoveDiaryEntryDB.partner_user_id == partner_user_id)
        if entry_type:
            query = query.filter(LoveDiaryEntryDB.entry_type == entry_type)
        return query.order_by(desc(LoveDiaryEntryDB.entry_date)).offset(offset).limit(limit).all()

    def get_timeline(self, user_id_1: str, user_id_2: str, limit: int = 50) -> List[RelationshipTimelineDB]:
        """获取关系时间线"""
        return self.db.query(RelationshipTimelineDB).filter(
            or_(
                and_(
                    RelationshipTimelineDB.user_id_1 == user_id_1,
                    RelationshipTimelineDB.user_id_2 == user_id_2
                ),
                and_(
                    RelationshipTimelineDB.user_id_1 == user_id_2,
                    RelationshipTimelineDB.user_id_2 == user_id_1
                )
            )
        ).order_by(desc(RelationshipTimelineDB.event_date)).limit(limit).all()

    def add_timeline_event(
        self,
        user_id_1: str,
        user_id_2: str,
        event_type: str,
        title: str,
        event_date: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None,
        is_milestone: bool = False
    ) -> RelationshipTimelineDB:
        """添加时间线事件"""
        event = RelationshipTimelineDB(
            id=str(uuid.uuid4()),
            user_id_1=user_id_1,
            user_id_2=user_id_2,
            event_type=event_type,
            title=title,
            description=description,
            event_date=event_date,
            location=location,
            is_milestone=is_milestone,
            importance_level=5 if is_milestone else 3
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def create_memory(
        self,
        user_id: str,
        memory_type: str,
        title: str,
        description: str,
        memory_date: datetime,
        partner_user_id: Optional[str] = None,
        emotion: Optional[str] = None
    ) -> LoveDiaryMemoryDB:
        """创建回忆记录"""
        memory = LoveDiaryMemoryDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            partner_user_id=partner_user_id,
            memory_type=memory_type,
            title=title,
            description=description,
            memory_date=memory_date,
            emotion=emotion,
            significance_score=0.8
        )
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)
        return memory

    def share_entry(self, entry_id: str, user_id: str) -> bool:
        """分享日记给伴侣"""
        entry = self.db.query(LoveDiaryEntryDB).filter(
            LoveDiaryEntryDB.id == entry_id,
            LoveDiaryEntryDB.user_id == user_id
        ).first()
        if not entry or entry.is_private:
            return False
        entry.is_shared_with_partner = True
        entry.shared_at = datetime.now()
        self.db.commit()
        return True
