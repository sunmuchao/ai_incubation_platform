#!/usr/bin/env python3
"""
索引性能基准测试框架

用于评估和优化代码索引管道的性能，包括：
1. 整体索引速度测试
2. 嵌入生成性能
3. 解析器性能
4. 向量存储写入性能
5. 增量索引效率

测试场景：
- 小型项目（<100 文件）
- 中型项目（100-1000 文件）
- 大型项目（>1000 文件）
"""
import os
import sys
import time
import json
import statistics
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import tempfile
import shutil

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.indexer.base import CodeChunk
from core.indexer.pipeline import IndexPipeline
from core.indexer.parsers.tree_sitter_parser import TreeSitterParser
from core.indexer.embeddings import BGEEmbedding, HashEmbedding
from core.indexer.vector_stores.chroma_store import ChromaVectorStore


@dataclass
class BenchmarkConfig:
    """基准测试配置"""
    test_project_path: str
    num_runs: int = 3
    batch_sizes: List[int] = field(default_factory=lambda: [32, 64, 128])
    parallel_modes: List[str] = field(default_factory=lambda: ['serial', 'thread', 'process'])
    embedding_models: List[str] = field(default_factory=lambda: ['hash', 'bge-small'])
    enable_cache: bool = True
    incremental: bool = True


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    test_name: str
    timestamp: str
    config: Dict[str, Any]

    # 性能指标
    total_files: int = 0
    total_chunks: int = 0
    total_symbols: int = 0

    # 时间指标
    total_time_seconds: float = 0.0
    avg_file_time_ms: float = 0.0
    files_per_second: float = 0.0
    chunks_per_second: float = 0.0

    # 嵌入性能
    embedding_time_seconds: float = 0.0
    embedding_throughput: float = 0.0  # chunks/second

    # 解析性能
    parsing_time_seconds: float = 0.0

    # 向量存储性能
    vector_store_time_seconds: float = 0.0

    # 资源指标
    peak_memory_mb: float = 0.0

    # 增量索引指标
    incremental_savings_percent: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "timestamp": self.timestamp,
            "config": self.config,
            "performance": {
                "total_files": self.total_files,
                "total_chunks": self.total_chunks,
                "total_symbols": self.total_symbols,
                "total_time_seconds": self.total_time_seconds,
                "avg_file_time_ms": self.avg_file_time_ms,
                "files_per_second": self.files_per_second,
                "chunks_per_second": self.chunks_per_second,
            },
            "breakdown": {
                "embedding_time_seconds": self.embedding_time_seconds,
                "embedding_throughput": self.embedding_throughput,
                "parsing_time_seconds": self.parsing_time_seconds,
                "vector_store_time_seconds": self.vector_store_time_seconds,
            },
            "resources": {
                "peak_memory_mb": self.peak_memory_mb,
            },
            "incremental": {
                "incremental_savings_percent": self.incremental_savings_percent,
            }
        }


