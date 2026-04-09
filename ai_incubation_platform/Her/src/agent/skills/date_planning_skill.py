"""
约会策划 Skill

AI 约会策划师 - 自主策划约会
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from agent.skills.base import BaseSkill
from utils.logger import logger


class DatePlanningAgentSkill:
    """
    约会策划 Skill

    核心能力:
    - 根据关系阶段推荐约会类型
    - 个性化地点推荐
    - 时间安排建议
    - 预算估算
    - 备选方案生成

    自主触发条件:
    - 关系阶段升级为"首次约会"
    - 双方聊天提到"见面"/"约会"关键词
    - 周末/节假日前主动建议
    """

    name = "date_planning"
    version = "1.0.0"
    description = """
    AI 约会策划师

    能力:
    - 根据关系阶段推荐约会类型
    - 个性化地点推荐
    - 时间安排建议
    - 预算估算
    - 备选方案生成
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
                "preferences": {
                    "type": "object",
                    "properties": {
                        "date_type": {
                            "type": "string",
                            "enum": ["casual", "formal", "romantic", "adventurous", "cultural"]
                        },
                        "budget_range": {
                            "type": "string",
                            "enum": ["low", "medium", "high"]
                        },
                        "duration": {
                            "type": "string",
                            "enum": ["short", "medium", "long"]
                        },
                        "time_preference": {
                            "type": "string",
                            "enum": ["morning", "afternoon", "evening", "any"]
                        }
                    }
                },
                "context": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "special_occasion": {"type": "string"}
                    }
                }
            },
            "required": ["match_id"]
        }

    def get_output_schema(self) -> dict:
        """获取输出参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "ai_message": {"type": "string"},
                "date_type": {"type": "string"},
                "plans": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "type": {"type": "string"},
                            "description": {"type": "string"},
                            "duration": {"type": "string"},
                            "budget_estimate": {"type": "string"},
                            "location_suggestions": {"type": "array"},
                            "tips": {"type": "array"},
                            "confidence_score": {"type": "number"}
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
                "booking_assistance": {
                    "type": "object",
                    "properties": {
                        "requires_reservation": {"type": "boolean"},
                        "booking_links": {"type": "array"}
                    }
                }
            }
        }

    async def execute(
        self,
        match_id: str,
        preferences: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> dict:
        """
        执行约会策划 Skill

        Args:
            match_id: 匹配记录 ID
            preferences: 偏好设置
            context: 上下文信息
            **kwargs: 额外参数

        Returns:
            Skill 执行结果
        """
        logger.info(f"DatePlanningAgentSkill: Executing for match_id={match_id}")

        # 获取匹配信息
        match_info = self._get_match_info(match_id)
        if not match_info:
            return {
                "success": False,
                "error": "Match not found",
                "ai_message": "未找到匹配记录"
            }

        # 获取关系阶段
        relationship_stage = match_info.get("relationship_stage", "chatting")

        # 根据关系阶段推荐约会类型
        date_type = self._recommend_date_type(relationship_stage, preferences)

        # 生成约会方案
        date_plans = await self._generate_date_plans(match_id, date_type, preferences, context)

        # 构建 UI
        generative_ui = self._build_generative_ui(date_plans)

        # 生成 AI 消息
        ai_message = self._generate_message(date_type, date_plans)

        return {
            "success": True,
            "ai_message": ai_message,
            "date_type": date_type,
            "plans": date_plans,
            "generative_ui": generative_ui,
            "booking_assistance": self._get_booking_assistance(date_plans)
        }

    def _get_match_info(self, match_id: str) -> Optional[dict]:
        """获取匹配信息"""
        # 从数据库获取真实匹配信息
        try:
            from db.models import MatchHistoryDB, UserDB
            from db.database import SessionLocal
            import json

            db = SessionLocal()

            # 获取匹配记录
            match = db.query(MatchHistoryDB).filter(MatchHistoryDB.id == match_id).first()

            if match:
                # 获取双方用户信息
                user_1 = db.query(UserDB).filter(UserDB.id == match.user_id_1).first()
                user_2 = db.query(UserDB).filter(UserDB.id == match.user_id_2).first()

                if user_1 and user_2:
                    # 解析兴趣
                    interests_1 = json.loads(user_1.interests) if user_1.interests else []
                    interests_2 = json.loads(user_2.interests) if user_2.interests else []
                    common_interests = list(set(interests_1) & set(interests_2))

                    db.close()

                    return {
                        "id": match_id,
                        "user_id_1": user_1.id,
                        "user_id_2": user_2.id,
                        "relationship_stage": self._infer_relationship_stage(match_id),
                        "common_interests": common_interests if common_interests else ["美食", "电影"],
                        "user_locations": {
                            "user_1": user_1.location or "未知",
                            "user_2": user_2.location or "未知"
                        },
                        "user_profiles": {
                            "user_1": {
                                "age": user_1.age,
                                "interests": interests_1,
                                "personality": "未知"
                            },
                            "user_2": {
                                "age": user_2.age,
                                "interests": interests_2,
                                "personality": "未知"
                            }
                        }
                    }

            db.close()

        except Exception as e:
            logger.error(f"DatePlanningSkill: Error getting match info: {e}")

        # 降级返回模拟数据
        return {
            "id": match_id,
            "user_id_1": "user-1",
            "user_id_2": "user-2",
            "relationship_stage": "dating",
            "common_interests": ["旅行", "美食", "电影"],
            "user_locations": {
                "user_1": "上海市浦东新区",
                "user_2": "上海市徐汇区"
            },
            "user_profiles": {
                "user_1": {"age": 28, "interests": ["美食", "电影", "健身"], "personality": "外向"},
                "user_2": {"age": 26, "interests": ["旅行", "摄影", "咖啡"], "personality": "温和"}
            }
        }

    def _infer_relationship_stage(self, match_id: str) -> str:
        """推断关系阶段"""
        # 根据对话数量推断关系阶段
        try:
            from db.models import ChatConversationDB
            from db.database import SessionLocal

            db = SessionLocal()
            match = db.query(MatchHistoryDB).filter(MatchHistoryDB.id == match_id).first()

            if match:
                # 计算对话数量
                conv_count = db.query(ChatConversationDB).filter(
                    ((ChatConversationDB.user_id_1 == match.user_id_1) &
                     (ChatConversationDB.user_id_2 == match.user_id_2)) |
                    ((ChatConversationDB.user_id_1 == match.user_id_2) &
                     (ChatConversationDB.user_id_2 == match.user_id_1))
                ).count()

                db.close()

                if conv_count == 0:
                    return "matched"
                elif conv_count < 10:
                    return "chatting"
                elif conv_count < 50:
                    return "exchanged_contacts"
                else:
                    return "dating"

            db.close()

        except Exception as e:
            logger.error(f"DatePlanningSkill: Error inferring relationship stage: {e}")

        return "dating"

    def _recommend_date_type(self, stage: str, preferences: dict = None) -> str:
        """根据关系阶段推荐约会类型"""
        # 如果用户有明确偏好，优先使用
        if preferences and preferences.get("date_type"):
            return preferences["date_type"]

        # 否则根据关系阶段推荐
        type_mapping = {
            "matched": "online_activity",       # 线上活动
            "chatting": "casual_meetup",        # 休闲见面
            "exchanged_contacts": "first_date", # 首次约会
            "first_date": "regular_date",       # 常规约会
            "dating": "romantic_date",          # 浪漫约会
            "in_relationship": "special_date"   # 特别约会
        }

        return type_mapping.get(stage, "casual_meetup")

    async def _generate_date_plans(self, match_id: str, date_type: str, preferences: dict = None, context: dict = None) -> list:
        """生成约会方案"""
        match_info = self._get_match_info(match_id)
        if not match_info:
            return []

        common_interests = match_info.get("common_interests", [])
        user_locations = match_info.get("user_locations", {})
        user_profiles = match_info.get("user_profiles", {})

        # 计算中间位置
        midpoint = self._calculate_midpoint(user_locations)

        plans = []

        if date_type == "first_date":
            plans = self._generate_first_date_plans(common_interests, midpoint, preferences, user_profiles)
        elif date_type == "casual_meetup":
            plans = self._generate_casual_date_plans(common_interests, midpoint, preferences)
        elif date_type == "romantic_date":
            plans = self._generate_romantic_date_plans(common_interests, midpoint, preferences)
        elif date_type == "regular_date":
            plans = self._generate_regular_date_plans(common_interests, midpoint, preferences)
        elif date_type == "online_activity":
            plans = self._generate_online_date_plans(common_interests, preferences)
        elif date_type == "special_date":
            plans = self._generate_special_date_plans(common_interests, midpoint, context)

        # 如果没有生成任何方案，返回默认方案
        if not plans:
            plans = self._generate_default_plans(midpoint)

        return plans

    def _generate_first_date_plans(self, interests: list, midpoint: str, preferences: dict, profiles: dict) -> list:
        """生成首次约会方案"""
        plans = [
            {
                "title": "咖啡厅轻松见面",
                "type": "casual",
                "description": "选择一家安静的精品咖啡厅，轻松自在地认识彼此。咖啡厅环境舒适，不会给对方太大压力，适合初次见面。",
                "duration": "1-2 小时",
                "location_suggestions": [
                    self._generate_location("咖啡厅", midpoint, "50-100 元/人"),
                    self._generate_location("茶馆", midpoint, "60-120 元/人")
                ],
                "conversation_starters": [
                    "聊聊最近看的电影/书籍",
                    "分享工作趣事",
                    "讨论共同的兴趣爱好",
                    "聊聊各自的周末活动"
                ],
                "budget_estimate": "50-150 元/人",
                "tips": [
                    "选择公共场所，注意安全",
                    "不要太晚结束，建议下午或傍晚",
                    "提前准备好话题，避免冷场",
                    "穿着得体但不要过于正式"
                ],
                "best_time": "下午 2-5 点或傍晚 6-8 点",
                "confidence_score": 0.95
            },
            {
                "title": "博物馆/艺术展",
                "type": "cultural",
                "description": "一起欣赏艺术作品，在交流中增进了解。展览提供了天然的话题，避免尴尬沉默。",
                "duration": "2-3 小时",
                "location_suggestions": [
                    self._generate_location("美术馆", midpoint, "50-100 元/人"),
                    self._generate_location("博物馆", midpoint, "30-80 元/人")
                ],
                "conversation_starters": [
                    "讨论喜欢的展品",
                    "分享艺术观点",
                    "聊聊各自的审美偏好",
                    "交流看展的体验"
                ],
                "budget_estimate": "100-200 元/人",
                "tips": [
                    "提前查好展览信息和开放时间",
                    "尊重对方观点，不要强加自己的看法",
                    "可以在附近安排简餐，延续交流"
                ],
                "best_time": "上午 10 点或下午 2 点",
                "confidence_score": 0.85
            },
            {
                "title": "户外散步 + 简餐",
                "type": "outdoor",
                "description": "在公园或河边散步，轻松自然地聊天。户外活动能缓解紧张感，创造轻松氛围。",
                "duration": "2-3 小时",
                "location_suggestions": [
                    self._generate_location("公园", midpoint, "免费"),
                    self._generate_location("河边步道", midpoint, "免费")
                ],
                "conversation_starters": [
                    "聊聊日常生活",
                    "分享童年回忆",
                    "讨论未来的计划",
                    "分享喜欢的季节和活动"
                ],
                "budget_estimate": "50-150 元/人 (简餐)",
                "tips": [
                    "注意天气预报，选择晴天",
                    "穿着舒适的鞋子",
                    "可以带瓶水",
                    "准备一个备选室内方案"
                ],
                "best_time": "下午 3-6 点",
                "confidence_score": 0.8
            }
        ]

        # 根据兴趣调整优先级
        if "艺术" in interests or "摄影" in interests:
            plans[1]["confidence_score"] = 0.95
        if "户外" in interests or "运动" in interests:
            plans[2]["confidence_score"] = 0.9

        return plans

    def _generate_casual_date_plans(self, interests: list, midpoint: str, preferences: dict) -> list:
        """生成休闲约会方案"""
        return [
            {
                "title": "市集/小店探索",
                "type": "casual",
                "description": "一起逛创意市集，发现有趣的小店，在轻松的氛围中增进了解。",
                "duration": "2-3 小时",
                "location_suggestions": [
                    self._generate_location("创意市集", midpoint, "自由消费"),
                    self._generate_location("文艺街区", midpoint, "自由消费")
                ],
                "budget_estimate": "100-300 元/人",
                "tips": [
                    "可以一起品尝小吃",
                    "看到有趣的东西可以互相分享",
                    "不要有购买压力，享受过程"
                ],
                "best_time": "周末下午",
                "confidence_score": 0.85
            },
            {
                "title": "电影 + 讨论",
                "type": "entertainment",
                "description": "一起看一场电影，之后找个地方聊聊观后感，是了解彼此价值观的好方式。",
                "duration": "3-4 小时",
                "location_suggestions": [
                    self._generate_location("电影院", midpoint, "50-100 元/人")
                ],
                "budget_estimate": "100-200 元/人",
                "tips": [
                    "选择有讨论空间的电影",
                    "观影后找个安静的地方聊聊感受",
                    "尊重对方对电影的理解"
                ],
                "best_time": "下午或晚上",
                "confidence_score": 0.8
            }
        ]

    def _generate_romantic_date_plans(self, interests: list, midpoint: str, preferences: dict) -> list:
        """生成浪漫约会方案"""
        return [
            {
                "title": "浪漫晚餐",
                "type": "romantic",
                "description": "选择一家有氛围的餐厅，享受二人世界。晚餐是增进感情的经典方式。",
                "duration": "2-3 小时",
                "location_suggestions": [
                    self._generate_location("法式餐厅", midpoint, "300-500 元/人"),
                    self._generate_location("江景餐厅", midpoint, "400-600 元/人"),
                    self._generate_location("日式料理", midpoint, "200-400 元/人")
                ],
                "budget_estimate": "300-600 元/人",
                "tips": [
                    "提前预订位置，要求安静的角落",
                    "注意着装要求",
                    "可以准备小惊喜",
                    "不要看手机，专注当下"
                ],
                "best_time": "晚上 7-9 点",
                "confidence_score": 0.95
            },
            {
                "title": "夜景散步",
                "type": "romantic",
                "description": "在城市的夜景中散步，营造浪漫氛围。适合关系稳定后的约会。",
                "duration": "1-2 小时",
                "location_suggestions": [
                    self._generate_location("观景台", midpoint, "免费"),
                    self._generate_location("滨江道", midpoint, "免费")
                ],
                "budget_estimate": "50-100 元/人 (饮品)",
                "tips": [
                    "注意保暖",
                    "可以带个小礼物",
                    "选择合适的时机表达心意"
                ],
                "best_time": "晚上 8-10 点",
                "confidence_score": 0.85
            }
        ]

    def _generate_regular_date_plans(self, interests: list, midpoint: str, preferences: dict) -> list:
        """生成常规约会方案"""
        plans = []

        # 基于兴趣生成
        if "美食" in interests:
            plans.append({
                "title": "美食探索",
                "type": "food",
                "description": "一起探索新的餐厅或美食街，分享美食体验。",
                "duration": "2-3 小时",
                "budget_estimate": "150-300 元/人",
                "confidence_score": 0.9
            })

        if "运动" in interests or "健身" in interests:
            plans.append({
                "title": "一起运动",
                "type": "active",
                "description": "一起打羽毛球、爬山或健身，增进互动的同时保持健康。",
                "duration": "2-3 小时",
                "budget_estimate": "50-150 元/人",
                "confidence_score": 0.85
            })

        if "电影" in interests:
            plans.append({
                "title": "私人影院",
                "type": "entertainment",
                "description": "选择一个舒适的私人影院，享受二人世界。",
                "duration": "2-4 小时",
                "budget_estimate": "100-200 元/人",
                "confidence_score": 0.85
            })

        return plans if plans else self._generate_casual_date_plans(interests, midpoint, preferences)

    def _generate_online_date_plans(self, interests: list, preferences: dict) -> list:
        """生成线上约会方案"""
        return [
            {
                "title": "视频聊天 + 云观影",
                "type": "online",
                "description": "通过视频通话一起看电影，分享实时感受。",
                "duration": "2-3 小时",
                "budget_estimate": "免费",
                "tips": [
                    "提前测试网络和设备",
                    "选择双方都能访问的影片",
                    "准备好零食和饮料"
                ],
                "confidence_score": 0.8
            },
            {
                "title": "在线游戏",
                "type": "online",
                "description": "一起玩在线游戏，在互动中增进了解。",
                "duration": "1-2 小时",
                "budget_estimate": "免费",
                "confidence_score": 0.75
            }
        ]

    def _generate_special_date_plans(self, interests: list, midpoint: str, context: dict) -> list:
        """生成特别约会方案"""
        occasion = context.get("special_occasion", "anniversary") if context else "anniversary"

        return [
            {
                "title": "纪念日特别约会",
                "type": "special",
                "description": f"为{occasion}特别策划的浪漫约会",
                "duration": "半天/全天",
                "budget_estimate": "500-1000 元/人",
                "tips": [
                    "提前规划所有细节",
                    "准备特别的礼物或惊喜",
                    "记录美好时刻"
                ],
                "confidence_score": 0.95
            }
        ]

    def _generate_default_plans(self, midpoint: str) -> list:
        """生成默认约会方案"""
        return [
            {
                "title": "咖啡 + 散步",
                "type": "casual",
                "description": "先在咖啡厅坐坐，然后在附近散步聊天。",
                "duration": "2-3 小时",
                "budget_estimate": "100-200 元/人",
                "confidence_score": 0.8
            }
        ]

    def _generate_location(self, location_type: str, midpoint: str, price_range: str) -> dict:
        """生成地点建议"""
        # 使用高德地图 API 搜索具体地点
        # 注：当前同步调用，生产环境应使用异步
        try:
            import asyncio
            from integration.amap_client import get_amap_client

            amap = get_amap_client()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 搜索地点
            places = loop.run_until_complete(
                amap.search_places(keywords=location_type, location=midpoint, radius=2000, limit=3)
            )

            if places:
                place = places[0]
                return {
                    "name": place.get("name", f"{location_type}推荐"),
                    "address": place.get("address", midpoint),
                    "area": place.get("location", midpoint),
                    "price_range": price_range,
                    "phone": place.get("tel", ""),
                    "rating": place.get("rating", ""),
                    "location": place.get("location")
                }

            loop.close()

        except Exception as e:
            logger.error(f"DatePlanningSkill: Error searching location: {e}")

        # 降级返回模拟数据
        return {
            "name": f"{location_type}推荐",
            "area": midpoint,
            "price_range": price_range,
            "note": "具体地点可根据实际位置查询"
        }

    def _calculate_midpoint(self, locations: dict) -> str:
        """
        计算中间位置

        使用高德地图 API 计算两个位置之间的地理中点
        """
        try:
            from integration.amap_client import get_amap_client
            import asyncio

            user_1_loc = locations.get("user_1", "")
            user_2_loc = locations.get("user_2", "")

            amap = get_amap_client()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 地理编码获取坐标
            geo1 = loop.run_until_complete(amap.geocode(user_1_loc)) if user_1_loc else None
            geo2 = loop.run_until_complete(amap.geocode(user_2_loc)) if user_2_loc else None

            if geo1 and geo2:
                # 解析坐标
                loc1 = geo1.get("location", "")
                loc2 = geo2.get("location", "")

                if loc1 and loc2:
                    lng1, lat1 = map(float, loc1.split(","))
                    lng2, lat2 = map(float, loc2.split(","))

                    # 计算中点坐标
                    mid_lng = (lng1 + lng2) / 2
                    mid_lat = (lat1 + lat2) / 2

                    # 逆地理编码获取地址
                    mid_geo = loop.run_until_complete(
                        amap.reverse_geocode(mid_lat, mid_lng)
                    )

                    loop.close()

                    if mid_geo:
                        return mid_geo.get("formatted_address", f"{mid_lng},{mid_lat}")

            loop.close()

        except Exception as e:
            logger.error(f"DatePlanningSkill: Error calculating midpoint: {e}")

        # 降级处理：简单字符串中点（不精确）
        if user_1_loc and user_2_loc:
            return f"{user_1_loc}与{user_2_loc}之间"

        return "市中心区域"

    def _build_generative_ui(self, date_plans: list) -> dict:
        """构建约会 UI 配置"""
        if not date_plans:
            return {
                "component_type": "empty_state",
                "props": {"message": "暂无约会方案", "description": "调整条件再试试"}
            }

        return {
            "component_type": "date_plan_carousel",
            "props": {
                "plans": date_plans,
                "show_details": True,
                "allow_filtering": True,
                "show_budget": True,
                "show_confidence": True,
                "booking_enabled": True
            }
        }

    def _generate_message(self, date_type: str, date_plans: list) -> str:
        """生成 AI 消息"""
        if not date_plans:
            return "暂时没有想到合适的约会方案，可以告诉我你的偏好吗？"

        type_names = {
            "first_date": "首次约会",
            "casual_meetup": "休闲约会",
            "romantic_date": "浪漫约会",
            "regular_date": "常规约会",
            "online_activity": "线上活动",
            "special_date": "特别约会"
        }

        message = f"为你们的{type_names.get(date_type, '约会')}策划了{len(date_plans)}个方案：\n\n"

        for i, plan in enumerate(date_plans[:3], 1):
            message += f"{i}. {plan.get('title', '')}\n"
            message += f"   {plan.get('description', '')}\n"
            message += f"   预算：{plan.get('budget_estimate', '')} | 时长：{plan.get('duration', '')}\n\n"

        message += "小贴士：选择你们都觉得舒适的方式最重要，不要有太大压力~"

        return message

    def _get_booking_assistance(self, date_plans: list) -> dict:
        """获取预订协助信息"""
        requires_reservation = False
        booking_links = []

        for plan in date_plans:
            if plan.get("type") in ["romantic", "formal"]:
                requires_reservation = True
                booking_links.append({
                    "plan": plan.get("title"),
                    "type": "restaurant",
                    "suggestion": "建议通过大众点评/美团预订"
                })

        return {
            "requires_reservation": requires_reservation,
            "booking_links": booking_links
        }

    # 自主触发器

    async def autonomous_trigger(self, user_id: str, trigger_type: str, context: dict) -> dict:
        """
        自主触发约会策划

        Args:
            user_id: 用户 ID
            trigger_type: 触发类型
            context: 上下文数据

        Returns:
            触发结果
        """
        logger.info(f"DatePlanningAgentSkill: Autonomous trigger {trigger_type} for {user_id}")

        if trigger_type == "relationship_stage_upgrade":
            return await self._handle_stage_upgrade(user_id, context)
        elif trigger_type == "date_keywords_detected":
            return await self._handle_date_keywords(user_id, context)
        elif trigger_type == "weekend_approaching":
            return await self._handle_weekend(user_id, context)
        elif trigger_type == "anniversary_approaching":
            return await self._handle_anniversary(user_id, context)
        else:
            return {"triggered": False, "reason": "unknown_trigger_type"}

    async def _handle_stage_upgrade(self, user_id: str, context: dict) -> dict:
        """处理关系阶段升级"""
        new_stage = context.get("new_stage", "")
        match_id = context.get("match_id")

        if new_stage == "first_date":
            # 首次约会，主动提供约会建议
            result = await self.execute(match_id=match_id)

            return {
                "triggered": True,
                "should_push": True,
                "push_message": "恭喜你们进入首次约会阶段！AI 已经为你们策划了几个约会方案，快去看看吧~",
                "plans": result.get("plans", [])
            }

        return {"triggered": False, "reason": "stage_not_applicable"}

    async def _handle_date_keywords(self, user_id: str, context: dict) -> dict:
        """处理约会关键词检测"""
        match_id = context.get("match_id")
        keywords = context.get("keywords", [])

        result = await self.execute(match_id=match_id)

        return {
            "triggered": True,
            "should_push": True,
            "push_message": f"注意到你们在聊{', '.join(keywords)}的话题，AI 准备了一些约会建议~",
            "plans": result.get("plans", [])
        }

    async def _handle_weekend(self, user_id: str, context: dict) -> dict:
        """处理周末临近"""
        match_id = context.get("match_id")
        is_weekend = context.get("is_weekend", False)

        if is_weekend:
            result = await self.execute(match_id=match_id)

            return {
                "triggered": True,
                "should_push": True,
                "push_message": "周末快到了，有什么约会计划吗？AI 为你们准备了一些建议~",
                "plans": result.get("plans", [])
            }

        return {"triggered": False, "reason": "not_weekend"}

    async def _handle_anniversary(self, user_id: str, context: dict) -> dict:
        """处理纪念日临近"""
        match_id = context.get("match_id")
        days_until = context.get("days_until", 0)
        occasion = context.get("occasion", "anniversary")

        if days_until <= 7:
            result = await self.execute(
                match_id=match_id,
                context={"special_occasion": occasion}
            )

            return {
                "triggered": True,
                "should_push": True,
                "push_message": f"{occasion}快到了（{days_until}天后）！准备一个特别的约会吧~",
                "plans": result.get("plans", [])
            }

        return {"triggered": False, "reason": "too_early"}


# 全局 Skill 实例
_date_planning_skill_instance: Optional[DatePlanningAgentSkill] = None


def get_date_planning_skill() -> DatePlanningAgentSkill:
    """获取约会策划 Skill 单例实例"""
    global _date_planning_skill_instance
    if _date_planning_skill_instance is None:
        _date_planning_skill_instance = DatePlanningAgentSkill()
    return _date_planning_skill_instance
