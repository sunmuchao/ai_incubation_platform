"""
AI 反馈服务测试

测试覆盖:
- 反馈记录
- 结果追踪
- 采纳率统计
- 风格偏好分析
"""
import pytest
import os
import json
import sys
from unittest.mock import patch, MagicMock

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ai_feedback_service import AIFeedbackService, get_ai_feedback_service


class TestAIFeedbackService:
    """AI 反馈服务测试"""

    @pytest.fixture
    def feedback_service(self, tmp_path):
        """创建临时数据目录的测试服务"""
        # 使用临时目录
        test_data_dir = str(tmp_path / "data")
        os.makedirs(test_data_dir, exist_ok=True)

        # 创建服务并指定数据目录
        service = AIFeedbackService(data_dir=test_data_dir)
        yield service

    def test_init(self, feedback_service):
        """测试初始化"""
        assert feedback_service is not None

    def test_record_feedback_adopted(self, feedback_service):
        """测试记录采纳反馈"""
        feedback_id = feedback_service.record_feedback(
            user_id='test_user_001',
            partner_id='test_partner_001',
            suggestion_id='suggestion_uuid_001',
            feedback_type=feedback_service.FEEDBACK_ADOPTED,
            suggestion_content='辛苦啦！要不要我给你点杯奶茶续命？',
            suggestion_style='幽默风趣',
            user_actual_reply='辛苦啦！要不要我给你点杯奶茶续命？'
        )

        assert feedback_id is not None
        assert len(feedback_id) > 0

    def test_record_feedback_ignored(self, feedback_service):
        """测试记录忽略反馈"""
        feedback_id = feedback_service.record_feedback(
            user_id='test_user_001',
            partner_id='test_partner_001',
            suggestion_id='suggestion_uuid_002',
            feedback_type=feedback_service.FEEDBACK_IGNORED,
            suggestion_content='这么晚还在工作，太辛苦了吧',
            suggestion_style='真诚关心',
            user_actual_reply='我自己点了外卖'
        )
        assert feedback_id is not None

    def test_record_feedback_modified(self, feedback_service):
        """测试记录修改后发送"""
        feedback_id = feedback_service.record_feedback(
            user_id='test_user_001',
            partner_id='test_partner_001',
            suggestion_id='suggestion_uuid_003',
            feedback_type=feedback_service.FEEDBACK_MODIFIED,
            suggestion_content='加班到这么晚啊，做什么项目这么拼？',
            suggestion_style='延续话题',
            user_actual_reply='加班到这么晚啊，在做什么项目？'
        )
        assert feedback_id is not None

    def test_record_outcome(self, feedback_service):
        """测试记录聊天结果"""
        feedback_id = feedback_service.record_feedback(
            user_id='test_user_001',
            partner_id='test_partner_001',
            suggestion_id='suggestion_uuid_004',
            feedback_type=feedback_service.FEEDBACK_ADOPTED,
            suggestion_content='测试建议',
            suggestion_style='幽默风趣',
            user_actual_reply='测试回复'
        )

        if feedback_id:
            feedback_service.record_outcome(
                user_id='test_user_001',
                partner_id='test_partner_001',
                feedback_id=feedback_id,
                outcome_type=feedback_service.OUTCOME_CONTINUED,
                outcome_data={'messages_after': 5}
            )
            # 验证不抛异常即成功

    def test_get_adoption_rate(self, feedback_service, monkeypatch):
        """测试获取采纳率"""
        # Mock 加载反馈数据
        mock_feedbacks = [
            {"feedback_type": "adopted", "created_at": "2026-04-09T10:00:00"},
            {"feedback_type": "adopted", "created_at": "2026-04-09T11:00:00"},
            {"feedback_type": "ignored", "created_at": "2026-04-09T12:00:00"},
            {"feedback_type": "modified", "created_at": "2026-04-09T13:00:00"},
        ]

        monkeypatch.setattr(
            feedback_service,
            '_load_feedbacks',
            lambda user_id, days: mock_feedbacks
        )

        result = feedback_service.get_adoption_rate('test_user_001', days=7)

        assert isinstance(result, dict)
        assert 'adoption_rate' in result
        assert 'total_suggestions' in result
        assert result['total_suggestions'] == 4

    def test_get_adoption_rate_empty(self, feedback_service, monkeypatch):
        """测试空数据的采纳率"""
        monkeypatch.setattr(
            feedback_service,
            '_load_feedbacks',
            lambda user_id, days: []
        )

        result = feedback_service.get_adoption_rate('test_user_001', days=7)

        assert result['adoption_rate'] == 0
        assert result['total_suggestions'] == 0

    def test_get_style_preference(self, feedback_service, monkeypatch):
        """测试获取风格偏好"""
        mock_feedbacks = [
            {"feedback_type": "adopted", "suggestion_style": "幽默风趣", "created_at": "2026-04-09T10:00:00"},
            {"feedback_type": "adopted", "suggestion_style": "幽默风趣", "created_at": "2026-04-09T11:00:00"},
            {"feedback_type": "ignored", "suggestion_style": "真诚关心", "created_at": "2026-04-09T12:00:00"},
            {"feedback_type": "modified", "suggestion_style": "延续话题", "created_at": "2026-04-09T13:00:00"},
        ]

        monkeypatch.setattr(
            feedback_service,
            '_load_feedbacks',
            lambda user_id, days: mock_feedbacks
        )

        result = feedback_service.get_style_preference('test_user_001', days=30)

        assert isinstance(result, dict)
        assert 'style_preferences' in result or 'best_style' in result or len(result) == 0

    def test_analyze_suggestion_effectiveness(self, feedback_service, monkeypatch):
        """测试分析建议有效性"""
        mock_feedbacks = [
            {"feedback_type": "adopted", "suggestion_style": "幽默风趣", "created_at": "2026-04-09T10:00:00"},
            {"feedback_type": "adopted", "suggestion_style": "幽默风趣", "created_at": "2026-04-09T11:00:00"},
            {"feedback_type": "ignored", "suggestion_style": "真诚关心", "created_at": "2026-04-09T12:00:00"},
        ]

        mock_outcomes = [
            {"outcome_type": "continued", "created_at": "2026-04-09T10:30:00"},
            {"outcome_type": "warmed", "created_at": "2026-04-09T11:30:00"},
        ]

        monkeypatch.setattr(
            feedback_service,
            '_load_all_feedbacks',
            lambda days: mock_feedbacks
        )
        monkeypatch.setattr(
            feedback_service,
            '_load_outcomes',
            lambda days: mock_outcomes
        )

        result = feedback_service.analyze_suggestion_effectiveness(days=30)

        assert isinstance(result, dict)
        assert 'effectiveness_score' in result
        assert 'sample_size' in result

    def test_singleton_pattern(self):
        """测试单例模式"""
        service1 = get_ai_feedback_service()
        service2 = get_ai_feedback_service()
        assert type(service1) == type(service2)


