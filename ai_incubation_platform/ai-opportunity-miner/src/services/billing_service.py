"""
v1.6 - 计费管理服务

功能：
1. 计费账户管理
2. 按量计费
3. 预付费套餐包
4. 充值管理
5. 账单生成
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from models.db_models import (
    BillingAccountDB, BillingItemDB, RechargeRecordDB, PackageDB,
    UserPackageDB, OrderDB, UserDB, BillingMode
)
import logging

logger = logging.getLogger(__name__)


class BillingService:
    """计费管理服务"""

    # 默认套餐包配置
    DEFAULT_PACKAGES = [
        {
            "name": "API 调用包 - 基础版",
            "code": "API_BASIC",
            "credits": 1000,
            "storage_gb": 0,
            "export_count": 0,
            "valid_days": 365,
            "original_price": 200,
            "current_price": 150,
        },
        {
            "name": "API 调用包 - 专业版",
            "code": "API_PRO",
            "credits": 5000,
            "storage_gb": 5,
            "export_count": 20,
            "valid_days": 365,
            "original_price": 800,
            "current_price": 600,
        },
        {
            "name": "API 调用包 - 企业版",
            "code": "API_ENTERPRISE",
            "credits": 50000,
            "storage_gb": 50,
            "export_count": 200,
            "valid_days": 365,
            "original_price": 5000,
            "current_price": 4000,
        },
        {
            "name": "存储空间包",
            "code": "STORAGE_PACK",
            "credits": 0,
            "storage_gb": 100,
            "export_count": 0,
            "valid_days": 365,
            "original_price": 500,
            "current_price": 400,
        },
        {
            "name": "导出次数包",
            "code": "EXPORT_PACK",
            "credits": 0,
            "storage_gb": 0,
            "export_count": 100,
            "valid_days": 365,
            "original_price": 300,
            "current_price": 200,
        },
    ]

    # 计费单价配置
    BILLING_RATES = {
        "api_call": 0.1,      # 每次 API 调用
        "storage_gb": 1.0,    # 每 GB 存储/月
        "export": 2.0,        # 每次导出
        "report": 10.0,       # 每份报告
        "ml_prediction": 5.0, # 每次 ML 预测
    }

    def __init__(self, db: Session):
        self.db = db

    # ==================== 计费账户管理 ====================

    def get_billing_account(self, user_id: str) -> Optional[BillingAccountDB]:
        """获取计费账户"""
        return self.db.query(BillingAccountDB).filter(
            BillingAccountDB.user_id == user_id
        ).first()

    def create_billing_account(
        self,
        user_id: str,
        billing_mode: BillingMode = BillingMode.SUBSCRIPTION,
        tenant_id: str = None,
    ) -> BillingAccountDB:
        """创建计费账户"""
        account = self.get_billing_account(user_id)
        if account:
            return account

        account = BillingAccountDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            tenant_id=tenant_id,
            billing_mode=billing_mode,
            balance=0,
            credit_limit=0,
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)

        logger.info(f"创建计费账户：user={user_id}, mode={billing_mode.value}")
        return account

    def update_billing_mode(self, user_id: str, new_mode: BillingMode) -> BillingAccountDB:
        """更新计费模式"""
        account = self.get_billing_account(user_id)
        if not account:
            account = self.create_billing_account(user_id, new_mode)
            return account

        account.billing_mode = new_mode
        self.db.commit()
        self.db.refresh(account)

        logger.info(f"更新计费模式：user={user_id}, new_mode={new_mode.value}")
        return account

    def get_account_balance(self, user_id: str) -> Dict[str, Any]:
        """获取账户余额信息"""
        account = self.get_billing_account(user_id)
        if not account:
            return {
                "balance": 0,
                "credit_limit": 0,
                "available_balance": 0,
            }

        return {
            "balance": account.balance,
            "credit_limit": account.credit_limit,
            "available_balance": account.balance + account.credit_limit,
            "billing_mode": account.billing_mode.value if account.billing_mode else None,
            "auto_recharge_enabled": account.auto_recharge_enabled,
            "auto_recharge_threshold": account.auto_recharge_threshold,
            "auto_recharge_amount": account.auto_recharge_amount,
        }

    # ==================== 按量计费 ====================

    def create_billing_item(
        self,
        user_id: str,
        item_name: str,
        item_type: str,
        quantity: float,
        unit_price: float = None,
        tenant_id: str = None,
        related_order_id: str = None,
        related_resource_id: str = None,
    ) -> BillingItemDB:
        """创建计费项目"""
        if unit_price is None:
            unit_price = self.BILLING_RATES.get(item_type, 0)

        total_amount = quantity * unit_price

        item = BillingItemDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            tenant_id=tenant_id,
            item_name=item_name,
            item_type=item_type,
            quantity=quantity,
            unit_price=unit_price,
            total_amount=total_amount,
            related_order_id=related_order_id,
            related_resource_id=related_resource_id,
            status="pending",
        )

        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)

        logger.info(f"创建计费项目：user={user_id}, item={item_name}, amount={total_amount}")
        return item

    def charge_billing_item(self, user_id: str, item_id: str) -> Dict[str, Any]:
        """从账户扣除计费项目费用"""
        account = self.get_billing_account(user_id)
        if not account:
            raise ValueError(f"计费账户不存在：{user_id}")

        item = self.db.query(BillingItemDB).filter(
            and_(
                BillingItemDB.id == item_id,
                BillingItemDB.user_id == user_id
            )
        ).first()
        if not item:
            raise ValueError(f"计费项目不存在：{item_id}")

        if item.status != "pending":
            raise ValueError(f"计费项目状态不是待支付：{item.status}")

        # 检查余额
        if account.balance < item.total_amount:
            # 检查是否启用自动充值
            if account.auto_recharge_enabled and account.balance < account.auto_recharge_threshold:
                # 自动充值
                self._auto_recharge(account)
            else:
                raise ValueError(f"账户余额不足：当前余额 {account.balance}, 需要 {item.total_amount}")

        # 扣款
        account.balance -= item.total_amount
        account.total_consumed += item.total_amount
        item.status = "billed"

        self.db.commit()

        logger.info(f"扣除计费项目：user={user_id}, item={item_id}, amount={item.total_amount}")
        return {
            "success": True,
            "item_id": item_id,
            "amount": item.total_amount,
            "balance_after": account.balance,
        }

    def _auto_recharge(self, account: BillingAccountDB):
        """自动充值（内部方法）"""
        # 这里应该调用支付接口进行自动充值
        # 简化处理：直接增加余额（实际需要支付成功回调）
        account.balance += account.auto_recharge_amount
        account.total_recharged += account.auto_recharge_amount

        logger.info(f"自动充值：user={account.user_id}, amount={account.auto_recharge_amount}")

    # ==================== 套餐包管理 ====================

    def initialize_packages(self):
        """初始化默认套餐包"""
        for pkg_config in self.DEFAULT_PACKAGES:
            existing = self.db.query(PackageDB).filter(
                PackageDB.code == pkg_config["code"]
            ).first()

            if not existing:
                package = PackageDB(
                    id=str(uuid.uuid4()),
                    name=pkg_config["name"],
                    code=pkg_config["code"],
                    credits=pkg_config["credits"],
                    storage_gb=pkg_config["storage_gb"],
                    export_count=pkg_config["export_count"],
                    valid_days=pkg_config["valid_days"],
                    original_price=pkg_config["original_price"],
                    current_price=pkg_config["current_price"],
                    is_active=True,
                )
                self.db.add(package)
                logger.info(f"创建套餐包：{pkg_config['name']}")

        self.db.commit()
        logger.info("套餐包初始化完成")

    def get_packages(self, is_active: bool = True) -> List[PackageDB]:
        """获取所有套餐包"""
        query = self.db.query(PackageDB)
        if is_active:
            query = query.filter(PackageDB.is_active == True)
        return query.all()

    def get_package_by_code(self, code: str) -> Optional[PackageDB]:
        """通过代码获取套餐包"""
        return self.db.query(PackageDB).filter(PackageDB.code == code).first()

    def purchase_package(
        self,
        user_id: str,
        package_code: str,
        order_id: str = None,
    ) -> UserPackageDB:
        """购买套餐包"""
        package = self.get_package_by_code(package_code)
        if not package:
            raise ValueError(f"套餐包不存在：{package_code}")

        now = datetime.now()
        end_date = now + timedelta(days=package.valid_days)

        user_package = UserPackageDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            package_id=package.id,
            order_id=order_id,
            credits_total=package.credits,
            credits_used=0,
            storage_gb_total=package.storage_gb,
            storage_gb_used=0,
            export_count_total=package.export_count,
            export_count_used=0,
            start_date=now,
            end_date=end_date,
            status="active",
        )

        self.db.add(user_package)
        self.db.commit()
        self.db.refresh(user_package)

        logger.info(f"购买套餐包：user={user_id}, package={package.name}")
        return user_package

    def get_user_packages(self, user_id: str, status: str = "active") -> List[UserPackageDB]:
        """获取用户的套餐包"""
        query = self.db.query(UserPackageDB).filter(
            UserPackageDB.user_id == user_id
        )
        if status:
            query = query.filter(UserPackageDB.status == status)
        return query.all()

    def get_package_summary(self, user_id: str) -> Dict[str, Any]:
        """获取用户套餐包汇总"""
        packages = self.get_user_packages(user_id, status="active")

        summary = {
            "total_credits": 0,
            "used_credits": 0,
            "remaining_credits": 0,
            "total_storage_gb": 0,
            "used_storage_gb": 0,
            "remaining_storage_gb": 0,
            "total_exports": 0,
            "used_exports": 0,
            "remaining_exports": 0,
            "packages": [],
        }

        for pkg in packages:
            summary["total_credits"] += pkg.credits_total
            summary["used_credits"] += pkg.credits_used
            summary["remaining_credits"] += (pkg.credits_total - pkg.credits_used)

            summary["total_storage_gb"] += pkg.storage_gb_total
            summary["used_storage_gb"] += pkg.storage_gb_used
            summary["remaining_storage_gb"] += (pkg.storage_gb_total - pkg.storage_gb_used)

            summary["total_exports"] += pkg.export_count_total
            summary["used_exports"] += pkg.export_count_used
            summary["remaining_exports"] += (pkg.export_count_total - pkg.export_count_used)

            summary["packages"].append({
                "name": pkg.package.name if pkg.package else "Unknown",
                "credits": pkg.credits_total - pkg.credits_used,
                "storage_gb": pkg.storage_gb_total - pkg.storage_gb_used,
                "exports": pkg.export_count_total - pkg.export_count_used,
                "end_date": pkg.end_date.isoformat(),
            })

        return summary

    def consume_package_credit(
        self,
        user_id: str,
        credit_type: str,
        count: int = 1,
    ) -> Dict[str, Any]:
        """
        消耗套餐包额度

        Args:
            user_id: 用户 ID
            credit_type: 额度类型 (credits/storage_gb/exports)
            count: 消耗数量

        Returns:
            dict: 消耗结果
        """
        packages = self.get_user_packages(user_id, status="active")
        if not packages:
            return {
                "success": False,
                "message": "没有可用的套餐包",
                "consumed": 0,
            }

        # 按到期时间排序，优先使用先到期的
        packages.sort(key=lambda x: x.end_date)

        remaining = count
        consumed = 0

        for pkg in packages:
            if remaining <= 0:
                break

            if credit_type == "credits":
                available = pkg.credits_total - pkg.credits_used
                consume = min(available, remaining)
                pkg.credits_used += consume
            elif credit_type == "storage_gb":
                available = pkg.storage_gb_total - pkg.storage_gb_used
                consume = min(available, remaining)
                pkg.storage_gb_used += consume
            elif credit_type == "exports":
                available = pkg.export_count_total - pkg.export_count_used
                consume = min(available, remaining)
                pkg.export_count_used += consume
            else:
                raise ValueError(f"无效的额度类型：{credit_type}")

            remaining -= consume
            consumed += consume

            # 检查是否用完
            if credit_type == "credits" and pkg.credits_used >= pkg.credits_total:
                if pkg.storage_gb_used >= pkg.storage_gb_total and pkg.export_count_used >= pkg.export_count_total:
                    pkg.status = "exhausted"
            elif credit_type == "storage_gb" and pkg.storage_gb_used >= pkg.storage_gb_total:
                if pkg.credits_used >= pkg.credits_total and pkg.export_count_used >= pkg.export_count_total:
                    pkg.status = "exhausted"
            elif credit_type == "exports" and pkg.export_count_used >= pkg.export_count_total:
                if pkg.credits_used >= pkg.credits_total and pkg.storage_gb_used >= pkg.storage_gb_total:
                    pkg.status = "exhausted"

        self.db.commit()

        # 检查过期套餐
        self._check_expired_packages(user_id)

        return {
            "success": remaining == 0,
            "consumed": consumed,
            "remaining_needed": remaining,
            "message": f"成功消耗 {consumed} {credit_type}" if remaining == 0 else f"套餐包额度不足，还差 {remaining} {credit_type}",
        }

    def _check_expired_packages(self, user_id: str):
        """检查并更新过期套餐包"""
        now = datetime.now()
        packages = self.db.query(UserPackageDB).filter(
            and_(
                UserPackageDB.user_id == user_id,
                UserPackageDB.status == "active",
                UserPackageDB.end_date < now
            )
        ).all()

        for pkg in packages:
            pkg.status = "expired"

        if packages:
            self.db.commit()
            logger.info(f"更新过期套餐包：user={user_id}, count={len(packages)}")

    # ==================== 充值管理 ====================

    def create_recharge_record(
        self,
        user_id: str,
        amount: float,
        order_id: str = None,
        tenant_id: str = None,
    ) -> RechargeRecordDB:
        """创建充值记录"""
        record = RechargeRecordDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            tenant_id=tenant_id,
            order_id=order_id,
            amount=amount,
            bonus_amount=0,  # 可根据充值金额计算赠送金额
            total_amount=amount,
            status="pending",
        )

        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        logger.info(f"创建充值记录：user={user_id}, amount={amount}")
        return record

    def complete_recharge(
        self,
        record_id: str,
        payment_method: str = None,
        transaction_id: str = None,
    ) -> RechargeRecordDB:
        """完成充值"""
        record = self.db.query(RechargeRecordDB).filter(
            RechargeRecordDB.id == record_id
        ).first()
        if not record:
            raise ValueError(f"充值记录不存在：{record_id}")

        if record.status != "pending":
            raise ValueError(f"充值记录状态不是待处理：{record.status}")

        record.status = "success"
        record.payment_method = payment_method
        record.transaction_id = transaction_id
        record.completed_at = datetime.now()

        # 更新计费账户余额
        account = self.get_billing_account(record.user_id)
        if not account:
            account = self.create_billing_account(record.user_id)

        account.balance += record.total_amount
        account.total_recharged += record.total_amount

        self.db.commit()
        self.db.refresh(record)

        logger.info(f"充值完成：user={record.user_id}, amount={record.total_amount}")
        return record

    def get_recharge_history(self, user_id: str, limit: int = 50) -> List[RechargeRecordDB]:
        """获取充值历史"""
        return self.db.query(RechargeRecordDB).filter(
            RechargeRecordDB.user_id == user_id
        ).order_by(RechargeRecordDB.created_at.desc()).limit(limit).all()

    # ==================== 账单生成 ====================

    def generate_bill(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """生成账单"""
        items = self.db.query(BillingItemDB).filter(
            and_(
                BillingItemDB.user_id == user_id,
                BillingItemDB.created_at >= start_date,
                BillingItemDB.created_at <= end_date,
            )
        ).all()

        total_amount = sum(item.total_amount for item in items)

        # 按类型分组
        by_type = {}
        for item in items:
            if item.item_type not in by_type:
                by_type[item.item_type] = {"count": 0, "amount": 0}
            by_type[item.item_type]["count"] += 1
            by_type[item.item_type]["amount"] += item.total_amount

        return {
            "user_id": user_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "total_amount": total_amount,
            "item_count": len(items),
            "by_type": by_type,
            "items": [item.to_dict() for item in items[:100]],  # 限制返回数量
        }


# 全局单例
def get_billing_service(db: Session) -> BillingService:
    """获取计费服务实例"""
    return BillingService(db)
