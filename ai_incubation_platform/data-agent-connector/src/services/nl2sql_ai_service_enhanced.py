"""
NL2SQL AI 服务增强版 - v1.3 准确率提升

新增功能:
1. Few-Shot 示例学习
2. Schema 关系增强
3. 查询澄清机制
4. SQL 自校正
5. 查询历史学习
"""
from typing import Optional, Dict, Any, List, Tuple, Set
import json
import re
import hashlib
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import asyncio

from utils.logger import logger
from config.settings import settings


# ============== 新增数据模型 ==============

class QueryExample:
    """查询示例（用于 Few-Shot Learning）"""

    def __init__(
        self,
        id: str,
        natural_language: str,
        sql: str,
        intent_type: str,
        tables: List[str],
        difficulty: str = "medium",
        success_rate: float = 1.0,
        usage_count: int = 0,
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.natural_language = natural_language
        self.sql = sql
        self.intent_type = intent_type
        self.tables = tables
        self.difficulty = difficulty
        self.success_rate = success_rate
        self.usage_count = usage_count
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "natural_language": self.natural_language,
            "sql": self.sql,
            "intent_type": self.intent_type,
            "tables": self.tables,
            "difficulty": self.difficulty,
            "success_rate": self.success_rate,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryExample":
        return cls(
            id=data["id"],
            natural_language=data["natural_language"],
            sql=data["sql"],
            intent_type=data["intent_type"],
            tables=data["tables"],
            difficulty=data.get("difficulty", "medium"),
            success_rate=data.get("success_rate", 1.0),
            usage_count=data.get("usage_count", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
        )


class SchemaRelation:
    """Schema 关系信息"""

    def __init__(
        self,
        source_table: str,
        target_table: str,
        relation_type: str,  # "one_to_many", "many_to_one", "one_to_one"
        source_columns: List[str],
        target_columns: List[str],
        description: Optional[str] = None
    ):
        self.source_table = source_table
        self.target_table = target_table
        self.relation_type = relation_type
        self.source_columns = source_columns
        self.target_columns = target_columns
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_table": self.source_table,
            "target_table": self.target_table,
            "relation_type": self.relation_type,
            "source_columns": self.source_columns,
            "target_columns": self.target_columns,
            "description": self.description
        }


class ClarificationQuestion:
    """澄清问题"""

    def __init__(
        self,
        question: str,
        options: List[str],
        reason: str
    ):
        self.question = question
        self.options = options
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "options": self.options,
            "reason": self.reason
        }


class SQLCorrectionResult:
    """SQL 校正结果"""

    def __init__(
        self,
        original_sql: str,
        corrected_sql: str,
        error_message: str,
        correction_reason: str,
        success: bool
    ):
        self.original_sql = original_sql
        self.corrected_sql = corrected_sql
        self.error_message = error_message
        self.correction_reason = correction_reason
        self.success = success

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_sql": self.original_sql,
            "corrected_sql": self.corrected_sql,
            "error_message": self.error_message,
            "correction_reason": self.correction_reason,
            "success": self.success
        }


# ============== 示例库管理器 ==============

