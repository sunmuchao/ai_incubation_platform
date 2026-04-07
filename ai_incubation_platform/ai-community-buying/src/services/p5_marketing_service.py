"""
P5 营销自动化系统 - 服务层实现

包含：
1. 用户分群服务 (Customer Segmentation Service) - RFM 模型用户分群
2. 营销自动化服务 (Marketing Automation Service) - 自动化营销活动执行
3. 营销 ROI 分析服务 (Marketing ROI Analysis Service) - 活动效果分析
4. A/B 测试服务 (A/B Testing Service) - 营销测试框架
5. 智能优惠券服务 (Smart Coupon Service) - 千人千券策略
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, cast, Date
from decimal import Decimal
import json
import logging
import hashlib
import random

from models.p5_entities import (
    CustomerSegmentEntity, CustomerSegmentMemberEntity, CustomerBehaviorEntity,
    MarketingAutomationEntity, AutomationTriggerLogEntity,
    CampaignROIEntity, CampaignDailyStatsEntity,
    ABTestEntity, ABTestVariantEntity, ABTestUserAssignmentEntity,
    SmartCouponStrategyEntity, UserCouponPreferenceEntity, MarketingEventEntity
)

logger = logging.getLogger(__name__)


# ====================  用户分群服务  ====================

class CustomerSegmentationService:
    """客户分群服务 - 基于 RFM 模型的用户价值分群"""

    def __init__(self, db: Session):
        self.db = db

    def calculate_rfm_scores(self, user_id: str) -> Dict[str, int]:
        """计算用户 RFM 评分"""
        now = datetime.now()

        # 获取用户购买行为
        from models.entities import OrderEntity
        orders = self.db.query(OrderEntity).filter(
            OrderEntity.user_id == user_id,
            OrderEntity.status == "completed"
        ).all()

        if not orders:
            return {"r": 1, "f": 1, "m": 1, "total": 3}

        # R - Recency (最近一次消费时间)
        last_order = max(orders, key=lambda x: x.completed_at or datetime.min)
        days_since_last = (now - last_order.completed_at).days if last_order.completed_at else 365

        if days_since_last <= 7:
            r_score = 5
        elif days_since_last <= 30:
            r_score = 4
        elif days_since_last <= 90:
            r_score = 3
        elif days_since_last <= 180:
            r_score = 2
        else:
            r_score = 1

        # F - Frequency (消费频率)
        order_count = len(orders)
        if order_count >= 10:
            f_score = 5
        elif order_count >= 5:
            f_score = 4
        elif order_count >= 3:
            f_score = 3
        elif order_count >= 2:
            f_score = 2
        else:
            f_score = 1

        # M - Monetary (消费金额)
        total_amount = sum(float(o.total_amount) for o in orders)
        if total_amount >= 1000:
            m_score = 5
        elif total_amount >= 500:
            m_score = 4
        elif total_amount >= 200:
            m_score = 3
        elif total_amount >= 50:
            m_score = 2
        else:
            m_score = 1

        return {"r": r_score, "f": f_score, "m": m_score, "total": r_score + f_score + m_score}

    def determine_segment_type(self, rfm_scores: Dict[str, int]) -> str:
        """根据 RFM 评分确定用户分群类型"""
        r, f, m = rfm_scores["r"], rfm_scores["f"], rfm_scores["m"]

        # 高价值客户：R 近 F 高 M 高
        if r >= 4 and f >= 4 and m >= 4:
            return "high_value"

        # 潜力客户：R 近但 F/M 低
        if r >= 4 and f <= 2 and m <= 2:
            return "potential"

        # 流失风险客户：R 远
        if r <= 2:
            return "churning"

        # 沉睡客户：R 很远且 F 低
        if r == 1 and f <= 2:
            return "dormant"

        # 价格敏感型：F 高但 M 低
        if f >= 4 and m <= 2:
            return "bargain_hunter"

        # 新客户：F=1
        if f == 1:
            return "new"

        return "potential"

    def update_user_segment(self, user_id: str) -> Optional[CustomerSegmentMemberEntity]:
        """更新用户分群信息"""
        # 计算 RFM 评分
        rfm_scores = self.calculate_rfm_scores(user_id)

        # 获取或创建用户分群成员记录
        member = self.db.query(CustomerSegmentMemberEntity).filter(
            CustomerSegmentMemberEntity.user_id == user_id
        ).first()

        if not member:
            member = CustomerSegmentMemberEntity(user_id=user_id)
            self.db.add(member)

        # 更新 RFM 评分
        member.recency_score = rfm_scores["r"]
        member.frequency_score = rfm_scores["f"]
        member.monetary_score = rfm_scores["m"]
        member.rfm_total = rfm_scores["total"]

        # 确定分群类型
        segment_type = self.determine_segment_type(rfm_scores)

        # 获取或创建分群
        segment = self.db.query(CustomerSegmentEntity).filter(
            CustomerSegmentEntity.segment_type == segment_type
        ).first()

        if not segment:
            segment = CustomerSegmentEntity(
                segment_name=f"{segment_type} Customers",
                segment_type=segment_type,
                rules=json.dumps({"auto_created": True})
            )
            self.db.add(segment)
            self.db.commit()
            self.db.refresh(segment)

        # 更新分群关联
        old_segment_id = member.segment_id
        member.segment_id = segment.id

        # 更新用户行为数据
        self._update_user_behavior(user_id)

        # 更新分群规模
        self._update_segment_count(segment.id)
        if old_segment_id:
            self._update_segment_count(old_segment_id)

        self.db.commit()
        self.db.refresh(member)

        logger.info(f"用户 {user_id} 分群更新：{segment_type}, RFM={rfm_scores}")
        return member

    def _update_user_behavior(self, user_id: str):
        """更新用户行为数据"""
        from models.entities import OrderEntity, GroupBuyEntity

        # 获取用户订单
        orders = self.db.query(OrderEntity).filter(
            OrderEntity.user_id == user_id,
            OrderEntity.status == "completed"
        ).all()

        # 获取或创建行为记录
        behavior = self.db.query(CustomerBehaviorEntity).filter(
            CustomerBehaviorEntity.user_id == user_id
        ).first()

        if not behavior:
            behavior = CustomerBehaviorEntity(user_id=user_id)
            self.db.add(behavior)

        if orders:
            behavior.total_orders = len(orders)
            behavior.total_amount = sum(o.total_amount for o in orders)
            behavior.avg_order_value = behavior.total_amount / len(orders)
            behavior.last_purchase_at = max(o.completed_at for o in orders if o.completed_at)

            # 分析购买品类偏好
            category_counts = {}
            for order in orders:
                # 简化处理，实际需要关联商品表
                pass

        self.db.commit()

    def _update_segment_count(self, segment_id: str):
        """更新分群规模统计"""
        count = self.db.query(CustomerSegmentMemberEntity).filter(
            CustomerSegmentMemberEntity.segment_id == segment_id
        ).count()

        segment = self.db.query(CustomerSegmentEntity).filter(
            CustomerSegmentEntity.id == segment_id
        ).first()

        if segment:
            segment.customer_count = count
            self.db.commit()

    def get_segment_members(self, segment_id: str, limit: int = 100) -> List[CustomerSegmentMemberEntity]:
        """获取分群成员列表"""
        return self.db.query(CustomerSegmentMemberEntity).filter(
            CustomerSegmentMemberEntity.segment_id == segment_id
        ).limit(limit).all()

    def get_user_segments(self, user_id: str) -> List[CustomerSegmentEntity]:
        """获取用户所属分群"""
        member = self.db.query(CustomerSegmentMemberEntity).filter(
            CustomerSegmentMemberEntity.user_id == user_id
        ).first()

        if not member:
            return []

        segment = self.db.query(CustomerSegmentEntity).filter(
            CustomerSegmentEntity.id == member.segment_id
        ).first()

        return [segment] if segment else []

    def create_segment(self, segment_name: str, segment_type: str, rules: Dict) -> CustomerSegmentEntity:
        """创建客户分群"""
        segment = CustomerSegmentEntity(
            segment_name=segment_name,
            segment_type=segment_type,
            rules=json.dumps(rules)
        )
        self.db.add(segment)
        self.db.commit()
        self.db.refresh(segment)
        logger.info(f"客户分群创建成功：{segment.id} - {segment_name}")
        return segment

    def list_segments(self, active_only: bool = True) -> List[CustomerSegmentEntity]:
        """获取客户分群列表"""
        query = self.db.query(CustomerSegmentEntity)
        if active_only:
            query = query.filter(CustomerSegmentEntity.is_active == True)
        return query.all()


# ====================  营销自动化服务  ====================

class MarketingAutomationService:
    """营销自动化服务 - 自动化营销活动执行"""

    def __init__(self, db: Session):
        self.db = db
        self.segmentation_service = CustomerSegmentationService(db)

    def create_automation(self, config: Dict) -> MarketingAutomationEntity:
        """创建营销自动化活动"""
        automation = MarketingAutomationEntity(
            campaign_name=config["campaign_name"],
            automation_type=config["automation_type"],
            trigger_config=json.dumps(config["trigger_config"]),
            target_segment_id=config.get("target_segment_id"),
            content_config=json.dumps(config["content_config"]),
            start_time=config.get("start_time"),
            end_time=config.get("end_time")
        )
        self.db.add(automation)
        self.db.commit()
        self.db.refresh(automation)
        logger.info(f"营销自动化活动创建成功：{automation.id} - {config['campaign_name']}")
        return automation

    def trigger_automation(self, automation_id: str, user_id: str, event_data: Dict) -> bool:
        """触发营销自动化"""
        automation = self.db.query(MarketingAutomationEntity).filter(
            MarketingAutomationEntity.id == automation_id
        ).first()

        if not automation or not automation.is_active:
            return False

        # 检查目标人群
        if automation.target_segment_id:
            member = self.db.query(CustomerSegmentMemberEntity).filter(
                CustomerSegmentMemberEntity.segment_id == automation.target_segment_id,
                CustomerSegmentMemberEntity.user_id == user_id
            ).first()
            if not member:
                return False

        # 创建触发日志
        trigger_log = AutomationTriggerLogEntity(
            automation_id=automation_id,
            user_id=user_id,
            trigger_event=event_data.get("event_type", "manual"),
            trigger_data=json.dumps(event_data)
        )
        self.db.add(trigger_log)

        # 更新触发次数
        automation.triggered_count += 1

        self.db.commit()

        # 执行营销内容（异步执行）
        self._execute_marketing_content(automation, user_id, trigger_log.id)

        logger.info(f"营销自动化触发：{automation_id} -> 用户 {user_id}")
        return True

    def _execute_marketing_content(self, automation: MarketingAutomationEntity, user_id: str, trigger_log_id: str):
        """执行营销内容"""
        content_config = json.loads(automation.content_config)

        try:
            if content_config.get("type") == "coupon":
                # 发放优惠券
                self._send_coupon(user_id, content_config)
            elif content_config.get("type") == "notification":
                # 发送通知
                self._send_notification(user_id, content_config)
            elif content_config.get("type") == "email":
                # 发送邮件
                self._send_email(user_id, content_config)

            # 更新执行状态
            trigger_log = self.db.query(AutomationTriggerLogEntity).filter(
                AutomationTriggerLogEntity.id == trigger_log_id
            ).first()
            if trigger_log:
                trigger_log.execution_status = "success"
                trigger_log.executed_at = datetime.now()
                self.db.commit()

        except Exception as e:
            logger.error(f"营销内容执行失败：{e}")
            trigger_log = self.db.query(AutomationTriggerLogEntity).filter(
                AutomationTriggerLogEntity.id == trigger_log_id
            ).first()
            if trigger_log:
                trigger_log.execution_status = "failed"
                self.db.commit()

    def _send_coupon(self, user_id: str, config: Dict):
        """发放优惠券"""
        from services.coupon_service import CouponService
        coupon_service = CouponService(self.db)

        template_id = config.get("template_id")
        if template_id:
            result = coupon_service.claim_coupon(user_id, template_id)
            logger.info(f"自动化发券结果：{result}")

    def _send_notification(self, user_id: str, config: Dict):
        """发送通知"""
        # 调用通知服务
        pass

    def _send_email(self, user_id: str, config: Dict):
        """发送邮件"""
        # 调用邮件服务
        pass

    def record_conversion(self, trigger_log_id: str, conversion_type: str, order_id: str, amount: Decimal):
        """记录转化事件"""
        trigger_log = self.db.query(AutomationTriggerLogEntity).filter(
            AutomationTriggerLogEntity.id == trigger_log_id
        ).first()

        if trigger_log:
            trigger_log.converted = True
            trigger_log.converted_at = datetime.now()
            trigger_log.conversion_type = conversion_type
            trigger_log.conversion_order_id = order_id
            trigger_log.conversion_amount = amount

            # 更新自动化活动统计
            automation = self.db.query(MarketingAutomationEntity).filter(
                MarketingAutomationEntity.id == trigger_log.automation_id
            ).first()
            if automation:
                automation.converted_count += 1
                automation.total_revenue += amount

            self.db.commit()
            logger.info(f"营销转化记录：{trigger_log_id} -> {order_id}, 金额 {amount}")

    def get_automation_stats(self, automation_id: str) -> Dict:
        """获取自动化活动统计"""
        automation = self.db.query(MarketingAutomationEntity).filter(
            MarketingAutomationEntity.id == automation_id
        ).first()

        if not automation:
            return {}

        return {
            "campaign_name": automation.campaign_name,
            "triggered_count": automation.triggered_count,
            "converted_count": automation.converted_count,
            "conversion_rate": automation.converted_count / automation.triggered_count if automation.triggered_count > 0 else 0,
            "total_revenue": float(automation.total_revenue)
        }

    def list_automations(self, status: Optional[str] = None) -> List[MarketingAutomationEntity]:
        """获取营销自动化活动列表"""
        query = self.db.query(MarketingAutomationEntity)
        if status:
            query = query.filter(MarketingAutomationEntity.status == status)
        return query.all()


# ====================  营销 ROI 分析服务  ====================

class MarketingROIAnalysisService:
    """营销 ROI 分析服务"""

    def __init__(self, db: Session):
        self.db = db

    def calculate_campaign_roi(self, campaign_id: str, start_date: datetime, end_date: datetime) -> CampaignROIEntity:
        """计算营销活动 ROI"""
        # 获取活动信息
        automation = self.db.query(MarketingAutomationEntity).filter(
            MarketingAutomationEntity.id == campaign_id
        ).first()

        if not automation:
            raise ValueError(f"活动不存在：{campaign_id}")

        # 计算成本
        total_cost = self._calculate_campaign_cost(campaign_id)

        # 计算收益
        trigger_logs = self.db.query(AutomationTriggerLogEntity).filter(
            AutomationTriggerLogEntity.automation_id == campaign_id,
            AutomationTriggerLogEntity.executed_at >= start_date,
            AutomationTriggerLogEntity.executed_at <= end_date,
            AutomationTriggerLogEntity.converted == True
        ).all()

        total_revenue = sum(float(log.conversion_amount or 0) for log in trigger_logs)
        order_count = len(set(log.conversion_order_id for log in trigger_logs if log.conversion_order_id))
        customer_count = len(set(log.user_id for log in trigger_logs))

        # 计算 ROI 指标
        roi = (total_revenue - total_cost) / total_cost if total_cost > 0 else 0
        roas = total_revenue / total_cost if total_cost > 0 else 0
        cpac = total_cost / len(trigger_logs) if trigger_logs else 0

        # 创建或更新 ROI 记录
        roi_record = CampaignROIEntity(
            campaign_id=campaign_id,
            campaign_name=automation.campaign_name,
            campaign_type=automation.automation_type,
            total_cost=total_cost,
            total_revenue=total_revenue,
            order_count=order_count,
            customer_count=customer_count,
            roi=roi,
            roas=roas,
            cpac=cpac,
            start_date=start_date,
            end_date=end_date,
            analysis_status="completed"
        )
        self.db.add(roi_record)
        self.db.commit()
        self.db.refresh(roi_record)

        logger.info(f"ROI 计算完成：{campaign_id}, ROI={roi:.2%}, ROAS={roas:.2f}")
        return roi_record

    def _calculate_campaign_cost(self, campaign_id: str) -> Decimal:
        """计算活动成本"""
        # 简化实现：统计发放的优惠券总价值
        from models.entities import CouponEntity, CouponTemplateEntity

        # 获取活动关联的优惠券模板
        automation = self.db.query(MarketingAutomationEntity).filter(
            MarketingAutomationEntity.id == campaign_id
        ).first()

        if not automation:
            return Decimal(0)

        content_config = json.loads(automation.content_config)
        template_id = content_config.get("template_id")

        if not template_id:
            return Decimal(0)

        template = self.db.query(CouponTemplateEntity).filter(
            CouponTemplateEntity.id == template_id
        ).first()

        if not template:
            return Decimal(0)

        # 成本 = 优惠券面值 × 使用数量
        cost = float(template.value) * template.used_quantity
        return Decimal(cost)

    def generate_daily_stats(self, campaign_id: str, stat_date: datetime) -> CampaignDailyStatsEntity:
        """生成每日统计"""
        # 获取当天数据
        start_of_day = datetime(stat_date.year, stat_date.month, stat_date.day, 0, 0, 0)
        end_of_day = datetime(stat_date.year, stat_date.month, stat_date.day, 23, 59, 59)

        trigger_logs = self.db.query(AutomationTriggerLogEntity).filter(
            AutomationTriggerLogEntity.automation_id == campaign_id,
            AutomationTriggerLogEntity.executed_at >= start_of_day,
            AutomationTriggerLogEntity.executed_at <= end_of_day
        ).all()

        impressions = len(trigger_logs)
        conversions = sum(1 for log in trigger_logs if log.converted)
        revenue = sum(float(log.conversion_amount or 0) for log in trigger_logs if log.converted)

        # 获取活动名称
        automation = self.db.query(MarketingAutomationEntity).filter(
            MarketingAutomationEntity.id == campaign_id
        ).first()

        daily_stats = CampaignDailyStatsEntity(
            campaign_id=campaign_id,
            campaign_name=automation.campaign_name if automation else "",
            stat_date=stat_date,
            impressions=impressions,
            reach=len(set(log.user_id for log in trigger_logs)),
            conversions=conversions,
            conversion_rate=conversions / impressions if impressions > 0 else 0,
            revenue=revenue
        )
        self.db.add(daily_stats)
        self.db.commit()

        return daily_stats

    def get_roi_report(self, campaign_id: str) -> List[CampaignROIEntity]:
        """获取 ROI 分析报告"""
        return self.db.query(CampaignROIEntity).filter(
            CampaignROIEntity.campaign_id == campaign_id
        ).order_by(CampaignROIEntity.end_date.desc()).all()


# ====================  A/B 测试服务  ====================

class ABTestService:
    """A/B 测试服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_ab_test(self, config: Dict) -> ABTestEntity:
        """创建 A/B 测试"""
        ab_test = ABTestEntity(
            test_name=config["test_name"],
            description=config.get("description"),
            goal_type=config["goal_type"],
            goal_metric=config["goal_metric"],
            traffic_percentage=config.get("traffic_percentage", 100),
            sample_size=config.get("sample_size", 1000),
            min_detectable_effect=config.get("min_detectable_effect", 0.05),
            variants_config=json.dumps(config["variants_config"]),
            start_time=config.get("start_time"),
            end_time=config.get("end_time")
        )
        self.db.add(ab_test)
        self.db.commit()
        self.db.refresh(ab_test)

        # 创建变体
        for variant_config in config["variants_config"]:
            variant = ABTestVariantEntity(
                test_id=ab_test.id,
                variant_name=variant_config["name"],
                variant_config=json.dumps(variant_config.get("config", {})),
                traffic_weight=variant_config.get("traffic_weight", 50)
            )
            self.db.add(variant)

        self.db.commit()
        logger.info(f"A/B 测试创建成功：{ab_test.id} - {config['test_name']}")
        return ab_test

    def assign_variant(self, test_id: str, user_id: str) -> str:
        """为用户分配测试变体"""
        # 检查是否已有分配
        existing = self.db.query(ABTestUserAssignmentEntity).filter(
            ABTestUserAssignmentEntity.test_id == test_id,
            ABTestUserAssignmentEntity.user_id == user_id
        ).first()

        if existing:
            return existing.variant_name

        # 获取测试配置
        ab_test = self.db.query(ABTestEntity).filter(
            ABTestEntity.id == test_id
        ).first()

        if not ab_test or ab_test.status != "running":
            return "control"  # 返回对照组

        # 获取变体
        variants = self.db.query(ABTestVariantEntity).filter(
            ABTestVariantEntity.test_id == test_id
        ).all()

        if not variants:
            return "control"

        # 使用一致性哈希分配变体
        variant_name = self._consistent_hash_variant(user_id, variants)

        # 创建分配记录
        assignment = ABTestUserAssignmentEntity(
            test_id=test_id,
            user_id=user_id,
            variant_name=variant_name
        )
        self.db.add(assignment)

        # 更新变体曝光数
        variant = self.db.query(ABTestVariantEntity).filter(
            ABTestVariantEntity.test_id == test_id,
            ABTestVariantEntity.variant_name == variant_name
        ).first()
        if variant:
            variant.impressions += 1
            self.db.commit()

        return variant_name

    def _consistent_hash_variant(self, user_id: str, variants: List[ABTestVariantEntity]) -> str:
        """使用一致性哈希分配变体"""
        # 生成用户哈希
        hash_value = int(hashlib.md5(user_id.encode()).hexdigest(), 16)

        # 计算总权重
        total_weight = sum(v.traffic_weight for v in variants)

        # 按权重分配
        hash_mod = hash_value % total_weight
        cumulative = 0

        for variant in variants:
            cumulative += variant.traffic_weight
            if hash_mod < cumulative:
                return variant.variant_name

        return variants[-1].variant_name

    def record_conversion(self, test_id: str, user_id: str, conversion_value: Decimal = 0):
        """记录转化事件"""
        assignment = self.db.query(ABTestUserAssignmentEntity).filter(
            ABTestUserAssignmentEntity.test_id == test_id,
            ABTestUserAssignmentEntity.user_id == user_id
        ).first()

        if assignment and not assignment.converted:
            assignment.converted = True
            assignment.converted_at = datetime.now()
            assignment.conversion_value = conversion_value

            # 更新变体统计
            variant = self.db.query(ABTestVariantEntity).filter(
                ABTestVariantEntity.test_id == test_id,
                ABTestVariantEntity.variant_name == assignment.variant_name
            ).first()
            if variant:
                variant.conversions += 1
                variant.revenue += conversion_value
                variant.conversion_rate = variant.conversions / variant.impressions if variant.impressions > 0 else 0

            self.db.commit()
            logger.info(f"A/B 测试转化记录：{test_id} -> 用户 {user_id}, 变体 {assignment.variant_name}")

    def analyze_test(self, test_id: str) -> Dict:
        """分析 A/B 测试结果"""
        ab_test = self.db.query(ABTestEntity).filter(
            ABTestEntity.id == test_id
        ).first()

        if not ab_test:
            return {}

        variants = self.db.query(ABTestVariantEntity).filter(
            ABTestVariantEntity.test_id == test_id
        ).all()

        results = []
        for variant in variants:
            results.append({
                "variant_name": variant.variant_name,
                "impressions": variant.impressions,
                "conversions": variant.conversions,
                "conversion_rate": float(variant.conversion_rate),
                "revenue": float(variant.revenue)
            })

        # 简单胜者判定（实际需要统计检验）
        if len(results) >= 2:
            winner = max(results, key=lambda x: x["conversion_rate"])
            baseline = min(results, key=lambda x: x["conversion_rate"])
            lift = (winner["conversion_rate"] - baseline["conversion_rate"]) / baseline["conversion_rate"] if baseline["conversion_rate"] > 0 else 0

            return {
                "test_name": ab_test.test_name,
                "status": ab_test.status,
                "variants": results,
                "winner": winner["variant_name"],
                "lift": lift
            }

        return {
            "test_name": ab_test.test_name,
            "status": ab_test.status,
            "variants": results
        }

    def start_test(self, test_id: str):
        """开始 A/B 测试"""
        ab_test = self.db.query(ABTestEntity).filter(
            ABTestEntity.id == test_id
        ).first()

        if ab_test:
            ab_test.status = "running"
            ab_test.start_time = datetime.now()
            self.db.commit()
            logger.info(f"A/B 测试开始：{test_id}")

    def conclude_test(self, test_id: str, winner_variant: str):
        """结束 A/B 测试"""
        ab_test = self.db.query(ABTestEntity).filter(
            ABTestEntity.id == test_id
        ).first()

        if ab_test:
            ab_test.status = "concluded"
            ab_test.end_time = datetime.now()
            ab_test.winner_variant = winner_variant
            self.db.commit()
            logger.info(f"A/B 测试结束：{test_id}, 胜者：{winner_variant}")


