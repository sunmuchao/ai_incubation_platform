"""
批量生成模拟测试用户数据（优化版）

支持大规模数据生成（1万+用户）
使用批量插入提高性能
"""
import random
import json
import uuid
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any
import sys

# 直接导入，避免模块问题
sys.path.insert(0, '/Users/sunmuchao/Downloads/ai_incubation_platform/Her/src')

from db.database import engine, Base
from db.models import (
    UserDB,
    UserVectorProfileDB,
    UserSocialMetricsDB,
    SwipeActionDB,
    UserFeedbackLearningDB,
)
from sqlalchemy.orm import sessionmaker

Session = sessionmaker(bind=engine)


# ==================== 模拟数据配置 ====================

CITIES = {
    "tier1": ["北京", "上海", "广州", "深圳"],
    "tier2": ["杭州", "南京", "苏州", "成都", "武汉", "西安", "重庆", "天津"],
    "tier3": ["青岛", "厦门", "长沙", "郑州", "福州", "昆明", "大连", "宁波", "合肥", "石家庄", "太原", "南昌"],
}

RELATIONSHIP_GOALS = ["serious", "marriage", "dating", "casual"]
DISLIKE_REASONS = ["age_not_match", "location_far", "not_my_type", "photo_concern", "bio_issue"]

INTERESTS = [
    "旅行", "美食", "摄影", "健身", "阅读", "电影", "音乐", "游戏",
    "烹饪", "徒步", "瑜伽", "宠物", "咖啡", "穿搭", "科技", "艺术",
    "跑步", "游泳", "骑行", "登山", "露营", "钓鱼", "滑雪", "冲浪",
    "绘画", "书法", "舞蹈", "乐器", "写作", "编程", "投资", "理财",
]

OCCUPATIONS = [
    "互联网/IT", "金融", "教育", "医疗", "法律", "媒体/广告", "制造业", "服务业",
    "自由职业", "学生", "公务员", "创业", "建筑师", "设计师", "工程师", "销售",
    "人力资源", "行政", "财务", "运营", "市场", "产品", "技术", "管理",
]

EDUCATIONS = ["高中", "大专", "本科", "硕士", "博士"]

MALE_NAMES = [
    "张伟", "李强", "王鹏", "刘洋", "陈浩", "杨帆", "赵磊", "周明",
    "吴涛", "郑凯", "孙旭", "马超", "朱辉", "胡斌", "林峰", "何晨",
    "郭建", "罗杰", "梁宇", "谢云", "唐俊", "韩磊", "曹阳", "冯威",
    "陆毅", "袁杰", "邓超", "许峰", "傅雷", "沈涛", "曾伟", "彭浩",
    "卢斌", "蒋涛", "蔡杰", "贾峰", "丁伟", "魏强", "薛磊", "叶峰",
    "阎斌", "余晨", "潘涛", "杜杰", "戴峰", "夏伟", "钟强", "汪磊",
    "田峰", "任杰", "姜涛", "范伟", "方磊", "石峰", "姚涛", "谭杰",
    "廖伟", "邹磊", "熊峰", "金涛", "陆杰", "郝伟", "孔磊", "白峰",
]

FEMALE_NAMES = [
    "张婷", "李娜", "王丽", "刘芳", "陈静", "杨雪", "赵敏", "周莹",
    "吴倩", "郑悦", "孙琪", "马琳", "朱洁", "胡颖", "林雨", "何欣",
    "郭蕾", "罗瑶", "梁瑶", "谢婷", "唐燕", "韩雪", "曹悦", "冯琳",
    "陆瑶", "袁婷", "邓悦", "许琳", "傅雪", "沈婷", "曾娜", "彭悦",
    "卢洁", "蒋悦", "蔡琳", "贾婷", "丁雪", "魏瑶", "薛悦", "叶婷",
    "阎琳", "余悦", "潘洁", "杜婷", "戴雪", "夏瑶", "钟悦", "汪婷",
    "田洁", "任悦", "姜婷", "范雪", "方瑶", "石悦", "姚婷", "谭雪",
    "廖瑶", "邹悦", "熊婷", "金洁", "陆瑶", "郝雪", "孔悦", "白婷",
]

AVATAR_BASE = "https://api.dicebear.com/7.x/avataaars/svg?seed="


# ==================== 批量生成函数 ====================

