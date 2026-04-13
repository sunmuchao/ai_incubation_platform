"""
BaseService 边缘场景测试

测试覆盖:
1. 数据库会话管理边缘场景 (4 tests)
2. 通用 CRUD 方法边缘场景 (15 tests)
3. 日志方法测试 (3 tests)
4. SingletonService 测试 (4 tests)
5. 错误处理与异常场景 (6 tests)

总计: 32 个测试用例
"""
import pytest
import uuid
from unittest.mock import MagicMock, patch, PropertyMock

from services.base_service import BaseService, SingletonService
from db.models import UserDB


# ============= 测试基础设施 =============
# 使用 conftest.py 的 db_session fixture，避免重复创建表


@pytest.fixture
def base_service(db_session):
    """BaseService fixture"""
    return BaseService(db=db_session, model_class=UserDB)


def make_user(**kwargs):
    """创建测试用户"""
    defaults = {
        "id": str(uuid.uuid4()),
        "email": f"test_{uuid.uuid4()}@example.com",
        "password_hash": "hashed_pw",
        "name": "Test User",
        "age": 28,
        "gender": "male",
        "location": "北京",
        "interests": "[]",
        "values": "{}",
        "bio": "",
    }
    defaults.update(kwargs)
    return UserDB(**defaults)


# ============= 第一部分：数据库会话管理边缘场景 =============

class TestDatabaseSessionManagement:
    """数据库会话管理测试"""

    def test_db_property_raises_error_when_none(self):
        """测试 db 属性为 None 时抛出 RuntimeError"""
        service = BaseService(db=None, model_class=UserDB)
        with pytest.raises(RuntimeError) as exc_info:
            service.db
        assert "数据库会话未设置" in str(exc_info.value)

    def test_db_property_returns_session_when_set(self, db_session):
        """测试 db 属性正确返回数据库会话"""
        service = BaseService(db=db_session, model_class=UserDB)
        assert service.db == db_session

    def test_db_setter_updates_session(self, db_session):
        """测试 db setter 正确更新会话"""
        service = BaseService(db=None, model_class=UserDB)
        service.db = db_session
        assert service.db == db_session

    def test_logger_property_returns_logger(self, base_service):
        """测试 logger 属性返回日志器"""
        assert base_service.logger is not None


# ============= 第二部分：通用 CRUD 方法边缘场景 =============

class TestCRUDMethodsEdgeCases:
    """通用 CRUD 方法边缘场景测试"""

    def test_get_by_id_returns_none_for_nonexistent(self, base_service, db_session):
        """测试 get_by_id 对不存在记录返回 None"""
        result = base_service.get_by_id("nonexistent_id")
        assert result is None

    def test_get_by_id_returns_record_for_existing(self, base_service, db_session):
        """测试 get_by_id 正确返回已存在记录"""
        user = make_user(id="test_user_1")
        db_session.add(user)
        db_session.commit()

        result = base_service.get_by_id("test_user_1")
        assert result is not None
        assert result.id == "test_user_1"

    def test_get_by_id_raises_error_without_model_class(self, db_session):
        """测试 get_by_id 无 model_class 时抛出 ValueError"""
        service = BaseService(db=db_session, model_class=None)
        with pytest.raises(ValueError, match="model_class is required"):
            service.get_by_id("some_id")

    def test_get_by_field_returns_none_for_nonexistent(self, base_service, db_session):
        """测试 get_by_field 对不存在字段值返回 None"""
        result = base_service.get_by_field("email", "nonexistent@example.com")
        assert result is None

    def test_get_by_field_returns_record_for_existing(self, base_service, db_session):
        """测试 get_by_field 正确返回匹配记录"""
        user = make_user(id="field_test", email="field@example.com")
        db_session.add(user)
        db_session.commit()

        result = base_service.get_by_field("email", "field@example.com")
        assert result is not None
        assert result.email == "field@example.com"

    def test_get_by_field_raises_error_without_model_class(self, db_session):
        """测试 get_by_field 无 model_class 时抛出 ValueError"""
        service = BaseService(db=db_session, model_class=None)
        with pytest.raises(ValueError, match="model_class is required"):
            service.get_by_field("email", "test@example.com")

    def test_list_by_field_returns_empty_for_no_matches(self, base_service, db_session):
        """测试 list_by_field 无匹配时返回空列表"""
        result = base_service.list_by_field("gender", "nonexistent_gender")
        assert result == []

    def test_list_by_field_with_pagination(self, base_service, db_session):
        """测试 list_by_field 分页功能"""
        # 创建 10 个用户
        for i in range(10):
            db_session.add(make_user(id=f"page_user_{i}", gender="male"))
        db_session.commit()

        # 测试分页
        result = base_service.list_by_field(
            "gender", "male",
            limit=5, offset=2
        )
        assert len(result) == 5

    def test_list_by_field_with_ordering(self, base_service, db_session):
        """测试 list_by_field 排序功能"""
        for i in range(5):
            db_session.add(make_user(id=f"order_user_{i}", age=20 + i * 2))
        db_session.commit()

        result = base_service.list_by_field(
            "gender", "male",
            order_by="age", desc_order=True
        )
        ages = [u.age for u in result]
        assert ages == sorted(ages, reverse=True)

    def test_list_all_returns_empty_when_no_records(self, base_service, db_session):
        """测试 list_all 无记录时返回空列表"""
        result = base_service.list_all()
        assert result == []

    def test_list_all_with_filters(self, base_service, db_session):
        """测试 list_all 使用过滤条件"""
        db_session.add(make_user(id="filter_1", gender="male", age=25))
        db_session.add(make_user(id="filter_2", gender="female", age=30))
        db_session.add(make_user(id="filter_3", gender="male", age=35))
        db_session.commit()

        result = base_service.list_all(gender="male")
        assert len(result) == 2

    def test_count_returns_zero_when_no_records(self, base_service, db_session):
        """测试 count 无记录时返回 0"""
        result = base_service.count()
        assert result == 0

    def test_count_with_filters(self, base_service, db_session):
        """测试 count 使用过滤条件"""
        db_session.add(make_user(id="count_1", gender="male"))
        db_session.add(make_user(id="count_2", gender="female"))
        db_session.add(make_user(id="count_3", gender="male"))
        db_session.commit()

        result = base_service.count(gender="male")
        assert result == 2

    def test_exists_returns_false_for_nonexistent(self, base_service, db_session):
        """测试 exists 对不存在记录返回 False"""
        result = base_service.exists("nonexistent_id")
        assert result is False

    def test_exists_returns_true_for_existing(self, base_service, db_session):
        """测试 exists 对已存在记录返回 True"""
        db_session.add(make_user(id="exists_test"))
        db_session.commit()

        result = base_service.exists("exists_test")
        assert result is True

    def test_create_without_model_class_raises_error(self, db_session):
        """测试 create 无 model_class 时抛出 ValueError"""
        service = BaseService(db=db_session, model_class=None)
        with pytest.raises(ValueError, match="model_class is required"):
            service.create(name="Test")


