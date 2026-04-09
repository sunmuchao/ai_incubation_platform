#!/usr/bin/env python3
"""
添加测试用户数据

用于测试匹配系统，添加一些女性用户以便男性用户可以匹配。
"""

import sys
import os
import json
import uuid
from datetime import datetime

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from db.database import get_db
from db.models import UserDB

# 测试用户数据
FEMALE_USERS = [
    {
        "id": str(uuid.uuid4()),
        "name": "小美",
        "age": 25,
        "gender": "female",
        "sexual_orientation": "heterosexual",
        "location": "上海",
        "email": "xiaomei@test.com",
        "password_hash": "",
        "bio": "喜欢旅行、摄影和咖啡。希望能遇到一个有趣的人一起探索世界~",
        "interests": ["旅行", "摄影", "咖啡", "阅读", "音乐"],
        "is_active": True,
    },
    {
        "id": str(uuid.uuid4()),
        "name": "小雨",
        "age": 27,
        "gender": "female",
        "sexual_orientation": "heterosexual",
        "location": "无锡",
        "email": "xiaoyu@test.com",
        "password_hash": "",
        "bio": "安静温柔的女孩，喜欢做瑜伽和画画。期待真诚的交流。",
        "interests": ["瑜伽", "画画", "音乐", "电影"],
        "is_active": True,
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Lisa",
        "age": 26,
        "gender": "female",
        "sexual_orientation": "heterosexual",
        "location": "苏州",
        "email": "lisa@test.com",
        "password_hash": "",
        "bio": "外企白领，热爱健身和美食。周末喜欢探店和短途旅行。",
        "interests": ["健身", "美食", "旅行", "购物"],
        "is_active": True,
    },
    {
        "id": str(uuid.uuid4()),
        "name": "梦梦",
        "age": 24,
        "gender": "female",
        "sexual_orientation": "heterosexual",
        "location": "杭州",
        "email": "mengmeng@test.com",
        "password_hash": "",
        "bio": "设计师，喜欢一切美好的事物。希望能找到 soulmate~",
        "interests": ["设计", "艺术展", "咖啡", "旅行"],
        "is_active": True,
    },
    {
        "id": str(uuid.uuid4()),
        "name": "思思",
        "age": 28,
        "gender": "female",
        "sexual_orientation": "heterosexual",
        "location": "无锡",
        "email": "sisi@test.com",
        "password_hash": "",
        "bio": "教师，性格开朗。喜欢运动、看书和交朋友。",
        "interests": ["运动", "阅读", "教学", "旅行"],
        "is_active": True,
    },
]

def add_test_users():
    """添加测试用户到数据库"""
    print("正在添加女性测试用户...")

    db = next(get_db())

    added_count = 0
    for user_data in FEMALE_USERS:
        try:
            # 检查用户是否已存在
            existing = db.query(UserDB).filter(UserDB.id == user_data["id"]).first()
            if existing:
                print(f"  - {user_data['name']} 已存在，跳过")
                continue

            # 检查邮箱是否已存在
            existing_by_email = db.query(UserDB).filter(UserDB.email == user_data["email"]).first()
            if existing_by_email:
                print(f"  - {user_data['email']} 已被使用，跳过")
                continue

            # 创建用户
            db_user = UserDB(
                id=user_data["id"],
                name=user_data["name"],
                email=user_data["email"],
                password_hash=user_data.get("password_hash", ""),
                age=user_data["age"],
                gender=user_data["gender"],
                location=user_data["location"],
                interests=json.dumps(user_data.get("interests", [])),
                bio=user_data.get("bio", ""),
                sexual_orientation=user_data.get("sexual_orientation", "heterosexual"),
            )
            db.add(db_user)
            db.commit()
            print(f"  + {user_data['name']} ({user_data['age']}岁，{user_data['location']}) - 已添加")
            added_count += 1

        except Exception as e:
            db.rollback()
            print(f"  ! 添加 {user_data['name']} 失败：{e}")

    print(f"\n完成！新增 {added_count} 位测试用户")

    # 统计数据库中用户总数
    total_users = db.query(UserDB).count()
    female_users = db.query(UserDB).filter(UserDB.gender == "female").count()
    male_users = db.query(UserDB).filter(UserDB.gender == "male").count()
    print(f"数据库中现在有 {total_users} 位用户（{male_users} 男，{female_users} 女）")

if __name__ == "__main__":
    add_test_users()