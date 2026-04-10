"""
匹配助手 Skill

AI 红娘核心 Skill - 对话式匹配
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from agent.skills.base import BaseSkill
from utils.logger import logger
import json


class MatchmakingSkill:
    """
    AI 红娘助手 Skill - 帮助用户找到合适的匹配对象

    核心能力:
    - 理解用户的自然语言需求
    - 从对话中提取匹配条件（硬性/软性）
    - 执行深度兼容性分析
    - 推送匹配推荐并生成解释
    - 支持多轮对话 refinement

    自主触发条件:
    - 每日推荐时间（早 8 点/晚 8 点）
    - 用户表达孤独/想恋爱
    - 用户资料更新后
    - 检测到高质量匹配（score > 0.85）
    """

    name = "matchmaking_assistant"
    version = "2.0.0"
    description = """
    AI 红娘助手，帮助用户找到合适的匹配对象

    能力:
    - 理解用户的自然语言需求（如'想找一个喜欢旅行的人'）
    - 从对话中提取匹配条件
    - 执行深度兼容性分析
    - 推送匹配推荐
    """

    def get_input_schema(self) -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "user_intent": {
                    "type": "string",
                    "description": "用户表达的匹配需求"
                },
                "hard_requirements": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "硬性条件（年龄/地点等）"
                },
                "soft_preferences": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "软性偏好（兴趣/性格等）"
                },
                "context": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "conversation_history": {"type": "array"},
                        "time_of_day": {"type": "string"}
                    }
                }
            },
            "required": ["user_intent"]
        }

    def get_output_schema(self) -> dict:
        """获取输出参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "ai_message": {"type": "string"},
                "matches": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string"},
                            "name": {"type": "string"},
                            "score": {"type": "number"},
                            "reasoning": {"type": "string"},
                            "common_interests": {"type": "array"}
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
            }
        }

    async def execute(
        self,
        user_intent: str,
        hard_requirements: Optional[List[str]] = None,
        soft_preferences: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> dict:
        """
        执行匹配助手 Skill

        Args:
            user_intent: 用户自然语言意图
            hard_requirements: 硬性条件列表
            soft_preferences: 软性偏好列表
            context: 上下文信息
            **kwargs: 额外参数

        Returns:
            Skill 执行结果
        """
        logger.info(f"MatchmakingSkill: Executing for intent='{user_intent[:50]}...'")

        start_time = datetime.now()

        # Step 1: 意图理解与参数提取
        intent_analysis = self._parse_intent(user_intent, context)

        # 合并用户指定的条件
        if hard_requirements:
            intent_analysis["hard_requirements"].extend(hard_requirements)
        if soft_preferences:
            intent_analysis["soft_preferences"].extend(soft_preferences)

        # Step 2: 执行匹配工作流
        from agent.workflows.autonomous_workflows import AutoMatchRecommendWorkflow

        workflow = AutoMatchRecommendWorkflow()
        workflow_result = workflow.execute(
            user_id=context.get("user_id") if context else "user-anonymous-dev",
            limit=intent_analysis.get("limit", 5),
            min_score=intent_analysis.get("min_score", 0.6),
            include_deep_analysis=True
        )

        # Step 3: 生成自然语言响应
        ai_message = self._generate_message(intent_analysis, workflow_result)

        # Step 4: 构建 Generative UI
        generative_ui = self._build_generative_ui(workflow_result)

        # Step 5: 生成建议操作
        suggested_actions = self._generate_actions(workflow_result)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "success": True,
            "ai_message": ai_message,
            "matches": workflow_result.get("recommendations", []),
            "generative_ui": generative_ui,
            "suggested_actions": suggested_actions,
            "skill_metadata": {
                "name": self.name,
                "version": self.version,
                "execution_time_ms": int(execution_time),
                "intent_type": intent_analysis.get("intent_type", "general")
            }
        }

    def _parse_intent(self, intent: str, context: dict = None) -> dict:
        """
        解析用户意图，提取匹配参数

        使用 LLM 进行深度语义理解，识别用户的真实意图和偏好条件，
        而非硬编码的关键词匹配。

        支持识别：
        - 意图类型（严肃恋爱/每日推荐/兴趣匹配/地点匹配等）
        - 硬性条件（年龄/地区/学历/收入等）
        - 软性偏好（兴趣/性格/生活方式等）
        - 情绪状态（期待/焦虑/孤独等）
        """
        logger.info(f"MatchmakingSkill: Parsing intent: {intent[:50]}...")

        # 尝试使用 LLM 进行意图识别
        llm_result = self._parse_intent_llm(intent)

        if llm_result and llm_result.get("intent_type"):
            logger.info(f"MatchmakingSkill: LLM parsed intent: {llm_result['intent_type']}")
            return {
                "intent_type": llm_result.get("intent_type", "general"),
                "limit": llm_result.get("limit", 5),
                "min_score": llm_result.get("min_score", 0.6),
                "hard_requirements": llm_result.get("hard_requirements", []),
                "soft_preferences": llm_result.get("soft_preferences", []),
                "emotional_state": llm_result.get("emotional_state", "normal"),
                "confidence": llm_result.get("confidence", 0.8),
                "is_llm_analyzed": True
            }

        # 降级到关键词匹配
        logger.info("MatchmakingSkill: Using fallback keyword matching")
        return self._parse_intent_fallback(intent, context)

    def _call_llm_sync(self, llm_service, prompt: str) -> str:
        """同步调用 LLM"""
        import asyncio

        try:
            # 检查是否有运行的事件循环
            try:
                loop = asyncio.get_running_loop()
                # 在有运行循环的环境中（如 FastAPI），创建新线程运行
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, llm_service._call_llm(prompt))
                    return future.result(timeout=30)
            except RuntimeError:
                # 没有运行中的事件循环，直接创建
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(llm_service._call_llm(prompt))
                finally:
                    loop.close()
        except Exception as e:
            logger.error(f"MatchmakingSkill: LLM sync call failed: {e}")
            raise

    def _extract_json_from_response(self, response: str) -> dict:
        """从 LLM 响应中提取 JSON"""
        # 清理响应，移除 markdown 代码块标记
        response = response.strip()
        if response.startswith('```json'):
            response = response[7:]
        if response.startswith('```'):
            response = response[3:]
        if response.endswith('```'):
            response = response[:-3]
        response = response.strip()

        # 尝试直接解析
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # 尝试使用正则提取 JSON
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # 所有尝试失败，返回默认值
        logger.warning(f"MatchmakingSkill: Failed to extract JSON from response: {response[:200]}")
        return {
            "intent_type": "general",
            "limit": 5,
            "min_score": 0.6,
            "hard_requirements": [],
            "soft_preferences": [],
            "emotional_state": "normal",
            "confidence": 0.5
        }

    def _parse_intent_llm(self, intent: str) -> Optional[dict]:
        """
        使用 LLM 解析用户意图（内部方法）

        Returns:
            意图分析结果，如果 LLM 调用失败则返回 None
        """
        from services.llm_semantic_service import get_llm_semantic_service

        llm_service = get_llm_semantic_service()

        # 简化的 prompt，提高兼容性
        prompt = f'''请分析用户的婚恋匹配需求，返回 JSON 格式结果。

用户输入：{intent}

返回 JSON 格式：
{{
    "intent_type": "serious_relationship" 或 "daily_browse" 或 "interest_based" 或 "location_based" 或 "general",
    "limit": 数字，
    "min_score": 数字，
    "hard_requirements": [],
    "soft_preferences": [],
    "emotional_state": "normal" 或 "excited" 或 "anxious" 或 "lonely"
}}

规则：
- "找对象/谈恋爱/结婚" → serious_relationship, min_score=0.75
- "看看/推荐/今日" → daily_browse, limit=10
- 提到地点 → location_based
- 提到兴趣 → interest_based，把兴趣加入 soft_preferences
- 其他 → general

只返回 JSON，不要其他文字。'''

        try:
            llm_response = self._call_llm_sync(llm_service, prompt)

            if not llm_response or llm_response.startswith('{"fallback"'):
                return None

            return self._extract_json_from_response(llm_response)

        except Exception as e:
            logger.debug(f"MatchmakingSkill: LLM intent parsing failed: {e}")
            return None

    def _parse_intent_fallback(self, intent: str, context: dict = None) -> dict:
        """
        # ==================== FALLBACK 方案 ====================
        # 此方法仅在 LLM 不可用时作为降级方案使用。
        # 主要意图识别应通过 _parse_intent_llm() 进行 AI 分析。
        # =======================================================

        使用关键词匹配进行简单的意图识别（降级方案）
        """
        result = {
            "intent_type": "general",
            "limit": 5,
            "min_score": 0.6,
            "hard_requirements": [],
            "soft_preferences": [],
            "emotional_state": "normal",
            "is_llm_analyzed": False
        }

        intent_lower = intent.lower()

        # 识别意图类型
        if any(word in intent_lower for word in ["认真", "谈恋爱", "结婚", "找对象"]):
            result["intent_type"] = "serious_relationship"
            result["min_score"] = 0.7
            result["hard_requirements"].append("goal=serious")

        if any(word in intent_lower for word in ["看看", "推荐", "今日", "每天", "每日"]):
            result["intent_type"] = "daily_browse"
            result["limit"] = 10

        if "旅行" in intent_lower or "旅游" in intent_lower:
            result["soft_preferences"].append("interest=旅行")

        if "美食" in intent_lower or "吃" in intent_lower:
            result["soft_preferences"].append("interest=美食")

        if "健身" in intent_lower or "运动" in intent_lower:
            result["soft_preferences"].append("interest=健身")

        if "阅读" in intent_lower or "书" in intent_lower:
            result["soft_preferences"].append("interest=阅读")

        # 提取数量
        for num_str, num_val in [("三个", 3), ("3 个", 3), ("五个", 5), ("5 个", 5), ("十个", 10), ("10 个", 10)]:
            if num_str in intent:
                result["limit"] = num_val
                break

        # 检测地点偏好
        if "附近" in intent or "同城" in intent or "本地" in intent:
            result["intent_type"] = "location_based"
            result["hard_requirements"].append("location=nearby")

        # 检测年龄偏好
        if "年轻" in intent:
            result["hard_requirements"].append("age_preference=younger")
        if "成熟" in intent:
            result["hard_requirements"].append("age_preference=older")

        return result

    def _generate_message(self, intent: dict, workflow_result: dict) -> str:
        """生成自然语言响应"""
        matches = workflow_result.get("recommendations", [])
        intent_type = intent.get("intent_type", "general")

        if not matches:
            if intent_type == "daily_browse":
                return "今天暂时没有新的推荐，保持耐心，好的缘分值得等待。建议你完善一下个人资料，增加曝光机会哦~"
            else:
                return "抱歉，根据您的需求暂时没有特别匹配的人选。可以适当放宽一些条件，或者完善个人资料增加匹配机会~"

        top_match = matches[0]
        match_name = top_match.get("user", {}).get("name", "TA")
        score = top_match.get("score", 0) * 100

        # 根据意图类型生成不同风格的消息
        if intent_type == "serious_relationship":
            message = f"为你找到{len(matches)}位以认真恋爱为目标的匹配对象！\n\n"
            message += f"最匹配的是{match_name}，匹配度{score:.0f}%。\n"
        elif intent_type == "daily_browse":
            message = f"今日推荐：{len(matches)}位潜在匹配对象！\n\n"
            message += f"重点关注：{match_name}，匹配度{score:.0f}%。\n"
        elif intent_type == "location_based":
            message = f"在你附近找到{len(matches)}位匹配对象！\n\n"
            message += f"最近的是{match_name}，匹配度{score:.0f}%。\n"
        else:
            message = f"为你找到{len(matches)}位潜在匹配对象！\n\n"
            message += f"最匹配的是{match_name}，匹配度{score:.0f}%。\n"

        # 添加推荐理由
        if top_match.get("reasoning"):
            message += f"\n推荐理由：{top_match['reasoning']}\n"

        # 添加共同兴趣
        if top_match.get("common_interests"):
            interests = top_match["common_interests"][:3]
            if interests:
                message += f"\n共同兴趣：{', '.join(interests)}\n"

        # 添加鼓励语
        if intent_type == "serious_relationship":
            message += "\n以认真态度寻找缘分，成功的概率会更高哦~"
        elif intent_type == "daily_browse":
            message += "\n每日推荐基于你的最新状态和活跃度，保持活跃会有更多好推荐！"

        return message

    def _build_generative_ui(self, workflow_result: dict) -> dict:
        """构建 Generative UI 配置"""
        matches = workflow_result.get("recommendations", [])

        if not matches:
            return {
                "component_type": "empty_state",
                "props": {
                    "message": "暂无匹配",
                    "description": "完善资料或稍后再试",
                    "icon": "search-outlined"
                }
            }

        # 根据匹配数量选择 UI 类型
        if len(matches) == 1:
            # 单个高亮展示
            return {
                "component_type": "match_spotlight",
                "props": {
                    "match": matches[0],
                    "highlight_score": True,
                    "show_reasoning": True,
                    "show_common_interests": True
                }
            }
        elif len(matches) <= 3:
            # 小卡片列表
            return {
                "component_type": "match_card_list",
                "props": {
                    "matches": matches,
                    "layout": "horizontal",
                    "show_score": True,
                    "show_reasoning": False
                }
            }
        else:
            # 轮播展示
            return {
                "component_type": "match_carousel",
                "props": {
                    "matches": matches[:5],
                    "autoplay": True,
                    "autoplay_interval": 5000,
                    "show_dots": True,
                    "show_arrows": True,
                    "show_score": True
                }
            }

    def _generate_actions(self, workflow_result: dict) -> list:
        """生成建议的下一步操作"""
        actions = []
        matches = workflow_result.get("recommendations", [])

        if not matches:
            return [
                {
                    "label": "完善个人资料",
                    "action_type": "edit_profile",
                    "params": {}
                },
                {
                    "label": "浏览全部推荐",
                    "action_type": "browse_all",
                    "params": {}
                }
            ]

        # 针对第一个匹配的操作
        first_match = matches[0]
        user_id = first_match.get("user_id")

        actions.append({
            "label": "查看最匹配的对象",
            "action_type": "view_profile",
            "params": {"user_id": user_id}
        })
        actions.append({
            "label": "发起对话",
            "action_type": "start_chat",
            "params": {"user_id": user_id}
        })

        if len(matches) > 1:
            actions.append({
                "label": "浏览更多推荐",
                "action_type": "browse_more",
                "params": {"offset": 3, "limit": 5}
            })

        actions.append({
            "label": "调整匹配条件",
            "action_type": "adjust_preferences",
            "params": {}
        })

        return actions

    async def autonomous_trigger(self, user_id: str, trigger_type: str) -> dict:
        """
        自主触发匹配推荐

        Args:
            user_id: 用户 ID
            trigger_type: 触发类型 (daily/time_based/quality_match/profile_updated)

        Returns:
            触发结果
        """
        logger.info(f"MatchmakingSkill: Autonomous trigger for {user_id}, type={trigger_type}")

        # 检查触发条件
        if trigger_type == "daily":
            # 每日推荐，检查是否已发送
            if not self._should_send_daily(user_id):
                return {"triggered": False, "reason": "already_sent_today"}

        elif trigger_type == "quality_match":
            # 检测是否有高质量匹配
            high_quality_matches = self._find_high_quality_matches(user_id, threshold=0.85)
            if not high_quality_matches:
                return {"triggered": False, "reason": "no_high_quality_match"}

        elif trigger_type == "profile_updated":
            # 资料更新后触发
            pass  # 总是触发

        # 执行匹配
        result = await self.execute(
            user_intent="今日推荐",
            context={"user_id": user_id, "trigger_type": trigger_type}
        )

        if result.get("matches"):
            # 这里应该调用推送通知服务
            logger.info(f"MatchmakingSkill: Would push notification for {len(result['matches'])} matches")
            return {"triggered": True, "result": result, "should_push": True}

        return {"triggered": False, "reason": "no_matches"}

    async def trigger_daily(self, user_id: str) -> dict:
        """
        每日推荐触发

        Args:
            user_id: 用户 ID

        Returns:
            触发结果
        """
        return await self.autonomous_trigger(user_id, "daily")

    async def trigger_quality_match(self, user_id: str) -> dict:
        """
        高质量匹配触发

        Args:
            user_id: 用户 ID

        Returns:
            触发结果
        """
        return await self.autonomous_trigger(user_id, "quality_match")

    def _should_send_daily(self, user_id: str) -> bool:
        """检查是否应该发送每日推荐"""
        # 实现每日推荐频率控制
        # 检查上次发送时间，确保不超过每天一次
        # 注：当前从用户资料中读取最后推荐时间，生产环境应从推荐记录表读取
        try:
            from db.models import UserDB
            from utils.db_session_manager import db_session

            with db_session() as db:
                user = db.query(UserDB).filter(UserDB.id == user_id).first()

                if user:
                    # 检查 last_daily_recommend 字段
                    last_recommend = getattr(user, "last_daily_recommend", None)

                    if last_recommend:
                        # 如果是今天发送过，跳过
                        if isinstance(last_recommend, datetime):
                            if last_recommend.date() == datetime.now().date():
                                logger.info(f"MatchmakingSkill: Daily recommend already sent today for user={user_id}")
                                return False

                    # 更新最后推荐时间
                    user.last_daily_recommend = datetime.now()
                    db.commit()
                    logger.info(f"MatchmakingSkill: Daily recommend allowed for user={user_id}")
                    return True

                return True
        except Exception as e:
            logger.error(f"MatchmakingSkill: Error checking daily recommend: {e}")
            return True

    def _find_high_quality_matches(self, user_id: str, threshold: float = 0.85) -> list:
        """查找高质量匹配"""
        # 实现高质量匹配检测
        # 预先计算匹配，当发现超过阈值时触发推送
        # 注：当前为简化实现，生产环境应从匹配计算服务获取
        logger.info(f"MatchmakingSkill: Looking for high quality matches for user={user_id}, threshold={threshold}")

        try:
            from db.models import MatchHistoryDB
            from utils.db_session_manager import db_session

            with db_session() as db:
                # 查找未推送的高质量匹配
                matches = db.query(MatchHistoryDB).filter(
                    (MatchHistoryDB.user_id_1 == user_id) | (MatchHistoryDB.user_id_2 == user_id),
                    MatchHistoryDB.compatibility_score >= threshold,
                    MatchHistoryDB.status == "pending"
                ).all()

                if matches:
                    logger.info(f"MatchmakingSkill: Found {len(matches)} high quality matches")
                    return [
                        {
                            "match_id": m.id,
                            "user_id": m.user_id_2 if m.user_id_1 == user_id else m.user_id_1,
                            "score": m.compatibility_score
                        }
                        for m in matches
                    ]

                return []
        except Exception as e:
            logger.error(f"MatchmakingSkill: Error finding high quality matches: {e}")
            return []


# 全局 Skill 实例
_matchmaking_skill_instance: Optional[MatchmakingSkill] = None


def get_matchmaking_skill() -> MatchmakingSkill:
    """获取匹配助手 Skill 单例实例"""
    global _matchmaking_skill_instance
    if _matchmaking_skill_instance is None:
        _matchmaking_skill_instance = MatchmakingSkill()
    return _matchmaking_skill_instance
