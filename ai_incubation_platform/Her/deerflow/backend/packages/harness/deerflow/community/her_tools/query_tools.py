"""
Her Tools - Safe Query Tool Module

安全的 SQL 查询工具：允许 Agent 在安全边界内自己生成查询语句。

【Agent Native 架构核心改进】
- Agent 不再只能调用预定义工具
- Agent 可以自己生成 SQL 来补齐缺失的信息
- 但有安全边界：只允许 SELECT，只允许特定表

解决的问题：
- 用户说"看看李明的详细介绍"
- Agent 知道名字"李明"，但不知道 user_id
- Agent 现在可以自己查询：SELECT id FROM users WHERE name='李明'
- 得到 ID 后，再调用 her_get_target_user

版本：v1.0.0 - 新增安全查询工具
"""
import logging
import json
import re
from typing import Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from .schemas import ToolResult, HerSafeQueryInput, HerFindUserByNameInput
from .helpers import ensure_her_in_path, run_async

logger = logging.getLogger(__name__)


# ==================== 安全边界配置 ====================

# 允许查询的表（白名单）
ALLOWED_TABLES = [
    "users",
    "profiles",
    "matches",
    "messages",
    "conversations",
]

# 禁止的关键词（黑名单）
FORBIDDEN_KEYWORDS = [
    "DELETE",
    "DROP",
    "UPDATE",
    "INSERT",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "EXEC",
    "EXECUTE",
    "GRANT",
    "REVOKE",
]


# ==================== Her Safe Query Tool ====================

class HerSafeQueryTool(BaseTool):
    """
    安全的 SQL 查询工具 - Agent Native 核心改进

    【设计原则】
    - Agent 可以自己生成 SQL 查询来补齐缺失信息
    - 但必须在安全边界内：只允许 SELECT，只允许白名单表
    - 这是 Agent Native 架构的"自主信息获取"能力

    【解决的问题】
    用户说"看看李明的详细介绍"
    → Agent 只有名字，没有 user_id
    → Agent 自己查询：SELECT id FROM users WHERE name='李明'
    → 得到 ID，再调用 her_get_target_user

    【安全边界】
    - 只允许 SELECT 语句
    - 只允许查询白名单表（users, profiles, matches 等）
    - 禁止 DELETE/DROP/UPDATE/INSERT 等修改操作
    - 自动限制返回行数（最多 10 行）
    """

    name: str = "her_safe_query"
    description: str = """
执行安全的 SQL 查询，用于补齐缺失的信息。

【使用场景】
当你知道某个实体的名字/属性，但缺少 ID 或其他关键信息时，可以自己生成查询。

示例场景：
- 用户说"看看李明的详细介绍"，但你只有名字"李明"，没有 user_id
- 你可以查询：SELECT id, name FROM users WHERE name='李明' LIMIT 1
- 得到 ID 后，再调用 her_get_target_user

【安全边界】
- 只允许 SELECT 语句
- 只允许查询：users, profiles, matches, messages 表
- 自动限制最多返回 10 行
- 禁止修改数据（DELETE/DROP/UPDATE/INSERT）

【参数】
sql: SQL 查询语句（必须是 SELECT）

【返回】
{ "rows": [...], "columns": [...], "row_count": N }

Agent 应该：
- 解析返回的 rows，提取需要的信息（如 user_id）
- 继续执行后续操作（如调用 her_get_target_user）
"""

    args_schema: Type[BaseModel] = HerSafeQueryInput

    def _run(self, sql: str) -> str:
        # 安全校验
        validation_result = self._validate_sql(sql)
        if not validation_result["valid"]:
            return json.dumps(ToolResult(
                success=False,
                error=validation_result["error"],
                summary="SQL 查询被安全边界拒绝"
            ).model_dump(), ensure_ascii=False)

        try:
            result = run_async(self._arun(sql))
        except Exception as e:
            logger.error(f"[her_safe_query] 查询执行失败: {e}")
            return json.dumps(ToolResult(
                success=False,
                error=str(e),
                summary="SQL 查询执行失败"
            ).model_dump(), ensure_ascii=False)

        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, sql: str) -> ToolResult:
        """执行安全的 SQL 查询"""
        ensure_her_in_path()

        try:
            from utils.db_session_manager import db_session
            from sqlalchemy import text

            # 自动添加 LIMIT（如果没有）
            safe_sql = self._add_limit_if_missing(sql)

            with db_session() as db:
                result = db.execute(text(safe_sql))

                # 获取列名
                columns = list(result.keys()) if result.returns_rows else []

                # 获取数据行
                rows = []
                if result.returns_rows:
                    for row in result:
                        row_dict = {}
                        for i, col in enumerate(columns):
                            value = row[i]
                            # 处理特殊类型
                            if value is not None:
                                if hasattr(value, 'isoformat'):
                                    value = value.isoformat()
                                elif isinstance(value, bytes):
                                    value = value.decode('utf-8', errors='ignore')
                            row_dict[col] = value
                        rows.append(row_dict)

                logger.info(f"[her_safe_query] 查询成功: {len(rows)} 行, SQL: {safe_sql[:100]}")

                return ToolResult(
                    success=True,
                    data={
                        "rows": rows,
                        "columns": columns,
                        "row_count": len(rows),
                        "query": safe_sql,
                    },
                    summary=f"查询成功，返回 {len(rows)} 行数据"
                )

        except Exception as e:
            logger.error(f"[her_safe_query] 执行失败: {e}")
            return ToolResult(
                success=False,
                error=f"SQL 执行错误: {str(e)}",
                summary="查询执行失败"
            )

    def _validate_sql(self, sql: str) -> dict:
        """
        校验 SQL 是否安全

        安全边界：
        1. 必须是 SELECT 语句
        2. 不能包含禁止关键词
        3. 只能查询白名单表
        """
        sql_upper = sql.strip().upper()

        # 检查 1：必须是 SELECT
        if not sql_upper.startswith("SELECT"):
            return {
                "valid": False,
                "error": "安全边界：只允许 SELECT 查询"
            }

        # 检查 2：禁止关键词
        for keyword in FORBIDDEN_KEYWORDS:
            if keyword in sql_upper:
                return {
                    "valid": False,
                    "error": f"安全边界：禁止使用 {keyword} 操作"
                }

        # 检查 3：白名单表
        # 提取 SQL 中的表名（简单正则匹配）
        table_pattern = r'\bFROM\s+(\w+)|\bJOIN\s+(\w+)'
        tables_found = re.findall(table_pattern, sql_upper)
        tables = [t[0] or t[1] for t in tables_found]

        for table in tables:
            if table.lower() not in ALLOWED_TABLES:
                return {
                    "valid": False,
                    "error": f"安全边界：表 '{table}' 不在白名单内，允许的表：{ALLOWED_TABLES}"
                }

        return {"valid": True, "error": None}

    def _add_limit_if_missing(self, sql: str) -> str:
        """自动添加 LIMIT（防止返回过多数据）"""
        sql_upper = sql.strip().upper()

        if "LIMIT" not in sql_upper:
            # 在末尾添加 LIMIT 10
            return sql.strip() + " LIMIT 10"

        return sql.strip()


