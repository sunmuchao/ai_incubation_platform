"""
RAG 效果评估指标

评估检索增强生成 (RAG) 系统在代码理解场景下的性能表现。

评估指标：
1. 检索召回率 (Recall@K)
2. 检索精度 (Precision@K)
3. NDCG (Normalized Discounted Cumulative Gain)
4. MRR (Mean Reciprocal Rank)
5. 答案相关性 (Answer Relevance)
6. 上下文利用率 (Context Utilization)
7. 幻觉检测率 (Hallucination Detection Rate)
"""
import os
import sys
import json
import time
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict


@dataclass
class EvaluationQuery:
    """评估查询"""
    query: str
    relevant_docs: List[int]  # 相关文档索引
    expected_answer: Optional[str] = None  # 期望的答案（可选）


@dataclass
class RetrievalResult:
    """检索结果"""
    query: str
    retrieved_docs: List[int]  # 检索到的文档索引
    scores: List[float]  # 每个文档的得分
    latency_ms: float  # 检索延迟


@dataclass
class EvaluationResult:
    """评估结果"""
    timestamp: str
    total_queries: int

    # 检索指标
    recall_at_k: Dict[int, float] = field(default_factory=dict)
    precision_at_k: Dict[int, float] = field(default_factory=dict)
    ndcg_at_k: Dict[int, float] = field(default_factory=dict)
    mrr: float = 0.0
    map_score: float = 0.0  # Mean Average Precision

    # 延迟指标
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0

    # 质量指标
    answer_relevance: float = 0.0
    context_utilization: float = 0.0
    hallucination_rate: float = 0.0

    # 总体评分
    overall_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp,
            "total_queries": self.total_queries,
            "retrieval": {
                "recall_at_k": self.recall_at_k,
                "precision_at_k": self.precision_at_k,
                "ndcg_at_k": self.ndcg_at_k,
                "mrr": self.mrr,
                "map_score": self.map_score,
            },
            "latency": {
                "avg_latency_ms": self.avg_latency_ms,
                "p50_latency_ms": self.p50_latency_ms,
                "p95_latency_ms": self.p95_latency_ms,
                "p99_latency_ms": self.p99_latency_ms,
            },
            "quality": {
                "answer_relevance": self.answer_relevance,
                "context_utilization": self.context_utilization,
                "hallucination_rate": self.hallucination_rate,
            },
            "overall_score": self.overall_score,
        }


