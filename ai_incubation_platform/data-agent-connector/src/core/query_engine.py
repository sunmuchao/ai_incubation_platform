"""
查询执行引擎
统一处理所有查询请求，整合安全检查、限流、审计、执行等全流程
"""
from typing import Dict, Any, Optional, List
import time
import asyncio
from connectors.base import ConnectorError
from .connection_manager import connection_manager
from .audit import audit_logger, AuditLogEntry
from .rate_limiter import rate_limiter
from utils.sql_safety import SQLSecurityChecker
from utils.logger import logger, connector_name_var
from config.settings import settings
from nl2sql.converter import nl2sql_converter
from .lineage import lineage_manager
from services.retry_service import retry_service, RetryConfig, RetryStrategy


class QueryExecutionResult:
    """查询执行结果"""
    def __init__(
        self,
        success: bool,
        data: Optional[List[Dict[str, Any]]] = None,
        error: Optional[str] = None,
        execution_time_ms: float = 0,
        operation_type: str = "",
        # 用于 API 层映射 HTTP 状态码
        error_code: str = ""
    ):
        self.success = success
        self.data = data or []
        self.error = error
        self.execution_time_ms = execution_time_ms
        self.operation_type = operation_type
        self.rows_returned = len(data) if data else 0
        self.error_code = error_code


