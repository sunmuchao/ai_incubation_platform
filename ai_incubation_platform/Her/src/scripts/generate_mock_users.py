"""
生成模拟测试用户数据

用于测试渐进式智能匹配系统功能
"""
import asyncio
import random
import json
import uuid
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any

from db.database import init_db
from db.models import (
    UserDB,
    UserVectorProfileDB,
    UserSocialMetricsDB,
    QuickStartRecordDB,
    UserFeedbackLearningDB,
    SwipeActionDB,
)
from utils.db_session_manager import db_session
from utils.logger import logger


# ==================== 模拟数据配置 ====================

# 城市列表（按层级）
CITIES = {
    "tier1": ["北京", "上海", "广州", "深圳"],
    "tier2": ["杭州", "南京", "苏州", "成都", "武汉", "西安", "重庆", "天津"],
    "tier3": ["青岛", "厦门", "长沙", "郑州", "福州", "昆明", "大连", "宁波"],
}

# 关系目标
RELATIONSHIP_GOALS = ["serious", "marriage", "dating", "casual"]

# 不喜欢原因
DISLIKE_REASONS = ["age_not_match", "location_far", "not_my_type", "photo_concern", "bio_issue"]

# 兴趣标签
INTERESTS = [
    "旅行", "美食", "摄影", "健身", "阅读", "电影", "音乐", "游戏",
    "烹饪", "徒步", "瑜伽", "宠物", "咖啡", "穿搭", "科技", "艺术"
]

# 职业类型
OCCUPATIONS = [
    "互联网/IT", "金融", "教育", "医疗", "法律", "媒体/广告", "制造业", "服务业",
    "自由职业", "学生", "公务员", "创业"
]

# 学历
EDUCATIONS = ["高中", "大专", "本科", "硕士", "博士"]


# ==================== 名字生成 ====================

MALE_NAMES = [
    "张伟", "李强", "王鹏", "刘洋", "陈浩", "杨帆", "赵磊", "周明",
    "吴涛", "郑凯", "孙旭", "马超", "朱辉", "胡斌", "林峰", "何晨",
    "郭建", "罗杰", "梁宇", "谢云", "唐俊", "韩磊", "曹阳", "冯威"
]

FEMALE_NAMES = [
    "张婷", "李娜", "王丽", "刘芳", "陈静", "杨雪", "赵敏", "周莹",
    "吴倩", "郑悦", "孙琪", "马琳", "朱洁", "胡颖", "林雨", "何欣",
    "郭蕾", "罗瑶", "梁瑶", "谢婷", "唐燕", "韩雪", "曹悦", "冯琳"
]

# 模拟头像（使用占位符服务）
AVATAR_BASE = "https://api.dicebear.com/7.x/avataaars/svg?seed="


def generate_user_id(index: int) -> str:
    """生成用户ID"""
    return f"user_{index:04d}"


def generate_avatar_url(user_id: str, gender: str) -> str:
    """生成头像URL"""
    # 使用 DiceBear 服务生成随机头像
    seed = f"{user_id}_{gender}"
    return f"{AVATAR_BASE}{seed}"


