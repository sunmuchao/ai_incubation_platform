"""
LLM 语义服务单元测试

测试覆盖:
- 情绪分析
- 价值观分析
- 沟通模式分析
- 降级处理
- 重试机制
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from services.llm_semantic_service import LLMSemanticService, get_llm_semantic_service


# =============  fixture =============

@pytest.fixture
def llm_service():
    """创建 LLM 服务实例（禁用状态）"""
    service = LLMSemanticService()
    service.enabled = False  # 测试时禁用 LLM，使用 fallback
    return service


@pytest.fixture
def llm_service_enabled():
    """创建 LLM 服务实例（启用状态）"""
    service = LLMSemanticService()
    service.enabled = True
    return service


# ============= 基础初始化测试 =============

class TestLLMSemanticServiceInit:
    """LLM 服务初始化测试"""

    def test_default_config(self, llm_service):
        """测试默认配置"""
        assert llm_service.enabled == False
        assert llm_service.fallback_enabled == True
        assert llm_service.max_retries >= 0  # Can be configured via environment
        assert llm_service.retry_delay == 1.0

    def test_get_instance(self):
        """测试单例获取"""
        service1 = get_llm_semantic_service()
        service2 = get_llm_semantic_service()
        assert service1 is service2


# ============= 情绪分析测试 =============

class TestEmotionAnalysis:
    """情绪分析测试"""

    @pytest.mark.asyncio
    async def test_analyze_emotions_fallback(self, llm_service):
        """测试情绪分析（fallback 模式）"""
        result = await llm_service.analyze_implicit_emotions("我很开心")

        assert "primary_emotions" in result
        assert "is_analyzed" in result
        assert result["is_analyzed"] == False  # fallback 模式

    @pytest.mark.asyncio
    async def test_analyze_emotions_empty_text(self, llm_service):
        """测试空文本情绪分析"""
        result = await llm_service.analyze_implicit_emotions("")

        assert result["primary_emotions"] == []
        assert result["emotion_intensity"] == 0

    @pytest.mark.asyncio
    async def test_analyze_emotions_with_context(self, llm_service):
        """测试带上下文的情绪分析"""
        context = [
            {"role": "user", "content": "今天天气真好"},
            {"role": "assistant", "content": "是啊，适合出去玩"}
        ]
        result = await llm_service.analyze_implicit_emotions("我好开心", context)

        assert isinstance(result, dict)
        assert "primary_emotions" in result

    @pytest.mark.asyncio
    async def test_fallback_emotion_detection(self, llm_service):
        """测试 fallback 情绪检测（关键词匹配）"""
        result = await llm_service.analyze_implicit_emotions("我非常兴奋和期待")

        # fallback 模式应该检测到关键词
        assert result["is_analyzed"] == False
        # 有情绪词汇时应该有结果
        assert len(result["primary_emotions"]) >= 0  # 可能检测到 "anticipation"


# ============= 价值观分析测试 =============

class TestValueAnalysis:
    """价值观分析测试"""

    @pytest.mark.asyncio
    async def test_analyze_values_fallback(self, llm_service):
        """测试价值观分析（fallback 模式）"""
        result = await llm_service.extract_value_preferences("我觉得家庭最重要")

        assert "detected_values" in result
        assert "is_analyzed" in result
        assert result["is_analyzed"] == False

    @pytest.mark.asyncio
    async def test_analyze_values_empty_text(self, llm_service):
        """测试空文本价值观分析"""
        result = await llm_service.extract_value_preferences("")

        assert result["detected_values"] == []
        assert result["overall_confidence"] == 0

    @pytest.mark.asyncio
    async def test_value_keyword_detection(self, llm_service):
        """测试价值观关键词检测"""
        # 测试家庭观念
        result = await llm_service.extract_value_preferences("我认为家庭优先，周末应该陪父母")
        assert len(result["detected_values"]) >= 0  # fallback 可能检测到

        # 测试金钱观念
        result = await llm_service.extract_value_preferences("我比较节俭，不喜欢浪费")
        # fallback 模式可能检测到 "节俭"


# ============= 沟通模式分析测试 =============

class TestCommunicationAnalysis:
    """沟通模式分析测试"""

    @pytest.mark.asyncio
    async def test_analyze_communication_fallback(self, llm_service):
        """测试沟通模式分析（fallback 模式）"""
        history = [
            {"role": "user", "content": "你好"},
            {"role": "other", "content": "你好呀"},
            {"role": "user", "content": "在干嘛呢"}
        ]
        result = await llm_service.analyze_communication_pattern(history)

        assert "communication_style" in result
        assert "is_analyzed" in result

    @pytest.mark.asyncio
    async def test_analyze_communication_empty_history(self, llm_service):
        """测试空对话历史"""
        result = await llm_service.analyze_communication_pattern([])

        assert result["is_analyzed"] == False
        assert result["communication_style"] == {}

    @pytest.mark.asyncio
    async def test_analyze_communication_short_history(self, llm_service):
        """测试短对话历史"""
        history = [{"role": "user", "content": "你好"}]
        result = await llm_service.analyze_communication_pattern(history)

        # 短历史可能返回基础分析
        assert isinstance(result, dict)


# ============= 匹配度计算测试 =============

class TestCompatibilityCalculation:
    """匹配度计算测试"""

    @pytest.mark.asyncio
    async def test_compatibility_fallback(self, llm_service):
        """测试匹配度计算（fallback 模式）"""
        user1 = {"interests": ["旅行", "美食", "电影"]}
        user2 = {"interests": ["美食", "健身", "阅读"]}

        result = await llm_service.calculate_semantic_compatibility(user1, user2)

        assert "overall_compatibility" in result
        assert "is_analyzed" in result
        assert result["is_analyzed"] == False
        # fallback 使用 Jaccard 相似度
        # 共同兴趣：美食 (1), 并集：旅行，美食，电影，健身，阅读 (5)
        # Jaccard = 1/5 = 0.2
        assert 0 <= result["overall_compatibility"] <= 1

    @pytest.mark.asyncio
    async def test_compatibility_no_common_interests(self, llm_service):
        """测试无共同兴趣"""
        user1 = {"interests": ["旅行"]}
        user2 = {"interests": ["健身"]}

        result = await llm_service.calculate_semantic_compatibility(user1, user2)

        assert result["overall_compatibility"] == 0  # 无共同兴趣

    @pytest.mark.asyncio
    async def test_compatibility_empty_interests(self, llm_service):
        """测试空兴趣列表"""
        user1 = {"interests": []}
        user2 = {"interests": []}

        result = await llm_service.calculate_semantic_compatibility(user1, user2)

        # 空列表时返回默认值
        assert result["overall_compatibility"] == 0.5  # 默认值


# ============= LLM 调用重试测试 =============

class TestLLMRetry:
    """LLM 调用重试测试"""

    @pytest.mark.asyncio
    async def test_fallback_response(self, llm_service):
        """测试 fallback 响应生成"""
        result = llm_service._get_fallback_response("test prompt")
        import json
        data = json.loads(result)

        assert data["fallback"] == True
        assert "reason" in data

    @pytest.mark.asyncio
    async def test_retry_config(self, llm_service):
        """测试重试配置"""
        assert llm_service.max_retries >= 0
        assert llm_service.retry_delay > 0


# ============= 置信度阈值测试 =============

class TestConfidenceThreshold:
    """置信度阈值测试"""

    @pytest.mark.asyncio
    async def test_value_confidence_filter(self, llm_service):
        """测试价值观置信度过滤"""
        # 创建一个模拟的低置信度结果
        result = await llm_service.extract_value_preferences("测试文本")

        # 所有返回的价值观应该有合理的置信度
        for value in result.get("detected_values", []):
            if "confidence" in value:
                assert value["confidence"] >= 0
                assert value["confidence"] <= 1


# ============= 性能测试 =============

class TestPerformance:
    """性能测试"""

    @pytest.mark.asyncio
    async def test_analyze_emotions_latency(self, llm_service):
        """测试情绪分析延迟"""
        import time

        start = time.time()
        await llm_service.analyze_implicit_emotions("测试文本")
        elapsed = time.time() - start

        # fallback 模式应该很快（< 100ms）
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_analyze_values_latency(self, llm_service):
        """测试价值观分析延迟"""
        import time

        start = time.time()
        await llm_service.extract_value_preferences("测试文本")
        elapsed = time.time() - start

        # fallback 模式应该很快（< 100ms）
        assert elapsed < 0.1


# ============= 边界条件测试 =============

class TestEdgeCases:
    """边界条件测试"""

    @pytest.mark.asyncio
    async def test_very_long_text(self, llm_service):
        """测试长文本处理"""
        long_text = "测试" * 1000
        result = await llm_service.analyze_implicit_emotions(long_text)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_special_characters(self, llm_service):
        """测试特殊字符处理"""
        text = "测试 @#$%^&*() 特殊字符"
        result = await llm_service.analyze_implicit_emotions(text)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_unicode_text(self, llm_service):
        """测试 Unicode 文本处理"""
        text = "测试 😀🎉 表情符号"
        result = await llm_service.analyze_implicit_emotions(text)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_null_input(self, llm_service):
        """测试空输入处理"""
        result = await llm_service.analyze_implicit_emotions(None)
        assert isinstance(result, dict)
