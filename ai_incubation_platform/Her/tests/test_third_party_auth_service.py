"""
第三方授权服务测试

测试覆盖:
1. 初始化与配置测试 (4 tests)
2. 微信授权流程测试 (6 tests)
3. 微信用户信息推断测试 (5 tests)
4. 昵称分析测试 (5 tests)
5. 地区分析测试 (4 tests)
6. 微信朋友圈数据处理测试 (6 tests)
7. 隐私政策测试 (4 tests)
8. 单例模式测试 (3 tests)
9. 异常处理测试 (5 tests)
10. 边界条件测试 (6 tests)

总计: 48 个测试用例

注意：使用 fixture 级别的 mock，避免污染全局命名空间
"""
import pytest
import os
import sys
import json
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock, PropertyMock
from typing import Dict, Any, List, Optional

# 添加路径 - 支持从 src 目录导入
_current_dir = os.path.dirname(os.path.abspath(__file__))
_src_dir = os.path.join(os.path.dirname(_current_dir), 'src')
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

# 设置环境变量避免其他模块的导入问题
os.environ['OPENAI_API_KEY'] = 'test-key'
os.environ['OPENAI_BASE_URL'] = 'https://test.api/v1'

# 注意：不在此处做模块级别的 mock，避免污染全局命名空间
# 使用 fixture 级别的 mock 来隔离测试


# ============= 测试基础设施 =============

@pytest.fixture(scope="class")
def mock_db_for_auth():
    """为第三方授权服务测试 mock db 模块（仅在当前测试类有效）"""
    # Mock db 模块及其所有子模块
    _db_mock = MagicMock()
    _db_mock.database = MagicMock()
    _db_mock.models = MagicMock()
    _db_mock.payment_models = MagicMock()
    _db_mock.audit = MagicMock()
    _db_mock.user_models = MagicMock()
    _db_mock.match_models = MagicMock()
    _db_mock.message_models = MagicMock()
    _db_mock.relationship_models = MagicMock()

    # 保存原始模块
    original_modules = {}
    modules_to_mock = [
        'db', 'db.database', 'db.models', 'db.payment_models', 'db.audit',
        'db.user_models', 'db.match_models', 'db.message_models', 'db.relationship_models'
    ]

    for module_name in modules_to_mock:
        original_modules[module_name] = sys.modules.get(module_name, None)

    # 应用 mock
    sys.modules['db'] = _db_mock
    sys.modules['db.database'] = _db_mock.database
    sys.modules['db.models'] = _db_mock.models
    sys.modules['db.payment_models'] = _db_mock.payment_models
    sys.modules['db.audit'] = _db_mock.audit
    sys.modules['db.user_models'] = _db_mock.user_models
    sys.modules['db.match_models'] = _db_mock.match_models
    sys.modules['db.message_models'] = _db_mock.message_models
    sys.modules['db.relationship_models'] = _db_mock.relationship_models

    yield _db_mock

    # 恢复原始模块
    for module_name, original in original_modules.items():
        if original is not None:
            sys.modules[module_name] = original
        else:
            sys.modules.pop(module_name, None)


@pytest.fixture
def third_party_auth_service(mock_db_for_auth):
    """创建第三方授权服务实例"""
    from services.third_party_auth_service import ThirdPartyAuthService
    service = ThirdPartyAuthService()
    return service


@pytest.fixture
def mock_wechat_access_token_response():
    """Mock 微信 access_token 响应"""
    return {
        "access_token": "mock_access_token_12345",
        "expires_in": 7200,
        "refresh_token": "mock_refresh_token",
        "openid": "mock_openid_abc123",
        "unionid": "mock_unionid_xyz789",
        "scope": "snsapi_userinfo"
    }


@pytest.fixture
def mock_wechat_user_info_response():
    """Mock 微信用户信息响应"""
    return {
        "openid": "mock_openid_abc123",
        "unionid": "mock_unionid_xyz789",
        "nickname": "测试用户🌸",
        "sex": 1,  # 男性
        "province": "北京",
        "city": "北京",
        "country": "中国",
        "headimgurl": "https://example.com/avatar.jpg",
        "privilege": []
    }


