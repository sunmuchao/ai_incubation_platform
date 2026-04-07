"""
分享裂变服务 - 分享链接生成、邀请追踪、奖励发放
"""
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session
import uuid
import logging

from models.entities import (
    ShareInviteEntity, ShareRewardRuleEntity,
    OrganizerProfileEntity, CouponEntity, CouponTemplateEntity
)
from models.product import ShareInvite, ShareRewardRule, ShareType

logger = logging.getLogger(__name__)


class ShareService:
    """分享裂变服务"""

    def __init__(self, db: Session):
        self.db = db

    # ========== 分享链接生成 ==========

    def generate_share_link(
        self,
        user_id: str,
        share_type: str,
        related_id: Optional[str] = None
    ) -> Dict:
        """生成分享链接/邀请码"""
        # 生成唯一邀请码
        invite_code = self._generate_invite_code(user_id)

        # 创建分享记录
        invite = ShareInviteEntity(
            inviter_id=user_id,
            invitee_id="",  # 待被邀请人填充
            invite_code=invite_code,
            share_type=share_type,
            related_id=related_id,
            status="pending",
            reward_amount=0.0,
            reward_status="pending"
        )
        self.db.add(invite)
        self.db.commit()
        self.db.refresh(invite)

        # 生成分享链接（实际项目中需要配置域名）
        base_url = "https://ai-community-buying.com"
        share_url = f"{base_url}/invite/{invite_code}"

        logger.info(
            f"分享链接生成成功：用户 {user_id}, 类型 {share_type}, 邀请码 {invite_code}"
        )
        return {
            "invite_code": invite_code,
            "share_url": share_url,
            "share_type": share_type,
            "related_id": related_id,
            "created_at": invite.created_at
        }

    def _generate_invite_code(self, user_id: str) -> str:
        """生成唯一邀请码"""
        unique_id = uuid.uuid4().hex[:6].upper()
        timestamp = datetime.now().strftime("%Y%m%d")
        # 可以使用用户 ID 的后几位增加辨识度
        user_suffix = user_id[-4:] if len(user_id) >= 4 else user_id
        return f"INV-{timestamp}-{unique_id}-{user_suffix}"

    # ========== 邀请转化 ==========

    def convert_invite(
        self,
        invite_code: str,
        invitee_id: str,
        order_amount: float = 0.0
    ) -> Dict:
        """邀请转化（被邀请人完成指定行为）"""
        # 查找邀请记录
        invite = self.db.query(ShareInviteEntity).filter(
            ShareInviteEntity.invite_code == invite_code
        ).first()

        if not invite:
            return {"success": False, "error": "邀请码无效"}

        if invite.status == "converted":
            return {"success": False, "error": "该邀请码已被使用"}

        # 获取奖励规则
        rule = self._get_reward_rule(invite.share_type)
        if not rule or not rule.is_active:
            logger.warning(f"分享类型 {invite.share_type} 无有效奖励规则")
            return {"success": False, "error": "该分享类型暂无奖励"}

        # 检查最低订单金额
        if order_amount < rule.min_order_amount:
            return {
                "success": False,
                "error": f"订单金额需满{rule.min_order_amount}元才能获得奖励"
            }

        # 检查邀请人每日奖励上限
        daily_reward = self._get_today_reward(invite.inviter_id)
        if daily_reward >= rule.max_reward_per_day:
            return {
                "success": False,
                "error": "邀请人今日奖励已达上限"
            }

        # 更新邀请记录
        invite.invitee_id = invitee_id
        invite.status = "converted"
        invite.converted_at = datetime.now()
        invite.reward_amount = rule.reward_value
        invite.reward_status = "pending"

        # 发放奖励
        reward_result = self._grant_reward(
            inviter_id=invite.inviter_id,
            reward_type=rule.reward_type,
            reward_value=rule.reward_value
        )

        if reward_result["success"]:
            invite.reward_status = "granted"

        self.db.commit()

        logger.info(
            f"邀请转化成功：邀请码 {invite_code}, "
            f"邀请人 {invite.inviter_id}, 被邀请人 {invitee_id}"
        )
        return {
            "success": True,
            "invite_code": invite_code,
            "inviter_id": invite.inviter_id,
            "invitee_id": invitee_id,
            "reward_type": rule.reward_type,
            "reward_amount": rule.reward_value,
            "reward_granted": reward_result["success"]
        }

    def _get_reward_rule(self, share_type: str) -> Optional[ShareRewardRule]:
        """获取分享奖励规则"""
        rule = self.db.query(ShareRewardRuleEntity).filter(
            ShareRewardRuleEntity.share_type == share_type,
            ShareRewardRuleEntity.is_active == True
        ).first()

        if not rule:
            return None

        return self._reward_rule_entity_to_model(rule)

    def _get_today_reward(self, user_id: str) -> float:
        """获取用户今日已获得的奖励总额"""
        today_start = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        invites = self.db.query(ShareInviteEntity).filter(
            ShareInviteEntity.inviter_id == user_id,
            ShareInviteEntity.created_at >= today_start,
            ShareInviteEntity.reward_status == "granted"
        ).all()

        return sum(i.reward_amount for i in invites)

    def _grant_reward(
        self,
        inviter_id: str,
        reward_type: str,
        reward_value: float
    ) -> Dict:
        """发放奖励"""
        if reward_type == "cash":
            # 现金奖励：更新团长档案
            return self._grant_cash_reward(inviter_id, reward_value)
        elif reward_type == "coupon":
            # 优惠券奖励：创建优惠券
            return self._grant_coupon_reward(inviter_id, reward_value)
        elif reward_type == "point":
            # 积分奖励（简化处理，记录日志）
            logger.info(f"积分奖励：用户 {inviter_id}, 积分 {reward_value}")
            return {"success": True, "reward_type": "point", "amount": reward_value}
        else:
            return {"success": False, "error": f"未知奖励类型：{reward_type}"}

    def _grant_cash_reward(
        self,
        user_id: str,
        amount: float
    ) -> Dict:
        """发放现金奖励"""
        # 查找或创建团长档案
        profile = self.db.query(OrganizerProfileEntity).filter(
            OrganizerProfileEntity.user_id == user_id
        ).first()

        if not profile:
            profile = OrganizerProfileEntity(user_id=user_id)
            self.db.add(profile)

        # 确保字段不为 None
        if profile.total_commission is None:
            profile.total_commission = 0.0
        if profile.available_commission is None:
            profile.available_commission = 0.0

        profile.total_commission += amount
        profile.available_commission += amount
        profile.last_active_at = datetime.now()

        self.db.commit()

        logger.info(f"现金奖励发放成功：用户 {user_id}, 金额 {amount}")
        return {"success": True, "reward_type": "cash", "amount": amount}

    def _grant_coupon_reward(
        self,
        user_id: str,
        template_value: float
    ) -> Dict:
        """发放优惠券奖励"""
        # 查找或创建专用的奖励优惠券模板
        template = self.db.query(CouponTemplateEntity).filter(
            CouponTemplateEntity.name == "邀请奖励券"
        ).first()

        if not template:
            # 创建默认奖励优惠券模板
            template = CouponTemplateEntity(
                name="邀请奖励券",
                type="fixed",
                value=template_value,
                min_purchase=0,
                total_quantity=100000,
                issued_quantity=0,
                used_quantity=0,
                valid_from=datetime.now(),
                valid_to=datetime.now().replace(year=datetime.now().year + 1),
                user_limit=0,  # 不限领取
                is_active=True
            )
            self.db.add(template)
            self.db.commit()
            self.db.refresh(template)

        # 创建优惠券
        coupon = CouponEntity(
            user_id=user_id,
            template_id=template.id,
            code=f"RWD-{uuid.uuid4().hex[:8].upper()}",
            status="available",
            valid_from=datetime.now(),
            valid_to=template.valid_to
        )
        self.db.add(coupon)

        # 更新模板发放数量
        template.issued_quantity += 1

        self.db.commit()
        self.db.refresh(coupon)

        logger.info(f"优惠券奖励发放成功：用户 {user_id}, 券码 {coupon.code}")
        return {
            "success": True,
            "reward_type": "coupon",
            "coupon_id": coupon.id,
            "coupon_code": coupon.code
        }

    # ========== 奖励规则管理 ==========

    def create_reward_rule(self, data: Dict) -> ShareRewardRule:
        """创建分享奖励规则"""
        rule = ShareRewardRuleEntity(
            name=data["name"],
            share_type=data["share_type"],
            reward_type=data.get("reward_type", "cash"),
            reward_value=data["reward_value"],
            min_order_amount=data.get("min_order_amount", 0.0),
            max_reward_per_day=data.get("max_reward_per_day", 100.0),
            is_active=data.get("is_active", True)
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)

        logger.info(f"分享奖励规则创建成功：{rule.id} - {rule.name}")
        return self._reward_rule_entity_to_model(rule)

    def get_reward_rule(self, rule_id: str) -> Optional[ShareRewardRule]:
        """获取分享奖励规则"""
        rule = self.db.query(ShareRewardRuleEntity).filter(
            ShareRewardRuleEntity.id == rule_id
        ).first()
        return self._reward_rule_entity_to_model(rule) if rule else None

    def list_reward_rules(
        self,
        active_only: bool = True,
        share_type: Optional[str] = None
    ) -> List[ShareRewardRule]:
        """获取分享奖励规则列表"""
        query = self.db.query(ShareRewardRuleEntity)
        if active_only:
            query = query.filter(ShareRewardRuleEntity.is_active == True)
        if share_type:
            query = query.filter(ShareRewardRuleEntity.share_type == share_type)
        rules = query.all()
        return [self._reward_rule_entity_to_model(r) for r in rules]

    def update_reward_rule(self, rule_id: str, updates: Dict) -> Optional[ShareRewardRule]:
        """更新分享奖励规则"""
        rule = self.db.query(ShareRewardRuleEntity).filter(
            ShareRewardRuleEntity.id == rule_id
        ).first()
        if not rule:
            return None

        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)

        self.db.commit()
        self.db.refresh(rule)
        return self._reward_rule_entity_to_model(rule)

    # ========== 分享记录查询 ==========

    def get_invite_record(self, invite_code: str) -> Optional[ShareInvite]:
        """获取邀请记录"""
        invite = self.db.query(ShareInviteEntity).filter(
            ShareInviteEntity.invite_code == invite_code
        ).first()
        return self._invite_entity_to_model(invite) if invite else None

    def get_user_invites(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[ShareInvite]:
        """获取用户的邀请记录列表"""
        invites = self.db.query(ShareInviteEntity).filter(
            ShareInviteEntity.inviter_id == user_id
        ).order_by(
            ShareInviteEntity.created_at.desc()
        ).limit(limit).all()

        return [self._invite_entity_to_model(i) for i in invites]

    def get_user_invite_stats(self, user_id: str) -> Dict:
        """获取用户邀请统计"""
        total = self.db.query(ShareInviteEntity).filter(
            ShareInviteEntity.inviter_id == user_id
        ).count()

        converted = self.db.query(ShareInviteEntity).filter(
            ShareInviteEntity.inviter_id == user_id,
            ShareInviteEntity.status == "converted"
        ).count()

        total_reward = self.db.query(ShareInviteEntity).filter(
            ShareInviteEntity.inviter_id == user_id,
            ShareInviteEntity.reward_status == "granted"
        ).all()
        total_reward_amount = sum(i.reward_amount for i in total_reward)

        today_reward = self._get_today_reward(user_id)

        return {
            "user_id": user_id,
            "total_invites": total,
            "converted_invites": converted,
            "conversion_rate": converted / total if total > 0 else 0,
            "total_reward": total_reward_amount,
            "today_reward": today_reward
        }

    # ========== 工具方法 ==========

    def _invite_entity_to_model(self, entity: ShareInviteEntity) -> ShareInvite:
        """实体转模型"""
        return ShareInvite(
            id=entity.id,
            inviter_id=entity.inviter_id,
            invitee_id=entity.invitee_id,
            invite_code=entity.invite_code,
            share_type=ShareType(entity.share_type),
            related_id=entity.related_id,
            status=entity.status,
            reward_amount=entity.reward_amount,
            reward_status=entity.reward_status,
            converted_at=entity.converted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )

    def _reward_rule_entity_to_model(self, entity: ShareRewardRuleEntity) -> ShareRewardRule:
        """实体转模型"""
        return ShareRewardRule(
            id=entity.id,
            name=entity.name,
            share_type=ShareType(entity.share_type),
            reward_type=entity.reward_type,
            reward_value=entity.reward_value,
            min_order_amount=entity.min_order_amount,
            max_reward_per_day=entity.max_reward_per_day,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
