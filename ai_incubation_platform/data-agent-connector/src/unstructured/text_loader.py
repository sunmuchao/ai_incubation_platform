"""
文本加载器 - 支持 TXT, Markdown, JSON, XML 文件解析
"""
import os
import json
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from pathlib import Path

from .base import UnstructuredDataConnector, UnstructuredConfig, DocumentChunk

try:
    from utils.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class TextLoader(UnstructuredDataConnector):
    """文本加载器 - 支持 TXT, Markdown, JSON, XML"""

    def __init__(self, config: UnstructuredConfig):
        super().__init__(config)
        self._document_text = ""
        self._metadata = {}

    async def connect(self) -> None:
        """验证文件是否存在"""
        if self.config.source_path:
            if not os.path.exists(self.config.source_path):
                raise FileNotFoundError(f"Text file not found: {self.config.source_path}")
        self._connected = True
        logger.info("Text loader connected", extra={"source": self.config.source_path})

    async def disconnect(self) -> None:
        """断开连接，清理缓存"""
        self._document_text = ""
        self._metadata = {}
        self._content_cache = []
        self._connected = False
        logger.info("Text loader disconnected")

    async def load_content(self) -> List[DocumentChunk]:
        """加载文本内容"""
        if not self._connected:
            await self.connect()

        # 如果已有缓存内容（如 from_string 创建），直接返回
        if self._content_cache:
            return self._content_cache

        source_path = self.config.source_path
        if not source_path:
            raise ValueError("source_path is required for text loading")

        ext = Path(source_path).suffix.lower()

        if ext == '.txt':
            text, metadata = await self._load_txt(source_path)
        elif ext in ['.md', '.markdown']:
            text, metadata = await self._load_markdown(source_path)
        elif ext == '.json':
            text, metadata = await self._load_json(source_path)
        elif ext in ['.xml', '.html']:
            text, metadata = await self._load_xml(source_path)
        else:
            # 默认当作文本处理
            text, metadata = await self._load_txt(source_path)

        self._document_text = text
        self._metadata = metadata

        # 分割成片段
        chunks = self._split_text(text)
        result = []
        for i, chunk in enumerate(chunks):
            result.append(self._create_chunk(
                content=chunk,
                index=i,
                metadata={**metadata, "chunk_type": "text", "file_type": ext}
            ))

        self._content_cache = result
        logger.info("Text file loaded", extra={"path": source_path, "chunks": len(result)})
        return result

    async def get_schema(self) -> Dict[str, Any]:
        """获取文档元数据"""
        return {
            "source_type": "text",
            "source_path": self.config.source_path,
            "chunk_size": self.config.chunk_size,
            "chunk_overlap": self.config.chunk_overlap,
            "metadata": self._metadata,
            "total_chunks": len(self._content_cache)
        }

    async def _load_txt(self, path: str) -> tuple:
        """加载 TXT 文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 统计行数
            lines = content.split('\n')

            return content, {
                "file_type": "txt",
                "line_count": len(lines),
                "char_count": len(content),
                "encoding": "utf-8"
            }
        except UnicodeDecodeError:
            # 尝试其他编码
            with open(path, 'r', encoding='gbk') as f:
                content = f.read()

            lines = content.split('\n')
            return content, {
                "file_type": "txt",
                "line_count": len(lines),
                "char_count": len(content),
                "encoding": "gbk"
            }

    async def _load_markdown(self, path: str) -> tuple:
        """加载 Markdown 文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析标题
            lines = content.split('\n')
            headers = []
            for line in lines:
                if line.startswith('#'):
                    headers.append(line.strip())

            return content, {
                "file_type": "markdown",
                "line_count": len(lines),
                "char_count": len(content),
                "header_count": len(headers),
                "headers": headers[:10]  # 只保留前 10 个标题
            }
        except UnicodeDecodeError:
            with open(path, 'r', encoding='gbk') as f:
                content = f.read()
            return content, {
                "file_type": "markdown",
                "encoding": "gbk"
            }

    async def _load_json(self, path: str) -> tuple:
        """加载 JSON 文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 格式化输出
            content = json.dumps(data, indent=2, ensure_ascii=False)

            # 提取键信息
            if isinstance(data, dict):
                keys = list(data.keys())
            elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                keys = list(data[0].keys())
            else:
                keys = []

            return content, {
                "file_type": "json",
                "top_level_keys": keys,
                "is_array": isinstance(data, list),
                "char_count": len(content)
            }
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")

    async def _load_xml(self, path: str) -> tuple:
        """加载 XML 文件"""
        try:
            tree = ET.parse(path)
            root = tree.getroot()

            # 提取文本内容
            text_parts = []

            def extract_text(element):
                if element.text and element.text.strip():
                    text_parts.append(element.text.strip())
                for child in element:
                    extract_text(child)
                if element.tail and element.tail.strip():
                    text_parts.append(element.tail.strip())

            extract_text(root)
            content = "\n".join(text_parts)

            # 提取根元素信息
            def get_elem_info(elem, path=""):
                info = {elem.tag: len(list(elem))}
                for child in elem:
                    info.update(get_elem_info(child, f"{path}/{elem.tag}"))
                return info

            structure = get_elem_info(root)

            return content, {
                "file_type": "xml",
                "root_element": root.tag,
                "structure": structure,
                "char_count": len(content)
            }
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML format: {str(e)}")

    @classmethod
    def from_string(cls, name: str, content: str, chunk_size: int = 1000, chunk_overlap: int = 100) -> "TextLoader":
        """从字符串创建加载器"""
        config = UnstructuredConfig(
            name=name,
            source_type="text",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        loader = cls(config)
        loader._document_text = content
        loader._connected = True

        # 预加载内容到缓存
        chunks = loader._split_text(content)
        for i, chunk_text in enumerate(chunks):
            loader._content_cache.append(loader._create_chunk(
                content=chunk_text,
                index=i,
                metadata={"chunk_type": "text", "source": "string"}
            ))
        loader._metadata = {
            "file_type": "string",
            "char_count": len(content),
            "chunk_count": len(chunks)
        }

        return loader
