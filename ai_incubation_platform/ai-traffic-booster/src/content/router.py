"""
内容优化 API 路由
"""
from fastapi import APIRouter
from schemas.content import (
    ContentOptimizationRequest,
    ContentOptimizationResult,
    ContentGenerationRequest,
    ContentGenerationResult
)
from schemas.common import Response
from core.response import success
from .service import content_service
from core.exceptions import BadRequestException, ContentTooLongException, ContentTooShortException
from core.config import settings

router = APIRouter(prefix="/content", tags=["内容优化"])


@router.post("/optimize", response_model=Response[ContentOptimizationResult])
async def optimize_content(request: ContentOptimizationRequest):
    """
    优化内容SEO质量和可读性
    - 智能调整关键词密度到合理范围
    - 优化内容结构和段落组织
    - 同义词替换提升内容丰富度
    - 自动补充内容长度
    - 提供详细的修改说明
    """
    if len(request.content.strip()) == 0:
        raise BadRequestException("内容不能为空")

    if not request.target_keywords or len(request.target_keywords) == 0:
        raise BadRequestException("目标关键词不能为空")

    if request.max_length and len(request.content) > request.max_length:
        raise ContentTooLongException(f"内容长度超过最大限制 {request.max_length} 字符")

    result = content_service.optimize_content(request)
    return success(data=result)


@router.post("/generate", response_model=Response[ContentGenerationResult])
async def generate_content(request: ContentGenerationRequest):
    """
    AI生成SEO友好的内容
    - 支持多种内容类型：文章、博客、产品描述、社交媒体文案等
    - 可自定义内容语气：专业、友好、 casual、权威等
    - 自动生成标题、大纲、正文、Meta描述
    - 内置SEO优化，保证内容符合搜索引擎要求
    - 生成内容自带SEO评分和优化建议
    """
    if len(request.topic.strip()) == 0:
        raise BadRequestException("内容主题不能为空")

    if not request.target_keywords or len(request.target_keywords) == 0:
        raise BadRequestException("目标关键词不能为空")

    if request.length < settings.MIN_CONTENT_LENGTH:
        raise ContentTooShortException(
            f"内容长度过短，必须 >= {settings.MIN_CONTENT_LENGTH} 字符"
        )
    if request.length > settings.MAX_CONTENT_LENGTH:
        raise ContentTooLongException(
            f"内容长度过长，必须 <= {settings.MAX_CONTENT_LENGTH} 字符"
        )

    result = content_service.generate_content(request)
    return success(data=result)
