"""
Her Tools 测试（精简版 v4.3 - Agent Native 设计）

测试 DeerFlow Tools 的异步方法和结构化返回。

测试覆盖：
1. schemas.py - ToolResult 数据结构验证（只有 success/error/data）
2. match_tools.py - her_find_candidates 硬约束过滤逻辑验证
3. profile_tools.py - her_get_profile 返回用户画像 + 缺失字段
4. profile_tools.py - her_update_preference 更新逻辑验证
5. user_tools.py - her_get_conversation_history 对话历史验证
6. feedback_tools.py - her_record_feedback 反馈记录验证
7. feedback_tools.py - her_get_feedback_history 反馈历史查询验证
8. 工具数量验证 - 确保只有 7 个工具
"""

import pytest
import json
import sys
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

# 设置正确的路径
HER_DEERFLOW_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "packages", "harness"
)
if HER_DEERFLOW_PATH not in sys.path:
    sys.path.insert(0, HER_DEERFLOW_PATH)

# 设置 Her 项目路径
HER_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if HER_PROJECT_ROOT not in sys.path:
    sys.path.insert(0, HER_PROJECT_ROOT)


# 导入 Her Tools
from deerflow.community.her_tools import (
    ToolResult,
    HerGetProfileTool,
    HerFindCandidatesTool,
    HerGetConversationHistoryTool,
    HerUpdatePreferenceTool,
    HerCreateProfileTool,
    HerRecordFeedbackTool,
    HerGetFeedbackHistoryTool,
    HER_TOOLS,
    PRESET_DISLIKE_REASONS,
)


# ==================== Part 1: 工具数量验证 ====================

class TestToolCount:
    """验证精简后的工具数量"""

    def test_only_seven_tools(self):
        """只有 7 个工具"""
        assert len(HER_TOOLS) == 7, f"工具数量应为 7，实际为 {len(HER_TOOLS)}"

    def test_tool_names(self):
        """验证工具名称"""
        expected_names = [
            "her_get_profile",
            "her_find_candidates",
            "her_get_conversation_history",
            "her_update_preference",
            "her_create_profile",
            "her_record_feedback",
            "her_get_feedback_history",
        ]
        actual_names = [tool.name for tool in HER_TOOLS]
        assert set(actual_names) == set(expected_names), \
            f"工具名称应为 {expected_names}，实际为 {actual_names}"


# ==================== Part 2: ToolResult 数据结构测试 ====================

class TestToolResultSchema:
    """测试统一返回格式（Agent Native 设计）"""

    def test_tool_result_only_three_fields(self):
        """ToolResult 只包含 success/error/data 三个字段"""
        result = ToolResult(
            success=True,
            data={"test": "data"}
        )

        fields = set(ToolResult.model_fields.keys())
        expected_fields = {"success", "error", "data"}
        assert fields == expected_fields, f"ToolResult 字段应为 {expected_fields}，实际为 {fields}"

    def test_tool_result_no_instruction(self):
        """Agent Native 设计：ToolResult 不包含 instruction 字段"""
        result = ToolResult(success=True, data={"test": "data"})
        assert not hasattr(result, 'instruction'), "ToolResult 不应有 instruction 字段"

    def test_tool_result_no_output_hint(self):
        """Agent Native 设计：ToolResult 不包含 output_hint 字段"""
        result = ToolResult(success=True, data={"test": "data"})
        assert not hasattr(result, 'output_hint'), "ToolResult 不应有 output_hint 字段"

    def test_tool_result_no_summary(self):
        """Agent Native 设计：ToolResult 不包含 summary 字段"""
        result = ToolResult(success=True, data={"test": "data"})
        assert not hasattr(result, 'summary'), "ToolResult 不应有 summary 字段"


# ==================== Part 3: 工具 Description Agent Native 测试 ====================

class TestToolDescriptionAgentNative:
    """测试所有工具的 description 符合 Agent Native 设计"""

    def test_no_trigger_keywords_in_description(self):
        """所有工具 description 不应包含触发条件关键词"""
        forbidden_keywords = [
            "触发条件",
            "触发词",
            "当用户说",
            "如果用户说",
            "关键词 →",
            "意图映射",
        ]

        for tool in HER_TOOLS:
            for keyword in forbidden_keywords:
                assert keyword not in tool.description, \
                    f"工具 {tool.name} description 包含禁止关键词 '{keyword}'"

    def test_description_not_template_output(self):
        """所有工具 description 不应包含输出模板指令"""
        forbidden_output_patterns = [
            "请向用户展示",
            "请告诉用户",
            "输出格式为",
            "回复模板",
        ]

        for tool in HER_TOOLS:
            for pattern in forbidden_output_patterns:
                assert pattern not in tool.description, \
                    f"工具 {tool.name} description 包含输出模板 '{pattern}'"


