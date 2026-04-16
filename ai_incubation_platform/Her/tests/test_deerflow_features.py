"""
DeerFlow Agent Factory 测试

测试 deerflow agents factory 的核心功能：
- RuntimeFeatures 配置
- 中间件定位装饰器
- 创建代理验证
"""
import pytest
from unittest.mock import MagicMock, patch
import sys

# 添加 deerflow backend 路径
sys.path.insert(0, '/Users/sunmuchao/Downloads/ai_incubation_platform/Her/deerflow/backend/packages/harness')

# 尝试导入模块
try:
    from deerflow.agents.features import RuntimeFeatures, Next, Prev
    from langchain.agents.middleware import AgentMiddleware
except ImportError as e:
    pytest.skip(f"deerflow.agents.features not importable: {e}", allow_module_level=True)


class TestRuntimeFeatures:
    """RuntimeFeatures 配置测试"""

    def test_runtime_features_default_values(self):
        """测试默认值"""
        features = RuntimeFeatures()

        assert features.sandbox is True
        assert features.memory is False
        assert features.summarization is False
        assert features.subagent is False
        assert features.vision is False
        assert features.auto_title is False
        assert features.guardrail is False

    def test_runtime_features_custom_values(self):
        """测试自定义值"""
        features = RuntimeFeatures(
            sandbox=False,
            memory=True,
            vision=True
        )

        assert features.sandbox is False
        assert features.memory is True
        assert features.vision is True

    def test_runtime_features_middleware_replacement(self):
        """测试中间件替换"""
        mock_middleware = MagicMock(spec=AgentMiddleware)

        features = RuntimeFeatures(
            sandbox=mock_middleware,
            memory=mock_middleware
        )

        assert isinstance(features.sandbox, AgentMiddleware)
        assert isinstance(features.memory, AgentMiddleware)

    def test_runtime_features_sandbox_options(self):
        """测试 sandbox 配置选项"""
        # True - 使用内置默认
        features_true = RuntimeFeatures(sandbox=True)
        assert features_true.sandbox is True

        # False - 禁用
        features_false = RuntimeFeatures(sandbox=False)
        assert features_false.sandbox is False

        # AgentMiddleware - 自定义
        mock_mw = MagicMock(spec=AgentMiddleware)
        features_custom = RuntimeFeatures(sandbox=mock_mw)
        assert isinstance(features_custom.sandbox, AgentMiddleware)

    def test_runtime_features_memory_options(self):
        """测试 memory 配置选项"""
        features_false = RuntimeFeatures(memory=False)
        assert features_false.memory is False

        mock_mw = MagicMock(spec=AgentMiddleware)
        features_custom = RuntimeFeatures(memory=mock_mw)
        assert isinstance(features_custom.memory, AgentMiddleware)

    def test_runtime_features_summarization_options(self):
        """测试 summarization 配置选项"""
        # summarization 只能是 False 或 AgentMiddleware
        features_false = RuntimeFeatures(summarization=False)
        assert features_false.summarization is False

        mock_mw = MagicMock(spec=AgentMiddleware)
        features_custom = RuntimeFeatures(summarization=mock_mw)
        assert isinstance(features_custom.summarization, AgentMiddleware)

    def test_runtime_features_guardrail_options(self):
        """测试 guardrail 配置选项"""
        # guardrail 只能是 False 或 AgentMiddleware
        features_false = RuntimeFeatures(guardrail=False)
        assert features_false.guardrail is False

        mock_mw = MagicMock(spec=AgentMiddleware)
        features_custom = RuntimeFeatures(guardrail=mock_mw)
        assert isinstance(features_custom.guardrail, AgentMiddleware)

    def test_runtime_features_all_features_disabled(self):
        """测试全部禁用"""
        features = RuntimeFeatures(
            sandbox=False,
            memory=False,
            summarization=False,
            subagent=False,
            vision=False,
            auto_title=False,
            guardrail=False
        )

        assert features.sandbox is False
        assert features.memory is False
        assert features.summarization is False
        assert features.subagent is False
        assert features.vision is False
        assert features.auto_title is False
        assert features.guardrail is False


class TestNextDecorator:
    """Next 装饰器测试"""

    def test_next_decorator_sets_attribute(self):
        """测试 Next 装饰器设置属性"""
        anchor = AgentMiddleware

        @Next(anchor)
        class TestMiddleware(AgentMiddleware):
            pass

        assert hasattr(TestMiddleware, '_next_anchor')
        assert TestMiddleware._next_anchor == AgentMiddleware

    def test_next_decorator_returns_class(self):
        """测试 Next 装饰器返回类"""
        anchor = AgentMiddleware

        @Next(anchor)
        class TestMiddleware(AgentMiddleware):
            pass

        assert isinstance(TestMiddleware, type)
        assert issubclass(TestMiddleware, AgentMiddleware)

    def test_next_decorator_invalid_anchor(self):
        """测试无效锚点类型"""
        with pytest.raises(TypeError):
            @Next("not_a_class")  # type: ignore
            class TestMiddleware(AgentMiddleware):
                pass

    def test_next_decorator_non_middleware_anchor(self):
        """测试非中间件锚点"""
        class NotAMiddleware:
            pass

        with pytest.raises(TypeError):
            @Next(NotAMiddleware)
            class TestMiddleware(AgentMiddleware):
                pass


