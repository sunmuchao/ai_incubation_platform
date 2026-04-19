"""
关系进展追踪服务测试

测试 RelationshipProgressService 的核心功能：
- 关系阶段定义
- 里程碑类型
- 进展记录
- 时间线获取
- 关系健康度评估
- 可视化数据生成
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
import uuid

# 尝试导入服务模块
try:
    from services.relationship_progress_service import (
        RelationshipProgressService,
        RELATIONSHIP_STAGES,
        MILESTONE_TYPES,
        relationship_progress_service,
    )
except ImportError:
    pytest.skip("relationship_progress_service not importable", allow_module_level=True)


class TestRelationshipStages:
    """关系阶段定义测试"""

    def test_stages_exist(self):
        """测试阶段存在"""
        expected_stages = [
            "matched",
            "chatting",
            "exchanged_contact",
            "first_date",
            "dating",
            "exclusive",
            "in_relationship"
        ]

        for stage in expected_stages:
            assert stage in RELATIONSHIP_STAGES

    def test_stages_count(self):
        """测试阶段数量"""
        assert len(RELATIONSHIP_STAGES) == 7

    def test_stages_order(self):
        """测试阶段顺序"""
        assert RELATIONSHIP_STAGES["matched"]["order"] == 1
        assert RELATIONSHIP_STAGES["chatting"]["order"] == 2
        assert RELATIONSHIP_STAGES["exchanged_contact"]["order"] == 3
        assert RELATIONSHIP_STAGES["first_date"]["order"] == 4
        assert RELATIONSHIP_STAGES["dating"]["order"] == 5
        assert RELATIONSHIP_STAGES["exclusive"]["order"] == 6
        assert RELATIONSHIP_STAGES["in_relationship"]["order"] == 7

    def test_stages_labels(self):
        """测试阶段标签"""
        assert RELATIONSHIP_STAGES["matched"]["label"] == "已匹配"
        assert RELATIONSHIP_STAGES["chatting"]["label"] == "聊天中"
        assert RELATIONSHIP_STAGES["exchanged_contact"]["label"] == "交换联系方式"
        assert RELATIONSHIP_STAGES["first_date"]["label"] == "首次约会"
        assert RELATIONSHIP_STAGES["dating"]["label"] == "约会中"
        assert RELATIONSHIP_STAGES["exclusive"]["label"] == "确定关系"
        assert RELATIONSHIP_STAGES["in_relationship"]["label"] == "恋爱中"

    def test_stages_structure(self):
        """测试阶段结构"""
        for stage, config in RELATIONSHIP_STAGES.items():
            assert "order" in config
            assert "label" in config
            assert "description" in config


class TestMilestoneTypes:
    """里程碑类型测试"""

    def test_milestone_types_exist(self):
        """测试里程碑类型存在"""
        expected_types = [
            "first_message",
            "first_like",
            "deep_conversation",
            "contact_exchange",
            "first_date",
            "anniversary",
            "relationship_status_change"
        ]

        for mt in expected_types:
            assert mt in MILESTONE_TYPES

    def test_milestone_types_count(self):
        """测试里程碑类型数量"""
        assert len(MILESTONE_TYPES) == 7

    def test_milestone_types_labels(self):
        """测试里程碑类型标签"""
        assert MILESTONE_TYPES["first_message"] == "第一条消息"
        assert MILESTONE_TYPES["first_like"] == "第一次点赞"
        assert MILESTONE_TYPES["deep_conversation"] == "深度对话"
        assert MILESTONE_TYPES["contact_exchange"] == "交换联系方式"
        assert MILESTONE_TYPES["first_date"] == "第一次约会"
        assert MILESTONE_TYPES["anniversary"] == "纪念日"
        assert MILESTONE_TYPES["relationship_status_change"] == "关系状态变更"


class TestServiceInitialization:
    """服务初始化测试"""

    def test_service_creation(self):
        """测试服务创建"""
        service = RelationshipProgressService()

        assert service is not None
        assert service._stage_progression_weights is not None

    def test_stage_progression_weights(self):
        """测试阶段进展权重"""
        service = RelationshipProgressService()

        weights = service._stage_progression_weights
        assert weights["message_count"] == 0.3
        assert weights["conversation_depth"] == 0.3
        assert weights["interaction_frequency"] == 0.2
        assert weights["milestone_achievement"] == 0.2

    def test_global_service_instance(self):
        """测试全局服务实例"""
        assert relationship_progress_service is not None
        assert isinstance(relationship_progress_service, RelationshipProgressService)


class TestInferStageFromProgress:
    """从进展推断阶段测试"""

    def test_first_message_to_chatting(self):
        """测试第一条消息 -> 聊天中"""
        service = RelationshipProgressService()

        stage = service._infer_stage_from_progress("first_message")
        assert stage == "chatting"

    def test_contact_exchange_to_exchanged_contact(self):
        """测试交换联系方式"""
        service = RelationshipProgressService()

        stage = service._infer_stage_from_progress("contact_exchange")
        assert stage == "exchanged_contact"

    def test_first_date_to_first_date(self):
        """测试首次约会"""
        service = RelationshipProgressService()

        stage = service._infer_stage_from_progress("first_date")
        assert stage == "first_date"

    def test_relationship_milestone_to_dating(self):
        """测试关系里程碑"""
        service = RelationshipProgressService()

        stage = service._infer_stage_from_progress("relationship_milestone")
        assert stage == "dating"

    def test_unknown_progress_type(self):
        """测试未知进展类型"""
        service = RelationshipProgressService()

        stage = service._infer_stage_from_progress("unknown_type")
        assert stage is None

    def test_empty_progress_type(self):
        """测试空进展类型"""
        service = RelationshipProgressService()

        stage = service._infer_stage_from_progress("")
        assert stage is None


class TestGetHealthLevel:
    """健康等级测试"""

    def test_excellent_level(self):
        """测试优秀等级"""
        service = RelationshipProgressService()

        level = service._get_health_level(9.0)
        assert level == "excellent"

        level = service._get_health_level(8.5)
        assert level == "excellent"

        level = service._get_health_level(8.0)
        assert level == "excellent"

    def test_good_level(self):
        """测试良好等级"""
        service = RelationshipProgressService()

        level = service._get_health_level(7.0)
        assert level == "good"

        level = service._get_health_level(6.5)
        assert level == "good"

        level = service._get_health_level(6.0)
        assert level == "good"

    def test_fair_level(self):
        """测试一般等级"""
        service = RelationshipProgressService()

        level = service._get_health_level(5.0)
        assert level == "fair"

        level = service._get_health_level(4.5)
        assert level == "fair"

        level = service._get_health_level(4.0)
        assert level == "fair"

    def test_needs_attention_level(self):
        """测试需要关注等级"""
        service = RelationshipProgressService()

        level = service._get_health_level(3.0)
        assert level == "needs_attention"

        level = service._get_health_level(2.0)
        assert level == "needs_attention"

        level = service._get_health_level(0.0)
        assert level == "needs_attention"


class TestEmptyHealthScore:
    """空健康评分测试"""

    def test_empty_health_score_structure(self):
        """测试空健康评分结构"""
        service = RelationshipProgressService()

        result = service._empty_health_score()

        assert result["overall_score"] == 0
        assert result["health_level"] == "no_data"
        assert "dimensions" in result
        assert result["dimensions"]["message_activity"] == 0
        assert result["dimensions"]["milestone_progress"] == 0
        assert result["dimensions"]["relationship_stage"] == 0

    def test_empty_health_score_suggestions(self):
        """测试空健康评分建议"""
        service = RelationshipProgressService()

        result = service._empty_health_score()

        assert len(result["suggestions"]) == 1
        assert "开始互动" in result["suggestions"][0]


class TestCalculateMilestoneScore:
    """里程碑得分计算测试"""

    def test_calculate_milestone_score_empty(self):
        """测试空里程碑"""
        service = RelationshipProgressService()

        score = service._calculate_milestone_score([])
        assert score == 0

    def test_calculate_milestone_score_single(self):
        """测试单个里程碑"""
        service = RelationshipProgressService()

        mock_progress = MagicMock()
        mock_progress.progress_score = 5

        score = service._calculate_milestone_score([mock_progress])
        # avg_score = 5, count_bonus = min(2, 1/5) = 0.2
        # (5/10) * 8 + 0.2 = 4.0 + 0.2 = 4.2
        assert score == 4.2

    def test_calculate_milestone_score_multiple(self):
        """测试多个里程碑"""
        service = RelationshipProgressService()

        mock_progresses = [
            MagicMock(progress_score=7),
            MagicMock(progress_score=8),
            MagicMock(progress_score=9),
        ]

        score = service._calculate_milestone_score(mock_progresses)
        # avg_score = 8, count_bonus = min(2, 3/5) = 0.6
        # (8/10) * 8 + 0.6 = 6.4 + 0.6 = 7.0
        assert score == 7.0

    def test_calculate_milestone_score_high_scores(self):
        """测试高分里程碑"""
        service = RelationshipProgressService()

        mock_progresses = [
            MagicMock(progress_score=10),
            MagicMock(progress_score=10),
            MagicMock(progress_score=10),
            MagicMock(progress_score=10),
            MagicMock(progress_score=10),
        ]

        score = service._calculate_milestone_score(mock_progresses)
        # avg_score = 10, count_bonus = min(2, 5/5) = 1
        # (10/10) * 8 + 1 = 8 + 1 = 9
        assert score == 9.0


class TestCalculateStageScore:
    """阶段得分计算测试"""

    def test_calculate_stage_score_empty(self):
        """测试空阶段"""
        service = RelationshipProgressService()

        score = service._calculate_stage_score([])
        assert score == 0

    def test_calculate_stage_score_matched(self):
        """测试匹配阶段"""
        service = RelationshipProgressService()

        mock_progress = MagicMock()
        mock_progress.progress_type = "matched"  # 不在映射中，返回 None

        score = service._calculate_stage_score([mock_progress])
        # None -> order 0
        assert score == 0

    def test_calculate_stage_score_chatting(self):
        """测试聊天阶段"""
        service = RelationshipProgressService()

        mock_progress = MagicMock()
        mock_progress.progress_type = "first_message"  # -> chatting, order 2

        score = service._calculate_stage_score([mock_progress])
        # order 2, (2/7) * 10 ≈ 2.86
        assert round(score, 1) == 2.9

    def test_calculate_stage_score_in_relationship(self):
        """测试恋爱阶段"""
        service = RelationshipProgressService()

        mock_progress = MagicMock()
        mock_progress.progress_type = "relationship_milestone"  # -> dating, order 5

        score = service._calculate_stage_score([mock_progress])
        # order 5, (5/7) * 10 ≈ 7.14
        assert round(score, 1) == 7.1


class TestGenerateHealthSuggestions:
    """健康建议生成测试"""

    def test_generate_suggestions_low_score(self):
        """测试低分建议"""
        service = RelationshipProgressService()

        mock_progresses = [
            MagicMock(progress_type="first_message")
        ]

        suggestions = service._generate_health_suggestions(3.0, mock_progresses)

        assert len(suggestions) >= 1
        assert any("互动较少" in s for s in suggestions)

    def test_generate_suggestions_medium_score(self):
        """测试中等分建议"""
        service = RelationshipProgressService()

        mock_progresses = [
            MagicMock(progress_type="first_message"),
            MagicMock(progress_type="deep_conversation"),
            MagicMock(progress_type="deep_conversation"),
            MagicMock(progress_type="deep_conversation"),
        ]

        suggestions = service._generate_health_suggestions(5.0, mock_progresses)

        assert any("线下见面" in s for s in suggestions)

    def test_generate_suggestions_no_first_date(self):
        """测试缺少首次约会建议"""
        service = RelationshipProgressService()

        mock_progresses = [
            MagicMock(progress_type="first_message"),
            MagicMock(progress_type="deep_conversation"),
            MagicMock(progress_type="deep_conversation"),
            MagicMock(progress_type="deep_conversation"),
        ]

        suggestions = service._generate_health_suggestions(6.0, mock_progresses)

        assert any("见面" in s for s in suggestions)

    def test_generate_suggestions_no_contact_exchange(self):
        """测试缺少交换联系方式建议"""
        service = RelationshipProgressService()

        mock_progresses = [
            MagicMock(progress_type="first_message"),
            MagicMock(progress_type="deep_conversation"),
            MagicMock(progress_type="first_like"),
        ]

        suggestions = service._generate_health_suggestions(6.0, mock_progresses)

        assert any("联系方式" in s for s in suggestions)

    def test_generate_suggestions_high_score(self):
        """测试高分建议"""
        service = RelationshipProgressService()

        mock_progresses = [
            MagicMock(progress_type="first_message"),
            MagicMock(progress_type="contact_exchange"),
            MagicMock(progress_type="first_date"),
        ]

        suggestions = service._generate_health_suggestions(8.0, mock_progresses)

        # 高分可能没有建议
        assert isinstance(suggestions, list)


class TestEdgeCases:
    """边界值测试"""

    def test_zero_score_health_level(self):
        """测试零分健康等级"""
        service = RelationshipProgressService()

        level = service._get_health_level(0.0)
        assert level == "needs_attention"

    def test_max_score_health_level(self):
        """测试满分健康等级"""
        service = RelationshipProgressService()

        level = service._get_health_level(10.0)
        assert level == "excellent"

    def test_boundary_score_excellent(self):
        """测试边界分数 - 优秀"""
        service = RelationshipProgressService()

        # 刚好 8.0 是优秀
        level = service._get_health_level(8.0)
        assert level == "excellent"

        # 7.99 是良好
        level = service._get_health_level(7.99)
        assert level == "good"

    def test_boundary_score_good(self):
        """测试边界分数 - 良好"""
        service = RelationshipProgressService()

        # 刚好 6.0 是良好
        level = service._get_health_level(6.0)
        assert level == "good"

        # 5.99 是一般
        level = service._get_health_level(5.99)
        assert level == "fair"

    def test_boundary_score_fair(self):
        """测试边界分数 - 一般"""
        service = RelationshipProgressService()

        # 刚好 4.0 是一般
        level = service._get_health_level(4.0)
        assert level == "fair"

        # 3.99 需要关注
        level = service._get_health_level(3.99)
        assert level == "needs_attention"

    def test_large_milestone_count(self):
        """测试大量里程碑"""
        service = RelationshipProgressService()

        mock_progresses = [
            MagicMock(progress_score=10)
            for _ in range(100)
        ]

        score = service._calculate_milestone_score(mock_progresses)
        # avg = 10, count_bonus = min(2, 100/5) = 2
        # (10/10) * 8 + 2 = 10
        assert score == 10.0

    def test_single_milestone(self):
        """测试单个里程碑"""
        service = RelationshipProgressService()

        mock_progress = MagicMock()
        mock_progress.progress_score = 1

        score = service._calculate_milestone_score([mock_progress])
        # avg = 1, count_bonus = min(2, 1/5) = 0.2
        # (1/10) * 8 + 0.2 = 0.8 + 0.2 = 1.0
        assert score == 1.0

    def test_zero_progress_score(self):
        """测试零进展评分"""
        service = RelationshipProgressService()

        mock_progress = MagicMock()
        mock_progress.progress_score = 0

        score = service._calculate_milestone_score([mock_progress])
        # avg = 0, count_bonus = 0.2
        # (0/10) * 8 + 0.2 = 0.2
        assert score == 0.2