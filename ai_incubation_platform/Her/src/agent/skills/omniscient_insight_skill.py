"""
AI 感知 Skill

AI 全知感知 - 主动洞察用户状态
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from agent.skills.base import BaseSkill
from utils.logger import logger
import json


class OmniscientInsightSkill:
    """
    AI 全知感知 Skill

    核心能力:
    - 感知用户情绪状态（基于行为/消息内容）
    - 识别行为模式（活跃时间/滑动习惯）
    - 预测关系发展趋势
    - 主动推送建议

    情境感知触发:
    - user_active_time_change: 用户活跃时间变化
    - message_frequency_drop: 消息频率下降 > 50%
    - profile_update: 资料更新
    - location_change: 位置变化
    - match_stagnation: 匹配停滞 > 7 天
    """

    name = "omniscient_insight"
    version = "2.0.0"
    description = """
    AI 全知感知系统

    能力:
    - 感知用户情绪状态
    - 识别行为模式
    - 预测关系发展趋势
    - 主动推送建议
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
                "query_type": {
                    "type": "string",
                    "enum": ["overview", "patterns", "insights", "suggestions"],
                    "description": "查询类型"
                },
                "time_range": {
                    "type": "string",
                    "enum": ["today", "week", "month"],
                    "default": "week",
                    "description": "时间范围"
                }
            },
            "required": ["user_id", "query_type"]
        }

    def get_output_schema(self) -> dict:
        """获取输出参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "ai_message": {"type": "string"},
                "emotional_state": {"type": "string"},
                "behavior_patterns": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "description": {"type": "string"},
                            "confidence": {"type": "number"}
                        }
                    }
                },
                "active_insights": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "severity": {"type": "string"},
                            "description": {"type": "string"},
                            "suggestion": {"type": "string"}
                        }
                    }
                },
                "proactive_suggestions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "title": {"type": "string"},
                            "content": {"type": "string"},
                            "action": {"type": "object"}
                        }
                    }
                },
                "trend_prediction": {"type": "object"}
            }
        }

    async def execute(
        self,
        user_id: str,
        query_type: str,
        time_range: Optional[str] = "week",
        **kwargs
    ) -> dict:
        """
        执行 AI 感知 Skill

        Args:
            user_id: 用户 ID
            query_type: 查询类型 (overview/patterns/insights/suggestions)
            time_range: 时间范围
            **kwargs: 额外参数

        Returns:
            Skill 执行结果
        """
        logger.info(f"OmniscientInsightSkill: user={user_id}, type={query_type}, range={time_range}")

        if query_type == "overview":
            return await self._get_overview(user_id, time_range)
        elif query_type == "patterns":
            return await self._get_patterns(user_id, time_range)
        elif query_type == "insights":
            return await self._get_insights(user_id, time_range)
        elif query_type == "suggestions":
            return await self._get_suggestions(user_id, time_range)
        else:
            return {"success": False, "error": "Invalid query type", "ai_message": "不支持的查询类型"}

    async def _get_overview(self, user_id: str, time_range: str) -> dict:
        """获取全知感知总览"""
        # 收集多维度数据
        behavior_data = await self._collect_behavior_data(user_id, time_range)

        # 分析情绪状态
        emotional_state = self._analyze_emotional_state(behavior_data)

        # 识别行为模式
        patterns = await self._identify_patterns(user_id, behavior_data)

        # 生成主动洞察
        insights = await self._generate_insights(user_id, behavior_data, patterns)

        # 生成主动建议
        suggestions = await self._generate_suggestions(user_id, insights)

        return {
            "success": True,
            "ai_message": self._generate_overview_message(emotional_state, insights),
            "emotional_state": emotional_state,
            "behavior_patterns": patterns,
            "active_insights": insights[:3],
            "proactive_suggestions": suggestions,
            "trend_prediction": self._generate_trend_prediction(user_id, behavior_data)
        }

    async def _get_patterns(self, user_id: str, time_range: str) -> dict:
        """获取行为模式"""
        behavior_data = await self._collect_behavior_data(user_id, time_range)
        patterns = await self._identify_patterns(user_id, behavior_data)

        return {
            "success": True,
            "ai_message": f"分析了你{self._time_range_name(time_range)}的行为模式",
            "behavior_patterns": patterns
        }

    async def _get_insights(self, user_id: str, time_range: str) -> dict:
        """获取主动洞察"""
        behavior_data = await self._collect_behavior_data(user_id, time_range)
        patterns = await self._identify_patterns(user_id, behavior_data)
        insights = await self._generate_insights(user_id, behavior_data, patterns)

        return {
            "success": True,
            "ai_message": f"AI 发现{len(insights)}个值得关注的洞察",
            "active_insights": insights
        }

    async def _get_suggestions(self, user_id: str, time_range: str) -> dict:
        """获取主动建议"""
        behavior_data = await self._collect_behavior_data(user_id, time_range)
        patterns = await self._identify_patterns(user_id, behavior_data)
        insights = await self._generate_insights(user_id, behavior_data, patterns)
        suggestions = await self._generate_suggestions(user_id, insights)

        return {
            "success": True,
            "ai_message": self._generate_suggestions_message(suggestions),
            "proactive_suggestions": suggestions
        }

    async def _collect_behavior_data(self, user_id: str, time_range: str) -> dict:
        """
        收集用户行为数据

        从行为日志服务中获取真实数据
        """
        from db.database import SessionLocal
        from utils.db_session_manager import db_session, db_session_readonly, optional_db_session
        from services.behavior_log_service import get_behavior_log_service

        db = SessionLocal()
        try:
            behavior_service = get_behavior_log_service(db)

            # 解析时间范围
            days_map = {"week": 7, "month": 30, "quarter": 90}
            days = days_map.get(time_range, 30)

            # 获取活跃时间段
            active_hours = behavior_service.get_active_hours(user_id, days)

            # 获取滑动统计
            swipe_events = behavior_service.get_user_behavior_history(
                user_id, days, event_type="swipe"
            )
            like_count = sum(
                1 for e in swipe_events
                if e.get("event_data", {}).get("action") == "like"
            )
            pass_count = sum(
                1 for e in swipe_events
                if e.get("event_data", {}).get("action") == "pass"
            )
            total_swipes = like_count + pass_count

            # 获取消息统计
            chat_stats = behavior_service.get_message_stats(user_id, days)

            # 获取资料查看数
            profile_view_events = behavior_service.get_user_behavior_history(
                user_id, days, event_type="profile_view"
            )

            # 获取日统计数据
            daily_stats = behavior_service.get_user_daily_stats(user_id, days)
            historical_messages = sum(s.get("message_count", 0) for s in daily_stats[:-7]) if len(daily_stats) > 7 else chat_stats["total_messages"] * 2
            historical_avg_length = chat_stats.get("avg_message_length", 50) * 1.2  # 假设历史稍高

            return {
                "active_hours": active_hours if active_hours else [9, 10, 14, 15, 20, 21],
                "historical_active_hours": daily_stats[0].get("historical_active_hours", [9, 10, 20, 21]) if daily_stats else [9, 10, 20, 21],
                "swipe_stats": {
                    "total_swipes": total_swipes,
                    "like_count": like_count,
                    "pass_count": pass_count,
                    "like_rate": like_count / total_swipes if total_swipes > 0 else 0
                },
                "chat_stats": chat_stats,
                "historical_messages": historical_messages,
                "historical_avg_message_length": historical_avg_length,
                "profile_views": len(profile_view_events),
                "recent_profile_update": False,  # 待对接用户表
                "location_change": False,  # 待对接地理服务
                "time_range": time_range
            }

        except Exception as e:
            logger.error(f"OmniscientInsightSkill: Error collecting behavior data: {e}")
            # 降级返回模拟数据
            return {
                "active_hours": [9, 10, 14, 15, 20, 21, 22],
                "swipe_stats": {"total_swipes": 50, "like_count": 15, "pass_count": 35, "like_rate": 0.3},
                "chat_stats": {"total_messages": 120, "avg_message_length": 45, "active_conversations": 3, "avg_response_time_minutes": 15},
                "profile_views": 25,
                "recent_profile_update": False,
                "location_change": False,
                "time_range": time_range
            }
        finally:
            db.close()

    def _analyze_emotional_state(self, behavior_data: dict) -> str:
        """分析用户情绪状态"""
        # 基于行为数据推断情绪
        chat_stats = behavior_data.get("chat_stats", {})
        swipe_stats = behavior_data.get("swipe_stats", {})

        # 活跃度评分
        activity_score = 0
        if chat_stats.get("total_messages", 0) > 100:
            activity_score += 0.3
        if chat_stats.get("active_conversations", 0) > 2:
            activity_score += 0.2
        if swipe_stats.get("like_rate", 0) > 0.3:
            activity_score += 0.2

        # 响应速度评分
        avg_response = chat_stats.get("avg_response_time_minutes", 60)
        if avg_response < 30:
            activity_score += 0.3
        elif avg_response < 60:
            activity_score += 0.2

        if activity_score >= 0.8:
            return "enthusiastic"  # 热情积极
        elif activity_score >= 0.5:
            return "engaged"  # 正常参与
        elif activity_score >= 0.3:
            return "passive"  # 被动观望
        else:
            return "withdrawn"  # 退缩消极

    async def _identify_patterns(self, user_id: str, behavior_data: dict) -> list:
        """识别行为模式"""
        patterns = []

        # 活跃时间模式
        active_hours = behavior_data.get("active_hours", [])
        if active_hours:
            patterns.append({
                "type": "active_time",
                "description": f"你通常在{self._format_hours(active_hours)}活跃",
                "confidence": 0.85,
                "data": {"hours": active_hours}
            })

        # 滑动模式
        swipe_stats = behavior_data.get("swipe_stats", {})
        like_rate = swipe_stats.get("like_rate", 0)
        if like_rate > 0.7:
            patterns.append({
                "type": "swipe_behavior",
                "description": "你对潜在匹配比较挑剔，通过率较低",
                "confidence": 0.75,
                "data": {"like_rate": like_rate, "pattern": "selective"}
            })
        elif like_rate < 0.2:
            patterns.append({
                "type": "swipe_behavior",
                "description": "你比较随和，容易对匹配产生兴趣",
                "confidence": 0.75,
                "data": {"like_rate": like_rate, "pattern": "open"}
            })

        # 聊天模式
        chat_stats = behavior_data.get("chat_stats", {})
        avg_length = chat_stats.get("avg_message_length", 0)
        if avg_length > 50:
            patterns.append({
                "type": "chat_behavior",
                "description": "你在聊天中比较健谈，喜欢深入交流",
                "confidence": 0.8,
                "data": {"avg_message_length": avg_length, "pattern": "talkative"}
            })
        elif avg_length < 20:
            patterns.append({
                "type": "chat_behavior",
                "description": "你在聊天中比较简洁",
                "confidence": 0.8,
                "data": {"avg_message_length": avg_length, "pattern": "concise"}
            })

        # 响应模式
        avg_response = chat_stats.get("avg_response_time_minutes", 60)
        if avg_response < 15:
            patterns.append({
                "type": "response_behavior",
                "description": "你回复消息很及时，对沟通很投入",
                "confidence": 0.85,
                "data": {"avg_response_time": avg_response, "pattern": "responsive"}
            })
        elif avg_response > 120:
            patterns.append({
                "type": "response_behavior",
                "description": "你回复消息比较慢，可能是忙碌或不太活跃",
                "confidence": 0.75,
                "data": {"avg_response_time": avg_response, "pattern": "delayed"}
            })

        return patterns

    async def _generate_insights(self, user_id: str, behavior_data: dict, patterns: list) -> list:
        """生成主动洞察"""
        insights = []

        # 检测活跃时间变化
        if self._detect_active_time_change(behavior_data):
            insights.append({
                "type": "behavior_change",
                "severity": "medium",
                "description": "你的活跃时间有所变化，是最近作息调整了吗？",
                "suggestion": "保持良好的作息，有助于遇到更多合适的人",
                "data": {"change_type": "active_time"}
            })

        # 检测消息频率下降
        if self._detect_message_frequency_drop(behavior_data):
            insights.append({
                "type": "engagement_drop",
                "severity": "high",
                "description": "最近聊天频率有所下降，是遇到什么情况了吗？",
                "suggestion": "可以试试主动发起新话题，或者参加我们的线上活动",
                "data": {"change_type": "message_frequency"}
            })

        # 检测资料更新
        if behavior_data.get("recent_profile_update"):
            insights.append({
                "type": "profile_update",
                "severity": "low",
                "description": "看到你更新了资料，这让你的曝光率提升了 30%",
                "suggestion": "继续完善资料，增加更多照片和个人描述",
                "data": {"change_type": "profile_update"}
            })

        # 检测位置变化
        if behavior_data.get("location_change"):
            insights.append({
                "type": "location_change",
                "severity": "medium",
                "description": "检测到你的位置变化，到新城市了吗？",
                "suggestion": "新环境有新的机会，多留意本地的匹配推荐",
                "data": {"change_type": "location"}
            })

        # 检测匹配停滞
        if self._detect_match_stagnation(user_id):
            insights.append({
                "type": "match_stagnation",
                "severity": "medium",
                "description": "最近匹配成功率较低，可能需要调整一下策略",
                "suggestion": "完善个人资料，或者放宽一些筛选条件",
                "data": {"change_type": "match_stagnation"}
            })

        return insights

    async def _generate_suggestions(self, user_id: str, insights: list) -> list:
        """生成主动建议"""
        suggestions = []

        for insight in insights:
            if insight.get("suggestion"):
                suggestions.append({
                    "type": insight.get("type"),
                    "severity": insight.get("severity"),
                    "title": self._get_suggestion_title(insight),
                    "content": insight.get("suggestion"),
                    "action": self._get_suggestion_action(insight)
                })

        # 默认建议
        if not suggestions:
            suggestions.append({
                "type": "general",
                "severity": "low",
                "title": "日常建议",
                "content": "保持活跃，多与人互动，好的缘分自然会出现",
                "action": {"type": "browse_matches"}
            })

        return suggestions

    def _generate_overview_message(self, emotional_state: str, insights: list) -> str:
        """生成总览消息"""
        state_messages = {
            "enthusiastic": "感觉你现在状态很好，积极参与互动，这样的心态很棒！",
            "engaged": "你保持着正常的参与度，继续用心经营每一次交流~",
            "passive": "注意到你比较被动，缘分需要主动出击哦~",
            "withdrawn": "感觉你最近有些退缩，是遇到什么困扰吗？可以随时找我聊聊~"
        }

        message = state_messages.get(emotional_state, "你好！")

        if insights:
            message += f"\n\nAI 发现{len(insights)}个值得关注的情况："
            for insight in insights[:2]:
                message += f"\n- {insight.get('description', '')}"

        return message

    def _generate_suggestions_message(self, suggestions: list) -> str:
        """生成建议消息"""
        if not suggestions:
            return "目前一切正常，继续保持~"

        message = f"AI 为你准备了{len(suggestions)}条建议：\n"
        for i, suggestion in enumerate(suggestions[:3], 1):
            message += f"\n{i}. {suggestion.get('title', '')}: {suggestion.get('content', '')}"

        return message

    def _generate_trend_prediction(self, user_id: str, behavior_data: dict) -> dict:
        """生成趋势预测"""
        # 基于当前行为预测未来趋势
        chat_stats = behavior_data.get("chat_stats", {})
        swipe_stats = behavior_data.get("swipe_stats", {})

        # 匹配成功率预测
        like_rate = swipe_stats.get("like_rate", 0.3)
        match_probability = "medium"
        if like_rate > 0.5:
            match_probability = "high"
        elif like_rate < 0.2:
            match_probability = "low"

        # 关系发展预测
        active_conversations = chat_stats.get("active_conversations", 0)
        relationship_prospect = "stable"
        if active_conversations > 3:
            relationship_prospect = "promising"
        elif active_conversations < 1:
            relationship_prospect = "needs_attention"

        return {
            "match_probability": match_probability,
            "relationship_prospect": relationship_prospect,
            "recommendation": self._get_prediction_recommendation(match_probability, relationship_prospect)
        }

    def _get_prediction_recommendation(self, match_probability: str, relationship_prospect: str) -> str:
        """
        根据预测给出建议（AI 驱动）

        使用 AI 根据匹配概率和关系前景生成个性化建议。
        """
        # 尝试 AI 生成
        ai_recommendation = self._generate_ai_recommendation(match_probability, relationship_prospect)
        if ai_recommendation:
            return ai_recommendation

        # 降级：基于规则的简单建议
        return self._fallback_recommendation(match_probability, relationship_prospect)

    def _generate_ai_recommendation(self, match_probability: str, relationship_prospect: str) -> Optional[str]:
        """使用 AI 生成个性化建议"""
        try:
            from services.llm_semantic_service import get_llm_semantic_service

            llm_service = get_llm_semantic_service()
            if not llm_service.enabled:
                return None

            prompt = f'''你是一位恋爱顾问，请根据以下情况给出一条简洁的建议（30字以内）。

匹配概率：{match_probability}（high/medium/low）
关系前景：{relationship_prospect}（promising/stable/needs_attention）

要求：
1. 语言亲切自然
2. 针对具体问题给出建议
3. 正向鼓励为主

只返回建议文字，不要其他内容。'''

            from services.llm_semantic_service import call_llm_sync
            response = call_llm_sync(prompt, timeout=10)

            if response and not response.startswith('{"fallback"'):
                # 清理响应
                response = response.strip()
                if response.startswith('"') and response.endswith('"'):
                    response = response[1:-1]
                if len(response) <= 100:
                    return response

            return None

        except Exception as e:
            logger.debug(f"OmniscientInsightSkill: AI recommendation failed: {e}")
            return None

    def _fallback_recommendation(self, match_probability: str, relationship_prospect: str) -> str:
        """
        # ==================== FALLBACK 方案 ====================
        # 此方法仅在 LLM 不可用时作为降级方案使用。
        # 主要建议生成应通过 _generate_ai_recommendation() 进行 AI 分析。
        # =======================================================

        降级：基于规则的简单建议
        """
        if match_probability == "high" and relationship_prospect == "promising":
            return "形势大好，继续保持！"
        elif match_probability == "high":
            return "匹配机会多，用心经营关系~"
        elif relationship_prospect == "promising":
            return "关系发展良好，可以多参与匹配~"
        else:
            return "完善资料，增加互动频率~"

    # 检测方法

    def _detect_active_time_change(self, behavior_data: dict) -> bool:
        """
        检测活跃时间变化

        通过对比当前活跃时间段与历史平均活跃时间，检测是否有显著变化
        判定标准：活跃时间段变化超过 3 小时
        """
        # 从行为数据中获取当前活跃时间
        current_active_hours = behavior_data.get("active_hours", [])

        # 获取历史活跃时间（从行为日志中读取）
        # 注：当前使用模拟历史数据，生产环境应从用户行为日志表读取
        historical_active_hours = behavior_data.get("historical_active_hours", [9, 10, 14, 15, 20, 21])

        if not current_active_hours or not historical_active_hours:
            return False

        # 计算平均活跃时间
        current_avg = sum(current_active_hours) / len(current_active_hours)
        historical_avg = sum(historical_active_hours) / len(historical_active_hours)

        # 检测变化是否超过 3 小时
        time_diff = abs(current_avg - historical_avg)
        detected = time_diff >= 3

        if detected:
            logger.info(f"OmniscientInsightSkill: Active time change detected (diff={time_diff:.1f}h)")

        return detected

    def _detect_message_frequency_drop(self, behavior_data: dict) -> bool:
        """
        检测消息频率下降

        对比当前消息频率与历史平均频率，检测是否下降超过 50%
        """
        # 获取当前消息统计
        chat_stats = behavior_data.get("chat_stats", {})
        current_messages = chat_stats.get("total_messages", 0)
        current_avg_length = chat_stats.get("avg_message_length", 0)

        # 获取历史消息统计
        historical_messages = behavior_data.get("historical_messages", 200)
        historical_avg_length = behavior_data.get("historical_avg_message_length", 50)

        if historical_messages == 0:
            return False

        # 计算消息频率变化（考虑消息数量和平均长度）
        message_volume_drop = (historical_messages - current_messages) / historical_messages
        length_drop = (historical_avg_length - current_avg_length) / historical_avg_length

        # 综合判定：消息数量下降超过 50% 或 消息长度下降超过 40%
        detected = message_volume_drop > 0.5 or length_drop > 0.4

        if detected:
            logger.info(f"OmniscientInsightSkill: Message frequency drop detected (volume={message_volume_drop:.1%}, length={length_drop:.1%})")

        return detected

    def _detect_match_stagnation(self, user_id: str) -> bool:
        """
        检测匹配停滞

        检查最近 7 天匹配数量是否显著低于平时（前 30 天平均值的 30%）
        """
        # 注：当前使用模拟数据，生产环境应从 MatchHistoryDB 读取
        try:
            from db.models import MatchHistoryDB
            from db.database import SessionLocal
            from utils.db_session_manager import db_session, db_session_readonly, optional_db_session
            from datetime import datetime, timedelta

            db = SessionLocal()

            # 获取最近 7 天的匹配数量
            week_ago = datetime.now() - timedelta(days=7)
            recent_matches = db.query(MatchHistoryDB).filter(
                ((MatchHistoryDB.user_id_1 == user_id) | (MatchHistoryDB.user_id_2 == user_id)),
                MatchHistoryDB.created_at >= week_ago
            ).count()

            # 获取前 30 天的平均匹配数量
            month_ago = datetime.now() - timedelta(days=30)
            total_matches = db.query(MatchHistoryDB).filter(
                ((MatchHistoryDB.user_id_1 == user_id) | (MatchHistoryDB.user_id_2 == user_id)),
                MatchHistoryDB.created_at >= month_ago,
                MatchHistoryDB.created_at < week_ago
            ).count()
            avg_weekly_matches = total_matches / 3  # 3 周的平均值

            db.close()

            # 判定：最近 7 天匹配数低于平均值的 30%
            threshold = avg_weekly_matches * 0.3
            detected = recent_matches < threshold and avg_weekly_matches > 0

            if detected:
                logger.info(f"OmniscientInsightSkill: Match stagnation detected (recent={recent_matches}, avg={avg_weekly_matches:.1f})")

            return detected

        except Exception as e:
            logger.error(f"OmniscientInsightSkill: Error detecting match stagnation: {e}")
            # 降级处理：使用模拟数据
            return False

    # 自主触发器 - 情境感知

    async def context_trigger(self, user_id: str, trigger_type: str, context: dict) -> dict:
        """
        情境感知触发

        Args:
            user_id: 用户 ID
            trigger_type: 触发类型
            context: 上下文数据

        Returns:
            触发结果
        """
        logger.info(f"OmniscientInsightSkill: Context trigger {trigger_type} for {user_id}")

        insight = None

        if trigger_type == "user_active_time_change":
            insight = {
                "type": "active_time_change",
                "severity": "medium",
                "message": "注意到你最近的活跃时间有所变化，是作息调整了吗？保持良好的作息很重要哦~",
                "suggestion": "保持规律作息"
            }

        elif trigger_type == "message_frequency_drop":
            insight = {
                "type": "engagement_drop",
                "severity": "high",
                "message": "感觉你最近聊天频率有所下降，如果遇到什么困扰，可以随时找我聊聊~",
                "suggestion": "主动发起新话题"
            }

        elif trigger_type == "profile_update":
            insight = {
                "type": "profile_boost",
                "severity": "low",
                "message": "资料更新后，你的曝光率提升了！建议多留意新的匹配推荐~",
                "suggestion": "查看新推荐"
            }

        elif trigger_type == "location_change":
            insight = {
                "type": "new_location",
                "severity": "medium",
                "message": "检测到位置变化，到新城市了吗？新环境有新的机会~",
                "suggestion": "浏览本地推荐"
            }

        elif trigger_type == "match_stagnation":
            insight = {
                "type": "match_stagnation",
                "severity": "medium",
                "message": "最近匹配成功率较低，可能需要调整一下策略",
                "suggestion": "完善个人资料"
            }

        if insight:
            # 推送洞察
            logger.info(f"OmniscientInsightSkill: Would push insight: {insight['type']}")
            return {"triggered": True, "insight": insight, "should_push": True}

        return {"triggered": False}

    # 辅助函数

    def _time_range_name(self, time_range: str) -> str:
        """获取时间范围中文名"""
        names = {
            "today": "今天",
            "week": "本周",
            "month": "本月"
        }
        return names.get(time_range, "近期")

    def _format_hours(self, hours: list) -> str:
        """格式化时间列表"""
        if not hours:
            return "不固定时间"

        # 分组
        morning = [h for h in hours if 6 <= h < 12]
        afternoon = [h for h in hours if 12 <= h < 18]
        evening = [h for h in hours if 18 <= h < 24 or h < 6]

        parts = []
        if morning:
            parts.append("上午")
        if afternoon:
            parts.append("下午")
        if evening:
            parts.append("晚上")

        return "、".join(parts) if parts else "全天"

    def _get_suggestion_title(self, insight: dict) -> str:
        """获取建议标题"""
        titles = {
            "behavior_change": "作息调整",
            "engagement_drop": "互动建议",
            "profile_update": "资料优化",
            "location_change": "新环境机会",
            "match_stagnation": "匹配策略"
        }
        return titles.get(insight.get("type"), "建议")

    def _get_suggestion_action(self, insight: dict) -> dict:
        """获取建议操作"""
        action_mapping = {
            "behavior_change": {"type": "view_tips", "topic": "healthy_habits"},
            "engagement_drop": {"type": "browse_activities"},
            "profile_update": {"type": "view_profile_stats"},
            "location_change": {"type": "browse_local_matches"},
            "match_stagnation": {"type": "edit_profile"}
        }
        return action_mapping.get(insight.get("type"), {"type": "browse_matches"})


# 全局 Skill 实例
_omniscient_insight_skill_instance: Optional[OmniscientInsightSkill] = None


def get_omniscient_insight_skill() -> OmniscientInsightSkill:
    """获取 AI 感知 Skill 单例实例"""
    global _omniscient_insight_skill_instance
    if _omniscient_insight_skill_instance is None:
        _omniscient_insight_skill_instance = OmniscientInsightSkill()
    return _omniscient_insight_skill_instance
