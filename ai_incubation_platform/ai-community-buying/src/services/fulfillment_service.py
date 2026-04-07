"""
履约追踪服务
负责履约记录管理、状态流转、事件追踪
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional, Tuple
from datetime import datetime
import json
import logging

from models.entities import FulfillmentEntity, FulfillmentEventEntity, OrderEntity, GroupBuyEntity
from models.product import FulfillmentStatus, EventType
from core.logging_config import get_logger

logger = get_logger("services.fulfillment")


class FulfillmentService:
    """履约追踪服务"""

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

    def create_fulfillment(self, data: dict) -> Tuple[FulfillmentEntity, bool]:
        """
        创建履约记录

        Args:
            data: 包含 order_id, group_buy_id, tracking_number, carrier, warehouse_id

        Returns:
            (履约记录实体，是否成功)
        """
        try:
            # 验证订单是否存在
            order = self.db.query(OrderEntity).filter(
                OrderEntity.id == data["order_id"]
            ).first()

            if not order:
                self._log("error", "订单不存在", {"order_id": data["order_id"]})
                return None, False

            # 验证团购是否存在
            group_buy = self.db.query(GroupBuyEntity).filter(
                GroupBuyEntity.id == data["group_buy_id"]
            ).first()

            if not group_buy:
                self._log("error", "团购不存在", {"group_buy_id": data["group_buy_id"]})
                return None, False

            # 检查是否已存在履约记录
            existing = self.db.query(FulfillmentEntity).filter(
                FulfillmentEntity.order_id == data["order_id"]
            ).first()

            if existing:
                self._log("warning", "履约记录已存在", {"order_id": data["order_id"]})
                return existing, True

            # 创建履约记录
            fulfillment = FulfillmentEntity(
                order_id=data["order_id"],
                group_buy_id=data["group_buy_id"],
                tracking_number=data.get("tracking_number"),
                carrier=data.get("carrier"),
                warehouse_id=data.get("warehouse_id"),
                status="pending"
            )

            self.db.add(fulfillment)
            self.db.commit()
            self.db.refresh(fulfillment)

            # 创建初始事件（订单创建）
            self.create_event(fulfillment.id, EventType.ORDER_CREATED, "订单已创建")

            self._log("info", "履约记录创建成功", {
                "fulfillment_id": fulfillment.id,
                "order_id": data["order_id"]
            })

            return fulfillment, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"创建履约记录失败：{str(e)}", {"data": data})
            return None, False

    def update_status(self, fulfillment_id: str, new_status: FulfillmentStatus,
                     notes: str = None) -> Tuple[Optional[FulfillmentEntity], bool]:
        """
        更新履约状态

        Args:
            fulfillment_id: 履约记录 ID
            new_status: 新状态
            notes: 备注信息

        Returns:
            (履约记录实体，是否成功)
        """
        try:
            fulfillment = self.db.query(FulfillmentEntity).filter(
                FulfillmentEntity.id == fulfillment_id
            ).first()

            if not fulfillment:
                self._log("error", "履约记录不存在", {"fulfillment_id": fulfillment_id})
                return None, False

            old_status = fulfillment.status
            fulfillment.status = new_status.value if isinstance(new_status, FulfillmentStatus) else new_status
            fulfillment.updated_at = datetime.now()

            if notes:
                fulfillment.notes = notes

            # 根据状态设置对应的时间戳
            if new_status == FulfillmentStatus.SHIPPING:
                fulfillment.shipped_at = datetime.now()
                self.create_event(fulfillment_id, EventType.SHIPPED, "已发货")
            elif new_status == FulfillmentStatus.DELIVERED:
                fulfillment.delivered_at = datetime.now()
                self.create_event(fulfillment_id, EventType.ARRIVED, "已到达自提点")
            elif new_status == FulfillmentStatus.COMPLETED:
                fulfillment.completed_at = datetime.now()
                self.create_event(fulfillment_id, EventType.COMPLETED, "已完成")
            elif new_status == FulfillmentStatus.CANCELLED:
                fulfillment.cancelled_at = datetime.now()

            self.db.commit()
            self.db.refresh(fulfillment)

            self._log("info", "履约状态更新成功", {
                "fulfillment_id": fulfillment_id,
                "old_status": old_status,
                "new_status": new_status.value if isinstance(new_status, FulfillmentStatus) else new_status
            })

            return fulfillment, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"更新履约状态失败：{str(e)}", {
                "fulfillment_id": fulfillment_id,
                "new_status": new_status
            })
            return None, False

    def create_event(self, fulfillment_id: str, event_type: EventType,
                    description: str, location: str = None,
                    operator: str = None, extra_data: dict = None) -> Tuple[Optional[FulfillmentEventEntity], bool]:
        """
        创建履约事件

        Args:
            fulfillment_id: 履约记录 ID
            event_type: 事件类型
            description: 事件描述
            location: 事件地点
            operator: 操作人
            extra_data: 额外数据

        Returns:
            (事件实体，是否成功)
        """
        try:
            # 验证履约记录是否存在
            fulfillment = self.db.query(FulfillmentEntity).filter(
                FulfillmentEntity.id == fulfillment_id
            ).first()

            if not fulfillment:
                self._log("error", "履约记录不存在", {"fulfillment_id": fulfillment_id})
                return None, False

            event = FulfillmentEventEntity(
                fulfillment_id=fulfillment_id,
                event_type=event_type.value if isinstance(event_type, EventType) else event_type,
                event_time=datetime.now(),
                location=location,
                description=description,
                operator=operator,
                extra_data=json.dumps(extra_data) if extra_data else None
            )

            self.db.add(event)
            self.db.commit()
            self.db.refresh(event)

            self._log("info", "履约事件创建成功", {
                "fulfillment_id": fulfillment_id,
                "event_type": event_type.value if isinstance(event_type, EventType) else event_type
            })

            return event, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"创建履约事件失败：{str(e)}", {
                "fulfillment_id": fulfillment_id,
                "event_type": event_type
            })
            return None, False

    def get_fulfillment(self, fulfillment_id: str) -> Optional[FulfillmentEntity]:
        """获取履约记录详情"""
        return self.db.query(FulfillmentEntity).filter(
            FulfillmentEntity.id == fulfillment_id
        ).first()

    def get_fulfillment_by_order(self, order_id: str) -> Optional[FulfillmentEntity]:
        """根据订单 ID 获取履约记录"""
        return self.db.query(FulfillmentEntity).filter(
            FulfillmentEntity.order_id == order_id
        ).first()

    def get_fulfillment_events(self, fulfillment_id: str) -> List[FulfillmentEventEntity]:
        """获取履约事件列表"""
        return self.db.query(FulfillmentEventEntity).filter(
            FulfillmentEventEntity.fulfillment_id == fulfillment_id
        ).order_by(FulfillmentEventEntity.event_time).all()

    def list_fulfillments(self, status: str = None, group_buy_id: str = None,
                         limit: int = 100, offset: int = 0) -> Tuple[List[FulfillmentEntity], int]:
        """
        获取履约记录列表

        Args:
            status: 状态过滤
            group_buy_id: 团购 ID 过滤
            limit: 返回数量上限
            offset: 偏移量

        Returns:
            (履约记录列表，总数)
        """
        query = self.db.query(FulfillmentEntity)

        if status:
            query = query.filter(FulfillmentEntity.status == status)

        if group_buy_id:
            query = query.filter(FulfillmentEntity.group_buy_id == group_buy_id)

        total = query.count()
        fulfillments = query.order_by(FulfillmentEntity.created_at.desc()).offset(offset).limit(limit).all()

        return fulfillments, total

    def get_user_fulfillments(self, user_id: str, limit: int = 100,
                             offset: int = 0) -> Tuple[List[FulfillmentEntity], int]:
        """
        获取用户的履约记录列表

        Args:
            user_id: 用户 ID
            limit: 返回数量上限
            offset: 偏移量

        Returns:
            (履约记录列表，总数)
        """
        # 通过订单关联用户
        query = self.db.query(FulfillmentEntity).join(
            OrderEntity, FulfillmentEntity.order_id == OrderEntity.id
        ).filter(OrderEntity.user_id == user_id)

        total = query.count()
        fulfillments = query.order_by(FulfillmentEntity.created_at.desc()).offset(offset).limit(limit).all()

        return fulfillments, total

    def get_organizer_fulfillments(self, organizer_id: str, status: str = None,
                                   limit: int = 100, offset: int = 0) -> Tuple[List[FulfillmentEntity], int]:
        """
        获取团长的履约记录列表

        Args:
            organizer_id: 团长 ID
            status: 状态过滤
            limit: 返回数量上限
            offset: 偏移量

        Returns:
            (履约记录列表，总数)
        """
        # 通过团购关联团长
        query = self.db.query(FulfillmentEntity).join(
            GroupBuyEntity, FulfillmentEntity.group_buy_id == GroupBuyEntity.id
        ).filter(GroupBuyEntity.organizer_id == organizer_id)

        if status:
            query = query.filter(FulfillmentEntity.status == status)

        total = query.count()
        fulfillments = query.order_by(FulfillmentEntity.created_at.desc()).offset(offset).limit(limit).all()

        return fulfillments, total

    def cancel_fulfillment(self, fulfillment_id: str, reason: str) -> Tuple[Optional[FulfillmentEntity], bool]:
        """
        取消履约记录

        Args:
            fulfillment_id: 履约记录 ID
            reason: 取消原因

        Returns:
            (履约记录实体，是否成功)
        """
        return self.update_status(fulfillment_id, FulfillmentStatus.CANCELLED, reason)

    def get_fulfillment_stats(self, group_buy_id: str = None) -> dict:
        """
        获取履约统计

        Args:
            group_buy_id: 团购 ID

        Returns:
            统计字典
        """
        query = self.db.query(FulfillmentEntity)

        if group_buy_id:
            query = query.filter(FulfillmentEntity.group_buy_id == group_buy_id)

        stats = {
            "total": query.count(),
            "pending": query.filter(FulfillmentEntity.status == "pending").count(),
            "shipping": query.filter(FulfillmentEntity.status == "shipping").count(),
            "delivered": query.filter(FulfillmentEntity.status == "delivered").count(),
            "completed": query.filter(FulfillmentEntity.status == "completed").count(),
            "cancelled": query.filter(FulfillmentEntity.status == "cancelled").count()
        }

        return stats
