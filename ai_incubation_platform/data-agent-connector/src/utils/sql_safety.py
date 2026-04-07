"""
SQL 安全检查工具
用于检测危险SQL语句，防止SQL注入和恶意操作
"""
import re
from typing import Tuple, List, Optional
from config.settings import settings


class SQLSecurityCheckResult:
    """SQL安全检查结果"""
    def __init__(
        self,
        is_safe: bool,
        reason: str = "",
        operation_type: str = "",
        error_code: str = ""
    ):
        self.is_safe = is_safe
        self.reason = reason
        self.operation_type = operation_type
        self.is_write_allowed = operation_type in settings.security.allow_write_operations
        self.error_code = error_code


class SQLSecurityChecker:
    """SQL安全检查器"""

    # SQL 操作类型正则
    OPERATION_PATTERNS = {
        'SELECT': re.compile(r'^\s*SELECT\s', re.IGNORECASE),
        'INSERT': re.compile(r'^\s*INSERT\s', re.IGNORECASE),
        'UPDATE': re.compile(r'^\s*UPDATE\s', re.IGNORECASE),
        'DELETE': re.compile(r'^\s*DELETE\s', re.IGNORECASE),
        'DROP': re.compile(r'^\s*DROP\s', re.IGNORECASE),
        'ALTER': re.compile(r'^\s*ALTER\s', re.IGNORECASE),
        'TRUNCATE': re.compile(r'^\s*TRUNCATE\s', re.IGNORECASE),
        'CREATE': re.compile(r'^\s*CREATE\s', re.IGNORECASE),
        'REPLACE': re.compile(r'^\s*REPLACE\s', re.IGNORECASE),
        'WITH': re.compile(r'^\s*WITH\s', re.IGNORECASE),
        'EXEC': re.compile(r'^\s*(EXEC|EXECUTE)\s', re.IGNORECASE),
        'UNION': re.compile(r'\bUNION\s+(ALL\s+)?SELECT\b', re.IGNORECASE),
        'COMMENT': re.compile(r'(--|#|/\*.*?\*/)', re.IGNORECASE | re.DOTALL),
        'MULTIPLE_STATEMENTS': re.compile(r';.*?[a-zA-Z]', re.DOTALL)
    }

    # 危险函数模式
    DANGEROUS_PATTERNS = [
        re.compile(r'\bINFORMATION_SCHEMA\b', re.IGNORECASE),
        re.compile(r'\bSYS\.(TABLES|DATABASES|SCHEMAS)\b', re.IGNORECASE),
        re.compile(r'\b(LOAD_FILE|INTO OUTFILE|INTO DUMPFILE)\b', re.IGNORECASE),
        re.compile(r'\b(EXEC|EXECUTE|SP_EXECUTESQL)\b', re.IGNORECASE),
        re.compile(r'\b(CMD_SHELL|XP_CMDSHELL)\b', re.IGNORECASE),
    ]

    @classmethod
    def check_sql_safety(cls, sql: str, role: str = "read_only") -> SQLSecurityCheckResult:
        """
        检查SQL语句安全性
        """
        sql = sql.strip()
        if not sql:
            return SQLSecurityCheckResult(False, "SQL语句为空", operation_type="UNKNOWN", error_code="sql_unsafe")

        # 检查多语句
        if cls.OPERATION_PATTERNS['MULTIPLE_STATEMENTS'].search(sql):
            top_level_op = cls._detect_operation_type(sql)
            return SQLSecurityCheckResult(False, "不允许多条SQL语句执行", operation_type=top_level_op, error_code="sql_unsafe")

        # 检查注释（暂不允许注释防止注入）
        if cls.OPERATION_PATTERNS['COMMENT'].search(sql):
            top_level_op = cls._detect_operation_type(sql)
            return SQLSecurityCheckResult(False, "SQL语句不允许包含注释", operation_type=top_level_op, error_code="sql_unsafe")

        # 检测操作类型
        operation_type = cls._detect_operation_type(sql)

        # 关键安全提升：危险写/DDL 关键词不再只看语句开头
        dangerous_ops_in_query = cls._find_dangerous_operations_in_anywhere(sql)
        if dangerous_ops_in_query:
            denied_op = dangerous_ops_in_query[0]

            # 只读角色：出现任何危险写/DDL 即拦截
            if role == "read_only":
                return SQLSecurityCheckResult(
                    False,
                    f"只读角色不允许执行 {denied_op} 操作",
                    denied_op,
                    error_code="permission_denied"
                )

            # 读写角色：仅允许 INSERT/UPDATE/DELETE，且 UPDATE/DELETE 必须包含 WHERE
            if role == "read_write":
                non_allowed = [op for op in dangerous_ops_in_query if op not in settings.security.allow_write_operations]
                if non_allowed:
                    denied_non_allowed_op = non_allowed[0]
                    return SQLSecurityCheckResult(
                        False,
                        f"读写角色不允许执行 {denied_non_allowed_op} 操作",
                        denied_non_allowed_op,
                        error_code="permission_denied"
                    )

                if any(op in {"UPDATE", "DELETE"} for op in dangerous_ops_in_query) and not cls._has_where_clause(sql):
                    where_op = next((op for op in dangerous_ops_in_query if op in {"UPDATE", "DELETE"}), "UPDATE")
                    return SQLSecurityCheckResult(
                        False,
                        f"{where_op} 语句必须包含WHERE条件",
                        where_op,
                        error_code="sql_unsafe"
                    )

        # 检查危险函数和模式
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern.search(sql):
                return SQLSecurityCheckResult(
                    False,
                    f"SQL包含危险函数或模式: {pattern.pattern}",
                    operation_type,
                    error_code="sql_unsafe"
                )

        # 检查UNION注入
        if operation_type == 'SELECT' and cls.OPERATION_PATTERNS['UNION'].search(sql):
            return SQLSecurityCheckResult(
                False,
                "不允许使用UNION查询",
                operation_type,
                error_code="sql_unsafe"
            )

        return SQLSecurityCheckResult(True, operation_type=operation_type)

    @classmethod
    def _detect_operation_type(cls, sql: str) -> str:
        """检测SQL操作类型"""
        # WITH ... SELECT 在语义上属于“读”查询（用于自动 LIMIT/审计等），
        # 即便内部包含数据修改语句，这里也按顶层 SELECT 处理。
        if cls.OPERATION_PATTERNS.get('WITH') and cls.OPERATION_PATTERNS['WITH'].match(sql):
            return 'SELECT'
        for op, pattern in cls.OPERATION_PATTERNS.items():
            if op in ['COMMENT', 'MULTIPLE_STATEMENTS', 'UNION']:
                continue
            if pattern.match(sql):
                return op
        return 'UNKNOWN'

    @classmethod
    def _strip_sql_literals(cls, sql: str) -> str:
        """移除/掩码字符串常量，减少对关键字的误判。"""
        sql = re.sub(r"'[^']*'", "''", sql)
        sql = re.sub(r'"[^"]*"', '""', sql)
        sql = re.sub(r'`[^`]*`', '``', sql)
        return sql

    @classmethod
    def _find_dangerous_operations_in_anywhere(cls, sql: str) -> List[str]:
        """
        在 SQL 任意位置查找危险 DML/DDL 关键词。
        返回值按“最先出现的顺序”排序（不去重，保证稳定）。
        """
        sql_clean = cls._strip_sql_literals(sql)
        found: List[tuple[int, str]] = []

        for op in settings.security.dangerous_operations:
            # 只做“词边界”匹配，减少误伤（如 colDROPX）
            m = re.search(rf'\b{re.escape(op)}\b', sql_clean, re.IGNORECASE)
            if m:
                found.append((m.start(), op.upper()))

        found.sort(key=lambda x: x[0])
        return [op for _, op in found]

    @classmethod
    def _has_where_clause(cls, sql: str) -> bool:
        """检查SQL是否包含WHERE子句"""
        # 先移除字符串内容避免误判
        sql_clean = re.sub(r"'[^']*'", "''", sql)
        sql_clean = re.sub(r'"[^"]*"', '""', sql_clean)
        return re.search(r'\bWHERE\b', sql_clean, re.IGNORECASE) is not None

    @classmethod
    def limit_query_rows(cls, sql: str, max_rows: int) -> str:
        """为查询添加LIMIT限制，防止返回过多数据"""
        sql = sql.rstrip(';')

        # 检查是否已有LIMIT子句
        if re.search(r'\bLIMIT\s+\d+', sql, re.IGNORECASE):
            # 检查现有LIMIT是否超过最大值
            match = re.search(r'\bLIMIT\s+(\d+)', sql, re.IGNORECASE)
            if match:
                existing_limit = int(match.group(1))
                if existing_limit > max_rows:
                    # 替换为更小的限制
                    sql = re.sub(r'\bLIMIT\s+\d+', f'LIMIT {max_rows}', sql, flags=re.IGNORECASE)
            return sql

        # SELECT / WITH 顶层语句添加LIMIT
        if cls.OPERATION_PATTERNS['SELECT'].match(sql) or (cls.OPERATION_PATTERNS.get('WITH') and cls.OPERATION_PATTERNS['WITH'].match(sql)):
            return f"{sql} LIMIT {max_rows}"

        return sql
