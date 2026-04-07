"""
P3 用户增长与运营工具 - 基础数据初始化脚本

用于初始化：
1. 邀请奖励规则
2. 任务定义（新手任务、日常任务）
3. 会员等级配置
4. 运营活动模板
"""

from sqlalchemy.orm import Session
from config.database import SessionLocal, engine
from models.p3_entities import (
    InviteRewardRuleEntity,
    TaskDefinitionEntity, TaskType, TaskRewardType,
    MemberLevelConfigEntity, MemberLevel,
    CampaignTemplateEntity, CampaignType
)
from datetime import datetime, timedelta
import json


def init_invite_reward_rules(db: Session):
    """初始化邀请奖励规则"""
    rule = InviteRewardRuleEntity(
        id="rule_invite_001",
        rule_name="standard_invite",
        inviter_cash_reward=10.0,
        invitee_cash_reward=5.0,
        inviter_points_reward=100,
        invitee_points_reward=50,
        min_order_amount=20.0,
        max_reward_per_day=500.0,
        is_active=True
    )
    db.add(rule)
    db.commit()
    print("✓ 邀请奖励规则初始化完成")


def init_task_definitions(db: Session):
    """初始化任务定义"""
    tasks = [
        # 新手任务
        TaskDefinitionEntity(
            id="task_newbie_001",
            task_code="NEWBIE_COMPLETE_PROFILE",
            task_name="完善个人资料",
            task_type=TaskType.NEWBIE,
            description="完善您的个人资料，包括头像、昵称、收货地址",
            icon_url="/icons/task_profile.png",
            target_type="profile_complete",
            target_value=1,
            reward_type=TaskRewardType.POINTS,
            reward_value=200,
            reward_extra=json.dumps({"coupon_id": "coupon_newbie_001"}),
            user_limit=1,
            is_active=True,
            sort_order=1
        ),
        TaskDefinitionEntity(
            id="task_newbie_002",
            task_code="NEWBIE_FIRST_ORDER",
            task_name="完成首单",
            task_type=TaskType.NEWBIE,
            description="完成您的首笔订单",
            icon_url="/icons/task_first_order.png",
            target_type="order_count",
            target_value=1,
            reward_type=TaskRewardType.POINTS,
            reward_value=500,
            reward_extra=json.dumps({"coupon_id": "coupon_newbie_002"}),
            user_limit=1,
            is_active=True,
            sort_order=2
        ),
        TaskDefinitionEntity(
            id="task_newbie_003",
            task_code="NEWBIE_INVITE_FRIEND",
            task_name="邀请好友",
            task_type=TaskType.NEWBIE,
            description="邀请一位好友注册",
            icon_url="/icons/task_invite.png",
            target_type="invite_count",
            target_value=1,
            reward_type=TaskRewardType.CASH,
            reward_value=10,
            reward_extra=None,
            user_limit=10,
            is_active=True,
            sort_order=3
        ),
        # 日常任务
        TaskDefinitionEntity(
            id="task_daily_001",
            task_code="DAILY_SIGNIN",
            task_name="每日签到",
            task_type=TaskType.DAILY,
            description="每日签到领取积分",
            icon_url="/icons/task_signin.png",
            target_type="signin_count",
            target_value=1,
            reward_type=TaskRewardType.POINTS,
            reward_value=10,
            reward_extra=json.dumps({"continuous_bonus": True}),
            user_limit=1,
            is_active=True,
            sort_order=10
        ),
        TaskDefinitionEntity(
            id="task_daily_002",
            task_code="DAILY_VIEW_PRODUCT",
            task_name="浏览商品",
            task_type=TaskType.DAILY,
            description="浏览 5 个商品",
            icon_url="/icons/task_view.png",
            target_type="view_count",
            target_value=5,
            reward_type=TaskRewardType.POINTS,
            reward_value=20,
            reward_extra=None,
            user_limit=1,
            is_active=True,
            sort_order=11
        ),
        TaskDefinitionEntity(
            id="task_daily_003",
            task_code="DAILY_SHARE",
            task_name="分享商品",
            task_type=TaskType.DAILY,
            description="分享商品给好友",
            icon_url="/icons/task_share.png",
            target_type="share_count",
            target_value=1,
            reward_type=TaskRewardType.POINTS,
            reward_value=30,
            reward_extra=None,
            user_limit=3,
            is_active=True,
            sort_order=12
        ),
        # 每周任务
        TaskDefinitionEntity(
            id="task_weekly_001",
            task_code="WEEKLY_ORDER",
            task_name="每周下单",
            task_type=TaskType.WEEKLY,
            description="每周完成 3 笔订单",
            icon_url="/icons/task_order.png",
            target_type="order_count",
            target_value=3,
            reward_type=TaskRewardType.POINTS,
            reward_value=100,
            reward_extra=json.dumps({"coupon_id": "coupon_weekly_001"}),
            user_limit=1,
            is_active=True,
            sort_order=20
        ),
        # 成长任务
        TaskDefinitionEntity(
            id="task_growth_001",
            task_code="GROWTH_TOTAL_ORDERS_10",
            task_name="累计下单 10 笔",
            task_type=TaskType.GROWTH,
            description="累计完成 10 笔订单",
            icon_url="/icons/task_growth.png",
            target_type="total_order_count",
            target_value=10,
            reward_type=TaskRewardType.GROWTH_VALUE,
            reward_value=100,
            reward_extra=None,
            user_limit=1,
            is_active=True,
            sort_order=30
        ),
        TaskDefinitionEntity(
            id="task_growth_002",
            task_code="GROWTH_TOTAL_AMOUNT_1000",
            task_name="累计消费 1000 元",
            task_type=TaskType.GROWTH,
            description="累计消费金额达到 1000 元",
            icon_url="/icons/task_growth.png",
            target_type="total_amount",
            target_value=1000,
            reward_type=TaskRewardType.GROWTH_VALUE,
            reward_value=200,
            reward_extra=None,
            user_limit=1,
            is_active=True,
            sort_order=31
        ),
    ]

    for task in tasks:
        db.add(task)

    db.commit()
    print(f"✓ 任务定义初始化完成（共{len(tasks)}个任务）")


