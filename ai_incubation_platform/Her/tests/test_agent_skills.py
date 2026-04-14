"""
Agent Skills 边缘场景测试

测试覆盖:
1. BaseSkill 基类测试 (8 tests)
2. SkillRegistry 注册表测试 (12 tests)
3. 具体 Skill 实现测试 (15 tests)
4. Skill 执行边缘场景 (10 tests)
5. 异步执行测试 (6 tests)

总计: 51 个测试用例
"""
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

from agent.skills.base import BaseSkill
from agent.skills.registry import SkillRegistry, get_skill_registry, initialize_default_skills


# ============= Mock Skill 用于测试 =============

class MockSkill(BaseSkill):
    """Mock Skill for testing"""

    name = "mock_skill"
    version = "1.0.0"
    description = "A mock skill for testing"

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "action": {"type": "string"},
            },
            "required": ["user_id"],
        }

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "data": {"type": "object"},
            },
        }

    async def execute(self, **kwargs) -> dict:
        if kwargs.get("fail"):
            return {"success": False, "error": "Intentional failure"}

        return {
            "success": True,
            "ai_message": f"Executed with user_id: {kwargs.get('user_id')}",
            "data": {"result": "ok"},
        }


class SyncMockSkill(BaseSkill):
    """同步执行的 Mock Skill"""

    name = "sync_mock_skill"
    version = "1.0.0"
    description = "A synchronous mock skill"

    def get_input_schema(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    def get_output_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    def execute(self, **kwargs) -> dict:
        return {"success": True, "data": {"sync": True}}


class InvalidSkill:
    """没有 execute 方法的无效 Skill"""

    name = "invalid_skill"
    description = "An invalid skill without execute method"


# ============= 第一部分：BaseSkill 基类测试 =============

class TestBaseSkill:
    """BaseSkill 基类测试"""

    def test_skill_metadata(self):
        """测试 Skill 元数据"""
        skill = MockSkill()

        assert skill.name == "mock_skill"
        assert skill.version == "1.0.0"
        assert skill.description == "A mock skill for testing"

    def test_get_input_schema(self):
        """测试获取输入 Schema"""
        skill = MockSkill()
        schema = skill.get_input_schema()

        assert schema["type"] == "object"
        assert "user_id" in schema["required"]
        assert "action" in schema["properties"]

    def test_get_output_schema(self):
        """测试获取输出 Schema"""
        skill = MockSkill()
        schema = skill.get_output_schema()

        assert schema["type"] == "object"
        assert "success" in schema["properties"]

    def test_get_metadata(self):
        """测试获取完整元数据"""
        skill = MockSkill()
        metadata = skill.get_metadata()

        assert metadata["name"] == "mock_skill"
        assert metadata["version"] == "1.0.0"
        assert "input_schema" in metadata
        assert "output_schema" in metadata

    def test_validate_input_valid(self):
        """测试有效输入验证"""
        skill = MockSkill()
        is_valid, error = skill.validate_input({"user_id": "test_user"})

        assert is_valid is True
        assert error is None

    def test_validate_input_missing_required(self):
        """测试缺少必填字段"""
        skill = MockSkill()
        is_valid, error = skill.validate_input({"action": "test"})

        assert is_valid is False
        assert "user_id" in error

    def test_validate_input_not_dict(self):
        """测试非字典输入"""
        skill = MockSkill()
        is_valid, error = skill.validate_input("not a dict")

        assert is_valid is False
        assert "dictionary" in error.lower()

    def test_log_execution(self):
        """测试执行日志"""
        skill = MockSkill()

        with patch("utils.logger.logger") as mock_logger:
            skill._log_execution("Test message", "info")
            mock_logger.info.assert_called_once()


# ============= 第二部分：SkillRegistry 注册表测试 =============

class TestSkillRegistry:
    """SkillRegistry 注册表测试"""

    @pytest.fixture(autouse=True)
    def setup_registry(self):
        """每个测试前清空注册表"""
        registry = SkillRegistry.get_instance()
        registry.clear()
        yield registry

    def test_singleton_pattern(self):
        """测试单例模式"""
        registry1 = SkillRegistry.get_instance()
        registry2 = SkillRegistry.get_instance()

        assert registry1 is registry2

    def test_register_skill(self, setup_registry):
        """测试注册 Skill"""
        registry = setup_registry
        skill = MockSkill()

        registry.register(skill)

        assert registry.get("mock_skill") == skill

    def test_register_skill_with_custom_name(self, setup_registry):
        """测试使用自定义名称注册"""
        registry = setup_registry
        skill = MockSkill()

        registry.register(skill, name="custom_name")

        assert registry.get("custom_name") == skill

    def test_register_skill_with_tags(self, setup_registry):
        """测试带标签注册"""
        registry = setup_registry
        skill = MockSkill()

        registry.register(skill, tags=["test", "mock"])

        metadata = registry.get_metadata("mock_skill")
        assert "test" in metadata["tags"]
        assert "mock" in metadata["tags"]

    def test_register_skill_without_name_raises_error(self, setup_registry):
        """测试无名称 Skill 注册抛出错误"""
        registry = setup_registry

        # 创建一个没有 name 属性的对象
        class NoNameSkill:
            description = "No name skill"

        invalid_skill = NoNameSkill()

        with pytest.raises(ValueError, match="name"):
            registry.register(invalid_skill)

    def test_register_duplicate_overwrites(self, setup_registry):
        """测试重复注册覆盖"""
        registry = setup_registry
        skill1 = MockSkill()
        skill2 = MockSkill()

        registry.register(skill1)
        registry.register(skill2)

        assert registry.get("mock_skill") == skill2

    def test_get_nonexistent_skill(self, setup_registry):
        """测试获取不存在的 Skill"""
        registry = setup_registry

        assert registry.get("nonexistent") is None

    def test_list_skills(self, setup_registry):
        """测试列出所有 Skill"""
        registry = setup_registry
        registry.register(MockSkill())
        registry.register(SyncMockSkill())

        skills = registry.list_skills()

        assert len(skills) == 2

    def test_list_skills_by_tag(self, setup_registry):
        """测试按标签筛选 Skill"""
        registry = setup_registry
        registry.register(MockSkill(), tags=["core"])
        registry.register(SyncMockSkill(), tags=["test"])

        skills = registry.list_skills(tag="core")

        assert len(skills) == 1
        assert skills[0]["name"] == "mock_skill"

    def test_clear_registry(self, setup_registry):
        """测试清空注册表"""
        registry = setup_registry
        registry.register(MockSkill())

        registry.clear()

        assert registry.list_skills() == []

    def test_get_metadata(self, setup_registry):
        """测试获取 Skill 元数据"""
        registry = setup_registry
        registry.register(MockSkill())

        metadata = registry.get_metadata("mock_skill")

        assert metadata is not None
        assert "description" in metadata
        assert "version" in metadata

    def test_get_metadata_nonexistent(self, setup_registry):
        """测试获取不存在 Skill 的元数据"""
        registry = setup_registry

        assert registry.get_metadata("nonexistent") is None


# ============= 第三部分：Skill 执行测试 =============

class TestSkillExecution:
    """Skill 执行测试"""

    @pytest.fixture(autouse=True)
    def setup_registry(self):
        """每个测试前清空注册表"""
        registry = SkillRegistry.get_instance()
        registry.clear()
        yield registry

    @pytest.mark.asyncio
    async def test_execute_async_skill(self, setup_registry):
        """测试执行异步 Skill"""
        registry = setup_registry
        registry.register(MockSkill())

        result = await registry.execute("mock_skill", user_id="test_user")

        assert result["success"] is True
        assert "test_user" in result["ai_message"]

    @pytest.mark.asyncio
    async def test_execute_sync_skill(self, setup_registry):
        """测试执行同步 Skill"""
        registry = setup_registry
        registry.register(SyncMockSkill())

        result = await registry.execute("sync_mock_skill")

        assert result["success"] is True
        assert result["data"]["sync"] is True

    @pytest.mark.asyncio
    async def test_execute_nonexistent_skill(self, setup_registry):
        """测试执行不存在的 Skill"""
        registry = setup_registry

        result = await registry.execute("nonexistent_skill")

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_skill_with_failure(self, setup_registry):
        """测试执行失败的 Skill"""
        registry = setup_registry
        registry.register(MockSkill())

        result = await registry.execute("mock_skill", user_id="test", fail=True)

        assert result["success"] is False
        assert "Intentional failure" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_skill_without_execute_method(self, setup_registry):
        """测试执行没有 execute 方法的 Skill"""
        registry = setup_registry
        registry.register(InvalidSkill())

        result = await registry.execute("invalid_skill")

        assert result["success"] is False
        assert "no execute method" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_skill_with_exception(self, setup_registry):
        """测试执行抛出异常的 Skill"""

        class ExceptionSkill(BaseSkill):
            name = "exception_skill"
            version = "1.0.0"
            description = "Throws exception"

            def get_input_schema(self):
                return {}

            def get_output_schema(self):
                return {}

            async def execute(self, **kwargs):
                raise RuntimeError("Unexpected error")

        registry = setup_registry
        registry.register(ExceptionSkill())

        result = await registry.execute("exception_skill")

        assert result["success"] is False
        assert "Unexpected error" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_with_extra_params(self, setup_registry):
        """测试带额外参数执行"""
        registry = setup_registry
        registry.register(MockSkill())

        result = await registry.execute(
            "mock_skill",
            user_id="test",
            extra_param="value",
            another_param=123,
        )

        assert result["success"] is True


# ============= 第四部分：边缘场景测试 =============

class TestSkillEdgeCases:
    """Skill 边缘场景测试"""

    @pytest.fixture(autouse=True)
    def setup_registry(self):
        """每个测试前清空注册表"""
        registry = SkillRegistry.get_instance()
        registry.clear()
        yield registry

    def test_skill_with_empty_name(self, setup_registry):
        """测试空名称 Skill"""

        class EmptyNameSkill(BaseSkill):
            name = ""
            version = "1.0.0"
            description = "Empty name"

            def get_input_schema(self):
                return {}

            def get_output_schema(self):
                return {}

            async def execute(self, **kwargs):
                return {"success": True}

        registry = setup_registry
        skill = EmptyNameSkill()

        with pytest.raises(ValueError):
            registry.register(skill)

    def test_skill_with_special_characters_name(self, setup_registry):
        """测试特殊字符名称 Skill"""

        class SpecialCharSkill(BaseSkill):
            name = "skill-with_special.chars"
            version = "1.0.0"
            description = "Special chars"

            def get_input_schema(self):
                return {}

            def get_output_schema(self):
                return {}

            async def execute(self, **kwargs):
                return {"success": True}

        registry = setup_registry
        skill = SpecialCharSkill()

        registry.register(skill)

        assert registry.get("skill-with_special.chars") is not None

    def test_skill_with_unicode_name(self, setup_registry):
        """测试 Unicode 名称 Skill"""

        class UnicodeSkill(BaseSkill):
            name = "技能_中文"
            version = "1.0.0"
            description = "Unicode name"

            def get_input_schema(self):
                return {}

            def get_output_schema(self):
                return {}

            async def execute(self, **kwargs):
                return {"success": True}

        registry = setup_registry
        skill = UnicodeSkill()

        registry.register(skill)

        assert registry.get("技能_中文") is not None

    def test_skill_with_empty_schema(self, setup_registry):
        """测试空 Schema Skill"""

        class EmptySchemaSkill(BaseSkill):
            name = "empty_schema"
            version = "1.0.0"
            description = "Empty schema"

            def get_input_schema(self):
                return {}

            def get_output_schema(self):
                return {}

            async def execute(self, **kwargs):
                return {"success": True}

        registry = setup_registry
        skill = EmptySchemaSkill()

        registry.register(skill)

        assert skill.validate_input({}) == (True, None)

    def test_skill_validate_input_with_none(self, setup_registry):
        """测试 None 输入验证"""
        skill = MockSkill()
        is_valid, error = skill.validate_input(None)

        assert is_valid is False

    def test_skill_with_large_input(self, setup_registry):
        """测试大输入数据"""

        class LargeInputSkill(BaseSkill):
            name = "large_input"
            version = "1.0.0"
            description = "Handles large input"

            def get_input_schema(self):
                return {"type": "object", "properties": {}, "required": []}

            def get_output_schema(self):
                return {}

            async def execute(self, **kwargs):
                return {"success": True, "data_size": len(str(kwargs))}

        registry = setup_registry
        skill = LargeInputSkill()
        registry.register(skill)

        # 大数据输入
        large_data = {"data": "A" * 10000}

        # 验证不会崩溃
        is_valid, _ = skill.validate_input(large_data)
        assert is_valid is True

    def test_skill_with_nested_data(self, setup_registry):
        """测试嵌套数据输入"""

        class NestedSkill(BaseSkill):
            name = "nested"
            version = "1.0.0"
            description = "Handles nested data"

            def get_input_schema(self):
                return {"type": "object", "properties": {}, "required": []}

            def get_output_schema(self):
                return {}

            async def execute(self, **kwargs):
                return {"success": True}

        registry = setup_registry
        skill = NestedSkill()
        registry.register(skill)

        nested_data = {
            "level1": {
                "level2": {
                    "level3": {"value": "deep"},
                },
            },
        }

        is_valid, _ = skill.validate_input(nested_data)
        assert is_valid is True

    def test_multiple_registries_are_same(self):
        """测试多次获取注册表返回同一实例"""
        SkillRegistry._instance = None  # 重置

        registry1 = SkillRegistry()
        registry2 = SkillRegistry()

        assert registry1 is registry2

    @pytest.mark.asyncio
    async def test_concurrent_skill_execution(self, setup_registry):
        """测试并发执行 Skill"""
        registry = setup_registry
        registry.register(MockSkill())

        # 并发执行
        tasks = [
            registry.execute("mock_skill", user_id=f"user_{i}")
            for i in range(10)
        ]

        results = await asyncio.gather(*tasks)

        assert all(r["success"] for r in results)


# ============= 第五部分：具体 Skill 测试 =============

class TestDefaultSkills:
    """默认 Skill 测试"""

    def test_initialize_default_skills(self):
        """测试初始化默认 Skills"""
        registry = get_skill_registry()
        registry.clear()

        initialized = initialize_default_skills()

        skills = initialized.list_skills()

        # 应该有多个默认 Skill
        assert len(skills) > 0

    # 注：matchmaking_skill 已废弃，匹配功能使用 ConversationMatchService + DeerFlow her_tools
    # 此测试已改为测试 precommunication_skill
    def test_get_precommunication_skill(self):
        """测试获取预沟通 Skill"""
        from agent.skills.precommunication_skill import get_precommunication_skill

        skill = get_precommunication_skill()

        assert skill.name == "pre_communication"
        assert skill.execute is not None

    @pytest.mark.asyncio
    async def test_precommunication_skill_execute(self):
        """测试预沟通 Skill 执行"""
        from agent.skills.precommunication_skill import get_precommunication_skill

        skill = get_precommunication_skill()

        # 测试 execute 方法存在
        assert hasattr(skill, 'execute')

        # 调用 execute 方法（简单参数测试）
        result = await skill.execute(
            user_id="test_user",
            match_id="test_match",
            action="start_conversation"
        )
        assert "success" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])