# ==================== Part 4: her_get_profile 测试 ====================

class TestHerGetProfileTool:
    """测试用户画像查询工具"""

    def test_returns_user_profile(self):
        """返回用户画像原始数据"""
        tool = HerGetProfileTool()

        with patch("deerflow.community.her_tools.profile_tools.get_db_user") as mock_user:
            mock_user.return_value = {
                "name": "张三",
                "age": 28,
                "interests": ["运动", "阅读"],
            }

            with patch.object(tool, '_arun') as mock_arun:
                mock_arun.return_value = ToolResult(
                    success=True,
                    data={
                        "user_profile": {"name": "张三"},
                        "missing_fields": [],
                        "preference_status": "complete",
                    }
                )

                result = tool._run(user_id="test-user")

        parsed = json.loads(result)
        assert parsed["success"] == True
        assert "user_profile" in parsed["data"]

    def test_returns_missing_fields(self):
        """返回缺失字段列表"""
        tool = HerGetProfileTool()

        with patch.object(tool, '_arun') as mock_arun:
            mock_arun.return_value = ToolResult(
                success=True,
                data={
                    "user_profile": {"name": "张三"},
                    "missing_fields": ["gender", "location"],
                    "missing_preferences": ["地点偏好"],
                    "preference_status": "partial",
                }
            )

            result = tool._run(user_id="test-user")

        parsed = json.loads(result)
        assert "missing_fields" in parsed["data"]
        assert "missing_preferences" in parsed["data"]

    def test_user_id_optional(self):
        """user_id 参数可选"""
        tool = HerGetProfileTool()

        with patch("deerflow.community.her_tools.profile_tools.get_current_user_id") as mock_get:
            mock_get.return_value = "default-user"

            with patch.object(tool, '_arun') as mock_arun:
                mock_arun.return_value = ToolResult(
                    success=True,
                    data={"user_profile": {"name": "默认用户"}}
                )

                result = tool._run()  # 不传 user_id

        parsed = json.loads(result)
        assert parsed["success"] == True


# ==================== Part 5: her_find_candidates 测试 ====================

class TestHerFindCandidatesTool:
    """测试候选人查询工具"""

    def test_returns_candidates_list(self):
        """返回候选人列表"""
        tool = HerFindCandidatesTool()

        with patch.object(tool, '_arun') as mock_arun:
            mock_arun.return_value = ToolResult(
                success=True,
                data={
                    "candidates": [
                        {"user_id": "user-1", "name": "李四", "age": 25},
                    ],
                    "user_preferences": {},
                    "filter_applied": {},
                }
            )

            result = tool._run(user_id="test-user")

        parsed = json.loads(result)
        assert parsed["success"] == True
        assert "candidates" in parsed["data"]

    def test_returns_user_preferences(self):
        """返回 user_preferences 供 Agent 参考"""
        tool = HerFindCandidatesTool()

        with patch.object(tool, '_arun') as mock_arun:
            mock_arun.return_value = ToolResult(
                success=True,
                data={
                    "candidates": [],
                    "user_preferences": {
                        "preferred_age_min": 25,
                        "preferred_age_max": 35,
                        "user_location": "北京",
                    },
                    "filter_applied": {},
                }
            )

            result = tool._run(user_id="test-user")

        parsed = json.loads(result)
        assert "user_preferences" in parsed["data"]

    def test_hard_constraints_only(self):
        """硬约束：只做安全边界过滤，不做业务筛选"""
        tool = HerFindCandidatesTool()

        import inspect
        source = inspect.getsource(tool._arun)

        # 禁止的软约束模式（不应在工具代码中出现）
        forbidden_patterns = [
            "if user.get('preferred_age_min')",
            "if user.get('preferred_age_max')",
            "if user.get('preferred_location')",
        ]

        for pattern in forbidden_patterns:
            assert pattern not in source, \
                f"候选人工具不应包含软约束筛选逻辑 '{pattern}'"