class RAGEvaluator:
    """
    RAG 效果评估器

    评估检索增强生成系统在代码理解场景下的性能。
    """

    def __init__(self, retriever, generator=None):
        """
        初始化评估器

        Args:
            retriever: 检索器，需要有 search(query, top_k) 方法
            generator: 生成器（可选），需要有 generate(query, context) 方法
        """
        self.retriever = retriever
        self.generator = generator
        self.results: List[EvaluationResult] = []

    def load_evaluation_queries(self, queries: List[EvaluationQuery]) -> None:
        """加载评估查询集"""
        self.queries = queries
        print(f"加载了 {len(queries)} 个评估查询")

    def _recall_at_k(self, retrieved: List[int], relevant: List[int], k: int) -> float:
        """计算 Recall@K"""
        if not relevant:
            return 0.0
        retrieved_set = set(retrieved[:k])
        relevant_set = set(relevant)
        return len(retrieved_set & relevant_set) / len(relevant_set)

    def _precision_at_k(self, retrieved: List[int], relevant: List[int], k: int) -> float:
        """计算 Precision@K"""
        if k == 0:
            return 0.0
        retrieved_set = set(retrieved[:k])
        relevant_set = set(relevant)
        return len(retrieved_set & relevant_set) / k

    def _dcg_at_k(self, retrieved: List[int], relevant: List[int], k: int) -> float:
        """计算 DCG@K"""
        relevant_set = set(relevant)
        dcg = 0.0
        for i, doc_id in enumerate(retrieved[:k]):
            if doc_id in relevant_set:
                rel = 1.0  # 二元相关性
                dcg += rel / (i + 1)  # log2(i+2) 简化为 i+1
        return dcg

    def _ndcg_at_k(self, retrieved: List[int], relevant: List[int], k: int) -> float:
        """计算 NDCG@K"""
        dcg = self._dcg_at_k(retrieved, relevant, k)

        # 理想 DCG
        ideal_retrieved = relevant[:k]
        idcg = self._dcg_at_k(ideal_retrieved, relevant, k)

        return dcg / idcg if idcg > 0 else 0.0

    def _reciprocal_rank(self, retrieved: List[int], relevant: List[int]) -> float:
        """计算 Reciprocal Rank"""
        relevant_set = set(relevant)
        for i, doc_id in enumerate(retrieved):
            if doc_id in relevant_set:
                return 1.0 / (i + 1)
        return 0.0

    def evaluate_retrieval(self, top_ks: List[int] = None) -> EvaluationResult:
        """
        评估检索性能

        Args:
            top_ks: 要评估的 K 值列表，默认为 [5, 10, 20]

        Returns:
            评估结果
        """
        if top_ks is None:
            top_ks = [5, 10, 20]

        print("\n评估检索性能...")

        recalls = defaultdict(list)
        precisions = defaultdict(list)
        ndcgs = defaultdict(list)
        reciprocal_ranks = []
        latencies = []

        for i, query in enumerate(self.queries):
            start_time = time.time()

            # 执行检索
            try:
                result = self.retriever.search(query.query, top_k=max(top_ks))
                retrieved_docs = result.get('doc_ids', result.get('ids', []))
                if isinstance(retrieved_docs[0], dict):
                    retrieved_docs = [d.get('id', d.get('doc_id')) for d in retrieved_docs]
            except Exception as e:
                print(f"  查询 {i+1} 检索失败：{e}")
                continue

            latency = (time.time() - start_time) * 1000
            latencies.append(latency)

            relevant_docs = query.relevant_docs

            # 计算指标
            for k in top_ks:
                recalls[k].append(self._recall_at_k(retrieved_docs, relevant_docs, k))
                precisions[k].append(self._precision_at_k(retrieved_docs, relevant_docs, k))
                ndcgs[k].append(self._ndcg_at_k(retrieved_docs, relevant_docs, k))

            reciprocal_ranks.append(self._reciprocal_rank(retrieved_docs, relevant_docs))

            if (i + 1) % 10 == 0:
                print(f"  已完成 {i+1}/{len(self.queries)} 个查询")

        # 计算平均值
        result = EvaluationResult(
            timestamp=datetime.now().isoformat(),
            total_queries=len(self.queries),
            recall_at_k={k: statistics.mean(v) for k, v in recalls.items()},
            precision_at_k={k: statistics.mean(v) for k, v in precisions.items()},
            ndcg_at_k={k: statistics.mean(v) for k, v in ndcgs.items()},
            mrr=statistics.mean(reciprocal_ranks) if reciprocal_ranks else 0.0,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0.0,
            p50_latency_ms=statistics.median(latencies) if latencies else 0.0,
            p95_latency_ms=sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 20 else 0.0,
            p99_latency_ms=sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) > 100 else 0.0,
        )

        # 计算 MAP
        # 简化计算，使用平均 recall 作为近似
        result.map_score = statistics.mean(list(result.recall_at_k.values())) if result.recall_at_k else 0.0

        # 计算总体评分
        # 检索质量 60% + 延迟 40%
        retrieval_score = statistics.mean(list(result.recall_at_k.values()))
        latency_score = max(0, 1 - result.avg_latency_ms / 1000)  # 1000ms 为 0 分
        result.overall_score = retrieval_score * 0.6 + latency_score * 0.4

        self.results.append(result)
        return result

    def evaluate_answer_quality(self, sample_size: int = 20) -> Dict[str, float]:
        """
        评估答案质量（需要生成器）

        Args:
            sample_size: 抽样评估的答案数量

        Returns:
            质量指标字典
        """
        if not self.generator:
            print("警告：未提供生成器，跳过答案质量评估")
            return {}

        print("\n评估答案质量...")

        relevance_scores = []
        context_utilization_scores = []
        hallucination_flags = []

        for i, query in enumerate(self.queries[:sample_size]):
            # 检索上下文
            try:
                retrieval_result = self.retriever.search(query.query, top_k=5)
                context = retrieval_result.get('context', '')
            except Exception as e:
                print(f"  查询 {i+1} 检索失败：{e}")
                continue

            # 生成答案
            try:
                answer = self.generator.generate(query.query, context)
            except Exception as e:
                print(f"  查询 {i+1} 生成失败：{e}")
                continue

            # 评估答案相关性（简化版，实际应该用 LLM 评估）
            relevance = self._estimate_answer_relevance(answer, query.expected_answer)
            relevance_scores.append(relevance)

            # 评估上下文利用率
            context_util = self._estimate_context_utilization(answer, context)
            context_utilization_scores.append(context_util)

            # 检测幻觉
            is_hallucination = self._detect_hallucination(answer, context)
            hallucination_flags.append(is_hallucination)

            if (i + 1) % 5 == 0:
                print(f"  已完成 {i+1}/{min(sample_size, len(self.queries))} 个答案评估")

        return {
            "answer_relevance": statistics.mean(relevance_scores) if relevance_scores else 0.0,
            "context_utilization": statistics.mean(context_utilization_scores) if context_utilization_scores else 0.0,
            "hallucination_rate": sum(hallucination_flags) / len(hallucination_flags) if hallucination_flags else 0.0,
        }

    def _estimate_answer_relevance(self, answer: str, expected: str) -> float:
        """估算答案相关性（简化版）"""
        if not expected:
            return 0.5  # 无期望答案时返回中等分数

        # 简单的重叠度计算
        answer_words = set(answer.lower().split())
        expected_words = set(expected.lower().split())

        if not answer_words or not expected_words:
            return 0.0

        overlap = len(answer_words & expected_words)
        union = len(answer_words | expected_words)
        return overlap / union if union > 0 else 0.0

    def _estimate_context_utilization(self, answer: str, context: str) -> float:
        """估算上下文利用率"""
        if not context:
            return 0.0

        # 检查答案中的关键词是否来自上下文
        context_words = set(context.lower().split())
        answer_words = answer.lower().split()

        if not answer_words:
            return 0.0

        matched = sum(1 for word in answer_words if word in context_words)
        return matched / len(answer_words)

    def _detect_hallucination(self, answer: str, context: str) -> bool:
        """检测幻觉（简化版）"""
        if not context:
            return True  # 没有上下文时认为是幻觉

        # 检查答案中的关键实体是否在上下文中
        # 简化实现：检查 50% 以上的答案词汇是否在上下文中
        context_words = set(context.lower().split())
        answer_words = [w for w in answer.lower().split() if len(w) > 3]  # 忽略短词

        if not answer_words:
            return False

        matched = sum(1 for word in answer_words if word in context_words)
        match_rate = matched / len(answer_words)

        return match_rate < 0.3  # 匹配率低于 30% 认为是幻觉

    def generate_report(self, output_path: str = "rag_evaluation_report.json") -> Dict:
        """
        生成评估报告

        Args:
            output_path: 报告输出路径

        Returns:
            报告字典
        """
        if not self.results:
            print("警告：没有评估结果")
            return {}

        # 使用最新的结果
        latest_result = self.results[-1]

        report = {
            "generated_at": datetime.now().isoformat(),
            "evaluation_summary": latest_result.to_dict(),
            "all_results": [r.to_dict() for r in self.results],
        }

        # 保存报告
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n报告已保存到：{output_path}")
        return report

    def print_summary(self) -> None:
        """打印评估摘要"""
        if not self.results:
            print("没有评估结果")
            return

        result = self.results[-1]

        print("\n" + "=" * 60)
        print("RAG 评估摘要")
        print("=" * 60)

        print(f"\n查询总数：{result.total_queries}")

        print("\n检索质量:")
        for k, v in result.recall_at_k.items():
            print(f"  Recall@{k}: {v:.4f}")
        for k, v in result.precision_at_k.items():
            print(f"  Precision@{k}: {v:.4f}")
        for k, v in result.ndcg_at_k.items():
            print(f"  NDCG@{k}: {v:.4f}")
        print(f"  MRR: {result.mrr:.4f}")
        print(f"  MAP: {result.map_score:.4f}")

        print("\n延迟指标:")
        print(f"  平均延迟：{result.avg_latency_ms:.2f}ms")
        print(f"  P50 延迟：{result.p50_latency_ms:.2f}ms")
        print(f"  P95 延迟：{result.p95_latency_ms:.2f}ms")
        print(f"  P99 延迟：{result.p99_latency_ms:.2f}ms")

        print("\n答案质量:")
        print(f"  答案相关性：{result.answer_relevance:.4f}")
        print(f"  上下文利用率：{result.context_utilization:.4f}")
        print(f"  幻觉检测率：{result.hallucination_rate:.4f}")

        print(f"\n总体评分：{result.overall_score:.4f}")
        print("=" * 60)


