"""
Relationship Advanced Service 单元测试

测试覆盖：
- RelationshipStateService: 关系状态管理服务
- DatingAdviceService: 约会建议生成服务
- LoveGuidanceService: 恋爱指导服务
- ChatSuggestionService: 聊天建议服务
- GiftRecommendationService: 礼物推荐服务
- RelationshipHealthService: 关系健康度分析服务
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, call
import json

from services.relationship_advanced_service import (
    RelationshipStateService,
    DatingAdviceService,
    LoveGuidanceService,
    ChatSuggestionService,
    GiftRecommendationService,
    RelationshipHealthService,
    RELATIONSHIP_STATES,
    TRANSITION_TYPES,
)


class TestRelationshipStateService:
    """关系状态管理服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return RelationshipStateService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return MagicMock()

    # ============= get_relationship_state 测试 =============

    @patch('services.relationship_advanced_service.db_session_readonly')
    def test_get_relationship_state_found(self, mock_db_session_readonly, service):
        """测试获取关系状态（存在）"""
        user_id_1 = "user_001"
        user_id_2 = "user_002"

        mock_state = MagicMock()
        mock_state.id = "state_001"
        mock_state.state = "dating"
        mock_state.state_label = "约会中"
        mock_state.state_description = "定期约会阶段"
        mock_state.confirmed_by_user1 = True
        mock_state.confirmed_by_user2 = False
        mock_state.state_changed_at = datetime(2024, 1, 15)
        mock_state.ai_confidence = 0.8
        mock_state.created_at = datetime(2024, 1, 10)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_state
        mock_db_session_readonly.return_value.__enter__.return_value = mock_db

        result = service.get_relationship_state(user_id_1, user_id_2)

        assert result is not None
        assert result["id"] == "state_001"
        assert result["state"] == "dating"
        assert result["confirmed_by_user1"] == True
        assert result["confirmed_by_user2"] == False

    @patch('services.relationship_advanced_service.db_session_readonly')
    def test_get_relationship_state_not_found(self, mock_db_session_readonly, service):
        """测试获取关系状态（不存在）"""
        user_id_1 = "user_001"
        user_id_2 = "user_002"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db_session_readonly.return_value.__enter__.return_value = mock_db

        result = service.get_relationship_state(user_id_1, user_id_2)

        assert result is None

    @patch('services.relationship_advanced_service.db_session_readonly')
    def test_get_relationship_state_reverse_order(self, mock_db_session_readonly, service):
        """测试获取关系状态（用户ID顺序相反）"""
        user_id_1 = "user_002"
        user_id_2 = "user_001"

        mock_state = MagicMock()
        mock_state.id = "state_001"
        mock_state.state = "chatting"
        mock_state.state_label = None
        mock_state.state_description = None
        mock_state.confirmed_by_user1 = False
        mock_state.confirmed_by_user2 = False
        mock_state.state_changed_at = None
        mock_state.ai_confidence = 0.5
        mock_state.created_at = datetime(2024, 1, 10)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_state
        mock_db_session_readonly.return_value.__enter__.return_value = mock_db

        result = service.get_relationship_state(user_id_1, user_id_2)

        assert result is not None
        # 当 state_label 为 None 时，应从 RELATIONSHIP_STATES 获取
        assert result["state_label"] == RELATIONSHIP_STATES.get("chatting", {}).get("label", "chatting")

    # ============= set_relationship_state 测试 =============

    @patch('services.relationship_advanced_service.db_session')
    def test_set_relationship_state_new_state(self, mock_db_session_ctx, service):
        """测试设置新的关系状态（创建新记录）"""
        user_id_1 = "user_001"
        user_id_2 = "user_002"
        new_state = "matched"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.set_relationship_state(user_id_1, user_id_2, new_state)

        assert result is not None  # 应返回 state.id
        mock_db.add.assert_called()

    @patch('services.relationship_advanced_service.db_session')
    def test_set_relationship_state_update_existing(self, mock_db_session_ctx, service):
        """测试更新现有关系状态"""
        user_id_1 = "user_001"
        user_id_2 = "user_002"
        new_state = "chatting"

        mock_state = MagicMock()
        mock_state.id = "state_001"
        mock_state.state = "matched"
        mock_state.confirmed_by_user1 = False
        mock_state.confirmed_by_user2 = False
        mock_state.confirmed_at = None

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_state
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.set_relationship_state(
            user_id_1, user_id_2, new_state,
            transition_type="manual",
            user_id_setting=user_id_1
        )

        assert result == "state_001"
        assert mock_state.state == new_state
        assert mock_state.confirmed_by_user1 == True
        mock_db.add.assert_called()  # 添加 transition 记录

    def test_set_relationship_state_invalid_state(self, service):
        """测试设置无效状态"""
        user_id_1 = "user_001"
        user_id_2 = "user_002"
        invalid_state = "invalid_state"

        with pytest.raises(ValueError, match="Invalid state"):
            service.set_relationship_state(user_id_1, user_id_2, invalid_state)

    @patch('services.relationship_advanced_service.db_session')
    def test_set_relationship_state_unusual_transition(self, mock_db_session_ctx, service):
        """测试异常状态转换（记录警告日志）"""
        user_id_1 = "user_001"
        user_id_2 = "user_002"
        new_state = "married"  # 从 matched 到 married 是异常转换

        mock_state = MagicMock()
        mock_state.id = "state_001"
        mock_state.state = "matched"
        mock_state.confirmed_by_user1 = False
        mock_state.confirmed_by_user2 = False
        mock_state.confirmed_at = None

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_state
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        with patch('services.relationship_advanced_service.logger') as mock_logger:
            result = service.set_relationship_state(user_id_1, user_id_2, new_state)

            mock_logger.warning.assert_called()
            assert "Unusual state transition" in mock_logger.warning.call_args[0][0]

    @patch('services.relationship_advanced_service.db_session')
    def test_set_relationship_state_both_confirm(self, mock_db_session_ctx, service):
        """测试双方都确认状态"""
        user_id_1 = "user_001"
        user_id_2 = "user_002"
        new_state = "exclusive"

        mock_state = MagicMock()
        mock_state.id = "state_001"
        mock_state.state = "dating"
        mock_state.confirmed_by_user1 = True  # user1 已确认
        mock_state.confirmed_by_user2 = False
        mock_state.confirmed_at = None

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_state
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.set_relationship_state(
            user_id_1, user_id_2, new_state,
            user_id_setting=user_id_2  # user2 确认
        )

        assert mock_state.confirmed_by_user2 == True
        assert mock_state.confirmed_at is not None  # 双方确认后设置确认时间

    # ============= get_state_history 测试 =============

    @patch('services.relationship_advanced_service.db_session_readonly')
    def test_get_state_history_with_records(self, mock_db_session_readonly, service):
        """测试获取状态历史（有记录）"""
        user_id_1 = "user_001"
        user_id_2 = "user_002"

        mock_transition1 = MagicMock()
        mock_transition1.id = "trans_001"
        mock_transition1.from_state = "matched"
        mock_transition1.to_state = "chatting"
        mock_transition1.to_state_label = "聊天中"
        mock_transition1.transition_type = "manual"
        mock_transition1.transition_reason = "开始交流"
        mock_transition1.trigger_event = None
        mock_transition1.ai_comment = "开始交流是了解彼此的第一步！"
        mock_transition1.next_stage_suggestions = json.dumps([
            {"action": "深入交流", "description": "分享更多个人信息和价值观"}
        ])
        mock_transition1.created_at = datetime(2024, 1, 12)

        mock_transition2 = MagicMock()
        mock_transition2.id = "trans_002"
        mock_transition2.from_state = "chatting"
        mock_transition2.to_state = "dating"
        mock_transition2.to_state_label = "约会中"
        mock_transition2.transition_type = "ai_detected"
        mock_transition2.transition_reason = None
        mock_transition2.trigger_event = "first_date"
        mock_transition2.ai_comment = "从暧昧到约会,关系更进一步！"
        mock_transition2.next_stage_suggestions = json.dumps([])
        mock_transition2.created_at = datetime(2024, 1, 15)

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = [
            mock_transition2, mock_transition1  # 按 created_at desc
        ]
        mock_db.query.return_value = mock_query
        mock_db_session_readonly.return_value.__enter__.return_value = mock_db

        history = service.get_state_history(user_id_1, user_id_2, limit=20)

        assert len(history) == 2
        assert history[0]["id"] == "trans_002"
        assert history[0]["from_state"] == "chatting"
        assert history[0]["to_state"] == "dating"
        assert isinstance(history[0]["next_stage_suggestions"], list)

    @patch('services.relationship_advanced_service.db_session_readonly')
    def test_get_state_history_empty(self, mock_db_session_readonly, service):
        """测试获取状态历史（无记录）"""
        user_id_1 = "user_001"
        user_id_2 = "user_002"

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = []
        mock_db.query.return_value = mock_query
        mock_db_session_readonly.return_value.__enter__.return_value = mock_db

        history = service.get_state_history(user_id_1, user_id_2)

        assert history == []

    # ============= confirm_relationship_state 测试 =============

    @patch('services.relationship_advanced_service.db_session')
    def test_confirm_relationship_state_success(self, mock_db_session_ctx, service):
        """测试确认关系状态（成功）"""
        user_id_1 = "user_001"
        user_id_2 = "user_002"
        confirming_user_id = "user_001"

        mock_state = MagicMock()
        mock_state.confirmed_by_user1 = False
        mock_state.confirmed_by_user2 = False
        mock_state.confirmed_at = None

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_state
        mock_db.commit.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.confirm_relationship_state(user_id_1, user_id_2, confirming_user_id)

        assert result == True
        assert mock_state.confirmed_by_user1 == True

    @patch('services.relationship_advanced_service.db_session')
    def test_confirm_relationship_state_state_not_found(self, mock_db_session_ctx, service):
        """测试确认关系状态（状态不存在）"""
        user_id_1 = "user_001"
        user_id_2 = "user_002"
        confirming_user_id = "user_001"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.confirm_relationship_state(user_id_1, user_id_2, confirming_user_id)

        assert result == False

    @patch('services.relationship_advanced_service.db_session')
    def test_confirm_relationship_state_invalid_user(self, mock_db_session_ctx, service):
        """测试确认关系状态（无效确认用户）"""
        user_id_1 = "user_001"
        user_id_2 = "user_002"
        confirming_user_id = "user_003"  # 不属于关系双方

        mock_state = MagicMock()

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_state
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.confirm_relationship_state(user_id_1, user_id_2, confirming_user_id)

        assert result == False

    # ============= 辅助方法测试 =============

    def test_generate_ai_comment_known_transition(self, service):
        """测试生成 AI 评论（已知转换）"""
        comment = service._generate_ai_comment("matched", "chatting")
        assert "开始交流" in comment

        comment = service._generate_ai_comment(None, "matched")
        assert "美好的相遇" in comment

    def test_generate_ai_comment_unknown_transition(self, service):
        """测试生成 AI 评论（未知转换）"""
        comment = service._generate_ai_comment("married", "separated")
        # 应返回默认评论
        assert "恭喜你们的关系进入新阶段" in comment or "separated" in comment

    def test_get_next_stage_suggestions_known_state(self, service):
        """测试获取下一阶段建议（已知状态）"""
        suggestions = service._get_next_stage_suggestions("matched")
        assert len(suggestions) > 0
        assert suggestions[0]["action"] == "发起对话"

        suggestions = service._get_next_stage_suggestions("dating")
        assert len(suggestions) > 0
        assert suggestions[0]["action"] == "定义关系"

    def test_get_next_stage_suggestions_unknown_state(self, service):
        """测试获取下一阶段建议（未知状态）"""
        suggestions = service._get_next_stage_suggestions("married")
        # 应返回默认建议
        assert len(suggestions) > 0
        assert "继续经营" in suggestions[0]["action"]

    def test_relationship_states_constants(self):
        """测试关系状态常量完整性"""
        assert "matched" in RELATIONSHIP_STATES
        assert "chatting" in RELATIONSHIP_STATES
        assert "ambiguity" in RELATIONSHIP_STATES
        assert "dating" in RELATIONSHIP_STATES
        assert "exclusive" in RELATIONSHIP_STATES
        assert "in_relationship" in RELATIONSHIP_STATES
        assert "engaged" in RELATIONSHIP_STATES
        assert "married" in RELATIONSHIP_STATES
        assert "separated" in RELATIONSHIP_STATES
        assert "broken_up" in RELATIONSHIP_STATES

        # 每个状态应有 order, label, description
        for state, info in RELATIONSHIP_STATES.items():
            assert "order" in info
            assert "label" in info
            assert "description" in info

    def test_transition_types_constants(self):
        """测试转换类型常量"""
        assert "manual" in TRANSITION_TYPES
        assert "ai_detected" in TRANSITION_TYPES
        assert "mutual_agreement" in TRANSITION_TYPES

    def test_state_transition_rules(self, service):
        """测试状态转换规则"""
        rules = service._state_transition_rules

        # 验证每个状态的允许转换
        assert "matched" in rules
        assert "chatting" in rules["matched"]
        assert "rejected" in rules["matched"]

        assert "dating" in rules
        assert "exclusive" in rules["dating"]
        assert "broken_up" in rules["dating"]


