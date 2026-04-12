"""
消息解读服务

参考 Hinge 的 Prompt 功能：
- AI 帮助用户理解对方消息的含义
- 分析消息背后的情感和意图
- 提供回复建议
- 避免误解，促进有效沟通
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from utils.logger import logger
from services.base_service import BaseService


class MessageInterpretationService(BaseService):
    """消息解读服务"""

    # 解读类型
    INTERPRETATION_TYPES = [
        "meaning",       # 含义解读
        "emotion",       # 情感分析
        "intent",        # 意图分析
        "suggestion",    # 回复建议
        "context",       # 上下文关联
    ]

    def __init__(self, db: Session):
        super().__init__(db)
        self.db = db

    async def interpret_message(
        self,
        user_id: str,
        message_id: str,
        message_content: str,
        partner_id: str,
        interpretation_type: str = "meaning",
        conversation_context: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        解读消息

        Args:
            user_id: 用户 ID
            message_id: 消息 ID
            message_content: 消息内容
            partner_id: 对方 ID
            interpretation_type: 解读类型（meaning/emotion/intent/suggestion/context）
            conversation_context: 对话上下文（最近几条消息）

        Returns:
            {
                "interpretation_id": 解读 ID,
                "message_id": 消息 ID,
                "interpretation_type": 解读类型,
                "result": 解读结果,
                "confidence": 置信度,
                "suggestions": 回复建议（可选）,
                "created_at": 创建时间
            }
        """
        # 根据解读类型选择分析方法
        if interpretation_type == "meaning":
            result = await self._analyze_meaning(message_content, conversation_context)
        elif interpretation_type == "emotion":
            result = await self._analyze_emotion(message_content)
        elif interpretation_type == "intent":
            result = await self._analyze_intent(message_content, conversation_context)
        elif interpretation_type == "suggestion":
            result = await self._generate_reply_suggestions(message_content, conversation_context)
        elif interpretation_type == "context":
            result = await self._analyze_context(message_content, conversation_context)
        else:
            # 综合解读
            result = await self._comprehensive_interpretation(message_content, conversation_context)

        interpretation_id = str(uuid.uuid4())

        # 记录解读历史
        from db.models import MessageInterpretationDB

        interpretation_record = MessageInterpretationDB(
            id=interpretation_id,
            user_id=user_id,
            message_id=message_id,
            partner_id=partner_id,
            interpretation_type=interpretation_type,
            result=result.get("summary", ""),
            details=result,
            confidence=result.get("confidence", 0.8),
            created_at=datetime.now()
        )
        self.db.add(interpretation_record)
        self.db.commit()

        logger.info(f"Message interpretation created: {interpretation_id} for message {message_id}")

        return {
            "interpretation_id": interpretation_id,
            "message_id": message_id,
            "interpretation_type": interpretation_type,
            "result": result,
            "confidence": result.get("confidence", 0.8),
            "created_at": datetime.now().isoformat()
        }

    async def _analyze_meaning(
        self,
        message_content: str,
        context: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        分析消息含义

        理解消息的字面意思和潜在含义
        """
        # 调用 AI 进行分析
        from services.llm_service import get_llm_service

        llm_service = get_llm_service()

        # 构建上下文
        context_text = ""
        if context:
            recent_messages = context[-5:]  # 最近 5 条消息
            context_text = "\n最近对话：\n" + "\n".join([
                f"{m.get('sender', '对方')}: {m.get('content', '')}"
                for m in recent_messages
            ])

        prompt = f"""请分析这条消息的含义：

消息内容："{message_content}"
{context_text}

请从以下角度分析：
1. 字面含义：消息直接表达的内容
2. 潜在含义：消息可能隐含的意思
3. 文化背景：是否有特定的文化或语境含义
4. 关键词：消息中的关键词及其可能的含义

请用简洁的语言总结，并给出置信度（0-1）。

回复格式：
{
  "literal_meaning": "字面含义",
  "hidden_meaning": "潜在含义（如果有）",
  "cultural_context": "文化背景说明（如果有）",
  "keywords": ["关键词列表"],
  "summary": "一句话总结",
  "confidence": 0.85
}"""

        try:
            result = await llm_service.generate(prompt)
            # 解析结果
            import json
            parsed = json.loads(result)
            return parsed
        except Exception as e:
            logger.error(f"Failed to analyze meaning: {e}")
            return {
                "literal_meaning": message_content,
                "hidden_meaning": None,
                "summary": "无法深入分析",
                "confidence": 0.5,
                "error": str(e)
            }

    async def _analyze_emotion(self, message_content: str) -> Dict[str, Any]:
        """
        分析消息情感

        识别消息中表达的情感状态
        """
        from services.llm_service import get_llm_service
        from services.emotion_analysis_service import EmotionAnalysisService

        # 使用现有的情感分析服务
        emotion_service = EmotionAnalysisService(self.db)
        try:
            emotion_result = await emotion_service.analyze_message(message_content)

            return {
                "primary_emotion": emotion_result.get("primary_emotion", "neutral"),
                "emotion_intensity": emotion_result.get("intensity", 0.5),
                "emotion_distribution": emotion_result.get("distribution", {}),
                "sentiment": emotion_result.get("sentiment", "neutral"),
                "summary": f"主要情感：{emotion_result.get('primary_emotion', '中性')}",
                "confidence": emotion_result.get("confidence", 0.7)
            }
        except Exception as e:
            logger.error(f"Failed to analyze emotion: {e}")
            return {
                "primary_emotion": "neutral",
                "emotion_intensity": 0.5,
                "summary": "情感分析失败",
                "confidence": 0.5
            }

    async def _analyze_intent(
        self,
        message_content: str,
        context: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        分析消息意图

        理解发送者的目的和期望
        """
        from services.llm_service import get_llm_service

        llm_service = get_llm_service()

        context_text = ""
        if context:
            recent_messages = context[-3:]
            context_text = "\n最近对话：\n" + "\n".join([
                f"{m.get('sender', '对方')}: {m.get('content', '')}"
                for m in recent_messages
            ])

        prompt = f"""请分析这条消息背后的意图：

消息内容："{message_content}"
{context_text}

请判断发送者可能的意图：
1. 主要意图：想要表达或达成什么
2. 期望回应：希望收到什么样的回复
3. 关系信号：对关系的暗示或期望
4. 行动提示：是否暗示要做某事

回复格式：
{
  "primary_intent": "主要意图",
  "expected_response": "期望的回应类型",
  "relationship_signal": "关系信号",
  "action_hint": "行动提示（如果有）",
  "summary": "一句话总结",
  "confidence": 0.8
}"""

        try:
            result = await llm_service.generate(prompt)
            import json
            parsed = json.loads(result)
            return parsed
        except Exception as e:
            logger.error(f"Failed to analyze intent: {e}")
            return {
                "primary_intent": "unknown",
                "summary": "意图分析失败",
                "confidence": 0.5
            }

    async def _generate_reply_suggestions(
        self,
        message_content: str,
        context: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        生成回复建议

        根据消息内容和上下文，提供合适的回复选项
        """
        from services.llm_service import get_llm_service

        llm_service = get_llm_service()

        context_text = ""
        if context:
            recent_messages = context[-5:]
            context_text = "\n最近对话：\n" + "\n".join([
                f"{m.get('sender', '对方')}: {m.get('content', '')}"
                for m in recent_messages
            ])

        prompt = f"""请为这条消息生成合适的回复建议：

消息内容："{message_content}"
{context_text}

请提供 3 种不同风格的回复建议：
1. 自然回复：最常见的回应方式
2. 深入回复：更有深度的回应
3. 幽默回复：轻松有趣的回应

每种回复请说明：
- 回复内容
- 适用场景
- 预期效果

回复格式：
{
  "suggestions": [
    {
      "type": "natural",
      "content": "回复内容",
      "scenario": "适用场景",
      "expected_effect": "预期效果"
    },
    ...
  ],
  "best_pick": "推荐最佳回复",
  "summary": "一句话建议",
  "confidence": 0.85
}"""

        try:
            result = await llm_service.generate(prompt)
            import json
            parsed = json.loads(result)
            return parsed
        except Exception as e:
            logger.error(f"Failed to generate suggestions: {e}")
            return {
                "suggestions": [
                    {"type": "natural", "content": "好的", "scenario": "一般情况"}
                ],
                "summary": "回复建议生成失败",
                "confidence": 0.5
            }

    async def _analyze_context(
        self,
        message_content: str,
        context: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        分析上下文关联

        理解消息在整个对话中的位置和意义
        """
        if not context:
            return {
                "context_relevance": "无上下文",
                "summary": "这是对话的开始",
                "confidence": 0.5
            }

        from services.llm_service import get_llm_service

        llm_service = get_llm_service()

        recent_messages = context[-10:]
        context_text = "\n最近对话：\n" + "\n".join([
            f"{m.get('sender', '对方')}: {m.get('content', '')}"
            for m in recent_messages
        ])

        prompt = f"""请分析这条消息在对话上下文中的意义：

当前消息："{message_content}"
{context_text}

请分析：
1. 话题延续：是否延续之前的话题
2. 话题转换：是否开启了新话题
3. 对话阶段：处于对话的哪个阶段（开场/深入/结束）
4. 关系进展：对关系发展的意义

回复格式：
{
  "topic_continuation": "话题延续说明",
  "topic_transition": "话题转换说明（如果有）",
  "conversation_stage": "对话阶段",
  "relationship_progress": "关系进展意义",
  "summary": "一句话总结",
  "confidence": 0.8
}"""

        try:
            result = await llm_service.generate(prompt)
            import json
            parsed = json.loads(result)
            return parsed
        except Exception as e:
            logger.error(f"Failed to analyze context: {e}")
            return {
                "context_relevance": "分析失败",
                "summary": "上下文分析失败",
                "confidence": 0.5
            }

    async def _comprehensive_interpretation(
        self,
        message_content: str,
        context: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        综合解读

        提供包含含义、情感、意图、建议的综合分析
        """
        # 并行调用各个分析
        meaning = await self._analyze_meaning(message_content, context)
        emotion = await self._analyze_emotion(message_content)
        intent = await self._analyze_intent(message_content, context)

        return {
            "meaning": meaning,
            "emotion": emotion,
            "intent": intent,
            "summary": f"含义：{meaning.get('summary', '')} | 情感：{emotion.get('primary_emotion', '')} | 意图：{intent.get('primary_intent', '')}",
            "confidence": min(meaning.get("confidence", 0.7), emotion.get("confidence", 0.7), intent.get("confidence", 0.7))
        }

    def get_interpretation_history(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取解读历史
        """
        from db.models import MessageInterpretationDB

        interpretations = self.db.query(MessageInterpretationDB).filter(
            MessageInterpretationDB.user_id == user_id
        ).order_by(desc(MessageInterpretationDB.created_at)).limit(limit).all()

        return [
            {
                "interpretation_id": i.id,
                "message_id": i.message_id,
                "interpretation_type": i.interpretation_type,
                "result": i.result,
                "details": i.details,
                "confidence": i.confidence,
                "created_at": i.created_at.isoformat()
            }
            for i in interpretations
        ]


# 服务工厂函数
def get_message_interpretation_service(db: Session) -> MessageInterpretationService:
    """获取消息解读服务实例"""
    return MessageInterpretationService(db)