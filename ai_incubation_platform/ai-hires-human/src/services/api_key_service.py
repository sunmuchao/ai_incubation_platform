"""
API 密钥管理服务。
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.api_key import APIKeyDB, DeveloperProfileDB, APIUsageLogDB, OAuthApplicationDB, OAuthAccessTokenDB


def generate_api_key() -> str:
    """生成一个新的 API 密钥。"""
    return f"sk_live_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """对 API 密钥进行哈希处理。"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def get_key_prefix(api_key: str) -> str:
    """获取 API 密钥前缀（用于标识）。"""
    # 返回前 8 个字符作为前缀
    return api_key[:8]


class APIKeyService:
    """API 密钥管理服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_api_key(
        self,
        owner_id: str,
        name: str,
        owner_type: str = "developer",
        description: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        rate_limit: int = 1000,
        rate_limit_daily: int = 10000,
        expires_in_days: Optional[int] = None,
    ) -> APIKeyDB:
        """创建新的 API 密钥。"""
        import uuid

        # 生成密钥
        api_key = generate_api_key()
        key_hash = hash_api_key(api_key)
        key_prefix = get_key_prefix(api_key)

        # 计算过期时间
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now() + timedelta(days=expires_in_days)

        # 创建数据库记录
        api_key_db = APIKeyDB(
            key_id=str(uuid.uuid4()),
            key_hash=key_hash,
            key_prefix=key_prefix,
            owner_id=owner_id,
            owner_type=owner_type,
            name=name,
            description=description,
            scopes=scopes or ["tasks:read", "tasks:write", "workers:read"],
            rate_limit=rate_limit,
            rate_limit_daily=rate_limit_daily,
            expires_at=expires_at,
        )

        self.db.add(api_key_db)
        await self.db.commit()
        await self.db.refresh(api_key_db)

        # 返回密钥（仅在创建时返回一次）
        api_key_db._plain_key = api_key  # 临时属性，仅供创建时返回
        return api_key_db

    async def get_api_key_by_hash(self, key_hash: str) -> Optional[APIKeyDB]:
        """通过哈希值获取 API 密钥。"""
        result = await self.db.execute(
            select(APIKeyDB).where(APIKeyDB.key_hash == key_hash)
        )
        return result.scalar_one_or_none()

    async def get_api_key_by_id(self, key_id: str) -> Optional[APIKeyDB]:
        """通过 ID 获取 API 密钥。"""
        result = await self.db.execute(
            select(APIKeyDB).where(APIKeyDB.key_id == key_id)
        )
        return result.scalar_one_or_none()

    async def list_api_keys(self, owner_id: str, include_inactive: bool = False) -> List[APIKeyDB]:
        """列出用户的所有 API 密钥。"""
        query = select(APIKeyDB).where(APIKeyDB.owner_id == owner_id)
        if not include_inactive:
            query = query.where(APIKeyDB.is_active == True).where(APIKeyDB.is_revoked == False)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def revoke_api_key(self, key_id: str, reason: str) -> bool:
        """吊销 API 密钥。"""
        api_key = await self.get_api_key_by_id(key_id)
        if not api_key:
            return False

        api_key.is_revoked = True
        api_key.is_active = False
        api_key.revoked_reason = reason
        await self.db.commit()
        return True

    async def update_last_used(self, key_id: str) -> None:
        """更新密钥最后使用时间。"""
        api_key = await self.get_api_key_by_id(key_id)
        if api_key:
            api_key.last_used_at = datetime.now()
            api_key.usage_count += 1
            await self.db.commit()

    async def check_rate_limit(self, key_id: str) -> Dict:
        """检查速率限制。"""
        api_key = await self.get_api_key_by_id(key_id)
        if not api_key:
            return {"allowed": False, "reason": "Invalid API key"}

        if not api_key.is_active or api_key.is_revoked:
            return {"allowed": False, "reason": "API key is revoked or inactive"}

        if api_key.expires_at and datetime.now() > api_key.expires_at:
            return {"allowed": False, "reason": "API key has expired"}

        # 检查每日限额
        today = datetime.now().strftime("%Y-%m-%d")
        if api_key.last_reset_date != today:
            api_key.daily_usage_count = 0
            api_key.last_reset_date = today

        if api_key.daily_usage_count >= api_key.rate_limit_daily:
            return {"allowed": False, "reason": "Daily rate limit exceeded"}

        return {"allowed": True, "rate_limit": api_key.rate_limit}

    async def increment_usage(self, key_id: str) -> None:
        """增加使用计数。"""
        api_key = await self.get_api_key_by_id(key_id)
        if api_key:
            api_key.daily_usage_count += 1
            await self.db.commit()


class DeveloperService:
    """开发者档案管理服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_developer(
        self,
        developer_id: str,
        name: str,
        email: str,
        developer_type: str = "individual",
    ) -> DeveloperProfileDB:
        """获取或创建开发者档案。"""
        result = await self.db.execute(
            select(DeveloperProfileDB).where(DeveloperProfileDB.developer_id == developer_id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            profile = DeveloperProfileDB(
                developer_id=developer_id,
                name=name,
                email=email,
                developer_type=developer_type,
            )
            self.db.add(profile)
            await self.db.commit()
            await self.db.refresh(profile)

        return profile

    async def update_developer(
        self,
        developer_id: str,
        **kwargs,
    ) -> DeveloperProfileDB:
        """更新开发者档案。"""
        profile = await self.get_or_create_developer(developer_id, "", "")
        for key, value in kwargs.items():
            if hasattr(profile, key) and value is not None:
                setattr(profile, key, value)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def get_developer(self, developer_id: str) -> Optional[DeveloperProfileDB]:
        """获取开发者档案。"""
        result = await self.db.execute(
            select(DeveloperProfileDB).where(DeveloperProfileDB.developer_id == developer_id)
        )
        return result.scalar_one_or_none()


class APIUsageService:
    """API 使用日志服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_request(
        self,
        api_key_id: str,
        endpoint: str,
        method: str,
        request_params: Optional[Dict] = None,
        request_body: Optional[Dict] = None,
        response_status: int = 200,
        response_size: int = 0,
        latency_ms: int = 0,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> APIUsageLogDB:
        """记录 API 请求日志。"""
        import uuid

        log = APIUsageLogDB(
            log_id=str(uuid.uuid4()),
            api_key_id=api_key_id,
            endpoint=endpoint,
            method=method,
            request_params=request_params,
            request_body=request_body,
            response_status=response_status,
            response_size=response_size,
            latency_ms=latency_ms,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        self.db.add(log)
        await self.db.commit()
        return log

    async def get_usage_stats(
        self,
        api_key_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict:
        """获取使用统计。"""
        query = select(APIUsageLogDB).where(
            and_(
                APIUsageLogDB.api_key_id == api_key_id,
                APIUsageLogDB.created_at >= start_date,
                APIUsageLogDB.created_at <= end_date,
            )
        )
        result = await self.db.execute(query)
        logs = list(result.scalars().all())

        total_requests = len(logs)
        successful_requests = sum(1 for log in logs if 200 <= log.response_status < 300)
        failed_requests = total_requests - successful_requests
        avg_latency = sum(log.latency_ms for log in logs) / total_requests if total_requests > 0 else 0

        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": successful_requests / total_requests if total_requests > 0 else 0,
            "avg_latency_ms": avg_latency,
        }
