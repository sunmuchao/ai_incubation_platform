"""
数据转换服务

实现:
1. SQL 转换任务 - 支持 SQL 查询结果的转换和加工
2. Python UDF 支持 - 用户自定义函数处理
3. 数据质量校验 - 数据验证规则引擎
4. 转换任务编排与调度
5. 转换模板库 - 预置常用转换
"""
import asyncio
import hashlib
import importlib.util
import inspect
import json
import re
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, Float, Index
from config.database import db_manager
from utils.logger import logger
from config.settings import settings


class TransformType(Enum):
    """转换类型"""
    SQL = "sql"
    PYTHON = "python"
    AGGREGATION = "aggregation"
    FILTER = "filter"
    JOIN = "join"
    PIVOT = "pivot"
    UNPIVOT = "unpivot"
    ENRICHMENT = "enrichment"


class QualityCheckType(Enum):
    """数据质量检查类型"""
    NOT_NULL = "not_null"
    UNIQUE = "unique"
    RANGE = "range"
    PATTERN = "pattern"
    REFERENTIAL = "referential"
    CUSTOM = "custom"


class JobStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TransformConfig:
    """转换配置"""
    name: str
    transform_type: TransformType
    source_tables: List[str]
    target_table: str
    config: Dict[str, Any] = field(default_factory=dict)
    schedule: Optional[str] = None  # cron 表达式
    enabled: bool = True


@dataclass
class QualityRule:
    """数据质量规则"""
    name: str
    check_type: QualityCheckType
    table_name: str
    column_name: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    severity: str = "error"  # warning, error, critical
    description: str = ""


@dataclass
class QualityResult:
    """数据质量检查结果"""
    rule_name: str
    table_name: str
    column_name: Optional[str]
    passed: bool
    checked_rows: int
    failed_rows: int
    error_rate: float
    error_message: Optional[str] = None
    checked_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class JobExecution:
    """任务执行记录"""
    job_name: str
    status: JobStatus
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    input_rows: int = 0
    output_rows: int = 0
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


class PythonUDF:
    """Python 用户自定义函数"""

    def __init__(self, name: str, code: str):
        self.name = name
        self.code = code
        self._func: Optional[Callable] = None
        self._load_error: Optional[str] = None

    def compile(self) -> bool:
        """编译 UDF 代码"""
        try:
            # 简化实现：使用 exec 执行代码
            namespace = {}
            exec(self.code, namespace)

            # 查找 transform 函数
            if 'transform' in namespace:
                self._func = namespace['transform']
            elif 'apply' in namespace:
                self._func = namespace['apply']
            else:
                # 查找第一个可调用的函数
                for name, obj in namespace.items():
                    if callable(obj) and not name.startswith('_'):
                        self._func = obj
                        break

            if self._func is None:
                self._load_error = "No transform/apply function found in UDF code"
                return False

            return True

        except Exception as e:
            self._load_error = str(e)
            logger.error(f"Failed to compile UDF {self.name}: {e}")
            return False

    def execute(self, data: Any) -> Any:
        """执行 UDF"""
        if self._func is None:
            raise ValueError(f"UDF {self.name} not compiled or has error: {self._load_error}")

        try:
            return self._func(data)
        except Exception as e:
            raise ValueError(f"UDF execution error: {e}")


class SQLTransformer:
    """SQL 转换器"""

    def __init__(self, config: TransformConfig):
        self.config = config
        self._sql_template = config.config.get("sql", "")

    async def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """执行 SQL 转换"""
        # 将数据转换为临时表，然后执行 SQL
        # 这里使用 SQLite 作为临时计算引擎
        import sqlite3
        import pandas as pd

        conn = sqlite3.connect(":memory:")

        try:
            # 创建临时表
            for i, table_name in enumerate(self.config.source_tables):
                df = pd.DataFrame(data)
                df.to_sql(table_name, conn, if_exists="replace", index=False)

            # 执行 SQL
            result = pd.read_sql_query(self._sql_template, conn)
            return result.to_dict("records")

        finally:
            conn.close()


class PythonTransformer:
    """Python 转换器"""

    def __init__(self, config: TransformConfig):
        self.config = config
        self._udf: Optional[PythonUDF] = None

        # 加载 UDF
        udf_code = config.config.get("python_code", "")
        if udf_code:
            self._udf = PythonUDF(config.name, udf_code)
            self._udf.compile()

    async def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """执行 Python 转换"""
        if self._udf is None:
            raise ValueError("No UDF configured for Python transformer")

        result = self._udf.execute(data)
        return result if isinstance(result, list) else [result]


