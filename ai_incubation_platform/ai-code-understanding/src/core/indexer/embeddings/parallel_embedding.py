"""
并行嵌入处理优化模块 - OPT-1 核心实现

功能:
1. 多线程/多进程并行嵌入生成
2. 代码分块缓存机制 (LRU 策略)
3. AST 哈希树增量检测 (类似 Merkle 树)
4. 智能批处理大小自适应

性能目标:
- 索引速度提升 3-5 倍
- 缓存命中率 > 60%
- 增量索引仅处理变更 AST 节点
"""
from __future__ import annotations

import os
import json
import hashlib
import logging
import threading
import multiprocessing as mp
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
import time

from ..base import BaseEmbedding, CodeChunk

logger = logging.getLogger(__name__)


@dataclass
class ASTNode:
    """AST 节点用于构建哈希树"""
    node_type: str  # function, class, import, statement
    content_hash: str  # 内容哈希
    children: List[ASTNode] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0
    symbol_name: Optional[str] = None

    def compute_merkle_hash(self) -> str:
        """计算 Merkle 哈希 (自底向上)"""
        children_hashes = [child.compute_merkle_hash() for child in sorted(self.children, key=lambda x: x.start_line)]
        combined = f"{self.node_type}:{self.content_hash}:{'|'.join(children_hashes)}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'node_type': self.node_type,
            'content_hash': self.content_hash,
            'start_line': self.start_line,
            'end_line': self.end_line,
            'symbol_name': self.symbol_name,
            'children': [c.to_dict() for c in self.children]
        }


@dataclass
class ASTHashTree:
    """
    AST 哈希树 (类似 Merkle 树)
    用于精确检测代码结构变更，实现增量索引
    """
    file_path: str
    language: str
    root_hash: str
    nodes: Dict[str, ASTNode] = field(default_factory=dict)  # symbol_name -> ASTNode
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    def detect_changes(self, new_tree: ASTHashTree) -> List[str]:
        """
        比较两棵树，返回变更的符号列表
        """
        changed_symbols = []

        # 根哈希相同，无变更
        if self.root_hash == new_tree.root_hash:
            return changed_symbols

        # 逐节点比较
        for symbol_name, new_node in new_tree.nodes.items():
            if symbol_name not in self.nodes:
                changed_symbols.append(symbol_name)  # 新增符号
            elif self.nodes[symbol_name].content_hash != new_node.content_hash:
                changed_symbols.append(symbol_name)  # 内容变更

        # 检测被删除的符号
        for symbol_name in self.nodes:
            if symbol_name not in new_tree.nodes:
                changed_symbols.append(f"DELETED:{symbol_name}")

        return changed_symbols

    def to_dict(self) -> Dict[str, Any]:
        return {
            'file_path': self.file_path,
            'language': self.language,
            'root_hash': self.root_hash,
            'nodes': {k: v.to_dict() for k, v in self.nodes.items()},
            'last_updated': self.last_updated
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ASTHashTree:
        def build_node(node_data: Dict) -> ASTNode:
            return ASTNode(
                node_type=node_data['node_type'],
                content_hash=node_data['content_hash'],
                start_line=node_data['start_line'],
                end_line=node_data['end_line'],
                symbol_name=node_data.get('symbol_name'),
                children=[build_node(c) for c in node_data.get('children', [])]
            )

        nodes = {k: build_node(v) for k, v in data.get('nodes', {}).items()}
        return cls(
            file_path=data['file_path'],
            language=data['language'],
            root_hash=data['root_hash'],
            nodes=nodes,
            last_updated=data.get('last_updated', datetime.now().isoformat())
        )


class LRUEmbeddingCache:
    """
    LRU Embedding 缓存
    用于避免重复计算相同的代码块嵌入
    """

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._cache: OrderedDict[str, List[float]] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def _make_key(self, chunk: CodeChunk) -> str:
        """生成缓存键"""
        # 使用代码内容 + 语言 + 符号信息的组合哈希
        key_parts = [
            chunk.language,
            chunk.content[:500],  # 前 500 字符
            ','.join(sorted(chunk.symbols)),
            str(chunk.start_line),
            str(chunk.end_line)
        ]
        return hashlib.md5('|'.join(key_parts).encode('utf-8')).hexdigest()

    def get(self, chunk: CodeChunk) -> Optional[List[float]]:
        """获取缓存的嵌入向量"""
        key = self._make_key(chunk)
        with self._lock:
            if key in self._cache:
                # 移动到末尾 (最近使用)
                self._cache.move_to_end(key)
                self._hits += 1
                return self._cache[key]
            self._misses += 1
            return None

    def put(self, chunk: CodeChunk, embedding: List[float]) -> None:
        """缓存嵌入向量"""
        key = self._make_key(chunk)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = embedding
            else:
                if len(self._cache) >= self.max_size:
                    # LRU 驱逐
                    self._cache.popitem(last=False)
                    self._evictions += 1
                self._cache[key] = embedding

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self._hits + self._misses
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'hits': self._hits,
            'misses': self._misses,
            'evictions': self._evictions,
            'hit_rate': round(self._hits / total * 100, 2) if total > 0 else 0
        }

    def save(self, path: str) -> None:
        """持久化缓存到磁盘"""
        with self._lock:
            data = {
                'cache': dict(self._cache),
                'stats': self.get_stats()
            }
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f)

    def load(self, path: str) -> bool:
        """从磁盘加载缓存"""
        if not os.path.exists(path):
            return False
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            with self._lock:
                self._cache = OrderedDict(data.get('cache', {}))
                # 限制加载后的大小
                while len(self._cache) > self.max_size:
                    self._cache.popitem(last=False)
            logger.info(f"成功加载嵌入缓存：{len(self._cache)} 条记录")
            return True
        except Exception as e:
            logger.error(f"加载嵌入缓存失败：{e}")
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()


