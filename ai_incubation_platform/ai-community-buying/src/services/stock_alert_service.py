"""
库存紧张提示服务 (任务#56)

功能：
- 库存阈值动态计算
- 库存紧张标签
- "X 人在看"热度提示
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import uuid
import logging
import time

from models.p0_entities import (
    ProductViewTrackerEntity,
    StockAlertConfigEntity,
    ProductHeatmapEntity
)
from models.entities import ProductEntity

logger = logging.getLogger(__name__)


class StockAlertService:
    """库存紧张提示服务"""

    def __init__(self, db: Session):
        self.db = db

    # ========== 库存阈值管理 ==========

    def get_stock_status(self, product_id: str) -> Dict[str, Any]:
        """获取商品库存状态"""
        product = self.db.query(ProductEntity).filter(
            ProductEntity.id == product_id
        ).first()

        if not product:
            raise ValueError(f"商品 {product_id} 不存在")

        # 获取库存配置
        config = self.db.query(StockAlertConfigEntity).filter(
            StockAlertConfigEntity.product_id == product_id
        ).first()

        # 默认阈值
        alert_threshold = config.alert_threshold if config else 10
        urgent_threshold = config.urgent_threshold if config else 5

        # 计算可用库存
        available_stock = product.stock - product.locked_stock

        # 判断库存状态
        if available_stock <= 0:
            stock_status = "out_of_stock"
            stock_label = "已售罄"
        elif available_stock <= urgent_threshold:
            stock_status = "urgent"
            stock_label = f"仅剩{available_stock}件"
        elif available_stock <= alert_threshold:
            stock_status = "low_stock"
            stock_label = f"仅剩{available_stock}件"
        else:
            stock_status = "sufficient"
            stock_label = "库存充足"

        return {
            "product_id": product_id,
            "available_stock": available_stock,
            "total_stock": product.stock,
            "locked_stock": product.locked_stock,
            "sold_stock": product.sold_stock,
            "stock_status": stock_status,
            "stock_label": stock_label,
            "alert_threshold": alert_threshold,
            "urgent_threshold": urgent_threshold
        }

    def set_stock_alert_config(
        self,
        product_id: str,
        alert_threshold: int = 10,
        urgent_threshold: int = 5
    ) -> StockAlertConfigEntity:
        """设置库存警报配置"""
        config = self.db.query(StockAlertConfigEntity).filter(
            StockAlertConfigEntity.product_id == product_id
        ).first()

        if config:
            config.alert_threshold = alert_threshold
            config.urgent_threshold = urgent_threshold
        else:
            config = StockAlertConfigEntity(
                id=str(uuid.uuid4()),
                product_id=product_id,
                alert_threshold=alert_threshold,
                urgent_threshold=urgent_threshold
            )
            self.db.add(config)

        self.db.commit()
        self.db.refresh(config)

        return config

    def get_low_stock_products(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取库存紧张商品列表"""
        now = datetime.now()
        products = self.db.query(ProductEntity).filter(
            and_(
                ProductEntity.stock > 0,
                ProductEntity.stock <= 10  # 默认阈值
            )
        ).order_by(ProductEntity.stock.asc()).limit(limit).all()

        return [self.get_stock_status(p.id) for p in products]

    # ========== 商品浏览追踪 ==========

    def track_view(
        self,
        product_id: str,
        session_id: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        device_type: Optional[str] = None
    ) -> None:
        """追踪商品浏览"""
        tracker = ProductViewTrackerEntity(
            id=str(uuid.uuid4()),
            product_id=product_id,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            device_type=device_type
        )

        self.db.add(tracker)

        # 更新热度数据
        self._update_heatmap(product_id, session_id)

        self.db.commit()

    def _update_heatmap(self, product_id: str, session_id: str) -> None:
        """更新商品热度"""
        heatmap = self.db.query(ProductHeatmapEntity).filter(
            ProductHeatmapEntity.product_id == product_id
        ).first()

        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)

        if not heatmap:
            heatmap = ProductHeatmapEntity(
                id=str(uuid.uuid4()),
                product_id=product_id,
                current_viewers=1,
                peak_viewers=1,
                total_views_today=1,
                total_views_week=1,
                total_views_month=1,
                heat_score=1.0
            )
            self.db.add(heatmap)
        else:
            # 增加浏览数
            heatmap.total_views_today += 1
            heatmap.total_views_week += 1
            heatmap.total_views_month += 1
            heatmap.current_viewers += 1

            # 更新 peak
            if heatmap.current_viewers > heatmap.peak_viewers:
                heatmap.peak_viewers = heatmap.current_viewers

            # 重新计算热度分数
            heatmap.heat_score = self._calculate_heat_score(heatmap)
            heatmap.last_updated = now

    def _calculate_heat_score(self, heatmap: ProductHeatmapEntity) -> float:
        """计算热度分数"""
        # 权重配置
        w_current = 10      # 当前浏览人数权重
        w_today = 1         # 今日浏览权重
        w_week = 0.1        # 本周浏览权重
        w_month = 0.01      # 本月浏览权重
        w_wishlist = 5      # 收藏权重
        w_share = 3         # 分享权重

        score = (
            heatmap.current_viewers * w_current +
            heatmap.total_views_today * w_today +
            heatmap.total_views_week * w_week +
            heatmap.total_views_month * w_month +
            heatmap.wishlist_count * w_wishlist +
            heatmap.share_count * w_share
        )

        # 归一化到 0-100
        return min(100, score)

    def get_product_heatmap(self, product_id: str) -> Dict[str, Any]:
        """获取商品热度信息"""
        heatmap = self.db.query(ProductHeatmapEntity).filter(
            ProductHeatmapEntity.product_id == product_id
        ).first()

        if not heatmap:
            return {
                "product_id": product_id,
                "current_viewers": 0,
                "heat_score": 0,
                "heat_label": ""
            }

        # 生成热度标签
        heat_label = self._get_heat_label(heatmap.heat_score)

        return {
            "product_id": product_id,
            "current_viewers": heatmap.current_viewers,
            "peak_viewers": heatmap.peak_viewers,
            "total_views_today": heatmap.total_views_today,
            "total_views_week": heatmap.total_views_week,
            "total_views_month": heatmap.total_views_month,
            "wishlist_count": heatmap.wishlist_count,
            "share_count": heatmap.share_count,
            "heat_score": heatmap.heat_score,
            "heat_label": heat_label,
            "last_updated": heatmap.last_updated.isoformat()
        }

    def _get_heat_label(self, heat_score: float) -> str:
        """获取热度标签"""
        if heat_score >= 80:
            return "🔥 火爆热销"
        elif heat_score >= 60:
            return "📈 人气飙升"
        elif heat_score >= 40:
            return "👀 多人关注"
        elif heat_score >= 20:
            return "📊 值得关注"
        else:
            return ""

    def get_viewers_count(self, product_id: str) -> int:
        """获取当前浏览人数"""
        heatmap = self.db.query(ProductHeatmapEntity).filter(
            ProductHeatmapEntity.product_id == product_id
        ).first()
        return heatmap.current_viewers if heatmap else 0

    def decrement_viewers(self, product_id: str) -> None:
        """减少浏览人数（用户离开时调用）"""
        heatmap = self.db.query(ProductHeatmapEntity).filter(
            ProductHeatmapEntity.product_id == product_id
        ).first()

        if heatmap and heatmap.current_viewers > 0:
            heatmap.current_viewers -= 1
            self.db.commit()

    def get_hot_products(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取热门商品列表"""
        products = self.db.query(ProductHeatmapEntity).filter(
            ProductHeatmapEntity.current_viewers > 0
        ).order_by(
            ProductHeatmapEntity.heat_score.desc(),
            ProductHeatmapEntity.current_viewers.desc()
        ).limit(limit).all()

        return [
            {
                "product_id": p.product_id,
                "current_viewers": p.current_viewers,
                "heat_score": p.heat_score,
                "heat_label": self._get_heat_label(p.heat_score)
            }
            for p in products
        ]

    # ========== 收藏和分享追踪 ==========

    def track_wishlist(self, product_id: str) -> None:
        """追踪商品收藏"""
        heatmap = self.db.query(ProductHeatmapEntity).filter(
            ProductHeatmapEntity.product_id == product_id
        ).first()

        if not heatmap:
            heatmap = ProductHeatmapEntity(
                id=str(uuid.uuid4()),
                product_id=product_id,
                wishlist_count=1,
                heat_score=5.0  # 收藏权重 5
            )
            self.db.add(heatmap)
        else:
            heatmap.wishlist_count += 1
            heatmap.heat_score = self._calculate_heat_score(heatmap)

        self.db.commit()

    def track_share(self, product_id: str) -> None:
        """追踪商品分享"""
        heatmap = self.db.query(ProductHeatmapEntity).filter(
            ProductHeatmapEntity.product_id == product_id
        ).first()

        if not heatmap:
            heatmap = ProductHeatmapEntity(
                id=str(uuid.uuid4()),
                product_id=product_id,
                share_count=1,
                heat_score=3.0  # 分享权重 3
            )
            self.db.add(heatmap)
        else:
            heatmap.share_count += 1
            heatmap.heat_score = self._calculate_heat_score(heatmap)

        self.db.commit()

    # ========== 综合库存和热度信息 ==========

    def get_product_enhanced_info(self, product_id: str) -> Dict[str, Any]:
        """获取商品增强信息（库存状态 + 热度信息）"""
        stock_info = self.get_stock_status(product_id)
        heatmap_info = self.get_product_heatmap(product_id)

        return {
            **stock_info,
            **heatmap_info,
            "urgency_tips": self._generate_urgency_tips(stock_info, heatmap_info)
        }

    def _generate_urgency_tips(
        self,
        stock_info: Dict[str, Any],
        heatmap_info: Dict[str, Any]
    ) -> Optional[str]:
        """生成 urgency 提示文案"""
        tips = []

        # 库存紧张提示
        if stock_info["stock_status"] == "urgent":
            tips.append(f"🔴 库存告急！仅剩{stock_info['available_stock']}件")
        elif stock_info["stock_status"] == "low_stock":
            tips.append(f"🟡 库存紧张！仅剩{stock_info['available_stock']}件")

        # 热度提示
        if heatmap_info.get("current_viewers", 0) >= 5:
            tips.append(f"👀 {heatmap_info['current_viewers']}人正在看")
        elif heatmap_info.get("heat_label"):
            tips.append(heatmap_info["heat_label"])

        return " | ".join(tips) if tips else None
