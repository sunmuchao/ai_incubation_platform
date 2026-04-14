"""
微信登录服务

实现微信开放平台扫码登录流程：
1. 生成登录二维码
2. 处理微信回调
3. 检查扫码登录状态

配置要求：
- 微信开放平台账号（已认证）
- 网站应用 AppID 和 AppSecret
- 配置回调域名

环境变量：
- WECHAT_APP_ID: 微信开放平台 AppID
- WECHAT_APP_SECRET: 微信开放平台 AppSecret
- WECHAT_REDIRECT_URI: 回调地址（需与开放平台配置一致）
"""
import os
import time
import uuid
import hashlib
import requests
from typing import Dict, Optional
from datetime import datetime, timedelta
from utils.logger import logger
from utils.db_session_manager import db_session
from db.models import UserDB


class WeChatLoginState:
    """微信登录状态存储"""

    def __init__(self):
        # 内存存储登录状态（生产环境应使用 Redis）
        self._states: Dict[str, Dict] = {}
        # 状态过期时间（5分钟）
        self._expire_seconds = 300

    def create_state(self) -> str:
        """创建登录状态"""
        state = uuid.uuid4().hex
        self._states[state] = {
            "status": "pending",  # pending/scanned/confirmed/expired
            "user_id": None,
            "created_at": datetime.now(),
        }
        return state

    def get_state(self, state: str) -> Optional[Dict]:
        """获取登录状态"""
        data = self._states.get(state)
        if not data:
            return None

        # 检查是否过期
        if datetime.now() - data["created_at"] > timedelta(seconds=self._expire_seconds):
            data["status"] = "expired"
            return data

        return data

    def update_state(self, state: str, **kwargs) -> None:
        """更新登录状态"""
        if state in self._states:
            self._states[state].update(kwargs)

    def delete_state(self, state: str) -> None:
        """删除登录状态"""
        self._states.pop(state, None)


