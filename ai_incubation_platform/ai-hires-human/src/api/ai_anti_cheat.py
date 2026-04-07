"""
AI 反作弊增强 API。

提供 AI 驱动的作弊检测功能：
1. 提交内容 AI 分析
2. 异常行为检测
3. 团伙作弊识别
4. 模型自学习
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from services.ai_anti_cheat_service import ai_anti_cheat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-anti-cheat", tags=["ai_anti_cheat"])


class AnalyzeSubmissionRequest(BaseModel):
    """提交分析请求。"""
    user_id: str
    task_id: str
    content: str
    user_history: Optional[Dict[str, Any]] = None
    device_info: Optional[Dict[str, Any]] = None


from pydantic import BaseModel


@router.post("/analyze-submission")
async def analyze_submission(request: AnalyzeSubmissionRequest):
    """
    AI 分析提交内容。

    综合使用以下技术进行检测：
    - 机器学习分类器：基于多维度特征预测作弊概率
    - 异常检测：识别偏离正常行为模式的提交
    - 图谱分析：检测团伙作弊

    返回综合风险评估和处置建议。
    """
    user_history = request.user_history or {}
    device_info = request.device_info or {}

    result = ai_anti_cheat_service.analyze_submission(
        user_id=request.user_id,
        task_id=request.task_id,
        content=request.content,
        user_history=user_history,
        device_info=device_info,
    )

    return result


@router.post("/analyze-submission-simple")
async def analyze_submission_simple(
    user_id: str,
    task_id: str,
    content: str,
    x_forwarded_for: Optional[str] = Header(None),
    user_agent: Optional[str] = Header(None),
):
    """
    简化版提交分析（自动提取请求头信息）。

    适用于快速集成场景。
    """
    user_history = {}
    device_info = {
        "ip_address": x_forwarded_for.split(",")[0].strip() if x_forwarded_for else None,
        "user_agent": user_agent,
    }

    result = ai_anti_cheat_service.analyze_submission(
        user_id=user_id,
        task_id=task_id,
        content=content,
        user_history=user_history,
        device_info=device_info,
    )

    return result


@router.get("/prediction/{user_id}/{task_id}")
async def get_prediction(user_id: str, task_id: str):
    """获取用户提交的 AI 预测结果。"""
    prediction = ai_anti_cheat_service.get_user_prediction(user_id, task_id)
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return prediction


@router.post("/mark-result")
async def mark_submission_result(
    user_id: str,
    task_id: str,
    actual_is_cheat: bool,
):
    """
    标记实际结果。

    用于模型自学习，提高预测准确性。
    """
    ai_anti_cheat_service.mark_submission_result(user_id, task_id, actual_is_cheat)
    return {
        "message": "Result recorded",
        "user_id": user_id,
        "task_id": task_id,
        "actual_is_cheat": actual_is_cheat,
    }


@router.get("/suspicious-users")
async def get_suspicious_users():
    """获取可疑用户列表。"""
    users = ai_anti_cheat_service.get_suspicious_users()
    return {
        "count": len(users),
        "users": users,
    }


@router.get("/fraud-clusters")
async def get_fraud_clusters():
    """
    获取检测到的欺诈集群。

    返回共享设备或 IP 的可疑用户群。
    """
    clusters = ai_anti_cheat_service.get_fraud_clusters()
    return {
        "count": len(clusters),
        "clusters": clusters,
    }


@router.post("/record-connection")
async def record_user_connection(
    user_id: str,
    device_id: str,
    ip_address: str,
):
    """
    记录用户连接关系。

    用于图谱分析检测团伙作弊。
    """
    ai_anti_cheat_service.record_user_connection(user_id, device_id, ip_address)
    return {
        "message": "Connection recorded",
        "user_id": user_id,
        "device_id": device_id[:8] + "...",
        "ip_address": ip_address,
    }


@router.get("/stats")
async def get_ai_anti_cheat_stats():
    """获取 AI 反作弊统计信息。"""
    # 获取预测数量
    prediction_count = len(ai_anti_cheat_service._user_predictions)

    # 获取可疑用户数量
    suspicious_count = len(ai_anti_cheat_service._suspicious_users)

    # 获取标注样本数量
    labeled_count = len(ai_anti_cheat_service.cheat_classifier._labeled_data)

    # 获取欺诈集群数量
    cluster_count = len(ai_anti_cheat_service.get_fraud_clusters())

    return {
        "prediction_count": prediction_count,
        "suspicious_user_count": suspicious_count,
        "labeled_samples": labeled_count,
        "fraud_clusters": cluster_count,
    }


@router.get("/features")
async def list_detection_features():
    """获取作弊检测特征说明。"""
    return {
        "features": [
            {
                "name": "content_length_ratio",
                "description": "内容长度与历史平均的比率",
                "weight": 0.15,
                "high_risk": "远低于或远高于历史平均",
            },
            {
                "name": "submission_speed",
                "description": "任务完成速度",
                "weight": 0.2,
                "high_risk": "完成时间过短（<5 分钟）",
            },
            {
                "name": "content_similarity",
                "description": "与历史提交内容的相似度",
                "weight": 0.25,
                "high_risk": "相似度>70%",
            },
            {
                "name": "user_history_quality",
                "description": "用户历史质量评分",
                "weight": 0.2,
                "high_risk": "历史质量评分低",
            },
            {
                "name": "time_pattern_score",
                "description": "提交时间模式",
                "weight": 0.1,
                "high_risk": "深夜时段（0-6 点）频繁提交",
            },
            {
                "name": "device_risk",
                "description": "设备风险评分",
                "weight": 0.1,
                "high_risk": "高风险设备或自动化工具",
            },
        ],
        "detection_methods": [
            {
                "name": "AI 分类器",
                "description": "基于集成学习的作弊分类器，综合多个特征进行预测",
            },
            {
                "name": "异常检测",
                "description": "使用 Z-score 和统计方法识别偏离正常模式的行为",
            },
            {
                "name": "图谱分析",
                "description": "检测用户 - 设备-IP 关系网络中的密集子图（作弊团伙）",
            },
        ],
    }


@router.get("/model-info")
async def get_model_info():
    """获取 AI 模型信息。"""
    return {
        "model_version": "v1.0",
        "model_type": "ensemble_classifier",
        "features_count": 6,
        "training_samples": len(ai_anti_cheat_service.cheat_classifier._labeled_data),
        "threshold": 0.6,
        "last_updated": datetime.now().isoformat(),
    }