# ====================  智能优惠券服务  ====================

class SmartCouponService:
    """智能优惠券服务 - 千人千券策略"""

    def __init__(self, db: Session):
        self.db = db
        self.segmentation_service = CustomerSegmentationService(db)

    def create_strategy(self, config: Dict) -> SmartCouponStrategyEntity:
        """创建智能优惠券策略"""
        strategy = SmartCouponStrategyEntity(
            strategy_name=config["strategy_name"],
            description=config.get("description"),
            target_segment_id=config.get("target_segment_id"),
            coupon_rules=json.dumps(config["coupon_rules"]),
            trigger_event=config.get("trigger_event"),
            max_coupons_per_user=config.get("max_coupons_per_user", 1),
            daily_limit=config.get("daily_limit", 1000)
        )
        self.db.add(strategy)
        self.db.commit()
        self.db.refresh(strategy)
        logger.info(f"智能优惠券策略创建成功：{strategy.id} - {config['strategy_name']}")
        return strategy

    def generate_coupon_for_user(self, user_id: str, strategy_id: str) -> Optional[Dict]:
        """为用户生成个性化优惠券"""
        strategy = self.db.query(SmartCouponStrategyEntity).filter(
            SmartCouponStrategyEntity.id == strategy_id
        ).first()

        if not strategy or not strategy.is_active:
            return None

        # 检查目标人群
        if strategy.target_segment_id:
            member = self.db.query(CustomerSegmentMemberEntity).filter(
                CustomerSegmentMemberEntity.segment_id == strategy.target_segment_id,
                CustomerSegmentMemberEntity.user_id == user_id
            ).first()
            if not member:
                return None

        # 获取用户优惠券偏好
        preference = self._get_user_preference(user_id)

        # 根据策略和偏好生成优惠券
        coupon_rules = json.loads(strategy.coupon_rules)
        coupon_config = self._personalize_coupon(coupon_rules, preference)

        # 更新策略统计
        strategy.total_issued += 1
        self.db.commit()

        logger.info(f"为用户 {user_id} 生成个性化优惠券：{coupon_config}")
        return coupon_config

    def _get_user_preference(self, user_id: str) -> Optional[UserCouponPreferenceEntity]:
        """获取用户优惠券偏好"""
        preference = self.db.query(UserCouponPreferenceEntity).filter(
            UserCouponPreferenceEntity.user_id == user_id
        ).first()

        if not preference:
            # 创建默认偏好
            preference = UserCouponPreferenceEntity(user_id=user_id)
            self.db.add(preference)
            self.db.commit()

        return preference

    def _personalize_coupon(self, coupon_rules: Dict, preference: UserCouponPreferenceEntity) -> Dict:
        """生成个性化优惠券配置"""
        # 根据用户偏好调整优惠券参数
        coupon_type = preference.preferred_coupon_type or coupon_rules.get("type", "fixed")

        # 在规则范围内随机生成优惠券值
        value_range = coupon_rules.get("value_range", [10, 50])
        discount_value = random.uniform(value_range[0], value_range[1])

        return {
            "type": coupon_type,
            "value": round(discount_value, 2),
            "min_purchase": coupon_rules.get("min_purchase", 0),
            "valid_days": coupon_rules.get("valid_days", 7)
        }

    def record_coupon_usage(self, user_id: str, coupon_id: str, order_amount: Decimal):
        """记录优惠券使用"""
        # 更新用户偏好统计
        preference = self._get_user_preference(user_id)
        if preference:
            preference.total_coupons_used += 1
            preference.usage_rate = preference.total_coupons_used / preference.total_coupons_received if preference.total_coupons_received > 0 else 0
            self.db.commit()

    def update_user_preference(self, user_id: str, preference_data: Dict):
        """更新用户优惠券偏好"""
        preference = self._get_user_preference(user_id)
        if preference:
            for key, value in preference_data.items():
                if hasattr(preference, key):
                    setattr(preference, key, value)
            self.db.commit()

    def get_strategy_stats(self, strategy_id: str) -> Dict:
        """获取策略统计"""
        strategy = self.db.query(SmartCouponStrategyEntity).filter(
            SmartCouponStrategyEntity.id == strategy_id
        ).first()

        if not strategy:
            return {}

        return {
            "strategy_name": strategy.strategy_name,
            "total_issued": strategy.total_issued,
            "total_used": strategy.total_used,
            "usage_rate": strategy.total_used / strategy.total_issued if strategy.total_issued > 0 else 0,
            "total_revenue": float(strategy.total_revenue)
        }


