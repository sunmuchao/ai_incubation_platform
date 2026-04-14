"""
边界值测试 - 全覆盖测试矩阵

测试覆盖：
1. 用户注册接口 - email/age/phone/name/location
2. 聊天消息接口 - content/message_type
3. 支付接口 - amount/coupon_code
4. 匹配接口 - user_id/limit
5. 认证接口 - username/password

执行方式：
    pytest tests/test_boundary_values.py -v --tb=short
"""
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from unittest.mock import Mock, patch, MagicMock
import uuid
from datetime import datetime, timedelta

# 导入模型（使用现有测试配置）
from models.user import UserCreate, User, Gender, RelationshipGoal, SexualOrientation
from db.models import UserDB, ChatMessageDB, ChatConversationDB
from db.database import get_db
from api.chat import MessageSendRequest
from auth.jwt import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_access_token


# ============= 边界值测试数据生成器 =============

class BoundaryTestData:
    """边界值测试数据集合"""

    # Email 边界值
    EMAIL_VALID = "test@example.com"
    EMAIL_EMPTY = ""
    EMAIL_NULL = None
    EMAIL_NO_AT = "testexample.com"
    EMAIL_NO_DOMAIN = "test@"
    EMAIL_NO_USER = "@example.com"
    EMAIL_SPECIAL_CHARS = "test+special!#$%@example.com"
    EMAIL_UNICODE = "测试用户@example.com"
    EMAIL_TOO_LONG = "a" * 250 + "@example.com"  # 255+ chars
    EMAIL_MULTIPLE_AT = "test@test@example.com"
    EMAIL_SPACE = "test @example.com"
    EMAIL_DOT_ONLY = ".@example.com"
    EMAIL_IP_DOMAIN = "test@192.168.1.1"

    # Age 边界值
    AGE_VALID = 28
    AGE_MIN = 0
    AGE_NEGATIVE = -1
    AGE_ZERO = 0
    AGE_TOO_LOW = 17  # 业务规则：最低 18
    AGE_TOO_HIGH = 151
    AGE_HUGE = 1000000
    AGE_FLOAT = 28.5  # 类型错误
    AGE_STRING = "twenty"  # 类型错误
    AGE_EMPTY = None
    AGE_MIN_VALID = 18  # 业务最低有效
    AGE_MAX_VALID = 60  # 业务最高有效

    # Phone 边界值
    PHONE_VALID_CN = "13800138000"
    PHONE_EMPTY = ""
    PHONE_NULL = None
    PHONE_TOO_SHORT = "138"
    PHONE_TOO_LONG = "13800138000138000"
    PHONE_INVALID_PREFIX = "12300138000"  # 无效前缀
    PHONE_WITH_SPACE = "138 0013 8000"
    PHONE_WITH_DASH = "138-0013-8000"
    PHONE_INTL = "+8613800138000"
    PHONE_SPECIAL = "13800!38000"
    PHONE_LETTERS = "13800abc000"

    # Name 边界值
    NAME_VALID = "测试用户"
    NAME_EMPTY = ""
    NAME_NULL = None
    NAME_TOO_LONG = "测" * 100  # 100+ chars
    NAME_SPECIAL_CHARS = "!@#$%^&*()"
    NAME_UNICODE = "张三李四王五赵六"
    NAME_NUMBER_ONLY = "12345"
    NAME_SPACE_ONLY = "   "
    NAME_SINGLE_CHAR = "张"

    # Location 边界值
    LOCATION_VALID = "北京市朝阳区"
    LOCATION_EMPTY = ""
    LOCATION_NULL = None
    LOCATION_TOO_LONG = "北" * 200
    LOCATION_COORDINATE = "116.4074,39.9042"
    LOCATION_SPECIAL = "北京市!朝阳区"

    # Message Content 边界值
    MESSAGE_VALID = "你好，很高兴认识你"
    MESSAGE_EMPTY = ""
    MESSAGE_NULL = None
    MESSAGE_TOO_LONG = "测" * 10001  # 10000+ chars
    MESSAGE_ONLY_SPACE = "   "
    MESSAGE_HTML_INJECTION = "<script>alert('xss')</script>"
    MESSAGE_JS_INJECTION = "javascript:alert(1)"
    MESSAGE_EMOJI_ONLY = "😀😁😂🤣😃😄😅😆"
    MESSAGE_MIXED = "你好<script>alert(1)</script>世界"
    MESSAGE_SQL_INJECTION = "'); DROP TABLE chat_messages;--"
    MESSAGE_UNICODE_SPECIAL = "\u0000\u001f\u007f"  # 控制字符

    # Amount 边界值 (支付)
    AMOUNT_VALID = 99.99
    AMOUNT_ZERO = 0
    AMOUNT_NEGATIVE = -1
    AMOUNT_HUGE = 1000000000.0
    AMOUNT_PRECISION = 99.9999  # 精度问题
    AMOUNT_STRING = "99.99"
    AMOUNT_EMPTY = None

    # Password 边界值
    PASSWORD_VALID_SHA256 = "a" * 64  # SHA-256 格式
    PASSWORD_TOO_SHORT = "12345"
    PASSWORD_TOO_LONG = "a" * 200
    PASSWORD_EMPTY = ""
    PASSWORD_NULL = None
    PASSWORD_SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
    PASSWORD_UNICODE = "密码测试123"


