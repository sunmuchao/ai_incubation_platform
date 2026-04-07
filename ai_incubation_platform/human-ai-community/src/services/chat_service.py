"""
Chat Service - AI 对话服务

提供 AI Agent 与用户的对话管理能力。
包括意图识别、上下文管理、对话历史等功能。
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

from models.member import CommunityMember, MemberType

logger = logging.getLogger(__name__)


@dataclass
class DialogueTurn:
    """对话轮次"""
    role: str  # user/assistant/system
    content: str
    intent: Optional[str] = None  # 识别的意图
    entities: Dict[str, Any] = field(default_factory=dict)  # 提取的实体
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DialogueContext:
    """对话上下文"""
    conversation_id: str
    user_id: str
    turns: List[DialogueTurn] = field(default_factory=list)
    user_profile: Optional[Dict[str, Any]] = None
    pending_intent: Optional[str] = None
    slot_values: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class ChatService:
    """
    AI 对话服务

    提供自然语言对话能力，支持：
    - 意图识别
    - 槽位填充
    - 上下文管理
    - 多轮对话
    """

    def __init__(self, community_service=None, agent_registry=None):
        self.community_service = community_service
        self.agent_registry = agent_registry or {}
        self._conversations: Dict[str, DialogueContext] = {}

    def get_or_create_conversation(self, user_id: str, conversation_id: Optional[str] = None) -> DialogueContext:
        """获取或创建对话上下文"""
        if conversation_id:
            if conversation_id in self._conversations:
                return self._conversations[conversation_id]
            else:
                raise ValueError(f"Conversation not found: {conversation_id}")

        # 创建新对话
        conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
        context = DialogueContext(
            conversation_id=conversation_id,
            user_id=user_id,
        )
        self._conversations[conversation_id] = context
        return context

    def get_conversation(self, conversation_id: str) -> Optional[DialogueContext]:
        """获取对话上下文"""
        return self._conversations.get(conversation_id)

    async def process_message(
        self,
        conversation_id: str,
        user_message: str,
    ) -> Dict[str, Any]:
        """
        处理用户消息

        返回 AI 响应、建议操作和更新后的上下文。
        """
        context = self._conversations.get(conversation_id)
        if not context:
            raise ValueError(f"Conversation not found: {conversation_id}")

        # 添加用户消息
        user_turn = DialogueTurn(
            role="user",
            content=user_message,
        )
        context.turns.append(user_turn)

        # 意图识别
        intent, entities = await self._recognize_intent(user_message, context)
        user_turn.intent = intent
        user_turn.entities = entities

        # 槽位填充
        if intent:
            await self._fill_slots(context, intent, entities)

        # 生成响应
        response = await self._generate_response(context, intent, entities)

        # 添加 AI 响应
        ai_turn = DialogueTurn(
            role="assistant",
            content=response["content"],
            intent=intent,
        )
        context.turns.append(ai_turn)
        context.updated_at = datetime.now()

        return {
            "conversation_id": conversation_id,
            "message": response["content"],
            "intent": intent,
            "suggested_actions": response.get("suggested_actions", []),
            "entities": entities,
        }

    async def _recognize_intent(self, message: str, context: DialogueContext) -> tuple:
        """
        意图识别

        实际实现应使用 NLU 模型或 LLM。
        这里是简化的规则匹配。
        """
        message_lower = message.lower()

        # 推荐意图
        if any(kw in message for kw in ["推荐", "recommend", "有什么好", "看看"]):
            return "recommendation", self._extract_recommendation_entities(message)

        # 匹配意图
        if any(kw in message for kw in ["匹配", "match", "找", "志同道合"]):
            return "matching", self._extract_matching_entities(message)

        # 治理意图
        if any(kw in message for kw in ["举报", "report", "违规", "审核", "moderate"]):
            return "moderation", self._extract_moderation_entities(message)

        # 查询意图
        if any(kw in message for kw in ["查询", "query", "查看", "状态", "status"]):
            return "query", self._extract_query_entities(message)

        # 问候
        if any(kw in message for kw in ["你好", "hello", "hi", "您好", "在吗"]):
            return "greeting", {}

        # 默认
        return "general", {}

    def _extract_recommendation_entities(self, message: str) -> Dict[str, Any]:
        """提取推荐相关实体"""
        entities = {}

        # 提取主题
        topics = ["人工智能", "编程", "数据科学", "产品", "设计", "创业"]
        for topic in topics:
            if topic in message:
                entities["topic"] = topic
                break

        return entities

    def _extract_matching_entities(self, message: str) -> Dict[str, Any]:
        """提取匹配相关实体"""
        entities = {}

        # 提取兴趣关键词
        interests = ["编程", "AI", "投资", "读书", "运动", "音乐", "游戏"]
        matched_interests = [i for i in interests if i in message]
        if matched_interests:
            entities["interests"] = matched_interests

        return entities

    def _extract_moderation_entities(self, message: str) -> Dict[str, Any]:
        """提取治理相关实体"""
        entities = {}

        # 提取 URL（如果有）
        import re
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message)
        if urls:
            entities["content_url"] = urls[0]

        # 提取举报类型
        report_types = ["垃圾广告", "暴力", "色情", "仇恨言论", "骚扰", "欺诈"]
        for rt in report_types:
            if rt in message:
                entities["report_type"] = rt
                break

        return entities

    def _extract_query_entities(self, message: str) -> Dict[str, Any]:
        """提取查询相关实体"""
        entities = {}

        query_types = ["治理报告", "统计数据", "我的记录", "系统状态"]
        for qt in query_types:
            if qt in message:
                entities["query_type"] = qt
                break

        return entities

    async def _fill_slots(self, context: DialogueContext, intent: str, entities: Dict[str, Any]):
        """槽位填充"""
        # 更新当前对话的槽位值
        context.slot_values.update(entities)

        # 检查是否已收集足够的槽位来执行意图
        required_slots = self._get_required_slots(intent)
        filled_slots = [slot for slot in required_slots if slot in context.slot_values]

        if len(filled_slots) == len(required_slots):
            # 所有槽位已填充，可以执行
            context.pending_intent = None
        else:
            # 需要继续收集槽位
            context.pending_intent = intent

    def _get_required_slots(self, intent: str) -> List[str]:
        """获取意图所需的槽位"""
        slot_requirements = {
            "recommendation": ["user_id"],
            "matching": ["user_id", "interests"],
            "moderation": ["content_id"],
            "query": ["query_type"],
        }
        return slot_requirements.get(intent, [])

    async def _generate_response(
        self,
        context: DialogueContext,
        intent: Optional[str],
        entities: Dict[str, Any],
    ) -> Dict[str, Any]:
        """生成 AI 响应"""
        if intent == "greeting":
            return {
                "content": "您好！我是社区 AI 助手，可以帮您：\n\n1. 推荐志同道合的成员\n2. 推荐相关内容和活动\n3. 处理违规内容举报\n4. 解答社区规则问题\n\n请问有什么可以帮您？",
                "suggested_actions": [
                    {"action": "find_members", "label": "找志同道合的人"},
                    {"action": "get_recommendations", "label": "获取内容推荐"},
                    {"action": "report_issue", "label": "举报问题"},
                ],
            }

        elif intent == "recommendation":
            if "topic" in entities:
                topic = entities["topic"]
                return {
                    "content": f"好的，我为您推荐与 **{topic}** 相关的内容和活动。\n\n正在分析您的兴趣偏好，请稍候...",
                    "suggested_actions": [
                        {"action": "view_recommendations", "label": "查看推荐", "topic": topic},
                    ],
                }
            else:
                return {
                    "content": "我可以为您推荐相关内容。请问您对什么主题感兴趣？\n\n例如：人工智能、编程、数据科学、产品设计等。",
                    "suggested_actions": [
                        {"action": "select_topic", "label": "选择主题", "topics": ["人工智能", "编程", "数据科学", "产品设计"]},
                    ],
                }

        elif intent == "matching":
            if "interests" in entities:
                interests_str = "、".join(entities["interests"])
                return {
                    "content": f"收到！您想寻找对 **{interests_str}** 感兴趣的伙伴。\n\n正在为您匹配志同道合的成员...",
                    "suggested_actions": [
                        {"action": "view_matches", "label": "查看匹配结果"},
                    ],
                }
            else:
                return {
                    "content": "我可以帮您找到志同道合的社区成员。\n\n请告诉我您的兴趣爱好，或者您想寻找什么样的伙伴？",
                    "suggested_actions": [
                        {"action": "describe_interests", "label": "描述兴趣", "placeholder": "例如：我喜欢 Python 编程和机器学习..."},
                    ],
                }

        elif intent == "moderation":
            if "content_url" in entities:
                return {
                    "content": f"收到举报。我正在分析内容：{entities['content_url'][:50]}...\n\n如有必要，我会立即采取处理措施。感谢您维护社区秩序！",
                    "suggested_actions": [
                        {"action": "check_status", "label": "查看处理进度"},
                    ],
                }
            else:
                return {
                    "content": "我是 AI 版主小安，负责维护社区秩序。\n\n如果您发现违规内容，请提供链接或详细描述，我会立即处理。",
                    "suggested_actions": [
                        {"action": "report_content", "label": "举报内容", "placeholder": "请提供内容链接或描述"},
                    ],
                }

        elif intent == "query":
            query_type = entities.get("query_type", "系统状态")
            return {
                "content": f"正在查询 **{query_type}**...\n\n当前社区运行正常。本周已处理 156 条内容，AI 决策准确率 94%。",
                "suggested_actions": [
                    {"action": "view_report", "label": "查看治理报告"},
                    {"action": "view_stats", "label": "查看统计数据"},
                ],
            }

        else:
            # 默认响应
            return {
                "content": "您好！我是社区 AI 助手，可以帮您：\n\n1. **推荐志同道合的成员** - 找到兴趣相投的伙伴\n2. **推荐相关内容和活动** - 发现您感兴趣的内容\n3. **处理违规内容举报** - 维护社区秩序\n4. **解答社区规则问题** - 了解社区规范\n\n请问有什么可以帮您？",
                "suggested_actions": [
                    {"action": "find_members", "label": "找志同道合的人"},
                    {"action": "get_recommendations", "label": "获取内容推荐"},
                    {"action": "report_issue", "label": "举报问题"},
                    {"action": "ask_rules", "label": "了解社区规则"},
                ],
            }

    def get_conversation_history(self, conversation_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取对话历史"""
        context = self._conversations.get(conversation_id)
        if not context:
            return []

        turns = context.turns[-limit:]
        return [
            {
                "role": turn.role,
                "content": turn.content,
                "intent": turn.intent,
                "entities": turn.entities,
                "timestamp": turn.timestamp.isoformat(),
            }
            for turn in turns
        ]


# 全局服务实例
_chat_service: Optional[ChatService] = None


def get_chat_service(community_service=None, agent_registry=None) -> ChatService:
    """获取聊天服务单例"""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService(community_service, agent_registry)
    return _chat_service
