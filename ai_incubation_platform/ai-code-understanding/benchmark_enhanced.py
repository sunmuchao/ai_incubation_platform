"""
增强版性能基准测试脚本 - 使用模拟嵌入（无需网络）
测试 OPT-1 到 OPT-6 所有优化策略的综合效果
"""
import os
import sys
import time
import json
import tempfile
import shutil
import random
import hashlib
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from src.core.indexer.base import CodeChunk, BaseEmbedding
from src.core.indexer.pipeline import IndexPipeline
from src.core.indexer.pipeline_enhanced import EnhancedIndexPipeline
from src.core.indexer.parsers.tree_sitter_parser import TreeSitterParser
from src.core.indexer.vector_stores.chroma_store import ChromaVectorStore


class MockEmbedding(BaseEmbedding):
    """模拟嵌入（用于基准测试，无需网络）"""
    def __init__(self, config=None):
        self.config = config or {}
        self.dimension = self.config.get('dimension', 384)

    def get_dimension(self) -> int:
        return self.dimension

    def encode_text(self, text: str) -> List[float]:
        # 基于内容哈希生成固定向量
        h = hashlib.md5(text.encode()).hexdigest()
        return [((ord(c) % 256) - 128) / 128.0 for c in h[:self.dimension]]

    def encode_chunks(self, chunks: List[CodeChunk]) -> List[CodeChunk]:
        for chunk in chunks:
            h = hashlib.md5(chunk.content.encode()).hexdigest()
            chunk.embedding = [((ord(c) % 256) - 128) / 128.0 for c in h[:self.dimension]]
        return chunks


def generate_test_files(output_dir: str, num_files: int = 100, lines_per_file: int = 50) -> List[str]:
    """生成测试文件"""
    os.makedirs(output_dir, exist_ok=True)
    files = []
    for i in range(num_files):
        file_path = os.path.join(output_dir, f"test_file_{i:04d}.py")
        with open(file_path, 'w') as f:
            f.write(f'"""\n测试文件 {i}\n"""\n\n')
            f.write('import os\nimport sys\nimport json\n\n')
            for j in range(lines_per_file // 5):
                f.write(f'def function_{i}_{j}(arg1, arg2):\n')
                f.write(f'    result = arg1 + arg2\n')
                f.write(f'    return result\n\n')
            f.write(f'class TestClass_{i}:\n')
            f.write(f'    def __init__(self, value):\n')
            f.write(f'        self.value = value\n\n')
        files.append(file_path)
    return files


def run_benchmark(pipeline, test_dir: str, collection: str, name: str, use_enhanced: bool = False) -> Dict[str, Any]:
    """运行基准测试"""
    print(f"\n{'='*60}")
    print(f"运行测试：{name}")
    print(f"{'='*60}")

    files = list(Path(test_dir).glob('*.py'))
    print(f"测试文件数：{len(files)}")

    start_time = time.time()

    if use_enhanced:
        stats = pipeline.index_directory(dir_path=test_dir, collection=collection)
    else:
        stats = pipeline.index_directory(dir_path=test_dir, collection_name=collection)

    elapsed = time.time() - start_time

    print(f"\n{name} 测试结果:")
    print(f"  总耗时：{elapsed:.2f}秒")
    print(f"  索引文件数：{stats.get('indexed_files', 0)}")
    print(f"  文件/秒：{stats.get('files_per_second', 0):.2f}")
    print(f"  chunk/秒：{stats.get('chunks_per_second', 0):.2f}")

    if 'cache_stats' in stats:
        print(f"  缓存命中率：{stats['cache_stats'].get('hit_rate', 0):.2f}%")

    return {
        'name': name,
        'elapsed_seconds': elapsed,
        'indexed_files': stats.get('indexed_files', 0),
        'total_chunks': stats.get('total_chunks', 0),
        'files_per_second': stats.get('files_per_second', 0),
        'chunks_per_second': stats.get('chunks_per_second', 0),
        'cache_stats': stats.get('cache_stats', {})
    }


def main():
    print("="*60)
    print("AI 代码理解平台 - 增强版性能基准测试（模拟嵌入）")
    print("目标：验证 5x 性能提升")
    print("="*60)

    test_base_dir = tempfile.mkdtemp(prefix='perf_test_')
    test_dir = os.path.join(test_base_dir, 'src')

    try:
        print("\n生成测试文件...")
        generate_test_files(test_dir, num_files=100, lines_per_file=50)
        print(f"测试文件生成完成：{test_dir}")

        # 基准测试
        print("\n[1/3] 基准测试（无优化）...")
        baseline_chroma = os.path.join(test_base_dir, 'chroma_baseline')
        parser = TreeSitterParser()
        embedding = MockEmbedding({'dimension': 384})
        vector_store = ChromaVectorStore({'persist_directory': baseline_chroma})
        vector_store.connect({})
        baseline = IndexPipeline(
            parsers=[parser], embedding=embedding, vector_store=vector_store,
            config={'enable_parallel_embedding': False, 'chunk_cache_size': 0, 'default_collection': 'baseline'}
        )
        baseline_result = run_benchmark(baseline, test_dir, 'baseline', '基准测试', use_enhanced=False)

        # 优化测试
        print("\n[2/3] 优化管线测试（全量 OPT-1~6）...")
        optimized_chroma = os.path.join(test_base_dir, 'chroma_optimized')
        vector_store2 = ChromaVectorStore({'persist_directory': optimized_chroma})
        vector_store2.connect({})
        optimized = EnhancedIndexPipeline(
            parsers=[parser], embedding=embedding, vector_store=vector_store2,
            config={'num_workers': 4, 'l1_cache_size': 10000, 'enable_cache': True, 'cache_prewarm': False}
        )
        optimized.initialize()
        optimized_result = run_benchmark(optimized, test_dir, 'optimized', '优化管线', use_enhanced=True)

        # 缓存复用测试
        print("\n[3/3] 缓存复用测试...")
        cached_result = run_benchmark(optimized, test_dir, 'optimized', '缓存复用', use_enhanced=True)

        # 汇总报告
        print("\n" + "="*60)
        print("性能基准测试汇总报告")
        print("="*60)
        print(f"\n【全量索引性能对比】")
        print(f"  基准测试：{baseline_result['files_per_second']:.2f} 文件/秒")
        print(f"  优化管线：{optimized_result['files_per_second']:.2f} 文件/秒")
        speedup = optimized_result['files_per_second'] / baseline_result['files_per_second'] if baseline_result['files_per_second'] > 0 else 0
        print(f"  性能提升：{speedup:.2f}x")

        if 'cache_stats' in cached_result:
            print(f"\n【缓存性能】缓存命中率：{cached_result['cache_stats'].get('hit_rate', 0):.2f}%")

        report = {
            'timestamp': datetime.now().isoformat(),
            'baseline': baseline_result,
            'optimized': optimized_result,
            'cached': cached_result,
            'speedup': speedup
        }
        print(f"\n{'='*60}")
        if speedup >= 5.0:
            print(f"✓ 达到 5x 性能目标！实际提升：{speedup:.2f}x")
        else:
            print(f"○ 未达到 5x 目标，当前提升：{speedup:.2f}x，差距：{5.0 - speedup:.2f}x")
        print("="*60)

        # 保存报告
        report_path = os.path.join(test_base_dir, 'benchmark_report.json')
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n报告已保存到：{report_path}")

        return report

    finally:
        if os.path.exists(test_base_dir):
            shutil.rmtree(test_base_dir)


if __name__ == '__main__':
    main()
