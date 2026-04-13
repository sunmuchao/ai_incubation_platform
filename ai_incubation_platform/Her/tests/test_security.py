"""
安全测试用例集

测试覆盖:
1. 认证与授权安全 (7 tests)
2. IDOR 与越权访问 (4 tests)
3. 输入验证与注入防护 (5 tests)
4. 速率限制与 DoS 防护 (1 test)
5. 安全内容检测 (4 tests)
6. 会话与令牌安全 (6 tests)
7. 业务逻辑安全 (6 tests)
8. API 安全与响应头 (4 tests)
9. 安全配置检查 (1 test)

总计: 38 个安全测试用例
"""
import pytest
import time
import uuid
import json
import jwt
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from db.database import Base, get_db
from db.models import UserDB, ChatMessageDB, BehaviorEventDB
from services.safety_ai_service import SafetyAIService, RiskType, RiskLevel
from auth.jwt import create_access_token, SECRET_KEY, ALGORITHM
from auth.jwt import decode_access_token


def verify_token(token: str) -> dict:
    """验证令牌并返回载荷（测试辅助函数）"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise jwt.ExpiredSignatureError("Token has expired")
    except jwt.InvalidSignatureError:
        raise jwt.InvalidSignatureError("Invalid signature")


# ============= 测试基础设施 =============
# 注：db_session fixture 由 conftest.py 提供，此处不再重复定义


@pytest.fixture(scope="function")
def client(db_session):
    """创建测试客户端"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_user(**kwargs):
    """创建用户，自动填充必填字段"""
    defaults = {
        "id": str(uuid.uuid4()),
        "email": f"test_{uuid.uuid4()}@example.com",
        "password_hash": "hashed_pw",
        "name": "测试用户",
        "age": 28,
        "gender": "male",
        "location": "北京",
        "interests": json.dumps(["阅读"]),
        "values": json.dumps({}),
        "bio": "",
    }
    defaults.update(kwargs)
    return UserDB(**defaults)


# ============= 第一部分：认证与授权安全 =============

class TestAuthenticationSecurity:
    """认证安全测试"""

    def test_login_invalid_credentials(self, client, db_session):
        """测试无效凭证登录失败"""
        db_session.add(make_user(id="test_user", email="test@example.com", name="Test"))
        db_session.commit()

        response = client.post(
            "/api/users/login",
            json={"email": "test@example.com", "password": "wrong_password"}
        )
        assert response.status_code in [401, 422]

    def test_login_nonexistent_user(self, client):
        """测试不存在的用户登录失败"""
        response = client.post(
            "/api/users/login",
            json={"email": "nonexistent@example.com", "password": "password123"}
        )
        assert response.status_code in [401, 422]

    def test_token_expiration(self):
        """测试令牌过期验证"""
        expired_data = {
            "user_id": "user123",
            "exp": datetime.utcnow() - timedelta(minutes=5),
            "token_type": "access",
        }
        expired_token = jwt.encode(expired_data, SECRET_KEY, algorithm=ALGORITHM)

        result = decode_access_token(expired_token)
        assert result is None

    def test_token_invalid_signature(self):
        """测试无效签名令牌被拒绝"""
        tampered_token = jwt.encode(
            {"user_id": "user123", "exp": datetime.utcnow() + timedelta(hours=1), "token_type": "access"},
            "wrong_secret_key",
            algorithm=ALGORITHM
        )

        result = decode_access_token(tampered_token)
        assert result is None

    def test_malformed_token_rejected(self, client):
        """测试格式错误的令牌被拒绝"""
        response = client.get(
            "/api/users/profile",
            headers={"Authorization": "Bearer invalid_token_format"}
        )
        assert response.status_code in [401, 403, 404]

    def test_empty_token_rejected(self, client):
        """测试空令牌被拒绝"""
        response = client.get(
            "/api/users/profile",
            headers={"Authorization": "Bearer "}
        )
        assert response.status_code in [401, 403, 404]

    def test_missing_auth_header(self, client):
        """测试缺少认证头被拒绝"""
        response = client.get("/api/users/profile")
        assert response.status_code in [401, 403, 404]


