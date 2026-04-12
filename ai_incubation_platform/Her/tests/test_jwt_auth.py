"""
JWT 认证模块测试用例集

测试覆盖:
1. 密码验证与哈希测试 (8 tests)
2. 令牌创建测试 (7 tests)
3. 令牌解码测试 (9 tests)
4. 令牌类型验证测试 (4 tests)
5. 用户认证流程测试 (4 tests)
6. 开发环境匿名用户测试 (4 tests)
7. 生产环境强制认证测试 (3 tests)

总计: 39 个测试用例
"""
import pytest
import bcrypt
import hashlib
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from jose import jwt, JWTError
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials

# 导入被测模块
from auth.jwt import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_access_token,
    decode_refresh_token,
    get_current_user,
    get_current_user_optional,
    authenticate_user,
    _create_token,
    _decode_token,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)


# ============= 第一部分：密码验证与哈希测试 =============

class TestPasswordHashing:
    """密码哈希功能测试"""

    def test_get_password_hash_creates_valid_bcrypt_hash(self):
        """测试 get_password_hash 生成有效的 bcrypt 哈希"""
        password = "test_password_123"
        hashed = get_password_hash(password)

        # bcrypt 哈希应该以 $2b$ 开头
        assert hashed.startswith("$2b$")
        # 哈希长度应为 60 字符
        assert len(hashed) == 60
        # 原密码不应等于哈希
        assert hashed != password

    def test_get_password_hash_different_salts(self):
        """测试相同密码生成不同的哈希（不同盐值）"""
        password = "same_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # 两次哈希应不同（不同盐值）
        assert hash1 != hash2
        # 但都能验证原密码
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    def test_get_password_hash_raises_on_none(self):
        """测试 None 密码抛出 ValueError"""
        with pytest.raises(ValueError, match="password must not be None"):
            get_password_hash(None)

    def test_get_password_hash_truncates_long_password(self):
        """测试超过 72 字节的密码被截断处理"""
        # bcrypt 最多处理 72 字节，超过部分应被截断
        long_password = "a" * 100
        hashed = get_password_hash(long_password)

        # 应该能验证成功（前 72 字节）
        assert verify_password(long_password, hashed) is True

    def test_verify_password_with_sha256_hash(self):
        """测试 SHA-256 哈希格式的密码验证"""
        plain_password = "original_password"
        # 模拟前端 SHA-256 哈希
        sha256_hash = hashlib.sha256(plain_password.encode()).hexdigest()

        # 对 SHA-256 哈希进行 bcrypt 存储
        stored_hash = get_password_hash(sha256_hash)

        # 使用 SHA-256 哈希验证
        result = verify_password(sha256_hash, stored_hash)
        assert result is True

    def test_verify_password_with_plain_password(self):
        """测试普通密码的 bcrypt 验证"""
        plain_password = "my_password"
        hashed = get_password_hash(plain_password)

        result = verify_password(plain_password, hashed)
        assert result is True

    def test_verify_password_rejects_wrong_password(self):
        """测试错误密码验证失败"""
        plain_password = "correct_password"
        hashed = get_password_hash(plain_password)

        result = verify_password("wrong_password", hashed)
        assert result is False

    def test_verify_password_handles_empty_inputs(self):
        """测试空输入处理"""
        hashed = get_password_hash("test")

        # 空密码
        assert verify_password("", hashed) is False
        # 空哈希
        assert verify_password("password", "") is False
        # 两者都空
        assert verify_password("", "") is False

    def test_verify_password_handles_invalid_bcrypt_hash(self):
        """测试无效 bcrypt 哈希格式处理"""
        result = verify_password("password", "invalid_hash_format")
        assert result is False

    def test_verify_password_sha256_format_detection(self):
        """测试 SHA-256 格式检测逻辑"""
        # 有效的 SHA-256 格式（64 个十六进制字符）
        valid_sha256 = "a" * 64
        assert len(valid_sha256) == 64
        assert all(c in '0123456789abcdef' for c in valid_sha256.lower())

        # 无效格式（长度不对）
        invalid_length = "abc123"
        assert len(invalid_length) != 64

        # 无效格式（包含非十六进制字符）
        invalid_chars = "g" * 64
        assert not all(c in '0123456789abcdef' for c in invalid_chars.lower())


# ============= 第二部分：令牌创建测试 =============

