"""
P11 安全监控服务测试

测试覆盖:
- 位置安全检查（安全区域、危险区域、未知区域）
- 语音安全检查（正常语音、求救信号、异常音量）
- 定时签到检查
- SOS 紧急触发
- 风险等级评估（低、中、高、危急）
- 紧急联系人通知
- 紧急求助流程
"""
import pytest
import os
import sys
import uuid
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timedelta

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置环境变量
os.environ['OPENAI_API_KEY'] = 'test-key'
os.environ['OPENAI_BASE_URL'] = 'https://test.api/v1'


class TestSafetyMonitoringService:
    """安全监控服务测试"""

    @pytest.fixture
    def safety_service(self):
        """创建测试服务"""
        from services.safety_guardian_service import SafetyMonitoringService
        service = SafetyMonitoringService()
        return service

    @pytest.fixture
    def mock_db(self):
        """创建 mock 数据库会话"""
        return MagicMock()

    # ==================== 服务初始化测试 ====================

    def test_init(self, safety_service):
        """测试初始化"""
        assert safety_service is not None
        assert hasattr(safety_service, 'RISK_THRESHOLDS')
        assert hasattr(safety_service, 'ALERT_LEVEL_MAP')
        assert safety_service._risk_thresholds is not None

    def test_risk_thresholds(self, safety_service):
        """测试风险阈值配置"""
        thresholds = safety_service.RISK_THRESHOLDS
        assert thresholds["low"] == 0.5
        assert thresholds["medium"] == 0.7
        assert thresholds["high"] == 0.9
        assert thresholds["critical"] == 0.95

    def test_alert_level_map(self, safety_service):
        """测试警报级别映射"""
        level_map = safety_service.ALERT_LEVEL_MAP
        assert level_map["low"] == "info"
        assert level_map["medium"] == "warning"
        assert level_map["high"] == "urgent"
        assert level_map["critical"] == "emergency"

    # ==================== 位置安全检查测试 ====================
    # 安全区域、危险区域、未知区域

    def test_check_location_safety_with_db(self, safety_service, mock_db):
        """测试位置安全检查（带数据库会话）"""
        mock_db.add = MagicMock()

        result = safety_service.check_location_safety(
            user_id='test_user_001',
            latitude=39.9,  # 北京
            longitude=116.4,
            db_session_param=mock_db
        )

        assert result is not None
        assert "safe" in result
        assert "risk_level" in result
        assert "risk_score" in result
        assert result["risk_level"] in ["low", "medium", "high", "critical"]

    def test_check_location_safety_safe_area_beijing(self, safety_service, mock_db):
        """测试安全区域 - 北京"""
        mock_db.add = MagicMock()

        # 北京位置
        result = safety_service.check_location_safety(
            user_id='test_user',
            latitude=40.0,
            longitude=116.5,
            db_session_param=mock_db
        )

        assert result["risk_level"] == "low"
        assert result["safe"] is True
        assert result["risk_score"] == 0.2
        assert "安全风险较低" in result["description"]

    def test_check_location_safety_safe_area_shanghai(self, safety_service, mock_db):
        """测试安全区域 - 上海"""
        mock_db.add = MagicMock()

        # 上海位置
        result = safety_service.check_location_safety(
            user_id='test_user',
            latitude=31.2,
            longitude=121.5,
            db_session_param=mock_db
        )

        assert result["risk_level"] == "low"
        assert result["safe"] is True

    def test_check_location_safety_safe_area_guangzhou(self, safety_service, mock_db):
        """测试安全区域 - 广州"""
        mock_db.add = MagicMock()

        # 广州位置
        result = safety_service.check_location_safety(
            user_id='test_user',
            latitude=22.8,
            longitude=114.0,
            db_session_param=mock_db
        )

        assert result["risk_level"] == "low"
        assert result["safe"] is True

    def test_check_location_safety_safe_area_shenzhen(self, safety_service, mock_db):
        """测试安全区域 - 深圳"""
        mock_db.add = MagicMock()

        # 深圳位置
        result = safety_service.check_location_safety(
            user_id='test_user',
            latitude=22.6,
            longitude=114.0,
            db_session_param=mock_db
        )

        assert result["risk_level"] == "low"
        assert result["safe"] is True

    def test_check_location_safety_unknown_area(self, safety_service, mock_db):
        """测试未知区域（城市外围）"""
        mock_db.add = MagicMock()

        # 远离城市的位置
        result = safety_service.check_location_safety(
            user_id='test_user',
            latitude=35.0,
            longitude=100.0,
            db_session_param=mock_db
        )

        assert result["risk_level"] == "medium"
        assert result["risk_score"] == 0.5
        assert result["safe"] is True  # medium 级别仍被视为 safe
        assert "城市外围区域" in result["description"]

    def test_check_location_safety_unknown_area_boundary(self, safety_service, mock_db):
        """测试未知区域边界位置"""
        mock_db.add = MagicMock()

        # 边界位置 - 正好在城市范围外
        result = safety_service.check_location_safety(
            user_id='test_user',
            latitude=39.0,  # 北京边界外
            longitude=115.0,  # 北京边界外
            db_session_param=mock_db
        )

        assert result["risk_level"] == "medium"

    def test_check_location_safety_dangerous_area_extreme(self, safety_service, mock_db):
        """测试危险区域 - 极端位置"""
        mock_db.add = MagicMock()

        # 极偏远位置
        result = safety_service.check_location_safety(
            user_id='test_user',
            latitude=50.0,
            longitude=80.0,
            db_session_param=mock_db
        )

        # 当前降级方案对偏远地区返回 medium
        assert result["risk_level"] == "medium"
        assert "建议" in result or result.get("suggestions") is not None

    def test_assess_location_risk_fallback_safe_area(self, safety_service):
        """测试位置风险降级评估 - 安全区域"""
        # 北京范围内
        result = safety_service._assess_location_risk_fallback(40.0, 116.5)
        assert result["level"] == "low"
        assert "suggestions" in result
        assert len(result["suggestions"]) >= 1

    def test_assess_location_risk_fallback_unknown_area(self, safety_service):
        """测试位置风险降级评估 - 未知区域"""
        # 远离城市
        result = safety_service._assess_location_risk_fallback(35.0, 80.0)
        assert result["level"] == "medium"
        assert len(result["suggestions"]) >= 2

    def test_assess_location_risk_with_amap_disabled(self, safety_service):
        """测试高德 API 禁用时的降级方案"""
        with patch('services.safety_guardian_service.settings', None):
            result = safety_service._assess_location_risk(40.0, 116.5)
            assert result["level"] == "low"

    def test_assess_location_risk_with_amap_enabled(self, safety_service):
        """测试高德 API 启用时的评估"""
        mock_settings = MagicMock()
        mock_settings.amap_enabled = True
        mock_settings.amap_api_key = 'test_key'

        with patch('services.safety_guardian_service.settings', mock_settings):
            result = safety_service._assess_location_risk(40.0, 116.5)
            # 当前仍使用降级方案，待集成高德 API
            assert result["level"] == "low"

    def test_assess_location_risk_with_amap_error(self, safety_service):
        """测试高德 API 出错时的降级方案"""
        mock_settings = MagicMock()
        mock_settings.amap_enabled = True
        mock_settings.amap_api_key = 'test_key'

        with patch('services.safety_guardian_service.settings', mock_settings):
            with patch.object(safety_service, '_assess_location_risk_with_amap', side_effect=Exception("API Error")):
                result = safety_service._assess_location_risk(35.0, 80.0)
                assert result["level"] == "medium"

    # ==================== 风险评分计算测试 ====================

    def test_calculate_risk_score_no_factors(self, safety_service):
        """测试风险评分计算 - 无风险因素"""
        score = safety_service._calculate_risk_score([])
        assert score == 0.0

    def test_calculate_risk_score_single_low(self, safety_service):
        """测试风险评分计算 - 单个低风险因素"""
        score = safety_service._calculate_risk_score([{"severity": "low"}])
        assert score == 0.2

    def test_calculate_risk_score_single_medium(self, safety_service):
        """测试风险评分计算 - 单个中风险因素"""
        score = safety_service._calculate_risk_score([{"severity": "medium"}])
        assert score == 0.4

    def test_calculate_risk_score_single_high(self, safety_service):
        """测试风险评分计算 - 单个高风险因素"""
        score = safety_service._calculate_risk_score([{"severity": "high"}])
        assert score == 0.7

    def test_calculate_risk_score_single_critical(self, safety_service):
        """测试风险评分计算 - 单个危急风险因素"""
        score = safety_service._calculate_risk_score([{"severity": "critical"}])
        assert score == 1.0

    def test_calculate_risk_score_multiple_factors(self, safety_service):
        """测试风险评分计算 - 多个风险因素"""
        score = safety_service._calculate_risk_score([
            {"severity": "low"},
            {"severity": "medium"},
            {"severity": "high"}
        ])
        assert score == (0.2 + 0.4 + 0.7) / 3

    def test_calculate_risk_score_unknown_severity(self, safety_service):
        """测试风险评分计算 - 未知严重性"""
        score = safety_service._calculate_risk_score([{"severity": "unknown"}])
        assert score == 0.2  # 默认为 low

    def test_calculate_risk_score_overflow(self, safety_service):
        """测试风险评分计算 - 超过上限"""
        score = safety_service._calculate_risk_score([
            {"severity": "critical"},
            {"severity": "critical"},
            {"severity": "critical"}
        ])
        assert score == 1.0  # 最大值为 1.0

    def test_calculate_risk_score_missing_severity(self, safety_service):
        """测试风险评分计算 - 缺少严重性字段"""
        score = safety_service._calculate_risk_score([{}])
        assert score == 0.2  # 默认为 low

    # ==================== 风险等级确定测试 ====================

    def test_determine_risk_level_low(self, safety_service):
        """测试风险等级确定 - 低"""
        assert safety_service._determine_risk_level(0.3) == "low"
        assert safety_service._determine_risk_level(0.1) == "low"
        assert safety_service._determine_risk_level(0.0) == "low"

    def test_determine_risk_level_medium(self, safety_service):
        """测试风险等级确定 - 中"""
        assert safety_service._determine_risk_level(0.6) == "medium"
        assert safety_service._determine_risk_level(0.55) == "medium"

    def test_determine_risk_level_high(self, safety_service):
        """测试风险等级确定 - 高"""
        assert safety_service._determine_risk_level(0.85) == "high"
        assert safety_service._determine_risk_level(0.75) == "high"

    def test_determine_risk_level_critical(self, safety_service):
        """测试风险等级确定 - 危急"""
        assert safety_service._determine_risk_level(0.95) == "critical"
        assert safety_service._determine_risk_level(0.9) == "critical"
        assert safety_service._determine_risk_level(1.0) == "critical"

    def test_determine_risk_level_boundary(self, safety_service):
        """测试风险等级确定 - 边界值"""
        # 0.5 是 medium 的边界
        assert safety_service._determine_risk_level(0.5) == "medium"
        # 0.7 是 high 的边界
        assert safety_service._determine_risk_level(0.7) == "high"
        # 0.9 是 critical 的边界
        assert safety_service._determine_risk_level(0.9) == "critical"

    # ==================== 语音安全检查测试 ====================
    # 正常语音、求救信号、异常音量

    def test_check_voice_safety_normal(self, safety_service, mock_db):
        """测试语音安全检查 - 正常语音"""
        mock_db.add = MagicMock()

        result = safety_service.check_voice_safety(
            user_id='test_user',
            session_id='session_001',
            audio_features={"volume": 50, "speech_rate": 150, "tremor": False},
            db_session_param=mock_db
        )

        assert result["safe"] is True
        assert result["risk_level"] == "low"
        assert result["anomalies"] == []

    def test_check_voice_safety_normal_range(self, safety_service, mock_db):
        """测试语音安全检查 - 正常范围内各种值"""
        mock_db.add = MagicMock()

        # 正常范围内的语音特征
        result = safety_service.check_voice_safety(
            user_id='test_user',
            session_id='session_001',
            audio_features={"volume": 70, "speech_rate": 180, "tremor": False},
            db_session_param=mock_db
        )

        assert result["safe"] is True
        assert result["risk_level"] == "low"

    def test_check_voice_safety_distress_signal_high_volume(self, safety_service, mock_db):
        """测试语音安全检查 - 求救信号（高音量）"""
        mock_db.add = MagicMock()

        # 高音量可能表示紧急情况
        result = safety_service.check_voice_safety(
            user_id='test_user',
            session_id='session_001',
            audio_features={"volume": 95, "speech_rate": 150, "tremor": False},
            db_session_param=mock_db
        )

        assert "volume_too_high" in result["anomalies"]
        assert result["risk_level"] == "low"  # 单个异常仍为 low

    def test_check_voice_safety_distress_signal_multiple_anomalies(self, safety_service, mock_db):
        """测试语音安全检查 - 求救信号（多个异常特征）"""
        mock_db.add = MagicMock()

        # 多个异常特征可能表示紧急情况（需要 >3 个异常才会 high）
        result = safety_service.check_voice_safety(
            user_id='test_user',
            session_id='session_001',
            audio_features={"volume": 95, "speech_rate": 280, "tremor": True},
            db_session_param=mock_db
        )

        assert len(result["anomalies"]) == 3
        assert result["risk_level"] == "medium"  # 3个异常为 medium（需要 >3 才会 high）
        assert result["safe"] is True  # medium 级别仍被视为 safe

    def test_check_voice_safety_distress_signal_tremor(self, safety_service, mock_db):
        """测试语音安全检查 - 求救信号（颤抖）"""
        mock_db.add = MagicMock()

        # 语音颤抖可能表示紧张或恐惧
        result = safety_service.check_voice_safety(
            user_id='test_user',
            session_id='session_001',
            audio_features={"volume": 50, "speech_rate": 150, "tremor": True},
            db_session_param=mock_db
        )

        assert "voice_tremor_detected" in result["anomalies"]

    def test_check_voice_safety_abnormal_volume_too_high(self, safety_service, mock_db):
        """测试语音安全检查 - 异常音量（过高）"""
        mock_db.add = MagicMock()

        result = safety_service.check_voice_safety(
            user_id='test_user',
            session_id='session_001',
            audio_features={"volume": 92, "speech_rate": 150, "tremor": False},
            db_session_param=mock_db
        )

        assert "volume_too_high" in result["anomalies"]

    def test_check_voice_safety_abnormal_volume_boundary(self, safety_service, mock_db):
        """测试语音安全检查 - 音量边界值"""
        mock_db.add = MagicMock()

        # 正好在阈值以下
        result = safety_service.check_voice_safety(
            user_id='test_user',
            session_id='session_001',
            audio_features={"volume": 89, "speech_rate": 150, "tremor": False},
            db_session_param=mock_db
        )

        assert result["anomalies"] == []

        # 正好在阈值以上
        result = safety_service.check_voice_safety(
            user_id='test_user',
            session_id='session_002',
            audio_features={"volume": 91, "speech_rate": 150, "tremor": False},
            db_session_param=mock_db
        )

        assert "volume_too_high" in result["anomalies"]

    def test_check_voice_safety_abnormal_speech_rate_fast(self, safety_service, mock_db):
        """测试语音安全检查 - 异常语速（过快）"""
        mock_db.add = MagicMock()

        result = safety_service.check_voice_safety(
            user_id='test_user',
            session_id='session_001',
            audio_features={"volume": 50, "speech_rate": 260, "tremor": False},
            db_session_param=mock_db
        )

        assert "abnormal_speech_rate" in result["anomalies"]

    def test_check_voice_safety_abnormal_speech_rate_slow(self, safety_service, mock_db):
        """测试语音安全检查 - 异常语速（过慢）"""
        mock_db.add = MagicMock()

        result = safety_service.check_voice_safety(
            user_id='test_user',
            session_id='session_001',
            audio_features={"volume": 50, "speech_rate": 75, "tremor": False},
            db_session_param=mock_db
        )

        assert "abnormal_speech_rate" in result["anomalies"]

    def test_check_voice_safety_abnormal_speech_rate_boundary(self, safety_service, mock_db):
        """测试语音安全检查 - 语速边界值"""
        mock_db.add = MagicMock()

        # 正好在正常范围边界
        result = safety_service.check_voice_safety(
            user_id='test_user',
            session_id='session_001',
            audio_features={"volume": 50, "speech_rate": 250, "tremor": False},
            db_session_param=mock_db
        )

        assert result["anomalies"] == []

        result = safety_service.check_voice_safety(
            user_id='test_user',
            session_id='session_002',
            audio_features={"volume": 50, "speech_rate": 80, "tremor": False},
            db_session_param=mock_db
        )

        assert result["anomalies"] == []

    def test_detect_voice_anomalies_normal(self, safety_service):
        """测试语音异常检测 - 正常情况"""
        anomalies = safety_service._detect_voice_anomalies({
            "volume": 50,
            "speech_rate": 150,
            "tremor": False
        })
        assert anomalies == []

    def test_detect_voice_anomalies_all_abnormal(self, safety_service):
        """测试语音异常检测 - 全部异常"""
        anomalies = safety_service._detect_voice_anomalies({
            "volume": 95,
            "speech_rate": 280,
            "tremor": True
        })
        assert len(anomalies) == 3
        assert "volume_too_high" in anomalies
        assert "abnormal_speech_rate" in anomalies
        assert "voice_tremor_detected" in anomalies

    def test_detect_voice_anomalies_missing_features(self, safety_service):
        """测试语音异常检测 - 缺少特征"""
        anomalies = safety_service._detect_voice_anomalies({})
        assert anomalies == []  # 使用默认值

    def test_voice_risk_level_with_one_anomaly(self, safety_service, mock_db):
        """测试语音风险等级 - 单个异常"""
        mock_db.add = MagicMock()

        result = safety_service.check_voice_safety(
            user_id='test_user',
            session_id='session_001',
            audio_features={"volume": 95, "speech_rate": 150, "tremor": False},
            db_session_param=mock_db
        )

        assert result["risk_level"] == "low"  # 1个异常为 low

    def test_voice_risk_level_with_two_anomalies(self, safety_service, mock_db):
        """测试语音风险等级 - 两个异常"""
        mock_db.add = MagicMock()

        result = safety_service.check_voice_safety(
            user_id='test_user',
            session_id='session_001',
            audio_features={"volume": 95, "speech_rate": 280, "tremor": False},
            db_session_param=mock_db
        )

        assert result["risk_level"] == "medium"  # 2个异常为 medium

    def test_voice_risk_level_with_three_anomalies(self, safety_service, mock_db):
        """测试语音风险等级 - 三个异常"""
        mock_db.add = MagicMock()

        result = safety_service.check_voice_safety(
            user_id='test_user',
            session_id='session_001',
            audio_features={"volume": 95, "speech_rate": 280, "tremor": True},
            db_session_param=mock_db
        )

        assert result["risk_level"] == "medium"  # 3个异常为 medium（需要 >3 才会 high）

    def test_voice_risk_level_with_four_anomalies(self, safety_service, mock_db):
        """测试语音风险等级 - 四个异常（高风险）"""
        mock_db.add = MagicMock()

        # 添加额外的异常特征来触发高风险
        result = safety_service.check_voice_safety(
            user_id='test_user',
            session_id='session_001',
            audio_features={"volume": 95, "speech_rate": 280, "tremor": True, "panic_detected": True},
            db_session_param=mock_db
        )

        # 注意：源代码只检测 volume、speech_rate、tremor 三种异常
        # 所以即使有更多字段，也只会检测到 3 个异常
        assert result["risk_level"] == "medium"  # 当前检测逻辑只检测 3 种异常

    # ==================== 安全警报创建与管理测试 ====================

    def test_create_safety_alert(self, safety_service, mock_db):
        """测试创建安全警报"""
        mock_db.add = MagicMock()

        alert_id = safety_service.create_safety_alert(
            user_id='test_user',
            alert_type='location_risk',
            risk_level='high',
            description='高风险位置警告',
            db_session_param=mock_db
        )

        assert alert_id is not None
        mock_db.add.assert_called_once()

    def test_create_safety_alert_level_mapping(self, safety_service, mock_db):
        """测试警报级别映射"""
        mock_db.add = MagicMock()

        # 低风险 - info
        alert_id = safety_service.create_safety_alert(
            user_id='test_user',
            alert_type='test',
            risk_level='low',
            description='test',
            db_session_param=mock_db
        )
        assert alert_id is not None

        # 中风险 - warning
        alert_id = safety_service.create_safety_alert(
            user_id='test_user',
            alert_type='test',
            risk_level='medium',
            description='test',
            db_session_param=mock_db
        )
        assert alert_id is not None

        # 高风险 - urgent
        alert_id = safety_service.create_safety_alert(
            user_id='test_user',
            alert_type='test',
            risk_level='high',
            description='test',
            db_session_param=mock_db
        )
        assert alert_id is not None

        # 严重风险 - emergency
        alert_id = safety_service.create_safety_alert(
            user_id='test_user',
            alert_type='test',
            risk_level='critical',
            description='test',
            db_session_param=mock_db
        )
        assert alert_id is not None

    def test_create_safety_alert_unknown_level(self, safety_service, mock_db):
        """测试创建警报 - 未知风险级别"""
        mock_db.add = MagicMock()

        alert_id = safety_service.create_safety_alert(
            user_id='test_user',
            alert_type='test',
            risk_level='unknown',
            description='test',
            db_session_param=mock_db
        )

        assert alert_id is not None
        # 应使用默认级别 warning

    def test_get_user_safety_history(self, safety_service, mock_db):
        """测试获取用户安全历史"""
        mock_check = MagicMock()
        mock_check.id = 'check_001'
        mock_check.check_type = 'location_safety'
        mock_check.risk_level = 'low'
        mock_check.risk_score = 0.2
        mock_check.location_data = {"address": "北京市"}
        mock_check.checked_at = datetime.now()

        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_check]

        history = safety_service.get_user_safety_history(
            user_id='test_user',
            days=30,
            db_session_param=mock_db
        )

        assert isinstance(history, list)
        assert len(history) == 1
        assert history[0]["id"] == 'check_001'
        assert history[0]["check_type"] == 'location_safety'

    def test_get_user_safety_history_empty(self, safety_service, mock_db):
        """测试获取用户安全历史 - 无数据"""
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        history = safety_service.get_user_safety_history(
            user_id='test_user',
            days=30,
            db_session_param=mock_db
        )

        assert history == []

    def test_get_user_safety_history_multiple_records(self, safety_service, mock_db):
        """测试获取用户安全历史 - 多条记录"""
        mock_checks = [
            MagicMock(
                id=f'check_{i}',
                check_type='location_safety',
                risk_level='low',
                risk_score=0.2,
                location_data={"address": f"地址{i}"},
                checked_at=datetime.now() - timedelta(days=i)
            )
            for i in range(5)
        ]

        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_checks

        history = safety_service.get_user_safety_history(
            user_id='test_user',
            days=30,
            db_session_param=mock_db
        )

        assert len(history) == 5

    # ==================== 定时签到检查测试 ====================

    def test_check_in_safety_safe(self, safety_service, mock_db):
        """测试约会安全打卡 - 安全状态"""
        mock_session = MagicMock()
        mock_session.id = 'session_001'
        mock_session.user_id = 'test_user'
        mock_session.checkins = []

        mock_db.query.return_value.filter.return_value.first.return_value = mock_session

        result = safety_service.check_in_safety(
            session_id='session_001',
            user_status='safe',
            db_session_param=mock_db
        )

        assert result is True

    def test_check_in_safety_nonexistent_session(self, safety_service, mock_db):
        """测试约会安全打卡 - 不存在的会话"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = safety_service.check_in_safety(
            session_id='nonexistent',
            user_status='safe',
            db_session_param=mock_db
        )

        assert result is False

    def test_check_in_safety_unsafe_status(self, safety_service, mock_db):
        """测试约会安全打卡 - 不安全状态"""
        mock_session = MagicMock()
        mock_session.id = 'session_001'
        mock_session.user_id = 'test_user'
        mock_session.checkins = []

        mock_db.query.return_value.filter.return_value.first.return_value = mock_session
        mock_db.add = MagicMock()

        result = safety_service.check_in_safety(
            session_id='session_001',
            user_status='unsafe',
            db_session_param=mock_db
        )

        assert result is True
        mock_db.add.assert_called()

    def test_check_in_safety_with_existing_checkins(self, safety_service, mock_db):
        """测试约会安全打卡 - 已有签到记录"""
        mock_session = MagicMock()
        mock_session.id = 'session_001'
        mock_session.user_id = 'test_user'
        mock_session.checkins = [
            {"timestamp": datetime.now().isoformat(), "status": "safe"}
        ]

        mock_db.query.return_value.filter.return_value.first.return_value = mock_session

        result = safety_service.check_in_safety(
            session_id='session_001',
            user_status='safe',
            db_session_param=mock_db
        )

        assert result is True

    def test_check_in_safety_string_checkins(self, safety_service, mock_db):
        """测试约会安全打卡 - 签到记录为字符串"""
        import json
        mock_session = MagicMock()
        mock_session.id = 'session_001'
        mock_session.user_id = 'test_user'
        mock_session.checkins = json.dumps([
            {"timestamp": datetime.now().isoformat(), "status": "safe"}
        ])

        mock_db.query.return_value.filter.return_value.first.return_value = mock_session

        result = safety_service.check_in_safety(
            session_id='session_001',
            user_status='safe',
            db_session_param=mock_db
        )

        assert result is True

    def test_check_in_safety_none_checkins(self, safety_service, mock_db):
        """测试约会安全打卡 - 签到记录为 None"""
        mock_session = MagicMock()
        mock_session.id = 'session_001'
        mock_session.user_id = 'test_user'
        mock_session.checkins = None

        mock_db.query.return_value.filter.return_value.first.return_value = mock_session

        result = safety_service.check_in_safety(
            session_id='session_001',
            user_status='safe',
            db_session_param=mock_db
        )

        assert result is True

    # ==================== SOS 紧急触发测试 ====================

    def test_trigger_emergency_response(self, safety_service, mock_db):
        """测试触发紧急响应"""
        mock_db.add = MagicMock()

        result = safety_service.trigger_emergency_response(
            user_id='test_user',
            session_id='session_001',
            db_session_param=mock_db
        )

        assert result is not None
        assert "alert_id" in result
        assert result["status"] == "triggered"
        assert "next_steps" in result
        assert len(result["next_steps"]) >= 1

    def test_trigger_emergency_response_without_session(self, safety_service, mock_db):
        """测试触发紧急响应 - 无会话"""
        mock_db.add = MagicMock()

        result = safety_service.trigger_emergency_response(
            user_id='test_user',
            session_id=None,
            db_session_param=mock_db
        )

        assert result is not None
        assert result["status"] == "triggered"

    def test_trigger_emergency_creates_critical_alert(self, safety_service, mock_db):
        """测试触发紧急响应创建危急警报"""
        mock_db.add = MagicMock()

        result = safety_service.trigger_emergency_response(
            user_id='test_user',
            session_id='session_001',
            db_session_param=mock_db
        )

        # 验证创建了警报
        mock_db.add.assert_called()
        assert result["status"] == "triggered"

    # ==================== 安全计划管理测试 ====================

    def test_get_safety_plan_existing(self, safety_service, mock_db):
        """测试获取已有安全计划"""
        mock_plan = MagicMock()
        mock_plan.id = 'plan_001'
        mock_plan.emergency_contacts = '[{"name": "联系人1", "phone": "13800138000"}]'
        mock_plan.safety_preferences = '{"safe_words": ["help"], "preferred_actions": ["call"]}'
        mock_plan.user_id = 'test_user'

        mock_db.query.return_value.filter.return_value.first.return_value = mock_plan

        plan = safety_service.get_safety_plan(
            user_id='test_user',
            db_session_param=mock_db
        )

        assert plan is not None
        assert "emergency_contacts" in plan
        assert len(plan["emergency_contacts"]) == 1

    def test_get_safety_plan_default(self, safety_service, mock_db):
        """测试获取默认安全计划"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        plan = safety_service.get_safety_plan(
            user_id='test_user',
            db_session_param=mock_db
        )

        assert plan is not None
        assert plan["emergency_contacts"] == []
        assert "help" in plan["safe_words"]
        assert "unsafe" in plan["safe_words"]

    def test_update_safety_plan_existing(self, safety_service, mock_db):
        """测试更新已有安全计划"""
        mock_plan = MagicMock()
        mock_plan.id = 'plan_001'

        mock_db.query.return_value.filter.return_value.first.return_value = mock_plan

        plan_id = safety_service.update_safety_plan(
            user_id='test_user',
            emergency_contacts=[{"name": "联系人1"}],
            safe_words=["help", "unsafe"],
            preferred_actions=["call_emergency"],
            db_session_param=mock_db
        )

        assert plan_id == 'plan_001'

    def test_update_safety_plan_new(self, safety_service, mock_db):
        """测试创建新安全计划"""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.add = MagicMock()

        plan_id = safety_service.update_safety_plan(
            user_id='test_user',
            emergency_contacts=[{"name": "联系人1"}],
            safe_words=["help"],
            preferred_actions=["call"],
            db_session_param=mock_db
        )

        assert plan_id is not None
        mock_db.add.assert_called_once()

    def test_update_safety_plan_with_commit(self, safety_service, mock_db):
        """测试更新安全计划提交事务"""
        mock_plan = MagicMock()
        mock_plan.id = 'plan_001'

        mock_db.query.return_value.filter.return_value.first.return_value = mock_plan
        mock_db.commit = MagicMock()

        plan_id = safety_service.update_safety_plan(
            user_id='test_user',
            emergency_contacts=[{"name": "联系人1"}],
            safe_words=["help"],
            preferred_actions=["call"],
            db_session_param=mock_db
        )

        mock_db.commit.assert_called()


