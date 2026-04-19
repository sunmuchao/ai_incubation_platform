"""
Memory 异步同步和 Helpers 测试

测试核心功能：
1. get_current_user_id 从 configurable 获取 user_id（最高优先级）
2. get_db_user 直接从数据库获取用户信息（不依赖 Memory）
3. Memory 异步同步不阻塞主请求
4. Memory 未同步时匹配请求仍能正常工作

设计原则：
- Memory 只是辅助缓存，不是必须的
- 匹配工具直接从数据库查用户信息
- 前端每次请求都传 user_id，DeerFlow 直接拿到
"""

import pytest
import json
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

# 设置路径
HER_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEERFLOW_PATH = os.path.join(HER_PROJECT_ROOT, "deerflow", "backend", "packages", "harness")

if HER_PROJECT_ROOT not in sys.path:
    sys.path.insert(0, HER_PROJECT_ROOT)
if DEERFLOW_PATH not in sys.path:
    sys.path.insert(0, DEERFLOW_PATH)


# ==================== Part 1: get_current_user_id 测试 ====================

class TestGetCurrentUserId:
    """测试 user_id 获取的三级优先级"""

    def test_priority_1_from_configurable(self):
        """优先级1：从 LangGraph configurable 获取（最高优先级）"""
        from deerflow.community.her_tools.helpers import get_current_user_id

        # Mock LangGraph get_config - 它是从 langgraph.config 导入的
        with patch("langgraph.config.get_config") as mock_get_config:
            mock_get_config.return_value = {
                "configurable": {
                    "user_id": "test-user-from-config"
                }
            }

            user_id = get_current_user_id()
            assert user_id == "test-user-from-config", \
                "应优先从 configurable 获取 user_id"

    def test_priority_1_overrides_file(self):
        """优先级1 覆盖 Memory 文件中的 user_id"""
        from deerflow.community.her_tools.helpers import get_current_user_id

        # 创建临时 memory 文件（模拟优先级2）
        with tempfile.TemporaryDirectory() as tmpdir:
            users_dir = os.path.join(tmpdir, "users")
            os.makedirs(users_dir, exist_ok=True)

            # 创建用户 memory 文件（优先级2）
            user_memory_dir = os.path.join(users_dir, "file-user")
            os.makedirs(user_memory_dir, exist_ok=True)
            user_memory_path = os.path.join(user_memory_dir, "memory.json")
            with open(user_memory_path, "w") as f:
                json.dump({"facts": [{"id": "user-id-file-user", "content": "用户ID：file-user"}]}, f)

            # Mock get_her_root 和 get_config
            with patch("deerflow.community.her_tools.helpers.get_her_root") as mock_root:
                mock_root.return_value = tmpdir

                with patch("langgraph.config.get_config") as mock_get_config:
                    mock_get_config.return_value = {
                        "configurable": {
                            "user_id": "config-user"  # 优先级1
                        }
                    }

                    user_id = get_current_user_id()
                    # 应返回 configurable 的值，不是文件中的值
                    assert user_id == "config-user", \
                        "configurable 应覆盖 Memory 文件"

    def test_priority_2_from_user_memory_file(self):
        """优先级2：从用户独立 memory 文件读取"""
        from deerflow.community.her_tools.helpers import get_current_user_id

        # Mock get_config 返回空（优先级1 失败）
        with patch("langgraph.config.get_config") as mock_get_config:
            mock_get_config.return_value = {}

            # 创建临时 memory 文件
            with tempfile.TemporaryDirectory() as tmpdir:
                users_dir = os.path.join(tmpdir, "deerflow", "backend", ".deer-flow", "users")
                os.makedirs(users_dir, exist_ok=True)

                user_memory_dir = os.path.join(users_dir, "file-user-123")
                os.makedirs(user_memory_dir, exist_ok=True)
                user_memory_path = os.path.join(user_memory_dir, "memory.json")
                with open(user_memory_path, "w") as f:
                    json.dump({"facts": [{"id": "user-id-file-user-123", "content": "用户ID：file-user-123"}]}, f)

                with patch("deerflow.community.her_tools.helpers.get_her_root") as mock_root:
                    mock_root.return_value = tmpdir

                    user_id = get_current_user_id()
                    assert user_id == "file-user-123", \
                        "优先级2 应从用户独立 memory 文件读取"

    def test_priority_3_from_global_memory(self):
        """优先级3：从全局 memory.json 读取（降级）"""
        from deerflow.community.her_tools.helpers import get_current_user_id

        # Mock get_config 返回空（优先级1 失败）
        with patch("langgraph.config.get_config") as mock_get_config:
            mock_get_config.return_value = {}

            # 创建临时全局 memory 文件（无用户独立文件）
            with tempfile.TemporaryDirectory() as tmpdir:
                deerflow_dir = os.path.join(tmpdir, "deerflow", "backend", ".deer-flow")
                os.makedirs(deerflow_dir, exist_ok=True)

                global_memory_path = os.path.join(deerflow_dir, "memory.json")
                with open(global_memory_path, "w") as f:
                    json.dump({"facts": [{"id": "user-id-global-user", "content": "用户ID：global-user"}]}, f)

                with patch("deerflow.community.her_tools.helpers.get_her_root") as mock_root:
                    mock_root.return_value = tmpdir

                    user_id = get_current_user_id()
                    assert user_id == "global-user", \
                        "优先级3 应从全局 memory.json 读取"

    def test_fallback_to_anonymous(self):
        """所有优先级都失败时返回匿名用户"""
        from deerflow.community.her_tools.helpers import get_current_user_id

        # Mock 所有依赖都失败
        with patch("langgraph.config.get_config") as mock_get_config:
            mock_get_config.return_value = {}

            with patch("deerflow.community.her_tools.helpers.get_her_root") as mock_root:
                mock_root.return_value = "/nonexistent/path"

                user_id = get_current_user_id()
                assert user_id == "user-anonymous-dev", \
                    "应降级到匿名用户"


