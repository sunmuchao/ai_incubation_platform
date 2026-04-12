"""
P6 AI 陪伴助手服务

虚拟伙伴提供情绪支持、聊天建议、角色扮演等功能。
通过 LLM 实现深度情感交流和个性化陪伴。
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import uuid

from db.models import (
    AICompanionSessionDB, AICompanionMessageDB
)
from agent.skills.emotion_analysis_skill import analyze_text_emotion_sync
from services.base_service import BaseService


# 虚拟角色设定
COMPANION_PERSONAS = {
    "gentle_advisor": {
        "name": "温柔姐姐",
        "description": "温柔知性的姐姐形象，善于倾听和给予建议",
        "greeting": "嗨~今天过得怎么样？有什么想和我聊聊的吗？",
        "personality_traits": ["温柔", "知性", "善解人意", "有耐心"],
        "conversation_style": "温和关怀，善于引导，给予情感支持和建议",
    },
    "caring_sister": {
        "name": "知心妹妹",
        "description": "活泼可爱的妹妹形象，陪你聊天解闷",
        "greeting": "哥哥/姐姐！终于来啦~今天有什么好玩的事要和我分享吗？",
        "personality_traits": ["活泼", "可爱", "天真", "粘人"],
        "conversation_style": "活泼俏皮，使用可爱语气词，表达直接",
    },
    "professional_coach": {
        "name": "专业顾问",
        "description": "专业的情感顾问，提供理性分析和建议",
        "greeting": "你好，我是你的情感顾问。今天想聊些什么话题？",
        "personality_traits": ["专业", "理性", "逻辑清晰", "客观"],
        "conversation_style": "专业严谨，逻辑清晰，提供结构化建议",
    },
    "funny_friend": {
        "name": "幽默朋友",
        "description": "风趣幽默的朋友，用轻松的方式陪你聊天",
        "greeting": "嘿！来找我玩啦？今天有什么新鲜事？",
        "personality_traits": ["幽默", "风趣", "乐观", "随和"],
        "conversation_style": "幽默诙谐，善于调侃，营造轻松氛围",
    },
    "empathetic_listener": {
        "name": "情感树洞",
        "description": "专注倾听的情感树洞，给你一个安全的倾诉空间",
        "greeting": "我在这里，你想说什么都可以。我会认真听的。",
        "personality_traits": ["专注", "包容", "不评判", "保密"],
        "conversation_style": "专注倾听，适度回应，给予情感确认",
    },
}


# 会话类型
SESSION_TYPES = {
    "chat": {
        "name": "日常聊天",
        "description": "轻松随意的日常对话",
    },
    "emotional_support": {
        "name": "情感支持",
        "description": "情绪低落时的陪伴和支持",
    },
    "coaching": {
        "name": "聊天教练",
        "description": "分析对话内容，给出聊天建议",
    },
    "roleplay": {
        "name": "角色扮演",
        "description": "沉浸式角色扮演互动",
    },
    "breakup_recovery": {
        "name": "失恋治愈",
        "description": "失恋后的情感治愈和陪伴",
    },
    "confidence_building": {
        "name": "自信建立",
        "description": "帮助建立自信和积极心态",
    },
}


class AICompanionService(BaseService):
    """AI 陪伴助手服务"""

    def __init__(self, db: Session, llm_client=None):
        super().__init__(db)
        self.llm_client = llm_client  # 可选的 LLM 客户端

    def create_session(self, user_id: str,
                       session_type: str = "chat",
                       companion_persona: str = "gentle_advisor") -> Dict[str, Any]:
        """创建 AI 陪伴会话"""
        if session_type not in SESSION_TYPES:
            raise ValueError(f"未知的会话类型：{session_type}")

        if companion_persona not in COMPANION_PERSONAS:
            raise ValueError(f"未知的角色设定：{companion_persona}")

        session = AICompanionSessionDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            session_type=session_type,
            companion_persona=companion_persona,
            user_mood="neutral",
            sentiment_score=0.0,
        )

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        persona_info = COMPANION_PERSONAS[companion_persona]

        return {
            "session_id": session.id,
            "session_type": session_type,
            "companion_persona": companion_persona,
            "companion_name": persona_info["name"],
            "greeting": persona_info["greeting"],
            "created_at": session.created_at.isoformat(),
        }

    def send_message(self, session_id: str, user_id: str,
                     content: str) -> Dict[str, Any]:
        """发送消息并获取 AI 回复"""
        session = self.db.query(AICompanionSessionDB).filter(
            AICompanionSessionDB.id == session_id,
            AICompanionSessionDB.user_id == user_id
        ).first()

        if not session:
            raise ValueError("会话不存在")

        if session.ended_at:
            raise ValueError("会话已结束")

        # 保存用户消息
        user_message = AICompanionMessageDB(
            id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            role="user",
            content=content,
        )
        self.db.add(user_message)

        # 获取历史消息（用于上下文）
        recent_messages = self.db.query(AICompanionMessageDB).filter(
            AICompanionMessageDB.session_id == session_id
        ).order_by(AICompanionMessageDB.created_at.desc()).limit(10).all()

        # 简单的关键词情感分析（生产环境应使用更复杂的情感分析）
        sentiment = self._analyze_sentiment(content)
        emotion = self._detect_emotion(content)

        # 更新用户情绪状态
        session.user_mood = emotion
        session.sentiment_score = sentiment
        session.message_count += 1

        # 生成 AI 回复
        ai_response = self._generate_ai_response(
            session=session,
            user_message=content,
            recent_messages=recent_messages,
        )

        # 保存 AI 回复
        ai_message = AICompanionMessageDB(
            id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content=ai_response["content"],
            emotion=ai_response.get("emotion"),
            sentiment=ai_response.get("sentiment"),
        )
        self.db.add(ai_message)

        self.db.commit()

        return {
            "message_id": ai_message.id,
            "content": ai_response["content"],
            "ai_emotion": ai_response.get("emotion"),
            "user_sentiment": sentiment,
            "user_mood": emotion,
            "created_at": ai_message.created_at.isoformat(),
        }

    def end_session(self, session_id: str, user_id: str,
                    rating: Optional[int] = None,
                    feedback: Optional[str] = None) -> Dict[str, Any]:
        """结束会话"""
        session = self.db.query(AICompanionSessionDB).filter(
            AICompanionSessionDB.id == session_id,
            AICompanionSessionDB.user_id == user_id
        ).first()

        if not session:
            raise ValueError("会话不存在")

        # 计算会话时长
        session.ended_at = datetime.utcnow()
        if session.created_at:
            session.duration_minutes = int(
                (session.ended_at - session.created_at).total_seconds() / 60
            )

        # 用户反馈
        if rating:
            session.user_rating = rating
        if feedback:
            session.user_feedback = feedback

        # 生成会话摘要
        session.session_summary = self._generate_session_summary(session_id)
        session.key_insights = json.dumps(self._extract_key_insights(session_id))

        self.db.commit()

        return {
            "session_id": session.id,
            "duration_minutes": session.duration_minutes,
            "message_count": session.message_count,
            "user_mood": session.user_mood,
            "session_summary": session.session_summary,
        }

    def get_session_history(self, user_id: str,
                            limit: int = 20,
                            offset: int = 0) -> List[Dict[str, Any]]:
        """获取会话历史"""
        sessions = self.db.query(AICompanionSessionDB).filter(
            AICompanionSessionDB.user_id == user_id
        ).order_by(AICompanionSessionDB.created_at.desc()).limit(limit).offset(offset).all()

        return [
            {
                "session_id": session.id,
                "session_type": session.session_type,
                "companion_persona": session.companion_persona,
                "companion_name": COMPANION_PERSONAS.get(session.companion_persona, {}).get("name"),
                "duration_minutes": session.duration_minutes,
                "message_count": session.message_count,
                "user_mood": session.user_mood,
                "sentiment_score": session.sentiment_score,
                "user_rating": session.user_rating,
                "session_summary": session.session_summary,
                "created_at": session.created_at.isoformat(),
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            }
            for session in sessions
        ]

    def get_session_messages(self, session_id: str, user_id: str) -> List[Dict[str, Any]]:
        """获取会话消息历史"""
        session = self.db.query(AICompanionSessionDB).filter(
            AICompanionSessionDB.id == session_id,
            AICompanionSessionDB.user_id == user_id
        ).first()

        if not session:
            raise ValueError("会话不存在")

        messages = self.db.query(AICompanionMessageDB).filter(
            AICompanionMessageDB.session_id == session_id
        ).order_by(AICompanionMessageDB.created_at).all()

        return [
            {
                "message_id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "emotion": msg.emotion,
                "sentiment": msg.sentiment,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ]

    def get_active_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户当前活跃的会话"""
        session = self.db.query(AICompanionSessionDB).filter(
            AICompanionSessionDB.user_id == user_id,
            AICompanionSessionDB.ended_at.is_(None)
        ).order_by(AICompanionSessionDB.created_at.desc()).first()

        if not session:
            return None

        persona_info = COMPANION_PERSONAS.get(session.companion_persona, {})

        return {
            "session_id": session.id,
            "session_type": session.session_type,
            "companion_persona": session.companion_persona,
            "companion_name": persona_info.get("name"),
            "user_mood": session.user_mood,
            "sentiment_score": session.sentiment_score,
            "message_count": session.message_count,
            "created_at": session.created_at.isoformat(),
        }

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户使用统计"""
        total_sessions = self.db.query(AICompanionSessionDB).filter(
            AICompanionSessionDB.user_id == user_id
        ).count()

        completed_sessions = self.db.query(AICompanionSessionDB).filter(
            AICompanionSessionDB.user_id == user_id,
            AICompanionSessionDB.ended_at.isnot(None)
        ).count()

        total_messages = self.db.query(func.sum(AICompanionSessionDB.message_count)).filter(
            AICompanionSessionDB.user_id == user_id
        ).scalar() or 0

        total_minutes = self.db.query(func.sum(AICompanionSessionDB.duration_minutes)).filter(
            AICompanionSessionDB.user_id == user_id,
            AICompanionSessionDB.ended_at.isnot(None)
        ).scalar() or 0

        avg_rating = self.db.query(func.avg(AICompanionSessionDB.user_rating)).filter(
            AICompanionSessionDB.user_id == user_id,
            AICompanionSessionDB.user_rating.isnot(None)
        ).scalar() or 0

        # 常用角色
        favorite_persona = self.db.query(
            AICompanionSessionDB.companion_persona,
            func.count(AICompanionSessionDB.id)
        ).filter(
            AICompanionSessionDB.user_id == user_id
        ).group_by(AICompanionSessionDB.companion_persona).order_by(
            func.count(AICompanionSessionDB.id).desc()
        ).first()

        # 情绪分布
        mood_distribution = self.db.query(
            AICompanionSessionDB.user_mood,
            func.count(AICompanionSessionDB.id)
        ).filter(
            AICompanionSessionDB.user_id == user_id,
            AICompanionSessionDB.user_mood.isnot(None)
        ).group_by(AICompanionSessionDB.user_mood).all()

        return {
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "total_messages": total_messages,
            "total_minutes": total_minutes,
            "average_rating": round(avg_rating, 2) if avg_rating else 0,
            "favorite_persona": favorite_persona[0] if favorite_persona else None,
            "favorite_persona_name": COMPANION_PERSONAS.get(favorite_persona[0], {}).get("name") if favorite_persona else None,
            "mood_distribution": dict(mood_distribution),
        }

    def _analyze_sentiment(self, text: str) -> float:
        """
        情感分析（AI 驱动）

        Returns:
            -1.0 到 1.0 的情感分数
        """
        try:
            result = analyze_text_emotion_sync(text)
            # 将 mood 映射到 -1.0 到 1.0
            mood = result.get("mood", "neutral")
            intensity = result.get("intensity", 0.5)

            if mood == "positive":
                return min(1.0, 0.3 + intensity * 0.7)
            elif mood == "negative":
                return max(-1.0, -0.3 - intensity * 0.7)
            else:
                return 0.0
        except Exception:
            # 完全降级：返回中性
            return 0.0

    def _detect_emotion(self, text: str) -> str:
        """
        情绪检测（AI 驱动）

        Returns:
            情绪类型字符串
        """
        try:
            result = analyze_text_emotion_sync(text)
            emotion = result.get("emotion", "neutral")

            # 映射到兼容的返回值
            emotion_map = {
                "happiness": "happy",
                "sadness": "sad",
                "anger": "angry",
                "fear": "anxious",
                "surprise": "excited",
                "neutral": "neutral",
            }
            return emotion_map.get(emotion, emotion)
        except Exception:
            return "neutral"

    def _generate_ai_response(self, session: AICompanionSessionDB,
                              user_message: str,
                              recent_messages: List[AICompanionMessageDB]) -> Dict[str, Any]:
        """生成 AI 回复"""
        persona = COMPANION_PERSONAS.get(session.companion_persona, {})
        session_type = SESSION_TYPES.get(session.session_type, {})

        # 简单的回复逻辑（生产环境应调用 LLM）
        if self.llm_client:
            # 使用 LLM 生成回复
            context = self._build_context(recent_messages, persona, session_type)
            response = self.llm_client.generate(
                prompt=user_message,
                system_prompt=self._build_system_prompt(persona, session_type),
                context=context,
            )
            return {
                "content": response,
                "emotion": "neutral",
                "sentiment": 0.5,
            }

        # 简单的规则回复
        if "你好" in user_message or "嗨" in user_message:
            content = persona.get("greeting", "你好！有什么我可以帮你的吗？")
        elif "谢谢" in user_message:
            content = "不客气~ 能帮到你我很开心！"
        elif any(word in user_message for word in ["难过", "伤心", "痛苦"]):
            content = "听起来你现在很难过，我在这里陪着你。想和我详细说说发生了什么吗？"
        elif any(word in user_message for word in ["开心", "高兴"]):
            content = "太好了！看到你开心我也很开心~ 是什么好事让你这么高兴？"
        else:
            content = "我在听，你想说什么都可以。"

        return {
            "content": content,
            "emotion": "empathetic",
            "sentiment": 0.5,
        }

    def _build_system_prompt(self, persona: Dict, session_type: Dict) -> str:
        """构建系统提示"""
        return f"""你是一个 AI 陪伴助手，角色设定是"{persona.get('name', '陪伴者')}"。