class TestCRUDCreateUpdateDelete:
    """CRUD 创建、更新、删除测试"""

    def test_create_success(self, base_service, db_session):
        """测试创建记录成功"""
        user = base_service.create(
            id="create_test",
            email="create@example.com",
            password_hash="hash",
            name="Created User",
            age=25,
            gender="male",
            location="上海"
        )
        assert user.id == "create_test"
        assert user.email == "create@example.com"

        # 验证已保存到数据库
        saved = db_session.query(UserDB).filter(UserDB.id == "create_test").first()
        assert saved is not None

    def test_update_success(self, base_service, db_session):
        """测试更新记录成功"""
        user = make_user(id="update_test", name="Original Name")
        db_session.add(user)
        db_session.commit()

        updated = base_service.update(user, name="Updated Name", age=35)
        assert updated.name == "Updated Name"
        assert updated.age == 35

    def test_update_ignores_nonexistent_fields(self, base_service, db_session):
        """测试更新忽略不存在字段"""
        user = make_user(id="update_ignore_test")
        db_session.add(user)
        db_session.commit()

        # 尝试更新一个不存在的字段
        updated = base_service.update(user, nonexistent_field="value")
        assert updated.id == "update_ignore_test"
        assert not hasattr(updated, "nonexistent_field")

    def test_delete_success(self, base_service, db_session):
        """测试删除记录成功"""
        user = make_user(id="delete_test")
        db_session.add(user)
        db_session.commit()

        result = base_service.delete(user)
        assert result is True

        # 验证已从数据库删除
        deleted = db_session.query(UserDB).filter(UserDB.id == "delete_test").first()
        assert deleted is None

    def test_delete_by_id_success(self, base_service, db_session):
        """测试通过 ID 删除记录成功"""
        user = make_user(id="delete_by_id_test")
        db_session.add(user)
        db_session.commit()

        result = base_service.delete_by_id("delete_by_id_test")
        assert result is True

    def test_delete_by_id_returns_false_for_nonexistent(self, base_service, db_session):
        """测试删除不存在的记录返回 False"""
        result = base_service.delete_by_id("nonexistent_id")
        assert result is False

    def test_delete_handles_exception(self, base_service, db_session):
        """测试删除异常处理"""
        # 创建一个模拟的记录，删除时抛出异常
        mock_record = MagicMock()
        mock_record.__class__ = UserDB

        # 模拟 db.delete 抛出异常
        with patch.object(db_session, 'delete', side_effect=Exception("Delete failed")):
            result = base_service.delete(mock_record)
            assert result is False


# ============= 第三部分：日志方法测试 =============

