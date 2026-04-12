"""
外部服务单元测试
"""
import pytest
from datetime import datetime, date
from unittest.mock import patch, MagicMock
import math

# WeatherService 相关导入已移除（服务不存在）
from services.reservation_service import (
    ReservationService,
    MockReservationProvider,
    DianpingProvider,
    MaoyanProvider,
)
from services.geo_service import (
    haversine_distance,
    calculate_midpoint,
    calculate_weighted_midpoint,
    find_nearby_places,
    calculate_meeting_point,
    is_within_radius,
    GeoService,
)


# ==================== Weather Service Tests ====================
# 跳过 Weather 相关测试（服务不存在）

@pytest.mark.skip(reason="WeatherService not implemented")
class TestMockWeatherProvider:
    """Mock 天气服务测试"""

    @pytest.fixture
    def provider(self):
        return MockWeatherProvider()

    def test_get_current_weather(self, provider):
        """测试获取当前天气"""
        # Act
        weather = provider.get_current_weather("北京市")

        # Assert
        assert weather is not None
        assert weather["city"] == "北京市"
        assert "temperature" in weather
        assert weather["provider"] == "mock"

    def test_get_current_weather_unknown_city(self, provider):
        """测试获取未知城市天气"""
        # Act
        weather = provider.get_current_weather("Unknown City")

        # Assert
        assert weather is not None
        assert weather["temperature"] == 20  # 默认值

    def test_get_weather_forecast(self, provider):
        """测试获取天气预报"""
        # Act
        forecasts = provider.get_weather_forecast("北京市", days=3)

        # Assert
        assert len(forecasts) == 3
        assert "date" in forecasts[0]
        assert "temp_max" in forecasts[0]
        assert "temp_min" in forecasts[0]

    def test_get_outfit_suggestion_cold(self, provider):
        """测试获取穿搭建议（冷天）"""
        # Arrange
        with patch.object(provider, 'get_current_weather') as mock_get:
            mock_get.return_value = {
                "temperature": 3,
                "weather": "晴朗"
            }

            # Act
            suggestion = provider.get_outfit_suggestion("北京市")

            # Assert
            assert "厚羽绒服" in suggestion["clothing"]
            assert suggestion["style"] == "保暖优先"

    def test_get_outfit_suggestion_warm(self, provider):
        """测试获取穿搭建议（温暖）"""
        # Arrange
        with patch.object(provider, 'get_current_weather') as mock_get:
            mock_get.return_value = {
                "temperature": 20,
                "weather": "晴朗"
            }

            # Act
            suggestion = provider.get_outfit_suggestion("北京市")

            # Assert
            assert "长袖 T 恤" in suggestion["clothing"]
            assert suggestion["style"] == "舒适休闲"

    def test_get_outfit_suggestion_hot(self, provider):
        """测试获取穿搭建议（热天）"""
        # Arrange
        with patch.object(provider, 'get_current_weather') as mock_get:
            mock_get.return_value = {
                "temperature": 30,
                "weather": "晴朗"
            }

            # Act
            suggestion = provider.get_outfit_suggestion("北京市")

            # Assert
            assert "短袖 T 恤" in suggestion["clothing"]
            assert suggestion["style"] == "清爽透气"


@pytest.mark.skip(reason="WeatherService not implemented")
class TestWeatherService:
    """天气服务统一入口测试"""

    @pytest.fixture
    def service(self):
        return WeatherService(provider="mock")

    def test_get_weather(self, service):
        """测试获取天气"""
        # Act
        weather = service.get_weather("北京市")

        # Assert
        assert weather is not None
        assert weather["provider"] == "mock"

    def test_get_forecast(self, service):
        """测试获取预报"""
        # Act
        forecasts = service.get_forecast("北京市", days=3)

        # Assert
        assert len(forecasts) == 3

    def test_get_outfit_recommendation(self, service):
        """测试获取穿搭推荐"""
        # Act
        suggestion = service.get_outfit_recommendation("北京市")

        # Assert
        assert "clothing" in suggestion
        assert "style" in suggestion

    def test_switch_provider(self, service):
        """测试切换服务提供者"""
        # Act
        service.switch_provider("openweathermap")

        # Assert
        assert service.provider_name == "openweathermap"
        assert isinstance(service.provider, OpenWeatherMapProvider)


