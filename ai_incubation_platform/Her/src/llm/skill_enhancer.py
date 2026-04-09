"""
LLM 增强的 Skill 意图理解模块

为所有 Agent Skills 提供统一的意图理解、参数提取和响应生成能力

AI Native 设计原则:
1. AI 依赖 - 核心意图理解完全依赖 LLM
2. 自主性 - AI 主动推断用户隐含需求
3. 对话优先 - 支持自然语言输入
4. Generative UI - AI 动态选择 UI 组件
"""
from typing import Dict, Any, Optional, List, Tuple
import json
from datetime import datetime
from utils.logger import logger
from llm.client import call_llm, analyze_text


class SkillIntentParser:
    """
    Skill 意图解析器

    使用 LLM 理解用户自然语言输入，提取 Skill 执行所需的参数
    """

    def __init__(self):
        self.skill_contexts = {
            "matchmaking_assistant": self._get_matchmaking_context(),
            "pre_communication": self._get_precommunication_context(),
            "omniscient_insight": self._get_insight_context(),
            "relationship_coach": self._get_relationship_context(),
            "date_planning": self._get_date_context(),
            "bill_analysis": self._get_bill_context(),
            "geo_location": self._get_geo_context(),
            "gift_ordering": self._get_gift_context(),
        }

    def _get_matchmaking_context(self) -> str:
        return """你是一个专业的 AI 红娘助手。用户会表达他们的择偶需求，你需要：
1. 理解用户的择偶意图（主动寻找/随便看看/特定条件）
2. 提取硬性条件（年龄范围、地理位置、身高等不可妥协的条件）
3. 提取软性偏好（兴趣爱好、性格特质、生活方式等）
4. 识别用户的语气和情感状态（急切/随意/认真）

返回 JSON 格式：
{
    "intent_type": "active_search|casual_browse|specific_request|daily_recommendation",
    "hard_requirements": ["条件 1", "条件 2"],
    "soft_preferences": ["偏好 1", "偏好 2"],
    "emotional_state": "eager|casual|serious|playful",
    "suggested_ui": "match_spotlight|match_carousel|match_list"
}"""

    def _get_precommunication_context(self) -> str:
        return """你是 AI 预沟通助手。用户会表达对预沟通的需求，你需要：
1. 识别操作类型（启动/检查状态/获取报告/取消）
2. 提取匹配 ID
3. 理解用户偏好（对话风格、关键话题）

返回 JSON 格式：
{
    "action": "start|check_status|get_report|cancel",
    "match_id": "匹配 ID",
    "preferences": {
        "conversation_style": "friendly|direct|humorous|deep",
        "key_topics": ["话题 1", "话题 2"]
    }
}"""

    def _get_insight_context(self) -> str:
        return """你是 AI 全知感知助手。用户会询问关于自己行为模式或状态的问题，你需要：
1. 识别查询类型（总览/行为模式/洞察/建议）
2. 提取时间范围
3. 理解用户关注焦点

返回 JSON 格式：
{
    "query_type": "overview|patterns|insights|suggestions",
    "time_range": "today|week|month",
    "focus_area": "matching|communication|dating|relationship"
}"""

    def _get_relationship_context(self) -> str:
        return """你是关系教练助手。用户会询问关系维护相关的问题，你需要：
1. 识别操作类型（健康检查/获取建议/策划约会/礼物建议）
2. 提取匹配 ID
3. 理解关系问题类型或场合

返回 JSON 格式：
{
    "action": "health_check|get_advice|plan_date|gift_suggestion",
    "match_id": "匹配 ID",
    "context": {
        "issue_type": "communication_drop|conflict|anniversary|milestone",
        "occasion": "birthday|anniversary|valentines|surprise",
        "budget_range": "low|medium|high"
    }
}"""

    def _get_date_context(self) -> str:
        return """你是约会策划助手。用户会请求约会建议，你需要：
1. 识别约会类型（首次/休闲/浪漫/冒险/文化）
2. 提取预算范围
3. 理解时长偏好和时间偏好

返回 JSON 格式：
{
    "date_type": "first_date|casual_meetup|romantic_date|adventurous_date|cultural_date",
    "budget_range": "low|medium|high",
    "duration": "short|medium|long",
    "time_preference": "morning|afternoon|evening|any"
}"""

    def _get_bill_context(self) -> str:
        return """你是账单分析助手。用户会询问消费相关的问题，你需要：
1. 识别操作类型（分析账单/获取画像/比较兼容性）
2. 提取时间范围
3. 如有兼容性比较，提取目标用户 ID

返回 JSON 格式：
{
    "action": "analyze|get_profile|compare_compatibility",
    "time_range": "month|quarter|year",
    "target_user_id": "目标用户 ID（可选）"
}"""

    def _get_geo_context(self) -> str:
        return """你是地理位置助手。用户会询问位置相关的问题，你需要：
1. 识别操作类型（分析轨迹/获取热区/检查兼容性/推荐约会地点）
2. 提取时间范围
3. 如有兼容性检查，提取目标用户 ID
4. 理解约会类型偏好

返回 JSON 格式：
{
    "action": "analyze_trajectory|get_hotzones|check_compatibility|recommend_date_spots",
    "time_range": "week|month|quarter",
    "target_user_id": "目标用户 ID（可选）",
    "date_type": "casual|formal|romantic"
}"""

    def _get_gift_context(self) -> str:
        return """你是礼物订购助手。用户会询问礼物相关的问题，你需要：
1. 识别操作类型（获取推荐/比较选项/下订单/追踪物流/获取场合提醒）
2. 提取匹配 ID
3. 理解场合类型和预算范围

返回 JSON 格式：
{
    "action": "get_suggestions|compare_options|place_order|track_delivery|get_occasion_reminder",
    "match_id": "匹配 ID",
    "occasion": "birthday|anniversary|valentines|christmas|surprise|apology",
    "budget_range": "under_100|100_300|300_500|500_1000|above_1000"
}"""

    async def parse_intent(
        self,
        skill_name: str,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        解析用户意图

        Args:
            skill_name: Skill 名称
            user_input: 用户自然语言输入
            context: 上下文信息（用户画像、历史对话等）

        Returns:
            解析后的参数 dict
        """
        logger.info(f"IntentParser: Parsing intent for skill={skill_name}, input={user_input[:50]}...")

        system_prompt = self.skill_contexts.get(skill_name, "请理解用户的意图并提取参数。")

        # 构建上下文信息
        context_info = ""
        if context:
            if context.get("user_id"):
                context_info += f"用户 ID: {context['user_id']}\n"
            if context.get("conversation_history"):
                context_info += f"对话历史：{context['conversation_history'][-2:]}\n"
            if context.get("time_of_day"):
                context_info += f"当前时间：{context['time_of_day']}\n"

        # 调用 LLM 解析意图
        prompt = f"""{context_info}
用户输入：{user_input}

请根据系统提示中的要求，提取参数并返回 JSON。"""

        try:
            response = call_llm(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,  # 意图理解用较低温度保证稳定性
                max_tokens=500
            )

            # 尝试解析 JSON
            result = self._parse_json_response(response)

            if result:
                logger.info(f"IntentParser: Successfully parsed intent for {skill_name}")
                return result
            else:
                logger.warning(f"IntentParser: Failed to parse JSON, using fallback for {skill_name}")
                return self._fallback_parse(skill_name, user_input, context)

        except Exception as e:
            logger.error(f"IntentParser: Parse failed: {e}, using fallback")
            return self._fallback_parse(skill_name, user_input, context)

    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析 LLM 返回的 JSON 响应"""
        try:
            # 尝试直接解析
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.debug(f"JSON parse failed: {e}, response: {response[:200]}")
            pass

        # 尝试提取 JSON 块
        import re
        json_pattern = r'\{[\s\S]*\}'
        match = re.search(json_pattern, response)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError as e:
                logger.debug(f"JSON extract failed: {e}")
                pass

        return None

    def _fallback_parse(
        self,
        skill_name: str,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """降级解析（关键词匹配）"""
        logger.info(f"IntentParser: Using fallback parsing for {skill_name}")

        user_input_lower = user_input.lower()

        if skill_name == "matchmaking_assistant":
            return self._fallback_matchmaking(user_input_lower, context)
        elif skill_name == "gift_ordering":
            return self._fallback_gift(user_input_lower, context)
        # ... 其他 Skill 的降级解析

        return {}

    def _fallback_matchmaking(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """匹配助手的降级解析"""
        # 检测意图类型
        if any(kw in user_input for kw in ["帮我找", "推荐", "介绍"]):
            intent_type = "active_search"
        elif any(kw in user_input for kw in ["随便看看", "逛逛"]):
            intent_type = "casual_browse"
        elif any(kw in user_input for kw in ["每日", "今天"]):
            intent_type = "daily_recommendation"
        else:
            intent_type = "specific_request"

        # 提取硬性条件（简单关键词）
        hard_requirements = []
        if "年龄" in user_input:
            import re
            age_match = re.search(r'年龄.?(\d+).?(\d+)', user_input)
            if age_match:
                hard_requirements.append(f"年龄 {age_match.group(1)}-{age_match.group(2)} 岁")

        # 提取软性偏好
        soft_preferences = []
        interest_keywords = ["旅行", "美食", "阅读", "运动", "音乐", "电影", "游戏"]
        for kw in interest_keywords:
            if kw in user_input:
                soft_preferences.append(kw)

        return {
            "user_intent": user_input,
            "intent_type": intent_type,
            "hard_requirements": hard_requirements,
            "soft_preferences": soft_preferences,
            "emotional_state": "casual",
            "suggested_ui": "match_list"
        }

    def _fallback_gift(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """礼物订购的降级解析"""
        # 检测场合
        occasion_map = {
            "生日": "birthday",
            "纪念日": "anniversary",
            "情人节": "valentines",
            "圣诞节": "christmas",
            "惊喜": "surprise",
            "道歉": "apology"
        }

        occasion = None
        for kw, val in occasion_map.items():
            if kw in user_input:
                occasion = val
                break

        # 检测预算
        budget_map = {
            "便宜": "under_100",
            "100 到 300": "100_300",
            "300 到 500": "300_500",
            "500 到 1000": "500_1000",
            "1000 以上": "above_1000"
        }

        budget_range = None
        for kw, val in budget_map.items():
            if kw in user_input:
                budget_range = val
                break

        return {
            "action": "get_suggestions",
            "occasion": occasion,
            "budget_range": budget_range
        }


class SkillResponseGenerator:
    """
    Skill 响应生成器

    使用 LLM 生成自然语言的响应消息和 Generative UI 配置
    """

    def __init__(self):
        self.response_templates = {
            "matchmaking_assistant": self._get_matchmaking_template(),
            "gift_ordering": self._get_gift_template(),
            "bill_analysis": self._get_bill_template(),
            "geo_location": self._get_geo_template(),
        }

    def _get_matchmaking_template(self) -> str:
        return """你是一个温暖的 AI 红娘。根据以下匹配结果，生成一段自然、亲切的回复：

匹配结果：
- 找到 {match_count} 位潜在匹配对象
- 最匹配的是 {top_match_name}，匹配度 {top_match_score}%
- 共同兴趣：{common_interests}

要求:
1. 用温暖、鼓励的语气
2. 突出最匹配的对象的亮点
3. 引导用户采取行动（查看详情/开始聊天）
4. 长度 50-150 字

只返回回复文本，不要 JSON。"""

    def _get_gift_template(self) -> str:
        return """你是一个贴心的礼物顾问。根据以下礼物推荐，生成一段自然、有帮助的回复：

礼物推荐：
- 共推荐 {gift_count} 份礼物
- 首推：{top_gift_name}，价格¥{top_gift_price}
- 推荐理由：{top_gift_reason}
- 场合：{occasion}

要求:
1. 用贴心、专业的语气
2. 解释为什么推荐这份礼物
3. 提醒送礼时机
4. 长度 50-150 字

只返回回复文本，不要 JSON。"""

    def _get_bill_template(self) -> str:
        return """你是一个专业的消费分析师。根据以下消费画像，生成一段分析结果：

消费画像:
- 消费层级：{level}
- 消费模式：{pattern}
- 偏好类别：{categories}

要求:
1. 用专业但易懂的语气
2. 解释消费特征
3. 说明对匹配的意义
4. 长度 50-150 字

只返回回复文本，不要 JSON。"""

    def _get_geo_template(self) -> str:
        return """你是一个贴心的约会策划师。根据以下位置分析，生成约会地点推荐：

分析结果:
- 双方活动热区中点：{midpoint}
- 推荐约会地点：{date_spots}
- 交通便利度：{convenience}

要求:
1. 用友好、热情的语气
2. 解释为什么推荐这些地点
3. 提供实用建议（交通、最佳时间）
4. 长度 50-150 字

只返回回复文本，不要 JSON。"""

    async def generate_response(
        self,
        skill_name: str,
        skill_result: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成响应

        Args:
            skill_name: Skill 名称
            skill_result: Skill 执行结果
            user_context: 用户上下文

        Returns:
            包含 ai_message 和 generative_ui 的完整响应
        """
        logger.info(f"ResponseGenerator: Generating response for skill={skill_name}")

        template = self.response_templates.get(skill_name)

        if not template:
            return self._generate_default_response(skill_result)

        # 填充模板参数
        template_data = self._extract_template_data(skill_name, skill_result)

        try:
            prompt = template.format(**template_data)

            ai_message = call_llm(
                prompt=prompt,
                temperature=0.7,  # 生成用较高温度增加多样性
                max_tokens=200
            )

            # 生成 Generative UI 配置
            generative_ui = self._generate_generative_ui(skill_name, skill_result)

            return {
                "ai_message": ai_message,
                "generative_ui": generative_ui,
                **skill_result
            }

        except Exception as e:
            logger.error(f"ResponseGenerator: Generation failed: {e}")
            return self._generate_default_response(skill_result)

    def _extract_template_data(
        self,
        skill_name: str,
        skill_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """提取模板数据"""
        if skill_name == "matchmaking_assistant":
            matches = skill_result.get("matches", [])
            top_match = matches[0] if matches else {}
            return {
                "match_count": len(matches),
                "top_match_name": top_match.get("name", "未知"),
                "top_match_score": int(top_match.get("score", 0) * 100),
                "common_interests": ", ".join(top_match.get("common_interests", []))
            }
        elif skill_name == "gift_ordering":
            gifts = skill_result.get("gift_suggestions", [])
            top_gift = gifts[0] if gifts else {}
            return {
                "gift_count": len(gifts),
                "top_gift_name": top_gift.get("name", "未知"),
                "top_gift_price": top_gift.get("price", 0),
                "top_gift_reason": top_gift.get("match_reason", ""),
                "occasion": skill_result.get("occasion_info", {}).get("occasion_type", "日常")
            }
        elif skill_name == "bill_analysis":
            profile = skill_result.get("consumption_profile", {})
            return {
                "level": profile.get("level", "未知"),
                "pattern": profile.get("spending_pattern", "未知"),
                "categories": ", ".join(profile.get("preferred_categories", []))
            }
        elif skill_name == "geo_location":
            spots = skill_result.get("date_spot_recommendations", [])
            return {
                "midpoint": "双方中点区域",
                "date_spots": ", ".join([s.get("name", "") for s in spots[:3]]),
                "convenience": "交通便利"
            }

        return {}

    def _generate_default_response(self, skill_result: Dict[str, Any]) -> Dict[str, Any]:
        """生成默认响应（无 LLM）"""
        return {
            "ai_message": skill_result.get("ai_message", "操作已完成"),
            "generative_ui": {"component_type": "empty_state", "props": {}},
            **skill_result
        }

    def _generate_generative_ui(
        self,
        skill_name: str,
        skill_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成 Generative UI 配置"""
        if skill_name == "matchmaking_assistant":
            matches = skill_result.get("matches", [])
            if len(matches) == 0:
                return {"component_type": "empty_state", "props": {"message": "暂未找到匹配"}}
            elif len(matches) <= 3:
                return {
                    "component_type": "match_card_list",
                    "props": {"matches": matches, "show_actions": True}
                }
            else:
                return {
                    "component_type": "match_carousel",
                    "props": {"matches": matches, "autoplay": True}
                }

        elif skill_name == "gift_ordering":
            gifts = skill_result.get("gift_suggestions", [])
            if len(gifts) <= 3:
                return {
                    "component_type": "gift_grid",
                    "props": {"gifts": gifts, "columns": 3}
                }
            else:
                return {
                    "component_type": "gift_carousel",
                    "props": {"gifts": gifts, "autoplay": True}
                }

        elif skill_name == "bill_analysis":
            return {
                "component_type": "consumption_profile",
                "props": {"profile": skill_result.get("consumption_profile", {})}
            }

        elif skill_name == "geo_location":
            return {
                "component_type": "date_spot_map",
                "props": {"spots": skill_result.get("date_spot_recommendations", [])}
            }

        return {"component_type": "empty_state", "props": {}}


# 全局单例
_intent_parser: Optional[SkillIntentParser] = None
_response_generator: Optional[SkillResponseGenerator] = None


def get_intent_parser() -> SkillIntentParser:
    """获取意图解析器单例"""
    global _intent_parser
    if _intent_parser is None:
        _intent_parser = SkillIntentParser()
    return _intent_parser


def get_response_generator() -> SkillResponseGenerator:
    """获取响应生成器单例"""
    global _response_generator
    if _response_generator is None:
        _response_generator = SkillResponseGenerator()
    return _response_generator
