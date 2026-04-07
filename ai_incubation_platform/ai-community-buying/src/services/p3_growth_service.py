"""
P3 用户增长与运营工具 - 服务层实现

包含：
1. 邀请裂变服务 (InviteReferralService)
2. 任务中心服务 (TaskCenterService)
3. 会员成长服务 (MembershipGrowthService)
4. 运营活动服务 (CampaignService)
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
import json
import uuid

from models.p3_entities import (
    # 邀请裂变
    InviteRelationEntity, InviteRewardRuleEntity, InviteRecordEntity, InviteStatus,
    # 任务中心
    TaskDefinitionEntity, UserTaskEntity, TaskProgressLogEntity, TaskType, TaskStatus, TaskRewardType,
    # 会员成长
    MemberProfileEntity, MemberLevelConfigEntity, GrowthValueLogEntity, MemberBenefitEntity, MemberLevel,
    # 运营活动
    CampaignTemplateEntity, CampaignInstanceEntity, CampaignParticipantEntity, CampaignType, CampaignStatus
)


# ====================  邀请裂变服务  ====================

class InviteReferralService:
    """邀请裂变服务"""

    def __init__(self, db: Session):
        self.db = db

    def generate_invite_code(self, user_id: str) -> str:
        """生成用户邀请码"""
        # 使用用户 ID 后 8 位 + 时间戳后 6 位
        code = f"INV{user_id[-6:].upper()}{datetime.now().strftime('%H%M%S')[-6:]}"
        return code[:16]  # 限制长度

    def create_invite_relation(self, inviter_id: str, invitee_id: str, invite_code: str) -> InviteRelationEntity:
        """创建邀请关系"""
        # 检查被邀请人是否已存在邀请关系
        existing = self.db.query(InviteRelationEntity).filter(
            InviteRelationEntity.invitee_id == invitee_id
        ).first()
        if existing:
            return existing

        relation = InviteRelationEntity(
            id=str(uuid.uuid4()),
            inviter_id=inviter_id,
            invitee_id=invitee_id,
            invite_code=invite_code,
            status=InviteStatus.PENDING
        )
        self.db.add(relation)
        self.db.commit()
        self.db.refresh(relation)
        return relation

    def register_user(self, user_id: str, invite_code: Optional[str] = None) -> Dict[str, Any]:
        """用户注册（绑定邀请关系）"""
        if not invite_code:
            return {"success": True, "message": "用户注册成功（无邀请人）"}

        # 查找邀请关系
        relation = self.db.query(InviteRelationEntity).filter(
            InviteRelationEntity.invite_code == invite_code
        ).first()

        if not relation:
            return {"success": False, "message": "邀请码无效"}

        # 更新邀请关系状态
        relation.status = InviteStatus.REGISTERED
        relation.registered_at = datetime.now()

        # 获取奖励规则
        rule = self._get_active_reward_rule()
        if rule:
            # 发放注册奖励（被邀请人）
            relation.invitee_reward = rule.invitee_cash_reward or 0

        self.db.commit()

        # 更新邀请人统计
        self._update_invite_record(relation.inviter_id)

        return {
            "success": True,
            "message": "用户注册成功",
            "invitee_reward": float(relation.invitee_reward) if relation.invitee_reward else 0
        }

    def activate_invite(self, user_id: str, order_id: str, order_amount: Decimal) -> Dict[str, Any]:
        """激活邀请（被邀请人完成首单）"""
        relation = self.db.query(InviteRelationEntity).filter(
            InviteRelationEntity.invitee_id == user_id,
            InviteRelationEntity.status == InviteStatus.REGISTERED
        ).first()

        if not relation:
            return {"success": False, "message": "未找到待激活的邀请关系"}

        # 检查首单金额是否满足要求
        rule = self._get_active_reward_rule()
        if rule and order_amount < rule.min_order_amount:
            return {
                "success": False,
                "message": f"订单金额未达到激活要求（最低{rule.min_order_amount}元）"
            }

        # 更新邀请关系状态
        relation.status = InviteStatus.ACTIVATED
        relation.activated_at = datetime.now()
        relation.first_order_id = order_id
        relation.first_order_amount = order_amount

        if rule:
            # 发放奖励
            relation.inviter_reward = rule.inviter_cash_reward or 0
            relation.invitee_reward = rule.invitee_cash_reward or 0
            relation.rewarded_at = datetime.now()

        self.db.commit()

        # 更新邀请人统计
        self._update_invite_record(relation.inviter_id)

        return {
            "success": True,
            "message": "邀请已激活，奖励已发放",
            "inviter_reward": float(relation.inviter_reward) if relation.inviter_reward else 0,
            "invitee_reward": float(relation.invitee_reward) if relation.invitee_reward else 0
        }

    def _get_active_reward_rule(self) -> Optional[InviteRewardRuleEntity]:
        """获取当前生效的奖励规则"""
        return self.db.query(InviteRewardRuleEntity).filter(
            InviteRewardRuleEntity.is_active == True
        ).first()

    def _update_invite_record(self, inviter_id: str):
        """更新邀请人统计记录"""
        record = self.db.query(InviteRecordEntity).filter(
            InviteRecordEntity.user_id == inviter_id
        ).first()

        if not record:
            record = InviteRecordEntity(
                id=str(uuid.uuid4()),
                user_id=inviter_id
            )
            self.db.add(record)

        # 统计数据
        stats = self.db.query(
            InviteRelationEntity.status,
            func.count(InviteRelationEntity.id)
        ).filter(
            InviteRelationEntity.inviter_id == inviter_id
        ).group_by(InviteRelationEntity.status).all()

        record.total_invites = sum(count for _, count in stats)
        record.registered_count = sum(
            count for status, count in stats if status == InviteStatus.REGISTERED
        )
        record.activated_count = sum(
            count for status, count in stats if status in [InviteStatus.ACTIVATED, InviteStatus.REWARDED]
        )

        # 累计奖励
        total_reward = self.db.query(
            func.sum(InviteRelationEntity.inviter_reward)
        ).filter(
            InviteRelationEntity.inviter_id == inviter_id
        ).scalar() or 0
        record.total_reward = total_reward

        # 周期统计
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        record.today_invites = self.db.query(InviteRelationEntity).filter(
            InviteRelationEntity.inviter_id == inviter_id,
            func.date(InviteRelationEntity.created_at) == today
        ).count()

        record.week_invites = self.db.query(InviteRelationEntity).filter(
            InviteRelationEntity.inviter_id == inviter_id,
            func.date(InviteRelationEntity.created_at) >= week_start
        ).count()

        record.month_invites = self.db.query(InviteRelationEntity).filter(
            InviteRelationEntity.inviter_id == inviter_id,
            func.date(InviteRelationEntity.created_at) >= month_start
        ).count()

        self.db.commit()

    def get_invite_record(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户邀请记录"""
        record = self.db.query(InviteRecordEntity).filter(
            InviteRecordEntity.user_id == user_id
        ).first()

        if not record:
            return None

        return {
            "total_invites": record.total_invites,
            "registered_count": record.registered_count,
            "activated_count": record.activated_count,
            "total_reward": float(record.total_reward) if record.total_reward else 0,
            "today_invites": record.today_invites,
            "week_invites": record.week_invites,
            "month_invites": record.month_invites,
            "ranking": record.ranking
        }

    def get_invite_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取邀请排行榜"""
        records = self.db.query(InviteRecordEntity).order_by(
            desc(InviteRecordEntity.activated_count),
            desc(InviteRecordEntity.total_reward)
        ).limit(limit).all()

        leaderboard = []
        for i, record in enumerate(records, 1):
            leaderboard.append({
                "ranking": i,
                "user_id": record.user_id,
                "activated_count": record.activated_count,
                "total_reward": float(record.total_reward) if record.total_reward else 0
            })

        return leaderboard


# ====================  任务中心服务  ====================

class TaskCenterService:
    """任务中心服务"""

    def __init__(self, db: Session):
        self.db = db

    def get_available_tasks(self, user_id: str, task_type: Optional[TaskType] = None) -> List[Dict[str, Any]]:
        """获取用户可参与的任务列表"""
        now = datetime.now()

        query = self.db.query(TaskDefinitionEntity).filter(
            TaskDefinitionEntity.is_active == True,
            or_(TaskDefinitionEntity.start_time == None, TaskDefinitionEntity.start_time <= now),
            or_(TaskDefinitionEntity.end_time == None, TaskDefinitionEntity.end_time >= now)
        )

        if task_type:
            query = query.filter(TaskDefinitionEntity.task_type == task_type)

        definitions = query.order_by(TaskDefinitionEntity.sort_order).all()

        tasks = []
        for defn in definitions:
            # 检查用户是否已有此任务
            user_task = self.db.query(UserTaskEntity).filter(
                UserTaskEntity.user_id == user_id,
                UserTaskEntity.task_id == defn.id
            ).first()

            # 检查用户限次
            if defn.user_limit > 0 and user_task:
                completed_count = self.db.query(UserTaskEntity).filter(
                    UserTaskEntity.user_id == user_id,
                    UserTaskEntity.task_id == defn.id,
                    UserTaskEntity.status == TaskStatus.COMPLETED
                ).count()
                if completed_count >= defn.user_limit:
                    continue

            task_info = {
                "task_id": defn.id,
                "task_code": defn.task_code,
                "task_name": defn.task_name,
                "task_type": defn.task_type.value,
                "description": defn.description,
                "icon_url": defn.icon_url,
                "target_type": defn.target_type,
                "target_value": defn.target_value,
                "reward_type": defn.reward_type.value,
                "reward_value": defn.reward_value,
                "reward_extra": json.loads(defn.reward_extra) if defn.reward_extra else None,
                "status": "not_started",
                "current_value": 0
            }

            if user_task:
                task_info["user_task_id"] = user_task.id
                task_info["status"] = user_task.status.value
                task_info["current_value"] = user_task.current_value
                task_info["reward_claimed"] = user_task.reward_claimed

            tasks.append(task_info)

        return tasks

    def start_task(self, user_id: str, task_id: str) -> Dict[str, Any]:
        """开始任务"""
        task_def = self.db.query(TaskDefinitionEntity).filter(
            TaskDefinitionEntity.id == task_id
        ).first()

        if not task_def:
            return {"success": False, "message": "任务不存在"}

        if not task_def.is_active:
            return {"success": False, "message": "任务已下线"}

        # 检查是否已有任务
        user_task = self.db.query(UserTaskEntity).filter(
            UserTaskEntity.user_id == user_id,
            UserTaskEntity.task_id == task_id
        ).first()

        if user_task:
            return {
                "success": True,
                "message": "任务已在进行中",
                "user_task_id": user_task.id,
                "status": user_task.status.value
            }

        # 创建用户任务
        user_task = UserTaskEntity(
            id=str(uuid.uuid4()),
            user_id=user_id,
            task_id=task_id,
            status=TaskStatus.IN_PROGRESS,
            current_value=0,
            target_value=task_def.target_value,
            started_at=datetime.now()
        )
        self.db.add(user_task)
        self.db.commit()
        self.db.refresh(user_task)

        return {
            "success": True,
            "message": "任务已开始",
            "user_task_id": user_task.id,
            "status": user_task.status.value,
            "current_value": 0,
            "target_value": task_def.target_value
        }

    def update_task_progress(self, user_id: str, action_type: str, action_value: int, action_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """更新任务进度（批量）"""
        updated_tasks = []

        # 查找所有相关任务
        user_tasks = self.db.query(UserTaskEntity).filter(
            UserTaskEntity.user_id == user_id,
            UserTaskEntity.status == TaskStatus.IN_PROGRESS
        ).all()

        for user_task in user_tasks:
            task_def = self.db.query(TaskDefinitionEntity).filter(
                TaskDefinitionEntity.id == user_task.task_id
            ).first()

            if not task_def or task_def.target_type != action_type:
                continue

            # 更新进度
            old_value = user_task.current_value
            new_value = min(old_value + action_value, task_def.target_value)
            user_task.current_value = new_value

            # 记录日志
            log = TaskProgressLogEntity(
                id=str(uuid.uuid4()),
                user_task_id=user_task.id,
                user_id=user_id,
                old_value=old_value,
                new_value=new_value,
                increment=action_value,
                action_type=action_type,
                action_id=action_id
            )
            self.db.add(log)

            # 检查是否完成
            if new_value >= task_def.target_value and user_task.status == TaskStatus.IN_PROGRESS:
                user_task.status = TaskStatus.COMPLETED
                user_task.completed_at = datetime.now()

            updated_tasks.append({
                "task_id": task_def.id,
                "task_name": task_def.task_name,
                "old_value": old_value,
                "new_value": new_value,
                "status": user_task.status.value,
                "completed": new_value >= task_def.target_value
            })

        self.db.commit()
        return updated_tasks

    def claim_task_reward(self, user_id: str, user_task_id: str) -> Dict[str, Any]:
        """领取任务奖励"""
        user_task = self.db.query(UserTaskEntity).filter(
            UserTaskEntity.id == user_task_id,
            UserTaskEntity.user_id == user_id
        ).first()

        if not user_task:
            return {"success": False, "message": "任务不存在"}

        if user_task.status != TaskStatus.COMPLETED:
            return {"success": False, "message": "任务未完成，无法领取奖励"}

        if user_task.reward_claimed:
            return {"success": False, "message": "奖励已领取"}

        task_def = self.db.query(TaskDefinitionEntity).filter(
            TaskDefinitionEntity.id == user_task.task_id
        ).first()

        if not task_def:
            return {"success": False, "message": "任务配置不存在"}

        # 标记奖励已领取
        user_task.reward_claimed = True
        user_task.reward_claimed_at = datetime.now()

        # 这里应该调用积分/优惠券服务发放奖励
        # 为简化，仅返回奖励信息
        reward_info = {
            "reward_type": task_def.reward_type.value,
            "reward_value": task_def.reward_value,
            "reward_extra": json.loads(task_def.reward_extra) if task_def.reward_extra else None
        }

        self.db.commit()

        return {
            "success": True,
            "message": "奖励领取成功",
            "reward": reward_info
        }

    def get_task_progress(self, user_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务进度"""
        user_task = self.db.query(UserTaskEntity).filter(
            UserTaskEntity.user_id == user_id,
            UserTaskEntity.task_id == task_id
        ).first()

        if not user_task:
            return None

        task_def = self.db.query(TaskDefinitionEntity).filter(
            TaskDefinitionEntity.id == task_id
        ).first()

        return {
            "user_task_id": user_task.id,
            "task_name": task_def.task_name if task_def else "",
            "status": user_task.status.value,
            "current_value": user_task.current_value,
            "target_value": user_task.target_value,
            "progress_percent": round(user_task.current_value / user_task.target_value * 100, 2) if user_task.target_value > 0 else 0,
            "reward_claimed": user_task.reward_claimed,
            "started_at": user_task.started_at.isoformat() if user_task.started_at else None,
            "completed_at": user_task.completed_at.isoformat() if user_task.completed_at else None
        }