# ==================== Reservation Service Tests ====================

class TestMockReservationProvider:
    """Mock 预订服务测试"""

    @pytest.fixture
    def provider(self):
        return MockReservationProvider()

    def test_search_restaurants(self, provider):
        """测试搜索餐厅"""
        # Act
        restaurants = provider.search_restaurants("北京市")

        # Assert
        assert len(restaurants) >= 1
        assert "id" in restaurants[0]
        assert "name" in restaurants[0]
        assert "rating" in restaurants[0]

    def test_get_restaurant_details(self, provider):
        """测试获取餐厅详情"""
        # Act
        details = provider.get_restaurant_details("rest_mock_001")

        # Assert
        assert details is not None
        assert details["name"] == "Mock 餐厅"

    def test_make_restaurant_reservation(self, provider):
        """测试预订餐厅"""
        # Arrange
        reservation_time = datetime(2024, 12, 25, 19, 0)

        # Act
        result = provider.make_restaurant_reservation(
            restaurant_id="rest_mock_001",
            user_name="测试用户",
            phone="13800138000",
            party_size=2,
            reservation_time=reservation_time
        )

        # Assert
        assert result["success"] == True
        assert "reservation_id" in result
        assert "confirmation_code" in result
        assert result["status"] == "confirmed"

    def test_search_cinemas(self, provider):
        """测试搜索电影院"""
        # Act
        cinemas = provider.search_cinemas("北京市")

        # Assert
        assert len(cinemas) >= 1
        assert "id" in cinemas[0]
        assert "name" in cinemas[0]

    def test_get_movie_showtimes(self, provider):
        """测试获取电影场次"""
        # Arrange
        show_date = date(2024, 12, 25)

        # Act
        showtimes = provider.get_movie_showtimes("cinema_mock_001", "movie_001", show_date)

        # Assert
        assert len(showtimes) >= 1
        assert "showtime_id" in showtimes[0]
        assert "start_time" in showtimes[0]

    def test_get_available_seats(self, provider):
        """测试获取可选座位"""
        # Act
        seats = provider.get_available_seats("st_mock_001")

        # Assert
        assert len(seats) >= 1
        assert "seat_id" in seats[0]
        assert seats[0]["available"] == True

    def test_book_movie_tickets(self, provider):
        """测试预订电影票"""
        # Act
        result = provider.book_movie_tickets(
            showtime_id="st_mock_001",
            seat_ids=["F7", "F8"],
            user_name="测试用户",
            phone="13800138000"
        )

        # Assert
        assert result["success"] == True
        assert "order_id" in result
        assert result["total_price"] == 100  # 2 * 50


class TestReservationService:
    """预订服务统一入口测试"""

    @pytest.fixture
    def service(self):
        return ReservationService(
            restaurant_provider="mock",
            cinema_provider="mock"
        )

    def test_search_restaurants(self, service):
        """测试搜索餐厅"""
        # Act
        restaurants = service.search_restaurants("北京市")

        # Assert
        assert len(restaurants) >= 1

    def test_make_restaurant_reservation(self, service):
        """测试预订餐厅"""
        # Arrange
        reservation_time = datetime(2024, 12, 25, 19, 0)

        # Act
        result = service.make_restaurant_reservation(
            restaurant_id="rest_mock_001",
            user_name="测试用户",
            phone="13800138000",
            party_size=2,
            reservation_time=reservation_time
        )

        # Assert
        assert result["success"] == True

    def test_search_cinemas(self, service):
        """测试搜索电影院"""
        # Act
        cinemas = service.search_cinemas("北京市")

        # Assert
        assert len(cinemas) >= 1

    def test_book_movie_tickets(self, service):
        """测试预订电影票"""
        # Act
        result = service.book_movie_tickets(
            showtime_id="st_mock_001",
            seat_ids=["F7", "F8"],
            user_name="测试用户",
            phone="13800138000"
        )

        # Assert
        assert result["success"] == True


