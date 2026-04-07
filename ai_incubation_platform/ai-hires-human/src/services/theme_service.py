"""
主题设置服务中心层 - v1.22 用户体验优化

提供个性化主题/皮肤功能的核心业务逻辑
"""
from datetime import datetime
from typing import Dict, List, Optional
import uuid
import logging

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.ux_theme import UserThemeSettingsDB, ThemePresetDB

logger = logging.getLogger(__name__)


# ==================== 主题设置服务 ====================

class ThemeService:
    """用户主题设置服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_theme(self, user_id: str) -> Optional[UserThemeSettingsDB]:
        """获取用户主题设置"""
        result = await self.db.execute(
            select(UserThemeSettingsDB).where(UserThemeSettingsDB.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create_theme(self, user_id: str) -> UserThemeSettingsDB:
        """获取用户主题设置，如果不存在则创建默认设置"""
        theme = await self.get_user_theme(user_id)

        if not theme:
            theme = UserThemeSettingsDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                theme_mode='system',
                accent_color='blue',
                font_size='medium',
                density='comfortable',
            )
            self.db.add(theme)
            await self.db.flush()

        return theme

    async def update_theme(self, user_id: str, theme_data: Dict) -> UserThemeSettingsDB:
        """更新用户主题设置"""
        theme = await self.get_or_create_theme(user_id)

        # 更新字段
        if 'theme_mode' in theme_data and theme_data['theme_mode'] in ['light', 'dark', 'system']:
            theme.theme_mode = theme_data['theme_mode']

        if 'accent_color' in theme_data and theme_data['accent_color'] in [
            'blue', 'purple', 'green', 'orange', 'pink', 'teal', 'coral', 'red', 'cyan'
        ]:
            theme.accent_color = theme_data['accent_color']

        if 'font_size' in theme_data and theme_data['font_size'] in ['small', 'medium', 'large']:
            theme.font_size = theme_data['font_size']

        if 'density' in theme_data and theme_data['density'] in ['compact', 'comfortable', 'spacious']:
            theme.density = theme_data['density']

        if 'custom_background' in theme_data:
            if theme_data['custom_background'] is None or len(theme_data['custom_background']) <= 500:
                theme.custom_background = theme_data['custom_background']

        if 'theme_preset' in theme_data:
            theme.theme_preset = theme_data['theme_preset']

        theme.updated_at = datetime.utcnow()
        await self.db.flush()

        logger.info(f"用户 {user_id} 更新了主题设置：{theme.theme_mode}/{theme.accent_color}")

        return theme

    async def get_available_themes(self) -> List[Dict]:
        """获取可用主题选项"""
        # 基础主题模式
        theme_modes = [
            {"key": "light", "name": "浅色模式", "icon": "sun"},
            {"key": "dark", "name": "深色模式", "icon": "moon"},
            {"key": "system", "name": "跟随系统", "icon": "desktop"},
        ]

        # 配色方案
        accent_colors = [
            {"key": "blue", "name": "海洋蓝", "hex": "#3B82F6"},
            {"key": "purple", "name": "梦幻紫", "hex": "#8B5CF6"},
            {"key": "green", "name": "清新绿", "hex": "#10B981"},
            {"key": "orange", "name": "活力橙", "hex": "#F59E0B"},
            {"key": "pink", "name": "樱花粉", "hex": "#EC4899"},
            {"key": "teal", "name": "青色", "hex": "#14B8A6"},
            {"key": "coral", "name": "珊瑚红", "hex": "#FF6B6B"},
            {"key": "red", "name": "中国红", "hex": "#EF4444"},
            {"key": "cyan", "name": "天蓝色", "hex": "#06B6D4"},
        ]

        # 字体大小
        font_sizes = [
            {"key": "small", "name": "小", "preview": "A"},
            {"key": "medium", "name": "中", "preview": "A"},
            {"key": "large", "name": "大", "preview": "A"},
        ]

        # 布局密度
        densities = [
            {"key": "compact", "name": "紧凑", "description": "显示更多内容"},
            {"key": "comfortable", "name": "舒适", "description": "默认间距"},
            {"key": "spacious", "name": "宽松", "description": "更大间距"},
        ]

        # 获取预设主题包
        result = await self.db.execute(
            select(ThemePresetDB)
            .where(ThemePresetDB.is_active == 1)
            .order_by(ThemePresetDB.sort_order if hasattr(ThemePresetDB, 'sort_order') else ThemePresetDB.created_at)
        )
        presets = result.scalars().all()

        return {
            "theme_modes": theme_modes,
            "accent_colors": accent_colors,
            "font_sizes": font_sizes,
            "densities": densities,
            "presets": [preset.to_dict() for preset in presets],
        }

    async def apply_preset_theme(self, user_id: str, preset_id: str) -> UserThemeSettingsDB:
        """应用预设主题"""
        # 获取预设主题
        result = await self.db.execute(
            select(ThemePresetDB).where(ThemePresetDB.id == preset_id)
        )
        preset = result.scalar_one_or_none()

        if not preset:
            raise ValueError(f"预设主题不存在：{preset_id}")

        if not preset.is_active:
            raise ValueError(f"预设主题已停用：{preset.name}")

        # 获取或创建用户主题设置
        theme = await self.get_or_create_theme(user_id)

        # TODO: 解析 preset.config_json 并应用到 theme
        # 目前简化处理，只设置 preset 名称
        theme.theme_preset = preset.name
        theme.updated_at = datetime.utcnow()

        await self.db.flush()

        logger.info(f"用户 {user_id} 应用了预设主题：{preset.name}")

        return theme

    async def reset_theme(self, user_id: str) -> UserThemeSettingsDB:
        """重置为主题默认设置"""
        theme = await self.get_or_create_theme(user_id)

        theme.theme_mode = 'system'
        theme.accent_color = 'blue'
        theme.font_size = 'medium'
        theme.density = 'comfortable'
        theme.custom_background = None
        theme.theme_preset = None
        theme.updated_at = datetime.utcnow()

        await self.db.flush()

        logger.info(f"用户 {user_id} 重置了主题设置")

        return theme


# ==================== 依赖注入 ====================

def get_theme_service(db: AsyncSession) -> ThemeService:
    """获取主题服务实例"""
    return ThemeService(db)
