"""
用户主题设置数据模型 - v1.22 用户体验优化

提供个性化主题/皮肤功能的数据持久化
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.ext.asyncio import AsyncSession
from database import Base


class UserThemeSettingsDB(Base):
    """用户主题设置数据库模型"""
    __tablename__ = "user_theme_settings"

    id = Column(String(36), primary_key=True, nullable=False)
    user_id = Column(String(36), nullable=False, index=True, comment="用户 ID")

    # 主题模式
    theme_mode = Column(String(20), default='system', comment="主题模式：light/dark/system")

    # 配色方案
    accent_color = Column(String(20), default='blue', comment="强调色：blue/purple/green/orange/pink/teal/coral")

    # 字体大小
    font_size = Column(String(10), default='medium', comment="字体大小：small/medium/large")

    # 布局密度
    density = Column(String(10), default='comfortable', comment="布局密度：compact/comfortable/spacious")

    # 自定义背景
    custom_background = Column(String(500), nullable=True, comment="自定义背景图片 URL")

    # 预设主题包（未来扩展）
    theme_preset = Column(String(50), nullable=True, comment="预设主题包名称")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<UserThemeSettingsDB(id={self.id}, user_id={self.user_id}, theme_mode={self.theme_mode})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "theme_mode": self.theme_mode,
            "accent_color": self.accent_color,
            "font_size": self.font_size,
            "density": self.density,
            "custom_background": self.custom_background,
            "theme_preset": self.theme_preset,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ThemePresetDB(Base):
    """预设主题包数据库模型（未来扩展用）"""
    __tablename__ = "theme_presets"

    id = Column(String(36), primary_key=True, nullable=False)
    name = Column(String(50), unique=True, nullable=False, comment="主题包名称")
    display_name = Column(String(100), nullable=False, comment="显示名称")
    description = Column(String(500), nullable=True, comment="主题包描述")
    thumbnail_url = Column(String(500), nullable=True, comment="缩略图 URL")

    # 主题配置（JSON 字符串）
    config_json = Column(String(2000), nullable=True, comment="主题配置 JSON")

    # 是否付费
    is_premium = Column(Integer, default=0, comment="是否付费主题：0=免费，1=付费")
    price_cents = Column(Integer, default=0, comment="价格（美分）")

    # 状态
    is_active = Column(Integer, default=1, comment="是否启用：0=停用，1=启用")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<ThemePresetDB(id={self.id}, name={self.name})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "thumbnail_url": self.thumbnail_url,
            "is_premium": bool(self.is_premium),
            "price_cents": self.price_cents,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
