"""
HTTP客户端工具
"""
import httpx
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

class HttpClient:
    """HTTP客户端封装"""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)

    async def async_get(self, url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict[str, Any]:
        """异步GET请求"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"GET request failed: {url}, error: {str(e)}")
                raise

    def get(self, url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict[str, Any]:
        """同步GET请求"""
        try:
            response = self.client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"GET request failed: {url}, error: {str(e)}")
            raise

    async def async_post(self, url: str, json: Dict, headers: Optional[Dict] = None) -> Dict[str, Any]:
        """异步POST请求"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=json, headers=headers)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"POST request failed: {url}, error: {str(e)}")
                raise

    def post(self, url: str, json: Dict, headers: Optional[Dict] = None) -> Dict[str, Any]:
        """同步POST请求"""
        try:
            response = self.client.post(url, json=json, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"POST request failed: {url}, error: {str(e)}")
            raise

http_client = HttpClient()
