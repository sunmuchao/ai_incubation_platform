"""
测试用户数据导入脚本

用于在开发环境中创建测试用户数据，方便测试匹配功能。
使用方法：
    cd /Users/sunmuchao/Downloads/ai_incubation_platform/matchmaker-agent
    python scripts/import_test_users.py

功能：
1. 创建多个测试用户（包含完整的个人信息）
2. 为每个用户生成兴趣爱好
3. 设置用户为活跃状态
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from db.database import SessionLocal
from db.repositories import UserRepository
from db.models import UserDB
from utils.logger import logger
from auth.jwt import get_password_hash
from datetime import datetime
import json
import uuid

# 测试用户数据
TEST_USERS = [
    {
        "username": "test_user_001",
        "password": "123456",
        "name": "小明",
        "age": 28,
        "gender": "male",
        "location": "北京",
        "bio": "互联网工程师，喜欢旅行、摄影和美食。希望能找到一个有趣的人一起探索世界。",
        "interests": ["旅行", "摄影", "美食", "编程", "电影"],
        "is_active": True,
    },
    {
        "username": "test_user_002",
        "password": "123456",
        "name": "小红",
        "age": 26,
        "gender": "female",
        "location": "北京",
        "bio": "设计师，热爱生活，喜欢画画、瑜伽和看书。期待遇见一个温暖的人。",
        "interests": ["画画", "瑜伽", "阅读", "咖啡", "花艺"],
        "is_active": True,
    },
    {
        "username": "test_user_003",
        "password": "123456",
        "name": "小刚",
        "age": 30,
        "gender": "male",
        "location": "上海",
        "bio": "金融从业者，平时喜欢健身、游泳和听音乐。希望能找到一个志同道合的伴侣。",
        "interests": ["健身", "游泳", "音乐", "投资", "旅行"],
        "is_active": True,
    },
    {
        "username": "test_user_004",
        "password": "123456",
        "name": "小丽",
        "age": 25,
        "gender": "female",
        "location": "上海",
        "bio": "教师，性格温柔善良，喜欢烘焙、手工和小动物。期待一份真挚的感情。",
        "interests": ["烘焙", "手工", "宠物", "追剧", "逛街"],
        "is_active": True,
    },
    {
        "username": "test_user_005",
        "password": "123456",
        "name": "小强",
        "age": 29,
        "gender": "male",
        "location": "深圳",
        "bio": "创业者，充满激情和活力，喜欢登山、骑行和科技。希望能找到一个理解和支持我的人。",
        "interests": ["登山", "骑行", "科技", "创业", "阅读"],
        "is_active": True,
    },
    {
        "username": "test_user_006",
        "password": "123456",
        "name": "小芳",
        "age": 27,
        "gender": "female",
        "location": "深圳",
        "bio": "产品经理，理性与感性并存，喜欢旅行、美食和看电影。期待遇见一个有趣且靠谱的人。",
        "interests": ["旅行", "美食", "电影", "购物", "摄影"],
        "is_active": True,
    },
    {
        "username": "test_user_007",
        "password": "123456",
        "name": "小李",
        "age": 31,
        "gender": "male",
        "location": "杭州",
        "bio": "程序员，性格温和，喜欢 coding、游戏和动漫。希望能找到一个可以一起打游戏的女生。",
        "interests": ["编程", "游戏", "动漫", "音乐", "美食"],
        "is_active": True,
    },
    {
        "username": "test_user_008",
        "password": "123456",
        "name": "小雅",
        "age": 24,
        "gender": "female",
        "location": "杭州",
        "bio": "自由职业者，热爱生活和自由，喜欢旅行、写作和手冲咖啡。期待一份轻松而美好的爱情。",
        "interests": ["旅行", "写作", "咖啡", "手工", "音乐"],
        "is_active": True,
    },
    {
        "username": "test_user_009",
        "password": "123456",
        "name": "小王",
        "age": 28,
        "gender": "male",
        "location": "成都",
        "bio": "厨师，热爱美食和生活，喜欢做饭、品尝美食和旅行。希望能找到一个吃货一起探索美食。",
        "interests": ["烹饪", "美食", "旅行", "电影", "健身"],
        "is_active": True,
    },
    {
        "username": "test_user_010",
        "password": "123456",
        "name": "小婷",
        "age": 26,
        "gender": "female",
        "location": "成都",
        "bio": "护士，善良细心，喜欢追剧、购物和旅行。期待遇见一个温柔体贴的人。",
        "interests": ["追剧", "购物", "旅行", "美食", "拍照"],
        "is_active": True,
    },
]


def create_test_users():
    """创建测试用户"""
    logger.info("开始创建测试用户...")

    db = SessionLocal()
    user_repo = UserRepository(db)
    created_count = 0
    skipped_count = 0

    try:
        for user_data in TEST_USERS:
            # 检查用户是否已存在（通过邮箱）
            # 邮箱等于用户名，方便登录测试
            email = user_data['username']
            existing_user = user_repo.get_by_email(email)
            if existing_user:
                logger.info(f"用户 {user_data['username']} 已存在，跳过")
                skipped_count += 1
                continue

            # 创建用户
            user = user_repo.create({
                "id": str(uuid.uuid4()),
                "name": user_data["name"],
                "email": email,
                "password_hash": get_password_hash(user_data["password"]),
                "age": user_data["age"],
                "gender": user_data["gender"],
                "location": user_data["location"],
                "bio": user_data["bio"],
                "interests": json.dumps(user_data["interests"]),
            })
            logger.info(f"创建用户成功：{user_data['username']} ({user_data['name']})")
            created_count += 1

        logger.info(f"测试用户创建完成！新建：{created_count}个，跳过：{skipped_count}个")

    except Exception as e:
        logger.error(f"创建测试用户失败：{e}")
        db.rollback()
        raise
    finally:
        db.close()


def print_test_accounts():
    """打印测试账号信息"""
    print("\n" + "=" * 60)
    print("测试账号列表")
    print("=" * 60)
    print(f"{'用户名':<20} {'姓名':<10} {'性别':<6} {'年龄':<6} {'城市':<10} {'密码':<10}")
    print("-" * 60)
    for user in TEST_USERS:
        print(f"{user['username']:<20} {user['name']:<10} {user['gender']:<6} {user['age']:<6} {user['location']:<10} {user['password']:<10}")
    print("=" * 60)
    print(f"总账号数：{len(TEST_USERS)}")
    print("所有账号密码均为：123456")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("AI Matchmaker - 测试用户数据导入工具")
    print("=" * 60)

    # 创建测试用户
    create_test_users()

    # 打印测试账号信息
    print_test_accounts()

    print("导入完成！你可以使用以上账号登录测试匹配功能。")
    print("=" * 60 + "\n")
