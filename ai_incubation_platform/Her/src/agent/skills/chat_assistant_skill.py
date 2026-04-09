"""
聊天助手 Skill

AI 聊天助手核心 Skill - 消息发送、会话管理、聊天建议
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from agent.skills.base import BaseSkill
from utils.logger import logger


class ChatAssistantSkill:
    """
    AI 聊天助手 Skill - 帮助用户更好地聊天

    核心能力:
    - 消息发送和管理
    - 会话列表和历史记录
    - 聊天建议生成（破冰、话题）
    - 已读/未读管理

    自主触发:
    - 检测到长时间未回复
    - 对方发送消息后提供回复建议
    - 定期提醒查看未读消息
    """

    name = "chat_assistant"
    version = "1.0.0"
    description = """
    AI 聊天助手，帮助用户更好地聊天

    能力:
    - 消息发送和管理
    - 会话列表和历史记录
    - 聊天建议生成（破冰、话题）
    - 已读/未读管理
    """

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": [
                        "send_message",
                        "get_conversations",
                        "get_history",
                        "mark_read",
                        "get_suggestions",
                        "get_unread_count"
                    ],
                    "description": "操作类型"
                },
                "user_id": {
                    "type": "string",
                    "description": "用户 ID"
                },
                "receiver_id": {
                    "type": "string",
                    "description": "接收者 ID"
                },
                "content": {
                    "type": "string",
                    "description": "消息内容"
                },
                "message_type": {
                    "type": "string",
                    "enum": ["text", "image", "emoji", "voice"],
                    "description": "消息类型"
                },
                "conversation_id": {
                    "type": "string",
                    "description": "会话 ID"
                },
                "message_id": {
                    "type": "string",
                    "description": "消息 ID"
                },
                "other_user_id": {
                    "type": "string",
                    "description": "对方用户 ID（用于获取历史）"
                },
                "limit": {
                    "type": "number",
                    "description": "返回数量",
                    "default": 20
                }
            },
            "required": ["operation", "user_id"]
        }

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "ai_message": {"type": "string"},
                "chat_data": {
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "string"},
                        "conversation_id": {"type": "string"},
                        "messages": {"type": "array"},
                        "conversations": {"type": "array"},
                        "unread_count": {"type": "number"},
                        "suggestions": {"type": "array"}
                    }
                },
                "generative_ui": {"type": "object"},
                "suggested_actions": {"type": "array"}
            },
            "required": ["success", "ai_message", "chat_data"]
        }

    async def execute(
        self,
        operation: str,
        user_id: str,
        receiver_id: Optional[str] = None,
        content: Optional[str] = None,
        message_type: str = "text",
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        other_user_id: Optional[str] = None,
        limit: int = 20,
        **kwargs
    ) -> dict:
        """执行聊天助手 Skill"""
        logger.info(f"ChatAssistantSkill: Executing operation={operation} for user={user_id}")

        start_time = datetime.now()

        try:
            from db.database import SessionLocal
            from services.chat_service import ChatService

            db = SessionLocal()
            try:
                service = ChatService(db)

                # 根据操作类型执行
                if operation == "send_message":
                    if not receiver_id or not content:
                        return {
                            "success": False,
                            "ai_message": "缺少接收者或消息内容",
                            "error": "Missing receiver_id or content"
                        }
                    result = self._send_message(service, user_id, receiver_id, content, message_type)
                elif operation == "get_conversations":
                    result = self._get_conversations(service, user_id)
                elif operation == "get_history":
                    if not other_user_id:
                        return {
                            "success": False,
                            "ai_message": "缺少对方用户 ID",
                            "error": "Missing other_user_id"
                        }
                    result = self._get_history(service, user_id, other_user_id, limit)
                elif operation == "mark_read":
                    if not message_id and not conversation_id:
                        return {
                            "success": False,
                            "ai_message": "缺少消息 ID 或会话 ID",
                            "error": "Missing message_id or conversation_id"
                        }
                    result = self._mark_read(service, user_id, message_id, conversation_id)
                elif operation == "get_suggestions":
                    if not other_user_id:
                        return {
                            "success": False,
                            "ai_message": "缺少对方用户 ID",
                            "error": "Missing other_user_id"
                        }
                    result = self._get_suggestions(user_id, other_user_id)
                elif operation == "get_unread_count":
                    result = self._get_unread_count(service, user_id)
                else:
                    return {
                        "success": False,
                        "ai_message": f"未知操作类型：{operation}",
                        "error": f"Unknown operation: {operation}"
                    }

                # 生成 AI 消息
                ai_message = self._generate_ai_message(result, operation)

                # 构建 Generative UI
                generative_ui = self._build_generative_ui(result, operation)

                # 生成建议操作
                suggested_actions = self._generate_actions(result, operation)

                execution_time = (datetime.now() - start_time).total_seconds() * 1000

                return {
                    "success": True,
                    "ai_message": ai_message,
                    "chat_data": result,
                    "generative_ui": generative_ui,
                    "suggested_actions": suggested_actions,
                    "skill_metadata": {
                        "name": self.name,
                        "version": self.version,
                        "execution_time_ms": int(execution_time),
                        "operation": operation
                    }
                }

            finally:
                db.close()

        except Exception as e:
            logger.error(f"ChatAssistantSkill: Execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "ai_message": "聊天操作失败，请稍后重试",
                "error": str(e)
            }

    def _send_message(self, service, user_id: str, receiver_id: str, content: str, message_type: str) -> Dict[str, Any]:
        """发送消息"""
        from services.chat_service import ChatService

        message = service.send_message(
            sender_id=user_id,
            receiver_id=receiver_id,
            content=content,
            message_type=message_type
        )

        return {
            "message_id": message.id,
            "conversation_id": message.conversation_id,
            "status": "sent",
            "created_at": message.created_at.isoformat()
        }

    def _get_conversations(self, service, user_id: str) -> Dict[str, Any]:
        """获取会话列表"""
        conversations = service.get_user_conversations(user_id)

        return {
            "conversations": [
                {
                    "id": c.id,
                    "partner_id": c.user_id_2 if c.user_id_1 == user_id else c.user_id_1,
                    "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
                    "last_message_preview": c.last_message_preview,
                    "unread_count": c.unread_count_user1 if c.user_id_1 == user_id else c.unread_count_user2
                }
                for c in conversations
            ],
            "total": len(conversations)
        }

    def _get_history(self, service, user_id: str, other_user_id: str, limit: int) -> Dict[str, Any]:
        """获取聊天历史"""
        messages = service.get_conversation_messages(
            user_id_1=user_id,
            user_id_2=other_user_id,
            limit=limit
        )

        return {
            "messages": [
                {
                    "id": m.id,
                    "sender_id": m.sender_id,
                    "content": m.content,
                    "message_type": m.message_type,
                    "is_read": m.is_read,
                    "created_at": m.created_at.isoformat()
                }
                for m in messages
            ],
            "total": len(messages)
        }

    def _mark_read(
        self,
        service,
        user_id: str,
        message_id: Optional[str],
        conversation_id: Optional[str]
    ) -> Dict[str, Any]:
        """标记已读"""
        success = False
        if message_id:
            success = service.mark_message_read(message_id, user_id)
        elif conversation_id:
            # 标记整个会话已读
            from db.models import ChatMessageDB
            from sqlalchemy import update

            db = service.db
            db.execute(
                update(ChatMessageDB)
                .where(
                    ChatMessageDB.conversation_id == conversation_id,
                    ChatMessageDB.receiver_id == user_id,
                    ~ChatMessageDB.is_read
                )
                .values(is_read=True)
            )
            db.commit()
            success = True

        return {"success": success, "status": "marked_read" if success else "failed"}

    def _get_suggestions(self, user_id: str, other_user_id: str) -> Dict[str, Any]:
        """获取聊天建议"""
        # 从数据库获取用户信息生成建议
        from db.database import SessionLocal
        from db.repositories import UserRepository

        db = SessionLocal()
        try:
            user_repo = UserRepository(db)
            other_user = user_repo.get_by_id(other_user_id)

            suggestions = []

            if other_user:
                # 基于兴趣生成建议
                import json
                interests = json.loads(other_user.interests) if other_user.interests else []

                if interests:
                    suggestions.append({
                        "type": "topic",
                        "content": f"聊聊 TA 喜欢的{interests[0] if interests else '兴趣'}",
                        "reason": "基于 TA 的兴趣"
                    })

                # 基于地理位置生成建议
                if other_user.location:
                    suggestions.append({
                        "type": "topic",
                        "content": f"问问 TA 在{other_user.location}的生活",
                        "reason": "基于 TA 的所在地"
                    })

            # 通用破冰建议
            suggestions.extend([
                {"type": "icebreaker", "content": "最近有看什么好看的电影吗？", "reason": "轻松开场"},
                {"type": "icebreaker", "content": "周末一般喜欢做什么呀？", "reason": "了解生活方式"},
                {"type": "icebreaker", "content": "有什么特别想去的地方吗？", "reason": "为约会做准备"}
            ])

            return {
                "suggestions": suggestions[:5],
                "has_common_interests": len(interests) > 0 if 'interests' in dir() else False
            }
        finally:
            db.close()

    def _get_unread_count(self, service, user_id: str) -> Dict[str, Any]:
        """获取未读消息数"""
        count = service.get_unread_count(user_id)
        return {"unread_count": count}

    def _generate_ai_message(self, result: Dict, operation: str) -> str:
        """生成 AI 消息"""
        if operation == "send_message":
            return "消息已发送~"
        elif operation == "get_conversations":
            count = result.get("total", 0)
            return f"找到{count}个会话"
        elif operation == "get_history":
            count = result.get("total", 0)
            return f"加载了{count}条消息"
        elif operation == "mark_read":
            return "已标记为已读" if result.get("success") else "标记失败"
        elif operation == "get_suggestions":
            suggestions = result.get("suggestions", [])
            return f"为你准备了{len(suggestions)}条聊天建议~"
        elif operation == "get_unread_count":
            count = result.get("unread_count", 0)
            if count > 0:
                return f"你有{count}条未读消息，快看看吧~"
            return "没有未读消息"
        return "操作完成"

    def _build_generative_ui(self, result: Dict, operation: str) -> Dict[str, Any]:
        """构建 Generative UI"""
        if operation == "send_message":
            return {
                "component_type": "message_sent",
                "props": {
                    "message_id": result.get("message_id"),
                    "status": "sent"
                }
            }
        elif operation == "get_conversations":
            return {
                "component_type": "conversation_list",
                "props": {
                    "conversations": result.get("conversations", []),
                    "show_unread": True
                }
            }
        elif operation == "get_history":
            return {
                "component_type": "chat_history",
                "props": {
                    "messages": result.get("messages", []),
                    "show_sender": True
                }
            }
        elif operation == "get_suggestions":
            return {
                "component_type": "suggestion_cards",
                "props": {
                    "suggestions": result.get("suggestions", []),
                    "show_reason": True
                }
            }
        elif operation == "get_unread_count":
            return {
                "component_type": "unread_badge",
                "props": {
                    "count": result.get("unread_count", 0)
                }
            }
        return {"component_type": "empty_state", "props": {"message": "暂无数据"}}

    def _generate_actions(self, result: Dict, operation: str) -> List[Dict[str, Any]]:
        """生成建议操作"""
        actions = []

        if operation == "send_message":
            actions.append({
                "label": "查看会话",
                "action_type": "view_conversation",
                "params": {"conversation_id": result.get("conversation_id")}
            })
        elif operation == "get_conversations":
            actions.append({
                "label": "开始新对话",
                "action_type": "start_new_chat",
                "params": {}
            })
        elif operation == "get_history":
            actions.append({
                "label": "发送消息",
                "action_type": "send_message",
                "params": {}
            })
        elif operation == "get_suggestions":
            actions.append({
                "label": "使用建议",
                "action_type": "use_suggestion",
                "params": {}
            })
            actions.append({
                "label": "刷新建议",
                "action_type": "refresh_suggestions",
                "params": {}
            })

        return actions

    async def autonomous_trigger(
        self,
        user_id: str,
        trigger_type: str,
        context: Optional[Dict] = None
    ) -> dict:
        """自主触发"""
        logger.info(f"ChatAssistantSkill: Autonomous trigger for user={user_id}, type={trigger_type}")

        if trigger_type == "unread_reminder":
            from db.database import SessionLocal
            from services.chat_service import ChatService

            db = SessionLocal()
            try:
                service = ChatService(db)
                count = service.get_unread_count(user_id)

                if count > 0:
                    return {
                        "triggered": True,
                        "result": {"unread_count": count},
                        "should_push": True,
                        "push_message": f"你有{count}条未读消息，记得及时回复哦~"
                    }
            finally:
                db.close()

        elif trigger_type == "reply_suggestion":
            # 检测到对方发送消息后，提供回复建议
            return {
                "triggered": True,
                "result": {"type": "reply_suggestion"},
                "should_push": False,
                "suggestion_mode": "active"
            }

        elif trigger_type == "inactive_reminder":
            # 长时间未聊天提醒
            return {
                "triggered": True,
                "result": {"type": "inactive_reminder"},
                "should_push": True,
                "push_message": "好久没联系了，要不要主动发个消息问候一下？"
            }

        return {"triggered": False, "reason": "not_needed"}


# 全局 Skill 实例
_chat_assistant_skill_instance: Optional[ChatAssistantSkill] = None


def get_chat_assistant_skill() -> ChatAssistantSkill:
    """获取聊天助手 Skill 单例实例"""
    global _chat_assistant_skill_instance
    if _chat_assistant_skill_instance is None:
        _chat_assistant_skill_instance = ChatAssistantSkill()
    return _chat_assistant_skill_instance
