"""
支付网关服务
实现支付宝、微信支付、Stripe 等第三方支付渠道的对接
"""
import hashlib
import hmac
import base64
import json
import time
import uuid
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from enum import Enum
import requests
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256

from config.settings import settings
from config.logging_config import get_logger

logger = get_logger(__name__)


class PaymentChannel(str, Enum):
    """支付渠道"""
    ALIPAY = "alipay"  # 支付宝
    WECHAT_PAY = "wechat_pay"  # 微信支付
    STRIPE = "stripe"  # Stripe (国际)
    BALANCE = "balance"  # 余额支付


class PaymentStatus(str, Enum):
    """支付状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class PaymentMethod(str, Enum):
    """支付方式"""
    # 支付宝
    ALIPAY_WAP = "alipay_wap"  # 手机网页支付
    ALIPAY_QR = "alipay_qr"  # 扫码支付
    ALIPAY_APP = "alipay_app"  # APP 支付
    ALIPAY_BARCODE = "alipay_barcode"  # 条码支付

    # 微信支付
    WECHAT_JSAPI = "wechat_jsapi"  # JSAPI 支付
    WECHAT_NATIVE = "wechat_native"  # 扫码支付
    WECHAT_APP = "wechat_app"  # APP 支付
    WECHAT_H5 = "wechat_h5"  # H5 支付

    # Stripe
    STRIPE_CARD = "stripe_card"  # 信用卡
    STRIPE_ALIPAY = "stripe_alipay"  # Stripe 支付宝


class PaymentGatewayBase(ABC):
    """支付网关抽象基类"""

    @abstractmethod
    def create_payment(self, order_id: str, amount: float, subject: str, **kwargs) -> Dict[str, Any]:
        """创建支付"""
        pass

    @abstractmethod
    def verify_callback(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """验证回调"""
        pass

    @abstractmethod
    def query_payment(self, order_id: str) -> Dict[str, Any]:
        """查询支付状态"""
        pass

    @abstractmethod
    def refund(self, transaction_id: str, amount: float, **kwargs) -> Dict[str, Any]:
        """退款"""
        pass


class AlipayGateway(PaymentGatewayBase):
    """
    支付宝支付网关

    文档：https://opendocs.alipay.com/open/270/105899
    """

    GATEWAY_URL = "https://openapi.alipay.com/gateway.do"
    GATEWAY_URL_SANDBOX = "https://openapi-sandbox.dl.alipaydev.com/gateway.do"

    def __init__(self, sandbox: bool = False):
        self.sandbox = sandbox
        self.gateway_url = self.GATEWAY_URL_SANDBOX if sandbox else self.GATEWAY_URL
        self.app_id = settings.alipay_app_id
        self.private_key = settings.alipay_private_key
        self.alipay_public_key = settings.alipay_public_key
        self.notify_url = settings.alipay_notify_url
        self.sign_type = "RSA2"
        self.charset = "utf-8"
        self.version = "1.0"

    def _sign(self, data: Dict[str, Any]) -> str:
        """生成签名"""
        # 排序参数
        sorted_data = {k: v for k, v in sorted(data.items()) if v and k != "sign"}
        # 拼接字符串
        sign_string = "&".join(f"{k}={v}" for k, v in sorted_data.items())
        # RSA 签名
        key = RSA.import_key(self.private_key.encode())
        h = SHA256.new(sign_string.encode())
        signature = pkcs1_15.new(key).sign(h)
        return base64.b64encode(signature).decode()

    def _verify(self, data: Dict[str, Any], sign: str) -> bool:
        """验证签名"""
        try:
            # 排序参数
            sorted_data = {k: v for k, v in sorted(data.items()) if v and k != "sign"}
            sign_string = "&".join(f"{k}={v}" for k, v in sorted_data.items())
            # 验证签名
            key = RSA.import_key(self.alipay_public_key.encode())
            h = SHA256.new(sign_string.encode())
            pkcs1_15.new(key).verify(h, base64.b64decode(sign))
            return True
        except Exception as e:
            logger.error(f"支付宝签名验证失败：{e}")
            return False

    def _build_common_params(self, method: str, biz_content: Dict[str, Any]) -> Dict[str, Any]:
        """构建公共参数"""
        params = {
            "app_id": self.app_id,
            "method": method,
            "charset": self.charset,
            "sign_type": self.sign_type,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": self.version,
            "biz_content": json.dumps(biz_content, ensure_ascii=False),
        }
        if self.notify_url:
            params["notify_url"] = self.notify_url
        return params

    def create_payment(
        self,
        order_id: str,
        amount: float,
        subject: str,
        method: str = "alipay.trade.wap.pay",
        **kwargs
    ) -> Dict[str, Any]:
        """
        创建支付宝支付

        Args:
            order_id: 订单 ID
            amount: 金额 (元)
            subject: 订单标题
            method: API 方法名
            **kwargs: 其他参数

        Returns:
            {
                "success": True,
                "payment_url": "https://...",  # 支付链接或表单 HTML
                "out_trade_no": order_id,
                "trade_no": "支付宝交易号",
            }
        """
        biz_content = {
            "out_trade_no": order_id,
            "total_amount": str(round(amount, 2)),
            "subject": subject,
            "product_code": "QUICK_WAP_WAY",
            "quit_url": kwargs.get("return_url", ""),
            "timeout_express": kwargs.get("timeout_express", "30m"),
        }

        # 添加买家信息
        if kwargs.get("buyer_id"):
            biz_content["buyer_id"] = kwargs["buyer_id"]

        params = self._build_common_params(method, biz_content)
        params["sign"] = self._sign(params)

        # 如果是页面支付，返回表单 HTML
        if "wap" in method or "page" in method:
            # 构建表单 HTML
            form_html = f"""
            <form id="alipay_form" name="alipay_form" action="{self.gateway_url}" method="POST">
                {''.join(f'<input type="hidden" name="{k}" value="{v}"/>' for k, v in params.items())}
                <input type="submit" value="立即支付"/>
            </form>
            <script>document.forms['alipay_form'].submit();</script>
            """
            return {
                "success": True,
                "payment_url": self.gateway_url,
                "form_html": form_html,
                "out_trade_no": order_id,
            }

        # 如果是扫码支付，返回二维码链接
        elif "qr" in method or "native" in method:
            response = requests.post(self.gateway_url, data=params, timeout=10)
            result = response.json()
            if result.get("alipay_trade_qrpay_response", {}).get("code") == "10000":
                qr_code = result["alipay_trade_qrpay_response"]["qr_code"]
                return {
                    "success": True,
                    "qr_code": qr_code,
                    "out_trade_no": order_id,
                }

        return {"success": False, "error": "Unsupported payment method"}

    def verify_callback(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """验证支付宝异步通知"""
        # 获取签名
        sign = data.get("sign")
        if not sign:
            return False, "Missing sign"

        # 验证签名
        if not self._verify(data, sign):
            return False, "Invalid sign"

        # 检查交易状态
        trade_status = data.get("trade_status")
        if trade_status == "TRADE_SUCCESS":
            return True, "success"
        elif trade_status == "TRADE_CLOSED":
            return False, "Trade closed"
        else:
            return False, f"Unexpected status: {trade_status}"

    def query_payment(self, order_id: str) -> Dict[str, Any]:
        """查询支付宝交易状态"""
        biz_content = {
            "out_trade_no": order_id,
        }
        params = self._build_common_params("alipay.trade.query", biz_content)
        params["sign"] = self._sign(params)

        response = requests.post(self.gateway_url, data=params, timeout=10)
        result = response.json()
        response_key = "alipay_trade_query_response"

        if result.get(response_key, {}).get("code") == "10000":
            trade_info = result[response_key]
            return {
                "success": True,
                "trade_no": trade_info.get("trade_no"),
                "out_trade_no": trade_info.get("out_trade_no"),
                "total_amount": trade_info.get("total_amount"),
                "trade_status": trade_info.get("trade_status"),
            }
        else:
            return {
                "success": False,
                "error": result.get(response_key, {}).get("sub_msg", "Query failed"),
            }

    def refund(self, transaction_id: str, amount: float, **kwargs) -> Dict[str, Any]:
        """支付宝退款"""
        biz_content = {
            "trade_no": transaction_id,
            "refund_amount": str(round(amount, 2)),
            "refund_reason": kwargs.get("reason", ""),
        }
        if kwargs.get("out_request_no"):
            biz_content["out_request_no"] = kwargs["out_request_no"]
        else:
            biz_content["out_request_no"] = str(uuid.uuid4())

        params = self._build_common_params("alipay.trade.refund", biz_content)
        params["sign"] = self._sign(params)

        response = requests.post(self.gateway_url, data=params, timeout=10)
        result = response.json()
        response_key = "alipay_trade_refund_response"

        if result.get(response_key, {}).get("code") == "10000":
            refund_info = result[response_key]
            return {
                "success": True,
                "refund_trade_no": refund_info.get("fund_change"),
                "refund_amount": refund_info.get("refund_amount"),
            }
        else:
            return {
                "success": False,
                "error": result.get(response_key, {}).get("sub_msg", "Refund failed"),
            }


class WechatPayGateway(PaymentGatewayBase):
    """
    微信支付网关 (API v3)

    文档：https://pay.weixin.qq.com/wiki/doc/apiv3/index.shtml
    """

    API_BASE = "https://api.mch.weixin.qq.com"
    API_BASE_SANDBOX = "https://api.mch.weixin.qq.com/sandboxnew"

    def __init__(self, sandbox: bool = False):
        self.sandbox = sandbox
        self.base_url = self.API_BASE_SANDBOX if sandbox else self.API_BASE
        self.mch_id = settings.wechat_pay_mch_id
        self.app_id = settings.wechat_pay_app_id
        self.api_v3_key = settings.wechat_pay_api_v3_key
        self.private_key = settings.wechat_pay_private_key
        self.serial_number = settings.wechat_pay_serial_number
        self.notify_url = settings.wechat_pay_notify_url

    def _generate_nonce(self) -> str:
        """生成随机字符串"""
        return uuid.uuid4().hex

    def _sign(self, message: str) -> str:
        """生成签名"""
        from Crypto.Signature import pkcs1_15
        from Crypto.Hash import SHA256

        key = RSA.import_key(self.private_key.encode())
        h = SHA256.new(message.encode())
        signature = pkcs1_15.new(key).sign(h)
        return base64.b64encode(signature).decode()

    def _get_authorization(
        self,
        method: str,
        url: str,
        body: Optional[str] = None,
        nonce: Optional[str] = None,
        timestamp: Optional[int] = None
    ) -> str:
        """生成 Authorization 头"""
        nonce = nonce or self._generate_nonce()
        timestamp = timestamp or int(time.time())

        # 构建签名串
        url_parts = url.replace("https://", "").split("/", 1)
        url_path = "/" + url_parts[1] if len(url_parts) > 1 else "/"
        if "?" in url_path:
            url_path = url_path.split("?")[0]

        sign_message = f"{method}\n{url_path}\n{timestamp}\n{nonce}\n{body or ''}\n"
        signature = self._sign(sign_message)

        return f'WECHATPAY2-SHA256-RSA2048 mchid="{self.mch_id}",nonce_str="{nonce}",signature="{signature}",timestamp="{timestamp}",serial_no="{self.serial_number}"'

    def create_payment(
        self,
        order_id: str,
        amount: int,  # 微信支付金额单位为分
        subject: str,
        method: str = "native",
        **kwargs
    ) -> Dict[str, Any]:
        """
        创建微信支付

        Args:
            order_id: 商户订单号
            amount: 金额 (分)
            subject: 订单标题
            method: 支付方式 (native/jsapi/app/h5)

        Returns:
            {
                "success": True,
                "code_url": "weixin://wxpay/bizpayurl?pr=xxx",  # 扫码支付链接
                "prepay_id": "wx201410272009395522657a690389285100",
            }
        """
        # 根据支付方式选择 API
        if method == "native":
            url = f"{self.base_url}/v3/pay/transactions/native"
        elif method == "jsapi":
            url = f"{self.base_url}/v3/pay/transactions/jsapi"
        elif method == "app":
            url = f"{self.base_url}/v3/pay/transactions/app"
        elif method == "h5":
            url = f"{self.base_url}/v3/pay/transactions/h5"
        else:
            return {"success": False, "error": "Unsupported payment method"}

        # 构建请求体
        body_data = {
            "appid": self.app_id,
            "mchid": self.mch_id,
            "description": subject,
            "out_trade_no": order_id,
            "notify_url": self.notify_url,
            "amount": {
                "total": amount,
                "currency": "CNY",
            },
        }

        # JSAPI 支付需要 openid
        if method == "jsapi" and kwargs.get("payer"):
            body_data["payer"] = kwargs["payer"]

        body = json.dumps(body_data, ensure_ascii=False)
        nonce = self._generate_nonce()
        timestamp = int(time.time())

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": self._get_authorization("POST", url, body, nonce, timestamp),
        }

        response = requests.post(url, headers=headers, data=body, timeout=10)
        result = response.json()

        if result.get("code") == "SUCCESS" or response.status_code == 200:
            return {
                "success": True,
                "prepay_id": result.get("prepay_id"),
                "code_url": result.get("code_url"),  # 扫码支付返回
            }
        else:
            return {
                "success": False,
                "error": result.get("message", "Create payment failed"),
            }

    def verify_callback(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """验证微信支付回调"""
        # 验证签名
        signature = data.get("signature", "")
        timestamp = data.get("timestamp", "")
        nonce = data.get("nonce", "")
        body = data.get("body", "")

        if not all([signature, timestamp, nonce, body]):
            return False, "Missing required fields"

        # 构建签名串
        sign_message = f"{timestamp}\n{nonce}\n{body}\n"
        try:
            from Crypto.Signature import pkcs1_15
            from Crypto.Hash import SHA256

            # 加载平台证书公钥
            key = RSA.import_key(self.api_v3_key.encode())
            h = SHA256.new(sign_message.encode())
            pkcs1_15.new(key).verify(h, base64.b64decode(signature))
            return True, "success"
        except Exception as e:
            logger.error(f"微信支付签名验证失败：{e}")
            return False, "Invalid sign"

    def query_payment(self, order_id: str) -> Dict[str, Any]:
        """查询微信支付订单"""
        url = f"{self.base_url}/v3/pay/transactions/out-trade-no/{order_id}"
        params = {"mchid": self.mch_id}

        nonce = self._generate_nonce()
        timestamp = int(time.time())

        headers = {
            "Accept": "application/json",
            "Authorization": self._get_authorization("GET", url, None, nonce, timestamp),
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)
        result = response.json()

        if result.get("trade_state") == "SUCCESS":
            return {
                "success": True,
                "transaction_id": result.get("transaction_id"),
                "trade_state": result.get("trade_state"),
                "total_amount": result.get("amount", {}).get("total"),
            }
        else:
            return {
                "success": False,
                "trade_state": result.get("trade_state", "NOT_FOUND"),
            }

    def refund(self, transaction_id: str, amount: int, **kwargs) -> Dict[str, Any]:
        """微信支付退款"""
        url = f"{self.base_url}/v3/refund/domestic/refunds"

        body_data = {
            "transaction_id": transaction_id,
            "out_refund_no": kwargs.get("out_refund_no", str(uuid.uuid4())),
            "amount": {
                "refund": amount,
                "total": amount,
                "currency": "CNY",
            },
            "reason": kwargs.get("reason", ""),
        }

        body = json.dumps(body_data, ensure_ascii=False)
        nonce = self._generate_nonce()
        timestamp = int(time.time())

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": self._get_authorization("POST", url, body, nonce, timestamp),
        }

        response = requests.post(url, headers=headers, data=body, timeout=10)
        result = response.json()

        if result.get("status") == "SUCCESS":
            return {
                "success": True,
                "refund_id": result.get("refund_id"),
                "refund_amount": result.get("amount", {}).get("refund"),
            }
        else:
            return {
                "success": False,
                "error": result.get("message", "Refund failed"),
            }


class StripeGateway(PaymentGatewayBase):
    """
    Stripe 支付网关

    文档：https://stripe.com/docs/api
    """

    API_BASE = "https://api.stripe.com/v1"

    def __init__(self, sandbox: bool = False):
        self.sandbox = sandbox
        self.api_key = settings.stripe_api_key
        self.webhook_secret = settings.stripe_webhook_secret
        self.notify_url = settings.stripe_notify_url

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def create_payment(
        self,
        order_id: str,
        amount: int,  # Stripe 金额单位为分
        subject: str,
        currency: str = "cny",
        **kwargs
    ) -> Dict[str, Any]:
        """
        创建 Stripe 支付 (Payment Intent)

        Args:
            order_id: 订单 ID
            amount: 金额 (分)
            subject: 订单描述
            currency: 货币代码 (默认 cny)

        Returns:
            {
                "success": True,
                "client_secret": "pi_xxx_secret_xxx",
                "payment_intent_id": "pi_xxx",
            }
        """
        url = f"{self.API_BASE}/payment_intents"

        data = {
            "amount": amount,
            "currency": currency,
            "description": subject,
            "metadata": {"order_id": order_id},
        }

        # 添加自动确认
        if kwargs.get("auto_confirm"):
            data["confirm"] = "true"

        # 添加支付方式
        if kwargs.get("payment_method_types"):
            data["payment_method_types"] = json.dumps(kwargs["payment_method_types"])

        # 添加成功/取消页面 URL
        if kwargs.get("return_url"):
            data["return_url"] = kwargs["return_url"]

        response = requests.post(url, headers=self._get_headers(), data=data, timeout=10)
        result = response.json()

        if "error" not in result:
            return {
                "success": True,
                "client_secret": result.get("client_secret"),
                "payment_intent_id": result.get("id"),
            }
        else:
            return {
                "success": False,
                "error": result["error"].get("message", "Create payment failed"),
            }

    def verify_callback(self, data: Dict[str, Any], sig_header: str) -> Tuple[bool, str]:
        """验证 Stripe Webhook 签名"""
        import stripe
        stripe.api_key = self.api_key

        try:
            event = stripe.Webhook.construct_event(
                data, sig_header, self.webhook_secret
            )
            return True, "success"
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Stripe 签名验证失败：{e}")
            return False, "Invalid signature"
        except Exception as e:
            logger.error(f"Stripe Webhook 处理失败：{e}")
            return False, str(e)

    def query_payment(self, payment_intent_id: str) -> Dict[str, Any]:
        """查询 Stripe 支付状态"""
        url = f"{self.API_BASE}/payment_intents/{payment_intent_id}"

        response = requests.get(url, headers=self._get_headers(), timeout=10)
        result = response.json()

        if "error" not in result:
            status_map = {
                "succeeded": "SUCCESS",
                "processing": "PROCESSING",
                "requires_payment_method": "PENDING",
                "requires_confirmation": "PENDING",
                "canceled": "CANCELLED",
            }
            return {
                "success": True,
                "status": status_map.get(result.get("status"), "UNKNOWN"),
                "amount": result.get("amount"),
                "currency": result.get("currency"),
            }
        else:
            return {
                "success": False,
                "error": result["error"].get("message", "Query failed"),
            }

    def refund(self, payment_intent_id: str, amount: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        """Stripe 退款"""
        url = f"{self.API_BASE}/refunds"

        data = {"payment_intent": payment_intent_id}
        if amount:
            data["amount"] = amount
        if kwargs.get("reason"):
            data["reason"] = kwargs["reason"]

        response = requests.post(url, headers=self._get_headers(), data=data, timeout=10)
        result = response.json()

        if "error" not in result:
            return {
                "success": True,
                "refund_id": result.get("id"),
                "refund_amount": result.get("amount"),
                "status": result.get("status"),
            }
        else:
            return {
                "success": False,
                "error": result["error"].get("message", "Refund failed"),
            }


# ==================== 支付网关工厂 ====================

class PaymentGatewayFactory:
    """支付网关工厂"""

    _gateways: Dict[PaymentChannel, PaymentGatewayBase] = {}

    @classmethod
    def get_gateway(cls, channel: PaymentChannel, sandbox: bool = False) -> PaymentGatewayBase:
        """获取支付网关实例"""
        if channel not in cls._gateways:
            if channel == PaymentChannel.ALIPAY:
                cls._gateways[channel] = AlipayGateway(sandbox=sandbox)
            elif channel == PaymentChannel.WECHAT_PAY:
                cls._gateways[channel] = WechatPayGateway(sandbox=sandbox)
            elif channel == PaymentChannel.STRIPE:
                cls._gateways[channel] = StripeGateway(sandbox=sandbox)
            else:
                raise ValueError(f"Unsupported payment channel: {channel}")
        return cls._gateways[channel]

    @classmethod
    def reset(cls):
        """重置所有网关实例 (用于测试)"""
        cls._gateways = {}


def get_payment_gateway(channel: str, sandbox: bool = False) -> PaymentGatewayBase:
    """获取支付网关的便捷函数"""
    return PaymentGatewayFactory.get_gateway(PaymentChannel(channel), sandbox)
