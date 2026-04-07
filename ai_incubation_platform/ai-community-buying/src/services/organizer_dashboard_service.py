"""
团长管理后台服务
负责团长仪表盘数据、经营分析、会员管理
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional, Tuple, Dict
from datetime import datetime, timedelta
import json
import logging

from models.entities import (
    OrganizerDashboardEntity, OrganizerProfileEntity, OrderEntity,
    GroupBuyEntity, CommissionRecordEntity, GroupMemberEntity
)
from models.product import OrderStatus, GroupBuyStatus
from core.logging_config import get_logger

logger = get_logger("services.organizer_dashboard")


class OrganizerDashboardService:
    """团长管理后台服务"""

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

    def get_dashboard_stats(self, user_id: str) -> Dict:
        """
        获取团长仪表盘统计数据

        Args:
            user_id: 团长用户 ID

        Returns:
            统计数据字典
        """
        try:
            # 获取今天开始的日期
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            # 统计订单数据（通过团购关联团长）
            order_query = self.db.query(OrderEntity).join(
                GroupBuyEntity, OrderEntity.group_buy_id == GroupBuyEntity.id
            ).filter(GroupBuyEntity.organizer_id == user_id)

            total_orders = order_query.count()
            today_orders = order_query.filter(OrderEntity.created_at >= today_start).count()

            # 销售额统计（只计算已完成订单）
            total_sales_result = order_query.filter(
                OrderEntity.status == OrderStatus.COMPLETED
            ).with_entities(func.sum(OrderEntity.total_amount)).scalar() or 0.0

            today_sales_result = order_query.filter(
                OrderEntity.status == OrderStatus.COMPLETED,
                OrderEntity.created_at >= today_start
            ).with_entities(func.sum(OrderEntity.total_amount)).scalar() or 0.0

            # 待处理订单
            pending_orders = order_query.filter(
                OrderEntity.status == OrderStatus.PENDING
            ).count()

            # 待配送订单
            pending_delivery = order_query.filter(
                OrderEntity.status == OrderStatus.PAID
            ).count()

            # 已完成订单
            completed_orders = order_query.filter(
                OrderEntity.status == OrderStatus.COMPLETED
            ).count()

            # 退款订单
            refund_orders = order_query.filter(
                or_(
                    OrderEntity.status == OrderStatus.REFUNDED,
                    OrderEntity.status == OrderStatus.CANCELLED
                )
            ).count()

            # 客户数统计（去重）
            total_customers = order_query.with_entities(
                func.count(func.distinct(OrderEntity.user_id))
            ).scalar() or 0

            # 佣金统计
            commission_result = self.db.query(CommissionRecordEntity).filter(
                CommissionRecordEntity.organizer_id == user_id,
                CommissionRecordEntity.status == "settled"
            ).with_entities(func.sum(CommissionRecordEntity.commission_amount)).scalar() or 0.0

            # 团长档案
            profile = self.db.query(OrganizerProfileEntity).filter(
                OrganizerProfileEntity.user_id == user_id
            ).first()

            customer_satisfaction = profile.rating if profile else 5.0

            stats = {
                "user_id": user_id,
                "total_sales": total_sales_result,
                "total_orders": total_orders,
                "total_customers": total_customers,
                "total_commission": commission_result,
                "today_sales": today_sales_result,
                "today_orders": today_orders,
                "pending_orders": pending_orders,
                "pending_delivery": pending_delivery,
                "completed_orders": completed_orders,
                "refund_orders": refund_orders,
                "customer_satisfaction": customer_satisfaction,
                "data_date": datetime.now()
            }

            self._log("info", "获取仪表盘统计成功", {
                "user_id": user_id,
                "total_sales": total_sales_result,
                "total_orders": total_orders
            })

            return stats

        except Exception as e:
            self._log("error", f"获取仪表盘统计失败：{str(e)}", {"user_id": user_id})
            raise

    def save_dashboard_snapshot(self, user_id: str) -> Optional[OrganizerDashboardEntity]:
        """
        保存仪表盘数据快照

        Args:
            user_id: 团长用户 ID

        Returns:
            保存的快照实体
        """
        try:
            stats = self.get_dashboard_stats(user_id)

            # 检查是否已存在今日快照
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            existing = self.db.query(OrganizerDashboardEntity).filter(
                OrganizerDashboardEntity.user_id == user_id,
                OrganizerDashboardEntity.data_date >= today_start
            ).first()

            if existing:
                # 更新现有快照
                existing.total_sales = stats["total_sales"]
                existing.total_orders = stats["total_orders"]
                existing.total_customers = stats["total_customers"]
                existing.total_commission = stats["total_commission"]
                existing.today_sales = stats["today_sales"]
                existing.today_orders = stats["today_orders"]
                existing.pending_orders = stats["pending_orders"]
                existing.pending_delivery = stats["pending_delivery"]
                existing.completed_orders = stats["completed_orders"]
                existing.refund_orders = stats["refund_orders"]
                existing.customer_satisfaction = stats["customer_satisfaction"]
                existing.updated_at = datetime.now()
                snapshot = existing
            else:
                # 创建新快照
                snapshot = OrganizerDashboardEntity(
                    user_id=user_id,
                    total_sales=stats["total_sales"],
                    total_orders=stats["total_orders"],
                    total_customers=stats["total_customers"],
                    total_commission=stats["total_commission"],
                    today_sales=stats["today_sales"],
                    today_orders=stats["today_orders"],
                    pending_orders=stats["pending_orders"],
                    pending_delivery=stats["pending_delivery"],
                    completed_orders=stats["completed_orders"],
                    refund_orders=stats["refund_orders"],
                    customer_satisfaction=stats["customer_satisfaction"],
                    data_date=datetime.now()
                )
                self.db.add(snapshot)

            self.db.commit()
            self.db.refresh(snapshot)

            self._log("info", "保存仪表盘快照成功", {
                "user_id": user_id,
                "snapshot_id": snapshot.id
            })

            return snapshot

        except Exception as e:
            self.db.rollback()
            self._log("error", f"保存仪表盘快照失败：{str(e)}", {"user_id": user_id})
            raise

    def get_dashboard_history(self, user_id: str, days: int = 30,
                             limit: int = 100) -> List[OrganizerDashboardEntity]:
        """
        获取仪表盘历史数据

        Args:
            user_id: 团长用户 ID
            days: 天数
            limit: 返回数量上限

        Returns:
            历史快照列表
        """
        start_date = datetime.now() - timedelta(days=days)

        snapshots = self.db.query(OrganizerDashboardEntity).filter(
            OrganizerDashboardEntity.user_id == user_id,
            OrganizerDashboardEntity.data_date >= start_date
        ).order_by(OrganizerDashboardEntity.data_date.desc()).limit(limit).all()

        return snapshots

    def get_group_list(self, organizer_id: str, status: str = None,
                      limit: int = 20, offset: int = 0) -> Tuple[List[GroupBuyEntity], int]:
        """
        获取团长的团购列表

        Args:
            organizer_id: 团长 ID
            status: 状态过滤
            limit: 返回数量上限
            offset: 偏移量

        Returns:
            (团购列表，总数)
        """
        query = self.db.query(GroupBuyEntity).filter(
            GroupBuyEntity.organizer_id == organizer_id
        )

        if status:
            query = query.filter(GroupBuyEntity.status == status)

        total = query.count()
        groups = query.order_by(GroupBuyEntity.created_at.desc()).offset(offset).limit(limit).all()

        return groups, total

    def get_member_list(self, group_buy_id: str, limit: int = 100,
                       offset: int = 0) -> Tuple[List[GroupMemberEntity], int]:
        """
        获取团购成员列表

        Args:
            group_buy_id: 团购 ID
            limit: 返回数量上限
            offset: 偏移量

        Returns:
            (成员列表，总数)
        """
        query = self.db.query(GroupMemberEntity).filter(
            GroupMemberEntity.group_buy_id == group_buy_id
        )

        total = query.count()
        members = query.order_by(GroupMemberEntity.join_time).offset(offset).limit(limit).all()

        return members, total

    def get_customer_list(self, organizer_id: str, limit: int = 100,
                         offset: int = 0) -> Tuple[List[Dict], int]:
        """
        获取客户列表（去重后的用户）

        Args:
            organizer_id: 团长 ID
            limit: 返回数量上限
            offset: 偏移量

        Returns:
            (客户列表，总数)
        """
        # 获取所有订单关联的用户 ID 及统计信息
        subquery = self.db.query(
            OrderEntity.user_id,
            func.count(OrderEntity.id).label("order_count"),
            func.sum(OrderEntity.total_amount).label("total_spent"),
            func.max(OrderEntity.created_at).label("last_order_at")
        ).join(
            GroupBuyEntity, OrderEntity.group_buy_id == GroupBuyEntity.id
        ).filter(
            GroupBuyEntity.organizer_id == organizer_id
        ).group_by(OrderEntity.user_id).subquery()

        query = self.db.query(subquery)

        total = query.count()
        results = query.offset(offset).limit(limit).all()

        customers = [
            {
                "user_id": r.user_id,
                "order_count": r.order_count,
                "total_spent": r.total_spent,
                "last_order_at": r.last_order_at
            }
            for r in results
        ]

        return customers, total

    def get_sales_trend(self, organizer_id: str, days: int = 7) -> List[Dict]:
        """
        获取销售趋势数据

        Args:
            organizer_id: 团长 ID
            days: 天数

        Returns:
            每日销售数据列表
        """
        today = datetime.now().date()
        trend_data = []

        for i in range(days):
            date = today - timedelta(days=i)
            start_of_day = datetime.combine(date, datetime.min.time())
            end_of_day = datetime.combine(date, datetime.max.time())

            # 查询当日订单数据
            order_query = self.db.query(OrderEntity).join(
                GroupBuyEntity, OrderEntity.group_buy_id == GroupBuyEntity.id
            ).filter(
                GroupBuyEntity.organizer_id == organizer_id,
                OrderEntity.created_at >= start_of_day,
                OrderEntity.created_at <= end_of_day
            )

            order_count = order_query.count()
            sales_amount = order_query.filter(
                OrderEntity.status == OrderStatus.COMPLETED
            ).with_entities(func.sum(OrderEntity.total_amount)).scalar() or 0.0

            trend_data.append({
                "date": date.isoformat(),
                "order_count": order_count,
                "sales_amount": sales_amount
            })

        return sorted(trend_data, key=lambda x: x["date"])

    def get_top_products(self, organizer_id: str, limit: int = 10) -> List[Dict]:
        """
        获取热销商品 TOP 榜

        Args:
            organizer_id: 团长 ID
            limit: 返回数量上限

        Returns:
            商品销售排行榜
        """
        from models.entities import ProductEntity

        results = self.db.query(
            OrderEntity.product_id,
            func.sum(OrderEntity.quantity).label("total_quantity"),
            func.sum(OrderEntity.total_amount).label("total_amount"),
            func.count(OrderEntity.id).label("order_count")
        ).join(
            GroupBuyEntity, OrderEntity.group_buy_id == GroupBuyEntity.id
        ).filter(
            GroupBuyEntity.organizer_id == organizer_id,
            OrderEntity.status == OrderStatus.COMPLETED
        ).group_by(OrderEntity.product_id).order_by(
            func.sum(OrderEntity.quantity).desc()
        ).limit(limit).all()

        # 获取商品信息
        product_ids = [r.product_id for r in results]
        products = self.db.query(ProductEntity).filter(
            ProductEntity.id.in_(product_ids)
        ).all()
        product_map = {p.id: p for p in products}

        top_products = []
        for r in results:
            product = product_map.get(r.product_id)
            top_products.append({
                "product_id": r.product_id,
                "product_name": product.name if product else "未知商品",
                "total_quantity": r.total_quantity,
                "total_amount": r.total_amount,
                "order_count": r.order_count
            })

        return top_products