def generate_user_vector(user_data: Dict) -> np.ndarray:
    """
    生成144维用户向量

    向量结构：
    - v0-v9: 人口统计学（年龄、性别、位置）
    - v10-v31: 价值观
    - v32-v47: 性格（大五人格）
    - v48-v63: 依恋类型
    - v64-v71: 成长偏好
    - v72-v87: 兴趣
    - v88-v103: 生活习惯
    - v104-v119: 行为特征
    - v120-v135: 沟通风格
    - v136-v143: 隐性推断
    """
    vector = np.zeros(144)

    # v0: 年龄归一化
    vector[0] = user_data["age"] / 100

    # v1-v2: 年龄偏好范围
    age_pref_min = max(18, user_data["age"] - random.randint(3, 8))
    age_pref_max = min(60, user_data["age"] + random.randint(3, 8))
    vector[1] = age_pref_min / 100
    vector[2] = age_pref_max / 100

    # v3: 性别编码
    vector[3] = 0.0 if user_data["gender"] == "male" else 1.0

    # v4: 性取向（默认异性）
    vector[4] = 0.0

    # v5: 性别偏好（异性）
    vector[5] = 1.0 if user_data["gender"] == "male" else 0.0

    # v6-v9: 地理编码
    city_tier = user_data.get("city_tier", 1)
    vector[6] = city_tier / 3  # 城市层级
    vector[7] = random.uniform(0.3, 0.8)  # 是否接受异地

    # v10-v31: 价值观（随机填充）
    for i in range(10, 32):
        vector[i] = random.uniform(0.3, 0.9)

    # v32-v47: 大五人格
    # 基于性别和年龄稍微调整
    if user_data["gender"] == "female":
        vector[40] = random.uniform(0.5, 0.9)  # 外向性（女性偏高）
        vector[42] = random.uniform(0.5, 0.85)  # 宜人性
    else:
        vector[40] = random.uniform(0.3, 0.7)
        vector[42] = random.uniform(0.3, 0.7)

    for i in range(32, 48):
        if vector[i] == 0:
            vector[i] = random.uniform(0.3, 0.8)

    # v48-v63: 依恋类型（随机）
    attachment_type = random.choice(["secure", "anxious", "avoidant", "mixed"])
    if attachment_type == "secure":
        vector[48] = 0.8
    elif attachment_type == "anxious":
        vector[50] = 0.7
    elif attachment_type == "avoidant":
        vector[52] = 0.7
    else:
        vector[48] = 0.4
        vector[50] = 0.4

    for i in range(48, 64):
        if vector[i] == 0:
            vector[i] = random.uniform(0.3, 0.7)

    # v64-v71: 成长偏好
    for i in range(64, 72):
        vector[i] = random.uniform(0.3, 0.8)

    # v72-v87: 兴趣（基于用户兴趣列表）
    for i in range(72, 88):
        vector[i] = random.choice([0.0, 0.5, 0.8, 1.0])

    # v88-v103: 生活习惯
    for i in range(88, 104):
        vector[i] = random.uniform(0.2, 0.8)

    # v104-v119: 行为特征
    for i in range(104, 120):
        vector[i] = random.uniform(0.2, 0.7)

    # v120-v135: 沟通风格
    for i in range(120, 136):
        vector[i] = random.uniform(0.3, 0.8)

    # v136-v143: 隐性推断（初始为低置信度）
    for i in range(136, 144):
        vector[i] = random.uniform(0.2, 0.5)

    return vector


def generate_bio(user_data: Dict) -> str:
    """生成简介"""
    templates = [
        f"我是{user_data['name']}，{user_data['occupation']}，喜欢{random.choice(user_data['interests'][:3])}。",
        f"{user_data['age']}岁，{user_data['city']}人，希望找到志同道合的人。",
        f"平时喜欢{random.choice(user_data['interests'])}，期待和你聊聊。",
        f"在{user_data['city']}生活，{user_data['education']}学历，寻找认真交往的伴侣。",
    ]

    extra = random.choice([
        "性格比较随和，喜欢安静的生活。",
        "热爱生活，喜欢尝试新鲜事物。",
        "工作之余喜欢健身和看书。",
        "是个吃货，喜欢探索美食。",
        "",
    ])

    base = random.choice(templates)
    if extra:
        return f"{base} {extra}"
    return base


async def create_mock_users(count: int = 50) -> List[str]:
    """
    创建模拟用户

    Args:
        count: 创建用户数量

    Returns:
        创建的用户ID列表
    """
    logger.info(f"开始创建 {count} 个模拟用户...")

    user_ids = []

    # 生成用户数据
    users_data = []
    for i in range(count):
        gender = random.choice(["male", "female"])
        city_tier_type = random.choices(["tier1", "tier2", "tier3"], weights=[40, 35, 25])[0]
        city = random.choice(CITIES[city_tier_type])
        city_tier = 1 if city_tier_type == "tier1" else (2 if city_tier_type == "tier2" else 3)

        name = random.choice(MALE_NAMES if gender == "male" else FEMALE_NAMES)
        age = random.randint(22, 40)

        user_data = {
            "id": generate_user_id(i),
            "name": name,
            "gender": gender,
            "age": age,
            "city": city,
            "city_tier": city_tier,
            "relationship_goal": random.choice(RELATIONSHIP_GOALS),
            "occupation": random.choice(OCCUPATIONS),
            "education": random.choice(EDUCATIONS),
            "interests": random.sample(INTERESTS, random.randint(3, 6)),
        }

        users_data.append(user_data)
        user_ids.append(user_data["id"])

    # 写入数据库
    with db_session() as db:
        for user_data in users_data:
            # 创建用户
            user = UserDB(
                id=user_data["id"],
                name=user_data["name"],
                email=f"{user_data['id']}@test.her.app",
                password_hash="test_password_hash",
                gender=user_data["gender"],
                age=user_data["age"],
                location=user_data["city"],
                relationship_goal=user_data["relationship_goal"],
                bio=generate_bio(user_data),
                interests=json.dumps(user_data["interests"]),
                avatar_url=generate_avatar_url(user_data["id"], user_data["gender"]),
                is_active=True,
                created_at=datetime.now() - timedelta(days=random.randint(1, 30))
            )
            db.add(user)

            # 创建用户向量
            vector = generate_user_vector(user_data)
            completeness = np.count_nonzero(vector) / 144

            vector_profile = UserVectorProfileDB(
                id=str(uuid.uuid4()),
                user_id=user_data["id"],
                vector=json.dumps(vector.tolist()),
                completeness_ratio=completeness,
                recommended_strategy="vector" if completeness > 0.5 else "basic",
                dimensions_detail=json.dumps({
                    "demographics": "filled",
                    "interests": random.sample(INTERESTS, 3),
                    "city_tier": user_data["city_tier"],
                }),
                created_at=datetime.now()
            )
            db.add(vector_profile)

            # 创建社交指标（给部分用户）
            if random.random() > 0.3:
                like_count = random.randint(5, 50)
                dislike_count = random.randint(0, 10)
                total = like_count + dislike_count
                like_rate = like_count / total if total > 0 else 0.7

                social_metrics = UserSocialMetricsDB(
                    id=str(uuid.uuid4()),
                    user_id=user_data["id"],
                    like_count=like_count,
                    dislike_count=dislike_count,
                    pass_count=random.randint(5, 20),
                    like_rate=like_rate,
                    chat_response_rate=random.uniform(0.5, 0.95),
                    success_match_count=random.randint(0, 5),
                    reputation_score=like_rate * 100,
                    last_calculated_at=datetime.now()
                )
                db.add(social_metrics)

        db.commit()

    logger.info(f"成功创建 {count} 个模拟用户")
    return user_ids


