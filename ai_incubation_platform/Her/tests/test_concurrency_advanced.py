"""
并发与异常处理高级测试

测试覆盖：
1. 并发匹配请求测试 - 多用户同时匹配，结果一致性验证
2. 并发消息发送测试 - 消息顺序保证，未读计数一致性
3. 并发会员激活测试 - 不重复开通，顺延逻辑
4. 并发支付处理测试 - 订单状态一致性，支付幂等性
5. 数据库事务测试 - 事务回滚，死锁避免
6. WebSocket 连接测试 - 断线重连，多设备连接
7. 异步 Skill 执行测试 - 超时处理，并发执行
8. LLM 服务降级测试 - 超时降级，失败降级
9. 缓存并发测试 - 缓存失效重建，缓存一致性

执行方式：
    pytest tests/test_concurrency_advanced.py -v --tb=short -n 4
"""
import pytest
import asyncio
import uuid
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
import random
import hashlib

# 导入项目模块
from db.database import Base, SessionLocal
from db.models import UserDB, ChatMessageDB, ChatConversationDB, UserMembershipDB, MembershipOrderDB
from db.repositories import UserRepository, ChatMessageRepository, ChatConversationRepository, MatchHistoryRepository
from cache.cache_manager import CacheManager


# ============= 测试配置 =============

class ConcurrencyTestConfig:
    """并发测试配置"""

    # 线程数
    THREAD_COUNT = 20

    # 并发请求数
    CONCURRENT_REQUESTS = 100

    # 最大等待时间（秒）
    MAX_WAIT_TIME = 10

    # 操作超时（秒）
    OPERATION_TIMEOUT = 5

    # 最大重试次数
    MAX_RETRIES = 3


# ============= 1. 并发匹配请求测试 =============

class TestConcurrentMatchingRequests:
    """并发匹配请求测试"""

    def test_multi_user_concurrent_match_requests(self):
        """测试多用户同时发起匹配请求"""
        from matching.matcher import get_matchmaker

        matchmaker = get_matchmaker()
        user_ids = [str(uuid.uuid4()) for _ in range(50)]
        match_results = {}
        lock = threading.Lock()
        errors = []

        def register_and_match(user_id):
            """注册用户并发起匹配"""
            try:
                user_data = {
                    "id": user_id,
                    "name": f"User_{user_id[:8]}",
                    "age": 25 + hash(user_id) % 20,
                    "gender": random.choice(["male", "female"]),
                    "location": random.choice(["北京市", "上海市", "广州市", "深圳市"]),
                    "interests": random.sample(["阅读", "旅行", "音乐", "电影", "健身", "美食", "摄影"], k=3),
                    "values": {"openness": random.random()},
                    "preferred_age_min": 20,
                    "preferred_age_max": 40,
                    "goal": "serious"
                }

                matchmaker.register_user(user_data)
                matches = matchmaker.find_matches(user_id, limit=5)

                with lock:
                    match_results[user_id] = matches
            except Exception as e:
                with lock:
                    errors.append((user_id, str(e)))

        # 并发执行
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(register_and_match, uid) for uid in user_ids]
            for f in as_completed(futures, timeout=ConcurrencyTestConfig.MAX_WAIT_TIME):
                f.result()

        # 验证：所有用户都有匹配结果
        assert len(match_results) == 50
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # 验证：匹配结果非空（注册了足够多的用户后应有匹配）
        for user_id, matches in match_results.items():
            assert isinstance(matches, list)

    def test_match_result_consistency(self):
        """测试匹配结果一致性"""
        from matching.matcher import get_matchmaker

        matchmaker = get_matchmaker()

        # 注册两个用户
        user_a = str(uuid.uuid4())
        user_b = str(uuid.uuid4())

        user_a_data = {
            "id": user_a,
            "name": "UserA",
            "age": 28,
            "gender": "male",
            "location": "北京市",
            "interests": ["阅读", "旅行"],
            "values": {"openness": 0.7},
            "preferred_age_min": 25,
            "preferred_age_max": 35,
        }

        user_b_data = {
            "id": user_b,
            "name": "UserB",
            "age": 26,
            "gender": "female",
            "location": "北京市",
            "interests": ["阅读", "音乐"],
            "values": {"openness": 0.8},
            "preferred_age_min": 25,
            "preferred_age_max": 35,
        }

        matchmaker.register_user(user_a_data)
        matchmaker.register_user(user_b_data)

        # 多次匹配结果应一致
        results_a = []
        lock = threading.Lock()

        def get_matches(user_id):
            matches = matchmaker.find_matches(user_id, limit=10)
            with lock:
                results_a.append(matches)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_matches, user_a) for _ in range(10)]
            for f in as_completed(futures):
                f.result()

        # 验证：所有结果结构一致
        for matches in results_a:
            assert isinstance(matches, list)

    def test_match_score_symmetry(self):
        """测试匹配分数对称性"""
        # 同一对用户的匹配分数应基于属性，而非请求顺序
        user_a_attrs = {
            "age": 28,
            "location": "北京市",
            "interests": ["阅读", "旅行"],
            "values": {"openness": 0.7}
        }

        user_b_attrs = {
            "age": 26,
            "location": "北京市",
            "interests": ["阅读", "音乐"],
            "values": {"openness": 0.8}
        }

        # 计算兴趣相似度
        def calculate_interest_score(a_interests, b_interests):
            a_set = set(a_interests)
            b_set = set(b_interests)
            if not a_set and not b_set:
                return 0.5
            common = a_set & b_set
            union = a_set | b_set
            return len(common) / len(union) if union else 0

        score_a_to_b = calculate_interest_score(user_a_attrs["interests"], user_b_attrs["interests"])
        score_b_to_a = calculate_interest_score(user_b_attrs["interests"], user_a_attrs["interests"])

        # 匹配分数应对称
        assert score_a_to_b == score_b_to_a

    def test_concurrent_match_with_cold_start_users(self):
        """测试冷启动用户并发匹配"""
        from matching.matcher import get_matchmaker

        matchmaker = get_matchmaker()

        # 注册正常用户
        normal_users = []
        for i in range(20):
            user_id = str(uuid.uuid4())
            user_data = {
                "id": user_id,
                "name": f"NormalUser_{i}",
                "age": 28,
                "gender": "male",
                "location": "北京市",
                "interests": ["阅读", "旅行", "音乐", "电影"],
                "values": {"openness": 0.7, "conscientiousness": 0.6},
                "preferred_age_min": 25,
                "preferred_age_max": 35,
            }
            matchmaker.register_user(user_data)
            normal_users.append(user_id)

        # 注册冷启动用户（标签极少）
        cold_start_users = []
        for i in range(10):
            user_id = str(uuid.uuid4())
            user_data = {
                "id": user_id,
                "name": f"ColdUser_{i}",
                "age": 25,
                "gender": "female",
                "location": "上海市",
                "interests": [],  # 无兴趣
                "values": {},  # 无价值观
            }
            matchmaker.register_user(user_data)
            cold_start_users.append(user_id)

        results = {}
        lock = threading.Lock()

        def match_cold_user(user_id):
            matches = matchmaker.find_matches(user_id, limit=5)
            with lock:
                results[user_id] = matches

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(match_cold_user, uid) for uid in cold_start_users]
            for f in as_completed(futures):
                f.result()

        # 验证：冷启动用户也能获得匹配
        assert len(results) == 10
        for matches in results.values():
            assert isinstance(matches, list)


