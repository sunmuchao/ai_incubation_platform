"""
缓存模块

提供多层缓存策略，用于提升匹配查询性能和降低数据库压力。
"""
from cache.cache_manager import cache_manager, CacheManager

__all__ = ["cache_manager", "CacheManager"]