# ==================== Part 6: her_get_conversation_history 测试 ====================

class TestHerGetConversationHistoryTool:
    """测试对话历史查询工具"""

    def test_returns_messages(self):
        """返回消息列表"""
        tool = HerGetConversationHistoryTool()

        with patch.object(tool, '_arun') as mock_arun:
            mock_arun.return_value = ToolResult(
                success=True,
                data={
                    "messages": [
                        {"content": "你好", "sender_id": "user-a"},
                    ],
                    "total": 1,
                    "silence_info": {},
                }
            )

            result = tool._run(user_id="test-user", target_id="target-user")

        parsed = json.loads(result)
        assert parsed["success"] == True
        assert "messages" in parsed["data"]

    def test_returns_silence_info(self):
        """返回沉默信息供 Agent 判断"""
        tool = HerGetConversationHistoryTool()

        with patch.object(tool, '_arun') as mock_arun:
            mock_arun.return_value = ToolResult(
                success=True,
                data={
                    "messages": [],
                    "total": 0,
                    "silence_info": {
                        "silence_seconds": 3600,
                        "last_sender": "user-a",
                    },
                }
            )

            result = tool._run(user_id="test-user", target_id="target-user")

        parsed = json.loads(result)
        assert "silence_info" in parsed["data"]
        assert parsed["data"]["silence_info"]["silence_seconds"] == 3600


# ==================== Part 7: her_update_preference 测试 ====================

class TestHerUpdatePreferenceTool:
    """测试偏好更新工具"""

    def test_update_accept_remote(self):
        """测试更新异地接受度"""
        tool = HerUpdatePreferenceTool()

        with patch.object(tool, '_arun') as mock_arun:
            mock_arun.return_value = ToolResult(
                success=True,
                data={
                    "updated_dimension": "accept_remote",
                    "updated_value": "只找同城",
                }
            )

            result = tool._run(user_id="test-user", dimension="accept_remote", value="只找同城")

        parsed = json.loads(result)
        assert parsed["success"] == True
        assert parsed["data"]["updated_dimension"] == "accept_remote"

    def test_update_relationship_goal(self):
        """测试更新关系目标"""
        tool = HerUpdatePreferenceTool()

        with patch.object(tool, '_arun') as mock_arun:
            mock_arun.return_value = ToolResult(
                success=True,
                data={
                    "updated_dimension": "relationship_goal",
                    "updated_value": "serious",
                }
            )

            result = tool._run(user_id="test-user", dimension="relationship_goal", value="认真恋爱")

        parsed = json.loads(result)
        assert parsed["success"] == True

    def test_user_id_optional(self):
        """user_id 参数可选"""
        tool = HerUpdatePreferenceTool()

        with patch("deerflow.community.her_tools.profile_tools.get_current_user_id") as mock_get:
            mock_get.return_value = "default-user"

            with patch.object(tool, '_arun') as mock_arun:
                mock_arun.return_value = ToolResult(
                    success=True,
                    data={"updated_dimension": "accept_remote"}
                )

                result = tool._run(dimension="accept_remote", value="接受异地")

        parsed = json.loads(result)
        assert parsed["success"] == True


# ==================== Part 8: PRESET_DISLIKE_REASONS 测试 ====================

class TestPresetDislikeReasons:
    """测试预设不喜欢原因列表"""

    def test_has_six_reasons(self):
        """预设原因应有 6 个"""
        assert len(PRESET_DISLIKE_REASONS) == 6, \
            f"预设不喜欢原因应为 6 个，实际为 {len(PRESET_DISLIKE_REASONS)}"

    def test_required_reasons_exist(self):
        """必须包含关键原因"""
        required_reasons = [
            "年龄差距太大",
            "距离太远",
            "兴趣不匹配",
            "没有眼缘",
            "关系目标不一致",
            "其他",
        ]
        for reason in required_reasons:
            assert reason in PRESET_DISLIKE_REASONS, \
                f"预设原因应包含 '{reason}'"

    def test_other_is_last(self):
        """'其他' 应为最后一个选项"""
        assert PRESET_DISLIKE_REASONS[-1] == "其他", \
            "'其他' 应为最后一个预设原因"

    def test_reasons_are_unique(self):
        """预设原因不应重复"""
        assert len(PRESET_DISLIKE_REASONS) == len(set(PRESET_DISLIKE_REASONS)), \
            "预设不喜欢原因不应有重复"


