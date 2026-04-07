"""
SQL Server 数据库连接器
"""
import asyncio
from typing import Any, Dict, List, Optional
from connectors.base import BaseConnector, ConnectorConfig, ConnectorError
from utils.logger import logger


class SQLServerConnector(BaseConnector):
    """Microsoft SQL Server 数据库连接器"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._connection = None
        self._cursor = None

    async def connect(self) -> None:
        """建立 SQL Server 连接"""
        try:
            import pyodbc
            parsed = self._parse_connection_string()

            # 构建 ODBC 连接字符串
            connection_string = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={parsed.get('host', 'localhost')},{parsed.get('port', 1433)};"
                f"DATABASE={parsed.get('database', 'master')};"
                f"UID={parsed.get('user')};"
                f"PWD={parsed.get('password')};"
            )

            # 可选参数
            if parsed.get('trusted_connection'):
                connection_string = (
                    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                    f"SERVER={parsed.get('host', 'localhost')},{parsed.get('port', 1433)};"
                    f"DATABASE={parsed.get('database', 'master')};"
                    f"Trusted_Connection=yes;"
                )

            self._connection = pyodbc.connect(connection_string)
            self._cursor = self._connection.cursor()
            self._connected = True
            logger.info(f"Connected to SQL Server: {parsed.get('host')}:{parsed.get('port')}")
        except Exception as e:
            raise ConnectorError(f"Failed to connect to SQL Server: {e}")

    async def disconnect(self) -> None:
        """断开 SQL Server 连接"""
        if self._cursor:
            self._cursor.close()
        if self._connection:
            self._connection.close()
        self._connected = False

    async def execute(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """执行 SQL 查询"""
        if not self._connected:
            raise ConnectorError("Not connected to SQL Server")

        try:
            if params:
                self._cursor.execute(query, params)
            else:
                self._cursor.execute(query)

            columns = [column[0] for column in self._cursor.description]
            rows = self._cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            raise ConnectorError(f"Query execution failed: {e}")

    async def get_schema(self) -> Dict[str, Any]:
        """获取数据库表结构"""
        try:
            # 获取所有表和 schema
            self._cursor.execute("""
                SELECT TABLE_SCHEMA, TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_TYPE = 'BASE TABLE'
                AND TABLE_SCHEMA NOT IN ('sys', 'INFORMATION_SCHEMA')
                ORDER BY TABLE_SCHEMA, TABLE_NAME
            """)
            tables = self._cursor.fetchall()

            schema = {}
            for table_schema, table_name in tables:
                key = f"{table_schema}.{table_name}"
                self._cursor.execute(f"""
                    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = '{table_schema}' AND TABLE_NAME = '{table_name}'
                    ORDER BY ORDINAL_POSITION
                """)
                columns = self._cursor.fetchall()
                schema[key] = {
                    "schema": table_schema,
                    "name": table_name,
                    "columns": [
                        {"name": col[0], "type": col[1], "nullable": col[2] == 'YES'}
                        for col in columns
                    ]
                }
            return {"tables": schema}
        except Exception as e:
            raise ConnectorError(f"Failed to get schema: {e}")

    def _parse_connection_string(self) -> Dict[str, Any]:
        """
        解析 SQL Server 连接字符串
        格式：sqlserver://user:password@host:port/database?trusted_connection=no
        """
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.config.connection_string)
        query_params = parse_qs(parsed.query)

        return {
            'user': parsed.username or '',
            'password': parsed.password or '',
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 1433,
            'database': parsed.path.strip('/') or 'master',
            'trusted_connection': query_params.get('trusted_connection', ['no'])[0].lower() == 'true'
        }


__all__ = ["SQLServerConnector"]