class ExampleLibrary:
    """查询示例库管理器"""

    def __init__(self):
        self._examples: List[QueryExample] = []
        self._builtin_examples = self._load_builtin_examples()

    def _load_builtin_examples(self) -> List[QueryExample]:
        """加载内置示例"""
        return [
            # 简单查询示例
            QueryExample(
                id="ex_001",
                natural_language="查询所有用户",
                sql="SELECT * FROM users",
                intent_type="simple_select",
                tables=["users"],
                difficulty="easy",
                success_rate=1.0
            ),
            QueryExample(
                id="ex_002",
                natural_language="查询年龄大于 18 岁的用户",
                sql="SELECT * FROM users WHERE age > 18",
                intent_type="conditional_query",
                tables=["users"],
                difficulty="easy",
                success_rate=1.0
            ),
            # 聚合查询示例
            QueryExample(
                id="ex_003",
                natural_language="统计用户总数",
                sql="SELECT COUNT(*) as total FROM users",
                intent_type="aggregation",
                tables=["users"],
                difficulty="easy",
                success_rate=1.0
            ),
            QueryExample(
                id="ex_004",
                natural_language="按部门分组统计用户数量",
                sql="SELECT department, COUNT(*) as count FROM users GROUP BY department",
                intent_type="group_by",
                tables=["users"],
                difficulty="medium",
                success_rate=1.0
            ),
            # 排序和限制示例
            QueryExample(
                id="ex_005",
                natural_language="查询工资最高的前 10 名员工",
                sql="SELECT * FROM employees ORDER BY salary DESC LIMIT 10",
                intent_type="top_n",
                tables=["employees"],
                difficulty="medium",
                success_rate=1.0
            ),
            # JOIN 查询示例
            QueryExample(
                id="ex_006",
                natural_language="查询每个用户的订单数量",
                sql="SELECT u.id, u.name, COUNT(o.id) as order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.id, u.name",
                intent_type="join",
                tables=["users", "orders"],
                difficulty="hard",
                success_rate=0.95
            ),
            # 时间范围查询示例
            QueryExample(
                id="ex_007",
                natural_language="查询上个月的订单",
                sql="SELECT * FROM orders WHERE created_at >= date_trunc('month', CURRENT_DATE - INTERVAL '1 month') AND created_at < date_trunc('month', CURRENT_DATE)",
                intent_type="time_range",
                tables=["orders"],
                difficulty="hard",
                success_rate=0.9
            ),
            # 复杂查询示例
            QueryExample(
                id="ex_008",
                natural_language="查询销售额前 10 的产品及其所属分类",
                sql="SELECT p.name, c.name as category, SUM(oi.quantity * oi.price) as total_sales FROM products p JOIN categories c ON p.category_id = c.id JOIN order_items oi ON p.id = oi.product_id GROUP BY p.id, p.name, c.name ORDER BY total_sales DESC LIMIT 10",
                intent_type="complex",
                tables=["products", "categories", "order_items"],
                difficulty="hard",
                success_rate=0.85
            ),
            # 模糊查询示例
            QueryExample(
                id="ex_009",
                natural_language="查询名字包含'张'的用户",
                sql="SELECT * FROM users WHERE name LIKE '%张%'",
                intent_type="conditional_query",
                tables=["users"],
                difficulty="easy",
                success_rate=1.0
            ),
            # 子查询示例
            QueryExample(
                id="ex_010",
                natural_language="查询购买过产品 A 的用户",
                sql="SELECT DISTINCT u.* FROM users u JOIN orders o ON u.id = o.user_id JOIN order_items oi ON o.id = oi.order_id JOIN products p ON oi.product_id = p.id WHERE p.name = '产品 A'",
                intent_type="complex",
                tables=["users", "orders", "order_items", "products"],
                difficulty="hard",
                success_rate=0.85
            )
        ]

    def add_example(self, example: QueryExample) -> None:
        """添加示例"""
        self._examples.append(example)
        logger.debug(f"Added query example: {example.id}")

    def get_similar_examples(
        self,
        natural_language: str,
        intent_type: Optional[str] = None,
        tables: Optional[List[str]] = None,
        limit: int = 3
    ) -> List[QueryExample]:
        """获取相似的示例"""
        scored_examples = []

        for example in self._builtin_examples + self._examples:
            score = 0.0

            # 意图匹配
            if intent_type and example.intent_type == intent_type:
                score += 2.0

            # 表匹配
            if tables:
                matching_tables = set(tables) & set(example.tables)
                score += len(matching_tables) * 1.0

            # 关键词匹配
            nl_words = set(natural_language.lower().split())
            example_words = set(example.natural_language.lower().split())
            word_overlap = len(nl_words & example_words)
            score += word_overlap * 0.5

            # 成功率加权
            score *= example.success_rate

            # 使用次数加权（避免过度使用同一示例）
            score /= (1 + example.usage_count * 0.1)

            scored_examples.append((score, example))

        # 按分数排序并返回 top N
        scored_examples.sort(key=lambda x: x[0], reverse=True)
        return [ex for score, ex in scored_examples[:limit]]

    def record_usage(self, example_id: str, success: bool) -> None:
        """记录示例使用情况"""
        for example in self._builtin_examples + self._examples:
            if example.id == example_id:
                example.usage_count += 1
                # 指数移动平均更新成功率
                new_success = 1.0 if success else 0.0
                example.success_rate = 0.8 * example.success_rate + 0.2 * new_success
                break

    @property
    def all_examples(self) -> List[QueryExample]:
        """获取所有示例"""
        return self._builtin_examples + self._examples

    @property
    def example_count(self) -> int:
        """获取示例数量"""
        return len(self._builtin_examples) + len(self._examples)