# ====================  会员成长服务  ====================

class MembershipGrowthService:
    """会员成长服务"""

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_member_profile(self, user_id: str) -> MemberProfileEntity:
        """获取或创建会员档案"""
        profile = self.db.query(MemberProfileEntity).filter(
            MemberProfileEntity.user_id == user_id
        ).first()

        if not profile:
            profile = MemberProfileEntity(
                id=str(uuid.uuid4()),
                user_id=user_id,
                current_level=MemberLevel.NORMAL,
                growth_value=0,
                total_growth_value=0
            )
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)

        return profile

    def add_growth_value(self, user_id: str, value: int, action_type: str, action_id: Optional[str] = None, remark: Optional[str] = None) -> Dict[str, Any]:
        """增加成长值"""
        profile = self.get_or_create_member_profile(user_id)

        old_value = profile.growth_value
        new_value = old_value + value

        # 记录成长值流水
        log = GrowthValueLogEntity(
            id=str(uuid.uuid4()),
            user_id=user_id,
            change_value=value,
            value_before=old_value,
            value_after=new_value,
            action_type=action_type,
            action_id=action_id,
            remark=remark
        )
        self.db.add(log)

        # 更新会员档案
        profile.growth_value = new_value
        profile.total_growth_value += value
        profile.updated_at = datetime.now()

        # 检查是否需要升级
        old_level = profile.current_level
        self._check_level_up(profile)
        level_changed = profile.current_level != old_level

        self.db.commit()

        return {
            "success": True,
            "message": f"成长值 +{value}",
            "old_value": old_value,
            "new_value": new_value,
            "current_level": profile.current_level.value,
            "level_up": level_changed,
            "next_level": profile.next_level.value if profile.next_level else None
        }

    def _check_level_up(self, profile: MemberProfileEntity):
        """检查是否升级"""
        configs = self.db.query(MemberLevelConfigEntity).filter(
            MemberLevelConfigEntity.is_active == True
        ).order_by(MemberLevelConfigEntity.sort_order).all()

        current_level = profile.current_level
        next_level = None

        for config in configs:
            if config.level.value == current_level.value:
                # 找到下一等级
                continue

            # 检查是否满足升级条件
            can_level_up = True
            if config.min_growth_value > 0 and profile.growth_value < config.min_growth_value:
                can_level_up = False
            if config.min_total_orders > 0 and profile.total_orders < config.min_total_orders:
                can_level_up = False
            if config.min_total_amount > 0 and profile.total_amount < config.min_total_amount:
                can_level_up = False

            if can_level_up:
                next_level = config.level
            else:
                break

        if next_level and next_level.value != current_level.value:
            profile.current_level = next_level
            profile.last_level_up_at = datetime.now()

            # 发放升级权益
            self._grant_level_benefits(profile.user_id, next_level)

        # 设置下一等级
        for config in configs:
            if config.level.value == (next_level.value if next_level else current_level.value):
                # 找到下一等级配置
                idx = configs.index(config)
                if idx < len(configs) - 1:
                    profile.next_level = configs[idx + 1].level
                else:
                    profile.next_level = None
                break

    def _grant_level_benefits(self, user_id: str, level: MemberLevel):
        """发放等级权益"""
        config = self.db.query(MemberLevelConfigEntity).filter(
            MemberLevelConfigEntity.level == level
        ).first()

        if not config or not config.benefit_codes:
            return

        benefit_codes = config.benefit_codes.split(",")
        benefits = json.loads(config.benefits) if config.benefits else {}

        for code in benefit_codes:
            benefit_value = benefits.get(code)
            if not benefit_value:
                continue

            benefit = MemberBenefitEntity(
                id=str(uuid.uuid4()),
                user_id=user_id,
                level=level,
                benefit_code=code,
                benefit_name=code,
                benefit_value=str(benefit_value),
                expires_at=datetime.now() + timedelta(days=30)  # 默认 30 天有效期
            )
            self.db.add(benefit)

    def get_member_profile(self, user_id: str) -> Dict[str, Any]:
        """获取会员档案"""
        profile = self.get_or_create_member_profile(user_id)

        # 获取等级配置
        level_config = self.db.query(MemberLevelConfigEntity).filter(
            MemberLevelConfigEntity.level == profile.current_level
        ).first()

        # 计算距离下一等级的进度
        next_level_value = 0
        if profile.next_level:
            next_config = self.db.query(MemberLevelConfigEntity).filter(
                MemberLevelConfigEntity.level == profile.next_level
            ).first()
            if next_config:
                next_level_value = next_config.min_growth_value

        progress_to_next = 0
        if next_level_value > 0:
            progress_to_next = round((profile.growth_value / next_level_value) * 100, 2)

        return {
            "user_id": profile.user_id,
            "current_level": profile.current_level.value,
            "current_level_name": level_config.level_name if level_config else profile.current_level.value,
            "growth_value": profile.growth_value,
            "total_growth_value": profile.total_growth_value,
            "total_orders": profile.total_orders,
            "total_amount": float(profile.total_amount) if profile.total_amount else 0,
            "member_days": profile.member_days,
            "next_level": profile.next_level.value if profile.next_level else None,
            "progress_to_next": progress_to_next,
            "benefits": json.loads(profile.benefits) if profile.benefits else [],
            "last_level_up_at": profile.last_level_up_at.isoformat() if profile.last_level_up_at else None
        }

    def update_member_stats(self, user_id: str, order_amount: Decimal):
        """更新会员统计（订单完成后调用）"""
        profile = self.get_or_create_member_profile(user_id)
        profile.total_orders += 1
        profile.total_amount += order_amount
        profile.member_days = (datetime.now() - profile.created_at).days if profile.created_at else 0
        self.db.commit()

    def get_level_configs(self) -> List[Dict[str, Any]]:
        """获取所有等级配置"""
        configs = self.db.query(MemberLevelConfigEntity).filter(
            MemberLevelConfigEntity.is_active == True
        ).order_by(MemberLevelConfigEntity.sort_order).all()

        result = []
        for config in configs:
            result.append({
                "level": config.level.value,
                "level_name": config.level_name,
                "min_growth_value": config.min_growth_value,
                "min_total_orders": config.min_total_orders,
                "min_total_amount": float(config.min_total_amount) if config.min_total_amount else 0,
                "benefits": json.loads(config.benefits) if config.benefits else [],
                "benefit_codes": config.benefit_codes.split(",") if config.benefit_codes else []
            })
        return result


