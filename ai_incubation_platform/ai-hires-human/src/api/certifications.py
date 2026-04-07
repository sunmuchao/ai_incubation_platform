"""
资格认证 API - 提供技能认证和资格管理功能。

功能：
1. 认证类型管理（通用资格、技能专项）
2. 认证申请和考试
3. 认证状态管理
4. 任务资格门槛设置
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.worker_profile_service import worker_profile_service

router = APIRouter(prefix="/api/certifications", tags=["certifications"])


# ========== 数据模型 ==========

class CertificationInfo(BaseModel):
    """认证信息。"""
    certification_id: str
    name: str
    description: str
    required_skills: List[str] = Field(default_factory=list)
    exam_questions: List[Dict] = Field(default_factory=list)
    passing_score: float = 0.8
    is_active: bool = True
    created_at: Optional[str] = None


class CertificationCreateRequest(BaseModel):
    """创建认证请求。"""
    certification_id: str
    name: str
    description: str
    required_skills: List[str] = Field(default_factory=list)
    passing_score: float = 0.8


class CertificationExamRequest(BaseModel):
    """认证考试请求。"""
    worker_id: str
    certification_id: str
    answers: Dict[str, str] = Field(default_factory=dict)


class CertificationExamResponse(BaseModel):
    """认证考试响应。"""
    certification_id: str
    worker_id: str
    passed: bool
    score: float
    message: str


# ========== 内存存储 ==========

_certifications: Dict[str, CertificationInfo] = {}
_worker_certifications: Dict[str, List[str]] = {}  # worker_id -> [certification_ids]
_certification_attempts: Dict[str, List[Dict]] = {}  # worker_id:cert_id -> [attempts]


# ========== 预置认证 ==========

def init_default_certifications():
    """初始化默认认证。"""
    default_certs = [
        CertificationInfo(
            certification_id="general_worker",
            name="通用工人资格",
            description="基础任务完成资格，所有工人都应获得",
            required_skills=[],
            exam_questions=[
                {
                    "question_id": "q1",
                    "question": "任务交付前应检查什么？",
                    "correct_answer": "确保交付内容符合验收标准",
                    "options": [
                        "直接提交，节省时间",
                        "确保交付内容符合验收标准",
                        "等别人先提交参考",
                        "只完成部分内容"
                    ]
                },
                {
                    "question_id": "q2",
                    "question": "发现任务描述不清晰时应如何处理？",
                    "correct_answer": "联系发布者请求澄清",
                    "options": [
                        "按照自己理解直接做",
                        "联系发布者请求澄清",
                        "放弃任务",
                        "随意提交"
                    ]
                }
            ],
            passing_score=0.5,
            is_active=True,
            created_at=datetime.now().isoformat()
        ),
        CertificationInfo(
            certification_id="data_annotation",
            name="数据标注专家",
            description="数据标注任务专业认证",
            required_skills=["annotation", "attention_to_detail"],
            exam_questions=[
                {
                    "question_id": "q1",
                    "question": "图像标注中，标注框应该怎样？",
                    "correct_answer": "紧密包围目标物体，包含完整物体",
                    "options": [
                        "尽可能大，包含背景",
                        "紧密包围目标物体，包含完整物体",
                        "只框选物体中心部分",
                        "随意框选"
                    ]
                },
                {
                    "question_id": "q2",
                    "question": "文本情感标注中，'这个产品还可以'应该标注为？",
                    "correct_answer": "中性/略微正面",
                    "options": [
                        "强烈正面",
                        "中性/略微正面",
                        "负面",
                        "强烈负面"
                    ]
                }
            ],
            passing_score=0.8,
            is_active=True,
            created_at=datetime.now().isoformat()
        ),
        CertificationInfo(
            certification_id="content_moderation",
            name="内容审核员",
            description="内容审核任务专业认证",
            required_skills=["content_review", "judgment"],
            exam_questions=[
                {
                    "question_id": "q1",
                    "question": "发现疑似违规内容时应如何处理？",
                    "correct_answer": "根据审核标准严格判定",
                    "options": [
                        "全部放过，避免误判",
                        "根据审核标准严格判定",
                        "全部标记违规",
                        "随机选择"
                    ]
                }
            ],
            passing_score=0.8,
            is_active=True,
            created_at=datetime.now().isoformat()
        ),
        CertificationInfo(
            certification_id="physical_task",
            name="线下任务资格",
            description="线下跑腿、现场采集等任务资格",
            required_skills=["mobile", "photography"],
            exam_questions=[
                {
                    "question_id": "q1",
                    "question": "线下拍照任务中，如何确保照片质量？",
                    "correct_answer": "光线充足、画面清晰、包含参考物",
                    "options": [
                        "快速拍摄，模糊也可以",
                        "光线充足、画面清晰、包含参考物",
                        "只用前置摄像头",
                        "随便拍一张"
                    ]
                }
            ],
            passing_score=0.8,
            is_active=True,
            created_at=datetime.now().isoformat()
        )
    ]

    for cert in default_certs:
        _certifications[cert.certification_id] = cert


# 初始化默认认证
init_default_certifications()


# ========== API 端点 ==========

@router.get("", response_model=List[CertificationInfo])
async def list_certifications(include_inactive: bool = False):
    """列出所有资格认证。"""
    certs = list(_certifications.values())
    if not include_inactive:
        certs = [c for c in certs if c.is_active]
    return certs


@router.get("/{certification_id}", response_model=CertificationInfo)
async def get_certification(certification_id: str):
    """获取认证详情。"""
    cert = _certifications.get(certification_id)
    if not cert:
        raise HTTPException(
            status_code=404,
            detail=f"Certification not found: {certification_id}"
        )

    # 隐藏考试答案
    cert_copy = CertificationInfo(
        certification_id=cert.certification_id,
        name=cert.name,
        description=cert.description,
        required_skills=cert.required_skills,
        exam_questions=[],  # 不返回题目
        passing_score=cert.passing_score,
        is_active=cert.is_active,
        created_at=cert.created_at
    )
    return cert_copy


@router.post("", response_model=CertificationInfo)
async def create_certification(request: CertificationCreateRequest):
    """创建新的资格认证。"""
    if request.certification_id in _certifications:
        raise HTTPException(
            status_code=400,
            detail=f"Certification already exists: {request.certification_id}"
        )

    cert = CertificationInfo(
        certification_id=request.certification_id,
        name=request.name,
        description=request.description,
        required_skills=request.required_skills,
        passing_score=request.passing_score,
        is_active=True,
        created_at=datetime.now().isoformat()
    )

    _certifications[request.certification_id] = cert
    return cert


@router.get("/workers/{worker_id}")
async def get_worker_certifications(worker_id: str):
    """获取工人已获得的认证列表。"""
    worker = worker_profile_service.get_profile(worker_id)
    if not worker:
        raise HTTPException(
            status_code=404,
            detail=f"Worker not found: {worker_id}"
        )

    cert_ids = _worker_certifications.get(worker_id, [])
    certs = [_certifications[cid] for cid in cert_ids if cid in _certifications]

    return {
        "worker_id": worker_id,
        "certifications": [
            {
                "certification_id": c.certification_id,
                "name": c.name,
                "description": c.description,
                "acquired_at": "N/A"  # TODO: 记录获取时间
            }
            for c in certs
        ],
        "total": len(certs)
    }


@router.get("/{certification_id}/exam")
async def get_certification_exam(certification_id: str):
    """获取认证考试题目。"""
    cert = _certifications.get(certification_id)
    if not cert:
        raise HTTPException(
            status_code=404,
            detail=f"Certification not found: {certification_id}"
        )

    if not cert.is_active:
        raise HTTPException(
            status_code=400,
            detail="This certification is currently inactive"
        )

    return {
        "certification_id": certification_id,
        "certification_name": cert.name,
        "passing_score": cert.passing_score,
        "questions": cert.exam_questions
    }


@router.post("/{certification_id}/exam", response_model=CertificationExamResponse)
async def submit_certification_exam(request: CertificationExamRequest):
    """提交认证考试答案。"""
    cert = _certifications.get(request.certification_id)
    if not cert:
        raise HTTPException(
            status_code=404,
            detail=f"Certification not found: {request.certification_id}"
        )

    worker = worker_profile_service.get_profile(request.worker_id)
    if not worker:
        raise HTTPException(
            status_code=404,
            detail=f"Worker not found: {request.worker_id}"
        )

    # 检查是否已经通过该认证
    existing_certs = _worker_certifications.get(request.worker_id, [])
    if request.certification_id in existing_certs:
        return CertificationExamResponse(
            certification_id=request.certification_id,
            worker_id=request.worker_id,
            passed=True,
            score=1.0,
            message="您已通过该认证，无需重复考试"
        )

    # 判卷
    if not cert.exam_questions:
        # 无考试的认证，直接通过
        _add_certification_to_worker(request.worker_id, request.certification_id)
        return CertificationExamResponse(
            certification_id=request.certification_id,
            worker_id=request.worker_id,
            passed=True,
            score=1.0,
            message="认证成功"
        )

    # 计算得分
    correct_count = 0
    total_questions = len(cert.exam_questions)

    for question in cert.exam_questions:
        user_answer = request.answers.get(question["question_id"], "")
        if user_answer.lower().strip() == question["correct_answer"].lower().strip():
            correct_count += 1

    score = correct_count / total_questions if total_questions > 0 else 0
    passed = score >= cert.passing_score

    # 记录考试尝试
    attempt_key = f"{request.worker_id}:{request.certification_id}"
    if attempt_key not in _certification_attempts:
        _certification_attempts[attempt_key] = []
    _certification_attempts[attempt_key].append({
        "timestamp": datetime.now().isoformat(),
        "score": score,
        "passed": passed
    })

    if passed:
        _add_certification_to_worker(request.worker_id, request.certification_id)
        # 更新工人 verified_skills
        for skill in cert.required_skills:
            if skill not in worker.verified_skills:
                worker.verified_skills.append(skill)
        worker.updated_at = datetime.now()

        return CertificationExamResponse(
            certification_id=request.certification_id,
            worker_id=request.worker_id,
            passed=True,
            score=score,
            message=f"恭喜通过认证！得分：{score:.1%}"
        )
    else:
        return CertificationExamResponse(
            certification_id=request.certification_id,
            worker_id=request.worker_id,
            passed=False,
            score=score,
            message=f"未通过认证，得分：{score:.1%}，需达到：{cert.passing_score:.1%}"
        )


def _add_certification_to_worker(worker_id: str, certification_id: str):
    """将认证添加到工人。"""
    if worker_id not in _worker_certifications:
        _worker_certifications[worker_id] = []
    if certification_id not in _worker_certifications[worker_id]:
        _worker_certifications[worker_id].append(certification_id)

    # 同步到工人画像
    worker = worker_profile_service.get_profile(worker_id)
    if worker and certification_id not in worker.certifications:
        worker.certifications.append(certification_id)


@router.delete("/workers/{worker_id}/{certification_id}")
async def revoke_certification(worker_id: str, certification_id: str, reason: str = ""):
    """撤销工人认证（管理员操作）。"""
    worker = worker_profile_service.get_profile(worker_id)
    if not worker:
        raise HTTPException(
            status_code=404,
            detail=f"Worker not found: {worker_id}"
        )

    if certification_id not in _certifications:
        raise HTTPException(
            status_code=404,
            detail=f"Certification not found: {certification_id}"
        )

    # 从列表中移除
    if worker_id in _worker_certifications:
        _worker_certifications[worker_id] = [
            c for c in _worker_certifications[worker_id]
            if c != certification_id
        ]

    # 从画像中移除
    if certification_id in worker.certifications:
        worker.certifications.remove(certification_id)

    # 移除相关 verified_skills
    cert = _certifications.get(certification_id)
    if cert:
        for skill in cert.required_skills:
            if skill in worker.verified_skills:
                worker.verified_skills.remove(skill)

    worker.updated_at = datetime.now()

    return {
        "message": "Certification revoked",
        "worker_id": worker_id,
        "certification_id": certification_id,
        "reason": reason
    }


@router.get("/workers/{worker_id}/attempts")
async def get_certification_attempts(worker_id: str, certification_id: str = None):
    """获取工人认证考试尝试记录。"""
    if certification_id:
        attempt_key = f"{worker_id}:{certification_id}"
        attempts = _certification_attempts.get(attempt_key, [])
        return {
            "worker_id": worker_id,
            "certification_id": certification_id,
            "attempts": attempts,
            "total_attempts": len(attempts)
        }
    else:
        # 返回所有尝试记录
        all_attempts = {}
        for key, attempts in _certification_attempts.items():
            if key.startswith(f"{worker_id}:"):
                cert_id = key.split(":")[1]
                all_attempts[cert_id] = attempts

        return {
            "worker_id": worker_id,
            "all_attempts": all_attempts
        }


@router.post("/check-requirement")
async def check_certification_requirement(
    worker_id: str,
    required_certifications: List[str]
):
    """检查工人是否满足认证要求。"""
    worker = worker_profile_service.get_profile(worker_id)
    if not worker:
        raise HTTPException(
            status_code=404,
            detail=f"Worker not found: {worker_id}"
        )

    worker_certs = set(_worker_certifications.get(worker_id, []))
    required = set(required_certifications)

    missing = required - worker_certs
    satisfied = required - missing

    return {
        "worker_id": worker_id,
        "required_certifications": list(required),
        "satisfied": list(satisfied),
        "missing": list(missing),
        "all_satisfied": len(missing) == 0
    }
