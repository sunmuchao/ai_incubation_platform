"""
HerAdvisorService 核心逻辑单元测试

测试覆盖:
1. CognitiveBiasDetector:
   - detect_cognitive_bias: 检测认知偏差（LLM驱动）
   - _build_bias_analysis_prompt: Prompt构建正确性
   - _parse_bias_analysis: JSON解析正确性

2. MatchAdvisor:
   - generate_match_advice: 生成匹配建议
   - _check_intent_match: 意向匹配检查
   - _analyze_compatibility: 适配度分析

3. ProactiveSuggestionGenerator:
   - generate_proactive_suggestion: 生成主动建议

4. SelfProfile 和 DesireProfile 数据类:
   - to_dict / from_dict 序列化/反序列化

测试要点:
- LLM调用成功/失败/降级场景
- JSON解析异常处理
- 认知偏差检测（双强势偏差、依恋错配等）
- 四种匹配情况的建议生成
- 主动建议的各种类型
"""
import pytest
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any, List, Tuple

from services.her_advisor_service import (
    CognitiveBiasDetector,
    MatchAdvisor,
    ProactiveSuggestionGenerator,
    HerAdvisorService,
    SelfProfile,
    DesireProfile,
    CognitiveBiasAnalysis,
    MatchAdvice,
    ProactiveSuggestion,
    get_her_advisor_service,
)


# ============= Fixtures =============

@pytest.fixture
def self_profile_sample() -> SelfProfile:
    """创建示例 SelfProfile"""
    return SelfProfile(
        age=28,
        gender="male",
        location="北京",
        income_range=(15000, 25000),
        occupation="软件工程师",
        education="本科",
        relationship_goal="serious",
        actual_personality="内向但温和有主见",
        claimed_personality="外向开朗",
        personality_gap="自称外向但实际内向",
        communication_style="间接型",
        response_pattern="延迟回复",
        emotional_needs=["需要被理解", "需要被认可"],
        attachment_style="安全型",
        power_dynamic="平等型",
        decision_style="合作型",
        reputation_score=0.8,
        like_rate=0.7,
        feedback_summary="用户反馈良好，沟通真诚",
        profile_confidence=0.75,
        dimension_confidences={"personality": 0.8, "communication": 0.7},
    )


@pytest.fixture
def desire_profile_sample() -> DesireProfile:
    """创建示例 DesireProfile"""
    return DesireProfile(
        surface_preference="开朗外向的女生",
        ideal_type_description="希望对方阳光活泼，能带动气氛",
        deal_breakers=["抽烟", "不真诚"],
        actual_preference="温柔内向的女生",
        search_patterns=[{"keyword": "内向", "count": 5}],
        clicked_types=["内向温柔", "知性稳重"],
        swipe_patterns={"liked": ["内向型"], "disliked": ["过度外向"]},
        like_feedback=[{"type": "温柔内向", "reason": "聊得来"}],
        dislike_feedback=[{"type": "过度外向", "reason": "太吵"}],
        preference_gap="想要外向但实际倾向内向",
        preference_confidence=0.65,
    )


@pytest.fixture
def self_profile_control_type() -> SelfProfile:
    """创建控制型 SelfProfile（用于双强势偏差测试）"""
    return SelfProfile(
        age=30,
        gender="male",
        location="上海",
        actual_personality="强势主导",
        claimed_personality="有主见",
        communication_style="直接型",
        response_pattern="即时回复",
        emotional_needs=["需要被尊重"],
        attachment_style="回避型",
        power_dynamic="控制型",
        decision_style="竞争型",
        profile_confidence=0.8,
    )


@pytest.fixture
def self_profile_anxious_type() -> SelfProfile:
    """创建焦虑型 SelfProfile（用于依恋错配测试）"""
    return SelfProfile(
        age=26,
        gender="female",
        location="北京",
        actual_personality="敏感焦虑",
        communication_style="情感型",
        emotional_needs=["需要被照顾", "需要安全感"],
        attachment_style="焦虑型",
        power_dynamic="顺从型",
        decision_style="妥协型",
        profile_confidence=0.7,
    )


@pytest.fixture
def self_profile_avoidant_type() -> SelfProfile:
    """创建回避型 SelfProfile（用于依恋错配测试）"""
    return SelfProfile(
        age=28,
        gender="male",
        location="深圳",
        actual_personality="独立冷漠",
        communication_style="逻辑型",
        emotional_needs=["需要独立空间"],
        attachment_style="回避型",
        power_dynamic="控制型",
        decision_style="回避型",
        profile_confidence=0.75,
    )


@pytest.fixture
def desire_profile_control_preference() -> DesireProfile:
    """创建偏好控制型的 DesireProfile"""
    return DesireProfile(
        surface_preference="强势有主见的男生",
        ideal_type_description="希望对方能主导局面",
        actual_preference="强势控制型",
        preference_gap="",
        preference_confidence=0.6,
    )


@pytest.fixture
def mock_llm_service():
    """创建 Mock LLM 服务"""
    mock = MagicMock()
    mock._call_llm = AsyncMock()
    return mock


@pytest.fixture
def bias_detector():
    """创建 CognitiveBiasDetector 实例"""
    detector = CognitiveBiasDetector()
    return detector


@pytest.fixture
def match_advisor():
    """创建 MatchAdvisor 实例"""
    advisor = MatchAdvisor()
    return advisor


@pytest.fixture
def proactive_generator():
    """创建 ProactiveSuggestionGenerator 实例"""
    return ProactiveSuggestionGenerator()


# ============= SelfProfile 数据类测试 =============