@pytest.fixture
def mock_wechat_user_info_female():
    """Mock 微信女性用户信息响应"""
    return {
        "openid": "mock_openid_female",
        "unionid": "mock_unionid_female",
        "nickname": "Emily",
        "sex": 2,  # 女性
        "province": "上海",
        "city": "上海",
        "country": "中国",
        "headimgurl": "https://example.com/avatar_female.jpg",
        "privilege": []
    }


@pytest.fixture
def mock_wechat_error_response():
    """Mock 微信错误响应"""
    return {
        "errcode": 40001,
        "errmsg": "invalid credential"
    }


@pytest.fixture
def mock_wechat_moments_data():
    """Mock 微信朋友圈数据"""
    from services.third_party_auth_service import WechatMomentsData
    return WechatMomentsData(
        posts_count=50,
        posts=[{"id": "1", "type": "photo"}, {"id": "2", "type": "text"}],
        interest_tags=["美食", "旅行", "摄影", "音乐", "电影"],
        sentiment_summary={"positive": 0.7, "neutral": 0.2, "negative": 0.1}
    )


@pytest.fixture
def mock_wechat_moments_minimal_data():
    """Mock 微信朋友圈数据（少于5条）"""
    from services.third_party_auth_service import WechatMomentsData
    return WechatMomentsData(
        posts_count=3,
        posts=[{"id": "1"}],
        interest_tags=["美食"],
        sentiment_summary={"positive": 0.5}
    )


@pytest.fixture
def mock_wechat_moments_active_data():
    """Mock 微信朋友圈数据（高活跃度）"""
    from services.third_party_auth_service import WechatMomentsData
    return WechatMomentsData(
        posts_count=150,
        posts=[{"id": str(i)} for i in range(150)],
        interest_tags=["美食", "旅行", "摄影", "音乐", "电影", "健身", "读书", "游戏"],
        sentiment_summary={"positive": 0.85, "neutral": 0.1, "negative": 0.05}
    )


@pytest.fixture
def mock_existing_profile():
    """Mock 已有用户画像"""
    from models.profile_vector_models import UserVectorProfile, DimensionValue, DataSource
    profile = UserVectorProfile(user_id="test_user_001")
    profile.set_dimension(0, 0.5, confidence=0.8, source=DataSource.REGISTRATION)  # 年龄
    profile.set_dimension(3, 0.0, confidence=0.9, source=DataSource.REGISTRATION)  # 性别
    return profile


# ============= 第一部分：初始化与配置测试 =============

class TestThirdPartyAuthServiceInit:
    """初始化与配置测试"""

    def test_init_creates_service(self, third_party_auth_service):
        """测试初始化创建服务实例"""
        assert third_party_auth_service is not None

    def test_init_has_auth_configs(self, third_party_auth_service):
        """测试初始化包含授权配置"""
        assert hasattr(third_party_auth_service, 'auth_configs')
        assert 'wechat' in third_party_auth_service.auth_configs

    def test_init_wechat_config_has_required_urls(self, third_party_auth_service):
        """测试微信配置包含必需的URL"""
        from services.third_party_auth_service import ThirdPartyProvider
        wechat_config = third_party_auth_service.auth_configs[ThirdPartyProvider.WECHAT]
        assert 'auth_url' in wechat_config
        assert 'token_url' in wechat_config
        assert 'user_info_url' in wechat_config

    def test_init_has_data_retention_policy(self, third_party_auth_service):
        """测试初始化包含数据保留策略"""
        assert hasattr(third_party_auth_service, 'data_retention_days')
        from services.third_party_auth_service import ThirdPartyProvider
        assert ThirdPartyProvider.WECHAT in third_party_auth_service.data_retention_days
        assert third_party_auth_service.data_retention_days[ThirdPartyProvider.WECHAT] == 30


class TestThirdPartyProviderEnum:
    """ThirdPartyProvider 枚举测试"""

    def test_wechat_provider_value(self):
        """测试微信平台枚举值"""
        from services.third_party_auth_service import ThirdPartyProvider
        assert ThirdPartyProvider.WECHAT.value == "wechat"

    def test_weibo_provider_value(self):
        """测试微博平台枚举值"""
        from services.third_party_auth_service import ThirdPartyProvider
        assert ThirdPartyProvider.WEIBO.value == "weibo"

    def test_douban_provider_value(self):
        """测试豆瓣平台枚举值"""
        from services.third_party_auth_service import ThirdPartyProvider
        assert ThirdPartyProvider.DOUBAN.value == "douban"

    def test_zhihu_provider_value(self):
        """测试知乎平台枚举值"""
        from services.third_party_auth_service import ThirdPartyProvider
        assert ThirdPartyProvider.ZHIHU.value == "zhihu"


