"""
P9-003: 高级搜索与筛选 API

API 端点:
- POST /api/marketplace/search - 高级搜索
- GET /api/marketplace/filters - 获取可用筛选条件
- POST /api/marketplace/save-search - 保存搜索条件
- GET /api/marketplace/saved-searches - 获取保存的搜索
"""

import logging
import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body
from datetime import datetime

from models.p9_models import (
    SearchRequest,
    SearchResponse,
    SearchResult,
    SavedSearch,
    SavedSearchResponse,
    SavedSearchListResponse,
    SortOrder,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/marketplace", tags=["高级搜索"])


# ==================== 模拟数据源 ====================

def _get_all_employees_for_search() -> List[Dict[str, Any]]:
    """获取所有员工数据用于搜索（模拟）"""
    return [
        {
            "id": "emp-001",
            "name": "数据分析助手",
            "avatar": "https://example.com/avatar1.png",
            "description": "专业的数据分析 AI 员工，擅长处理结构化数据",
            "skills": {
                "python": "advanced",
                "data_analysis": "expert",
                "sql": "intermediate",
                "visualization": "intermediate",
            },
            "categories": ["technical", "analysis"],
            "rating": 4.8,
            "review_count": 120,
            "hourly_rate": 50.0,
            "availability": "available",
        },
        {
            "id": "emp-002",
            "name": "NLP 专家",
            "avatar": "https://example.com/avatar2.png",
            "description": "自然语言处理专家，擅长文本分析和生成",
            "skills": {
                "python": "advanced",
                "nlp": "expert",
                "machine_learning": "advanced",
                "deep_learning": "intermediate",
            },
            "categories": ["technical", "ai_specialized"],
            "rating": 4.9,
            "review_count": 85,
            "hourly_rate": 80.0,
            "availability": "available",
        },
        {
            "id": "emp-003",
            "name": "全栈开发助手",
            "avatar": "https://example.com/avatar3.png",
            "description": "全栈开发 AI 员工，可处理前后端任务",
            "skills": {
                "javascript": "advanced",
                "python": "intermediate",
                "react": "advanced",
                "nodejs": "intermediate",
            },
            "categories": ["technical"],
            "rating": 4.7,
            "review_count": 200,
            "hourly_rate": 60.0,
            "availability": "hired",
        },
        {
            "id": "emp-004",
            "name": "UI 设计助手",
            "avatar": "https://example.com/avatar4.png",
            "description": "UI/UX 设计 AI 员工，擅长界面设计",
            "skills": {
                "design": "expert",
                "ui_design": "advanced",
                "ux_design": "advanced",
                "figma": "intermediate",
            },
            "categories": ["design"],
            "rating": 4.6,
            "review_count": 95,
            "hourly_rate": 55.0,
            "availability": "available",
        },
        {
            "id": "emp-005",
            "name": "内容写作助手",
            "avatar": "https://example.com/avatar5.png",
            "description": "专业内容写作 AI 员工，擅长文章撰写",
            "skills": {
                "writing": "expert",
                "editing": "advanced",
                "translation": "intermediate",
            },
            "categories": ["writing"],
            "rating": 4.5,
            "review_count": 150,
            "hourly_rate": 40.0,
            "availability": "available",
        },
        {
            "id": "emp-006",
            "name": "机器学习工程师",
            "avatar": "https://example.com/avatar6.png",
            "description": "机器学习专家，擅长模型训练和部署",
            "skills": {
                "python": "expert",
                "machine_learning": "expert",
                "pytorch": "advanced",
                "tensorflow": "advanced",
            },
            "categories": ["technical", "ai_specialized"],
            "rating": 4.9,
            "review_count": 60,
            "hourly_rate": 100.0,
            "availability": "available",
        },
    ]


# ==================== 内存存储 ====================

_saved_searches: Dict[str, SavedSearch] = {}


# ==================== 搜索核心逻辑 ====================

def _calculate_match_score(
    employee: Dict[str, Any],
    request: SearchRequest
) -> float:
    """
    计算匹配分数

    基于技能匹配、评分、价格等因素综合计算
    """
    score = 0.0
    weights = {
        "skill_match": 0.4,
        "category_match": 0.2,
        "rating": 0.2,
        "price_match": 0.1,
        "availability": 0.1,
    }

    # 技能匹配
    if request.skills:
        employee_skills = set(s.lower() for s in employee.get("skills", {}).keys())
        search_skills = set(s.lower() for s in request.skills)
        skill_overlap = len(employee_skills & search_skills)
        skill_match = skill_overlap / len(search_skills) if search_skills else 0
        score += weights["skill_match"] * skill_match * 100
    else:
        score += weights["skill_match"] * 50  # 无技能要求时给平均分

    # 类别匹配
    if request.categories:
        employee_categories = set(employee.get("categories", []))
        search_categories = set(c.lower() for c in request.categories)
        category_match = len(employee_categories & search_categories) > 0
        score += weights["category_match"] * (100 if category_match else 0)
    else:
        score += weights["category_match"] * 50

    # 评分匹配
    rating_score = (employee.get("rating", 0) / 5.0) * 100
    score += weights["rating"] * rating_score

    # 价格匹配（越便宜分数越高）
    if request.max_hourly_rate:
        if employee.get("hourly_rate", 0) <= request.max_hourly_rate:
            price_ratio = employee["hourly_rate"] / request.max_hourly_rate
            score += weights["price_match"] * (1 - price_ratio) * 100
        else:
            score += weights["price_match"] * 0  # 超出预算
    else:
        score += weights["price_match"] * 50

    # 可用性匹配
    if request.availability is not None:
        is_available = employee.get("availability") == "available"
        if request.availability == is_available:
            score += weights["availability"] * 100
        else:
            score += weights["availability"] * 0
    else:
        score += weights["availability"] * 50

    return min(100, score)  # 限制在 0-100


def _matches_filters(
    employee: Dict[str, Any],
    request: SearchRequest
) -> bool:
    """检查员工是否匹配所有筛选条件"""
    # 技能筛选
    if request.skills:
        employee_skills = set(s.lower() for s in employee.get("skills", {}).keys())
        if not any(s.lower() in employee_skills for s in request.skills):
            return False

    # 类别筛选
    if request.categories:
        employee_categories = employee.get("categories", [])
        if not any(c.lower() in employee_categories for c in request.categories):
            return False

    # 评分筛选
    if request.min_rating is not None:
        if employee.get("rating", 0) < request.min_rating:
            return False

    # 价格筛选
    if request.max_hourly_rate is not None:
        if employee.get("hourly_rate", 0) > request.max_hourly_rate:
            return False

    # 可用性筛选
    if request.availability is not None:
        is_available = employee.get("availability") == "available"
        if request.availability != is_available:
            return False

    return True


def _sort_results(
    results: List[Dict[str, Any]],
    request: SearchRequest
) -> List[Dict[str, Any]]:
    """对结果排序"""
    reverse = request.sort_order == SortOrder.DESC

    if request.sort_by == "rating":
        return sorted(results, key=lambda x: x.get("rating", 0), reverse=reverse)
    elif request.sort_by == "hourly_rate":
        return sorted(results, key=lambda x: x.get("hourly_rate", 0), reverse=reverse)
    elif request.sort_by == "review_count":
        return sorted(results, key=lambda x: x.get("review_count", 0), reverse=reverse)
    elif request.sort_by == "match_score":
        return sorted(results, key=lambda x: x.get("_match_score", 0), reverse=reverse)
    else:
        return results


# ==================== API 端点 ====================

@router.post("/search", response_model=SearchResponse)
async def search_employees(request: SearchRequest):
    """
    高级搜索 AI 员工

    支持多种筛选条件:
    - **keyword**: 关键词搜索（名称、描述）
    - **skills**: 技能筛选
    - **categories**: 类别筛选
    - **min_rating**: 最低评分
    - **max_hourly_rate**: 最高时薪
    - **availability**: 可用性筛选
    - **sort_by**: 排序字段
    - **sort_order**: 排序方向
    """
    try:
        all_employees = _get_all_employees_for_search()

        # 关键词搜索
        filtered = []
        for emp in all_employees:
            # 关键词匹配
            if request.keyword:
                keyword_lower = request.keyword.lower()
                name_match = keyword_lower in emp.get("name", "").lower()
                desc_match = keyword_lower in emp.get("description", "").lower()
                skill_match = any(keyword_lower in s.lower() for s in emp.get("skills", {}).keys())

                if not (name_match or desc_match or skill_match):
                    continue

            # 筛选条件匹配
            if not _matches_filters(emp, request):
                continue

            # 计算匹配分数
            match_score = _calculate_match_score(emp, request)
            emp_with_score = emp.copy()
            emp_with_score["_match_score"] = match_score

            filtered.append(emp_with_score)

        # 排序
        sorted_results = _sort_results(filtered, request)

        # 分页
        total = len(sorted_results)
        start = (request.page - 1) * request.page_size
        end = start + request.page_size
        paginated = sorted_results[start:end]

        # 转换为 SearchResult
        results = []
        for emp in paginated:
            matched_skills = []
            if request.skills:
                employee_skills = set(s.lower() for s in emp.get("skills", {}).keys())
                matched_skills = [s for s in request.skills if s.lower() in employee_skills]

            result = SearchResult(
                employee_id=emp["id"],
                employee_name=emp["name"],
                avatar=emp.get("avatar"),
                description=emp.get("description"),
                skills=emp.get("skills", {}),
                rating=emp.get("rating", 0),
                review_count=emp.get("review_count", 0),
                hourly_rate=emp.get("hourly_rate", 0),
                availability=emp.get("availability", "unknown"),
                match_score=round(emp.get("_match_score", 0), 2),
                matched_skills=matched_skills,
            )
            results.append(result)

        # 获取可用筛选条件
        filters = _get_available_filters(all_employees)

        return SearchResponse(
            success=True,
            results=results,
            total=total,
            page=request.page,
            page_size=request.page_size,
            filters=filters,
            message=f"找到 {total} 个匹配的 AI 员工"
        )
    except Exception as e:
        logger.error(f"搜索失败：{e}")
        raise HTTPException(status_code=500, detail=f"搜索失败：{str(e)}")


@router.get("/filters")
async def get_available_filters():
    """
    获取可用筛选条件

    返回所有可选的技能、类别、价格范围等
    """
    all_employees = _get_all_employees_for_search()
    filters = _get_available_filters(all_employees)

    return {
        "success": True,
        "filters": filters
    }


def _get_available_filters(employees: List[Dict[str, Any]]) -> Dict[str, Any]:
    """获取可用筛选条件"""
    # 技能统计
    skill_counts = {}
    for emp in employees:
        for skill in emp.get("skills", {}).keys():
            skill_counts[skill] = skill_counts.get(skill, 0) + 1

    # 类别统计
    category_counts = {}
    for emp in employees:
        for cat in emp.get("categories", []):
            category_counts[cat] = category_counts.get(cat, 0) + 1

    # 价格范围
    rates = [emp.get("hourly_rate", 0) for emp in employees]
    min_rate = min(rates) if rates else 0
    max_rate = max(rates) if rates else 0

    return {
        "skills": [
            {"name": skill, "count": count}
            for skill, count in sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
        ],
        "categories": [
            {"name": cat, "count": count}
            for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        ],
        "price_range": {
            "min": min_rate,
            "max": max_rate,
            "ranges": [
                {"label": f"${min_rate}-${min_rate + 20}", "count": sum(1 for r in rates if min_rate <= r <= min_rate + 20)},
                {"label": f"${min_rate + 20}-${min_rate + 50}", "count": sum(1 for r in rates if min_rate + 20 < r <= min_rate + 50)},
                {"label": f"${min_rate + 50}+", "count": sum(1 for r in rates if r > min_rate + 50)},
            ]
        },
        "rating_ranges": [
            {"label": "4.5+", "min": 4.5},
            {"label": "4.0+", "min": 4.0},
            {"label": "3.5+", "min": 3.5},
        ],
        "availability": [
            {"value": True, "label": "可用", "count": sum(1 for e in employees if e.get("availability") == "available")},
            {"value": False, "label": "被雇佣", "count": sum(1 for e in employees if e.get("availability") != "available")},
        ]
    }


@router.post("/save-search", response_model=SavedSearchResponse)
async def save_search(
    name: str = Body(..., description="搜索名称"),
    search_params: Dict[str, Any] = Body(..., description="搜索参数"),
    tenant_id: str = Body(..., description="租户 ID"),
    user_id: str = Body(..., description="用户 ID")
):
    """
    保存搜索条件

    用于后续快速执行相同的搜索
    """
    try:
        saved_search = SavedSearch(
            id=str(uuid.uuid4()),
            name=name,
            tenant_id=tenant_id,
            user_id=user_id,
            search_params=search_params,
            created_at=datetime.now(),
            last_executed_at=datetime.now()
        )

        _saved_searches[saved_search.id] = saved_search

        return SavedSearchResponse(
            success=True,
            saved_search=saved_search,
            message="搜索条件已保存"
        )
    except Exception as e:
        logger.error(f"保存搜索失败：{e}")
        raise HTTPException(status_code=500, detail=f"保存搜索失败：{str(e)}")


@router.get("/saved-searches", response_model=SavedSearchListResponse)
async def get_saved_searches(
    tenant_id: str = Query(..., description="租户 ID"),
    user_id: str = Query(..., description="用户 ID")
):
    """
    获取保存的搜索列表

    - **tenant_id**: 租户 ID
    - **user_id**: 用户 ID
    """
    try:
        saved = [
            s for s in _saved_searches.values()
            if s.tenant_id == tenant_id and s.user_id == user_id
        ]

        saved.sort(key=lambda x: x.created_at, reverse=True)

        return SavedSearchListResponse(
            success=True,
            saved_searches=saved,
            total=len(saved),
            message=f"找到 {len(saved)} 个保存的搜索"
        )
    except Exception as e:
        logger.error(f"获取保存的搜索失败：{e}")
        raise HTTPException(status_code=500, detail=f"获取保存的搜索失败：{str(e)}")


@router.delete("/saved-searches/{search_id}")
async def delete_saved_search(search_id: str):
    """
    删除保存的搜索

    - **search_id**: 保存的搜索 ID
    """
    if search_id not in _saved_searches:
        raise HTTPException(status_code=404, detail="保存的搜索不存在")

    del _saved_searches[search_id]

    return {"success": True, "message": "保存的搜索已删除"}