class AggregationTransformer:
    """聚合转换器"""

    def __init__(self, config: TransformConfig):
        self.config = config

    async def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """执行聚合转换"""
        import pandas as pd

        df = pd.DataFrame(data)
        agg_config = self.config.config.get("aggregation", {})

        group_by = agg_config.get("group_by", [])
        aggregations = agg_config.get("aggregations", {})

        if group_by:
            grouped = df.groupby(group_by)
            result_df = grouped.agg(aggregations)
            result_df = result_df.reset_index()
        else:
            result_df = df.agg(aggregations).to_frame().T

        return result_df.to_dict("records")


class FilterTransformer:
    """过滤器"""

    def __init__(self, config: TransformConfig):
        self.config = config
        self._conditions = config.config.get("conditions", [])

    async def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """执行过滤"""
        result = []
        for row in data:
            if self._match_conditions(row):
                result.append(row)
        return result

    def _match_conditions(self, row: Dict[str, Any]) -> bool:
        """检查是否匹配条件"""
        for condition in self._conditions:
            column = condition.get("column")
            operator = condition.get("operator")
            value = condition.get("value")

            row_value = row.get(column)

            if not self._evaluate_operator(row_value, operator, value):
                return False

        return True

    def _evaluate_operator(self, actual: Any, operator: str, expected: Any) -> bool:
        """评估操作符"""
        ops = {
            "=": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            ">": lambda a, b: a > b,
            ">=": lambda a, b: a >= b,
            "<": lambda a, b: a < b,
            "<=": lambda a, b: a <= b,
            "in": lambda a, b: a in b if isinstance(b, (list, tuple)) else False,
            "not_in": lambda a, b: a not in b if isinstance(b, (list, tuple)) else True,
            "like": lambda a, b: self._like_match(str(a), str(b)),
            "is_null": lambda a, b: a is None,
            "is_not_null": lambda a, b: a is not None,
        }

        op_func = ops.get(operator)
        if op_func:
            return op_func(actual, expected)
        return False

    def _like_match(self, value: str, pattern: str) -> bool:
        """LIKE 模式匹配"""
        # 转换 SQL LIKE 模式到正则表达式
        regex_pattern = pattern.replace("%", ".*").replace("_", ".")
        return bool(re.match(f"^{regex_pattern}$", value, re.IGNORECASE))


