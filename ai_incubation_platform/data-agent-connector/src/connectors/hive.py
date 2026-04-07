"""
Apache Hive 连接器 - 异步
"""
import asyncio
from typing import Any, Dict, List, Optional
from connectors.base import BaseConnector, ConnectorConfig, ConnectorError, HealthStatus


class HiveConnector(BaseConnector):
    """Apache Hive 数据仓库连接器（使用 impyla 异步包装）"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._connection = None
        self._cursor = None

    async def connect(self) -> None:
        """建立 Hive 连接"""
        try:
            from impala.dbapi import connect

            parsed = self._parse_connection_string()

            # Hive 连接通常是同步的，需要在 executor 中运行
            loop = asyncio.get_event_loop()

            def _sync_connect():
                return connect(
                    host=parsed.get('host', 'localhost'),
                    port=int(parsed.get('port', 10000)),
                    database=parsed.get('database', 'default'),
                    user=parsed.get('user', ''),
                    password=parsed.get('password', ''),
                    auth_mechanism=parsed.get('auth', 'NOSASL'),
                )

            self._connection = await loop.run_in_executor(None, _sync_connect)
            self._cursor = self._connection.cursor()
            self._connected = True

        except Exception as e:
            raise ConnectorError(f"Failed to connect to Hive: {e}")

    async def disconnect(self) -> None:
        """断开 Hive 连接"""
        if self._cursor:
            self._cursor.close()
        if self._connection:
            self._connection.close()
        self._connected = False

    async def execute(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """执行 Hive SQL 查询"""
        if not self._connected:
            raise ConnectorError("Not connected to Hive")

        try:
            loop = asyncio.get_event_loop()

            def _sync_execute():
                self._cursor.execute(query, params or ())
                if self._cursor.description:
                    columns = [desc[0] for desc in self._cursor.description]
                    rows = self._cursor.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
                return []

            return await loop.run_in_executor(None, _sync_execute)

        except Exception as e:
            raise ConnectorError(f"Query execution failed: {e}")

    async def get_schema(self) -> Dict[str, Any]:
        """获取 Hive 数据库结构"""
        if not self._connected:
            raise ConnectorError("Not connected to Hive")

        try:
            loop = asyncio.get_event_loop()

            def _sync_get_schema():
                schema = {}

                # 获取所有数据库
                self._cursor.execute("SHOW DATABASES")
                databases = [row[0] for row in self._cursor.fetchall()]

                for db in databases:
                    self._cursor.execute(f"USE {db}")
                    self._cursor.execute("SHOW TABLES")
                    tables = [row[0] for row in self._cursor.fetchall()]

                    db_schema = {}
                    for table in tables:
                        self._cursor.execute(f"DESCRIBE {table}")
                        columns = self._cursor.fetchall()
                        db_schema[table] = [
                            {"name": col[0], "type": col[1], "nullable": True}
                            for col in columns if col[0] and not col[0].startswith('#')
                        ]

                    schema[db] = db_schema

                return {"databases": schema}

            return await loop.run_in_executor(None, _sync_get_schema)

        except Exception as e:
            raise ConnectorError(f"Failed to get schema: {e}")

    async def health_check(self) -> HealthStatus:
        """Hive 健康检查"""
        import time
        start_time = time.time()

        try:
            if not self._connected:
                await self.connect()

            # 执行简单的查询
            await self.execute("SELECT 1")

            latency_ms = (time.time() - start_time) * 1000

            return HealthStatus(
                status="healthy",
                latency_ms=round(latency_ms, 2),
                message="Hive connection OK",
                timestamp=str(asyncio.get_event_loop().time()),
                connector_type="hive",
                connector_name=self.config.name
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return HealthStatus(
                status="unhealthy",
                latency_ms=round(latency_ms, 2),
                message=str(e),
                timestamp=str(asyncio.get_event_loop().time()),
                connector_type="hive",
                connector_name=self.config.name
            )

    async def get_databases(self) -> List[str]:
        """获取所有数据库列表"""
        result = await self.execute("SHOW DATABASES")
        return [row[list(row.keys())[0]] for row in result]

    async def get_table_stats(self, database: str, table: str) -> Dict[str, Any]:
        """获取表统计信息"""
        if not self._connected:
            raise ConnectorError("Not connected to Hive")

        try:
            loop = asyncio.get_event_loop()

            def _sync_get_stats():
                self._cursor.execute(f"USE {database}")
                self._cursor.execute(f"DESCRIBE FORMATTED {table}")
                rows = self._cursor.fetchall()

                stats = {}
                for row in rows:
                    if row[0] and row[1]:
                        key = row[0].strip()
                        value = row[1].strip()
                        stats[key] = value

                return stats

            return await loop.run_in_executor(None, _sync_get_stats)

        except Exception as e:
            raise ConnectorError(f"Failed to get table stats: {e}")

    async def get_partition_info(self, database: str, table: str) -> List[Dict[str, Any]]:
        """获取分区信息"""
        if not self._connected:
            raise ConnectorError("Not connected to Hive")

        try:
            loop = asyncio.get_event_loop()

            def _sync_get_partitions():
                self._cursor.execute(f"USE {database}")
                self._cursor.execute(f"SHOW PARTITIONS {table}")
                partitions = [row[0] for row in self._cursor.fetchall()]

                return [{"partition": p} for p in partitions]

            return await loop.run_in_executor(None, _sync_get_partitions)

        except Exception as e:
            raise ConnectorError(f"Failed to get partition info: {e}")

    def _parse_connection_string(self) -> Dict[str, str]:
        """
        解析连接字符串
        格式：hive://host:port/database?user=xxx&password=xxx&auth=SASL
        """
        from urllib.parse import urlparse, parse_qs

        parsed = urlparse(self.config.connection_string)
        query_params = parse_qs(parsed.query)

        return {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 10000,
            'database': parsed.path.lstrip('/') or query_params.get('database', ['default'])[0],
            'user': parsed.username or query_params.get('user', [''])[0],
            'password': parsed.password or query_params.get('password', [''])[0],
            'auth': query_params.get('auth', ['NOSASL'])[0],
        }


# 导出
__all__ = ["HiveConnector"]
