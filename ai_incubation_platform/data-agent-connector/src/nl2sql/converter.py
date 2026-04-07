"""
NL2SQL 转换器 - 自然语言转 SQL
"""
from typing import Optional, Dict, Any, List, Tuple
import re
import json
from datetime import datetime, timedelta
from utils.logger import logger
from config.settings import settings


class SchemaCache:
    """Schema 缓存管理器"""

    def __init__(self, ttl_seconds: int = 3600):
        self._cache: Dict[str, Tuple[Dict[str, Any], datetime]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)

    def get(self, connector_name: str) -> Optional[Dict[str, Any]]:
        """获取缓存的Schema"""
        if connector_name not in self._cache:
            return None

        schema, cached_at = self._cache[connector_name]
        if datetime.utcnow() - cached_at > self._ttl:
            # 缓存过期
            del self._cache[connector_name]
            return None

        return schema

    def set(self, connector_name: str, schema: Dict[str, Any]) -> None:
        """设置Schema缓存"""
        self._cache[connector_name] = (schema, datetime.utcnow())
        logger.debug(f"Schema cached for {connector_name}", extra={"ttl": self._ttl.total_seconds()})

    def invalidate(self, connector_name: str) -> None:
        """失效指定连接器的Schema缓存"""
        if connector_name in self._cache:
            del self._cache[connector_name]
            logger.debug(f"Schema cache invalidated for {connector_name}")

    def clear(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
        logger.debug("All schema cache cleared")

    @property
    def size(self) -> int:
        """获取缓存条目数量"""
        return len(self._cache)


class NL2SQLConverter:
    """自然语言转 SQL 转换器"""

    def __init__(self):
        self._schema_cache = SchemaCache()
        self._operator_patterns = [
            (r'(\w+)\s*大于\s*(\d+)', r'\1 > \2'),
            (r'(\w+)\s*小于\s*(\d+)', r'\1 < \2'),
            (r'(\w+)\s*等于\s*(\w+)', self._replace_equals),
            (r'(\w+)\s*是\s*(\w+)', self._replace_equals),
            (r'(\w+)\s*不等于\s*(\w+)', self._replace_not_equals),
            (r'(\w+)\s*不是\s*(\w+)', self._replace_not_equals),
            (r'(\w+)\s*大于等于\s*(\d+)', r'\1 >= \2'),
            (r'(\w+)\s*小于等于\s*(\d+)', r'\1 <= \2'),
            (r'(\w+)\s*包含\s*"([^"]+)"', r"\1 LIKE '%\2%'"),
            (r'(\w+)\s*包含\s*\'([^\']+)\'', r"\1 LIKE '%\2%'"),
            (r'(\w+)\s*以\s*"([^"]+)"\s*开头', r"\1 LIKE '\2%'"),
            (r'(\w+)\s*以\s*\'([^\']+)\'\s*开头', r"\1 LIKE '\2%'"),
            (r'(\w+)\s*以\s*"([^"]+)"\s*结尾', r"\1 LIKE '%\2'"),
            (r'(\w+)\s*以\s*\'([^\']+)\'\s*结尾', r"\1 LIKE '%\2'"),
        ]

        # 聚合函数映射
        self._aggregation_patterns = [
            (r'统计|总数|count\s*\(', 'COUNT(*)'),
            (r'总和|sum\s*\(', 'SUM({column})'),
            (r'平均|avg\s*\(', 'AVG({column})'),
            (r'最大|max\s*\(', 'MAX({column})'),
            (r'最小|min\s*\(', 'MIN({column})'),
        ]

        # 排序模式
        self._order_patterns = [
            (r'按\s*(\w+)\s*排序', r'ORDER BY \1 ASC'),
            (r'按\s*(\w+)\s*升序', r'ORDER BY \1 ASC'),
            (r'按\s*(\w+)\s*降序', r'ORDER BY \1 DESC'),
        ]

        # 同义词表
        self._synonyms = {
            '用户': ['用户', '人', 'user', 'person', '成员'],
            '部门': ['部门', '团队', 'group', 'team', '组织'],
            '订单': ['订单', 'order', '交易', 'purchase'],
            '产品': ['产品', '商品', 'product', 'item', 'goods'],
            '价格': ['价格', 'price', '金额', 'cost'],
            '时间': ['时间', 'date', 'time', '日期'],
            '状态': ['状态', 'status', 'state'],
        }

    @property
    def schema_cache(self) -> SchemaCache:
        """获取Schema缓存实例"""
        return self._schema_cache

    def register_schema(self, connector_name: str, schema: Dict[str, Any]) -> None:
        """注册连接器的Schema"""
        self._schema_cache.set(connector_name, schema)

    def convert(self, natural_language: str, connector_name: Optional[str] = None, context: Optional[dict] = None) -> str:
        """
        将自然语言转换为 SQL 查询

        支持的查询模式：
        - 基础查询："查询所有用户" → SELECT * FROM users
        - 条件查询："查询年龄大于 18 的用户" → SELECT * FROM users WHERE age > 18
        - 模糊查询："查询名字包含 '张' 的用户" → SELECT * FROM users WHERE name LIKE '%张%'
        - 聚合查询："统计用户总数" → SELECT COUNT(*) FROM users
        - 分组统计："按部门分组统计用户数量" → SELECT department, COUNT(*) FROM users GROUP BY department
        - 排序查询："按年龄降序排列用户" → SELECT * FROM users ORDER BY age DESC
        - 组合查询："查询年龄大于 18 并且部门是 '技术部' 的用户，按入职时间排序"
        """
        nl = natural_language.lower().strip()
        context = context or {}

        # 获取Schema
        schema = None
        if connector_name:
            schema = self._schema_cache.get(connector_name)

        if not schema:
            logger.warning("No schema available for NL2SQL conversion", extra={"connector_name": connector_name})
            # 使用上下文提供的Schema或默认Schema
            schema = context.get('schema', {})

        # 检测表名
        table = self._detect_table(nl, schema)

        # 检测查询类型和构建SQL
        sql_parts = {
            'select': '*',
            'from': table,
            'where': None,
            'group_by': None,
            'order_by': None,
            'limit': None
        }

        # 处理聚合查询
        select_clause, is_aggregation = self._extract_aggregation(nl, table, schema)
        if select_clause:
            sql_parts['select'] = select_clause

        # 处理分组
        group_by = self._extract_group_by(nl, table, schema)
        if group_by:
            sql_parts['group_by'] = group_by

        # 处理WHERE条件
        where_clause = self._extract_where(nl, table, schema)
        if where_clause:
            sql_parts['where'] = where_clause

        # 处理排序
        order_by = self._extract_order_by(nl, table, schema)
        if order_by:
            sql_parts['order_by'] = order_by

        # 处理LIMIT
        limit = self._extract_limit(nl)
        if limit:
            sql_parts['limit'] = limit

        # 构建完整SQL
        sql = self._build_sql(sql_parts)

        logger.info(
            "NL2SQL conversion completed",
            extra={
                "natural_language": natural_language,
                "sql": sql,
                "connector_name": connector_name
            }
        )

        return sql

    def _detect_table(self, nl: str, schema: Dict[str, Any]) -> str:
        """从自然语言中检测表名"""
        tables = schema.get('tables', {}).keys() if schema else []

        # 精确匹配
        for table in tables:
            if table.lower() in nl:
                return table

        # 同义词匹配
        for table in tables:
            synonyms = self._synonyms.get(table, [])
            if any(syn.lower() in nl for syn in synonyms):
                return table

        # 从上下文获取默认表
        if 'default_table' in schema:
            return schema['default_table']

        # 默认返回第一个表或users
        return list(tables)[0] if tables else "users"

    def _extract_aggregation(self, nl: str, table: str, schema: Dict[str, Any]) -> Tuple[str, bool]:
        """提取聚合函数"""
        columns = self._get_table_columns(table, schema)

        for pattern, agg_template in self._aggregation_patterns:
            if re.search(pattern, nl):
                # 查找相关的列
                agg_column = '*'
                for col in columns:
                    if col in nl or self._is_related(col, nl):
                        agg_column = col
                        break

                if '{column}' in agg_template:
                    return agg_template.format(column=agg_column), True
                return agg_template, True

        return '', False

    def _extract_group_by(self, nl: str, table: str, schema: Dict[str, Any]) -> Optional[str]:
        """提取GROUP BY子句"""
        if '分组' not in nl and 'group by' not in nl:
            return None

        columns = self._get_table_columns(table, schema)

        # 查找分组字段
        for col in columns:
            if col in nl or self._is_related(col, nl):
                return f"{col}, COUNT(*)" if '统计' in nl else col

        # 默认分组字段
        return "department, COUNT(*)" if '统计' in nl else "department"

    def _extract_where(self, nl: str, table: str, schema: Dict[str, Any]) -> Optional[str]:
        """提取WHERE条件"""
        conditions = []
        columns = self._get_table_columns(table, schema)

        # 处理各种操作符模式
        for pattern, replacement in self._operator_patterns:
            matches = list(re.finditer(pattern, nl))
            for match in matches:
                column = match.group(1)
                # 验证列名是否存在
                if columns and column not in columns:
                    # 尝试查找相关列
                    related_col = self._find_related_column(column, columns)
                    if related_col:
                        # 替换为实际列名
                        new_match = (match.group(0).replace(column, related_col),) + match.groups()[1:]
                        if callable(replacement):
                            cond = replacement(*new_match)
                        else:
                            cond = replacement.replace(r'\1', related_col)
                            for i in range(2, 10):
                                if f'\\{i}' in cond and len(new_match) > i:
                                    cond = cond.replace(f'\\{i}', new_match[i])
                        conditions.append(cond)
                else:
                    if callable(replacement):
                        cond = replacement(*match.groups())
                    else:
                        cond = match.expand(replacement)
                    conditions.append(cond)

        # 处理AND/OR逻辑
        if '并且' in nl or '且' in nl or 'and' in nl:
            return ' AND '.join(conditions)
        elif '或者' in nl or '或' in nl or 'or' in nl:
            return ' OR '.join(conditions)

        return ' AND '.join(conditions) if conditions else None

    def _extract_order_by(self, nl: str, table: str, schema: Dict[str, Any]) -> Optional[str]:
        """提取ORDER BY子句"""
        columns = self._get_table_columns(table, schema)

        for pattern, replacement in self._order_patterns:
            match = re.search(pattern, nl)
            if match:
                column = match.group(1)
                # 验证列名
                if columns and column not in columns:
                    related_col = self._find_related_column(column, columns)
                    if related_col:
                        return replacement.replace(r'\1', related_col)
                return match.expand(replacement)

        return None

    def _extract_limit(self, nl: str) -> Optional[str]:
        """提取LIMIT子句"""
        match = re.search(r'前\s*(\d+)\s*条|limit\s*(\d+)', nl)
        if match:
            limit = match.group(1) or match.group(2)
            return f"LIMIT {limit}"
        return None

    def _build_sql(self, parts: Dict[str, Any]) -> str:
        """构建完整SQL语句"""
        sql = f"SELECT {parts['select']} FROM {parts['from']}"

        if parts['where']:
            sql += f" WHERE {parts['where']}"

        if parts['group_by']:
            sql += f" GROUP BY {parts['group_by']}"

        if parts['order_by']:
            sql += f" {parts['order_by']}"

        if parts['limit']:
            sql += f" {parts['limit']}"

        return sql

    def _get_table_columns(self, table: str, schema: Dict[str, Any]) -> List[str]:
        """获取表的所有列名"""
        tables = schema.get('tables', {})
        if table not in tables:
            return []
        return [col['name'] for col in tables[table]]

    def _find_related_column(self, keyword: str, columns: List[str]) -> Optional[str]:
        """查找相关的列名"""
        keyword = keyword.lower()
        for col in columns:
            if col.lower() == keyword:
                return col
            if self._is_related(col, keyword):
                return col
        return None

    def _is_related(self, word: str, text: str) -> bool:
        """语义相关检测"""
        word_lower = word.lower()
        text_lower = text.lower()

        # 直接包含
        if word_lower in text_lower or text_lower in word_lower:
            return True

        # 同义词匹配
        for key, synonyms in self._synonyms.items():
            if word_lower in [s.lower() for s in synonyms]:
                return any(s.lower() in text_lower for s in synonyms)
            if text_lower in [s.lower() for s in synonyms]:
                return any(s.lower() in word_lower for s in synonyms)

        return False

    def _replace_equals(self, column: str, value: str) -> str:
        """替换等于条件"""
        if value.isdigit():
            return f"{column} = {value}"
        return f"{column} = '{value}'"

    def _replace_not_equals(self, column: str, value: str) -> str:
        """替换不等于条件"""
        if value.isdigit():
            return f"{column} != {value}"
        return f"{column} != '{value}'"


# 全局转换器实例
nl2sql_converter = NL2SQLConverter()
