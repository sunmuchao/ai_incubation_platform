"""
Schema 发现增强模块 - v1.4
提供跨表关系自动发现、索引信息、分区信息和表统计信息
"""
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import re


@dataclass
class ColumnInfo:
    """列信息"""
    name: str
    type: str
    nullable: bool = True
    primary_key: bool = False
    foreign_key: Optional[str] = None  # 引用的表。列
    indexed: bool = False
    comment: Optional[str] = None


@dataclass
class IndexInfo:
    """索引信息"""
    name: str
    columns: List[str]
    unique: bool = False
    primary: bool = False
    index_type: Optional[str] = None  # BTREE, HASH, etc.


@dataclass
class ForeignKeyInfo:
    """外键信息"""
    column: str
    referenced_table: str
    referenced_column: str
    constraint_name: Optional[str] = None


@dataclass
class TableStats:
    """表统计信息"""
    row_count: int = 0
    size_bytes: int = 0
    last_updated: Optional[str] = None
    avg_row_size: float = 0.0


@dataclass
class PartitionInfo:
    """分区信息"""
    partition_column: str
    partition_type: str  # RANGE, LIST, HASH, etc.
    partitions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class EnhancedTableSchema:
    """增强的表 Schema"""
    table_name: str
    schema_name: Optional[str] = None
    columns: List[ColumnInfo] = field(default_factory=list)
    indexes: List[IndexInfo] = field(default_factory=list)
    foreign_keys: List[ForeignKeyInfo] = field(default_factory=list)
    stats: Optional[TableStats] = None
    partitions: Optional[PartitionInfo] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "table_name": self.table_name,
            "schema_name": self.schema_name,
            "columns": [
                {
                    "name": c.name,
                    "type": c.type,
                    "nullable": c.nullable,
                    "primary_key": c.primary_key,
                    "foreign_key": c.foreign_key,
                    "indexed": c.indexed,
                    "comment": c.comment,
                }
                for c in self.columns
            ],
            "indexes": [
                {
                    "name": i.name,
                    "columns": i.columns,
                    "unique": i.unique,
                    "primary": i.primary,
                    "index_type": i.index_type,
                }
                for i in self.indexes
            ],
            "foreign_keys": [
                {
                    "column": f.column,
                    "referenced_table": f.referenced_table,
                    "referenced_column": f.referenced_column,
                    "constraint_name": f.constraint_name,
                }
                for f in self.foreign_keys
            ],
            "stats": {
                "row_count": self.stats.row_count,
                "size_bytes": self.stats.size_bytes,
                "last_updated": self.stats.last_updated,
                "avg_row_size": self.stats.avg_row_size,
            } if self.stats else None,
            "partitions": {
                "partition_column": self.partitions.partition_column,
                "partition_type": self.partitions.partition_type,
                "partitions": self.partitions.partitions,
            } if self.partitions else None,
        }


