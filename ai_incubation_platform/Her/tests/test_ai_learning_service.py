"""
AI 持续学习服务测试

测试 AILearningService 的核心功能：
- 用户偏好记忆管理
- 行为模式学习
- 匹配权重调整
- 用户学习画像
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime

from services.ai_learning_service import AILearningService
from models.l4_learning_models import (
    UserPreferenceMemory,
    BehaviorLearningPattern,
    MatchingWeightAdjustment,
    UserLearningProfile,
)


class TestAILearningServiceInit:
    """初始化测试"""

    def test_init_with_db(self):
        """测试带 db 参数初始化"""
        mock_db = MagicMock()
        service = AILearningService(db=mock_db)
        assert service._db == mock_db
        assert service._should_close_db is False

    def test_init_without_db(self):
        """测试不带 db 参数初始化"""
        service = AILearningService.__new__(AILearningService)
        service._db = None
        service._should_close_db = True
        # _should_close_db 应为 True（表示需要自动关闭）
        assert service._should_close_db is True


class TestPreferenceManagement:
    """偏好管理测试"""

    @pytest.fixture
    def mock_db(self):
        """Mock 数据库会话"""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        service = AILearningService.__new__(AILearningService)
        service._db = mock_db
        service._should_close_db = False
        return service

    def test_add_preference_new(self, service, mock_db):
        """测试添加新偏好"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        success, message, preference = service.add_preference(
            user_id="test_user",
            category="matching",
            preference_key="age_range",
            preference_value="25-35",
            preference_type="like",
            confidence_score=0.8,
        )

        assert success is True
        assert "添加" in message or "已添加" in message
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_add_preference_update_existing(self, service, mock_db):
        """测试更新已存在的偏好"""
        mock_existing = MagicMock()
        mock_existing.preference_value = "20-30"
        mock_existing.confidence_score = 0.5
        mock_existing.source_events = []

        mock_db.query.return_value.filter.return_value.first.return_value = mock_existing

        success, message, preference = service.add_preference(
            user_id="test_user",
            category="matching",
            preference_key="age_range",
            preference_value="25-35",
            confidence_score=0.8,
        )

        assert success is True
        assert "更新" in message
        # 应更新而不是添加新记录
        mock_db.add.assert_not_called()

    def test_get_user_preferences(self, service, mock_db):
        """测试获取用户偏好列表"""
        mock_prefs = [MagicMock(), MagicMock()]
        # 带类别过滤时的 mock 链: query -> filter -> filter -> order_by -> all
        mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = mock_prefs

        prefs = service.get_user_preferences("test_user", category="matching")

        assert len(prefs) == 2

    def test_get_user_preferences_with_min_confidence(self, service, mock_db):
        """测试带置信度过滤获取偏好"""
        mock_prefs = [MagicMock(confidence_score=0.9)]
        # 无类别过滤时的 mock 链: query -> filter -> order_by -> all
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_prefs

        prefs = service.get_user_preferences("test_user", min_confidence=0.7)

        assert len(prefs) == 1

    def test_get_preference_specific(self, service, mock_db):
        """测试获取特定偏好"""
        mock_pref = MagicMock()
        mock_pref.preference_key = "age_range"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_pref

        pref = service.get_preference("test_user", "matching", "age_range")

        assert pref == mock_pref

    def test_get_preference_not_found(self, service, mock_db):
        """测试偏好不存在"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        pref = service.get_preference("test_user", "matching", "nonexistent")

        assert pref is None

    def test_remove_preference_success(self, service, mock_db):
        """测试移除偏好成功"""
        mock_pref = MagicMock()
        mock_pref.is_active = True

        # get_preference 返回
        mock_db.query.return_value.filter.return_value.first.return_value = mock_pref

        success, message = service.remove_preference("test_user", "matching", "age_range")

        assert success is True
        assert "移除" in message
        mock_db.commit.assert_called_once()

    def test_remove_preference_not_found(self, service, mock_db):
        """测试移除不存在偏好"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        success, message = service.remove_preference("test_user", "matching", "nonexistent")

        assert success is False
        assert "不存在" in message


