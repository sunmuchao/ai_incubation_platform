"""
极光推送 API 客户端

提供移动端推送通知功能
文档：https://docs.jiguang.cn/jpush/server/push/server_overview/
"""
import httpx
import base64
from typing import Optional, List, Dict, Any
from config import settings
from utils.logger import logger


class JPushClient:
    """极光推送客户端"""

    # 推送 API 端点
    PUSH_URL = "https://api.jpush.cn/v3/push"
    VALIDATE_URL = "https://api.jpush.cn/v3/push/validate"

    def __init__(self):
        self.app_key = settings.jpush_app_key
        self.master_secret = settings.jpush_master_secret
        self.enabled = settings.jpush_enabled and bool(self.app_key) and bool(self.master_secret)

        if not self.enabled:
            logger.warning("JPushClient: JPUSH_ENABLED=false or credentials not set, using mock mode")

    def _get_auth_header(self) -> str:
        """获取认证头"""
        auth_str = f"{self.app_key}:{self.master_secret}"
        encoded = base64.b64encode(auth_str.encode()).decode()
        return f"Basic {encoded}"

    async def push(
        self,
        target: List[str],
        title: str,
        content: str,
        notification_type: str = "notification",
        extras: Optional[Dict[str, Any]] = None,
        platform: str = "all"
    ) -> Dict[str, Any]:
        """
        推送通知

        Args:
            target: 目标用户 ID 列表（registration_id 或 alias）
            title: 通知标题
            content: 通知内容
            notification_type: 通知类型（notification/alert）
            extras: 额外参数
            platform: 目标平台（all/ios/android）

        Returns:
            推送结果
        """
        if not self.enabled:
            # Mock 模式
            logger.info(f"JPush mock: Push to {len(target)} users - {title}: {content}")
            return {
                "success": True,
                "sendno": "mock_sendno",
                "msg_id": "mock_msg_id",
                "pushed_count": len(target),
                "status": "mock_delivered"
            }

        # 构建推送 payload
        payload = {
            "platform": platform,
            "audience": {
                "alias": target  # 使用 alias 推送给特定用户
            },
            "notification": {
                "alert": content,
                "android": {
                    "title": title,
                    "builder_id": 1
                },
                "ios": {
                    "alert": content,
                    "badge": "+1",
                    "sound": "default"
                }
            },
            "options": {
                "time_to_live": 86400,  # 24 小时
                "apns_production": False  # 开发环境
            }
        }

        # 添加额外参数
        if extras:
            payload["notification"]["android"]["extras"] = extras
            payload["notification"]["ios"]["extras"] = extras

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.PUSH_URL,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": self._get_auth_header()
                    }
                )
                response.raise_for_status()
                data = response.json()

                logger.info(f"JPush: Push sent to {len(target)} users, msg_id={data.get('msg_id')}")

                return {
                    "success": True,
                    "sendno": data.get("sendno"),
                    "msg_id": data.get("msg_id"),
                    "pushed_count": len(target)
                }

        except httpx.HTTPError as e:
            logger.error(f"JPush HTTP error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"JPush request failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def push_to_all(
        self,
        title: str,
        content: str,
        extras: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        推送给所有用户

        Args:
            title: 通知标题
            content: 通知内容
            extras: 额外参数

        Returns:
            推送结果
        """
        if not self.enabled:
            logger.info(f"JPush mock: Broadcast - {title}: {content}")
            return {
                "success": True,
                "status": "mock_broadcast"
            }

        payload = {
            "platform": "all",
            "audience": "all",
            "notification": {
                "alert": content,
                "android": {
                    "title": title
                },
                "ios": {
                    "alert": content,
                    "badge": "+1"
                }
            }
        }

        if extras:
            payload["notification"]["android"]["extras"] = extras
            payload["notification"]["ios"]["extras"] = extras

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.PUSH_URL,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": self._get_auth_header()
                    }
                )
                response.raise_for_status()
                data = response.json()

                logger.info(f"JPush: Broadcast sent, msg_id={data.get('msg_id')}")

                return {
                    "success": True,
                    "msg_id": data.get("msg_id")
                }

        except Exception as e:
            logger.error(f"JPush broadcast failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def push_sms(
        self,
        mobile: str,
        template_id: int,
        params: List[str]
    ) -> Dict[str, Any]:
        """
        发送短信（极光验证码短信）

        Args:
            mobile: 手机号
            template_id: 模板 ID
            params: 模板参数

        Returns:
            发送结果
        """
        if not self.enabled:
            logger.info(f"JPush mock SMS: {mobile}, template={template_id}")
            return {
                "success": True,
                "msg_id": "mock_sms_id"
            }

        # 注意：实际使用时需要配置短信模板
        payload = {
            "mobile": mobile,
            "template_id": template_id,
            "vars": params
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.jpush.cn/v3/validcodes",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": self._get_auth_header()
                    }
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "success": True,
                    "msg_id": data.get("msg_id")
                }

        except Exception as e:
            logger.error(f"JPush SMS failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# 全局客户端实例
_jpush_client: Optional[JPushClient] = None


def get_jpush_client() -> JPushClient:
    """获取极光推送客户端单例"""
    global _jpush_client
    if _jpush_client is None:
        _jpush_client = JPushClient()
    return _jpush_client
