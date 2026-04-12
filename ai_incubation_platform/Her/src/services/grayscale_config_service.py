"""
灰度配置服务 - A/B 测试与功能开关

核心功能：
- 功能开关（Feature Flags）
- A/B 测试分组
- 灰度比例控制
- 用户分组策略

设计参考：docs/PROGRESSIVE_SMART_MATCHING_SYSTEM.md
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
import hashlib

from sqlalchemy.orm import Session
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, JSON, Float
from sqlalchemy.sql import func

from services.base_service import BaseService
from db.models import (
    Base,
    FeatureFlagDB,
    ABExperimentDB,
    UserExperimentAssignmentDB,
)
from utils.db_session_manager import db_session
from utils.logger import logger


# ==================== 数据结构 ====================

@dataclass
class FeatureFlag:
    """功能开关"""
    flag_key: str
    name: str
    is_enabled: bool = False
    rollout_percentage: int = 0
    target_user_groups: List[str] = field(default_factory=list)
    config_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExperimentVariant:
    """实验变体"""
    name: str
    weight: int  # 权重百分比
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExperimentResult:
    """实验分组结果"""
    experiment_key: str
    variant_name: str
    config: Dict[str, Any]
    is_new_assignment: bool


# ==================== 灰度配置服务 ====================

class GrayscaleConfigService(BaseService[FeatureFlagDB]):
    """
    灰度配置服务

    核心能力：
    - 功能开关管理
    - 灰度比例控制
    - 用户分组策略
    - A/B 实验管理
    """

    def __init__(self, db: Session = None):
        super().__init__(db, FeatureFlagDB)

    def is_feature_enabled(
        self,
        flag_key: str,
        user_id: str,
        user_context: Dict[str, Any] = None
    ) -> bool:
        """
        检查功能是否对用户启用

        Args:
            flag_key: 功能开关标识
            user_id: 用户ID
            user_context: 用户上下文（城市、会员等级等）

        Returns:
            功能是否启用
        """
        with db_session() as db:
            flag = db.query(FeatureFlagDB).filter(
                FeatureFlagDB.flag_key == flag_key
            ).first()

            if not flag or not flag.is_enabled:
                return False

            # 检查时间范围
            now = datetime.now()
            if flag.start_time and now < flag.start_time:
                return False
            if flag.end_time and now > flag.end_time:
                return False

            # 检查用户群
            if flag.target_user_groups:
                user_group = user_context.get("user_group", "normal")
                if user_group not in flag.target_user_groups:
                    return False

            # 检查城市
            if flag.target_cities:
                user_city = user_context.get("city", "")
                if user_city and user_city not in flag.target_cities:
                    return False

            # 灰度比例检查
            if flag.rollout_percentage < 100:
                # 使用用户ID哈希进行分组
                hash_value = self._hash_user_id(user_id, flag_key)
                bucket = hash_value % 100
                return bucket < flag.rollout_percentage

            return True

    def get_feature_config(
        self,
        flag_key: str,
        user_id: str,
        user_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        获取功能配置（如果功能启用）
        """
        if not self.is_feature_enabled(flag_key, user_id, user_context):
            return {}

        with db_session() as db:
            flag = db.query(FeatureFlagDB).filter(
                FeatureFlagDB.flag_key == flag_key
            ).first()

            if flag:
                return flag.config_data or {}

            return {}

    def _hash_user_id(self, user_id: str, salt: str = "") -> int:
        """使用用户ID计算哈希值"""
        hash_str = f"{user_id}:{salt}"
        hash_value = int(hashlib.md5(hash_str.encode()).hexdigest()[:8], 16)
        return hash_value

    # ==================== A/B 实验管理 ====================

    def get_experiment_variant(
        self,
        experiment_key: str,
        user_id: str
    ) -> ExperimentResult:
        """
        获取用户在实验中的分组

        Args:
            experiment_key: 实验标识
            user_id: 用户ID

        Returns:
            ExperimentResult: 分组结果
        """
        with db_session() as db:
            # 1. 检查已有分组
            existing = db.query(UserExperimentAssignmentDB).filter(
                UserExperimentAssignmentDB.user_id == user_id,
                UserExperimentAssignmentDB.experiment_key == experiment_key,
                UserExperimentAssignmentDB.is_active == True
            ).first()

            if existing:
                # 获取变体配置
                experiment = db.query(ABExperimentDB).filter(
                    ABExperimentDB.experiment_key == experiment_key
                ).first()

                if experiment:
                    variant_config = self._get_variant_config(
                        experiment.variants, existing.variant_name
                    )
                    return ExperimentResult(
                        experiment_key=experiment_key,
                        variant_name=existing.variant_name,
                        config=variant_config,
                        is_new_assignment=False
                    )

            # 2. 新用户分组
            experiment = db.query(ABExperimentDB).filter(
                ABExperimentDB.experiment_key == experiment_key,
                ABExperimentDB.status == "running"
            ).first()

            if not experiment:
                return ExperimentResult(
                    experiment_key=experiment_key,
                    variant_name="control",
                    config={},
                    is_new_assignment=False
                )

            # 3. 计算分组
            variant_name = self._assign_variant(user_id, experiment.variants)
            variant_config = self._get_variant_config(experiment.variants, variant_name)

            # 4. 持久化分组
            import uuid
            assignment = UserExperimentAssignmentDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                experiment_key=experiment_key,
                variant_name=variant_name,
                is_active=True
            )
            db.add(assignment)
            db.commit()

            return ExperimentResult(
                experiment_key=experiment_key,
                variant_name=variant_name,
                config=variant_config,
                is_new_assignment=True
            )

    def _assign_variant(self, user_id: str, variants: List[Dict]) -> str:
        """根据权重分配变体"""
        hash_value = self._hash_user_id(user_id)
        bucket = hash_value % 100

        cumulative = 0
        for variant in variants:
            cumulative += variant.get("weight", 0)
            if bucket < cumulative:
                return variant.get("name", "control")

        return variants[-1].get("name", "control") if variants else "control"

    def _get_variant_config(self, variants: List[Dict], variant_name: str) -> Dict:
        """获取变体配置"""
        for variant in variants:
            if variant.get("name") == variant_name:
                return variant.get("config", {})
        return {}

    # ==================== 快速入门灰度配置 ====================

    def is_quick_start_enabled(self, user_id: str, user_context: Dict[str, Any] = None) -> bool:
        """
        检查快速入门功能是否对用户启用

        用于 A/B 测试对比：
        - A 组：走 QuickStart 流程
        - B 组：走原有 ProfileCollection 流程
        """
        return self.is_feature_enabled(
            flag_key="quick_start_flow",
            user_id=user_id,
            user_context=user_context
        )

    def get_quick_start_variant(self, user_id: str) -> str:
        """
        获取快速入门实验分组

        实验设计：
        - variant_a: 新的 QuickStart 流程（30秒入门）
        - variant_b: 原有 ProfileCollection 流程（完整问答）
        """
        result = self.get_experiment_variant(
            experiment_key="quick_start_ab_test",
            user_id=user_id
        )
        return result.variant_name


