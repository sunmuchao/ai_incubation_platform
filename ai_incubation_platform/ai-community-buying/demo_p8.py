#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
P8 智能风控/信用体系 - 演示脚本

演示功能:
1. 用户信用评分查询与计算
2. 风控规则管理
3. 黑名单管理
4. 订单风险评估
"""
import requests
import json

BASE_URL = "http://localhost:8005"


def print_section(title):
    """打印章节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_response(response, description=""):
    """打印响应结果"""
    print(f"\n{description}")
    print(f"状态码：{response.status_code}")
    if response.ok:
        print(f"响应数据：{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"错误信息：{response.text}")


# ====================  1. 信用体系演示  ====================

def demo_credit_system():
    """演示信用体系功能"""
    print_section("1. 信用体系演示")

    user_id = "demo_user_001"

    # 1.1 获取用户信用分
    print("\n--- 1.1 获取用户信用分 ---")
    response = requests.get(
        f"{BASE_URL}/api/p8/credit/score",
        params={"user_id": user_id}
    )
    print_response(response, "获取信用分:")

    # 1.2 获取信用因子
    print("\n--- 1.2 获取信用因子 ---")
    response = requests.get(f"{BASE_URL}/api/p8/credit/factors")
    print_response(response, "信用因子配置:")

    # 1.3 更新信用分
    print("\n--- 1.3 更新信用分 (完成订单 +50 分) ---")
    response = requests.post(
        f"{BASE_URL}/api/p8/credit/update",
        json={
            "user_id": user_id,
            "change": 50,
            "reason": "完成订单",
            "change_type": "ORDER_COMPLETE"
        }
    )
    print_response(response, "信用分更新:")

    # 1.4 获取信用历史
    print("\n--- 1.4 获取信用历史 ---")
    response = requests.get(
        f"{BASE_URL}/api/p8/credit/history",
        params={"user_id": user_id, "limit": 10}
    )
    print_response(response, "信用历史记录:")


# ====================  2. 风控规则演示  ====================

def demo_risk_rules():
    """演示风控规则功能"""
    print_section("2. 风控规则演示")

    # 2.1 创建风控规则
    print("\n--- 2.1 创建风控规则 ---")
    rule_data = {
        "rule_code": "DEMO_HIGH_AMOUNT",
        "rule_name": "高额订单风控规则",
        "rule_type": "order",
        "rule_category": "AMOUNT",
        "conditions": [
            {"field": "amount", "operator": ">", "threshold": 2000}
        ],
        "action": "review",
        "risk_score": 30,
        "priority": 50,
        "description": "订单金额超过 2000 元需要审核"
    }
    response = requests.post(f"{BASE_URL}/api/p8/rules/", json=rule_data)
    print_response(response, "创建风控规则:")

    # 2.2 获取所有规则
    print("\n--- 2.2 获取所有风控规则 ---")
    response = requests.get(f"{BASE_URL}/api/p8/rules/")
    print_response(response, "风控规则列表:")

    # 2.3 规则评估
    print("\n--- 2.3 规则评估 (高额订单) ---")
    response = requests.post(
        f"{BASE_URL}/api/p8/rules/evaluate",
        json={
            "context": {
                "user_id": "demo_user_001",
                "amount": 3000,  # 高额订单
                "device_id": "device_001"
            },
            "rule_type": "order"
        }
    )
    print_response(response, "规则评估结果 (高额):")

    print("\n--- 2.4 规则评估 (普通订单) ---")
    response = requests.post(
        f"{BASE_URL}/api/p8/rules/evaluate",
        json={
            "context": {
                "user_id": "demo_user_001",
                "amount": 500,  # 普通订单
                "device_id": "device_001"
            },
            "rule_type": "order"
        }
    )
    print_response(response, "规则评估结果 (普通):")


# ====================  3. 黑名单管理演示  ====================

def demo_blacklist():
    """演示黑名单管理功能"""
    print_section("3. 黑名单管理演示")

    # 3.1 添加到黑名单
    print("\n--- 3.1 添加到黑名单 ---")
    response = requests.post(
        f"{BASE_URL}/api/p8/blacklist/",
        json={
            "target_type": "user",
            "target_value": "fraud_user_001",
            "reason": "欺诈行为",
            "blacklist_type": "PERMANENT",
            "reason_code": "FRAUD"
        }
    )
    print_response(response, "添加到黑名单:")

    # 3.2 检查黑名单
    print("\n--- 3.2 检查黑名单 (欺诈用户) ---")
    response = requests.get(
        f"{BASE_URL}/api/p8/blacklist/check",
        params={"target_type": "user", "target_value": "fraud_user_001"}
    )
    print_response(response, "黑名单检查结果:")

    print("\n--- 3.3 检查黑名单 (正常用户) ---")
    response = requests.get(
        f"{BASE_URL}/api/p8/blacklist/check",
        params={"target_type": "user", "target_value": "normal_user"}
    )
    print_response(response, "黑名单检查结果 (正常):")

    # 3.3 获取黑名单列表
    print("\n--- 3.4 获取黑名单列表 ---")
    response = requests.get(f"{BASE_URL}/api/p8/blacklist/")
    print_response(response, "黑名单列表:")


# ====================  4. 订单风控演示  ====================

def demo_order_risk():
    """演示订单风险评估功能"""
    print_section("4. 订单风险评估演示")

    # 4.1 评估正常订单
    print("\n--- 4.1 评估正常订单 ---")
    response = requests.post(
        f"{BASE_URL}/api/p8/order-risk/assess",
        json={
            "order_id": "ORDER_DEMO_001",
            "user_id": "demo_user_001",
            "amount": 500
        }
    )
    print_response(response, "正常订单风险评估:")

    # 4.2 评估高额订单
    print("\n--- 4.2 评估高额订单 ---")
    response = requests.post(
        f"{BASE_URL}/api/p8/order-risk/assess",
        json={
            "order_id": "ORDER_DEMO_002",
            "user_id": "demo_user_001",
            "amount": 8000
        }
    )
    print_response(response, "高额订单风险评估:")

    # 4.3 评估黑名单用户订单
    print("\n--- 4.3 评估黑名单用户订单 ---")
    response = requests.post(
        f"{BASE_URL}/api/p8/order-risk/assess",
        json={
            "order_id": "ORDER_DEMO_003",
            "user_id": "fraud_user_001",
            "amount": 500
        }
    )
    print_response(response, "黑名单用户订单风险评估:")

    # 4.4 欺诈举报
    print("\n--- 4.4 欺诈举报 ---")
    response = requests.post(
        f"{BASE_URL}/api/p8/order-risk/fraud-report",
        json={
            "order_id": "ORDER_DEMO_004",
            "user_id": "suspect_user_001",
            "reason": "虚假订单信息",
            "evidence": {"screenshot": "test.png", "ip": "192.168.1.100"}
        }
    )
    print_response(response, "欺诈举报:")


# ====================  主程序  ====================

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║           AI 社区团购 - P8 智能风控/信用体系演示              ║
╠═══════════════════════════════════════════════════════════╣
║  演示内容:                                                 ║
║  1. 信用体系 - 用户信用评分查询与计算                        ║
║  2. 风控规则 - 规则管理与风险评估                          ║
║  3. 黑名单管理 - 黑名单 CRUD 与检查                          ║
║  4. 订单风控 - 订单风险评估与欺诈举报                       ║
╚═══════════════════════════════════════════════════════════╝

请确保服务已启动：python src/main.py
    """)

    input("按 Enter 键开始演示...")

    try:
        demo_credit_system()
        input("\n按 Enter 键继续风控规则演示...")

        demo_risk_rules()
        input("\n按 Enter 键继续黑名单管理演示...")

        demo_blacklist()
        input("\n按 Enter 键继续订单风控演示...")

        demo_order_risk()

        print_section("演示完成")
        print("所有 P8 智能风控/信用体系功能演示结束!\n")

    except requests.exceptions.ConnectionError:
        print("\n❌ 错误：无法连接到服务")
        print(f"请确保服务已在 {BASE_URL} 启动")
        print("\n启动服务命令：python src/main.py")
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误：{e}")
