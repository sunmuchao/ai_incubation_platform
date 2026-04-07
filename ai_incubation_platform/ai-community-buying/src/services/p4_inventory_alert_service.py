"""
P4 供应链服务 - 库存预警服务
负责库存监控、预警生成、预警处理
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional, Tuple, Dict
from datetime import datetime, timedelta
import logging

from models.p4_entities import InventoryAlertEntity, InventoryAlertActionEntity
from models.entities import ProductEntity
from models.p4_models import AlertLevel, AlertType, AlertStatus, ActionType, ActionStatus
from core.logging_config import get_logger

logger = get_logger("services.p4.inventory_alert")


class InventoryAlertService:
    """库存预警服务"""

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

    def check_inventory_and_create_alert(self, product_id: str, community_id: str,
                                          low_stock_threshold: int = 10,
                                          critical_threshold: int = 5) -> Tuple[Optional[InventoryAlertEntity], bool]:
        """
        检查库存并创建预警

        Args:
            product_id: 商品 ID
            community_id: 社区 ID
            low_stock_threshold: 低库存阈值
            critical_threshold: 严重缺货阈值

        Returns:
            (预警实体，是否成功)
        """
        try:
            # 获取商品库存
            product = self.db.query(ProductEntity).filter(ProductEntity.id == product_id).first()
            if not product:
                self._log("error", "商品不存在", {"product_id": product_id})
                return None, False

            current_stock = product.stock

            # 判断预警等级
            if current_stock <= 0:
                alert_level = AlertLevel.CRITICAL
                alert_type = AlertType.STOCK_OUT
                message = f"商品 {product.name} 已缺货，当前库存：0"
            elif current_stock <= critical_threshold:
                alert_level = AlertLevel.CRITICAL
                alert_type = AlertType.STOCK_LOW
                message = f"商品 {product.name} 严重缺货，当前库存：{current_stock}"
            elif current_stock <= low_stock_threshold:
                alert_level = AlertLevel.LOW
                alert_type = AlertType.STOCK_LOW
                message = f"商品 {product.name} 库存不足，当前库存：{current_stock}"
            else:
                # 库存充足，不需要预警
                return None, True

            # 检查是否已存在活跃预警
            existing = self.db.query(InventoryAlertEntity).filter(
                and_(
                    InventoryAlertEntity.product_id == product_id,
                    InventoryAlertEntity.community_id == community_id,
                    InventoryAlertEntity.status == AlertStatus.ACTIVE.value
                )
            ).first()

            if existing:
                self._log("info", "预警已存在", {"product_id": product_id, "alert_id": existing.id})
                return existing, True

            # 创建预警
            alert = InventoryAlertEntity(
                product_id=product_id,
                community_id=community_id,
                current_stock=current_stock,
                threshold=low_stock_threshold if alert_level == AlertLevel.LOW else critical_threshold,
                alert_level=alert_level.value,
                alert_type=alert_type.value,
                message=message,
                status=AlertStatus.ACTIVE.value,
                suggested_quantity=(low_stock_threshold * 2) if current_stock > 0 else low_stock_threshold * 3
            )

            self.db.add(alert)
            self.db.commit()
            self.db.refresh(alert)

            self._log("info", "库存预警创建成功", {
                "alert_id": alert.id,
                "product_id": product_id,
                "alert_level": alert_level.value
            })

            return alert, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"检查库存并创建预警失败：{str(e)}", {"product_id": product_id})
            return None, False

    def get_alert(self, alert_id: str) -> Optional[InventoryAlertEntity]:
        """获取预警详情"""
        return self.db.query(InventoryAlertEntity).filter(
            InventoryAlertEntity.id == alert_id
        ).first()

    def list_alerts(self, community_id: str = None, status: str = None,
                    alert_level: str = None, limit: int = 100) -> List[InventoryAlertEntity]:
        """获取预警列表"""
        query = self.db.query(InventoryAlertEntity)

        if community_id:
            query = query.filter(InventoryAlertEntity.community_id == community_id)
        if status:
            query = query.filter(InventoryAlertEntity.status == status)
        if alert_level:
            query = query.filter(InventoryAlertEntity.alert_level == alert_level)

        return query.order_by(InventoryAlertEntity.created_at.desc()).limit(limit).all()

    def handle_alert(self, alert_id: str, handler_id: str,
                     notes: str = None) -> Tuple[Optional[InventoryAlertEntity], bool]:
        """
        处理预警

        Args:
            alert_id: 预警 ID
            handler_id: 处理人 ID
            notes: 处理备注

        Returns:
            (预警实体，是否成功)
        """
        try:
            alert = self.db.query(InventoryAlertEntity).filter(
                InventoryAlertEntity.id == alert_id
            ).first()

            if not alert:
                self._log("error", "预警不存在", {"alert_id": alert_id})
                return None, False

            alert.status = AlertStatus.HANDLED.value
            alert.handler_id = handler_id
            alert.handled_at = datetime.now()
            alert.handled_notes = notes or ""
            alert.updated_at = datetime.now()

            self.db.commit()
            self.db.refresh(alert)

            self._log("info", "预警处理成功", {"alert_id": alert_id, "handler_id": handler_id})

            return alert, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"处理预警失败：{str(e)}", {"alert_id": alert_id})
            return None, False

    def create_action(self, alert_id: str, action_type: str,
                      action_quantity: int = None, action_cost: float = 0.0,
                      expected_effect_date: datetime = None,
                      notes: str = None) -> Tuple[Optional[InventoryAlertActionEntity], bool]:
        """
        创建预警处理行动

        Args:
            alert_id: 预警 ID
            action_type: 行动类型
            action_quantity: 行动数量
            action_cost: 行动成本
            expected_effect_date: 预期生效日期
            notes: 备注

        Returns:
            (行动实体，是否成功)
        """
        try:
            alert = self.db.query(InventoryAlertEntity).filter(
                InventoryAlertEntity.id == alert_id
            ).first()

            if not alert:
                self._log("error", "预警不存在", {"alert_id": alert_id})
                return None, False

            action = InventoryAlertActionEntity(
                alert_id=alert_id,
                action_type=action_type,
                action_quantity=action_quantity,
                action_cost=action_cost,
                expected_effect_date=expected_effect_date,
                notes=notes
            )

            self.db.add(action)
            self.db.commit()
            self.db.refresh(action)

            self._log("info", "预警行动创建成功", {"alert_id": alert_id, "action_type": action_type})

            return action, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"创建预警行动失败：{str(e)}", {"alert_id": alert_id})
            return None, False

    def execute_action(self, action_id: str, executor_id: str,
                       notes: str = None) -> Tuple[Optional[InventoryAlertActionEntity], bool]:
        """
        执行预警行动

        Args:
            action_id: 行动 ID
            executor_id: 执行人 ID
            notes: 备注

        Returns:
            (行动实体，是否成功)
        """
        try:
            action = self.db.query(InventoryAlertActionEntity).filter(
                InventoryAlertActionEntity.id == action_id
            ).first()

            if not action:
                self._log("error", "行动不存在", {"action_id": action_id})
                return None, False

            action.status = ActionStatus.COMPLETED.value
            action.executor_id = executor_id
            action.executed_at = datetime.now()
            if notes:
                action.notes = notes
            action.updated_at = datetime.now()

            self.db.commit()
            self.db.refresh(action)

            self._log("info", "预警行动执行成功", {"action_id": action_id, "executor_id": executor_id})

            return action, True

        except Exception as e:
            self.db.rollback()
            self._log("error", f"执行预警行动失败：{str(e)}", {"action_id": action_id})
            return None, False

    def get_alert_stats(self, community_id: str = None) -> Dict:
        """
        获取预警统计

        Args:
            community_id: 社区 ID

        Returns:
            统计字典
        """
        query = self.db.query(InventoryAlertEntity)

        if community_id:
            query = query.filter(InventoryAlertEntity.community_id == community_id)

        return {
            "total": query.count(),
            "active": query.filter(InventoryAlertEntity.status == AlertStatus.ACTIVE.value).count(),
            "handled": query.filter(InventoryAlertEntity.status == AlertStatus.HANDLED.value).count(),
            "low_stock": query.filter(InventoryAlertEntity.alert_level == AlertLevel.LOW.value).count(),
            "critical": query.filter(InventoryAlertEntity.alert_level == AlertLevel.CRITICAL.value).count(),
            "stock_out": query.filter(InventoryAlertEntity.alert_type == AlertType.STOCK_OUT.value).count()
        }

    def run_inventory_check(self, low_stock_threshold: int = 10,
                            critical_threshold: int = 5) -> int:
        """
        运行库存检查任务

        Args:
            low_stock_threshold: 低库存阈值
            critical_threshold: 严重缺货阈值

        Returns:
            创建的预警数量
        """
        # 获取所有活跃商品
        products = self.db.query(ProductEntity).filter(
            ProductEntity.status == "active"
        ).all()

        created_count = 0
        for product in products:
            # 为每个商品创建预警（假设社区 ID 为"default"）
            alert, success = self.check_inventory_and_create_alert(
                product_id=product.id,
                community_id="default",
                low_stock_threshold=low_stock_threshold,
                critical_threshold=critical_threshold
            )
            if success and alert:
                created_count += 1

        return created_count
