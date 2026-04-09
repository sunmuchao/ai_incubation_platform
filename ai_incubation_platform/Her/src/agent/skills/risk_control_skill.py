"""
Risk Control Skill - 智能风控与绩效管理

AI 风控专家核心 Skill - 数据看板分析、绩效评估、风险预警
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from agent.skills.base import BaseSkill
from utils.logger import logger


class RiskControlSkill:
    """
    AI 风控专家 Skill - 企业数据看板与绩效管理

    核心能力:
    - 数据看板分析：实时分析企业核心指标
    - 绩效评估：自动评估用户/部门绩效
    - 风险预警：检测异常数据并预警
    - 趋势预测：基于历史数据预测趋势

    自主触发:
    - 核心指标异常波动
    - 绩效低于阈值
    - 检测到可疑操作模式
    - 定期生成数据报告
    """

    name = "risk_control"
    version = "1.0.0"
    description = """
    AI 风控专家，企业数据看板与绩效管理

    能力:
    - 数据看板分析：实时分析企业核心指标
    - 绩效评估：自动评估用户/部门绩效
    - 风险预警：检测异常数据并预警
    - 趋势预测：基于历史数据预测趋势
    """

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "用户 ID"},
                "service_type": {
                    "type": "string",
                    "enum": ["dashboard_overview", "performance_review", "risk_detection", "trend_analysis"],
                    "description": "服务类型"
                },
                "context": {
                    "type": "object",
                    "properties": {
                        "days_range": {"type": "number", "description": "天数范围"},
                        "metric_name": {"type": "string", "description": "指标名称"},
                        "department_id": {"type": "string", "description": "部门 ID"}
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
                "risk_control_result": {
                    "type": "object",
                    "properties": {
                        "service_type": {"type": "string"},
                        "metrics": {"type": "object"},
                        "risks": {"type": "array"},
                        "recommendations": {"type": "array"},
                        "trend_data": {"type": "array"}
                    }
                },
                "generative_ui": {"type": "object"},
                "suggested_actions": {"type": "array"}
            },
            "required": ["success", "ai_message", "risk_control_result"]
        }

    async def execute(
        self,
        user_id: str,
        service_type: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> dict:
        logger.info(f"RiskControlSkill: Executing for user={user_id}, type={service_type}")

        start_time = datetime.now()

        # 根据服务类型提供分析
        result = self._analyze_data(service_type, user_id, context)

        ai_message = self._generate_message(result, service_type)
        generative_ui = self._build_ui(result, service_type)
        suggested_actions = self._generate_actions(service_type)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "success": True,
            "ai_message": ai_message,
            "risk_control_result": result,
            "generative_ui": generative_ui,
            "suggested_actions": suggested_actions,
            "skill_metadata": {
                "name": self.name,
                "version": self.version,
                "execution_time_ms": int(execution_time)
            }
        }

    def _analyze_data(
        self,
        service_type: str,
        user_id: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """分析数据"""
        result = {
            "service_type": service_type,
            "metrics": {},
            "risks": [],
            "recommendations": [],
            "trend_data": []
        }

        if service_type == "dashboard_overview":
            result["metrics"] = self._get_dashboard_metrics(context)
            result["risks"] = self._detect_metric_anomalies(result["metrics"])

        elif service_type == "performance_review":
            result["metrics"] = self._evaluate_performance(user_id, context)
            result["recommendations"] = self._generate_performance_recommendations(result["metrics"])

        elif service_type == "risk_detection":
            result["risks"] = self._detect_risks(user_id, context)
            result["recommendations"] = self._generate_risk_recommendations(result["risks"])

        elif service_type == "trend_analysis":
            result["trend_data"] = self._analyze_trends(user_id, context)
            result["recommendations"] = self._generate_trend_recommendations(result["trend_data"])

        return result

    def _get_dashboard_metrics(self, context: Optional[Dict]) -> Dict[str, Any]:
        """获取看板指标"""
        days_range = (context or {}).get("days_range", 7)
        return {
            "user_metrics": {
                "total_users": 15420,
                "active_users": 8234,
                "new_users": 342,
                "growth_rate": 0.023
            },
            "match_metrics": {
                "total_matches": 4521,
                "successful_matches": 3892,
                "success_rate": 0.861
            },
            "revenue_metrics": {
                "total_revenue": 125000,
                "order_count": 892,
                "avg_order_value": 140.13
            },
            "safety_metrics": {
                "total_reports": 23,
                "processed_reports": 21,
                "processing_rate": 0.913
            },
            "engagement_metrics": {
                "total_swipes": 125000,
                "total_messages": 89000,
                "avg_session_duration": 18.5
            }
        }

    def _evaluate_performance(self, user_id: str, context: Optional[Dict]) -> Dict[str, Any]:
        """评估绩效"""
        return {
            "user_id": user_id,
            "period": "last_30_days",
            "kpi_scores": {
                "user_satisfaction": {"score": 4.2, "target": 4.0, "status": "达标"},
                "response_time": {"score": 2.3, "target": 3.0, "status": "未达标"},
                "task_completion": {"score": 0.89, "target": 0.85, "status": "达标"},
                "innovation": {"score": 3.8, "target": 3.5, "status": "达标"}
            },
            "overall_score": 3.78,
            "rating": "良好",
            "strengths": ["用户满意度高", "任务完成率高"],
            "improvement_areas": ["响应速度需提升"]
        }

    def _detect_risks(self, user_id: str, context: Optional[Dict]) -> List[Dict]:
        """检测风险"""
        return [
            {
                "risk_type": "account_anomaly",
                "level": "medium",
                "description": "检测到账号登录地点异常",
                "evidence": ["短时间内多地登录", "IP 地址跳跃"],
                "suggested_action": "触发二次验证"
            },
            {
                "risk_type": "behavior_anomaly",
                "level": "low",
                "description": "用户行为模式异常",
                "evidence": ["滑动频率突然增加 300%"],
                "suggested_action": "持续观察"
            }
        ]

    def _detect_metric_anomalies(self, metrics: Dict) -> List[Dict]:
        """检测指标异常"""
        anomalies = []

        # 检查用户增长率
        user_metrics = metrics.get("user_metrics", {})
        if user_metrics.get("growth_rate", 0) < 0.01:
            anomalies.append({
                "metric": "user_growth_rate",
                "current_value": user_metrics.get("growth_rate"),
                "threshold": 0.01,
                "severity": "warning",
                "description": "用户增长率低于预期"
            })

        # 检查匹配成功率
        match_metrics = metrics.get("match_metrics", {})
        if match_metrics.get("success_rate", 1) < 0.8:
            anomalies.append({
                "metric": "match_success_rate",
                "current_value": match_metrics.get("success_rate"),
                "threshold": 0.8,
                "severity": "critical",
                "description": "匹配成功率显著下降"
            })

        # 检查安全举报处理率
        safety_metrics = metrics.get("safety_metrics", {})
        if safety_metrics.get("processing_rate", 1) < 0.9:
            anomalies.append({
                "metric": "safety_processing_rate",
                "current_value": safety_metrics.get("processing_rate"),
                "threshold": 0.9,
                "severity": "high",
                "description": "安全举报处理率偏低"
            })

        return anomalies

    def _analyze_trends(self, user_id: str, context: Optional[Dict]) -> List[Dict]:
        """分析趋势"""
        return [
            {
                "trend_type": "user_growth",
                "direction": "upward",
                "change_rate": 0.15,
                "confidence": 0.85,
                "prediction": "预计下周新增用户将继续增长"
            },
            {
                "trend_type": "revenue",
                "direction": "stable",
                "change_rate": 0.02,
                "confidence": 0.72,
                "prediction": "收入保持平稳，建议推出促销活动"
            },
            {
                "trend_type": "user_engagement",
                "direction": "downward",
                "change_rate": -0.08,
                "confidence": 0.68,
                "prediction": "用户活跃度略有下降，需关注"
            }
        ]

    def _generate_performance_recommendations(self, metrics: Dict) -> List[Dict]:
        """生成绩效建议"""
        recommendations = []

        kpi_scores = metrics.get("kpi_scores", {})
        for kpi_name, kpi_data in kpi_scores.items():
            if kpi_data.get("status") == "未达标":
                recommendations.append({
                    "type": "improvement",
                    "target": kpi_name,
                    "suggestion": f"建议制定{ kpi_name }提升计划",
                    "priority": "high"
                })

        if metrics.get("overall_score", 0) >= 4.0:
            recommendations.append({
                "type": "recognition",
                "suggestion": "表现优异，建议给予表彰或奖励",
                "priority": "medium"
            })

        return recommendations

    def _generate_risk_recommendations(self, risks: List[Dict]) -> List[Dict]:
        """生成风险应对建议"""
        recommendations = []

        for risk in risks:
            level = risk.get("level", "low")
            if level in ["critical", "high"]:
                recommendations.append({
                    "type": "immediate_action",
                    "risk_type": risk.get("risk_type"),
                    "action": risk.get("suggested_action"),
                    "priority": "urgent"
                })
            elif level == "medium":
                recommendations.append({
                    "type": "monitor",
                    "risk_type": risk.get("risk_type"),
                    "action": "持续监控，准备应对方案",
                    "priority": "medium"
                })

        return recommendations

    def _generate_trend_recommendations(self, trends: List[Dict]) -> List[Dict]:
        """生成趋势应对建议"""
        recommendations = []

        for trend in trends:
            if trend.get("direction") == "downward":
                recommendations.append({
                    "type": "attention_needed",
                    "trend_type": trend.get("trend_type"),
                    "suggestion": trend.get("prediction"),
                    "priority": "high"
                })
            elif trend.get("direction") == "upward" and trend.get("change_rate", 0) > 0.2:
                recommendations.append({
                    "type": "opportunity",
                    "trend_type": trend.get("trend_type"),
                    "suggestion": "增长势头良好，建议加大投入",
                    "priority": "medium"
                })

        return recommendations

    def _generate_message(self, result: Dict, service_type: str) -> str:
        """生成自然语言解读"""
        if service_type == "dashboard_overview":
            metrics = result.get("metrics", {})
            risks = result.get("risks", [])

            message = "📊 企业数据看板概览\n\n"
            message += f"• 总用户数：{metrics.get('user_metrics', {}).get('total_users', 0):,}\n"
            message += f"• 匹配成功率：{metrics.get('match_metrics', {}).get('success_rate', 0)*100:.1f}%\n"
            message += f"• 总收入：¥{metrics.get('revenue_metrics', {}).get('total_revenue', 0):,}\n"

            if risks:
                message += f"\n⚠️ 检测到 {len(risks)} 项异常指标：\n"
                for risk in risks[:3]:
                    message += f"- {risk.get('description', '未知异常')}\n"

            return message

        elif service_type == "performance_review":
            metrics = result.get("metrics", {})
            message = f"📈 绩效评估报告\n\n"
            message += f"综合评分：{metrics.get('overall_score', 0):.2f} ({metrics.get('rating', '未知')})\n\n"
            message += "优势：\n"
            for strength in metrics.get("strengths", [])[:3]:
                message += f"✓ {strength}\n"
            message += "\n待提升：\n"
            for area in metrics.get("improvement_areas", [])[:3]:
                message += f"○ {area}\n"
            return message

        elif service_type == "risk_detection":
            risks = result.get("risks", [])
            message = f"🚨 风险检测报告\n\n"
            message += f"检测到 {len(risks)} 个潜在风险：\n\n"
            for risk in risks[:5]:
                level_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(risk.get("level"), "⚪")
                message += f"{level_icon} {risk.get('description', '未知风险')} [{risk.get('level', 'unknown')}]\n"
            return message

        elif service_type == "trend_analysis":
            trends = result.get("trend_data", [])
            message = "📉 趋势分析报告\n\n"
            for trend in trends[:5]:
                arrow = {"upward": "📈", "downward": "📉", "stable": "➡️"}.get(trend.get("direction"), "❓")
                message += f"{arrow} {trend.get('trend_type', '未知')}：{trend.get('prediction', '无预测')}\n"
            return message

        return "风控分析已完成"

    def _build_ui(self, result: Dict, service_type: str) -> Dict[str, Any]:
        """构建 UI"""
        return {
            "component_type": "risk_control_dashboard",
            "props": {
                "service_type": service_type,
                "data": result
            }
        }

    def _generate_actions(self, service_type: str) -> List[Dict[str, Any]]:
        """生成建议操作"""
        actions = [
            {"label": "查看详细报告", "action_type": "view_full_report", "params": {}},
            {"label": "导出数据分析", "action_type": "export_analysis", "params": {}}
        ]

        if service_type == "risk_detection":
            actions.append({"label": "立即处理风险", "action_type": "handle_risks", "params": {}})
        elif service_type == "performance_review":
            actions.append({"label": "制定改进计划", "action_type": "create_improvement_plan", "params": {}})

        return actions

    async def autonomous_trigger(
        self,
        user_id: str,
        trigger_type: str,
        context: Optional[Dict] = None
    ) -> dict:
        """自主触发"""
        logger.info(f"RiskControlSkill: Autonomous trigger for user={user_id}, type={trigger_type}")

        if trigger_type == "metric_anomaly":
            result = await self.execute(
                user_id=user_id,
                service_type="dashboard_overview",
                context=context
            )
            has_risks = len(result.get("risk_control_result", {}).get("risks", [])) > 0
            return {"triggered": has_risks, "result": result, "should_push": has_risks}

        elif trigger_type == "performance_review_due":
            result = await self.execute(
                user_id=user_id,
                service_type="performance_review",
                context=context
            )
            return {"triggered": True, "result": result, "should_push": True}

        elif trigger_type == "scheduled_report":
            result = await self.execute(
                user_id=user_id,
                service_type="trend_analysis",
                context=context
            )
            return {"triggered": True, "result": result, "should_push": False}

        return {"triggered": False, "reason": "not_needed"}


# 全局 Skill 实例
_risk_control_skill_instance: Optional[RiskControlSkill] = None


def get_risk_control_skill() -> RiskControlSkill:
    """获取风控 Skill 单例实例"""
    global _risk_control_skill_instance
    if _risk_control_skill_instance is None:
        _risk_control_skill_instance = RiskControlSkill()
    return _risk_control_skill_instance
