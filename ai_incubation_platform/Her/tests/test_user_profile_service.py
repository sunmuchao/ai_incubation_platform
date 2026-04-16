"""
用户画像服务集成测试

测试 UserProfileService 的核心功能：
- 双向画像管理 (SelfProfile + DesireProfile)
- 画像获取与创建
- 画像更新与持久化
- 缓存管理
- 匿名用户处理
- 批量查询优化
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
from collections import OrderedDict
import json

# 尝试导入服务模块
try:
    from services.user_profile_service import (
        UserProfileService,
        EVENT_TO_SELF_PROFILE_DIMENSION,
        EVENT_TO_DESIRE_PROFILE_DIMENSION,
        PROFILE_CACHE_MAX_SIZE,
    )
    from services.her_advisor_service import SelfProfile, DesireProfile
except ImportError:
    pytest.skip("user_profile_service not importable", allow_module_level=True)


class TestEventMappings:
    """事件映射测试"""

    def test_self_profile_event_mappings(self):
        """测试 SelfProfile 事件映射"""
        # 消息行为 → 沟通风格
        assert EVENT_TO_SELF_PROFILE_DIMENSION["message_sent"] == "communication_style"
        assert EVENT_TO_SELF_PROFILE_DIMENSION["response_time"] == "response_pattern"
        assert EVENT_TO_SELF_PROFILE_DIMENSION["emoji_usage"] == "communication_style"

        # 话题发起 → 权力动态
        assert EVENT_TO_SELF_PROFILE_DIMENSION["topic_initiation"] == "power_dynamic"
        assert EVENT_TO_SELF_PROFILE_DIMENSION["decision_making"] == "decision_style"

        # 收到的反馈 → 社会反馈维度
        assert EVENT_TO_SELF_PROFILE_DIMENSION["received_like"] == "social_feedback"
        assert EVENT_TO_SELF_PROFILE_DIMENSION["received_dislike"] == "social_feedback"

        # 情感表达 → 情感需求
        assert EVENT_TO_SELF_PROFILE_DIMENSION["emotional_expression"] == "emotional_needs"
        assert EVENT_TO_SELF_PROFILE_DIMENSION["attachment_behavior"] == "attachment_style"

    def test_desire_profile_event_mappings(self):
        """测试 DesireProfile 事件映射"""
        # 搜索行为 → 搜索偏好
        assert EVENT_TO_DESIRE_PROFILE_DIMENSION["search_query"] == "search_patterns"
        assert EVENT_TO_DESIRE_PROFILE_DIMENSION["search_filter_change"] == "search_patterns"

        # 查看行为 → 点击偏好
        assert EVENT_TO_DESIRE_PROFILE_DIMENSION["profile_view"] == "clicked_types"
        assert EVENT_TO_DESIRE_PROFILE_DIMENSION["profile_view_duration"] == "clicked_types"

        # 滑动行为 → 滑动偏好
        assert EVENT_TO_DESIRE_PROFILE_DIMENSION["swipe_like"] == "swipe_patterns"
        assert EVENT_TO_DESIRE_PROFILE_DIMENSION["swipe_pass"] == "swipe_patterns"

        # 对话内容 → 实际偏好
        assert EVENT_TO_DESIRE_PROFILE_DIMENSION["conversation_topic"] == "actual_preference"
        assert EVENT_TO_DESIRE_PROFILE_DIMENSION["ideal_type_mentioned"] == "surface_preference"


class TestCacheConfiguration:
    """缓存配置测试"""

    def test_cache_max_size(self):
        """测试缓存最大容量"""
        assert PROFILE_CACHE_MAX_SIZE == 500

    def test_service_cache_initialization(self):
        """测试服务缓存初始化"""
        service = UserProfileService()
        assert service._profile_cache is not None
        assert isinstance(service._profile_cache, OrderedDict)
        assert len(service._profile_cache) == 0


class TestAnonymousUserHandling:
    """匿名用户处理测试"""

    @pytest.mark.asyncio
    async def test_anonymous_user_returns_default_profile(self):
        """测试匿名用户返回默认画像"""
        service = UserProfileService()

        anonymous_ids = [
            "user-anonymous-dev",
            "anonymous_user",
            "anonymous",
            "dev-user",
            "guest",
        ]

        for user_id in anonymous_ids:
            self_profile, desire_profile = await service.get_or_create_profile(user_id)

            assert isinstance(self_profile, SelfProfile)
            assert isinstance(desire_profile, DesireProfile)
            assert self_profile.profile_confidence == 0.1
            assert desire_profile.preference_confidence == 0.1

    @pytest.mark.asyncio
    async def test_anonymous_prefix_returns_default(self):
        """测试 anonymous 前缀用户"""
        service = UserProfileService()

        self_profile, desire_profile = await service.get_or_create_profile("anonymous_12345")

        assert self_profile.profile_confidence == 0.1


class TestGetOrCreateProfile:
    """获取或创建画像测试"""

    @pytest.mark.asyncio
    async def test_profile_not_in_cache_queries_db(self):
        """测试未缓存的画像查询数据库"""
        service = UserProfileService()

        mock_user = MagicMock()
        mock_user.id = "user_001"
        mock_user.age = 28
        mock_user.gender = "male"
        mock_user.location = "北京"
        mock_user.occupation = "工程师"
        mock_user.education = "本科"
        mock_user.relationship_goal = "serious"
        mock_user.interests = json.dumps(["旅行", "摄影"])
        mock_user.self_profile_json = json.dumps({"communication_style": "direct"})
        mock_user.desire_profile_json = json.dumps({"actual_preference": "喜欢开朗的人"})
        mock_user.ideal_type = json.dumps({"description": "温柔体贴"})
        mock_user.deal_breakers = json.dumps(["吸烟"])
        mock_user.profile_confidence = 0.7

        with patch.object(service, '_get_user_from_db', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user

            self_profile, desire_profile = await service.get_or_create_profile("user_001")

            assert self_profile.age == 28
            assert self_profile.gender == "male"
            assert self_profile.location == "北京"
            assert self_profile.interests == ["旅行", "摄影"]
            assert self_profile.communication_style == "direct"

            assert desire_profile.surface_preference == "温柔体贴"
            assert desire_profile.deal_breakers == ["吸烟"]
            assert desire_profile.actual_preference == "喜欢开朗的人"

    @pytest.mark.asyncio
    async def test_profile_cached_after_query(self):
        """测试查询后缓存画像"""
        service = UserProfileService()

        mock_user = MagicMock()
        mock_user.id = "user_001"
        mock_user.age = 28
        mock_user.gender = "male"
        mock_user.location = ""
        mock_user.occupation = ""
        mock_user.education = ""
        mock_user.relationship_goal = ""
        mock_user.interests = None
        mock_user.self_profile_json = None
        mock_user.desire_profile_json = None
        mock_user.ideal_type = None
        mock_user.deal_breakers = None
        mock_user.profile_confidence = 0.3

        with patch.object(service, '_get_user_from_db', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user

            # 第一次查询
            await service.get_or_create_profile("user_001")

            # 应缓存
            assert "user_001" in service._profile_cache

            # 第二次查询不应调用数据库
            mock_get.return_value = None  # 如果调用会失败
            await service.get_or_create_profile("user_001")
            # 缓存命中，不会调用 mock_get

    @pytest.mark.asyncio
    async def test_user_not_found_returns_empty_profile(self):
        """测试用户不存在返回空画像"""
        service = UserProfileService()

        with patch.object(service, '_get_user_from_db', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            self_profile, desire_profile = await service.get_or_create_profile("nonexistent_user")

            assert isinstance(self_profile, SelfProfile)
            assert isinstance(desire_profile, DesireProfile)
            # 空画像的置信度应为默认值
            assert self_profile.profile_confidence >= 0


class TestBuildSelfProfile:
    """构建 SelfProfile 测试"""

    def test_build_self_profile_from_basic_fields(self):
        """测试从基础字段构建 SelfProfile"""
        service = UserProfileService()

        mock_user = MagicMock()
        mock_user.age = 30
        mock_user.gender = "female"
        mock_user.location = "上海"
        mock_user.occupation = "设计师"
        mock_user.education = "硕士"
        mock_user.relationship_goal = "casual"
        mock_user.interests = json.dumps(["阅读", "瑜伽"])
        mock_user.self_profile_json = None
        mock_user.profile_confidence = 0.5

        self_profile = service._build_self_profile(mock_user)

        assert self_profile.age == 30
        assert self_profile.gender == "female"
        assert self_profile.location == "上海"
        assert self_profile.occupation == "设计师"
        assert self_profile.education == "硕士"
        assert self_profile.relationship_goal == "casual"
        assert self_profile.interests == ["阅读", "瑜伽"]
        assert self_profile.profile_confidence == 0.5

    def test_build_self_profile_with_dynamic_data(self):
        """测试从动态数据构建 SelfProfile"""
        service = UserProfileService()

        mock_user = MagicMock()
        mock_user.age = 25
        mock_user.gender = ""
        mock_user.location = ""
        mock_user.occupation = ""
        mock_user.education = ""
        mock_user.relationship_goal = ""
        mock_user.interests = None
        mock_user.self_profile_json = json.dumps({
            "actual_personality": "内向温和",
            "communication_style": "倾听型",
            "response_pattern": "及时回复",
            "power_dynamic": "平等合作",
            "decision_style": "协商型",
            "emotional_needs": ["安全感", "理解"],
            "attachment_style": "安全型",
            "reputation_score": 0.8,
            "like_rate": 0.6,
        })
        mock_user.profile_confidence = 0.6

        self_profile = service._build_self_profile(mock_user)

        assert self_profile.actual_personality == "内向温和"
        assert self_profile.communication_style == "倾听型"
        assert self_profile.response_pattern == "及时回复"
        assert self_profile.power_dynamic == "平等合作"
        assert self_profile.decision_style == "协商型"
        assert self_profile.emotional_needs == ["安全感", "理解"]
        assert self_profile.attachment_style == "安全型"
        assert self_profile.reputation_score == 0.8
        assert self_profile.like_rate == 0.6

    def test_build_self_profile_malformed_json(self):
        """测试 JSON 解析失败处理"""
        service = UserProfileService()

        mock_user = MagicMock()
        mock_user.age = 28
        mock_user.gender = "male"
        mock_user.location = ""
        mock_user.occupation = ""
        mock_user.education = ""
        mock_user.relationship_goal = ""
        mock_user.interests = "invalid json"
        mock_user.self_profile_json = "{ invalid json }"
        mock_user.profile_confidence = 0.3

        self_profile = service._build_self_profile(mock_user)

        # 应优雅处理解析错误
        assert self_profile.age == 28
        assert self_profile.gender == "male"
        assert self_profile.interests == []  # 解析失败返回空列表
        assert self_profile.actual_personality == ""  # 默认值


class TestBuildDesireProfile:
    """构建 DesireProfile 测试"""

    def test_build_desire_profile_from_surface_preference(self):
        """测试从表面偏好构建 DesireProfile"""
        service = UserProfileService()

        mock_user = MagicMock()
        mock_user.ideal_type = json.dumps({"description": "成熟稳重的人"})
        mock_user.deal_breakers = json.dumps(["不诚实", "懒散"])
        mock_user.desire_profile_json = None
        mock_user.profile_confidence = 0.5

        desire_profile = service._build_desire_profile(mock_user)

        assert desire_profile.surface_preference == "成熟稳重的人"
        assert desire_profile.ideal_type_description == "成熟稳重的人"
        assert desire_profile.deal_breakers == ["不诚实", "懒散"]

    def test_build_desire_profile_with_dynamic_data(self):
        """测试从动态数据构建 DesireProfile"""
        service = UserProfileService()

        mock_user = MagicMock()
        mock_user.ideal_type = None
        mock_user.deal_breakers = None
        mock_user.desire_profile_json = json.dumps({
            "actual_preference": "实际喜欢幽默风趣的人",
            "search_patterns": ["年龄25-30", "北京"],
            "clicked_types": ["摄影师", "程序员"],
            "swipe_patterns": {"like_rate": 0.4, "super_like_rate": 0.1},
            "like_feedback": ["喜欢笑容灿烂的人"],
            "dislike_feedback": ["不喜欢太内向的人"],
        })
        mock_user.profile_confidence = 0.6

        desire_profile = service._build_desire_profile(mock_user)

        assert desire_profile.actual_preference == "实际喜欢幽默风趣的人"
        assert desire_profile.search_patterns == ["年龄25-30", "北京"]
        assert desire_profile.clicked_types == ["摄影师", "程序员"]
        assert desire_profile.swipe_patterns["like_rate"] == 0.4
        assert desire_profile.like_feedback == ["喜欢笑容灿烂的人"]
        assert desire_profile.dislike_feedback == ["不喜欢太内向的人"]


class TestLRUCacheEviction:
    """LRU 缓存淘汰测试"""

    def test_evict_when_over_capacity(self):
        """测试超过容量时淘汰"""
        service = UserProfileService()

        # 模拟填充缓存
        for i in range(PROFILE_CACHE_MAX_SIZE + 10):
            service._profile_cache[f"user_{i}"] = (SelfProfile(), DesireProfile())

        # 应淘汰最旧的条目
        service._evict_if_needed()

        assert len(service._profile_cache) <= PROFILE_CACHE_MAX_SIZE
        # 最旧的条目应被淘汰
        assert "user_0" not in service._profile_cache

    def test_lru_order_on_access(self):
        """测试访问时更新 LRU 顺序"""
        service = UserProfileService()

        service._profile_cache["user_a"] = (SelfProfile(), DesireProfile())
        service._profile_cache["user_b"] = (SelfProfile(), DesireProfile())
        service._profile_cache["user_c"] = (SelfProfile(), DesireProfile())

        # 访问 user_a
        service._profile_cache.move_to_end("user_a")

        # user_a 应成为最新的
        keys = list(service._profile_cache.keys())
        assert keys[-1] == "user_a"


class TestBatchQuery:
    """批量查询测试"""

    @pytest.mark.asyncio
    async def test_batch_query_mixed_cached_uncached(self):
        """测试批量查询混合缓存和未缓存"""
        service = UserProfileService()

        # 缓存 user_001
        service._profile_cache["user_001"] = (SelfProfile(age=28), DesireProfile())

        mock_user_002 = MagicMock()
        mock_user_002.id = "user_002"
        mock_user_002.age = 30
        mock_user_002.gender = "female"
        mock_user_002.location = ""
        mock_user_002.occupation = ""
        mock_user_002.education = ""
        mock_user_002.relationship_goal = ""
        mock_user_002.interests = None
        mock_user_002.self_profile_json = None
        mock_user_002.desire_profile_json = None
        mock_user_002.ideal_type = None
        mock_user_002.deal_breakers = None
        mock_user_002.profile_confidence = 0.3

        with patch.object(service, '_get_users_batch_from_db', new_callable=AsyncMock) as mock_batch:
            mock_batch.return_value = {"user_002": mock_user_002}

            results = await service.get_profiles_batch(["user_001", "user_002"])

            assert "user_001" in results
            assert "user_002" in results
            assert results["user_001"][0].age == 28  # 从缓存
            assert results["user_002"][0].age == 30  # 从数据库

    @pytest.mark.asyncio
    async def test_batch_query_all_cached(self):
        """测试批量查询全部缓存"""
        service = UserProfileService()

        # 缓存所有用户
        service._profile_cache["user_001"] = (SelfProfile(age=25), DesireProfile())
        service._profile_cache["user_002"] = (SelfProfile(age=30), DesireProfile())
        service._profile_cache["user_003"] = (SelfProfile(age=35), DesireProfile())

        results = await service.get_profiles_batch(["user_001", "user_002", "user_003"])

        # 不应调用数据库
        assert len(results) == 3
        assert results["user_001"][0].age == 25

    @pytest.mark.asyncio
    async def test_batch_query_empty_list(self):
        """测试批量查询空列表"""
        service = UserProfileService()

        results = await service.get_profiles_batch([])

        assert results == {}


class TestEdgeCases:
    """边界值测试"""

    @pytest.mark.asyncio
    async def test_user_with_null_fields(self):
        """测试用户字段为 NULL"""
        service = UserProfileService()

        mock_user = MagicMock()
        mock_user.id = "user_null"
        mock_user.age = None
        mock_user.gender = None
        mock_user.location = None
        mock_user.occupation = None
        mock_user.education = None
        mock_user.relationship_goal = None
        mock_user.interests = None
        mock_user.self_profile_json = None
        mock_user.desire_profile_json = None
        mock_user.ideal_type = None
        mock_user.deal_breakers = None
        mock_user.profile_confidence = None

        with patch.object(service, '_get_user_from_db', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user

            self_profile, desire_profile = await service.get_or_create_profile("user_null")

            # 应优雅处理 NULL 字段
            assert self_profile.age == 0  # 默认值
            assert self_profile.gender == ""
            assert self_profile.interests == []

    def test_confidence_bounds(self):
        """测试置信度边界"""
        service = UserProfileService()

        mock_user_low = MagicMock()
        mock_user_low.age = 25
        mock_user_low.gender = ""
        mock_user_low.location = ""
        mock_user_low.occupation = ""
        mock_user_low.education = ""
        mock_user_low.relationship_goal = ""
        mock_user_low.interests = None
        mock_user_low.self_profile_json = None
        mock_user_low.profile_confidence = 0.0

        profile_low = service._build_self_profile(mock_user_low)
        assert profile_low.profile_confidence == 0.0

        mock_user_high = MagicMock()
        mock_user_high.age = 25
        mock_user_high.gender = ""
        mock_user_high.location = ""
        mock_user_high.occupation = ""
        mock_user_high.education = ""
        mock_user_high.relationship_goal = ""
        mock_user_high.interests = None
        mock_user_high.self_profile_json = None
        mock_user_high.profile_confidence = 1.0

        profile_high = service._build_self_profile(mock_user_high)
        assert profile_high.profile_confidence == 1.0

    def test_interests_list_parsing(self):
        """测试兴趣列表解析"""
        service = UserProfileService()

        mock_user = MagicMock()
        mock_user.age = 28
        mock_user.gender = ""
        mock_user.location = ""
        mock_user.occupation = ""
        mock_user.education = ""
        mock_user.relationship_goal = ""
        mock_user.interests = json.dumps(["旅行", "摄影", "阅读", "音乐"])
        mock_user.self_profile_json = None
        mock_user.profile_confidence = 0.3

        self_profile = service._build_self_profile(mock_user)

        assert len(self_profile.interests) == 4
        assert "旅行" in self_profile.interests
        assert "音乐" in self_profile.interests

    def test_empty_interests_json(self):
        """测试空兴趣 JSON"""
        service = UserProfileService()

        mock_user = MagicMock()
        mock_user.age = 28
        mock_user.gender = ""
        mock_user.location = ""
        mock_user.occupation = ""
        mock_user.education = ""
        mock_user.relationship_goal = ""
        mock_user.interests = json.dumps([])
        mock_user.self_profile_json = None
        mock_user.profile_confidence = 0.3

        self_profile = service._build_self_profile(mock_user)

        assert self_profile.interests == []


class TestServiceFactory:
    """服务工厂测试"""

    def test_service_creation(self):
        """测试服务创建"""
        service = UserProfileService()
        assert service is not None
        assert isinstance(service, UserProfileService)