"""
市场 API 路由
"""
from fastapi import APIRouter, Query
from typing import List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.employee import AIEmployee, EmployeeStatus, SkillLevel
from services.employee_service import employee_service

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])


@router.get("/employees", response_model=List[AIEmployee])
async def list_marketplace_employees(
    status: Optional[EmployeeStatus] = EmployeeStatus.AVAILABLE,
    min_rating: Optional[float] = Query(0, ge=0, le=5),
    max_hourly_rate: Optional[float] = None,
    skill: Optional[str] = None,
    skill_level: Optional[SkillLevel] = None
):
    """浏览市场上的AI员工"""
    employees = employee_service.list_employees(status)

    # 过滤条件
    filtered = []
    for emp in employees:
        # 最低评分过滤
        if emp.rating < min_rating:
            continue

        # 最高时薪过滤
        if max_hourly_rate and emp.hourly_rate > max_hourly_rate:
            continue

        # 技能过滤
        if skill:
            if skill not in emp.skills:
                continue
            if skill_level and emp.skills[skill] != skill_level:
                continue

        filtered.append(emp)

    # 按评分降序排序
    return sorted(filtered, key=lambda e: e.rating, reverse=True)


@router.get("/search", response_model=List[AIEmployee])
async def search_marketplace(
    keyword: str,
    min_rating: Optional[float] = Query(0, ge=0, le=5),
    max_hourly_rate: Optional[float] = None
):
    """搜索市场上的AI员工"""
    all_employees = employee_service.list_employees(EmployeeStatus.AVAILABLE)
    keyword = keyword.lower()

    results = []
    for emp in all_employees:
        # 搜索匹配：名称、描述、技能名称
        match = (
            keyword in emp.name.lower() or
            keyword in emp.description.lower() or
            any(keyword in skill.lower() for skill in emp.skills.keys())
        )

        if match and emp.rating >= min_rating:
            if not max_hourly_rate or emp.hourly_rate <= max_hourly_rate:
                results.append(emp)

    # 按评分降序排序
    return sorted(results, key=lambda e: e.rating, reverse=True)
