"""
DeerFlow 工具封装层

将数据连接器操作封装为 DeerFlow 2.0 可调工具，供 Agent 使用。
所有工具调用均经过安全校验、限流和审计。
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

from utils.logger import logger
from core.connection_manager import connection_manager
from core.query_engine import query_engine
from nl2sql.converter import nl2sql_converter
from connectors.base import ConnectorConfig, ConnectorFactory


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "message": self.message,
            "metadata": self.metadata
        }


# ============================================================================
# 连接器管理工具
# ============================================================================

async def tool_list_connectors() -> ToolResult:
    """
    列出所有已连接的数据源

    返回：
        - sources: 数据源列表，包含名称、类型、连接状态等
    """
    try:
        sources = await connection_manager.list_connectors()
        return ToolResult(
            success=True,
            data={"sources": sources, "count": len(sources)}
        )
    except Exception as e:
        logger.error("tool_list_connectors failed", extra={"error": str(e)})
        return ToolResult(success=False, error=str(e))


async def tool_connect_datasource(
    name: str,
    connector_type: str,
    datasource_name: Optional[str] = None,
    role: str = "read_only"
) -> ToolResult:
    """
    连接新的数据源

    参数：
        - name: 连接器名称（用户自定义）
        - connector_type: 连接器类型 (mysql, postgresql, mongodb, redis, sqlite, elasticsearch, rest_api)
        - datasource_name: 数据源名称，用于从环境变量加载凭据（可选，默认使用 name）
        - role: 角色 (read_only, read_write)

    返回：
        - status: 连接状态
        - message: 连接结果消息
    """
    try:
        config = ConnectorConfig(
            name=name,
            datasource_name=datasource_name or name
        )
        connector = await connection_manager.create_connector(
            connector_type=connector_type,
            config=config,
            created_by="agent",
            role=role
        )
        return ToolResult(
            success=True,
            data={"status": "connected", "name": name, "type": connector_type},
            message=f"成功连接到数据源 {name}"
        )
    except Exception as e:
        logger.error("tool_connect_datasource failed", extra={"error": str(e), "connector_name": name})
        return ToolResult(success=False, error=f"连接失败：{str(e)}")


async def tool_disconnect_datasource(name: str) -> ToolResult:
    """
    断开数据源连接

    参数：
        - name: 连接器名称

    返回：
        - status: 断开状态
    """
    try:
        success = await connection_manager.remove_connector(name)
        if success:
            return ToolResult(
                success=True,
                data={"status": "disconnected", "name": name},
                message=f"已断开数据源 {name}"
            )
        else:
            return ToolResult(success=False, error=f"数据源 {name} 不存在")
    except Exception as e:
        logger.error("tool_disconnect_datasource failed", extra={"error": str(e), "name": name})
        return ToolResult(success=False, error=str(e))


# ============================================================================
# 查询工具
# ============================================================================

async def tool_execute_sql(
    connector_name: str,
    sql: str,
    params: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = "agent",
    role: str = "read_only"
) -> ToolResult:
    """
    执行 SQL 查询

    参数：
        - connector_name: 连接器名称
        - sql: SQL 语句
        - params: SQL 参数（可选）
        - user_id: 用户 ID（用于审计）
        - role: 角色 (read_only, read_write)

    安全约束：
        - 只读角色仅允许 SELECT 查询
        - 危险 SQL 自动拦截（DROP/ALTER/TRUNCATE 等）
        - 查询结果自动限制最大行数
        - 所有查询记录审计日志

    返回：
        - data: 查询结果列表
        - execution_time_ms: 执行耗时
        - operation_type: 操作类型 (SELECT, INSERT, UPDATE, DELETE)
        - rows_returned: 返回行数
    """
    try:
        result = await query_engine.execute_query(
            connector_name=connector_name,
            query=sql,
            params=params,
            user_id=user_id,
            role=role
        )

        if result.success:
            return ToolResult(
                success=True,
                data=result.data,
                metadata={
                    "execution_time_ms": result.execution_time_ms,
                    "operation_type": result.operation_type,
                    "rows_returned": result.rows_returned
                }
            )
        else:
            return ToolResult(
                success=False,
                error=result.error,
                metadata={
                    "error_code": getattr(result, "error_code", ""),
                    "operation_type": result.operation_type
                }
            )
    except Exception as e:
        logger.error("tool_execute_sql failed", extra={"error": str(e), "connector": connector_name})
        return ToolResult(success=False, error=f"执行失败：{str(e)}")


async def tool_nl_query(
    connector_name: str,
    natural_language: str,
    user_id: Optional[str] = "agent",
    role: str = "read_only"
) -> ToolResult:
    """
    自然语言查询 - 将自然语言转换为 SQL 并执行

    参数：
        - connector_name: 连接器名称
        - natural_language: 自然语言查询，如"查询年龄大于 18 岁的用户"
        - user_id: 用户 ID（用于审计）
        - role: 角色 (read_only, read_write)

    支持的查询模式：
        - 基础查询："查询所有用户"
        - 条件查询："查询年龄大于 18 的用户"
        - 聚合查询："统计用户总数"
        - 分组统计："按部门分组统计用户数量"
        - 排序查询："按年龄降序排列用户"

    返回：
        - data: 查询结果
        - natural_language: 原始自然语言查询
        - execution_time_ms: 执行耗时
    """
    try:
        result = await query_engine.execute_natural_language_query(
            connector_name=connector_name,
            natural_language=natural_language,
            user_id=user_id,
            role=role
        )

        if result.success:
            return ToolResult(
                success=True,
                data=result.data,
                metadata={
                    "natural_language": natural_language,
                    "execution_time_ms": result.execution_time_ms,
                    "operation_type": result.operation_type,
                    "rows_returned": result.rows_returned
                }
            )
        else:
            return ToolResult(
                success=False,
                error=result.error,
                metadata={"natural_language": natural_language}
            )
    except Exception as e:
        logger.error("tool_nl_query failed", extra={"error": str(e), "connector": connector_name})
        return ToolResult(success=False, error=f"查询失败：{str(e)}")


# ============================================================================
# Schema 工具
# ============================================================================

async def tool_get_schema(
    connector_name: str,
    use_cache: bool = True
) -> ToolResult:
    """
    获取数据源的 Schema 信息

    参数：
        - connector_name: 连接器名称
        - use_cache: 是否使用缓存（默认 True）

    返回：
        - schema: Schema 信息，包含表结构、字段定义等
        - cached: 是否来自缓存
    """
    try:
        connector = await connection_manager.get_connector(connector_name)
        if not connector:
            return ToolResult(success=False, error=f"数据源 {connector_name} 不存在")

        # 尝试从缓存获取
        if use_cache:
            cached_schema = nl2sql_converter.schema_cache.get(connector_name)
            if cached_schema:
                return ToolResult(
                    success=True,
                    data={"schema": cached_schema},
                    metadata={"cached": True, "source": "cache"}
                )

        # 从数据源获取 Schema
        schema = await connector.get_schema()
        nl2sql_converter.register_schema(connector_name, schema)

        return ToolResult(
            success=True,
            data={"schema": schema},
            metadata={"cached": False, "source": "datasource"}
        )
    except Exception as e:
        logger.error("tool_get_schema failed", extra={"error": str(e), "connector": connector_name})
        return ToolResult(success=False, error=str(e))


async def tool_refresh_schema(
    connector_name: str,
    user_id: Optional[str] = "agent"
) -> ToolResult:
    """
    刷新数据源的 Schema 缓存

    参数：
        - connector_name: 连接器名称
        - user_id: 用户 ID（用于审计）

    返回：
        - schema: 更新后的 Schema
        - message: 刷新结果消息
    """
    try:
        connector = await connection_manager.get_connector(connector_name)
        if not connector:
            return ToolResult(success=False, error=f"数据源 {connector_name} 不存在")

        # 获取最新 Schema 并更新缓存
        schema = await connector.get_schema()
        nl2sql_converter.schema_cache.invalidate(connector_name)
        nl2sql_converter.register_schema(connector_name, schema)

        logger.info(
            "Schema refreshed",
            extra={"connector_name": connector_name, "user_id": user_id}
        )

        return ToolResult(
            success=True,
            data={"schema": schema},
            message=f"数据源 {connector_name} 的 Schema 已刷新"
        )
    except Exception as e:
        logger.error("tool_refresh_schema failed", extra={"error": str(e), "connector": connector_name})
        return ToolResult(success=False, error=str(e))


async def tool_list_available_connector_types() -> ToolResult:
    """
    列出所有可用的连接器类型

    返回：
        - types: 连接器类型列表
        - descriptions: 各类型的描述
    """
    types = ConnectorFactory.list_types()
    return ToolResult(
        success=True,
        data={
            "types": types,
            "count": len(types),
            "descriptions": {
                "mysql": "MySQL 关系数据库",
                "postgresql": "PostgreSQL 关系数据库",
                "sqlite": "SQLite 轻量级数据库",
                "mongodb": "MongoDB 文档数据库",
                "redis": "Redis 键值存储",
                "elasticsearch": "Elasticsearch 搜索引擎",
                "rest_api": "REST API 接口"
            }
        }
    )


# ============================================================================
# 数据血缘工具
# ============================================================================

from core.lineage import lineage_manager


async def tool_get_lineage(
    connector_name: str,
    table_name: str
) -> ToolResult:
    """
    获取表的数据血缘关系

    参数：
        - connector_name: 连接器名称
        - table_name: 表名

    返回：
        - lineage: 血缘信息，包含上游依赖、下游依赖、相关边等
    """
    try:
        lineage = lineage_manager.get_table_lineage(connector_name, table_name)
        return ToolResult(
            success=True,
            data=lineage,
            metadata={}
        )
    except Exception as e:
        logger.error("tool_get_lineage failed", extra={"error": str(e)})
        return ToolResult(success=False, error=str(e))


async def tool_analyze_impact(
    connector_name: str,
    table_name: str,
    proposed_changes: Optional[Dict[str, Any]] = None
) -> ToolResult:
    """
    分析表变更的影响范围

    参数：
        - connector_name: 连接器名称
        - table_name: 表名
        - proposed_changes: 拟议的变更，如：
            {
                "change_type": "drop_table|schema_change|data_change",
                "details": {...}
            }

    返回：
        - impact: 影响分析结果，包含受影响节点、风险等级、摘要等
    """
    try:
        result = lineage_manager.analyze_impact(connector_name, table_name, proposed_changes)
        return ToolResult(
            success=True,
            data=result.to_dict(),
            metadata={}
        )
    except Exception as e:
        logger.error("tool_analyze_impact failed", extra={"error": str(e)})
        return ToolResult(success=False, error=str(e))


async def tool_get_data_dictionary(
    connector_name: str,
    table_name: Optional[str] = None
) -> ToolResult:
    """
    获取数据字典

    参数：
        - connector_name: 连接器名称
        - table_name: 表名（可选，不传则返回全部）

    返回：
        - dictionary: 数据字典信息
    """
    try:
        dictionary = lineage_manager.get_data_dictionary(connector_name, table_name)
        return ToolResult(
            success=True,
            data=dictionary,
            metadata={}
        )
    except Exception as e:
        logger.error("tool_get_data_dictionary failed", extra={"error": str(e)})
        return ToolResult(success=False, error=str(e))


async def tool_search_data_dictionary(
    keyword: str,
    connector_name: Optional[str] = None
) -> ToolResult:
    """
    搜索数据字典

    参数：
        - keyword: 搜索关键词
        - connector_name: 连接器名称（可选）

    返回：
        - results: 搜索结果列表
    """
    try:
        results = await lineage_manager.search_data_dictionary(keyword, connector_name)
        return ToolResult(
            success=True,
            data={"results": results, "count": len(results)},
            metadata={}
        )
    except Exception as e:
        logger.error("tool_search_data_dictionary failed", extra={"error": str(e)})
        return ToolResult(success=False, error=str(e))


async def tool_sync_dictionary_from_code(
    connector_name: str,
    project_name: str,
    table_pattern: Optional[str] = None
) -> ToolResult:
    """
    从代码理解服务同步数据字典

    参数：
        - connector_name: 连接器名称
        - project_name: 代码理解服务中的项目名称
        - table_pattern: 表名模式（可选）

    返回：
        - sync_result: 同步结果
    """
    try:
        result = await lineage_manager.sync_data_dictionary_from_code_understanding(
            connector_name,
            project_name,
            table_pattern
        )
        return ToolResult(
            success=True,
            data=result,
            metadata={}
        )
    except Exception as e:
        logger.error("tool_sync_dictionary_from_code failed", extra={"error": str(e)})
        return ToolResult(success=False, error=str(e))


async def tool_record_lineage(
    connector_name: str,
    sql: str,
    user_id: Optional[str] = "agent"
) -> ToolResult:
    """
    记录 SQL 查询的血缘关系

    参数：
        - connector_name: 连接器名称
        - sql: SQL 语句
        - user_id: 用户 ID

    返回：
        - lineage_record: 血缘记录结果
    """
    try:
        # 从 SQL 中提取操作类型和表
        sql_upper = sql.strip().upper()
        if sql_upper.startswith("SELECT"):
            operation_type = "SELECT"
        elif sql_upper.startswith("INSERT"):
            operation_type = "INSERT"
        elif sql_upper.startswith("UPDATE"):
            operation_type = "UPDATE"
        elif sql_upper.startswith("DELETE"):
            operation_type = "DELETE"
        else:
            operation_type = "OTHER"

        result = lineage_manager.record_query_impact(
            datasource=connector_name,
            query=sql,
            operation_type=operation_type,
            affected_tables=[],
            user=user_id
        )

        return ToolResult(
            success=True,
            data=result,
            metadata={"operation_type": operation_type}
        )
    except Exception as e:
        logger.error("tool_record_lineage failed", extra={"error": str(e)})
        return ToolResult(success=False, error=str(e))


async def tool_get_lineage_statistics() -> ToolResult:
    """
    获取血缘统计信息

    返回：
        - statistics: 血缘图统计信息
    """
    try:
        stats = lineage_manager.get_lineage_statistics()
        return ToolResult(
            success=True,
            data=stats,
            metadata={}
        )
    except Exception as e:
        logger.error("tool_get_lineage_statistics failed", extra={"error": str(e)})
        return ToolResult(success=False, error=str(e))


# ============================================================================
# 工具注册表
# ============================================================================

TOOLS_REGISTRY = {
    # 连接器管理
    "list_connectors": {
        "func": tool_list_connectors,
        "description": "列出所有已连接的数据源",
        "parameters": {}
    },
    "connect_datasource": {
        "func": tool_connect_datasource,
        "description": "连接新的数据源",
        "parameters": {
            "name": {"type": "string", "required": True, "description": "连接器名称"},
            "connector_type": {"type": "string", "required": True, "description": "连接器类型"},
            "datasource_name": {"type": "string", "required": False, "description": "数据源名称（用于从环境加载凭据）"},
            "role": {"type": "string", "required": False, "default": "read_only", "description": "角色 (read_only|read_write)"}
        }
    },
    "disconnect_datasource": {
        "func": tool_disconnect_datasource,
        "description": "断开数据源连接",
        "parameters": {
            "name": {"type": "string", "required": True, "description": "连接器名称"}
        }
    },
    # 查询工具
    "execute_sql": {
        "func": tool_execute_sql,
        "description": "执行 SQL 查询（带安全校验和审计）",
        "parameters": {
            "connector_name": {"type": "string", "required": True, "description": "连接器名称"},
            "sql": {"type": "string", "required": True, "description": "SQL 语句"},
            "params": {"type": "object", "required": False, "description": "SQL 参数"},
            "role": {"type": "string", "required": False, "default": "read_only", "description": "角色 (read_only|read_write)"}
        }
    },
    "nl_query": {
        "func": tool_nl_query,
        "description": "自然语言查询 - 将自然语言转换为 SQL 并执行",
        "parameters": {
            "connector_name": {"type": "string", "required": True, "description": "连接器名称"},
            "natural_language": {"type": "string", "required": True, "description": "自然语言查询"},
            "role": {"type": "string", "required": False, "default": "read_only", "description": "角色"}
        }
    },
    # Schema 工具
    "get_schema": {
        "func": tool_get_schema,
        "description": "获取数据源的 Schema 信息",
        "parameters": {
            "connector_name": {"type": "string", "required": True, "description": "连接器名称"},
            "use_cache": {"type": "boolean", "required": False, "default": True, "description": "是否使用缓存"}
        }
    },
    "refresh_schema": {
        "func": tool_refresh_schema,
        "description": "刷新数据源的 Schema 缓存",
        "parameters": {
            "connector_name": {"type": "string", "required": True, "description": "连接器名称"}
        }
    },
    "list_available_connector_types": {
        "func": tool_list_available_connector_types,
        "description": "列出所有可用的连接器类型",
        "parameters": {}
    },
    # 数据血缘工具
    "get_lineage": {
        "func": tool_get_lineage,
        "description": "获取表的数据血缘关系",
        "parameters": {
            "connector_name": {"type": "string", "required": True, "description": "连接器名称"},
            "table_name": {"type": "string", "required": True, "description": "表名"}
        }
    },
    "analyze_impact": {
        "func": tool_analyze_impact,
        "description": "分析表变更的影响范围",
        "parameters": {
            "connector_name": {"type": "string", "required": True, "description": "连接器名称"},
            "table_name": {"type": "string", "required": True, "description": "表名"},
            "proposed_changes": {"type": "object", "required": False, "description": "拟议的变更"}
        }
    },
    "get_data_dictionary": {
        "func": tool_get_data_dictionary,
        "description": "获取数据字典",
        "parameters": {
            "connector_name": {"type": "string", "required": True, "description": "连接器名称"},
            "table_name": {"type": "string", "required": False, "description": "表名（可选）"}
        }
    },
    "search_data_dictionary": {
        "func": tool_search_data_dictionary,
        "description": "搜索数据字典",
        "parameters": {
            "keyword": {"type": "string", "required": True, "description": "搜索关键词"},
            "connector_name": {"type": "string", "required": False, "description": "连接器名称（可选）"}
        }
    },
    "sync_dictionary_from_code": {
        "func": tool_sync_dictionary_from_code,
        "description": "从代码理解服务同步数据字典",
        "parameters": {
            "connector_name": {"type": "string", "required": True, "description": "连接器名称"},
            "project_name": {"type": "string", "required": True, "description": "代码理解服务中的项目名称"},
            "table_pattern": {"type": "string", "required": False, "description": "表名模式（可选）"}
        }
    },
    "record_lineage": {
        "func": tool_record_lineage,
        "description": "记录 SQL 查询的血缘关系",
        "parameters": {
            "connector_name": {"type": "string", "required": True, "description": "连接器名称"},
            "sql": {"type": "string", "required": True, "description": "SQL 语句"},
            "user_id": {"type": "string", "required": False, "default": "agent", "description": "用户 ID"}
        }
    },
    "get_lineage_statistics": {
        "func": tool_get_lineage_statistics,
        "description": "获取血缘统计信息",
        "parameters": {}
    }
}


def get_tool_descriptions() -> Dict[str, str]:
    """获取所有工具的简短描述"""
    return {name: info["description"] for name, info in TOOLS_REGISTRY.items()}


def get_tool_schema(tool_name: str) -> Optional[Dict[str, Any]]:
    """获取指定工具的完整 schema"""
    return TOOLS_REGISTRY.get(tool_name)


async def execute_tool(tool_name: str, **kwargs) -> ToolResult:
    """
    执行指定的工具

    参数：
        - tool_name: 工具名称
        - **kwargs: 工具参数

    返回：
        ToolResult 执行结果
    """
    if tool_name not in TOOLS_REGISTRY:
        return ToolResult(success=False, error=f"未知工具：{tool_name}")

    func = TOOLS_REGISTRY[tool_name]["func"]
    try:
        return await func(**kwargs)
    except TypeError as e:
        # 参数错误
        return ToolResult(success=False, error=f"参数错误：{str(e)}")
    except Exception as e:
        logger.error(f"Tool execution failed: {tool_name}", extra={"error": str(e)})
        return ToolResult(success=False, error=f"执行失败：{str(e)}")
