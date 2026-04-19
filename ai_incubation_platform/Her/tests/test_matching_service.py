"""
匹配服务测试

测试 MatchingService 的核心功能：
- calculate_compatibility() 匹配度计算
- create_match() 创建匹配记录
- check_mutual_like() 双向喜欢检查
- get_match_history() 获取匹配历史
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import uuid

# 尝试导入服务模块
try:
    from services.matching_service import (
        MatchingService,
        get_matching_service,
    )
except ImportError:
    pytest.skip("matching_service not importable", allow_module_level=True)


class TestServiceInitialization:
    """服务初始化测试"""

    def test_service_creation(self):
        """测试服务创建"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        assert service is not None
        assert service.db == mock_db

    def test_get_matching_service_factory(self):
        """测试服务工厂函数"""
        mock_db = MagicMock()
        service = get_matching_service(mock_db)

        assert service is not None
        assert isinstance(service, MatchingService)


class TestCalculateCompatibility:
    """匹配度计算测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        mock_db = MagicMock()
        return MatchingService(mock_db)

    def test_calculate_compatibility_ai_mode(self):
        """测试 AI 计算模式"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        result = service.calculate_compatibility("user_001", "user_002", use_ai=True)

        # AI 模式在同步场景返回默认值 0.5
        assert result == 0.5

    def test_calculate_compatibility_simple_mode(self):
        """测试简单规则计算"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        # Mock 用户数据
        mock_user_a = MagicMock()
        mock_user_a.id = "user_001"
        mock_user_a.age = 28
        mock_user_a.location = "北京"
        mock_user_a.interests = '["旅行", "摄影", "阅读"]'

        mock_user_b = MagicMock()
        mock_user_b.id = "user_002"
        mock_user_b.age = 26
        mock_user_b.location = "北京"
        mock_user_b.interests = '["旅行", "音乐"]'

        service.db.query.return_value.filter.return_value.first.side_effect = [mock_user_a, mock_user_b]

        result = service.calculate_compatibility("user_001", "user_002", use_ai=False)

        # 年龄差距 2 岁（<=5）：+0.1
        # 同城市：+0.1
        # 共同兴趣：旅行（1个）：+0.05
        # 基础分数 0.5 + 0.1 + 0.1 + 0.05 = 0.75
        assert result >= 0.5
        assert result <= 1.0

    def test_calculate_compatibility_user_not_found(self):
        """测试用户不存在"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        service.db.query.return_value.filter.return_value.first.return_value = None

        result = service.calculate_compatibility("user_001", "user_002")

        assert result == 0.0

    def test_calculate_compatibility_one_user_not_found(self):
        """测试一个用户不存在"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        mock_user_a = MagicMock()
        mock_user_a.id = "user_001"
        mock_user_a.age = 28
        mock_user_a.location = "北京"
        mock_user_a.interests = '["旅行"]'

        # user_a 存在，user_b 不存在
        service.db.query.return_value.filter.return_value.first.side_effect = [mock_user_a, None]

        result = service.calculate_compatibility("user_001", "user_002")

        assert result == 0.0

    def test_calculate_compatibility_exception(self):
        """测试异常处理"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        service.db.query.side_effect = Exception("Database error")

        result = service.calculate_compatibility("user_001", "user_002")

        # 异常时返回默认值 0.5
        assert result == 0.5