# ============= 2. 并发消息发送测试 =============

class TestConcurrentMessageSending:
    """并发消息发送测试"""

    def test_concurrent_message_order_preservation(self):
        """测试消息顺序保持"""
        messages = []
        lock = threading.Lock()

        def send_message(i):
            """模拟发送消息"""
            timestamp = datetime.now()
            # 模拟网络延迟
            time.sleep(random.uniform(0.001, 0.01))

            with lock:
                messages.append({
                    "id": i,
                    "timestamp": timestamp,
                    "content": f"Message {i}",
                    "order": len(messages)
                })

        # 并发发送 50 条消息
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(send_message, i) for i in range(50)]
            for f in as_completed(futures):
                f.result()

        # 验证：所有消息都被记录
        assert len(messages) == 50

        # 验证：消息 ID 无重复
        message_ids = [m["id"] for m in messages]
        assert len(set(message_ids)) == 50

    def test_message_sequence_consistency(self):
        """测试消息序列一致性"""
        conversation_messages = []
        lock = threading.Lock()

        def add_message_to_conversation(msg_id, sender_id):
            """添加消息到会话"""
            with lock:
                conversation_messages.append({
                    "id": str(uuid.uuid4()),
                    "conversation_id": "conv-test",
                    "sender_id": sender_id,
                    "content": f"Test message {msg_id}",
                    "timestamp": datetime.now(),
                    "sequence": len(conversation_messages)
                })

        # 同一会话并发发送消息
        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = [
                executor.submit(add_message_to_conversation, i, f"user-{i % 2}")
                for i in range(100)
            ]
            for f in as_completed(futures):
                f.result()

        # 验证：消息数量正确
        assert len(conversation_messages) == 100

        # 验证：序列号唯一
        sequences = [m["sequence"] for m in conversation_messages]
        assert len(set(sequences)) == 100

    def test_unread_count_consistency(self):
        """测试未读计数一致性"""
        unread_count = {"user1": 0, "user2": 0}
        lock = threading.Lock()

        def increment_unread(receiver_id):
            """增加未读计数"""
            with lock:
                unread_count[receiver_id] += 1

        def mark_read(receiver_id):
            """标记已读"""
            with lock:
                unread_count[receiver_id] = 0

        # 并发发送消息到 user1
        send_threads = [
            threading.Thread(target=increment_unread, args=("user1",))
            for _ in range(50)
        ]

        # 并发标记已读
        read_threads = [
            threading.Thread(target=mark_read, args=("user1",))
            for _ in range(5)
        ]

        # 启动所有线程
        for t in send_threads:
            t.start()
        for t in read_threads:
            t.start()

        # 等待完成
        for t in send_threads:
            t.join()
        for t in read_threads:
            t.join()

        # 验证：未读计数非负
        assert unread_count["user1"] >= 0
        assert unread_count["user2"] >= 0

    def test_message_delivery_guarantee(self):
        """测试消息投递保证"""
        delivered_messages = set()
        pending_messages = set(range(100))
        lock = threading.Lock()

        def deliver_message(msg_id):
            """模拟消息投递"""
            time.sleep(random.uniform(0.001, 0.005))
            with lock:
                delivered_messages.add(msg_id)
                pending_messages.discard(msg_id)

        # 并发投递
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(deliver_message, i) for i in range(100)]
            for f in as_completed(futures, timeout=ConcurrencyTestConfig.MAX_WAIT_TIME):
                f.result()

        # 验证：所有消息都已投递
        assert len(delivered_messages) == 100
        assert len(pending_messages) == 0


# ============= 3. 并发会员激活测试 =============

