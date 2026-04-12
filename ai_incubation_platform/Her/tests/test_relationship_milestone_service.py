"""
P10 关系里程碑服务单元测试
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import json

from services.relationship_milestone_service import (
    RelationshipMilestoneService,
    RELATIONSHIP_STAGES_P10,
    MILESTONE_TYPES_P10,
    CELEBRATION_SUGGESTIONS,
)
from models.milestone_models import RelationshipMilestoneDB


class TestRelationshipMilestoneService:
    """关系里程碑服务测试类"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return RelationshipMilestoneService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        session = MagicMock()

        # 设置 query 链式调用
        mock_query = MagicMock()
        session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.filter_by.return_value = mock_query

        # 设置基础操作
        session.add.return_value = None
        session.commit.return_value = None
        session.refresh.return_value = None
        session.rollback.return_value = None
        return session

    def test_record_milestone_success(self, service, mock_db_session):
        """测试成功记录里程碑"""
        # Arrange
        user_id_1 = "user_001"
        user_id_2 = "user_002"
        milestone_type = "first_date_completed"
        title = "第一次约会"
        description = "我们一起去了星巴克喝咖啡"

        # Act
        with patch.object(service, '_update_stage_history_if_needed'):
            milestone_id = service.record_milestone(
                user_id_1=user_id_1,
                user_id_2=user_id_2,
                milestone_type=milestone_type,
                title=title,
                description=description,
                db_session_param=mock_db_session
            )

        # Assert
        assert milestone_id is not None
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called()

    def test_record_milestone_with_celebration(self, service, mock_db_session):
        """测试记录里程碑并建议庆祝"""
        # Arrange
        user_id_1 = "user_001"
        user_id_2 = "user_002"
        milestone_type = "anniversary_1month"  # 属于 anniversary 类别
        title = "一月纪念日"
        description = "在一起一个月了"
        celebration_suggested = True

        # Act
        with patch.object(service, '_update_stage_history_if_needed'):
            milestone_id = service.record_milestone(
                user_id_1=user_id_1,
                user_id_2=user_id_2,
                milestone_type=milestone_type,
                title=title,
                description=description,
                celebration_suggested=celebration_suggested,
                db_session_param=mock_db_session
            )

        # Assert
        assert milestone_id is not None
        # 验证庆祝建议是否正确生成
        called_args = mock_db_session.add.call_args[0][0]
        assert called_args.celebration_suggested == True
        assert called_args.celebration_type == "gift"  # anniversary 类别对应 gift

    def test_record_milestone_with_ai_analysis(self, service, mock_db_session):
        """测试记录里程碑并包含 AI 分析"""
        # Arrange
        user_id_1 = "user_001"
        user_id_2 = "user_002"
        milestone_type = "relationship_exclusive"
        title = "确定关系"
        description = "我们正式在一起了"
        ai_analysis = {
            "significance_score": 0.9,
            "relationship_stage": "exclusive",
            "suggestions": ["多沟通彼此的感受", "规划未来"]
        }

        # Act
        with patch.object(service, '_update_stage_history_if_needed'):
            milestone_id = service.record_milestone(
                user_id_1=user_id_1,
                user_id_2=user_id_2,
                milestone_type=milestone_type,
                title=title,
                description=description,
                ai_analysis=ai_analysis,
                db_session_param=mock_db_session
            )

        # Assert
        assert milestone_id is not None
        called_args = mock_db_session.add.call_args[0][0]
        assert json.loads(called_args.ai_analysis) == ai_analysis

    def test_get_milestone_timeline(self, service, mock_db_session):
        """测试获取里程碑时间线"""
        # Arrange
        user_id_1 = "user_001"
        user_id_2 = "user_002"

        mock_milestone = MagicMock()
        mock_milestone.id = "milestone_001"
        mock_milestone.user_id_1 = user_id_1
        mock_milestone.user_id_2 = user_id_2
        mock_milestone.milestone_type = "first_date_completed"
        mock_milestone.title = "第一次约会"
        mock_milestone.description = "我们一起喝咖啡"
        mock_milestone.milestone_date = datetime(2024, 1, 15)
        mock_milestone.celebration_suggested = True
        mock_milestone.celebration_type = "activity"
        mock_milestone.celebration_description = "安排一次特别的约会"
        mock_milestone.ai_analysis = ""
        mock_milestone.user_rating = 5
        mock_milestone.user_note = "很开心的一天"
        mock_milestone.is_private = False
        mock_milestone.created_at = datetime(2024, 1, 15, 10, 0)

        # Mock the query chain properly
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.all.return_value = [mock_milestone]
        mock_db_session.query.return_value = mock_query

        # Mock MatchHistoryDB query (return None for unknown stage)
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Mock _get_stage_history to return empty list
        with patch.object(service, '_get_stage_history', return_value=[]):
            # Act
            timeline = service.get_milestone_timeline(user_id_1, user_id_2, db_session_param=mock_db_session)

        # Assert
        assert timeline is not None
        assert timeline["user_ids"] == [user_id_1, user_id_2]
        assert len(timeline["milestones"]) == 1
        assert timeline["milestones"][0]["id"] == "milestone_001"
        assert timeline["milestones"][0]["type"] == "first_date_completed"
        assert timeline["milestones"][0]["label"] == "完成第一次约会"

    def test_get_milestone_timeline_empty(self, service, mock_db_session):
        """测试获取空的时间线"""
        # Arrange
        user_id_1 = "user_001"
        user_id_2 = "user_002"

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act
        timeline = service.get_milestone_timeline(user_id_1, user_id_2, db_session_param=mock_db_session)

        # Assert
        assert timeline is not None
        assert len(timeline["milestones"]) == 0
        assert timeline["total_milestones"] == 0

    def test_generate_relationship_insight(self, service, mock_db_session):
        """测试生成关系洞察"""
        # Arrange
        user_id_1 = "user_001"
        user_id_2 = "user_002"
        insight_type = "communication_pattern"
        title = "沟通模式分析"
        content = "你们的沟通频率很高，这是一个好的开始"
        action_suggestion = "继续保持开放的沟通"
        priority = "normal"

        # Act
        insight_id = service.generate_relationship_insight(
            user_id_1=user_id_1,
            user_id_2=user_id_2,
            insight_type=insight_type,
            title=title,
            content=content,
            action_suggestion=action_suggestion,
            priority=priority,
            db_session_param=mock_db_session
        )

        # Assert
        assert insight_id is not None
        mock_db_session.add.assert_called_once()

    def test_get_relationship_insights(self, service, mock_db_session):
        """测试获取关系洞察"""
        # Arrange
        user_id = "user_001"

        mock_insight = MagicMock()
        mock_insight.id = "insight_001"
        mock_insight.user_id_1 = user_id
        mock_insight.user_id_2 = "user_002"
        mock_insight.insight_type = "communication_pattern"
        mock_insight.title = "沟通模式分析"
        mock_insight.content = "你们的沟通频率很高"
        mock_insight.action_suggestion = "继续保持开放的沟通"
        mock_insight.priority = "normal"
        mock_insight.confidence_score = 0.85
        mock_insight.is_read_user1 = False
        mock_insight.is_read_user2 = False
        mock_insight.is_actioned = False
        mock_insight.created_at = datetime(2024, 1, 15)
        mock_insight.expires_at = None

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = [mock_insight]
        mock_db_session.query.return_value = mock_query

        # Act
        insights = service.get_relationship_insights(user_id, db_session_param=mock_db_session)

        # Assert
        assert len(insights) == 1
        assert insights[0]["id"] == "insight_001"
        assert insights[0]["is_read"] == False

    def test_mark_insight_read(self, service, mock_db_session):
        """测试标记洞察为已读"""
        # Arrange
        insight_id = "insight_001"
        user_id = "user_001"

        mock_insight = MagicMock()
        mock_insight.id = insight_id
        mock_insight.user_id_1 = user_id
        mock_insight.user_id_2 = "user_002"
        mock_insight.is_read_user1 = False
        mock_insight.is_read_user2 = False

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_insight
        mock_db_session.commit.return_value = None

        # Act
        result = service.mark_insight_read(insight_id, user_id, db_session_param=mock_db_session)

        # Assert
        assert result == True
        mock_db_session.commit.assert_called_once()

    def test_mark_insight_read_not_found(self, service, mock_db_session):
        """测试标记不存在的洞察"""
        # Arrange
        insight_id = "insight_not_exist"
        user_id = "user_001"

        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act
        result = service.mark_insight_read(insight_id, user_id)

        # Assert
        assert result == False

    def test_get_milestone_statistics(self, service, mock_db_session):
        """测试获取里程碑统计"""
        # Arrange
        user_id_1 = "user_001"
        user_id_2 = "user_002"

        mock_milestone1 = MagicMock()
        mock_milestone1.milestone_type = "first_date_completed"
        mock_milestone1.user_rating = 5
        mock_milestone1.milestone_date = datetime(2024, 1, 15)

        mock_milestone2 = MagicMock()
        mock_milestone2.milestone_type = "relationship_exclusive"
        mock_milestone2.user_rating = 5
        mock_milestone2.milestone_date = datetime(2024, 2, 14)

        mock_db_session.query.return_value.filter.return_value.all.return_value = [
            mock_milestone1, mock_milestone2
        ]

        # Act
        stats = service.get_milestone_statistics(user_id_1, user_id_2, db_session_param=mock_db_session)

        # Assert
        assert stats["total_milestones"] == 2
        assert "category_stats" in stats
        assert "relationship_score" in stats

    def test_get_milestone_by_id(self, service, mock_db_session):
        """测试根据 ID 获取里程碑"""
        # Arrange
        milestone_id = "milestone_001"

        mock_milestone = MagicMock()
        mock_milestone.id = milestone_id
        mock_milestone.user_id_1 = "user_001"
        mock_milestone.user_id_2 = "user_002"
        mock_milestone.milestone_type = "first_date_completed"
        mock_milestone.title = "第一次约会"
        mock_milestone.description = "我们一起喝咖啡"
        mock_milestone.milestone_date = datetime(2024, 1, 15)
        mock_milestone.celebration_suggested = True
        mock_milestone.celebration_type = "activity"
        mock_milestone.celebration_description = "安排一次特别的约会"
        mock_milestone.ai_analysis = ""
        mock_milestone.user_rating = 5
        mock_milestone.user_note = "很开心"
        mock_milestone.is_private = False
        mock_milestone.created_at = datetime(2024, 1, 15)
        mock_milestone.updated_at = datetime(2024, 1, 15)

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_milestone

        # Act
        milestone = service.get_milestone_by_id(milestone_id, db_session_param=mock_db_session)

        # Assert
        assert milestone is not None
        assert milestone["id"] == milestone_id
        assert milestone["milestone_type"] == "first_date_completed"
        assert milestone["milestone_type_label"] == "完成第一次约会"

    def test_get_milestone_by_id_not_found(self, service, mock_db_session):
        """测试获取不存在的里程碑"""
        # Arrange
        milestone_id = "milestone_not_exist"

        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act
        milestone = service.get_milestone_by_id(milestone_id)

        # Assert
        assert milestone is None

    def test_update_milestone(self, service, mock_db_session):
        """测试更新里程碑"""
        # Arrange
        milestone_id = "milestone_001"
        new_title = "更新后的标题"
        new_rating = 4
        new_note = "更新后的备注"

        mock_milestone = MagicMock()
        mock_milestone.id = milestone_id
        mock_milestone.title = "原标题"
        mock_milestone.user_rating = 5
        mock_milestone.user_note = "原备注"

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_milestone
        mock_db_session.commit.return_value = None

        # Act
        result = service.update_milestone(
            milestone_id,
            title=new_title,
            user_rating=new_rating,
            user_note=new_note,
            db_session_param=mock_db_session
        )

        # Assert
        assert result == True
        assert mock_milestone.title == new_title
        assert mock_milestone.user_rating == new_rating
        assert mock_milestone.user_note == new_note
        mock_db_session.commit.assert_called_once()

    def test_update_milestone_not_found(self, service, mock_db_session):
        """测试更新不存在的里程碑"""
        # Arrange
        milestone_id = "milestone_not_exist"

        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act
        result = service.update_milestone(milestone_id, title="新标题", db_session_param=mock_db_session)

        # Assert
        assert result == False

    def test_celebrate_milestone(self, service, mock_db_session):
        """测试庆祝里程碑"""
        # Arrange
        milestone_id = "milestone_001"
        celebration_type = "gift"

        mock_milestone = MagicMock()
        mock_milestone.id = milestone_id
        mock_milestone.milestone_type = "anniversary_1month"
        mock_milestone.celebration_suggested = False
        mock_milestone.celebration_type = None
        mock_milestone.celebration_description = None

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_milestone
        mock_db_session.commit.return_value = None

        # Act
        result = service.celebrate_milestone(milestone_id, celebration_type, db_session_param=mock_db_session)

        # Assert
        assert result == True
        assert mock_milestone.celebration_suggested == True
        assert mock_milestone.celebration_type == celebration_type
        mock_db_session.commit.assert_called_once()

    def test_celebrate_milestone_not_found(self, service, mock_db_session):
        """测试庆祝不存在的里程碑"""
        # Arrange
        milestone_id = "milestone_not_exist"

        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act
        result = service.celebrate_milestone(milestone_id, "gift", db_session_param=mock_db_session)

        # Assert
        assert result == False

    def test_relationship_stages_complete(self):
        """测试关系阶段定义完整性"""
        # Assert
        assert "unknown" in RELATIONSHIP_STAGES_P10
        assert "matched" in RELATIONSHIP_STAGES_P10
        assert "chatting" in RELATIONSHIP_STAGES_P10
        assert "first_date" in RELATIONSHIP_STAGES_P10
        assert "exclusive" in RELATIONSHIP_STAGES_P10
        assert "in_relationship" in RELATIONSHIP_STAGES_P10
        assert "engaged" in RELATIONSHIP_STAGES_P10
        assert "married" in RELATIONSHIP_STAGES_P10

    def test_milestone_types_complete(self):
        """测试里程碑类型定义完整性"""
        # Assert
        assert "first_match" in MILESTONE_TYPES_P10
        assert "first_message" in MILESTONE_TYPES_P10
        assert "first_date_completed" in MILESTONE_TYPES_P10
        assert "relationship_exclusive" in MILESTONE_TYPES_P10
        assert "anniversary_1month" in MILESTONE_TYPES_P10

    def test_celebration_suggestions_complete(self):
        """测试庆祝建议完整性"""
        # Assert
        assert "beginning" in CELEBRATION_SUGGESTIONS
        assert "communication" in CELEBRATION_SUGGESTIONS
        assert "dating" in CELEBRATION_SUGGESTIONS
        assert "anniversary" in CELEBRATION_SUGGESTIONS
        assert "commitment" in CELEBRATION_SUGGESTIONS