class TestWechatAuthData:
    """WechatAuthData dataclass 测试"""

    def test_wechat_auth_data_creation(self):
        """测试微信授权数据创建"""
        from services.third_party_auth_service import WechatAuthData
        data = WechatAuthData(
            openid="test_openid",
            nickname="测试用户"
        )
        assert data.openid == "test_openid"
        assert data.nickname == "测试用户"

    def test_wechat_auth_data_default_authorized_at(self):
        """测试微信授权数据默认授权时间"""
        from services.third_party_auth_service import WechatAuthData
        data = WechatAuthData(openid="test_openid")
        assert data.authorized_at is not None
        assert isinstance(data.authorized_at, datetime)

    def test_wechat_auth_data_custom_authorized_at(self):
        """测试微信授权数据自定义授权时间"""
        from services.third_party_auth_service import WechatAuthData
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        data = WechatAuthData(openid="test_openid", authorized_at=custom_time)
        assert data.authorized_at == custom_time

    def test_wechat_auth_data_gender_values(self):
        """测试微信授权数据性别值"""
        from services.third_party_auth_service import WechatAuthData
        data_male = WechatAuthData(openid="test", gender=1)
        data_female = WechatAuthData(openid="test", gender=2)
        data_unknown = WechatAuthData(openid="test", gender=0)

        assert data_male.gender == 1
        assert data_female.gender == 2
        assert data_unknown.gender == 0


class TestWechatMomentsData:
    """WechatMomentsData dataclass 测试"""

    def test_wechat_moments_data_creation(self):
        """测试微信朋友圈数据创建"""
        from services.third_party_auth_service import WechatMomentsData
        data = WechatMomentsData(
            posts_count=100,
            interest_tags=["美食", "旅行"]
        )
        assert data.posts_count == 100
        assert "美食" in data.interest_tags

    def test_wechat_moments_data_default_lists(self):
        """测试微信朋友圈数据默认列表"""
        from services.third_party_auth_service import WechatMomentsData
        data = WechatMomentsData(posts_count=10)
        assert data.posts == []
        assert data.interest_tags == []
        assert data.sentiment_summary == {}

    def test_wechat_moments_data_custom_posts(self):
        """测试微信朋友圈数据自定义帖子列表"""
        from services.third_party_auth_service import WechatMomentsData
        posts = [{"id": "1", "content": "test"}]
        data = WechatMomentsData(posts_count=1, posts=posts)
        assert len(data.posts) == 1
        assert data.posts[0]["id"] == "1"


# ============= 第二部分：微信授权流程测试 =============