# ============== Schema 关系管理器 ==============

class SchemaRelationManager:
    """Schema 关系管理器"""

    def __init__(self):
        self._relations: Dict[str, List[SchemaRelation]] = {}
        self._foreign_keys: Dict[str, Dict[str, str]] = {}

    def add_relation(
        self,
        source_table: str,
        target_table: str,
        relation_type: str,
        source_columns: List[str],
        target_columns: List[str],
        description: Optional[str] = None
    ) -> None:
        """添加表关系"""
        key = f"{source_table}_{target_table}"
        relation = SchemaRelation(
            source_table=source_table,
            target_table=target_table,
            relation_type=relation_type,
            source_columns=source_columns,
            target_columns=target_columns,
            description=description
        )

        if source_table not in self._relations:
            self._relations[source_table] = []
        self._relations[source_table].append(relation)

        # 记录外键关系
        for src_col, tgt_col in zip(source_columns, target_columns):
            self._foreign_keys[f"{source_table}.{src_col}"] = f"{target_table}.{tgt_col}"

    def get_relations(self, table: str) -> List[SchemaRelation]:
        """获取表的关联关系"""
        return self._relations.get(table, [])

    def get_join_path(self, source_table: str, target_table: str) -> Optional[List[SchemaRelation]]:
        """获取两表之间的 JOIN 路径（BFS）"""
        if source_table == target_table:
            return []

        visited = {source_table}
        queue = [(source_table, [])]

        while queue:
            current_table, path = queue.pop(0)

            for relation in self._relations.get(current_table, []):
                if relation.target_table == target_table:
                    return path + [relation]

                if relation.target_table not in visited:
                    visited.add(relation.target_table)
                    queue.append((relation.target_table, path + [relation]))

        # 尝试反向查找
        for table, relations in self._relations.items():
            for relation in relations:
                if relation.source_table == target_table and relation.target_table == source_table:
                    # 反向关系
                    return [SchemaRelation(
                        source_table=relation.target_table,
                        target_table=relation.source_table,
                        relation_type=relation.relation_type,
                        source_columns=relation.target_columns,
                        target_columns=relation.source_columns,
                        description=relation.description
                    )]

        return None

    def format_relations_for_prompt(self, tables: List[str]) -> str:
        """格式化关系为 Prompt 文本"""
        lines = []

        for table in tables:
            relations = self.get_relations(table)
            if relations:
                lines.append(f"\n表 '{table}' 的关联关系:")
                for rel in relations:
                    join_cond = " AND ".join([
                        f"{rel.source_table}.{sc} = {rel.target_table}.{tc}"
                        for sc, tc in zip(rel.source_columns, rel.target_columns)
                    ])
                    lines.append(f"  - {rel.relation_type}: {rel.target_table} (关联条件：{join_cond})")

        return "\n".join(lines) if lines else "\n无显式关联关系，需要根据外键推断 JOIN 条件"

    def auto_discover_relations(self, schema: Dict[str, Any]) -> None:
        """从 Schema 中自动发现关系"""
        tables = schema.get('tables', {})

        # 查找命名约定暗示的关系
        for table_name, columns in tables.items():
            for col in columns:
                col_name = col.get('name', '').lower()

                # 检测外键列（如 user_id, order_id）
                if col_name.endswith('_id') and col_name != 'id':
                    referenced_table = col_name[:-3]  # 去掉 _id

                    # 检查是否存在对应的表
                    if referenced_table in tables or referenced_table + 's' in tables:
                        target_table = referenced_table if referenced_table in tables else referenced_table + 's'
                        self.add_relation(
                            source_table=table_name,
                            target_table=target_table,
                            relation_type="many_to_one",
                            source_columns=[col['name']],
                            target_columns=['id'],
                            description=f"自动发现：{table_name}.{col['name']} -> {target_table}.id"
                        )


# ============== 增强的 LLM 提供商 ==============

