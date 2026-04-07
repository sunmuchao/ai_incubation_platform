"""
质量改进建议服务 (Quality Improvement Service)。

功能：
1. 质量问题分析 - 分析交付内容的的质量问题
2. 改进建议生成 - 提供具体可执行的质量改进建议
3. 技能提升推荐 - 推荐相关的培训和提升资源
4. 质量趋势追踪 - 追踪工人质量改进趋势
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class QualityIssueCategory(str, Enum):
    """质量问题类别。"""
    COMPLETENESS = "completeness"  # 完整性不足
    ACCURACY = "accuracy"  # 准确性问题
    FORMAT = "format"  # 格式问题
    DETAIL = "detail"  # 详细度不足
    PROFESSIONALISM = "professionalism"  # 专业性问题
    TIMELINESS = "timeliness"  # 及时性问题
    COMMUNICATION = "communication"  # 沟通问题


class QualityIssueSeverity(str, Enum):
    """质量问题严重程度。"""
    CRITICAL = "critical"  # 严重
    MAJOR = "major"  # 主要
    MINOR = "minor"  # 次要


class QualityIssue(BaseModel):
    """质量问题。"""
    issue_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: QualityIssueCategory
    severity: QualityIssueSeverity
    description: str
    evidence: Optional[str] = None  # 问题证据
    impact_score: float = 0.0  # 对整体质量的影响 (0-1)


class ImprovementSuggestion(BaseModel):
    """改进建议。"""
    suggestion_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    priority: str = "medium"  # low, medium, high
    estimated_effort: str = "medium"  # low, medium, high
    related_issues: List[str] = Field(default_factory=list)  # 相关问题 ID
    action_items: List[str] = Field(default_factory=list)  # 具体行动项


class TrainingResource(BaseModel):
    """培训资源。"""
    resource_id: str
    title: str
    type: str  # tutorial, course, guide, template
    url: Optional[str] = None
    duration_minutes: int = 30
    difficulty: str = "beginner"  # beginner, intermediate, advanced
    relevant_skills: List[str] = Field(default_factory=list)


class QualityImprovementRequest(BaseModel):
    """质量改进请求。"""
    task_id: str
    worker_id: str
    delivery_content: str
    acceptance_criteria: List[str]
    rejection_reason: Optional[str] = None  # 如果有拒绝原因
    task_category: str = "general"  # 任务类别
    worker_history: Optional[Dict[str, Any]] = None


class QualityImprovementResponse(BaseModel):
    """质量改进响应。"""
    success: bool
    analysis_id: Optional[str] = None
    quality_score: float = 0.0
    issues: List[QualityIssue] = Field(default_factory=list)
    suggestions: List[ImprovementSuggestion] = Field(default_factory=list)
    recommended_training: List[TrainingResource] = Field(default_factory=list)
    message: str = ""


class QualityImprovementRecord(BaseModel):
    """质量改进记录。"""
    analysis_id: str
    task_id: str
    worker_id: str

    # 质量评估
    quality_score: float
    issues: List[QualityIssue]
    suggestions: List[ImprovementSuggestion]

    # 追踪
    improvements_made: List[str] = Field(default_factory=list)
    follow_up_date: Optional[datetime] = None

    # 元数据
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class QualityImprovementService:
    """
    质量改进建议服务。

    核心功能：
    1. 质量问题分析 - 多维度分析交付内容的质量问题
    2. 改进建议生成 - 提供具体可执行的改进建议
    3. 技能提升推荐 - 根据问题类型推荐培训资源
    4. 质量趋势追踪 - 追踪工人质量改进趋势
    """

    # 问题类别权重
    CATEGORY_WEIGHTS = {
        QualityIssueCategory.COMPLETENESS: 0.25,
        QualityIssueCategory.ACCURACY: 0.25,
        QualityIssueCategory.FORMAT: 0.10,
        QualityIssueCategory.DETAIL: 0.20,
        QualityIssueCategory.PROFESSIONALISM: 0.10,
        QualityIssueCategory.TIMELINESS: 0.05,
        QualityIssueCategory.COMMUNICATION: 0.05,
    }

    # 任务类别特定的检查规则
    TASK_CATEGORY_RULES = {
        "data_annotation": {
            "min_accuracy": 0.95,
            "required_fields": ["label", "confidence"],
        },
        "content_moderation": {
            "min_accuracy": 0.90,
            "required_fields": ["decision", "reason"],
        },
        "survey": {
            "min_completion_rate": 0.80,
            "required_fields": ["answers"],
        },
        "transcription": {
            "min_word_accuracy": 0.95,
            "required_fields": ["transcript"],
        },
        "image_collection": {
            "min_images": 1,
            "required_fields": ["image_urls", "location"],
        },
    }

    def __init__(self):
        # 内存存储改进记录
        self._improvement_records: Dict[str, QualityImprovementRecord] = {}
        self._worker_quality_history: Dict[str, List[float]] = {}

        # 预定义培训资源库
        self._training_resources = self._initialize_training_resources()

    def _initialize_training_resources(self) -> List[TrainingResource]:
        """初始化培训资源库。"""
        return [
            TrainingResource(
                resource_id="tr_001",
                title="数据标注最佳实践",
                type="course",
                duration_minutes=60,
                difficulty="beginner",
                relevant_skills=["data_annotation", "attention_to_detail"],
            ),
            TrainingResource(
                resource_id="tr_002",
                title="内容审核指南",
                type="guide",
                duration_minutes=30,
                difficulty="intermediate",
                relevant_skills=["content_moderation", "judgment"],
            ),
            TrainingResource(
                resource_id="tr_003",
                title="如何撰写高质量的调研报告",
                type="tutorial",
                duration_minutes=45,
                difficulty="intermediate",
                relevant_skills=["survey", "reporting"],
            ),
            TrainingResource(
                resource_id="tr_004",
                title="转录 accuracy 提升技巧",
                type="tutorial",
                duration_minutes=40,
                difficulty="advanced",
                relevant_skills=["transcription", "listening"],
            ),
            TrainingResource(
                resource_id="tr_005",
                title="照片采集质量标准",
                type="guide",
                duration_minutes=20,
                difficulty="beginner",
                relevant_skills=["photography", "image_quality"],
            ),
            TrainingResource(
                resource_id="tr_006",
                title="职场沟通技巧",
                type="course",
                duration_minutes=90,
                difficulty="beginner",
                relevant_skills=["communication", "professionalism"],
            ),
            TrainingResource(
                resource_id="tr_007",
                title="时间管理与截止日期遵守",
                type="course",
                duration_minutes=45,
                difficulty="beginner",
                relevant_skills=["time_management", "timeliness"],
            ),
            TrainingResource(
                resource_id="tr_008",
                title="高质量交付的 10 个要点",
                type="guide",
                duration_minutes=15,
                difficulty="beginner",
                relevant_skills=["general", "quality"],
            ),
        ]

    def analyze_and_suggest(self, request: QualityImprovementRequest) -> QualityImprovementResponse:
        """
        分析质量问题并生成改进建议。

        Args:
            request: 质量改进请求

        Returns:
            包含问题分析、改进建议和培训推荐的响应
        """
        try:
            # 1. 分析质量问题
            issues = self._analyze_quality_issues(request)

            # 2. 计算质量得分
            quality_score = self._calculate_quality_score(issues)

            # 3. 生成改进建议
            suggestions = self._generate_suggestions(issues, request)

            # 4. 推荐培训资源
            recommended_training = self._recommend_training(issues, request.task_category)

            # 5. 创建分析记录
            analysis_id = f"qi_{uuid.uuid4().hex[:16]}"
            record = QualityImprovementRecord(
                analysis_id=analysis_id,
                task_id=request.task_id,
                worker_id=request.worker_id,
                quality_score=quality_score,
                issues=issues,
                suggestions=suggestions,
            )

            # 6. 存储记录
            self._improvement_records[analysis_id] = record

            # 7. 更新工人质量历史
            self._update_worker_history(request.worker_id, quality_score)

            # 8. 生成消息
            message = self._generate_message(quality_score, issues, suggestions)

            logger.info(
                "Quality improvement analysis completed: analysis_id=%s, worker_id=%s, score=%.2f",
                analysis_id, request.worker_id, quality_score
            )

            return QualityImprovementResponse(
                success=True,
                analysis_id=analysis_id,
                quality_score=round(quality_score, 3),
                issues=issues,
                suggestions=suggestions,
                recommended_training=recommended_training,
                message=message,
            )

        except Exception as e:
            logger.exception("Quality improvement analysis failed: %s", e)
            return QualityImprovementResponse(
                success=False,
                message=f"质量分析失败：{str(e)}",
                quality_score=0.5,
            )

    def _analyze_quality_issues(self, request: QualityImprovementRequest) -> List[QualityIssue]:
        """分析质量问题。"""
        issues = []

        # 1. 完整性检查
        completeness_issue = self._check_completeness(request)
        if completeness_issue:
            issues.append(completeness_issue)

        # 2. 准确性检查
        accuracy_issue = self._check_accuracy(request)
        if accuracy_issue:
            issues.append(accuracy_issue)

        # 3. 格式检查
        format_issue = self._check_format(request)
        if format_issue:
            issues.append(format_issue)

        # 4. 详细度检查
        detail_issue = self._check_detail(request)
        if detail_issue:
            issues.append(detail_issue)

        # 5. 专业性检查
        professionalism_issue = self._check_professionalism(request)
        if professionalism_issue:
            issues.append(professionalism_issue)

        # 6. 如果有拒绝原因，额外分析
        if request.rejection_reason:
            rejection_issues = self._analyze_rejection_reason(request.rejection_reason)
            issues.extend(rejection_issues)

        return issues

    def _check_completeness(self, request: QualityImprovementRequest) -> Optional[QualityIssue]:
        """检查完整性问题。"""
        content = request.delivery_content
        criteria = request.acceptance_criteria

        issues = []

        # 检查是否回应了所有验收标准
        if criteria:
            unaddressed_criteria = []
            for criterion in criteria:
                # 简化检查：看验收标准中的关键词是否出现在交付内容中
                keywords = self._extract_keywords(criterion)
                if not any(kw in content for kw in keywords):
                    unaddressed_criteria.append(criterion)

            if unaddressed_criteria:
                issues.append(f"未回应验收标准：{len(unaddressed_criteria)}项")

        # 检查内容长度
        if len(content) < 50:
            issues.append("交付内容过于简短")

        if issues:
            return QualityIssue(
                category=QualityIssueCategory.COMPLETENESS,
                severity=QualityIssueSeverity.MAJOR if len(issues) >= 2 else QualityIssueSeverity.MINOR,
                description="; ".join(issues),
                evidence=f"内容长度:{len(content)}, 未回应标准:{len(unaddressed_criteria) if 'unaddressed_criteria' in dir() else 0}",
                impact_score=0.3 * len(issues),
            )
        return None

    def _check_accuracy(self, request: QualityImprovementRequest) -> Optional[QualityIssue]:
        """检查准确性问题。"""
        content = request.delivery_content
        rejection_reason = request.rejection_reason

        issues = []

        # 如果有拒绝原因，检查是否包含准确性相关的问题
        if rejection_reason:
            accuracy_keywords = ["错误", "不准确", "不对", "incorrect", "wrong", "error"]
            if any(kw in rejection_reason.lower() for kw in accuracy_keywords):
                issues.append("交付内容存在准确性问题")

        # 检查是否有明显的数据错误模式
        if self._detect_obvious_errors(content):
            issues.append("检测到明显的数据错误")

        if issues:
            return QualityIssue(
                category=QualityIssueCategory.ACCURACY,
                severity=QualityIssueSeverity.CRITICAL if len(issues) >= 2 else QualityIssueSeverity.MAJOR,
                description="; ".join(issues),
                impact_score=0.4 * len(issues),
            )
        return None

    def _check_format(self, request: QualityImprovementRequest) -> Optional[QualityIssue]:
        """检查格式问题。"""
        content = request.delivery_content

        issues = []

        # 检查是否有基本的结构
        if len(content) > 100 and "\n" not in content:
            issues.append("内容缺乏基本结构（无分段）")

        # 检查是否有格式标记
        format_indicators = ["\n", "-", "•", "1.", "2.", "：", ":"]
        if not any(fi in content for fi in format_indicators):
            if len(content) > 50:
                issues.append("内容格式单一，缺乏结构化呈现")

        if issues:
            return QualityIssue(
                category=QualityIssueCategory.FORMAT,
                severity=QualityIssueSeverity.MINOR,
                description="; ".join(issues),
                impact_score=0.15,
            )
        return None

    def _check_detail(self, request: QualityImprovementRequest) -> Optional[QualityIssue]:
        """检查详细度问题。"""
        content = request.delivery_content
        criteria = request.acceptance_criteria

        issues = []

        # 检查详细程度
        if len(content) < 100:
            issues.append("内容详细度不足")

        # 检查是否有具体数据支撑
        has_data = any(c.isdigit() for c in content)
        if not has_data and len(content) > 50:
            issues.append("缺乏具体数据支撑")

        # 检查是否有解释说明
        explanation_keywords = ["因为", "所以", "原因是", "由于", "because", "therefore", "reason"]
        if not any(kw in content.lower() for kw in explanation_keywords):
            if request.rejection_reason and "why" in request.rejection_reason.lower():
                issues.append("缺乏必要的解释说明")

        if issues:
            return QualityIssue(
                category=QualityIssueCategory.DETAIL,
                severity=QualityIssueSeverity.MINOR,
                description="; ".join(issues),
                impact_score=0.2 * len(issues),
            )
        return None

    def _check_professionalism(self, request: QualityImprovementRequest) -> Optional[QualityIssue]:
        """检查专业性问题。"""
        content = request.delivery_content

        issues = []

        # 检查是否有不专业的表达
        informal_patterns = ["!!!", "???", "...", "随便", "可能", "大概", "maybe", "idk"]
        informal_count = sum(1 for pattern in informal_patterns if pattern in content)

        if informal_count >= 2:
            issues.append("表达过于随意，缺乏专业性")

        # 检查是否有拼写/语法问题的模式
        if self._detect_language_issues(content):
            issues.append("存在语言表达问题")

        if issues:
            return QualityIssue(
                category=QualityIssueCategory.PROFESSIONALISM,
                severity=QualityIssueSeverity.MINOR,
                description="; ".join(issues),
                impact_score=0.15,
            )
        return None

    def _analyze_rejection_reason(self, rejection_reason: str) -> List[QualityIssue]:
        """分析拒绝原因，提取质量问题。"""
        issues = []

        reason_lower = rejection_reason.lower()

        # 映射拒绝原因到问题类别
        if any(kw in reason_lower for kw in ["不完整", "missing", "incomplete"]):
            issues.append(QualityIssue(
                category=QualityIssueCategory.COMPLETENESS,
                severity=QualityIssueSeverity.MAJOR,
                description="雇主指出内容不完整",
                evidence=rejection_reason,
                impact_score=0.4,
            ))

        if any(kw in reason_lower for kw in ["错误", "错误", "incorrect", "wrong"]):
            issues.append(QualityIssue(
                category=QualityIssueCategory.ACCURACY,
                severity=QualityIssueSeverity.CRITICAL,
                description="雇主指出内容存在错误",
                evidence=rejection_reason,
                impact_score=0.5,
            ))

        if any(kw in reason_lower for kw in ["格式", "format"]):
            issues.append(QualityIssue(
                category=QualityIssueCategory.FORMAT,
                severity=QualityIssueSeverity.MINOR,
                description="雇主指出格式不符合要求",
                evidence=rejection_reason,
                impact_score=0.2,
            ))

        return issues

    def _generate_suggestions(
        self,
        issues: List[QualityIssue],
        request: QualityImprovementRequest,
    ) -> List[ImprovementSuggestion]:
        """生成改进建议。"""
        suggestions = []

        # 按类别分组问题
        issues_by_category = {}
        for issue in issues:
            category = issue.category.value
            if category not in issues_by_category:
                issues_by_category[category] = []
            issues_by_category[category].append(issue)

        # 为每个类别生成建议
        suggestion_templates = {
            "completeness": ImprovementSuggestion(
                title="提升内容完整性",
                description="确保交付内容回应所有验收标准，提供完整的交付物",
                priority="high",
                estimated_effort="medium",
                action_items=[
                    "在提交前对照验收标准逐一检查",
                    "创建交付清单 (checklist) 确保无遗漏",
                    "如有不确定，主动与雇主沟通确认",
                ],
            ),
            "accuracy": ImprovementSuggestion(
                title="提高准确性",
                description="仔细核对交付内容，确保数据和信息的准确性",
                priority="high",
                estimated_effort="high",
                action_items=[
                    "提交前进行至少一次全面复核",
                    "对关键数据进行二次验证",
                    "使用交叉验证方法确认答案",
                ],
            ),
            "format": ImprovementSuggestion(
                title="改进格式规范",
                description="按照要求的格式组织内容，提升可读性",
                priority="medium",
                estimated_effort="low",
                action_items=[
                    "仔细阅读格式要求",
                    "使用分段、列表等方式组织内容",
                    "参考优质交付样例的格式",
                ],
            ),
            "detail": ImprovementSuggestion(
                title="增加内容详细度",
                description="提供更详细、更有深度的交付内容",
                priority="medium",
                estimated_effort="medium",
                action_items=[
                    "不仅提供答案，还要提供推理过程",
                    "用具体数据和事实支撑结论",
                    "适当提供背景和上下文信息",
                ],
            ),
            "professionalism": ImprovementSuggestion(
                title="提升专业性",
                description="使用专业、规范的语言和表达方式",
                priority="medium",
                estimated_effort="low",
                action_items=[
                    "避免使用口语化、随意的表达",
                    "注意拼写和语法",
                    "保持客观、中立的语气",
                ],
            ),
        }

        for category, category_issues in issues_by_category.items():
            if category in suggestion_templates:
                suggestion = suggestion_templates[category]
                suggestion.related_issues = [issue.issue_id for issue in category_issues]

                # 根据严重程度调整优先级
                if any(issue.severity == QualityIssueSeverity.CRITICAL for issue in category_issues):
                    suggestion.priority = "high"
                elif any(issue.severity == QualityIssueSeverity.MAJOR for issue in category_issues):
                    suggestion.priority = "medium"

                suggestions.append(suggestion)

        return suggestions

    def _recommend_training(
        self,
        issues: List[QualityIssue],
        task_category: str,
    ) -> List[TrainingResource]:
        """推荐培训资源。"""
        if not issues:
            return []

        # 收集需要的技能
        needed_skills = set()

        skill_mapping = {
            QualityIssueCategory.COMPLETENESS: ["attention_to_detail", "quality"],
            QualityIssueCategory.ACCURACY: ["accuracy", "attention_to_detail"],
            QualityIssueCategory.FORMAT: ["professionalism"],
            QualityIssueCategory.DETAIL: ["analytical_thinking"],
            QualityIssueCategory.PROFESSIONALISM: ["communication", "professionalism"],
            QualityIssueCategory.TIMELINESS: ["time_management"],
            QualityIssueCategory.COMMUNICATION: ["communication"],
        }

        for issue in issues:
            needed_skills.update(skill_mapping.get(issue.category, []))

        # 添加任务类别相关的技能
        category_skills = {
            "data_annotation": ["data_annotation"],
            "content_moderation": ["content_moderation"],
            "survey": ["survey", "reporting"],
            "transcription": ["transcription", "listening"],
            "image_collection": ["photography", "image_quality"],
        }
        needed_skills.update(category_skills.get(task_category, []))

        # 匹配培训资源
        recommended = []
        for resource in self._training_resources:
            if any(skill in resource.relevant_skills for skill in needed_skills):
                recommended.append(resource)

        # 按相关性和难度排序
        recommended.sort(key=lambda r: (
            -len(set(r.relevant_skills) & needed_skills),
            r.difficulty == "beginner",  # 优先推荐初级
        ))

        return recommended[:3]  # 最多推荐 3 个

    def _calculate_quality_score(self, issues: List[QualityIssue]) -> float:
        """计算质量得分。"""
        if not issues:
            return 1.0

        # 计算总影响分数
        total_impact = 0.0
        for issue in issues:
            # 严重程度加成
            severity_multiplier = {
                QualityIssueSeverity.CRITICAL: 1.5,
                QualityIssueSeverity.MAJOR: 1.0,
                QualityIssueSeverity.MINOR: 0.5,
            }
            total_impact += issue.impact_score * severity_multiplier.get(issue.severity, 1.0)

        # 质量得分 = 1 - 总影响（最低 0）
        return max(0.0, 1.0 - total_impact)

    def _generate_message(
        self,
        quality_score: float,
        issues: List[QualityIssue],
        suggestions: List[ImprovementSuggestion],
    ) -> str:
        """生成分析消息。"""
        if quality_score >= 0.8:
            base = "质量良好，"
        elif quality_score >= 0.6:
            base = "质量一般，"
        elif quality_score >= 0.4:
            base = "质量需改进，"
        else:
            base = "质量较差，"

        if issues:
            issue_summary = f"发现{len(issues)}项质量问题"
        else:
            issue_summary = "未发现明显问题"

        if suggestions:
            suggestion_summary = f"生成{len(suggestions)}条改进建议"
        else:
            suggestion_summary = "无需特别改进"

        return f"{base}{issue_summary}，{suggestion_summary}。"

    # ========== 辅助方法 ==========

    def _extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """提取关键词。"""
        # 简化实现：按字分割
        chinese_chars = []
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                chinese_chars.append(char)
        return list(set(chinese_chars))[:max_keywords]

    def _detect_obvious_errors(self, content: str) -> bool:
        """检测明显错误。"""
        # 简化实现：检查是否有明显的错误模式
        error_patterns = ["不知道", "不清楚", "随便", "n/a", "N/A", "???"]
        return any(pattern in content for pattern in error_patterns)

    def _detect_language_issues(self, content: str) -> bool:
        """检测语言问题。"""
        # 检查是否有过多的标点
        informal_count = content.count("!!!") + content.count("???") + content.count("。。。")
        # 也检查中文标点重复
        informal_count += content.count("！！！！") + content.count("。。。。。")
        return informal_count >= 1

    def _update_worker_history(self, worker_id: str, quality_score: float) -> None:
        """更新工人质量历史。"""
        if worker_id not in self._worker_quality_history:
            self._worker_quality_history[worker_id] = []
        self._worker_quality_history[worker_id].append(quality_score)

    # ========== 公开方法 ==========

    def get_analysis(self, analysis_id: str) -> Optional[QualityImprovementRecord]:
        """获取分析记录。"""
        return self._improvement_records.get(analysis_id)

    def get_worker_quality_trend(self, worker_id: str) -> Dict[str, Any]:
        """获取工人质量趋势。"""
        history = self._worker_quality_history.get(worker_id, [])

        if not history:
            return {"worker_id": worker_id, "trend": "unknown", "data_points": 0}

        # 计算趋势
        if len(history) >= 3:
            recent_avg = sum(history[-3:]) / 3
            older_avg = sum(history[:3]) / 3 if len(history) > 3 else recent_avg

            if recent_avg > older_avg * 1.1:
                trend = "improving"
            elif recent_avg < older_avg * 0.9:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "worker_id": worker_id,
            "trend": trend,
            "data_points": len(history),
            "average_quality": round(sum(history) / len(history), 3),
            "recent_quality": round(history[-1], 3) if history else 0,
        }

    def get_improvement_stats(self) -> Dict[str, Any]:
        """获取改进统计。"""
        if not self._improvement_records:
            return {"total_analyses": 0}

        records = list(self._improvement_records.values())

        issue_counts = {}
        for record in records:
            for issue in record.issues:
                category = issue.category.value
                issue_counts[category] = issue_counts.get(category, 0) + 1

        avg_quality = sum(r.quality_score for r in records) / len(records)

        return {
            "total_analyses": len(records),
            "average_quality_score": round(avg_quality, 3),
            "issue_distribution": issue_counts,
            "most_common_issue": max(issue_counts.items(), key=lambda x: x[1])[0] if issue_counts else None,
        }


# 全局单例
quality_improvement_service = QualityImprovementService()
