"""
连接器性能基准测试框架 - v1.4
用于测试和比较不同连接器的性能表现
"""
import asyncio
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import statistics

from connectors.base import ConnectorConfig, ConnectorFactory, HealthStatus


@dataclass
class BenchmarkConfig:
    """基准测试配置"""
    # 连接测试
    connection_iterations: int = 10
    # 查询测试
    query_iterations: int = 100
    simple_query: str = "SELECT 1"
    # 并发测试
    concurrency_levels: List[int] = field(default_factory=lambda: [1, 5, 10, 20])
    concurrent_query: str = "SELECT 1"
    # 超时设置
    timeout_seconds: int = 60


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    connector_type: str
    connector_name: str
    test_timestamp: str

    # 连接性能
    connection_success_rate: float = 0.0
    connection_avg_latency_ms: float = 0.0
    connection_p50_latency_ms: float = 0.0
    connection_p95_latency_ms: float = 0.0
    connection_p99_latency_ms: float = 0.0

    # 查询性能
    query_success_rate: float = 0.0
    query_avg_latency_ms: float = 0.0
    query_p50_latency_ms: float = 0.0
    query_p95_latency_ms: float = 0.0
    query_p99_latency_ms: float = 0.0
    query_throughput_qps: float = 0.0  # 每秒查询数

    # 并发性能
    concurrency_results: Dict[int, Dict[str, float]] = field(default_factory=dict)

    # 总体评分
    overall_score: float = 0.0
    grade: str = "N/A"  # A, B, C, D, F

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "connector_type": self.connector_type,
            "connector_name": self.connector_name,
            "test_timestamp": self.test_timestamp,
            "connection_performance": {
                "success_rate": self.connection_success_rate,
                "avg_latency_ms": self.connection_avg_latency_ms,
                "p50_latency_ms": self.connection_p50_latency_ms,
                "p95_latency_ms": self.connection_p95_latency_ms,
                "p99_latency_ms": self.connection_p99_latency_ms,
            },
            "query_performance": {
                "success_rate": self.query_success_rate,
                "avg_latency_ms": self.query_avg_latency_ms,
                "p50_latency_ms": self.query_p50_latency_ms,
                "p95_latency_ms": self.query_p95_latency_ms,
                "p99_latency_ms": self.query_p99_latency_ms,
                "throughput_qps": self.query_throughput_qps,
            },
            "concurrency_performance": self.concurrency_results,
            "overall": {
                "score": self.overall_score,
                "grade": self.grade,
            }
        }