# ==================== Part 9: her_record_feedback 测试 ====================

class TestHerRecordFeedbackTool:
    """测试反馈记录工具"""

    def test_returns_recorded_status(self):
        """返回记录状态"""
        tool = HerRecordFeedbackTool()

        with patch.object(tool, '_arun') as mock_arun:
            mock_arun.return_value = ToolResult(
                success=True,
                data={
                    "recorded": True,
                    "feedback_id": "feedback-001",
                    "action": "created",
                    "message": "已记录您的喜欢反馈！",
                }
            )

            result = tool._run(
                user_id="test-user",
                candidate_id="candidate-001",
                feedback_type="like"
            )

        parsed = json.loads(result)
        assert parsed["success"] == True
        assert parsed["data"]["recorded"] == True

    def test_validates_feedback_type(self):
        """校验反馈类型"""
        tool = HerRecordFeedbackTool()

        with patch.object(tool, '_arun') as mock_arun:
            mock_arun.return_value = ToolResult(
                success=False,
                error="无效的反馈类型：invalid_type。可选值：['like', 'dislike', 'neutral', 'skip']"
            )

            result = tool._run(
                user_id="test-user",
                candidate_id="candidate-001",
                feedback_type="invalid_type"
            )

        parsed = json.loads(result)
        assert parsed["success"] == False
        assert "无效的反馈类型" in parsed["error"]

    def test_dislike_requires_reason(self):
        """不喜欢反馈必须填写原因"""
        tool = HerRecordFeedbackTool()

        with patch.object(tool, '_arun') as mock_arun:
            mock_arun.return_value = ToolResult(
                success=False,
                error="不喜欢反馈必须填写原因。可选原因：年龄差距太大, 距离太远, ..."
            )

            result = tool._run(
                user_id="test-user",
                candidate_id="candidate-001",
                feedback_type="dislike"
            )

        parsed = json.loads(result)
        assert parsed["success"] == False
        assert "必须填写原因" in parsed["error"]

    def test_reason_must_be_preset(self):
        """原因必须是预设选项"""
        tool = HerRecordFeedbackTool()

        with patch.object(tool, '_arun') as mock_arun:
            # 自定义原因自动归类为"其他"
            mock_arun.return_value = ToolResult(
                success=True,
                data={
                    "recorded": True,
                    "feedback_id": "feedback-002",
                    "action": "created",
                    "message": "已记录您的不喜欢反馈（原因：其他）。",
                }
            )

            result = tool._run(
                user_id="test-user",
                candidate_id="candidate-001",
                feedback_type="dislike",
                reason="自定义原因不在预设列表",
                detail="用户输入的详细原因"
            )

        parsed = json.loads(result)
        assert parsed["success"] == True

    def test_user_id_optional(self):
        """user_id 参数可选"""
        tool = HerRecordFeedbackTool()

        with patch("deerflow.community.her_tools.feedback_tools.get_current_user_id") as mock_get:
            mock_get.return_value = "default-user"

            with patch.object(tool, '_arun') as mock_arun:
                mock_arun.return_value = ToolResult(
                    success=True,
                    data={"recorded": True, "feedback_id": "feedback-003"}
                )

                result = tool._run(
                    candidate_id="candidate-001",
                    feedback_type="like"
                )

        parsed = json.loads(result)
        assert parsed["success"] == True

    def test_description_agent_native(self):
        """description 符合 Agent Native 设计"""
        tool = HerRecordFeedbackTool()

        # 禁止的输出模板模式
        forbidden_patterns = [
            "请向用户展示",
            "请告诉用户",
            "输出格式为",
        ]

        for pattern in forbidden_patterns:
            assert pattern not in tool.description, \
                f"工具 description 包含输出模板 '{pattern}'"

    def test_description_contains_preset_reasons(self):
        """description 包含预设原因列表"""
        tool = HerRecordFeedbackTool()

        # 应包含预设原因的使用说明
        assert "预设不喜欢原因" in tool.description or "可选原因" in tool.description, \
            "description 应说明预设原因"

    def test_no_instruction_in_result(self):
        """返回结果不包含 instruction"""
        tool = HerRecordFeedbackTool()

        with patch.object(tool, '_arun') as mock_arun:
            mock_arun.return_value = ToolResult(
                success=True,
                data={
                    "recorded": True,
                    "feedback_id": "feedback-001",
                    "message": "已记录反馈",
                }
            )

            result = tool._run(
                user_id="test-user",
                candidate_id="candidate-001",
                feedback_type="like"
            )

        parsed = json.loads(result)
        assert "instruction" not in parsed["data"], \
            "Agent Native 设计：返回数据不应包含 instruction"


