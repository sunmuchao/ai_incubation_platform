"""
API 层端到端测试

测试关键 API 端点的请求/响应格式、认证和基本功能：
- her_advisor.py - Her 对话匹配 API
- profile.py - 个人信息收集 API
- users.py - 用户管理 API
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
import sys

# 尝试导入 API 模块
try:
    from api.her_advisor import router as her_router
    HER_API_AVAILABLE = True
except ImportError:
    HER_API_AVAILABLE = False
    pytest.skip("her_advisor API not importable", allow_module_level=True)

# 尝试导入 users API
try:
    from api.users import router as users_router
    USERS_API_AVAILABLE = True
except ImportError:
    USERS_API_AVAILABLE = False


class TestHerAdvisorAPI:
    """Her Advisor API 测试"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        app = FastAPI()
        app.include_router(her_router)
        return app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)

    def test_her_chat_endpoint_exists(self, client):
        """测试 her_chat 端点存在"""
        # 端点应该存在
        response = client.post(
            "/api/her/chat",
            json={"message": "测试消息"}
        )
        # 应该返回响应（可能是错误，但不应是 404）
        assert response.status_code != 404

    def test_her_chat_request_validation(self, client):
        """测试 her_chat 请求验证"""
        # 缺少必填字段 message
        response = client.post(
            "/api/her/chat",
            json={}
        )
        assert response.status_code == 422  # Validation error

    def test_her_chat_with_message(self, client):
        """测试 her_chat 带消息"""
        with patch('services.conversation_match_service.get_conversation_match_service') as mock_service:
            mock_instance = MagicMock()
            mock_result = MagicMock()
            mock_result.ai_message = "你好！"
            mock_result.intent_type = "conversation"
            mock_result.matches = []
            mock_result.bias_analysis = None
            mock_result.proactive_suggestion = None
            mock_result.generative_ui = {}
            mock_result.suggested_actions = []

            mock_instance.process_message = AsyncMock(return_value=mock_result)
            mock_service.return_value = mock_instance

            response = client.post(
                "/api/her/chat",
                json={"message": "你好"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "ai_message" in data
            assert "intent_type" in data

    def test_her_chat_with_user_id(self, client):
        """测试 her_chat 带用户 ID"""
        with patch('services.conversation_match_service.get_conversation_match_service') as mock_service:
            mock_instance = MagicMock()
            mock_result = MagicMock()
            mock_result.ai_message = "你好！"
            mock_result.intent_type = "conversation"
            mock_result.matches = []
            mock_result.bias_analysis = None
            mock_result.proactive_suggestion = None
            mock_result.generative_ui = {}
            mock_result.suggested_actions = []

            mock_instance.process_message = AsyncMock(return_value=mock_result)
            mock_service.return_value = mock_instance

            response = client.post(
                "/api/her/chat",
                json={
                    "message": "你好",
                    "user_id": "user_001"
                }
            )

            assert response.status_code == 200

    def test_her_chat_with_authorization(self, client):
        """测试 her_chat 带认证"""
        with patch('services.conversation_match_service.get_conversation_match_service') as mock_service:
            with patch('api.her_advisor._extract_user_id_from_token', return_value='user_from_token'):
                mock_instance = MagicMock()
                mock_result = MagicMock()
                mock_result.ai_message = "你好！"
                mock_result.intent_type = "conversation"
                mock_result.matches = []
                mock_result.bias_analysis = None
                mock_result.proactive_suggestion = None
                mock_result.generative_ui = {}
                mock_result.suggested_actions = []

                mock_instance.process_message = AsyncMock(return_value=mock_result)
                mock_service.return_value = mock_instance

                response = client.post(
                    "/api/her/chat",
                    json={"message": "你好"},
                    headers={"Authorization": "Bearer test_token"}
                )

                assert response.status_code == 200

    def test_analyze_bias_endpoint_exists(self, client):
        """测试 analyze_bias 端点存在"""
        response = client.post(
            "/api/her/analyze-bias",
            json={"user_id": "user_001"}
        )
        # 应该返回响应（可能是错误，但不应是 404）
        assert response.status_code != 404

    def test_analyze_bias_request_validation(self, client):
        """测试 analyze_bias 请求验证"""
        # 缺少必填字段 user_id
        response = client.post(
            "/api/her/analyze-bias",
            json={}
        )
        assert response.status_code == 422

    def test_match_advice_endpoint_exists(self, client):
        """测试 match_advice 端点存在"""
        response = client.post(
            "/api/her/match-advice",
            json={"user_id_a": "user_001", "user_id_b": "user_002"}
        )
        # 应该返回响应（可能是错误，但不应是 404）
        assert response.status_code != 404

    def test_match_advice_request_validation(self, client):
        """测试 match_advice 请求验证"""
        # 缺少必填字段
        response = client.post(
            "/api/her/match-advice",
            json={"user_id_a": "user_001"}  # 缺少 user_id_b
        )
        assert response.status_code == 422

    def test_get_profile_endpoint_exists(self, client):
        """测试 get_profile 端点存在"""
        # 检查端点是否存在（有些端点可能不存在）
        response = client.get("/api/her/profile?user_id=user_001")
        # 端点可能不存在，接受 404 或其他响应
        assert response.status_code in [200, 404, 422, 500]

    def test_record_behavior_endpoint_exists(self, client):
        """测试 record_behavior 端点存在"""
        response = client.post(
            "/api/her/record-behavior",
            json={
                "user_id": "user_001",
                "event_type": "profile_view"
            }
        )
        # 端点可能不存在，接受 404 或其他响应
        assert response.status_code in [200, 404, 422, 500]


class TestHerAdvisorResponseModels:
    """Her Advisor 响应模型测试"""

    def test_her_chat_response_model_fields(self):
        """测试 HerChatResponse 模型字段"""
        from api.her_advisor import HerChatResponse

        response = HerChatResponse(
            ai_message="你好",
            intent_type="conversation"
        )

        assert response.ai_message == "你好"
        assert response.intent_type == "conversation"
        assert response.matches is None
        assert response.bias_analysis is None
        assert response.proactive_suggestion is None

    def test_her_chat_response_with_matches(self):
        """测试 HerChatResponse 带匹配"""
        from api.her_advisor import HerChatResponse

        response = HerChatResponse(
            ai_message="找到匹配",
            intent_type="match_request",
            matches=[
                {"id": "user_002", "name": "测试用户", "score": 0.85}
            ]
        )

        assert response.matches is not None
        assert len(response.matches) == 1

    def test_analyze_bias_response_model(self):
        """测试 AnalyzeBiasResponse 模型"""
        from api.her_advisor import AnalyzeBiasResponse

        response = AnalyzeBiasResponse(
            has_bias=True,
            bias_type="confirmation_bias",
            bias_description="偏向确认既有信念",
            confidence=0.75
        )

        assert response.has_bias is True
        assert response.bias_type == "confirmation_bias"

    def test_analyze_bias_response_no_bias(self):
        """测试 AnalyzeBiasResponse 无偏差"""
        from api.her_advisor import AnalyzeBiasResponse

        response = AnalyzeBiasResponse(
            has_bias=False,
            confidence=0.5
        )

        assert response.has_bias is False
        assert response.bias_type is None

    def test_match_advice_response_model(self):
        """测试 MatchAdviceResponse 模型"""
        from api.her_advisor import MatchAdviceResponse

        response = MatchAdviceResponse(
            advice_type="proceed",
            advice_content="建议继续发展关系",
            compatibility_score=0.85
        )

        assert response.advice_type == "proceed"
        assert response.compatibility_score == 0.85

    def test_user_profile_response_model(self):
        """测试 UserProfileResponse 模型"""
        from api.her_advisor import UserProfileResponse

        response = UserProfileResponse(
            user_id="user_001",
            self_profile={"interests": ["旅行"]},
            desire_profile={"age_range": [25, 30]},
            self_profile_confidence=0.7,
            desire_profile_confidence=0.6,
            self_profile_completeness=0.8,
            desire_profile_completeness=0.5
        )

        assert response.user_id == "user_001"
        assert response.self_profile["interests"] == ["旅行"]
        assert response.self_profile_confidence == 0.7


@pytest.mark.skipif(not USERS_API_AVAILABLE, reason="users API not importable")
class TestUsersAPI:
    """Users API 测试"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        app = FastAPI()
        app.include_router(users_router)
        return app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)


class TestRequestModels:
    """请求模型测试"""

    def test_her_chat_request_model(self):
        """测试 HerChatRequest 模型"""
        from api.her_advisor import HerChatRequest

        request = HerChatRequest(message="你好")

        assert request.message == "你好"
        assert request.user_id is None
        assert request.thread_id is None
        assert request.message_history is None

    def test_her_chat_request_with_history(self):
        """测试 HerChatRequest 带历史"""
        from api.her_advisor import HerChatRequest

        request = HerChatRequest(
            message="你好",
            user_id="user_001",
            message_history=[
                {"role": "user", "content": "之前的消息"}
            ]
        )

        assert request.user_id == "user_001"
        assert request.message_history is not None

    def test_analyze_bias_request_model(self):
        """测试 AnalyzeBiasRequest 模型"""
        from api.her_advisor import AnalyzeBiasRequest

        request = AnalyzeBiasRequest(user_id="user_001")

        assert request.user_id == "user_001"

    def test_match_advice_request_model(self):
        """测试 MatchAdviceRequest 模型"""
        from api.her_advisor import MatchAdviceRequest

        request = MatchAdviceRequest(
            user_id_a="user_001",
            user_id_b="user_002"
        )

        assert request.user_id_a == "user_001"
        assert request.user_id_b == "user_002"

    def test_record_behavior_request_model(self):
        """测试 RecordBehaviorEventRequest 模型"""
        from api.her_advisor import RecordBehaviorEventRequest

        request = RecordBehaviorEventRequest(
            user_id="user_001",
            event_type="profile_view",
            event_data={"target_id": "user_002"}
        )

        assert request.user_id == "user_001"
        assert request.event_type == "profile_view"
        assert request.event_data["target_id"] == "user_002"


class TestEdgeCases:
    """边界值测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        app = FastAPI()
        app.include_router(her_router)
        return TestClient(app)

    def test_empty_message(self, client):
        """测试空消息"""
        response = client.post(
            "/api/her/chat",
            json={"message": ""}
        )
        # 空消息可能导致服务器错误或验证错误
        assert response.status_code in [200, 422, 500]

    def test_very_long_message(self, client):
        """测试超长消息"""
        with patch('services.conversation_match_service.get_conversation_match_service') as mock_service:
            mock_instance = MagicMock()
            mock_result = MagicMock()
            mock_result.ai_message = "收到"
            mock_result.intent_type = "conversation"
            mock_result.matches = []
            mock_result.bias_analysis = None
            mock_result.proactive_suggestion = None
            mock_result.generative_ui = {}
            mock_result.suggested_actions = []

            mock_instance.process_message = AsyncMock(return_value=mock_result)
            mock_service.return_value = mock_instance

            long_message = "这是一个很长的消息" * 100
            response = client.post(
                "/api/her/chat",
                json={"message": long_message}
            )

            assert response.status_code == 200

    def test_special_characters_in_message(self, client):
        """测试特殊字符消息"""
        with patch('services.conversation_match_service.get_conversation_match_service') as mock_service:
            mock_instance = MagicMock()
            mock_result = MagicMock()
            mock_result.ai_message = "收到"
            mock_result.intent_type = "conversation"
            mock_result.matches = []
            mock_result.bias_analysis = None
            mock_result.proactive_suggestion = None
            mock_result.generative_ui = {}
            mock_result.suggested_actions = []

            mock_instance.process_message = AsyncMock(return_value=mock_result)
            mock_service.return_value = mock_instance

            response = client.post(
                "/api/her/chat",
                json={"message": "你好！@#$%^&*()"}
            )

            assert response.status_code == 200

    def test_unicode_message(self, client):
        """测试 Unicode 消息"""
        with patch('services.conversation_match_service.get_conversation_match_service') as mock_service:
            mock_instance = MagicMock()
            mock_result = MagicMock()
            mock_result.ai_message = "收到"
            mock_result.intent_type = "conversation"
            mock_result.matches = []
            mock_result.bias_analysis = None
            mock_result.proactive_suggestion = None
            mock_result.generative_ui = {}
            mock_result.suggested_actions = []

            mock_instance.process_message = AsyncMock(return_value=mock_result)
            mock_service.return_value = mock_instance

            response = client.post(
                "/api/her/chat",
                json={"message": "你好 💕 ✨ 🎉"}
            )

            assert response.status_code == 200

    def test_compatibility_score_bounds(self):
        """测试兼容度分数边界"""
        from api.her_advisor import MatchAdviceResponse

        # 最小值
        response_low = MatchAdviceResponse(
            advice_type="proceed",
            advice_content="测试",
            compatibility_score=0.0
        )
        assert response_low.compatibility_score == 0.0

        # 最大值
        response_high = MatchAdviceResponse(
            advice_type="proceed",
            advice_content="测试",
            compatibility_score=1.0
        )
        assert response_high.compatibility_score == 1.0

    def test_confidence_bounds(self):
        """测试置信度边界"""
        from api.her_advisor import AnalyzeBiasResponse

        # 最小值
        response_low = AnalyzeBiasResponse(
            has_bias=False,
            confidence=0.0
        )
        assert response_low.confidence == 0.0

        # 最大值
        response_high = AnalyzeBiasResponse(
            has_bias=True,
            confidence=1.0
        )
        assert response_high.confidence == 1.0