"""
P7 技能认证考试服务

提供：
- 题库管理系统
- 在线考试功能
- 自动评分与认证
- 认证标识展示
"""
import uuid
import random
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from enum import Enum
from collections import defaultdict


# ==================== 数据模型 ====================

class QuestionType(str, Enum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    CODE_COMPLETION = "code_completion"
    PRACTICAL_TASK = "practical_task"


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class ExamStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    GRADED = "graded"
    CERTIFIED = "certified"
    EXPIRED = "expired"


class CertificationLevel(str, Enum):
    FOUNDATION = "foundation"
    INTERMEDIATE = "intermediate"
    PROFESSIONAL = "professional"
    EXPERT = "expert"


class Question(BaseModel):
    """题目模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    certification_id: str
    question_type: QuestionType
    difficulty: DifficultyLevel
    question_text: str
    question_stem: Optional[Dict[str, Any]] = None
    options: Optional[List[Dict[str, str]]] = None
    correct_answer: Any
    score: float = 1.0
    partial_credit: bool = False
    explanation: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    order: int = 0


class ExamAttempt(BaseModel):
    """考试尝试记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    certification_id: str
    user_id: str
    tenant_id: Optional[str] = None
    status: ExamStatus = ExamStatus.NOT_STARTED
    questions: List[Question] = Field(default_factory=list)
    answers: List[Dict[str, Any]] = Field(default_factory=list)
    score: Optional[float] = None
    max_score: Optional[float] = None
    percentage: Optional[float] = None
    passed: Optional[bool] = None
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    time_spent_seconds: Optional[int] = None
    feedback: Optional[str] = None
    question_results: List[Dict[str, Any]] = Field(default_factory=list)


class Certification(BaseModel):
    """认证模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    skill_category: str
    skill_tag_id: Optional[str] = None
    level: CertificationLevel = CertificationLevel.FOUNDATION
    passing_score: float = 70.0
    time_limit_minutes: int = 60
    total_questions: int = 20
    valid_days: int = 365
    exam_fee: float = 0.0
    renewal_fee: float = 0.0
    status: str = "draft"
    total_attempts: int = 0
    pass_rate: float = 0.0
    average_score: float = 0.0
    badge_icon_url: Optional[str] = None
    badge_color: Optional[str] = None
    created_by: str
    created_at: datetime = Field(default_factory=datetime.now)


class CertificationHolder(BaseModel):
    """认证持有者"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    certification_id: str
    certification_name: str
    certification_level: CertificationLevel
    skill_category: str
    user_id: str
    tenant_id: Optional[str] = None
    obtained_at: datetime
    expires_at: Optional[datetime] = None
    certificate_number: str
    certificate_url: Optional[str] = None
    status: str = "active"
    renewal_count: int = 0


class ExamResult(BaseModel):
    """考试结果"""
    exam_id: str
    certification_id: str
    user_id: str
    status: ExamStatus
    score: float
    max_score: float
    percentage: float
    passed: bool
    passing_score: float
    time_spent_seconds: int
    time_limit_seconds: int
    correct_count: int
    total_count: int
    question_details: List[Dict[str, Any]]
    feedback: Optional[str] = None
    certificate_earned: Optional[Dict[str, Any]] = None


# ==================== 服务类 ====================

class CertificationService:
    """技能认证考试服务"""

    def __init__(self):
        # 内存存储（实际应使用数据库）
        self._certifications: Dict[str, Certification] = {}
        self._questions: Dict[str, Question] = {}
        self._exam_attempts: Dict[str, ExamAttempt] = {}
        self._certification_holders: Dict[str, CertificationHolder] = {}
        self._question_banks: Dict[str, Dict[str, Any]] = {}

    # ==================== 认证管理 ====================

    def create_certification(self, data: Dict[str, Any]) -> Certification:
        """创建认证考试"""
        cert = Certification(
            id=str(uuid.uuid4()),
            name=data['name'],
            description=data.get('description'),
            skill_category=data['skill_category'],
            skill_tag_id=data.get('skill_tag_id'),
            level=CertificationLevel(data.get('level', 'foundation')),
            passing_score=data.get('passing_score', 70.0),
            time_limit_minutes=data.get('time_limit_minutes', 60),
            total_questions=data.get('total_questions', 20),
            valid_days=data.get('valid_days', 365),
            exam_fee=data.get('exam_fee', 0.0),
            renewal_fee=data.get('renewal_fee', 0.0),
            status=data.get('status', 'draft'),
            badge_icon_url=data.get('badge_icon_url'),
            badge_color=data.get('badge_color'),
            created_by=data['created_by']
        )
        self._certifications[cert.id] = cert
        return cert

    def get_certification(self, cert_id: str) -> Optional[Certification]:
        """获取认证详情"""
        return self._certifications.get(cert_id)

    def list_certifications(self, status: Optional[str] = None,
                           skill_category: Optional[str] = None,
                           level: Optional[str] = None) -> List[Certification]:
        """列出认证考试"""
        certs = list(self._certifications.values())

        if status:
            certs = [c for c in certs if c.status == status]
        if skill_category:
            certs = [c for c in certs if c.skill_category == skill_category]
        if level:
            certs = [c for c in certs if c.level.value == level]

        return certs

    def update_certification_status(self, cert_id: str, status: str) -> Optional[Certification]:
        """更新认证状态"""
        if cert_id in self._certifications:
            self._certifications[cert_id].status = status
            return self._certifications[cert_id]
        return None

    def delete_certification(self, cert_id: str) -> bool:
        """删除认证"""
        if cert_id in self._certifications:
            # 删除关联题目
            question_ids = [q.id for q in self._questions.values() if q.certification_id == cert_id]
            for qid in question_ids:
                del self._questions[qid]
            del self._certifications[cert_id]
            return True
        return False

    # ==================== 题库管理 ====================

    def create_question(self, data: Dict[str, Any]) -> Question:
        """创建题目"""
        question = Question(
            id=str(uuid.uuid4()),
            certification_id=data['certification_id'],
            question_type=QuestionType(data['question_type']),
            difficulty=DifficultyLevel(data.get('difficulty', 'medium')),
            question_text=data['question_text'],
            question_stem=data.get('question_stem'),
            options=data.get('options'),
            correct_answer=data['correct_answer'],
            score=data.get('score', 1.0),
            partial_credit=data.get('partial_credit', False),
            explanation=data.get('explanation'),
            tags=data.get('tags', []),
            order=data.get('order', 0)
        )
        self._questions[question.id] = question
        return question

    def get_question(self, question_id: str) -> Optional[Question]:
        """获取题目"""
        return self._questions.get(question_id)

    def get_certification_questions(self, cert_id: str) -> List[Question]:
        """获取认证的所有题目"""
        questions = [q for q in self._questions.values() if q.certification_id == cert_id]
        questions.sort(key=lambda x: x.order)
        return questions

    def update_question(self, question_id: str, data: Dict[str, Any]) -> Optional[Question]:
        """更新题目"""
        if question_id in self._questions:
            question = self._questions[question_id]
            for key, value in data.items():
                if hasattr(question, key):
                    setattr(question, key, value)
            return question
        return None

    def delete_question(self, question_id: str) -> bool:
        """删除题目"""
        if question_id in self._questions:
            del self._questions[question_id]
            return True
        return False

    # ==================== 试卷生成 ====================

    def generate_exam_paper(self, cert_id: str, user_id: str) -> Optional[ExamAttempt]:
        """
        生成试卷

        从题库中随机选择题目组成试卷
        """
        if cert_id not in self._certifications:
            return None

        cert = self._certifications[cert_id]
        all_questions = self.get_certification_questions(cert_id)

        if len(all_questions) < cert.total_questions:
            # 题目数量不足
            return None

        # 按难度分层抽样
        questions_by_difficulty = defaultdict(list)
        for q in all_questions:
            questions_by_difficulty[q.difficulty].append(q)

        # 难度分布：easy 30%, medium 50%, hard 20%
        difficulty_distribution = {
            DifficultyLevel.EASY: 0.3,
            DifficultyLevel.MEDIUM: 0.5,
            DifficultyLevel.HARD: 0.2
        }

        selected_questions = []
        for difficulty, ratio in difficulty_distribution.items():
            count = int(cert.total_questions * ratio)
            available = questions_by_difficulty.get(difficulty, [])
            selected = random.sample(available, min(count, len(available)))
            selected_questions.extend(selected)

        # 如果未达到目标数量，从剩余题目中补充
        remaining = cert.total_questions - len(selected_questions)
        if remaining > 0:
            used_ids = {q.id for q in selected_questions}
            remaining_questions = [q for q in all_questions if q.id not in used_ids]
            additional = random.sample(remaining_questions, min(remaining, len(remaining_questions)))
            selected_questions.extend(additional)

        # 创建考试尝试记录
        attempt = ExamAttempt(
            id=str(uuid.uuid4()),
            certification_id=cert_id,
            user_id=user_id,
            status=ExamStatus.NOT_STARTED,
            questions=selected_questions
        )
        self._exam_attempts[attempt.id] = attempt

        return attempt

    # ==================== 考试管理 ====================

    def start_exam(self, attempt_id: str) -> Optional[ExamAttempt]:
        """开始考试"""
        if attempt_id in self._exam_attempts:
            attempt = self._exam_attempts[attempt_id]
            attempt.status = ExamStatus.IN_PROGRESS
            attempt.started_at = datetime.now()
            return attempt
        return None

    def submit_exam(self, attempt_id: str, answers: List[Dict[str, Any]]) -> Optional[ExamResult]:
        """
        提交考试并自动评分

        Returns:
            ExamResult: 考试结果
        """
        if attempt_id not in self._exam_attempts:
            return None

        attempt = self._exam_attempts[attempt_id]
        if attempt.status != ExamStatus.IN_PROGRESS:
            return None

        attempt.answers = answers
        attempt.submitted_at = datetime.now()
        attempt.status = ExamStatus.SUBMITTED

        # 计算用时
        if attempt.started_at:
            attempt.time_spent_seconds = int((attempt.submitted_at - attempt.started_at).total_seconds())

        # 评分
        result = self._grade_exam(attempt)

        # 更新尝试记录
        attempt.score = result.score
        attempt.max_score = result.max_score
        attempt.percentage = result.percentage
        attempt.passed = result.passed
        attempt.status = ExamStatus.GRADED
        attempt.feedback = result.feedback
        attempt.question_results = result.question_details

        # 如果通过，颁发认证
        if result.passed:
            cert = self._certifications[attempt.certification_id]
            certificate = self._issue_certificate(cert, attempt.user_id, attempt.tenant_id, attempt.id)
            attempt.status = ExamStatus.CERTIFIED
            result.certificate_earned = {
                'certificate_id': certificate.id,
                'certificate_number': certificate.certificate_number,
                'expires_at': certificate.expires_at.isoformat() if certificate.expires_at else None
            }

        # 更新认证统计
        self._update_certification_stats(attempt.certification_id, result.passed, result.percentage)

        return result

    def _grade_exam(self, attempt: ExamAttempt) -> ExamResult:
        """
        自动评分
        """
        cert = self._certifications[attempt.certification_id]
        answers_dict = {a.get('question_id'): a.get('answer') for a in attempt.answers}

        total_score = 0.0
        max_score = 0.0
        correct_count = 0
        question_details = []

        for question in attempt.questions:
            max_score += question.score
            user_answer = answers_dict.get(question.id)

            is_correct, earned_score = self._grade_single_question(question, user_answer)

            total_score += earned_score
            if is_correct:
                correct_count += 1

            question_details.append({
                'question_id': question.id,
                'question_text': question.question_text[:50] + '...' if len(question.question_text) > 50 else question.question_text,
                'question_type': question.question_type.value,
                'correct_answer': self._format_answer(question.correct_answer, question.question_type),
                'user_answer': self._format_answer(user_answer, question.question_type) if user_answer else None,
                'is_correct': is_correct,
                'earned_score': earned_score,
                'max_score': question.score,
                'explanation': question.explanation
            })

        percentage = (total_score / max_score * 100) if max_score > 0 else 0
        passed = percentage >= cert.passing_score

        # 生成反馈
        if passed:
            feedback = f"恭喜您通过了 {cert.name} 考试！您的得分为 {percentage:.1f}%。"
            if percentage >= 90:
                feedback += " 成绩优异！"
            elif percentage >= 80:
                feedback += " 成绩良好！"
        else:
            feedback = f"很遗憾，您未能通过 {cert.name} 考试。您的得分为 {percentage:.1f}%，及格分数为 {cert.passing_score}%。"

        return ExamResult(
            exam_id=attempt.id,
            certification_id=attempt.certification_id,
            user_id=attempt.user_id,
            status=ExamStatus.GRADED,
            score=total_score,
            max_score=max_score,
            percentage=percentage,
            passed=passed,
            passing_score=cert.passing_score,
            time_spent_seconds=attempt.time_spent_seconds or 0,
            time_limit_seconds=cert.time_limit_minutes * 60,
            correct_count=correct_count,
            total_count=len(attempt.questions),
            question_details=question_details,
            feedback=feedback
        )

    def _grade_single_question(self, question: Question, user_answer: Any) -> Tuple[bool, float]:
        """
        评分单个题目
        """
        if question.question_type == QuestionType.SINGLE_CHOICE:
            is_correct = str(user_answer).upper() == str(question.correct_answer).upper()
            return is_correct, question.score if is_correct else 0.0

        elif question.question_type == QuestionType.MULTIPLE_CHOICE:
            # 多选题：全部选对得满分，选对部分得部分分
            correct_set = set(str(a).upper() for a in question.correct_answer)
            user_set = set(str(a).upper() for a in (user_answer or []))

            if correct_set == user_set:
                return True, question.score
            elif user_set.issubset(correct_set) and len(user_set) > 0:
                # 部分正确
                if question.partial_credit:
                    partial_score = len(user_set & correct_set) / len(correct_set) * question.score
                    return False, partial_score
                return False, 0.0
            return False, 0.0

        elif question.question_type == QuestionType.TRUE_FALSE:
            is_correct = str(user_answer).lower() == str(question.correct_answer).lower()
            return is_correct, question.score if is_correct else 0.0

        elif question.question_type in [QuestionType.SHORT_ANSWER, QuestionType.CODE_COMPLETION]:
            # 简答和代码填空：精确匹配或包含关键词
            if isinstance(question.correct_answer, list):
                # 多个可选答案
                is_correct = any(
                    str(user_answer).strip().lower() == str(ans).strip().lower()
                    for ans in question.correct_answer
                )
            else:
                is_correct = str(user_answer).strip().lower() == str(question.correct_answer).strip().lower()
            return is_correct, question.score if is_correct else 0.0

        elif question.question_type == QuestionType.PRACTICAL_TASK:
            # 实操题：需要特殊评分逻辑（这里简化处理）
            # 实际应由人工评分或通过测试用例
            return False, 0.0

        return False, 0.0

    def _format_answer(self, answer: Any, question_type: QuestionType) -> str:
        """格式化答案显示"""
        if answer is None:
            return "未作答"

        if question_type == QuestionType.MULTIPLE_CHOICE:
            if isinstance(answer, list):
                return ", ".join(str(a) for a in answer)
            return str(answer)

        return str(answer)

    # ==================== 证书管理 ====================

    def _issue_certificate(self, cert: Certification, user_id: str, tenant_id: Optional[str],
                          attempt_id: str) -> CertificationHolder:
        """颁发证书"""
        # 生成证书编号
        cert_number = f"CERT-{cert.skill_category.upper()[:3]}-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

        # 计算过期时间
        expires_at = datetime.now() + timedelta(days=cert.valid_days) if cert.valid_days > 0 else None

        holder = CertificationHolder(
            id=str(uuid.uuid4()),
            certification_id=cert.id,
            certification_name=cert.name,
            certification_level=cert.level,
            skill_category=cert.skill_category,
            user_id=user_id,
            tenant_id=tenant_id,
            obtained_at=datetime.now(),
            expires_at=expires_at,
            certificate_number=cert_number,
            status="active"
        )
        self._certification_holders[holder.id] = holder
        return holder

    def get_user_certifications(self, user_id: str) -> List[CertificationHolder]:
        """获取用户的认证"""
        holders = [h for h in self._certification_holders.values() if h.user_id == user_id]
        # 检查过期
        now = datetime.now()
        for h in holders:
            if h.expires_at and h.expires_at < now and h.status == "active":
                h.status = "expired"
        return holders

    def get_certification_holders(self, cert_id: str) -> List[CertificationHolder]:
        """获取认证的持有者列表"""
        return [h for h in self._certification_holders.values() if h.certification_id == cert_id]

    def verify_certificate(self, certificate_number: str) -> Optional[Dict[str, Any]]:
        """验证证书"""
        holder = next((h for h in self._certification_holders.values() if h.certificate_number == certificate_number), None)
        if not holder:
            return None

        # 检查过期
        now = datetime.now()
        if holder.expires_at and holder.expires_at < now:
            status = "expired"
        else:
            status = holder.status

        return {
            'certificate_number': certificate_number,
            'holder_name': holder.certification_name,
            'level': holder.certification_level.value,
            'skill_category': holder.skill_category,
            'obtained_at': holder.obtained_at.isoformat(),
            'expires_at': holder.expires_at.isoformat() if holder.expires_at else None,
            'status': status,
            'valid': status == "active"
        }

    def _update_certification_stats(self, cert_id: str, passed: bool, score: float):
        """更新认证统计信息"""
        if cert_id not in self._certifications:
            return

        cert = self._certifications[cert_id]
        cert.total_attempts += 1

        # 更新通过率
        passed_count = int(cert.pass_rate * (cert.total_attempts - 1))
        if passed:
            passed_count += 1
        cert.pass_rate = passed_count / cert.total_attempts

        # 更新平均分
        cert.average_score = (cert.average_score * (cert.total_attempts - 1) + score) / cert.total_attempts

    # ==================== 统计与分析 ====================

    def get_exam_statistics(self, cert_id: str) -> Dict[str, Any]:
        """获取考试统计"""
        attempts = [a for a in self._exam_attempts.values() if a.certification_id == cert_id]

        if not attempts:
            return {
                'total_attempts': 0,
                'pass_rate': 0,
                'average_score': 0,
                'average_time_spent': 0
            }

        completed = [a for a in attempts if a.status in [ExamStatus.GRADED, ExamStatus.CERTIFIED]]
        passed = sum(1 for a in completed if a.passed)

        avg_score = sum(a.percentage or 0 for a in completed) / len(completed) if completed else 0
        avg_time = sum(a.time_spent_seconds or 0 for a in completed) / len(completed) if completed else 0

        return {
            'total_attempts': len(attempts),
            'completed_attempts': len(completed),
            'passed_attempts': passed,
            'pass_rate': passed / len(completed) * 100 if completed else 0,
            'average_score': avg_score,
            'average_time_spent': avg_time,
            'certification_rate': sum(1 for a in attempts if a.status == ExamStatus.CERTIFIED) / len(attempts) * 100 if attempts else 0
        }

    def get_question_statistics(self, question_id: str) -> Dict[str, Any]:
        """获取题目统计"""
        if question_id not in self._questions:
            return {}

        question = self._questions[question_id]

        # 统计答题情况
        total_attempts = 0
        correct_count = 0

        for attempt in self._exam_attempts.values():
            for result in attempt.question_results:
                if result.get('question_id') == question_id:
                    total_attempts += 1
                    if result.get('is_correct'):
                        correct_count += 1

        return {
            'question_id': question_id,
            'question_text': question.question_text[:50] + '...' if len(question.question_text) > 50 else question.question_text,
            'difficulty': question.difficulty.value,
            'total_attempts': total_attempts,
            'correct_count': correct_count,
            'correct_rate': correct_count / total_attempts * 100 if total_attempts > 0 else 0
        }


# 全局服务实例
certification_service = CertificationService()