class TestProcessWechatAuth:
    """微信授权流程测试"""

    @pytest.mark.asyncio
    async def test_process_wechat_auth_success(
        self,
        third_party_auth_service,
        mock_wechat_access_token_response,
        mock_wechat_user_info_response
    ):
        """测试微信授权成功流程"""
        user_id = "test_user_001"
        auth_code = "test_auth_code"

        # Mock httpx.AsyncClient
        with patch('httpx.AsyncClient') as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_client

            # Mock access_token 响应
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = mock_wechat_access_token_response
            mock_client.get.return_value = mock_token_response

            # 先 mock access_token，再 mock user_info
            mock_user_info_response_obj = MagicMock()
            mock_user_info_response_obj.json.return_value = mock_wechat_user_info_response

            # 设置 get 返回不同的响应
            mock_client.get.side_effect = [
                mock_token_response,  # 第一次调用获取 access_token
                mock_user_info_response_obj  # 第二次调用获取用户信息
            ]

            result = await third_party_auth_service.process_wechat_auth(
                user_id=user_id,
                auth_code=auth_code
            )

            assert result is not None
            assert result.user_id == user_id
            assert result.user_consent == True
            assert result.source.value == "wechat_basic"

    @pytest.mark.asyncio
    async def test_process_wechat_auth_with_existing_profile(
        self,
        third_party_auth_service,
        mock_wechat_access_token_response,
        mock_wechat_user_info_response,
        mock_existing_profile
    ):
        """测试微信授权传入已有画像"""
        user_id = "test_user_001"
        auth_code = "test_auth_code"

        with patch('httpx.AsyncClient') as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value.__aenter__.__aenter__ = mock_client

            mock_token_response = MagicMock()
            mock_token_response.json.return_value = mock_wechat_access_token_response

            mock_user_info_response_obj = MagicMock()
            mock_user_info_response_obj.json.return_value = mock_wechat_user_info_response

            mock_client.get.side_effect = [
                mock_token_response,
                mock_user_info_response_obj
            ]

            result = await third_party_auth_service.process_wechat_auth(
                user_id=user_id,
                auth_code=auth_code,
                existing_profile=mock_existing_profile
            )

            assert result.user_id == user_id

    @pytest.mark.asyncio
    async def test_process_wechat_auth_api_error(
        self,
        third_party_auth_service,
        mock_wechat_error_response
    ):
        """测试微信授权 API 错误"""
        user_id = "test_user_001"
        auth_code = "invalid_code"

        with patch('httpx.AsyncClient') as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value.__aenter__.__aenter__ = mock_client

            mock_response = MagicMock()
            mock_response.json.return_value = mock_wechat_error_response
            mock_client.get.return_value = mock_response

            result = await third_party_auth_service.process_wechat_auth(
                user_id=user_id,
                auth_code=auth_code
            )

            # 失败时返回空的推断结果
            assert result is not None
            assert result.user_consent == False

    @pytest.mark.asyncio
    async def test_process_wechat_auth_network_error(self, third_party_auth_service):
        """测试微信授权网络错误"""
        user_id = "test_user_001"
        auth_code = "test_auth_code"

        with patch('httpx.AsyncClient') as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value.__aenter__.__aenter__ = mock_client
            mock_client.get.side_effect = Exception("Network error")

            result = await third_party_auth_service.process_wechat_auth(
                user_id=user_id,
                auth_code=auth_code
            )

            assert result.user_consent == False

    @pytest.mark.asyncio
    async def test_get_wechat_access_token_success(
        self,
        third_party_auth_service,
        mock_wechat_access_token_response
    ):
        """测试获取微信 access_token 成功"""
        auth_code = "test_auth_code"

        # 创建 mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_wechat_access_token_response

        # 创建 async mock client
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch('httpx.AsyncClient') as MockClient:
            # 正确配置 __aenter__ 和 __aexit__
            MockClient.return_value.__aenter__.return_value = mock_client
            MockClient.return_value.__aexit__.return_value = None

            result = await third_party_auth_service._get_wechat_access_token(auth_code)

            assert "access_token" in result
            assert "openid" in result

    @pytest.mark.asyncio
    async def test_get_wechat_access_token_error(
        self,
        third_party_auth_service,
        mock_wechat_error_response
    ):
        """测试获取微信 access_token 错误"""
        auth_code = "invalid_code"

        # 创建 mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_wechat_error_response

        # 创建 async mock client
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch('httpx.AsyncClient') as MockClient:
            MockClient.return_value.__aenter__.return_value = mock_client
            MockClient.return_value.__aexit__.return_value = None

            with pytest.raises(Exception) as exc_info:
                await third_party_auth_service._get_wechat_access_token(auth_code)

            assert "WeChat API error" in str(exc_info.value)


# ============= 第三部分：微信用户信息推断测试 =============

