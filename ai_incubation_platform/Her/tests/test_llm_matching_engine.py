"""
LLM 匹配引擎测试

覆盖范围:
- LLMMatchingEngine (src/services/llm_matching_engine.py)
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
import asyncio

from services.llm_matching_engine import LLMMatchingEngine, get_llm_matching_engine


class TestLLMMatchingEngineInit:
    """测试 LLMMatchingEngine 初始化"""

    def test_init(self):
        """测试初始化"""
        mock_db = MagicMock()
        engine = LLMMatchingEngine(mock_db)

        assert engine.db == mock_db
        assert engine.config["max_candidates"] == 100
        assert engine.config["llm_analysis_limit"] == 20
        assert engine.config["final_recommendations"] == 10
        assert engine.config["cache_ttl_hours"] == 24
        assert engine.config["min_basic_compatibility"] == 0.3

    def test_custom_config(self):
        """测试自定义配置"""
        mock_db = MagicMock()
        engine = LLMMatchingEngine(mock_db)
        engine.config["max_candidates"] = 50

        assert engine.config["max_candidates"] == 50


class TestGenerateCacheKey:
    """测试缓存键生成"""

    def test_generate_cache_key(self):
        """测试生成缓存键"""
        mock_db = MagicMock()
        engine = LLMMatchingEngine(mock_db)

        key = engine._generate_cache_key("user-123", 10)

        assert key.startswith("deep_matches:")
        assert len(key) > len("deep_matches:")

    def test_cache_key_consistency(self):
        """测试缓存键一致性"""
        mock_db = MagicMock()
        engine = LLMMatchingEngine(mock_db)

        key1 = engine._generate_cache_key("user-123", 10)
        key2 = engine._generate_cache_key("user-123", 10)

        assert key1 == key2

    def test_cache_key_different_users(self):
        """测试不同用户缓存键不同"""
        mock_db = MagicMock()
        engine = LLMMatchingEngine(mock_db)

        key1 = engine._generate_cache_key("user-123", 10)
        key2 = engine._generate_cache_key("user-456", 10)

        assert key1 != key2


class TestGetUserProfile:
    """测试获取用户画像"""

    @pytest.mark.asyncio
    async def test_get_user_profile_success(self):
        """测试成功获取用户画像"""
        mock_db = MagicMock()

        # Mock 用户数据
        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.age = 28
        mock_user.gender = "male"
        mock_user.location = "北京"
        mock_user.interests = ["阅读", "旅行"]
        mock_user.bio = "热爱生活"
        mock_user.occupation = "工程师"
        mock_user.education = "本科"

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_user,  # 用户查询
            None,  # 偏好查询
        ]

        # Mock 对话查询
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        engine = LLMMatchingEngine(mock_db)

        with patch('services.behavior_learning_service.BehaviorLearningService') as mock_behavior:
            mock_behavior.return_value.get_user_features.return_value = None
            profile = await engine._get_user_profile("user-123")

        assert profile is not None
        assert profile["user_id"] == "user-123"
        assert profile["age"] == 28
        assert profile["gender"] == "male"
        assert profile["location"] == "北京"
        assert profile["interests"] == ["阅读", "旅行"]

    @pytest.mark.asyncio
    async def test_get_user_profile_not_found(self):
        """测试用户不存在"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        engine = LLMMatchingEngine(mock_db)
        profile = await engine._get_user_profile("nonexistent")

        assert profile is None

    @pytest.mark.asyncio
    async def test_get_user_profile_with_preferences(self):
        """测试带偏好的用户画像"""
        mock_db = MagicMock()

        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.age = 28
        mock_user.gender = "male"
        mock_user.location = "北京"
        mock_user.interests = []
        mock_user.bio = ""
        mock_user.occupation = ""
        mock_user.education = ""

        mock_preference = MagicMock()
        mock_preference.preferred_age_range = [25, 35]
        mock_preference.preferred_location_range = 30

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_user,
            mock_preference,
        ]
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        engine = LLMMatchingEngine(mock_db)

        with patch('services.behavior_learning_service.BehaviorLearningService') as mock_behavior:
            mock_behavior.return_value.get_user_features.return_value = None
            profile = await engine._get_user_profile("user-123")

        assert profile["preferences"]["age_range"] == [25, 35]
        assert profile["preferences"]["location_range"] == 30


