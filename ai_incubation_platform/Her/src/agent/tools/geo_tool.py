"""
地理位置服务工具

提供基于经纬度的距离计算和地理位置匹配功能。
参考 Tinder 的地理位置匹配机制，支持距离筛选和附近的人推荐。
"""
from typing import Dict, Any, List, Optional, Tuple
import math
from dataclasses import dataclass
from utils.logger import logger


@dataclass
class Location:
    """地理位置数据类"""
    latitude: float  # 纬度 (-90 to 90)
    longitude: float  # 经度 (-180 to 180)
    city: str = ""
    district: str = ""
    country: str = "China"


class GeoService:
    """
    地理位置服务

    功能：
    - Haversine 距离计算
    - 附近的人筛选
    - 距离范围查询
    - 地理位置编码/解码
    """

    # 地球半径（公里）
    EARTH_RADIUS_KM = 6371

    # 中国主要城市坐标
    CHINA_CITIES = {
        "北京": Location(39.9042, 116.4074, "北京", "", "China"),
        "上海": Location(31.2304, 121.4737, "上海", "", "China"),
        "广州": Location(23.1291, 113.2644, "广州", "广东", "China"),
        "深圳": Location(22.5431, 114.0579, "深圳", "广东", "China"),
        "成都": Location(30.5728, 104.0668, "成都", "四川", "China"),
        "杭州": Location(30.2741, 120.1551, "杭州", "浙江", "China"),
        "南京": Location(32.0603, 118.7969, "南京", "江苏", "China"),
        "武汉": Location(30.5928, 114.3055, "武汉", "湖北", "China"),
        "西安": Location(34.3416, 108.9398, "西安", "陕西", "China"),
        "重庆": Location(29.5630, 106.5516, "重庆", "", "China"),
        "天津": Location(39.3434, 117.3616, "天津", "", "China"),
        "苏州": Location(31.2989, 120.5853, "苏州", "江苏", "China"),
        "无锡": Location(31.4912, 120.3124, "无锡", "江苏", "China"),
        "厦门": Location(24.4798, 118.0894, "厦门", "福建", "China"),
        "长沙": Location(28.2282, 112.9388, "长沙", "湖南", "China"),
        "青岛": Location(36.0671, 120.3826, "青岛", "山东", "China"),
        "大连": Location(38.9140, 121.6147, "大连", "辽宁", "China"),
    }

    @staticmethod
    def haversine_distance(loc1: Location, loc2: Location) -> float:
        """
        使用 Haversine 公式计算两点间的大圆距离

        Args:
            loc1: 位置 1
            loc2: 位置 2

        Returns:
            距离（公里）
        """
        lat1_rad = math.radians(loc1.latitude)
        lat2_rad = math.radians(loc2.latitude)
        delta_lat = math.radians(loc2.latitude - loc1.latitude)
        delta_lon = math.radians(loc2.longitude - loc1.longitude)

        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return GeoService.EARTH_RADIUS_KM * c

    @staticmethod
    def calculate_distance(loc1_str: str, loc2_str: str) -> Optional[float]:
        """
        根据位置字符串计算距离

        Args:
            loc1_str: 位置 1 字符串（城市名或"城市，区"格式）
            loc2_str: 位置 2 字符串

        Returns:
            距离（公里），如果无法解析则返回 None
        """
        loc1 = GeoService.parse_location(loc1_str)
        loc2 = GeoService.parse_location(loc2_str)

        if loc1 is None or loc2 is None:
            return None

        return GeoService.haversine_distance(loc1, loc2)

    @staticmethod
    def parse_location(location_str: str) -> Optional[Location]:
        """
        解析位置字符串为 Location 对象

        Args:
            location_str: 位置字符串（如"北京市"、"上海"、"广州，天河"）

        Returns:
            Location 对象，如果无法解析则返回 None
        """
        if not location_str:
            return None

        # 清理字符串
        location_str = location_str.strip()

        # 尝试直接匹配城市
        for city, location in GeoService.CHINA_CITIES.items():
            if city in location_str or location_str in city:
                return location

        # 尝试解析"城市，区"格式
        if "，" in location_str:
            parts = location_str.split("，")
            city_part = parts[0]
            district_part = parts[1] if len(parts) > 1 else ""

            for city, location in GeoService.CHINA_CITIES.items():
                if city_part in city or city in city_part:
                    return Location(
                        latitude=location.latitude,
                        longitude=location.longitude,
                        city=city,
                        district=district_part,
                        country=location.country
                    )

        # 尝试提取城市关键字
        for city in GeoService.CHINA_CITIES.keys():
            if any(keyword in location_str for keyword in [city, city.replace("市", "")]):
                return GeoService.CHINA_CITIES[city]

        # 无法解析，返回 None
        logger.warning(f"GeoService: Unable to parse location: {location_str}")
        return None

    @staticmethod
    def is_within_range(user_location: str, target_location: str, max_distance_km: float) -> bool:
        """
        检查两个位置是否在指定距离范围内

        Args:
            user_location: 用户位置
            target_location: 目标位置
            max_distance_km: 最大距离（公里）

        Returns:
            是否在范围内
        """
        distance = GeoService.calculate_distance(user_location, target_location)
        if distance is None:
            return False
        return distance <= max_distance_km

    @staticmethod
    def get_location_display_name(location_str: str) -> str:
        """
        获取位置的显示名称

        Args:
            location_str: 位置字符串

        Returns:
            格式化的显示名称
        """
        location = GeoService.parse_location(location_str)
        if location:
            if location.district:
                return f"{location.city}{location.district}"
            return location.city
        return location_str


