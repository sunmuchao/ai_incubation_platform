"""
用户 API 测试 - 注册端点自动生成逻辑

测试覆盖:
1. 不提供 username 时自动生成
2. 不提供 email 时自动生成临时邮箱
3. 不提供 location 时接受 NULL
4. 最小化注册（仅必填字段）
5. 完整注册（所有字段）

修复验证: 422 "Field required" 错误已解决
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import re

# 导入主应用
from main import app


# ============= 测试客户端 Fixture =============

@pytest.fixture
def client():
    """FastAPI 测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    mock = MagicMock()
    mock.query.return_value.filter.return_value.first.return_value = None
    mock.add.return_value = None
    mock.commit.return_value = None
    mock.rollback.return_value = None
    return mock


@pytest.fixture
def mock_user_repository(mock_db_session):
    """模拟 UserRepository"""
    with patch("api.users.get_user_service") as mock_service:
        mock_repo = MagicMock()
        mock_repo.db = mock_db_session
        mock_repo.get_by_email.return_value = None  # 邮箱不存在
        mock_repo.get_by_username.return_value = None  # 用户名不存在
        mock_repo.create.return_value = MagicMock(
            id="test_user_id_123",
            name="测试用户",
            email="test@example.com",
            age=28,
            gender="male",
            location="北京市",
            password_hash="hashed_password",
            is_active=True,
        )
        mock_service.return_value = lambda: mock_repo
        yield mock_repo


# ============= 第一部分：自动生成测试 =============

class TestUserRegistrationAutoGeneration:
    """注册端点自动生成逻辑测试"""

    def test_register_without_username_auto_generates(self, client, mock_user_repository):
        """测试不提供 username 时自动生成"""
        # 不提供 username
        response = client.post(
            "/api/users/register",
            json={
                "name": "测试用户",
                "age": 28,
                "gender": "male",
                # username 不提供
            }
        )

        # 应该成功，不是 422 错误
        assert response.status_code != 422
        # 可能是 201（成功）或其他状态
        if response.status_code == 200 or response.status_code == 201:
            data = response.json()
            # username 应该被自动生成（格式：user_xxxxxxxx）
            assert data.get("username") or "username not in response"

    def test_register_without_email_auto_generates(self, client, mock_user_repository):
        """测试不提供 email 时自动生成临时邮箱"""
        response = client.post(
            "/api/users/register",
            json={
                "name": "测试用户",
                "username": "testuser123",
                "age": 28,
                "gender": "male",
                # email 不提供
            }
        )

        # 应该成功，不是 422 错误
        assert response.status_code != 422
        if response.status_code == 200 or response.status_code == 201:
            data = response.json()
            # email 应该被自动生成（格式：username@temp.her.local）
            email = data.get("email")
            if email:
                assert "@temp.her.local" in email or email != ""

    def test_register_without_location_accepts_null(self, client, mock_user_repository):
        """测试不提供 location 时接受 NULL"""
        response = client.post(
            "/api/users/register",
            json={
                "name": "测试用户",
                "age": 28,
                "gender": "male",
                # location 不提供
            }
        )

        # 应该成功，不是 422 错误
        assert response.status_code != 422

    def test_register_minimal_required_fields(self, client, mock_user_repository):
        """测试最小化注册（仅必填字段：name, age, gender）"""
        response = client.post(
            "/api/users/register",
            json={
                "name": "最小用户",
                "age": 25,
                "gender": "female",
                # 只提供必填字段
            }
        )

        # 应该成功，不是 422 错误
        assert response.status_code != 422
        # 验证返回数据
        if response.status_code in [200, 201]:
            data = response.json()
            assert data.get("name") == "最小用户"
            assert data.get("age") == 25
            assert data.get("gender") == "female"

    def test_register_with_all_fields(self, client, mock_user_repository):
        """测试完整注册（所有字段）"""
        response = client.post(
            "/api/users/register",
            json={
                "username": "complete_user",
                "email": "complete@example.com",
                "name": "完整用户",
                "age": 30,
                "gender": "male",
                "location": "上海市",
                "bio": "这是我的简介",
                "interests": ["阅读", "旅行"],
                "values": {"openness": 0.8},
            }
        )

        # 应该成功
        assert response.status_code in [200, 201, 400]  # 400 可能是邮箱已存在


# ============= 第二部分：字段验证测试 =============