class TestInferFromWechatData:
    """微信用户信息推断测试"""

    @pytest.mark.asyncio
    async def test_infer_from_wechat_data_male(self, third_party_auth_service):
        """测试从微信数据推断男性用户"""
        from services.third_party_auth_service import WechatAuthData
        from models.profile_vector_models import DataSource

        wechat_data = WechatAuthData(
            openid="test_openid",
            nickname="测试用户",
            gender=1,
            province="北京",
            city="北京"
        )

        result = await third_party_auth_service._infer_from_wechat_data(
            user_id="test_user_001",
            wechat_data=wechat_data
        )

        assert result is not None
        assert result.user_id == "test_user_001"
        assert result.source == DataSource.WECHAT_BASIC
        assert 3 in result.dimension_inferences  # 性别维度
        assert result.dimension_inferences[3].value == 0.0  # 男性

    @pytest.mark.asyncio
    async def test_infer_from_wechat_data_female(self, third_party_auth_service):
        """测试从微信数据推断女性用户"""
        from services.third_party_auth_service import WechatAuthData

        wechat_data = WechatAuthData(
            openid="test_openid",
            nickname="Emily",
            gender=2,
            province="上海",
            city="上海"
        )

        result = await third_party_auth_service._infer_from_wechat_data(
            user_id="test_user_002",
            wechat_data=wechat_data
        )

        assert result is not None
        assert 3 in result.dimension_inferences  # 性别维度
        assert result.dimension_inferences[3].value == 1.0  # 女性

    @pytest.mark.asyncio
    async def test_infer_from_wechat_data_tier1_city(self, third_party_auth_service):
        """测试从微信数据推断一线城市用户"""
        from services.third_party_auth_service import WechatAuthData

        wechat_data = WechatAuthData(
            openid="test_openid",
            nickname="北京用户",
            gender=1,
            province="北京",
            city="北京"
        )

        result = await third_party_auth_service._infer_from_wechat_data(
            user_id="test_user_003",
            wechat_data=wechat_data
        )

        assert 6 in result.dimension_inferences  # 城市层级维度
        assert result.dimension_inferences[6].value == 1.0  # 一线城市

    @pytest.mark.asyncio
    async def test_infer_from_wechat_data_tier2_city(self, third_party_auth_service):
        """测试从微信数据推断二线城市用户"""
        from services.third_party_auth_service import WechatAuthData

        wechat_data = WechatAuthData(
            openid="test_openid",
            nickname="杭州用户",
            gender=2,
            province="浙江",
            city="杭州"
        )

        result = await third_party_auth_service._infer_from_wechat_data(
            user_id="test_user_004",
            wechat_data=wechat_data
        )

        assert 6 in result.dimension_inferences  # 城市层级维度
        assert result.dimension_inferences[6].value == 0.7  # 二线城市

    @pytest.mark.asyncio
    async def test_infer_from_wechat_data_with_existing_profile(
        self,
        third_party_auth_service,
        mock_existing_profile
    ):
        """测试从微信数据推断传入已有画像"""
        from services.third_party_auth_service import WechatAuthData

        wechat_data = WechatAuthData(
            openid="test_openid",
            nickname="测试用户",
            gender=1,
            province="北京",
            city="北京"
        )

        result = await third_party_auth_service._infer_from_wechat_data(
            user_id="test_user_001",
            wechat_data=wechat_data,
            existing_profile=mock_existing_profile
        )

        assert result is not None


# ============= 第四部分：昵称分析测试 =============

class TestAnalyzeNickname:
    """昵称分析测试"""

    def test_analyze_nickname_emoji(self, third_party_auth_service):
        """测试包含表情符号的昵称分析"""
        nickname = "测试用户🌸✨"
        result = third_party_auth_service._analyze_nickname(nickname)

        assert result is not None
        assert result.get("emoji_usage") == True

    def test_analyze_nickname_special_chars(self, third_party_auth_service):
        """测试包含特殊字符的昵称分析"""
        nickname = "❤小红❤"
        result = third_party_auth_service._analyze_nickname(nickname)

        assert result is not None
        assert result.get("style") == "cute"

    def test_analyze_nickname_english(self, third_party_auth_service):
        """测试英文昵称分析"""
        nickname = "EmilyRose"
        result = third_party_auth_service._analyze_nickname(nickname)

        assert result is not None
        assert result.get("style") == "english"
        assert result.get("education_hint") == True

    def test_analyze_nickname_plain(self, third_party_auth_service):
        """测试普通昵称分析"""
        nickname = "小明"
        result = third_party_auth_service._analyze_nickname(nickname)

        assert result is not None

    def test_analyze_nickname_empty(self, third_party_auth_service):
        """测试空昵称分析"""
        nickname = ""
        result = third_party_auth_service._analyze_nickname(nickname)

        assert result == {} or result is not None


# ============= 第五部分：地区分析测试 =============

