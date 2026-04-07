"""
StarRocks/Doris OLAP 数据库连接器
基于 MySQL 协议兼容
"""
import asyncio
from typing import Any, Dict, List, Optional
from connectors.base import BaseConnector, ConnectorConfig, ConnectorError
from utils.logger import logger


class StarRocksConnector(BaseConnector):
    """StarRocks/Doris OLAP 数据库连接器"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._connection = None
        self._cursor = None
        self._flavor = config.connection_string.split(':')[0] if config.connection_string else 'starrocks'

    async def connect(self) -> None:
        """建立 StarRocks/Doris 连接"""
        try:
            import aiomysql
            parsed = self._parse_connection_string()

            self._connection = await aiomysql.connect(
                host=parsed.get('host', 'localhost'),
                port=int(parsed.get('port', 9030)),
                user=parsed.get('user', 'root'),
                password=parsed.get('password', ''),
                db=parsed.get('database', 'default'),
                autocommit=True,
                connect_timeout=self.config.timeout
            )
            self._cursor = await self._connection.cursor()
            self._connected = True

            db_type = "StarRocks" if 'starrocks' in self._flavor else "Doris"
            logger.info(f"Connected to {db_type}: {parsed.get('host')}:{parsed.get('port')}")

        except Exception as e:
            raise ConnectorError(f"Failed to connect to StarRocks/Doris: {e}")

    async def disconnect(self) -> None:
        """断开连接"""
        if self._cursor:
            await self._cursor.close()
        if self._connection:
            await self._connection.close()
        self._connected = False

    async def execute(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """执行 SQL 查询"""
        if not self._connected:
            raise ConnectorError("Not connected to database")

        try:
            await self._cursor.execute(query, params or ())
            columns = [desc[0] for desc in self._cursor.description] if self._cursor.description else []
            rows = await self._cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            raise ConnectorError(f"Query execution failed: {e}")

    async def get_schema(self) -> Dict[str, Any]:
        """获取数据库表结构"""
        try:
            # 获取所有表
            await self._cursor.execute("""
                SELECT table_name, table_schema
                FROM information_schema.tables
                WHERE table_schema = database()
                ORDER BY table_name
            """)
            tables = await self._cursor.fetchall()

            schema = {}
            for table_name, table_schema in tables:
                # 跳过系统表
                if table_schema in ('information_schema', 'mysql', 'sys'):
                    continue

                key = f"{table_schema}.{table_name}"

                # 获取列信息
                await self._cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default, column_comment
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """, (table_schema, table_name))
                columns = await self._cursor.fetchall()

                # 获取表信息
                await self._cursor.execute("""
                    SELECT table_type, engine, table_rows, data_length
                    FROM information_schema.tables
                    WHERE table_schema = %s AND table_name = %s
                """, (table_schema, table_name))
                table_info = await self._cursor.fetchone()

                schema[key] = {
                    "schema": table_schema,
                    "name": table_name,
                    "columns": [
                        {
                            "name": col[0],
                            "type": col[1],
                            "nullable": col[2] == 'YES',
                            "default": col[3],
                            "comment": col[4]
                        }
                        for col in columns
                    ],
                    "table_type": table_info[0] if table_info else 'BASE TABLE',
                    "engine": table_info[1] if table_info else 'OLAP',
                    "row_count": table_info[2] if table_info else 0,
                    "data_length": table_info[3] if table_info else 0
                }

            return {"tables": schema}

        except Exception as e:
            raise ConnectorError(f"Failed to get schema: {e}")

    def _parse_connection_string(self) -> Dict[str, str]:
        """
        解析连接字符串
        格式：starrocks://user:pass@host:port/database
              doris://user:pass@host:port/database
        """
        from urllib.parse import urlparse, parse_qs

        parsed = urlparse(self.config.connection_string)
        query_params = parse_qs(parsed.query)

        return {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 9030,
            'user': parsed.username or 'root',
            'password': parsed.password or '',
            'database': parsed.path.lstrip('/') or query_params.get('database', ['default'])[0]
        }

    async def get_databases(self) -> List[str]:
        """获取所有数据库列表"""
        try:
            await self._cursor.execute("SHOW DATABASES")
            return [row[0] for row in await self._cursor.fetchall()]
        except Exception as e:
            raise ConnectorError(f"Failed to list databases: {e}")

    async def get_table_info(self, table_name: str, database: Optional[str] = None) -> Dict[str, Any]:
        """获取表详细信息"""
        try:
            db = database or (await self._cursor.execute("SELECT DATABASE()")) or await self._cursor.fetchone()[0]

            # 获取列信息
            await self._cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default, column_comment, ordinal_position
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
            """, (db, table_name))
            columns = await self._cursor.fetchall()

            # 获取索引信息
            await self._cursor.execute("""
                SELECT index_name, column_name, non_unique, comment
                FROM information_schema.statistics
                WHERE table_schema = %s AND table_name = %s
            """, (db, table_name))
            indexes = await self._cursor.fetchall()

            # 获取表信息
            await self._cursor.execute("""
                SELECT table_type, engine, table_rows, data_length, create_time
                FROM information_schema.tables
                WHERE table_schema = %s AND table_name = %s
            """, (db, table_name))
            table_info = await self._cursor.fetchone()

            return {
                "database": db,
                "table_name": table_name,
                "columns": [
                    {
                        "name": col[0],
                        "type": col[1],
                        "nullable": col[2] == 'YES',
                        "default": col[3],
                        "comment": col[4],
                        "position": col[5]
                    }
                    for col in columns
                ],
                "indexes": [
                    {
                        "name": idx[0],
                        "column": idx[1],
                        "non_unique": idx[2],
                        "comment": idx[3]
                    }
                    for idx in indexes
                ] if indexes else [],
                "table_type": table_info[0] if table_info else 'BASE TABLE',
                "engine": table_info[1] if table_info else 'OLAP',
                "row_count": table_info[2] if table_info else 0,
                "data_length": table_info[3] if table_info else 0,
                "create_time": str(table_info[4]) if table_info and table_info[4] else None
            }

        except Exception as e:
            raise ConnectorError(f"Failed to get table info: {e}")

    async def get_partition_info(self, table_name: str) -> List[Dict[str, Any]]:
        """获取分区信息（StarRocks/Doris 特有）"""
        try:
            # StarRocks/Doris 分区信息查询
            await self._cursor.execute(f"""
                SHOW PARTITIONS FROM {table_name}
            """)
            partitions = await self._cursor.fetchall()

            # 获取列名
            columns = [desc[0] for desc in self._cursor.description]

            return [dict(zip(columns, row)) for row in partitions]

        except Exception as e:
            # 如果表没有分区，返回空列表
            logger.debug(f"No partitions found for {table_name}: {e}")
            return []

    async def explain_query(self, query: str) -> Dict[str, Any]:
        """获取查询执行计划"""
        try:
            await self._cursor.execute(f"EXPLAIN {query}")
            rows = await self._cursor.fetchall()
            columns = [desc[0] for desc in self._cursor.description]

            plan = []
            for row in rows:
                plan.append(dict(zip(columns, row)))

            return {
                "query": query,
                "plan": plan,
                "plan_text": "\n".join([str(row) for row in plan])
            }

        except Exception as e:
            raise ConnectorError(f"Failed to explain query: {e}")

    async def get_backend_status(self) -> List[Dict[str, Any]]:
        """获取后端节点状态（StarRocks/Doris 特有）"""
        try:
            await self._cursor.execute("SHOW BACKENDS")
            rows = await self._cursor.fetchall()
            columns = [desc[0] for desc in self._cursor.description]

            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.warning(f"Failed to get backend status: {e}")
            return []


# 导出连接器类
__all__ = ["StarRocksConnector"]
