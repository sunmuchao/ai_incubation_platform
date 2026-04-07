"""
动态定价工具 - 基于成团概率的价格优化

根据当前参与人数、目标人数、历史成团率等因素，计算最优价格。
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import math

from tools.base import BaseTool, ToolMetadata, ToolResponse


class DynamicPricingTool(BaseTool):
    """动态定价工具 - 基于成团概率的价格优化"""

    def __init__(self, db_session: Optional[Session] = None):
        super().__init__()
        self.db = db_session

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="dynamic_pricing",
            description="基于成团概率和市场需求计算最优价格",
            version="1.0.0",
            tags=["pricing", "optimization", "groupbuy"],
            author="ai-community-buying"
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "商品 ID"
                },
                "current_participants": {
                    "type": "integer",
                    "description": "当前参与人数",
                    "minimum": 0
                },
                "target_size": {
                    "type": "integer",
                    "description": "目标成团人数",
                    "minimum": 1
                },
                "base_price": {
                    "type": "number",
                    "description": "商品基础价格",
                    "minimum": 0
                },
                "deadline_hours": {
                    "type": "number",
                    "description": "距离截止的小时数",
                    "minimum": 0
                },
                "historical_success_rate": {
                    "type": "number",
                    "description": "历史成团率 (0-1)",
                    "minimum": 0,
                    "maximum": 1,
                    "default": 0.7
                }
            },
            "required": ["product_id", "current_participants", "target_size", "base_price"]
        }

    def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolResponse:
        """执行动态价格计算"""
        request_id = context.get("request_id") if context else None

        product_id = params.get("product_id")
        current_participants = params.get("current_participants", 1)
        target_size = params.get("target_size", 2)
        base_price = params.get("base_price")
        deadline_hours = params.get("deadline_hours", 24)
        historical_success_rate = params.get("historical_success_rate", 0.7)

        # 获取商品信息（如果有数据库连接）
        product_info = None
        if self.db:
            product_info = self._get_product_info(product_id)
            if not product_info:
                return ToolResponse.fail(
                    error=f"商品 {product_id} 不存在",
                    request_id=request_id
                )
            # 如果参数未提供，使用数据库中的值
            if base_price is None:
                base_price = product_info["price"]

        # 计算成团概率
        success_probability = self._calculate_success_probability(
            current_participants=current_participants,
            target_size=target_size,
            deadline_hours=deadline_hours,
            historical_success_rate=historical_success_rate
        )

        # 计算动态价格
        dynamic_price = self._calculate_dynamic_price(
            base_price=base_price,
            success_probability=success_probability,
            progress_ratio=current_participants / target_size if target_size > 0 else 0,
            time_pressure=self._calculate_time_pressure(deadline_hours)
        )

        # 计算折扣率
        discount_rate = round(dynamic_price / base_price, 3) if base_price > 0 else 1.0

        # 生成定价建议
        pricing_advice = self._generate_pricing_advice(
            success_probability=success_probability,
            discount_rate=discount_rate,
            progress_ratio=current_participants / target_size if target_size > 0 else 0
        )

        return ToolResponse.ok(
            data={
                "product_id": product_id,
                "base_price": base_price,
                "dynamic_price": round(dynamic_price, 2),
                "discount_rate": discount_rate,
                "success_probability": round(success_probability, 3),
                "current_participants": current_participants,
                "target_size": target_size,
                "progress_ratio": round(current_participants / target_size, 3) if target_size > 0 else 0,
                "pricing_advice": pricing_advice
            },
            request_id=request_id
        )

    def _get_product_info(self, product_id: str) -> Optional[Dict]:
        """从数据库获取商品信息"""
        from models.entities import ProductEntity

        product = self.db.query(ProductEntity).filter(ProductEntity.id == product_id).first()
        if not product:
            return None

        return {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "stock": product.stock,
            "min_group_size": product.min_group_size,
            "max_group_size": product.max_group_size
        }

    def _calculate_success_probability(
        self,
        current_participants: int,
        target_size: int,
        deadline_hours: float,
        historical_success_rate: float
    ) -> float:
        """
        计算成团概率

        考虑因素:
        1. 当前进度 (current_participants / target_size)
        2. 时间压力 (剩余时间)
        3. 历史成团率
        """
        # 进度因子 - 使用 S 型曲线，进度越高概率增长越快
        progress_ratio = current_participants / target_size if target_size > 0 else 0
        progress_factor = 1 / (1 + math.exp(-10 * (progress_ratio - 0.5)))

        # 时间因子 - 剩余时间越少，如果需要更多人则概率降低
        time_factor = min(1.0, deadline_hours / 24)  # 24 小时为基准

        # 综合计算
        base_probability = historical_success_rate
        progress_weight = 0.5  # 进度权重 50%
        time_weight = 0.2      # 时间权重 20%
        history_weight = 0.3   # 历史权重 30%

        probability = (
            progress_factor * progress_weight +
            time_factor * time_weight +
            base_probability * history_weight
        )

        # 确保概率在 0-1 之间
        return max(0.0, min(1.0, probability))

    def _calculate_time_pressure(self, deadline_hours: float) -> float:
        """计算时间压力 (0-1，越接近截止时间压力越大)"""
        if deadline_hours <= 0:
            return 1.0
        if deadline_hours <= 1:
            return 0.9
        if deadline_hours <= 6:
            return 0.7
        if deadline_hours <= 12:
            return 0.5
        if deadline_hours <= 24:
            return 0.3
        return 0.1

    def _calculate_dynamic_price(
        self,
        base_price: float,
        success_probability: float,
        progress_ratio: float,
        time_pressure: float
    ) -> float:
        """
        计算动态价格

        策略:
        1. 成团概率高时，可以维持原价或小幅降价吸引更多用户
        2. 成团概率低时，需要更大折扣刺激参团
        3. 时间压力大时，增加折扣力度
        """
        # 基础折扣 - 基于成团概率
        if success_probability >= 0.8:
            # 高概率，小幅优惠
            prob_discount = 0.95
        elif success_probability >= 0.6:
            # 中等概率，适度优惠
            prob_discount = 0.90
        elif success_probability >= 0.4:
            # 中等偏低，较大优惠
            prob_discount = 0.85
        else:
            # 低概率，大幅优惠
            prob_discount = 0.80

        # 时间压力折扣
        time_discount = 1.0 - (time_pressure * 0.1)  # 最大 10% 额外折扣

        # 进度折扣 - 接近成团时额外激励
        if progress_ratio >= 0.8:
            progress_bonus = 0.98  # 只差一点时再降 2%
        else:
            progress_bonus = 1.0

        # 综合计算
        dynamic_price = base_price * prob_discount * time_discount * progress_bonus

        # 确保价格不低于成本价（假设成本价为 base_price 的 50%）
        min_price = base_price * 0.5
        return max(min_price, dynamic_price)

    def _generate_pricing_advice(
        self,
        success_probability: float,
        discount_rate: float,
        progress_ratio: float
    ) -> Dict[str, Any]:
        """生成定价建议"""
        advice = {
            "action": "hold",  # hold, reduce, aggressive
            "reason": "",
            "suggested_actions": []
        }

        if success_probability >= 0.8:
            advice["action"] = "hold"
            advice["reason"] = "成团概率很高，建议维持当前价格策略"
            if progress_ratio >= 0.9:
                advice["suggested_actions"].append("即将成团，可考虑推送通知加速最后阶段")
        elif success_probability >= 0.5:
            advice["action"] = "moderate"
            advice["reason"] = "成团概率中等，可适度调整价格刺激参团"
            advice["suggested_actions"].append("可考虑设置 5-10% 的限时优惠")
            advice["suggested_actions"].append("推送给关注该商品的用户")
        else:
            advice["action"] = "aggressive"
            advice["reason"] = "成团概率较低，建议采取积极的价格策略"
            advice["suggested_actions"].append("建议设置 15-20% 的折扣")
            advice["suggested_actions"].append("考虑延长团购时间")
            advice["suggested_actions"].append("定向推送给高活用户")

        # 根据进度补充建议
        if progress_ratio < 0.3:
            advice["suggested_actions"].append("当前进度较慢，考虑增加曝光渠道")

        return advice