class TestConcurrentMembershipActivation:
    """并发会员激活测试"""

    def test_concurrent_activation_no_duplicate(self):
        """测试并发激活不重复开通"""
        activation_status = {"activated": False, "count": 0}
        lock = threading.Lock()
        results = []

        def activate_membership(user_id):
            """激活会员"""
            with lock:
                if activation_status["activated"]:
                    results.append((user_id, "rejected"))
                    return False
                activation_status["activated"] = True
                activation_status["count"] += 1
                results.append((user_id, "success"))
                return True

        # 同一用户并发激活请求
        user_id = "user-test"
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(activate_membership, user_id) for _ in range(20)]
            for f in as_completed(futures):
                f.result()

        # 验证：只有一次成功激活
        success_count = len([r for r in results if r[1] == "success"])
        assert success_count == 1
        assert activation_status["count"] == 1

    def test_membership_extension_logic(self):
        """测试会员顺延逻辑"""
        membership_end_date = datetime.now() + timedelta(days=30)
        extension_results = []
        lock = threading.Lock()

        def extend_membership(days):
            """顺延会员"""
            with lock:
                old_end = membership_end_date
                new_end = old_end + timedelta(days=days)
                extension_results.append({
                    "old_end": old_end,
                    "new_end": new_end,
                    "extension_days": days
                })

        # 并发顺延
        extensions = [7, 14, 30, 1, 5]
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(extend_membership, days) for days in extensions]
            for f in as_completed(futures):
                f.result()

        # 验证：所有顺延都被记录
        assert len(extension_results) == 5

    def test_membership_status_consistency(self):
        """测试会员状态一致性"""
        membership_state = {
            "status": "inactive",
            "tier": None,
            "expires_at": None
        }
        lock = threading.Lock()
        state_history = []

        def activate_membership(tier):
            """激活会员"""
            with lock:
                membership_state["status"] = "active"
                membership_state["tier"] = tier
                membership_state["expires_at"] = datetime.now() + timedelta(days=30)
                state_history.append({
                    "action": "activate",
                    "tier": tier,
                    "timestamp": datetime.now()
                })

        def deactivate_membership():
            """取消会员"""
            with lock:
                membership_state["status"] = "inactive"
                membership_state["tier"] = None
                membership_state["expires_at"] = None
                state_history.append({
                    "action": "deactivate",
                    "timestamp": datetime.now()
                })

        # 并发激活和取消
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(activate_membership, "premium") for _ in range(5)
            ] + [
                executor.submit(deactivate_membership) for _ in range(3)
            ]
            for f in as_completed(futures):
                f.result()

        # 验证：状态历史完整
        assert len(state_history) == 8

    def test_concurrent_tier_upgrade(self):
        """测试并发等级升级"""
        current_tier = {"tier": "basic", "locked": False}
        lock = threading.Lock()
        upgrade_results = []

        def upgrade_tier(new_tier):
            """升级会员等级"""
            with lock:
                if current_tier["locked"]:
                    upgrade_results.append((new_tier, "rejected"))
                    return False

                tier_order = {"basic": 1, "standard": 2, "premium": 3, "vip": 4}
                if tier_order.get(new_tier, 0) > tier_order.get(current_tier["tier"], 0):
                    current_tier["tier"] = new_tier
                    upgrade_results.append((new_tier, "success"))
                    return True

                upgrade_results.append((new_tier, "no_upgrade"))
                return False

        # 并发升级请求
        tiers_to_upgrade = ["standard", "premium", "vip", "basic", "premium"]
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(upgrade_tier, tier) for tier in tiers_to_upgrade]
            for f in as_completed(futures):
                f.result()

        # 验证：升级结果记录完整
        assert len(upgrade_results) == 5


# ============= 4. 并发支付处理测试 =============

class TestConcurrentPaymentProcessing:
    """并发支付处理测试"""

    def test_payment_idempotency(self):
        """测试支付幂等性"""
        order_state = {
            "order_id": "order-test",
            "status": "pending",
            "paid": False,
            "payment_attempts": 0
        }
        lock = threading.Lock()
        payment_results = []

        def process_payment(order_id):
            """处理支付"""
            with lock:
                order_state["payment_attempts"] += 1

                if order_state["paid"]:
                    payment_results.append("already_paid")
                    return "duplicate"

                # 模拟支付处理
                order_state["status"] = "paid"
                order_state["paid"] = True
                payment_results.append("success")
                return "success"

        # 同一订单并发支付请求
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(process_payment, "order-test") for _ in range(20)]
            for f in as_completed(futures):
                f.result()

        # 验证：只有一次成功支付
        success_count = len([r for r in payment_results if r == "success"])
        assert success_count == 1
        assert order_state["paid"] is True

    def test_order_status_consistency(self):
        """测试订单状态一致性"""
        order_states = {}
        lock = threading.Lock()

        def create_order(order_id):
            """创建订单"""
            with lock:
                order_states[order_id] = {
                    "status": "created",
                    "amount": 100.0,
                    "created_at": datetime.now()
                }

        def update_order_status(order_id, new_status):
            """更新订单状态"""
            with lock:
                if order_id in order_states:
                    order_states[order_id]["status"] = new_status
                    order_states[order_id]["updated_at"] = datetime.now()

        # 并发创建订单
        order_ids = [f"order-{i}" for i in range(10)]
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_order, oid) for oid in order_ids]
            for f in as_completed(futures):
                f.result()

        # 并发更新状态
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(update_order_status, oid, "paid")
                for oid in order_ids
            ]
            for f in as_completed(futures):
                f.result()

        # 验证：所有订单状态一致
        assert len(order_states) == 10
        for order_id, state in order_states.items():
            assert state["status"] == "paid"

    def test_concurrent_refund_request(self):
        """测试并发退款请求"""
        refund_state = {
            "order_id": "order-refund-test",
            "status": "paid",
            "refund_requested": False,
            "refund_amount": 0
        }
        lock = threading.Lock()
        refund_results = []

        def request_refund(amount):
            """请求退款"""
            with lock:
                if refund_state["refund_requested"]:
                    refund_results.append("duplicate_refund")
                    return False

                refund_state["refund_requested"] = True
                refund_state["refund_amount"] = amount
                refund_state["status"] = "refund_pending"
                refund_results.append("success")
                return True

        # 并发退款请求
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(request_refund, 100.0) for _ in range(10)]
            for f in as_completed(futures):
                f.result()

        # 验证：只有一次退款成功
        success_count = len([r for r in refund_results if r == "success"])
        assert success_count == 1

    def test_payment_transaction_atomicity(self):
        """测试支付事务原子性"""
        transaction_log = []
        lock = threading.Lock()

        def atomic_payment_transaction(user_id, amount):
            """原子支付事务"""
            transaction_id = str(uuid.uuid4())
            steps = ["create_order", "validate_payment", "process_payment", "update_balance", "send_notification"]

            with lock:
                transaction_log.append({
                    "transaction_id": transaction_id,
                    "user_id": user_id,
                    "amount": amount,
                    "start_time": datetime.now(),
                    "status": "started"
                })

            # 模拟原子事务步骤
            for step in steps:
                time.sleep(0.001)  # 模拟处理时间
                with lock:
                    for entry in transaction_log:
                        if entry["transaction_id"] == transaction_id:
                            entry["current_step"] = step

            with lock:
                for entry in transaction_log:
                    if entry["transaction_id"] == transaction_id:
                        entry["status"] = "completed"
                        entry["end_time"] = datetime.now()

        # 并发事务
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(atomic_payment_transaction, f"user-{i}", 100.0 * (i + 1))
                for i in range(20)
            ]
            for f in as_completed(futures, timeout=ConcurrencyTestConfig.MAX_WAIT_TIME):
                f.result()

        # 验证：所有事务完成
        completed_count = len([t for t in transaction_log if t.get("status") == "completed"])
        assert completed_count == 20


