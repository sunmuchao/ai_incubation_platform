"""
地理分布分析服务 - P7 核心能力

提供 IP 地理位置解析、地域分布统计、地图可视化数据生成
"""
import os
import socket
import struct
import logging
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


@dataclass
class GeoLocation:
    """地理位置信息"""
    ip: str
    country: str = "Unknown"
    country_code: str = "Unknown"
    region: str = "Unknown"
    city: str = "Unknown"
    latitude: float = 0.0
    longitude: float = 0.0
    timezone: str = "UTC"
    isp: str = "Unknown"


@dataclass
class GeoDistribution:
    """地域分布统计"""
    country_distribution: Dict[str, int] = field(default_factory=dict)
    region_distribution: Dict[str, int] = field(default_factory=dict)
    city_distribution: Dict[str, int] = field(default_factory=dict)
    total_ips: int = 0
    unique_countries: int = 0
    unique_regions: int = 0
    unique_cities: int = 0


class IPGeolocationDB:
    """
    IP 地理位置数据库

    支持多种数据源：
    - MaxMind GeoIP2（推荐）
    - IP2Location
    - 离线 IP 库
    - 在线 API（ip-api.com, ipinfo.io）
    """

    def __init__(self, data_source: str = "offline"):
        """
        初始化 IP 地理位置数据库

        Args:
            data_source: 数据源类型 ("maxmind", "ip2location", "offline", "api")
        """
        self.data_source = data_source
        self._db_path = os.getenv("GEOIP_DB_PATH", "data/geoip")
        self._api_key = os.getenv("IPAPI_KEY")  # ip-api.com 或 ipinfo.io 的 API key

        # 离线 IP 库数据（简化版本，用于演示）
        self._ip_ranges = self._load_offline_ip_ranges()

    def _load_offline_ip_ranges(self) -> List[Dict]:
        """加载离线 IP 范围数据（简化版本）"""
        # 这里是一些常见的 IP 范围示例
        # 实际应用中应该加载完整的 IP 地理位置库
        return [
            # 中国大陆 IP 段示例
            {"start": "1.0.1.0", "end": "1.0.32.255", "country": "China", "country_code": "CN", "region": " Guangdong", "city": "Guangzhou"},
            {"start": "1.1.0.0", "end": "1.1.0.255", "country": "China", "country_code": "CN", "region": "Fujian", "city": "Xiamen"},
            {"start": "14.0.0.0", "end": "14.255.255.255", "country": "China", "country_code": "CN", "region": "Various", "city": "Various"},
            # 美国 IP 段示例
            {"start": "3.0.0.0", "end": "3.255.255.255", "country": "United States", "country_code": "US", "region": "Various", "city": "Various"},
            {"start": "4.0.0.0", "end": "4.255.255.255", "country": "United States", "country_code": "US", "region": "Various", "city": "Various"},
            # 日本 IP 段示例
            {"start": "14.192.0.0", "end": "14.223.255.255", "country": "Japan", "country_code": "JP", "region": "Tokyo", "city": "Tokyo"},
            # 韩国 IP 段示例
            {"start": "1.112.0.0", "end": "1.113.255.255", "country": "South Korea", "country_code": "KR", "region": "Seoul", "city": "Seoul"},
            # 欧洲 IP 段示例
            {"start": "2.0.0.0", "end": "2.255.255.255", "country": "United Kingdom", "country_code": "GB", "region": "England", "city": "London"},
        ]

    def _ip_to_int(self, ip: str) -> int:
        """将 IP 地址转换为整数"""
        try:
            return struct.unpack("!I", socket.inet_aton(ip))[0]
        except Exception:
            return 0

    def lookup(self, ip: str) -> GeoLocation:
        """
        查找 IP 的地理位置

        Args:
            ip: IP 地址

        Returns:
            地理位置信息
        """
        # 本地 IP 地址
        if ip in ["127.0.0.1", "localhost", "::1"]:
            return GeoLocation(
                ip=ip,
                country="Localhost",
                country_code="XX",
                city="Local"
            )

        # 根据数据源选择查找方式
        if self.data_source == "api":
            return self._lookup_by_api(ip)
        else:
            return self._lookup_offline(ip)

    def _lookup_offline(self, ip: str) -> GeoLocation:
        """离线查找"""
        ip_int = self._ip_to_int(ip)

        for ip_range in self._ip_ranges:
            start_int = self._ip_to_int(ip_range["start"])
            end_int = self._ip_to_int(ip_range["end"])

            if start_int <= ip_int <= end_int:
                return GeoLocation(
                    ip=ip,
                    country=ip_range["country"],
                    country_code=ip_range["country_code"],
                    region=ip_range.get("region", "Unknown"),
                    city=ip_range.get("city", "Unknown")
                )

        # 未找到匹配，返回未知
        return GeoLocation(
            ip=ip,
            country="Unknown",
            country_code="XX",
            city="Unknown"
        )

    def _lookup_by_api(self, ip: str) -> GeoLocation:
        """通过在线 API 查找"""
        try:
            import httpx

            # 使用 ip-api.com（免费，无需 API key）
            response = httpx.get(
                f"http://ip-api.com/json/{ip}",
                timeout=5
            )
            data = response.json()

            if data.get("status") == "success":
                return GeoLocation(
                    ip=ip,
                    country=data.get("country", "Unknown"),
                    country_code=data.get("countryCode", "XX"),
                    region=data.get("regionName", "Unknown"),
                    city=data.get("city", "Unknown"),
                    latitude=data.get("lat", 0.0),
                    longitude=data.get("lon", 0.0),
                    timezone=data.get("timezone", "UTC"),
                    isp=data.get("isp", "Unknown")
                )

        except Exception as e:
            logger.warning(f"API lookup failed for {ip}: {e}")

        # API 失败时回退到离线查找
        return self._lookup_offline(ip)

    def lookup_batch(self, ips: List[str]) -> List[GeoLocation]:
        """批量查找 IP 地理位置"""
        return [self.lookup(ip) for ip in ips]