class TestAnalyzeLocation:
    """地区分析测试"""

    def test_analyze_location_tier1_beijing(self, third_party_auth_service):
        """测试北京地区分析"""
        result = third_party_auth_service._analyze_location("北京", "北京")

        assert result is not None
        assert result.get("city_tier") == 1.0
        assert result.get("tier") == "一线"

    def test_analyze_location_tier1_shanghai(self, third_party_auth_service):
        """测试上海地区分析"""
        result = third_party_auth_service._analyze_location("上海", "上海")

        assert result.get("city_tier") == 1.0

    def test_analyze_location_tier2_hangzhou(self, third_party_auth_service):
        """测试杭州地区分析"""
        result = third_party_auth_service._analyze_location("浙江", "杭州")

        assert result.get("city_tier") == 0.7
        assert result.get("tier") == "二线"

    def test_analyze_location_other_city(self, third_party_auth_service):
        """测试其他城市地区分析"""
        result = third_party_auth_service._analyze_location("山东", "潍坊")

        assert result.get("city_tier") == 0.5
        assert result.get("tier") == "其他"


# ============= 第六部分：微信朋友圈数据处理测试 =============

class TestProcessWechatMoments:
    """微信朋友圈数据处理测试"""

    @pytest.mark.asyncio
    async def test_process_wechat_moments_success(
        self,
        third_party_auth_service,
        mock_wechat_moments_data
    ):
        """测试处理微信朋友圈数据成功"""
        result = await third_party_auth_service.process_wechat_moments(
            user_id="test_user_001",
            moments_data=mock_wechat_moments_data
        )

        assert result is not None
        assert result.user_id == "test_user_001"
        assert result.source.value == "wechat_moments"
        assert result.user_consent == True
        assert "interests" in result.inferred_profile

    @pytest.mark.asyncio
    async def test_process_wechat_moments_insufficient_data(
        self,
        third_party_auth_service,
        mock_wechat_moments_minimal_data
    ):
        """测试处理微信朋友圈数据不足"""
        result = await third_party_auth_service.process_wechat_moments(
            user_id="test_user_002",
            moments_data=mock_wechat_moments_minimal_data
        )

        assert result is not None
        assert result.inferred_profile.get("status") == "insufficient_data"

    @pytest.mark.asyncio
    async def test_process_wechat_moments_high_activity(
        self,
        third_party_auth_service,
        mock_wechat_moments_active_data
    ):
        """测试处理高活跃度朋友圈数据"""
        result = await third_party_auth_service.process_wechat_moments(
            user_id="test_user_003",
            moments_data=mock_wechat_moments_active_data
        )

        assert result is not None
        # 高活跃度推断社交活跃度
        assert 40 in result.dimension_inferences  # 社交活跃度维度

    @pytest.mark.asyncio
    async def test_process_wechat_moments_with_sentiment(
        self,
        third_party_auth_service,
        mock_wechat_moments_data
    ):
        """测试处理带情感分析的朋友圈数据"""
        result = await third_party_auth_service.process_wechat_moments(
            user_id="test_user_004",
            moments_data=mock_wechat_moments_data
        )

        assert "sentiment" in result.inferred_profile
        # 情感倾向推断乐观程度
        assert 42 in result.dimension_inferences

    @pytest.mark.asyncio
    async def test_process_wechat_moments_with_interest_tags(
        self,
        third_party_auth_service,
        mock_wechat_moments_data
    ):
        """测试处理带兴趣标签的朋友圈数据"""
        result = await third_party_auth_service.process_wechat_moments(
            user_id="test_user_005",
            moments_data=mock_wechat_moments_data
        )

        assert "interests" in result.inferred_profile
        assert len(result.inferred_profile["interests"]) > 0

    @pytest.mark.asyncio
    async def test_process_wechat_moments_with_existing_profile(
        self,
        third_party_auth_service,
        mock_wechat_moments_data,
        mock_existing_profile
    ):
        """测试处理朋友圈数据传入已有画像"""
        result = await third_party_auth_service.process_wechat_moments(
            user_id="test_user_001",
            moments_data=mock_wechat_moments_data,
            existing_profile=mock_existing_profile
        )

        assert result is not None


# ============= 第七部分：隐私政策测试 =============

