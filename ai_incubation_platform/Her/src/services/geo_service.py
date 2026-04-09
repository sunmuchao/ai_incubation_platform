"""
地理服务模块

功能：
1. Haversine 公式计算两点间距离
2. 计算两个位置的地理中点
3. 查找中点附近的场所

配置项：
- AMENITIES_API_KEY: 场所搜索 API 密钥（可选）
"""
import math
from typing import Dict, List, Optional, Any, Tuple
import logging

logger = logging.getLogger(__name__)


# 地球半径（公里）
EARTH_RADIUS_KM = 6371.0


def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:
    """
    使用 Haversine 公式计算两点间的大圆距离

    Args:
        lat1: 点 1 纬度
        lon1: 点 1 经度
        lat2: 点 2 纬度
        lon2: 点 2 经度

    Returns:
        两点间的距离（公里）

    Example:
        >>> haversine_distance(39.9042, 116.4074, 31.2304, 121.4737)
        1067.35  # 北京到上海的距离
    """
    # 将经纬度从度转换为弧度
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    # Haversine 公式
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = EARTH_RADIUS_KM * c
    return distance


def calculate_midpoint(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> Dict[str, float]:
    """
    计算两个地理坐标的中点

    Args:
        lat1: 点 1 纬度
        lon1: 点 1 经度
        lat2: 点 2 纬度
        lon2: 点 2 经度

    Returns:
        中点坐标 {"latitude": float, "longitude": float}

    Example:
        >>> calculate_midpoint(39.9042, 116.4074, 31.2304, 121.4737)
        {'latitude': 35.5873, 'longitude': 118.9269}
    """
    # 转换为弧度
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # 计算中点
    # 使用球面几何的中点公式
    delta_lon = lon2_rad - lon1_rad

    # 中间变量
    Bx = math.cos(lat2_rad) * math.cos(delta_lon)
    By = math.cos(lat2_rad) * math.sin(delta_lon)

    # 计算中点纬度和经度
    mid_lat_rad = math.atan2(
        math.sin(lat1_rad) + math.sin(lat2_rad),
        math.sqrt(
            (math.cos(lat1_rad) + Bx) ** 2 + By ** 2
        )
    )
    mid_lon_rad = lon1_rad + math.atan2(By, math.cos(lat1_rad) + Bx)

    # 转换回度
    return {
        "latitude": math.degrees(mid_lat_rad),
        "longitude": math.degrees(mid_lon_rad)
    }


def calculate_weighted_midpoint(
    locations: List[Dict[str, float]],
    weights: Optional[List[float]] = None
) -> Dict[str, float]:
    """
    计算多个位置的加权中点

    Args:
        locations: 位置列表，每个位置包含 {"latitude": float, "longitude": float}
        weights: 权重列表（可选，默认为等权重）

    Returns:
        加权中点坐标

    Example:
        >>> locations = [
        ...     {"latitude": 39.9042, "longitude": 116.4074},  # 北京
        ...     {"latitude": 31.2304, "longitude": 121.4737},  # 上海
        ...     {"latitude": 23.1291, "longitude": 113.2644},  # 广州
        ... ]
        >>> calculate_weighted_midpoint(locations)
        {'latitude': 31.2304, 'longitude': 117.2644}
    """
    if not locations:
        raise ValueError("Locations list cannot be empty")

    if len(locations) == 1:
        return {
            "latitude": locations[0]["latitude"],
            "longitude": locations[0]["longitude"]
        }

    # 如果没有提供权重，使用等权重
    if weights is None:
        weights = [1.0] * len(locations)
    elif len(weights) != len(locations):
        raise ValueError("Weights length must match locations length")

    # 归一化权重
    total_weight = sum(weights)
    weights = [w / total_weight for w in weights]

    # 将经纬度转换为 3D 笛卡尔坐标
    x_sum = 0.0
    y_sum = 0.0
    z_sum = 0.0

    for loc, weight in zip(locations, weights):
        lat_rad = math.radians(loc["latitude"])
        lon_rad = math.radians(loc["longitude"])

        x = weight * math.cos(lat_rad) * math.cos(lon_rad)
        y = weight * math.cos(lat_rad) * math.sin(lon_rad)
        z = weight * math.sin(lat_rad)

        x_sum += x
        y_sum += y
        z_sum += z

    # 将笛卡尔坐标转换回经纬度
    mid_lon_rad = math.atan2(y_sum, x_sum)
    mid_hyp = math.sqrt(x_sum ** 2 + y_sum ** 2)
    mid_lat_rad = math.atan2(z_sum, mid_hyp)

    return {
        "latitude": math.degrees(mid_lat_rad),
        "longitude": math.degrees(mid_lon_rad)
    }


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: Optional[str] = None,
    radius_km: float = 5.0,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    查找中点附近的场所

    Args:
        latitude: 中心点纬度
        longitude: 中心点经度
        place_type: 场所类型 (restaurant, cafe, cinema, park, etc.)
        radius_km: 搜索半径（公里）
        limit: 返回数量限制

    Returns:
        场所列表

    Note:
        实际使用时需要集成地图 API（如 Google Places、高德地图、百度地图等）
        这里提供一个 Mock 实现
    """
    # Mock 场所数据
    mock_places = {
        "restaurant": [
            {"name": "浪漫西餐厅", "type": "restaurant", "cuisine": "西餐", "rating": 4.8},
            {"name": "日式料理店", "type": "restaurant", "cuisine": "日料", "rating": 4.6},
            {"name": "意大利餐厅", "type": "restaurant", "cuisine": "意大利菜", "rating": 4.5},
            {"name": "中餐厅", "type": "restaurant", "cuisine": "中餐", "rating": 4.4},
            {"name": "火锅店", "type": "restaurant", "cuisine": "火锅", "rating": 4.3},
        ],
        "cafe": [
            {"name": "星巴克咖啡", "type": "cafe", "rating": 4.5},
            {"name": "Costa Coffee", "type": "cafe", "rating": 4.4},
            {"name": "独立咖啡馆", "type": "cafe", "rating": 4.7},
        ],
        "cinema": [
            {"name": "万达影城", "type": "cinema", "features": ["IMAX", "杜比"], "rating": 4.8},
            {"name": "UME 影城", "type": "cinema", "features": ["激光 IMAX"], "rating": 4.6},
            {"name": "百丽宫影城", "type": "cinema", "features": ["艺术电影"], "rating": 4.7},
        ],
        "park": [
            {"name": "中央公园", "type": "park", "features": ["散步", "野餐"], "rating": 4.6},
            {"name": "城市花园", "type": "park", "features": ["赏花", "休闲"], "rating": 4.4},
        ],
        "shopping": [
            {"name": "购物中心", "type": "shopping", "features": ["餐饮", "娱乐"], "rating": 4.5},
            {"name": "百货商场", "type": "shopping", "features": ["购物", "餐饮"], "rating": 4.3},
        ]
    }

    # 如果没有指定类型，返回所有类型
    if place_type and place_type in mock_places:
        places = mock_places[place_type]
    elif place_type:
        # 尝试模糊匹配
        for key in mock_places:
            if place_type.lower() in key.lower():
                places = mock_places[key]
                break
        else:
            places = []
    else:
        # 返回所有场所
        places = []
        for category_places in mock_places.values():
            places.extend(category_places)

    # 为每个场所添加距离和坐标信息
    result = []
    for i, place in enumerate(places[:limit]):
        # 在搜索半径内生成随机偏移
        distance_offset = (i + 1) * radius_km / (limit + 1)
        angle = (i * 45) % 360  # 均匀分布

        # 计算偏移后的坐标（近似）
        lat_offset = (distance_offset / EARTH_RADIUS_KM) * math.cos(math.radians(angle))
        lon_offset = (distance_offset / EARTH_RADIUS_KM) * math.sin(math.radians(angle))

        place_lat = latitude + math.degrees(lat_offset)
        place_lon = longitude + math.degrees(lon_offset)

        result.append({
            "id": f"place_{place_type}_{i}",
            "name": place["name"],
            "type": place["type"],
            "latitude": place_lat,
            "longitude": place_lon,
            "distance_km": round(distance_offset, 2),
            "rating": place.get("rating", 0),
            "cuisine": place.get("cuisine"),
            "features": place.get("features", []),
            "address": f"中点附近 {distance_offset:.1f}km 处"
        })

    # 按距离排序
    result.sort(key=lambda x: x["distance_km"])

    return result


def calculate_meeting_point(
    user1_location: Dict[str, float],
    user2_location: Dict[str, float],
    place_type: Optional[str] = None,
    search_radius_km: float = 5.0
) -> Dict[str, Any]:
    """
    计算两人见面的最佳地点

    Args:
        user1_location: 用户 1 位置 {"latitude": float, "longitude": float}
        user2_location: 用户 2 位置 {"latitude": float, "longitude": float}
        place_type: 场所类型（可选）
        search_radius_km: 搜索半径（公里）

    Returns:
        包含中点和附近场所的信息

    Example:
        >>> user1 = {"latitude": 39.9042, "longitude": 116.4074}  # 北京
        >>> user2 = {"latitude": 39.8042, "longitude": 116.5074}  # 北京通州
        >>> result = calculate_meeting_point(user1, user2, "cafe")
    """
    # 计算中点
    midpoint = calculate_midpoint(
        user1_location["latitude"],
        user1_location["longitude"],
        user2_location["latitude"],
        user2_location["longitude"]
    )

    # 计算两人到中点的距离
    distance1 = haversine_distance(
        user1_location["latitude"],
        user1_location["longitude"],
        midpoint["latitude"],
        midpoint["longitude"]
    )
    distance2 = haversine_distance(
        user2_location["latitude"],
        user2_location["longitude"],
        midpoint["latitude"],
        midpoint["longitude"]
    )

    # 查找附近场所
    nearby_places = find_nearby_places(
        midpoint["latitude"],
        midpoint["longitude"],
        place_type,
        search_radius_km
    )

    return {
        "midpoint": midpoint,
        "user1_distance_km": round(distance1, 2),
        "user2_distance_km": round(distance2, 2),
        "total_distance_km": round(distance1 + distance2, 2),
        "nearby_places": nearby_places,
        "place_type": place_type
    }


def format_coordinates(latitude: float, longitude: float) -> str:
    """
    格式化坐标显示

    Args:
        latitude: 纬度
        longitude: 经度

    Returns:
        格式化后的坐标字符串
    """
    lat_direction = "N" if latitude >= 0 else "S"
    lon_direction = "E" if longitude >= 0 else "W"

    lat_deg = int(abs(latitude))
    lat_min = (abs(latitude) - lat_deg) * 60

    lon_deg = int(abs(longitude))
    lon_min = (abs(longitude) - lon_deg) * 60

    return f"{lat_deg}°{lat_min:.2f}'{lat_direction} {lon_deg}°{lon_min:.2f}'{lon_direction}"


def is_within_radius(
    center_lat: float,
    center_lon: float,
    point_lat: float,
    point_lon: float,
    radius_km: float
) -> bool:
    """
    检查点是否在指定半径范围内

    Args:
        center_lat: 中心点纬度
        center_lon: 中心点经度
        point_lat: 待检查点纬度
        point_lon: 待检查点经度
        radius_km: 半径（公里）

    Returns:
        是否在范围内
    """
    distance = haversine_distance(center_lat, center_lon, point_lat, point_lon)
    return distance <= radius_km


class GeoService:
    """地理服务统一入口"""

    def __init__(self):
        """初始化地理服务"""
        pass

    def get_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        获取两点间距离

        Args:
            lat1, lon1: 点 1 坐标
            lat2, lon2: 点 2 坐标

        Returns:
            距离（公里）
        """
        return haversine_distance(lat1, lon1, lat2, lon2)

    def get_midpoint(self, lat1: float, lon1: float, lat2: float, lon2: float) -> Dict[str, float]:
        """
        获取两点中点

        Args:
            lat1, lon1: 点 1 坐标
            lat2, lon2: 点 2 坐标

        Returns:
            中点坐标
        """
        return calculate_midpoint(lat1, lon1, lat2, lon2)

    def find_date_spots(
        self,
        user1_lat: float,
        user1_lon: float,
        user2_lat: float,
        user2_lon: float,
        spot_type: Optional[str] = None,
        radius_km: float = 5.0
    ) -> Dict[str, Any]:
        """
        查找约会地点

        Args:
            user1_lat, user1_lon: 用户 1 坐标
            user2_lat, user2_lon: 用户 2 坐标
            spot_type: 地点类型
            radius_km: 搜索半径

        Returns:
            包含中点和附近地点的信息
        """
        return calculate_meeting_point(
            {"latitude": user1_lat, "longitude": user1_lon},
            {"latitude": user2_lat, "longitude": user2_lon},
            spot_type,
            radius_km
        )


# 全局服务实例
geo_service = GeoService()