class TestBasicFiltering:
    """测试基础条件筛选"""

    @pytest.mark.asyncio
    async def test_basic_filtering(self):
        """测试基础筛选"""
        mock_db = MagicMock()

        # Mock 候选用户
        mock_candidate1 = MagicMock()
        mock_candidate1.id = "candidate-1"
        mock_candidate1.age = 26
        mock_candidate1.gender = "female"
        mock_candidate1.location = "北京,朝阳"
        mock_candidate1.interests = ["阅读"]
        mock_candidate1.bio = ""
        mock_candidate1.occupation = ""
        mock_candidate1.education = ""
        mock_candidate1.avatar_url = None

        mock_candidate2 = MagicMock()
        mock_candidate2.id = "candidate-2"
        mock_candidate2.age = 30
        mock_candidate2.gender = "female"
        mock_candidate2.location = "北京,海淀"
        mock_candidate2.interests = []
        mock_candidate2.bio = ""
        mock_candidate2.occupation = ""
        mock_candidate2.education = ""
        mock_candidate2.avatar_url = None

        # 设置完整的 mock 链
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.filter.return_value.filter.return_value = mock_query
        mock_query.filter.return_value.filter.return_value.filter.return_value = mock_query
        mock_query.filter.return_value.filter.return_value.filter.return_value.filter.return_value = mock_query
        mock_query.filter.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value = mock_query
        mock_query.filter.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value = mock_query
        mock_query.limit.return_value.all.return_value = [mock_candidate1, mock_candidate2]

        engine = LLMMatchingEngine(mock_db)

        user_profile = {
            "gender": "male",
            "location": "北京",
            "preferences": {
                "age_range": [22, 35],
                "location_range": 50
            }
        }

        candidates = await engine._basic_filtering("user-123", user_profile)

        assert len(candidates) == 2
        assert candidates[0]["user_id"] == "candidate-1"
        assert candidates[0]["age"] == 26

    @pytest.mark.asyncio
    async def test_basic_filtering_empty(self):
        """测试空候选结果"""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.filter.return_value.filter.return_value = mock_query
        mock_query.filter.return_value.filter.return_value.filter.return_value = mock_query
        mock_query.filter.return_value.filter.return_value.filter.return_value.filter.return_value = mock_query
        mock_query.filter.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value = mock_query
        mock_query.filter.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value = mock_query
        mock_query.limit.return_value.all.return_value = []

        engine = LLMMatchingEngine(mock_db)

        user_profile = {
            "gender": "male",
            "location": "上海",
            "preferences": {
                "age_range": [22, 35],
                "location_range": 50
            }
        }

        candidates = await engine._basic_filtering("user-123", user_profile)

        assert isinstance(candidates, list)
        assert len(candidates) == 0


