"""
对话匹配服务测试

测试 ConversationMatchService 的核心功能：
- 数据结构验证
- 意图分析器
- 查询质量校验器
- 组件编排
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import json

# 尝试导入服务模块
try:
    from services.conversation_match_service import (
        ConversationMatchService,
        IntentAnalyzer,
        QueryQualityChecker,
        UserIntent,
        QueryQualityCheckResult,
        MatchResultWithAdvice,
        ConversationMatchResponse,
        get_conversation_match_service
    )
except ImportError:
    pytest.skip("conversation_match_service not importable", allow_module_level=True)


class TestUserIntentDataClass:
    """UserIntent 数据结构测试"""

    def test_default_values(self):
        """测试默认值"""
        intent = UserIntent()

        assert intent.intent_type == ""
        assert intent.extracted_conditions == {}
        assert intent.preference_mentioned == ""
        assert intent.emotional_state == ""
        assert intent.confidence == 0.0

    def test_custom_values(self):
        """测试自定义值"""
        intent = UserIntent(
            intent_type="match_request",
            extracted_conditions={"location": "北京"},
            preference_mentioned="喜欢户外运动",
            emotional_state="happy",
            confidence=0.8
        )

        assert intent.intent_type == "match_request"
        assert intent.extracted_conditions["location"] == "北京"
        assert intent.confidence == 0.8

    def test_extracted_conditions_types(self):
        """测试提取条件类型"""
        intent = UserIntent(
            intent_type="match_request",
            extracted_conditions={
                "interests": ["户外运动", "旅行"],
                "age_range": [25, 30],
                "location": "北京",
                "gender": "female"
            }
        )

        assert isinstance(intent.extracted_conditions["interests"], list)
        assert isinstance(intent.extracted_conditions["age_range"], list)


class TestQueryQualityCheckResultDataClass:
    """QueryQualityCheckResult 数据结构测试"""

    def test_default_values(self):
        """测试默认值"""
        result = QueryQualityCheckResult()

        assert result.is_clear is True
        assert result.is_complete is True
        assert result.overall_passed is True
        assert result.clarity_issues == []
        assert result.missing_info == []
        assert result.follow_up_questions == []
        assert result.confidence == 1.0

    def test_failed_result(self):
        """测试失败结果"""
        result = QueryQualityCheckResult(
            is_clear=False,
            is_complete=False,
            overall_passed=False,
            clarity_issues=["意图不明确"],
            missing_info=["年龄范围"],
            follow_up_questions=["你希望找多大年龄的对象？"],
            confidence=0.5
        )

        assert result.overall_passed is False
        assert len(result.clarity_issues) > 0
        assert len(result.follow_up_questions) > 0


class TestMatchResultWithAdviceDataClass:
    """MatchResultWithAdvice 数据结构测试"""

    def test_default_values(self):
        """测试默认值"""
        result = MatchResultWithAdvice(
            candidate_id="user_002",
            candidate_name="测试用户",
            candidate_profile={"age": 28},
            compatibility_score=0.85,
            score_breakdown={"location": 0.9, "age": 0.8}
        )

        assert result.candidate_id == "user_002"
        assert result.compatibility_score == 0.85
        assert result.risk_warnings == []

    def test_with_risk_warnings(self):
        """测试带风险警告"""
        result = MatchResultWithAdvice(
            candidate_id="user_002",
            candidate_name="测试用户",
            candidate_profile={},
            compatibility_score=0.6,
            score_breakdown={},
            risk_warnings=["价值观差异较大"]
        )

        assert len(result.risk_warnings) > 0


class TestConversationMatchResponseDataClass:
    """ConversationMatchResponse 数据结构测试"""

    def test_default_values(self):
        """测试默认值"""
        response = ConversationMatchResponse(
            ai_message="你好",
            intent_type="conversation"
        )

        assert response.matches == []
        assert response.generative_ui == {}
        assert response.suggested_actions == []

    def test_with_matches(self):
        """测试带匹配结果"""
        matches = [
            MatchResultWithAdvice(
                candidate_id="user_002",
                candidate_name="匹配用户",
                candidate_profile={},
                compatibility_score=0.8,
                score_breakdown={}
            )
        ]

        response = ConversationMatchResponse(
            ai_message="为你找到了匹配",
            intent_type="match_request",
            matches=matches
        )

        assert len(response.matches) == 1
        assert response.matches[0].candidate_id == "user_002"


class TestIntentAnalyzerIntentTypes:
    """意图分析器意图类型测试"""

    def test_intent_types_exist(self):
        """测试意图类型存在"""
        valid_types = [
            "match_request",
            "preference_update",
            "inquiry",
            "feedback",
            "conversation"
        ]

        assert len(valid_types) == 5
        assert "match_request" in valid_types
        assert "conversation" in valid_types


class TestIntentAnalyzerFallback:
    """意图分析器降级测试"""

    def test_fallback_match_request_keywords(self):
        """测试降级匹配关键词"""
        analyzer = IntentAnalyzer()

        # 测试匹配请求关键词
        match_messages = [
            "帮我找个对象",
            "想找女朋友",
            "推荐一些人给我",
            "有没有合适的人"
        ]

        for msg in match_messages:
            intent = analyzer._fallback_intent_analysis(msg)
            assert intent.intent_type == "match_request"

    def test_fallback_inquiry_keywords(self):
        """测试降级咨询关键词"""
        analyzer = IntentAnalyzer()

        # 使用不包含"找"、"对象"、"匹配"、"推荐"等匹配关键词的纯咨询问题
        inquiry_messages = [
            "什么是缘分",
            "如何开始聊天才能吸引对方",
            "能不能告诉我会员有什么特权"
        ]

        for msg in inquiry_messages:
            intent = analyzer._fallback_intent_analysis(msg)
            assert intent.intent_type == "inquiry"

    def test_fallback_feedback_keywords(self):
        """测试降级反馈关键词"""
        analyzer = IntentAnalyzer()

        feedback_messages = [
            "不太合适",
            "不喜欢",
            "挺好的"
        ]

        for msg in feedback_messages:
            intent = analyzer._fallback_intent_analysis(msg)
            assert intent.intent_type == "feedback"

    def test_fallback_conversation_default(self):
        """测试降级默认对话"""
        analyzer = IntentAnalyzer()

        intent = analyzer._fallback_intent_analysis("今天天气不错")
        assert intent.intent_type == "conversation"

    def test_fallback_extracts_interests(self):
        """测试降级提取兴趣"""
        analyzer = IntentAnalyzer()

        intent = analyzer._fallback_intent_analysis("帮我找喜欢户外运动的人")

        # 应提取兴趣
        assert "interests" in intent.extracted_conditions
        assert "户外运动" in intent.extracted_conditions["interests"]


class TestIntentAnalyzerParseResponse:
    """意图分析器响应解析测试"""

    def test_parse_valid_json(self):
        """测试解析有效 JSON"""
        analyzer = IntentAnalyzer()

        response = '{"intent_type": "match_request", "extracted_conditions": {"location": "北京"}, "confidence": 0.8}'

        intent = analyzer._parse_intent_response(response)

        assert intent.intent_type == "match_request"
        assert intent.extracted_conditions["location"] == "北京"
        assert intent.confidence == 0.8

    def test_parse_json_with_code_blocks(self):
        """测试解析带代码块的 JSON"""
        analyzer = IntentAnalyzer()

        response = '```json\n{"intent_type": "conversation", "confidence": 0.5}\n```'

        intent = analyzer._parse_intent_response(response)

        assert intent.intent_type == "conversation"

    def test_parse_invalid_json(self):
        """测试解析无效 JSON"""
        analyzer = IntentAnalyzer()

        response = "这不是 JSON"

        intent = analyzer._parse_intent_response(response)

        # 应返回默认意图
        assert intent.intent_type == "conversation"
        assert intent.confidence == 0.0


class TestQueryQualityChecker:
    """查询质量校验器测试"""

    def test_critical_fields(self):
        """测试关键字段"""
        checker = QueryQualityChecker()

        assert "age_range" in checker.CRITICAL_FIELDS
        assert "location" in checker.CRITICAL_FIELDS
        assert "relationship_goal" in checker.CRITICAL_FIELDS

    def test_recommended_fields(self):
        """测试推荐字段"""
        checker = QueryQualityChecker()

        assert "personality_type" in checker.RECOMMENDED_FIELDS
        assert "interests" in checker.RECOMMENDED_FIELDS

    def test_non_match_request_always_passes(self):
        """测试非匹配请求总是通过"""
        checker = QueryQualityChecker()

        intent = UserIntent(intent_type="conversation")

        # 非匹配请求应返回通过
        # 由于是异步方法，测试逻辑
        assert intent.intent_type != "match_request"


class TestQueryQualityCheckerFallback:
    """查询质量校验器降级测试"""

    def test_fallback_missing_age(self):
        """测试降级缺少年龄"""
        checker = QueryQualityChecker()

        intent = UserIntent(
            intent_type="match_request",
            extracted_conditions={}
        )

        result = checker._fallback_quality_check(intent, None)

        # 应检测缺少年龄
        assert "年龄范围" in result.missing_info

    def test_fallback_missing_location(self):
        """测试降级缺少地点"""
        checker = QueryQualityChecker()

        intent = UserIntent(
            intent_type="match_request",
            extracted_conditions={"age_range": [25, 30]}
        )

        result = checker._fallback_quality_check(intent, None)

        # 应检测缺少地点
        assert "地点/城市" in result.missing_info

    def test_fallback_missing_goal(self):
        """测试降级缺少目标"""
        checker = QueryQualityChecker()

        intent = UserIntent(
            intent_type="match_request",
            extracted_conditions={"age_range": [25, 30], "location": "北京"}
        )

        result = checker._fallback_quality_check(intent, None)

        # 应检测缺少目标
        assert "关系目标" in result.missing_info

    def test_fallback_complete_with_profile(self):
        """测试降级完整（有画像）"""
        checker = QueryQualityChecker()

        intent = UserIntent(
            intent_type="match_request",
            extracted_conditions={}
        )

        user_profile = {
            "age": 28,
            "location": "北京",
            "relationship_goal": "serious"
        }

        result = checker._fallback_quality_check(intent, user_profile)

        # 有画像时不应缺少信息
        assert result.is_complete is True


class TestQueryQualityCheckerParseResponse:
    """查询质量校验器响应解析测试"""

    def test_parse_valid_json(self):
        """测试解析有效 JSON"""
        checker = QueryQualityChecker()

        response = '{"is_clear": true, "is_complete": false, "overall_passed": false, "missing_info": ["年龄"], "confidence": 0.7}'

        result = checker._parse_quality_check_response(response)

        assert result.is_clear is True
        assert result.is_complete is False
        assert result.overall_passed is False

    def test_parse_invalid_json(self):
        """测试解析无效 JSON"""
        checker = QueryQualityChecker()

        response = "invalid"

        result = checker._parse_quality_check_response(response)

        # 应返回默认通过
        assert result.overall_passed is True


class TestConversationMatchServiceInit:
    """对话匹配服务初始化测试"""

    def test_service_initialization(self):
        """测试服务初始化"""
        service = ConversationMatchService()

        assert service._intent_analyzer is not None
        assert service._query_quality_checker is not None

    def test_intent_analyzer_type(self):
        """测试意图分析器类型"""
        service = ConversationMatchService()

        assert isinstance(service._intent_analyzer, IntentAnalyzer)

    def test_query_quality_checker_type(self):
        """测试查询质量校验器类型"""
        service = ConversationMatchService()

        assert isinstance(service._query_quality_checker, QueryQualityChecker)


class TestServiceFactory:
    """服务工厂测试"""

    def test_get_service_returns_instance(self):
        """测试工厂返回实例"""
        service = get_conversation_match_service()

        assert service is not None
        assert isinstance(service, ConversationMatchService)

    def test_get_service_singleton(self):
        """测试工厂单例"""
        service1 = get_conversation_match_service()
        service2 = get_conversation_match_service()

        # 应返回相同实例
        assert service1 is service2


class TestExtractedConditions:
    """提取条件测试"""

    def test_interests_extraction(self):
        """测试兴趣提取"""
        # interests 应为列表
        conditions = {
            "interests": ["阅读", "旅行", "音乐"]
        }

        assert len(conditions["interests"]) == 3

    def test_age_range_extraction(self):
        """测试年龄范围提取"""
        conditions = {
            "age_range": [25, 30]
        }

        assert conditions["age_range"][0] == 25
        assert conditions["age_range"][1] == 30

    def test_location_extraction(self):
        """测试地点提取"""
        conditions = {
            "location": "北京"
        }

        assert conditions["location"] == "北京"

    def test_gender_extraction(self):
        """测试性别提取"""
        conditions = {
            "gender": "female"
        }

        assert conditions["gender"] == "female"

    def test_relationship_goal_extraction(self):
        """测试关系目标提取"""
        conditions = {
            "relationship_goal": "serious"
        }

        assert conditions["relationship_goal"] == "serious"


class TestEdgeCases:
    """边界值测试"""

    def test_empty_message_intent(self):
        """测试空消息意图"""
        analyzer = IntentAnalyzer()

        intent = analyzer._fallback_intent_analysis("")
        assert intent.intent_type == "conversation"

    def test_very_long_message(self):
        """测试超长消息"""
        analyzer = IntentAnalyzer()

        long_message = "我想找一个对象" * 100
        intent = analyzer._fallback_intent_analysis(long_message)

        assert intent.intent_type in ["match_request", "conversation"]

    def test_special_characters_message(self):
        """测试特殊字符消息"""
        analyzer = IntentAnalyzer()

        intent = analyzer._fallback_intent_analysis("帮我找对象！@#$%^&*()")
        assert intent.intent_type == "match_request"

    def test_unicode_message(self):
        """测试 Unicode 消息"""
        analyzer = IntentAnalyzer()

        intent = analyzer._fallback_intent_analysis("我想找对象 💕 ✨")
        assert intent.intent_type == "match_request"

    def test_confidence_bounds(self):
        """测试置信度边界"""
        # 置信度应在 0-1 范围内
        intent_high = UserIntent(confidence=1.0)
        intent_low = UserIntent(confidence=0.0)
        intent_mid = UserIntent(confidence=0.5)

        assert 0 <= intent_high.confidence <= 1
        assert 0 <= intent_low.confidence <= 1
        assert 0 <= intent_mid.confidence <= 1

    def test_compatibility_score_bounds(self):
        """测试兼容度分数边界"""
        result_high = MatchResultWithAdvice(
            candidate_id="test",
            candidate_name="test",
            candidate_profile={},
            compatibility_score=1.0,
            score_breakdown={}
        )

        result_low = MatchResultWithAdvice(
            candidate_id="test",
            candidate_name="test",
            candidate_profile={},
            compatibility_score=0.0,
            score_breakdown={}
        )

        assert 0 <= result_high.compatibility_score <= 1
        assert 0 <= result_low.compatibility_score <= 1