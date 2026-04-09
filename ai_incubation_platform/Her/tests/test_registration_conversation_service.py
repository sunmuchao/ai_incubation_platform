"""
注册对话服务测试

测试 AI 红娘与注册用户的对话服务
"""
import pytest
from datetime import datetime
from services.registration_conversation_service import RegistrationConversationService


class TestCreateConversationSession:
    """测试创建对话会话"""

    def test_create_session_basic(self):
        """测试基本会话创建"""
        service = RegistrationConversationService()
        session = service.create_conversation_session("user-123", "张三")

        assert session["user_id"] == "user-123"
        assert session["user_name"] == "张三"
        assert session["current_stage"] == "welcome"
        assert session["stage_order"] == 0
        assert session["is_completed"] is False
        assert session["ai_message"] is not None
        assert len(session["conversation_history"]) == 0
        assert len(session["collected_data"]) == 0

    def test_create_session_contains_welcome_message(self):
        """测试欢迎语包含用户名"""
        service = RegistrationConversationService()
        session = service.create_conversation_session("user-456", "李四")

        assert "李四" in session["ai_message"] or "你" in session["ai_message"]

    def test_create_session_has_timestamp(self):
        """测试会话包含时间戳"""
        service = RegistrationConversationService()
        session = service.create_conversation_session("user-789", "王五")

        assert "created_at" in session
        assert session["created_at"] is not None


class TestProcessUserResponse:
    """测试处理用户回答"""

    def setup_method(self):
        """每个测试前的设置"""
        self.service = RegistrationConversationService()
        self.session = self.service.create_conversation_session("user-test", "测试用户")

    def test_process_welcome_stage(self):
        """测试欢迎阶段处理"""
        # 欢迎阶段不需要用户回答，直接进入下一阶段
        assert self.session["current_stage"] == "welcome"

    def test_extract_relationship_goal_serious(self):
        """测试提取认真恋爱期望"""
        # 手动设置到关系期望阶段
        self.session["current_stage"] = "relationship_goal"
        self.session["stage_order"] = 1

        result = self.service.process_user_response(
            self.session, "我希望找到认真恋爱的对象"
        )

        assert result["collected_data"]["goal"] == "serious"

    def test_extract_relationship_goal_marriage(self):
        """测试提取结婚期望"""
        self.session["current_stage"] = "relationship_goal"
        self.session["stage_order"] = 1

        result = self.service.process_user_response(
            self.session, "我想结婚，建立家庭"
        )

        assert result["collected_data"]["goal"] == "marriage"

    def test_extract_relationship_goal_casual(self):
        """测试提取交友期望"""
        self.session["current_stage"] = "relationship_goal"
        self.session["stage_order"] = 1

        result = self.service.process_user_response(
            self.session, "先交个朋友看看，随缘"
        )

        assert result["collected_data"]["goal"] == "casual"

    def test_extract_relationship_goal_default(self):
        """测试默认关系期望（无法识别时）"""
        self.session["current_stage"] = "relationship_goal"
        self.session["stage_order"] = 1

        result = self.service.process_user_response(
            self.session, "还没想好"
        )

        assert result["collected_data"]["goal"] == "serious"  # 默认为认真恋爱

    def test_extract_ideal_partner_description(self):
        """测试提取理想型描述"""
        self.session["current_stage"] = "ideal_partner"
        self.session["stage_order"] = 2
        self.session["collected_data"]["goal"] = "serious"

        result = self.service.process_user_response(
            self.session, "希望对方性格温柔，有上进心，年龄比我大一点"
        )

        assert "ideal_partner_desc" in result["collected_data"]
        assert result["collected_data"]["ideal_partner_desc"] == "希望对方性格温柔，有上进心，年龄比我大一点"

    def test_extract_values_family(self):
        """测试提取家庭价值观"""
        self.session["current_stage"] = "values"
        self.session["stage_order"] = 3
        self.session["collected_data"]["goal"] = "serious"

        result = self.service.process_user_response(
            self.session, "我最看重家庭观念，希望对方孝顺、顾家"
        )

        assert "values" in result["collected_data"]
        assert "family" in result["collected_data"]["values"]

    def test_extract_values_career(self):
        """测试提取事业价值观"""
        self.session["current_stage"] = "values"
        self.session["stage_order"] = 3
        self.session["collected_data"]["goal"] = "serious"

        result = self.service.process_user_response(
            self.session, "希望对方有事业心，工作上进"
        )

        assert "values" in result["collected_data"]
        assert "career" in result["collected_data"]["values"]

    def test_progress_through_stages(self):
        """测试对话阶段推进"""
        stages_order = []
        current_session = self.session

        # 模拟完成所有阶段
        # 注意：第一条消息从 welcome 推进到 relationship_goal
        responses = [
            "你好",  # welcome -> relationship_goal
            "认真恋爱",  # relationship_goal -> ideal_partner
            "温柔善良，有共同语言",  # ideal_partner -> values
            "家庭和责任",  # values -> lifestyle
            "旅行",  # lifestyle -> final
        ]

        for i, response in enumerate(responses):
            current_session = self.service.process_user_response(current_session, response)
            stages_order.append(current_session["current_stage"])

        # 验证阶段顺序正确
        # 第一条消息后进入 relationship_goal 阶段
        assert stages_order[0] == "relationship_goal"
        assert stages_order[1] == "ideal_partner"
        assert stages_order[2] == "values"
        assert stages_order[3] == "lifestyle"
        assert stages_order[4] == "final"

    def test_conversation_completion(self):
        """测试对话完成标记"""
        self.session["current_stage"] = "lifestyle"
        self.session["stage_order"] = 4

        result = self.service.process_user_response(
            self.session, "我喜欢看电影、健身"
        )

        assert result["is_completed"] is True
        assert result["current_stage"] == "final"
        assert result["stage_order"] == 5

    def test_conversation_history_recorded(self):
        """测试对话历史被记录"""
        self.session["current_stage"] = "relationship_goal"
        self.session["stage_order"] = 1

        result = self.service.process_user_response(
            self.session, "我想找认真恋爱的"
        )

        assert len(result["conversation_history"]) >= 1
        assert result["conversation_history"][0]["stage"] == "relationship_goal"
        assert "user_response" in result["conversation_history"][0]


