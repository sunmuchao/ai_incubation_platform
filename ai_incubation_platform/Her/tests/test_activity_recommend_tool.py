"""
活动推荐工具测试

测试 ActivityRecommendTool 的核心功能：
- 活动推荐生成
- 共同兴趣匹配
- 难度过滤
- 通用活动推荐
"""
import pytest
from unittest.mock import MagicMock, patch

from agent.tools.activity_recommend_tool import ActivityRecommendTool


class TestActivityRecommendToolConfig:
    """配置测试"""

    def test_tool_name(self):
        """测试工具名"""
        assert ActivityRecommendTool.name == "activity_recommend"

    def test_tool_description(self):
        """测试工具描述"""
        assert "活动" in ActivityRecommendTool.description or "推荐" in ActivityRecommendTool.description

    def test_tool_tags(self):
        """测试工具标签"""
        assert "activity" in ActivityRecommendTool.tags
        assert "recommend" in ActivityRecommendTool.tags

    def test_interest_to_activity_count(self):
        """测试兴趣到活动映射数量"""
        assert len(ActivityRecommendTool.INTEREST_TO_ACTIVITY) >= 10

    def test_interest_to_activity_content(self):
        """测试兴趣到活动映射内容"""
        assert "阅读" in ActivityRecommendTool.INTEREST_TO_ACTIVITY
        assert "旅行" in ActivityRecommendTool.INTEREST_TO_ACTIVITY
        assert "音乐" in ActivityRecommendTool.INTEREST_TO_ACTIVITY
        assert "电影" in ActivityRecommendTool.INTEREST_TO_ACTIVITY

    def test_activities_per_interest(self):
        """测试每个兴趣的活动数量"""
        for interest, activities in ActivityRecommendTool.INTEREST_TO_ACTIVITY.items():
            assert len(activities) >= 1

    def test_activity_difficulty_levels(self):
        """测试活动难度级别"""
        assert len(ActivityRecommendTool.ACTIVITY_DIFFICULTY) >= 5
        assert "咖啡厅" in ActivityRecommendTool.ACTIVITY_DIFFICULTY
        assert "密室逃脱" in ActivityRecommendTool.ACTIVITY_DIFFICULTY

    def test_difficulty_values(self):
        """测试难度值"""
        difficulties = ActivityRecommendTool.ACTIVITY_DIFFICULTY.values()
        assert "easy" in difficulties
        assert "medium" in difficulties
        assert "hard" in difficulties


class TestInputSchema:
    """输入 Schema 测试"""

    def test_input_schema_type(self):
        """测试 schema 类型"""
        schema = ActivityRecommendTool.get_input_schema()
        assert schema["type"] == "object"

    def test_input_schema_required_fields(self):
        """测试必填字段"""
        schema = ActivityRecommendTool.get_input_schema()
        assert "user_interests" in schema["required"]
        assert "target_interests" in schema["required"]

    def test_input_schema_optional_fields(self):
        """测试可选字段"""
        schema = ActivityRecommendTool.get_input_schema()
        assert "location" in schema["properties"]
        assert "difficulty" in schema["properties"]

    def test_difficulty_enum(self):
        """测试难度枚举"""
        schema = ActivityRecommendTool.get_input_schema()
        difficulty_enum = schema["properties"]["difficulty"]["enum"]
        assert "easy" in difficulty_enum
        assert "medium" in difficulty_enum
        assert "hard" in difficulty_enum
        assert "any" in difficulty_enum

    def test_user_interests_array_type(self):
        """测试用户兴趣数组类型"""
        schema = ActivityRecommendTool.get_input_schema()
        assert schema["properties"]["user_interests"]["type"] == "array"


