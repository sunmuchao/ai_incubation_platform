"""
Embedding 降级包装器：主模型不可用时自动切换到离线实现。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..base import BaseEmbedding, CodeChunk


class ResilientEmbedding(BaseEmbedding):
    """
    用于“索引管线最小可用版本”的兜底：
    - primary：尽量使用更好的 embedding（例如 BGE）
    - fallback：离线/轻量 embedding（例如 HashEmbedding）
    """

    def __init__(self, primary: BaseEmbedding, fallback: BaseEmbedding):
        self.primary = primary
        self.fallback = fallback
        self._use_fallback = False

        # 索引在 init 阶段会调用 get_dimension；这里固定主模型维度（要求 fallback 同维度）
        self._dimension = int(self.primary.get_dimension())

    def get_dimension(self) -> int:
        return self._dimension

    def encode_text(self, text: str) -> List[float]:
        if not self._use_fallback:
            try:
                return self.primary.encode_text(text)
            except Exception:
                self._use_fallback = True
        return self.fallback.encode_text(text)

    def encode_chunks(self, chunks: List[CodeChunk]) -> List[CodeChunk]:
        if not self._use_fallback:
            try:
                return self.primary.encode_chunks(chunks)
            except Exception:
                self._use_fallback = True
        return self.fallback.encode_chunks(chunks)

