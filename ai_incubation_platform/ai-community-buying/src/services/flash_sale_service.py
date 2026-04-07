"""
限时秒杀服务 (任务#13)

功能：
- 秒杀活动管理（创建/编辑/上下架）
- 时间段控制（整点开启、倒计时）
- 秒杀库存独立管理
- 高并发下单优化
- 防刷单机制
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import uuid
import hashlib
import logging

from models.p0_entities import FlashSaleEntity, FlashSaleOrderEntity, FlashSaleStatus
from models.entities import ProductEntity

logger = logging.getLogger(__name__)


class FlashSaleService:
    """限时秒杀服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_flash_sale(
        self,
        product_id: str,
        title: str,
        flash_price: float,
        flash_stock: int,
        start_time: datetime,
        end_time: datetime,
        created_by: str,
        min_group_size: int = 1,
        max_group_size: int = 10,
        per_user_limit: int = 1
    ) -> FlashSaleEntity:
        """创建秒杀活动"""
        # 验证商品存在
        product = self.db.query(ProductEntity).filter(ProductEntity.id == product_id).first()
        if not product:
            raise ValueError(f"商品 {product_id} 不存在")

        # 验证秒杀价格
        if flash_price >= product.price:
            raise ValueError("秒杀价格必须低于原价")

        # 验证时间
        if start_time >= end_time:
            raise ValueError("开始时间必须早于结束时间")

        # 检查商品是否已有进行中的秒杀
        existing = self.db.query(FlashSaleEntity).filter(
            and_(
                FlashSaleEntity.product_id == product_id,
                FlashSaleEntity.status.in_([FlashSaleStatus.UPCOMING, FlashSaleStatus.ONGOING])
            )
        ).first()
        if existing:
            raise ValueError(f"商品已有进行中的秒杀活动")

        # 创建秒杀活动
        flash_sale = FlashSaleEntity(
            id=str(uuid.uuid4()),
            product_id=product_id,
            title=title,
            flash_price=flash_price,
            flash_stock=flash_stock,
            total_stock=flash_stock,
            min_group_size=min_group_size,
            max_group_size=max_group_size,
            start_time=start_time,
            end_time=end_time,
            status=self._calculate_status(start_time, end_time),
            per_user_limit=per_user_limit,
            created_by=created_by
        )

        self.db.add(flash_sale)
        self.db.commit()
        self.db.refresh(flash_sale)

        logger.info(f"创建秒杀活动：{flash_sale.id}, 商品：{product_id}, 价格：{flash_price}")
        return flash_sale

    def update_flash_sale(
        self,
        flash_sale_id: str,
        title: Optional[str] = None,
        flash_price: Optional[float] = None,
        flash_stock: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        per_user_limit: Optional[int] = None
    ) -> FlashSaleEntity:
        """更新秒杀活动"""
        flash_sale = self._get_flash_sale(flash_sale_id)

        # 进行中的秒杀只能更新库存
        if flash_sale.status == FlashSaleStatus.ONGOING:
            if flash_stock is not None:
                flash_sale.flash_stock = flash_stock
                flash_sale.total_stock = flash_stock
            self.db.commit()
            self.db.refresh(flash_sale)
            return flash_sale

        # 未开始的秒杀可以更新所有字段
        if title is not None:
            flash_sale.title = title
        if flash_price is not None:
            flash_sale.flash_price = flash_price
        if flash_stock is not None:
            flash_sale.flash_stock = flash_stock
            flash_sale.total_stock = flash_stock
        if start_time is not None:
            flash_sale.start_time = start_time
        if end_time is not None:
            flash_sale.end_time = end_time
        if per_user_limit is not None:
            flash_sale.per_user_limit = per_user_limit

        # 重新计算状态
        flash_sale.status = self._calculate_status(flash_sale.start_time, flash_sale.end_time)

        self.db.commit()
        self.db.refresh(flash_sale)
        return flash_sale

    def toggle_flash_sale(self, flash_sale_id: str) -> FlashSaleEntity:
        """上下架秒杀活动"""
        flash_sale = self._get_flash_sale(flash_sale_id)

        if flash_sale.status == FlashSaleStatus.ONGOING:
            # 进行中不能下架，只能结束
            flash_sale.status = FlashSaleStatus.ENDED
        elif flash_sale.status in [FlashSaleStatus.UPCOMING, FlashSaleStatus.EXPIRED]:
            # 未开始或已过期可以重新激活
            flash_sale.status = FlashSaleStatus.UPCOMING

        self.db.commit()
        self.db.refresh(flash_sale)
        return flash_sale

    def get_flash_sale(self, flash_sale_id: str) -> FlashSaleEntity:
        """获取秒杀详情"""
        flash_sale = self._get_flash_sale(flash_sale_id)
        # 更新浏览人数
        flash_sale.view_count += 1
        self.db.commit()
        return flash_sale

    def list_flash_sales(
        self,
        status: Optional[str] = None,
        product_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[FlashSaleEntity]:
        """获取秒杀列表"""
        query = self.db.query(FlashSaleEntity)

        if status:
            query = query.filter(FlashSaleEntity.status == status)
        if product_id:
            query = query.filter(FlashSaleEntity.product_id == product_id)

        # 自动更新过期状态
        now = datetime.now()
        self.db.query(FlashSaleEntity).filter(
            and_(
                FlashSaleEntity.status == FlashSaleStatus.ONGOING,
                FlashSaleEntity.end_time < now
            )
        ).update({"status": FlashSaleStatus.ENDED})

        return query.order_by(FlashSaleEntity.start_time.desc()).offset(offset).limit(limit).all()

    def place_order(
        self,
        flash_sale_id: str,
        user_id: str,
        quantity: int,
        device_fingerprint: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> FlashSaleOrderEntity:
        """秒杀下单（高并发优化版本）"""
        # 开启事务
        flash_sale = self.db.query(FlashSaleEntity).with_for_update().filter(
            FlashSaleEntity.id == flash_sale_id
        ).first()

        if not flash_sale:
            raise ValueError("秒杀活动不存在")

        # 检查秒杀状态
        now = datetime.now()
        current_status = self._calculate_status(flash_sale.start_time, flash_sale.end_time)
        if current_status != FlashSaleStatus.ONGOING:
            raise ValueError(f"秒杀活动状态：{current_status}")

        # 检查库存
        if flash_sale.flash_stock < quantity:
            raise ValueError("秒杀库存不足")

        # 防刷单：检查用户限购
        existing_orders = self.db.query(FlashSaleOrderEntity).filter(
            and_(
                FlashSaleOrderEntity.flash_sale_id == flash_sale_id,
                FlashSaleOrderEntity.user_id == user_id
            )
        ).all()
        total_purchased = sum(o.quantity for o in existing_orders)
        if total_purchased + quantity > flash_sale.per_user_limit:
            raise ValueError(f"超过限购数量，每人限购{flash_sale.per_user_limit}件")

        # 防刷单：设备指纹检查
        if device_fingerprint:
            device_orders = self.db.query(FlashSaleOrderEntity).filter(
                and_(
                    FlashSaleOrderEntity.flash_sale_id == flash_sale_id,
                    FlashSaleOrderEntity.device_fingerprint == device_fingerprint
                )
            ).count()
            if device_orders >= flash_sale.per_user_limit:
                raise ValueError("该设备已达到购买上限")

        # 扣减库存（使用数据库行锁保证原子性）
        flash_sale.flash_stock -= quantity
        flash_sale.purchased_count += quantity

        # 创建订单
        order = FlashSaleOrderEntity(
            id=str(uuid.uuid4()),
            flash_sale_id=flash_sale_id,
            user_id=user_id,
            product_id=flash_sale.product_id,
            quantity=quantity,
            unit_price=flash_sale.flash_price,
            total_amount=flash_sale.flash_price * quantity,
            status="pending",
            order_number=self._generate_order_number(),
            device_fingerprint=device_fingerprint,
            ip_address=ip_address
        )

        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)

        logger.info(f"秒杀下单成功：{order.id}, 用户：{user_id}, 数量：{quantity}")
        return order

    def get_user_orders(self, flash_sale_id: str, user_id: str) -> List[FlashSaleOrderEntity]:
        """获取用户的秒杀订单"""
        return self.db.query(FlashSaleOrderEntity).filter(
            and_(
                FlashSaleOrderEntity.flash_sale_id == flash_sale_id,
                FlashSaleOrderEntity.user_id == user_id
            )
        ).all()

    def get_countdown(self, flash_sale_id: str) -> Dict[str, Any]:
        """获取秒杀倒计时"""
        flash_sale = self._get_flash_sale(flash_sale_id)
        now = datetime.now()

        if flash_sale.status == FlashSaleStatus.UPCOMING:
            remaining = (flash_sale.start_time - now).total_seconds()
            return {
                "status": "upcoming",
                "remaining_seconds": max(0, remaining),
                "start_time": flash_sale.start_time.isoformat(),
                "message": f"距离秒杀开始还有 {self._format_countdown(remaining)}"
            }
        elif flash_sale.status == FlashSaleStatus.ONGOING:
            remaining = (flash_sale.end_time - now).total_seconds()
            return {
                "status": "ongoing",
                "remaining_seconds": max(0, remaining),
                "end_time": flash_sale.end_time.isoformat(),
                "message": f"距离秒杀结束还有 {self._format_countdown(remaining)}"
            }
        else:
            return {
                "status": flash_sale.status,
                "remaining_seconds": 0,
                "message": "秒杀已结束"
            }

    def _get_flash_sale(self, flash_sale_id: str) -> FlashSaleEntity:
        """获取秒杀活动（内部方法）"""
        flash_sale = self.db.query(FlashSaleEntity).filter(
            FlashSaleEntity.id == flash_sale_id
        ).first()
        if not flash_sale:
            raise ValueError(f"秒杀活动 {flash_sale_id} 不存在")
        return flash_sale

    def _calculate_status(self, start_time: datetime, end_time: datetime) -> str:
        """计算秒杀状态"""
        now = datetime.now()
        if now < start_time:
            return FlashSaleStatus.UPCOMING
        elif now < end_time:
            return FlashSaleStatus.ONGOING
        else:
            return FlashSaleStatus.ENDED

    def _format_countdown(self, seconds: float) -> str:
        """格式化倒计时"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _generate_order_number(self) -> str:
        """生成订单号"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        random_str = str(uuid.uuid4())[:8]
        return f"FS{timestamp}{random_str}"
