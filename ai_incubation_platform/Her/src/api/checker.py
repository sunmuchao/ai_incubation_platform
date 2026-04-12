"""
系统检查 API 路由

合并 api_checker.py 和 skills_checker.py 的路由，
统一提供 API 注册检查和 Skills 同步检查功能。
"""

from fastapi import APIRouter

from utils.api_checker import APIChecker, get_api_checker_report
from utils.skills_checker import SkillsChecker, get_skills_sync_report

router = APIRouter(prefix="/api/checker", tags=["系统检查"])


# ========== API 注册检查 ==========

@router.get("/api-registration")
async def check_api_registration_endpoint():
    """检查 API 注册情况"""
    return get_api_checker_report()


@router.get("/defined-routers")
async def get_defined_routers_endpoint():
    """获取所有定义的路由"""
    checker = APIChecker()
    return {
        "success": True,
        "routers": list(checker.get_defined_routers())
    }


@router.get("/registered-routers")
async def get_registered_routers_endpoint():
    """获取所有已注册的路由"""
    checker = APIChecker()
    return {
        "success": True,
        "routers": list(checker.get_registered_routers())
    }


# ========== Skills 同步检查 ==========

@router.get("/skills-sync")
async def check_skills_sync_endpoint():
    """检查前后端 Skills 同步情况"""
    return get_skills_sync_report()


@router.get("/backend-skills")
async def get_backend_skills_endpoint():
    """获取后端所有 Skills"""
    checker = SkillsChecker()
    return {
        "success": True,
        "skills": list(checker.get_backend_skills())
    }


@router.get("/frontend-skills")
async def get_frontend_skills_endpoint():
    """获取前端所有 Skills"""
    checker = SkillsChecker()
    return {
        "success": True,
        "skills": list(checker.get_frontend_skills())
    }