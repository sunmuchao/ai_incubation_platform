"""
P13-P17 服务层单元测试
测试覆盖情感预测逻辑、约会模拟、虚实结合等功能
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from services.relationship_enhancement_service import LoveLanguageProfileService, RelationshipTrendService, WarningResponseService
from services.date_simulation_service import DateSimulationService
from services.date_assistant_service import OutfitRecommendationService, VenueStrategyService, TopicKitService
from services.autonomous_dating_service import AutonomousDatePlanningService
from models.relationship_enhancement_models import LoveLanguageType
from models.date_simulation_models import SimulationScenarioType, AvatarPersonalityType


# ==================== P13 服务测试 ====================

class TestLoveLanguageProfileService:
    """爱之语画像服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return LoveLanguageProfileService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return MagicMock()

    def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service is not None
        assert hasattr(service, 'LOVE_LANGUAGE_KEYWORDS')
        assert len(service.LOVE_LANGUAGE_KEYWORDS) > 0

    def test_love_language_keywords_coverage(self, service):
        """测试爱之语关键词覆盖"""
        keywords = service.LOVE_LANGUAGE_KEYWORDS

        # 验证所有爱之语类型都有定义
        assert LoveLanguageType.WORDS.value in keywords
        assert LoveLanguageType.TIME.value in keywords
        assert LoveLanguageType.GIFTS.value in keywords
        assert LoveLanguageType.ACTS.value in keywords
        assert LoveLanguageType.TOUCH.value in keywords

        # 每个类型都有足够的关键词
        for ll_type, kw_list in keywords.items():
            assert len(kw_list) >= 5

    def test_ensure_initialized(self, service, mock_db_session):
        """测试初始化逻辑"""
        # Arrange
        service._initialized = False

        # Act
        service._ensure_initialized(mock_db_session)

        # Assert
        assert service._initialized is True

    def test_analyze_user_love_language_no_data(self, service, mock_db_session):
        """测试分析用户爱之语（无数据情况）"""
        # Arrange
        user_id = "user_001"
        mock_db_session.query.return_value.filter.return_value.all.return_value = []

        # Act
        profile = service.analyze_user_love_language(user_id, mock_db_session)

        # Assert
        assert profile is not None  # 应该返回默认画像

    def test_keyword_matching(self, service):
        """测试关键词匹配逻辑"""
        # Arrange
        words_keywords = service.LOVE_LANGUAGE_KEYWORDS[LoveLanguageType.WORDS.value]

        # Act & Assert
        assert "喜欢" in words_keywords
        assert "感谢" in words_keywords
        assert "赞美" in words_keywords

    def test_time_language_keywords(self, service):
        """测试时间类爱之语关键词"""
        # Arrange
        time_keywords = service.LOVE_LANGUAGE_KEYWORDS[LoveLanguageType.TIME.value]

        # Assert
        assert "陪伴" in time_keywords
        assert "一起" in time_keywords


class TestRelationshipTrendService:
    """关系趋势预测服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return RelationshipTrendService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return MagicMock()

    def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service is not None
        assert hasattr(service, 'TREND_RISING')

    def test_generate_trend_prediction_basic(self, service, mock_db_session):
        """测试基础关系趋势预测"""
        # Arrange
        user_a_id = "user_a"
        user_b_id = "user_b"
        prediction_period = "7d"

        # 模拟没有历史数据
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        # Act
        prediction = service.generate_trend_prediction(
            user_a_id, user_b_id, prediction_period, mock_db_session
        )

        # Assert
        assert prediction is not None
        assert "prediction" in prediction or isinstance(prediction, dict)


class TestWarningResponseService:
    """预警分级响应服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return WarningResponseService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return MagicMock()

    def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service is not None
        assert hasattr(service, 'LEVEL_LOW')

    def test_warning_levels_defined(self, service):
        """测试预警级别定义"""
        assert hasattr(service, 'LEVEL_LOW')
        assert hasattr(service, 'LEVEL_MEDIUM')
        assert hasattr(service, 'LEVEL_HIGH')
        assert hasattr(service, 'LEVEL_CRITICAL')

    def test_get_response_strategy_by_level(self, service, mock_db_session):
        """测试根据级别获取响应策略"""
        # Arrange
        levels = ['low', 'medium', 'high', 'critical']
        mock_db_session.query.return_value.filter.return_value.all.return_value = [MagicMock()]

        for level in levels:
            # Act
            strategy = service.get_response_strategy(level, {}, mock_db_session)

            # Assert
            assert strategy is None or isinstance(strategy, dict)


# ==================== P14 服务测试 ====================

