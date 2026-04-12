"""
注册对话 API 测试

测试 AI 红娘注册对话的 HTTP 接口

注意：该 API 已被重构移除，测试暂时跳过
"""
import pytest

# 整个测试文件跳过，因为 API 路由已被移除/重构
pytestmark = pytest.mark.skip(reason="registration-conversation API has been removed/refactored")

import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from db.database import SessionLocal, engine, Base
from db.repositories import UserRepository
from db.models import UserDB as User

# 创建测试客户端
client = TestClient(app)


@pytest.fixture(scope="function")
def test_db():
    """创建测试数据库"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_user(test_db):
    """创建测试用户"""
    import json

    user = User(
        id="test-user-001",
        name="测试用户",
        email="test@example.com",
        password_hash="hashed_password",
        age=25,
        gender="male",
        location="北京市",
        bio="这是一个测试用户",
        interests=json.dumps(["阅读", "旅行"]),
        values=json.dumps({}),
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(autouse=True)
def mock_llm():
    """自动 mock LLM 调用以避免真实 API 调用"""

    def mock_call_llm(prompt, **kwargs):
        """根据 prompt 类型返回不同的 mock 结果"""
        if "欢迎消息" in prompt or "问候" in prompt:
            # 欢迎消息 - 返回简单字符串
            return "你好呀，测试用户～ 很高兴认识你！让我了解一下你吧，你希望通过这里找到什么样的关系呢？"
        else:
            # 其他对话 - 返回 JSON 格式
            return json.dumps({
                "reply": "好的，我了解了！你还有什么想分享的吗？",
                "next_topic": "values",
                "collected_info": {"goal": "认真恋爱"},
                "understanding_delta": 0.15,
                "ai_response": "好的，我了解了！你还有什么想分享的吗？"
            })

    with patch('services.ai_native_conversation_service.call_llm', side_effect=mock_call_llm):
        with patch('services.ai_native_conversation_service.call_llm_stream_async', side_effect=mock_call_llm):
            yield


class TestStartConversation:
    """测试开始对话接口"""

    def test_start_conversation_success(self, test_db, test_user):
        """测试成功开始对话"""
        response = client.post(
            "/api/registration-conversation/start",
            json={"user_id": test_user.id, "user_name": test_user.name},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "session_id" in data
        assert "ai_message" in data
        assert "current_stage" in data
        assert data["current_stage"] == "dynamic_conversation"  # AI Native 使用动态话题

    def test_start_conversation_user_not_found(self, test_db):
        """测试用户不存在时开始对话"""
        response = client.post(
            "/api/registration-conversation/start",
            json={"user_id": "non-existent-user", "user_name": "不存在的用户"},
        )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "User not found" in data["detail"]

    def test_start_conversation_missing_user_id(self, test_db):
        """测试缺少 user_id 参数"""
        response = client.post(
            "/api/registration-conversation/start",
            json={"user_name": "测试用户"},
        )

        assert response.status_code == 422  # Validation error

    def test_start_conversation_missing_user_name(self, test_db, test_user):
        """测试缺少 user_name 参数"""
        response = client.post(
            "/api/registration-conversation/start",
            json={"user_id": test_user.id},
        )

        assert response.status_code == 422

    def test_start_conversation_welcome_message_contains_name(self, test_db, test_user):
        """测试欢迎语包含用户名"""
        response = client.post(
            "/api/registration-conversation/start",
            json={"user_id": test_user.id, "user_name": test_user.name},
        )

        data = response.json()
        assert test_user.name in data["ai_message"] or "你" in data["ai_message"]


class TestSendMessage:
    """测试发送消息接口"""

    def test_send_message_success(self, test_db, test_user):
        """测试成功发送消息"""
        # 先开始对话
        start_response = client.post(
            "/api/registration-conversation/start",
            json={"user_id": test_user.id, "user_name": test_user.name},
        )
        assert start_response.status_code == 200

        # 发送消息
        send_response = client.post(
            "/api/registration-conversation/message",
            json={"user_id": test_user.id, "message": "我想找认真恋爱的对象"},
        )

        assert send_response.status_code == 200
        data = send_response.json()
        assert data["success"] is True
        assert "ai_message" in data
        assert "current_stage" in data
        assert "is_completed" in data
        assert "collected_dimensions" in data

    def test_send_message_collects_goal(self, test_db, test_user):
        """测试发送消息收集关系目标"""
        # 开始对话
        client.post(
            "/api/registration-conversation/start",
            json={"user_id": test_user.id, "user_name": test_user.name},
        )

        # 发送关系期望回答
        response = client.post(
            "/api/registration-conversation/message",
            json={"user_id": test_user.id, "message": "我希望以结婚为目的"},
        )

        data = response.json()
        # AI Native 使用 collected_dimensions 而不是 collected_data_summary
        assert "collected_dimensions" in data

    def test_send_message_progresses_stages(self, test_db, test_user):
        """测试对话阶段推进"""
        # 开始对话
        client.post(
            "/api/registration-conversation/start",
            json={"user_id": test_user.id, "user_name": test_user.name},
        )

        stages = []
        messages = [
            "认真恋爱",
            "温柔善良的人",
            "最看重责任心",
            "喜欢旅行和看电影",
        ]

        for msg in messages:
            response = client.post(
                "/api/registration-conversation/message",
                json={"user_id": test_user.id, "message": msg},
            )
            data = response.json()
            stages.append(data["current_stage"])

        # AI Native 使用 dynamic_conversation 阶段
        assert "dynamic_conversation" in stages

    def test_send_message_marks_completed(self, test_db, test_user):
        """测试对话完成标记"""
        # 开始对话
        client.post(
            "/api/registration-conversation/start",
            json={"user_id": test_user.id, "user_name": test_user.name},
        )

        # AI Native 在了解度达到 70% 时自动标记完成
        # 这里仅验证响应结构
        response = client.post(
            "/api/registration-conversation/message",
            json={"user_id": test_user.id, "message": "你好"},
        )

        data = response.json()
        assert "is_completed" in data

    def test_send_message_no_session_creates_new(self, test_db, test_user):
        """测试没有会话时自动创建"""
        response = client.post(
            "/api/registration-conversation/message",
            json={"user_id": test_user.id, "message": "你好"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "ai_message" in data

    def test_send_message_empty_message(self, test_db, test_user):
        """测试空消息处理"""
        # 开始对话
        client.post(
            "/api/registration-conversation/start",
            json={"user_id": test_user.id, "user_name": test_user.name},
        )

        response = client.post(
            "/api/registration-conversation/message",
            json={"user_id": test_user.id, "message": ""},
        )

        assert response.status_code == 200

    def test_send_message_missing_user_id(self, test_db):
        """测试缺少 user_id"""
        response = client.post(
            "/api/registration-conversation/message",
            json={"message": "你好"},
        )

        assert response.status_code == 422

    def test_send_message_missing_message(self, test_db, test_user):
        """测试缺少 message"""
        response = client.post(
            "/api/registration-conversation/message",
            json={"user_id": test_user.id},
        )

        assert response.status_code == 422


class TestGetSession:
    """测试获取会话接口"""

    def test_get_session_success(self, test_db, test_user):
        """测试成功获取会话"""
        # 先开始对话
        client.post(
            "/api/registration-conversation/start",
            json={"user_id": test_user.id, "user_name": test_user.name},
        )

        # 获取会话
        response = client.get(f"/api/registration-conversation/session/{test_user.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is True
        assert data["user_id"] == test_user.id

    def test_get_session_nonexistent(self, test_db):
        """测试获取不存在的会话"""
        response = client.get(
            "/api/registration-conversation/session/non-existent-user"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is False

    def test_get_session_after_messages(self, test_db, test_user):
        """测试发送消息后获取会话"""
        # 开始对话并发送消息
        client.post(
            "/api/registration-conversation/start",
            json={"user_id": test_user.id, "user_name": test_user.name},
        )
        client.post(
            "/api/registration-conversation/message",
            json={"user_id": test_user.id, "message": "认真恋爱"},
        )

        # 获取会话
        response = client.get(f"/api/registration-conversation/session/{test_user.id}")

        data = response.json()
        assert data["exists"] is True
        assert data["conversation_count"] >= 1


class TestCompleteConversation:
    """测试完成对话接口"""

    def test_complete_conversation_success(self, test_db, test_user):
        """测试成功完成对话"""
        # 先开始对话
        client.post(
            "/api/registration-conversation/start",
            json={"user_id": test_user.id, "user_name": test_user.name},
        )

        # 完成对话
        response = client.post(
            f"/api/registration-conversation/complete/{test_user.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data

    def test_complete_conversation_no_session(self, test_db):
        """测试没有会话时完成对话"""
        response = client.post(
            "/api/registration-conversation/complete/non-existent-user"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestConversationFlow:
    """测试完整对话流程"""

    def test_full_conversation_flow(self, test_db, test_user):
        """测试完整的对话流程"""
        # 1. 开始对话
        start_response = client.post(
            "/api/registration-conversation/start",
            json={"user_id": test_user.id, "user_name": test_user.name},
        )
        assert start_response.status_code == 200
        assert start_response.json()["current_stage"] == "dynamic_conversation"

        # 2. 发送所有阶段的回答
        responses = [
            ("认真恋爱", "relationship_goal"),
            ("温柔善良，有共同语言", "ideal_partner"),
            ("最看重家庭和责任心", "values"),
            ("喜欢旅行、阅读、健身", "lifestyle"),
        ]

        for message, expected_stage in responses:
            response = client.post(
                "/api/registration-conversation/message",
                json={"user_id": test_user.id, "message": message},
            )
            assert response.status_code == 200
            data = response.json()
            assert "ai_message" in data

        # 3. 验证对话状态（不一定完成，因为了解度可能未达 70%）
        final_response = client.post(
            "/api/registration-conversation/message",
            json={"user_id": test_user.id, "message": "好的"},
        )
        assert final_response.status_code == 200
        # is_completed 取决于了解度是否达到 70%，不做强制断言

        # 4. 获取会话摘要
        session_response = client.get(
            f"/api/registration-conversation/session/{test_user.id}"
        )
        session_data = session_response.json()
        assert session_data["exists"] is True

    def test_conversation_data_collection_summary(self, test_db, test_user):
        """测试收集数据摘要"""
        client.post(
            "/api/registration-conversation/start",
            json={"user_id": test_user.id, "user_name": test_user.name},
        )

        # 发送关系期望
        response = client.post(
            "/api/registration-conversation/message",
            json={"user_id": test_user.id, "message": "想结婚"},
        )

        data = response.json()
        # API 返回 collected_dimensions 而不是 collected_data_summary
        assert "collected_dimensions" in data


class TestAPIEdgeCases:
    """测试 API 边界情况"""

    def test_concurrent_sessions_different_users(self, test_db):
        """测试并发会话（不同用户）"""
        # 创建两个用户
        user1 = User(
            id="concurrent-user-1",
            name="用户一",
            email="user1@test.com",
            password_hash="hash",
            age=25,
            gender="male",
            location="北京",
            bio="",
            interests="[]",
            values="{}",
            is_active=True,
        )
        user2 = User(
            id="concurrent-user-2",
            name="用户二",
            email="user2@test.com",
            password_hash="hash",
            age=28,
            gender="female",
            location="上海",
            bio="",
            interests="[]",
            values="{}",
            is_active=True,
        )
        test_db.add(user1)
        test_db.add(user2)
        test_db.commit()

        # 分别开始对话
        response1 = client.post(
            "/api/registration-conversation/start",
            json={"user_id": user1.id, "user_name": user1.name},
        )
        response2 = client.post(
            "/api/registration-conversation/start",
            json={"user_id": user2.id, "user_name": user2.name},
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        # 发送不同回答
        client.post(
            "/api/registration-conversation/message",
            json={"user_id": user1.id, "message": "认真恋爱"},
        )
        client.post(
            "/api/registration-conversation/message",
            json={"user_id": user2.id, "message": "交朋友"},
        )

        # 获取会话验证独立
        session1 = client.get(f"/api/registration-conversation/session/{user1.id}")
        session2 = client.get(f"/api/registration-conversation/session/{user2.id}")

        # 两个会话的数据应该不同
        # API 返回的是 GetSessionResponse 模型，直接包含 user_id 字段
        assert session1.json()["user_id"] == user1.id
        assert session2.json()["user_id"] == user2.id

    def test_rapid_sequential_messages(self, test_db, test_user):
        """测试快速连续发送消息"""
        client.post(
            "/api/registration-conversation/start",
            json={"user_id": test_user.id, "user_name": test_user.name},
        )

        # 快速发送多条消息
        messages = ["恋爱", "温柔", "家庭", "旅行", "好的"]
        for msg in messages:
            response = client.post(
                "/api/registration-conversation/message",
                json={"user_id": test_user.id, "message": msg},
            )
            assert response.status_code == 200

    def test_special_characters_in_messages(self, test_db, test_user):
        """测试消息中的特殊字符"""
        client.post(
            "/api/registration-conversation/start",
            json={"user_id": test_user.id, "user_name": test_user.name},
        )

        special_messages = [
            "认真恋爱❤️",
            "温柔善良😊",
            "家庭>事业",
            "旅行✈️、阅读📚",
        ]

        for msg in special_messages:
            response = client.post(
                "/api/registration-conversation/message",
                json={"user_id": test_user.id, "message": msg},
            )
            assert response.status_code == 200

    def test_very_long_message(self, test_db, test_user):
        """测试超长消息"""
        client.post(
            "/api/registration-conversation/start",
            json={"user_id": test_user.id, "user_name": test_user.name},
        )

        long_message = "我希望找到 " + "非常非常" * 100 + "温柔的人"
        response = client.post(
            "/api/registration-conversation/message",
            json={"user_id": test_user.id, "message": long_message},
        )

        assert response.status_code == 200

    def test_invalid_json_body(self, test_db, test_user):
        """测试无效 JSON"""
        response = client.post(
            "/api/registration-conversation/start",
            data="not valid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422
