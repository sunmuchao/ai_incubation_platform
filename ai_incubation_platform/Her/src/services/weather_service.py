"""
天气服务模块

支持：
1. OpenWeatherMap API（国际）
2. 和风天气 API（国内）
3. Mock 实现（用于测试）

配置项：
- WEATHER_PROVIDER: 天气服务提供商 (openweathermap, qweather, mock)
- OPENWEATHERMAP_API_KEY: OpenWeatherMap API 密钥
- QWEATHER_API_KEY: 和风天气 API 密钥
"""
import os
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
from abc import ABC, abstractmethod
from utils.logger import logger


class WeatherProvider(ABC):
    """天气服务提供者抽象基类"""

    @abstractmethod
    def get_current_weather(self, city: str) -> Optional[Dict[str, Any]]:
        """获取当前天气"""
        pass

    @abstractmethod
    def get_weather_forecast(self, city: str, days: int = 3) -> List[Dict[str, Any]]:
        """获取天气预报"""
        pass

    @abstractmethod
    def get_outfit_suggestion(self, city: str) -> Dict[str, Any]:
        """基于天气获取穿搭建议"""
        pass


class OpenWeatherMapProvider(WeatherProvider):
    """OpenWeatherMap 天气服务提供者"""

    BASE_URL = "https://api.openweathermap.org/data/2.5"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENWEATHERMAP_API_KEY")
        if not self.api_key:
            logger.warning("OpenWeatherMap API key not configured")

    def get_current_weather(self, city: str) -> Optional[Dict[str, Any]]:
        """
        获取当前天气

        Args:
            city: 城市名

        Returns:
            天气数据
        """
        if not self.api_key:
            return None

        try:
            url = f"{self.BASE_URL}/weather"
            params = {
                "q": city,
                "appid": self.api_key,
                "units": "metric",
                "lang": "zh_cn"
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            return {
                "city": city,
                "temperature": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "humidity": data["main"]["humidity"],
                "pressure": data["main"]["pressure"],
                "weather": data["weather"][0]["description"],
                "weather_icon": data["weather"][0]["icon"],
                "wind_speed": data["wind"]["speed"],
                "clouds": data.get("clouds", {}).get("all", 0),
                "provider": "openweathermap",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching weather from OpenWeatherMap: {e}")
            return None

    def get_weather_forecast(self, city: str, days: int = 3) -> List[Dict[str, Any]]:
        """
        获取天气预报

        Args:
            city: 城市名
            days: 预报天数 (1-5)

        Returns:
            天气预报列表
        """
        if not self.api_key:
            return []

        days = min(max(days, 1), 5)  # 限制 1-5 天

        try:
            url = f"{self.BASE_URL}/forecast"
            params = {
                "q": city,
                "appid": self.api_key,
                "units": "metric",
                "lang": "zh_cn"
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # 整理每日预报
            daily_forecasts = {}
            for item in data["list"]:
                dt_txt = item["dt_txt"]
                date = dt_txt.split(" ")[0]
                if date not in daily_forecasts:
                    daily_forecasts[date] = {
                        "date": date,
                        "temp_max": item["main"]["temp"],
                        "temp_min": item["main"]["temp"],
                        "weather": item["weather"][0]["description"],
                        "weather_icon": item["weather"][0]["icon"],
                        "humidity": item["main"]["humidity"],
                        "wind_speed": item["wind"]["speed"]
                    }
                else:
                    daily_forecasts[date]["temp_max"] = max(
                        daily_forecasts[date]["temp_max"], item["main"]["temp"]
                    )
                    daily_forecasts[date]["temp_min"] = min(
                        daily_forecasts[date]["temp_min"], item["main"]["temp"]
                    )

            return list(daily_forecasts.values())[:days]
        except Exception as e:
            logger.error(f"Error fetching forecast from OpenWeatherMap: {e}")
            return []

    def get_outfit_suggestion(self, city: str) -> Dict[str, Any]:
        """
        基于天气获取穿搭建议

        Args:
            city: 城市名

        Returns:
            穿搭建议
        """
        weather = self.get_current_weather(city)
        if not weather:
            return {"error": "无法获取天气数据"}

        temp = weather["temperature"]
        weather_desc = weather["weather"].lower()

        # 温度穿搭建议
        if temp < 5:
            clothing = ["厚羽绒服", "毛衣", "保暖内衣", "围巾", "手套"]
            style = "保暖优先"
        elif temp < 15:
            clothing = ["外套", "毛衣/卫衣", "长裤", "薄围巾"]
            style = "注意保暖"
        elif temp < 25:
            clothing = ["长袖 T 恤", "薄外套", "牛仔裤/休闲裤"]
            style = "舒适休闲"
        else:
            clothing = ["短袖 T 恤", "短裤/裙子", "凉鞋"]
            style = "清爽透气"

        # 天气状况建议
        accessories = []
        if "rain" in weather_desc or "drizzle" in weather_desc:
            accessories.append("雨伞")
            accessories.append("防水鞋")
        if "snow" in weather_desc:
            accessories.append("防滑鞋")
            accessories.append("厚手套")
        if "sunny" in weather_desc or "clear" in weather_desc:
            accessories.append("太阳镜")
            accessories.append("防晒霜")
        if "cloud" in weather_desc:
            accessories.append("薄外套备用")

        # 约会场景建议
        date_outfit_tips = []
        if temp < 10:
            date_outfit_tips.append("室内有暖气，建议内搭选择精致的单品")
        if "rain" in weather_desc:
            date_outfit_tips.append("雨天路滑，建议选择防滑的鞋子")
        if temp > 25:
            date_outfit_tips.append("天气较热，建议携带纸巾和小风扇")

        return {
            "city": city,
            "temperature": temp,
            "weather": weather_desc,
            "clothing": clothing,
            "style": style,
            "accessories": accessories,
            "date_outfit_tips": date_outfit_tips,
            "provider": "openweathermap"
        }


class QWeatherProvider(WeatherProvider):
    """和风天气服务提供者（中国国内）"""

    BASE_URL = "https://devapi.qweather.com/v7"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("QWEATHER_API_KEY")
        if not self.api_key:
            logger.warning("QWeather API key not configured")

    def _get_city_location(self, city: str) -> Optional[Dict[str, str]]:
        """获取城市地理位置 ID"""
        try:
            url = f"{self.BASE_URL}/city/search"
            params = {
                "location": city,
                "key": self.api_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("code") == "200" and data.get("location"):
                return data["location"][0]
            return None
        except Exception as e:
            logger.error(f"Error fetching city location: {e}")
            return None

    def get_current_weather(self, city: str) -> Optional[Dict[str, Any]]:
        """获取当前天气"""
        if not self.api_key:
            return None

        try:
            # 先获取城市 ID
            location_info = self._get_city_location(city)
            if not location_info:
                logger.warning(f"City {city} not found")
                return None

            location_id = location_info["id"]

            # 获取天气数据
            url = f"{self.BASE_URL}/weather/now"
            params = {
                "location": location_id,
                "key": self.api_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("code") != "200":
                return None

            now = data.get("now", {})

            return {
                "city": city,
                "temperature": float(now.get("temp", 0)),
                "feels_like": float(now.get("feelsLike", 0)),
                "humidity": int(now.get("humidity", 0)),
                "pressure": int(now.get("pressure", 0)),
                "weather": now.get("text", "未知"),
                "weather_icon": now.get("icon", ""),
                "wind_speed": float(now.get("windSpeed", 0)),
                "wind_direction": now.get("windDir", ""),
                "clouds": int(now.get("cloud", 0)),
                "provider": "qweather",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching weather from QWeather: {e}")
            return None

    def get_weather_forecast(self, city: str, days: int = 3) -> List[Dict[str, Any]]:
        """获取天气预报"""
        if not self.api_key:
            return []

        days = min(max(days, 1), 7)  # 和风天气支持最多 7 天

        try:
            location_info = self._get_city_location(city)
            if not location_info:
                return []

            location_id = location_info["id"]

            url = f"{self.BASE_URL}/weather/{days}d"
            params = {
                "location": location_id,
                "key": self.api_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("code") != "200":
                return []

            forecasts = []
            for daily in data.get("daily", []):
                forecasts.append({
                    "date": daily.get("fxDate", ""),
                    "temp_max": float(daily.get("tempMax", 0)),
                    "temp_min": float(daily.get("tempMin", 0)),
                    "weather": daily.get("textDay", ""),
                    "weather_icon": daily.get("iconDay", ""),
                    "humidity": int(daily.get("humidity", 0)),
                    "wind_speed": float(daily.get("windSpeedDay", 0)),
                    "wind_direction": daily.get("windDirDay", "")
                })

            return forecasts
        except Exception as e:
            logger.error(f"Error fetching forecast from QWeather: {e}")
            return []

    def get_outfit_suggestion(self, city: str) -> Dict[str, Any]:
        """基于天气获取穿搭建议"""
        weather = self.get_current_weather(city)
        if not weather:
            return {"error": "无法获取天气数据"}

        temp = weather["temperature"]
        weather_desc = weather["weather"]

        # 温度穿搭建议
        if temp < 5:
            clothing = ["厚羽绒服", "毛衣", "保暖内衣", "围巾", "手套"]
            style = "保暖优先"
        elif temp < 15:
            clothing = ["外套", "毛衣/卫衣", "长裤", "薄围巾"]
            style = "注意保暖"
        elif temp < 25:
            clothing = ["长袖 T 恤", "薄外套", "牛仔裤/休闲裤"]
            style = "舒适休闲"
        else:
            clothing = ["短袖 T 恤", "短裤/裙子", "凉鞋"]
            style = "清爽透气"

        # 天气状况建议
        accessories = []
        if "雨" in weather_desc:
            accessories.append("雨伞")
            accessories.append("防水鞋")
        if "雪" in weather_desc:
            accessories.append("防滑鞋")
            accessories.append("厚手套")
        if "晴" in weather_desc:
            accessories.append("太阳镜")
            accessories.append("防晒霜")
        if "云" in weather_desc:
            accessories.append("薄外套备用")

        # 约会场景建议
        date_outfit_tips = []
        if temp < 10:
            date_outfit_tips.append("室内有暖气，建议内搭选择精致的单品")
        if "雨" in weather_desc:
            date_outfit_tips.append("雨天路滑，建议选择防滑的鞋子")
        if temp > 25:
            date_outfit_tips.append("天气较热，建议携带纸巾和小风扇")

        return {
            "city": city,
            "temperature": temp,
            "weather": weather_desc,
            "clothing": clothing,
            "style": style,
            "accessories": accessories,
            "date_outfit_tips": date_outfit_tips,
            "provider": "qweather"
        }


class MockWeatherProvider(WeatherProvider):
    """Mock 天气服务提供者（用于测试和降级）"""

    def __init__(self):
        self.mock_data = {
            "北京市": {
                "temperature": 22,
                "feels_like": 21,
                "humidity": 45,
                "weather": "晴朗",
                "wind_speed": 2.5
            },
            "上海市": {
                "temperature": 25,
                "feels_like": 26,
                "humidity": 60,
                "weather": "多云",
                "wind_speed": 3.0
            },
            "深圳市": {
                "temperature": 28,
                "feels_like": 30,
                "humidity": 75,
                "weather": "晴热",
                "wind_speed": 2.0
            },
            "广州市": {
                "temperature": 27,
                "feels_like": 29,
                "humidity": 70,
                "weather": "多云",
                "wind_speed": 2.5
            },
        }

    def get_current_weather(self, city: str) -> Optional[Dict[str, Any]]:
        """获取模拟的当前天气"""
        mock = self.mock_data.get(city, {
            "temperature": 20,
            "feels_like": 20,
            "humidity": 50,
            "weather": "晴朗",
            "wind_speed": 2.0
        })

        return {
            "city": city,
            "temperature": mock["temperature"],
            "feels_like": mock["feels_like"],
            "humidity": mock["humidity"],
            "pressure": 1013,
            "weather": mock["weather"],
            "weather_icon": "sunny",
            "wind_speed": mock["wind_speed"],
            "clouds": 10,
            "provider": "mock",
            "timestamp": datetime.now().isoformat()
        }

    def get_weather_forecast(self, city: str, days: int = 3) -> List[Dict[str, Any]]:
        """获取模拟的天气预报"""
        forecasts = []
        base_temp = self.mock_data.get(city, {}).get("temperature", 20)

        for i in range(days):
            forecasts.append({
                "date": datetime.now().strftime(f"%Y-%m-%d"),
                "temp_max": base_temp + i * 2,
                "temp_min": base_temp - i * 2,
                "weather": "晴朗" if i % 2 == 0 else "多云",
                "weather_icon": "sunny" if i % 2 == 0 else "cloudy",
                "humidity": 50 + i * 5,
                "wind_speed": 2.0 + i * 0.5
            })

        return forecasts

    def get_outfit_suggestion(self, city: str) -> Dict[str, Any]:
        """获取模拟的穿搭建议"""
        weather = self.get_current_weather(city)
        temp = weather["temperature"]

        if temp < 5:
            clothing = ["厚羽绒服", "毛衣", "保暖内衣"]
            style = "保暖优先"
        elif temp < 15:
            clothing = ["外套", "毛衣", "长裤"]
            style = "注意保暖"
        elif temp < 25:
            clothing = ["长袖 T 恤", "薄外套", "牛仔裤"]
            style = "舒适休闲"
        else:
            clothing = ["短袖 T 恤", "短裤/裙子"]
            style = "清爽透气"

        return {
            "city": city,
            "temperature": temp,
            "weather": weather["weather"],
            "clothing": clothing,
            "style": style,
            "accessories": ["太阳镜"],
            "date_outfit_tips": ["保持清爽整洁", "选择舒适的鞋子"],
            "provider": "mock"
        }


class WeatherService:
    """天气服务统一入口"""

    def __init__(self, provider: Optional[str] = None):
        """
        初始化天气服务

        Args:
            provider: 服务提供商 (openweathermap, qweather, mock)
        """
        self.provider_name = provider or os.getenv("WEATHER_PROVIDER", "mock")
        self.provider = self._create_provider(self.provider_name)

    def _create_provider(self, provider_name: str) -> WeatherProvider:
        """创建天气服务提供者"""
        if provider_name == "openweathermap":
            return OpenWeatherMapProvider()
        elif provider_name == "qweather":
            return QWeatherProvider()
        else:
            return MockWeatherProvider()

    def get_weather(self, city: str) -> Optional[Dict[str, Any]]:
        """
        获取天气信息

        Args:
            city: 城市名

        Returns:
            天气数据
        """
        return self.provider.get_current_weather(city)

    def get_forecast(self, city: str, days: int = 3) -> List[Dict[str, Any]]:
        """
        获取天气预报

        Args:
            city: 城市名
            days: 预报天数

        Returns:
            天气预报列表
        """
        return self.provider.get_weather_forecast(city, days)

    def get_outfit_recommendation(self, city: str) -> Dict[str, Any]:
        """
        获取穿搭推荐

        Args:
            city: 城市名

        Returns:
            穿搭推荐
        """
        return self.provider.get_outfit_suggestion(city)

    def switch_provider(self, provider_name: str):
        """切换天气服务提供者"""
        self.provider = self._create_provider(provider_name)
        self.provider_name = provider_name
        logger.info(f"Switched weather provider to {provider_name}")


# 全局服务实例
weather_service = WeatherService()
