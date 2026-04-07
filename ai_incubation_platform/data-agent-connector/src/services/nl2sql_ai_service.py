"""
NL2SQL AI 服务 - 基于 LLM 的自然语言转 SQL 服务

功能:
1. LLM 集成用于 SQL 生成
2. 查询意图识别
3. SQL 验证和安全检查
4. 查询优化建议
5. 结果解释生成
"""
from typing import Optional, Dict, Any, List, Tuple
import json
import re
from datetime import datetime
from abc import ABC, abstractmethod

from utils.logger import logger
from config.settings import settings


class QueryIntent:
    """查询意图识别结果"""

    # 意图类型
    SIMPLE_SELECT = "simple_select"  # 简单查询
    CONDITIONAL_QUERY = "conditional_query"  # 条件查询
    AGGREGATION = "aggregation"  # 聚合统计
    GROUP_BY = "group_by"  # 分组统计
    ORDER_BY = "order_by"  # 排序查询
    JOIN = "join"  # 多表 JOIN
    TIME_RANGE = "time_range"  # 时间范围查询
    COMPARISON = "comparison"  # 对比分析
    TREND = "trend"  # 趋势分析
    TOP_N = "top_n"  # Top N 查询
    COMPLEX = "complex"  # 复杂查询

    def __init__(
        self,
        intent_type: str,
        confidence: float,
        tables: List[str],
        columns: List[str],
        conditions: List[Dict[str, Any]],
        aggregations: List[Dict[str, str]],
        order_by: Optional[Dict[str, str]],
        limit: Optional[int],
        time_range: Optional[Dict[str, str]],
        join_info: Optional[List[Dict[str, Any]]] = None
    ):
        self.intent_type = intent_type
        self.confidence = confidence
        self.tables = tables
        self.columns = columns
        self.conditions = conditions
        self.aggregations = aggregations
        self.order_by = order_by
        self.limit = limit
        self.time_range = time_range
        self.join_info = join_info or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_type": self.intent_type,
            "confidence": self.confidence,
            "tables": self.tables,
            "columns": self.columns,
            "conditions": self.conditions,
            "aggregations": self.aggregations,
            "order_by": self.order_by,
            "limit": self.limit,
            "time_range": self.time_range,
            "join_info": self.join_info
        }


class SQLValidationResult:
    """SQL 验证结果"""

    def __init__(
        self,
        is_valid: bool,
        errors: List[str],
        warnings: List[str],
        suggestions: List[str]
    ):
        self.is_valid = is_valid
        self.errors = errors
        self.warnings = warnings
        self.suggestions = suggestions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions
        }


