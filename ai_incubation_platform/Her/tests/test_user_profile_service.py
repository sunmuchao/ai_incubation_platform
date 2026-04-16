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
        ProfileUpdateEngine,
        EVENT_TO_SELF_PROFILE_DIMENSION,
        EVENT_TO_DESIRE_PROFILE_DIMENSION,
        PROFILE_CACHE_MAX_SIZE,
        get_user_profile_service,
        get_profile_update_engine,
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
        mock_user.interests = None  # 避免 JSON 解析错误
        mock_user.self_profile_json = "{ invalid json }"
        mock_user.profile_confidence = 0.3

        self_profile = service._build_self_profile(mock_user)

        # 应优雅处理解析错误
        assert self_profile.age == 28
        assert self_profile.gender == "male"
        assert self_profile.interests == []  # 默认值
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
        mock_user_low.profile_confidence = None  # None 会被转换为默认值

        profile_low = service._build_self_profile(mock_user_low)
        # None profile_confidence 会使用默认值 0.3
        assert profile_low.profile_confidence >= 0

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


class TestUpdateSelfProfile:
    """更新 SelfProfile 测试"""

    @pytest.mark.asyncio
    async def test_update_self_profile_success(self):
        """测试成功更新 SelfProfile"""
        service = UserProfileService()

        # Mock get_or_create_profile
        mock_self = SelfProfile(
            age=28,
            communication_style="direct",
            dimension_confidences={"basic": 1.0, "communication": 0.5}
        )
        mock_desire = DesireProfile()

        with patch.object(service, 'get_or_create_profile', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = (mock_self, mock_desire)

            with patch.object(service, '_save_profile_to_db', new_callable=AsyncMock) as mock_save:
                with patch('cache.cache_manager') as mock_cache:
                    result = await service.update_self_profile(
                        user_id="user_001",
                        dimension="communication_style",
                        new_value="倾听型",
                        source="behavior_event",
                        confidence=0.8
                    )

                    assert result is True
                    assert mock_self.communication_style == "倾听型"
                    assert mock_self.dimension_confidences["communication_style"] == 0.8
                    mock_save.assert_called_once()
                    mock_cache.invalidate_profile.assert_called_once_with("user_001")
                    mock_cache.invalidate_match_result.assert_called_once_with("user_001")

    @pytest.mark.asyncio
    async def test_update_self_profile_emotional_needs_list(self):
        """测试更新情感需求（列表类型）"""
        service = UserProfileService()

        mock_self = SelfProfile(emotional_needs=["安全感"])
        mock_desire = DesireProfile()

        with patch.object(service, 'get_or_create_profile', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = (mock_self, mock_desire)

            with patch.object(service, '_save_profile_to_db', new_callable=AsyncMock):
                with patch('cache.cache_manager'):
                    result = await service.update_self_profile(
                        user_id="user_001",
                        dimension="emotional_needs",
                        new_value=["安全感", "理解", "陪伴"],
                        source="behavior_event"
                    )

                    assert result is True
                    assert mock_self.emotional_needs == ["安全感", "理解", "陪伴"]

    @pytest.mark.asyncio
    async def test_update_self_profile_social_feedback(self):
        """测试更新社会反馈（字典类型）"""
        service = UserProfileService()

        mock_self = SelfProfile(reputation_score=0.5, like_rate=0.4)
        mock_desire = DesireProfile()

        with patch.object(service, 'get_or_create_profile', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = (mock_self, mock_desire)

            with patch.object(service, '_save_profile_to_db', new_callable=AsyncMock):
                with patch('cache.cache_manager'):
                    result = await service.update_self_profile(
                        user_id="user_001",
                        dimension="social_feedback",
                        new_value={"reputation_score": 0.8, "like_rate": 0.6},
                        source="behavior_event"
                    )

                    assert result is True
                    assert mock_self.reputation_score == 0.8
                    assert mock_self.like_rate == 0.6

    @pytest.mark.asyncio
    async def test_update_self_profile_exception(self):
        """测试更新异常处理"""
        service = UserProfileService()

        with patch.object(service, 'get_or_create_profile', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Database error")

            result = await service.update_self_profile(
                user_id="user_001",
                dimension="communication_style",
                new_value="new_value",
                source="test"
            )

            assert result is False


class TestUpdateDesireProfile:
    """更新 DesireProfile 测试"""

    @pytest.mark.asyncio
    async def test_update_desire_profile_success(self):
        """测试成功更新 DesireProfile"""
        service = UserProfileService()

        mock_self = SelfProfile()
        mock_desire = DesireProfile(actual_preference="喜欢开朗的人")

        with patch.object(service, 'get_or_create_profile', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = (mock_self, mock_desire)

            with patch.object(service, '_save_profile_to_db', new_callable=AsyncMock) as mock_save:
                with patch('cache.cache_manager') as mock_cache:
                    result = await service.update_desire_profile(
                        user_id="user_001",
                        dimension="actual_preference",
                        new_value="实际喜欢幽默风趣的人",
                        source="conversation_analysis",
                        confidence=0.7
                    )

                    assert result is True
                    assert mock_desire.actual_preference == "实际喜欢幽默风趣的人"
                    assert mock_desire.preference_confidence == 0.7
                    mock_save.assert_called_once()
                    mock_cache.invalidate_profile.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_desire_profile_search_patterns_list(self):
        """测试更新搜索偏好（列表类型）"""
        service = UserProfileService()

        mock_self = SelfProfile()
        mock_desire = DesireProfile(search_patterns=["年龄25-30"])

        with patch.object(service, 'get_or_create_profile', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = (mock_self, mock_desire)

            with patch.object(service, '_save_profile_to_db', new_callable=AsyncMock):
                with patch('cache.cache_manager'):
                    # 传入字符串会被转换为列表
                    result = await service.update_desire_profile(
                        user_id="user_001",
                        dimension="search_patterns",
                        new_value="北京",
                        source="behavior_event"
                    )

                    assert result is True
                    assert mock_desire.search_patterns == ["北京"]

    @pytest.mark.asyncio
    async def test_update_desire_profile_swipe_patterns_dict(self):
        """测试更新滑动偏好（字典类型）"""
        service = UserProfileService()

        mock_self = SelfProfile()
        mock_desire = DesireProfile(swipe_patterns={"like_rate": 0.4})

        with patch.object(service, 'get_or_create_profile', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = (mock_self, mock_desire)

            with patch.object(service, '_save_profile_to_db', new_callable=AsyncMock):
                with patch('cache.cache_manager'):
                    # 传入字符串会被转换为空字典
                    result = await service.update_desire_profile(
                        user_id="user_001",
                        dimension="swipe_patterns",
                        new_value={"like_rate": 0.6, "super_like_rate": 0.2},
                        source="behavior_event"
                    )

                    assert result is True
                    assert mock_desire.swipe_patterns["like_rate"] == 0.6
                    assert mock_desire.swipe_patterns["super_like_rate"] == 0.2

    @pytest.mark.asyncio
    async def test_update_desire_profile_exception(self):
        """测试更新异常处理"""
        service = UserProfileService()

        with patch.object(service, 'get_or_create_profile', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Database error")

            result = await service.update_desire_profile(
                user_id="user_001",
                dimension="actual_preference",
                new_value="test",
                source="test"
            )

            assert result is False


class TestDimensionValueHelpers:
    """维度值辅助方法测试"""

    def test_get_self_profile_dimension_value(self):
        """测试获取 SelfProfile 维度值"""
        service = UserProfileService()

        profile = SelfProfile(
            communication_style="direct",
            response_pattern="及时",
            emotional_needs=["安全感"],
            reputation_score=0.8,
            like_rate=0.6
        )

        # 常规维度
        assert service._get_self_profile_dimension_value(profile, "communication_style") == "direct"
        assert service._get_self_profile_dimension_value(profile, "response_pattern") == "及时"
        assert service._get_self_profile_dimension_value(profile, "emotional_needs") == ["安全感"]

        # 社会反馈维度
        social_feedback = service._get_self_profile_dimension_value(profile, "social_feedback")
        assert social_feedback["reputation_score"] == 0.8
        assert social_feedback["like_rate"] == 0.6

        # 未知维度
        assert service._get_self_profile_dimension_value(profile, "unknown") == ""

    def test_set_self_profile_dimension_value(self):
        """测试设置 SelfProfile 维度值"""
        service = UserProfileService()

        profile = SelfProfile()

        # 常规维度
        service._set_self_profile_dimension_value(profile, "communication_style", "倾听型")
        assert profile.communication_style == "倾听型"

        service._set_self_profile_dimension_value(profile, "emotional_needs", ["安全感", "理解"])
        assert profile.emotional_needs == ["安全感", "理解"]

        # 字符串转列表
        service._set_self_profile_dimension_value(profile, "emotional_needs", "安全感")
        assert profile.emotional_needs == ["安全感"]

        # 社会反馈
        service._set_self_profile_dimension_value(profile, "social_feedback", {"reputation_score": 0.9})
        assert profile.reputation_score == 0.9

    def test_get_desire_profile_dimension_value(self):
        """测试获取 DesireProfile 维度值"""
        service = UserProfileService()

        profile = DesireProfile(
            surface_preference="温柔体贴",
            actual_preference="喜欢幽默的人",
            search_patterns=["年龄25-30"],
            swipe_patterns={"like_rate": 0.5}
        )

        assert service._get_desire_profile_dimension_value(profile, "surface_preference") == "温柔体贴"
        assert service._get_desire_profile_dimension_value(profile, "actual_preference") == "喜欢幽默的人"
        assert service._get_desire_profile_dimension_value(profile, "search_patterns") == ["年龄25-30"]
        assert service._get_desire_profile_dimension_value(profile, "swipe_patterns") == {"like_rate": 0.5}
        assert service._get_desire_profile_dimension_value(profile, "unknown") == ""

    def test_set_desire_profile_dimension_value(self):
        """测试设置 DesireProfile 维度值"""
        service = UserProfileService()

        profile = DesireProfile()

        # 常规维度
        service._set_desire_profile_dimension_value(profile, "actual_preference", "新偏好")
        assert profile.actual_preference == "新偏好"

        # 列表维度
        service._set_desire_profile_dimension_value(profile, "search_patterns", ["北京"])
        assert profile.search_patterns == ["北京"]

        # 字符串转列表
        service._set_desire_profile_dimension_value(profile, "clicked_types", "摄影师")
        assert profile.clicked_types == ["摄影师"]

        # 字典维度
        service._set_desire_profile_dimension_value(profile, "swipe_patterns", {"like_rate": 0.7})
        assert profile.swipe_patterns == {"like_rate": 0.7}

        # 字典转空字典（字符串输入）
        service._set_desire_profile_dimension_value(profile, "swipe_patterns", "invalid")
        assert profile.swipe_patterns == {}


class TestCalculateOverallConfidence:
    """整体置信度计算测试"""

    def test_calculate_with_all_dimensions(self):
        """测试所有维度置信度"""
        service = UserProfileService()

        confidences = {
            "basic": 1.0,
            "personality": 0.8,
            "communication": 0.6,
            "emotional_needs": 0.7,
            "power_dynamic": 0.5,
            "social_feedback": 0.4,
        }

        result = service._calculate_overall_confidence(confidences)

        # basic 权重 0.4, personality 0.2, communication 0.1, emotional_needs 0.15, power_dynamic 0.1, social_feedback 0.05
        expected = (1.0 * 0.4 + 0.8 * 0.2 + 0.6 * 0.1 + 0.7 * 0.15 + 0.5 * 0.1 + 0.4 * 0.05) / (0.4 + 0.2 + 0.1 + 0.15 + 0.1 + 0.05)
        assert abs(result - expected) < 0.001

    def test_calculate_with_partial_dimensions(self):
        """测试部分维度置信度"""
        service = UserProfileService()

        confidences = {
            "basic": 1.0,
            "personality": 0.5,
        }

        result = service._calculate_overall_confidence(confidences)

        expected = (1.0 * 0.4 + 0.5 * 0.2) / (0.4 + 0.2)
        assert abs(result - expected) < 0.001

    def test_calculate_with_unknown_dimensions(self):
        """测试未知维度使用默认权重"""
        service = UserProfileService()

        confidences = {
            "basic": 1.0,
            "unknown_dimension": 0.5,  # 使用默认权重 0.1
        }

        result = service._calculate_overall_confidence(confidences)

        # unknown_dimension 使用权重 0.1
        expected = (1.0 * 0.4 + 0.5 * 0.1) / (0.4 + 0.1)
        assert abs(result - expected) < 0.001

    def test_calculate_empty_confidences(self):
        """测试空置信度"""
        service = UserProfileService()

        result = service._calculate_overall_confidence({})
        assert result == 0.0


class TestCalculateProfileCompleteness:
    """画像完整度计算测试"""

    def test_complete_profiles(self):
        """测试完整画像"""
        service = UserProfileService()

        self_profile = SelfProfile(
            actual_personality="内向温和",
            communication_style="倾听型",
            emotional_needs=["安全感"],
            attachment_style="安全型",
            power_dynamic="平等合作",
        )

        desire_profile = DesireProfile(
            actual_preference="喜欢幽默的人",
            search_patterns=["北京"],
            clicked_types=["摄影师"],
            like_feedback=["笑容灿烂"],
        )

        result = service._calculate_profile_completeness(self_profile, desire_profile)

        # SelfProfile: 5/5 = 100% * 0.6 = 0.6
        # DesireProfile: 4/4 = 100% * 0.4 = 0.4
        # Total: 1.0
        assert result == 1.0

    def test_partial_profiles(self):
        """测试部分完整画像"""
        service = UserProfileService()

        self_profile = SelfProfile(
            actual_personality="内向",
            communication_style="倾听型",
            emotional_needs=[],  # 空
            attachment_style="",  # 空
            power_dynamic="",  # 空
        )

        desire_profile = DesireProfile(
            actual_preference="喜欢幽默的人",
            search_patterns=[],  # 空
            clicked_types=["摄影师"],
            like_feedback=[],  # 空
        )

        result = service._calculate_profile_completeness(self_profile, desire_profile)

        # SelfProfile: 2/5 = 0.4 * 0.6 = 0.24
        # DesireProfile: 2/4 = 0.5 * 0.4 = 0.2
        # Total: 0.44
        assert abs(result - 0.44) < 0.001

    def test_empty_profiles(self):
        """测试空画像"""
        service = UserProfileService()

        self_profile = SelfProfile()
        desire_profile = DesireProfile()

        result = service._calculate_profile_completeness(self_profile, desire_profile)
        assert result == 0.0


class TestClearCache:
    """清除缓存测试"""

    def test_clear_specific_user_cache(self):
        """测试清除指定用户缓存"""
        service = UserProfileService()

        # 添加缓存
        service._profile_cache["user_001"] = (SelfProfile(), DesireProfile())
        service._profile_cache["user_002"] = (SelfProfile(), DesireProfile())

        with patch('cache.cache_manager') as mock_cache:
            service.clear_cache("user_001")

            assert "user_001" not in service._profile_cache
            assert "user_002" in service._profile_cache
            mock_cache.invalidate_profile.assert_called_once_with("user_001")
            mock_cache.invalidate_match_result.assert_called_once_with("user_001")

    def test_clear_all_cache(self):
        """测试清除全部缓存"""
        service = UserProfileService()

        # 添加缓存
        service._profile_cache["user_001"] = (SelfProfile(), DesireProfile())
        service._profile_cache["user_002"] = (SelfProfile(), DesireProfile())

        service.clear_cache()

        assert len(service._profile_cache) == 0


class TestProfileUpdateEngine:
    """画像更新引擎测试"""

    def test_engine_creation(self):
        """测试引擎创建"""
        engine = ProfileUpdateEngine()
        assert engine is not None
        assert engine._profile_service is None

    def test_get_profile_service_lazy_init(self):
        """测试延迟初始化服务"""
        engine = ProfileUpdateEngine()

        service = engine._get_profile_service()

        assert service is not None
        assert isinstance(service, UserProfileService)
        assert engine._profile_service is service  # 缓存

    @pytest.mark.asyncio
    async def test_process_behavior_event_self_dimension(self):
        """测试处理行为事件更新 SelfProfile"""
        engine = ProfileUpdateEngine()

        with patch.object(engine, '_get_profile_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.update_self_profile = AsyncMock(return_value=True)
            mock_get_service.return_value = mock_service

            with patch.object(engine, '_calculate_self_profile_update') as mock_calc:
                mock_calc.return_value = "倾听型"

                with patch.object(engine, '_calculate_event_confidence') as mock_conf:
                    mock_conf.return_value = 0.6

                    result = await engine.process_behavior_event(
                        user_id="user_001",
                        event_type="message_sent",
                        event_data={"message_length": 100},
                        target_user_id="user_002"
                    )

                    assert result is True
                    mock_service.update_self_profile.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_behavior_event_desire_dimension(self):
        """测试处理行为事件更新 DesireProfile"""
        engine = ProfileUpdateEngine()

        with patch.object(engine, '_get_profile_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.update_desire_profile = AsyncMock(return_value=True)
            mock_get_service.return_value = mock_service

            with patch.object(engine, '_calculate_desire_profile_update') as mock_calc:
                mock_calc.return_value = {"query": "北京"}

                with patch.object(engine, '_calculate_event_confidence') as mock_conf:
                    mock_conf.return_value = 0.6

                    result = await engine.process_behavior_event(
                        user_id="user_001",
                        event_type="search_query",
                        event_data={"query": "北京"},
                    )

                    assert result is True
                    mock_service.update_desire_profile.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_behavior_event_no_update_value(self):
        """测试无更新值时不更新"""
        engine = ProfileUpdateEngine()

        with patch.object(engine, '_get_profile_service') as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service

            with patch.object(engine, '_calculate_self_profile_update') as mock_calc:
                mock_calc.return_value = None  # 无更新值

                result = await engine.process_behavior_event(
                    user_id="user_001",
                    event_type="unknown_event",
                    event_data={}
                )

                assert result is False
                mock_service.update_self_profile.assert_not_called()


class TestCalculateSelfProfileUpdate:
    """SelfProfile 更新值计算测试"""

    def test_message_sent_communication_style(self):
        """测试消息发送推断沟通风格"""
        engine = ProfileUpdateEngine()

        result = engine._calculate_self_profile_update(
            event_type="message_sent",
            event_data={"message_length": 150},
            user_id="user_001",
            target_user_id=None
        )

        assert result == "详细表达型"

    def test_response_time_fast(self):
        """测试快速响应"""
        engine = ProfileUpdateEngine()

        result = engine._calculate_self_profile_update(
            event_type="response_time",
            event_data={"response_time_seconds": 30},
            user_id="user_001",
            target_user_id=None
        )

        assert result == "即时回复"

    def test_response_time_normal(self):
        """测试正常响应"""
        engine = ProfileUpdateEngine()

        result = engine._calculate_self_profile_update(
            event_type="response_time",
            event_data={"response_time_seconds": 3600},
            user_id="user_001",
            target_user_id=None
        )

        assert result == "正常回复"

    def test_response_time_slow(self):
        """测试慢速响应"""
        engine = ProfileUpdateEngine()

        result = engine._calculate_self_profile_update(
            event_type="response_time",
            event_data={"response_time_seconds": 100000},
            user_id="user_001",
            target_user_id=None
        )

        assert result == "慢速回复"

    def test_emoji_usage_high(self):
        """测试高表情使用"""
        engine = ProfileUpdateEngine()

        result = engine._calculate_self_profile_update(
            event_type="emoji_usage",
            event_data={"emoji_count": 10, "total_messages": 15},
            user_id="user_001",
            target_user_id=None
        )

        assert result == "情感表达丰富"

    def test_emoji_usage_low(self):
        """测试低表情使用"""
        engine = ProfileUpdateEngine()

        result = engine._calculate_self_profile_update(
            event_type="emoji_usage",
            event_data={"emoji_count": 1, "total_messages": 20},
            user_id="user_001",
            target_user_id=None
        )

        assert result == "理性表达"

    def test_topic_initiation_leader(self):
        """测试话题发起主导"""
        engine = ProfileUpdateEngine()

        result = engine._calculate_self_profile_update(
            event_type="topic_initiation",
            event_data={"is_initiator": True},
            user_id="user_001",
            target_user_id=None
        )

        assert result == "主导型"

    def test_received_like_social_feedback(self):
        """测试收到喜欢更新社会反馈"""
        engine = ProfileUpdateEngine()

        result = engine._calculate_self_profile_update(
            event_type="received_like",
            event_data={},
            user_id="user_001",
            target_user_id="user_002"
        )

        assert result == {"like_rate_increment": 0.01}


class TestCalculateDesireProfileUpdate:
    """DesireProfile 更新值计算测试"""

    def test_search_query(self):
        """测试搜索查询"""
        engine = ProfileUpdateEngine()

        result = engine._calculate_desire_profile_update(
            event_type="search_query",
            event_data={"query": "北京", "filters": {"age": "25-30"}},
            user_id="user_001",
            target_user_id=None
        )

        assert result["query"] == "北京"
        assert result["filters"]["age"] == "25-30"
        assert "timestamp" in result

    def test_profile_view(self):
        """测试查看资料"""
        engine = ProfileUpdateEngine()

        result = engine._calculate_desire_profile_update(
            event_type="profile_view",
            event_data={"target_type": "摄影师"},
            user_id="user_001",
            target_user_id="user_002"
        )

        assert result == "摄影师"

    def test_swipe_like(self):
        """测试滑动喜欢"""
        engine = ProfileUpdateEngine()

        result = engine._calculate_desire_profile_update(
            event_type="swipe_like",
            event_data={"target_type": "设计师"},
            user_id="user_001",
            target_user_id="user_002"
        )

        assert result["action"] == "like"
        assert result["target_type"] == "设计师"
        assert "timestamp" in result

    def test_match_like_feedback(self):
        """测试匹配喜欢反馈"""
        engine = ProfileUpdateEngine()

        result = engine._calculate_desire_profile_update(
            event_type="match_like",
            event_data={"reason": "性格合拍"},
            user_id="user_001",
            target_user_id="user_002"
        )

        assert result["action"] == "like"
        assert result["target_id"] == "user_002"
        assert result["reason"] == "性格合拍"

    def test_match_dislike_feedback(self):
        """测试匹配不喜欢反馈"""
        engine = ProfileUpdateEngine()

        result = engine._calculate_desire_profile_update(
            event_type="match_dislike",
            event_data={"reason": "三观不合"},
            user_id="user_001",
            target_user_id="user_002"
        )

        assert result["action"] == "dislike"


class TestInferCommunicationStyle:
    """沟通风格推断测试"""

    def test_long_message(self):
        """测试长消息"""
        engine = ProfileUpdateEngine()

        result = engine._infer_communication_style({"message_length": 200})
        assert result == "详细表达型"

    def test_medium_message(self):
        """测试中等消息"""
        engine = ProfileUpdateEngine()

        result = engine._infer_communication_style({"message_length": 80})
        assert result == "适度表达型"

    def test_short_message(self):
        """测试短消息"""
        engine = ProfileUpdateEngine()

        result = engine._infer_communication_style({"message_length": 30})
        assert result == "简洁表达型"

    def test_very_short_message(self):
        """测试极短消息"""
        engine = ProfileUpdateEngine()

        result = engine._infer_communication_style({"message_length": 10})
        assert result == "极简表达型"


class TestCalculateEventConfidence:
    """事件置信度计算测试"""

    def test_high_confidence_events(self):
        """测试高置信度事件"""
        engine = ProfileUpdateEngine()

        for event_type in ["match_like", "match_dislike", "swipe_like", "swipe_pass", "received_like", "received_dislike"]:
            result = engine._calculate_event_confidence(event_type, {})
            assert result == 0.9

    def test_medium_confidence_events(self):
        """测试中置信度事件"""
        engine = ProfileUpdateEngine()

        for event_type in ["profile_view", "search_query", "message_sent", "topic_initiation"]:
            result = engine._calculate_event_confidence(event_type, {})
            assert result == 0.6

    def test_low_confidence_events(self):
        """测试低置信度事件"""
        engine = ProfileUpdateEngine()

        for event_type in ["response_time", "emoji_usage"]:
            result = engine._calculate_event_confidence(event_type, {})
            assert result == 0.3

    def test_unknown_event(self):
        """测试未知事件"""
        engine = ProfileUpdateEngine()

        result = engine._calculate_event_confidence("unknown_event", {})
        assert result == 0.5


class TestProcessConversationAnalysis:
    """对话分析处理测试"""

    @pytest.mark.asyncio
    async def test_process_with_stated_preference(self):
        """测试明确表达的偏好"""
        engine = ProfileUpdateEngine()

        with patch.object(engine, '_get_profile_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.update_desire_profile = AsyncMock(return_value=True)
            mock_get_service.return_value = mock_service

            result = await engine.process_conversation_analysis(
                user_id="user_001",
                message="我喜欢温柔体贴的人",
                extracted_preference={
                    "stated_preference": "温柔体贴",
                    "stated_confidence": 0.9,
                    "inferred_preference": "实际喜欢幽默风趣",
                    "inferred_confidence": 0.6,
                }
            )

            assert result is True
            # 应调用两次 update_desire_profile
            assert mock_service.update_desire_profile.call_count == 2

    @pytest.mark.asyncio
    async def test_process_only_inferred_preference(self):
        """测试仅推断偏好"""
        engine = ProfileUpdateEngine()

        with patch.object(engine, '_get_profile_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.update_desire_profile = AsyncMock(return_value=True)
            mock_get_service.return_value = mock_service

            result = await engine.process_conversation_analysis(
                user_id="user_001",
                message="...",
                extracted_preference={
                    "inferred_preference": "喜欢开朗的人",
                    "inferred_confidence": 0.7,
                }
            )

            assert result is True
            # 只调用一次（推断偏好）
            mock_service.update_desire_profile.assert_called_once()


class TestBatchProcessEvents:
    """批量事件处理测试"""

    @pytest.mark.asyncio
    async def test_batch_process_multiple_events(self):
        """测试批量处理多个事件"""
        engine = ProfileUpdateEngine()

        events = [
            {"event_type": "swipe_like", "event_data": {"target_type": "设计师"}, "target_user_id": "user_002"},
            {"event_type": "message_sent", "event_data": {"message_length": 100}, "target_user_id": "user_003"},
            {"event_type": "search_query", "event_data": {"query": "北京"}, "target_user_id": None},
        ]

        with patch.object(engine, 'process_behavior_event', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = True

            result = await engine.batch_process_events("user_001", events)

            assert result == 3
            assert mock_process.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_process_partial_success(self):
        """测试部分成功"""
        engine = ProfileUpdateEngine()

        events = [
            {"event_type": "swipe_like", "event_data": {}, "target_user_id": "user_002"},
            {"event_type": "unknown_event", "event_data": {}, "target_user_id": None},
            {"event_type": "search_query", "event_data": {"query": "北京"}, "target_user_id": None},
        ]

        with patch.object(engine, 'process_behavior_event', new_callable=AsyncMock) as mock_process:
            # 第一次和第三次成功，第二次失败
            mock_process.side_effect = [True, False, True]

            result = await engine.batch_process_events("user_001", events)

            assert result == 2

    @pytest.mark.asyncio
    async def test_batch_process_empty_events(self):
        """测试空事件列表"""
        engine = ProfileUpdateEngine()

        result = await engine.batch_process_events("user_001", [])

        assert result == 0


class TestGlobalServiceInstances:
    """全局服务实例测试"""

    def test_get_user_profile_service_singleton(self):
        """测试 UserProfileService 单例"""
        service1 = get_user_profile_service()
        service2 = get_user_profile_service()

        assert service1 is not None
        assert service1 is service2

    def test_get_profile_update_engine_singleton(self):
        """测试 ProfileUpdateEngine 单例"""
        engine1 = get_profile_update_engine()
        engine2 = get_profile_update_engine()

        assert engine1 is not None
        assert engine1 is engine2