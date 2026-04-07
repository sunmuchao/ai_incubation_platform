"""
嵌入模型基准测试

评估不同嵌入模型在代码理解场景下的性能表现。
支持多种模型的对比测试，包括：
- BGE 系列 (BGE-base, BGE-large-code, BGE-m3)
- Sentence Transformers 系列
- 哈希嵌入 (基线)

基准测试指标：
1. 嵌入生成速度 (tokens/秒)
2. 检索召回率 (Recall@K)
3. 检索精度 (Precision@K)
4. 语义相似度准确性
5. 内存占用
"""
import os
import sys
import time
import hashlib
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import json

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@dataclass
class BenchmarkConfig:
    """基准测试配置"""
    model_name: str
    test_dataset: str
    batch_size: int = 32
    num_trials: int = 3
    recall_k: List[int] = field(default_factory=lambda: [5, 10, 20])
    max_samples: int = 100


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    model_name: str
    timestamp: str
    config: BenchmarkConfig

    # 性能指标
    embedding_speed: float = 0.0  # tokens/秒
    avg_latency_ms: float = 0.0  # 平均延迟 (毫秒)

    # 检索质量指标
    recall_at_k: Dict[int, float] = field(default_factory=dict)
    precision_at_k: Dict[int, float] = field(default_factory=dict)
    ndcg_at_k: Dict[int, float] = field(default_factory=dict)

    # 资源指标
    memory_usage_mb: float = 0.0
    model_size_mb: float = 0.0

    # 语义准确性
    semantic_accuracy: float = 0.0

    # 总体评分
    overall_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "model_name": self.model_name,
            "timestamp": self.timestamp,
            "config": {
                "model_name": self.config.model_name,
                "test_dataset": self.config.test_dataset,
                "batch_size": self.config.batch_size,
                "num_trials": self.config.num_trials,
            },
            "performance": {
                "embedding_speed": self.embedding_speed,
                "avg_latency_ms": self.avg_latency_ms,
            },
            "retrieval": {
                "recall_at_k": self.recall_at_k,
                "precision_at_k": self.precision_at_k,
                "ndcg_at_k": self.ndcg_at_k,
            },
            "resources": {
                "memory_usage_mb": self.memory_usage_mb,
                "model_size_mb": self.model_size_mb,
            },
            "accuracy": {
                "semantic_accuracy": self.semantic_accuracy,
            },
            "overall_score": self.overall_score,
        }


