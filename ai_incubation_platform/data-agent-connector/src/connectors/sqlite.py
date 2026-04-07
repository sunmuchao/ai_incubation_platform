"""
SQLite 数据库连接器
"""
from typing import Any, Dict, List, Optional
import aiosqlite
from connectors.base import BaseConnector, ConnectorConfig, ConnectorError


class SQLiteConnector(BaseConnector):
    """SQLite 数据库连接器"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._connection = None

    async def connect(self) -> None:
        """建立 SQLite 连接"""
        try:
            # SQLite连接字符串格式: sqlite:///path/to/database.db
            db_path = self.config.connection_string.replace('sqlite:///', '')
            self._connection = await aiosqlite.connect(db_path)
            self._connection.row_factory = aiosqlite.Row
            self._connected = True
        except Exception as e:
            raise ConnectorError(f"Failed to connect to SQLite: {e}")

    async def disconnect(self) -> None:
        """断开 SQLite 连接"""
        if self._connection:
            await self._connection.close()
        self._connected = False

    async def execute(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """执行 SQL 查询"""
        if not self._connected:
            raise ConnectorError("Not connected to database")

        try:
            cursor = await self._connection.execute(query, params or ())
            if query.strip().upper().startswith(('SELECT', 'PRAGMA')):
                rows = await cursor.fetchall()
                result = [dict(row) for row in rows]
                await cursor.close()
                return result
            else:
                await self._connection.commit()
                result = [{"rows_affected": cursor.rowcount, "last_insert_id": cursor.lastrowid}]
                await cursor.close()
                return result
        except Exception as e:
            await self._connection.rollback()
            raise ConnectorError(f"Query execution failed: {e}")

    async def get_schema(self) -> Dict[str, Any]:
        """获取数据库表结构"""
        if not self._connected:
            raise ConnectorError("Not connected to database")

        try:
            # 获取所有表
            cursor = await self._connection.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = [row[0] for row in await cursor.fetchall()]
            await cursor.close()

            schema = {}
            for table in tables:
                cursor = await self._connection.execute(f"PRAGMA table_info({table})")
                columns = await cursor.fetchall()
                schema[table] = [
                    {
                        "name": col[1],
                        "type": col[2],
                        "nullable": col[3] == 0,
                        "primary_key": col[5] == 1
                    }
                    for col in columns
                ]
                await cursor.close()

            return {"tables": schema}
        except Exception as e:
            raise ConnectorError(f"Failed to get schema: {e}")


# 导出
__all__ = ["SQLiteConnector"]
