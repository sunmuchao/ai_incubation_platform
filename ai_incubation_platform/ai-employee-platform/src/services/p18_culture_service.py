"""
P18 阶段服务层 - 组织文化构建 (Organizational Culture Building)

本模块实现组织文化构建相关的业务逻辑，包括：
- 文化价值观管理
- 员工认可与奖励
- 团队凝聚力建设
- 文化契合度评估
- 多样性与包容性
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import uuid
import math

from models.p18_models import (
    CultureValue, CultureValueAlignment, Recognition, Badge, EmployeeBadge,
    TeamCohesionEvent, CultureFitAssessment, DiversityMetric, InclusionInitiative,
    CulturePulse, CulturePulseResponse, RewardRedemption, CultureMetrics,
    CultureValueType, RecognitionType, RecognitionCategory, AwardTier, TeamEventType,
    InclusionInitiativeType, DiversityDimension, SentimentLevel,
    CultureDB
)


# ==================== 文化价值观服务 ====================

class CultureValueService:
    """文化价值观服务"""
    
    def __init__(self, db: CultureDB):
        self.db = db
    
    def create_value(self, tenant_id: str, name: str, description: str,
                     value_type: CultureValueType, behavioral_indicators: List[str],
                     priority: int = 1, created_by: str = "") -> CultureValue:
        """创建文化价值观"""
        value = CultureValue(
            tenant_id=tenant_id,
            name=name,
            description=description,
            value_type=value_type,
            behavioral_indicators=behavioral_indicators,
            priority=priority,
            created_by=created_by
        )
        return self.db.save_culture_value(value)
    
    def update_value(self, value_id: str, name: Optional[str] = None,
                     description: Optional[str] = None,
                     behavioral_indicators: Optional[List[str]] = None,
                     priority: Optional[int] = None) -> Optional[CultureValue]:
        """更新文化价值观"""
        value = self.db.get_culture_value(value_id)
        if not value:
            return None
        
        if name is not None:
            value.name = name
        if description is not None:
            value.description = description
        if behavioral_indicators is not None:
            value.behavioral_indicators = behavioral_indicators
        if priority is not None:
            value.priority = priority
        
        return self.db.save_culture_value(value)
    
    def deactivate_value(self, value_id: str) -> bool:
        """停用文化价值观"""
        value = self.db.get_culture_value(value_id)
        if not value:
            return False
        value.is_active = False
        self.db.save_culture_value(value)
        return True
    
    def get_value(self, value_id: str) -> Optional[CultureValue]:
        """获取文化价值观"""
        return self.db.get_culture_value(value_id)
    
    def list_values(self, tenant_id: str, active_only: bool = True) -> List[CultureValue]:
        """列出文化价值观"""
        return self.db.list_culture_values(tenant_id, active_only)
    
    def assess_employee_alignment(self, employee_id: str, culture_value_id: str,
                                   alignment_score: float, assessor_id: str,
                                   evidence_examples: List[str] = None,
                                   comments: str = "",
                                   improvement_suggestions: List[str] = None) -> CultureValueAlignment:
        """评估员工文化价值观对齐度"""
        alignment = CultureValueAlignment(
            tenant_id="",  # 从 culture_value 获取
            employee_id=employee_id,
            culture_value_id=culture_value_id,
            alignment_score=alignment_score,
            assessor_id=assessor_id,
            evidence_examples=evidence_examples or [],
            comments=comments,
            improvement_suggestions=improvement_suggestions or []
        )
        return self.db.save_alignment(alignment)
    
    def get_employee_alignment_summary(self, employee_id: str) -> Dict[str, Any]:
        """获取员工文化价值观对齐度汇总"""
        alignments = self.db.get_employee_alignments(employee_id)
        if not alignments:
            return {"avg_alignment": 0, "alignments": [], "value_count": 0}
        
        avg_alignment = sum(a.alignment_score for a in alignments) / len(alignments)
        return {
            "avg_alignment": avg_alignment,
            "alignments": [a.to_dict() for a in alignments],
            "value_count": len(alignments)
        }


# ==================== 员工认可服务 ====================

class RecognitionService:
    """员工认可服务"""
    
    def __init__(self, db: CultureDB):
        self.db = db
    
    def give_recognition(self, tenant_id: str, recipient_id: str, giver_id: str,
                         recognition_type: RecognitionType, category: RecognitionCategory,
                         title: str, description: str, points: int = 0,
                         culture_value_ids: List[str] = None,
                         recipient_type: str = "individual") -> Recognition:
        """给予员工认可"""
        recognition = Recognition(
            tenant_id=tenant_id,
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            giver_id=giver_id,
            recognition_type=recognition_type,
            category=category,
            title=title,
            description=description,
            points=points,
            culture_value_ids=culture_value_ids or []
        )
        
        # 自动认可直接批准，其他需要审批
        if recognition_type == RecognitionType.AUTOMATED:
            recognition.status = "approved"
            recognition.approved_by = "system"
            recognition.approved_at = datetime.now()
        
        return self.db.save_recognition(recognition)
    
    def approve_recognition(self, recognition_id: str, approver_id: str) -> Optional[Recognition]:
        """批准认可记录"""
        recognition = self.db.get_recognition(recognition_id)
        if not recognition or recognition.status != "pending":
            return None
        
        recognition.status = "approved"
        recognition.approved_by = approver_id
        recognition.approved_at = datetime.now()
        
        # 授予徽章（如果有）
        if recognition.badge_id and recognition.recipient_type == "individual":
            self._award_recognition_badge(recognition)
        
        return self.db.save_recognition(recognition)
    
    def reject_recognition(self, recognition_id: str, approver_id: str) -> Optional[Recognition]:
        """拒绝认可记录"""
        recognition = self.db.get_recognition(recognition_id)
        if not recognition or recognition.status != "pending":
            return None
        
        recognition.status = "rejected"
        recognition.approved_by = approver_id
        recognition.approved_at = datetime.now()
        
        return self.db.save_recognition(recognition)
    
    def _award_recognition_badge(self, recognition: Recognition):
        """授予认可关联的徽章"""
        if not recognition.badge_id or recognition.recipient_type != "individual":
            return
        
        badge = self.db.get_recognition(recognition.badge_id)  # 这里应该是获取 badge，但模型中没有直接获取方法
        # 实际实现需要从 badges 表获取
        
        employee_badge = EmployeeBadge(
            tenant_id=recognition.tenant_id,
            employee_id=recognition.recipient_id,
            badge_id=recognition.badge_id,
            earned_at=datetime.now(),
            recognition_id=recognition.id
        )
        self.db.award_badge(employee_badge)
    
    def get_recognition(self, recognition_id: str) -> Optional[Recognition]:
        """获取认可记录"""
        return self.db.get_recognition(recognition_id)
    
    def list_recognitions(self, tenant_id: str, recipient_id: Optional[str] = None,
                          limit: int = 50) -> List[Recognition]:
        """列出认可记录"""
        return self.db.list_recognitions(tenant_id, recipient_id, limit)
    
    def get_employee_recognition_summary(self, employee_id: str, tenant_id: str) -> Dict[str, Any]:
        """获取员工认可汇总"""
        recognitions = self.db.list_recognitions(tenant_id, employee_id, limit=100)
        
        # 统计
        total_points = sum(r.points for r in recognitions if r.status == "approved")
        by_category = {}
        by_type = {}
        
        for r in recognitions:
            if r.status != "approved":
                continue
            cat = r.category.value
            typ = r.recognition_type.value
            by_category[cat] = by_category.get(cat, 0) + 1
            by_type[typ] = by_type.get(typ, 0) + 1
        
        return {
            "total_recognitions": len([r for r in recognitions if r.status == "approved"]),
            "total_points": total_points,
            "by_category": by_category,
            "by_type": by_type,
            "recent_recognitions": [r.to_dict() for r in recognitions[:10]]
        }


# ==================== 徽章服务 ====================

class BadgeService:
    """徽章服务"""
    
    def __init__(self, db: CultureDB):
        self.db = db
    
    def create_badge(self, tenant_id: str, name: str, description: str,
                     category: RecognitionCategory, tier: AwardTier,
                     icon_url: str = "", criteria: Dict[str, Any] = None,
                     points_value: int = 0) -> Badge:
        """创建徽章"""
        badge = Badge(
            tenant_id=tenant_id,
            name=name,
            description=description,
            category=category,
            tier=tier,
            icon_url=icon_url,
            criteria=criteria or {},
            points_value=points_value
        )
        return self.db.save_badge(badge)
    
    def list_badges(self, tenant_id: str, active_only: bool = True) -> List[Badge]:
        """列出徽章"""
        return self.db.list_badges(tenant_id, active_only)
    
    def award_badge(self, tenant_id: str, employee_id: str, badge_id: str,
                    recognition_id: Optional[str] = None,
                    expires_at: Optional[datetime] = None) -> EmployeeBadge:
        """授予员工徽章"""
        employee_badge = EmployeeBadge(
            tenant_id=tenant_id,
            employee_id=employee_id,
            badge_id=badge_id,
            earned_at=datetime.now(),
            recognition_id=recognition_id,
            expires_at=expires_at
        )
        return self.db.award_badge(employee_badge)
    
    def get_employee_badges(self, employee_id: str) -> List[EmployeeBadge]:
        """获取员工的徽章"""
        return self.db.get_employee_badges(employee_id)
    
    def check_auto_badge_eligibility(self, employee_id: str, tenant_id: str) -> List[str]:
        """检查员工是否符合自动授予徽章的条件"""
        earned_badges = self.get_employee_badges(employee_id)
        earned_badge_ids = set(eb.badge_id for eb in earned_badges)
        newly_earned = []
        
        # 这里应该实现自动徽章条件检查逻辑
        # 例如：获得 10 次认可自动授予"受欢迎"徽章
        
        return newly_earned


# ==================== 团队凝聚力服务 ====================

class TeamCohesionService:
    """团队凝聚力服务"""
    
    def __init__(self, db: CultureDB):
        self.db = db
    
    def create_event(self, tenant_id: str, team_id: str, organizer_id: str,
                     event_type: TeamEventType, title: str, description: str,
                     start_time: datetime, end_time: datetime,
                     location: str = "", max_participants: int = 0,
                     budget: Optional[float] = None) -> TeamCohesionEvent:
        """创建团队活动"""
        event = TeamCohesionEvent(
            tenant_id=tenant_id,
            team_id=team_id,
            organizer_id=organizer_id,
            event_type=event_type,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            location=location,
            max_participants=max_participants,
            budget=budget
        )
        return self.db.save_team_event(event)
    
    def join_event(self, event_id: str, employee_id: str) -> Optional[TeamCohesionEvent]:
        """加入团队活动"""
        event = self.db.get_team_event(event_id)
        if not event or event.status != "planned":
            return None
        
        # 检查人数限制
        if event.max_participants > 0 and len(event.participants) >= event.max_participants:
            return None
        
        if employee_id not in event.participants:
            event.participants.append(employee_id)
            self.db.save_team_event(event)
        
        return event
    
    def leave_event(self, event_id: str, employee_id: str) -> Optional[TeamCohesionEvent]:
        """离开团队活动"""
        event = self.db.get_team_event(event_id)
        if not event:
            return None
        
        if employee_id in event.participants:
            event.participants.remove(employee_id)
            self.db.save_team_event(event)
        
        return event
    
    def complete_event(self, event_id: str, photos: List[str] = None,
                       feedback_summary: str = None) -> Optional[TeamCohesionEvent]:
        """完成团队活动"""
        event = self.db.get_team_event(event_id)
        if not event:
            return None
        
        event.status = "completed"
        if photos:
            event.photos = photos
        if feedback_summary:
            event.feedback_summary = feedback_summary
        
        return self.db.save_team_event(event)
    
    def cancel_event(self, event_id: str) -> bool:
        """取消团队活动"""
        event = self.db.get_team_event(event_id)
        if not event:
            return False
        
        event.status = "cancelled"
        self.db.save_team_event(event)
        return True
    
    def get_event(self, event_id: str) -> Optional[TeamCohesionEvent]:
        """获取团队活动"""
        return self.db.get_team_event(event_id)
    
    def list_team_events(self, tenant_id: str, team_id: Optional[str] = None) -> List[TeamCohesionEvent]:
        """列出团队活动"""
        return self.db.list_team_events(tenant_id, team_id)
    
    def get_team_cohesion_metrics(self, team_id: str, tenant_id: str) -> Dict[str, Any]:
        """获取团队凝聚力指标"""
        events = self.db.list_team_events(tenant_id, team_id)
        
        total_events = len(events)
        completed_events = len([e for e in events if e.status == "completed"])
        
        # 计算平均参与率
        total_participants = sum(len(e.participants) for e in events if e.status == "completed")
        avg_participants = total_participants / completed_events if completed_events > 0 else 0
        
        return {
            "total_events": total_events,
            "completed_events": completed_events,
            "planned_events": len([e for e in events if e.status == "planned"]),
            "cancelled_events": len([e for e in events if e.status == "cancelled"]),
            "avg_participation": avg_participants,
            "recent_events": [e.to_dict() for e in events[:5]]
        }


# ==================== 文化契合度评估服务 ====================

class CultureFitService:
    """文化契合度评估服务"""
    
    def __init__(self, db: CultureDB):
        self.db = db
    
    def create_assessment(self, tenant_id: str, employee_id: str, assessor_id: str,
                          assessment_type: str, overall_score: float,
                          dimension_scores: Dict[str, float],
                          strengths: List[str] = None,
                          development_areas: List[str] = None,
                          comments: str = "",
                          recommendations: List[str] = None) -> CultureFitAssessment:
        """创建文化契合度评估"""
        assessment = CultureFitAssessment(
            tenant_id=tenant_id,
            employee_id=employee_id,
            assessor_id=assessor_id,
            assessment_type=assessment_type,
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            strengths=strengths or [],
            development_areas=development_areas or [],
            comments=comments,
            recommendations=recommendations or []
        )
        return self.db.save_culture_fit_assessment(assessment)
    
    def get_employee_assessments(self, employee_id: str) -> List[CultureFitAssessment]:
        """获取员工的文化契合度评估历史"""
        return self.db.get_employee_culture_fit(employee_id)
    
    def get_latest_assessment(self, employee_id: str) -> Optional[CultureFitAssessment]:
        """获取员工最新的文化契合度评估"""
        assessments = self.get_employee_assessments(employee_id)
        return assessments[0] if assessments else None
    
    def calculate_team_culture_fit_avg(self, employee_ids: List[str]) -> float:
        """计算团队平均文化契合度"""
        if not employee_ids:
            return 0.0
        
        total_score = 0.0
        count = 0
        
        for emp_id in employee_ids:
            assessments = self.get_employee_assessments(emp_id)
            if assessments:
                total_score += assessments[0].overall_score
                count += 1
        
        return total_score / count if count > 0 else 0.0


# ==================== 多样性与包容性服务 ====================

class DiversityInclusionService:
    """多样性与包容性服务"""
    
    def __init__(self, db: CultureDB):
        self.db = db
    
    def record_diversity_metric(self, tenant_id: str, dimension: DiversityDimension,
                                 distribution: Dict[str, float],
                                 representation_rate: float,
                                 inclusion_index: float,
                                 team_id: Optional[str] = None,
                                 comments: str = "") -> DiversityMetric:
        """记录多样性指标"""
        metric = DiversityMetric(
            tenant_id=tenant_id,
            dimension=dimension,
            team_id=team_id,
            metric_date=datetime.now(),
            distribution=distribution,
            representation_rate=representation_rate,
            inclusion_index=inclusion_index,
            comments=comments
        )
        return self.db.save_diversity_metric(metric)
    
    def get_diversity_trends(self, tenant_id: str, dimension: DiversityDimension,
                              team_id: Optional[str] = None) -> List[DiversityMetric]:
        """获取多样性趋势"""
        return self.db.get_diversity_metrics(tenant_id, dimension)
    
    def create_inclusion_initiative(self, tenant_id: str, initiative_type: InclusionInitiativeType,
                                     title: str, description: str, owner_id: str,
                                     target_dimensions: List[DiversityDimension],
                                     start_date: datetime,
                                     end_date: Optional[datetime] = None,
                                     budget: Optional[float] = None) -> InclusionInitiative:
        """创建包容性举措"""
        initiative = InclusionInitiative(
            tenant_id=tenant_id,
            initiative_type=initiative_type,
            title=title,
            description=description,
            owner_id=owner_id,
            target_dimensions=target_dimensions,
            start_date=start_date,
            end_date=end_date,
            budget=budget
        )
        return self.db.save_inclusion_initiative(initiative)
    
    def update_initiative_status(self, initiative_id: str, status: str) -> Optional[InclusionInitiative]:
        """更新举措状态"""
        initiative = self.db.get_inclusion_initiative(initiative_id) if hasattr(self.db, 'get_inclusion_initiative') else None
        # 需要从 DB 获取，这里简化处理
        return initiative
    
    def list_initiatives(self, tenant_id: str, status: Optional[str] = None) -> List[InclusionInitiative]:
        """列出包容性举措"""
        return self.db.list_inclusion_initiatives(tenant_id, status)
    
    def calculate_diversity_index(self, distributions: Dict[str, Dict[str, float]]) -> float:
        """
        计算多样性指数（使用 Shannon Diversity Index）
        
        distributions: {dimension: {category: proportion}}
        """
        if not distributions:
            return 0.0
        
        indices = []
        for dimension, categories in distributions.items():
            if not categories:
                continue
            
            shannon_index = 0.0
            for proportion in categories.values():
                if proportion > 0:
                    shannon_index -= proportion * math.log(proportion)
            
            # 归一化到 0-100
            max_index = math.log(len(categories)) if len(categories) > 1 else 1
            normalized_index = (shannon_index / max_index * 100) if max_index > 0 else 0
            indices.append(normalized_index)
        
        return sum(indices) / len(indices) if indices else 0.0


# ==================== 文化脉冲调查服务 ====================

class CulturePulseService:
    """文化脉冲调查服务"""
    
    def __init__(self, db: CultureDB):
        self.db = db
    
    def create_pulse(self, tenant_id: str, title: str, question: str,
                     question_type: str = "scale",
                     scale_min: int = 1, scale_max: int = 5,
                     scale_labels: Dict[int, str] = None,
                     options: List[str] = None,
                     is_anonymous: bool = True,
                     frequency: str = "weekly",
                     created_by: str = "") -> CulturePulse:
        """创建文化脉冲调查"""
        pulse = CulturePulse(
            tenant_id=tenant_id,
            title=title,
            question=question,
            question_type=question_type,
            scale_min=scale_min,
            scale_max=scale_max,
            scale_labels=scale_labels or {},
            options=options or [],
            is_anonymous=is_anonymous,
            frequency=frequency,
            created_by=created_by
        )
        return self.db.save_culture_pulse(pulse)
    
    def deactivate_pulse(self, pulse_id: str) -> bool:
        """停用脉冲调查"""
        pulse = self.db.get_culture_pulse(pulse_id) if hasattr(self.db, 'get_culture_pulse') else None
        if not pulse:
            return False
        pulse.is_active = False
        self.db.save_culture_pulse(pulse)
        return True
    
    def list_pulses(self, tenant_id: str, active_only: bool = True) -> List[CulturePulse]:
        """列出脉冲调查"""
        return self.db.list_culture_pulses(tenant_id, active_only)
    
    def submit_response(self, pulse_id: str, respondent_id: Optional[str],
                        response_value: Optional[float] = None,
                        response_text: Optional[str] = None,
                        is_anonymous: bool = True) -> CulturePulseResponse:
        """提交脉冲调查回复"""
        response = CulturePulseResponse(
            pulse_id=pulse_id,
            respondent_id=respondent_id or "",
            response_value=response_value,
            response_text=response_text,
            is_anonymous=is_anonymous
        )
        
        # AI 情感分析（如果有文本回复）
        if response_text:
            response.sentiment = self._analyze_sentiment(response_text)
        
        return self.db.save_pulse_response(response)
    
    def _analyze_sentiment(self, text: str) -> SentimentLevel:
        """分析文本情感（简化版）"""
        # 实际实现应该调用 AI 服务进行情感分析
        positive_words = ['好', '满意', '积极', '喜欢', '棒', 'great', 'good', 'excellent']
        negative_words = ['差', '不满意', '消极', '讨厌', '糟', 'bad', 'poor', 'terrible']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count + 2:
            return SentimentLevel.VERY_POSITIVE
        elif positive_count > negative_count:
            return SentimentLevel.POSITIVE
        elif negative_count > positive_count + 2:
            return SentimentLevel.VERY_NEGATIVE
        elif negative_count > positive_count:
            return SentimentLevel.NEGATIVE
        else:
            return SentimentLevel.NEUTRAL
    
    def get_pulse_results(self, pulse_id: str) -> Dict[str, Any]:
        """获取脉冲调查结果"""
        responses = self.db.get_pulse_responses(pulse_id)
        
        if not responses:
            return {"total_responses": 0, "responses": []}
        
        # 统计分析
        numeric_responses = [r.response_value for r in responses if r.response_value is not None]
        avg_score = sum(numeric_responses) / len(numeric_responses) if numeric_responses else 0
        
        sentiment_distribution = {}
        for r in responses:
            if r.sentiment:
                sent = r.sentiment.value
                sentiment_distribution[sent] = sentiment_distribution.get(sent, 0) + 1
        
        return {
            "total_responses": len(responses),
            "avg_score": avg_score,
            "sentiment_distribution": sentiment_distribution,
            "participation_rate": 0,  # 需要总人数来计算
            "recent_responses": [r.to_dict() for r in responses[-20:]]
        }


# ==================== 积分兑换服务 ====================

class RewardRedemptionService:
    """积分兑换服务"""
    
    def __init__(self, db: CultureDB):
        self.db = db
    
    def request_redemption(self, tenant_id: str, employee_id: str,
                           reward_name: str, reward_description: str,
                           points_cost: int) -> RewardRedemption:
        """请求积分兑换"""
        redemption = RewardRedemption(
            tenant_id=tenant_id,
            employee_id=employee_id,
            reward_name=reward_name,
            reward_description=reward_description,
            points_cost=points_cost
        )
        return self.db.save_reward_redemption(redemption)
    
    def approve_redemption(self, redemption_id: str, approver_id: str) -> Optional[RewardRedemption]:
        """批准积分兑换"""
        redemption = self.db.get_reward_redemption(redemption_id) if hasattr(self.db, 'get_reward_redemption') else None
        if not redemption or redemption.status != "pending":
            return None
        
        redemption.status = "approved"
        redemption.approved_by = approver_id
        redemption.approved_at = datetime.now()
        
        return self.db.save_reward_redemption(redemption)
    
    def fulfill_redemption(self, redemption_id: str) -> Optional[RewardRedemption]:
        """完成积分兑换"""
        redemption = self.db.get_reward_redemption(redemption_id) if hasattr(self.db, 'get_reward_redemption') else None
        if not redemption or redemption.status != "approved":
            return None
        
        redemption.status = "fulfilled"
        redemption.fulfilled_at = datetime.now()
        
        return self.db.save_reward_redemption(redemption)
    
    def get_employee_redemptions(self, employee_id: str) -> List[RewardRedemption]:
        """获取员工的积分兑换记录"""
        return self.db.get_employee_redemptions(employee_id)


# ==================== 文化指标汇总服务 ====================

class CultureMetricsService:
    """文化指标汇总服务"""
    
    def __init__(self, db: CultureDB, 
                 culture_value_service: CultureValueService,
                 recognition_service: RecognitionService,
                 team_cohesion_service: TeamCohesionService,
                 culture_fit_service: CultureFitService,
                 diversity_service: DiversityInclusionService,
                 pulse_service: CulturePulseService):
        self.db = db
        self.culture_value_service = culture_value_service
        self.recognition_service = recognition_service
        self.team_cohesion_service = team_cohesion_service
        self.culture_fit_service = culture_fit_service
        self.diversity_service = diversity_service
        self.pulse_service = pulse_service
    
    def calculate_daily_metrics(self, tenant_id: str, 
                                 employee_ids: List[str]) -> CultureMetrics:
        """计算每日文化指标"""
        metrics = CultureMetrics(
            tenant_id=tenant_id,
            metric_date=datetime.now()
        )
        
        # 1. 文化价值观对齐度
        alignment_scores = []
        for emp_id in employee_ids:
            summary = self.culture_value_service.get_employee_alignment_summary(emp_id)
            if summary["avg_alignment"] > 0:
                alignment_scores.append(summary["avg_alignment"])
        
        if alignment_scores:
            metrics.avg_culture_alignment = sum(alignment_scores) / len(alignment_scores)
        
        # 2. 认可与奖励
        total_recognitions = 0
        recognitions_by_category = {}
        total_points = 0
        for emp_id in employee_ids:
            summary = self.recognition_service.get_employee_recognition_summary(emp_id, tenant_id)
            total_recognitions += summary["total_recognitions"]
            total_points += summary["total_points"]
            for cat, count in summary["by_category"].items():
                recognitions_by_category[cat] = recognitions_by_category.get(cat, 0) + count
        
        metrics.total_recognitions = total_recognitions
        metrics.recognitions_by_category = recognitions_by_category
        metrics.avg_points_per_employee = total_points / len(employee_ids) if employee_ids else 0
        
        # 3. 团队凝聚力
        # 简化：统计所有团队活动
        metrics.team_events_count = 0  # 需要遍历所有团队
        metrics.avg_event_participation = 0
        
        # 4. 文化契合度
        fit_scores = []
        for emp_id in employee_ids:
            assessment = self.culture_fit_service.get_latest_assessment(emp_id)
            if assessment:
                fit_scores.append(assessment.overall_score)
        
        if fit_scores:
            metrics.avg_culture_fit_score = sum(fit_scores) / len(fit_scores)
        
        # 5. 多样性与包容性（简化）
        metrics.diversity_index = 75.0  # 示例值
        metrics.inclusion_index = 80.0  # 示例值
        
        # 6. 文化脉冲
        metrics.pulse_participation_rate = 0.7  # 示例值
        metrics.avg_pulse_score = 4.2  # 示例值
        
        # 7. 整体文化健康度（加权平均）
        weights = {
            "alignment": 0.2,
            "recognition": 0.2,
            "cohesion": 0.15,
            "fit": 0.2,
            "diversity": 0.15,
            "pulse": 0.1
        }
        
        normalized_scores = [
            metrics.avg_culture_alignment,  # 0-100
            min(100, metrics.total_recognitions / max(1, len(employee_ids)) * 10),  # 归一化
            metrics.avg_event_participation * 10,  # 归一化
            metrics.avg_culture_fit_score,  # 0-100
            metrics.diversity_index,  # 0-100
            metrics.avg_pulse_score * 20  # 1-5 -> 0-100
        ]
        
        weighted_sum = sum(s * w for s, w in zip(normalized_scores, weights.values()))
        metrics.overall_culture_health_score = weighted_sum
        
        return self.db.save_culture_metrics(metrics)
    
    def get_culture_dashboard(self, tenant_id: str, 
                               days: int = 30) -> Dict[str, Any]:
        """获取文化仪表盘"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        metrics_list = self.db.get_culture_metrics(tenant_id, start_date, end_date)
        
        if not metrics_list:
            return {"message": "No metrics available"}
        
        # 最新指标
        latest = metrics_list[0]
        
        # 趋势分析
        trend_data = {
            "culture_alignment": [m.avg_culture_alignment for m in reversed(metrics_list)],
            "recognitions": [m.total_recognitions for m in reversed(metrics_list)],
            "culture_fit": [m.avg_culture_fit_score for m in reversed(metrics_list)],
            "diversity_index": [m.diversity_index for m in reversed(metrics_list)],
            "overall_health": [m.overall_culture_health_score for m in reversed(metrics_list)]
        }
        
        return {
            "latest_metrics": latest.to_dict(),
            "trend_data": trend_data,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }


