"""
P9 多平台/小程序集成 - 服务层实现

提供多平台集成的核心业务逻辑：
- 平台认证服务 (微信/支付宝登录)
- 平台账号同步服务
- 平台订单管理服务
- 平台通知推送服务
- 平台配置管理服务
"""

import json
import hashlib
import hmac
import base64
import time
import requests
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from uuid import uuid4
import logging

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models.p9_entities import (
    PlatformAccountEntity,
    PlatformOrderEntity,
    PlatformNotificationEntity,
    PlatformConfigEntity,
    PlatformSyncLogEntity,
)
from models.p9_models import (
    PlatformType,
    PlatformLoginRequest,
    PlatformLoginResponse,
    PlatformBindRequest,
    PlatformBindResponse,
    PlatformOrderCreate,
    PlatformOrderUpdate,
    PlatformOrderResponse,
    PlatformNotificationCreate,
    PlatformNotificationSendRequest,
    PlatformNotificationResponse,
    PlatformConfigCreate,
    PlatformConfigUpdate,
    PlatformSyncLogCreate,
    OrderStatus,
    PaymentStatus,
    SyncStatus,
    SyncDirection,
    SyncAction,
    SendStatus,
)

logger = logging.getLogger(__name__)


# ============= 平台认证适配器 =============

class PlatformAuthAdapter:
    """平台认证适配器基类"""

    def __init__(self, app_id: str, app_secret: str, **kwargs):
        self.app_id = app_id
        self.app_secret = app_secret
        self.config = kwargs

    def get_access_token(self) -> str:
        """获取平台访问令牌"""
        raise NotImplementedError

    def code_to_session(self, code: str) -> Dict[str, Any]:
        """使用登录 code 换取会话信息"""
        raise NotImplementedError

    def decrypt_user_info(self, encrypted_data: str, iv: str, session_key: str) -> Dict[str, Any]:
        """解密用户信息"""
        raise NotImplementedError

    def send_notification(self, recipient: str, template_id: str, content: Dict[str, Any],
                          page_path: Optional[str] = None) -> Tuple[bool, str]:
        """发送平台通知"""
        raise NotImplementedError


