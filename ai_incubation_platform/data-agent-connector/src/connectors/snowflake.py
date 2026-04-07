"""
Snowflake 数据仓库连接器
"""
import asyncio
from typing import Any, Dict, List, Optional
from connectors.base import BaseConnector, ConnectorConfig, ConnectorError
from utils.logger import logger


class SnowflakeConnector(BaseConnector):
    """Snowflake 数据仓库连接器"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._connection = None
        self._cursor = None

    async def connect(self) -> None:
        """建立 Snowflake 连接"""
        try:
            import snowflake.connector
            parsed = self._parse_connection_string()

            # Snowflake 连接参数
            self._connection = snowflake.connector.connect(
                user=parsed.get('user'),
                password=parsed.get('password'),
                account=parsed.get('account'),
                database=parsed.get('database'),
                schema=parsed.get('schema', 'PUBLIC'),
                warehouse=parsed.get('warehouse'),
                role=parsed.get('role', 'PUBLIC')
            )
            self._cursor = self._connection.cursor()
            self._connected = True
            logger.info(f"Connected to Snowflake account: {parsed.get('account')}")
        except Exception as e:
            raise ConnectorError(f"Failed to connect to Snowflake: {e}")

    async def disconnect(self) -> None:
        """断开 Snowflake 连接"""
        if self._cursor:
            self._cursor.close()
        if self._connection:
            self._connection.close()
        self._connected = False

    async def execute(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """执行 SQL 查询"""
        if not self._connected:
            raise ConnectorError("Not connected to Snowflake")

        try:
            self._cursor.execute(query, params or {})
            columns = [desc[0] for desc in self._cursor.description] if self._cursor.description else []
            rows = self._cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            raise ConnectorError(f"Query execution failed: {e}")

    async def get_schema(self) -> Dict[str, Any]:
        """获取数据库表结构"""
        try:
            # 获取所有表
            self._cursor.execute("""
                SELECT table_name, table_schema
                FROM information_schema.tables
                WHERE table_schema NOT IN ('INFORMATION_SCHEMA', 'PG_CATALOG')
                ORDER BY table_schema, table_name
            """)
            tables = self._cursor.fetchall()

            schema = {}
            for table_name, table_schema in tables:
                key = f"{table_schema}.{table_name}"
                self._cursor.execute(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = '{table_schema}' AND table_name = '{table_name}'
                    ORDER BY ordinal_position
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

    def _parse_connection_string(self) -> Dict[str, str]:
        """
        解析连接字符串
        格式：snowflake://user:password@account/warehouse/database/schema?role=role_name
        """
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.config.connection_string)
        query_params = parse_qs(parsed.query)

        # Snowflake 账号格式可能是：account_id.region.cloud_platform
        account = parsed.hostname or ''
        if parsed.netloc and '@' in parsed.netloc:
            # user:pass@account 格式
            account = parsed.netloc.split('@')[-1]

        return {
            'user': parsed.username or '',
            'password': parsed.password or '',
            'account': account.split('/')[0] if account else '',
            'warehouse': parsed.path.split('/')[1] if len(parsed.path.split('/')) > 1 else (query_params.get('warehouse', [''])[0]),
            'database': parsed.path.split('/')[2] if len(parsed.path.split('/')) > 2 else (query_params.get('database', [''])[0]),
            'schema': parsed.path.split('/')[3] if len(parsed.path.split('/')) > 3 else (query_params.get('schema', ['PUBLIC'])[0]),
            'role': query_params.get('role', ['PUBLIC'])[0]
        }


# 导出连接器类
__all__ = ["SnowflakeConnector"]
