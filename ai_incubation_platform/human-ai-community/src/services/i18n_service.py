"""
国际化服务 (i18n Service)
提供多语言翻译、时区适配、本地化内容支持
"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
import pytz

class I18nService:
    """国际化服务类"""

    # 支持的语言
    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'zh': '简体中文',
        'zh-TW': '繁體中文',
        'ja': '日本語',
        'ko': '한국어',
        'es': 'Español',
        'fr': 'Français',
        'de': 'Deutsch',
        'ru': 'Русский',
        'ar': 'العربية'  # RTL
    }

    # RTL 语言
    RTL_LANGUAGES = {'ar', 'he', 'fa', 'ur'}

    # 默认语言
    DEFAULT_LANGUAGE = 'en'

    def __init__(self, translations_dir: str = None):
        """初始化国际化服务"""
        if translations_dir is None:
            translations_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'content',
                'translations'
            )
        self.translations_dir = translations_dir
        self._translations: Dict[str, Dict[str, str]] = {}
        self._load_all_translations()

    def _load_all_translations(self):
        """加载所有翻译文件"""
        if not os.path.exists(self.translations_dir):
            os.makedirs(self.translations_dir, exist_ok=True)
            self._create_default_translations()

        for lang in self.SUPPORTED_LANGUAGES.keys():
            self._load_translation(lang)

    def _create_default_translations(self):
        """创建默认翻译文件"""
        # 英文翻译（默认）
        en_translations = {
            # 通用
            'welcome': 'Welcome',
            'goodbye': 'Goodbye',
            'save': 'Save',
            'cancel': 'Cancel',
            'delete': 'Delete',
            'edit': 'Edit',
            'create': 'Create',
            'update': 'Update',
            'search': 'Search',
            'loading': 'Loading...',
            'success': 'Success',
            'error': 'Error',
            'confirm': 'Confirm',

            # 导航
            'nav_home': 'Home',
            'nav_posts': 'Posts',
            'nav_channels': 'Channels',
            'nav_profile': 'Profile',
            'nav_settings': 'Settings',
            'nav_admin': 'Admin',

            # 用户相关
            'user_login': 'Login',
            'user_logout': 'Logout',
            'user_register': 'Register',
            'user_profile': 'Profile',
            'user_settings': 'Settings',

            # 内容相关
            'post_title': 'Title',
            'post_content': 'Content',
            'post_create': 'Create Post',
            'post_edit': 'Edit Post',
            'post_delete': 'Delete Post',
            'post_reply': 'Reply',
            'post_like': 'Like',
            'post_share': 'Share',

            # 社区相关
            'community_name': 'Community Name',
            'community_description': 'Description',
            'community_members': 'Members',
            'community_join': 'Join',
            'community_leave': 'Leave',

            # 通知
            'notification_new': 'New Notification',
            'notification_view_all': 'View All',
            'notification_mark_read': 'Mark as Read',

            # AI 相关
            'ai_author': 'AI Author',
            'ai_human': 'Human Author',
            'ai_mixed': 'Human + AI',
            'ai_assisted': 'AI-Assisted',
            'ai_generated': 'AI-Generated',
            'ai_model': 'AI Model',

            # 时间相关
            'time_just_now': 'Just now',
            'time_minutes_ago': '{0} minutes ago',
            'time_hours_ago': '{0} hours ago',
            'time_days_ago': '{0} days ago',
            'time_weeks_ago': '{0} weeks ago',
            'time_months_ago': '{0} months ago',

            # 错误消息
            'error_not_found': 'Not Found',
            'error_unauthorized': 'Unauthorized',
            'error_server': 'Server Error',
            'error_network': 'Network Error',

            # 验证
            'validate_required': 'This field is required',
            'validate_email': 'Please enter a valid email',
            'validate_min_length': 'Minimum length is {0} characters',
            'validate_max_length': 'Maximum length is {0} characters',
        }

        # 中文翻译
        zh_translations = {
            # 通用
            'welcome': '欢迎',
            'goodbye': '再见',
            'save': '保存',
            'cancel': '取消',
            'delete': '删除',
            'edit': '编辑',
            'create': '创建',
            'update': '更新',
            'search': '搜索',
            'loading': '加载中...',
            'success': '成功',
            'error': '错误',
            'confirm': '确认',

            # 导航
            'nav_home': '首页',
            'nav_posts': '帖子',
            'nav_channels': '频道',
            'nav_profile': '个人资料',
            'nav_settings': '设置',
            'nav_admin': '管理',

            # 用户相关
            'user_login': '登录',
            'user_logout': '退出',
            'user_register': '注册',
            'user_profile': '个人资料',
            'user_settings': '设置',

            # 内容相关
            'post_title': '标题',
            'post_content': '内容',
            'post_create': '创建帖子',
            'post_edit': '编辑帖子',
            'post_delete': '删除帖子',
            'post_reply': '回复',
            'post_like': '点赞',
            'post_share': '分享',

            # 社区相关
            'community_name': '社区名称',
            'community_description': '描述',
            'community_members': '成员',
            'community_join': '加入',
            'community_leave': '退出',

            # 通知
            'notification_new': '新通知',
            'notification_view_all': '查看全部',
            'notification_mark_read': '标记为已读',

            # AI 相关
            'ai_author': 'AI 作者',
            'ai_human': '人类作者',
            'ai_mixed': '人类+AI',
            'ai_assisted': 'AI 辅助',
            'ai_generated': 'AI 生成',
            'ai_model': 'AI 模型',

            # 时间相关
            'time_just_now': '刚刚',
            'time_minutes_ago': '{0} 分钟前',
            'time_hours_ago': '{0} 小时前',
            'time_days_ago': '{0} 天前',
            'time_weeks_ago': '{0} 周前',
            'time_months_ago': '{0} 个月前',

            # 错误消息
            'error_not_found': '未找到',
            'error_unauthorized': '未授权',
            'error_server': '服务器错误',
            'error_network': '网络错误',

            # 验证
            'validate_required': '此字段为必填项',
            'validate_email': '请输入有效的邮箱地址',
            'validate_min_length': '最少需要{0}个字符',
            'validate_max_length': '最多{0}个字符',
        }

        # 保存默认翻译
        self._save_translation('en', en_translations)
        self._save_translation('zh', zh_translations)

    def _save_translation(self, lang: str, translations: Dict[str, str]):
        """保存翻译到文件"""
        filepath = os.path.join(self.translations_dir, f'{lang}.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(translations, f, ensure_ascii=False, indent=2)

    def _load_translation(self, lang: str):
        """加载指定语言的翻译"""
        filepath = os.path.join(self.translations_dir, f'{lang}.json')
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                self._translations[lang] = json.load(f)
        else:
            self._translations[lang] = {}

    def t(self, key: str, lang: str = None, *args) -> str:
        """翻译文本

        Args:
            key: 翻译键
            lang: 语言代码，默认使用默认语言
            *args: 格式化参数

        Returns:
            翻译后的文本
        """
        if lang is None:
            lang = self.DEFAULT_LANGUAGE

        # 尝试获取翻译
        translation = self._translations.get(lang, {}).get(key)

        # 如果没有找到，尝试使用默认语言
        if translation is None:
            translation = self._translations.get(self.DEFAULT_LANGUAGE, {}).get(key)

        # 如果仍然没有找到，返回键名
        if translation is None:
            translation = key

        # 格式化参数
        if args:
            translation = translation.format(*args)

        return translation

    def is_rtl(self, lang: str = None) -> bool:
        """判断是否为 RTL 语言"""
        if lang is None:
            lang = self.DEFAULT_LANGUAGE
        return lang in self.RTL_LANGUAGES

    def get_language_name(self, lang: str) -> str:
        """获取语言名称"""
        return self.SUPPORTED_LANGUAGES.get(lang, lang)

    def get_supported_languages(self) -> Dict[str, str]:
        """获取支持的语言列表"""
        return self.SUPPORTED_LANGUAGES.copy()

    def format_datetime(self, dt: datetime, lang: str = None,
                        timezone: str = None) -> str:
        """格式化日期时间为本地化格式

        Args:
            dt: 日期时间对象
            lang: 语言代码
            timezone: 时区，默认 UTC

        Returns:
            格式化后的字符串
        """
        if timezone:
            dt = dt.astimezone(pytz.timezone(timezone))

        if lang in ['zh', 'zh-TW']:
            return dt.strftime('%Y年%m月%d日 %H:%M')
        elif lang == 'ja':
            return dt.strftime('%Y年%m月%d日 %H時%M分')
        elif lang == 'ko':
            return dt.strftime('%Y년%m월%d일 %H:%M')
        else:
            return dt.strftime('%Y-%m-%d %H:%M')

    def format_relative_time(self, dt: datetime, lang: str = None,
                            timezone: str = None) -> str:
        """格式化相对时间（如：5 分钟前）

        Args:
            dt: 日期时间对象
            lang: 语言代码
            timezone: 时区，默认 UTC

        Returns:
            相对时间字符串
        """
        if timezone:
            dt = dt.astimezone(pytz.timezone(timezone))

        now = datetime.now(pytz.UTC)
        diff = (now - dt).total_seconds()

        if lang is None:
            lang = self.DEFAULT_LANGUAGE

        if diff < 60:
            return self.t('time_just_now', lang)
        elif diff < 3600:
            minutes = int(diff // 60)
            return self.t('time_minutes_ago', lang, minutes)
        elif diff < 86400:
            hours = int(diff // 3600)
            return self.t('time_hours_ago', lang, hours)
        elif diff < 604800:
            days = int(diff // 86400)
            return self.t('time_days_ago', lang, days)
        elif diff < 2592000:
            weeks = int(diff // 604800)
            return self.t('time_weeks_ago', lang, weeks)
        else:
            months = int(diff // 2592000)
            return self.t('time_months_ago', lang, months)

    def add_translation(self, lang: str, key: str, value: str):
        """添加或更新翻译"""
        if lang not in self._translations:
            self._translations[lang] = {}
        self._translations[lang][key] = value
        self._save_translation(lang, self._translations[lang])

    def get_language_direction(self, lang: str) -> str:
        """获取语言书写方向"""
        return 'rtl' if self.is_rtl(lang) else 'ltr'


# 全局服务实例
_i18n_service: Optional[I18nService] = None

def get_i18n_service() -> I18nService:
    """获取国际化服务实例"""
    global _i18n_service
    if _i18n_service is None:
        _i18n_service = I18nService()
    return _i18n_service
