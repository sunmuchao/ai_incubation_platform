"""
P16 圈子融合服务单元测试

测试内容：
1. 部落匹配服务
2. 数字小家服务
3. 见家长模拟服务
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.social_tribe_service import (
    TribeMatchingService,
    DigitalHomeService,
    FamilyMeetingSimulationService,
    tribe_matching_service,
    digital_home_service,
    family_meeting_simulation_service
)
from models.social_tribe_models import (
    LifestyleTribeDB,
    UserTribeMembershipDB,
    TribeCompatibilityDB,
    CoupleDigitalHomeDB,
    CoupleGoalDB,
    CoupleCheckinDB,
    VirtualRoleDB,
    FamilyMeetingSimulationDB
)


class TestTribeMatchingService:
    """部落匹配服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return TribeMatchingService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return MagicMock()

    def test_tag_compatibility_matrix(self, service):
        """测试标签兼容性矩阵"""
        assert "outdoor" in service.TAG_COMPATIBILITY
        assert "homebody" in service.TAG_COMPATIBILITY
        assert "fitness" in service.TAG_COMPATIBILITY

        # 验证兼容性定义
        assert "compatible" in service.TAG_COMPATIBILITY["outdoor"]
        assert "conflicting" in service.TAG_COMPATIBILITY["outdoor"]

    def test_calculate_tribe_compatibility(self, service, mock_db_session):
        """测试计算部落兼容性"""
        user_a_id = "user_a_001"
        user_b_id = "user_b_001"

        # Mock memberships
        mock_tribe_a = MagicMock()
        mock_tribe_a.tribe_id = "tribe_001"

        mock_tribe_b = MagicMock()
        mock_tribe_b.tribe_id = "tribe_001"  # 共同部落

        mock_db_session.query.return_value.filter.return_value.all.side_effect = [
            [mock_tribe_a],  # User A tribes
            [mock_tribe_b]   # User B tribes
        ]

        # Mock tribe with lifestyle tags
        mock_tribe_detail = MagicMock()
        mock_tribe_detail.id = "tribe_001"
        mock_tribe_detail.lifestyle_tags = ["outdoor", "fitness"]

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_tribe_detail

        result = service.calculate_tribe_compatibility(
            user_a_id, user_b_id, mock_db_session
        )

        assert "common_tribes" in result
        assert "compatible_tags" in result
        assert "conflicting_tags" in result
        assert "compatibility_score" in result
        assert "fusion_suggestions" in result

        # 有共同部落，兼容性应大于 0
        assert result["compatibility_score"] >= 0

    def test_calculate_compatibility_no_common_tribes(self, service, mock_db_session):
        """测试无共同部落时的兼容性计算"""
        # Mock different tribes
        mock_tribe_a = MagicMock()
        mock_tribe_a.tribe_id = "tribe_a"

        mock_tribe_b = MagicMock()
        mock_tribe_b.tribe_id = "tribe_b"

        mock_db_session.query.return_value.filter.return_value.all.side_effect = [
            [mock_tribe_a],
            [mock_tribe_b]
        ]

        # Mock tribes with conflicting tags
        def get_tribe(tribe_id):
            mock = MagicMock()
            if tribe_id == "tribe_a":
                mock.lifestyle_tags = ["outdoor"]
            else:
                mock.lifestyle_tags = ["homebody"]
            return mock

        mock_db_session.query.return_value.filter.return_value.first.side_effect = lambda: None

        result = service.calculate_tribe_compatibility(
            "user_a", "user_b", mock_db_session
        )

        assert len(result["common_tribes"]) == 0

    def test_get_user_lifestyle_tags(self, service, mock_db_session):
        """测试获取用户生活方式标签"""
        mock_membership = MagicMock()
        mock_membership.tribe_id = "tribe_001"

        mock_tribe = MagicMock()
        mock_tribe.lifestyle_tags = ["outdoor", "fitness", "traveler"]

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_tribe

        tags = service._get_user_lifestyle_tags([mock_membership], mock_db_session)

        assert "outdoor" in tags
        assert "fitness" in tags

    def test_generate_fusion_suggestions(self, service):
        """测试生成圈子融合建议"""
        tags_a = ["outdoor", "music"]
        tags_b = ["fitness", "music"]
        compatible = [("outdoor", "fitness")]

        suggestions = service._generate_fusion_suggestions(tags_a, tags_b, compatible)

        assert len(suggestions) > 0
        assert any(s["type"] in ["shared_activity", "explore", "share"] for s in suggestions)

    def test_generate_suggestions_with_unique_tags(self, service):
        """测试生成独特兴趣建议"""
        tags_a = ["reading", "gaming"]
        tags_b = ["outdoor", "fitness"]
        compatible = []

        suggestions = service._generate_fusion_suggestions(tags_a, tags_b, compatible)

        # 应有 explore 和 share 建议
        types = [s["type"] for s in suggestions]
        assert "explore" in types or "share" in types


