"""
活动推荐服务 - P3

基于地图 API 的地点推荐优化：
- 接入高德/百度地图 API
- 基于用户位置的附近推荐
- 约会地点智能推荐
- 地点收藏和管理

注意：生产环境需要配置地图 API 密钥
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json
import math
import os
from sqlalchemy.orm import Session
from utils.db_session_manager import db_session, db_session_readonly
from db.database import SessionLocal
from db.models import SavedLocationDB, UserDB
from utils.logger import logger


# 预定义地点类型
LOCATION_TYPES = {
    "cafe": {"label": "咖啡厅", "keywords": ["咖啡", "cafe", "starbucks", "瑞幸"]},
    "restaurant": {"label": "餐厅", "keywords": ["餐厅", "饭店", "美食", "料理"]},
    "park": {"label": "公园", "keywords": ["公园", "绿地", "广场", "江边"]},
    "cinema": {"label": "电影院", "keywords": ["电影", "影院", "IMAX", "影城"]},
    "activity": {"label": "活动", "keywords": ["展览", "演出", "音乐会", "话剧", "展览"]},
    "museum": {"label": "博物馆", "keywords": ["博物馆", "美术馆", "展览", "画廊"]},
    "sports": {"label": "运动", "keywords": ["健身房", "游泳", "网球", "羽毛球", "攀岩"]},
    "bar": {"label": "酒吧", "keywords": ["酒吧", "清吧", "pub", "lounge"]}
}


class GeoService:
    """地理服务（不依赖外部 API 的基础功能）"""

    # 城市坐标（简化版）
    CITY_COORDINATES = {
        "北京": (39.9042, 116.4074),
        "上海": (31.2304, 106.1954),
        "广州": (23.1291, 113.2644),
        "深圳": (22.5431, 114.0579),
        "杭州": (30.2741, 120.1551),
        "成都": (30.5728, 104.0668),
        "武汉": (30.5928, 114.3055),
        "西安": (34.3416, 108.9398)
    }

    @staticmethod
    def calculate_distance(location1: str, location2: str) -> Optional[float]:
        """
        计算两个地点之间的距离（简化版）

        Args:
            location1: 地点 1
            location2: 地点 2

        Returns:
            距离（公里），无法计算返回 None
        """
        # 尝试从城市名获取坐标
        coords1 = GeoService._get_coordinates(location1)
        coords2 = GeoService._get_coordinates(location2)

        if not coords1 or not coords2:
            return None

        # Haversine 公式计算距离
        lat1, lon1 = coords1
        lat2, lon2 = coords2

        R = 6371  # 地球半径（公里）
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (
            math.sin(dlat / 2) ** 2 +
            math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
            math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    @staticmethod
    def _get_coordinates(location: str) -> Optional[Tuple[float, float]]:
        """获取地点坐标"""
        # 检查是否是完整坐标
        if "," in location:
            try:
                parts = location.split(",")
                return (float(parts[0]), float(parts[1]))
            except (ValueError, IndexError):
                pass

        # 尝试匹配城市
        for city, coords in GeoService.CITY_COORDINATES.items():
            if city in location:
                return coords

        return None


class MapAPIService:
    """地图 API 服务（支持高德/百度）"""

    def __init__(self):
        self._api_key = os.getenv("MAP_API_KEY")
        self._api_provider = os.getenv("MAP_API_PROVIDER", "amap")  # amap 或 baidu
        self._enabled = self._api_key is not None

    def search_nearby(
        self,
        latitude: float,
        longitude: float,
        keyword: str = "咖啡厅",
        radius: int = 3000,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索附近地点

        Args:
            latitude: 纬度
            longitude: 经度
            keyword: 搜索关键词
            radius: 搜索半径（米）
            limit: 返回数量

        Returns:
            地点列表
        """
        if not self._enabled:
            logger.warning("Map API not configured, returning mock results")
            return self._mock_search(latitude, longitude, keyword, radius, limit)

        try:
            if self._api_provider == "amap":
                return self._search_amap(latitude, longitude, keyword, radius, limit)
            else:
                return self._search_baidu(latitude, longitude, keyword, radius, limit)
        except Exception as e:
            logger.error(f"Map API search error: {e}")
            return self._mock_search(latitude, longitude, keyword, radius, limit)

    def _search_amap(
        self,
        latitude: float,
        longitude: float,
        keyword: str,
        radius: int,
        limit: int
    ) -> List[Dict[str, Any]]:
        """高德地图搜索"""
        import requests

        url = "https://restapi.amap.com/v3/place/text"
        params = {
            "key": self._api_key,
            "location": f"{longitude},{latitude}",
            "keywords": keyword,
            "radius": radius,
            "limit": limit,
            "output": "json"
        }

        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if data.get("status") == "1":
            return [
                {
                    "name": poi["name"],
                    "address": poi.get("address", ""),
                    "latitude": float(poi.get("latitude", 0)),
                    "longitude": float(poi.get("longitude", 0)),
                    "type": poi.get("type", ""),
                    "rating": float(poi.get("biz_ext", {}).get("rating", 0)),
                    "price_level": self._parse_price_level(poi.get("biz_ext", {}).get("cost", ""))
                }
                for poi in data.get("pois", [])
            ]
        return []

    def _search_baidu(
        self,
        latitude: float,
        longitude: float,
        keyword: str,
        radius: int,
        limit: int
    ) -> List[Dict[str, Any]]:
        """百度地图搜索"""
        import requests

        url = "https://api.map.baidu.com/place/v2/search"
        params = {
            "query": keyword,
            "location": f"{latitude},{longitude}",
            "radius": radius,
            "page_size": limit,
            "ak": self._api_key,
            "output": "json"
        }

        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if data.get("status") == 0:
            return [
                {
                    "name": r["name"],
                    "address": r.get("address", ""),
                    "latitude": r["location"]["lat"],
                    "longitude": r["location"]["lng"],
                    "rating": float(r.get("detail_info", {}).get("overall_rating", 0)),
                    "price_level": r.get("detail_info", {}).get("price", 0)
                }
                for r in data.get("results", [])
            ]
        return []

    def _mock_search(
        self,
        latitude: float,
        longitude: float,
        keyword: str,
        radius: int,
        limit: int
    ) -> List[Dict[str, Any]]:
        """模拟搜索结果（用于测试）"""
        import random

        base_places = [
            {"name": "星巴克咖啡", "type": "cafe", "rating": 4.5, "price": 2},
            {"name": "漫咖啡", "type": "cafe", "rating": 4.3, "price": 2},
            {"name": "海底捞火锅", "type": "restaurant", "rating": 4.6, "price": 3},
            {"name": "外婆家", "type": "restaurant", "rating": 4.2, "price": 1},
            {"name": "中央公园", "type": "park", "rating": 4.4, "price": 0},
            {"name": "万达影城", "type": "cinema", "rating": 4.3, "price": 2},
            {"name": "市博物馆", "type": "museum", "rating": 4.5, "price": 0},
            {"name": "健身工坊", "type": "sports", "rating": 4.2, "price": 2},
        ]

        results = []
        for i, place in enumerate(random.sample(base_places, min(limit, len(base_places)))):
            # 在基础坐标上加一点偏移
            results.append({
                "name": place["name"],
                "address": f"某街道{i + 1}号",
                "latitude": latitude + (i - 2) * 0.01,
                "longitude": longitude + (i - 2) * 0.01,
                "type": place["type"],
                "rating": place["rating"],
                "price_level": place["price"],
                "distance": round(random.uniform(0.5, 3.0), 2)
            })

        return results

    def _parse_price_level(self, cost_str: str) -> int:
        """解析价格等级"""
        try:
            cost = int(cost_str.replace("¥", ""))
            if cost < 50:
                return 1
            elif cost < 150:
                return 2
            elif cost < 300:
                return 3
            else:
                return 4
        except (ValueError, AttributeError):
            return 2  # 默认中等价位


