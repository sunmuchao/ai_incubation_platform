"""
P7 提案系统增强服务

提供：
- 提案模板功能
- 邀请投标功能
- 提案点券机制（防 spam）
- 提案数据分析
"""
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from enum import Enum
from collections import defaultdict


# ==================== 数据模型 ====================

class ProposalTemplate(BaseModel):
    """提案模板"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    tenant_id: str
    name: str
    title_template: str  # 标题模板
    content_template: str  # 内容模板
    category: Optional[str] = None  # 适用类别
    tags: List[str] = Field(default_factory=list)  # 标签
    usage_count: int = 0  # 使用次数
    is_public: bool = False  # 是否公开
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class JobInvitation(BaseModel):
    """邀请投标"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    job_posting_id: str
    inviter_id: str  # 邀请人
    invitee_id: str  # 被邀请人（员工所有者）
    employee_id: Optional[str] = None  # 指定员工
    message: Optional[str] = None
    status: str = "pending"  # pending, accepted, declined, expired
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.now)
    responded_at: Optional[datetime] = None


class CouponBook(BaseModel):
    """点券本"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    tenant_id: str
    total_coupons: int = 0  # 总点券数
    used_coupons: int = 0  # 已使用
    remaining_coupons: int = 0  # 剩余
    monthly_refresh: int = 10  # 每月刷新额度
    last_refresh_date: datetime
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class CouponTransaction(BaseModel):
    """点券交易记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    tenant_id: str
    coupon_book_id: str
    transaction_type: str  # use, refund, refresh, purchase
    amount: int
    balance_after: int
    related_proposal_id: Optional[str] = None
    description: str
    created_at: datetime = Field(default_factory=datetime.now)


class ProposalAnalytics(BaseModel):
    """提案数据分析"""
    user_id: str
    period: str

    # 总体统计
    total_proposals: int
    pending_proposals: int
    accepted_proposals: int
    rejected_proposals: int
    cancelled_proposals: int

    # 转化率
    acceptance_rate: float
    response_rate: float

    # 时间分析
    avg_response_time_hours: float
    avg_acceptance_time_hours: float

    # 职位类别分析
    category_breakdown: Dict[str, int]

    # 趋势
    trend: str  # improving, stable, declining


# ==================== 服务类 ====================

