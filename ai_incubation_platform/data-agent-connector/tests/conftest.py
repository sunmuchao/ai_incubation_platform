"""
pytest 配置文件
"""
import sys
import os
from pathlib import Path
import asyncio

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 加载测试环境变量
os.environ["ENVIRONMENT"] = "test"
os.environ["SECURITY__API_KEY"] = "test-api-key"


import pytest
from sqlalchemy import text


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """设置测试数据库，确保表已创建"""
    from config.database import db_manager

    # 异步初始化数据库
    async def init():
        await db_manager.init_db()

    asyncio.run(init())
    yield
