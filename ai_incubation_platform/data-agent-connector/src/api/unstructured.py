"""
非结构化数据 API 路由
"""
import os
import tempfile
import base64
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Body
from pydantic import BaseModel

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unstructured.base import UnstructuredConfig, DocumentChunk
from unstructured.document_loader import DocumentLoader
from unstructured.text_loader import TextLoader
from unstructured.image_loader import ImageLoader
from unstructured.web_loader import WebLoader
from unstructured.email_loader import EmailLoader
from unstructured.chat_loader import ChatLoader
from utils.logger import logger

router = APIRouter(prefix="/api/unstructured", tags=["unstructured"])


# ==================== 请求/响应模型 ====================

class UploadResponse(BaseModel):
    """上传响应"""
    file_id: str
    file_name: str
    file_type: str
    size: int
    status: str


class ParseRequest(BaseModel):
    """解析请求"""
    file_path: Optional[str] = None
    source_type: str = "document"  # document, text, image, web, email, chat
    chunk_size: int = 1000
    chunk_overlap: int = 100
    options: Dict[str, Any] = {}


class ParseResponse(BaseModel):
    """解析响应"""
    file_id: str
    source_type: str
    total_chunks: int
    total_characters: int
    metadata: Dict[str, Any]
    chunks: List[Dict[str, Any]]


class WebScrapeRequest(BaseModel):
    """网页抓取请求"""
    url: str
    timeout: int = 30
    chunk_size: int = 1000


class OcrRequest(BaseModel):
    """OCR 请求"""
    image_path: Optional[str] = None
    image_base64: Optional[str] = None
    language: str = "ch"  # ch 或 en


class OcrResponse(BaseModel):
    """OCR 响应"""
    text: str
    metadata: Dict[str, Any]
    chunks: List[Dict[str, Any]]


# ==================== 文件上传 ====================

@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """上传文件"""
    try:
        # 生成临时文件 ID
        import uuid
        file_id = str(uuid.uuid4())

        # 创建临时目录
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"{file_id}_{file.filename}")

        # 保存文件
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # 获取文件类型
        ext = os.path.splitext(file.filename)[1].lower()
        file_type = _get_source_type(ext)

        return UploadResponse(
            file_id=file_id,
            file_name=file.filename,
            file_type=file_type,
            size=len(content),
            status="uploaded"
        )
    except Exception as e:
        logger.error("Upload failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/upload_base64", response_model=UploadResponse)