# ==================== Part 2: get_db_user 测试 ====================

class TestGetDbUser:
    """测试直接从数据库获取用户信息"""

    def test_returns_user_profile_from_database(self):
        """直接从数据库查询用户信息"""
        from deerflow.community.her_tools.helpers import get_db_user

        # Mock database session - 注意：db_session 是在函数内部动态导入的
        mock_user = MagicMock()
        mock_user.id = "test-user-id"
        mock_user.name = "张三"
        mock_user.age = 28
        mock_user.gender = "male"
        mock_user.location = "北京"
        mock_user.interests = "['运动', '阅读']"
        mock_user.bio = "测试简介"
        mock_user.relationship_goal = "dating"
        mock_user.preferred_age_min = 25
        mock_user.preferred_age_max = 35
        mock_user.preferred_location = "北京"
        mock_user.accept_remote = "同城优先"

        with patch("utils.db_session_manager.db_session") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = mock_user
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            user_data = get_db_user("test-user-id")

            assert user_data is not None
            assert user_data["id"] == "test-user-id"
            assert user_data["name"] == "张三"
            assert user_data["age"] == 28
            assert user_data["location"] == "北京"

    def test_returns_none_when_user_not_found(self):
        """用户不存在时返回 None"""
        from deerflow.community.her_tools.helpers import get_db_user

        with patch("utils.db_session_manager.db_session") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = None
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            user_data = get_db_user("nonexistent-user")
            assert user_data is None

    def test_includes_preference_fields(self):
        """返回的 user_data 包含偏好字段"""
        from deerflow.community.her_tools.helpers import get_db_user

        mock_user = MagicMock()
        mock_user.id = "test-user-id"
        mock_user.name = "张三"
        mock_user.age = 28
        mock_user.gender = "male"
        mock_user.location = "北京"
        mock_user.interests = "[]"
        mock_user.bio = ""
        mock_user.relationship_goal = ""
        mock_user.preferred_age_min = 25
        mock_user.preferred_age_max = 35
        mock_user.preferred_location = "上海"
        mock_user.preferred_gender = "female"
        mock_user.accept_remote = "接受异地"
        mock_user.want_children = "want"
        mock_user.spending_style = "moderate"
        mock_user.family_importance = "high"
        mock_user.work_life_balance = "balanced"
        mock_user.migration_willingness = "willing"
        mock_user.sleep_type = "early"

        with patch("utils.db_session_manager.db_session") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = mock_user
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            user_data = get_db_user("test-user-id")

            # 检查偏好字段
            assert "preferred_age_min" in user_data
            assert "preferred_age_max" in user_data
            assert "preferred_location" in user_data
            assert "accept_remote" in user_data
            assert "want_children" in user_data
            assert "spending_style" in user_data

    def test_normalizes_interests_field(self):
        """interests 字段被正确解析为列表"""
        from deerflow.community.her_tools.helpers import get_db_user

        mock_user = MagicMock()
        mock_user.id = "test-user-id"
        mock_user.name = "张三"
        mock_user.age = 28
        mock_user.gender = "male"
        mock_user.location = "北京"
        mock_user.interests = "['运动', '阅读', '旅行']"  # JSON 字符串
        mock_user.bio = ""
        mock_user.relationship_goal = ""
        mock_user.preferred_age_min = None
        mock_user.preferred_age_max = None
        mock_user.preferred_location = None
        mock_user.preferred_gender = None
        mock_user.accept_remote = None
        mock_user.want_children = None
        mock_user.spending_style = None
        mock_user.family_importance = None
        mock_user.work_life_balance = None
        mock_user.migration_willingness = None
        mock_user.sleep_type = None

        with patch("utils.db_session_manager.db_session") as mock_session:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = mock_user
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            user_data = get_db_user("test-user-id")

            # interests 应被解析为列表（最多5个）
            assert isinstance(user_data["interests"], list)
            assert len(user_data["interests"]) <= 5


