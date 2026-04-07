"""
v1.6 - 配额管理服务

功能：
1. 配额配置管理（按订阅等级）
2. 配额使用追踪
3. 配额限制检查
4. 超额处理（按量计费/阻止/通知）
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from models.db_models import (
    QuotaConfigDB, QuotaUsageDB, UserDB, SubscriptionTier, QuotaType
)
import logging

logger = logging.getLogger(__name__)


class QuotaService:
    """配额管理服务"""

    # 默认配额配置（如果数据库中没有配置）
    DEFAULT_QUOTA_CONFIGS = {
        "free": {
            "daily_searches": {"limit": 10, "unit": "times", "overage_policy": "block"},
            "monthly_reports": {"limit": 2, "unit": "times", "overage_policy": "block"},
            "daily_api_calls": {"limit": 100, "unit": "times", "overage_policy": "block"},
            "storage": {"limit": 1, "unit": "GB", "overage_policy": "block"},
            "export_count": {"limit": 5, "unit": "times", "overage_policy": "block", "quota_type": "monthly"},
        },
        "pro": {
            "daily_searches": {"limit": 100, "unit": "times", "overage_policy": "charge", "overage_price": 0.1},
            "monthly_reports": {"limit": 20, "unit": "times", "overage_policy": "charge", "overage_price": 5.0},
            "daily_api_calls": {"limit": 1000, "unit": "times", "overage_policy": "charge", "overage_price": 0.05},
            "storage": {"limit": 10, "unit": "GB", "overage_policy": "charge", "overage_price": 1.0},
            "export_count": {"limit": 50, "unit": "times", "overage_policy": "charge", "overage_price": 1.0, "quota_type": "monthly"},
        },
        "enterprise": {
            "daily_searches": {"limit": -1, "unit": "times", "overage_policy": "notify"},
            "monthly_reports": {"limit": -1, "unit": "times", "overage_policy": "notify"},
            "daily_api_calls": {"limit": -1, "unit": "times", "overage_policy": "notify"},
            "storage": {"limit": 100, "unit": "GB", "overage_policy": "charge", "overage_price": 0.5},
            "export_count": {"limit": -1, "unit": "times", "overage_policy": "notify", "quota_type": "monthly"},
        },
    }

    def __init__(self, db: Session):
        self.db = db

    # ==================== 配额配置管理 ====================

    def initialize_quota_configs(self):
        """初始化配额配置"""
        for tier, configs in self.DEFAULT_QUOTA_CONFIGS.items():
            for feature_name, config in configs.items():
                existing = self.db.query(QuotaConfigDB).filter(
                    and_(
                        QuotaConfigDB.subscription_tier == tier,
                        QuotaConfigDB.feature_name == feature_name
                    )
                ).first()

                quota_type_str = config.get("quota_type", "daily")
                quota_type = QuotaType[quota_type_str.upper()] if quota_type_str.upper() in QuotaType.__members__ else QuotaType.DAILY

                if not existing:
                    quota_config = QuotaConfigDB(
                        id=str(uuid.uuid4()),
                        subscription_tier=tier,
                        feature_name=feature_name,
                        quota_type=quota_type,
                        limit_value=config["limit"],
                        unit=config["unit"],
                        overage_policy=config.get("overage_policy", "block"),
                        overage_price=config.get("overage_price"),
                    )
                    self.db.add(quota_config)
                    logger.info(f"创建配额配置：tier={tier}, feature={feature_name}")

        self.db.commit()
        logger.info("配额配置初始化完成")

    def get_quota_config(self, subscription_tier: str, feature_name: str) -> Optional[QuotaConfigDB]:
        """获取配额配置"""
        return self.db.query(QuotaConfigDB).filter(
            and_(
                QuotaConfigDB.subscription_tier == subscription_tier,
                QuotaConfigDB.feature_name == feature_name
            )
        ).first()

    def get_all_quota_configs(self, subscription_tier: str) -> List[QuotaConfigDB]:
        """获取某订阅等级的所有配额配置"""
        return self.db.query(QuotaConfigDB).filter(
            QuotaConfigDB.subscription_tier == subscription_tier
        ).all()

    def update_quota_config(
        self,
        subscription_tier: str,
        feature_name: str,
        limit_value: int = None,
        overage_policy: str = None,
        overage_price: float = None,
    ) -> QuotaConfigDB:
        """更新配额配置"""
        config = self.get_quota_config(subscription_tier, feature_name)
        if not config:
            raise ValueError(f"配额配置不存在：tier={subscription_tier}, feature={feature_name}")

        if limit_value is not None:
            config.limit_value = limit_value
        if overage_policy is not None:
            config.overage_policy = overage_policy
        if overage_price is not None:
            config.overage_price = overage_price

        self.db.commit()
        self.db.refresh(config)

        logger.info(f"更新配额配置：tier={subscription_tier}, feature={feature_name}")
        return config

    # ==================== 配额使用追踪 ====================

    def get_period_bounds(self, quota_type: QuotaType) -> tuple:
        """获取配额周期边界"""
        now = datetime.now()

        if quota_type == QuotaType.DAILY:
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=1)
        elif quota_type == QuotaType.MONTHLY:
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if now.month == 12:
                period_end = period_start.replace(year=now.year + 1, month=1)
            else:
                period_end = period_start.replace(month=now.month + 1)
        else:  # ONE_TIME
            period_start = datetime.min
            period_end = datetime.max

        return period_start, period_end

    def get_usage_record(
        self,
        user_id: str,
        feature_name: str,
        quota_type: QuotaType,
    ) -> Optional[QuotaUsageDB]:
        """获取配额使用记录"""
        period_start, period_end = self.get_period_bounds(quota_type)

        return self.db.query(QuotaUsageDB).filter(
            and_(
                QuotaUsageDB.user_id == user_id,
                QuotaUsageDB.feature_name == feature_name,
                QuotaUsageDB.quota_type == quota_type,
                QuotaUsageDB.period_start == period_start,
                QuotaUsageDB.period_end == period_end,
            )
        ).first()

    def record_usage(
        self,
        user_id: str,
        feature_name: str,
        count: int = 1,
        tenant_id: str = None,
    ) -> Dict[str, Any]:
        """
        记录配额使用

        Returns:
            dict: {
                "allowed": bool,  # 是否允许使用
                "used_count": int,  # 当前已使用
                "limit": int,  # 限制
                "remaining": int,  # 剩余
                "overage": int,  # 超额
                "overage_charge": float,  # 超额费用
                "policy": str,  # 超额处理策略
            }
        """
        user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user:
            raise ValueError(f"用户不存在：{user_id}")

        subscription_tier = user.subscription_tier
        config = self.get_quota_config(subscription_tier, feature_name)

        if not config:
            # 没有配置，默认允许
            return {
                "allowed": True,
                "used_count": count,
                "limit": -1,
                "remaining": -1,
                "overage": 0,
                "overage_charge": 0,
                "policy": "none",
            }

        quota_type = config.quota_type
        period_start, period_end = self.get_period_bounds(quota_type)

        # 获取或创建使用记录
        usage = self.get_usage_record(user_id, feature_name, quota_type)
        if not usage:
            usage = QuotaUsageDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                tenant_id=tenant_id,
                feature_name=feature_name,
                quota_type=quota_type,
                used_count=0,
                overage_count=0,
                overage_charge=0,
                period_start=period_start,
                period_end=period_end,
            )
            self.db.add(usage)

        # 计算使用情况
        limit = config.limit_value
        new_used_count = usage.used_count + count
        overage = max(0, new_used_count - limit) if limit != -1 else 0

        # 检查是否允许使用
        allowed = True
        if limit != -1 and new_used_count > limit:
            if config.overage_policy == "block":
                allowed = False
            # charge 和 notify 策略允许使用

        if allowed:
            usage.used_count = new_used_count
            if overage > 0:
                usage.overage_count = overage
                if config.overage_price and config.overage_policy == "charge":
                    usage.overage_charge = overage * config.overage_price

            self.db.commit()

        remaining = max(0, limit - new_used_count) if limit != -1 else -1

        result = {
            "allowed": allowed,
            "used_count": new_used_count if allowed else usage.used_count,
            "limit": limit,
            "remaining": remaining,
            "overage": overage if allowed else 0,
            "overage_charge": usage.overage_charge if allowed else 0,
            "policy": config.overage_policy,
            "feature": feature_name,
            "quota_type": quota_type.value,
        }

        logger.info(f"记录配额使用：user={user_id}, feature={feature_name}, count={count}, result={result}")
        return result

    def check_quota(self, user_id: str, feature_name: str, count: int = 1) -> Dict[str, Any]:
        """
        检查配额（不记录使用）

        Returns:
            dict: 配额检查结果是
        """
        user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user:
            return {"allowed": False, "reason": "用户不存在"}

        subscription_tier = user.subscription_tier
        config = self.get_quota_config(subscription_tier, feature_name)

        if not config:
            return {
                "allowed": True,
                "limit": -1,
                "remaining": -1,
                "policy": "none",
            }

        quota_type = config.quota_type
        usage = self.get_usage_record(user_id, feature_name, quota_type)

        used_count = usage.used_count if usage else 0
        limit = config.limit_value
        remaining = max(0, limit - used_count) if limit != -1 else -1

        allowed = True
        if limit != -1 and used_count + count > limit:
            if config.overage_policy == "block":
                allowed = False

        return {
            "allowed": allowed,
            "used_count": used_count,
            "limit": limit,
            "remaining": remaining,
            "policy": config.overage_policy,
            "overage_price": config.overage_price,
        }

    def get_usage_stats(
        self,
        user_id: str,
        feature_name: str = None,
        include_history: bool = False,
    ) -> Dict[str, Any]:
        """获取配额使用统计"""
        user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user:
            return {}

        query = self.db.query(QuotaUsageDB).filter(QuotaUsageDB.user_id == user_id)

        if feature_name:
            query = query.filter(QuotaUsageDB.feature_name == feature_name)

        if not include_history:
            # 只返回当前周期的数据
            now = datetime.now()
            daily_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            monthly_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(
                and_(
                    QuotaUsageDB.period_start >= daily_start,
                    QuotaUsageDB.period_start <= monthly_start + timedelta(days=31)
                )
            )

        usage_records = query.all()

        # 按功能分组
        stats = {}
        for record in usage_records:
            key = record.feature_name
            if key not in stats:
                stats[key] = {
                    "feature_name": record.feature_name,
                    "quota_type": record.quota_type.value,
                    "used_count": 0,
                    "overage_count": 0,
                    "overage_charge": 0,
                }
            stats[key]["used_count"] += record.used_count
            stats[key]["overage_count"] += record.overage_count
            stats[key]["overage_charge"] += record.overage_charge

        # 添加配额限制信息
        for feature_name, feature_stats in stats.items():
            config = self.get_quota_config(user.subscription_tier, feature_name)
            if config:
                feature_stats["limit"] = config.limit_value
                feature_stats["unit"] = config.unit
                feature_stats["overage_policy"] = config.overage_policy

        return {
            "user_id": user_id,
            "subscription_tier": user.subscription_tier,
            "usage_stats": stats,
        }

    def reset_usage(self, user_id: str, feature_name: str = None):
        """重置配额使用（管理员操作）"""
        query = self.db.query(QuotaUsageDB).filter(QuotaUsageDB.user_id == user_id)
        if feature_name:
            query = query.filter(QuotaUsageDB.feature_name == feature_name)

        query.delete()
        self.db.commit()

        logger.info(f"重置配额使用：user={user_id}, feature={feature_name or 'all'}")


# 全局单例
def get_quota_service(db: Session) -> QuotaService:
    """获取配额服务实例"""
    return QuotaService(db)
