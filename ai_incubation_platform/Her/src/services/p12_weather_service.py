"""
P12 行为实验室 - 关系气象报告服务

关系气象报告服务 - 情感温度计算、天气描述、行动建议
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
from db.database import SessionLocal
from db.models import ConversationDB, ChatMessageDB
from models.p12_models import RelationshipWeatherReportDB, EmotionWarningDB
from utils.logger import logger
from utils.db_session_manager import db_session, db_session_readonly, optional_db_session


class RelationshipWeatherService:
    """关系气象报告服务"""

    # 天气描述映射 - 使用温度范围元组 (min, max)
    WEATHER_DESCRIPTIONS = [
        (80, 100, "sunny"),  # 晴朗
        (60, 80, "partly_cloudy"),  # 多云
        (40, 60, "cloudy"),  # 阴天
        (20, 40, "rainy"),  # 雨天
        (0, 20, "stormy"),  # 暴风雨
    ]

    WEATHER_LABELS = {
        "sunny": "阳光明媚",
        "partly_cloudy": "晴时多云",
        "cloudy": "阴云密布",
        "rainy": "小雨淅沥",
        "stormy": "雷雨交加"
    }

    def generate_weather_report(
        self,
        user_a_id: str,
        user_b_id: str,
        report_period: str = "weekly",
        db_session_param: Optional[Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        生成关系气象报告

        Args:
            user_a_id: 用户 A ID
            user_b_id: 用户 B ID
            report_period: 报告周期（daily, weekly, monthly）
            db_session_param: 可选的数据库会话

        Returns:
            气象报告
        """
        with optional_db_session(db_session_param) as db:
            # 确定报告日期范围
            now = datetime.now()
            if report_period == "daily":
                days_back = 1
                report_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif report_period == "weekly":
                days_back = 7
                report_date = now - timedelta(days=now.weekday())  # 本周一
                report_date = report_date.replace(hour=0, minute=0, second=0, microsecond=0)
            else:  # monthly
                days_back = 30
                report_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            since = now - timedelta(days=days_back)

            # 收集关系数据
            data = self._collect_relationship_data(
                user_a_id, user_b_id, since, db
            )

            # 计算情感温度
            emotional_temperature = self._calculate_emotional_temperature(data)

            # 确定天气描述
            weather_description = self._determine_weather(emotional_temperature)

            # 生成亮点
            highlights = self._generate_highlights(data, emotional_temperature)

            # 生成关注领域
            areas_of_concern = self._generate_areas_of_concern(data)

            # 生成冲突热点图
            conflict_heatmap = self._generate_conflict_heatmap(data)

            # 生成情感温度曲线
            temperature_curve = self._generate_temperature_curve(
                user_a_id, user_b_id, days_back, db
            )

            # 生成 AI 总结
            ai_summary = self._generate_ai_summary(
                weather_description, emotional_temperature, highlights, areas_of_concern
            )

            # 生成行动建议
            action_suggestions = self._generate_action_suggestions(
                weather_description, areas_of_concern
            )

            # 创建报告记录
            report_id = f"report_{report_period}_{report_date.strftime('%Y%m%d')}_{user_a_id[:4]}{user_b_id[:4]}"

            report = RelationshipWeatherReportDB(
                id=report_id,
                user_a_id=user_a_id,
                user_b_id=user_b_id,
                report_period=report_period,
                report_date=report_date,
                emotional_temperature=emotional_temperature,
                weather_description=weather_description,
                highlights=highlights,
                areas_of_concern=areas_of_concern,
                conflict_heatmap=conflict_heatmap,
                temperature_curve=temperature_curve,
                ai_summary=ai_summary,
                action_suggestions=action_suggestions
            )

            db.add(report)

            logger.info(f"Generated weather report: {report_id}, temp={emotional_temperature}")

            return {
                "id": report_id,
                "report_period": report_period,
                "report_date": report_date.isoformat(),
                "emotional_temperature": emotional_temperature,
                "weather_description": weather_description,
                "weather_label": self.WEATHER_LABELS.get(weather_description, ""),
                "highlights": highlights,
                "areas_of_concern": areas_of_concern,
                "conflict_heatmap": conflict_heatmap,
                "temperature_curve": temperature_curve,
                "ai_summary": ai_summary,
                "action_suggestions": action_suggestions
            }

    def get_user_reports(
        self,
        user_id: str,
        report_period: Optional[str] = None,
        limit: int = 10,
        db_session_param: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """获取用户的报告历史"""
        with optional_db_session(db_session_param) as db:
            query = db.query(RelationshipWeatherReportDB).filter(
                (RelationshipWeatherReportDB.user_a_id == user_id) |
                (RelationshipWeatherReportDB.user_b_id == user_id)
            )

            if report_period:
                query = query.filter(RelationshipWeatherReportDB.report_period == report_period)

            reports = query.order_by(
                RelationshipWeatherReportDB.report_date.desc()
            ).limit(limit).all()

            return [self._report_to_dict(r) for r in reports]

    def _collect_relationship_data(
        self,
        user_a_id: str,
        user_b_id: str,
        since: datetime,
        db: Any
    ) -> Dict[str, Any]:
        """收集关系数据"""
        data = {
            "messages": [],
            "warnings": [],
            "positive_interactions": 0,
            "negative_interactions": 0,
            "conversation_count": 0,
            "avg_response_time": 0
        }

        # 获取共同对话
        conversations = db.query(ConversationDB).filter(
            ((ConversationDB.user_id_1 == user_a_id) & (ConversationDB.user_id_2 == user_b_id)) |
            ((ConversationDB.user_id_1 == user_b_id) & (ConversationDB.user_id_2 == user_a_id))
        ).all()

        conversation_ids = [c.id for c in conversations]
        data["conversation_count"] = len(conversation_ids)

        if conversation_ids:
            # 获取消息
            messages = db.query(ChatMessageDB).filter(
                ChatMessageDB.conversation_id.in_(conversation_ids),
                ChatMessageDB.created_at >= since
            ).all()
            data["messages"] = messages

            # 简单分析消息情感
            for msg in messages:
                if self._is_positive_message(msg.content):
                    data["positive_interactions"] += 1
                elif self._is_negative_message(msg.content):
                    data["negative_interactions"] += 1

        # 获取预警记录
        warnings = db.query(EmotionWarningDB).filter(
            EmotionWarningDB.created_at >= since
        ).all()
        data["warnings"] = warnings

        return data

    def _is_positive_message(self, content: str) -> bool:
        """判断消息是否积极"""
        positive_words = ["开心", "喜欢", "爱", "谢谢", "感谢", "好", "棒", "温暖", "幸福"]
        return any(word in content.lower() for word in positive_words)

    def _is_negative_message(self, content: str) -> bool:
        """判断消息是否消极"""
        negative_words = ["生气", "讨厌", "烦", "难过", "失望", "够了", "随便", "呵呵"]
        return any(word in content.lower() for word in negative_words)

    def _calculate_emotional_temperature(self, data: Dict[str, Any]) -> float:
        """计算情感温度（0-100）"""
        # 基础温度 50
        temperature = 50.0

        # 基于积极/消极互动比例调整
        total = data["positive_interactions"] + data["negative_interactions"]
        if total > 0:
            positive_ratio = data["positive_interactions"] / total
            temperature += (positive_ratio - 0.5) * 40  # 最多±20 分

        # 基于预警数量扣减
        warning_count = len(data.get("warnings", []))
        temperature -= min(20, warning_count * 5)

        # 基于对话频率加分
        if data["conversation_count"] > 0:
            temperature += min(10, data["conversation_count"] * 2)

        return max(0, min(100, temperature))

    def _determine_weather(self, temperature: float) -> str:
        """根据温度确定天气描述"""
        for min_temp, max_temp, weather in self.WEATHER_DESCRIPTIONS:
            if min_temp < temperature <= max_temp:
                return weather
        return "cloudy"

    def _generate_highlights(
        self,
        data: Dict[str, Any],
        temperature: float
    ) -> List[Dict[str, Any]]:
        """生成亮点"""
        highlights = []

        if temperature >= 80:
            highlights.append({
                "type": "high_temperature",
                "title": "关系热度高涨",
                "description": "你们的情感温度处于高位，继续保持真诚的交流！"
            })

        if data["positive_interactions"] > data["negative_interactions"] * 2:
            highlights.append({
                "type": "positive_ratio",
                "title": "积极互动满满",
                "description": "你们的积极互动远超消极互动，这是健康关系的标志！"
            })

        if data["conversation_count"] >= 7:
            highlights.append({
                "type": "frequent_communication",
                "title": "沟通频繁",
                "description": "你们保持频繁的沟通，这是增进了解的基础。"
            })

        return highlights

    def _generate_areas_of_concern(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成需要关注的领域"""
        concerns = []

        warning_count = len(data.get("warnings", []))
        if warning_count >= 3:
            concerns.append({
                "type": "frequent_conflicts",
                "title": "冲突频发",
                "description": f"本周检测到{warning_count}次情绪预警，建议学习一些冲突管理技巧。",
                "priority": "high"
            })

        if data["negative_interactions"] > data["positive_interactions"]:
            concerns.append({
                "type": "negative_ratio",
                "title": "消极互动偏多",
                "description": "消极互动超过积极互动，试着多表达欣赏和感谢。",
                "priority": "medium"
            })

        if data["conversation_count"] <= 2:
            concerns.append({
                "type": "low_communication",
                "title": "沟通不足",
                "description": "本周沟通次数较少，主动联系是维系关系的关键。",
                "priority": "medium"
            })

        return concerns

    def _generate_conflict_heatmap(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """生成冲突热点图"""
        heatmap = {
            "topics": defaultdict(int),
            "times": defaultdict(int),
            "triggers": []
        }

        for warning in data.get("warnings", []):
            # 按时间统计
            if warning.created_at:
                hour = warning.created_at.hour
                if 9 <= hour < 12:
                    heatmap["times"]["morning"] += 1
                elif 12 <= hour < 18:
                    heatmap["times"]["afternoon"] += 1
                else:
                    heatmap["times"]["evening"] += 1

            # 按触发原因统计
            reason = getattr(warning, "trigger_reason", "")
            if "绝对化" in reason:
                heatmap["triggers"].append("绝对化表达")
            if "轻蔑" in reason:
                heatmap["triggers"].append("轻蔑气")

        # 转换为普通字典
        heatmap["topics"] = dict(heatmap["topics"])
        heatmap["times"] = dict(heatmap["times"])
        heatmap["triggers"] = list(set(heatmap["triggers"]))

        return heatmap

    def _generate_temperature_curve(
        self,
        user_a_id: str,
        user_b_id: str,
        days: int,
        db: Any
    ) -> List[Dict[str, Any]]:
        """生成情感温度曲线数据"""
        curve = []

        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")

            # 获取当天的数据计算温度
            # 简化实现：使用随机波动
            base_temp = 65 + (i % 7) * 3  # 基础温度
            curve.append({
                "date": date_str,
                "temperature": min(100, max(0, base_temp))
            })

        return list(reversed(curve))

    def _generate_ai_summary(
        self,
        weather: str,
        temperature: float,
        highlights: List[Dict[str, Any]],
        concerns: List[Dict[str, Any]]
    ) -> str:
        """生成 AI 总结"""
        weather_label = self.WEATHER_LABELS.get(weather, "")

        summary_parts = [f"本周你们的关系天气是{weather_label}，情感温度{temperature:.0f}分。"]

        if highlights:
            summary_parts.append(f"有{len(highlights)}个亮点时刻。")

        if concerns:
            summary_parts.append(f"需要关注{len(concerns)}个方面。")

        if temperature >= 70:
            summary_parts.append("整体而言，你们的关系处于健康状态，继续保持！")
        elif temperature >= 40:
            summary_parts.append("你们的关系有些波动，建议多关注彼此的感受。")
        else:
            summary_parts.append("你们的关系正面临挑战，建议寻求专业帮助或深入沟通。")

        return "".join(summary_parts)

    def _generate_action_suggestions(
        self,
        weather: str,
        concerns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """生成行动建议"""
        suggestions = []

        # 基于天气的通用建议
        if weather in ["rainy", "stormy"]:
            suggestions.append({
                "type": "general",
                "title": "关系修复",
                "content": "建议安排一次真诚的对话，倾听彼此的感受，避免指责和防御。",
                "priority": 1
            })
        elif weather == "cloudy":
            suggestions.append({
                "type": "general",
                "title": "增加互动",
                "content": "试着主动分享日常，增加积极的互动机会。",
                "priority": 2
            })
        else:
            suggestions.append({
                "type": "general",
                "title": "保持现状",
                "content": "你们的关系状态良好，继续保持真诚的沟通和关心。",
                "priority": 3
            })

        # 基于具体问题的建议
        for concern in concerns:
            if concern["type"] == "frequent_conflicts":
                suggestions.append({
                    "type": "conflict_management",
                    "title": "学习冲突管理",
                    "content": "可以尝试'我语句'表达法，或使用冷静锦囊技巧。",
                    "priority": 1
                })

        return sorted(suggestions, key=lambda x: x.get("priority", 99))

    def _report_to_dict(self, report: RelationshipWeatherReportDB) -> Dict[str, Any]:
        """将报告对象转换为字典"""
        return {
            "id": report.id,
            "report_period": report.report_period,
            "report_date": report.report_date.isoformat() if report.report_date else None,
            "emotional_temperature": report.emotional_temperature,
            "weather_description": report.weather_description,
            "highlights": report.highlights,
            "areas_of_concern": report.areas_of_concern,
            "conflict_heatmap": report.conflict_heatmap,
            "temperature_curve": report.temperature_curve,
            "ai_summary": report.ai_summary,
            "action_suggestions": report.action_suggestions,
            "created_at": report.created_at.isoformat() if report.created_at else None
        }


# 全局服务实例
relationship_weather_service = RelationshipWeatherService()