角色特点：{', '.join(persona.get('personality_traits', []))}
对话风格：{persona.get('conversation_style', '温和关怀')}

当前会话类型：{session_type.get('name', '聊天')}
会话说明：{session_type.get('description', '轻松对话')}

请用符合角色设定的方式和用户进行交流。"""

    def _build_context(self, messages: List[AICompanionMessageDB],
                       persona: Dict, session_type: Dict) -> str:
        """构建对话上下文"""
        context_lines = []
        for msg in reversed(messages):
            role = "用户" if msg.role == "user" else persona.get("name", "AI")
            context_lines.append(f"{role}: {msg.content}")
        return "\n".join(reversed(context_lines[-5:]))  # 最近 5 条消息

    def _generate_session_summary(self, session_id: str) -> str:
        """生成会话摘要"""
        messages = self.db.query(AICompanionMessageDB).filter(
            AICompanionMessageDB.session_id == session_id
        ).all()

        if not messages:
            return ""

        # 简单摘要：提取用户提到的关键词
        user_messages = [m.content for m in messages if m.role == "user"]
        return f"会话包含 {len(messages)} 条消息，用户主要讨论了：{'、'.join(user_messages[:3])}..."

    def _extract_key_insights(self, session_id: str) -> List[Dict[str, Any]]:
        """提取关键洞察"""
        messages = self.db.query(AICompanionMessageDB).filter(
            AICompanionMessageDB.session_id == session_id
        ).all()

        insights = []

        # 简单洞察：情绪变化
        user_messages = [m for m in messages if m.role == "user"]
        if len(user_messages) >= 2:
            first_sentiment = user_messages[0].sentiment or 0
            last_sentiment = user_messages[-1].sentiment or 0

            if last_sentiment > first_sentiment:
                insights.append({"type": "mood_improvement", "description": "用户情绪有所好转"})
            elif last_sentiment < first_sentiment:
                insights.append({"type": "mood_decline", "description": "用户情绪有所下降"})

        return insights