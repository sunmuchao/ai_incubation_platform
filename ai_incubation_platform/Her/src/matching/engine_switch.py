"""
引擎切换器

管理双引擎的切换逻辑，包括：
- 付费状态检查
- 模式切换
- 计费统计
- 免责声明展示

架构：
┌─────────────────────────────────────────────────────────────────┐
│                    模式切换层                                    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              EngineSwitch                                │    │
│  │                                                         │    │
│  │  • 检查用户付费状态                                     │    │
│  │  • 切换引擎                                             │    │
│  │  • 计费统计                                             │    │
│  │                                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from matching.engine_base import (
    MatchEngine,
    MatchRequest,
    MatchResult,
    EngineType,
)
from matching.rule_engine import RuleMatchEngine, get_rule_engine
from matching.agentic_engine import AgenticMatchEngine, get_agentic_engine
from utils.logger import logger


class PaymentType(Enum):
    """付费类型"""
    NONE = "none"               # 未付费
    SUBSCRIPTION = "subscription"  # 订阅制
    PAY_PER_USE = "pay_per_use"   # 按次付费
    MEMBER_BENEFIT = "member_benefit"  # 会员权益


@dataclass
class PaymentStatus:
    """
    付费状态

    用户在许愿模式的付费情况
    """
    access: bool  # 是否有权限
    payment_type: PaymentType

    # 订阅信息
    subscription_expires_at: Optional[datetime] = None

    # 按次付费信息
    remaining_count: int = 0  # 剩余次数
    total_purchased: int = 0  # 总购买次数

    # 会员权益
    member_level: Optional[str] = None  # 黄金/铂金/VIP


@dataclass
class SwitchResult:
    """
    切换结果

    引擎切换操作的结果
    """
    success: bool
    engine_type: EngineType

    # 失败原因
    reason: Optional[str] = None
    message: Optional[str] = None

    # 付费信息（如果需要）
    pricing: Optional[Dict[str, Any]] = None

    # 免责声明
    warning: Optional[str] = None

    # 权限信息
    payment_status: Optional[PaymentStatus] = None


@dataclass
class PricingInfo:
    """
    定价信息

    许愿模式的定价方案
    """
    # 按次付费
    single_use: float = 9.9       # 单次许愿 ¥9.9
    pack_5: float = 39.9          # 5次套餐 ¥39.9
    pack_20: float = 99.9         # 20次套餐 ¥99.9

    # 订阅制
    monthly_subscription: float = 29.9   # 月度 ¥29.9/月
    quarterly_subscription: float = 69.9  # 季度 ¥69.9/季
    yearly_subscription: float = 199.9    # 年度 ¥199.9/年

    # 会员权益
    member_benefits: Dict[str, int] = field(default_factory=lambda: {
        "黄金会员": 10,   # 每月10次
        "铂金会员": -1,   # 无限次（用-1表示）
        "VIP会员": -1,    # 无限次 + 优先响应
    })


class PaymentChecker:
    """
    付费检查器

    检查用户是否有许愿模式的访问权限。
    支持多种付费方式：
    1. 订阅制（月/季/年）
    2. 按次付费（单次/套餐）
    3. 会员权益（黄金/铂金/VIP）
    """

    def __init__(self):
        """初始化付费检查器"""
        # 模拟用户付费状态存储
        # 实际应从数据库或支付系统获取
        self._payment_records: Dict[str, PaymentStatus] = {}
        logger.info("PaymentChecker initialized")

    async def check_wish_mode_access(self, user_id: str) -> PaymentStatus:
        """
        检查用户是否有许愿模式权限

        Args:
            user_id: 用户 ID

        Returns:
            PaymentStatus: 付费状态
        """
        # 查询数据库获取付费状态
        # 这里使用模拟数据，实际需接入支付系统
        payment_status = self._payment_records.get(user_id)

        if payment_status:
            # 检查订阅是否过期
            if payment_status.payment_type == PaymentType.SUBSCRIPTION:
                if payment_status.subscription_expires_at:
                    if datetime.now() > payment_status.subscription_expires_at:
                        # 订阅已过期
                        return PaymentStatus(
                            access=False,
                            payment_type=PaymentType.NONE
                        )
                    else:
                        # 订阅有效
                        return payment_status

            # 检查按次付费余额
            elif payment_status.payment_type == PaymentType.PAY_PER_USE:
                if payment_status.remaining_count > 0:
                    return payment_status
                else:
                    # 余额已用完
                    return PaymentStatus(
                        access=False,
                        payment_type=PaymentType.NONE
                    )

            # 会员权益
            elif payment_status.payment_type == PaymentType.MEMBER_BENEFIT:
                # 会员权益检查（实际应查询会员系统）
                return payment_status

        # 未付费用户 - 新用户首次免费体验
        # 给予一次免费体验机会
        return PaymentStatus(
            access=True,  # 首次体验免费
            payment_type=PaymentType.NONE,
            remaining_count=1  # 一次免费体验
        )

    async def record_payment(
        self,
        user_id: str,
        payment_type: PaymentType,
        details: Dict[str, Any]
    ) -> PaymentStatus:
        """
        记录用户付费

        Args:
            user_id: 用户 ID
            payment_type: 付费类型
            details: 付费详情

        Returns:
            PaymentStatus: 更新后的付费状态
        """
        if payment_type == PaymentType.SUBSCRIPTION:
            # 订阅制
            duration = details.get("duration", "monthly")
            if duration == "monthly":
                expires_at = datetime.now() + timedelta(days=30)
            elif duration == "quarterly":
                expires_at = datetime.now() + timedelta(days=90)
            elif duration == "yearly":
                expires_at = datetime.now() + timedelta(days=365)
            else:
                expires_at = datetime.now() + timedelta(days=30)

            status = PaymentStatus(
                access=True,
                payment_type=PaymentType.SUBSCRIPTION,
                subscription_expires_at=expires_at
            )

        elif payment_type == PaymentType.PAY_PER_USE:
            # 按次付费
            count = details.get("count", 1)
            existing = self._payment_records.get(user_id)
            remaining = existing.remaining_count if existing else 0

            status = PaymentStatus(
                access=True,
                payment_type=PaymentType.PAY_PER_USE,
                remaining_count=remaining + count,
                total_purchased=existing.total_purchased + count if existing else count
            )

        elif payment_type == PaymentType.MEMBER_BENEFIT:
            # 会员权益
            member_level = details.get("member_level", "黄金会员")
            status = PaymentStatus(
                access=True,
                payment_type=PaymentType.MEMBER_BENEFIT,
                member_level=member_level
            )

        else:
            status = PaymentStatus(
                access=False,
                payment_type=PaymentType.NONE
            )

        # 存储付费状态
        self._payment_records[user_id] = status

        logger.info(
            f"PaymentChecker: recorded payment for user={user_id}, "
            f"type={payment_type.value}"
        )

        return status

    async def consume_wish(self, user_id: str) -> Dict[str, Any]:
        """
        消耗一次许愿次数

        Args:
            user_id: 用户 ID

        Returns:
            消耗结果：
            - success: 是否成功
            - remaining: 剩余次数
            - type: 付费类型
        """
        payment_status = await self.check_wish_mode_access(user_id)

        if not payment_status.access:
            return {
                "success": False,
                "reason": "no_access",
                "message": "请购买许愿模式服务"
            }

        # 订阅制和会员权益不扣次数（无限次）
        if payment_status.payment_type == PaymentType.SUBSCRIPTION:
            return {
                "success": True,
                "type": "subscription",
                "remaining": -1  # 无限
            }

        if payment_status.payment_type == PaymentType.MEMBER_BENEFIT:
            # 检查会员权益次数限制
            benefits = PricingInfo.member_benefits
            limit = benefits.get(payment_status.member_level, 10)
            if limit == -1:
                return {
                    "success": True,
                    "type": "member_benefit",
                    "remaining": -1  # 无限
                }

        # 按次付费扣减次数
        if payment_status.payment_type == PaymentType.PAY_PER_USE:
            if payment_status.remaining_count <= 0:
                return {
                    "success": False,
                    "reason": "no_balance",
                    "message": "许愿次数已用完"
                }

            # 扣减
            payment_status.remaining_count -= 1
            self._payment_records[user_id] = payment_status

            return {
                "success": True,
                "type": "pay_per_use",
                "remaining": payment_status.remaining_count
            }

        # 首次免费体验
        if payment_status.payment_type == PaymentType.NONE and payment_status.remaining_count == 1:
            # 扣减免费体验次数
            payment_status.remaining_count = 0
            self._payment_records[user_id] = PaymentStatus(
                access=False,
                payment_type=PaymentType.NONE
            )

            return {
                "success": True,
                "type": "free_trial",
                "remaining": 0,
                "message": "免费体验已使用，请购买服务继续使用"
            }

        return {
            "success": False,
            "reason": "unknown",
            "message": "付费状态异常"
        }


class WishModeBilling:
    """
    许愿模式计费

    负责计费统计和消费记录
    """

    def __init__(self, payment_checker: PaymentChecker):
        """初始化计费服务"""
        self._payment_checker = payment_checker
        self._usage_records: Dict[str, List[Dict]] = {}  # 使用记录
        logger.info("WishModeBilling initialized")

    async def record_usage(
        self,
        user_id: str,
        session_id: str,
        candidates_count: int
    ) -> Dict[str, Any]:
        """
        记录使用情况

        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            candidates_count: 候选人数

        Returns:
            记录结果
        """
        # 消耗次数
        consume_result = await self._payment_checker.consume_wish(user_id)

        if not consume_result.get("success"):
            return consume_result

        # 记录使用情况
        usage_record = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "candidates_count": candidates_count,
            "billing_type": consume_result.get("type")
        }

        if user_id not in self._usage_records:
            self._usage_records[user_id] = []
        self._usage_records[user_id].append(usage_record)

        logger.info(
            f"WishModeBilling: recorded usage for user={user_id}, "
            f"session={session_id}"
        )

        return consume_result

    async def get_usage_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        获取使用统计

        Args:
            user_id: 用户 ID

        Returns:
            使用统计数据
        """
        records = self._usage_records.get(user_id, [])

        if not records:
            return {
                "total_sessions": 0,
                "total_candidates": 0,
                "first_used": None,
                "last_used": None
            }

        return {
            "total_sessions": len(records),
            "total_candidates": sum(r["candidates_count"] for r in records),
            "first_used": records[0]["timestamp"],
            "last_used": records[-1]["timestamp"],
            "by_type": self._aggregate_by_type(records)
        }

    def _aggregate_by_type(self, records: List[Dict]) -> Dict[str, int]:
        """按类型聚合"""
        counts = {}
        for r in records:
            type_ = r.get("billing_type", "unknown")
            counts[type_] = counts.get(type_, 0) + 1
        return counts