class LLMProvider(ABC):
    """LLM 提供商抽象基类"""

    @abstractmethod
    async def generate_sql(
        self,
        natural_language: str,
        schema: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, float]:
        """生成 SQL 并返回置信度"""
        pass

    @abstractmethod
    async def recognize_intent(
        self,
        natural_language: str,
        schema: Dict[str, Any]
    ) -> QueryIntent:
        """识别查询意图"""
        pass

    @abstractmethod
    async def explain_result(
        self,
        natural_language: str,
        sql: str,
        result: List[Dict[str, Any]],
        schema: Dict[str, Any]
    ) -> str:
        """解释查询结果"""
        pass

    @abstractmethod
    async def suggest_optimization(
        self,
        sql: str,
        schema: Dict[str, Any],
        execution_stats: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """生成查询优化建议"""
        pass


class AnthropicLLMProvider(LLMProvider):
    """Anthropic Claude LLM 提供商"""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key or getattr(settings, 'anthropic_api_key', None)
        self.model = model
        self._client = None

    def _get_client(self):
        """懒加载 LLM 客户端"""
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
                self._client = AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                logger.error("Anthropic SDK not installed. Run: pip install anthropic")
                raise
        return self._client

    async def generate_sql(
        self,
        natural_language: str,
        schema: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, float]:
        """使用 Claude 生成 SQL"""
        client = self._get_client()

        schema_str = self._format_schema(schema)
        context_str = json.dumps(context, ensure_ascii=False) if context else "无"

        prompt = f"""你是一个专业的 SQL 专家。请根据以下数据库 Schema，将用户的自然语言查询转换为准确的 SQL 语句。

## 数据库 Schema
{schema_str}

## 查询上下文
{context_str}

## 用户查询
{natural_language}

## 要求
1. 只输出 SQL 语句，不要包含其他解释
2. 使用标准 SQL 语法
3. 确保表名和列名与 Schema 一致
4. 如果查询涉及多表 JOIN，请明确指定关联条件
5. 如果查询模糊或不完整，请基于 Schema 做出合理假设

## SQL 语句
"""

        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            sql = response.content[0].text.strip()
            # 清理 SQL 语句，去除 Markdown 代码块标记
            sql = re.sub(r'^```sql\s*|\s*```$', '', sql).strip()
            sql = re.sub(r'^```\s*|\s*```$', '', sql).strip()

            # 估算置信度（基于响应长度和 SQL 结构完整性）
            confidence = self._estimate_confidence(sql, schema)

            logger.info(
                "LLM generated SQL",
                extra={
                    "natural_language": natural_language,
                    "sql": sql,
                    "confidence": confidence
                }
            )

            return sql, confidence

        except Exception as e:
            logger.error("LLM SQL generation failed", extra={"error": str(e)})
            raise

    async def recognize_intent(
        self,
        natural_language: str,
        schema: Dict[str, Any]
    ) -> QueryIntent:
        """使用 Claude 识别查询意图"""
        client = self._get_client()

        schema_str = self._format_schema(schema)

        prompt = f"""你是一个专业的数据分析师。请分析用户的自然语言查询，识别其查询意图。

## 数据库 Schema
{schema_str}

## 用户查询
{natural_language}

## 任务
分析查询意图，输出 JSON 格式结果：
{{
    "intent_type": "意图类型",
    "confidence": 0.0-1.0 之间的置信度,
    "tables": ["涉及的表名列表"],
    "columns": ["涉及的列名列表"],
    "conditions": [{{"column": "列名", "operator": "操作符", "value": "值"}}],
    "aggregations": [{{"function": "COUNT|SUM|AVG|MAX|MIN", "column": "列名"}}],
    "order_by": {{"column": "列名", "direction": "ASC|DESC"}},
    "limit": 数字或 null,
    "time_range": {{"start": "开始时间", "end": "结束时间"}} 或 null,
    "join_info": [{{"left_table": "左表", "right_table": "右表", "condition": "关联条件"}}]
}}

意图类型选项：
- simple_select: 简单查询（如"查询所有用户"）
- conditional_query: 条件查询（如"查询年龄大于 18 的用户"）
- aggregation: 聚合统计（如"统计用户总数"）
- group_by: 分组统计（如"按部门分组统计用户数量"）
- order_by: 排序查询（如"按工资降序排列"）
- join: 多表 JOIN（如"查询每个用户的订单"）
- time_range: 时间范围查询（如"查询上个月的订单"）
- comparison: 对比分析（如"比较各部门的平均工资"）
- trend: 趋势分析（如"分析销售额的月度趋势"）
- top_n: Top N 查询（如"销售额前 10 的产品"）
- complex: 复杂查询（多种意图组合）

## JSON 结果
"""

        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            content = response.content[0].text.strip()
            # 清理 Markdown 代码块标记
            content = re.sub(r'^```json\s*|\s*```$', '', content).strip()
            content = re.sub(r'^```\s*|\s*```$', '', content).strip()

            intent_data = json.loads(content)

            intent = QueryIntent(
                intent_type=intent_data.get("intent_type", "simple_select"),
                confidence=intent_data.get("confidence", 0.5),
                tables=intent_data.get("tables", []),
                columns=intent_data.get("columns", []),
                conditions=intent_data.get("conditions", []),
                aggregations=intent_data.get("aggregations", []),
                order_by=intent_data.get("order_by"),
                limit=intent_data.get("limit"),
                time_range=intent_data.get("time_range"),
                join_info=intent_data.get("join_info", [])
            )

            logger.info(
                "Query intent recognized",
                extra={
                    "natural_language": natural_language,
                    "intent_type": intent.intent_type,
                    "confidence": intent.confidence
                }
            )

            return intent

        except Exception as e:
            logger.error("Intent recognition failed", extra={"error": str(e)})
            # 返回默认意图
            return QueryIntent(
                intent_type="simple_select",
                confidence=0.5,
                tables=[],
                columns=[],
                conditions=[],
                aggregations=[],
                order_by=None,
                limit=None,
                time_range=None,
                join_info=[]
            )

    async def explain_result(
        self,
        natural_language: str,
        sql: str,
        result: List[Dict[str, Any]],
        schema: Dict[str, Any]
    ) -> str:
        """使用 Claude 解释查询结果"""
        client = self._get_client()

        # 限制结果长度以避免过长
        result_preview = result[:10] if len(result) > 10 else result
        result_summary = f"共 {len(result)} 条结果，以下是前 {len(result_preview)} 条:"

        result_str = json.dumps(result_preview, ensure_ascii=False, indent=2)

        prompt = f"""你是一个专业的数据分析师。请根据以下信息，用简洁易懂的中文解释查询结果。

## 用户原始查询
{natural_language}

## 执行的 SQL
{sql}

## 查询结果
{result_summary}
{result_str}

## 要求
1. 用自然语言描述结果
2. 突出关键洞察和数据趋势
3. 如果结果异常或为空，说明可能的原因
4. 控制解释长度在 200 字以内

## 结果解释
"""

        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=300,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            explanation = response.content[0].text.strip()

            logger.info("Result explanation generated", extra={"length": len(explanation)})

            return explanation

        except Exception as e:
            logger.error("Result explanation failed", extra={"error": str(e)})
            return f"查询返回 {len(result)} 条结果。"

    async def suggest_optimization(
        self,
        sql: str,
        schema: Dict[str, Any],
        execution_stats: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """使用 Claude 生成查询优化建议"""
        client = self._get_client()

        schema_str = self._format_schema(schema)
        stats_str = json.dumps(execution_stats, ensure_ascii=False) if execution_stats else "无"

        prompt = f"""你是一个数据库性能优化专家。请分析以下 SQL 查询并提供优化建议。

## 数据库 Schema
{schema_str}

## SQL 查询
{sql}

## 执行统计
{stats_str}

## 要求
1. 分析 SQL 可能存在的性能问题
2. 提供具体的优化建议
3. 每条建议单独一行，以短横线开头
4. 如果没有明显问题，输出"无明显优化空间"

## 优化建议
"""

        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            content = response.content[0].text.strip()

            # 解析建议为列表
            suggestions = []
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('-') or line.startswith('*'):
                    suggestions.append(line[1:].strip())
                elif line and not line.startswith('#'):
                    suggestions.append(line)

            logger.info("Optimization suggestions generated", extra={"count": len(suggestions)})

            return suggestions

        except Exception as e:
            logger.error("Optimization suggestion failed", extra={"error": str(e)})
            return []

    def _format_schema(self, schema: Dict[str, Any]) -> str:
        """格式化 Schema 为可读字符串"""
        lines = []

        tables = schema.get('tables', {})
        for table_name, columns in tables.items():
            lines.append(f"表：{table_name}")
            for col in columns:
                col_type = col.get('type', 'unknown')
                col_name = col.get('name', 'unknown')
                nullable = "NULL" if col.get('nullable', True) else "NOT NULL"
                lines.append(f"  - {col_name} ({col_type}) {nullable}")
            lines.append("")

        return '\n'.join(lines)

    def _estimate_confidence(self, sql: str, schema: Dict[str, Any]) -> float:
        """估算 SQL 生成的置信度"""
        confidence = 0.5

        # 检查 SQL 基本结构
        if re.match(r'^SELECT\s+.+\s+FROM\s+\w+', sql, re.IGNORECASE):
            confidence += 0.2

        # 检查表名是否在 Schema 中
        tables = schema.get('tables', {}).keys()
        for table in tables:
            if table.lower() in sql.lower():
                confidence += 0.15
                break

        # 检查 SQL 长度是否合理
        if 20 < len(sql) < 1000:
            confidence += 0.15

        return min(confidence, 1.0)


class NL2SQLAIService:
    """NL2SQL AI 服务"""

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self._llm_provider = llm_provider or AnthropicLLMProvider()
        self._query_history: List[Dict[str, Any]] = []

    @property
    def llm_provider(self) -> LLMProvider:
        return self._llm_provider

    @llm_provider.setter
    def llm_provider(self, provider: LLMProvider):
        self._llm_provider = provider

    async def convert_to_sql(
        self,
        natural_language: str,
        schema: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        将自然语言转换为 SQL

        Args:
            natural_language: 自然语言查询
            schema: 数据库 Schema
            context: 查询上下文
            use_llm: 是否使用 LLM（False 则使用规则匹配）

        Returns:
            {
                "sql": "生成的 SQL",
                "intent": QueryIntent,
                "confidence": 0.0-1.0,
                "validation": SQLValidationResult,
                "suggestions": ["优化建议"]
            }
        """
        logger.info(
            "Converting natural language to SQL",
            extra={
                "natural_language": natural_language,
                "use_llm": use_llm
            }
        )

        # 1. 意图识别
        try:
            intent = await self._llm_provider.recognize_intent(natural_language, schema)
        except Exception as e:
            logger.warning("Intent recognition failed, using default", extra={"error": str(e)})
            intent = QueryIntent(
                intent_type="simple_select",
                confidence=0.5,
                tables=[],
                columns=[],
                conditions=[],
                aggregations=[],
                order_by=None,
                limit=None,
                time_range=None
            )

        # 2. SQL 生成
        try:
            if use_llm:
                sql, confidence = await self._llm_provider.generate_sql(
                    natural_language, schema, context
                )
            else:
                # 使用规则匹配（降级方案）
                from nl2sql.converter import nl2sql_converter
                sql = nl2sql_converter.convert(natural_language)
                confidence = 0.5
        except Exception as e:
            logger.error("SQL generation failed", extra={"error": str(e)})
            return {
                "sql": "",
                "intent": intent,
                "confidence": 0.0,
                "validation": SQLValidationResult(
                    is_valid=False,
                    errors=[f"SQL 生成失败：{str(e)}"],
                    warnings=[],
                    suggestions=[]
                ).to_dict(),
                "suggestions": []
            }

        # 3. SQL 验证
        validation = self._validate_sql(sql, schema)

        # 4. 优化建议
        suggestions = await self._llm_provider.suggest_optimization(sql, schema)

        # 5. 记录历史
        self._query_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "natural_language": natural_language,
            "sql": sql,
            "intent": intent.to_dict(),
            "confidence": confidence
        })

        return {
            "sql": sql,
            "intent": intent.to_dict(),
            "confidence": confidence,
            "validation": validation.to_dict(),
            "suggestions": suggestions
        }

    async def explain_result(
        self,
        natural_language: str,
        sql: str,
        result: List[Dict[str, Any]],
        schema: Dict[str, Any]
    ) -> str:
        """解释查询结果"""
        return await self._llm_provider.explain_result(natural_language, sql, result, schema)

    def _validate_sql(self, sql: str, schema: Dict[str, Any]) -> SQLValidationResult:
        """验证 SQL 的有效性"""
        errors = []
        warnings = []
        suggestions = []

        # 1. 基本语法检查
        sql_upper = sql.upper().strip()
        if not sql_upper.startswith('SELECT'):
            errors.append("只支持 SELECT 查询语句")

        # 2. 表名验证
        tables_in_schema = set(t.lower() for t in schema.get('tables', {}).keys())
        import re
        from_matches = re.findall(r'FROM\s+(\w+)', sql, re.IGNORECASE)
        join_matches = re.findall(r'JOIN\s+(\w+)', sql, re.IGNORECASE)
        all_tables = from_matches + join_matches

        for table in all_tables:
            if table.lower() not in tables_in_schema:
                errors.append(f"表 '{table}' 不在 Schema 中")

        # 3. SQL 安全检查
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE']
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                errors.append(f"包含危险关键字：{keyword}")

        # 4. 性能警告
        if 'SELECT *' in sql_upper:
            warnings.append("使用 SELECT * 可能影响性能，建议指定具体列")

        if 'WHERE' not in sql_upper and 'LIMIT' not in sql_upper:
            warnings.append("查询没有 WHERE 条件或 LIMIT 限制，可能返回大量数据")

        # 5. 优化建议
        if 'DISTINCT' in sql_upper and 'GROUP BY' not in sql_upper:
            suggestions.append("考虑使用 GROUP BY 替代 DISTINCT 可能性能更好")

        if 'ORDER BY' in sql_upper and 'LIMIT' not in sql_upper:
            suggestions.append("ORDER BY 查询建议添加 LIMIT 限制返回数量")

        is_valid = len(errors) == 0

        return SQLValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )

    def get_query_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取查询历史"""
        return self._query_history[-limit:]

    def clear_history(self):
        """清空查询历史"""
        self._query_history.clear()


# 全局服务实例
nl2sql_ai_service = NL2SQLAIService()
