"""
高德地图 API 客户端

提供地理编码、距离计算、地点搜索等功能
文档：https://lbs.amap.com/api/webservice/guide/create-project/get-key
"""
import httpx
import hashlib
import time
from typing import Optional, List, Dict, Any
from config import settings
from utils.logger import logger


class AMapClient:
    """高德地图 API 客户端"""

    # Web API 端点
    GEOCODING_URL = "https://restapi.amap.com/v3/geocode/geo"
    REVERSE_GEOCODING_URL = "https://restapi.amap.com/v3/geocode/regeo"
    DISTANCE_URL = "https://restapi.amap.com/v3/distance"
    SEARCH_URL = "https://restapi.amap.com/v3/place/text"
    DIRECTION_URL = "https://restapi.amap.com/v3/direction/walking"

    def __init__(self):
        self.api_key = settings.amap_api_key
        self.enabled = settings.amap_enabled and bool(self.api_key)

        if not self.enabled:
            logger.warning("AMapClient: AMAP_ENABLED=false or AMAP_API_KEY not set, using mock mode")

    def _sign_request(self, params: Dict[str, str]) -> Dict[str, str]:
        """添加签名参数（如果使用安全密钥）"""
        if settings.amap_api_secret:
            # 按 key 的 ASCII 码排序
            sorted_params = sorted(params.items())
            param_str = "&".join(f"{k}={v}" for k, v in sorted_params)
            # 添加安全密钥
            param_str += settings.amap_api_secret
            # 计算 SHA1 签名
            signature = hashlib.sha1(param_str.encode()).hexdigest()
            params["sig"] = signature

        params["key"] = self.api_key
        return params

    async def _request(self, url: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """发送 HTTP 请求"""
        # 转换参数为字符串
        str_params = {k: str(v) for k, v in params.items()}
        str_params = self._sign_request(str_params)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=str_params)
                response.raise_for_status()
                data = response.json()

                # 检查返回状态
                if data.get("status") == "1":
                    return data
                else:
                    logger.error(f"AMap API error: {data.get('info', 'Unknown error')}")
                    return None

        except httpx.HTTPError as e:
            logger.error(f"AMap HTTP error: {e}")
            return None
        except Exception as e:
            logger.error(f"AMap request failed: {e}")
            return None

    async def geocode(self, address: str, city: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        地理编码：地址转坐标

        Args:
            address: 地址
            city: 城市名

        Returns:
            {"location": "116.481493,39.990454", "formatted_address": "..."}
        """
        if not self.enabled:
            # Mock 模式：返回北京中心点
            logger.info(f"AMap mock geocode: {address}")
            return {
                "location": "116.397428,39.90923",
                "formatted_address": f"北京市（模拟）{address}"
            }

        params = {
            "address": address,
            "output": "json"
        }
        if city:
            params["city"] = city

        result = await self._request(self.GEOCODING_URL, params)

        if result and result.get("geocodes"):
            geocode = result["geocodes"][0]
            return {
                "location": geocode.get("location"),
                "formatted_address": geocode.get("formatted_address"),
                "province": geocode.get("province"),
                "city": geocode.get("city"),
                "district": geocode.get("district")
            }

        return None

    async def reverse_geocode(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """
        逆地理编码：坐标转地址

        Args:
            latitude: 纬度
            longitude: 经度

        Returns:
            {"formatted_address": "...", "city": "..."}
        """
        if not self.enabled:
            # Mock 模式
            logger.info(f"AMap mock reverse geocode: {latitude},{longitude}")
            return {
                "formatted_address": "北京市朝阳区（模拟）",
                "city": "北京市",
                "district": "朝阳区"
            }

        params = {
            "location": f"{longitude},{latitude}",
            "output": "json"
        }

        result = await self._request(self.REVERSE_GEOCODING_URL, params)

        if result and result.get("regeocode"):
            regeo = result["regeocode"]
            return {
                "formatted_address": regeo.get("formatted_address"),
                "city": regeo.get("addressComponent", {}).get("city"),
                "district": regeo.get("addressComponent", {}).get("district"),
                "street": regeo.get("addressComponent", {}).get("street")
            }

        return None

    async def calculate_distance(
        self,
        origin: str,
        destination: str,
        mode: str = "walking"
    ) -> Optional[Dict[str, Any]]:
        """
        距离计算

        Args:
            origin: 起点坐标（经度，纬度）
            destination: 终点坐标（经度，纬度）
            mode: 距离计算类型（walking: 步行，driving: 驾车）

        Returns:
            {"distance": "1234", "duration": "567"}
        """
        if not self.enabled:
            # Mock 模式：简单估算
            logger.info(f"AMap mock distance: {origin} -> {destination}")
            return {
                "distance": "1000",
                "duration": "300"
            }

        params = {
            "origins": origin,
            "destination": destination,
            "type": mode
        }

        result = await self._request(self.DISTANCE_URL, params)

        if result and result.get("results"):
            dist_result = result["results"][0]
            return {
                "distance": dist_result.get("distance"),  # 单位：米
                "duration": dist_result.get("duration"),  # 单位：秒
                "origin": dist_result.get("origin"),
                "destination": dist_result.get("destination")
            }

        return None

    async def search_places(
        self,
        keywords: str,
        city: Optional[str] = None,
        location: Optional[str] = None,
        radius: int = 1000,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        地点搜索

        Args:
            keywords: 搜索关键词
            city: 城市名
            location: 中心点坐标（经度，纬度）
            radius: 搜索半径（米）
            limit: 返回数量

        Returns:
            地点列表
        """
        if not self.enabled:
            # Mock 模式
            logger.info(f"AMap mock search: {keywords} in {city or 'unknown city'}")
            return self._mock_places(keywords, city)

        params = {
            "keywords": keywords,
            "radius": radius,
            "limit": limit,
            "output": "json"
        }
        if city:
            params["city"] = city
        if location:
            params["location"] = location
            params["radius"] = radius

        result = await self._request(self.SEARCH_URL, params)

        if result and result.get("pois"):
            return [
                {
                    "id": poi.get("id"),
                    "name": poi.get("name"),
                    "address": poi.get("address"),
                    "location": poi.get("location"),
                    "type": poi.get("type"),
                    "tel": poi.get("tel"),
                    "rating": poi.get("biz_ext", {}).get("rating") if poi.get("biz_ext") else None
                }
                for poi in result["pois"]
            ]

        return []

    def _mock_places(self, keywords: str, city: Optional[str] = None) -> List[Dict[str, Any]]:
        """Mock 地点搜索"""
        city_name = city or "某市"

        # 根据关键词返回模拟数据
        if "餐厅" in keywords or "餐饮" in keywords or keywords in ["美食", "吃饭"]:
            return [
                {"id": "mock_1", "name": f"{city_name}浪漫西餐厅", "address": f"{city_name}市中心商业街 1 号",
                 "location": "116.397428,39.90923", "type": "餐饮服务", "tel": "010-12345678", "rating": "4.8"},
                {"id": "mock_2", "name": f"{city_name}日式料理", "address": f"{city_name}朝阳区某某路 2 号",
                 "location": "116.407428,39.91923", "type": "餐饮服务", "tel": "010-87654321", "rating": "4.6"}
            ]
        elif "咖啡" in keywords:
            return [
                {"id": "mock_3", "name": f"{city_name}星巴克", "address": f"{city_name}市中心",
                 "location": "116.397428,39.90923", "type": "餐饮服务", "tel": "010-11223344", "rating": "4.5"}
            ]
        elif "电影" in keywords or "影院" in keywords:
            return [
                {"id": "mock_4", "name": f"{city_name}万达影城", "address": f"{city_name}市中心购物中心",
                 "location": "116.397428,39.90923", "type": "生活服务", "tel": "010-55667788", "rating": "4.7"}
            ]
        else:
            return [
                {"id": "mock_5", "name": f"{city_name}中心广场", "address": f"{city_name}市中心",
                 "location": "116.397428,39.90923", "type": "地名地址", "tel": "", "rating": ""}
            ]

    async def getwalking_direction(
        self,
        origin: str,
        destination: str
    ) -> Optional[Dict[str, Any]]:
        """
        步行路线规划

        Args:
            origin: 起点坐标（经度，纬度）
            destination: 终点坐标（经度，纬度）

        Returns:
            路线信息
        """
        if not self.enabled:
            # Mock 模式
            return {
                "distance": "1000",
                "duration": "300",
                "steps": ["从起点出发", "步行 300 米", "到达目的地"]
            }

        params = {
            "origin": origin,
            "destination": destination,
            "output": "json"
        }

        result = await self._request(self.DIRECTION_URL, params)

        if result and result.get("route"):
            route = result["route"]
            paths = route.get("paths", [])
            if paths:
                path = paths[0]
                return {
                    "distance": path.get("distance"),
                    "duration": path.get("duration"),
                    "steps": [
                        step.get("instruction")
                        for step in path.get("steps", [])
                    ]
                }

        return None


# 全局客户端实例
_amap_client: Optional[AMapClient] = None


def get_amap_client() -> AMapClient:
    """获取高德地图客户端单例"""
    global _amap_client
    if _amap_client is None:
        _amap_client = AMapClient()
    return _amap_client
