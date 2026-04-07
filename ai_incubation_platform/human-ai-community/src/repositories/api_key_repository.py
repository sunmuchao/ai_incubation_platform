"""
API Key Repository
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from repositories.base import BaseRepository
from db.models import DBAPIKey, DBAPIKeyUsage, DBAPIRequestLog


class APIKeyRepository(BaseRepository):
    """API Key Repository"""

    def __init__(self, db: AsyncSession):
        super().__init__(DBAPIKey, db)

    async def get_by_key(self, key: str) -> Optional[DBAPIKey]:
        """根据密钥值获取 API Key"""
        result = await self.db.execute(select(DBAPIKey).where(DBAPIKey.key == key))
        return result.scalar_one_or_none()

    async def get_by_owner(self, owner_id: str, owner_type: str = "member") -> List[DBAPIKey]:
        """根据所有者获取 API Key 列表"""
        result = await self.db.execute(
            select(DBAPIKey)
            .where(DBAPIKey.owner_id == owner_id)
            .where(DBAPIKey.owner_type == owner_type)
            .order_by(DBAPIKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_active_keys(self, limit: int = 100) -> List[DBAPIKey]:
        """获取激活状态的 API Key 列表"""
        result = await self.db.execute(
            select(DBAPIKey)
            .where(DBAPIKey.status == "active")
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_last_used(self, id: str) -> Optional[DBAPIKey]:
        """更新最后使用时间"""
        instance = await self.get(id)
        if instance:
            instance.last_used_at = datetime.now()
            instance.total_requests += 1
            today = datetime.now().date()
            # 如果是新的一天，重置今日计数
            if instance.today_requests == 0 or instance.updated_at.date() != today:
                instance.today_requests = 1
            else:
                instance.today_requests += 1
            await self.db.flush()
            await self.db.refresh(instance)
        return instance

    async def increment_usage(self, id: str) -> Optional[DBAPIKey]:
        """增加使用计数"""
        instance = await self.get(id)
        if instance:
            instance.total_requests += 1
            today = datetime.now().date()
            if instance.updated_at and instance.updated_at.date() == today:
                instance.today_requests += 1
            else:
                instance.today_requests = 1
            await self.db.flush()
            await self.db.refresh(instance)
        return instance

    async def revoke(self, id: str) -> Optional[DBAPIKey]:
        """撤销 API Key"""
        return await self.update(id, {"status": "revoked"})

    async def activate(self, id: str) -> Optional[DBAPIKey]:
        """激活 API Key"""
        return await self.update(id, {"status": "active"})

    async def get_usage_stats(
        self,
        api_key_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """获取使用统计"""
        start_date = datetime.now() - timedelta(days=days)

        # 获取请求日志
        result = await self.db.execute(
            select(DBAPIRequestLog)
            .where(DBAPIRequestLog.api_key_id == api_key_id)
            .where(DBAPIRequestLog.created_at >= start_date)
        )
        logs = list(result.scalars().all())

        if not logs:
            return {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "rate_limited_requests": 0,
                "avg_response_time_ms": 0,
                "requests_by_status": {},
                "requests_by_endpoint": {},
            }

        total = len(logs)
        successful = sum(1 for log in logs if 200 <= log.status_code < 300)
        failed = total - successful
        rate_limited = sum(1 for log in logs if log.is_rate_limited)
        avg_response_time = sum(log.response_time_ms for log in logs) / total

        # 按状态码统计
        status_counts = {}
        for log in logs:
            status_str = str(log.status_code)
            status_counts[status_str] = status_counts.get(status_str, 0) + 1

        # 按端点统计
        endpoint_counts = {}
        for log in logs:
            endpoint = log.endpoint or log.path
            endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1

        return {
            "total_requests": total,
            "successful_requests": successful,
            "failed_requests": failed,
            "rate_limited_requests": rate_limited,
            "avg_response_time_ms": round(avg_response_time, 2),
            "requests_by_status": status_counts,
            "requests_by_endpoint": endpoint_counts,
        }


class APIKeyUsageRepository(BaseRepository):
    """API Key 使用统计 Repository"""

    def __init__(self, db: AsyncSession):
        super().__init__(DBAPIKeyUsage, db)

    async def get_daily_usage(
        self,
        api_key_id: str,
        date: datetime
    ) -> Optional[DBAPIKeyUsage]:
        """获取指定日期的使用统计"""
        start_of_day = datetime(date.year, date.month, date.day, 0, 0, 0)
        end_of_day = datetime(date.year, date.month, date.day, 23, 59, 59)

        result = await self.db.execute(
            select(DBAPIKeyUsage)
            .where(DBAPIKeyUsage.api_key_id == api_key_id)
            .where(DBAPIKeyUsage.period == "day")
            .where(DBAPIKeyUsage.period_start >= start_of_day)
            .where(DBAPIKeyUsage.period_end <= end_of_day)
        )
        return result.scalar_one_or_none()

    async def create_or_update_daily(
        self,
        api_key_id: str,
        usage_data: Dict[str, Any]
    ) -> DBAPIKeyUsage:
        """创建或更新每日使用统计"""
        today = datetime.now()
        start_of_day = datetime(today.year, today.month, today.day, 0, 0, 0)
        end_of_day = datetime(today.year, today.month, today.day, 23, 59, 59)

        existing = await self.get_daily_usage(api_key_id, today)

        if existing:
            # 更新现有记录
            existing.total_requests += usage_data.get("total_requests", 0)
            existing.successful_requests += usage_data.get("successful_requests", 0)
            existing.failed_requests += usage_data.get("failed_requests", 0)
            existing.rate_limited_requests += usage_data.get("rate_limited_requests", 0)
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        else:
            # 创建新记录
            new_usage = DBAPIKeyUsage(
                api_key_id=api_key_id,
                period="day",
                period_start=start_of_day,
                period_end=end_of_day,
                total_requests=usage_data.get("total_requests", 0),
                successful_requests=usage_data.get("successful_requests", 0),
                failed_requests=usage_data.get("failed_requests", 0),
                rate_limited_requests=usage_data.get("rate_limited_requests", 0),
                avg_response_time_ms=usage_data.get("avg_response_time_ms", 0),
                peak_requests_per_second=usage_data.get("peak_requests_per_second", 0),
                requests_by_endpoint=usage_data.get("requests_by_endpoint", {}),
                requests_by_status=usage_data.get("requests_by_status", {}),
            )
            self.db.add(new_usage)
            await self.db.flush()
            await self.db.refresh(new_usage)
            return new_usage


class APIRequestLogRepository(BaseRepository):
    """API 请求日志 Repository"""

    def __init__(self, db: AsyncSession):
        super().__init__(DBAPIRequestLog, db)

    async def create_log(self, log_data: Dict[str, Any]) -> DBAPIRequestLog:
        """创建请求日志"""
        log = DBAPIRequestLog(**log_data)
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)
        return log

    async def get_logs_by_key(
        self,
        api_key_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[DBAPIRequestLog]:
        """根据 API Key 获取请求日志"""
        result = await self.db.execute(
            select(DBAPIRequestLog)
            .where(DBAPIRequestLog.api_key_id == api_key_id)
            .order_by(DBAPIRequestLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_logs_by_date_range(
        self,
        api_key_id: str,
        start_date: datetime,
        end_date: datetime,
        limit: int = 1000
    ) -> List[DBAPIRequestLog]:
        """根据日期范围获取请求日志"""
        result = await self.db.execute(
            select(DBAPIRequestLog)
            .where(DBAPIRequestLog.api_key_id == api_key_id)
            .where(DBAPIRequestLog.created_at >= start_date)
            .where(DBAPIRequestLog.created_at <= end_date)
            .order_by(DBAPIRequestLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def cleanup_old_logs(self, days: int = 30) -> int:
        """清理旧的请求日志"""
        cutoff_date = datetime.now() - timedelta(days=days)
        result = await self.db.execute(
            select(func.count())
            .select_from(DBAPIRequestLog)
            .where(DBAPIRequestLog.created_at < cutoff_date)
        )
        count = result.scalar()

        await self.db.execute(
            DBAPIRequestLog.__table__.delete()
            .where(DBAPIRequestLog.created_at < cutoff_date)
        )
        return count or 0
