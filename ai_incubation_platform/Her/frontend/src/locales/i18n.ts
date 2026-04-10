/**
 * i18n 配置
 * 支持中文、英文、日文、韩文
 */
import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

// 导入语言包
import zhCN from './zh'
import enUS from './en'
import jaJP from './ja'
import koKR from './ko'

// 语言资源
const resources = {
  zh: {
    translation: zhCN,
  },
  en: {
    translation: enUS,
  },
  ja: {
    translation: jaJP,
  },
  ko: {
    translation: koKR,
  },
}

// 支持的语言列表
export const SUPPORTED_LANGUAGES = [
  { code: 'zh', name: '简体中文', nativeName: '简体中文' },
  { code: 'en', name: 'English', nativeName: 'English' },
  { code: 'ja', name: 'Japanese', nativeName: '日本語' },
  { code: 'ko', name: 'Korean', nativeName: '한국어' },
] as const

export type LanguageCode = typeof SUPPORTED_LANGUAGES[number]['code']

// 初始化 i18n
i18n
  .use(LanguageDetector) // 自动检测用户语言
  .use(initReactI18next) // 绑定 react-i18next
  .init({
    resources,
    fallbackLng: 'zh', // 默认语言
    supportedLngs: ['zh', 'en', 'ja', 'ko'], // 支持的语言

    // 语言检测配置
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      lookupLocalStorage: 'her-language',
      caches: ['localStorage'],
    },

    interpolation: {
      escapeValue: false, // React 已经处理 XSS
    },

    // 调试模式（开发环境）
    debug: typeof process !== 'undefined' ? process.env.NODE_ENV === 'development' : false,
  })

export default i18n

/**
 * 切换语言
 */
export const changeLanguage = async (lang: LanguageCode) => {
  await i18n.changeLanguage(lang)
  localStorage.setItem('her-language', lang)
  // 更新 HTML lang 属性
  document.documentElement.lang = lang
}

/**
 * 获取当前语言
 */
export const getCurrentLanguage = (): LanguageCode => {
  return (i18n.language || 'zh') as LanguageCode
}

/**
 * 获取语言显示名称
 */
export const getLanguageName = (code: LanguageCode): string => {
  const lang = SUPPORTED_LANGUAGES.find(l => l.code === code)
  return lang?.nativeName || code
}