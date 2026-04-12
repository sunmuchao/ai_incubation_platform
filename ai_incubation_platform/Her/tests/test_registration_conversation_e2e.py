"""
注册对话端到端集成测试

测试完整的用户注册 -> AI 对话 -> 数据保存流程

注意：该 API 和服务已被重构移除，测试暂时跳过
"""
import pytest

# 整个测试文件跳过，因为 API 路由和服务已被移除/重构
pytestmark = pytest.mark.skip(reason="registration-conversation API and service have been removed/refactored")

import json
from fastapi.testclient import TestClient
from main import app
from db.database import SessionLocal, engine, Base
from db.repositories import UserRepository
from db.models import UserDB
from models.user import User
from services.registration_conversation_service import registration_conversation_service

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
def registered_user(test_db):
    """创建已注册但未完成对话的用户"""
    user = UserDB(
        id="e2e-user-001",
        name="端到端测试用户",
        email="e2e@example.com",
        password_hash="hashed_password",
        age=28,
        gender="female",
        location="上海市",
        bio="喜欢旅行和摄影",
        interests='["旅行", "摄影", "美食"]',  # JSON 字符串
        values='{}',  # JSON 字符串
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


class TestE2ERegistrationConversationFlow:
    """端到端注册对话流程测试"""

    def test_full_registration_to_conversation_flow(self, test_db, registered_user):
        """测试从注册到对话完成的完整流程"""
        # 步骤 1: 用户注册成功（模拟已完成）
        # 实际场景中，注册 API 会创建用户并返回用户信息
        user_id = registered_user.id
        user_name = registered_user.name

        # 步骤 2: 前端调用开始对话接口
        start_response = client.post(
            "/api/registration-conversation/start",
            json={"user_id": user_id, "user_name": user_name},
        )
        assert start_response.status_code == 200
        start_data = start_response.json()
        assert start_data["success"] is True
        # current_stage 可能是 "welcome" 或 "dynamic_conversation" 取决于实现
        assert start_data["current_stage"] in ["welcome", "dynamic_conversation"]

        # 步骤 3: 用户依次回答每个阶段的问题
        # 阶段 1: 关系期望
        msg1_response = client.post(
            "/api/registration-conversation/message",
            json={"user_id": user_id, "message": "我希望以结婚为目的交往"},
        )
        assert msg1_response.status_code == 200
        msg1_data = msg1_response.json()
        assert msg1_data["collected_data_summary"]["goal"] == "marriage"
        assert msg1_data["current_stage"] == "ideal_partner"

        # 阶段 2: 理想型描述
        msg2_response = client.post(
            "/api/registration-conversation/message",
            json={"user_id": user_id, "message": "希望对方温柔体贴，有责任感，年龄相仿"},
        )
        assert msg2_response.status_code == 200
        msg2_data = msg2_response.json()
        assert "ideal_partner_desc" in msg2_data["collected_data_summary"] or msg2_data["current_stage"] == "values"

        # 阶段 3: 价值观
        msg3_response = client.post(
            "/api/registration-conversation/message",
            json={"user_id": user_id, "message": "最看重家庭观念和个人成长"},
        )
        assert msg3_response.status_code == 200
        msg3_data = msg3_response.json()

        # 阶段 4: 生活方式
        msg4_response = client.post(
            "/api/registration-conversation/message",
            json={"user_id": user_id, "message": "周末喜欢爬山、看展览、和朋友聚餐"},
        )
        assert msg4_response.status_code == 200
        msg4_data = msg4_response.json()

        # 步骤 4: 验证对话完成
        assert msg4_data["is_completed"] is True
        assert msg4_data["current_stage"] == "final"

        # 步骤 5: 调用完成接口
        complete_response = client.post(
            f"/api/registration-conversation/complete/{user_id}"
        )
        assert complete_response.status_code == 200

        # 步骤 6: 验证会话状态
        session_response = client.get(
            f"/api/registration-conversation/session/{user_id}"
        )
        assert session_response.status_code == 200
        session_data = session_response.json()
        assert session_data["success"] is True
        assert session_data["session"]["is_completed"] is True

    def test_conversation_updates_user_data(self, test_db, registered_user):
        """测试对话数据可以应用到用户资料"""
        user_id = registered_user.id

        # 开始对话
        client.post(
            "/api/registration-conversation/start",
            json={"user_id": user_id, "user_name": registered_user.name},
        )

        # 收集数据
        client.post(
            "/api/registration-conversation/message",
            json={"user_id": user_id, "message": "认真恋爱"},
        )
        client.post(
            "/api/registration-conversation/message",
            json={"user_id": user_id, "message": "温柔善良"},
        )
        client.post(
            "/api/registration-conversation/message",
            json={"user_id": user_id, "message": "家庭最重要"},
        )
        client.post(
            "/api/registration-conversation/message",
            json={"user_id": user_id, "message": "旅行"},
        )

        # 获取会话收集的数据
        session_response = client.get(f"/api/registration-conversation/session/{user_id}")
        session_data = session_response.json()

        assert session_data["session"]["collected_data"]["goal"] == "serious"

    def test_user_can_login_after_registration(self, test_db, registered_user):
        """测试用户注册后可以正常登录"""
        # 完成注册对话
        client.post(
            "/api/registration-conversation/start",
            json={"user_id": registered_user.id, "user_name": registered_user.name},
        )
        client.post(
            "/api/registration-conversation/message",
            json={"user_id": registered_user.id, "message": "认真恋爱"},
        )

        # 尝试登录（使用真实登录接口）
        login_response = client.post(
            "/api/users/login",
            json={"username": registered_user.username, "password": "password123"},
        )
        # 因为密码不匹配，应该返回 401
        assert login_response.status_code == 401

    def test_multiple_users_concurrent_conversations(self, test_db):
        """测试多个用户并发进行对话"""
        # 创建多个测试用户
        users = []
        for i in range(3):
            user = User(
                id=f"concurrent-user-{i}",
                username=f"user{i}",
                email=f"user{i}@test.com",
                password="hash",
                name=f"用户{i}",
                age=25 + i,
                gender="male",
                location="北京",
            )
            test_db.add(user)
            users.append(user)
        test_db.commit()

        # 每个用户独立开始对话
        sessions = []
        for user in users:
            response = client.post(
                "/api/registration-conversation/start",
                json={"user_id": user.id, "user_name": user.name},
            )
            assert response.status_code == 200
            sessions.append(response.json()["session_id"])

        # 验证会话 ID 各不相同
        assert len(set(sessions)) == len(sessions)

        # 每个用户发送不同的回答
        responses = ["认真恋爱", "结婚", "交朋友"]
        for i, (user, response_msg) in enumerate(zip(users, responses)):
            msg_response = client.post(
                "/api/registration-conversation/message",
                json={"user_id": user.id, "message": response_msg},
            )
            assert msg_response.status_code == 200

        # 验证每个用户的会话独立
        for i, user in enumerate(users):
            session_response = client.get(
                f"/api/registration-conversation/session/{user.id}"
            )
            session_data = session_response.json()
            assert session_data["session"]["user_id"] == user.id


class TestE2EDataPersistence:
    """端到端数据持久化测试"""

    def test_collected_data_can_be_applied_to_user(self, test_db, registered_user):
        """测试收集的数据可以应用到用户记录"""
        user_id = registered_user.id

        # 开始并完成对话
        client.post(
            "/api/registration-conversation/start",
            json={"user_id": user_id, "user_name": registered_user.name},
        )

        responses = ["结婚", "温柔", "家庭", "旅行"]
        for msg in responses:
            client.post(
                "/api/registration-conversation/message",
                json={"user_id": user_id, "message": msg},
            )

        # 获取会话数据
        session_response = client.get(f"/api/registration-conversation/session/{user_id}")
        session_data = session_response.json()

        # 验证数据被正确收集
        assert session_data["session"]["is_completed"] is True
        assert session_data["session"]["collected_data"]["goal"] == "marriage"

    def test_session_survives_server_restart(self, test_db, registered_user):
        """测试会话数据在模拟服务重启后仍然可用"""
        user_id = registered_user.id

        # 开始对话
        start_response = client.post(
            "/api/registration-conversation/start",
            json={"user_id": user_id, "user_name": registered_user.name},
        )
        session_id = start_response.json()["session_id"]

        # 发送一条消息
        client.post(
            "/api/registration-conversation/message",
            json={"user_id": user_id, "message": "认真恋爱"},
        )

        # 模拟服务重启（创建新的测试客户端）
        new_client = TestClient(app)

        # 获取会话（应该仍然可用，因为存储在内存中）
        # 注意：在真实场景中，应该使用 Redis 或数据库存储会话
        session_response = new_client.get(
            f"/api/registration-conversation/session/{user_id}"
        )
        session_data = session_response.json()

        # 在内存存储模式下，会话应该仍然存在
        assert session_data["success"] is True


class TestE2EApiIntegration:
    """端到端 API 集成测试"""

    def test_registration_conversation_api_integrated(self, test_db, registered_user):
        """测试注册对话 API 已正确集成到主应用"""
        # 访问根端点，验证功能列表包含注册对话
        root_response = client.get("/")
        root_data = root_response.json()

        assert "注册对话 AI 红娘" in root_data["features"]

        # 验证端点注册
        assert "registration-conversation-start" in root_data["endpoints"]
        assert "registration-conversation-message" in root_data["endpoints"]
        assert "registration-conversation-session" in root_data["endpoints"]
        assert "registration-conversation-complete" in root_data["endpoints"]

    def test_health_check_includes_registration(self, test_db):
        """测试健康检查端点"""
        health_response = client.get("/health")
        assert health_response.status_code == 200
        health_data = health_response.json()
        assert health_data["status"] in ["healthy", "degraded"]

    def test_metrics_endpoint_accessible(self, test_db):
        """测试指标端点可访问"""
        metrics_response = client.get("/metrics")
        assert metrics_response.status_code == 200


class TestE2EBoundaryConditions:
    """端到端边界条件测试"""

    def test_user_deletes_localstorage_and_returns(self, test_db, registered_user):
        """测试用户清除 localStorage 后返回"""
        user_id = registered_user.id

        # 开始对话
        client.post(
            "/api/registration-conversation/start",
            json={"user_id": user_id, "user_name": registered_user.name},
        )

        # 发送部分消息
        client.post(
            "/api/registration-conversation/message",
            json={"user_id": user_id, "message": "认真恋爱"},
        )

        # 模拟用户清除状态后重新访问（通过获取会话）
        session_response = client.get(f"/api/registration-conversation/session/{user_id}")
        assert session_response.status_code == 200
        session_data = session_response.json()

        # 会话应该仍然存在
        assert session_data["success"] is True
        assert session_data["session"]["current_stage"] != "welcome"

    def test_conversation_timeout_simulation(self, test_db, registered_user):
        """测试对话超时模拟（长时间不进行对话）"""
        user_id = registered_user.id

        # 开始对话
        client.post(
            "/api/registration-conversation/start",
            json={"user_id": user_id, "user_name": registered_user.name},
        )

        # 立即获取会话（模拟用户离开后返回）
        session_response = client.get(f"/api/registration-conversation/session/{user_id}")
        session_data = session_response.json()

        # 会话应该仍然有效
        assert session_data["success"] is True

    def test_incomplete_then_complete_later(self, test_db, registered_user):
        """测试用户中途离开后继续完成对话"""
        user_id = registered_user.id

        # 开始对话
        client.post(
            "/api/registration-conversation/start",
            json={"user_id": user_id, "user_name": registered_user.name},
        )

        # 只回答一个问题
        client.post(
            "/api/registration-conversation/message",
            json={"user_id": user_id, "message": "以结婚为目的"},
        )

        # 获取会话状态
        session1 = client.get(f"/api/registration-conversation/session/{user_id}").json()
        assert session1["session"]["is_completed"] is False

        # 稍后继续完成
        client.post(
            "/api/registration-conversation/message",
            json={"user_id": user_id, "message": "温柔"},
        )
        client.post(
            "/api/registration-conversation/message",
            json={"user_id": user_id, "message": "家庭"},
        )
        client.post(
            "/api/registration-conversation/message",
            json={"user_id": user_id, "message": "旅行"},
        )

        # 再次获取会话
        session2 = client.get(f"/api/registration-conversation/session/{user_id}").json()
        assert session2["session"]["is_completed"] is True


class TestE2ESecurityAndValidation:
    """端到端安全和验证测试"""

    def test_invalid_user_id_format(self, test_db):
        """测试无效用户 ID 格式"""
        response = client.post(
            "/api/registration-conversation/start",
            json={"user_id": "", "user_name": "测试"},
        )
        # 空用户 ID 应该返回 404 或 422
        assert response.status_code in [404, 422]

    def test_malformed_request_body(self, test_db):
        """测试畸形的请求体"""
        # 缺少必要字段
        response = client.post(
            "/api/registration-conversation/start",
            json={"user_id": "user-123"},  # 缺少 user_name
        )
        assert response.status_code == 422

    def test_sql_injection_attempt(self, test_db, registered_user):
        """测试 SQL 注入尝试"""
        malicious_user_id = "user-123'; DROP TABLE users; --"

        # 开始对话
        response = client.post(
            "/api/registration-conversation/start",
            json={"user_id": malicious_user_id, "user_name": "测试"},
        )
        # 应该返回 404（用户不存在）而不是 SQL 错误
        assert response.status_code == 404

        # 验证数据库表仍然存在
        health_response = client.get("/health")
        assert health_response.status_code == 200

    def test_xss_attempt_in_message(self, test_db, registered_user):
        """测试 XSS 注入尝试"""
        user_id = registered_user.id

        client.post(
            "/api/registration-conversation/start",
            json={"user_id": user_id, "user_name": registered_user.name},
        )

        # 尝试注入脚本
        malicious_message = "<script>alert('xss')</script>"
        response = client.post(
            "/api/registration-conversation/message",
            json={"user_id": user_id, "message": malicious_message},
        )

        assert response.status_code == 200
        data = response.json()
        # 消息应该被当作普通文本处理，不被执行
        assert malicious_message in data["ai_message"] or data["current_stage"] != "welcome"


class TestE2EPerformance:
    """端到端性能测试"""

    def test_response_time_under_normal_load(self, test_db, registered_user):
        """测试正常负载下的响应时间"""
        import time

        user_id = registered_user.id

        # 开始对话
        start = time.time()
        client.post(
            "/api/registration-conversation/start",
            json={"user_id": user_id, "user_name": registered_user.name},
        )
        start_time = time.time() - start

        # 应该在 1 秒内响应
        assert start_time < 1.0

        # 发送消息
        msg_start = time.time()
        client.post(
            "/api/registration-conversation/message",
            json={"user_id": user_id, "message": "认真恋爱"},
        )
        msg_time = time.time() - msg_start

        # 应该在 2 秒内响应（因为要处理 AI 逻辑）
        assert msg_time < 2.0

    def test_memory_session_storage_efficiency(self, test_db):
        """测试内存会话存储效率"""
        # 创建大量并发会话
        session_count = 50
        responses = []

        for i in range(session_count):
            user = User(
                id=f"perf-user-{i}",
                username=f"perfuser{i}",
                email=f"perf{i}@test.com",
                password="hash",
                name=f"性能用户{i}",
                age=25,
                gender="male",
                location="北京",
            )
            test_db.add(user)
        test_db.commit()

        # 所有用户同时开始对话
        for i in range(session_count):
            response = client.post(
                "/api/registration-conversation/start",
                json={"user_id": f"perf-user-{i}", "user_name": f"性能用户{i}"},
            )
            responses.append(response.status_code)

        # 所有请求都应该成功
        assert all(code == 200 for code in responses)