def init_member_level_configs(db: Session):
    """初始化会员等级配置"""
    levels = [
        MemberLevelConfigEntity(
            id="level_normal",
            level=MemberLevel.NORMAL,
            level_name="普通会员",
            min_growth_value=0,
            min_total_orders=0,
            min_total_amount=0,
            benefits=json.dumps({
                "discount_rate": 1.0,
                "free_shipping_threshold": 99,
                "customer_service": "standard"
            }),
            benefit_codes="discount_rate,free_shipping_threshold,customer_service",
            min_maintain_growth_value=0,
            review_period_days=0,
            is_active=True,
            sort_order=1
        ),
        MemberLevelConfigEntity(
            id="level_silver",
            level=MemberLevel.SILVER,
            level_name="白银会员",
            min_growth_value=500,
            min_total_orders=5,
            min_total_amount=500,
            benefits=json.dumps({
                "discount_rate": 0.98,
                "free_shipping_threshold": 59,
                "customer_service": "priority",
                "birthday_coupon": 20,
                "monthly_coupons": 3
            }),
            benefit_codes="discount_rate,free_shipping_threshold,customer_service,birthday_coupon,monthly_coupons",
            min_maintain_growth_value=300,
            review_period_days=90,
            is_active=True,
            sort_order=2
        ),
        MemberLevelConfigEntity(
            id="level_gold",
            level=MemberLevel.GOLD,
            level_name="黄金会员",
            min_growth_value=2000,
            min_total_orders=20,
            min_total_amount=2000,
            benefits=json.dumps({
                "discount_rate": 0.95,
                "free_shipping_threshold": 39,
                "customer_service": "vip",
                "birthday_coupon": 50,
                "monthly_coupons": 5,
                "exclusive_products": True,
                "early_access": True
            }),
            benefit_codes="discount_rate,free_shipping_threshold,customer_service,birthday_coupon,monthly_coupons,exclusive_products,early_access",
            min_maintain_growth_value=1500,
            review_period_days=90,
            is_active=True,
            sort_order=3
        ),
        MemberLevelConfigEntity(
            id="level_platinum",
            level=MemberLevel.PLATINUM,
            level_name="铂金会员",
            min_growth_value=5000,
            min_total_orders=50,
            min_total_amount=5000,
            benefits=json.dumps({
                "discount_rate": 0.92,
                "free_shipping_threshold": 0,
                "customer_service": "dedicated",
                "birthday_coupon": 100,
                "monthly_coupons": 10,
                "exclusive_products": True,
                "early_access": True,
                "free_returns": True,
                "price_protection": True
            }),
            benefit_codes="discount_rate,free_shipping_threshold,customer_service,birthday_coupon,monthly_coupons,exclusive_products,early_access,free_returns,price_protection",
            min_maintain_growth_value=4000,
            review_period_days=90,
            is_active=True,
            sort_order=4
        ),
        MemberLevelConfigEntity(
            id="level_diamond",
            level=MemberLevel.DIAMOND,
            level_name="钻石会员",
            min_growth_value=10000,
            min_total_orders=100,
            min_total_amount=10000,
            benefits=json.dumps({
                "discount_rate": 0.90,
                "free_shipping_threshold": 0,
                "customer_service": "black_card",
                "birthday_coupon": 200,
                "monthly_coupons": 20,
                "exclusive_products": True,
                "early_access": True,
                "free_returns": True,
                "price_protection": True,
                "personal_shopper": True,
                "offline_events": True
            }),
            benefit_codes="discount_rate,free_shipping_threshold,customer_service,birthday_coupon,monthly_coupons,exclusive_products,early_access,free_returns,price_protection,personal_shopper,offline_events",
            min_maintain_growth_value=8000,
            review_period_days=90,
            is_active=True,
            sort_order=5
        ),
    ]

    for level in levels:
        db.add(level)

    db.commit()
    print(f"✓ 会员等级配置初始化完成（共{len(levels)}个等级）")


