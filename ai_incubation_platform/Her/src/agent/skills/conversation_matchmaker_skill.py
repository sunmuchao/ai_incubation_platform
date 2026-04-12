"""
Conversation Matchmaker Skill - 对话式匹配专家

AI 匹配专家核心 Skill - 意图理解、自主推荐、关系分析
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from agent.skills.base import BaseSkill
from utils.logger import logger


class ConversationMatchmakerSkill(BaseSkill):
    """
    AI 匹配专家 Skill - 对话式匹配与关系指导

    核心能力:
    - 意图理解：解析用户自然语言意图
    - 自主推荐：基于 AI 分析的个性化推荐
    - 关系分析：关系健康度检测和建议
    - 话题推荐：智能破冰话题生成

    自主触发:
    - 定期推送优质匹配
    - 关系异常预警
    - 长期未互动关系激活
    - 用户生日等特殊日期推荐
    """

    name = "conversation_matchmaker"
    version = "1.0.0"
    description = """
    AI 匹配专家，对话式匹配与关系指导

    能力:
    - 意图理解：解析用户自然语言意图
    - 自主推荐：基于 AI 分析的个性化推荐
    - 关系分析：关系健康度检测和建议
    - 话题推荐：智能破冰话题生成
    """

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "用户 ID"},
                "service_type": {
                    "type": "string",
                    "enum": ["intent_matching", "daily_recommend", "relationship_analysis", "topic_suggestion"],
                    "description": "服务类型"
                },
                "context": {
                    "type": "object",
                    "properties": {
                        "user_intent": {"type": "string", "description": "用户意图描述"},
                        "match_id": {"type": "string", "description": "匹配 ID"},
                        "analysis_type": {"type": "string", "description": "分析类型"},
                        "preferences": {"type": "object", "description": "偏好设置"}
                    }
                }
            },
            "required": ["user_id", "service_type"]
        }

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "ai_message": {"type": "string"},
                "matchmaker_result": {
                    "type": "object",
                    "properties": {
                        "service_type": {"type": "string"},
                        "matches": {"type": "array"},
                        "intent_analysis": {"type": "object"},
                        "relationship_report": {"type": "object"},
                        "topics": {"type": "array"},
                        "recommendations": {"type": "array"}
                    }
                },
                "generative_ui": {"type": "object"},
                "suggested_actions": {"type": "array"}
            },
            "required": ["success", "ai_message", "matchmaker_result"]
        }

    async def execute(
        self,
        user_id: str,
        service_type: str = None,
        context: Optional[Dict[str, Any]] = None,
        action: str = None,  # 前端兼容参数
        intent_text: str = None,  # 前端兼容参数
        **kwargs
    ) -> dict:
        # 参数兼容映射：前端 action -> 后端 service_type
        if service_type is None and action is not None:
            service_type = self._map_action_to_service_type(action)

        if service_type is None:
            # 默认使用意图匹配
            service_type = "intent_matching"

        # 如果有 intent_text，注入到 context
        if intent_text and context is None:
            context = {"user_intent": intent_text}
        elif intent_text and context:
            context["user_intent"] = intent_text

        logger.info(f"ConversationMatchmakerSkill: Executing for user={user_id}, type={service_type}")

        start_time = datetime.now()

        # 根据服务类型提供匹配服务（改为异步调用）
        result = await self._provide_matching_service(service_type, user_id, context)

        ai_message = self._generate_message(result, service_type)
        generative_ui = self._build_ui(result, service_type)
        suggested_actions = self._generate_actions(service_type)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "success": True,
            "ai_message": ai_message,
            "matchmaker_result": result,
            "generative_ui": generative_ui,
            "suggested_actions": suggested_actions,
            "skill_metadata": {
                "name": self.name,
                "version": self.version,
                "execution_time_ms": int(execution_time)
            }
        }

    async def _provide_matching_service(
        self,
        service_type: str,
        user_id: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """提供匹配服务"""
        result = {
            "service_type": service_type,
            "matches": [],
            "intent_analysis": {},
            "relationship_report": {},
            "topics": [],
            "recommendations": []
        }

        if service_type == "intent_matching":
            result["intent_analysis"] = await self._parse_intent(context)
            result["matches"] = self._execute_intent_matching(user_id, result["intent_analysis"])
            result["recommendations"] = self._generate_matching_recommendations(result["matches"])

        elif service_type == "daily_recommend":
            result["matches"] = self._generate_daily_recommendations(user_id, context)
            result["recommendations"] = self._generate_daily_tips()

        elif service_type == "relationship_analysis":
            result["relationship_report"] = self._analyze_relationship(user_id, context)
            result["recommendations"] = self._generate_relationship_recommendations(result["relationship_report"])

        elif service_type == "topic_suggestion":
            result["topics"] = self._generate_topics(user_id, context)
            result["recommendations"] = self._generate_topic_tips()

        return result

    async def _parse_intent(self, context: Optional[Dict]) -> Dict[str, Any]:
        """
        解析用户意图

        使用 LLM 进行深度语义理解，识别用户的真实意图，
        而非硬编码的关键词匹配。
        """
        user_intent = (context or {}).get("user_intent", "")
        user_id = (context or {}).get("user_id", "")

        logger.info(f"ConversationMatchmakerSkill: Parsing intent with LLM: {user_intent[:50]}...")

        # 尝试使用 LLM 进行意图识别
        try:
            from services.llm_semantic_service import get_llm_semantic_service
            import asyncio

            llm_service = get_llm_semantic_service()

            # 构建意图分类 prompt
            intent_prompt = f"""
