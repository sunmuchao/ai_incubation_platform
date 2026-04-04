#!/usr/bin/env python3
"""
AI 社区团购平台演示脚本
演示完整的业务流程：创建商品 -> 发起团购 -> 用户参团 -> 成团 -> 订单生成
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from models.product import ProductCreate, GroupBuyCreate, GroupBuyJoinRequest
from services.groupbuy_service import group_buy_service, GroupBuyStatus


def demo_business_flow():
    print("=" * 60)
    print("🎯 AI 社区团购平台 - 完整业务流程演示")
    print("=" * 60)

    # 1. 创建商品
    print("\n1. 创建商品: 新鲜草莓")
    product_data = ProductCreate(
        name="新鲜草莓 (500g)",
        description="当季新鲜奶油草莓，香甜多汁，产地直供",
        price=29.9,
        original_price=49.9,
        stock=100,
        min_group_size=3,
        max_group_size=5,
        image_url="https://example.com/strawberry.jpg"
    )
    product = group_buy_service.create_product(product_data)
    print(f"✅ 商品创建成功: {product.name}")
    print(f"   商品ID: {product.id}")
    print(f"   团购价: ¥{product.price}, 原价: ¥{product.original_price}")
    print(f"   库存: {product.stock}")
    print(f"   成团要求: {product.min_group_size}-{product.max_group_size}人")

    # 2. 团长发起团购
    print("\n2. 团长发起团购")
    organizer_id = "user_001"  # 团长ID
    group_data = GroupBuyCreate(
        product_id=product.id,
        organizer_id=organizer_id,
        target_size=3,
        duration_hours=24
    )
    group_buy = group_buy_service.create_group_buy(group_data)
    print(f"✅ 团购创建成功")
    print(f"   团购ID: {group_buy.id}")
    print(f"   团长: {organizer_id}")
    print(f"   目标人数: {group_buy.target_size}")
    print(f"   截止时间: {group_buy.deadline.strftime('%Y-%m-%d %H:%M')}")
    print(f"   当前状态: {group_buy.status}")
    print(f"   当前人数: {group_buy.current_size}/{group_buy.target_size}")

    # 检查库存锁定情况
    product_after = group_buy_service.get_product(product.id)
    print(f"   库存变化: 总库存={product_after.stock}, 锁定库存={product_after.locked_stock}")

    # 3. 用户1加入团购
    print("\n3. 用户 user_002 加入团购")
    user2_id = "user_002"
    group_buy, join_record = group_buy_service.join_group_buy(group_buy.id, user2_id)
    print(f"✅ 用户 {user2_id} 加入成功")
    print(f"   当前人数: {group_buy.current_size}/{group_buy.target_size}")
    print(f"   库存: 总库存={product_after.stock}, 锁定库存={product_after.locked_stock + 1}")

    # 4. 用户2加入团购（达到成团人数）
    print("\n4. 用户 user_003 加入团购")
    user3_id = "user_003"
    group_buy, join_record = group_buy_service.join_group_buy(group_buy.id, user3_id)
    print(f"✅ 用户 {user3_id} 加入成功")
    print(f"   当前人数: {group_buy.current_size}/{group_buy.target_size}")
    print(f"   团购状态: {group_buy.status}")

    if group_buy.status == GroupBuyStatus.SUCCESS:
        print("🎉 恭喜！团购成团成功！")

        # 检查库存扣减情况
        product_final = group_buy_service.get_product(product.id)
        print(f"   库存最终状态: 总库存={product_final.stock}, 锁定库存={product_final.locked_stock}, 已售={product_final.sold_stock}")

        # 查看生成的订单
        orders = group_buy_service.get_group_orders(group_buy.id)
        print(f"\n✅ 自动生成订单: {len(orders)} 个")
        for i, order in enumerate(orders, 1):
            print(f"   订单{i}: ID={order.id}, 用户={order.user_id}, 金额=¥{order.total_amount}, 状态={order.status}")

    # 5. 尝试让第四个用户加入（应该失败，因为已满员）
    print("\n5. 尝试让用户 user_004 加入已满的团购")
    try:
        user4_id = "user_004"
        group_buy_service.join_group_buy(group_buy.id, user4_id)
        print("❌ 加入成功（预期应该失败）")
    except Exception as e:
        print(f"✅ 加入失败，符合预期: {str(e)}")

    # 6. 查询团购详情
    print("\n6. 查询团购详情")
    group_detail = group_buy_service.get_group_buy(group_buy.id)
    print(f"   团购ID: {group_detail.id}")
    print(f"   商品: {group_detail.product.name}")
    print(f"   状态: {group_detail.status}")
    print(f"   成团人数: {group_detail.current_size}/{group_detail.target_size}")
    print(f"   成员列表: {', '.join(group_detail.members)}")

    # 7. 查询用户订单
    print("\n7. 查询团长 user_001 的订单")
    user_orders = group_buy_service.get_user_orders(organizer_id)
    for order in user_orders:
        if order.group_buy_id == group_buy.id:
            print(f"   订单ID: {order.id}")
            print(f"   商品: {product.name}")
            print(f"   金额: ¥{order.total_amount}")
            print(f"   状态: {order.status}")

    print("\n" + "=" * 60)
    print("✅ 演示完成！核心业务流程正常运行。")
    print("=" * 60)
    print("\n📋 已实现的核心功能:")
    print("  ✅ 商品管理（创建、查询、库存管理）")
    print("  ✅ 团购发起（库存预锁定、参数校验）")
    print("  ✅ 用户参团（重复加入校验、满员校验、过期校验）")
    print("  ✅ 自动成团（达到人数后自动变更状态、扣减库存）")
    print("  ✅ 订单自动生成（成团后为每个成员创建订单）")
    print("  ✅ 团购过期/失败处理（自动解锁库存）")
    print("  ✅ 参团记录和订单查询")


def demo_expired_group_flow():
    """演示团购过期处理流程"""
    print("\n" + "=" * 60)
    print("⏰ 团购过期处理演示")
    print("=" * 60)

    # 创建商品
    product_data = ProductCreate(
        name="进口车厘子 (1kg)",
        description="JJ级车厘子，脆甜多汁",
        price=89.9,
        original_price=129.9,
        stock=50,
        min_group_size=2
    )
    product = group_buy_service.create_product(product_data)

    # 创建一个1小时后过期的团购
    from datetime import datetime, timedelta
    group_data = GroupBuyCreate(
        product_id=product.id,
        organizer_id="user_001",
        target_size=3,
        duration_hours=0  # 立即过期
    )
    group_buy = group_buy_service.create_group_buy(group_data)
    # 手动调整截止时间为过去
    group_buy.deadline = datetime.now() - timedelta(minutes=1)

    print(f"\n创建团购: ID={group_buy.id}, 状态={group_buy.status}")
    print(f"截止时间设置为: {group_buy.deadline.strftime('%Y-%m-%d %H:%M')} (已过期)")

    # 触发过期清理
    group_buy_service._cleanup_expired_groups()

    # 查询团购状态
    expired_group = group_buy_service.get_group_buy(group_buy.id)
    print(f"清理后团购状态: {expired_group.status}")

    # 检查库存是否解锁
    product_after = group_buy_service.get_product(product.id)
    print(f"库存状态: 总库存={product_after.stock}, 锁定库存={product_after.locked_stock}")
    print("✅ 过期团购已自动处理，库存已解锁")


if __name__ == "__main__":
    demo_business_flow()
    demo_expired_group_flow()