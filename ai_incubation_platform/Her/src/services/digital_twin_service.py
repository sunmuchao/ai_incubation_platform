"""
数字分身预聊服务

P2 功能：基于用户数据训练的 AI 代理，模拟用户行为进行预沟通
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
import json
import asyncio

from db.database import SessionLocal
from models.p2_digital_twin_models import (
    DigitalTwinProfile,
    DigitalTwinSimulation,
    DigitalTwinReport,
)
from utils.logger import logger


class DigitalTwinService:
    """数字分身服务"""

    def __init__(self):
        self._db: Optional[Session] = None
        self._should_close_db: bool = False

    def _get_db(self) -> Session:
        """获取数据库会话"""
        if self._db is None:
            self._db = SessionLocal()
            self._should_close_db = True
        return self._db

    def close_db(self):
        """关闭数据库会话（仅关闭自己创建的）"""
        if self._should_close_db and self._db is not None:
            try:
                self._db.commit()
                self._db.close()
            except Exception as e:
                logger.error(f"Error closing database session: {e}")
            finally:
                self._db = None
                self._should_close_db = False

    # ========== 数字分身配置管理 ==========

    def create_twin_profile(
        self,
        user_id: str,
        display_name: str,
        personality_traits: Dict,
        communication_style: str = "medium",
        core_values: List[str] = None,
        interests: List[str] = None,
        deal_breakers: List[str] = None,
        response_patterns: List[str] = None,
        topic_preferences: List[str] = None,
        conversation_starters: List[str] = None,
        simulation_temperature: float = 0.7,
        response_length_preference: str = "medium",
    ) -> Tuple[bool, str, Optional[DigitalTwinProfile]]:
        """
        创建数字分身配置

        Args:
            user_id: 用户 ID
            display_name: 显示名称
            personality_traits: 性格特征（大五人格等）
            communication_style: 沟通风格
            core_values: 核心价值观
            interests: 兴趣爱好
            deal_breakers: 不可接受的行为
            response_patterns: 常见回复模式
            topic_preferences: 喜欢的话题
            conversation_starters: 开场白偏好
            simulation_temperature: AI 创造性 0-1
            response_length_preference: 回复长度偏好

        Returns:
            (success, message, profile)
        """
        try:
            db = self._get_db()

            # 检查是否已存在
            existing = db.query(DigitalTwinProfile).filter(
                DigitalTwinProfile.user_id == user_id,
                DigitalTwinProfile.is_active == True
            ).first()

            if existing:
                # 更新现有配置
                existing.display_name = display_name
                existing.personality_traits = personality_traits or existing.personality_traits
                existing.communication_style = communication_style
                existing.core_values = core_values or existing.core_values
                existing.interests = interests or existing.interests
                existing.deal_breakers = deal_breakers or existing.deal_breakers
                existing.response_patterns = response_patterns or existing.response_patterns
                existing.topic_preferences = topic_preferences or existing.topic_preferences
                existing.conversation_starters = (
                    conversation_starters or existing.conversation_starters
                )
                existing.simulation_temperature = simulation_temperature
                existing.response_length_preference = response_length_preference

                db.commit()
                db.refresh(existing)
                logger.info(f"Updated digital twin profile for user {user_id}")
                return True, "数字分身配置已更新", existing
            else:
                # 创建新配置
                profile = DigitalTwinProfile(
                    user_id=user_id,
                    display_name=display_name,
                    personality_traits=personality_traits or {},
                    communication_style=communication_style,
                    core_values=core_values or [],
                    interests=interests or [],
                    deal_breakers=deal_breakers or [],
                    response_patterns=response_patterns or [],
                    topic_preferences=topic_preferences or [],
                    conversation_starters=conversation_starters or [],
                    simulation_temperature=simulation_temperature,
                    response_length_preference=response_length_preference,
                )
                db.add(profile)
                db.commit()
                db.refresh(profile)
                logger.info(f"Created digital twin profile for user {user_id}")
                return True, "数字分身配置已创建", profile

        except Exception as e:
            logger.error(f"Failed to create twin profile: {e}")
            return False, str(e), None

    def get_twin_profile(self, user_id: str) -> Optional[DigitalTwinProfile]:
        """获取用户的数字分身配置"""
        db = self._get_db()
        return db.query(DigitalTwinProfile).filter(
            DigitalTwinProfile.user_id == user_id,
            DigitalTwinProfile.is_active == True
        ).first()

    def update_twin_profile(
        self,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """更新数字分身配置"""
        try:
            db = self._get_db()
            profile = self.get_twin_profile(user_id)

            if not profile:
                return False, "未找到数字分身配置"

            for key, value in updates.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)

            db.commit()
            logger.info(f"Updated twin profile for user {user_id}")
            return True, "配置已更新"

        except Exception as e:
            logger.error(f"Failed to update twin profile: {e}")
            return False, str(e)

    # ========== 模拟会话管理 ==========

    def start_simulation(
        self,
        user_a_id: str,
        user_b_id: str,
        total_rounds: int = 10,
        simulation_config: Dict = None,
    ) -> Tuple[bool, str, Optional[DigitalTwinSimulation]]:
        """
        启动数字分身模拟

        Args:
            user_a_id: 用户 A ID
            user_b_id: 用户 B ID
            total_rounds: 模拟轮数
            simulation_config: 模拟配置

        Returns:
            (success, message, simulation)
        """
        try:
            db = self._get_db()

            # 获取双方分身配置
            twin_a = self.get_twin_profile(user_a_id)
            twin_b = self.get_twin_profile(user_b_id)

            if not twin_a:
                return False, f"用户 {user_a_id} 的数字分身未配置", None
            if not twin_b:
                return False, f"用户 {user_b_id} 的数字分身未配置", None

            # 创建模拟会话
            simulation = DigitalTwinSimulation(
                user_a_id=user_a_id,
                user_b_id=user_b_id,
                status="running",
                total_rounds=total_rounds,
                completed_rounds=0,
                conversation_log=[],
                simulation_config=simulation_config or {},
                started_at=datetime.now(),
            )

            db.add(simulation)
            db.commit()
            db.refresh(simulation)

            logger.info(
                f"Started digital twin simulation: {user_a_id} vs {user_b_id}"
            )
            return True, "模拟已开始", simulation

        except Exception as e:
            logger.error(f"Failed to start simulation: {e}")
            return False, str(e), None

    async def run_simulation(
        self,
        simulation_id: int,
        callback: Optional[callable] = None,
    ) -> Tuple[bool, str]:
        """
        运行数字分身模拟

        Args:
            simulation_id: 模拟 ID
            callback: 进度回调函数

        Returns:
            (success, message)
        """
        try:
            db = self._get_db()
            simulation = db.query(DigitalTwinSimulation).filter(
                DigitalTwinSimulation.id == simulation_id
            ).first()

            if not simulation:
                return False, "模拟未找到"

            if simulation.status != "running":
                return False, f"模拟状态不正确：{simulation.status}"

            # 获取双方分身配置
            twin_a = self.get_twin_profile(simulation.user_a_id)
            twin_b = self.get_twin_profile(simulation.user_b_id)

            if not twin_a or not twin_b:
                return False, "分身配置不存在"

            # 运行模拟对话
            conversation_log = []
            for round_num in range(1, simulation.total_rounds + 1):
                # 生成对话（调用 LLM）
                if round_num % 2 == 1:
                    # 用户 A 的分身先发言
                    initiator = twin_a
                    responder = twin_b
                    initiator_id = simulation.user_a_id
                    responder_id = simulation.user_b_id
                else:
                    initiator = twin_b
                    responder = twin_a
                    initiator_id = simulation.user_b_id
                    responder_id = simulation.user_a_id

                # 生成回复
                response = await self._generate_response(
                    initiator=initiator,
                    responder=responder,
                    conversation_history=conversation_log,
                    round_num=round_num,
                )

                conversation_log.append({
                    "round": round_num,
                    "speaker_id": initiator_id,
                    "speaker_name": initiator.display_name,
                    "message": response.get("message", ""),
                    "analysis": response.get("analysis", {}),
                    "timestamp": datetime.now().isoformat(),
                })

                # 更新进度
                simulation.completed_rounds = round_num
                simulation.conversation_log = conversation_log
                db.commit()

                if callback:
                    await callback(round_num, response)

            # 模拟完成，生成分析报告
            analysis_result = await self._generate_analysis(
                simulation, conversation_log, twin_a, twin_b
            )

            # 更新模拟结果
            simulation.status = "completed"
            simulation.completed_at = datetime.now()
            simulation.compatibility_score = analysis_result["compatibility_score"]
            simulation.chemistry_score = analysis_result["chemistry_score"]
            simulation.communication_match = analysis_result["communication_match"]
            simulation.values_alignment = analysis_result["values_alignment"]
            simulation.highlights = analysis_result["highlights"]
            simulation.potential_conflicts = analysis_result["potential_conflicts"]
            simulation.conversation_highlights = analysis_result[
                "conversation_highlights"
            ]
            simulation.ai_analysis = analysis_result["ai_analysis"]
            simulation.ai_suggestions = analysis_result["ai_suggestions"]

            db.commit()
            logger.info(f"Completed simulation {simulation_id}")

            return True, "模拟完成"

        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            return False, str(e)

    async def _generate_response(
        self,
        initiator: DigitalTwinProfile,
        responder: DigitalTwinProfile,
        conversation_history: List[Dict],
        round_num: int,
    ) -> Dict[str, Any]:
        """
        生成分身回复

        降级方案：
        - LLM 启用时：调用 LLM 生成自然语言回复
        - LLM 未启用时：使用基于规则的模板回复
        """
        # 尝试使用 LLM 生成回复
        if settings.llm_enabled and settings.llm_api_key:
            try:
                return self._generate_reply_with_llm(
                    initiator, responder, conversation_history, round_num
                )
            except Exception as e:
                logger.warning(f"LLM reply generation failed: {e}, using fallback template")

        # 降级方案：基于规则的模板回复
        return self._generate_reply_fallback(initiator, responder, conversation_history, round_num)

    def _generate_reply_with_llm(
        self,
        initiator: DigitalTwinProfile,
        responder: DigitalTwinProfile,
        conversation_history: List[Dict],
        round_num: int,
    ) -> Dict[str, Any]:
        """使用 LLM 生成分身回复"""
        logger.info(f"Using LLM for digital twin reply (round={round_num})")

        # 构建 prompt
        prompt = self._build_digital_twin_prompt(initiator, responder, conversation_history, round_num)

        # 调用 LLM 客户端
        from integration.llm_client import LLMIntegrationClient
        llm_client = LLMIntegrationClient()

        try:
            import asyncio
            llm_response = asyncio.run(llm_client.generate_chat(prompt))

            # 解析 LLM 响应
            message, analysis = self._parse_llm_response(llm_response)

            return {"message": message, "analysis": analysis}

        except Exception as e:
            logger.warning(f"LLM chat failed: {e}, using fallback")
            raise  # 抛出异常让上层调用降级方案

    def _build_digital_twin_prompt(
        self,
        initiator: DigitalTwinProfile,
        responder: DigitalTwinProfile,
        conversation_history: List[Dict],
        round_num: int,
    ) -> str:
        """构建数字孪生对话 prompt"""
        # 提取用户画像信息
        initiator_info = {
            "name": initiator.user_name,
            "interests": initiator.interests,
            "values": initiator.values,
            "communication_style": initiator.communication_style,
        }
        responder_info = {
            "name": responder.user_name,
            "interests": responder.interests,
            "values": responder.values,
            "communication_style": responder.communication_style,
        }

        # 构建对话历史
        history_text = ""
        for msg in conversation_history[-5:]:  # 只保留最近 5 轮
            history_text += f"{msg['sender']}: {msg['message']}\n"

        prompt = f"""你是一个 AI 数字孪生助手，正在模拟两个用户之间的对话。