class TestDatingAdviceService:
    """约会建议生成服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return DatingAdviceService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return MagicMock()

    # ============= generate_advice 测试 =============

    @patch('services.relationship_advanced_service.db_session')
    def test_generate_advice_success(self, mock_db_session_ctx, service):
        """测试生成约会建议（成功）"""
        user_id = "user_001"
        target_user_id = "user_002"
        advice_type = "first_date"

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.location = "北京市"

        mock_target_user = MagicMock()
        mock_target_user.id = target_user_id

        mock_db = MagicMock()
        mock_query = MagicMock()
        # 第一个 query 返回 user，第二个返回 target_user
        mock_query.filter.return_value.first.side_effect = [mock_user, mock_target_user]
        mock_db.query.return_value = mock_query
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.generate_advice(user_id, target_user_id, advice_type)

        assert result is not None
        mock_db.add.assert_called()

    @patch('services.relationship_advanced_service.db_session')
    def test_generate_advice_user_not_found(self, mock_db_session_ctx, service):
        """测试生成约会建议（用户不存在）"""
        user_id = "user_not_exist"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        with pytest.raises(ValueError, match="User not found"):
            service.generate_advice(user_id)

    @patch('services.relationship_advanced_service.db_session')
    def test_generate_advice_without_target_user(self, mock_db_session_ctx, service):
        """测试生成约会建议（无目标用户）"""
        user_id = "user_001"
        advice_type = "routine"

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.location = "上海市"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.generate_advice(user_id, advice_type=advice_type)

        assert result is not None

    @patch('services.relationship_advanced_service.db_session')
    def test_generate_advice_unknown_type(self, mock_db_session_ctx, service):
        """测试生成约会建议（未知类型，使用默认）"""
        user_id = "user_001"
        advice_type = "unknown_type"

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.location = "北京市"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.generate_advice(user_id, advice_type=advice_type)

        assert result is not None
        # 应使用 routine 模板

    def test_generate_title_first_date(self, service):
        """测试生成标题（首次约会）"""
        template = {"description": "轻松的咖啡厅约会,便于交流"}
        title = service._generate_title("first_date", template)
        assert "首次约会建议" in title

    def test_generate_title_anniversary(self, service):
        """测试生成标题（纪念日）"""
        template = {"description": "浪漫餐厅共进晚餐"}
        title = service._generate_title("anniversary", template)
        assert "纪念日特别策划" in title

    def test_generate_title_unknown_type(self, service):
        """测试生成标题（未知类型）"""
        template = {"description": "测试活动"}
        title = service._generate_title("unknown", template)
        assert "约会建议" in title

    def test_generate_reasoning_with_target(self, service):
        """测试生成 reasoning（有目标用户）"""
        mock_user = MagicMock()
        mock_target = MagicMock()
        template = {"type": "cafe"}

        reasoning = service._generate_reasoning(mock_user, mock_target, "first_date", template)
        assert "兴趣匹配" in reasoning or "cafe" in reasoning

    def test_generate_reasoning_without_target(self, service):
        """测试生成 reasoning（无目标用户）"""
        mock_user = MagicMock()
        template = {"type": "park"}

        reasoning = service._generate_reasoning(mock_user, None, "routine", template)
        assert "偏好" in reasoning

    def test_get_venue_suggestions_with_data(self, service, mock_db_session):
        """测试获取地点建议（有数据）"""
        mock_venue = MagicMock()
        mock_venue.venue_name = "浪漫咖啡厅"
        mock_venue.address = "北京市朝阳区"
        mock_venue.rating = 4.5
        mock_venue.price_level = 2

        mock_db_session.query.return_value.filter.return_value.limit.return_value.all.return_value = [
            mock_venue
        ]

        venues = service._get_venue_suggestions(mock_db_session, "北京市", "cafe")

        assert len(venues) == 1
        assert venues[0]["name"] == "浪漫咖啡厅"
        assert venues[0]["rating"] == 4.5

    def test_get_venue_suggestions_no_data(self, service, mock_db_session):
        """测试获取地点建议（无数据）"""
        mock_db_session.query.return_value.filter.return_value.limit.return_value.all.return_value = []

        venues = service._get_venue_suggestions(mock_db_session, "北京市", "cafe")

        assert venues == []

    # ============= get_advice 测试 =============

    @patch('services.relationship_advanced_service.db_session_readonly')
    def test_get_advice_with_records(self, mock_db_session_readonly, service):
        """测试获取约会建议（有记录）"""
        user_id = "user_001"

        mock_advice = MagicMock()
        mock_advice.id = "advice_001"
        mock_advice.advice_type = "first_date"
        mock_advice.title = "首次约会建议"
        mock_advice.description = "轻松的咖啡厅约会"
        mock_advice.activity_type = "cafe"
        mock_advice.venue_suggestions = json.dumps([{"name": "浪漫咖啡厅"}])
        mock_advice.estimated_cost = 100
        mock_advice.estimated_duration = 60
        mock_advice.reasoning = "基于兴趣匹配"
        mock_advice.status = "pending"
        mock_advice.confidence_score = 0.8
        mock_advice.created_at = datetime(2024, 1, 15)

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = [mock_advice]
        mock_db.query.return_value = mock_query
        mock_db_session_readonly.return_value.__enter__.return_value = mock_db

        advices = service.get_advice(user_id)

        assert len(advices) == 1
        assert advices[0]["id"] == "advice_001"
        assert advices[0]["advice_type"] == "first_date"
        assert isinstance(advices[0]["venue_suggestions"], list)

    @patch('services.relationship_advanced_service.db_session_readonly')
    def test_get_advice_with_status_filter(self, mock_db_session_readonly, service):
        """测试获取约会建议（带状态过滤）"""
        user_id = "user_001"
        status = "accepted"

        mock_advice = MagicMock()
        mock_advice.id = "advice_001"
        mock_advice.status = status
        mock_advice.venue_suggestions = None
        mock_advice.created_at = datetime(2024, 1, 15)

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        # 第二个 filter 是状态过滤
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = [mock_advice]
        mock_db.query.return_value = mock_query
        mock_db_session_readonly.return_value.__enter__.return_value = mock_db

        advices = service.get_advice(user_id, status=status)

        assert len(advices) == 1
        assert advices[0]["status"] == status

    @patch('services.relationship_advanced_service.db_session_readonly')
    def test_get_advice_empty(self, mock_db_session_readonly, service):
        """测试获取约会建议（无记录）"""
        user_id = "user_001"

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = []
        mock_db.query.return_value = mock_query
        mock_db_session_readonly.return_value.__enter__.return_value = mock_db

        advices = service.get_advice(user_id)

        assert advices == []

    # ============= accept_advice 测试 =============

    @patch('services.relationship_advanced_service.db_session')
    def test_accept_advice_success(self, mock_db_session_ctx, service):
        """测试接受约会建议（成功）"""
        advice_id = "advice_001"

        mock_advice = MagicMock()
        mock_advice.status = "pending"
        mock_advice.accepted_at = None

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_advice
        mock_db.commit.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.accept_advice(advice_id)

        assert result == True
        assert mock_advice.status == "accepted"
        assert mock_advice.accepted_at is not None

    @patch('services.relationship_advanced_service.db_session')
    def test_accept_advice_not_found(self, mock_db_session_ctx, service):
        """测试接受约会建议（不存在）"""
        advice_id = "advice_not_exist"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.accept_advice(advice_id)

        assert result == False

    def test_date_templates_complete(self, service):
        """测试约会模板完整性"""
        assert "first_date" in service._date_templates
        assert "anniversary" in service._date_templates
        assert "routine" in service._date_templates

        # 每个模板应有多个选项
        assert len(service._date_templates["first_date"]) > 0
        assert len(service._date_templates["anniversary"]) > 0


class TestLoveGuidanceService:
    """恋爱指导服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return LoveGuidanceService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return MagicMock()

    # ============= generate_guidance 测试 =============

    @patch('services.relationship_advanced_service.db_session')
    def test_generate_guidance_success(self, mock_db_session_ctx, service):
        """测试生成恋爱指导（成功）"""
        user_id = "user_001"
        guidance_type = "chat_advice"

        mock_user = MagicMock()
        mock_user.id = user_id

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.generate_guidance(user_id, guidance_type)

        assert result is not None
        mock_db.add.assert_called()

    @patch('services.relationship_advanced_service.db_session')
    def test_generate_guidance_user_not_found(self, mock_db_session_ctx, service):
        """测试生成恋爱指导（用户不存在）"""
        user_id = "user_not_exist"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        with pytest.raises(ValueError, match="User not found"):
            service.generate_guidance(user_id, "chat_advice")

    @patch('services.relationship_advanced_service.db_session')
    def test_generate_guidance_with_context(self, mock_db_session_ctx, service):
        """测试生成恋爱指导（带上下文）"""
        user_id = "user_001"
        guidance_type = "conflict_resolution"
        scenario = "意见分歧"
        target_user_id = "user_002"
        context = {"emotion_keywords": ["烦", "累"]}

        mock_user = MagicMock()
        mock_user.id = user_id

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.generate_guidance(
            user_id, guidance_type, scenario, target_user_id, context
        )

        assert result is not None

    def test_generate_guidance_content_chat_advice(self, service):
        """测试生成指导内容（聊天建议）"""
        title, content, steps = service._generate_guidance_content("chat_advice", None, None)

        assert title == "聊天技巧指南"
        assert "沟通" in content
        assert len(steps) == 4
        assert steps[0]["action"] == "倾听对方"

    def test_generate_guidance_content_conflict_resolution(self, service):
        """测试生成指导内容（冲突解决）"""
        title, content, steps = service._generate_guidance_content("conflict_resolution", None, None)

        assert title == "冲突解决指南"
        assert "冲突" in content
        assert len(steps) == 4
        assert steps[0]["action"] == "冷静下来"

    def test_generate_guidance_content_unknown_type(self, service):
        """测试生成指导内容（未知类型）"""
        title, content, steps = service._generate_guidance_content("unknown_type", None, None)

        assert title == "恋爱指南"
        assert len(steps) >= 1

    def test_get_dos_and_donts_chat_advice(self, service):
        """测试获取 Dos 和 Don'ts（聊天建议）"""
        result = service._get_dos_and_donts("chat_advice")

        assert "dos" in result
        assert "donts" in result
        assert "保持真诚" in result["dos"]
        assert "打断对方" in result["donts"]

    def test_get_dos_and_donts_unknown_type(self, service):
        """测试获取 Dos 和 Don'ts（未知类型）"""
        result = service._get_dos_and_donts("unknown_type")

        assert "dos" in result
        assert "donts" in result
        assert len(result["dos"]) > 0

    def test_generate_reasoning_known_types(self, service):
        """测试生成 reasoning（已知类型）"""
        reasoning = service._generate_reasoning("chat_advice")
        assert "心理学研究" in reasoning

        reasoning = service._generate_reasoning("conflict_resolution")
        assert "关系治疗师" in reasoning

    def test_generate_reasoning_unknown_type(self, service):
        """测试生成 reasoning（未知类型）"""
        reasoning = service._generate_reasoning("unknown_type")
        assert "专业研究" in reasoning

    # ============= get_guidance 测试 =============

    @patch('services.relationship_advanced_service.db_session_readonly')
    def test_get_guidance_with_records(self, mock_db_session_readonly, service):
        """测试获取恋爱指导（有记录）"""
        user_id = "user_001"

        mock_guidance = MagicMock()
        mock_guidance.id = "guidance_001"
        mock_guidance.guidance_type = "chat_advice"
        mock_guidance.title = "聊天技巧指南"
        mock_guidance.content = "良好的沟通是关系发展的基础"
        mock_guidance.step_by_step_guide = json.dumps([{"step": 1, "action": "倾听"}])
        mock_guidance.dos_and_donts = json.dumps({"dos": ["保持真诚"], "donts": ["打断"]})
        mock_guidance.is_read = False
        mock_guidance.is_actioned = False
        mock_guidance.created_at = datetime(2024, 1, 15)

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = [mock_guidance]
        mock_db.query.return_value = mock_query
        mock_db_session_readonly.return_value.__enter__.return_value = mock_db

        guidances = service.get_guidance(user_id)

        assert len(guidances) == 1
        assert guidances[0]["guidance_type"] == "chat_advice"
        assert isinstance(guidances[0]["step_by_step_guide"], list)
        assert isinstance(guidances[0]["dos_and_donts"], dict)

    @patch('services.relationship_advanced_service.db_session_readonly')
    def test_get_guidance_with_type_filter(self, mock_db_session_readonly, service):
        """测试获取恋爱指导（带类型过滤）"""
        user_id = "user_001"
        guidance_type = "gift_recommendation"

        mock_guidance = MagicMock()
        mock_guidance.id = "guidance_001"
        mock_guidance.guidance_type = guidance_type
        mock_guidance.step_by_step_guide = None
        mock_guidance.dos_and_donts = None
        mock_guidance.created_at = datetime(2024, 1, 15)

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = [mock_guidance]
        mock_db.query.return_value = mock_query
        mock_db_session_readonly.return_value.__enter__.return_value = mock_db

        guidances = service.get_guidance(user_id, guidance_type=guidance_type)

        assert len(guidances) == 1

    @patch('services.relationship_advanced_service.db_session_readonly')
    def test_get_guidance_empty(self, mock_db_session_readonly, service):
        """测试获取恋爱指导（无记录）"""
        user_id = "user_001"

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = []
        mock_db.query.return_value = mock_query
        mock_db_session_readonly.return_value.__enter__.return_value = mock_db

        guidances = service.get_guidance(user_id)

        assert guidances == []


