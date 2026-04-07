"""
库存预警工具 - 监控库存水平并生成补货建议

实时监控商品库存，当库存低于阈值时发出预警，并生成智能补货建议。
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from tools.base import BaseTool, ToolMetadata, ToolResponse


class StockAlertTool(BaseTool):
    """库存预警工具 - 监控和补货建议"""

    def __init__(self, db_session: Optional[Session] = None):
        super().__init__()
        self.db = db_session
        # 默认预警阈值
        self.default_alert_threshold = 10
        # 紧急预警阈值
        self.critical_threshold = 5

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="stock_alert",
            description="监控商品库存水平，生成预警和补货建议",
            version="1.0.0",
            tags=["inventory", "alert", "stock", "replenishment"],
            author="ai-community-buying"
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "product_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要检查的商品 ID 列表，为空则检查所有商品"
                },
                "alert_threshold": {
                    "type": "integer",
                    "description": "预警阈值（库存低于此值触发预警）",
                    "default": 10,
                    "minimum": 1
                },
                "include_sold_out": {
                    "type": "boolean",
                    "description": "是否包含已售罄的商品",
                    "default": True
                },
                "community_id": {
                    "type": "string",
                    "description": "社区 ID（用于个性化补货建议）",
                    "default": "default"
                }
            },
            "required": []
        }

    def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResponse:
        """执行库存预警检查"""
        request_id = context.get("request_id") if context else None

        product_ids = params.get("product_ids", [])
        alert_threshold = params.get("alert_threshold", self.default_alert_threshold)
        include_sold_out = params.get("include_sold_out", True)
        community_id = params.get("community_id", "default")

        # 如果没有数据库连接，返回模拟数据
        if self.db is None:
            return self._get_mock_alerts(
                product_ids=product_ids,
                alert_threshold=alert_threshold,
                include_sold_out=include_sold_out,
                community_id=community_id,
                request_id=request_id
            )

        # 从数据库获取库存预警
        return self._get_db_alerts(
            product_ids=product_ids,
            alert_threshold=alert_threshold,
            include_sold_out=include_sold_out,
            community_id=community_id,
            request_id=request_id
        )

    def _get_mock_alerts(
        self,
        product_ids: List[str],
        alert_threshold: int,
        include_sold_out: bool,
        community_id: str,
        request_id: Optional[str]
    ) -> ToolResponse:
        """生成模拟库存预警数据"""
        # 模拟商品库存数据
        mock_products = [
            {"id": "p1", "name": "新鲜鸡蛋", "stock": 5, "locked_stock": 2, "sold_stock": 50, "status": "active"},
            {"id": "p2", "name": "有机牛奶", "stock": 3, "locked_stock": 1, "sold_stock": 30, "status": "active"},
            {"id": "p3", "name": "进口水果", "stock": 0, "locked_stock": 0, "sold_stock": 100, "status": "sold_out"},
            {"id": "p4", "name": "精选肉类", "stock": 15, "locked_stock": 3, "sold_stock": 20, "status": "active"},
            {"id": "p5", "name": "新鲜蔬菜", "stock": 8, "locked_stock": 2, "sold_stock": 40, "status": "active"},
        ]

        # 过滤商品
        if product_ids:
            mock_products = [p for p in mock_products if p["id"] in product_ids]

        # 过滤已售罄商品
        if not include_sold_out:
            mock_products = [p for p in mock_products if p["status"] != "sold_out"]

        alerts = []
        for product in mock_products:
            available_stock = product["stock"] - product["locked_stock"]

            # 判断预警级别
            alert_level = "normal"
            if available_stock <= 0 or product["status"] == "sold_out":
                alert_level = "critical"
            elif available_stock <= self.critical_threshold:
                alert_level = "critical"
            elif available_stock <= alert_threshold:
                alert_level = "warning"

            # 只返回需要预警的商品
            if alert_level != "normal":
                alert = {
                    "product_id": product["id"],
                    "product_name": product["name"],
                    "current_stock": product["stock"],
                    "locked_stock": product["locked_stock"],
                    "available_stock": available_stock,
                    "sold_stock": product["sold_stock"],
                    "alert_level": alert_level,
                    "status": product["status"]
                }

                # 生成补货建议
                alert["replenishment_suggestion"] = self._generate_replenishment_suggestion(
                    product=product,
                    alert_level=alert_level,
                    community_id=community_id
                )

                alerts.append(alert)

        # 按预警级别和可用库存排序
        level_priority = {"critical": 0, "warning": 1}
        alerts.sort(key=lambda x: (level_priority.get(x["alert_level"], 2), x["available_stock"]))

        summary = self._generate_summary(alerts, mock_products)

        return ToolResponse.ok(
            data={
                "community_id": community_id,
                "check_time": datetime.now().isoformat(),
                "summary": summary,
                "alerts": alerts,
                "total_alerts": len(alerts),
                "critical_count": len([a for a in alerts if a["alert_level"] == "critical"]),
                "warning_count": len([a for a in alerts if a["alert_level"] == "warning"])
            },
            request_id=request_id
        )

    def _get_db_alerts(
        self,
        product_ids: List[str],
        alert_threshold: int,
        include_sold_out: bool,
        community_id: str,
        request_id: Optional[str]
    ) -> ToolResponse:
        """从数据库获取库存预警"""
        from models.entities import ProductEntity
        from models.product import ProductStatus

        # 构建查询
        query = self.db.query(ProductEntity)

        if product_ids:
            query = query.filter(ProductEntity.id.in_(product_ids))

        if not include_sold_out:
            query = query.filter(ProductEntity.status != ProductStatus.SOLD_OUT)

        products = query.all()

        alerts = []
        for product in products:
            available_stock = product.stock - product.locked_stock

            # 判断预警级别
            alert_level = "normal"
            if available_stock <= 0 or product.status == ProductStatus.SOLD_OUT:
                alert_level = "critical"
            elif available_stock <= self.critical_threshold:
                alert_level = "critical"
            elif available_stock <= alert_threshold:
                alert_level = "warning"

            # 只返回需要预警的商品
            if alert_level != "normal":
                alert = {
                    "product_id": product.id,
                    "product_name": product.name,
                    "current_stock": product.stock,
                    "locked_stock": product.locked_stock,
                    "available_stock": available_stock,
                    "sold_stock": product.sold_stock,
                    "alert_level": alert_level,
                    "status": product.status.value
                }

                # 生成补货建议
                alert["replenishment_suggestion"] = self._generate_replenishment_suggestion(
                    product={
                        "name": product.name,
                        "stock": product.stock,
                        "sold_stock": product.sold_stock,
                        "price": product.price
                    },
                    alert_level=alert_level,
                    community_id=community_id
                )

                alerts.append(alert)

        # 排序
        level_priority = {"critical": 0, "warning": 1}
        alerts.sort(key=lambda x: (level_priority.get(x["alert_level"], 2), x["available_stock"]))

        summary = self._generate_summary(alerts, products)

        return ToolResponse.ok(
            data={
                "community_id": community_id,
                "check_time": datetime.now().isoformat(),
                "summary": summary,
                "alerts": alerts,
                "total_alerts": len(alerts),
                "critical_count": len([a for a in alerts if a["alert_level"] == "critical"]),
                "warning_count": len([a for a in alerts if a["alert_level"] == "warning"])
            },
            request_id=request_id
        )

    def _generate_replenishment_suggestion(
        self,
        product: Dict,
        alert_level: str,
        community_id: str
    ) -> Dict[str, Any]:
        """生成补货建议"""
        suggestion = {
            "priority": "high" if alert_level == "critical" else "medium",
            "suggested_quantity": 0,
            "reason": "",
            "actions": []
        }

        sold_stock = product.get("sold_stock", 0)
        current_stock = product.get("stock", 0)

        # 基于销售速度计算建议补货量
        if sold_stock > 50:
            # 热销商品，建议大量补货
            suggestion["suggested_quantity"] = max(50, sold_stock)
            suggestion["reason"] = "该商品销量良好，建议大量补货"
            suggestion["actions"].append("优先安排补货")
            suggestion["actions"].append("考虑增加安全库存")
        elif sold_stock > 20:
            # 正常销售，建议适量补货
            suggestion["suggested_quantity"] = max(30, sold_stock)
            suggestion["reason"] = "该商品销售稳定，建议适量补货"
            suggestion["actions"].append("按常规流程补货")
        else:
            # 销量较低，建议少量补货
            suggestion["suggested_quantity"] = max(20, sold_stock) if sold_stock > 0 else 20
            suggestion["reason"] = "该商品销量较低，建议少量补货或观察"
            suggestion["actions"].append("评估商品受欢迎程度")
            suggestion["actions"].append("考虑调整选品或定价")

        # 根据预警级别调整建议
        if alert_level == "critical":
            suggestion["priority"] = "urgent"
            suggestion["actions"].insert(0, "立即补货")
            if current_stock == 0:
                suggestion["actions"].append("考虑暂时下架商品")

        return suggestion

    def _generate_summary(self, alerts: List[Dict], all_products: List) -> Dict[str, Any]:
        """生成库存摘要"""
        total_products = len(all_products)
        alert_count = len(alerts)
        critical_count = len([a for a in alerts if a["alert_level"] == "critical"])
        warning_count = len([a for a in alerts if a["alert_level"] == "warning"])

        health_score = 100 - (critical_count * 20 + warning_count * 5)
        health_score = max(0, min(100, health_score))

        if health_score >= 80:
            health_status = "healthy"
            health_description = "库存状况良好"
        elif health_score >= 60:
            health_status = "warning"
            health_description = "部分商品需要补货"
        elif health_score >= 40:
            health_status = "concerning"
            health_description = "库存状况需关注"
        else:
            health_status = "critical"
            health_description = "库存状况严峻，需立即处理"

        return {
            "total_products": total_products,
            "normal_count": total_products - alert_count,
            "alert_count": alert_count,
            "critical_count": critical_count,
            "warning_count": warning_count,
            "health_score": health_score,
            "health_status": health_status,
            "health_description": health_description
        }