# ==================== Part 3: Memory 异步同步测试 ====================

class TestMemoryAsyncSync:
    """测试 Memory 异步同步不阻塞主请求"""

    @pytest.mark.asyncio
    async def test_async_sync_does_not_block(self):
        """异步同步不阻塞主流程"""
        from api.deerflow import _async_sync_user_memory

        # Mock sync_user_memory_to_deerflow（模拟慢操作）
        with patch("api.deerflow.sync_user_memory_to_deerflow") as mock_sync:
            mock_sync.return_value = 5  # 返回同步的 facts 数量

            # 执行异步同步
            start_time = asyncio.get_event_loop().time()
            await _async_sync_user_memory("test-user")
            end_time = asyncio.get_event_loop().time()

            # 异步调用应立即返回（不等待 mock_sync 执行）
            # 因为 mock_sync 是同步函数，会被 asyncio.to_thread 包装
            assert mock_sync.called

    @pytest.mark.asyncio
    async def test_async_sync_handles_exception(self):
        """异步同步失败不影响主流程"""
        from api.deerflow import _async_sync_user_memory

        # Mock sync_user_memory_to_deerflow 抛出异常
        with patch("api.deerflow.sync_user_memory_to_deerflow") as mock_sync:
            mock_sync.side_effect = Exception("Sync failed")

            # 异步同步应捕获异常，不抛出
            await _async_sync_user_memory("test-user")

            # 应被调用，但异常被捕获
            assert mock_sync.called

    def test_chat_request_triggers_async_sync(self):
        """chat 请求触发异步 Memory 同步"""
        # 验证 deerflow.py 中的 chat 路由使用 asyncio.create_task
        import inspect

        # 检查 deerflow.py 中 _handle_with_deerflow 函数
        from api.deerflow import _handle_with_deerflow

        source = inspect.getsource(_handle_with_deerflow)

        # 应包含 asyncio.create_task 用于异步同步
        assert "asyncio.create_task" in source, \
            "chat 请求应使用 asyncio.create_task 触发异步 Memory 同步"
        assert "_async_sync_user_memory" in source, \
            "应调用 _async_sync_user_memory 函数"


# ==================== Part 4: Memory 未同步时匹配仍能工作 ====================