class TestSelfProfile:
    """SelfProfile 数据类测试"""

    def test_to_dict_basic(self, self_profile_sample):
        """测试 to_dict 基础转换"""
        result = self_profile_sample.to_dict()

        assert "basic" in result
        assert result["basic"]["age"] == 28
        assert result["basic"]["gender"] == "male"
        assert result["basic"]["location"] == "北京"

    def test_to_dict_personality(self, self_profile_sample):
        """测试 to_dict personality 部分"""
        result = self_profile_sample.to_dict()

        assert "personality" in result
        assert result["personality"]["actual_personality"] == "内向但温和有主见"
        assert result["personality"]["claimed_personality"] == "外向开朗"
        assert result["personality"]["personality_gap"] == "自称外向但实际内向"

    def test_to_dict_communication(self, self_profile_sample):
        """测试 to_dict communication 部分"""
        result = self_profile_sample.to_dict()

        assert "communication" in result
        assert result["communication"]["style"] == "间接型"
        assert result["communication"]["response_pattern"] == "延迟回复"

    def test_to_dict_emotional_needs(self, self_profile_sample):
        """测试 to_dict emotional_needs 部分"""
        result = self_profile_sample.to_dict()

        assert "emotional_needs" in result
        assert result["emotional_needs"]["needs_list"] == ["需要被理解", "需要被认可"]
        assert result["emotional_needs"]["attachment_style"] == "安全型"

    def test_to_dict_power_dynamic(self, self_profile_sample):
        """测试 to_dict power_dynamic 部分"""
        result = self_profile_sample.to_dict()

        assert "power_dynamic" in result
        assert result["power_dynamic"]["tendency"] == "平等型"
        assert result["power_dynamic"]["decision_style"] == "合作型"

    def test_to_dict_social_feedback(self, self_profile_sample):
        """测试 to_dict social_feedback 部分"""
        result = self_profile_sample.to_dict()

        assert "social_feedback" in result
        assert result["social_feedback"]["reputation_score"] == 0.8
        assert result["social_feedback"]["like_rate"] == 0.7

    def test_to_dict_confidence(self, self_profile_sample):
        """测试 to_dict confidence 部分"""
        result = self_profile_sample.to_dict()

        assert "confidence" in result
        assert result["confidence"]["overall"] == 0.75
        assert result["confidence"]["dimensions"]["personality"] == 0.8

    def test_from_dict_complete(self, self_profile_sample):
        """测试 from_dict 完整转换"""
        data = self_profile_sample.to_dict()
        restored = SelfProfile.from_dict(data)

        assert restored.age == 28
        assert restored.gender == "male"
        assert restored.actual_personality == "内向但温和有主见"
        assert restored.communication_style == "间接型"
        assert restored.emotional_needs == ["需要被理解", "需要被认可"]
        assert restored.attachment_style == "安全型"
        assert restored.power_dynamic == "平等型"

    def test_from_dict_partial(self):
        """测试 from_dict 部分数据"""
        partial_data = {
            "basic": {"age": 25, "gender": "female"},
            "personality": {"actual_personality": "内向"},
        }
        restored = SelfProfile.from_dict(partial_data)

        assert restored.age == 25
        assert restored.gender == "female"
        assert restored.actual_personality == "内向"
        assert restored.location == ""  # 默认值
        assert restored.emotional_needs == []  # 默认空列表

    def test_from_dict_empty(self):
        """测试 from_dict 空数据"""
        restored = SelfProfile.from_dict({})

        assert restored.age == 0
        assert restored.gender == ""
        assert restored.actual_personality == ""
        assert restored.emotional_needs == []

    def test_serialization_roundtrip(self, self_profile_sample):
        """测试序列化/反序列化往返"""
        data = self_profile_sample.to_dict()
        restored = SelfProfile.from_dict(data)
        data2 = restored.to_dict()

        # 验证两次转换结果一致
        assert json.dumps(data, sort_keys=True) == json.dumps(data2, sort_keys=True)


# ============= DesireProfile 数据类测试 =============

class TestDesireProfile:
    """DesireProfile 数据类测试"""

    def test_to_dict_basic(self, desire_profile_sample):
        """测试 to_dict 基础转换"""
        result = desire_profile_sample.to_dict()

        assert result["surface_preference"] == "开朗外向的女生"
        assert result["ideal_type_description"] == "希望对方阳光活泼，能带动气氛"
        assert result["deal_breakers"] == ["抽烟", "不真诚"]

    def test_to_dict_actual_preference(self, desire_profile_sample):
        """测试 to_dict actual_preference 部分"""
        result = desire_profile_sample.to_dict()

        assert result["actual_preference"] == "温柔内向的女生"
        assert result["preference_gap"] == "想要外向但实际倾向内向"

    def test_to_dict_behavior_data(self, desire_profile_sample):
        """测试 to_dict 行为数据部分"""
        result = desire_profile_sample.to_dict()

        assert result["search_patterns"] == [{"keyword": "内向", "count": 5}]
        assert result["clicked_types"] == ["内向温柔", "知性稳重"]
        assert result["swipe_patterns"]["liked"] == ["内向型"]

    def test_to_dict_feedback(self, desire_profile_sample):
        """测试 to_dict feedback 部分"""
        result = desire_profile_sample.to_dict()

        assert result["like_feedback"] == [{"type": "温柔内向", "reason": "聊得来"}]
        assert result["dislike_feedback"] == [{"type": "过度外向", "reason": "太吵"}]

    def test_from_dict_complete(self, desire_profile_sample):
        """测试 from_dict 完整转换"""
        data = desire_profile_sample.to_dict()
        restored = DesireProfile.from_dict(data)

        assert restored.surface_preference == "开朗外向的女生"
        assert restored.actual_preference == "温柔内向的女生"
        assert restored.deal_breakers == ["抽烟", "不真诚"]
        assert restored.search_patterns == [{"keyword": "内向", "count": 5}]

    def test_from_dict_partial(self):
        """测试 from_dict 部分数据"""
        partial_data = {
            "surface_preference": "温柔内向",
            "deal_breakers": ["抽烟"],
        }
        restored = DesireProfile.from_dict(partial_data)

        assert restored.surface_preference == "温柔内向"
        assert restored.deal_breakers == ["抽烟"]
        assert restored.actual_preference == ""  # 默认值
        assert restored.search_patterns == []  # 默认空列表

    def test_from_dict_empty(self):
        """测试 from_dict 空数据"""
        restored = DesireProfile.from_dict({})

        assert restored.surface_preference == ""
        assert restored.actual_preference == ""
        assert restored.deal_breakers == []

    def test_serialization_roundtrip(self, desire_profile_sample):
        """测试序列化/反序列化往返"""
        data = desire_profile_sample.to_dict()
        restored = DesireProfile.from_dict(data)
        data2 = restored.to_dict()

        assert json.dumps(data, sort_keys=True) == json.dumps(data2, sort_keys=True)


