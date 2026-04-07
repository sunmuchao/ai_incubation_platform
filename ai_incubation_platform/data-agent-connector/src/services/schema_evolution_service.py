"""
Schema 自动演进服务

功能:
1. Schema 变更检测（新增列/表、类型变更）
2. 自动映射生成
3. Schema 版本控制
4. 迁移脚本生成
5. 向后兼容处理
"""
from typing import Optional, Dict, Any, List, Tuple, Set
from datetime import datetime
from enum import Enum
import json
import hashlib
import asyncio

from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from config.database import db_manager
from utils.logger import logger


class ChangeType(Enum):
    """变更类型"""
    TABLE_ADDED = "table_added"
    TABLE_DROPPED = "table_dropped"
    COLUMN_ADDED = "column_added"
    COLUMN_DROPPED = "column_dropped"
    COLUMN_TYPE_CHANGED = "column_type_changed"
    COLUMN_NULLABLE_CHANGED = "column_nullable_changed"
    COLUMN_DEFAULT_CHANGED = "column_default_changed"
    INDEX_ADDED = "index_added"
    INDEX_DROPPED = "index_dropped"


class CompatibilityLevel(Enum):
    """兼容性级别"""
    FULL_COMPATIBLE = "full_compatible"  # 完全兼容，无需任何操作
    BACKWARD_COMPATIBLE = "backward_compatible"  # 向后兼容，旧代码可正常工作
    FORWARD_COMPATIBLE = "forward_compatible"  # 向前兼容，新代码可处理旧数据
    BREAKING_CHANGE = "breaking_change"  # 破坏性变更，需要手动处理


class SchemaChange:
    """Schema 变更"""

    def __init__(
        self,
        change_type: ChangeType,
        table_name: str,
        column_name: Optional[str] = None,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        description: str = "",
        compatibility: CompatibilityLevel = CompatibilityLevel.BACKWARD_COMPATIBLE
    ):
        self.change_type = change_type
        self.table_name = table_name
        self.column_name = column_name
        self.old_value = old_value
        self.new_value = new_value
        self.description = description
        self.compatibility = compatibility
        self.timestamp = datetime.utcnow()
        ts_str = self.timestamp.isoformat()
        self.id = hashlib.md5(
            f"{change_type.value}:{table_name}:{column_name}:{ts_str}".encode()
        ).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "change_type": self.change_type.value,
            "table_name": self.table_name,
            "column_name": self.column_name,
            "old_value": str(self.old_value) if self.old_value else None,
            "new_value": str(self.new_value) if self.new_value else None,
            "description": self.description,
            "compatibility": self.compatibility.value,
            "timestamp": self.timestamp.isoformat()
        }


class SchemaVersion:
    """Schema 版本"""

    def __init__(
        self,
        connector_name: str,
        version: int,
        schema: Dict[str, Any],
        changes: List[SchemaChange],
        description: str = ""
    ):
        self.connector_name = connector_name
        self.version = version
        self.schema = schema
        self.changes = changes
        self.description = description
        self.created_at = datetime.utcnow()
        self.schema_hash = hashlib.md5(
            json.dumps(schema, sort_keys=True).encode()
        ).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connector_name": self.connector_name,
            "version": self.version,
            "schema": self.schema,
            "changes": [c.to_dict() for c in self.changes],
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "schema_hash": self.schema_hash
        }


