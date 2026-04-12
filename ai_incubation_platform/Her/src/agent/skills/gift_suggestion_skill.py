"""
礼物推荐 Skill

AI 根据场景、对方兴趣、关系阶段推荐合适的礼物
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from agent.skills.base import BaseSkill
from utils.logger import logger


class GiftSuggestionSkill:
    """
    礼物推荐 Skill

    核心能力:
    - 根据场景推荐礼物（生日/纪念日/日常/感谢）
    - 分析对方兴趣匹配礼物
    - 考虑预算和关系阶段
    - 生成推荐理由

    自主触发条件:
    - 用户询问送什么礼物
    - 纪念日临近（系统主动推送）
    - 对方生日提醒
    """

    name = "gift_suggestion"
    version = "1.0.0"
    description = """
    AI 礼物推荐服务

    能力:
    - 场景化礼物推荐
    - 个性化匹配
    - 预算适配
    - 推荐理由生成
    """

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
                    "description": "对方用户 ID"
                },
                "occasion": {
                    "type": "string",
                    "enum": ["birthday", "anniversary", "daily", "thank_you", "apology", "celebration"],
                    "description": "送礼场景"
                },
                "budget": {
                    "type": "number",
                    "description": "预算范围（可选）"
                },
                "action": {
                    "type": "string",
                    "enum": ["recommend", "get_popular", "get_by_interest"],
                    "description": "操作类型"
                }
            },
            "required": ["user_id", "partner_id", "occasion"]
        }

    def get_output_schema(self) -> dict:
        """获取输出参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "ai_message": {"type": "string"},
                "recommendations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "gift_id": {"type": "string"},
                            "name": {"type": "string"},
                            "price": {"type": "number"},
                            "icon": {"type": "string"},
                            "reason": {"type": "string"},
                            "suitability_score": {"type": "number"},
                            "occasion_match": {"type": "boolean"}
                        }
                    }
                },
                "budget_analysis": {"type": "object"},
                "generative_ui": {"type": "object"}
            }
        }

    async def execute(
        self,
        user_id: str,
        partner_id: str,
        occasion: str,
        budget: Optional[float] = None,
        action: str = "recommend",
        **kwargs
    ) -> dict:
        """
        执行礼物推荐 Skill

        Args:
            user_id: 用户 ID
            partner_id: 对方用户 ID
            occasion: 送礼场景
            budget: 预算范围
            action: 操作类型

        Returns:
            Skill 执行结果
        """
        logger.info(f"GiftSuggestionSkill: action={action}, user={user_id}, partner={partner_id}, occasion={occasion}")

        if action == "recommend":
            return await self._recommend_gifts(user_id, partner_id, occasion, budget)
        elif action == "get_popular":
            return await self._get_popular_gifts(occasion)
        elif action == "get_by_interest":
            return await self._get_gifts_by_interest(partner_id, occasion)
        else:
            return {"success": False, "error": "Invalid action", "ai_message": "不支持的操作"}

    async def _recommend_gifts(
        self,
        user_id: str,
        partner_id: str,
        occasion: str,
        budget: Optional[float] = None
    ) -> dict:
        """推荐礼物"""
        # 获取对方信息
        partner_info = self._get_partner_info(partner_id)

        # 获取礼物库
        gift_catalog = self._get_gift_catalog()

        # 根据场景筛选
        occasion_gifts = self._filter_by_occasion(gift_catalog, occasion)

        # 根据兴趣匹配
        matched_gifts = self._match_by_interest(occasion_gifts, partner_info.get("interests", []))

        # 根据预算筛选
        if budget:
            matched_gifts = [g for g in matched_gifts if g["price"] <= budget]

        # 生成推荐理由
        for gift in matched_gifts[:5]:
            gift["reason"] = self._generate_reason(gift, partner_info, occasion)
            gift["suitability_score"] = self._calculate_suitability(gift, partner_info, occasion)

        # 排序
        matched_gifts.sort(key=lambda g: g.get("suitability_score", 0), reverse=True)

        # 生成 AI 消息
        ai_message = self._generate_ai_message(matched_gifts[:5], occasion, budget)

        return {
            "success": True,
            "ai_message": ai_message,
            "recommendations": matched_gifts[:5],
            "budget_analysis": {
                "min_price": min(g["price"] for g in matched_gifts[:5]) if matched_gifts else 0,
                "max_price": max(g["price"] for g in matched_gifts[:5]) if matched_gifts else 0,
                "recommended_budget": sum(g["price"] for g in matched_gifts[:3]) / 3 if len(matched_gifts) >= 3 else 0
            },
            "generative_ui": self._build_gift_ui(matched_gifts[:5])
        }

    async def _get_popular_gifts(self, occasion: str) -> dict:
        """获取热门礼物"""
        gift_catalog = self._get_gift_catalog()
        popular_gifts = [g for g in gift_catalog if g.get("is_popular") and g.get("category") == occasion]

        return {
            "success": True,
            "ai_message": f"这是{occasion}场景的热门礼物~",
            "recommendations": popular_gifts[:5]
        }

    async def _get_gifts_by_interest(self, partner_id: str, occasion: str) -> dict:
        """根据兴趣获取礼物"""
        partner_info = self._get_partner_info(partner_id)
        gift_catalog = self._get_gift_catalog()

        matched_gifts = self._match_by_interest(gift_catalog, partner_info.get("interests", []))

        return {
            "success": True,
            "ai_message": f"根据TA的兴趣，我推荐这些礼物~",
            "recommendations": matched_gifts[:5]
        }

    def _get_partner_info(self, partner_id: str) -> dict:
        """获取对方信息"""
        try:
            from db.models import UserDB
            from db.database import SessionLocal
            import json

            db = SessionLocal()
            user = db.query(UserDB).filter(UserDB.id == partner_id).first()

            if user:
                interests = json.loads(user.interests) if user.interests else []
                db.close()
                return {
                    "id": partner_id,
                    "name": user.name,
                    "interests": interests,
                    "age": user.age,
                    "gender": user.gender
                }
            db.close()
        except Exception as e:
            logger.error(f"GiftSuggestionSkill: Error getting partner info: {e}")

        # 降级：返回默认数据
        return {
            "id": partner_id,
            "name": "TA",
            "interests": ["旅行", "美食", "音乐"],
            "age": 25
        }

    def _get_gift_catalog(self) -> list:
        """获取礼物库"""
        # 模拟礼物数据（实际应从数据库或配置读取）
        return [
            # 生日礼物
            {"gift_id": "g1", "name": "生日蛋糕", "price": 50, "icon": "cake", "category": "birthday", "is_popular": True, "tags": ["美食", "庆祝"]},
            {"gift_id": "g2", "name": "定制照片书", "price": 150, "icon": "book", "category": "birthday", "is_popular": True, "tags": ["纪念", "旅行", "摄影"]},
            {"gift_id": "g3", "name": "生日鲜花", "price": 100, "icon": "flower", "category": "birthday", "is_popular": True, "tags": ["浪漫", "自然"]},
            {"gift_id": "g4", "name": "生日贺卡", "price": 10, "icon": "card", "category": "birthday", "tags": ["简单", "心意"]},

            # 纪念日礼物
            {"gift_id": "g5", "name": "红玫瑰", "price": 200, "icon": "rose", "category": "anniversary", "is_popular": True, "tags": ["浪漫", "爱情"]},
            {"gift_id": "g6", "name": "情侣戒指", "price": 500, "icon": "ring", "category": "anniversary", "is_popular": True, "tags": ["纪念", "爱情"]},
            {"gift_id": "g7", "name": "纪念相册", "price": 100, "icon": "album", "category": "anniversary", "tags": ["纪念", "旅行"]},

            # 日常礼物
            {"gift_id": "g8", "name": "咖啡", "price": 5, "icon": "coffee", "category": "daily", "is_popular": True, "tags": ["美食", "咖啡"]},
            {"gift_id": "g9", "name": "冰淇淋", "price": 8, "icon": "icecream", "category": "daily", "is_popular": True, "tags": ["美食", "甜食"]},
            {"gift_id": "g10", "name": "爱心拥抱", "price": 1, "icon": "hug", "category": "daily", "is_popular": True, "tags": ["温暖", "简单"]},

            # 感谢礼物
            {"gift_id": "g11", "name": "感谢卡片", "price": 5, "icon": "thankcard", "category": "thank_you", "tags": ["简单", "心意"]},
            {"gift_id": "g12", "name": "小礼物", "price": 20, "icon": "gift", "category": "thank_you", "tags": ["日常"]},

            # VIP礼物
            {"gift_id": "g13", "name": "钻戒", "price": 1000, "icon": "diamond", "category": "vip", "is_popular": True, "tags": ["奢华", "爱情"]},
            {"gift_id": "g14", "name": "城堡", "price": 500, "icon": "castle", "category": "vip", "tags": ["奢华", "浪漫"]},
        ]

    def _filter_by_occasion(self, gifts: list, occasion: str) -> list:
        """根据场景筛选礼物"""
        if occasion == "birthday":
            return [g for g in gifts if g.get("category") in ["birthday", "daily"]]
        elif occasion == "anniversary":
            return [g for g in gifts if g.get("category") in ["anniversary", "birthday", "vip"]]
        elif occasion == "daily":
            return [g for g in gifts if g.get("category") in ["daily", "thank_you"]]
        elif occasion == "thank_you":
            return [g for g in gifts if g.get("category") in ["thank_you", "daily"]]
        elif occasion == "apology":
            return [g for g in gifts if g.get("category") in ["daily", "thank_you"]]
        elif occasion == "celebration":
            return [g for g in gifts if g.get("category") in ["birthday", "anniversary", "vip"]]
        return gifts

    def _match_by_interest(self, gifts: list, interests: list) -> list:
        """根据兴趣匹配礼物"""
        matched = []
        for gift in gifts:
            gift_tags = gift.get("tags", [])
            # 计算兴趣匹配度
            match_score = len(set(gift_tags) & set(interests)) / max(len(gift_tags), 1)
            gift["interest_match_score"] = match_score
            matched.append(gift)

        # 按匹配度排序
        matched.sort(key=lambda g: g.get("interest_match_score", 0), reverse=True)
        return matched

    def _generate_reason(self, gift: dict, partner_info: dict, occasion: str) -> str:
        """生成推荐理由"""
        name = partner_info.get("name", "TA")
        interests = partner_info.get("interests", [])

        # 检查兴趣匹配
        matched_interests = set(gift.get("tags", [])) & set(interests)
        if matched_interests:
            return f"{name}对{list(matched_interests)[0]}感兴趣，这个礼物很合适~"

        # 场景匹配
        occasion_reasons = {
            "birthday": f"生日送{gift['name']}，寓意美好祝福~",
            "anniversary": f"纪念日送{gift['name']}，纪念你们的美好时光~",
            "daily": f"日常送{gift['name']}，表达你的心意~",
            "thank_you": f"感谢时送{gift['name']}，表达你的感激~",
            "apology": f"道歉时送{gift['name']}，表达你的诚意~",
            "celebration": f"庆祝时送{gift['name']}，分享喜悦~"
        }

        return occasion_reasons.get(occasion, f"送{gift['name']}，表达你的心意~")

    def _calculate_suitability(self, gift: dict, partner_info: dict, occasion: str) -> float:
        """计算适配度"""
        score = 0.0

        # 场景匹配（40%）
        if gift.get("category") == occasion:
            score += 0.4
        elif gift.get("category") == "daily":
            score += 0.2

        # 兴趣匹配（30%）
        interest_match = gift.get("interest_match_score", 0)
        score += interest_match * 0.3

        # 热门度（20%）
        if gift.get("is_popular"):
            score += 0.2

        # 价格合理性（10%）
        # 简化：价格在合理范围内加分
        if gift.get("price", 0) <= 300:
            score += 0.1

        return min(score, 1.0)

    def _generate_ai_message(self, gifts: list, occasion: str, budget: Optional[float]) -> str:
        """生成 AI 消息"""
        occasion_names = {
            "birthday": "生日",
            "anniversary": "纪念日",
            "daily": "日常",
            "thank_you": "感谢",
            "apology": "道歉",
            "celebration": "庆祝"
        }

        occasion_name = occasion_names.get(occasion, occasion)

        if not gifts:
            return f"抱歉，没有找到合适的{occasion_name}礼物，你可以看看礼物商店的其他选择~"

        message = f"为{occasion_name}场景推荐了{len(gifts)}个礼物~\n"

        if budget:
            message += f"符合你的预算（{budget}元以内），以下是推荐：\n"
        else:
            message += "以下是根据TA的兴趣推荐：\n"

        for i, gift in enumerate(gifts[:3], 1):
            message += f"\n{i}. {gift['name']} - ¥{gift['price']}"
            message += f"\n   {gift.get('reason', '')}"

        message += "\n\n点击礼物可以直接购买~"

        return message

    def _build_gift_ui(self, gifts: list) -> dict:
        """构建 Generative UI"""
        if not gifts:
            return {
                "component_type": "empty_state",
                "props": {"message": "暂无推荐礼物"}
            }

        return {
            "component_type": "GiftRecommendCarousel",
            "props": {
                "gifts": gifts,
                "show_purchase_button": True,
                "show_reason": True
            }
        }

    # 自主触发器

    async def autonomous_trigger(self, user_id: str, trigger_type: str, context: dict) -> dict:
        """
        自主触发礼物推荐

        Args:
            user_id: 用户 ID
            trigger_type: 触发类型
            context: 上下文

        Returns:
            触发结果
        """
        logger.info(f"GiftSuggestionSkill: Autonomous trigger {trigger_type} for {user_id}")

        if trigger_type == "anniversary_reminder":
            return await self._handle_anniversary_reminder(user_id, context)
        elif trigger_type == "birthday_reminder":
            return await self._handle_birthday_reminder(user_id, context)
        else:
            return {"triggered": False, "reason": "unknown_trigger_type"}

    async def _handle_anniversary_reminder(self, user_id: str, context: dict) -> dict:
        """处理纪念日提醒"""
        days_until = context.get("days_until", 0)
        partner_id = context.get("partner_id")
        anniversary_type = context.get("anniversary_type", "anniversary")

        if days_until <= 7:
            result = await self._recommend_gifts(user_id, partner_id, "anniversary")

            return {
                "triggered": True,
                "should_push": True,
                "push_message": f"{anniversary_type}快到了（{days_until}天后）！我帮你想想送什么礼物~",
                "recommendations": result.get("recommendations", [])
            }

        return {"triggered": False, "reason": "too_early"}

    async def _handle_birthday_reminder(self, user_id: str, context: dict) -> dict:
        """处理生日提醒"""
        days_until = context.get("days_until", 0)
        partner_id = context.get("partner_id")

        if days_until <= 7:
            result = await self._recommend_gifts(user_id, partner_id, "birthday")

            return {
                "triggered": True,
                "should_push": True,
                "push_message": f"TA的生日快到了（{days_until}天后）！我帮你挑选生日礼物~",
                "recommendations": result.get("recommendations", [])
            }

        return {"triggered": False, "reason": "too_early"}


# 全局 Skill 实例
_gift_suggestion_skill_instance: Optional[GiftSuggestionSkill] = None


def get_gift_suggestion_skill() -> GiftSuggestionSkill:
    """获取礼物推荐 Skill 单例实例"""
    global _gift_suggestion_skill_instance
    if _gift_suggestion_skill_instance is None:
        _gift_suggestion_skill_instance = GiftSuggestionSkill()
    return _gift_suggestion_skill_instance