class EmbeddingBenchmark:
    """
    嵌入模型基准测试器

    评估不同嵌入模型在代码理解场景下的性能表现。
    """

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.results: List[BenchmarkResult] = []
        self._test_corpus: List[str] = []
        self._test_queries: List[Tuple[str, List[int]]] = []  # (query, relevant_indices)

    def load_test_dataset(self, dataset_path: str) -> None:
        """
        加载测试数据集

        数据集格式：JSONL，每行包含：
        {
            "text": "代码片段或文档",
            "query": "相关查询",  # 可选
            "relevant": [相关文档索引列表]  # 可选
        }
        """
        print(f"加载测试数据集：{dataset_path}")
        # TODO: 实现数据集加载
        # 目前使用示例数据
        self._test_corpus = [
            "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
            "class UserService: 用户服务类，处理用户认证和授权",
            "SELECT * FROM users WHERE id = ?",
            "async def fetch_data(url): async with aiohttp.ClientSession() as session: ...",
            "#include <iostream> int main() { std::cout << 'Hello World'; return 0; }",
            "const express = require('express'); const app = express();",
            "docker run -d --name my-container my-image",
            "kubectl apply -f deployment.yaml",
            "terraform init && terraform apply",
            "npm install --save-dev typescript @types/node",
        ]
        self._test_queries = [
            ("递归函数实现", [0]),
            ("用户认证服务", [1]),
            ("数据库查询用户", [2]),
            ("异步 HTTP 请求", [3]),
            ("C++ Hello World", [4]),
            ("Express 框架初始化", [5]),
            ("Docker 容器运行", [6]),
            ("Kubernetes 部署", [7]),
            ("Terraform 初始化", [8]),
            ("npm 安装依赖", [9]),
        ]
        print(f"加载完成：{len(self._test_corpus)} 个文档，{len(self._test_queries)} 个查询")

    def _get_embedder(self, model_name: str):
        """获取嵌入模型"""
        if model_name == "hash":
            return HashEmbedder()
        elif model_name == "bge-base":
            return BGEBaseEmbedder()
        elif model_name == "bge-large-code":
            return BGELargeCodeEmbedder()
        elif model_name == "bge-m3":
            return BGEM3Embedder()
        else:
            raise ValueError(f"未知的模型：{model_name}")

    def benchmark_speed(self, embedder) -> Tuple[float, float]:
        """
        基准测试嵌入生成速度

        Returns:
            (tokens_per_second, avg_latency_ms)
        """
        print(f"  测试嵌入生成速度...")
        total_tokens = 0
        total_time = 0.0
        latencies = []

        for trial in range(self.config.num_trials):
            start_time = time.time()
            for text in self._test_corpus:
                token_count = len(text) // 4  # 估算 token 数
                total_tokens += token_count

                emb_start = time.time()
                embedding = embedder.encode(text)
                emb_end = time.time()
                latencies.append((emb_end - emb_start) * 1000)  # ms

            end_time = time.time()
            total_time += (end_time - start_time)

        tokens_per_second = total_tokens / total_time if total_time > 0 else 0
        avg_latency = statistics.mean(latencies) if latencies else 0

        print(f"    Tokens/秒：{tokens_per_second:.2f}")
        print(f"    平均延迟：{avg_latency:.2f}ms")

        return tokens_per_second, avg_latency

    def benchmark_retrieval(self, embedder) -> Dict[int, Tuple[float, float]]:
        """
        基准测试检索质量

        Returns:
            {k: (recall_at_k, precision_at_k)}
        """
        print(f"  测试检索质量...")

        # 构建索引
        print("    构建索引...")
        corpus_embeddings = []
        for text in self._test_corpus:
            embedding = embedder.encode(text)
            corpus_embeddings.append(embedding)

        results = {}
        for k in self.config.recall_k:
            recalls = []
            precisions = []

            for query_text, relevant_indices in self._test_queries:
                query_embedding = embedder.encode(query_text)

                # 计算相似度
                similarities = []
                for i, corpus_emb in enumerate(corpus_embeddings):
                    sim = self._cosine_similarity(query_embedding, corpus_emb)
                    similarities.append((i, sim))

                # 排序取 top-k
                similarities.sort(key=lambda x: x[1], reverse=True)
                top_k_indices = [idx for idx, _ in similarities[:k]]

                # 计算召回率和精度
                relevant_set = set(relevant_indices)
                retrieved_set = set(top_k_indices)

                if len(relevant_set) > 0:
                    recall = len(relevant_set & retrieved_set) / len(relevant_set)
                    recalls.append(recall)

                if len(retrieved_set) > 0:
                    precision = len(relevant_set & retrieved_set) / len(retrieved_set)
                    precisions.append(precision)

            avg_recall = statistics.mean(recalls) if recalls else 0
            avg_precision = statistics.mean(precisions) if precisions else 0

            results[k] = (avg_recall, avg_precision)
            print(f"    Recall@{k}: {avg_recall:.4f}, Precision@{k}: {avg_precision:.4f}")

        return results

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """计算余弦相似度"""
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def benchmark_semantic_accuracy(self, embedder) -> float:
        """
        基准测试语义准确性

        测试相似代码片段的嵌入是否接近，不同代码的嵌入是否远离。

        Returns:
            准确性得分 (0-1)
        """
        print(f"  测试语义准确性...")

        # 语义相似对
        similar_pairs = [
            ("def add(a, b): return a + b", "def sum(x, y): return x + y"),
            ("SELECT * FROM users", "SELECT * FROM orders"),
            ("npm install", "pip install"),
        ]

        # 语义不同对
        different_pairs = [
            ("def add(a, b): return a + b", "class Database: pass"),
            ("SELECT * FROM users", "docker run nginx"),
            ("npm install", "kubectl apply -f deployment.yaml"),
        ]

        similar_scores = []
        different_scores = []

        for text1, text2 in similar_pairs:
            emb1 = embedder.encode(text1)
            emb2 = embedder.encode(text2)
            sim = self._cosine_similarity(emb1, emb2)
            similar_scores.append(sim)

        for text1, text2 in different_pairs:
            emb1 = embedder.encode(text1)
            emb2 = embedder.encode(text2)
            sim = self._cosine_similarity(emb1, emb2)
            different_scores.append(sim)

        avg_similar = statistics.mean(similar_scores) if similar_scores else 0
        avg_different = statistics.mean(different_scores) if different_scores else 0

        # 准确性：相似对得分高，不同对得分低
        # 简单评分：similar - different 的差值
        accuracy = (avg_similar - avg_different + 1) / 2  # 归一化到 0-1
        accuracy = max(0, min(1, accuracy))

        print(f"    相似对平均得分：{avg_similar:.4f}")
        print(f"    不同对平均得分：{avg_different:.4f}")
        print(f"    语义准确性：{accuracy:.4f}")

        return accuracy

    def run_benchmark(self, model_name: str) -> BenchmarkResult:
        """
        运行完整基准测试

        Args:
            model_name: 模型名称 (hash, bge-base, bge-large-code, bge-m3)

        Returns:
            基准测试结果
        """
        print(f"\n{'='*60}")
        print(f"基准测试：{model_name}")
        print(f"{'='*60}")

        embedder = self._get_embedder(model_name)

        # 速度测试
        speed, latency = self.benchmark_speed(embedder)

        # 检索质量测试
        retrieval_results = self.benchmark_retrieval(embedder)

        # 语义准确性测试
        semantic_accuracy = self.benchmark_semantic_accuracy(embedder)

        # 计算总体评分 (加权平均)
        # 速度权重 30%, 检索质量 40%, 语义准确性 30%
        recall_scores = [v[0] for v in retrieval_results.values()]
        precision_scores = [v[1] for v in retrieval_results.values()]

        avg_recall = statistics.mean(recall_scores) if recall_scores else 0
        avg_precision = statistics.mean(precision_scores) if precision_scores else 0

        # 归一化速度得分 (假设 1000 tokens/s 为满分)
        speed_score = min(1.0, speed / 1000)

        overall_score = (
            speed_score * 0.3 +
            avg_recall * 0.4 +
            semantic_accuracy * 0.3
        )

        result = BenchmarkResult(
            model_name=model_name,
            timestamp=datetime.now().isoformat(),
            config=self.config,
            embedding_speed=speed,
            avg_latency_ms=latency,
            recall_at_k={k: v[0] for k, v in retrieval_results.items()},
            precision_at_k={k: v[1] for k, v in retrieval_results.items()},
            semantic_accuracy=semantic_accuracy,
            overall_score=overall_score,
        )

        self.results.append(result)
        return result

    def generate_report(self, output_path: str = "benchmark_report.json") -> Dict:
        """
        生成基准测试报告

        Args:
            output_path: 报告输出路径

        Returns:
            报告字典
        """
        report = {
            "generated_at": datetime.now().isoformat(),
            "config": {
                "test_dataset": self.config.test_dataset,
                "batch_size": self.config.batch_size,
                "num_trials": self.config.num_trials,
            },
            "models_tested": len(self.results),
            "results": [r.to_dict() for r in self.results],
            "ranking": sorted(
                [r.to_dict() for r in self.results],
                key=lambda x: x["overall_score"],
                reverse=True
            ),
        }

        # 保存报告
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n报告已保存到：{output_path}")
        return report