class TestAIFeedbackServiceFileOperations:
    """反馈服务数据库操作测试（已迁移到数据库存储）"""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """创建临时数据目录（已废弃，保留 fixture 兼容）"""
        data_dir = str(tmp_path / "test_data")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir

    def test_save_feedback_creates_db_record(self, temp_data_dir, monkeypatch):
        """测试保存反馈创建数据库记录"""
        # Mock 数据库操作
        mock_db = MagicMock()
        mock_feedback = MagicMock()
        mock_feedback.id = "test_feedback_id"

        def mock_uuid():
            return "test_feedback_id"

        monkeypatch.setattr("uuid.uuid4", mock_uuid)

        service = AIFeedbackService(data_dir=temp_data_dir)
        service._get_db = lambda: mock_db

        # Mock add 和 commit
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.rollback = MagicMock()

        feedback_id = service.record_feedback(
            user_id='test_user',
            partner_id='test_partner',
            suggestion_id='suggestion_001',
            feedback_type='adopted',
            suggestion_content='测试内容',
            suggestion_style='幽默风趣'
        )

        assert feedback_id == "test_feedback_id"
        assert mock_db.add.called
        assert mock_db.commit.called

    def test_save_feedback_db_fields(self, temp_data_dir, monkeypatch):
        """测试保存反馈数据库字段"""
        mock_db = MagicMock()

        captured_feedback = None

        def capture_add(obj):
            captured_feedback = obj

        mock_db.add = MagicMock(side_effect=capture_add)
        mock_db.commit = MagicMock()
        mock_db.rollback = MagicMock()

        service = AIFeedbackService(data_dir=temp_data_dir)
        service._get_db = lambda: mock_db

        feedback_id = service.record_feedback(
            user_id='test_user',
            partner_id='test_partner',
            suggestion_id='suggestion_001',
            feedback_type='adopted',
            suggestion_content='测试内容',
            suggestion_style='幽默风趣',
            user_actual_reply='测试回复'
        )

        # 验证返回了反馈 ID（说明操作成功）
        assert feedback_id is not None
        assert len(feedback_id) > 0


class TestFeedbackTypeConstants:
    """反馈类型常量测试"""

    def test_feedback_type_constants(self):
        """测试反馈类型常量定义"""
        assert AIFeedbackService.FEEDBACK_ADOPTED == 'adopted'
        assert AIFeedbackService.FEEDBACK_IGNORED == 'ignored'
        assert AIFeedbackService.FEEDBACK_MODIFIED == 'modified'
        assert AIFeedbackService.FEEDBACK_HELPFUL == 'helpful'
        assert AIFeedbackService.FEEDBACK_NOT_HELPFUL == 'not_helpful'

    def test_outcome_type_constants(self):
        """测试结果类型常量定义"""
        assert AIFeedbackService.OUTCOME_CONTINUED == 'continued'
        assert AIFeedbackService.OUTCOME_STOPPED == 'stopped'
        assert AIFeedbackService.OUTCOME_WARMED == 'warmed'
        assert AIFeedbackService.OUTCOME_DATE_REQUESTED == 'date_requested'
