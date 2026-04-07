"""
P10 API 路由 - 关系里程碑追踪增强、约会建议引擎、双人互动游戏

P10-001: 关系里程碑追踪增强
- 记录关系里程碑
- 获取里程碑时间线
- 获取关系洞察
- 里程碑统计分析

P10-002: 约会建议引擎
- 获取约会建议
- 响应约会建议
- 约会地点推荐

P10-004: 双人互动游戏
- 创建游戏
- 参与游戏
- 获取游戏结果
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.relationship_milestone_service import relationship_milestone_service
from utils.logger import logger

# 创建路由器
router_milestones = APIRouter(prefix="/api/milestones", tags=["milestones"])
router_date_suggestions = APIRouter(prefix="/api/date-suggestions", tags=["date-suggestions"])
router_couple_games = APIRouter(prefix="/api/couple-games", tags=["couple-games"])


# ============= P10-001: 关系里程碑追踪增强 API =============

class MilestoneRecordRequest(BaseModel):
    """记录里程碑请求"""
    user_id_1: str = Field(..., description="用户 ID 1")
    user_id_2: str = Field(..., description="用户 ID 2")
    milestone_type: str = Field(..., description="里程碑类型")
    title: str = Field(..., description="里程碑标题")
    description: str = Field(..., description="里程碑描述")
    milestone_date: Optional[str] = Field(None, description="里程碑发生时间 ISO 格式")
    celebration_suggested: bool = Field(False, description="是否建议庆祝")
    ai_analysis: Optional[Dict[str, Any]] = Field(None, description="AI 分析数据")
    is_private: bool = Field(False, description="是否私密里程碑")


class MilestoneUpdateRequest(BaseModel):
    """更新里程碑请求"""
    title: Optional[str] = Field(None, description="里程碑标题")
    description: Optional[str] = Field(None, description="里程碑描述")
    user_rating: Optional[int] = Field(None, ge=1, le=5, description="用户评分")
    user_note: Optional[str] = Field(None, description="用户备注")


@router_milestones.post("/record")
async def record_milestone(request: MilestoneRecordRequest):
    """
    记录关系里程碑

    用于记录用户关系中的重要时刻，如第一次约会、确定关系等。
    """
    try:
        milestone_date = None
        if request.milestone_date:
            milestone_date = datetime.fromisoformat(request.milestone_date.replace('Z', '+00:00'))

        milestone_id = relationship_milestone_service.record_milestone(
            user_id_1=request.user_id_1,
            user_id_2=request.user_id_2,
            milestone_type=request.milestone_type,
            title=request.title,
            description=request.description,
            milestone_date=milestone_date,
            celebration_suggested=request.celebration_suggested,
            ai_analysis=request.ai_analysis,
            is_private=request.is_private
        )

        return {
            "milestone_id": milestone_id,
            "status": "recorded"
        }
    except Exception as e:
        logger.error(f"Error recording milestone: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router_milestones.get("/timeline/{user_id_1}/{user_id_2}")
async def get_milestone_timeline(
    user_id_1: str,
    user_id_2: str,
    include_private: bool = False
):
    """
    获取关系里程碑时间线

    返回两人关系中的所有里程碑事件，按时间排序。
    """
    try:
        timeline = relationship_milestone_service.get_milestone_timeline(
            user_id_1=user_id_1,
            user_id_2=user_id_2,
            include_private=include_private
        )
        return timeline
    except Exception as e:
        logger.error(f"Error getting milestone timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router_milestones.get("/{milestone_id}")
async def get_milestone_details(milestone_id: str):
    """
    获取里程碑详情
    """
    # 注：实际实现需要从服务层添加获取单个里程碑的方法
    # 这里暂时返回占位实现
    return {
        "milestone_id": milestone_id,
        "status": "not_implemented"
    }


@router_milestones.put("/{milestone_id}")
async def update_milestone(milestone_id: str, request: MilestoneUpdateRequest):
    """
    更新里程碑

    用户可以更新里程碑的标题、描述、评分或添加备注。
    """
    # 注：实际实现需要从服务层添加更新里程碑的方法
    return {
        "milestone_id": milestone_id,
        "status": "not_implemented"
    }


@router_milestones.post("/{milestone_id}/celebrate")
async def celebrate_milestone(milestone_id: str, celebration_type: str = "card"):
    """
    庆祝里程碑

    用户可以选择庆祝方式（card, gift, activity）来纪念这个时刻。
    """
    # 注：实际实现需要记录庆祝行为
    return {
        "milestone_id": milestone_id,
        "celebration_type": celebration_type,
        "status": "celebrated"
    }


@router_milestones.get("/stats/{user_id_1}/{user_id_2}")
async def get_milestone_statistics(
    user_id_1: str,
    user_id_2: str
):
    """
    获取里程碑统计数据

    返回两人关系的统计信息，包括里程碑数量、类别分布、关系得分等。
    """
    try:
        stats = relationship_milestone_service.get_milestone_statistics(
            user_id_1=user_id_1,
            user_id_2=user_id_2
        )
        return stats
    except Exception as e:
        logger.error(f"Error getting milestone statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= 关系洞察 API =============

@router_milestones.post("/insights/generate")
async def generate_insight(
    user_id_1: str = Body(...),
    user_id_2: str = Body(...),
    insight_type: str = Body(...),
    title: str = Body(...),
    content: str = Body(...),
    action_suggestion: Optional[str] = Body(None),
    priority: str = Body("normal"),
    expires_hours: Optional[int] = Body(None)
):
    """
    生成关系洞察

    AI 分析用户关系后生成的洞察和建议。
    """
    try:
        insight_id = relationship_milestone_service.generate_relationship_insight(
            user_id_1=user_id_1,
            user_id_2=user_id_2,
            insight_type=insight_type,
            title=title,
            content=content,
            action_suggestion=action_suggestion,
            priority=priority,
            expires_hours=expires_hours
        )
        return {
            "insight_id": insight_id,
            "status": "generated"
        }
    except Exception as e:
        logger.error(f"Error generating insight: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router_milestones.get("/insights/{user_id}")
async def get_user_insights(
    user_id: str,
    unread_only: bool = False,
    limit: int = 20
):
    """
    获取用户的关系洞察

    返回 AI 生成的关系分析和建议。
    """
    try:
        insights = relationship_milestone_service.get_relationship_insights(
            user_id=user_id,
            unread_only=unread_only,
            limit=limit
        )
        return {"insights": insights}
    except Exception as e:
        logger.error(f"Error getting insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router_milestones.post("/insights/{insight_id}/read")
async def mark_insight_read(insight_id: str, user_id: str = Body(...)):
    """
    标记洞察为已读
    """
    try:
        success = relationship_milestone_service.mark_insight_read(
            insight_id=insight_id,
            user_id=user_id
        )
        if success:
            return {"status": "marked_read"}
        else:
            raise HTTPException(status_code=404, detail="Insight not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking insight as read: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= P10-002: 约会建议引擎 API =============

class DateSuggestionRequest(BaseModel):
    """约会建议请求"""
    user_id: str = Field(..., description="用户 ID")
    target_user_id: Optional[str] = Field(None, description="约会对象 ID")
    date_type: str = Field(..., description="约会类型")
    preferences: Optional[Dict[str, Any]] = Field(None, description="偏好设置")


class DateSuggestionResponseRequest(BaseModel):
    """约会建议响应"""
    action: str = Field(..., description="响应动作：accept, reject, counter")
    feedback: Optional[str] = Field(None, description="反馈说明")
    counter_suggestion: Optional[str] = Field(None, description="反向建议（如果是 counter）")


@router_date_suggestions.post("/generate")
async def generate_date_suggestion(request: DateSuggestionRequest):
    """
    生成约会建议

    基于用户兴趣和位置生成个性化的约会地点和活动建议。
    """
    # 注：需要实现约会建议服务
    return {
        "status": "not_implemented",
        "message": "约会建议引擎将在后续实现"
    }


@router_date_suggestions.get("/list/{user_id}")
async def get_user_date_suggestions(
    user_id: str,
    status: Optional[str] = None,
    limit: int = 10
):
    """
    获取用户的约会建议列表
    """
    # 注：需要实现约会建议服务
    return {
        "suggestions": [],
        "status": "not_implemented"
    }


@router_date_suggestions.post("/{suggestion_id}/respond")
async def respond_to_date_suggestion(
    suggestion_id: str,
    request: DateSuggestionResponseRequest
):
    """
    响应约会建议

    接受、拒绝或提出反向建议。
    """
    # 注：需要实现约会建议服务
    return {
        "status": "not_implemented"
    }


@router_date_suggestions.get("/venues")
async def get_date_venues(
    city: str,
    venue_type: Optional[str] = None,
    price_level: Optional[int] = None,
    limit: int = 20
):
    """
    获取约会地点推荐

    按城市、类型、价格等筛选约会地点。
    """
    # 注：需要实现约会地点服务
    return {
        "venues": [],
        "status": "not_implemented"
    }


# ============= P10-004: 双人互动游戏 API =============

class CoupleGameCreateRequest(BaseModel):
    """创建游戏请求"""
    user_id_1: str = Field(..., description="用户 ID 1")
    user_id_2: str = Field(..., description="用户 ID 2")
    game_type: str = Field(..., description="游戏类型")
    game_config: Optional[Dict[str, Any]] = Field(None, description="游戏配置")
    difficulty: str = Field("normal", description="难度等级")


class CoupleGameRoundRequest(BaseModel):
    """游戏轮次请求"""
    game_id: str = Field(..., description="游戏 ID")
    round_number: int = Field(..., description="轮次号")
    answer: str = Field(..., description="用户回答")
    user_id: str = Field(..., description="回答用户 ID")


@router_couple_games.post("/create")
async def create_couple_game(request: CoupleGameCreateRequest):
    """
    创建双人互动游戏

    可创建的游戏类型包括：
    - qna_mutual: 互相问答
    - values_quiz: 价值观测试
    - preference_match: 偏好匹配
    - personality_quiz: 性格测试
    """
    # 注：需要实现游戏服务
    return {
        "status": "not_implemented",
        "message": "双人互动游戏将在后续实现"
    }


@router_couple_games.get("/list/{user_id}")
async def get_user_games(
    user_id: str,
    status: Optional[str] = None,
    limit: int = 10
):
    """
    获取用户参与的游戏列表
    """
    # 注：需要实现游戏服务
    return {
        "games": [],
        "status": "not_implemented"
    }


@router_couple_games.get("/{game_id}")
async def get_game_details(game_id: str):
    """
    获取游戏详情
    """
    # 注：需要实现游戏服务
    return {
        "status": "not_implemented"
    }


@router_couple_games.post("/{game_id}/round")
async def submit_game_round(request: CoupleGameRoundRequest):
    """
    提交游戏轮次回答
    """
    # 注：需要实现游戏服务
    return {
        "status": "not_implemented"
    }


@router_couple_games.post("/{game_id}/start")
async def start_game(game_id: str, user_id: str = Body(...)):
    """
    开始游戏
    """
    # 注：需要实现游戏服务
    return {
        "status": "not_implemented"
    }


@router_couple_games.post("/{game_id}/complete")
async def complete_game(game_id: str, user_id: str = Body(...)):
    """
    完成游戏并获取结果洞察
    """
    # 注：需要实现游戏服务
    return {
        "status": "not_implemented"
    }


@router_couple_games.get("/{game_id}/insights")
async def get_game_insights(game_id: str):
    """
    获取游戏结果洞察

    AI 分析游戏结果，生成兼容性洞察和建议。
    """
    # 注：需要实现游戏服务
    return {
        "status": "not_implemented"
    }
