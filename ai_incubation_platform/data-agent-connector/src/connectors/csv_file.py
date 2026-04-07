"""
CSV 文件连接器
"""
import asyncio
import csv
import os
from typing import Any, Dict, List, Optional
from connectors.base import BaseConnector, ConnectorConfig, ConnectorError
from utils.logger import logger


class CSVConnector(BaseConnector):
    """CSV 文件连接器"""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._base_path = None
        self._current_file = None
        self._schema_cache = {}

    async def connect(self) -> None:
        """建立 CSV 连接（验证路径）"""
        try:
            parsed = self._parse_connection_string()
            self._base_path = parsed.get('path', './data/csv')

            if not os.path.exists(self._base_path):
                os.makedirs(self._base_path, exist_ok=True)

            self._connected = True
            logger.info(f"CSV connector ready, base path: {self._base_path}")
        except Exception as e:
            raise ConnectorError(f"Failed to connect to CSV path: {e}")

    async def disconnect(self) -> None:
        """断开 CSV 连接"""
        self._current_file = None
        self._schema_cache.clear()
        self._connected = False

    async def execute(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """
        执行 CSV 查询
        查询格式：
        - "SELECT * FROM filename.csv" - 读取文件
        - "SELECT column1, column2 FROM filename.csv WHERE condition" - 带条件查询
        - "INSERT INTO filename.csv VALUES (...)" - 写入数据
        - "DESCRIBE filename.csv" - 查看文件结构
        """
        if not self._connected:
            raise ConnectorError("CSV connector not connected")

        query_upper = query.upper().strip()

        try:
            # 解析查询
            if query_upper.startswith("SELECT "):
                return await self._select(query, params)
            elif query_upper.startswith("INSERT INTO "):
                return await self._insert(query, params)
            elif query_upper.startswith("DESCRIBE "):
                return await self._describe(query)
            else:
                raise ConnectorError(f"Unknown CSV query: {query}")
        except Exception as e:
            raise ConnectorError(f"CSV query execution failed: {e}")

    async def _select(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """执行 SELECT 查询"""
        import re

        # 解析 FROM 子句
        from_match = re.search(r'FROM\s+([^\s]+)', query, re.IGNORECASE)
        if not from_match:
            raise ConnectorError("Invalid query: missing FROM clause")

        filename = from_match.group(1)
        filepath = os.path.join(self._base_path, filename)

        if not os.path.exists(filepath):
            raise ConnectorError(f"File not found: {filepath}")

        # 解析 SELECT 列
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', query, re.IGNORECASE)
        columns = None
        if select_match:
            select_str = select_match.group(1).strip()
            if select_str != '*':
                columns = [c.strip() for c in select_str.split(',')]

        # 解析 WHERE 条件
        where_match = re.search(r'WHERE\s+(.+?)(?:\s+LIMIT|\s+ORDER|$)', query, re.IGNORECASE)
        where_condition = None
        if where_match:
            where_condition = where_match.group(1).strip()

        # 解析 LIMIT
        limit_match = re.search(r'LIMIT\s+(\d+)', query, re.IGNORECASE)
        limit = None
        if limit_match:
            limit = int(limit_match.group(1))

        # 读取 CSV 文件
        results = []
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 应用 WHERE 条件
                if where_condition and not self._evaluate_condition(row, where_condition, params):
                    continue

                # 选择列
                if columns:
                    row = {k: v for k, v in row.items() if k in columns}

                results.append(row)

                # 应用 LIMIT
                if limit and len(results) >= limit:
                    break

        return results

    async def _insert(self, query: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
        """执行 INSERT 查询"""
        import re

        # 解析 INSERT INTO filename.csv VALUES
        insert_match = re.search(r'INSERT INTO\s+([^\s]+)\s+VALUES\s*\((.+)\)', query, re.IGNORECASE)
        if not insert_match:
            raise ConnectorError("Invalid INSERT query")

        filename = insert_match.group(1)
        values_str = insert_match.group(2)

        # 解析值
        values = [v.strip().strip("'\"") for v in values_str.split(',')]

        filepath = os.path.join(self._base_path, filename)

        # 获取表头
        file_exists = os.path.exists(filepath)
        if file_exists:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader)
        else:
            # 从 params 获取列名
            if params and 'columns' in params:
                headers = params['columns']
            else:
                headers = [f"column_{i}" for i in range(len(values))]

        # 写入数据
        with open(filepath, 'a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(headers)
            writer.writerow(values[:len(headers)])

        return [{"status": "inserted", "rows": 1}]

    async def _describe(self, query: str) -> List[Dict[str, Any]]:
        """描述 CSV 文件结构"""
        import re

        describe_match = re.search(r'DESCRIBE\s+([^\s]+)', query, re.IGNORECASE)
        if not describe_match:
            raise ConnectorError("Invalid DESCRIBE query")

        filename = describe_match.group(1)
        filepath = os.path.join(self._base_path, filename)

        if not os.path.exists(filepath):
            raise ConnectorError(f"File not found: {filepath}")

        # 读取文件结构
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)

            # 采样几行来推断类型
            sample_rows = []
            for i, row in enumerate(reader):
                if i >= 10:
                    break
                sample_rows.append(row)

        # 推断列类型
        column_types = {}
        for i, header in enumerate(headers):
            types_in_column = [self._infer_type(row[i]) for row in sample_rows if i < len(row)]
            if all(t == 'integer' for t in types_in_column):
                column_types[header] = 'integer'
            elif all(t in ('integer', 'number') for t in types_in_column):
                column_types[header] = 'number'
            else:
                column_types[header] = 'string'

        return [{
            "filename": filename,
            "columns": [
                {"name": h, "type": column_types.get(h, 'string')}
                for h in headers
            ],
            "row_count": len(sample_rows)
        }]

    def _evaluate_condition(self, row: Dict[str, str], condition: str, params: Optional[dict] = None) -> bool:
        """评估 WHERE 条件"""
        import re

        # 替换列名引用
        def replace_column(match):
            col_name = match.group(1)
            value = row.get(col_name, '')
            if value is None:
                return 'NULL'
            # 尝试转换为数字
            try:
                if '.' in value:
                    return str(float(value))
                return str(int(value))
            except ValueError:
                return f"'{value}'"

        # 简单条件解析
        parsed_condition = condition
        for col_name in row.keys():
            parsed_condition = re.sub(
                rf'\b{re.escape(col_name)}\b',
                lambda m: f"'{row.get(col_name, '')}'" if not row.get(col_name, '').isdigit() else row.get(col_name, ''),
                parsed_condition
            )

        # 替换比较运算符
        parsed_condition = parsed_condition.replace('=', '==')
        parsed_condition = parsed_condition.replace('!=', '<>')
        parsed_condition = parsed_condition.replace('<>', '!=')

        try:
            # 安全评估
            result = eval(parsed_condition, {"__builtins__": {}}, {})
            return bool(result)
        except Exception:
            return False

    def _infer_type(self, value: str) -> str:
        """推断值类型"""
        if not value:
            return 'null'
        try:
            int(value)
            return 'integer'
        except ValueError:
            pass
        try:
            float(value)
            return 'number'
        except ValueError:
            pass
        return 'string'

    async def get_schema(self) -> Dict[str, Any]:
        """获取 CSV 目录下的所有文件结构"""
        try:
            schema = {}
            for filename in os.listdir(self._base_path):
                if filename.endswith('.csv'):
                    filepath = os.path.join(self._base_path, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        headers = next(reader)
                        row_count = sum(1 for _ in reader)

                    schema[filename] = {
                        "type": "csv",
                        "columns": [{"name": h, "type": "string"} for h in headers],
                        "row_count": row_count
                    }

            return {"files": schema}
        except Exception as e:
            raise ConnectorError(f"Failed to get CSV schema: {e}")

    def _parse_connection_string(self) -> Dict[str, str]:
        """
        解析 CSV 连接字符串
        格式：csv:///path/to/csv/files
        """
        from urllib.parse import urlparse
        parsed = urlparse(self.config.connection_string)
        return {
            'path': parsed.path or './data/csv'
        }


__all__ = ["CSVConnector"]
