"""
P9-001: AI 员工能力图谱 API

API 端点:
- GET /api/ai-capability-graph - 获取全局能力图谱
- GET /api/ai-capability-graph/{employee_id} - 获取单个 AI 员工能力图谱
- GET /api/ai-capability-graph/similar/{employee_id} - 推荐相似 AI
- POST /api/ai-capability-graph/evolution-path - 获取进化路径建议
- GET /api/ai-capability-graph/industry-benchmark - 获取行业基准
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from models.p9_models import (
    CapabilityGraphResponse,
    SimilarEmployeesResponse,
    EvolutionPathResponse,
    IndustryBenchmarkResponse,
    EvolutionPathRequest,
)
from services.capability_graph_service import capability_graph_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-capability-graph", tags=["AI 能力图谱"])


# ==================== 模拟数据源 ====================
# 实际应从数据库获取

def _get_employee_data(employee_id: str) -> Optional[Dict[str, Any]]:
    """获取员工数据（模拟）"""
    # 这里应该从数据库查询
    employees_db = {
        "emp-001": {
            "id": "emp-001",
            "name": "数据分析助手",
            "skills": {
                "python": {"proficiency": 0.8},
                "data_analysis": {"proficiency": 0.9},
                "sql": {"proficiency": 0.7},
                "visualization": {"proficiency": 0.6},
                "machine_learning": {"proficiency": 0.5},
            },
            "training_history": [
                {"skill": "python", "completed_at": "2026-03-01T10:00:00"},
                {"skill": "data_analysis", "completed_at": "2026-03-05T10:00:00"},
            ],
            "usage_stats": {
                "python": {"count": 100, "success_rate": 0.95, "avg_time": 5.0},
                "data_analysis": {"count": 150, "success_rate": 0.92, "avg_time": 10.0},
            },
            "rating": 4.8,
            "hourly_rate": 50.0,
        },
        "emp-002": {
            "id": "emp-002",
            "name": "NLP 专家",
            "skills": {
                "python": {"proficiency": 0.7},
                "nlp": {"proficiency": 0.9},
                "machine_learning": {"proficiency": 0.8},
                "deep_learning": {"proficiency": 0.7},
                "pytorch": {"proficiency": 0.6},
            },
            "training_history": [
                {"skill": "nlp", "completed_at": "2026-02-15T10:00:00"},
                {"skill": "machine_learning", "completed_at": "2026-02-20T10:00:00"},
            ],
            "usage_stats": {
                "nlp": {"count": 200, "success_rate": 0.94, "avg_time": 8.0},
                "machine_learning": {"count": 80, "success_rate": 0.90, "avg_time": 15.0},
            },
            "rating": 4.9,
            "hourly_rate": 80.0,
        },
        "emp-003": {
            "id": "emp-003",
            "name": "全栈开发助手",
            "skills": {
                "javascript": {"proficiency": 0.85},
                "python": {"proficiency": 0.6},
                "react": {"proficiency": 0.8},
                "nodejs": {"proficiency": 0.7},
                "database": {"proficiency": 0.6},
            },
            "training_history": [
                {"skill": "javascript", "completed_at": "2026-01-10T10:00:00"},
                {"skill": "react", "completed_at": "2026-01-20T10:00:00"},
            ],
            "usage_stats": {
                "javascript": {"count": 300, "success_rate": 0.96, "avg_time": 3.0},
                "react": {"count": 250, "success_rate": 0.93, "avg_time": 5.0},
            },
            "rating": 4.7,
            "hourly_rate": 60.0,
        },
    }
    return employees_db.get(employee_id)


def _get_all_employees() -> List[Dict[str, Any]]:
    """获取所有员工数据（模拟）"""
    return [
        {
            "id": "emp-001",
            "name": "数据分析助手",
            "skills": {
                "python": {"proficiency": 0.8},
                "data_analysis": {"proficiency": 0.9},
                "sql": {"proficiency": 0.7},
            },
            "rating": 4.8,
            "hourly_rate": 50.0,
        },
        {
            "id": "emp-002",
            "name": "NLP 专家",
            "skills": {
                "python": {"proficiency": 0.7},
                "nlp": {"proficiency": 0.9},
                "machine_learning": {"proficiency": 0.8},
            },
            "rating": 4.9,
            "hourly_rate": 80.0,
        },
        {
            "id": "emp-003",
            "name": "全栈开发助手",
            "skills": {
                "javascript": {"proficiency": 0.85},
                "python": {"proficiency": 0.6},
                "react": {"proficiency": 0.8},
            },
            "rating": 4.7,
            "hourly_rate": 60.0,
        },
        {
            "id": "emp-004",
            "name": "UI 设计助手",
            "skills": {
                "design": {"proficiency": 0.9},
                "ui_design": {"proficiency": 0.85},
                "figma": {"proficiency": 0.8},
            },
            "rating": 4.6,
            "hourly_rate": 55.0,
        },
    ]


# ==================== API 端点 ====================

@router.get("", response_model=CapabilityGraphResponse)
async def get_global_capability_graph(
    employee_ids: Optional[List[str]] = Query(None, description="员工 ID 列表，为空则返回所有")
):
    """
    获取全局能力图谱

    - **employee_ids**: 可选，指定要包含的员工 ID 列表
    - 返回所有指定员工的能力图谱集合
    """
    try:
        all_ids = employee_ids or [emp["id"] for emp in _get_all_employees()]
        graphs = []

        for emp_id in all_ids:
            employee_data = _get_employee_data(emp_id)
            if employee_data:
                graph = capability_graph_service.build_graph(emp_id, employee_data)
                graphs.append(graph)

        return CapabilityGraphResponse(
            success=True,
            message=f"成功获取 {len(graphs)} 个能力图谱",
            graph=graphs[0] if len(graphs) == 1 else None
        )
    except Exception as e:
        logger.error(f"获取全局能力图谱失败：{e}")
        return CapabilityGraphResponse(
            success=False,
            message=f"获取能力图谱失败：{str(e)}"
        )


@router.get("/{employee_id}", response_model=CapabilityGraphResponse)
async def get_employee_capability_graph(employee_id: str):
    """
    获取单个 AI 员工能力图谱

    - **employee_id**: AI 员工 ID
    """
    try:
        # 检查是否已有缓存
        graph = capability_graph_service.get_graph(employee_id)

        if not graph:
            # 构建新图谱
            employee_data = _get_employee_data(employee_id)
            if not employee_data:
                return CapabilityGraphResponse(
                    success=False,
                    message=f"未找到员工：{employee_id}"
                )
            graph = capability_graph_service.build_graph(employee_id, employee_data)

        return CapabilityGraphResponse(
            success=True,
            graph=graph,
            message="成功获取能力图谱"
        )
    except Exception as e:
        logger.error(f"获取员工能力图谱失败：{employee_id}, error: {e}")
        return CapabilityGraphResponse(
            success=False,
            message=f"获取能力图谱失败：{str(e)}"
        )


@router.get("/similar/{employee_id}", response_model=SimilarEmployeesResponse)
async def get_similar_employees(
    employee_id: str,
    limit: int = Query(5, ge=1, le=20, description="返回数量限制")
):
    """
    推荐相似的 AI 员工

    基于能力图谱的相似度计算，返回最相似的 AI 员工

    - **employee_id**: 参考员工 ID
    - **limit**: 返回数量限制 (1-20)
    """
    try:
        # 确保参考员工有图谱
        employee_data = _get_employee_data(employee_id)
        if not employee_data:
            return SimilarEmployeesResponse(
                success=False,
                message=f"未找到员工：{employee_id}"
            )

        capability_graph_service.build_graph(employee_id, employee_data)

        # 获取所有员工
        all_employees = _get_all_employees()

        # 查找相似员工
        similar = capability_graph_service.find_similar_employees(
            employee_id,
            all_employees,
            limit
        )

        return SimilarEmployeesResponse(
            success=True,
            similar_employees=similar,
            message=f"找到 {len(similar)} 个相似员工"
        )
    except Exception as e:
        logger.error(f"查找相似员工失败：{e}")
        return SimilarEmployeesResponse(
            success=False,
            message=f"查找相似员工失败：{str(e)}"
        )


@router.post("/evolution-path", response_model=EvolutionPathResponse)
async def get_evolution_path(request: EvolutionPathRequest):
    """
    获取进化路径建议

    基于当前能力状态和目标角色，生成能力提升路径

    请求体:
    - **employee_id**: 员工 ID
    - **target_role**: 可选，目标角色 (如 data_scientist, nlp_engineer)
    - **budget**: 可选，训练预算
    - **timeline**: 可选，时间范围
    """
    try:
        employee_data = _get_employee_data(request.employee_id)
        if not employee_data:
            return EvolutionPathResponse(
                success=False,
                message=f"未找到员工：{request.employee_id}"
            )

        evolution_path = capability_graph_service.generate_evolution_path(
            request,
            employee_data
        )

        if not evolution_path:
            return EvolutionPathResponse(
                success=False,
                message="无法生成进化路径"
            )

        return EvolutionPathResponse(
            success=True,
            evolution_path=evolution_path,
            message="成功生成进化路径"
        )
    except Exception as e:
        logger.error(f"生成进化路径失败：{e}")
        return EvolutionPathResponse(
            success=False,
            message=f"生成进化路径失败：{str(e)}"
        )


@router.get("/industry-benchmark", response_model=IndustryBenchmarkResponse)
async def get_industry_benchmark(
    category: Optional[str] = Query(None, description="技能类别")
):
    """
    获取行业基准数据

    - **category**: 可选，技能类别 (technical, ai_specialized 等)
    """
    try:
        if category:
            benchmarks = capability_graph_service.get_industry_benchmark(category)
        else:
            # 返回所有类别
            all_benchmarks = []
            for cat in ["technical", "ai_specialized", "design", "writing"]:
                all_benchmarks.extend(capability_graph_service.get_industry_benchmark(cat))
            benchmarks = all_benchmarks

        return IndustryBenchmarkResponse(
            success=True,
            benchmarks=benchmarks,
            message="成功获取行业基准"
        )
    except Exception as e:
        logger.error(f"获取行业基准失败：{e}")
        return IndustryBenchmarkResponse(
            success=False,
            message=f"获取行业基准失败：{str(e)}"
        )


# ==================== 辅助端点 ====================

@router.get("/debug/relationships")
async def debug_skill_relationships():
    """
    调试端点：查看预定义的技能关系

    用于开发和测试
    """
    return {
        "success": True,
        "relationships": capability_graph_service._skill_relationships
    }
