"""
Skill 缓存机制测试

测试 SkillCacheManager 和相关功能：
- 缓存存取
- TTL 管理
- 缓存失效
- 统计信息
- 装饰器功能
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
import asyncio
import hashlib
import json

from agent.skills.cache import (
    SkillCacheConfig,
    SkillCacheManager,
    get_cache_manager,
    cache_skill_result,
    invalidate_skill_cache
)


class TestSkillCacheConfig:
    """缓存配置测试"""

    def test_default_ttl(self):
        """测试默认 TTL"""
        assert SkillCacheConfig.DEFAULT_TTL == 300

    def test_skill_cache_config_exists(self):
        """测试 Skill 缓存配置存在"""
        assert len(SkillCacheConfig.SKILL_CACHE_CONFIG) >= 5

    def test_risk_control_ttl(self):
        """测试风控 TTL"""
        assert SkillCacheConfig.SKILL_CACHE_CONFIG["risk_control"] == 600

    def test_cache_key_prefix(self):
        """测试缓存键前缀"""
        assert SkillCacheConfig.CACHE_KEY_PREFIX == "skill_cache:"

    def test_max_cache_entries(self):
        """测试最大缓存条目数"""
        assert SkillCacheConfig.MAX_CACHE_ENTRIES == 1000

    def test_safety_guardian_ttl(self):
        """测试安全守护 TTL"""
        assert SkillCacheConfig.SKILL_CACHE_CONFIG["safety_guardian"] == 30

    def test_emotion_translator_ttl(self):
        """测试情感翻译器 TTL"""
        assert SkillCacheConfig.SKILL_CACHE_CONFIG["emotion_translator"] == 60


class TestSkillCacheManager:
    """缓存管理器测试"""

    def test_manager_initialization(self):
        """测试管理器初始化"""
        manager = SkillCacheManager()
        assert manager._cache == {}
        assert manager._cache_stats["hits"] == 0
        assert manager._cache_stats["misses"] == 0

    def test_generate_cache_key(self):
        """测试缓存键生成"""
        manager = SkillCacheManager()
        key = manager._generate_cache_key("test_skill", {"user_id": "123"})

        assert key.startswith("skill_cache:test_skill:")
        assert len(key) > 20

    def test_generate_cache_key_consistency(self):
        """测试缓存键一致性"""
        manager = SkillCacheManager()
        key1 = manager._generate_cache_key("test_skill", {"user_id": "123"})
        key2 = manager._generate_cache_key("test_skill", {"user_id": "123"})

        assert key1 == key2

    def test_generate_cache_key_different_params(self):
        """测试不同参数的缓存键"""
        manager = SkillCacheManager()
        key1 = manager._generate_cache_key("test_skill", {"user_id": "123"})
        key2 = manager._generate_cache_key("test_skill", {"user_id": "456"})

        assert key1 != key2

    def test_get_ttl_default(self):
        """测试默认 TTL"""
        manager = SkillCacheManager()
        ttl = manager._get_ttl("unknown_skill")

        assert ttl == SkillCacheConfig.DEFAULT_TTL

    def test_get_ttl_custom(self):
        """测试自定义 TTL"""
        manager = SkillCacheManager()
        ttl = manager._get_ttl("risk_control")

        assert ttl == 600


class TestCacheGetSet:
    """缓存存取测试"""

    def test_set_and_get(self):
        """测试设置和获取"""
        manager = SkillCacheManager()
        data = {"result": "test_data"}

        manager.set("test_skill", {"user_id": "123"}, data)
        result = manager.get("test_skill", {"user_id": "123"})

        assert result == data

    def test_get_miss(self):
        """测试获取失败"""
        manager = SkillCacheManager()

        result = manager.get("test_skill", {"user_id": "123"})

        assert result is None
        assert manager._cache_stats["misses"] == 1

    def test_get_hit(self):
        """测试获取成功"""
        manager = SkillCacheManager()
        data = {"result": "test_data"}

        manager.set("test_skill", {"user_id": "123"}, data)
        result = manager.get("test_skill", {"user_id": "123"})

        assert result == data
        assert manager._cache_stats["hits"] == 1

    def test_set_with_custom_ttl(self):
        """测试自定义 TTL"""
        manager = SkillCacheManager()
        data = {"result": "test_data"}

        manager.set("test_skill", {"user_id": "123"}, data, ttl=60)

        result = manager.get("test_skill", {"user_id": "123"})
        assert result == data

    def test_get_expired(self):
        """测试过期缓存"""
        manager = SkillCacheManager()
        data = {"result": "test_data"}

        # 设置已过期的缓存
        manager.set("test_skill", {"user_id": "123"}, data, ttl=-1)

        result = manager.get("test_skill", {"user_id": "123"})

        assert result is None
        assert manager._cache_stats["evictions"] == 1


class TestCacheInvalidation:
    """缓存失效测试"""

    def test_invalidate_specific(self):
        """测试失效特定缓存"""
        manager = SkillCacheManager()
        data = {"result": "test_data"}

        manager.set("test_skill", {"user_id": "123"}, data)
        count = manager.invalidate("test_skill", {"user_id": "123"})

        assert count == 1
        assert manager.get("test_skill", {"user_id": "123"}) is None

    def test_invalidate_all_for_skill(self):
        """测试失效 Skill 所有缓存"""
        manager = SkillCacheManager()

        manager.set("test_skill", {"user_id": "123"}, {"data": 1})
        manager.set("test_skill", {"user_id": "456"}, {"data": 2})
        manager.set("other_skill", {"user_id": "123"}, {"data": 3})

        count = manager.invalidate("test_skill")

        assert count == 2
        assert manager.get("test_skill", {"user_id": "123"}) is None
        assert manager.get("test_skill", {"user_id": "456"}) is None
        assert manager.get("other_skill", {"user_id": "123"}) is not None

    def test_invalidate_nonexistent(self):
        """测试失效不存在的缓存"""
        manager = SkillCacheManager()

        count = manager.invalidate("nonexistent_skill", {"user_id": "123"})

        assert count == 0


class TestCacheStats:
    """缓存统计测试"""

    def test_get_stats_initial(self):
        """测试初始统计"""
        manager = SkillCacheManager()

        stats = manager.get_stats()

        assert stats["total_entries"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0

    def test_get_stats_with_data(self):
        """测试有数据的统计"""
        manager = SkillCacheManager()

        manager.set("test_skill", {"user_id": "123"}, {"data": 1})
        manager.get("test_skill", {"user_id": "123"})  # hit
        manager.get("test_skill", {"user_id": "456"})  # miss

        stats = manager.get_stats()

        assert stats["total_entries"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5

    def test_get_stats_with_evictions(self):
        """测试有清理的统计"""
        manager = SkillCacheManager()

        manager.set("test_skill", {"user_id": "123"}, {"data": 1}, ttl=-1)
        manager.get("test_skill", {"user_id": "123"})  # expired, eviction

        stats = manager.get_stats()

        assert stats["evictions"] == 1


class TestCacheClear:
    """缓存清空测试"""

    def test_clear_all(self):
        """测试清空所有缓存"""
        manager = SkillCacheManager()

        manager.set("test_skill", {"user_id": "123"}, {"data": 1})
        manager.set("other_skill", {"user_id": "456"}, {"data": 2})

        manager.clear()

        assert len(manager._cache) == 0

    def test_clear_stats_preserved(self):
        """测试清空后统计保留"""
        manager = SkillCacheManager()

        manager.set("test_skill", {"user_id": "123"}, {"data": 1})
        manager.get("test_skill", {"user_id": "123"})  # hit

        manager.clear()

        # 统计不因清空而重置
        assert manager._cache_stats["hits"] == 1


class TestCacheManagerSingleton:
    """缓存管理器单例测试"""

    def test_get_cache_manager_returns_instance(self):
        """测试获取缓存管理器返回实例"""
        manager = get_cache_manager()

        assert manager is not None
        assert isinstance(manager, SkillCacheManager)

    def test_get_cache_manager_singleton(self):
        """测试单例模式"""
        manager1 = get_cache_manager()
        manager2 = get_cache_manager()

        assert manager1 is manager2


class TestEvictOldest:
    """清理最旧缓存测试"""

    def test_evict_when_limit_reached(self):
        """测试达到限制时清理"""
        manager = SkillCacheManager()

        # 添加多个缓存条目
        for i in range(5):
            manager.set("test_skill", {"user_id": str(i)}, {"data": i})

        # 手动触发清理
        manager._evict_oldest()

        assert len(manager._cache) == 4
        assert manager._cache_stats["evictions"] == 1


class TestCacheSkillResultDecorator:
    """缓存装饰器测试"""

    @pytest.mark.asyncio
    async def test_decorator_caches_result(self):
        """测试装饰器缓存结果"""
        # 重置缓存管理器
        import agent.skills.cache as cache_module
        cache_module._cache_manager = None

        call_counts = {"count": 0}

        @cache_skill_result("test_skill")
        async def test_func(user_id: str):
            call_counts["count"] += 1
            return {"success": True, "data": f"result_{user_id}"}

        # 第一次调用
        result1 = await test_func(user_id="123")
        assert result1["success"] is True
        assert call_counts["count"] == 1

        # 第二次调用（应命中缓存）
        result2 = await test_func(user_id="123")
        assert result2["success"] is True
        assert call_counts["count"] == 1  # 没有增加

    @pytest.mark.asyncio
    async def test_decorator_different_params(self):
        """测试装饰器不同参数"""
        import agent.skills.cache as cache_module
        cache_module._cache_manager = None

        call_counts = {"count": 0}

        @cache_skill_result("test_skill")
        async def test_func(user_id: str):
            call_counts["count"] += 1
            return {"success": True, "data": f"result_{user_id}"}

        await test_func(user_id="123")
        await test_func(user_id="456")

        assert call_counts["count"] == 2  # 不同参数，各自调用

    @pytest.mark.asyncio
    async def test_decorator_no_cache_failed_result(self):
        """测试装饰器不缓存失败结果"""
        import agent.skills.cache as cache_module
        cache_module._cache_manager = None

        call_counts = {"count": 0}

        @cache_skill_result("test_skill")
        async def test_func(user_id: str):
            call_counts["count"] += 1
            return {"success": False, "error": "test error"}

        await test_func(user_id="123")
        await test_func(user_id="123")

        assert call_counts["count"] == 2  # 失败结果不缓存


class TestEdgeCases:
    """边界值测试"""

    def test_empty_params(self):
        """测试空参数"""
        manager = SkillCacheManager()

        key = manager._generate_cache_key("test_skill", {})
        manager.set("test_skill", {}, {"data": 1})

        result = manager.get("test_skill", {})
        assert result == {"data": 1}

    def test_large_params(self):
        """测试大参数"""
        manager = SkillCacheManager()
        large_params = {"data": "x" * 1000}

        manager.set("test_skill", large_params, {"result": 1})
        result = manager.get("test_skill", large_params)

        assert result == {"result": 1}

    def test_special_characters_in_skill_name(self):
        """测试 Skill 名称特殊字符"""
        manager = SkillCacheManager()

        manager.set("test_skill_特殊", {"user_id": "123"}, {"data": 1})
        result = manager.get("test_skill_特殊", {"user_id": "123"})

        assert result == {"data": 1}

    def test_unicode_params(self):
        """测试 Unicode 参数"""
        manager = SkillCacheManager()
        params = {"用户": "测试"}

        manager.set("test_skill", params, {"data": 1})
        result = manager.get("test_skill", params)

        assert result == {"data": 1}

    def test_concurrent_access(self):
        """测试并发访问"""
        manager = SkillCacheManager()

        # 模拟并发设置
        for i in range(10):
            manager.set("test_skill", {"user_id": str(i)}, {"data": i})

        # 验证所有缓存条目
        for i in range(10):
            result = manager.get("test_skill", {"user_id": str(i)})
            assert result == {"data": i}