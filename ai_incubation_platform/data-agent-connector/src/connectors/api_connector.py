"""
REST API 连接器
"""
from typing import Any, Dict, List, Optional
import aiohttp
from connectors.base import BaseConnector, ConnectorConfig, ConnectorError


class RESTAPIConnector(BaseConnector):
    """REST API 连接器"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
        self._base_url = config.connection_string.rstrip('/')

    async def connect(self) -> None:
        """建立 HTTP 会话"""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
        self._connected = True

    async def disconnect(self) -> None:
        """关闭 HTTP 会话"""
        if self._session:
            await self._session.close()
        self._connected = False

    async def execute(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """
        执行 HTTP 请求
        query 格式：METHOD /path (e.g., "GET /users", "POST /data")
        """
        if not self._connected:
            raise ConnectorError("Not connected")

        parts = query.split(' ', 1)
        method = parts[0].upper()
        path = parts[1] if len(parts) > 1 else '/'

        url = f"{self._base_url}{path}"

        try:
            async with self._session.request(
                method, url,
                json=params.get('body') if params else None,
                params=params.get('query') if params else None
            ) as response:
                if response.status >= 400:
                    raise ConnectorError(f"HTTP {response.status}")
                return await response.json()
        except Exception as e:
            raise ConnectorError(f"Request failed: {e}")

    async def get_schema(self) -> Dict[str, Any]:
        """获取 API 端点信息（简化版）"""
        return {"endpoints": ["GET /", "GET /health"]}