class TestExtractInformation:
    """测试信息提取功能"""

    def setup_method(self):
        self.service = RegistrationConversationService()

    def test_extract_goal_keywords_variations(self):
        """测试关系期望关键词变体识别"""
        # 认真恋爱关键词
        assert self.service._extract_information(
            "relationship_goal", "想谈一场不分手的恋爱"
        ) == {"goal": "serious"}

        assert self.service._extract_information(
            "relationship_goal", "长期稳定关系"
        ) == {"goal": "serious"}

    def test_extract_goal_marriage_keywords(self):
        """测试结婚相关关键词识别"""
        result = self.service._extract_information(
            "relationship_goal", "想找个合适的人结婚生子"
        )
        assert result == {"goal": "marriage"}

    def test_extract_goal_casual_keywords(self):
        """测试交友相关关键词识别"""
        result = self.service._extract_information(
            "relationship_goal", "先交朋友，看缘分发展"
        )
        assert result == {"goal": "casual"}

    def test_extract_values_multiple(self):
        """测试多个价值观同时识别"""
        result = self.service._extract_information(
            "values", "希望对方顾家、有责任心、性格开朗"
        )

        assert "values" in result
        assert len(result["values"]) >= 1

    def test_no_extraction_unrelated_stage(self):
        """测试无关阶段不提取信息"""
        result = self.service._extract_information("welcome", "你好")
        assert result is None


class TestGenerateAIResponse:
    """测试 AI 回复生成"""

    def setup_method(self):
        self.service = RegistrationConversationService()
        self.collected_data = {"goal": "serious"}
        self.session = {"user_name": "测试用户"}

    def test_empathy_response_for_goal(self):
        """测试共情回复"""
        response = self.service._generate_ai_response(
            self.session, "relationship_goal", "我想认真恋爱", self.collected_data
        )

        assert "我懂你" in response or "认真" in response or "💕" in response

    def test_response_contains_next_question(self):
        """测试回复包含下一个问题"""
        response = self.service._generate_ai_response(
            self.session, "ideal_partner", "温柔的人", self.collected_data
        )

        assert self.service.STAGES["ideal_partner"]["question"] in response

    def test_final_message_contains_summary(self):
        """测试结束语包含信息摘要"""
        collected = {
            "goal": "serious",
            "ideal_partner_desc": "温柔善良",
            "values": {"family": 0.8},
        }

        message = self.service._generate_final_message(collected)

        assert "认真恋爱" in message or "了解" in message
        assert "完善" in message or "查看" in message


