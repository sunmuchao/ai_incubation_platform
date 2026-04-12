"""
P14 实战演习服务单元测试
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import json

from services.date_simulation_service import (
    DateSimulationService,
)
from services.couple_game_service import (
    CoupleGameService,
    GAME_TYPES,
    QUESTION_POOLS,
)
from models.date_simulation_models import (
    SimulationScenarioType,
    AvatarPersonalityType,
)


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

    def test_create_avatar(self, service, mock_db_session):
        """测试创建 AI 约会分身"""
        # Arrange
        user_id = "user_001"
        avatar_name = "测试分身"
        personality = AvatarPersonalityType.OUTGOING.value
        interests = ["音乐", "旅行"]

        # Mock user
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.interests = ["音乐", "旅行", "阅读"]

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        # Act
        avatar = service.create_avatar(
            user_id, avatar_name, personality, interests, mock_db_session
        )

        # Assert
        assert avatar is not None
        assert avatar.avatar_name == avatar_name
        assert avatar.personality == personality
        mock_db_session.add.assert_called_once()

    def test_create_avatar_without_interests(self, service, mock_db_session):
        """测试创建分身时不指定兴趣（使用用户兴趣）"""
        # Arrange
        user_id = "user_001"
        avatar_name = "测试分身"
        personality = AvatarPersonalityType.INTROVERTED.value

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.interests = ["阅读", "电影"]

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
        assert avatar.interests == ["阅读", "电影"]

    def test_generate_personality_traits(self, service):
        """测试生成性格特征"""
        # Test different personality types
        traits = service._generate_personality_traits(AvatarPersonalityType.OUTGOING.value)
        assert "健谈" in traits
        assert "热情" in traits

        traits = service._generate_personality_traits(AvatarPersonalityType.INTROVERTED.value)
        assert "内敛" in traits
        assert "深思" in traits

        traits = service._generate_personality_traits(AvatarPersonalityType.HUMOROUS.value)
        assert "幽默" in traits
        assert "风趣" in traits

        traits = service._generate_personality_traits(AvatarPersonalityType.SERIOUS.value)
        assert "认真" in traits
        assert "稳重" in traits

    def test_get_conversation_style(self, service):
        """测试获取对话风格"""
        # Test different personality types
        style = service._get_conversation_style(AvatarPersonalityType.OUTGOING.value)
        assert style == "casual"

        style = service._get_conversation_style(AvatarPersonalityType.INTROVERTED.value)
        assert style == "thoughtful"

        style = service._get_conversation_style(AvatarPersonalityType.HUMOROUS.value)
        assert style == "playful"

    def test_get_avatar(self, service, mock_db_session):
        """测试获取 AI 分身"""
        # Arrange
        avatar_id = "avatar_001"

        mock_avatar = MagicMock()
        mock_avatar.id = avatar_id
        mock_avatar.user_id = "user_001"
        mock_avatar.avatar_name = "测试分身"
        mock_avatar.is_active = True

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_avatar

        # Act
        avatar = service.get_avatar(avatar_id, mock_db_session)

        # Assert
        assert avatar is not None
        assert avatar.id == avatar_id

    def test_get_avatar_not_found(self, service, mock_db_session):
        """测试获取不存在的分身"""
        # Arrange
        avatar_id = "avatar_not_exist"

        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act
        avatar = service.get_avatar(avatar_id, mock_db_session)

        # Assert
        assert avatar is None

    def test_get_user_avatars(self, service, mock_db_session):
        """测试获取用户的分身列表"""
        # Arrange
        user_id = "user_001"

        mock_avatar1 = MagicMock()
        mock_avatar1.id = "avatar_001"
        mock_avatar1.user_id = user_id
        mock_avatar1.is_active = True

        mock_avatar2 = MagicMock()
        mock_avatar2.id = "avatar_002"
        mock_avatar2.user_id = user_id
        mock_avatar2.is_active = True

        mock_db_session.query.return_value.filter.return_value.all.return_value = [
            mock_avatar1, mock_avatar2
        ]

        # Act
        avatars = service.get_user_avatars(user_id, mock_db_session)

        # Assert
        assert len(avatars) == 2

    def test_start_simulation(self, service, mock_db_session):
        """测试开始约会模拟"""
        # Arrange
        user_id = "user_001"
        avatar_id = "avatar_001"
        scenario = SimulationScenarioType.RESTAURANT.value
        simulation_goal = "练习首次约会对话"

        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        # Act
        simulation = service.start_simulation(
            user_id, avatar_id, scenario, simulation_goal, mock_db_session
        )

        # Assert
        assert simulation is not None
        assert simulation.scenario == scenario
        assert simulation.simulation_goal == simulation_goal
        assert simulation.status == "ongoing"
        mock_db_session.add.assert_called_once()

    def test_start_simulation_custom_scenario(self, service, mock_db_session):
        """测试开始自定义场景模拟"""
        # Arrange
        user_id = "user_001"
        avatar_id = "avatar_001"
        scenario = "custom_scenario"
        simulation_goal = "自定义模拟"

        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        # Act
        simulation = service.start_simulation(
            user_id, avatar_id, scenario, simulation_goal, mock_db_session
        )

        # Assert
        assert simulation is not None
        assert scenario in simulation.scenario_description

    def test_add_message_to_simulation(self, service, mock_db_session):
        """测试添加消息到模拟对话"""
        # Arrange
        simulation_id = "sim_001"
        role = "user"
        content = "你好，很高兴见到你！"

        mock_simulation = MagicMock()
        mock_simulation.id = simulation_id
        mock_simulation.conversation_history = []
        mock_simulation.message_count = 0

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_simulation
        mock_db_session.commit.return_value = None

        # Act
        result = service.add_message_to_simulation(
            simulation_id, role, content, mock_db_session
        )

        # Assert
        assert result == True
        assert len(mock_simulation.conversation_history) == 1
        assert mock_simulation.conversation_history[0]["role"] == role
        assert mock_simulation.conversation_history[0]["content"] == content
        assert mock_simulation.message_count == 1

    def test_add_message_to_simulation_not_found(self, service, mock_db_session):
        """测试添加到不存在的模拟"""
        # Arrange
        simulation_id = "sim_not_exist"
        role = "user"
        content = "你好"

        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act
        result = service.add_message_to_simulation(
            simulation_id, role, content, mock_db_session
        )

        # Assert
        assert result == False

    def test_complete_simulation(self, service, mock_db_session):
        """测试完成模拟"""
        # Arrange
        simulation_id = "sim_001"
        self_rating = 8

        mock_simulation = MagicMock()
        mock_simulation.id = simulation_id
        mock_simulation.avatar_id = "avatar_001"
        mock_simulation.is_completed = False
        mock_simulation.status = "ongoing"
        mock_simulation.created_at = datetime(2024, 1, 15, 10, 0)

        mock_avatar = MagicMock()
        mock_avatar.id = "avatar_001"
        mock_avatar.usage_count = 5

        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            mock_simulation, mock_avatar
        ]
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        # Act
        simulation = service.complete_simulation(
            simulation_id, self_rating, mock_db_session
        )

        # Assert
        assert simulation.is_completed == True
        assert simulation.status == "completed"
        assert simulation.self_rating == self_rating
        assert mock_avatar.usage_count == 6  # 使用次数 +1

    def test_complete_simulation_not_found(self, service, mock_db_session):
        """测试完成不存在的模拟"""
        # Arrange
        simulation_id = "sim_not_exist"

        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act & Assert
        with pytest.raises(ValueError):
            service.complete_simulation(simulation_id, None, mock_db_session)

    def test_generate_feedback(self, service, mock_db_session):
        """测试生成模拟反馈"""
        # Arrange
        simulation_id = "sim_001"

        mock_simulation = MagicMock()
        mock_simulation.id = simulation_id
        mock_simulation.conversation_history = [
            {"role": "user", "content": "你好，很高兴见到你！", "timestamp": "2024-01-15T10:00:00"},
            {"role": "ai", "content": "你好，我也很高兴见到你！", "timestamp": "2024-01-15T10:00:30"},
            {"role": "user", "content": "这家餐厅环境不错", "timestamp": "2024-01-15T10:01:00"},
            {"role": "ai", "content": "是的，我也很喜欢这里", "timestamp": "2024-01-15T10:01:30"},
        ]

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_simulation
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        # Act
        feedback = service.generate_feedback(simulation_id, mock_db_session)

        # Assert
        assert feedback is not None
        assert feedback.simulation_id == simulation_id
        assert feedback.overall_score >= 1
        assert feedback.overall_score <= 10
        mock_db_session.add.assert_called_once()

    def test_generate_feedback_no_data(self, service, mock_db_session):
        """测试生成反馈（无数据）"""
        # Arrange
        simulation_id = "sim_001"

        mock_simulation = MagicMock()
        mock_simulation.id = simulation_id
        mock_simulation.conversation_history = []

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_simulation

        # Act & Assert
        with pytest.raises(ValueError):
            service.generate_feedback(simulation_id, mock_db_session)

    def test_analyze_conversation(self, service):
        """测试分析对话历史"""
        # Arrange
        conversation_history = [
            {"role": "user", "content": "你好，很高兴见到你！", "timestamp": "2024-01-15T10:00:00"},
            {"role": "ai", "content": "你好，我也很高兴见到你！", "timestamp": "2024-01-15T10:00:30"},
            {"role": "user", "content": "这家餐厅环境不错，你喜欢意大利菜吗？", "timestamp": "2024-01-15T10:01:00"},
            {"role": "ai", "content": "是的，我也很喜欢这里的氛围", "timestamp": "2024-01-15T10:01:30"},
            {"role": "user", "content": "那太好了，我们可以多点几道菜尝尝", "timestamp": "2024-01-15T10:02:00"},
        ]

        # Act
        analysis = service._analyze_conversation(conversation_history)

        # Assert
        assert "overall_score" in analysis
        assert "conversation_score" in analysis
        assert "empathy_score" in analysis
        assert "humor_score" in analysis
        assert "confidence_score" in analysis
        assert "listening_score" in analysis
        assert "comments" in analysis
        assert "highlights" in analysis
        assert "suggestions" in analysis

    def test_generate_comments(self, service):
        """测试生成 AI 评语"""
        # Test high score
        comments = service._generate_comments(8, [])
        assert "出色" in comments or "好" in comments

        # Test medium score
        comments = service._generate_comments(6, [])
        assert "不错" in comments

        # Test low score
        comments = service._generate_comments(4, [])
        assert "进步空间" in comments or "练习" in comments

    def test_extract_key_moments(self, service):
        """测试提取关键时刻"""
        # Arrange
        conversation_history = [
            {"role": "user", "content": "消息 1", "timestamp": "2024-01-15T10:00:00"},
            {"role": "ai", "content": "消息 2", "timestamp": "2024-01-15T10:00:30"},
            {"role": "user", "content": "消息 3", "timestamp": "2024-01-15T10:01:00"},
            {"role": "ai", "content": "消息 4", "timestamp": "2024-01-15T10:01:30"},
        ]

        # Act
        key_moments = service._extract_key_moments(conversation_history)

        # Assert
        assert len(key_moments) > 0
        assert "index" in key_moments[0]
        assert "role" in key_moments[0]
        assert "content" in key_moments[0]

    def test_get_simulation(self, service, mock_db_session):
        """测试获取模拟记录"""
        # Arrange
        simulation_id = "sim_001"

        mock_simulation = MagicMock()
        mock_simulation.id = simulation_id
        mock_simulation.user_id = "user_001"

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_simulation

        # Act
        simulation = service.get_simulation(simulation_id, mock_db_session)

        # Assert
        assert simulation is not None
        assert simulation.id == simulation_id

    def test_get_simulation_not_found(self, service, mock_db_session):
        """测试获取不存在的模拟"""
        # Arrange
        simulation_id = "sim_not_exist"

        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act
        simulation = service.get_simulation(simulation_id, mock_db_session)

        # Assert
        assert simulation is None

    def test_get_user_simulations(self, service, mock_db_session):
        """测试获取用户的模拟历史"""
        # Arrange
        user_id = "user_001"
        limit = 10

        mock_sim1 = MagicMock()
        mock_sim1.id = "sim_001"
        mock_sim1.user_id = user_id

        mock_sim2 = MagicMock()
        mock_sim2.id = "sim_002"
        mock_sim2.user_id = user_id

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            mock_sim1, mock_sim2
        ]

        # Act
        simulations = service.get_user_simulations(user_id, mock_db_session, limit)

        # Assert
        assert len(simulations) == 2

    def test_get_simulation_feedback(self, service, mock_db_session):
        """测试获取模拟反馈"""
        # Arrange
        simulation_id = "sim_001"

        mock_feedback = MagicMock()
        mock_feedback.id = "feedback_001"
        mock_feedback.simulation_id = simulation_id

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_feedback

        # Act
        feedback = service.get_simulation_feedback(simulation_id, mock_db_session)

        # Assert
        assert feedback is not None
        assert feedback.simulation_id == simulation_id

    def test_default_scenarios_complete(self, service):
        """测试默认场景配置完整性"""
        # Assert
        assert SimulationScenarioType.RESTAURANT.value in service.DEFAULT_SCENARIOS
        assert SimulationScenarioType.CAFE.value in service.DEFAULT_SCENARIOS
        assert SimulationScenarioType.PARK.value in service.DEFAULT_SCENARIOS
        assert SimulationScenarioType.CINEMA.value in service.DEFAULT_SCENARIOS

        # Verify scenario structure
        for scenario_type, config in service.DEFAULT_SCENARIOS.items():
            assert "name" in config
            assert "description" in config
            assert "atmosphere" in config
            assert "suitable_for" in config


class TestCoupleGameService:
    """双人互动游戏服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return CoupleGameService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return MagicMock()

    def test_create_couple_game(self, service, mock_db_session):
        """测试创建双人互动游戏"""
        # Arrange
        user_id_1 = "user_001"
        user_id_2 = "user_002"
        game_type = "qna_mutual"  # Use valid game type
        difficulty = "normal"

        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        # Mock match history to indicate users are matched
        mock_match = MagicMock()
        mock_match.relationship_stage = "dating"

        # Create a mock query that returns the match for ANY call
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_match

        # Always return the mock_query for any query call
        mock_db_session.query.return_value = mock_query

        # Act - note: game_config is None (default), then difficulty, then db_session
        game_id = service.create_couple_game(
            user_id_1, user_id_2, game_type, None, difficulty, mock_db_session
        )

        # Assert
        assert game_id is not None

    def test_get_game_types(self):
        """测试游戏类型定义"""
        # Assert
        assert "qna_mutual" in GAME_TYPES
        assert "values_quiz" in GAME_TYPES
        assert "preference_match" in GAME_TYPES

    def test_question_pools_exist(self):
        """测试问题库配置存在"""
        # Assert
        assert len(QUESTION_POOLS) > 0
        assert "mutual" in QUESTION_POOLS
        assert "values" in QUESTION_POOLS
        assert "preference" in QUESTION_POOLS