你是一个专业的婚恋匹配助手 Her，请分析用户的真实意图。

用户输入："{user_intent}"

请分析：
1. 用户的核心意图是什么？
2. 用户是否有明确的偏好条件？（年龄/地区/兴趣/学历等）
3. 用户想要多少个推荐？
4. 用户的语气和情绪状态如何？

请返回严格的 JSON 格式：
{{
    "intent_type": "serious_relationship/daily_browse/interest_based/location_based/education_based/relationship_analysis/topic_suggestion/date_planning/icebreaker/capability_inquiry/general",
    "limit": 5,
    "min_score": 0.6,
    "preferences": {{
        "interests": [],
        "location_priority": "nearby/any",
        "education_priority": "high/any",
        "age_range": {{ "min": 0, "max": 100 }}
    }},
    "emotional_state": "normal/excited/anxious/lonely/confident",
    "suggestions": []
}}

意图类型说明：
- serious_relationship: 用户想找对象、认真谈恋爱、结婚
- daily_browse: 用户想看看推荐、浏览
- interest_based: 用户提到兴趣爱好（旅行、运动等）
- location_based: 用户提到地点（附近、同城等）
- education_based: 用户提到学历要求
- relationship_analysis: 用户想分析现有关系
- topic_suggestion: 用户想要聊天话题
- date_planning: 用户想策划约会
- icebreaker: 用户想了解如何开启对话
- capability_inquiry: 用户询问你能做什么、你的功能、介绍你自己
- general: 其他一般意图

