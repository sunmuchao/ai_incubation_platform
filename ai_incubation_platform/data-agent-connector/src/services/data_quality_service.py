"""
数据质量监控服务

实现：
1. 完整性检查
2. 准确性检查
3. 一致性检查
4. 及时性检查
5. 异常检测
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from sqlalchemy import select, desc, and_, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import db_manager
from models.data_quality import QualityRuleModel, QualityResultModel, AnomalyModel, QualityDashboardModel
from utils.logger import logger


class RuleType(str, Enum):
    """规则类型"""
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    ANOMALY = "anomaly"


class CheckStatus(str, Enum):
    """检查状态"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    ERROR = "error"


class DataQualityService:
    """数据质量监控服务"""

    def __init__(self):
        self._initialized = False
        self._scheduler_task = None

    async def initialize(self):
        """初始化服务"""
        self._initialized = True
        # 启动定时调度任务
        self._scheduler_task = asyncio.create_task(self._schedule_loop())
        logger.info("Data quality service initialized")

    async def close(self):
        """关闭服务"""
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        self._initialized = False

    async def _schedule_loop(self):
        """定时调度检查任务"""
        while self._initialized:
            try:
                await self._run_scheduled_checks()
                await asyncio.sleep(60)  # 每分钟检查一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduled checks: {e}")
                await asyncio.sleep(60)

    async def _run_scheduled_checks(self):
        """运行调度的检查任务"""
        async with db_manager.get_async_session() as session:
            # 获取所有启用的调度规则
            now = datetime.utcnow()
            result = await session.execute(
                select(QualityRuleModel).where(
                    and_(
                        QualityRuleModel.is_active == True,
                        QualityRuleModel.schedule_enabled == True,
                        QualityRuleModel.schedule_cron.isnot(None)
                    )
                )
            )
            rules = result.scalars().all()

            for rule in rules:
                # 检查是否需要运行
                should_run = await self._should_run_rule(rule, now)
                if should_run:
                    await self.execute_rule(rule.id)

    async def _should_run_rule(self, rule: QualityRuleModel, now: datetime) -> bool:
        """判断规则是否应该运行"""
        # 简化实现：检查上次运行时间
        if rule.last_checked_at is None:
            return True

        # 根据 interval 判断
        if rule.schedule_interval_seconds:
            elapsed = (now - rule.last_checked_at).total_seconds()
            return elapsed >= rule.schedule_interval_seconds

        return False

    # ==================== 规则管理 ====================

    async def create_rule(
        self,
        name: str,
        datasource: str,
        table_name: str,
        rule_type: str,
        rule_expression: str,
        threshold: float = None,
        column_name: str = None,
        description: str = None,
        severity: str = "warning",
        schedule_enabled: bool = False,
        schedule_cron: str = None,
        created_by: str = None
    ) -> str:
        """创建质量规则"""
        async with db_manager.get_async_session() as session:
            rule = QualityRuleModel(
                name=name,
                description=description,
                datasource=datasource,
                table_name=table_name,
                column_name=column_name,
                rule_type=rule_type,
                rule_expression=rule_expression,
                threshold=threshold,
                severity=severity,
                schedule_enabled=schedule_enabled,
                schedule_cron=schedule_cron,
                created_by=created_by
            )
            session.add(rule)
            await session.flush()
            return rule.id

    async def get_rule(self, rule_id: str) -> Optional[QualityRuleModel]:
        """获取规则"""
        async with db_manager.get_async_session() as session:
            result = await session.execute(
                select(QualityRuleModel).where(QualityRuleModel.id == rule_id)
            )
            return result.scalar_one_or_none()

    async def list_rules(
        self,
        datasource: str = None,
        table_name: str = None,
        rule_type: str = None,
        is_active: bool = True
    ) -> List[QualityRuleModel]:
        """列出规则"""
        async with db_manager.get_async_session() as session:
            conditions = [QualityRuleModel.is_active == is_active]
            if datasource:
                conditions.append(QualityRuleModel.datasource == datasource)
            if table_name:
                conditions.append(QualityRuleModel.table_name == table_name)
            if rule_type:
                conditions.append(QualityRuleModel.rule_type == rule_type)

            result = await session.execute(
                select(QualityRuleModel).where(and_(*conditions))
                .order_by(desc(QualityRuleModel.created_at))
            )
            return list(result.scalars().all())

    async def delete_rule(self, rule_id: str) -> bool:
        """删除规则"""
        async with db_manager.get_async_session() as session:
            result = await session.execute(
                select(QualityRuleModel).where(QualityRuleModel.id == rule_id)
            )
            rule = result.scalar_one_or_none()
            if rule:
                await session.delete(rule)
                return True
            return False

    # ==================== 完整性检查 ====================

    async def check_completeness(
        self,
        datasource: str,
        table_name: str,
        columns: List[str] = None,
        threshold: float = 0.95
    ) -> Dict[str, Any]:
        """
        完整性检查 - 检查空值率

        Args:
            datasource: 数据源
            table_name: 表名
            columns: 列列表
            threshold: 完整性阈值

        Returns:
            检查结果
        """
        start_time = time.time()

        try:
            # 获取连接器
            from connectors.database import DatabaseConnector
            connector = DatabaseConnector(datasource)
            await connector.connect()

            # 获取表信息
            if not columns:
                columns = await connector.get_columns(table_name)
                columns = [col["name"] for col in columns]

            # 检查每列的空值率
            results = {}
            total_rows = 0
            for col in columns:
                row = await connector.execute_query(
                    f"""
                    SELECT
                        COUNT(*) as total,
                        COUNT({col}) as non_null,
                        SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END) as null_count
                    FROM {table_name}
                    """
                )
                if row:
                    total_rows = row[0].get("total", 0)
                    null_count = row[0].get("null_count", 0)
                    non_null = row[0].get("non_null", 0)
                    completeness = non_null / total_rows if total_rows > 0 else 0

                    results[col] = {
                        "total": total_rows,
                        "non_null": non_null,
                        "null_count": null_count,
                        "completeness": round(completeness, 4),
                        "passed": completeness >= threshold
                    }

            await connector.disconnect()

            # 总体评分
            avg_completeness = sum(r["completeness"] for r in results.values()) / len(results) if results else 0
            all_passed = all(r["passed"] for r in results.values())

            return {
                "status": CheckStatus.PASSED.value if all_passed else CheckStatus.FAILED.value,
                "metrics": {
                    "average_completeness": round(avg_completeness, 4),
                    "column_results": results,
                    "threshold": threshold
                },
                "total_rows": total_rows,
                "execution_time_ms": int((time.time() - start_time) * 1000)
            }

        except Exception as e:
            logger.error(f"Completeness check failed: {e}")
            return {
                "status": CheckStatus.ERROR.value,
                "error": str(e),
                "execution_time_ms": int((time.time() - start_time) * 1000)
            }

    # ==================== 准确性检查 ====================

    async def check_accuracy(
        self,
        datasource: str,
        table_name: str,
        rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        准确性检查 - 检查数据格式和范围

        Args:
            datasource: 数据源
            table_name: 表名
            rules: 规则列表，每项包含 column, condition

        Returns:
            检查结果
        """
        start_time = time.time()

        try:
            from connectors.database import DatabaseConnector
            connector = DatabaseConnector(datasource)
            await connector.connect()

            results = {}
            for rule in rules:
                col = rule.get("column")
                condition = rule.get("condition")  # 如：age > 0 AND age < 150

                sql = f"""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN {condition} THEN 1 ELSE 0 END) as valid_count
                FROM {table_name}
                WHERE {col} IS NOT NULL
                """

                row = await connector.execute_query(sql)
                if row:
                    total = row[0].get("total", 0)
                    valid = row[0].get("valid_count", 0)
                    accuracy = valid / total if total > 0 else 0

                    results[col] = {
                        "total": total,
                        "valid": valid,
                        "invalid": total - valid,
                        "accuracy": round(accuracy, 4),
                        "condition": condition
                    }

            await connector.disconnect()

            avg_accuracy = sum(r["accuracy"] for r in results.values()) / len(results) if results else 0

            return {
                "status": CheckStatus.PASSED.value if avg_accuracy >= 0.95 else CheckStatus.FAILED.value,
                "metrics": {
                    "average_accuracy": round(avg_accuracy, 4),
                    "column_results": results
                },
                "execution_time_ms": int((time.time() - start_time) * 1000)
            }

        except Exception as e:
            logger.error(f"Accuracy check failed: {e}")
            return {
                "status": CheckStatus.ERROR.value,
                "error": str(e),
                "execution_time_ms": int((time.time() - start_time) * 1000)
            }

    # ==================== 一致性检查 ====================

    async def check_consistency(
        self,
        source_datasource: str,
        target_datasource: str,
        table_name: str,
        key_columns: List[str]
    ) -> Dict[str, Any]:
        """
        一致性检查 - 检查跨数据源数据一致性

        Args:
            source_datasource: 源数据源
            target_datasource: 目标数据源
            table_name: 表名
            key_columns: 关键列

        Returns:
            检查结果
        """
        start_time = time.time()

        try:
            from connectors.database import DatabaseConnector

            source_conn = DatabaseConnector(source_datasource)
            target_conn = DatabaseConnector(target_datasource)

            await source_conn.connect()
            await target_conn.connect()

            # 获取源数据
            key_cols_str = ", ".join(key_columns)
            source_data = await source_conn.execute_query(
                f"SELECT {key_cols_str}, COUNT(*) as cnt FROM {table_name} GROUP BY {key_cols_str}"
            )

            # 获取目标数据
            target_data = await target_conn.execute_query(
                f"SELECT {key_cols_str}, COUNT(*) as cnt FROM {table_name} GROUP BY {key_cols_str}"
            )

            # 比较
            source_set = set(tuple(row[col] for col in key_columns) for row in source_data)
            target_set = set(tuple(row[col] for col in key_columns) for row in target_data)

            missing_in_target = source_set - target_set
            extra_in_target = target_set - source_set

            await source_conn.disconnect()
            await target_conn.disconnect()

            is_consistent = len(missing_in_target) == 0 and len(extra_in_target) == 0

            return {
                "status": CheckStatus.PASSED.value if is_consistent else CheckStatus.FAILED.value,
                "metrics": {
                    "source_count": len(source_data),
                    "target_count": len(target_data),
                    "missing_in_target": len(missing_in_target),
                    "extra_in_target": len(extra_in_target)
                },
                "execution_time_ms": int((time.time() - start_time) * 1000)
            }

        except Exception as e:
            logger.error(f"Consistency check failed: {e}")
            return {
                "status": CheckStatus.ERROR.value,
                "error": str(e),
                "execution_time_ms": int((time.time() - start_time) * 1000)
            }

    # ==================== 及时性检查 ====================

    async def check_timeliness(
        self,
        datasource: str,
        table_name: str,
        timestamp_column: str,
        max_delay_hours: int = 24
    ) -> Dict[str, Any]:
        """
        及时性检查 - 检查数据更新延迟

        Args:
            datasource: 数据源
            table_name: 表名
            timestamp_column: 时间戳列
            max_delay_hours: 最大延迟小时数

        Returns:
            检查结果
        """
        start_time = time.time()

        try:
            from connectors.database import DatabaseConnector
            connector = DatabaseConnector(datasource)
            await connector.connect()

            # 获取最新时间戳
            row = await connector.execute_query(
                f"SELECT MAX({timestamp_column}) as latest FROM {table_name}"
            )

            await connector.disconnect()

            if row and row[0].get("latest"):
                latest = row[0]["latest"]
                if isinstance(latest, datetime):
                    delay = (datetime.utcnow() - latest).total_seconds() / 3600
                else:
                    delay = 0  # 无法解析时间

                is_timely = delay <= max_delay_hours

                return {
                    "status": CheckStatus.PASSED.value if is_timely else CheckStatus.FAILED.value,
                    "metrics": {
                        "latest_timestamp": latest.isoformat() if isinstance(latest, datetime) else str(latest),
                        "delay_hours": round(delay, 2),
                        "max_allowed_hours": max_delay_hours
                    },
                    "execution_time_ms": int((time.time() - start_time) * 1000)
                }
            else:
                return {
                    "status": CheckStatus.FAILED.value,
                    "metrics": {
                        "error": "No data found"
                    },
                    "execution_time_ms": int((time.time() - start_time) * 1000)
                }

        except Exception as e:
            logger.error(f"Timeliness check failed: {e}")
            return {
                "status": CheckStatus.ERROR.value,
                "error": str(e),
                "execution_time_ms": int((time.time() - start_time) * 1000)
            }

    # ==================== 异常检测 ====================

    async def detect_anomalies(
        self,
        datasource: str,
        table_name: str,
        column: str,
        time_range: timedelta = None
    ) -> List[Dict[str, Any]]:
        """
        异常检测 - 检测数值异常

        Args:
            datasource: 数据源
            table_name: 表名
            column: 列名
            time_range: 时间范围

        Returns:
            异常列表
        """
        start_time = time.time()
        anomalies = []

        try:
            from connectors.database import DatabaseConnector
            connector = DatabaseConnector(datasource)
            await connector.connect()

            # 计算统计信息
            where_clause = ""
            if time_range:
                cutoff = datetime.utcnow() - time_range
                where_clause = f"WHERE updated_at >= '{cutoff}'"

            stats = await connector.execute_query(
                f"""
                SELECT
                    AVG({column}) as mean,
                    STDDEV({column}) as stddev,
                    MIN({column}) as min_val,
                    MAX({column}) as max_val
                FROM {table_name}
                {where_clause}
                """
            )

            if stats and stats[0]:
                mean = stats[0].get("mean", 0)
                stddev = stats[0].get("stddev", 1)

                # 检测 3-sigma 异常
                lower_bound = mean - 3 * stddev
                upper_bound = mean + 3 * stddev

                # 查找异常值
                outliers = await connector.execute_query(
                    f"""
                    SELECT * FROM {table_name}
                    WHERE {column} < {lower_bound} OR {column} > {upper_bound}
                    {where_clause}
                    LIMIT 100
                    """
                )

                for row in outliers:
                    value = row.get(column)
                    if value:
                        deviation = abs(value - mean) / stddev if stddev > 0 else 0
                        anomalies.append({
                            "datasource": datasource,
                            "table_name": table_name,
                            "column": column,
                            "row_id": row.get("id", str(row)),
                            "anomaly_type": "value",
                            "anomaly_score": min(1.0, deviation / 3),
                            "expected_value": f"{mean:.2f}",
                            "actual_value": str(value),
                            "deviation": round(deviation, 2)
                        })

            await connector.disconnect()

            logger.info(f"Detected {len(anomalies)} anomalies in {table_name}.{column}")
            return anomalies

        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return []

    # ==================== 执行规则 ====================

    async def execute_rule(self, rule_id: str) -> Dict[str, Any]:
        """执行质量规则"""
        rule = await self.get_rule(rule_id)
        if not rule:
            return {"error": "Rule not found"}

        result = None
        start_time = time.time()

        try:
            if rule.rule_type == RuleType.COMPLETENESS.value:
                result = await self.check_completeness(
                    datasource=rule.datasource,
                    table_name=rule.table_name,
                    columns=[rule.column_name] if rule.column_name else None,
                    threshold=rule.threshold or 0.95
                )
            elif rule.rule_type == RuleType.ACCURACY.value:
                # 解析规则表达式
                rules = eval(rule.rule_expression) if rule.rule_expression else []
                result = await self.check_accuracy(
                    datasource=rule.datasource,
                    table_name=rule.table_name,
                    rules=rules
                )
            elif rule.rule_type == RuleType.CONSISTENCY.value:
                # 解析规则表达式
                config = eval(rule.rule_expression) if rule.rule_expression else {}
                result = await self.check_consistency(
                    source_datasource=rule.datasource,
                    target_datasource=config.get("target_datasource", ""),
                    table_name=rule.table_name,
                    key_columns=config.get("key_columns", [])
                )
            elif rule.rule_type == RuleType.TIMELINESS.value:
                result = await self.check_timeliness(
                    datasource=rule.datasource,
                    table_name=rule.table_name,
                    timestamp_column=rule.column_name or "updated_at",
                    max_delay_hours=int(rule.threshold) if rule.threshold else 24
                )
            elif rule.rule_type == RuleType.ANOMALY.value:
                anomalies = await self.detect_anomalies(
                    datasource=rule.datasource,
                    table_name=rule.table_name,
                    column=rule.column_name
                )
                result = {
                    "status": CheckStatus.FAILED.value if anomalies else CheckStatus.PASSED.value,
                    "anomalies": anomalies,
                    "anomaly_count": len(anomalies)
                }

            # 保存结果
            if result:
                await self._save_result(rule_id, result)

                # 更新规则的最后检查时间
                async with db_manager.get_async_session() as session:
                    rule.last_checked_at = datetime.utcnow()
                    session.add(rule)

            return result or {"error": "No result"}

        except Exception as e:
            logger.error(f"Rule execution failed: {e}")
            return {
                "status": CheckStatus.ERROR.value,
                "error": str(e)
            }

    async def _save_result(self, rule_id: str, result: Dict[str, Any]):
        """保存检查结果"""
        async with db_manager.get_async_session() as session:
            quality_result = QualityResultModel(
                rule_id=rule_id,
                status=result.get("status", "unknown"),
                actual_value=result.get("metrics", {}).get("average_completeness") or
                             result.get("metrics", {}).get("average_accuracy"),
                expected_value=None,
                metrics=result.get("metrics", {}),
                error_count=result.get("metrics", {}).get("error_count", 0),
                total_count=result.get("total_rows", 0),
                error_rate=result.get("metrics", {}).get("error_rate"),
                error_samples=result.get("metrics", {}).get("column_results", [])[:10],
                execution_time_ms=result.get("execution_time_ms", 0)
            )
            session.add(quality_result)

    # ==================== 结果查询 ====================

    async def get_results(
        self,
        rule_id: str = None,
        status: str = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[QualityResultModel]:
        """获取检查结果"""
        async with db_manager.get_async_session() as session:
            conditions = [
                QualityResultModel.checked_at >= datetime.utcnow() - timedelta(hours=hours)
            ]
            if rule_id:
                conditions.append(QualityResultModel.rule_id == rule_id)
            if status:
                conditions.append(QualityResultModel.status == status)

            result = await session.execute(
                select(QualityResultModel)
                .where(and_(*conditions))
                .order_by(desc(QualityResultModel.checked_at))
                .limit(limit)
            )
            return list(result.scalars().all())

    async def get_anomalies(
        self,
        datasource: str = None,
        table_name: str = None,
        is_resolved: bool = False,
        hours: int = 24,
        limit: int = 100
    ) -> List[AnomalyModel]:
        """获取异常记录"""
        async with db_manager.get_async_session() as session:
            conditions = [
                AnomalyModel.detected_at >= datetime.utcnow() - timedelta(hours=hours),
                AnomalyModel.is_resolved == is_resolved
            ]
            if datasource:
                conditions.append(AnomalyModel.datasource == datasource)
            if table_name:
                conditions.append(AnomalyModel.table_name == table_name)

            result = await session.execute(
                select(AnomalyModel)
                .where(and_(*conditions))
                .order_by(desc(AnomalyModel.detected_at))
                .limit(limit)
            )
            return list(result.scalars().all())


# 全局数据质量服务实例
data_quality_service = DataQualityService()
