"""
悬浮球快速对话服务

功能:
- 用户问 Her 关于匹配对象的问题
- AI 分析聊天上下文给出建议
- 支持"她为什么不回我"等场景化问题
"""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import json

from llm.client import call_llm
from utils.db_session_manager import db_session, db_session_readonly, optional_db_session
from db.models import UserDB, ChatMessageDB, ChatConversationDB
from utils.logger import logger
from sqlalchemy import or_, and_, desc
from services.memory_service import get_memory_service
from services.ai_feedback_service import get_ai_feedback_service


class QuickChatService:
    """悬浮球快速对话服务"""

    def __init__(self, db: Optional[Session] = None):
        # 使用延迟导入避免模块加载顺序问题
        from db.database import SessionLocal
        self.db = db or SessionLocal()
        self._should_close_db = db is None

    def close(self):
        """关闭数据库会话"""
        if self._should_close_db and self.db is not None:
            try:
                self.db.close()
            except Exception as e:
                logger.error(f"Error closing database session: {e}")
            finally:
                self.db = None

    def get_ai_advice(
        self,
        current_user_id: str,
        partner_id: str,
        question: str,
        recent_messages: List[Dict],
    ) -> Dict:
        """
        获取 AI 建议

        Args:
            current_user_id: 当前用户 ID
            partner_id: 匹配对象 ID
            question: 用户问题 (如"她为什么不回我消息")
            recent_messages: 最近聊天记录

        Returns:
            AI 建议字典
        """
        try:
            # 1. 获取记忆服务，检索相关记忆
            memory_service = get_memory_service()
            contextual_memories = []
            if memory_service:
                # 从问题中提取关键词搜索相关记忆
                contextual_memories = memory_service.get_contextual_memories(
                    user_id=current_user_id,
                    current_context=question,
                    limit=5,
                )
                logger.info(f"Found {len(contextual_memories)} contextual memories for user {current_user_id}")

            # 2. 获取对方资料
            partner_profile = self._get_partner_profile(partner_id)

            # 3. 获取双方聊天记录（如果前端传来的不够，从 DB 补充）
            conversation_history = self._get_conversation_history(
                current_user_id, partner_id, limit=20
            )

            # 如果前端没传聊天记录，用后端的
            if not recent_messages and conversation_history:
                recent_messages = conversation_history

            # 4. 构建 Prompt（加入记忆）
            prompt = self._build_prompt_with_memory(
                question=question,
                partner_profile=partner_profile,
                recent_messages=recent_messages,
                memories=contextual_memories,
            )

            # 5. 调用 LLM
            response = call_llm(
                prompt=prompt,
                system_prompt="你是一位专业的情感军师，帮助用户分析和匹配对象的聊天。语气温暖、专业，不要说教。",
                temperature=0.7,
                max_tokens=600,
            )

            # 6. 解析并返回
            return self._parse_response(response)

        except Exception as e:
            logger.error(f"QuickChat advice failed: {e}")
            return {
                "answer": "抱歉，我现在无法思考，请稍后再试～",
                "suggestions": [],
                "analysis": {},
            }

    def suggest_reply(
        self,
        current_user_id: str,
        partner_id: str,
        last_message: Dict,
        recent_messages: List[Dict],
        relationship_stage: str = "初识",
    ) -> Dict:
        """
        生成回复建议

        Args:
            current_user_id: 当前用户 ID
            partner_id: 匹配对象 ID
            last_message: 对方最后一条消息
            recent_messages: 最近聊天记录
            relationship_stage: 关系阶段

        Returns:
            回复建议列表
        """
        try:
            # 1. 获取记忆服务，检索相关记忆
            memory_service = get_memory_service()
            contextual_memories = []
            if memory_service:
                # 从对方消息中提取关键词搜索相关记忆
                contextual_memories = memory_service.get_contextual_memories(
                    user_id=current_user_id,
                    current_context=last_message.get("content", ""),
                    limit=3,
                )
                logger.info(f"Found {len(contextual_memories)} contextual memories for reply suggestion")

            partner_profile = self._get_partner_profile(partner_id)

            prompt = self._build_reply_prompt_with_memory(
                partner_profile=partner_profile,
                last_message=last_message,
                recent_messages=recent_messages,
                relationship_stage=relationship_stage,
                memories=contextual_memories,
            )

            response = call_llm(
                prompt=prompt,
                system_prompt="你是一位恋爱聊天助手，帮用户生成回复建议。输出严格的 JSON 格式。",
                temperature=0.8,
                max_tokens=400,
            )

            # 解析 JSON 响应
            try:
                result = json.loads(response.strip())
                suggestions = result.get("suggestions", [])

                # 为每个建议生成唯一 ID（用于反馈追踪）
                import uuid
                for sug in suggestions:
                    sug["id"] = str(uuid.uuid4())

                # 2. 对话结束后提取记忆（异步处理，不阻塞响应）
                if memory_service and recent_messages:
                    try:
                        dialogue_text = "\n".join([f"{m.get('senderId', 'unknown')}: {m.get('content', '')}" for m in recent_messages[-5:]])
                        memory_service.extract_memory_from_dialogue(
                            dialogue=dialogue_text,
                            user_id=current_user_id,
                        )
                        logger.info(f"Extracted memories from dialogue for user {current_user_id}")
                    except Exception as e:
                        logger.warning(f"Memory extraction failed: {e}")

                return {"success": True, "suggestions": suggestions}
            except json.JSONDecodeError:
                # 降级处理：尝试从文本中提取
                return {
                    "success": True,
                    "suggestions": [
                        {"style": "真诚关心", "content": response.strip()[:50], "id": str(__import__('uuid').uuid4())},
                    ],
                }

        except Exception as e:
            logger.error(f"Suggest reply failed: {e}")
            return {
                "success": False,
                "suggestions": [
                    {"style": "默认", "content": "抱歉，AI 思考中，请稍后再试～", "id": str(__import__('uuid').uuid4())},
                ],
            }

    def record_suggestion_feedback(
        self,
        current_user_id: str,
        partner_id: str,
        suggestion_id: str,
        feedback_type: str,
        suggestion_content: str,
        suggestion_style: str,
        user_actual_reply: Optional[str] = None,
    ) -> str:
        """
        记录用户对 AI 建议的反馈

        Args:
            current_user_id: 当前用户 ID
            partner_id: 匹配对象 ID
            suggestion_id: 建议 ID
            feedback_type: 反馈类型 (adopted/ignored/modified)
            suggestion_content: AI 建议内容
            suggestion_style: 建议风格
            user_actual_reply: 用户实际发送的内容

        Returns:
            反馈记录 ID
        """
        feedback_service = get_ai_feedback_service()
        return feedback_service.record_feedback(
            user_id=current_user_id,
            partner_id=partner_id,
            suggestion_id=suggestion_id,
            feedback_type=feedback_type,
            suggestion_content=suggestion_content,
            suggestion_style=suggestion_style,
            user_actual_reply=user_actual_reply,
        )

    def _get_partner_profile(self, partner_id: str) -> Dict:
        """获取对方资料"""
        try:
            user = self.db.query(UserDB).filter(UserDB.id == partner_id).first()
            if not user:
                return {"name": "TA", "age": "?", "location": "未知", "interests": []}

            return {
                "name": user.name or "TA",
                "age": user.age or "?",
                "location": user.location or "未知",
                "gender": user.gender or "",
                "interests": user.interests or [],
                "bio": user.bio or "",
            }
        except Exception as e:
            logger.error(f"Get partner profile failed: {e}")
            return {"name": "TA", "age": "?", "location": "未知", "interests": []}

    def _get_conversation_history(
        self,
        user_id_1: str,
        user_id_2: str,
        limit: int = 20,
    ) -> List[Dict]:
        """获取聊天历史"""
        try:
            # 获取会话
            conversation = self.db.query(ChatConversationDB).filter(
                or_(
                    and_(
                        ChatConversationDB.user_id_1 == user_id_1,
                        ChatConversationDB.user_id_2 == user_id_2,
                    ),
                    and_(
                        ChatConversationDB.user_id_1 == user_id_2,
                        ChatConversationDB.user_id_2 == user_id_1,
                    ),
                )
            ).first()

            if not conversation:
                return []

            # 获取消息
            messages = (
                self.db.query(ChatMessageDB)
                .filter(ChatMessageDB.conversation_id == conversation.id)
                .order_by(desc(ChatMessageDB.created_at))
                .limit(limit)
                .all()
            )

            return [
                {
                    "senderId": "me" if msg.sender_id == user_id_1 else "her",
                    "content": msg.content,
                    "timestamp": msg.created_at.isoformat(),
                }
                for msg in messages
            ]
        except Exception as e:
            logger.error(f"Get conversation history failed: {e}")
            return []

    def _build_prompt(
        self,
        question: str,
        partner_profile: Dict,
        recent_messages: List[Dict],
    ) -> str:
        """构建 AI Prompt"""

        # 格式化聊天记录
        messages_text = self._format_messages(recent_messages)

        return f"""用户正在和匹配对象聊天，需要你的建议。

## 对方资料
- 昵称：{partner_profile.get('name', '未知')}
- 年龄：{partner_profile.get('age', '?')}
- 所在地：{partner_profile.get('location', '未知')}
- 兴趣爱好：{', '.join(partner_profile.get('interests', [])) or '未填写'}

## 最近聊天内容
{messages_text}

## 用户问题
{question}

## 任务
1. 分析问题背后的情绪（用户是焦虑/困惑/生气？）
2. 根据聊天记录分析对方的态度
3. 给出具体、可操作的建议

请温暖、专业地回复，不要说教。如果需要更多信息，也请友善地询问。
"""

    def _build_prompt_with_memory(
        self,
        question: str,
        partner_profile: Dict,
        recent_messages: List[Dict],
        memories: List[Dict],
    ) -> str:
        """构建带记忆检索的 AI Prompt"""

        # 格式化聊天记录
        messages_text = self._format_messages(recent_messages)

        # 格式化记忆
        memory_text = ""
        if memories:
            memory_lines = []
            for mem in memories:
                content = mem.get("content", "")
                category = mem.get("category", "")
                importance = mem.get("importance", 3)
                if importance >= 4:  # 只显示重要记忆
                    memory_lines.append(f"- {content}")
            if memory_lines:
                memory_text = "\n".join(memory_lines)

        return f"""用户正在和匹配对象聊天，需要你的建议。

## 对方资料
- 昵称：{partner_profile.get('name', '未知')}
- 年龄：{partner_profile.get('age', '?')}
- 所在地：{partner_profile.get('location', '未知')}
- 兴趣爱好：{', '.join(partner_profile.get('interests', [])) or '未填写'}

## 最近聊天内容
{messages_text}

## 用户的重要信息（来自长期记忆）
{memory_text if memory_text else "暂无相关记忆"}

## 用户问题
{question}

## 任务
1. 分析问题背后的情绪（用户是焦虑/困惑/生气？）
2. 根据聊天记录和长期记忆分析对方的态度
3. 结合用户的历史偏好，给出个性化建议

请温暖、专业地回复，不要说教。如果需要更多信息，也请友善地询问。
"""

    def _build_reply_prompt(
        self,
        partner_profile: Dict,
        last_message: Dict,
        recent_messages: List[Dict],
        relationship_stage: str,
    ) -> str:
        """构建回复建议 Prompt"""

        messages_text = self._format_messages(recent_messages)

        return f"""帮用户生成回复建议。

## 对方资料
- 昵称：{partner_profile.get('name', '未知')}
- 关系阶段：{relationship_stage}

## 对方刚发的消息
{last_message.get('content', '')}

## 最近聊天上下文
{messages_text}

## 任务
生成 3 种不同风格的回复，每种 25 字以内：
1. 【幽默风趣】- 用轻松幽默的方式回应
2. 【真诚关心】- 表达关心和在意
3. 【延续话题】- 让对话能继续下去

请严格输出 JSON 格式：
{{
  "suggestions": [
    {{"style": "幽默风趣", "content": "..."}},
    {{"style": "真诚关心", "content": "..."}},
    {{"style": "延续话题", "content": "..."}}
  ]
}}
"""

    def _build_reply_prompt_with_memory(
        self,
        partner_profile: Dict,
        last_message: Dict,
        recent_messages: List[Dict],
        relationship_stage: str,
        memories: List[Dict],
    ) -> str:
        """构建带记忆的回复建议 Prompt"""

        messages_text = self._format_messages(recent_messages)

        # 格式化记忆
        memory_text = ""
        if memories:
            memory_lines = []
            for mem in memories:
                content = mem.get("content", "")
                category = mem.get("category", "")
                if category in ["preference", "user_info", "relationship"]:
                    memory_lines.append(f"- {content}")
            if memory_lines:
                memory_text = "\n".join(memory_lines)

        return f"""帮用户生成回复建议。

## 对方资料
- 昵称：{partner_profile.get('name', '未知')}
- 关系阶段：{relationship_stage}

## 对方刚发的消息
{last_message.get('content', '')}

## 最近聊天上下文
{messages_text}

## 用户的相关记忆（帮助个性化回复）
{memory_text if memory_text else "暂无相关记忆"}

## 任务
生成 3 种不同风格的回复，每种 25 字以内：
1. 【幽默风趣】- 用轻松幽默的方式回应
2. 【真诚关心】- 表达关心和在意
3. 【延续话题】- 让对话能继续下去

请结合用户的记忆和偏好，生成更个性化的回复。

请严格输出 JSON 格式：
{{
  "suggestions": [
    {{"style": "幽默风趣", "content": "..."}},
    {{"style": "真诚关心", "content": "..."}},
    {{"style": "延续话题", "content": "..."}}
  ]
}}
"""

    def _format_messages(self, messages: List[Dict]) -> str:
        """格式化聊天记录"""
        if not messages:
            return "暂无聊天记录"

        lines = []
        # 只取最近 10 条
        for msg in messages[-10:]:
            sender = "你" if msg.get("senderId") == "me" else "对方"
            content = msg.get("content", "...")
            lines.append(f"{sender}: {content}")
        return "\n".join(lines)

    def _parse_response(self, llm_output: str) -> Dict:
        """解析 LLM 输出"""
        # 尝试提取建议
        suggestions = []

        # 简单版本：直接返回文本
        return {
            "answer": llm_output,
            "suggestions": suggestions,
            "analysis": {
                "partnerMood": "unknown",
                "responseDelay": "unknown",
                "riskLevel": "low",
            },
        }


# 测试
if __name__ == "__main__":
    from sqlalchemy import or_, and_

    service = QuickChatService()

    result = service.get_ai_advice(
        current_user_id="test_user",
        partner_id="test_partner",
        question="她为什么不回我消息？",
        recent_messages=[
            {"senderId": "me", "content": "在干嘛呢？", "timestamp": "2026-04-09T10:00:00Z"},
            {"senderId": "her", "content": "在开会", "timestamp": "2026-04-09T10:05:00Z"},
        ],
    )

    print(f"Result: {result}")