class GeoDistributionAnalyzer:
    """
    地域分布分析器

    统计和分析地域分布数据
    """

    def __init__(self, geo_db: IPGeolocationDB):
        self._geo_db = geo_db
        self._ip_cache: Dict[str, GeoLocation] = {}

    def analyze_distribution(
        self,
        ips: List[str],
        dimension: str = "country"
    ) -> GeoDistribution:
        """
        分析地域分布

        Args:
            ips: IP 地址列表
            dimension: 分析维度 ("country", "region", "city")

        Returns:
            地域分布统计
        """
        country_dist: Dict[str, int] = defaultdict(int)
        region_dist: Dict[str, int] = defaultdict(int)
        city_dist: Dict[str, int] = defaultdict(int)

        countries = set()
        regions = set()
        cities = set()

        for ip in ips:
            # 使用缓存
            if ip not in self._ip_cache:
                self._ip_cache[ip] = self._geo_db.lookup(ip)

            location = self._ip_cache[ip]

            country_dist[location.country] += 1
            region_dist[f"{location.country}-{location.region}"] += 1
            city_dist[f"{location.country}-{location.region}-{location.city}"] += 1

            countries.add(location.country)
            regions.add(location.region)
            cities.add(location.city)

        return GeoDistribution(
            country_distribution=dict(country_dist),
            region_distribution=dict(region_dist),
            city_distribution=dict(city_dist),
            total_ips=len(ips),
            unique_countries=len(countries),
            unique_regions=len(regions),
            unique_cities=len(cities)
        )

    def get_top_regions(self, distribution: GeoDistribution, limit: int = 10) -> List[Dict]:
        """获取 Top 地区"""
        sorted_regions = sorted(
            distribution.country_distribution.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        return [
            {"region": region, "count": count, "percentage": round(count / distribution.total_ips * 100, 2)}
            for region, count in sorted_regions
        ]

    def get_geo_json_data(
        self,
        distribution: GeoDistribution,
        geo_type: str = "country"
    ) -> Dict:
        """
        生成地图可视化数据（GeoJSON 格式）

        Args:
            distribution: 地域分布数据
            geo_type: 地理类型 ("country", "region")

        Returns:
            GeoJSON 格式的数据
        """
        # 国家代码映射
        country_codes = {
            "China": "CN",
            "United States": "US",
            "Japan": "JP",
            "South Korea": "KR",
            "United Kingdom": "GB",
            "Germany": "DE",
            "France": "FR",
            "India": "IN",
            "Brazil": "BR",
            "Australia": "AU",
            "Canada": "CA",
            "Russia": "RU",
            "Unknown": "XX"
        }

        features = []
        for country, count in distribution.country_distribution.items():
            country_code = country_codes.get(country, "XX")
            features.append({
                "type": "Feature",
                "properties": {
                    "name": country,
                    "code": country_code,
                    "value": count,
                    "percentage": round(count / distribution.total_ips * 100, 2) if distribution.total_ips > 0 else 0
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": self._get_country_centroid(country_code)
                }
            })

        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "total_ips": distribution.total_ips,
                "unique_countries": distribution.unique_countries,
                "geo_type": geo_type
            }
        }

    def _get_country_centroid(self, country_code: str) -> Tuple[float, float]:
        """获取国家中心点坐标（简化版本）"""
        centroids = {
            "CN": (104.1954, 35.8617),
            "US": (-95.7129, 37.0902),
            "JP": (138.2529, 36.2048),
            "KR": (127.7669, 35.9078),
            "GB": (-2.0, 54.0),
            "DE": (10.4515, 51.1657),
            "FR": (2.2137, 46.2276),
            "IN": (78.9629, 20.5937),
            "BR": (-53.0975, -14.235),
            "AU": (133.7751, -25.2744),
            "CA": (-106.3468, 56.1304),
            "RU": (105.3188, 61.524),
            "XX": (0.0, 0.0)
        }
        return centroids.get(country_code, centroids["XX"])