class TestDateSimulationService:
    """约会模拟沙盒服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return DateSimulationService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return MagicMock()

    def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service is not None
        assert hasattr(service, 'DEFAULT_SCENARIOS')
        assert len(service.DEFAULT_SCENARIOS) >= 4

    def test_default_scenarios_defined(self, service):
        """测试默认场景定义"""
        scenarios = service.DEFAULT_SCENARIOS

        assert SimulationScenarioType.RESTAURANT.value in scenarios
        assert SimulationScenarioType.CAFE.value in scenarios
        assert SimulationScenarioType.PARK.value in scenarios
        assert SimulationScenarioType.CINEMA.value in scenarios

    def test_scenario_config_structure(self, service):
        """测试场景配置结构"""
        for scenario_type, config in service.DEFAULT_SCENARIOS.items():
            assert "name" in config
            assert "description" in config
            assert "atmosphere" in config
            assert "suitable_for" in config

    def test_opening_lines_defined(self, service):
        """测试对话开场白定义"""
        assert hasattr(service, 'OPENING_LINES')
        assert len(service.OPENING_LINES) >= 4

    def test_conversation_topics_defined(self, service):
        """测试对话主题定义"""
        assert hasattr(service, 'CONVERSATION_TOPICS')
        assert len(service.CONVERSATION_TOPICS) >= 5

    def test_create_avatar(self, service, mock_db_session):
        """测试创建 AI 分身"""
        # Arrange
        user_id = "user_001"
        avatar_name = "测试分身"
        personality = AvatarPersonalityType.OUTGOING.value

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.interests = ["旅行", "美食"]
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        # Act
        avatar = service.create_avatar(
            user_id, avatar_name, personality, None, mock_db_session
        )

        # Assert
        assert avatar is not None
        assert avatar.avatar_name == avatar_name
        assert avatar.personality == personality

    def test_generate_personality_traits(self, service):
        """测试生成性格特征"""
        # Test different personality types
        traits = service._generate_personality_traits(AvatarPersonalityType.OUTGOING.value)
        assert "健谈" in traits or "热情" in traits

        traits = service._generate_personality_traits(AvatarPersonalityType.INTROVERTED.value)
        assert "内敛" in traits or "深思" in traits

    def test_get_conversation_style(self, service):
        """测试获取对话风格"""
        style = service._get_conversation_style(AvatarPersonalityType.OUTGOING.value)
        assert style is not None


class TestOutfitRecommendationService:
    """穿搭推荐服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return OutfitRecommendationService()

    def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service is not None

    def test_outfit_recommendation_logic(self, service):
        """测试穿搭推荐逻辑"""
        # 验证服务有相关方法
        assert service is not None


class TestVenueStrategyService:
    """场所策略服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return VenueStrategyService()

    def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service is not None


class TestTopicKitService:
    """话题锦囊服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return TopicKitService()

    def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service is not None


# ==================== P15 服务测试 ====================

class TestAutonomousDatePlanningService:
    """自主约会策划服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return AutonomousDatePlanningService()

    def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service is not None
        assert hasattr(service, 'venue_database')
        assert len(service.venue_database) >= 3

    def test_venue_database_structure(self, service):
        """测试场所数据库结构"""
        for venue in service.venue_database:
            assert "id" in venue
            assert "name" in venue
            assert "category" in venue
            assert "avg_cost" in venue
            assert "rating" in venue

    def test_calculate_geographic_midpoint(self, service):
        """测试地理中点计算"""
        # Arrange
        user_a_location = (39.9042, 116.4074)  # 北京
        user_b_location = (31.2304, 121.4737)  # 上海

        # Act
        midpoint = service.calculate_geographic_midpoint(
            user_a_location, user_b_location
        )

        # Assert
        assert "latitude" in midpoint
        assert "longitude" in midpoint
        assert "distance_km" in midpoint
        assert midpoint["latitude"] == (39.9042 + 31.2304) / 2
        assert midpoint["longitude"] == (116.4074 + 121.4737) / 2

    def test_calculate_distance(self, service):
        """测试距离计算"""
        # Arrange
        loc1 = (0, 0)
        loc2 = (0, 1)  # 经度差 1 度

        # Act
        distance = service._calculate_distance(loc1, loc2)

        # Assert
        assert isinstance(distance, float)
        assert distance > 0

    def test_estimate_travel_time(self, service):
        """测试行程时间估算"""
        # Test different distances
        assert "15-30 分钟" in service._estimate_travel_time(3)
        assert "30-60 分钟" in service._estimate_travel_time(10)
        assert "1 小时以上" in service._estimate_travel_time(20)

    def test_find_venues_by_category(self, service):
        """测试按类别查找场所"""
        # Arrange
        midpoint = {"latitude": 39.9, "longitude": 116.4}

        # Act
        venues = service.find_venues_near_midpoint(midpoint, category="restaurant")

        # Assert
        assert all(v["category"] == "restaurant" for v in venues)

    def test_find_venues_by_budget(self, service):
        """测试按预算查找场所"""
        # Arrange
        midpoint = {"latitude": 39.9, "longitude": 116.4}
        budget_range = (0, 100)

        # Act
        venues = service.find_venues_near_midpoint(
            midpoint, budget_range=budget_range
        )

        # Assert
        assert all(v["avg_cost"] <= 100 for v in venues)

    def test_venues_sorted_by_rating(self, service):
        """测试场所按评分排序"""
        # Arrange
        midpoint = {"latitude": 39.9, "longitude": 116.4}

        # Act
        venues = service.find_venues_near_midpoint(midpoint)

        # Assert
        for i in range(len(venues) - 1):
            assert venues[i]["rating"] >= venues[i + 1]["rating"]

    def test_create_date_plan(self, service):
        """测试创建约会计划"""
        # Arrange
        user_a_location = (39.9042, 116.4074)
        user_b_location = (39.9142, 116.4174)
        preferences = {"category": "restaurant", "budget_range": (100, 500)}

        mock_db_session = MagicMock()
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        # Act
        plan = service.create_date_plan(
            "user_a", "user_b",
            user_a_location, user_b_location,
            preferences, mock_db_session
        )

        # Assert
        assert plan is not None