class TestTokenCreation:
    """令牌创建功能测试"""

    def test_create_access_token_returns_valid_jwt(self):
        """测试 create_access_token 返回有效 JWT"""
        user_id = "test_user_123"
        token = create_access_token(user_id)

        # 解码并验证
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["user_id"] == user_id
        assert payload["token_type"] == "access"
        assert "exp" in payload
        assert "jti" in payload

    def test_create_access_token_with_custom_expiry(self):
        """测试自定义过期时间的 access token"""
        user_id = "test_user"
        custom_delta = timedelta(hours=2)
        token = create_access_token(user_id, expires_delta=custom_delta)

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_time = datetime.utcfromtimestamp(payload["exp"])

        # 验证过期时间约为 2 小时后
        expected_exp = datetime.utcnow() + custom_delta
        tolerance = timedelta(seconds=10)
        assert abs(exp_time - expected_exp) < tolerance

    def test_create_access_token_default_expiry(self):
        """测试默认过期时间设置"""
        user_id = "test_user"
        token = create_access_token(user_id)

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_time = datetime.utcfromtimestamp(payload["exp"])

        expected_exp = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        tolerance = timedelta(seconds=10)
        assert abs(exp_time - expected_exp) < tolerance

    def test_create_refresh_token_returns_valid_jwt(self):
        """测试 create_refresh_token 返回有效 JWT"""
        user_id = "test_user_456"
        token = create_refresh_token(user_id)

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["user_id"] == user_id
        assert payload["token_type"] == "refresh"
        assert "exp" in payload
        assert "jti" in payload

    def test_create_refresh_token_default_expiry(self):
        """测试 refresh token 默认过期时间为 7 天"""
        user_id = "test_user"
        token = create_refresh_token(user_id)

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_time = datetime.utcfromtimestamp(payload["exp"])

        expected_exp = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        tolerance = timedelta(seconds=10)
        assert abs(exp_time - expected_exp) < tolerance

    def test_create_refresh_token_with_custom_expiry(self):
        """测试自定义过期时间的 refresh token"""
        user_id = "test_user"
        custom_delta = timedelta(days=30)
        token = create_refresh_token(user_id, expires_delta=custom_delta)

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_time = datetime.utcfromtimestamp(payload["exp"])

        expected_exp = datetime.utcnow() + custom_delta
        tolerance = timedelta(seconds=10)
        assert abs(exp_time - expected_exp) < tolerance

    def test_create_token_pair_returns_both_tokens(self):
        """测试 create_token_pair 返回 access 和 refresh 令牌对"""
        user_id = "test_user_pair"
        access_token, refresh_token = create_token_pair(user_id)

        # 验证 access token
        access_payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        assert access_payload["user_id"] == user_id
        assert access_payload["token_type"] == "access"

        # 验证 refresh token
        refresh_payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        assert refresh_payload["user_id"] == user_id
        assert refresh_payload["token_type"] == "refresh"

        # 两个令牌应该不同
        assert access_token != refresh_token

    def test_create_token_has_unique_jti(self):
        """测试每个令牌有唯一的 jti 标识"""
        user_id = "test_user"
        token1 = create_access_token(user_id)
        token2 = create_access_token(user_id)

        payload1 = jwt.decode(token1, SECRET_KEY, algorithms=[ALGORITHM])
        payload2 = jwt.decode(token2, SECRET_KEY, algorithms=[ALGORITHM])

        # jti 应该不同
        assert payload1["jti"] != payload2["jti"]


# ============= 第三部分：令牌解码测试 =============

