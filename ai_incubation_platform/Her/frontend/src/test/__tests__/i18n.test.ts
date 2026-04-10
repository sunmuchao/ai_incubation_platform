/**
 * 国际化测试
 */
import i18n from '../../locales/i18n'
import { SUPPORTED_LANGUAGES, changeLanguage, getCurrentLanguage, getLanguageName } from '../../locales/i18n'

describe('i18n 国际化测试', () => {
  beforeEach(() => {
    // 重置语言为默认
    i18n.changeLanguage('zh')
  })

  describe('语言配置', () => {
    it('应该支持4种语言', () => {
      expect(SUPPORTED_LANGUAGES).toHaveLength(4)
      expect(SUPPORTED_LANGUAGES.map(l => l.code)).toEqual(['zh', 'en', 'ja', 'ko'])
    })

    it('每种语言应该有name和nativeName', () => {
      SUPPORTED_LANGUAGES.forEach(lang => {
        expect(lang).toHaveProperty('code')
        expect(lang).toHaveProperty('name')
        expect(lang).toHaveProperty('nativeName')
        expect(lang.code).toBeTruthy()
        expect(lang.name).toBeTruthy()
        expect(lang.nativeName).toBeTruthy()
      })
    })
  })

  describe('翻译测试', () => {
    it('中文翻译应该正确', () => {
      i18n.changeLanguage('zh')
      expect(i18n.t('app.name')).toBe('Her')
      expect(i18n.t('auth.login')).toBe('登录')
      expect(i18n.t('common.loading')).toBe('加载中...')
    })

    it('英文翻译应该正确', () => {
      i18n.changeLanguage('en')
      expect(i18n.t('app.name')).toBe('Her')
      expect(i18n.t('auth.login')).toBe('Login')
      expect(i18n.t('common.loading')).toBe('Loading...')
    })

    it('日文翻译应该正确', () => {
      i18n.changeLanguage('ja')
      expect(i18n.t('app.name')).toBe('Her')
      expect(i18n.t('auth.login')).toBe('ログイン')
      expect(i18n.t('common.loading')).toBe('読み込み中...')
    })

    it('韩文翻译应该正确', () => {
      i18n.changeLanguage('ko')
      expect(i18n.t('app.name')).toBe('Her')
      expect(i18n.t('auth.login')).toBe('로그인')
      expect(i18n.t('common.loading')).toBe('로딩 중...')
    })
  })

  describe('嵌套翻译测试', () => {
    it('应该正确翻译嵌套键', () => {
      i18n.changeLanguage('zh')
      expect(i18n.t('nav.home')).toBe('首页')
      expect(i18n.t('nav.chat')).toBe('聊天')
      expect(i18n.t('settings.language')).toBe('语言设置')
    })

    it('应该支持带参数的翻译', () => {
      i18n.changeLanguage('zh')
      expect(i18n.t('home.greeting', { name: '测试' })).toBe('你好，测试')
    })
  })

  describe('语言切换功能', () => {
    it('changeLanguage 应该正确切换语言', async () => {
      await changeLanguage('en')
      expect(getCurrentLanguage()).toBe('en')
      expect(i18n.t('common.loading')).toBe('Loading...')

      await changeLanguage('zh')
      expect(getCurrentLanguage()).toBe('zh')
      expect(i18n.t('common.loading')).toBe('加载中...')
    })

    it('getLanguageName 应该返回正确的语言名称', () => {
      expect(getLanguageName('zh')).toBe('简体中文')
      expect(getLanguageName('en')).toBe('English')
      expect(getLanguageName('ja')).toBe('日本語')
      expect(getLanguageName('ko')).toBe('한국어')
    })
  })

  describe('缺失键处理', () => {
    it('缺失的键应该返回键本身', () => {
      const result = i18n.t('nonexistent.key')
      expect(result).toBeTruthy()
    })
  })

  describe('语言包完整性', () => {
    const requiredKeys = [
      'app.name',
      'app.slogan',
      'auth.login',
      'auth.logout',
      'nav.home',
      'nav.chat',
      'common.loading',
      'common.confirm',
      'common.cancel',
      'language.title',
    ]

    it.each(SUPPORTED_LANGUAGES)('$code 语言包应该包含所有必需的键', async (lang) => {
      await i18n.changeLanguage(lang.code)

      requiredKeys.forEach(key => {
        const result = i18n.t(key)
        expect(result).toBeTruthy()
        expect(result).not.toBe(key) // 确保翻译存在
      })
    })
  })
})