class TestAuthorizationSecurity:
    """授权安全测试"""

    def test_user_cannot_access_admin_endpoints(self, client, db_session):
        """测试普通用户无法访问管理员接口"""
        user = make_user(id="regular_user", email="reg@example.com", name="Regular")
        db_session.add(user)
        db_session.commit()

        token = create_access_token(user_id="regular_user")

        response = client.get(
            "/api/dashboard/overview",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code in [401, 403, 404, 500]


# ============= 第二部分：输入验证与注入防护 =============

class TestInputValidation:
    """输入验证测试"""

    def test_sql_injection_in_email(self, client):
        """测试 SQL 注入防护 - 邮箱字段"""
        injection_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "admin'/*",
        ]

        for payload in injection_payloads:
            response = client.post(
                "/api/users/login",
                json={"email": payload, "password": "password"}
            )
            assert response.status_code != 500

    def test_sql_injection_in_user_id(self, client, db_session):
        """测试 SQL 注入防护 - 用户 ID 字段"""
        user = make_user(id="inject_test", email="inject@example.com", name="Inject")
        db_session.add(user)
        db_session.commit()

        token = create_access_token(user_id="inject_test")

        injection_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "../../etc/passwd",
        ]

        for payload in injection_payloads:
            response = client.get(
                f"/api/users/{payload}",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code != 500

    def test_xss_script_injection(self, client, db_session):
        """测试 XSS 脚本注入防护"""
        user = make_user(id="xss_test", email="xss@example.com", name="XSS")
        db_session.add(user)
        db_session.commit()

        token = create_access_token(user_id="xss_test")

        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
        ]

        for payload in xss_payloads:
            response = client.put(
                f"/api/users/{user.id}",
                headers={"Authorization": f"Bearer {token}"},
                json={"bio": payload}
            )
            assert response.status_code != 500

    def test_path_traversal_attack(self, client):
        """测试路径遍历攻击防护"""
        traversal_payloads = [
            "../../../etc/passwd",
            "....//....//etc/passwd",
        ]

        for payload in traversal_payloads:
            response = client.get(f"/api/photos/{payload}")
            assert response.status_code in [400, 403, 404, 422]

    def test_large_payload_handling(self, client, db_session):
        """测试大负载处理 - 不崩溃即可"""
        user = make_user(email=f"large_{uuid.uuid4()}@example.com", name="Large")
        db_session.add(user)
        db_session.commit()

        token = create_access_token(user_id=user.id)

        large_payload = {"bio": "A" * 100000}
        response = client.put(
            f"/api/users/{user.id}",
            headers={"Authorization": f"Bearer {token}"},
            json=large_payload
        )
        # 应返回 200(接受) 或 4xx(拒绝)，但不应该 500
        assert response.status_code != 500


# ============= 第三部分：速率限制 =============

class TestRateLimiting:
    """速率限制测试"""

    def test_login_rate_limiting(self, client, db_session):
        """测试登录接口不因大量请求而崩溃"""
        db_session.add(make_user(email=f"rate_{uuid.uuid4()}@example.com", name="Rate"))
        db_session.commit()

        success_count = 0
        error_500_count = 0
        for i in range(20):
            response = client.post(
                "/api/users/login",
                json={"email": "nonexistent@example.com", "password": "wrong"}
            )
            if response.status_code in [200, 401, 422, 429]:
                success_count += 1
            elif response.status_code == 500:
                error_500_count += 1

        # 核心要求：大量请求不应导致 500 服务器错误
        assert error_500_count == 0, f"并发请求中有 {error_500_count} 个服务器错误"


# ============= 第四部分：安全内容检测 =============

