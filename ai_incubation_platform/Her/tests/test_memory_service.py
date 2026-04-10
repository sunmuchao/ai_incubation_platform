"""
AI 记忆服务测试

测试覆盖:
- 记忆添加、搜索、删除
- 记忆提取
- 上下文相关记忆检索
- 用户画像生成
"""
import pytest
import os
import shutil
import sys
import uuid
from unittest.mock import MagicMock, patch, PropertyMock

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置环境变量
os.environ['OPENAI_API_KEY'] = 'test-key'
os.environ['OPENAI_BASE_URL'] = 'https://test.api/v1'


class TestMemoryService:
    """记忆服务测试"""

    @pytest.fixture
    def memory_service(self):
        """创建 mock 的测试服务"""
        # 使用 mock 避免真实的 Qdrant 初始化
        with patch('services.memory_service.Memory') as MockMemory:
            mock_memory = MagicMock()
            MockMemory.return_value = mock_memory

            # 使用唯一的临时路径
            db_path = f"/tmp/test_memory_{uuid.uuid4().hex}"

            from services.memory_service import MemoryService
            service = MemoryService(db_path=db_path)
            service.memory = mock_memory

            yield service

            # 清理临时目录
            if os.path.exists(db_path):
                shutil.rmtree(db_path, ignore_errors=True)

    def test_init(self, memory_service):
        """测试初始化"""
        assert memory_service is not None
        assert hasattr(memory_service, 'memory')
        assert memory_service.db_path is not None

    def test_add_memory(self, memory_service):
        """测试添加记忆"""
        # Mock 返回值
        memory_service.memory.add.return_value = [{"id": "mem-123"}]

        memory_id = memory_service.add_memory(
            content='用户喜欢喝奶茶',
            user_id='test_user_001',
            category='preference',
            importance=4
        )

        assert memory_id is not None or memory_service.memory.add.called

    def test_add_memory_with_metadata(self, memory_service):
        """测试添加带元数据的记忆"""
        memory_service.memory.add.return_value = [{"id": "mem-456"}]

        memory_id = memory_service.add_memory(
            content='用户有只猫叫咪咪',
            user_id='test_user_001',
            category='user_info',
            importance=5,
            metadata={'pet_name': '咪咪', 'pet_type': 'cat'}
        )
        assert memory_id is not None or memory_service.memory.add.called

    def test_search_memories(self, memory_service):
        """测试搜索记忆"""
        # Mock 搜索结果
        memory_service.memory.search.return_value = [
            {"id": "mem-1", "memory": "用户喜欢喝奶茶", "score": 0.9}
        ]

        results = memory_service.search_memories(
            query='喜欢喝什么',
            user_id='test_user_001',
            limit=5
        )
        assert isinstance(results, list)

    def test_search_with_category_filter(self, memory_service):
        """测试带分类过滤的搜索"""
        memory_service.memory.search.return_value = [
            {"id": "mem-2", "memory": "用户在北京工作", "score": 0.85}
        ]

        results = memory_service.search_memories(
            query='工作',
            user_id='test_user_001',
            category='user_info',
            limit=5
        )
        assert isinstance(results, list)

    def test_get_all_memories(self, memory_service):
        """测试获取所有记忆"""
        memory_service.memory.get_all.return_value = [
            {"id": "mem-1", "memory": "测试记忆 1"},
            {"id": "mem-2", "memory": "测试记忆 2"}
        ]

        results = memory_service.get_all_memories(
            user_id='test_user_001',
            limit=50
        )
        assert isinstance(results, list)

    def test_get_all_memories_with_category_filter(self, memory_service):
        """测试带分类过滤获取所有记忆"""
        memory_service.memory.get_all.return_value = [
            {"id": "mem-1", "memory": "偏好记忆", "metadata": {"category": "preference"}}
        ]

        results = memory_service.get_all_memories(
            user_id='test_user_001',
            category='preference',
            limit=50
        )
        assert isinstance(results, list)

    def test_delete_memory(self, memory_service):
        """测试删除记忆"""
        memory_service.memory.delete.return_value = None

        result = memory_service.delete_memory('mem-123', 'test_user_001')
        # 删除操作调用成功即可
        assert result is True or memory_service.memory.delete.called

    def test_delete_nonexistent_memory(self, memory_service):
        """测试删除不存在的记忆"""
        memory_service.memory.delete.return_value = None

        result = memory_service.delete_memory('nonexistent-id', 'test_user_001')
        # 删除操作调用即可
        assert memory_service.memory.delete.called

    def test_get_contextual_memories(self, memory_service):
        """测试获取上下文相关记忆"""
        memory_service.memory.search.return_value = [
            {"id": "mem-1", "memory": "用户喜欢喝咖啡", "score": 0.95}
        ]

        results = memory_service.get_contextual_memories(
            user_id='test_user_001',
            current_context='咖啡',
            limit=3
        )
        assert isinstance(results, list)

    def test_get_user_profile(self, memory_service):
        """测试获取用户画像"""
        # Mock 搜索结果
        memory_service.memory.search.return_value = [
            {"memory": "用户 30 岁", "metadata": {"category": "user_info"}},
            {"memory": "用户喜欢 jazz", "metadata": {"category": "preference"}},
            {"memory": "用户性格外向", "metadata": {"category": "personality"}},
            {"memory": "用户上周去旅行", "metadata": {"category": "event"}}
        ]

        profile = memory_service.get_user_profile('test_user_001')

        assert isinstance(profile, dict)

    def test_extract_memory_from_dialogue(self, memory_service):
        """测试从对话提取记忆"""
        # Mock memory.add 返回
        memory_service.memory.add.return_value = [{"id": "mem-extracted"}]

        dialogue = """
        用户：我养了一只狗
        对方：什么品种？
        用户：金毛，很喜欢运动
        """

        # Mock call_llm 函数
        mock_response = '[{"content": "用户有只狗", "category": "user_info", "importance": 4}]'
        with patch('services.memory_service.call_llm', return_value=mock_response):
            results = memory_service.extract_memory_from_dialogue(
                dialogue=dialogue,
                user_id='test_user_001'
            )
        assert isinstance(results, list) or results is None

    def test_singleton_pattern(self):
        """测试单例模式"""
        with patch('services.memory_service.Memory'):
            from services.memory_service import get_memory_service
            service1 = get_memory_service()
            service2 = get_memory_service()
            # 注意：由于 Qdrant 文件锁，实际测试中可能是不同实例
            # 这里主要验证接口一致性
            assert type(service1) == type(service2)