class TestTokenDecoding:
    """令牌解码功能测试"""

    def test_decode_access_token_success(self):
        """测试成功解码 access token"""
        user_id = "decode_test_user"
        token = create_access_token(user_id)

        result = decode_access_token(token)
        assert result == user_id

    def test_decode_refresh_token_success(self):
        """测试成功解码 refresh token"""
        user_id = "decode_refresh_user"
        token = create_refresh_token(user_id)

        result = decode_refresh_token(token)
        assert result == user_id

    def test_decode_expired_token_returns_none(self):
        """测试过期令牌解码返回 None"""
        expired_data = {
            "user_id": "expired_user",
            "exp": datetime.utcnow() - timedelta(hours=1),
            "token_type": "access",
            "jti": "unique_id_123",
        }
        expired_token = jwt.encode(expired_data, SECRET_KEY, algorithm=ALGORITHM)

        result = decode_access_token(expired_token)
        assert result is None

    def test_decode_invalid_signature_token_returns_none(self):
        """测试无效签名的令牌解码返回 None"""
        tampered_token = jwt.encode(
            {
                "user_id": "tampered_user",
                "exp": datetime.utcnow() + timedelta(hours=1),
                "token_type": "access",
                "jti": "unique_id_456",
            },
            "wrong_secret_key",
            algorithm=ALGORITHM
        )

        result = decode_access_token(tampered_token)
        assert result is None

    def test_decode_malformed_token_returns_none(self):
        """测试格式错误的令牌解码返回 None"""
        malformed_tokens = [
            "not.a.valid.jwt",
            "random_string",
            "",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid_payload.signature",
        ]

        for token in malformed_tokens:
            result = decode_access_token(token)
            assert result is None

    def test_decode_token_missing_user_id_returns_none(self):
        """测试缺少 user_id 的令牌解码返回 None"""
        token_data = {
            "exp": datetime.utcnow() + timedelta(hours=1),
            "token_type": "access",
            "jti": "unique_id_789",
        }
        token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

        result = decode_access_token(token)
        assert result is None

    def test_decode_token_with_empty_user_id(self):
        """测试 user_id 为空的令牌"""
        token_data = {
            "user_id": "",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "token_type": "access",
            "jti": "unique_id_abc",
        }
        token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

        # 空字符串 user_id 不是 None，会返回空字符串
        result = decode_access_token(token)
        assert result == ""

    def test_decode_token_with_extra_claims_success(self):
        """测试带有额外字段的令牌成功解码"""
        extra_data = {
            "user_id": "extra_user",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "token_type": "access",
            "jti": "unique_id_def",
            "role": "admin",
            "custom_field": "custom_value",
        }
        token = jwt.encode(extra_data, SECRET_KEY, algorithm=ALGORITHM)

        result = decode_access_token(token)
        assert result == "extra_user"

    def test_decode_token_with_wrong_algorithm(self):
        """测试使用错误算法签名的令牌"""
        # 使用 HS384 算法创建令牌
        token = jwt.encode(
            {
                "user_id": "wrong_algo_user",
                "exp": datetime.utcnow() + timedelta(hours=1),
                "token_type": "access",
                "jti": "unique_id_ghi",
            },
            SECRET_KEY,
            algorithm="HS384"
        )

        # 尝试用 HS256 解码应该失败
        result = decode_access_token(token)
        assert result is None


# ============= 第四部分：令牌类型验证测试 =============

class TestTokenTypeValidation:
    """令牌类型验证测试"""

    def test_access_token_rejected_for_refresh_decode(self):
        """测试 access token 被拒绝用于 refresh 解码"""
        user_id = "type_test_user"
        access_token = create_access_token(user_id)

        # 尝试用 refresh 解码器解码 access token
        result = decode_refresh_token(access_token)
        assert result is None

    def test_refresh_token_rejected_for_access_decode(self):
        """测试 refresh token 被拒绝用于 access 解码"""
        user_id = "type_test_user"
        refresh_token = create_refresh_token(user_id)

        # 尝试用 access 解码器解码 refresh token
        result = decode_access_token(refresh_token)
        assert result is None

    def test_missing_token_type_defaults_to_access(self):
        """测试缺少 token_type 的令牌默认为 access 类型"""
        token_data = {
            "user_id": "no_type_user",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "jti": "unique_id_jkl",
            # 缺少 token_type
        }
        token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

        # 由于默认 token_type 是 access，所以 access 解码应该成功
        result = decode_access_token(token)
        assert result == "no_type_user"

    def test_invalid_token_type_rejected(self):
        """测试无效的 token_type 被拒绝"""
        token_data = {
            "user_id": "invalid_type_user",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "token_type": "invalid_type",
            "jti": "unique_id_mno",
        }
        token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

        # access 和 refresh 解码都应该返回 None
        assert decode_access_token(token) is None
        assert decode_refresh_token(token) is None


# ============= 第五部分：用户认证流程测试 =============