## 用户 A 画像
- 名字：{initiator_info['name']}
- 兴趣：{initiator_info['interests']}
- 价值观：{initiator_info['values']}
- 沟通风格：{initiator_info['communication_style']}

## 用户 B 画像
- 名字：{responder_info['name']}
- 兴趣：{responder_info['interests']}
- 价值观：{responder_info['values']}
- 沟通风格：{responder_info['communication_style']}

## 对话历史
{history_text}

## 当前回合
第 {round_num} 轮

请生成用户 B 的回复，要求：
1. 符合用户 B 的沟通风格
2. 延续对话话题
3. 自然、真诚、有吸引力
4. 长度适中（20-50 字）

请以 JSON 格式返回：
{{
    "message": "回复内容",
    "analysis": {{
        "intent": "意图（opening/getting_to_know/deepening/closing）",
        "tone": "语气（friendly/curious/engaged/reflective）",
        "topic": "话题",
        "emotion": "情感（positive/neutral/negative）"
    }}
}}
"""
        return prompt

    def _parse_llm_response(self, llm_response: Dict[str, Any]) -> tuple:
        """解析 LLM 响应"""
        try:
            if isinstance(llm_response, str):
                import json
                llm_response = json.loads(llm_response)

            message = llm_response.get("message", "")
            analysis = llm_response.get("analysis", {"intent": "unknown", "tone": "neutral"})

            return message, analysis

        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return "很有趣的观点！", {"intent": "response", "tone": "engaged"}

    def _generate_reply_fallback(
        self,
        initiator: DigitalTwinProfile,
        responder: DigitalTwinProfile,
        conversation_history: List[Dict],
        round_num: int,
    ) -> Dict[str, Any]:
        """降级方案：基于回合数和预设模板生成分身回复"""
        # 根据回合数和话题生成回复
        if round_num == 1:
            # 第一轮：开场白
            message = self._generate_opening_message(initiator)
            analysis = {"intent": "opening", "tone": "friendly"}
        elif round_num <= 3:
            # 前期：了解基本信息
            message = self._generate_early_message(initiator, conversation_history)
            analysis = {"intent": "getting_to_know", "tone": "curious"}
        elif round_num <= 7:
            # 中期：深入交流
            message = self._generate_deep_message(initiator, conversation_history)
            analysis = {"intent": "deepening", "tone": "engaged"}
        else:
            # 后期：总结或展望
            message = self._generate_closing_message(initiator, conversation_history)
            analysis = {"intent": "closing", "tone": "reflective"}

        return {"message": message, "analysis": analysis}

    def _generate_opening_message(self, profile: DigitalTwinProfile) -> str:
        """生成开场白"""
        # 从预设的开场白中选择或生成
        starters = profile.conversation_starters or [
            "你好！很高兴认识你~",
            "嗨，看到你也喜欢旅行，有什么推荐的地方吗？",
            "你好呀，最近有什么好看的电影推荐吗？",
        ]
        return starters[0] if starters else "你好！很高兴认识你~"

    def _generate_early_message(
        self, profile: DigitalTwinProfile, history: List[Dict]
    ) -> str:
        """生成早期对话"""
        # 基于兴趣和话题生成
        interests = profile.interests or ["旅行", "电影", "美食"]
        messages = [
            f"我平时很喜欢{interests[0]}，你呢？",
            "你周末一般都喜欢做什么？",
            "最近有什么有趣的事情发生吗？",
        ]
        return messages[0] if messages else "你平时有什么爱好吗？"

    def _generate_deep_message(
        self, profile: DigitalTwinProfile, history: List[Dict]
    ) -> str:
        """生成深入对话"""
        values = profile.core_values or ["家庭", "事业", "成长"]
        messages = [
            f"我觉得{values[0]}对我很重要，你怎么看？",
            "你对未来的生活有什么期待？",
            "你认为一段好的关系最重要的是什么？",
        ]
        return messages[0] if messages else "你觉得两个人相处最重要的是什么？"

    def _generate_closing_message(
        self, profile: DigitalTwinProfile, history: List[Dict]
    ) -> str:
        """生成结束对话"""
        messages = [
            "今天聊得很开心，希望有机会再聊~",
            "和你聊天很愉快，期待下次交流！",
            "感觉我们有很多共同点，希望有机会深入了解~",
        ]
        return messages[0] if messages else "今天聊得很开心！"

    async def _generate_analysis(
        self,
        simulation: DigitalTwinSimulation,
        conversation_log: List[Dict],
        twin_a: DigitalTwinProfile,
        twin_b: DigitalTwinProfile,
    ) -> Dict[str, Any]:
        """
        生成模拟分析报告

        降级方案：
        - LLM 启用时：调用 LLM 生成深度分析
        - LLM 未启用时：使用基于规则的匹配算法
        """
        # 尝试使用 LLM 生成分析
        if settings.llm_enabled and settings.llm_api_key:
            try:
                return await self._generate_analysis_with_llm(
                    simulation, conversation_log, twin_a, twin_b
                )
            except Exception as e:
                logger.warning(f"LLM analysis generation failed: {e}, using fallback")

        # 降级方案：基于规则的匹配分析
        return self._generate_analysis_fallback(simulation, conversation_log, twin_a, twin_b)

    async def _generate_analysis_with_llm(
        self,
        simulation: DigitalTwinSimulation,
        conversation_log: List[Dict],
        twin_a: DigitalTwinProfile,
        twin_b: DigitalTwinProfile,
    ) -> Dict[str, Any]:
        """使用 LLM 生成模拟分析"""
        logger.info("Using LLM for digital twin compatibility analysis")

        # 构建 prompt
        prompt = self._build_analysis_prompt(simulation, conversation_log, twin_a, twin_b)

        # 调用 LLM 客户端
        from integration.llm_client import LLMIntegrationClient
        llm_client = LLMIntegrationClient()

        try:
            import asyncio
            llm_response = await llm_client.generate_chat(prompt)

            # 解析 LLM 响应
            analysis = self._parse_analysis_llm_response(llm_response)

            return analysis

        except Exception as e:
            logger.warning(f"LLM analysis failed: {e}, using fallback")
            raise  # 抛出异常让上层调用降级方案

    def _build_analysis_prompt(
        self,
        simulation: DigitalTwinSimulation,
        conversation_log: List[Dict],
        twin_a: DigitalTwinProfile,
        twin_b: DigitalTwinProfile,
    ) -> str:
        """构建分析 prompt"""
        # 对话历史
        conversation_text = ""
        for msg in conversation_log[-10:]:  # 只保留最近 10 条
            conversation_text += f"{msg.get('sender', 'A')}: {msg.get('message', '')}\n"

        prompt = f"""你是一个专业的 AI 情感分析师，正在分析两个 AI 数字孪生体之间的模拟对话。