# ============= 嵌入模型实现 =============

class HashEmbedder:
    """哈希嵌入（基线模型）"""

    def encode(self, text: str) -> List[float]:
        """生成哈希嵌入"""
        hash_bytes = hashlib.sha256(text.encode()).digest()
        # 转换为 256 维向量
        return [b / 255.0 for b in hash_bytes]


class BGEBaseEmbedder:
    """BGE-base 嵌入模型"""

    def __init__(self):
        self._model = None
        self._tokenizer = None

    def _load_model(self):
        """懒加载模型"""
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer('BAAI/bge-base-zh-v1.5')
        except ImportError:
            print("警告：sentence-transformers 未安装，使用哈希嵌入降级")
            self._model = HashEmbedder()

    def encode(self, text: str) -> List[float]:
        """生成嵌入"""
        if self._model is None:
            self._load_model()

        if isinstance(self._model, HashEmbedder):
            return self._model.encode(text)

        try:
            embedding = self._model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            print(f"嵌入生成失败：{e}，使用哈希嵌入降级")
            return HashEmbedder().encode(text)


class BGELargeCodeEmbedder:
    """BGE-large-code 嵌入模型（专为代码优化）"""

    def __init__(self):
        self._model = None

    def _load_model(self):
        """懒加载模型"""
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer('BAAI/bge-large-code-v1.5')
        except ImportError:
            print("警告：sentence-transformers 未安装，使用哈希嵌入降级")
            self._model = HashEmbedder()

    def encode(self, text: str) -> List[float]:
        """生成嵌入"""
        if self._model is None:
            self._load_model()

        if isinstance(self._model, HashEmbedder):
            return self._model.encode(text)

        try:
            embedding = self._model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            print(f"嵌入生成失败：{e}，使用哈希嵌入降级")
            return HashEmbedder().encode(text)