class DataQualityChecker:
    """数据质量检查器"""

    def __init__(self):
        self._rules: Dict[str, QualityRule] = {}
        self._custom_checks: Dict[str, Callable] = {}

    def register_rule(self, rule: QualityRule) -> None:
        """注册质量规则"""
        self._rules[rule.name] = rule

    def unregister_rule(self, rule_name: str) -> None:
        """注销质量规则"""
        if rule_name in self._rules:
            del self._rules[rule_name]

    def register_custom_check(self, name: str, check_func: Callable) -> None:
        """注册自定义检查"""
        self._custom_checks[name] = check_func

    async def check(self, data: List[Dict[str, Any]], rules: Optional[List[str]] = None) -> List[QualityResult]:
        """执行数据质量检查"""
        results = []
        rules_to_check = rules or list(self._rules.keys())

        for rule_name in rules_to_check:
            rule = self._rules.get(rule_name)
            if not rule:
                continue

            try:
                result = await self._execute_rule(rule, data)
                results.append(result)
            except Exception as e:
                results.append(QualityResult(
                    rule_name=rule_name,
                    table_name=rule.table_name,
                    column_name=rule.column_name,
                    passed=False,
                    checked_rows=len(data),
                    failed_rows=len(data),
                    error_rate=1.0,
                    error_message=str(e)
                ))

        return results

    async def _execute_rule(self, rule: QualityRule, data: List[Dict[str, Any]]) -> QualityResult:
        """执行单个规则"""
        if rule.check_type == QualityCheckType.NOT_NULL:
            return self._check_not_null(rule, data)
        elif rule.check_type == QualityCheckType.UNIQUE:
            return self._check_unique(rule, data)
        elif rule.check_type == QualityCheckType.RANGE:
            return self._check_range(rule, data)
        elif rule.check_type == QualityCheckType.PATTERN:
            return self._check_pattern(rule, data)
        elif rule.check_type == QualityCheckType.CUSTOM:
            return await self._check_custom(rule, data)
        else:
            raise ValueError(f"Unknown check type: {rule.check_type}")

    def _check_not_null(self, rule: QualityRule, data: List[Dict[str, Any]]) -> QualityResult:
        """检查非空"""
        column = rule.column_name
        failed_rows = sum(1 for row in data if row.get(column) is None)
        return QualityResult(
            rule_name=rule.name,
            table_name=rule.table_name,
            column_name=column,
            passed=failed_rows == 0,
            checked_rows=len(data),
            failed_rows=failed_rows,
            error_rate=failed_rows / len(data) if data else 0
        )

    def _check_unique(self, rule: QualityRule, data: List[Dict[str, Any]]) -> QualityResult:
        """检查唯一性"""
        column = rule.column_name
        values = [row.get(column) for row in data if row.get(column) is not None]
        unique_values = set(values)
        failed_rows = len(values) - len(unique_values)
        return QualityResult(
            rule_name=rule.name,
            table_name=rule.table_name,
            column_name=column,
            passed=failed_rows == 0,
            checked_rows=len(values),
            failed_rows=failed_rows,
            error_rate=failed_rows / len(values) if values else 0
        )

    def _check_range(self, rule: QualityRule, data: List[Dict[str, Any]]) -> QualityResult:
        """检查范围"""
        column = rule.column_name
        min_val = rule.params.get("min")
        max_val = rule.params.get("max")
        failed_rows = 0

        for row in data:
            value = row.get(column)
            if value is not None:
                if min_val is not None and value < min_val:
                    failed_rows += 1
                elif max_val is not None and value > max_val:
                    failed_rows += 1

        return QualityResult(
            rule_name=rule.name,
            table_name=rule.table_name,
            column_name=column,
            passed=failed_rows == 0,
            checked_rows=len(data),
            failed_rows=failed_rows,
            error_rate=failed_rows / len(data) if data else 0
        )

    def _check_pattern(self, rule: QualityRule, data: List[Dict[str, Any]]) -> QualityResult:
        """检查模式匹配"""
        column = rule.column_name
        pattern = rule.params.get("pattern", ".*")
        failed_rows = 0

        try:
            regex = re.compile(pattern)
            for row in data:
                value = row.get(column)
                if value is not None and not regex.match(str(value)):
                    failed_rows += 1
        except re.error as e:
            return QualityResult(
                rule_name=rule.name,
                table_name=rule.table_name,
                column_name=column,
                passed=False,
                checked_rows=len(data),
                failed_rows=len(data),
                error_rate=1.0,
                error_message=f"Invalid regex pattern: {e}"
            )

        return QualityResult(
            rule_name=rule.name,
            table_name=rule.table_name,
            column_name=column,
            passed=failed_rows == 0,
            checked_rows=len(data),
            failed_rows=failed_rows,
            error_rate=failed_rows / len(data) if data else 0
        )

    async def _check_custom(self, rule: QualityRule, data: List[Dict[str, Any]]) -> QualityResult:
        """执行自定义检查"""
        check_func = self._custom_checks.get(rule.name)
        if not check_func:
            raise ValueError(f"Custom check '{rule.name}' not found")

        try:
            result = await check_func(data) if asyncio.iscoroutinefunction(check_func) else check_func(data)

            if isinstance(result, bool):
                return QualityResult(
                    rule_name=rule.name,
                    table_name=rule.table_name,
                    column_name=rule.column_name,
                    passed=result,
                    checked_rows=len(data),
                    failed_rows=0 if result else len(data),
                    error_rate=0 if result else 1.0
                )
            elif isinstance(result, dict):
                return QualityResult(
                    rule_name=rule.name,
                    table_name=rule.table_name,
                    column_name=rule.column_name,
                    passed=result.get("passed", False),
                    checked_rows=result.get("checked_rows", len(data)),
                    failed_rows=result.get("failed_rows", 0),
                    error_rate=result.get("error_rate", 0)
                )
            else:
                raise ValueError("Custom check should return bool or dict")

        except Exception as e:
            return QualityResult(
                rule_name=rule.name,
                table_name=rule.table_name,
                column_name=rule.column_name,
                passed=False,
                checked_rows=len(data),
                failed_rows=len(data),
                error_rate=1.0,
                error_message=str(e)
            )