async def create_mock_interactions(user_ids: List[str]) -> None:
    """
    创建模拟交互数据

    Args:
        user_ids: 用户ID列表
    """
    logger.info("开始创建模拟交互数据...")

    with db_session() as db:
        # 创建一些滑动记录
        interactions_count = 0

        for i, user_id in enumerate(user_ids[:30]):  # 前30个用户有交互
            # 每个用户随机滑动 5-15 次
            swipe_count = random.randint(5, 15)

            # 选择目标用户（异性）
            gender = "female" if i % 2 == 0 else "male"  # 假设偶数索引是男性

            target_pool = [
                uid for uid in user_ids
                if db.query(UserDB).filter(UserDB.id == uid).first()
                and db.query(UserDB).filter(UserDB.id == uid).first().gender != gender
            ]

            if not target_pool:
                continue

            targets = random.sample(target_pool, min(swipe_count, len(target_pool)))

            for target_id in targets:
                action = random.choices(["like", "pass", "super_like"], weights=[30, 60, 10])[0]

                swipe = SwipeActionDB(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    target_user_id=target_id,
                    action=action,
                    is_matched=False,
                    created_at=datetime.now() - timedelta(hours=random.randint(1, 48))
                )
                db.add(swipe)
                interactions_count += 1

                # 30% 概率添加反馈学习记录
                if action == "pass" and random.random() > 0.7:
                    feedback = UserFeedbackLearningDB(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        feedback_type="dislike",
                        target_match_id=target_id,
                        dislike_reason=random.choice(DISLIKE_REASONS),
                        confidence_score=random.uniform(0.5, 0.9),
                        created_at=datetime.now() - timedelta(hours=random.randint(1, 24))
                    )
                    db.add(feedback)

        db.commit()

    logger.info(f"成功创建 {interactions_count} 条交互记录")


async def main():
    """主函数"""
    print("=" * 60)
    print("模拟测试用户生成器")
    print("=" * 60)

    # 初始化数据库
    init_db()
    print("✅ 数据库初始化完成")

    # 创建用户
    user_ids = await create_mock_users(50)
    print(f"✅ 创建了 {len(user_ids)} 个模拟用户")

    # 创建交互数据
    await create_mock_interactions(user_ids)
    print("✅ 创建了交互数据")

    # 打印统计
    with db_session() as db:
        male_count = db.query(UserDB).filter(UserDB.gender == "male").count()
        female_count = db.query(UserDB).filter(UserDB.gender == "female").count()
        vector_count = db.query(UserVectorProfileDB).count()
        metrics_count = db.query(UserSocialMetricsDB).count()
        swipe_count = db.query(SwipeActionDB).count()

        print("\n📊 数据统计:")
        print(f"  - 总用户数: {len(user_ids)}")
        print(f"  - 男性用户: {male_count}")
        print(f"  - 女性用户: {female_count}")
        print(f"  - 用户向量: {vector_count}")
        print(f"  - 社交指标: {metrics_count}")
        print(f"  - 滑动记录: {swipe_count}")

        # 打印几个示例用户
        print("\n📋 示例用户:")
        sample_users = db.query(UserDB).limit(5).all()
        for u in sample_users:
            print(f"  - {u.name} ({u.gender}, {u.age}岁, {u.location}, {u.relationship_goal})")

    print("\n✅ 模拟数据生成完成!")


if __name__ == "__main__":
    asyncio.run(main())