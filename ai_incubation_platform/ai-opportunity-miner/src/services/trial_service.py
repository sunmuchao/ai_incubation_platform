"""
P6 - 试用服务

功能：
1. 试用申请与管理
2. 试用转订阅
3. 试用取消
4. 试用统计
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from models.db_models import TrialRecordDB, UserDB
from services.user_service import UserService
import logging

logger = logging.getLogger(__name__)


class TrialService:
    """试用服务"""

    # 试用配置
    TRIAL_CONFIG = {
        "pro": {
            "trial_days": 7,  # 专业版试用 7 天
            "eligible_tiers": ["free"],  # 只有免费版用户可以试用
        },
        "enterprise": {
            "trial_days": 14,  # 企业版试用 14 天
            "eligible_tiers": ["free", "pro"],  # 免费版和专业版用户可以试用
        },
    }

    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)

    # ==================== 试用申请 ====================

    def start_trial(
        self,
        user_id: str,
        trial_tier: str = "pro",
    ) -> Dict[str, Any]:
        """
        开始试用

        Args:
            user_id: 用户 ID
            trial_tier: 试用等级 (pro/enterprise)

        Returns:
            dict: 试用信息
        """
        # 检查用户是否存在
        user = self.user_service.get_user(user_id)
        if not user:
            raise ValueError(f"用户不存在：{user_id}")

        # 检查试用等级是否有效
        if trial_tier not in self.TRIAL_CONFIG:
            raise ValueError(f"不支持的试用等级：{trial_tier}")

        # 检查用户是否有资格试用
        eligible_tiers = self.TRIAL_CONFIG[trial_tier]["eligible_tiers"]
        if user.subscription_tier not in eligible_tiers:
            raise ValueError(f"用户当前订阅等级 ({user.subscription_tier}) 不符合试用条件")

        # 检查用户是否已经试用过
        existing_trial = self.db.query(TrialRecordDB).filter(
            TrialRecordDB.user_id == user_id
        ).first()

        if existing_trial:
            if existing_trial.status == "active":
                raise ValueError(f"用户已有正在进行的试用")
            elif existing_trial.status == "converted":
                raise ValueError(f"用户已试用过并转化为付费用户")

        # 创建试用记录
        trial_days = self.TRIAL_CONFIG[trial_tier]["trial_days"]
        trial_start = datetime.now()
        trial_end = trial_start + timedelta(days=trial_days)

        trial = TrialRecordDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            trial_tier=trial_tier,
            trial_start=trial_start,
            trial_end=trial_end,
            status="active",
        )

        self.db.add(trial)

        # 临时升级用户订阅等级为试用等级
        user.subscription_tier = trial_tier
        user.subscription_started_at = trial_start
        user.subscription_expires_at = trial_end

        self.db.commit()
        self.db.refresh(trial)

        logger.info(f"开始试用：user_id={user_id}, tier={trial_tier}, end={trial_end}")

        return {
            "trial": trial.to_dict(),
            "message": f"试用已开始，您现在可以体验 {trial_tier} 版的所有功能",
            "trial_end": trial_end.isoformat(),
            "trial_days_remaining": trial_days,
        }

    # ==================== 试用管理 ====================

    def get_trial_status(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取试用状态

        Args:
            user_id: 用户 ID

        Returns:
            dict: 试用状态信息
        """
        trial = self.db.query(TrialRecordDB).filter(
            TrialRecordDB.user_id == user_id
        ).first()

        if not trial:
            return None

        result = trial.to_dict()

        # 计算剩余天数
        if trial.status == "active":
            now = datetime.now()
            if now >= trial.trial_end:
                # 试用已过期
                trial.status = "expired"
                self.db.commit()
                result["status"] = "expired"

                # 降级用户到免费版
                user = self.user_service.get_user(user_id)
                if user:
                    user.subscription_tier = "free"
                    user.subscription_expires_at = None
                    self.db.commit()
            else:
                remaining = trial.trial_end - now
                result["days_remaining"] = remaining.days
                result["hours_remaining"] = remaining.seconds // 3600

        return result

    def cancel_trial(
        self,
        user_id: str,
        reason: str = None,
    ) -> Dict[str, Any]:
        """
        取消试用

        Args:
            user_id: 用户 ID
            reason: 取消原因

        Returns:
            dict: 取消结果
        """
        trial = self.db.query(TrialRecordDB).filter(
            TrialRecordDB.user_id == user_id
        ).first()

        if not trial:
            raise ValueError(f"用户没有试用记录")

        if trial.status != "active":
            raise ValueError(f"试用状态不是进行中：{trial.status}")

        # 更新试用记录
        trial.status = "cancelled"
        trial.cancelled_at = datetime.now()
        trial.cancel_reason = reason

        # 降级用户到免费版
        user = self.user_service.get_user(user_id)
        if user:
            user.subscription_tier = "free"
            user.subscription_expires_at = None

        self.db.commit()

        logger.info(f"试用已取消：user_id={user_id}, reason={reason}")

        return {
            "success": True,
            "message": "试用已取消",
            "cancelled_at": trial.cancelled_at.isoformat(),
        }

    def convert_trial(
        self,
        user_id: str,
        new_tier: str,
    ) -> Dict[str, Any]:
        """
        试用转订阅

        Args:
            user_id: 用户 ID
            new_tier: 新订阅等级

        Returns:
            dict: 转化结果
        """
        trial = self.db.query(TrialRecordDB).filter(
            TrialRecordDB.user_id == user_id
        ).first()

        if not trial:
            raise ValueError(f"用户没有试用记录")

        if trial.status != "active":
            raise ValueError(f"试用状态不是进行中：{trial.status}")

        # 更新试用记录
        trial.status = "converted"
        trial.converted_at = datetime.now()
        trial.converted_tier = new_tier

        # 更新用户订阅
        user = self.user_service.get_user(user_id)
        if user:
            user.subscription_tier = new_tier
            user.subscription_started_at = datetime.now()
            user.subscription_expires_at = datetime.now() + timedelta(days=30)

        self.db.commit()

        logger.info(f"试用转化成功：user_id={user_id}, new_tier={new_tier}")

        return {
            "success": True,
            "message": f"试用已成功转化为 {new_tier} 订阅",
            "subscription_expires_at": user.subscription_expires_at.isoformat(),
        }

    # ==================== 试用统计 ====================

    def get_trial_statistics(self) -> Dict[str, Any]:
        """
        获取试用统计

        Returns:
            dict: 试用统计数据
        """
        # 按状态统计
        active_count = self.db.query(TrialRecordDB).filter(
            TrialRecordDB.status == "active"
        ).count()

        converted_count = self.db.query(TrialRecordDB).filter(
            TrialRecordDB.status == "converted"
        ).count()

        expired_count = self.db.query(TrialRecordDB).filter(
            TrialRecordDB.status == "expired"
        ).count()

        cancelled_count = self.db.query(TrialRecordDB).filter(
            TrialRecordDB.status == "cancelled"
        ).count()

        # 转化率
        total_finished = converted_count + expired_count + cancelled_count
        conversion_rate = 0
        if total_finished > 0:
            conversion_rate = converted_count / total_finished * 100

        # 按等级统计
        pro_count = self.db.query(TrialRecordDB).filter(
            TrialRecordDB.trial_tier == "pro"
        ).count()

        enterprise_count = self.db.query(TrialRecordDB).filter(
            TrialRecordDB.trial_tier == "enterprise"
        ).count()

        return {
            "total_trials": active_count + converted_count + expired_count + cancelled_count,
            "active_trials": active_count,
            "converted_trials": converted_count,
            "expired_trials": expired_count,
            "cancelled_trials": cancelled_count,
            "conversion_rate": round(conversion_rate, 2),
            "by_tier": {
                "pro": pro_count,
                "enterprise": enterprise_count,
            },
        }

    def get_expired_trials(self) -> List[TrialRecordDB]:
        """获取已过期的试用记录"""
        now = datetime.now()
        return self.db.query(TrialRecordDB).filter(
            TrialRecordDB.status == "active",
            TrialRecordDB.trial_end < now
        ).all()

    def get_trials_expiring_soon(self, days: int = 3) -> List[TrialRecordDB]:
        """获取即将过期的试用记录"""
        now = datetime.now()
        expiry_threshold = now + timedelta(days=days)

        return self.db.query(TrialRecordDB).filter(
            TrialRecordDB.status == "active",
            TrialRecordDB.trial_end <= expiry_threshold,
            TrialRecordDB.trial_end > now
        ).all()


# 全局单例
def get_trial_service(db: Session) -> TrialService:
    """获取试用服务实例"""
    return TrialService(db)
