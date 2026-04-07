"""
图片加载器 - 支持 OCR 文字识别
"""
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from .base import UnstructuredDataConnector, UnstructuredConfig, DocumentChunk

try:
    from utils.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class ImageLoader(UnstructuredDataConnector):
    """图片加载器 - 支持 OCR 文字识别"""

    def __init__(self, config: UnstructuredConfig):
        super().__init__(config)
        self._ocr_text = ""
        self._metadata = {}
        self._ocr_language = config.options.get("language", "ch")  # ch 或 en

    async def connect(self) -> None:
        """验证文件是否存在"""
        if self.config.source_path:
            if not os.path.exists(self.config.source_path):
                raise FileNotFoundError(f"Image not found: {self.config.source_path}")
        self._connected = True
        logger.info("Image loader connected", extra={"source": self.config.source_path})

    async def disconnect(self) -> None:
        """断开连接，清理缓存"""
        self._ocr_text = ""
        self._metadata = {}
        self._content_cache = []
        self._connected = False
        logger.info("Image loader disconnected")

    async def load_content(self) -> List[DocumentChunk]:
        """加载图片并进行 OCR 识别"""
        if not self._connected:
            await self.connect()

        source_path = self.config.source_path
        if not source_path:
            raise ValueError("source_path is required for image loading")

        text, metadata = await self._perform_ocr(source_path)

        self._ocr_text = text
        self._metadata = metadata

        # 如果 OCR 结果为空，返回空片段
        if not text.strip():
            result = [self._create_chunk(
                content="[No text detected in image]",
                index=0,
                metadata={**metadata, "chunk_type": "image", "ocr_result": "empty"}
            )]
        else:
            # 分割成片段
            chunks = self._split_text(text)
            result = []
            for i, chunk in enumerate(chunks):
                result.append(self._create_chunk(
                    content=chunk,
                    index=i,
                    metadata={**metadata, "chunk_type": "image", "ocr_result": "success"}
                ))

        self._content_cache = result
        logger.info("Image OCR completed", extra={"path": source_path, "chunks": len(result)})
        return result

    async def get_schema(self) -> Dict[str, Any]:
        """获取图片元数据"""
        return {
            "source_type": "image",
            "source_path": self.config.source_path,
            "chunk_size": self.config.chunk_size,
            "chunk_overlap": self.config.chunk_overlap,
            "metadata": self._metadata,
            "total_chunks": len(self._content_cache),
            "ocr_language": self._ocr_language
        }

    async def _perform_ocr(self, path: str) -> tuple:
        """执行 OCR 识别"""
        try:
            # 首先尝试使用 PaddleOCR（中文支持更好）
            return await self._paddle_ocr(path)
        except ImportError:
            try:
                # 备选：使用 pytesseract
                return await self._tesseract_ocr(path)
            except ImportError:
                raise ImportError(
                    "PaddleOCR or pytesseract is required for OCR. "
                    "Install with: pip install paddlepaddle paddleocr"
                    "or: pip install pytesseract pillow"
                )

    async def _paddle_ocr(self, path: str) -> tuple:
        """使用 PaddleOCR 进行识别"""
        try:
            from paddleocr import PaddleOCR
            from PIL import Image

            # 初始化 OCR
            lang = "ch" if self._ocr_language == "ch" else "en"
            ocr = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)

            # 获取图片信息
            img = Image.open(path)
            width, height = img.size

            # 执行 OCR
            result = ocr.ocr(path, cls=True)

            # 提取文字
            text_lines = []
            text_boxes = []

            if result and result[0]:
                for line in result[0]:
                    if line and len(line) >= 2:
                        box = line[0]  # 文本框坐标
                        text = line[1][0]  # 识别的文字
                        confidence = line[1][1]  # 置信度
                        text_lines.append(text)
                        text_boxes.append({
                            "box": box,
                            "confidence": confidence,
                            "text": text
                        })

            full_text = "\n".join(text_lines)

            return full_text, {
                "file_type": "image",
                "image_size": {"width": width, "height": height},
                "ocr_engine": "paddleocr",
                "language": lang,
                "text_blocks": len(text_lines),
                "text_boxes": text_boxes[:5]  # 只保留前 5 个详细信息
            }
        except Exception as e:
            logger.error("PaddleOCR failed", extra={"error": str(e)})
            raise

    async def _tesseract_ocr(self, path: str) -> tuple:
        """使用 Tesseract OCR 进行识别"""
        try:
            import pytesseract
            from PIL import Image

            # 打开图片
            img = Image.open(path)
            width, height = img.size

            # 设置语言
            lang = "chi_sim+eng" if self._ocr_language == "ch" else "eng"

            # 执行 OCR
            full_text = pytesseract.image_to_string(img, lang=lang)

            # 获取详细数据
            data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)

            # 统计信息
            total_words = sum(1 for conf in data["conf"] if conf > 0)

            return full_text, {
                "file_type": "image",
                "image_size": {"width": width, "height": height},
                "ocr_engine": "tesseract",
                "language": lang,
                "word_count": total_words,
                "avg_confidence": sum(data["conf"]) / max(1, len([c for c in data["conf"] if c > 0]))
            }
        except Exception as e:
            logger.error("Tesseract OCR failed", extra={"error": str(e)})
            raise

    @staticmethod
    async def ocr_image(path: str, language: str = "ch") -> Dict[str, Any]:
        """静态方法：快速对图片进行 OCR"""
        config = UnstructuredConfig(
            name="temp_ocr",
            source_type="image",
            source_path=path,
            options={"language": language}
        )
        loader = ImageLoader(config)
        await loader.connect()
        chunks = await loader.load_content()
        await loader.disconnect()

        return {
            "text": "\n".join(chunk.content for chunk in chunks),
            "metadata": loader._metadata,
            "chunks": [chunk.to_dict() for chunk in chunks]
        }
