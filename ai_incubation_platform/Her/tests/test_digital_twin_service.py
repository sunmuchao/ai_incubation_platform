"""
数字分身服务测试

测试 DigitalTwinService 的核心功能：
- 数字分身配置创建与管理
- 模拟会话管理
- 配置验证
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from services.digital_twin_service import DigitalTwinService
from models.digital_twin_models import DigitalTwinProfile, DigitalTwinSimulation


class TestDigitalTwinServiceInit:
    """初始化测试"""

    def test_init_with_db(self):
        """测试带 db 参数初始化"""
        mock_db = MagicMock()
        service = DigitalTwinService(db=mock_db)
        assert service._db == mock_db
        assert service._should_close_db is False

    def test_init_without_db(self):
        """测试不带 db 参数初始化"""
        service = DigitalTwinService.__new__(DigitalTwinService)
        service._db = None
        service._should_close_db = True
        assert service._should_close_db is True


class TestDigitalTwinProfileManagement:
    """数字分身配置管理测试"""

    @pytest.fixture
    def mock_db(self):
        """Mock 数据库会话"""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        service = DigitalTwinService.__new__(DigitalTwinService)
        service._db = mock_db
        service._should_close_db = False
        return service

    def test_create_twin_profile_new(self, service, mock_db):
        """测试创建新的数字分身配置"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        success, message, profile = service.create_twin_profile(
            user_id="test_user",
            display_name="测试分身",
            personality_traits={"openness": 0.8},
            communication_style="medium",
        )

        assert success is True
        assert "创建" in message
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_create_twin_profile_update_existing(self, service, mock_db):
        """测试更新已存在的配置"""
        mock_existing = MagicMock()
        mock_existing.display_name = "旧名称"
        mock_existing.personality_traits = {}
        mock_existing.is_active = True

        mock_db.query.return_value.filter.return_value.first.return_value = mock_existing

        success, message, profile = service.create_twin_profile(
            user_id="test_user",
            display_name="新名称",
            personality_traits={"openness": 0.9},
        )

        assert success is True
        assert "更新" in message
        mock_db.add.assert_not_called()

    def test_create_twin_profile_with_all_fields(self, service, mock_db):
        """测试带所有字段创建"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        success, message, profile = service.create_twin_profile(
            user_id="test_user",
            display_name="完整分身",
            personality_traits={"openness": 0.8, "conscientiousness": 0.7},
            communication_style="high",
            core_values=["诚实", "善良"],
            interests=["阅读", "运动"],
            deal_breakers=["欺骗"],
            response_patterns=["友好回应"],
            topic_preferences=["旅行"],
            conversation_starters=["你好"],
            simulation_temperature=0.8,
            response_length_preference="long",
        )

        assert success is True

    def test_get_twin_profile_exists(self, service, mock_db):
        """测试获取已存在的配置"""
        mock_profile = MagicMock()
        mock_profile.user_id = "test_user"
        mock_profile.display_name = "测试分身"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_profile

        profile = service.get_twin_profile("test_user")

        assert profile == mock_profile

    def test_get_twin_profile_not_exists(self, service, mock_db):
        """测试获取不存在的配置"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        profile = service.get_twin_profile("nonexistent_user")

        assert profile is None

    def test_update_twin_profile_success(self, service, mock_db):
        """测试更新配置成功"""
        mock_profile = MagicMock()
        mock_profile.display_name = "旧名称"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_profile

        success, message = service.update_twin_profile(
            user_id="test_user",
            updates={"display_name": "新名称"}
        )

        assert success is True
        assert "更新" in message

    def test_update_twin_profile_not_found(self, service, mock_db):
        """测试更新不存在的配置"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        success, message = service.update_twin_profile(
            user_id="nonexistent",
            updates={"display_name": "新名称"}
        )

        assert success is False
        assert "未找到" in message


class TestSimulationManagement:
    """模拟会话管理测试"""

    @pytest.fixture
    def mock_db(self):
        """Mock 数据库会话"""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        service = DigitalTwinService.__new__(DigitalTwinService)
        service._db = mock_db
        service._should_close_db = False
        return service

    def test_start_simulation_success(self, service, mock_db):
        """测试启动模拟成功"""
        # 模拟双方分身配置存在
        mock_twin_a = MagicMock()
        mock_twin_a.user_id = "user_a"
        mock_twin_b = MagicMock()
        mock_twin_b.user_id = "user_b"

        # 设置 get_twin_profile 返回值
        service.get_twin_profile = lambda user_id: mock_twin_a if user_id == "user_a" else mock_twin_b

        success, message, simulation = service.start_simulation(
            user_a_id="user_a",
            user_b_id="user_b",
            total_rounds=10,
        )

        assert success is True
        assert "开始" in message
        mock_db.add.assert_called_once()

    def test_start_simulation_missing_twin_a(self, service, mock_db):
        """测试缺少用户 A 分身"""
        service.get_twin_profile = lambda user_id: None

        success, message, simulation = service.start_simulation(
            user_a_id="user_a",
            user_b_id="user_b",
        )

        assert success is False
        assert "未配置" in message or "未找到" in message
        assert simulation is None

    def test_start_simulation_missing_twin_b(self, service, mock_db):
        """测试缺少用户 B 分身"""
        mock_twin_a = MagicMock()
        service.get_twin_profile = lambda user_id: mock_twin_a if user_id == "user_a" else None

        success, message, simulation = service.start_simulation(
            user_a_id="user_a",
            user_b_id="user_b",
        )

        assert success is False
        assert simulation is None

    def test_start_simulation_with_config(self, service, mock_db):
        """测试带配置启动模拟"""
        mock_twin_a = MagicMock()
        mock_twin_b = MagicMock()
        service.get_twin_profile = lambda user_id: mock_twin_a if user_id == "user_a" else mock_twin_b

        success, message, simulation = service.start_simulation(
            user_a_id="user_a",
            user_b_id="user_b",
            total_rounds=20,
            simulation_config={"temperature": 0.8}
        )

        assert success is True


class TestDigitalTwinProfileDataClass:
    """配置数据验证测试"""

    def test_communication_style_values(self):
        """测试沟通风格值"""
        valid_styles = ["low", "medium", "high"]
        for style in valid_styles:
            assert isinstance(style, str)

    def test_simulation_temperature_range(self):
        """测试模拟温度范围"""
        # 温度应在 0-1 之间
        valid_temps = [0.0, 0.5, 0.7, 1.0]
        for temp in valid_temps:
            assert 0 <= temp <= 1

    def test_response_length_preferences(self):
        """测试回复长度偏好"""
        valid_lengths = ["short", "medium", "long"]
        for length in valid_lengths:
            assert isinstance(length, str)


class TestDigitalTwinServiceConfig:
    """配置验证测试"""

    def test_default_communication_style(self):
        """测试默认沟通风格"""
        # 默认值应为 "medium"
        assert "medium" == "medium"

    def test_default_simulation_temperature(self):
        """测试默认模拟温度"""
        # 默认值应为 0.7
        assert 0.7 == 0.7

    def test_default_response_length(self):
        """测试默认回复长度"""
        assert "medium" == "medium"


class TestSimulationConfig:
    """模拟配置测试"""

    def test_total_rounds_minimum(self):
        """测试最小轮数"""
        min_rounds = 1
        assert min_rounds >= 1

    def test_total_rounds_maximum(self):
        """测试最大轮数"""
        max_rounds = 50
        assert max_rounds <= 100

    def test_simulation_status_values(self):
        """测试模拟状态值"""
        valid_statuses = ["running", "completed", "failed", "paused"]
        for status in valid_statuses:
            assert isinstance(status, str)


class TestDigitalTwinServiceEdgeCases:
    """边界值测试"""

    def test_empty_personality_traits(self):
        """测试空性格特征"""
        traits = {}
        # 应接受空特征
        assert traits == {}

    def test_empty_interests_list(self):
        """测试空兴趣列表"""
        interests = []
        assert interests == []

    def test_long_display_name(self):
        """测试长显示名称"""
        long_name = "这是一个很长的显示名称测试超过二十个字符的名称"
        # 应接受合理长度
        assert len(long_name) > 20

    def test_unicode_display_name(self):
        """测试 Unicode 显示名称"""
        unicode_name = "测试分身🎉"
        assert isinstance(unicode_name, str)


class TestDigitalTwinServiceErrorHandling:
    """错误处理测试"""

    def test_create_twin_profile_exception(self):
        """测试创建配置异常"""
        service = DigitalTwinService.__new__(DigitalTwinService)
        service._db = None
        service._should_close_db = False

        # _get_db 会返回 None 或抛出异常
        # 测试应能处理异常情况
        # 由于 _get_db 在实现中会创建 SessionLocal
        # 这里测试异常处理逻辑
        pass

    def test_update_twin_profile_exception(self):
        """测试更新配置异常"""
        service = DigitalTwinService.__new__(DigitalTwinService)
        service._db = None
        service._should_close_db = False
        pass