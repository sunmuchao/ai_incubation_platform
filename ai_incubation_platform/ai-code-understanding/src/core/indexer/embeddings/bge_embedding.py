"""
BGE系列Embedding模型实现
针对代码场景优化，支持中英文混合代码
"""
from typing import Any, Dict, List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

from ..base import BaseEmbedding, CodeChunk


class BGEEmbedding(BaseEmbedding):
    """
    BGE Embedding实现
    默认使用bge-small-code-v1.5，针对代码场景优化
    模型选型思路：
    - bge-small-code-v1.5: 轻量、速度快、代码检索效果好，适合本地部署
    - bge-base-code-v1.5: 效果更好，资源占用适中
    - bge-large-code-v1.5: 最佳效果，适合服务端部署
    """

    DEFAULT_MODEL = "BAAI/bge-small-code-v1.5"
    DEFAULT_DIMENSION = 512  # small版本维度

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.model_name = self.config.get('model_name', self.DEFAULT_MODEL)
        self.device = self.config.get('device', 'cpu')  # 可选cuda, mps
        self.normalize_embeddings = self.config.get('normalize_embeddings', True)

        # 模型懒加载
        self._model = None
        self._dimension = self.config.get('dimension', self.DEFAULT_DIMENSION)

    def _load_model(self) -> None:
        """延迟加载模型"""
        if self._model is None:
            self._model = SentenceTransformer(
                self.model_name,
                device=self.device,
                trust_remote_code=True
            )
            # 自动获取维度
            if hasattr(self._model, 'get_sentence_embedding_dimension'):
                self._dimension = self._model.get_sentence_embedding_dimension()

    def get_dimension(self) -> int:
        return self._dimension

    def encode_text(self, text: str) -> List[float]:
        self._load_model()

        # BGE系列推荐在查询前加"为这个句子生成表示以用于检索相关文档："前缀
        # 代码场景可以用专门的前缀
        query_prefix = self.config.get('query_prefix', '')
        if query_prefix:
            text = query_prefix + text

        embedding = self._model.encode(
            text,
            normalize_embeddings=self.normalize_embeddings,
            convert_to_numpy=True
        )

        return embedding.tolist()

    def encode_chunks(self, chunks: List[CodeChunk]) -> List[CodeChunk]:
        self._load_model()

        # 批量编码
        texts = []
        for chunk in chunks:
            # 代码块的表示：优先用符号名+内容，增强语义
            if chunk.symbols:
                prefix = f"{' '.join(chunk.symbols)}\n"
            else:
                prefix = ""
            texts.append(prefix + chunk.content)

        # 代码段落用不同的前缀
        passage_prefix = self.config.get('passage_prefix', '')
        if passage_prefix:
            texts = [passage_prefix + text for text in texts]

        embeddings = self._model.encode(
            texts,
            normalize_embeddings=self.normalize_embeddings,
            convert_to_numpy=True,
            batch_size=self.config.get('batch_size', 32),
            show_progress_bar=self.config.get('show_progress_bar', False)
        )

        # 赋值embedding
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding.tolist()

        return chunks


class BGELargeCodeEmbedding(BGEEmbedding):
    """BGE大模型版本，效果更好"""
    DEFAULT_MODEL = "BAAI/bge-large-code-v1.5"
    DEFAULT_DIMENSION = 1024


class BGEM3Embedding(BaseEmbedding):
    """
    BGE-M3多模态Embedding
    支持多语言、长文本、跨模态检索
    """

    DEFAULT_MODEL = "BAAI/bge-m3"
    DEFAULT_DIMENSION = 1024

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.model_name = self.config.get('model_name', self.DEFAULT_MODEL)
        self.device = self.config.get('device', 'cpu')
        self._model = None
        self._dimension = self.config.get('dimension', self.DEFAULT_DIMENSION)

    def _load_model(self) -> None:
        if self._model is None:
            from FlagEmbedding import BGEM3FlagModel
            self._model = BGEM3FlagModel(
                self.model_name,
                device=self.device,
                use_fp16=self.config.get('use_fp16', False)
            )

    def get_dimension(self) -> int:
        return self._dimension

    def encode_text(self, text: str) -> List[float]:
        self._load_model()
        embeddings = self._model.encode(
            [text],
            batch_size=1,
            max_length=self.config.get('max_length', 8192),
        )['dense_vecs']
        return embeddings[0].tolist()

    def encode_chunks(self, chunks: List[CodeChunk]) -> List[CodeChunk]:
        self._load_model()
        texts = []
        for chunk in chunks:
            if chunk.symbols:
                prefix = f"{' '.join(chunk.symbols)}\n"
            else:
                prefix = ""
            texts.append(prefix + chunk.content)

        embeddings = self._model.encode(
            texts,
            batch_size=self.config.get('batch_size', 16),
            max_length=self.config.get('max_length', 8192),
        )['dense_vecs']

        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding.tolist()

        return chunks
