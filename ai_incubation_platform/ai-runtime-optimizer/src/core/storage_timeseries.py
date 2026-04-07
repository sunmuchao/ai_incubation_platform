"""
时序数据库存储层：InfluxDB 集成
提供高性能的时序数据存储和查询能力，支持长期存储和数据降采样
"""
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)

try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS
    from influxdb_client.client.query_api import QueryApi
    from influxdb import InfluxDBClient as InfluxDBClientV1
    INFLUXDB_AVAILABLE = True
except ImportError:
    INFLUXDB_AVAILABLE = False
    logger.warning("InfluxDB client not installed. Install with: pip install influxdb-client")


class InfluxDBStorage:
    """InfluxDB 时序存储实现

    支持:
    - 高性能时序数据写入
    - Flux 查询语言
    - 数据保留策略 (Retention Policy)
    - 连续查询 (Continuous Query) 用于降采样
    - 多 bucket 管理
    """

    def __init__(
        self,
        url: str = "http://localhost:8086",
        token: str = "my-token",
        org: str = "my-org",
        bucket: str = "ai-optimizer",
        retention_policy: str = "30d",
        use_v1: bool = False,
        v1_username: str = None,
        v1_password: str = None,
        v1_database: str = None
    ):
        """初始化 InfluxDB 连接

        Args:
            url: InfluxDB URL (v2: http://localhost:8086, v1: http://localhost:8086)
            token: InfluxDB v2 API token
            org: InfluxDB v2 组织名
            bucket: InfluxDB v2 bucket 名
            retention_policy: 数据保留策略 (如 "30d", "7d", "365d")
            use_v1: 是否使用 InfluxDB v1 协议
            v1_username: InfluxDB v1 用户名
            v1_password: InfluxDB v1 密码
            v1_database: InfluxDB v1 数据库名
        """
        self.url = url
        self.org = org
        self.bucket = bucket
        self.use_v1 = use_v1

        if use_v1:
            # InfluxDB v1.x 客户端
            self.client = InfluxDBClientV1(
                host=url.replace("http://", "").split("/")[0].split(":")[0],
                port=int(url.split(":")[-1]) if ":" in url.split("/")[-1] else 8086,
                username=v1_username or "admin",
                password=v1_password or "password",
                database=v1_database or bucket
            )
            self.write_api = None
            self.query_api = None
        else:
            # InfluxDB v2.x 客户端
            self.client = InfluxDBClient(url=url, token=token, org=org)
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.client.query_api()

        self._prefix = "ai_optimizer"
        self._setup_bucket(retention_policy)

    def _setup_bucket(self, retention_policy: str) -> None:
        """设置 bucket 和保留策略"""
        if self.use_v1:
            # v1 使用 database，不需要显式创建
            logger.info(f"Using InfluxDB v1 database: {self.bucket}")
            return

        try:
            buckets_api = self.client.buckets_api()
            bucket = buckets_api.find_bucket_by_name(self.bucket)

            if bucket is None:
                # 创建 bucket 并设置保留策略
                retention_seconds = self._parse_retention(retention_policy)
                bucket = buckets_api.create_bucket(
                    bucket_name=self.bucket,
                    retention_rules=[{"type": "expire", "everySeconds": retention_seconds}]
                )
                logger.info(f"Created bucket: {self.bucket} with retention {retention_policy}")
            else:
                logger.info(f"Using existing bucket: {self.bucket}")

        except Exception as e:
            logger.warning(f"Failed to setup bucket: {e}. Will use default bucket.")

    def _parse_retention(self, retention_policy: str) -> int:
        """解析保留策略为秒数

        Args:
            retention_policy: 如 "7d", "30d", "365d", "24h"

        Returns:
            保留时间的秒数
        """
        unit = retention_policy[-1]
        value = int(retention_policy[:-1])

        if unit == 'h':
            return value * 3600
        elif unit == 'd':
            return value * 86400
        elif unit == 'w':
            return value * 604800
        elif unit == 'M':
            return value * 2592000  # 30 天
        elif unit == 'y':
            return value * 31536000  # 365 天
        else:
            return value  # 默认为秒

    def _get_measurement(self, metric_type: str) -> str:
        """获取 measurement 名称"""
        return f"{self._prefix}_{metric_type}"

    def record_metric(
        self,
        service_name: str,
        metric_name: str,
        value: float,
        timestamp: datetime = None,
        tags: Dict[str, str] = None,
        fields: Dict[str, Any] = None
    ) -> bool:
        """记录单个指标数据点

        Args:
            service_name: 服务名
            metric_name: 指标名
            value: 指标值
            timestamp: 时间戳，默认当前时间
            tags: 标签（用于索引和过滤）
            fields: 字段（存储的数据）

        Returns:
            是否写入成功
        """
        if not INFLUXDB_AVAILABLE:
            logger.error("InfluxDB client not available")
            return False

        try:
            if timestamp is None:
                timestamp = datetime.utcnow()

            # 构建默认 tags
            default_tags = {
                "service_name": service_name,
                "metric_name": metric_name,
            }
            if tags:
                default_tags.update(tags)

            # 构建默认 fields
            default_fields = {"value": value}
            if fields:
                default_fields.update(fields)

            # 创建 Point
            point = Point(self._get_measurement("metrics")) \
                .tag("service", service_name) \
                .tag("metric", metric_name) \
                .tag(**{k: str(v) for k, v in default_tags.items()}) \
                .field(**{k: float(v) if isinstance(v, (int, float)) else str(v)
                         for k, v in default_fields.items()}) \
                .time(timestamp, WritePrecision.NS)

            if self.use_v1:
                # v1 写入
                json_body = [
                    {
                        "measurement": self._get_measurement("metrics"),
                        "tags": default_tags,
                        "fields": default_fields,
                        "time": timestamp.isoformat()
                    }
                ]
                self.client.write_points(json_body)
            else:
                # v2 写入
                self.write_api.write(bucket=self.bucket, record=point)

            return True

        except Exception as e:
            logger.error(f"Failed to write metric: {e}")
            return False

    def record_metrics_batch(
        self,
        metrics: List[Dict[str, Any]]
    ) -> Tuple[int, int]:
        """批量记录指标数据

        Args:
            metrics: 指标列表，每个指标包含:
                - service_name: str
                - metric_name: str
                - value: float
                - timestamp: datetime (可选)
                - tags: Dict (可选)
                - fields: Dict (可选)

        Returns:
            (成功数量，失败数量)
        """
        if not INFLUXDB_AVAILABLE:
            return (0, len(metrics))

        success_count = 0
        fail_count = 0

        points = []
        for m in metrics:
            try:
                timestamp = m.get("timestamp") or datetime.utcnow()
                service_name = m.get("service_name", "unknown")
                metric_name = m.get("metric_name", "unknown")
                value = m.get("value", 0)
                tags = m.get("tags", {})
                fields = m.get("fields", {})

                point = Point(self._get_measurement("metrics")) \
                    .tag("service", service_name) \
                    .tag("metric", metric_name) \
                    .tag(**{k: str(v) for k, v in tags.items()}) \
                    .field(**{k: float(v) if isinstance(v, (int, float)) else str(v)
                             for k, v in {**{"value": value}, **fields}.items()}) \
                    .time(timestamp, WritePrecision.NS)
                points.append(point)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to prepare metric point: {e}")
                fail_count += 1

        if points and not self.use_v1:
            try:
                self.write_api.write(bucket=self.bucket, record=points)
            except Exception as e:
                logger.error(f"Failed to write batch: {e}")
                fail_count += len(points)
                success_count = 0

        return (success_count, fail_count)

    def query_metrics(
        self,
        service_name: str = None,
        metric_name: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        aggregation: str = None,
        aggregation_window: str = "1m",
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """查询指标数据

        Args:
            service_name: 服务名过滤
            metric_name: 指标名过滤
            start_time: 开始时间
            end_time: 结束时间
            aggregation: 聚合函数 (mean, max, min, sum, count)
            aggregation_window: 聚合窗口 (如 "1m", "5m", "1h")
            limit: 返回结果数量限制

        Returns:
            指标数据列表
        """
        if not INFLUXDB_AVAILABLE:
            return []

        # 默认时间范围：最近 1 小时
        if start_time is None:
            start_time = datetime.utcnow() - timedelta(hours=1)
        if end_time is None:
            end_time = datetime.utcnow()

        # 构建 Flux 查询
        bucket_filter = f'from(bucket: "{self.bucket}")'
        range_filter = f'  |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})'

        # 构建过滤器
        filters = ['r._measurement == "ai_optimizer_metrics"']
        if service_name:
            filters.append(f'r.service == "{service_name}"')
        if metric_name:
            filters.append(f'r.metric == "{metric_name}"')

        filter_expr = '  |> filter(fn: (r) => ' + ' and '.join(filters) + ')'

        # 聚合
        if aggregation:
            agg_func = f'mean(column: "value")'
            if aggregation == 'max':
                agg_func = 'max(column: "value")'
            elif aggregation == 'min':
                agg_func = 'min(column: "value")'
            elif aggregation == 'sum':
                agg_func = 'sum(column: "value")'
            elif aggregation == 'count':
                agg_func = 'count(column: "value")'
            elif aggregation == 'percentile_95':
                agg_func = 'percentileAggregate(column: "value", method: "estimate", percentage: 0.95)'
            elif aggregation == 'percentile_99':
                agg_func = 'percentileAggregate(column: "value", method: "estimate", percentage: 0.99)'

            agg_expr = f'  |> aggregateWindow(every: {aggregation_window}, fn: {agg_func}, createEmpty: false)'
        else:
            agg_expr = ''

        # 限制结果数量
        limit_expr = f'  |> limit(n: {limit})'

        flux_query = f'''
{bucket_filter}
{range_filter}
{filter_expr}
{agg_expr}
{limit_expr}
'''

        try:
            if self.use_v1:
                # v1 使用 InfluxQL
                where_clauses = []
                if service_name:
                    where_clauses.append(f'"service" = \'{service_name}\'')
                if metric_name:
                    where_clauses.append(f'"metric" = \'{metric_name}\'')

                where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
                agg_func = aggregation or 'mean'

                query = f'''
SELECT {agg_func}("value")
FROM "{self._get_measurement('metrics')}"
WHERE {where_clause}
AND time >= '{start_time.isoformat()}'
AND time <= '{end_time.isoformat()}'
GROUP BY time({aggregation_window}), "service", "metric"
ORDER BY time DESC
LIMIT {limit}
'''
                result = self.client.query(query)
                return self._parse_v1_result(result)
            else:
                # v2 使用 Flux
                result = self.query_api.query(flux_query)
                return self._parse_flux_result(result)

        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []

    def _parse_flux_result(self, result) -> List[Dict[str, Any]]:
        """解析 Flux 查询结果"""
        data = []
        for table in result:
            for record in table.records:
                data.append({
                    "time": record.get_time(),
                    "service": record.values.get("service"),
                    "metric": record.values.get("metric"),
                    "value": record.get_value(),
                    "_value": record.get_value(),
                    "_time": record.get_time(),
                })
        return data

    def _parse_v1_result(self, result) -> List[Dict[str, Any]]:
        """解析 InfluxQL 查询结果"""
        data = []
        if result and len(result) > 0:
            for point in result[0].get_points():
                data.append({
                    "time": point.get("time"),
                    "service": point.get("service"),
                    "metric": point.get("metric"),
                    "value": point.get("mean") or point.get("value"),
                })
        return data

    def get_service_metrics(
        self,
        service_name: str,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100
    ) -> Dict[str, List[float]]:
        """获取服务的所有指标时间序列

        Args:
            service_name: 服务名
            start_time: 开始时间
            end_time: 结束时间
            limit: 每个指标的最大数据点数

        Returns:
            {metric_name: [values]}
        """
        results = self.query_metrics(
            service_name=service_name,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )

        # 按指标名分组
        metrics_by_name = {}
        for r in results:
            metric = r.get("metric")
            if metric:
                if metric not in metrics_by_name:
                    metrics_by_name[metric] = []
                metrics_by_name[metric].append({
                    "time": r.get("time"),
                    "value": r.get("value")
                })

        return metrics_by_name

    def get_metric_stats(
        self,
        service_name: str,
        metric_name: str,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> Dict[str, Any]:
        """获取指标统计信息

        Args:
            service_name: 服务名
            metric_name: 指标名
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            统计信息 {mean, min, max, std_dev, count, ...}
        """
        stats = {}

        # 查询均值
        result = self.query_metrics(
            service_name=service_name,
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time,
            aggregation="mean"
        )
        if result:
            values = [r.get("value") for r in result if r.get("value") is not None]
            if values:
                stats["mean"] = sum(values) / len(values)

        # 查询最大值
        result = self.query_metrics(
            service_name=service_name,
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time,
            aggregation="max"
        )
        if result and result[0].get("value"):
            stats["max"] = result[0].get("value")

        # 查询最小值
        result = self.query_metrics(
            service_name=service_name,
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time,
            aggregation="min"
        )
        if result and result[0].get("value"):
            stats["min"] = result[0].get("value")

        # 查询数量
        result = self.query_metrics(
            service_name=service_name,
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time,
            aggregation="count"
        )
        if result and result[0].get("value"):
            stats["count"] = int(result[0].get("value"))

        return stats

    def create_downsampling_policy(
        self,
        source_bucket: str = None,
        dest_bucket: str = None,
        aggregation_window: str = "1h",
        retention_policy: str = "90d",
        policy_name: str = "hourly_downsample"
    ) -> bool:
        """创建数据降采样策略

        Args:
            source_bucket: 源 bucket
            dest_bucket: 目标 bucket
            aggregation_window: 聚合窗口
            retention_policy: 保留策略
            policy_name: 策略名

        Returns:
            是否创建成功
        """
        if self.use_v1:
            # v1 使用连续查询
            source_db = source_bucket or self.bucket
            dest_db = dest_bucket or f"{self.bucket}_downsampled"

            query = f'''
CREATE DATABASE {dest_db}
'''
            self.client.query(query)

            cq_query = f'''
CREATE CONTINUOUS QUERY {policy_name} ON {source_db}
BEGIN
  SELECT mean("value") AS "value"
  INTO {dest_db}."autogen"."{self._get_measurement('metrics')}"
  FROM "{self._get_measurement('metrics')}"
  GROUP BY time({aggregation_window}), "service", "metric"
END
'''
            try:
                self.client.query(cq_query)
                logger.info(f"Created continuous query: {policy_name}")
                return True
            except Exception as e:
                logger.error(f"Failed to create CQ: {e}")
                return False
        else:
            # v2 使用任务 (Task)
            source_bucket = source_bucket or self.bucket
            dest_bucket = dest_bucket or f"{self.bucket}_downsampled"

            # 首先创建目标 bucket
            try:
                buckets_api = self.client.buckets_api()
                dest_bucket_obj = buckets_api.find_bucket_by_name(dest_bucket)
                if dest_bucket_obj is None:
                    retention_seconds = self._parse_retention(retention_policy)
                    buckets_api.create_bucket(
                        bucket_name=dest_bucket,
                        retention_rules=[{"type": "expire", "everySeconds": retention_seconds}]
                    )
            except Exception as e:
                logger.error(f"Failed to create dest bucket: {e}")

            # 创建任务
            tasks_api = self.client.tasks_api()

            flux_task = f'''
option task = {{
  name: "{policy_name}",
  every: {aggregation_window},
  offset: 10s
}}

data = from(bucket: "{source_bucket}")
  |> range(start: -{aggregation_window * 2})
  |> filter(fn: (r) => r._measurement == "ai_optimizer_metrics")
  |> aggregateWindow(every: {aggregation_window}, fn: mean, createEmpty: false)

data
  |> to(bucket: "{dest_bucket}")
'''
            try:
                task = tasks_api.create_task(flux_task)
                logger.info(f"Created task: {policy_name} (id: {task.id})")
                return True
            except Exception as e:
                logger.error(f"Failed to create task: {e}")
                return False

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            if self.use_v1:
                result = self.client.ping()
                return {
                    "status": "healthy",
                    "type": "influxdb_v1",
                    "ping": result
                }
            else:
                health = self.client.health()
                return {
                    "status": "healthy" if health.status == "pass" else "unhealthy",
                    "type": "influxdb_v2",
                    "message": health.message
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": f"InfluxDB connection failed: {str(e)}"
            }

    def close(self):
        """关闭连接"""
        if self.client:
            self.client.close()


# ==================== 混合存储层 ====================

class HybridStorage:
    """混合存储层：同时支持 Redis 和 InfluxDB

    策略:
    - 热数据 (最近 1 小时): 写入 Redis + InfluxDB
    - 温数据 (最近 24 小时): 从 Redis 读取，不存在则从 InfluxDB 读取
    - 冷数据 (24 小时前): 仅从 InfluxDB 读取
    """

    def __init__(
        self,
        redis_storage=None,
        influxdb_storage: InfluxDBStorage = None,
        redis_ttl_seconds: int = 3600  # Redis 中数据的 TTL
    ):
        """初始化混合存储

        Args:
            redis_storage: Redis 存储实例
            influxdb_storage: InfluxDB 存储实例
            redis_ttl_seconds: Redis 中数据的 TTL（秒）
        """
        self.redis_storage = redis_storage
        self.influxdb_storage = influxdb_storage
        self.redis_ttl_seconds = redis_ttl_seconds

    def record_metric(self, service_name: str, metric_name: str, value: float,
                     timestamp: datetime = None, tags: Dict[str, str] = None) -> bool:
        """记录指标到两个存储"""
        success = True

        # 写入 InfluxDB（持久化）
        if self.influxdb_storage:
            success = self.influxdb_storage.record_metric(
                service_name, metric_name, value, timestamp, tags
            ) and success

        # 写入 Redis（热数据缓存）
        if self.redis_storage and hasattr(self.redis_storage, 'redis'):
            try:
                key = f"ai-optimizer:timeseries:{service_name}:{metric_name}"
                record = {
                    "timestamp": (timestamp or datetime.utcnow()).isoformat(),
                    "value": value
                }
                self.redis_storage.redis.rpush(key, json.dumps(record))
                # 设置过期时间
                self.redis_storage.redis.expire(key, self.redis_ttl_seconds)
                # 保持列表长度
                self.redis_storage.redis.ltrim(key, -1000, -1)
            except Exception as e:
                logger.error(f"Failed to write to Redis: {e}")
                success = False

        return success

    def query_metrics(
        self,
        service_name: str = None,
        metric_name: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        aggregation: str = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """查询指标数据，优先从 Redis 读取热数据"""
        # 如果是查询最近的数据，优先从 Redis 读取
        if start_time is None or (datetime.utcnow() - start_time).total_seconds() < self.redis_ttl_seconds:
            if self.redis_storage and hasattr(self.redis_storage, 'redis'):
                try:
                    if service_name and metric_name:
                        key = f"ai-optimizer:timeseries:{service_name}:{metric_name}"
                        records = self.redis_storage.redis.lrange(key, -limit, -1)
                        if records:
                            data = []
                            for r in records:
                                record = json.loads(r)
                                data.append({
                                    "time": datetime.fromisoformat(record["timestamp"]),
                                    "service": service_name,
                                    "metric": metric_name,
                                    "value": record["value"]
                                })
                            return data
                except Exception as e:
                    logger.error(f"Failed to read from Redis: {e}")

        # 从 InfluxDB 读取
        if self.influxdb_storage:
            return self.influxdb_storage.query_metrics(
                service_name=service_name,
                metric_name=metric_name,
                start_time=start_time,
                end_time=end_time,
                aggregation=aggregation,
                limit=limit
            )

        return []

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health = {
            "status": "healthy",
            "components": {}
        }

        if self.redis_storage:
            if hasattr(self.redis_storage, 'health_check'):
                health["components"]["redis"] = self.redis_storage.health_check()
            else:
                health["components"]["redis"] = {"status": "unknown"}

        if self.influxdb_storage:
            health["components"]["influxdb"] = self.influxdb_storage.health_check()

        # 整体状态：只要有一个组件不健康就不健康
        for comp_health in health["components"].values():
            if comp_health.get("status") != "healthy":
                health["status"] = "degraded"
                break

        return health


# ==================== 全局实例 ====================

_influxdb_instance: Optional[InfluxDBStorage] = None
_hybrid_instance: Optional[HybridStorage] = None


def get_influxdb_storage(
    url: str = None,
    token: str = None,
    org: str = "my-org",
    bucket: str = "ai-optimizer"
) -> InfluxDBStorage:
    """获取或创建 InfluxDB 存储实例"""
    global _influxdb_instance

    if _influxdb_instance is None:
        from core.config import config

        url = url or getattr(config, 'influxdb_url', 'http://localhost:8086')
        token = token or getattr(config, 'influxdb_token', 'my-token')
        org = org or getattr(config, 'influxdb_org', 'my-org')
        bucket = bucket or getattr(config, 'influxdb_bucket', 'ai-optimizer')

        _influxdb_instance = InfluxDBStorage(
            url=url,
            token=token,
            org=org,
            bucket=bucket
        )

    return _influxdb_instance


def get_hybrid_storage(
    redis_storage=None,
    influxdb_storage: InfluxDBStorage = None
) -> HybridStorage:
    """获取或创建混合存储实例"""
    global _hybrid_instance

    if _hybrid_instance is None:
        from core.config import config

        # 延迟导入避免循环依赖
        if redis_storage is None:
            try:
                from core.storage_redis import get_redis_storage
                redis_storage = get_redis_storage()
            except Exception:
                logger.warning("Redis storage not available")

        if influxdb_storage is None:
            influxdb_storage = get_influxdb_storage()

        ttl = getattr(config, 'timeseries_redis_ttl_seconds', 3600)
        _hybrid_instance = HybridStorage(
            redis_storage=redis_storage,
            influxdb_storage=influxdb_storage,
            redis_ttl_seconds=ttl
        )

    return _hybrid_instance
