"""
订单管理服务
负责订单的 CRUD 操作和状态流转
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from models.db_models import (
    OrderDB, OrderStatusEnum, AIEmployeeDB, EmployeeStatusEnum, UsageRecordDB, RiskLevelEnum
)
from services.base_service import BaseService
from config.settings import settings


class OrderService(BaseService):
    """订单服务"""

    def create_order(
        self,
        tenant_id: str,
        employee_id: str,
        hirer_id: str,
        owner_id: str,
        duration_hours: int,
        task_description: str
    ) -> Optional[OrderDB]:
        """创建订单"""
        try:
            # 获取员工信息
            employee = self.db.query(AIEmployeeDB).filter(AIEmployeeDB.id == employee_id).first()
            if not employee or employee.status != EmployeeStatusEnum.AVAILABLE:
                self.logger.warning(f"Employee not available: {employee_id}")
                return None

            # 租户隔离校验
            if employee.tenant_id != tenant_id:
                self.logger.warning(f"Cross-tenant order attempt: employee tenant={employee.tenant_id}, order tenant={tenant_id}")
                return None

            # 计算费用
            total_amount = employee.hourly_rate * duration_hours
            platform_fee = total_amount * settings.platform_fee_rate
            owner_earning = total_amount - platform_fee

            order = OrderDB(
                tenant_id=tenant_id,
                employee_id=employee_id,
                hirer_id=hirer_id,
                owner_id=owner_id,
                duration_hours=duration_hours,
                task_description=task_description,
                hourly_rate=employee.hourly_rate,
                total_amount=total_amount,
                platform_fee=platform_fee,
                owner_earning=owner_earning
            )
            self.db.add(order)

            # 创建用量记录
            usage = UsageRecordDB(
                tenant_id=tenant_id,
                user_id=hirer_id,
                resource_type="employee_rental",
                resource_id=employee_id,
                quantity=duration_hours,
                unit="hours",
                unit_price=employee.hourly_rate,
                total_amount=total_amount,
                description=f"租赁 AI 员工：{employee.name}",
                start_time=datetime.now()
            )
            self.db.add(usage)

            self.db.commit()
            self.db.refresh(order)
            self.logger.info(f"Created order: {order.id}")
            return order
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to create order: {str(e)}")
            raise

    def get_order(self, order_id: str) -> Optional[OrderDB]:
        """获取订单"""
        return self.db.query(OrderDB).filter(OrderDB.id == order_id).first()

    def list_orders(
        self,
        tenant_id: Optional[str] = None,
        employee_id: Optional[str] = None,
        hirer_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        status: Optional[OrderStatusEnum] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[OrderDB]:
        """获取订单列表"""
        query = self.db.query(OrderDB)
        if tenant_id:
            query = query.filter(OrderDB.tenant_id == tenant_id)
        if employee_id:
            query = query.filter(OrderDB.employee_id == employee_id)
        if hirer_id:
            query = query.filter(OrderDB.hirer_id == hirer_id)
        if owner_id:
            query = query.filter(OrderDB.owner_id == owner_id)
        if status:
            query = query.filter(OrderDB.status == status)
        return query.offset(offset).limit(limit).all()

    def confirm_order(self, order_id: str) -> bool:
        """确认订单"""
        order = self.get_order(order_id)
        if not order or order.status != OrderStatusEnum.PENDING:
            return False

        try:
            order.status = OrderStatusEnum.CONFIRMED
            order.confirmed_at = datetime.now()
            # 更新员工状态为已雇佣
            employee = self.db.query(AIEmployeeDB).filter(AIEmployeeDB.id == order.employee_id).first()
            if employee:
                employee.status = EmployeeStatusEnum.HIRED
            self.db.commit()
            self.logger.info(f"Confirmed order: {order_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to confirm order: {str(e)}")
            raise

    def start_order(self, order_id: str) -> bool:
        """开始执行订单"""
        order = self.get_order(order_id)
        if not order or order.status != OrderStatusEnum.CONFIRMED:
            return False

        try:
            order.status = OrderStatusEnum.IN_PROGRESS
            order.started_at = datetime.now()
            self.db.commit()
            self.logger.info(f"Started order: {order_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to start order: {str(e)}")
            raise

    def complete_order(
        self,
        order_id: str,
        rating: Optional[float] = None,
        review: Optional[str] = None,
        review_tags: Optional[List[str]] = None
    ) -> bool:
        """完成订单"""
        order = self.get_order(order_id)
        if not order or order.status != OrderStatusEnum.IN_PROGRESS:
            return False

        try:
            order.status = OrderStatusEnum.COMPLETED
            order.completed_at = datetime.now()

            if rating is not None:
                order.rating = rating
            if review:
                order.review = review
            if review_tags:
                order.review_tags = review_tags

            # 执行风险检查
            self._perform_risk_check(order)

            # 更新员工统计数据
            employee = self.db.query(AIEmployeeDB).filter(AIEmployeeDB.id == order.employee_id).first()
            if employee:
                employee.total_jobs += 1
                employee.total_earnings += order.owner_earning
                if rating:
                    # 更新平均评分
                    employee.rating = (employee.rating * employee.review_count + rating) / (employee.review_count + 1)
                    employee.review_count += 1
                # 如果员工未被风控封禁，恢复为可用状态
                if employee.status != EmployeeStatusEnum.OFFLINE:
                    employee.status = EmployeeStatusEnum.AVAILABLE

            self.db.commit()
            self.logger.info(f"Completed order: {order_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to complete order: {str(e)}")
            raise

    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        order = self.get_order(order_id)
        if not order or order.status not in [OrderStatusEnum.PENDING, OrderStatusEnum.CONFIRMED]:
            return False

        try:
            order.status = OrderStatusEnum.CANCELLED
            order.cancelled_at = datetime.now()
            # 恢复员工状态为可用
            employee = self.db.query(AIEmployeeDB).filter(AIEmployeeDB.id == order.employee_id).first()
            if employee:
                employee.status = EmployeeStatusEnum.AVAILABLE
            self.db.commit()
            self.logger.info(f"Cancelled order: {order_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to cancel order: {str(e)}")
            raise

    def _perform_risk_check(self, order: OrderDB) -> None:
        """执行订单风险检查"""
        risk_factors = []

        # 长订单检测
        if order.duration_hours > settings.max_order_duration_hours:
            risk_factors.append("long_duration_order")

        # 敏感内容检测
        sensitive_keywords = ["敏感", "违规", "违法", "欺诈"]
        if any(keyword in order.task_description for keyword in sensitive_keywords):
            risk_factors.append("sensitive_content")

        # 异常高费率检测
        if order.hourly_rate > settings.max_hourly_rate:
            risk_factors.append("abnormal_high_rate")

        order.risk_factors = risk_factors
        order.risk_check_passed = len(risk_factors) == 0

        # 更新员工风险评分
        employee = self.db.query(AIEmployeeDB).filter(AIEmployeeDB.id == order.employee_id).first()
        if employee:
            risk_score_increase = len(risk_factors) * 10
            employee.risk_score = min(100, employee.risk_score + risk_score_increase)
            employee.violation_count += len(risk_factors)

            # 更新风险等级
            if employee.risk_score >= settings.risk_score_block_threshold:
                employee.risk_level = RiskLevelEnum.BLOCKED
                employee.status = EmployeeStatusEnum.OFFLINE
            elif employee.risk_score >= settings.risk_score_high_threshold:
                employee.risk_level = RiskLevelEnum.HIGH
            elif employee.risk_score >= settings.risk_score_medium_threshold:
                employee.risk_level = RiskLevelEnum.MEDIUM
            else:
                employee.risk_level = RiskLevelEnum.LOW

            employee.last_risk_check = datetime.now()