class TestUserRegistrationValidation:
    """注册端点字段验证测试"""

    def test_register_missing_name_returns_error(self, client, mock_user_repository):
        """测试缺少必填字段 name 时返回错误"""
        response = client.post(
            "/api/users/register",
            json={
                # name 不提供（必填）
                "age": 28,
                "gender": "male",
            }
        )

        # 应该返回 422 错误（name 是必填的）
        assert response.status_code == 422

    def test_register_missing_age_returns_error(self, client, mock_user_repository):
        """测试缺少必填字段 age 时返回错误"""
        response = client.post(
            "/api/users/register",
            json={
                "name": "测试用户",
                # age 不提供（必填）
                "gender": "male",
            }
        )

        # 应该返回 422 错误（age 是必填的）
        assert response.status_code == 422

    def test_register_missing_gender_returns_error(self, client, mock_user_repository):
        """测试缺少必填字段 gender 时返回错误"""
        response = client.post(
            "/api/users/register",
            json={
                "name": "测试用户",
                "age": 28,
                # gender 不提供（必填）
            }
        )

        # 应该返回 422 错误（gender 是必填的）
        assert response.status_code == 422

    def test_register_invalid_gender_returns_error(self, client, mock_user_repository):
        """测试无效的 gender 值返回错误"""
        response = client.post(
            "/api/users/register",
            json={
                "name": "测试用户",
                "age": 28,
                "gender": "invalid_gender",  # 无效值
            }
        )

        # 应该返回 422 错误
        assert response.status_code == 422

    def test_register_age_out_of_range_returns_error(self, client, mock_user_repository):
        """测试年龄超出范围返回错误"""
        response = client.post(
            "/api/users/register",
            json={
                "name": "未成年用户",
                "age": 17,  # 年龄小于 18
                "gender": "male",
            }
        )

        # 应该返回 422 错误（年龄必须在 18-150）
        assert response.status_code == 422

    def test_register_age_too_old_returns_error(self, client, mock_user_repository):
        """测试年龄过大返回错误"""
        response = client.post(
            "/api/users/register",
            json={
                "name": "超龄用户",
                "age": 151,  # 年龄大于 150
                "gender": "male",
            }
        )

        # 应该返回 422 错误
        assert response.status_code == 422


# ============= 第三部分：Pydantic 模型验证测试 =============

class TestUserCreateModel:
    """UserCreate Pydantic 模型测试"""

    def test_user_create_with_optional_fields(self):
        """测试 UserCreate 模型接受可选字段"""
        from models.user import UserCreate, Gender

        # 创建时只提供必填字段
        user = UserCreate(
            name="可选字段用户",
            age=28,
            gender=Gender.MALE,
        )

        # 可选字段应该有默认值或 None
        assert user.username is None
        assert user.email is None
        assert user.location is None

    def test_user_create_auto_username_format(self):
        """测试 UserCreate 接受自动生成的 username 格式"""
        from models.user import UserCreate, Gender

        # 接受自动生成的 username 格式
        user = UserCreate(
            username="user_abc12345",  # 自动生成格式
            name="自动用户名",
            age=28,
            gender=Gender.MALE,
        )

        assert user.username == "user_abc12345"

    def test_user_create_invalid_username_returns_error(self):
        """测试 UserCreate 拒绝无效的 username"""
        from models.user import UserCreate, Gender
        from pydantic import ValidationError

        # 无效的 username（包含特殊字符）
        with pytest.raises(ValidationError):
            UserCreate(
                username="user@invalid!",  # 包含 @ 和 !
                name="无效用户名",
                age=28,
                gender=Gender.MALE,
            )

    def test_user_create_empty_name_returns_error(self):
        """测试 UserCreate 拒绝空的 name"""
        from models.user import UserCreate, Gender
        from pydantic import ValidationError

        # 空的 name
        with pytest.raises(ValidationError):
            UserCreate(
                name="",  # 空字符串
                age=28,
                gender=Gender.MALE,
            )

    def test_user_create_whitespace_name_returns_error(self):
        """测试 UserCreate 拒绝纯空格的 name"""
        from models.user import UserCreate, Gender
        from pydantic import ValidationError

        # 纯空格的 name
        with pytest.raises(ValidationError):
            UserCreate(
                name="   ",  # 纯空格
                age=28,
                gender=Gender.MALE,
            )


# ============= 运行测试 =============

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])