class IndexerBenchmark:
    """索引器基准测试器"""

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.results: List[BenchmarkResult] = []
        self._test_dir: Optional[Path] = None

    def setup_test_project(self) -> Path:
        """
        准备测试项目
        如果指定了测试项目路径则使用，否则创建示例项目
        """
        if self.config.test_project_path and os.path.exists(self.config.test_project_path):
            return Path(self.config.test_project_path)

        # 创建示例测试项目
        test_dir = Path(tempfile.mkdtemp(prefix="benchmark_test_"))
        self._create_sample_project(test_dir)
        return test_dir

    def _create_sample_project(self, base_dir: Path) -> None:
        """创建示例项目结构用于测试"""
        # 创建 Python 项目结构
        (base_dir / "src").mkdir(parents=True, exist_ok=True)
        (base_dir / "tests").mkdir(parents=True, exist_ok=True)
        (base_dir / "utils").mkdir(parents=True, exist_ok=True)

        # 生成 Python 文件
        for i in range(50):
            file_path = base_dir / "src" / f"module_{i}.py"
            self._generate_sample_python_file(file_path, i)

        # 生成测试文件
        for i in range(20):
            file_path = base_dir / "tests" / f"test_module_{i}.py"
            self._generate_sample_python_file(file_path, i, is_test=True)

        # 生成工具文件
        for i in range(10):
            file_path = base_dir / "utils" / f"helper_{i}.py"
            self._generate_sample_python_file(file_path, i)

    def _generate_sample_python_file(self, path: Path, index: int, is_test: bool = False) -> None:
        """生成示例 Python 文件"""
        content = f'''"""
Module {index} - Sample code for benchmarking
"""
import os
import sys
from typing import List, Dict, Optional


class SampleClass{index}:
    """Sample class for testing"""

    def __init__(self, name: str, value: int = 0):
        self.name = name
        self.value = value
        self._data: List[int] = []

    def process(self, items: List[int]) -> Dict[str, int]:
        """Process items and return result"""
        result = {{}}
        for i, item in enumerate(items):
            result[f"item_{{i}}"] = item * self.value
        return result

    def validate(self) -> bool:
        """Validate internal state"""
        return len(self._data) > 0 and all(x >= 0 for x in self._data)


def function_alpha_{index}(data: List[float], threshold: float = 0.5) -> List[float]:
    """
    Process data with threshold filtering

    Args:
        data: Input data list
        threshold: Filtering threshold

    Returns:
        Filtered data
    """
    return [x for x in data if x > threshold]


def function_beta_{index}(items: List[str], transform: bool = True) -> Dict[str, str]:
    """Transform items to dictionary"""
    result = {{}}
    for i, item in enumerate(items):
        key = f"key_{{i}}"
        value = item.upper() if transform else item
        result[key] = value
    return result


async def async_function_{index}(url: str) -> Dict[str, Any]:
    """Async function for testing"""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()


'''
        if is_test:
            content += f'''

# Test functions
def test_function_alpha_{index}():
    """Test function alpha"""
    data = [0.1, 0.3, 0.5, 0.7, 0.9]
    result = function_alpha_{index}(data, threshold=0.5)
    assert result == [0.7, 0.9], f"Expected [0.7, 0.9], got {{result}}"


def test_function_beta_{index}():
    """Test function beta"""
    items = ["a", "b", "c"]
    result = function_beta_{index}(items)
    assert result == {{"key_0": "A", "key_1": "B", "key_2": "C"}}


def test_sample_class_{index}():
    """Test sample class"""
    obj = SampleClass{index}("test", 10)
    assert obj.name == "test"
    assert obj.value == 10

'''
        path.write_text(content, encoding='utf-8')

    def cleanup_test_project(self, test_dir: Path) -> None:
        """清理测试项目"""
        if self._test_dir and test_dir != Path(self.config.test_project_path):
            shutil.rmtree(self._test_dir, ignore_errors=True)

    def _get_memory_usage_mb(self) -> float:
        """获取当前内存使用（MB）"""
        try:
            import resource
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # macOS returns KB
        except:
            return 0.0

    def run_full_index_benchmark(self, pipeline: IndexPipeline, test_dir: Path) -> BenchmarkResult:
        """运行完整索引基准测试"""
        start_time = time.time()
        peak_memory = 0.0

        # 统计信息
        stats = {
            'total_files': 0,
            'total_chunks': 0,
            'total_symbols': 0,
            'parsing_time': 0.0,
            'embedding_time': 0.0,
            'vector_store_time': 0.0,
        }

        # 收集所有 Python 文件
        files = list(test_dir.glob("**/*.py"))
        stats['total_files'] = len(files)

        # 索引所有文件
        for i, file_path in enumerate(files):
            file_start = time.time()

            try:
                # 解析阶段
                parse_start = time.time()
                language = pipeline._detect_language(str(file_path))
                parser = pipeline.get_parser_for_language(language)
                if parser:
                    result = parser.parse_file(str(file_path))
                    stats['parsing_time'] += time.time() - parse_start
                    stats['total_chunks'] += len(result.chunks)
                    stats['total_symbols'] += len(result.symbols)

                    # 嵌入阶段
                    embed_start = time.time()
                    chunks_with_embedding = pipeline.embedding.encode_chunks(result.chunks)
                    stats['embedding_time'] += time.time() - embed_start

                    # 向量存储阶段
                    vs_start = time.time()
                    pipeline.vector_store.upsert_chunks(pipeline.default_collection, chunks_with_embedding)
                    stats['vector_store_time'] += time.time() - vs_start

                    stats['total_files'] += 1
            except Exception as e:
                print(f"索引文件失败 {file_path}: {e}")

            # 更新峰值内存
            current_memory = self._get_memory_usage_mb()
            peak_memory = max(peak_memory, current_memory)

        total_time = time.time() - start_time

        result = BenchmarkResult(
            test_name="full_index_benchmark",
            timestamp=datetime.now().isoformat(),
            config={
                "test_dir": str(test_dir),
                "batch_size": pipeline.batch_size,
                "enable_parallel": pipeline.enable_parallel_embedding,
            },
            total_files=stats['total_files'],
            total_chunks=stats['total_chunks'],
            total_symbols=stats['total_symbols'],
            total_time_seconds=total_time,
            avg_file_time_ms=(total_time / max(stats['total_files'], 1)) * 1000,
            files_per_second=stats['total_files'] / max(total_time, 0.001),
            chunks_per_second=stats['total_chunks'] / max(total_time, 0.001),
            embedding_time_seconds=stats['embedding_time'],
            embedding_throughput=stats['total_chunks'] / max(stats['embedding_time'], 0.001),
            parsing_time_seconds=stats['parsing_time'],
            vector_store_time_seconds=stats['vector_store_time'],
            peak_memory_mb=peak_memory,
        )

        return result

    def run_incremental_benchmark(self, pipeline: IndexPipeline, test_dir: Path) -> Tuple[BenchmarkResult, BenchmarkResult]:
        """运行增量索引基准测试"""
        # 第一次完整索引
        print("  第一次完整索引...")
        result_full = self.run_full_index_benchmark(pipeline, test_dir)

        # 修改一个文件
        modified_file = list(test_dir.glob("**/*.py"))[0]
        original_content = modified_file.read_text()
        modified_content = original_content + "\n# Modified for incremental test\n"
        modified_file.write_text(modified_content)

        # 第二次增量索引
        print("  第二次增量索引...")
        result_incremental = self.run_full_index_benchmark(pipeline, test_dir)

        # 恢复文件
        modified_file.write_text(original_content)

        # 计算节省
        if result_full.total_time_seconds > 0:
            savings = (1 - result_incremental.total_time_seconds / result_full.total_time_seconds) * 100
            result_incremental.incremental_savings_percent = max(0, savings)

        return result_full, result_incremental

    def run_all_benchmarks(self) -> Dict[str, Any]:
        """运行所有基准测试"""
        test_dir = self.setup_test_project()
        print(f"测试项目：{test_dir}")
        print(f"文件数量：{len(list(test_dir.glob('**/*.py')))}")

        results = {}

        # 测试不同嵌入模型
        for model_name in self.config.embedding_models:
            print(f"\n测试嵌入模型：{model_name}")

            try:
                # 创建临时测试目录
                temp_test_dir = Path(tempfile.mkdtemp(prefix=f"benchmark_{model_name}_"))
                shutil.copytree(test_dir, temp_test_dir, dirs_exist_ok=True)

                # 创建 pipeline
                pipeline = self._create_pipeline(model_name)

                # 运行测试
                result = self.run_full_index_benchmark(pipeline, temp_test_dir)
                results[f"embedding_{model_name}"] = result.to_dict()

                # 清理
                shutil.rmtree(temp_test_dir, ignore_errors=True)

            except Exception as e:
                print(f"  测试失败：{e}")
                results[f"embedding_{model_name}"] = {"error": str(e)}

        # 测试增量索引
        print("\n测试增量索引...")
        try:
            temp_test_dir = Path(tempfile.mkdtemp(prefix="benchmark_incremental_"))
            shutil.copytree(test_dir, temp_test_dir, dirs_exist_ok=True)

            pipeline = self._create_pipeline('hash')  # 使用快速模型
            result_full, result_inc = self.run_incremental_benchmark(pipeline, temp_test_dir)
            results['incremental'] = {
                'full_index': result_full.to_dict(),
                'incremental_index': result_inc.to_dict(),
            }

            shutil.rmtree(temp_test_dir, ignore_errors=True)
        except Exception as e:
            print(f"  增量索引测试失败：{e}")
            results['incremental'] = {"error": str(e)}

        # 清理
        self.cleanup_test_project(test_dir)

        return {
            "generated_at": datetime.now().isoformat(),
            "config": {
                "test_project_path": self.config.test_project_path,
                "num_runs": self.config.num_runs,
            },
            "results": results,
            "summary": self._generate_summary(results),
        }

    def _create_pipeline(self, model_name: str) -> IndexPipeline:
        """创建索引 pipeline"""
        # 创建嵌入模型
        if model_name == 'hash':
            embedding = HashEmbedding()
        elif model_name == 'bge-small':
            embedding = BGEEmbedding({'model_name': 'BAAI/bge-small-code-v1.5'})
        else:
            embedding = HashEmbedding()

        # 创建解析器
        parser = TreeSitterParser()

        # 创建向量存储（使用内存模式）
        vector_store = ChromaVectorStore()

        # 创建 pipeline
        pipeline = IndexPipeline(
            parsers=[parser],
            embedding=embedding,
            vector_store=vector_store,
            config={
                'batch_size': 64,
                'enable_parallel_embedding': False,  # 基础测试先不使用并行
                'chunk_cache_size': 10000,
            }
        )

        return pipeline

    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """生成摘要"""
        summary = {
            "fastest_embedding": None,
            "slowest_embedding": None,
            "avg_files_per_second": 0,
            "recommendations": [],
        }

        embedding_results = {k: v for k, v in results.items() if k.startswith('embedding_') and 'error' not in v}

        if embedding_results:
            # 找到最快和最慢的
            speeds = {k: v['performance']['chunks_per_second'] for k, v in embedding_results.items()}
            summary["fastest_embedding"] = max(speeds, key=speeds.get) if speeds else None
            summary["slowest_embedding"] = min(speeds, key=speeds.get) if speeds else None

            # 平均性能
            avg_throughput = statistics.mean(speeds.values()) if speeds else 0
            summary["avg_files_per_second"] = statistics.mean(
                v['performance']['files_per_second'] for v in embedding_results.values()
            )

            # 生成建议
            if avg_throughput < 100:
                summary["recommendations"].append("索引速度较低，建议启用并行嵌入处理")
            if summary["fastest_embedding"] and 'hash' not in summary["fastest_embedding"]:
                summary["recommendations"].append("考虑使用哈希嵌入进行快速原型开发")

        return summary


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="索引器性能基准测试")
    parser.add_argument(
        "--test-project",
        type=str,
        default="",
        help="测试项目路径"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="benchmark_results.json",
        help="结果输出路径"
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="测试运行次数"
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=["hash", "bge-small"],
        help="要测试的嵌入模型"
    )

    args = parser.parse_args()

    config = BenchmarkConfig(
        test_project_path=args.test_project,
        num_runs=args.runs,
        embedding_models=args.models,
    )

    benchmark = IndexerBenchmark(config)
    results = benchmark.run_all_benchmarks()

    # 保存结果
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print("基准测试完成")
    print(f"{'='*60}")
    print(f"结果已保存到：{args.output}")
    print(f"\n摘要:")
    print(f"  平均文件/秒：{results['summary']['avg_files_per_second']:.2f}")
    print(f"  最快嵌入模型：{results['summary']['fastest_embedding']}")
    if results['summary']['recommendations']:
        print(f"\n建议:")
        for rec in results['summary']['recommendations']:
            print(f"  - {rec}")


if __name__ == "__main__":
    main()