class TestGetPrivacyPolicy:
    """隐私政策测试"""

    def test_get_privacy_policy_wechat(self, third_party_auth_service):
        """测试获取微信隐私政策"""
        from services.third_party_auth_service import ThirdPartyProvider

        result = third_party_auth_service.get_privacy_policy(ThirdPartyProvider.WECHAT)

        assert result is not None
        assert result["provider"] == "wechat"
        assert "data_retention_days" in result
        assert "data_usage" in result
        assert "user_rights" in result

    def test_get_privacy_policy_weibo(self, third_party_auth_service):
        """测试获取微博隐私政策"""
        from services.third_party_auth_service import ThirdPartyProvider

        result = third_party_auth_service.get_privacy_policy(ThirdPartyProvider.WEIBO)

        assert result["provider"] == "weibo"

    def test_get_privacy_policy_douban(self, third_party_auth_service):
        """测试获取豆瓣隐私政策"""
        from services.third_party_auth_service import ThirdPartyProvider

        result = third_party_auth_service.get_privacy_policy(ThirdPartyProvider.DOUBAN)

        assert result["provider"] == "douban"

    def test_get_privacy_policy_has_user_rights(self, third_party_auth_service):
        """测试隐私政策包含用户权利"""
        from services.third_party_auth_service import ThirdPartyProvider

        result = third_party_auth_service.get_privacy_policy(ThirdPartyProvider.WECHAT)

        user_rights = result.get("user_rights", [])
        assert len(user_rights) > 0
        assert any("查看" in right for right in user_rights)
        assert any("删除" in right for right in user_rights)


# ============= 第八部分：单例模式测试 =============

class TestSingletonPattern:
    """单例模式测试"""

    def test_get_third_party_auth_service_singleton(self):
        """测试获取单例"""
        from services.third_party_auth_service import (
            get_third_party_auth_service,
            _third_party_auth_service
        )

        # 重置单例
        import services.third_party_auth_service as module
        module._third_party_auth_service = None

        service1 = get_third_party_auth_service()
        service2 = get_third_party_auth_service()

        assert service1 is service2

    def test_singleton_same_instance(self):
        """测试单例返回相同实例"""
        from services.third_party_auth_service import get_third_party_auth_service

        import services.third_party_auth_service as module
        module._third_party_auth_service = None

        instances = [get_third_party_auth_service() for _ in range(10)]

        assert all(inst is instances[0] for inst in instances)

    def test_singleton_reset(self):
        """测试单例重置"""
        from services.third_party_auth_service import (
            get_third_party_auth_service,
            ThirdPartyAuthService
        )

        import services.third_party_auth_service as module
        module._third_party_auth_service = None

        service1 = get_third_party_auth_service()
        module._third_party_auth_service = None
        service2 = get_third_party_auth_service()

        assert service1 is not service2


# ============= 第九部分：异常处理测试 =============