# ==================== 全局单例 ====================

_grayscale_config_service: Optional[GrayscaleConfigService] = None


def get_grayscale_config_service() -> GrayscaleConfigService:
    """获取灰度配置服务实例"""
    global _grayscale_config_service
    if _grayscale_config_service is None:
        _grayscale_config_service = GrayscaleConfigService()
    return _grayscale_config_service


# ==================== 初始化默认配置 ====================

DEFAULT_FEATURE_FLAGS = [
    {
        "flag_key": "quick_start_flow",
        "name": "快速入门流程",
        "description": "30秒快速入门 - 全量启用",
        "is_enabled": True,
        "rollout_percentage": 100,  # 100% 全量启用（无真实用户，直接全迁移）
        "target_user_groups": ["new_user"],
        "config_data": {
            "flow": "quick_start"  # 直接使用快速入门流程
        }
    },
    {
        "flag_key": "feedback_learning",
        "name": "反馈学习",
        "description": "不喜欢时追问原因并学习偏好",
        "is_enabled": True,
        "rollout_percentage": 100,  # 全量开放
        "target_user_groups": ["new_user", "normal"],
        "config_data": {}
    },
    {
        "flag_key": "behavior_tracking",
        "name": "行为追踪",
        "description": "隐性偏好推断功能",
        "is_enabled": True,
        "rollout_percentage": 100,  # 全量开放
        "target_user_groups": [],
        "config_data": {}
    },
]

# A/B 实验配置暂时不启用（无真实用户）
DEFAULT_AB_EXPERIMENTS = [
    {
        "experiment_key": "quick_start_ab_test",
        "name": "快速入门 A/B 测试",
        "description": "暂时禁用，全量使用快速入门流程",
        "status": "paused",  # 暂停状态
        "variants": [
            {"name": "variant_a", "weight": 100, "config": {"flow": "quick_start"}},
            {"name": "variant_b", "weight": 0, "config": {"flow": "profile_collection"}}
        ],
        "primary_metric": "first_day_retention",
        "secondary_metrics": ["completion_rate", "first_match_time", "first_interaction_time"],
        "traffic_allocation": 100
    }
]


async def init_default_feature_flags() -> None:
    """初始化默认功能开关配置"""
    import uuid

    with db_session() as db:
        for flag_data in DEFAULT_FEATURE_FLAGS:
            existing = db.query(FeatureFlagDB).filter(
                FeatureFlagDB.flag_key == flag_data["flag_key"]
            ).first()

            if not existing:
                flag = FeatureFlagDB(
                    id=str(uuid.uuid4()),
                    **flag_data
                )
                db.add(flag)

        db.commit()
        logger.info("Default feature flags initialized")


async def init_default_ab_experiments() -> None:
    """初始化默认 A/B 实验配置"""
    import uuid

    with db_session() as db:
        for exp_data in DEFAULT_AB_EXPERIMENTS:
            existing = db.query(ABExperimentDB).filter(
                ABExperimentDB.experiment_key == exp_data["experiment_key"]
            ).first()

            if not existing:
                experiment = ABExperimentDB(
                    id=str(uuid.uuid4()),
                    **exp_data
                )
                db.add(experiment)

        db.commit()
        logger.info("Default A/B experiments initialized")