def generate_users_batch(batch_size: int, start_index: int) -> List[Dict]:
    """批量生成用户数据"""
    users = []

    for i in range(start_index, start_index + batch_size):
        gender = random.choice(["male", "female"])
        city_tier_type = random.choices(["tier1", "tier2", "tier3"], weights=[35, 40, 25])[0]
        city = random.choice(CITIES[city_tier_type])
        city_tier = 1 if city_tier_type == "tier1" else (2 if city_tier_type == "tier2" else 3)

        name = random.choice(MALE_NAMES if gender == "male" else FEMALE_NAMES)
        # 添加随机后缀避免名字重复
        if random.random() > 0.7:
            name = name + random.choice(["啊", "哦", "呢", "呀", "哈"])

        age = random.randint(22, 45)

        user_data = {
            "id": f"user_{i:05d}",
            "name": name,
            "gender": gender,
            "age": age,
            "city": city,
            "city_tier": city_tier,
            "relationship_goal": random.choice(RELATIONSHIP_GOALS),
            "occupation": random.choice(OCCUPATIONS),
            "education": random.choice(EDUCATIONS),
            "interests": random.sample(INTERESTS, random.randint(3, 8)),
        }
        users.append(user_data)

    return users


def generate_vector(user_data: Dict) -> np.ndarray:
    """生成144维向量"""
    vector = np.zeros(144)

    # 人口统计学
    vector[0] = user_data["age"] / 100
    vector[1] = max(18, user_data["age"] - random.randint(3, 10)) / 100
    vector[2] = min(60, user_data["age"] + random.randint(3, 10)) / 100
    vector[3] = 0.0 if user_data["gender"] == "male" else 1.0
    vector[4] = 0.0
    vector[5] = 1.0 if user_data["gender"] == "male" else 0.0
    vector[6] = user_data["city_tier"] / 3
    vector[7] = random.uniform(0.3, 0.7)

    # 其他维度随机填充
    for i in range(8, 144):
        vector[i] = random.uniform(0.2, 0.9)

    return vector


def generate_bio(user_data: Dict) -> str:
    """生成简介"""
    templates = [
        f"{user_data['occupation']}，{user_data['education']}学历，喜欢{random.choice(user_data['interests'][:3])}。",
        f"{user_data['age']}岁，生活在{user_data['city']}，希望找到志同道合的人。",
        f"热爱{random.choice(user_data['interests'])}和{random.choice(user_data['interests'])}，期待和你分享生活。",
        f"在{user_data['city']}工作，{user_data['occupation']}行业，寻找认真交往的伴侣。",
        f"性格{random.choice(['开朗', '温和', '稳重', '活泼'])}，喜欢{random.choice(user_data['interests'])}。",
    ]

    extras = [
        "周末喜欢户外活动。",
        "是个吃货，喜欢探索美食。",
        "喜欢安静的生活。",
        "热爱旅行，去过很多地方。",
        "",
    ]

    base = random.choice(templates)
    extra = random.choice(extras)
    return f"{base} {extra}" if extra else base


def batch_insert_users(users_data: List[Dict], session) -> int:
    """批量插入用户"""
    user_objects = []
    vector_objects = []
    metrics_objects = []

    for user_data in users_data:
        # 用户对象
        user = UserDB(
            id=user_data["id"],
            name=user_data["name"],
            email=f"{user_data['id']}@mock.her.app",
            password_hash="mock_password",
            gender=user_data["gender"],
            age=user_data["age"],
            location=user_data["city"],
            relationship_goal=user_data["relationship_goal"],
            bio=generate_bio(user_data),
            interests=json.dumps(user_data["interests"]),
            avatar_url=f"{AVATAR_BASE}{user_data['id']}_{user_data['gender']}",
            is_active=True,
            created_at=datetime.now() - timedelta(days=random.randint(1, 90))
        )
        user_objects.append(user)

        # 向量对象
        vector = generate_vector(user_data)
        completeness = np.count_nonzero(vector) / 144
        vector_obj = UserVectorProfileDB(
            id=str(uuid.uuid4()),
            user_id=user_data["id"],
            vector=json.dumps(vector.tolist()),
            completeness_ratio=completeness,
            recommended_strategy="vector" if completeness > 0.6 else "basic",
            dimensions_detail=json.dumps({
                "interests": user_data["interests"][:4],
                "city_tier": user_data["city_tier"],
            }),
            created_at=datetime.now()
        )
        vector_objects.append(vector_obj)

        # 社交指标（70%用户有）
        if random.random() > 0.3:
            like_count = random.randint(10, 200)
            dislike_count = random.randint(0, 30)
            total = like_count + dislike_count + random.randint(5, 50)
            like_rate = like_count / total

            metrics_obj = UserSocialMetricsDB(
                id=str(uuid.uuid4()),
                user_id=user_data["id"],
                like_count=like_count,
                dislike_count=dislike_count,
                pass_count=random.randint(10, 100),
                like_rate=like_rate,
                chat_response_rate=random.uniform(0.4, 0.95),
                success_match_count=random.randint(0, 15),
                reputation_score=like_rate * 100,
                last_calculated_at=datetime.now()
            )
            metrics_objects.append(metrics_obj)

    # 批量插入
    session.bulk_save_objects(user_objects)
    session.bulk_save_objects(vector_objects)
    session.bulk_save_objects(metrics_objects)

    return len(user_objects)