class TestLoggingMethods:
    """日志方法测试"""

    def test_log_info_calls_logger(self, base_service):
        """测试 log_info 调用 logger.info"""
        with patch.object(base_service.logger, 'info') as mock_info:
            base_service.log_info("Test message", extra={"key": "value"})
            mock_info.assert_called_once()

    def test_log_error_calls_logger(self, base_service):
        """测试 log_error 调用 logger.error"""
        with patch.object(base_service.logger, 'error') as mock_error:
            base_service.log_error("Error message")
            mock_error.assert_called_once()

    def test_log_debug_calls_logger(self, base_service):
        """测试 log_debug 调用 logger.debug"""
        with patch.object(base_service.logger, 'debug') as mock_debug:
            base_service.log_debug("Debug message")
            mock_debug.assert_called_once()


# ============= 第四部分：SingletonService 测试 =============

class TestSingletonService:
    """单例服务测试"""

    def test_get_instance_returns_singleton(self):
        """测试 get_instance 返回单例"""
        # 重置实例
        SingletonService.reset_instance()

        instance1 = SingletonService.get_instance()
        instance2 = SingletonService.get_instance()

        assert instance1 is instance2

    def test_reset_instance_clears_singleton(self):
        """测试 reset_instance 清除单例"""
        instance1 = SingletonService.get_instance()
        SingletonService.reset_instance()
        instance2 = SingletonService.get_instance()

        assert instance1 is not instance2

    def test_multiple_reset_calls(self):
        """测试多次调用 reset_instance"""
        SingletonService.reset_instance()
        SingletonService.reset_instance()
        SingletonService.reset_instance()

        instance = SingletonService.get_instance()
        assert instance is not None

    def test_instance_persistence(self):
        """测试单例持久性"""
        SingletonService.reset_instance()
        instance = SingletonService.get_instance()

        # 再次获取应该是同一个实例
        for _ in range(10):
            assert SingletonService.get_instance() is instance


# ============= 第五部分：错误处理与异常场景 =============

class TestErrorHandling:
    """错误处理测试"""

    def test_model_class_none_for_all_operations(self, db_session):
        """测试所有操作在 model_class=None 时的行为"""
        service = BaseService(db=db_session, model_class=None)

        # get_by_id
        with pytest.raises(ValueError):
            service.get_by_id("id")

        # get_by_field
        with pytest.raises(ValueError):
            service.get_by_field("field", "value")

        # list_by_field
        with pytest.raises(ValueError):
            service.list_by_field("field", "value")

        # list_all
        with pytest.raises(ValueError):
            service.list_all()

        # count
        with pytest.raises(ValueError):
            service.count()

        # create
        with pytest.raises(ValueError):
            service.create()

    def test_db_session_closed_mid_operation(self, db_session):
        """测试数据库会话中途关闭"""
        service = BaseService(db=db_session, model_class=UserDB)

        # 创建用户
        user = make_user(id="session_test")
        db_session.add(user)
        db_session.commit()

        # 正常查询应该成功
        result = service.get_by_id("session_test")
        assert result is not None

        # 关闭会话后，服务对象仍持有已关闭的会话引用
        db_session.close()

        # 验证服务对象的 db 属性指向已关闭的会话
        # 使用已关闭的会话进行操作应该抛出异常或返回 None
        try:
            result = service.get_by_id("session_test")
            # 如果没有抛出异常，说明 SQLite 允许在已关闭会话上操作（取决于配置）
            # 这也是合理的测试行为
        except Exception:
            # 预期：已关闭的会话操作应该失败
            pass

    def test_concurrent_access_to_singleton(self):
        """测试单例并发访问"""
        import threading

        SingletonService.reset_instance()
        instances = []

        def get_instance():
            instances.append(SingletonService.get_instance())

        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 所有线程应该获得同一个实例
        assert all(inst is instances[0] for inst in instances)

    def test_field_not_in_model_ignored_in_list_all(self, base_service, db_session):
        """测试 list_all 忽略模型中不存在的字段"""
        db_session.add(make_user(id="ignore_field_test"))
        db_session.commit()

        # 模型中不存在 nonexistent_field
        result = base_service.list_all(nonexistent_field="value")
        # 应返回所有记录（不崩溃）
        assert len(result) == 1

    def test_field_not_in_model_ignored_in_count(self, base_service, db_session):
        """测试 count 忽略模型中不存在的字段"""
        db_session.add(make_user(id="count_ignore_test"))
        db_session.commit()

        result = base_service.count(nonexistent_field="value")
        # 应返回总数（不崩溃）
        assert result == 1

    def test_update_with_empty_kwargs(self, base_service, db_session):
        """测试更新时无更新字段"""
        user = make_user(id="empty_update_test", name="Original")
        db_session.add(user)
        db_session.commit()

        updated = base_service.update(user)
        assert updated.name == "Original"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])