class ActivityRecommendationService:
    """活动推荐服务"""

    def __init__(self) -> None:
        self.map_api = MapAPIService()
        self.geo_service = GeoService()

    def recommend_date_locations(
        self,
        user_id: str,
        target_user_id: Optional[str] = None,
        location_type: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        推荐约会地点

        Args:
            user_id: 用户 ID
            target_user_id: 对方用户 ID（可选，用于计算中间点）
            location_type: 地点类型（可选）
            limit: 返回数量

        Returns:
            推荐地点列表
        """
        with db_session_readonly() as db:
            # 获取用户位置
            user = db.query(UserDB).filter(UserDB.id == user_id).first()
            if not user:
                return {"error": "user_not_found", "locations": []}

            # 计算搜索中心点
            if target_user_id:
                target = db.query(UserDB).filter(UserDB.id == target_user_id).first()
                if target:
                    center_location = self._calculate_midpoint(user.location, target.location)
                else:
                    center_location = user.location
            else:
                center_location = user.location

            # 获取坐标
            coords = GeoService._get_coordinates(center_location)
            if not coords:
                # 使用默认坐标（北京）
                coords = (39.9042, 116.4074)

            latitude, longitude = coords

            # 确定搜索类型
            if location_type:
                types_to_search = [location_type]
            else:
                # 默认推荐多种类型
                types_to_search = ["cafe", "restaurant", "park", "activity"]

            all_locations = []
            for loc_type in types_to_search:
                type_info = LOCATION_TYPES.get(loc_type, {})
                keyword = type_info.get("label", "休闲")

                locations = self.map_api.search_nearby(
                    latitude, longitude,
                    keyword=keyword,
                    radius=3000,
                    limit=limit // len(types_to_search)
                )

                for loc in locations:
                    loc["location_type"] = loc_type
                    loc["source"] = "map_api"

                all_locations.extend(locations)

            # 按评分排序
            all_locations.sort(key=lambda x: x.get("rating", 0), reverse=True)

            return {
                "center_location": center_location,
                "coordinates": {"latitude": latitude, "longitude": longitude},
                "locations": all_locations[:limit],
                "total": len(all_locations)
            }

    def _calculate_midpoint(self, location1: str, location2: str) -> str:
        """计算两个地点的中间点"""
        coords1 = GeoService._get_coordinates(location1)
        coords2 = GeoService._get_coordinates(location2)

        if coords1 and coords2:
            mid_lat = (coords1[0] + coords2[0]) / 2
            mid_lon = (coords1[1] + coords2[1]) / 2
            return f"{mid_lat},{mid_lon}"

        return location1  # 无法计算时返回第一个地点

    def save_location(
        self,
        user_id: str,
        location_name: str,
        location_type: str,
        address: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        reason: Optional[str] = None,
        tags: Optional[List[str]] = None,
        rating: Optional[float] = None,
        price_level: Optional[int] = None
    ) -> str:
        """
        收藏地点

        Args:
            user_id: 用户 ID
            location_name: 地点名称
            location_type: 地点类型
            address: 地址
            latitude: 纬度
            longitude: 经度
            reason: 收藏理由
            tags: 标签
            rating: 评分
            price_level: 价格等级

        Returns:
            收藏 ID
        """
        location_id = str(__import__('uuid').uuid4())

        with db_session() as db:
            saved_location = SavedLocationDB(
                id=location_id,
                user_id=user_id,
                location_name=location_name,
                location_type=location_type,
                address=address,
                latitude=latitude,
                longitude=longitude,
                reason=reason,
                tags=json.dumps(tags or []),
                rating=rating,
                price_level=price_level,
                source="manual"
            )
            db.add(saved_location)
            # auto-commits

            logger.info(f"Saved location: {location_name} for user {user_id}")
            return location_id

    def get_saved_locations(
        self,
        user_id: str,
        location_type: Optional[str] = None,
        is_active: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取收藏的地点

        Args:
            user_id: 用户 ID
            location_type: 地点类型过滤
            is_active: 是否只获取有效地点

        Returns:
            地点列表
        """
        with db_session_readonly() as db:
            query = db.query(SavedLocationDB).filter(
                SavedLocationDB.user_id == user_id
            )

            if location_type:
                query = query.filter(SavedLocationDB.location_type == location_type)

            if is_active:
                query = query.filter(SavedLocationDB.is_active == True)

            locations = query.order_by(SavedLocationDB.created_at.desc()).all()

            return [
                {
                    "id": loc.id,
                    "name": loc.location_name,
                    "type": loc.location_type,
                    "address": loc.address,
                    "latitude": loc.latitude,
                    "longitude": loc.longitude,
                    "reason": loc.reason,
                    "tags": json.loads(loc.tags) if loc.tags else [],
                    "rating": loc.rating,
                    "price_level": loc.price_level,
                    "created_at": loc.created_at.isoformat()
                }
                for loc in locations
            ]

    def delete_saved_location(self, user_id: str, location_id: str) -> bool:
        """删除收藏的地点"""
        with db_session() as db:
            location = db.query(SavedLocationDB).filter(
                SavedLocationDB.id == location_id,
                SavedLocationDB.user_id == user_id
            ).first()

            if location:
                location.is_active = False
                # auto-commits
                return True
            return False

    def get_activity_recommendations(
        self,
        user_id: str,
        occasion: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取活动推荐

        Args:
            user_id: 用户 ID
            occasion: 场合（first_date, weekend, special）

        Returns:
            推荐列表
        """
        # 根据场合推荐不同类型的活动
        occasion_types = {
            "first_date": ["cafe", "park", "museum"],  # 第一次约会：轻松、可交流
            "weekend": ["activity", "restaurant", "cinema"],  # 周末：休闲娱乐
            "special": ["restaurant", "bar", "activity"],  # 特殊场合：高级餐厅、活动
            "casual": ["cafe", "park", "sports"]  #  casual：随意
        }

        types = occasion_types.get(occasion, ["cafe", "restaurant"])

        return self.recommend_date_locations(
            user_id=user_id,
            limit=15
        )


# 全局服务实例
activity_recommendation_service = ActivityRecommendationService()