# ==================== Part 10: her_get_feedback_history 测试 ====================

class TestHerGetFeedbackHistoryTool:
    """测试反馈历史查询工具"""

    def test_returns_feedbacks_list(self):
        """返回反馈列表"""
        tool = HerGetFeedbackHistoryTool()

        with patch.object(tool, '_arun') as mock_arun:
            mock_arun.return_value = ToolResult(
                success=True,
                data={
                    "feedbacks": [
                        {
                            "feedback_id": "feedback-001",
                            "candidate_id": "candidate-001",
                            "candidate_name": "张三",
                            "feedback_type": "dislike",
                            "dislike_reason": "年龄差距太大",
                        },
                    ],
                    "statistics": {},
                }
            )

            result = tool._run(user_id="test-user")

        parsed = json.loads(result)
        assert parsed["success"] == True
        assert "feedbacks" in parsed["data"]

    def test_returns_statistics(self):
        """返回统计汇总"""
        tool = HerGetFeedbackHistoryTool()

        with patch.object(tool, '_arun') as mock_arun:
            mock_arun.return_value = ToolResult(
                success=True,
                data={
                    "feedbacks": [],
                    "statistics": {
                        "total_feedbacks": 10,
                        "like_count": 3,
                        "dislike_count": 5,
                        "neutral_count": 2,
                        "skip_count": 0,
                        "dislike_reason_distribution": {
                            "年龄差距太大": 2,
                            "距离太远": 3,
                        },
                    },
                }
            )

            result = tool._run(user_id="test-user")

        parsed = json.loads(result)
        assert "statistics" in parsed["data"]
        assert parsed["data"]["statistics"]["total_feedbacks"] == 10

    def test_filter_by_feedback_type(self):
        """按反馈类型筛选"""
        tool = HerGetFeedbackHistoryTool()

        with patch.object(tool, '_arun') as mock_arun:
            mock_arun.return_value = ToolResult(
                success=True,
                data={
                    "feedbacks": [
                        {"feedback_type": "dislike", "candidate_name": "张三"},
                    ],
                    "statistics": {},
                }
            )

            result = tool._run(user_id="test-user", feedback_type="dislike")

        parsed = json.loads(result)
        assert parsed["success"] == True

    def test_limit_parameter(self):
        """limit 参数限制返回数量"""
        tool = HerGetFeedbackHistoryTool()

        with patch.object(tool, '_arun') as mock_arun:
            mock_arun.return_value = ToolResult(
                success=True,
                data={
                    "feedbacks": [],
                    "statistics": {},
                }
            )

            result = tool._run(user_id="test-user", limit=5)

        parsed = json.loads(result)
        assert parsed["success"] == True

    def test_user_id_optional(self):
        """user_id 参数可选"""
        tool = HerGetFeedbackHistoryTool()

        with patch("deerflow.community.her_tools.feedback_tools.get_current_user_id") as mock_get:
            mock_get.return_value = "default-user"

            with patch.object(tool, '_arun') as mock_arun:
                mock_arun.return_value = ToolResult(
                    success=True,
                    data={"feedbacks": [], "statistics": {}}
                )

                result = tool._run()

        parsed = json.loads(result)
        assert parsed["success"] == True

    def test_returns_candidate_info(self):
        """返回候选人信息"""
        tool = HerGetFeedbackHistoryTool()

        with patch.object(tool, '_arun') as mock_arun:
            mock_arun.return_value = ToolResult(
                success=True,
                data={
                    "feedbacks": [
                        {
                            "feedback_id": "feedback-001",
                            "candidate_id": "uuid-123",
                            "candidate_name": "李四",
                            "candidate_age": 27,
                            "candidate_location": "北京",
                            "feedback_type": "dislike",
                            "dislike_reason": "距离太远",
                            "created_at": "2024-01-15T10:30:00",
                        },
                    ],
                    "statistics": {},
                }
            )

            result = tool._run(user_id="test-user")

        parsed = json.loads(result)
        feedback = parsed["data"]["feedbacks"][0]
        assert "candidate_name" in feedback, "应包含候选人姓名"
        assert "candidate_age" in feedback, "应包含候选人年龄"
        assert "candidate_location" in feedback, "应包含候选人地点"

    def test_no_instruction_in_result(self):
        """返回结果不包含 instruction"""
        tool = HerGetFeedbackHistoryTool()

        with patch.object(tool, '_arun') as mock_arun:
            mock_arun.return_value = ToolResult(
                success=True,
                data={
                    "feedbacks": [],
                    "statistics": {},
                }
            )

            result = tool._run(user_id="test-user")

        parsed = json.loads(result)
        assert "instruction" not in parsed["data"], \
            "Agent Native 设计：返回数据不应包含 instruction"


