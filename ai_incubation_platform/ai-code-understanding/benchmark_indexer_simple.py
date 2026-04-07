#!/usr/bin/env python3
"""
索引性能基准测试框架 - 简化版本

用于评估和优化代码索引管道的性能，仅使用 Hash Embedding 避免依赖问题。
"""
import os
import sys
import time
import json
import statistics
import argparse
import hashlib
import tempfile
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))


@dataclass
class CodeChunk:
    """代码分块数据结构"""
    file_path: str
    language: str
    content: str
    start_line: int
    end_line: int
    chunk_type: str
    symbols: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class BenchmarkConfig:
    """基准测试配置"""
    test_project_path: str
    num_runs: int = 3
    batch_sizes: List[int] = field(default_factory=lambda: [32, 64, 128])
    enable_parallel: bool = True
    num_workers: int = 4


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    test_name: str
    timestamp: str
    config: Dict[str, Any]

    total_files: int = 0
    total_chunks: int = 0
    total_symbols: int = 0
    total_time_seconds: float = 0.0
    files_per_second: float = 0.0
    chunks_per_second: float = 0.0
    avg_file_time_ms: float = 0.0

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
                "files_per_second": self.files_per_second,
                "chunks_per_second": self.chunks_per_second,
                "avg_file_time_ms": self.avg_file_time_ms,
            }
        }


class SimpleHashEmbedding:
    """简化版 Hash Embedding，不依赖 numpy"""

    def __init__(self, dimension: int = 512):
        self.dimension = dimension
        self.normalize = True

    def get_dimension(self) -> int:
        return self.dimension

    def encode_text(self, text: str) -> List[float]:
        vec = [0.0] * self.dimension
        if not text:
            return vec

        # 简单 token 化
        tokens = text.lower().split()
        for token in tokens:
            h = hashlib.md5(token.encode("utf-8")).hexdigest()
            idx = int(h, 16) % self.dimension
            vec[idx] += 1.0

        # 归一化
        if self.normalize:
            norm = sum(x * x for x in vec) ** 0.5
            if norm > 0:
                vec = [x / norm for x in vec]

        return vec

    def encode_chunks(self, chunks: List[CodeChunk]) -> List[CodeChunk]:
        for chunk in chunks:
            text = f"{chunk.file_path} {' '.join(chunk.symbols)} {chunk.content}"
            chunk.embedding = self.encode_text(text)
        return chunks