class WechatAuthAdapter(PlatformAuthAdapter):
    """微信小程序认证适配器"""

    API_BASE = "https://api.weixin.qq.com"

    def get_access_token(self) -> str:
        """获取微信小程序全局 access_token"""
        url = f"{self.API_BASE}/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.app_id,
            "secret": self.app_secret
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            result = response.json()
            if "access_token" in result:
                return result["access_token"]
            else:
                logger.error(f"获取微信 access_token 失败：{result}")
                raise Exception(f"微信 API 错误：{result.get('errmsg', 'unknown error')}")
        except Exception as e:
            logger.error(f"获取微信 access_token 异常：{e}")
            raise

    def code_to_session(self, code: str) -> Dict[str, Any]:
        """使用微信登录 code 换取会话信息"""
        url = f"{self.API_BASE}/sns/jscode2session"
        params = {
            "appid": self.app_id,
            "secret": self.app_secret,
            "js_code": code,
            "grant_type": "authorization_code"
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            result = response.json()
            if "openid" in result:
                return {
                    "openid": result["openid"],
                    "unionid": result.get("unionid"),
                    "session_key": result["session_key"],
                }
            else:
                logger.error(f"微信 code2session 失败：{result}")
                raise Exception(f"微信 API 错误：{result.get('errmsg', 'unknown error')}")
        except Exception as e:
            logger.error(f"微信 code2session 异常：{e}")
            raise

    def decrypt_user_info(self, encrypted_data: str, iv: str, session_key: str) -> Dict[str, Any]:
        """解密微信用户信息"""
        try:
            from Crypto.Cipher import AES
            import base64
            import json

            session_key_bytes = base64.b64decode(session_key)
            encrypted_data_bytes = base64.b64decode(encrypted_data)
            iv_bytes = base64.b64decode(iv)

            cipher = AES.new(session_key_bytes, AES.MODE_CBC, iv_bytes)
            decrypted = cipher.decrypt(encrypted_data_bytes)

            # 去除 padding
            pad = decrypted[-1]
            decrypted = decrypted[:-pad]

            user_info = json.loads(decrypted.decode('utf-8'))
            return user_info
        except Exception as e:
            logger.error(f"解密微信用户信息失败：{e}")
            raise Exception(f"解密失败：{str(e)}")

    def send_notification(self, recipient: str, template_id: str, content: Dict[str, Any],
                          page_path: Optional[str] = None) -> Tuple[bool, str]:
        """发送微信订阅消息"""
        try:
            access_token = self.get_access_token()
            url = f"{self.API_BASE}/cgi-bin/message/subscribe/send"

            # 构建消息数据
            data = {
                "touser": recipient,
                "template_id": template_id,
                "page": page_path or "pages/index/index",
                "miniprogram_state": "formal",  # formal, trial, develop
                "lang": "zh_CN",
                "data": content
            }

            response = requests.post(url, json=data, params={"access_token": access_token}, timeout=10)
            result = response.json()

            if result.get("errcode", 0) == 0:
                return True, "发送成功"
            else:
                return False, f"微信 API 错误：{result.get('errmsg', 'unknown error')}"
        except Exception as e:
            logger.error(f"发送微信通知异常：{e}")
            return False, str(e)


class AlipayAuthAdapter(PlatformAuthAdapter):
    """支付宝小程序认证适配器"""

    API_BASE = "https://openapi.alipay.com/gateway.do"

    def __init__(self, app_id: str, app_secret: str, **kwargs):
        super().__init__(app_id, app_secret, **kwargs)
        self.mch_id = kwargs.get("mch_id")
        self.cert_path = kwargs.get("cert_path")
        self.key_path = kwargs.get("key_path")

    def _sign(self, params: Dict[str, Any]) -> str:
        """支付宝签名"""
        # 简化签名实现，实际生产环境需要完整实现
        sign_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()) if v)
        signature = hmac.new(
            self.app_secret.encode('utf-8'),
            sign_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def get_access_token(self) -> str:
        """获取支付宝 access_token"""
        # 简化实现，实际需要使用系统级 access_token
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        params = {
            "app_id": self.app_id,
            "method": "alipay.system.oauth.token",
            "timestamp": timestamp,
            "format": "json",
            "charset": "utf-8",
            "sign_type": "RSA2",
        }
        # 实际生产环境需要完整实现
        return "alipay_access_token_placeholder"

    def code_to_session(self, code: str) -> Dict[str, Any]:
        """使用支付宝登录 code 换取用户信息"""
        # 简化实现
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        params = {
            "app_id": self.app_id,
            "method": "alipay.user.info.share",
            "timestamp": timestamp,
            "format": "json",
            "charset": "utf-8",
            "auth_token": code,
        }
        params["sign"] = self._sign(params)

        try:
            response = requests.post(self.API_BASE, data=params, timeout=10)
            result = response.json()

            # 解析响应
            api_response = result.get("alipay_user_info_share_response", {})
            if api_response.get("code") == "10000":
                return {
                    "user_id": api_response.get("user_id"),
                    "avatar": api_response.get("avatar"),
                    "nick_name": api_response.get("nick_name"),
                    "gender": api_response.get("gender"),
                }
            else:
                raise Exception(f"支付宝 API 错误：{api_response.get('sub_msg', 'unknown error')}")
        except Exception as e:
            logger.error(f"支付宝 code2session 异常：{e}")
            raise

    def decrypt_user_info(self, encrypted_data: str, iv: str, session_key: str) -> Dict[str, Any]:
        """支付宝通常不需要解密用户信息"""
        return json.loads(encrypted_data) if encrypted_data else {}

    def send_notification(self, recipient: str, template_id: str, content: Dict[str, Any],
                          page_path: Optional[str] = None) -> Tuple[bool, str]:
        """发送支付宝模板消息"""
        # 简化实现
        try:
            # 实际生产环境需要调用支付宝模板消息 API
            logger.info(f"发送支付宝模板消息给 {recipient}, 模板 {template_id}")
            return True, "发送成功 (模拟)"
        except Exception as e:
            logger.error(f"发送支付宝通知异常：{e}")
            return False, str(e)


# ============= 平台认证服务 =============

class PlatformAuthService:
    """平台认证服务"""

    def __init__(self, db: Session):
        self.db = db
        self._adapters: Dict[str, PlatformAuthAdapter] = {}

    def _get_adapter(self, platform: str) -> Optional[PlatformAuthAdapter]:
        """获取平台认证适配器"""
        if platform in self._adapters:
            return self._adapters[platform]

        # 从数据库加载配置
        config = self.db.query(PlatformConfigEntity).filter(
            PlatformConfigEntity.platform == platform,
            PlatformConfigEntity.is_enabled == True
        ).first()

        if not config:
            logger.warning(f"平台 {platform} 配置未找到或未启用")
            return None

        # 创建适配器
        if platform == PlatformType.WECHAT.value:
            adapter = WechatAuthAdapter(
                app_id=config.app_id,
                app_secret=config.app_secret,
                encoding_aes_key=config.encoding_aes_key
            )
        elif platform == PlatformType.ALIPAY.value:
            adapter = AlipayAuthAdapter(
                app_id=config.app_id,
                app_secret=config.app_secret,
                mch_id=config.mch_id,
                cert_path=config.cert_path,
                key_path=config.key_path
            )
        else:
            logger.warning(f"不支持的平台类型：{platform}")
            return None

        self._adapters[platform] = adapter
        return adapter

    def login(self, request: PlatformLoginRequest) -> PlatformLoginResponse:
        """
        平台用户登录

        流程:
        1. 使用 code 换取平台用户信息
        2. 查找或创建平台账号
        3. 查找或创建系统用户
        4. 返回登录结果
        """
        adapter = self._get_adapter(request.platform.value)
        if not adapter:
            raise Exception(f"平台 {request.platform.value} 不可用")

        # 1. code 换取会话
        session_info = adapter.code_to_session(request.code)
        logger.info(f"平台 {request.platform.value} 会话信息：{session_info}")

        platform_user_id = session_info.get("openid") or session_info.get("user_id")
        union_id = session_info.get("unionid")

        # 2. 查找或创建平台账号
        platform_account = self.db.query(PlatformAccountEntity).filter(
            PlatformAccountEntity.platform == request.platform.value,
            PlatformAccountEntity.platform_user_id == platform_user_id
        ).first()

        is_new_user = False
        if not platform_account:
            is_new_user = True
            # 创建新平台账号
            platform_account = PlatformAccountEntity(
                id=str(uuid4()),
                platform=request.platform.value,
                platform_user_id=platform_user_id,
                union_id=union_id,
                session_key=session_info.get("session_key"),
                nickname=session_info.get("nick_name") or session_info.get("nickname"),
                avatar_url=session_info.get("avatar") or session_info.get("avatar_url"),
                gender=session_info.get("gender"),
                is_active=True,
            )
            self.db.add(platform_account)
            self.db.commit()
            self.db.refresh(platform_account)
        else:
            # 更新会话信息
            platform_account.session_key = session_info.get("session_key")
            platform_account.union_id = union_id or platform_account.union_id
            platform_account.updated_at = datetime.utcnow()
            self.db.commit()

        # 3. 返回登录结果
        return PlatformLoginResponse(
            success=True,
            user_id=platform_account.user_id or str(uuid4()),  # 实际应关联系统用户
            platform_account_id=platform_account.id,
            is_new_user=is_new_user,
            access_token=self._generate_system_token(platform_account.id),
            user_info={
                "platform": request.platform.value,
                "platform_user_id": platform_user_id,
                "union_id": union_id,
                "nickname": platform_account.nickname,
                "avatar_url": platform_account.avatar_url,
            }
        )

    def bind(self, request: PlatformBindRequest) -> PlatformBindResponse:
        """绑定平台账号到系统用户"""
        adapter = self._get_adapter(request.platform.value)
        if not adapter:
            raise Exception(f"平台 {request.platform.value} 不可用")

        # 1. code 换取平台用户信息
        session_info = adapter.code_to_session(request.code)
        platform_user_id = session_info.get("openid") or session_info.get("user_id")

        # 2. 检查是否已被绑定
        existing = self.db.query(PlatformAccountEntity).filter(
            PlatformAccountEntity.platform == request.platform.value,
            PlatformAccountEntity.platform_user_id == platform_user_id
        ).first()

        if existing:
            if existing.user_id == request.user_id:
                return PlatformBindResponse(
                    success=True,
                    platform_account_id=existing.id,
                    message="账号已绑定"
                )
            else:
                return PlatformBindResponse(
                    success=False,
                    platform_account_id=existing.id,
                    message="该账号已被其他用户绑定"
                )

        # 3. 创建绑定关系
        platform_account = PlatformAccountEntity(
            id=str(uuid4()),
            user_id=request.user_id,
            platform=request.platform.value,
            platform_user_id=platform_user_id,
            union_id=session_info.get("unionid"),
            session_key=session_info.get("session_key"),
            nickname=session_info.get("nick_name") or session_info.get("nickname"),
            avatar_url=session_info.get("avatar") or session_info.get("avatar_url"),
            gender=session_info.get("gender"),
            is_active=True,
        )
        self.db.add(platform_account)
        self.db.commit()

        return PlatformBindResponse(
            success=True,
            platform_account_id=platform_account.id,
            message="绑定成功"
        )

    def unbind(self, user_id: str, platform: str) -> bool:
        """解绑平台账号"""
        platform_account = self.db.query(PlatformAccountEntity).filter(
            PlatformAccountEntity.user_id == user_id,
            PlatformAccountEntity.platform == platform
        ).first()

        if not platform_account:
            return False

        platform_account.is_active = False
        self.db.commit()
        return True

    def get_account(self, user_id: str, platform: Optional[str] = None) -> List[PlatformAccountEntity]:
        """获取用户的平台账号"""
        query = self.db.query(PlatformAccountEntity).filter(
            PlatformAccountEntity.user_id == user_id,
            PlatformAccountEntity.is_active == True
        )
        if platform:
            query = query.filter(PlatformAccountEntity.platform == platform)
        return query.all()

    def _generate_system_token(self, platform_account_id: str) -> str:
        """生成系统访问令牌"""
        # 简化实现，实际应使用 JWT
        token_data = f"{platform_account_id}:{datetime.utcnow().isoformat()}"
        return base64.b64encode(token_data.encode()).decode()


# ============= 平台订单服务 =============

class PlatformOrderService:
    """平台订单服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_order_mapping(self, order: PlatformOrderCreate) -> PlatformOrderEntity:
        """创建平台订单映射"""
        platform_order = PlatformOrderEntity(
            id=str(uuid4()),
            global_order_id=order.global_order_id,
            platform=order.platform.value,
            platform_order_id=order.platform_order_id,
            platform_order_no=order.platform_order_no,
            transaction_id=order.transaction_id,
            payment_amount=order.payment_amount,
            platform_metadata=json.dumps(order.platform_metadata) if order.platform_metadata else None,
            sync_status=SyncStatus.SYNCED.value,
        )
        self.db.add(platform_order)
        self.db.commit()
        self.db.refresh(platform_order)

        # 记录同步日志
        self._log_sync(
            sync_type="order",
            platform=order.platform.value,
            sync_direction=SyncDirection.INBOUND,
            sync_action=SyncAction.CREATE,
            platform_resource_id=order.platform_order_id,
            internal_resource_id=order.global_order_id,
        )

        return platform_order

    def get_order(self, platform_order_id: str) -> Optional[PlatformOrderEntity]:
        """获取平台订单"""
        return self.db.query(PlatformOrderEntity).filter(
            PlatformOrderEntity.platform_order_id == platform_order_id
        ).first()

    def get_orders_by_global_id(self, global_order_id: str) -> List[PlatformOrderEntity]:
        """根据全局订单 ID 获取所有平台订单"""
        return self.db.query(PlatformOrderEntity).filter(
            PlatformOrderEntity.global_order_id == global_order_id
        ).all()

    def get_orders_by_user(self, user_id: str, platform: Optional[str] = None) -> List[PlatformOrderEntity]:
        """根据用户 ID 获取平台订单"""
        # 需要通过全局订单关联用户
        from models.order_entities import OrderEntity
        query = self.db.query(PlatformOrderEntity).join(
            OrderEntity, PlatformOrderEntity.global_order_id == OrderEntity.id
        ).filter(
            OrderEntity.user_id == user_id
        )
        if platform:
            query = query.filter(PlatformOrderEntity.platform == platform)
        return query.all()

    def update_order_status(self, platform_order_id: str, update: PlatformOrderUpdate) -> PlatformOrderEntity:
        """更新平台订单状态"""
        platform_order = self.db.query(PlatformOrderEntity).filter(
            PlatformOrderEntity.platform_order_id == platform_order_id
        ).first()

        if not platform_order:
            raise Exception(f"平台订单 {platform_order_id} 不存在")

        # 更新字段
        if update.order_status:
            platform_order.order_status = update.order_status.value
        if update.payment_status:
            platform_order.payment_status = update.payment_status.value
        if update.payment_time:
            platform_order.payment_time = update.payment_time
        if update.refund_amount is not None:
            platform_order.refund_amount = update.refund_amount
        if update.refund_time:
            platform_order.refund_time = update.refund_time
        if update.refund_reason:
            platform_order.refund_reason = update.refund_reason
        if update.sync_status:
            platform_order.sync_status = update.sync_status.value

        platform_order.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(platform_order)

        return platform_order

    def sync_to_platform(self, global_order_id: str, platform: str,
                         order_status: Optional[OrderStatus] = None,
                         notify_user: bool = True) -> Tuple[bool, str]:
        """
        同步订单状态到平台

        实际生产环境需要调用平台 API 同步订单状态
        """
        platform_order = self.db.query(PlatformOrderEntity).filter(
            PlatformOrderEntity.global_order_id == global_order_id,
            PlatformOrderEntity.platform == platform
        ).first()

        if not platform_order:
            return False, f"平台 {platform} 订单不存在"

        # 记录同步日志
        self._log_sync(
            sync_type="order",
            platform=platform,
            sync_direction=SyncDirection.OUTBOUND,
            sync_action=SyncAction.UPDATE,
            platform_resource_id=platform_order.platform_order_id,
            internal_resource_id=global_order_id,
            request_data={"order_status": order_status.value if order_status else None},
        )

        # 简化实现，实际应调用平台 API
        platform_order.sync_status = SyncStatus.SYNCED.value
        platform_order.last_sync_at = datetime.utcnow()
        self.db.commit()

        return True, "同步成功"

    def _log_sync(self, sync_type: str, platform: str, sync_direction: SyncDirection,
                  sync_action: SyncAction, **kwargs):
        """记录同步日志"""
        log = PlatformSyncLogEntity(
            id=str(uuid4()),
            sync_type=sync_type,
            platform=platform,
            sync_direction=sync_direction.value,
            sync_action=sync_action.value,
            platform_resource_id=kwargs.get("platform_resource_id"),
            internal_resource_id=kwargs.get("internal_resource_id"),
            sync_status="success",
            request_data=json.dumps(kwargs.get("request_data")) if kwargs.get("request_data") else None,
            response_data=json.dumps(kwargs.get("response_data")) if kwargs.get("response_data") else None,
            error_message=kwargs.get("error_message"),
            duration_ms=kwargs.get("duration_ms"),
            operator_id=kwargs.get("operator_id"),
            operator_type=kwargs.get("operator_type", "system"),
        )
        self.db.add(log)
        self.db.commit()


# ============= 平台通知服务 =============

class PlatformNotificationService:
    """平台通知服务"""

    # 通知模板定义
    TEMPLATES = {
        PlatformType.WECHAT.value: {
            "order_paid": {
                "template_id": "wechat_order_paid_template",
                "fields": ["character_string1", "thing2", "thing3", "thing4"]
            },
            "order_ready": {
                "template_id": "wechat_order_ready_template",
                "fields": ["character_string1", "thing2", "time3"]
            },
            "group_success": {
                "template_id": "wechat_group_success_template",
                "fields": ["character_string1", "thing2", "thing3"]
            },
        },
        PlatformType.ALIPAY.value: {
            "order_paid": {
                "template_id": "alipay_order_paid_template",
                "fields": ["order_no", "product_name", "pay_time"]
            },
            "order_ready": {
                "template_id": "alipay_order_ready_template",
                "fields": ["order_no", "product_name", "pickup_time"]
            },
        },
    }

    def __init__(self, db: Session):
        self.db = db
        self._adapters: Dict[str, PlatformAuthAdapter] = {}

    def _get_adapter(self, platform: str) -> Optional[PlatformAuthAdapter]:
        """获取平台认证适配器"""
        if platform in self._adapters:
            return self._adapters[platform]

        config = self.db.query(PlatformConfigEntity).filter(
            PlatformConfigEntity.platform == platform,
            PlatformConfigEntity.is_enabled == True
        ).first()

        if not config:
            return None

        if platform == PlatformType.WECHAT.value:
            adapter = WechatAuthAdapter(
                app_id=config.app_id,
                app_secret=config.app_secret,
            )
        elif platform == PlatformType.ALIPAY.value:
            adapter = AlipayAuthAdapter(
                app_id=config.app_id,
                app_secret=config.app_secret,
            )
        else:
            return None

        self._adapters[platform] = adapter
        return adapter

    def send(self, request: PlatformNotificationSendRequest) -> PlatformNotificationResponse:
        """发送平台通知"""
        adapter = self._get_adapter(request.platform.value)
        if not adapter:
            raise Exception(f"平台 {request.platform.value} 不可用")

        # 获取用户平台账号
        platform_account = self.db.query(PlatformAccountEntity).filter(
            PlatformAccountEntity.user_id == request.user_id,
            PlatformAccountEntity.platform == request.platform.value,
            PlatformAccountEntity.is_active == True
        ).first()

        if not platform_account:
            raise Exception(f"用户未绑定平台 {request.platform.value}")

        recipient = platform_account.platform_user_id

        # 发送通知
        success, message = adapter.send_notification(
            recipient=recipient,
            template_id=request.template_id,
            content=request.content,
            page_path=request.page_path
        )

        # 创建通知记录
        notification = PlatformNotificationEntity(
            id=str(uuid4()),
            user_id=request.user_id,
            platform=request.platform.value,
            notification_type=NotificationType.SUBSCRIBE_MSG.value,
            template_id=request.template_id,
            template_name=request.template_name,
            recipient=recipient,
            title=request.title,
            content=json.dumps(request.content),
            page_path=request.page_path,
            send_status=SendStatus.SENT.value if success else SendStatus.FAILED.value,
            send_error=None if success else message,
            send_time=datetime.utcnow() if success else None,
            retry_count=request.retry_count,
            platform_response=json.dumps({"message": message}),
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)

        return PlatformNotificationResponse(
            id=notification.id,
            user_id=notification.user_id,
            platform=notification.platform,
            notification_type=notification.notification_type,
            template_id=notification.template_id,
            template_name=notification.template_name,
            title=notification.title,
            content=notification.content,
            page_path=notification.page_path,
            send_status=notification.send_status,
            send_time=notification.send_time,
            read_status=notification.read_status,
            read_time=notification.read_time,
            created_at=notification.created_at,
        )

    def send_order_notification(self, user_id: str, platform: str,
                                order_id: str, order_no: str,
                                notification_type: str) -> PlatformNotificationResponse:
        """发送订单相关通知"""
        # 获取模板
        templates = self.TEMPLATES.get(platform, {})
        template_info = templates.get(notification_type)

        if not template_info:
            raise Exception(f"平台 {platform} 没有 {notification_type} 模板")

        # 构建通知内容
        content_map = {
            "order_paid": {
                "character_string1": {"value": order_no},
                "thing2": {"value": "订单已支付"},
                "thing3": {"value": "请等待商家发货"},
                "thing4": {"value": "查看详情"}
            },
            "order_ready": {
                "character_string1": {"value": order_no},
                "thing2": {"value": "订单已备货完成"},
                "time3": {"value": datetime.utcnow().strftime("%Y-%m-%d %H:%M")}
            },
            "group_success": {
                "character_string1": {"value": order_no},
                "thing2": {"value": "团购成功"},
                "thing3": {"value": "请等待配送或自提"}
            },
        }

        content = content_map.get(notification_type, {})

        request = PlatformNotificationSendRequest(
            user_id=user_id,
            platform=PlatformType(platform),
            template_id=template_info["template_id"],
            template_name=notification_type,
            content=content,
            page_path=f"pages/order/detail?id={order_id}",
            title=f"订单{order_no}通知"
        )

        return self.send(request)

    def get_notifications(self, user_id: str, platform: Optional[str] = None,
                          limit: int = 20) -> List[PlatformNotificationEntity]:
        """获取用户通知"""
        query = self.db.query(PlatformNotificationEntity).filter(
            PlatformNotificationEntity.user_id == user_id
        )
        if platform:
            query = query.filter(PlatformNotificationEntity.platform == platform)
        return query.order_by(PlatformNotificationEntity.created_at.desc()).limit(limit).all()

    def mark_as_read(self, notification_id: str) -> bool:
        """标记通知为已读"""
        notification = self.db.query(PlatformNotificationEntity).filter(
            PlatformNotificationEntity.id == notification_id
        ).first()

        if not notification:
            return False

        notification.read_status = True
        notification.read_time = datetime.utcnow()
        self.db.commit()
        return True


# ============= 平台配置服务 =============

class PlatformConfigService:
    """平台配置服务"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, config: PlatformConfigCreate) -> PlatformConfigEntity:
        """创建平台配置"""
        entity = PlatformConfigEntity(
            id=str(uuid4()),
            platform=config.platform.value,
            platform_name=config.platform_name,
            app_id=config.app_id,
            app_secret=config.app_secret,
            encoding_aes_key=config.encoding_aes_key,
            mch_id=config.mch_id,
            mch_key=config.mch_key,
            cert_path=config.cert_path,
            key_path=config.key_path,
            api_version=config.api_version,
            api_base_url=config.api_base_url,
            webhook_url=config.webhook_url,
            webhook_token=config.webhook_token,
            is_enabled=config.is_enabled,
            config_json=json.dumps(config.config_json) if config.config_json else None,
            remarks=config.remarks,
        )
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def get(self, platform: str) -> Optional[PlatformConfigEntity]:
        """获取平台配置"""
        return self.db.query(PlatformConfigEntity).filter(
            PlatformConfigEntity.platform == platform
        ).first()

    def get_all(self, enabled_only: bool = False) -> List[PlatformConfigEntity]:
        """获取所有平台配置"""
        query = self.db.query(PlatformConfigEntity)
        if enabled_only:
            query = query.filter(PlatformConfigEntity.is_enabled == True)
        return query.all()

    def update(self, platform: str, update: PlatformConfigUpdate) -> Optional[PlatformConfigEntity]:
        """更新平台配置"""
        config = self.get(platform)
        if not config:
            return None

        update_data = update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(config, key):
                setattr(config, key, value)

        config.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(config)
        return config

    def delete(self, platform: str) -> bool:
        """删除平台配置"""
        config = self.get(platform)
        if not config:
            return False

        self.db.delete(config)
        self.db.commit()
        return True


# ============= 平台同步日志服务 =============

class PlatformSyncLogService:
    """平台同步日志服务"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, log: PlatformSyncLogCreate) -> PlatformSyncLogEntity:
        """创建同步日志"""
        entity = PlatformSyncLogEntity(
            id=str(uuid4()),
            sync_type=log.sync_type,
            platform=log.platform.value,
            sync_direction=log.sync_direction.value,
            sync_action=log.sync_action.value,
            platform_resource_id=log.platform_resource_id,
            internal_resource_id=log.internal_resource_id,
            sync_status="success" if not log.error_message else "failed",
            request_data=json.dumps(log.request_data) if log.request_data else None,
            response_data=json.dumps(log.response_data) if log.response_data else None,
            error_message=log.error_message,
            duration_ms=log.duration_ms,
            operator_id=log.operator_id,
            operator_type=log.operator_type or "system",
        )
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def query(self, sync_type: Optional[str] = None, platform: Optional[str] = None,
              sync_status: Optional[str] = None, internal_resource_id: Optional[str] = None,
              start_time: Optional[datetime] = None, end_time: Optional[datetime] = None,
              page: int = 1, page_size: int = 20) -> Tuple[List[PlatformSyncLogEntity], int]:
        """查询同步日志"""
        query = self.db.query(PlatformSyncLogEntity)

        if sync_type:
            query = query.filter(PlatformSyncLogEntity.sync_type == sync_type)
        if platform:
            query = query.filter(PlatformSyncLogEntity.platform == platform)
        if sync_status:
            query = query.filter(PlatformSyncLogEntity.sync_status == sync_status)
        if internal_resource_id:
            query = query.filter(PlatformSyncLogEntity.internal_resource_id == internal_resource_id)
        if start_time:
            query = query.filter(PlatformSyncLogEntity.created_at >= start_time)
        if end_time:
            query = query.filter(PlatformSyncLogEntity.created_at <= end_time)

        total = query.count()
        logs = query.order_by(PlatformSyncLogEntity.created_at.desc())\
                    .offset((page - 1) * page_size)\
                    .limit(page_size)\
                    .all()

        return logs, total

    def get_stats(self, platform: Optional[str] = None,
                  start_time: Optional[datetime] = None,
                  end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """获取同步统计"""
        query = self.db.query(PlatformSyncLogEntity)

        if platform:
            query = query.filter(PlatformSyncLogEntity.platform == platform)
        if start_time:
            query = query.filter(PlatformSyncLogEntity.created_at >= start_time)
        if end_time:
            query = query.filter(PlatformSyncLogEntity.created_at <= end_time)

        total = query.count()
        success = query.filter(PlatformSyncLogEntity.sync_status == "success").count()
        failed = query.filter(PlatformSyncLogEntity.sync_status == "failed").count()

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": success / total if total > 0 else 0,
        }


# ============= 统一平台服务 =============

class PlatformIntegrationService:
    """
    平台集成统一服务

    整合所有平台相关服务，提供统一接口
    """

    def __init__(self, db: Session):
        self.db = db
        self.auth_service = PlatformAuthService(db)
        self.order_service = PlatformOrderService(db)
        self.notification_service = PlatformNotificationService(db)
        self.config_service = PlatformConfigService(db)
        self.sync_log_service = PlatformSyncLogService(db)

    def get_platform_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有平台统计信息"""
        configs = self.config_service.get_all()
        stats = {}

        for config in configs:
            platform = config.platform

            # 账号统计
            account_count = self.db.query(PlatformAccountEntity).filter(
                PlatformAccountEntity.platform == platform
            ).count()

            active_account_count = self.db.query(PlatformAccountEntity).filter(
                PlatformAccountEntity.platform == platform,
                PlatformAccountEntity.is_active == True
            ).count()

            # 订单统计
            order_count = self.db.query(PlatformOrderEntity).filter(
                PlatformOrderEntity.platform == platform
            ).count()

            # 通知统计
            notification_count = self.db.query(PlatformNotificationEntity).filter(
                PlatformNotificationEntity.platform == platform
            ).count()

            failed_notification_count = self.db.query(PlatformNotificationEntity).filter(
                PlatformNotificationEntity.platform == platform,
                PlatformNotificationEntity.send_status == SendStatus.FAILED.value
            ).count()

            stats[platform] = {
                "total_accounts": account_count,
                "active_accounts": active_account_count,
                "total_orders": order_count,
                "total_notifications": notification_count,
                "failed_notifications": failed_notification_count,
                "is_enabled": config.is_enabled,
            }

        return stats
