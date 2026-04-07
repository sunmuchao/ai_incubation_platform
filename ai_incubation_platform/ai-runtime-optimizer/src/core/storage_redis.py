"""
Redis 存储层：分析结果与状态持久化
生产环境使用 Redis 实现数据持久化和多实例共享
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
import json
import redis
from redis import Redis

from models.analysis import AnalysisResult, CodeProposalsResult


class RedisStorage:
    """Redis 存储实现"""

    def __init__(self, redis_url: str = "redis://localhost:6379/0",
                 max_records_per_service: int = 100):
        """初始化 Redis 连接

        Args:
            redis_url: Redis 连接 URL
            max_records_per_service: 每个服务最多保留的记录数
        """
        self.redis: Redis = redis.from_url(redis_url)
        self._max_records_per_service = max_records_per_service
        self._prefix = "ai-optimizer"

    def _get_key(self, service_name: str, data_type: str) -> str:
        """生成 Redis key"""
        return f"{self._prefix}:{data_type}:{service_name}"

    def _serialize(self, obj: Any) -> str:
        """序列化对象为 JSON"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {k: self._serialize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._serialize(v) for v in obj]
        if hasattr(obj, 'model_dump'):
            return self._serialize(obj.model_dump())
        return obj

    def _deserialize_datetime(self, value: Any) -> Any:
        """反序列化 datetime 字段"""
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                pass
        return value

    def record_metrics(self, service_name: str, metrics: Dict[str, Any]) -> None:
        """记录指标快照"""
        key = self._get_key(service_name, "metrics")
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "data": metrics
        }
        self.redis.rpush(key, json.dumps(self._serialize(record)))
        # 保留最新的 N 条记录
        self.redis.ltrim(key, -self._max_records_per_service, -1)

    def record_usage(self, service_name: str, usage: Dict[str, Any]) -> None:
        """记录使用情况"""
        key = self._get_key(service_name, "usage")
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "data": usage
        }
        self.redis.rpush(key, json.dumps(self._serialize(record)))
        # 保留最新的 N 条记录
        self.redis.ltrim(key, -self._max_records_per_service, -1)

    def save_analysis_result(self, result: AnalysisResult) -> None:
        """保存分析结果"""
        key = self._get_key(result.service, "analysis")
        record = self._serialize(result)
        self.redis.rpush(key, json.dumps(record))
        # 保留最新的 N 条记录
        self.redis.ltrim(key, -self._max_records_per_service, -1)

        # 保存最新分析结果的引用（用于快速查询）
        latest_key = f"{self._prefix}:latest:analysis:{result.service}"
        if result.usage_informed:
            # 综合分析结果保存到单独的 key
            holistic_key = f"{self._prefix}:latest:holistic:{result.service}"
            self.redis.set(holistic_key, json.dumps(record))

    def save_code_proposals(self, result: CodeProposalsResult) -> None:
        """保存代码提案结果"""
        key = self._get_key(result.service, "proposals")
        record = self._serialize(result)
        self.redis.rpush(key, json.dumps(record))
        # 保留最新的 N 条记录
        self.redis.ltrim(key, -self._max_records_per_service, -1)

    def get_last_metrics(self, service_name: str) -> Optional[Dict[str, Any]]:
        """获取服务最新的指标"""
        key = self._get_key(service_name, "metrics")
        last_record = self.redis.lindex(key, -1)
        if last_record:
            record = json.loads(last_record)
            return record.get("data")
        return None

    def get_last_usage(self, service_name: str) -> Optional[Dict[str, Any]]:
        """获取服务最新的使用情况"""
        key = self._get_key(service_name, "usage")
        last_record = self.redis.lindex(key, -1)
        if last_record:
            record = json.loads(last_record)
            return record.get("data")
        return None

    def get_last_analysis(self, service_name: Optional[str] = None) -> Optional[AnalysisResult]:
        """获取最新的分析结果"""
        if service_name:
            key = self._get_key(service_name, "analysis")
            last_record = self.redis.lindex(key, -1)
            if last_record:
                record = json.loads(last_record)
                return AnalysisResult(**record)
        else:
            # 获取所有服务中最新的分析结果
            keys = self.redis.keys(f"{self._prefix}:analysis:*")
            latest_result = None
            latest_time = None
            for key in keys:
                last_record = self.redis.lindex(key, -1)
                if last_record:
                    record = json.loads(last_record)
                    created_at = record.get("created_at")
                    if created_at and (latest_time is None or created_at > latest_time):
                        latest_time = created_at
                        latest_result = AnalysisResult(**record)
            return latest_result
        return None

    def get_last_holistic(self, service_name: Optional[str] = None) -> Optional[AnalysisResult]:
        """获取最新的综合分析结果"""
        if service_name:
            key = f"{self._prefix}:latest:holistic:{service_name}"
            record_json = self.redis.get(key)
            if record_json:
                record = json.loads(record_json)
                return AnalysisResult(**record)
        else:
            # 获取所有服务中最新的综合分析结果
            keys = self.redis.keys(f"{self._prefix}:latest:holistic:*")
            latest_result = None
            latest_time = None
            for key in keys:
                record_json = self.redis.get(key)
                if record_json:
                    record = json.loads(record_json)
                    created_at = record.get("created_at")
                    if created_at and (latest_time is None or created_at > latest_time):
                        latest_time = created_at
                        latest_result = AnalysisResult(**record)
            return latest_result
        return None

    def get_latest_recommendations(self, service_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取最新的建议列表"""
        # 优先返回综合分析结果
        result = self.get_last_holistic(service_name)
        if not result:
            result = self.get_last_analysis(service_name)

        if not result:
            return []

        return [
            {
                "id": s.id,
                "strategy_id": s.strategy_id,
                "type": s.type,
                "action": s.action,
                "confidence": s.confidence,
                "priority": s.priority,
                "evidence": s.evidence,
                "tags": s.tags,
                "created_at": s.created_at.isoformat() if isinstance(s.created_at, datetime) else s.created_at
            }
            for s in result.suggestions
        ]

    def get_analysis_history(self, service_name: str, limit: int = 20) -> List[AnalysisResult]:
        """获取服务的分析历史"""
        key = self._get_key(service_name, "analysis")
        records = self.redis.lrange(key, -limit, -1)
        results = []
        for record_json in reversed(records):
            record = json.loads(record_json)
            results.append(AnalysisResult(**record))
        return results

    def get_proposal_history(self, service_name: str, limit: int = 20) -> List[CodeProposalsResult]:
        """获取服务的代码提案历史"""
        key = self._get_key(service_name, "proposals")
        records = self.redis.lrange(key, -limit, -1)
        results = []
        for record_json in reversed(records):
            record = json.loads(record_json)
            results.append(CodeProposalsResult(**record))
        return results

    def get_all_services(self) -> List[str]:
        """获取所有有记录的服务名"""
        services = set()
        keys = self.redis.keys(f"{self._prefix}:*")
        for key in keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            parts = key_str.split(":")
            if len(parts) >= 3:
                service_name = parts[2]
                if service_name not in ("latest",):
                    services.add(service_name)
        return sorted(list(services))

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            self.redis.ping()
            info = self.redis.info("server")
            return {
                "status": "healthy",
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
            }
        except Exception as e:
            error_type = type(e).__name__
            return {
                "status": "unhealthy",
                "error": f"Redis connection failed ({error_type}): {str(e)}"
            }

    def close(self):
        """关闭 Redis 连接"""
        self.redis.close()


# 全局存储实例（延迟初始化）
_storage_instance: Optional[RedisStorage] = None


def get_redis_storage(redis_url: Optional[str] = None,
                      max_records: int = 100) -> RedisStorage:
    """获取或创建 Redis 存储实例"""
    global _storage_instance
    if _storage_instance is None:
        url = redis_url or "redis://localhost:6379/0"
        _storage_instance = RedisStorage(url, max_records)
    return _storage_instance
