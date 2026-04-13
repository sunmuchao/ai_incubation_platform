#!/usr/bin/env python3
"""
生成无锡女性测试用户数据 - 使用原生SQL直接插入

条件：
- 地点：无锡
- 年龄：25-30岁
- 关系目标：奔着结婚去（marriage/serious）
- 活跃状态：is_active=True
"""

import sqlite3
import json
import uuid
import random
from datetime import datetime, timedelta

# 数据库路径
DB_PATH = "matchmaker_agent.db"

# 无锡女性用户数据
WUXI_FEMALE_USERS = [
    {
        "name": "雨婷",
        "age": 25,
        "gender": "female",
        "sexual_orientation": "heterosexual",
        "location": "无锡",
        "relationship_goal": "marriage",
        "bio": "无锡本地人，会计工作。喜欢烘焙、旅行和瑜伽。希望能遇到一个真诚的人，一起经营温暖的家。",
        "interests": ["烘焙", "旅行", "瑜伽", "阅读", "电影"],
    },
    {
        "name": "思琪",
        "age": 26,
        "gender": "female",
        "sexual_orientation": "heterosexual",
        "location": "无锡",
        "relationship_goal": "marriage",
        "bio": "小学老师，性格温柔。喜欢小朋友，也喜欢画画和手工。期待找到志同道合的伴侣，一起组建家庭。",
        "interests": ["画画", "手工", "阅读", "旅行", "摄影"],
    },
    {
        "name": "晓雯",
        "age": 27,
        "gender": "female",
        "sexual_orientation": "heterosexual",
        "location": "无锡",
        "relationship_goal": "serious",
        "bio": "外企运营经理，工作稳定。平时喜欢健身、美食和短途旅行。想找一个靠谱的人，认真交往。",
        "interests": ["健身", "美食", "旅行", "音乐", "咖啡"],
    },
    {
        "name": "婉清",
        "age": 28,
        "gender": "female",
        "sexual_orientation": "heterosexual",
        "location": "无锡",
        "relationship_goal": "marriage",
        "bio": "无锡新区工作，产品经理。喜欢摄影、爬山和看电影。希望能遇到一个有趣又靠谱的人，一起探索生活。",
        "interests": ["摄影", "爬山", "电影", "阅读", "美食"],
    },
    {
        "name": "佳慧",
        "age": 29,
        "gender": "female",
        "sexual_orientation": "heterosexual",
        "location": "无锡",
        "relationship_goal": "marriage",
        "bio": "医院护士，性格开朗细心。喜欢烹饪、宠物和瑜伽。期待找到一个善良的人，一起走进婚姻。",
        "interests": ["烹饪", "宠物", "瑜伽", "音乐", "旅行"],
    },
    {
        "name": "梦瑶",
        "age": 30,
        "gender": "female",
        "sexual_orientation": "heterosexual",
        "location": "无锡",
        "relationship_goal": "serious",
        "bio": "设计师，喜欢一切美好的事物。平时逛艺术展、喝咖啡、做手工。想找一个懂生活的人，认真交往。",
        "interests": ["设计", "艺术展", "咖啡", "手工", "旅行"],
    },
    {
        "name": "晓琳",
        "age": 25,
        "gender": "female",
        "sexual_orientation": "heterosexual",
        "location": "无锡",
        "relationship_goal": "marriage",
        "bio": "银行职员，性格稳重。喜欢阅读、古典音乐和茶艺。希望能找到一个成熟稳重的人，共度余生。",
        "interests": ["阅读", "古典音乐", "茶艺", "瑜伽", "旅行"],
    },
    {
        "name": "怡萱",
        "age": 26,
        "gender": "female",
        "sexual_orientation": "heterosexual",
        "location": "无锡",
        "relationship_goal": "serious",
        "bio": "文案策划，性格活泼。喜欢摄影、美食探店和音乐节。期待遇到一个有趣的人，一起探索无锡的美食。",
        "interests": ["摄影", "美食", "音乐", "旅行", "咖啡"],
    },
    {
        "name": "若云",
        "age": 27,
        "gender": "female",
        "sexual_orientation": "heterosexual",
        "location": "无锡",
        "relationship_goal": "marriage",
        "bio": "小学音乐老师，会弹钢琴和吉他。喜欢音乐、旅行和阅读。希望能找到一个懂艺术的人，一起组建家庭。",
        "interests": ["音乐", "钢琴", "旅行", "阅读", "电影"],
    },
    {
        "name": "诗涵",
        "age": 28,
        "gender": "female",
        "sexual_orientation": "heterosexual",
        "location": "无锡",
        "relationship_goal": "marriage",
        "bio": "无锡太湖边长大，喜欢湖景和自然。平时做瑜伽、喝茶、看书。想找一个安静稳重的人，认真交往走向婚姻。",
        "interests": ["瑜伽", "茶艺", "阅读", "自然", "摄影"],
    },
    {
        "name": "悦然",
        "age": 29,
        "gender": "female",
        "sexual_orientation": "heterosexual",
        "location": "无锡",
        "relationship_goal": "serious",
        "bio": "电商运营，性格开朗。喜欢健身、美食和周末短途旅行。期待找到一个积极向上的人，一起规划未来。",
        "interests": ["健身", "美食", "旅行", "购物", "电影"],
    },
    {
        "name": "清雅",
        "age": 30,
        "gender": "female",
        "sexual_orientation": "heterosexual",
        "location": "无锡",
        "relationship_goal": "marriage",
        "bio": "事业单位工作，性格温和。喜欢插花、茶艺和古典音乐。希望能找到一个稳重的人，一起步入婚姻。",
        "interests": ["插花", "茶艺", "古典音乐", "阅读", "瑜伽"],
    },
]

