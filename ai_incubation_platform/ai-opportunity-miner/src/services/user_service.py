"""
P6 - 用户管理服务

功能：
1. 用户注册、登录、信息管理
2. 密码加密验证
3. 用户订阅管理
4. 审计日志记录
"""
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from models.db_models import UserDB, AuditLogDB, UsageRecordDB, SubscriptionTier
from config.settings import settings


class UserService:
    """用户服务"""

    # 订阅套餐配置
    SUBSCRIPTION_PLANS = {
        "free": {
            "name": "免费版",
            "price": 0,
            "limits": {
                "daily_searches": 10,
                "monthly_reports": 2,
                "data_sources": ["news", "enterprise"],
                "ai_analysis": False,
                "export_formats": ["json"],
            }
        },
        "pro": {
            "name": "专业版",
            "price": 299,  # 元/月
            "limits": {
                "daily_searches": 100,
                "monthly_reports": 20,
                "data_sources": ["news", "enterprise", "financing", "patent"],
                "ai_analysis": True,
                "export_formats": ["json", "pdf", "excel"],
            }
        },
        "enterprise": {
            "name": "企业版",
            "price": 999,  # 元/月
            "limits": {
                "daily_searches": -1,  # 无限制
                "monthly_reports": -1,  # 无限制
                "data_sources": ["news", "enterprise", "financing", "patent", "policy", "supply_chain"],
                "ai_analysis": True,
                "export_formats": ["json", "pdf", "excel", "api"],
                "api_access": True,
                "priority_support": True,
            }
        }
    }

    def __init__(self, db: Session):
        self.db = db

    # ==================== 用户管理 ====================

    def create_user(self, username: str, email: str, password: str, **kwargs) -> UserDB:
        """创建新用户"""
        # 检查用户名是否已存在
        existing = self.db.query(UserDB).filter(UserDB.username == username).first()
        if existing:
            raise ValueError(f"用户名 {username} 已存在")

        # 检查邮箱是否已存在
        existing = self.db.query(UserDB).filter(UserDB.email == email).first()
        if existing:
            raise ValueError(f"邮箱 {email} 已被注册")

        # 创建用户
        user = UserDB(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            password_hash=self._hash_password(password),
            full_name=kwargs.get("full_name"),
            company_name=kwargs.get("company_name"),
            phone=kwargs.get("phone"),
            subscription_tier="free",  # 默认免费版
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        # 记录审计日志
        self._log_action(user.id, "USER_REGISTER", "用户注册")

        return user

    def authenticate(self, username: str, password: str) -> Optional[UserDB]:
        """验证用户登录"""
        user = self.db.query(UserDB).filter(UserDB.username == username).first()
        if not user:
            return None

        if not user.is_active:
            return None

        if not self._verify_password(password, user.password_hash):
            return None

        # 更新最后登录时间
        user.last_login_at = datetime.now()
        self.db.commit()

        # 记录审计日志
        self._log_action(user.id, "USER_LOGIN", "用户登录")

        return user

    def get_user(self, user_id: str) -> Optional[UserDB]:
        """获取用户信息"""
        return self.db.query(UserDB).filter(UserDB.id == user_id).first()

    def get_user_by_username(self, username: str) -> Optional[UserDB]:
        """通过用户名获取用户"""
        return self.db.query(UserDB).filter(UserDB.username == username).first()

    def update_user(self, user_id: str, **kwargs) -> UserDB:
        """更新用户信息"""
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"用户 {user_id} 不存在")

        # 更新字段
        allowed_fields = ["full_name", "company_name", "phone", "email"]
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(user, field, value)

        # 密码更新
        if "password" in kwargs:
            user.password_hash = self._hash_password(kwargs["password"])

        self.db.commit()
        self.db.refresh(user)

        # 记录审计日志
        self._log_action(user_id, "USER_UPDATE", "更新用户信息")

        return user

    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        # 使用 SHA-256 哈希（生产环境应使用 bcrypt 或 argon2）
        return hashlib.sha256(password.encode()).hexdigest()

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        return self._hash_password(password) == password_hash

    # ==================== 订阅管理 ====================

    def get_subscription_plan(self, tier: str) -> Dict[str, Any]:
        """获取订阅套餐信息"""
        return self.SUBSCRIPTION_PLANS.get(tier, self.SUBSCRIPTION_PLANS["free"])

    def get_user_limits(self, user_id: str) -> Dict[str, Any]:
        """获取用户限制"""
        user = self.get_user(user_id)
        if not user:
            return self.SUBSCRIPTION_PLANS["free"]["limits"]

        return self.SUBSCRIPTION_PLANS.get(user.subscription_tier, self.SUBSCRIPTION_PLANS["free"])["limits"]

    def upgrade_subscription(self, user_id: str, new_tier: str) -> UserDB:
        """升级订阅"""
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"用户 {user_id} 不存在")

        if new_tier not in self.SUBSCRIPTION_PLANS:
            raise ValueError(f"无效的订阅等级：{new_tier}")

        user.subscription_tier = new_tier
        user.subscription_started_at = datetime.now()
        user.subscription_expires_at = datetime.now() + timedelta(days=30)  # 默认 30 天

        self.db.commit()
        self.db.refresh(user)

        # 记录审计日志
        self._log_action(user_id, "SUBSCRIPTION_UPGRADE", f"升级订阅到 {new_tier}")

        return user

    def cancel_subscription(self, user_id: str) -> UserDB:
        """取消订阅（降级到免费版）"""
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"用户 {user_id} 不存在")

        user.subscription_tier = "free"
        user.subscription_expires_at = None

        self.db.commit()
        self.db.refresh(user)

        # 记录审计日志
        self._log_action(user_id, "SUBSCRIPTION_CANCEL", "取消订阅")

        return user

    # ==================== 用量管理 ====================

    def record_usage(self, user_id: str, feature: str, count: int = 1, details: Dict = None):
        """记录使用量"""
        user = self.get_user(user_id)
        if not user:
            return

        today = datetime.now().strftime("%Y-%m-%d")

        # 检查是否已有今日记录
        record = self.db.query(UsageRecordDB).filter(
            UsageRecordDB.user_id == user_id,
            UsageRecordDB.feature == feature,
            UsageRecordDB.date == today
        ).first()

        if record:
            record.count += count
        else:
            record = UsageRecordDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                feature=feature,
                count=count,
                details=details or {},
                date=today,
            )
            self.db.add(record)

        self.db.commit()

    def get_usage_stats(self, user_id: str, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """获取用量统计"""
        user = self.get_user(user_id)
        if not user:
            return {}

        query = self.db.query(UsageRecordDB).filter(UsageRecordDB.user_id == user_id)

        if start_date:
            query = query.filter(UsageRecordDB.date >= start_date)
        if end_date:
            query = query.filter(UsageRecordDB.date <= end_date)

        records = query.all()

        # 按功能分组统计
        stats = {}
        for record in records:
            if record.feature not in stats:
                stats[record.feature] = 0
            stats[record.feature] += record.count

        return {
            "user_id": user_id,
            "subscription_tier": user.subscription_tier,
            "usage_stats": stats,
            "period": {
                "start": start_date or "all",
                "end": end_date or "today",
            }
        }

    def check_limit(self, user_id: str, feature: str, limit_key: str) -> bool:
        """检查是否超出限制"""
        user = self.get_user(user_id)
        if not user:
            return False

        limits = self.SUBSCRIPTION_PLANS.get(user.subscription_tier, self.SUBSCRIPTION_PLANS["free"])["limits"]
        limit = limits.get(limit_key, -1)

        if limit == -1:  # 无限制
            return True

        today = datetime.now().strftime("%Y-%m-%d")
        record = self.db.query(UsageRecordDB).filter(
            UsageRecordDB.user_id == user_id,
            UsageRecordDB.feature == feature,
            UsageRecordDB.date == today
        ).first()

        current_count = record.count if record else 0
        return current_count < limit

    # ==================== 审计日志 ====================

    def _log_action(self, user_id: str, action: str, notes: str = None, **kwargs):
        """记录审计日志"""
        log = AuditLogDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            action=action,
            notes=notes,
            request_method=kwargs.get("request_method"),
            request_path=kwargs.get("request_path"),
            request_body=kwargs.get("request_body"),
            response_status=kwargs.get("response_status"),
            ip_address=kwargs.get("ip_address"),
            user_agent=kwargs.get("user_agent"),
        )
        self.db.add(log)
        self.db.commit()

    def get_audit_logs(self, user_id: str, limit: int = 50) -> List[AuditLogDB]:
        """获取用户审计日志"""
        return self.db.query(AuditLogDB).filter(
            AuditLogDB.user_id == user_id
        ).order_by(AuditLogDB.created_at.desc()).limit(limit).all()


# 全局单例（用于 API 层）
_user_service_instances = {}


def get_user_service(db: Session) -> UserService:
    """获取用户服务实例"""
    return UserService(db)