def init_campaign_templates(db: Session):
    """初始化运营活动模板"""
    templates = [
        CampaignTemplateEntity(
            id="template_flash_sale",
            template_name="限时秒杀模板",
            campaign_type=CampaignType.FLASH_SALE,
            config=json.dumps({
                "max_participants": 1000,
                "discount_rate": 0.5,
                "max_discount_amount": 50,
                "time_slots": ["10:00", "14:00", "20:00"],
                "slot_duration_minutes": 30
            }),
            rules=json.dumps({
                "min_order_amount": 0,
                "max_purchase_per_user": 2,
                "refund_policy": "no_refund"
            }),
            description="限时秒杀活动模板，支持多个时间段，自动补货",
            tags="秒杀，限时，特价",
            is_active=True
        ),
        CampaignTemplateEntity(
            id="template_group_buy",
            template_name="拼团活动模板",
            campaign_type=CampaignType.GROUP_BUY,
            config=json.dumps({
                "min_group_size": 3,
                "max_group_size": 10,
                "group_discount": 0.15,
                "auto_group": True,
                "group_timeout_hours": 24
            }),
            rules=json.dumps({
                "min_order_amount": 0,
                "max_purchase_per_user": 5,
                "refund_before_ship": True
            }),
            description="拼团活动模板，支持自动成团和手动成团",
            tags="拼团，团购，社交",
            is_active=True
        ),
        CampaignTemplateEntity(
            id="template_coupon_rain",
            template_name="优惠券雨模板",
            campaign_type=CampaignType.COUPON_RAIN,
            config=json.dumps({
                "total_coupons": 5000,
                "coupon_values": [5, 10, 20, 50],
                "drop_interval_seconds": 60,
                "drop_duration_minutes": 30
            }),
            rules=json.dumps({
                "min_order_amount": 50,
                "valid_days": 7,
                "stackable": False
            }),
            description="优惠券雨活动模板，定时掉落优惠券",
            tags="优惠券，互动，营销",
            is_active=True
        ),
        CampaignTemplateEntity(
            id="template_new_user_special",
            template_name="新人专享模板",
            campaign_type=CampaignType.NEW_USER_SPECIAL,
            config=json.dumps({
                "new_user_days": 7,
                "exclusive_products": [],
                "first_order_discount": 0.2,
                "new_user_coupon_package": True
            }),
            rules=json.dumps({
                "only_first_order": True,
                "max_discount_amount": 100,
                "cannot_stack": True
            }),
            description="新人专享活动模板，针对新注册用户的专属优惠",
            tags="新人，首单，优惠",
            is_active=True
        ),
    ]

    for template in templates:
        db.add(template)

    db.commit()
    print(f"✓ 运营活动模板初始化完成（共{len(templates)}个模板）")


def main():
    """主函数"""
    print("=" * 50)
    print("P3 用户增长与运营工具 - 基础数据初始化")
    print("=" * 50)

    db = SessionLocal()

    try:
        # 检查是否已初始化
        existing_rule = db.query(InviteRewardRuleEntity).first()
        if existing_rule:
            print("⚠ 检测到已存在的数据，跳过初始化")
            return

        print("\n开始初始化基础数据...")

        # 初始化各项数据
        init_invite_reward_rules(db)
        init_task_definitions(db)
        init_member_level_configs(db)
        init_campaign_templates(db)

        print("\n" + "=" * 50)
        print("✓ P3 基础数据初始化完成！")
        print("=" * 50)

    except Exception as e:
        db.rollback()
        print(f"✗ 初始化失败：{e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
