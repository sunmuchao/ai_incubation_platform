"""
约见提议工具测试

测试 DateProposalTool 的核心功能：
- 约见提议生成
- 地点类型建议
- 时间建议
- 合规校验
- 历史记录
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from agent.tools.date_proposal_tool import DateProposalTool


class TestDateProposalToolConfig:
    """配置测试"""

    def test_tool_name(self):
        """测试工具名"""
        assert DateProposalTool.name == "date_proposal"

    def test_tool_description(self):
        """测试工具描述"""
        assert "约见" in DateProposalTool.description or "提议" in DateProposalTool.description

    def test_tool_tags(self):
        """测试工具标签"""
        assert "date" in DateProposalTool.tags
        assert "proposal" in DateProposalTool.tags

    def test_location_types_count(self):
        """测试地点类型数量"""
        assert len(DateProposalTool.DATE_LOCATION_TYPES) >= 5

    def test_location_types_content(self):
        """测试地点类型内容"""
        assert "咖啡厅" in DateProposalTool.DATE_LOCATION_TYPES
        assert "餐厅" in DateProposalTool.DATE_LOCATION_TYPES
        assert "公园" in DateProposalTool.DATE_LOCATION_TYPES

    def test_activities_config(self):
        """测试活动配置"""
        assert "咖啡厅" in DateProposalTool.DATE_ACTIVITIES
        assert len(DateProposalTool.DATE_ACTIVITIES["咖啡厅"]) >= 1

    def test_activities_for_all_location_types(self):
        """测试每个地点类型都有活动"""
        for location_type in DateProposalTool.DATE_LOCATION_TYPES:
            activities = DateProposalTool.DATE_ACTIVITIES.get(location_type, [])
            assert len(activities) >= 1


class TestInputSchema:
    """输入 Schema 测试"""

    def test_input_schema_type(self):
        """测试 schema 类型"""
        schema = DateProposalTool.get_input_schema()
        assert schema["type"] == "object"

    def test_input_schema_required_fields(self):
        """测试必填字段"""
        schema = DateProposalTool.get_input_schema()
        assert "user_id" in schema["required"]
        assert "target_user_id" in schema["required"]

    def test_input_schema_optional_fields(self):
        """测试可选字段"""
        schema = DateProposalTool.get_input_schema()
        assert "location_type" in schema["properties"]
        assert "preferred_time" in schema["properties"]
        assert "custom_message" in schema["properties"]

    def test_location_type_enum(self):
        """测试地点类型枚举"""
        schema = DateProposalTool.get_input_schema()
        location_enum = schema["properties"]["location_type"]["enum"]
        assert "咖啡厅" in location_enum
        assert len(location_enum) >= 5


class TestHandleDateProposal:
    """约见提议处理测试"""

    def test_handle_basic_proposal(self):
        """测试基本约见提议"""
        result = DateProposalTool.handle(
            user_id="user_001",
            target_user_id="user_002"
        )

        assert "proposal_id" in result
        assert "status" in result
        assert result["compliance_passed"] is True

    def test_handle_with_location_type(self):
        """测试带地点类型的提议"""
        result = DateProposalTool.handle(
            user_id="user_001",
            target_user_id="user_002",
            location_type="咖啡厅"
        )

        assert result["location_type"] == "咖啡厅"
        assert "suggested_activities" in result

    def test_handle_with_preferred_time(self):
        """测试带期望时间的提议"""
        result = DateProposalTool.handle(
            user_id="user_001",
            target_user_id="user_002",
            preferred_time="周六下午3点"
        )

        assert result["preferred_time"] == "周六下午3点"

    def test_handle_without_location_type(self):
        """测试不带地点类型的提议"""
        result = DateProposalTool.handle(
            user_id="user_001",
            target_user_id="user_002"
        )

        # 应提供默认地点建议
        assert "suggested_location_types" in result
        assert len(result["suggested_location_types"]) >= 1

    def test_handle_without_preferred_time(self):
        """测试不带期望时间的提议"""
        result = DateProposalTool.handle(
            user_id="user_001",
            target_user_id="user_002"
        )

        # 应提供时间建议
        assert "suggested_times" in result
        assert len(result["suggested_times"]) >= 1

    def test_handle_with_custom_message(self):
        """测试带自定义消息的提议"""
        result = DateProposalTool.handle(
            user_id="user_001",
            target_user_id="user_002",
            custom_message="想请你喝咖啡"
        )

        assert "message" in result
        assert result["compliance_passed"] is True

    def test_handle_with_inappropriate_message(self):
        """测试不当消息被拦截"""
        result = DateProposalTool.handle(
            user_id="user_001",
            target_user_id="user_002",
            custom_message="这里有赌博"
        )

        assert result["compliance_passed"] is False
        assert len(result["issues"]) > 0

    def test_handle_proposal_id_format(self):
        """测试提议 ID 格式"""
        result = DateProposalTool.handle(
            user_id="user_001",
            target_user_id="user_002"
        )

        assert result["proposal_id"].startswith("dp_")
        assert "user_001" in result["proposal_id"]
        assert "user_002" in result["proposal_id"]


class TestSuggestedTimes:
    """时间建议测试"""

    def test_get_suggested_times(self):
        """测试获取时间建议"""
        times = DateProposalTool._get_suggested_times()

        assert len(times) >= 3
        assert any("周六" in t or "周日" in t for t in times)
        assert any("工作日" in t or "晚上" in t for t in times)

    def test_suggested_times_format(self):
        """测试时间建议格式"""
        times = DateProposalTool._get_suggested_times()

        for time in times:
            assert isinstance(time, str)
            assert len(time) > 0


class TestDefaultMessage:
    """默认消息测试"""

    def test_generate_default_message_cafe(self):
        """测试咖啡厅消息"""
        message = DateProposalTool._generate_default_message("咖啡厅", "周六下午")

        assert "咖啡厅" in message or "咖啡" in message
        assert "周六下午" in message

    def test_generate_default_message_restaurant(self):
        """测试餐厅消息"""
        message = DateProposalTool._generate_default_message("餐厅", "周末晚上")

        assert "餐厅" in message

    def test_generate_default_message_park(self):
        """测试公园消息"""
        message = DateProposalTool._generate_default_message("公园", "周日")

        assert "公园" in message

    def test_generate_default_message_unknown_location(self):
        """测试未知地点消息"""
        message = DateProposalTool._generate_default_message("未知地点", "周末")

        # 应有默认消息
        assert len(message) > 0

    def test_default_message_is_polite(self):
        """测试默认消息礼貌性"""
        message = DateProposalTool._generate_default_message("咖啡厅", "周六下午")

        # 应包含礼貌用语
        assert "邀请" in message or "一起" in message or "有空" in message


class TestProposalHistory:
    """提议历史测试"""

    def test_record_proposal(self):
        """测试记录提议"""
        # 清空历史
        DateProposalTool._proposal_history = []

        proposal = {
            "user_id": "user_001",
            "target_user_id": "user_002",
            "timestamp": datetime.now().isoformat(),
            "location_type": "咖啡厅",
            "status": "draft"
        }
        DateProposalTool._record_proposal(proposal)

        assert len(DateProposalTool._proposal_history) == 1
        assert DateProposalTool._proposal_history[0] == proposal

    def test_get_proposal_history_as_initiator(self):
        """测试作为发起者获取历史"""
        DateProposalTool._proposal_history = []
        DateProposalTool._record_proposal({
            "user_id": "user_001",
            "target_user_id": "user_002",
            "timestamp": datetime.now().isoformat()
        })

        history = DateProposalTool.get_proposal_history("user_001")

        assert len(history) == 1

    def test_get_proposal_history_as_target(self):
        """测试作为目标获取历史"""
        DateProposalTool._proposal_history = []
        DateProposalTool._record_proposal({
            "user_id": "user_001",
            "target_user_id": "user_002",
            "timestamp": datetime.now().isoformat()
        })

        history = DateProposalTool.get_proposal_history("user_002")

        assert len(history) == 1

    def test_history_limit(self):
        """测试历史记录限制"""
        DateProposalTool._proposal_history = []

        # 添加超过 100 条记录
        for i in range(110):
            DateProposalTool._record_proposal({
                "user_id": f"user_{i}",
                "target_user_id": "target",
                "timestamp": datetime.now().isoformat()
            })

        # 实现逻辑：超过100条时保留最后50条
        # 但由于是在添加时检查，可能略有差异
        assert len(DateProposalTool._proposal_history) <= 60

    def test_restaurant_activities(self):
        """测试餐厅活动"""
        activities = DateProposalTool.DATE_ACTIVITIES.get("餐厅", [])
        # 活动是 "共进晚餐", "美食探索", "DIY 料理"
        assert "共进晚餐" in activities or "美食探索" in activities

    def test_park_activities(self):
        """测试公园活动"""
        activities = DateProposalTool.DATE_ACTIVITIES.get("公园", [])
        assert "散步" in activities or "野餐" in activities


class TestEdgeCases:
    """边界值测试"""

    def test_same_user_proposal(self):
        """测试同用户提议"""
        result = DateProposalTool.handle(
            user_id="user_001",
            target_user_id="user_001"
        )

        # 应能处理（虽然不合理）
        assert "proposal_id" in result

    def test_empty_custom_message(self):
        """测试空自定义消息"""
        result = DateProposalTool.handle(
            user_id="user_001",
            target_user_id="user_002",
            custom_message=""
        )

        # 空消息应使用默认
        assert "message" in result

    def test_long_custom_message(self):
        """测试长自定义消息"""
        long_message = "这是一个很长的消息" * 100
        result = DateProposalTool.handle(
            user_id="user_001",
            target_user_id="user_002",
            custom_message=long_message
        )

        assert "message" in result

    def test_special_characters_in_message(self):
        """测试消息特殊字符"""
        result = DateProposalTool.handle(
            user_id="user_001",
            target_user_id="user_002",
            custom_message="你好！@#$%^&*()"
        )

        assert "message" in result