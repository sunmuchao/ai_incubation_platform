"""
P10 约会建议服务单元测试
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import json

from services.date_suggestion_service import (
    DateSuggestionService,
    DATE_TYPES,
)


class TestDateSuggestionService:
    """约会建议服务测试类"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return DateSuggestionService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return MagicMock()

    def test_generate_date_suggestion_success(self, service, mock_db_session):
        """测试成功生成约会建议"""
        # Arrange
        user_id = "user_001"
        target_user_id = "user_002"
        date_type = "coffee"

        # Mock user
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.location = "北京市"
        mock_user.interests = json.dumps(["咖啡", "阅读", "旅行"])

        # Mock target user
        mock_target_user = MagicMock()
        mock_target_user.id = target_user_id
        mock_target_user.interests = json.dumps(["咖啡", "音乐", "电影"])

        # Mock match record
        mock_match = MagicMock()
        mock_match.relationship_stage = "chatting"

        # Mock venue query
        mock_venue = MagicMock()
        mock_venue.venue_name = "星巴克"
        mock_venue.venue_type = "coffee"
        mock_venue.address = "北京市朝阳区"
        mock_venue.latitude = 39.9042
        mock_venue.longitude = 116.4074
        mock_venue.rating = 4.5
        mock_venue.price_level = 2

        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            mock_user, mock_target_user, mock_match
        ]
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_venue]
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        # Act
        suggestion_id = service.generate_date_suggestion(
            user_id=user_id,
            target_user_id=target_user_id,
            date_type=date_type,
            db_session=mock_db_session
        )

        # Assert
        assert suggestion_id is not None
        mock_db_session.add.assert_called_once()

    def test_generate_date_suggestion_auto_type(self, service, mock_db_session):
        """测试自动生成约会类型"""
        # Arrange
        user_id = "user_001"
        target_user_id = "user_002"

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.location = "上海市"
        mock_user.interests = json.dumps(["咖啡", "聊天"])

        mock_target_user = MagicMock()
        mock_target_user.id = target_user_id
        mock_target_user.interests = json.dumps(["咖啡", "聊天"])

        mock_match = MagicMock()
        mock_match.relationship_stage = "exchanged_contact"

        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            mock_user, mock_target_user, mock_match
        ]
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        # Act
        suggestion_id = service.generate_date_suggestion(
            user_id=user_id,
            target_user_id=target_user_id,
            db_session=mock_db_session
        )

        # Assert
        assert suggestion_id is not None

    def test_generate_date_suggestion_no_target(self, service, mock_db_session):
        """测试生成约会建议（无目标用户）"""
        # Arrange
        user_id = "user_001"
        date_type = "coffee"

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.location = "深圳市"
        mock_user.interests = json.dumps(["咖啡"])

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_user
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        # Act
        suggestion_id = service.generate_date_suggestion(
            user_id=user_id,
            date_type=date_type,
            db_session=mock_db_session
        )

        # Assert
        assert suggestion_id is not None

    def test_generate_date_suggestion_user_not_found(self, service, mock_db_session):
        """测试生成约会建议（用户不存在）"""
        # Arrange
        user_id = "user_not_exist"

        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="User not found"):
            service.generate_date_suggestion(
                user_id=user_id,
                db_session=mock_db_session
            )

    def test_suggest_date_type_early_stage(self, service):
        """测试建议约会类型（早期阶段）"""
        # Arrange
        relationship_stage = "chatting"

        mock_user = MagicMock()
        mock_user.interests = json.dumps(["咖啡", "聊天"])

        mock_target = MagicMock()
        mock_target.interests = json.dumps(["咖啡", "音乐"])

        # Act
        date_type = service._suggest_date_type(relationship_stage, mock_user, mock_target)

        # Assert
        assert date_type == "coffee"

    def test_suggest_date_type_later_stage(self, service):
        """测试建议约会类型（后期阶段）"""
        # Arrange
        relationship_stage = "first_date"

        mock_user = MagicMock()
        mock_user.interests = json.dumps(["美食", "电影"])

        mock_target = MagicMock()
        mock_target.interests = json.dumps(["美食", "旅行"])

        # Act
        date_type = service._suggest_date_type(relationship_stage, mock_user, mock_target)

        # Assert
        assert date_type == "meal"

    def test_find_suitable_venue_found(self, service, mock_db_session):
        """测试查找合适的约会地点（找到）"""
        # Arrange
        user = MagicMock()
        user.location = "北京市"

        target_user = MagicMock()

        date_type = "coffee"

        mock_venue = MagicMock()
        mock_venue.venue_name = "星巴克"
        mock_venue.venue_type = "coffee"
        mock_venue.address = "北京市朝阳区"
        mock_venue.latitude = 39.9042
        mock_venue.longitude = 116.4074
        mock_venue.rating = 4.5
        mock_venue.price_level = 2

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_venue]

        # Act
        venue = service._find_suitable_venue(
            mock_db_session, user, target_user, date_type, None
        )

        # Assert
        assert venue is not None
        assert venue["name"] == "星巴克"
        assert venue["rating"] == 4.5

    def test_find_suitable_venue_not_found(self, service, mock_db_session):
        """测试查找合适的约会地点（未找到）"""
        # Arrange
        user = MagicMock()
        user.location = "北京市"
        target_user = MagicMock()
        date_type = "coffee"

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        # Act
        venue = service._find_suitable_venue(
            mock_db_session, user, target_user, date_type, None
        )

        # Assert
        assert venue is None

    def test_generate_generic_venue(self, service):
        """测试生成通用约会地点"""
        # Arrange
        mock_user = MagicMock()
        mock_user.location = "城市中心"

        # Test different date types
        for date_type in DATE_TYPES.keys():
            # Act
            venue = service._generate_generic_venue(mock_user, date_type)

            # Assert
            assert venue is not None
            assert "name" in venue
            assert "address" in venue

    def test_calculate_match_score(self, service):
        """测试计算匹配分数"""
        # Arrange
        mock_user1 = MagicMock()
        mock_user1.interests = json.dumps(["咖啡", "阅读", "旅行"])

        mock_user2 = MagicMock()
        mock_user2.interests = json.dumps(["咖啡", "音乐", "旅行"])

        mock_venue = {"rating": 4.5}
        date_type = "coffee"

        # Act
        score = service._calculate_match_score(mock_user1, mock_user2, mock_venue, date_type)

        # Assert
        assert score > 0.5  # 有共同兴趣，分数应高于基础分
        assert score <= 1.0

    def test_calculate_match_score_no_common_interests(self, service):
        """测试计算匹配分数（无共同兴趣）"""
        # Arrange
        mock_user1 = MagicMock()
        mock_user1.interests = json.dumps(["咖啡", "阅读"])

        mock_user2 = MagicMock()
        mock_user2.interests = json.dumps(["运动", "游戏"])

        mock_venue = {"rating": 3.0}
        date_type = "coffee"

        # Act
        score = service._calculate_match_score(mock_user1, mock_user2, mock_venue, date_type)

        # Assert
        assert score >= 0.5  # 至少为基础分

    def test_generate_recommendation_reason(self, service):
        """测试生成推荐理由"""
        # Arrange
        mock_user = MagicMock()
        mock_user.interests = json.dumps(["咖啡", "阅读"])

        mock_target = MagicMock()
        mock_target.interests = json.dumps(["咖啡", "音乐"])

        mock_venue = {"rating": 4.5}
        date_type = "coffee"
        relationship_stage = "chatting"

        # Act
        reason = service._generate_recommendation_reason(
            mock_user, mock_target, mock_venue, date_type, relationship_stage
        )

        # Assert
        assert len(reason) > 0
        assert "轻松" in reason or "了解" in reason  # chatting 阶段的理由

    def test_generate_recommendation_reason_no_target(self, service):
        """测试生成推荐理由（无目标用户）"""
        # Arrange
        mock_user = MagicMock()
        mock_user.interests = json.dumps(["咖啡"])

        mock_target = None
        mock_venue = {"rating": 4.0}
        date_type = "coffee"
        relationship_stage = "chatting"

        # Act
        reason = service._generate_recommendation_reason(
            mock_user, mock_target, mock_venue, date_type, relationship_stage
        )

        # Assert
        assert len(reason) > 0

    def test_suggest_best_time(self, service):
        """测试建议最佳时间"""
        # Test different date types
        time = service._suggest_best_time("coffee")
        assert "下午" in time

        time = service._suggest_best_time("meal")
        assert "晚上" in time

        time = service._suggest_best_time("movie")
        assert len(time) > 0

        time = service._suggest_best_time("outdoor")
        assert len(time) > 0

    def test_get_common_interests(self, service):
        """测试获取共同兴趣"""
        # Arrange
        mock_user1 = MagicMock()
        mock_user1.interests = json.dumps(["咖啡", "阅读", "旅行", "音乐"])

        mock_user2 = MagicMock()
        mock_user2.interests = json.dumps(["咖啡", "旅行", "电影", "游戏"])

        # Act
        common = service._get_common_interests(mock_user1, mock_user2)

        # Assert
        assert len(common) == 2
        assert "咖啡" in common
        assert "旅行" in common

    def test_get_common_interests_no_overlap(self, service):
        """测试获取共同兴趣（无重叠）"""
        # Arrange
        mock_user1 = MagicMock()
        mock_user1.interests = json.dumps(["咖啡", "阅读"])

        mock_user2 = MagicMock()
        mock_user2.interests = json.dumps(["运动", "游戏"])

        # Act
        common = service._get_common_interests(mock_user1, mock_user2)

        # Assert
        assert len(common) == 0

    def test_get_common_interests_empty(self, service):
        """测试获取共同兴趣（空兴趣列表）"""
        # Arrange
        mock_user1 = MagicMock()
        mock_user1.interests = json.dumps([])

        mock_user2 = MagicMock()
        mock_user2.interests = json.dumps(["咖啡", "阅读"])

        # Act
        common = service._get_common_interests(mock_user1, mock_user2)

        # Assert
        assert len(common) == 0

    def test_get_user_date_suggestions(self, service, mock_db_session):
        """测试获取用户的约会建议列表"""
        # Arrange
        user_id = "user_001"
        status = "pending"
        limit = 10

        mock_suggestion = MagicMock()
        mock_suggestion.id = "suggestion_001"
        mock_suggestion.user_id = user_id
        mock_suggestion.target_user_id = "user_002"
        mock_suggestion.date_type = "coffee"
        mock_suggestion.venue_name = "星巴克"
        mock_suggestion.venue_type = "咖啡"
        mock_suggestion.address = "北京市朝阳区"
        mock_suggestion.recommendation_reason = "轻松的约会"
        mock_suggestion.estimated_cost = 100
        mock_suggestion.estimated_duration = 60
        mock_suggestion.best_time_suggestion = "下午 2-4 点"
        mock_suggestion.match_score = 0.75
        mock_suggestion.status = status
        mock_suggestion.suggested_at = datetime(2024, 1, 15)
        mock_suggestion.responded_at = None
        mock_suggestion.user_rating = None
        mock_suggestion.user_feedback = None

        # Mock the query chain properly
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = [mock_suggestion]
        mock_db_session.query.return_value = mock_query

        # Act
        suggestions = service.get_user_date_suggestions(
            user_id, status, limit, mock_db_session
        )

        # Assert
        assert len(suggestions) == 1
        assert suggestions[0]["id"] == "suggestion_001"
        assert suggestions[0]["date_type_label"] == "咖啡约会"

    def test_respond_to_date_suggestion_accept(self, service, mock_db_session):
        """测试响应约会建议（接受）"""
        # Arrange
        suggestion_id = "suggestion_001"
        action = "accept"

        mock_suggestion = MagicMock()
        mock_suggestion.id = suggestion_id
        mock_suggestion.status = "pending"

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_suggestion
        mock_db_session.commit.return_value = None

        # Act
        result = service.respond_to_date_suggestion(
            suggestion_id, action, None, None, mock_db_session
        )

        # Assert
        assert result == True
        assert mock_suggestion.status == "accepted"

    def test_respond_to_date_suggestion_reject(self, service, mock_db_session):
        """测试响应约会建议（拒绝）"""
        # Arrange
        suggestion_id = "suggestion_001"
        action = "reject"
        feedback = "不太合适"

        mock_suggestion = MagicMock()
        mock_suggestion.id = suggestion_id
        mock_suggestion.status = "pending"

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_suggestion
        mock_db_session.commit.return_value = None

        # Act
        result = service.respond_to_date_suggestion(
            suggestion_id, action, feedback, None, mock_db_session
        )

        # Assert
        assert result == True
        assert mock_suggestion.status == "rejected"
        assert mock_suggestion.user_feedback == feedback

    def test_respond_to_date_suggestion_not_found(self, service, mock_db_session):
        """测试响应不存在的约会建议"""
        # Arrange
        suggestion_id = "suggestion_not_exist"
        action = "accept"

        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act
        result = service.respond_to_date_suggestion(
            suggestion_id, action, None, None, mock_db_session
        )

        # Assert
        assert result == False

    def test_get_date_venues(self, service, mock_db_session):
        """测试获取约会地点列表"""
        # Arrange
        city = "北京市"
        venue_type = "coffee"
        limit = 20

        mock_venue = MagicMock()
        mock_venue.id = "venue_001"
        mock_venue.venue_name = "星巴克"
        mock_venue.venue_type = "coffee"
        mock_venue.category = "咖啡"
        mock_venue.address = "北京市朝阳区"
        mock_venue.city = city
        mock_venue.district = "朝阳区"
        mock_venue.latitude = 39.9042
        mock_venue.longitude = 116.4074
        mock_venue.rating = 4.5
        mock_venue.review_count = 100
        mock_venue.price_level = 2
        mock_venue.tags = json.dumps(["咖啡", "休闲"])
        mock_venue.suitable_for = json.dumps(["first_date", "casual"])
        mock_venue.is_popular = True

        # Mock the query chain properly with patch
        with patch('services.date_suggestion_service.SessionLocal', return_value=mock_db_session):
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value.limit.return_value.all.return_value = [mock_venue]
            mock_db_session.query.return_value = mock_query

            # Act
            venues = service.get_date_venues(city, venue_type, None, limit)

        # Assert
        assert len(venues) == 1
        assert venues[0]["id"] == "venue_001"
        assert venues[0]["city"] == city

    def test_add_date_venue(self, service, mock_db_session):
        """测试添加约会地点"""
        # Arrange
        venue_name = "新咖啡馆"
        venue_type = "coffee"
        address = "北京市朝阳区某某路"
        city = "北京市"
        latitude = 39.9042
        longitude = 116.4074

        # Mock SessionLocal
        with patch('services.date_suggestion_service.SessionLocal', return_value=mock_db_session):
            mock_db_session.add.return_value = None
            mock_db_session.commit.return_value = None
            mock_db_session.refresh.return_value = None

            # Act
            result = service.add_date_venue(
                venue_name=venue_name,
                venue_type=venue_type,
                address=address,
                city=city,
                latitude=latitude,
                longitude=longitude
            )

        # Assert
        assert result is not None
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        # Act
        venue_id = service.add_date_venue(
            venue_name, venue_type, address, city,
            latitude, longitude
        )

        # Assert
        assert venue_id is not None
        mock_db_session.add.assert_called_once()

    def test_date_types_complete(self):
        """测试约会类型定义完整性"""
        # Assert
        assert "coffee" in DATE_TYPES
        assert "meal" in DATE_TYPES
        assert "movie" in DATE_TYPES
        assert "outdoor" in DATE_TYPES
        assert "culture" in DATE_TYPES
        assert "sports" in DATE_TYPES
        assert "entertainment" in DATE_TYPES
        assert "creative" in DATE_TYPES

    def test_date_type_structure(self):
        """测试约会类型结构"""
        # Assert
        for date_type, info in DATE_TYPES.items():
            assert "label" in info
            assert "duration" in info
            assert "price_range" in info
            assert "suitable_stages" in info
