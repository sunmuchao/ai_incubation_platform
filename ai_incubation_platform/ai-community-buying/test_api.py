#!/usr/bin/env python3
"""
API 测试脚本
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8005/api"

def test_api_flow():
    """测试完整API流程"""
    print("=" * 60)
    print("🧪 API 功能测试")
    print("=" * 60)

    # 1. 测试创建商品
    print("\n1. 测试创建商品接口 POST /api/products")
    product_data = {
        "name": "测试商品 - 有机蔬菜礼盒",
        "description": "多种有机蔬菜组合，新鲜健康",
        "price": 59.9,
        "original_price": 89.9,
        "stock": 50,
        "min_group_size": 2,
        "max_group_size": 4,
        "image_url": "https://example.com/vegetable.jpg"
    }
    response = requests.post(f"{BASE_URL}/products", json=product_data)
    assert response.status_code == 200, f"创建商品失败: {response.text}"
    product = response.json()
    product_id = product["id"]
    print(f"✅ 创建商品成功, ID: {product_id}")
    print(f"   商品名称: {product['name']}")
    print(f"   库存: {product['stock']}")

    # 2. 测试获取商品列表
    print("\n2. 测试获取商品列表接口 GET /api/products")
    response = requests.get(f"{BASE_URL}/products")
    assert response.status_code == 200, f"获取商品列表失败: {response.text}"
    products = response.json()
    print(f"✅ 获取商品列表成功, 共 {len(products)} 个商品")

    # 3. 测试发起团购
    print("\n3. 测试发起团购接口 POST /api/groups")
    group_data = {
        "product_id": product_id,
        "organizer_id": "test_user_001",
        "target_size": 2,
        "duration_hours": 24
    }
    response = requests.post(f"{BASE_URL}/groups", json=group_data)
    assert response.status_code == 200, f"发起团购失败: {response.text}"
    group = response.json()
    group_id = group["id"]
    print(f"✅ 发起团购成功, ID: {group_id}")
    print(f"   团长: {group['organizer_id']}")
    print(f"   目标人数: {group['target_size']}")
    print(f"   当前人数: {group['current_size']}")

    # 4. 测试获取活跃团购列表
    print("\n4. 测试获取活跃团购列表接口 GET /api/groups")
    response = requests.get(f"{BASE_URL}/groups")
    assert response.status_code == 200, f"获取活跃团购失败: {response.text}"
    groups = response.json()
    print(f"✅ 获取活跃团购列表成功, 共 {len(groups)} 个活跃团购")

    # 5. 测试加入团购
    print("\n5. 测试加入团购接口 POST /api/groups/{group_id}/join")
    join_data = {
        "user_id": "test_user_002"
    }
    response = requests.post(f"{BASE_URL}/groups/{group_id}/join", json=join_data)
    assert response.status_code == 200, f"加入团购失败: {response.text}"
    result = response.json()
    print(f"✅ 加入团购成功")
    print(f"   当前人数: {result['current_size']}/{result['target_size']}")
    print(f"   团购状态: {result['status']}")

    # 6. 测试查询团购详情
    print("\n6. 测试查询团购详情接口 GET /api/groups/{group_id}")
    response = requests.get(f"{BASE_URL}/groups/{group_id}")
    assert response.status_code == 200, f"查询团购详情失败: {response.text}"
    group_detail = response.json()
    print(f"✅ 查询团购详情成功")
    print(f"   团购状态: {group_detail['status']}")
    print(f"   成员列表: {', '.join(group_detail['members'])}")

    # 7. 测试获取团购订单列表
    if group_detail['status'] == 'success':
        print("\n7. 测试获取团购订单列表接口 GET /api/groups/{group_id}/orders")
        response = requests.get(f"{BASE_URL}/groups/{group_id}/orders")
        assert response.status_code == 200, f"获取团购订单失败: {response.text}"
        orders = response.json()
        print(f"✅ 获取团购订单成功, 共 {len(orders)} 个订单")
        for order in orders:
            print(f"     - 订单ID: {order['id']}, 用户: {order['user_id']}, 金额: ¥{order['total_amount']}")

    # 8. 测试获取用户参团记录
    print("\n8. 测试获取用户参团记录接口 GET /api/users/{user_id}/join-records")
    response = requests.get(f"{BASE_URL}/users/test_user_001/join-records")
    assert response.status_code == 200, f"获取用户参团记录失败: {response.text}"
    records = response.json()
    print(f"✅ 获取用户参团记录成功")
    print(f"   总参团次数: {records['total_joined']}")

    print("\n" + "=" * 60)
    print("🎉 所有API接口测试通过!")
    print("=" * 60)
    print("\n📊 测试结果:")
    print("  ✅ 商品管理接口正常")
    print("  ✅ 团购管理接口正常")
    print("  ✅ 订单查询接口正常")
    print("  ✅ 统计查询接口正常")
    print("\n🌐 完整的API文档请访问: http://localhost:8005/docs")

if __name__ == "__main__":
    # 先启动服务
    import subprocess
    import time
    import atexit

    # 启动服务
    print("启动API服务...")
    proc = subprocess.Popen(
        ["python", "src/main.py"],
        cwd="/Users/sunmuchao/Downloads/ai_incubation_platform/ai-community-buying",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    atexit.register(proc.terminate)

    # 等待服务启动
    time.sleep(3)

    try:
        test_api_flow()
    finally:
        proc.terminate()
        proc.wait()