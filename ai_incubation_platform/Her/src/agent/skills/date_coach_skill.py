"""
约会教练 Skill - AI 约会军师

AI 约会顾问核心 Skill - 约会模拟、穿搭推荐、场所策略、话题锦囊
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from agent.skills.base import BaseSkill
from utils.logger import logger
import json
import random


class DateCoachSkill(BaseSkill):
    """
    AI 约会教练 Skill - 帮助你成为约会高手

    核心能力:
    - 约会模拟沙盒：与 AI 分身练习约会对话
    - 穿搭推荐：根据场合、天气、对方喜好推荐着装
    - 场所策略：推荐适合的约会地点
    - 话题锦囊：提供话题、破冰句、应对策略

    自主触发:
    - 约会前提醒和准备建议
    - 约会后复盘和改进建议
    - 检测到约会邀请时
    """

    name = "date_coach"
    version = "1.0.0"
    description = """
    AI 约会教练，帮助你成为约会高手

    能力:
    - 约会模拟沙盒：与 AI 分身练习各种约会场景
    - 穿搭推荐：根据场合、天气、对方喜好推荐着装
    - 场所策略：推荐适合的关系阶段约会地点
    - 话题锦囊：提供破冰话题、深度交流问题、应对策略
    - 实时指导：约会中的悄悄话建议
    """

    # 约会场景类型
    DATE_SCENARIOS = {
        "first_date": {
            "name": "初次约会",
            "goal": "建立良好第一印象，了解彼此",
            "duration": "1-2 小时",
            "budget": "中等",
            "pressure": "低"
        },
        "casual_date": {
            "name": "休闲约会",
            "goal": "放松相处，增进了解",
            "duration": "2-3 小时",
            "budget": "低至中等",
            "pressure": "低"
        },
        "romantic_date": {
            "name": "浪漫约会",
            "goal": "营造浪漫氛围，推进关系",
            "duration": "3-4 小时",
            "budget": "中高",
            "pressure": "中"
        },
        "adventure_date": {
            "name": "冒险约会",
            "goal": "共同体验刺激，创造回忆",
            "duration": "半天至一天",
            "budget": "中等",
            "pressure": "中"
        },
        "intimate_date": {
            "name": "亲密约会",
            "goal": "深度交流，增进亲密感",
            "duration": "2-4 小时",
            "budget": "低至中等",
            "pressure": "低"
        }
    }

    # 关系阶段适合的约会类型
    STAGE_APPROPRIATE_DATES = {
        "initial": ["casual_date"],
        "getting_to_know": ["first_date", "casual_date"],
        "attraction": ["casual_date", "adventure_date"],
        "dating": ["romantic_date", "adventure_date", "intimate_date"],
        "exclusive": ["romantic_date", "intimate_date"],
        "deepening": ["romantic_date", "intimate_date"],
        "commitment": ["romantic_date", "intimate_date"],
        "long_term": ["romantic_date", "adventure_date", "intimate_date"]
    }

    def get_input_schema(self) -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "用户 ID"
                },
                "partner_id": {
                    "type": "string",
                    "description": "约会对象 ID"
                },
                "service_type": {
                    "type": "string",
                    "enum": ["date_simulation", "outfit_recommendation", "venue_strategy", "topic_kit", "pre_date_prep", "post_date_review"],
                    "description": "服务类型"
                },
                "date_context": {
                    "type": "object",
                    "properties": {
                        "date_type": {"type": "string"},
                        "venue": {"type": "string"},
                        "time": {"type": "string"},
                        "weather": {"type": "string"},
                        "relationship_stage": {"type": "string"},
                        "partner_preferences": {"type": "object"}
                    }
                },
                "simulation_scenario": {
                    "type": "string",
                    "description": "模拟场景（用于约会模拟）"
                },
                "conversation_history": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "对话历史（用于模拟或复盘）"
                }
            },
            "required": ["user_id", "service_type"]
        }

    def get_output_schema(self) -> dict:
        """获取输出参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "ai_message": {"type": "string"},
                "coach_result": {
                    "type": "object",
                    "properties": {
                        "service_type": {"type": "string"},
                        "recommendations": {"type": "array"},
                        "simulation_feedback": {"type": "object"},
                        "outfit_suggestions": {"type": "array"},
                        "venue_recommendations": {"type": "array"},
                        "topic_kit": {"type": "object"},
                        "prep_checklist": {"type": "array"},
                        "review_summary": {"type": "object"}
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
            },
            "required": ["success", "ai_message", "coach_result"]
        }

    async def execute(
        self,
        user_id: str,
        service_type: str,
        partner_id: Optional[str] = None,
        date_context: Optional[Dict[str, Any]] = None,
        simulation_scenario: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None,
        **kwargs
    ) -> dict:
        """
        执行约会教练 Skill

        Args:
            user_id: 用户 ID
            service_type: 服务类型
            partner_id: 约会对象 ID
            date_context: 约会上下文
            simulation_scenario: 模拟场景
            conversation_history: 对话历史
            **kwargs: 额外参数

        Returns:
            Skill 执行结果
        """
        logger.info(f"DateCoachSkill: Executing for user={user_id}, type={service_type}")

        start_time = datetime.now()

        # Step 1: 根据服务类型执行教练功能
        coach_result = await self._perform_coaching(
            service_type=service_type,
            user_id=user_id,
            partner_id=partner_id,
            date_context=date_context,
            simulation_scenario=simulation_scenario,
            conversation_history=conversation_history
        )

        # Step 2: 生成自然语言建议
        ai_message = self._generate_message(coach_result, service_type)

        # Step 3: 构建 Generative UI
        generative_ui = self._build_ui(coach_result, service_type)

        # Step 4: 生成建议操作
        suggested_actions = self._generate_actions(coach_result, service_type)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "success": True,
            "ai_message": ai_message,
            "coach_result": coach_result,
            "generative_ui": generative_ui,
            "suggested_actions": suggested_actions,
            "skill_metadata": {
                "name": self.name,
                "version": self.version,
                "execution_time_ms": int(execution_time),
                "service_type": service_type
            }
        }

    async def _perform_coaching(
        self,
        service_type: str,
        user_id: str,
        partner_id: Optional[str],
        date_context: Optional[Dict],
        simulation_scenario: Optional[str],
        conversation_history: Optional[List[Dict]]
    ) -> Dict[str, Any]:
        """执行教练功能"""
        result = {
            "service_type": service_type,
            "recommendations": [],
            "simulation_feedback": None,
            "outfit_suggestions": [],
            "venue_recommendations": [],
            "topic_kit": {},
            "prep_checklist": [],
            "review_summary": None
        }

        try:
            if service_type == "date_simulation":
                # 约会模拟
                simulation_result = self._run_date_simulation(
                    user_id=user_id,
                    scenario=simulation_scenario,
                    conversation_history=conversation_history
                )
                result["simulation_feedback"] = simulation_result

            elif service_type == "outfit_recommendation":
                # 穿搭推荐
                outfit_suggestions = self._recommend_outfit(
                    date_context=date_context,
                    user_id=user_id
                )
                result["outfit_suggestions"] = outfit_suggestions

            elif service_type == "venue_strategy":
                # 场所策略
                venue_recommendations = self._recommend_venues(
                    date_context=date_context,
                    user_id=user_id,
                    partner_id=partner_id
                )
                result["venue_recommendations"] = venue_recommendations

            elif service_type == "topic_kit":
                # 话题锦囊
                topic_kit = self._generate_topic_kit(
                    date_context=date_context,
                    user_id=user_id,
                    partner_id=partner_id
                )
                result["topic_kit"] = topic_kit

            elif service_type == "pre_date_prep":
                # 约会前准备
                prep_checklist = self._generate_prep_checklist(
                    date_context=date_context
                )
                result["prep_checklist"] = prep_checklist
                result["topic_kit"] = self._generate_topic_kit(date_context, user_id, partner_id)

            elif service_type == "post_date_review":
                # 约会后复盘
                review_summary = self._review_date(
                    conversation_history=conversation_history,
                    date_context=date_context
                )
                result["review_summary"] = review_summary

            return result

        except Exception as e:
            logger.error(f"DateCoachSkill: Coaching failed: {e}")
            return result

    def _run_date_simulation(
        self,
        user_id: str,
        scenario: Optional[str],
        conversation_history: Optional[List[Dict]]
    ) -> Dict[str, Any]:
        """运行约会模拟"""
        # 默认场景
        if not scenario:
            scenario = "first_date"

        scenario_info = self.DATE_SCENARIOS.get(scenario, self.DATE_SCENARIOS["first_date"])

        # 模拟 AI 分身的回应
        ai_responses = self._generate_ai_responses(scenario, conversation_history)

        # 提供反馈
        feedback = self._generate_simulation_feedback(conversation_history, scenario)

        return {
            "scenario": scenario,
            "scenario_name": scenario_info["name"],
            "scenario_goal": scenario_info["goal"],
            "ai_responses": ai_responses,
            "feedback": feedback,
            "tips": self._get_scenario_tips(scenario)
        }

    def _generate_ai_responses(self, scenario: str, user_messages: Optional[List[Dict]]) -> List[Dict[str, Any]]:
        """生成 AI 分身的回应"""
        # 简化实现：预设回应
        responses = {
            "first_date": [
                {"context": "初次见面问候", "response": "你好呀！很高兴终于见面了~"},
                {"context": "聊兴趣爱好", "response": "哇，这个我也很喜欢！你平时都怎么玩？"},
                {"context": "询问工作", "response": "听起来很有意思，是什么让你选择这个行业的？"},
                {"context": "结束约会", "response": "今天很开心，希望下次还能见到你！"}
            ],
            "romantic_date": [
                {"context": "营造氛围", "response": "这里好美啊，和你一起来更美了"},
                {"context": "表达感受", "response": "和你在一起的时间总是过得这么快"},
                {"context": "肢体接触试探", "response": "*没有躲开，微微靠近*"}
            ]
        }

        return responses.get(scenario, responses["first_date"])

    def _generate_simulation_feedback(
        self,
        conversation_history: Optional[List[Dict]],
        scenario: str
    ) -> Dict[str, Any]:
        """生成模拟反馈"""
        if not conversation_history:
            return {
                "overall_score": 75,
                "strengths": ["态度友好", "善于倾听"],
                "areas_to_improve": ["可以多问开放性问题", "注意眼神交流"],
                "highlights": [],
                "suggestions": [
                    "约会中保持自然微笑",
                    "多问'为什么'类问题深入了解对方",
                    "注意不要一直看手机"
                ]
            }

        # 分析对话质量
        message_count = len(conversation_history)
        avg_length = sum(len(m.get("content", "")) for m in conversation_history) / max(message_count, 1)

        score = 70
        strengths = []
        improvements = []

        if message_count >= 10:
            score += 10
            strengths.append("互动频繁")
        if avg_length >= 30:
            score += 10
            strengths.append("对话深入")
        else:
            improvements.append("可以展开更多话题")

        return {
            "overall_score": min(score, 95),
            "strengths": strengths or ["态度友好"],
            "areas_to_improve": improvements or ["可以更多展示真实的自己"],
            "highlights": [],
            "suggestions": self._get_scenario_tips(scenario)
        }

    def _get_scenario_tips(self, scenario: str) -> List[str]:
        """获取场景提示"""
        tips = {
            "first_date": [
                "保持轻松自然，不要过于紧张",
                "多问开放性问题，了解对方",
                "注意倾听，不要只顾着说自己",
                "适当的眼神交流，展现诚意",
                "结束后及时表达感谢"
            ],
            "romantic_date": [
                "营造浪漫氛围，但不要过于刻意",
                "适时表达感受，但不要太急",
                "注意对方的肢体语言反馈",
                "准备一个小惊喜会加分"
            ],
            "casual_date": [
                "放松心态，享受当下",
                "找到共同兴趣点深入聊",
                "不要有太大压力，自然就好"
            ]
        }
        return tips.get(scenario, tips["first_date"])

    def _recommend_outfit(
        self,
        date_context: Optional[Dict],
        user_id: str
    ) -> List[Dict[str, Any]]:
        """推荐穿搭"""
        if not date_context:
            return self._get_default_outfit_recommendations()

        date_type = date_context.get("date_type", "first_date")
        weather = date_context.get("weather", "sunny")
        venue = date_context.get("venue", "restaurant")

        # 根据场合推荐
        outfit_base = {
            "first_date": {
                "style": "干净得体，展现最好的一面",
                "formality": "smart_casual"
            },
            "casual_date": {
                "style": "舒适自然，展现真实性格",
                "formality": "casual"
            },
            "romantic_date": {
                "style": "略有正式感，展现重视",
                "formality": "semi_formal"
            },
            "adventure_date": {
                "style": "方便活动，舒适为主",
                "formality": "sporty"
            }
        }

        base_info = outfit_base.get(date_type, outfit_base["first_date"])

        # 根据天气调整
        weather_adjustments = {
            "sunny": "注意防晒，选择透气材质",
            "rainy": "带伞，避免白色易湿透衣物",
            "cloudy": "温差可能大，带件外套",
            "cold": "保暖为主，但不要太臃肿"
        }

        suggestions = [
            {
                "type": "overall_style",
                "suggestion": base_info["style"],
                "formality": base_info["formality"]
            },
            {
                "type": "weather_tip",
                "suggestion": weather_adjustments.get(weather, "根据天气适当调整")
            },
            {
                "type": "grooming",
                "suggestion": "保持头发整洁，指甲修剪干净，淡香水即可"
            },
            {
                "type": "accessories",
                "suggestion": "简约为主，不要过于花哨"
            }
        ]

        # 性别特定建议
        suggestions.extend([
            {
                "type": "male_specific",
                "suggestion": "衬衫 + 休闲裤/牛仔裤，皮鞋或干净的运动鞋"
            },
            {
                "type": "female_specific",
                "suggestion": "连衣裙/上衣 + 半身裙，舒适的鞋子（可能要走路）"
            }
        ])

        return suggestions

    def _get_default_outfit_recommendations(self) -> List[Dict[str, Any]]:
        """获取默认穿搭建议"""
        return [
            {"type": "general", "suggestion": "初次约会建议 smart casual 风格"},
            {"type": "top", "suggestion": "衬衫或 Polo 衫，避免花哨图案"},
            {"type": "bottom", "suggestion": "休闲裤或牛仔裤，干净整洁"},
            {"type": "shoes", "suggestion": "皮鞋或干净的运动鞋"},
            {"type": "grooming", "suggestion": "保持头发整洁，指甲修剪干净"}
        ]

    def _recommend_venues(
        self,
        date_context: Optional[Dict],
        user_id: str,
        partner_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """推荐约会场所"""
        if not date_context:
            return self._get_default_venue_recommendations()

        relationship_stage = date_context.get("relationship_stage", "getting_to_know")
        budget = date_context.get("budget", "medium")
        location = date_context.get("location", "city_center")

        # 根据关系阶段推荐
        stage_venues = {
            "initial": [
                {"type": "coffee_shop", "name": "安静的咖啡馆", "reason": "轻松低压，方便交流"},
                {"type": "park", "name": "公园散步", "reason": "自然环境，边走边聊"}
            ],
            "getting_to_know": [
                {"type": "restaurant", "name": "特色餐厅", "reason": "美食话题，了解口味"},
                {"type": "museum", "name": "美术馆/博物馆", "reason": "共同体验，话题丰富"},
                {"type": "workshop", "name": "手作体验课", "reason": "互动合作，创造回忆"}
            ],
            "attraction": [
                {"type": "scenic_spot", "name": "观景台/夜景", "reason": "浪漫氛围，推进关系"},
                {"type": "concert", "name": "音乐会/Livehouse", "reason": "共同兴趣，情绪共鸣"},
                {"type": "theme_park", "name": "游乐园", "reason": "玩在一起，展现童心"}
            ],
            "dating": [
                {"type": "fine_dining", "name": "高级餐厅", "reason": "正式感，表达重视"},
                {"type": "weekend_trip", "name": "周边短途游", "reason": "独处时间，深入了解"},
                {"type": "cooking_class", "name": "料理课", "reason": "合作默契，居家预演"}
            ]
        }

        venues = stage_venues.get(relationship_stage, stage_venues["getting_to_know"])

        # 添加预算提示
        budget_tips = {
            "low": "选择性价比高的场所，真诚比花钱更重要",
            "medium": "中等预算，注重体验而非价格",
            "high": "预算充足，可以选择更有仪式感的场所"
        }

        result = []
        for venue in venues:
            venue["budget_tip"] = budget_tips.get(budget, budget_tips["medium"])
            result.append(venue)

        return result

    def _get_default_venue_recommendations(self) -> List[Dict[str, Any]]:
        """获取默认场所推荐"""
        return [
            {"type": "coffee_shop", "name": "咖啡馆", "reason": "适合初次见面，轻松无压力"},
            {"type": "restaurant", "name": "餐厅", "reason": "美食话题，了解彼此口味"},
            {"type": "activity", "name": "体验活动", "reason": "共同参与，创造回忆"}
        ]

    def _generate_topic_kit(
        self,
        date_context: Optional[Dict],
        user_id: str,
        partner_id: Optional[str]
    ) -> Dict[str, Any]:
        """生成话题锦囊"""
        if not date_context:
            return self._get_default_topic_kit()

        relationship_stage = date_context.get("relationship_stage", "getting_to_know")
        date_type = date_context.get("date_type", "first_date")

        # 根据关系阶段提供话题
        stage_topics = {
            "initial": {
                "icebreakers": [
                    "今天怎么过来的？路上还顺利吗？",
                    "这家店是你选的吗？有什么推荐的吗？",
                    "平时周末都喜欢做什么？"
                ],
                "safe_topics": ["兴趣爱好", "工作/学习", "美食", "旅行经历", "影视音乐"],
                "avoid_topics": ["前任", "收入", "敏感政治话题", "过于私人的问题"]
            },
            "getting_to_know": {
                "icebreakers": [
                    "上次你说的那个事情后来怎么样了？",
                    "最近有什么新鲜事想分享吗？"
                ],
                "deep_questions": [
                    "你理想中的生活是什么样的？",
                    "有什么事情是你一直坚持的？",
                    "最近有什么让你特别开心的事？"
                ],
                "safe_topics": ["未来规划", "价值观", "家庭观念", "生活习惯"],
                "avoid_topics": ["过早承诺", "过于严肃的话题"]
            },
            "attraction": {
                "flirty_lines": [
                    "和你在一起时间总是过得特别快",
                    "你今天看起来特别好看"
                ],
                "connection_builders": [
                    "我发现我们有很多共同点",
                    "你刚才说的那个想法很有意思"
                ]
            },
            "dating": {
                "relationship_topics": [
                    "我们对这段关系的期待是什么？",
                    "有什么是我可以做得更好的？"
                ],
                "future_planning": [
                    "下次我们可以一起去...",
                    "一直想和你一起尝试..."
                ]
            }
        }

        topics = stage_topics.get(relationship_stage, stage_topics["getting_to_know"])

        # 通用技巧
        topics["tips"] = [
            "多问开放性问题（为什么、怎么样）",
            "积极倾听，适时回应",
            "分享自己的感受，不要只问问题",
            "注意对方的肢体语言反馈"
        ]

        topics["emergency_exits"] = [
            "冷场时：'对了，我一直想问你...'",
            "尴尬时：'这个话题有点沉重，我们聊点轻松的'",
            "需要暂停：'我去下洗手间'"
        ]

        return topics

    def _get_default_topic_kit(self) -> Dict[str, Any]:
        """获取默认话题包"""
        return {
            "icebreakers": ["今天过得怎么样？", "最近有什么新鲜事？"],
            "safe_topics": ["兴趣爱好", "工作/学习", "美食", "旅行"],
            "tips": ["多倾听", "保持眼神交流", "真诚最重要"]
        }

    def _generate_prep_checklist(self, date_context: Optional[Dict]) -> List[Dict[str, Any]]:
        """生成约会前准备清单"""
        checklist = [
            {
                "category": "外表准备",
                "items": [
                    {"task": "洗头洗澡", "priority": "high", "done": False},
                    {"task": "修剪指甲", "priority": "high", "done": False},
                    {"task": "准备干净衣物", "priority": "high", "done": False},
                    {"task": "检查口气清新", "priority": "medium", "done": False}
                ]
            },
            {
                "category": "物品准备",
                "items": [
                    {"task": "手机充满电", "priority": "high", "done": False},
                    {"task": "准备纸巾/湿巾", "priority": "medium", "done": False},
                    {"task": "带现金/银行卡", "priority": "high", "done": False},
                    {"task": "准备小礼物（可选）", "priority": "low", "done": False}
                ]
            },
            {
                "category": "心理准备",
                "items": [
                    {"task": "放松心态，不要紧张", "priority": "high", "done": False},
                    {"task": "准备 2-3 个话题", "priority": "medium", "done": False},
                    {"task": "设定合理期待", "priority": "medium", "done": False}
                ]
            },
            {
                "category": "行程确认",
                "items": [
                    {"task": "确认时间地点", "priority": "high", "done": False},
                    {"task": "查看交通路线", "priority": "high", "done": False},
                    {"task": "提前 10 分钟到达", "priority": "high", "done": False},
                    {"task": "查看天气预报", "priority": "medium", "done": False}
                ]
            }
        ]

        # 根据约会类型调整
        if date_context:
            date_type = date_context.get("date_type", "first_date")
            if date_type == "romantic_date":
                checklist.append({
                    "category": "浪漫准备",
                    "items": [
                        {"task": "准备小惊喜", "priority": "medium", "done": False},
                        {"task": "想好表白/表达时机", "priority": "low", "done": False}
                    ]
                })

        return checklist

    def _review_date(
        self,
        conversation_history: Optional[List[Dict]],
        date_context: Optional[Dict]
    ) -> Dict[str, Any]:
        """约会后复盘"""
        if not conversation_history:
            return {
                "overall_rating": "N/A",
                "summary": "暂无足够数据进行复盘",
                "highlights": [],
                "areas_to_improve": ["下次可以准备更多话题"],
                "next_steps": ["主动联系，表达感谢"]
            }

        # 分析约会质量
        message_count = len(conversation_history)
        positive_indicators = 0
        negative_indicators = 0

        positive_words = ["开心", "高兴", "喜欢", "有趣", "好玩", "谢谢", "下次"]
        negative_words = ["尴尬", "无聊", "算了", "不"]

        for msg in conversation_history:
            content = msg.get("content", "")
            for word in positive_words:
                if word in content:
                    positive_indicators += 1
            for word in negative_words:
                if word in content:
                    negative_indicators += 1

        # 生成总结
        if positive_indicators > negative_indicators * 2:
            rating = "很好"
            summary = "约会进展顺利，对方反应积极"
        elif positive_indicators > negative_indicators:
            rating = "不错"
            summary = "约会整体良好，有一些亮点时刻"
        else:
            rating = "一般"
            summary = "约会有提升空间，不要气馁"

        return {
            "overall_rating": rating,
            "summary": summary,
            "positive_moments": positive_indicators,
            "concerning_moments": negative_indicators,
            "highlights": ["主动开启话题", "倾听对方分享"],
            "areas_to_improve": ["可以更多表达自己", "注意肢体语言"],
            "next_steps": [
                "24 小时内发送感谢消息",
                "表达想再见面的意愿",
                "提出具体的下次约会建议"
            ]
        }

    def _generate_message(self, coach_result: Dict, service_type: str) -> str:
        """生成自然语言建议"""
        if service_type == "date_simulation":
            feedback = coach_result.get("simulation_feedback", {})
            message = f"💪 约会模拟完成\n\n"
            message += f"场景：{feedback.get('scenario_name', '初次约会')}\n"
            message += f"综合评分：{feedback.get('overall_score', 0)}/100\n\n"
            message += f"优点：{', '.join(feedback.get('strengths', []))}\n"
            message += f"改进：{', '.join(feedback.get('areas_to_improve', []))}\n\n"
            message += f"小贴士：\n"
            for tip in feedback.get('tips', [])[:3]:
                message += f"- {tip}\n"
            return message

        elif service_type == "outfit_recommendation":
            suggestions = coach_result.get("outfit_suggestions", [])
            message = f"👔 穿搭建议\n\n"
            for sug in suggestions[:4]:
                message += f"{sug.get('type', '建议')}: {sug.get('suggestion', '')}\n"
            return message

        elif service_type == "venue_strategy":
            venues = coach_result.get("venue_recommendations", [])
            message = f"📍 约会场所推荐\n\n"
            for venue in venues[:3]:
                message += f"{venue.get('name', '场所')} ({venue.get('type', '')})\n"
                message += f"  理由：{venue.get('reason', '')}\n\n"
            return message

        elif service_type == "topic_kit":
            kit = coach_result.get("topic_kit", {})
            message = f"💬 话题锦囊\n\n"

            icebreakers = kit.get("icebreakers", [])
            if icebreakers:
                message += f"破冰话题：\n"
                for topic in icebreakers[:3]:
                    message += f"- {topic}\n"
                message += "\n"

            tips = kit.get("tips", [])
            if tips:
                message += f"聊天技巧：\n"
                for tip in tips[:3]:
                    message += f"- {tip}\n"
            return message

        elif service_type == "pre_date_prep":
            checklist = coach_result.get("prep_checklist", [])
            message = f"✅ 约会前准备清单\n\n"
            for category in checklist[:3]:
                message += f"【{category.get('category', '准备')}】\n"
                for item in category.get("items", [])[:3]:
                    status = "□" if not item.get("done") else "✓"
                    message += f"{status} {item.get('task', '')}\n"
                message += "\n"
            return message

        elif service_type == "post_date_review":
            review = coach_result.get("review_summary", {})
            message = f"📊 约会复盘\n\n"
            message += f"整体评价：{review.get('overall_rating', 'N/A')}\n"
            message += f"总结：{review.get('summary', '')}\n\n"

            next_steps = review.get("next_steps", [])
            if next_steps:
                message += f"下一步建议：\n"
                for step in next_steps[:3]:
                    message += f"- {step}\n"
            return message

        return "约会教练已就绪，随时为你提供帮助！"

    def _build_ui(self, coach_result: Dict, service_type: str) -> Dict[str, Any]:
        """构建 UI"""
        if service_type == "date_simulation":
            return {
                "component_type": "date_simulation_feedback",
                "props": coach_result.get("simulation_feedback", {})
            }
        elif service_type == "outfit_recommendation":
            return {
                "component_type": "outfit_recommendations",
                "props": {"suggestions": coach_result.get("outfit_suggestions", [])}
            }
        elif service_type == "venue_strategy":
            return {
                "component_type": "venue_recommendations",
                "props": {"venues": coach_result.get("venue_recommendations", [])}
            }
        elif service_type == "topic_kit":
            return {
                "component_type": "topic_kit",
                "props": coach_result.get("topic_kit", {})
            }
        elif service_type == "pre_date_prep":
            return {
                "component_type": "prep_checklist",
                "props": {"checklist": coach_result.get("prep_checklist", [])}
            }
        elif service_type == "post_date_review":
            return {
                "component_type": "date_review",
                "props": coach_result.get("review_summary", {})
            }
        return {"component_type": "coach_empty", "props": {}}

    def _generate_actions(self, coach_result: Dict, service_type: str) -> List[Dict[str, Any]]:
        """生成建议操作"""
        actions = []

        if service_type == "pre_date_prep":
            actions.append({
                "label": "开始准备",
                "action_type": "start_prep",
                "params": {}
            })
        elif service_type == "post_date_review":
            actions.append({
                "label": "发送感谢消息",
                "action_type": "send_thank_you",
                "params": {}
            })

        actions.append({
            "label": "获取更多建议",
            "action_type": "get_more_tips",
            "params": {}
        })

        return actions

    async def autonomous_trigger(
        self,
        user_id: str,
        trigger_type: str,
        partner_id: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> dict:
        """
        自主触发约会教练

        Args:
            user_id: 用户 ID
            trigger_type: 触发类型 (pre_date_reminder, post_date_followup, date_invite_detected)
            partner_id: 约会对象 ID
            context: 上下文信息

        Returns:
            触发结果
        """
        logger.info(f"DateCoachSkill: Autonomous trigger for user={user_id}, type={trigger_type}")

        should_trigger = False
        service_type = "pre_date_prep"

        if trigger_type == "pre_date_reminder":
            # 约会前提醒
            should_trigger = True
            service_type = "pre_date_prep"
        elif trigger_type == "post_date_followup":
            # 约会后跟进
            should_trigger = True
            service_type = "post_date_review"
        elif trigger_type == "date_invite_detected":
            # 检测到约会邀请
            should_trigger = True
            service_type = "venue_strategy"

        if should_trigger:
            result = await self.execute(
                user_id=user_id,
                service_type=service_type,
                partner_id=partner_id,
                date_context=context
            )
            return {
                "triggered": True,
                "result": result,
                "should_push": True
            }

        return {"triggered": False, "reason": "not_needed"}


# 全局 Skill 实例
_date_coach_skill_instance: Optional[DateCoachSkill] = None


def get_date_coach_skill() -> DateCoachSkill:
    """获取约会教练 Skill 单例实例"""
    global _date_coach_skill_instance
    if _date_coach_skill_instance is None:
        _date_coach_skill_instance = DateCoachSkill()
    return _date_coach_skill_instance
