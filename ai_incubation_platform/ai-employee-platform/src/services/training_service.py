"""
P4 训练数据版本化服务

提供:
- 训练数据版本管理
- 增量训练支持
- A/B 测试
- 版本回溯
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from collections import defaultdict
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

# 使用 db_models 中的模型定义，避免重复注册问题
from models.db_models import (
    Base,
    AIEmployeeDB,
    TenantDB,
)

# 从 p4_training_models 导入模型定义
from models.p4_training_models import (
    TrainingDataVersionDB,
    TrainingTaskDB,
    TrainingDatasetDB,
    TrainingJobDB,
    ABTestDB,
    TrainingStatus,
    TrainingDataSource,
)

# 注意：所有训练相关的 SQLAlchemy 模型已在 p4_training_models.py 中统一定义


class TrainingService:
    """训练数据版本化服务"""

    def __init__(self, db: Session):
        self.db = db

    # ============== 版本管理 ==============

    def create_version(
        self,
        employee_id: str,
        tenant_id: str,
        user_id: str,
        parent_version_id: Optional[str] = None,
        version_name: Optional[str] = None,
        training_config: Optional[Dict] = None,
        description: Optional[str] = None,
        changes: Optional[List[str]] = None
    ) -> TrainingDataVersionDB:
        """创建新的训练数据版本"""
        # 获取当前最大版本号
        max_version = self.db.query(func.max(TrainingDataVersionDB.version_number)).filter(
            TrainingDataVersionDB.employee_id == employee_id,
            TrainingDataVersionDB.is_deleted == False
        ).scalar() or 0

        version_id = str(uuid.uuid4())

        version = TrainingDataVersionDB(
            id=version_id,
            employee_id=employee_id,
            tenant_id=tenant_id,
            version_number=max_version + 1,
            version_name=version_name or f"v{max_version + 1}",
            parent_version_id=parent_version_id,
            training_config=training_config,
            description=description,
            changes=changes,
            created_by=user_id,
            training_status=TrainingStatus.PENDING,
            is_active=False
        )

        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)

        return version

    def get_version(self, version_id: str, tenant_id: str) -> Optional[TrainingDataVersionDB]:
        """获取版本详情"""
        return self.db.query(TrainingDataVersionDB).filter(
            TrainingDataVersionDB.id == version_id,
            TrainingDataVersionDB.tenant_id == tenant_id,
            TrainingDataVersionDB.is_deleted == False
        ).first()

    def list_versions(
        self,
        employee_id: str,
        tenant_id: str,
        limit: int = 50
    ) -> List[TrainingDataVersionDB]:
        """列出所有版本"""
        return self.db.query(TrainingDataVersionDB).filter(
            TrainingDataVersionDB.employee_id == employee_id,
            TrainingDataVersionDB.tenant_id == tenant_id,
            TrainingDataVersionDB.is_deleted == False
        ).order_by(desc(TrainingDataVersionDB.version_number)).limit(limit).all()

    def delete_version(self, version_id: str, tenant_id: str) -> bool:
        """删除版本（软删除）"""
        version = self.get_version(version_id, tenant_id)
        if not version:
            return False

        version.is_deleted = True
        self.db.commit()
        return True

    def activate_version(self, version_id: str, tenant_id: str) -> Optional[TrainingDataVersionDB]:
        """激活版本"""
        version = self.get_version(version_id, tenant_id)
        if not version:
            return None

        # 先停用当前激活的版本
        self.db.query(TrainingDataVersionDB).filter(
            TrainingDataVersionDB.employee_id == version.employee_id,
            TrainingDataVersionDB.tenant_id == tenant_id,
            TrainingDataVersionDB.is_active == True
        ).update({"is_active": False})

        # 激活目标版本
        version.is_active = True
        self.db.commit()
        self.db.refresh(version)

        return version

    def get_active_version(self, employee_id: str, tenant_id: str) -> Optional[TrainingDataVersionDB]:
        """获取当前激活的版本"""
        return self.db.query(TrainingDataVersionDB).filter(
            TrainingDataVersionDB.employee_id == employee_id,
            TrainingDataVersionDB.tenant_id == tenant_id,
            TrainingDataVersionDB.is_active == True,
            TrainingDataVersionDB.is_deleted == False
        ).first()

    # ============== 版本回溯 ==============

    def rollback_to_version(self, version_id: str, tenant_id: str, user_id: str) -> Optional[TrainingDataVersionDB]:
        """回滚到指定版本"""
        version = self.get_version(version_id, tenant_id)
        if not version:
            return None

        # 创建新版本（基于目标版本的快照）
        new_version = self.create_version(
            employee_id=version.employee_id,
            tenant_id=tenant_id,
            user_id=user_id,
            parent_version_id=version_id,
            version_name=f"rollback-to-{version.version_number}",
            description=f"回滚到版本 {version.version_number}",
            changes=[f"Rollback to version {version.version_number}"]
        )

        # 复制训练配置
        version.training_config = new_version.training_config
        self.db.commit()

        return self.activate_version(version_id, tenant_id)

    def compare_versions(
        self,
        version_a_id: str,
        version_b_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """比较两个版本的差异"""
        version_a = self.get_version(version_a_id, tenant_id)
        version_b = self.get_version(version_b_id, tenant_id)

        if not version_a or not version_b:
            return None

        # 比较指标
        def compare_metrics(metrics_a, metrics_b):
            if not metrics_a or not metrics_b:
                return None
            comparison = {}
            all_keys = set(metrics_a.keys()) | set(metrics_b.keys())
            for key in all_keys:
                val_a = metrics_a.get(key, 0)
                val_b = metrics_b.get(key, 0)
                if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                    diff = ((val_b - val_a) / val_a * 100) if val_a != 0 else 0
                    comparison[key] = {
                        "version_a": val_a,
                        "version_b": val_b,
                        "diff_percent": round(diff, 2)
                    }
            return comparison

        return {
            "version_a": {
                "id": version_a.id,
                "version_number": version_a.version_number,
                "training_metrics": version_a.training_metrics,
                "validation_metrics": version_a.validation_metrics,
                "test_metrics": version_a.test_metrics
            },
            "version_b": {
                "id": version_b.id,
                "version_number": version_b.version_number,
                "training_metrics": version_b.training_metrics,
                "validation_metrics": version_b.validation_metrics,
                "test_metrics": version_b.test_metrics
            },
            "metrics_comparison": compare_metrics(
                version_a.test_metrics or version_a.validation_metrics,
                version_b.test_metrics or version_b.validation_metrics
            ),
            "config_comparison": {
                "base_model": {
                    "version_a": version_a.base_model,
                    "version_b": version_b.base_model
                },
                "training_config": {
                    "version_a": version_a.training_config,
                    "version_b": version_b.training_config
                }
            }
        }

    # ============== 训练任务管理 ==============

    def create_training_job(
        self,
        version_id: str,
        tenant_id: str,
        user_id: str,
        job_name: str,
        job_type: str,
        training_config: Dict,
        resource_config: Optional[Dict] = None
    ) -> TrainingJobDB:
        """创建训练任务"""
        version = self.get_version(version_id, tenant_id)
        if not version:
            raise ValueError(f"Version {version_id} not found")

        job_id = str(uuid.uuid4())

        job = TrainingJobDB(
            id=job_id,
            version_id=version_id,
            employee_id=version.employee_id,
            tenant_id=tenant_id,
            job_name=job_name,
            job_type=job_type,
            training_config=training_config,
            resource_config=resource_config or {},
            status=TrainingStatus.PENDING,
            created_by=user_id
        )

        self.db.add(job)

        # 更新版本状态
        version.training_status = TrainingStatus.IN_PROGRESS
        version.training_started_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(job)

        return job

    def update_job_progress(
        self,
        job_id: str,
        tenant_id: str,
        progress_percent: int,
        current_step: Optional[str] = None,
        training_metrics: Optional[Dict] = None
    ) -> TrainingJobDB:
        """更新训练进度"""
        job = self.db.query(TrainingJobDB).filter(
            TrainingJobDB.id == job_id,
            TrainingJobDB.tenant_id == tenant_id
        ).first()

        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.progress_percent = min(100, max(0, progress_percent))
        if current_step:
            job.current_step = current_step
        if training_metrics:
            if job.training_metrics is None:
                job.training_metrics = {}
            job.training_metrics.update(training_metrics)

        self.db.commit()
        self.db.refresh(job)

        return job

    def complete_job(
        self,
        job_id: str,
        tenant_id: str,
        success: bool,
        final_metrics: Optional[Dict] = None,
        model_artifact_path: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> TrainingJobDB:
        """完成训练任务"""
        job = self.db.query(TrainingJobDB).filter(
            TrainingJobDB.id == job_id,
            TrainingJobDB.tenant_id == tenant_id
        ).first()

        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.completed_at = datetime.utcnow()
        job.status = TrainingStatus.COMPLETED if success else TrainingStatus.FAILED

        if success:
            job.final_metrics = final_metrics
            job.model_artifact_path = model_artifact_path

            # 更新版本信息
            version = self.db.query(TrainingDataVersionDB).filter(
                TrainingDataVersionDB.id == job.version_id
            ).first()
            if version:
                version.training_status = TrainingStatus.COMPLETED
                version.training_completed_at = job.completed_at
                version.training_duration_seconds = int(
                    (job.completed_at - job.started_at).total_seconds() if job.started_at else 0
                )
                version.training_metrics = final_metrics
                version.model_artifact_path = model_artifact_path
        else:
            job.error_message = error_message

        self.db.commit()
        self.db.refresh(job)

        return job

    # ============== A/B 测试 ==============

    def create_ab_test(
        self,
        employee_id: str,
        tenant_id: str,
        user_id: str,
        test_name: str,
        variant_a_version_id: str,
        variant_b_version_id: str,
        traffic_split_percent: int = 50,
        target_metric: Optional[str] = None,
        min_sample_size: int = 100,
        confidence_level: float = 0.95,
        description: Optional[str] = None
    ) -> ABTestDB:
        """创建 A/B 测试"""
        # 验证版本存在
        variant_a = self.get_version(variant_a_version_id, tenant_id)
        variant_b = self.get_version(variant_b_version_id, tenant_id)

        if not variant_a or not variant_b:
            raise ValueError("One or both versions not found")

        test_id = str(uuid.uuid4())

        test = ABTestDB(
            id=test_id,
            employee_id=employee_id,
            tenant_id=tenant_id,
            test_name=test_name,
            description=description,
            variant_a_version_id=variant_a_version_id,
            variant_b_version_id=variant_b_version_id,
            traffic_split_percent=traffic_split_percent,
            target_metric=target_metric,
            min_sample_size=min_sample_size,
            confidence_level=confidence_level,
            created_by=user_id
        )

        self.db.add(test)
        self.db.commit()
        self.db.refresh(test)

        return test

    def get_ab_test(self, test_id: str, tenant_id: str) -> Optional[ABTestDB]:
        """获取 A/B 测试详情"""
        return self.db.query(ABTestDB).filter(
            ABTestDB.id == test_id,
            ABTestDB.tenant_id == tenant_id
        ).first()

    def list_ab_tests(
        self,
        employee_id: str,
        tenant_id: str
    ) -> List[ABTestDB]:
        """列出 A/B 测试"""
        return self.db.query(ABTestDB).filter(
            ABTestDB.employee_id == employee_id,
            ABTestDB.tenant_id == tenant_id
        ).order_by(desc(ABTestDB.created_at)).all()

    def complete_ab_test(
        self,
        test_id: str,
        tenant_id: str,
        variant_a_metrics: Dict,
        variant_b_metrics: Dict,
        winner_version_id: str
    ) -> ABTestDB:
        """完成 A/B 测试"""
        test = self.get_ab_test(test_id, tenant_id)
        if not test:
            raise ValueError(f"AB test {test_id} not found")

        test.status = "completed"
        test.completed_at = datetime.utcnow()
        test.variant_a_metrics = variant_a_metrics
        test.variant_b_metrics = variant_b_metrics
        test.winner_version_id = winner_version_id

        self.db.commit()
        self.db.refresh(test)

        return test

    # ============== 版本 lineage ==============

    def get_version_lineage(self, version_id: str, tenant_id: str) -> Dict[str, Any]:
        """获取版本谱系（祖先和后代）"""
        version = self.get_version(version_id, tenant_id)
        if not version:
            return None

        # 获取祖先
        ancestors = []
        current = version
        while current and current.parent_version_id:
            parent = self.get_version(current.parent_version_id, tenant_id)
            if parent:
                ancestors.append({
                    "id": parent.id,
                    "version_number": parent.version_number,
                    "version_name": parent.version_name
                })
                current = parent
            else:
                break

        # 获取后代
        descendants = self.db.query(TrainingDataVersionDB).filter(
            TrainingDataVersionDB.parent_version_id == version_id,
            TrainingDataVersionDB.tenant_id == tenant_id,
            TrainingDataVersionDB.is_deleted == False
        ).all()

        return {
            "version": {
                "id": version.id,
                "version_number": version.version_number,
                "version_name": version.version_name
            },
            "ancestors": ancestors,
            "descendants": [
                {
                    "id": d.id,
                    "version_number": d.version_number,
                    "version_name": d.version_name
                }
                for d in descendants
            ]
        }
