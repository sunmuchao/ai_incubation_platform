"""
关系偏好服务测试

测试覆盖:
- 关系类型标签
- 关系状态
- 偏好更新
- 兼容性匹配
"""
import pytest
import os
import sys
from unittest.mock import MagicMock, patch
from datetime import datetime

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置环境变量
os.environ['OPENAI_API_KEY'] = 'test-key'
os.environ['OPENAI_BASE_URL'] = 'https://test.api/v1'


class TestRelationshipPreferenceService:
    """关系偏好服务测试"""

    @pytest.fixture
    def mock_db(self):
        """创建 mock 数据库会话"""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_db):
        """创建测试服务"""
        from services.relationship_preference_service import RelationshipPreferenceService
        return RelationshipPreferenceService(mock_db)

    def test_init(self, service):
        """测试初始化"""
        assert service is not None
        assert service.db is not None

    def test_get_all_relationship_types(self, service):
        """测试获取所有关系类型"""
        types = service.get_all_relationship_types()

        assert len(types) == 8
        type_keys = [t["key"] for t in types]
        assert "serious_relationship" in type_keys
        assert "casual_dating" in type_keys
        assert "marriage_minded" in type_keys
        assert "friendship_first" in type_keys
        assert "networking" in type_keys
        assert "not_sure" in type_keys
        assert "open_to_explore" in type_keys
        assert "polyamory" in type_keys

    def test_get_all_relationship_statuses(self, service):
        """测试获取所有关系状态"""
        statuses = service.get_all_relationship_statuses()

        assert len(statuses) == 6
        status_keys = [s["key"] for s in statuses]
        assert "single" in status_keys
        assert "in_relationship" in status_keys
        assert "married" in status_keys
        assert "divorced" in status_keys
        assert "widowed" in status_keys
        assert "complicated" in status_keys

    def test_get_user_preferences_existing(self, service, mock_db):
        """测试获取已有用户偏好"""
        mock_pref = MagicMock()
        mock_pref.user_id = 'user_001'
        mock_pref.relationship_types = '["serious_relationship", "casual_dating"]'
        mock_pref.current_status = 'single'
        mock_pref.expectation_description = '寻找真爱'
        mock_pref.created_at = datetime.now()
        mock_pref.updated_at = datetime.now()

        mock_db.query.return_value.filter.return_value.first.return_value = mock_pref

        result = service.get_user_preferences('user_001')

        assert result is not None
        assert result["user_id"] == 'user_001'
        assert len(result["relationship_types"]) == 2

    def test_get_user_preferences_not_found(self, service, mock_db):
        """测试获取不存在的用户偏好"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = service.get_user_preferences('nonexistent')

        assert result is None

    def test_update_preferences_create(self, service, mock_db):
        """测试创建用户偏好"""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        result = service.update_preferences(
            user_id='user_001',
            relationship_types=['serious_relationship'],
            current_status='single',
            expectation_description='寻找真爱'
        )

        mock_db.add.assert_called()

    def test_update_preferences_update(self, service, mock_db):
        """测试更新用户偏好"""
        mock_pref = MagicMock()
        mock_pref.user_id = 'user_001'
        mock_pref.relationship_types = '[]'
        mock_pref.current_status = None
        mock_pref.expectation_description = None

        mock_db.query.return_value.filter.return_value.first.return_value = mock_pref
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        # Mock get_user_preferences for return
        with patch.object(service, 'get_user_preferences', return_value={"user_id": "user_001"}):
            result = service.update_preferences(
                user_id='user_001',
                relationship_types=['serious_relationship'],
                current_status='single'
            )

        assert result is not None

    def test_update_preferences_invalid_type(self, service, mock_db):
        """测试更新无效关系类型"""
        with pytest.raises(ValueError):
            service.update_preferences(
                user_id='user_001',
                relationship_types=['invalid_type']
            )

    def test_update_preferences_invalid_status(self, service, mock_db):
        """测试更新无效关系状态"""
        with pytest.raises(ValueError):
            service.update_preferences(
                user_id='user_001',
                current_status='invalid_status'
            )

    def test_match_relationship_compatibility_no_prefs(self, service, mock_db):
        """测试无偏好时的兼容性匹配"""
        with patch.object(service, 'get_user_preferences', return_value=None):
            result = service.match_relationship_compatibility('user_001', 'user_002')

        assert result["compatible"] is False
        assert result["score"] == 0

    def test_match_relationship_compatibility_high(self, service, mock_db):
        """测试高兼容性匹配"""
        user_pref = {
            "relationship_types": [{"key": "serious_relationship"}],
            "current_status": "single",
            "expectation_description": "寻找真爱 期待长久"
        }
        target_pref = {
            "relationship_types": [{"key": "serious_relationship"}],
            "current_status": "single",
            "expectation_description": "寻找真爱 期待长久"
        }

        with patch.object(service, 'get_user_preferences', side_effect=[user_pref, target_pref]):
            result = service.match_relationship_compatibility('user_001', 'user_002')

        assert result["compatible"] is True
        assert result["score"] >= 50

    def test_match_relationship_compatibility_low(self, service, mock_db):
        """测试低兼容性匹配"""
        user_pref = {
            "relationship_types": [{"key": "serious_relationship"}],
            "current_status": "single",
            "expectation_description": "寻找稳定关系"
        }
        target_pref = {
            "relationship_types": [{"key": "casual_dating"}],
            "current_status": "in_relationship",
            "expectation_description": "随意交友"
        }

        with patch.object(service, 'get_user_preferences', side_effect=[user_pref, target_pref]):
            result = service.match_relationship_compatibility('user_001', 'user_002')

        # 应该有兼容性分数
        assert "score" in result
        assert "details" in result

    def test_generate_recommendation_high(self, service):
        """测试高分推荐"""
        recommendation = service._generate_recommendation(85, [])
        assert "高度匹配" in recommendation

    def test_generate_recommendation_medium(self, service):
        """测试中等分推荐"""
        recommendation = service._generate_recommendation(60, [])
        assert "compatible" in recommendation or "基本" in recommendation

    def test_generate_recommendation_low(self, service):
        """测试低分推荐"""
        recommendation = service._generate_recommendation(25, [])
        assert "差异" in recommendation or "明确" in recommendation

    def test_get_users_by_relationship_type(self, service, mock_db):
        """测试按关系类型获取用户"""
        mock_prefs = [MagicMock(user_id='user_001'), MagicMock(user_id='user_002')]
        mock_db.query.return_value.filter.return_value.limit.return_value.all.return_value = mock_prefs

        users = service.get_users_by_relationship_type('serious_relationship')

        assert len(users) == 2

    def test_get_compatibility_stats_no_prefs(self, service, mock_db):
        """测试无偏好时的兼容性统计"""
        with patch.object(service, 'get_user_preferences', return_value=None):
            result = service.get_compatibility_stats('user_001')

        assert result["potential_match_rate"] == 0

    def test_get_compatibility_stats_with_prefs(self, service, mock_db):
        """测试有偏好时的兼容性统计"""
        user_pref = {
            "relationship_types": [{"key": "serious_relationship"}]
        }

        mock_all_prefs = [MagicMock(relationship_types='["serious_relationship"]')]
        mock_db.query.return_value.all.return_value = mock_all_prefs

        with patch.object(service, 'get_user_preferences', return_value=user_pref):
            result = service.get_compatibility_stats('user_001')

        assert "potential_match_rate" in result


class TestRelationshipTypesDefinitions:
    """关系类型定义测试"""

    def test_relationship_types_structure(self):
        """测试关系类型结构"""
        from services.relationship_preference_service import RELATIONSHIP_TYPES

        for key, info in RELATIONSHIP_TYPES.items():
            assert "name" in info
            assert "description" in info
            assert "category" in info

    def test_relationship_statuses_structure(self):
        """测试关系状态结构"""
        from services.relationship_preference_service import RELATIONSHIP_STATUSES

        for key, info in RELATIONSHIP_STATUSES.items():
            assert "name" in info
            assert "description" in info

    def test_relationship_type_categories(self):
        """测试关系类型分类"""
        from services.relationship_preference_service import RELATIONSHIP_TYPES

        categories = set(info["category"] for info in RELATIONSHIP_TYPES.values())
        assert "romantic" in categories
        assert "friendship" in categories
        assert "social" in categories
        assert "exploring" in categories