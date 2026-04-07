"""
孵化器门户集成客户端
实现与统一门户的用户同步、权限验证、数据推送等功能
"""
from typing import Optional, Dict, Any
import httpx
from config import settings
from utils.logger import logger
import jwt
from datetime import datetime


class PortalIntegrationClient:
    """孵化器门户集成客户端"""

    def __init__(self):
        self.enabled = settings.portal_enabled
        self.api_url = settings.portal_api_url.rstrip('/') if settings.portal_api_url else ""
        self.api_key = settings.portal_api_key
        self.jwt_secret = settings.portal_jwt_secret
        self.client = httpx.AsyncClient(timeout=10.0) if self.enabled else None

    async def verify_portal_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证门户JWT令牌"""
        if not self.enabled or not self.jwt_secret:
            return None

        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            logger.info(f"Portal token verified for user: {payload.get('user_id')}")
            return payload
        except jwt.JWTError as e:
            logger.warning(f"Portal token verification failed: {str(e)}")
            return None

    async def sync_user_to_portal(self, user_data: Dict[str, Any]) -> bool:
        """同步用户数据到门户"""
        if not self.enabled or not self.api_url:
            return False

        try:
            response = await self.client.post(
                f"{self.api_url}/api/users/sync",
                headers={"X-API-Key": self.api_key},
                json={
                    "user_id": user_data["id"],
                    "name": user_data["name"],
                    "email": user_data["email"],
                    "avatar": user_data.get("avatar"),
                    "source": "matchmaker_agent",
                    "metadata": {
                        "age": user_data.get("age"),
                        "gender": user_data.get("gender"),
                        "location": user_data.get("location")
                    }
                }
            )
            response.raise_for_status()
            logger.info(f"User {user_data['id']} synced to portal successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to sync user to portal: {str(e)}")
            return False

    async def push_match_event(self, user_id: str, matched_user_id: str, score: float) -> bool:
        """推送匹配事件到门户"""
        if not self.enabled or not self.api_url:
            return False

        try:
            response = await self.client.post(
                f"{self.api_url}/api/events/match",
                headers={"X-API-Key": self.api_key},
                json={
                    "user_id": user_id,
                    "matched_user_id": matched_user_id,
                    "compatibility_score": score,
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "matchmaker_agent"
                }
            )
            response.raise_for_status()
            logger.debug(f"Match event pushed to portal: {user_id} <-> {matched_user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to push match event to portal: {str(e)}")
            return False

    async def get_portal_user_info(self, portal_user_id: str) -> Optional[Dict[str, Any]]:
        """从门户获取用户信息"""
        if not self.enabled or not self.api_url:
            return None

        try:
            response = await self.client.get(
                f"{self.api_url}/api/users/{portal_user_id}",
                headers={"X-API-Key": self.api_key}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get user info from portal: {str(e)}")
            return None

    async def close(self):
        """关闭HTTP客户端"""
        if self.client:
            await self.client.aclose()


# 全局门户客户端实例
portal_client = PortalIntegrationClient()