class EngineSwitch:
    """
    引擎切换器

    管理双引擎的切换逻辑
    """

    def __init__(self):
        """初始化引擎切换器"""
        self._rule_engine = get_rule_engine()
        self._agentic_engine = get_agentic_engine()
        self._payment_checker = PaymentChecker()
        self._billing = WishModeBilling(self._payment_checker)

        # 免责声明
        self._disclaimer = """
⚠️ 许愿模式服务说明：

1. AI顾问服务内容：
   • 帮助分析你的需求
   • 告知潜在风险和建议
   • 按你的意愿寻找匹配对象

2. 服务边界：
   • AI不保证一定能找到理想对象
   • AI不保证匹配成功后能发展关系
   • 最终能否聊得来，取决于你们双方
   • 感情需要双方经营，不是条件匹配就够了

3. 退款政策：
   • 按次付费：一经使用，不支持退款
   • 订阅制：可按剩余天数比例退款

4. 风险提示：
   • 多个硬性条件叠加会缩小匹配池
   • 过于追求"完美"可能错过合适的人
   • 建议适当放宽条件，给更多候选人机会
"""

        logger.info("EngineSwitch initialized")

    async def switch_to_wish_mode(
        self,
        user_id: str
    ) -> SwitchResult:
        """
        切换到许愿模式

        Args:
            user_id: 用户 ID

        Returns:
            SwitchResult: 切换结果
        """
        # 检查付费状态
        payment_status = await self._payment_checker.check_wish_mode_access(user_id)

        if not payment_status.access:
            # 未付费
            return SwitchResult(
                success=False,
                engine_type=EngineType.RULE,
                reason="need_payment",
                message="许愿模式为付费服务，请先购买",
                pricing=self._get_pricing_info(),
                payment_status=payment_status
            )

        # 付费用户或免费体验
        return SwitchResult(
            success=True,
            engine_type=EngineType.AGENTIC,
            warning=self._disclaimer,
            payment_status=payment_status
        )

    async def switch_to_rule_mode(
        self,
        user_id: str
    ) -> SwitchResult:
        """
        切换到常规模式

        Args:
            user_id: 用户 ID

        Returns:
            SwitchResult: 切换结果（常规模式免费，无需检查）
        """
        return SwitchResult(
            success=True,
            engine_type=EngineType.RULE,
            message="已切换到常规模式（免费）"
        )

    async def match(
        self,
        request: MatchRequest,
        engine_type: EngineType = EngineType.RULE
    ) -> MatchResult:
        """
        执行匹配（自动选择引擎）

        Args:
            request: 匹配请求
            engine_type: 指定引擎类型

        Returns:
            MatchResult: 匹配结果
        """
        if engine_type == EngineType.AGENTIC:
            # 许愿模式需要检查付费
            payment_status = await self._payment_checker.check_wish_mode_access(request.user_id)

            if not payment_status.access:
                return MatchResult(
                    success=False,
                    error="请购买许愿模式服务",
                    error_code="NO_ACCESS",
                    engine_type=EngineType.AGENTIC
                )

            # 执行许愿模式匹配
            result = await self._agentic_engine.match(request)

            # 计费
            if result.success:
                session = self._agentic_engine.create_session(
                    request.user_id,
                    request.wish_description or ""
                )
                await self._billing.record_usage(
                    request.user_id,
                    session.session_id,
                    len(result.candidates)
                )

            return result

        else:
            # 常规模式（免费）
            return await self._rule_engine.match(request)

    def get_pricing(self) -> Dict[str, Any]:
        """获取定价信息"""
        return self._get_pricing_info()

    def _get_pricing_info(self) -> Dict[str, Any]:
        """获取定价信息"""
        pricing = PricingInfo()

        return {
            "pay_per_use": {
                "single": {
                    "price": pricing.single_use,
                    "unit": "¥",
                    "description": "单次许愿"
                },
                "pack_5": {
                    "price": pricing.pack_5,
                    "unit": "¥",
                    "description": "5次套餐（省¥9.6）"
                },
                "pack_20": {
                    "price": pricing.pack_20,
                    "unit": "¥",
                    "description": "20次套餐（省¥98）"
                }
            },
            "subscription": {
                "monthly": {
                    "price": pricing.monthly_subscription,
                    "unit": "¥/月",
                    "description": "月度会员（无限次许愿）"
                },
                "quarterly": {
                    "price": pricing.quarterly_subscription,
                    "unit": "¥/季",
                    "description": "季度会员（无限次许愿）"
                },
                "yearly": {
                    "price": pricing.yearly_subscription,
                    "unit": "¥/年",
                    "description": "年度会员（无限次许愿）"
                }
            },
            "member_benefits": pricing.member_benefits,
            "disclaimer": self._disclaimer
        }

    async def get_user_usage(self, user_id: str) -> Dict[str, Any]:
        """获取用户使用统计"""
        return await self._billing.get_usage_statistics(user_id)

    def get_current_engine(self, user_id: str) -> EngineType:
        """
        获取用户当前使用的引擎类型

        Args:
            user_id: 用户 ID

        Returns:
            EngineType: 当前引擎类型
        """
        # 默认为常规模式
        # 如果用户在许愿会话中，返回 Agentic
        session = self._agentic_engine._sessions.get(user_id)
        if session and not session.is_completed:
            return EngineType.AGENTIC

        return EngineType.RULE


# 全局引擎切换器实例
_engine_switch_instance: Optional[EngineSwitch] = None


def get_engine_switch() -> EngineSwitch:
    """
    获取引擎切换器实例

    Returns:
        EngineSwitch: 全局引擎切换器实例
    """
    global _engine_switch_instance
    if _engine_switch_instance is None:
        _engine_switch_instance = EngineSwitch()
    return _engine_switch_instance