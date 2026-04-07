"""
非结构化数据连接器基类
"""
from abc import ABC, abstractmethod
from typing import Any, Optional, List, Dict
from dataclasses import dataclass, field
from datetime import datetime
import hashlib


@dataclass
class DocumentChunk:
    """文档片段"""
    content: str  # 文本内容
    source: str  # 来源文件/URL
    chunk_index: int  # 片段索引
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "content": self.content,
            "source": self.source,
            "chunk_index": self.chunk_index,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }

    @property
    def content_hash(self) -> str:
        """内容哈希值，用于去重"""
        return hashlib.md5(self.content.encode()).hexdigest()


@dataclass
class UnstructuredConfig:
    """非结构化数据连接器配置"""
    name: str
    source_type: str  # document, text, image, web, email, chat
    source_path: Optional[str] = None  # 本地文件路径
    source_url: Optional[str] = None  # URL
    chunk_size: int = 1000  # 分片大小（字符数）
    chunk_overlap: int = 100  # 分片重叠
    timeout: int = 30
    options: Dict[str, Any] = field(default_factory=dict)  # 额外配置


class UnstructuredDataConnector(ABC):
    """非结构化数据连接器基类"""

    def __init__(self, config: UnstructuredConfig):
        self.config = config
        self._connected = False
        self._content_cache: List[DocumentChunk] = []

    @property
    def is_connected(self) -> bool:
        return self._connected

    @abstractmethod
    async def connect(self) -> None:
        """建立连接/加载数据源"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""
        pass

    @abstractmethod
    async def load_content(self) -> List[DocumentChunk]:
        """加载内容并分片"""
        pass

    @abstractmethod
    async def get_schema(self) -> Dict[str, Any]:
        """获取数据结构/模式"""
        pass

    async def get_chunks(self) -> List[DocumentChunk]:
        """获取已加载的文档片段"""
        if not self._content_cache:
            self._content_cache = await self.load_content()
        return self._content_cache

    async def get_content(self) -> str:
        """获取完整文本内容"""
        chunks = await self.get_chunks()
        return "\n".join(chunk.content for chunk in chunks)

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    def _split_text(self, text: str) -> List[str]:
        """将文本分割成指定大小的片段"""
        if len(text) <= self.config.chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + self.config.chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - self.config.chunk_overlap
            if start >= len(text):
                break
        return chunks

    def _create_chunk(self, content: str, index: int, metadata: Dict[str, Any] = None) -> DocumentChunk:
        """创建文档片段"""
        return DocumentChunk(
            content=content,
            source=self.config.source_path or self.config.source_url or self.config.name,
            chunk_index=index,
            metadata=metadata or {}
        )