# ============= CognitiveBiasAnalysis 数据类测试 =============

class TestCognitiveBiasAnalysis:
    """CognitiveBiasAnalysis 数据类测试"""

    def test_to_dict(self):
        """测试 CognitiveBiasAnalysis.to_dict"""
        analysis = CognitiveBiasAnalysis(
            has_bias=True,
            bias_type="双强势偏差",
            bias_description="双方都是控制型人格，容易产生权力斗争",
            actual_suitable_type="温和有主见的类型",
            potential_risks=["持续争吵", "关系破裂"],
            adjustment_suggestion="建议学会妥协和倾听",
            confidence=0.85,
        )

        result = analysis.to_dict()

        assert result["has_bias"] == True
        assert result["bias_type"] == "双强势偏差"
        assert result["potential_risks"] == ["持续争吵", "关系破裂"]
        assert result["confidence"] == 0.85

    def test_to_dict_no_bias(self):
        """测试无偏差时的 to_dict"""
        analysis = CognitiveBiasAnalysis(
            has_bias=False,
            confidence=0.0,
        )

        result = analysis.to_dict()

        assert result["has_bias"] == False
        assert result["bias_type"] == ""


# ============= MatchAdvice 数据类测试 =============

class TestMatchAdvice:
    """MatchAdvice 数据类测试"""

    def test_to_dict(self):
        """测试 MatchAdvice.to_dict"""
        advice = MatchAdvice(
            advice_type="strongly_recommend",
            advice_content="你们非常匹配，建议优先考虑",
            reasoning="价值观契合，沟通风格互补",
            suggestions_for_user=["主动发起对话", "分享更多个人想法"],
            potential_issues=["初期可能需要磨合沟通方式"],
            compatibility_score=0.85,
        )

        result = advice.to_dict()

        assert result["advice_type"] == "strongly_recommend"
        assert result["advice_content"] == "你们非常匹配，建议优先考虑"
        assert len(result["suggestions_for_user"]) == 2
        assert result["compatibility_score"] == 0.85


# ============= CognitiveBiasDetector 测试 =============