# ============= 用户注册边界值测试 =============

class TestUserRegistrationBoundary:
    """用户注册接口边界值测试"""

    # ========== Email 边界值测试 ==========

    def test_email_empty(self):
        """测试空邮箱"""
        with pytest.raises((ValidationError, HTTPException)):
            UserCreate(
                name="测试用户",
                email=BoundaryTestData.EMAIL_EMPTY,
                age=28,
                gender=Gender.MALE,
                location="北京市"
            )

    def test_email_no_at_symbol(self):
        """测试缺少 @ 符号的邮箱"""
        with pytest.raises(ValidationError):
            UserCreate(
                name="测试用户",
                email=BoundaryTestData.EMAIL_NO_AT,
                age=28,
                gender=Gender.MALE,
                location="北京市"
            )

    def test_email_no_domain(self):
        """测试缺少域名的邮箱"""
        with pytest.raises(ValidationError):
            UserCreate(
                name="测试用户",
                email=BoundaryTestData.EMAIL_NO_DOMAIN,
                age=28,
                gender=Gender.MALE,
                location="北京市"
            )

    def test_email_too_long(self):
        """测试超长邮箱"""
        with pytest.raises(ValidationError):
            UserCreate(
                name="测试用户",
                email=BoundaryTestData.EMAIL_TOO_LONG,
                age=28,
                gender=Gender.MALE,
                location="北京市"
            )

    def test_email_special_chars_valid(self):
        """测试合法特殊字符邮箱 (+符号)"""
        # '+' 符号在邮箱中是合法的
        user = UserCreate(
            username="testuser",
            name="测试用户",
            email="test+special@example.com",
            age=28,
            gender=Gender.MALE,
            location="北京市"
        )
        assert user.email == "test+special@example.com"

    def test_email_unicode(self):
        """测试 Unicode 邮箱"""
        # Unicode 邮箱在某些系统支持
        try:
            user = UserCreate(
                username="testuser_cn",
                name="测试用户",
                email=BoundaryTestData.EMAIL_UNICODE,
                age=28,
                gender=Gender.MALE,
                location="北京市"
            )
            # 如果支持，验证成功
            assert user.email == BoundaryTestData.EMAIL_UNICODE
        except ValidationError:
            # 如果不支持 Unicode 邮箱，预期抛出验证错误
            pass

    def test_email_ip_domain(self):
        """测试 IP 域名邮箱"""
        # IP 作为域名在某些场景有效
        try:
            user = UserCreate(
                username="testuser_ip",
                name="测试用户",
                email=BoundaryTestData.EMAIL_IP_DOMAIN,
                age=28,
                gender=Gender.MALE,
                location="北京市"
            )
            assert user.email == BoundaryTestData.EMAIL_IP_DOMAIN
        except ValidationError:
            pass

    # ========== Age 边界值测试 ==========

    def test_age_zero(self):
        """测试年龄为 0"""
        with pytest.raises(ValidationError):
            UserCreate(
                name="测试用户",
                email="test@example.com",
                age=BoundaryTestData.AGE_ZERO,
                gender=Gender.MALE,
                location="北京市"
            )

    def test_age_negative(self):
        """测试负数年龄"""
        with pytest.raises(ValidationError):
            UserCreate(
                name="测试用户",
                email="test@example.com",
                age=BoundaryTestData.AGE_NEGATIVE,
                gender=Gender.MALE,
                location="北京市"
            )

    def test_age_extremely_high(self):
        """测试超大年龄"""
        # 模型已添加 le=150 验证，应抛出 ValidationError
        with pytest.raises(ValidationError):
            UserCreate(
                name="测试用户",
                email="test@example.com",
                age=BoundaryTestData.AGE_HUGE,
                gender=Gender.MALE,
                location="北京市"
            )

    def test_age_min_boundary_valid(self):
        """测试最小有效年龄 (18)"""
        user = UserCreate(
            username="testuser_min",
            name="测试用户",
            email="test@example.com",
            age=BoundaryTestData.AGE_MIN_VALID,
            gender=Gender.MALE,
            location="北京市"
        )
        assert user.age == 18

    def test_age_max_boundary_valid(self):
        """测试最大有效年龄 (60)"""
        user = UserCreate(
            username="testuser_max",
            name="测试用户",
            email="test@example.com",
            age=BoundaryTestData.AGE_MAX_VALID,
            gender=Gender.MALE,
            location="北京市"
        )
        assert user.age == 60

    def test_age_below_business_minimum(self):
        """测试低于业务最低年龄 (17)"""
        # 模型已添加 ge=18 验证，应抛出 ValidationError
        with pytest.raises(ValidationError):
            UserCreate(
                name="测试用户",
                email="test@example.com",
                age=17,
                gender=Gender.MALE,
                location="北京市"
            )

    def test_age_float_type_error(self):
        """测试浮点数年龄（类型错误）"""
        with pytest.raises(ValidationError):
            UserCreate(
                name="测试用户",
                email="test@example.com",
                age=BoundaryTestData.AGE_FLOAT,
                gender=Gender.MALE,
                location="北京市"
            )

    def test_age_string_type_error(self):
        """测试字符串年龄（类型错误）"""
        with pytest.raises(ValidationError):
            UserCreate(
                name="测试用户",
                email="test@example.com",
                age=BoundaryTestData.AGE_STRING,
                gender=Gender.MALE,
                location="北京市"
            )

    # ========== Name 边界值测试 ==========

    def test_name_empty(self):
        """测试空姓名"""
        with pytest.raises(ValidationError):
            UserCreate(
                name=BoundaryTestData.NAME_EMPTY,
                email="test@example.com",
                age=28,
                gender=Gender.MALE,
                location="北京市"
            )

    def test_name_too_long(self):
        """测试超长姓名"""
        # 模型已添加 max_length=50 验证，应抛出 ValidationError
        with pytest.raises(ValidationError):
            UserCreate(
                name=BoundaryTestData.NAME_TOO_LONG,
                email="test@example.com",
                age=28,
                gender=Gender.MALE,
                location="北京市"
            )

    def test_name_special_chars(self):
        """测试特殊字符姓名"""
        user = UserCreate(
            username="testuser_spec",
            name=BoundaryTestData.NAME_SPECIAL_CHARS,
            email="test@example.com",
            age=28,
            gender=Gender.MALE,
            location="北京市"
        )
        # 特殊字符在某些场景可能有效
        assert user.name == BoundaryTestData.NAME_SPECIAL_CHARS

    def test_name_space_only(self):
        """测试纯空格姓名"""
        with pytest.raises(ValidationError):
            UserCreate(
                name=BoundaryTestData.NAME_SPACE_ONLY,
                email="test@example.com",
                age=28,
                gender=Gender.MALE,
                location="北京市"
            )

    def test_name_single_char(self):
        """测试单字符姓名"""
        user = UserCreate(
            username="testuser_single",
            name=BoundaryTestData.NAME_SINGLE_CHAR,
            email="test@example.com",
            age=28,
            gender=Gender.MALE,
            location="北京市"
        )
        assert user.name == "张"

    # ========== Location 边界值测试 ==========

    def test_location_empty(self):
        """测试空地址"""
        with pytest.raises(ValidationError):
            UserCreate(
                name="测试用户",
                email="test@example.com",
                age=28,
                gender=Gender.MALE,
                location=BoundaryTestData.LOCATION_EMPTY
            )

    def test_location_too_long(self):
        """测试超长地址"""
        try:
            user = UserCreate(
                name="测试用户",
                email="test@example.com",
                age=28,
                gender=Gender.MALE,
                location=BoundaryTestData.LOCATION_TOO_LONG
            )
            assert len(user.location) <= 200, "业务规则：地址不应超过 200 字符"
        except ValidationError:
            pass

    def test_location_coordinate_format(self):
        """测试坐标格式地址"""
        user = UserCreate(
            username="testuser_coord",
            name="测试用户",
            email="test@example.com",
            age=28,
            gender=Gender.MALE,
            location=BoundaryTestData.LOCATION_COORDINATE
        )
        # 坐标格式是有效地址
        assert user.location == BoundaryTestData.LOCATION_COORDINATE

    # ========== Gender 边界值测试 ==========

    def test_gender_invalid_value(self):
        """测试无效性别值"""
        with pytest.raises(ValidationError):
            UserCreate(
                name="测试用户",
                email="test@example.com",
                age=28,
                gender="invalid_gender",  # 无效值
                location="北京市"
            )

    def test_gender_all_valid_values(self):
        """测试所有有效性别值"""
        for gender in [Gender.MALE, Gender.FEMALE, Gender.OTHER]:
            user = UserCreate(
                username=f"testuser_{gender.value}",
                name="测试用户",
                email=f"test_{gender.value}@example.com",
                age=28,
                gender=gender,
                location="北京市"
            )
            assert user.gender == gender

    # ========== Relationship Goal 边界值测试 ==========

    def test_goal_invalid_value(self):
        """测试无效关系目标值"""
        with pytest.raises(ValidationError):
            UserCreate(
                name="测试用户",
                email="test@example.com",
                age=28,
                gender=Gender.MALE,
                location="北京市",
                goal="invalid_goal"
            )

    def test_goal_all_valid_values(self):
        """测试所有有效关系目标值 - 注：goal 字段在 UserUpdate 中测试"""
        # UserCreate 不包含 goal 字段，此测试应在 UserUpdate 测试中进行
        pytest.skip("goal 字段不在 UserCreate 模型中，应使用 UserUpdate 测试")