class TestRoughRanking:
    """测试粗排"""

    @pytest.mark.asyncio
    async def test_rough_ranking_with_interests(self):
        """测试基于兴趣的粗排"""
        mock_db = MagicMock()

        # Mock 用户画像查询
        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.age = 28
        mock_user.gender = "male"
        mock_user.location = "北京"
        mock_user.interests = ["阅读", "旅行", "音乐"]
        mock_user.bio = ""
        mock_user.occupation = "工程师"
        mock_user.education = "本科"

        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_user, None]
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        engine = LLMMatchingEngine(mock_db)

        candidates = [
            {
                "user_id": "candidate-1",
                "interests": ["阅读", "旅行", "运动"],
                "education": "本科",
                "occupation": "设计师"
            },
            {
                "user_id": "candidate-2",
                "interests": ["游戏", "电影"],
                "education": "硕士",
                "occupation": "产品经理"
            }
        ]

        with patch('services.behavior_learning_service.BehaviorLearningService') as mock_behavior:
            mock_behavior.return_value.get_user_features.return_value = None
            ranked = await engine._rough_ranking("user-123", candidates)

        assert len(ranked) == 2
        # candidate-1 有更多共同兴趣，应该排在前面
        assert ranked[0]["user_id"] == "candidate-1"
        assert "rough_score" in ranked[0]

    @pytest.mark.asyncio
    async def test_rough_ranking_education_match(self):
        """测试教育背景匹配"""
        mock_db = MagicMock()

        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.age = 28
        mock_user.gender = "male"
        mock_user.location = "北京"
        mock_user.interests = []
        mock_user.bio = ""
        mock_user.occupation = "工程师"
        mock_user.education = "本科"

        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_user, None]
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        engine = LLMMatchingEngine(mock_db)

        candidates = [
            {
                "user_id": "candidate-1",
                "interests": [],
                "education": "本科",
                "occupation": ""
            },
            {
                "user_id": "candidate-2",
                "interests": [],
                "education": "博士",
                "occupation": ""
            }
        ]

        with patch('services.behavior_learning_service.BehaviorLearningService') as mock_behavior:
            mock_behavior.return_value.get_user_features.return_value = None
            ranked = await engine._rough_ranking("user-123", candidates)

        # 相同学历的候选人应该有更高的分数
        assert ranked[0]["rough_score"] >= ranked[1]["rough_score"]


