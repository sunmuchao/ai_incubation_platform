"""
数据治理服务

实现：
1. 数据分类管理
2. 数据标签管理
3. 敏感数据识别
4. 脱敏策略执行
5. 治理指标统计
6. 治理仪表板
"""
import asyncio
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from sqlalchemy import select, desc, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import db_manager
from models.data_governance import (
    DataClassificationModel,
    DataLabelModel,
    SensitivityLevelModel,
    MaskingPolicyModel,
    GovernanceMetricModel,
    SensitiveDataRecordModel
)
from models.data_quality import QualityRuleModel, QualityResultModel
from models.lineage_db import LineageNodeModel, LineageEdgeModel
from utils.logger import logger


class SensitivityLevel(str, Enum):
    """敏感级别枚举"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class LabelType(str, Enum):
    """标签类型枚举"""
    CLASSIFICATION = "classification"
    SENSITIVITY = "sensitivity"
    BUSINESS = "business"
    CUSTOM = "custom"


class MaskingType(str, Enum):
    """脱敏类型枚举"""
    FULL = "full"
    PARTIAL = "partial"
    HASH = "hash"
    ENCRYPT = "encrypt"
    REDACT = "redact"


# 敏感数据识别模式
SENSITIVE_PATTERNS = {
    "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    "phone_cn": r"^1[3-9]\d{9}$",
    "phone_us": r"^\+?1?\s*\(?[0-9]{3}\)?[\s.-]?[0-9]{3}[\s.-]?[0-9]{4}$",
    "ssn": r"^\d{3}-\d{2}-\d{4}$",
    "credit_card": r"^\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}$",
    "bank_account_cn": r"^\d{16,19}$",
    "id_card_cn": r"^\d{17}[\dXx]$",
    "passport": r"^[A-Z0-9]{6,9}$",
    "ip_address": r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",
    "mac_address": r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$",
    "crypto_wallet": r"^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$|^(bc1|0x)[a-zA-Z0-9]{30,40}$",
}

# 敏感列名关键词
SENSITIVE_KEYWORDS = {
    "email": ["email", "mail", "e_mail", "电子邮件"],
    "phone": ["phone", "tel", "mobile", "cell", "电话", "手机"],
    "ssn": ["ssn", "social_security", "社保"],
    "credit_card": ["credit_card", "card_no", "card_number", "信用卡", "银行卡号"],
    "bank_account": ["bank_account", "account_no", "银行账号"],
    "id_card": ["id_card", "identity_card", "身份证"],
    "passport": ["passport", "护照"],
    "address": ["address", "addr", "地址"],
    "name": ["name", "姓名", "用户名"],
    "password": ["password", "passwd", "pwd", "密码"],
    "salary": ["salary", "income", "wage", "工资", "薪水"],
    "birthday": ["birthday", "birth", "dob", "birth_date", "生日", "出生"],
    "gender": ["gender", "sex", "性别"],
}


class DataGovernanceService:
    """数据治理服务"""

    def __init__(self):
        self._initialized = False
        self._sensitivity_patterns_cache: Dict[str, re.Pattern] = {}

    async def initialize(self):
        """初始化服务"""
        self._initialized = True
        # 预编译敏感数据识别模式
        for pattern_type, pattern in SENSITIVE_PATTERNS.items():
            self._sensitivity_patterns_cache[pattern_type] = re.compile(pattern, re.IGNORECASE)
        logger.info("Data governance service initialized")

    async def close(self):
        """关闭服务"""
        self._initialized = False
        self._sensitivity_patterns_cache.clear()

    # ==================== 数据分类管理 ====================

    async def create_classification(
        self,
        name: str,
        description: str = None,
        parent_id: str = None,
        level: int = 1,
        tags: List[str] = None,
        created_by: str = None
    ) -> str:
        """创建数据分类"""
        async with db_manager.get_async_session() as session:
            classification = DataClassificationModel(
                name=name,
                description=description,
                parent_id=parent_id,
                level=level,
                tags=tags or [],
                created_by=created_by
            )
            session.add(classification)
            await session.flush()
            logger.info(f"Created data classification: {name}")
            return classification.id

    async def get_classification(self, classification_id: str) -> Optional[DataClassificationModel]:
        """获取分类详情"""
        async with db_manager.get_async_session() as session:
            result = await session.execute(
                select(DataClassificationModel).where(
                    DataClassificationModel.id == classification_id
                )
            )
            return result.scalar_one_or_none()

    async def list_classifications(
        self,
        parent_id: str = None,
        level: int = None,
        is_active: bool = True
    ) -> List[DataClassificationModel]:
        """列出分类"""
        async with db_manager.get_async_session() as session:
            conditions = [DataClassificationModel.is_active == is_active]
            if parent_id:
                conditions.append(DataClassificationModel.parent_id == parent_id)
            if level:
                conditions.append(DataClassificationModel.level == level)

            result = await session.execute(
                select(DataClassificationModel)
                .where(and_(*conditions))
                .order_by(DataClassificationModel.level, DataClassificationModel.name)
            )
            return list(result.scalars().all())

    async def get_classification_tree(self) -> List[Dict[str, Any]]:
        """获取分类树"""
        async with db_manager.get_async_session() as session:
            result = await session.execute(
                select(DataClassificationModel)
                .where(DataClassificationModel.is_active == True)
                .order_by(DataClassificationModel.level, DataClassificationModel.name)
            )
            classifications = list(result.scalars().all())

        # 构建树形结构
        tree = []
        by_id = {c.id: {**c.to_dict(), "children": []} for c in classifications}

        for c in classifications:
            if c.parent_id and c.parent_id in by_id:
                by_id[c.parent_id]["children"].append(by_id[c.id])
            else:
                tree.append(by_id[c.id])

        return tree

    async def delete_classification(self, classification_id: str) -> bool:
        """删除分类"""
        async with db_manager.get_async_session() as session:
            result = await session.execute(
                select(DataClassificationModel).where(
                    DataClassificationModel.id == classification_id
                )
            )
            classification = result.scalar_one_or_none()
            if classification:
                await session.delete(classification)
                return True
            return False

    # ==================== 数据标签管理 ====================

    async def add_label(
        self,
        datasource: str,
        table_name: str,
        label_type: str,
        label_key: str,
        label_value: str = None,
        column_name: str = None,
        source: str = "manual",
        confidence: float = None,
        created_by: str = None
    ) -> str:
        """添加数据标签"""
        async with db_manager.get_async_session() as session:
            label = DataLabelModel(
                datasource=datasource,
                table_name=table_name,
                column_name=column_name,
                label_type=label_type,
                label_key=label_key,
                label_value=label_value,
                source=source,
                confidence=confidence,
                created_by=created_by
            )
            session.add(label)
            await session.flush()
            logger.info(f"Added data label: {label_key}={label_value} on {datasource}.{table_name}")
            return label.id

    async def get_labels(
        self,
        datasource: str = None,
        table_name: str = None,
        column_name: str = None,
        label_type: str = None
    ) -> List[DataLabelModel]:
        """获取标签列表"""
        async with db_manager.get_async_session() as session:
            conditions = [DataLabelModel.is_active == True]
            if datasource:
                conditions.append(DataLabelModel.datasource == datasource)
            if table_name:
                conditions.append(DataLabelModel.table_name == table_name)
            if column_name:
                conditions.append(DataLabelModel.column_name == column_name)
            if label_type:
                conditions.append(DataLabelModel.label_type == label_type)

            result = await session.execute(
                select(DataLabelModel).where(and_(*conditions))
            )
            return list(result.scalars().all())

    async def remove_label(self, label_id: str) -> bool:
        """移除标签"""
        async with db_manager.get_async_session() as session:
            result = await session.execute(
                select(DataLabelModel).where(DataLabelModel.id == label_id)
            )
            label = result.scalar_one_or_none()
            if label:
                label.is_active = False
                return True
            return False

    # ==================== 敏感级别管理 ====================

    async def create_sensitivity_level(
        self,
        name: str,
        level: int,
        description: str = None,
        color: str = None,
        encryption_required: bool = False,
        masking_required: bool = False,
        audit_required: bool = True,
        access_control: str = "rbac",
        created_by: str = None
    ) -> str:
        """创建敏感级别"""
        async with db_manager.get_async_session() as session:
            sensitivity = SensitivityLevelModel(
                name=name,
                level=level,
                description=description,
                color=color,
                encryption_required=encryption_required,
                masking_required=masking_required,
                audit_required=audit_required,
                access_control=access_control,
                created_by=created_by
            )
            session.add(sensitivity)
            await session.flush()
            return sensitivity.id

    async def list_sensitivity_levels(self) -> List[SensitivityLevelModel]:
        """获取敏感级别列表"""
        async with db_manager.get_async_session() as session:
            result = await session.execute(
                select(SensitivityLevelModel)
                .where(SensitivityLevelModel.is_active == True)
                .order_by(SensitivityLevelModel.level)
            )
            return list(result.scalars().all())

    # ==================== 敏感数据识别 ====================

    async def scan_sensitive_data(
        self,
        datasource: str,
        table_name: str,
        columns: List[str] = None,
        sample_size: int = 1000
    ) -> List[Dict[str, Any]]:
        """扫描敏感数据"""
        start_time = time.time()
        results = []

        try:
            from connectors.database import DatabaseConnector
            connector = DatabaseConnector(datasource)
            await connector.connect()

            # 获取列信息
            if not columns:
                col_info = await connector.get_columns(table_name)
                columns = [col["name"] for col in col_info]

            # 逐列扫描
            for column in columns:
                detection_result = await self._detect_column_sensitivity(
                    datasource=datasource,
                    table_name=table_name,
                    column_name=column,
                    connector=connector,
                    sample_size=sample_size
                )
                if detection_result:
                    results.append(detection_result)

            await connector.disconnect()

            # 保存检测结果
            await self._save_sensitive_records(results)

            logger.info(f"Scanned {len(columns)} columns, found {len(results)} sensitive columns")
            return results

        except Exception as e:
            logger.error(f"Sensitive data scan failed: {e}")
            return []

    async def _detect_column_sensitivity(
        self,
        datasource: str,
        table_name: str,
        column_name: str,
        connector: Any,
        sample_size: int
    ) -> Optional[Dict[str, Any]]:
        """检测列的敏感性"""
        try:
            # 1. 基于列名关键词识别
            sensitivity_from_name = self._match_sensitive_keywords(column_name)

            # 2. 采样数据进行模式匹配
            samples = await self._get_column_samples(connector, table_name, column_name, sample_size)
            sensitivity_from_data = self._match_sensitive_patterns(samples)

            # 3. 综合判断
            combined_sensitivity = self._combine_sensitivity_results(
                sensitivity_from_name,
                sensitivity_from_data
            )

            if combined_sensitivity:
                return {
                    "datasource": datasource,
                    "table_name": table_name,
                    "column_name": column_name,
                    **combined_sensitivity
                }

            return None

        except Exception as e:
            logger.error(f"Column sensitivity detection failed: {e}")
            return None

    def _match_sensitive_keywords(self, column_name: str) -> Optional[Dict[str, Any]]:
        """基于列名关键词匹配敏感度"""
        column_lower = column_name.lower()

        for pattern_type, keywords in SENSITIVE_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in column_lower:
                    return {
                        "sensitivity_level": self._get_sensitivity_for_type(pattern_type),
                        "sensitivity_score": 0.7,
                        "detection_method": "keyword",
                        "pattern_type": pattern_type,
                        "confidence": 0.7
                    }

        return None

    def _match_sensitive_patterns(self, samples: List[str]) -> Optional[Dict[str, Any]]:
        """基于数据模式匹配敏感度"""
        if not samples:
            return None

        # 统计每种模式的匹配数
        pattern_matches = {}
        for sample in samples:
            if not sample:
                continue
            for pattern_type, pattern in self._sensitivity_patterns_cache.items():
                if pattern.match(str(sample).strip()):
                    pattern_matches[pattern_type] = pattern_matches.get(pattern_type, 0) + 1

        # 找出匹配最多的模式
        if pattern_matches:
            best_match = max(pattern_matches.items(), key=lambda x: x[1])
            match_ratio = best_match[1] / len(samples)

            if match_ratio > 0.5:  # 超过 50% 的数据匹配
                return {
                    "sensitivity_level": self._get_sensitivity_for_type(best_match[0]),
                    "sensitivity_score": match_ratio,
                    "detection_method": "pattern",
                    "pattern_type": best_match[0],
                    "confidence": min(0.95, match_ratio + 0.2)
                }

        return None

    def _combine_sensitivity_results(
        self,
        name_result: Optional[Dict],
        data_result: Optional[Dict]
    ) -> Optional[Dict]:
        """综合命名和数据匹配结果"""
        if not name_result and not data_result:
            return None

        if name_result and data_result:
            # 两者都匹配，取最高置信度
            if name_result.get("pattern_type") == data_result.get("pattern_type"):
                # 同一类型，取平均置信度
                avg_confidence = (name_result["confidence"] + data_result["confidence"]) / 2
                return {
                    "sensitivity_level": name_result["sensitivity_level"],
                    "sensitivity_score": max(name_result["sensitivity_score"], data_result["sensitivity_score"]),
                    "detection_method": "hybrid",
                    "pattern_type": name_result["pattern_type"],
                    "confidence": avg_confidence
                }
            else:
                # 不同类型，取置信度高的
                return name_result if name_result["confidence"] > data_result["confidence"] else data_result

        return name_result or data_result

    def _get_sensitivity_for_type(self, pattern_type: str) -> str:
        """根据敏感类型获取敏感级别"""
        high_sensitivity = {"ssn", "credit_card", "bank_account", "id_card", "password"}
        medium_sensitivity = {"email", "phone", "passport", "address", "salary"}

        if pattern_type in high_sensitivity:
            return SensitivityLevel.CONFIDENTIAL.value
        elif pattern_type in medium_sensitivity:
            return SensitivityLevel.INTERNAL.value
        return SensitivityLevel.PUBLIC.value

    async def _get_column_samples(
        self,
        connector: Any,
        table_name: str,
        column_name: str,
        sample_size: int
    ) -> List[str]:
        """获取列样本数据"""
        try:
            rows = await connector.execute_query(
                f"SELECT DISTINCT `{column_name}` FROM {table_name} WHERE `{column_name}` IS NOT NULL LIMIT {sample_size}"
            )
            return [str(row.get(column_name, "")) for row in rows] if rows else []
        except:
            return []

    async def _save_sensitive_records(self, results: List[Dict[str, Any]]):
        """保存敏感数据记录"""
        async with db_manager.get_async_session() as session:
            for result in results:
                record = SensitiveDataRecordModel(
                    datasource=result["datasource"],
                    table_name=result["table_name"],
                    column_name=result["column_name"],
                    sensitivity_level=result["sensitivity_level"],
                    sensitivity_score=result["sensitivity_score"],
                    detection_method=result["detection_method"],
                    pattern_type=result.get("pattern_type"),
                    confidence=result.get("confidence")
                )
                session.add(record)

    async def get_sensitive_records(
        self,
        datasource: str = None,
        table_name: str = None,
        sensitivity_level: str = None,
        is_masked: bool = None,
        is_reviewed: bool = None,
        limit: int = 100
    ) -> List[SensitiveDataRecordModel]:
        """获取敏感数据记录"""
        async with db_manager.get_async_session() as session:
            conditions = []
            if datasource:
                conditions.append(SensitiveDataRecordModel.datasource == datasource)
            if table_name:
                conditions.append(SensitiveDataRecordModel.table_name == table_name)
            if sensitivity_level:
                conditions.append(SensitiveDataRecordModel.sensitivity_level == sensitivity_level)
            if is_masked is not None:
                conditions.append(SensitiveDataRecordModel.is_masked == is_masked)
            if is_reviewed is not None:
                conditions.append(SensitiveDataRecordModel.is_reviewed == is_reviewed)

            query = select(SensitiveDataRecordModel)
            if conditions:
                query = query.where(and_(*conditions))
            query = query.order_by(desc(SensitiveDataRecordModel.detected_at)).limit(limit)

            result = await session.execute(query)
            return list(result.scalars().all())

    async def review_sensitive_record(
        self,
        record_id: str,
        is_confirmed: bool,
        reviewed_by: str,
        review_notes: str = None
    ) -> bool:
        """审核敏感数据记录"""
        async with db_manager.get_async_session() as session:
            result = await session.execute(
                select(SensitiveDataRecordModel).where(
                    SensitiveDataRecordModel.id == record_id
                )
            )
            record = result.scalar_one_or_none()
            if record:
                record.is_reviewed = True
                record.reviewed_by = reviewed_by
                record.reviewed_at = datetime.utcnow()
                record.review_notes = review_notes
                if not is_confirmed:
                    record.sensitivity_score = 0  # 标记为误报
                return True
            return False

    # ==================== 脱敏策略管理 ====================

    async def create_masking_policy(
        self,
        name: str,
        masking_type: str,
        description: str = None,
        sensitivity_level: str = None,
        data_type: str = None,
        column_pattern: str = None,
        masking_params: Dict = None,
        priority: int = 100,
        created_by: str = None
    ) -> str:
        """创建脱敏策略"""
        async with db_manager.get_async_session() as session:
            policy = MaskingPolicyModel(
                name=name,
                description=description,
                masking_type=masking_type,
                sensitivity_level=sensitivity_level,
                data_type=data_type,
                column_pattern=column_pattern,
                masking_params=masking_params or {},
                priority=priority,
                created_by=created_by
            )
            session.add(policy)
            await session.flush()
            return policy.id

    async def list_masking_policies(
        self,
        sensitivity_level: str = None,
        is_active: bool = True
    ) -> List[MaskingPolicyModel]:
        """列出脱敏策略"""
        async with db_manager.get_async_session() as session:
            conditions = [MaskingPolicyModel.is_active == is_active]
            if sensitivity_level:
                conditions.append(MaskingPolicyModel.sensitivity_level == sensitivity_level)

            result = await session.execute(
                select(MaskingPolicyModel)
                .where(and_(*conditions))
                .order_by(MaskingPolicyModel.priority)
            )
            return list(result.scalars().all())

    async def apply_masking(
        self,
        value: Any,
        policy: MaskingPolicyModel
    ) -> str:
        """应用脱敏"""
        if value is None:
            return None

        str_value = str(value)
        masking_type = policy.masking_type
        params = policy.masking_params or {}

        if masking_type == MaskingType.FULL.value:
            return "*" * min(len(str_value), 10)

        elif masking_type == MaskingType.PARTIAL.value:
            keep_first = params.get("keep_first", 2)
            keep_last = params.get("keep_last", 2)
            mask_char = params.get("mask_char", "*")
            if len(str_value) <= keep_first + keep_last:
                return mask_char * len(str_value)
            return str_value[:keep_first] + mask_char * (len(str_value) - keep_first - keep_last) + str_value[-keep_last:]

        elif masking_type == MaskingType.HASH.value:
            import hashlib
            algorithm = params.get("algorithm", "sha256")
            if algorithm == "md5":
                return hashlib.md5(str_value.encode()).hexdigest()
            else:
                return hashlib.sha256(str_value.encode()).hexdigest()

        elif masking_type == MaskingType.REDACT.value:
            return params.get("replacement", "[REDACTED]")

        else:
            return str_value

    async def delete_masking_policy(self, policy_id: str) -> bool:
        """删除脱敏策略"""
        async with db_manager.get_async_session() as session:
            result = await session.execute(
                select(MaskingPolicyModel).where(
                    MaskingPolicyModel.id == policy_id
                )
            )
            policy = result.scalar_one_or_none()
            if policy:
                policy.is_active = False
                return True
            return False

    # ==================== 治理指标统计 ====================

    async def calculate_governance_score(
        self,
        datasource: str = None,
        period_type: str = "day"
    ) -> Dict[str, Any]:
        """计算治理分数"""
        async with db_manager.get_async_session() as session:
            # 1. 分类覆盖率
            classification_coverage = await self._calculate_classification_coverage(session, datasource)

            # 2. 敏感数据识别率
            sensitivity_coverage = await self._calculate_sensitivity_coverage(session, datasource)

            # 3. 数据质量分数
            quality_score = await self._calculate_quality_score(session, datasource)

            # 4. 血缘覆盖率
            lineage_coverage = await self._calculate_lineage_coverage(session, datasource)

            # 5. 策略合规率
            policy_compliance = await self._calculate_policy_compliance(session, datasource)

            # 计算综合分数 (加权平均)
            governance_score = (
                classification_coverage * 0.2 +
                sensitivity_coverage * 0.25 +
                quality_score * 0.25 +
                lineage_coverage * 0.15 +
                policy_compliance * 0.15
            )

            return {
                "governance_score": round(governance_score, 2),
                "classification_coverage": round(classification_coverage, 2),
                "sensitivity_coverage": round(sensitivity_coverage, 2),
                "quality_score": round(quality_score, 2),
                "lineage_coverage": round(lineage_coverage, 2),
                "policy_compliance": round(policy_compliance, 2)
            }

    async def _calculate_classification_coverage(
        self,
        session: AsyncSession,
        datasource: str = None
    ) -> float:
        """计算分类覆盖率"""
        try:
            # 获取已标注的表数量
            query = select(func.count(func.distinct(DataLabelModel.table_name)))
            conditions = [
                DataLabelModel.is_active == True,
                DataLabelModel.label_type == "classification"
            ]
            if datasource:
                conditions.append(DataLabelModel.datasource == datasource)
            query = query.where(and_(*conditions))
            result = await session.execute(query)
            labeled_tables = result.scalar() or 0

            # 获取总表数 (从血缘节点中估算)
            query = select(func.count(func.distinct(LineageNodeModel.name)))
            conditions = [
                LineageNodeModel.is_current == True,
                LineageNodeModel.node_type == "table"
            ]
            if datasource:
                conditions.append(LineageNodeModel.datasource == datasource)
            query = query.where(and_(*conditions))
            result = await session.execute(query)
            total_tables = result.scalar() or 1

            return min(100, (labeled_tables / total_tables) * 100) if total_tables > 0 else 0
        except:
            return 0

    async def _calculate_sensitivity_coverage(
        self,
        session: AsyncSession,
        datasource: str = None
    ) -> float:
        """计算敏感数据覆盖率"""
        try:
            # 获取已扫描的表数量
            query = select(func.count(func.distinct(SensitiveDataRecordModel.table_name)))
            conditions = [SensitiveDataRecordModel.detection_method.isnot(None)]
            if datasource:
                conditions.append(SensitiveDataRecordModel.datasource == datasource)
            query = query.where(and_(*conditions))
            result = await session.execute(query)
            scanned_tables = result.scalar() or 0

            # 获取总表数
            query = select(func.count(func.distinct(LineageNodeModel.name)))
            conditions = [
                LineageNodeModel.is_current == True,
                LineageNodeModel.node_type == "table"
            ]
            if datasource:
                conditions.append(LineageNodeModel.datasource == datasource)
            query = query.where(and_(*conditions))
            result = await session.execute(query)
            total_tables = result.scalar() or 1

            return min(100, (scanned_tables / total_tables) * 100) if total_tables > 0 else 0
        except:
            return 0

    async def _calculate_quality_score(
        self,
        session: AsyncSession,
        datasource: str = None
    ) -> float:
        """计算数据质量分数"""
        try:
            # 获取最近的质量检查结果
            conditions = [QualityResultModel.status.isnot(None)]
            if datasource:
                # 需要通过 rule_id 关联到 datasource
                pass

            query = select(
                func.count(QualityResultModel.id),
                func.sum(func.case((QualityResultModel.status == "passed", 1), else_=0))
            ).where(and_(*conditions))
            result = await session.execute(query)
            total, passed = result.one()

            return (passed / total * 100) if total > 0 else 100
        except:
            return 0

    async def _calculate_lineage_coverage(
        self,
        session: AsyncSession,
        datasource: str = None
    ) -> float:
        """计算血缘覆盖率"""
        try:
            # 统计有血缘关系的表
            query = select(func.count(func.distinct(LineageNodeModel.name)))
            conditions = [LineageNodeModel.is_current == True]
            if datasource:
                conditions.append(LineageNodeModel.datasource == datasource)
            query = query.where(and_(*conditions))
            result = await session.execute(query)
            lineage_tables = result.scalar() or 0

            # 获取总表数
            query = select(func.count(func.distinct(LineageNodeModel.name)))
            conditions = [LineageNodeModel.is_current == True]
            if datasource:
                conditions.append(LineageNodeModel.datasource == datasource)
            query = query.where(and_(*conditions))
            result = await session.execute(query)
            total_tables = result.scalar() or 1

            return min(100, (lineage_tables / total_tables) * 100) if total_tables > 0 else 0
        except:
            return 0

    async def _calculate_policy_compliance(
        self,
        session: AsyncSession,
        datasource: str = None
    ) -> float:
        """计算策略合规率"""
        try:
            # 获取已脱敏的敏感数据比例
            query = select(
                func.count(SensitiveDataRecordModel.id),
                func.sum(func.case((SensitiveDataRecordModel.is_masked == True, 1), else_=0))
            )
            conditions = [SensitiveDataRecordModel.sensitivity_level.isnot(None)]
            if datasource:
                conditions.append(SensitiveDataRecordModel.datasource == datasource)
            query = query.where(and_(*conditions))
            result = await session.execute(query)
            total, masked = result.one()

            return (masked / total * 100) if total > 0 else 100
        except:
            return 100

    async def record_governance_metric(
        self,
        metric_type: str,
        metric_value: float,
        datasource: str = None,
        table_name: str = None,
        target_value: float = None,
        period_type: str = "day",
        details: Dict = None,
        created_by: str = None
    ) -> str:
        """记录治理指标"""
        async with db_manager.get_async_session() as session:
            now = datetime.utcnow()
            if period_type == "day":
                period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                period_end = period_start + timedelta(days=1)
            elif period_type == "hour":
                period_start = now.replace(minute=0, second=0, microsecond=0)
                period_end = period_start + timedelta(hours=1)
            else:
                period_start = now
                period_end = now + timedelta(days=1)

            metric = GovernanceMetricModel(
                metric_type=metric_type,
                metric_value=metric_value,
                datasource=datasource,
                table_name=table_name,
                target_value=target_value,
                period_start=period_start,
                period_end=period_end,
                period_type=period_type,
                details=details or {},
                created_by=created_by
            )
            session.add(metric)
            await session.flush()
            return metric.id

    # ==================== 治理仪表板 ====================

    async def get_governance_dashboard(self, datasource: str = None) -> Dict[str, Any]:
        """获取治理仪表板"""
        async with db_manager.get_async_session() as session:
            # 1. 治理分数
            scores = await self.calculate_governance_score(datasource)

            # 2. 敏感数据统计
            sensitive_stats = await self._get_sensitive_stats(session, datasource)

            # 3. 分类统计
            classification_stats = await self._get_classification_stats(session, datasource)

            # 4. 质量检查统计
            quality_stats = await self._get_quality_stats(session, datasource)

            # 5. 血缘统计
            lineage_stats = await self._get_lineage_stats(session, datasource)

            return {
                "governance_score": scores["governance_score"],
                "sub_scores": scores,
                "sensitive_data": sensitive_stats,
                "classifications": classification_stats,
                "quality": quality_stats,
                "lineage": lineage_stats
            }

    async def _get_sensitive_stats(
        self,
        session: AsyncSession,
        datasource: str = None
    ) -> Dict[str, Any]:
        """获取敏感数据统计"""
        try:
            conditions = []
            if datasource:
                conditions.append(SensitiveDataRecordModel.datasource == datasource)

            # 总数
            query = select(func.count(SensitiveDataRecordModel.id))
            if conditions:
                query = query.where(and_(*conditions))
            result = await session.execute(query)
            total = result.scalar() or 0

            # 按级别统计
            query = select(
                SensitiveDataRecordModel.sensitivity_level,
                func.count(SensitiveDataRecordModel.id)
            )
            if conditions:
                query = query.where(and_(*conditions))
            query = query.group_by(SensitiveDataRecordModel.sensitivity_level)
            result = await session.execute(query)
            by_level = {row[0]: row[1] for row in result.all()}

            # 未审核数量
            query = select(func.count(SensitiveDataRecordModel.id)).where(
                SensitiveDataRecordModel.is_reviewed == False
            )
            if conditions:
                query = query.where(and_(*conditions))
            result = await session.execute(query)
            pending_review = result.scalar() or 0

            return {
                "total": total,
                "by_level": by_level,
                "pending_review": pending_review
            }
        except:
            return {"total": 0, "by_level": {}, "pending_review": 0}

    async def _get_classification_stats(
        self,
        session: AsyncSession,
        datasource: str = None
    ) -> Dict[str, Any]:
        """获取分类统计"""
        try:
            conditions = [DataLabelModel.is_active == True]
            if datasource:
                conditions.append(DataLabelModel.datasource == datasource)

            query = select(func.count(DataLabelModel.id)).where(and_(*conditions))
            result = await session.execute(query)
            total = result.scalar() or 0

            return {"total_labels": total}
        except:
            return {"total_labels": 0}

    async def _get_quality_stats(
        self,
        session: AsyncSession,
        datasource: str = None
    ) -> Dict[str, Any]:
        """获取质量统计"""
        try:
            # 获取最近 24 小时的结果
            cutoff = datetime.utcnow() - timedelta(hours=24)

            query = select(
                func.count(QualityResultModel.id),
                func.sum(func.case((QualityResultModel.status == "passed", 1), else_=0)),
                func.sum(func.case((QualityResultModel.status == "failed", 1), else_=0)),
                func.sum(func.case((QualityResultModel.status == "warning", 1), else_=0))
            ).where(QualityResultModel.checked_at >= cutoff)
            result = await session.execute(query)
            total, passed, failed, warning = result.one()

            return {
                "total_checks": total or 0,
                "passed": passed or 0,
                "failed": failed or 0,
                "warning": warning or 0,
                "pass_rate": round((passed / total * 100) if total > 0 else 100, 2)
            }
        except:
            return {"total_checks": 0, "passed": 0, "failed": 0, "warning": 0, "pass_rate": 100}

    async def _get_lineage_stats(
        self,
        session: AsyncSession,
        datasource: str = None
    ) -> Dict[str, Any]:
        """获取血缘统计"""
        try:
            conditions = [LineageNodeModel.is_current == True]
            if datasource:
                conditions.append(LineageNodeModel.datasource == datasource)

            # 节点统计
            query = select(func.count(LineageNodeModel.id)).where(and_(*conditions))
            result = await session.execute(query)
            total_nodes = result.scalar() or 0

            # 边统计
            conditions = [LineageEdgeModel.is_current == True]
            if datasource:
                conditions.append(LineageEdgeModel.source_id.in_(
                    select(LineageNodeModel.id).where(and_(*conditions))
                ))
            query = select(func.count(LineageEdgeModel.id)).where(and_(*conditions))
            result = await session.execute(query)
            total_edges = result.scalar() or 0

            return {
                "total_nodes": total_nodes,
                "total_edges": total_edges
            }
        except:
            return {"total_nodes": 0, "total_edges": 0}


# 全局数据治理服务实例
data_governance_service = DataGovernanceService()