class TestRelationshipStageHistory:
    """关系阶段历史测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return RelationshipMilestoneService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        session = MagicMock()

        # 设置 query 链式调用
        mock_query = MagicMock()
        session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.filter_by.return_value = mock_query

        # 设置基础操作
        session.add.return_value = None
        session.commit.return_value = None
        session.refresh.return_value = None
        session.rollback.return_value = None
        return session

    def test_update_stage_history_on_milestone(self, service, mock_db_session):
        """测试里程碑触发阶段历史更新"""
        # Arrange
        user_id_1 = "user_001"
        user_id_2 = "user_002"
        milestone_type = "first_date_completed"  # 应该触发从 chatting 到 first_date 的升级
        milestone_date = datetime(2024, 1, 15)

        # 模拟当前关系阶段为 chatting
        mock_match = MagicMock()
        mock_match.relationship_stage = "chatting"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_match
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None

        # Act
        service._update_stage_history_if_needed(
            user_id_1, user_id_2, milestone_type, milestone_date, mock_db_session
        )

        # Assert
        mock_db_session.add.assert_called()  # 应该添加阶段历史记录

    def test_no_stage_change_for_same_stage(self, service, mock_db_session):
        """测试相同阶段不记录历史"""
        # Arrange
        user_id_1 = "user_001"
        user_id_2 = "user_002"
        milestone_type = "first_like"  # 不会触发阶段变化
        milestone_date = datetime(2024, 1, 15)

        # Act
        service._update_stage_history_if_needed(
            user_id_1, user_id_2, milestone_type, milestone_date, mock_db_session
        )

        # Assert
        mock_db_session.add.assert_not_called()

    def test_generate_stage_ai_comment(self, service):
        """测试生成阶段变更 AI 评论"""
        # Test various stage transitions
        comment = service._generate_stage_ai_comment("matched", "chatting")
        assert "开始" in comment or "交流" in comment

        comment = service._generate_stage_ai_comment("chatting", "exchanged_contact")
        assert "进一步" in comment or "联系方式" in comment

        comment = service._generate_stage_ai_comment("exclusive", "in_relationship")
        assert "关系" in comment or "经营" in comment

    def test_get_next_stage_suggestions(self, service):
        """测试获取下一阶段建议"""
        # Test for matched stage
        suggestions = service._get_next_stage_suggestions("matched")
        assert len(suggestions) > 0
        assert any("发起对话" in s.get("action", "") for s in suggestions)

        # Test for chatting stage
        suggestions = service._get_next_stage_suggestions("chatting")
        assert len(suggestions) > 0
        assert any("深入交流" in s.get("action", "") for s in suggestions)

        # Test for unknown stage (default)
        suggestions = service._get_next_stage_suggestions("unknown")
        assert len(suggestions) > 0


class TestRelationshipScoreCalculation:
    """关系得分计算测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return RelationshipMilestoneService()

    def test_calculate_relationship_score_empty(self, service):
        """测试空里程碑列表的得分"""
        # Arrange
        milestones = []

        # Act
        score = service._calculate_relationship_score(milestones)

        # Assert
        assert score == 0.0

    def test_calculate_relationship_score_with_milestones(self, service):
        """测试有里程碑时的得分"""
        # Arrange
        mock_milestone1 = MagicMock()
        mock_milestone1.milestone_type = "first_match"
        mock_milestone1.user_rating = 5

        mock_milestone2 = MagicMock()
        mock_milestone2.milestone_type = "relationship_exclusive"
        mock_milestone2.user_rating = 5

        milestones = [mock_milestone1, mock_milestone2]

        # Act
        score = service._calculate_relationship_score(milestones)

        # Assert
        assert score > 0
        assert score <= 100  # 分数应该归一化到 0-100

    def test_calculate_relationship_score_weighted(self, service):
        """测试不同类别里程碑的权重"""
        # Arrange
        # commitment 类别的里程碑权重更高
        mock_marriage = MagicMock()
        mock_marriage.milestone_type = "marriage"
        mock_marriage.user_rating = None

        milestones = [mock_marriage]

        # Act
        score = service._calculate_relationship_score(milestones)

        # Assert
        # marriage 属于 commitment 类别，权重应该是 3.0
        # 预期分数 = 3.0 * 10 = 30
        assert score == 30.0