class ConnectorBenchmark:
    """连接器基准测试器"""

    def __init__(self, config: BenchmarkConfig):
        self.config = config

    async def run_all_tests(
        self,
        connector_type: str,
        connector_config: ConnectorConfig
    ) -> BenchmarkResult:
        """运行所有基准测试"""
        result = BenchmarkResult(
            connector_type=connector_type,
            connector_name=connector_config.name,
            test_timestamp=datetime.utcnow().isoformat()
        )

        # 1. 连接性能测试
        conn_latencies = await self._test_connection_performance(connector_type, connector_config)
        if conn_latencies:
            result.connection_success_rate = 100.0
            result.connection_avg_latency_ms = statistics.mean(conn_latencies)
            result.connection_p50_latency_ms = self._percentile(conn_latencies, 50)
            result.connection_p95_latency_ms = self._percentile(conn_latencies, 95)
            result.connection_p99_latency_ms = self._percentile(conn_latencies, 99)

        # 2. 查询性能测试
        query_latencies, query_success = await self._test_query_performance(connector_type, connector_config)
        if query_latencies:
            result.query_success_rate = query_success
            result.query_avg_latency_ms = statistics.mean(query_latencies)
            result.query_p50_latency_ms = self._percentile(query_latencies, 50)
            result.query_p95_latency_ms = self._percentile(query_latencies, 95)
            result.query_p99_latency_ms = self._percentile(query_latencies, 99)
            total_time = sum(query_latencies) / 1000  # 转秒
            result.query_throughput_qps = len(query_latencies) / total_time if total_time > 0 else 0

        # 3. 并发性能测试
        for concurrency in self.config.concurrency_levels:
            concurrency_result = await self._test_concurrency_performance(
                connector_type, connector_config, concurrency
            )
            result.concurrency_results[concurrency] = concurrency_result

        # 4. 计算总体评分
        self._calculate_overall_score(result)

        return result

    async def _test_connection_performance(
        self,
        connector_type: str,
        config: ConnectorConfig
    ) -> List[float]:
        """测试连接性能"""
        latencies = []

        for i in range(self.config.connection_iterations):
            start = time.time()
            try:
                connector = ConnectorFactory.create(connector_type, config)
                await connector.connect()
                await connector.disconnect()
                latency_ms = (time.time() - start) * 1000
                latencies.append(latency_ms)
            except Exception as e:
                latencies.append(float('inf'))

        # 过滤失败的连接
        return [l for l in latencies if l != float('inf')]

    async def _test_query_performance(
        self,
        connector_type: str,
        config: ConnectorConfig
    ) -> tuple:
        """测试查询性能"""
        latencies = []
        success_count = 0

        connector = None
        try:
            connector = ConnectorFactory.create(connector_type, config)
            await connector.connect()

            for i in range(self.config.query_iterations):
                start = time.time()
                try:
                    await connector.execute(self.config.simple_query)
                    latency_ms = (time.time() - start) * 1000
                    latencies.append(latency_ms)
                    success_count += 1
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            if connector:
                await connector.disconnect()

        success_rate = (success_count / self.config.query_iterations) * 100 if self.config.query_iterations > 0 else 0
        return latencies, success_rate

    async def _test_concurrency_performance(
        self,
        connector_type: str,
        config: ConnectorConfig,
        concurrency: int
    ) -> Dict[str, float]:
        """测试并发性能"""
        async def run_query(connector):
            start = time.time()
            try:
                await connector.execute(self.config.concurrent_query)
                return (time.time() - start) * 1000
            except Exception:
                return float('inf')

        connector = None
        try:
            connector = ConnectorFactory.create(connector_type, config)
            await connector.connect()

            # 并发执行查询
            tasks = [run_query(connector) for _ in range(concurrency)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            valid_results = [r for r in results if isinstance(r, (int, float)) and r != float('inf')]

            if valid_results:
                avg_latency = statistics.mean(valid_results)
                total_time = max(valid_results) / 1000 if valid_results else 1
                throughput = len(valid_results) / total_time

                return {
                    "success_rate": len(valid_results) / concurrency * 100,
                    "avg_latency_ms": round(avg_latency, 2),
                    "throughput_qps": round(throughput, 2),
                }
            else:
                return {
                    "success_rate": 0.0,
                    "avg_latency_ms": 0.0,
                    "throughput_qps": 0.0,
                }
        except Exception:
            return {
                "success_rate": 0.0,
                "avg_latency_ms": 0.0,
                "throughput_qps": 0.0,
            }
        finally:
            if connector:
                await connector.disconnect()

    def _percentile(self, data: List[float], percentile: int) -> float:
        """计算百分位数"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def _calculate_overall_score(self, result: BenchmarkResult) -> None:
        """计算总体评分"""
        score = 0.0

        # 连接性能评分 (25%)
        if result.connection_success_rate > 0:
            conn_score = min(100, result.connection_success_rate)
            if result.connection_avg_latency_ms < 100:
                conn_score *= 1.0
            elif result.connection_avg_latency_ms < 500:
                conn_score *= 0.8
            elif result.connection_avg_latency_ms < 1000:
                conn_score *= 0.6
            else:
                conn_score *= 0.4
            score += conn_score * 0.25

        # 查询性能评分 (50%)
        if result.query_success_rate > 0:
            query_score = min(100, result.query_success_rate)
            if result.query_avg_latency_ms < 10:
                query_score *= 1.0
            elif result.query_avg_latency_ms < 50:
                query_score *= 0.9
            elif result.query_avg_latency_ms < 100:
                query_score *= 0.7
            else:
                query_score *= 0.5
            score += query_score * 0.50

        # 并发性能评分 (25%)
        if result.concurrency_results:
            concurrency_scores = []
            for level, metrics in result.concurrency_results.items():
                if metrics.get("success_rate", 0) > 0:
                    concurrency_scores.append(metrics.get("success_rate", 0))
            if concurrency_scores:
                score += statistics.mean(concurrency_scores) * 0.25

        result.overall_score = round(score, 2)

        # 评定等级
        if score >= 90:
            result.grade = "A"
        elif score >= 80:
            result.grade = "B"
        elif score >= 70:
            result.grade = "C"
        elif score >= 60:
            result.grade = "D"
        else:
            result.grade = "F"


class BenchmarkReporter:
    """基准测试报告生成器"""

    @staticmethod
    def generate_markdown_report(results: List[BenchmarkResult]) -> str:
        """生成 Markdown 格式报告"""
        lines = [
            "# 连接器性能基准测试报告",
            "",
            f"**生成时间**: {datetime.utcnow().isoformat()}",
            "",
            "## 测试概要",
            "",
            f"- **测试连接器数量**: {len(results)}",
            f"- **测试时间范围**: {results[0].test_timestamp if results else 'N/A'}",
            "",
            "## 性能排名",
            "",
            "| 排名 | 连接器 | 类型 | 总体评分 | 等级 | 查询 QPS | P95 延迟 |",
            "|------|--------|------|----------|------|----------|----------|",
        ]

        # 按评分排序
        sorted_results = sorted(results, key=lambda r: r.overall_score, reverse=True)

        for i, result in enumerate(sorted_results, 1):
            lines.append(
                f"| {i} | {result.connector_name} | {result.connector_type} | "
                f"{result.overall_score} | {result.grade} | "
                f"{result.query_throughput_qps:.1f} | {result.query_p95_latency_ms:.2f}ms |"
            )

        lines.extend([
            "",
            "## 详细结果",
            "",
        ])

        for result in results:
            lines.extend([
                f"### {result.connector_name} ({result.connector_type})",
                "",
                f"**总体评分**: {result.overall_score} ({result.grade})",
                "",
                "#### 连接性能",
                f"- 成功率：{result.connection_success_rate:.1f}%",
                f"- 平均延迟：{result.connection_avg_latency_ms:.2f}ms",
                f"- P50 延迟：{result.connection_p50_latency_ms:.2f}ms",
                f"- P95 延迟：{result.connection_p95_latency_ms:.2f}ms",
                f"- P99 延迟：{result.connection_p99_latency_ms:.2f}ms",
                "",
                "#### 查询性能",
                f"- 成功率：{result.query_success_rate:.1f}%",
                f"- 平均延迟：{result.query_avg_latency_ms:.2f}ms",
                f"- P50 延迟：{result.query_p50_latency_ms:.2f}ms",
                f"- P95 延迟：{result.query_p95_latency_ms:.2f}ms",
                f"- 吞吐量：{result.query_throughput_qps:.1f} QPS",
                "",
                "#### 并发性能",
            ])

            for concurrency, metrics in result.concurrency_results.items():
                lines.append(
                    f"- 并发度 {concurrency}: 成功率 {metrics.get('success_rate', 0):.1f}%, "
                    f"平均延迟 {metrics.get('avg_latency_ms', 0):.2f}ms, "
                    f"吞吐量 {metrics.get('throughput_qps', 0):.1f} QPS"
                )

            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def generate_json_report(results: List[BenchmarkResult]) -> Dict[str, Any]:
        """生成 JSON 格式报告"""
        return {
            "report_timestamp": datetime.utcnow().isoformat(),
            "total_connectors": len(results),
            "results": [r.to_dict() for r in results],
            "ranking": [
                {
                    "rank": i + 1,
                    "connector": r.connector_name,
                    "type": r.connector_type,
                    "score": r.overall_score,
                    "grade": r.grade
                }
                for i, r in enumerate(sorted(results, key=lambda x: x.overall_score, reverse=True))
            ]
        }


# 便捷函数
async def benchmark_connector(
    connector_type: str,
    config: ConnectorConfig,
    benchmark_config: Optional[BenchmarkConfig] = None
) -> BenchmarkResult:
    """便捷函数：运行连接器基准测试"""
    if benchmark_config is None:
        benchmark_config = BenchmarkConfig()

    benchmark = ConnectorBenchmark(benchmark_config)
    return await benchmark.run_all_tests(connector_type, config)


async def benchmark_all_connectors(
    configs: List[tuple],
    benchmark_config: Optional[BenchmarkConfig] = None
) -> List[BenchmarkResult]:
    """
    便捷函数：批量测试所有连接器

    configs: [(connector_type, ConnectorConfig), ...]
    """
    if benchmark_config is None:
        benchmark_config = BenchmarkConfig()

    results = []
    for connector_type, config in configs:
        try:
            result = await benchmark_connector(connector_type, config, benchmark_config)
            results.append(result)
        except Exception as e:
            print(f"Failed to benchmark {connector_type}: {e}")

    return results


# 导出
__all__ = [
    "BenchmarkConfig",
    "BenchmarkResult",
    "ConnectorBenchmark",
    "BenchmarkReporter",
    "benchmark_connector",
    "benchmark_all_connectors",
]