# ==================== 统一外观服务 ====================

class CultureService:
    """组织文化统一外观服务"""
    
    def __init__(self, db_path: str = "test.db"):
        self.db = CultureDB(db_path)
        self.culture_value_service = CultureValueService(self.db)
        self.recognition_service = RecognitionService(self.db)
        self.badge_service = BadgeService(self.db)
        self.team_cohesion_service = TeamCohesionService(self.db)
        self.culture_fit_service = CultureFitService(self.db)
        self.diversity_service = DiversityInclusionService(self.db)
        self.pulse_service = CulturePulseService(self.db)
        self.redemption_service = RewardRedemptionService(self.db)
        self.metrics_service = None  # 延迟初始化
        
        # 初始化指标服务（需要其他服务实例）
        self.metrics_service = CultureMetricsService(
            self.db,
            self.culture_value_service,
            self.recognition_service,
            self.team_cohesion_service,
            self.culture_fit_service,
            self.diversity_service,
            self.pulse_service
        )
    
    # 委托方法 - 文化价值观
    def create_culture_value(self, *args, **kwargs):
        return self.culture_value_service.create_value(*args, **kwargs)
    
    def list_culture_values(self, *args, **kwargs):
        return self.culture_value_service.list_values(*args, **kwargs)
    
    def assess_employee_alignment(self, *args, **kwargs):
        return self.culture_value_service.assess_employee_alignment(*args, **kwargs)
    
    # 委托方法 - 员工认可
    def give_recognition(self, *args, **kwargs):
        return self.recognition_service.give_recognition(*args, **kwargs)
    
    def approve_recognition(self, *args, **kwargs):
        return self.recognition_service.approve_recognition(*args, **kwargs)
    
    def list_recognitions(self, *args, **kwargs):
        return self.recognition_service.list_recognitions(*args, **kwargs)
    
    # 委托方法 - 徽章
    def create_badge(self, *args, **kwargs):
        return self.badge_service.create_badge(*args, **kwargs)
    
    def award_badge(self, *args, **kwargs):
        return self.badge_service.award_badge(*args, **kwargs)
    
    # 委托方法 - 团队活动
    def create_team_event(self, *args, **kwargs):
        return self.team_cohesion_service.create_event(*args, **kwargs)
    
    def join_team_event(self, *args, **kwargs):
        return self.team_cohesion_service.join_event(*args, **kwargs)
    
    def list_team_events(self, *args, **kwargs):
        return self.team_cohesion_service.list_team_events(*args, **kwargs)
    
    # 委托方法 - 文化契合度
    def create_culture_fit_assessment(self, *args, **kwargs):
        return self.culture_fit_service.create_assessment(*args, **kwargs)
    
    # 委托方法 - 多样性与包容性
    def record_diversity_metric(self, *args, **kwargs):
        return self.diversity_service.record_diversity_metric(*args, **kwargs)
    
    def create_inclusion_initiative(self, *args, **kwargs):
        return self.diversity_service.create_inclusion_initiative(*args, **kwargs)
    
    # 委托方法 - 文化脉冲
    def create_culture_pulse(self, *args, **kwargs):
        return self.pulse_service.create_pulse(*args, **kwargs)
    
    def submit_pulse_response(self, *args, **kwargs):
        return self.pulse_service.submit_response(*args, **kwargs)
    
    def get_pulse_results(self, *args, **kwargs):
        return self.pulse_service.get_pulse_results(*args, **kwargs)
    
    # 委托方法 - 积分兑换
    def request_redemption(self, *args, **kwargs):
        return self.redemption_service.request_redemption(*args, **kwargs)
    
    # 委托方法 - 文化指标
    def calculate_daily_metrics(self, *args, **kwargs):
        return self.metrics_service.calculate_daily_metrics(*args, **kwargs)
    
    def get_culture_dashboard(self, *args, **kwargs):
        return self.metrics_service.get_culture_dashboard(*args, **kwargs)


# 导出所有服务类
__all__ = [
    'CultureValueService',
    'RecognitionService',
    'BadgeService',
    'TeamCohesionService',
    'CultureFitService',
    'DiversityInclusionService',
    'CulturePulseService',
    'RewardRedemptionService',
    'CultureMetricsService',
    'CultureService'
]
