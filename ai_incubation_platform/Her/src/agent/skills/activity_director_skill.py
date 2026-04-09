"""
Activity Director Skill - 活动策展导演

AI 活动导演核心 Skill - 地点推荐、活动策划、场景营造
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from agent.skills.base import BaseSkill
from utils.logger import logger


class ActivityDirectorSkill:
    """
    AI 活动导演 Skill - 活动策划与场景营造专家

    核心能力:
    - 智能地点推荐：基于位置、偏好、场合推荐约会地点
    - 活动策划：设计完整的约会流程和活动安排
    - 场景营造：提供氛围营造建议
    - 收藏管理：管理用户收藏的地点和活动

    自主触发:
    - 检测到用户有约会计划
    - 周末/节假日前的活动推荐
    - 特殊日期（纪念日等）的活动策划
    - 基于位置的附近地点推荐
    """

    name = "activity_director"
    version = "1.0.0"
    description = """
    AI 活动导演，活动策划与场景营造专家

    能力:
    - 智能地点推荐：基于位置、偏好、场合推荐约会地点
    - 活动策划：设计完整的约会流程和活动安排
    - 场景营造：提供氛围营造建议
    - 收藏管理：管理用户收藏的地点和活动
    """

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "用户 ID"},
                "service_type": {
                    "type": "string",
                    "enum": ["location_recommendation", "activity_planning", "scene_creation", "saved_locations"],
                    "description": "服务类型"
                },
                "context": {
                    "type": "object",
                    "properties": {
                        "occasion": {"type": "string", "description": "场合类型"},
                        "location_type": {"type": "string", "description": "地点类型"},
                        "target_user_id": {"type": "string", "description": "约会对象 ID"},
                        "budget_range": {"type": "string", "description": "预算范围"},
                        "time_slot": {"type": "string", "description": "时间段"}
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
                "director_result": {
                    "type": "object",
                    "properties": {
                        "service_type": {"type": "string"},
                        "recommendations": {"type": "array"},
                        "activity_plan": {"type": "object"},
                        "scene_suggestions": {"type": "array"},
                        "saved_locations": {"type": "array"}
                    }
                },
                "generative_ui": {"type": "object"},
                "suggested_actions": {"type": "array"}
            },
            "required": ["success", "ai_message", "director_result"]
        }

    async def execute(
        self,
        user_id: str,
        service_type: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> dict:
        logger.info(f"ActivityDirectorSkill: Executing for user={user_id}, type={service_type}")

        start_time = datetime.now()

        # 根据服务类型提供推荐
        result = self._curate_activities(service_type, user_id, context)

        ai_message = self._generate_message(result, service_type)
        generative_ui = self._build_ui(result, service_type)
        suggested_actions = self._generate_actions(service_type)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "success": True,
            "ai_message": ai_message,
            "director_result": result,
            "generative_ui": generative_ui,
            "suggested_actions": suggested_actions,
            "skill_metadata": {
                "name": self.name,
                "version": self.version,
                "execution_time_ms": int(execution_time)
            }
        }

    def _curate_activities(
        self,
        service_type: str,
        user_id: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """策划活动"""
        result = {
            "service_type": service_type,
            "recommendations": [],
            "activity_plan": {},
            "scene_suggestions": [],
            "saved_locations": []
        }

        if service_type == "location_recommendation":
            result["recommendations"] = self._recommend_locations(user_id, context)
            result["scene_suggestions"] = self._generate_scene_tips(result["recommendations"])

        elif service_type == "activity_planning":
            result["activity_plan"] = self._plan_activity(user_id, context)
            result["recommendations"] = self._get_plan_locations(result["activity_plan"])

        elif service_type == "scene_creation":
            result["scene_suggestions"] = self._create_scene(user_id, context)
            result["recommendations"] = self._get_scene_items(result["scene_suggestions"])

        elif service_type == "saved_locations":
            result["saved_locations"] = self._get_user_saved_locations(user_id, context)

        return result

    def _recommend_locations(self, user_id: str, context: Optional[Dict]) -> List[Dict]:
        """推荐地点"""
        occasion = (context or {}).get("occasion", "casual")
        location_type = (context or {}).get("location_type")
        budget = (context or {}).get("budget_range", "medium")

        # 基于场合的推荐模板
        occasion_recommendations = {
            "first_date": [
                {
                    "name": "静语咖啡馆",
                    "type": "cafe",
                    "reason": "安静舒适，适合初次交流",
                    "atmosphere": "温馨、私密",
                    "budget": "¥50-100",
                    "best_time": "下午 2-5 点",
                    "suitability": 0.95,
                    "features": ["安静", "有包间", "wifi"]
                },
                {
                    "name": "城市艺术空间",
                    "type": "gallery",
                    "reason": "艺术展览提供丰富话题",
                    "atmosphere": "文艺、轻松",
                    "budget": "¥80-150",
                    "best_time": "周末下午",
                    "suitability": 0.85,
                    "features": ["展览", "咖啡", "文创"]
                }
            ],
            "weekend": [
                {
                    "name": "阳光公园",
                    "type": "park",
                    "reason": "自然环境放松身心",
                    "atmosphere": "自然、惬意",
                    "budget": "免费",
                    "best_time": "上午 10 点 - 下午 4 点",
                    "suitability": 0.88,
                    "features": ["散步", "野餐", "拍照"]
                },
                {
                    "name": "创意市集",
                    "type": "market",
                    "reason": "一起探索有趣的小物",
                    "atmosphere": "热闹、有趣",
                    "budget": "¥100-200",
                    "best_time": "周末全天",
                    "suitability": 0.82,
                    "features": ["购物", "美食", "手工"]
                }
            ],
            "anniversary": [
                {
                    "name": "云端餐厅",
                    "type": "fine_dining",
                    "reason": "高空景观，浪漫氛围",
                    "atmosphere": "浪漫、高级",
                    "budget": "¥500+",
                    "best_time": "晚上 7-9 点",
                    "suitability": 0.98,
                    "features": ["景观", "法式料理", "红酒"]
                },
                {
                    "name": "星空观景台",
                    "type": "viewpoint",
                    "reason": "一起看星星的浪漫时刻",
                    "atmosphere": "浪漫、私密",
                    "budget": "¥100-200",
                    "best_time": "晚上 8 点后",
                    "suitability": 0.92,
                    "features": ["夜景", "安静", "拍照"]
                }
            ],
            "casual": [
                {
                    "name": "街角书店",
                    "type": "bookstore",
                    "reason": "文艺青年的约会圣地",
                    "atmosphere": "文艺、安静",
                    "budget": "¥50-100",
                    "best_time": "下午",
                    "suitability": 0.85,
                    "features": ["阅读", "咖啡", "交流"]
                },
                {
                    "name": "美食广场",
                    "type": "food_court",
                    "reason": "多种选择，满足各口味",
                    "atmosphere": "热闹、随意",
                    "budget": "¥100-150",
                    "best_time": "午餐/晚餐",
                    "suitability": 0.80,
                    "features": ["美食", "选择多", "实惠"]
                }
            ]
        }

        recommendations = occasion_recommendations.get(occasion, occasion_recommendations["casual"])

        # 如果有特定地点类型，进行过滤
        if location_type:
            recommendations = [r for r in recommendations if r["type"] == location_type]

        return recommendations

    def _plan_activity(self, user_id: str, context: Optional[Dict]) -> Dict[str, Any]:
        """策划活动"""
        occasion = (context or {}).get("occasion", "first_date")
        time_slot = (context or {}).get("time_slot", "afternoon")
        budget = (context or {}).get("budget_range", "medium")

        # 完整的活动策划
        plans = {
            "first_date": {
                "title": "初次约会完美计划",
                "duration": "3-4 小时",
                "budget_range": "¥200-400",
                "timeline": [
                    {
                        "time": "14:00",
                        "activity": "咖啡馆见面",
                        "location_type": "cafe",
                        "description": "在安静的咖啡馆初次交流，点一杯咖啡放松聊天",
                        "tips": "提前 5 分钟到达，选择靠窗或角落位置"
                    },
                    {
                        "time": "15:30",
                        "activity": "艺术展览漫步",
                        "location_type": "gallery",
                        "description": "一起欣赏艺术作品，寻找共同话题",
                        "tips": "不要过于专业，以感受和分享为主"
                    },
                    {
                        "time": "17:30",
                        "activity": "晚餐时光",
                        "location_type": "restaurant",
                        "description": "选择一家有特色的餐厅共进晚餐",
                        "tips": "提前预订，避免排队等待"
                    }
                ],
                "backup_plan": "如遇下雨，可改为室内商场或博物馆",
                "conversation_starters": [
                    "最近有看什么好看的电影吗？",
                    "平时周末喜欢做什么？",
                    "有没有特别想去的地方？"
                ]
            },
            "weekend": {
                "title": "周末休闲计划",
                "duration": "5-6 小时",
                "budget_range": "¥300-500",
                "timeline": [
                    {
                        "time": "10:00",
                        "activity": "早午餐",
                        "location_type": "brunch",
                        "description": "享受悠闲的早午餐时光",
                        "tips": "选择评价好的网红店"
                    },
                    {
                        "time": "12:00",
                        "activity": "公园散步/骑行",
                        "location_type": "park",
                        "description": "在大自然中放松身心",
                        "tips": "准备防晒和饮用水"
                    },
                    {
                        "time": "15:00",
                        "activity": "下午茶",
                        "location_type": "cafe",
                        "description": "休息聊天，分享下午的感受",
                        "tips": "找一家有特色的甜品店"
                    },
                    {
                        "time": "17:00",
                        "activity": "创意市集/购物",
                        "location_type": "market",
                        "description": "一起探索有趣的小店",
                        "tips": "可以互相为对方挑选小礼物"
                    }
                ],
                "backup_plan": "天气不佳可改为室内活动如电影院、密室逃脱",
                "conversation_starters": [
                    "这周工作怎么样？",
                    "有什么有趣的事情想分享吗？"
                ]
            },
            "anniversary": {
                "title": "纪念日浪漫计划",
                "duration": "4-5 小时",
                "budget_range": "¥800-1500",
                "timeline": [
                    {
                        "time": "17:00",
                        "activity": "日落观景",
                        "location_type": "viewpoint",
                        "description": "一起看日落，营造浪漫氛围",
                        "tips": "提前查好日落时间，准备小惊喜"
                    },
                    {
                        "time": "18:30",
                        "activity": "精致晚餐",
                        "location_type": "fine_dining",
                        "description": "在高级餐厅享用纪念日晚餐",
                        "tips": "提前告知餐厅是纪念日，可能会有惊喜"
                    },
                    {
                        "time": "20:30",
                        "activity": "夜景漫步/酒吧小酌",
                        "location_type": "bar",
                        "description": "饭后散步或找家安静的酒吧",
                        "tips": "点一杯鸡尾酒，回顾美好时光"
                    }
                ],
                "backup_plan": "预订前确认营业时间和位置",
                "special_suggestions": [
                    "准备一份小礼物或手写卡片",
                    "收集这一年的照片做成小相册",
                    "提前和餐厅沟通准备惊喜"
                ]
            }
        }

        return plans.get(occasion, plans["first_date"])

    def _create_scene(self, user_id: str, context: Optional[Dict]) -> List[Dict]:
        """创建场景建议"""
        occasion = (context or {}).get("occasion", "romantic_dinner")

        scene_suggestions = {
            "romantic_dinner": [
                {
                    "element": "灯光",
                    "suggestion": "选择暖色调灯光，营造温馨氛围",
                    "importance": "high"
                },
                {
                    "element": "音乐",
                    "suggestion": "轻柔的爵士乐或钢琴曲作为背景",
                    "importance": "medium"
                },
                {
                    "element": "着装",
                    "suggestion": "Smart Casual 或正装，展现重视",
                    "importance": "high"
                },
                {
                    "element": "话题",
                    "suggestion": "准备一些深度话题，避免敏感话题",
                    "importance": "high"
                }
            ],
            "casual_chat": [
                {
                    "element": "环境",
                    "suggestion": "选择安静但不冷清的地方",
                    "importance": "high"
                },
                {
                    "element": "座位",
                    "suggestion": "选择面对面或 L 型座位，方便交流",
                    "importance": "medium"
                },
                {
                    "element": "话题准备",
                    "suggestion": "准备 3-5 个开放性问题",
                    "importance": "medium"
                }
            ],
            "first_meeting": [
                {
                    "element": "地点选择",
                    "suggestion": "公共场所，交通便利，方便双方到达",
                    "importance": "high"
                },
                {
                    "element": "时间控制",
                    "suggestion": "首次见面建议 1-2 小时，留有余地",
                    "importance": "medium"
                },
                {
                    "element": "破冰准备",
                    "suggestion": "准备自我介绍和几个轻松话题",
                    "importance": "high"
                }
            ]
        }

        return scene_suggestions.get(occasion, scene_suggestions["casual_chat"])

    def _get_user_saved_locations(self, user_id: str, context: Optional[Dict]) -> List[Dict]:
        """获取用户收藏的地点"""
        # 模拟用户收藏的地点
        return [
            {
                "id": "loc-001",
                "name": "那家咖啡馆",
                "type": "cafe",
                "address": "某某路 123 号",
                "reason": "第一次约会的地方，很有纪念意义",
                "rating": 4.8,
                "tags": ["咖啡", "安静", "适合聊天"]
            },
            {
                "id": "loc-002",
                "name": "星空餐厅",
                "type": "fine_dining",
                "address": "中心大厦 38 层",
                "reason": "纪念日想去的地方",
                "rating": 4.9,
                "tags": ["浪漫", "景观", "法餐"]
            },
            {
                "id": "loc-003",
                "name": "城市公园",
                "type": "park",
                "address": "市中心",
                "reason": "周末散步的好地方",
                "rating": 4.5,
                "tags": ["自然", "免费", "拍照"]
            }
        ]

    def _generate_scene_tips(self, recommendations: List[Dict]) -> List[Dict]:
        """生成场景营造建议"""
        tips = []
        for rec in recommendations[:2]:
            tips.append({
                "location": rec.get("name"),
                "atmosphere_tip": rec.get("atmosphere", ""),
                "best_time": rec.get("best_time", ""),
                "conversation_tip": "准备一些开放性问题，多倾听对方"
            })
        return tips

    def _get_plan_locations(self, activity_plan: Dict) -> List[Dict]:
        """获取活动策划中的地点"""
        locations = []
        timeline = activity_plan.get("timeline", [])
        for item in timeline:
            locations.append({
                "time": item.get("time"),
                "activity": item.get("activity"),
                "location_type": item.get("location_type"),
                "tips": item.get("tips")
            })
        return locations

    def _get_scene_items(self, scene_suggestions: List[Dict]) -> List[Dict]:
        """获取场景元素"""
        return [{"element": s.get("element"), "suggestion": s.get("suggestion")} for s in scene_suggestions]

    def _generate_message(self, result: Dict, service_type: str) -> str:
        """生成自然语言解读"""
        if service_type == "location_recommendation":
            recs = result.get("recommendations", [])
            message = "📍 活动地点推荐\n\n"
            for rec in recs[:3]:
                message += f"【{rec.get('name', '未知')}】\n"
                message += f"{rec.get('reason', '')}\n"
                message += f"氛围：{rec.get('atmosphere', '')} | 预算：{rec.get('budget', '')}\n"
                message += f"最佳时间：{rec.get('best_time', '')}\n\n"
            return message

        elif service_type == "activity_planning":
            plan = result.get("activity_plan", {})
            message = f"📋 {plan.get('title', '活动计划')}\n\n"
            message += f"时长：{plan.get('duration', '')} | 预算：{plan.get('budget_range', '')}\n\n"

            timeline = plan.get("timeline", [])
            for item in timeline[:3]:
                message += f"{item.get('time')} {item.get('activity')}\n"
                message += f"  {item.get('description', '')}\n"
                message += f"  💡 {item.get('tips', '')}\n\n"

            if plan.get("backup_plan"):
                message += f"备选方案：{plan['backup_plan']}\n"

            return message

        elif service_type == "scene_creation":
            scenes = result.get("scene_suggestions", [])
            message = "✨ 场景营造建议\n\n"
            for scene in scenes[:4]:
                message += f"• {scene.get('element')}: {scene.get('suggestion', '')}\n"
            return message

        elif service_type == "saved_locations":
            locations = result.get("saved_locations", [])
            message = f"⭐ 收藏的地点 ({len(locations)}个)\n\n"
            for loc in locations[:5]:
                message += f"📍 {loc.get('name', '未知')} ({loc.get('type', '')})\n"
                message += f"   {loc.get('reason', '')}\n"
                message += f"   评分：{'★' * int(loc.get('rating', 0)//2)}\n\n"
            return message

        return "活动策划已完成"

    def _build_ui(self, result: Dict, service_type: str) -> Dict[str, Any]:
        """构建 UI"""
        return {
            "component_type": "activity_director_dashboard",
            "props": {
                "service_type": service_type,
                "data": result
            }
        }

    def _generate_actions(self, service_type: str) -> List[Dict[str, Any]]:
        """生成建议操作"""
        actions = [
            {"label": "查看详细推荐", "action_type": "view_details", "params": {}},
            {"label": "保存到收藏", "action_type": "save_to_favorites", "params": {}}
        ]

        if service_type == "location_recommendation":
            actions.append({"label": "导航到地点", "action_type": "navigate", "params": {}})
        elif service_type == "activity_planning":
            actions.append({"label": "分享计划", "action_type": "share_plan", "params": {}})
        elif service_type == "saved_locations":
            actions.append({"label": "管理收藏", "action_type": "manage_saved", "params": {}})

        return actions

    async def autonomous_trigger(
        self,
        user_id: str,
        trigger_type: str,
        context: Optional[Dict] = None
    ) -> dict:
        """自主触发"""
        logger.info(f"ActivityDirectorSkill: Autonomous trigger for user={user_id}, type={trigger_type}")

        if trigger_type == "weekend_recommendation":
            result = await self.execute(
                user_id=user_id,
                service_type="location_recommendation",
                context={"occasion": "weekend"}
            )
            return {"triggered": True, "result": result, "should_push": True}

        elif trigger_type == "special_date_reminder":
            result = await self.execute(
                user_id=user_id,
                service_type="activity_planning",
                context={"occasion": "anniversary"}
            )
            return {"triggered": True, "result": result, "should_push": True}

        elif trigger_type == "first_date_detected":
            result = await self.execute(
                user_id=user_id,
                service_type="activity_planning",
                context={"occasion": "first_date"}
            )
            return {"triggered": True, "result": result, "should_push": True}

        return {"triggered": False, "reason": "not_needed"}


# 全局 Skill 实例
_activity_director_skill_instance: Optional[ActivityDirectorSkill] = None


def get_activity_director_skill() -> ActivityDirectorSkill:
    """获取活动导演 Skill 单例实例"""
    global _activity_director_skill_instance
    if _activity_director_skill_instance is None:
        _activity_director_skill_instance = ActivityDirectorSkill()
    return _activity_director_skill_instance