class QueryEngine:
    """查询执行引擎"""

    def __init__(self):
        self._sql_checker = SQLSecurityChecker()

    async def execute_query(
        self,
        connector_name: str,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        role: str = "read_only"
    ) -> QueryExecutionResult:
        """
        执行查询的完整流程
        """
        start_time = time.time()
        operation_type = ""
        success = False
        error_message = None
        result_data = None
        rate_limiter_permit_acquired = False
        original_query = query

        # 设置上下文
        connector_token = connector_name_var.set(connector_name)

        try:
            # 1. 限流检查
            if not await rate_limiter.acquire():
                error_message = "请求过于频繁，请稍后再试"
                execution_time_ms = (time.time() - start_time) * 1000
                # rate-limit 也纳入审计
                await audit_logger.log(AuditLogEntry(
                    operation_type="RATE_LIMIT",
                    connector_name=connector_name,
                    query=original_query,
                    params=params,
                    success=False,
                    error_message=error_message,
                    error_code="rate_limited",
                    execution_time_ms=execution_time_ms,
                    rows_returned=0,
                    user_id=user_id,
                    role=role
                ))
                return QueryExecutionResult(
                    success=False,
                    error=error_message,
                    execution_time_ms=execution_time_ms,
                    error_code="rate_limited"
                )
            rate_limiter_permit_acquired = True

            # 2. 获取连接器
            connector = await connection_manager.get_connector(connector_name)
            if not connector:
                error_message = f"数据源 {connector_name} 不存在或已断开"
                execution_time_ms = (time.time() - start_time) * 1000
                await audit_logger.log(AuditLogEntry(
                    operation_type="CONNECTOR_NOT_FOUND",
                    connector_name=connector_name,
                    query=original_query,
                    params=params,
                    success=False,
                    error_message=error_message,
                    error_code="connector_not_found",
                    execution_time_ms=execution_time_ms,
                    rows_returned=0,
                    user_id=user_id,
                    role=role
                ))
                return QueryExecutionResult(
                    success=False,
                    error=error_message,
                    execution_time_ms=execution_time_ms,
                    error_code="connector_not_found"
                )

            # 3. SQL安全检查
            safety_result = self._sql_checker.check_sql_safety(query, role)
            operation_type = safety_result.operation_type

            if not safety_result.is_safe:
                error_message = f"SQL安全检查失败: {safety_result.reason}"
                logger.warning(
                    "SQL security check failed",
                    extra={
                        "query": query,
                        "reason": safety_result.reason,
                        "operation_type": operation_type,
                        "role": role
                    }
                )
                execution_time_ms = (time.time() - start_time) * 1000
                await audit_logger.log(AuditLogEntry(
                    operation_type=operation_type,
                    connector_name=connector_name,
                    query=original_query,
                    params=params,
                    success=False,
                    error_message=error_message,
                    error_code=(getattr(safety_result, "error_code", "") or "sql_unsafe"),
                    execution_time_ms=execution_time_ms,
                    rows_returned=0,
                    user_id=user_id,
                    role=role
                ))
                return QueryExecutionResult(
                    success=False,
                    error=error_message,
                    operation_type=operation_type,
                    execution_time_ms=execution_time_ms,
                    error_code=(getattr(safety_result, "error_code", "") or "sql_unsafe")
                )

            # 4. 自动添加LIMIT限制
            if operation_type == "SELECT":
                query = self._sql_checker.limit_query_rows(query, settings.security.max_query_rows)

            # 5. 执行查询
            logger.info(
                "Executing query",
                extra={
                    "query": query,
                    "params": params,
                    "operation_type": operation_type,
                    "role": role
                }
            )

            # 运行时超时控制（避免长查询拖垮资源）
            query_timeout_s = getattr(settings.security, "query_timeout", 0) or 0

            # 定义执行函数以便重试
            async def execute_connector_query():
                return await connector.execute(query, params)

            try:
                if query_timeout_s > 0:
                    # 如果启用了重试
                    if settings.retry.enabled:
                        result_data = await asyncio.wait_for(
                            retry_service.execute_with_retry(
                                execute_connector_query,
                                config=RetryConfig(
                                    strategy=RetryStrategy(settings.retry.strategy),
                                    max_retries=settings.retry.max_retries,
                                    base_delay=settings.retry.base_delay,
                                    max_delay=settings.retry.max_delay,
                                )
                            ),
                            timeout=query_timeout_s
                        )
                    else:
                        result_data = await asyncio.wait_for(
                            execute_connector_query(),
                            timeout=query_timeout_s
                        )
                else:
                    # 没有超时设置
                    if settings.retry.enabled:
                        result_data = await retry_service.execute_with_retry(
                            execute_connector_query,
                            config=RetryConfig(
                                strategy=RetryStrategy(settings.retry.strategy),
                                max_retries=settings.retry.max_retries,
                                base_delay=settings.retry.base_delay,
                                max_delay=settings.retry.max_delay,
                            )
                        )
                    else:
                        result_data = await execute_connector_query()

                success = True
                # 更新查询计数（仅在执行成功时）
                await connection_manager.increment_query_count(connector_name)

            except ConnectorError as e:
                error_message = f"查询执行失败: {str(e)}"
                success = False
                logger.error(
                    "Query execution failed",
                    extra={"error": str(e), "query": query}
                )
            except asyncio.TimeoutError:
                error_message = f"查询超时：超过 {query_timeout_s} 秒"
                success = False
                logger.warning(
                    "Query timeout",
                    extra={"query": query, "query_timeout_s": query_timeout_s, "connector_name": connector_name}
                )
            except Exception as e:
                error_message = f"系统错误: {str(e)}"
                success = False
                logger.error(
                    "Unexpected error during query execution",
                    extra={"error": str(e), "query": query},
                    exc_info=True
                )

            execution_time_ms = (time.time() - start_time) * 1000

            final_error_code = (
                "query_timeout" if error_message and str(error_message).startswith("查询超时") else
                "execution_error" if not success else ""
            )

            # 6. 记录审计日志
            await audit_logger.log(AuditLogEntry(
                operation_type=operation_type,
                connector_name=connector_name,
                query=query,
                params=params,
                success=success,
                error_message=error_message,
                error_code=final_error_code,
                execution_time_ms=execution_time_ms,
                rows_returned=len(result_data) if result_data else 0,
                user_id=user_id,
                role=role
            ))

            # 7. 记录数据血缘（占位实现）
            if success and operation_type in ["SELECT", "INSERT", "UPDATE", "DELETE"]:
                try:
                    # 简单解析影响的表（占位实现，后续将完善SQL解析）
                    affected_tables = self._extract_affected_tables(query)
                    lineage_manager.record_query_impact(
                        datasource=connector_name,
                        query=query,
                        operation_type=operation_type,
                        affected_tables=affected_tables,
                        user=user_id
                    )
                except Exception as e:
                    logger.warning(f"Failed to record lineage: {str(e)}", exc_info=True)

            return QueryExecutionResult(
                success=success,
                data=result_data,
                error=error_message,
                operation_type=operation_type,
                execution_time_ms=execution_time_ms,
                error_code=final_error_code
            )

        finally:
            # 释放限流许可
            if rate_limiter_permit_acquired:
                await rate_limiter.release()
            # 恢复上下文
            connector_name_var.reset(connector_token)

    def _extract_affected_tables(self, query: str) -> List[str]:
        """
        简单提取SQL查询中影响的表名（占位实现）
        后续将使用完整SQL解析器支持复杂查询
        """
        import re
        query_lower = query.lower()
        tables = []

        # 简单匹配FROM/JOIN/INTO/UPDATE后的表名
        patterns = [
            r'from\s+([^\s,;]+)',
            r'join\s+([^\s,;]+)',
            r'into\s+([^\s,;]+)',
            r'update\s+([^\s,;]+)'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, query_lower)
            for match in matches:
                # 清理表名（去掉别名、引号等）
                table = match.strip('`"\'[]')
                if table and table not in tables:
                    tables.append(table)

        return tables

    async def execute_natural_language_query(
        self,
        connector_name: str,
        natural_language: str,
        params: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        role: str = "read_only"
    ) -> QueryExecutionResult:
        """
        执行自然语言查询
        """
        start_time = time.time()

        try:
            # 获取连接器Schema
            connector = await connection_manager.get_connector(connector_name)
            if not connector:
                return QueryExecutionResult(
                    success=False,
                    error=f"数据源 {connector_name} 不存在或已断开",
                    execution_time_ms=(time.time() - start_time) * 1000
                )

            # 尝试从缓存获取Schema
            schema = nl2sql_converter.schema_cache.get(connector_name)
            if not schema:
                # 从数据源获取Schema并缓存
                schema = await connector.get_schema()
                nl2sql_converter.register_schema(connector_name, schema)

            # 转换自然语言为SQL
            try:
                sql = nl2sql_converter.convert(natural_language, connector_name)
                logger.info(
                    "Natural language query converted to SQL",
                    extra={
                        "natural_language": natural_language,
                        "sql": sql,
                        "connector_name": connector_name
                    }
                )
            except Exception as e:
                error_message = f"自然语言转换失败: {str(e)}"
                logger.error(error_message, exc_info=True)
                return QueryExecutionResult(
                    success=False,
                    error=error_message,
                    execution_time_ms=(time.time() - start_time) * 1000
                )

            # 执行生成的SQL
            return await self.execute_query(
                connector_name=connector_name,
                query=sql,
                params=params,
                user_id=user_id,
                role=role
            )

        except Exception as e:
            error_message = f"自然语言查询处理失败: {str(e)}"
            logger.error(error_message, exc_info=True)
            return QueryExecutionResult(
                success=False,
                error=error_message,
                execution_time_ms=(time.time() - start_time) * 1000
            )


# 全局查询引擎实例
query_engine = QueryEngine()