class GeoAnalyticsService:
    """
    地理分析服务

    整合 IP 地理位置查询和分布分析
    """

    def __init__(self):
        self._geo_db = IPGeolocationDB()
        self._analyzer = GeoDistributionAnalyzer(self._geo_db)

        # 存储事件地理位置数据
        self._event_geo_data: Dict[str, GeoLocation] = {}

    def lookup_ip(self, ip: str) -> GeoLocation:
        """查询单个 IP 的地理位置"""
        return self._geo_db.lookup(ip)

    def lookup_batch(self, ips: List[str]) -> List[GeoLocation]:
        """批量查询 IP 地理位置"""
        return self._geo_db.lookup_batch(ips)

    def record_event_location(self, event_id: str, ip: str):
        """记录事件的地理位置"""
        location = self._geo_db.lookup(ip)
        self._event_geo_data[event_id] = location

    def get_event_location(self, event_id: str) -> Optional[GeoLocation]:
        """获取事件的地理位置"""
        return self._event_geo_data.get(event_id)

    def analyze_traffic_distribution(
        self,
        event_ips: List[str],
        dimension: str = "country"
    ) -> Dict[str, Any]:
        """
        分析流量地域分布

        Args:
            event_ips: 事件 IP 列表
            dimension: 分析维度

        Returns:
            分布分析结果
        """
        distribution = self._analyzer.analyze_distribution(event_ips, dimension)

        return {
            "summary": {
                "total_ips": distribution.total_ips,
                "unique_countries": distribution.unique_countries,
                "unique_regions": distribution.unique_regions,
                "unique_cities": distribution.unique_cities
            },
            "country_distribution": distribution.country_distribution,
            "region_distribution": distribution.region_distribution,
            "city_distribution": distribution.city_distribution,
            "top_regions": self._analyzer.get_top_regions(distribution, limit=20),
            "map_data": self._analyzer.get_geo_json_data(distribution, dimension)
        }

    def get_china_map_data(self, event_ips: List[str]) -> Dict[str, Any]:
        """
        生成中国地图数据

        Args:
            event_ips: 事件 IP 列表

        Returns:
            中国地图数据
        """
        distribution = self._analyzer.analyze_distribution(event_ips, "region")

        # 筛选中国地区数据
        china_regions = {}
        for key, count in distribution.region_distribution.items():
            if "China" in key:
                region_name = key.replace("China-", "")
                china_regions[region_name] = count

        # 生成省份坐标
        province_coords = {
            "Beijing": (116.4074, 39.9042),
            "Shanghai": (121.4737, 31.2304),
            "Guangdong": (113.2644, 23.1291),
            "Shenzhen": (114.0579, 22.5431),
            "Zhejiang": (120.1551, 30.2741),
            "Jiangsu": (118.7969, 32.0603),
            "Fujian": (119.2965, 26.0745),
            "Sichuan": (104.0665, 30.5728),
            "Hubei": (114.3054, 30.5928),
            "Hunan": (112.9388, 28.2282),
            "Anhui": (117.2830, 31.8612),
            "Henan": (113.6253, 34.7466),
            "Shandong": (117.0000, 36.6667),
            "Hebei": (114.5149, 38.0428),
            "Liaoning": (123.4315, 41.8057),
            "Shaanxi": (108.9398, 34.3416),
            "Yunnan": (102.7125, 25.0434),
            "Guizhou": (106.6302, 26.6477),
            "Chongqing": (106.5516, 29.5647),
            "Tianjin": (117.2008, 39.0842),
        }

        features = []
        for region, count in china_regions.items():
            coords = province_coords.get(region, (105.0, 35.0))
            features.append({
                "type": "Feature",
                "properties": {
                    "name": region,
                    "value": count
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": coords
                }
            })

        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "total_china_ips": sum(china_regions.values()),
                "unique_provinces": len(china_regions)
            }
        }

    def get_geo_insights(self, event_ips: List[str]) -> List[Dict[str, Any]]:
        """
        生成地理洞察

        Args:
            event_ips: 事件 IP 列表

        Returns:
            地理洞察列表
        """
        distribution = self._analyzer.analyze_distribution(event_ips)
        insights = []

        # 洞察 1: 主要流量来源
        if distribution.country_distribution:
            top_country = max(distribution.country_distribution.items(), key=lambda x: x[1])
            insights.append({
                "type": "primary_source",
                "title": "主要流量来源",
                "content": f"{top_country[0]} 是最大的流量来源，占比 {round(top_country[1]/distribution.total_ips*100, 1)}%",
                "data": {"country": top_country[0], "count": top_country[1]}
            })

        # 洞察 2: 地理集中度
        if distribution.unique_countries <= 3 and distribution.total_ips > 10:
            insights.append({
                "type": "concentration",
                "title": "地理集中度较高",
                "content": f"流量来自 {distribution.unique_countries} 个国家/地区，建议拓展更多地域市场",
                "data": {"unique_countries": distribution.unique_countries}
            })

        # 洞察 3: 国际化程度
        if distribution.unique_countries >= 10:
            insights.append({
                "type": "internationalization",
                "title": "高度国际化",
                "content": f"流量覆盖 {distribution.unique_countries} 个国家/地区，具有良好的国际化特征",
                "data": {"unique_countries": distribution.unique_countries}
            })

        return insights


# 全局地理分析服务实例
geo_analytics_service = GeoAnalyticsService()
