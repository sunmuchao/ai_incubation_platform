/**
 * 前端国际化模块
 * 支持多语言切换、RTL 布局、本地化格式化
 */

class I18n {
    constructor() {
        this.currentLang = localStorage.getItem('lang') || 'en';
        this.translations = {};
        this.rtlLanguages = ['ar', 'he', 'fa', 'ur'];
        this.supportedLanguages = {
            'en': 'English',
            'zh': '简体中文',
            'zh-TW': '繁體中文',
            'ja': '日本語',
            'ko': '한국어',
            'es': 'Español',
            'fr': 'Français',
            'de': 'Deutsch',
            'ru': 'Русский',
            'ar': 'العربية'
        };
    }

    /**
     * 初始化国际化模块
     */
    async init() {
        await this.loadTranslations(this.currentLang);
        this.applyLanguageDirection();
        this.translatePage();
    }

    /**
     * 加载翻译文件
     */
    async loadTranslations(lang) {
        try {
            const response = await fetch(`/api/i18n/locale/${lang}`);
            if (response.ok) {
                const data = await response.json();
                this.translations = data.translations;
            } else {
                console.warn(`Failed to load translations for ${lang}, using fallback`);
                this.translations = {};
            }
        } catch (error) {
            console.error('Error loading translations:', error);
            this.translations = {};
        }
    }

    /**
     * 翻译文本
     */
    t(key, ...args) {
        let translation = this.translations[key] || key;

        // 格式化参数
        if (args.length > 0) {
            args.forEach((arg, index) => {
                translation = translation.replace(new RegExp(`\\{${index}\\}`, 'g'), arg);
            });
        }

        return translation;
    }

    /**
     * 翻译页面
     */
    translatePage() {
        // 翻译所有带 data-i18n 属性的元素
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            const args = element.getAttribute('data-i18n-args');

            if (key) {
                const argsArray = args ? args.split(',') : [];
                element.textContent = this.t(key, ...argsArray);
            }
        });

        // 翻译所有带 i18n-placeholder 属性的输入框
        document.querySelectorAll('[i18n-placeholder]').forEach(element => {
            const key = element.getAttribute('i18n-placeholder');
            if (key) {
                element.placeholder = this.t(key);
            }
        });

        // 翻译所有带 i18n-title 属性的元素
        document.querySelectorAll('[i18n-title]').forEach(element => {
            const key = element.getAttribute('i18n-title');
            if (key) {
                element.title = this.t(key);
            }
        });

        // 更新 HTML lang 属性
        document.documentElement.lang = this.currentLang;
    }

    /**
     * 应用语言方向（LTR/RTL）
     */
    applyLanguageDirection() {
        const isRTL = this.rtlLanguages.includes(this.currentLang);
        document.documentElement.dir = isRTL ? 'rtl' : 'ltr';
        document.body.classList.toggle('rtl', isRTL);
        document.body.classList.toggle('ltr', !isRTL);
    }

    /**
     * 切换语言
     */
    async setLanguage(lang) {
        if (this.supportedLanguages[lang]) {
            this.currentLang = lang;
            localStorage.setItem('lang', lang);
            await this.loadTranslations(lang);
            this.applyLanguageDirection();
            this.translatePage();

            // 触发语言切换事件
            window.dispatchEvent(new CustomEvent('languageChanged', {
                detail: { lang, isRTL: this.rtlLanguages.includes(lang) }
            }));
        }
    }

    /**
     * 获取支持的语言列表
     */
    getSupportedLanguages() {
        return Object.entries(this.supportedLanguages).map(([code, name]) => ({
            code,
            name,
            isRTL: this.rtlLanguages.includes(code)
        }));
    }

    /**
     * 格式化日期时间
     */
    formatDateTime(date, options = {}) {
        const defaultOptions = {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        };

        const mergedOptions = { ...defaultOptions, ...options };

        // 根据语言调整日期格式
        if (this.currentLang === 'zh' || this.currentLang === 'zh-TW') {
            return date.toLocaleString('zh-CN', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } else if (this.currentLang === 'ja') {
            return date.toLocaleString('ja-JP', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } else if (this.currentLang === 'ko') {
            return date.toLocaleString('ko-KR', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        }

        return date.toLocaleString(this.currentLang, mergedOptions);
    }

    /**
     * 格式化相对时间
     */
    formatRelativeTime(date) {
        const now = new Date();
        const diffMs = now - date;
        const diffSec = Math.floor(diffMs / 1000);
        const diffMin = Math.floor(diffSec / 60);
        const diffHour = Math.floor(diffMin / 60);
        const diffDay = Math.floor(diffHour / 24);
        const diffWeek = Math.floor(diffDay / 7);
        const diffMonth = Math.floor(diffDay / 30);

        if (diffSec < 60) {
            return this.t('time_just_now');
        } else if (diffMin < 60) {
            return this.t('time_minutes_ago', diffMin);
        } else if (diffHour < 24) {
            return this.t('time_hours_ago', diffHour);
        } else if (diffDay < 7) {
            return this.t('time_days_ago', diffDay);
        } else if (diffWeek < 4) {
            return this.t('time_weeks_ago', diffWeek);
        } else {
            return this.t('time_months_ago', diffMonth);
        }
    }

    /**
     * 格式化数字
     */
    formatNumber(num, options = {}) {
        return new Intl.NumberFormat(this.currentLang, options).format(num);
    }

    /**
     * 格式化货币
     */
    formatCurrency(amount, currency = 'USD') {
        return new Intl.NumberFormat(this.currentLang, {
            style: 'currency',
            currency: currency
        }).format(amount);
    }

    /**
     * 创建语言选择器
     */
    createLanguageSelector(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const select = document.createElement('select');
        select.className = 'language-selector';
        select.value = this.currentLang;

        Object.entries(this.supportedLanguages).forEach(([code, name]) => {
            const option = document.createElement('option');
            option.value = code;
            option.textContent = name;
            if (this.rtlLanguages.includes(code)) {
                option.style.direction = 'rtl';
            }
            select.appendChild(option);
        });

        select.addEventListener('change', (e) => {
            this.setLanguage(e.target.value);
        });

        container.appendChild(select);
    }
}

// 创建全局实例
window.i18n = new I18n();

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    window.i18n.init();
});