class ASTHashTreeCache:
    """
    AST 哈希树持久化缓存
    用于跨会话的增量索引检测
    """

    def __init__(self, cache_dir: str = "./data/ast_hash_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._trees: Dict[str, ASTHashTree] = {}
        self._lock = threading.RLock()
        self._load_metadata()

    def _get_cache_file_path(self, file_path: str) -> str:
        """获取缓存文件路径 (使用哈希避免路径问题)"""
        hash_key = hashlib.md5(file_path.encode('utf-8')).hexdigest()
        return str(self.cache_dir / f"{hash_key}.json")

    def _load_metadata(self) -> None:
        """加载元数据索引"""
        meta_file = self.cache_dir / "_metadata.json"
        if meta_file.exists():
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                # 懒加载，只记录路径
                self._file_to_hash = {k: v.get('root_hash') for k, v in metadata.items()}
            except:
                self._file_to_hash = {}
        else:
            self._file_to_hash = {}

    def _save_metadata(self) -> None:
        """保存元数据索引"""
        meta_file = self.cache_dir / "_metadata.json"
        metadata = {}
        for file_path, tree in self._trees.items():
            metadata[file_path] = {
                'root_hash': tree.root_hash,
                'language': tree.language,
                'last_updated': tree.last_updated,
                'node_count': len(tree.nodes)
            }
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

    def get(self, file_path: str) -> Optional[ASTHashTree]:
        """获取文件的 AST 哈希树"""
        file_path = str(file_path)
        with self._lock:
            if file_path in self._trees:
                return self._trees[file_path]

            # 尝试从磁盘加载
            cache_file = self._get_cache_file_path(file_path)
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    tree = ASTHashTree.from_dict(data)
                    self._trees[file_path] = tree
                    return tree
                except Exception as e:
                    logger.warning(f"加载 AST 哈希树失败：{e}")
            return None

    def put(self, tree: ASTHashTree) -> None:
        """保存 AST 哈希树"""
        with self._lock:
            self._trees[tree.file_path] = tree

            # 持久化到磁盘
            cache_file = self._get_cache_file_path(tree.file_path)
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(tree.to_dict(), f, indent=2)
                self._save_metadata()
            except Exception as e:
                logger.error(f"保存 AST 哈希树失败：{e}")

    def remove(self, file_path: str) -> None:
        """删除文件的 AST 哈希树"""
        file_path = str(file_path)
        with self._lock:
            if file_path in self._trees:
                del self._trees[file_path]
            cache_file = self._get_cache_file_path(file_path)
            if os.path.exists(cache_file):
                os.remove(cache_file)
            self._save_metadata()

    def needs_indexing(self, file_path: str, new_root_hash: str) -> bool:
        """检查文件是否需要重新索引"""
        cached_tree = self.get(file_path)
        if cached_tree is None:
            return True  # 首次索引
        return cached_tree.root_hash != new_root_hash


def _worker_encode_chunk(args: Tuple) -> Tuple[int, CodeChunk]:
    """工作进程：嵌入生成 (用于多进程并行)"""
    idx, chunk_data, model_name, device = args

    # 重建 CodeChunk
    chunk = CodeChunk(
        file_path=chunk_data['file_path'],
        language=chunk_data['language'],
        content=chunk_data['content'],
        start_line=chunk_data['start_line'],
        end_line=chunk_data['end_line'],
        chunk_type=chunk_data['chunk_type'],
        symbols=chunk_data['symbols'],
        metadata=chunk_data.get('metadata', {})
    )

    # 懒加载模型 (每个进程独立)
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_name, device=device, trust_remote_code=True)

    # 生成嵌入
    text = chunk.content
    if chunk.symbols:
        text = f"{' '.join(chunk.symbols)}\n{text}"
    embedding = model.encode(text, normalize_embeddings=True, convert_to_numpy=True)
    chunk.embedding = embedding.tolist()

    return idx, chunk


