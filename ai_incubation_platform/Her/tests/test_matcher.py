"""
匹配算法单元测试
测试覆盖 matcher.py 的核心匹配逻辑
"""
import pytest
from unittest.mock import patch, MagicMock
from matching.matcher import MatchmakerAlgorithm


class TestMatchmakerAlgorithm:
    """匹配算法测试类"""

    @pytest.fixture
    def matcher(self):
        """创建匹配算法实例"""
        return MatchmakerAlgorithm()

    @pytest.fixture
    def sample_users(self):
        """示例用户数据"""
        return {
            "user1": {
                "id": "user1",
                "name": "张三",
                "age": 28,
                "gender": "male",
                "location": "北京市",
                "interests": ["旅行", "摄影", "美食"],
                "values": {"family": 0.8, "career": 0.6},
                "preferred_age_min": 22,
                "preferred_age_max": 32,
                "preferred_gender": "female",
                "preferred_locations": ["北京市", "上海市"],
                "sexual_orientation": "heterosexual",
            },
            "user2": {
                "id": "user2",
                "name": "李四",
                "age": 26,
                "gender": "female",
                "location": "北京市",
                "interests": ["旅行", "阅读", "美食"],
                "values": {"family": 0.9, "career": 0.5},
                "preferred_age_min": 25,
                "preferred_age_max": 35,
                "preferred_gender": "male",
                "preferred_locations": ["北京市"],
                "sexual_orientation": "heterosexual",
            },
            "user3": {
                "id": "user3",
                "name": "王五",
                "age": 30,
                "gender": "male",
                "location": "上海市",
                "interests": ["健身", "音乐", "电影"],
                "values": {"family": 0.5, "career": 0.9},
                "preferred_age_min": 22,
                "preferred_age_max": 30,
                "preferred_gender": "female",
                "preferred_locations": ["上海市"],
                "sexual_orientation": "heterosexual",
            },
            "user4": {
                "id": "user4",
                "name": "赵六",
                "age": 25,
                "gender": "female",
                "location": "广州市",
                "interests": ["旅行", "摄影", "音乐"],
                "values": {"family": 0.7, "career": 0.7},
                "preferred_age_min": 25,
                "preferred_age_max": 35,
                "preferred_gender": "male",
                "preferred_locations": ["广州市", "深圳市"],
                "sexual_orientation": "heterosexual",
            },
            "user5": {
                "id": "user5",
                "name": "钱七",
                "age": 29,
                "gender": "male",
                "location": "北京市",
                "interests": ["旅行", "摄影", "美食", "阅读"],
                "values": {"family": 0.85, "career": 0.55},
                "preferred_age_min": 20,
                "preferred_age_max": 30,
                "preferred_gender": "female",
                "preferred_locations": ["北京市"],
                "sexual_orientation": "bisexual",
            },
        }

    def test_register_user(self, matcher, sample_users):
        """测试注册用户"""
        user = sample_users["user1"]
        matcher.register_user(user)
        assert "user1" in matcher._users
        assert matcher._users["user1"]["name"] == "张三"
        assert "旅行" in matcher._interest_popularity

    def test_unregister_user(self, matcher, sample_users):
        """测试注销用户"""
        user = sample_users["user1"]
        matcher.register_user(user)
        matcher.unregister_user("user1")
        assert "user1" not in matcher._users

    def test_unregister_nonexistent_user(self, matcher):
        """测试注销不存在的用户"""
        matcher.unregister_user("nonexistent")  # 不应该抛出异常

    def test_find_matches_basic(self, matcher, sample_users):
        """测试基础匹配功能"""
        for user in sample_users.values():
            matcher.register_user(user)

        matches = matcher.find_matches("user1", limit=5)

        assert len(matches) > 0
        assert all("user_id" in m for m in matches)
        assert all("score" in m for m in matches)
        assert all("breakdown" in m for m in matches)
        assert all(m["user_id"] != "user1" for m in matches)

    def test_find_matches_respects_age_preference(self, matcher, sample_users):
        """测试匹配尊重年龄偏好"""
        restrictive_user = {
            "id": "restrictive",
            "name": "挑剔用户",
            "age": 30,
            "gender": "male",
            "location": "北京市",
            "interests": ["旅行"],
            "preferred_age_min": 35,
            "preferred_age_max": 40,
            "preferred_gender": "female",
            "sexual_orientation": "heterosexual",
        }
        matcher.register_user(restrictive_user)
        matcher.register_user(sample_users["user2"])  # 26 岁，不在偏好范围内

        matches = matcher.find_matches("restrictive", limit=5)
        assert not any(m["user_id"] == "user2" for m in matches)

    def test_find_matches_gender_preference(self, matcher, sample_users):
        """测试性别偏好匹配"""
        for user in sample_users.values():
            matcher.register_user(user)

        matches = matcher.find_matches("user1", limit=10)
        matched_ids = [m["user_id"] for m in matches]
        # user3 是男性，不应该匹配
        assert "user3" not in matched_ids

    def test_cold_start_user_detection(self, matcher):
        """测试冷启动用户检测"""
        cold_start_user = {
            "id": "cold_start",
            "name": "冷启动用户",
            "age": 25,
            "gender": "female",
            "location": "北京市",
            "interests": [],
            "preferred_age_min": 20,
            "preferred_age_max": 30,
            "sexual_orientation": "heterosexual",
        }
        is_cold_start = matcher._is_cold_start_user(cold_start_user)
        assert is_cold_start is True

    def test_non_cold_start_user_detection(self, matcher, sample_users):
        """测试非冷启动用户检测"""
        matcher.register_user(sample_users["user1"])
        is_cold_start = matcher._is_cold_start_user(sample_users["user1"])
        assert is_cold_start is False

    def test_calculate_compatibility_interest_overlap(self, matcher, sample_users):
        """测试兴趣重叠度计算"""
        matcher.register_user(sample_users["user1"])
        matcher.register_user(sample_users["user2"])

        score, breakdown = matcher._calculate_compatibility(
            sample_users["user1"], sample_users["user2"]
        )

        assert isinstance(score, float)
        assert 0 <= score <= 1
        assert "interests" in breakdown
        assert breakdown["interests"] > 0

    def test_calculate_compatibility_values_alignment(self, matcher, sample_users):
        """测试价值观对齐度计算"""
        matcher.register_user(sample_users["user1"])
        matcher.register_user(sample_users["user2"])

        score, breakdown = matcher._calculate_compatibility(
            sample_users["user1"], sample_users["user2"]
        )

        assert "values" in breakdown

    def test_location_score_same_location(self, matcher):
        """测试相同位置的 location 分数"""
        user1 = {"location": "北京市朝阳区"}
        user2 = {"location": "北京市朝阳区"}

        _, breakdown = matcher._calculate_compatibility(user1, user2)
        assert breakdown["location"] == 1.0

    def test_location_score_different_city(self, matcher):
        """测试不同城市的 location 分数"""
        user1 = {"location": "北京市朝阳区"}
        user2 = {"location": "上海市浦东新区"}

        _, breakdown = matcher._calculate_compatibility(user1, user2)
        assert breakdown["location"] < 1.0

    def test_check_basic_compatibility_mutual_attraction(self, matcher, sample_users):
        """测试双向吸引力检查"""
        user1 = sample_users["user1"]  # male, prefers female
        user2 = sample_users["user2"]  # female, prefers male

        is_compatible = matcher._check_basic_compatibility(user1, user2)
        assert is_compatible is True

    def test_check_basic_compatibility_single_attraction(self, matcher, sample_users):
        """测试单向吸引力（不兼容）"""
        user1 = sample_users["user1"]  # male, prefers female
        user3 = sample_users["user3"]  # male, prefers female

        is_compatible = matcher._check_basic_compatibility(user1, user3)
        assert is_compatible is False

    def test_bisexual_matching(self, matcher, sample_users):
        """测试双性恋用户的匹配"""
        bisexual_user = {
            "id": "bisexual",
            "name": "双性恋用户",
            "age": 28,
            "gender": "female",
            "location": "北京市",
            "interests": ["旅行", "音乐"],
            "preferred_age_min": 25,
            "preferred_age_max": 35,
            "preferred_gender": None,
            "sexual_orientation": "bisexual",
        }
        matcher.register_user(bisexual_user)
        matcher.register_user(sample_users["user1"])  # male
        matcher.register_user(sample_users["user2"])  # female

        matches = matcher.find_matches("bisexual", limit=10)
        matched_ids = [m["user_id"] for m in matches]
        assert "user1" in matched_ids or "user2" in matched_ids

    def test_homosexual_matching(self, matcher):
        """测试同性恋用户的匹配"""
        gay_user = {
            "id": "gay",
            "name": "同性恋用户",
            "age": 28,
            "gender": "male",
            "location": "北京市",
            "interests": ["旅行", "音乐"],
            "preferred_age_min": 25,
            "preferred_age_max": 35,
            "preferred_gender": "male",
            "sexual_orientation": "homosexual",
        }
        another_gay_user = {
            "id": "gay2",
            "name": "另一个同性恋用户",
            "age": 30,
            "gender": "male",
            "location": "北京市",
            "interests": ["旅行", "电影"],
            "preferred_age_min": 25,
            "preferred_age_max": 35,
            "preferred_gender": "male",
            "sexual_orientation": "homosexual",
        }
        female_user = {
            "id": "female",
            "name": "女性用户",
            "age": 26,
            "gender": "female",
            "location": "北京市",
            "interests": ["旅行"],
            "preferred_age_min": 25,
            "preferred_age_max": 35,
            "preferred_gender": "male",
            "sexual_orientation": "heterosexual",
        }

        matcher.register_user(gay_user)
        matcher.register_user(another_gay_user)
        matcher.register_user(female_user)

        matches = matcher.find_matches("gay", limit=10)
        matched_ids = [m["user_id"] for m in matches]
        assert "gay2" in matched_ids
        assert "female" not in matched_ids

    def test_find_matches_limit(self, matcher, sample_users):
        """测试匹配数量限制"""
        for user in sample_users.values():
            matcher.register_user(user)

        matches_limited = matcher.find_matches("user1", limit=2)
        assert len(matches_limited) <= 2

    def test_find_matches_nonexistent_user(self, matcher, sample_users):
        """测试不存在用户的匹配"""
        for user in sample_users.values():
            matcher.register_user(user)

        matches = matcher.find_matches("nonexistent", limit=5)
        assert len(matches) == 0

    def test_find_matches_empty_database(self, matcher):
        """测试空数据库的匹配"""
        matches = matcher.find_matches("any_user", limit=5)
        assert len(matches) == 0

    def test_cold_start_compatibility_calculation(self, matcher, sample_users):
        """测试冷启动兼容性计算"""
        cold_user = {
            "id": "cold",
            "name": "冷启动",
            "age": 25,
            "gender": "female",
            "location": "北京市",
            "interests": [],
        }
        matcher.register_user(cold_user)
        matcher.register_user(sample_users["user1"])

        score, breakdown = matcher._calculate_cold_start_compatibility(cold_user, sample_users["user1"])
        assert isinstance(score, float)
        assert "interests" in breakdown

    def test_interest_popularity_tracking(self, matcher, sample_users):
        """测试兴趣流行度追踪"""
        matcher.register_user(sample_users["user1"])
        matcher.register_user(sample_users["user2"])

        popularity = matcher._interest_popularity.get("旅行", 0)
        assert popularity >= 2

    def test_match_score_ranking(self, matcher, sample_users):
        """测试匹配分数排序"""
        for user in sample_users.values():
            matcher.register_user(user)

        matches = matcher.find_matches("user1", limit=10)
        for i in range(len(matches) - 1):
            assert matches[i]["score"] >= matches[i + 1]["score"]

    def test_update_global_stats_after_registration(self, matcher, sample_users):
        """测试注册后全局统计更新"""
        initial_interests = matcher._interest_popularity.copy()
        matcher.register_user(sample_users["user1"])
        assert matcher._interest_popularity != initial_interests

    def test_generate_match_reasoning(self, matcher, sample_users):
        """测试生成匹配理由"""
        matcher.register_user(sample_users["user1"])
        matcher.register_user(sample_users["user2"])

        score, breakdown = matcher._calculate_compatibility(
            sample_users["user1"], sample_users["user2"]
        )

        # Mock LLM service to avoid real API calls
        with patch('services.llm_semantic_service.get_llm_semantic_service') as mock_llm:
            mock_service = MagicMock()
            mock_service.enabled = False  # Disable LLM, use fallback
            mock_llm.return_value = mock_service

            reasoning = matcher.generate_match_reasoning(
                sample_users["user1"], sample_users["user2"], score, breakdown
            )

        assert isinstance(reasoning, str)
        assert len(reasoning) > 0

    def test_user_with_no_interests(self, matcher):
        """测试没有兴趣的用户匹配"""
        no_interest_user = {
            "id": "no_interest",
            "name": "无兴趣用户",
            "age": 28,
            "gender": "male",
            "location": "北京市",
            "interests": [],
            "preferred_age_min": 20,
            "preferred_age_max": 35,
            "sexual_orientation": "heterosexual",
        }
        normal_user = {
            "id": "normal",
            "name": "普通用户",
            "age": 26,
            "gender": "female",
            "location": "北京市",
            "interests": ["旅行", "美食"],
            "preferred_age_min": 25,
            "preferred_age_max": 35,
            "sexual_orientation": "heterosexual",
        }

        matcher.register_user(no_interest_user)
        matcher.register_user(normal_user)

        matches = matcher.find_matches("no_interest", limit=5)
        assert len(matches) > 0

    def test_user_with_all_same_interests(self, matcher):
        """测试兴趣完全相同的用户匹配"""
        user1 = {
            "id": "twin1",
            "name": "双胞胎 1",
            "age": 28,
            "gender": "male",
            "location": "北京市",
            "interests": ["旅行", "摄影", "美食", "阅读", "音乐"],
            "values": {"family": 0.8, "career": 0.6},
            "preferred_age_min": 25,
            "preferred_age_max": 32,
            "sexual_orientation": "heterosexual",
        }
        user2 = {
            "id": "twin2",
            "name": "双胞胎 2",
            "age": 27,
            "gender": "female",
            "location": "北京市",
            "interests": ["旅行", "摄影", "美食", "阅读", "音乐"],
            "values": {"family": 0.85, "career": 0.55},
            "preferred_age_min": 25,
            "preferred_age_max": 32,
            "sexual_orientation": "heterosexual",
        }

        matcher.register_user(user1)
        matcher.register_user(user2)

        matches = matcher.find_matches("twin1", limit=5)
        assert len(matches) > 0
        assert matches[0]["user_id"] == "twin2"

    def test_extreme_age_preferences(self, matcher):
        """测试极端年龄偏好"""
        extreme_user = {
            "id": "extreme",
            "name": "极端用户",
            "age": 50,
            "gender": "male",
            "location": "北京市",
            "interests": ["旅行"],
            "preferred_age_min": 18,
            "preferred_age_max": 80,
            "sexual_orientation": "heterosexual",
        }
        young_user = {
            "id": "young",
            "name": "年轻用户",
            "age": 20,
            "gender": "female",
            "location": "北京市",
            "interests": ["旅行"],
            "preferred_age_min": 40,
            "preferred_age_max": 60,
            "sexual_orientation": "heterosexual",
        }

        matcher.register_user(extreme_user)
        matcher.register_user(young_user)

        matches = matcher.find_matches("extreme", limit=5)
        matched_ids = [m["user_id"] for m in matches]
        assert "young" in matched_ids

    @pytest.mark.skip(reason="get_mutual_matches 方法尚未实现")
    def test_get_mutual_matches(self, matcher):
        """测试获取双向匹配"""
        user1 = {
            "id": "user1",
            "name": "用户 1",
            "age": 28,
            "gender": "male",
            "location": "北京市",
            "interests": ["旅行"],
            "preferred_age_min": 20,
            "preferred_age_max": 35,
            "sexual_orientation": "heterosexual",
        }
        user2 = {
            "id": "user2",
            "name": "用户 2",
            "age": 26,
            "gender": "female",
            "location": "北京市",
            "interests": ["旅行"],
            "preferred_age_min": 25,
            "preferred_age_max": 35,
            "sexual_orientation": "heterosexual",
        }

        matcher.register_user(user1)
        matcher.register_user(user2)

        mutual_matches = matcher.get_mutual_matches("user1")
        assert isinstance(mutual_matches, list)
