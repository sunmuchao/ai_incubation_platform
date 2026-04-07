"""
Presto/Trino 连接器 - 异步
"""
import asyncio
from typing import Any, Dict, List, Optional
from connectors.base import BaseConnector, ConnectorConfig, ConnectorError, HealthStatus


class PrestoConnector(BaseConnector):
    """Presto/Trino 数据仓库连接器（使用 prestodb 异步包装）"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._connection = None
        self._cursor = None

    async def connect(self) -> None:
        """建立 Presto/Trino 连接"""
        try:
            import prestodb

            parsed = self._parse_connection_string()

            # Presto 连接是同步的，需要在 executor 中运行
            loop = asyncio.get_event_loop()

            def _sync_connect():
                conn = prestodb.dbapi.connect(
                    host=parsed.get('host', 'localhost'),
                    port=int(parsed.get('port', 8080)),
                    user=parsed.get('user', 'presto'),
                    catalog=parsed.get('catalog', 'hive'),
                    schema=parsed.get('schema', 'default'),
                )
                if parsed.get('password'):
                    conn._client_session.password = parsed.get('password')
                return conn

            self._connection = await loop.run_in_executor(None, _sync_connect)
            self._cursor = self._connection.cursor()
            self._connected = True

        except Exception as e:
            raise ConnectorError(f"Failed to connect to Presto/Trino: {e}")

    async def disconnect(self) -> None:
        """断开 Presto/Trino 连接"""
        if self._cursor:
            self._cursor.close()
        if self._connection:
            self._connection.close()
        self._connected = False

    async def execute(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """执行 Presto SQL 查询"""
        if not self._connected:
            raise ConnectorError("Not connected to Presto/Trino")

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
        """获取 Presto/Trino 数据库结构"""
        if not self._connected:
            raise ConnectorError("Not connected to Presto/Trino")

        try:
            loop = asyncio.get_event_loop()

            def _sync_get_schema():
                schema = {}

                # 获取所有 catalog
                self._cursor.execute("SHOW CATALOGS")
                catalogs = [row[0] for row in self._cursor.fetchall()]

                for catalog in catalogs:
                    # 切换到 catalog
                    self._cursor.execute(f"USE {catalog}.{self._get_schema_name()}")

                    # 获取所有表
                    self._cursor.execute("SHOW TABLES")
                    tables = [row[0] for row in self._cursor.fetchall()]

                    catalog_schema = {}
                    for table in tables:
                        self._cursor.execute(f"DESCRIBE {table}")
                        columns = self._cursor.fetchall()
                        catalog_schema[table] = [
                            {"name": col[0], "type": col[1], "nullable": True}
                            for col in columns
                        ]

                    schema[catalog] = catalog_schema

                return {"catalogs": schema}

            return await loop.run_in_executor(None, _sync_get_schema)

        except Exception as e:
            raise ConnectorError(f"Failed to get schema: {e}")

    async def health_check(self) -> HealthStatus:
        """Presto/Trino 健康检查"""
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
                message="Presto/Trino connection OK",
                timestamp=str(asyncio.get_event_loop().time()),
                connector_type="presto",
                connector_name=self.config.name
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return HealthStatus(
                status="unhealthy",
                latency_ms=round(latency_ms, 2),
                message=str(e),
                timestamp=str(asyncio.get_event_loop().time()),
                connector_type="presto",
                connector_name=self.config.name
            )

    async def get_catalogs(self) -> List[str]:
        """获取所有 Catalog 列表"""
        result = await self.execute("SHOW CATALOGS")
        return [row[list(row.keys())[0]] for row in result]

    async def get_schemas(self, catalog: str) -> List[str]:
        """获取指定 Catalog 下的所有 Schema"""
        result = await self.execute(f"SHOW SCHEMAS FROM {catalog}")
        return [row[list(row.keys())[0]] for row in result]

    async def get_table_stats(self, catalog: str, schema: str, table: str) -> Dict[str, Any]:
        """获取表统计信息"""
        if not self._connected:
            raise ConnectorError("Not connected to Presto/Trino")

        try:
            loop = asyncio.get_event_loop()

            def _sync_get_stats():
                # 使用 information_schema 获取统计信息
                query = f"""
                    SELECT table_name, row_count, data_size
                    FROM {catalog}.information_schema.tables
                    WHERE table_schema = '{schema}' AND table_name = '{table}'
                """
                self._cursor.execute(query)
                rows = self._cursor.fetchall()

                if rows:
                    return {
                        "table_name": rows[0][0],
                        "row_count": rows[0][1] if len(rows[0]) > 1 else 0,
                        "data_size": rows[0][2] if len(rows[0]) > 2 else 0,
                    }
                return {}

            return await loop.run_in_executor(None, _sync_get_stats)

        except Exception as e:
            raise ConnectorError(f"Failed to get table stats: {e}")

    async def explain_query(self, query: str) -> Dict[str, Any]:
        """获取查询执行计划"""
        if not self._connected:
            raise ConnectorError("Not connected to Presto/Trino")

        try:
            result = await self.execute(f"EXPLAIN {query}")
            return {"plan": result}
        except Exception as e:
            raise ConnectorError(f"Failed to explain query: {e}")

    def _parse_connection_string(self) -> Dict[str, str]:
        """
        解析连接字符串
        格式：presto://user@host:port/catalog/schema
        """
        from urllib.parse import urlparse, parse_qs

        parsed = urlparse(self.config.connection_string)
        query_params = parse_qs(parsed.query)

        path_parts = parsed.path.strip('/').split('/')

        return {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 8080,
            'user': parsed.username or query_params.get('user', ['presto'])[0],
            'password': parsed.password or query_params.get('password', [''])[0],
            'catalog': path_parts[0] if len(path_parts) > 0 else 'hive',
            'schema': path_parts[1] if len(path_parts) > 1 else 'default',
        }

    def _get_schema_name(self) -> str:
        """获取 schema 名称"""
        parsed = self._parse_connection_string()
        return parsed.get('schema', 'default')


# 导出
__all__ = ["PrestoConnector"]