class TestDeepSemanticAnalysis:
    """测试深度语义分析"""

    @pytest.mark.asyncio
    async def test_deep_semantic_analysis(self):
        """测试深度语义分析"""
        mock_db = MagicMock()

        # Mock 用户画像
        mock_profile = MagicMock()
        mock_profile.id = "user-123"
        mock_profile.age = 28
        mock_profile.gender = "male"
        mock_profile.location = "北京"
        mock_profile.interests = []
        mock_profile.bio = ""
        mock_profile.occupation = ""
        mock_profile.education = ""

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_profile, None, mock_profile, None
        ]
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        engine = LLMMatchingEngine(mock_db)

        # Mock semantic service
        with patch.object(engine.semantic_service, 'calculate_semantic_compatibility', new_callable=AsyncMock) as mock_semantic:
            mock_semantic.return_value = {
                "overall_compatibility": 0.85,
                "value_alignment": {"aligned_values": ["信任", "真诚"]},
                "communication_compatibility": {"tips": ["多倾听"]},
                "relationship_strengths": ["互补性高"]
            }

            with patch('services.behavior_learning_service.BehaviorLearningService') as mock_behavior:
                mock_behavior.return_value.get_user_features.return_value = None

                candidates = [
                    {
                        "user_id": "candidate-1",
                        "rough_score": 0.6
                    }
                ]

                user_profile = {
                    "user_id": "user-123",
                    "conversation_samples": []
                }

                analyzed = await engine._deep_semantic_analysis("user-123", user_profile, candidates)

        assert len(analyzed) == 1
        assert "deep_analysis" in analyzed[0]
        assert analyzed[0]["semantic_score"] == 0.85

    @pytest.mark.asyncio
    async def test_deep_semantic_analysis_error_handling(self):
        """测试深度语义分析错误处理"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        engine = LLMMatchingEngine(mock_db)

        with patch.object(engine.semantic_service, 'calculate_semantic_compatibility', new_callable=AsyncMock) as mock_semantic:
            mock_semantic.side_effect = Exception("LLM Error")

            candidates = [
                {
                    "user_id": "candidate-1",
                    "rough_score": 0.6
                }
            ]

            user_profile = {
                "user_id": "user-123",
                "conversation_samples": []
            }

            analyzed = await engine._deep_semantic_analysis("user-123", user_profile, candidates)

        # 应该降级使用粗排分数
        assert len(analyzed) == 1
        assert analyzed[0]["semantic_score"] == 0.6


class TestFinalRanking:
    """测试综合排序"""

    @pytest.mark.asyncio
    async def test_final_ranking(self):
        """测试综合排序"""
        mock_db = MagicMock()
        engine = LLMMatchingEngine(mock_db)

        candidates = [
            {
                "user_id": "candidate-1",
                "name": "小红",
                "age": 26,
                "location": "北京",
                "avatar_url": "",
                "interests": ["阅读"],
                "bio": "",
                "rough_score": 0.7,
                "semantic_score": 0.9,
                "deep_analysis": {
                    "value_alignment": {"aligned_values": ["信任"]},
                    "communication_compatibility": {"tips": ["多交流"]}
                }
            },
            {
                "user_id": "candidate-2",
                "name": "小丽",
                "age": 28,
                "location": "上海",
                "avatar_url": "",
                "interests": ["旅行"],
                "bio": "",
                "rough_score": 0.5,
                "semantic_score": 0.6,
                "deep_analysis": {}
            }
        ]

        result = await engine._final_ranking(candidates, 10)

        assert len(result) == 2
        # candidate-1 应该排在前面（分数更高）
        assert result[0]["user_id"] == "candidate-1"
        assert "compatibility_score" in result[0]
        assert "match_reasons" in result[0]

    @pytest.mark.asyncio
    async def test_final_ranking_with_limit(self):
        """测试带限制的综合排序"""
        mock_db = MagicMock()
        engine = LLMMatchingEngine(mock_db)

        candidates = [
            {
                "user_id": f"candidate-{i}",
                "name": f"用户{i}",
                "age": 25 + i,
                "location": "北京",
                "avatar_url": "",
                "interests": [],
                "bio": "",
                "rough_score": 0.5 + i * 0.01,
                "semantic_score": 0.5 + i * 0.02,
                "deep_analysis": {}
            }
            for i in range(20)
        ]

        result = await engine._final_ranking(candidates, 5)

        assert len(result) == 5


class TestGenerateMatchReasons:
    """测试生成匹配理由"""

    def test_generate_match_reasons_with_llm_reasoning(self):
        """测试带 LLM 推理的匹配理由"""
        mock_db = MagicMock()
        engine = LLMMatchingEngine(mock_db)

        candidate = {
            "deep_analysis": {
                "match_reasoning": "你们都重视家庭和真诚",
                "value_alignment": {
                    "aligned_values": ["信任", "真诚", "责任"]
                },
                "communication_compatibility": {
                    "strengths": ["互补性高", "倾听能力"]
                }
            },
            "user_interests": ["阅读", "旅行"],
            "interests": ["阅读", "运动", "电影"]
        }

        reasons = engine._generate_match_reasons(candidate)

        assert len(reasons) > 0
        assert any("信任" in r or "真诚" in r for r in reasons)

    def test_generate_match_reasons_with_common_interests(self):
        """测试带共同兴趣的匹配理由"""
        mock_db = MagicMock()
        engine = LLMMatchingEngine(mock_db)

        candidate = {
            "deep_analysis": {},
            "user_interests": ["阅读", "旅行", "音乐"],
            "interests": ["阅读", "运动", "旅行"]
        }

        reasons = engine._generate_match_reasons(candidate)

        # 应该包含共同兴趣
        assert any("阅读" in r or "旅行" in r for r in reasons)

    def test_generate_match_reasons_max_four(self):
        """测试匹配理由最多 4 条"""
        mock_db = MagicMock()
        engine = LLMMatchingEngine(mock_db)

        candidate = {
            "deep_analysis": {
                "match_reasoning": "理由1",
                "value_alignment": {"aligned_values": ["信任", "真诚", "责任", "尊重", "理解"]},
                "communication_compatibility": {"strengths": ["互补性高", "倾听能力", "表达清晰"]}
            },
            "user_interests": ["阅读", "旅行", "音乐", "运动", "电影"],
            "interests": ["阅读", "旅行", "音乐", "运动", "电影"]
        }

        reasons = engine._generate_match_reasons(candidate)

        assert len(reasons) <= 4


class TestGetLLMMatchingEngine:
    """测试工厂函数"""

    def test_get_llm_matching_engine(self):
        """测试获取引擎实例"""
        mock_db = MagicMock()
        engine = get_llm_matching_engine(mock_db)

        assert engine is not None
        assert isinstance(engine, LLMMatchingEngine)
        assert engine.db == mock_db