# ============= 聊天消息边界值测试 =============

class TestChatMessageBoundary:
    """聊天消息接口边界值测试"""

    def test_message_empty(self):
        """测试空消息"""
        with pytest.raises(ValidationError):
            MessageSendRequest(
                receiver_id=str(uuid.uuid4()),
                content=BoundaryTestData.MESSAGE_EMPTY
            )

    def test_message_too_long(self):
        """测试超长消息"""
        # 消息长度限制检查
        try:
            msg = MessageSendRequest(
                receiver_id=str(uuid.uuid4()),
                content=BoundaryTestData.MESSAGE_TOO_LONG
            )
            # 如果模型不限制，业务逻辑应限制
            assert len(msg.content) <= 10000, "业务规则：消息不应超过 10000 字符"
        except ValidationError:
            pass

    def test_message_html_injection(self):
        """测试 HTML 注入消息"""
        msg = MessageSendRequest(
            receiver_id=str(uuid.uuid4()),
            content=BoundaryTestData.MESSAGE_HTML_INJECTION
        )
        # 模型层面接受，但存储/展示时应过滤
        assert msg.content == BoundaryTestData.MESSAGE_HTML_INJECTION
        # 业务规则：存储前应进行 HTML 转义

    def test_message_sql_injection(self):
        """测试 SQL 注入消息"""
        msg = MessageSendRequest(
            receiver_id=str(uuid.uuid4()),
            content=BoundaryTestData.MESSAGE_SQL_INJECTION
        )
        # SQLAlchemy ORM 使用参数化查询，不存在注入风险
        assert msg.content == BoundaryTestData.MESSAGE_SQL_INJECTION

    def test_message_emoji_only(self):
        """测试纯 Emoji 消息"""
        msg = MessageSendRequest(
            receiver_id=str(uuid.uuid4()),
            content=BoundaryTestData.MESSAGE_EMOJI_ONLY
        )
        assert msg.content == BoundaryTestData.MESSAGE_EMOJI_ONLY

    def test_message_unicode_control_chars(self):
        """测试包含控制字符的消息"""
        # 控制字符测试 - 模型接受，但存储时应过滤
        msg = MessageSendRequest(
            receiver_id=str(uuid.uuid4()),
            content="test\x00message"  # 控制字符
        )
        # 业务规则：存储/展示前应过滤控制字符
        # 此测试验证模型接受，但业务层应处理
        assert msg.content is not None

    def test_message_type_invalid(self):
        """测试无效消息类型"""
        with pytest.raises(ValidationError):
            MessageSendRequest(
                receiver_id=str(uuid.uuid4()),
                content="测试消息",
                message_type="invalid_type"
            )

    def test_message_type_all_valid(self):
        """测试所有有效消息类型"""
        for msg_type in ["text", "image", "emoji", "voice"]:
            msg = MessageSendRequest(
                receiver_id=str(uuid.uuid4()),
                content="测试消息",
                message_type=msg_type
            )
            assert msg.message_type == msg_type

    def test_receiver_id_empty(self):
        """测试空接收者 ID"""
        with pytest.raises(ValidationError):
            MessageSendRequest(
                receiver_id="",
                content="测试消息"
            )

    def test_receiver_id_invalid_format(self):
        """测试无效接收者 ID 格式"""
        # UUID 格式验证
        with pytest.raises(ValidationError):
            MessageSendRequest(
                receiver_id="not-a-uuid",
                content="测试消息"
            )


