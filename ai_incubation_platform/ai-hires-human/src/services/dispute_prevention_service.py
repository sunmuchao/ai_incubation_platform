"""
争议预防服务 (Dispute Prevention Service)。

功能：
1. 争议风险预测 - 在任务交付前预测争议可能性
2. 争议因素分析 - 识别可能导致争议的关键因素
3. 预防措施建议 - 提供可执行的争议预防建议
4. 争议预警系统 - 对高风险任务发出预警
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DisputeRiskLevel(str, Enum):
    """争议风险等级。"""
    LOW = "low"  # 低风险
    MEDIUM = "medium"  # 中风险
    HIGH = "high"  # 高风险
    CRITICAL = "critical"  # 极高风险


class DisputeFactorType(str, Enum):
    """争议因素类型。"""
    COMMUNICATION = "communication"  # 沟通不足
    REQUIREMENT_CLARITY = "requirement_clarity"  # 需求不清晰
    DEADLINE_PRESSURE = "deadline_pressure"  # 期限压力
    PAYMENT_DISPUTE = "payment_dispute"  # 支付争议
    QUALITY_MISMATCH = "quality_mismatch"  # 质量不匹配
    WORKER_HISTORY = "worker_history"  # 工人历史问题
    EMPLOYER_HISTORY = "employer_history"  # 雇主历史问题


class DisputeFactor(BaseModel):
    """争议因素。"""
    factor_type: DisputeFactorType
    description: str
    risk_contribution: float  # 风险贡献度 (0-1)
    evidence: Optional[str] = None  # 证据描述


class DisputePreventionRequest(BaseModel):
    """争议预防请求。"""
    task_id: str
    employer_id: str
    worker_id: str
    task_description: str
    acceptance_criteria: List[str]
    reward_amount: float
    deadline_hours: Optional[int] = None
    worker_history: Optional[Dict[str, Any]] = None
    employer_history: Optional[Dict[str, Any]] = None


class DisputePreventionResponse(BaseModel):
    """争议预防响应。"""
    success: bool
    risk_id: Optional[str] = None
    risk_level: DisputeRiskLevel = DisputeRiskLevel.MEDIUM
    risk_score: float = 0.5  # 0-1，越高越可能产生争议
    dispute_factors: List[DisputeFactor] = Field(default_factory=list)
    prevention_recommendations: List[str] = Field(default_factory=list)
    early_warning: bool = False  # 是否需要早期预警
    message: str = ""


class DisputeRiskRecord(BaseModel):
    """争议风险记录。"""
    risk_id: str
    task_id: str
    employer_id: str
    worker_id: str

    # 风险评估
    risk_level: DisputeRiskLevel
    risk_score: float
    dispute_factors: List[DisputeFactor]

    # 预防措施
    prevention_recommendations: List[str]
    actions_taken: List[str] = Field(default_factory=list)

    # 状态追踪
    status: str = "active"  # active, resolved, disputed
    actual_dispute_occurred: bool = False

    # 元数据
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class DisputePreventionService:
    """
    争议预防服务。

    核心功能：
    1. 争议风险预测 - 基于多维度特征预测争议可能性
    2. 争议因素分析 - 识别并量化各因素的风险贡献
    3. 预防措施建议 - 提供可执行的预防建议
    4. 争议预警系统 - 对高风险任务发出预警
    """

    # 风险阈值配置
    MEDIUM_RISK_THRESHOLD = 0.4
    HIGH_RISK_THRESHOLD = 0.7
    CRITICAL_RISK_THRESHOLD = 0.85

    # 因素权重配置
    FACTOR_WEIGHTS = {
        DisputeFactorType.COMMUNICATION: 0.15,
        DisputeFactorType.REQUIREMENT_CLARITY: 0.25,
        DisputeFactorType.DEADLINE_PRESSURE: 0.15,
        DisputeFactorType.PAYMENT_DISPUTE: 0.20,
        DisputeFactorType.QUALITY_MISMATCH: 0.15,
        DisputeFactorType.WORKER_HISTORY: 0.05,
        DisputeFactorType.EMPLOYER_HISTORY: 0.05,
    }

    def __init__(self):
        # 内存存储风险记录
        self._risk_records: Dict[str, DisputeRiskRecord] = {}
        self._task_risks: Dict[str, str] = {}  # task_id -> risk_id

    def assess_dispute_risk(self, request: DisputePreventionRequest) -> DisputePreventionResponse:
        """
        评估争议风险。

        Args:
            request: 争议预防请求

        Returns:
            包含风险评估结果和预防建议的响应
        """
        try:
            # 1. 分析各争议因素
            dispute_factors = self._analyze_dispute_factors(request)

            # 2. 计算风险得分
            risk_score = self._calculate_risk_score(dispute_factors)

            # 3. 确定风险等级
            risk_level = self._determine_risk_level(risk_score)

            # 4. 生成预防建议
            prevention_recommendations = self._generate_prevention_recommendations(
                dispute_factors, risk_level
            )

            # 5. 创建风险记录
            risk_id = f"dpr_{uuid.uuid4().hex[:16]}"
            risk_record = DisputeRiskRecord(
                risk_id=risk_id,
                task_id=request.task_id,
                employer_id=request.employer_id,
                worker_id=request.worker_id,
                risk_level=risk_level,
                risk_score=risk_score,
                dispute_factors=dispute_factors,
                prevention_recommendations=prevention_recommendations,
            )

            # 6. 存储记录
            self._risk_records[risk_id] = risk_record
            self._task_risks[request.task_id] = risk_id

            # 7. 判断是否需要早期预警
            early_warning = risk_level in [DisputeRiskLevel.HIGH, DisputeRiskLevel.CRITICAL]

            logger.info(
                "Dispute risk assessed: risk_id=%s, task_id=%s, risk_level=%s, score=%.2f",
                risk_id, request.task_id, risk_level.value, risk_score
            )

            # 8. 生成消息
            message = self._generate_risk_message(risk_level, dispute_factors)

            return DisputePreventionResponse(
                success=True,
                risk_id=risk_id,
                risk_level=risk_level,
                risk_score=round(risk_score, 3),
                dispute_factors=dispute_factors,
                prevention_recommendations=prevention_recommendations,
                early_warning=early_warning,
                message=message,
            )

        except Exception as e:
            logger.exception("Dispute risk assessment failed: %s", e)
            return DisputePreventionResponse(
                success=False,
                message=f"争议风险评估失败：{str(e)}",
                risk_score=0.5,
            )

    def _analyze_dispute_factors(self, request: DisputePreventionRequest) -> List[DisputeFactor]:
        """分析争议因素。"""
        factors = []

        # 1. 需求清晰度分析
        requirement_factor = self._analyze_requirement_clarity(request)
        if requirement_factor:
            factors.append(requirement_factor)

        # 2. 期限压力分析
        deadline_factor = self._analyze_deadline_pressure(request)
        if deadline_factor:
            factors.append(deadline_factor)

        # 3. 支付合理性分析
        payment_factor = self._analyze_payment_dispute_risk(request)
        if payment_factor:
            factors.append(payment_factor)

        # 4. 质量匹配置信度分析
        quality_factor = self._analyze_quality_mismatch_risk(request)
        if quality_factor:
            factors.append(quality_factor)

        # 5. 工人历史分析
        worker_factor = self._analyze_worker_history_risk(request)
        if worker_factor:
            factors.append(worker_factor)

        # 6. 雇主历史分析
        employer_factor = self._analyze_employer_history_risk(request)
        if employer_factor:
            factors.append(employer_factor)

        # 7. 沟通风险分析
        communication_factor = self._analyze_communication_risk(request)
        if communication_factor:
            factors.append(communication_factor)

        return factors

    def _analyze_requirement_clarity(self, request: DisputePreventionRequest) -> Optional[DisputeFactor]:
        """分析需求清晰度风险。"""
        description = request.task_description
        criteria = request.acceptance_criteria

        issues = []
        risk_contribution = 0.0

        # 检查描述长度
        if len(description) < 50:
            issues.append("任务描述过于简短")
            risk_contribution += 0.3

        # 检查是否有明确的验收标准
        if not criteria or len(criteria) == 0:
            issues.append("没有验收标准")
            risk_contribution += 0.4
        elif len(criteria) == 1:
            issues.append("验收标准过于单一")
            risk_contribution += 0.15

        # 检查验收标准是否具体
        for criterion in criteria:
            if len(criterion) < 5:
                issues.append("验收标准不够具体")
                risk_contribution += 0.1
                break

        # 检查是否包含量化指标
        quantifiable_keywords = ["个", "张", "条", "分钟", "小时", "%", "至少", "不超过", ">= ", "<= "]
        has_quantifiable = any(kw in description or kw in str(criteria) for kw in quantifiable_keywords)
        if not has_quantifiable:
            issues.append("缺少量化指标")
            risk_contribution += 0.15

        if issues:
            return DisputeFactor(
                factor_type=DisputeFactorType.REQUIREMENT_CLARITY,
                description="; ".join(issues),
                risk_contribution=min(risk_contribution, 1.0),
                evidence=f"描述长度:{len(description)}, 验收标准数量:{len(criteria) if criteria else 0}",
            )
        return None

    def _analyze_deadline_pressure(self, request: DisputePreventionRequest) -> Optional[DisputeFactor]:
        """分析期限压力风险。"""
        if not request.deadline_hours or request.deadline_hours <= 0:
            return None

        # 基于任务复杂度评估期限合理性
        description_length = len(request.task_description)
        expected_hours = description_length / 100 * 2  # 简化估算

        if request.deadline_hours < expected_hours * 0.5:
            return DisputeFactor(
                factor_type=DisputeFactorType.DEADLINE_PRESSURE,
                description=f"期限过于紧张 ({request.deadline_hours}小时)，远低于预期工时 ({expected_hours:.1f}小时)",
                risk_contribution=0.7,
                evidence=f"预期工时:{expected_hours:.1f}h, 实际期限:{request.deadline_hours}h",
            )
        elif request.deadline_hours < expected_hours:
            return DisputeFactor(
                factor_type=DisputeFactorType.DEADLINE_PRESSURE,
                description=f"期限较为紧张",
                risk_contribution=0.4,
                evidence=f"预期工时:{expected_hours:.1f}h, 实际期限:{request.deadline_hours}h",
            )
        return None

    def _analyze_payment_dispute_risk(self, request: DisputePreventionRequest) -> Optional[DisputeFactor]:
        """分析支付争议风险。"""
        if request.reward_amount <= 0:
            return DisputeFactor(
                factor_type=DisputeFactorType.PAYMENT_DISPUTE,
                description="报酬为零或负数",
                risk_contribution=0.9,
            )

        # 基于任务复杂度评估报酬合理性
        description_length = len(request.task_description)
        base_reward = description_length * 0.5  # 简化估算

        if request.reward_amount < base_reward * 0.3:
            return DisputeFactor(
                factor_type=DisputeFactorType.PAYMENT_DISPUTE,
                description=f"报酬过低，可能引发争议",
                risk_contribution=0.6,
                evidence=f"建议报酬:¥{base_reward:.1f}, 实际报酬:¥{request.reward_amount}",
            )
        elif request.reward_amount < base_reward * 0.5:
            return DisputeFactor(
                factor_type=DisputeFactorType.PAYMENT_DISPUTE,
                description=f"报酬偏低",
                risk_contribution=0.3,
                evidence=f"建议报酬:¥{base_reward:.1f}, 实际报酬:¥{request.reward_amount}",
            )
        return None

    def _analyze_quality_mismatch_risk(self, request: DisputePreventionRequest) -> Optional[DisputeFactor]:
        """分析质量不匹配风险。"""
        # 检查验收标准是否主观
        subjective_keywords = ["好看", "美观", "专业", "高质量", "优秀"]
        criteria_str = " ".join(request.acceptance_criteria) if request.acceptance_criteria else ""

        subjective_count = sum(1 for kw in subjective_keywords if kw in criteria_str)

        if subjective_count >= 2:
            return DisputeFactor(
                factor_type=DisputeFactorType.QUALITY_MISMATCH,
                description="验收标准包含过多主观性描述，容易导致质量标准不一致",
                risk_contribution=0.5,
                evidence=f"主观性词汇数量:{subjective_count}",
            )
        return None

    def _analyze_worker_history_risk(self, request: DisputePreventionRequest) -> Optional[DisputeFactor]:
        """分析工人历史风险。"""
        if not request.worker_history:
            return None

        history = request.worker_history
        issues = []
        risk_contribution = 0.0

        # 检查 dispute_rate
        dispute_rate = history.get("dispute_rate", 0)
        if dispute_rate > 0.2:
            issues.append(f"工人历史争议率较高 ({dispute_rate:.1%})")
            risk_contribution += 0.4

        # 检查 rejection_rate
        rejection_rate = history.get("rejection_rate", 0)
        if rejection_rate > 0.3:
            issues.append(f"工人历史拒绝率较高 ({rejection_rate:.1%})")
            risk_contribution += 0.3

        # 检查平均评分
        avg_rating = history.get("average_rating", 5.0)
        if avg_rating < 3.0:
            issues.append(f"工人平均评分较低 ({avg_rating:.1f}/5.0)")
            risk_contribution += 0.3

        if issues:
            return DisputeFactor(
                factor_type=DisputeFactorType.WORKER_HISTORY,
                description="; ".join(issues),
                risk_contribution=min(risk_contribution, 0.8),
            )
        return None

    def _analyze_employer_history_risk(self, request: DisputePreventionRequest) -> Optional[DisputeFactor]:
        """分析雇主历史风险。"""
        if not request.employer_history:
            return None

        history = request.employer_history
        issues = []
        risk_contribution = 0.0

        # 检查 rejection_rate
        rejection_rate = history.get("rejection_rate", 0)
        if rejection_rate > 0.3:
            issues.append(f"雇主历史拒绝率较高 ({rejection_rate:.1%})")
            risk_contribution += 0.5

        # 检查平均支付时间
        avg_payment_days = history.get("avg_payment_days", 1)
        if avg_payment_days > 7:
            issues.append(f"雇主平均支付时间较长 ({avg_payment_days:.1f}天)")
            risk_contribution += 0.3

        # 检查雇主评分
        employer_rating = history.get("employer_rating", 5.0)
        if employer_rating < 3.0:
            issues.append(f"雇主评分较低 ({employer_rating:.1f}/5.0)")
            risk_contribution += 0.2

        if issues:
            return DisputeFactor(
                factor_type=DisputeFactorType.EMPLOYER_HISTORY,
                description="; ".join(issues),
                risk_contribution=min(risk_contribution, 0.8),
            )
        return None

    def _analyze_communication_risk(self, request: DisputePreventionRequest) -> Optional[DisputeFactor]:
        """分析沟通风险。"""
        # 检查任务描述是否包含联系方式或沟通渠道
        communication_keywords = ["联系", "沟通", "消息", "phone", "email", "wechat", "微信"]
        description = request.task_description.lower()

        has_communication_channel = any(kw in description for kw in communication_keywords)

        if not has_communication_channel:
            return DisputeFactor(
                factor_type=DisputeFactorType.COMMUNICATION,
                description="任务未明确沟通渠道，可能导致沟通不畅",
                risk_contribution=0.3,
            )
        return None

    def _calculate_risk_score(self, factors: List[DisputeFactor]) -> float:
        """计算争议风险得分。"""
        if not factors:
            return 0.1  # 无风险因素时返回低风险

        # 加权计算
        weighted_risk = 0.0
        total_weight = 0.0

        for factor in factors:
            weight = self.FACTOR_WEIGHTS.get(factor.factor_type, 0.1)
            weighted_risk += factor.risk_contribution * weight
            total_weight += weight

        # 归一化
        if total_weight > 0:
            base_risk = weighted_risk / total_weight
        else:
            base_risk = 0.5

        # 因素数量加成（因素越多，风险越高）
        quantity_bonus = min(0.2, len(factors) * 0.05)

        return min(1.0, base_risk + quantity_bonus)

    def _determine_risk_level(self, risk_score: float) -> DisputeRiskLevel:
        """确定风险等级。"""
        if risk_score >= self.CRITICAL_RISK_THRESHOLD:
            return DisputeRiskLevel.CRITICAL
        elif risk_score >= self.HIGH_RISK_THRESHOLD:
            return DisputeRiskLevel.HIGH
        elif risk_score >= self.MEDIUM_RISK_THRESHOLD:
            return DisputeRiskLevel.MEDIUM
        else:
            return DisputeRiskLevel.LOW

    def _generate_prevention_recommendations(
        self,
        factors: List[DisputeFactor],
        risk_level: DisputeRiskLevel,
    ) -> List[str]:
        """生成争议预防建议。"""
        recommendations = []

        # 通用建议
        if risk_level == DisputeRiskLevel.CRITICAL:
            recommendations.append("【高风险预警】建议在任务开始前进行人工审核和双方确认")
        elif risk_level == DisputeRiskLevel.HIGH:
            recommendations.append("【风险预警】建议加强任务过程中的沟通和节点确认")

        # 基于具体因素的建议
        for factor in factors:
            if factor.factor_type == DisputeFactorType.REQUIREMENT_CLARITY:
                recommendations.append("建议细化任务描述，包含具体的交付标准和验收条件")
                recommendations.append("建议使用量化指标替代主观描述（如：数量、尺寸、时长等）")

            elif factor.factor_type == DisputeFactorType.DEADLINE_PRESSURE:
                recommendations.append("建议延长任务期限或分期交付，降低时间压力")

            elif factor.factor_type == DisputeFactorType.PAYMENT_DISPUTE:
                recommendations.append("建议参考市场均价调整报酬，避免因报酬产生争议")
                recommendations.append("建议启用平台资金托管功能，保障双方权益")

            elif factor.factor_type == DisputeFactorType.QUALITY_MISMATCH:
                recommendations.append("建议提供具体的质量参考样例或模板")
                recommendations.append("建议使用黄金标准测试预先评估工人能力")

            elif factor.factor_type == DisputeFactorType.WORKER_HISTORY:
                recommendations.append("建议选择信誉更高的工人，或增加中期检查节点")

            elif factor.factor_type == DisputeFactorType.EMPLOYER_HISTORY:
                recommendations.append("建议工人要求雇主提供预付款或资金托管")

            elif factor.factor_type == DisputeFactorType.COMMUNICATION:
                recommendations.append("建议在任务描述中明确沟通渠道和响应时间要求")

        # 去重
        return list(dict.fromkeys(recommendations))

    def _generate_risk_message(self, risk_level: DisputeRiskLevel, factors: List[DisputeFactor]) -> str:
        """生成风险消息。"""
        level_messages = {
            DisputeRiskLevel.LOW: "争议风险较低，可正常执行任务",
            DisputeRiskLevel.MEDIUM: "存在一定争议风险，建议关注预防建议",
            DisputeRiskLevel.HIGH: "争议风险较高，强烈建议采取预防措施",
            DisputeRiskLevel.CRITICAL: "争议风险极高，建议暂停任务并重新评估",
        }

        base_message = level_messages.get(risk_level, "未知风险等级")

        if factors:
            factor_summary = f"主要风险因素：{len(factors)}项"
            return f"{base_message}。{factor_summary}"

        return base_message

    def get_risk_record(self, risk_id: str) -> Optional[DisputeRiskRecord]:
        """获取风险记录。"""
        return self._risk_records.get(risk_id)

    def get_risk_by_task(self, task_id: str) -> Optional[DisputeRiskRecord]:
        """通过任务 ID 获取风险记录。"""
        risk_id = self._task_risks.get(task_id)
        if risk_id:
            return self._risk_records.get(risk_id)
        return None

    def record_dispute_outcome(
        self,
        risk_id: str,
        dispute_occurred: bool,
        dispute_reason: Optional[str] = None,
    ) -> bool:
        """记录实际争议结果。"""
        record = self._risk_records.get(risk_id)
        if not record:
            return False

        record.actual_dispute_occurred = dispute_occurred
        record.status = "disputed" if dispute_occurred else "resolved"
        record.updated_at = datetime.now()

        if dispute_reason:
            record.actions_taken.append(f"争议原因：{dispute_reason}")

        logger.info(
            "Dispute outcome recorded: risk_id=%s, occurred=%s",
            risk_id, dispute_occurred
        )
        return True

    def get_high_risk_tasks(self, min_risk_level: DisputeRiskLevel = DisputeRiskLevel.HIGH) -> List[DisputeRiskRecord]:
        """获取高风险任务列表。"""
        return [
            record for record in self._risk_records.values()
            if record.risk_level.value >= min_risk_level.value
        ]

    def get_risk_statistics(self) -> Dict[str, Any]:
        """获取风险统计信息。"""
        if not self._risk_records:
            return {"total_assessments": 0}

        records = list(self._risk_records.values())

        level_counts = {}
        for record in records:
            level = record.risk_level.value
            level_counts[level] = level_counts.get(level, 0) + 1

        avg_risk_score = sum(r.risk_score for r in records) / len(records)
        dispute_rate = sum(1 for r in records if r.actual_dispute_occurred) / len(records)

        return {
            "total_assessments": len(records),
            "average_risk_score": round(avg_risk_score, 3),
            "level_distribution": level_counts,
            "dispute_rate": round(dispute_rate, 3),
            "high_risk_count": sum(1 for r in records if r.risk_level in [DisputeRiskLevel.HIGH, DisputeRiskLevel.CRITICAL]),
        }


# 全局单例
dispute_prevention_service = DisputePreventionService()