class TestHandleActivityRecommend:
    """活动推荐处理测试"""

    def test_handle_with_common_interests(self):
        """测试有共同兴趣"""
        result = ActivityRecommendTool.handle(
            user_interests=["阅读", "音乐", "旅行"],
            target_interests=["阅读", "电影", "美食"]
        )

        assert "recommendations" in result
        assert "common_interests" in result
        assert "阅读" in result["common_interests"]
        assert len(result["recommendations"]) > 0

    def test_handle_no_common_interests(self):
        """测试无共同兴趣"""
        result = ActivityRecommendTool.handle(
            user_interests=["阅读", "音乐"],
            target_interests=["健身", "游戏"]
        )

        # 应提供通用活动推荐
        assert len(result["recommendations"]) > 0
        assert result["common_interests"] == []

    def test_handle_with_location(self):
        """测试带地点"""
        result = ActivityRecommendTool.handle(
            user_interests=["阅读", "音乐"],
            target_interests=["阅读"],
            location="北京"
        )

        assert "recommendations" in result

    def test_handle_with_difficulty_easy(self):
        """测试难度过滤 - easy"""
        result = ActivityRecommendTool.handle(
            user_interests=["阅读", "咖啡"],
            target_interests=["阅读", "咖啡"],
            difficulty="easy"
        )

        assert "recommendations" in result
        # 所有推荐应为 easy 难度
        for rec in result["recommendations"]:
            assert rec["difficulty"] == "easy"

    def test_handle_with_difficulty_hard(self):
        """测试难度过滤 - hard"""
        result = ActivityRecommendTool.handle(
            user_interests=["游戏"],
            target_interests=["游戏"],
            difficulty="hard"
        )

        # hard 难度的活动可能有限
        assert "recommendations" in result

    def test_handle_with_difficulty_any(self):
        """测试难度过滤 - any"""
        result = ActivityRecommendTool.handle(
            user_interests=["阅读", "音乐"],
            target_interests=["阅读"],
            difficulty="any"
        )

        assert len(result["recommendations"]) > 0

    def test_handle_recommendations_count(self):
        """测试推荐数量限制"""
        result = ActivityRecommendTool.handle(
            user_interests=["阅读", "音乐", "旅行", "电影"],
            target_interests=["阅读", "音乐", "旅行", "电影"]
        )

        # 应最多返回 5 个推荐
        assert len(result["recommendations"]) <= 5

    def test_handle_recommendation_structure(self):
        """测试推荐结构"""
        result = ActivityRecommendTool.handle(
            user_interests=["阅读"],
            target_interests=["阅读"]
        )

        if result["recommendations"]:
            rec = result["recommendations"][0]
            assert "activity" in rec
            assert "based_on_interest" in rec
            assert "difficulty" in rec
            assert "description" in rec

    def test_handle_total_count(self):
        """测试总数统计"""
        result = ActivityRecommendTool.handle(
            user_interests=["阅读", "音乐"],
            target_interests=["阅读"]
        )

        assert "total" in result


class TestGetActivityDescription:
    """活动描述获取测试"""

    def test_get_bookstore_description(self):
        """测试书店约会描述"""
        desc = ActivityRecommendTool._get_activity_description("书店约会")
        assert "书店" in desc or "书" in desc

    def test_get_cafe_description(self):
        """测试咖啡厅描述"""
        desc = ActivityRecommendTool._get_activity_description("咖啡厅闲聊")
        assert "咖啡" in desc or "聊天" in desc

    def test_get_park_description(self):
        """测试公园散步描述"""
        desc = ActivityRecommendTool._get_activity_description("公园散步")
        assert "散步" in desc or "自然" in desc

    def test_get_unknown_activity_description(self):
        """测试未知活动描述"""
        desc = ActivityRecommendTool._get_activity_description("未知活动")
        assert "愉快" in desc or "时光" in desc

    def test_get_escape_room_description(self):
        """测试密室逃脱描述"""
        desc = ActivityRecommendTool._get_activity_description("密室逃脱")
        assert "解谜" in desc or "默契" in desc

    def test_get_concert_description(self):
        """测试音乐会描述"""
        desc = ActivityRecommendTool._get_activity_description("音乐会")
        assert "音乐" in desc or "艺术" in desc