class TestDigitalHomeService:
    """数字小家服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return DigitalHomeService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return MagicMock()

    def test_create_digital_home(self, service, mock_db_session):
        """测试创建数字小家"""
        user_a_id = "user_a_001"
        user_b_id = "user_b_001"
        home_name = "温馨小家"
        theme = "浪漫"

        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        home = service.create_digital_home(
            user_a_id, user_b_id, home_name, theme, mock_db_session
        )

        assert home is not None
        assert home.user_a_id == user_a_id
        assert home.user_b_id == user_b_id
        assert home.home_name == home_name
        assert home.theme == theme
        assert home.shared_space_config is not None

    def test_create_digital_home_default_theme(self, service, mock_db_session):
        """测试创建数字小家使用默认主题"""
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        home = service.create_digital_home(
            "user_a", "user_b", "小家", db_session=mock_db_session
        )

        assert home.theme == "温馨"

    def test_create_couple_goal(self, service, mock_db_session):
        """测试创建共同目标"""
        home_id = "home_001"
        goal_title = "一起减肥 10 斤"
        goal_type = "health"
        target_value = 10.0
        target_date = datetime.utcnow() + timedelta(days=30)

        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        goal = service.create_couple_goal(
            home_id, "user_a", "user_b",
            goal_title, goal_type, target_value, target_date,
            mock_db_session
        )

        assert goal is not None
        assert goal.goal_title == goal_title
        assert goal.goal_type == goal_type
        assert goal.target_value == target_value
        assert goal.status == "active"

    def test_checkin_goal(self, service, mock_db_session):
        """测试打卡目标"""
        goal_id = "goal_001"
        user_id = "user_001"

        # Mock goal
        mock_goal = MagicMock()
        mock_goal.id = goal_id
        mock_goal.current_value = 0.0
        mock_goal.target_value = 10.0
        mock_goal.status = "active"

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_goal
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        checkin = service.checkin_goal(
            goal_id, user_id, checkin_value=2.0,
            proof_photo_urls=["photo1.jpg"],
            db_session=mock_db_session
        )

        assert checkin is not None
        assert checkin.checkin_value == 2.0
        assert mock_goal.current_value == 2.0
        mock_db_session.commit.assert_called()

    def test_checkin_goal_complete(self, service, mock_db_session):
        """测试完成目标打卡"""
        mock_goal = MagicMock()
        mock_goal.id = "goal_001"
        mock_goal.current_value = 8.0
        mock_goal.target_value = 10.0
        mock_goal.status = "active"

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_goal
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        service.checkin_goal("goal_001", "user_001", checkin_value=3.0, db_session=mock_db_session)

        # 应完成目标
        assert mock_goal.current_value == 11.0
        assert mock_goal.status == "completed"
        assert mock_goal.completed_at is not None

    def test_checkin_goal_not_found(self, service, mock_db_session):
        """测试打卡不存在目标"""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="目标不存在"):
            service.checkin_goal("nonexistent_goal", "user_001", db_session=mock_db_session)


class TestFamilyMeetingSimulationService:
    """见家长模拟服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return FamilyMeetingSimulationService()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return MagicMock()

    def test_create_virtual_role(self, service, mock_db_session):
        """测试创建虚拟角色"""
        user_id = "user_001"
        role_name = "严厉的父亲"
        role_type = "parent"
        personality = "严厉"

        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        role = service.create_virtual_role(
            user_id, role_name, role_type, personality, mock_db_session
        )

        assert role is not None
        assert role.role_name == role_name
        assert role.role_type == role_type
        assert role.personality == personality
        assert len(role.typical_questions) > 0

    def test_create_virtual_role_gentle_parent(self, service, mock_db_session):
        """测试创建温和型家长角色"""
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        role = service.create_virtual_role(
            "user_001", "温和的母亲", "parent", "温和", mock_db_session
        )

        assert role is not None
        assert any("孩子" in q or "认识" in q for q in role.typical_questions)

    def test_generate_typical_questions(self, service):
        """测试生成典型问题"""
        # 严厉家长
        questions = service._generate_typical_questions("parent", "严厉")
        assert len(questions) > 0
        assert any("工作" in q or "房" in q or "结婚" in q for q in questions)

        # 温和家长
        questions = service._generate_typical_questions("parent", "温和")
        assert len(questions) > 0

        # 开明家长
        questions = service._generate_typical_questions("parent", "开明")
        assert len(questions) > 0

    def test_start_simulation(self, service, mock_db_session):
        """测试开始见家长模拟"""
        user_id = "user_001"
        role_id = "role_001"
        scenario = "第一次去对方家"

        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        simulation = service.start_simulation(
            user_id, role_id, scenario, mock_db_session
        )

        assert simulation is not None
        assert simulation.user_id == user_id
        assert simulation.role_id == role_id
        assert simulation.scenario == scenario
        assert simulation.status == "ongoing"
        assert simulation.conversation_history == []

    def test_add_simulation_message(self, service, mock_db_session):
        """测试添加模拟对话消息"""
        simulation_id = "sim_001"

        mock_sim = MagicMock()
        mock_sim.id = simulation_id
        mock_sim.conversation_history = None

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_sim
        mock_db_session.commit.return_value = None

        result = service.add_simulation_message(
            simulation_id, "user", "你好，我是小王", mock_db_session
        )

        assert result is True
        assert len(mock_sim.conversation_history) == 1
        assert mock_sim.conversation_history[0]["role"] == "user"
        assert mock_sim.conversation_history[0]["content"] == "你好，我是小王"

    def test_add_simulation_message_not_found(self, service, mock_db_session):
        """测试添加消息到不存在的模拟"""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        result = service.add_simulation_message(
            "nonexistent_sim", "user", "hello", mock_db_session
        )

        assert result is False

    def test_complete_simulation(self, service, mock_db_session):
        """测试完成模拟"""
        simulation_id = "sim_001"
        performance_scores = {
            "communication": 8,
            "respect": 9,
            "confidence": 7
        }

        mock_sim = MagicMock()
        mock_sim.id = simulation_id
        mock_sim.conversation_history = []

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_sim
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        result = service.complete_simulation(
            simulation_id, performance_scores, mock_db_session
        )

        assert result is not None
        assert result.is_completed is True
        assert result.completed_at is not None
        assert result.performance_scores == performance_scores
        assert result.ai_feedback is not None

    def test_complete_simulation_not_found(self, service, mock_db_session):
        """测试完成不存在的模拟"""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="模拟不存在"):
            service.complete_simulation("nonexistent_sim", {}, mock_db_session)

    def test_generate_ai_feedback(self, service):
        """测试生成 AI 反馈"""
        # 高分
        feedback = service._generate_ai_feedback({"communication": 9, "respect": 9})
        assert "出色" in feedback or "良好" in feedback

        # 中等分数
        feedback = service._generate_ai_feedback({"communication": 6, "respect": 7})
        assert "不错" in feedback or "改进" in feedback

        # 低分
        feedback = service._generate_ai_feedback({"communication": 3, "respect": 4})
        assert "建议" in feedback or "练习" in feedback

    def test_generate_improvement_suggestions(self, service):
        """测试生成改进建议"""
        scores = {
            "communication": 4,
            "respect": 5,
            "confidence": 3
        }

        suggestions = service._generate_improvement_suggestions(scores)

        assert len(suggestions) > 0
        assert any("表达" in s for s in suggestions)
        assert any("自信" in s for s in suggestions)