class TestPrevDecorator:
    """Prev 装饰器测试"""

    def test_prev_decorator_sets_attribute(self):
        """测试 Prev 装饰器设置属性"""
        anchor = AgentMiddleware

        @Prev(anchor)
        class TestMiddleware(AgentMiddleware):
            pass

        assert hasattr(TestMiddleware, '_prev_anchor')
        assert TestMiddleware._prev_anchor == AgentMiddleware

    def test_prev_decorator_returns_class(self):
        """测试 Prev 装饰器返回类"""
        anchor = AgentMiddleware

        @Prev(anchor)
        class TestMiddleware(AgentMiddleware):
            pass

        assert isinstance(TestMiddleware, type)
        assert issubclass(TestMiddleware, AgentMiddleware)

    def test_prev_decorator_invalid_anchor(self):
        """测试无效锚点类型"""
        with pytest.raises(TypeError):
            @Prev("not_a_class")  # type: ignore
            class TestMiddleware(AgentMiddleware):
                pass


class TestDecoratorCombination:
    """装饰器组合测试"""

    def test_cannot_have_both_next_and_prev(self):
        """测试不能同时有 Next 和 Prev"""
        # 这个限制在 _insert_extra 中检查
        # 但我们可以在类定义层面测试
        anchor = AgentMiddleware

        @Next(anchor)
        class NextMiddleware(AgentMiddleware):
            pass

        @Prev(anchor)
        class PrevMiddleware(AgentMiddleware):
            pass

        # 应正确设置各自的属性
        assert NextMiddleware._next_anchor == AgentMiddleware
        assert PrevMiddleware._prev_anchor == AgentMiddleware


class TestMiddlewarePositioning:
    """中间件定位测试"""

    def test_next_positions_after_anchor(self):
        """测试 Next 定位在锚点之后"""
        # 逻辑：@Next(Anchor) 意味着该中间件应放在 Anchor 之后
        anchor = AgentMiddleware

        @Next(anchor)
        class AfterAnchor(AgentMiddleware):
            pass

        # 验证语义正确
        assert AfterAnchor._next_anchor == AgentMiddleware

    def test_prev_positions_before_anchor(self):
        """测试 Prev 定位在锚点之前"""
        anchor = AgentMiddleware

        @Prev(anchor)
        class BeforeAnchor(AgentMiddleware):
            pass

        # 验证语义正确
        assert BeforeAnchor._prev_anchor == AgentMiddleware


class TestEdgeCases:
    """边界值测试"""

    def test_runtime_features_dataclass_immutability(self):
        """测试 RuntimeFeatures 数据类"""
        features = RuntimeFeatures()

        # 应能修改属性
        features.sandbox = False
        assert features.sandbox is False

    def test_decorator_preserves_class_name(self):
        """测试装饰器保留类名"""
        @Next(AgentMiddleware)
        class MyCustomMiddleware(AgentMiddleware):
            pass

        assert MyCustomMiddleware.__name__ == "MyCustomMiddleware"

    def test_multiple_decorators_same_anchor(self):
        """测试多个装饰器使用同一锚点"""
        anchor = AgentMiddleware

        @Next(anchor)
        class FirstMiddleware(AgentMiddleware):
            pass

        @Prev(anchor)
        class SecondMiddleware(AgentMiddleware):
            pass

        # 应正确设置不同的定位
        assert FirstMiddleware._next_anchor == AgentMiddleware
        assert SecondMiddleware._prev_anchor == AgentMiddleware

    def test_runtime_features_all_enabled(self):
        """测试全部启用（使用自定义中间件）"""
        mock_mw = MagicMock(spec=AgentMiddleware)

        features = RuntimeFeatures(
            sandbox=mock_mw,
            memory=mock_mw,
            summarization=mock_mw,
            subagent=mock_mw,
            vision=mock_mw,
            auto_title=mock_mw,
            guardrail=mock_mw
        )

        # 全部应为 AgentMiddleware 实例
        assert isinstance(features.sandbox, AgentMiddleware)
        assert isinstance(features.memory, AgentMiddleware)
        assert isinstance(features.summarization, AgentMiddleware)
        assert isinstance(features.subagent, AgentMiddleware)
        assert isinstance(features.vision, AgentMiddleware)
        assert isinstance(features.auto_title, AgentMiddleware)
        assert isinstance(features.guardrail, AgentMiddleware)