class TransformJob:
    """转换任务"""

    def __init__(
        self,
        config: TransformConfig,
        quality_checker: Optional[DataQualityChecker] = None
    ):
        self.config = config
        self.quality_checker = quality_checker or DataQualityChecker()
        self._transformer = self._create_transformer(config)
        self._execution_history: List[JobExecution] = []

    def _create_transformer(self, config: TransformConfig):
        """创建转换器"""
        transformers = {
            TransformType.SQL: SQLTransformer,
            TransformType.PYTHON: PythonTransformer,
            TransformType.AGGREGATION: AggregationTransformer,
            TransformType.FILTER: FilterTransformer,
        }

        transformer_class = transformers.get(config.transform_type)
        if not transformer_class:
            raise ValueError(f"Unsupported transform type: {config.transform_type}")

        return transformer_class(config)

    async def execute(self, data: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], JobExecution]:
        """执行转换任务"""
        execution = JobExecution(
            job_name=self.config.name,
            status=JobStatus.RUNNING,
            started_at=datetime.utcnow(),
            input_rows=len(data)
        )

        try:
            # 执行转换
            result = await self._transformer.transform(data)

            # 质量检查
            quality_results = await self.quality_checker.check(result)
            failed_checks = [r for r in quality_results if not r.passed]

            if failed_checks:
                errors = [f"{r.rule_name}: {r.error_message}" for r in failed_checks if r.error_message]
                execution.status = JobStatus.FAILED
                execution.error_message = f"Quality checks failed: {', '.join(errors)}"
            else:
                execution.status = JobStatus.SUCCESS

            execution.output_rows = len(result)
            execution.metrics["quality_results"] = [r.__dict__ for r in quality_results]

        except Exception as e:
            execution.status = JobStatus.FAILED
            execution.error_message = str(e)
            execution.metrics["error_trace"] = traceback.format_exc()
            result = []

        execution.ended_at = datetime.utcnow()
        self._execution_history.append(execution)

        return result, execution

    def get_execution_history(self, limit: int = 10) -> List[JobExecution]:
        """获取执行历史"""
        return self._execution_history[-limit:]


class TransformScheduler:
    """转换任务调度器"""

    def __init__(self):
        self._jobs: Dict[str, TransformJob] = {}
        self._running = False
        self._schedule_tasks: Dict[str, asyncio.Task] = {}

    def register_job(self, job: TransformJob) -> None:
        """注册任务"""
        self._jobs[job.config.name] = job

        # 如果有调度配置，启动定时任务
        if job.config.schedule and job.config.enabled:
            self._start_scheduled_job(job)

    def unregister_job(self, job_name: str) -> None:
        """注销任务"""
        if job_name in self._jobs:
            # 停止调度任务
            if job_name in self._schedule_tasks:
                self._schedule_tasks[job_name].cancel()
                del self._schedule_tasks[job_name]
            del self._jobs[job_name]

    def _start_scheduled_job(self, job: TransformJob) -> None:
        """启动定时调度任务"""
        async def run_loop():
            while self._running and job.config.enabled:
                try:
                    # 解析 cron 表达式 (简化实现)
                    interval = self._parse_cron(job.config.schedule)
                    await asyncio.sleep(interval)

                    # 执行任务
                    # 注意：这里需要从数据源获取数据
                    logger.info(f"Scheduled job execution: {job.config.name}")

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Scheduled job error: {e}")
                    await asyncio.sleep(60)  # 错误后等待 1 分钟

        task = asyncio.create_task(run_loop())
        self._schedule_tasks[job.config.name] = task

    def _parse_cron(self, cron_expr: str) -> int:
        """解析 cron 表达式，返回间隔秒数 (简化实现)"""
        # 支持简单的间隔表示法
        if cron_expr.startswith("*/"):
            parts = cron_expr.split()
            if len(parts) >= 1:
                try:
                    minutes = int(parts[0].replace("*/", ""))
                    return minutes * 60
                except ValueError:
                    pass

        # 默认每分钟执行一次
        return 60

    async def start(self) -> None:
        """启动调度器"""
        self._running = True
        logger.info("Transform scheduler started")

    async def stop(self) -> None:
        """停止调度器"""
        self._running = False

        for task in self._schedule_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        logger.info("Transform scheduler stopped")


