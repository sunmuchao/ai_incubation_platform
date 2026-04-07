"""
P7 - API 密钥管理服务

功能：
1. API Key 创建、删除、管理
2. API 访问鉴权
3. 速率限制
4. 使用统计
"""
import uuid
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from models.db_models import APIKeyDB, APIUsageLogDB, UserDB
from services.user_service import UserService


class APIKeyService:
    """API 密钥服务"""

    # 默认权限范围
    DEFAULT_SCOPES = ["read:opportunities", "read:trends"]
    AVAILABLE_SCOPES = [
        "read:opportunities",
        "write:opportunities",
        "read:trends",
        "read:companies",
        "read:investment",
        "read:equity",
        "ml:predict",
        "export:report",
    ]

    # 默认速率限制
    DEFAULT_RATE_LIMIT_PER_MINUTE = 60
    DEFAULT_RATE_LIMIT_PER_DAY = 1000

    def __init__(self, db: Session):
        self.db = db

    # ==================== API Key 管理 ====================

    def create_api_key(
        self,
        user_id: str,
        name: str,
        description: str = None,
        scopes: List[str] = None,
        rate_limit_per_minute: int = None,
        rate_limit_per_day: int = None,
        expires_in_days: int = None,
    ) -> APIKeyDB:
        """创建 API Key"""
        user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user:
            raise ValueError(f"用户 {user_id} 不存在")

        # 检查订阅等级（只有企业版可以创建 API Key）
        if user.subscription_tier != "enterprise":
            # 专业版可以创建但有更多限制
            if user.subscription_tier != "pro":
                raise ValueError("只有专业版或企业版用户可以创建 API Key")

        # 验证权限范围
        if scopes:
            for scope in scopes:
                if scope not in self.AVAILABLE_SCOPES:
                    raise ValueError(f"无效的权限范围：{scope}")
        else:
            scopes = self.DEFAULT_SCOPES.copy()

        # 生成 API Key
        raw_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        # 计算过期时间
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now() + timedelta(days=expires_in_days)

        api_key = APIKeyDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            key=key_hash,
            name=name,
            description=description,
            scopes=scopes,
            rate_limit_per_minute=rate_limit_per_minute or self.DEFAULT_RATE_LIMIT_PER_MINUTE,
            rate_limit_per_day=rate_limit_per_day or self.DEFAULT_RATE_LIMIT_PER_DAY,
            expires_at=expires_at,
        )

        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)

        # 返回时包含原始 key（只显示一次）
        api_key._raw_key = raw_key
        return api_key

    def get_api_key(self, api_key_id: str) -> Optional[APIKeyDB]:
        """获取 API Key 详情"""
        return self.db.query(APIKeyDB).filter(
            APIKeyDB.id == api_key_id
        ).first()

    def get_api_key_by_key(self, key: str) -> Optional[APIKeyDB]:
        """通过密钥字符串获取 API Key"""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.db.query(APIKeyDB).filter(
            APIKeyDB.key == key_hash
        ).first()

    def list_api_keys(self, user_id: str) -> List[APIKeyDB]:
        """获取用户的所有 API Key"""
        return self.db.query(APIKeyDB).filter(
            APIKeyDB.user_id == user_id
        ).order_by(APIKeyDB.created_at.desc()).all()

    def revoke_api_key(self, api_key_id: str, user_id: str) -> bool:
        """撤销 API Key"""
        api_key = self.get_api_key(api_key_id)
        if not api_key:
            raise ValueError(f"API Key {api_key_id} 不存在")

        if api_key.user_id != user_id:
            raise ValueError("无权操作此 API Key")

        api_key.is_active = False
        self.db.commit()
        return True

    def update_api_key(
        self,
        api_key_id: str,
        user_id: str,
        name: str = None,
        description: str = None,
        scopes: List[str] = None,
        rate_limit_per_minute: int = None,
        rate_limit_per_day: int = None,
    ) -> APIKeyDB:
        """更新 API Key"""
        api_key = self.get_api_key(api_key_id)
        if not api_key:
            raise ValueError(f"API Key {api_key_id} 不存在")

        if api_key.user_id != user_id:
            raise ValueError("无权操作此 API Key")

        if name:
            api_key.name = name
        if description is not None:
            api_key.description = description
        if scopes:
            for scope in scopes:
                if scope not in self.AVAILABLE_SCOPES:
                    raise ValueError(f"无效的权限范围：{scope}")
            api_key.scopes = scopes
        if rate_limit_per_minute:
            api_key.rate_limit_per_minute = rate_limit_per_minute
        if rate_limit_per_day:
            api_key.rate_limit_per_day = rate_limit_per_day

        self.db.commit()
        self.db.refresh(api_key)
        return api_key

    # ==================== API 鉴权 ====================

    def authenticate_api_key(self, key: str) -> Optional[APIKeyDB]:
        """验证 API Key"""
        api_key = self.get_api_key_by_key(key)
        if not api_key:
            return None

        # 检查是否激活
        if not api_key.is_active:
            return None

        # 检查是否过期
        if api_key.expires_at and api_key.expires_at < datetime.now():
            api_key.is_active = False
            self.db.commit()
            return None

        # 更新最后使用时间
        api_key.last_used_at = datetime.now()
        self.db.commit()

        return api_key

    def check_permission(self, api_key: APIKeyDB, required_scope: str) -> bool:
        """检查 API Key 是否有指定权限"""
        if not api_key.scopes:
            return False
        return required_scope in api_key.scopes

    # ==================== 速率限制 ====================

    def check_rate_limit(self, api_key_id: str, user_id: str) -> Dict[str, Any]:
        """检查速率限制"""
        today = datetime.now().strftime("%Y-%m-%d")
        current_minute = datetime.now().strftime("%Y-%m-%d %H:%M")

        api_key = self.get_api_key(api_key_id)
        if not api_key:
            return {"allowed": False, "reason": "API Key not found"}

        # 检查每分钟限制
        minute_logs = self.db.query(APIUsageLogDB).filter(
            APIUsageLogDB.api_key_id == api_key_id,
            APIUsageLogDB.created_at >= current_minute,
        ).count()

        if minute_logs >= api_key.rate_limit_per_minute:
            return {
                "allowed": False,
                "reason": "Rate limit per minute exceeded",
                "retry_after_seconds": 60,
            }

        # 检查每天限制
        day_logs = self.db.query(APIUsageLogDB).filter(
            APIUsageLogDB.api_key_id == api_key_id,
            APIUsageLogDB.created_at >= today,
        ).count()

        if day_logs >= api_key.rate_limit_per_day:
            return {
                "allowed": False,
                "reason": "Rate limit per day exceeded",
                "retry_after_seconds": 86400,
            }

        return {"allowed": True}

    def log_api_usage(
        self,
        api_key_id: str,
        user_id: str,
        endpoint: str,
        method: str,
        request_params: Dict = None,
        response_status: int = None,
        response_time_ms: int = None,
    ):
        """记录 API 使用日志"""
        log = APIUsageLogDB(
            id=str(uuid.uuid4()),
            api_key_id=api_key_id,
            user_id=user_id,
            endpoint=endpoint,
            method=method,
            request_params=request_params,
            response_status=response_status,
            response_time_ms=response_time_ms,
        )
        self.db.add(log)
        self.db.commit()

    # ==================== 使用统计 ====================

    def get_usage_stats(
        self,
        api_key_id: str,
        start_date: str = None,
        end_date: str = None,
    ) -> Dict[str, Any]:
        """获取 API 使用统计"""
        query = self.db.query(APIUsageLogDB).filter(
            APIUsageLogDB.api_key_id == api_key_id
        )

        if start_date:
            query = query.filter(APIUsageLogDB.created_at >= start_date)
        if end_date:
            query = query.filter(APIUsageLogDB.created_at <= end_date)

        logs = query.all()

        # 按端点统计
        endpoint_stats = {}
        for log in logs:
            if log.endpoint not in endpoint_stats:
                endpoint_stats[log.endpoint] = {"count": 0, "total_time": 0}
            endpoint_stats[log.endpoint]["count"] += 1
            if log.response_time_ms:
                endpoint_stats[log.endpoint]["total_time"] += log.response_time_ms

        # 计算平均响应时间
        for endpoint in endpoint_stats:
            count = endpoint_stats[endpoint]["count"]
            total_time = endpoint_stats[endpoint]["total_time"]
            endpoint_stats[endpoint]["avg_response_time_ms"] = total_time / count if count > 0 else 0

        return {
            "api_key_id": api_key_id,
            "total_requests": len(logs),
            "period": {
                "start": start_date or "all",
                "end": end_date or "today",
            },
            "endpoint_stats": endpoint_stats,
        }


# 全局单例
_api_key_service_instances = {}


def get_api_key_service(db: Session) -> APIKeyService:
    """获取 API 密钥服务实例"""
    return APIKeyService(db)