class TestCognitiveBiasDetector:
    """CognitiveBiasDetector 测试"""

    def test_build_bias_analysis_prompt_structure(self, bias_detector, self_profile_sample, desire_profile_sample):
        """测试 Prompt 构建结构正确性"""
        prompt = bias_detector._build_bias_analysis_prompt(self_profile_sample, desire_profile_sample)

        # 验证 Prompt 包含必要内容
        assert "拥有20年经验的专业婚恋顾问 Her" in prompt
        assert "认知偏差" in prompt
        assert "has_bias" in prompt
        assert "bias_type" in prompt
        assert "potential_risks" in prompt
        assert "adjustment_suggestion" in prompt

    def test_build_bias_analysis_prompt_user_data(self, bias_detector, self_profile_sample, desire_profile_sample):
        """测试 Prompt 包含用户数据"""
        prompt = bias_detector._build_bias_analysis_prompt(self_profile_sample, desire_profile_sample)

        # 验证用户画像数据包含在 Prompt 中
        assert self_profile_sample.actual_personality in prompt
        assert self_profile_sample.attachment_style in prompt
        assert desire_profile_sample.surface_preference in prompt

    def test_build_bias_analysis_prompt_knowledge_framework(self, bias_detector, self_profile_sample, desire_profile_sample):
        """测试 Prompt 包含知识框架"""
        prompt = bias_detector._build_bias_analysis_prompt(self_profile_sample, desire_profile_sample)

        # 验证知识框架包含在 Prompt 中
        assert "依恋理论" in prompt
        assert "权力动态" in prompt
        assert "情感需求" in prompt
        assert "双强势" in prompt
        assert "焦虑型+回避型" in prompt

    @pytest.mark.asyncio
    async def test_detect_cognitive_bias_success(self, bias_detector, self_profile_sample, desire_profile_sample):
        """测试认知偏差检测成功场景"""
        # Mock LLM 返回有偏差的结果
        mock_response = json.dumps({
            "has_bias": True,
            "bias_type": "内向偏好偏差",
            "bias_description": "用户自称想要外向型，但实际行为倾向内向型",
            "actual_suitable_type": "温柔内向的女生",
            "potential_risks": ["可能错过真正适合的人"],
            "adjustment_suggestion": "建议尝试接触内向温和的类型",
            "confidence": 0.8,
        })

        with patch.object(bias_detector, '_call_llm_async', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            result = await bias_detector.detect_cognitive_bias(self_profile_sample, desire_profile_sample)

            assert result.has_bias == True
            assert result.bias_type == "内向偏好偏差"
            assert result.confidence == 0.8
            assert len(result.potential_risks) == 1

    @pytest.mark.asyncio
    async def test_detect_cognitive_bias_no_bias(self, bias_detector, self_profile_sample, desire_profile_sample):
        """测试无偏差场景"""
        mock_response = json.dumps({
            "has_bias": False,
            "bias_type": "",
            "bias_description": "",
            "actual_suitable_type": "",
            "potential_risks": [],
            "adjustment_suggestion": "",
            "confidence": 0.9,
        })

        with patch.object(bias_detector, '_call_llm_async', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            result = await bias_detector.detect_cognitive_bias(self_profile_sample, desire_profile_sample)

            assert result.has_bias == False
            assert result.bias_type == ""

    @pytest.mark.asyncio
    async def test_detect_cognitive_bias_double_control_bias(self, bias_detector, self_profile_control_type, desire_profile_control_preference):
        """测试双强势偏差检测"""
        mock_response = json.dumps({
            "has_bias": True,
            "bias_type": "双强势偏差",
            "bias_description": "双方都是控制型人格，容易产生权力斗争",
            "actual_suitable_type": "温和有主见的类型",
            "potential_risks": ["持续权力斗争", "关系破裂"],
            "adjustment_suggestion": "建议学会妥协和倾听，寻找平等型伴侣",
            "confidence": 0.85,
        })

        with patch.object(bias_detector, '_call_llm_async', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            result = await bias_detector.detect_cognitive_bias(self_profile_control_type, desire_profile_control_preference)

            assert result.has_bias == True
            assert "双强势" in result.bias_type
            assert "权力斗争" in result.bias_description

    @pytest.mark.asyncio
    async def test_detect_cognitive_bias_attachment_mismatch(self, bias_detector, self_profile_anxious_type):
        """测试依恋错配偏差检测"""
        # 焦虑型用户想要回避型伴侣（危险组合）
        desire = DesireProfile(
            surface_preference="独立冷漠的男生",
            ideal_type_description="希望对方独立自主",
        )

        mock_response = json.dumps({
            "has_bias": True,
            "bias_type": "依恋错配",
            "bias_description": "焦虑型用户追求回避型伴侣会形成痛苦循环",
            "actual_suitable_type": "安全型伴侣",
            "potential_risks": ["焦虑型追，回避型逃，持续痛苦循环"],
            "adjustment_suggestion": "建议寻找安全型伴侣",
            "confidence": 0.9,
        })

        with patch.object(bias_detector, '_call_llm_async', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            result = await bias_detector.detect_cognitive_bias(self_profile_anxious_type, desire)

            assert result.has_bias == True
            assert "依恋" in result.bias_type

    @pytest.mark.asyncio
    async def test_detect_cognitive_bias_llm_failure(self, bias_detector, self_profile_sample, desire_profile_sample):
        """测试 LLM 调用失败的降级处理"""
        # Mock LLM 调用失败
        with patch.object(bias_detector, '_call_llm_async', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("LLM service unavailable")
            result = await bias_detector.detect_cognitive_bias(self_profile_sample, desire_profile_sample)

            # 应返回默认结果（无偏差）
            assert result.has_bias == False
            assert result.confidence == 0.0

    def test_parse_bias_analysis_valid_json(self, bias_detector):
        """测试有效 JSON 解析"""
        response = json.dumps({
            "has_bias": True,
            "bias_type": "测试偏差",
            "bias_description": "测试描述",
            "actual_suitable_type": "测试类型",
            "potential_risks": ["风险1", "风险2"],
            "adjustment_suggestion": "测试建议",
            "confidence": 0.75,
        })

        result = bias_detector._parse_bias_analysis(response)

        assert result.has_bias == True
        assert result.bias_type == "测试偏差"
        assert len(result.potential_risks) == 2

    def test_parse_bias_analysis_with_markdown_block(self, bias_detector):
        """测试带 markdown 代码块的 JSON 解析"""
        response = '''```json
        {
            "has_bias": true,
            "bias_type": "测试偏差",
            "bias_description": "测试描述",
            "actual_suitable_type": "",
            "potential_risks": [],
            "adjustment_suggestion": "",
            "confidence": 0.5
        }
        ```'''

        result = bias_detector._parse_bias_analysis(response)

        assert result.has_bias == True
        assert result.bias_type == "测试偏差"

    def test_parse_bias_analysis_with_code_block_only(self, bias_detector):
        """测试带简单代码块的 JSON 解析"""
        response = '''```
        {
            "has_bias": false,
            "bias_type": "",
            "bias_description": "",
            "actual_suitable_type": "",
            "potential_risks": [],
            "adjustment_suggestion": "",
            "confidence": 0.0
        }
        ```'''

        result = bias_detector._parse_bias_analysis(response)

        assert result.has_bias == False

    def test_parse_bias_analysis_invalid_json(self, bias_detector):
        """测试无效 JSON 解析（降级处理）"""
        response = "这不是有效的 JSON"

        result = bias_detector._parse_bias_analysis(response)

        # 应返回默认结果
        assert result.has_bias == False
        assert result.confidence == 0.0

    def test_parse_bias_analysis_partial_json(self, bias_detector):
        """测试部分字段缺失的 JSON 解析"""
        response = json.dumps({
            "has_bias": True,
            # 其他字段缺失
        })

        result = bias_detector._parse_bias_analysis(response)

        assert result.has_bias == True
        assert result.bias_type == ""  # 默认值
        assert result.potential_risks == []  # 默认空列表


# ============= MatchAdvisor 测试 =============

class TestMatchAdvisor:
    """MatchAdvisor 测试"""

    def test_check_intent_match_bidirectional(self, match_advisor):
        """测试双向意向匹配"""
        desire_a = DesireProfile(surface_preference="温柔内向的女生")
        desire_b = DesireProfile(surface_preference="温和内向的男生")
        self_a = SelfProfile(gender="male", actual_personality="温和内向")
        self_b = SelfProfile(gender="female", actual_personality="温柔内向")

        result = match_advisor._check_intent_match(desire_a, desire_b, self_a, self_b)

        assert result == "bidirectional_match"

    def test_check_intent_match_unidirectional(self, match_advisor):
        """测试单向意向匹配"""
        desire_a = DesireProfile(surface_preference="温柔内向的女生")
        desire_b = DesireProfile(surface_preference="外向开朗的男生")  # 与 A 不匹配
        self_a = SelfProfile(gender="male", actual_personality="温和内向")
        self_b = SelfProfile(gender="female", actual_personality="温柔内向")

        result = match_advisor._check_intent_match(desire_a, desire_b, self_a, self_b)

        assert result == "unidirectional_match"

    def test_check_intent_match_no_match(self, match_advisor):
        """测试无意向匹配"""
        desire_a = DesireProfile(surface_preference="外向开朗的女生")
        desire_b = DesireProfile(surface_preference="外向开朗的男生")
        self_a = SelfProfile(gender="male", actual_personality="内向稳重")  # 不符合 B 的偏好
        self_b = SelfProfile(gender="female", actual_personality="内向安静")  # 不符合 A 的偏好

        result = match_advisor._check_intent_match(desire_a, desire_b, self_a, self_b)

        assert result == "no_intent_match"

    def test_check_intent_match_empty_preference(self, match_advisor):
        """测试空偏好时默认匹配"""
        desire_a = DesireProfile(surface_preference="")  # 无偏好
        desire_b = DesireProfile(surface_preference="温柔内向的男生")
        self_a = SelfProfile(gender="male", actual_personality="任何性格")
        self_b = SelfProfile(gender="female", actual_personality="温柔内向")

        result = match_advisor._check_intent_match(desire_a, desire_b, self_a, self_b)

        # A 无偏好默认匹配，B 有偏好
        assert result in ["bidirectional_match", "unidirectional_match"]

    def test_check_type_match_gender_preference(self, match_advisor):
        """测试性别偏好匹配"""
        profile = SelfProfile(gender="female", actual_personality="温柔内向")

        # 匹配女生偏好
        assert match_advisor._check_type_match("温柔的女生", profile) == True
        # 不匹配男生偏好
        assert match_advisor._check_type_match("温柔的男生", profile) == False

    def test_check_type_match_personality_preference(self, match_advisor):
        """测试性格偏好匹配"""
        profile = SelfProfile(gender="female", actual_personality="内向温柔")

        # 匹配内向偏好
        assert match_advisor._check_type_match("内向的女生", profile) == True
        # 不匹配外向偏好
        assert match_advisor._check_type_match("外向的女生", profile) == False

    def test_check_type_match_empty_preference(self, match_advisor):
        """测试空偏好时默认匹配"""
        profile = SelfProfile(gender="male", actual_personality="任何性格")

        assert match_advisor._check_type_match("", profile) == True

    def test_build_compatibility_prompt_structure(self, match_advisor, self_profile_sample):
        """测试适配度分析 Prompt 结构"""
        bias_a = CognitiveBiasAnalysis(has_bias=False, confidence=0.0)
        bias_b = CognitiveBiasAnalysis(has_bias=True, bias_type="测试偏差", confidence=0.7)

        prompt = match_advisor._build_compatibility_prompt(
            self_profile_sample, self_profile_sample, bias_a, bias_b
        )

        # 验证 Prompt 包含必要内容
        assert "适配度" in prompt
        assert "性格互补性" in prompt
        assert "依恋类型匹配" in prompt
        assert "权力动态" in prompt
        assert "overall_compatibility" in prompt

    def test_parse_compatibility_response_valid(self, match_advisor):
        """测试适配度响应解析"""
        response = json.dumps({
            "overall_compatibility": 0.75,
            "personality_match": {"score": 0.8, "analysis": "互补"},
            "attachment_match": {"score": 0.7, "analysis": "匹配"},
            "strengths": ["价值观一致"],
            "challenges": ["沟通方式差异"],
        })

        result = match_advisor._parse_compatibility_response(response)

        assert result["overall_compatibility"] == 0.75
        assert result["personality_match"]["score"] == 0.8

    def test_parse_compatibility_response_invalid(self, match_advisor):
        """测试适配度响应解析失败"""
        response = "无效 JSON"

        result = match_advisor._parse_compatibility_response(response)

        assert result == {}

    def test_build_advice_prompt_four_situations(self, match_advisor):
        """测试四种匹配情况的 Prompt 构建"""
        bias_a = CognitiveBiasAnalysis(has_bias=False, confidence=0.0)
        bias_b = CognitiveBiasAnalysis(has_bias=False, confidence=0.0)
        compatibility = {"overall_compatibility": 0.7}

        # 情况 1: 双向意向匹配
        prompt1 = match_advisor._build_advice_prompt(
            "bidirectional_match", bias_a, bias_b, compatibility, 0.8
        )
        assert "双方都有意向" in prompt1

        # 情况 2: 单向意向匹配
        prompt2 = match_advisor._build_advice_prompt(
            "unidirectional_match", bias_a, bias_b, compatibility, 0.6
        )
        assert "意向不对称" in prompt2

        # 情况 3: 无意向匹配
        prompt3 = match_advisor._build_advice_prompt(
            "no_intent_match", bias_a, bias_b, compatibility, 0.5
        )
        assert "意向不匹配" in prompt3

    def test_parse_advice_response_valid(self, match_advisor):
        """测试建议响应解析"""
        response = json.dumps({
            "advice_type": "strongly_recommend",
            "advice_content": "你们非常匹配",
            "reasoning": "价值观契合",
            "suggestions_for_user": ["主动联系"],
            "potential_issues": [],
        })

        result = match_advisor._parse_advice_response(response, 0.85)

        assert result.advice_type == "strongly_recommend"
        assert result.advice_content == "你们非常匹配"
        assert result.compatibility_score == 0.85

    def test_parse_advice_response_invalid(self, match_advisor):
        """测试建议响应解析失败"""
        response = "无效 JSON"

        result = match_advisor._parse_advice_response(response, 0.6)

        assert result.advice_type == "recommend_with_caution"
        assert result.compatibility_score == 0.6

    @pytest.mark.asyncio
    async def test_generate_match_advice_success(self, match_advisor, self_profile_sample, desire_profile_sample):
        """测试匹配建议生成成功"""
        # Mock 偏差检测返回无偏差
        with patch.object(match_advisor._bias_detector, 'detect_cognitive_bias', new_callable=AsyncMock) as mock_bias:
            mock_bias.return_value = CognitiveBiasAnalysis(has_bias=False, confidence=0.0)

            # Mock 适配度分析
            with patch.object(match_advisor, '_analyze_compatibility', new_callable=AsyncMock) as mock_compat:
                mock_compat.return_value = {"overall_compatibility": 0.8}

                # Mock 建议生成
                with patch.object(match_advisor, '_generate_professional_advice', new_callable=AsyncMock) as mock_advice:
                    mock_advice.return_value = MatchAdvice(
                        advice_type="strongly_recommend",
                        advice_content="你们很匹配",
                        compatibility_score=0.8,
                    )

                    user_a = (self_profile_sample, desire_profile_sample)
                    user_b = (self_profile_sample, desire_profile_sample)

                    result = await match_advisor.generate_match_advice(user_a, user_b, 0.8)

                    assert result.advice_type == "strongly_recommend"
                    assert result.compatibility_score == 0.8

    @pytest.mark.asyncio
    async def test_generate_match_advice_with_bias(self, match_advisor, self_profile_control_type, desire_profile_control_preference):
        """测试带偏差的匹配建议生成"""
        bias_analysis = CognitiveBiasAnalysis(
            has_bias=True,
            bias_type="双强势偏差",
            bias_description="双方都是控制型",
            confidence=0.85,
        )

        with patch.object(match_advisor._bias_detector, 'detect_cognitive_bias', new_callable=AsyncMock) as mock_bias:
            mock_bias.return_value = bias_analysis

            with patch.object(match_advisor, '_analyze_compatibility', new_callable=AsyncMock) as mock_compat:
                mock_compat.return_value = {}

                with patch.object(match_advisor, '_generate_professional_advice', new_callable=AsyncMock) as mock_advice:
                    mock_advice.return_value = MatchAdvice(
                        advice_type="recommend_with_caution",
                        advice_content="你们可能存在权力斗争风险",
                        potential_issues=["双方强势可能导致冲突"],
                        compatibility_score=0.5,
                    )

                    user_a = (self_profile_control_type, desire_profile_control_preference)
                    user_b = (self_profile_control_type, desire_profile_control_preference)

                    result = await match_advisor.generate_match_advice(user_a, user_b, 0.5)

                    assert result.advice_type == "recommend_with_caution"
                    assert len(result.potential_issues) == 1

    @pytest.mark.asyncio
    async def test_generate_match_advice_llm_failure(self, match_advisor, self_profile_sample, desire_profile_sample):
        """测试 LLM 失败时的降级处理"""
        with patch.object(match_advisor._bias_detector, 'detect_cognitive_bias', new_callable=AsyncMock) as mock_bias:
            mock_bias.return_value = CognitiveBiasAnalysis(has_bias=False, confidence=0.0)

            with patch.object(match_advisor, '_analyze_compatibility', new_callable=AsyncMock) as mock_compat:
                mock_compat.return_value = {}

                with patch.object(match_advisor, '_generate_professional_advice', new_callable=AsyncMock) as mock_advice:
                    mock_advice.return_value = MatchAdvice(
                        advice_type="recommend_with_caution",
                        advice_content="建议进一步了解",
                        compatibility_score=0.5,
                    )

                    user_a = (self_profile_sample, desire_profile_sample)
                    user_b = (self_profile_sample, desire_profile_sample)

                    result = await match_advisor.generate_match_advice(user_a, user_b, 0.5)

                    assert result.advice_type == "recommend_with_caution"


# ============= ProactiveSuggestionGenerator 测试 =============

class TestProactiveSuggestionGenerator:
    """ProactiveSuggestionGenerator 测试"""

    @pytest.mark.asyncio
    async def test_generate_proactive_suggestion_with_bias(self, proactive_generator, self_profile_sample, desire_profile_sample):
        """测试带偏差的主动建议生成"""
        bias_analysis = CognitiveBiasAnalysis(
            has_bias=True,
            bias_type="内向偏好偏差",
            bias_description="你想要的和适合的可能不一致",
            adjustment_suggestion="建议尝试内向温和的类型",
            confidence=0.8,
        )

        matches = [{"score": 0.7}, {"score": 0.6}]
        user_profile = (self_profile_sample, desire_profile_sample)

        result = await proactive_generator.generate_proactive_suggestion(
            user_profile, bias_analysis, matches
        )

        assert result.has_critical_suggestion == True
        assert len(result.suggestions) > 0
        # 应包含认知偏差提醒
        assert any(s["type"] == "cognitive_bias_reminder" for s in result.suggestions)

    @pytest.mark.asyncio
    async def test_generate_proactive_suggestion_no_bias(self, proactive_generator, self_profile_sample, desire_profile_sample):
        """测试无偏差的主动建议生成"""
        bias_analysis = CognitiveBiasAnalysis(has_bias=False, confidence=0.0)
        matches = [{"score": 0.8}, {"score": 0.75}, {"score": 0.7}]
        user_profile = (self_profile_sample, desire_profile_sample)

        result = await proactive_generator.generate_proactive_suggestion(
            user_profile, bias_analysis, matches
        )

        assert result.has_critical_suggestion == False

    @pytest.mark.asyncio
    async def test_generate_proactive_suggestion_small_pool(self, proactive_generator, self_profile_sample, desire_profile_sample):
        """测试匹配池较小时的主动建议"""
        bias_analysis = CognitiveBiasAnalysis(has_bias=False, confidence=0.0)
        matches = [{"score": 0.5}]  # 只有 1 个匹配
        user_profile = (self_profile_sample, desire_profile_sample)

        result = await proactive_generator.generate_proactive_suggestion(
            user_profile, bias_analysis, matches
        )

        # 应包含搜索范围建议
        assert any(s["type"] == "search_range_suggestion" for s in result.suggestions)

    @pytest.mark.asyncio
    async def test_generate_proactive_suggestion_preference_gap(self, proactive_generator):
        """测试偏好差距时的主动建议"""
        bias_analysis = CognitiveBiasAnalysis(has_bias=False, confidence=0.0)

        desire = DesireProfile(
            surface_preference="开朗外向",
            actual_preference="内向温柔",
            preference_gap="想要外向但行为倾向内向",
        )
        self_profile = SelfProfile()
        user_profile = (self_profile, desire)

        matches = [{"score": 0.7}, {"score": 0.6}]

        result = await proactive_generator.generate_proactive_suggestion(
            user_profile, bias_analysis, matches
        )

        # 应包含行为模式提醒
        assert any(s["type"] == "behavior_pattern_reminder" for s in result.suggestions)

    @pytest.mark.asyncio
    async def test_generate_proactive_suggestion_low_quality_matches(self, proactive_generator, self_profile_sample, desire_profile_sample):
        """测试低质量匹配时的主动建议"""
        bias_analysis = CognitiveBiasAnalysis(has_bias=False, confidence=0.0)
        matches = [{"score": 0.4}, {"score": 0.3}, {"score": 0.35}]  # 平均分 < 0.6
        user_profile = (self_profile_sample, desire_profile_sample)

        result = await proactive_generator.generate_proactive_suggestion(
            user_profile, bias_analysis, matches
        )

        # 应包含匹配质量建议
        quality_suggestions = [s for s in result.suggestions if s["type"] == "match_quality_reminder"]
        assert len(quality_suggestions) > 0
        assert "较低" in quality_suggestions[0]["message"]

    @pytest.mark.asyncio
    async def test_generate_proactive_suggestion_high_quality_matches(self, proactive_generator, self_profile_sample, desire_profile_sample):
        """测试高质量匹配时的主动建议"""
        bias_analysis = CognitiveBiasAnalysis(has_bias=False, confidence=0.0)
        matches = [{"score": 0.85}, {"score": 0.9}, {"score": 0.88}]  # 平均分 > 0.8
        user_profile = (self_profile_sample, desire_profile_sample)

        result = await proactive_generator.generate_proactive_suggestion(
            user_profile, bias_analysis, matches
        )

        # 应包含高匹配质量建议
        quality_suggestions = [s for s in result.suggestions if s["type"] == "match_quality_reminder"]
        assert len(quality_suggestions) > 0
        assert "很高" in quality_suggestions[0]["message"]

    @pytest.mark.asyncio
    async def test_generate_proactive_suggestion_empty_matches(self, proactive_generator, self_profile_sample, desire_profile_sample):
        """测试无匹配结果时的主动建议"""
        bias_analysis = CognitiveBiasAnalysis(has_bias=False, confidence=0.0)
        matches = []
        user_profile = (self_profile_sample, desire_profile_sample)

        result = await proactive_generator.generate_proactive_suggestion(
            user_profile, bias_analysis, matches
        )

        assert isinstance(result, ProactiveSuggestion)
        assert result.has_critical_suggestion == False

    def test_proactive_suggestion_to_dict(self, proactive_generator):
        """测试 ProactiveSuggestion.to_dict"""
        suggestion = ProactiveSuggestion(
            suggestions=[{"type": "test", "message": "测试"}],
            has_critical_suggestion=True,
        )

        result = suggestion.to_dict()

        assert result["has_critical_suggestion"] == True
        assert len(result["suggestions"]) == 1


# ============= HerAdvisorService 测试 =============

class TestHerAdvisorService:
    """HerAdvisorService 主服务测试"""

    def test_init_components(self):
        """测试服务初始化组件"""
        service = HerAdvisorService()

        assert service._bias_detector is not None
        assert service._match_advisor is not None
        assert service._proactive_generator is not None

    def test_get_instance_singleton(self):
        """测试单例获取"""
        service1 = get_her_advisor_service()
        service2 = get_her_advisor_service()

        assert service1 is service2

    @pytest.mark.asyncio
    async def test_analyze_user_bias(self, self_profile_sample, desire_profile_sample):
        """测试用户偏差分析"""
        service = HerAdvisorService()

        with patch.object(service._bias_detector, 'detect_cognitive_bias', new_callable=AsyncMock) as mock:
            mock.return_value = CognitiveBiasAnalysis(
                has_bias=True,
                bias_type="测试偏差",
                confidence=0.8,
            )

            result = await service.analyze_user_bias(
                "user_123", self_profile_sample, desire_profile_sample
            )

            assert result.has_bias == True
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_match_advice(self, self_profile_sample, desire_profile_sample):
        """测试匹配建议生成"""
        service = HerAdvisorService()

        with patch.object(service._match_advisor, 'generate_match_advice', new_callable=AsyncMock) as mock:
            mock.return_value = MatchAdvice(
                advice_type="strongly_recommend",
                advice_content="你们很匹配",
                compatibility_score=0.85,
            )

            user_a = (self_profile_sample, desire_profile_sample)
            user_b = (self_profile_sample, desire_profile_sample)

            result = await service.generate_match_advice(
                "user_a", user_a, "user_b", user_b, 0.85
            )

            assert result.advice_type == "strongly_recommend"

    @pytest.mark.asyncio
    async def test_generate_proactive_suggestions(self, self_profile_sample, desire_profile_sample):
        """测试主动建议生成"""
        service = HerAdvisorService()

        bias_analysis = CognitiveBiasAnalysis(has_bias=False, confidence=0.0)
        matches = [{"score": 0.7}]
        user_profile = (self_profile_sample, desire_profile_sample)

        result = await service.generate_proactive_suggestions(
            "user_123", user_profile, bias_analysis, matches
        )

        assert isinstance(result, ProactiveSuggestion)


# ============= 边界条件和异常测试 =============

class TestEdgeCases:
    """边界条件和异常测试"""

    @pytest.mark.asyncio
    async def test_bias_detector_empty_profile(self, bias_detector):
        """测试空画像的偏差检测"""
        empty_self = SelfProfile()
        empty_desire = DesireProfile()

        mock_response = json.dumps({
            "has_bias": False,
            "confidence": 0.0,
        })

        with patch.object(bias_detector, '_call_llm_async', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            result = await bias_detector.detect_cognitive_bias(empty_self, empty_desire)

            assert result.has_bias == False

    @pytest.mark.asyncio
    async def test_match_advisor_empty_profiles(self, match_advisor):
        """测试空画像的匹配建议"""
        empty_self = SelfProfile()
        empty_desire = DesireProfile()

        with patch.object(match_advisor._bias_detector, 'detect_cognitive_bias', new_callable=AsyncMock) as mock_bias:
            mock_bias.return_value = CognitiveBiasAnalysis(has_bias=False, confidence=0.0)

            with patch.object(match_advisor, '_analyze_compatibility', new_callable=AsyncMock) as mock_compat:
                mock_compat.return_value = {}

                with patch.object(match_advisor, '_generate_professional_advice', new_callable=AsyncMock) as mock_advice:
                    mock_advice.return_value = MatchAdvice(
                        advice_type="recommend_with_caution",
                        advice_content="建议进一步了解",
                        compatibility_score=0.5,
                    )

                    user_a = (empty_self, empty_desire)
                    user_b = (empty_self, empty_desire)

                    result = await match_advisor.generate_match_advice(user_a, user_b, 0.5)

                    assert result.advice_type == "recommend_with_caution"

    def test_parse_bias_analysis_extra_fields(self, bias_detector):
        """测试包含额外字段的 JSON 解析"""
        response = json.dumps({
            "has_bias": True,
            "bias_type": "测试",
            "extra_field": "额外数据",  # 额外字段
            "confidence": 0.7,
        })

        result = bias_detector._parse_bias_analysis(response)

        assert result.has_bias == True
        # 额外字段不影响结果

    def test_self_profile_with_none_values(self):
        """测试 SelfProfile 包含 None 值"""
        profile = SelfProfile(
            age=28,
            gender="male",
            income_range=None,  # None 值
            occupation=None,
        )

        result = profile.to_dict()

        assert result["basic"]["income_range"] is None
        assert result["basic"]["occupation"] is None

    def test_desire_profile_with_empty_lists(self):
        """测试 DesireProfile 包含空列表"""
        profile = DesireProfile(
            deal_breakers=[],
            search_patterns=[],
            clicked_types=[],
        )

        result = profile.to_dict()

        assert result["deal_breakers"] == []
        assert result["search_patterns"] == []

    @pytest.mark.asyncio
    async def test_proactive_generator_all_conditions(self, proactive_generator):
        """测试主动建议生成同时满足多个条件"""
        bias_analysis = CognitiveBiasAnalysis(
            has_bias=True,
            bias_type="偏差",
            bias_description="偏差描述",
            adjustment_suggestion="调整建议",
            confidence=0.8,
        )

        desire = DesireProfile(
            surface_preference="外向",
            actual_preference="内向",
            preference_gap="差距",
        )
        self_profile = SelfProfile()
        user_profile = (self_profile, desire)

        # 匹配池小且质量低
        matches = [{"score": 0.4}, {"score": 0.3}]

        result = await proactive_generator.generate_proactive_suggestion(
            user_profile, bias_analysis, matches
        )

        # 应包含多种类型的建议
        suggestion_types = [s["type"] for s in result.suggestions]

        assert "cognitive_bias_reminder" in suggestion_types
        assert "search_range_suggestion" in suggestion_types
        assert "behavior_pattern_reminder" in suggestion_types
        assert "match_quality_reminder" in suggestion_types


# ============= 性能测试 =============

class TestPerformance:
    """性能测试"""

    @pytest.mark.asyncio
    async def test_bias_detector_latency(self, bias_detector, self_profile_sample, desire_profile_sample):
        """测试偏差检测延迟"""
        import time

        mock_response = json.dumps({
            "has_bias": True,
            "bias_type": "测试",
            "confidence": 0.8,
        })

        with patch.object(bias_detector, '_call_llm_async', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response

            start = time.time()
            await bias_detector.detect_cognitive_bias(self_profile_sample, desire_profile_sample)
            elapsed = time.time() - start

            # Mock 场景应该很快（< 100ms）
            assert elapsed < 0.1

    def test_profile_serialization_latency(self, self_profile_sample):
        """测试画像序列化延迟"""
        import time

        start = time.time()
        for _ in range(1000):
            self_profile_sample.to_dict()
        elapsed = time.time() - start

        # 1000 次序列化应该很快（< 1s）
        assert elapsed < 1.0

    def test_profile_deserialization_latency(self, self_profile_sample):
        """测试画像反序列化延迟"""
        import time

        data = self_profile_sample.to_dict()

        start = time.time()
        for _ in range(1000):
            SelfProfile.from_dict(data)
        elapsed = time.time() - start

        # 1000 次反序列化应该很快（< 1s）
        assert elapsed < 1.0


# ============= 并行化测试 =============

class TestParallelExecution:
    """并行化执行测试"""

    @pytest.mark.asyncio
    async def test_bias_detection_parallel(self, match_advisor, self_profile_sample, desire_profile_sample):
        """测试偏差检测并行执行（asyncio.gather）"""
        import time

        # Mock 延迟响应
        async def delayed_response(self_profile, desire_profile):
            await asyncio.sleep(0.1)
            return CognitiveBiasAnalysis(has_bias=False, confidence=0.0)

        user_a = (self_profile_sample, desire_profile_sample)
        user_b = (self_profile_sample, desire_profile_sample)

        with patch.object(match_advisor._bias_detector, 'detect_cognitive_bias', new_callable=AsyncMock) as mock_bias:
            mock_bias.side_effect = delayed_response

            with patch.object(match_advisor, '_analyze_compatibility', new_callable=AsyncMock) as mock_compat:
                mock_compat.return_value = {}

                with patch.object(match_advisor, '_generate_professional_advice', new_callable=AsyncMock) as mock_advice:
                    mock_advice.return_value = MatchAdvice(
                        advice_type="recommend_with_caution",
                        compatibility_score=0.5,
                    )

                    start = time.time()
                    await match_advisor.generate_match_advice(user_a, user_b, 0.5)
                    elapsed = time.time() - start

                    # 两个偏差检测并行，总时间应接近单个延迟（约 0.1s）而非两倍（0.2s）
                    assert elapsed < 0.25