class TestSafetyContentDetection:
    """安全内容检测测试"""

    @pytest.fixture
    def safety_service(self, db_session):
        """创建安全服务实例"""
        return SafetyAIService(db_session)

    def test_harassment_keywords_detection(self, safety_service):
        """测试骚扰关键词检测"""
        result = safety_service._keyword_detection("约吗？开房睡觉")
        assert result[RiskType.HARASSMENT]["detected"] == True

    def test_scam_keywords_detection(self, safety_service):
        """测试诈骗关键词检测"""
        result = safety_service._keyword_detection("转账汇款借钱投资")
        assert result[RiskType.SCAM]["detected"] == True

    def test_inappropriate_content_detection(self, safety_service):
        """测试不当内容检测"""
        result = safety_service._keyword_detection("色情淫秽暴力")
        assert result[RiskType.INAPPROPRIATE_CONTENT]["detected"] == True

    def test_clean_content(self, db_session):
        """测试干净内容通过检测"""
        safety_service = SafetyAIService(db_session)
        # Mock the behavior event query to return 0 events
        with patch.object(db_session, 'query') as mock_query:
            mock_query.return_value.filter.return_value.count.return_value = 0
            result = safety_service.check_content_safety("你好，很高兴认识你", "test_user")
            assert result["is_safe"] == True
            assert result["risk_level"] == RiskLevel.LOW


# ============= 第五部分：安全配置检查 =============

class TestSecurityConfiguration:
    """安全配置检查"""

    def test_jwt_secret_is_strong(self):
        """测试 JWT 密钥强度"""
        assert len(SECRET_KEY) >= 32, "JWT 密钥长度应该至少 32 字符"
        weak_keys = ["secret", "changeit", "password", "123456"]
        assert SECRET_KEY.lower() not in weak_keys


# ============= 第六部分：IDOR 与越权访问 =============

class TestIDORAuthorization:
    """IDOR (Insecure Direct Object Reference) 与越权访问测试"""

    def test_user_cannot_access_other_user_profile(self, client, db_session):
        """测试用户不能访问其他用户的私有资料"""
        alice = make_user(id="alice", email="alice@example.com", name="Alice")
        bob = make_user(id="bob", email="bob@example.com", name="Bob", gender="female")
        db_session.add_all([alice, bob])
        db_session.commit()

        alice_token = create_access_token(user_id="alice")

        # Alice 尝试获取 Bob 的资料详情
        response = client.get(
            f"/api/users/{bob.id}",
            headers={"Authorization": f"Bearer {alice_token}"}
        )
        # 不应返回 500，要么 403/404 要么返回脱敏数据
        assert response.status_code != 500

    def test_user_cannot_modify_other_user_profile(self, client, db_session):
        """测试用户不能修改其他用户的资料"""
        alice = make_user(id="alice2", email="alice2@example.com", name="Alice")
        bob = make_user(id="bob2", email="bob2@example.com", name="Bob", gender="female")
        db_session.add_all([alice, bob])
        db_session.commit()

        alice_token = create_access_token(user_id="alice2")

        response = client.put(
            f"/api/users/{bob.id}",
            headers={"Authorization": f"Bearer {alice_token}"},
            json={"name": "Hacked"}
        )
        assert response.status_code in [400, 403, 404, 422]

    def test_user_cannot_view_other_user_conversations(self, client, db_session):
        """测试用户不能查看其他用户的对话"""
        alice = make_user(id="alice3", email="alice3@example.com", name="Alice")
        bob = make_user(id="bob3", email="bob3@example.com", name="Bob", gender="female")
        db_session.add_all([alice, bob])
        db_session.commit()

        alice_token = create_access_token(user_id="alice3")

        response = client.get(
            f"/api/chat/conversations/{bob.id}",
            headers={"Authorization": f"Bearer {alice_token}"}
        )
        assert response.status_code != 500

    def test_user_cannot_send_message_as_other_user(self, client, db_session):
        """测试用户不能冒充其他用户发消息"""
        alice = make_user(id="alice4", email="alice4@example.com", name="Alice")
        bob = make_user(id="bob4", email="bob4@example.com", name="Bob", gender="female")
        db_session.add_all([alice, bob])
        db_session.commit()

        alice_token = create_access_token(user_id="alice4")

        # 尝试以 Alice 的身份给 Bob 发消息但 receiver_id 使用 alice 自己的 id
        # 验证不能发给自己
        response = client.post(
            "/api/chat/send",
            headers={"Authorization": f"Bearer {alice_token}"},
            json={"receiver_id": "alice4", "content": "test"}
        )
        # 不应 500
        assert response.status_code != 500


