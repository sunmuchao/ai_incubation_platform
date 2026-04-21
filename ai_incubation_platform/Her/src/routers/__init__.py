"""
路由自动注册中心

使用自动扫描机制替代手动导入，减少维护成本。

自动扫描规则：
1. 扫描 api/*.py 所有文件
2. 提取所有以 'router' 开头的变量（router, router_xxx）
3. 自动注册到 FastAPI 应用

版本历史：
- v1.0.0: 手动导入（43 个路由文件，180+ 行代码）
- v2.0.0: 自动扫描注册（~50 行代码）
"""
from fastapi import FastAPI
import importlib
import pathlib
from typing import List

from utils.logger import logger


def discover_routers(api_dir: pathlib.Path) -> List[tuple]:
    """
    发现所有 API 路由器

    Args:
        api_dir: api 目录路径

    Returns:
        [(router_name, router_object), ...] 列表
    """
    routers = []

    for py_file in api_dir.glob("*.py"):
        # 排除 __init__.py 和非路由文件
        if py_file.name.startswith("_"):
            continue

        module_name = f"api.{py_file.stem}"

        try:
            module = importlib.import_module(module_name)

            # 提取所有以 'router' 开头的变量
            for attr_name in dir(module):
                if attr_name.startswith("router"):
                    router_obj = getattr(module, attr_name)
                    # 验证是否是 APIRouter
                    if hasattr(router_obj, "routes"):
                        routers.append((attr_name, router_obj))
                        logger.debug(f"[RouterDiscovery] 发现路由: {module_name}.{attr_name}")

        except Exception as e:
            logger.warning(f"[RouterDiscovery] 导入 {module_name} 失败: {e}")

    return routers


def register_all_routers(app: FastAPI) -> None:
    """
    自动注册所有路由到 FastAPI 应用

    使用自动扫描机制，无需手动维护导入列表
    """
    logger.info("[RouterRegistry] 开始自动扫描注册路由...")

    # 获取 api 目录路径
    api_dir = pathlib.Path(__file__).parent.parent / "api"

    if not api_dir.exists():
        logger.error(f"[RouterRegistry] API 目录不存在: {api_dir}")
        return

    # 发现所有路由器
    routers = discover_routers(api_dir)

    # 注册到应用
    registered_count = 0
    for router_name, router_obj in routers:
        try:
            app.include_router(router_obj)
            registered_count += 1
            logger.debug(f"[RouterRegistry] 注册成功: {router_name}")
        except Exception as e:
            logger.error(f"[RouterRegistry] 注册 {router_name} 失败: {e}")

    logger.info(f"[RouterRegistry] 路由自动注册完成，共 {registered_count} 个路由器")

    # 打印路由摘要（便于调试）
    _print_router_summary(app, registered_count)


def _print_router_summary(app: FastAPI, total_count: int) -> None:
    """打印路由摘要信息"""
    routes_by_prefix = {}

    for route in app.routes:
        if hasattr(route, "path"):
            prefix = route.path.split("/")[1] if route.path.count("/") >= 1 else "root"
            if prefix not in routes_by_prefix:
                routes_by_prefix[prefix] = 0
            routes_by_prefix[prefix] += 1

    logger.info(f"[RouterRegistry] 路由分布: {dict(sorted(routes_by_prefix.items()))}")


def get_api_endpoints_summary() -> dict:
    """获取 API 端点摘要（兼容旧接口）"""
    return {
        "core": "/api/users, /api/matching, /api/relationship",
        "social": "/api/chat, /api/photos, /api/activities",
        "membership": "/api/membership, /api/payment",
        "safety": "/api/identity, /api/verification",
        "ai_features": "/api/ai-companion, /api/skills",
        "milestone": "/api/milestones, /api/date-suggestions, /api/couple-games",
        "life_integration": "/api/autonomous-dating, /api/relationship-albums, /api/tribe",
        "ai_native": "/api/ai-awareness, /api/deerflow, /api/autonomous",
    }