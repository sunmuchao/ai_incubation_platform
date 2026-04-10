"""
个人信息收集 Skill - AI Native 设计

核心理念：
- AI 自主判断需要收集什么信息
- AI 动态生成问题和选项
- 不是硬编码的问题列表，而是根据上下文智能生成
- 深度追问：不满足于表面回答，持续挖掘真实偏好

工作流程：
1. 分析对话上下文，识别信息缺口
2. 生成个性化问题和选项
3. 用户选择后分析回答深度
4. 如果不够深入，生成追问
5. 更新用户画像
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from agent.skills.base import BaseSkill
from utils.logger import logger
import json


class ProfileCollectionSkill:
    """
    AI 个人信息收集 Skill

    能力：
    - 智能识别用户画像中的信息缺口
    - 动态生成个性化问题和选项
    - 支持多种问题类型（单选、多选、标签选择）
    - 自适应对话上下文
    - 深度追问：分析回答深度，不够深入时继续追问

    自主触发条件：
    - 检测到用户意图需要更多信息（如"帮我找对象"但没说偏好）
    - 匹配推荐时发现关键信息缺失
    - 用户主动完善资料
    """

    name = "profile_collection"
    version = "2.0.0"
    description = """
    AI 个人信息收集助手，通过对话收集用户偏好和资料

    能力：
    - 智能识别信息缺口
    - 动态生成问题卡片
    - 自适应对话上下文
    - 深度追问挖掘真实偏好
    """

    # 信息维度定义 - 扩展支持细分维度
    PROFILE_DIMENSIONS = {
        "relationship_goal": {
            "name": "关系目标",
            "priority": 1,
            "importance": "high",
            "sub_dimensions": ["commitment_level", "timeline"],  # 可追问的子维度
        },
        "age_preference": {
            "name": "年龄偏好",
            "priority": 2,
            "importance": "medium",
            "sub_dimensions": [],
        },
        "location_preference": {
            "name": "地域偏好",
            "priority": 3,
            "importance": "medium",
            "sub_dimensions": ["relocation_willingness"],
        },
        "interests": {
            "name": "兴趣爱好",
            "priority": 4,
            "importance": "medium",
            "sub_dimensions": ["interest_styles", "frequency"],  # 可追问细节
        },
        "personality": {
            "name": "性格特点",
            "priority": 4,
            "importance": "high",
            "sub_dimensions": ["communication_style", "emotional_expression"],
        },
        "lifestyle": {
            "name": "生活方式",
            "priority": 5,
            "importance": "low",
            "sub_dimensions": ["social_preference", "routine"],
        },
        "values": {
            "name": "价值观念",
            "priority": 6,
            "importance": "medium",
            "sub_dimensions": ["family_values", "career_priority"],
        },
        "deal_breakers": {
            "name": "底线原则",
            "priority": 7,
            "importance": "high",
            "sub_dimensions": [],
        },
    }

    # 追问深度配置 - 智能、克制、不钻牛角尖
    FOLLOW_UP_CONFIG = {
        "max_depth": 2,  # 每个维度最多追问 2 层（避免钻牛角尖）
        "depth_threshold": 0.5,  # 回答深度低于 0.5 则需要追问
        "high_importance_max_depth": 2,  # 高重要性维度最多追问 2 层
        "medium_importance_max_depth": 1,  # 中等重要性维度最多追问 1 层
        "low_importance_no_follow_up": True,  # 低重要性维度不追问
        "total_questions_limit": 8,  # 整体问题数量限制（避免用户疲劳）
        "adaptive_threshold": True,  # 根据维度重要性动态调整阈值
    }

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "conversation_context": {"type": "array"},
                "current_profile": {"type": "object"},
                "trigger_reason": {
                    "type": "string",
                    "enum": ["user_intent", "matching_need", "profile_update", "explicit_request", "follow_up"]
                },
                "previous_answer": {"type": "object"},  # 用户刚回答的内容
            },
            "required": ["user_id"]
        }

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "need_collection": {"type": "boolean"},
                "need_follow_up": {"type": "boolean"},  # 是否需要追问
                "question_card": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "subtitle": {"type": "string"},
                        "question_type": {"type": "string"},
                        "options": {"type": "array"},
                        "dimension": {"type": "string"},
                        "depth": {"type": "number"},  # 当前追问深度
                    }
                },
                "ai_message": {"type": "string"},
                "profile_gaps": {"type": "array"},
                "answer_depth": {"type": "number"},  # 回答深度评分
            }
        }

    async def execute(
        self,
        user_id: str,
        conversation_context: Optional[List[Dict]] = None,
        current_profile: Optional[Dict] = None,
        trigger_reason: str = "user_intent",
        previous_answer: Optional[Dict] = None,
        **kwargs
    ) -> dict:
        """
        执行信息收集 Skill

        Args:
            user_id: 用户 ID
            conversation_context: 对话上下文
            current_profile: 当前用户画像
            trigger_reason: 触发原因
            previous_answer: 用户刚回答的内容（用于追问场景）

        Returns:
            Skill 执行结果
        """
        logger.info(f"ProfileCollectionSkill: Executing for user={user_id}, reason={trigger_reason}")

        start_time = datetime.now()
        profile = current_profile or {}

        # 如果是追问场景，分析上一个回答
        if trigger_reason == "follow_up" and previous_answer:
            follow_up_result = await self._analyze_and_follow_up(
                user_id=user_id,
                previous_answer=previous_answer,
                profile=profile,
                context=conversation_context
            )
            if follow_up_result:
                return follow_up_result

        # Step 1: 分析信息缺口
        profile_gaps = self._analyze_profile_gaps(profile)

        if not profile_gaps:
            return {
                "success": True,
                "need_collection": False,
                "ai_message": "我已经很了解你了，还有什么想和我说的吗？",
            }

        # Step 2: 选择最需要收集的维度
        target_dimension = self._select_target_dimension(profile_gaps, conversation_context)

        # Step 3: AI 生成问题和选项
        question_card = await self._generate_question_card(
            dimension=target_dimension,
            context=conversation_context,
            profile=profile,
            depth=0
        )

        # Step 4: 生成 AI 引导语
        ai_message = self._generate_ai_message(target_dimension, trigger_reason)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "success": True,
            "need_collection": True,
            "need_follow_up": False,
            "question_card": question_card,
            "ai_message": ai_message,
            "profile_gaps": [gap["dimension"] for gap in profile_gaps],
            "skill_metadata": {
                "name": self.name,
                "version": self.version,
                "execution_time_ms": int(execution_time),
                "target_dimension": target_dimension,
            }
        }

    async def _analyze_and_follow_up(
        self,
        user_id: str,
        previous_answer: Dict,
        profile: Dict,
        context: Optional[List[Dict]] = None
    ) -> Optional[Dict]:
        """
        分析用户回答，判断是否需要追问

        智能、克制的追问策略：
        - 根据维度重要性决定是否追问
        - 低重要性维度不追问，避免浪费时间
        - 高重要性维度适度追问，但不超过 2 层
        - 避免在单个问题上钻牛角尖

        Returns:
            如果需要追问，返回追问结果；否则返回 None
        """
        dimension = previous_answer.get("dimension")
        answer = previous_answer.get("answer")
        current_depth = previous_answer.get("depth", 0)

        if not dimension or answer is None:
            return None

        # 获取维度重要性
        dimension_info = self.PROFILE_DIMENSIONS.get(dimension, {})
        importance = dimension_info.get("importance", "medium")

        # 低重要性维度不追问，避免浪费时间
        if importance == "low" and self.FOLLOW_UP_CONFIG["low_importance_no_follow_up"]:
            logger.info(f"ProfileCollectionSkill: Skipping follow-up for low importance dimension {dimension}")
            return None

        # 根据重要性决定最大追问深度
        if importance == "high":
            max_depth = self.FOLLOW_UP_CONFIG["high_importance_max_depth"]
        elif importance == "medium":
            max_depth = self.FOLLOW_UP_CONFIG["medium_importance_max_depth"]
        else:
            max_depth = self.FOLLOW_UP_CONFIG["max_depth"]

        # 检查是否达到该维度的最大深度
        if current_depth >= max_depth:
            logger.info(f"ProfileCollectionSkill: Max depth ({max_depth}) reached for {dimension} (importance={importance})")
            return None

        # 分析回答深度
        depth_score, analysis = await self._analyze_answer_depth(
            dimension=dimension,
            answer=answer,
            context=context
        )

        logger.info(f"ProfileCollectionSkill: Answer depth for {dimension} = {depth_score}")

        # 根据重要性动态调整阈值
        threshold = self.FOLLOW_UP_CONFIG["depth_threshold"]
        if self.FOLLOW_UP_CONFIG["adaptive_threshold"]:
            # 高重要性维度阈值更低（更愿意追问），低重要性维度阈值更高（减少追问）
            if importance == "high":
                threshold = 0.4  # 高重要性：深度 < 0.4 才追问
            elif importance == "low":
                threshold = 0.7  # 低重要性：深度 < 0.7 才追问（基本不追问）

        # 如果回答足够深入，不需要追问
        if depth_score >= threshold:
            return None

        # 生成追问（避免过于具体或钻牛角尖）
        follow_up_card = await self._generate_follow_up_question(
            dimension=dimension,
            original_answer=answer,
            analysis=analysis,
            current_depth=current_depth + 1,
            context=context,
            importance=importance  # 传递重要性，让追问生成更智能
        )

        if follow_up_card:
            return {
                "success": True,
                "need_collection": True,
                "need_follow_up": True,
                "question_card": follow_up_card,
                "ai_message": analysis.get("follow_up_hint", "能再多说一点吗？"),
                "answer_depth": depth_score,
                "profile_gaps": [],
            }

        return None

    async def _analyze_answer_depth(
        self,
        dimension: str,
        answer: Any,
        context: Optional[List[Dict]] = None
    ) -> Tuple[float, Dict]:
        """
        分析回答的深度

        Returns:
            (depth_score, analysis)
            depth_score: 0.0 - 1.0，越高越深入
            analysis: 分析详情，包含追问建议
        """
        # 尝试 AI 分析
        ai_result = await self._ai_analyze_depth(dimension, answer, context)
        if ai_result:
            return ai_result

        # 降级：基于规则的深度评估
        return self._rule_based_depth_analysis(dimension, answer)

    async def _ai_analyze_depth(
        self,
        dimension: str,
        answer: Any,
        context: Optional[List[Dict]] = None
    ) -> Optional[Tuple[float, Dict]]:
        """使用 AI 分析回答深度"""
        try:
            from services.llm_semantic_service import get_llm_semantic_service

            llm_service = get_llm_semantic_service()
            if not llm_service.enabled:
                return None

            dimension_info = self.PROFILE_DIMENSIONS.get(dimension, {})
            dimension_name = dimension_info.get("name", dimension)

            answer_text = answer if isinstance(answer, str) else json.dumps(answer, ensure_ascii=False)

            prompt = f'''你是一位专业的约会顾问，正在分析用户回答的深度。

分析维度：{dimension_name}
用户回答：{answer_text}

请评估这个回答的深度，并判断是否需要追问。

返回 JSON 格式：
{{
    "depth_score": 0.0-1.0,
    "is_specific": true/false,
    "has_examples": true/false,
    "has_preferences": true/false,
    "analysis": "简要分析",
    "follow_up_needed": true/false,
    "follow_up_hint": "如果需要追问，这里写引导语",
    "follow_up_question": "如果需要追问，这里写具体问题",
    "follow_up_options": [
        {{"value": "xxx", "label": "选项文本", "icon": "emoji"}}
    ]
}}

深度评估标准：
- 0.0-0.3: 太笼统，如"我喜欢旅行"
- 0.3-0.6: 有方向但不具体，如"我喜欢户外旅行"
- 0.6-0.8: 有具体偏好，如"我喜欢徒步，走过青藏线"
- 0.8-1.0: 非常具体，包含偏好、经历、原因等

只返回 JSON。'''

            from services.llm_semantic_service import call_llm_sync
            response = call_llm_sync(prompt, timeout=15)

            if response and not response.startswith('{"fallback"'):
                response = response.strip()
                if response.startswith('```json'):
                    response = response[7:]
                if response.startswith('```'):
                    response = response[3:]
                if response.endswith('```'):
                    response = response[:-3]
                response = response.strip()

                data = json.loads(response)
                depth_score = float(data.get("depth_score", 0.5))
                return depth_score, data

            return None

        except Exception as e:
            logger.debug(f"ProfileCollectionSkill: AI depth analysis failed: {e}")
            return None

    def _rule_based_depth_analysis(self, dimension: str, answer: Any) -> Tuple[float, Dict]:
        """基于规则的深度分析（降级方案）"""
        answer_text = answer if isinstance(answer, str) else json.dumps(answer, ensure_ascii=False)

        # 简单的深度评估规则
        depth = 0.3  # 基础分

        # 长度判断
        if len(answer_text) > 50:
            depth += 0.2
        if len(answer_text) > 100:
            depth += 0.1

        # 包含具体词汇
        specific_indicators = ["因为", "比如", "例如", "具体", "特别是", "最喜欢"]
        for indicator in specific_indicators:
            if indicator in answer_text:
                depth += 0.1
                break

        # 是列表选择，通常不够深入
        if isinstance(answer, list) and len(answer) <= 3:
            depth = max(0.4, depth)  # 至少 0.4，因为选择了具体选项

        return min(1.0, depth), {"follow_up_needed": depth < 0.6}

    async def _generate_follow_up_question(
        self,
        dimension: str,
        original_answer: Any,
        analysis: Dict,
        current_depth: int,
        context: Optional[List[Dict]] = None,
        importance: str = "medium"
    ) -> Optional[Dict]:
        """
        生成追问问题卡片

        智能、克制的追问策略：
        - 根据重要性调整追问风格
        - 高重要性：深入挖掘，问具体场景
        - 中等重要性：适度追问，问偏好细节
        - 低重要性：基本不追问（已在上层过滤）
        """
        # 如果 AI 分析已经给出了追问问题
        if analysis.get("follow_up_question"):
            question = analysis["follow_up_question"]
            # 添加克制的提示语，避免钻牛角尖
            if importance == "high" and current_depth == 1:
                question += "（简单说说就好~）"
            return {
                "question": question,
                "subtitle": analysis.get("follow_up_hint"),
                "question_type": "single_choice" if analysis.get("follow_up_options") else "text",
                "options": analysis.get("follow_up_options", []),
                "dimension": dimension,
                "depth": current_depth,
            }

        # 否则生成追问
        dimension_info = self.PROFILE_DIMENSIONS.get(dimension, {})
        sub_dimensions = dimension_info.get("sub_dimensions", [])

        # 根据子维度生成追问
        if sub_dimensions:
            sub_dimension = sub_dimensions[min(current_depth - 1, len(sub_dimensions) - 1)]
            return await self._generate_question_card(
                dimension=f"{dimension}.{sub_dimension}",
                context=context,
                profile={"original_answer": original_answer},
                depth=current_depth
            )

        # 没有预定义子维度，AI 生成追问
        return await self._ai_generate_follow_up(dimension, original_answer, current_depth, context, importance)

    async def _ai_generate_follow_up(
        self,
        dimension: str,
        original_answer: Any,
        depth: int,
        context: Optional[List[Dict]] = None,
        importance: str = "medium"
    ) -> Optional[Dict]:
        """
        AI 生成追问

        智能、克制的追问策略：
        - 高重要性维度：深入但不过度（最多 2 层）
        - 中等重要性维度：适度追问（最多 1 层）
        - 避免钻牛角尖，保持对话自然
        """
        try:
            from services.llm_semantic_service import get_llm_semantic_service

            llm_service = get_llm_semantic_service()
            if not llm_service.enabled:
                return None

            dimension_info = self.PROFILE_DIMENSIONS.get(dimension, {})
            dimension_name = dimension_info.get("name", dimension)

            # 根据重要性调整追问风格
            importance_guidance = {
                "high": "这是重要维度，可以稍微深入一点，但不要超过 1-2 个问题。",
                "medium": "适度追问即可，不要过于深入。",
                "low": "这个维度不太重要，不建议追问。"
            }

            guidance = importance_guidance.get(importance, importance_guidance["medium"])

            prompt = f'''用户说喜欢"{original_answer}"，但这个回答比较笼统。
请生成一个追问，帮助更好地了解 TA 的真实偏好。

维度：{dimension_name}
重要性：{importance}
用户回答：{original_answer}
追问深度：第 {depth} 层追问

指导原则：{guidance}

返回 JSON 格式：
{{
    "question": "追问的问题（自然亲切，像朋友在问，不要过于正式或钻牛角尖）",
    "subtitle": "可选的引导语",
    "question_type": "single_choice 或 text",
    "options": [
        {{"value": "xxx", "label": "选项", "icon": "emoji"}}
    ]
}}

要求：
1. 问题要具体但不过度，帮助了解更细分的偏好
2. 选项要能帮助区分不同的子类型
3. 保持轻松自然的语气，避免审问式
4. 只返回 JSON'''

            from services.llm_semantic_service import call_llm_sync
            response = call_llm_sync(prompt, timeout=15)

            if response and not response.startswith('{"fallback"'):
                response = response.strip()
                if response.startswith('```json'):
                    response = response[7:]
                if response.startswith('```'):
                    response = response[3:]
                if response.endswith('```'):
                    response = response[:-3]
                response = response.strip()

                data = json.loads(response)
                data["dimension"] = dimension
                data["depth"] = depth
                return data

            return None

        except Exception as e:
            logger.debug(f"ProfileCollectionSkill: AI follow-up generation failed: {e}")
            return None

    def _analyze_profile_gaps(self, profile: Dict) -> List[Dict]:
        """分析用户画像中的信息缺口"""
        gaps = []

        for dimension, info in self.PROFILE_DIMENSIONS.items():
            value = profile.get(dimension)
            if self._is_empty_value(value):
                gaps.append({
                    "dimension": dimension,
                    "name": info["name"],
                    "priority": info["priority"],
                    "importance": info["importance"],
                })

        # 按优先级排序
        gaps.sort(key=lambda x: x["priority"])
        return gaps

    def _is_empty_value(self, value: Any) -> bool:
        """判断值是否为空"""
        if value is None:
            return True
        if isinstance(value, str) and not value.strip():
            return True
        if isinstance(value, (list, dict)) and len(value) == 0:
            return True
        return False

    def _select_target_dimension(
        self,
        gaps: List[Dict],
        context: Optional[List[Dict]] = None
    ) -> str:
        """
        选择最需要收集的维度

        优先级：
        1. 对话上下文中提到的维度
        2. 重要性高的维度
        3. 默认顺序
        """
        if not gaps:
            return "relationship_goal"

        # 如果有上下文，检查是否提到了某些维度
        if context:
            context_text = " ".join([
                msg.get("content", "") for msg in context[-5:]  # 最近 5 条消息
            ])

            # 根据关键词判断可能相关的维度
            dimension_keywords = {
                "relationship_goal": ["关系", "恋爱", "结婚", "对象", "朋友"],
                "age_preference": ["年龄", "岁", "年轻", "成熟"],
                "location_preference": ["地点", "城市", "同城", "附近", "异地"],
                "interests": ["兴趣", "爱好", "喜欢", "电影", "音乐", "旅行"],
            }

            for dimension, keywords in dimension_keywords.items():
                if any(kw in context_text for kw in keywords):
                    # 检查这个维度是否在缺口中
                    if any(g["dimension"] == dimension for g in gaps):
                        return dimension

        # 默认返回优先级最高的缺口
        return gaps[0]["dimension"]

    async def _generate_question_card(
        self,
        dimension: str,
        context: Optional[List[Dict]] = None,
        profile: Optional[Dict] = None,
        depth: int = 0
    ) -> Dict:
        """
        AI 生成问题和选项卡片

        Args:
            dimension: 信息维度
            context: 对话上下文
            profile: 用户画像
            depth: 当前深度（0=首次提问，1+=追问）

        Returns:
            {
                "question": "问题文本",
                "subtitle": "可选的副标题",
                "question_type": "single_choice" | "multiple_choice" | "tags",
                "options": [
                    {"value": "xxx", "label": "显示文本", "icon": "emoji"}
                ],
                "dimension": "维度标识",
                "depth": 当前深度
            }
        """
        # 尝试 AI 生成
        ai_card = await self._generate_question_with_ai(dimension, context, profile, depth)
        if ai_card:
            ai_card["depth"] = depth
            return ai_card

        # 降级：使用预定义模板
        card = self._get_fallback_question_card(dimension)
        card["depth"] = depth
        return card

    async def _generate_question_with_ai(
        self,
        dimension: str,
        context: Optional[List[Dict]] = None,
        profile: Optional[Dict] = None,
        depth: int = 0
    ) -> Optional[Dict]:
        """使用 AI 动态生成问题卡片"""
        try:
            from services.llm_semantic_service import get_llm_semantic_service

            llm_service = get_llm_semantic_service()
            if not llm_service.enabled:
                return None

            dimension_info = self.PROFILE_DIMENSIONS.get(dimension, {})
            dimension_name = dimension_info.get("name", dimension)

            # 构建上下文
            context_summary = ""
            if context:
                recent_messages = context[-3:]
                context_summary = "对话背景：\n" + "\n".join([
                    f"- {msg.get('role', 'user')}: {msg.get('content', '')[:100]}"
                    for msg in recent_messages
                ])

            prompt = f'''你是一位贴心的约会顾问，正在通过聊天了解用户的需求。

正在了解的维度：{dimension_name}
{context_summary}

请生成一个问题和 3-4 个选项，帮助用户表达偏好。

返回 JSON 格式：
{{
    "question": "问题文本（简短亲切，像朋友在问）",
    "subtitle": "可选的副标题提示",
    "question_type": "single_choice 或 multiple_choice 或 tags",
    "options": [
        {{"value": "选项值", "label": "显示文本", "icon": "一个emoji"}}
    ]
}}

要求：
1. 问题要自然、有温度，不要太正式
2. 选项要具体、有代表性，能覆盖常见情况
3. 每个选项配一个 emoji 图标
4. question_type 根据维度选择：单选用 single_choice，多选用 multiple_choice
5. 只返回 JSON，不要其他内容'''

            from services.llm_semantic_service import call_llm_sync
            response = call_llm_sync(prompt, timeout=15)

            if response and not response.startswith('{"fallback"'):
                response = response.strip()
                if response.startswith('```json'):
                    response = response[7:]
                if response.startswith('```'):
                    response = response[3:]
                if response.endswith('```'):
                    response = response[:-3]
                response = response.strip()

                data = json.loads(response)
                data["dimension"] = dimension
                return data

            return None

        except Exception as e:
            logger.debug(f"ProfileCollectionSkill: AI question generation failed: {e}")
            return None

    def _get_fallback_question_card(self, dimension: str) -> Dict:
        """
        降级：预定义的问题模板

        注意：这是 AI 不可用时的 fallback 方案
        """
        templates = {
            "relationship_goal": {
                "question": "你想找什么样的关系呢？",
                "question_type": "single_choice",
                "options": [
                    {"value": "serious", "label": "认真恋爱", "icon": "💕"},
                    {"value": "casual", "label": "轻松约会", "icon": "☕"},
                    {"value": "friendship", "label": "交朋友", "icon": "🤝"},
                    {"value": "marriage", "label": "奔着结婚", "icon": "💍"},
                ],
            },
            "age_preference": {
                "question": "对方年龄有什么偏好吗？",
                "question_type": "single_choice",
                "options": [
                    {"value": "younger", "label": "比我小", "icon": "🌸"},
                    {"value": "same_age", "label": "年龄相仿", "icon": "同龄"},
                    {"value": "older", "label": "比我大", "icon": "成熟"},
                    {"value": "any", "label": "无所谓", "icon": "❓"},
                ],
            },
            "location_preference": {
                "question": "地域方面有要求吗？",
                "question_type": "single_choice",
                "options": [
                    {"value": "same_city", "label": "同城最好", "icon": "🏙️"},
                    {"value": "same_province", "label": "同省也行", "icon": "🗺️"},
                    {"value": "anywhere", "label": "不限", "icon": "🌍"},
                ],
            },
            "interests": {
                "question": "平时喜欢做什么呢？",
                "subtitle": "选择 3-5 个你最感兴趣的",
                "question_type": "tags",
                "options": [
                    {"value": "travel", "label": "旅行", "icon": "✈️"},
                    {"value": "food", "label": "美食", "icon": "🍜"},
                    {"value": "music", "label": "音乐", "icon": "🎵"},
                    {"value": "movie", "label": "电影", "icon": "🎬"},
                    {"value": "reading", "label": "阅读", "icon": "📚"},
                    {"value": "fitness", "label": "健身", "icon": "💪"},
                    {"value": "photography", "label": "摄影", "icon": "📷"},
                    {"value": "gaming", "label": "游戏", "icon": "🎮"},
                ],
            },
            "lifestyle": {
                "question": "理想的周末是怎样的？",
                "question_type": "single_choice",
                "options": [
                    {"value": "home", "label": "宅家休息", "icon": "🛋️"},
                    {"value": "explore", "label": "探索城市", "icon": "🌆"},
                    {"value": "nature", "label": "亲近自然", "icon": "🌲"},
                    {"value": "social", "label": "朋友聚会", "icon": "🎉"},
                ],
            },
            "values": {
                "question": "未来有什么规划吗？",
                "question_type": "single_choice",
                "options": [
                    {"value": "career_first", "label": "先拼事业", "icon": "💼"},
                    {"value": "family_first", "label": "家庭为重", "icon": "👨‍👩‍👧"},
                    {"value": "balance", "label": "两者平衡", "icon": "⚖️"},
                    {"value": "freedom", "label": "自由自在", "icon": "🕊️"},
                ],
            },
            "deal_breakers": {
                "question": "有什么是不能接受的吗？",
                "subtitle": "选择你的底线",
                "question_type": "multiple_choice",
                "options": [
                    {"value": "smoking", "label": "吸烟", "icon": "🚬"},
                    {"value": "drinking", "label": "酗酒", "icon": "🍺"},
                    {"value": "gambling", "label": "赌博", "icon": "🎰"},
                    {"value": "lazy", "label": "懒惰", "icon": "💤"},
                    {"value": "negative", "label": "负能量", "icon": "😤"},
                ],
            },
        }

        card = templates.get(dimension, templates["relationship_goal"])
        card["dimension"] = dimension
        return card

    def _generate_ai_message(self, dimension: str, trigger_reason: str) -> str:
        """生成 AI 引导语"""
        dimension_name = self.PROFILE_DIMENSIONS.get(dimension, {}).get("name", "信息")

        messages = {
            "user_intent": f"为了更好地帮你，我想了解一下你的{dimension_name}~",
            "matching_need": f"要帮你找到更合适的 TA，我需要知道你的{dimension_name}",
            "profile_update": f"更新一下你的{dimension_name}吧？",
            "explicit_request": f"好的，告诉我你的{dimension_name}吧~",
        }

        return messages.get(trigger_reason, f"和我说说你的{dimension_name}吧~")

    async def process_user_answer(
        self,
        user_id: str,
        dimension: str,
        answer: Any,
        profile: Optional[Dict] = None,
        current_depth: int = 0,
        context: Optional[List[Dict]] = None
    ) -> Dict:
        """
        处理用户的回答

        智能、克制的追问策略：
        - 根据维度重要性决定是否追问
        - 低重要性维度不追问
        - 高重要性维度适度追问，但不超过限制
        - 避免在单个问题上钻牛角尖

        Args:
            user_id: 用户 ID
            dimension: 信息维度
            answer: 用户选择的答案
            profile: 当前用户画像
            current_depth: 当前追问深度
            context: 对话上下文

        Returns:
            处理结果，包含 AI 回复、是否需要追问、下一个问题
        """
        logger.info(f"ProfileCollectionSkill: Processing answer for {dimension} from user={user_id}, depth={current_depth}")

        # 更新用户画像
        updated_profile = {**(profile or {}), dimension: answer}

        # 获取维度重要性
        dimension_info = self.PROFILE_DIMENSIONS.get(dimension, {})
        importance = dimension_info.get("importance", "medium")

        # Step 1: 分析回答深度
        depth_score, analysis = await self._analyze_answer_depth(
            dimension=dimension,
            answer=answer,
            context=context
        )

        logger.info(f"ProfileCollectionSkill: Answer depth = {depth_score}, importance = {importance}")

        # Step 2: 判断是否需要追问（智能、克制）
        need_follow_up = False

        # 低重要性维度不追问
        if importance == "low" and self.FOLLOW_UP_CONFIG["low_importance_no_follow_up"]:
            logger.info(f"ProfileCollectionSkill: Skipping follow-up for low importance dimension {dimension}")
            need_follow_up = False
        else:
            # 根据重要性决定最大追问深度
            if importance == "high":
                max_depth = self.FOLLOW_UP_CONFIG["high_importance_max_depth"]
                threshold = 0.4  # 高重要性：深度 < 0.4 才追问
            elif importance == "medium":
                max_depth = self.FOLLOW_UP_CONFIG["medium_importance_max_depth"]
                threshold = 0.5  # 中等重要性：深度 < 0.5 才追问
            else:
                max_depth = self.FOLLOW_UP_CONFIG["max_depth"]
                threshold = self.FOLLOW_UP_CONFIG["depth_threshold"]

            need_follow_up = (
                depth_score < threshold and
                current_depth < max_depth
            )

        # Step 3: 生成确认回复
        ai_message = self._generate_acknowledgment(dimension, answer)

        result = {
            "success": True,
            "ai_message": ai_message,
            "updated_profile": updated_profile,
            "answer_depth": depth_score,
            "need_follow_up": need_follow_up,
        }

        # Step 4: 如果需要追问，生成追问问题
        if need_follow_up:
            follow_up_card = await self._generate_follow_up_question(
                dimension=dimension,
                original_answer=answer,
                analysis=analysis,
                current_depth=current_depth + 1,
                context=context,
                importance=importance
            )
            if follow_up_card:
                result["next_question"] = follow_up_card
                result["is_follow_up"] = True
                return result

        # Step 5: 不需要追问，检查是否有其他信息缺口
        remaining_gaps = self._analyze_profile_gaps(updated_profile)
        result["has_more_questions"] = len(remaining_gaps) > 0

        # 如果还有其他缺口，准备下一个问题
        if remaining_gaps:
            next_dimension = remaining_gaps[0]["dimension"]
            next_card = await self._generate_question_card(
                dimension=next_dimension,
                context=context,
                profile=updated_profile,
            )
            result["next_question"] = next_card

        return result

    def _generate_acknowledgment(self, dimension: str, answer: Any) -> str:
        """生成确认回复"""
        dimension_name = self.PROFILE_DIMENSIONS.get(dimension, {}).get("name", "偏好")

        if isinstance(answer, list):
            answer_text = "、".join(str(a) for a in answer[:3])
            if len(answer) > 3:
                answer_text += f"等 {len(answer)} 个"
        else:
            answer_text = str(answer)

        # 简单的确认语
        templates = [
            f"收到，你选择了{answer_text}~",
            f"明白了，{answer_text}是个不错的选择！",
            f"好的，{answer_text}，我记下了~",
            f"了解，{answer_text}！",
        ]

        import random
        return random.choice(templates)


# 全局实例
_profile_collection_skill: Optional[ProfileCollectionSkill] = None


def get_profile_collection_skill() -> ProfileCollectionSkill:
    """获取 Skill 单例"""
    global _profile_collection_skill
    if _profile_collection_skill is None:
        _profile_collection_skill = ProfileCollectionSkill()
    return _profile_collection_skill