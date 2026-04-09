"""
AI 预沟通 Skill

AI 替身预沟通服务 - 替用户先聊 50 句
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from agent.skills.base import BaseSkill
from utils.logger import logger


class PreCommunicationAgentSkill:
    """
    AI 替身预沟通 Skill

    核心能力:
    - 启动 AI 替身对话
    - 监控对话进度（每 10 句总结）
    - 提取关键信息（定居计划/宠物态度/婚姻观念）
    - 生成匹配报告
    - 建议是否开启人工对话

    自主触发条件:
    - 新匹配产生且双方资料完整度 > 80%
    - 基础条件匹配度 > 0.75
    - 用户长时间未主动发起对话（> 48 小时）
    """

    name = "pre_communication"
    version = "2.0.0"
    description = """
    AI 替身预沟通服务

    能力:
    - 启动 AI 替身对话
    - 监控对话进度
    - 提取关键信息（定居计划/宠物态度等）
    - 生成匹配报告
    - 建议是否开启人工对话
    """

    def get_input_schema(self) -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "match_id": {
                    "type": "string",
                    "description": "匹配记录 ID"
                },
                "user_id": {
                    "type": "string",
                    "description": "用户 ID"
                },
                "action": {
                    "type": "string",
                    "enum": ["start", "check_status", "get_report", "cancel"],
                    "description": "操作类型"
                },
                "preferences": {
                    "type": "object",
                    "properties": {
                        "conversation_style": {
                            "type": "string",
                            "enum": ["friendly", "direct", "humorous"]
                        },
                        "key_topics": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                }
            },
            "required": ["match_id", "action"]
        }

    def get_output_schema(self) -> dict:
        """获取输出参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "session_id": {"type": "string"},
                "status": {"type": "string"},
                "ai_message": {"type": "string"},
                "progress": {
                    "type": "object",
                    "properties": {
                        "message_count": {"type": "integer"},
                        "completion_percentage": {"type": "number"},
                        "key_insights": {"type": "array"}
                    }
                },
                "match_report": {"type": "object"},
                "recommendation": {
                    "type": "string",
                    "enum": ["proceed_to_chat", "not_recommended", "need_more_time"]
                }
            }
        }

    async def execute(
        self,
        match_id: str,
        action: str,
        user_id: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> dict:
        """
        执行 AI 预沟通 Skill

        Args:
            match_id: 匹配记录 ID
            action: 操作类型 (start/check_status/get_report/cancel)
            user_id: 用户 ID
            preferences: 偏好设置
            **kwargs: 额外参数

        Returns:
            Skill 执行结果
        """
        logger.info(f"PreCommunicationAgentSkill: action={action}, match_id={match_id}")

        if action == "start":
            return await self._start_session(match_id, user_id, preferences)
        elif action == "check_status":
            return await self._check_status(match_id)
        elif action == "get_report":
            return await self._generate_report(match_id)
        elif action == "cancel":
            return await self._cancel_session(match_id)
        else:
            return {"success": False, "error": "Invalid action", "ai_message": "不支持的操作类型"}

    async def _start_session(self, match_id: str, user_id: str, preferences: dict = None) -> dict:
        """启动 AI 预沟通会话"""
        # Step 1: 获取匹配信息
        match_info = self._get_match_info(match_id)
        if not match_info:
            return {"success": False, "error": "Match not found", "ai_message": "未找到匹配记录"}

        # Step 2: 检查是否适合启动预沟通
        suitability = self._should_start_precomm(match_info)
        if not suitability["suitable"]:
            return {
                "success": False,
                "reason": suitability["reason"],
                "ai_message": suitability["message"]
            }

        # Step 3: 创建会话
        session_id = await self._create_session(match_id, user_id, preferences)

        # Step 4: 启动 AI 对话
        dialog_result = await self._start_ai_dialog(session_id, match_info, preferences)

        return {
            "success": True,
            "session_id": session_id,
            "status": "in_progress",
            "ai_message": "AI 替身已启动，正在与对方进行预沟通。预计需要 50 句对话，完成后会生成详细报告~",
            "progress": {
                "message_count": 0,
                "completion_percentage": 0,
                "estimated_completion": "约 30 分钟",
                "key_insights": []
            }
        }

    async def _check_status(self, match_id: str) -> dict:
        """检查预沟通进度"""
        session = self._get_session(match_id)
        if not session:
            return {
                "success": False,
                "error": "Session not found",
                "ai_message": "未找到预沟通会话"
            }

        progress = session.get("progress", {})
        status = session.get("status", "unknown")

        return {
            "success": True,
            "session_id": session.get("id"),
            "status": status,
            "ai_message": self._generate_status_message(progress),
            "progress": progress
        }

    async def _generate_report(self, match_id: str) -> dict:
        """生成匹配报告"""
        session = self._get_session(match_id)
        if not session:
            return {
                "success": False,
                "error": "Session not found",
                "ai_message": "未找到预沟通会话"
            }

        if session.get("status") != "completed":
            return {
                "success": False,
                "error": "Session not completed",
                "ai_message": f"预沟通尚未完成，当前进度：{session.get('progress', {}).get('completion_percentage', 0):.0f}%"
            }

        # 分析对话内容
        dialog_analysis = await self._analyze_dialog(session.get("messages", []))

        # 提取关键信息
        key_insights = self._extract_insights(dialog_analysis)

        # 生成建议
        recommendation = self._generate_recommendation(dialog_analysis, key_insights)

        return {
            "success": True,
            "session_id": session.get("id"),
            "status": "completed",
            "match_report": {
                "compatibility_score": dialog_analysis.get("compatibility_score", 0),
                "key_insights": key_insights,
                "conversation_highlights": dialog_analysis.get("highlights", []),
                "potential_concerns": dialog_analysis.get("concerns", []),
                "communication_style_match": dialog_analysis.get("style_match", "unknown")
            },
            "recommendation": recommendation,
            "ai_message": self._generate_report_message(key_insights, recommendation)
        }

    async def _cancel_session(self, match_id: str) -> dict:
        """取消预沟通会话"""
        session = self._get_session(match_id)
        if not session:
            return {
                "success": False,
                "error": "Session not found",
                "ai_message": "未找到预沟通会话"
            }

        # 取消会话
        await self._cancel_ai_dialog(session.get("id"))

        return {
            "success": True,
            "session_id": session.get("id"),
            "status": "cancelled",
            "ai_message": "已取消 AI 预沟通，你可以随时重新开始"
        }

    def _get_match_info(self, match_id: str) -> Optional[dict]:
        """获取匹配信息"""
        # 注：当前使用模拟数据，待对接数据库
        logger.info(f"PreCommunicationAgentSkill: Getting match info for {match_id}")
        # 这里使用模拟数据
        return {
            "id": match_id,
            "user_id_1": "user-1",
            "user_id_2": "user-2",
            "user_a_profile_completeness": 0.85,
            "user_b_profile_completeness": 0.90,
            "base_score": 0.78,
            "common_interests": ["旅行", "美食"]
        }

    def _should_start_precomm(self, match_info: dict) -> dict:
        """判断是否适合启动预沟通"""
        # 资料完整度检查
        profile_completeness = (
            match_info.get("user_a_profile_completeness", 0) +
            match_info.get("user_b_profile_completeness", 0)
        ) / 2

        if profile_completeness < 0.8:
            return {
                "suitable": False,
                "reason": "low_profile_completeness",
                "message": "当前匹配的资料完整度不高，建议先完善资料再进行 AI 预沟通~"
            }

        # 基础匹配度检查
        if match_info.get("base_score", 0) < 0.75:
            return {
                "suitable": False,
                "reason": "low_base_score",
                "message": "基础匹配度一般，建议先多了解一下对方~"
            }

        # 检查是否已有进行中的会话
        # 注：当前跳过数据库检查，待对接数据库服务
        logger.info(f"PreCommunicationAgentSkill: Checking for existing sessions (mock)")

        return {"suitable": True}

    async def _create_session(self, match_id: str, user_id: str, preferences: dict = None) -> str:
        """创建预沟通会话"""
        session_id = f"precomm-{match_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 注：当前仅记录日志，待对接数据库
        logger.info(f"PreCommunicationAgentSkill: Created session {session_id}")

        return session_id

    async def _start_ai_dialog(self, session_id: str, match_info: dict, preferences: dict = None) -> dict:
        """启动 AI 对话（调用 P18 AI Interlocutor API）"""
        # 注：当前仅记录日志，待对接 AI Interlocutor 服务
        logger.info(f"PreCommunicationAgentSkill: Starting AI dialog for session {session_id}")

        return {
            "session_id": session_id,
            "status": "started",
            "dialog_config": {
                "style": preferences.get("conversation_style", "friendly") if preferences else "friendly",
                "key_topics": preferences.get("key_topics", []) if preferences else []
            }
        }

    async def _cancel_ai_dialog(self, session_id: str) -> dict:
        """取消 AI 对话"""
        # 注：当前仅记录日志，待对接 API
        logger.info(f"PreCommunicationAgentSkill: Cancelling dialog for session {session_id}")
        return {"status": "cancelled"}

    def _get_session(self, match_id: str) -> Optional[dict]:
        """获取会话信息"""
        # 注：当前使用模拟数据，待对接数据库
        logger.info(f"PreCommunicationAgentSkill: Getting session for match={match_id}")
        # 模拟数据
        return {
            "id": f"precomm-{match_id}",
            "status": "in_progress",
            "progress": {
                "message_count": 25,
                "completion_percentage": 50,
                "key_insights": []
            },
            "messages": []
        }

    def _generate_status_message(self, progress: dict) -> str:
        """生成进度消息"""
        count = progress.get("message_count", 0)
        percentage = progress.get("completion_percentage", 0)

        if percentage <= 0:
            return "AI 对话即将开始，请耐心等待~"
        elif percentage < 30:
            return f"AI 对话正在进行中，已完成{percentage:.0f}% ({count}/50 句)。目前进展顺利~"
        elif percentage < 70:
            return f"进度过半！已完成{percentage:.0f}% ({count}/50 句)。AI 发现了一些有趣的共同点~"
        elif percentage < 100:
            return f"即将完成！已完成{percentage:.0f}% ({count}/50 句)。报告正在生成中..."
        else:
            return "AI 预沟通已完成，详细报告已生成！"

    async def _analyze_dialog(self, messages: list) -> dict:
        """分析对话内容"""
        # 注：当前使用模拟分析，待对接 LLM 服务
        logger.info(f"PreCommunicationAgentSkill: Analyzing dialog with {len(messages)} messages")
        # 模拟分析结果
        return {
            "compatibility_score": 0.82,
            "highlights": [
                "双方都喜欢旅行，分享了各自的旅行经历",
                "对美食有共同兴趣，讨论了喜欢的菜系",
                "价值观相似，对未来的规划一致"
            ],
            "concerns": [],
            "style_match": "good",
            "key_topics_discussed": ["旅行", "美食", "工作", "家庭"]
        }

    def _extract_insights(self, dialog_analysis: dict) -> list:
        """提取关键信息"""
        insights = []

        # 从对话亮点中提取
        for highlight in dialog_analysis.get("highlights", []):
            insights.append({
                "type": "common_interest",
                "content": highlight,
                "confidence": 0.8
            })

        # 注：更深层的洞察提取待实现，如：
        # - 定居计划
        # - 宠物态度
        # - 婚姻观念
        # - 生育计划

        return insights

    def _generate_recommendation(self, dialog_analysis: dict, insights: list) -> str:
        """生成是否继续的建议"""
        compatibility = dialog_analysis.get("compatibility_score", 0.5)
        concerns_count = len(dialog_analysis.get("concerns", []))

        if compatibility >= 0.8 and concerns_count == 0:
            return "proceed_to_chat"
        elif compatibility >= 0.6 and concerns_count <= 1:
            return "proceed_to_chat"
        elif compatibility < 0.5 or concerns_count >= 2:
            return "not_recommended"
        else:
            return "need_more_time"

    def _generate_report_message(self, key_insights: list, recommendation: str) -> str:
        """生成报告消息"""
        recommendation_messages = {
            "proceed_to_chat": "AI 预沟通结果显示你们很契合！建议开启人工对话，进一步深入了解~",
            "not_recommended": "AI 分析发现你们在一些重要方面存在差异，建议慎重考虑是否继续",
            "need_more_time": "AI 还需要更多对话来进行准确判断，建议延长预沟通时间"
        }

        message = "AI 预沟通报告已完成！\n\n"
        message += f"匹配度评分：{len(key_insights)} 个关键发现\n"

        if key_insights:
            message += "\n关键发现：\n"
            for i, insight in enumerate(key_insights[:3], 1):
                message += f"{i}. {insight.get('content', '')}\n"

        message += f"\nAI 建议：{recommendation_messages.get(recommendation, '')}"

        return message

    async def autonomous_trigger(self, user_id: str) -> dict:
        """
        自主检测并启动预沟通

        Args:
            user_id: 用户 ID

        Returns:
            触发结果
        """
        logger.info(f"PreCommunicationAgentSkill: Autonomous trigger for {user_id}")

        # 查找适合的新匹配
        suitable_matches = self._find_suitable_matches_for_precomm(user_id)

        if not suitable_matches:
            return {"triggered": False, "reason": "no_suitable_matches"}

        # 自动启动预沟通
        for match in suitable_matches[:1]:  # 只启动一个
            result = await self.execute(
                match_id=match.get("id"),
                action="start",
                user_id=user_id
            )

            if result.get("success"):
                return {
                    "triggered": True,
                    "result": result,
                    "should_push": True,
                    "push_message": f"AI 已自动为你与{match.get('user_name')}启动预沟通~"
                }

        return {"triggered": False, "reason": "failed_to_start"}

    def _find_suitable_matches_for_precomm(self, user_id: str) -> list:
        """查找适合预沟通的匹配"""
        # 注：当前返回空列表，待对接数据库查询服务
        # 条件：
        # 1. 新匹配（< 24 小时）
        # 2. 双方资料完整度 > 80%
        # 3. 基础匹配度 > 0.75
        # 4. 用户未主动发起对话（> 48 小时）
        logger.info(f"PreCommunicationAgentSkill: Finding suitable matches for precomm for user={user_id}")
        return []


# 全局 Skill 实例
_precommunication_skill_instance: Optional[PreCommunicationAgentSkill] = None


def get_precommunication_skill() -> PreCommunicationAgentSkill:
    """获取 AI 预沟通 Skill 单例实例"""
    global _precommunication_skill_instance
    if _precommunication_skill_instance is None:
        _precommunication_skill_instance = PreCommunicationAgentSkill()
    return _precommunication_skill_instance
