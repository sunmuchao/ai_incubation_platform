"""
佣金服务 - 团长佣金计算、结算和提现
"""
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session
import logging

from models.entities import (
    CommissionRuleEntity, CommissionRecordEntity,
    OrganizerProfileEntity, GroupBuyEntity, OrderEntity
)
from models.product import CommissionRule, CommissionRecord, OrganizerProfile

logger = logging.getLogger(__name__)


class CommissionService:
    """佣金服务"""

    def __init__(self, db: Session):
        self.db = db

    # ========== 佣金规则管理 ==========

    def create_rule(self, data: Dict) -> CommissionRule:
        """创建佣金规则"""
        rule = CommissionRuleEntity(
            name=data["name"],
            commission_rate=data["commission_rate"],
            min_order_amount=data.get("min_order_amount", 0.0),
            max_commission=data.get("max_commission"),
            description=data.get("description"),
            is_active=data.get("is_active", True)
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)

        logger.info(f"佣金规则创建成功：{rule.id} - {rule.name}")
        return self._entity_to_model(rule)

    def get_rule(self, rule_id: str) -> Optional[CommissionRule]:
        """获取佣金规则详情"""
        rule = self.db.query(CommissionRuleEntity).filter(
            CommissionRuleEntity.id == rule_id
        ).first()
        return self._entity_to_model(rule) if rule else None

    def list_rules(self, active_only: bool = True) -> List[CommissionRule]:
        """获取佣金规则列表"""
        query = self.db.query(CommissionRuleEntity)
        if active_only:
            query = query.filter(CommissionRuleEntity.is_active == True)
        rules = query.order_by(CommissionRuleEntity.commission_rate).all()
        return [self._entity_to_model(r) for r in rules]

    def update_rule(self, rule_id: str, updates: Dict) -> Optional[CommissionRule]:
        """更新佣金规则"""
        rule = self.db.query(CommissionRuleEntity).filter(
            CommissionRuleEntity.id == rule_id
        ).first()
        if not rule:
            return None

        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)

        self.db.commit()
        self.db.refresh(rule)
        return self._entity_to_model(rule)

    def get_applicable_rule(self, organizer_id: str, order_amount: float) -> Optional[CommissionRule]:
        """获取适用于指定团长的佣金规则"""
        # 获取团长等级
        profile = self.get_organizer_profile(organizer_id)
        level = profile.level if profile else "normal"

        # 根据等级和订单金额匹配规则
        query = self.db.query(CommissionRuleEntity).filter(
            CommissionRuleEntity.is_active == True,
            CommissionRuleEntity.min_order_amount <= order_amount
        )

        # 根据等级筛选规则名称
        level_to_rule = {
            "normal": "普通团长",
            "gold": "金牌团长",
            "diamond": "钻石团长"
        }
        rule_name = level_to_rule.get(level, "普通团长")
        query = query.filter(CommissionRuleEntity.name == rule_name)

        rule = query.first()

        # 如果没有匹配到特定等级的规则，返回默认规则
        if not rule:
            rule = self.db.query(CommissionRuleEntity).filter(
                CommissionRuleEntity.is_active == True,
                CommissionRuleEntity.name == "默认规则"
            ).first()

        return self._entity_to_model(rule) if rule else None

    # ========== 佣金计算与结算 ==========

    def calculate_commission(
        self,
        organizer_id: str,
        group_buy_id: str,
        order_amount: float
    ) -> Dict:
        """计算佣金"""
        rule = self.get_applicable_rule(organizer_id, order_amount)

        if not rule:
            return {
                "commission_rate": 0.0,
                "commission_amount": 0.0,
                "rule_name": "无适用规则"
            }

        # 计算佣金
        commission_amount = order_amount * rule.commission_rate

        # 应用佣金上限
        if rule.max_commission and commission_amount > rule.max_commission:
            commission_amount = rule.max_commission

        return {
            "rule_id": rule.id,
            "rule_name": rule.name,
            "commission_rate": rule.commission_rate,
            "commission_amount": round(commission_amount, 2),
            "order_amount": order_amount
        }

    def settle_commission(self, group_buy_id: str) -> Optional[CommissionRecord]:
        """结算团购佣金（团购成功后调用）"""
        group_buy = self.db.query(GroupBuyEntity).filter(
            GroupBuyEntity.id == group_buy_id
        ).first()

        if not group_buy or group_buy.status != "success":
            logger.warning(f"团购 {group_buy_id} 无法结算佣金：状态异常")
            return None

        # 获取团购所有订单
        orders = self.db.query(OrderEntity).filter(
            OrderEntity.group_buy_id == group_buy_id,
            OrderEntity.status.in_(["paid", "completed"])
        ).all()

        if not orders:
            logger.warning(f"团购 {group_buy_id} 无有效订单，无法结算佣金")
            return None

        # 计算总订单金额
        total_amount = sum(o.total_amount for o in orders)
        order_ids = [o.id for o in orders]

        # 计算佣金
        commission_info = self.calculate_commission(
            group_buy.organizer_id,
            group_buy_id,
            total_amount
        )

        if commission_info["commission_amount"] <= 0:
            logger.info(f"团购 {group_buy_id} 佣金为 0，跳过结算")
            return None

        # 创建佣金记录
        record = CommissionRecordEntity(
            organizer_id=group_buy.organizer_id,
            group_buy_id=group_buy_id,
            order_ids=",".join(order_ids),
            total_amount=total_amount,
            commission_rate=commission_info["commission_rate"],
            commission_amount=commission_info["commission_amount"],
            status="pending",
            rule_id=commission_info["rule_id"]
        )
        self.db.add(record)

        # 更新团长档案
        self._update_organizer_profile(
            group_buy.organizer_id,
            commission_amount=commission_info["commission_amount"],
            order_count=len(orders),
            sales_amount=total_amount
        )

        self.db.commit()
        self.db.refresh(record)

        logger.info(
            f"佣金结算成功：团购 {group_buy_id}, "
            f"团长 {group_buy.organizer_id}, 金额 {commission_info['commission_amount']}"
        )
        return self._record_entity_to_model(record)

    # ========== 团长档案管理 ==========

    def get_organizer_profile(self, user_id: str) -> Optional[OrganizerProfile]:
        """获取团长档案"""
        profile = self.db.query(OrganizerProfileEntity).filter(
            OrganizerProfileEntity.user_id == user_id
        ).first()
        return self._profile_entity_to_model(profile) if profile else None

    def create_organizer_profile(self, user_id: str) -> OrganizerProfile:
        """创建团长档案"""
        # 检查是否已存在
        existing = self.get_organizer_profile(user_id)
        if existing:
            return existing

        profile = OrganizerProfileEntity(user_id=user_id)
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)

        logger.info(f"团长档案创建成功：{user_id}")
        return self._profile_entity_to_model(profile)

    def _update_organizer_profile(
        self,
        user_id: str,
        commission_amount: float = 0,
        order_count: int = 0,
        sales_amount: float = 0
    ) -> OrganizerProfile:
        """更新团长档案数据"""
        profile = self.db.query(OrganizerProfileEntity).filter(
            OrganizerProfileEntity.user_id == user_id
        ).first()

        if not profile:
            profile = OrganizerProfileEntity(user_id=user_id)
            self.db.add(profile)

        profile.total_commission += commission_amount
        profile.available_commission += commission_amount
        profile.total_orders += order_count
        profile.total_sales += sales_amount
        profile.last_active_at = datetime.now()

        # 根据业绩自动升级
        self._update_organizer_level(profile)

        self.db.commit()
        self.db.refresh(profile)
        return self._profile_entity_to_model(profile)

    def _update_organizer_level(self, profile: OrganizerProfileEntity) -> None:
        """根据业绩更新团长等级"""
        # 钻石团长：累计销售额 >= 100000 或 累计订单 >= 1000
        if profile.total_sales >= 100000 or profile.total_orders >= 1000:
            profile.level = "diamond"
        # 金牌团长：累计销售额 >= 10000 或 累计订单 >= 100
        elif profile.total_sales >= 10000 or profile.total_orders >= 100:
            profile.level = "gold"
        # 普通团长
        else:
            profile.level = "normal"

    def list_organizer_profiles(
        self,
        level: Optional[str] = None,
        limit: int = 50
    ) -> List[OrganizerProfile]:
        """获取团长列表"""
        query = self.db.query(OrganizerProfileEntity)
        if level:
            query = query.filter(OrganizerProfileEntity.level == level)
        profiles = query.order_by(
            OrganizerProfileEntity.total_commission.desc()
        ).limit(limit).all()
        return [self._profile_entity_to_model(p) for p in profiles]

    # ========== 佣金提现 ==========

    def withdraw_commission(
        self,
        organizer_id: str,
        amount: float
    ) -> Dict:
        """佣金提现"""
        profile = self.get_organizer_profile(organizer_id)
        if not profile:
            return {"success": False, "error": "团长档案不存在"}

        if profile.available_commission < amount:
            return {"success": False, "error": "可提现佣金不足"}

        if amount <= 0:
            return {"success": False, "error": "提现金额必须大于 0"}

        # 更新档案
        profile_entity = self.db.query(OrganizerProfileEntity).filter(
            OrganizerProfileEntity.user_id == organizer_id
        ).first()
        profile_entity.available_commission -= amount
        profile_entity.last_active_at = datetime.now()

        # 更新待结算佣金记录为已提现
        records = self.db.query(CommissionRecordEntity).filter(
            CommissionRecordEntity.organizer_id == organizer_id,
            CommissionRecordEntity.status == "pending"
        ).order_by(
            CommissionRecordEntity.created_at
        ).all()

        remaining = amount
        for record in records:
            if remaining <= 0:
                break
            if record.commission_amount <= remaining:
                record.status = "withdrawn"
                record.withdrawn_at = datetime.now()
                remaining -= record.commission_amount
            else:
                # 部分提现（简化处理：标记为已结算）
                record.status = "settled"
                record.withdrawn_at = datetime.now()
                remaining = 0

        self.db.commit()

        logger.info(
            f"佣金提现成功：团长 {organizer_id}, 金额 {amount}"
        )
        return {
            "success": True,
            "withdrawn_amount": amount,
            "remaining_commission": profile.available_commission
        }

    def list_commission_records(
        self,
        organizer_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[CommissionRecord]:
        """获取佣金记录列表"""
        query = self.db.query(CommissionRecordEntity).filter(
            CommissionRecordEntity.organizer_id == organizer_id
        )
        if status:
            query = query.filter(CommissionRecordEntity.status == status)
        records = query.order_by(
            CommissionRecordEntity.created_at.desc()
        ).limit(limit).all()
        return [self._record_entity_to_model(r) for r in records]

    # ========== 工具方法 ==========

    def _entity_to_model(self, entity: CommissionRuleEntity) -> CommissionRule:
        """实体转模型"""
        return CommissionRule(
            id=entity.id,
            name=entity.name,
            commission_rate=entity.commission_rate,
            min_order_amount=entity.min_order_amount,
            max_commission=entity.max_commission,
            description=entity.description,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )

    def _record_entity_to_model(self, entity: CommissionRecordEntity) -> CommissionRecord:
        """实体转模型"""
        return CommissionRecord(
            id=entity.id,
            organizer_id=entity.organizer_id,
            group_buy_id=entity.group_buy_id,
            order_ids=entity.order_ids.split(",") if entity.order_ids else [],
            total_amount=entity.total_amount,
            commission_rate=entity.commission_rate,
            commission_amount=entity.commission_amount,
            status=entity.status,
            rule_id=entity.rule_id,
            settled_at=entity.settled_at,
            withdrawn_at=entity.withdrawn_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )

    def _profile_entity_to_model(self, entity: OrganizerProfileEntity) -> OrganizerProfile:
        """实体转模型"""
        return OrganizerProfile(
            id=entity.id,
            user_id=entity.user_id,
            level=entity.level,
            total_commission=entity.total_commission,
            available_commission=entity.available_commission,
            total_orders=entity.total_orders,
            total_sales=entity.total_sales,
            rating=entity.rating,
            joined_at=entity.joined_at,
            last_active_at=entity.last_active_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
