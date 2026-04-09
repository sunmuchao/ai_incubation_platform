"""
P2: 礼物闭环集成服务

功能包括：
- 电商平台对接（京东/淘宝）
- 礼物推荐 AI 排序
- 佣金追踪
- 订单物流追踪
- 礼物反馈分析
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json
import uuid
import hashlib


# ============= 电商 API 配置 =============

ECOMMERCE_PLATFORMS = {
    "jd": {
        "name": "京东",
        "api_base": "https://api.jd.com",
        "commission_rate_range": (0.05, 0.15),  # 5%-15%
    },
    "taobao": {
        "name": "淘宝",
        "api_base": "https://api.taobao.com",
        "commission_rate_range": (0.03, 0.12),
    },
    "pinduoduo": {
        "name": "拼多多",
        "api_base": "https://api.pinduoduo.com",
        "commission_rate_range": (0.02, 0.10),
    },
}

# 礼物场合分类
GIFT_OCCASIONS = {
    "birthday": "生日",
    "anniversary": "纪念日",
    "valentines": "情人节",
    "christmas": "圣诞节",
    "qixi": "七夕节",
    "mothers_day": "母亲节",
    "fathers_day": "父亲节",
    "apology": "道歉",
    "surprise": "惊喜",
    "just_because": "日常小礼物",
}

# 预算范围
BUDGET_RANGES = {
    "under_100": (0, 100, "100 元以下"),
    "100_to_300": (100, 300, "100-300 元"),
    "300_to_500": (300, 500, "300-500 元"),
    "500_to_1000": (500, 1000, "500-1000 元"),
    "above_1000": (1000, 999999, "1000 元以上"),
}


class GiftIntegrationService:
    """礼物闭环集成服务"""

    def __init__(self, db: Session):
        self.db = db

    # ============= 礼物推荐 =============

    def get_gift_suggestions(
        self,
        occasion: str,
        budget_range: str,
        recipient_preferences: Dict[str, Any],
        sender_user_id: str,
        recipient_user_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        获取礼物推荐

        Args:
            occasion: 场合 (birthday/anniversary/valentines 等)
            budget_range: 预算范围
            recipient_preferences: 接收人喜好
            sender_user_id: 发送人用户 ID
            recipient_user_id: 接收人用户 ID（可选）
            limit: 返回数量

        Returns:
            礼物推荐列表
        """
        # 获取预算范围
        budget = BUDGET_RANGES.get(budget_range, (0, 999999, "不限"))
        min_price, max_price, _ = budget

        # Mock 产品数据（实际应对接电商 API）
        mock_products = self._get_mock_products(occasion, min_price, max_price)

        # AI 排序
        ranked_products = self._ai_rank_products(
            mock_products, recipient_preferences
        )

        # 添加佣金信息
        products_with_commission = [
            self._add_commission_info(p, sender_user_id)
            for p in ranked_products[:limit]
        ]

        return products_with_commission

    def _get_mock_products(
        self, occasion: str, min_price: float, max_price: float
    ) -> List[Dict[str, Any]]:
        """获取 Mock 产品数据（实际应对接电商 API）"""
        # Mock 产品库
        all_products = [
            {
                "id": "jd_001",
                "platform": "jd",
                "name": "施华洛世奇天鹅项链",
                "price": 599,
                "category": "jewelry",
                "tags": ["浪漫", "经典", "女生喜欢"],
                "image_url": "https://example.com/necklace.jpg",
                "commission_rate": 0.08,
            },
            {
                "id": "tb_002",
                "platform": "taobao",
                "name": "YSL 口红礼盒套装",
                "price": 899,
                "category": "beauty",
                "tags": ["美妆", "大牌", "实用"],
                "image_url": "https://example.com/lipstick.jpg",
                "commission_rate": 0.10,
            },
            {
                "id": "jd_003",
                "platform": "jd",
                "name": "富士拍立得相机",
                "price": 799,
                "category": "electronics",
                "tags": ["记录美好", "有趣", "创意"],
                "image_url": "https://example.com/camera.jpg",
                "commission_rate": 0.06,
            },
            {
                "id": "tb_004",
                "platform": "taobao",
                "name": "定制星空投影灯",
                "price": 299,
                "category": "home_decor",
                "tags": ["浪漫", "定制", "氛围"],
                "image_url": "https://example.com/projector.jpg",
                "commission_rate": 0.12,
            },
            {
                "id": "jd_005",
                "platform": "jd",
                "name": "蔻驰女士钱包",
                "price": 1299,
                "category": "fashion",
                "tags": ["轻奢", "实用", "品牌"],
                "image_url": "https://example.com/wallet.jpg",
                "commission_rate": 0.07,
            },
            {
                "id": "tb_006",
                "platform": "taobao",
                "name": "手工巧克力礼盒",
                "price": 199,
                "category": "food",
                "tags": ["甜蜜", "分享", "浪漫"],
                "image_url": "https://example.com/chocolate.jpg",
                "commission_rate": 0.15,
            },
        ]

        # 根据价格筛选
        filtered = [
            p for p in all_products
            if min_price <= p["price"] <= max_price
        ]

        # 根据场合筛选（简化实现）
        if occasion == "birthday":
            # 生日优先推荐珠宝、美妆
            filtered.sort(key=lambda x: x["category"] in ["jewelry", "beauty"], reverse=True)
        elif occasion == "anniversary":
            # 纪念日优先推荐浪漫类
            filtered.sort(key=lambda x: "浪漫" in x["tags"], reverse=True)
        elif occasion == "valentines":
            # 情人节优先推荐珠宝、美妆
            filtered.sort(key=lambda x: x["category"] in ["jewelry", "beauty", "food"], reverse=True)

        return filtered

    def _ai_rank_products(
        self,
        products: List[Dict[str, Any]],
        preferences: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        AI 排序产品

        基于接收人画像进行个性化排序
        """
        # 提取偏好
        favorite_colors = preferences.get("favorite_colors", [])
        favorite_brands = preferences.get("favorite_brands", [])
        hobbies = preferences.get("hobbies", [])
        style = preferences.get("style", "any")

        scored_products = []

        for product in products:
            score = 0.0

            # 类别匹配
            product_category = product.get("category", "")
            if product_category in preferences.get("favorite_categories", []):
                score += 0.3

            # 标签匹配
            product_tags = product.get("tags", [])
            for tag in product_tags:
                if tag in preferences.get("preferred_tags", []):
                    score += 0.1

            # 品牌匹配
            product_name = product.get("name", "").lower()
            for brand in favorite_brands:
                if brand.lower() in product_name:
                    score += 0.2

            # 价格偏好
            price_preference = preferences.get("price_preference", "moderate")
            if price_preference == "luxury" and product["price"] > 500:
                score += 0.1
            elif price_preference == "budget" and product["price"] < 300:
                score += 0.1

            scored_products.append((score, product))

        # 按分数排序
        scored_products.sort(key=lambda x: x[0], reverse=True)

        return [p for _, p in scored_products]

    def _add_commission_info(
        self,
        product: Dict[str, Any],
        sender_user_id: str,
    ) -> Dict[str, Any]:
        """添加佣金信息"""
        platform = product.get("platform", "jd")
        platform_info = ECOMMERCE_PLATFORMS.get(platform, ECOMMERCE_PLATFORMS["jd"])

        commission_rate = product.get("commission_rate", 0.05)
        commission_amount = product["price"] * commission_rate

        # 生成推广链接（Mock）
        affiliate_link = self._generate_affiliate_link(
            product["id"], sender_user_id, platform
        )

        return {
            **product,
            "commission_rate": commission_rate,
            "commission_amount": round(commission_amount, 2),
            "affiliate_link": affiliate_link,
            "platform_name": platform_info["name"],
        }

    def _generate_affiliate_link(
        self,
        product_id: str,
        user_id: str,
        platform: str,
    ) -> str:
        """生成推广链接"""
        # Mock 实现，实际应调用电商平台 API
        affiliate_code = hashlib.md5(f"{product_id}:{user_id}".encode()).hexdigest()[:8]
        return f"https://{platform}.com/item/{product_id}?affiliate={affiliate_code}"

    # ============= 订单管理 =============

    def place_order(
        self,
        product_id: str,
        sender_user_id: str,
        recipient_user_id: str,
        delivery_info: Dict[str, Any],
        gift_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        下单订购

        Args:
            product_id: 产品 ID
            sender_user_id: 发送人用户 ID
            recipient_user_id: 接收人用户 ID
            delivery_info: 配送信息
            gift_message: 礼物留言

        Returns:
            订单信息
        """
        # Mock 下单（实际应调用电商平台 API）
        order_id = f"ORDER_{uuid.uuid4().hex[:12]}"
        tracking_no = f"TRACK_{uuid.uuid4().hex[:16]}"

        # 预计配送时间
        estimated_delivery = datetime.now() + timedelta(days=3)

        return {
            "order_id": order_id,
            "product_id": product_id,
            "sender_user_id": sender_user_id,
            "recipient_user_id": recipient_user_id,
            "tracking_no": tracking_no,
            "status": "confirmed",
            "gift_message": gift_message,
            "delivery_info": delivery_info,
            "estimated_delivery": estimated_delivery.isoformat(),
            "created_at": datetime.now().isoformat(),
        }

    def track_order(self, order_id: str) -> Dict[str, Any]:
        """
        追踪订单物流

        Args:
            order_id: 订单 ID

        Returns:
            物流信息
        """
        # Mock 物流信息（实际应调用物流 API）
        return {
            "order_id": order_id,
            "status": "in_transit",
            "current_location": "上海转运中心",
            "estimated_delivery": (datetime.now() + timedelta(days=2)).isoformat(),
            "tracking_history": [
                {
                    "time": (datetime.now() - timedelta(hours=12)).isoformat(),
                    "status": "已发货",
                    "location": "广州",
                },
                {
                    "time": (datetime.now() - timedelta(hours=6)).isoformat(),
                    "status": "到达上海转运中心",
                    "location": "上海",
                },
            ],
        }

    # ============= 佣金统计 =============

    def get_commission_stats(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        获取佣金统计

        Args:
            user_id: 用户 ID
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            佣金统计信息
        """
        # Mock 统计数据
        return {
            "user_id": user_id,
            "period": {
                "start": (start_date or (datetime.now() - timedelta(days=30))).isoformat(),
                "end": (end_date or datetime.now()).isoformat(),
            },
            "total_orders": 15,
            "total_commission": 458.50,
            "pending_commission": 125.00,
            "paid_commission": 333.50,
            "top_category": "jewelry",
            "average_order_value": 650,
        }

    # ============= 礼物反馈分析 =============

    def submit_gift_feedback(
        self,
        order_id: str,
        recipient_user_id: str,
        rating: int,
        feedback_text: Optional[str] = None,
        would_use_again: bool = True,
    ) -> Dict[str, Any]:
        """
        提交礼物反馈

        Args:
            order_id: 订单 ID
            recipient_user_id: 接收人用户 ID
            rating: 评分 (1-5)
            feedback_text: 反馈文字
            would_use_again: 是否愿意再次使用

        Returns:
            反馈结果
        """
        # Mock 提交
        return {
            "success": True,
            "feedback_id": str(uuid.uuid4()),
            "order_id": order_id,
            "rating": rating,
            "message": "感谢您的反馈！",
        }

    def analyze_gift_effectiveness(
        self,
        sender_user_id: str,
        recipient_user_id: str,
    ) -> Dict[str, Any]:
        """
        分析礼物有效性

        Args:
            sender_user_id: 发送人用户 ID
            recipient_user_id: 接收人用户 ID

        Returns:
            有效性分析
        """
        # Mock 分析
        return {
            "sender_user_id": sender_user_id,
            "recipient_user_id": recipient_user_id,
            "total_gifts_sent": 5,
            "average_rating": 4.2,
            "best_received_category": "jewelry",
            "recommendations": [
                "对方似乎更喜欢珠宝类礼物",
                "预算在 500-1000 元的礼物评价最高",
                "定制类礼物获得更高情感价值评分",
            ],
        }

    # ============= 重要日期提醒 =============

    def get_upcoming_events(
        self,
        user_id: str,
        days_ahead: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        获取即将到来的重要日期

        Args:
            user_id: 用户 ID
            days_ahead: 提前多少天

        Returns:
            重要日期列表
        """
        # Mock 数据
        today = datetime.now()
        return [
            {
                "event": "生日",
                "partner_name": "小红",
                "date": (today + timedelta(days=12)).isoformat(),
                "days_remaining": 12,
                "gift_suggestions": ["项链", "口红", "鲜花"],
            },
            {
                "event": "纪念日",
                "partner_name": "小红",
                "date": (today + timedelta(days=25)).isoformat(),
                "days_remaining": 25,
                "gift_suggestions": ["定制礼物", "浪漫晚餐", "写真集"],
            },
        ]

    def set_gift_reminder(
        self,
        user_id: str,
        event_name: str,
        event_date: datetime,
        partner_name: str,
        reminder_days_before: int = 7,
    ) -> Dict[str, Any]:
        """
        设置礼物提醒

        Args:
            user_id: 用户 ID
            event_name: 事件名称
            event_date: 事件日期
            partner_name: 对方名称
            reminder_days_before: 提前多少天提醒

        Returns:
            提醒设置结果
        """
        reminder_id = str(uuid.uuid4())
        reminder_date = event_date - timedelta(days=reminder_days_before)

        return {
            "reminder_id": reminder_id,
            "user_id": user_id,
            "event_name": event_name,
            "event_date": event_date.isoformat(),
            "partner_name": partner_name,
            "reminder_date": reminder_date.isoformat(),
            "status": "active",
        }


# ============================================
# 工具函数
# ============================================

def get_occasion_name(occasion: str) -> str:
    """获取场合中文名称"""
    return GIFT_OCCASIONS.get(occasion, occasion)


def get_budget_range_display(budget_range: str) -> str:
    """获取预算范围显示名称"""
    range_info = BUDGET_RANGES.get(budget_range, (0, 999999, "不限"))
    return range_info[2]
