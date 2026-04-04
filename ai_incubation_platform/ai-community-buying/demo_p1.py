#!/usr/bin/env python3
"""
P1阶段功能演示脚本
演示数据持久化、智能推荐、动态定价、通知体系功能
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.database import Base, get_db
from models.product import ProductCreate, GroupBuyCreate, GroupBuyJoinRequest
from models.entities import ProductEntity, GroupBuyEntity, OrderEntity, NotificationEntity, ProductRecommendationEntity
from services.groupbuy_service_db import GroupBuyServiceDB
from services.recommendation_service import recommendation_service
from services.notification_service import notification_service
from datetime import datetime, timedelta
from sqlalchemy import Enum as SAEnum

# 创建SQLite内存数据库用于演示
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# SQLite不支持原生Enum类型，需要特殊处理
for column in ProductEntity.__table__.columns:
    if isinstance(column.type, SAEnum):
        column.type.create_constraint = False
for column in GroupBuyEntity.__table__.columns:
    if isinstance(column.type, SAEnum):
        column.type.create_constraint = False
for column in OrderEntity.__table__.columns:
    if isinstance(column.type, SAEnum):
        column.type.create_constraint = False

# 创建表
Base.metadata.create_all(bind=engine)

def get_test_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def demo_p1_features():
    print("=" * 60)
    print("🎯 AI 社区团购平台 - P1阶段功能演示")
    print("=" * 60)

    db = next(get_test_db())
    gb_service = GroupBuyServiceDB(db)

    # 1. 数据持久化演示
    print("\n1. 数据持久化功能演示")
    print("-" * 40)

    # 创建多个商品
    products_data = [
        ProductCreate(
            name="新鲜草莓 (500g)",
            description="当季新鲜奶油草莓，香甜多汁，产地直供",
            price=29.9,
            original_price=49.9,
            stock=100,
            min_group_size=3,
            max_group_size=5
        ),
        ProductCreate(
            name="进口车厘子 (1kg)",
            description="JJ级车厘子，脆甜多汁",
            price=89.9,
            original_price=129.9,
            stock=50,
            min_group_size=2,
            max_group_size=4
        ),
        ProductCreate(
            name="有机蔬菜礼盒",
            description="多种有机蔬菜组合，健康营养",
            price=59.9,
            original_price=89.9,
            stock=30,
            min_group_size=2,
            max_group_size=6
        ),
        ProductCreate(
            name="鲜牛奶 (1L*6盒)",
            description="牧场直供鲜牛奶，无添加",
            price=49.9,
            original_price=69.9,
            stock=80,
            min_group_size=3,
            max_group_size=10
        )
    ]

    created_products = []
    for pd in products_data:
        product = gb_service.create_product(pd)
        created_products.append(product)
        print(f"✅ 创建商品: {product.name}, ID: {product.id}, 库存: {product.stock}")

    # 2. 智能推荐演示
    print("\n2. 智能推荐功能演示")
    print("-" * 40)

    community_id = "community_001"
    recommendations = recommendation_service.get_recommended_products(db, community_id, limit=3)

    print(f"📊 社区 {community_id} 的推荐商品:")
    for i, rec in enumerate(recommendations, 1):
        product = rec["product"]
        print(f"   {i}. {product.name}")
        print(f"      推荐分数: {rec['score']}/100")
        print(f"      推荐理由: {rec['reason']}")
        print(f"      价格: ¥{product.price} (原价: ¥{product.original_price})")

    # 3. 动态定价演示
    print("\n3. 动态定价功能演示")
    print("-" * 40)

    test_product = created_products[0]  # 草莓
    print(f"测试商品: {test_product.name}, 基础价格: ¥{test_product.price}")

    # 不同成团进度的价格
    for progress in [1, 2, 3]:  # 1/3, 2/3, 3/3
        dynamic_price = recommendation_service.calculate_dynamic_price(
            test_product, progress, 3
        )
        discount = round(dynamic_price / test_product.price * 10, 1)
        print(f"   进度 {progress}/3: 价格 ¥{dynamic_price}, {discount}折")

    # 4. 通知体系演示
    print("\n4. 通知体系功能演示")
    print("-" * 40)

    # 创建一个低库存商品触发预警
    low_stock_product = ProductCreate(
        name="限量榴莲",
        description="猫山王榴莲，限量供应",
        price=199.9,
        original_price=299.9,
        stock=5,  # 低于预警阈值10
        min_group_size=2,
        max_group_size=2
    )
    low_product = gb_service.create_product(low_stock_product)
    print(f"✅ 创建低库存商品: {low_product.name}, 库存: {low_product.stock}")

    # 触发库存预警
    alert_count = notification_service.check_and_send_stock_alerts(db)
    print(f"📢 发送库存预警: {alert_count} 条")

    # 查看管理员通知
    admin_notifications = notification_service.get_user_notifications(db, "admin")
    print(f"📋 管理员收到的通知: {len(admin_notifications)} 条")
    for notif in admin_notifications:
        if notif.type == "stock_alert":
            print(f"   🚨 {notif.title}: {notif.content}")

    # 5. 团购流程与进度通知
    print("\n5. 团购流程与进度通知")
    print("-" * 40)

    # 发起团购
    organizer_id = "user_001"
    group_data = GroupBuyCreate(
        product_id=test_product.id,
        organizer_id=organizer_id,
        target_size=3,
        duration_hours=24
    )
    group_buy = gb_service.create_group_buy(group_data)
    print(f"✅ 团购创建成功: {group_buy.id}, 商品: {test_product.name}")

    # 用户1加入（达到50%进度）
    user2_id = "user_002"
    group_buy, _ = gb_service.join_group_buy(group_buy.id, user2_id)
    print(f"✅ 用户 {user2_id} 加入，当前人数: {group_buy.current_size}/{group_buy.target_size}")

    # 检查进度通知
    notifications_user1 = notification_service.get_user_notifications(db, organizer_id)
    progress_notifs = [n for n in notifications_user1 if n.type == "group_progress"]
    print(f"📢 进度通知: 发送了 {len(progress_notifs)} 条进度通知")

    # 用户2加入（达到100%，成团）
    user3_id = "user_003"
    group_buy, _ = gb_service.join_group_buy(group_buy.id, user3_id)
    print(f"✅ 用户 {user3_id} 加入，当前人数: {group_buy.current_size}/{group_buy.target_size}")
    print(f"   团购状态: {group_buy.status}")

    # 检查成团通知
    notifications = notification_service.get_user_notifications(db, organizer_id)
    success_notifs = [n for n in notifications if n.type == "group_success"]
    print(f"🎉 成团通知: 发送了 {len(success_notifs)} 条成团成功通知")
    if success_notifs:
        print(f"   通知内容: {success_notifs[0].content}")

    # 查看生成的订单
    orders = gb_service.get_group_orders(group_buy.id)
    print(f"\n✅ 自动生成订单: {len(orders)} 个")
    for i, order in enumerate(orders, 1):
        print(f"   订单{i}: 用户={order.user_id}, 金额=¥{order.total_amount}, 状态={order.status}")

    # 6. 验证数据持久化
    print("\n6. 验证数据持久化")
    print("-" * 40)

    # 重新查询商品
    product_from_db = gb_service.get_product(test_product.id)
    print(f"🔍 从数据库查询商品: {product_from_db.name}")
    print(f"   库存: {product_from_db.stock}, 已售: {product_from_db.sold_stock}, 锁定: {product_from_db.locked_stock}")

    # 查询团购记录
    groups = gb_service.list_group_buys_by_status("success")
    print(f"🔍 成功的团购记录: {len(groups)} 个")

    print("\n" + "=" * 60)
    print("✅ P1阶段功能演示完成！")
    print("=" * 60)
    print("\n📋 已实现的P1阶段功能:")
    print("  ✅ 数据持久化：SQLAlchemy ORM集成，数据存储到数据库")
    print("  ✅ 智能选品：基于销量、成团率、利润率的综合推荐算法")
    print("  ✅ 动态定价：根据成团进度、库存、销量动态调整价格")
    print("  ✅ 通知体系：库存预警、团购进度、成团结果通知")
    print("  ✅ API兼容：原有接口保持不变，新增推荐和通知API")

    # 清理测试数据库
    os.remove("./test.db")

if __name__ == "__main__":
    demo_p1_features()