async def upload_base64(file_data: Dict[str, Any] = Body(...)):
    """上传 base64 编码的文件"""
    try:
        import uuid
        file_id = str(uuid.uuid4())

        # 解析 base64
        base64_data = file_data.get("content", "")
        filename = file_data.get("filename", "unknown.bin")

        if base64_data.startswith("data:"):
            base64_data = base64_data.split(",")[1]

        content = base64.b64decode(base64_data)

        # 保存文件
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"{file_id}_{filename}")

        with open(file_path, "wb") as f:
            f.write(content)

        ext = os.path.splitext(filename)[1].lower()
        file_type = _get_source_type(ext)

        return UploadResponse(
            file_id=file_id,
            file_name=filename,
            file_type=file_type,
            size=len(content),
            status="uploaded"
        )
    except Exception as e:
        logger.error("Base64 upload failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ==================== 解析文件 ====================

@router.post("/parse", response_model=ParseResponse)
async def parse_file(request: ParseRequest):
    """解析文件"""
    try:
        config = UnstructuredConfig(
            name=request.file_path or "unknown",
            source_type=request.source_type,
            source_path=request.file_path,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            options=request.options
        )

        loader = _create_loader(request.source_type, config)
        await loader.connect()
        chunks = await loader.load_content()
        schema = await loader.get_schema()
        await loader.disconnect()

        return ParseResponse(
            file_id=request.file_path or "unknown",
            source_type=request.source_type,
            total_chunks=len(chunks),
            total_characters=sum(len(c.content) for c in chunks),
            metadata=schema.get("metadata", {}),
            chunks=[c.to_dict() for c in chunks]
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Parse failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Parse failed: {str(e)}")


@router.get("/{file_id}/content")
async def get_content(file_id: str, source_type: str = "document"):
    """获取解析后的内容"""
    try:
        # 查找临时文件
        temp_dir = tempfile.gettempdir()
        file_path = None
        for f in os.listdir(temp_dir):
            if f.startswith(file_id):
                file_path = os.path.join(temp_dir, f)
                break

        if not file_path:
            raise HTTPException(status_code=404, detail="File not found")

        config = UnstructuredConfig(
            name=file_path,
            source_type=source_type,
            source_path=file_path
        )

        loader = _create_loader(source_type, config)
        await loader.connect()
        content = await loader.get_content()
        schema = await loader.get_schema()
        await loader.disconnect()

        return {
            "file_id": file_id,
            "source_type": source_type,
            "content": content,
            "metadata": schema.get("metadata", {}),
            "total_characters": len(content)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get content failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Get content failed: {str(e)}")


# ==================== 网页抓取 ====================

@router.post("/web/scrape")
async def scrape_web(request: WebScrapeRequest):
    """抓取网页内容"""
    try:
        config = UnstructuredConfig(
            name=request.url,
            source_type="web",
            source_url=request.url,
            chunk_size=request.chunk_size,
            timeout=request.timeout
        )

        loader = WebLoader(config)
        await loader.connect()
        chunks = await loader.load_content()
        schema = await loader.get_schema()
        await loader.disconnect()

        return {
            "url": request.url,
            "title": schema.get("metadata", {}).get("title", ""),
            "content": "\n".join(c.content for c in chunks),
            "metadata": schema.get("metadata", {}),
            "total_chunks": len(chunks)
        }
    except Exception as e:
        logger.error("Web scrape failed", extra={"url": request.url, "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Web scrape failed: {str(e)}")


@router.post("/web/crawl")
async def crawl_web(start_url: str, max_pages: int = 10, allowed_domains: Optional[str] = None):
    """爬取多个网页"""
    try:
        config = UnstructuredConfig(
            name="crawl",
            source_type="web",
            source_url=start_url,
            options={
                "max_depth": 2,
                "allowed_domains": allowed_domains.split(",") if allowed_domains else []
            }
        )

        loader = WebLoader(config)
        await loader.connect()
        results = await loader.crawl(start_url, max_pages)
        await loader.disconnect()

        return {
            "start_url": start_url,
            "pages_crawled": len(results),
            "results": results
        }
    except Exception as e:
        logger.error("Web crawl failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Web crawl failed: {str(e)}")


# ==================== OCR 识别 ====================

@router.post("/ocr", response_model=OcrResponse)
async def perform_ocr(request: OcrRequest):
    """执行 OCR 识别"""
    try:
        image_path = request.image_path

        # 如果是 base64，先保存为临时文件
        if request.image_base64:
            import uuid
            file_id = str(uuid.uuid4())
            temp_dir = tempfile.gettempdir()

            base64_data = request.image_base64
            if base64_data.startswith("data:"):
                base64_data = base64_data.split(",")[1]

            content = base64.b64decode(base64_data)
            image_path = os.path.join(temp_dir, f"{file_id}.png")

            with open(image_path, "wb") as f:
                f.write(content)

        if not image_path:
            raise ValueError("image_path or image_base64 is required")

        # 使用 ImageLoader 进行 OCR
        result = await ImageLoader.ocr_image(image_path, request.language)

        return OcrResponse(
            text=result["text"],
            metadata=result["metadata"],
            chunks=result["chunks"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("OCR failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")


# ==================== 聊天记录解析 ====================

@router.post("/chat/parse")
async def parse_chat(
    file_path: str,
    platform: str = "generic",
    chunk_size: int = 1000
):
    """解析聊天记录"""
    try:
        config = UnstructuredConfig(
            name=file_path,
            source_type="chat",
            source_path=file_path,
            chunk_size=chunk_size,
            options={"platform": platform}
        )

        loader = ChatLoader(config)
        await loader.connect()
        chunks = await loader.load_content()
        schema = await loader.get_schema()
        await loader.disconnect()

        return {
            "file_path": file_path,
            "platform": platform,
            "message_count": schema.get("metadata", {}).get("message_count", 0),
            "participants": schema.get("metadata", {}).get("participants", []),
            "content": "\n".join(c.content for c in chunks),
            "chunks": [c.to_dict() for c in chunks]
        }
    except Exception as e:
        logger.error("Chat parse failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Chat parse failed: {str(e)}")


# ==================== 辅助函数 ====================

def _get_source_type(ext: str) -> str:
    """根据文件扩展名获取源类型"""
    document_exts = ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt']
    text_exts = ['.txt', '.md', '.markdown', '.json', '.xml', '.html']
    image_exts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
    email_exts = ['.eml', '.msg']
    chat_exts = ['.json', '.txt', '.csv']

    if ext in document_exts:
        return "document"
    elif ext in text_exts:
        return "text"
    elif ext in image_exts:
        return "image"
    elif ext in email_exts:
        return "email"
    elif ext in chat_exts:
        return "chat"
    else:
        return "document"


def _create_loader(source_type: str, config: UnstructuredConfig):
    """根据类型创建加载器"""
    if source_type == "document":
        return DocumentLoader(config)
    elif source_type == "text":
        return TextLoader(config)
    elif source_type == "image":
        return ImageLoader(config)
    elif source_type == "web":
        return WebLoader(config)
    elif source_type == "email":
        return EmailLoader(config)
    elif source_type == "chat":
        return ChatLoader(config)
    else:
        raise ValueError(f"Unknown source type: {source_type}")
