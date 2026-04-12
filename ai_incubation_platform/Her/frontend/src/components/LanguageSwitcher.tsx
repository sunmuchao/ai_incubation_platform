/**
 * 语言切换组件
 */
import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Modal, Button, Typography, Space, Divider } from 'antd'
import { GlobalOutlined, CheckOutlined } from '@ant-design/icons'
import { SUPPORTED_LANGUAGES, changeLanguage, getCurrentLanguage, type LanguageCode } from '../locales/i18n'
import './LanguageSwitcher.less'

const { Text } = Typography

interface LanguageSwitcherProps {
  /** 触发方式：按钮或图标 */
  trigger?: 'button' | 'icon'
  /** 按钮大小 */
  size?: 'small' | 'middle' | 'large'
  /** 是否显示当前语言名称 */
  showCurrentLang?: boolean
  /** 切换后的回调 */
  onChange?: (lang: LanguageCode) => void
}

const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({
  trigger = 'button',
  size = 'middle',
  showCurrentLang = true,
  onChange,
}) => {
  const { t } = useTranslation()
  const [modalVisible, setModalVisible] = useState(false)
  const [currentLang, setCurrentLang] = useState<LanguageCode>(getCurrentLanguage())
  const [loading, setLoading] = useState(false)

  // 切换语言
  const handleLanguageChange = async (lang: LanguageCode) => {
    if (lang === currentLang) {
      setModalVisible(false)
      return
    }

    setLoading(true)
    try {
      await changeLanguage(lang)
      setCurrentLang(lang)
      setModalVisible(false)
      onChange?.(lang)
    } finally {
      setLoading(false)
    }
  }

  // 打开语言选择弹窗
  const openModal = () => {
    setCurrentLang(getCurrentLanguage())
    setModalVisible(true)
  }

  return (
    <>
      {/* 触发器 */}
      {trigger === 'button' ? (
        <Button
          icon={<GlobalOutlined />}
          onClick={openModal}
          size={size}
          className="language-switcher-btn"
        >
          {showCurrentLang && (
            <span className="current-lang-name">
              {SUPPORTED_LANGUAGES.find(l => l.code === getCurrentLanguage())?.nativeName}
            </span>
          )}
        </Button>
      ) : (
        <Button
          type="text"
          icon={<GlobalOutlined />}
          onClick={openModal}
          size={size}
          className="language-switcher-icon"
        />
      )}

      {/* 语言选择弹窗 */}
      <Modal
        title={
          <Space>
            <GlobalOutlined />
            <span>{t('language.title')}</span>
          </Space>
        }
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        className="language-switcher-modal"
        width={320}
      >
        <div className="language-list">
          {SUPPORTED_LANGUAGES.map((lang) => (
            <div
              key={lang.code}
              className={`language-item ${currentLang === lang.code ? 'selected' : ''}`}
              onClick={() => !loading && handleLanguageChange(lang.code)}
            >
              <div className="language-item-content">
                <span className="language-native-name">{lang.nativeName}</span>
                {lang.code !== lang.nativeName && (
                  <span className="language-name">{lang.name}</span>
                )}
              </div>
              {currentLang === lang.code && (
                <CheckOutlined className="check-icon" />
              )}
            </div>
          ))}
        </div>

        <Divider />

        <div className="language-info">
          <Text type="secondary" className="info-text">
            {t('language.select')}
          </Text>
        </div>
      </Modal>
    </>
  )
}

export default LanguageSwitcher