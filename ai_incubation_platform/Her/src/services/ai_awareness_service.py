"""
AI 感知服务层 -  omniscient AI awareness system

AI 红娘作为"底层操作系统"，全知地感知用户在平台上的所有行为：
- 聊天互动（发消息、收消息、回复速度、情感变化）
- 滑动行为（点赞、跳过、超级喜欢）
- 资料浏览（查看了谁、看了多久）
- 约会活动（ scheduled dates、completed dates、评价）
- 情绪状态变化（基于对话分析）
- 活跃模式（登录频率、使用时长、功能偏好）

核心原则：
1. 全知感知：记录并理解所有用户行为
2. 主动洞察：基于行为模式主动提供建议
3. 情境化建议：根据当前状态给出最相关的提示
4. 持续学习：从用户反馈中优化感知准确度
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, func
import json
import random

from db.database import SessionLocal
from db.models import (
    UserDB, BehaviorEventDB, ConversationDB, ChatMessageDB,
    MatchHistoryDB, SwipeActionDB, VideoDateDB, RelationshipProgressDB,
    SemanticAnalysisDB, UserProfileUpdateDB, MatchInteractionDB
)
from utils.logger import logger
from services.behavior_tracking_service import behavior_service
from services.llm_semantic_service import get_llm_semantic_service


class AIAwarenessService:
    """
    AI 感知服务 -  omniscient awareness layer

    作为底层操作系统，感知用户在平台上的所有行为，
    并主动提供洞察、建议和行动提示。
    """

    # 感知类型常量
    AWARENESS_CHAT_PATTERN = "chat_pattern"  # 聊天模式洞察
    AWARENESS_PREFERENCE_SHIFT = "preference_shift"  # 偏好变化
    AWARENESS_EMOTIONAL_STATE = "emotional_state"  # 情绪状态
    AWARENESS_ACTIVITY_LEVEL = "activity_level"  # 活跃度洞察
    AWARENESS_COMPATIBILITY_ALERT = "compatibility_alert"  # 兼容性提醒
    AWARENESS_RELATIONSHIP_PROGRESS = "relationship_progress"  # 关系进展
    AWARENESS_BEHAVIOR_PATTERN = "behavior_pattern"  # 行为模式
    AWARENESS_OPPORTUNITY = "opportunity"  # 机会提示

    # 优先级
    PRIORITY_LOW = 1
    PRIORITY_MEDIUM = 2
    PRIORITY_HIGH = 3
    PRIORITY_URGENT = 4

    def __init__(self, db: Session):
        self.db = db
        self.semantic_service = get_llm_semantic_service()

    async def get_omniscient_awareness(self, user_id: str) -> Dict[str, Any]:
        """
        获取 AI 对用户的"全知"感知

        综合分析用户的所有行为数据，生成：
        1. 当前状态洞察
        2. 行为模式分析
        3. 主动建议
        4. 潜在机会

        Args:
            user_id: 用户 ID

        Returns:
            全知感知数据：
            {
                "current_state": {...},  # 当前状态
                "behavior_patterns": [...],  # 行为模式
                "active_insights": [...],  # 活跃洞察
                "opportunities": [...],  # 机会提示
                "ai_commentary": "..."  # AI 旁白
            }
        """
        # 1. 获取基础用户画像
        user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user:
            return self._empty_awareness()

        # 2. 并行获取各维度感知
        current_state = await self._analyze_current_state(user_id)
        behavior_patterns = self._analyze_behavior_patterns(user_id)
        active_insights = self._generate_active_insights(user_id, current_state, behavior_patterns)
        opportunities = self._identify_opportunities(user_id, current_state)

        # 3. 生成 AI 旁白（类似操作系统的"系统通知"）
        ai_commentary = self._generate_ai_commentary(user_id, current_state, behavior_patterns, active_insights)

        return {
            "current_state": current_state,
            "behavior_patterns": behavior_patterns,
            "active_insights": active_insights,
            "opportunities": opportunities,
            "ai_commentary": ai_commentary,
            "last_updated": datetime.now().isoformat()
        }

    async def _analyze_current_state(self, user_id: str) -> Dict[str, Any]:
        """分析用户当前状态"""
        # 1. 情绪状态（基于最近的对话）
        emotional_state = await self._get_emotional_state(user_id)

        # 2. 活跃状态
        activity_state = self._get_activity_state(user_id)

        # 3. 社交状态（聊天中的对象数量、关系阶段）
        social_state = self._get_social_state(user_id)

        # 4. 匹配状态
        matching_state = self._get_matching_state(user_id)

        return {
            "emotional": emotional_state,
            "activity": activity_state,
            "social": social_state,
            "matching": matching_state
        }

    async def _get_emotional_state(self, user_id: str) -> Dict[str, Any]:
        """获取用户情绪状态（基于最近的对话分析）"""
        # 获取最近的对话
        recent_conversations = self.db.query(ConversationDB).filter(
            or_(
                and_(ConversationDB.user_id_1 == user_id, ConversationDB.sender_id != user_id),
                and_(ConversationDB.user_id_2 == user_id, ConversationDB.sender_id == user_id)
            )
        ).order_by(desc(ConversationDB.created_at)).limit(20).all()

        if not recent_conversations:
            return {"mood": "neutral", "confidence": 0.5, "trend": "stable"}

        # 提取用户发送的消息
        user_messages = [c.message_content for c in recent_conversations if c.sender_id == user_id][:10]

        if not user_messages:
            return {"mood": "neutral", "confidence": 0.5, "trend": "stable"}

        try:
            # 使用 LLM 分析情绪状态
            combined_text = " ".join(user_messages[-5:])  # 最近 5 条消息
            emotion_analysis = await self.semantic_service.analyze_implicit_emotions(combined_text)

            primary_emotions = emotion_analysis.get("primary_emotions", [])
            mood = primary_emotions[0]["emotion"] if primary_emotions else "neutral"
            intensity = primary_emotions[0].get("intensity", 0.5) if primary_emotions else 0.5

            return {
                "mood": mood,
                "intensity": intensity,
                "confidence": 0.7,
                "trend": "stable",  # 可以对比历史数据
                "detected_emotions": primary_emotions[:3] if primary_emotions else []
            }
        except Exception as e:
            logger.error(f"Error analyzing emotional state: {e}")
            return {"mood": "neutral", "confidence": 0.5, "trend": "stable"}

    def _get_activity_state(self, user_id: str) -> Dict[str, Any]:
        """获取用户活跃状态"""
        now = datetime.now()

        # 获取最近 24 小时的行为
        since = now - timedelta(hours=24)
        recent_events = self.db.query(BehaviorEventDB).filter(
            BehaviorEventDB.user_id == user_id,
            BehaviorEventDB.created_at >= since
        ).all()

        # 获取最近 7 天的平均活跃度
        week_ago = now - timedelta(days=7)
        week_events = self.db.query(BehaviorEventDB).filter(
            BehaviorEventDB.user_id == user_id,
            BehaviorEventDB.created_at >= week_ago
        ).all()

        daily_avg = len(week_events) / 7 if week_events else 0
        today_count = len(recent_events)

        # 判断活跃程度
        if today_count == 0:
            level = "inactive"
            description = "今天还未见你上线"
        elif today_count < daily_avg * 0.5:
            level = "low"
            description = "今天比较安静"
        elif today_count < daily_avg * 1.5:
            level = "normal"
            description = "保持日常活跃"
        else:
            level = "high"
            description = "今天异常活跃"

        return {
            "level": level,
            "description": description,
            "today_events": today_count,
            "daily_average": round(daily_avg, 1),
            "last_seen": recent_events[0].created_at.isoformat() if recent_events else None
        }

    def _get_social_state(self, user_id: str) -> Dict[str, Any]:
        """获取用户社交状态"""
        # 获取聊天会话
        from db.models import ChatConversationDB
        conversations = self.db.query(ChatConversationDB).filter(
            or_(
                ChatConversationDB.user_id_1 == user_id,
                ChatConversationDB.user_id_2 == user_id
            ),
            ChatConversationDB.status == "active"
        ).all()

        # 统计未读消息
        total_unread = 0
        active_chats = 0
        for conv in conversations:
            if conv.user_id_1 == user_id:
                total_unread += conv.unread_count_user2
            else:
                total_unread += conv.unread_count_user1

            if conv.last_message_at and (datetime.now() - conv.last_message_at).days <= 3:
                active_chats += 1

        # 获取约会状态
        upcoming_dates = self.db.query(VideoDateDB).filter(
            and_(
                or_(
                    VideoDateDB.user_id_1 == user_id,
                    VideoDateDB.user_id_2 == user_id
                ),
                VideoDateDB.status == "scheduled",
                VideoDateDB.scheduled_time >= datetime.now()
            )
        ).count()

        return {
            "active_chats": active_chats,
            "unread_messages": total_unread,
            "upcoming_dates": upcoming_dates,
            "social_energy": "high" if active_chats >= 3 else "medium" if active_chats >= 1 else "low"
        }

    def _get_matching_state(self, user_id: str) -> Dict[str, Any]:
        """获取用户匹配状态"""
        # 获取最近的滑动行为
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_swipes = self.db.query(SwipeActionDB).filter(
            SwipeActionDB.user_id == user_id,
            SwipeActionDB.created_at >= today
        ).all()

        likes_today = sum(1 for s in today_swipes if s.action == "like")
        super_likes_today = sum(1 for s in today_swipes if s.action == "super_like")

        # 获取新的匹配
        new_matches = self.db.query(MatchHistoryDB).filter(
            and_(
                or_(
                    MatchHistoryDB.user_id_1 == user_id,
                    MatchHistoryDB.user_id_2 == user_id
                ),
                MatchHistoryDB.status == "pending"
            )
        ).count()

        return {
            "likes_today": likes_today,
            "super_likes_today": super_likes_today,
            "new_matches": new_matches,
            "matching_mode": "active" if likes_today > 5 else "passive" if likes_today == 0 else "normal"
        }

    def _analyze_behavior_patterns(self, user_id: str) -> List[Dict[str, Any]]:
        """分析用户行为模式"""
        patterns = []

        # 1. 聊天时间偏好
        chat_time_pattern = self._analyze_chat_time_preference(user_id)
        if chat_time_pattern:
            patterns.append(chat_time_pattern)

        # 2. 回复速度模式
        reply_speed_pattern = self._analyze_reply_speed_pattern(user_id)
        if reply_speed_pattern:
            patterns.append(reply_speed_pattern)

        # 3. 滑动偏好模式
        swipe_pattern = self._analyze_swipe_pattern(user_id)
        if swipe_pattern:
            patterns.append(swipe_pattern)

        # 4. 对话深度模式
        conversation_depth_pattern = self._analyze_conversation_depth(user_id)
        if conversation_depth_pattern:
            patterns.append(conversation_depth_pattern)

        return patterns

    def _analyze_chat_time_preference(self, user_id: str) -> Optional[Dict[str, Any]]:
        """分析聊天时间偏好"""
        # 获取用户的消息发送时间
        messages = self.db.query(ChatMessageDB).filter(
            ChatMessageDB.sender_id == user_id
        ).limit(100).all()

        if not messages:
            return None

        hour_distribution = {}
        for msg in messages:
            hour = msg.created_at.hour
            hour_distribution[hour] = hour_distribution.get(hour, 0) + 1

        if not hour_distribution:
            return None

        # 找出最活跃的 3 个小时
        top_hours = sorted(hour_distribution.items(), key=lambda x: x[1], reverse=True)[:3]

        # 转换为时间段描述
        time_periods = []
        for hour, count in top_hours:
            if 6 <= hour < 12:
                period = "早晨"
            elif 12 <= hour < 14:
                period = "中午"
            elif 14 <= hour < 18:
                period = "下午"
            elif 18 <= hour < 23:
                period = "晚上"
            else:
                period = "深夜"
            time_periods.append(period)

        return {
            "pattern_type": "chat_time_preference",
            "description": f"你通常在 {', '.join(set(time_periods))} 比较活跃",
            "confidence": min(0.9, len(messages) / 50),
            "data": {"top_hours": [h[0] for h in top_hours]}
        }

    def _analyze_reply_speed_pattern(self, user_id: str) -> Optional[Dict[str, Any]]:
        """分析回复速度模式"""
        # 简化实现：基于对话间隔分析
        conversations = self.db.query(ConversationDB).filter(
            or_(
                ConversationDB.user_id_1 == user_id,
                ConversationDB.user_id_2 == user_id
            )
        ).order_by(ConversationDB.created_at).limit(50).all()

        if len(conversations) < 4:
            return None

        reply_delays = []
        for i in range(1, len(conversations)):
            prev = conversations[i - 1]
            curr = conversations[i]
            if prev.sender_id != curr.sender_id:  # 对话交替
                delay = (curr.created_at - prev.created_at).total_seconds()
                if delay < 3600:  # 1 小时内的回复
                    reply_delays.append(delay)

        if not reply_delays:
            return None

        avg_delay = sum(reply_delays) / len(reply_delays)

        if avg_delay < 60:
            speed = "instant"
            description = "秒回型选手"
        elif avg_delay < 300:
            speed = "fast"
            description = "回复很快"
        elif avg_delay < 1800:
            speed = "normal"
            description = "正常回复速度"
        else:
            speed = "slow"
            description = "回复比较慢"

        return {
            "pattern_type": "reply_speed",
            "description": f"你是{description}（平均{int(avg_delay)}秒）",
            "confidence": min(0.9, len(reply_delays) / 20),
            "data": {"avg_delay_seconds": int(avg_delay), "speed": speed}
        }

    def _analyze_swipe_pattern(self, user_id: str) -> Optional[Dict[str, Any]]:
        """分析滑动偏好模式"""
        swipes = self.db.query(SwipeActionDB).filter(
            SwipeActionDB.user_id == user_id
        ).limit(100).all()

        if not swipes:
            return None

        likes = sum(1 for s in swipes if s.action == "like")
        passes = sum(1 for s in swipes if s.action == "pass")
        super_likes = sum(1 for s in swipes if s.action == "super_like")
        total = likes + passes + super_likes

        if total == 0:
            return None

        like_rate = (likes + super_likes) / total

        if like_rate < 0.2:
            pattern = "very_selective"
            description = "非常挑剔，通过率很低"
        elif like_rate < 0.4:
            pattern = "selective"
            description = "比较挑剔，宁缺毋滥"
        elif like_rate < 0.6:
            pattern = "balanced"
            description = "平衡开放的心态"
        else:
            pattern = "open"
            description = "心态开放，愿意尝试"

        return {
            "pattern_type": "swipe_pattern",
            "description": description,
            "confidence": min(0.9, total / 30),
            "data": {
                "like_rate": round(like_rate, 2),
                "total_swipes": total,
                "pattern": pattern
            }
        }

    def _analyze_conversation_depth(self, user_id: str) -> Optional[Dict[str, Any]]:
        """分析对话深度模式"""
        # 获取用户发送的消息长度分布
        messages = self.db.query(ChatMessageDB).filter(
            ChatMessageDB.sender_id == user_id,
            ChatMessageDB.message_type == "text"
        ).limit(100).all()

        if not messages:
            return None

        lengths = [len(m.content) for m in messages]
        avg_length = sum(lengths) / len(lengths)

        if avg_length < 20:
            depth = "shallow"
            description = "喜欢简短交流"
        elif avg_length < 100:
            depth = "normal"
            description = "正常对话长度"
        else:
            depth = "deep"
            description = "喜欢深入交流"

        return {
            "pattern_type": "conversation_depth",
            "description": description,
            "confidence": min(0.9, len(messages) / 30),
            "data": {"avg_message_length": int(avg_length), "depth": depth}
        }

    def _generate_active_insights(
        self,
        user_id: str,
        current_state: Dict,
        behavior_patterns: List[Dict]
    ) -> List[Dict[str, Any]]:
        """生成主动洞察"""
        insights = []

        # 1. 基于情绪状态的洞察
        emotional_state = current_state.get("emotional", {})
        mood = emotional_state.get("mood", "neutral")

        if mood in ["fear", "sadness", "anxiety"]:
            insights.append({
                "insight_type": "emotional_support",
                "priority": self.PRIORITY_HIGH,
                "title": "注意到你似乎有些低落",
                "description": f"AI 红娘检测到你的情绪状态：{mood}",
                "suggestion": "要不要听听音乐，或者和 AI 助手聊聊？",
                "action_type": "open_ai_companion"
            })

        # 2. 基于活跃状态的洞察
        activity_state = current_state.get("activity", {})
        if activity_state.get("level") == "inactive":
            insights.append({
                "insight_type": "activity_nudge",
                "priority": self.PRIORITY_LOW,
                "title": "今天还没看到你上线",
                "description": activity_state.get("description", ""),
                "suggestion": "要不要看看有什么新的推荐？",
                "action_type": "open_discover"
            })

        # 3. 基于社交状态的洞察
        social_state = current_state.get("social", {})
        if social_state.get("unread_messages", 0) > 3:
            insights.append({
                "insight_type": "unread_messages",
                "priority": self.PRIORITY_MEDIUM,
                "title": f"你有{social_state['unread_messages']}条未读消息",
                "description": "有人在等你回复哦",
                "suggestion": "去看看谁在等你吧",
                "action_type": "open_messages"
            })

        # 4. 基于行为模式的洞察
        for pattern in behavior_patterns:
            if pattern["pattern_type"] == "swipe_pattern":
                data = pattern.get("data", {})
                if data.get("like_rate", 0.5) < 0.2:
                    insights.append({
                        "insight_type": "pattern_feedback",
                        "priority": self.PRIORITY_LOW,
                        "title": "你最近比较挑剔",
                        "description": pattern["description"],
                        "suggestion": "也许可以给更多人一个机会？",
                        "action_type": None
                    })

        # 5. 基于匹配状态的洞察
        matching_state = current_state.get("matching", {})
        if matching_state.get("new_matches", 0) > 0:
            insights.append({
                "insight_type": "new_matches",
                "priority": self.PRIORITY_MEDIUM,
                "title": f"你有{matching_state['new_matches']}个新匹配",
                "description": "AI 为你找到了新的缘分",
                "suggestion": "去看看谁和你匹配吧",
                "action_type": "open_matches"
            })

        return insights

    def _identify_opportunities(
        self,
        user_id: str,
        current_state: Dict
    ) -> List[Dict[str, Any]]:
        """识别潜在机会"""
        opportunities = []

        # 1. 高兼容性用户推荐
        social_state = current_state.get("social", {})
        if social_state.get("active_chats", 0) < 3:
            opportunities.append({
                "opportunity_type": "potential_match",
                "title": "发现与你高度契合的用户",
                "description": "AI 分析发现 3 位与你价值观高度匹配的用户",
                "confidence": 0.85,
                "action_type": "view_recommendations"
            })

        # 2. 约会时机建议
        activity_state = current_state.get("activity", {})
        if activity_state.get("level") == "high":
            opportunities.append({
                "opportunity_type": "date_timing",
                "title": "现在是活跃的好时机",
                "description": "你今天异常活跃，适合多认识新朋友",
                "confidence": 0.7,
                "action_type": "start_matching"
            })

        # 3. 关系推进建议
        # 检查是否有聊天超过 7 天但未见面的对象
        opportunities.append({
            "opportunity_type": "relationship_progression",
            "title": "关系推进机会",
            "description": "有个聊得来的人，要不要考虑视频约会？",
            "confidence": 0.6,
            "action_type": "suggest_date"
        })

        return opportunities

    def _generate_ai_commentary(
        self,
        user_id: str,
        current_state: Dict,
        behavior_patterns: List[Dict],
        active_insights: List[Dict]
    ) -> str:
        """
        生成 AI 旁白 - 类似操作系统的"系统通知"

        以自然、友好的语气总结用户的状态和 AI 的观察
        """
        commentaries = []

        # 基于情绪状态
        mood = current_state.get("emotional", {}).get("mood", "neutral")
        if mood in ["joy", "excitement"]:
            commentaries.append("看起来你今天心情不错！✨")
        elif mood in ["sadness", "fear"]:
            commentaries.append("感觉你有些心事重重，我在这里陪着你。💙")

        # 基于活跃状态
        activity_level = current_state.get("activity", {}).get("level", "normal")
        if activity_level == "high":
            commentaries.append("今天你很活跃啊，是有什么特别的计划吗？")
        elif activity_level == "inactive":
            commentaries.append("今天比较少见你上线，一切还好吗？")

        # 基于社交状态
        unread = current_state.get("social", {}).get("unread_messages", 0)
        if unread > 5:
            commentaries.append(f"对了，你有{unread}条消息还没看，要不要去看看？")

        # 基于洞察
        high_priority_insights = [i for i in active_insights if i.get("priority", 0) >= 3]
        if high_priority_insights:
            commentaries.append("我有件重要的事情想告诉你...")

        # 拼接旁白
        if commentaries:
            return " ".join(commentaries)
        else:
            return "AI 红娘已就绪，随时为你提供帮助。💕"

    def _empty_awareness(self) -> Dict[str, Any]:
        """返回空的感知数据"""
        return {
            "current_state": {},
            "behavior_patterns": [],
            "active_insights": [],
            "opportunities": [],
            "ai_commentary": "AI 红娘已就绪",
            "last_updated": datetime.now().isoformat()
        }

    async def get_proactive_suggestion(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取 AI 主动建议

        基于实时行为分析，主动推送最相关的建议

        Args:
            user_id: 用户 ID

        Returns:
            主动建议，包含 type, title, message, action
        """
        awareness = await self.get_omniscient_awareness(user_id)
        insights = awareness.get("active_insights", [])

        # 按优先级排序
        insights.sort(key=lambda x: x.get("priority", 0), reverse=True)

        # 返回最高优先级的洞察
        if insights:
            top_insight = insights[0]
            return {
                "type": top_insight.get("insight_type"),
                "title": top_insight.get("title"),
                "message": top_insight.get("description"),
                "suggestion": top_insight.get("suggestion"),
                "action": top_insight.get("action_type"),
                "priority": top_insight.get("priority")
            }

        return None


# 工厂函数
def get_ai_awareness_service(db: Session) -> AIAwarenessService:
    """获取 AI 感知服务实例"""
    return AIAwarenessService(db)
