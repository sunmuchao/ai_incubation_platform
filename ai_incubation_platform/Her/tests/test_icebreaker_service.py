"""
破冰问题服务测试

测试覆盖:
1. 初始化与内置问题库 (5 tests)
2. 获取破冰问题方法 (8 tests)
3. 个性化问题推荐 (6 tests)
4. 问题类别进展 (5 tests)
5. 反馈记录 (6 tests)
6. 问题统计 (5 tests)
7. 边界场景与异常处理 (8 tests)

总计: 37 个测试用例
"""
import pytest
import os
import sys
import json
import uuid
from unittest.mock import MagicMock, patch, PropertyMock
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置环境变量
os.environ['OPENAI_API_KEY'] = 'test-key'
os.environ['OPENAI_BASE_URL'] = 'https://test.api/v1'

from db.database import Base
from db.models import IcebreakerQuestionDB, UserDB
from services.icebreaker_service import IcebreakerService


# ============= 测试基础设施 =============

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)

Base.metadata.create_all(bind=test_engine)


@pytest.fixture
def db_session():
    """数据库会话 fixture - 每个测试独立的数据库"""
    # 每个测试使用独立的内存数据库
    test_db_url = f"sqlite:///:memory:{uuid.uuid4()}"
    engine = create_engine(
        test_db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def service(db_session):
    """创建测试服务"""
    return IcebreakerService(db_session)


def make_question(**kwargs):
    """创建测试破冰问题"""
    defaults = {
        "id": str(uuid.uuid4()),
        "question": "测试问题内容",
        "category": "casual",
        "depth_level": 1,
        "suitable_scenarios": json.dumps(["first_date"]),
        "usage_count": 0,
        "positive_feedback_rate": 0.5,
    }
    defaults.update(kwargs)
    return IcebreakerQuestionDB(**defaults)


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


# ============= 第一部分：初始化与内置问题库测试 =============

class TestInitialization:
    """初始化测试"""

    def test_service_init_with_db(self, db_session):
        """测试服务初始化"""
        service = IcebreakerService(db_session)
        assert service.db == db_session
        assert service._model_class == IcebreakerQuestionDB

    def test_builtin_questions_count(self, service, db_session):
        """测试内置问题库数量"""
        count = db_session.query(IcebreakerQuestionDB).count()
        assert count == len(IcebreakerService.BUILTIN_QUESTIONS)

    def test_builtin_questions_categories(self, service, db_session):
        """测试内置问题分类分布"""
        categories = db_session.query(
            IcebreakerQuestionDB.category,
            func.count(IcebreakerQuestionDB.id)
        ).group_by(IcebreakerQuestionDB.category).all()

        category_counts = {cat: cnt for cat, cnt in categories}
        assert "casual" in category_counts
        assert "deep" in category_counts
        assert "fun" in category_counts
        assert "values" in category_counts

    def test_init_skip_if_data_exists(self, db_session):
        """测试已有数据时跳过初始化"""
        # 清空数据库（确保没有内置问题干扰）
        db_session.query(IcebreakerQuestionDB).delete()
        db_session.commit()

        # 先添加一条数据
        db_session.add(make_question(id="existing_question"))
        db_session.commit()

        # 创建新服务实例
        service = IcebreakerService(db_session)

        # 验证内置问题没有添加（因为已有数据，所以跳过初始化）
        count = db_session.query(IcebreakerQuestionDB).count()
        # 只有手动添加的 1 条，证明跳过了内置问题的初始化
        assert count == 1

    def test_builtin_questions_structure(self):
        """测试内置问题结构完整性"""
        for q in IcebreakerService.BUILTIN_QUESTIONS:
            assert "question" in q
            assert "category" in q
            assert "depth_level" in q
            assert q["category"] in ["casual", "deep", "fun", "values"]
            assert 1 <= q["depth_level"] <= 5


# ============= 第二部分：获取破冰问题方法测试 =============

class TestGetQuestions:
    """获取破冰问题测试"""

    def test_get_questions_basic(self, service):
        """测试基础获取问题"""
        questions = service.get_questions(limit=5)
        assert len(questions) <= 5
        for q in questions:
            assert "id" in q
            assert "question" in q
            assert "category" in q
            assert "depth_level" in q
            assert "usage_count" in q

    def test_get_questions_by_category(self, service, db_session):
        """测试按分类获取问题"""
        # 清空数据库重新初始化
        db_session.query(IcebreakerQuestionDB).delete()
        db_session.commit()

        # 添加测试数据
        db_session.add(make_question(id="q1", category="casual"))
        db_session.add(make_question(id="q2", category="deep"))
        db_session.add(make_question(id="q3", category="fun"))
        db_session.commit()

        # 测试分类过滤
        casual_questions = service.get_questions(category="casual")
        assert all(q["category"] == "casual" for q in casual_questions)

    def test_get_questions_by_depth_level(self, service, db_session):
        """测试按深度级别获取问题"""
        # 清空数据库重新初始化
        db_session.query(IcebreakerQuestionDB).delete()
        db_session.commit()

        # 添加测试数据
        db_session.add(make_question(id="q1", depth_level=1))
        db_session.add(make_question(id="q2", depth_level=3))
        db_session.add(make_question(id="q3", depth_level=5))
        db_session.commit()

        # 测试深度过滤
        level_3_questions = service.get_questions(depth_level=3)
        assert all(q["depth_level"] == 3 for q in level_3_questions)

    def test_get_questions_combined_filters(self, service, db_session):
        """测试组合过滤条件"""
        # 清空数据库重新初始化
        db_session.query(IcebreakerQuestionDB).delete()
        db_session.commit()

        # 添加测试数据
        db_session.add(make_question(id="q1", category="casual", depth_level=1))
        db_session.add(make_question(id="q2", category="casual", depth_level=3))
        db_session.add(make_question(id="q3", category="deep", depth_level=1))
        db_session.commit()

        # 测试组合过滤
        questions = service.get_questions(category="casual", depth_level=1)
        assert len(questions) == 1
        assert questions[0]["category"] == "casual"
        assert questions[0]["depth_level"] == 1

    def test_get_questions_limit(self, service, db_session):
        """测试数量限制"""
        # 清空数据库重新初始化
        db_session.query(IcebreakerQuestionDB).delete()
        db_session.commit()

        # 添加多条数据
        for i in range(20):
            db_session.add(make_question(id=f"q{i}"))
        db_session.commit()

        # 测试数量限制
        questions = service.get_questions(limit=10)
        assert len(questions) == 10

    def test_get_questions_empty_database(self, db_session):
        """测试空数据库返回空列表"""
        # 不初始化内置问题
        db_session.query(IcebreakerQuestionDB).delete()
        db_session.commit()

        # 创建不自动初始化的服务
        with patch.object(IcebreakerService, '_init_builtin_questions'):
            service = IcebreakerService(db_session)

        questions = service.get_questions()
        assert questions == []

    def test_get_questions_random_order(self, service, db_session):
        """测试随机排序"""
        # 清空数据库重新初始化
        db_session.query(IcebreakerQuestionDB).delete()
        db_session.commit()

        # 添加多条数据
        for i in range(10):
            db_session.add(make_question(id=f"q{i}", question=f"问题{i}"))
        db_session.commit()

        # 多次获取，顺序应该可能不同（由于随机）
        questions1 = service.get_questions(limit=10)
        questions2 = service.get_questions(limit=10)

        # 验证返回数量正确
        assert len(questions1) == 10
        assert len(questions2) == 10

    def test_get_questions_return_format(self, service):
        """测试返回格式"""
        questions = service.get_questions(limit=1)
        if questions:
            q = questions[0]
            assert isinstance(q["id"], str)
            assert isinstance(q["question"], str)
            assert isinstance(q["category"], str)
            assert isinstance(q["depth_level"], int)
            assert isinstance(q["usage_count"], int)


# ============= 第三部分：个性化问题推荐测试 =============

class TestPersonalizedQuestions:
    """个性化问题推荐测试"""

    def test_get_personalized_questions_common_interests(self, service, db_session):
        """测试有共同兴趣时返回轻松话题"""
        # 创建两个有共同兴趣的用户
        user1 = make_user(
            id="user1",
            interests=json.dumps(["阅读", "旅行", "音乐"])
        )
        user2 = make_user(
            id="user2",
            interests=json.dumps(["阅读", "摄影", "美食"])
        )
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()

        # Mock get_questions 返回特定类别的问题
        with patch.object(service, 'get_questions') as mock_get:
            mock_get.return_value = [
                {"id": "q1", "question": "轻松问题", "category": "casual", "depth_level": 1}
            ]
            questions = service.get_personalized_questions("user1", "user2")

            # 应该调用 casual 类别
            mock_get.assert_called_with(category="casual", limit=5)

    def test_get_personalized_questions_similar_age(self, service, db_session):
        """测试年龄相仿时返回趣味话题"""
        # 创建两个年龄相仿但没有共同兴趣的用户
        user1 = make_user(
            id="user1",
            age=28,
            interests=json.dumps(["阅读"])
        )
        user2 = make_user(
            id="user2",
            age=26,  # 年龄差 <= 3
            interests=json.dumps(["运动"])
        )
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()

        # Mock get_questions 返回特定类别的问题
        with patch.object(service, 'get_questions') as mock_get:
            mock_get.return_value = [
                {"id": "q1", "question": "趣味问题", "category": "fun", "depth_level": 2}
            ]
            questions = service.get_personalized_questions("user1", "user2")

            # 应该调用 fun 类别
            mock_get.assert_called_with(category="fun", limit=5)

    def test_get_personalized_questions_default(self, service, db_session):
        """测试默认情况返回混合问题"""
        # 创建两个没有共同兴趣且年龄差距较大的用户
        user1 = make_user(
            id="user1",
            age=25,
            interests=json.dumps(["阅读"])
        )
        user2 = make_user(
            id="user2",
            age=40,  # 年龄差 > 3
            interests=json.dumps(["运动"])
        )
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()

        # Mock get_questions 返回混合问题
        with patch.object(service, 'get_questions') as mock_get:
            mock_get.return_value = [
                {"id": "q1", "question": "混合问题", "category": "casual", "depth_level": 1}
            ]
            questions = service.get_personalized_questions("user1", "user2")

            # 应调用无类别的 get_questions
            mock_get.assert_called_with(limit=5)

    def test_get_personalized_questions_user_not_found(self, service, db_session):
        """测试用户不存在时返回默认问题"""
        # Mock get_questions 返回
        with patch.object(service, 'get_questions') as mock_get:
            mock_get.return_value = [
                {"id": "q1", "question": "默认问题", "category": "casual", "depth_level": 1}
            ]
            questions = service.get_personalized_questions("nonexistent1", "nonexistent2")

            # 用户不存在时调用默认 get_questions
            mock_get.assert_called_with(limit=5)
            assert len(questions) == 1

    def test_get_personalized_questions_empty_interests(self, service, db_session):
        """测试用户兴趣为空的情况"""
        # 创建兴趣为空的用户
        user1 = make_user(id="user1", age=28, interests="")
        user2 = make_user(id="user2", age=30, interests="")
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()

        # Mock get_questions
        with patch.object(service, 'get_questions') as mock_get:
            mock_get.return_value = []
            questions = service.get_personalized_questions("user1", "user2")

            # 年龄差 <= 3，应返回 fun 类别
            mock_get.assert_called_with(category="fun", limit=5)

    def test_get_personalized_questions_limit(self, service, db_session):
        """测试自定义数量限制"""
        user1 = make_user(id="user1", interests=json.dumps(["阅读"]))
        user2 = make_user(id="user2", interests=json.dumps(["阅读"]))
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()

        with patch.object(service, 'get_questions') as mock_get:
            mock_get.return_value = []
            questions = service.get_personalized_questions("user1", "user2", limit=10)

            mock_get.assert_called_with(category="casual", limit=10)


# ============= 第四部分：问题类别进展测试 =============

class TestCategoryProgression:
    """问题类别进展测试"""

    def test_progression_early_stage(self, service):
        """测试约会初期返回 casual"""
        category = service.get_category_progression("date_001", games_played=0)
        assert category == "casual"

        category = service.get_category_progression("date_001", games_played=1)
        assert category == "casual"

        category = service.get_category_progression("date_001", games_played=2)
        assert category == "casual"

    def test_progression_fun_stage(self, service):
        """测试约会中期返回 fun"""
        category = service.get_category_progression("date_001", games_played=3)
        assert category == "fun"

        category = service.get_category_progression("date_001", games_played=4)
        assert category == "fun"

    def test_progression_deep_stage(self, service):
        """测试约会深入阶段返回 deep"""
        category = service.get_category_progression("date_001", games_played=5)
        assert category == "deep"

        category = service.get_category_progression("date_001", games_played=6)
        assert category == "deep"

    def test_progression_values_stage(self, service):
        """测试约会后期返回 values"""
        category = service.get_category_progression("date_001", games_played=7)
        assert category == "values"

        category = service.get_category_progression("date_001", games_played=10)
        assert category == "values"

    def test_progression_thresholds(self, service):
        """测试边界值"""
        # 测试各阶段边界
        assert service.get_category_progression("d1", 0) == "casual"
        assert service.get_category_progression("d1", 2) == "casual"
        assert service.get_category_progression("d1", 3) == "fun"
        assert service.get_category_progression("d1", 4) == "fun"
        assert service.get_category_progression("d1", 5) == "deep"
        assert service.get_category_progression("d1", 6) == "deep"
        assert service.get_category_progression("d1", 7) == "values"


# ============= 第五部分：反馈记录测试 =============

class TestRecordFeedback:
    """反馈记录测试"""

    def test_record_positive_feedback(self, service, db_session):
        """测试记录正面反馈"""
        # 添加测试问题
        question = make_question(
            id="feedback_q1",
            usage_count=5,
            positive_feedback_rate=0.8
        )
        db_session.add(question)
        db_session.commit()

        result = service.record_feedback("feedback_q1", is_positive=True)

        assert result is True

        # 验证更新后的数据
        updated = db_session.query(IcebreakerQuestionDB).filter(
            IcebreakerQuestionDB.id == "feedback_q1"
        ).first()
        assert updated.usage_count == 6
        # 好评率应该更新（移动平均）
        assert updated.positive_feedback_rate > 0.8

    def test_record_negative_feedback(self, service, db_session):
        """测试记录负面反馈"""
        # 添加测试问题
        question = make_question(
            id="feedback_q2",
            usage_count=5,
            positive_feedback_rate=0.8
        )
        db_session.add(question)
        db_session.commit()

        result = service.record_feedback("feedback_q2", is_positive=False)

        assert result is True

        # 验证更新后的数据
        updated = db_session.query(IcebreakerQuestionDB).filter(
            IcebreakerQuestionDB.id == "feedback_q2"
        ).first()
        assert updated.usage_count == 6
        # 好评率应该下降
        assert updated.positive_feedback_rate < 0.8

    def test_record_feedback_question_not_found(self, service):
        """测试问题不存在时返回 False"""
        result = service.record_feedback("nonexistent_id", is_positive=True)
        assert result is False

    def test_record_feedback_first_usage(self, service, db_session):
        """测试首次使用时的反馈"""
        # 添加使用次数为 0 的问题
        question = make_question(
            id="feedback_q3",
            usage_count=0,
            positive_feedback_rate=0.5
        )
        db_session.add(question)
        db_session.commit()

        result = service.record_feedback("feedback_q3", is_positive=True)

        assert result is True
        updated = db_session.query(IcebreakerQuestionDB).filter(
            IcebreakerQuestionDB.id == "feedback_q3"
        ).first()
        assert updated.usage_count == 1
        # 首次好评应更新好评率
        assert updated.positive_feedback_rate == 1.0

    def test_record_feedback_rate_calculation(self, service, db_session):
        """测试好评率计算"""
        # 添加测试问题
        question = make_question(
            id="feedback_q4",
            usage_count=10,
            positive_feedback_rate=0.5
        )
        db_session.add(question)
        db_session.commit()

        # 记录正面反馈
        service.record_feedback("feedback_q4", is_positive=True)

        updated = db_session.query(IcebreakerQuestionDB).filter(
            IcebreakerQuestionDB.id == "feedback_q4"
        ).first()

        # 移动平均计算: (0.5 * 10 + 1) / 11 ≈ 0.545
        expected_rate = (0.5 * 10 + 1) / 11
        assert abs(updated.positive_feedback_rate - expected_rate) < 0.01

    def test_record_feedback_negative_rate_calculation(self, service, db_session):
        """测试负面反馈好评率计算"""
        # 添加测试问题
        question = make_question(
            id="feedback_q5",
            usage_count=10,
            positive_feedback_rate=0.5
        )
        db_session.add(question)
        db_session.commit()

        # 记录负面反馈
        service.record_feedback("feedback_q5", is_positive=False)

        updated = db_session.query(IcebreakerQuestionDB).filter(
            IcebreakerQuestionDB.id == "feedback_q5"
        ).first()

        # 移动平均计算: (0.5 * 10 + 0) / 11 ≈ 0.455
        expected_rate = (0.5 * 10) / 11
        assert abs(updated.positive_feedback_rate - expected_rate) < 0.01


# ============= 第六部分：问题统计测试 =============

class TestQuestionStats:
    """问题统计测试"""

    def test_get_question_stats_basic(self, service):
        """测试基础统计"""
        stats = service.get_question_stats()

        assert "total_questions" in stats
        assert "by_category" in stats
        assert "most_used" in stats
        assert stats["total_questions"] > 0

    def test_get_question_stats_by_category(self, service):
        """测试分类统计"""
        stats = service.get_question_stats()

        by_category = stats["by_category"]
        assert isinstance(by_category, dict)
        # 应包含所有分类
        assert "casual" in by_category
        assert "deep" in by_category
        assert "fun" in by_category
        assert "values" in by_category

    def test_get_question_stats_most_used(self, service, db_session):
        """测试最常用问题统计"""
        # 清空数据库
        db_session.query(IcebreakerQuestionDB).delete()
        db_session.commit()

        # 添加有使用次数的问题
        db_session.add(make_question(id="q1", usage_count=100))
        db_session.add(make_question(id="q2", usage_count=50))
        db_session.add(make_question(id="q3", usage_count=10))
        db_session.commit()

        stats = service.get_question_stats()

        most_used = stats["most_used"]
        assert len(most_used) <= 5
        # 应按使用次数降序排列
        if len(most_used) >= 2:
            assert most_used[0]["usage_count"] >= most_used[1]["usage_count"]

    def test_get_question_stats_empty_database(self, db_session):
        """测试空数据库统计"""
        # 不初始化内置问题
        db_session.query(IcebreakerQuestionDB).delete()
        db_session.commit()

        # 创建不自动初始化的服务
        with patch.object(IcebreakerService, '_init_builtin_questions'):
            service = IcebreakerService(db_session)

        stats = service.get_question_stats()

        assert stats["total_questions"] == 0
        assert stats["by_category"] == {}
        assert stats["most_used"] == []

    def test_get_question_stats_most_used_limit(self, service, db_session):
        """测试最常用问题数量限制"""
        # 清空数据库
        db_session.query(IcebreakerQuestionDB).delete()
        db_session.commit()

        # 添加超过 5 条有使用次数的问题
        for i in range(10):
            db_session.add(make_question(id=f"q{i}", usage_count=i * 10))
        db_session.commit()

        stats = service.get_question_stats()

        # 最多返回 5 条
        assert len(stats["most_used"]) <= 5


# ============= 第七部分：边界场景与异常处理测试 =============

class TestEdgeCases:
    """边界场景测试"""

    def test_service_with_none_db(self):
        """测试 db 为 None 时抛出 RuntimeError"""
        # IcebreakerService 在 __init__ 中会调用 _init_builtin_questions
        # 这会访问 db，所以需要 mock 绕过初始化来测试 db 属性的 RuntimeError
        with patch.object(IcebreakerService, '_init_builtin_questions'):
            service = IcebreakerService(db=None)
            # 现在测试 db 属性访问
            with pytest.raises(RuntimeError) as exc_info:
                service.db
            assert "数据库会话未设置" in str(exc_info.value)

    def test_db_setter(self, db_session):
        """测试 db setter"""
        # 需要 mock 绕过初始化来创建 db=None 的实例
        with patch.object(IcebreakerService, '_init_builtin_questions'):
            service = IcebreakerService(db=None)
            service.db = db_session
            assert service.db == db_session

    def test_get_questions_negative_limit(self, service):
        """测试负数 limit"""
        # SQLite 的 limit 为负数时可能返回所有记录
        # 这里测试不会崩溃
        questions = service.get_questions(limit=-1)
        assert isinstance(questions, list)

    def test_get_questions_zero_limit(self, service):
        """测试 zero limit"""
        questions = service.get_questions(limit=0)
        assert len(questions) == 0

    def test_get_questions_large_limit(self, service, db_session):
        """测试超大 limit"""
        # 添加一些数据
        for i in range(5):
            db_session.add(make_question(id=f"large_{i}"))
        db_session.commit()

        questions = service.get_questions(limit=10000)
        # 应返回所有可用数据（不超过实际数量）
        assert len(questions) <= db_session.query(IcebreakerQuestionDB).count()

    def test_record_feedback_multiple_times(self, service, db_session):
        """测试多次记录反馈"""
        question = make_question(id="multi_feedback", usage_count=0)
        db_session.add(question)
        db_session.commit()

        # 多次记录反馈
        for i in range(10):
            service.record_feedback("multi_feedback", is_positive=(i % 2 == 0))

        updated = db_session.query(IcebreakerQuestionDB).filter(
            IcebreakerQuestionDB.id == "multi_feedback"
        ).first()

        assert updated.usage_count == 10
        # 好评率应介于 0 和 1 之间
        assert 0 <= updated.positive_feedback_rate <= 1

    def test_get_personalized_questions_one_user_exists(self, service, db_session):
        """测试只有一个用户存在时返回默认问题"""
        user1 = make_user(id="user1", interests=json.dumps(["阅读"]))
        db_session.add(user1)
        db_session.commit()

        with patch.object(service, 'get_questions') as mock_get:
            mock_get.return_value = []
            questions = service.get_personalized_questions("user1", "nonexistent")

            # 应调用默认 get_questions
            mock_get.assert_called_with(limit=5)

    def test_logger_property(self, service):
        """测试 logger 属性"""
        assert service.logger is not None


class TestConcurrencyAndPerformance:
    """并发和性能相关测试"""

    def test_multiple_service_instances(self, db_session):
        """测试多个服务实例共享数据"""
        # 第一个服务初始化数据
        service1 = IcebreakerService(db_session)
        count1 = db_session.query(IcebreakerQuestionDB).count()

        # 第二个服务应跳过初始化
        service2 = IcebreakerService(db_session)
        count2 = db_session.query(IcebreakerQuestionDB).count()

        assert count1 == count2
        assert count1 == len(IcebreakerService.BUILTIN_QUESTIONS)

    def test_builtin_questions_id_generation(self, db_session):
        """测试内置问题 ID 生成"""
        service = IcebreakerService(db_session)

        questions = db_session.query(IcebreakerQuestionDB).all()
        ids = [q.id for q in questions]

        # ID 应唯一
        assert len(ids) == len(set(ids))

        # ID 应为字符串
        for id in ids:
            assert isinstance(id, str)

    def test_question_category_valid(self, service, db_session):
        """测试所有问题分类有效"""
        questions = db_session.query(IcebreakerQuestionDB).all()

        valid_categories = ["casual", "deep", "fun", "values"]
        for q in questions:
            assert q.category in valid_categories

    def test_question_depth_level_valid(self, service, db_session):
        """测试所有问题深度级别有效"""
        questions = db_session.query(IcebreakerQuestionDB).all()

        for q in questions:
            assert 1 <= q.depth_level <= 5


class TestIntegration:
    """集成测试"""

    def test_full_workflow(self, service, db_session):
        """测试完整工作流程"""
        # 1. 创建用户
        user1 = make_user(
            id="workflow_user1",
            age=28,
            interests=json.dumps(["旅行", "音乐"])
        )
        user2 = make_user(
            id="workflow_user2",
            age=30,
            interests=json.dumps(["旅行", "摄影"])
        )
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()

        # 2. 获取问题类别进展
        category = service.get_category_progression("date_001", games_played=3)
        assert category in ["casual", "fun", "deep", "values"]

        # 3. 获取问题
        questions = service.get_questions(category=category, limit=5)
        assert len(questions) > 0

        # 4. 记录反馈
        if questions:
            question_id = questions[0]["id"]
            result = service.record_feedback(question_id, is_positive=True)
            assert result is True

        # 5. 获取统计
        stats = service.get_question_stats()
        assert stats["total_questions"] > 0

    def test_personalized_workflow(self, service, db_session):
        """测试个性化推荐工作流程"""
        # 创建有共同兴趣的用户
        user1 = make_user(
            id="personal_user1",
            age=28,
            interests=json.dumps(["阅读", "旅行"])
        )
        user2 = make_user(
            id="personal_user2",
            age=30,
            interests=json.dumps(["阅读", "美食"])
        )
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()

        # 获取个性化问题
        questions = service.get_personalized_questions(
            "personal_user1",
            "personal_user2",
            limit=3
        )

        # 应返回问题列表
        assert isinstance(questions, list)
        assert len(questions) <= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--cov=services.icebreaker_service", "--cov-report=term-missing"])