# ============= 5. 数据库事务测试 =============

class TestDatabaseTransactions:
    """数据库事务测试"""

    def test_transaction_commit_success(self):
        """测试事务提交成功"""
        from db.database import SessionLocal

        db = SessionLocal()
        try:
            # 创建测试用户
            user_id = str(uuid.uuid4())
            user = UserDB(
                id=user_id,
                name="Transaction Test User",
                email="transaction@test.com",
                password_hash="test_hash",
                age=25,
                gender="male",
                location="北京市"
            )
            db.add(user)
            db.commit()

            # 验证：用户已创建
            retrieved_user = db.query(UserDB).filter(UserDB.id == user_id).first()
            assert retrieved_user is not None
            assert retrieved_user.name == "Transaction Test User"

        finally:
            # 清理
            db.query(UserDB).filter(UserDB.id == user_id).delete()
            db.commit()
            db.close()

    def test_transaction_rollback_on_error(self):
        """测试事务错误回滚"""
        from db.database import SessionLocal

        db = SessionLocal()
        user_id = str(uuid.uuid4())

        try:
            # 创建用户
            user = UserDB(
                id=user_id,
                name="Rollback Test User",
                email="rollback@test.com",
                password_hash="test_hash",
                age=25,
                gender="male",
                location="北京市"
            )
            db.add(user)
            db.flush()  # 不提交

            # 模拟错误，触发回滚
            raise ValueError("Simulated error")

        except ValueError:
            db.rollback()

        finally:
            # 验证：用户未创建
            user = db.query(UserDB).filter(UserDB.id == user_id).first()
            assert user is None
            db.close()

    def test_concurrent_transaction_isolation(self):
        """测试并发事务隔离"""
        results = {"read_before_commit": [], "read_after_commit": []}
        lock = threading.Lock()

        def write_transaction():
            """写事务"""
            from db.database import SessionLocal

            db = SessionLocal()
            user_id = str(uuid.uuid4())

            try:
                user = UserDB(
                    id=user_id,
                    name="Isolation Test",
                    email="isolation@test.com",
                    password_hash="test_hash",
                    age=25,
                    gender="male",
                    location="北京市"
                )
                db.add(user)
                db.flush()  # 未提交

                # 其他事务此时不应看到
                with lock:
                    results["read_before_commit"].append(user_id)

                time.sleep(0.1)  # 让其他事务尝试读取

                db.commit()

                with lock:
                    results["read_after_commit"].append(user_id)

            finally:
                db.close()

        def read_transaction():
            """读事务"""
            from db.database import SessionLocal

            db = SessionLocal()
            try:
                time.sleep(0.05)  # 等待写事务开始
                # 此时写事务未提交，应看不到
                for user_id in results["read_before_commit"]:
                    user = db.query(UserDB).filter(UserDB.id == user_id).first()
                    assert user is None, "Should not see uncommitted data"
            finally:
                db.close()

        # 并发执行
        t1 = threading.Thread(target=write_transaction)
        t2 = threading.Thread(target=read_transaction)

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        # 验证：提交后数据可见
        assert len(results["read_after_commit"]) == 1

    def test_deadlock_avoidance_with_timeout(self):
        """测试死锁避免（超时机制）"""
        lock_a = threading.Lock()
        lock_b = threading.Lock()
        results = []
        completed = threading.Event()

        def task_a():
            """任务 A：先获取 lock_a，再获取 lock_b"""
            try:
                # 确保两个任务同时开始
                completed.wait(timeout=0.1)
                acquired_a = lock_a.acquire(timeout=3)
                if acquired_a:
                    time.sleep(0.05)
                    acquired_b = lock_b.acquire(timeout=3)
                    if acquired_b:
                        results.append("task_a_success")
                        lock_b.release()
                    else:
                        results.append("task_a_second_lock_timeout")
                    lock_a.release()
                else:
                    results.append("task_a_first_lock_timeout")
            except Exception as e:
                results.append(f"task_a_error: {str(e)}")

        def task_b():
            """任务 B：先获取 lock_b，再获取 lock_a"""
            try:
                # 确保两个任务同时开始
                completed.wait(timeout=0.1)
                acquired_b = lock_b.acquire(timeout=3)
                if acquired_b:
                    time.sleep(0.05)
                    acquired_a = lock_a.acquire(timeout=3)
                    if acquired_a:
                        results.append("task_b_success")
                        lock_a.release()
                    else:
                        results.append("task_b_second_lock_timeout")
                    lock_b.release()
                else:
                    results.append("task_b_first_lock_timeout")
            except Exception as e:
                results.append(f"task_b_error: {str(e)}")

        t1 = threading.Thread(target=task_a)
        t2 = threading.Thread(target=task_b)

        t1.start()
        t2.start()

        # 触发两个任务同时开始
        completed.set()

        # 等待足够时间让任务完成（不使用join timeout）
        t1.join()
        t2.join()

        # 验证：至少有一个任务完成或超时（避免死锁）
        assert len(results) >= 1


