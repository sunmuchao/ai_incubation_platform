"""
AI 辅助创作服务

提供 AI 辅助创作功能：
- 内容润色
- 内容扩写
- 翻译
- 内容摘要
- AI 生成建议

所有 AI 辅助内容都会明确标注 AI 参与度
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import uuid
import json

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.manager import db_manager
from models.member import MemberType, ContentType

logger = logging.getLogger(__name__)

# 尝试导入 DeerFlow 2.0
try:
    from deerflow_integration import AgentRuntime, AgentConfig, ToolContext
    DEERFLOW_AVAILABLE = True
except ImportError:
    DEERFLOW_AVAILABLE = False
    logger.warning("DeerFlow 2.0 未安装，AI 辅助功能将使用占位实现")


# AI 辅助类型
class AIAssistType:
    POLISH = "polish"           # 润色
    EXPAND = "expand"           # 扩写
    TRANSLATE = "translate"     # 翻译
    SUMMARIZE = "summarize"     # 摘要
    GENERATE = "generate"       # 生成
    SUGGEST = "suggest"         # 建议


# 翻译语言配置
TRANSLATION_LANGUAGES = {
    "en": "英语",
    "zh": "中文",
    "ja": "日语",
    "ko": "韩语",
    "fr": "法语",
    "de": "德语",
    "es": "西班牙语",
}

# AI 辅助标识
AI_ASSIST_BADGES = {
    AIAssistType.POLISH: "📝 AI 润色",
    AIAssistType.EXPAND: "✍️ AI 扩写",
    AIAssistType.TRANSLATE: "🌐 AI 翻译",
    AIAssistType.SUMMARIZE: "📋 AI 摘要",
    AIAssistType.GENERATE: "🤖 AI 生成",
    AIAssistType.SUGGEST: "💡 AI 建议",
}


class AIAssistService:
    """AI 辅助创作服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._call_history = []
        self._agent_runtime = None

        if DEERFLOW_AVAILABLE:
            try:
                self._agent_runtime = AgentRuntime(AgentConfig(
                    name="ai_assist",
                    description="AI 辅助创作助手",
                ))
                logger.info("DeerFlow 2.0 Agent 运行时初始化成功")
            except Exception as e:
                logger.error(f"DeerFlow 2.0 初始化失败：{e}")

    async def polish_content(
        self,
        content: str,
        style: str = "formal",
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        润色内容

        Args:
            content: 原始内容
            style: 风格（formal 正式，casual 休闲，academic 学术，creative 创意）
            user_id: 用户 ID

        Returns:
            {
                "original": str,
                "polished": str,
                "assist_type": str,
                "ai_badge": str,
                "confidence": float,
            }
        """
        logger.info(f"润色内容：{len(content)} 字符，风格：{style}")

        if DEERFLOW_AVAILABLE and self._agent_runtime:
            result = await self._call_llm_with_retry(
                prompt=self._build_polish_prompt(content, style),
                user_id=user_id
            )
        else:
            result = self._mock_polish(content, style)

        return {
            "original": content,
            "polished": result["content"],
            "assist_type": AIAssistType.POLISH,
            "ai_badge": AI_ASSIST_BADGES[AIAssistType.POLISH],
            "style": style,
            "confidence": result.get("confidence", 0.8),
            "changes": result.get("changes", []),
        }

    async def expand_content(
        self,
        content: str,
        direction: str = "detail",
        target_length: int = None,
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        扩写内容

        Args:
            content: 原始内容
            direction: 扩写方向（detail 增加细节，example 添加例子，explain 增加解释）
            target_length: 目标长度
            user_id: 用户 ID

        Returns:
            {
                "original": str,
                "expanded": str,
                "assist_type": str,
                "ai_badge": str,
                "expansion_ratio": float,
            }
        """
        logger.info(f"扩写内容：{len(content)} 字符，方向：{direction}")

        if DEERFLOW_AVAILABLE and self._agent_runtime:
            result = await self._call_llm_with_retry(
                prompt=self._build_expand_prompt(content, direction, target_length),
                user_id=user_id
            )
        else:
            result = self._mock_expand(content, direction)

        expanded = result["content"]
        return {
            "original": content,
            "expanded": expanded,
            "assist_type": AIAssistType.EXPAND,
            "ai_badge": AI_ASSIST_BADGES[AIAssistType.EXPAND],
            "direction": direction,
            "expansion_ratio": round(len(expanded) / len(content), 2) if content else 0,
        }

    async def translate_content(
        self,
        content: str,
        target_lang: str = "en",
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        翻译内容

        Args:
            content: 原始内容
            target_lang: 目标语言
            user_id: 用户 ID

        Returns:
            {
                "original": str,
                "translated": str,
                "assist_type": str,
                "ai_badge": str,
                "source_lang": str,
                "target_lang": str,
            }
        """
        logger.info(f"翻译内容：{len(content)} 字符，目标语言：{target_lang}")

        if DEERFLOW_AVAILABLE and self._agent_runtime:
            result = await self._call_llm_with_retry(
                prompt=self._build_translate_prompt(content, target_lang),
                user_id=user_id
            )
        else:
            result = self._mock_translate(content, target_lang)

        return {
            "original": content,
            "translated": result["content"],
            "assist_type": AIAssistType.TRANSLATE,
            "ai_badge": AI_ASSIST_BADGES[AIAssistType.TRANSLATE],
            "source_lang": result.get("source_lang", "zh"),
            "target_lang": target_lang,
        }

    async def summarize_content(
        self,
        content: str,
        max_length: int = 200,
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        摘要内容

        Args:
            content: 原始内容
            max_length: 最大长度
            user_id: 用户 ID

        Returns:
            {
                "original": str,
                "summary": str,
                "assist_type": str,
                "ai_badge": str,
                "compression_ratio": float,
            }
        """
        logger.info(f"摘要内容：{len(content)} 字符，最大长度：{max_length}")

        if DEERFLOW_AVAILABLE and self._agent_runtime:
            result = await self._call_llm_with_retry(
                prompt=self._build_summarize_prompt(content, max_length),
                user_id=user_id
            )
        else:
            result = self._mock_summarize(content, max_length)

        summary = result["content"]
        return {
            "original": content,
            "summary": summary,
            "assist_type": AIAssistType.SUMMARIZE,
            "ai_badge": AI_ASSIST_BADGES[AIAssistType.SUMMARIZE],
            "compression_ratio": round(len(summary) / len(content), 2) if content else 0,
        }

    async def generate_content(
        self,
        topic: str,
        style: str = "normal",
        length: str = "medium",
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        AI 生成内容

        Args:
            topic: 主题
            style: 风格
            length: 长度（short, medium, long）
            user_id: 用户 ID

        Returns:
            {
                "content": str,
                "assist_type": str,
                "ai_badge": str,
                "topic": str,
                "style": str,
            }
        """
        logger.info(f"AI 生成内容：主题 {topic}，风格 {style}，长度 {length}")

        if DEERFLOW_AVAILABLE and self._agent_runtime:
            result = await self._call_llm_with_retry(
                prompt=self._build_generate_prompt(topic, style, length),
                user_id=user_id
            )
        else:
            result = self._mock_generate(topic, style, length)

        return {
            "content": result["content"],
            "assist_type": AIAssistType.GENERATE,
            "ai_badge": AI_ASSIST_BADGES[AIAssistType.GENERATE],
            "topic": topic,
            "style": style,
            "length": length,
        }

    async def get_writing_suggestions(
        self,
        content: str,
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        获取写作建议

        Args:
            content: 内容
            user_id: 用户 ID

        Returns:
            {
                "suggestions": List[Dict],
                "assist_type": str,
                "ai_badge": str,
            }
        """
        logger.info(f"获取写作建议：{len(content)} 字符")

        if DEERFLOW_AVAILABLE and self._agent_runtime:
            result = await self._call_llm_with_retry(
                prompt=self._build_suggest_prompt(content),
                user_id=user_id
            )
        else:
            result = self._mock_suggest(content)

        return {
            "suggestions": result["suggestions"],
            "assist_type": AIAssistType.SUGGEST,
            "ai_badge": AI_ASSIST_BADGES[AIAssistType.SUGGEST],
        }

    async def _call_llm_with_retry(
        self,
        prompt: str,
        user_id: str = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """调用 LLM（带重试）"""
        last_error = None

        for attempt in range(max_retries):
            try:
                # 使用 DeerFlow 2.0 调用
                # 这里是简化的调用示例，实际需要根据 DeerFlow API 调整
                response = await self._call_deerflow(prompt, user_id)

                self._call_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "prompt_length": len(prompt),
                    "success": True,
                })

                return response
            except Exception as e:
                last_error = e
                logger.warning(f"LLM 调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")

        # 所有重试失败，返回降级结果
        logger.error(f"LLM 调用失败：{last_error}")
        return {
            "content": prompt,  # 返回原始内容作为降级
            "confidence": 0.0,
            "error": str(last_error)
        }

    async def _call_deerflow(self, prompt: str, user_id: str = None) -> Dict[str, Any]:
        """调用 DeerFlow 2.0 Agent"""
        if not self._agent_runtime:
            raise RuntimeError("DeerFlow Agent 未初始化")

        # 构建 Agent 调用上下文
        context = ToolContext(
            agent_name="ai_assist",
            user_id=user_id,
            input_data={"prompt": prompt}
        )

        # 调用 Agent（这里是简化示例）
        # 实际使用需要参考 DeerFlow 2.0 的具体 API
        response = await self._agent_runtime.execute(
            prompt=prompt,
            context=context
        )

        return {
            "content": response.get("content", ""),
            "confidence": response.get("confidence", 0.8),
            "model": response.get("model", "unknown"),
        }

    # ==================== 占位实现（用于无 LLM 环境）====================

    def _build_polish_prompt(self, content: str, style: str) -> str:
        """构建润色 prompt"""
        style_descriptions = {
            "formal": "正式、专业",
            "casual": "轻松、口语化",
            "academic": "学术、严谨",
            "creative": "创意、生动"
        }
        return f"请将以下内容润色为{style_descriptions.get(style, '更流畅')}的风格：\n\n{content}"

    def _mock_polish(self, content: str, style: str) -> Dict[str, Any]:
        """占位润色实现"""
        # 简单的润色模拟：添加风格标记
        polished = f"[{style} 风格润色] {content}"
        return {
            "content": polished,
            "confidence": 0.7,
            "changes": ["风格调整", "语句优化"]
        }

    def _build_expand_prompt(self, content: str, direction: str, target_length: int = None) -> str:
        """构建扩写 prompt"""
        direction_descriptions = {
            "detail": "增加更多细节",
            "example": "添加具体例子",
            "explain": "增加解释说明"
        }
        length_hint = f"，目标长度约{target_length}字" if target_length else ""
        return f"请{direction_descriptions.get(direction, '扩展')}以下内容{length_hint}：\n\n{content}"

    def _mock_expand(self, content: str, direction: str) -> Dict[str, Any]:
        """占位扩写实现"""
        expansions = {
            "detail": " [详细内容扩展：添加更多背景信息和细节描述]",
            "example": " [举例说明：例如...]",
            "explain": " [补充解释：这意味着...]"
        }
        expanded = content + expansions.get(direction, " [内容扩展]")
        return {
            "content": expanded,
            "confidence": 0.7
        }

    def _build_translate_prompt(self, content: str, target_lang: str) -> str:
        """构建翻译 prompt"""
        lang_name = TRANSLATION_LANGUAGES.get(target_lang, target_lang)
        return f"请将以下内容翻译为{lang_name}：\n\n{content}"

    def _mock_translate(self, content: str, target_lang: str) -> Dict[str, Any]:
        """占位翻译实现"""
        # 简单模拟：返回带标记的原文
        return {
            "content": f"[{target_lang} 翻译] {content}",
            "source_lang": "zh",
            "confidence": 0.5
        }

    def _build_summarize_prompt(self, content: str, max_length: int) -> str:
        """构建摘要 prompt"""
        return f"请将以下内容摘要为{max_length}字以内的概述：\n\n{content}"

    def _mock_summarize(self, content: str, max_length: int) -> Dict[str, Any]:
        """占位摘要实现"""
        # 简单截取前 max_length 个字
        summary = content[:max_length] + "..." if len(content) > max_length else content
        return {
            "content": summary,
            "confidence": 0.6
        }

    def _build_generate_prompt(self, topic: str, style: str, length: str) -> str:
        """构建生成 prompt"""
        return f"请围绕'{topic}'主题，以{style}风格写一篇{length}长度的内容"

    def _mock_generate(self, topic: str, style: str, length: str) -> Dict[str, Any]:
        """占位生成实现"""
        content = f"[AI 生成内容]\n\n主题：{topic}\n风格：{style}\n\n关于{topic}，这是一个 AI 生成的示例内容。"
        return {
            "content": content,
            "confidence": 0.6
        }

    def _build_suggest_prompt(self, content: str) -> str:
        """构建建议 prompt"""
        return f"请对以下内容提供写作建议和改进意见：\n\n{content}"

    def _mock_suggest(self, content: str) -> Dict[str, Any]:
        """占位建议实现"""
        suggestions = [
            {"type": "structure", "suggestion": "可以考虑增加开头引入"},
            {"type": "clarity", "suggestion": "部分语句可以更简洁"},
            {"type": "engagement", "suggestion": "可以添加一些互动性问题"}
        ]
        return {
            "suggestions": suggestions,
            "confidence": 0.5
        }

    def get_assist_history(self, user_id: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """获取辅助历史"""
        history = self._call_history
        if user_id:
            # 如果有用户标识，可以过滤
            pass
        return list(reversed(history[-limit:]))


# 全局服务实例
_ai_assist_service: Optional[AIAssistService] = None


def get_ai_assist_service(db: AsyncSession) -> AIAssistService:
    """获取 AI 辅助服务实例"""
    global _ai_assist_service
    if _ai_assist_service is None or _ai_assist_service.db is not db:
        _ai_assist_service = AIAssistService(db)
    return _ai_assist_service
