"""
Oracle 数据库连接器
"""
import asyncio
from typing import Any, Dict, List, Optional
from connectors.base import BaseConnector, ConnectorConfig, ConnectorError
from utils.logger import logger


class OracleConnector(BaseConnector):
    """Oracle 数据库连接器"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._connection = None
        self._cursor = None

    async def connect(self) -> None:
        """建立 Oracle 连接"""
        try:
            import cx_Oracle
            parsed = self._parse_connection_string()

            # 创建 DSN
            dsn = cx_Oracle.makedsn(
                host=parsed.get('host', 'localhost'),
                port=int(parsed.get('port', 1521)),
                service_name=parsed.get('service_name') or parsed.get('sid')
            )

            self._connection = cx_Oracle.connect(
                user=parsed.get('user'),
                password=parsed.get('password'),
                dsn=dsn
            )
            self._cursor = self._connection.cursor()
            self._connected = True
            logger.info(f"Connected to Oracle: {parsed.get('service_name') or parsed.get('sid')}")
        except Exception as e:
            raise ConnectorError(f"Failed to connect to Oracle: {e}")

    async def disconnect(self) -> None:
        """断开 Oracle 连接"""
        if self._cursor:
            self._cursor.close()
        if self._connection:
            self._connection.close()
        self._connected = False

    async def execute(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """执行 SQL 查询"""
        if not self._connected:
            raise ConnectorError("Not connected to Oracle")

        try:
            self._cursor.execute(query, params or {})
            columns = [desc[0].lower() for desc in self._cursor.description]
            rows = self._cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            raise ConnectorError(f"Query execution failed: {e}")

    async def get_schema(self) -> Dict[str, Any]:
        """获取数据库表结构"""
        try:
            # 获取所有表
            self._cursor.execute("""
                SELECT table_name, owner
                FROM all_tables
                WHERE owner NOT IN ('SYS', 'SYSTEM', 'DBSNMP', 'SYSMAN', 'OUTLN', 'APEX_*')
                ORDER BY owner, table_name
            """)
            tables = self._cursor.fetchall()

            schema = {}
            for table_name, owner in tables:
                key = f"{owner}.{table_name}"
                self._cursor.execute(f"""
                    SELECT column_name, data_type, nullable
                    FROM all_tab_columns
                    WHERE owner = '{owner}' AND table_name = '{table_name}'
                    ORDER BY column_id
                """)
                columns = self._cursor.fetchall()
                schema[key] = {
                    "schema": owner,
                    "name": table_name,
                    "columns": [
                        {"name": col[0], "type": col[1], "nullable": col[2] == 'Y'}
                        for col in columns
                    ]
                }
            return {"tables": schema}
        except Exception as e:
            raise ConnectorError(f"Failed to get schema: {e}")

    def _parse_connection_string(self) -> Dict[str, str]:
        """
        解析 Oracle 连接字符串
        格式：oracle://user:password@host:port/service_name
        或：oracle://user:password@host:port:sid
        """
        from urllib.parse import urlparse
        parsed = urlparse(self.config.connection_string)

        path_parts = parsed.path.strip('/').split('/')
        service_name = path_parts[0] if path_parts else None

        # 检查是否是 SID 格式
        if ':' in (parsed.path.strip('/')):
            parts = parsed.path.strip('/').split(':')
            service_name = parts[1] if len(parts) > 1 else parts[0]

        return {
            'user': parsed.username or '',
            'password': parsed.password or '',
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 1521,
            'service_name': service_name,
            'sid': None  # 支持 SID 格式
        }


__all__ = ["OracleConnector"]
