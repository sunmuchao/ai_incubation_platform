"""
预订服务模块

支持：
1. 餐厅预订（美团/大众点评 API 抽象）
2. 电影院选座 API 抽象
3. Mock 实现（用于测试）

配置项：
- RESERVATION_PROVIDER: 预订服务提供商 (dianping, maoyan, mock)
- DIANPING_API_KEY: 大众点评 API 密钥
- MAOYAN_API_KEY: 猫眼 API 密钥
"""
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from abc import ABC, abstractmethod
import uuid
from utils.logger import logger


class ReservationProvider(ABC):
    """预订服务提供者抽象基类"""

    @abstractmethod
    def search_restaurants(self, city: str, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """搜索餐厅"""
        raise NotImplementedError("Subclasses must implement search_restaurants")

    @abstractmethod
    def get_restaurant_details(self, restaurant_id: str) -> Optional[Dict[str, Any]]:
        """获取餐厅详情"""
        raise NotImplementedError("Subclasses must implement get_restaurant_details")

    @abstractmethod
    def make_restaurant_reservation(
        self,
        restaurant_id: str,
        user_name: str,
        phone: str,
        party_size: int,
        reservation_time: datetime
    ) -> Dict[str, Any]:
        """预订餐厅"""
        raise NotImplementedError("Subclasses must implement make_restaurant_reservation")

    @abstractmethod
    def search_cinemas(self, city: str, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """搜索电影院"""
        raise NotImplementedError("Subclasses must implement search_cinemas")

    @abstractmethod
    def get_movie_showtimes(self, cinema_id: str, movie_id: str, show_date: date) -> List[Dict[str, Any]]:
        """获取电影场次"""
        raise NotImplementedError("Subclasses must implement get_movie_showtimes")

    @abstractmethod
    def get_available_seats(self, showtime_id: str) -> List[Dict[str, Any]]:
        """获取可选座位"""
        raise NotImplementedError("Subclasses must implement get_available_seats")

    @abstractmethod
    def book_movie_tickets(
        self,
        showtime_id: str,
        seat_ids: List[str],
        user_name: str,
        phone: str
    ) -> Dict[str, Any]:
        """预订电影票"""
        raise NotImplementedError("Subclasses must implement book_movie_tickets")


class DianpingProvider(ReservationProvider):
    """大众点评 API 提供者（餐厅预订）"""

    BASE_URL = "https://api.dianping.com/v1"

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.api_key = api_key or os.getenv("DIANPING_API_KEY")
        self.api_secret = api_secret or os.getenv("DIANPING_API_SECRET")
        if not self.api_key:
            logger.warning("Dianping API key not configured")

    def search_restaurants(self, city: str, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        搜索餐厅

        Args:
            city: 城市名
            filters: 筛选条件 {cuisine, price_range, rating_min, ...}

        Returns:
            餐厅列表
        """
        if not self.api_key:
            return []

        try:
            url = f"{self.BASE_URL}/restaurant/search"
            params = {
                "city": city,
                "apikey": self.api_key,
                "limit": 20
            }

            if filters:
                if filters.get("cuisine"):
                    params["cuisine"] = filters["cuisine"]
                if filters.get("price_range"):
                    params["price_range"] = filters["price_range"]
                if filters.get("rating_min"):
                    params["rating_min"] = filters["rating_min"]

            # 实际使用时需要添加签名
            # response = requests.get(url, params=params, timeout=10)
            # response.raise_for_status()
            # data = response.json()

            # Mock 响应（实际使用时替换）
            logger.info(f"Search restaurants in {city} with filters: {filters}")
            return self._mock_restaurant_search(city, filters)
        except Exception as e:
            logger.error(f"Error searching restaurants: {e}")
            return []

    def get_restaurant_details(self, restaurant_id: str) -> Optional[Dict[str, Any]]:
        """获取餐厅详情"""
        if not self.api_key:
            return None

        try:
            url = f"{self.BASE_URL}/restaurant/{restaurant_id}"
            params = {"apikey": self.api_key}

            # 实际使用时需要添加签名
            # response = requests.get(url, params=params, timeout=10)
            # response.raise_for_status()
            # data = response.json()

            logger.info(f"Get restaurant details: {restaurant_id}")
            return self._mock_restaurant_details(restaurant_id)
        except Exception as e:
            logger.error(f"Error fetching restaurant details: {e}")
            return None

    def make_restaurant_reservation(
        self,
        restaurant_id: str,
        user_name: str,
        phone: str,
        party_size: int,
        reservation_time: datetime
    ) -> Dict[str, Any]:
        """
        预订餐厅

        Args:
            restaurant_id: 餐厅 ID
            user_name: 预订人姓名
            phone: 联系电话
            party_size: 用餐人数
            reservation_time: 预订时间

        Returns:
            预订结果
        """
        if not self.api_key:
            return {"error": "API not configured"}

        try:
            url = f"{self.BASE_URL}/reservation/create"
            data = {
                "restaurant_id": restaurant_id,
                "user_name": user_name,
                "phone": phone,
                "party_size": party_size,
                "reservation_time": reservation_time.isoformat(),
                "apikey": self.api_key
            }

            # 实际使用时需要添加签名
            # response = requests.post(url, json=data, timeout=10)
            # response.raise_for_status()
            # result = response.json()

            logger.info(f"Make reservation at {restaurant_id} for {user_name}")

            # Mock 响应
            return {
                "success": True,
                "reservation_id": str(uuid.uuid4()),
                "confirmation_code": f"DP{uuid.uuid4().hex[:8].upper()}",
                "restaurant_id": restaurant_id,
                "user_name": user_name,
                "party_size": party_size,
                "reservation_time": reservation_time.isoformat(),
                "status": "confirmed",
                "message": "预订成功，请按时到达"
            }
        except Exception as e:
            logger.error(f"Error making reservation: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def search_cinemas(self, city: str, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """搜索电影院"""
        # 大众点评主要做餐厅，电影院建议用猫眼
        logger.warning("Dianping is not suitable for cinema search, use Maoyan instead")
        return []

    def get_movie_showtimes(self, cinema_id: str, movie_id: str, show_date: date) -> List[Dict[str, Any]]:
        """获取电影场次"""
        return []

    def get_available_seats(self, showtime_id: str) -> List[Dict[str, Any]]:
        """获取可选座位"""
        return []

    def book_movie_tickets(
        self,
        showtime_id: str,
        seat_ids: List[str],
        user_name: str,
        phone: str
    ) -> Dict[str, Any]:
        """预订电影票"""
        return {"error": "Dianping does not support movie booking"}

    def _mock_restaurant_search(self, city: str, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Mock 餐厅搜索结果"""
        mock_restaurants = [
            {
                "id": "rest_001",
                "name": f"{city}浪漫西餐厅",
                "cuisine": "西餐",
                "rating": 4.8,
                "price_range": 3,
                "address": f"{city}市中心商业街 1 号",
                "phone": "010-12345678",
                "image": "https://example.com/restaurant1.jpg",
                "features": ["浪漫", "适合约会", "有包间"]
            },
            {
                "id": "rest_002",
                "name": f"{city}日式料理店",
                "cuisine": "日料",
                "rating": 4.6,
                "price_range": 4,
                "address": f"{city}朝阳区某某路 2 号",
                "phone": "010-87654321",
                "image": "https://example.com/restaurant2.jpg",
                "features": ["安静", "精致", "适合约会"]
            },
            {
                "id": "rest_003",
                "name": f"{city}意大利餐厅",
                "cuisine": "意大利菜",
                "rating": 4.5,
                "price_range": 3,
                "address": f"{city}海淀区某某街 3 号",
                "phone": "010-11223344",
                "image": "https://example.com/restaurant3.jpg",
                "features": ["正宗", "温馨", "有露台"]
            }
        ]

        # 根据筛选条件过滤
        if filters:
            if filters.get("cuisine"):
                mock_restaurants = [r for r in mock_restaurants if filters["cuisine"] in r["cuisine"]]
            if filters.get("rating_min"):
                mock_restaurants = [r for r in mock_restaurants if r["rating"] >= filters["rating_min"]]

        return mock_restaurants

    def _mock_restaurant_details(self, restaurant_id: str) -> Optional[Dict[str, Any]]:
        """Mock 餐厅详情"""
        return {
            "id": restaurant_id,
            "name": "浪漫西餐厅",
            "cuisine": "西餐",
            "rating": 4.8,
            "review_count": 1250,
            "price_range": 3,
            "average_cost": 200,
            "address": "市中心商业街 1 号",
            "phone": "010-12345678",
            "business_hours": {
                "monday": "10:00-22:00",
                "tuesday": "10:00-22:00",
                "wednesday": "10:00-22:00",
                "thursday": "10:00-22:00",
                "friday": "10:00-23:00",
                "saturday": "10:00-23:00",
                "sunday": "10:00-22:00"
            },
            "features": ["浪漫", "适合约会", "有包间", "可预订"],
            "images": [
                "https://example.com/restaurant1.jpg",
                "https://example.com/restaurant1_interior.jpg"
            ],
            "menu_highlights": ["牛排", "意面", "沙拉", "甜点"],
            "reservation_available": True,
            "description": "这是一家浪漫的西餐厅，适合情侣约会和特殊纪念日庆祝。"
        }


class MaoyanProvider(ReservationProvider):
    """猫眼 API 提供者（电影院选座）"""

    BASE_URL = "https://api.maoyan.com/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("MAOYAN_API_KEY")
        if not self.api_key:
            logger.warning("Maoyan API key not configured")

    def search_restaurants(self, city: str, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """猫眼主要做电影，不支持餐厅搜索"""
        logger.warning("Maoyan does not support restaurant search")
        return []

    def get_restaurant_details(self, restaurant_id: str) -> Optional[Dict[str, Any]]:
        """猫眼不支持餐厅"""
        return None

    def make_restaurant_reservation(
        self,
        restaurant_id: str,
        user_name: str,
        phone: str,
        party_size: int,
        reservation_time: datetime
    ) -> Dict[str, Any]:
        """猫眼不支持餐厅预订"""
        return {"error": "Maoyan does not support restaurant reservation"}

    def search_cinemas(self, city: str, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        搜索电影院

        Args:
            city: 城市名
            filters: 筛选条件 {district, brand, ...}

        Returns:
            电影院列表
        """
        if not self.api_key:
            return []

        try:
            url = f"{self.BASE_URL}/cinema/search"
            params = {
                "city": city,
                "apikey": self.api_key,
                "limit": 20
            }

            if filters:
                if filters.get("district"):
                    params["district"] = filters["district"]
                if filters.get("brand"):
                    params["brand"] = filters["brand"]

            # 实际使用时需要添加签名
            # response = requests.get(url, params=params, timeout=10)
            # response.raise_for_status()
            # data = response.json()

            logger.info(f"Search cinemas in {city} with filters: {filters}")
            return self._mock_cinema_search(city, filters)
        except Exception as e:
            logger.error(f"Error searching cinemas: {e}")
            return []

    def get_movie_showtimes(self, cinema_id: str, movie_id: str, show_date: date) -> List[Dict[str, Any]]:
        """
        获取电影场次

        Args:
            cinema_id: 电影院 ID
            movie_id: 电影 ID
            show_date: 放映日期

        Returns:
            场次列表
        """
        if not self.api_key:
            return []

        try:
            url = f"{self.BASE_URL}/movie/showtimes"
            params = {
                "cinema_id": cinema_id,
                "movie_id": movie_id,
                "date": show_date.isoformat(),
                "apikey": self.api_key
            }

            # 实际使用时需要添加签名
            # response = requests.get(url, params=params, timeout=10)
            # response.raise_for_status()
            # data = response.json()

            logger.info(f"Get showtimes for cinema {cinema_id} movie {movie_id} on {show_date}")
            return self._mock_showtimes(cinema_id, movie_id, show_date)
        except Exception as e:
            logger.error(f"Error fetching showtimes: {e}")
            return []

    def get_available_seats(self, showtime_id: str) -> List[Dict[str, Any]]:
        """
        获取可选座位

        Args:
            showtime_id: 场次 ID

        Returns:
            座位列表
        """
        if not self.api_key:
            return []

        try:
            url = f"{self.BASE_URL}/showtime/{showtime_id}/seats"
            params = {"apikey": self.api_key}

            # 实际使用时需要添加签名
            # response = requests.get(url, params=params, timeout=10)
            # response.raise_for_status()
            # data = response.json()

            logger.info(f"Get available seats for showtime {showtime_id}")
            return self._mock_available_seats(showtime_id)
        except Exception as e:
            logger.error(f"Error fetching available seats: {e}")
            return []

    def book_movie_tickets(
        self,
        showtime_id: str,
        seat_ids: List[str],
        user_name: str,
        phone: str
    ) -> Dict[str, Any]:
        """
        预订电影票

        Args:
            showtime_id: 场次 ID
            seat_ids: 座位 ID 列表
            user_name: 预订人姓名
            phone: 联系电话

        Returns:
            预订结果
        """
        if not self.api_key:
            return {"error": "API not configured"}

        try:
            url = f"{self.BASE_URL}/ticket/book"
            data = {
                "showtime_id": showtime_id,
                "seat_ids": seat_ids,
                "user_name": user_name,
                "phone": phone,
                "apikey": self.api_key
            }

            # 实际使用时需要添加签名
            # response = requests.post(url, json=data, timeout=10)
            # response.raise_for_status()
            # result = response.json()

            logger.info(f"Book movie tickets for {user_name} at showtime {showtime_id}")

            # Mock 响应
            return {
                "success": True,
                "order_id": str(uuid.uuid4()),
                "confirmation_code": f"MY{uuid.uuid4().hex[:8].upper()}",
                "showtime_id": showtime_id,
                "seat_ids": seat_ids,
                "total_price": len(seat_ids) * 50,
                "status": "confirmed",
                "message": "出票成功，请按时观影"
            }
        except Exception as e:
            logger.error(f"Error booking tickets: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _mock_cinema_search(self, city: str, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Mock 电影院搜索结果"""
        mock_cinemas = [
            {
                "id": "cinema_001",
                "name": f"{city}万达影城 (市中心店)",
                "brand": "万达",
                "rating": 4.8,
                "address": f"{city}市中心商业街",
                "phone": "010-12345678",
                "features": ["IMAX", "杜比全景声", "情侣座"],
                "distance": 1.5
            },
            {
                "id": "cinema_002",
                "name": f"{city}UME 影城",
                "brand": "UME",
                "rating": 4.6,
                "address": f"{city}朝阳区某某购物中心",
                "phone": "010-87654321",
                "features": ["激光 IMAX", "VIP 厅", "按摩座椅"],
                "distance": 3.2
            },
            {
                "id": "cinema_003",
                "name": f"{city}百丽宫影城",
                "brand": "百丽宫",
                "rating": 4.7,
                "address": f"{city}海淀区某某广场",
                "phone": "010-11223344",
                "features": ["艺术电影", "高品质音效"],
                "distance": 5.0
            }
        ]

        return mock_cinemas

    def _mock_showtimes(self, cinema_id: str, movie_id: str, show_date: date) -> List[Dict[str, Any]]:
        """Mock 电影场次"""
        return [
            {
                "showtime_id": f"st_{cinema_id}_{movie_id}_001",
                "movie_id": movie_id,
                "cinema_id": cinema_id,
                "start_time": f"{show_date.isoformat()} 10:30",
                "end_time": f"{show_date.isoformat()} 12:30",
                "hall": "1 号厅",
                "hall_type": "IMAX",
                "language": "国语",
                "price": 50,
                "seats_total": 100,
                "seats_available": 45
            },
            {
                "showtime_id": f"st_{cinema_id}_{movie_id}_002",
                "movie_id": movie_id,
                "cinema_id": cinema_id,
                "start_time": f"{show_date.isoformat()} 14:00",
                "end_time": f"{show_date.isoformat()} 16:00",
                "hall": "2 号厅",
                "hall_type": "普通厅",
                "language": "国语",
                "price": 45,
                "seats_total": 80,
                "seats_available": 30
            },
            {
                "showtime_id": f"st_{cinema_id}_{movie_id}_003",
                "movie_id": movie_id,
                "cinema_id": cinema_id,
                "start_time": f"{show_date.isoformat()} 19:30",
                "end_time": f"{show_date.isoformat()} 21:30",
                "hall": "3 号厅",
                "hall_type": "情侣厅",
                "language": "国语",
                "price": 60,
                "seats_total": 40,
                "seats_available": 12
            }
        ]

    def _mock_available_seats(self, showtime_id: str) -> List[Dict[str, Any]]:
        """Mock 可选座位"""
        # 生成座位图
        seats = []
        rows = 8
        cols = 10

        for row in range(rows):
            for col in range(cols):
                seat_id = f"{chr(65 + row)}{col + 1}"
                # 随机标记一些座位为已售
                is_available = (row + col) % 3 != 0
                seats.append({
                    "seat_id": seat_id,
                    "row": row + 1,
                    "column": col + 1,
                    "type": "normal" if row < 6 else "vip",
                    "price": 50 if row < 6 else 70,
                    "available": is_available,
                    "label": f"{chr(65 + row)}排{col + 1}座"
                })

        return [s for s in seats if s["available"]]


class MockReservationProvider(ReservationProvider):
    """Mock 预订服务提供者（用于测试和降级）"""

    def search_restaurants(self, city: str, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Mock 餐厅搜索"""
        return [
            {
                "id": "rest_mock_001",
                "name": f"{city} Mock 浪漫餐厅",
                "cuisine": "西餐",
                "rating": 4.8,
                "price_range": 3,
                "address": f"{city}Mock 路 1 号",
                "phone": "010-00000000",
                "features": ["浪漫", "适合约会"],
                "reservation_available": True
            },
            {
                "id": "rest_mock_002",
                "name": f"{city} Mock 日料店",
                "cuisine": "日料",
                "rating": 4.6,
                "price_range": 4,
                "address": f"{city}Mock 路 2 号",
                "phone": "010-00000001",
                "features": ["安静", "精致"],
                "reservation_available": True
            }
        ]

    def get_restaurant_details(self, restaurant_id: str) -> Optional[Dict[str, Any]]:
        """Mock 餐厅详情"""
        return {
            "id": restaurant_id,
            "name": "Mock 餐厅",
            "cuisine": "西餐",
            "rating": 4.8,
            "price_range": 3,
            "address": "Mock 路 1 号",
            "phone": "010-00000000",
            "business_hours": {"monday": "10:00-22:00"},
            "features": ["浪漫", "适合约会"],
            "reservation_available": True
        }

    def make_restaurant_reservation(
        self,
        restaurant_id: str,
        user_name: str,
        phone: str,
        party_size: int,
        reservation_time: datetime
    ) -> Dict[str, Any]:
        """Mock 餐厅预订"""
        return {
            "success": True,
            "reservation_id": str(uuid.uuid4()),
            "confirmation_code": f"MOCK{uuid.uuid4().hex[:8].upper()}",
            "restaurant_id": restaurant_id,
            "user_name": user_name,
            "party_size": party_size,
            "reservation_time": reservation_time.isoformat(),
            "status": "confirmed",
            "message": "Mock 预订成功"
        }

    def search_cinemas(self, city: str, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Mock 电影院搜索"""
        return [
            {
                "id": "cinema_mock_001",
                "name": f"{city} Mock 影城",
                "brand": "Mock",
                "rating": 4.8,
                "address": f"{city}Mock 商业街",
                "features": ["IMAX", "情侣座"],
                "distance": 1.0
            }
        ]

    def get_movie_showtimes(self, cinema_id: str, movie_id: str, show_date: date) -> List[Dict[str, Any]]:
        """Mock 电影场次"""
        return [
            {
                "showtime_id": f"st_mock_001",
                "movie_id": movie_id,
                "cinema_id": cinema_id,
                "start_time": f"{show_date.isoformat()} 19:30",
                "end_time": f"{show_date.isoformat()} 21:30",
                "hall": "1 号厅",
                "hall_type": "IMAX",
                "language": "国语",
                "price": 50,
                "seats_total": 100,
                "seats_available": 50
            }
        ]

    def get_available_seats(self, showtime_id: str) -> List[Dict[str, Any]]:
        """Mock 可选座位"""
        return [
            {"seat_id": "F7", "row": 6, "column": 7, "type": "normal", "price": 50, "available": True, "label": "F 排 7 座"},
            {"seat_id": "F8", "row": 6, "column": 8, "type": "normal", "price": 50, "available": True, "label": "F 排 8 座"},
            {"seat_id": "G7", "row": 7, "column": 7, "type": "normal", "price": 50, "available": True, "label": "G 排 7 座"},
            {"seat_id": "G8", "row": 7, "column": 8, "type": "normal", "price": 50, "available": True, "label": "G 排 8 座"},
        ]

    def book_movie_tickets(
        self,
        showtime_id: str,
        seat_ids: List[str],
        user_name: str,
        phone: str
    ) -> Dict[str, Any]:
        """Mock 电影票预订"""
        return {
            "success": True,
            "order_id": str(uuid.uuid4()),
            "confirmation_code": f"MOCK{uuid.uuid4().hex[:8].upper()}",
            "showtime_id": showtime_id,
            "seat_ids": seat_ids,
            "total_price": len(seat_ids) * 50,
            "status": "confirmed",
            "message": "Mock 出票成功"
        }


class ReservationService:
    """预订服务统一入口"""

    def __init__(self, restaurant_provider: Optional[str] = None, cinema_provider: Optional[str] = None):
        """
        初始化预订服务

        Args:
            restaurant_provider: 餐厅服务提供商 (dianping, mock)
            cinema_provider: 电影院服务提供商 (maoyan, mock)
        """
        self.restaurant_provider_name = restaurant_provider or os.getenv("RESERVATION_RESTAURANT_PROVIDER", "mock")
        self.cinema_provider_name = cinema_provider or os.getenv("RESERVATION_CINEMA_PROVIDER", "mock")

        self.restaurant_provider = self._create_restaurant_provider(self.restaurant_provider_name)
        self.cinema_provider = self._create_cinema_provider(self.cinema_provider_name)

    def _create_restaurant_provider(self, provider_name: str) -> ReservationProvider:
        """创建餐厅服务提供者"""
        if provider_name == "dianping":
            return DianpingProvider()
        else:
            return MockReservationProvider()

    def _create_cinema_provider(self, provider_name: str) -> ReservationProvider:
        """创建电影院服务提供者"""
        if provider_name == "maoyan":
            return MaoyanProvider()
        else:
            return MockReservationProvider()

    # 餐厅相关方法

    def search_restaurants(self, city: str, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """搜索餐厅"""
        return self.restaurant_provider.search_restaurants(city, filters)

    def get_restaurant_details(self, restaurant_id: str) -> Optional[Dict[str, Any]]:
        """获取餐厅详情"""
        return self.restaurant_provider.get_restaurant_details(restaurant_id)

    def make_restaurant_reservation(
        self,
        restaurant_id: str,
        user_name: str,
        phone: str,
        party_size: int,
        reservation_time: datetime
    ) -> Dict[str, Any]:
        """预订餐厅"""
        return self.restaurant_provider.make_restaurant_reservation(
            restaurant_id, user_name, phone, party_size, reservation_time
        )

    # 电影院相关方法

    def search_cinemas(self, city: str, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """搜索电影院"""
        return self.cinema_provider.search_cinemas(city, filters)

    def get_movie_showtimes(self, cinema_id: str, movie_id: str, show_date: date) -> List[Dict[str, Any]]:
        """获取电影场次"""
        return self.cinema_provider.get_movie_showtimes(cinema_id, movie_id, show_date)

    def get_available_seats(self, showtime_id: str) -> List[Dict[str, Any]]:
        """获取可选座位"""
        return self.cinema_provider.get_available_seats(showtime_id)

    def book_movie_tickets(
        self,
        showtime_id: str,
        seat_ids: List[str],
        user_name: str,
        phone: str
    ) -> Dict[str, Any]:
        """预订电影票"""
        return self.cinema_provider.book_movie_tickets(showtime_id, seat_ids, user_name, phone)

    def switch_restaurant_provider(self, provider_name: str):
        """切换餐厅服务提供者"""
        self.restaurant_provider = self._create_restaurant_provider(provider_name)
        self.restaurant_provider_name = provider_name
        logger.info(f"Switched restaurant provider to {provider_name}")

    def switch_cinema_provider(self, provider_name: str):
        """切换电影院服务提供者"""
        self.cinema_provider = self._create_cinema_provider(provider_name)
        self.cinema_provider_name = provider_name
        logger.info(f"Switched cinema provider to {provider_name}")


# 全局服务实例
reservation_service = ReservationService()
