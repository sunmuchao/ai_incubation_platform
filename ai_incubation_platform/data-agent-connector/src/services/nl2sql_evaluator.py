"""
NL2SQL 准确率评估框架

功能:
1. 测试集管理
2. 准确率评估
3. 错误分析
4. 性能基准测试
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
import asyncio

from utils.logger import logger


@dataclass
class TestQuery:
    """测试查询"""
    id: str
    natural_language: str
    expected_sql: str
    intent_type: str
    tables: List[str]
    difficulty: str  # easy, medium, hard
    category: str  # simple_select, conditional, aggregation, join, etc.
    description: Optional[str] = None


@dataclass
class TestResult:
    """测试结果"""
    test_id: str
    natural_language: str
    expected_sql: str
    actual_sql: str
    is_correct: bool
    confidence: float
    latency_ms: float
    error_message: Optional[str] = None
    mismatch_reason: Optional[str] = None  # 错误原因


@dataclass
class EvaluationReport:
    """评估报告"""
    total_tests: int
    correct_count: int
    accuracy: float
    avg_confidence: float
    avg_latency_ms: float
    accuracy_by_difficulty: Dict[str, float]
    accuracy_by_category: Dict[str, float]
    error_breakdown: Dict[str, int]
    failed_tests: List[TestResult]
    timestamp: str


class NL2SQLTestSuite:
    """NL2SQL 测试套件"""

    def __init__(self):
        self._test_queries: List[TestQuery] = []
        self._load_builtin_tests()

    def _load_builtin_tests(self):
        """加载内置测试用例"""
        self._test_queries = [
            # ========== 简单查询 (Easy) ==========
            TestQuery(
                id="t001",
                natural_language="查询所有用户",
                expected_sql="SELECT * FROM users",
                intent_type="simple_select",
                tables=["users"],
                difficulty="easy",
                category="simple_select",
                description="基础全表查询"
            ),
            TestQuery(
                id="t002",
                natural_language="查询年龄大于 18 的用户",
                expected_sql="SELECT * FROM users WHERE age > 18",
                intent_type="conditional_query",
                tables=["users"],
                difficulty="easy",
                category="conditional",
                description="简单条件查询"
            ),
            TestQuery(
                id="t003",
                natural_language="查询名字包含'张'的用户",
                expected_sql="SELECT * FROM users WHERE name LIKE '%张%'",
                intent_type="conditional_query",
                tables=["users"],
                difficulty="easy",
                category="conditional",
                description="模糊查询"
            ),
            TestQuery(
                id="t004",
                natural_language="查询北京的用户",
                expected_sql="SELECT * FROM users WHERE city = '北京'",
                intent_type="conditional_query",
                tables=["users"],
                difficulty="easy",
                category="conditional",
                description="等值条件查询"
            ),
            # ========== 聚合查询 (Medium) ==========
            TestQuery(
                id="t005",
                natural_language="统计用户总数",
                expected_sql="SELECT COUNT(*) as total FROM users",
                intent_type="aggregation",
                tables=["users"],
                difficulty="medium",
                category="aggregation",
                description="计数聚合"
            ),
            TestQuery(
                id="t006",
                natural_language="按部门分组统计用户数量",
                expected_sql="SELECT department, COUNT(*) as count FROM users GROUP BY department",
                intent_type="group_by",
                tables=["users"],
                difficulty="medium",
                category="aggregation",
                description="分组聚合"
            ),
            TestQuery(
                id="t007",
                natural_language="查询用户的平均年龄",
                expected_sql="SELECT AVG(age) as avg_age FROM users",
                intent_type="aggregation",
                tables=["users"],
                difficulty="medium",
                category="aggregation",
                description="平均值聚合"
            ),
            TestQuery(
                id="t008",
                natural_language="查询工资最高的员工",
                expected_sql="SELECT * FROM employees ORDER BY salary DESC LIMIT 1",
                intent_type="top_n",
                tables=["employees"],
                difficulty="medium",
                category="order_limit",
                description="排序取顶"
            ),
            TestQuery(
                id="t009",
                natural_language="查询工资最高的前 10 名员工",
                expected_sql="SELECT * FROM employees ORDER BY salary DESC LIMIT 10",
                intent_type="top_n",
                tables=["employees"],
                difficulty="medium",
                category="order_limit",
                description="Top N 查询"
            ),
            # ========== 复杂查询 (Hard) ==========
            TestQuery(
                id="t010",
                natural_language="查询每个用户的订单数量",
                expected_sql="SELECT u.id, u.name, COUNT(o.id) as order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.id, u.name",
                intent_type="join",
                tables=["users", "orders"],
                difficulty="hard",
                category="join",
                description="LEFT JOIN 聚合"
            ),
            TestQuery(
                id="t011",
                natural_language="查询有订单的用户",
                expected_sql="SELECT DISTINCT u.* FROM users u INNER JOIN orders o ON u.id = o.user_id",
                intent_type="join",
                tables=["users", "orders"],
                difficulty="hard",
                category="join",
                description="INNER JOIN 去重"
            ),
            TestQuery(
                id="t012",
                natural_language="查询销售额前 10 的产品",
                expected_sql="SELECT p.name, SUM(oi.quantity * oi.price) as total_sales FROM products p JOIN order_items oi ON p.id = oi.product_id GROUP BY p.id, p.name ORDER BY total_sales DESC LIMIT 10",
                intent_type="complex",
                tables=["products", "order_items"],
                difficulty="hard",
                category="join_aggregation",
                description="JOIN+ 聚合 + 排序"
            ),
            TestQuery(
                id="t013",
                natural_language="查询上个月的订单",
                expected_sql="SELECT * FROM orders WHERE created_at >= date_trunc('month', CURRENT_DATE - INTERVAL '1 month') AND created_at < date_trunc('month', CURRENT_DATE)",
                intent_type="time_range",
                tables=["orders"],
                difficulty="hard",
                category="time_range",
                description="相对时间范围"
            ),
            TestQuery(
                id="t014",
                natural_language="查询 2024 年的订单",
                expected_sql="SELECT * FROM orders WHERE EXTRACT(YEAR FROM created_at) = 2024",
                intent_type="time_range",
                tables=["orders"],
                difficulty="hard",
                category="time_range",
                description="年份筛选"
            ),
            TestQuery(
                id="t015",
                natural_language="查询购买过产品 A 的用户",
                expected_sql="SELECT DISTINCT u.* FROM users u JOIN orders o ON u.id = o.user_id JOIN order_items oi ON o.id = oi.order_id JOIN products p ON oi.product_id = p.id WHERE p.name = '产品 A'",
                intent_type="complex",
                tables=["users", "orders", "order_items", "products"],
                difficulty="hard",
                category="multi_join",
                description="多表 JOIN 子查询"
            ),
            # ========== 边界情况 ==========
            TestQuery(
                id="t016",
                natural_language="查询没有订单的用户",
                expected_sql="SELECT u.* FROM users u LEFT JOIN orders o ON u.id = o.user_id WHERE o.id IS NULL",
                intent_type="join",
                tables=["users", "orders"],
                difficulty="hard",
                category="anti_join",
                description="反连接查询"
            ),
            TestQuery(
                id="t017",
                natural_language="查询订单数量大于 5 的用户",
                expected_sql="SELECT u.id, u.name, COUNT(o.id) as order_count FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.id, u.name HAVING COUNT(o.id) > 5",
                intent_type="having",
                tables=["users", "orders"],
                difficulty="hard",
                category="having",
                description="HAVING 子句"
            ),
            TestQuery(
                id="t018",
                natural_language="查询年龄最小的用户",
                expected_sql="SELECT * FROM users ORDER BY age ASC LIMIT 1",
                intent_type="top_n",
                tables=["users"],
                difficulty="medium",
                category="order_limit",
                description="最小值查询"
            ),
            TestQuery(
                id="t019",
                natural_language="统计各部门工资总和",
                expected_sql="SELECT department, SUM(salary) as total_salary FROM employees GROUP BY department",
                intent_type="aggregation",
                tables=["employees"],
                difficulty="medium",
                category="aggregation",
                description="分组求和"
            ),
            TestQuery(
                id="t020",
                natural_language="查询既在技术部工资又高于 10000 的员工",
                expected_sql="SELECT * FROM employees WHERE department = '技术部' AND salary > 10000",
                intent_type="conditional_query",
                tables=["employees"],
                difficulty="medium",
                category="conditional",
                description="AND 条件组合"
            )
        ]

    def add_test(self, test_query: TestQuery) -> None:
        """添加测试用例"""
        self._test_queries.append(test_query)

    def get_tests_by_difficulty(self, difficulty: str) -> List[TestQuery]:
        """按难度获取测试用例"""
        return [t for t in self._test_queries if t.difficulty == difficulty]

    def get_tests_by_category(self, category: str) -> List[TestQuery]:
        """按类别获取测试用例"""
        return [t for t in self._test_queries if t.category == category]

    @property
    def all_tests(self) -> List[TestQuery]:
        """获取所有测试用例"""
        return self._test_queries.copy()

    @property
    def test_count(self) -> int:
        """测试用例数量"""
        return len(self._test_queries)


class NL2SQLEvaluator:
    """NL2SQL 评估器"""

    def __init__(self, nl2sql_service):
        self.nl2sql_service = nl2sql_service
        self.test_suite = NL2SQLTestSuite()
        self._test_results: List[TestResult] = []

    def _normalize_sql(self, sql: str) -> str:
        """标准化 SQL 用于比较"""
        # 移除多余空格
        sql = ' '.join(sql.split())
        # 统一大小写（关键字大写）
        sql = sql.upper()
        # 移除分号
        sql = sql.rstrip(';')
        return sql.strip()

    def _sql_equivalent(self, sql1: str, sql2: str) -> bool:
        """判断两个 SQL 是否等价（简化版）"""
        return self._normalize_sql(sql1) == self._normalize_sql(sql2)

    def _analyze_mismatch(self, expected: str, actual: str) -> str:
        """分析 SQL 不匹配的原因"""
        expected_norm = self._normalize_sql(expected)
        actual_norm = self._normalize_sql(actual)

        # 检查是否是结构差异
        if expected_norm == actual_norm:
            return "格式差异（语义等价）"

        # 检查表名差异
        import re
        expected_tables = set(re.findall(r'FROM\s+(\w+)', expected_norm, re.IGNORECASE))
        actual_tables = set(re.findall(r'FROM\s+(\w+)', actual_norm, re.IGNORECASE))
        if expected_tables != actual_tables:
            return f"表名差异：期望{expected_tables}, 实际{actual_tables}"

        # 检查列差异
        expected_cols = set(re.findall(r'SELECT\s+(.+?)\s+FROM', expected_norm, re.IGNORECASE | re.DOTALL))
        actual_cols = set(re.findall(r'SELECT\s+(.+?)\s+FROM', actual_norm, re.IGNORECASE | re.DOTALL))
        if expected_cols != actual_cols:
            return f"列差异：期望{expected_cols}, 实际{actual_cols}"

        # 检查条件差异
        expected_where = re.findall(r'WHERE\s+(.+?)(?:GROUP|ORDER|LIMIT|$)', expected_norm, re.IGNORECASE | re.DOTALL)
        actual_where = re.findall(r'WHERE\s+(.+?)(?:GROUP|ORDER|LIMIT|$)', actual_norm, re.IGNORECASE | re.DOTALL)
        if expected_where != actual_where:
            return f"WHERE 条件差异"

        return "SQL 结构差异"

    async def run_evaluation(
        self,
        schema: Dict[str, Any],
        use_llm: bool = True,
        enable_self_correction: bool = True
    ) -> EvaluationReport:
        """运行完整评估"""

        logger.info(f"Starting NL2SQL evaluation with {self.test_suite.test_count} tests")

        results: List[TestResult] = []
        correct_count = 0
        total_confidence = 0.0
        total_latency = 0.0

        # 按难度和类别统计
        difficulty_stats: Dict[str, Dict[str, int]] = {
            "easy": {"total": 0, "correct": 0},
            "medium": {"total": 0, "correct": 0},
            "hard": {"total": 0, "correct": 0}
        }
        category_stats: Dict[str, Dict[str, int]] = {}
        error_breakdown: Dict[str, int] = {}

        for test in self.test_suite.all_tests:
            start_time = datetime.utcnow()

            try:
                # 执行 NL2SQL 转换
                result = await self.nl2sql_service.convert_to_sql(
                    natural_language=test.natural_language,
                    schema=schema,
                    use_llm=use_llm,
                    enable_self_correction=enable_self_correction
                )

                actual_sql = result.get("sql", "")
                confidence = result.get("confidence", 0.0)
                validation = result.get("validation", {})

                latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

                # 判断是否正确
                is_correct = self._sql_equivalent(test.expected_sql, actual_sql)

                # 如果不正确，分析原因
                mismatch_reason = None
                if not is_correct:
                    mismatch_reason = self._analyze_mismatch(test.expected_sql, actual_sql)

                    # 统计错误类型
                    if "表名差异" in mismatch_reason:
                        error_breakdown["table_error"] = error_breakdown.get("table_error", 0) + 1
                    elif "列差异" in mismatch_reason:
                        error_breakdown["column_error"] = error_breakdown.get("column_error", 0) + 1
                    elif "WHERE" in mismatch_reason:
                        error_breakdown["where_error"] = error_breakdown.get("where_error", 0) + 1
                    elif "JOIN" in actual_sql.upper() and "JOIN" not in test.expected_sql.upper():
                        error_breakdown["join_error"] = error_breakdown.get("join_error", 0) + 1
                    else:
                        error_breakdown["other_error"] = error_breakdown.get("other_error", 0) + 1

                if is_correct:
                    correct_count += 1

                # 更新统计
                difficulty_stats[test.difficulty]["total"] += 1
                if is_correct:
                    difficulty_stats[test.difficulty]["correct"] += 1

                if test.category not in category_stats:
                    category_stats[test.category] = {"total": 0, "correct": 0}
                category_stats[test.category]["total"] += 1
                if is_correct:
                    category_stats[test.category]["correct"] += 1

                total_confidence += confidence
                total_latency += latency_ms

                results.append(TestResult(
                    test_id=test.id,
                    natural_language=test.natural_language,
                    expected_sql=test.expected_sql,
                    actual_sql=actual_sql,
                    is_correct=is_correct,
                    confidence=confidence,
                    latency_ms=latency_ms,
                    mismatch_reason=mismatch_reason
                ))

            except Exception as e:
                logger.error(f"Test {test.id} failed with exception", extra={"error": str(e)})
                results.append(TestResult(
                    test_id=test.id,
                    natural_language=test.natural_language,
                    expected_sql=test.expected_sql,
                    actual_sql="",
                    is_correct=False,
                    confidence=0.0,
                    latency_ms=0,
                    error_message=str(e),
                    mismatch_reason="执行异常"
                ))
                error_breakdown["execution_error"] = error_breakdown.get("execution_error", 0) + 1

        self._test_results = results

        # 计算统计
        accuracy = correct_count / self.test_suite.test_count if self.test_suite.test_count > 0 else 0
        avg_confidence = total_confidence / self.test_suite.test_count if self.test_suite.test_count > 0 else 0
        avg_latency = total_latency / self.test_suite.test_count if self.test_suite.test_count > 0 else 0

        # 按难度计算准确率
        accuracy_by_difficulty = {}
        for diff, stats in difficulty_stats.items():
            if stats["total"] > 0:
                accuracy_by_difficulty[diff] = stats["correct"] / stats["total"]
            else:
                accuracy_by_difficulty[diff] = 0.0

        # 按类别计算准确率
        accuracy_by_category = {}
        for cat, stats in category_stats.items():
            if stats["total"] > 0:
                accuracy_by_category[cat] = stats["correct"] / stats["total"]
            else:
                accuracy_by_category[cat] = 0.0

        # 获取失败的测试
        failed_tests = [r for r in results if not r.is_correct]

        report = EvaluationReport(
            total_tests=self.test_suite.test_count,
            correct_count=correct_count,
            accuracy=accuracy,
            avg_confidence=avg_confidence,
            avg_latency_ms=avg_latency,
            accuracy_by_difficulty=accuracy_by_difficulty,
            accuracy_by_category=accuracy_by_category,
            error_breakdown=error_breakdown,
            failed_tests=failed_tests,
            timestamp=datetime.utcnow().isoformat()
        )

        logger.info(
            "NL2SQL evaluation completed",
            extra={
                "total_tests": report.total_tests,
                "accuracy": report.accuracy,
                "avg_confidence": report.avg_confidence,
                "avg_latency_ms": report.avg_latency_ms
            }
        )

        return report

    def format_report(self, report: EvaluationReport) -> str:
        """格式化评估报告"""
        lines = [
            "=" * 60,
            "NL2SQL 准确率评估报告",
            "=" * 60,
            f"评估时间：{report.timestamp}",
            f"测试总数：{report.total_tests}",
            f"正确数量：{report.correct_count}",
            f"准确率：{report.accuracy:.2%}",
            f"平均置信度：{report.avg_confidence:.2f}",
            f"平均延迟：{report.avg_latency_ms:.1f}ms",
            "",
            "按难度分类:",
            f"  - Easy:   {report.accuracy_by_difficulty.get('easy', 0):.2%}",
            f"  - Medium: {report.accuracy_by_difficulty.get('medium', 0):.2%}",
            f"  - Hard:   {report.accuracy_by_difficulty.get('hard', 0):.2%}",
            "",
            "按类别分类:",
        ]

        for cat, acc in report.accuracy_by_category.items():
            lines.append(f"  - {cat}: {acc:.2%}")

        lines.extend([
            "",
            "错误类型分布:",
        ])
        for error_type, count in report.error_breakdown.items():
            lines.append(f"  - {error_type}: {count}")

        if report.failed_tests:
            lines.extend([
                "",
                "失败测试详情:",
                "-" * 40,
            ])
            for test in report.failed_tests[:10]:  # 只显示前 10 个
                lines.extend([
                    f"[{test.test_id}] {test.natural_language}",
                    f"  期望：{test.expected_sql[:100]}...",
                    f"  实际：{test.actual_sql[:100]}...",
                    f"  原因：{test.mismatch_reason}",
                    ""
                ])

        lines.append("=" * 60)
        return "\n".join(lines)

    def save_report(self, report: EvaluationReport, output_path: str) -> None:
        """保存报告为 JSON"""
        report_data = {
            "total_tests": report.total_tests,
            "correct_count": report.correct_count,
            "accuracy": report.accuracy,
            "avg_confidence": report.avg_confidence,
            "avg_latency_ms": report.avg_latency_ms,
            "accuracy_by_difficulty": report.accuracy_by_difficulty,
            "accuracy_by_category": report.accuracy_by_category,
            "error_breakdown": report.error_breakdown,
            "timestamp": report.timestamp,
            "failed_tests": [
                {
                    "test_id": t.test_id,
                    "natural_language": t.natural_language,
                    "expected_sql": t.expected_sql,
                    "actual_sql": t.actual_sql,
                    "mismatch_reason": t.mismatch_reason
                }
                for t in report.failed_tests
            ]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Evaluation report saved to {output_path}")


# 全局评估器实例（延迟初始化）
evaluator = None

def get_evaluator(nl2sql_service) -> NL2SQLEvaluator:
    """获取评估器实例"""
    global evaluator
    if evaluator is None:
        evaluator = NL2SQLEvaluator(nl2sql_service)
    return evaluator