## 用户 A 画像
- 名字：{twin_a.user_name}
- 兴趣：{twin_a.interests}
- 价值观：{twin_a.core_values}
- 沟通风格：{twin_a.communication_style}

## 用户 B 画像
- 名字：{twin_b.user_name}
- 兴趣：{twin_b.interests}
- 价值观：{twin_b.core_values}
- 沟通风格：{twin_b.communication_style}

## 对话历史
{conversation_text}

## 模拟信息
- 总对话轮数：{len(conversation_log) // 2}
- 模拟状态：{simulation.status}

请分析这段对话，评估双方的兼容性，并以 JSON 格式返回：
{{
    "compatibility_score": 75,  // 综合匹配度 0-100
    "highlights": ["亮点 1", "亮点 2"],  // 2-4 个亮点
    "concerns": ["关注点 1"],  // 0-2 个关注点
    "suggestions": ["建议 1", "建议 2"],  // 2-3 个建议
    "analysis": {{
        "communication": 80,  // 沟通质量 0-100
        "interests": 70,  // 兴趣匹配度 0-100
        "values": 75,  // 价值观匹配度 0-100
        "emotional_connection": 65  // 情感连接度 0-100
    }}
}}
"""
        return prompt

    def _parse_analysis_llm_response(self, llm_response: Dict[str, Any]) -> Dict[str, Any]:
        """解析 LLM 分析响应"""
        try:
            if isinstance(llm_response, str):
                import json
                llm_response = json.loads(llm_response)

            # 提取分析结果
            compatibility_score = llm_response.get("compatibility_score", 50)
            highlights = llm_response.get("highlights", [])
            concerns = llm_response.get("concerns", [])
            suggestions = llm_response.get("suggestions", [])
            analysis = llm_response.get("analysis", {})

            return {
                "compatibility_score": compatibility_score,
                "highlights": highlights,
                "concerns": concerns,
                "suggestions": suggestions,
                "detailed_analysis": analysis
            }

        except Exception as e:
            logger.error(f"Failed to parse LLM analysis response: {e}")
            # 返回默认分析
            return {
                "compatibility_score": 50,
                "highlights": ["双方进行了友好交流"],
                "concerns": [],
                "suggestions": ["建议进一步了解对方"],
                "detailed_analysis": {}
            }

    def _generate_analysis_fallback(
        self,
        simulation: DigitalTwinSimulation,
        conversation_log: List[Dict],
        twin_a: DigitalTwinProfile,
        twin_b: DigitalTwinProfile,
    ) -> Dict[str, Any]:
        """降级方案：基于规则生成模拟分析报告"""
        # 模拟分析结果
        # 基于双方的兴趣、价值观等计算匹配度
        interests_a = set(twin_a.interests or [])
        interests_b = set(twin_b.interests or [])
        common_interests = len(interests_a & interests_b)
        total_interests = len(interests_a | interests_b)

        # 计算兴趣匹配度 (0-100)
        interest_score = (common_interests / max(total_interests, 1)) * 100

        # 基于对话轮次计算互动质量
        conversation_rounds = len(conversation_log) // 2
        conversation_score = min(100, conversation_rounds * 10)

        # 生成亮点
        highlights = []
        if common_interests > 0:
            highlights.append(f"双方有{common_interests}个共同兴趣爱好")
        if conversation_rounds > 3:
            highlights.append("对话互动积极，持续时间较长")
        if not highlights:
            highlights.append("初次接触，有待进一步了解")

        # 生成潜在冲突
        potential_conflicts = [
            "生活节奏可能存在差异",
            "消费观念需要进一步了解",
        ]

        # 返回分析结果
        return {
            "common_interests": common_interests,
            "interest_score": interest_score,
            "conversation_score": conversation_score,
            "highlights": highlights,
            "potential_conflicts": potential_conflicts,
            "conversation_highlights": conversation_log[:3],  # 前几轮对话
            "ai_analysis": {
                "summary": "模拟显示双方有较好的兼容性",
                "communication_style": "双方沟通顺畅",
                "values_compatibility": "价值观高度一致",
            },
            "ai_suggestions": [
                "建议初次约会选择轻松的咖啡馆或书店",
                "可以深入聊聊各自的旅行经历",
                "避免过早讨论敏感话题如婚姻规划",
            ],
        }

    # ========== 报告生成 ==========

    def generate_report(
        self,
        simulation_id: int,
        user_id: str,
    ) -> Tuple[bool, str, Optional[DigitalTwinReport]]:
        """
        生成复盘报告

        Args:
            simulation_id: 模拟 ID
            user_id: 查看报告的用户 ID

        Returns:
            (success, message, report)
        """
        try:
            db = self._get_db()
            simulation = db.query(DigitalTwinSimulation).filter(
                DigitalTwinSimulation.id == simulation_id
            ).first()

            if not simulation:
                return False, "模拟未找到", None

            if simulation.status != "completed":
                return False, "模拟尚未完成", None

            # 检查报告是否已存在
            existing_report = db.query(DigitalTwinReport).filter(
                DigitalTwinReport.simulation_id == simulation_id,
                DigitalTwinReport.user_id == user_id,
            ).first()

            if existing_report:
                return True, "报告已存在", existing_report

            # 创建报告
            report = DigitalTwinReport(
                simulation_id=simulation_id,
                user_id=user_id,
                report_title="数字分身相亲复盘报告",
                report_summary=self._generate_report_summary(simulation),
                report_content=simulation.ai_analysis,
                overall_compatibility=simulation.compatibility_score,
                dimension_scores={
                    "communication": simulation.communication_match,
                    "values": simulation.values_alignment,
                    "chemistry": simulation.chemistry_score,
                },
                strengths=simulation.highlights,
                growth_areas=simulation.potential_conflicts,
                date_suggestions=simulation.ai_suggestions,
                conversation_snippets=simulation.conversation_highlights,
                is_generated=True,
            )

            db.add(report)
            db.commit()
            db.refresh(report)

            logger.info(f"Generated report for simulation {simulation_id}")
            return True, "报告已生成", report

        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return False, str(e), None

    def _generate_report_summary(self, simulation: DigitalTwinSimulation) -> str:
        """生成报告摘要"""
        score = simulation.compatibility_score
        if score >= 80:
            verdict = "高度兼容"
        elif score >= 60:
            verdict = "中等兼容"
        else:
            verdict = "需要进一步了解"

        return (
            f"经过{simulation.total_rounds}轮对话模拟，"
            f"你们的整体兼容性为{score:.0f}分（{verdict}）。"
            f"AI 发现{len(simulation.highlights)}个契合点和"
            f"{len(simulation.potential_conflicts)}个潜在需要注意的方面。"
        )

    def get_report(self, user_id: str, simulation_id: int) -> Optional[DigitalTwinReport]:
        """获取报告"""
        db = self._get_db()
        return db.query(DigitalTwinReport).filter(
            DigitalTwinReport.simulation_id == simulation_id,
            DigitalTwinReport.user_id == user_id,
        ).first()

    def mark_report_viewed(self, report_id: int) -> bool:
        """标记报告已查看"""
        try:
            db = self._get_db()
            report = db.query(DigitalTwinReport).filter(
                DigitalTwinReport.id == report_id
            ).first()
            if report:
                report.is_viewed = True
                db.commit()
                return True
            return False
        except Exception:
            return False


# 全局单例
digital_twin_service = DigitalTwinService()
