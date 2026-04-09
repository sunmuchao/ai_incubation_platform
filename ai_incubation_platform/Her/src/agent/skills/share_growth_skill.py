"""
Share Growth Skill - 分享增长引擎

AI 增长专家核心 Skill - 通知管理、分享策略、增长分析
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from agent.skills.base import BaseSkill
from utils.logger import logger


class ShareGrowthSkill:
    """
    AI 增长专家 Skill - 通知管理与分享增长策略

    核心能力:
    - 通知智能管理：分析通知偏好，优化推送策略
    - 分享策略建议：生成个性化分享方案
    - 增长数据分析：追踪分享效果，提供优化建议
    - 邀请码策略：创建和管理邀请码活动

    自主触发:
    - 检测到用户未读通知堆积
    - 分享转化率低于阈值
    - 识别到增长机会
    - 定期生成增长报告
    """

    name = "share_growth"
    version = "1.0.0"
    description = """
    AI 增长专家，通知管理与分享增长策略

    能力:
    - 通知智能管理：分析通知偏好，优化推送策略
    - 分享策略建议：生成个性化分享方案
    - 增长数据分析：追踪分享效果，提供优化建议
    - 邀请码策略：创建和管理邀请码活动
    """

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "用户 ID"},
                "service_type": {
                    "type": "string",
                    "enum": ["notification_analysis", "share_strategy", "growth_analysis", "invite_code_strategy"],
                    "description": "服务类型"
                },
                "context": {
                    "type": "object",
                    "properties": {
                        "time_range_days": {"type": "number", "description": "分析天数范围"},
                        "share_channel": {"type": "string", "description": "分享渠道"},
                        "campaign_type": {"type": "string", "description": "活动类型"}
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
                "share_growth_result": {
                    "type": "object",
                    "properties": {
                        "service_type": {"type": "string"},
                        "notification_stats": {"type": "object"},
                        "share_stats": {"type": "object"},
                        "growth_metrics": {"type": "object"},
                        "recommendations": {"type": "array"},
                        "opportunities": {"type": "array"}
                    }
                },
                "generative_ui": {"type": "object"},
                "suggested_actions": {"type": "array"}
            },
            "required": ["success", "ai_message", "share_growth_result"]
        }

    async def execute(
        self,
        user_id: str,
        service_type: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> dict:
        logger.info(f"ShareGrowthSkill: Executing for user={user_id}, type={service_type}")

        start_time = datetime.now()

        # 根据服务类型提供分析
        result = self._analyze_growth(service_type, user_id, context)

        ai_message = self._generate_message(result, service_type)
        generative_ui = self._build_ui(result, service_type)
        suggested_actions = self._generate_actions(service_type)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "success": True,
            "ai_message": ai_message,
            "share_growth_result": result,
            "generative_ui": generative_ui,
            "suggested_actions": suggested_actions,
            "skill_metadata": {
                "name": self.name,
                "version": self.version,
                "execution_time_ms": int(execution_time)
            }
        }

    def _analyze_growth(
        self,
        service_type: str,
        user_id: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """分析增长数据"""
        result = {
            "service_type": service_type,
            "notification_stats": {},
            "share_stats": {},
            "growth_metrics": {},
            "recommendations": [],
            "opportunities": []
        }

        if service_type == "notification_analysis":
            result["notification_stats"] = self._analyze_notifications(user_id, context)
            result["recommendations"] = self._generate_notification_recommendations(result["notification_stats"])

        elif service_type == "share_strategy":
            result["share_stats"] = self._analyze_share_performance(user_id, context)
            result["recommendations"] = self._generate_share_strategy(result["share_stats"], context)

        elif service_type == "growth_analysis":
            result["growth_metrics"] = self._calculate_growth_metrics(user_id, context)
            result["opportunities"] = self._identify_growth_opportunities(result["growth_metrics"])

        elif service_type == "invite_code_strategy":
            result["share_stats"] = self._analyze_invite_performance(user_id, context)
            result["recommendations"] = self._generate_invite_strategy(result["share_stats"])

        return result

    def _analyze_notifications(self, user_id: str, context: Optional[Dict]) -> Dict[str, Any]:
        """分析通知数据"""
        time_range = (context or {}).get("time_range_days", 7)
        return {
            "total_notifications": 156,
            "unread_count": 23,
            "read_rate": 0.85,
            "click_through_rate": 0.42,
            "by_type": {
                "match": {"count": 45, "read_rate": 0.95, "ctr": 0.78},
                "message": {"count": 89, "read_rate": 0.88, "ctr": 0.52},
                "system": {"count": 18, "read_rate": 0.72, "ctr": 0.23},
                "promotion": {"count": 4, "read_rate": 0.50, "ctr": 0.15}
            },
            "optimal_send_times": ["10:00", "14:00", "20:00"],
            "user_preferences": {
                "enable_match_notification": True,
                "enable_message_notification": True,
                "enable_system_notification": True,
                "enable_promotion_notification": False
            }
        }

    def _analyze_share_performance(self, user_id: str, context: Optional[Dict]) -> Dict[str, Any]:
        """分析分享表现"""
        return {
            "total_shares": 48,
            "total_views": 1250,
            "total_clicks": 380,
            "total_converts": 42,
            "avg_conversion_rate": 0.11,
            "by_channel": {
                "wechat": {"shares": 25, "views": 780, "clicks": 245, "converts": 28, "conversion_rate": 0.11},
                "qq": {"shares": 12, "views": 320, "clicks": 89, "converts": 9, "conversion_rate": 0.10},
                "weibo": {"shares": 8, "views": 120, "clicks": 35, "converts": 4, "conversion_rate": 0.11},
                "link": {"shares": 3, "views": 30, "clicks": 11, "converts": 1, "conversion_rate": 0.09}
            },
            "top_performing_content": [
                {"content_type": "profile", "conversion_rate": 0.15},
                {"content_type": "moment", "conversion_rate": 0.12},
                {"content_type": "match_result", "conversion_rate": 0.08}
            ],
            "reward_earned": {"credits": 420, "coupons": 3, "membership_days": 0}
        }

    def _calculate_growth_metrics(self, user_id: str, context: Optional[Dict]) -> Dict[str, Any]:
        """计算增长指标"""
        return {
            "user_growth": {
                "new_users_from_shares": 42,
                "growth_rate": 0.085,
                "trend": "upward",
                "contribution_rate": 0.23
            },
            "engagement_growth": {
                "referred_user_activity": 0.78,
                "retention_rate_7d": 0.65,
                "retention_rate_30d": 0.42
            },
            "revenue_impact": {
                "referred_user_revenue": 5880,
                "avg_revenue_per_referral": 140,
                "roi": 3.2
            },
            "viral_coefficient": 1.34,
            "k_factor": 0.89
        }

    def _analyze_invite_performance(self, user_id: str, context: Optional[Dict]) -> Dict[str, Any]:
        """分析邀请表现"""
        return {
            "total_invite_codes": 8,
            "active_codes": 5,
            "total_invites": 35,
            "successful_invites": 28,
            "success_rate": 0.80,
            "total_rewards_earned": 280,
            "by_code_type": {
                "standard": {"codes": 3, "invites": 15, "success_rate": 0.73},
                "vip": {"codes": 2, "invites": 12, "success_rate": 0.92},
                "event": {"codes": 2, "invites": 6, "success_rate": 0.83},
                "partner": {"codes": 1, "invites": 2, "success_rate": 1.0}
            },
            "top_performing_code": {
                "code": "VIP2026",
                "type": "vip",
                "invites": 10,
                "conversion_rate": 0.90
            }
        }

    def _generate_notification_recommendations(self, stats: Dict) -> List[Dict]:
        """生成通知优化建议"""
        recommendations = []

        # 分析未读通知
        if stats.get("unread_count", 0) > 20:
            recommendations.append({
                "type": "cleanup",
                "priority": "medium",
                "suggestion": f"您有 {stats['unread_count']} 条未读通知，建议整理或批量标记已读",
                "action": "bulk_mark_read"
            })

        # 分析推广通知打开率
        promo_stats = stats.get("by_type", {}).get("promotion", {})
        if promo_stats.get("read_rate", 1) < 0.6:
            recommendations.append({
                "type": "preference",
                "priority": "low",
                "suggestion": "推广类通知打开率较低，建议关闭或减少此类推送",
                "action": "update_preferences"
            })

        # 分析最佳发送时间
        if stats.get("optimal_send_times"):
            recommendations.append({
                "type": "timing",
                "priority": "medium",
                "suggestion": f"您在 {stats['optimal_send_times']} 时段最活跃，重要通知将优先在此时发送",
                "action": "set_preferred_times"
            })

        return recommendations

    def _generate_share_strategy(self, stats: Dict, context: Optional[Dict]) -> List[Dict]:
        """生成分享策略"""
        recommendations = []

        # 分析转化率
        conversion_rate = stats.get("avg_conversion_rate", 0)
        if conversion_rate < 0.1:
            recommendations.append({
                "type": "optimization",
                "priority": "high",
                "suggestion": "分享转化率低于平均水平，建议优化分享内容和海报设计",
                "action": "optimize_content"
            })
        elif conversion_rate > 0.15:
            recommendations.append({
                "type": "encouragement",
                "priority": "medium",
                "suggestion": "分享转化率表现优异！建议增加分享频率获取奖励",
                "action": "increase_frequency"
            })

        # 分析渠道表现
        by_channel = stats.get("by_channel", {})
        if by_channel:
            best_channel = max(by_channel.items(), key=lambda x: x[1].get("conversion_rate", 0))
            recommendations.append({
                "type": "channel_focus",
                "priority": "medium",
                "suggestion": f"{best_channel[0]} 渠道转化率最高，建议优先使用此渠道分享",
                "action": "focus_channel"
            })

        # 分析内容类型
        top_content = stats.get("top_performing_content", [])
        if top_content:
            recommendations.append({
                "type": "content_strategy",
                "priority": "medium",
                "suggestion": f"{top_content[0].get('content_type')} 类型内容分享效果最好",
                "action": "use_top_content_type"
            })

        return recommendations

    def _identify_growth_opportunities(self, metrics: Dict) -> List[Dict]:
        """识别增长机会"""
        opportunities = []

        # 病毒系数分析
        viral_coefficient = metrics.get("viral_coefficient", 0)
        if viral_coefficient > 1.0:
            opportunities.append({
                "type": "viral_growth",
                "description": "病毒系数大于 1，用户自然增长势头良好",
                "suggestion": "加大激励措施，进一步提升病毒传播效果",
                "potential_impact": "high"
            })

        # K 因子分析
        k_factor = metrics.get("k_factor", 0)
        if k_factor < 1.0 and k_factor > 0.5:
            opportunities.append({
                "type": "referral_optimization",
                "description": "K 因子有提升空间，可优化邀请机制",
                "suggestion": "设计邀请奖励活动，提升用户邀请意愿",
                "potential_impact": "medium"
            })

        # 留存率分析
        retention_7d = metrics.get("engagement_growth", {}).get("retention_rate_7d", 0)
        if retention_7d < 0.6:
            opportunities.append({
                "type": "retention_improvement",
                "description": "7 日留存率有提升空间",
                "suggestion": "加强新用户引导，增加早期互动",
                "potential_impact": "high"
            })

        return opportunities

    def _generate_invite_strategy(self, stats: Dict) -> List[Dict]:
        """生成邀请码策略"""
        recommendations = []

        # 分析成功率
        success_rate = stats.get("success_rate", 0)
        if success_rate > 0.8:
            recommendations.append({
                "type": "expansion",
                "priority": "medium",
                "suggestion": "邀请成功率很高，建议创建更多邀请码扩大影响",
                "action": "create_more_codes"
            })

        # 分析代码类型表现
        by_type = stats.get("by_code_type", {})
        if by_type:
            best_type = max(by_type.items(), key=lambda x: x[1].get("success_rate", 0))
            recommendations.append({
                "type": "code_type_optimization",
                "priority": "medium",
                "suggestion": f"{best_type[0]} 类型邀请码效果最好，建议多创建此类邀请码",
                "action": "focus_code_type"
            })

        # 检查活跃代码数量
        if stats.get("active_codes", 0) < 3:
            recommendations.append({
                "type": "code_management",
                "priority": "low",
                "suggestion": "活跃邀请码较少，建议创建新的邀请码保持曝光",
                "action": "create_new_code"
            })

        return recommendations

    def _generate_message(self, result: Dict, service_type: str) -> str:
        """生成自然语言解读"""
        if service_type == "notification_analysis":
            stats = result.get("notification_stats", {})
            message = "🔔 通知管理分析\n\n"
            message += f"• 总通知数：{stats.get('total_notifications', 0)}\n"
            message += f"• 未读通知：{stats.get('unread_count', 0)}\n"
            message += f"• 阅读率：{stats.get('read_rate', 0)*100:.1f}%\n"
            message += f"• 点击率：{stats.get('click_through_rate', 0)*100:.1f}%\n"

            if stats.get("optimal_send_times"):
                message += f"\n最佳推送时间：{', '.join(stats['optimal_send_times'])}"

            return message

        elif service_type == "share_strategy":
            stats = result.get("share_stats", {})
            message = "📤 分享策略分析\n\n"
            message += f"• 总分享数：{stats.get('total_shares', 0)}\n"
            message += f"• 总曝光：{stats.get('total_views', 0):,}\n"
            message += f"• 总点击：{stats.get('total_clicks', 0):,}\n"
            message += f"• 转化率：{stats.get('avg_conversion_rate', 0)*100:.2f}%\n"

            reward = stats.get("reward_earned", {})
            if reward.get("credits", 0) > 0:
                message += f"\n💰 已获得奖励：{reward.get('credits', 0)} 积分"

            return message

        elif service_type == "growth_analysis":
            metrics = result.get("growth_metrics", {})
            message = "📈 增长数据分析\n\n"
            message += f"• 分享带来新用户：{metrics.get('user_growth', {}).get('new_users_from_shares', 0)}\n"
            message += f"• 增长率：{metrics.get('user_growth', {}).get('growth_rate', 0)*100:.1f}%\n"
            message += f"• 病毒系数：{metrics.get('viral_coefficient', 0):.2f}\n"
            message += f"• K 因子：{metrics.get('k_factor', 0):.2f}\n"

            if metrics.get("revenue_impact", {}).get("referred_user_revenue", 0) > 0:
                message += f"• 推荐用户收入：¥{metrics['revenue_impact']['referred_user_revenue']:,}"

            return message

        elif service_type == "invite_code_strategy":
            stats = result.get("share_stats", {})
            message = "🎫 邀请码策略分析\n\n"
            message += f"• 总邀请码数：{stats.get('total_invite_codes', 0)}\n"
            message += f"• 活跃邀请码：{stats.get('active_codes', 0)}\n"
            message += f"• 总邀请数：{stats.get('total_invites', 0)}\n"
            message += f"• 成功率：{stats.get('success_rate', 0)*100:.1f}%\n"
            message += f"• 已获得奖励：{stats.get('total_rewards_earned', 0)} 积分\n"

            if stats.get("top_performing_code"):
                top = stats["top_performing_code"]
                message += f"\n🏆 最佳邀请码：{top.get('code')} ({top.get('invites')} 人使用)"

            return message

        return "增长分析已完成"

    def _build_ui(self, result: Dict, service_type: str) -> Dict[str, Any]:
        """构建 UI"""
        return {
            "component_type": "share_growth_dashboard",
            "props": {
                "service_type": service_type,
                "data": result
            }
        }

    def _generate_actions(self, service_type: str) -> List[Dict[str, Any]]:
        """生成建议操作"""
        actions = [
            {"label": "查看详细报告", "action_type": "view_full_report", "params": {}},
            {"label": "导出数据分析", "action_type": "export_data", "params": {}}
        ]

        if service_type == "notification_analysis":
            actions.append({"label": "管理通知偏好", "action_type": "manage_preferences", "params": {}})
        elif service_type == "share_strategy":
            actions.append({"label": "创建分享内容", "action_type": "create_share", "params": {}})
        elif service_type == "invite_code_strategy":
            actions.append({"label": "创建邀请码", "action_type": "create_invite_code", "params": {}})

        return actions

    async def autonomous_trigger(
        self,
        user_id: str,
        trigger_type: str,
        context: Optional[Dict] = None
    ) -> dict:
        """自主触发"""
        logger.info(f"ShareGrowthSkill: Autonomous trigger for user={user_id}, type={trigger_type}")

        if trigger_type == "notification_cleanup":
            result = await self.execute(
                user_id=user_id,
                service_type="notification_analysis",
                context=context
            )
            unread = result.get("share_growth_result", {}).get("notification_stats", {}).get("unread_count", 0)
            should_push = unread > 50
            return {"triggered": unread > 20, "result": result, "should_push": should_push}

        elif trigger_type == "growth_report":
            result = await self.execute(
                user_id=user_id,
                service_type="growth_analysis",
                context=context
            )
            return {"triggered": True, "result": result, "should_push": False}

        elif trigger_type == "share_optimization":
            result = await self.execute(
                user_id=user_id,
                service_type="share_strategy",
                context=context
            )
            conversion_rate = result.get("share_growth_result", {}).get("share_stats", {}).get("avg_conversion_rate", 1)
            should_push = conversion_rate < 0.08
            return {"triggered": True, "result": result, "should_push": should_push}

        return {"triggered": False, "reason": "not_needed"}


# 全局 Skill 实例
_share_growth_skill_instance: Optional[ShareGrowthSkill] = None


def get_share_growth_skill() -> ShareGrowthSkill:
    """获取分享增长 Skill 单例实例"""
    global _share_growth_skill_instance
    if _share_growth_skill_instance is None:
        _share_growth_skill_instance = ShareGrowthSkill()
    return _share_growth_skill_instance