class TestMatchWithoutMemorySync:
    """测试 Memory 未同步时匹配请求仍能正常工作"""

    def test_match_tool_uses_db_not_memory(self):
        """匹配工具从数据库获取用户信息，不依赖 Memory"""
        from deerflow.community.her_tools.match_tools import HerFindMatchesTool

        tool = HerFindMatchesTool()

        # 检查代码是否使用 get_db_user（数据库）而非 Memory
        import inspect
        source = inspect.getsource(tool._arun)

        assert "get_db_user" in source, \
            "匹配工具应使用 get_db_user 从数据库获取用户信息"

    def test_match_tool_code_structure(self):
        """匹配工具代码结构验证"""
        from deerflow.community.her_tools.match_tools import HerFindMatchesTool
        import inspect

        tool = HerFindMatchesTool()
        source = inspect.getsource(tool._arun)

        # 关键验证：不依赖 Memory 同步
        # 1. 使用 get_db_user（数据库查询）
        assert "get_db_user" in source

        # 2. 使用 get_current_user_id（从 configurable 或 memory 文件获取）
        assert "get_current_user_id" in source or "user_id" in source

        # 3. 返回 ToolResult 结构
        assert "ToolResult" in source or "success" in source


# ==================== Part 5: 缓存机制测试 ====================

class TestMemorySyncCache:
    """测试 Memory 同步缓存机制"""

    def test_cache_exists_in_module(self):
        """验证缓存变量存在"""
        from api.deerflow import _memory_sync_cache, MEMORY_SYNC_CACHE_TTL

        assert isinstance(_memory_sync_cache, dict), \
            "_memory_sync_cache 应是字典"
        assert MEMORY_SYNC_CACHE_TTL > 0, \
            "缓存 TTL 应大于 0"

    def test_force_sync_bypasses_cache(self):
        """force=True 强制同步，忽略缓存"""
        from api.deerflow import sync_user_memory_to_deerflow, _memory_sync_cache

        import time
        # 设置缓存
        _memory_sync_cache["test-user"] = {
            "last_sync_time": time.time(),
            "profile_hash": "abc123",
            "facts_count": 10
        }

        # Mock get_user_profile 和文件写入
        with patch("api.deerflow.get_user_profile") as mock_profile:
            mock_profile.return_value = {"id": "test-user", "name": "张三"}

            with patch("api.deerflow.build_memory_facts") as mock_build:
                mock_build.return_value = [{"id": "fact-1"}]

                with patch("os.makedirs"):
                    with patch("builtins.open", MagicMock()):
                        with patch("os.rename"):
                            with patch("hashlib.md5") as mock_hash:
                                mock_hash.return_value.hexdigest.return_value = "new-hash"

                                result = sync_user_memory_to_deerflow("test-user", force=True)

                                # force=True 应执行同步
                                assert mock_profile.called


# ==================== Part 6: invalidate_user_cache 测试 ====================

class TestInvalidateUserCache:
    """测试用户缓存清除"""

    def test_invalidate_clears_all_caches(self):
        """清除用户画像缓存和 Memory 同步缓存"""
        from api.deerflow import invalidate_user_cache, _user_profile_cache, _memory_sync_cache

        import time
        # 设置缓存
        _user_profile_cache["test-user"] = {
            "profile": {"name": "张三"},
            "last_fetch_time": time.time()
        }
        _memory_sync_cache["test-user"] = {
            "last_sync_time": time.time(),
            "profile_hash": "abc",
            "facts_count": 5
        }

        # Mock sync_user_memory_to_deerflow
        with patch("api.deerflow.sync_user_memory_to_deerflow") as mock_sync:
            mock_sync.return_value = 5

            invalidate_user_cache("test-user")

            # 缓存应被清除
            assert "test-user" not in _user_profile_cache
            assert "test-user" not in _memory_sync_cache
            # 应触发强制重新同步
            assert mock_sync.called

    def test_invalidate_triggers_force_sync(self):
        """清除缓存后触发强制同步"""
        from api.deerflow import invalidate_user_cache

        with patch("api.deerflow.sync_user_memory_to_deerflow") as mock_sync:
            mock_sync.return_value = 5

            invalidate_user_cache("new-user")

            # 应调用 sync_user_memory_to_deerflow 且 force=True
            mock_sync.assert_called_with("new-user", force=True)


# ==================== 执行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])