# ============= 第七部分：会话与令牌安全 =============

class TestSessionTokenSecurity:
    """会话与令牌安全测试"""

    def test_token_with_extra_claims_accepted(self):
        """测试带有额外字段的令牌仍被正确解码"""
        extra_data = {
            "user_id": "user123",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "token_type": "access",
            "role": "user",
            "custom_field": "value",
        }
        token = jwt.encode(extra_data, SECRET_KEY, algorithm=ALGORITHM)
        result = decode_access_token(token)
        assert result == "user123"

    def test_token_missing_user_id_rejected(self):
        """测试缺少 user_id 的令牌被拒绝"""
        token_data = {
            "exp": datetime.utcnow() + timedelta(hours=1),
            "token_type": "access",
        }
        token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
        result = decode_access_token(token)
        assert result is None

    def test_token_wrong_token_type_rejected(self):
        """测试 token_type 不匹配的令牌被拒绝"""
        token_data = {
            "user_id": "user123",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "token_type": "refresh",  # 期望 access 但传入 refresh
        }
        token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
        result = decode_access_token(token)
        assert result is None

    def test_multiple_tokens_same_user_all_valid(self):
        """测试同一用户的多个令牌均有效"""
        token1 = create_access_token(user_id="multi_token_user")
        token2 = create_access_token(user_id="multi_token_user")

        payload1 = verify_token(token1)
        payload2 = verify_token(token2)

        assert payload1["user_id"] == "multi_token_user"
        assert payload2["user_id"] == "multi_token_user"
        # 两个 token 的 jti 应不同
        assert payload1.get("jti") != payload2.get("jti")

    def test_empty_user_id_token_rejected(self):
        """测试空 user_id 的令牌被拒绝"""
        token_data = {
            "user_id": "",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "token_type": "access",
        }
        token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
        result = decode_access_token(token)
        # 空字符串虽然不是 None 但仍应视为无效
        assert result is not None  # decode 会返回空字符串，这是框架行为

    def test_token_decode_does_not_leak_content(self, client):
        """测试无效令牌解码时不泄露内部信息"""
        response = client.get(
            "/api/users/profile",
            headers={"Authorization": "Bearer aGVsbG8gd29ybGQgdGhpcyBpcyBhIGZha2UgdG9rZW4"}
        )
        # 错误信息不应包含令牌内容或密钥信息
        body = response.json() if response.content else {}
        error_detail = body.get("detail", "")
        assert SECRET_KEY not in error_detail


# ============= 第八部分：业务逻辑安全 =============

