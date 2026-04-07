"""
Redis 连接器 - 异步
"""
import asyncio
import json
from typing import Any, Dict, List, Optional
from connectors.base import BaseConnector, ConnectorConfig, ConnectorError


class RedisConnector(BaseConnector):
    """Redis 数据库连接器（使用 redis.asyncio）"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._redis = None

    async def connect(self) -> None:
        """建立 Redis 连接"""
        try:
            import redis.asyncio as redis
            self._redis = redis.from_url(
                self.config.connection_string,
                socket_timeout=self.config.timeout,
                socket_connect_timeout=self.config.timeout,
                decode_responses=True
            )
            # 测试连接
            await self._redis.ping()
            self._connected = True
        except Exception as e:
            raise ConnectorError(f"Failed to connect to Redis: {e}")

    async def disconnect(self) -> None:
        """断开 Redis 连接"""
        if self._redis:
            await self._redis.close()
        self._connected = False

    async def execute(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """
        执行 Redis 命令
        支持简化的查询语法:
        - "GET key" - 获取字符串值
        - "SET key value" - 设置字符串值
        - "HGETALL key" - 获取哈希所有字段
        - "HSET key field value" - 设置哈希字段
        - "LPUSH key value1 value2 ..." - 列表左推
        - "RPUSH key value1 value2 ..." - 列表右推
        - "LRANGE key start end" - 获取列表范围
        - "SADD key member1 member2 ..." - 集合添加
        - "SMEMBERS key" - 获取集合所有成员
        - "ZADD key score1 member1 score2 member2 ..." - 有序集合添加
        - "ZRANGE key start end WITHSCORES" - 获取有序集合范围
        - "DEL key" - 删除键
        - "EXISTS key" - 检查键是否存在
        - "TTL key" - 获取键剩余 TTL
        - "KEYS pattern" - 匹配键名
        """
        if not self._connected:
            raise ConnectorError("Not connected to database")

        try:
            parts = query.split()
            if not parts:
                raise ConnectorError("Empty query")

            command = parts[0].upper()
            args = parts[1:] if len(parts) > 1 else []

            result = await self._redis.execute_command(command, *args)

            # 格式化结果
            return self._format_result(command, result)

        except Exception as e:
            raise ConnectorError(f"Command execution failed: {e}")

    def _format_result(self, command: str, result: Any) -> List[Dict[str, Any]]:
        """格式化命令结果"""
        if result is None:
            return [{"result": None}]

        if isinstance(result, bool):
            return [{"result": result}]

        if isinstance(result, int):
            return [{"result": result}]

        if isinstance(result, str):
            return [{"result": result}]

        if isinstance(result, list):
            # 处理 WITHSCORES 选项
            if len(result) > 0 and isinstance(result[0], tuple):
                return [dict(item) for item in result]
            return [{"result": item} for item in result]

        if isinstance(result, dict):
            return [{"result": result}]

        return [{"result": str(result)}]

    async def get_schema(self) -> Dict[str, Any]:
        """获取 Redis 数据结构"""
        if not self._connected:
            raise ConnectorError("Not connected to database")

        # 获取所有键
        keys = await self._redis.keys("*")

        schema = {}
        for key in keys[:100]:  # 限制最多 100 个键
            key_type = await self._redis.type(key)

            key_info = {
                "key": key,
                "type": key_type,
                "ttl": await self._redis.ttl(key)
            }

            # 获取示例值
            try:
                if key_type == "string":
                    value = await self._redis.get(key)
                    key_info["sample_value"] = value[:100] if value else None
                elif key_type == "hash":
                    value = await self._redis.hgetall(key)
                    key_info["sample_value"] = dict(list(value.items())[:5])
                elif key_type == "list":
                    value = await self._redis.lrange(key, 0, 4)
                    key_info["sample_value"] = value
                elif key_type == "set":
                    value = await self._redis.smembers(key)
                    key_info["sample_value"] = list(value)[:5]
                elif key_type == "zset":
                    value = await self._redis.zrange(key, 0, 4, withscores=True)
                    key_info["sample_value"] = value
            except Exception:
                key_info["sample_value"] = None

            schema[key] = key_info

        return {"keys": schema, "total_keys": len(keys)}

    # 便捷方法

    async def get(self, key: str) -> Optional[str]:
        """获取字符串值"""
        return await self._redis.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """设置字符串值"""
        return await self._redis.set(key, value, ex=ex)

    async def hgetall(self, key: str) -> Dict[str, str]:
        """获取哈希所有字段"""
        return await self._redis.hgetall(key)

    async def hset(self, key: str, field: str, value: str) -> int:
        """设置哈希字段"""
        return await self._redis.hset(key, field, value)

    async def lpush(self, key: str, *values: str) -> int:
        """列表左推"""
        return await self._redis.lpush(key, *values)

    async def rpush(self, key: str, *values: str) -> int:
        """列表右推"""
        return await self._redis.rpush(key, *values)

    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        """获取列表范围"""
        return await self._redis.lrange(key, start, end)

    async def sadd(self, key: str, *members: str) -> int:
        """集合添加"""
        return await self._redis.sadd(key, *members)

    async def smembers(self, key: str) -> set:
        """获取集合所有成员"""
        return await self._redis.smembers(key)

    async def zadd(self, key: str, mapping: Dict[str, float]) -> int:
        """有序集合添加"""
        return await self._redis.zadd(key, mapping)

    async def zrange(self, key: str, start: int, end: int, withscores: bool = False) -> List:
        """获取有序集合范围"""
        return await self._redis.zrange(key, start, end, withscores=withscores)

    async def publish(self, channel: str, message: str) -> int:
        """发布消息到频道"""
        return await self._redis.publish(channel, message)

    async def subscribe(self, *channels: str):
        """订阅频道"""
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(*channels)
        return pubsub


# 导出
__all__ = ["RedisConnector"]