class TestP16Integration:
    """P16 服务集成测试"""

    def test_global_service_instances(self):
        """测试全局服务实例存在"""
        from services.social_tribe_service import (
            tribe_matching_service,
            digital_home_service,
            family_meeting_simulation_service
        )

        assert tribe_matching_service is not None
        assert digital_home_service is not None
        assert family_meeting_simulation_service is not None

    def test_tribe_matching_workflow(self):
        """测试部落匹配完整工作流"""
        service = TribeMatchingService()

        # 验证兼容性矩阵
        assert service.TAG_COMPATIBILITY is not None
        assert len(service.TAG_COMPATIBILITY) > 0

    def test_digital_home_workflow(self):
        """测试数字小家完整工作流"""
        service = DigitalHomeService()

        # 不使用数据库验证基本功能
        assert service is not None

    def test_family_simulation_workflow(self):
        """测试见家长模拟完整工作流"""
        service = FamilyMeetingSimulationService()

        # 测试问题生成
        questions = service._generate_typical_questions("parent", "严厉")
        assert len(questions) > 0

        # 测试反馈生成
        feedback = service._generate_ai_feedback({"communication": 8, "respect": 8})
        assert feedback is not None

        # 测试建议生成
        suggestions = service._generate_improvement_suggestions({
            "communication": 4,
            "confidence": 3
        })
        assert len(suggestions) > 0