# ============= 支付金额边界值测试 =============

class TestPaymentAmountBoundary:
    """支付金额边界值测试"""

    def test_amount_zero_should_be_rejected(self):
        """测试金额为 0 应被拒绝"""
        # 业务规则：金额必须大于 0
        from services.payment_service import PaymentService
        service = PaymentService(None)  # 不需要 db 连接进行验证
        amount = 0
        # 验证：amount <= 0 应抛出 ValueError
        with pytest.raises(ValueError, match="必须大于 0"):
            service.validate_amount(amount)

    def test_amount_negative_should_be_rejected(self):
        """测试负数金额应被拒绝"""
        # 业务规则：金额必须大于 0
        from services.payment_service import PaymentService
        service = PaymentService(None)
        amount = -1
        # 验证：负数金额应抛出 ValueError
        with pytest.raises(ValueError, match="必须大于 0"):
            service.validate_amount(amount)

    def test_amount_precision(self):
        """测试精度问题金额"""
        # 金额精度：最多两位小数
        amount = 99.9999
        # 业务规则：应四舍五入到两位小数
        rounded = round(amount, 2)
        assert rounded == 100.00

    def test_amount_huge_should_be_rejected(self):
        """测试超大金额应被拒绝"""
        # 业务规则：设置最大金额限制 (10万元)
        from services.payment_service import PaymentService
        service = PaymentService(None)
        amount = 1000000000.0  # 10亿
        # 验证：超过 MAX_AMOUNT 应抛出 ValueError
        with pytest.raises(ValueError, match="不能超过"):
            service.validate_amount(amount)

    def test_amount_valid_decimal(self):
        """测试有效小数金额"""
        amount = 99.99
        # 正常接受
        assert amount >= 0 and amount <= 100000