class EnhancedProposalService:
    """增强提案服务"""

    def __init__(self):
        # 内存存储
        self._templates: Dict[str, ProposalTemplate] = {}
        self._invitations: Dict[str, JobInvitation] = {}
        self._coupon_books: Dict[str, CouponBook] = {}
        self._coupon_transactions: Dict[str, CouponTransaction] = {}
        self._proposal_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total": 0,
            "pending": 0,
            "accepted": 0,
            "rejected": 0,
            "cancelled": 0,
            "expired": 0,
            "coupons_used": 0
        })

        # 点券配置
        self._coupon_config = {
            "default_monthly_refresh": 10,  # 每月免费点券
            "cost_per_proposal": 1,  # 每条提案消耗点券
            "max_proposals_per_job": 3,  # 单个职位最多提案次数
        }

    # ==================== 提案模板管理 ====================

    def create_template(self, data: Dict[str, Any]) -> ProposalTemplate:
        """创建提案模板"""
        template = ProposalTemplate(
            id=str(uuid.uuid4()),
            user_id=data['user_id'],
            tenant_id=data['tenant_id'],
            name=data['name'],
            title_template=data['title_template'],
            content_template=data['content_template'],
            category=data.get('category'),
            tags=data.get('tags', [])
        )
        self._templates[template.id] = template
        return template

    def get_template(self, template_id: str) -> Optional[ProposalTemplate]:
        """获取模板"""
        return self._templates.get(template_id)

    def list_templates(self, user_id: str, include_public: bool = True) -> List[ProposalTemplate]:
        """获取模板列表"""
        templates = [t for t in self._templates.values() if t.user_id == user_id]

        if include_public:
            public_templates = [t for t in self._templates.values() if t.is_public]
            templates.extend(public_templates)

        return templates

    def update_template(self, template_id: str, data: Dict[str, Any]) -> Optional[ProposalTemplate]:
        """更新模板"""
        if template_id in self._templates:
            template = self._templates[template_id]
            for key, value in data.items():
                if hasattr(template, key) and key not in ['id', 'created_at', 'usage_count']:
                    setattr(template, key, value)
            template.updated_at = datetime.now()
            return template
        return None

    def delete_template(self, template_id: str) -> bool:
        """删除模板"""
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False

    def increment_template_usage(self, template_id: str):
        """增加模板使用次数"""
        if template_id in self._templates:
            self._templates[template_id].usage_count += 1

    # ==================== 邀请投标管理 ====================

    def create_invitation(self, data: Dict[str, Any]) -> JobInvitation:
        """创建邀请投标"""
        expires_at = datetime.now() + timedelta(days=data.get('expires_days', 7))

        invitation = JobInvitation(
            id=str(uuid.uuid4()),
            tenant_id=data['tenant_id'],
            job_posting_id=data['job_posting_id'],
            inviter_id=data['inviter_id'],
            invitee_id=data['invitee_id'],
            employee_id=data.get('employee_id'),
            message=data.get('message'),
            expires_at=expires_at
        )
        self._invitations[invitation.id] = invitation
        return invitation

    def get_invitation(self, invitation_id: str) -> Optional[JobInvitation]:
        """获取邀请"""
        return self._invitations.get(invitation_id)

    def accept_invitation(self, invitation_id: str, employee_id: Optional[str] = None) -> bool:
        """接受邀请"""
        invitation = self.get_invitation(invitation_id)
        if not invitation or invitation.status != 'pending':
            return False

        # 检查是否过期
        if invitation.expires_at < datetime.now():
            invitation.status = 'expired'
            return False

        invitation.status = 'accepted'
        invitation.responded_at = datetime.now()
        if employee_id:
            invitation.employee_id = employee_id

        return True

    def decline_invitation(self, invitation_id: str, reason: Optional[str] = None) -> bool:
        """拒绝邀请"""
        invitation = self.get_invitation(invitation_id)
        if not invitation or invitation.status != 'pending':
            return False

        invitation.status = 'declined'
        invitation.responded_at = datetime.now()

        return True

    def list_invitations(self, invitee_id: Optional[str] = None,
                        inviter_id: Optional[str] = None,
                        status: Optional[str] = None) -> List[JobInvitation]:
        """获取邀请列表"""
        invitations = list(self._invitations.values())

        if invitee_id:
            invitations = [i for i in invitations if i.invitee_id == invitee_id]
        if inviter_id:
            invitations = [i for i in invitations if i.inviter_id == inviter_id]
        if status:
            invitations = [i for i in invitations if i.status == status]

        # 过滤过期
        now = datetime.now()
        active = []
        for i in invitations:
            if i.expires_at < now and i.status == 'pending':
                i.status = 'expired'
            active.append(i)

        return active

    def expire_invitations(self) -> int:
        """过期超时邀请"""
        now = datetime.now()
        expired_count = 0
        for invitation in self._invitations.values():
            if invitation.status == 'pending' and invitation.expires_at < now:
                invitation.status = 'expired'
                expired_count += 1
        return expired_count

    # ==================== 点券管理 ====================

    def get_or_create_coupon_book(self, user_id: str, tenant_id: str) -> CouponBook:
        """获取或创建点券本"""
        book_key = f"{user_id}_{tenant_id}"

        if book_key in self._coupon_books:
            book = self._coupon_books[book_key]
            # 检查是否需要刷新
            self._check_and_refresh_coupon_book(book)
            return book

        # 创建新的点券本
        now = datetime.now()
        book = CouponBook(
            id=str(uuid.uuid4()),
            user_id=user_id,
            tenant_id=tenant_id,
            total_coupons=self._coupon_config['default_monthly_refresh'],
            remaining_coupons=self._coupon_config['default_monthly_refresh'],
            last_refresh_date=now
        )
        self._coupon_books[book_key] = book

        # 记录初始点券
        self._record_coupon_transaction(
            user_id=user_id,
            tenant_id=tenant_id,
            coupon_book_id=book.id,
            transaction_type='refresh',
            amount=book.total_coupons,
            balance_after=book.remaining_coupons,
            description="初始点券"
        )

        return book

    def _check_and_refresh_coupon_book(self, book: CouponBook):
        """检查并刷新点券（每月刷新）"""
        now = datetime.now()
        days_since_refresh = (now - book.last_refresh_date).days

        if days_since_refresh >= 30:
            # 刷新点券
            old_remaining = book.remaining_coupons
            book.remaining_coupons = min(
                book.remaining_coupons + book.monthly_refresh,
                book.total_coupons + book.monthly_refresh
            )
            book.total_coupons += book.monthly_refresh
            book.last_refresh_date = now
            book.updated_at = now

            # 记录刷新
            self._record_coupon_transaction(
                user_id=book.user_id,
                tenant_id=book.tenant_id,
                coupon_book_id=book.id,
                transaction_type='refresh',
                amount=book.monthly_refresh,
                balance_after=book.remaining_coupons,
                description=f"月度刷新 ({book.monthly_refresh}点券)"
            )

    def use_coupon(self, user_id: str, tenant_id: str, proposal_id: str) -> bool:
        """使用点券"""
        book_key = f"{user_id}_{tenant_id}"

        if book_key not in self._coupon_books:
            return False

        book = self._coupon_books[book_key]

        if book.remaining_coupons < self._coupon_config['cost_per_proposal']:
            return False

        # 扣除点券
        book.remaining_coupons -= self._coupon_config['cost_per_proposal']
        book.used_coupons += self._coupon_config['cost_per_proposal']
        book.updated_at = datetime.now()

        # 记录交易
        self._record_coupon_transaction(
            user_id=user_id,
            tenant_id=tenant_id,
            coupon_book_id=book.id,
            transaction_type='use',
            amount=-self._coupon_config['cost_per_proposal'],
            balance_after=book.remaining_coupons,
            related_proposal_id=proposal_id,
            description=f"提案消耗 ({proposal_id})"
        )

        # 更新统计
        self._proposal_stats[user_id]['coupons_used'] += self._coupon_config['cost_per_proposal']

        return True

    def refund_coupon(self, user_id: str, tenant_id: str, proposal_id: str, reason: str) -> bool:
        """退还点券"""
        book_key = f"{user_id}_{tenant_id}"

        if book_key not in self._coupon_books:
            return False

        book = self._coupon_books[book_key]

        # 退还点券
        book.remaining_coupons += self._coupon_config['cost_per_proposal']
        book.used_coupons -= self._coupon_config['cost_per_proposal']
        book.updated_at = datetime.now()

        # 记录交易
        self._record_coupon_transaction(
            user_id=user_id,
            tenant_id=tenant_id,
            coupon_book_id=book.id,
            transaction_type='refund',
            amount=self._coupon_config['cost_per_proposal'],
            balance_after=book.remaining_coupons,
            related_proposal_id=proposal_id,
            description=f"点券退还：{reason}"
        )

        return True

    def _record_coupon_transaction(self, user_id: str, tenant_id: str,
                                   coupon_book_id: str, transaction_type: str,
                                   amount: int, balance_after: int,
                                   description: str,
                                   related_proposal_id: Optional[str] = None):
        """记录点券交易"""
        transaction = CouponTransaction(
            id=str(uuid.uuid4()),
            user_id=user_id,
            tenant_id=tenant_id,
            coupon_book_id=coupon_book_id,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=balance_after,
            related_proposal_id=related_proposal_id,
            description=description
        )
        self._coupon_transactions[transaction.id] = transaction

    def get_coupon_transactions(self, user_id: str, tenant_id: str,
                                limit: int = 50) -> List[CouponTransaction]:
        """获取点券交易记录"""
        transactions = [
            t for t in self._coupon_transactions.values()
            if t.user_id == user_id and t.tenant_id == tenant_id
        ]
        transactions.sort(key=lambda x: x.created_at, reverse=True)
        return transactions[:limit]

    def get_coupon_stats(self, user_id: str, tenant_id: str) -> Dict[str, Any]:
        """获取点券统计"""
        book = self.get_or_create_coupon_book(user_id, tenant_id)

        return {
            "total_coupons": book.total_coupons,
            "used_coupons": book.used_coupons,
            "remaining_coupons": book.remaining_coupons,
            "monthly_refresh": book.monthly_refresh,
            "last_refresh_date": book.last_refresh_date.isoformat(),
            "next_refresh_days": max(0, 30 - (datetime.now() - book.last_refresh_date).days)
        }

    # ==================== 提案数据分析 ====================

    def record_proposal(self, user_id: str, proposal_data: Dict[str, Any]):
        """记录提案统计"""
        self._proposal_stats[user_id]['total'] += 1
        self._proposal_stats[user_id]['pending'] += 1

    def update_proposal_status(self, user_id: str, old_status: str, new_status: str):
        """更新提案状态统计"""
        stats = self._proposal_stats[user_id]

        if old_status in stats:
            stats[old_status] -= 1
        if new_status in stats:
            stats[new_status] += 1

    def analyze_proposals(self, user_id: str, period: str = "last_30_days") -> ProposalAnalytics:
        """分析提案数据"""
        stats = self._proposal_stats[user_id]

        total = stats['total']
        if total == 0:
            return ProposalAnalytics(
                user_id=user_id,
                period=period,
                total_proposals=0,
                pending_proposals=0,
                accepted_proposals=0,
                rejected_proposals=0,
                cancelled_proposals=0,
                acceptance_rate=0,
                response_rate=0,
                avg_response_time_hours=0,
                avg_acceptance_time_hours=0,
                category_breakdown={},
                trend="stable"
            )

        # 计算转化率
        responded = stats['accepted'] + stats['rejected'] + stats['cancelled'] + stats['expired']
        acceptance_rate = (stats['accepted'] / total * 100) if total > 0 else 0
        response_rate = (responded / total * 100) if total > 0 else 0

        # 简化趋势分析
        if acceptance_rate >= 30:
            trend = "improving"
        elif acceptance_rate >= 15:
            trend = "stable"
        else:
            trend = "declining"

        return ProposalAnalytics(
            user_id=user_id,
            period=period,
            total_proposals=total,
            pending_proposals=stats['pending'],
            accepted_proposals=stats['accepted'],
            rejected_proposals=stats['rejected'],
            cancelled_proposals=stats['cancelled'],
            acceptance_rate=round(acceptance_rate, 2),
            response_rate=round(response_rate, 2),
            avg_response_time_hours=0,  # 需要实际数据
            avg_acceptance_time_hours=0,
            category_breakdown={},
            trend=trend
        )

    def get_proposal_dashboard(self, user_id: str) -> Dict[str, Any]:
        """获取提案仪表板数据"""
        stats = self._proposal_stats[user_id]
        analytics = self.analyze_proposals(user_id)

        return {
            "user_id": user_id,
            "overview": {
                "total_proposals": stats['total'],
                "pending": stats['pending'],
                "accepted": stats['accepted'],
                "rejected": stats['rejected'],
                "acceptance_rate": analytics.acceptance_rate
            },
            "coupon_usage": {
                "coupons_used": stats['coupons_used'],
                "avg_cost_per_accepted": stats['coupons_used'] / stats['accepted'] if stats['accepted'] > 0 else 0
            },
            "trend": analytics.trend,
            "recommendations": self._generate_proposal_recommendations(analytics)
        }

    def _generate_proposal_recommendations(self, analytics: ProposalAnalytics) -> List[str]:
        """生成提案建议"""
        recommendations = []

        if analytics.acceptance_rate < 10:
            recommendations.append("接受率较低，建议优化提案内容和定价策略")
        elif analytics.acceptance_rate < 20:
            recommendations.append("接受率有提升空间，建议针对匹配的职位提案")

        if analytics.pending_proposals > 10:
            recommendations.append("有待处理的提案，建议跟进提案状态")

        if analytics.trend == "declining":
            recommendations.append("提案效果呈下降趋势，建议调整投标策略")

        if not recommendations:
            recommendations.append("提案表现良好，保持当前策略")

        return recommendations


# 全局服务实例
enhanced_proposal_service = EnhancedProposalService()