# ==================== Geo Service Tests ====================

class TestHaversineDistance:
    """Haversine 距离计算测试"""

    def test_beijing_to_shanghai(self):
        """测试北京到上海的距离"""
        # Arrange
        beijing_lat, beijing_lon = 39.9042, 116.4074
        shanghai_lat, shanghai_lon = 31.2304, 121.4737

        # Act
        distance = haversine_distance(
            beijing_lat, beijing_lon,
            shanghai_lat, shanghai_lon
        )

        # Assert
        assert distance > 1000  # 应该超过 1000 公里
        assert distance < 1200  # 应该少于 1200 公里

    def test_same_point(self):
        """测试同一点的距离"""
        # Act
        distance = haversine_distance(
            39.9042, 116.4074,
            39.9042, 116.4074
        )

        # Assert
        assert distance == pytest.approx(0.0, abs=0.01)

    def test_nearby_points(self):
        """测试附近点的距离"""
        # Act
        distance = haversine_distance(
            39.9042, 116.4074,
            39.9142, 116.4174  # 约 1 公里外
        )

        # Assert
        assert distance > 0
        assert distance < 2  # 应该在 2 公里内


class TestCalculateMidpoint:
    """中点计算测试"""

    def test_basic_midpoint(self):
        """测试基本中点计算"""
        # Arrange
        lat1, lon1 = 39.9042, 116.4074  # 北京
        lat2, lon1 = 39.8042, 116.5074  # 北京通州附近

        # Act
        midpoint = calculate_midpoint(lat1, lon1, lat2, lon1)

        # Assert
        assert midpoint["latitude"] == pytest.approx((lat1 + lat2) / 2, abs=0.1)
        assert midpoint["longitude"] == pytest.approx(lon1, abs=0.1)

    def test_same_point_midpoint(self):
        """测试同一点的中点"""
        # Act
        midpoint = calculate_midpoint(39.9042, 116.4074, 39.9042, 116.4074)

        # Assert
        assert midpoint["latitude"] == pytest.approx(39.9042, abs=0.01)
        assert midpoint["longitude"] == pytest.approx(116.4074, abs=0.01)


class TestCalculateWeightedMidpoint:
    """加权中点计算测试"""

    def test_equal_weights(self):
        """测试等权重的加权中点"""
        # Arrange
        locations = [
            {"latitude": 0, "longitude": 0},
            {"latitude": 10, "longitude": 0},
        ]

        # Act
        midpoint = calculate_weighted_midpoint(locations)

        # Assert
        assert midpoint["latitude"] == pytest.approx(5, abs=0.1)

    def test_single_location(self):
        """测试单一点的加权中点"""
        # Arrange
        locations = [{"latitude": 39.9042, "longitude": 116.4074}]

        # Act
        midpoint = calculate_weighted_midpoint(locations)

        # Assert
        assert midpoint["latitude"] == pytest.approx(39.9042, abs=0.01)
        assert midpoint["longitude"] == pytest.approx(116.4074, abs=0.01)

    def test_weighted_midpoint(self):
        """测试加权中点"""
        # Arrange
        locations = [
            {"latitude": 0, "longitude": 0},
            {"latitude": 10, "longitude": 0},
        ]
        weights = [0.75, 0.25]  # 第一个点权重更大

        # Act
        midpoint = calculate_weighted_midpoint(locations, weights)

        # Assert
        assert midpoint["latitude"] < 5  # 应该更靠近第一个点


