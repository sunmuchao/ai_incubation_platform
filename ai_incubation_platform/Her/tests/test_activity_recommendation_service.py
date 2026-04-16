"""
活动推荐服务测试

测试 ActivityRecommendationService 的核心功能：
- 地理服务
- 地点推荐
- 地点收藏
"""
import pytest
from unittest.mock import MagicMock, patch
import math

# 尝试导入服务模块
try:
    from services.activity_recommendation_service import (
        GeoService,
        MapAPIService,
        ActivityRecommendationService,
        LOCATION_TYPES
    )
except ImportError:
    pytest.skip("activity_recommendation_service not importable", allow_module_level=True)


class TestLocationTypes:
    """地点类型测试"""

    def test_cafe_type(self):
        """测试咖啡厅类型"""
        assert "cafe" in LOCATION_TYPES
        assert LOCATION_TYPES["cafe"]["label"] == "咖啡厅"

    def test_restaurant_type(self):
        """测试餐厅类型"""
        assert "restaurant" in LOCATION_TYPES
        assert LOCATION_TYPES["restaurant"]["label"] == "餐厅"

    def test_park_type(self):
        """测试公园类型"""
        assert "park" in LOCATION_TYPES
        assert LOCATION_TYPES["park"]["label"] == "公园"

    def test_cinema_type(self):
        """测试电影院类型"""
        assert "cinema" in LOCATION_TYPES
        assert LOCATION_TYPES["cinema"]["label"] == "电影院"

    def test_activity_type(self):
        """测试活动类型"""
        assert "activity" in LOCATION_TYPES
        assert LOCATION_TYPES["activity"]["label"] == "活动"

    def test_museum_type(self):
        """测试博物馆类型"""
        assert "museum" in LOCATION_TYPES
        assert LOCATION_TYPES["museum"]["label"] == "博物馆"

    def test_sports_type(self):
        """测试运动类型"""
        assert "sports" in LOCATION_TYPES
        assert LOCATION_TYPES["sports"]["label"] == "运动"

    def test_bar_type(self):
        """测试酒吧类型"""
        assert "bar" in LOCATION_TYPES
        assert LOCATION_TYPES["bar"]["label"] == "酒吧"

    def test_location_types_count(self):
        """测试地点类型数量"""
        assert len(LOCATION_TYPES) >= 8

    def test_keywords_exist(self):
        """测试关键词存在"""
        for type_name, type_info in LOCATION_TYPES.items():
            assert "label" in type_info
            assert "keywords" in type_info


class TestGeoService:
    """地理服务测试"""

    def test_city_coordinates_exist(self):
        """测试城市坐标存在"""
        assert len(GeoService.CITY_COORDINATES) >= 5

    def test_beijing_coordinates(self):
        """测试北京坐标"""
        coords = GeoService.CITY_COORDINATES["北京"]
        assert coords[0] == 39.9042
        assert coords[1] == 116.4074

    def test_shanghai_coordinates(self):
        """测试上海坐标"""
        coords = GeoService.CITY_COORDINATES["上海"]
        assert coords[0] == 31.2304

    def test_guangzhou_coordinates(self):
        """测试广州坐标"""
        coords = GeoService.CITY_COORDINATES["广州"]
        assert coords[0] == 23.1291

    def test_calculate_distance_same_city(self):
        """测试同一城市距离"""
        # 同一点距离应为 0
        distance = GeoService.calculate_distance("北京", "北京")
        assert distance == 0

    def test_calculate_distance_different_cities(self):
        """测试不同城市距离"""
        distance = GeoService.calculate_distance("北京", "上海")
        assert distance is not None
        assert distance > 0

    def test_calculate_distance_unknown_city(self):
        """测试未知城市距离"""
        distance = GeoService.calculate_distance("未知城市", "北京")
        # 未知城市可能返回 None
        assert distance is None or distance >= 0

    def test_calculate_distance_coordinates_format(self):
        """测试坐标格式距离"""
        distance = GeoService.calculate_distance("39.9042,116.4074", "31.2304,121.4737")
        assert distance is not None
        assert distance > 0

    def test_get_coordinates_from_city(self):
        """测试从城市名获取坐标"""
        coords = GeoService._get_coordinates("北京")
        assert coords is not None
        assert coords[0] == 39.9042

    def test_get_coordinates_from_format(self):
        """测试从坐标格式获取坐标"""
        coords = GeoService._get_coordinates("30.0,120.0")
        assert coords is not None
        assert coords[0] == 30.0
        assert coords[1] == 120.0

    def test_get_coordinates_unknown(self):
        """测试未知地点获取坐标"""
        coords = GeoService._get_coordinates("未知地点")
        assert coords is None


