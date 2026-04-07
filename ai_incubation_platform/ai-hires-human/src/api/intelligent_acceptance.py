"""
智能验收助手 API。

提供 AI 自动验收检查、验收报告查询等功能。
"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from models.intelligent_acceptance import (
    AcceptanceConfig,
    AcceptanceReport,
    AcceptanceRequest,
    AcceptanceResponse,
    CheckResult,
)
from services.intelligent_acceptance_service import intelligent_acceptance_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intelligent-acceptance", tags=["intelligent_acceptance"])


@router.post("/check", response_model=AcceptanceResponse)
async def check_acceptance(request: AcceptanceRequest):
    """
    执行智能验收检查。

    系统会自动分析交付内容是否符合验收标准，包括：
    - 语义相似度匹配
    - 关键词检查
    - 格式验证
    - 内容质量分析

    返回验收报告和建议（通过/拒绝/人工复核）。
    """
    if not request.acceptance_criteria:
        raise HTTPException(status_code=400, detail="验收标准不能为空")

    if not request.delivery_content:
        raise HTTPException(status_code=400, detail="交付内容不能为空")

    response = intelligent_acceptance_service.check_acceptance(request)
    return response


@router.get("/report/{report_id}", response_model=AcceptanceReport)
async def get_acceptance_report(report_id: str):
    """获取验收报告详情。"""
    report = intelligent_acceptance_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/task/{task_id}/reports", response_model=List[AcceptanceReport])
async def get_acceptance_reports_by_task(task_id: str):
    """获取任务的所有验收报告。"""
    reports = intelligent_acceptance_service.get_reports_by_task(task_id)
    return reports


@router.post("/config")
async def update_acceptance_config(config: AcceptanceConfig):
    """更新验收配置。"""
    intelligent_acceptance_service.config = config
    return {"message": "Configuration updated", "config": config.dict()}


@router.get("/config")
async def get_acceptance_config():
    """获取当前验收配置。"""
    return intelligent_acceptance_service.config


@router.get("/methods")
async def list_check_methods():
    """获取所有可用的检查方法说明。"""
    return {
        "check_methods": [
            {
                "name": "semantic_similarity",
                "type": "text_match",
                "description": "基于文本语义相似度匹配，比较交付内容与验收标准的语义相关性",
                "config": {"threshold": "相似度阈值 (0-1)，默认 0.75"},
            },
            {
                "name": "keyword_match",
                "type": "keyword_check",
                "description": "关键词匹配检查，验证交付内容是否包含必要的关键词",
                "config": {
                    "keywords": "关键词列表",
                    "match_all": "是否需要匹配所有关键词 (boolean)",
                },
            },
            {
                "name": "format_validation",
                "type": "format_check",
                "description": "格式验证，检查交付内容是否符合指定格式（JSON/XML/Markdown 等）",
                "config": {"format": "格式类型 (json/xml/markdown/email/url 等)"},
            },
            {
                "name": "image_verification",
                "type": "image_check",
                "description": "图片检查，验证交付的图片附件是否符合要求",
                "config": {
                    "min_quality": "最低质量要求 (low/medium/high)",
                    "required_objects": "必需包含的对象列表",
                },
            },
            {
                "name": "file_verification",
                "type": "file_check",
                "description": "文件检查，验证交付的文件附件是否完整",
                "config": {"required_file": "必需的文件名"},
            },
            {
                "name": "content_quality",
                "type": "custom",
                "description": "内容质量检查，分析内容的完整性、可读性和原创性",
                "config": {
                    "min_word_count": "最小字数要求",
                    "min_sentence_count": "最小句子数要求",
                    "max_repetition_ratio": "最大重复率",
                },
            },
        ]
    }


@router.post("/batch-check")
async def batch_check_acceptance(requests: List[AcceptanceRequest]):
    """
    批量执行验收检查。

    适用于需要同时验收多个交付内容的场景。
    """
    results = []
    for req in requests:
        try:
            response = intelligent_acceptance_service.check_acceptance(req)
            results.append({
                "task_id": req.task_id,
                "success": response.success,
                "report_id": response.report_id,
                "overall_result": response.overall_result.value,
                "recommendation": response.recommendation,
            })
        except Exception as e:
            results.append({
                "task_id": req.task_id,
                "success": False,
                "error": str(e),
            })

    return {"results": results, "total": len(requests)}
