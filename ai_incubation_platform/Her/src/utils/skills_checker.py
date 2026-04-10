"""
Skills 同步检查工具

启动时验证前端 Skills 定义与后端 Registry 一致，防止前后端不同步导致错误。

使用方式：
    from utils.skills_checker import check_skills_sync

    # 在 main.py 启动时调用
    check_skills_sync()
"""

import os
import re
import ast
from typing import Set, List, Tuple, Dict
from pathlib import Path

from utils.logger import logger


class SkillsChecker:
    """Skills 同步检查器"""

    def __init__(self, base_dir: str = None):
        """
        初始化检查器

        Args:
            base_dir: 项目根目录
        """
        if base_dir is None:
            current_file = os.path.abspath(__file__)
            self.base_dir = os.path.dirname(os.path.dirname(current_file))
        else:
            self.base_dir = base_dir

        self.skills_dir = os.path.join(self.base_dir, 'agent', 'skills')
        self.registry_file = os.path.join(self.skills_dir, 'registry.py')
        self.frontend_file = None

        # 尝试找到前端文件
        frontend_base = os.path.dirname(self.base_dir)
        possible_paths = [
            os.path.join(frontend_base, 'frontend', 'src', 'api', 'skillClient.ts'),
            os.path.join(frontend_base, 'Her', 'frontend', 'src', 'api', 'skillClient.ts'),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                self.frontend_file = path
                break

    def get_backend_skills(self) -> Set[str]:
        """
        获取后端注册的所有 Skills

        Returns:
            Skill 名称集合
        """
        skills = set()

        if not os.path.exists(self.registry_file):
            logger.warning(f"Registry file not found: {self.registry_file}")
            return skills

        with open(self.registry_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 匹配 registry.register() 调用
        # 方式1: registry.register(skill_instance, tags=[...])
        # 方式2: registry.register(get_xxx_skill(), tags=[...])

        # 匹配 tags 参数来确定 Skill 名称
        # 实际上我们需要从 skill 实例获取 name

        # 简化方法：查找所有 get_xxx_skill 函数调用
        pattern = r'registry\.register\(get_(\w+)_skill\(\)'
        for match in re.finditer(pattern, content):
            skill_name = match.group(1)
            # 转换为 camelCase
            parts = skill_name.split('_')
            camel_name = parts[0] + ''.join(p.capitalize() for p in parts[1:])
            skills.add(camel_name)

        # 也匹配直接传入实例的情况
        # registry.register(skill_instance, tags=[...])
        # 需要从 skill 实例的 name 属性获取

        logger.info(f"Found {len(skills)} Skills in backend registry")
        return skills

    def get_frontend_skills(self) -> Set[str]:
        """
        获取前端定义的所有 Skills

        Returns:
            Skill 名称集合
        """
        skills = set()

        if not self.frontend_file or not os.path.exists(self.frontend_file):
            logger.warning(f"Frontend skillClient.ts not found")
            return skills

        with open(self.frontend_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 匹配导出的 skills 对象
        # export const skills = { ... }
        # 或
        # export default skillRegistry 后面的 skills 对象

        # 查找 skills 对象定义
        pattern = r'(\w+):\s*\w+Skill'
        for match in re.finditer(pattern, content):
            skill_name = match.group(1)
            # 过滤掉注释行
            if '//' in content[:match.start()].split('\n')[-1]:
                continue
            skills.add(skill_name)

        logger.info(f"Found {len(skills)} Skills in frontend")
        return skills

    def check_sync(self) -> Tuple[bool, Dict[str, List[str]]]:
        """
        检查前后端 Skills 是否同步

        Returns:
            (是否同步, 差异报告)
        """
        backend_skills = self.get_backend_skills()
        frontend_skills = self.get_frontend_skills()

        # 前端有但后端没有（已删除）
        frontend_only = frontend_skills - backend_skills

        # 后端有但前端没有（新增未同步）
        backend_only = backend_skills - frontend_skills

        # 共同的
        common = frontend_skills & backend_skills

        is_sync = len(frontend_only) == 0 and len(backend_only) == 0

        report = {
            'frontend_only': list(frontend_only),  # 前端残留引用
            'backend_only': list(backend_only),    # 前端缺失引用
            'common': list(common),                # 同步的
            'frontend_total': len(frontend_skills),
            'backend_total': len(backend_skills),
        }

        return is_sync, report

    def generate_report(self) -> dict:
        """
        生成详细的同步检查报告

        Returns:
            检查报告字典
        """
        is_sync, report = self.check_sync()

        return {
            'success': is_sync,
            **report
        }


def check_skills_sync(raise_on_error: bool = False) -> bool:
    """
    检查前后端 Skills 同步情况

    Args:
        raise_on_error: 是否在发现不同步时抛出异常

    Returns:
        是否同步
    """
    checker = SkillsChecker()
    is_sync, report = checker.check_sync()

    if is_sync:
        logger.info(f"✅ Frontend and backend Skills are in sync ({report['common']} common skills)")
        return True
    else:
        issues = []

        if report['frontend_only']:
            issues.append(f"Frontend has deleted Skills: {report['frontend_only']}")

        if report['backend_only']:
            issues.append(f"Frontend missing Skills: {report['backend_only']}")

        error_msg = f"❌ Skills not in sync. {'; '.join(issues)}"
        logger.warning(error_msg)

        if raise_on_error:
            raise RuntimeError(error_msg)

        return False


def get_skills_sync_report() -> dict:
    """
    获取 Skills 同步检查报告

    Returns:
        检查报告字典
    """
    checker = SkillsChecker()
    return checker.generate_report()


# ========== FastAPI 路由（用于调试）==========

from fastapi import APIRouter

router = APIRouter(prefix="/api/checker", tags=["系统检查"])


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