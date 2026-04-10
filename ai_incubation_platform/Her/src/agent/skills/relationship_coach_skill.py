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

    自主触发条件:
    - 沟通频率下降 > 50%
    - 检测到负面关键词
    - 纪念日临近
    - 关系里程碑达成
    """

    name = "relationship_coach"
    version = "1.0.0"
    description = """
    关系维护教练

    能力:
    - 监测关系健康度
    - 识别矛盾预警信号
    - 提供沟通建议
    - 策划约会活动
    - 送礼建议
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
                "action": {
                    "type": "string",
                    "enum": ["health_check", "get_advice", "plan_date", "gift_suggestion"],
                    "description": "操作类型"
                },
                "context": {
                    "type": "object",
                    "properties": {
                        "issue_type": {"type": "string"},
                        "occasion": {"type": "string"},
                        "budget": {"type": "number"}
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
                }
            }
        }

    async def execute(
        self,
        match_id: str,
        action: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> dict:
        """
        执行关系教练 Skill

        Args:
            match_id: 匹配记录 ID
            action: 操作类型
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

    def _get_match_info(self, match_id: str) -> Optional[dict]:
        """获取匹配信息"""
        # 从数据库获取匹配信息
        # 注：当前优先从数据库读取，降级时使用模拟数据
        try:
            from db.models import MatchHistoryDB, ChatConversationDB
            from db.database import SessionLocal
            from utils.db_session_manager import db_session, db_session_readonly, optional_db_session
            from sqlalchemy.orm import joinedload

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
