"""
新人专享服务 (任务#14)

功能：
- 新人身份识别
- 新人专享价商品池
- 新人券包自动发放
- 新人任务引导
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import uuid
import json

from models.p0_entities import (
    NewbieProfileEntity, NewbieStatus,
    NewbieProductEntity, NewbieCouponTemplateEntity,
    NewbieTaskEntity, NewbieTaskProgressEntity
)
from models.entities import ProductEntity, CouponEntity
from sqlalchemy import or_
import logging

logger = logging.getLogger(__name__)


class NewbieService:
    """新人专享服务"""

    def __init__(self, db: Session):
        self.db = db

    # ========== 新人身份识别 ==========

    def get_or_create_newbie_profile(self, user_id: str) -> NewbieProfileEntity:
        """获取或创建新人档案"""
        profile = self.db.query(NewbieProfileEntity).filter(
            NewbieProfileEntity.user_id == user_id
        ).first()

        if not profile:
            # 创建新人档案
            profile = NewbieProfileEntity(
                id=str(uuid.uuid4()),
                user_id=user_id,
                status=NewbieStatus.ELIGIBLE,
                registered_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=7)  # 新人权益 7 天有效
            )
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
            logger.info(f"创建新人档案：{user_id}")

        return profile

    def check_newbie_eligibility(self, user_id: str) -> Dict[str, Any]:
        """检查新人资格"""
        profile = self.get_or_create_newbie_profile(user_id)

        # 检查是否过期
        if profile.expires_at and datetime.now() > profile.expires_at:
            profile.status = NewbieStatus.EXPIRED
            self.db.commit()
            return {
                "is_newbie": False,
                "status": NewbieStatus.EXPIRED,
                "message": "新人权益已过期"
            }

        # 检查是否已完成首单
        if profile.status == NewbieStatus.FIRST_ORDER:
            return {
                "is_newbie": False,
                "status": profile.status,
                "message": "已完成首单，不再是新人"
            }

        return {
            "is_newbie": True,
            "status": profile.status,
            "message": "符合新人资格",
            "expires_at": profile.expires_at.isoformat() if profile.expires_at else None
        }

    # ========== 新人专享商品池 ==========

    def add_newbie_product(
        self,
        product_id: str,
        newbie_price: float,
        original_price: float,
        stock_limit: int = 100,
        per_user_limit: int = 1,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> NewbieProductEntity:
        """添加新人专享商品"""
        # 验证商品存在
        product = self.db.query(ProductEntity).filter(ProductEntity.id == product_id).first()
        if not product:
            raise ValueError(f"商品 {product_id} 不存在")

        # 验证价格
        if newbie_price >= original_price:
            raise ValueError("新人专享价必须低于原价")

        # 检查是否已是新人专享商品
        existing = self.db.query(NewbieProductEntity).filter(
            NewbieProductEntity.product_id == product_id
        ).first()
        if existing:
            existing.newbie_price = newbie_price
            existing.stock_limit = stock_limit
            existing.per_user_limit = per_user_limit
            existing.is_active = True
            self.db.commit()
            self.db.refresh(existing)
            return existing

        # 创建新人专享商品
        newbie_product = NewbieProductEntity(
            id=str(uuid.uuid4()),
            product_id=product_id,
            newbie_price=newbie_price,
            original_price=original_price,
            stock_limit=stock_limit,
            per_user_limit=per_user_limit,
            start_time=start_time,
            end_time=end_time,
            is_active=True
        )

        self.db.add(newbie_product)
        self.db.commit()
        self.db.refresh(newbie_product)

        logger.info(f"添加新人专享商品：{product_id}, 价格：{newbie_price}")
        return newbie_product

    def get_newbie_products(self, limit: int = 20) -> List[NewbieProductEntity]:
        """获取新人专享商品列表"""
        now = datetime.now()
        return self.db.query(NewbieProductEntity).filter(
            and_(
                NewbieProductEntity.is_active == True,
                or_(
                    NewbieProductEntity.start_time == None,
                    NewbieProductEntity.start_time <= now
                ),
                or_(
                    NewbieProductEntity.end_time == None,
                    NewbieProductEntity.end_time > now
                )
            )
        ).limit(limit).all()

    def purchase_newbie_product(
        self,
        user_id: str,
        product_id: str,
        quantity: int
    ) -> Dict[str, Any]:
        """购买新人专享商品"""
        # 检查新人资格
        eligibility = self.check_newbie_eligibility(user_id)
        if not eligibility["is_newbie"]:
            raise ValueError(f"不符合新人资格：{eligibility['message']}")

        # 获取新人专享商品
        newbie_product = self.db.query(NewbieProductEntity).filter(
            NewbieProductEntity.product_id == product_id
        ).first()
        if not newbie_product or not newbie_product.is_active:
            raise ValueError("该商品不在新人专享池中")

        # 检查库存
        if newbie_product.purchased_count + quantity > newbie_product.stock_limit:
            raise ValueError("新人专享库存不足")

        # 检查限购
        # TODO: 查询用户已购买数量
        if quantity > newbie_product.per_user_limit:
            raise ValueError(f"超过限购数量，每人限购{newbie_product.per_user_limit}件")

        # 更新购买数量
        newbie_product.purchased_count += quantity

        self.db.commit()

        return {
            "product_id": product_id,
            "quantity": quantity,
            "unit_price": newbie_product.newbie_price,
            "total_amount": newbie_product.newbie_price * quantity
        }

    # ========== 新人券包 ==========

    def create_newbie_coupon_template(
        self,
        name: str,
        coupon_config: Dict[str, Any],
        total_quantity: int = 10000,
        description: str = ""
    ) -> NewbieCouponTemplateEntity:
        """创建新人券包模板"""
        template = NewbieCouponTemplateEntity(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            coupon_config=json.dumps(coupon_config),
            total_quantity=total_quantity
        )

        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)

        logger.info(f"创建新人券包模板：{name}")
        return template

    def claim_newbie_coupon(self, user_id: str) -> Dict[str, Any]:
        """领取新人券包"""
        profile = self.get_or_create_newbie_profile(user_id)

        # 检查是否已领取
        if profile.benefits_claimed:
            return {
                "success": False,
                "message": "已领取过新人券包"
            }

        # 获取券包模板
        template = self.db.query(NewbieCouponTemplateEntity).filter(
            NewbieCouponTemplateEntity.is_active == True
        ).first()
        if not template:
            return {
                "success": False,
                "message": "暂无可用新人券包"
            }

        # 检查库存
        if template.claimed_quantity >= template.total_quantity:
            return {
                "success": False,
                "message": "新人券包已领完"
            }

        # 解析券包配置并发放优惠券
        coupon_config = json.loads(template.coupon_config)
        claimed_coupons = []

        for config in coupon_config:
            coupon = CouponEntity(
                id=str(uuid.uuid4()),
                user_id=user_id,
                template_id=config["template_id"],
                code=self._generate_coupon_code(),
                status="available",
                valid_from=datetime.now(),
                valid_to=datetime.now() + timedelta(days=config.get("valid_days", 30))
            )
            self.db.add(coupon)
            claimed_coupons.append({
                "coupon_id": coupon.id,
                "code": coupon.code,
                "value": config.get("value", 0)
            })

        # 更新状态
        profile.benefits_claimed = True
        profile.coupon_claimed_at = datetime.now()
        profile.status = NewbieStatus.CLAIMED
        template.claimed_quantity += 1

        self.db.commit()

        logger.info(f"用户 {user_id} 领取新人券包，获得{len(claimed_coupons)}张优惠券")

        return {
            "success": True,
            "message": "领取成功",
            "coupons": claimed_coupons
        }

    # ========== 新人任务引导 ==========

    def create_newbie_task(
        self,
        task_name: str,
        task_type: str,
        description: str,
        reward_type: str,
        reward_value: float,
        reward_desc: str,
        sort_order: int = 0
    ) -> NewbieTaskEntity:
        """创建新人任务"""
        task = NewbieTaskEntity(
            id=str(uuid.uuid4()),
            task_name=task_name,
            task_type=task_type,
            description=description,
            reward_type=reward_type,
            reward_value=reward_value,
            reward_desc=reward_desc,
            sort_order=sort_order
        )

        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        logger.info(f"创建新人任务：{task_name}")
        return task

    def get_newbie_tasks(self, user_id: str) -> List[Dict[str, Any]]:
        """获取新人任务列表（含进度）"""
        tasks = self.db.query(NewbieTaskEntity).filter(
            NewbieTaskEntity.is_active == True
        ).order_by(NewbieTaskEntity.sort_order).all()

        result = []
        for task in tasks:
            progress = self.db.query(NewbieTaskProgressEntity).filter(
                and_(
                    NewbieTaskProgressEntity.user_id == user_id,
                    NewbieTaskProgressEntity.task_id == task.id
                )
            ).first()

            result.append({
                "task_id": task.id,
                "task_name": task.task_name,
                "task_type": task.task_type,
                "description": task.description,
                "reward_type": task.reward_type,
                "reward_value": task.reward_value,
                "reward_desc": task.reward_desc,
                "status": progress.status if progress else "not_started",
                "progress": progress.progress if progress else 0,
                "target": progress.target if progress else task.target if hasattr(task, 'target') else 1,
                "reward_claimed": progress.reward_claimed if progress else False
            })

        return result

    def complete_newbie_task(self, user_id: str, task_type: str) -> Dict[str, Any]:
        """完成新人任务"""
        profile = self.get_or_create_newbie_profile(user_id)

        # 获取任务
        task = self.db.query(NewbieTaskEntity).filter(
            and_(
                NewbieTaskEntity.task_type == task_type,
                NewbieTaskEntity.is_active == True
            )
        ).first()
        if not task:
            return {"success": False, "message": "任务不存在"}

        # 获取或创建进度
        progress = self.db.query(NewbieTaskProgressEntity).filter(
            and_(
                NewbieTaskProgressEntity.user_id == user_id,
                NewbieTaskProgressEntity.task_id == task.id
            )
        ).first()

        if not progress:
            progress = NewbieTaskProgressEntity(
                id=str(uuid.uuid4()),
                user_id=user_id,
                task_id=task.id,
                status="completed",
                progress=1,
                target=1,
                completed_at=datetime.now()
            )
            self.db.add(progress)
        else:
            progress.status = "completed"
            progress.progress = 1
            progress.completed_at = datetime.now()

        # 特殊处理：首单任务更新新人状态
        if task_type == "first_order":
            profile.status = NewbieStatus.FIRST_ORDER
            profile.first_order_at = datetime.now()

        self.db.commit()

        logger.info(f"用户 {user_id} 完成任务：{task.task_name}")

        return {
            "success": True,
            "message": "任务完成",
            "reward_type": task.reward_type,
            "reward_value": task.reward_value,
            "reward_desc": task.reward_desc
        }

    def claim_task_reward(self, user_id: str, task_id: str) -> Dict[str, Any]:
        """领取任务奖励"""
        progress = self.db.query(NewbieTaskProgressEntity).filter(
            and_(
                NewbieTaskProgressEntity.user_id == user_id,
                NewbieTaskProgressEntity.task_id == task_id
            )
        ).first()

        if not progress:
            return {"success": False, "message": "任务进度不存在"}

        if progress.status != "completed":
            return {"success": False, "message": "任务未完成"}

        if progress.reward_claimed:
            return {"success": False, "message": "奖励已领取"}

        # 获取任务
        task = self.db.query(NewbieTaskEntity).filter(
            NewbieTaskEntity.id == task_id
        ).first()

        # 标记奖励已领取
        progress.reward_claimed = True
        progress.claimed_at = datetime.now()

        # TODO: 根据奖励类型发放奖励
        # 这里简化处理，实际应该调用优惠券服务或积分服务

        self.db.commit()

        logger.info(f"用户 {user_id} 领取任务奖励：{task.task_name}")

        return {
            "success": True,
            "message": "奖励领取成功",
            "reward_type": task.reward_type,
            "reward_value": task.reward_value
        }

    def _generate_coupon_code(self) -> str:
        """生成优惠券码"""
        return f"NB{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:8].upper()}"
