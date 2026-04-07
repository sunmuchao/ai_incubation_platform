"""
演示数据初始化模块

用于初始化社区平台的演示数据
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)


async def init_demo_data(db: Optional[AsyncSession] = None):
    """
    初始化演示数据

    Args:
        db: 数据库会话（可选）

    Returns:
        None
    """
    logger.info("Demo data initialization skipped (stub implementation)")
    # Stub implementation - 演示数据初始化已跳过
    # 生产环境不应该使用演示数据
    pass


if __name__ == "__main__":
    import asyncio
    asyncio.run(init_demo_data())
