"""
拼单返现服务 (任务#30)

功能：
- 拼单活动创建
- 返现规则配置
- 拼单进度追踪
- 返现自动发放
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import uuid
import logging

from models.p0_entities import (
    GroupBuyCashbackEntity,
    GroupBuyCashbackParticipantEntity,
    GroupBuyCashbackRecordEntity,
    GroupBuyCashbackStatus
)
from models.entities import GroupBuyEntity, ProductEntity

logger = logging.getLogger(__name__)


class GroupBuyCashbackService:
    """拼单返现服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_cashback_activity(
        self,
        creator_user_id: str,
        groupbuy_id: str,
        target_participants: int = 3,
        cashback_percentage: float = 0.2,
        max_cashback_amount: Optional[float] = None,
        deadline_hours: int = 24
    ) -> GroupBuyCashbackEntity:
        """创建拼单返现活动"""
        # 验证团购存在
        groupbuy = self.db.query(GroupBuyEntity).filter(
            GroupBuyEntity.id == groupbuy_id
        ).first()
        if not groupbuy:
            raise ValueError(f"团购 {groupbuy_id} 不存在")

        # 验证目标人数
        if target_participants < 2:
            raise ValueError("目标人数至少为 2 人")

        if target_participants > groupbuy.target_size:
            raise ValueError("目标人数不能超过团购总人数")

        # 验证返现比例
        if cashback_percentage <= 0 or cashback_percentage > 1:
            raise ValueError("返现比例必须在 0-1 之间")

        # 检查是否已有拼单返现活动
        existing = self.db.query(GroupBuyCashbackEntity).filter(
            and_(
                GroupBuyCashbackEntity.groupbuy_id == groupbuy_id,
                GroupBuyCashbackEntity.status == GroupBuyCashbackStatus.ACTIVE
            )
        ).first()
        if existing:
            raise ValueError("该团购已有进行中的拼单返现活动")

        # 创建拼单返现活动
        deadline = datetime.now() + timedelta(hours=deadline_hours)
        cashback = GroupBuyCashbackEntity(
            id=str(uuid.uuid4()),
            creator_user_id=creator_user_id,
            groupbuy_id=groupbuy_id,
            product_id=groupbuy.product_id,
            target_participants=target_participants,
            cashback_percentage=cashback_percentage,
            max_cashback_amount=max_cashback_amount,
            current_participants=1,
            status=GroupBuyCashbackStatus.ACTIVE,
            deadline=deadline,
            cashback_total=0.0,
            cashback_per_person=0.0
        )

        self.db.add(cashback)
        self.db.commit()
        self.db.refresh(cashback)

        logger.info(f"创建拼单返现活动：{cashback.id}, 目标人数：{target_participants}, 返现比例：{cashback_percentage}")
        return cashback

    def join_cashback(
        self,
        cashback_id: str,
        user_id: str,
        payment_amount: float
    ) -> GroupBuyCashbackParticipantEntity:
        """参与拼单返现"""
        cashback = self.db.query(GroupBuyCashbackEntity).filter(
            GroupBuyCashbackEntity.id == cashback_id
        ).first()

        if not cashback:
            raise ValueError("拼单返现活动不存在")

        # 检查活动状态
        if cashback.status != GroupBuyCashbackStatus.ACTIVE:
            raise ValueError(f"活动状态：{cashback.status}")

        # 检查是否过期
        if datetime.now() > cashback.deadline:
            cashback.status = GroupBuyCashbackStatus.EXPIRED
            self.db.commit()
            raise ValueError("活动已过期")

        # 检查是否已满
        if cashback.current_participants >= cashback.target_participants:
            raise ValueError("拼单已满")

        # 检查用户是否已参与
        existing = self.db.query(GroupBuyCashbackParticipantEntity).filter(
            and_(
                GroupBuyCashbackParticipantEntity.cashback_id == cashback_id,
                GroupBuyCashbackParticipantEntity.user_id == user_id
            )
        ).first()
        if existing:
            raise ValueError("您已参与该拼单")

        # 创建参与者记录
        participant = GroupBuyCashbackParticipantEntity(
            id=str(uuid.uuid4()),
            cashback_id=cashback_id,
            user_id=user_id,
            payment_amount=payment_amount,
            cashback_status="pending"
        )

        self.db.add(participant)

        # 更新参与人数
        cashback.current_participants += 1

        # 检查是否达成目标
        if cashback.current_participants >= cashback.target_participants:
            cashback.status = GroupBuyCashbackStatus.COMPLETED
            # 计算人均返现
            self._calculate_cashback(cashback)
            # 自动发放返现
            self._distribute_cashback(cashback)

        self.db.commit()
        self.db.refresh(participant)

        logger.info(f"用户 {user_id} 参与拼单返现：{cashback_id}, 当前人数：{cashback.current_participants}")
        return participant

    def get_cashback_progress(self, cashback_id: str) -> Dict[str, Any]:
        """获取拼单进度"""
        cashback = self.db.query(GroupBuyCashbackEntity).filter(
            GroupBuyCashbackEntity.id == cashback_id
        ).first()

        if not cashback:
            raise ValueError("拼单返现活动不存在")

        participants = self.db.query(GroupBuyCashbackParticipantEntity).filter(
            GroupBuyCashbackParticipantEntity.cashback_id == cashback_id
        ).all()

        remaining_time = (cashback.deadline - datetime.now()).total_seconds()

        return {
            "cashback_id": cashback_id,
            "status": cashback.status,
            "target_participants": cashback.target_participants,
            "current_participants": cashback.current_participants,
            "progress_percentage": (cashback.current_participants / cashback.target_participants) * 100,
            "cashback_percentage": cashback.cashback_percentage,
            "cashback_per_person": cashback.cashback_per_person,
            "deadline": cashback.deadline.isoformat(),
            "remaining_seconds": max(0, remaining_time),
            "participants": [
                {
                    "user_id": p.user_id,
                    "join_time": p.join_time.isoformat(),
                    "cashback_amount": p.cashback_amount,
                    "cashback_status": p.cashback_status
                }
                for p in participants
            ]
        }

    def get_user_cashbacks(self, user_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取用户的拼单返现列表"""
        query = self.db.query(GroupBuyCashbackEntity).filter(
            or_(
                GroupBuyCashbackEntity.creator_user_id == user_id,
                GroupBuyCashbackEntity.participants.any(user_id=user_id)
            )
        )

        if status:
            query = query.filter(GroupBuyCashbackEntity.status == status)

        cashbacks = query.all()

        return [
            {
                "cashback_id": c.id,
                "creator_id": c.creator_user_id,
                "groupbuy_id": c.groupbuy_id,
                "status": c.status,
                "target_participants": c.target_participants,
                "current_participants": c.current_participants,
                "cashback_per_person": c.cashback_per_person,
                "deadline": c.deadline.isoformat(),
                "is_creator": c.creator_user_id == user_id
            }
            for c in cashbacks
        ]

    def _calculate_cashback(self, cashback: GroupBuyCashbackEntity) -> None:
        """计算返现金额"""
        # 获取所有参与者的支付金额
        participants = self.db.query(GroupBuyCashbackParticipantEntity).filter(
            GroupBuyCashbackParticipantEntity.cashback_id == cashback.id
        ).all()

        total_payment = sum(p.payment_amount for p in participants)
        cashback_total = total_payment * cashback.cashback_percentage

        # 检查最高返现上限
        if cashback.max_cashback_amount and cashback_total > cashback.max_cashback_amount:
            cashback_total = cashback.max_cashback_amount

        cashback.cashback_total = cashback_total
        cashback.cashback_per_person = cashback_total / cashback.target_participants

        logger.info(f"计算返现：活动 {cashback.id}, 总金额 {cashback_total}, 人均 {cashback.cashback_per_person}")

    def _distribute_cashback(self, cashback: GroupBuyCashbackEntity) -> None:
        """自动发放返现"""
        participants = self.db.query(GroupBuyCashbackParticipantEntity).filter(
            GroupBuyCashbackParticipantEntity.cashback_id == cashback.id
        ).all()

        for participant in participants:
            participant.cashback_amount = cashback.cashback_per_person
            participant.cashback_status = "granted"

            # 创建返现记录
            record = GroupBuyCashbackRecordEntity(
                id=str(uuid.uuid4()),
                cashback_id=cashback.id,
                participant_id=participant.id,
                user_id=participant.user_id,
                cashback_amount=cashback.cashback_per_person,
                status="granted",
                granted_at=datetime.now()
            )
            self.db.add(record)

        logger.info(f"发放返现：活动 {cashback.id}, {len(participants)}人，人均 {cashback.cashback_per_person}")

    def withdraw_cashback(self, user_id: str, record_id: str) -> Dict[str, Any]:
        """提现返现"""
        record = self.db.query(GroupBuyCashbackRecordEntity).filter(
            GroupBuyCashbackRecordEntity.id == record_id
        ).first()

        if not record:
            return {"success": False, "message": "返现记录不存在"}

        if record.user_id != user_id:
            return {"success": False, "message": "无权操作"}

        if record.status != "granted":
            return {"success": False, "message": f"返现状态：{record.status}"}

        # 更新状态
        record.status = "withdrawn"
        record.withdrawn_at = datetime.now()

        # TODO: 调用支付系统进行实际提现

        self.db.commit()

        logger.info(f"用户 {user_id} 提现返现：{record_id}, 金额 {record.cashback_amount}")

        return {
            "success": True,
            "message": "提现成功",
            "amount": record.cashback_amount
        }

    def get_cashback_records(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的返现记录"""
        records = self.db.query(GroupBuyCashbackRecordEntity).filter(
            GroupBuyCashbackRecordEntity.user_id == user_id
        ).order_by(GroupBuyCashbackRecordEntity.created_at.desc()).all()

        return [
            {
                "record_id": r.id,
                "cashback_id": r.cashback_id,
                "amount": r.cashback_amount,
                "status": r.status,
                "granted_at": r.granted_at.isoformat() if r.granted_at else None,
                "withdrawn_at": r.withdrawn_at.isoformat() if r.withdrawn_at else None
            }
            for r in records
        ]

    def cancel_cashback(self, cashback_id: str, creator_user_id: str) -> Dict[str, Any]:
        """取消拼单返现活动（仅创建者可操作）"""
        cashback = self.db.query(GroupBuyCashbackEntity).filter(
            GroupBuyCashbackEntity.id == cashback_id
        ).first()

        if not cashback:
            return {"success": False, "message": "活动不存在"}

        if cashback.creator_user_id != creator_user_id:
            return {"success": False, "message": "仅创建者可取消"}

        if cashback.status != GroupBuyCashbackStatus.ACTIVE:
            return {"success": False, "message": f"活动状态：{cashback.status}"}

        # 更新状态
        cashback.status = GroupBuyCashbackStatus.EXPIRED

        # 退还参与者状态
        participants = self.db.query(GroupBuyCashbackParticipantEntity).filter(
            GroupBuyCashbackParticipantEntity.cashback_id == cashback_id
        ).all()
        for p in participants:
            p.cashback_status = "cancelled"

        self.db.commit()

        logger.info(f"取消拼单返现活动：{cashback_id}")

        return {"success": True, "message": "活动已取消"}