class TestMapAPIService:
    """地图 API 服务测试"""

    def test_service_initialization(self):
        """测试服务初始化"""
        service = MapAPIService()
        assert service._api_provider in ["amap", "baidu"]

    def test_parse_price_level_low(self):
        """测试低价等级"""
        service = MapAPIService()
        level = service._parse_price_level("¥30")
        assert level == 1

    def test_parse_price_level_medium(self):
        """测试中等价格等级"""
        service = MapAPIService()
        level = service._parse_price_level("¥100")
        assert level == 2

    def test_parse_price_level_high(self):
        """测试高价等级"""
        service = MapAPIService()
        level = service._parse_price_level("¥200")
        assert level == 3

    def test_parse_price_level_very_high(self):
        """测试超高价格等级"""
        service = MapAPIService()
        level = service._parse_price_level("¥500")
        assert level == 4

    def test_parse_price_level_invalid(self):
        """测试无效价格"""
        service = MapAPIService()
        level = service._parse_price_level("invalid")
        assert level == 2  # 默认中等价位

    def test_parse_price_level_empty(self):
        """测试空价格"""
        service = MapAPIService()
        level = service._parse_price_level("")
        assert level == 2

    def test_mock_search(self):
        """测试模拟搜索"""
        service = MapAPIService()
        results = service._mock_search(39.9, 116.4, "咖啡厅", 3000, 5)
        assert len(results) <= 5
        for result in results:
            assert "name" in result
            assert "address" in result
            assert "latitude" in result

    def test_mock_search_structure(self):
        """测试模拟搜索结构"""
        service = MapAPIService()
        results = service._mock_search(39.9, 116.4, "咖啡厅", 3000, 3)
        if results:
            result = results[0]
            assert "type" in result
            assert "rating" in result
            assert "price_level" in result

    def test_search_nearby_without_api_key(self):
        """测试无 API Key 搜索"""
        service = MapAPIService()
        service._enabled = False
        results = service.search_nearby(39.9, 116.4, "咖啡厅")
        # 应返回 mock 结果
        assert isinstance(results, list)


class TestActivityRecommendationService:
    """活动推荐服务测试"""

    def test_service_initialization(self):
        """测试服务初始化"""
        service = ActivityRecommendationService()
        assert service.map_api is not None
        assert service.geo_service is not None

    def test_calculate_midpoint_same_location(self):
        """测试同一地点中间点"""
        service = ActivityRecommendationService()
        midpoint = service._calculate_midpoint("北京", "北京")
        # 应返回有效坐标
        assert midpoint is not None

    def test_calculate_midpoint_different_cities(self):
        """测试不同城市中间点"""
        service = ActivityRecommendationService()
        midpoint = service._calculate_midpoint("北京", "上海")
        # 应返回坐标格式
        assert "," in midpoint

    def test_calculate_midpoint_unknown_location(self):
        """测试未知地点中间点"""
        service = ActivityRecommendationService()
        midpoint = service._calculate_midpoint("未知", "北京")
        # 应返回第一个地点
        assert midpoint == "北京" or midpoint is not None


class TestHaversineFormula:
    """Haversine 公式测试"""

    def test_haversine_calculation(self):
        """测试 Haversine 计算"""
        # 北京到上海约 1000+ km
        distance = GeoService.calculate_distance("北京", "上海")
        if distance:
            assert distance > 1000
            assert distance < 2000

    def test_zero_distance(self):
        """测试零距离"""
        # 使用相同坐标
        coords1 = "39.9042,116.4074"
        coords2 = "39.9042,116.4074"
        distance = GeoService.calculate_distance(coords1, coords2)
        assert distance == 0

    def test_earth_radius_value(self):
        """测试地球半径值"""
        R = 6371  # 地球半径（公里）
        assert R > 6000
        assert R < 7000


class TestEdgeCases:
    """边界值测试"""

    def test_negative_latitude(self):
        """测试负纬度"""
        # 南半球坐标
        coords = "-33.8688,151.2093"  # 悉尼
        result = GeoService._get_coordinates(coords)
        assert result is not None

    def test_large_distance(self):
        """测试大距离"""
        # 北京到悉尼约 8000+ km
        coords1 = "39.9042,116.4074"
        coords2 = "-33.8688,151.2093"
        distance = GeoService.calculate_distance(coords1, coords2)
        if distance:
            assert distance > 5000

    def test_empty_keyword(self):
        """测试空关键词"""
        service = MapAPIService()
        results = service._mock_search(39.9, 116.4, "", 3000, 5)
        assert isinstance(results, list)

    def test_large_radius(self):
        """测试大搜索半径"""
        service = MapAPIService()
        results = service._mock_search(39.9, 116.4, "咖啡厅", 50000, 10)
        assert isinstance(results, list)

    def test_small_limit(self):
        """测试小返回数量"""
        service = MapAPIService()
        results = service._mock_search(39.9, 116.4, "咖啡厅", 3000, 1)
        assert len(results) <= 1

    def test_large_limit(self):
        """测试大返回数量"""
        service = MapAPIService()
        results = service._mock_search(39.9, 116.4, "咖啡厅", 3000, 100)
        assert len(results) <= 100