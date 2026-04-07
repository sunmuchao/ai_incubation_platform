"""
BigQuery 数据仓库连接器
"""
import asyncio
from typing import Any, Dict, List, Optional
from connectors.base import BaseConnector, ConnectorConfig, ConnectorError
from utils.logger import logger


class BigQueryConnector(BaseConnector):
    """Google BigQuery 数据仓库连接器"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._client = None
        self._project = None
        self._dataset = None

    async def connect(self) -> None:
        """建立 BigQuery 连接"""
        try:
            from google.cloud import bigquery
            from google.oauth2 import service_account

            parsed = self._parse_connection_string()

            # 解析认证方式
            credentials = None
            if parsed.get('credentials_path'):
                # 使用服务账号密钥文件
                credentials = service_account.Credentials.from_service_account_file(
                    parsed['credentials_path']
                )
            elif parsed.get('credentials_json'):
                # 使用服务账号 JSON 字符串
                import json
                import tempfile
                import os

                # 将 JSON 写入临时文件
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    f.write(parsed['credentials_json'])
                    temp_path = f.name

                try:
                    credentials = service_account.Credentials.from_service_account_file(temp_path)
                finally:
                    os.unlink(temp_path)

            # 创建 BigQuery 客户端
            self._client = bigquery.Client(
                project=parsed.get('project'),
                credentials=credentials
            )
            self._project = parsed.get('project')
            self._dataset = parsed.get('dataset')

            # 测试连接
            await asyncio.get_event_loop().run_in_executor(None, lambda: list(self._client.list_datasets(max_results=1)))

            self._connected = True
            logger.info(f"Connected to BigQuery project: {self._project}")
        except Exception as e:
            raise ConnectorError(f"Failed to connect to BigQuery: {e}")

    async def disconnect(self) -> None:
        """断开 BigQuery 连接"""
        if self._client:
            self._client.close()
        self._connected = False

    async def execute(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """执行 SQL 查询"""
        if not self._connected:
            raise ConnectorError("Not connected to BigQuery")

        try:
            loop = asyncio.get_event_loop()

            # 配置查询参数
            job_config = None
            if params:
                from google.cloud import bigquery
                job_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter(key, self._infer_type(value), value)
                        for key, value in params.items()
                    ]
                )

            # 执行查询
            def run_query():
                query_job = self._client.query(query, job_config=job_config)
                return list(query_job.result())

            rows = await loop.run_in_executor(None, run_query)

            # 转换为字典列表
            result = []
            for row in rows:
                row_dict = {}
                for key in row.keys():
                    value = getattr(row, key)
                    # 处理特殊类型
                    if hasattr(value, 'isoformat'):
                        value = value.isoformat()
                    elif isinstance(value, bytes):
                        value = value.decode('utf-8')
                    row_dict[key] = value
                result.append(row_dict)

            logger.debug(f"BigQuery query returned {len(result)} rows")
            return result

        except Exception as e:
            raise ConnectorError(f"Query execution failed: {e}")

    def _infer_type(self, value: Any) -> str:
        """推断参数类型用于 BigQuery 参数化查询"""
        if value is None:
            return "STRING"
        elif isinstance(value, bool):
            return "BOOL"
        elif isinstance(value, int):
            return "INT64"
        elif isinstance(value, float):
            return "FLOAT64"
        elif isinstance(value, str):
            return "STRING"
        elif hasattr(value, 'isoformat'):
            return "TIMESTAMP"
        else:
            return "STRING"

    async def get_schema(self) -> Dict[str, Any]:
        """获取数据集表结构"""
        try:
            loop = asyncio.get_event_loop()

            # 获取所有表
            def list_tables():
                dataset_ref = self._client.dataset(self._dataset) if self._dataset else None
                if dataset_ref:
                    return list(self._client.list_tables(dataset_ref))
                else:
                    # 如果没有指定数据集，列出所有数据集的表
                    tables = []
                    for dataset in self._client.list_datasets():
                        for table in self._client.list_tables(dataset):
                            tables.append(table)
                    return tables

            tables = await loop.run_in_executor(None, list_tables)

            schema = {}
            for table_ref in tables:
                table_id = f"{table_ref.project}.{table_ref.dataset_id}.{table_ref.table_id}"

                # 获取表详情
                def get_table_details():
                    table = self._client.get_table(table_ref)
                    columns = []
                    for field in table.schema:
                        col_info = {
                            "name": field.name,
                            "type": field.field_type,
                            "nullable": field.is_nullable,
                            "mode": field.mode  # NULLABLE, REQUIRED, REPEATED
                        }
                        if field.description:
                            col_info["description"] = field.description
                        columns.append(col_info)

                    return {
                        "schema": table_ref.dataset_id,
                        "name": table_ref.table_id,
                        "columns": columns,
                        "row_count": table.num_rows if table.num_rows else 0,
                        "created": str(table.created) if table.created else None,
                        "description": table.description if hasattr(table, 'description') else None
                    }

                schema[table_id] = await loop.run_in_executor(None, get_table_details)

            return {"tables": schema}

        except Exception as e:
            raise ConnectorError(f"Failed to get schema: {e}")

    def _parse_connection_string(self) -> Dict[str, str]:
        """
        解析 BigQuery 连接字符串
        格式：
        - bigquery://project/dataset?credentials_path=/path/to/credentials.json
        - bigquery://project/dataset?credentials_json={json_string}
        """
        from urllib.parse import urlparse, parse_qs

        parsed = urlparse(self.config.connection_string)
        query_params = parse_qs(parsed.query)

        # 处理 credentials_json 参数（可能需要 URL 解码）
        credentials_json = None
        if 'credentials_json' in query_params:
            import urllib.parse
            credentials_json = urllib.parse.unquote(query_params['credentials_json'][0])

        return {
            'project': parsed.hostname or (parsed.path.split('/')[1] if len(parsed.path.split('/')) > 1 else ''),
            'dataset': parsed.path.split('/')[2] if len(parsed.path.split('/')) > 2 else (query_params.get('dataset', [''])[0] or self._dataset),
            'credentials_path': query_params.get('credentials_path', [''])[0],
            'credentials_json': credentials_json
        }

    async def get_table_details(self, table_id: str) -> Dict[str, Any]:
        """获取单个表的详细信息"""
        try:
            from google.cloud import bigquery

            # 解析表 ID
            parts = table_id.split('.')
            if len(parts) == 3:
                project, dataset, table_name = parts
                table_ref = bigquery.TableReference(
                    bigquery.DatasetReference(project, dataset),
                    table_name
                )
            elif len(parts) == 2:
                dataset, table_name = parts
                table_ref = self._client.get_table(f"{self._project}.{dataset}.{table_name}")
            else:
                raise ConnectorError(f"Invalid table ID format: {table_id}")

            loop = asyncio.get_event_loop()

            def get_details():
                table = self._client.get_table(table_ref)
                return {
                    "full_table_id": f"{table.project}.{table.dataset_id}.{table.table_id}",
                    "schema": [
                        {
                            "name": field.name,
                            "type": field.field_type,
                            "nullable": field.is_nullable,
                            "mode": field.mode,
                            "description": field.description
                        }
                        for field in table.schema
                    ],
                    "row_count": table.num_rows,
                    "size_bytes": table.num_bytes,
                    "created": str(table.created) if table.created else None,
                    "modified": str(table.modified) if table.modified else None,
                    "description": table.description,
                    "labels": table.labels or {}
                }

            return await loop.run_in_executor(None, get_details)

        except Exception as e:
            raise ConnectorError(f"Failed to get table details: {e}")

    async def get_dataset_list(self) -> List[Dict[str, Any]]:
        """获取所有数据集列表"""
        try:
            loop = asyncio.get_event_loop()

            def list_datasets():
                datasets = []
                for dataset in self._client.list_datasets():
                    datasets.append({
                        "project": dataset.project,
                        "dataset_id": dataset.dataset_id,
                        "created": str(dataset.created) if dataset.created else None,
                        "description": dataset.description if hasattr(dataset, 'description') else None
                    })
                return datasets

            return await loop.run_in_executor(None, list_datasets)

        except Exception as e:
            raise ConnectorError(f"Failed to list datasets: {e}")

    async def query_dry_run(self, query: str) -> Dict[str, Any]:
        """
        执行查询预检（验证 SQL 语法并估算数据量）
        """
        try:
            loop = asyncio.get_event_loop()

            def dry_run():
                from google.cloud import bigquery
                job_config = bigquery.QueryJobConfig(dry_run=True)
                query_job = self._client.query(query, job_config=job_config)
                return {
                    "valid": True,
                    "total_bytes_processed": query_job.total_bytes_processed,
                    "estimated_cost_usd": query_job.total_bytes_processed * 5 / (1024 ** 4)  # $5 per TB
                }

            return await loop.run_in_executor(None, dry_run)

        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }


# 导出连接器类
__all__ = ["BigQueryConnector"]
