"""
情境感知检测 Skill

DigitalTwin 功能：检测当前对话情境，识别沉默、冲突、深度交流等状态
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from agent.skills.base import BaseSkill
from utils.logger import logger


class ContextDetectorSkill:
    """
    情境感知检测 Skill

    核心能力:
    - 沉默检测与分级
    - 冲突情绪识别
    - 关系阶段感知
    - 对话深度评估
    - 情境类型分类

    自主触发条件:
    - 对话进行中实时监控
    - 沉默超过阈值时
    - 检测到情绪波动时
    """

    name = "context_detector"
    version = "1.0.0"
    description = """
    情境感知检测专家

    能力:
    - 沉默检测 (30s/60s/120s 分级)
    - 冲突情绪识别
    - 关系阶段感知
    - 对话深度评估
    - 8 种情境类型分类
    """

    def get_input_schema(self) -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "conversation_id": {
                    "type": "string",
                    "description": "对话 ID"
                },
                "user_id": {
                    "type": "string",
                    "description": "用户 ID"
                },
                "partner_id": {
                    "type": "string",
                    "description": "对方 ID"
                },
                "silence_duration": {
                    "type": "integer",
                    "description": "沉默时长 (秒)"
                },
                "recent_messages": {
                    "type": "array",
                    "description": "最近消息列表"
                },
                "check_type": {
                    "type": "string",
                    "enum": ["full", "silence", "conflict", "depth"],
                    "description": "检测类型"
                }
            },
            "required": ["conversation_id", "user_id"]
        }

    def get_output_schema(self) -> dict:
        """获取输出 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "context_type": {"type": "string"},
                "context_name": {"type": "string"},
                "confidence": {"type": "number"},
                "indicators": {"type": "object"},
                "suggested_actions": {"type": "array"}
            }
        }

    async def execute(
        self,
        conversation_id: str,
        user_id: str,
        partner_id: Optional[str] = None,
        silence_duration: int = 0,
        recent_messages: Optional[List[Dict]] = None,
        check_type: str = "full",
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行情境检测

        Args:
            conversation_id: 对话 ID
            user_id: 用户 ID
            partner_id: 对方 ID
            silence_duration: 沉默时长
            recent_messages: 最近消息
            check_type: 检测类型

        Returns:
            检测结果
        """
        logger.info(f"ContextDetector: Detecting context for conv={conversation_id}")

        try:
            # 收集情境指标
            indicators = self._collect_indicators(
                conversation_id, user_id, partner_id,
                silence_duration, recent_messages
            )

            # 检测情境类型
            if check_type == "silence":
                context_type = self._detect_silence_context(silence_duration)
            elif check_type == "conflict":
                context_type = self._detect_conflict_context(recent_messages)
            elif check_type == "depth":
                context_type = self._detect_depth_context(recent_messages)
            else:  # full
                context_type = self._detect_full_context(indicators)

            # 获取情境信息
            context_info = self._get_context_info(context_type)

            # 生成建议行动
            suggested_actions = self._generate_suggested_actions(context_type, indicators)

            # 构建响应
            return self._build_response(
                context_type, context_info, indicators, suggested_actions
            )

        except Exception as e:
            logger.error(f"ContextDetector execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "ai_message": "情境检测失败，请稍后再试"
            }

    def _collect_indicators(
        self,
        conversation_id: str,
        user_id: str,
        partner_id: Optional[str],
        silence_duration: int,
        recent_messages: Optional[List[Dict]]
    ) -> Dict:
        """收集情境指标"""
        indicators = {
            "silence_duration": silence_duration,
            "message_count": len(recent_messages) if recent_messages else 0,
            "conflict_detected": False,
            "depth_score": 0.5,
            "mood": "neutral",
            "energy_level": "medium",
        }

        # 分析最近消息
        if recent_messages:
            # 检测冲突
            conflict_keywords = ["生气", "吵架", "矛盾", "不满", "为什么", "总是", "从不"]
            for msg in recent_messages:
                content = msg.get("content", "")
                if any(kw in content for kw in conflict_keywords):
                    indicators["conflict_detected"] = True
                    break

            # 评估对话深度
            depth_keywords = ["未来", "期待", "感受", "想法", "重要", "希望", "梦想"]
            depth_count = sum(
                1 for msg in recent_messages
                if any(kw in msg.get("content", "") for kw in depth_keywords)
            )
            indicators["depth_score"] = min(1.0, depth_count / max(1, len(recent_messages)))

        # 获取关系阶段
        indicators["relationship_stage"] = self._get_relationship_stage(user_id, partner_id)

        return indicators

    def _detect_silence_context(self, silence_duration: int) -> str:
        """检测沉默情境"""
        if silence_duration >= 120:
            return "silence_critical"
        elif silence_duration >= 60:
            return "silence_awkward"
        elif silence_duration >= 30:
            return "silence_mild"
        else:
            return "normal"

    def _detect_conflict_context(self, recent_messages: Optional[List[Dict]]) -> str:
        """检测冲突情境"""
        if not recent_messages:
            return "normal"

        # 检测激烈言辞
        conflict_indicators = 0
        negative_keywords = ["讨厌", "烦", "够了", "分手", "离开", "错误", "问题"]

        for msg in recent_messages:
            content = msg.get("content", "")
            if any(kw in content for kw in negative_keywords):
                conflict_indicators += 1

        if conflict_indicators >= 3:
            return "conflict_severe"
        elif conflict_indicators >= 1:
            return "conflict_mild"
        else:
            return "normal"

    def _detect_depth_context(self, recent_messages: Optional[List[Dict]]) -> str:
        """检测深度交流情境"""
        if not recent_messages:
            return "normal"

        depth_keywords = ["内心", "感受", "价值观", "未来规划", "家庭", "梦想", "期待"]
        depth_count = sum(
            1 for msg in recent_messages
            if len(msg.get("content", "")) > 50  # 长消息
            and any(kw in msg.get("content", "") for kw in depth_keywords)
        )

        if depth_count >= 3:
            return "deep_conversation"
        elif depth_count >= 1:
            return "moderate_conversation"
        else:
            return "casual_chat"

    def _detect_full_context(self, indicators: Dict) -> str:
        """综合检测情境"""
        # 优先级：冲突 > 沉默 > 深度 > 正常

        if indicators.get("conflict_detected"):
            return "conflict"

        silence = indicators.get("silence_duration", 0)
        if silence >= 60:
            return "silence"

        if indicators.get("depth_score", 0) >= 0.7:
            return "deep_conversation"

        # 关系阶段判断
        stage = indicators.get("relationship_stage", "initial")
        if stage == "initial":
            return "first_contact"

        return "normal"

    def _get_context_info(self, context_type: str) -> Dict:
        """获取情境信息"""
        context_info = {
            "silence": {
                "name": "沉默尴尬",
                "description": "对话出现沉默，可能需要打破僵局",
                "urgency": "medium",
            },
            "silence_mild": {
                "name": "轻微沉默",
                "description": "短暂沉默，属于正常范围",
                "urgency": "low",
            },
            "silence_awkward": {
                "name": "尴尬沉默",
                "description": "沉默时间较长，可能感到尴尬",
                "urgency": "medium",
            },
            "silence_critical": {
                "name": "危险沉默",
                "description": "长时间沉默，需要立即干预",
                "urgency": "high",
            },
            "conflict": {
                "name": "观点冲突",
                "description": "检测到观点或情绪冲突",
                "urgency": "high",
            },
            "conflict_mild": {
                "name": "轻微分歧",
                "description": "存在轻微意见不合",
                "urgency": "low",
            },
            "conflict_severe": {
                "name": "激烈冲突",
                "description": "检测到激烈言辞或情绪",
                "urgency": "critical",
            },
            "deep_conversation": {
                "name": "深度交流",
                "description": "正在进行深入的话题讨论",
                "urgency": "low",
            },
            "first_contact": {
                "name": "首次接触",
                "description": "双方刚开始认识",
                "urgency": "medium",
            },
            "normal": {
                "name": "正常对话",
                "description": "对话正常进行中",
                "urgency": "none",
            },
        }

        return context_info.get(context_type, {
            "name": "未知",
            "description": "无法识别情境",
            "urgency": "none",
        })

    def _generate_suggested_actions(
        self,
        context_type: str,
        indicators: Dict
    ) -> List[Dict]:
        """生成建议行动"""
        actions = []

        if context_type in ["silence", "silence_awkward", "silence_critical"]:
            actions.append({
                "type": "icebreaker",
                "priority": "high",
                "message": "推荐破冰话题或游戏",
                "action": "suggest_icebreaker",
            })

        if context_type in ["conflict", "conflict_severe"]:
            actions.append({
                "type": "mediation",
                "priority": "high",
                "message": "AI 介入调解，缓和气氛",
                "action": "mediate_conflict",
            })

        if context_type == "deep_conversation":
            actions.append({
                "type": "support",
                "priority": "low",
                "message": "提供深度话题支持",
                "action": "support_deep_talk",
            })

        if context_type == "first_contact":
            actions.append({
                "type": "guidance",
                "priority": "medium",
                "message": "提供开场白建议",
                "action": "suggest_opening",
            })

        return actions

    def _build_response(
        self,
        context_type: str,
        context_info: Dict,
        indicators: Dict,
        suggested_actions: List[Dict]
    ) -> Dict[str, Any]:
        """构建响应"""
        ai_message = self._generate_ai_message(context_type, context_info, indicators)

        return {
            "success": True,
            "data": {
                "context_type": context_type,
                "context_name": context_info.get("name", "未知"),
                "context_description": context_info.get("description", ""),
                "urgency": context_info.get("urgency", "none"),
                "indicators": indicators,
                "suggested_actions": suggested_actions,
            },
            "ai_message": ai_message,
        }

    def _generate_ai_message(
        self,
        context_type: str,
        context_info: Dict,
        indicators: Dict
    ) -> str:
        """生成 AI 消息"""
        context_name = context_info.get("name", "未知情境")
        description = context_info.get("description", "")

        return f"检测到当前情境：{context_name}。\n{description}"

    def _get_relationship_stage(
        self,
        user_id: str,
        partner_id: Optional[str]
    ) -> str:
        """获取关系阶段"""
        if not partner_id:
            return "initial"

        from utils.db_session_manager import db_session
        from db.models import MatchHistoryDB

        with db_session() as db:
            match = db.query(MatchHistoryDB).filter(
                ((MatchHistoryDB.user_a_id == user_id) & (MatchHistoryDB.user_b_id == partner_id)) |
                ((MatchHistoryDB.user_a_id == partner_id) & (MatchHistoryDB.user_b_id == user_id))
            ).first()

            if match:
                return match.match_status or "initial"
            return "initial"


# 全局单例获取函数
_skill_instance: Optional[ContextDetectorSkill] = None


def get_context_detector_skill() -> ContextDetectorSkill:
    """获取情境感知检测 Skill 实例"""
    global _skill_instance
    if _skill_instance is None:
        _skill_instance = ContextDetectorSkill()
    return _skill_instance