class TestExceptionHandling:
    """异常处理测试"""

    @pytest.mark.asyncio
    async def test_process_wechat_auth_exception_returns_empty_inference(
        self,
        third_party_auth_service
    ):
        """测试微信授权异常返回空推断"""
        with patch.object(
            third_party_auth_service,
            '_get_wechat_access_token',
            side_effect=Exception("Test error")
        ):
            result = await third_party_auth_service.process_wechat_auth(
                user_id="test_user",
                auth_code="test_code"
            )

            assert result.user_consent == False

    @pytest.mark.asyncio
    async def test_get_user_info_api_error(self, third_party_auth_service):
        """测试获取用户信息 API 错误"""
        mock_error_response = {"errcode": 40001, "errmsg": "invalid credential"}

        # 创建 mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_error_response

        # 创建 async mock client
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch('httpx.AsyncClient') as MockClient:
            MockClient.return_value.__aenter__.return_value = mock_client
            MockClient.return_value.__aexit__.return_value = None

            with pytest.raises(Exception) as exc_info:
                await third_party_auth_service._get_wechat_user_info(
                    access_token="invalid_token",
                    openid="test_openid"
                )

            assert "WeChat API error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_infer_from_wechat_data_empty_nickname(self, third_party_auth_service):
        """测试推断空昵称数据"""
        from services.third_party_auth_service import WechatAuthData

        wechat_data = WechatAuthData(
            openid="test_openid",
            nickname=""
        )

        result = await third_party_auth_service._infer_from_wechat_data(
            user_id="test_user",
            wechat_data=wechat_data
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_infer_from_wechat_data_unknown_gender(self, third_party_auth_service):
        """测试推断未知性别数据"""
        from services.third_party_auth_service import WechatAuthData

        wechat_data = WechatAuthData(
            openid="test_openid",
            nickname="测试",
            gender=0  # 未知
        )

        result = await third_party_auth_service._infer_from_wechat_data(
            user_id="test_user",
            wechat_data=wechat_data
        )

        assert result is not None
        # 未知性别不推断性别维度
        assert 3 not in result.dimension_inferences

    @pytest.mark.asyncio
    async def test_process_wechat_moments_empty_interests(self, third_party_auth_service):
        """测试处理空兴趣标签朋友圈"""
        from services.third_party_auth_service import WechatMomentsData

        moments_data = WechatMomentsData(
            posts_count=50,
            interest_tags=[]
        )

        result = await third_party_auth_service.process_wechat_moments(
            user_id="test_user",
            moments_data=moments_data
        )

        assert result is not None


# ============= 第十部分：边界条件测试 =============

class TestEdgeCases:
    """边界条件测试"""

    def test_analyze_nickname_long_name(self, third_party_auth_service):
        """测试长昵称分析"""
        nickname = "这是一个非常非常非常非常非常长的昵称超过二十个字符"
        result = third_party_auth_service._analyze_nickname(nickname)

        assert result is not None

    def test_analyze_location_empty_province_city(self, third_party_auth_service):
        """测试空地区分析"""
        result = third_party_auth_service._analyze_location("", "")

        assert result.get("city_tier") == 0.5
        assert result.get("tier") == "其他"

    def test_analyze_location_partial_city_match(self, third_party_auth_service):
        """测试城市名称部分匹配"""
        # "北京市" 包含 "北京"
        result = third_party_auth_service._analyze_location("北京", "北京市")

        assert result.get("city_tier") == 1.0

    @pytest.mark.asyncio
    async def test_process_wechat_moments_zero_posts(self, third_party_auth_service):
        """测试零帖子朋友圈"""
        from services.third_party_auth_service import WechatMomentsData

        moments_data = WechatMomentsData(posts_count=0)

        result = await third_party_auth_service.process_wechat_moments(
            user_id="test_user",
            moments_data=moments_data
        )

        assert result.inferred_profile.get("status") == "insufficient_data"

    @pytest.mark.asyncio
    async def test_request_moments_permission(self, third_party_auth_service):
        """测试请求朋友圈访问权限"""
        result = await third_party_auth_service.request_moments_permission(
            user_id="test_user_001"
        )

        assert result is not None
        assert "status" in result
        assert "message" in result
        assert "privacy_note" in result

    def test_data_summary_truncates_long_nickname(self, third_party_auth_service):
        """测试数据摘要截断长昵称"""
        from services.third_party_auth_service import WechatAuthData

        wechat_data = WechatAuthData(
            openid="test_openid",
            nickname="这是一个超过二十个字符的长昵称用于测试截断",
            province="北京",
            city="北京"
        )

        # 验证昵称截断逻辑（在推断中）
        import asyncio
        result = asyncio.run(third_party_auth_service._infer_from_wechat_data(
            user_id="test_user",
            wechat_data=wechat_data
        ))

        # data_summary 中昵称应该被截断到20字符
        if result.data_summary:
            summary_data = json.loads(result.data_summary)
            assert len(summary_data.get("nickname", "")) <= 20


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_wechat_auth_flow_mocked(self, third_party_auth_service):
        """测试完整微信授权流程（Mock）"""
        user_id = "integration_test_user"
        auth_code = "integration_test_code"

        mock_token_response = {
            "access_token": "integration_token",
            "openid": "integration_openid"
        }

        mock_user_info = {
            "openid": "integration_openid",
            "nickname": "集成测试用户",
            "sex": 1,
            "province": "北京",
            "city": "北京",
            "headimgurl": "https://example.com/avatar.jpg"
        }

        # 创建 mock responses
        mock_resp1 = MagicMock()
        mock_resp1.json.return_value = mock_token_response

        mock_resp2 = MagicMock()
        mock_resp2.json.return_value = mock_user_info

        # 创建 async mock client
        mock_client = AsyncMock()
        mock_client.get.side_effect = [mock_resp1, mock_resp2]

        with patch('httpx.AsyncClient') as MockClient:
            MockClient.return_value.__aenter__.return_value = mock_client
            MockClient.return_value.__aexit__.return_value = None

            result = await third_party_auth_service.process_wechat_auth(
                user_id=user_id,
                auth_code=auth_code
            )

            assert result.user_id == user_id
            assert result.user_consent == True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])