# ============= 示例检索器 =============

class MockRetriever:
    """模拟检索器（用于测试）"""

    def __init__(self, corpus: List[str]):
        self.corpus = corpus
        self._index = {}
        for i, doc in enumerate(corpus):
            self._index[i] = doc.lower()

    def search(self, query: str, top_k: int = 10) -> Dict:
        """模拟检索"""
        query_lower = query.lower()

        # 简单的关键词匹配
        scores = []
        for i, doc in self._index.items():
            # 计算重叠词数
            query_words = set(query_lower.split())
            doc_words = set(doc.split())
            overlap = len(query_words & doc_words)
            scores.append((i, overlap))

        # 排序
        scores.sort(key=lambda x: x[1], reverse=True)

        return {
            'ids': [i for i, _ in scores[:top_k]],
            'scores': [s for _, s in scores[:top_k]],
            'context': ' '.join([self.corpus[i] for i, _ in scores[:top_k]]),
        }


# ============= 命令行入口 =============

def main():
    """运行 RAG 评估"""
    import argparse

    parser = argparse.ArgumentParser(description="RAG 效果评估")
    parser.add_argument(
        "--queries",
        default="sample",
        help="评估查询文件路径"
    )
    parser.add_argument(
        "--output",
        default="rag_evaluation_report.json",
        help="报告输出路径"
    )
    parser.add_argument(
        "--top-ks",
        nargs="+",
        type=int,
        default=[5, 10, 20],
        help="要评估的 K 值列表"
    )

    args = parser.parse_args()

    # 创建模拟检索器
    corpus = [
        "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
        "class UserService: 用户服务类，处理用户认证和授权",
        "SELECT * FROM users WHERE id = ?",
        "async def fetch_data(url): async with aiohttp.ClientSession() as session: ...",
        "#include <iostream> int main() { std::cout << 'Hello World'; return 0; }",
    ]
    retriever = MockRetriever(corpus)

    # 创建评估器
    evaluator = RAGEvaluator(retriever)

    # 加载评估查询
    queries = [
        EvaluationQuery(query="递归函数", relevant_docs=[0]),
        EvaluationQuery(query="用户认证", relevant_docs=[1]),
        EvaluationQuery(query="数据库查询", relevant_docs=[2]),
        EvaluationQuery(query="异步 HTTP", relevant_docs=[3]),
        EvaluationQuery(query="C++ 程序", relevant_docs=[4]),
    ]
    evaluator.load_evaluation_queries(queries)

    # 运行评估
    result = evaluator.evaluate_retrieval(top_ks=args.top_ks)

    # 打印摘要
    evaluator.print_summary()

    # 生成报告
    evaluator.generate_report(args.output)


if __name__ == "__main__":
    main()
