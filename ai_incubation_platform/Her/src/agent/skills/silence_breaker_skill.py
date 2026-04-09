"""
沉默破冰 Skill - 尴尬沉默检测 + 话题生成

AI 社交助手核心 Skill - 尴尬沉默识别、情境话题生成、自然过渡建议
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from agent.skills.base import BaseSkill
from utils.logger import logger
import json
import re


class SilenceBreakerSkill(BaseSkill):
    """
    AI 沉默破冰助手 Skill - 化解尴尬，让对话流畅自然

    核心能力:
    - 尴尬沉默检测（基于时间、上下文、情感）
    - 情境话题生成（基于共同兴趣、历史对话、当前场景）
    - 自然过渡建议（从沉默到新话题的平滑衔接）
    - 对话节奏分析（判断何时该说话、何时该倾听）

    自主触发:
    - 对话沉默超过阈值（5 秒/10 秒/15 秒分级）
    - 检测到尴尬信号（回复变短、回应延迟）
    - 话题枯竭预警
    """

    name = "silence_breaker"
    version = "1.0.0"
    description = """
    AI 沉默破冰助手，化解对话中的尴尬沉默

    能力:
    - 尴尬沉默检测：识别对话中的沉默时刻
    - 情境话题生成：根据上下文生成合适的话题
    - 自然过渡：提供平滑的话题切换建议
    - 对话节奏分析：判断最佳介入时机
    """

    # 沉默阈值（秒）
    SILENCE_THRESHOLD = {
        "minor": 5,      # 轻微沉默
        "moderate": 10,  # 中等沉默
        "severe": 15,    # 严重沉默
        "critical": 30   # 危险沉默
    }

    # 话题类别
    TOPIC_CATEGORIES = [
        "interests",      # 兴趣爱好
        "daily_life",     # 日常生活
        "travel",         # 旅行经历
        "food",           # 美食
        "entertainment",  # 娱乐
        "work",           # 工作
        "childhood",      # 童年回忆
        "future_plans",   # 未来计划
        "relationship",   # 关系话题
        "current_mood"    # 当下心情
    ]

    def get_input_schema(self) -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "conversation_id": {
                    "type": "string",
                    "description": "对话 ID"
                },
                "session_id": {
                    "type": "string",
                    "description": "会话 ID"
                },
                "user_a_id": {
                    "type": "string",
                    "description": "用户 A ID"
                },
                "user_b_id": {
                    "type": "string",
                    "description": "用户 B ID"
                },
                "silence_duration": {
                    "type": "number",
                    "description": "沉默持续时间（秒）"
                },
                "context": {
                    "type": "object",
                    "properties": {
                        "last_topic": {"type": "string"},
                        "conversation_stage": {"type": "string"},  # initial, developing, deep
                        "relationship_stage": {"type": "string"},  # new, getting_to_know, comfortable
                        "time_of_day": {"type": "string"},
                        "location": {"type": "string"}
                    }
                },
                "conversation_history": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "最近对话历史"
                },
                "user_profiles": {
                    "type": "object",
                    "description": "用户资料（兴趣、爱好等）"
                }
            },
            "required": ["conversation_id", "user_a_id", "user_b_id"]
        }

    def get_output_schema(self) -> dict:
        """获取输出参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "ai_message": {"type": "string"},
                "silence_analysis": {
                    "type": "object",
                    "properties": {
                        "silence_duration": {"type": "number"},
                        "silence_level": {"type": "string"},
                        "is_awkward": {"type": "boolean"},
                        "possible_reasons": {"type": "array"},
                        "recommended_action": {"type": "string"}
                    }
                },
                "generated_topics": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "topic": {"type": "string"},
                            "category": {"type": "string"},
                            "opener": {"type": "string"},
                            "follow_up_questions": {"type": "array"},
                            "confidence": {"type": "number"}
                        }
                    }
                },
                "generative_ui": {
                    "type": "object",
                    "properties": {
                        "component_type": {"type": "string"},
                        "props": {"type": "object"}
                    }
                },
                "suggested_actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "action_type": {"type": "string"},
                            "params": {"type": "object"}
                        }
                    }
                }
            },
            "required": ["success", "ai_message", "silence_analysis", "generated_topics"]
        }

    async def execute(
        self,
        conversation_id: str,
        user_a_id: str,
        user_b_id: str,
        session_id: Optional[str] = None,
        silence_duration: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict]] = None,
        user_profiles: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> dict:
        """
        执行沉默破冰 Skill

        Args:
            conversation_id: 对话 ID
            user_a_id: 用户 A ID
            user_b_id: 用户 B ID
            session_id: 会话 ID
            silence_duration: 沉默持续时间
            context: 上下文信息
            conversation_history: 对话历史
            user_profiles: 用户资料
            **kwargs: 额外参数

        Returns:
            Skill 执行结果
        """
        logger.info(f"SilenceBreakerSkill: Executing for conversation={conversation_id}")

        start_time = datetime.now()

        # Step 1: 分析沉默状态
        silence_analysis = self._analyze_silence(
            silence_duration=silence_duration,
            conversation_history=conversation_history,
            context=context
        )

        # Step 2: 生成破冰话题
        generated_topics = self._generate_topics(
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            context=context,
            conversation_history=conversation_history,
            user_profiles=user_profiles
        )

        # Step 3: 生成自然语言建议
        ai_message = self._generate_message(silence_analysis, generated_topics)

        # Step 4: 构建 Generative UI
        generative_ui = self._build_ui(silence_analysis, generated_topics)

        # Step 5: 生成建议操作
        suggested_actions = self._generate_actions(generated_topics)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "success": True,
            "ai_message": ai_message,
            "silence_analysis": silence_analysis,
            "generated_topics": generated_topics,
            "generative_ui": generative_ui,
            "suggested_actions": suggested_actions,
            "skill_metadata": {
                "name": self.name,
                "version": self.version,
                "execution_time_ms": int(execution_time),
                "silence_level": silence_analysis.get("silence_level")
            }
        }

    def _analyze_silence(
        self,
        silence_duration: Optional[float] = None,
        conversation_history: Optional[List[Dict]] = None,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """分析沉默状态"""
        # 默认沉默时长
        if silence_duration is None:
            silence_duration = self._estimate_silence_from_history(conversation_history)

        # 判断沉默等级
        silence_level = self._classify_silence_level(silence_duration)

        # 判断是否尴尬
        is_awkward = self._is_awkward_silence(
            silence_duration=silence_duration,
            conversation_history=conversation_history,
            context=context
        )

        # 分析可能原因
        possible_reasons = self._analyze_silence_reasons(
            conversation_history=conversation_history,
            context=context
        )

        # 推荐操作
        recommended_action = self._recommend_action(silence_level, is_awkward)

        return {
            "silence_duration": silence_duration,
            "silence_level": silence_level,
            "is_awkward": is_awkward,
            "possible_reasons": possible_reasons,
            "recommended_action": recommended_action
        }

    def _classify_silence_level(self, duration: float) -> str:
        """分类沉默等级"""
        if duration >= self.SILENCE_THRESHOLD["critical"]:
            return "critical"
        elif duration >= self.SILENCE_THRESHOLD["severe"]:
            return "severe"
        elif duration >= self.SILENCE_THRESHOLD["moderate"]:
            return "moderate"
        elif duration >= self.SILENCE_THRESHOLD["minor"]:
            return "minor"
        return "normal"

    def _estimate_silence_from_history(self, history: Optional[List[Dict]]) -> float:
        """从对话历史估算沉默时长"""
        if not history or len(history) < 2:
            return 5.0

        # 获取最后一条消息的时间
        last_message = history[-1]
        last_time_str = last_message.get("created_at")

        if not last_time_str:
            return 5.0

        try:
            if isinstance(last_time_str, str):
                last_time = datetime.fromisoformat(last_time_str.replace('Z', '+00:00'))
            else:
                last_time = last_time_str

            elapsed = (datetime.now() - last_time.replace(tzinfo=None)).total_seconds()
            return max(elapsed, 0)
        except Exception:
            return 5.0

    def _is_awkward_silence(
        self,
        silence_duration: float,
        conversation_history: Optional[List[Dict]],
        context: Optional[Dict]
    ) -> bool:
        """判断是否是尴尬沉默"""
        # 沉默超过 10 秒默认是尴尬的
        if silence_duration >= 10:
            return True

        # 检查对话历史中的尴尬信号
        if conversation_history:
            # 回复变短
            recent_lengths = [len(m.get("content", "")) for m in conversation_history[-4:]]
            if len(recent_lengths) >= 2:
                avg_recent = sum(recent_lengths[-2:]) / 2
                avg_earlier = sum(recent_lengths[:-2]) / 2 if len(recent_lengths) > 2 else avg_recent
                if avg_recent < avg_earlier * 0.5:
                    return True

            # 回应延迟增加
            # 检查上下文
            if context:
                stage = context.get("conversation_stage", "initial")
                if stage == "initial":
                    return silence_duration >= 5

        return False

    def _analyze_silence_reasons(
        self,
        conversation_history: Optional[List[Dict]],
        context: Optional[Dict]
    ) -> List[str]:
        """分析沉默的可能原因"""
        reasons = []

        if not conversation_history:
            return ["对话刚刚开始"]

        # 检查话题是否耗尽
        recent_topics = set()
        for msg in conversation_history[-10:]:
            content = msg.get("content", "").lower()
            if "电影" in content or "movie" in content:
                recent_topics.add("movie")
            if "吃" in content or "food" in content:
                recent_topics.add("food")
            if "工作" in content or "work" in content:
                recent_topics.add("work")

        if len(recent_topics) >= 3:
            reasons.append("已聊过多个话题，可能暂时枯竭")

        # 检查关系阶段
        if context:
            stage = context.get("relationship_stage", "new")
            if stage == "new":
                reasons.append("初次交流，还在熟悉阶段")
            elif stage == "comfortable":
                reasons.append("关系舒适，沉默也可能是自然的")

        # 检查时间
        time_of_day = context.get("time_of_day") if context else None
        if time_of_day in ["late_night", "early_morning"]:
            reasons.append("时间较晚，可能有些疲劳")

        if not reasons:
            reasons.append("对话自然停顿")

        return reasons

    def _recommend_action(self, silence_level: str, is_awkward: bool) -> str:
        """推荐操作"""
        if silence_level == "critical":
            return "immediate_intervention"
        elif silence_level == "severe" or is_awkward:
            return "suggest_topic"
        elif silence_level == "moderate":
            return "gentle_nudge"
        return "wait_natural"

    def _generate_topics(
        self,
        user_a_id: str,
        user_b_id: str,
        context: Optional[Dict],
        conversation_history: Optional[List[Dict]],
        user_profiles: Optional[Dict]
    ) -> List[Dict[str, Any]]:
        """生成破冰话题"""
        topics = []

        # 获取用户兴趣
        interests = self._extract_common_interests(user_profiles)

        # 获取已聊过的话题
        discussed_topics = self._extract_discussed_topics(conversation_history)

        # 生成话题
        topic_generators = [
            self._generate_interest_topic,
            self._generate_daily_life_topic,
            self._generate_travel_topic,
            self._generate_food_topic,
            self._generate_entertainment_topic,
            self._generate_childhood_topic
        ]

        for generator in topic_generators:
            topic = generator(
                interests=interests,
                discussed_topics=discussed_topics,
                context=context
            )
            if topic:
                topics.append(topic)
                if len(topics) >= 5:
                    break

        return topics

    def _extract_common_interests(self, user_profiles: Optional[Dict]) -> List[str]:
        """提取共同兴趣"""
        if not user_profiles:
            return ["美食", "旅行", "电影"]

        # 简化实现
        interests_a = user_profiles.get("user_a_interests", [])
        interests_b = user_profiles.get("user_b_interests", [])

        common = list(set(interests_a) & set(interests_b))
        return common if common else ["美食", "旅行", "音乐"]

    def _extract_discussed_topics(self, history: Optional[List[Dict]]) -> List[str]:
        """提取已讨论的话题"""
        if not history:
            return []

        discussed = set()
        topic_keywords = {
            "电影": ["电影", "movie", "影院", "看片"],
            "美食": ["吃", "food", "餐厅", "料理"],
            "旅行": ["旅行", "travel", "旅游", "去过"],
            "工作": ["工作", "work", "上班", "职业"],
            "音乐": ["音乐", "music", "歌", "听"]
        }

        for msg in history[-20:]:
            content = msg.get("content", "").lower()
            for topic, keywords in topic_keywords.items():
                if any(kw in content for kw in keywords):
                    discussed.add(topic)

        return list(discussed)

    def _generate_interest_topic(
        self,
        interests: List[str],
        discussed_topics: List[str],
        context: Optional[Dict]
    ) -> Optional[Dict[str, Any]]:
        """生成兴趣话题"""
        available = [i for i in interests if i not in discussed_topics]
        if not available:
            return None

        topic = available[0]
        return {
            "topic": f"聊聊{topic}",
            "category": "interests",
            "opener": f"对了，你好像对{topic}很感兴趣？",
            "follow_up_questions": [
                f"你最喜欢{topic}的什么？",
                f"什么时候开始喜欢{topic}的？",
                f"有什么特别推荐的吗？"
            ],
            "confidence": 0.9
        }

    def _generate_daily_life_topic(
        self,
        interests: List[str],
        discussed_topics: List[str],
        context: Optional[Dict]
    ) -> Optional[Dict[str, Any]]:
        """生成日常生活话题"""
        if "日常生活" in discussed_topics:
            return None

        time_of_day = context.get("time_of_day") if context else None

        if time_of_day == "morning":
            return {
                "topic": "早晨习惯",
                "category": "daily_life",
                "opener": "你平时早上都喜欢做什么呀？",
                "follow_up_questions": [
                    "是早起型还是夜猫子型？",
                    "早餐一般都吃什么？",
                    "有没有什么晨间仪式？"
                ],
                "confidence": 0.8
            }
        elif time_of_day in ["afternoon", "evening"]:
            return {
                "topic": "今日趣事",
                "category": "daily_life",
                "opener": "今天有什么有趣的事情发生吗？",
                "follow_up_questions": [
                    "工作或学习顺利吗？",
                    "有没有遇到什么好玩的人？",
                    "心情怎么样？"
                ],
                "confidence": 0.8
            }

        return {
            "topic": "周末计划",
            "category": "daily_life",
            "opener": "周末有什么安排吗？",
            "follow_up_questions": [
                "喜欢宅家还是出门？",
                "有什么特别的爱好吗？",
                "推荐的活动？"
            ],
            "confidence": 0.75
        }

    def _generate_travel_topic(
        self,
        interests: List[str],
        discussed_topics: List[str],
        context: Optional[Dict]
    ) -> Optional[Dict[str, Any]]:
        """生成旅行话题"""
        if "旅行" in discussed_topics:
            return None

        return {
            "topic": "旅行经历",
            "category": "travel",
            "opener": "你去过的地方里，最喜欢哪里？",
            "follow_up_questions": [
                "有没有特别想再去的地方？",
                "喜欢什么样的旅行方式？",
                "一个人旅行过吗？感觉如何？"
            ],
            "confidence": 0.7
        }

    def _generate_food_topic(
        self,
        interests: List[str],
        discussed_topics: List[str],
        context: Optional[Dict]
    ) -> Optional[Dict[str, Any]]:
        """生成美食话题"""
        if "美食" in discussed_topics:
            return None

        return {
            "topic": "美食探索",
            "category": "food",
            "opener": "你最近有吃到什么好吃的吗？",
            "follow_up_questions": [
                "喜欢什么菜系？",
                "会自己做饭吗？",
                "有没有特别推荐的餐厅？"
            ],
            "confidence": 0.75
        }

    def _generate_entertainment_topic(
        self,
        interests: List[str],
        discussed_topics: List[str],
        context: Optional[Dict]
    ) -> Optional[Dict[str, Any]]:
        """生成娱乐话题"""
        if "电影" in discussed_topics:
            return None

        return {
            "topic": "影视推荐",
            "category": "entertainment",
            "opener": "最近有看什么好看的电影或剧吗？",
            "follow_up_questions": [
                "喜欢什么类型的？",
                "有没有反复刷的？",
                "推荐一部给我？"
            ],
            "confidence": 0.7
        }

    def _generate_childhood_topic(
        self,
        interests: List[str],
        discussed_topics: List[str],
        context: Optional[Dict]
    ) -> Optional[Dict[str, Any]]:
        """生成童年回忆话题"""
        if "童年" in discussed_topics:
            return None

        relationship_stage = context.get("relationship_stage") if context else "new"
        if relationship_stage == "new":
            return None  # 关系初期不适合聊童年

        return {
            "topic": "童年回忆",
            "category": "childhood",
            "opener": "你小时候是什么样的？",
            "follow_up_questions": [
                "有什么有趣的童年经历？",
                "小时候的梦想是什么？",
                "有没有怀念的东西？"
            ],
            "confidence": 0.6
        }

    def _generate_message(self, silence_analysis: Dict, generated_topics: List[Dict]) -> str:
        """生成自然语言建议"""
        silence_level = silence_analysis.get("silence_level", "normal")
        is_awkward = silence_analysis.get("is_awkward", False)
        reasons = silence_analysis.get("possible_reasons", [])
        recommended = silence_analysis.get("recommended_action", "")

        # 基础消息
        if silence_level == "normal":
            message = "对话节奏正常，无需干预~\n"
        elif silence_level == "minor":
            message = "检测到短暂停顿，这是对话的自然节奏。\n"
        elif silence_level == "moderate":
            message = "对话暂时安静下来了，可以考虑开启新话题。\n"
        elif silence_level == "severe":
            message = "沉默时间较长，可能有些尴尬了。\n"
        elif silence_level == "critical":
            message = "⚠️ 检测到严重沉默，建议立即介入！\n"

        # 添加原因分析
        if reasons:
            message += f"\n可能原因：{reasons[0]}\n"

        # 添加话题建议
        if generated_topics and recommended in ["suggest_topic", "immediate_intervention"]:
            message += "\n推荐话题：\n"
            for i, topic in enumerate(generated_topics[:3], 1):
                message += f"{i}. {topic['opener']}\n"

        return message

    def _build_ui(self, silence_analysis: Dict, generated_topics: List[Dict]) -> Dict[str, Any]:
        """构建 UI"""
        silence_level = silence_analysis.get("silence_level", "normal")

        if silence_level == "normal":
            return {
                "component_type": "silence_status",
                "props": {
                    "status": "normal",
                    "message": "对话流畅"
                }
            }

        # 话题卡片列表
        return {
            "component_type": "topic_suggestions",
            "props": {
                "silence_level": silence_level,
                "topics": [
                    {
                        "title": t["topic"],
                        "opener": t["opener"],
                        "follow_ups": t["follow_up_questions"][:2]
                    }
                    for t in generated_topics[:3]
                ],
                "show_confidence": True
            }
        }

    def _generate_actions(self, generated_topics: List[Dict]) -> List[Dict[str, Any]]:
        """生成建议操作"""
        actions = []

        if not generated_topics:
            return [{
                "label": "等待自然恢复",
                "action_type": "wait_natural",
                "params": {}
            }]

        # 添加话题操作
        for topic in generated_topics[:2]:
            actions.append({
                "label": f"使用：{topic['topic']}",
                "action_type": "use_topic",
                "params": {
                    "opener": topic["opener"],
                    "topic": topic["topic"]
                }
            })

        actions.append({
            "label": "查看更多话题",
            "action_type": "show_more_topics",
            "params": {}
        })

        return actions

    async def autonomous_trigger(
        self,
        conversation_id: str,
        user_a_id: str,
        user_b_id: str,
        trigger_type: str,
        context: Optional[Dict] = None
    ) -> dict:
        """
        自主触发沉默检测

        Args:
            conversation_id: 对话 ID
            user_a_id: 用户 A ID
            user_b_id: 用户 B ID
            trigger_type: 触发类型 (timeout, awkward_detected, topic_exhausted)
            context: 上下文信息

        Returns:
            触发结果
        """
        logger.info(f"SilenceBreakerSkill: Autonomous trigger for conversation={conversation_id}, type={trigger_type}")

        # 获取对话历史
        from db.database import SessionLocal
        from db.models import ChatMessageDB

        db = SessionLocal()
        try:
            # 获取最近消息
            messages = db.query(ChatMessageDB).filter(
                ChatMessageDB.conversation_id == conversation_id
            ).order_by(ChatMessageDB.created_at.desc()).limit(20).all()

            conversation_history = [
                {"content": m.content, "created_at": m.created_at, "sender_id": m.sender_id}
                for m in messages
            ][::-1]

            # 估算沉默时长
            silence_duration = self._estimate_silence_from_history(conversation_history)

            # 判断是否需要触发
            should_trigger = False
            if trigger_type == "timeout" and silence_duration >= self.SILENCE_THRESHOLD["moderate"]:
                should_trigger = True
            elif trigger_type == "awkward_detected":
                should_trigger = self._is_awkward_silence(silence_duration, conversation_history, context)
            elif trigger_type == "topic_exhausted":
                discussed = self._extract_discussed_topics(conversation_history)
                should_trigger = len(discussed) >= 3

            if should_trigger:
                result = await self.execute(
                    conversation_id=conversation_id,
                    user_a_id=user_a_id,
                    user_b_id=user_b_id,
                    silence_duration=silence_duration,
                    conversation_history=conversation_history,
                    context=context
                )
                return {
                    "triggered": True,
                    "result": result,
                    "should_push": True
                }

            return {"triggered": False, "reason": "not_needed"}

        finally:
            db.close()


# 全局 Skill 实例
_silence_breaker_skill_instance: Optional[SilenceBreakerSkill] = None


def get_silence_breaker_skill() -> SilenceBreakerSkill:
    """获取沉默破冰 Skill 单例实例"""
    global _silence_breaker_skill_instance
    if _silence_breaker_skill_instance is None:
        _silence_breaker_skill_instance = SilenceBreakerSkill()
    return _silence_breaker_skill_instance