class SimpleParser:
    """简化版代码解析器"""

    def __init__(self):
        self.supported_languages = ['python', 'javascript', 'typescript', 'java', 'go', 'rust']

    def supports_language(self, language: str) -> bool:
        return language.lower() in self.supported_languages

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """解析文件，返回分块和符号"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        language = self._detect_language(file_path)
        chunks = self._extract_chunks(content, file_path, language)
        symbols = self._extract_symbols(content, file_path, language)

        return {
            'file_path': file_path,
            'language': language,
            'chunks': chunks,
            'symbols': symbols,
        }

    def _detect_language(self, file_path: str) -> str:
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
        }
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, 'unknown')

    def _extract_chunks(self, content: str, file_path: str, language: str) -> List[CodeChunk]:
        """提取代码分块"""
        chunks = []
        lines = content.split('\n')

        current_chunk_start = 0
        current_chunk_content = []
        current_symbols = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # 检测函数/类定义
            is_definition = any(
                stripped.startswith(kw) for kw in
                ['def ', 'class ', 'func ', 'function ', 'const ', 'let ', 'var ', 'interface ']
            )

            if is_definition and current_chunk_content:
                # 保存之前的分块
                chunk = CodeChunk(
                    file_path=file_path,
                    language=language,
                    content='\n'.join(current_chunk_content),
                    start_line=current_chunk_start,
                    end_line=i - 1,
                    chunk_type='function' if 'def ' in stripped or 'function ' in stripped else 'class',
                    symbols=current_symbols.copy(),
                )
                chunks.append(chunk)
                current_chunk_content = []
                current_symbols = []
                current_chunk_start = i

            current_chunk_content.append(line)

            # 提取符号名
            if stripped.startswith('def '):
                match = stripped[4:].split('(')[0].strip()
                if match:
                    current_symbols.append(match)
            elif stripped.startswith('class '):
                match = stripped[6:].split('(')[0].strip()
                match = match.split(':')[0].strip()
                if match:
                    current_symbols.append(match)

        # 添加最后一个分块
        if current_chunk_content:
            chunk = CodeChunk(
                file_path=file_path,
                language=language,
                content='\n'.join(current_chunk_content),
                start_line=current_chunk_start,
                end_line=len(lines),
                chunk_type='module',
                symbols=current_symbols,
            )
            chunks.append(chunk)

        return chunks

    def _extract_symbols(self, content: str, file_path: str, language: str) -> List[Dict[str, Any]]:
        """提取符号列表"""
        symbols = []
        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            if stripped.startswith('def '):
                name = stripped[4:].split('(')[0].strip()
                symbols.append({
                    'name': name,
                    'type': 'function',
                    'line': i,
                })
            elif stripped.startswith('class '):
                name = stripped[6:].split('(')[0].strip().split(':')[0].strip()
                symbols.append({
                    'name': name,
                    'type': 'class',
                    'line': i,
                })

        return symbols


class SimpleVectorStore:
    """简化版向量存储（内存）"""

    def __init__(self):
        self.collections: Dict[str, List[CodeChunk]] = {}

    def connect(self, config: Dict[str, Any]) -> None:
        pass

    def create_collection(self, name: str, dimension: int) -> None:
        if name not in self.collections:
            self.collections[name] = []

    def upsert_chunks(self, collection_name: str, chunks: List[CodeChunk]) -> int:
        if collection_name not in self.collections:
            self.collections[collection_name] = []
        self.collections[collection_name].extend(chunks)
        return len(chunks)

    def search(self, collection_name: str, query_embedding: List[float], top_k: int = 10) -> List[CodeChunk]:
        return []


class IndexPipeline:
    """简化版索引管线"""

    def __init__(self, embedding, parser, vector_store, config: Dict[str, Any] = None):
        self.embedding = embedding
        self.parser = parser
        self.vector_store = vector_store
        self.config = config or {}
        self.default_collection = 'code_index'
        self.batch_size = self.config.get('batch_size', 64)
        self.enable_parallel = self.config.get('enable_parallel', False)
        self.num_workers = self.config.get('num_workers', 4)
        self.vector_store.create_collection(self.default_collection, embedding.get_dimension())

    def index_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """索引单个文件"""
        try:
            result = self.parser.parse_file(file_path)
            chunks_with_embedding = self.embedding.encode_chunks(result['chunks'])
            self.vector_store.upsert_chunks(self.default_collection, chunks_with_embedding)
            return result
        except Exception as e:
            return None

    def index_directory(self, dir_path: Path) -> Dict[str, Any]:
        """索引目录"""
        files = list(dir_path.glob("**/*.py"))

        stats = {
            'total_files': len(files),
            'success_files': 0,
            'failed_files': 0,
            'total_chunks': 0,
            'total_symbols': 0,
        }

        if self.enable_parallel:
            # 并行模式
            with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                futures = {executor.submit(self.index_file, str(f)): f for f in files}
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        stats['success_files'] += 1
                        stats['total_chunks'] += len(result['chunks'])
                        stats['total_symbols'] += len(result['symbols'])
                    else:
                        stats['failed_files'] += 1
        else:
            # 串行模式
            for file_path in files:
                result = self.index_file(str(file_path))
                if result:
                    stats['success_files'] += 1
                    stats['total_chunks'] += len(result['chunks'])
                    stats['total_symbols'] += len(result['symbols'])
                else:
                    stats['failed_files'] += 1

        return stats


class IndexerBenchmark:
    """索引器基准测试器"""

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.results: List[BenchmarkResult] = []

    def setup_test_project(self) -> Path:
        """准备测试项目"""
        if self.config.test_project_path and os.path.exists(self.config.test_project_path):
            return Path(self.config.test_project_path)

        test_dir = Path(tempfile.mkdtemp(prefix="benchmark_test_"))
        self._create_sample_project(test_dir)
        return test_dir

    def _create_sample_project(self, base_dir: Path) -> None:
        """创建示例项目"""
        (base_dir / "src").mkdir(parents=True, exist_ok=True)
        (base_dir / "tests").mkdir(parents=True, exist_ok=True)

        # 生成 50 个 Python 文件
        for i in range(50):
            file_path = base_dir / "src" / f"module_{i}.py"
            self._generate_sample_python_file(file_path, i)

        # 生成 20 个测试文件
        for i in range(20):
            file_path = base_dir / "tests" / f"test_{i}.py"
            self._generate_sample_python_file(file_path, i, is_test=True)

    def _generate_sample_python_file(self, path: Path, index: int, is_test: bool = False) -> None:
        content = f'''"""
