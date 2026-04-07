"""
质量改进建议 API - 提供质量问题分析、改进建议生成和培训推荐功能。

功能端点:
1. 质量分析：分析交付内容的的质量问题
2. 改进建议：生成具体的改进建议
3. 培训推荐：推荐相关的培训资源
4. 趋势追踪：获取工人质量改进趋势
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from services.quality_improvement_service import (
    quality_improvement_service,
    QualityImprovementRequest,
    QualityIssueCategory,
    QualityIssueSeverity,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quality-improvement", tags=["quality_improvement"])


@router.post("/analyze")
async def analyze_quality(request: QualityImprovementRequest):
    """
    分析质量问题并生成改进建议。

    当交付被拒绝或质量评分较低时，调用此接口获取：
    - 详细的质量问题分析
    - 具体的改进建议
    - 推荐的培训资源

    **请求参数**:
    - task_id: 任务 ID
    - worker_id: 工人 ID
    - delivery_content: 交付内容
    - acceptance_criteria: 验收标准列表
    - rejection_reason: 拒绝原因（可选）
    - task_category: 任务类别

    **返回**:
    - quality_score: 质量得分 (0-1)
    - issues: 质量问题列表
    - suggestions: 改进建议列表
    - recommended_training: 推荐培训资源
    """
    response = quality_improvement_service.analyze_and_suggest(request)
    return {
        "success": response.success,
        "analysis_id": response.analysis_id,
        "quality_score": response.quality_score,
        "issues": [
            {
                "issue_id": issue.issue_id,
                "category": issue.category.value,
                "severity": issue.severity.value,
                "description": issue.description,
                "impact_score": issue.impact_score,
                "evidence": issue.evidence,
            }
            for issue in response.issues
        ],
        "suggestions": [
            {
                "suggestion_id": suggestion.suggestion_id,
                "title": suggestion.title,
                "description": suggestion.description,
                "priority": suggestion.priority,
                "estimated_effort": suggestion.estimated_effort,
                "action_items": suggestion.action_items,
            }
            for suggestion in response.suggestions
        ],
        "recommended_training": [
            {
                "resource_id": resource.resource_id,
                "title": resource.title,
                "type": resource.type,
                "duration_minutes": resource.duration_minutes,
                "difficulty": resource.difficulty,
                "relevant_skills": resource.relevant_skills,
            }
            for resource in response.recommended_training
        ],
        "message": response.message,
    }


@router.get("/analysis/{analysis_id}")
async def get_analysis(analysis_id: str):
    """
    获取质量分析记录详情。

    返回指定分析 ID 的完整记录。
    """
    record = quality_improvement_service.get_analysis(analysis_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Analysis not found: {analysis_id}")

    return {
        "analysis_id": record.analysis_id,
        "task_id": record.task_id,
        "worker_id": record.worker_id,
        "quality_score": record.quality_score,
        "issues": [
            {
                "category": issue.category.value,
                "severity": issue.severity.value,
                "description": issue.description,
            }
            for issue in record.issues
        ],
        "suggestions": [
            {
                "title": suggestion.title,
                "description": suggestion.description,
                "priority": suggestion.priority,
            }
            for suggestion in record.suggestions
        ],
        "improvements_made": record.improvements_made,
        "created_at": record.created_at.isoformat(),
    }


@router.get("/worker/{worker_id}/trend")
async def get_worker_quality_trend(worker_id: str):
    """
    获取工人质量改进趋势。

    返回工人的质量得分趋势分析。
    """
    trend = quality_improvement_service.get_worker_quality_trend(worker_id)
    return {"trend": trend}


@router.get("/worker/{worker_id}/history")
async def get_worker_quality_history(
    worker_id: str,
    limit: int = Query(20, description="返回记录数量限制"),
):
    """
    获取工人质量分析历史。

    返回工人最近的质量分析记录列表。
    """
    # 获取所有分析记录，筛选出该工人的
    all_records = quality_improvement_service._improvement_records.values()
    worker_records = [r for r in all_records if r.worker_id == worker_id]

    # 按创建时间降序排序
    worker_records.sort(key=lambda r: r.created_at, reverse=True)

    return {
        "worker_id": worker_id,
        "total_analyses": len(worker_records),
        "analyses": [
            {
                "analysis_id": r.analysis_id,
                "task_id": r.task_id,
                "quality_score": r.quality_score,
                "issue_count": len(r.issues),
                "created_at": r.created_at.isoformat(),
            }
            for r in worker_records[:limit]
        ],
    }


@router.get("/statistics")
async def get_improvement_statistics():
    """
    获取质量改进统计信息。

    返回平台整体的质量分析统计。
    """
    stats = quality_improvement_service.get_improvement_stats()
    return {"statistics": stats}


@router.get("/issue-categories")
async def list_issue_categories():
    """
    获取质量问题类别说明。

    返回所有质量问题类别的详细说明。
    """
    return {
        "categories": [
            {
                "category": "completeness",
                "name": "完整性不足",
                "description": "交付内容未回应所有验收标准，或缺少必要的交付物",
                "common_indicators": [
                    "未回应验收标准中的要求",
                    "交付内容过于简短",
                    "缺少必需的附件或文件",
                ],
                "typical_impact": "高 - 直接影响任务验收结果",
            },
            {
                "category": "accuracy",
                "name": "准确性问题",
                "description": "交付内容存在事实错误、数据不准确",
                "common_indicators": [
                    "数据或信息错误",
                    "答案与问题不匹配",
                    "明显的逻辑错误",
                ],
                "typical_impact": "严重 - 可能导致任务直接被拒绝",
            },
            {
                "category": "format",
                "name": "格式问题",
                "description": "交付内容的格式不符合要求",
                "common_indicators": [
                    "未按指定格式提交",
                    "缺乏基本结构（如分段、列表）",
                    "文件格式错误",
                ],
                "typical_impact": "中 - 可能影响验收体验",
            },
            {
                "category": "detail",
                "name": "详细度不足",
                "description": "交付内容过于简略，缺乏必要的细节",
                "common_indicators": [
                    "内容过于简短",
                    "缺乏数据支撑",
                    "没有解释说明",
                ],
                "typical_impact": "中 - 可能被认为敷衍了事",
            },
            {
                "category": "professionalism",
                "name": "专业性问题",
                "description": "表达方式不够专业、规范",
                "common_indicators": [
                    "使用口语化、随意的表达",
                    "拼写或语法错误",
                    "语气不当",
                ],
                "typical_impact": "低到中 - 影响专业形象",
            },
            {
                "category": "timeliness",
                "name": "及时性问题",
                "description": "未能在截止日期前交付",
                "common_indicators": [
                    "逾期交付",
                    "临近截止才提交",
                ],
                "typical_impact": "中 - 可能影响雇主后续安排",
            },
            {
                "category": "communication",
                "name": "沟通问题",
                "description": "与雇主的沟通不畅",
                "common_indicators": [
                    "未及时回复消息",
                    "未主动确认需求",
                    "未报告进度或问题",
                ],
                "typical_impact": "中 - 可能导致需求理解偏差",
            },
        ]
    }


@router.get("/issue-severities")
async def list_issue_severities():
    """获取问题严重程度说明。"""
    return {
        "severities": [
            {
                "level": "critical",
                "name": "严重",
                "description": "严重影响交付质量，通常导致任务被拒绝",
                "recommended_action": "立即优先修复",
            },
            {
                "level": "major",
                "name": "主要",
                "description": "显著影响交付质量，需要尽快修复",
                "recommended_action": "优先修复",
            },
            {
                "level": "minor",
                "name": "次要",
                "description": "对质量影响较小，可在后续改进",
                "recommended_action": "逐步改进",
            },
        ]
    }


@router.get("/suggestions")
async def list_suggestion_templates(
    category: Optional[str] = Query(None, description="按类别筛选"),
):
    """
    获取改进建议模板。

    返回预定义的改进建议模板。
    """
    templates = {
        "completeness": {
            "title": "提升内容完整性",
            "priority": "high",
            "action_items": [
                "在提交前对照验收标准逐一检查",
                "创建交付清单 (checklist) 确保无遗漏",
                "如有不确定，主动与雇主沟通确认",
            ],
        },
        "accuracy": {
            "title": "提高准确性",
            "priority": "high",
            "action_items": [
                "提交前进行至少一次全面复核",
                "对关键数据进行二次验证",
                "使用交叉验证方法确认答案",
            ],
        },
        "format": {
            "title": "改进格式规范",
            "priority": "medium",
            "action_items": [
                "仔细阅读格式要求",
                "使用分段、列表等方式组织内容",
                "参考优质交付样例的格式",
            ],
        },
        "detail": {
            "title": "增加内容详细度",
            "priority": "medium",
            "action_items": [
                "不仅提供答案，还要提供推理过程",
                "用具体数据和事实支撑结论",
                "适当提供背景和上下文信息",
            ],
        },
        "professionalism": {
            "title": "提升专业性",
            "priority": "medium",
            "action_items": [
                "避免使用口语化、随意的表达",
                "注意拼写和语法",
                "保持客观、中立的语气",
            ],
        },
    }

    if category:
        if category in templates:
            return {"template": templates[category]}
        else:
            raise HTTPException(status_code=400, detail=f"Unknown category: {category}")

    return {"templates": templates}


@router.get("/training-resources")
async def list_training_resources(
    difficulty: Optional[str] = Query(None, description="按难度筛选 (beginner/intermediate/advanced)"),
    resource_type: Optional[str] = Query(None, description="按类型筛选 (course/tutorial/guide)"),
):
    """
    获取培训资源列表。

    返回平台提供的所有培训资源。
    """
    resources = quality_improvement_service._training_resources

    # 筛选
    filtered = resources
    if difficulty:
        filtered = [r for r in filtered if r.difficulty == difficulty]
    if resource_type:
        filtered = [r for r in filtered if r.type == resource_type]

    return {
        "resources": [
            {
                "resource_id": r.resource_id,
                "title": r.title,
                "type": r.type,
                "duration_minutes": r.duration_minutes,
                "difficulty": r.difficulty,
                "relevant_skills": r.relevant_skills,
            }
            for r in filtered
        ],
        "total": len(filtered),
    }
