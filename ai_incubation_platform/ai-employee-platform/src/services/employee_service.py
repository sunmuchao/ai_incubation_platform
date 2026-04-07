"""
AI 员工管理服务
负责 AI 员工的 CRUD 操作
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select

from models.db_models import (
    AIEmployeeDB, EmployeeStatusEnum, SkillLevelEnum, RiskLevelEnum
)
from config.database import get_db
from config.logging_config import get_logger


class EmployeeService:
    """AI 员工服务"""

    def __init__(self, db: Session = None):
        """
        初始化服务

        Args:
            db: 数据库会话（可选，为 None 时自动获取）
        """
        self._db = db
        self.logger = get_logger(self.__class__.__name__)

    @property
    def db(self) -> Session:
        """获取数据库会话"""
        if self._db is None:
            self._db = next(get_db())
        return self._db

    def create_employee(
        self,
        tenant_id: str,
        owner_id: str,
        name: str,
        description: str,
        skills: Dict[str, str] = None,
        hourly_rate: float = 10.0,
        agent_config: Dict[str, Any] = None
    ) -> AIEmployeeDB:
        """创建 AI 员工"""
        try:
            employee = AIEmployeeDB(
                tenant_id=tenant_id,
                owner_id=owner_id,
                name=name,
                description=description,
                skills=skills or {},
                hourly_rate=hourly_rate,
                agent_config=agent_config or {}
            )
            self.db.add(employee)
            self.db.commit()
            self.db.refresh(employee)
            self.logger.info(f"Created employee: {employee.id}, name: {name}")
            return employee
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to create employee: {str(e)}")
            raise

    def get_employee(self, employee_id: str) -> Optional[AIEmployeeDB]:
        """获取 AI 员工"""
        return self.db.query(AIEmployeeDB).filter(AIEmployeeDB.id == employee_id).first()

    def list_employees(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[EmployeeStatusEnum] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AIEmployeeDB]:
        """获取员工列表"""
        query = self.db.query(AIEmployeeDB)
        if tenant_id:
            query = query.filter(AIEmployeeDB.tenant_id == tenant_id)
        if status:
            query = query.filter(AIEmployeeDB.status == status)
        return query.offset(offset).limit(limit).all()

    def update_status(
        self,
        employee_id: str,
        status: EmployeeStatusEnum
    ) -> bool:
        """更新员工状态"""
        employee = self.get_employee(employee_id)
        if not employee:
            return False

        try:
            employee.status = status
            employee.updated_at = datetime.now()
            self.db.commit()
            self.logger.info(f"Updated employee {employee_id} status to {status.value}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to update employee status: {str(e)}")
            raise

    def update_employee(
        self,
        employee_id: str,
        **kwargs
    ) -> Optional[AIEmployeeDB]:
        """更新员工信息"""
        employee = self.get_employee(employee_id)
        if not employee:
            return None

        try:
            for key, value in kwargs.items():
                if hasattr(employee, key):
                    setattr(employee, key, value)
            employee.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(employee)
            return employee
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to update employee: {str(e)}")
            raise

    def search_employees(
        self,
        skill: str,
        min_rating: float = 0,
        tenant_id: Optional[str] = None
    ) -> List[AIEmployeeDB]:
        """搜索员工"""
        query = self.db.query(AIEmployeeDB).filter(
            AIEmployeeDB.status == EmployeeStatusEnum.AVAILABLE
        )
        if tenant_id:
            query = query.filter(AIEmployeeDB.tenant_id == tenant_id)

        employees = query.all()
        # 过滤技能和评分
        results = []
        for emp in employees:
            if skill in emp.skills and emp.rating >= min_rating:
                results.append(emp)
        return sorted(results, key=lambda e: e.rating, reverse=True)

    def delete_employee(self, employee_id: str) -> bool:
        """删除员工"""
        employee = self.get_employee(employee_id)
        if not employee:
            return False

        try:
            self.db.delete(employee)
            self.db.commit()
            self.logger.info(f"Deleted employee: {employee_id}")
            return True
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to delete employee: {str(e)}")
            raise


# 创建全局服务实例（延迟初始化 db）
employee_service = EmployeeService()