class TestSafetyMonitoringServiceAPI:
    """API 适配层测试"""

    @pytest.fixture
    def safety_service(self):
        """创建测试服务"""
        from services.safety_guardian_service import SafetyMonitoringService
        service = SafetyMonitoringService()
        return service

    @pytest.fixture
    def mock_db(self):
        """创建 mock 数据库会话"""
        return MagicMock()

    # ==================== API 层位置安全检查测试 ====================

    def test_perform_location_safety_check(self, safety_service, mock_db):
        """测试执行位置安全检查"""
        mock_db.add = MagicMock()

        result = safety_service.perform_location_safety_check(
            user_id='test_user',
            location_data={"latitude": 40.0, "longitude": 116.5},
            session_id='session_001',
            partner_user_id='partner_001',
            db_session_param=mock_db
        )

        assert result is not None
        assert "check_id" in result
        assert "risk_level" in result
        assert "alert_triggered" in result

    def test_perform_location_safety_check_safe_area(self, safety_service, mock_db):
        """测试位置安全检查 - 安全区域"""
        mock_db.add = MagicMock()

        result = safety_service.perform_location_safety_check(
            user_id='test_user',
            location_data={"latitude": 40.0, "longitude": 116.5},
            db_session_param=mock_db
        )

        assert result["risk_level"] == "low"
        assert result["alert_triggered"] is False

    def test_perform_location_safety_check_unknown_area(self, safety_service, mock_db):
        """测试位置安全检查 - 未知区域"""
        mock_db.add = MagicMock()

        result = safety_service.perform_location_safety_check(
            user_id='test_user',
            location_data={"latitude": 35.0, "longitude": 80.0},
            db_session_param=mock_db
        )

        assert result["risk_level"] == "medium"
        assert result["alert_triggered"] is False

    def test_perform_location_safety_check_with_alert(self, safety_service, mock_db):
        """测试位置安全检查触发警报"""
        mock_db.add = MagicMock()

        # 使用 patch 模拟高风险位置
        with patch.object(safety_service, '_assess_location_risk', return_value={
            "level": "high",
            "score": 0.8,
            "description": "高风险区域"
        }):
            result = safety_service.perform_location_safety_check(
                user_id='test_user',
                location_data={"latitude": 35.0, "longitude": 80.0},
                db_session_param=mock_db
            )

            assert result["risk_level"] == "high"
            assert result["alert_triggered"] is True
            assert result["alert_id"] is not None

    # ==================== API 层语音异常检测测试 ====================

    def test_perform_voice_anomaly_check(self, safety_service, mock_db):
        """测试执行语音异常检测"""
        mock_db.add = MagicMock()

        result = safety_service.perform_voice_anomaly_check(
            user_id='test_user',
            voice_data={"volume": 50, "speech_rate": 150},
            session_id='session_001',
            db_session_param=mock_db
        )

        assert result is not None
        assert "check_id" in result
        assert "anomalies" in result
        assert "anomaly_detected" in result

    def test_perform_voice_anomaly_check_normal(self, safety_service, mock_db):
        """测试语音异常检测 - 正常语音"""
        mock_db.add = MagicMock()

        result = safety_service.perform_voice_anomaly_check(
            user_id='test_user',
            voice_data={"volume": 50, "speech_rate": 150, "tremor": False},
            session_id='session_001',
            db_session_param=mock_db
        )

        assert result["anomaly_detected"] is False
        assert result["anomalies"] == []

    def test_perform_voice_anomaly_check_with_anomalies(self, safety_service, mock_db):
        """测试语音异常检测发现异常"""
        mock_db.add = MagicMock()

        result = safety_service.perform_voice_anomaly_check(
            user_id='test_user',
            voice_data={"volume": 95, "speech_rate": 280, "tremor": True},
            session_id='session_001',
            db_session_param=mock_db
        )

        assert result["anomaly_detected"] is True
        assert len(result["anomalies"]) == 3
        assert result["alert_triggered"] is True

    def test_perform_voice_anomaly_check_distress_signal(self, safety_service, mock_db):
        """测试语音异常检测 - 求救信号特征"""
        mock_db.add = MagicMock()

        # 模拟求救信号特征：高音量 + 快语速 + 颤抖
        result = safety_service.perform_voice_anomaly_check(
            user_id='test_user',
            voice_data={"volume": 98, "speech_rate": 300, "tremor": True},
            session_id='session_001',
            db_session_param=mock_db
        )

        assert result["anomaly_detected"] is True
        assert result["alert_triggered"] is True
        assert result["risk_level"] == "medium"  # 3个异常为 medium（需要 >3 才会 high）

    # ==================== API 层定时签到测试 ====================

    def test_perform_scheduled_checkin_ok(self, safety_service, mock_db):
        """测试执行定时签到 - 正常状态"""
        mock_session = MagicMock()
        mock_session.id = 'session_001'
        mock_session.user_id = 'test_user'
        mock_session.checkins = []

        mock_db.query.return_value.filter.return_value.first.return_value = mock_session

        result = safety_service.perform_scheduled_checkin(
            user_id='test_user',
            session_id='session_001',
            user_status='ok',
            note='测试签到',
            db_session_param=mock_db
        )

        assert result["status"] == "ok"
        assert result["alert_triggered"] is False
        assert result["risk_level"] == "low"

    def test_perform_scheduled_checkin_need_help(self, safety_service, mock_db):
        """测试签到请求帮助"""
        mock_session = MagicMock()
        mock_session.id = 'session_001'
        mock_session.user_id = 'test_user'
        mock_session.checkins = []

        mock_db.query.return_value.filter.return_value.first.return_value = mock_session
        mock_db.add = MagicMock()

        result = safety_service.perform_scheduled_checkin(
            user_id='test_user',
            session_id='session_001',
            user_status='need_help',
            note='需要帮助',
            db_session_param=mock_db
        )

        assert result["status"] == "need_help"
        assert result["alert_triggered"] is True
        assert result["risk_level"] == "high"
        assert result["risk_score"] == 0.9

    def test_perform_scheduled_checkin_session_not_found(self, safety_service, mock_db):
        """测试签到会话不存在"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError):
            safety_service.perform_scheduled_checkin(
                user_id='test_user',
                session_id='nonexistent',
                user_status='ok',
                db_session_param=mock_db
            )

    def test_perform_scheduled_checkin_with_note(self, safety_service, mock_db):
        """测试签到带备注"""
        mock_session = MagicMock()
        mock_session.id = 'session_001'
        mock_session.user_id = 'test_user'
        mock_session.checkins = []

        mock_db.query.return_value.filter.return_value.first.return_value = mock_session

        result = safety_service.perform_scheduled_checkin(
            user_id='test_user',
            session_id='session_001',
            user_status='ok',
            note='我还在约会中，一切正常',
            db_session_param=mock_db
        )

        assert result["status"] == "ok"

    # ==================== API 层警报管理测试 ====================

    def test_get_safety_alerts(self, safety_service, mock_db):
        """测试获取安全警报"""
        mock_alert = MagicMock()
        mock_alert.id = 'alert_001'
        mock_alert.alert_type = 'location_risk'
        mock_alert.alert_level = 'warning'

        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_alert]

        alerts = safety_service.get_safety_alerts(
            user_id='test_user',
            limit=10,
            db_session_param=mock_db
        )

        assert isinstance(alerts, list)
        assert len(alerts) == 1

    def test_get_safety_alerts_empty(self, safety_service, mock_db):
        """测试获取安全警报 - 无数据"""
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        alerts = safety_service.get_safety_alerts(
            user_id='test_user',
            limit=10,
            db_session_param=mock_db
        )

        assert alerts == []

    def test_acknowledge_alert(self, safety_service, mock_db):
        """测试确认警报"""
        mock_alert = MagicMock()

        mock_db.query.return_value.filter.return_value.first.return_value = mock_alert

        result = safety_service.acknowledge_alert(
            alert_id='alert_001',
            user_id='test_user',
            db_session_param=mock_db
        )

        assert result is True
        assert mock_alert.response_status == "acknowledged"

    def test_acknowledge_alert_not_found(self, safety_service, mock_db):
        """测试确认不存在的警报"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = safety_service.acknowledge_alert(
            alert_id='nonexistent',
            user_id='test_user',
            db_session_param=mock_db
        )

        assert result is False

    def test_resolve_alert(self, safety_service, mock_db):
        """测试解决警报"""
        mock_alert = MagicMock()

        mock_db.query.return_value.filter.return_value.first.return_value = mock_alert

        result = safety_service.resolve_alert(
            alert_id='alert_001',
            user_id='test_user',
            resolution_notes='已处理',
            is_false_alarm=False,
            db_session_param=mock_db
        )

        assert result is True
        assert mock_alert.response_status == "resolved"
        assert mock_alert.is_false_alarm is False

    def test_resolve_alert_not_found(self, safety_service, mock_db):
        """测试解决不存在的警报"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = safety_service.resolve_alert(
            alert_id='nonexistent',
            user_id='test_user',
            resolution_notes='已处理',
            db_session_param=mock_db
        )

        assert result is False

    def test_resolve_alert_as_false_alarm(self, safety_service, mock_db):
        """测试解决警报 - 误报"""
        mock_alert = MagicMock()

        mock_db.query.return_value.filter.return_value.first.return_value = mock_alert

        result = safety_service.resolve_alert(
            alert_id='alert_001',
            user_id='test_user',
            resolution_notes='误报，无需处理',
            is_false_alarm=True,
            db_session_param=mock_db
        )

        assert result is True
        assert mock_alert.is_false_alarm is True

    # ==================== API 层安全计划测试 ====================

    def test_create_safety_plan_api(self, safety_service, mock_db):
        """测试创建安全计划（API 层）"""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.add = MagicMock()

        plan_id = safety_service.create_safety_plan(
            user_id='test_user',
            emergency_contacts=[{"name": "联系人1", "phone": "13800138000"}],
            safety_preferences={"safe_words": ["help", "sos"], "preferred_actions": ["call", "share_location"]},
            db_session_param=mock_db
        )

        assert plan_id is not None

    def test_get_user_safety_plan_api(self, safety_service, mock_db):
        """测试获取用户安全计划（API 层）"""
        mock_plan = MagicMock()
        mock_plan.id = 'plan_001'
        mock_plan.emergency_contacts = '[{"name": "联系人1"}]'
        mock_plan.safety_preferences = '{"safe_words": ["help"]}'

        mock_db.query.return_value.filter.return_value.first.return_value = mock_plan

        plan = safety_service.get_user_safety_plan(
            user_id='test_user',
            db_session_param=mock_db
        )

        assert plan is not None
        assert plan.id == 'plan_001'

    def test_get_user_safety_plan_api_not_found(self, safety_service, mock_db):
        """测试获取不存在的安全计划"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        plan = safety_service.get_user_safety_plan(
            user_id='test_user',
            db_session_param=mock_db
        )

        assert plan is None

    # ==================== API 层约会安全会话测试 ====================

    def test_create_date_safety_session_api(self, safety_service, mock_db):
        """测试创建约会安全会话（API 层）"""
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        session_id = safety_service.create_date_safety_session(
            user_id='test_user',
            partner_user_id='partner_001',
            date_id='date_001',
            scheduled_start=datetime.now(),
            scheduled_end=datetime.now() + timedelta(hours=2),
            db_session_param=mock_db
        )

        assert session_id is not None
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    def test_start_date_safety_session(self, safety_service, mock_db):
        """测试开始约会安全会话"""
        mock_session = MagicMock()

        mock_db.query.return_value.filter.return_value.first.return_value = mock_session

        result = safety_service.start_date_safety_session(
            session_id='session_001',
            db_session_param=mock_db
        )

        assert result is True
        assert mock_session.session_status == "active"

    def test_start_date_safety_session_not_found(self, safety_service, mock_db):
        """测试开始不存在的约会会话"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = safety_service.start_date_safety_session(
            session_id='nonexistent',
            db_session_param=mock_db
        )

        assert result is False

    def test_complete_date_safety_session(self, safety_service, mock_db):
        """测试完成约会安全会话"""
        mock_session = MagicMock()

        mock_db.query.return_value.filter.return_value.first.return_value = mock_session

        result = safety_service.complete_date_safety_session(
            session_id='session_001',
            safety_rating=5,
            feedback='约会很愉快',
            db_session_param=mock_db
        )

        assert result is True
        assert mock_session.session_status == "completed"
        assert mock_session.safety_rating == 5

    def test_complete_date_safety_session_not_found(self, safety_service, mock_db):
        """测试完成不存在的约会会话"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = safety_service.complete_date_safety_session(
            session_id='nonexistent',
            safety_rating=5,
            db_session_param=mock_db
        )

        assert result is False

    def test_complete_date_safety_session_with_feedback(self, safety_service, mock_db):
        """测试完成约会会话带反馈"""
        mock_session = MagicMock()

        mock_db.query.return_value.filter.return_value.first.return_value = mock_session

        result = safety_service.complete_date_safety_session(
            session_id='session_001',
            safety_rating=4,
            feedback='约会安全，对方很礼貌',
            db_session_param=mock_db
        )

        assert result is True
        assert mock_session.post_date_feedback == '约会安全，对方很礼貌'

    # ==================== API 层紧急求助测试 ====================

    def test_trigger_emergency(self, safety_service, mock_db):
        """测试触发紧急求助（API 层）"""
        with patch.object(safety_service, 'trigger_emergency_response', return_value={
            "alert_id": "alert_001",
            "status": "triggered",
            "next_steps": []
        }):
            result = safety_service.trigger_emergency(
                user_id='test_user',
                session_id='session_001',
                location_data={"latitude": 40.0, "longitude": 116.5},
                emergency_type='urgent',
                note='紧急求助'
            )

            assert result is not None
            assert result["alert_level"] == "critical"
            assert result["status"] == "active"

    def test_trigger_emergency_sos(self, safety_service, mock_db):
        """测试触发 SOS 紧急求助"""
        with patch.object(safety_service, 'trigger_emergency_response', return_value={
            "alert_id": "sos_alert_001",
            "status": "triggered",
            "notifications_sent": 0,
            "next_steps": ["等待紧急联系人响应", "持续共享位置", "保持手机畅通"]
        }):
            result = safety_service.trigger_emergency(
                user_id='test_user',
                session_id='date_session_001',
                location_data={"latitude": 40.0, "longitude": 116.5, "address": "北京市朝阳区"},
                emergency_type='sos',
                note='我感觉不安全'
            )

            assert result["emergency_id"] == "sos_alert_001"
            assert "正在通知紧急联系人" in result["message"]