class BGEM3Embedder:
    """BGE-m3 嵌入模型（多语言、多功能）"""

    def __init__(self):
        self._model = None

    def _load_model(self):
        """懒加载模型"""
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer('BAAI/bge-m3')
        except ImportError:
            print("警告：sentence-transformers 未安装，使用哈希嵌入降级")
            self._model = HashEmbedder()

    def encode(self, text: str) -> List[float]:
        """生成嵌入"""
        if self._model is None:
            self._load_model()

        if isinstance(self._model, HashEmbedder):
            return self._model.encode(text)

        try:
            embedding = self._model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            print(f"嵌入生成失败：{e}，使用哈希嵌入降级")
            return HashEmbedder().encode(text)


# ============= 命令行入口 =============

def main():
    """运行基准测试"""
    import argparse

    parser = argparse.ArgumentParser(description="嵌入模型基准测试")
    parser.add_argument(
        "--models",
        nargs="+",
        default=["hash", "bge-base"],
        help="要测试的模型列表"
    )
    parser.add_argument(
        "--output",
        default="benchmark_report.json",
        help="报告输出路径"
    )
    parser.add_argument(
        "--dataset",
        default="sample",
        help="测试数据集路径"
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=3,
        help="测试次数"
    )

    args = parser.parse_args()

    config = BenchmarkConfig(
        model_name=args.models[0],
        test_dataset=args.dataset,
        num_trials=args.trials,
    )

    benchmark = EmbeddingBenchmark(config)
    benchmark.load_test_dataset(args.dataset)

    for model in args.models:
        benchmark.run_benchmark(model)

    benchmark.generate_report(args.output)

    # 打印排名
    print("\n" + "=" * 60)
    print("模型排名")
    print("=" * 60)
    for i, result in enumerate(sorted(benchmark.results, key=lambda x: x.overall_score, reverse=True), 1):
        print(f"{i}. {result.model_name}: {result.overall_score:.4f}")


if __name__ == "__main__":
    main()
