"""
P6 - 支付网关抽象层

提供统一的支付接口抽象，支持多种支付方式：
- 支付宝 (Alipay)
- 微信支付 (WeChat Pay)
- Stripe (国际信用卡)
- 模拟支付 (Mock - 用于测试)

设计原则：
1. 策略模式：不同支付方式实现统一接口
2. 易于扩展：新增支付方式只需实现 PaymentGateway 接口
3. 安全：签名验证、回调验证
"""
import uuid
import hashlib
import hmac
import base64
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PaymentGatewayError(Exception):
    """支付网关异常基类"""
    pass


class PaymentGateway(ABC):
    """支付网关抽象基类"""

    @abstractmethod
    def create_payment(self, order_no: str, amount: float, description: str, **kwargs) -> Dict[str, Any]:
        """
        创建支付订单

        Args:
            order_no: 订单号
            amount: 金额
            description: 订单描述
            **kwargs: 额外参数

        Returns:
            dict: 支付信息，包含支付 URL 或二维码等
        """
        pass

    @abstractmethod
    def verify_callback(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        验证支付回调

        Args:
            data: 回调数据

        Returns:
            Tuple[bool, str]: (是否验证通过，交易 ID 或错误信息)
        """
        pass

    @abstractmethod
    def refund(self, transaction_id: str, amount: float, reason: str) -> Dict[str, Any]:
        """
        退款

        Args:
            transaction_id: 原交易 ID
            amount: 退款金额
            reason: 退款原因

        Returns:
            dict: 退款结果
        """
        pass

    @abstractmethod
    def query_payment(self, transaction_id: str) -> Dict[str, Any]:
        """
        查询支付状态

        Args:
            transaction_id: 交易 ID

        Returns:
            dict: 支付状态信息
        """
        pass


class MockPaymentGateway(PaymentGateway):
    """
    模拟支付网关 - 用于开发和测试

    模拟支付流程：
    1. 创建支付订单时生成模拟交易号
    2. 回调验证始终通过（测试环境）
    3. 退款直接返回成功
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.mock_transactions = {}  # 内存存储模拟交易

    def create_payment(self, order_no: str, amount: float, description: str, **kwargs) -> Dict[str, Any]:
        """创建模拟支付订单"""
        transaction_id = f"mock_{uuid.uuid4().hex[:16]}"

        # 生成模拟支付 URL（实际测试中直接调用回调）
        mock_pay_url = f"http://mock.payment/pay?order_no={order_no}&amount={amount}"

        # 存储交易信息
        self.mock_transactions[transaction_id] = {
            "order_no": order_no,
            "amount": amount,
            "description": description,
            "status": "pending",
            "created_at": datetime.now(),
        }

        logger.info(f"[MockPayment] 创建支付订单：order_no={order_no}, amount={amount}, transaction_id={transaction_id}")

        return {
            "payment_method": "mock",
            "transaction_id": transaction_id,
            "order_no": order_no,
            "amount": amount,
            "pay_url": mock_pay_url,
            "qr_code": f"data:image/png;base64,{base64.b64encode(mock_pay_url.encode()).decode()}",
            "status": "pending",
            "message": "模拟支付已创建，请调用回调接口完成支付",
        }

    def verify_callback(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """验证模拟支付回调"""
        transaction_id = data.get("transaction_id")

        if not transaction_id:
            return False, "缺少交易 ID"

        if transaction_id not in self.mock_transactions:
            return False, f"交易不存在：{transaction_id}"

        # 更新交易状态
        self.mock_transactions[transaction_id]["status"] = "success"
        self.mock_transactions[transaction_id]["paid_at"] = datetime.now()

        logger.info(f"[MockPayment] 支付成功：transaction_id={transaction_id}")
        return True, transaction_id

    def refund(self, transaction_id: str, amount: float, reason: str) -> Dict[str, Any]:
        """模拟退款"""
        if transaction_id not in self.mock_transactions:
            return {
                "success": False,
                "error": f"交易不存在：{transaction_id}",
            }

        # 更新交易状态
        self.mock_transactions[transaction_id]["status"] = "refunded"
        self.mock_transactions[transaction_id]["refunded_at"] = datetime.now()
        self.mock_transactions[transaction_id]["refund_amount"] = amount

        refund_id = f"refund_{uuid.uuid4().hex[:16]}"

        logger.info(f"[MockPayment] 退款成功：transaction_id={transaction_id}, refund_id={refund_id}, amount={amount}")

        return {
            "success": True,
            "refund_id": refund_id,
            "transaction_id": transaction_id,
            "amount": amount,
            "reason": reason,
        }

    def query_payment(self, transaction_id: str) -> Dict[str, Any]:
        """查询模拟支付状态"""
        if transaction_id not in self.mock_transactions:
            return {
                "success": False,
                "error": f"交易不存在：{transaction_id}",
            }

        tx = self.mock_transactions[transaction_id]
        return {
            "success": True,
            "transaction_id": transaction_id,
            "order_no": tx["order_no"],
            "amount": tx["amount"],
            "status": tx["status"],
            "created_at": tx["created_at"].isoformat() if tx["created_at"] else None,
            "paid_at": tx.get("paid_at", {}).isoformat() if tx.get("paid_at") else None,
        }

    # 测试专用方法：模拟支付回调
    def simulate_payment_callback(self, transaction_id: str) -> Dict[str, Any]:
        """模拟支付回调（测试用）"""
        if transaction_id not in self.mock_transactions:
            raise PaymentGatewayError(f"交易不存在：{transaction_id}")

        tx = self.mock_transactions[transaction_id]
        if tx["status"] != "pending":
            raise PaymentGatewayError(f"交易状态不正确：{tx['status']}")

        # 更新状态
        tx["status"] = "success"
        tx["paid_at"] = datetime.now()

        return {
            "transaction_id": transaction_id,
            "order_no": tx["order_no"],
            "amount": tx["amount"],
            "status": "success",
            "paid_at": tx["paid_at"].isoformat(),
        }


class AlipayGateway(PaymentGateway):
    """
    支付宝支付网关

    TODO: 生产环境需要实现完整的支付宝 SDK 集成
    包括：
    1. RSA2 签名验证
    2. 异步回调处理
    3. 退款接口
    4. 订单查询
    """

    def __init__(self, config: Dict[str, Any]):
        self.app_id = config.get("app_id", "")
        self.private_key = config.get("private_key", "")
        self.alipay_public_key = config.get("alipay_public_key", "")
        self.notify_url = config.get("notify_url", "")
        self.return_url = config.get("return_url", "")

    def create_payment(self, order_no: str, amount: float, description: str, **kwargs) -> Dict[str, Any]:
        """创建支付宝支付订单"""
        # TODO: 实现支付宝 SDK 调用
        # 目前返回模拟响应
        logger.warning("[AlipayGateway] 支付宝支付尚未实现，返回模拟响应")

        return {
            "payment_method": "alipay",
            "order_no": order_no,
            "amount": amount,
            "pay_url": f"https://openapi.alipay.com/gateway.do?order_no={order_no}",
            "qr_code": None,  # TODO: 生成支付宝二维码
            "status": "pending",
            "message": "支付宝支付接口待实现",
        }

    def verify_callback(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """验证支付宝回调签名"""
        # TODO: 实现 RSA2 签名验证
        logger.warning("[AlipayGateway] 回调验证尚未实现")
        return False, "支付宝回调验证未实现"

    def refund(self, transaction_id: str, amount: float, reason: str) -> Dict[str, Any]:
        """支付宝退款"""
        # TODO: 实现支付宝退款 API
        return {
            "success": False,
            "error": "支付宝退款接口未实现",
        }

    def query_payment(self, transaction_id: str) -> Dict[str, Any]:
        """查询支付宝订单状态"""
        # TODO: 实现支付宝订单查询 API
        return {
            "success": False,
            "error": "支付宝订单查询接口未实现",
        }


class WeChatPayGateway(PaymentGateway):
    """
    微信支付网关

    TODO: 生产环境需要实现完整的微信支付 SDK 集成
    """

    def __init__(self, config: Dict[str, Any]):
        self.app_id = config.get("app_id", "")
        self.mch_id = config.get("mch_id", "")
        self.api_key = config.get("api_key", "")
        self.notify_url = config.get("notify_url", "")

    def create_payment(self, order_no: str, amount: float, description: str, **kwargs) -> Dict[str, Any]:
        """创建微信支付订单"""
        # TODO: 实现微信支付 SDK 调用
        logger.warning("[WeChatPayGateway] 微信支付尚未实现，返回模拟响应")

        return {
            "payment_method": "wechat",
            "order_no": order_no,
            "amount": amount,
            "pay_url": None,
            "qr_code": None,  # TODO: 生成微信支付二维码
            "status": "pending",
            "message": "微信支付接口待实现",
        }

    def verify_callback(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """验证微信支付回调签名"""
        # TODO: 实现微信支付签名验证
        logger.warning("[WeChatPayGateway] 回调验证尚未实现")
        return False, "微信支付回调验证未实现"

    def refund(self, transaction_id: str, amount: float, reason: str) -> Dict[str, Any]:
        """微信支付退款"""
        # TODO: 实现微信支付退款 API
        return {
            "success": False,
            "error": "微信支付退款接口未实现",
        }

    def query_payment(self, transaction_id: str) -> Dict[str, Any]:
        """查询微信支付订单状态"""
        # TODO: 实现微信支付订单查询 API
        return {
            "success": False,
            "error": "微信支付订单查询接口未实现",
        }


class StripeGateway(PaymentGateway):
    """
    Stripe 支付网关（用于国际支付）

    TODO: 生产环境需要实现完整的 Stripe SDK 集成
    """

    def __init__(self, config: Dict[str, Any]):
        self.api_key = config.get("api_key", "")
        self.webhook_secret = config.get("webhook_secret", "")

    def create_payment(self, order_no: str, amount: float, description: str, **kwargs) -> Dict[str, Any]:
        """创建 Stripe 支付订单"""
        # TODO: 实现 Stripe SDK 调用
        logger.warning("[StripeGateway] Stripe 支付尚未实现，返回模拟响应")

        return {
            "payment_method": "stripe",
            "order_no": order_no,
            "amount": amount,
            "payment_intent_id": f"pi_{uuid.uuid4().hex[:16]}",
            "client_secret": None,  # TODO: Stripe client secret
            "status": "pending",
            "message": "Stripe 支付接口待实现",
        }

    def verify_callback(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """验证 Stripe Webhook 签名"""
        # TODO: 实现 Stripe Webhook 签名验证
        logger.warning("[StripeGateway] Webhook 验证尚未实现")
        return False, "Stripe Webhook 验证未实现"

    def refund(self, transaction_id: str, amount: float, reason: str) -> Dict[str, Any]:
        """Stripe 退款"""
        # TODO: 实现 Stripe 退款 API
        return {
            "success": False,
            "error": "Stripe 退款接口未实现",
        }

    def query_payment(self, transaction_id: str) -> Dict[str, Any]:
        """查询 Stripe 支付状态"""
        # TODO: 实现 Stripe 支付查询 API
        return {
            "success": False,
            "error": "Stripe 支付查询接口未实现",
        }


# ==================== 支付网关工厂 ====================


class PaymentGatewayFactory:
    """支付网关工厂类"""

    _gateways = {
        "mock": MockPaymentGateway,
        "alipay": AlipayGateway,
        "wechat": WeChatPayGateway,
        "stripe": StripeGateway,
    }

    @classmethod
    def register_gateway(cls, name: str, gateway_class):
        """注册新的支付网关"""
        cls._gateways[name] = gateway_class

    @classmethod
    def get_gateway(cls, name: str, config: Dict[str, Any] = None) -> PaymentGateway:
        """获取支付网关实例"""
        if name not in cls._gateways:
            raise PaymentGatewayError(f"不支持的支付方式：{name}")

        gateway_class = cls._gateways[name]
        return gateway_class(config or {})

    @classmethod
    def get_supported_methods(cls) -> list:
        """获取支持的支付方式"""
        return list(cls._gateways.keys())


# ==================== 全局支付管理器 ====================


class PaymentManager:
    """
    支付管理器 - 统一管理所有支付网关

    使用示例:
        payment_manager = PaymentManager()
        gateway = payment_manager.get_gateway("mock")
        result = gateway.create_payment(...)
    """

    def __init__(self, default_gateway: str = "mock"):
        self.default_gateway = default_gateway
        self._gateways: Dict[str, PaymentGateway] = {}

    def configure(self, payment_methods: Dict[str, Dict[str, Any]]):
        """
        配置支付方式

        Args:
            payment_methods: 支付方式配置字典
                {
                    "mock": {},  # 模拟支付不需要配置
                    "alipay": {"app_id": "...", "private_key": "..."},
                    "wechat": {"app_id": "...", "mch_id": "..."},
                    "stripe": {"api_key": "..."},
                }
        """
        for name, config in payment_methods.items():
            try:
                self._gateways[name] = PaymentGatewayFactory.get_gateway(name, config)
                logger.info(f"支付网关 [{name}] 已配置")
            except PaymentGatewayError as e:
                logger.error(f"支付网关 [{name}] 配置失败：{e}")

    def get_gateway(self, name: str = None) -> PaymentGateway:
        """获取支付网关实例"""
        gateway_name = name or self.default_gateway

        if gateway_name not in self._gateways:
            # 自动配置默认网关
            if gateway_name == "mock":
                self._gateways["mock"] = PaymentGatewayFactory.get_gateway("mock")
            else:
                raise PaymentGatewayError(f"支付网关 [{gateway_name}] 未配置")

        return self._gateways[gateway_name]

    def process_payment(self, order_no: str, amount: float, description: str,
                       payment_method: str = None, **kwargs) -> Dict[str, Any]:
        """
        处理支付请求

        Args:
            order_no: 订单号
            amount: 金额
            description: 订单描述
            payment_method: 支付方式（可选，默认使用配置的默认方式）
            **kwargs: 额外参数

        Returns:
            dict: 支付结果
        """
        gateway = self.get_gateway(payment_method)
        return gateway.create_payment(order_no, amount, description, **kwargs)

    def verify_callback(self, payment_method: str, data: Dict[str, Any]) -> Tuple[bool, str]:
        """验证支付回调"""
        gateway = self.get_gateway(payment_method)
        return gateway.verify_callback(data)

    def refund(self, payment_method: str, transaction_id: str, amount: float,
               reason: str) -> Dict[str, Any]:
        """处理退款"""
        gateway = self.get_gateway(payment_method)
        return gateway.refund(transaction_id, amount, reason)

    def get_supported_methods(self) -> list:
        """获取支持的支付方式"""
        return PaymentGatewayFactory.get_supported_methods()


# 全局单例
_payment_manager = PaymentManager(default_gateway="mock")


def get_payment_manager() -> PaymentManager:
    """获取支付管理器实例"""
    return _payment_manager


def initialize_payment_gateways(config: Dict[str, Dict[str, Any]] = None):
    """初始化支付网关"""
    if config:
        _payment_manager.configure(config)
    else:
        # 默认只启用模拟支付
        _payment_manager.configure({"mock": {}})

    logger.info(f"支付网关初始化完成，支持的方式：{PaymentGatewayFactory.get_supported_methods()}")
