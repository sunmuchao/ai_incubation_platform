"""
API 注册检查工具

启动时验证所有定义的 API 路由都已注册，防止遗漏导致 404 错误。

使用方式：
    from utils.api_checker import check_api_registration

    # 在 main.py 启动时调用
    check_api_registration()
"""

import os
import re
import ast
from typing import Set, List, Tuple
from pathlib import Path

from utils.logger import logger


class APIChecker:
    """API 注册检查器"""

    def __init__(self, base_dir: str = None):
        """
        初始化检查器

        Args:
            base_dir: 项目根目录，默认为 src 目录的父目录
        """
        if base_dir is None:
            # 默认使用 src 目录
            current_file = os.path.abspath(__file__)
            self.base_dir = os.path.dirname(os.path.dirname(current_file))
        else:
            self.base_dir = base_dir

        self.api_dir = os.path.join(self.base_dir, 'api')
        self.routers_file = os.path.join(self.base_dir, 'routers', '__init__.py')

    def get_defined_routers(self) -> Set[str]:
        """
        获取所有定义的路由模块

        Returns:
            路由模块名称集合
        """
        defined = set()

        if not os.path.exists(self.api_dir):
            logger.warning(f"API directory not found: {self.api_dir}")
            return defined

        for filename in os.listdir(self.api_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                module_name = filename[:-3]  # 去掉 .py
                defined.add(module_name)

        logger.info(f"Found {len(defined)} API modules defined")
        return defined

    def get_registered_routers(self) -> Set[str]:
        """
        获取已注册的路由模块

        通过解析 routers/__init__.py 文件提取已注册的路由

        Returns:
            已注册的路由模块名称集合
        """
        registered = set()

        if not os.path.exists(self.routers_file):
            logger.warning(f"Routers file not found: {self.routers_file}")
            return registered

        with open(self.routers_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 匹配 import 语句中的模块名
        # 例如: from api.users import router as users_router
        import_pattern = r'from\s+api\.(\w+)\s+import'
        for match in re.finditer(import_pattern, content):
            registered.add(match.group(1))

        # 也匹配 services 目录中的路由
        # 例如: from services.scene_detection_service import router
        services_pattern = r'from\s+services\.(\w+)\s+import\s+router'
        for match in re.finditer(services_pattern, content):
            registered.add(f"services.{match.group(1)}")

        logger.info(f"Found {len(registered)} API modules registered")
        return registered

    def check_registration(self) -> Tuple[bool, List[str]]:
        """
        检查所有定义的路由是否都已注册

        Returns:
            (是否全部注册, 缺失的路由列表)
        """
        defined = self.get_defined_routers()
        registered = self.get_registered_routers()

        # 排除不需要注册的模块
        exclude_modules = {
            'errors',  # 错误处理模块
        }

        defined = defined - exclude_modules

        # 找出未注册的路由
        missing = defined - registered

        if missing:
            return False, list(missing)

        return True, []

    def generate_report(self) -> dict:
        """
        生成详细的检查报告

        Returns:
            检查报告字典
        """
        defined = self.get_defined_routers()
        registered = self.get_registered_routers()

        exclude_modules = {'errors'}
        defined = defined - exclude_modules

        missing = defined - registered
        extra = registered - defined

        return {
            'success': len(missing) == 0,
            'total_defined': len(defined),
            'total_registered': len(registered),
            'missing_routers': list(missing),
            'extra_routers': list(extra),
            'all_defined': list(defined),
            'all_registered': list(registered),
        }


def check_api_registration(raise_on_error: bool = False) -> bool:
    """
    检查 API 注册情况

    Args:
        raise_on_error: 是否在发现缺失时抛出异常

    Returns:
        是否全部注册
    """
    checker = APIChecker()
    success, missing = checker.check_registration()

    if success:
        logger.info("✅ All API routers are properly registered")
        return True
    else:
        error_msg = f"❌ Missing API router registrations: {missing}"
        logger.error(error_msg)

        if raise_on_error:
            raise RuntimeError(error_msg)

        return False


def get_api_checker_report() -> dict:
    """
    获取 API 检查报告

    Returns:
        检查报告字典
    """
    checker = APIChecker()
    return checker.generate_report()


# ========== FastAPI 路由（用于调试）==========

from fastapi import APIRouter

router = APIRouter(prefix="/api/checker", tags=["系统检查"])


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