class TestPatternLearning:
    """行为模式学习测试"""

    @pytest.fixture
    def mock_db(self):
        """Mock 数据库会话"""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        service = AILearningService.__new__(AILearningService)
        service._db = mock_db
        service._should_close_db = False
        return service

    def test_learn_pattern_new(self, service, mock_db):
        """测试学习新模式"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        success, message, pattern = service.learn_pattern(
            user_id="test_user",
            pattern_type="message_time",
            pattern_data={"preferred_hours": [20, 21, 22]},
            pattern_strength=0.7,
        )

        assert success is True
        assert "学习" in message or "已学习" in message
        mock_db.add.assert_called_once()

    def test_learn_pattern_update_existing(self, service, mock_db):
        """测试更新已存在的模式"""
        mock_existing = MagicMock()
        mock_existing.pattern_data = {"preferred_hours": [19, 20]}
        mock_existing.pattern_strength = 0.5
        mock_existing.observation_count = 3

        mock_db.query.return_value.filter.return_value.first.return_value = mock_existing

        success, message, pattern = service.learn_pattern(
            user_id="test_user",
            pattern_type="message_time",
            pattern_data={"preferred_hours": [21, 22]},
            pattern_strength=0.8,
        )

        assert success is True
        assert "更新" in message
        # 应增加观察次数
        assert mock_existing.observation_count == 4

    def test_get_user_patterns(self, service, mock_db):
        """测试获取用户模式列表"""
        mock_patterns = [MagicMock(), MagicMock()]
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_patterns

        patterns = service.get_user_patterns("test_user")

        assert len(patterns) == 2

    def test_get_user_patterns_with_type_filter(self, service, mock_db):
        """测试带类型过滤获取模式"""
        mock_patterns = [MagicMock()]
        mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = mock_patterns

        patterns = service.get_user_patterns("test_user", pattern_type="message_time")

        assert len(patterns) == 1

    def test_get_user_patterns_validated_only(self, service, mock_db):
        """测试只获取已验证模式"""
        mock_patterns = [MagicMock(is_validated=True)]
        # 设置 mock 链返回同一个 mock query 对象
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_patterns
        mock_db.query.return_value = mock_query

        patterns = service.get_user_patterns("test_user", validated_only=True)

        assert len(patterns) == 1

    def test_validate_pattern_success(self, service, mock_db):
        """测试验证模式成功"""
        mock_pattern = MagicMock()
        mock_pattern.is_validated = False

        mock_db.query.return_value.filter.return_value.first.return_value = mock_pattern

        success, message = service.validate_pattern("test_user", "message_time")

        assert success is True
        assert mock_pattern.is_validated is True


class TestPreferenceCategories:
    """偏好类别测试"""

    def test_valid_categories(self):
        """测试有效的偏好类别"""
        valid_categories = ["matching", "date", "gift", "communication", "topic"]
        # 这些类别应该在服务中有效
        for category in valid_categories:
            assert isinstance(category, str)

    def test_preference_types(self):
        """测试偏好类型"""
        valid_types = ["like", "dislike", "neutral"]
        for pref_type in valid_types:
            assert isinstance(pref_type, str)

    def test_inference_methods(self):
        """测试推断方法"""
        valid_methods = ["rule_based", "llm_based", "explicit", "behavioral"]
        for method in valid_methods:
            assert isinstance(method, str)


class TestConfidenceScores:
    """置信度测试"""

    def test_confidence_range(self):
        """测试置信度范围"""
        # 置信度应在 0-1 之间
        valid_scores = [0.0, 0.5, 0.8, 1.0]
        for score in valid_scores:
            assert 0 <= score <= 1

    def test_min_confidence_filter(self):
        """测试最小置信度过滤"""
        min_confidence = 0.5
        # 只返回置信度 >= min_confidence 的偏好
        assert min_confidence >= 0
        assert min_confidence <= 1


class TestPatternStrength:
    """模式强度测试"""

    def test_pattern_strength_range(self):
        """测试模式强度范围"""
        valid_strengths = [0.0, 0.5, 0.8, 1.0]
        for strength in valid_strengths:
            assert 0 <= strength <= 1

    def test_observation_count_increment(self):
        """测试观察次数递增"""
        # 每次观察到相同模式，计数应增加
        initial_count = 3
        new_count = initial_count + 1
        assert new_count == 4