# ====================  运营活动服务  ====================

class CampaignService:
    """运营活动服务"""

    def __init__(self, db: Session):
        self.db = db

    def get_campaign_templates(self, campaign_type: Optional[CampaignType] = None) -> List[Dict[str, Any]]:
        """获取活动模板列表"""
        query = self.db.query(CampaignTemplateEntity).filter(
            CampaignTemplateEntity.is_active == True
        )

        if campaign_type:
            query = query.filter(CampaignTemplateEntity.campaign_type == campaign_type)

        templates = query.all()

        result = []
        for template in templates:
            result.append({
                "template_id": template.id,
                "template_name": template.template_name,
                "campaign_type": template.campaign_type.value,
                "description": template.description,
                "tags": template.tags.split(",") if template.tags else [],
                "thumbnail": template.thumbnail,
                "config": json.loads(template.config) if template.config else {},
                "rules": json.loads(template.rules) if template.rules else {},
                "usage_count": template.usage_count
            })
        return result

    def create_campaign(self, campaign_name: str, campaign_type: CampaignType,
                       start_time: datetime, end_time: datetime,
                       config: Dict[str, Any], rules: Optional[Dict[str, Any]] = None,
                       template_id: Optional[str] = None,
                       creator_id: str = "admin") -> Dict[str, Any]:
        """创建活动实例"""
        campaign_no = f"CAMP{datetime.now().strftime('%Y%m%d%H%M%S')}"

        campaign = CampaignInstanceEntity(
            id=str(uuid.uuid4()),
            campaign_no=campaign_no,
            template_id=template_id,
            campaign_name=campaign_name,
            campaign_type=campaign_type,
            start_time=start_time,
            end_time=end_time,
            status=CampaignStatus.SCHEDULED,
            config=json.dumps(config),
            rules=json.dumps(rules) if rules else None,
            creator_id=creator_id
        )
        self.db.add(campaign)

        # 更新模板使用次数
        if template_id:
            template = self.db.query(CampaignTemplateEntity).filter(
                CampaignTemplateEntity.id == template_id
            ).first()
            if template:
                template.usage_count += 1

        self.db.commit()
        self.db.refresh(campaign)

        return {
            "success": True,
            "message": "活动创建成功",
            "campaign_no": campaign_no,
            "campaign_id": campaign.id
        }

    def get_active_campaigns(self, user_id: str) -> List[Dict[str, Any]]:
        """获取当前可进行的活动列表"""
        now = datetime.now()
        campaigns = self.db.query(CampaignInstanceEntity).filter(
            CampaignInstanceEntity.status == CampaignStatus.ACTIVE,
            CampaignInstanceEntity.start_time <= now,
            CampaignInstanceEntity.end_time >= now
        ).all()

        result = []
        for campaign in campaigns:
            # 检查用户是否已参与
            participated = self.db.query(CampaignParticipantEntity).filter(
                CampaignParticipantEntity.campaign_id == campaign.id,
                CampaignParticipantEntity.user_id == user_id
            ).first()

            result.append({
                "campaign_id": campaign.id,
                "campaign_no": campaign.campaign_no,
                "campaign_name": campaign.campaign_name,
                "campaign_type": campaign.campaign_type.value,
                "start_time": campaign.start_time.isoformat(),
                "end_time": campaign.end_time.isoformat(),
                "participant_count": campaign.participant_count,
                "config": json.loads(campaign.config) if campaign.config else {},
                "rules": json.loads(campaign.rules) if campaign.rules else {},
                "participated": participated is not None
            })
        return result

    def participate_campaign(self, campaign_id: str, user_id: str,
                            reward_type: Optional[str] = None,
                            reward_value: Optional[str] = None,
                            order_id: Optional[str] = None) -> Dict[str, Any]:
        """参与活动"""
        campaign = self.db.query(CampaignInstanceEntity).filter(
            CampaignInstanceEntity.id == campaign_id
        ).first()

        if not campaign:
            return {"success": False, "message": "活动不存在"}

        if campaign.status != CampaignStatus.ACTIVE:
            return {"success": False, "message": "活动不可参与"}

        # 检查是否已参与
        existing = self.db.query(CampaignParticipantEntity).filter(
            CampaignParticipantEntity.campaign_id == campaign_id,
            CampaignParticipantEntity.user_id == user_id
        ).first()

        if existing:
            return {"success": False, "message": "您已参与过此活动"}

        # 创建参与记录
        participant = CampaignParticipantEntity(
            id=str(uuid.uuid4()),
            campaign_id=campaign_id,
            user_id=user_id,
            order_id=order_id,
            reward_type=reward_type,
            reward_value=reward_value
        )
        self.db.add(participant)

        # 更新活动参与人数
        campaign.participant_count += 1
        if order_id:
            campaign.order_count += 1

        self.db.commit()

        return {
            "success": True,
            "message": "参与成功",
            "reward_type": reward_type,
            "reward_value": reward_value
        }

    def update_campaign_stats(self, campaign_id: str, gmv: Decimal):
        """更新活动统计数据"""
        campaign = self.db.query(CampaignInstanceEntity).filter(
            CampaignInstanceEntity.id == campaign_id
        ).first()

        if campaign:
            campaign.gmv += gmv
            self.db.commit()
