"""
推送服务

实现主动推送功能，支持：
- 警报生成和推送
- 推送渠道管理
- 推送历史记录
"""
import logging
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
import json
import os

logger = logging.getLogger(__name__)


class PushService:
    """
    推送服务

    负责管理和执行各种推送通知
    """

    def __init__(self):
        self.push_channels = {}
        self.alert_history = []
        self.subscribers = []
        self._init_default_channels()

    def _init_default_channels(self):
        """初始化默认推送渠道"""
        # 默认渠道：控制台日志
        self.register_channel("console", self._console_push)

        # 如果配置了 webhook，添加 webhook 渠道
        webhook_url = os.getenv("PUSH_WEBHOOK_URL")
        if webhook_url:
            self.register_channel("webhook", self._webhook_push)

    def register_channel(self, name: str, handler: Callable):
        """
        注册推送渠道

        Args:
            name: 渠道名称
            handler: 推送处理函数
        """
        self.push_channels[name] = handler
        logger.info(f"Registered push channel: {name}")

    def subscribe(self, callback: Callable, channels: List[str] = None):
        """
        订阅推送

        Args:
            callback: 回调函数
            channels: 订阅的渠道列表，None 表示所有渠道
        """
        self.subscribers.append({
            "callback": callback,
            "channels": channels or list(self.push_channels.keys())
        })
        logger.info(f"New subscriber with channels: {channels or 'all'}")

    async def send_alert(
        self,
        alert_type: str,
        data: Dict[str, Any],
        priority: str = "medium",
        title: str = None,
        message: str = None
    ) -> Dict[str, Any]:
        """
        发送警报

        Args:
            alert_type: 警报类型
            data: 警报数据
            priority: 优先级 (low, medium, high, critical)
            title: 警报标题
            message: 警报消息

        Returns:
            推送结果
        """
        alert = {
            "alert_id": f"alert_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "alert_type": alert_type,
            "priority": priority,
            "title": title or alert_type,
            "message": message or "",
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        }

        # 推送到所有渠道
        push_results = {}
        for channel_name, channel_handler in self.push_channels.items():
            try:
                result = await channel_handler(alert)
                push_results[channel_name] = {
                    "success": True,
                    "result": result
                }
            except Exception as e:
                logger.error(f"Push to {channel_name} failed: {e}")
                push_results[channel_name] = {
                    "success": False,
                    "error": str(e)
                }

        # 通知订阅者
        for subscriber in self.subscribers:
            for channel in subscriber["channels"]:
                if channel in self.push_channels:
                    try:
                        subscriber["callback"](alert, channel)
                    except Exception as e:
                        logger.error(f"Subscriber callback failed: {e}")

        # 记录历史
        alert["status"] = "sent"
        alert["push_results"] = push_results
        self.alert_history.append(alert)

        # 限制历史记录大小
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-500:]

        logger.info(f"Alert sent: {alert['alert_id']} - {alert['title']}")
        return {
            "alert_id": alert["alert_id"],
            "status": "sent",
            "channels": push_results
        }

    async def _console_push(self, alert: Dict) -> Dict:
        """控制台推送（日志）"""
        priority_emoji = {
            "critical": "[紧急]",
            "high": "[重要]",
            "medium": "[通知]",
            "low": "[信息]"
        }
        emoji = priority_emoji.get(alert["priority"], "[通知]")
        logger.info(f"{emoji} {alert['title']}: {alert['message']}")
        return {"logged": True}

    async def _webhook_push(self, alert: Dict) -> Dict:
        """Webhook 推送"""
        webhook_url = os.getenv("PUSH_WEBHOOK_URL")
        if not webhook_url:
            return {"skipped": True, "reason": "No webhook URL configured"}

        try:
            import requests
            response = requests.post(
                webhook_url,
                json=alert,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            return {
                "status_code": response.status_code,
                "response": response.text[:200] if response.text else ""
            }
        except Exception as e:
            return {"error": str(e)}

    def get_alert_history(
        self,
        alert_type: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        获取警报历史

        Args:
            alert_type: 按类型筛选
            priority: 按优先级筛选
            limit: 返回数量限制

        Returns:
            警报历史列表
        """
        filtered = self.alert_history

        if alert_type:
            filtered = [a for a in filtered if a.get("alert_type") == alert_type]
        if priority:
            filtered = [a for a in filtered if a.get("priority") == priority]

        return filtered[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """获取推送统计"""
        stats = {
            "total_alerts": len(self.alert_history),
            "channels": list(self.push_channels.keys()),
            "subscribers": len(self.subscribers),
            "by_priority": {},
            "by_type": {}
        }

        for alert in self.alert_history:
            priority = alert.get("priority", "unknown")
            alert_type = alert.get("alert_type", "unknown")

            stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1
            stats["by_type"][alert_type] = stats["by_type"].get(alert_type, 0) + 1

        return stats


# 全局推送服务实例
push_service = PushService()


def get_push_service() -> PushService:
    """获取全局推送服务实例"""
    return push_service