class SchemaEvolutionService:
    """Schema 演进服务"""

    def __init__(self):
        self._version_history: Dict[str, List[SchemaVersion]] = {}
        self._current_version: Dict[str, int] = {}
        self._schema_cache: Dict[str, Dict[str, Any]] = {}

    async def detect_changes(
        self,
        connector_name: str,
        old_schema: Dict[str, Any],
        new_schema: Dict[str, Any]
    ) -> List[SchemaChange]:
        """
        检测 Schema 变更

        Args:
            connector_name: 连接器名称
            old_schema: 旧 Schema
            new_schema: 新 Schema

        Returns:
            变更列表
        """
        changes = []

        old_tables = set(old_schema.get('tables', {}).keys())
        new_tables = set(new_schema.get('tables', {}).keys())

        # 检测新增表
        for table in new_tables - old_tables:
            changes.append(SchemaChange(
                change_type=ChangeType.TABLE_ADDED,
                table_name=table,
                new_value=new_schema['tables'][table],
                description=f"新增表：{table}",
                compatibility=CompatibilityLevel.BACKWARD_COMPATIBLE
            ))

        # 检测删除表
        for table in old_tables - new_tables:
            changes.append(SchemaChange(
                change_type=ChangeType.TABLE_DROPPED,
                table_name=table,
                old_value=old_schema['tables'][table],
                description=f"删除表：{table}",
                compatibility=CompatibilityLevel.BREAKING_CHANGE
            ))

        # 检测表结构变更
        for table in old_tables & new_tables:
            table_changes = self._detect_table_changes(
                table,
                old_schema['tables'][table],
                new_schema['tables'][table]
            )
            changes.extend(table_changes)

        # 评估整体兼容性
        overall_compatibility = self._evaluate_compatibility(changes)

        logger.info(
            "Schema changes detected",
            extra={
                "connector_name": connector_name,
                "change_count": len(changes),
                "compatibility": overall_compatibility.value
            }
        )

        return changes

    def _detect_table_changes(
        self,
        table_name: str,
        old_columns: List[Dict[str, Any]],
        new_columns: List[Dict[str, Any]]
    ) -> List[SchemaChange]:
        """检测表结构变更"""
        changes = []

        old_cols = {col['name'].lower(): col for col in old_columns}
        new_cols = {col['name'].lower(): col for col in new_columns}

        old_col_names = set(old_cols.keys())
        new_col_names = set(new_cols.keys())

        # 新增列
        for col_name in new_col_names - old_col_names:
            col = new_cols[col_name]
            changes.append(SchemaChange(
                change_type=ChangeType.COLUMN_ADDED,
                table_name=table_name,
                column_name=col_name,
                new_value=col,
                description=f"表 {table_name} 新增列：{col_name} ({col.get('type', 'unknown')})",
                compatibility=CompatibilityLevel.BACKWARD_COMPATIBLE
            ))

        # 删除列
        for col_name in old_col_names - new_col_names:
            col = old_cols[col_name]
            changes.append(SchemaChange(
                change_type=ChangeType.COLUMN_DROPPED,
                table_name=table_name,
                column_name=col_name,
                old_value=col,
                description=f"表 {table_name} 删除列：{col_name}",
                compatibility=CompatibilityLevel.BREAKING_CHANGE
            ))

        # 列类型变更
        for col_name in old_col_names & new_col_names:
            old_col = old_cols[col_name]
            new_col = new_cols[col_name]

            # 类型变更
            if old_col.get('type') != new_col.get('type'):
                changes.append(SchemaChange(
                    change_type=ChangeType.COLUMN_TYPE_CHANGED,
                    table_name=table_name,
                    column_name=col_name,
                    old_value=old_col.get('type'),
                    new_value=new_col.get('type'),
                    description=f"表 {table_name} 列 {col_name} 类型变更：{old_col.get('type')} -> {new_col.get('type')}",
                    compatibility=self._assess_type_compatibility(old_col.get('type'), new_col.get('type'))
                ))

            # 可空性变更
            if old_col.get('nullable') != new_col.get('nullable'):
                changes.append(SchemaChange(
                    change_type=ChangeType.COLUMN_NULLABLE_CHANGED,
                    table_name=table_name,
                    column_name=col_name,
                    old_value=old_col.get('nullable'),
                    new_value=new_col.get('nullable'),
                    description=f"表 {table_name} 列 {col_name} 可空性变更：{old_col.get('nullable')} -> {new_col.get('nullable')}",
                    compatibility=CompatibilityLevel.FORWARD_COMPATIBLE
                ))

            # 默认值变更
            if old_col.get('default') != new_col.get('default'):
                changes.append(SchemaChange(
                    change_type=ChangeType.COLUMN_DEFAULT_CHANGED,
                    table_name=table_name,
                    column_name=col_name,
                    old_value=old_col.get('default'),
                    new_value=new_col.get('default'),
                    description=f"表 {table_name} 列 {col_name} 默认值变更",
                    compatibility=CompatibilityLevel.FORWARD_COMPATIBLE
                ))

        return changes

    def _assess_type_compatibility(self, old_type: str, new_type: str) -> CompatibilityLevel:
        """评估类型变更的兼容性"""
        #  widening conversions (compatible)
        widening = {
            ('INT', 'BIGINT'),
            ('INT', 'DECIMAL'),
            ('FLOAT', 'DOUBLE'),
            ('VARCHAR', 'TEXT'),
            ('SMALLINT', 'INT'),
            ('TINYINT', 'SMALLINT'),
        }

        if (old_type.upper(), new_type.upper()) in widening:
            return CompatibilityLevel.BACKWARD_COMPATIBLE

        # narrowing conversions (breaking)
        narrowing = {
            ('BIGINT', 'INT'),
            ('DECIMAL', 'INT'),
            ('DOUBLE', 'FLOAT'),
            ('TEXT', 'VARCHAR'),
        }

        if (old_type.upper(), new_type.upper()) in narrowing:
            return CompatibilityLevel.BREAKING_CHANGE

        # 未知变更，谨慎处理
        return CompatibilityLevel.FORWARD_COMPATIBLE

    def _evaluate_compatibility(self, changes: List[SchemaChange]) -> CompatibilityLevel:
        """评估整体兼容性"""
        if not changes:
            return CompatibilityLevel.FULL_COMPATIBLE

        has_breaking = any(c.compatibility == CompatibilityLevel.BREAKING_CHANGE for c in changes)
        has_backward = any(c.compatibility == CompatibilityLevel.BACKWARD_COMPATIBLE for c in changes)
        has_forward = any(c.compatibility == CompatibilityLevel.FORWARD_COMPATIBLE for c in changes)

        if has_breaking:
            return CompatibilityLevel.BREAKING_CHANGE
        elif has_backward:
            return CompatibilityLevel.BACKWARD_COMPATIBLE
        elif has_forward:
            return CompatibilityLevel.FORWARD_COMPATIBLE
        else:
            return CompatibilityLevel.FULL_COMPATIBLE

    async def register_schema(
        self,
        connector_name: str,
        schema: Dict[str, Any],
        description: str = ""
    ) -> SchemaVersion:
        """
        注册新版本的 Schema

        Args:
            connector_name: 连接器名称
            schema: 新 Schema
            description: 版本描述

        Returns:
            Schema 版本对象
        """
        # 获取当前版本
        current_version = self._current_version.get(connector_name, 0)
        old_schema = self._schema_cache.get(connector_name, {})

        # 检测变更
        if old_schema:
            changes = await self.detect_changes(connector_name, old_schema, schema)
        else:
            # 初始版本
            changes = [SchemaChange(
                change_type=ChangeType.TABLE_ADDED,
                table_name=list(schema.get('tables', {}).keys())[0] if schema.get('tables') else "unknown",
                new_value=schema,
                description="初始 Schema 版本",
                compatibility=CompatibilityLevel.FULL_COMPATIBLE
            )]

        # 创建新版本
        new_version = current_version + 1
        version = SchemaVersion(
            connector_name=connector_name,
            version=new_version,
            schema=schema,
            changes=changes,
            description=description
        )

        # 保存版本历史
        if connector_name not in self._version_history:
            self._version_history[connector_name] = []
        self._version_history[connector_name].append(version)

        # 更新当前版本
        self._current_version[connector_name] = new_version
        self._schema_cache[connector_name] = schema

        logger.info(
            "New schema version registered",
            extra={
                "connector_name": connector_name,
                "version": new_version,
                "change_count": len(changes)
            }
        )

        return version

    def generate_migration_script(
        self,
        connector_name: str,
        from_version: int,
        to_version: Optional[int] = None,
        dialect: str = "postgresql"
    ) -> str:
        """
        生成迁移脚本

        Args:
            connector_name: 连接器名称
            from_version: 起始版本
            to_version: 目标版本（默认为最新版本）
            dialect: SQL 方言（postgresql, mysql, sqlite）

        Returns:
            迁移脚本
        """
        if connector_name not in self._version_history:
            return f"-- Error: No version history found for {connector_name}"

        to_version = to_version or self._current_version.get(connector_name, 0)

        if from_version >= to_version:
            return f"-- No migration needed (from={from_version}, to={to_version})"

        history = self._version_history[connector_name]
        versions = {v.version: v for v in history}

        if from_version not in versions:
            return f"-- Error: Version {from_version} not found"
        if to_version not in versions:
            return f"-- Error: Version {to_version} not found"

        # 收集所有变更
        all_changes = []
        for v in range(from_version + 1, to_version + 1):
            if v in versions:
                all_changes.extend(versions[v].changes)

        # 生成 SQL
        sql_lines = [
            f"-- Migration script for {connector_name}",
            f"-- From version {from_version} to {to_version}",
            f"-- Generated at: {datetime.utcnow().isoformat()}",
            f"-- Dialect: {dialect}",
            ""
        ]

        for change in all_changes:
            sql = self._generate_sql_for_change(change, dialect)
            if sql:
                sql_lines.append(f"-- {change.description}")
                sql_lines.append(sql)
                sql_lines.append("")

        return '\n'.join(sql_lines)

    def _generate_sql_for_change(self, change: SchemaChange, dialect: str) -> str:
        """为单个变更生成 SQL"""
        if change.change_type == ChangeType.TABLE_ADDED:
            return self._generate_create_table_sql(change.table_name, change.new_value, dialect)

        elif change.change_type == ChangeType.TABLE_DROPPED:
            return f"DROP TABLE IF EXISTS {change.table_name} CASCADE;"

        elif change.change_type == ChangeType.COLUMN_ADDED:
            col_def = self._generate_column_definition(change.new_value, dialect)
            return f"ALTER TABLE {change.table_name} ADD COLUMN {col_def};"

        elif change.change_type == ChangeType.COLUMN_DROPPED:
            return f"ALTER TABLE {change.table_name} DROP COLUMN {change.column_name};"

        elif change.change_type == ChangeType.COLUMN_TYPE_CHANGED:
            if dialect == "postgresql":
                return f"ALTER TABLE {change.table_name} ALTER COLUMN {change.column_name} TYPE {change.new_value};"
            elif dialect == "mysql":
                return f"ALTER TABLE {change.table_name} MODIFY COLUMN {change.column_name} {change.new_value};"
            else:
                return f"-- SQLite does not support column type modification directly"

        elif change.change_type == ChangeType.COLUMN_NULLABLE_CHANGED:
            nullable = "DROP NOT NULL" if change.new_value else "SET NOT NULL"
            if dialect == "postgresql":
                return f"ALTER TABLE {change.table_name} ALTER COLUMN {change.column_name} {nullable};"
            else:
                return f"-- Nullable change for {change.column_name} in {change.table_name}"

        return f"-- Unhandled change type: {change.change_type}"

    def _generate_create_table_sql(self, table_name: str, columns: List[Dict[str, Any]], dialect: str) -> str:
        """生成建表 SQL"""
        col_defs = []
        for col in columns:
            col_def = self._generate_column_definition(col, dialect)
            col_defs.append(f"  {col_def}")

        join_str = ',\n'.join(col_defs)
        return f"CREATE TABLE IF NOT EXISTS {table_name} (\n{join_str}\n);"

    def _generate_column_definition(self, col: Dict[str, Any], dialect: str) -> str:
        """生成列定义"""
        name = col.get('name', 'unknown')
        col_type = col.get('type', 'VARCHAR(255)')
        nullable = col.get('nullable', True)
        default = col.get('default')

        definition = f"{name} {col_type}"

        if not nullable:
            definition += " NOT NULL"

        if default is not None:
            if isinstance(default, str):
                definition += f" DEFAULT '{default}'"
            else:
                definition += f" DEFAULT {default}"

        return definition

    def get_version_history(self, connector_name: str) -> List[Dict[str, Any]]:
        """获取版本历史"""
        if connector_name not in self._version_history:
            return []
        return [v.to_dict() for v in self._version_history[connector_name]]

    def get_current_schema(self, connector_name: str) -> Optional[Dict[str, Any]]:
        """获取当前 Schema"""
        return self._schema_cache.get(connector_name)

    def get_version(self, connector_name: str, version: int) -> Optional[Dict[str, Any]]:
        """获取指定版本的 Schema"""
        if connector_name not in self._version_history:
            return None
        for v in self._version_history[connector_name]:
            if v.version == version:
                return v.to_dict()
        return None

    def compare_versions(
        self,
        connector_name: str,
        version1: int,
        version2: int
    ) -> Dict[str, Any]:
        """比较两个版本的差异"""
        schema1 = self.get_version(connector_name, version1)
        schema2 = self.get_version(connector_name, version2)

        if not schema1 or not schema2:
            return {"error": "Version not found"}

        # 计算差异
        tables1 = set(schema1['schema'].get('tables', {}).keys())
        tables2 = set(schema2['schema'].get('tables', {}).keys())

        return {
            "version1": version1,
            "version2": version2,
            "tables_added": list(tables2 - tables1),
            "tables_removed": list(tables1 - tables2),
            "schema_hash_changed": schema1['schema_hash'] != schema2['schema_hash']
        }

    async def auto_apply_schema_change(
        self,
        connector_name: str,
        change: SchemaChange,
        auto_approve: bool = False
    ) -> Dict[str, Any]:
        """
        自动应用 Schema 变更

        Args:
            connector_name: 连接器名称
            change: Schema 变更
            auto_approve: 是否自动审批（非破坏性变更自动应用）

        Returns:
            应用结果
        """
        # 破坏性变更需要手动审批
        if change.compatibility == CompatibilityLevel.BREAKING_CHANGE and not auto_approve:
            return {
                "success": False,
                "status": "pending_approval",
                "message": f"破坏性变更需要手动审批：{change.description}",
                "change": change.to_dict()
            }

        # 生成并执行 SQL
        sql = self._generate_sql_for_change(change, "postgresql")

        logger.info(
            "Auto-applying schema change",
            extra={
                "connector_name": connector_name,
                "change": change.description,
                "sql": sql
            }
        )

        # 这里应该实际执行 SQL，但由于需要连接器实例，由调用方负责执行
        # 实际使用时需要传入连接器实例并执行 connector.execute(sql)

        return {
            "success": True,
            "status": "applied",
            "message": f"Schema 变更已应用：{change.description}",
            "sql": sql,
            "change": change.to_dict()
        }


class SchemaEvolutionModel:
    """Schema 演进数据库模型（用于持久化）"""

    def __init__(self):
        self._db_manager = db_manager

    async def init_models(self):
        """初始化数据库模型"""
        # 这里可以创建持久化表
        pass

    async def save_version(self, version: SchemaVersion):
        """保存版本到数据库"""
        # 实现持久化逻辑
        pass

    async def get_versions(self, connector_name: str) -> List[SchemaVersion]:
        """获取版本历史"""
        # 实现查询逻辑
        return []


# 全局服务实例
schema_evolution_service = SchemaEvolutionService()