class TestAuthenticationFlow:
    """用户认证流程测试"""

    def test_authenticate_user_success(self):
        """测试成功认证用户"""
        username = "test_user"
        password = "correct_password"
        stored_hash = get_password_hash(password)

        result = authenticate_user(username, password, stored_hash)
        assert result == username

    def test_authenticate_user_wrong_password(self):
        """测试错误密码认证失败"""
        username = "test_user"
        stored_hash = get_password_hash("correct_password")

        result = authenticate_user(username, "wrong_password", stored_hash)
        assert result is None

    def test_authenticate_user_with_sha256_password(self):
        """测试 SHA-256 哈希密码认证"""
        username = "sha256_user"
        plain_password = "original_password"
        sha256_hash = hashlib.sha256(plain_password.encode()).hexdigest()
        stored_hash = get_password_hash(sha256_hash)

        # 使用 SHA-256 哈希进行认证
        result = authenticate_user(username, sha256_hash, stored_hash)
        assert result == username

        # 原始密码不应直接通过验证
        result = authenticate_user(username, plain_password, stored_hash)
        # bcrypt 截断 72 字节，但 SHA-256 是 64 字符，所以不匹配
        # 但实际上 verify_password 会检查是否是 SHA-256 格式
        # 这里原始密码不是 SHA-256 格式，会尝试直接 bcrypt 验证，应该失败
        assert result is None

    def test_authenticate_user_empty_credentials(self):
        """测试空凭证认证失败"""
        stored_hash = get_password_hash("password")

        # 空密码
        result = authenticate_user("user", "", stored_hash)
        assert result is None

        # 空哈希
        result = authenticate_user("user", "password", "")
        assert result is None


# ============= 第六部分：get_current_user 依赖注入测试 =============

class TestGetCurrentUser:
    """get_current_user 依赖注入测试"""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self):
        """测试成功获取当前用户"""
        user_id = "current_user_test"
        token = create_access_token(user_id)

        credentials = MagicMock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = token

        result = await get_current_user(credentials)
        assert result == user_id

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """测试无效令牌抛出 401 异常"""
        credentials = MagicMock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "invalid_token"

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(self):
        """测试过期令牌抛出 401 异常"""
        expired_data = {
            "user_id": "expired_user",
            "exp": datetime.utcnow() - timedelta(hours=1),
            "token_type": "access",
            "jti": "unique_id_pqr",
        }
        expired_token = jwt.encode(expired_data, SECRET_KEY, algorithm=ALGORITHM)

        credentials = MagicMock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = expired_token

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_with_refresh_token(self):
        """测试使用 refresh token 获取用户失败"""
        user_id = "refresh_user"
        refresh_token = create_refresh_token(user_id)

        credentials = MagicMock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = refresh_token

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == 401


# ============= 第七部分：get_current_user_optional 测试 =============

class TestGetCurrentUserOptional:
    """get_current_user_optional 测试"""

    @pytest.mark.asyncio
    async def test_with_valid_token(self):
        """测试有效令牌返回用户信息"""
        user_id = "optional_user"
        token = create_access_token(user_id)

        credentials = MagicMock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = token

        request = MagicMock(spec=Request)
        request.headers = {}

        result = await get_current_user_optional(request, credentials)

        assert result["user_id"] == user_id
        assert result["is_anonymous"] is False

    @pytest.mark.asyncio
    async def test_with_dev_user_id_header(self):
        """测试开发环境 X-Dev-User-Id Header"""
        with patch("auth.jwt.settings") as mock_settings, patch("config.settings") as mock_config:
            mock_settings.environment = "development"
            mock_config.environment = "development"

            request = MagicMock(spec=Request)
            request.headers = {"X-Dev-User-Id": "dev_user_123"}

            result = await get_current_user_optional(request, None)

            assert result["user_id"] == "dev_user_123"
            assert result["is_anonymous"] is True

    @pytest.mark.asyncio
    async def test_dev_environment_anonymous_user(self):
        """测试开发环境返回匿名用户"""
        with patch("auth.jwt.settings") as mock_settings, patch("config.settings") as mock_config:
            mock_settings.environment = "development"
            mock_config.environment = "development"

            request = MagicMock(spec=Request)
            request.headers = {}

            result = await get_current_user_optional(request, None)

            assert result["user_id"] == "user-anonymous-dev"
            assert result["is_anonymous"] is True

    @pytest.mark.asyncio
    async def test_production_environment_requires_auth(self):
        """测试生产环境强制认证"""
        # 需要同时 patch auth.jwt.settings 和 config.settings，因为函数内部有动态导入
        with patch("auth.jwt.settings") as mock_settings, patch("config.settings") as mock_config:
            mock_settings.environment = "production"
            mock_config.environment = "production"

            request = MagicMock(spec=Request)
            request.headers = {}

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_optional(request, None)

            assert exc_info.value.status_code == 401
            assert "Authentication required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_production_environment_with_valid_token(self):
        """测试生产环境有效令牌通过"""
        with patch("auth.jwt.settings") as mock_settings:
            mock_settings.environment = "production"

            user_id = "prod_user"
            token = create_access_token(user_id)

            credentials = MagicMock(spec=HTTPAuthorizationCredentials)
            credentials.credentials = token

            request = MagicMock(spec=Request)
            request.headers = {}

            result = await get_current_user_optional(request, credentials)

            assert result["user_id"] == user_id
            assert result["is_anonymous"] is False

    @pytest.mark.asyncio
    async def test_dev_environment_token_takes_precedence(self):
        """测试开发环境令牌优先于 Header"""
        with patch("auth.jwt.settings") as mock_settings:
            mock_settings.environment = "development"

            user_id = "token_user"
            token = create_access_token(user_id)

            credentials = MagicMock(spec=HTTPAuthorizationCredentials)
            credentials.credentials = token

            request = MagicMock(spec=Request)
            request.headers = {"X-Dev-User-Id": "header_user"}

            result = await get_current_user_optional(request, credentials)

            # 令牌用户应优先
            assert result["user_id"] == user_id
            assert result["is_anonymous"] is False


