"""
为用户添加随机头像图片

使用中国人头像图片：
- 本地头像目录：static/avatars/
- 男性头像：static/avatars/male_001.svg ~ male_XXX.svg
- 女性头像：static/avatars/female_001.svg ~ female_XXX.svg

头像要求：
- 男性：中国帅哥头像，精致、阳光、有气质
- 女性：中国美女头像，精致、优雅、有气质
"""
import sys
import os
import glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

import random
import argparse
from db.database import get_db
from db.repositories import UserRepository
from utils.logger import logger

# 头像目录配置
# 头像需要预先下载到 Her/static/avatars/ 目录下
# 男性头像命名：male_001.svg, male_002.jpg, ...
# 女性头像命名：female_001.svg, female_002.jpg, ...
AVATARS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'avatars')

# 头像服务器基础 URL（生产环境配置为实际的 CDN 或服务器地址）
AVATAR_BASE_URL = "/static/avatars"

# 头像文件扩展名（支持 .svg 和 .jpg）
AVATAR_EXTENSIONS = ['.svg', '.jpg', '.jpeg', '.png', '.webp']


def count_available_avatars(prefix: str) -> int:
    """
    统计指定前缀的可用头像数量

    Args:
        prefix: 头像文件前缀（'male' 或 'female'）

    Returns:
        可用的头像数量
    """
    count = 0
    for ext in AVATAR_EXTENSIONS:
        pattern = os.path.join(AVATARS_DIR, f"{prefix}_*{ext}")
        count += len(glob.glob(pattern))
    return count


def get_available_avatar_files(prefix: str) -> list:
    """
    获取指定前缀的所有可用头像文件列表

    Args:
        prefix: 头像文件前缀（'male' 或 'female'）

    Returns:
        头像文件名列表
    """
    files = []
    for ext in AVATAR_EXTENSIONS:
        pattern = os.path.join(AVATARS_DIR, f"{prefix}_*{ext}")
        files.extend(glob.glob(pattern))
    return files


# 自动检测头像数量（在模块加载时）
MALE_AVATAR_COUNT = count_available_avatars('male')
FEMALE_AVATAR_COUNT = count_available_avatars('female')

# 如果头像数量为 0，设置一个默认值以避免除零错误
if MALE_AVATAR_COUNT == 0:
    MALE_AVATAR_COUNT = 100  # 默认值
if FEMALE_AVATAR_COUNT == 0:
    FEMALE_AVATAR_COUNT = 100  # 默认值


def get_avatar_url(user_id: str, gender: str) -> str:
    """
    为用户生成头像 URL（使用本地中国人头像）

    Args:
        user_id: 用户 ID
        gender: 用户性别 (male/female)

    Returns:
        头像 URL
    """
    # 根据性别选择头像前缀
    if gender == "female":
        prefix = "female"
        files = get_available_avatar_files('female')
    else:
        prefix = "male"
        files = get_available_avatar_files('male')

    # 如果没有可用头像，返回默认头像
    if not files:
        logger.warning(f"No {prefix} avatars found in {AVATARS_DIR}")
        return f"{AVATAR_BASE_URL}/default.svg"

    # 随机选择一个头像文件
    selected_file = random.choice(files)
    img_filename = os.path.basename(selected_file)

    # 返回本地头像 URL
    avatar_url = f"{AVATAR_BASE_URL}/{img_filename}"

    logger.info(f"Generated avatar for {gender}: {avatar_url}")
    return avatar_url


def update_user_avatar(db, user_id: str, avatar_url: str) -> bool:
    """更新用户头像"""
    try:
        from db.models import UserDB
        db.query(UserDB).filter(UserDB.id == user_id).update({"avatar_url": avatar_url})
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to update avatar for user {user_id}: {e}")
        db.rollback()
        return False


def add_avatars_to_all_users(gender_specific: bool = True, dry_run: bool = False):
    """
    为所有用户添加头像

    Args:
        gender_specific: 是否根据性别选择头像
        dry_run: 仅预览，不实际更新
    """
    db = next(get_db())
    user_repo = UserRepository(db)

    # 获取所有用户
    all_users = user_repo.list_all()

    if not all_users:
        logger.warning("No users found in database")
        return

    logger.info(f"Found {len(all_users)} users in database")

    updated_count = 0
    skipped_count = 0

    for db_user in all_users:
        user_id = db_user.id
        current_avatar = db_user.avatar_url
        gender = db_user.gender

        # 如果已有头像，跳过
        if current_avatar:
            logger.info(f"User {user_id} ({db_user.name}) already has avatar, skipping")
            skipped_count += 1
            continue

        # 生成头像 URL
        avatar_url = get_avatar_url(user_id, gender)

        if dry_run:
            logger.info(f"[DRY RUN] Would update user {user_id} ({db_user.name}, {gender}) -> {avatar_url}")
            updated_count += 1
        else:
            # 更新头像
            if update_user_avatar(db, user_id, avatar_url):
                logger.info(f"✓ Updated avatar for user {user_id} ({db_user.name}, {gender}) -> {avatar_url}")
                updated_count += 1
            else:
                logger.error(f"✗ Failed to update avatar for user {user_id}")

    db.close()

    logger.info(f"\n{'='*50}")
    logger.info(f"Summary:")
    logger.info(f"  - Updated: {updated_count} users")
    logger.info(f"  - Skipped: {skipped_count} users (already have avatar)")
    logger.info(f"  - Total:   {len(all_users)} users")
    logger.info(f"{'='*50}")

    if dry_run:
        logger.info("\nThis was a DRY RUN. No changes were made.")
        logger.info("Run without --dry-run to apply changes.")


def reset_all_avatars():
    """重置所有用户头像为空"""
    db = next(get_db())
    from db.models import UserDB
    db.query(UserDB).update({"avatar_url": None})
    db.commit()
    db.close()
    logger.info("All user avatars have been reset to NULL")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="为用户添加随机头像")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅预览更改，不实际更新数据库"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="重置所有用户头像为空"
    )
    parser.add_argument(
        "--any-gender",
        action="store_true",
        help="不考虑性别，随机分配头像"
    )

    args = parser.parse_args()

    if args.reset:
        reset_all_avatars()
    else:
        add_avatars_to_all_users(
            gender_specific=not args.any_gender,
            dry_run=args.dry_run
        )