class TestChatSuggestionService:
    """聊天建议服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return ChatSuggestionService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return MagicMock()

    # ============= generate_suggestion 测试 =============

    @patch('services.relationship_advanced_service.db_session')
    def test_generate_suggestion_success(self, mock_db_session_ctx, service):
        """测试生成聊天建议（成功）"""
        user_id = "user_001"
        suggestion_type = "opener"

        mock_db = MagicMock()
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.generate_suggestion(user_id, suggestion_type)

        assert result is not None
        mock_db.add.assert_called()

    @patch('services.relationship_advanced_service.db_session')
    def test_generate_suggestion_with_context(self, mock_db_session_ctx, service):
        """测试生成聊天建议（带上下文个性化）"""
        user_id = "user_001"
        suggestion_type = "opener"
        context = {"common_interest": "摄影", "description": "首次对话"}

        mock_db = MagicMock()
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.generate_suggestion(user_id, suggestion_type, context=context)

        assert result is not None

    @patch('services.relationship_advanced_service.db_session')
    def test_generate_suggestion_with_conversation_id(self, mock_db_session_ctx, service):
        """测试生成聊天建议（带会话ID）"""
        user_id = "user_001"
        suggestion_type = "topic"
        conversation_id = "conv_001"
        target_user_id = "user_002"

        mock_db = MagicMock()
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.generate_suggestion(
            user_id, suggestion_type, conversation_id, target_user_id
        )

        assert result is not None

    @patch('services.relationship_advanced_service.db_session')
    def test_generate_suggestion_unknown_type(self, mock_db_session_ctx, service):
        """测试生成聊天建议（未知类型，使用默认）"""
        user_id = "user_001"
        suggestion_type = "unknown_type"

        mock_db = MagicMock()
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.generate_suggestion(user_id, suggestion_type)

        assert result is not None
        # 应使用 topic 模板

    def test_get_tone_for_type(self, service):
        """测试根据建议类型获取语气"""
        assert service._get_tone_for_type("opener") == "casual"
        assert service._get_tone_for_type("compliment") == "sincere"
        assert service._get_tone_for_type("confession") == "romantic"
        assert service._get_tone_for_type("unknown") == "casual"

    def test_suggestion_templates_complete(self, service):
        """测试建议模板完整性"""
        assert "opener" in service._suggestion_templates
        assert "topic" in service._suggestion_templates
        assert "compliment" in service._suggestion_templates
        assert "date_invitation" in service._suggestion_templates

        # 每个模板应有多个选项
        assert len(service._suggestion_templates["opener"]) >= 3

    # ============= get_suggestions 测试 =============

    @patch('services.relationship_advanced_service.db_session_readonly')
    def test_get_suggestions_with_records(self, mock_db_session_readonly, service):
        """测试获取聊天建议（有记录）"""
        user_id = "user_001"

        mock_suggestion = MagicMock()
        mock_suggestion.id = "suggestion_001"
        mock_suggestion.suggestion_type = "opener"
        mock_suggestion.suggested_text = "嗨！看到你也在摄影，有什么推荐的吗？"
        mock_suggestion.alternative_texts = json.dumps(["你好，很高兴认识你"])
        mock_suggestion.tone = "casual"
        mock_suggestion.confidence_score = 0.7
        mock_suggestion.status = "pending"
        mock_suggestion.created_at = datetime(2024, 1, 15)

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = [mock_suggestion]
        mock_db.query.return_value = mock_query
        mock_db_session_readonly.return_value.__enter__.return_value = mock_db

        suggestions = service.get_suggestions(user_id)

        assert len(suggestions) == 1
        assert suggestions[0]["suggestion_type"] == "opener"
        assert isinstance(suggestions[0]["alternative_texts"], list)

    @patch('services.relationship_advanced_service.db_session_readonly')
    def test_get_suggestions_with_type_filter(self, mock_db_session_readonly, service):
        """测试获取聊天建议（带类型过滤）"""
        user_id = "user_001"
        suggestion_type = "date_invitation"

        mock_suggestion = MagicMock()
        mock_suggestion.id = "suggestion_001"
        mock_suggestion.suggestion_type = suggestion_type
        mock_suggestion.alternative_texts = None
        mock_suggestion.created_at = datetime(2024, 1, 15)

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = [mock_suggestion]
        mock_db.query.return_value = mock_query
        mock_db_session_readonly.return_value.__enter__.return_value = mock_db

        suggestions = service.get_suggestions(user_id, suggestion_type=suggestion_type)

        assert len(suggestions) == 1

    @patch('services.relationship_advanced_service.db_session_readonly')
    def test_get_suggestions_empty(self, mock_db_session_readonly, service):
        """测试获取聊天建议（无记录）"""
        user_id = "user_001"

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = []
        mock_db.query.return_value = mock_query
        mock_db_session_readonly.return_value.__enter__.return_value = mock_db

        suggestions = service.get_suggestions(user_id)

        assert suggestions == []

    # ============= mark_used 测试 =============

    @patch('services.relationship_advanced_service.db_session')
    def test_mark_used_success(self, mock_db_session_ctx, service):
        """测试标记建议已使用（成功）"""
        suggestion_id = "suggestion_001"

        mock_suggestion = MagicMock()
        mock_suggestion.status = "pending"
        mock_suggestion.used_at = None

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_suggestion
        mock_db.commit.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.mark_used(suggestion_id)

        assert result == True
        assert mock_suggestion.status == "used"
        assert mock_suggestion.used_at is not None

    @patch('services.relationship_advanced_service.db_session')
    def test_mark_used_not_found(self, mock_db_session_ctx, service):
        """测试标记建议已使用（不存在）"""
        suggestion_id = "suggestion_not_exist"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.mark_used(suggestion_id)

        assert result == False


class TestGiftRecommendationService:
    """礼物推荐服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return GiftRecommendationService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return MagicMock()

    # ============= generate_recommendation 测试 =============

    @patch('services.relationship_advanced_service.db_session')
    def test_generate_recommendation_success(self, mock_db_session_ctx, service):
        """测试生成礼物推荐（成功）"""
        user_id = "user_001"
        occasion = "birthday"

        mock_db = MagicMock()
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.generate_recommendation(user_id, occasion)

        assert result is not None
        mock_db.add.assert_called()

    @patch('services.relationship_advanced_service.db_session')
    def test_generate_recommendation_with_recipient(self, mock_db_session_ctx, service):
        """测试生成礼物推荐（带收礼人）"""
        user_id = "user_001"
        occasion = "anniversary"
        recipient_user_id = "user_002"

        mock_db = MagicMock()
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.generate_recommendation(user_id, occasion, recipient_user_id)

        assert result is not None

    @patch('services.relationship_advanced_service.db_session')
    def test_generate_recommendation_with_budget(self, mock_db_session_ctx, service):
        """测试生成礼物推荐（带预算筛选）"""
        user_id = "user_001"
        occasion = "valentines"
        budget_range = (100, 300)

        mock_db = MagicMock()
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.generate_recommendation(user_id, occasion, budget_range=budget_range)

        assert result is not None

    @patch('services.relationship_advanced_service.db_session')
    def test_generate_recommendation_with_preferences(self, mock_db_session_ctx, service):
        """测试生成礼物推荐（带偏好）"""
        user_id = "user_001"
        occasion = "birthday"
        preferences = {"categories": ["个性化", "生活用品"]}

        mock_db = MagicMock()
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.generate_recommendation(user_id, occasion, preferences=preferences)

        assert result is not None

    @patch('services.relationship_advanced_service.db_session')
    def test_generate_recommendation_unknown_occasion(self, mock_db_session_ctx, service):
        """测试生成礼物推荐（未知场合，使用默认）"""
        user_id = "user_001"
        occasion = "unknown_occasion"

        mock_db = MagicMock()
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.generate_recommendation(user_id, occasion)

        assert result is not None
        # 应使用 just_because 模板

    def test_generate_reasoning(self, service):
        """测试生成推荐理由"""
        gift = {"name": "定制相册", "category": "个性化", "description": "收集你们的照片制作成册"}
        reasoning = service._generate_reasoning(gift, "birthday")

        assert "定制相册" in reasoning
        assert "个性化" in reasoning
        assert "birthday" in reasoning

    def test_get_personalization_tips_personalized(self, service):
        """测试获取个性化建议（个性化类别）"""
        gift = {"category": "个性化"}
        tips = service._get_personalization_tips(gift)

        assert len(tips) > 0
        assert "照片" in tips[0]

    def test_get_personalization_tips_jewelry(self, service):
        """测试获取个性化建议（首饰类别）"""
        gift = {"category": "首饰"}
        tips = service._get_personalization_tips(gift)

        assert len(tips) > 0
        assert "尺寸" in tips[0]

    def test_get_personalization_tips_unknown(self, service):
        """测试获取个性化建议（未知类别）"""
        gift = {"category": "unknown"}
        tips = service._get_personalization_tips(gift)

        assert len(tips) > 0
        assert "用心" in tips[0]

    def test_gift_templates_complete(self, service):
        """测试礼物模板完整性"""
        assert "birthday" in service._gift_templates
        assert "anniversary" in service._gift_templates
        assert "valentines" in service._gift_templates
        assert "just_because" in service._gift_templates

        # 每个模板应有多个选项
        assert len(service._gift_templates["birthday"]) >= 3

    # ============= get_recommendations 测试 =============

    @patch('services.relationship_advanced_service.db_session_readonly')
    def test_get_recommendations_with_records(self, mock_db_session_readonly, service):
        """测试获取礼物推荐（有记录）"""
        user_id = "user_001"

        mock_recommendation = MagicMock()
        mock_recommendation.id = "rec_001"
        mock_recommendation.occasion = "birthday"
        mock_recommendation.gift_name = "定制相册"
        mock_recommendation.gift_description = "收集你们的照片制作成册"
        mock_recommendation.gift_category = "个性化"
        mock_recommendation.price_range_min = 100
        mock_recommendation.price_range_max = 300
        mock_recommendation.reasoning = "用心制作"
        mock_recommendation.personalization_tips = json.dumps(["加入照片"])
        mock_recommendation.status = "pending"
        mock_recommendation.created_at = datetime(2024, 1, 15)

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = [mock_recommendation]
        mock_db.query.return_value = mock_query
        mock_db_session_readonly.return_value.__enter__.return_value = mock_db

        recommendations = service.get_recommendations(user_id)

        assert len(recommendations) == 1
        assert recommendations[0]["gift_name"] == "定制相册"
        assert isinstance(recommendations[0]["price_range"], dict)
        assert isinstance(recommendations[0]["personalization_tips"], list)

    @patch('services.relationship_advanced_service.db_session_readonly')
    def test_get_recommendations_with_occasion_filter(self, mock_db_session_readonly, service):
        """测试获取礼物推荐（带场合过滤）"""
        user_id = "user_001"
        occasion = "anniversary"

        mock_recommendation = MagicMock()
        mock_recommendation.id = "rec_001"
        mock_recommendation.occasion = occasion
        mock_recommendation.personalization_tips = None
        mock_recommendation.created_at = datetime(2024, 1, 15)

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = [mock_recommendation]
        mock_db.query.return_value = mock_query
        mock_db_session_readonly.return_value.__enter__.return_value = mock_db

        recommendations = service.get_recommendations(user_id, occasion=occasion)

        assert len(recommendations) == 1

    @patch('services.relationship_advanced_service.db_session_readonly')
    def test_get_recommendations_empty(self, mock_db_session_readonly, service):
        """测试获取礼物推荐（无记录）"""
        user_id = "user_001"

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = []
        mock_db.query.return_value = mock_query
        mock_db_session_readonly.return_value.__enter__.return_value = mock_db

        recommendations = service.get_recommendations(user_id)

        assert recommendations == []


