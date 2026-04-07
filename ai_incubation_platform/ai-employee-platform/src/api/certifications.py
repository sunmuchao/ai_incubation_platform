"""
P7 技能认证考试 API

提供：
- 题库管理系统
- 在线考试功能
- 自动评分与认证
- 认证标识展示
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/certifications", tags=["P7-技能认证"])

# 导入服务
from services.certification_service import (
    certification_service, Certification, Question, ExamAttempt,
    CertificationHolder, ExamResult, ExamStatus
)


# ==================== 请求/响应模型 ====================

class CertificationCreate(BaseModel):
    """创建认证考试"""
    name: str
    description: Optional[str] = None
    skill_category: str
    skill_tag_id: Optional[str] = None
    level: str = "foundation"  # foundation, intermediate, professional, expert
    passing_score: float = Field(ge=0, le=100, default=70.0)
    time_limit_minutes: int = Field(ge=1, default=60)
    total_questions: int = Field(ge=1, default=20)
    valid_days: int = Field(ge=0, default=365)
    exam_fee: float = Field(ge=0, default=0.0)
    renewal_fee: float = Field(ge=0, default=0.0)
    badge_icon_url: Optional[str] = None
    badge_color: Optional[str] = None


class CertificationUpdate(BaseModel):
    """更新认证考试"""
    name: Optional[str] = None
    description: Optional[str] = None
    passing_score: Optional[float] = Field(None, ge=0, le=100)
    time_limit_minutes: Optional[int] = Field(None, ge=1)
    total_questions: Optional[int] = Field(None, ge=1)
    valid_days: Optional[int] = Field(None, ge=0)
    exam_fee: Optional[float] = Field(None, ge=0)
    renewal_fee: Optional[float] = Field(None, ge=0)
    badge_icon_url: Optional[str] = None
    badge_color: Optional[str] = None


class QuestionCreate(BaseModel):
    """创建题目"""
    certification_id: str
    question_type: str  # single_choice, multiple_choice, true_false, short_answer, code_completion, practical_task
    difficulty: str = "medium"  # easy, medium, hard, expert
    question_text: str
    question_stem: Optional[Dict[str, Any]] = None
    options: Optional[List[Dict[str, str]]] = None
    correct_answer: Any
    score: float = Field(ge=0, default=1.0)
    partial_credit: bool = False
    explanation: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    order: int = Field(ge=0, default=0)


class QuestionUpdate(BaseModel):
    """更新题目"""
    question_text: Optional[str] = None
    question_stem: Optional[Dict[str, Any]] = None
    options: Optional[List[Dict[str, str]]] = None
    correct_answer: Optional[Any] = None
    score: Optional[float] = None
    partial_credit: Optional[bool] = None
    explanation: Optional[str] = None
    tags: Optional[List[str]] = None
    order: Optional[int] = None


class AnswerSubmit(BaseModel):
    """提交的答案"""
    question_id: str
    answer: Any


class ExamStartResponse(BaseModel):
    """开始考试响应"""
    exam_id: str
    certification_id: str
    certification_name: str
    time_limit_minutes: int
    total_questions: int
    questions: List[Dict[str, Any]]
    started_at: str
    expires_at: str


class ExamSubmitRequest(BaseModel):
    """提交考试请求"""
    answers: List[AnswerSubmit]


class ExamResultResponse(BaseModel):
    """考试结果响应"""
    exam_id: str
    certification_id: str
    certification_name: str
    status: str
    score: float
    max_score: float
    percentage: float
    passed: bool
    passing_score: float
    time_spent_seconds: int
    time_limit_seconds: int
    correct_count: int
    total_count: int
    feedback: str
    question_details: List[Dict[str, Any]]
    certificate_earned: Optional[Dict[str, Any]] = None


class CertificateResponse(BaseModel):
    """证书响应"""
    id: str
    certification_name: str
    certification_level: str
    skill_category: str
    certificate_number: str
    obtained_at: str
    expires_at: Optional[str]
    status: str


# ==================== 认证管理端点 ====================

@router.post("", response_model=Dict[str, Any])
async def create_certification(cert: CertificationCreate, user_id: str = Query(...)):
    """
    创建技能认证考试

    - **name**: 认证名称
    - **skill_category**: 技能分类
    - **level**: 认证等级 (foundation/intermediate/professional/expert)
    - **passing_score**: 及格分数 (0-100)
    - **time_limit_minutes**: 考试时限 (分钟)
    - **total_questions**: 题目总数
    - **valid_days**: 认证有效期 (天，0 表示永久有效)
    """
    data = cert.model_dump()
    data['created_by'] = user_id

    certification = certification_service.create_certification(data)

    return {
        "message": "认证考试创建成功",
        "certification": {
            "id": certification.id,
            "name": certification.name,
            "skill_category": certification.skill_category,
            "level": certification.level.value,
            "status": certification.status
        }
    }


@router.get("", response_model=Dict[str, Any])
async def list_certifications(
    status: Optional[str] = Query(None),
    skill_category: Optional[str] = Query(None),
    level: Optional[str] = Query(None)
):
    """
    获取认证考试列表

    可按状态、技能分类、等级过滤
    """
    certifications = certification_service.list_certifications(
        status=status,
        skill_category=skill_category,
        level=level
    )

    return {
        "total": len(certifications),
        "certifications": [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "skill_category": c.skill_category,
                "level": c.level.value,
                "passing_score": c.passing_score,
                "time_limit_minutes": c.time_limit_minutes,
                "total_questions": c.total_questions,
                "exam_fee": c.exam_fee,
                "pass_rate": round(c.pass_rate * 100, 1),
                "status": c.status
            }
            for c in certifications
        ]
    }


@router.get("/{cert_id}", response_model=Dict[str, Any])
async def get_certification(cert_id: str):
    """
    获取认证考试详情
    """
    certification = certification_service.get_certification(cert_id)
    if not certification:
        raise HTTPException(status_code=404, detail="认证考试不存在")

    questions = certification_service.get_certification_questions(cert_id)

    return {
        "certification": {
            "id": certification.id,
            "name": certification.name,
            "description": certification.description,
            "skill_category": certification.skill_category,
            "level": certification.level.value,
            "passing_score": certification.passing_score,
            "time_limit_minutes": certification.time_limit_minutes,
            "total_questions": len(questions),
            "valid_days": certification.valid_days,
            "exam_fee": certification.exam_fee,
            "renewal_fee": certification.renewal_fee,
            "pass_rate": round(certification.pass_rate * 100, 1),
            "average_score": round(certification.average_score, 1),
            "status": certification.status,
            "badge_icon_url": certification.badge_icon_url,
            "badge_color": certification.badge_color,
            "created_at": certification.created_at.isoformat()
        },
        "question_count": len(questions)
    }


@router.post("/{cert_id}/publish")
async def publish_certification(cert_id: str):
    """
    发布认证考试

    将认证状态从 draft 改为 active，使其对用户可见
    """
    certification = certification_service.update_certification_status(cert_id, "active")
    if not certification:
        raise HTTPException(status_code=404, detail="认证考试不存在")

    return {
        "message": "认证考试已发布",
        "certification_id": cert_id,
        "status": "active"
    }


@router.delete("/{cert_id}")
async def delete_certification(cert_id: str):
    """
    删除认证考试
    """
    success = certification_service.delete_certification(cert_id)
    if not success:
        raise HTTPException(status_code=404, detail="认证考试不存在")

    return {"message": "认证考试已删除"}


# ==================== 题库管理端点 ====================

@router.post("/{cert_id}/questions", response_model=Dict[str, Any])
async def create_question(cert_id: str, question: QuestionCreate, user_id: str = Query(...)):
    """
    创建考试题目

    - **question_type**: 题目类型 (single_choice/multiple_choice/true_false/short_answer/code_completion/practical_task)
    - **difficulty**: 难度等级 (easy/medium/hard/expert)
    - **question_text**: 题目描述
    - **options**: 选项列表（选择题需要）
    - **correct_answer**: 正确答案
    - **score**: 题目分值
    - **explanation**: 答案解析
    """
    data = question.model_dump()
    data['created_by'] = user_id

    # 验证认证 ID 一致性
    if data['certification_id'] != cert_id:
        raise HTTPException(status_code=400, detail="certification_id 不匹配")

    created = certification_service.create_question(data)

    return {
        "message": "题目创建成功",
        "question": {
            "id": created.id,
            "question_type": created.question_type.value,
            "difficulty": created.difficulty.value,
            "score": created.score
        }
    }


@router.get("/{cert_id}/questions", response_model=Dict[str, Any])
async def get_certification_questions(cert_id: str):
    """
    获取认证考试的所有题目
    """
    if cert_id not in certification_service._certifications:
        raise HTTPException(status_code=404, detail="认证考试不存在")

    questions = certification_service.get_certification_questions(cert_id)

    return {
        "certification_id": cert_id,
        "total": len(questions),
        "questions": [
            {
                "id": q.id,
                "question_type": q.question_type.value,
                "difficulty": q.difficulty.value,
                "question_text": q.question_text[:100] + '...' if len(q.question_text) > 100 else q.question_text,
                "score": q.score,
                "order": q.order,
                "tags": q.tags
            }
            for q in questions
        ]
    }


@router.get("/questions/{question_id}", response_model=Dict[str, Any])
async def get_question(question_id: str):
    """
    获取题目详情
    """
    question = certification_service.get_question(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")

    return {
        "question": {
            "id": question.id,
            "certification_id": question.certification_id,
            "question_type": question.question_type.value,
            "difficulty": question.difficulty.value,
            "question_text": question.question_text,
            "question_stem": question.question_stem,
            "options": question.options,
            "correct_answer": question.correct_answer,
            "score": question.score,
            "partial_credit": question.partial_credit,
            "explanation": question.explanation,
            "tags": question.tags,
            "order": question.order
        }
    }


@router.put("/questions/{question_id}")
async def update_question(question_id: str, update: QuestionUpdate):
    """
    更新题目
    """
    data = update.model_dump(exclude_none=True)
    question = certification_service.update_question(question_id, data)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")

    return {"message": "题目更新成功"}


@router.delete("/questions/{question_id}")
async def delete_question(question_id: str):
    """
    删除题目
    """
    success = certification_service.delete_question(question_id)
    if not success:
        raise HTTPException(status_code=404, detail="题目不存在")

    return {"message": "题目已删除"}


# ==================== 考试端点 ====================

@router.post("/{cert_id}/start", response_model=ExamStartResponse)
async def start_exam(cert_id: str, user_id: str = Query(...), tenant_id: Optional[str] = Query(None)):
    """
    开始考试

    系统会自动从题库中随机生成试卷
    """
    certification = certification_service.get_certification(cert_id)
    if not certification:
        raise HTTPException(status_code=404, detail="认证考试不存在")

    if certification.status != "active":
        raise HTTPException(status_code=400, detail="认证考试尚未发布")

    # 生成试卷
    attempt = certification_service.generate_exam_paper(cert_id, user_id)
    if not attempt:
        raise HTTPException(status_code=400, detail="无法生成试卷，题目数量不足")

    # 设置租户信息
    attempt.tenant_id = tenant_id

    # 开始考试
    attempt = certification_service.start_exam(attempt.id)

    # 计算过期时间
    expires_at = datetime.now() + __import__('datetime').timedelta(minutes=certification.time_limit_minutes)

    # 返回题目（不含答案）
    questions_data = []
    for q in attempt.questions:
        questions_data.append({
            "id": q.id,
            "question_type": q.question_type.value,
            "question_text": q.question_text,
            "question_stem": q.question_stem,
            "options": q.options,
            "score": q.score
        })

    return ExamStartResponse(
        exam_id=attempt.id,
        certification_id=cert_id,
        certification_name=certification.name,
        time_limit_minutes=certification.time_limit_minutes,
        total_questions=len(attempt.questions),
        questions=questions_data,
        started_at=attempt.started_at.isoformat(),
        expires_at=expires_at.isoformat()
    )


@router.post("/{cert_id}/submit", response_model=ExamResultResponse)
async def submit_exam(cert_id: str, exam_id: str, request: ExamSubmitRequest, user_id: str = Query(...)):
    """
    提交考试

    系统会自动评分并返回结果
    """
    # 验证考试归属
    attempt = certification_service._exam_attempts.get(exam_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="考试记录不存在")

    if attempt.certification_id != cert_id:
        raise HTTPException(status_code=400, detail="考试 ID 与认证 ID 不匹配")

    if attempt.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权提交此考试")

    # 转换答案格式
    answers = [{"question_id": a.question_id, "answer": a.answer} for a in request.answers]

    # 提交并评分
    result = certification_service.submit_exam(exam_id, answers)
    if not result:
        raise HTTPException(status_code=400, detail="无法提交考试")

    certification = certification_service.get_certification(cert_id)

    return ExamResultResponse(
        exam_id=result.exam_id,
        certification_id=result.certification_id,
        certification_name=certification.name if certification else cert_id,
        status=result.status.value,
        score=result.score,
        max_score=result.max_score,
        percentage=result.percentage,
        passed=result.passed,
        passing_score=result.passing_score,
        time_spent_seconds=result.time_spent_seconds,
        time_limit_seconds=result.time_limit_seconds,
        correct_count=result.correct_count,
        total_count=result.total_count,
        feedback=result.feedback,
        question_details=result.question_details,
        certificate_earned=result.certificate_earned
    )


@router.get("/attempts/{exam_id}")
async def get_exam_attempt(exam_id: str, user_id: str = Query(...)):
    """
    获取考试记录
    """
    attempt = certification_service._exam_attempts.get(exam_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="考试记录不存在")

    if attempt.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权查看此考试记录")

    return {
        "exam_id": attempt.id,
        "certification_id": attempt.certification_id,
        "status": attempt.status.value,
        "score": attempt.score,
        "percentage": attempt.percentage,
        "passed": attempt.passed,
        "started_at": attempt.started_at.isoformat() if attempt.started_at else None,
        "submitted_at": attempt.submitted_at.isoformat() if attempt.submitted_at else None,
        "time_spent_seconds": attempt.time_spent_seconds
    }


@router.get("/{cert_id}/statistics")
async def get_certification_statistics(cert_id: str):
    """
    获取认证考试统计信息
    """
    if cert_id not in certification_service._certifications:
        raise HTTPException(status_code=404, detail="认证考试不存在")

    stats = certification_service.get_exam_statistics(cert_id)

    return {
        "certification_id": cert_id,
        "statistics": stats
    }


# ==================== 证书管理端点 ====================

@router.get("/users/{user_id}/certificates", response_model=Dict[str, Any])
async def get_user_certificates(user_id: str):
    """
    获取用户的认证证书列表
    """
    holders = certification_service.get_user_certifications(user_id)

    return {
        "user_id": user_id,
        "total": len(holders),
        "certificates": [
            {
                "id": h.id,
                "certification_name": h.certification_name,
                "certification_level": h.certification_level.value,
                "skill_category": h.skill_category,
                "certificate_number": h.certificate_number,
                "obtained_at": h.obtained_at.isoformat(),
                "expires_at": h.expires_at.isoformat() if h.expires_at else None,
                "status": h.status
            }
            for h in holders
        ]
    }


@router.get("/certificates/{certificate_number}/verify")
async def verify_certificate(certificate_number: str):
    """
    验证证书真伪

    输入证书编号，返回验证结果
    """
    result = certification_service.verify_certificate(certificate_number)
    if not result:
        raise HTTPException(status_code=404, detail="证书不存在")

    return {
        "certificate_number": certificate_number,
        "valid": result['valid'],
        "status": result['status'],
        "holder": {
            "certification_name": result['holder_name'],
            "level": result['level'],
            "skill_category": result['skill_category'],
            "obtained_at": result['obtained_at'],
            "expires_at": result['expires_at']
        }
    }


@router.get("/{cert_id}/holders")
async def get_certification_holders(cert_id: str):
    """
    获取认证持有者列表
    """
    if cert_id not in certification_service._certifications:
        raise HTTPException(status_code=404, detail="认证考试不存在")

    holders = certification_service.get_certification_holders(cert_id)

    return {
        "certification_id": cert_id,
        "total_holders": len(holders),
        "holders": [
            {
                "user_id": h.user_id,
                "certificate_number": h.certificate_number,
                "obtained_at": h.obtained_at.isoformat(),
                "status": h.status
            }
            for h in holders
        ]
    }


# ==================== 健康检查 ====================

@router.get("/health")
async def health_check():
    """
    认证服务健康检查
    """
    return {
        "status": "healthy",
        "service": "certification_service",
        "version": "v1.0",
        "total_certifications": len(certification_service._certifications),
        "total_questions": len(certification_service._questions),
        "total_attempts": len(certification_service._exam_attempts),
        "total_certificates": len(certification_service._certification_holders)
    }
