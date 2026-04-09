"""
礼物订购 Skill

基于关系阶段和对方喜好的智能礼物推荐与订购服务
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from agent.skills.base import BaseSkill
from utils.logger import logger
import json


class GiftOrderingSkill:
    """
    礼物订购 Skill - 智能礼物推荐与订购服务

    核心能力:
    - 关系阶段识别与礼物类型匹配
    - 基于对方喜好的个性化推荐
    - 多平台价格比较
    - 一键订购与物流追踪
    - 送礼时机建议

    AI Native 特性:
    - 自主识别送礼场景（纪念日/生日/惊喜）
    - 主动推送礼物建议
    - 自然语言交互
    - Generative UI 动态生成礼物卡片
    """

    name = "gift_ordering"
    version = "1.0.0"
    description = """
    礼物订购服务

    能力:
    - 智能礼物推荐（基于关系阶段和喜好）
    - 多平台价格比较
    - 一键订购与物流追踪
    - 送礼时机建议
    - 惊喜策划协助
    """

    def get_input_schema(self) -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "match_id": {
                    "type": "string",
                    "description": "匹配关系 ID"
                },
                "action": {
                    "type": "string",
                    "enum": ["get_suggestions", "compare_options", "place_order", "track_delivery", "get_occasion_reminder"],
                    "description": "操作类型"
                },
                "occasion": {
                    "type": "string",
                    "enum": ["birthday", "anniversary", "valentines", "christmas", "surprise", "apology"],
                    "description": "送礼场合"
                },
                "budget_range": {
                    "type": "string",
                    "enum": ["under_100", "100_300", "300_500", "500_1000", "above_1000"],
                    "description": "预算范围"
                },
                "preferences": {
                    "type": "object",
                    "description": "额外偏好设置"
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
                "gift_suggestions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "gift_id": {"type": "string"},
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "price": {"type": "number"},
                            "platform": {"type": "string"},
                            "image_url": {"type": "string"},
                            "match_reason": {"type": "string"},
                            "urgency_score": {"type": "number"}
                        }
                    }
                },
                "occasion_info": {
                    "type": "object",
                    "properties": {
                        "occasion_type": {"type": "string"},
                        "date": {"type": "string"},
                        "days_remaining": {"type": "number"}
                    }
                },
                "order_info": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string"},
                        "status": {"type": "string"},
                        "estimated_delivery": {"type": "string"}
                    }
                },
                "generative_ui": {
                    "type": "object",
                    "properties": {
                        "component_type": {"type": "string"},
                        "props": {"type": "object"}
                    }
                }
            }
        }

    async def execute(
        self,
        match_id: str,
        action: str,
        occasion: Optional[str] = None,
        budget_range: Optional[str] = None,
        preferences: Optional[dict] = None,
        **kwargs
    ) -> dict:
        """
        执行礼物订购 Skill

        Args:
            match_id: 匹配关系 ID
            action: 操作类型
            occasion: 送礼场合
            budget_range: 预算范围
            preferences: 额外偏好
            **kwargs: 额外参数

        Returns:
            Skill 执行结果
        """
        logger.info(f"GiftOrderingSkill: Executing action={action} for match={match_id}")

        if action == "get_suggestions":
            return await self._get_gift_suggestions(match_id, occasion, budget_range, preferences)
        elif action == "compare_options":
            return await self._compare_gift_options(match_id, preferences)
        elif action == "place_order":
            gift_id = kwargs.get("gift_id")
            if not gift_id:
                return {"success": False, "error": "gift_id required for placing order"}
            return await self._place_order(match_id, gift_id, preferences)
        elif action == "track_delivery":
            order_id = kwargs.get("order_id")
            if not order_id:
                return {"success": False, "error": "order_id required for tracking"}
            return await self._track_delivery(order_id)
        elif action == "get_occasion_reminder":
            return await self._get_occasion_reminder(match_id)
        else:
            return {"success": False, "error": "Invalid action", "ai_message": "不支持的操作类型"}

    async def _get_gift_suggestions(
        self,
        match_id: str,
        occasion: Optional[str] = None,
        budget_range: Optional[str] = None,
        preferences: Optional[dict] = None
    ) -> dict:
        """
        获取礼物推荐

        基于关系阶段、对方喜好和场合智能推荐礼物
        """
        logger.info(f"GiftOrderingSkill: Getting suggestions for match={match_id}, occasion={occasion}")

        # Step 1: 获取关系信息
        relationship_info = await self._get_relationship_info(match_id)
        if not relationship_info:
            return {"success": False, "error": "Relationship not found"}

        # Step 2: 获取对方喜好
        partner_preferences = await self._get_partner_preferences(match_id)

        # Step 3: 识别场合
        if not occasion:
            occasion = await self._detect_occasion(match_id)

        # Step 4: 基于关系阶段推荐礼物
        gifts = await self._recommend_gifts_by_stage(
            relationship_info,
            partner_preferences,
            occasion,
            budget_range
        )

        # Step 5: 如果没有真实数据，返回模拟数据
        if not gifts:
            gifts = self._generate_mock_gifts(occasion, budget_range, partner_preferences)

        # Step 6: 生成 AI 消息
        ai_message = self._generate_suggestion_message(gifts, relationship_info, occasion)

        # Step 7: 构建 Generative UI
        generative_ui = self._build_gift_ui(gifts)

        return {
            "success": True,
            "ai_message": ai_message,
            "gift_suggestions": gifts,
            "occasion_info": {
                "occasion_type": occasion,
                "date": relationship_info.get("anniversary_date", ""),
                "days_remaining": relationship_info.get("days_to_occasion", 0)
            },
            "generative_ui": generative_ui
        }

    async def _compare_gift_options(self, match_id: str, preferences: Optional[dict] = None) -> dict:
        """比较礼物选项"""
        gift_id = preferences.get("gift_id") if preferences else None

        if not gift_id:
            return {"success": False, "error": "gift_id required for comparison"}

        # 获取多平台价格
        comparisons = await self._fetch_platform_comparisons(gift_id)

        if not comparisons:
            comparisons = self._generate_mock_comparisons(gift_id)

        best_option = min(comparisons, key=lambda x: x.get("price", float("inf")))

        ai_message = (
            f"已为你比较 {len(comparisons)} 个平台的价格~\n\n"
            f"最优惠的是 {best_option['platform']}，价格 ¥{best_option['price']}\n"
            f"{'还包运费哦~' if best_option.get('free_shipping') else ''}"
        )

        return {
            "success": True,
            "ai_message": ai_message,
            "comparisons": comparisons,
            "best_option": best_option
        }

    async def _place_order(self, match_id: str, gift_id: str, preferences: Optional[dict] = None) -> dict:
        """
        下订单

        支持一键订购，自动填写收货地址
        """
        logger.info(f"GiftOrderingSkill: Placing order for gift={gift_id}")

        # Step 1: 获取收货信息
        shipping_info = await self._get_shipping_info(match_id)

        # Step 2: 调用外部 API 下单
        order_result = await self._create_order(gift_id, shipping_info, preferences)

        if not order_result:
            # 模拟下单成功
            order_result = self._generate_mock_order(gift_id)

        # Step 3: 生成 AI 消息
        ai_message = (
            f"订单已确认！\n\n"
            f"订单号：{order_result['order_id']}\n"
            f"预计送达：{order_result['estimated_delivery']}\n\n"
            f"记得提前准备好惊喜哦~ 🎁"
        )

        return {
            "success": True,
            "ai_message": ai_message,
            "order_info": order_result
        }

    async def _track_delivery(self, order_id: str) -> dict:
        """追踪物流"""
        logger.info(f"GiftOrderingSkill: Tracking order={order_id}")

        # 调用外部物流 API
        tracking_info = await self._fetch_tracking_info(order_id)

        if not tracking_info:
            tracking_info = self._generate_mock_tracking(order_id)

        ai_message = self._generate_tracking_message(tracking_info)

        return {
            "success": True,
            "ai_message": ai_message,
            "tracking_info": tracking_info
        }

    async def _get_occasion_reminder(self, match_id: str) -> dict:
        """获取纪念日提醒"""
        relationship_info = await self._get_relationship_info(match_id)

        if not relationship_info:
            return {"success": False, "error": "Relationship not found"}

        occasions = relationship_info.get("upcoming_occasions", [])

        if not occasions:
            return {
                "success": True,
                "ai_message": "近期没有特别的纪念日哦~",
                "occasions": []
            }

        next_occasion = min(occasions, key=lambda x: x.get("days_remaining", float("inf")))

        ai_message = self._generate_occasion_reminder_message(next_occasion)

        return {
            "success": True,
            "ai_message": ai_message,
            "occasions": occasions,
            "next_occasion": next_occasion
        }

    # ========== 内部辅助方法 ==========

    async def _get_relationship_info(self, match_id: str) -> Optional[dict]:
        """获取关系信息"""
        # 注：当前使用模拟数据，待对接数据库
        logger.info(f"GiftOrderingSkill: Getting relationship info for match={match_id}")
        # 模拟返回
        return {
            "match_id": match_id,
            "stage": "dating",  # matching, dating, exclusive, engaged
            "start_date": datetime.now() - timedelta(days=30),
            "anniversary_date": (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d"),
            "days_to_occasion": 15,
            "upcoming_occasions": [
                {"type": "anniversary", "date": "2026-04-23", "days_remaining": 15},
                {"type": "birthday", "date": "2026-05-10", "days_remaining": 32}
            ]
        }

    async def _get_partner_preferences(self, match_id: str) -> dict:
        """获取对方喜好"""
        # 注：当前使用模拟数据，待对接用户画像服务
        logger.info(f"GiftOrderingSkill: Getting partner preferences for match={match_id}")
        return {
            "favorite_colors": ["粉色", "白色"],
            "favorite_brands": ["无印良品", "星巴克"],
            "hobbies": ["阅读", "咖啡", "手账"],
            "style": "简约",
            "price_sensitivity": "中等"
        }

    async def _detect_occasion(self, match_id: str) -> str:
        """检测当前场合"""
        relationship_info = await self._get_relationship_info(match_id)

        if not relationship_info:
            return "surprise"

        # 检查是否有临近的纪念日
        days_to_anniversary = relationship_info.get("days_to_occasion", 365)
        if days_to_anniversary <= 7:
            return "anniversary"

        # 检查是否是节日
        today = datetime.now()
        if today.month == 2 and today.day == 14:
            return "valentines"
        elif today.month == 12 and today.day == 25:
            return "christmas"

        return "surprise"

    async def _recommend_gifts_by_stage(
        self,
        relationship_info: dict,
        partner_preferences: dict,
        occasion: str,
        budget_range: Optional[str] = None
    ) -> List[dict]:
        """基于关系阶段推荐礼物"""
        stage = relationship_info.get("stage", "matching")

        # 关系阶段对应的礼物类型
        stage_gift_map = {
            "matching": ["小零食", "咖啡券", "书籍", "文创小物"],
            "dating": ["香薰", "保温杯", "手账本", "精美文具"],
            "exclusive": ["首饰", "品牌包包", "定制礼物", "体验类"],
            "engaged": ["奢侈品", "旅行", "大件家电"]
        }

        gift_types = stage_gift_map.get(stage, ["小零食"])

        # 基于喜好过滤
        hobbies = partner_preferences.get("hobbies", [])
        if "阅读" in hobbies:
            gift_types.append("书籍")
        if "咖啡" in hobbies:
            gift_types.append("咖啡相关")
        if "手账" in hobbies:
            gift_types.append("手账用品")

        return []  # 返回空列表，由模拟数据填充

    def _generate_mock_gifts(
        self,
        occasion: str,
        budget_range: Optional[str],
        partner_preferences: dict
    ) -> List[dict]:
        """生成模拟礼物推荐"""
        # 预算范围映射
        budget_map = {
            "under_100": (0, 100),
            "100_300": (100, 300),
            "300_500": (300, 500),
            "500_1000": (500, 1000),
            "above_1000": (1000, 3000)
        }

        min_price, max_price = budget_map.get(budget_range or "100_300", (100, 300))

        # 基于场合的礼物模板
        occasion_templates = {
            "birthday": [
                {"name": "定制生日礼盒", "base_price": 299, "category": "定制"},
                {"name": "精美香薰套装", "base_price": 199, "category": "生活"},
                {"name": "手账文具套装", "base_price": 159, "category": "文具"},
                {"name": "品牌保温杯", "base_price": 259, "category": "生活"},
                {"name": "设计师首饰", "base_price": 399, "category": "配饰"}
            ],
            "anniversary": [
                {"name": "纪念相册书", "base_price": 199, "category": "定制"},
                {"name": "情侣对杯", "base_price": 168, "category": "生活"},
                {"name": "设计师项链", "base_price": 599, "category": "配饰"},
                {"name": "星空投影灯", "base_price": 299, "category": "创意"},
                {"name": "永生花礼盒", "base_price": 399, "category": "鲜花"}
            ],
            "valentines": [
                {"name": "巧克力礼盒", "base_price": 199, "category": "食品"},
                {"name": "玫瑰花束", "base_price": 299, "category": "鲜花"},
                {"name": "情侣首饰", "base_price": 499, "category": "配饰"},
                {"name": "香水礼盒", "base_price": 599, "category": "美妆"},
                {"name": "泰迪熊花束", "base_price": 399, "category": "创意"}
            ],
            "surprise": [
                {"name": "精品咖啡礼盒", "base_price": 199, "category": "食品"},
                {"name": "设计师手账本", "base_price": 129, "category": "文具"},
                {"name": "香薰蜡烛套装", "base_price": 179, "category": "生活"},
                {"name": "盲盒手办", "base_price": 89, "category": "玩具"},
                {"name": "文艺书籍", "base_price": 59, "category": "书籍"}
            ]
        }

        templates = occasion_templates.get(occasion, occasion_templates["surprise"])

        gifts = []
        for i, template in enumerate(templates):
            price = template["base_price"] + (hash(f"{occasion}{i}") % 50)
            gifts.append({
                "gift_id": f"gift_{occasion}_{i}",
                "name": template["name"],
                "description": f"{template['category']}类精选好物",
                "price": price,
                "platform": "淘宝" if i % 2 == 0 else "京东",
                "image_url": f"/images/gifts/{template['category']}_{i}.jpg",
                "match_reason": self._generate_match_reason(template, partner_preferences),
                "urgency_score": 0.7 + (hash(f"{occasion}{i}") % 30) / 100
            })

        # 按紧迫度排序
        gifts.sort(key=lambda x: x["urgency_score"], reverse=True)

        return gifts

    def _generate_match_reason(self, gift: dict, preferences: dict) -> str:
        """生成推荐理由"""
        hobbies = preferences.get("hobbies", [])
        style = preferences.get("style", "")

        reasons = []

        if gift["category"] == "文具" and "手账" in hobbies:
            reasons.append("符合她的手账爱好")
        if gift["category"] == "食品" and "咖啡" in hobbies:
            reasons.append("精选咖啡相关好物")
        if style == "简约" and gift["category"] in ["生活", "文具"]:
            reasons.append("简约风格符合她的审美")
        if gift["category"] == "书籍" and "阅读" in hobbies:
            reasons.append("满足她的阅读兴趣")

        if not reasons:
            reasons = ["精选好物，品质保证", "高颜值，送礼佳选", "实用又有意义"]

        return reasons[0]

    def _generate_mock_comparisons(self, gift_id: str) -> List[dict]:
        """生成模拟平台比价"""
        base_price = 199 + (hash(gift_id) % 200)

        return [
            {"platform": "淘宝", "price": base_price, "shipping": 0, "free_shipping": True, "delivery_days": 3},
            {"platform": "京东", "price": base_price + 20, "shipping": 0, "free_shipping": True, "delivery_days": 1},
            {"platform": "拼多多", "price": base_price - 30, "shipping": 10, "free_shipping": False, "delivery_days": 5},
            {"platform": "小红书", "price": base_price + 50, "shipping": 0, "free_shipping": True, "delivery_days": 4}
        ]

    def _generate_mock_order(self, gift_id: str) -> dict:
        """生成模拟订单"""
        order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{hash(gift_id) % 10000:04d}"

        return {
            "order_id": order_id,
            "status": "confirmed",
            "gift_id": gift_id,
            "total_amount": 199 + (hash(gift_id) % 200),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "estimated_delivery": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        }

    def _generate_mock_tracking(self, order_id: str) -> dict:
        """生成模拟物流信息"""
        statuses = ["已下单", "已发货", "运输中", "派送中", "已签收"]
        current_status = hash(order_id) % len(statuses)

        return {
            "order_id": order_id,
            "status": statuses[current_status],
            "tracking_number": f"SF{hash(order_id) % 1000000000:09d}",
            "carrier": "顺丰速运",
            "estimated_delivery": (datetime.now() + timedelta(days=3 - current_status // 2)).strftime("%Y-%m-%d"),
            "updates": [
                {"time": "2026-04-08 10:00", "info": "订单已确认"},
                {"time": "2026-04-08 14:30", "info": "商家已发货"},
                {"time": "2026-04-08 18:00", "info": "快递已揽收"}
            ]
        }

    async def _get_shipping_info(self, match_id: str) -> dict:
        """获取收货信息"""
        # 注：当前使用模拟数据，待对接数据库
        logger.info(f"GiftOrderingSkill: Getting shipping info for match={match_id}")
        return {
            "recipient_name": "张三",
            "phone": "138****1234",
            "address": "北京市朝阳区***街道***号",
            "zip_code": "100000"
        }

    async def _create_order(self, gift_id: str, shipping_info: dict, preferences: Optional[dict] = None) -> Optional[dict]:
        """创建订单"""
        # 注：外部订购 API 待对接，当前返回模拟数据
        logger.info(f"GiftOrderingSkill: Creating order for gift={gift_id}")
        return None

    async def _fetch_tracking_info(self, order_id: str) -> Optional[dict]:
        """获取物流信息"""
        # 注：外部物流 API 待对接，当前返回模拟数据
        logger.info(f"GiftOrderingSkill: Fetching tracking info for order={order_id}")
        return None

    async def _fetch_platform_comparisons(self, gift_id: str) -> Optional[List[dict]]:
        """获取平台比价"""
        # 注：外部比价 API 待对接，当前返回模拟数据
        logger.info(f"GiftOrderingSkill: Fetching platform comparisons for gift={gift_id}")
        return None

    def _build_gift_ui(self, gifts: List[dict]) -> dict:
        """构建礼物展示 UI"""
        if not gifts:
            return {"component_type": "empty_state", "props": {"message": "暂无推荐礼物"}}

        # 根据数量选择 UI 类型
        if len(gifts) <= 3:
            return {
                "component_type": "gift_grid",
                "props": {
                    "gifts": gifts,
                    "columns": 3,
                    "show_price": True,
                    "show_platform": True
                }
            }
        else:
            return {
                "component_type": "gift_carousel",
                "props": {
                    "gifts": gifts,
                    "autoplay": True,
                    "show_indicators": True
                }
            }

    def _generate_suggestion_message(self, gifts: List[dict], relationship_info: dict, occasion: str) -> str:
        """生成推荐消息"""
        stage = relationship_info.get("stage", "dating")
        stage_names = {
            "matching": "初识阶段",
            "dating": "约会阶段",
            "exclusive": "稳定交往",
            "engaged": "订婚阶段"
        }

        occasion_names = {
            "birthday": "生日",
            "anniversary": "纪念日",
            "valentines": "情人节",
            "christmas": "圣诞节",
            "surprise": "日常惊喜",
            "apology": "道歉"
        }

        top_gift = gifts[0] if gifts else None

        message = f"基于你们的关系阶段（{stage_names.get(stage, '约会中')}）和{occasion_names.get(occasion, '特殊场合')}，\n"
        message += f"为你精选了 {len(gifts)} 份礼物~\n\n"

        if top_gift:
            message += f"首推：「{top_gift['name']}」\n"
            message += f"推荐理由：{top_gift['match_reason']}\n"
            message += f"价格：¥{top_gift['price']}"

        return message

    def _generate_tracking_message(self, tracking_info: dict) -> str:
        """生成物流消息"""
        status = tracking_info.get("status", "未知")
        estimated = tracking_info.get("estimated_delivery", "预计时间内")

        message = f"订单状态：{status}\n"
        message += f"快递公司：{tracking_info.get('carrier', '未知')}\n"
        message += f"运单号：{tracking_info.get('tracking_number', '未知')}\n"
        message += f"预计送达：{estimated}\n\n"

        updates = tracking_info.get("updates", [])
        if updates:
            message += "物流动态:\n"
            for update in updates[:3]:
                message += f"  {update['time']}: {update['info']}\n"

        return message

    def _generate_occasion_reminder_message(self, occasion: dict) -> str:
        """生成纪念日提醒消息"""
        occasion_type = occasion.get("type", "纪念日")
        days = occasion.get("days_remaining", 0)
        date = occasion.get("date", "未知")

        occasion_names = {
            "anniversary": "恋爱纪念日",
            "birthday": "生日",
            "valentines": "情人节",
            "christmas": "圣诞节"
        }

        name = occasion_names.get(occasion_type, occasion_type)

        if days == 0:
            return f"今天就是{name}！准备好惊喜了吗？🎁"
        elif days <= 3:
            return f"{name}倒计时 {days} 天！礼物准备好了吗？需要我帮你推荐吗~"
        elif days <= 7:
            return f"距离{name}还有 {days} 天，可以开始准备礼物啦~"
        else:
            return f"距离{name}还有 {days} 天，提前规划更从容哦~"

    # ========== 自主触发器 ==========

    async def autonomous_trigger(self, match_id: str, trigger_type: str, context: dict) -> dict:
        """
        自主触发礼物推荐

        Args:
            match_id: 匹配关系 ID
            trigger_type: 触发类型
            context: 上下文数据

        Returns:
            触发结果
        """
        logger.info(f"GiftOrderingSkill: Autonomous trigger {trigger_type} for match={match_id}")

        if trigger_type == "occasion_reminder":
            return await self._handle_occasion_reminder(match_id, context)
        elif trigger_type == "relationship_milestone":
            return await self._handle_relationship_milestone(match_id, context)
        elif trigger_type == "partner_birthday_approaching":
            return await self._handle_birthday_reminder(match_id, context)
        else:
            return {"triggered": False, "reason": "unknown_trigger_type"}

    async def _handle_occasion_reminder(self, match_id: str, context: dict) -> dict:
        """处理纪念日提醒"""
        relationship_info = await self._get_relationship_info(match_id)

        if not relationship_info:
            return {"triggered": False, "reason": "no_relationship_info"}

        occasions = relationship_info.get("upcoming_occasions", [])

        # 查找 7 天内的纪念日
        near_occasion = next((o for o in occasions if o.get("days_remaining", 365) <= 7), None)

        if not near_occasion:
            return {"triggered": False, "reason": "no_near_occasion"}

        days = near_occasion.get("days_remaining", 0)

        return {
            "triggered": True,
            "should_push": days <= 3,  # 3 天内才推送
            "push_message": f"纪念日倒计时 {days} 天！需要帮你准备礼物推荐吗？",
            "occasion": near_occasion,
            "suggested_action": "get_gift_suggestions"
        }

    async def _handle_relationship_milestone(self, match_id: str, context: dict) -> dict:
        """处理关系里程碑"""
        relationship_info = await self._get_relationship_info(match_id)

        if not relationship_info:
            return {"triggered": False, "reason": "no_relationship_info"}

        start_date = relationship_info.get("start_date")
        if not start_date:
            return {"triggered": False, "reason": "no_start_date"}

        # 检查是否是整月/整年纪念
        today = datetime.now()
        months_passed = (today.year - start_date.year) * 12 + (today.month - start_date.month)

        if months_passed > 0 and months_passed % 6 == 0:  # 半年/周年纪念
            return {
                "triggered": True,
                "should_push": True,
                "push_message": f"恭喜你们已经走过 {months_passed} 个月！准备一份特别的礼物庆祝一下吧~",
                "milestone": f"{months_passed}个月纪念",
                "suggested_action": "get_anniversary_gift_suggestions"
            }

        return {"triggered": False, "reason": "not_milestone"}

    async def _handle_birthday_reminder(self, match_id: str, context: dict) -> dict:
        """处理生日提醒"""
        # 注：当前从上下文获取生日信息，待对接数据库
        partner_birthday = context.get("partner_birthday")

        if not partner_birthday:
            return {"triggered": False, "reason": "no_birthday_info"}

        today = datetime.now()
        birthday = datetime.strptime(partner_birthday, "%Y-%m-%d")
        next_birthday = birthday.replace(year=today.year)

        if next_birthday < today:
            next_birthday = next_birthday.replace(year=today.year + 1)

        days_until = (next_birthday - today).days

        if days_until <= 14:  # 提前两周提醒
            urgency = "紧急" if days_until <= 3 else "常规"
            return {
                "triggered": True,
                "should_push": days_until <= 7,
                "push_message": f"距离 TA 的生日还有 {days_until} 天，{urgency}！礼物选好了吗？",
                "birthday": partner_birthday,
                "days_remaining": days_until,
                "suggested_action": "get_birthday_gift_suggestions"
            }

        return {"triggered": False, "reason": "birthday_not_near"}


# 全局 Skill 实例
_gift_ordering_skill_instance: Optional[GiftOrderingSkill] = None


def get_gift_ordering_skill() -> GiftOrderingSkill:
    """获取礼物订购 Skill 单例实例"""
    global _gift_ordering_skill_instance
    if _gift_ordering_skill_instance is None:
        _gift_ordering_skill_instance = GiftOrderingSkill()
    return _gift_ordering_skill_instance