class TestRelationshipHealthService:
    """关系健康度分析服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return RelationshipHealthService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return MagicMock()

    # ============= assess_relationship_health 测试 =============

    @patch('services.relationship_advanced_service.db_session')
    def test_assess_relationship_health_success(self, mock_db_session_ctx, service):
        """测试评估关系健康度（成功）"""
        user_id_1 = "user_001"
        user_id_2 = "user_002"

        # Mock 消息数据
        mock_message = MagicMock()
        mock_message.created_at = datetime(2024, 1, 15)

        mock_first_message = MagicMock()
        mock_first_message.created_at = datetime(2024, 1, 1)

        mock_db = MagicMock()
        mock_query = MagicMock()
        # count() 返回消息数量
        mock_query.filter.return_value.count.return_value = 100
        # order_by().first() 返回最后消息
        mock_query.filter.return_value.order_by.return_value.first.side_effect = [
            mock_message, mock_first_message
        ]
        mock_db.query.return_value = mock_query
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.assess_relationship_health(user_id_1, user_id_2)

        assert result is not None
        assert "assessment_id" in result
        assert "overall_score" in result
        assert "health_level" in result
        assert "dimensions" in result
        assert "strengths" in result
        assert "growth_areas" in result

    @patch('services.relationship_advanced_service.db_session')
    def test_assess_relationship_health_no_messages(self, mock_db_session_ctx, service):
        """测试评估关系健康度（无消息）"""
        user_id_1 = "user_001"
        user_id_2 = "user_002"

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.count.return_value = 0
        mock_query.filter.return_value.order_by.return_value.first.return_value = None
        mock_db.query.return_value = mock_query
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db_session_ctx.return_value.__enter__.return_value = mock_db

        result = service.assess_relationship_health(user_id_1, user_id_2)

        assert result is not None
        # 无消息时应有默认分数
        assert result["overall_score"] >= 0

    # ============= _collect_relationship_metrics 测试 =============

    def test_collect_relationship_metrics_with_data(self, service, mock_db_session):
        """测试收集关系指标（有数据）"""
        user_id_1 = "user_001"
        user_id_2 = "user_002"

        mock_last_message = MagicMock()
        mock_last_message.created_at = datetime(2024, 1, 15)

        mock_first_message = MagicMock()
        mock_first_message.created_at = datetime(2024, 1, 1)

        mock_db_session.query.return_value.filter.return_value.count.return_value = 200
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.first.side_effect = [
            mock_last_message, mock_first_message
        ]

        metrics = service._collect_relationship_metrics(mock_db_session, user_id_1, user_id_2)

        assert metrics["message_count"] == 200
        assert metrics["relationship_days"] == 14
        assert metrics["last_interaction"] is not None

    def test_collect_relationship_metrics_no_messages(self, service, mock_db_session):
        """测试收集关系指标（无消息）"""
        user_id_1 = "user_001"
        user_id_2 = "user_002"

        mock_db_session.query.return_value.filter.return_value.count.return_value = 0
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

        metrics = service._collect_relationship_metrics(mock_db_session, user_id_1, user_id_2)

        assert metrics["message_count"] == 0
        assert metrics["relationship_days"] == 1  # 默认值
        assert metrics["last_interaction"] is None

    # ============= 分数计算测试 =============

    def test_calculate_communication_score_high_activity(self, service):
        """测试计算沟通得分（高活跃度）"""
        metrics = {"message_count": 500, "relationship_days": 30}

        score = service._calculate_communication_score(metrics)

        assert score >= 0
        assert score <= 10
        # 每天约 16 条消息，分数应较高
        assert score >= 10

    def test_calculate_communication_score_low_activity(self, service):
        """测试计算沟通得分（低活跃度）"""
        metrics = {"message_count": 10, "relationship_days": 30}

        score = service._calculate_communication_score(metrics)

        assert score >= 0
        assert score < 5

    def test_calculate_communication_score_zero_days(self, service):
        """测试计算沟通得分（零天）"""
        metrics = {"message_count": 10, "relationship_days": 0}

        score = service._calculate_communication_score(metrics)

        assert score == 5.0  # 默认分数

    def test_calculate_trust_score_long_term(self, service):
        """测试计算信任得分（长期关系）"""
        metrics = {"relationship_days": 200}

        score = service._calculate_trust_score(metrics)

        assert score == 8.0

    def test_calculate_trust_score_medium_term(self, service):
        """测试计算信任得分（中期关系）"""
        metrics = {"relationship_days": 90}

        score = service._calculate_trust_score(metrics)

        assert score == 7.0

    def test_calculate_trust_score_short_term(self, service):
        """测试计算信任得分（短期关系）"""
        metrics = {"relationship_days": 7}

        score = service._calculate_trust_score(metrics)

        assert score == 5.0

    def test_calculate_trust_score_new_relationship(self, service):
        """测试计算信任得分（新关系）"""
        metrics = {"relationship_days": 3}

        score = service._calculate_trust_score(metrics)

        assert score == 4.0

    def test_calculate_intimacy_score_high_messages(self, service):
        """测试计算亲密度得分（高消息量）"""
        metrics = {"message_count": 500}

        score = service._calculate_intimacy_score(metrics)

        assert score == 8.0

    def test_calculate_intimacy_score_medium_messages(self, service):
        """测试计算亲密度得分（中等消息量）"""
        metrics = {"message_count": 150}

        score = service._calculate_intimacy_score(metrics)

        # 150 条消息落在 >= 100 范围，返回 6.0
        assert score == 6.0

    def test_calculate_intimacy_score_low_messages(self, service):
        """测试计算亲密度得分（低消息量）"""
        metrics = {"message_count": 30}

        score = service._calculate_intimacy_score(metrics)

        assert score == 4.0

    def test_calculate_commitment_score(self, service):
        """测试计算承诺度得分"""
        metrics = {"relationship_days": 60}

        score = service._calculate_commitment_score(metrics)

        assert score >= 0
        assert score <= 10
        # 60天约 2分
        assert score >= 1.5

    def test_calculate_compatibility_score(self, service):
        """测试计算兼容性得分"""
        metrics = {}

        score = service._calculate_compatibility_score(metrics)

        assert score == 7.0  # 默认值

    # ============= 健康等级测试 =============

    def test_get_health_level_excellent(self, service):
        """测试获取健康等级（优秀）"""
        level = service._get_health_level(8.5)
        assert level == "excellent"

    def test_get_health_level_good(self, service):
        """测试获取健康等级（良好）"""
        level = service._get_health_level(6.5)
        assert level == "good"

    def test_get_health_level_fair(self, service):
        """测试获取健康等级（一般）"""
        level = service._get_health_level(4.5)
        assert level == "fair"

    def test_get_health_level_needs_attention(self, service):
        """测试获取健康等级（需关注）"""
        level = service._get_health_level(3.0)
        assert level == "needs_attention"

    # ============= 关系分析测试 =============

    def test_analyze_relationship_high_scores(self, service):
        """测试分析关系（高分）"""
        strengths, growth_areas = service._analyze_relationship(
            8.0, 8.5, 7.5, 8.0, 7.0
        )

        assert len(strengths) >= 4  # 大多数维度应被视为优势
        assert len(growth_areas) <= 1

    def test_analyze_relationship_low_scores(self, service):
        """测试分析关系（低分）"""
        strengths, growth_areas = service._analyze_relationship(
            4.0, 5.0, 4.5, 5.5, 5.0
        )

        assert len(strengths) <= 1
        assert len(growth_areas) >= 3  # 大多数维度应被视为需改进

    def test_analyze_relationship_mixed_scores(self, service):
        """测试分析关系（混合分数）"""
        strengths, growth_areas = service._analyze_relationship(
            7.5, 5.0, 8.0, 4.5, 6.0
        )

        # 高分维度：沟通质量、亲密度
        assert "沟通质量" in strengths
        assert "亲密度" in strengths
        # 低分维度：承诺度
        assert "承诺度" in growth_areas

    # ============= 建议生成测试 =============

    def test_generate_suggestions_for_communication(self, service):
        """测试生成建议（沟通质量）"""
        suggestions = service._generate_suggestions(["沟通质量"])

        assert len(suggestions) > 0
        assert any("交流频率" in s for s in suggestions)

    def test_generate_suggestions_for_trust(self, service):
        """测试生成建议（信任度）"""
        suggestions = service._generate_suggestions(["信任度"])

        assert len(suggestions) > 0
        assert any("诚实透明" in s for s in suggestions)

    def test_generate_suggestions_for_multiple_areas(self, service):
        """测试生成建议（多个领域）"""
        suggestions = service._generate_suggestions(["沟通质量", "信任度", "亲密度"])

        assert len(suggestions) <= 5  # 应限制为最多 5 条

    def test_generate_suggestions_empty(self, service):
        """测试生成建议（无需改进领域）"""
        suggestions = service._generate_suggestions([])

        assert len(suggestions) == 1
        assert "用心经营" in suggestions[0]


class TestGlobalServiceInstances:
    """全局服务实例测试"""

    def test_relationship_state_service_instance(self):
        """测试全局关系状态服务实例"""
        from services.relationship_advanced_service import relationship_state_service
        assert isinstance(relationship_state_service, RelationshipStateService)

    def test_dating_advice_service_instance(self):
        """测试全局约会建议服务实例"""
        from services.relationship_advanced_service import dating_advice_service
        assert isinstance(dating_advice_service, DatingAdviceService)

    def test_love_guidance_service_instance(self):
        """测试全局恋爱指导服务实例"""
        from services.relationship_advanced_service import love_guidance_service
        assert isinstance(love_guidance_service, LoveGuidanceService)

    def test_chat_suggestion_service_instance(self):
        """测试全局聊天建议服务实例"""
        from services.relationship_advanced_service import chat_suggestion_service
        assert isinstance(chat_suggestion_service, ChatSuggestionService)

    def test_gift_recommendation_service_instance(self):
        """测试全局礼物推荐服务实例"""
        from services.relationship_advanced_service import gift_recommendation_service
        assert isinstance(gift_recommendation_service, GiftRecommendationService)

    def test_relationship_health_service_instance(self):
        """测试全局关系健康度服务实例"""
        from services.relationship_advanced_service import relationship_health_service
        assert isinstance(relationship_health_service, RelationshipHealthService)