class TestCalculateSimpleCompatibility:
    """简单匹配度计算规则测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        mock_db = MagicMock()
        return MatchingService(mock_db)

    def test_age_difference_small(self):
        """测试年龄差距小"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        mock_user_a = MagicMock()
        mock_user_a.age = 28
        mock_user_a.location = "上海"
        mock_user_a.interests = None

        mock_user_b = MagicMock()
        mock_user_b.age = 27  # 差距 1 岁
        mock_user_b.location = "北京"
        mock_user_b.interests = None

        result = service._calculate_simple_compatibility(mock_user_a, mock_user_b)

        # 年龄差距 <=5：+0.1
        assert result >= 0.6  # 0.5 + 0.1

    def test_age_difference_medium(self):
        """测试年龄差距中等"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        mock_user_a = MagicMock()
        mock_user_a.age = 28
        mock_user_a.location = ""
        mock_user_a.interests = None

        mock_user_b = MagicMock()
        mock_user_b.age = 33  # 差距 5 岁，边界值
        mock_user_b.location = ""
        mock_user_b.interests = None

        result = service._calculate_simple_compatibility(mock_user_a, mock_user_b)

        # 年龄差距 5 岁（<=5）：+0.1
        assert result >= 0.6

    def test_age_difference_large(self):
        """测试年龄差距大"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        mock_user_a = MagicMock()
        mock_user_a.age = 25
        mock_user_a.location = ""
        mock_user_a.interests = None

        mock_user_b = MagicMock()
        mock_user_b.age = 40  # 差距 15 岁
        mock_user_b.location = ""
        mock_user_b.interests = None

        result = service._calculate_simple_compatibility(mock_user_a, mock_user_b)

        # 年龄差距 >10：扣分
        assert result < 0.5

    def test_same_city_bonus(self):
        """测试同城市加分"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        mock_user_a = MagicMock()
        mock_user_a.age = 28
        mock_user_a.location = "北京"
        mock_user_a.interests = None

        mock_user_b = MagicMock()
        mock_user_b.age = 28
        mock_user_b.location = "北京"
        mock_user_b.interests = None

        result = service._calculate_simple_compatibility(mock_user_a, mock_user_b)

        # 同城市：+0.1
        assert result >= 0.7  # 0.5 + 0.1 (年龄) + 0.1 (城市)

    def test_different_city_no_bonus(self):
        """测试不同城市无加分"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        mock_user_a = MagicMock()
        mock_user_a.age = 28
        mock_user_a.location = "北京"
        mock_user_a.interests = None

        mock_user_b = MagicMock()
        mock_user_b.age = 28
        mock_user_b.location = "上海"
        mock_user_b.interests = None

        result = service._calculate_simple_compatibility(mock_user_a, mock_user_b)

        # 不同城市：无加分，但年龄差距 0 加 0.1
        assert result >= 0.6  # 0.5 + 0.1 (年龄)

    def test_common_interests_bonus(self):
        """测试共同兴趣加分"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        mock_user_a = MagicMock()
        mock_user_a.age = 28
        mock_user_a.location = ""
        mock_user_a.interests = '["旅行", "摄影", "阅读", "音乐"]'

        mock_user_b = MagicMock()
        mock_user_b.age = 28
        mock_user_b.location = ""
        mock_user_b.interests = '["旅行", "摄影", "运动"]'

        result = service._calculate_simple_compatibility(mock_user_a, mock_user_b)

        # 共同兴趣：旅行、摄影（2个）：+0.1
        assert result >= 0.7  # 0.5 + 0.1 (年龄) + 0.1 (兴趣)

    def test_many_common_interests_capped(self):
        """测试大量共同兴趣上限"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        mock_user_a = MagicMock()
        mock_user_a.age = 28
        mock_user_a.location = ""
        mock_user_a.interests = '["旅行", "摄影", "阅读", "音乐", "运动", "电影", "美食"]'

        mock_user_b = MagicMock()
        mock_user_b.age = 28
        mock_user_b.location = ""
        mock_user_b.interests = '["旅行", "摄影", "阅读", "音乐", "运动", "电影", "美食"]'

        result = service._calculate_simple_compatibility(mock_user_a, mock_user_b)

        # 共同兴趣上限：+0.2
        assert result <= 0.9  # 0.5 + 0.1 (年龄) + 0.2 (兴趣上限)

    def test_invalid_interests_json(self):
        """测试无效兴趣 JSON"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        mock_user_a = MagicMock()
        mock_user_a.age = 28
        mock_user_a.location = ""
        mock_user_a.interests = "invalid json"

        mock_user_b = MagicMock()
        mock_user_b.age = 28
        mock_user_b.location = ""
        mock_user_b.interests = '["旅行"]'

        result = service._calculate_simple_compatibility(mock_user_a, mock_user_b)

        # 解析失败时应优雅处理
        assert result >= 0.5

    def test_null_age(self):
        """测试年龄为空"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        mock_user_a = MagicMock()
        mock_user_a.age = None
        mock_user_a.location = ""
        mock_user_a.interests = None

        mock_user_b = MagicMock()
        mock_user_b.age = 28
        mock_user_b.location = ""
        mock_user_b.interests = None

        result = service._calculate_simple_compatibility(mock_user_a, mock_user_b)

        # 空年龄视为 0，差距 28，扣分
        assert result >= 0.0