class TestApplyCollectedData:
    """测试应用收集的数据"""

    def setup_method(self):
        self.service = RegistrationConversationService()

    def test_apply_goal_data(self):
        """测试应用关系目标数据"""
        session = {"collected_data": {"goal": "marriage"}}
        user_data = {"goal": None}

        result = self.service.apply_collected_data(session, user_data)

        assert result["goal"] == "marriage"

    def test_apply_values_data(self):
        """测试应用价值观数据"""
        session = {
            "collected_data": {
                "values": {"family": 0.8, "career": 0.6}
            }
        }
        user_data = {"values": {}}

        result = self.service.apply_collected_data(session, user_data)

        assert "family" in result["values"]
        assert result["values"]["family"] == 0.8

    def test_apply_ideal_partner_data(self):
        """测试应用理想型数据"""
        session = {"collected_data": {"ideal_partner_desc": "温柔，有责任心"}}
        user_data = {}

        result = self.service.apply_collected_data(session, user_data)

        assert result["ideal_partner_desc"] == "温柔，有责任心"

    def test_merge_existing_values(self):
        """测试合并已存在的价值观数据"""
        session = {
            "collected_data": {
                "values": {"family": 0.9}
            }
        }
        user_data = {"values": {"career": 0.7}}

        result = self.service.apply_collected_data(session, user_data)

        assert "family" in result["values"]
        assert "career" in result["values"]


class TestGetSessionSummary:
    """测试获取会话摘要"""

    def setup_method(self):
        self.service = RegistrationConversationService()
        self.session = self.service.create_conversation_session("user-summary", "摘要用户")

    def test_summary_contains_basic_info(self):
        """测试摘要包含基本信息"""
        summary = self.service.get_session_summary(self.session)

        assert summary["user_id"] == "user-summary"
        assert summary["user_name"] == "摘要用户"
        assert "is_completed" in summary
        assert "current_stage" in summary

    def test_summary_conversation_count(self):
        """测试会话计数正确"""
        self.session["conversation_history"].append({"stage": "test", "user_response": "test"})
        self.session["conversation_history"].append({"stage": "test2", "user_response": "test2"})

        summary = self.service.get_session_summary(self.session)

        assert summary["conversation_count"] == 2


class TestEdgeCases:
    """测试边界情况"""

    def setup_method(self):
        self.service = RegistrationConversationService()

    def test_empty_user_response(self):
        """测试空用户回答"""
        session = self.service.create_conversation_session("user-edge", "边缘用户")
        session["current_stage"] = "relationship_goal"
        session["stage_order"] = 1

        result = self.service.process_user_response(session, "")

        # 空回答应该仍然推进流程
        assert result["current_stage"] != "welcome"

    def test_very_long_response(self):
        """测试超长回答处理"""
        session = self.service.create_conversation_session("user-edge", "边缘用户")
        session["current_stage"] = "ideal_partner"
        session["stage_order"] = 2

        long_response = "a" * 1000
        result = self.service.process_user_response(session, long_response)

        assert result["collected_data"]["ideal_partner_desc"] == long_response

    def test_special_characters_in_response(self):
        """测试特殊字符回答"""
        session = self.service.create_conversation_session("user-edge", "边缘用户")
        session["current_stage"] = "ideal_partner"
        session["stage_order"] = 2

        special_response = "希望对方喜欢🎵音乐，热爱🌊大海，相信✨缘分"
        result = self.service.process_user_response(session, special_response)

        assert result["collected_data"]["ideal_partner_desc"] == special_response

    def test_mixed_language_response(self):
        """测试混合语言回答"""
        session = self.service.create_conversation_session("user-edge", "边缘用户")
        session["current_stage"] = "relationship_goal"
        session["stage_order"] = 1

        mixed_response = "我想找 serious relationship，不是 casual 的"
        result = self.service.process_user_response(session, mixed_response)

        # 应该能识别关键词
        assert "goal" in result["collected_data"]

    def test_rapid_stage_progression(self):
        """测试快速连续问答"""
        session = self.service.create_conversation_session("user-rapid", "快速用户")

        # 模拟快速完成所有阶段
        # 需要 6 条消息才能完成（从 welcome 到 final）
        responses = ["你好", "认真恋爱", "温柔", "家庭", "旅行", "好的"]

        for response in responses:
            session = self.service.process_user_response(session, response)

        # 最终应该完成对话
        assert session["is_completed"] is True

    def test_multiple_sessions_independent(self):
        """测试多个会话相互独立"""
        session1 = self.service.create_conversation_session("user-1", "用户一")
        session2 = self.service.create_conversation_session("user-2", "用户二")

        # 第一条消息从 welcome 推进到 relationship_goal
        session1 = self.service.process_user_response(session1, "认真恋爱")
        session2 = self.service.process_user_response(session2, "交朋友")

        # 第二条消息才真正收集数据
        session1 = self.service.process_user_response(session1, "想找个认真的人")
        session2 = self.service.process_user_response(session2, "先做朋友")

        # 收集的数据应该独立
        assert session1["collected_data"]["goal"] == "serious"
        assert session2["collected_data"]["goal"] == "casual"
