"""
主动推送工作流

实现 AI 主动发现并推送高价值商机
"""
import logging
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AlertPushWorkflow:
    """
    主动推送工作流

    流程：
    1. 监控数据源变化
    2. 识别新信号
    3. 评估警报级别
    4. 执行推送动作
    """

    def __init__(self):
        self.workflow_id = f"alert_push_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.push_callbacks: List[Callable] = []

    def register_push_callback(self, callback: Callable):
        """
        注册推送回调

        Args:
            callback: 回调函数，签名为 callback(alert: Dict)
        """
        self.push_callbacks.append(callback)
        logger.info(f"Registered push callback: {callback.__name__}")

    async def run(
        self,
        keywords: Optional[List[str]] = None,
        industries: Optional[List[str]] = None,
        confidence_threshold: float = 0.7,
        value_threshold: float = 1000000
    ) -> Dict[str, Any]:
        """
        执行主动推送工作流

        Args:
            keywords: 监控关键词
            industries: 监控行业
            confidence_threshold: 置信度阈值
            value_threshold: 价值阈值

        Returns:
            推送结果汇总
        """
        logger.info(f"Starting alert push workflow: {self.workflow_id}")

        # Step 1: 发现新机会
        discovery_result = await self._step_discover_new_opportunities(
            keywords, industries, 7  # 最近 7 天
        )

        # Step 2: 筛选高价值机会
        filtered_result = await self._step_filter_high_value(
            discovery_result,
            confidence_threshold,
            value_threshold
        )

        # Step 3: 评估警报级别
        alert_result = await self._step_evaluate_alerts(filtered_result)

        # Step 4: 执行推送
        push_result = await self._step_execute_push(alert_result)

        return {
            "workflow_id": self.workflow_id,
            "status": "completed",
            "opportunities_discovered": discovery_result.get("count", 0),
            "opportunities_filtered": filtered_result.get("count", 0),
            "alerts_generated": alert_result.get("count", 0),
            "alerts_pushed": push_result.get("pushed_count", 0),
            "timestamp": datetime.now().isoformat()
        }

    async def _step_discover_new_opportunities(
        self,
        keywords: Optional[List[str]],
        industries: Optional[List[str]],
        days: int
    ) -> Dict[str, Any]:
        """Step 1: 发现新机会"""
        from tools import get_all_tools
        tools_map = {t["name"]: t for t in get_all_tools()}

        discover_tool = tools_map.get("discover_opportunities")
        if not discover_tool:
            return {"opportunities": [], "count": 0}

        all_opportunities = []

        # 基于关键词发现
        if keywords:
            import inspect
            if inspect.iscoroutinefunction(discover_tool["handler"]):
                result = await discover_tool["handler"](keywords=keywords, days=days)
            else:
                result = discover_tool["handler"](keywords=keywords, days=days)
            all_opportunities.extend(result.get("opportunities", []))

        # 基于行业发现
        if industries:
            for industry in industries:
                if inspect.iscoroutinefunction(discover_tool["handler"]):
                    result = await discover_tool["handler"](industry=industry, days=days)
                else:
                    result = discover_tool["handler"](industry=industry, days=days)
                all_opportunities.extend(result.get("opportunities", []))

        # 去重
        seen_ids = set()
        unique_opps = []
        for opp in all_opportunities:
            opp_id = opp.get("id")
            if opp_id and opp_id not in seen_ids:
                seen_ids.add(opp_id)
                unique_opps.append(opp)

        return {"opportunities": unique_opps, "count": len(unique_opps)}

    async def _step_filter_high_value(
        self,
        discovery_result: Dict[str, Any],
        confidence_threshold: float,
        value_threshold: float
    ) -> Dict[str, Any]:
        """Step 2: 筛选高价值机会"""
        opportunities = discovery_result.get("opportunities", [])

        filtered = []
        for opp in opportunities:
            confidence = opp.get("confidence_score", 0)
            value = opp.get("potential_value", 0)

            if confidence >= confidence_threshold or value >= value_threshold:
                filtered.append({
                    **opp,
                    "filter_reason": self._get_filter_reason(confidence, value, confidence_threshold, value_threshold)
                })

        return {"opportunities": filtered, "count": len(filtered)}

    def _get_filter_reason(
        self,
        confidence: float,
        value: float,
        confidence_threshold: float,
        value_threshold: float
    ) -> str:
        """获取筛选原因"""
        reasons = []
        if confidence >= confidence_threshold:
            reasons.append(f"高置信度 ({confidence:.1%})")
        if value >= value_threshold:
            reasons.append(f"高价值 ({value:,})")
        return ", ".join(reasons)

    async def _step_evaluate_alerts(self, filtered_result: Dict[str, Any]) -> Dict[str, Any]:
        """Step 3: 评估警报级别"""
        opportunities = filtered_result.get("opportunities", [])

        alerts = []
        for opp in opportunities:
            confidence = opp.get("confidence_score", 0)
            value = opp.get("potential_value", 0)

            # 评估警报级别
            if confidence >= 0.9 and value >= 10000000:
                priority = "critical"
                alert_type = "high_value_critical"
            elif confidence >= 0.8 or value >= 5000000:
                priority = "high"
                alert_type = "high_value"
            elif confidence >= 0.7:
                priority = "medium"
                alert_type = "new_opportunity"
            else:
                priority = "low"
                alert_type = "info"

            alerts.append({
                "alert_id": f"alert_{opp.get('id', 'unknown')}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "alert_type": alert_type,
                "priority": priority,
                "opportunity": opp,
                "message": self._generate_alert_message(opp, alert_type, priority)
            })

        return {"alerts": alerts, "count": len(alerts)}

    def _generate_alert_message(self, opp: Dict, alert_type: str, priority: str) -> str:
        """生成警报消息"""
        title = opp.get("title", "未知商机")
        confidence = opp.get("confidence_score", 0)
        value = opp.get("potential_value", 0)

        prefix_map = {
            "critical": "[紧急]",
            "high": "[重要]",
            "medium": "[通知]",
            "low": "[信息]"
        }

        prefix = prefix_map.get(priority, "[通知]")
        return f"{prefix} {title} - 置信度 {confidence:.1%}, 潜在价值 {value:,}"

    async def _step_execute_push(self, alert_result: Dict[str, Any]) -> Dict[str, Any]:
        """Step 4: 执行推送"""
        alerts = alert_result.get("alerts", [])
        pushed_count = 0

        for alert in alerts:
            # 调用所有注册的推送回调
            for callback in self.push_callbacks:
                try:
                    callback(alert)
                    pushed_count += 1
                except Exception as e:
                    logger.error(f"Push callback failed: {e}")

        return {
            "pushed_count": pushed_count,
            "total_alerts": len(alerts),
            "callbacks_invoked": len(self.push_callbacks)
        }


# 全局工作流实例
alert_push_workflow = AlertPushWorkflow