@dataclass
class RelationGraph:
    """表关系图"""
    # 一对多关系：table -> [(referenced_table, column)]
    one_to_many: Dict[str, List[Tuple[str, str]]] = field(default_factory=dict)
    # 多对一关系：table -> [(referenced_table, column)]
    many_to_one: Dict[str, List[Tuple[str, str]]] = field(default_factory=dict)
    # 多对多关系：(table1, table2) -> junction_table
    many_to_many: List[Tuple[str, str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "one_to_many": {k: list(v) for k, v in self.one_to_many.items()},
            "many_to_one": {k: list(v) for k, v in self.many_to_one.items()},
            "many_to_many": [
                {"table1": t1, "table2": t2, "junction": j}
                for t1, t2, j in self.many_to_many
            ],
        }


class SchemaRelationManager:
    """
    Schema 关系管理器
    自动发现表之间的外键关系和关联模式
    """

    # 常见的外键命名模式
    FK_PATTERNS = [
        r'^(.+)_id$',  # user_id -> users.id
        r'^(.+)[Ii]d$',  # userId/userId -> users.id
        r'^(.+)_fk$',  # user_fk
        r'^fk_(.+)_(.+)$',  # fk_orders_users
    ]

    # 常见的关联表命名模式（多对多）
    JUNCTION_PATTERNS = [
        r'^(.+)_(.+)_map$',  # users_roles_map
        r'^(.+)_(.+)_rel$',  # users_roles_rel
        r'^(.+)_(.+)_link$',  # users_roles_link
        r'^(.+)_(.+)_assoc$',  # users_roles_assoc
        r'^(.+)_to_(.+)$',  # user_to_role
    ]

    def __init__(self):
        self._relations = RelationGraph()
        self._tables: Dict[str, EnhancedTableSchema] = {}

    def auto_discover_relations(self, schemas: Dict[str, Dict[str, Any]]) -> RelationGraph:
        """
        自动发现表之间的关系

        Args:
            schemas: {table_name: {columns: [{name, type, ...}]}}

        Returns:
            RelationGraph: 发现的关系图
        """
        self._relations = RelationGraph()
        table_names = set(schemas.keys())

        # 解析所有表的列信息
        table_columns: Dict[str, Set[str]] = {}
        for table_name, schema in schemas.items():
            columns = schema.get('columns', [])
            if isinstance(columns, list):
                table_columns[table_name] = {
                    col['name'] if isinstance(col, dict) else str(col)
                    for col in columns
                }
            elif isinstance(columns, dict):
                table_columns[table_name] = set(columns.keys())
            else:
                table_columns[table_name] = set()

        # 发现外键关系
        for table_name, columns in table_columns.items():
            for column in columns:
                referenced_table = self._infer_foreign_key(column, table_names)
                if referenced_table:
                    self._add_relation(table_name, column, referenced_table)

        # 发现多对多关系
        for table_name in table_names:
            self._check_junction_table(table_name, table_names, table_columns)

        return self._relations

    def _infer_foreign_key(self, column: str, table_names: Set[str]) -> Optional[str]:
        """根据列名推断外键引用的表"""
        column_lower = column.lower()

        for pattern in self.FK_PATTERNS:
            match = re.match(pattern, column_lower)
            if match:
                # 提取潜在的表名
                if len(match.groups()) >= 1:
                    potential_table = match.group(1)

                    # 尝试匹配表名（单复数转换）
                    matched = self._match_table_name(potential_table, table_names)
                    if matched:
                        return matched

        return None

    def _match_table_name(self, name: str, table_names: Set[str]) -> Optional[str]:
        """匹配表名（考虑单复数和驼峰命名）"""
        # 直接匹配
        if name in table_names:
            return name

        # 尝试复数形式
        plural_forms = [
            name + 's',  # user -> users
            name + 'es',  # class -> classes
            name[:-1] + 'ies',  # city -> cities
        ]
        for plural in plural_forms:
            if plural in table_names:
                return plural

        # 尝试单数形式
        if name.endswith('s'):
            singular = name[:-1]  # users -> user
            if singular in table_names:
                return singular

        # 尝试驼峰命名转小写（userId -> userid）
        name_lower = name.lower()
        for table in table_names:
            if table.lower() == name_lower:
                return table

        return None

    def _add_relation(self, from_table: str, column: str, to_table: str) -> None:
        """添加关系"""
        # 添加到多对一关系
        if from_table not in self._relations.many_to_one:
            self._relations.many_to_one[from_table] = []
        self._relations.many_to_one[from_table].append((to_table, column))

        # 添加到一对多关系
        if to_table not in self._relations.one_to_many:
            self._relations.one_to_many[to_table] = []
        self._relations.one_to_many[to_table].append((from_table, column))

    def _check_junction_table(
        self,
        table_name: str,
        table_names: Set[str],
        table_columns: Dict[str, Set[str]]
    ) -> None:
        """检查是否为关联表（多对多）"""
        for pattern in self.JUNCTION_PATTERNS:
            match = re.match(pattern, table_name.lower())
            if match:
                table1_candidate = match.group(1)
                table2_candidate = match.group(2)

                # 尝试匹配实际的表名
                t1 = self._match_table_name(table1_candidate, table_names)
                t2 = self._match_table_name(table2_candidate, table_names)

                if t1 and t2:
                    # 验证关联表是否包含两个外键
                    columns = table_columns.get(table_name, set())
                    col1_match = any(
                        self._match_table_name(self._infer_foreign_key(c, table_names) or '', {t1})
                        for c in columns
                    )
                    col2_match = any(
                        self._match_table_name(self._infer_foreign_key(c, table_names) or '', {t2})
                        for c in columns
                    )

                    if col1_match and col2_match:
                        self._relations.many_to_many.append((t1, t2, table_name))

                break

    def build_enhanced_schema(
        self,
        table_name: str,
        base_schema: Dict[str, Any],
        include_stats: bool = False,
        include_indexes: bool = False,
        include_partitions: bool = False
    ) -> EnhancedTableSchema:
        """
        构建增强的表 Schema

        Args:
            table_name: 表名
            base_schema: 基础 Schema 信息
            include_stats: 是否包含统计信息
            include_indexes: 是否包含索引信息
            include_partitions: 是否包含分区信息
        """
        enhanced = EnhancedTableSchema(table_name=table_name)

        # 解析列信息
        columns = base_schema.get('columns', [])
        for col in columns:
            if isinstance(col, dict):
                col_name = col.get('name', str(col))
                col_type = col.get('type', 'UNKNOWN')
                nullable = col.get('nullable', True)
            else:
                col_name = str(col)
                col_type = 'UNKNOWN'
                nullable = True

            # 推断外键
            fk_table = self._infer_foreign_key(col_name, set(self._tables.keys()))

            column_info = ColumnInfo(
                name=col_name,
                type=col_type,
                nullable=nullable,
                primary_key=col.get('primary_key', False) if isinstance(col, dict) else False,
                foreign_key=f"{fk_table}.{col_name}" if fk_table else None,
            )
            enhanced.columns.append(column_info)

        # 添加索引信息
        if include_indexes and 'indexes' in base_schema:
            for idx in base_schema.get('indexes', []):
                index_info = IndexInfo(
                    name=idx.get('name', ''),
                    columns=idx.get('columns', []),
                    unique=idx.get('unique', False),
                    primary=idx.get('primary', False),
                    index_type=idx.get('type'),
                )
                enhanced.indexes.append(index_info)

        # 添加统计信息
        if include_stats and 'stats' in base_schema:
            stats = base_schema.get('stats', {})
            enhanced.stats = TableStats(
                row_count=stats.get('row_count', 0),
                size_bytes=stats.get('size_bytes', 0),
                last_updated=stats.get('last_updated'),
                avg_row_size=stats.get('avg_row_size', 0.0),
            )

        # 添加分区信息
        if include_partitions and 'partitions' in base_schema:
            parts = base_schema.get('partitions', {})
            enhanced.partitions = PartitionInfo(
                partition_column=parts.get('column', ''),
                partition_type=parts.get('type', 'UNKNOWN'),
                partitions=parts.get('partitions', []),
            )

        return enhanced

    def get_join_path(
        self,
        from_table: str,
        to_table: str,
        max_depth: int = 5
    ) -> Optional[List[Tuple[str, str, str]]]:
        """
        获取两个表之间的 JOIN 路径

        Args:
            from_table: 起始表
            to_table: 目标表
            max_depth: 最大搜索深度

        Returns:
            [(table1, table2, join_column), ...] 或 None
        """
        from collections import deque

        # BFS 搜索
        queue = deque([(from_table, [])])
        visited = {from_table}

        while queue:
            current, path = queue.popleft()

            if len(path) >= max_depth:
                continue

            # 检查是否到达目标
            if current == to_table:
                return path

            # 探索相邻表（通过外键）
            for next_table, column in self._relations.many_to_one.get(current, []):
                if next_table not in visited:
                    visited.add(next_table)
                    new_path = path + [(current, next_table, column)]
                    queue.append((next_table, new_path))

            for next_table, column in self._relations.one_to_many.get(current, []):
                if next_table not in visited:
                    visited.add(next_table)
                    new_path = path + [(current, next_table, column)]
                    queue.append((next_table, new_path))

        return None

    def suggest_indexes(
        self,
        table_name: str,
        query_patterns: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        建议应该创建的索引

        Args:
            table_name: 表名
            query_patterns: 查询模式列表

        Returns:
            建议的索引列表
        """
        suggestions = []

        if table_name in self._tables:
            table = self._tables[table_name]

            # 外键列建议索引
            for col in table.columns:
                if col.foreign_key and not col.indexed:
                    suggestions.append({
                        "type": "foreign_key",
                        "columns": [col.name],
                        "reason": f"Foreign key column '{col.name}' should be indexed for better JOIN performance",
                    })

            # 基于查询模式建议索引
            if query_patterns:
                for pattern in query_patterns:
                    # 提取 WHERE 条件中的列
                    where_cols = re.findall(r'WHERE\s+\w+\.(\w+)\s*=', pattern, re.IGNORECASE)
                    for col_name in where_cols:
                        col_info = next((c for c in table.columns if c.name == col_name), None)
                        if col_info and not col_info.indexed:
                            suggestions.append({
                                "type": "query_optimization",
                                "columns": [col_name],
                                "reason": f"Column '{col_name}' is used in WHERE clause",
                            })

        return suggestions


# 导出
__all__ = [
    "ColumnInfo",
    "IndexInfo",
    "ForeignKeyInfo",
    "TableStats",
    "PartitionInfo",
    "EnhancedTableSchema",
    "RelationGraph",
    "SchemaRelationManager",
]