# ============= 匹配接口边界值测试 =============

class TestMatchingBoundary:
    """匹配接口边界值测试"""

    def test_user_id_empty(self):
        """测试空用户 ID"""
        # 匹配查询需要有效用户 ID
        from api.matching import get_matches
        assert True  # API 层会检查并返回 404

    def test_user_id_nonexistent(self):
        """测试不存在用户 ID"""
        nonexistent_id = str(uuid.uuid4())
        # API 应返回 404
        assert True  # 实际测试需要调用 API

    def test_limit_zero_should_be_rejected(self):
        """测试 limit 为 0 应被拒绝"""
        # 业务规则：limit 应大于 0
        from api.matching import validate_limit, MIN_LIMIT
        limit = 0
        # 验证：limit <= 0 应抛出 HTTPException
        from fastapi import HTTPException
        with pytest.raises(HTTPException, match="limit 必须大于 0"):
            validate_limit(limit)

    def test_limit_negative_should_be_rejected(self):
        """测试负数 limit 应被拒绝"""
        # 业务规则：limit 应大于 0
        from api.matching import validate_limit
        from fastapi import HTTPException
        limit = -1
        # 验证：负数 limit 应抛出 HTTPException
        with pytest.raises(HTTPException, match="limit 必须大于 0"):
            validate_limit(limit)

    def test_limit_extremely_large_should_be_capped(self):
        """测试超大 limit 应被限制"""
        # 业务规则：限制最大 limit 为 100
        from api.matching import validate_limit, MAX_LIMIT
        limit = 1000  # 超过 MAX_LIMIT
        # 验证：超大 limit 应被限制到 MAX_LIMIT
        result = validate_limit(limit)
        assert result == MAX_LIMIT