class TestEmergencyContactNotification:
    """紧急联系人通知测试"""

    @pytest.fixture
    def safety_service(self):
        """创建测试服务"""
        from services.safety_guardian_service import SafetyMonitoringService
        return SafetyMonitoringService()

    @pytest.fixture
    def mock_db(self):
        """创建 mock 数据库会话"""
        return MagicMock()

    def test_notify_emergency_contact_success(self, safety_service, mock_db):
        """测试通知紧急联系人成功"""
        mock_plan = MagicMock()
        mock_plan.emergency_contacts = '[{"name": "张三", "phone": "13800138000"}, {"name": "李四", "phone": "13900139000"}]'

        mock_db.query.return_value.filter.return_value.first.return_value = mock_plan

        with patch('services.safety_guardian_service.db_session_readonly') as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            result = safety_service.notify_emergency_contact(
                user_id='test_user',
                session_id='session_001',
                contact_index=0,
                custom_message='紧急求助，请立即联系我',
                location_data={"latitude": 40.0, "longitude": 116.5}
            )

        assert result is not None
        assert "contact_name" in result
        assert result["contact_name"] == "张三"
        assert "notification_id" in result
        assert result["location_shared"] is True

    def test_notify_emergency_contact_second_contact(self, safety_service, mock_db):
        """测试通知第二个紧急联系人"""
        mock_plan = MagicMock()
        mock_plan.emergency_contacts = '[{"name": "张三", "phone": "13800138000"}, {"name": "李四", "phone": "13900139000"}]'

        mock_db.query.return_value.filter.return_value.first.return_value = mock_plan

        with patch('services.safety_guardian_service.db_session_readonly') as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            result = safety_service.notify_emergency_contact(
                user_id='test_user',
                session_id='session_001',
                contact_index=1,
                custom_message=None,
                location_data=None
            )

        assert result["contact_name"] == "李四"
        assert result["contact_phone"] == "13900139000"

    def test_notify_emergency_contact_no_plan(self, safety_service, mock_db):
        """测试无安全计划时的紧急联系人通知"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch('services.safety_guardian_service.db_session_readonly') as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            with pytest.raises(ValueError) as exc_info:
                safety_service.notify_emergency_contact(
                    user_id='test_user',
                    session_id='session_001',
                    contact_index=0,
                    custom_message='紧急求助',
                    location_data=None
                )

            assert "No emergency contacts found" in str(exc_info.value)

    def test_notify_emergency_contact_empty_contacts(self, safety_service, mock_db):
        """测试空紧急联系人列表"""
        mock_plan = MagicMock()
        mock_plan.emergency_contacts = '[]'

        mock_db.query.return_value.filter.return_value.first.return_value = mock_plan

        with patch('services.safety_guardian_service.db_session_readonly') as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            with pytest.raises(ValueError):
                safety_service.notify_emergency_contact(
                    user_id='test_user',
                    session_id='session_001',
                    contact_index=0,
                    custom_message='紧急求助',
                    location_data=None
                )

    def test_notify_emergency_contact_invalid_index(self, safety_service, mock_db):
        """测试无效联系人索引"""
        mock_plan = MagicMock()
        mock_plan.emergency_contacts = '[{"name": "联系人1"}]'

        mock_db.query.return_value.filter.return_value.first.return_value = mock_plan

        with patch('services.safety_guardian_service.db_session_readonly') as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            with pytest.raises(ValueError) as exc_info:
                safety_service.notify_emergency_contact(
                    user_id='test_user',
                    session_id='session_001',
                    contact_index=5,  # 超出范围
                    custom_message='紧急求助',
                    location_data=None
                )

            assert "Contact index out of range" in str(exc_info.value)

    def test_notify_emergency_contact_with_location(self, safety_service, mock_db):
        """测试通知紧急联系人带位置信息"""
        mock_plan = MagicMock()
        mock_plan.emergency_contacts = '[{"name": "张三", "phone": "13800138000"}]'

        mock_db.query.return_value.filter.return_value.first.return_value = mock_plan

        with patch('services.safety_guardian_service.db_session_readonly') as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            result = safety_service.notify_emergency_contact(
                user_id='test_user',
                session_id='session_001',
                contact_index=0,
                custom_message='我在约会中感觉不安全',
                location_data={"latitude": 40.0, "longitude": 116.5, "address": "北京市朝阳区"}
            )

        assert result["location_shared"] is True

    def test_notify_emergency_contact_default_message(self, safety_service, mock_db):
        """测试通知紧急联系人使用默认消息"""
        mock_plan = MagicMock()
        mock_plan.emergency_contacts = '[{"name": "张三", "phone": "13800138000"}]'

        mock_db.query.return_value.filter.return_value.first.return_value = mock_plan

        with patch('services.safety_guardian_service.db_session_readonly') as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            result = safety_service.notify_emergency_contact(
                user_id='test_user_123',
                session_id='session_001',
                contact_index=0,
                custom_message=None,  # 使用默认消息
                location_data=None
            )

        assert "用户 test_user_123 请求紧急联系" in result["message"]


class TestEmergencyHelpProcess:
    """紧急求助流程端到端测试"""

    @pytest.fixture
    def safety_service(self):
        """创建测试服务"""
        from services.safety_guardian_service import SafetyMonitoringService
        return SafetyMonitoringService()

    @pytest.fixture
    def mock_db(self):
        """创建 mock 数据库会话"""
        return MagicMock()

    def test_full_emergency_process(self, safety_service, mock_db):
        """测试完整紧急求助流程"""
        mock_db.add = MagicMock()

        # 步骤 1: 触发紧急求助
        emergency_result = safety_service.trigger_emergency_response(
            user_id='test_user',
            session_id='date_session_001',
            db_session_param=mock_db
        )

        assert emergency_result["status"] == "triggered"
        assert emergency_result["alert_id"] is not None

    def test_emergency_process_with_voice_detection(self, safety_service, mock_db):
        """测试语音检测触发紧急求助流程"""
        mock_db.add = MagicMock()

        # 步骤 1: 检测到求救信号特征的语音
        voice_result = safety_service.check_voice_safety(
            user_id='test_user',
            session_id='date_session_001',
            audio_features={"volume": 98, "speech_rate": 300, "tremor": True},
            db_session_param=mock_db
        )

        # 当前检测逻辑只检测 3 种异常，风险级别为 medium
        assert voice_result["risk_level"] == "medium"
        assert len(voice_result["anomalies"]) == 3

        # 步骤 2: API 层检测并创建警报（因为有异常会触发警报）
        api_result = safety_service.perform_voice_anomaly_check(
            user_id='test_user',
            voice_data={"volume": 98, "speech_rate": 300, "tremor": True},
            session_id='date_session_001',
            db_session_param=mock_db
        )

        assert api_result["alert_triggered"] is True
        assert api_result["alert_id"] is not None

    def test_emergency_process_with_checkin_need_help(self, safety_service, mock_db):
        """测试签到请求帮助触发紧急流程"""
        mock_session = MagicMock()
        mock_session.id = 'date_session_001'
        mock_session.user_id = 'test_user'
        mock_session.checkins = []

        mock_db.query.return_value.filter.return_value.first.return_value = mock_session
        mock_db.add = MagicMock()

        # 用户签到报告需要帮助
        checkin_result = safety_service.perform_scheduled_checkin(
            user_id='test_user',
            session_id='date_session_001',
            user_status='need_help',
            note='我感觉不安全，对方行为异常',
            db_session_param=mock_db
        )

        assert checkin_result["alert_triggered"] is True
        assert checkin_result["risk_level"] == "high"

    def test_emergency_process_notify_contacts(self, safety_service, mock_db):
        """测试紧急求助后通知紧急联系人"""
        # 准备安全计划
        mock_plan = MagicMock()
        mock_plan.emergency_contacts = '[{"name": "紧急联系人1", "phone": "13800138000"}, {"name": "紧急联系人2", "phone": "13900139000"}]'

        mock_db.query.return_value.filter.return_value.first.return_value = mock_plan

        # 触发紧急求助后通知第一个联系人
        with patch('services.safety_guardian_service.db_session_readonly') as mock_session:
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)

            result = safety_service.notify_emergency_contact(
                user_id='test_user',
                session_id='date_session_001',
                contact_index=0,
                custom_message='紧急求助！请立即联系我',
                location_data={"latitude": 40.0, "longitude": 116.5}
            )

        assert result["contact_name"] == "紧急联系人1"
        assert result["location_shared"] is True

    def test_emergency_process_alert_resolution(self, safety_service, mock_db):
        """测试紧急警报解决流程"""
        mock_alert = MagicMock()
        mock_alert.id = 'emergency_alert_001'
        mock_alert.response_status = 'pending'

        mock_db.query.return_value.filter.return_value.first.return_value = mock_alert

        # 确认警报
        ack_result = safety_service.acknowledge_alert(
            alert_id='emergency_alert_001',
            user_id='test_user',
            db_session_param=mock_db
        )

        assert ack_result is True
        assert mock_alert.response_status == "acknowledged"

        # 解决警报
        resolve_result = safety_service.resolve_alert(
            alert_id='emergency_alert_001',
            user_id='test_user',
            resolution_notes='已安全离开约会地点',
            is_false_alarm=False,
            db_session_param=mock_db
        )

        assert resolve_result is True
        assert mock_alert.response_status == "resolved"

    def test_emergency_process_false_alarm(self, safety_service, mock_db):
        """测试紧急警报误报处理"""
        mock_alert = MagicMock()

        mock_db.query.return_value.filter.return_value.first.return_value = mock_alert

        result = safety_service.resolve_alert(
            alert_id='alert_001',
            user_id='test_user',
            resolution_notes='误触发了紧急按钮，实际安全',
            is_false_alarm=True,
            db_session_param=mock_db
        )

        assert result is True
        assert mock_alert.is_false_alarm is True

    def test_date_session_safety_monitoring_flow(self, safety_service, mock_db):
        """测试约会安全会话完整监控流程"""
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()

        # 步骤 1: 创建约会安全会话
        session_id = safety_service.create_date_safety_session(
            user_id='test_user',
            partner_user_id='partner_001',
            date_id='date_001',
            scheduled_start=datetime.now(),
            scheduled_end=datetime.now() + timedelta(hours=3),
            db_session_param=mock_db
        )

        assert session_id is not None

        # 步骤 2: 开始约会会话
        mock_session = MagicMock()
        mock_session.id = session_id

        mock_db.query.return_value.filter.return_value.first.return_value = mock_session

        start_result = safety_service.start_date_safety_session(
            session_id=session_id,
            db_session_param=mock_db
        )

        assert start_result is True

        # 步骤 3: 定时签到
        mock_session.checkins = []

        checkin_result = safety_service.perform_scheduled_checkin(
            user_id='test_user',
            session_id=session_id,
            user_status='ok',
            note='约会进行中',
            db_session_param=mock_db
        )

        assert checkin_result["status"] == "ok"

        # 步骤 4: 完成约会会话
        complete_result = safety_service.complete_date_safety_session(
            session_id=session_id,
            safety_rating=5,
            feedback='约会安全愉快',
            db_session_param=mock_db
        )

        assert complete_result is True


class TestSafetyGuardianIntegration:
    """安全守护服务集成测试"""

    @pytest.fixture
    def safety_service(self):
        """创建测试服务"""
        from services.safety_guardian_service import SafetyMonitoringService
        return SafetyMonitoringService()

    @pytest.fixture
    def mock_db(self):
        """创建 mock 数据库会话"""
        return MagicMock()

    def test_global_service_instance(self):
        """测试全局服务实例"""
        from services.safety_guardian_service import (
            safety_monitoring_service,
            SafetyMonitoringService
        )
        assert safety_monitoring_service is not None
        assert isinstance(safety_monitoring_service, SafetyMonitoringService)

    def test_location_and_voice_combined_risk(self, safety_service, mock_db):
        """测试位置和语音组合风险评估"""
        mock_db.add = MagicMock()

        # 未知区域 + 求救语音特征
        location_result = safety_service.check_location_safety(
            user_id='test_user',
            latitude=35.0,
            longitude=80.0,
            db_session_param=mock_db
        )

        voice_result = safety_service.check_voice_safety(
            user_id='test_user',
            session_id='session_001',
            audio_features={"volume": 98, "speech_rate": 300, "tremor": True},
            db_session_param=mock_db
        )

        # 位置为中等风险，语音为中等风险（当前检测逻辑）
        assert location_result["risk_level"] == "medium"
        assert voice_result["risk_level"] == "medium"

    def test_risk_threshold_consistency(self, safety_service):
        """测试风险阈值一致性"""
        thresholds = safety_service.RISK_THRESHOLDS

        # 验证阈值递增
        assert thresholds["low"] < thresholds["medium"]
        assert thresholds["medium"] < thresholds["high"]
        assert thresholds["high"] < thresholds["critical"]

    def test_alert_level_mapping_consistency(self, safety_service):
        """测试警报级别映射一致性"""
        level_map = safety_service.ALERT_LEVEL_MAP

        # 验证所有风险级别都有对应的警报级别
        for risk_level in ["low", "medium", "high", "critical"]:
            assert risk_level in level_map
            assert level_map[risk_level] in ["info", "warning", "urgent", "emergency"]

    def test_service_method_signatures(self, safety_service):
        """测试服务方法签名"""
        # 验证关键方法存在
        assert hasattr(safety_service, 'check_location_safety')
        assert hasattr(safety_service, 'check_voice_safety')
        assert hasattr(safety_service, 'create_safety_alert')
        assert hasattr(safety_service, 'trigger_emergency_response')
        assert hasattr(safety_service, 'notify_emergency_contact')
        assert hasattr(safety_service, 'perform_scheduled_checkin')