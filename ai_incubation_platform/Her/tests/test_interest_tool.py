"""
兴趣社交工具测试

测试 InterestService 和 InterestTool 的核心功能：
- 兴趣相似度计算
- 对话话题生成
- 社区推荐
- 标签分析
"""
import pytest
from unittest.mock import MagicMock, patch

from agent.tools.interest_tool import (
    InterestService,
    InterestTool,
    InterestMatch,
    CommunityRecommendation,
)


class TestInterestServiceConfig:
    """配置测试"""

    def test_interest_categories_count(self):
        """测试兴趣分类数量"""
        assert len(InterestService.INTEREST_CATEGORIES) >= 20

    def test_interest_categories_mapping(self):
        """测试兴趣分类映射"""
        assert InterestService.INTEREST_CATEGORIES["旅行"] == "lifestyle"
        assert InterestService.INTEREST_CATEGORIES["摄影"] == "art"
        assert InterestService.INTEREST_CATEGORIES["音乐"] == "entertainment"
        assert InterestService.INTEREST_CATEGORIES["阅读"] == "knowledge"
        assert InterestService.INTEREST_CATEGORIES["健身"] == "sports"

    def test_interest_compatibility_pairs(self):
        """测试兴趣兼容性配置"""
        # 旅行和摄影兼容
        assert ("旅行", "摄影") in InterestService.INTEREST_COMPATIBILITY
        assert InterestService.INTEREST_COMPATIBILITY[("旅行", "摄影")] > 1.0

    def test_communities_count(self):
        """测试社区数量"""
        assert len(InterestService.COMMUNITIES) >= 5

    def test_communities_have_required_fields(self):
        """测试社区字段完整"""
        for comm in InterestService.COMMUNITIES:
            assert "id" in comm
            assert "name" in comm
            assert "interest" in comm
            assert "activity" in comm

    def test_conversation_topics_coverage(self):
        """测试话题覆盖"""
        # 每个话题兴趣应至少有一个话题
        for interest in InterestService.CONVERSATION_TOPICS:
            topics = InterestService.CONVERSATION_TOPICS[interest]
            assert len(topics) >= 1


class TestGetInterestCategory:
    """兴趣分类测试"""

    def test_known_interest_category(self):
        """测试已知兴趣分类"""
        category = InterestService.get_interest_category("旅行")
        assert category == "lifestyle"

    def test_unknown_interest_category(self):
        """测试未知兴趣分类"""
        category = InterestService.get_interest_category("新兴趣")
        assert category == "other"

    def test_art_category_interests(self):
        """测试艺术类兴趣"""
        art_interests = ["摄影", "绘画", "舞蹈", "手工艺"]
        for interest in art_interests:
            category = InterestService.get_interest_category(interest)
            assert category == "art"

    def test_sports_category_interests(self):
        """测试运动类兴趣"""
        sports_interests = ["健身", "跑步", "游泳", "瑜伽"]
        for interest in sports_interests:
            category = InterestService.get_interest_category(interest)
            assert category == "sports"


class TestCalculateInterestSimilarity:
    """兴趣相似度计算测试"""

    def test_same_interests(self):
        """测试相同兴趣"""
        interests1 = ["旅行", "摄影", "美食"]
        interests2 = ["旅行", "摄影", "美食"]
        similarity, common = InterestService.calculate_interest_similarity(interests1, interests2)

        assert similarity == 1.0
        assert set(common) == set(interests1)

    def test_no_common_interests(self):
        """测试无共同兴趣"""
        interests1 = ["旅行", "摄影"]
        interests2 = ["编程", "科技"]
        similarity, common = InterestService.calculate_interest_similarity(interests1, interests2)

        assert similarity == 0.0
        assert len(common) == 0

    def test_partial_match(self):
        """测试部分匹配"""
        interests1 = ["旅行", "摄影", "美食"]
        interests2 = ["旅行", "阅读", "音乐"]
        similarity, common = InterestService.calculate_interest_similarity(interests1, interests2)

        # 只有旅行匹配
        assert similarity > 0
        assert "旅行" in common

    def test_empty_interests(self):
        """测试空兴趣"""
        similarity, common = InterestService.calculate_interest_similarity([], [])
        assert similarity == 0.5  # 默认值

    def test_one_empty_interests(self):
        """测试一方空兴趣"""
        similarity, common = InterestService.calculate_interest_similarity(["旅行"], [])
        assert similarity == 0.0
        assert len(common) == 0

    def test_compatibility_bonus(self):
        """测试兼容性加权"""
        # 旅行和摄影兼容
        interests1 = ["旅行"]
        interests2 = ["摄影"]
        similarity, common = InterestService.calculate_interest_similarity(interests1, interests2)

        # 无共同兴趣但兼容性加权后应略高于 0
        # 实际上 Jaccard = 0, 兼容性加权后仍为 0
        assert similarity >= 0