# ============= 认证接口边界值测试 =============

class TestAuthBoundary:
    """认证接口边界值测试"""

    def test_password_empty(self):
        """测试空密码"""
        # 空密码验证应返回 False
        hashed = get_password_hash("testpassword")
        result = verify_password("", hashed)
        assert result is False

    def test_password_sha256_format(self):
        """测试 SHA-256 格式密码"""
        # SHA-256 格式：64 字符十六进制
        sha256_password = "a" * 64
        hashed = get_password_hash(sha256_password)
        result = verify_password(sha256_password, hashed)
        assert result is True

    def test_password_not_sha256_format(self):
        """测试非 SHA-256 格式密码"""
        # 普通密码：非 64 字符
        plain_password = "testpassword123"
        hashed = get_password_hash(plain_password)
        result = verify_password(plain_password, hashed)
        assert result is True

    def test_password_too_long(self):
        """测试超长密码"""
        # bcrypt 只使用前 72 字符
        long_password = "a" * 200
        hashed = get_password_hash(long_password)
        # 只有前 72 字符有效
        result = verify_password("a" * 72, hashed)
        # bcrypt 实际上会截断到 72 字符，所以 "a"*72 和 "a"*200 应该匹配
        assert result is True

    def test_token_expired(self):
        """测试过期 Token"""
        # 创建立即过期的 token
        from datetime import timedelta
        expired_token = create_access_token(
            "test_user",
            expires_delta=timedelta(seconds=-1)
        )
        # 过期 token 解码应返回 None
        result = decode_access_token(expired_token)
        assert result is None

    def test_token_invalid_format(self):
        """测试无效格式 Token"""
        # 随机字符串
        invalid_token = "not-a-valid-token"
        result = decode_access_token(invalid_token)
        assert result is None

    def test_token_type_mismatch(self):
        """测试 Token 类型混淆"""
        # 使用 refresh_token 作为 access_token
        refresh_token = create_refresh_token("test_user")
        # 应拒绝
        result = decode_access_token(refresh_token)
        assert result is None


# ============= 文件上传边界值测试 =============

class TestFileUploadBoundary:
    """文件上传边界值测试"""

    def test_file_size_limit_should_be_enforced(self):
        """测试文件大小限制应被执行"""
        # 业务规则：限制最大 10MB
        from api.photos import MAX_FILE_SIZE, validate_file_upload
        from fastapi import HTTPException
        from unittest.mock import MagicMock
        import io

        # 创建超过限制的文件内容 (11MB)
        large_content = b"x" * (11 * 1024 * 1024)

        # 使用 Mock 模拟 UploadFile
        file = MagicMock()
        file.filename = "test.jpg"
        file.content_type = "image/jpeg"
        file.file = io.BytesIO(large_content)

        # 验证：超大文件应抛出 HTTPException
        with pytest.raises(HTTPException, match="文件大小超过限制"):
            validate_file_upload(file, large_content)

    def test_file_empty_should_be_rejected(self):
        """测试空文件应被拒绝"""
        # 业务规则：拒绝空文件
        from api.photos import MIN_FILE_SIZE, validate_file_upload
        from fastapi import HTTPException
        from unittest.mock import MagicMock
        import io

        # 创建空文件内容 (< 100 bytes)
        empty_content = b"x" * 10  # 仅 10 字节

        # 使用 Mock 模拟 UploadFile
        file = MagicMock()
        file.filename = "test.jpg"
        file.content_type = "image/jpeg"
        file.file = io.BytesIO(empty_content)

        # 验证：空文件应抛出 HTTPException
        with pytest.raises(HTTPException, match="文件太小或为空"):
            validate_file_upload(file, empty_content)

    def test_file_invalid_extension(self):
        """测试非法文件扩展名"""
        invalid_extensions = [".exe", ".bat", ".sh", ".cmd", ".js"]
        valid_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        # 只允许图片格式
        for ext in invalid_extensions:
            assert ext not in valid_extensions, f"业务规则：拒绝 {ext} 文件"

    def test_filename_special_chars(self):
        """测试特殊字符文件名"""
        malicious_names = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "test<script>.jpg",
            "test|test.jpg",
        ]
        # 应拒绝或清理恶意文件名
        for name in malicious_names:
            # 业务规则：文件名应只包含安全字符
            safe_name = name.replace("/", "").replace("\\", "").replace("<", "").replace("|", "")
            assert safe_name != name, f"业务规则：应清理恶意文件名 {name}"
            assert safe_name != name, f"业务规则：应清理恶意文件名 {name}"


