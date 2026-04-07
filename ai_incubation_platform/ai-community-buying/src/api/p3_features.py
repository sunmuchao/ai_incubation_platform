"""
P3 用户增长与运营工具 - API 路由

包含：
1. 邀请裂变 API
2. 任务中心 API
3. 会员成长 API
4. 运营活动 API
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

from config.database import get_db
from sqlalchemy.orm import Session
from models.p3_entities import TaskType, CampaignType
from services.p3_growth_service import (
    InviteReferralService,
    TaskCenterService,
    MembershipGrowthService,
    CampaignService
)


# ====================  路由器定义  ====================

# 邀请裂变 API 路由
invite_router = APIRouter(prefix="/api/p3/invite", tags=["P3-邀请裂变"])

# 任务中心 API 路由
task_router = APIRouter(prefix="/api/p3/tasks", tags=["P3-任务中心"])

# 会员成长 API 路由
member_router = APIRouter(prefix="/api/p3/member", tags=["P3-会员成长"])

# 运营活动 API 路由
campaign_router = APIRouter(prefix="/api/p3/campaigns", tags=["P3-运营活动"])


# ====================  Pydantic 模型  ====================

# --- 邀请裂变相关模型 ---

class InviteRegisterRequest(BaseModel):
    """用户注册请求"""
    invite_code: Optional[str] = Field(None, description="邀请码")


class InviteActivateRequest(BaseModel):
    """邀请激活请求"""
    order_id: str = Field(..., description="订单 ID")
    order_amount: float = Field(..., gt=0, description="订单金额")


# --- 任务中心相关模型 ---

class TaskStartRequest(BaseModel):
    """开始任务请求"""
    task_id: str = Field(..., description="任务 ID")


class TaskProgressUpdateRequest(BaseModel):
    """更新任务进度请求"""
    action_type: str = Field(..., description="行动类型（如 order_count, view_count）")
    action_value: int = Field(..., ge=0, description="行动值")
    action_id: Optional[str] = Field(None, description="关联行动 ID")


class TaskClaimRewardRequest(BaseModel):
    """领取任务奖励请求"""
    user_task_id: str = Field(..., description="用户任务 ID")


# --- 会员成长相关模型 ---

class GrowthValueAddRequest(BaseModel):
    """增加成长值请求"""
    value: int = Field(..., gt=0, description="成长值")
    action_type: str = Field(..., description="行动类型")
    action_id: Optional[str] = Field(None, description="关联行动 ID")
    remark: Optional[str] = Field(None, description="备注")


class MemberStatsUpdateRequest(BaseModel):
    """更新会员统计请求"""
    order_amount: float = Field(..., gt=0, description="订单金额")


# --- 运营活动相关模型 ---

class CampaignCreateRequest(BaseModel):
    """创建活动请求"""
    campaign_name: str = Field(..., description="活动名称")
    campaign_type: str = Field(..., description="活动类型")
    start_time: str = Field(..., description="开始时间 (ISO 格式)")
    end_time: str = Field(..., description="结束时间 (ISO 格式)")
    config: Dict[str, Any] = Field(default_factory=dict, description="活动配置")
    rules: Optional[Dict[str, Any]] = Field(None, description="活动规则")
    template_id: Optional[str] = Field(None, description="模板 ID")


class CampaignParticipateRequest(BaseModel):
    """参与活动请求"""
    reward_type: Optional[str] = Field(None, description="奖励类型")
    reward_value: Optional[str] = Field(None, description="奖励值")
    order_id: Optional[str] = Field(None, description="关联订单 ID")


# ====================  邀请裂变 API  ====================

@invite_router.post("/generate-code")
async def generate_invite_code(user_id: str = Query(..., description="用户 ID"),
                               db: Session = Depends(get_db)):
    """生成邀请码"""
    service = InviteReferralService(db)
    code = service.generate_invite_code(user_id)
    return {
        "success": True,
        "invite_code": code,
        "message": "邀请码生成成功"
    }


@invite_router.post("/register")
async def invite_register(request: InviteRegisterRequest,
                          user_id: str = Query(..., description="新用户 ID"),
                          db: Session = Depends(get_db)):
    """用户注册（绑定邀请关系）"""
    service = InviteReferralService(db)
    result = service.register_user(user_id, request.invite_code)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@invite_router.post("/activate")
async def invite_activate(request: InviteActivateRequest,
                          user_id: str = Query(..., description="新用户 ID"),
                          db: Session = Depends(get_db)):
    """邀请激活（完成首单）"""
    service = InviteReferralService(db)
    result = service.activate_invite(user_id, request.order_id, Decimal(str(request.order_amount)))

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@invite_router.get("/record")
async def get_invite_record(user_id: str = Query(..., description="用户 ID"),
                            db: Session = Depends(get_db)):
    """获取用户邀请记录"""
    service = InviteReferralService(db)
    record = service.get_invite_record(user_id)

    if not record:
        return {
            "success": True,
            "message": "暂无邀请记录",
            "record": {
                "total_invites": 0,
                "registered_count": 0,
                "activated_count": 0,
                "total_reward": 0,
                "today_invites": 0,
                "week_invites": 0,
                "month_invites": 0,
                "ranking": 0
            }
        }

    return {"success": True, "record": record}


@invite_router.get("/leaderboard")
async def get_invite_leaderboard(limit: int = Query(10, ge=1, le=100, description="返回数量"),
                                 db: Session = Depends(get_db)):
    """获取邀请排行榜"""
    service = InviteReferralService(db)
    leaderboard = service.get_invite_leaderboard(limit)
    return {"success": True, "leaderboard": leaderboard}


# ====================  任务中心 API  ====================

@task_router.get("/list")
async def get_available_tasks(user_id: str = Query(..., description="用户 ID"),
                              task_type: Optional[str] = Query(None, description="任务类型"),
                              db: Session = Depends(get_db)):
    """获取可参与任务列表"""
    service = TaskCenterService(db)

    task_type_enum = None
    if task_type:
        try:
            task_type_enum = TaskType(task_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的任务类型：{task_type}")

    tasks = service.get_available_tasks(user_id, task_type_enum)
    return {"success": True, "tasks": tasks}


@task_router.post("/start")
async def start_task(request: TaskStartRequest,
                     user_id: str = Query(..., description="用户 ID"),
                     db: Session = Depends(get_db)):
    """开始任务"""
    service = TaskCenterService(db)
    result = service.start_task(user_id, request.task_id)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@task_router.post("/progress/update")
async def update_task_progress(request: TaskProgressUpdateRequest,
                               user_id: str = Query(..., description="用户 ID"),
                               db: Session = Depends(get_db)):
    """更新任务进度"""
    service = TaskCenterService(db)
    updated_tasks = service.update_task_progress(
        user_id,
        request.action_type,
        request.action_value,
        request.action_id
    )
    return {"success": True, "updated_tasks": updated_tasks}


@task_router.post("/reward/claim")
async def claim_task_reward(request: TaskClaimRewardRequest,
                            user_id: str = Query(..., description="用户 ID"),
                            db: Session = Depends(get_db)):
    """领取任务奖励"""
    service = TaskCenterService(db)
    result = service.claim_task_reward(user_id, request.user_task_id)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@task_router.get("/progress/{task_id}")
async def get_task_progress(task_id: str,
                            user_id: str = Query(..., description="用户 ID"),
                            db: Session = Depends(get_db)):
    """获取任务进度"""
    service = TaskCenterService(db)
    progress = service.get_task_progress(user_id, task_id)

    if not progress:
        return {"success": True, "message": "任务未开始", "progress": None}

    return {"success": True, "progress": progress}


# ====================  会员成长 API  ====================

@member_router.get("/profile")
async def get_member_profile(user_id: str = Query(..., description="用户 ID"),
                             db: Session = Depends(get_db)):
    """获取会员档案"""
    service = MembershipGrowthService(db)
    profile = service.get_member_profile(user_id)
    return {"success": True, "profile": profile}


@member_router.post("/growth-value/add")
async def add_growth_value(request: GrowthValueAddRequest,
                           user_id: str = Query(..., description="用户 ID"),
                           db: Session = Depends(get_db)):
    """增加成长值"""
    service = MembershipGrowthService(db)
    result = service.add_growth_value(
        user_id,
        request.value,
        request.action_type,
        request.action_id,
        request.remark
    )
    return result


@member_router.post("/stats/update")
async def update_member_stats(request: MemberStatsUpdateRequest,
                              user_id: str = Query(..., description="用户 ID"),
                              db: Session = Depends(get_db)):
    """更新会员统计"""
    service = MembershipGrowthService(db)
    service.update_member_stats(user_id, Decimal(str(request.order_amount)))
    return {"success": True, "message": "会员统计更新成功"}


@member_router.get("/levels")
async def get_level_configs(db: Session = Depends(get_db)):
    """获取等级配置"""
    service = MembershipGrowthService(db)
    levels = service.get_level_configs()
    return {"success": True, "levels": levels}


# ====================  运营活动 API  ====================

@campaign_router.get("/templates")
async def get_campaign_templates(campaign_type: Optional[str] = Query(None, description="活动类型"),
                                 db: Session = Depends(get_db)):
    """获取活动模板列表"""
    service = CampaignService(db)

    campaign_type_enum = None
    if campaign_type:
        try:
            campaign_type_enum = CampaignType(campaign_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的活动类型：{campaign_type}")

    templates = service.get_campaign_templates(campaign_type_enum)
    return {"success": True, "templates": templates}


@campaign_router.post("/create")
async def create_campaign(request: CampaignCreateRequest,
                          db: Session = Depends(get_db)):
    """创建活动实例"""
    service = CampaignService(db)

    try:
        campaign_type = CampaignType(request.campaign_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的活动类型：{request.campaign_type}")

    try:
        start_time = datetime.fromisoformat(request.start_time)
        end_time = datetime.fromisoformat(request.end_time)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的时间格式，请使用 ISO 格式")

    result = service.create_campaign(
        request.campaign_name,
        campaign_type,
        start_time,
        end_time,
        request.config,
        request.rules,
        request.template_id
    )
    return result


@campaign_router.get("/active")
async def get_active_campaigns(user_id: str = Query(..., description="用户 ID"),
                               db: Session = Depends(get_db)):
    """获取当前可进行的活动列表"""
    service = CampaignService(db)
    campaigns = service.get_active_campaigns(user_id)
    return {"success": True, "campaigns": campaigns}


@campaign_router.post("/participate/{campaign_id}")
async def participate_campaign(campaign_id: str,
                               request: CampaignParticipateRequest,
                               user_id: str = Query(..., description="用户 ID"),
                               db: Session = Depends(get_db)):
    """参与活动"""
    service = CampaignService(db)
    result = service.participate_campaign(
        campaign_id,
        user_id,
        request.reward_type,
        request.reward_value,
        request.order_id
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result