# 头像基础URL
AVATAR_BASE = "https://api.dicebear.com/7.x/avataaars/svg?seed="


def add_wuxi_female_users():
    """添加无锡女性测试用户到数据库"""
    print("正在添加无锡女性测试用户...")
    print("条件：无锡、25-30岁、奔着结婚去（marriage/serious）")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    added_count = 0
    for user_data in WUXI_FEMALE_USERS:
        user_id = str(uuid.uuid4())
        email = f"{user_data['name']}_{random.randint(1000,9999)}@wuxi.test.com"
        avatar_url = f"{AVATAR_BASE}{user_id}"
        created_at = (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d %H:%M:%S")

        try:
            # 检查邮箱是否已存在
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                print(f"  - {user_data['name']} 邮箱已存在，生成新邮箱")
                email = f"{user_data['name']}_{uuid.uuid4().hex[:8]}@wuxi.test.com"

            # 直接插入数据
            cursor.execute("""
                INSERT INTO users (
                    id, name, email, password_hash, age, gender, location,
                    interests, bio, avatar_url, is_active, created_at,
                    relationship_goal, sexual_orientation,
                    preferred_age_min, preferred_age_max, preferred_location, preferred_gender,
                    is_permanently_banned, violation_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                user_data["name"],
                email,
                "",  # 测试用户无需密码
                user_data["age"],
                user_data["gender"],
                user_data["location"],
                json.dumps(user_data.get("interests", [])),
                user_data.get("bio", ""),
                avatar_url,
                1,  # is_active
                created_at,
                user_data["relationship_goal"],
                user_data.get("sexual_orientation", "heterosexual"),
                25,  # preferred_age_min
                35,  # preferred_age_max
                "无锡",  # preferred_location
                "male",  # preferred_gender
                0,  # is_permanently_banned = False（关键！）
                0,  # violation_count
            ))
            conn.commit()
            print(f"  ✓ {user_data['name']} ({user_data['age']}岁，{user_data['location']}，{user_data['relationship_goal']}) - 已添加")
            added_count += 1

        except Exception as e:
            conn.rollback()
            print(f"  ✗ 添加 {user_data['name']} 失败：{e}")

    print("=" * 60)
    print(f"完成！新增 {added_count} 位无锡女性测试用户")

    # 统计数据库中符合条件的用户
    cursor.execute("""
        SELECT COUNT(*) FROM users
        WHERE gender = 'female'
        AND location = '无锡'
        AND age BETWEEN 25 AND 30
        AND relationship_goal IN ('marriage', 'serious')
        AND is_active = 1
    """)
    wuxi_female = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM users
        WHERE gender = 'female'
        AND location = '无锡'
    """)
    wuxi_all_female = cursor.fetchone()[0]

    print(f"\n📊 数据库统计:")
    print(f"  - 无锡女性用户总数: {wuxi_all_female}")
    print(f"  - 符合条件（25-30岁、奔着结婚去）: {wuxi_female}")

    # 显示新添加的用户
    cursor.execute("""
        SELECT name, age, relationship_goal, bio
        FROM users
        WHERE gender = 'female'
        AND location = '无锡'
        AND age BETWEEN 25 AND 30
        AND relationship_goal IN ('marriage', 'serious')
        AND is_active = 1
        ORDER BY created_at DESC
        LIMIT 12
    """)
    users = cursor.fetchall()
    print(f"\n📋 新添加的无锡女性用户列表:")
    for u in users:
        print(f"  - {u[0]} ({u[1]}岁, {u[2]})")
        print(f"    简介: {u[3][:50]}...")

    conn.close()


if __name__ == "__main__":
    add_wuxi_female_users()