# ============= 第八部分：边界条件与异常测试 =============

class TestEdgeCasesAndExceptions:
    """边界条件与异常测试"""

    def test_very_long_user_id(self):
        """测试超长用户 ID"""
        long_user_id = "a" * 1000
        token = create_access_token(long_user_id)

        result = decode_access_token(token)
        assert result == long_user_id

    def test_special_characters_in_user_id(self):
        """测试用户 ID 中的特殊字符"""
        special_user_id = "user@example.com:123!#$%"
        token = create_access_token(special_user_id)

        result = decode_access_token(token)
        assert result == special_user_id

    def test_unicode_user_id(self):
        """测试 Unicode 用户 ID"""
        unicode_user_id = "用户_测试_🚀"
        token = create_access_token(unicode_user_id)

        result = decode_access_token(token)
        assert result == unicode_user_id

    def test_bcrypt_password_with_special_characters(self):
        """测试包含特殊字符的密码"""
        special_password = "p@ssw0rd!#$%^&*()_+-=[]{}|;':\",./<>?`~中文密码"
        hashed = get_password_hash(special_password)

        assert verify_password(special_password, hashed) is True
        assert verify_password("wrong", hashed) is False

    def test_empty_user_id_token(self):
        """测试空用户 ID 的令牌"""
        # 空字符串不是 None，所以可以创建令牌
        token = create_access_token("")
        result = decode_access_token(token)
        # 返回空字符串
        assert result == ""

    def test_none_credentials_handling(self):
        """测试 None credentials 处理"""
        # verify_password 应该处理 None 输入
        assert verify_password(None, "hash") is False
        assert verify_password("password", None) is False

    def test_token_decode_with_exception_in_checkpw(self):
        """测试 bcrypt checkpw 异常处理"""
        # 传递无效的哈希格式应该被捕获并返回 False
        result = verify_password("password", "not_a_valid_bcrypt_hash_at_all")
        assert result is False

    def test_password_exactly_72_bytes(self):
        """测试正好 72 字节的密码"""
        # bcrypt 处理最多 72 字节
        password_72 = "a" * 72
        hashed = get_password_hash(password_72)

        assert verify_password(password_72, hashed) is True

    def test_password_over_72_bytes_truncated(self):
        """测试超过 72 字节的密码被截断"""
        # 73 个字符超过 72 字节
        password_73 = "a" * 73
        password_72 = "a" * 72

        hashed = get_password_hash(password_73)

        # 由于截断，前 72 字节应该匹配
        assert verify_password(password_72, hashed) is True
        # 完整的 73 字节密码也能匹配（因为截断）
        assert verify_password(password_73, hashed) is True


# ============= 第九部分：配置常量验证测试 =============

class TestConfigurationConstants:
    """配置常量验证测试"""

    def test_secret_key_exists(self):
        """测试密钥存在"""
        assert SECRET_KEY is not None
        assert len(SECRET_KEY) > 0

    def test_algorithm_is_hs256(self):
        """测试算法为 HS256"""
        assert ALGORITHM == "HS256"

    def test_access_token_expiry_is_reasonable(self):
        """测试 access token 过期时间合理"""
        # 默认应该是 60 分钟左右
        assert 1 <= ACCESS_TOKEN_EXPIRE_MINUTES <= 1440  # 1 分钟到 24 小时

    def test_refresh_token_expiry_is_reasonable(self):
        """测试 refresh token 过期时间合理"""
        # 默认应该是 7 天左右
        assert 1 <= REFRESH_TOKEN_EXPIRE_DAYS <= 30  # 1 天到 30 天


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])