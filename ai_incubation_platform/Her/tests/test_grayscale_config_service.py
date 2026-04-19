"""
灰度配置服务测试

测试 GrayscaleConfigService 的核心功能：
- 功能开关配置常量
- 哈希计算
- 变体分配
- 实验分组
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import hashlib

# 尝试导入服务模块
try:
    from services.grayscale_config_service import (
        GrayscaleConfigService,
        FeatureFlag,
        ExperimentVariant,
        ExperimentResult,
        DEFAULT_FEATURE_FLAGS,
        DEFAULT_AB_EXPERIMENTS,
        get_grayscale_config_service,
    )
except ImportError:
    pytest.skip("grayscale_config_service not importable", allow_module_level=True)


class TestFeatureFlagDataclass:
    """FeatureFlag 数据类测试"""

    def test_feature_flag_creation(self):
        """测试功能开关创建"""
        flag = FeatureFlag(
            flag_key="test_flag",
            name="测试开关",
            is_enabled=True,
            rollout_percentage=50
        )

        assert flag.flag_key == "test_flag"
        assert flag.name == "测试开关"
        assert flag.is_enabled is True
        assert flag.rollout_percentage == 50

    def test_feature_flag_defaults(self):
        """测试功能开关默认值"""
        flag = FeatureFlag(
            flag_key="test_flag",
            name="测试开关"
        )

        assert flag.is_enabled is False
        assert flag.rollout_percentage == 0
        assert flag.target_user_groups == []
        assert flag.config_data == {}

    def test_feature_flag_with_groups(self):
        """测试带用户群的功能开关"""
        flag = FeatureFlag(
            flag_key="test_flag",
            name="测试开关",
            target_user_groups=["vip", "beta_testers"]
        )

        assert len(flag.target_user_groups) == 2
        assert "vip" in flag.target_user_groups


class TestExperimentVariantDataclass:
    """ExperimentVariant 数据类测试"""

    def test_variant_creation(self):
        """测试变体创建"""
        variant = ExperimentVariant(
            name="variant_a",
            weight=50,
            config={"feature_enabled": True}
        )

        assert variant.name == "variant_a"
        assert variant.weight == 50
        assert variant.config["feature_enabled"] is True

    def test_variant_defaults(self):
        """测试变体默认值"""
        variant = ExperimentVariant(
            name="control",
            weight=100
        )

        assert variant.config == {}


class TestExperimentResultDataclass:
    """ExperimentResult 数据类测试"""

    def test_result_creation(self):
        """测试结果创建"""
        result = ExperimentResult(
            experiment_key="test_exp",
            variant_name="variant_a",
            config={"setting": 1},
            is_new_assignment=True
        )

        assert result.experiment_key == "test_exp"
        assert result.variant_name == "variant_a"
        assert result.config["setting"] == 1
        assert result.is_new_assignment is True

    def test_result_defaults(self):
        """测试结果默认值"""
        result = ExperimentResult(
            experiment_key="test_exp",
            variant_name="control",
            config={},
            is_new_assignment=False
        )

        assert result.variant_name == "control"
        assert result.is_new_assignment is False


class TestDefaultFeatureFlags:
    """默认功能开关配置测试"""

    def test_default_flags_count(self):
        """测试默认开关数量"""
        assert len(DEFAULT_FEATURE_FLAGS) == 3

    def test_quick_start_flow_flag(self):
        """测试快速入门开关"""
        flag = DEFAULT_FEATURE_FLAGS[0]

        assert flag["flag_key"] == "quick_start_flow"
        assert flag["name"] == "快速入门流程"
        assert flag["is_enabled"] is True
        assert flag["rollout_percentage"] == 100

    def test_feedback_learning_flag(self):
        """测试反馈学习开关"""
        flag = DEFAULT_FEATURE_FLAGS[1]

        assert flag["flag_key"] == "feedback_learning"
        assert flag["is_enabled"] is True
        assert flag["rollout_percentage"] == 100

    def test_behavior_tracking_flag(self):
        """测试行为追踪开关"""
        flag = DEFAULT_FEATURE_FLAGS[2]

        assert flag["flag_key"] == "behavior_tracking"
        assert flag["is_enabled"] is True

    def test_all_flags_have_required_fields(self):
        """测试所有开关包含必填字段"""
        required_fields = ["flag_key", "name", "is_enabled", "rollout_percentage"]

        for flag in DEFAULT_FEATURE_FLAGS:
            for field in required_fields:
                assert field in flag


class TestDefaultABExperiments:
    """默认 A/B 实验配置测试"""

    def test_default_experiments_count(self):
        """测试默认实验数量"""
        assert len(DEFAULT_AB_EXPERIMENTS) == 1

    def test_quick_start_ab_experiment(self):
        """测试快速入门实验"""
        exp = DEFAULT_AB_EXPERIMENTS[0]

        assert exp["experiment_key"] == "quick_start_ab_test"
        assert exp["name"] == "快速入门 A/B 测试"
        assert exp["status"] == "paused"

    def test_experiment_variants(self):
        """测试实验变体"""
        exp = DEFAULT_AB_EXPERIMENTS[0]
        variants = exp["variants"]

        assert len(variants) == 2
        assert variants[0]["name"] == "variant_a"
        assert variants[0]["weight"] == 100
        assert variants[1]["name"] == "variant_b"
        assert variants[1]["weight"] == 0

    def test_experiment_metrics(self):
        """测试实验指标"""
        exp = DEFAULT_AB_EXPERIMENTS[0]

        assert exp["primary_metric"] == "first_day_retention"
        assert len(exp["secondary_metrics"]) == 3


class TestHashUserId:
    """用户 ID 哈希计算测试"""

    def test_hash_returns_int(self):
        """测试哈希返回整数"""
        service = GrayscaleConfigService()

        hash_value = service._hash_user_id("user_001")

        assert isinstance(hash_value, int)

    def test_hash_consistency(self):
        """测试哈希一致性"""
        service = GrayscaleConfigService()

        hash1 = service._hash_user_id("user_001")
        hash2 = service._hash_user_id("user_001")

        assert hash1 == hash2

    def test_hash_different_users(self):
        """测试不同用户哈希不同"""
        service = GrayscaleConfigService()

        hash1 = service._hash_user_id("user_001")
        hash2 = service._hash_user_id("user_002")

        assert hash1 != hash2

    def test_hash_with_salt(self):
        """测试带盐值哈希"""
        service = GrayscaleConfigService()

        hash1 = service._hash_user_id("user_001", "salt1")
        hash2 = service._hash_user_id("user_001", "salt2")

        assert hash1 != hash2

    def test_hash_range(self):
        """测试哈希值范围"""
        service = GrayscaleConfigService()

        # 多个用户哈希应在合理范围内
        for i in range(100):
            hash_value = service._hash_user_id(f"user_{i}")
            assert hash_value >= 0
            assert hash_value < 2**32  # 8位十六进制的最大值


class TestAssignVariant:
    """变体分配测试"""

    def test_assign_variant_basic(self):
        """测试基本变体分配"""
        service = GrayscaleConfigService()

        variants = [
            {"name": "control", "weight": 50},
            {"name": "variant_a", "weight": 50}
        ]

        variant = service._assign_variant("user_001", variants)

        assert variant in ["control", "variant_a"]

    def test_assign_variant_consistency(self):
        """测试分配一致性"""
        service = GrayscaleConfigService()

        variants = [
            {"name": "control", "weight": 50},
            {"name": "variant_a", "weight": 50}
        ]

        # 同一用户多次分配应相同
        variant1 = service._assign_variant("user_001", variants)
        variant2 = service._assign_variant("user_001", variants)

        assert variant1 == variant2

    def test_assign_variant_distribution(self):
        """测试变体分布"""
        service = GrayscaleConfigService()

        variants = [
            {"name": "control", "weight": 50},
            {"name": "variant_a", "weight": 50}
        ]

        # 统计多个用户的分配结果
        results = {}
        for i in range(100):
            variant = service._assign_variant(f"user_{i}", variants)
            results[variant] = results.get(variant, 0) + 1

        # 应有两种变体
        assert len(results) == 2

    def test_assign_variant_single_variant(self):
        """测试单一变体"""
        service = GrayscaleConfigService()

        variants = [
            {"name": "control", "weight": 100}
        ]

        variant = service._assign_variant("user_001", variants)

        assert variant == "control"

    def test_assign_variant_empty_list(self):
        """测试空变体列表"""
        service = GrayscaleConfigService()

        variant = service._assign_variant("user_001", [])

        assert variant == "control"

    def test_assign_variant_zero_weights(self):
        """测试零权重"""
        service = GrayscaleConfigService()

        variants = [
            {"name": "control", "weight": 0},
            {"name": "variant_a", "weight": 0}
        ]

        variant = service._assign_variant("user_001", variants)

        # 应返回最后一个
        assert variant == "variant_a"


class TestGetVariantConfig:
    """获取变体配置测试"""

    def test_get_variant_config_found(self):
        """测试找到变体配置"""
        service = GrayscaleConfigService()

        variants = [
            {"name": "control", "config": {"setting": 0}},
            {"name": "variant_a", "config": {"setting": 1}}
        ]

        config = service._get_variant_config(variants, "variant_a")

        assert config["setting"] == 1

    def test_get_variant_config_not_found(self):
        """测试未找到变体配置"""
        service = GrayscaleConfigService()

        variants = [
            {"name": "control", "config": {"setting": 0}}
        ]

        config = service._get_variant_config(variants, "variant_b")

        assert config == {}

    def test_get_variant_config_empty_variants(self):
        """测试空变体列表"""
        service = GrayscaleConfigService()

        config = service._get_variant_config([], "control")

        assert config == {}

    def test_get_variant_config_missing_config(self):
        """测试缺失配置字段"""
        service = GrayscaleConfigService()

        variants = [
            {"name": "control"}  # 缺少 config 字段
        ]

        config = service._get_variant_config(variants, "control")

        assert config == {}


class TestServiceInitialization:
    """服务初始化测试"""

    def test_service_creation_with_db(self):
        """测试带数据库初始化"""
        mock_db = MagicMock()
        service = GrayscaleConfigService(mock_db)

        assert service is not None

    def test_service_creation_without_db(self):
        """测试无数据库初始化"""
        service = GrayscaleConfigService()

        assert service is not None

    def test_global_service_instance(self):
        """测试全局服务实例"""
        service1 = get_grayscale_config_service()
        service2 = get_grayscale_config_service()

        assert service1 is not None
        assert service1 is service2  # 单例


class TestEdgeCases:
    """边界值测试"""

    def test_hash_empty_user_id(self):
        """测试空用户 ID 哈希"""
        service = GrayscaleConfigService()

        hash_value = service._hash_user_id("")

        assert isinstance(hash_value, int)

    def test_hash_special_characters(self):
        """测试特殊字符哈希"""
        service = GrayscaleConfigService()

        hash_value = service._hash_user_id("user-特殊-字符")

        assert isinstance(hash_value, int)

    def test_assign_variant_uneven_weights(self):
        """测试不均匀权重"""
        service = GrayscaleConfigService()

        variants = [
            {"name": "control", "weight": 30},
            {"name": "variant_a", "weight": 70}
        ]

        variant = service._assign_variant("user_001", variants)

        assert variant in ["control", "variant_a"]

    def test_assign_variant_multiple_variants(self):
        """测试多变体"""
        service = GrayscaleConfigService()

        variants = [
            {"name": "control", "weight": 25},
            {"name": "variant_a", "weight": 25},
            {"name": "variant_b", "weight": 25},
            {"name": "variant_c", "weight": 25}
        ]

        variant = service._assign_variant("user_001", variants)

        assert variant in ["control", "variant_a", "variant_b", "variant_c"]

    def test_rollout_percentage_boundary(self):
        """测试灰度比例边界"""
        # 0% 和 100% 边界值
        for percentage in [0, 50, 100]:
            flag = FeatureFlag(
                flag_key="test",
                name="test",
                rollout_percentage=percentage
            )
            assert flag.rollout_percentage == percentage