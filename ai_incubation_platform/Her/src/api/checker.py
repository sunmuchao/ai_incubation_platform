"""
系统检查 API 路由

Skills 同步检查功能。
"""

from fastapi import APIRouter

from utils.skills_checker import SkillsChecker, get_skills_sync_report

router = APIRouter(prefix="/api/checker", tags=["系统检查"])


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