class WeChatLoginService:
    """微信登录服务"""

    def __init__(self):
        self.app_id = os.getenv("WECHAT_APP_ID", "")
        self.app_secret = os.getenv("WECHAT_APP_SECRET", "")
        # 默认回调地址
        self.redirect_uri = os.getenv(
            "WECHAT_REDIRECT_URI",
            "http://localhost:5173/api/wechat/callback"
        )
        self.state_store = WeChatLoginState()

        if not self.app_id or not self.app_secret:
            logger.warning("WeChat login not configured: missing WECHAT_APP_ID or WECHAT_APP_SECRET")

    def is_configured(self) -> bool:
        """检查微信登录是否已配置"""
        return bool(self.app_id and self.app_secret)

    def get_qrcode_url(self) -> Dict:
        """
        生成微信扫码登录二维码 URL

        Returns:
            {
                "qrcode_url": "二维码图片 URL",
                "state": "状态标识",
                "expires_in": 过期时间（秒）
            }
        """
        if not self.is_configured():
            raise ValueError("微信登录未配置，请联系管理员")

        # 创建登录状态
        state = self.state_store.create_state()

        # 构建微信扫码登录 URL
        # 文档：https://open.weixin.qq.com/cgi-bin/showdocument?action=dir_list&t=resource/res_list&verify=1&id=open1419316505&token=&lang=zh_CN
        base_url = "https://open.weixin.qq.com/connect/qrconnect"

        params = {
            "appid": self.app_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "snsapi_login",  # snsapi_login 为扫码登录
            "state": state,
            # 可选：自定义样式
            # "style": "black",
            # "href": "自定义 CSS URL",
        }

        # 构建 URL
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        qr_url = f"{base_url}?{query_string}#wechat_redirect"

        logger.info(f"Created WeChat login state: {state}")

        return {
            "qrcode_url": qr_url,
            "state": state,
            "expires_in": 300,  # 5分钟过期
        }

    def check_login_status(self, state: str) -> Dict:
        """
        检查扫码登录状态（轮询接口）

        Args:
            state: 登录状态标识

        Returns:
            {
                "status": "pending/scanned/confirmed/expired",
                "user_id": "用户 ID（仅 confirmed 时）",
                "token": "登录令牌（仅 confirmed 时）"
            }
        """
        state_data = self.state_store.get_state(state)

        if not state_data:
            return {
                "status": "invalid",
                "message": "无效的登录状态",
            }

        return {
            "status": state_data["status"],
            "user_id": state_data.get("user_id"),
            "token": state_data.get("token"),
        }

    def handle_callback(self, code: str, state: str) -> Dict:
        """
        处理微信回调

        当用户扫码确认后，微信会回调此接口，携带 code 和 state。

        Args:
            code: 微信授权码
            state: 登录状态标识

        Returns:
            处理结果
        """
        # 验证 state
        state_data = self.state_store.get_state(state)
        if not state_data:
            logger.warning(f"Invalid WeChat login state: {state}")
            return {"success": False, "message": "无效的登录状态"}

        if state_data["status"] == "expired":
            return {"success": False, "message": "登录已过期，请重新扫码"}

        # 更新状态为已扫描
        self.state_store.update_state(state, status="scanned")

        try:
            # 1. 使用 code 换取 access_token
            token_data = self._get_access_token(code)
            access_token = token_data.get("access_token")
            openid = token_data.get("openid")
            unionid = token_data.get("unionid")

            if not access_token or not openid:
                raise ValueError("获取 access_token 失败")

            # 2. 获取用户信息
            user_info = self._get_user_info(access_token, openid)

            # 3. 创建或查找用户
            user, token = self._create_or_get_user(user_info, openid, unionid)

            # 4. 更新登录状态
            self.state_store.update_state(
                state,
                status="confirmed",
                user_id=user.id,
                token=token,
            )

            logger.info(f"WeChat login success: openid={openid}, user_id={user.id}")

            return {
                "success": True,
                "user_id": user.id,
                "token": token,
            }

        except Exception as e:
            logger.error(f"WeChat login callback failed: {e}")
            self.state_store.update_state(state, status="failed")
            return {
                "success": False,
                "message": str(e),
            }

    def _get_access_token(self, code: str) -> Dict:
        """
        使用 code 换取 access_token

        文档：https://open.weixin.qq.com/cgi-bin/showdocument?action=dir_list&t=resource/res_list&verify=1&id=open1419316505&token=&lang=zh_CN
        """
        url = "https://api.weixin.qq.com/sns/oauth2/access_token"

        params = {
            "appid": self.app_id,
            "secret": self.app_secret,
            "code": code,
            "grant_type": "authorization_code",
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if "errcode" in data:
            raise ValueError(f"WeChat API error: {data.get('errmsg', 'Unknown error')}")

        return data

    def _get_user_info(self, access_token: str, openid: str) -> Dict:
        """
        获取微信用户信息

        文档：https://open.weixin.qq.com/cgi-bin/showdocument?action=dir_list&t=resource/res_list&verify=1&id=open1419316518&token=&lang=zh_CN
        """
        url = "https://api.weixin.qq.com/sns/userinfo"

        params = {
            "access_token": access_token,
            "openid": openid,
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if "errcode" in data:
            raise ValueError(f"WeChat API error: {data.get('errmsg', 'Unknown error')}")

        return data

    def _create_or_get_user(self, wechat_user: Dict, openid: str, unionid: Optional[str]) -> tuple:
        """
        创建或获取用户

        如果用户已存在（通过 openid 或 unionid 匹配），返回已有用户。
        否则创建新用户。

        Args:
            wechat_user: 微信用户信息
            openid: 微信 openid
            unionid: 微信 unionid（可选）

        Returns:
            (UserDB, token)
        """
        from auth.jwt import create_access_token

        with db_session() as db:
            # 查找已有用户（通过 wechat_openid）
            user = db.query(UserDB).filter(
                UserDB.wechat_openid == openid
            ).first()

            if not user and unionid:
                # 尝试通过 unionid 查找
                user = db.query(UserDB).filter(
                    UserDB.wechat_unionid == unionid
                ).first()

            if user:
                # 已有用户，更新信息
                user.last_login = datetime.now()
                db.commit()
            else:
                # 创建新用户
                nickname = wechat_user.get("nickname", f"微信用户_{openid[-6:]}")
                headimgurl = wechat_user.get("headimgurl", "")
                sex = wechat_user.get("sex", 0)  # 0-未知, 1-男, 2-女

                user = UserDB(
                    id=f"wechat-{uuid.uuid4().hex[:12]}",
                    username=f"wechat_{openid[-8:]}",
                    name=nickname,
                    # 微信用户默认密码为随机值，用户需后续设置
                    password=hashlib.sha256(uuid.uuid4().hex.encode()).hexdigest(),
                    email=f"{openid}@wechat.placeholder",  # 占位邮箱
                    gender="male" if sex == 1 else "female" if sex == 2 else "unknown",
                    age=0,  # 微信不提供年龄
                    location=wechat_user.get("city", ""),
                    avatar_url=headimgurl,
                    wechat_openid=openid,
                    wechat_unionid=unionid,
                    created_at=datetime.now(),
                    last_login=datetime.now(),
                )

                db.add(user)
                db.commit()
                db.refresh(user)

                logger.info(f"Created new user from WeChat: {user.id}")

            # 生成 JWT token
            token = create_access_token({"sub": user.id, "username": user.username or user.name})

            return user, token


# 全局实例
wechat_login_service = WeChatLoginService()