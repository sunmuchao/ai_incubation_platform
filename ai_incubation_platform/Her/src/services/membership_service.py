"""
会员订阅服务 - SQLAlchemy 版本

Future 增强：
- 使用次数追踪（每日限制计数）
- 缓存失效集成
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
import uuid

from models.membership import (
    MembershipTier,
    MembershipFeature,
    UserMembership,
    MembershipOrder,
    MembershipCreate,
    MembershipBenefit,
    MEMBERSHIP_FEATURES,
    MEMBERSHIP_LIMITS,
    MEMBERSHIP_PRICES,
    MEMBERSHIP_BENEFITS,
    UserUsageTrackerDB,
)
from db.database import SessionLocal
from utils.db_session_manager import db_session, db_session_readonly, optional_db_session
from db.database import engine
from db.models import UserMembershipDB, MembershipOrderDB
from sqlalchemy.orm import Session
from utils.logger import logger
from cache import cache_manager
from services.base_service import BaseService


class MembershipService(BaseService):
    """会员订阅服务 - SQLAlchemy 版本"""

    def __init__(self, db: Session):
        super().__init__(db)

    def get_user_membership(self, user_id: str) -> UserMembership:
        """获取用户会员状态"""
        membership_db = self.db.query(UserMembershipDB).filter(
            UserMembershipDB.user_id == user_id,
            UserMembershipDB.status == "active"
        ).order_by(UserMembershipDB.end_date.desc()).first()

        if membership_db:
            return UserMembership(
                id=membership_db.id,
                user_id=membership_db.user_id,
                tier=MembershipTier(membership_db.tier),
                status=membership_db.status,
                start_date=membership_db.start_date,
                end_date=membership_db.end_date,
                auto_renew=membership_db.auto_renew,
                payment_method=membership_db.payment_method,
                subscription_id=membership_db.subscription_id,
                created_at=membership_db.created_at or datetime.now(),
                updated_at=membership_db.updated_at or datetime.now(),
            )

        # 返回免费会员状态
        return UserMembership(user_id=user_id, tier=MembershipTier.FREE, status='inactive')

    def check_feature_access(self, user_id: str, feature: MembershipFeature) -> bool:
        """检查用户是否有权访问某个会员权益"""
        membership = self.get_user_membership(user_id)
        return membership.has_feature(feature)

    def get_user_limit(self, user_id: str, limit_type: str) -> int:
        """获取用户某个限制的值 (-1 表示无限制)"""
        membership = self.get_user_membership(user_id)
        return membership.get_limit(limit_type)

    def _get_today_str(self) -> str:
        """获取今日日期字符串（YYYY-MM-DD）"""
        return datetime.now().strftime("%Y-%m-%d")

    def _get_usage_tracker(self, user_id: str, date: str) -> Optional[UserUsageTrackerDB]:
        """获取用户当日使用记录"""
        return self.db.query(UserUsageTrackerDB).filter(
            UserUsageTrackerDB.user_id == user_id,
            UserUsageTrackerDB.usage_date == date
        ).first()

    def _create_usage_tracker(self, user_id: str, date: str) -> UserUsageTrackerDB:
        """创建用户使用记录"""
        tracker = UserUsageTrackerDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            usage_date=date,
            like_count=0,
            super_like_count=0,
            rewind_count=0,
            boost_count=0,
        )
        self.db.add(tracker)
        self.db.commit()
        return tracker

    def _get_or_create_usage_tracker(self, user_id: str, date: str) -> UserUsageTrackerDB:
        """获取或创建用户使用记录"""
        tracker = self._get_usage_tracker(user_id, date)
        if not tracker:
            tracker = self._create_usage_tracker(user_id, date)
        return tracker

    def get_daily_usage_count(self, user_id: str, action: str) -> int:
        """获取用户今日某动作的使用次数"""
        today = self._get_today_str()
        tracker = self._get_usage_tracker(user_id, today)

        if not tracker:
            return 0

        action_map = {
            "like": lambda t: t.like_count,
            "super_like": lambda t: t.super_like_count,
            "rewind": lambda t: t.rewind_count,
            "boost": lambda t: t.boost_count,
        }

        if action in action_map:
            return action_map[action](tracker)
        return 0

    def increment_usage_count(self, user_id: str, action: str) -> bool:
        """
        增加用户使用次数

        Args:
            user_id: 用户 ID
            action: 动作类型 (like, super_like, rewind, boost)

        Returns:
            bool: 是否成功增加
        """
        today = self._get_today_str()
        tracker = self._get_or_create_usage_tracker(user_id, today)

        if action == "like":
            tracker.like_count += 1
        elif action == "super_like":
            tracker.super_like_count += 1
        elif action == "rewind":
            tracker.rewind_count += 1
        elif action == "boost":
            tracker.boost_count += 1
        else:
            return False

        self.db.commit()
        logger.info(f"User {user_id} usage incremented: {action}, count={tracker.__dict__.get(action + '_count', 0)}")
        return True

    def check_action_limit(self, user_id: str, action: str) -> Tuple[bool, str]:
        """
        检查用户是否可以执行某个动作
        返回：(是否允许，限制说明)
        """
        membership = self.get_user_membership(user_id)

        if action == "like":
            limit = membership.get_limit("daily_likes")
            if limit == -1:
                return True, ""
            # 检查今日已使用的喜欢次数
            used_count = self.get_daily_usage_count(user_id, "like")
            if used_count >= limit:
                return False, f"今日喜欢次数已达上限（{used_count}/{limit}）"
            return True, ""

        elif action == "super_like":
            limit = membership.get_limit("daily_super_likes")
            if limit == 0:
                return False, "超级喜欢是会员专属功能"
            # 检查今日已使用的超级喜欢次数
            used_count = self.get_daily_usage_count(user_id, "super_like")
            if used_count >= limit:
                return False, f"今日超级喜欢次数已达上限（{used_count}/{limit}）"
            return True, ""

        elif action == "rewind":
            limit = membership.get_limit("daily_rewinds")
            if limit == 0:
                return False, "回退功能是会员专属功能"
            # 检查今日已使用的回退次数
            used_count = self.get_daily_usage_count(user_id, "rewind")
            if used_count >= limit:
                return False, f"今日回退次数已达上限（{used_count}/{limit}）"
            return True, ""

        elif action == "boost":
            limit = membership.get_limit("daily_boosts")
            if limit == 0:
                return False, "加速曝光是高级会员专属功能"
            # 检查今日已使用的加速次数
            used_count = self.get_daily_usage_count(user_id, "boost")
            if used_count >= limit:
                return False, f"今日加速曝光次数已达上限（{used_count}/{limit}）"
            return True, ""

        return True, ""

    def get_membership_plans(self) -> List[Dict]:
        """获取所有会员计划"""
        plans = []

        for tier in [MembershipTier.STANDARD, MembershipTier.PREMIUM]:
            prices = MEMBERSHIP_PRICES[tier]
            features = MEMBERSHIP_FEATURES[tier]

            # 月度计划
            plans.append({
                "tier": tier.value,
                "duration_months": 1,
                "price": prices["monthly"],
                "original_price": prices["monthly"],
                "discount_rate": 0,
                "features": [f.value for f in features],
                "popular": tier == MembershipTier.PREMIUM,
            })

            # 季度计划
            plans.append({
                "tier": tier.value,
                "duration_months": 3,
                "price": prices["quarterly"],
                "original_price": prices["monthly"] * 3,
                "discount_rate": round(1 - prices["quarterly"] / (prices["monthly"] * 3), 2),
                "features": [f.value for f in features],
                "popular": False,
            })

            # 年度计划
            plans.append({
                "tier": tier.value,
                "duration_months": 12,
                "price": prices["yearly"],
                "original_price": prices["monthly"] * 12,
                "discount_rate": round(1 - prices["yearly"] / (prices["monthly"] * 12), 2),
                "features": [f.value for f in features],
                "popular": False,
            })

        return plans

    def get_membership_benefits(self) -> List[Dict]:
        """获取会员权益说明"""
        return [
            {
                "feature": b.feature.value,
                "name": b.name,
                "description": b.description,
                "icon": b.icon,
            }
            for b in MEMBERSHIP_BENEFITS
        ]

    def create_membership_order(self, user_id: str, request: MembershipCreate) -> MembershipOrder:
        """创建会员订单"""
        # 计算价格
        prices = MEMBERSHIP_PRICES[request.tier]
        duration_key = {1: "monthly", 3: "quarterly", 12: "yearly"}.get(
            request.duration_months, "monthly"
        )
        amount = prices.get(duration_key, prices["monthly"])

        order = MembershipOrder(
            user_id=user_id,
            tier=request.tier,
            duration_months=request.duration_months,
            amount=amount,
            original_amount=prices.get(duration_key, prices["monthly"]),
            payment_method=request.payment_method,
        )

        # 保存到数据库
        db = self.db
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO membership_orders
            (id, user_id, tier, duration_months, amount, original_amount, status, payment_method)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            order.id,
            order.user_id,
            order.tier.value,
            order.duration_months,
            order.amount,
            order.original_amount,
            order.status,
            order.payment_method,
        ))
        db.commit()
        cursor.close()

        logger.info(f"创建会员订单：user_id={user_id}, tier={request.tier}, amount={amount}")
        return order

    def create_membership_order_with_amount(
        self,
        user_id: str,
        tier: MembershipTier,
        duration_months: int,
        amount: float,
        original_amount: float,
        discount_code: Optional[str] = None,
        payment_method: str = "wechat",
        auto_renew: bool = False,
    ) -> MembershipOrder:
        """创建会员订单（指定金额，支持优惠券）"""
        order = MembershipOrder(
            user_id=user_id,
            tier=tier,
            duration_months=duration_months,
            amount=amount,
            original_amount=original_amount,
            discount_code=discount_code,
            payment_method=payment_method,
        )

        # 保存到数据库
        db = self.db
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO membership_orders
            (id, user_id, tier, duration_months, amount, original_amount, discount_code, status, payment_method)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            order.id,
            order.user_id,
            order.tier.value,
            order.duration_months,
            order.amount,
            order.original_amount,
            order.discount_code,
            order.status,
            order.payment_method,
        ))
        db.commit()
        cursor.close()

        logger.info(f"创建会员订单（含优惠）：user_id={user_id}, tier={tier}, original={original_amount}, final={amount}")
        return order

    def process_payment(self, order_id: str, payment_result: Dict) -> MembershipOrder:
        """处理支付结果"""
        db = self._get_db()
        cursor = db.cursor(dictionary=True)

        # 获取订单
        cursor.execute("SELECT * FROM membership_orders WHERE id = %s", (order_id,))
        order_row = cursor.fetchone()

        if not order_row:
            raise ValueError(f"订单不存在：{order_id}")

        order = MembershipOrder(
            id=order_row['id'],
            user_id=order_row['user_id'],
            tier=MembershipTier(order_row['tier']),
            duration_months=order_row['duration_months'],
            amount=order_row['amount'],
            original_amount=order_row['original_amount'],
            status=order_row['status'],
            payment_method=order_row.get('payment_method'),
            created_at=order_row['created_at'],
        )

        if payment_result.get("success"):
            # 支付成功，更新订单状态
            cursor.execute("""
                UPDATE membership_orders
                SET status = 'paid', payment_time = %s
                WHERE id = %s
            """, (datetime.now(), order_id))

            # 激活会员
            self._activate_membership(
                user_id=order.user_id,
                tier=order.tier,
                duration_months=order.duration_months,
                payment_method=order.payment_method,
                order_id=order_id,
            )

            logger.info(f"会员支付成功：order_id={order_id}, user_id={order.user_id}")
        else:
            # 支付失败
            cursor.execute("""
                UPDATE membership_orders
                SET status = 'failed'
                WHERE id = %s
            """, (order_id,))

            logger.warning(f"会员支付失败：order_id={order_id}")

        db.commit()
        cursor.close()

        order.status = "paid" if payment_result.get("success") else "failed"
        return order

    def _activate_membership(
        self,
        user_id: str,
        tier: MembershipTier,
        duration_months: int,
        payment_method: Optional[str] = None,
        order_id: Optional[str] = None,
    ):
        """激活会员"""
        db = self._get_db()
        cursor = db.cursor()

        # 检查现有会员状态
        cursor.execute("""
            SELECT * FROM user_memberships
            WHERE user_id = %s AND status = 'active'
            ORDER BY end_date DESC
            LIMIT 1
        """, (user_id,))

        existing = cursor.fetchone()
        now = datetime.now()

        if existing and existing['end_date'] and existing['end_date'] > now:
            # 现有会员未过期，顺延
            new_end_date = existing['end_date'] + timedelta(days=duration_months * 30)
            cursor.execute("""
                UPDATE user_memberships
                SET tier = %s, end_date = %s, updated_at = %s
                WHERE id = %s
            """, (tier.value, new_end_date, now, existing['id']))
        else:
            # 新开通会员
            start_date = now
            end_date = now + timedelta(days=duration_months * 30)
            membership_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO user_memberships
                (id, user_id, tier, status, start_date, end_date, auto_renew, payment_method, created_at, updated_at)
                VALUES (%s, %s, %s, 'active', %s, %s, %s, %s, %s, %s)
            """, (
                membership_id,
                user_id,
                tier.value,
                start_date,
                end_date,
                False,
                payment_method,
                now,
                now,
            ))

        db.commit()
        cursor.close()

        logger.info(f"激活会员：user_id={user_id}, tier={tier.value}, duration={duration_months}个月")

        # Future 增强：会员状态变更后失效用户缓存
        cache_manager.get_instance().invalidate_on_membership_change(user_id)

    def cancel_subscription(self, user_id: str) -> bool:
        """取消自动续费"""
        db = self._get_db()
        cursor = db.cursor()

        cursor.execute("""
            UPDATE user_memberships
            SET auto_renew = False, updated_at = %s
            WHERE user_id = %s AND status = 'active'
        """, (datetime.now(), user_id))

        affected = cursor.rowcount
        db.commit()
        cursor.close()

        if affected > 0:
            logger.info(f"取消自动续费：user_id={user_id}")

        return affected > 0

    def get_membership_stats(self) -> Dict:
        """获取会员统计信息"""
        db = self._get_db()
        cursor = db.cursor(dictionary=True)

        # 各等级会员数量
        cursor.execute("""
            SELECT tier, COUNT(*) as count
            FROM user_memberships
            WHERE status = 'active'
            GROUP BY tier
        """)
        tier_counts = {row['tier']: row['count'] for row in cursor.fetchall()}

        # 本月新增会员
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM user_memberships
            WHERE status = 'active'
            AND DATE_FORMAT(created_at, '%Y-%m') = DATE_FORMAT(CURDATE(), '%Y-%m')
        """)
        new_this_month = cursor.fetchone()['count']

        # 本月到期会员
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM user_memberships
            WHERE status = 'active'
            AND DATE_FORMAT(end_date, '%Y-%m') = DATE_FORMAT(CURDATE(), '%Y-%m')
        """)
        expired_this_month = cursor.fetchone()['count']

        # 本月收入
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as total
            FROM membership_orders
            WHERE status = 'paid'
            AND DATE_FORMAT(payment_time, '%Y-%m') = DATE_FORMAT(CURDATE(), '%Y-%m')
        """)
        revenue_this_month = cursor.fetchone()['total']

        # 本年收入
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as total
            FROM membership_orders
            WHERE status = 'paid'
            AND DATE_FORMAT(payment_time, '%Y') = DATE_FORMAT(CURDATE(), '%Y')
        """)
        revenue_this_year = cursor.fetchone()['total']

        cursor.close()

        return {
            "total_members": sum(tier_counts.values()),
            "free_members": tier_counts.get("free", 0),
            "standard_members": tier_counts.get("standard", 0),
            "premium_members": tier_counts.get("premium", 0),
            "new_members_this_month": new_this_month,
            "expired_members_this_month": expired_this_month,
            "revenue_this_month": float(revenue_this_month),
            "revenue_this_year": float(revenue_this_year),
        }

    def use_feature(self, user_id: str, feature: MembershipFeature) -> tuple[bool, str]:
        """
        使用会员权益（用于计数类权益）
        返回：(是否成功，消息)
        """
        membership = self.get_user_membership(user_id)

        if not membership.has_feature(feature):
            return False, f"需要 {membership.tier.value} 会员才能使用此功能"

        # 根据权益类型检查并增加使用次数
        feature_to_action = {
            MembershipFeature.SUPER_LIKES: "super_like",
            MembershipFeature.BOOST: "boost",
            MembershipFeature.REWIND: "rewind",
        }

        action = feature_to_action.get(feature)
        if action:
            # 检查是否超过限制
            can_use, message = self.check_action_limit(user_id, action)
            if not can_use:
                return False, message

            # 增加使用次数
            self.increment_usage_count(user_id, action)
            return True, f"成功使用 {feature.value}，当前可用次数：{self.get_limit_remaining(user_id, action)}"

        # 非计数类权益，直接使用
        return True, ""

    def get_limit_remaining(self, user_id: str, action: str) -> int:
        """获取某动作剩余可用次数"""
        membership = self.get_user_membership(user_id)
        limit = membership.get_limit(f"daily_{action}s")

        if limit == -1:
            return -1  # 无限制

        used = self.get_daily_usage_count(user_id, action)
        return max(0, limit - used)


# 全局服务实例（使用时需要传入 db session）
def get_membership_service(db: Session = None) -> MembershipService:
    """获取会员服务实例"""
    if db is None:
        raise ValueError("db session must be provided - use with db_session() as db: get_membership_service(db)")
    return MembershipService(db)