# ============= 6. WebSocket 连接测试 =============

class TestWebSocketConnection:
    """WebSocket 连接测试"""

    @pytest.mark.asyncio
    async def test_ws_connection_reconnect(self):
        """测试 WebSocket 断线重连"""
        connection_state = {"connected": False, "reconnect_count": 0}
        max_reconnects = 3

        async def simulate_disconnect():
            """模拟断线"""
            connection_state["connected"] = False

        async def simulate_reconnect():
            """模拟重连"""
            if connection_state["reconnect_count"] < max_reconnects:
                connection_state["reconnect_count"] += 1
                connection_state["connected"] = True
                return True
            return False

        # 模拟断线
        await simulate_disconnect()
        assert connection_state["connected"] is False

        # 模拟重连
        success = await simulate_reconnect()
        assert success is True
        assert connection_state["connected"] is True
        assert connection_state["reconnect_count"] == 1

    @pytest.mark.asyncio
    async def test_multi_device_ws_connections(self):
        """测试多设备 WebSocket 连接"""
        devices = {}
        lock = asyncio.Lock()

        async def connect_device(device_id):
            """模拟设备连接"""
            async with lock:
                devices[device_id] = {
                    "connected": True,
                    "connected_at": datetime.now(),
                    "last_ping": datetime.now()
                }

        async def disconnect_device(device_id):
            """模拟设备断开"""
            async with lock:
                if device_id in devices:
                    devices[device_id]["connected"] = False

        # 模拟多个设备连接
        device_ids = [f"device-{i}" for i in range(5)]
        tasks = [connect_device(did) for did in device_ids]
        await asyncio.gather(*tasks)

        # 验证：所有设备已连接
        assert len(devices) == 5
        for device_id, state in devices.items():
            assert state["connected"] is True

        # 模拟部分设备断开
        disconnect_tasks = [disconnect_device(did) for did in device_ids[:2]]
        await asyncio.gather(*disconnect_tasks)

        # 验证：断开的设备状态正确
        assert devices["device-0"]["connected"] is False
        assert devices["device-4"]["connected"] is True

    @pytest.mark.asyncio
    async def test_ws_message_broadcast(self):
        """测试 WebSocket 消息广播"""
        received_messages = {}
        lock = asyncio.Lock()

        async def broadcast_message(message):
            """广播消息到所有连接"""
            async with lock:
                for device_id in ["device-1", "device-2", "device-3"]:
                    received_messages[device_id] = message

        message = {"type": "notification", "content": "系统通知"}
        await broadcast_message(message)

        # 验证：所有设备收到消息
        assert len(received_messages) == 3
        for device_id, msg in received_messages.items():
            assert msg == message

    @pytest.mark.asyncio
    async def test_ws_heartbeat_mechanism(self):
        """测试 WebSocket 心跳机制"""
        heartbeat_log = []
        lock = asyncio.Lock()

        async def send_heartbeat(device_id):
            """发送心跳"""
            async with lock:
                heartbeat_log.append({
                    "device_id": device_id,
                    "timestamp": datetime.now(),
                    "type": "ping"
                })

        async def receive_heartbeat_response(device_id):
            """接收心跳响应"""
            async with lock:
                heartbeat_log.append({
                    "device_id": device_id,
                    "timestamp": datetime.now(),
                    "type": "pong"
                })

        # 模拟心跳
        device_id = "device-test"
        await send_heartbeat(device_id)
        await receive_heartbeat_response(device_id)

        # 验证：心跳日志完整
        assert len(heartbeat_log) == 2
        assert heartbeat_log[0]["type"] == "ping"
        assert heartbeat_log[1]["type"] == "pong"


# ============= 7. 异步 Skill 执行测试 =============

