"""
下载中国人头像图片

使用 DiceBear 头像 API（稳定可靠）
- 提供卡通风格的头像
- 支持多种风格选择
- 免费使用，无需 API Key

使用方法：
    cd /Users/sunmuchao/Downloads/ai_incubation_platform/Her
    python scripts/download_chinese_avatars.py --male-count 100 --female-count 100
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

import argparse
import requests
import random
from pathlib import Path
from utils.logger import logger

# 头像保存目录
AVATARS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'avatars')

# DiceBear API - 稳定可靠的头像生成服务
# 文档：https://www.dicebear.com/
DICEBEAR_BASE_URL = "https://api.dicebear.com/7.x"

# 可选的头像风格
# avataaars - 经典卡通风格（推荐）
# avataaars-neutral - 中性色调版本
# notionists - Notion 风格
# notionists-neutral - Notion 中性风格
MALE_STYLES = ['avataaars', 'avataaars-neutral']
FEMALE_STYLES = ['avataaars', 'avataaars-neutral']


def ensure_avatars_dir():
    """确保头像目录存在"""
    os.makedirs(AVATARS_DIR, exist_ok=True)
    logger.info(f"Avatars directory: {AVATARS_DIR}")


def download_image(url: str, save_path: str) -> bool:
    """
    下载图片并保存

    Args:
        url: 图片 URL
        save_path: 保存路径

    Returns:
        是否下载成功
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/svg+xml,image/*,*/*;q=0.8',
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        # DiceBear 返回 SVG 格式，保存为 svg 文件
        with open(save_path, 'wb') as f:
            f.write(response.content)

        logger.info(f"Downloaded: {save_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return False


def download_avatars_from_dicebear(male_count: int, female_count: int):
    """
    从 DiceBear API 下载头像

    提供卡通风格的头像，稳定可靠
    """
    ensure_avatars_dir()

    downloaded_male = 0
    downloaded_female = 0

    # 下载男性头像
    logger.info(f"Downloading {male_count} male avatars from DiceBear API...")
    for i in range(1, male_count + 1):
        seed = f"chinese_male_{i}_{random.randint(1, 10000)}"
        style = random.choice(MALE_STYLES)
        # 使用男性化的背景色和发型限制
        avatar_url = f"{DICEBEAR_BASE_URL}/{style}/svg?seed={seed}&backgroundColor=b6e3f4,c0aede,d1d4f9&hair=short&facialHair=maybe"
        save_path = os.path.join(AVATARS_DIR, f"male_{i:03d}.svg")

        if download_image(avatar_url, save_path):
            downloaded_male += 1

        if i % 10 == 0:
            logger.info(f"Progress: {i}/{male_count} male avatars")

    # 下载女性头像
    logger.info(f"Downloading {female_count} female avatars from DiceBear API...")
    for i in range(1, female_count + 1):
        seed = f"chinese_female_{i}_{random.randint(1, 10000)}"
        style = random.choice(FEMALE_STYLES)
        # 使用女性化的背景色和发型限制
        avatar_url = f"{DICEBEAR_BASE_URL}/{style}/svg?seed={seed}&backgroundColor=ffc0cb,ffb6c1,ffcce0&hair=long,bob,short&makeup=true"
        save_path = os.path.join(AVATARS_DIR, f"female_{i:03d}.svg")

        if download_image(avatar_url, save_path):
            downloaded_female += 1

        if i % 10 == 0:
            logger.info(f"Progress: {i}/{female_count} female avatars")

    logger.info(f"\nDownload complete!")
    logger.info(f"Male avatars: {downloaded_male}/{male_count}")
    logger.info(f"Female avatars: {downloaded_female}/{female_count}")

    return downloaded_male, downloaded_female


def check_avatar_sources():
    """
    查看可用的头像源建议
    """
    sources = """
===========================================
中国人头像图片源建议
===========================================

方案 1：DiceBear API（当前使用）✓
------------------------------------
API 地址：https://www.dicebear.com/
- 卡通风格头像
- 稳定可靠，免费使用
- 支持自定义风格、发型、背景色等
- 适合用于头像占位符或卡通风格应用


方案 2：真实照片 - 手动下载（最佳质量）
------------------------------------
从以下网站下载中国人头像图片：

1. Unsplash (https://unsplash.com)
   - 搜索：chinese man portrait, chinese woman portrait
   - 图片质量高，免费可商用

2. Pexels (https://www.pexels.com)
   - 搜索：chinese portrait, asian portrait
   - 免费可商用

3. Pixabay (https://pixabay.com)
   - 搜索：chinese portrait
   - 免费可商用

下载后按以下命名保存到 static/avatars/ 目录：
- 男性：male_001.jpg, male_002.jpg, ...
- 女性：female_001.jpg, female_002.jpg, ...


方案 3：AI 生成（可定制化）
---------------------------
使用 AI 工具生成中国人头像：

1. Stable Diffusion WebUI
   - 提示词示例（男）：
     "chinese handsome young man portrait, professional photo, studio lighting, 8k"
   - 提示词示例（女）：
     "chinese beautiful young woman portrait, professional photo, studio lighting, 8k"

2. Midjourney
   - 提示词示例（男）：
     "portrait of a handsome chinese man, studio photo --ar 1:1 --v 6"
   - 提示词示例（女）：
     "portrait of a beautiful chinese woman, studio photo --ar 1:1 --v 6"

3. 即梦 AI / 文心一格（国内 AI 工具）
   - 提示词：中国帅哥肖像，专业摄影
   - 提示词：中国美女肖像，专业摄影


方案 4：购买商业头像库
------------------------------------
1. Shutterstock
2. Getty Images
3. 视觉中国（国内）
4. 站酷海洛（国内）

===========================================
"""
    print(sources)


def main():
    parser = argparse.ArgumentParser(description="下载中国人头像图片")
    parser.add_argument("--male-count", type=int, default=100, help="男性头像数量（默认：100）")
    parser.add_argument("--female-count", type=int, default=100, help="女性头像数量（默认：100）")
    parser.add_argument("--check-sources", action="store_true", help="查看推荐的头像源")
    args = parser.parse_args()

    if args.check_sources:
        check_avatar_sources()
        return

    print("\n" + "=" * 60)
    print("中国人头像下载工具")
    print("=" * 60)
    print(f"计划下载：男性 {args.male_count} 个，女性 {args.female_count} 个")
    print("头像源：DiceBear API (https://www.dicebear.com/)")
    print("风格：卡通风格（avataaars）")
    print("=" * 60 + "\n")

    # 检查头像目录
    ensure_avatars_dir()

    # 从 DiceBear API 下载头像
    downloaded_male, downloaded_female = download_avatars_from_dicebear(
        args.male_count, args.female_count
    )

    print("\n" + "=" * 60)
    print("下载完成！")
    print("=" * 60)
    print(f"头像保存目录：{AVATARS_DIR}")
    print(f"男性头像：{downloaded_male} 个")
    print(f"女性头像：{downloaded_female} 个")
    print("\n提示：")
    print(f"1. 头像文件已保存到 {AVATARS_DIR}")
    print(f"2. 运行以下脚本更新数据库中的用户头像：")
    print(f"   python scripts/add_user_avatars.py")
    print("\n如需真实照片，请参考：python scripts/download_chinese_avatars.py --check-sources")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
