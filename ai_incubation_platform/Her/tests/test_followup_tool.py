"""
跟进记录工具测试

测试 FollowupTool 的核心功能：
- 跟进记录生成
- 关系阶段管理
- 跟进建议
- 历史记录
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from agent.tools.followup_tool import FollowupTool


class TestFollowupToolConfig:
    """配置测试"""

    def test_tool_name(self):
        """测试工具名"""
        assert FollowupTool.name == "followup_record"

    def test_tool_description(self):
        """测试工具描述"""
        assert "跟进" in FollowupTool.description or "记录" in FollowupTool.description

    def test_tool_tags(self):
        """测试工具标签"""
        assert "followup" in FollowupTool.tags
        assert "tracking" in FollowupTool.tags

    def test_relationship_stages_count(self):
        """测试关系阶段数量"""
        assert len(FollowupTool.RELATIONSHIP_STAGES) == 5

    def test_relationship_stages_content(self):
        """测试关系阶段内容"""
        stages = [s["stage"] for s in FollowupTool.RELATIONSHIP_STAGES]
        assert "initial" in stages
        assert "getting_to_know" in stages
        assert "dating" in stages
        assert "exclusive" in stages
        assert "committed" in stages

    def test_followup_suggestions_exist(self):
        """测试跟进建议存在"""
        assert len(FollowupTool.FOLLOWUP_SUGGESTIONS) == 5
        assert "initial" in FollowupTool.FOLLOWUP_SUGGESTIONS
        assert "committed" in FollowupTool.FOLLOWUP_SUGGESTIONS

    def test_suggestions_per_stage(self):
        """测试每个阶段的建议数量"""
        for stage, suggestions in FollowupTool.FOLLOWUP_SUGGESTIONS.items():
            assert len(suggestions) >= 3


class TestInputSchema:
    """输入 Schema 测试"""

    def test_input_schema_type(self):
        """测试 schema 类型"""
        schema = FollowupTool.get_input_schema()
        assert schema["type"] == "object"

    def test_input_schema_required_fields(self):
        """测试必填字段"""
        schema = FollowupTool.get_input_schema()
        assert "user_id" in schema["required"]
        assert "target_user_id" in schema["required"]
        assert "action" in schema["required"]

    def test_input_schema_optional_fields(self):
        """测试可选字段"""
        schema = FollowupTool.get_input_schema()
        assert "notes" in schema["properties"]
        assert "relationship_stage" in schema["properties"]

    def test_action_enum(self):
        """测试动作枚举"""
        schema = FollowupTool.get_input_schema()
        action_enum = schema["properties"]["action"]["enum"]
        assert "message_sent" in action_enum
        assert "date_completed" in action_enum
        assert "gift_sent" in action_enum
        assert "confession" in action_enum
        assert "milestone" in action_enum

    def test_relationship_stage_enum(self):
        """测试关系阶段枚举"""
        schema = FollowupTool.get_input_schema()
        stage_enum = schema["properties"]["relationship_stage"]["enum"]
        assert "initial" in stage_enum
        assert "committed" in stage_enum


class TestHandleFollowup:
    """跟进记录处理测试"""

    def test_handle_basic_followup(self):
        """测试基本跟进记录"""
        result = FollowupTool.handle(
            user_id="user_001",
            target_user_id="user_002",
            action="message_sent"
        )

        assert result["success"] is True
        assert "record_id" in result
        assert "timestamp" in result
        assert "current_stage" in result
        assert "suggestions" in result

    def test_handle_with_notes(self):
        """测试带备注的跟进"""
        result = FollowupTool.handle(
            user_id="user_001",
            target_user_id="user_002",
            action="date_completed",
            notes="第一次约会，去了咖啡厅"
        )

        assert result["success"] is True

    def test_handle_with_relationship_stage(self):
        """测试带关系阶段的跟进"""
        result = FollowupTool.handle(
            user_id="user_001",
            target_user_id="user_002",
            action="milestone",
            relationship_stage="dating"
        )

        assert result["current_stage"] == "正式约会"

    def test_handle_initial_stage(self):
        """测试初识阶段"""
        result = FollowupTool.handle(
            user_id="user_001",
            target_user_id="user_002",
            action="message_sent",
            relationship_stage="initial"
        )

        assert result["current_stage"] == "初识阶段"
        assert len(result["suggestions"]) > 0

    def test_handle_committed_stage(self):
        """测试稳定关系阶段"""
        result = FollowupTool.handle(
            user_id="user_001",
            target_user_id="user_002",
            action="milestone",
            relationship_stage="committed"
        )

        assert result["current_stage"] == "稳定关系"

    def test_handle_suggestions_count(self):
        """测试建议数量限制"""
        result = FollowupTool.handle(
            user_id="user_001",
            target_user_id="user_002",
            action="message_sent"
        )

        # 应最多返回 3 条建议
        assert len(result["suggestions"]) <= 3

    def test_handle_without_relationship_stage(self):
        """测试不带关系阶段的跟进"""
        result = FollowupTool.handle(
            user_id="user_001",
            target_user_id="user_002",
            action="message_sent"
        )

        # 默认使用 initial 阶段
        assert result["current_stage"] == "初识阶段"


class TestGetStageName:
    """阶段名称获取测试"""

    def test_get_initial_stage_name(self):
        """测试初识阶段名称"""
        name = FollowupTool._get_stage_name("initial")
        assert name == "初识阶段"

    def test_get_dating_stage_name(self):
        """测试约会阶段名称"""
        name = FollowupTool._get_stage_name("dating")
        assert name == "正式约会"

    def test_get_committed_stage_name(self):
        """测试稳定关系阶段名称"""
        name = FollowupTool._get_stage_name("committed")
        assert name == "稳定关系"

    def test_get_unknown_stage_name(self):
        """测试未知阶段名称"""
        name = FollowupTool._get_stage_name("unknown")
        assert name == "未知阶段"


class TestFollowupHistory:
    """跟进历史测试"""

    def test_record_followup(self):
        """测试记录跟进"""
        FollowupTool._followup_history = []

        record = {
            "user_id": "user_001",
            "target_user_id": "user_002",
            "action": "message_sent",
            "timestamp": datetime.now().isoformat()
        }
        FollowupTool._record_followup(record)

        assert len(FollowupTool._followup_history) == 1

    def test_get_followup_history_as_initiator(self):
        """测试作为发起者获取历史"""
        FollowupTool._followup_history = []
        FollowupTool._record_followup({
            "user_id": "user_001",
            "target_user_id": "user_002",
            "timestamp": datetime.now().isoformat()
        })

        history = FollowupTool.get_followup_history("user_001")
        assert len(history) == 1

    def test_get_followup_history_with_target(self):
        """测试带目标用户的历史"""
        FollowupTool._followup_history = []
        FollowupTool._record_followup({
            "user_id": "user_001",
            "target_user_id": "user_002",
            "timestamp": datetime.now().isoformat()
        })
        FollowupTool._record_followup({
            "user_id": "user_001",
            "target_user_id": "user_003",
            "timestamp": datetime.now().isoformat()
        })

        history = FollowupTool.get_followup_history("user_001", "user_002")
        assert len(history) == 1

    def test_history_limit(self):
        """测试历史记录限制"""
        FollowupTool._followup_history = []

        # 添加超过 500 条记录
        for i in range(520):
            FollowupTool._record_followup({
                "user_id": f"user_{i}",
                "target_user_id": "target",
                "timestamp": datetime.now().isoformat()
            })

        # 超过500条时保留最后200条，但由于添加过程中可能触发多次清理
        # 实际保留的数量可能略多
        assert len(FollowupTool._followup_history) <= 250


class TestRelationshipProgress:
    """关系进展分析测试"""

    def test_get_progress_no_data(self):
        """测试无数据时"""
        FollowupTool._followup_history = []

        progress = FollowupTool.get_relationship_progress("user_001", "user_002")

        assert progress["status"] == "no_data"
        assert "暂无跟进记录" in progress["message"]

    def test_get_progress_with_data(self):
        """测试有数据时"""
        FollowupTool._followup_history = []
        FollowupTool._record_followup({
            "user_id": "user_001",
            "target_user_id": "user_002",
            "action": "message_sent",
            "relationship_stage": "initial",
            "timestamp": datetime.now().isoformat()
        })
        FollowupTool._record_followup({
            "user_id": "user_001",
            "target_user_id": "user_002",
            "action": "date_completed",
            "relationship_stage": "getting_to_know",
            "timestamp": datetime.now().isoformat()
        })

        progress = FollowupTool.get_relationship_progress("user_001", "user_002")

        assert progress["status"] == "active"
        assert progress["total_interactions"] == 2
        assert "last_interaction" in progress
        assert "action_distribution" in progress

    def test_get_progress_action_distribution(self):
        """测试互动类型分布"""
        FollowupTool._followup_history = []
        FollowupTool._record_followup({
            "user_id": "user_001",
            "target_user_id": "user_002",
            "action": "message_sent",
            "timestamp": datetime.now().isoformat()
        })
        FollowupTool._record_followup({
            "user_id": "user_001",
            "target_user_id": "user_002",
            "action": "message_sent",
            "timestamp": datetime.now().isoformat()
        })
        FollowupTool._record_followup({
            "user_id": "user_001",
            "target_user_id": "user_002",
            "action": "date_completed",
            "timestamp": datetime.now().isoformat()
        })

        progress = FollowupTool.get_relationship_progress("user_001", "user_002")

        assert progress["action_distribution"]["message_sent"] == 2
        assert progress["action_distribution"]["date_completed"] == 1

    def test_get_progress_current_stage(self):
        """测试当前阶段"""
        FollowupTool._followup_history = []
        FollowupTool._record_followup({
            "user_id": "user_001",
            "target_user_id": "user_002",
            "action": "milestone",
            "relationship_stage": "dating",
            "timestamp": datetime.now().isoformat()
        })

        progress = FollowupTool.get_relationship_progress("user_001", "user_002")

        assert progress["current_stage"] == "正式约会"


class TestAnalyzeTrend:
    """趋势分析测试"""

    def test_analyze_trend_insufficient_data(self):
        """测试数据不足"""
        records = [
            {"relationship_stage": "initial", "timestamp": datetime.now().isoformat()}
        ]

        trend = FollowupTool._analyze_trend(records)
        assert "数据不足" in trend

    def test_analyze_trend_progressing(self):
        """测试关系递进"""
        records = [
            {"relationship_stage": "initial", "timestamp": datetime.now().isoformat()},
            {"relationship_stage": "getting_to_know", "timestamp": datetime.now().isoformat()},
            {"relationship_stage": "dating", "timestamp": datetime.now().isoformat()},
        ]

        trend = FollowupTool._analyze_trend(records)
        assert "递进" in trend or "良好" in trend

    def test_analyze_trend_stable(self):
        """测试关系稳定"""
        records = [
            {"relationship_stage": "dating", "timestamp": datetime.now().isoformat()},
            {"relationship_stage": "dating", "timestamp": datetime.now().isoformat()},
            {"relationship_stage": "dating", "timestamp": datetime.now().isoformat()},
        ]

        trend = FollowupTool._analyze_trend(records)
        assert "稳定" in trend

    def test_analyze_trend_no_stages(self):
        """测试无阶段信息"""
        records = [
            {"action": "message_sent", "timestamp": datetime.now().isoformat()},
            {"action": "message_sent", "timestamp": datetime.now().isoformat()},
            {"action": "message_sent", "timestamp": datetime.now().isoformat()},
        ]

        trend = FollowupTool._analyze_trend(records)
        assert isinstance(trend, str)


class TestEdgeCases:
    """边界值测试"""

    def test_same_user_followup(self):
        """测试同用户跟进"""
        result = FollowupTool.handle(
            user_id="user_001",
            target_user_id="user_001",
            action="message_sent"
        )

        assert result["success"] is True

    def test_empty_notes(self):
        """测试空备注"""
        result = FollowupTool.handle(
            user_id="user_001",
            target_user_id="user_002",
            action="date_completed",
            notes=""
        )

        assert result["success"] is True

    def test_long_notes(self):
        """测试长备注"""
        long_notes = "这是一个很长的备注信息" * 100
        result = FollowupTool.handle(
            user_id="user_001",
            target_user_id="user_002",
            action="date_completed",
            notes=long_notes
        )

        assert result["success"] is True

    def test_special_characters_in_notes(self):
        """测试备注特殊字符"""
        result = FollowupTool.handle(
            user_id="user_001",
            target_user_id="user_002",
            action="date_completed",
            notes="特殊字符测试！@#$%^&*()"
        )

        assert result["success"] is True

    def test_all_actions(self):
        """测试所有动作类型"""
        actions = ["message_sent", "date_completed", "gift_sent", "confession", "milestone"]

        for action in actions:
            result = FollowupTool.handle(
                user_id="user_001",
                target_user_id="user_002",
                action=action
            )
            assert result["success"] is True