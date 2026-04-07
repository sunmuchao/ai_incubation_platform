"""
数据库连接器
"""
import asyncio
from typing import Any, Dict, List, Optional
from connectors.base import BaseConnector, ConnectorConfig, ConnectorError


class MySQLConnector(BaseConnector):
    """MySQL 数据库连接器"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._connection = None
        self._cursor = None

    async def connect(self) -> None:
        """建立 MySQL 连接"""
        try:
            import aiomysql
            parsed = self._parse_connection_string()
            self._connection = await aiomysql.connect(
                host=parsed.get('host', 'localhost'),
                port=int(parsed.get('port', 3306)),
                user=parsed.get('user', 'root'),
                password=parsed.get('password', ''),
                db=parsed.get('database', ''),
                autocommit=True
            )
            self._cursor = await self._connection.cursor()
            self._connected = True
        except Exception as e:
            raise ConnectorError(f"Failed to connect to MySQL: {e}")

    async def disconnect(self) -> None:
        """断开 MySQL 连接"""
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
            columns = [desc[0] for desc in self._cursor.description]
            rows = await self._cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            raise ConnectorError(f"Query execution failed: {e}")

    async def get_schema(self) -> Dict[str, Any]:
        """获取数据库表结构"""
        tables_query = "SHOW TABLES"
        await self._cursor.execute(tables_query)
        tables = [row[0] for row in await self._cursor.fetchall()]

        schema = {}
        for table in tables:
            await self._cursor.execute(f"DESCRIBE {table}")
            columns = await self._cursor.fetchall()
            schema[table] = [
                {"name": col[0], "type": col[1], "nullable": col[2] == 'YES'}
                for col in columns
            ]
        return {"tables": schema}

    def _parse_connection_string(self) -> Dict[str, str]:
        """解析连接字符串 mysql://user:pass@host:port/db"""
        from urllib.parse import urlparse
        parsed = urlparse(self.config.connection_string)
        return {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 3306,
            'user': parsed.username or 'root',
            'password': parsed.password or '',
            'database': parsed.path.lstrip('/') or ''
        }


class PostgreSQLConnector(BaseConnector):
    """PostgreSQL 数据库连接器"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._connection = None
        self._cursor = None

    async def connect(self) -> None:
        """建立 PostgreSQL 连接"""
        try:
            import asyncpg
            self._connection = await asyncpg.connect(self.config.connection_string)
            self._connected = True
        except Exception as e:
            raise ConnectorError(f"Failed to connect to PostgreSQL: {e}")

    async def disconnect(self) -> None:
        """断开 PostgreSQL 连接"""
        if self._connection:
            await self._connection.close()
        self._connected = False

    async def execute(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """执行 SQL 查询"""
        if not self._connected:
            raise ConnectorError("Not connected to database")

        try:
            rows = await self._connection.fetch(query, *(params or {}).values())
            return [dict(row) for row in rows]
        except Exception as e:
            raise ConnectorError(f"Query execution failed: {e}")

    async def get_schema(self) -> Dict[str, Any]:
        """获取数据库表结构"""
        query = """
        SELECT table_name, column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
        """
        rows = await self._connection.fetch(query)

        schema = {}
        for row in rows:
            table = row['table_name']
            if table not in schema:
                schema[table] = []
            schema[table].append({
                "name": row['column_name'],
                "type": row['data_type'],
                "nullable": row['is_nullable'] == 'YES'
            })
        return {"tables": schema}
