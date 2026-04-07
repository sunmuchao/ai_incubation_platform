"""
服务层基类
"""
from typing import TypeVar, Generic
from sqlalchemy.orm import Session
from config.logging_config import get_logger

T = TypeVar('T')


class BaseService:
    """服务基类"""

    def __init__(self, db: Session):
        """
        初始化服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self.logger = get_logger(self.__class__.__name__)
