"""
门户集成客户端

提供与外部门户系统的集成能力：
- 用户同步
- 令牌验证
- 匹配事件推送
- 用户信息获取

降级方案：
- 禁用时所有操作返回默认值（None/False）
- 异常时自动降级，不阻塞主流程
"""
from typing import Optional, Dict, Any
import jwt
from datetime import datetime, timedelta
from config import settings
from utils.logger import logger
import httpx


class PortalIntegrationClient:
    """门户集成客户端"""

    def __init__(self):
        self.enabled = settings.portal_enabled
        self.api_url = settings.portal_api_url.rstrip('/') if settings.portal_api_url else ""
        self.api_key = settings.portal_api_key
        self.jwt_secret = settings.portal_jwt_secret

        # HTTP 客户端
        self.client = None
        if self.enabled and self.api_url:
            self.client = httpx.AsyncClient(timeout=30.0)

        logger.info(f"Portal Client initialized: enabled={self.enabled}, api_url={self.api_url}")

    async def verify_portal_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证门户 JWT 令牌

        Args:
            token: JWT 令牌字符串

        Returns:
            解码后的 payload，验证失败返回 None
        """
        if not self.enabled:
            logger.debug("Portal integration disabled, skipping token verification")
            return None

        if not self.jwt_secret:
            logger.warning("Portal JWT secret not configured")
            return None

        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=["HS256"]
            )
            logger.debug(f"Portal token verified successfully for user: {payload.get('user_id')}")
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Portal token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Portal token verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during token verification: {e}")
            return None

    async def sync_user_to_portal(self, user_data: Dict[str, Any]) -> bool:
        """
        同步用户数据到门户系统

        Args:
            user_data: 用户数据字典

        Returns:
            同步成功返回 True，失败返回 False
        """
        if not self.enabled:
            logger.debug("Portal integration disabled, skipping user sync")
            return False

        if not self.api_url:
            logger.warning("Portal API URL not configured")
            return False

        if not self.client:
            logger.warning("Portal client not initialized")
            return False

        try:
            headers = {
                "X-API-Key": self.api_key,
                "Content-Type": "application/json"
            }

            response = await self.client.post(
                f"{self.api_url}/api/users/sync",
                headers=headers,
                json=user_data
            )
            response.raise_for_status()

            logger.info(f"User synced to portal successfully: {user_data.get('id')}")
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Portal sync failed with status {e.response.status_code}: {e}")
            return False
        except Exception as e:
            logger.error(f"Portal sync failed with exception: {e}")
            return False

    async def push_match_event(
        self,
        user_a_id: str,
        user_b_id: str,
        compatibility_score: float
    ) -> bool:
        """
        推送匹配事件到门户系统

        Args:
            user_a_id: 用户 A ID
            user_b_id: 用户 B ID
            compatibility_score: 匹配度分数

        Returns:
            推送成功返回 True，失败返回 False
        """
        if not self.enabled:
            logger.debug("Portal integration disabled, skipping match event push")
            return False

        if not self.api_url:
            logger.warning("Portal API URL not configured")
            return False

        if not self.client:
            logger.warning("Portal client not initialized")
            return False

        try:
            headers = {
                "X-API-Key": self.api_key,
                "Content-Type": "application/json"
            }

            payload = {
                "user_a_id": user_a_id,
                "user_b_id": user_b_id,
                "compatibility_score": compatibility_score,
                "event_type": "match_created",
                "timestamp": datetime.utcnow().isoformat()
            }

            response = await self.client.post(
                f"{self.api_url}/api/events/match",
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            logger.info(f"Match event pushed to portal: {user_a_id} <-> {user_b_id}")
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Portal match event push failed with status {e.response.status_code}: {e}")
            return False
        except Exception as e:
            logger.error(f"Portal match event push failed with exception: {e}")
            return False

    async def get_portal_user_info(self, portal_user_id: str) -> Optional[Dict[str, Any]]:
        """
        从门户系统获取用户信息

        Args:
            portal_user_id: 门户用户 ID

        Returns:
            用户信息字典，失败返回 None
        """
        if not self.enabled:
            logger.debug("Portal integration disabled, skipping user info fetch")
            return None

        if not self.api_url:
            logger.warning("Portal API URL not configured")
            return None

        if not self.client:
            logger.warning("Portal client not initialized")
            return None

        try:
            headers = {
                "X-API-Key": self.api_key,
                "Content-Type": "application/json"
            }

            response = await self.client.get(
                f"{self.api_url}/api/users/{portal_user_id}",
                headers=headers
            )
            response.raise_for_status()

            user_info = response.json()
            logger.debug(f"Portal user info fetched: {portal_user_id}")
            return user_info

        except httpx.HTTPStatusError as e:
            logger.error(f"Portal user info fetch failed with status {e.response.status_code}: {e}")
            return None
        except Exception as e:
            logger.error(f"Portal user info fetch failed with exception: {e}")
            return None

    async def close(self):
        """关闭 HTTP 客户端"""
        if self.client:
            await self.client.aclose()
            logger.debug("Portal client closed")


# 全局门户客户端实例
portal_client = PortalIntegrationClient()