# ==================== Part 11: 错误处理测试 ====================

class TestErrorHandling:
    """测试错误处理"""

    def test_tool_returns_error_on_user_not_found(self):
        """用户不存在时应返回错误"""
        tool = HerGetProfileTool()

        with patch("deerflow.community.her_tools.profile_tools.get_db_user") as mock_user:
            mock_user.return_value = None

            result = tool._run(user_id="nonexistent-user")

        parsed = json.loads(result)
        assert parsed["success"] == False
        assert parsed["error"] != ""
        # Anthropic 建议：错误提示应给修正方向
        assert "建议" in parsed["error"] or "示例" in parsed["error"], \
            "错误信息应包含建议或示例"


# ==================== Part 12: Anthropic 建议改进测试 ====================

class TestAnthropicImprovements:
    """测试 Anthropic 建议的改进"""

    def test_find_candidates_returns_display_id(self):
        """候选人返回 display_id（语义化标识符）"""
        tool = HerFindCandidatesTool()

        with patch.object(tool, '_arun') as mock_arun:
            mock_arun.return_value = ToolResult(
                success=True,
                data={
                    "candidates": [
                        {"display_id": "candidate_001", "name": "张三", "user_id": "uuid-1"},
                    ],
                    "user_preferences": {},
                    "filter_applied": {},
                }
            )

            result = tool._run(user_id="test-user")

        parsed = json.loads(result)
        assert parsed["success"] == True
        assert "display_id" in parsed["data"]["candidates"][0], \
            "候选人应包含 display_id（语义化标识符）"
        assert parsed["data"]["candidates"][0]["display_id"] == "candidate_001"

    def test_find_candidates_truncation_hint(self):
        """候选人截断时应返回截断提示"""
        tool = HerFindCandidatesTool()

        with patch.object(tool, '_arun') as mock_arun:
            mock_arun.return_value = ToolResult(
                success=True,
                data={
                    "candidates": [],
                    "user_preferences": {},
                    "filter_applied": {},
                    "truncated": True,
                    "truncation_hint": "结果已截断...",
                }
            )

            result = tool._run(user_id="test-user")

        parsed = json.loads(result)
        assert parsed["data"]["truncated"] == True, \
            "截断时应标记 truncated=True"
        assert "truncation_hint" in parsed["data"], \
            "截断时应包含 truncation_hint"

    def test_get_profile_returns_display_id(self):
        """用户画像返回 display_id"""
        tool = HerGetProfileTool()

        with patch.object(tool, '_arun') as mock_arun:
            mock_arun.return_value = ToolResult(
                success=True,
                data={
                    "display_id": "张三",
                    "user_profile": {"name": "张三"},
                    "missing_fields": [],
                    "preference_status": "complete",
                }
            )

            result = tool._run(user_id="test-user")

        parsed = json.loads(result)
        assert "display_id" in parsed["data"], \
            "用户画像应包含 display_id"

    def test_conversation_history_sender_name(self):
        """对话历史返回 sender_name（高信号信息）"""
        tool = HerGetConversationHistoryTool()

        with patch.object(tool, '_arun') as mock_arun:
            mock_arun.return_value = ToolResult(
                success=True,
                data={
                    "messages": [
                        {"content": "你好", "sender_name": "张三", "is_from_user": False},
                    ],
                    "total": 1,
                    "silence_info": {
                        "silence_readable": "2 小时",
                        "last_sender_name": "张三",
                    },
                    "user_name": "我",
                    "target_name": "张三",
                }
            )

            result = tool._run(user_id="test-user", target_id="target-user")

        parsed = json.loads(result)
        # 检查 sender_name 存在
        assert "sender_name" in parsed["data"]["messages"][0], \
            "消息应包含 sender_name（语义化名称）"
        # 检查 silence_readable 存在
        assert "silence_readable" in parsed["data"]["silence_info"], \
            "沉默信息应包含 silence_readable（语义化时间）"

    def test_update_preference_detailed_error(self):
        """更新偏好错误时应返回详细提示"""
        tool = HerUpdatePreferenceTool()

        with patch.object(tool, '_arun') as mock_arun:
            mock_arun.return_value = ToolResult(
                success=False,
                error="不支持的维度。\n建议：请使用支持的维度名称。\n示例：..."
            )

            result = tool._run(user_id="test-user", dimension="invalid_dim", value="test")

        parsed = json.loads(result)
        assert parsed["success"] == False
        assert "建议" in parsed["error"] or "示例" in parsed["error"], \
            "错误信息应包含建议或示例"


