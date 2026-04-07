"""
索引管线基础抽象层
定义通用接口，支持多语言、多解析器、多向量存储的扩展
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import uuid


@dataclass
class CodeChunk:
    """代码分块数据结构：最小索引单元"""
    # chunk_id 由系统在对象创建时生成；为了兼容 Python 3.9 dataclass
    #（"带默认值字段"不能出现在"必填字段"之前），这里将 chunk_id 设为 init=False
    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4()), init=False)
    file_path: str
    language: str
    content: str
    start_line: int
    end_line: int
    chunk_type: str  # function, class, module, comment, etc.
    symbols: List[str] = field(default_factory=list)  # 包含的符号名
    metadata: Dict[str, Any] = field(default_factory=dict)  # 扩展字段
    embedding: Optional[List[float]] = None


@dataclass
class CodeSymbol:
    """代码符号结构：函数、类、变量等定义"""
    name: str
    symbol_type: str  # function, class, variable, interface
    file_path: str
    start_line: int
    end_line: int
    signature: Optional[str] = None
    docstring: Optional[str] = None
    modifiers: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)  # 引用位置


@dataclass
class FileIndexResult:
    """单文件索引结果"""
    file_path: str
    language: str
    chunks: List[CodeChunk]
    symbols: List[CodeSymbol]
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


class BaseParser(ABC):
    """代码解析器基类：支持多语言扩展"""

    @abstractmethod
    def supports_language(self, language: str) -> bool:
        """是否支持指定语言"""
        pass

    @abstractmethod
    def parse_file(self, file_path: Union[str, Path]) -> FileIndexResult:
        """解析单个文件，返回分块与符号信息"""
        pass

    @abstractmethod
    def parse_content(self, content: str, language: str, file_path: Optional[str] = None) -> FileIndexResult:
        """解析代码内容"""
        pass


class BaseEmbedding(ABC):
    """Embedding 模型基类：支持多种嵌入模型扩展"""

    @abstractmethod
    def get_dimension(self) -> int:
        """获取向量维度"""
        pass

    @abstractmethod
    def encode_text(self, text: str) -> List[float]:
        """编码单个文本"""
        pass

    @abstractmethod
    def encode_chunks(self, chunks: List[CodeChunk]) -> List[CodeChunk]:
        """批量编码代码块"""
        pass


class BaseVectorStore(ABC):
    """向量存储基类：支持多种向量数据库扩展（LlamaIndex 兼容）"""

    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> None:
        """连接向量存储"""
        pass

    @abstractmethod
    def create_collection(self, collection_name: str, dimension: int) -> None:
        """创建集合"""
        pass

    @abstractmethod
    def upsert_chunks(self, collection_name: str, chunks: List[CodeChunk]) -> int:
        """插入或更新代码块"""
        pass

    @abstractmethod
    def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[CodeChunk]:
        """语义搜索相关代码块"""
        pass

    @abstractmethod
    def delete_by_file(self, collection_name: str, file_path: str) -> int:
        """删除指定文件的所有块"""
        pass

    # ========== LlamaIndex 扩展方法 ==========

    def get_retriever(
        self,
        similarity_top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ):
        """获取检索器（LlamaIndex 兼容）"""
        raise NotImplementedError("此向量存储不支持 get_retriever 方法")

    def as_query_engine(self, **kwargs):
        """转换为查询引擎（LlamaIndex 兼容）"""
        raise NotImplementedError("此向量存储不支持 as_query_engine 方法")
