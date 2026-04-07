"""
Databricks 统一分析引擎连接器
"""
import asyncio
from typing import Any, Dict, List, Optional
from connectors.base import BaseConnector, ConnectorConfig, ConnectorError
from utils.logger import logger


class DatabricksConnector(BaseConnector):
    """Databricks 统一分析引擎连接器"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._connection = None
        self._cursor = None

    async def connect(self) -> None:
        """建立 Databricks 连接"""
        try:
            import databricks.sql
            parsed = self._parse_connection_string()

            # Databricks 连接参数
            self._connection = databricks.sql.connect(
                server_hostname=parsed.get('server_hostname'),
                http_path=parsed.get('http_path'),
                access_token=parsed.get('access_token'),
                catalog=parsed.get('catalog', 'hive_metastore'),
                schema=parsed.get('schema', 'default'),
                _user_agent_entry='data-agent-connector'
            )
            self._cursor = self._connection.cursor()
            self._connected = True

            logger.info(f"Connected to Databricks: {parsed.get('server_hostname')}")

        except Exception as e:
            raise ConnectorError(f"Failed to connect to Databricks: {e}")

    async def disconnect(self) -> None:
        """断开 Databricks 连接"""
        if self._cursor:
            self._cursor.close()
        if self._connection:
            self._connection.close()
        self._connected = False

    async def execute(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """执行 SQL 查询"""
        if not self._connected:
            raise ConnectorError("Not connected to Databricks")

        try:
            loop = asyncio.get_event_loop()

            def run_query():
                cursor = self._connection.cursor()
                cursor.execute(query, params or {})

                # 获取列名
                columns = [desc[0] for desc in cursor.description] if cursor.description else []

                # 获取结果
                rows = cursor.fetchall()
                result = [dict(zip(columns, row)) for row in rows]
                cursor.close()
                return result

            return await loop.run_in_executor(None, run_query)

        except Exception as e:
            raise ConnectorError(f"Query execution failed: {e}")

    async def get_schema(self) -> Dict[str, Any]:
        """获取数据库表结构"""
        try:
            loop = asyncio.get_event_loop()

            def get_schema():
                cursor = self._connection.cursor()

                # 获取所有表
                cursor.catalogs()
                catalogs = [row[0] for row in cursor.fetchall()]

                schema = {}

                for catalog in catalogs:
                    if catalog in ('system', 'information_schema'):
                        continue

                    # 获取该 catalog 下的 schemas
                    cursor.schemas(catalog=catalog)
                    schemas_result = cursor.fetchall()

                    for schema_name in [s[0] for s in schemas_result]:
                        if schema_name in ('information_schema', 'sys'):
                            continue

                        # 获取该 schema 下的表
                        cursor.tables(catalog=catalog, schema=schema_name)
                        tables_result = cursor.fetchall()

                        for table_info in tables_result:
                            table_name = table_info[0]
                            table_type = table_info[3] if len(table_info) > 3 else 'TABLE'

                            key = f"{catalog}.{schema_name}.{table_name}"

                            # 获取列信息
                            cursor.columns(catalog=catalog, schema=schema_name, table_name=table_name)
                            columns_result = cursor.fetchall()

                            columns = []
                            for col in columns_result:
                                columns.append({
                                    "name": col[3],  # COLUMN_NAME
                                    "type": col[5],  # TYPE_NAME
                                    "nullable": col[10] == 1 if len(col) > 10 else True,  # NULLABLE
                                    "comment": col[12] if len(col) > 12 else None  # REMARKS
                                })

                            schema[key] = {
                                "catalog": catalog,
                                "schema": schema_name,
                                "name": table_name,
                                "columns": columns,
                                "table_type": table_type
                            }

                cursor.close()
                return {"tables": schema}

            return await loop.run_in_executor(None, get_schema)

        except Exception as e:
            raise ConnectorError(f"Failed to get schema: {e}")

    def _parse_connection_string(self) -> Dict[str, str]:
        """
        解析 Databricks 连接字符串
        格式：databricks://server_hostname/http_path?access_token=token&catalog=hive_metastore&schema=default
        """
        from urllib.parse import urlparse, parse_qs

        parsed = urlparse(self.config.connection_string)
        query_params = parse_qs(parsed.query)

        return {
            'server_hostname': parsed.hostname or '',
            'http_path': parsed.path.lstrip('/') or query_params.get('http_path', [''])[0],
            'access_token': query_params.get('access_token', [''])[0],
            'catalog': query_params.get('catalog', ['hive_metastore'])[0],
            'schema': query_params.get('schema', ['default'])[0]
        }

    async def get_cluster_info(self) -> Dict[str, Any]:
        """获取集群信息"""
        try:
            loop = asyncio.get_event_loop()

            def get_info():
                cursor = self._connection.cursor()

                # 获取 Spark 版本等信息
                cursor.execute("SELECT version()")
                version_result = cursor.fetchone()

                # 获取当前数据库信息
                cursor.execute("SELECT current_database()")
                db_result = cursor.fetchone()

                cursor.close()

                return {
                    "version": version_result[0] if version_result else None,
                    "current_database": db_result[0] if db_result else None
                }

            return await loop.run_in_executor(None, get_info)

        except Exception as e:
            logger.warning(f"Failed to get cluster info: {e}")
            return {}

    async def get_tables_in_schema(self, catalog: str, schema: str) -> List[Dict[str, Any]]:
        """获取指定 schema 下的所有表"""
        try:
            loop = asyncio.get_event_loop()

            def get_tables():
                cursor = self._connection.cursor()
                cursor.tables(catalog=catalog, schema=schema)
                tables_result = cursor.fetchall()

                tables = []
                for table_info in tables_result:
                    tables.append({
                        "table_name": table_info[0],
                        "table_type": table_info[3] if len(table_info) > 3 else 'TABLE',
                        "remarks": table_info[7] if len(table_info) > 7 else None
                    })

                cursor.close()
                return tables

            return await loop.run_in_executor(None, get_tables)

        except Exception as e:
            raise ConnectorError(f"Failed to get tables: {e}")

    async def describe_table(self, table_full_name: str) -> Dict[str, Any]:
        """
        获取表详细信息
        参数 table_full_name 格式：catalog.schema.table
        """
        try:
            loop = asyncio.get_event_loop()

            def describe():
                cursor = self._connection.cursor()

                # 解析表名
                parts = table_full_name.split('.')
                if len(parts) != 3:
                    raise ValueError("Table name must be in format: catalog.schema.table")

                catalog, schema, table = parts

                # DESCRIBE EXTENDED 获取详细信息
                cursor.execute(f"DESCRIBE EXTENDED {table_full_name}")
                describe_result = cursor.fetchall()

                # 获取列信息
                cursor.columns(catalog=catalog, schema=schema, table_name=table)
                columns_result = cursor.fetchall()

                columns = []
                for col in columns_result:
                    columns.append({
                        "name": col[3],
                        "type": col[5],
                        "nullable": col[10] == 1 if len(col) > 10 else True,
                        "comment": col[12] if len(col) > 12 else None
                    })

                # 解析 DESCRIBE EXTENDED 结果
                table_details = {"columns": columns}
                for row in describe_result:
                    if len(row) >= 2:
                        key = row[0]
                        value = row[1]
                        if key not in ('# col_name', '# Detailed Table Information'):
                            table_details[key] = value

                cursor.close()
                return table_details

            return await loop.run_in_executor(None, describe)

        except Exception as e:
            raise ConnectorError(f"Failed to describe table: {e}")

    async def execute_statement(self, statement: str) -> Dict[str, Any]:
        """
        执行 DDL/DML 语句（非查询）
        返回执行结果统计
        """
        if not self._connected:
            raise ConnectorError("Not connected to Databricks")

        try:
            loop = asyncio.get_event_loop()

            def run_statement():
                cursor = self._connection.cursor()
                cursor.execute(statement)

                result = {
                    "rowcount": cursor.rowcount,
                    "description": str(cursor.description) if cursor.description else None
                }

                # 如果是查询，返回第一行
                if cursor.description:
                    result["first_row"] = cursor.fetchone()

                cursor.close()
                return result

            return await loop.run_in_executor(None, run_statement)

        except Exception as e:
            raise ConnectorError(f"Statement execution failed: {e}")


# 导出连接器类
__all__ = ["DatabricksConnector"]