Module {index} - Sample code
"""
from typing import List, Dict, Optional


class SampleClass{index}:
    """Sample class"""

    def __init__(self, name: str, value: int = 0):
        self.name = name
        self.value = value

    def process(self, items: List[int]) -> Dict[str, int]:
        result = {{}}
        for i, item in enumerate(items):
            result[f"item_{{i}}"] = item * self.value
        return result

    def validate(self) -> bool:
        return self.value > 0


def function_alpha_{index}(data: List[float], threshold: float = 0.5) -> List[float]:
    """Filter data by threshold"""
    return [x for x in data if x > threshold]


def function_beta_{index}(items: List[str]) -> Dict[str, str]:
    """Transform items"""
    return {{f"key_{{i}}": item.upper() for i, item in enumerate(items)}}


async def async_function_{index}(url: str) -> Dict:
    """Async function"""
    return {{"url": url, "status": "ok"}}

'''
        if is_test:
            content += f'''
def test_function_{index}():
    """Test function"""
    assert True

'''
        path.write_text(content, encoding='utf-8')

    def cleanup_test_project(self, test_dir: Path) -> None:
        """清理测试项目"""
        if test_dir and self.config.test_project_path == "":
            shutil.rmtree(test_dir, ignore_errors=True)

    def run_benchmark(self, enable_parallel: bool = False, num_workers: int = 4) -> BenchmarkResult:
        """运行基准测试"""
        test_dir = self.setup_test_project()
        print(f"测试项目：{test_dir}")
        print(f"文件数量：{len(list(test_dir.glob('**/*.py')))}")

        # 创建组件
        embedding = SimpleHashEmbedding(dimension=512)
        parser = SimpleParser()
        vector_store = SimpleVectorStore()

        # 创建 pipeline
        pipeline = IndexPipeline(
            embedding=embedding,
            parser=parser,
            vector_store=vector_store,
            config={
                'batch_size': 64,
                'enable_parallel': enable_parallel,
                'num_workers': num_workers,
            }
        )

        # 运行测试
        start_time = time.time()

        files = list(test_dir.glob("**/*.py"))
        stats = pipeline.index_directory(test_dir)

        total_time = time.time() - start_time

        result = BenchmarkResult(
            test_name="parallel_benchmark" if enable_parallel else "serial_benchmark",
            timestamp=datetime.now().isoformat(),
            config={
                "enable_parallel": enable_parallel,
                "num_workers": num_workers,
            },
            total_files=stats['success_files'],
            total_chunks=stats['total_chunks'],
            total_symbols=stats['total_symbols'],
            total_time_seconds=total_time,
            files_per_second=stats['success_files'] / max(total_time, 0.001),
            chunks_per_second=stats['total_chunks'] / max(total_time, 0.001),
            avg_file_time_ms=(total_time / max(stats['success_files'], 1)) * 1000,
        )

        self.results.append(result)
        self.cleanup_test_project(test_dir)

        return result

    def run_all_benchmarks(self) -> Dict[str, Any]:
        """运行所有基准测试"""
        results = {}

        # 串行基准
        print("\n" + "=" * 60)
        print("测试 1: 串行索引")
        print("=" * 60)
        serial_result = self.run_benchmark(enable_parallel=False)
        results['serial'] = serial_result.to_dict()
        print(f"  文件/秒：{serial_result.files_per_second:.2f}")
        print(f"  分块/秒：{serial_result.chunks_per_second:.2f}")

        # 并行基准
        print("\n" + "=" * 60)
        print("测试 2: 并行索引 (4 workers)")
        print("=" * 60)
        parallel_result = self.run_benchmark(enable_parallel=True, num_workers=4)
        results['parallel_4'] = parallel_result.to_dict()
        print(f"  文件/秒：{parallel_result.files_per_second:.2f}")
        print(f"  分块/秒：{parallel_result.chunks_per_second:.2f}")

        # 计算加速比
        speedup = parallel_result.total_time_seconds / max(serial_result.total_time_seconds, 0.001)

        return {
            "generated_at": datetime.now().isoformat(),
            "results": results,
            "summary": {
                "serial_files_per_second": serial_result.files_per_second,
                "parallel_files_per_second": parallel_result.files_per_second,
                "speedup_ratio": speedup,
                "recommendations": self._generate_recommendations(serial_result, parallel_result),
            }
        }

    def _generate_recommendations(self, serial: BenchmarkResult, parallel: BenchmarkResult) -> List[str]:
        """生成优化建议"""
        recommendations = []

        speedup = parallel.total_time_seconds / max(serial.total_time_seconds, 0.001)
        if speedup < 0.8:
            recommendations.append("并行处理带来显著加速，建议在生产环境使用")
        elif speedup < 1.0:
            recommendations.append("并行处理有轻微加速，可考虑调整 worker 数量优化")
        else:
            recommendations.append("并行处理未带来加速，可能由于：1) 任务本身较轻量 2) I/O 瓶颈 3) 锁竞争")

        if serial.chunks_per_second < 100:
            recommendations.append("索引速度较低，建议：1) 使用更快的 embedding 模型 2) 优化解析器性能")

        return recommendations


def main():
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
        default=1,
        help="测试运行次数"
    )

    args = parser.parse_args()

    config = BenchmarkConfig(
        test_project_path=args.test_project,
        num_runs=args.runs,
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
    print(f"  串行索引速度：{results['summary']['serial_files_per_second']:.2f} 文件/秒")
    print(f"  并行索引速度：{results['summary']['parallel_files_per_second']:.2f} 文件/秒")
    print(f"  加速比：{results['summary']['speedup_ratio']:.2f}x")
    print(f"\n建议:")
    for rec in results['summary']['recommendations']:
        print(f"  - {rec}")


if __name__ == "__main__":
    main()
