"""
关系教练 Skill

关系维护教练 - 帮助用户维护关系
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from agent.skills.base import BaseSkill
from utils.logger import logger


class RelationshipCoachSkill:
    """
    关系教练 Skill

    核心能力:
    - 监测关系健康度
    - 识别矛盾预警信号
    - 提供沟通建议
    - 策划约会活动
    - 送礼建议
    - 关系压力测试（替代已删除的 relationship_stress_test API）

    自主触发条件:
    - 沟通频率下降 > 50%
    - 检测到负面关键词
    - 纪念日临近
    - 关系里程碑达成
    """

    name = "relationship_coach"
    version = "1.1.0"
    description = """
    关系维护教练

    能力:
    - 监测关系健康度
    - 识别矛盾预警信号
    - 提供沟通建议
    - 策划约会活动
    - 送礼建议
    - 关系压力测试
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
                "partner_id": {
                    "type": "string",
                    "description": "伴侣用户 ID"
                },
                "action": {
                    "type": "string",
                    "enum": ["health_check", "get_advice", "plan_date", "gift_suggestion", "stress_test", "stress_test_answer", "stress_test_result"],
                    "description": "操作类型"
                },
                "context": {
                    "type": "object",
                    "properties": {
                        "issue_type": {"type": "string"},
                        "occasion": {"type": "string"},
                        "budget": {"type": "number"},
                        "scenario_type": {"type": "string"},
                        "relationship_stage": {"type": "string"},
                        "test_id": {"type": "string"},
                        "question_id": {"type": "string"},
                        "selected_option": {"type": "string"}
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
                "ai_message": {"type": "string"},
                "health_score": {"type": "number"},
                "issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "severity": {"type": "string"},
                            "description": {"type": "string"}
                        }
                    }
                },
                "recommendations": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "date_plans": {
                    "type": "array",
                    "items": {"type": "object"}
                },
                "gift_suggestions": {
                    "type": "array",
                    "items": {"type": "object"}
                },
                # 压力测试相关
                "test_id": {"type": "string"},
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question_id": {"type": "string"},
                            "scenario_description": {"type": "string"},
                            "options": {"type": "array"},
                            "difficulty": {"type": "integer"},
                            "key_insight": {"type": "string"}
                        }
                    }
                },
                "analysis": {"type": "object"},
                "summary": {"type": "object"}
            }
        }

    async def execute(
        self,
        match_id: str,
        action: str,
        user_id: Optional[str] = None,
        partner_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> dict:
        """
        执行关系教练 Skill

        Args:
            match_id: 匹配记录 ID
            action: 操作类型
            user_id: 用户 ID
            partner_id: 伴侣用户 ID
            context: 上下文信息
            **kwargs: 额外参数

        Returns:
            Skill 执行结果
        """
        logger.info(f"RelationshipCoachSkill: action={action}, match_id={match_id}")

        if action == "health_check":
            return await self._health_check(match_id, context)
        elif action == "get_advice":
            return await self._get_advice(match_id, context)
        elif action == "plan_date":
            return await self._plan_date(match_id, context)
        elif action == "gift_suggestion":
            return await self._gift_suggestion(match_id, context)
        elif action == "stress_test":
            return await self._stress_test(user_id, partner_id, context)
        elif action == "stress_test_answer":
            return await self._stress_test_answer(context)
        elif action == "stress_test_result":
            return await self._stress_test_result(context)
        else:
            return {"success": False, "error": "Invalid action", "ai_message": "不支持的操作类型"}

    async def _health_check(self, match_id: str, context: dict = None) -> dict:
        """关系健康检查"""
        # 使用 RelationshipTrackingTool
        from agent.tools.autonomous_tools import RelationshipTrackingTool

        tracking_result = RelationshipTrackingTool.handle(match_id=match_id, period="weekly")

        if "error" in tracking_result:
            return {
                "success": False,
                "error": tracking_result["error"],
                "ai_message": "无法获取关系数据"
            }

        health_score = tracking_result.get("health_score", 0)
        issues = tracking_result.get("potential_issues", [])
        recommendations = tracking_result.get("recommendations", [])

        # 生成 AI 消息
        ai_message = self._generate_health_message(health_score, issues)

        return {
            "success": True,
            "ai_message": ai_message,
            "health_score": health_score,
            "issues": issues,
            "recommendations": recommendations,
            "interaction_summary": tracking_result.get("interaction_summary", {})
        }

    async def _get_advice(self, match_id: str, context: dict = None) -> dict:
        """获取关系建议"""
        issue_type = context.get("issue_type", "general") if context else "general"

        # 获取关系数据
        from agent.tools.autonomous_tools import RelationshipTrackingTool
        tracking_result = RelationshipTrackingTool.handle(match_id=match_id, period="weekly")

        health_score = tracking_result.get("health_score", 0)
        current_stage = tracking_result.get("current_stage", "unknown")

        # 生成建议
        advice = self._generate_advice(issue_type, current_stage, health_score)

        return {
            "success": True,
            "ai_message": advice.get("message", ""),
            "detailed_advice": advice.get("detailed", ""),
            "action_items": advice.get("action_items", [])
        }

    async def _plan_date(self, match_id: str, context: dict = None) -> dict:
        """策划约会"""
        # 获取匹配信息
        match_info = self._get_match_info(match_id)
        if not match_info:
            return {
                "success": False,
                "error": "Match not found",
                "ai_message": "未找到匹配记录"
            }

        relationship_stage = match_info.get("relationship_stage", "chatting")
        common_interests = match_info.get("common_interests", [])
        user_locations = match_info.get("locations", {})

        # 根据关系阶段推荐约会类型
        date_type = self._recommend_date_type(relationship_stage)

        # 生成约会方案
        date_plans = await self._generate_date_plans(date_type, common_interests, user_locations, context)

        return {
            "success": True,
            "ai_message": f"为你们策划了{len(date_plans)}个约会方案~",
            "date_type": date_type,
            "plans": date_plans,
            "generative_ui": self._build_date_ui(date_plans)
        }

    async def _gift_suggestion(self, match_id: str, context: dict = None) -> dict:
        """送礼建议"""
        # 获取匹配信息
        match_info = self._get_match_info(match_id)
        if not match_info:
            return {
                "success": False,
                "error": "Match not found",
                "ai_message": "未找到匹配记录"
            }

        occasion = context.get("occasion", "general") if context else "general"
        budget = context.get("budget", 500) if context else 500

        # 获取对方兴趣
        partner_interests = match_info.get("partner_interests", [])

        # 生成礼物建议
        gift_suggestions = self._generate_gift_suggestions(occasion, budget, partner_interests)

        return {
            "success": True,
            "ai_message": self._generate_gift_message(gift_suggestions),
            "gift_suggestions": gift_suggestions
        }

    # ========== 关系压力测试（替代已删除的 relationship_stress_test API）==========

    async def _stress_test(
        self,
        user_id: str,
        partner_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> dict:
        """
        创建关系压力测试

        Args:
            user_id: 用户 ID
            partner_id: 伴侣用户 ID
            context: 包含 scenario_type, relationship_stage 等

        Returns:
            测试创建结果
        """
        scenario_type = context.get("scenario_type", "value_conflict") if context else "value_conflict"
        relationship_stage = context.get("relationship_stage", "dating") if context else "dating"

        # 生成测试 ID
        test_id = f"stress-test-{user_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 生成测试问题
        questions = self._generate_stress_test_questions(scenario_type, relationship_stage)

        logger.info(f"RelationshipCoachSkill: Created stress test {test_id} with {len(questions)} questions")

        return {
            "success": True,
            "test_id": test_id,
            "questions": questions,
            "scenario_type": scenario_type,
            "ai_message": f"已创建关系压力测试（{scenario_type}场景），共{len(questions)}个问题"
        }

    async def _stress_test_answer(self, context: Optional[Dict[str, Any]] = None) -> dict:
        """
        提交压力测试答案

        Args:
            context: 包含 test_id, question_id, selected_option

        Returns:
            答案分析结果
        """
        test_id = context.get("test_id", "") if context else ""
        question_id = context.get("question_id", "") if context else ""
        selected_option = context.get("selected_option", "") if context else ""

        # 模拟分析结果
        analysis = {
            "attitude_analysis": "你的回答显示你在面对价值观冲突时倾向于妥协和沟通，这是一种健康的处理方式。",
            "communication_advice": "建议在类似情况下，先表达自己的感受，再倾听对方的想法，最后共同寻找解决方案。",
            "resilience_score": 75
        }

        logger.info(f"RelationshipCoachSkill: Answer submitted for test={test_id}, question={question_id}")

        return {
            "success": True,
            "analysis": analysis,
            "ai_message": analysis.get("attitude_analysis", "")
        }

    async def _stress_test_result(self, context: Optional[Dict[str, Any]] = None) -> dict:
        """
        获取压力测试结果

        Args:
            context: 包含 test_id

        Returns:
            测试结果总结
        """
        test_id = context.get("test_id", "") if context else ""

        # 模拟结果
        summary = {
            "average_resilience_score": 78,
            "overall_risk_level": "低风险",
            "key_findings": [
                "在价值观冲突场景中表现出较强的沟通能力",
                "倾向于通过协商解决分歧",
                "情绪控制能力良好"
            ],
            "recommendations": [
                "继续保持开放的沟通态度",
                "在面对重大分歧时，可以尝试提前准备",
                "定期进行关系健康检查"
            ]
        }

        logger.info(f"RelationshipCoachSkill: Getting result for test={test_id}")

        return {
            "success": True,
            "summary": summary,
            "ai_message": f"测试完成！平均韧性评分：{summary['average_resilience_score']}，风险等级：{summary['overall_risk_level']}"
        }

    def _generate_stress_test_questions(self, scenario_type: str, relationship_stage: str) -> list:
        """生成压力测试问题"""
        questions = []

        if scenario_type == "value_conflict":
            questions = [
                {
                    "question_id": "q1",
                    "scenario_description": "你们在讨论未来定居城市时产生了分歧。你希望留在现在的城市发展事业，而对方想回老家照顾父母。",
                    "options": [
                        {"id": "a", "content": "直接表达自己的想法，希望对方能理解", "consequence": "可能导致分歧加深"},
                        {"id": "b", "content": "先倾听对方的想法，再表达自己的顾虑", "consequence": "有助于理解彼此立场"},
                        {"id": "c", "content": "提出折中方案，比如先在现在的城市发展几年再考虑", "consequence": "可能双方都能接受"},
                        {"id": "d", "content": "暂时回避这个问题，等以后再说", "consequence": "问题可能会积累"}
                    ],
                    "difficulty": 3,
                    "key_insight": "定居问题涉及双方的核心价值观，需要坦诚沟通"
                },
                {
                    "question_id": "q2",
                    "scenario_description": "对方希望你以后能照顾TA的父母，但你觉得这会影响自己的事业发展。",
                    "options": [
                        {"id": "a", "content": "直接表达自己的顾虑，希望对方能理解", "consequence": "可能导致对方感到被忽视"},
                        {"id": "b", "content": "提出可以定期探望但无法全职照顾", "consequence": "坦诚但可能不被接受"},
                        {"id": "c", "content": "同意对方的想法，但内心感到不满", "consequence": "可能积累负面情绪"},
                        {"id": "d", "content": "讨论其他解决方案，比如请护工或定期探望", "consequence": "可能找到双方都接受的方案"}
                    ],
                    "difficulty": 4,
                    "key_insight": "家庭责任分配需要双方协商"
                },
                {
                    "question_id": "q3",
                    "scenario_description": "对方希望你们能尽快结婚，但你觉得还需要更多时间了解彼此。",
                    "options": [
                        {"id": "a", "content": "直接表达自己的想法，希望对方能等待", "consequence": "可能导致对方感到被拒绝"},
                        {"id": "b", "content": "提出可以先订婚，给自己更多时间准备", "consequence": "折中方案"},
                        {"id": "c", "content": "同意对方的想法，但内心感到压力", "consequence": "可能导致以后的问题"},
                        {"id": "d", "content": "坦诚讨论自己对婚姻的想法和顾虑", "consequence": "有助于理解彼此立场"}
                    ],
                    "difficulty": 4,
                    "key_insight": "婚姻时间表需要双方达成共识"
                }
            ]

        elif scenario_type == "lifestyle_difference":
            questions = [
                {
                    "question_id": "q1",
                    "scenario_description": "对方喜欢早起锻炼，而你喜欢晚睡晚起。对方希望你调整作息。",
                    "options": [
                        {"id": "a", "content": "尝试调整自己的作息适应对方", "consequence": "可能牺牲自己的舒适"},
                        {"id": "b", "content": "提出可以部分调整，但保留自己的节奏", "consequence": "折中方案"},
                        {"id": "c", "content": "表达自己的习惯难以改变", "consequence": "可能导致冲突"},
                        {"id": "d", "content": "讨论如何在不改变作息的情况下增加相处时间", "consequence": "创新方案"}
                    ],
                    "difficulty": 2,
                    "key_insight": "生活习惯差异可以通过协商解决"
                },
                {
                    "question_id": "q2",
                    "scenario_description": "对方喜欢整洁有序的生活环境，而你喜欢随性的生活方式。",
                    "options": [
                        {"id": "a", "content": "尝试改变自己的习惯适应对方", "consequence": "可能牺牲自己的舒适"},
                        {"id": "b", "content": "提出可以共同制定一些基本规则", "consequence": "折中方案"},
                        {"id": "c", "content": "表达自己的生活方式难以改变", "consequence": "可能导致冲突"},
                        {"id": "d", "content": "讨论如何在不改变风格的情况下保持整洁", "consequence": "创新方案"}
                    ],
                    "difficulty": 2,
                    "key_insight": "生活风格差异需要双方妥协"
                }
            ]

        elif scenario_type == "economic_disagreement":
            questions = [
                {
                    "question_id": "q1",
                    "scenario_description": "对方希望你们能共同存钱买房，但你觉得应该先享受生活。",
                    "options": [
                        {"id": "a", "content": "表达自己希望平衡存钱和享受生活", "consequence": "可能不被接受"},
                        {"id": "b", "content": "提出可以部分存钱，同时保留享受生活的预算", "consequence": "折中方案"},
                        {"id": "c", "content": "同意对方的想法，但内心感到不满", "consequence": "可能积累负面情绪"},
                        {"id": "d", "content": "坦诚讨论自己对金钱的看法", "consequence": "有助于理解彼此立场"}
                    ],
                    "difficulty": 3,
                    "key_insight": "金钱观念差异需要坦诚沟通"
                }
            ]

        elif scenario_type == "communication_style":
            questions = [
                {
                    "question_id": "q1",
                    "scenario_description": "对方在遇到问题时喜欢直接讨论，而你更喜欢自己消化后再谈。",
                    "options": [
                        {"id": "a", "content": "尝试改变自己的习惯适应对方", "consequence": "可能牺牲自己的舒适"},
                        {"id": "b", "content": "提出可以给自己一些时间消化后再讨论", "consequence": "折中方案"},
                        {"id": "c", "content": "表达自己的沟通方式难以改变", "consequence": "可能导致冲突"},
                        {"id": "d", "content": "讨论如何找到双方都舒适的沟通方式", "consequence": "创新方案"}
                    ],
                    "difficulty": 2,
                    "key_insight": "沟通风格差异需要双方理解"
                }
            ]

        else:  # family_relation
            questions = [
                {
                    "question_id": "q1",
                    "scenario_description": "对方的父母对你有偏见，对方希望你主动改善关系。",
                    "options": [
                        {"id": "a", "content": "主动尝试改善关系", "consequence": "可能需要时间"},
                        {"id": "b", "content": "提出可以先通过对方了解父母的想法", "consequence": "间接方式"},
                        {"id": "c", "content": "表达自己需要对方的支持才能改善关系", "consequence": "寻求帮助"},
                        {"id": "d", "content": "讨论如何在不强迫自己的情况下改善关系", "consequence": "协商方案"}
                    ],
                    "difficulty": 4,
                    "key_insight": "家庭关系需要双方共同努力"
                }
            ]

        return questions

    def _get_match_info(self, match_id: str) -> Optional[dict]:
        """获取匹配信息"""
        # 从数据库获取匹配信息
        # 注：当前优先从数据库读取，降级时使用模拟数据
        try:
            from db.models import MatchHistoryDB, ChatConversationDB
            from db.database import SessionLocal
            from utils.db_session_manager import db_session, db_session_readonly, optional_db_session
            from sqlalchemy.orm import joinedload  # @deprecated: joinedload import unused, will be removed

            db = SessionLocal()

            # 获取匹配记录
            match = db.query(MatchHistoryDB).filter(MatchHistoryDB.id == match_id).first()

            if match:
                # 获取双方用户的兴趣
                from db.models import UserDB
                user_a = db.query(UserDB).filter(UserDB.id == match.user_id_1).first()
                user_b = db.query(UserDB).filter(UserDB.id == match.user_id_2).first()

                if user_a and user_b:
                    # 解析共同兴趣
                    import json
                    interests_a = json.loads(user_a.interests) if user_a.interests else []
                    interests_b = json.loads(user_b.interests) if user_b.interests else []
                    common_interests = list(set(interests_a) & set(interests_b))

                    # 获取关系阶段（从对话数量推断）
                    conversation_count = db.query(ChatConversationDB).filter(
                        ((ChatConversationDB.user_id_1 == user_a.id) & (ChatConversationDB.user_id_2 == user_b.id)) |
                        ((ChatConversationDB.user_id_1 == user_b.id) & (ChatConversationDB.user_id_2 == user_a.id))
                    ).count()

                    if conversation_count == 0:
                        relationship_stage = "matched"
                    elif conversation_count < 10:
                        relationship_stage = "chatting"
                    elif conversation_count < 50:
                        relationship_stage = "exchanged_contacts"
                    else:
                        relationship_stage = "dating"

                    db.close()

                    return {
                        "id": match_id,
                        "relationship_stage": relationship_stage,
                        "common_interests": common_interests if common_interests else ["旅行", "美食"],
                        "locations": {"midpoint": "上海市中心"},  # 注：地理位置待对接 geo_location_skill
                        "partner_interests": interests_b if interests_b else ["咖啡", "手工艺品"],
                        "anniversary_date": None  # 注：纪念日需用户手动设置
                    }

            db.close()

        except Exception as e:
            logger.error(f"RelationshipCoachSkill: Error getting match info: {e}")

        # 降级：返回模拟数据
        logger.info(f"RelationshipCoachSkill: Using mock data for match_id={match_id}")
        return {
            "id": match_id,
            "relationship_stage": "dating",
            "common_interests": ["旅行", "美食", "电影"],
            "locations": {"midpoint": "上海市中心"},
            "partner_interests": ["咖啡", "手工艺品", "音乐会"],
            "anniversary_date": "2026-05-20"
        }

    def _recommend_date_type(self, stage: str) -> str:
        """根据关系阶段推荐约会类型"""
        type_mapping = {
            "matched": "online_activity",
            "chatting": "casual_meetup",
            "exchanged_contacts": "first_date",
            "first_date": "regular_date",
            "dating": "romantic_date",
            "in_relationship": "special_date"
        }
        return type_mapping.get(stage, "casual_meetup")

    async def _generate_date_plans(self, date_type: str, common_interests: list, locations: dict, context: dict = None) -> list:
        """生成约会方案"""
        plans = []

        if date_type == "first_date":
            plans = [
                {
                    "title": "咖啡厅轻松见面",
                    "type": "casual",
                    "description": "选择一家安静的精品咖啡厅，轻松自在地认识彼此",
                    "duration": "1-2 小时",
                    "location_suggestions": [
                        {"name": "星巴克臻选", "address": "市中心店", "price_range": "50-100 元/人"},
                        {"name": "独立咖啡馆", "address": "创意园区店", "price_range": "40-80 元/人"}
                    ],
                    "conversation_starters": [
                        "聊聊最近看的电影/书籍",
                        "分享工作趣事",
                        "讨论共同的兴趣爱好"
                    ],
                    "budget_estimate": "50-100 元/人",
                    "tips": [
                        "选择公共场所，注意安全",
                        "不要太晚结束",
                        "提前准备好话题"
                    ],
                    "confidence_score": 0.9
                },
                {
                    "title": "博物馆/艺术展",
                    "type": "cultural",
                    "description": "一起欣赏艺术作品，在交流中增进了解",
                    "duration": "2-3 小时",
                    "location_suggestions": [
                        {"name": "市美术馆", "address": "文化区", "price_range": "50-100 元/人"},
                        {"name": "当代艺术中心", "address": "创意园区", "price_range": "80-150 元/人"}
                    ],
                    "conversation_starters": [
                        "讨论喜欢的展品",
                        "分享艺术观点",
                        "聊聊各自的审美偏好"
                    ],
                    "budget_estimate": "100-200 元/人",
                    "tips": [
                        "提前查好展览信息",
                        "尊重对方观点",
                        "可以在附近安排简餐"
                    ],
                    "confidence_score": 0.85
                },
                {
                    "title": "户外散步 + 简餐",
                    "type": "outdoor",
                    "description": "在公园或河边散步，轻松自然地聊天",
                    "duration": "2-3 小时",
                    "location_suggestions": [
                        {"name": "市中心公园", "address": "地铁直达", "price_range": "免费"},
                        {"name": "河边步道", "address": "景观区", "price_range": "免费"}
                    ],
                    "conversation_starters": [
                        "聊聊日常生活",
                        "分享童年回忆",
                        "讨论未来的计划"
                    ],
                    "budget_estimate": "50-150 元/人 (简餐)",
                    "tips": [
                        "注意天气",
                        "穿着舒适的鞋子",
                        "可以带瓶水"
                    ],
                    "confidence_score": 0.8
                }
            ]

        elif date_type == "romantic_date":
            plans = [
                {
                    "title": "浪漫晚餐",
                    "type": "romantic",
                    "description": "选择一家有氛围的餐厅，享受二人世界",
                    "duration": "2-3 小时",
                    "location_suggestions": [
                        {"name": "法式餐厅", "address": "市中心", "price_range": "300-500 元/人"},
                        {"name": "江景餐厅", "address": "滨江道", "price_range": "400-600 元/人"}
                    ],
                    "budget_estimate": "300-600 元/人",
                    "tips": [
                        "提前预订位置",
                        "注意着装要求",
                        "可以准备小惊喜"
                    ],
                    "confidence_score": 0.9
                }
            ]

        elif date_type == "casual_meetup":
            plans = [
                {
                    "title": "市集/小店探索",
                    "type": "casual",
                    "description": "一起逛创意市集，发现有趣的小店",
                    "duration": "2-3 小时",
                    "budget_estimate": "100-200 元/人",
                    "confidence_score": 0.8
                }
            ]

        return plans

    def _build_date_ui(self, date_plans: list) -> dict:
        """构建约会 UI 配置"""
        if not date_plans:
            return {
                "component_type": "empty_state",
                "props": {"message": "暂无约会方案"}
            }

        return {
            "component_type": "date_plan_carousel",
            "props": {
                "plans": date_plans,
                "show_details": True,
                "allow_booking": True
            }
        }

    def _generate_gift_suggestions(self, occasion: str, budget: float, partner_interests: list) -> list:
        """生成礼物建议"""
        suggestions = []

        if occasion == "anniversary":
            suggestions = [
                {
                    "name": "定制照片书",
                    "description": "收集你们的珍贵回忆，制作成精美的照片书",
                    "price_range": "100-300 元",
                    "suitability": 0.9,
                    "purchase_link": "淘宝/京东搜索'定制照片书'"
                },
                {
                    "name": "手工巧克力礼盒",
                    "description": "甜蜜的心意，适合纪念日分享",
                    "price_range": "150-400 元",
                    "suitability": 0.85,
                    "purchase_link": "高端巧克力品牌官方店"
                }
            ]

        elif occasion == "birthday":
            suggestions = [
                {
                    "name": "个性化首饰",
                    "description": "刻上特殊日期或名字的首饰",
                    "price_range": "200-800 元",
                    "suitability": 0.9,
                    "purchase_link": "首饰品牌官方店"
                },
                {
                    "name": "体验类礼物",
                    "description": "SPA 券、烹饪课程等体验",
                    "price_range": "300-1000 元",
                    "suitability": 0.85,
                    "purchase_link": "体验平台"
                }
            ]

        elif occasion == "holiday":
            suggestions = [
                {
                    "name": "节日主题礼盒",
                    "description": "应景的节日礼物",
                    "price_range": "100-500 元",
                    "suitability": 0.8
                }
            ]

        else:
            suggestions = [
                {
                    "name": "鲜花 + 手写卡片",
                    "description": "简单但充满心意的小惊喜",
                    "price_range": "100-300 元",
                    "suitability": 0.85
                },
                {
                    "name": "对方兴趣相关的物品",
                    "description": "根据其爱好选择相关礼物",
                    "price_range": "200-500 元",
                    "suitability": 0.9
                }
            ]

        return suggestions

    def _generate_health_message(self, health_score: float, issues: list) -> str:
        """生成健康检查消息"""
        stage_names = {
            "matched": "匹配成功",
            "chatting": "聊天中",
            "exchanged_contacts": "已交换联系方式",
            "first_date": "已首次约会",
            "dating": "交往中",
            "in_relationship": "确定关系"
        }

        if health_score >= 0.8:
            base_message = "你们的关系发展非常健康，互动频繁且稳定。继续保持真诚的沟通，关系有望更进一步！"
        elif health_score >= 0.6:
            base_message = "你们的关系整体稳定，但还有提升空间。可以尝试增加一些互动频率，或者安排一次线下见面。"
        else:
            base_message = "你们的关系可能需要更多关注。近期互动较少，建议主动联系对方，重新建立连接。"

        if issues:
            base_message += f"\n\n注意：发现{len(issues)} 个潜在问题："
            for issue in issues[:2]:
                base_message += f"\n- {issue.get('description', '未知问题')}"

        return base_message

    def _generate_advice(self, issue_type: str, stage: str, health_score: float) -> dict:
        """生成关系建议"""
        advice_templates = {
            "low_interaction": {
                "message": "最近互动较少，关系可能停滞",
                "detailed": "互动频率是关系健康的重要指标。建议：\n1. 主动分享日常生活中的趣事\n2. 邀请对方一起参加线上活动\n3. 安排固定的聊天时间",
                "action_items": ["发送一条问候消息", "分享一个有趣的话题", "提议周末活动"]
            },
            "communication_gap": {
                "message": "感觉沟通有障碍",
                "detailed": "沟通障碍可能源于：\n1. 话题枯竭\n2. 回应不及时\n3. 缺乏深度交流\n\n建议从共同兴趣入手，或者聊聊最近看的电影/书籍。",
                "action_items": ["找出一个新话题", "安排一次视频通话", "一起看同一部电影"]
            },
            "anniversary_coming": {
                "message": "纪念日快到了",
                "detailed": "纪念日是增进感情的好机会：\n1. 准备一个小惊喜\n2. 写一封手写信\n3. 安排一次特别的约会",
                "action_items": ["准备礼物", "安排约会", "写一封感谢信"]
            },
            "general": {
                "message": "保持真诚沟通，关系需要双方共同经营",
                "detailed": f"你们目前处于{stage}阶段，健康度{health_score * 100:.0f}%。\n\n通用建议：\n1. 保持稳定的沟通频率\n2. 真诚表达自己的感受\n3. 尊重对方的空间和节奏",
                "action_items": ["主动发起一次深入对话", "分享一个个人故事", "询问对方的想法"]
            }
        }

        return advice_templates.get(issue_type, advice_templates["general"])

    def _generate_gift_message(self, suggestions: list) -> str:
        """生成礼物建议消息"""
        if not suggestions:
            return "暂时没有想到合适的礼物建议，心意最重要~"

        message = f"为你准备了{len(suggestions)}个礼物灵感：\n"
        for i, suggestion in enumerate(suggestions[:3], 1):
            message += f"\n{i}. {suggestion.get('name', '')} - {suggestion.get('price_range', '')}"
            message += f"\n   {suggestion.get('description', '')}"

        message += "\n\n记住：礼物的心意比价格更重要~"

        return message

    # 自主触发器

    async def autonomous_trigger(self, user_id: str, trigger_type: str, context: dict) -> dict:
        """
        自主关系干预

        Args:
            user_id: 用户 ID
            trigger_type: 触发类型
            context: 上下文数据

        Returns:
            触发结果
        """
        logger.info(f"RelationshipCoachSkill: Autonomous trigger {trigger_type} for {user_id}")

        if trigger_type == "communication_drop":
            return await self._handle_communication_drop(user_id, context)
        elif trigger_type == "anniversary_reminder":
            return await self._handle_anniversary_reminder(user_id, context)
        elif trigger_type == "milestone_reached":
            return await self._handle_milestone_reached(user_id, context)
        else:
            return {"triggered": False, "reason": "unknown_trigger_type"}

    async def _handle_communication_drop(self, user_id: str, context: dict) -> dict:
        """处理沟通频率下降"""
        affected_matches = context.get("matches", [])

        for match_id in affected_matches[:1]:  # 只处理一个
            advice = await self._get_advice(match_id, {"issue_type": "low_interaction"})

            return {
                "triggered": True,
                "should_push": True,
                "push_message": f"注意到你们最近互动减少，{advice.get('ai_message', '主动联系一下吧~')}",
                "match_id": match_id
            }

        return {"triggered": False, "reason": "no_affected_matches"}

    async def _handle_anniversary_reminder(self, user_id: str, context: dict) -> dict:
        """处理纪念日提醒"""
        days_until = context.get("days_until", 0)
        occasion = context.get("occasion", "anniversary")
        match_id = context.get("match_id")

        if days_until <= 7:
            gift_advice = await self._gift_suggestion(match_id, {"occasion": occasion})

            return {
                "triggered": True,
                "should_push": True,
                "push_message": f"{occasion}快到了（{days_until}天后）！准备一份特别的礼物吧~",
                "suggestions": gift_advice.get("gift_suggestions", [])
            }

        return {"triggered": False, "reason": "too_early"}

    async def _handle_milestone_reached(self, user_id: str, context: dict) -> dict:
        """处理关系里程碑达成"""
        milestone = context.get("milestone", "unknown")
        match_id = context.get("match_id")

        milestone_messages = {
            "100_messages": "恭喜你们完成 100 条消息里程碑！继续用心交流~",
            "first_date": "首次约会完成！这是一个美好的开始，记得分享你的感受~",
            "30_days": "你们已经相识 30 天了！时间过得真快，继续经营这段关系吧~"
        }

        return {
            "triggered": True,
            "should_push": True,
            "push_message": milestone_messages.get(milestone, "恭喜你们达成关系里程碑！"),
            "match_id": match_id
        }


# 全局 Skill 实例
_relationship_coach_skill_instance: Optional[RelationshipCoachSkill] = None


def get_relationship_coach_skill() -> RelationshipCoachSkill:
    """获取关系教练 Skill 单例实例"""
    global _relationship_coach_skill_instance
    if _relationship_coach_skill_instance is None:
        _relationship_coach_skill_instance = RelationshipCoachSkill()
    return _relationship_coach_skill_instance