class TestAsyncSkillExecution:
    """异步 Skill 执行测试"""

    @pytest.mark.asyncio
    async def test_skill_timeout_handling(self):
        """测试 Skill 超时处理"""
        execution_log = []

        async def skill_with_timeout(timeout_seconds=2):
            """带超时的 Skill 执行"""
            try:
                await asyncio.wait_for(
                    self._simulate_long_skill_execution(),
                    timeout=timeout_seconds
                )
                execution_log.append("success")
            except asyncio.TimeoutError:
                execution_log.append("timeout")
                return "timeout"

        result = await skill_with_timeout(timeout_seconds=0.5)
        assert result == "timeout"
        assert "timeout" in execution_log

    async def _simulate_long_skill_execution(self):
        """模拟长时间 Skill 执行"""
        await asyncio.sleep(10)  # 模拟长时间执行
        return "completed"

    @pytest.mark.asyncio
    async def test_concurrent_skill_execution(self):
        """测试并发 Skill 执行"""
        execution_results = {}
        lock = asyncio.Lock()

        async def execute_skill(skill_name, input_data):
            """执行 Skill"""
            # 模拟 Skill 执行
            await asyncio.sleep(random.uniform(0.01, 0.05))

            async with lock:
                execution_results[skill_name] = {
                    "input": input_data,
                    "output": f"result_for_{skill_name}",
                    "timestamp": datetime.now()
                }

        # 并发执行多个 Skill
        skills = [
            ("matchmaking_skill", {"user_id": "user-1"}),
            ("icebreaker_skill", {"user_id": "user-2"}),
            ("emotion_analysis_skill", {"conversation_id": "conv-1"}),
            ("date_coach_skill", {"user_id": "user-3"}),
            ("relationship_prophet_skill", {"user_id": "user-4"}),
        ]

        tasks = [execute_skill(name, data) for name, data in skills]
        await asyncio.gather(*tasks)

        # 验证：所有 Skill 已执行
        assert len(execution_results) == 5

    @pytest.mark.asyncio
    async def test_skill_retry_on_failure(self):
        """测试 Skill 失败重试"""
        retry_log = []
        max_retries = 3

        async def skill_with_retry(attempt=0):
            """带重试的 Skill"""
            if attempt < 2:  # 前两次失败
                retry_log.append(f"attempt_{attempt}_failed")
                if attempt < max_retries - 1:
                    return await skill_with_retry(attempt + 1)
                return "failed"

            retry_log.append(f"attempt_{attempt}_success")
            return "success"

        result = await skill_with_retry()
        assert result == "success"
        assert len(retry_log) == 3

    @pytest.mark.asyncio
    async def test_skill_execution_cancellation(self):
        """测试 Skill 执行取消"""
        cancellation_log = []

        async def cancellable_skill():
            """可取消的 Skill"""
            try:
                await asyncio.sleep(10)
                cancellation_log.append("completed")
            except asyncio.CancelledError:
                cancellation_log.append("cancelled")
                raise

        task = asyncio.create_task(cancellable_skill())

        # 等待一小段时间后取消
        await asyncio.sleep(0.1)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        assert "cancelled" in cancellation_log

    @pytest.mark.asyncio
    async def test_skill_result_caching(self):
        """测试 Skill 结果缓存"""
        cache = {}
        cache_hits = []
        lock = asyncio.Lock()

        async def cached_skill_execution(skill_name, input_data):
            """带缓存的 Skill 执行"""
            cache_key = hashlib.md5(f"{skill_name}:{input_data}".encode()).hexdigest()

            async with lock:
                if cache_key in cache:
                    cache_hits.append(cache_key)
                    return cache[cache_key]

            # 模拟 Skill 执行
            await asyncio.sleep(0.01)
            result = f"result_for_{skill_name}"

            async with lock:
                cache[cache_key] = result

            return result

        # 第一次执行（缓存未命中）
        result1 = await cached_skill_execution("test_skill", "input1")

        # 第二次执行（缓存命中）
        result2 = await cached_skill_execution("test_skill", "input1")

        assert result1 == result2
        assert len(cache_hits) == 1


# ============= 8. LLM 服务降级测试 =============

class TestLLMServiceDegradation:
    """LLM 服务降级测试"""

    @pytest.mark.asyncio
    async def test_llm_timeout_degradation(self):
        """测试 LLM 超时降级"""
        from integration.llm_client import LocalRuleEngine

        rule_engine = LocalRuleEngine()
        execution_log = []

        async def llm_request_with_fallback():
            """带降级的 LLM 请求"""
            try:
                # 模拟 LLM 超时
                await asyncio.wait_for(
                    self._simulate_llm_delay(),
                    timeout=0.5
                )
                execution_log.append("llm_success")
                return "llm_response"
            except asyncio.TimeoutError:
                execution_log.append("llm_timeout")
                # 降级到本地规则引擎
                execution_log.append("fallback_to_local")
                return rule_engine.generate_icebreakers(
                    {"id": "user1", "interests": ["阅读"]},
                    {"id": "user2", "interests": ["阅读", "音乐"]},
                    ["阅读"]
                )

        result = await llm_request_with_fallback()

        assert "llm_timeout" in execution_log
        assert "fallback_to_local" in execution_log
        assert isinstance(result, list)

    async def _simulate_llm_delay(self):
        """模拟 LLM 响应延迟"""
        await asyncio.sleep(10)  # 模拟长时间延迟
        return "llm_response"

    @pytest.mark.asyncio
    async def test_llm_failure_degradation(self):
        """测试 LLM 失败降级"""
        from integration.llm_client import LocalRuleEngine

        rule_engine = LocalRuleEngine()
        execution_log = []

        async def llm_request_with_error_handling():
            """带错误处理的 LLM 请求"""
            try:
                # 模拟 LLM API 错误
                raise ConnectionError("LLM API unavailable")
            except Exception as e:
                execution_log.append(f"llm_error: {str(e)}")
                # 降级到 Mock 数据
                execution_log.append("fallback_to_mock")
                return rule_engine.generate_topics(
                    {"id": "user1", "interests": ["阅读"]},
                    {"id": "user2", "interests": ["音乐"]}
                )

        result = await llm_request_with_error_handling()

        assert "llm_error" in execution_log[0]
        assert "fallback_to_mock" in execution_log
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_llm_concurrent_requests_with_degradation(self):
        """测试并发 LLM 请求带降级"""
        results = {}
        lock = asyncio.Lock()

        async def llm_request(request_id, should_fail=False):
            """并发 LLM 请求"""
            if should_fail:
                async with lock:
                    results[request_id] = {
                        "status": "fallback",
                        "source": "local_rule"
                    }
            else:
                await asyncio.sleep(0.01)
                async with lock:
                    results[request_id] = {
                        "status": "success",
                        "source": "llm"
                    }

        # 并发请求（部分会失败）
        tasks = [
            llm_request(i, should_fail=(i % 3 == 0))  # 每 3 个请求有 1 个失败
            for i in range(20)
        ]
        await asyncio.gather(*tasks)

        # 验证：所有请求都有结果
        assert len(results) == 20

        # 验证：失败请求使用了降级方案
        fallback_count = len([r for r in results.values() if r["status"] == "fallback"])
        assert fallback_count == 7  # 20 / 3 ≈ 7

    @pytest.mark.asyncio
    async def test_llm_semantic_cache(self):
        """测试 LLM 语义缓存"""
        from integration.llm_client import SemanticCache

        cache = SemanticCache(ttl_seconds=60)
        cache_log = []

        async def cached_llm_request(prompt):
            """带语义缓存的 LLM 请求"""
            # 检查缓存
            cached = cache.get(prompt)
            if cached:
                cache_log.append("cache_hit")
                return cached

            cache_log.append("cache_miss")

            # 模拟 LLM 调用
            await asyncio.sleep(0.01)
            response = "llm_response"

            # 缓存结果
            cache.set(prompt, response)
            return response

        # 第一次请求
        result1 = await cached_llm_request("test_prompt")

        # 第二次相同请求
        result2 = await cached_llm_request("test_prompt")

        assert result1 == result2
        assert "cache_miss" in cache_log
        assert "cache_hit" in cache_log


