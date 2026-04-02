#!/usr/bin/env python3
"""
P1功能验证脚本，无需启动服务，直接测试内部逻辑
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.task import TaskCreate, TaskStatus, InteractionType, TaskPriority
from services.task_service import task_service
from services.anti_cheat_service import anti_cheat_service
from services.payment_service import payment_service
from models.payment import PaymentRequest, PayoutRequest, TaskPaymentRequest


def test_enhanced_search():
    """测试增强的搜索功能"""
    print("🚀 测试增强的搜索功能...")

    # 创建测试任务
    task1 = TaskCreate(
        ai_employer_id="agent_001",
        title="北京线下采集任务",
        description="采集北京朝阳区门店照片",
        capability_gap="AI无法线下到场",
        interaction_type=InteractionType.PHYSICAL,
        location_hint="北京朝阳区",
        required_skills={"role": "线下采集"},
        reward_amount=150.0,
        priority=TaskPriority.HIGH
    )
    t1 = task_service.create_task(task1)

    task2 = TaskCreate(
        ai_employer_id="agent_001",
        title="上海数据标注任务",
        description="标注图片中的人物",
        capability_gap="需要人类判断力",
        interaction_type=InteractionType.DIGITAL,
        location_hint="上海",
        required_skills={"role": "数据标注"},
        reward_amount=80.0,
        priority=TaskPriority.MEDIUM
    )
    t2 = task_service.create_task(task2)

    task3 = TaskCreate(
        ai_employer_id="agent_002",
        title="广州上门安装任务",
        description="上门安装路由器",
        capability_gap="需要物理操作",
        interaction_type=InteractionType.PHYSICAL,
        location_hint="广州天河区",
        required_skills={"role": "安装师傅"},
        reward_amount=200.0,
        priority=TaskPriority.URGENT
    )
    t3 = task_service.create_task(task3)

    # 测试地点筛选
    results = task_service.search_tasks(location="北京")
    assert len(results) == 1
    assert results[0].id == t1.id
    print("✅ 地点筛选功能正常")

    # 测试报酬范围筛选
    results = task_service.search_tasks(min_reward=100, max_reward=180)
    assert len(results) == 1
    assert results[0].id == t1.id
    print("✅ 报酬范围筛选功能正常")

    # 测试优先级筛选
    results = task_service.search_tasks(priority=TaskPriority.URGENT)
    assert len(results) == 1
    assert results[0].id == t3.id
    print("✅ 优先级筛选功能正常")

    # 测试关键词搜索
    results = task_service.search_tasks(keyword="标注")
    assert len(results) == 1
    assert results[0].id == t2.id
    print("✅ 关键词搜索功能正常")

    # 测试排序
    results = task_service.search_tasks(sort_by="reward", sort_order="desc")
    assert len(results) == 3
    assert results[0].reward_amount == 200.0  # t3
    assert results[1].reward_amount == 150.0  # t1
    assert results[2].reward_amount == 80.0   # t2
    print("✅ 排序功能正常")

    print("🎉 增强搜索功能测试通过！\n")


def test_anti_cheat():
    """测试反作弊功能"""
    print("🚀 测试反作弊功能...")

    worker_id = "test_worker_001"
    task_id = "test_task_001"
    content = "这是测试交付内容"
    attachments = ["https://example.com/photo1.jpg"]

    # 测试提交频率检测
    ok, reason = anti_cheat_service.check_submission_frequency(worker_id)
    assert ok, f"首次提交应该通过: {reason}"
    print("✅ 首次提交频率检测通过")

    # 记录提交
    content_hash = anti_cheat_service.record_submission(task_id, worker_id, content, attachments)
    assert content_hash
    print("✅ 提交记录成功")

    # 测试重复提交检测
    ok, reason = anti_cheat_service.check_duplicate_delivery(task_id, content, attachments, worker_id)
    assert not ok, "相同内容重复提交应该被拒绝"
    assert "重复提交" in reason
    print("✅ 重复提交检测正常")

    # 测试风险分数
    risk_score = anti_cheat_service.get_worker_risk_score(worker_id)
    assert 0 <= risk_score <= 1
    print(f"✅ 工人风险分数正常: {risk_score:.2f}")

    print("🎉 反作弊功能测试通过！\n")


def test_payment_service():
    """测试支付服务功能"""
    print("🚀 测试支付服务功能...")

    employer_id = "employer_001"
    worker_id = "worker_001"
    task_id = "task_payment_001"

    # 测试充值
    deposit_req = PaymentRequest(
        user_id=employer_id,
        amount=1000.0,
        payment_method="alipay",
        description="充值1000元"
    )
    deposit_tx = payment_service.create_deposit(deposit_req)
    assert deposit_tx.status == "success"
    assert deposit_tx.amount == 1000.0
    wallet = payment_service.get_wallet_balance(employer_id)
    assert wallet.balance == 1000.0
    print("✅ 充值功能正常")

    # 测试任务支付
    payment_req = TaskPaymentRequest(
        task_id=task_id,
        ai_employer_id=employer_id,
        worker_id=worker_id,
        amount=100.0,
        platform_fee_rate=0.1
    )
    payment_tx, fee_tx = payment_service.process_task_payment(payment_req)
    assert payment_tx.status == "success"
    assert fee_tx.amount == 10.0  # 10%服务费

    # 检查余额变化
    employer_wallet = payment_service.get_wallet_balance(employer_id)
    assert employer_wallet.balance == 900.0  # 1000 - 100
    worker_wallet = payment_service.get_wallet_balance(worker_id)
    assert worker_wallet.balance == 90.0  # 100 - 10服务费
    print("✅ 任务支付与结算功能正常")

    # 测试提现
    payout_req = PayoutRequest(
        worker_id=worker_id,
        amount=50.0,
        payout_method="wechat",
        payout_account="wx123456"
    )
    payout_tx = payment_service.create_payout(payout_req)
    assert payout_tx.status == "success"
    worker_wallet = payment_service.get_wallet_balance(worker_id)
    assert worker_wallet.balance == 40.0  # 90 - 50
    print("✅ 提现功能正常")

    # 测试交易记录查询
    txs = payment_service.list_user_transactions(employer_id)
    assert len(txs) >= 2  # 充值 + 支付
    print("✅ 交易记录查询功能正常")

    print("🎉 支付服务功能测试通过！\n")


def main():
    try:
        test_enhanced_search()
        test_anti_cheat()
        test_payment_service()
        print("🏆 所有P1功能内部逻辑测试全部通过！")
        print("\n📋 已完成的P1功能：")
        print("✅ 反作弊与重复交付检测功能")
        print("✅ 支付/结算接口层（Mock实现）")
        print("✅ 多维度搜索与筛选功能增强")
        print("✅ 持久化存储方案设计文档")
        print("\n📁 新增文件：")
        print("   - src/models/payment.py - 支付数据模型")
        print("   - src/services/anti_cheat_service.py - 反作弊服务")
        print("   - src/services/payment_service.py - 支付服务")
        print("   - src/api/payment.py - 支付API")
        print("   - PERSISTENCE_DESIGN.md - 持久化存储设计")
        print("   - CHANGELOG.md - 更新日志")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
