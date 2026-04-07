"""
非结构化数据连接器模块

支持以下数据源：
- 文档文件 (PDF, Word, Excel, PPT)
- 文本数据 (TXT, Markdown, JSON, XML)
- 图片文件 (带 OCR 识别)
- 网页内容
- 电子邮件
- 聊天记录
"""

from .base import UnstructuredDataConnector, UnstructuredConfig, DocumentChunk
from .document_loader import DocumentLoader
from .text_loader import TextLoader
from .image_loader import ImageLoader
from .web_loader import WebLoader
from .email_loader import EmailLoader
from .chat_loader import ChatLoader

__all__ = [
    "UnstructuredDataConnector",
    "UnstructuredConfig",
    "DocumentChunk",
    "DocumentLoader",
    "TextLoader",
    "ImageLoader",
    "WebLoader",
    "EmailLoader",
    "ChatLoader",
]