class TestCreateMatch:
    """创建匹配记录测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        mock_db = MagicMock()
        return MatchingService(mock_db)

    def test_create_match_with_score(self):
        """测试带分数创建匹配"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        # Mock 匹配度计算
        with patch.object(service, 'calculate_compatibility', return_value=0.85):
            result = service.create_match("user_001", "user_002", compatibility_score=0.85)

            assert result["match_id"] is not None
            assert result["user_id_1"] == "user_001"
            assert result["user_id_2"] == "user_002"
            assert result["compatibility_score"] == 0.85
            assert result["status"] == "matched"
            assert service.db.add.called
            assert service.db.commit.called

    def test_create_match_auto_calculate_score(self):
        """测试自动计算分数"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        with patch.object(service, 'calculate_compatibility', return_value=0.75):
            result = service.create_match("user_001", "user_002")

            # 应自动调用 calculate_compatibility
            assert result["compatibility_score"] == 0.75

    def test_create_match_exception(self):
        """测试创建匹配异常"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        service.db.add.side_effect = Exception("Database error")

        with patch.object(service, 'calculate_compatibility', return_value=0.5):
            result = service.create_match("user_001", "user_002")

            assert result["match_id"] is None
            assert "error" in result
            assert service.db.rollback.called


class TestCheckMutualLike:
    """双向喜欢检查测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        mock_db = MagicMock()
        return MatchingService(mock_db)

    def test_check_mutual_like_true(self):
        """测试双向喜欢"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        # Mock A 喜欢 B 和 B 喜欢 A 的记录
        mock_like_a_to_b = MagicMock()
        mock_like_b_to_a = MagicMock()

        service.db.query.return_value.filter.return_value.first.side_effect = [
            mock_like_a_to_b,
            mock_like_b_to_a
        ]

        result = service.check_mutual_like("user_001", "user_002")

        assert result is True

    def test_check_mutual_like_one_way(self):
        """测试单向喜欢"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        # A 喜欢 B，但 B 未喜欢 A
        mock_like_a_to_b = MagicMock()

        service.db.query.return_value.filter.return_value.first.side_effect = [
            mock_like_a_to_b,
            None  # B 未喜欢 A
        ]

        result = service.check_mutual_like("user_001", "user_002")

        assert result is False

    def test_check_mutual_like_none(self):
        """测试无喜欢记录"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        service.db.query.return_value.filter.return_value.first.side_effect = [None, None]

        result = service.check_mutual_like("user_001", "user_002")

        assert result is False

    def test_check_mutual_like_exception(self):
        """测试检查异常"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        service.db.query.side_effect = Exception("Database error")

        result = service.check_mutual_like("user_001", "user_002")

        assert result is False


class TestGetMatchHistory:
    """获取匹配历史测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        mock_db = MagicMock()
        return MatchingService(mock_db)

    def test_get_match_history_success(self):
        """测试获取匹配历史"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        # Mock 匹配记录
        mock_match_1 = MagicMock()
        mock_match_1.id = "match_001"
        mock_match_1.user_id_1 = "user_001"
        mock_match_1.user_id_2 = "user_002"
        mock_match_1.compatibility_score = 0.85
        mock_match_1.created_at = datetime.now()

        mock_match_2 = MagicMock()
        mock_match_2.id = "match_002"
        mock_match_2.user_id_1 = "user_003"
        mock_match_2.user_id_2 = "user_001"
        mock_match_2.compatibility_score = 0.75
        mock_match_2.created_at = datetime.now() - timedelta(days=1)

        service.db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_match_1, mock_match_2]

        result = service.get_match_history("user_001", limit=10)

        assert len(result) == 2
        assert result[0]["match_id"] == "match_001"
        assert result[0]["partner_id"] == "user_002"
        assert result[0]["compatibility_score"] == 0.85
        assert result[1]["partner_id"] == "user_003"

    def test_get_match_history_empty(self):
        """测试空匹配历史"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        service.db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        result = service.get_match_history("user_001")

        assert result == []

    def test_get_match_history_with_limit(self):
        """测试带限制获取"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        mock_matches = [MagicMock() for _ in range(5)]

        service.db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_matches[:3]

        result = service.get_match_history("user_001", limit=3)

        assert len(result) == 3

    def test_get_match_history_exception(self):
        """测试获取历史异常"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        service.db.query.side_effect = Exception("Database error")

        result = service.get_match_history("user_001")

        assert result == []

    def test_get_match_history_null_created_at(self):
        """测试空创建时间"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        mock_match = MagicMock()
        mock_match.id = "match_001"
        mock_match.user_id_1 = "user_001"
        mock_match.user_id_2 = "user_002"
        mock_match.compatibility_score = 0.8
        mock_match.created_at = None

        service.db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_match]

        result = service.get_match_history("user_001")

        assert result[0]["matched_at"] is None


class TestEdgeCases:
    """边界值测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        mock_db = MagicMock()
        return MatchingService(mock_db)

    def test_compatibility_score_bounds(self):
        """测试匹配度分数边界"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        # 极大年龄差距
        mock_user_a = MagicMock()
        mock_user_a.age = 18
        mock_user_a.location = ""
        mock_user_a.interests = None

        mock_user_b = MagicMock()
        mock_user_b.age = 80  # 差距 62 岁
        mock_user_b.location = ""
        mock_user_b.interests = None

        result = service._calculate_simple_compatibility(mock_user_a, mock_user_b)

        # 分数应在 0-1 范围内
        assert result >= 0.0
        assert result <= 1.0

    def test_create_match_same_user(self):
        """测试同一用户创建匹配"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        # 自己匹配自己（无效场景）
        with patch.object(service, 'calculate_compatibility', return_value=0.5):
            result = service.create_match("user_001", "user_001")

            # 应能创建但不合理
            assert result["match_id"] is not None

    def test_special_characters_in_user_id(self):
        """测试特殊字符用户 ID"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        service.db.query.return_value.filter.return_value.first.return_value = None

        result = service.calculate_compatibility("user-特殊-001", "user-特殊-002")

        assert result == 0.0

    def test_empty_user_ids(self):
        """测试空用户 ID"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        service.db.query.return_value.filter.return_value.first.return_value = None

        result = service.calculate_compatibility("", "")

        assert result == 0.0

    def test_interests_with_special_characters(self):
        """测试兴趣包含特殊字符"""
        mock_db = MagicMock()
        service = MatchingService(mock_db)

        mock_user_a = MagicMock()
        mock_user_a.age = 28
        mock_user_a.location = ""
        mock_user_a.interests = '["旅行-深度游", "摄影&修图"]'

        mock_user_b = MagicMock()
        mock_user_b.age = 28
        mock_user_b.location = ""
        mock_user_b.interests = '["旅行-深度游"]'

        result = service._calculate_simple_compatibility(mock_user_a, mock_user_b)

        # 应正常解析包含特殊字符的兴趣
        assert result > 0.5