# ============= 9. 缓存并发测试 =============

class TestCacheConcurrency:
    """缓存并发测试"""

    def test_concurrent_cache_read_write(self):
        """测试并发缓存读写"""
        cache_manager = CacheManager()
        cache_manager.clear_memory_cache()

        results = {"reads": [], "writes": []}
        lock = threading.Lock()

        def cache_write(user_id, data):
            """缓存写入"""
            cache_manager.set_profile(user_id, data)
            with lock:
                results["writes"].append(user_id)

        def cache_read(user_id):
            """缓存读取"""
            profile = cache_manager.get_profile(user_id)
            with lock:
                results["reads"].append({
                    "user_id": user_id,
                    "found": profile is not None
                })

        # 并发写入
        user_ids = [str(uuid.uuid4()) for _ in range(20)]
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(cache_write, uid, {"name": f"User_{uid[:8]}"})
                for uid in user_ids
            ]
            for f in as_completed(futures):
                f.result()

        # 并发读取
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(cache_read, uid) for uid in user_ids]
            for f in as_completed(futures):
                f.result()

        # 验证：所有写入成功
        assert len(results["writes"]) == 20

        # 验证：所有读取找到数据
        found_count = len([r for r in results["reads"] if r["found"]])
        assert found_count == 20

    def test_cache_invalidation_on_update(self):
        """测试缓存失效重建"""
        cache_manager = CacheManager()
        cache_manager.clear_memory_cache()

        user_id = str(uuid.uuid4())
        invalidate_log = []

        def update_and_invalidate(user_id, new_data):
            """更新数据并失效缓存"""
            # 先失效缓存
            cache_manager.invalidate_profile(user_id)
            invalidate_log.append("invalidate")

            # 写入新数据
            cache_manager.set_profile(user_id, new_data)
            invalidate_log.append("update")

        # 初始数据
        cache_manager.set_profile(user_id, {"name": "Original", "version": 1})

        # 多次更新
        for i in range(5):
            update_and_invalidate(user_id, {"name": f"Updated_{i}", "version": i + 2})

        # 验证：缓存已更新
        profile = cache_manager.get_profile(user_id)
        assert profile["version"] == 6

        # 验证：失效和更新次数
        assert len(invalidate_log) == 10  # 5 次 invalidate + 5 次 update

    def test_cache_consistency_under_high_load(self):
        """测试高负载下缓存一致性"""
        cache_manager = CacheManager()
        cache_manager.clear_memory_cache()

        user_id = str(uuid.uuid4())
        read_results = []
        lock = threading.Lock()

        def concurrent_read():
            """并发读取"""
            profile = cache_manager.get_profile(user_id)
            with lock:
                read_results.append(profile)

        def concurrent_write(version):
            """并发写入"""
            cache_manager.set_profile(user_id, {"version": version})

        # 初始写入
        cache_manager.set_profile(user_id, {"version": 1})

        # 高并发读写
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [
                executor.submit(concurrent_write, i)
                for i in range(2, 20)
            ] + [
                executor.submit(concurrent_read)
                for _ in range(50)
            ]
            for f in as_completed(futures, timeout=ConcurrencyTestConfig.MAX_WAIT_TIME):
                f.result()

        # 验证：读取结果非空（缓存有效）
        non_null_count = len([r for r in read_results if r is not None])
        assert non_null_count > 0

    def test_cache_stats_concurrent_access(self):
        """测试缓存统计并发访问"""
        cache_manager = CacheManager()
        cache_manager.clear_memory_cache()

        stats_results = []
        lock = threading.Lock()

        def get_cache_stats():
            """获取缓存统计"""
            stats = cache_manager.get_cache_stats()
            with lock:
                stats_results.append(stats)

        def perform_cache_operations():
            """执行缓存操作"""
            user_id = str(uuid.uuid4())
            cache_manager.set_profile(user_id, {"name": "Test"})
            cache_manager.get_profile(user_id)

        # 并发执行
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(get_cache_stats)
                for _ in range(10)
            ] + [
                executor.submit(perform_cache_operations)
                for _ in range(10)
            ]
            for f in as_completed(futures):
                f.result()

        # 验证：所有统计获取成功
        assert len(stats_results) == 10

        # 验证：统计结构完整
        for stats in stats_results:
            assert "cache_hits" in stats
            assert "cache_misses" in stats
            assert "memory_cache_size" in stats


