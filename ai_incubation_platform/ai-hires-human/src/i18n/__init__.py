"""
国际化 (i18n) 核心服务。

功能：
1. 多语言翻译管理
2. 语言偏好设置
3. 自动语言检测
4. 翻译缓存
"""
import os
from typing import Dict, Optional
from functools import lru_cache

# 支持的语言列表
SUPPORTED_LANGUAGES = {
    "zh_CN": "简体中文",
    "en_US": "English",
    "ja_JP": "日本語",
    "ko_KR": "한국어",
}

DEFAULT_LANGUAGE = "zh_CN"


class I18nService:
    """
    国际化服务。

    核心功能：
    1. 翻译文本获取
    2. 语言偏好管理
    3. 翻译缓存
    """

    def __init__(self):
        self._translations: Dict[str, Dict[str, str]] = {}
        self._load_all_translations()

    def _load_all_translations(self) -> None:
        """加载所有翻译文件。"""
        for lang_code in SUPPORTED_LANGUAGES:
            try:
                module = __import__(f"i18n.{lang_code}", fromlist=["TRANSLATIONS"])
                self._translations[lang_code] = module.TRANSLATIONS
            except ImportError:
                self._translations[lang_code] = {}

    def get(self, key: str, lang: str = DEFAULT_LANGUAGE, default: Optional[str] = None) -> str:
        """
        获取翻译文本。

        Args:
            key: 翻译键，如 "task.title"
            lang: 语言代码，如 "zh_CN", "en_US"
            default: 默认值（如果翻译不存在）

        Returns:
            翻译后的文本
        """
        if lang not in self._translations:
            lang = DEFAULT_LANGUAGE

        translations = self._translations.get(lang, {})
        return translations.get(key, default or key)

    def t(self, key: str, lang: str = DEFAULT_LANGUAGE, **kwargs) -> str:
        """
        获取翻译文本并格式化。

        Args:
            key: 翻译键
            lang: 语言代码
            **kwargs: 格式化参数

        Returns:
            格式化后的翻译文本

        Example:
            >>> i18n.t("task.reward", lang="zh_CN", amount=100, currency="CNY")
            '报酬：100 CNY'
        """
        text = self.get(key, lang)
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text

    def get_supported_languages(self) -> Dict[str, str]:
        """获取支持的语言列表。"""
        return SUPPORTED_LANGUAGES.copy()

    def detect_language(self, accept_language: Optional[str] = None) -> str:
        """
        根据 Accept-Language 头检测用户语言偏好。

        Args:
            accept_language: HTTP Accept-Language 头

        Returns:
            最佳匹配的语言代码
        """
        if not accept_language:
            return DEFAULT_LANGUAGE

        # 解析 Accept-Language 头
        # 格式示例："zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
        languages = []
        for part in accept_language.split(","):
            part = part.strip()
            if ";" in part:
                lang, quality = part.split(";")
                try:
                    q = float(quality.split("=")[1])
                except (ValueError, IndexError):
                    q = 1.0
            else:
                lang = part
                q = 1.0
            languages.append((lang.strip(), q))

        # 按质量排序
        languages.sort(key=lambda x: x[1], reverse=True)

        # 找到最佳匹配
        for lang_code, _ in languages:
            # 规范化语言代码
            normalized = lang_code.replace("-", "_")

            # 精确匹配
            if normalized in SUPPORTED_LANGUAGES:
                return normalized

            # 语言前缀匹配 (如 zh 匹配 zh_CN)
            lang_prefix = normalized.split("_")[0]
            for supported in SUPPORTED_LANGUAGES:
                if supported.startswith(lang_prefix):
                    return supported

        return DEFAULT_LANGUAGE


# 全局实例
_i18n_service: Optional[I18nService] = None


def get_i18n_service() -> I18nService:
    """获取国际化服务实例。"""
    global _i18n_service
    if _i18n_service is None:
        _i18n_service = I18nService()
    return _i18n_service


def t(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """快捷翻译函数。"""
    return get_i18n_service().t(key, lang, **kwargs)


def get_supported_languages() -> Dict[str, str]:
    """获取支持的语言列表。"""
    return get_i18n_service().get_supported_languages()


def detect_language(accept_language: Optional[str] = None) -> str:
    """检测用户语言偏好。"""
    return get_i18n_service().detect_language(accept_language)
