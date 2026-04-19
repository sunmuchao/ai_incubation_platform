"""
微信登录服务集成测试

测试 WeChatLoginService 的核心功能：
- 登录状态管理
- 二维码生成
- 登录状态检查
- 回调处理
- 用户创建与查找
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
import uuid
import hashlib

# 尝试导入服务模块
try:
    from services.wechat_login_service import (
        WeChatLoginService,
        WeChatLoginState,
        wechat_login_service,
    )
except ImportError:
    pytest.skip("wechat_login_service not importable", allow_module_level=True)


class TestWeChatLoginState:
    """微信登录状态管理测试"""

    def test_create_state(self):
        """测试创建登录状态"""
        state_store = WeChatLoginState()

        state = state_store.create_state()

        assert state is not None
        assert isinstance(state, str)
        assert len(state) == 32  # UUID hex

        # 状态应存储
        assert state in state_store._states
        assert state_store._states[state]["status"] == "pending"

    def test_get_state_pending(self):
        """测试获取 pending 状态"""
        state_store = WeChatLoginState()

        state = state_store.create_state()
        data = state_store.get_state(state)

        assert data is not None
        assert data["status"] == "pending"
        assert data["user_id"] is None

    def test_get_state_expired(self):
        """测试获取过期状态"""
        state_store = WeChatLoginState()

        state = state_store.create_state()

        # 手动设置为过期时间
        state_store._states[state]["created_at"] = datetime.now() - timedelta(seconds=400)

        data = state_store.get_state(state)

        assert data["status"] == "expired"

    def test_get_state_not_found(self):
        """测试获取不存在的状态"""
        state_store = WeChatLoginState()

        data = state_store.get_state("nonexistent_state")

        assert data is None

    def test_update_state(self):
        """测试更新状态"""
        state_store = WeChatLoginState()

        state = state_store.create_state()
        state_store.update_state(state, status="scanned", user_id="user_001")

        data = state_store.get_state(state)

        assert data["status"] == "scanned"
        assert data["user_id"] == "user_001"

    def test_update_nonexistent_state(self):
        """测试更新不存在的状态"""
        state_store = WeChatLoginState()

        # 应不报错
        state_store.update_state("nonexistent", status="scanned")

        assert "nonexistent" not in state_store._states

    def test_delete_state(self):
        """测试删除状态"""
        state_store = WeChatLoginState()

        state = state_store.create_state()
        state_store.delete_state(state)

        assert state not in state_store._states

    def test_delete_nonexistent_state(self):
        """测试删除不存在的状态"""
        state_store = WeChatLoginState()

        # 应不报错
        state_store.delete_state("nonexistent")

    def test_state_expire_seconds(self):
        """测试状态过期时间"""
        state_store = WeChatLoginState()

        assert state_store._expire_seconds == 300  # 5分钟


class TestWeChatLoginServiceInit:
    """微信登录服务初始化测试"""

    def test_service_initialization(self):
        """测试服务初始化"""
        with patch.dict('os.environ', {
            'WECHAT_APP_ID': 'test_app_id',
            'WECHAT_APP_SECRET': 'test_app_secret',
            'WECHAT_REDIRECT_URI': 'http://test.com/callback'
        }):
            service = WeChatLoginService()

            assert service.app_id == 'test_app_id'
            assert service.app_secret == 'test_app_secret'
            assert service.redirect_uri == 'http://test.com/callback'
            assert service.state_store is not None

    def test_service_without_config(self):
        """测试未配置环境变量"""
        # 清除环境变量
        with patch.dict('os.environ', {}, clear=True):
            service = WeChatLoginService()

            assert service.app_id == ""
            assert service.app_secret == ""
            assert not service.is_configured()

    def test_is_configured_true(self):
        """测试已配置"""
        with patch.dict('os.environ', {
            'WECHAT_APP_ID': 'test_app_id',
            'WECHAT_APP_SECRET': 'test_app_secret'
        }):
            service = WeChatLoginService()

            assert service.is_configured() is True

    def test_is_configured_false(self):
        """测试未配置"""
        with patch.dict('os.environ', {}, clear=True):
            service = WeChatLoginService()

            assert service.is_configured() is False


class TestGetQRCodeURL:
    """二维码 URL 生成测试"""

    def test_get_qrcode_url_success(self):
        """测试生成二维码 URL"""
        with patch.dict('os.environ', {
            'WECHAT_APP_ID': 'test_app_id',
            'WECHAT_APP_SECRET': 'test_app_secret',
            'WECHAT_REDIRECT_URI': 'http://test.com/callback'
        }):
            service = WeChatLoginService()

            result = service.get_qrcode_url()

            assert "qrcode_url" in result
            assert "state" in result
            assert "expires_in" in result

            assert result["qrcode_url"].startswith("https://open.weixin.qq.com/connect/qrconnect")
            assert "appid=test_app_id" in result["qrcode_url"]
            assert result["expires_in"] == 300

    def test_get_qrcode_url_not_configured(self):
        """测试未配置时生成二维码"""
        with patch.dict('os.environ', {}, clear=True):
            service = WeChatLoginService()

            with pytest.raises(ValueError, match="微信登录未配置"):
                service.get_qrcode_url()

    def test_qrcode_url_contains_correct_params(self):
        """测试二维码 URL 包含正确参数"""
        with patch.dict('os.environ', {
            'WECHAT_APP_ID': 'wx12345678',
            'WECHAT_APP_SECRET': 'secret123',
            'WECHAT_REDIRECT_URI': 'http://localhost:5173/api/wechat/callback'
        }):
            service = WeChatLoginService()

            result = service.get_qrcode_url()

            url = result["qrcode_url"]
            assert "appid=wx12345678" in url
            assert "redirect_uri=http://localhost:5173/api/wechat/callback" in url
            assert "response_type=code" in url
            assert "scope=snsapi_login" in url
            assert "#wechat_redirect" in url


class TestCheckLoginStatus:
    """登录状态检查测试"""

    def test_check_status_pending(self):
        """测试检查 pending 状态"""
        with patch.dict('os.environ', {
            'WECHAT_APP_ID': 'test_app_id',
            'WECHAT_APP_SECRET': 'test_app_secret'
        }):
            service = WeChatLoginService()

            state = service.state_store.create_state()
            result = service.check_login_status(state)

            assert result["status"] == "pending"
            assert result["user_id"] is None
            assert result["token"] is None

    def test_check_status_confirmed(self):
        """测试检查 confirmed 状态"""
        with patch.dict('os.environ', {
            'WECHAT_APP_ID': 'test_app_id',
            'WECHAT_APP_SECRET': 'test_app_secret'
        }):
            service = WeChatLoginService()

            state = service.state_store.create_state()
            service.state_store.update_state(
                state,
                status="confirmed",
                user_id="user_001",
                token="test_token"
            )

            result = service.check_login_status(state)

            assert result["status"] == "confirmed"
            assert result["user_id"] == "user_001"
            assert result["token"] == "test_token"

    def test_check_status_invalid(self):
        """测试检查无效状态"""
        with patch.dict('os.environ', {
            'WECHAT_APP_ID': 'test_app_id',
            'WECHAT_APP_SECRET': 'test_app_secret'
        }):
            service = WeChatLoginService()

            result = service.check_login_status("invalid_state")

            assert result["status"] == "invalid"
            assert "message" in result

    def test_check_status_expired(self):
        """测试检查过期状态"""
        with patch.dict('os.environ', {
            'WECHAT_APP_ID': 'test_app_id',
            'WECHAT_APP_SECRET': 'test_app_secret'
        }):
            service = WeChatLoginService()

            state = service.state_store.create_state()
            # 设置为过期
            service.state_store._states[state]["created_at"] = datetime.now() - timedelta(seconds=400)

            result = service.check_login_status(state)

            assert result["status"] == "expired"


class TestHandleCallback:
    """回调处理测试"""

    def test_handle_callback_invalid_state(self):
        """测试无效 state 回调"""
        with patch.dict('os.environ', {
            'WECHAT_APP_ID': 'test_app_id',
            'WECHAT_APP_SECRET': 'test_app_secret'
        }):
            service = WeChatLoginService()

            result = service.handle_callback("test_code", "invalid_state")

            assert result["success"] is False
            assert "无效的登录状态" in result["message"]

    def test_handle_callback_expired_state(self):
        """测试过期 state 回调"""
        with patch.dict('os.environ', {
            'WECHAT_APP_ID': 'test_app_id',
            'WECHAT_APP_SECRET': 'test_app_secret'
        }):
            service = WeChatLoginService()

            state = service.state_store.create_state()
            service.state_store._states[state]["created_at"] = datetime.now() - timedelta(seconds=400)

            result = service.handle_callback("test_code", state)

            assert result["success"] is False
            assert "过期" in result["message"]

    def test_handle_callback_success(self):
        """测试成功回调"""
        with patch.dict('os.environ', {
            'WECHAT_APP_ID': 'test_app_id',
            'WECHAT_APP_SECRET': 'test_app_secret'
        }):
            service = WeChatLoginService()

            state = service.state_store.create_state()

            # Mock 外部 API 调用
            with patch.object(service, '_get_access_token') as mock_token:
                mock_token.return_value = {
                    "access_token": "test_access_token",
                    "openid": "test_openid",
                    "unionid": "test_unionid"
                }

                with patch.object(service, '_get_user_info') as mock_user_info:
                    mock_user_info.return_value = {
                        "nickname": "测试用户",
                        "headimgurl": "http://test.com/avatar.jpg",
                        "sex": 1
                    }

                    with patch.object(service, '_create_or_get_user') as mock_create:
                        mock_user = MagicMock()
                        mock_user.id = "wechat-test123"
                        mock_create.return_value = (mock_user, "test_jwt_token")

                        result = service.handle_callback("test_code", state)

                        assert result["success"] is True
                        assert result["user_id"] == "wechat-test123"
                        assert result["token"] == "test_jwt_token"

                        # 状态应更新为 confirmed
                        state_data = service.state_store.get_state(state)
                        assert state_data["status"] == "confirmed"

    def test_handle_callback_api_failure(self):
        """测试 API 调用失败"""
        with patch.dict('os.environ', {
            'WECHAT_APP_ID': 'test_app_id',
            'WECHAT_APP_SECRET': 'test_app_secret'
        }):
            service = WeChatLoginService()

            state = service.state_store.create_state()

            with patch.object(service, '_get_access_token') as mock_token:
                mock_token.side_effect = ValueError("WeChat API error")

                result = service.handle_callback("test_code", state)

                assert result["success"] is False
                assert "message" in result

                # 状态应更新为 failed
                state_data = service.state_store.get_state(state)
                assert state_data["status"] == "failed"


class TestGetAccessToken:
    """获取 Access Token 测试"""

    def test_get_access_token_success(self):
        """测试成功获取 token"""
        with patch.dict('os.environ', {
            'WECHAT_APP_ID': 'test_app_id',
            'WECHAT_APP_SECRET': 'test_app_secret'
        }):
            service = WeChatLoginService()

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "access_token": "ACCESS_TOKEN",
                "expires_in": 7200,
                "refresh_token": "REFRESH_TOKEN",
                "openid": "OPENID",
                "unionid": "UNIONID"
            }
            mock_response.raise_for_status = MagicMock()

            with patch('requests.get', return_value=mock_response):
                result = service._get_access_token("test_code")

                assert result["access_token"] == "ACCESS_TOKEN"
                assert result["openid"] == "OPENID"
                assert result["unionid"] == "UNIONID"

    def test_get_access_token_error_response(self):
        """测试错误响应"""
        with patch.dict('os.environ', {
            'WECHAT_APP_ID': 'test_app_id',
            'WECHAT_APP_SECRET': 'test_app_secret'
        }):
            service = WeChatLoginService()

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "errcode": 40029,
                "errmsg": "invalid code"
            }
            mock_response.raise_for_status = MagicMock()

            with patch('requests.get', return_value=mock_response):
                with pytest.raises(ValueError, match="WeChat API error"):
                    service._get_access_token("invalid_code")


class TestGetUserInfo:
    """获取用户信息测试"""

    def test_get_user_info_success(self):
        """测试成功获取用户信息"""
        with patch.dict('os.environ', {
            'WECHAT_APP_ID': 'test_app_id',
            'WECHAT_APP_SECRET': 'test_app_secret'
        }):
            service = WeChatLoginService()

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "openid": "OPENID",
                "nickname": "测试用户",
                "sex": 1,
                "province": "北京",
                "city": "北京",
                "country": "中国",
                "headimgurl": "http://test.com/avatar.jpg",
                "privilege": [],
                "unionid": "UNIONID"
            }
            mock_response.raise_for_status = MagicMock()

            with patch('requests.get', return_value=mock_response):
                result = service._get_user_info("test_token", "test_openid")

                assert result["nickname"] == "测试用户"
                assert result["sex"] == 1
                assert result["city"] == "北京"

    def test_get_user_info_error_response(self):
        """测试错误响应"""
        with patch.dict('os.environ', {
            'WECHAT_APP_ID': 'test_app_id',
            'WECHAT_APP_SECRET': 'test_app_secret'
        }):
            service = WeChatLoginService()

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "errcode": 40001,
                "errmsg": "invalid credential"
            }
            mock_response.raise_for_status = MagicMock()

            with patch('requests.get', return_value=mock_response):
                with pytest.raises(ValueError, match="WeChat API error"):
                    service._get_user_info("invalid_token", "test_openid")


class TestCreateOrGetUser:
    """创建或获取用户测试"""

    def test_create_new_user(self):
        """测试创建新用户"""
        with patch.dict('os.environ', {
            'WECHAT_APP_ID': 'test_app_id',
            'WECHAT_APP_SECRET': 'test_app_secret'
        }):
            service = WeChatLoginService()

            wechat_user = {
                "nickname": "微信用户",
                "sex": 1,
                "city": "上海",
                "headimgurl": "http://wx.com/avatar.jpg"
            }

            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = None

            mock_new_user = MagicMock()
            mock_new_user.id = "wechat-abc123def456"

            mock_db.add = MagicMock()
            mock_db.commit = MagicMock()
            mock_db.refresh = MagicMock()

            with patch('services.wechat_login_service.db_session') as mock_session:
                mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
                mock_session.return_value.__exit__ = MagicMock(return_value=False)

                with patch('auth.jwt.create_access_token', return_value="jwt_token"):
                    # 模拟 UserDB 创建
                    with patch('services.wechat_login_service.UserDB') as mock_user_class:
                        mock_user_class.return_value = mock_new_user

                        user, token = service._create_or_get_user(wechat_user, "openid123", "unionid123")

                        assert token == "jwt_token"
                        # 应创建新用户
                        assert mock_db.add.called

    def test_get_existing_user_by_openid(self):
        """测试通过 openid 查找已有用户"""
        with patch.dict('os.environ', {
            'WECHAT_APP_ID': 'test_app_id',
            'WECHAT_APP_SECRET': 'test_app_secret'
        }):
            service = WeChatLoginService()

            mock_existing_user = MagicMock()
            mock_existing_user.id = "existing_user_001"
            mock_existing_user.username = "wechat_user"
            mock_existing_user.name = "已有用户"

            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = mock_existing_user
            mock_db.commit = MagicMock()

            with patch('services.wechat_login_service.db_session') as mock_session:
                mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
                mock_session.return_value.__exit__ = MagicMock(return_value=False)

                with patch('auth.jwt.create_access_token', return_value="jwt_token_for_existing"):
                    user, token = service._create_or_get_user({}, "openid123", None)

                    assert token == "jwt_token_for_existing"
                    # 应更新 last_login
                    assert mock_db.commit.called

    def test_get_existing_user_by_unionid(self):
        """测试通过 unionid 查找已有用户"""
        with patch.dict('os.environ', {
            'WECHAT_APP_ID': 'test_app_id',
            'WECHAT_APP_SECRET': 'test_app_secret'
        }):
            service = WeChatLoginService()

            mock_existing_user = MagicMock()
            mock_existing_user.id = "existing_user_unionid"

            mock_db = MagicMock()

            # 第一次查询 openid 返回 None
            first_query = MagicMock()
            first_query.filter.return_value.first.return_value = None

            # 第二次查询 unionid 返回用户
            second_query = MagicMock()
            second_query.filter.return_value.first.return_value = mock_existing_user

            mock_db.query.side_effect = [first_query, second_query]
            mock_db.commit = MagicMock()

            with patch('services.wechat_login_service.db_session') as mock_session:
                mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
                mock_session.return_value.__exit__ = MagicMock(return_value=False)

                with patch('auth.jwt.create_access_token', return_value="jwt_token_unionid"):
                    user, token = service._create_or_get_user({}, "openid123", "unionid123")

                    assert token == "jwt_token_unionid"


class TestGlobalInstance:
    """全局实例测试"""

    def test_global_instance_exists(self):
        """测试全局实例存在"""
        # 全局实例应存在（即使环境变量未配置）
        assert wechat_login_service is not None
        assert isinstance(wechat_login_service, WeChatLoginService)

    def test_global_instance_state_store(self):
        """测试全局实例状态存储"""
        assert wechat_login_service.state_store is not None
        assert isinstance(wechat_login_service.state_store, WeChatLoginState)


class TestEdgeCases:
    """边界值测试"""

    def test_state_expiry_boundary(self):
        """测试状态过期边界"""
        state_store = WeChatLoginState()

        state = state_store.create_state()

        # 刚好 5 分钟（300秒）内，不应过期
        state_store._states[state]["created_at"] = datetime.now() - timedelta(seconds=299)
        data = state_store.get_state(state)
        assert data["status"] == "pending"

        # 超过 5 分钟，应过期
        state_store._states[state]["created_at"] = datetime.now() - timedelta(seconds=301)
        data = state_store.get_state(state)
        assert data["status"] == "expired"

    def test_empty_wechat_user_info(self):
        """测试空微信用户信息"""
        with patch.dict('os.environ', {
            'WECHAT_APP_ID': 'test_app_id',
            'WECHAT_APP_SECRET': 'test_app_secret'
        }):
            service = WeChatLoginService()

            # 空 dict，应使用默认值
            wechat_user = {}

            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = None

            mock_new_user = MagicMock()
            mock_new_user.id = "wechat-new"

            with patch('services.wechat_login_service.db_session') as mock_session:
                mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
                mock_session.return_value.__exit__ = MagicMock(return_value=False)

                with patch('auth.jwt.create_access_token', return_value="token"):
                    with patch('services.wechat_login_service.UserDB') as mock_user_class:
                        mock_user_class.return_value = mock_new_user

                        user, token = service._create_or_get_user(wechat_user, "openid123", None)

                        # 应创建用户
                        assert mock_user_class.called

    def test_sex_field_mapping(self):
        """测试性别字段映射"""
        # sex: 0-未知, 1-男, 2-女
        with patch.dict('os.environ', {
            'WECHAT_APP_ID': 'test_app_id',
            'WECHAT_APP_SECRET': 'test_app_secret'
        }):
            service = WeChatLoginService()

            # 测试男性
            wechat_user_male = {"sex": 1}

            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = None

            with patch('services.wechat_login_service.db_session') as mock_session:
                mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
                mock_session.return_value.__exit__ = MagicMock(return_value=False)

                with patch('auth.jwt.create_access_token', return_value="token"):
                    with patch('services.wechat_login_service.UserDB') as mock_user_class:
                        mock_user_class.return_value = MagicMock()

                        service._create_or_get_user(wechat_user_male, "openid_male", None)

                        # 检查 UserDB 调用参数
                        call_kwargs = mock_user_class.call_args[1]
                        assert call_kwargs["gender"] == "male"

    def test_state_uuid_format(self):
        """测试状态 UUID 格式"""
        state_store = WeChatLoginState()

        state = state_store.create_state()

        # 应为 32 字符 hex
        assert len(state) == 32
        # 应为有效 hex
        assert all(c in '0123456789abcdef' for c in state)

    def test_multiple_states(self):
        """测试多个并发状态"""
        state_store = WeChatLoginState()

        states = [state_store.create_state() for _ in range(10)]

        # 所有状态应独立存在
        assert len(state_store._states) == 10

        for state in states:
            data = state_store.get_state(state)
            assert data["status"] == "pending"

    def test_default_redirect_uri(self):
        """测试默认回调地址"""
        with patch.dict('os.environ', {
            'WECHAT_APP_ID': 'test_app_id',
            'WECHAT_APP_SECRET': 'test_app_secret'
        }, clear=True):
            service = WeChatLoginService()

            # 应有默认值
            assert service.redirect_uri == "http://localhost:5173/api/wechat/callback"