def batch_insert_swipes(user_ids: List[str], user_genders: Dict, session) -> int:
    """批量插入滑动记录"""
    swipe_objects = []
    feedback_objects = []

    # 每个用户滑动 10-30 次
    for user_id in user_ids:
        gender = user_genders.get(user_id, "male")
        opposite_gender = "female" if gender == "male" else "male"

        targets = [u for u in user_ids if user_genders.get(u) == opposite_gender and u != user_id]
        if not targets:
            continue

        swipe_count = random.randint(10, 30)
        selected_targets = random.sample(targets, min(swipe_count, len(targets)))

        for target_id in selected_targets:
            action = random.choices(["like", "pass", "super_like"], weights=[35, 55, 10])[0]

            swipe = SwipeActionDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                target_user_id=target_id,
                action=action,
                is_matched=action == "like" and random.random() > 0.9,
                created_at=datetime.now() - timedelta(hours=random.randint(1, 200))
            )
            swipe_objects.append(swipe)

            # 25% 的 pass 添加反馈
            if action == "pass" and random.random() > 0.75:
                feedback = UserFeedbackLearningDB(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    feedback_type="dislike",
                    target_match_id=target_id,
                    dislike_reason=random.choice(DISLIKE_REASONS),
                    confidence_score=random.uniform(0.4, 0.9),
                    created_at=datetime.now() - timedelta(hours=random.randint(1, 100))
                )
                feedback_objects.append(feedback)

    session.bulk_save_objects(swipe_objects)
    session.bulk_save_objects(feedback_objects)

    return len(swipe_objects), len(feedback_objects)


def main():
    """主函数"""
    TARGET_COUNT = 10000
    BATCH_SIZE = 500

    print("=" * 60)
    print(f"批量生成 {TARGET_COUNT} 个模拟用户")
    print("=" * 60)

    # 初始化数据库
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表已就绪")

    session = Session()

    try:
        # 分批生成用户
        total_users = 0
        total_batches = TARGET_COUNT // BATCH_SIZE

        print(f"\n生成用户数据（{total_batches} 批次）...")

        for batch_idx in range(total_batches):
            start_index = batch_idx * BATCH_SIZE
            users_data = generate_users_batch(BATCH_SIZE, start_index)
            count = batch_insert_users(users_data, session)
            total_users += count

            # 每5批提交一次
            if (batch_idx + 1) % 5 == 0:
                session.commit()
                print(f"  批次 {batch_idx + 1}/{total_batches} 完成，累计 {total_users} 用户")

        # 最后提交
        session.commit()
        print(f"\n✅ 用户数据生成完成: {total_users} 个用户")

        # 收集用户信息用于生成交互
        users = session.query(UserDB).filter(UserDB.id.like('user_%')).all()
        user_ids = [u.id for u in users]
        user_genders = {u.id: u.gender for u in users}

        print(f"\n生成交互数据...")
        swipe_count, feedback_count = batch_insert_swipes(user_ids, user_genders, session)
        session.commit()

        print(f"✅ 滑动记录: {swipe_count} 条")
        print(f"✅ 反馈记录: {feedback_count} 条")

        # 最终统计
        print("\n" + "=" * 60)
        print("📊 最终统计")
        print("=" * 60)

        male_count = session.query(UserDB).filter(UserDB.gender == "male").count()
        female_count = session.query(UserDB).filter(UserDB.gender == "female").count()
        vector_count = session.query(UserVectorProfileDB).count()
        metrics_count = session.query(UserSocialMetricsDB).count()
        swipe_total = session.query(SwipeActionDB).count()
        feedback_total = session.query(UserFeedbackLearningDB).count()

        print(f"总用户数: {total_users}")
        print(f"男性用户: {male_count}")
        print(f"女性用户: {female_count}")
        print(f"向量画像: {vector_count}")
        print(f"社交指标: {metrics_count}")
        print(f"滑动记录: {swipe_total}")
        print(f"反馈记录: {feedback_total}")

        # 城市分布
        print("\n城市分布:")
        for tier_type, cities in CITIES.items():
            count = sum(1 for u in users if u.location in cities)
            print(f"  {tier_type}: {count} 用户")

        # 关系目标分布
        print("\n关系目标分布:")
        for goal in RELATIONSHIP_GOALS:
            count = session.query(UserDB).filter(UserDB.relationship_goal == goal).count()
            print(f"  {goal}: {count} 用户")

        print("\n✅ 模拟数据生成完成!")

    except Exception as e:
        session.rollback()
        print(f"❌ 错误: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()