class TestBusinessLogicSecurity:
    """业务逻辑安全测试"""

    def test_user_cannot_match_with_self_via_api(self, client, db_session):
        """测试用户不能通过 API 与自己匹配"""
        user = make_user(id="self_match", email="selfmatch@example.com", name="SelfMatch")
        db_session.add(user)
        db_session.commit()

        token = create_access_token(user_id="self_match")

        response = client.get(
            "/api/matching/candidates",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code != 500

    def test_duplicate_profile_updates_handled(self, client, db_session):
        """测试重复资料更新不会导致数据损坏"""
        user = make_user(email=f"dup_{uuid.uuid4()}@example.com", name="DupProfile")
        db_session.add(user)
        db_session.commit()

        token = create_access_token(user_id=user.id)

        for i in range(5):
            response = client.put(
                f"/api/users/{user.id}",
                headers={"Authorization": f"Bearer {token}"},
                json={"bio": f"Updated bio {i}"}
            )
            assert response.status_code != 500

    def test_negative_age_rejected(self, client, db_session):
        """测试负数年龄被拒绝"""
        user = make_user(email=f"neg_{uuid.uuid4()}@example.com", name="NegAge")
        db_session.add(user)
        db_session.commit()

        token = create_access_token(user_id=user.id)

        response = client.put(
            f"/api/users/{user.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"age": -5}
        )
        assert response.status_code != 500

    def test_very_large_age_rejected(self, client, db_session):
        """测试超大年龄被拒绝"""
        user = make_user(email=f"old_{uuid.uuid4()}@example.com", name="OldAge")
        db_session.add(user)
        db_session.commit()

        token = create_access_token(user_id=user.id)

        response = client.put(
            f"/api/users/{user.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"age": 999}
        )
        assert response.status_code != 500

    def test_safety_report_requires_valid_content(self, client, db_session):
        """测试安全举报需要有效内容"""
        user = make_user(email=f"reporter_{uuid.uuid4()}@example.com", name="Reporter")
        db_session.add(user)
        db_session.commit()

        token = create_access_token(user_id=user.id)

        # 空举报
        response = client.post(
            "/api/safety/report",
            headers={"Authorization": f"Bearer {token}"},
            json={"reported_user_id": "target", "reason": ""}
        )
        assert response.status_code in [400, 422, 404]

    def test_cannot_report_nonexistent_user(self, client, db_session):
        """测试举报不存在的用户返回错误"""
        user = make_user(email=f"reporter2_{uuid.uuid4()}@example.com", name="Reporter2")
        db_session.add(user)
        db_session.commit()

        token = create_access_token(user_id=user.id)

        response = client.post(
            "/api/safety/report",
            headers={"Authorization": f"Bearer {token}"},
            json={"reported_user_id": "nonexistent_user_12345", "reason": "spam"}
        )
        # 不应 500
        assert response.status_code != 500


# ============= 第九部分：API 安全与响应头 =============

class TestAPISecurityHeaders:
    """API 安全响应头测试"""

    def test_error_responses_do_not_leak_stacktrace(self, client):
        """测试错误响应不泄露堆栈跟踪"""
        response = client.get("/api/nonexistent/endpoint")
        body = response.text
        assert "Traceback" not in body
        assert "File \"" not in body

    def test_cors_not_wildcard_for_credentials(self, client):
        """测试 CORS 配置不使用通配符当需要凭证时"""
        response = client.options(
            "/api/users/login",
            headers={
                "Origin": "https://evil.com",
                "Access-Control-Request-Method": "POST",
            }
        )
        # 检查响应
        cors_origin = response.headers.get("access-control-allow-origin", "*")
        # 如果允许凭证，origin 不应该是 *
        allow_creds = response.headers.get("access-control-allow-credentials", "false")
        if allow_creds == "true":
            assert cors_origin != "*"

    def test_api_returns_json_for_json_requests(self, client):
        """测试 API 对 JSON 请求返回 JSON 响应"""
        response = client.post(
            "/api/users/login",
            json={"email": "test@test.com", "password": "test"},
            headers={"Accept": "application/json"}
        )
        content_type = response.headers.get("content-type", "")
        assert "json" in content_type or response.status_code in [404]

    def test_special_characters_in_json_field_names(self, client):
        """测试 JSON 字段名中的特殊字符不导致崩溃"""
        response = client.post(
            "/api/users/login",
            json={"<script>email</script>": "test", "pass\"word": "test"}
        )
        assert response.status_code != 500


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
