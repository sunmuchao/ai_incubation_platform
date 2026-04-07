"""
离线可用的“最小”Embedding：用稳定哈希把文本映射到固定维度向量。

目标：
- 不依赖外网/模型下载（本地即可运行）
- 提供与向量库一致的维度（便于从 BGE 自动降级）
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional

import numpy as np

from ..base import BaseEmbedding, CodeChunk


class HashEmbedding(BaseEmbedding):
    """
    用 token 哈希计数生成向量，作为 BGEEmbedding 的离线兜底。

    说明：这不是“语义强”向量，只是为了让索引管线在无模型下载条件下可跑通。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._dimension = int(self.config.get("dimension", 512))
        self._normalize = bool(self.config.get("normalize_embeddings", True))

        # 简单 token 规则：兼容中英文、数字、下划线
        self._token_re = re.compile(r"[A-Za-z0-9_]+")

    def get_dimension(self) -> int:
        return self._dimension

    def _hash_to_index(self, token: str) -> int:
        h = hashlib.md5(token.encode("utf-8")).hexdigest()
        return int(h, 16) % self._dimension

    def encode_text(self, text: str) -> List[float]:
        vec = np.zeros(self._dimension, dtype=np.float32)
        if not text:
            return vec.tolist()

        tokens = self._token_re.findall(text.lower())
        for t in tokens:
            vec[self._hash_to_index(t)] += 1.0

        if self._normalize:
            norm = float(np.linalg.norm(vec))
            if norm > 0:
                vec = vec / norm

        return vec.tolist()

    def encode_chunks(self, chunks: List[CodeChunk]) -> List[CodeChunk]:
        for chunk in chunks:
            # HashEmbedding 用于离线 P0：把 symbols + 文件路径 + 内容一起编码，
            # 让检索更容易定位到“按模块/路径问”的场景。
            if chunk.symbols:
                text = f"{chunk.file_path}\n{' '.join(chunk.symbols)}\n{chunk.content}"
            else:
                text = f"{chunk.file_path}\n{chunk.content}"
            chunk.embedding = self.encode_text(text)
        return chunks