class HerFindUserByNameTool(BaseTool):
    """
    按名字查找用户工具 - 更便捷的封装

    对于不想自己写 SQL 的 Agent，提供这个便捷工具。
    直接传名字，返回匹配的用户列表。
    """

    name: str = "her_find_user_by_name"
    description: str = """
【触发条件】当你只有用户名字，需要获取 user_id 时调用。

【使用场景】用户说"看看李明的详细介绍" → 你只有名字"李明" → 调用此工具获取 user_id → 再调用 her_get_target_user。

【参数】
- name: 用户名字
- location: 城市（可选）

【返回】用户列表（含 user_id）。
"""

    args_schema: Type[BaseModel] = HerFindUserByNameInput

    def _run(self, name: str, location: str = "", limit: int = 5) -> str:
        try:
            result = run_async(self._arun(name, location, limit))
        except Exception as e:
            return json.dumps(ToolResult(
                success=False,
                error=str(e),
                summary="查询失败"
            ).model_dump(), ensure_ascii=False)

        return json.dumps(result.model_dump(), ensure_ascii=False)

    async def _arun(self, name: str, location: str = "", limit: int = 5) -> ToolResult:
        """根据名字查找用户"""
        ensure_her_in_path()

        try:
            from utils.db_session_manager import db_session
            from db.models import UserDB
            from sqlalchemy import or_

            with db_session() as db:
                # 构建查询条件
                query = db.query(UserDB)

                # 名字匹配（支持模糊匹配）
                query = query.filter(UserDB.name.ilike(f"%{name}%"))

                # 如果有地点，添加地点条件
                if location:
                    query = query.filter(UserDB.location.ilike(f"%{location}%"))

                # 限制数量
                query = query.limit(limit)

                users = query.all()

                # 构建返回数据
                user_list = []
                for u in users:
                    user_list.append({
                        "user_id": u.id,
                        "name": u.name,
                        "age": u.age or 0,
                        "gender": u.gender or "",
                        "location": u.location or "",
                        "occupation": u.occupation or "",
                        "interests": json.loads(u.interests) if u.interests else [],
                    })

                logger.info(f"[her_find_user_by_name] 找到 {len(user_list)} 个用户，名字={name}")

                return ToolResult(
                    success=True,
                    data={
                        "users": user_list,
                        "total": len(user_list),
                        "query_name": name,
                    },
                    summary=f"找到 {len(user_list)} 个匹配 '{name}' 的用户"
                )

        except Exception as e:
            logger.error(f"[her_find_user_by_name] 查询失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                summary="查询失败"
            )


# ==================== Tool Instances ====================

her_safe_query_tool = HerSafeQueryTool()
her_find_user_by_name_tool = HerFindUserByNameTool()


# ==================== Exports ====================

__all__ = [
    "HerSafeQueryTool",
    "HerFindUserByNameTool",
    "her_safe_query_tool",
    "her_find_user_by_name_tool",
]