# ====================  营销事件追踪服务  ====================

class MarketingEventService:
    """营销事件追踪服务"""

    def __init__(self, db: Session):
        self.db = db

    def track_event(self, user_id: str, event_type: str, event_data: Dict,
                   campaign_id: Optional[str] = None, coupon_id: Optional[str] = None,
                   order_id: Optional[str] = None):
        """追踪营销事件"""
        event = MarketingEventEntity(
            user_id=user_id,
            event_type=event_type,
            event_data=json.dumps(event_data),
            campaign_id=campaign_id,
            coupon_id=coupon_id,
            order_id=order_id
        )
        self.db.add(event)
        self.db.commit()
        logger.debug(f"营销事件追踪：{user_id} - {event_type}")

    def get_user_events(self, user_id: str, event_type: Optional[str] = None,
                       limit: int = 100) -> List[MarketingEventEntity]:
        """获取用户营销事件"""
        query = self.db.query(MarketingEventEntity).filter(
            MarketingEventEntity.user_id == user_id
        )
        if event_type:
            query = query.filter(MarketingEventEntity.event_type == event_type)
        return query.order_by(MarketingEventEntity.event_time.desc()).limit(limit).all()

    def get_campaign_events(self, campaign_id: str, limit: int = 1000) -> List[MarketingEventEntity]:
        """获取活动相关事件"""
        return self.db.query(MarketingEventEntity).filter(
            MarketingEventEntity.campaign_id == campaign_id
        ).order_by(MarketingEventEntity.event_time.desc()).limit(limit).all()
