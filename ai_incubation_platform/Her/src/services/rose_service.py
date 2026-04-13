"""
玫瑰表达服务

参考 Hinge 的玫瑰机制：
- 稀缺表达：每月有限玫瑰，不能滥用
- 优先展示：发送玫瑰后出现在对方的 Standout 列表
- 双向匹配：如果双方都发送玫瑰，形成特殊匹配
"""
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
import uuid
from sqlalchemy.orm import Session

from models.rose import (
    RoseBalance,
    RoseTransaction,
    RoseSendRequest,
    RoseSendResponse,
    RoseSource,
    RoseStatus,
    StandoutProfile,
    StandoutListResponse,
    ROSE_ALLOCATION,
    ROSE_PACKAGES,
    UserRoseBalanceDB,
    RoseTransactionDB,
    RosePurchaseDB,
)
from db.repositories import UserRepository
from utils.logger import logger
from services.membership_service import MembershipService
from models.membership import MembershipTier
from services.base_service import BaseService


class RoseService(BaseService):
    """玫瑰表达服务"""

    def __init__(self, db: Session):
        super().__init__(db)

    def get_user_balance(self, user_id: str) -> RoseBalance:
        """获取用户玫瑰余额"""
        # 获取或创建余额记录
        balance_db = self.db.query(UserRoseBalanceDB).filter(
            UserRoseBalanceDB.user_id == user_id
        ).first()

        if not balance_db:
            # 创建初始余额记录
            membership_svc = MembershipService(self.db)
            membership = membership_svc.get_user_membership(user_id)

            monthly_roses = ROSE_ALLOCATION.get(membership.tier.value, ROSE_ALLOCATION["free"])["monthly_roses"]

            balance_db = UserRoseBalanceDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                available_count=monthly_roses,
                total_received_this_month=monthly_roses,
                free_allocation=monthly_roses if membership.tier == MembershipTier.FREE else 0,
                membership_allocation=monthly_roses if membership.tier != MembershipTier.FREE else 0,
            )
            self.db.add(balance_db)
            self.db.commit()
            self.db.refresh(balance_db)

        # 计算下次刷新日期（下月初）
        now = datetime.now()
        next_refresh = datetime(now.year, now.month, 1) + timedelta(days=32)
        next_refresh = datetime(next_refresh.year, next_refresh.month, 1)

        return RoseBalance(
            user_id=user_id,
            available_count=balance_db.available_count,
            sent_count=balance_db.sent_this_month,
            monthly_allocation=balance_db.total_received_this_month,
            next_refresh_date=next_refresh,
            purchase_available=True,
        )

    def send_rose(
        self,
        sender_id: str,
        request: RoseSendRequest
    ) -> RoseSendResponse:
        """
        发送玫瑰

        Args:
            sender_id: 发送者 ID
            request: 发送请求

        Returns:
            RoseSendResponse: 发送结果
        """
        # 1. 检查余额
        balance = self.get_user_balance(sender_id)
        if balance.available_count <= 0:
            return RoseSendResponse(
                success=False,
                message="没有可用的玫瑰，请购买或等待下月刷新",
                roses_remaining=0,
            )

        # 2. 检查目标用户是否存在
        user_repo = UserRepository(self.db)
        target_user = user_repo.get_by_id(request.target_user_id)
        if not target_user:
            return RoseSendResponse(
                success=False,
                message="目标用户不存在",
                roses_remaining=balance.available_count,
            )

        # 3. 检查是否已经发送过玫瑰给同一用户
        existing = self.db.query(RoseTransactionDB).filter(
            RoseTransactionDB.sender_id == sender_id,
            RoseTransactionDB.receiver_id == request.target_user_id,
            RoseTransactionDB.status == RoseStatus.SENT.value,
        ).first()

        if existing:
            return RoseSendResponse(
                success=False,
                message="已经向该用户发送过玫瑰",
                roses_remaining=balance.available_count,
            )

        # 4. 确定使用的玫瑰来源
        balance_db = self.db.query(UserRoseBalanceDB).filter(
            UserRoseBalanceDB.user_id == sender_id
        ).first()

        rose_source = self._determine_rose_source(balance_db)

        # 5. 计算匹配度（使用 AI 判断）
        # 注：matchmaker 已废弃，使用 HerAdvisorService
        sender_user = user_repo.get_by_id(sender_id)
        if sender_user and target_user:
            from api.users import _from_db
            from services.her_advisor_service import get_her_advisor_service
            from services.user_profile_service import get_user_profile_service
            import asyncio

            sender_obj = _from_db(sender_user)
            target_obj = _from_db(target_user)

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            try:
                profile_service = get_user_profile_service()
                her_advisor = get_her_advisor_service()

                self_a, desire_a = loop.run_until_complete(
                    profile_service.get_or_create_profile(sender_id)
                )
                self_b, desire_b = loop.run_until_complete(
                    profile_service.get_or_create_profile(request.target_user_id)
                )

                advice = loop.run_until_complete(
                    her_advisor.generate_match_advice(
                        sender_id, (self_a, desire_a),
                        request.target_user_id, (self_b, desire_b)
                    )
                )
                score = advice.compatibility_score
            except Exception:
                score = 0.5
        else:
            score = 0.5

        # 6. 创建交易记录
        transaction = RoseTransactionDB(
            id=str(uuid.uuid4()),
            sender_id=sender_id,
            receiver_id=request.target_user_id,
            rose_source=rose_source.value,
            status=RoseStatus.SENT.value,
            message=request.message,
            compatibility_score=score,
            in_standout=True,
            standout_priority=int(score * 100),  # 匹配度越高，优先级越高
            standout_expires_at=datetime.now() + timedelta(hours=24),  # 24小时后在 Standout 中展示
        )
        self.db.add(transaction)

        # 7. 更新余额
        balance_db.available_count -= 1
        balance_db.sent_this_month += 1
        self.db.commit()

        # 8. 检查是否双向玫瑰（匹配）
        is_match = False
        reverse_rose = self.db.query(RoseTransactionDB).filter(
            RoseTransactionDB.sender_id == request.target_user_id,
            RoseTransactionDB.receiver_id == sender_id,
            RoseTransactionDB.status == RoseStatus.SENT.value,
        ).first()

        if reverse_rose:
            is_match = True
            # 更新双方状态为匹配
            transaction.status = RoseStatus.MATCHED.value if hasattr(RoseStatus, 'MATCHED') else "matched"
            reverse_rose.status = RoseStatus.MATCHED.value if hasattr(RoseStatus, 'MATCHED') else "matched"
            self.db.commit()

            logger.info(f"Rose match! {sender_id} <-> {request.target_user_id}")

        # 9. 创建匹配记录（如果双向喜欢）
        if is_match:
            from db.models import MatchHistoryDB
            match_record = MatchHistoryDB(
                id=str(uuid.uuid4()),
                user_id_1=sender_id,
                user_id_2=request.target_user_id,
                compatibility_score=score,
                status="matched",
                match_reasoning="双方互送玫瑰，形成特殊匹配",
            )
            self.db.add(match_record)
            self.db.commit()

        logger.info(f"Rose sent: {sender_id} -> {request.target_user_id}, source={rose_source}")

        return RoseSendResponse(
            success=True,
            message="玫瑰已发送，TA 将在 Standout 中看到你",
            roses_remaining=balance_db.available_count,
            transaction_id=transaction.id,
            is_match=is_match,
        )

    def _determine_rose_source(self, balance_db: UserRoseBalanceDB) -> RoseSource:
        """确定使用的玫瑰来源（优先使用免费，然后会员，最后购买）"""
        if balance_db.free_allocation > 0:
            balance_db.free_allocation -= 1
            return RoseSource.FREE_MONTHLY
        elif balance_db.membership_allocation > 0:
            balance_db.membership_allocation -= 1
            return RoseSource.MEMBERSHIP_STANDARD
        elif balance_db.purchased_count > 0:
            balance_db.purchased_count -= 1
            return RoseSource.PURCHASED
        elif balance_db.gifted_count > 0:
            balance_db.gifted_count -= 1
            return RoseSource.GIFT
        else:
            return RoseSource.FREE_MONTHLY  # 默认

    def get_standout_list(self, user_id: str) -> StandoutListResponse:
        """
        获取 Standout 列表（收到玫瑰的用户）

        Args:
            user_id: 用户 ID

        Returns:
            StandoutListResponse: Standout 列表
        """
        # 查询收到的玫瑰（未过期、在 Standout 中）
        roses = self.db.query(RoseTransactionDB).filter(
            RoseTransactionDB.receiver_id == user_id,
            RoseTransactionDB.in_standout == True,
            RoseTransactionDB.status == RoseStatus.SENT.value,
            RoseTransactionDB.standout_expires_at > datetime.now(),
        ).order_by(
            RoseTransactionDB.standout_priority.desc(),
            RoseTransactionDB.sent_at.desc()
        ).all()

        user_repo = UserRepository(self.db)
        profiles = []
        unread_count = 0

        for rose in roses:
            sender = user_repo.get_by_id(rose.sender_id)
            if not sender:
                continue

            if not rose.is_seen:
                unread_count += 1

            from api.users import _from_db
            sender_obj = _from_db(sender)

            profile = StandoutProfile(
                user_id=rose.sender_id,
                user_data={
                    "name": sender_obj.name,
                    "age": sender_obj.age,
                    "avatar_url": sender_obj.avatar_url,
                    "location": sender_obj.location,
                    "bio": sender_obj.bio,
                    "interests": sender_obj.interests,
                },
                rose_received_at=rose.sent_at,
                rose_count=1,
                latest_message=rose.message,
                compatibility_score=rose.compatibility_score or 0.5,
                standout_expires_at=rose.standout_expires_at,
                is_liked=False,
                is_passed=False,
            )
            profiles.append(profile)

        return StandoutListResponse(
            profiles=profiles,
            total_count=len(profiles),
            unread_count=unread_count,
        )

    def mark_rose_seen(self, transaction_id: str) -> bool:
        """标记玫瑰已查看"""
        transaction = self.db.query(RoseTransactionDB).filter(
            RoseTransactionDB.id == transaction_id
        ).first()

        if not transaction:
            return False

        transaction.is_seen = True
        transaction.seen_at = datetime.now()
        self.db.commit()

        return True

    def respond_to_standout(
        self,
        user_id: str,
        standout_user_id: str,
        action: str  # "like" or "pass"
    ) -> Tuple[bool, str]:
        """
        回应 Standout 用户

        Args:
            user_id: 当前用户 ID
            standout_user_id: Standout 用户 ID
            action: 动作（like 或 pass）

        Returns:
            (是否成功, 消息)
        """
        # 找到对应的玫瑰交易
        rose = self.db.query(RoseTransactionDB).filter(
            RoseTransactionDB.sender_id == standout_user_id,
            RoseTransactionDB.receiver_id == user_id,
            RoseTransactionDB.status == RoseStatus.SENT.value,
        ).first()

        if not rose:
            return False, "未找到对应的玫瑰记录"

        # 标记已查看
        rose.is_seen = True
        rose.seen_at = datetime.now()

        if action == "like":
            # 喜欢该用户，创建匹配
            rose.status = "matched"

            # 创建匹配记录
            from db.models import MatchHistoryDB
            match = MatchHistoryDB(
                id=str(uuid.uuid4()),
                user_id_1=standout_user_id,
                user_id_2=user_id,
                compatibility_score=rose.compatibility_score or 0.8,
                status="matched",
                match_reasoning="收到玫瑰后回应喜欢，形成匹配",
            )
            self.db.add(match)

            # 记录滑动行为
            from db.models import SwipeActionDB
            swipe = SwipeActionDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                target_user_id=standout_user_id,
                action="like",
            )
            self.db.add(swipe)

            self.db.commit()

            logger.info(f"Standout response: {user_id} liked {standout_user_id}")

            return True, "匹配成功！你们开始聊天吧"

        elif action == "pass":
            # 无感，从 Standout 移除
            rose.in_standout = False

            # 记录滑动行为
            from db.models import SwipeActionDB
            swipe = SwipeActionDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                target_user_id=standout_user_id,
                action="pass",
            )
            self.db.add(swipe)

            self.db.commit()

            logger.info(f"Standout response: {user_id} passed {standout_user_id}")

            return True, "已移除"

        return False, "无效操作"

    def purchase_roses(
        self,
        user_id: str,
        package_type: str,
        payment_method: str = "wechat"
    ) -> Tuple[bool, str, Optional[RosePurchaseDB]]:
        """
        购买玫瑰

        Args:
            user_id: 用户 ID
            package_type: 套餐类型 (single, bundle_3, bundle_5)
            payment_method: 支付方式

        Returns:
            (是否成功, 消息, 购买记录)
        """
        package = ROSE_PACKAGES.get(package_type)
        if not package:
            return False, "无效的套餐类型", None

        # 创建购买记录
        purchase = RosePurchaseDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            package_type=package_type,
            rose_count=package["count"],
            amount=package["price"],
            payment_method=payment_method,
            payment_status="pending",
        )
        self.db.add(purchase)
        self.db.commit()

        # 支付订单创建（当前为模拟流程，集成支付服务后可对接真实支付）

        logger.info(f"Rose purchase created: user={user_id}, package={package_type}, amount={package['price']}")

        return True, "购买订单已创建", purchase

    def complete_purchase(self, purchase_id: str) -> bool:
        """完成购买（支付成功后调用）"""
        purchase = self.db.query(RosePurchaseDB).filter(
            RosePurchaseDB.id == purchase_id
        ).first()

        if not purchase:
            return False

        purchase.payment_status = "paid"
        purchase.payment_time = datetime.now()

        # 更新用户余额
        balance_db = self.db.query(UserRoseBalanceDB).filter(
            UserRoseBalanceDB.user_id == purchase.user_id
        ).first()

        if balance_db:
            balance_db.available_count += purchase.rose_count
            balance_db.purchased_count += purchase.rose_count
            balance_db.total_received_this_month += purchase.rose_count
        else:
            # 如果没有余额记录，创建新的
            balance_db = UserRoseBalanceDB(
                id=str(uuid.uuid4()),
                user_id=purchase.user_id,
                available_count=purchase.rose_count,
                total_received_this_month=purchase.rose_count,
                purchased_count=purchase.rose_count,
            )
            self.db.add(balance_db)

        self.db.commit()

        logger.info(f"Rose purchase completed: purchase_id={purchase_id}, roses_added={purchase.rose_count}")

        return True

    def refresh_monthly_roses(self) -> int:
        """
        刷新所有用户的月度玫瑰（系统定时任务）

        Returns:
            刷新的用户数量
        """
        now = datetime.now()
        current_month = datetime(now.year, now.month, 1)

        # 查询所有余额记录
        balances = self.db.query(UserRoseBalanceDB).all()

        refreshed_count = 0
        for balance in balances:
            # 获取用户会员状态
            membership_svc = MembershipService(self.db)
            membership = membership_svc.get_user_membership(balance.user_id)

            monthly_roses = ROSE_ALLOCATION.get(membership.tier.value, ROSE_ALLOCATION["free"])["monthly_roses"]

            # 重置余额
            balance.available_count = monthly_roses
            balance.total_received_this_month = monthly_roses
            balance.sent_this_month = 0
            balance.free_allocation = monthly_roses if membership.tier == MembershipTier.FREE else 0
            balance.membership_allocation = monthly_roses if membership.tier != MembershipTier.FREE else 0
            balance.purchased_count = 0  # 保留购买的数量，不重置
            balance.gifted_count = 0
            balance.last_refresh_at = now

            refreshed_count += 1

        self.db.commit()

        logger.info(f"Monthly roses refreshed for {refreshed_count} users")

        return refreshed_count

    def get_rose_packages(self) -> List[dict]:
        """获取玫瑰购买套餐列表"""
        packages = []
        for package_type, package_info in ROSE_PACKAGES.items():
            packages.append({
                "type": package_type,
                "count": package_info["count"],
                "price": package_info["price"],
                "original_price": package_info["original_price"],
                "discount": package_info.get("discount"),
                "price_per_rose": round(package_info["price"] / package_info["count"], 2),
            })
        return packages


# 服务工厂函数
def get_rose_service(db: Session) -> RoseService:
    """获取玫瑰服务实例"""
    return RoseService(db)