class TestInterestActivityMapping:
    """兴趣活动映射测试"""

    def test_reading_activities(self):
        """测试阅读活动"""
        activities = ActivityRecommendTool.INTEREST_TO_ACTIVITY.get("阅读", [])
        assert "书店约会" in activities or "图书馆" in activities

    def test_travel_activities(self):
        """测试旅行活动"""
        activities = ActivityRecommendTool.INTEREST_TO_ACTIVITY.get("旅行", [])
        assert "城市探索" in activities or "周边游" in activities

    def test_music_activities(self):
        """测试音乐活动"""
        activities = ActivityRecommendTool.INTEREST_TO_ACTIVITY.get("音乐", [])
        assert "音乐会" in activities or "Livehouse" in activities

    def test_movie_activities(self):
        """测试电影活动"""
        activities = ActivityRecommendTool.INTEREST_TO_ACTIVITY.get("电影", [])
        assert "电影院" in activities

    def test_fitness_activities(self):
        """测试健身活动"""
        activities = ActivityRecommendTool.INTEREST_TO_ACTIVITY.get("健身", [])
        assert "健身房" in activities or "瑜伽课" in activities

    def test_food_activities(self):
        """测试美食活动"""
        activities = ActivityRecommendTool.INTEREST_TO_ACTIVITY.get("美食", [])
        assert "美食探店" in activities or "DIY 料理" in activities

    def test_art_activities(self):
        """测试艺术活动"""
        activities = ActivityRecommendTool.INTEREST_TO_ACTIVITY.get("艺术", [])
        assert "美术馆" in activities or "艺术展览" in activities

    def test_game_activities(self):
        """测试游戏活动"""
        activities = ActivityRecommendTool.INTEREST_TO_ACTIVITY.get("游戏", [])
        assert "电玩城" in activities or "桌游吧" in activities


class TestDifficultySorting:
    """难度排序测试"""

    def test_recommendations_sorted_by_difficulty(self):
        """测试推荐按难度排序"""
        result = ActivityRecommendTool.handle(
            user_interests=["阅读", "游戏"],
            target_interests=["阅读", "游戏"],
            difficulty="any"
        )

        # 检查排序（先易后难）
        difficulty_order = {"easy": 0, "medium": 1, "hard": 2}
        if len(result["recommendations"]) > 1:
            for i in range(len(result["recommendations"]) - 1):
                curr_diff = result["recommendations"][i]["difficulty"]
                next_diff = result["recommendations"][i + 1]["difficulty"]
                assert difficulty_order.get(curr_diff, 1) <= difficulty_order.get(next_diff, 2)


class TestEdgeCases:
    """边界值测试"""

    def test_empty_interests(self):
        """测试空兴趣列表"""
        result = ActivityRecommendTool.handle(
            user_interests=[],
            target_interests=[]
        )

        # 应提供通用活动推荐
        assert len(result["recommendations"]) > 0

    def test_single_interest(self):
        """测试单个兴趣"""
        result = ActivityRecommendTool.handle(
            user_interests=["阅读"],
            target_interests=["阅读"]
        )

        assert len(result["recommendations"]) > 0

    def test_many_common_interests(self):
        """测试多个共同兴趣"""
        result = ActivityRecommendTool.handle(
            user_interests=["阅读", "音乐", "旅行", "电影", "健身"],
            target_interests=["阅读", "音乐", "旅行", "电影", "健身"]
        )

        # 即使有多个共同兴趣，推荐数量也应限制
        assert len(result["recommendations"]) <= 5

    def test_unknown_interest(self):
        """测试未知兴趣"""
        result = ActivityRecommendTool.handle(
            user_interests=["未知兴趣"],
            target_interests=["未知兴趣"]
        )

        # 应提供通用活动推荐
        assert len(result["recommendations"]) > 0

    def test_all_difficulty_levels(self):
        """测试所有难度级别"""
        for difficulty in ["easy", "medium", "hard", "any"]:
            result = ActivityRecommendTool.handle(
                user_interests=["阅读"],
                target_interests=["阅读"],
                difficulty=difficulty
            )
            assert "recommendations" in result

    def test_special_characters_in_interest(self):
        """测试兴趣中的特殊字符"""
        result = ActivityRecommendTool.handle(
            user_interests=["阅读", "测试!@#"],
            target_interests=["阅读"]
        )

        assert "recommendations" in result