class GeoTool:
    """
    地理位置工具 - Agent 工具封装

    功能：
    - 计算两个用户之间的距离
    - 筛选指定范围内的用户
    - 获取位置信息
    """

    name = "geo_service"
    description = "提供地理位置相关的计算和查询服务"
    tags = ["geo", "location", "distance"]

    @staticmethod
    def get_input_schema() -> dict:
        """获取输入参数 JSONSchema"""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作类型",
                    "enum": ["calculate_distance", "check_range", "parse_location"]
                },
                "user_id": {
                    "type": "string",
                    "description": "用户 ID（用于 calculate_distance 和 check_range）"
                },
                "target_user_id": {
                    "type": "string",
                    "description": "目标用户 ID（用于 calculate_distance 和 check_range）"
                },
                "location_str": {
                    "type": "string",
                    "description": "位置字符串（用于 parse_location）"
                },
                "max_distance_km": {
                    "type": "number",
                    "description": "最大距离（公里），用于 check_range",
                    "default": 50
                }
            },
            "required": ["action"]
        }

    @staticmethod
    def handle(
        action: str,
        user_id: str = None,
        target_user_id: str = None,
        location_str: str = None,
        max_distance_km: float = 50
    ) -> dict:
        """
        处理地理位置相关请求

        Args:
            action: 操作类型
            user_id: 用户 ID
            target_user_id: 目标用户 ID
            location_str: 位置字符串
            max_distance_km: 最大距离

        Returns:
            操作结果
        """
        logger.info(f"GeoTool: Executing action={action}, user_id={user_id}, target_user_id={target_user_id}")

        try:
            if action == "parse_location":
                if not location_str:
                    return {"error": "location_str is required for parse_location action"}

                location = GeoService.parse_location(location_str)
                if location:
                    return {
                        "latitude": location.latitude,
                        "longitude": location.longitude,
                        "city": location.city,
                        "district": location.district,
                        "display_name": GeoService.get_location_display_name(location_str)
                    }
                else:
                    return {"error": f"Unable to parse location: {location_str}"}

            elif action == "calculate_distance":
                if not user_id or not target_user_id:
                    return {"error": "user_id and target_user_id are required"}

                from db.database import get_db
                from db.repositories import UserRepository

                db = next(get_db())
                user_repo = UserRepository(db)

                db_user = user_repo.get_by_id(user_id)
                db_target = user_repo.get_by_id(target_user_id)

                if not db_user or not db_target:
                    return {"error": "User not found"}

                distance = GeoService.calculate_distance(db_user.location, db_target.location)

                if distance is not None:
                    return {
                        "distance_km": round(distance, 2),
                        "user_location": db_user.location,
                        "target_location": db_target.location,
                        "is_nearby": distance < 10,
                        "display_message": GeoTool._generate_distance_message(distance)
                    }
                else:
                    return {
                        "distance_km": None,
                        "message": "无法解析位置信息"
                    }

            elif action == "check_range":
                if not user_id or not target_user_id:
                    return {"error": "user_id and target_user_id are required"}

                from db.database import get_db
                from db.repositories import UserRepository

                db = next(get_db())
                user_repo = UserRepository(db)

                db_user = user_repo.get_by_id(user_id)
                db_target = user_repo.get_by_id(target_user_id)

                if not db_user or not db_target:
                    return {"error": "User not found"}

                is_within = GeoService.is_within_range(
                    db_user.location,
                    db_target.location,
                    max_distance_km
                )

                distance = GeoService.calculate_distance(db_user.location, db_target.location)

                return {
                    "is_within_range": is_within,
                    "max_distance_km": max_distance_km,
                    "actual_distance_km": round(distance, 2) if distance else None,
                    "user_location": db_user.location,
                    "target_location": db_target.location
                }

            else:
                return {"error": f"Unknown action: {action}"}

        except Exception as e:
            logger.error(f"GeoTool: Failed to execute action {action}: {e}")
            return {"error": str(e)}

    @staticmethod
    def _generate_distance_message(distance: float) -> str:
        """生成距离显示消息"""
        if distance < 1:
            return f"距离约 {int(distance * 1000)} 米"
        elif distance < 10:
            return f"距离 {distance:.1f} 公里，非常近"
        elif distance < 50:
            return f"距离 {distance:.1f} 公里，在同城范围内"
        elif distance < 200:
            return f"距离 {distance:.0f} 公里，属于邻近城市"
        else:
            return f"距离 {distance:.0f} 公里，异地"
