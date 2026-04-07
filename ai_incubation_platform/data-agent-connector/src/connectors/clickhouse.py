"""
ClickHouse OLAP 数据库连接器
"""
import asyncio
from typing import Any, Dict, List, Optional
from connectors.base import BaseConnector, ConnectorConfig, ConnectorError
from utils.logger import logger


class ClickHouseConnector(BaseConnector):
    """ClickHouse OLAP 数据库连接器"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._client = None
        self._connection = None

    async def connect(self) -> None:
        """建立 ClickHouse 连接"""
        try:
            import clickhouse_connect
            from clickhouse_connect.driver.client import Client

            parsed = self._parse_connection_string()

            # 创建 ClickHouse 客户端
            self._client = clickhouse_connect.get_client(
                host=parsed.get('host', 'localhost'),
                port=int(parsed.get('port', 8123)),
                username=parsed.get('user', 'default'),
                password=parsed.get('password', ''),
                database=parsed.get('database', 'default'),
                send_receive_timeout=self.config.timeout,
                connect_timeout=self.config.timeout
            )

            # 测试连接
            result = self._client.command("SELECT 1")
            self._connected = True
            logger.info(f"Connected to ClickHouse: {parsed.get('host')}:{parsed.get('port')}")

        except Exception as e:
            raise ConnectorError(f"Failed to connect to ClickHouse: {e}")

    async def disconnect(self) -> None:
        """断开 ClickHouse 连接"""
        if self._client:
            self._client.close()
        self._connected = False

    async def execute(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """执行 SQL 查询"""
        if not self._connected:
            raise ConnectorError("Not connected to ClickHouse")

        try:
            loop = asyncio.get_event_loop()

            def run_query():
                if params:
                    # 使用参数化查询
                    result = self._client.query(query, params)
                else:
                    result = self._client.query(query)

                columns = result.column_names
                rows = []
                for row in result.result_rows:
                    row_dict = {}
                    for idx, col in enumerate(columns):
                        value = row[idx]
                        # 处理 datetime 类型
                        if hasattr(value, 'isoformat'):
                            value = value.isoformat()
                        row_dict[col] = value
                    rows.append(row_dict)
                return rows

            return await loop.run_in_executor(None, run_query)

        except Exception as e:
            raise ConnectorError(f"Query execution failed: {e}")

    async def get_schema(self) -> Dict[str, Any]:
        """获取数据库表结构"""
        try:
            loop = asyncio.get_event_loop()

            def get_schema():
                # 获取所有表
                tables_result = self._client.query("""
                    SELECT name, database
                    FROM system.tables
                    WHERE database = database()
                    ORDER BY name
                """)

                schema = {}
                for table_row in tables_result.result_rows:
                    table_name = table_row[0]
                    database = table_row[1]

                    # 获取表列信息
                    columns_result = self._client.query("""
                        SELECT name, type, is_nullable
                        FROM system.columns
                        WHERE database = database() AND table = %s
                        ORDER BY position
                    """, (table_name,))

                    columns = []
                    for col_row in columns_result.result_rows:
                        columns.append({
                            "name": col_row[0],
                            "type": col_row[1],
                            "nullable": col_row[2] == 1
                        })

                    # 获取表统计信息
                    stats_result = self._client.query("""
                        SELECT rows, bytes_on_disk, compression_rate
                        FROM system.tables
                        WHERE database = database() AND name = %s
                    """, (table_name,))

                    stats_row = stats_result.result_rows[0] if stats_result.result_rows else None

                    key = f"{database}.{table_name}" if database else table_name
                    schema[key] = {
                        "schema": database,
                        "name": table_name,
                        "columns": columns,
                        "row_count": stats_row[0] if stats_row else 0,
                        "size_bytes": stats_row[1] if stats_row else 0,
                        "compression_rate": stats_row[2] if stats_row else 1.0,
                        "engine": self._get_table_engine(table_name)
                    }

                return {"tables": schema}

            return await loop.run_in_executor(None, get_schema)

        except Exception as e:
            raise ConnectorError(f"Failed to get schema: {e}")

    def _get_table_engine(self, table_name: str) -> str:
        """获取表引擎类型"""
        try:
            result = self._client.query("""
                SELECT engine
                FROM system.tables
                WHERE database = database() AND name = %s
            """, (table_name,))
            if result.result_rows:
                return result.result_rows[0][0]
            return "Unknown"
        except Exception:
            return "Unknown"

    def _parse_connection_string(self) -> Dict[str, str]:
        """
        解析 ClickHouse 连接字符串
        格式：clickhouse://user:pass@host:port/database
        """
        from urllib.parse import urlparse, parse_qs

        parsed = urlparse(self.config.connection_string)
        query_params = parse_qs(parsed.query)

        return {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 8123,
            'user': parsed.username or 'default',
            'password': parsed.password or '',
            'database': parsed.path.lstrip('/') or query_params.get('database', ['default'])[0]
        }

    async def get_databases(self) -> List[str]:
        """获取所有数据库列表"""
        try:
            loop = asyncio.get_event_loop()

            def list_databases():
                result = self._client.query("SHOW DATABASES")
                return [row[0] for row in result.result_rows]

            return await loop.run_in_executor(None, list_databases)
        except Exception as e:
            raise ConnectorError(f"Failed to list databases: {e}")

    async def get_table_partitions(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表分区信息"""
        try:
            loop = asyncio.get_event_loop()

            def get_partitions():
                result = self._client.query("""
                    SELECT partition, name, rows, bytes_on_disk
                    FROM system.parts
                    WHERE database = database() AND table = %s
                    ORDER BY partition
                """, (table_name,))

                partitions = []
                for row in result.result_rows:
                    partitions.append({
                        "partition": row[0],
                        "name": row[1],
                        "rows": row[2],
                        "bytes_on_disk": row[3]
                    })
                return partitions

            return await loop.run_in_executor(None, get_partitions)
        except Exception as e:
            raise ConnectorError(f"Failed to get partitions: {e}")

    async def optimize_table(self, table_name: str, partition: Optional[str] = None) -> bool:
        """优化表（合并分区）"""
        try:
            if partition:
                query = f"OPTIMIZE TABLE {table_name} PARTITION '{partition}' FINAL"
            else:
                query = f"OPTIMIZE TABLE {table_name} FINAL"

            await self.execute(query)
            return True
        except Exception as e:
            logger.error(f"Failed to optimize table {table_name}: {e}")
            return False

    async def get_query_stats(self, query_id: str) -> Dict[str, Any]:
        """获取查询统计信息"""
        try:
            loop = asyncio.get_event_loop()

            def get_stats():
                result = self._client.query("""
                    SELECT query_duration_ms, read_rows, read_bytes, result_rows, result_bytes
                    FROM system.query_log
                    WHERE query_id = %s
                    ORDER BY event_time DESC
                    LIMIT 1
                """, (query_id,))

                if result.result_rows:
                    row = result.result_rows[0]
                    return {
                        "duration_ms": row[0],
                        "read_rows": row[1],
                        "read_bytes": row[2],
                        "result_rows": row[3],
                        "result_bytes": row[4]
                    }
                return None

            return await loop.run_in_executor(None, get_stats)
        except Exception as e:
            raise ConnectorError(f"Failed to get query stats: {e}")


# 导出连接器类
__all__ = ["ClickHouseConnector"]
