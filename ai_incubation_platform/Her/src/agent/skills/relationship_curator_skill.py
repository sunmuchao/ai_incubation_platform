"""
关系策展 Skill - 情感纪念册策划师

AI 关系策展人核心 Skill - 回忆整理、纪念册生成、里程碑追踪
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from agent.skills.base import BaseSkill
from utils.logger import logger


class RelationshipCuratorSkill:
    """
    AI 关系策展人 Skill - 为你们的关系策划美好纪念

    核心能力:
    - 回忆整理：自动整理聊天记录、合照、约会记录
    - 纪念册生成：创建主题情感纪念册
    - 里程碑追踪：记录关系重要时刻
    -  Anniversary 提醒：重要日子提前提醒

    自主触发:
    - 满月/百日/周年纪念日前提醒
    - 检测到美好回忆时刻
    - 定期生成关系月报
    """

    name = "relationship_curator"
    version = "1.0.0"
    description = """
    AI 关系策展人，为你们的关系策划美好纪念

    能力:
    - 回忆整理：自动整理聊天记录、合照、约会记录
    - 纪念册生成：创建主题情感纪念册
    - 里程碑追踪：记录关系重要时刻
    - Anniversary 提醒：重要日子提前提醒
    """

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_a_id": {"type": "string", "description": "用户 A ID"},
                "user_b_id": {"type": "string", "description": "用户 B ID"},
                "service_type": {
                    "type": "string",
                    "enum": ["memory_collection", "album_creation", "milestone_tracking", "anniversary_reminder"],
                    "description": "服务类型"
                },
                "context": {
                    "type": "object",
                    "properties": {
                        "relationship_start_date": {"type": "string"},
                        "album_theme": {"type": "string"},
                        "period_days": {"type": "number"}
                    }
                }
            },
            "required": ["user_a_id", "user_b_id", "service_type"]
        }

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "ai_message": {"type": "string"},
                "curator_result": {
                    "type": "object",
                    "properties": {
                        "service_type": {"type": "string"},
                        "memories": {"type": "array"},
                        "milestones": {"type": "array"},
                        "album_suggestions": {"type": "array"},
                        "upcoming_dates": {"type": "array"}
                    }
                },
                "generative_ui": {"type": "object"},
                "suggested_actions": {"type": "array"}
            },
            "required": ["success", "ai_message", "curator_result"]
        }

    async def execute(
        self,
        user_a_id: str,
        user_b_id: str,
        service_type: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> dict:
        logger.info(f"RelationshipCuratorSkill: Executing for users={user_a_id},{user_b_id}, type={service_type}")

        start_time = datetime.now()

        result = await self._curate_relationship(service_type, user_a_id, user_b_id, context)

        ai_message = self._generate_message(result, service_type)
        generative_ui = self._build_ui(result, service_type)
        suggested_actions = self._generate_actions(service_type)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "success": True,
            "ai_message": ai_message,
            "curator_result": result,
            "generative_ui": generative_ui,
            "suggested_actions": suggested_actions,
            "skill_metadata": {
                "name": self.name,
                "version": self.version,
                "execution_time_ms": int(execution_time)
            }
        }

    async def _curate_relationship(
        self,
        service_type: str,
        user_a_id: str,
        user_b_id: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """策划关系内容"""
        result = {
            "service_type": service_type,
            "memories": [],
            "milestones": [],
            "album_suggestions": [],
            "upcoming_dates": []
        }

        if service_type == "memory_collection":
            result["memories"] = self._collect_memories(user_a_id, user_b_id, context)

        elif service_type == "album_creation":
            result["album_suggestions"] = self._suggest_albums(user_a_id, user_b_id, context)

        elif service_type == "milestone_tracking":
            result["milestones"] = self._track_milestones(user_a_id, user_b_id, context)

        elif service_type == "anniversary_reminder":
            result["upcoming_dates"] = self._get_upcoming_dates(context)

        return result

    def _collect_memories(
        self,
        user_a_id: str,
        user_b_id: str,
        context: Optional[Dict]
    ) -> List[Dict]:
        """收集回忆"""
        # 简化实现
        return [
            {
                "type": "first_date",
                "title": "初次约会",
                "date": "2026-01-15",
                "description": "在那家咖啡馆的初次见面"
            },
            {
                "type": "confession",
                "title": "表白日",
                "date": "2026-02-14",
                "description": "情人节的勇敢表白"
            },
            {
                "type": "trip",
                "title": "第一次旅行",
                "date": "2026-03-20",
                "description": "周末的短途旅行"
            }
        ]

    def _suggest_albums(
        self,
        user_a_id: str,
        user_b_id: str,
        context: Optional[Dict]
    ) -> List[Dict]:
        """建议纪念册"""
        return [
            {
                "theme": "我们的第一次",
                "description": "记录所有的第一次体验",
                "suggested_content": ["第一次约会", "第一次牵手", "第一次旅行"]
            },
            {
                "theme": "月度精选",
                "description": "每个月的美好瞬间",
                "suggested_content": ["合照", "聊天记录", "约会票根"]
            },
            {
                "theme": "情书集",
                "description": "收集彼此写的信",
                "suggested_content": ["手写情书", "微信长消息", "卡片"]
            }
        ]

    def _track_milestones(
        self,
        user_a_id: str,
        user_b_id: str,
        context: Optional[Dict]
    ) -> List[Dict]:
        """追踪里程碑"""
        if context and context.get("relationship_start_date"):
            start_date = datetime.fromisoformat(context["relationship_start_date"].replace('Z', '+00:00'))
            days_together = (datetime.now() - start_date.replace(tzinfo=None)).days

            return [
                {"name": "在一起", "date": context["relationship_start_date"], "completed": True},
                {"name": "100 天纪念", "date": self._date_after_days(start_date, 100), "completed": days_together >= 100},
                {"name": "半年纪念", "date": self._date_after_days(start_date, 180), "completed": days_together >= 180},
                {"name": "一周年纪念", "date": self._date_after_days(start_date, 365), "completed": days_together >= 365}
            ]

        return []

    def _get_upcoming_dates(self, context: Optional[Dict]) -> List[Dict]:
        """获取即将到来的重要日期"""
        if not context or not context.get("relationship_start_date"):
            return []

        start_date = datetime.fromisoformat(context["relationship_start_date"].replace('Z', '+00:00'))
        days_together = (datetime.now() - start_date.replace(tzinfo=None)).days

        upcoming = []

        # 计算下一个里程碑
        next_milestones = [100, 180, 365, 500]
        for milestone in next_milestones:
            if days_together < milestone:
                days_left = milestone - days_together
                upcoming.append({
                    "name": f"{milestone}天纪念",
                    "date": self._date_after_days(start_date, milestone),
                    "days_left": days_left
                })
                break

        # 月纪念
        months_together = days_together // 30
        next_month = months_together + 1
        next_month_date = start_date + timedelta(days=next_month * 30)
        upcoming.append({
            "name": f"{next_month}个月纪念",
            "date": next_month_date.isoformat(),
            "days_left": (next_month_date - datetime.now()).days
        })

        return upcoming

    def _date_after_days(self, start_date: datetime, days: int) -> str:
        """计算多少天后的日期"""
        result = start_date + timedelta(days=days)
        return result.strftime("%Y-%m-%d")

    def _generate_message(self, result: Dict, service_type: str) -> str:
        """生成自然语言解读"""
        if service_type == "memory_collection":
            memories = result.get("memories", [])
            message = f"💕 回忆收集\n\n"
            message += f"已收集 {len(memories)} 个美好回忆：\n"
            for memory in memories[:5]:
                message += f"- {memory.get('title', '回忆')} ({memory.get('date', '')})\n"
            return message

        elif service_type == "album_creation":
            albums = result.get("album_suggestions", [])
            message = f"📔 纪念册建议\n\n"
            for album in albums:
                message += f"【{album.get('theme', '主题')}】\n"
                message += f"{album.get('description', '')}\n\n"
            return message

        elif service_type == "milestone_tracking":
            milestones = result.get("milestones", [])
            message = f"🎯 关系里程碑\n\n"
            for milestone in milestones:
                status = "✓" if milestone.get("completed") else "○"
                message += f"{status} {milestone.get('name', '')}: {milestone.get('date', '')}\n"
            return message

        elif service_type == "anniversary_reminder":
            dates = result.get("upcoming_dates", [])
            message = f"⏰ 重要日期提醒\n\n"
            for date_info in dates:
                message += f"{date_info.get('name', '')}: 还有{date_info.get('days_left', 0)}天\n"
            return message

        return "关系策展服务已就绪"

    def _build_ui(self, result: Dict, service_type: str) -> Dict[str, Any]:
        """构建 UI"""
        return {
            "component_type": "relationship_curator",
            "props": {
                "service_type": service_type,
                "data": result
            }
        }

    def _generate_actions(self, service_type: str) -> List[Dict[str, Any]]:
        """生成建议操作"""
        return [
            {"label": "创建纪念册", "action_type": "create_album", "params": {}},
            {"label": "分享回忆", "action_type": "share_memory", "params": {}}
        ]

    async def autonomous_trigger(
        self,
        user_a_id: str,
        user_b_id: str,
        trigger_type: str,
        context: Optional[Dict] = None
    ) -> dict:
        """自主触发"""
        logger.info(f"RelationshipCuratorSkill: Autonomous trigger for users={user_a_id},{user_b_id}, type={trigger_type}")

        if trigger_type == "anniversary_reminder":
            result = await self.execute(
                user_a_id=user_a_id,
                user_b_id=user_b_id,
                service_type="anniversary_reminder",
                context=context
            )
            return {"triggered": True, "result": result, "should_push": True}

        elif trigger_type == "monthly_report":
            result = await self.execute(
                user_a_id=user_a_id,
                user_b_id=user_b_id,
                service_type="memory_collection",
                context=context
            )
            return {"triggered": True, "result": result, "should_push": False}

        return {"triggered": False, "reason": "not_needed"}


# 全局 Skill 实例
_relationship_curator_skill_instance: Optional[RelationshipCuratorSkill] = None


def get_relationship_curator_skill() -> RelationshipCuratorSkill:
    """获取关系策展 Skill 单例实例"""
    global _relationship_curator_skill_instance
    if _relationship_curator_skill_instance is None:
        _relationship_curator_skill_instance = RelationshipCuratorSkill()
    return _relationship_curator_skill_instance
