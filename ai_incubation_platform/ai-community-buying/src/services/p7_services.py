"""
P7 阶段 - 游戏化运营和砍价玩法服务层

包含:
1. 成就系统服务 (AchievementService)
2. 排行榜服务 (LeaderboardService)
3. 砍价玩法服务 (BargainService)
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc, asc
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import json
import random
import logging

from models.p7_entities import (
    AchievementDefinitionEntity, UserAchievementEntity, AchievementBadgeEntity,
    LeaderboardEntity, LeaderboardHistoryEntity,
    BargainActivityEntity, BargainOrderEntity, BargainHelpEntity,
    AchievementType, AchievementTier, AchievementStatus,
    LeaderboardType, LeaderboardPeriod, BargainStatus
)
from models.p6_entities import PointsAccountEntity, PointsTransactionEntity
from core.logging_config import get_logger

logger = get_logger("services.p7")


# ====================  成就系统服务  ====================

class AchievementService:
    """成就系统服务"""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logger
        self.request_id = ""
        self.user_id = ""

    def set_request_context(self, request_id: str, user_id: str = ""):
        """设置请求上下文"""
        self.request_id = request_id
        self.user_id = user_id

    def _log(self, level: str, message: str, extra: dict = None):
        """结构化日志"""
        log_data = {"request_id": self.request_id, "user_id": self.user_id}
        if extra:
            log_data.update(extra)
        getattr(self.logger, level)(message, extra=log_data)

    def get_all_achievements(self, is_active: bool = True) -> List[AchievementDefinitionEntity]:
        """获取所有成就定义"""
        query = self.db.query(AchievementDefinitionEntity)
        if is_active:
            query = query.filter(AchievementDefinitionEntity.is_active == True)
        return query.order_by(AchievementDefinitionEntity.sort_order).all()

    def get_achievement_by_code(self, achievement_code: str) -> Optional[AchievementDefinitionEntity]:
        """通过成就代码获取成就定义"""
        return self.db.query(AchievementDefinitionEntity).filter(
            AchievementDefinitionEntity.achievement_code == achievement_code
        ).first()

    def get_user_achievements(self, user_id: str,
                              status: AchievementStatus = None) -> List[Dict]:
        """获取用户成就列表"""
        query = self.db.query(UserAchievementEntity).filter(
            UserAchievementEntity.user_id == user_id
        )
        if status:
            query = query.filter(UserAchievementEntity.status == status)

        user_achievements = query.all()

        # 关联成就定义信息
        result = []
        for ua in user_achievements:
            achievement_def = self.db.query(AchievementDefinitionEntity).filter(
                AchievementDefinitionEntity.id == ua.achievement_id
            ).first()
            if achievement_def:
                result.append({
                    "achievement": achievement_def,
                    "user_achievement": ua,
                    "progress_percent": round(ua.current_progress / ua.target_progress * 100, 2) if ua.target_progress > 0 else 0
                })

        return result

    def get_user_badges(self, user_id: str) -> List[AchievementBadgeEntity]:
        """获取用户徽章列表"""
        return self.db.query(AchievementBadgeEntity).filter(
            AchievementBadgeEntity.user_id == user_id
        ).all()

    def check_and_unlock_achievements(self, user_id: str,
                                       achievement_type: AchievementType,
                                       current_value: int,
                                       check_all: bool = False) -> List[Dict]:
        """
        检查并解锁成就

        Args:
            user_id: 用户 ID
            achievement_type: 成就类型
            current_value: 当前值 (如订单数、消费金额等)
            check_all: 是否检查所有成就 (包括已解锁的)

        Returns:
            新解锁的成就列表
        """
        unlocked_achievements = []

        # 获取该类型的所有成就定义
        query = self.db.query(AchievementDefinitionEntity).filter(
            AchievementDefinitionEntity.achievement_type == achievement_type,
            AchievementDefinitionEntity.is_active == True
        )

        for achievement_def in query.all():
            # 检查用户是否已有该成就记录
            user_achievement = self.db.query(UserAchievementEntity).filter(
                and_(
                    UserAchievementEntity.user_id == user_id,
                    UserAchievementEntity.achievement_id == achievement_def.id
                )
            ).first()

            # 如果成就已解锁且已领取奖励，跳过
            if user_achievement and user_achievement.status == AchievementStatus.CLAIMED:
                if not check_all:
                    continue

            # 检查是否达成条件
            if current_value >= achievement_def.condition_target:
                if not user_achievement:
                    # 创建新的成就记录
                    user_achievement = UserAchievementEntity(
                        id=f"ua_{user_id}_{achievement_def.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        user_id=user_id,
                        achievement_id=achievement_def.id,
                        current_progress=current_value,
                        target_progress=achievement_def.condition_target,
                        status=AchievementStatus.UNLOCKED,
                        unlocked_at=datetime.now(),
                        progress_data=json.dumps({
                            "achieved_at": datetime.now().isoformat(),
                            "final_value": current_value
                        })
                    )
                    self.db.add(user_achievement)

                    # 创建徽章
                    badge = self._create_badge(user_id, achievement_def)

                    unlocked_achievements.append({
                        "achievement": achievement_def,
                        "badge": badge,
                        "message": f"恭喜解锁成就：{achievement_def.achievement_name}"
                    })

                    self._log("info", f"用户解锁新成就", {
                        "achievement_id": achievement_def.id,
                        "achievement_name": achievement_def.achievement_name
                    })
                elif user_achievement.status == AchievementStatus.LOCKED:
                    # 更新已有成就状态
                    user_achievement.current_progress = current_value
                    user_achievement.status = AchievementStatus.UNLOCKED
                    user_achievement.unlocked_at = datetime.now()

                    # 创建徽章
                    badge = self._create_badge(user_id, achievement_def)

                    unlocked_achievements.append({
                        "achievement": achievement_def,
                        "badge": badge,
                        "message": f"恭喜解锁成就：{achievement_def.achievement_name}"
                    })
                elif user_achievement.status == AchievementStatus.IN_PROGRESS:
                    # 更新进度并解锁
                    user_achievement.current_progress = current_value
                    user_achievement.status = AchievementStatus.UNLOCKED
                    user_achievement.unlocked_at = datetime.now()

                    badge = self._create_badge(user_id, achievement_def)

                    unlocked_achievements.append({
                        "achievement": achievement_def,
                        "badge": badge,
                        "message": f"恭喜解锁成就：{achievement_def.achievement_name}"
                    })
                elif user_achievement.current_progress < current_value:
                    # 更新进度 (成就已解锁但未达成更高目标)
                    user_achievement.current_progress = current_value

        return unlocked_achievements

    def update_achievement_progress(self, user_id: str,
                                     achievement_type: AchievementType,
                                     increment_value: int) -> List[Dict]:
        """
        更新成就进度 (增量更新)

        Args:
            user_id: 用户 ID
            achievement_type: 成就类型
            increment_value: 增量值

        Returns:
            新解锁的成就列表
        """
        # 获取用户当前总进度
        total_progress = self._get_user_total_progress(user_id, achievement_type)
        return self.check_and_unlock_achievements(user_id, achievement_type, total_progress)

    def _get_user_total_progress(self, user_id: str,
                                  achievement_type: AchievementType) -> int:
        """获取用户某类型成就的总进度"""
        # 根据成就类型计算总进度
        if achievement_type == AchievementType.ORDER:
            # 从订单统计 (这里简化处理，实际需要从订单表统计)
            from models.entities import OrderEntity
            count = self.db.query(func.count(OrderEntity.id)).filter(
                OrderEntity.user_id == user_id
            ).scalar() or 0
            return count
        elif achievement_type == AchievementType.SIGNIN:
            # 从签到记录统计
            from models.p6_entities import SigninCalendarEntity
            count = self.db.query(func.count(SigninCalendarEntity.id)).filter(
                SigninCalendarEntity.user_id == user_id
            ).scalar() or 0
            return count
        elif achievement_type == AchievementType.SHARE:
            # 从分享记录统计
            from models.entities import ShareInviteEntity
            count = self.db.query(func.count(ShareInviteEntity.id)).filter(
                ShareInviteEntity.inviter_id == user_id
            ).scalar() or 0
            return count
        return 0

    def _create_badge(self, user_id: str,
                      achievement_def: AchievementDefinitionEntity) -> AchievementBadgeEntity:
        """创建成就徽章"""
        badge = AchievementBadgeEntity(
            id=f"badge_{user_id}_{achievement_def.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            user_id=user_id,
            achievement_id=achievement_def.id,
            badge_name=achievement_def.achievement_name,
            badge_icon=achievement_def.icon_url,
            tier=achievement_def.tier
        )
        self.db.add(badge)
        return badge

    def claim_achievement_reward(self, user_id: str,
                                  achievement_id: str) -> Tuple[Optional[Dict], bool]:
        """
        领取成就奖励

        Returns:
            (奖励信息，是否成功)
        """
        user_achievement = self.db.query(UserAchievementEntity).filter(
            and_(
                UserAchievementEntity.user_id == user_id,
                UserAchievementEntity.achievement_id == achievement_id
            )
        ).first()

        if not user_achievement:
            return {"error": "成就记录不存在"}, False

        if user_achievement.status != AchievementStatus.UNLOCKED:
            return {"error": "成就未解锁或奖励已领取"}, False

        # 获取成就定义
        achievement_def = self.db.query(AchievementDefinitionEntity).filter(
            AchievementDefinitionEntity.id == achievement_id
        ).first()

        if not achievement_def:
            return {"error": "成就定义不存在"}, False

        # 发放奖励
        reward_info = self._grant_reward(user_id, achievement_def)

        # 更新成就状态
        user_achievement.status = AchievementStatus.CLAIMED
        user_achievement.claimed_at = datetime.now()

        self.db.commit()

        self._log("info", "成就奖励领取成功", {
            "achievement_id": achievement_id,
            "reward_type": achievement_def.reward_type
        })

        return reward_info, True

    def _grant_reward(self, user_id: str,
                      achievement_def: AchievementDefinitionEntity) -> Dict:
        """发放成就奖励"""
        reward_type = achievement_def.reward_type
        reward_value = achievement_def.reward_value

        if reward_type == "points":
            # 发放积分奖励
            account = self.db.query(PointsAccountEntity).filter(
                PointsAccountEntity.user_id == user_id
            ).first()

            if not account:
                # 创建积分账户
                account = PointsAccountEntity(
                    id=f"pa_{user_id}",
                    user_id=user_id,
                    total_points=reward_value,
                    available_points=reward_value
                )
                self.db.add(account)
            else:
                account.total_points += reward_value
                account.available_points += reward_value

            # 记录流水
            transaction = PointsTransactionEntity(
                id=f"pt_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                user_id=user_id,
                transaction_type="earn",
                points_amount=reward_value,
                balance_after=account.available_points,
                source="achievement",
                source_id=achievement_def.id,
                description=f"成就奖励：{achievement_def.achievement_name}"
            )
            self.db.add(transaction)

            return {"type": "points", "amount": reward_value}

        elif reward_type == "coupon":
            # 发放优惠券 (简化处理，实际需要调用优惠券服务)
            return {"type": "coupon", "coupon_id": str(reward_value)}

        elif reward_type == "badge":
            return {"type": "badge", "badge_id": achievement_def.id}

        return {"type": "none"}


# ====================  排行榜服务  ====================

class LeaderboardService:
    """排行榜服务"""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logger
        self.request_id = ""
        self.user_id = ""

    def set_request_context(self, request_id: str, user_id: str = ""):
        """设置请求上下文"""
        self.request_id = request_id
        self.user_id = user_id

    def _log(self, level: str, message: str, extra: dict = None):
        """结构化日志"""
        log_data = {"request_id": self.request_id, "user_id": self.user_id}
        if extra:
            log_data.update(extra)
        getattr(self.logger, level)(message, extra=log_data)

    def get_leaderboard(self, leaderboard_type: LeaderboardType,
                        period: LeaderboardPeriod,
                        limit: int = 100) -> List[Dict]:
        """获取排行榜数据"""
        period_key = self._get_period_key(period)

        rankings = self.db.query(LeaderboardEntity).filter(
            and_(
                LeaderboardEntity.leaderboard_type == leaderboard_type,
                LeaderboardEntity.period == period,
                LeaderboardEntity.period_key == period_key
            )
        ).order_by(LeaderboardEntity.rank).limit(limit).all()

        return [
            {
                "rank": r.rank,
                "user_id": r.user_id,
                "score": float(r.score),
                "extra_data": json.loads(r.extra_data) if r.extra_data else None
            }
            for r in rankings
        ]

    def get_user_rank(self, user_id: str,
                       leaderboard_type: LeaderboardType,
                       period: LeaderboardPeriod) -> Optional[Dict]:
        """获取用户排名"""
        period_key = self._get_period_key(period)

        ranking = self.db.query(LeaderboardEntity).filter(
            and_(
                LeaderboardEntity.leaderboard_type == leaderboard_type,
                LeaderboardEntity.period == period,
                LeaderboardEntity.period_key == period_key,
                LeaderboardEntity.user_id == user_id
            )
        ).first()

        if ranking:
            return {
                "rank": ranking.rank,
                "score": float(ranking.score),
                "period": period.value,
                "leaderboard_type": leaderboard_type.value
            }
        return None

    def update_leaderboard(self, leaderboard_type: LeaderboardType,
                           period: LeaderboardPeriod,
                           user_scores: List[Tuple[str, Decimal]]) -> bool:
        """
        更新排行榜数据

        Args:
            leaderboard_type: 排行榜类型
            period: 周期
            user_scores: 用户分数列表 [(user_id, score), ...]
        """
        period_key = self._get_period_key(period)

        try:
            # 按分数排序
            sorted_scores = sorted(user_scores, key=lambda x: x[1], reverse=True)

            # 删除旧数据
            self.db.query(LeaderboardEntity).filter(
                and_(
                    LeaderboardEntity.leaderboard_type == leaderboard_type,
                    LeaderboardEntity.period == period,
                    LeaderboardEntity.period_key == period_key
                )
            ).delete()

            # 插入新数据
            for rank, (user_id, score) in enumerate(sorted_scores, 1):
                entry = LeaderboardEntity(
                    id=f"lb_{leaderboard_type.value}_{period_key}_{user_id}",
                    leaderboard_type=leaderboard_type,
                    period=period,
                    period_key=period_key,
                    user_id=user_id,
                    rank=rank,
                    score=score
                )
                self.db.add(entry)

            self.db.commit()
            self._log("info", "排行榜更新成功", {
                "type": leaderboard_type.value,
                "period": period.value,
                "count": len(user_scores)
            })
            return True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"更新排行榜失败：{str(e)}")
            return False

    def _get_period_key(self, period: LeaderboardPeriod) -> str:
        """获取周期标识"""
        now = datetime.now()

        if period == LeaderboardPeriod.DAILY:
            return now.strftime("%Y-%m-%d")
        elif period == LeaderboardPeriod.WEEKLY:
            # ISO 周
            return now.strftime("%Y-W%W")
        elif period == LeaderboardPeriod.MONTHLY:
            return now.strftime("%Y-%m")
        else:  # ALL_TIME
            return "all_time"

    def recalculate_user_rank(self, user_id: str,
                               leaderboard_type: LeaderboardType,
                               new_score: Decimal) -> bool:
        """重新计算用户排名"""
        period = LeaderboardPeriod.MONTHLY  # 默认月度榜
        period_key = self._get_period_key(period)

        try:
            # 获取或创建用户排名记录
            existing = self.db.query(LeaderboardEntity).filter(
                and_(
                    LeaderboardEntity.leaderboard_type == leaderboard_type,
                    LeaderboardEntity.period == period,
                    LeaderboardEntity.period_key == period_key,
                    LeaderboardEntity.user_id == user_id
                )
            ).first()

            if existing:
                existing.score = new_score
            else:
                new_entry = LeaderboardEntity(
                    id=f"lb_{leaderboard_type.value}_{period_key}_{user_id}",
                    leaderboard_type=leaderboard_type,
                    period=period,
                    period_key=period_key,
                    user_id=user_id,
                    rank=0,  # 临时排名
                    score=new_score
                )
                self.db.add(new_entry)

            # 重新计算所有排名
            all_entries = self.db.query(LeaderboardEntity).filter(
                and_(
                    LeaderboardEntity.leaderboard_type == leaderboard_type,
                    LeaderboardEntity.period == period,
                    LeaderboardEntity.period_key == period_key
                )
            ).order_by(desc(LeaderboardEntity.score)).all()

            for rank, entry in enumerate(all_entries, 1):
                entry.rank = rank

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"重新计算排名失败：{str(e)}")
            return False


# ====================  砍价玩法服务  ====================

class BargainService:
    """砍价玩法服务"""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logger
        self.request_id = ""
        self.user_id = ""

    def set_request_context(self, request_id: str, user_id: str = ""):
        """设置请求上下文"""
        self.request_id = request_id
        self.user_id = user_id

    def _log(self, level: str, message: str, extra: dict = None):
        """结构化日志"""
        log_data = {"request_id": self.request_id, "user_id": self.user_id}
        if extra:
            log_data.update(extra)
        getattr(self.logger, level)(message, extra=log_data)

    def get_active_activities(self) -> List[BargainActivityEntity]:
        """获取进行中的砍价活动"""
        now = datetime.now()
        return self.db.query(BargainActivityEntity).filter(
            and_(
                BargainActivityEntity.is_active == True,
                BargainActivityEntity.status == "ongoing",
                BargainActivityEntity.start_time <= now,
                BargainActivityEntity.end_time >= now
            )
        ).all()

    def get_activity_by_id(self, activity_id: str) -> Optional[BargainActivityEntity]:
        """获取砍价活动详情"""
        return self.db.query(BargainActivityEntity).filter(
            BargainActivityEntity.id == activity_id
        ).first()

    def create_bargain_order(self, activity_id: str,
                             user_id: str) -> Tuple[Optional[BargainOrderEntity], str]:
        """
        创建砍价订单

        Returns:
            (砍价订单，错误信息)
        """
        activity = self.get_activity_by_id(activity_id)

        if not activity:
            return None, "砍价活动不存在"

        if not activity.is_active:
            return None, "砍价活动已结束"

        now = datetime.now()
        if activity.start_time > now:
            return None, "砍价活动尚未开始"
        if activity.end_time < now:
            return None, "砍价活动已结束"

        # 检查库存
        if activity.used_stock >= activity.total_stock:
            return None, "活动库存已用完"

        # 检查用户是否已有进行中的砍价
        existing = self.db.query(BargainOrderEntity).filter(
            and_(
                BargainOrderEntity.activity_id == activity_id,
                BargainOrderEntity.user_id == user_id,
                BargainOrderEntity.status == BargainStatus.IN_PROGRESS
            )
        ).first()

        if existing:
            return existing, ""

        # 创建砍价订单
        bargain_no = f"B{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"
        expires_at = now + timedelta(hours=activity.duration_hours)

        bargain_order = BargainOrderEntity(
            id=f"bo_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            bargain_no=bargain_no,
            activity_id=activity_id,
            product_id=activity.product_id,
            user_id=user_id,
            original_price=activity.original_price,
            current_price=activity.initial_price,
            floor_price=activity.floor_price,
            bargain_count=0,
            max_bargain_count=activity.max_bargain_count,
            remaining_bargains=activity.max_bargain_count,
            status=BargainStatus.IN_PROGRESS,
            started_at=now,
            expires_at=expires_at
        )

        self.db.add(bargain_order)

        # 更新活动库存
        activity.used_stock += 1

        self.db.commit()
        self.db.refresh(bargain_order)

        self._log("info", "砍价订单创建成功", {
            "bargain_no": bargain_no,
            "activity_id": activity_id
        })

        return bargain_order, ""

    def help_bargain(self, bargain_order_id: str,
                     helper_user_id: str) -> Tuple[Optional[Dict], str]:
        """
        帮助砍价

        Returns:
            (砍价结果，错误信息)
        """
        bargain_order = self.db.query(BargainOrderEntity).filter(
            BargainOrderEntity.id == bargain_order_id
        ).first()

        if not bargain_order:
            return None, "砍价订单不存在"

        if bargain_order.status != BargainStatus.IN_PROGRESS:
            return None, "该砍价订单已结束"

        if bargain_order.expires_at < datetime.now():
            bargain_order.status = BargainStatus.EXPIRED
            self.db.commit()
            return None, "砍价已过期"

        if bargain_order.remaining_bargains <= 0:
            return None, "已达到最大砍价次数"

        # 检查助力者是否已砍过
        existing_help = self.db.query(BargainHelpEntity).filter(
            and_(
                BargainHelpEntity.bargain_order_id == bargain_order_id,
                BargainHelpEntity.helper_user_id == helper_user_id
            )
        ).first()

        if existing_help:
            return None, "您已经帮助砍过价了"

        # 检查助力者是否就是发起人
        if helper_user_id == bargain_order.user_id:
            return None, "不能给自己砍价"

        # 获取活动规则
        activity = self.get_activity_by_id(bargain_order.activity_id)
        if not activity:
            return None, "砍价活动不存在"

        # 计算砍价金额
        bargain_amount = self._calculate_bargain_amount(
            current_price=bargain_order.current_price,
            floor_price=bargain_order.floor_price,
            min_amount=activity.min_bargain_amount,
            max_amount=activity.max_bargain_amount,
            remaining_bargains=bargain_order.remaining_bargains,
            is_new_user=False  # 简化处理，假设不是新用户
        )

        # 确保不会砍到底价以下
        if bargain_order.current_price - bargain_amount < bargain_order.floor_price:
            bargain_amount = bargain_order.current_price - bargain_order.floor_price

        # 记录砍价
        price_before = bargain_order.current_price
        bargain_order.current_price -= bargain_amount
        bargain_order.bargain_count += 1
        bargain_order.remaining_bargains -= 1

        # 检查是否砍到底价
        if bargain_order.current_price <= bargain_order.floor_price:
            bargain_order.status = BargainStatus.SUCCESS
            bargain_order.completed_at = datetime.now()

        help_record = BargainHelpEntity(
            id=f"bh_{bargain_order_id}_{helper_user_id}",
            bargain_order_id=bargain_order_id,
            helper_user_id=helper_user_id,
            bargain_amount=bargain_amount,
            price_before=price_before,
            price_after=bargain_order.current_price
        )
        self.db.add(help_record)

        self.db.commit()

        result = {
            "bargain_amount": float(bargain_amount),
            "price_before": float(price_before),
            "price_after": float(bargain_order.current_price),
            "remaining_bargains": bargain_order.remaining_bargains,
            "is_success": bargain_order.status == BargainStatus.SUCCESS,
            "current_price": float(bargain_order.current_price),
            "floor_price": float(bargain_order.floor_price)
        }

        self._log("info", "砍价助力成功", {
            "bargain_order_id": bargain_order_id,
            "bargain_amount": float(bargain_amount)
        })

        return result, ""

    def _calculate_bargain_amount(self, current_price: Decimal,
                                   floor_price: Decimal,
                                   min_amount: Decimal,
                                   max_amount: Decimal,
                                   remaining_bargains: int,
                                   is_new_user: bool = False) -> Decimal:
        """
        计算砍价金额

        策略:
        1. 前期砍得多，后期砍得少
        2. 新用户砍得更多
        """
        # 剩余可砍总价
        remaining_amount = current_price - floor_price

        if remaining_bargains <= 0:
            return Decimal(0)

        # 基础随机范围
        base_min = float(min_amount)
        base_max = float(max_amount)

        # 根据剩余金额调整
        if remaining_amount < base_max:
            base_max = float(remaining_amount)

        # 新用户砍得更多
        if is_new_user:
            base_max = min(base_max * 1.5, float(remaining_amount))

        # 随机生成砍价金额
        bargain_amount = Decimal(str(random.uniform(base_min, base_max))).quantize(Decimal('0.01'))

        return max(min_amount, bargain_amount)

    def get_bargain_order(self, bargain_order_id: str) -> Optional[BargainOrderEntity]:
        """获取砍价订单详情"""
        return self.db.query(BargainOrderEntity).filter(
            BargainOrderEntity.id == bargain_order_id
        ).first()

    def get_bargain_helps(self, bargain_order_id: str) -> List[BargainHelpEntity]:
        """获取砍价助力记录"""
        return self.db.query(BargainHelpEntity).filter(
            BargainHelpEntity.bargain_order_id == bargain_order_id
        ).all()

    def complete_bargain_order(self, bargain_order_id: str,
                                user_id: str) -> Tuple[bool, str]:
        """
        完成砍价订单 (生成正式订单)

        Returns:
            (是否成功，错误信息)
        """
        bargain_order = self.get_bargain_order(bargain_order_id)

        if not bargain_order:
            return False, "砍价订单不存在"

        if bargain_order.user_id != user_id:
            return False, "无权限操作"

        if bargain_order.status != BargainStatus.SUCCESS:
            return False, "砍价尚未成功"

        if bargain_order.order_id:
            return False, "订单已生成"

        # 这里简化处理，实际应该调用订单服务生成正式订单
        # bargain_order.order_id = generated_order_id
        # bargain_order.ordered_at = datetime.now()

        self._log("info", "砍价订单完成", {
            "bargain_order_id": bargain_order_id
        })

        return True, ""