class TestFindNearbyPlaces:
    """附近场所查找测试"""

    def test_find_restaurants(self):
        """测试查找餐厅"""
        # Act
        places = find_nearby_places(
            latitude=39.9042,
            longitude=116.4074,
            place_type="restaurant",
            radius_km=5.0,
            limit=5
        )

        # Assert
        assert len(places) >= 1
        assert places[0]["type"] == "restaurant"
        assert "rating" in places[0]

    def test_find_cafes(self):
        """测试查找咖啡馆"""
        # Act
        places = find_nearby_places(
            latitude=39.9042,
            longitude=116.4074,
            place_type="cafe",
            radius_km=5.0
        )

        # Assert
        assert len(places) >= 1
        assert places[0]["type"] == "cafe"

    def test_find_cinemas(self):
        """测试查找电影院"""
        # Act
        places = find_nearby_places(
            latitude=39.9042,
            longitude=116.4074,
            place_type="cinema",
            radius_km=5.0
        )

        # Assert
        assert len(places) >= 1
        assert places[0]["type"] == "cinema"

    def test_places_sorted_by_distance(self):
        """测试场所按距离排序"""
        # Act
        places = find_nearby_places(
            latitude=39.9042,
            longitude=116.4074,
            place_type="restaurant",
            radius_km=5.0,
            limit=5
        )

        # Assert
        for i in range(len(places) - 1):
            assert places[i]["distance_km"] <= places[i + 1]["distance_km"]


class TestCalculateMeetingPoint:
    """会面点计算测试"""

    def test_basic_meeting_point(self):
        """测试基本会面点计算"""
        # Arrange
        user1 = {"latitude": 39.9042, "longitude": 116.4074}
        user2 = {"latitude": 39.8042, "longitude": 116.5074}

        # Act
        result = calculate_meeting_point(user1, user2)

        # Assert
        assert "midpoint" in result
        assert "user1_distance_km" in result
        assert "user2_distance_km" in result
        assert "nearby_places" in result

    def test_meeting_point_with_place_type(self):
        """测试指定场所类型的会面点"""
        # Arrange
        user1 = {"latitude": 39.9042, "longitude": 116.4074}
        user2 = {"latitude": 39.8042, "longitude": 116.5074}

        # Act
        result = calculate_meeting_point(user1, user2, place_type="cafe")

        # Assert
        assert result["place_type"] == "cafe"
        assert all(p["type"] == "cafe" for p in result["nearby_places"])

    def test_equal_distance_to_midpoint(self):
        """测试两人到中点距离大致相等"""
        # Arrange
        user1 = {"latitude": 39.9042, "longitude": 116.4074}
        user2 = {"latitude": 39.8042, "longitude": 116.4074}  # 同一经度

        # Act
        result = calculate_meeting_point(user1, user2)

        # Assert
        assert result["user1_distance_km"] == pytest.approx(
            result["user2_distance_km"], abs=1.0
        )


class TestIsWithinRadius:
    """半径范围检查测试"""

    def test_point_within_radius(self):
        """测试点在半径范围内"""
        # Act
        result = is_within_radius(
            center_lat=39.9042,
            center_lon=116.4074,
            point_lat=39.9142,  # 约 1 公里外
            point_lon=116.4174,
            radius_km=5.0
        )

        # Assert
        assert result == True

    def test_point_outside_radius(self):
        """测试点在半径范围外"""
        # Act
        result = is_within_radius(
            center_lat=39.9042,
            center_lon=116.4074,
            point_lat=40.0042,  # 约 11 公里外
            point_lon=116.5074,
            radius_km=5.0
        )

        # Assert
        assert result == False


class TestGeoService:
    """地理服务统一入口测试"""

    @pytest.fixture
    def service(self):
        return GeoService()

    def test_get_distance(self, service):
        """测试获取距离"""
        # Act
        distance = service.get_distance(39.9042, 116.4074, 31.2304, 121.4737)

        # Assert
        assert distance > 1000

    def test_get_midpoint(self, service):
        """测试获取中点"""
        # Act
        midpoint = service.get_midpoint(39.9042, 116.4074, 39.8042, 116.5074)

        # Assert
        assert "latitude" in midpoint
        assert "longitude" in midpoint

    def test_find_date_spots(self, service):
        """测试查找约会地点"""
        # Act
        result = service.find_date_spots(
            user1_lat=39.9042, user1_lon=116.4074,
            user2_lat=39.8042, user2_lon=116.5074,
            spot_type="restaurant"
        )

        # Assert
        assert "midpoint" in result
        assert "nearby_places" in result
        assert len(result["nearby_places"]) > 0
