"""
安全风控 AI 服务单元测试
测试覆盖：内容安全检测、用户风险评估、异常行为检测
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import uuid

from services.safety_ai_service import (
    SafetyAIService, RiskType, RiskLevel,
    HARASSMENT_KEYWORDS, SCAM_KEYWORDS, INAPPROPRIATE_KEYWORDS
)
from db.models import UserDB, ConversationDB, BehaviorEventDB, ChatMessageDB


class TestSafetyAIService:
    """安全风控 AI 服务测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        session = MagicMock()
        session.add.return_value = None
        session.commit.return_value = None
        session.refresh.return_value = None
        return session

    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        return SafetyAIService(mock_db)

    def test_service_initialization(self, service, mock_db):
        """测试服务初始化"""
        assert service is not None
        assert service.db == mock_db
        assert hasattr(service, 'harassment_pattern')
        assert hasattr(service, 'scam_pattern')
        assert hasattr(service, 'inappropriate_pattern')

    # ==================== 内容安全检测 ====================

    def test_check_content_safety_clean_content(self, service, mock_db):
        """测试检查内容安全 - 干净内容"""
        # Arrange
        mock_db.query.return_value.filter.return_value.count.return_value = 0

        # Act
        result = service.check_content_safety(
            content="你好，很高兴认识你",
            sender_id="user_001"
        )

        # Assert
        assert result["is_safe"] == True
        assert result["risk_level"] == RiskLevel.LOW
        assert result["risk_score"] == 0
        assert result["risk_types"] == []
        assert result["action_suggestion"] == "none"

    def test_check_content_safety_harassment_detected(self, service, mock_db):
        """测试检查内容安全 - 检测到骚扰"""
        # Arrange
        mock_db.query.return_value.filter.return_value.count.return_value = 0

        # Act
        result = service.check_content_safety(
            content="约吗？今晚开房",
            sender_id="user_001"
        )

        # Assert
        assert result["is_safe"] == False
        assert result["risk_level"] in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert RiskType.HARASSMENT in result["risk_types"]

    def test_check_content_safety_scam_detected(self, service, mock_db):
        """测试检查内容安全 - 检测到诈骗"""
        # Arrange
        mock_db.query.return_value.filter.return_value.count.return_value = 0

        # Act
        result = service.check_content_safety(
            content="我最近有个投资理财的好项目，回报率很高，你要不要试试？需要转账给我",
            sender_id="user_001"
        )

        # Assert
        assert result["is_safe"] == False
        assert RiskType.SCAM in result["risk_types"]

    def test_check_content_safety_inappropriate_content(self, service, mock_db):
        """测试检查内容安全 - 检测到不当内容"""
        # Arrange
        mock_db.query.return_value.filter.return_value.count.return_value = 0

        # Act
        result = service.check_content_safety(
            content="这里有色情淫秽内容，还有暴力杀人的视频",
            sender_id="user_001"
        )

        # Assert
        assert result["is_safe"] == False
        assert RiskType.INAPPROPRIATE_CONTENT in result["risk_types"]

    def test_check_content_safety_spam_detected(self, service, mock_db):
        """测试检查内容安全 - 检测到垃圾信息"""
        # Arrange
        mock_db.query.return_value.filter.return_value.count.return_value = 0

        # Act
        result = service.check_content_safety(
            content="加 V 信：abc123456 获取更多资源【点击链接】http://example.com",
            sender_id="user_001"
        )

        # Assert
        assert result["is_safe"] == False
        assert RiskType.SPAM in result["risk_types"]

    def test_check_content_safety_with_context_harassment(self, service, mock_db):
        """测试检查内容安全 - 上下文分析检测到持续性骚扰"""
        # Arrange
        mock_db.query.return_value.filter.return_value.count.return_value = 0

        context_messages = [
            {"sender_id": "user_001", "content": "为什么不回我消息？"},
            {"sender_id": "user_001", "content": "别不理我，马上回复我"},
            {"sender_id": "user_002", "content": "在忙"},
            {"sender_id": "user_001", "content": "你必须回复我！"},
        ]

        # Act
        result = service.check_content_safety(
            content="为什么不回我？",
            sender_id="user_001",
            context_messages=context_messages
        )

        # Assert
        assert "context_analysis" in result["details"]
        context = result["details"]["context_analysis"]
        assert context["pattern"] in ["persistent_harassment", "spamming", "normal"]

    def test_check_content_safety_high_risk_sender(self, mock_db):
        """测试检查内容安全 - 高风险发送者"""
        # Arrange
        service = SafetyAIService(mock_db)
        mock_db.query.return_value.filter.return_value.count.return_value = 10  # 多次违规

        # Act
        result = service.check_content_safety(
            content="有些可疑的内容",
            sender_id="user_high_risk"
        )

        # Assert
        assert result["details"]["sender_risk"]["violation_count"] == 10
        assert result["details"]["sender_risk"]["risk_level"] == RiskLevel.HIGH

    def test_keyword_detection_harassment(self, service):
        """测试关键词检测 - 骚扰"""
        # Act
        result = service._keyword_detection("约吗？开房睡觉")

        # Assert
        assert result[RiskType.HARASSMENT]["detected"] == True
        assert result[RiskType.HARASSMENT]["count"] > 0

    def test_keyword_detection_scam(self, service):
        """测试关键词检测 - 诈骗"""
        # Act
        result = service._keyword_detection("转账汇款借钱投资")

        # Assert
        assert result[RiskType.SCAM]["detected"] == True
        assert result[RiskType.SCAM]["count"] > 0

    def test_keyword_detection_inappropriate(self, service):
        """测试关键词检测 - 不当内容"""
        # Act
        result = service._keyword_detection("色情淫秽暴力")

        # Assert
        assert result[RiskType.INAPPROPRIATE_CONTENT]["detected"] == True
        assert result[RiskType.INAPPROPRIATE_CONTENT]["count"] > 0

    def test_keyword_detection_clean(self, service):
        """测试关键词检测 - 干净内容"""
        # Act
        result = service._keyword_detection("今天天气真好")

        # Assert
        assert result[RiskType.HARASSMENT]["detected"] == False
        assert result[RiskType.SCAM]["detected"] == False
        assert result[RiskType.INAPPROPRIATE_CONTENT]["detected"] == False

    def test_pattern_detection_spam(self, service):
        """测试模式检测 - 垃圾信息"""
        # Act
        result = service._pattern_detection("加 V 信：abc123 http://example.com 12345678901")

        # Assert
        assert result[RiskType.SPAM]["detected"] == True
        assert result[RiskType.SPAM]["count"] > 0

    def test_pattern_detection_clean(self, service):
        """测试模式检测 - 干净内容"""
        # Act
        result = service._pattern_detection("正常聊天内容")

        # Assert
        assert result[RiskType.SPAM]["detected"] == False

    def test_context_analysis_insufficient_messages(self, service):
        """测试上下文分析 - 消息不足"""
        # Arrange
        messages = [
            {"sender_id": "user_001", "content": "你好"},
        ]

        # Act
        result = service._context_analysis(messages, "user_001")

        # Assert
        assert result["risk_score"] == 0
        assert result["pattern"] == "normal"

    def test_context_analysis_high_frequency(self, service):
        """测试上下文分析 - 高频率消息"""
        # Arrange
        messages = [
            {"sender_id": "user_001", "content": "在吗"},
            {"sender_id": "user_001", "content": "回复我"},
            {"sender_id": "user_001", "content": "别不理我"},
            {"sender_id": "user_001", "content": "看到消息"},
            {"sender_id": "user_002", "content": "忙"},
        ]

        # Act
        result = service._context_analysis(messages, "user_001")

        # Assert
        assert result["sender_message_count"] == 4
        assert result["message_count"] == 5

    def test_context_analysis_negative_content(self, service):
        """测试上下文分析 - 负面内容"""
        # Arrange
        messages = [
            {"sender_id": "user_001", "content": "约吗"},
            {"sender_id": "user_001", "content": "开房"},
            {"sender_id": "user_001", "content": "睡觉"},
            {"sender_id": "user_002", "content": "不要"},
        ]

        # Act
        result = service._context_analysis(messages, "user_001")

        # Assert
        assert result["negative_ratio"] > 0.3

    def test_get_sender_risk_profile_no_violations(self, service, mock_db):
        """测试获取发送者风险画像 - 无违规"""
        # Arrange
        mock_db.query.return_value.filter.return_value.count.return_value = 0

        # Act
        result = service._get_sender_risk_profile("user_clean")

        # Assert
        assert result["violation_count"] == 0
        assert result["base_risk_score"] == 0
        assert result["risk_level"] == RiskLevel.LOW

    def test_get_sender_risk_profile_high_violations(self, service, mock_db):
        """测试获取发送者风险画像 - 多次违规"""
        # Arrange
        mock_db.query.return_value.filter.return_value.count.return_value = 5

        # Act
        result = service._get_sender_risk_profile("user_risky")

        # Assert
        assert result["violation_count"] == 5
        assert result["base_risk_score"] == 50
        assert result["risk_level"] == RiskLevel.HIGH

    def test_calculate_risk_score_low(self, service):
        """测试计算风险分数 - 低风险"""
        # Arrange
        keyword_results = {
            RiskType.HARASSMENT: {"detected": False, "count": 0},
            RiskType.SCAM: {"detected": False, "count": 0},
            RiskType.INAPPROPRIATE_CONTENT: {"detected": False, "count": 0},
        }
        pattern_results = {RiskType.SPAM: {"detected": False, "count": 0}}
        sender_risk = {"base_risk_score": 0}

        # Act
        score = service._calculate_risk_score(keyword_results, pattern_results, sender_risk)

        # Assert
        assert score == 0

    def test_calculate_risk_score_high(self, service):
        """测试计算风险分数 - 高风险"""
        # Arrange
        keyword_results = {
            RiskType.HARASSMENT: {"detected": True, "count": 5},
            RiskType.SCAM: {"detected": False, "count": 0},
            RiskType.INAPPROPRIATE_CONTENT: {"detected": False, "count": 0},
        }
        pattern_results = {RiskType.SPAM: {"detected": False, "count": 0}}
        sender_risk = {"base_risk_score": 50}

        # Act
        score = service._calculate_risk_score(keyword_results, pattern_results, sender_risk)

        # Assert
        assert score > 50  # 50 + 5*15 = 125, capped at 100

    def test_get_risk_level_critical(self, service):
        """测试获取风险等级 - 严重"""
        assert service._get_risk_level(90) == RiskLevel.CRITICAL
        assert service._get_risk_level(80) == RiskLevel.CRITICAL

    def test_get_risk_level_high(self, service):
        """测试获取风险等级 - 高"""
        assert service._get_risk_level(70) == RiskLevel.HIGH
        assert service._get_risk_level(60) == RiskLevel.HIGH

    def test_get_risk_level_medium(self, service):
        """测试获取风险等级 - 中"""
        assert service._get_risk_level(50) == RiskLevel.MEDIUM
        assert service._get_risk_level(30) == RiskLevel.MEDIUM

    def test_get_risk_level_low(self, service):
        """测试获取风险等级 - 低"""
        assert service._get_risk_level(20) == RiskLevel.LOW
        assert service._get_risk_level(0) == RiskLevel.LOW

    def test_get_risk_types_detected(self, service):
        """测试获取风险类型"""
        # Arrange
        keyword_results = {
            RiskType.HARASSMENT: {"detected": True},
            RiskType.SCAM: {"detected": False},
            RiskType.INAPPROPRIATE_CONTENT: {"detected": True},
        }
        pattern_results = {RiskType.SPAM: {"detected": True}}

        # Act
        result = service._get_risk_types(keyword_results, pattern_results)

        # Assert
        assert RiskType.HARASSMENT in result
        assert RiskType.INAPPROPRIATE_CONTENT in result
        assert RiskType.SPAM in result

    def test_get_action_suggestion_critical(self, service):
        """测试获取处置建议 - 严重"""
        result = service._get_action_suggestion(RiskLevel.CRITICAL, {"violation_count": 0})
        assert result == "block_user_and_report"

    def test_get_action_suggestion_high_repeat(self, service):
        """测试获取处置建议 - 高风险且累犯"""
        result = service._get_action_suggestion(RiskLevel.HIGH, {"violation_count": 5})
        assert result == "temporary_ban"

    def test_get_action_suggestion_high_first(self, service):
        """测试获取处置建议 - 高风险初犯"""
        result = service._get_action_suggestion(RiskLevel.HIGH, {"violation_count": 0})
        assert result == "strong_warning"

    def test_get_action_suggestion_medium(self, service):
        """测试获取处置建议 - 中风险"""
        result = service._get_action_suggestion(RiskLevel.MEDIUM, {"violation_count": 0})
        assert result == "warning"

    def test_get_action_suggestion_low(self, service):
        """测试获取处置建议 - 低风险"""
        result = service._get_action_suggestion(RiskLevel.LOW, {"violation_count": 0})
        assert result == "none"

    def test_log_risk_content_success(self, service, mock_db):
        """测试记录风险内容成功"""
        # Act
        service._log_risk_content(
            sender_id="user_001",
            content="违规内容",
            risk_level=RiskLevel.HIGH,
            risk_types=[RiskType.HARASSMENT]
        )

        # Assert
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    def test_log_risk_content_error(self, service, mock_db):
        """测试记录风险内容出错"""
        # Arrange
        mock_db.commit.side_effect = Exception("DB Error")

        # Act
        service._log_risk_content(
            sender_id="user_001",
            content="违规内容",
            risk_level=RiskLevel.HIGH,
            risk_types=[RiskType.HARASSMENT]
        )

        # Assert
        mock_db.rollback.assert_called()

    # ==================== 用户风险评估 ====================

    def test_assess_user_risk_success(self, mock_db):
        """测试用户风险评估成功"""
        # Arrange
        service = SafetyAIService(mock_db)

        mock_user = MagicMock()
        mock_user.avatar_url = "avatar.jpg"
        mock_user.bio = "这是一个完整的个人简介，超过 20 个字"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        mock_db.query.return_value.filter.return_value.all.return_value = []

        # Mock count for swipe detection
        mock_db.query.return_value.filter.return_value.count.return_value = 10

        # Mock messages for message detection
        mock_messages = [MagicMock(receiver_id="user_a"), MagicMock(receiver_id="user_b")]
        mock_db.query.return_value.filter.return_value.all.side_effect = [[], mock_messages]

        # Act
        result = service.assess_user_risk("user_001")

        # Assert
        assert "user_id" in result
        assert "risk_score" in result
        assert "risk_level" in result
        assert "violation_count" in result
        assert "abnormal_behaviors" in result
        assert "profile_authenticity" in result
        assert "recommendations" in result

    def test_assess_user_risk_not_found(self, service, mock_db):
        """测试用户风险评估 - 用户不存在"""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Act
        result = service.assess_user_risk("nonexistent_user")

        # Assert
        assert "error" in result
        assert result["error"] == "User not found"

    def test_detect_abnormal_behaviors_normal(self, service, mock_db):
        """测试检测异常行为 - 正常"""
        # Arrange
        mock_db.query.return_value.filter.return_value.count.return_value = 10
        mock_db.query.return_value.filter.return_value.all.return_value = [
            MagicMock(receiver_id="user_a"),
            MagicMock(receiver_id="user_b"),
        ]

        # Act
        result = service._detect_abnormal_behaviors("user_001")

        # Assert
        assert result["abnormal_swipe"] == False
        assert result["abnormal_messaging"] == False

    def test_detect_abnormal_behaviors_swipe_spam(self, service, mock_db):
        """测试检测异常行为 - 滑动 spam"""
        # Arrange
        mock_db.query.return_value.filter.return_value.count.return_value = 100

        # Act
        result = service._detect_abnormal_behaviors("user_001")

        # Assert
        assert result["abnormal_swipe"] == True
        assert result["swipe_count_1h"] == 100

    def test_detect_abnormal_behaviors_message_spam(self, service, mock_db):
        """测试检测异常行为 - 消息 spam"""
        # Arrange
        mock_db.query.return_value.filter.return_value.count.return_value = 10
        mock_messages = [MagicMock(receiver_id=f"user_{i}") for i in range(30)]
        mock_db.query.return_value.filter.return_value.all.return_value = mock_messages

        # Act
        result = service._detect_abnormal_behaviors("user_001")

        # Assert
        assert result["abnormal_messaging"] == True
        assert result["message_receivers_1h"] == 30

    def test_check_profile_authenticity_complete(self, service):
        """测试检查资料真实性 - 完整"""
        # Arrange
        user = MagicMock()
        user.avatar_url = "avatar.jpg"
        user.bio = "这是一个完整的个人简介，超过 20 个字"

        # Act
        result = service._check_profile_authenticity(user)

        # Assert
        assert result["score"] == 100
        assert result["issues"] == []
        assert result["is_suspicious"] == False

    def test_check_profile_authenticity_no_avatar(self, service):
        """测试检查资料真实性 - 无头像"""
        # Arrange
        user = MagicMock()
        user.avatar_url = None
        user.bio = "这是一个完整的个人简介，超过 20 个字"

        # Act
        result = service._check_profile_authenticity(user)

        # Assert
        assert result["score"] == 80  # 扣 20 分
        assert "no_avatar" in result["issues"]

    def test_check_profile_authenticity_incomplete_bio(self, service):
        """测试检查资料真实性 - 简介不完整"""
        # Arrange
        user = MagicMock()
        user.avatar_url = "avatar.jpg"
        user.bio = "短简介"

        # Act
        result = service._check_profile_authenticity(user)

        # Assert
        assert result["score"] == 85  # 扣 15 分
        assert "incomplete_bio" in result["issues"]

    def test_check_profile_authenticity_suspicious(self, service):
        """测试检查资料真实性 - 可疑"""
        # Arrange
        user = MagicMock()
        user.avatar_url = None
        user.bio = "短"

        # Act
        result = service._check_profile_authenticity(user)

        # Assert
        assert result["score"] == 65  # 100 - 20 - 15 = 65
        assert "no_avatar" in result["issues"]
        assert "incomplete_bio" in result["issues"]

    def test_calculate_user_risk_score_low(self, service):
        """测试计算用户风险分数 - 低"""
        # Arrange
        abnormal_behaviors = {"abnormal_swipe": False, "abnormal_messaging": False}
        profile_authenticity = {"is_suspicious": False}

        # Act
        score = service._calculate_user_risk_score(0, abnormal_behaviors, profile_authenticity)

        # Assert
        assert score == 0

    def test_calculate_user_risk_score_high(self, service):
        """测试计算用户风险分数 - 高"""
        # Arrange
        abnormal_behaviors = {"abnormal_swipe": True, "abnormal_messaging": True}
        profile_authenticity = {"is_suspicious": True}

        # Act
        score = service._calculate_user_risk_score(10, abnormal_behaviors, profile_authenticity)

        # Assert
        assert score >= 90  # 50 + 15 + 20 + 25 = 110, capped at 100

    def test_get_user_risk_recommendations_high_risk(self, service):
        """测试获取用户风险处理建议 - 高风险"""
        # Arrange
        abnormal_behaviors = {"abnormal_swipe": True, "abnormal_messaging": True}

        # Act
        result = service._get_user_risk_recommendations(90, abnormal_behaviors)

        # Assert
        assert any("封禁" in rec for rec in result)
        assert any("滑动" in rec for rec in result)
        assert any("发消息" in rec for rec in result)

    def test_get_user_risk_recommendations_medium_risk(self, service):
        """测试获取用户风险处理建议 - 中风险"""
        # Arrange
        abnormal_behaviors = {"abnormal_swipe": False, "abnormal_messaging": False}

        # Act
        result = service._get_user_risk_recommendations(50, abnormal_behaviors)

        # Assert
        assert any("警告" in rec for rec in result)

    def test_get_user_risk_recommendations_low_risk(self, service):
        """测试获取用户风险处理建议 - 低风险"""
        # Arrange
        abnormal_behaviors = {"abnormal_swipe": False, "abnormal_messaging": False}

        # Act
        result = service._get_user_risk_recommendations(10, abnormal_behaviors)

        # Assert
        assert result == []

    # ==================== 统计与报告 ====================

    def test_get_safety_stats_success(self, service, mock_db):
        """测试获取安全统计成功"""
        # Arrange
        mock_events = [
            MagicMock(event_data={"risk_types": [RiskType.HARASSMENT]}),
            MagicMock(event_data={"risk_types": [RiskType.SCAM]}),
            MagicMock(event_data={"risk_types": [RiskType.HARASSMENT]}),
        ]
        mock_db.query.return_value.filter.return_value.all.return_value = mock_events

        # Act
        result = service.get_safety_stats(days=7)

        # Assert
        assert result["total_violations"] == 3
        assert "violations_by_type" in result
        assert "period_days" in result
        assert "daily_average" in result

    def test_get_safety_stats_empty(self, service, mock_db):
        """测试获取安全统计 - 无数据"""
        # Arrange
        mock_db.query.return_value.filter.return_value.all.return_value = []

        # Act
        result = service.get_safety_stats(days=7)

        # Assert
        assert result["total_violations"] == 0
        assert result["violations_by_type"] == {}
        assert result["period_days"] == 7

    def test_get_safety_service_function(self, mock_db):
        """测试 get_safety_service 函数"""
        # Arrange
        from services.safety_ai_service import get_safety_service

        # Act
        service = get_safety_service(mock_db)

        # Assert
        assert isinstance(service, SafetyAIService)
        assert service.db == mock_db