class ParallelEmbeddingProcessor:
    """
    并行嵌入处理器

    支持三种并行模式:
    1. 多线程模式 - 适合 I/O 密集型
    2. 多进程模式 - 适合 CPU 密集型 (模型推理)
    3. 混合模式 - 结合两者优势
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # 并行配置
        self.mode = self.config.get('mode', 'hybrid')  # 'thread', 'process', 'hybrid'
        self.num_workers = self.config.get('num_workers', min(mp.cpu_count(), 8))
        self.batch_size = self.config.get('batch_size', 64)

        # 模型配置
        self.model_name = self.config.get('model_name', 'BAAI/bge-small-code-v1.5')
        self.device = self.config.get('device', 'cpu')

        # 缓存配置
        self.enable_cache = self.config.get('enable_cache', True)
        self.cache_size = self.config.get('cache_size', 10000)
        self.cache_persistence = self.config.get('cache_persistence', True)
        self.cache_dir = Path(self.config.get('cache_dir', './data/embedding_cache'))

        # AST 哈希树配置
        self.ast_hash_cache_dir = self.config.get('ast_hash_cache_dir', './data/ast_hash_cache')

        # 初始化缓存
        self._embedding_cache: Optional[LRUEmbeddingCache] = None
        self._ast_hash_cache: Optional[ASTHashTreeCache] = None

        # 统计信息
        self._stats = {
            'total_processed': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'batches_processed': 0,
            'total_time': 0.0
        }

        self._lock = threading.Lock()

    def initialize(self) -> None:
        """初始化缓存和模型"""
        if self.enable_cache:
            self._embedding_cache = LRUEmbeddingCache(max_size=self.cache_size)

            # 尝试加载持久化缓存
            if self.cache_persistence:
                cache_file = self.cache_dir / "embedding_cache.json"
                self._embedding_cache.load(str(cache_file))

            self._ast_hash_cache = ASTHashTreeCache(cache_dir=self.ast_hash_cache_dir)

        logger.info(f"并行嵌入处理器初始化完成：mode={self.mode}, workers={self.num_workers}")

    def _build_ast_hash_tree(
        self,
        content: str,
        language: str,
        symbols: Optional[List[Any]] = None
    ) -> ASTHashTree:
        """
        从代码内容构建 AST 哈希树

        Args:
            content: 代码内容
            language: 编程语言
            symbols: 符号列表 (可选)

        Returns:
            ASTHashTree 对象
        """
        lines = content.split('\n')
        nodes: Dict[str, ASTNode] = {}

        # 简化的 AST 节点提取 (基于代码结构)
        # 实际使用应集成 tree-sitter 解析
        current_node: Optional[ASTNode] = None
        indent_stack = []

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue

            # 检测函数/类定义
            if any(stripped.startswith(kw) for kw in ['def ', 'class ', 'func ', 'function ']):
                if current_node:
                    current_node.end_line = line_num - 1

                # 提取符号名
                match = None
                for pattern in [r'def\s+(\w+)', r'class\s+(\w+)', r'func\s+(\w+)']:
                    import re
                    match = re.match(pattern, stripped)
                    if match:
                        break

                if match:
                    symbol_name = match.group(1)
                    node_type = 'function' if 'def ' in stripped or 'func ' in stripped else 'class'
                    content_hash = hashlib.md5(stripped.encode('utf-8')).hexdigest()

                    current_node = ASTNode(
                        node_type=node_type,
                        content_hash=content_hash,
                        start_line=line_num,
                        symbol_name=symbol_name
                    )
                    nodes[symbol_name] = current_node

        if current_node:
            current_node.end_line = len(lines)

        # 计算根哈希
        root_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

        return ASTHashTree(
            file_path='',
            language=language,
            root_hash=root_hash,
            nodes=nodes
        )

    def encode_chunks_parallel(
        self,
        chunks: List[CodeChunk],
        callback: Optional[Callable[[int, int], None]] = None
    ) -> List[CodeChunk]:
        """
        并行嵌入生成

        Args:
            chunks: 代码块列表
            callback: 进度回调函数 (current, total)

        Returns:
            嵌入后的代码块列表
        """
        if not chunks:
            return chunks

        start_time = time.time()
        results = list(chunks)  # 复制列表

        # 分离缓存命中和未命中的块
        pending_chunks = []
        pending_indices = []

        for i, chunk in enumerate(chunks):
            if self.enable_cache and self._embedding_cache:
                cached_embedding = self._embedding_cache.get(chunk)
                if cached_embedding is not None:
                    chunk.embedding = cached_embedding
                    with self._lock:
                        self._stats['cache_hits'] += 1
                    continue

            pending_chunks.append(chunk)
            pending_indices.append(i)

        with self._lock:
            self._stats['cache_misses'] += len(pending_chunks)

        if not pending_chunks:
            # 全部命中缓存
            with self._lock:
                self._stats['total_processed'] += len(chunks)
                self._stats['total_time'] += time.time() - start_time
            return results

        # 批量处理
        batches = []
        for i in range(0, len(pending_chunks), self.batch_size):
            batch = pending_chunks[i:i + self.batch_size]
            batches.append((i // self.batch_size, batch))

        if self.mode == 'process':
            # 多进程模式
            results = self._encode_multiprocess(results, pending_indices, pending_chunks, callback)
        elif self.mode == 'thread':
            # 多线程模式
            results = self._encode_multithread(results, pending_indices, pending_chunks, callback)
        else:
            # 混合模式：批量使用多线程
            results = self._encode_multithread(results, pending_indices, pending_chunks, callback)

        # 更新缓存
        if self.enable_cache and self._embedding_cache:
            for chunk in chunks:
                if chunk.embedding is not None:
                    self._embedding_cache.put(chunk, chunk.embedding)

        elapsed = time.time() - start_time
        with self._lock:
            self._stats['total_processed'] += len(chunks)
            self._stats['batches_processed'] += len(batches)
            self._stats['total_time'] += elapsed

        logger.info(f"并行嵌入处理完成：{len(chunks)} chunks, {elapsed:.2f}s, {len(chunks)/elapsed:.1f} chunks/s")

        return results

    def _encode_multithread(
        self,
        results: List[CodeChunk],
        pending_indices: List[int],
        pending_chunks: List[CodeChunk],
        callback: Optional[Callable[[int, int], None]] = None
    ) -> List[CodeChunk]:
        """多线程嵌入生成"""
        from sentence_transformers import SentenceTransformer

        # 加载模型 (主线程)
        model = SentenceTransformer(self.model_name, device=self.device, trust_remote_code=True)

        def process_batch(batch_indices: List[int], batch_chunks: List[CodeChunk]) -> List[Tuple[int, CodeChunk]]:
            batch_results = []

            # 批量编码
            texts = []
            for chunk in batch_chunks:
                text = chunk.content
                if chunk.symbols:
                    text = f"{' '.join(chunk.symbols)}\n{text}"
                texts.append(text)

            embeddings = model.encode(
                texts,
                normalize_embeddings=True,
                convert_to_numpy=True,
                batch_size=self.batch_size,
                show_progress_bar=False
            )

            for i, (idx, chunk) in enumerate(zip(batch_indices, batch_chunks)):
                chunk.embedding = embeddings[i].tolist()
                batch_results.append((idx, chunk))

            return batch_results

        # 使用线程池
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = []
            for i in range(0, len(pending_chunks), self.batch_size):
                batch_indices = pending_indices[i:i + self.batch_size]
                batch_chunks = pending_chunks[i:i + self.batch_size]
                future = executor.submit(process_batch, batch_indices, batch_chunks)
                futures.append(future)

            for future in as_completed(futures):
                batch_results = future.result()
                for idx, chunk in batch_results:
                    results[idx] = chunk

                if callback:
                    processed = sum(len(f.result()) for f in futures if f.done())
                    callback(processed, len(pending_chunks))

        return results

    def _encode_multiprocess(
        self,
        results: List[CodeChunk],
        pending_indices: List[int],
        pending_chunks: List[CodeChunk],
        callback: Optional[Callable[[int, int], None]] = None
    ) -> List[CodeChunk]:
        """多进程嵌入生成"""
        # 准备进程间数据
        chunk_data_list = []
        for chunk in pending_chunks:
            chunk_data = {
                'file_path': chunk.file_path,
                'language': chunk.language,
                'content': chunk.content,
                'start_line': chunk.start_line,
                'end_line': chunk.end_line,
                'chunk_type': chunk.chunk_type,
                'symbols': chunk.symbols,
                'metadata': chunk.metadata
            }
            chunk_data_list.append(chunk_data)

        # 准备任务参数
        tasks = []
        for i, chunk_data in enumerate(chunk_data_list):
            tasks.append((i, chunk_data, self.model_name, self.device))

        # 进程池处理
        with ProcessPoolExecutor(max_workers=self.num_workers) as executor:
            futures = [executor.submit(_worker_encode_chunk, task) for task in tasks]

            for future in as_completed(futures):
                idx, chunk = future.result()
                original_idx = pending_indices[idx]
                results[original_idx] = chunk

                if callback:
                    done = sum(1 for f in futures if f.done())
                    callback(done, len(pending_chunks))

        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        stats = {**self._stats}

        if self._embedding_cache:
            stats['cache'] = self._embedding_cache.get_stats()

        if self._ast_hash_cache:
            stats['ast_cache_enabled'] = True

        return stats

    def save_cache(self) -> None:
        """持久化缓存到磁盘"""
        if self._embedding_cache and self.cache_persistence:
            cache_file = self.cache_dir / "embedding_cache.json"
            self._embedding_cache.save(str(cache_file))
            logger.info(f"嵌入缓存已保存到：{cache_file}")

    def clear_cache(self) -> None:
        """清空所有缓存"""
        if self._embedding_cache:
            self._embedding_cache.clear()
        if self._ast_hash_cache:
            self._ast_hash_cache = ASTHashTreeCache(cache_dir=self.ast_hash_cache_dir)


# 便捷函数
def create_parallel_processor(
    mode: str = 'hybrid',
    num_workers: int = 4,
    model_name: str = 'BAAI/bge-small-code-v1.5',
    device: str = 'cpu',
    cache_size: int = 10000,
    enable_cache: bool = True
) -> ParallelEmbeddingProcessor:
    """创建并行嵌入处理器"""
    config = {
        'mode': mode,
        'num_workers': num_workers,
        'model_name': model_name,
        'device': device,
        'cache_size': cache_size,
        'enable_cache': enable_cache,
        'cache_persistence': True
    }
    processor = ParallelEmbeddingProcessor(config)
    processor.initialize()
    return processor