注意：
- 如果用户问"你能干什么"、"你有什么功能"、"介绍一下你自己"，属于 capability_inquiry
- 如果用户说"找对象"/"谈恋爱"，属于 serious_relationship
- 如果用户提到地点，属于 location_based
- 如果用户提到兴趣，属于 interest_based
"""

            # 异步调用 LLM（添加超时保护）
            try:
                llm_response = await asyncio.wait_for(
                    llm_service._call_llm(intent_prompt),
                    timeout=10.0  # 10秒超时
                )
            except asyncio.TimeoutError:
                logger.warning("ConversationMatchmakerSkill: LLM timeout, using fallback")
                return self._parse_intent_fallback(user_intent)

            # 解析 LLM 响应
            import json
            llm_result = json.loads(llm_response)

            # 构建结果
            analysis = {
                "intent_type": llm_result.get("intent_type", "general"),
                "limit": llm_result.get("limit", 5),
                "min_score": llm_result.get("min_score", 0.6),
                "preferences": llm_result.get("preferences", {}),
                "suggestions": self._generate_intent_suggestions(llm_result),
                "emotional_state": llm_result.get("emotional_state", "normal"),
                "is_llm_analyzed": True
            }

            logger.info(f"ConversationMatchmakerSkill: LLM parsed intent: {analysis['intent_type']}")

            return analysis

        except Exception as e:
            logger.warning(f"ConversationMatchmakerSkill: LLM intent parsing failed: {e}, using fallback")
            # 降级到关键词匹配
            return self._parse_intent_fallback(user_intent)

    def _generate_intent_suggestions(self, llm_result: Dict) -> List[str]:
        """根据 LLM 分析结果生成建议"""
        suggestions = []
        intent_type = llm_result.get("intent_type", "general")

        intent_suggestions = {
            "serious_relationship": "基于关系目标的严肃匹配",
            "daily_browse": "每日精选推荐",
            "interest_based": "基于兴趣的匹配",
            "location_based": "基于地理位置的匹配",
            "education_based": "基于学历的匹配",
            "relationship_analysis": "关系健康度分析",
            "topic_suggestion": "智能话题推荐",
            "date_planning": "约会策划建议",
            "icebreaker": "破冰话题建议",
            "general": "智能匹配推荐",  # 添加 general 类型
        }

        if intent_type in intent_suggestions:
            suggestions.append(intent_suggestions[intent_type])

        # 确保至少有一个建议
        if not suggestions:
            suggestions.append("寻找匹配对象")

        # 添加情绪相关的建议
        emotional_state = llm_result.get("emotional_state", "normal")
        if emotional_state == "lonely":
            suggestions.append("感受到你可能有些孤单，我会用心为你寻找懂你的 TA")
        elif emotional_state == "excited":
            suggestions.append("感受到你的期待，让我们一起开启这段缘分~")

        return suggestions

    def _map_action_to_service_type(self, action: str) -> str:
        """
        参数兼容映射：将前端的 action 参数转换为后端的 service_type

        前端 action 值:
        - match_by_intent -> intent_matching
        - daily_recommend -> daily_recommend
        - suggest_topics -> topic_suggestion
        - analyze_compatibility -> relationship_analysis
        """
        action_mapping = {
            "match_by_intent": "intent_matching",
            "daily_recommend": "daily_recommend",
            "suggest_topics": "topic_suggestion",
            "analyze_compatibility": "relationship_analysis",
            # 直接匹配（前端可能直接传 service_type）
            "intent_matching": "intent_matching",
            "relationship_analysis": "relationship_analysis",
            "topic_suggestion": "topic_suggestion",
        }
        mapped = action_mapping.get(action, "intent_matching")
        logger.debug(f"ConversationMatchmakerSkill: Mapped action '{action}' -> service_type '{mapped}'")
        return mapped

    def _parse_intent_fallback(self, user_intent: str) -> Dict[str, Any]:
        """
        # ==================== FALLBACK 方案 ====================
        # 此方法仅在 LLM 不可用时作为降级方案使用。
        # 主要意图识别应通过 _parse_intent_with_llm() 进行 AI 分析。
        # =======================================================

        降级意图识别（当 LLM 不可用时）
        """
        intent_lower = user_intent.lower() if user_intent else ""

        analysis = {
            "intent_type": "general",
            "limit": 5,
            "min_score": 0.6,
            "preferences": {},
            "suggestions": ["基于 AI 的智能匹配推荐"],
            "is_llm_analyzed": False
        }

        # 识别意图类型
        # 能力询问 - 用户问"你能干什么"
        if any(phrase in intent_lower for phrase in ["你能干", "你能做", "你有什么功能", "你是谁", "介绍你自己", "你能帮我"]):
            analysis["intent_type"] = "capability_inquiry"
            analysis["suggestions"] = ["能力介绍"]
            return analysis

        if any(word in user_intent for word in ["找对象", "谈恋爱", "认真"]):
            analysis["intent_type"] = "serious_relationship"
            analysis["min_score"] = 0.6  # 降低阈值以获取更多推荐
            analysis["suggestions"].append("基于关系目标的严肃匹配")

        if any(word in user_intent for word in ["看看", "每日", "每天"]):
            analysis["intent_type"] = "daily_browse"
            analysis["suggestions"].append("每日精选推荐")

        if "旅行" in user_intent or "旅游" in user_intent:
            analysis["intent_type"] = "interest_based"
            analysis["suggestions"].append("基于旅行兴趣的匹配")
            analysis["preferences"]["interests"] = ["旅行", "旅游"]

        if "附近" in user_intent or "同城" in user_intent or "本地" in user_intent:
            analysis["intent_type"] = "location_based"
            analysis["suggestions"].append("基于地理位置的匹配")
            analysis["preferences"]["location_priority"] = "nearby"

        # 提取数量意图
        if "三个" in user_intent or "3 个" in user_intent:
            analysis["limit"] = 3
        elif "十个" in user_intent or "10 个" in user_intent:
            analysis["limit"] = 10

        return analysis

    def _execute_intent_matching(self, user_id: str, intent_analysis: Dict) -> List[Dict]:
        """执行意图匹配"""
        # 模拟匹配结果
        return [
            {
                "user_id": "user-001",
                "name": "小美",
                "age": 26,
                "occupation": "UI 设计师",
                "location": "北京市朝阳区",
                "avatar": "https://example.com/avatar1.jpg",
                "score": 0.92,
                "match_reasons": [
                    "你们都热爱旅行，去过很多相同的地方",
                    "性格互补指数 85%",
                    "对关系的期望一致"
                ],
                "common_interests": ["旅行", "摄影", "美食"],
                "compatibility": {
                    "interests": 0.88,
                    "personality": 0.85,
                    "values": 0.90,
                    "lifestyle": 0.82
                }
            },
            {
                "user_id": "user-002",
                "name": "小雨",
                "age": 24,
                "occupation": "产品经理",
                "location": "北京市海淀区",
                "avatar": "https://example.com/avatar2.jpg",
                "score": 0.87,
                "match_reasons": [
                    "同为互联网从业者，有共同语言",
                    "都喜欢看电影，品味相似",
                    "生活方式匹配度高"
                ],
                "common_interests": ["电影", "阅读", "咖啡"],
                "compatibility": {
                    "interests": 0.82,
                    "personality": 0.78,
                    "values": 0.85,
                    "lifestyle": 0.88
                }
            },
            {
                "user_id": "user-003",
                "name": "小雪",
                "age": 25,
                "occupation": "高中教师",
                "location": "北京市东城区",
                "avatar": "https://example.com/avatar3.jpg",
                "score": 0.83,
                "match_reasons": [
                    "性格温和，容易相处",
                    "都喜欢安静的生活方式",
                    "对未来规划相似"
                ],
                "common_interests": ["阅读", "旅行", "烹饪"],
                "compatibility": {
                    "interests": 0.75,
                    "personality": 0.88,
                    "values": 0.82,
                    "lifestyle": 0.85
                }
            }
        ]

    def _generate_daily_recommendations(self, user_id: str, context: Optional[Dict]) -> List[Dict]:
        """生成每日推荐"""
        return [
            {
                "user_id": "user-001",
                "name": "小美",
                "age": 26,
                "occupation": "UI 设计师",
                "avatar": "https://example.com/avatar1.jpg",
                "score": 0.92,
                "daily_reason": "今天的新推荐！她刚更新了动态",
                "highlight": "你们有 3 个共同兴趣",
                "icebreaker": "看到她最近去了云南旅行，你也喜欢那里吗？"
            },
            {
                "user_id": "user-004",
                "name": "小雅",
                "age": 27,
                "occupation": "市场经理",
                "avatar": "https://example.com/avatar4.jpg",
                "score": 0.88,
                "daily_reason": "高匹配度推荐",
                "highlight": "同是天蝎座，性格匹配度高",
                "icebreaker": "她喜欢品鉴咖啡，你知道哪家咖啡馆不错吗？"
            },
            {
                "user_id": "user-005",
                "name": "小文",
                "age": 25,
                "occupation": "编辑",
                "avatar": "https://example.com/avatar5.jpg",
                "score": 0.85,
                "daily_reason": "活跃用户推荐",
                "highlight": "文艺青年，喜欢写作和阅读",
                "icebreaker": "最近有看什么好书吗？她可以给你推荐"
            }
        ]

    def _analyze_relationship(self, user_id: str, context: Optional[Dict]) -> Dict[str, Any]:
        """分析关系"""
        match_id = (context or {}).get("match_id", "match-001")

        return {
            "match_id": match_id,
            "partner": {
                "name": "小美",
                "avatar": "https://example.com/avatar1.jpg"
            },
            "current_stage": "chatting",
            "stage_progress": 0.45,
            "health_score": 0.78,
            "health_level": "良好",
            "interaction_stats": {
                "total_messages": 156,
                "avg_response_time": "15 分钟",
                "chat_frequency": "每天 2-3 次",
                "last_interaction": "2 小时前"
            },
            "relationship_timeline": [
                {"event": "匹配成功", "date": "2026-03-15", "completed": True},
                {"event": "首次聊天", "date": "2026-03-16", "completed": True},
                {"event": "交换微信", "date": "2026-03-25", "completed": True},
                {"event": "首次约会", "date": "2026-04-05", "completed": True},
                {"event": "确定关系", "date": "未达成", "completed": False}
            ],
            "potential_issues": [
                {
                    "issue_type": "response_delay",
                    "description": "最近回复速度变慢",
                    "severity": "low",
                    "suggestion": "可能对方比较忙，可以关心一下"
                }
            ],
            "strengths": [
                "聊天氛围轻松愉快",
                "有较多共同话题",
                "双方都表达了见面意愿"
            ],
            "next_milestone": {
                "name": "第二次约会",
                "suggestion": "可以开始规划下一次见面了",
                "optimal_timing": "本周内"
            }
        }

    def _generate_topics(self, user_id: str, context: Optional[Dict]) -> List[Dict]:
        """生成话题建议"""
        match_id = (context or {}).get("match_id", "match-001")
        chat_context = (context or {}).get("context", "first_chat")

        return [
            {
                "category": "轻松破冰",
                "topics": [
                    {
                        "topic": "今天过得怎么样？有什么有趣的事情吗？",
                        "context": "日常问候，适合开启对话",
                        "follow_up": "如果对方提到具体的事，可以深入询问细节"
                    },
                    {
                        "topic": "最近有看什么好看的电影/剧吗？",
                        "context": "娱乐话题，容易找到共同语言",
                        "follow_up": "可以讨论剧情、演员、推荐彼此"
                    }
                ]
            },
            {
                "category": "兴趣探索",
                "topics": [
                    {
                        "topic": "你平时周末最喜欢做什么？",
                        "context": "了解对方的生活方式",
                        "follow_up": "可以分享自己的周末安排，寻找共同点"
                    },
                    {
                        "topic": "你去过最难忘的旅行地是哪里？",
                        "context": "旅行话题可以了解价值观和经历",
                        "follow_up": "分享彼此的旅行故事和照片"
                    }
                ]
            },
            {
                "category": "深度交流",
                "topics": [
                    {
                        "topic": "你觉得理想的生活状态是什么样的？",
                        "context": "适合关系深入后探讨未来",
                        "follow_up": "可以讨论各自的人生规划和目标"
                    },
                    {
                        "topic": "工作中最有成就感的是什么？",
                        "context": "了解对方的职业价值观",
                        "follow_up": "分享彼此的职业经历和感悟"
                    }
                ]
            },
            {
                "category": "暧昧互动",
                "topics": [
                    {
                        "topic": "你相信一见钟情吗？",
                        "context": "带一点暧昧的问题，试探对方态度",
                        "follow_up": "根据对方反应调整后续话题"
                    },
                    {
                        "topic": "你觉得我们有哪些相似的地方？",
                        "context": "引导对方思考两人的连接",
                        "follow_up": "可以顺势表达对对方的好感"
                    }
                ]
            }
        ]

    def _generate_matching_recommendations(self, matches: List[Dict]) -> List[Dict]:
        """生成匹配建议"""
        recommendations = []

        if matches:
            top_match = matches[0]
            recommendations.append({
                "type": "top_pick",
                "priority": "high",
                "title": f"重点推荐：{top_match['name']}",
                "suggestion": f"匹配度{top_match['score']*100:.0f}%，建议优先联系",
                "action": "contact_top_match"
            })

        recommendations.append({
            "type": "engagement",
            "priority": "medium",
            "title": "主动出击",
            "suggestion": "看到心仪的对象，主动打招呼成功率更高",
            "action": "send_greeting"
        })

        return recommendations

    def _generate_daily_tips(self) -> List[Dict]:
        """生成每日小贴士"""
        return [
            {
                "tip": "完善个人资料可以提升匹配质量",
                "description": "上传清晰照片、填写详细自我介绍"
            },
            {
                "tip": "每天登录可以增加曝光机会",
                "description": "活跃用户更容易被看到"
            },
            {
                "tip": "真诚是最好的交友方式",
                "description": "不要刻意迎合，做真实的自己"
            }
        ]

    def _generate_relationship_recommendations(self, report: Dict) -> List[Dict]:
        """生成关系建议"""
        recommendations = []

        health_score = report.get("health_score", 0)
        if health_score >= 0.8:
            recommendations.append({
                "type": "encouragement",
                "priority": "medium",
                "title": "关系发展良好",
                "suggestion": "继续保持真诚沟通，可以规划下一次见面",
                "action": "plan_next_date"
            })
        elif health_score >= 0.6:
            recommendations.append({
                "type": "improvement",
                "priority": "medium",
                "title": "关系稳定",
                "suggestion": "可以尝试增加互动频率，加深了解",
                "action": "increase_interaction"
            })
        else:
            recommendations.append({
                "type": "attention",
                "priority": "high",
                "title": "关系需要关注",
                "suggestion": "建议主动联系对方，重新建立连接",
                "action": "reconnect"
            })

        # 基于下一步建议
        next_milestone = report.get("next_milestone", {})
        if next_milestone:
            recommendations.append({
                "type": "milestone",
                "priority": "medium",
                "title": f"下一里程碑：{next_milestone.get('name')}",
                "suggestion": next_milestone.get('suggestion', ''),
                "action": "achieve_milestone"
            })

        return recommendations

    def _generate_topic_tips(self) -> List[Dict]:
        """生成话题技巧"""
        return [
            {
                "tip": "多问开放性问题",
                "description": "用'什么'、'为什么'、'怎么样'开头，鼓励对方分享"
            },
            {
                "tip": "积极倾听比会说更重要",
                "description": "给予回应、复述对方的话，让对方感受到被理解"
            },
            {
                "tip": "适当自我披露",
                "description": "分享一些自己的故事和感受，增进亲密度"
            }
        ]

    def _generate_message(self, result: Dict, service_type: str) -> str:
        """生成自然语言解读"""
        if service_type == "intent_matching":
            matches = result.get("matches", [])
            intent = result.get("intent_analysis", {})

            # 安全获取第一个 suggestion
            suggestions = intent.get("suggestions", ['寻找匹配对象'])
            first_suggestion = suggestions[0] if suggestions else '寻找匹配对象'

            message = f"🔍 理解到你的需求：{first_suggestion}\n\n"
            message += f"为你找到 {len(matches)} 位潜在匹配对象：\n\n"

            for i, match in enumerate(matches[:3], 1):
                message += f"{i}. {match['name']}，{match['age']}岁，{match['occupation']}\n"
                message += f"   匹配度：{match['score']*100:.0f}%\n"
                message += f"   共同兴趣：{', '.join(match.get('common_interests', [])[:3])}\n"
                if match.get('match_reasons'):
                    message += f"   推荐理由：{match['match_reasons'][0]}\n"
                message += "\n"

            return message

        elif service_type == "daily_recommend":
            matches = result.get("matches", [])
            message = "🌟 每日精选推荐\n\n"
            message += f"今天为你找到 {len(matches)} 位优质对象：\n\n"

            for match in matches[:3]:
                message += f"【{match['name']}】{match['age']}岁，{match['occupation']}\n"
                message += f"匹配度：{match['score']*100:.0f}%\n"
                message += f"推荐理由：{match.get('daily_reason', '')}\n"
                message += f"亮点：{match.get('highlight', '')}\n"
                message += f"💡 破冰建议：{match.get('icebreaker', '')}\n\n"

            return message

        elif service_type == "relationship_analysis":
            report = result.get("relationship_report", {})
            message = f"📊 关系健康度报告\n\n"
            message += f"当前阶段：{self._get_stage_name(report.get('current_stage', ''))}\n"
            message += f"健康度：{report.get('health_score', 0)*100:.0f}% ({report.get('health_level', '')})\n\n"

            message += "互动统计：\n"
            stats = report.get("interaction_stats", {})
            message += f"• 总消息数：{stats.get('total_messages', 0)}\n"
            message += f"• 平均回复：{stats.get('avg_response_time', '未知')}\n"
            message += f"• 聊天频率：{stats.get('chat_frequency', '未知')}\n"
            message += f"• 最近互动：{stats.get('last_interaction', '未知')}\n\n"

            if report.get("strengths"):
                message += "优势：\n"
                for strength in report["strengths"][:3]:
                    message += f"✓ {strength}\n"

            if report.get("potential_issues"):
                message += "\n需要注意：\n"
                for issue in report["potential_issues"][:2]:
                    message += f"⚠ {issue.get('description', '')}\n"

            next_ms = report.get("next_milestone", {})
            if next_ms:
                message += f"\n🎯 下一目标：{next_ms.get('name')}\n"
                message += f"建议：{next_ms.get('suggestion', '')}"

            return message

        elif service_type == "topic_suggestion":
            topics = result.get("topics", [])
            message = "💬 智能话题推荐\n\n"

            for category in topics[:3]:
                message += f"【{category.get('category', '话题')}】\n"
                for topic in category.get('topics', [])[:2]:
                    message += f"• {topic.get('topic', '')}\n"
                    message += f"  （{topic.get('context', '')}）\n"
                message += "\n"

            tips = result.get("recommendations", [])
            if tips:
                message += "💡 聊天小贴士：\n"
                for tip in tips[:2]:
                    message += f"- {tip.get('tip', '')}\n"

            return message

        return "匹配服务已完成"

    def _get_stage_name(self, stage: str) -> str:
        """获取关系阶段中文名"""
        names = {
            "matched": "匹配成功",
            "chatting": "聊天中",
            "exchanged_contacts": "已交换联系方式",
            "first_date": "已首次约会",
            "dating": "交往中",
            "in_relationship": "确定关系"
        }
        return names.get(stage, stage)

    def _build_ui(self, result: Dict, service_type: str) -> Dict[str, Any]:
        """构建 UI"""
        return {
            "component_type": "conversation_matchmaker_dashboard",
            "props": {
                "service_type": service_type,
                "data": result
            }
        }

    def _generate_actions(self, service_type: str) -> List[Dict[str, Any]]:
        """生成建议操作"""
        actions = [
            {"label": "查看详细报告", "action_type": "view_full_report", "params": {}},
            {"label": "保存分析结果", "action_type": "save_analysis", "params": {}}
        ]

        if service_type == "intent_matching":
            actions.extend([
                {"label": "联系最匹配", "action_type": "contact_top_match", "params": {}},
                {"label": "浏览更多", "action_type": "browse_more", "params": {}}
            ])
        elif service_type == "relationship_analysis":
            actions.append({"label": "发送消息", "action_type": "send_message", "params": {}})
        elif service_type == "topic_suggestion":
            actions.append({"label": "复制话题", "action_type": "copy_topics", "params": {}})

        return actions

    async def autonomous_trigger(
        self,
        user_id: str,
        trigger_type: str,
        context: Optional[Dict] = None
    ) -> dict:
        """自主触发"""
        logger.info(f"ConversationMatchmakerSkill: Autonomous trigger for user={user_id}, type={trigger_type}")

        if trigger_type == "daily_recommend":
            result = await self.execute(
                user_id=user_id,
                service_type="daily_recommend",
                context=context
            )
            has_matches = len(result.get("matches", [])) > 0
            return {"triggered": has_matches, "result": result, "should_push": has_matches}

        elif trigger_type == "relationship_check":
            result = await self.execute(
                user_id=user_id,
                service_type="relationship_analysis",
                context=context
            )
            health_score = result.get("matchmaker_result", {}).get("relationship_report", {}).get("health_score", 1)
            should_push = health_score < 0.6  # 健康度低时推送提醒
            return {"triggered": True, "result": result, "should_push": should_push}

        elif trigger_type == "inactive_match_reminder":
            result = await self.execute(
                user_id=user_id,
                service_type="relationship_analysis",
                context=context
            )
            return {"triggered": True, "result": result, "should_push": True}

        return {"triggered": False, "reason": "not_needed"}


# 全局 Skill 实例
_conversation_matchmaker_skill_instance: Optional[ConversationMatchmakerSkill] = None


def get_conversation_matchmaker_skill() -> ConversationMatchmakerSkill:
    """获取对话式匹配专家 Skill 单例实例"""
    global _conversation_matchmaker_skill_instance
    if _conversation_matchmaker_skill_instance is None:
        _conversation_matchmaker_skill_instance = ConversationMatchmakerSkill()
    return _conversation_matchmaker_skill_instance