class EnhancedAnthropicLLMProvider:
    """增强的 Anthropic LLM 提供商 - 支持 Few-Shot 和关系感知"""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model = model
        self._client = None
        self._example_library = ExampleLibrary()
        self._relation_manager = SchemaRelationManager()

    def _get_client(self):
        """懒加载客户端"""
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
                self._client = AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                logger.error("Anthropic SDK not installed")
                raise
        return self._client

    def _format_schema_with_relations(self, schema: Dict[str, Any], tables: Optional[List[str]] = None) -> str:
        """格式化 Schema 并添加关系信息"""
        lines = []
        all_tables = schema.get('tables', {})

        # 如果指定了表，只显示相关表
        target_tables = tables if tables else list(all_tables.keys())

        for table_name in target_tables:
            if table_name not in all_tables:
                continue

            columns = all_tables[table_name]
            lines.append(f"\n## 表：{table_name}")

            for col in columns:
                col_type = col.get('type', 'unknown')
                col_name = col.get('name', 'unknown')
                nullable = "NULL" if col.get('nullable', True) else "NOT NULL"

                # 检查是否是外键
                fk_info = ""
                if f"{table_name}.{col_name}" in self._relation_manager._foreign_keys:
                    fk_target = self._relation_manager._foreign_keys[f"{table_name}.{col_name}"]
                    fk_info = f" [外键 -> {fk_target}]"

                lines.append(f"  - `{col_name}` ({col_type}) {nullable}{fk_info}")

        # 添加关系说明
        lines.append("\n## 表关联关系")
        lines.append(self._relation_manager.format_relations_for_prompt(target_tables))

        return "\n".join(lines)

    def _build_few_shot_prompt(
        self,
        natural_language: str,
        intent_type: Optional[str],
        tables: Optional[List[str]]
    ) -> str:
        """构建 Few-Shot 示例 Prompt"""
        examples = self._example_library.get_similar_examples(
            natural_language,
            intent_type,
            tables,
            limit=3
        )

        if not examples:
            return ""

        lines = ["\n## 参考示例"]
        for i, ex in enumerate(examples, 1):
            lines.append(f"\n示例 {i}:")
            lines.append(f"  查询：{ex.natural_language}")
            lines.append(f"  SQL: {ex.sql}")

        return "\n".join(lines)

    async def generate_sql(
        self,
        natural_language: str,
        schema: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, float]:
        """生成 SQL（增强版 - 带 Few-Shot 和关系感知）"""
        client = self._get_client()

        # 先识别意图以获取相关表和示例
        try:
            intent = await self.recognize_intent(natural_language, schema)
            tables = intent.tables if intent.tables else None
            intent_type = intent.intent_type
        except Exception as e:
            logger.warning("Intent recognition failed during SQL generation", extra={"error": str(e)})
            tables = None
            intent_type = None

        # 自动发现关系
        self._relation_manager.auto_discover_relations(schema)

        # 格式化 Schema（带关系）
        schema_str = self._format_schema_with_relations(schema, tables)

        # 获取 Few-Shot 示例
        few_shot_str = self._build_few_shot_prompt(natural_language, intent_type, tables)

        # 构建上下文
        context_str = json.dumps(context, ensure_ascii=False) if context else "无"

        prompt = f"""你是一个专业的 SQL 专家。请根据以下数据库 Schema，将用户的自然语言查询转换为准确的 SQL 语句。

## 数据库 Schema
{schema_str}
{few_shot_str}

## 查询上下文
{context_str}

## 用户查询
{natural_language}

## SQL 生成要求
1. **只输出 SQL 语句**，不要包含其他解释或 Markdown 标记
2. **使用标准 SQL 语法**，兼容 PostgreSQL
3. **确保表名和列名与 Schema 完全一致**（区分大小写）
4. **涉及多表查询时**，明确指定 JOIN 类型和关联条件
5. **如果查询模糊**，基于 Schema 和常见用法做出合理假设
6. **对于聚合查询**，确保 GROUP BY 子句包含所有非聚合列
7. **对于时间查询**，使用适当的日期函数

## SQL 语句
"""

        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1  # 降低温度以提高准确性
            )

            sql = response.content[0].text.strip()
            # 清理 SQL 语句
            sql = re.sub(r'^```sql\s*|\s*```$', '', sql).strip()
            sql = re.sub(r'^```\s*|\s*```$', '', sql).strip()

            # 估算置信度
            confidence = self._estimate_confidence(sql, schema, natural_language)

            # 记录示例使用（如果匹配了示例）
            if intent_type:
                for ex in self._example_library.get_similar_examples(natural_language, intent_type, tables, limit=1):
                    self._example_library.record_usage(ex.id, confidence > 0.7)

            logger.info(
                "LLM generated SQL (enhanced)",
                extra={
                    "natural_language": natural_language,
                    "sql": sql,
                    "confidence": confidence,
                    "used_few_shot": bool(few_shot_str),
                    "intent_type": intent_type
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
    ) -> 'QueryIntent':
        """识别查询意图"""
        # 使用原有的实现
        from .nl2sql_ai_service import AnthropicLLMProvider, QueryIntent

        base_provider = AnthropicLLMProvider(api_key=self.api_key, model=self.model)
        return await base_provider.recognize_intent(natural_language, schema)

    def _estimate_confidence(
        self,
        sql: str,
        schema: Dict[str, Any],
        natural_language: str
    ) -> float:
        """估算置信度（增强版）"""
        confidence = 0.5

        # 基本结构检查
        if re.match(r'^SELECT\s+.+\s+FROM\s+\w+', sql, re.IGNORECASE):
            confidence += 0.2

        # 表名验证
        tables = schema.get('tables', {}).keys()
        for table in tables:
            if table.lower() in sql.lower():
                confidence += 0.15
                break

        # 长度合理性
        if 20 < len(sql) < 2000:
            confidence += 0.1

        # 如果包含关系信息，增加置信度
        if 'JOIN' in sql.upper():
            # JOIN 查询更难，但如果结构正确，说明质量高
            if re.search(r'JOIN\s+\w+\s+ON', sql, re.IGNORECASE):
                confidence += 0.1

        return min(confidence, 0.95)


# ============== SQL 自校正器 ==============

class SQLSelfCorrector:
    """SQL 自校正器"""

    def __init__(self, llm_provider: EnhancedAnthropicLLMProvider):
        self.llm_provider = llm_provider

    async def correct_sql(
        self,
        sql: str,
        error_message: str,
        schema: Dict[str, Any]
    ) -> SQLCorrectionResult:
        """尝试自动校正 SQL"""

        schema_str = self.llm_provider._format_schema_with_relations(schema)

        prompt = f"""你是一个 SQL 调试专家。以下 SQL 执行失败，请分析错误原因并提供修正后的 SQL。

## 数据库 Schema
{schema_str}

## 原始 SQL
{sql}

## 错误信息
{error_message}

## 任务
1. 分析错误原因
2. 提供修正后的 SQL
3. 只输出修正后的 SQL，不要其他解释

## 修正后的 SQL
"""

        try:
            client = self.llm_provider._get_client()
            response = await client.messages.create(
                model=self.llm_provider.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )

            corrected_sql = response.content[0].text.strip()
            corrected_sql = re.sub(r'^```sql\s*|\s*```$', '', corrected_sql).strip()
            corrected_sql = re.sub(r'^```\s*|\s*```$', '', corrected_sql).strip()

            # 确定校正原因
            if "syntax error" in error_message.lower():
                reason = "语法错误修正"
            elif "does not exist" in error_message.lower():
                reason = "表/列名修正"
            elif "type" in error_message.lower():
                reason = "类型错误修正"
            else:
                reason = "其他错误修正"

            result = SQLCorrectionResult(
                original_sql=sql,
                corrected_sql=corrected_sql,
                error_message=error_message,
                correction_reason=reason,
                success=corrected_sql != sql
            )

            logger.info(
                "SQL self-correction completed",
                extra={
                    "original_sql": sql[:100],
                    "corrected_sql": corrected_sql[:100],
                    "reason": reason,
                    "success": result.success
                }
            )

            return result

        except Exception as e:
            logger.error("SQL self-correction failed", extra={"error": str(e)})
            return SQLCorrectionResult(
                original_sql=sql,
                corrected_sql=sql,
                error_message=error_message,
                correction_reason="校正失败：" + str(e),
                success=False
            )


# ============== 查询澄清器 ==============

class QueryClarifier:
    """查询澄清器"""

    def __init__(self):
        self._ambiguous_patterns = [
            ("最新", ["按时间排序", "按 ID 排序"]),
            ("热门", ["按销量", "按评分", "按浏览量"]),
            ("表现好", ["按销售额", "按利润率", "按增长率"]),
            ("相关", ["按类别", "按标签", "按关键词"])
        ]

    def detect_ambiguity(
        self,
        natural_language: str,
        schema: Dict[str, Any]
    ) -> Optional[ClarificationQuestion]:
        """检测查询中的歧义"""

        for pattern, options in self._ambiguous_patterns:
            if pattern in natural_language:
                return ClarificationQuestion(
                    question=f"您说的'{pattern}'具体是指什么？",
                    options=options,
                    reason=f"查询中包含模糊词汇'{pattern}'，需要明确排序或筛选标准"
                )

        # 检测缺少必要信息的查询
        if "哪些" in natural_language and "where" not in natural_language.lower():
            # 检查是否有多个可能的表
            tables = list(schema.get('tables', {}).keys())
            if len(tables) > 1:
                return ClarificationQuestion(
                    question="您想查询哪个表的数据？",
                    options=tables,
                    reason="查询未指定具体的数据表"
                )

        return None

    def apply_clarification(
        self,
        natural_language: str,
        clarification: str
    ) -> str:
        """应用澄清结果到查询"""
        # 简单的澄清结果应用
        if "按时间" in clarification:
            return natural_language + "（按创建时间排序）"
        elif "按销量" in clarification:
            return natural_language + "（按销量降序）"
        elif "按销售额" in clarification:
            return natural_language + "（按销售额降序）"

        return natural_language


# ============== 增强的 NL2SQL 服务 ==============

class NL2SQLAIServiceEnhanced:
    """增强的 NL2SQL AI 服务 - v1.3"""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        self.llm_provider = EnhancedAnthropicLLMProvider(api_key=api_key, model=model)
        self.self_corrector = SQLSelfCorrector(self.llm_provider)
        self.clarifier = QueryClarifier()
        self._query_history: List[Dict[str, Any]] = []
        self._max_correction_attempts = 2

    async def convert_to_sql(
        self,
        natural_language: str,
        schema: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        use_llm: bool = True,
        enable_self_correction: bool = True
    ) -> Dict[str, Any]:
        """将自然语言转换为 SQL（增强版）"""

        logger.info(
            "Converting natural language to SQL (enhanced v1.3)",
            extra={
                "natural_language": natural_language,
                "use_llm": use_llm,
                "enable_self_correction": enable_self_correction
            }
        )

        # 1. 检查歧义
        clarification = self.clarifier.detect_ambiguity(natural_language, schema)
        if clarification:
            logger.info("Query ambiguity detected", extra={"question": clarification.question})
            # 在实际应用中，这里会返回澄清问题给用户
            # 这里我们暂时跳过，假设用户选择了第一个选项

        # 2. 意图识别
        try:
            intent = await self.llm_provider.recognize_intent(natural_language, schema)
        except Exception as e:
            logger.warning("Intent recognition failed", extra={"error": str(e)})
            from .nl2sql_ai_service import QueryIntent
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

        # 3. SQL 生成（使用 Few-Shot 和关系增强）
        sql = ""
        confidence = 0.0

        try:
            if use_llm:
                sql, confidence = await self.llm_provider.generate_sql(
                    natural_language, schema, context
                )
            else:
                from nl2sql.converter import nl2sql_converter
                sql = nl2sql_converter.convert(natural_language)
                confidence = 0.5
        except Exception as e:
            logger.error("SQL generation failed", extra={"error": str(e)})
            return self._create_error_result(f"SQL 生成失败：{str(e)}")

        # 4. SQL 验证
        from .nl2sql_ai_service import SQLValidationResult
        validation = self._validate_sql(sql, schema)

        if not validation.is_valid:
            # 尝试自校正
            if enable_self_correction and validation.errors:
                correction_result = await self._self_correct(
                    sql, validation.errors[0], schema
                )
                if correction_result.success:
                    sql = correction_result.corrected_sql
                    # 重新验证
                    validation = self._validate_sql(sql, schema)

        # 5. 获取优化建议
        try:
            suggestions = await self.llm_provider.suggest_optimization(sql, schema)
        except Exception:
            suggestions = []

        # 6. 记录历史
        self._query_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "natural_language": natural_language,
            "sql": sql,
            "intent": intent.to_dict() if hasattr(intent, 'to_dict') else {},
            "confidence": confidence,
            "validation": validation.to_dict() if hasattr(validation, 'to_dict') else {},
            "clarification": clarification.to_dict() if clarification else None
        })

        return {
            "sql": sql,
            "intent": intent.to_dict() if hasattr(intent, 'to_dict') else {},
            "confidence": confidence,
            "validation": validation.to_dict() if hasattr(validation, 'to_dict') else {},
            "suggestions": suggestions,
            "clarification": clarification.to_dict() if clarification else None
        }

    async def _self_correct(
        self,
        sql: str,
        error_message: str,
        schema: Dict[str, Any]
    ) -> SQLCorrectionResult:
        """执行 SQL 自校正"""
        return await self.self_corrector.correct_sql(sql, error_message, schema)

    async def execute_with_self_correction(
        self,
        sql: str,
        executor: callable,
        schema: Dict[str, Any]
    ) -> Tuple[Any, Optional[SQLCorrectionResult]]:
        """执行 SQL 并在失败时尝试自校正"""

        try:
            result = await executor(sql)
            return result, None
        except Exception as e:
            error_message = str(e)
            logger.warning("SQL execution failed, attempting self-correction",
                          extra={"sql": sql, "error": error_message})

            correction_result = await self.self_corrector.correct_sql(
                sql, error_message, schema
            )

            if correction_result.success:
                logger.info("Self-correction succeeded, retrying execution")
                try:
                    result = await executor(correction_result.corrected_sql)
                    return result, correction_result
                except Exception as retry_error:
                    logger.error("Retry after self-correction also failed",
                                extra={"error": str(retry_error)})

            return None, correction_result

    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            "sql": "",
            "intent": {},
            "confidence": 0.0,
            "validation": {
                "is_valid": False,
                "errors": [error_message],
                "warnings": [],
                "suggestions": []
            },
            "suggestions": [],
            "clarification": None
        }

    def _validate_sql(self, sql: str, schema: Dict[str, Any]) -> 'SQLValidationResult':
        """验证 SQL"""
        from .nl2sql_ai_service import SQLValidationResult

        errors = []
        warnings = []
        suggestions = []

        sql_upper = sql.upper().strip()

        # 只支持 SELECT
        if not sql_upper.startswith('SELECT'):
            errors.append("只支持 SELECT 查询语句")

        # 表名验证
        tables_in_schema = set(t.lower() for t in schema.get('tables', {}).keys())
        import re
        from_matches = re.findall(r'FROM\s+(\w+)', sql, re.IGNORECASE)
        join_matches = re.findall(r'JOIN\s+(\w+)', sql, re.IGNORECASE)

        for table in from_matches + join_matches:
            if table.lower() not in tables_in_schema:
                errors.append(f"表 '{table}' 不在 Schema 中")

        # 安全检查
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE']
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                errors.append(f"包含危险关键字：{keyword}")

        # 性能警告
        if 'SELECT *' in sql_upper:
            warnings.append("使用 SELECT * 可能影响性能，建议指定具体列")

        if 'WHERE' not in sql_upper and 'LIMIT' not in sql_upper:
            warnings.append("查询没有 WHERE 条件或 LIMIT 限制，可能返回大量数据")

        return SQLValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )

    def get_example_library(self) -> ExampleLibrary:
        """获取示例库"""
        return self.llm_provider._example_library

    def get_relation_manager(self) -> SchemaRelationManager:
        """获取关系管理器"""
        return self.llm_provider._relation_manager

    def add_query_example(self, natural_language: str, sql: str, intent_type: str, tables: List[str]) -> str:
        """添加查询示例"""
        import uuid
        example_id = f"ex_{uuid.uuid4().hex[:8]}"
        example = QueryExample(
            id=example_id,
            natural_language=natural_language,
            sql=sql,
            intent_type=intent_type,
            tables=tables,
            difficulty="medium",
            success_rate=1.0
        )
        self.llm_provider._example_library.add_example(example)
        return example_id

    def get_query_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取查询历史"""
        return self._query_history[-limit:]

    def clear_history(self):
        """清空查询历史"""
        self._query_history.clear()


# ============== 全局服务实例 ==============

nl2sql_ai_service_enhanced = NL2SQLAIServiceEnhanced()