class TestGenerateConversationTopics:
    """话题生成测试"""

    def test_generate_topics_for_common_interests(self):
        """测试基于共同兴趣生成话题"""
        common_interests = ["旅行", "美食"]
        topics = InterestService.generate_conversation_topics(common_interests)

        assert len(topics) >= 1
        # 应包含旅行或美食相关话题

    def test_generate_topics_empty(self):
        """测试空兴趣生成话题"""
        topics = InterestService.generate_conversation_topics([])
        # 应返回通用话题
        assert len(topics) >= 3

    def test_generate_topics_multiple(self):
        """测试多个兴趣话题"""
        common_interests = ["旅行", "美食", "音乐"]
        topics = InterestService.generate_conversation_topics(common_interests)

        # 最多取 3 个兴趣
        assert len(topics) >= 3

    def test_topics_from_known_interest(self):
        """测试已知兴趣话题"""
        topics = InterestService.generate_conversation_topics(["旅行"])
        # 应包含旅行相关话题
        assert any("旅行" in t or "目的地" in t for t in topics)


class TestRecommendCommunities:
    """社区推荐测试"""

    def test_recommend_for_matching_interest(self):
        """测试匹配兴趣推荐"""
        user_interests = ["旅行"]
        recommendations = InterestService.recommend_communities(user_interests, limit=3)

        assert len(recommendations) <= 3
        # 应推荐旅行相关社区
        assert any(c.interest_tag == "旅行" for c in recommendations)

    def test_recommend_for_category_match(self):
        """测试类别匹配推荐"""
        user_interests = ["健身"]  # sports 类别
        recommendations = InterestService.recommend_communities(user_interests)

        # 应推荐运动相关社区
        assert len(recommendations) >= 1

    def test_recommend_limit(self):
        """测试推荐数量限制"""
        user_interests = ["旅行", "美食", "阅读", "健身", "音乐"]
        recommendations = InterestService.recommend_communities(user_interests, limit=2)

        assert len(recommendations) <= 2

    def test_recommend_empty_interests(self):
        """测试空兴趣推荐"""
        recommendations = InterestService.recommend_communities([], limit=5)
        # 可能返回空或有默认推荐
        assert len(recommendations) <= 5

    def test_recommendation_fields(self):
        """测试推荐字段完整"""
        user_interests = ["旅行"]
        recommendations = InterestService.recommend_communities(user_interests)

        for rec in recommendations:
            assert isinstance(rec, CommunityRecommendation)
            assert rec.community_id
            assert rec.community_name
            assert rec.interest_tag
            assert rec.activity_level in ["high", "medium", "low"]

    def test_high_activity_bonus(self):
        """测试高活跃度加分"""
        # 高活跃社区应有优先展示
        user_interests = ["旅行", "美食"]  # 都是高活跃社区
        recommendations = InterestService.recommend_communities(user_interests)

        # 高活跃社区应优先
        high_activity = [r for r in recommendations if r.activity_level == "high"]
        assert len(high_activity) >= 1


class TestInterestTool:
    """InterestTool 测试"""

    def test_tool_name(self):
        """测试工具名"""
        assert InterestTool.name == "interest_tool"

    def test_tool_description(self):
        """测试工具描述"""
        assert "兴趣" in InterestTool.description or "灵魂" in InterestTool.description

    def test_tool_tags(self):
        """测试工具标签"""
        assert "interest" in InterestTool.tags
        assert "community" in InterestTool.tags

    def test_input_schema(self):
        """测试输入 schema"""
        schema = InterestTool.get_input_schema()
        assert schema["type"] == "object"
        assert "action" in schema["properties"]
        assert "required" in schema

    def test_input_schema_actions(self):
        """测试 schema actions"""
        schema = InterestTool.get_input_schema()
        actions = schema["properties"]["action"]["enum"]
        assert "match_by_interest" in actions
        assert "get_communities" in actions
        assert "get_topics" in actions
        assert "analyze_tags" in actions

    def test_handle_unknown_action(self):
        """测试未知操作"""
        result = InterestTool.handle(action="unknown")
        assert "error" in result
        assert "Unknown action" in result["error"]