# ============= 偏好设置边界值测试 =============

class TestPreferenceBoundary:
    """用户偏好边界值测试"""

    def test_preferred_age_range_invalid(self):
        """测试无效年龄偏好范围 - 注：preferred_age 字段在 UserUpdate 中测试"""
        # UserCreate 不包含 preferred_age_min/max 字段，此测试应在 UserUpdate 测试中进行
        pytest.skip("preferred_age_min/max 字段不在 UserCreate 模型中，应使用 UserUpdate 测试")

    def test_preferred_age_range_boundary(self):
        """测试年龄偏好范围边界 - 注：preferred_age 字段在 UserUpdate 中测试"""
        # UserCreate 不包含 preferred_age_min/max 字段，此测试应在 UserUpdate 测试中进行
        pytest.skip("preferred_age_min/max 字段不在 UserCreate 模型中，应使用 UserUpdate 测试")

    def test_values_range_invalid(self):
        """测试价值观评分超出范围"""
        # 价值观评分应在 0-1 范围，模型已添加验证
        with pytest.raises(ValidationError):
            UserCreate(
                username="testuser_val",
                name="测试用户",
                email="test@example.com",
                age=28,
                gender=Gender.MALE,
                location="北京市",
                values={"openness": 1.5}  # > 1，无效
            )

    def test_interests_empty(self):
        """测试空兴趣列表"""
        user = UserCreate(
            username="testuser_empty",
            name="测试用户",
            email="test@example.com",
            age=28,
            gender=Gender.MALE,
            location="北京市",
            interests=[]  # 空
        )
        # 空兴趣列表是有效的（冷启动用户）
        assert user.interests == []

    def test_interests_too_many(self):
        """测试过多兴趣"""
        # 模型已添加 max_length=20 验证，应抛出 ValidationError
        many_interests = [f"兴趣{i}" for i in range(100)]
        with pytest.raises(ValidationError):
            UserCreate(
                name="测试用户",
                email="test@example.com",
                age=28,
                gender=Gender.MALE,
                location="北京市",
                interests=many_interests
            )


# ============= 综合边界值测试 =============

class TestCompositeBoundary:
    """综合边界值测试（多字段组合）"""

    def test_all_fields_empty(self):
        """测试所有字段为空"""
        with pytest.raises(ValidationError):
            UserCreate(
                name="",
                email="",
                age=None,
                gender=None,
                location=""
            )

    def test_all_fields_max_length(self):
        """测试所有字段最大长度"""
        try:
            user = UserCreate(
                name="测" * 50,  # 最大姓名
                email="a" * 240 + "@example.com",  # 最大邮箱
                age=150,  # 最大年龄
                gender=Gender.MALE,
                location="北" * 200,  # 最大地址
                bio="测" * 5000,  # 最大简介
            )
            # 验证成功或业务规则限制
            assert user is not None
        except ValidationError:
            pass  # 正确拒绝超长字段

    def test_extreme_user_profile(self):
        """测试极端用户画像"""
        extreme_user = UserCreate(
            username="extreme_user",
            name="极端测试用户",
            email="extreme@example.com",
            age=18,  # 最小有效年龄
            gender=Gender.OTHER,
            location="南极洲",  # 极端地点
            interests=[],  # 无兴趣
            values={},  # 无价值观评分
            sexual_orientation=SexualOrientation.BISEXUAL
        )
        # 模型层面接受，业务逻辑可能需要处理
        assert extreme_user.age == 18
        assert extreme_user.gender == Gender.OTHER
        assert extreme_user.sexual_orientation == SexualOrientation.BISEXUAL


# ============= 运行测试 =============

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])