"""
外部服务集成模块

提供高德地图、极光推送、短信服务等外部 API 的集成
"""
from integration.amap_client import AMapClient, get_amap_client
from integration.jpush_client import JPushClient, get_jpush_client

__all__ = [
    "AMapClient",
    "get_amap_client",
    "JPushClient",
    "get_jpush_client",
]