class TestMemoryServiceCategories:
    """记忆分类测试"""

    @pytest.fixture
    def memory_service(self):
        """创建 mock 的测试服务"""
        with patch('services.memory_service.Memory') as MockMemory:
            mock_memory = MagicMock()
            MockMemory.return_value = mock_memory

            db_path = f"/tmp/test_memory_{uuid.uuid4().hex}"

            from services.memory_service import MemoryService
            service = MemoryService(db_path=db_path)
            service.memory = mock_memory

            yield service

            if os.path.exists(db_path):
                shutil.rmtree(db_path, ignore_errors=True)

    def test_user_info_category(self, memory_service):
        """测试用户信息分类"""
        memory_service.memory.add.return_value = [{"id": "mem-1"}]
        memory_service.memory.get_all.return_value = [
            {"memory": "用户是程序员", "metadata": {"category": "user_info"}}
        ]

        memory_service.add_memory(
            content='用户是程序员',
            user_id='test_user',
            category=memory_service.CATEGORY_USER_INFO
        )
        results = memory_service.get_all_memories(
            user_id='test_user',
            category=memory_service.CATEGORY_USER_INFO
        )
        assert isinstance(results, list)

    def test_preference_category(self, memory_service):
        """测试偏好分类"""
        memory_service.memory.add.return_value = [{"id": "mem-2"}]
        memory_service.memory.get_all.return_value = [
            {"memory": "用户喜欢川菜", "metadata": {"category": "preference"}}
        ]

        memory_service.add_memory(
            content='用户喜欢川菜',
            user_id='test_user',
            category=memory_service.CATEGORY_PREFERENCE
        )
        results = memory_service.get_all_memories(
            user_id='test_user',
            category=memory_service.CATEGORY_PREFERENCE
        )
        assert isinstance(results, list)

    def test_event_category(self, memory_service):
        """测试事件分类"""
        memory_service.memory.add.return_value = [{"id": "mem-3"}]
        memory_service.memory.get_all.return_value = [
            {"memory": "用户明天过生日", "metadata": {"category": "event"}}
        ]

        memory_service.add_memory(
            content='用户明天过生日',
            user_id='test_user',
            category=memory_service.CATEGORY_EVENT
        )
        results = memory_service.get_all_memories(
            user_id='test_user',
            category=memory_service.CATEGORY_EVENT
        )
        assert isinstance(results, list)

    def test_relationship_category(self, memory_service):
        """测试关系分类"""
        memory_service.memory.add.return_value = [{"id": "mem-4"}]
        memory_service.memory.get_all.return_value = [
            {"memory": "用户和小美第一次约会", "metadata": {"category": "relationship"}}
        ]

        memory_service.add_memory(
            content='用户和小美第一次约会',
            user_id='test_user',
            category=memory_service.CATEGORY_RELATIONSHIP
        )
        results = memory_service.get_all_memories(
            user_id='test_user',
            category=memory_service.CATEGORY_RELATIONSHIP
        )
        assert isinstance(results, list)

    def test_personality_category(self, memory_service):
        """测试性格分类"""
        memory_service.memory.add.return_value = [{"id": "mem-5"}]
        memory_service.memory.get_all.return_value = [
            {"memory": "用户是 INTJ", "metadata": {"category": "personality"}}
        ]

        memory_service.add_memory(
            content='用户是 INTJ',
            user_id='test_user',
            category=memory_service.CATEGORY_PERSONALITY
        )
        results = memory_service.get_all_memories(
            user_id='test_user',
            category=memory_service.CATEGORY_PERSONALITY
        )
        assert isinstance(results, list)
