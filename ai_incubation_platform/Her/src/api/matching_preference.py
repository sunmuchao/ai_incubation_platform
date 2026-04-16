"""
高级匹配偏好 API

提供更细化的匹配条件设置：
- 年龄、身高、教育、职业等偏好
- AI 建议偏好设置
- 匹配分数计算
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from db.database import get_db
from services.advanced_matching_preference_service import (
    AdvancedMatchingPreferenceService,
    get_advanced_matching_preference_service
)
from utils.logger import logger

router = APIRouter(prefix="/api/matching-preferences", tags=["Matching Preferences"])

# 🔧 [缓存同步] 导入缓存清除函数，确保偏好更新后 AI 能获取最新数据
try:
    from api.deerflow import invalidate_user_cache
    CACHE_INVALIDATION_AVAILABLE = True
except ImportError:
    logger.warning("deerflow cache invalidation not available")
    CACHE_INVALIDATION_AVAILABLE = False
    invalidate_user_cache = None


class PreferenceRequest(BaseModel):
    """偏好设置请求"""
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    height_min: Optional[int] = None
    height_max: Optional[int] = None
    education: Optional[List[str]] = None
    occupation: Optional[List[str]] = None
    lifestyle: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    location_city: Optional[str] = None
    max_distance: Optional[int] = None
    relationship_goal: Optional[str] = None
    relationship_expectation: Optional[List[str]] = None
    deal_breakers: Optional[List[str]] = None
    weight_config: Optional[Dict[str, float]] = None


class PreferenceResponse(BaseModel):
    """偏好响应"""
    preference_id: str
    user_id: str
    age_min: int
    age_max: int
    height_min: Optional[int] = None
    height_max: Optional[int] = None
    education: Optional[List[str]] = None
    occupation: Optional[List[str]] = None
    lifestyle: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    location_city: Optional[str] = None
    max_distance: int
    relationship_goal: Optional[str] = None
    relationship_expectation: Optional[List[str]] = None
    deal_breakers: Optional[List[str]] = None
    weight_config: Optional[Dict[str, float]] = None
    created_at: str
    updated_at: str


class MatchScoreRequest(BaseModel):
    """匹配分数计算请求"""
    user_id: str
    candidate_profile: Dict[str, Any]


@router.get("/schema")
async def get_preference_schema():
    """
    获取偏好配置模板

    返回所有维度的配置信息
    """
    service = AdvancedMatchingPreferenceService(None)
    return {"dimensions": service.DIMENSIONS}


@router.post("/save")
async def save_preferences(
    user_id: str,
    request: PreferenceRequest,
    db: Session = Depends(get_db)
):
    """
    保存用户匹配偏好
    """
    try:
        service = get_advanced_matching_preference_service(db)
        result = service.save_preferences(user_id, request.dict())

        # 🔧 [缓存同步] 清除缓存，确保 AI 下次对话能获取最新偏好
        # 用户更新年龄偏好、异地接受度等设置后，AI 需要用新偏好做推荐
        if CACHE_INVALIDATION_AVAILABLE and invalidate_user_cache:
            invalidate_user_cache(user_id)
            logger.info(f"[缓存同步] 匹配偏好更新后缓存已清除: {user_id}")

        logger.info(f"Saved matching preferences for user {user_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to save preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get/{user_id}", response_model=Optional[PreferenceResponse])
async def get_preferences(user_id: str, db: Session = Depends(get_db)):
    """
    获取用户匹配偏好
    """
    try:
        service = get_advanced_matching_preference_service(db)
        preferences = service.get_user_preferences(user_id)
        return preferences
    except Exception as e:
        logger.error(f"Failed to get preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/score")
async def calculate_match_score(
    request: MatchScoreRequest,
    db: Session = Depends(get_db)
):
    """
    计算匹配分数

    根据用户偏好和候选人资料计算匹配度
    """
    try:
        service = get_advanced_matching_preference_service(db)

        # 获取用户偏好
        user_preferences = service.get_user_preferences(request.user_id)
        if not user_preferences:
            user_preferences = {}

        # 计算分数
        score = service.calculate_match_score(user_preferences, request.candidate_profile)

        return {"score": score, "preference_id": user_preferences.get("preference_id")}
    except Exception as e:
        logger.error(f"Failed to calculate match score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions/{user_id}")
async def get_preference_suggestions(user_id: str, db: Session = Depends(get_db)):
    """
    AI 生成偏好建议

    根据用户资料，AI 建议合适的匹配偏好
    """
    try:
        # 获取用户资料
        from db.models import UserDB
        user = db.query(UserDB).filter(UserDB.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        user_profile = {
            "age": user.age,
            "gender": user.gender,
            "location": user.location,
            "interests": user.interests,
            "bio": user.bio,
            "goal": user.goal
        }

        service = get_advanced_matching_preference_service(db)
        suggestions = await service.generate_preference_suggestions(user_profile)
        return suggestions
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get preference suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/options/{dimension}")
async def get_dimension_options(dimension: str):
    """
    获取特定维度的选项列表

    用于前端下拉选择
    """
    dimension_options = {
        "education": ["高中", "大专", "本科", "硕士", "博士", "不限"],
        "occupation": ["互联网", "金融", "教育", "医疗", "艺术", "公务员", "学生", "其他"],
        "lifestyle": ["早睡早起", "熬夜党", "运动达人", "宅家派", "吃货", "健康饮食"],
        "relationship_goal": ["寻找伴侣", "结交朋友", "拓展人脉", "随缘"],
        "relationship_expectation": ["长期关系", "短期接触", "先了解再说", "不确定"]
    }

    return {"options": dimension_options.get(dimension, [])}