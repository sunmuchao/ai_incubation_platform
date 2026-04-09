"""
Video Date Coach Skill - 视频约会教练

AI 约会教练核心 Skill - 视频约会管理、破冰建议、互动指导
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from agent.skills.base import BaseSkill
from utils.logger import logger


class VideoDateCoachSkill:
    """
    AI 视频约会教练 Skill - 视频约会全流程指导

    核心能力:
    - 约会管理：预约、取消、完成约会
    - 破冰建议：个性化破冰问题推荐
    - 互动指导：约会中的实时建议
    - 约会复盘：约会后的评分和反馈分析

    自主触发:
    - 约会前提醒和准备建议
    - 检测到约会即将开始
    - 约会后邀请复盘
    - 长期未约会用户的激活
    """

    name = "video_date_coach"
    version = "1.0.0"
    description = """
    AI 视频约会教练，视频约会全流程指导

    能力:
    - 约会管理：预约、取消、完成约会
    - 破冰建议：个性化破冰问题推荐
    - 互动指导：约会中的实时建议
    - 约会复盘：约会后的评分和反馈分析
    """

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "用户 ID"},
                "service_type": {
                    "type": "string",
                    "enum": ["date_management", "icebreaker_suggestion", "interaction_coaching", "date_review"],
                    "description": "服务类型"
                },
                "context": {
                    "type": "object",
                    "properties": {
                        "date_id": {"type": "string", "description": "约会 ID"},
                        "partner_id": {"type": "string", "description": "约会对象 ID"},
                        "scheduled_time": {"type": "string", "description": "预约时间"},
                        "date_stage": {"type": "string", "description": "约会阶段：pre_date, during_date, post_date"}
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
                "coach_result": {
                    "type": "object",
                    "properties": {
                        "service_type": {"type": "string"},
                        "dates": {"type": "array"},
                        "icebreakers": {"type": "array"},
                        "coaching_tips": {"type": "array"},
                        "review_summary": {"type": "object"},
                        "recommendations": {"type": "array"}
                    }
                },
                "generative_ui": {"type": "object"},
                "suggested_actions": {"type": "array"}
            },
            "required": ["success", "ai_message", "coach_result"]
        }

    async def execute(
        self,
        user_id: str,
        service_type: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> dict:
        logger.info(f"VideoDateCoachSkill: Executing for user={user_id}, type={service_type}")

        start_time = datetime.now()

        # 根据服务类型提供指导
        result = self._coach_video_date(service_type, user_id, context)

        ai_message = self._generate_message(result, service_type)
        generative_ui = self._build_ui(result, service_type)
        suggested_actions = self._generate_actions(service_type)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "success": True,
            "ai_message": ai_message,
            "coach_result": result,
            "generative_ui": generative_ui,
            "suggested_actions": suggested_actions,
            "skill_metadata": {
                "name": self.name,
                "version": self.version,
                "execution_time_ms": int(execution_time)
            }
        }

    def _coach_video_date(
        self,
        service_type: str,
        user_id: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """视频约会指导"""
        result = {
            "service_type": service_type,
            "dates": [],
            "icebreakers": [],
            "coaching_tips": [],
            "review_summary": {},
            "recommendations": []
        }

        if service_type == "date_management":
            result["dates"] = self._manage_dates(user_id, context)
            result["recommendations"] = self._generate_date_recommendations(result["dates"])

        elif service_type == "icebreaker_suggestion":
            result["icebreakers"] = self._generate_icebreakers(user_id, context)
            result["coaching_tips"] = self._generate_icebreaker_tips()

        elif service_type == "interaction_coaching":
            result["coaching_tips"] = self._generate_interaction_tips(user_id, context)
            result["recommendations"] = self._generate_interaction_recommendations()

        elif service_type == "date_review":
            result["review_summary"] = self._review_date(user_id, context)
            result["recommendations"] = self._generate_review_recommendations(result["review_summary"])

        return result

    def _manage_dates(self, user_id: str, context: Optional[Dict]) -> List[Dict]:
        """管理约会"""
        date_stage = (context or {}).get("date_stage", "upcoming")

        # 模拟约会数据
        return [
            {
                "date_id": "date-001",
                "partner": {
                    "id": "user-123",
                    "name": "小美",
                    "avatar": "https://example.com/avatar.jpg",
                    "age": 26,
                    "occupation": "设计师"
                },
                "status": "scheduled",
                "scheduled_time": "2026-04-10T19:00:00",
                "duration_minutes": 30,
                "theme": "初次见面",
                "background": "cafe",
                "preparation_tips": [
                    "提前 5 分钟进入房间测试设备",
                    "准备 2-3 个破冰话题",
                    "保持良好的光线和网络"
                ]
            },
            {
                "date_id": "date-002",
                "partner": {
                    "id": "user-456",
                    "name": "小丽",
                    "avatar": "https://example.com/avatar2.jpg",
                    "age": 24,
                    "occupation": "产品经理"
                },
                "status": "completed",
                "scheduled_time": "2026-04-05T20:00:00",
                "duration_minutes": 45,
                "theme": "深入了解",
                "background": "starry",
                "rating": 4,
                "review": "聊得很开心，有很多共同话题"
            },
            {
                "date_id": "date-003",
                "partner": {
                    "id": "user-789",
                    "name": "小雪",
                    "avatar": "https://example.com/avatar3.jpg",
                    "age": 25,
                    "occupation": "教师"
                },
                "status": "pending",
                "scheduled_time": None,
                "duration_minutes": 30,
                "theme": "轻松聊天",
                "background": "default",
                "next_step": "等待对方确认时间"
            }
        ]

    def _generate_icebreakers(self, user_id: str, context: Optional[Dict]) -> List[Dict]:
        """生成破冰问题"""
        date_id = (context or {}).get("date_id")
        partner_id = (context or {}).get("partner_id")

        # 基于场景的破冰问题
        return [
            {
                "category": "兴趣探索",
                "questions": [
                    {
                        "question": "你平时周末最喜欢做什么？",
                        "follow_up": "为什么喜欢这个活动？",
                        "tip": "从兴趣爱好入手是最安全的破冰方式"
                    },
                    {
                        "question": "最近有看什么好看的电影/剧吗？",
                        "follow_up": "能简单介绍一下剧情吗？",
                        "tip": "影视话题容易引起共鸣"
                    },
                    {
                        "question": "你去过最难忘的旅行地是哪里？",
                        "follow_up": "那里有什么特别的地方？",
                        "tip": "旅行话题可以了解对方的价值观"
                    }
                ]
            },
            {
                "category": "职业生活",
                "questions": [
                    {
                        "question": "你的工作日常是什么样的？",
                        "follow_up": "工作中最有成就感的部分是什么？",
                        "tip": "展现对对方职业的兴趣"
                    },
                    {
                        "question": "当初为什么选择这个行业？",
                        "follow_up": "有没有想过尝试其他行业？",
                        "tip": "了解对方的职业动机"
                    }
                ]
            },
            {
                "category": "深度交流",
                "questions": [
                    {
                        "question": "你觉得理想的生活状态是什么样的？",
                        "follow_up": "现在的生活离理想状态还有多远？",
                        "tip": "适合关系深入后使用"
                    },
                    {
                        "question": "你相信缘分吗？为什么？",
                        "follow_up": "你觉得我们相遇是缘分吗？",
                        "tip": "带一点暧昧的问题，慎用"
                    }
                ]
            },
            {
                "category": "互动游戏",
                "questions": [
                    {
                        "question": "我们来玩个游戏吧：每人说一个自己的小秘密",
                        "follow_up": "我先来，你愿意分享吗？",
                        "tip": "增加互动趣味性"
                    },
                    {
                        "question": "如果可以拥有一种超能力，你想要什么？",
                        "follow_up": "为什么选择这个超能力？",
                        "tip": "轻松有趣的话题"
                    }
                ]
            }
        ]

    def _generate_interaction_tips(self, user_id: str, context: Optional[Dict]) -> List[Dict]:
        """生成互动建议"""
        date_stage = (context or {}).get("date_stage", "during_date")

        return [
            {
                "stage": "开场",
                "tips": [
                    "保持微笑，语速适中",
                    "先聊一些轻松的话题热身",
                    "注意眼神交流（看摄像头而非屏幕）"
                ],
                "avoid": [
                    "不要一上来就问敏感问题（收入、房产等）",
                    "避免抱怨或负能量话题",
                    "不要频繁看手机"
                ]
            },
            {
                "stage": "深入交流",
                "tips": [
                    "多问开放性问题，鼓励对方分享",
                    "积极倾听，给予回应",
                    "寻找共同点，建立连接"
                ],
                "avoid": [
                    "不要打断对方说话",
                    "避免争论敏感话题（政治、宗教等）",
                    "不要过度吹嘘自己"
                ]
            },
            {
                "stage": "结束",
                "tips": [
                    "提前 5 分钟暗示即将结束",
                    "表达感谢和愉快的感受",
                    "如果感觉好，可以主动提出下次见面"
                ],
                "closing_lines": [
                    "今天聊得很开心，希望下次还能和你聊天",
                    "时间过得好快，期待下次见面",
                    "和你聊天很愉快，我们可以加微信继续聊吗？"
                ]
            }
        ]

    def _review_date(self, user_id: str, context: Optional[Dict]) -> Dict[str, Any]:
        """约会复盘"""
        date_id = (context or {}).get("date_id")

        return {
            "date_id": date_id or "date-001",
            "overall_rating": 4.2,
            "dimensions": {
                "conversation_quality": {
                    "score": 4.5,
                    "comment": "对话流畅，有很多共同话题"
                },
                "chemistry": {
                    "score": 4.0,
                    "comment": "有一定的化学反应，但还可以更深"
                },
                "authenticity": {
                    "score": 4.8,
                    "comment": "双方都很真诚"
                },
                "engagement": {
                    "score": 4.0,
                    "comment": "互动积极，但有时会有短暂沉默"
                }
            },
            "highlights": [
                "发现共同的旅行爱好",
                "对方对你的职业很感兴趣",
                "笑声很多，氛围轻松"
            ],
            "areas_for_improvement": [
                "可以更多表达自己的感受",
                "沉默时可以主动换话题",
                "结束时可以更明确表达继续发展的意愿"
            ],
            "compatibility_analysis": {
                "overall": 0.78,
                "interests_match": 0.85,
                "communication_style": 0.72,
                "values_alignment": 0.80,
                "recommendation": "建议继续接触，有很大发展潜力"
            },
            "next_steps": [
                "主动发消息表达愉快的心情",
                "可以开始规划线下见面",
                "保持联系但不要过于频繁"
            ]
        }

    def _generate_date_recommendations(self, dates: List[Dict]) -> List[Dict]:
        """生成约会建议"""
        recommendations = []

        upcoming = [d for d in dates if d.get("status") == "scheduled"]
        if upcoming:
            date = upcoming[0]
            recommendations.append({
                "type": "preparation",
                "priority": "high",
                "title": f"准备与{date['partner']['name']}的约会",
                "suggestion": f"约会将于{date['scheduled_time']}开始，请提前准备",
                "action": "prepare_date"
            })

        pending = [d for d in dates if d.get("status") == "pending"]
        if pending:
            recommendations.append({
                "type": "follow_up",
                "priority": "medium",
                "title": "跟进待确认的约会",
                "suggestion": f"有{len(pending)}个约会等待对方确认时间",
                "action": "follow_up_pending"
            })

        return recommendations

    def _generate_icebreaker_tips(self) -> List[Dict]:
        """生成破冰技巧"""
        return [
            {
                "tip": "真诚是最好的破冰工具",
                "description": "不要刻意迎合，做真实的自己更容易吸引到合适的人"
            },
            {
                "tip": "多问开放性问题",
                "description": "用'什么'、'为什么'、'怎么样'开头，鼓励对方分享更多"
            },
            {
                "tip": "积极倾听比会说更重要",
                "description": "给予回应、复述对方的话，让对方感受到被理解"
            },
            {
                "tip": "适当的幽默可以活跃气氛",
                "description": "但不要过度，避免敏感话题的玩笑"
            }
        ]

    def _generate_interaction_recommendations(self) -> List[Dict]:
        """生成互动建议"""
        return [
            {
                "type": "engagement",
                "priority": "medium",
                "title": "增加互动深度",
                "suggestion": "尝试分享一些个人故事，鼓励对方也这样做",
                "action": "deepen_connection"
            },
            {
                "type": "body_language",
                "priority": "low",
                "title": "注意肢体语言",
                "suggestion": "保持微笑，适当点头，展现你的专注和兴趣",
                "action": "improve_body_language"
            }
        ]

    def _generate_review_recommendations(self, review: Dict) -> List[Dict]:
        """生成复盘建议"""
        recommendations = []

        overall = review.get("overall_rating", 0)
        if overall >= 4.0:
            recommendations.append({
                "type": "encouragement",
                "priority": "medium",
                "title": "约会表现优秀",
                "suggestion": "继续保持真诚和开放的态度，你们很有发展潜力",
                "action": "continue_engaging"
            })
        elif overall >= 3.0:
            recommendations.append({
                "type": "improvement",
                "priority": "medium",
                "title": "有提升空间",
                "suggestion": "参考改进建议，下次约会可以做得更好",
                "action": "improve_skills"
            })
        else:
            recommendations.append({
                "type": "guidance",
                "priority": "high",
                "title": "需要调整策略",
                "suggestion": "可能需要重新审视自己的约会方式和期望",
                "action": "rethink_approach"
            })

        # 基于下一步建议
        for next_step in review.get("next_steps", [])[:2]:
            recommendations.append({
                "type": "next_action",
                "priority": "medium",
                "title": "下一步行动",
                "suggestion": next_step,
                "action": "take_next_step"
            })

        return recommendations

    def _generate_message(self, result: Dict, service_type: str) -> str:
        """生成自然语言解读"""
        if service_type == "date_management":
            dates = result.get("dates", [])
            scheduled = sum(1 for d in dates if d.get("status") == "scheduled")
            completed = sum(1 for d in dates if d.get("status") == "completed")

            message = "📅 视频约会管理\n\n"
            message += f"已安排：{scheduled} 个 | 已完成：{completed} 个\n\n"

            for date in dates[:3]:
                status_icon = {"scheduled": "🔵", "completed": "✅", "pending": "⏳"}.get(date.get("status"), "⚪")
                partner = date.get("partner", {})
                message += f"{status_icon} {partner.get('name', '未知')} - {date.get('theme', '约会')}\n"
                if date.get("scheduled_time"):
                    message += f"  时间：{date['scheduled_time'][:16].replace('T', ' ')}\n"
                if date.get("next_step"):
                    message += f"  状态：{date['next_step']}\n"

            return message

        elif service_type == "icebreaker_suggestion":
            icebreakers = result.get("icebreakers", [])
            message = "💬 破冰话题建议\n\n"

            for category in icebreakers[:3]:
                message += f"【{category.get('category', '话题')}】\n"
                for q in category.get('questions', [])[:2]:
                    message += f"• {q.get('question', '')}\n"
                message += "\n"

            tips = result.get("coaching_tips", [])
            if tips:
                message += "💡 技巧提示：\n"
                for tip in tips[:2]:
                    message += f"- {tip.get('tip', '')}\n"

            return message

        elif service_type == "interaction_coaching":
            tips = result.get("coaching_tips", [])
            message = "🎯 互动指导\n\n"

            for stage_tip in tips[:3]:
                message += f"【{stage_tip.get('stage', '阶段')}】\n"
                message += "建议：\n"
                for tip in stage_tip.get('tips', [])[:2]:
                    message += f"✓ {tip}\n"
                message += "避免：\n"
                for avoid in stage_tip.get('avoid', [])[:2]:
                    message += f"✗ {avoid}\n"
                message += "\n"

            return message

        elif service_type == "date_review":
            review = result.get("review_summary", {})
            message = f"📊 约会复盘报告\n\n"
            message += f"综合评分：{review.get('overall_rating', 0)}/5.0\n\n"

            message += "维度评分：\n"
            for dim_name, dim_data in review.get("dimensions", {}).items():
                message += f"• {dim_name}: {dim_data.get('score', 0)}/5.0\n"

            message += "\n亮点：\n"
            for highlight in review.get("highlights", [])[:3]:
                message += f"✓ {highlight}\n"

            message += "\n改进建议：\n"
            for area in review.get("areas_for_improvement", [])[:3]:
                message += f"○ {area}\n"

            return message

        return "视频约会指导已完成"

    def _build_ui(self, result: Dict, service_type: str) -> Dict[str, Any]:
        """构建 UI"""
        return {
            "component_type": "video_date_coach_dashboard",
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

        if service_type == "date_management":
            actions.append({"label": "预约新约会", "action_type": "schedule_date", "params": {}})
        elif service_type == "icebreaker_suggestion":
            actions.append({"label": "复制破冰话题", "action_type": "copy_topics", "params": {}})
        elif service_type == "date_review":
            actions.append({"label": "发送跟进消息", "action_type": "send_followup", "params": {}})

        return actions

    async def autonomous_trigger(
        self,
        user_id: str,
        trigger_type: str,
        context: Optional[Dict] = None
    ) -> dict:
        """自主触发"""
        logger.info(f"VideoDateCoachSkill: Autonomous trigger for user={user_id}, type={trigger_type}")

        if trigger_type == "pre_date_reminder":
            result = await self.execute(
                user_id=user_id,
                service_type="date_management",
                context={"date_stage": "upcoming"}
            )
            has_scheduled = any(d.get("status") == "scheduled" for d in result.get("dates", []))
            if has_scheduled:
                return {"triggered": True, "result": result, "should_push": True}
            return {"triggered": False, "reason": "no_scheduled_dates"}

        elif trigger_type == "icebreaker_needed":
            result = await self.execute(
                user_id=user_id,
                service_type="icebreaker_suggestion",
                context=context
            )
            return {"triggered": True, "result": result, "should_push": True}

        elif trigger_type == "post_date_review":
            result = await self.execute(
                user_id=user_id,
                service_type="date_review",
                context=context
            )
            return {"triggered": True, "result": result, "should_push": True}

        return {"triggered": False, "reason": "not_needed"}


# 全局 Skill 实例
_video_date_coach_skill_instance: Optional[VideoDateCoachSkill] = None


def get_video_date_coach_skill() -> VideoDateCoachSkill:
    """获取视频约会教练 Skill 单例实例"""
    global _video_date_coach_skill_instance
    if _video_date_coach_skill_instance is None:
        _video_date_coach_skill_instance = VideoDateCoachSkill()
    return _video_date_coach_skill_instance