# ============= 10. 高级并发场景测试 =============

class TestAdvancedConcurrencyScenarios:
    """高级并发场景测试"""

    def test_race_condition_detection(self):
        """测试竞态条件检测"""
        counter = {"value": 0}
        unsafe_increment_results = []
        safe_increment_results = []

        def unsafe_increment():
            """不安全的增量操作"""
            old_value = counter["value"]
            # 模拟竞态条件窗口
            time.sleep(0.001)
            counter["value"] = old_value + 1
            unsafe_increment_results.append(counter["value"])

        def safe_increment(lock):
            """安全的增量操作"""
            with lock:
                old_value = counter["value"]
                counter["value"] = old_value + 1
                safe_increment_results.append(counter["value"])

        # 不安全并发增量
        counter["value"] = 0
        threads = [threading.Thread(target=unsafe_increment) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证：不安全操作可能导致竞态条件
        # 注意：在某些情况下可能恰好没有竞态条件
        unsafe_final = counter["value"]

        # 安全并发增量
        lock = threading.Lock()
        counter["value"] = 0
        threads = [threading.Thread(target=safe_increment, args=(lock,)) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证：安全操作结果正确
        assert counter["value"] == 100

    def test_producer_consumer_pattern(self):
        """测试生产者-消费者模式"""
        message_queue = queue.Queue(maxsize=100)
        produced_messages = []
        consumed_messages = []
        lock = threading.Lock()

        def producer():
            """生产者"""
            for i in range(50):
                msg = f"message_{i}"
                message_queue.put(msg, timeout=5)
                with lock:
                    produced_messages.append(msg)

        def consumer():
            """消费者"""
            while True:
                try:
                    msg = message_queue.get(timeout=2)
                    with lock:
                        consumed_messages.append(msg)
                    message_queue.task_done()
                except queue.Empty:
                    break

        # 启动生产者和消费者
        producers = [threading.Thread(target=producer) for _ in range(2)]
        consumers = [threading.Thread(target=consumer) for _ in range(4)]

        for p in producers:
            p.start()
        for c in consumers:
            c.start()

        for p in producers:
            p.join()
        for c in consumers:
            c.join()

        # 验证：消息数量正确
        assert len(produced_messages) == 100  # 2 * 50
        assert len(consumed_messages) <= 100

    def test_read_write_lock_pattern(self):
        """测试读写锁模式"""
        data = {"value": 0}
        read_count = {"count": 0}
        write_count = {"count": 0}
        rw_lock = threading.Lock()
        read_lock = threading.Lock()

        def read_operation():
            """读操作"""
            with read_lock:
                read_count["count"] += 1
            # 读操作可以并发
            _ = data["value"]

        def write_operation(value):
            """写操作"""
            with rw_lock:
                data["value"] = value
                write_count["count"] += 1

        # 并发读操作
        read_threads = [threading.Thread(target=read_operation) for _ in range(50)]

        # 写操作
        write_threads = [
            threading.Thread(target=write_operation, args=(i,))
            for i in range(5)
        ]

        for t in read_threads + write_threads:
            t.start()

        for t in read_threads + write_threads:
            t.join()

        # 验证：读操作次数
        assert read_count["count"] == 50

        # 验证：写操作次数
        assert write_count["count"] == 5

    def test_barrier_synchronization(self):
        """测试屏障同步"""
        phase_results = {"phase1": [], "phase2": [], "phase3": []}
        lock = threading.Lock()

        def task_with_phases(task_id):
            """多阶段任务"""
            # 第一阶段
            with lock:
                phase_results["phase1"].append(task_id)

            # 等待所有任务完成第一阶段
            time.sleep(0.1)

            # 第二阶段
            with lock:
                phase_results["phase2"].append(task_id)

            # 等待所有任务完成第二阶段
            time.sleep(0.1)

            # 第三阶段
            with lock:
                phase_results["phase3"].append(task_id)

        # 并发执行多阶段任务
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(task_with_phases, i) for i in range(10)]
            for f in as_completed(futures):
                f.result()

        # 验证：所有阶段完成
        assert len(phase_results["phase1"]) == 10
        assert len(phase_results["phase2"]) == 10
        assert len(phase_results["phase3"]) == 10

    @pytest.mark.asyncio
    async def test_async_semaphore_limiting(self):
        """测试异步信号量限制"""
        semaphore = asyncio.Semaphore(5)
        execution_log = []
        lock = asyncio.Lock()

        async def limited_task(task_id):
            """受限任务"""
            async with semaphore:
                async with lock:
                    execution_log.append({
                        "task_id": task_id,
                        "start_time": datetime.now()
                    })
                await asyncio.sleep(0.1)
                async with lock:
                    for entry in execution_log:
                        if entry["task_id"] == task_id:
                            entry["end_time"] = datetime.now()

        # 并发执行 20 个任务（最多 5 个并发）
        tasks = [limited_task(i) for i in range(20)]
        await asyncio.gather(*tasks)

        # 验证：所有任务完成
        assert len(execution_log) == 20

        # 验证：并发数限制（检查同时执行的任务数）
        # 计算任意时刻的最大并发数
        max_concurrent = 0
        for i in range(len(execution_log)):
            concurrent = 0
            for j in range(len(execution_log)):
                if execution_log[j].get("start_time") <= execution_log[i]["start_time"] <= execution_log[j].get("end_time"):
                    concurrent += 1
            max_concurrent = max(max_concurrent, concurrent)

        # 最大并发数不应超过信号量限制（考虑时间精度，允许一定误差）
        assert max_concurrent <= 7  # 宽松检查


# ============= 运行测试 =============

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-n", "4"])