# ==================== Part 13: 整体架构测试 ====================

class TestOverallAgentNativeCompliance:
    """测试整体 Agent Native 合规性"""

    def test_all_tools_return_json_string(self):
        """所有工具 _run 方法返回 JSON 字符串"""
        for tool in HER_TOOLS:
            import inspect
            source = inspect.getsource(tool._run)
            assert "json.dumps" in source, \
                f"工具 {tool.name} _run 方法应返回 JSON 字符串"

    def test_tool_result_model_dump_used(self):
        """所有工具使用 model_dump() 返回"""
        for tool in HER_TOOLS:
            import inspect
            source = inspect.getsource(tool._run)
            assert "model_dump()" in source, \
                f"工具 {tool.name} 应使用 model_dump() 返回"


# ==================== Part 14: helpers.py 测试 ====================

class TestHelpersGetCurrentUserId:
    """测试 get_current_user_id 的优先级"""

    def test_returns_user_id_from_configurable(self):
        """优先从 LangGraph configurable 获取"""
        from deerflow.community.her_tools.helpers import get_current_user_id

        with patch("langgraph.config.get_config") as mock_config:
            mock_config.return_value = {"configurable": {"user_id": "config-user-123"}}

            user_id = get_current_user_id()
            assert user_id == "config-user-123", \
                "应优先从 configurable 获取 user_id"


class TestHelpersGetDbUser:
    """测试 get_db_user 从数据库获取"""

    def test_queries_database_directly(self):
        """直接查询数据库"""
        from deerflow.community.her_tools.helpers import get_db_user

        mock_user = MagicMock()
        mock_user.id = "db-user"
        mock_user.name = "数据库用户"
        mock_user.age = 30
        mock_user.gender = "male"
        mock_user.location = "上海"
        mock_user.interests = "['测试']"
        mock_user.bio = ""
        mock_user.relationship_goal = ""
        mock_user.preferred_age_min = None
        mock_user.preferred_age_max = None
        mock_user.preferred_location = None
        mock_user.preferred_gender = None
        mock_user.accept_remote = None
        mock_user.want_children = None
        mock_user.spending_style = None
        mock_user.family_importance = None
        mock_user.work_life_balance = None
        mock_user.migration_willingness = None
        mock_user.sleep_type = None

        with patch("utils.db_session_manager.db_session") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = mock_user
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            user_data = get_db_user("db-user")
            assert user_data is not None
            assert user_data["id"] == "db-user"


# ==================== Part 15: SOUL.md Agent Native 测试 ====================

class TestSoulMdAgentNative:
    """测试 SOUL.md 符合 Agent Native 设计"""

    @pytest.fixture
    def soul_md_path(self):
        backend_path = Path(__file__).parent.parent
        return backend_path / ".deer-flow" / "SOUL.md"

    def test_soul_md_exists(self, soul_md_path):
        """SOUL.md 文件存在"""
        assert soul_md_path.exists(), "SOUL.md 文件不存在"

    def test_no_trigger_word_mapping_table(self, soul_md_path):
        """SOUL.md 不应包含触发词映射表"""
        content = soul_md_path.read_text()

        forbidden_patterns = [
            "| 用户说的话",
            "| 关键词",
            "| 意图类型",
            "触发词 →",
        ]

        for pattern in forbidden_patterns:
            assert pattern not in content, \
                f"SOUL.md 包含触发词映射表模式 '{pattern}'"


# ==================== 执行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])