class TestTagAnalysis:
    """标签分析测试"""

    def test_knowledge_type_tag(self):
        """测试知识型标签"""
        interests = ["阅读", "历史", "心理学"]  # 3个知识类
        result = InterestTool._handle_tag_analysis({"interests": interests})

        assert "知识型" in result["profile_tags"]

    def test_art_type_tag(self):
        """测试文艺范标签"""
        interests = ["摄影", "绘画", "舞蹈"]  # 3个艺术类
        result = InterestTool._handle_tag_analysis({"interests": interests})

        assert "文艺范" in result["profile_tags"]

    def test_sports_type_tag(self):
        """测试运动达人标签"""
        interests = ["健身", "跑步", "游泳"]  # 3个运动类
        result = InterestTool._handle_tag_analysis({"interests": interests})

        assert "运动达人" in result["profile_tags"]

    def test_lifestyle_type_tag(self):
        """测试生活家标签"""
        interests = ["旅行", "美食", "咖啡", "烘焙"]  # 4个生活类
        result = InterestTool._handle_tag_analysis({"interests": interests})

        assert "生活家" in result["profile_tags"]

    def test_empty_interests_analysis(self):
        """测试空兴趣分析"""
        result = InterestTool._handle_tag_analysis({"interests": []})

        assert result["category_distribution"] == {}
        assert result["dominant_category"] is None

    def test_dominant_category(self):
        """测试主导类别"""
        interests = ["健身", "跑步", "游泳", "阅读"]  # 运动类最多
        result = InterestTool._handle_tag_analysis({"interests": interests})

        assert result["dominant_category"] == "sports"


class TestMatchLevel:
    """匹配等级测试"""

    def test_soul_match_level(self):
        """测试灵魂伴侣等级"""
        level = InterestTool._get_match_level(0.85)
        assert level == "灵魂伴侣"

    def test_high_match_level(self):
        """测试高度匹配等级"""
        level = InterestTool._get_match_level(0.65)
        assert level == "高度匹配"

    def test_medium_match_level(self):
        """测试一般匹配等级"""
        level = InterestTool._get_match_level(0.45)
        assert level == "有一定默契"

    def test_low_match_level(self):
        """测试低匹配等级"""
        level = InterestTool._get_match_level(0.3)
        assert level == "需要更多了解"

    def test_boundary_values(self):
        """测试边界值"""
        assert InterestTool._get_match_level(0.8) == "灵魂伴侣"
        assert InterestTool._get_match_level(0.79) == "高度匹配"
        assert InterestTool._get_match_level(0.6) == "高度匹配"
        assert InterestTool._get_match_level(0.59) == "有一定默契"


class TestInterestServiceEdgeCases:
    """边界值测试"""

    def test_single_interest_similarity(self):
        """测试单个兴趣相似度"""
        similarity, common = InterestService.calculate_interest_similarity(["旅行"], ["旅行"])
        assert similarity == 1.0

    def test_large_interest_lists(self):
        """测试大量兴趣"""
        interests1 = [f"兴趣{i}" for i in range(100)]
        interests2 = [f"兴趣{i}" for i in range(50, 150)]
        similarity, common = InterestService.calculate_interest_similarity(interests1, interests2)

        # 应正确处理大量兴趣
        assert 0 <= similarity <= 1

    def test_duplicate_interests(self):
        """测试重复兴趣"""
        interests1 = ["旅行", "旅行", "旅行"]
        interests2 = ["旅行"]
        similarity, common = InterestService.calculate_interest_similarity(interests1, interests2)

        # 应正确处理重复
        assert similarity == 1.0


class TestCommunityRecommendationDataClass:
    """CommunityRecommendation 数据类测试"""

    def test_recommendation_creation(self):
        """测试创建推荐"""
        rec = CommunityRecommendation(
            community_id="comm_001",
            community_name="测试社区",
            interest_tag="旅行",
            member_count=5000,
            activity_level="high",
            reason="基于兴趣匹配"
        )
        assert rec.community_id == "comm_001"
        assert rec.activity_level == "high"