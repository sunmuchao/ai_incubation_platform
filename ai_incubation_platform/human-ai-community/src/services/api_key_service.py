"""
API Key 管理服务

提供 API Key 的创建、验证、速率限制等功能
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
import uuid

from models.api_key import (
    APIKey, APIKeyCreate, APIKeyUpdate, APIKeyUsage,
    APIKeyType, APIKeyStatus, APIKeyTier
)
from repositories.api_key_repository import (
    APIKeyRepository, APIKeyUsageRepository, APIRequestLogRepository
)
from db.manager import db_manager
from core.config import settings

logger = logging.getLogger(__name__)


# 各等级的默认速率限制配置
TIER_LIMITS = {
    APIKeyTier.FREE: {
        "rate_limit": 10,        # 每秒 10 次请求
        "daily_limit": 10000,    # 每日 1 万次
        "scopes": ["read"],      # 只读权限
    },
    APIKeyTier.BASIC: {
        "rate_limit": 50,        # 每秒 50 次请求
        "daily_limit": 100000,   # 每日 10 万次
        "scopes": ["read", "write"],
    },
    APIKeyTier.PRO: {
        "rate_limit": 200,       # 每秒 200 次请求
        "daily_limit": 1000000,  # 每日 100 万次
        "scopes": ["read", "write", "admin"],
    },
    APIKeyTier.ENTERPRISE: {
        "rate_limit": 1000,      # 每秒 1000 次请求
        "daily_limit": 10000000, # 每日 1000 万次
        "scopes": ["*"],         # 所有权限
    },
}


class APIKeyService:
    """API Key 管理服务"""

    def __init__(self):
        self._api_key_repo: Optional[APIKeyRepository] = None
        self._usage_repo: Optional[APIKeyUsageRepository] = None
        self._log_repo: Optional[APIRequestLogRepository] = None

    def _get_repo(self, db):
        """获取 repository 实例"""
        if self._api_key_repo is None:
            self._api_key_repo = APIKeyRepository(db)
        if self._usage_repo is None:
            self._usage_repo = APIKeyUsageRepository(db)
        if self._log_repo is None:
            self._log_repo = APIRequestLogRepository(db)
        return self._api_key_repo, self._usage_repo, self._log_repo

    async def create_api_key(
        self,
        request: APIKeyCreate,
        owner_id: str,
        owner_type: str = "member"
    ) -> APIKey:
        """创建新的 API Key"""
        async for db in db_manager.get_session():
            repo, _, _ = self._get_repo(db)

            # 确定速率限制
            tier_limits = TIER_LIMITS.get(request.tier, TIER_LIMITS[APIKeyTier.FREE])

            api_key_data = {
                "name": request.name,
                "owner_id": owner_id,
                "owner_type": owner_type,
                "key_type": request.key_type.value,
                "tier": request.tier.value,
                "rate_limit": request.tier.value in TIER_LIMITS and TIER_LIMITS[request.tier]["rate_limit"] or tier_limits["rate_limit"],
                "daily_limit": request.tier.value in TIER_LIMITS and TIER_LIMITS[request.tier]["daily_limit"] or tier_limits["daily_limit"],
                "status": APIKeyStatus.ACTIVE.value,
                "scopes": request.scopes or tier_limits["scopes"],
                "ip_whitelist": request.ip_whitelist,
                "expires_at": request.expires_at,
                "description": request.description,
                "metadata": request.metadata,
            }

            db_api_key = await repo.create(api_key_data)
            await db.commit()

            logger.info(f"创建新的 API Key: {db_api_key.id} ({db_api_key.name})")

            return self._to_domain_model(db_api_key)

    async def get_api_key(self, api_key_id: str) -> Optional[APIKey]:
        """根据 ID 获取 API Key"""
        async for db in db_manager.get_session():
            repo, _, _ = self._get_repo(db)
            db_api_key = await repo.get(api_key_id)
            if db_api_key:
                return self._to_domain_model(db_api_key)
            return None

    async def get_api_key_by_key(self, key: str) -> Optional[APIKey]:
        """根据密钥值获取 API Key"""
        async for db in db_manager.get_session():
            repo, _, _ = self._get_repo(db)
            db_api_key = await repo.get_by_key(key)
            if db_api_key:
                return self._to_domain_model(db_api_key)
            return None

    async def list_api_keys(
        self,
        owner_id: Optional[str] = None,
        status: Optional[APIKeyStatus] = None,
        limit: int = 100
    ) -> List[APIKey]:
        """获取 API Key 列表"""
        async for db in db_manager.get_session():
            repo, _, _ = self._get_repo(db)

            if owner_id:
                db_keys = await repo.get_by_owner(owner_id)
            elif status:
                db_keys = await repo.list_by_filter({"status": status.value}, limit)
            else:
                db_keys = await repo.get_active_keys(limit)

            return [self._to_domain_model(key) for key in db_keys]

    async def update_api_key(
        self,
        api_key_id: str,
        request: APIKeyUpdate
    ) -> Optional[APIKey]:
        """更新 API Key"""
        async for db in db_manager.get_session():
            repo, _, _ = self._get_repo(db)

            update_data = {}
            if request.name is not None:
                update_data["name"] = request.name
            if request.status is not None:
                update_data["status"] = request.status.value
            if request.rate_limit is not None:
                update_data["rate_limit"] = request.rate_limit
            if request.daily_limit is not None:
                update_data["daily_limit"] = request.daily_limit
            if request.scopes is not None:
                update_data["scopes"] = request.scopes
            if request.description is not None:
                update_data["description"] = request.description
            if request.metadata is not None:
                update_data["metadata"] = request.metadata

            if not update_data:
                return await self.get_api_key(api_key_id)

            db_api_key = await repo.update(api_key_id, update_data)
            await db.commit()

            if db_api_key:
                logger.info(f"更新 API Key: {api_key_id}")
                return self._to_domain_model(db_api_key)
            return None

    async def revoke_api_key(self, api_key_id: str) -> bool:
        """撤销 API Key"""
        async for db in db_manager.get_session():
            repo, _, _ = self._get_repo(db)
            result = await repo.revoke(api_key_id)
            await db.commit()

            if result:
                logger.info(f"撤销 API Key: {api_key_id}")
                return True
            return False

    async def validate_api_key(self, key: str) -> Tuple[bool, Optional[APIKey], str]:
        """
        验证 API Key

        Returns:
            (是否有效，API Key 对象，错误消息)
        """
        api_key = await self.get_api_key_by_key(key)

        if not api_key:
            return False, None, "Invalid API key"

        if api_key.status != APIKeyStatus.ACTIVE:
            return False, api_key, f"API key is {api_key.status.value}"

        if api_key.is_expired():
            return False, api_key, "API key has expired"

        return True, api_key, ""

    async def check_rate_limit(self, api_key: APIKey) -> Tuple[bool, Dict[str, Any]]:
        """
        检查速率限制

        Returns:
            (是否超过限制，限流信息)
        """
        # 检查今日请求数是否超过每日限制
        if api_key.today_requests >= api_key.daily_limit:
            return False, {
                "limited": True,
                "reason": "daily_limit_exceeded",
                "retry_after": 3600,  # 1 小时后重试
            }

        # 使用简单的令牌桶算法检查秒级速率限制
        # 实际生产环境建议使用 Redis
        now = datetime.now()
        time_since_last_update = (now - api_key.updated_at).total_seconds() if api_key.updated_at else float('inf')

        # 如果距离上次请求超过 1 秒，重置计数
        if time_since_last_update >= 1.0:
            return True, {
                "limited": False,
                "remaining": api_key.rate_limit,
                "reset": 1,
            }

        # 简单的每秒请求数检查
        if api_key.today_requests % api_key.rate_limit == 0 and time_since_last_update < 0.1:
            return False, {
                "limited": True,
                "reason": "rate_limit_exceeded",
                "retry_after": 1,
            }

        return True, {
            "limited": False,
            "remaining": max(0, api_key.rate_limit - (api_key.today_requests % api_key.rate_limit)),
            "reset": 1,
        }

    async def log_request(
        self,
        api_key_id: str,
        request_id: str,
        method: str,
        path: str,
        endpoint: str,
        status_code: int,
        response_time_ms: float,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        is_rate_limited: bool = False,
        rate_limit_remaining: Optional[int] = None
    ):
        """记录 API 请求日志"""
        async for db in db_manager.get_session():
            _, _, log_repo = self._get_repo(db)

            log_data = {
                "api_key_id": api_key_id,
                "request_id": request_id,
                "method": method,
                "path": path,
                "endpoint": endpoint,
                "status_code": status_code,
                "response_time_ms": response_time_ms,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "is_rate_limited": is_rate_limited,
                "rate_limit_remaining": rate_limit_remaining,
            }

            await log_repo.create_log(log_data)

            # 更新 API Key 使用计数
            await log_repo.db.execute(
                log_repo.db.model.__table__.update()
                .where(log_repo.db.model.id == api_key_id)
                .values(total_requests=log_repo.db.model.total_requests + 1)
            )

            await db.commit()

    async def get_usage_stats(
        self,
        api_key_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """获取使用统计"""
        async for db in db_manager.get_session():
            repo, _, _ = self._get_repo(db)
            return await repo.get_usage_stats(api_key_id, days)

    def _to_domain_model(self, db_api_key) -> APIKey:
        """将数据库模型转换为领域模型"""
        key_type = APIKeyType(db_api_key.key_type)
        tier = APIKeyTier(db_api_key.tier)
        status = APIKeyStatus(db_api_key.status)

        return APIKey(
            id=db_api_key.id,
            name=db_api_key.name,
            key=db_api_key.key,
            owner_id=db_api_key.owner_id,
            owner_type=db_api_key.owner_type,
            key_type=key_type,
            tier=tier,
            rate_limit=db_api_key.rate_limit,
            daily_limit=db_api_key.daily_limit,
            status=status,
            scopes=db_api_key.scopes or [],
            ip_whitelist=db_api_key.ip_whitelist,
            expires_at=db_api_key.expires_at,
            last_used_at=db_api_key.last_used_at,
            created_at=db_api_key.created_at,
            updated_at=db_api_key.updated_at,
            total_requests=db_api_key.total_requests,
            today_requests=db_api_key.today_requests,
            description=db_api_key.description,
            metadata=db_api_key.metadata or {},
        )


# 全局服务实例
api_key_service = APIKeyService()
