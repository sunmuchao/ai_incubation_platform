"""
情境感知渲染服务

Values 功能：基于对话情境、用户状态、关系阶段动态选择 UI 组件
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session

from db.database import SessionLocal
from utils.db_session_manager import db_session, db_session_readonly, optional_db_session
from utils.logger import logger
from services.base_service import BaseService


class AdaptiveUIContext:
    """情境上下文"""

    def __init__(
        self,
        user_id: str,
        conversation_id: str = None,
        partner_id: str = None,
        relationship_stage: str = "initial",
        silence_duration: int = 0,
        conflict_detected: bool = False,
        mood: str = "neutral",
        energy_level: str = "medium",
        time_of_day: str = "day",
        day_of_week: str = "weekday",
    ):
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.partner_id = partner_id
        self.relationship_stage = relationship_stage
        self.silence_duration = silence_duration  # 沉默时长（秒）
        self.conflict_detected = conflict_detected
        self.mood = mood
        self.energy_level = energy_level
        self.time_of_day = time_of_day
        self.day_of_week = day_of_week

    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "partner_id": self.partner_id,
            "relationship_stage": self.relationship_stage,
            "silence_duration": self.silence_duration,
            "conflict_detected": self.conflict_detected,
            "mood": self.mood,
            "energy_level": self.energy_level,
            "time_of_day": self.time_of_day,
            "day_of_week": self.day_of_week,
        }


class AdaptiveUIRenderer(BaseService):
    """
    自适应 UI 渲染器

    根据情境动态选择最适合的 UI 组件
    """

    # 情境类型定义
    CONTEXT_TYPES = {
        "normal": "正常对话",
        "silence": "沉默尴尬",
        "conflict": "观点冲突",
        "breakthrough": "关系突破",
        "deep Conversation": "深度交流",
        "casual": "轻松闲聊",
        "first_contact": "首次接触",
        "pre_date": "约会前夕",
        "post_date": "约会之后",
    }

    # UI 组件配置
    UI_COMPONENTS = {
        # 聊天输入类
        "chat_input": {
            "name": "聊天输入框",
            "type": "input",
            "props": {
                "placeholder": "输入消息...",
                "enable_voice": True,
                "enable_emoji": True,
            },
        },
        "chat_input_with_suggestions": {
            "name": "带建议的聊天输入",
            "type": "input_with_suggestions",
            "props": {
                "placeholder": "输入消息或选择建议...",
                "suggested_replies": [],
                "enable_voice": True,
            },
        },
        "ai_translator_input": {
            "name": "AI 传声筒输入",
            "type": "ai_assisted_input",
            "props": {
                "placeholder": "AI 帮你高情商表达...",
                "ai_rewrite": True,
                "tone_options": ["幽默", "真诚", "温柔", "直接"],
            },
        },
        # 卡片类
        "ai_response_card": {
            "name": "AI 响应卡片",
            "type": "card",
            "props": {
                "show_ai_avatar": True,
                "enable_feedback": True,
            },
        },
        "insight_card": {
            "name": "洞察卡片",
            "type": "card",
            "props": {
                "style": "insight",
                "enable_share": True,
            },
        },
        "meditation_card": {
            "name": "情感调解卡片",
            "type": "card",
            "props": {
                "style": "meditation",
                "calming_colors": True,
            },
        },
        # 列表类
        "suggestion_list": {
            "name": "建议列表",
            "type": "list",
            "props": {
                "layout": "vertical",
                "enable_swipe": False,
            },
        },
        "topic_list": {
            "name": "话题列表",
            "type": "list",
            "props": {
                "layout": "grid",
                "enable_selection": True,
            },
        },
        # 特殊组件
        "conflict_mediator": {
            "name": "冲突调解器",
            "type": "mediator",
            "props": {
                "show_tips": True,
                "calm_mode": True,
            },
        },
        "icebreaker_game": {
            "name": "破冰游戏",
            "type": "game",
            "props": {
                "game_type": "question",
                "difficulty": "easy",
            },
        },
        "silence_breaker": {
            "name": "沉默打破器",
            "type": "activity",
            "props": {
                "activity_type": "topic",
                "urgency": "normal",
            },
        },
        "mood_selector": {
            "name": "情绪选择器",
            "type": "selector",
            "props": {
                "moods": ["开心", "平静", "焦虑", "难过", "兴奋"],
                "enable_custom": True,
            },
        },
    }

    def __init__(self, db: Optional[Session] = None):
        """
        初始化服务

        Args:
            db: 可选的数据库会话，如果不提供则在使用时创建临时会话

        推荐用法:
            with db_session() as db:
                service = AdaptiveUIService(db=db)
                service.select_component(context)
        """
        super().__init__(db)
        self._should_close_db: bool = db is None

    def _get_db(self) -> Session:
        """
        获取数据库会话

        注意：推荐在构造函数中传入 db session，避免延迟创建。
        """
        if self._db is None:
            self._db = SessionLocal()
            self._should_close_db = True
        return self._db

    def close(self):
        """关闭服务持有的数据库会话（如果是自己创建的）"""
        if self._should_close_db and self._db is not None:
            try:
                self._db.commit()
                self._db.close()
            except Exception as e:
                logger.error(f"Error closing database session: {e}")
            finally:
                self._db = None
                self._should_close_db = False

    def detect_context_type(self, context: AdaptiveUIContext) -> str:
        """
        检测情境类型

        Args:
            context: 情境上下文

        Returns:
            情境类型
        """
        # 沉默检测
        if context.silence_duration > 30:
            return "silence"

        # 冲突检测
        if context.conflict_detected:
            return "conflict"

        # 关系阶段判断
        if context.relationship_stage == "initial":
            return "first_contact"

        # 情绪判断
        if context.mood in ["anxious", "nervous"]:
            return "pre_date" if context.time_of_day == "evening" else "casual"

        if context.mood in ["happy", "excited"]:
            return "breakthrough" if context.relationship_stage in ["dating", "exclusive"] else "casual"

        # 时间判断
        if context.time_of_day == "night" and context.day_of_week in ["friday", "saturday"]:
            return "deep_conversation"

        return "normal"

    def select_component(
        self,
        context: AdaptiveUIContext,
        data_type: str = None,
        extra_context: Dict = None,
    ) -> Dict[str, Any]:
        """
        选择 UI 组件

        Args:
            context: 情境上下文
            data_type: 数据类型（可选）
            extra_context: 额外上下文（可选）

        Returns:
            UI 组件配置
        """
        context_type = self.detect_context_type(context)
        logger.info(f"Detected context type: {context_type}")

        # 情境 1: 沉默尴尬
        if context_type == "silence":
            return self._handle_silence_context(context)

        # 情境 2: 观点冲突
        elif context_type == "conflict":
            return self._handle_conflict_context(context)

        # 情境 3: 首次接触
        elif context_type == "first_contact":
            return self._handle_first_contact_context(context)

        # 情境 4: 约会前夕
        elif context_type == "pre_date":
            return self._handle_pre_date_context(context)

        # 情境 5: 关系突破
        elif context_type == "breakthrough":
            return self._handle_breakthrough_context(context)

        # 情境 6: 深度交流
        elif context_type == "deep_conversation":
            return self._handle_deep_conversation_context(context)

        # 默认：正常对话
        else:
            return self._handle_normal_context(context, data_type)

    def _handle_silence_context(self, context: AdaptiveUIContext) -> Dict:
        """处理沉默情境"""
        urgency = "high" if context.silence_duration > 60 else "normal"

        return {
            "component_type": "silence_breaker",
            "props": {
                "activity_type": "topic",
                "urgency": urgency,
                "suggested_topics": [
                    "我猜你现在可能有点紧张，其实我也一样",
                    "不如我们聊聊各自最近看过的一部电影？",
                    "AI 观察到你们都提到了喜欢旅行，要不要深入聊聊？",
                ],
                "icebreaker_game": {
                    "enabled": True,
                    "game_type": "question",
                },
            },
            "context_type": "silence",
        }

    def _handle_conflict_context(self, context: AdaptiveUIContext) -> Dict:
        """处理冲突情境"""
        return {
            "component_type": "conflict_mediator",
            "props": {
                "show_tips": True,
                "calm_mode": True,
                "mediation_tips": [
                    "尝试从对方的角度理解这个问题",
                    "这个话题可能比较敏感，先换个轻松的话题吧",
                    "深呼吸，让我们一起冷静地交流",
                ],
                "ai_message": "AI 观察到你们对这个话题有不同看法，这很正常。要不要先聊聊彼此的感受？",
            },
            "context_type": "conflict",
        }

    def _handle_first_contact_context(self, context: AdaptiveUIContext) -> Dict:
        """处理首次接触情境"""
        return {
            "component_type": "chat_input_with_suggestions",
            "props": {
                "placeholder": "打个招呼吧~",
                "suggested_replies": [
                    "你好！很高兴认识你",
                    "看到你也喜欢旅行，有什么推荐的地方吗？",
                    "你的照片很有气质，可以聊聊吗？",
                ],
                "enable_voice": True,
                "show_profile_highlights": True,
            },
            "context_type": "first_contact",
        }

    def _handle_pre_date_context(self, context: AdaptiveUIContext) -> Dict:
        """处理约会前夕情境"""
        return {
            "component_type": "ai_translator_input",
            "props": {
                "placeholder": "紧张吗？让 AI 帮你表达...",
                "ai_rewrite": True,
                "tone_options": ["幽默", "真诚", "温柔", "直接"],
                "date_tips": [
                    "记得确认见面时间和地点",
                    "提前规划交通路线",
                    "保持轻松愉快的心情",
                ],
            },
            "context_type": "pre_date",
        }

    def _handle_breakthrough_context(self, context: AdaptiveUIContext) -> Dict:
        """处理关系突破情境"""
        return {
            "component_type": "insight_card",
            "props": {
                "style": "celebration",
                "title": "关系更进一步",
                "message": "AI 观察到你们的关系正在升温",
                "enable_share": True,
                "milestone_type": "breakthrough",
            },
            "context_type": "breakthrough",
        }

    def _handle_deep_conversation_context(self, context: AdaptiveUIContext) -> Dict:
        """处理深度交流情境"""
        return {
            "component_type": "chat_input",
            "props": {
                "placeholder": "深入聊聊...",
                "enable_voice": True,
                "enable_emoji": True,
                "show_deep_topics": True,
                "deep_topics": [
                    "你对未来的期待是什么？",
                    "什么对你来说最重要？",
                    "你理想中的关系是什么样的？",
                ],
            },
            "context_type": "deep_conversation",
        }

    def _handle_normal_context(
        self,
        context: AdaptiveUIContext,
        data_type: str = None,
    ) -> Dict:
        """处理正常对话情境"""
        # 根据数据类型选择组件
        if data_type == "match":
            return {
                "component_type": "match_card_list",
                "props": {
                    "layout": "swipe",
                    "show_details": True,
                },
            }
        elif data_type == "gift":
            return {
                "component_type": "gift_grid",
                "props": {
                    "layout": "grid",
                    "show_commission": False,
                },
            }
        elif data_type == "date":
            return {
                "component_type": "date_spot_list",
                "props": {
                    "show_map": True,
                    "show_reviews": True,
                },
            }
        else:
            return {
                "component_type": "chat_input",
                "props": {
                    "placeholder": "输入消息...",
                    "enable_voice": True,
                    "enable_emoji": True,
                },
            }

    def render(
        self,
        context: AdaptiveUIContext,
        data: Dict = None,
    ) -> Dict[str, Any]:
        """
        渲染 UI

        Args:
            context: 情境上下文
            data: 数据（可选）

        Returns:
            完整的 UI 配置
        """
        component_config = self.select_component(context, data.get("type") if data else None)

        # 合并数据
        if data:
            component_config["props"]["data"] = data

        return {
            "render_mode": "adaptive",
            "context_type": self.detect_context_type(context),
            "component": component_config,
            "metadata": {
                "user_id": context.user_id,
                "timestamp": datetime.now().isoformat(),
            },
        }


# 全局单例
adaptive_ui_renderer = AdaptiveUIRenderer()