class TransformTemplateLibrary:
    """转换模板库"""

    TEMPLATES = {
        "deduplicate": {
            "description": "去重转换",
            "type": TransformType.PYTHON,
            "config": {
                "python_code": """
def transform(data):
    seen = set()
    result = []
    for row in data:
        key = tuple(sorted(row.items()))
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result
"""
            }
        },
        "normalize_columns": {
            "description": "列名标准化",
            "type": TransformType.PYTHON,
            "config": {
                "python_code": """
def transform(data):
    import re
    result = []
    for row in data:
        new_row = {}
        for key, value in row.items():
            # 转换为小写，空格替换为下划线
            new_key = re.sub(r'\\s+', '_', key.lower())
            new_row[new_key] = value
        result.append(new_row)
    return result
"""
            }
        },
        "filter_nulls": {
            "description": "过滤空值",
            "type": TransformType.FILTER,
            "config": {
                "conditions": [
                    {"column": None, "operator": "is_not_null", "value": None}
                ]
            }
        },
        "sum_aggregation": {
            "description": "求和聚合",
            "type": TransformType.AGGREGATION,
            "config": {
                "aggregation": {
                    "group_by": [],
                    "aggregations": {"*": "sum"}
                }
            }
        },
        "pivot_table": {
            "description": "数据透视表",
            "type": TransformType.PIVOT,
            "config": {}
        }
    }

    @classmethod
    def get_template(cls, name: str) -> Optional[Dict[str, Any]]:
        """获取模板"""
        return cls.TEMPLATES.get(name)

    @classmethod
    def list_templates(cls) -> List[Dict[str, Any]]:
        """列出所有模板"""
        return [
            {"name": name, "description": info["description"], "type": info["type"].value}
            for name, info in cls.TEMPLATES.items()
        ]

    @classmethod
    def create_job_from_template(
        cls,
        template_name: str,
        job_name: str,
        source_tables: List[str],
        target_table: str
    ) -> TransformJob:
        """从模板创建任务"""
        template = cls.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")

        config = TransformConfig(
            name=job_name,
            transform_type=template["type"],
            source_tables=source_tables,
            target_table=target_table,
            config=template["config"]
        )

        return TransformJob(config)


# 数据库初始化
async def init_transform_tables():
    """初始化转换相关数据库表"""
    async with db_manager.get_async_session() as session:
        from sqlalchemy import Table, MetaData
        metadata = MetaData()

        transform_jobs = Table(
            'transform_jobs', metadata,
            Column('id', Integer, primary_key=True),
            Column('name', String(255), unique=True, nullable=False),
            Column('transform_type', String(50), nullable=False),
            Column('source_tables', JSON),
            Column('target_table', String(255), nullable=False),
            Column('config', JSON),
            Column('schedule', String(100)),
            Column('enabled', Boolean, default=True),
            Column('created_at', DateTime, default=datetime.utcnow),
            Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
            Index('idx_transform_jobs_name', 'name'),
            Index('idx_transform_jobs_enabled', 'enabled'),
        )

        quality_rules = Table(
            'quality_rules', metadata,
            Column('id', Integer, primary_key=True),
            Column('name', String(255), unique=True, nullable=False),
            Column('check_type', String(50), nullable=False),
            Column('table_name', String(255), nullable=False),
            Column('column_name', String(255)),
            Column('params', JSON),
            Column('severity', String(20), default='error'),
            Column('description', Text),
            Column('enabled', Boolean, default=True),
            Column('created_at', DateTime, default=datetime.utcnow),
            Index('idx_quality_rules_name', 'name'),
            Index('idx_quality_rules_table', 'table_name'),
        )

        job_executions = Table(
            'job_executions', metadata,
            Column('id', Integer, primary_key=True),
            Column('job_name', String(255), nullable=False),
            Column('status', String(20), nullable=False),
            Column('started_at', DateTime),
            Column('ended_at', DateTime),
            Column('input_rows', Integer, default=0),
            Column('output_rows', Integer, default=0),
            Column('error_message', Text),
            Column('metrics', JSON),
            Column('created_at', DateTime, default=datetime.utcnow),
            Index('idx_job_executions_job', 'job_name'),
            Index('idx_job_executions_status', 'status'),
            Index('idx_job_executions_created', 'created_at'),
        )

        await db_manager.init_db()
        logger.info("Transform database tables initialized")


# 全局服务实例
quality_checker = DataQualityChecker()
transform_scheduler = TransformScheduler()


async def start_transform_service():
    """启动转换服务"""
    await init_transform_tables()
    await transform_scheduler.start()
    logger.info("Transform service started")


async def stop_transform_service():
    """停止转换服务"""
    await transform_scheduler.stop()
    logger.info("Transform service stopped")
