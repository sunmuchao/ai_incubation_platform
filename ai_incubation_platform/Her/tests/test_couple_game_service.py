"""
双人互动游戏服务测试

测试 CoupleGameService 的核心功能：
- 游戏类型定义
- 问题库结构
- 游戏配置参数
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
import json

# 尝试导入服务模块
try:
    from services.couple_game_service import (
        GAME_TYPES,
        QUESTION_POOLS,
    )
except ImportError:
    pytest.skip("couple_game_service not importable", allow_module_level=True)


class TestGameTypes:
    """游戏类型定义测试"""

    def test_game_types_exist(self):
        """测试游戏类型存在"""
        expected_types = [
            "qna_mutual",
            "values_quiz",
            "preference_match",
            "personality_quiz",
            "trivia_couple",
            "future_planning",
            "memory_lane"
        ]

        for game_type in expected_types:
            assert game_type in GAME_TYPES

    def test_game_types_count(self):
        """测试游戏类型数量"""
        assert len(GAME_TYPES) == 7

    def test_game_type_structure(self):
        """测试游戏类型结构"""
        for game_type, config in GAME_TYPES.items():
            assert "label" in config
            assert "description" in config
            assert "min_rounds" in config
            assert "default_rounds" in config
            assert "question_pool" in config

    def test_qna_mutual_config(self):
        """测试互相问答配置"""
        config = GAME_TYPES["qna_mutual"]

        assert config["label"] == "互相问答"
        assert config["min_rounds"] == 5
        assert config["default_rounds"] == 10
        assert config["question_pool"] == "mutual"

    def test_values_quiz_config(self):
        """测试价值观测试配置"""
        config = GAME_TYPES["values_quiz"]

        assert config["label"] == "价值观测试"
        assert config["min_rounds"] == 5
        assert config["default_rounds"] == 8
        assert config["question_pool"] == "values"

    def test_preference_match_config(self):
        """测试偏好匹配配置"""
        config = GAME_TYPES["preference_match"]

        assert config["label"] == "偏好匹配"
        assert config["min_rounds"] == 5
        assert config["default_rounds"] == 10
        assert config["question_pool"] == "preference"

    def test_personality_quiz_config(self):
        """测试性格测试配置"""
        config = GAME_TYPES["personality_quiz"]

        assert config["label"] == "性格测试"
        assert config["min_rounds"] == 8
        assert config["default_rounds"] == 12
        assert config["question_pool"] == "personality"

    def test_trivia_couple_config(self):
        """测试情侣知识问答配置"""
        config = GAME_TYPES["trivia_couple"]

        assert config["label"] == "情侣知识问答"
        assert config["min_rounds"] == 5
        assert config["default_rounds"] == 10
        assert config["question_pool"] == "trivia"

    def test_future_planning_config(self):
        """测试未来规划游戏配置"""
        config = GAME_TYPES["future_planning"]

        assert config["label"] == "未来规划游戏"
        assert config["min_rounds"] == 5
        assert config["default_rounds"] == 8
        assert config["question_pool"] == "future"

    def test_memory_lane_config(self):
        """测试回忆之旅配置"""
        config = GAME_TYPES["memory_lane"]

        assert config["label"] == "回忆之旅"
        assert config["min_rounds"] == 3
        assert config["default_rounds"] == 5
        assert config["question_pool"] == "memory"


class TestQuestionPools:
    """问题库测试"""

    def test_question_pools_exist(self):
        """测试问题库存在"""
        expected_pools = [
            "mutual",
            "values",
            "preference",
            "personality",
            "trivia",
            "future",
            "memory"
        ]

        for pool in expected_pools:
            assert pool in QUESTION_POOLS

    def test_mutual_question_pool(self):
        """测试互相问答问题库"""
        pool = QUESTION_POOLS["mutual"]

        assert len(pool) >= 10
        assert isinstance(pool, list)
        # 检查问题内容
        assert any("周末" in q for q in pool)
        assert any("三个词" in q for q in pool)

    def test_values_question_pool(self):
        """测试价值观问题库"""
        pool = QUESTION_POOLS["values"]

        assert len(pool) >= 5
        assert isinstance(pool, list)
        # 检查问题内容
        assert any("事业" in q and "爱情" in q for q in pool)

    def test_preference_question_pool(self):
        """测试偏好问题库"""
        pool = QUESTION_POOLS["preference"]

        assert isinstance(pool, list)
        assert len(pool) >= 5

    def test_personality_question_pool(self):
        """测试性格问题库"""
        pool = QUESTION_POOLS["personality"]

        assert isinstance(pool, list)
        assert len(pool) >= 5

    def test_trivia_question_pool(self):
        """测试情侣知识问题库"""
        pool = QUESTION_POOLS["trivia"]

        assert isinstance(pool, list)
        assert len(pool) >= 5

    def test_future_question_pool(self):
        """测试未来规划问题库"""
        pool = QUESTION_POOLS["future"]

        assert isinstance(pool, list)
        assert len(pool) >= 5

    def test_memory_question_pool(self):
        """测试回忆问题库"""
        pool = QUESTION_POOLS["memory"]

        assert isinstance(pool, list)
        assert len(pool) >= 3

    def test_all_questions_are_strings(self):
        """测试所有问题为字符串"""
        for pool_name, pool in QUESTION_POOLS.items():
            for question in pool:
                assert isinstance(question, str)
                assert len(question) > 0


class TestGameTypeValidation:
    """游戏类型验证测试"""

    def test_min_rounds_positive(self):
        """测试最小轮数为正数"""
        for game_type, config in GAME_TYPES.items():
            assert config["min_rounds"] > 0

    def test_default_rounds_greater_than_min(self):
        """测试默认轮数大于最小轮数"""
        for game_type, config in GAME_TYPES.items():
            assert config["default_rounds"] >= config["min_rounds"]

    def test_question_pool_matches_game_type(self):
        """测试问题池匹配游戏类型"""
        for game_type, config in GAME_TYPES.items():
            pool_name = config["question_pool"]
            assert pool_name in QUESTION_POOLS


class TestQuestionPoolMappings:
    """问题池映射测试"""

    def test_all_game_types_have_valid_pools(self):
        """测试所有游戏类型有有效问题池"""
        for game_type, config in GAME_TYPES.items():
            pool_name = config["question_pool"]
            # 问题池应存在
            assert pool_name in QUESTION_POOLS
            # 问题池应有足够问题
            pool = QUESTION_POOLS[pool_name]
            assert len(pool) >= config["min_rounds"]


class TestEdgeCases:
    """边界值测试"""

    def test_min_rounds_range(self):
        """测试最小轮数范围"""
        min_rounds_values = [config["min_rounds"] for config in GAME_TYPES.values()]

        # 最小轮数应在合理范围
        assert min(min_rounds_values) >= 3
        assert max(min_rounds_values) <= 12

    def test_default_rounds_range(self):
        """测试默认轮数范围"""
        default_rounds_values = [config["default_rounds"] for config in GAME_TYPES.values()]

        # 默认轮数应在合理范围
        assert min(default_rounds_values) >= 5
        assert max(default_rounds_values) <= 12

    def test_question_pool_sizes(self):
        """测试问题池大小"""
        for pool_name, pool in QUESTION_POOLS.items():
            # 问题池应有足够问题
            assert len(pool) >= 3

    def test_question_length(self):
        """测试问题长度"""
        for pool_name, pool in QUESTION_POOLS.items():
            for question in pool:
                # 问题应有合理长度（至少 5 字符，最短问题可能是 "我的生日是哪一天？"）
                assert len(question) >= 5
                assert len(question) <= 200