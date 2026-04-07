/**
 * Settings 页面 - 设置
 * Bento Grid & Monochromatic 设计风格
 */

import React from 'react';
import { Card, Switch, Slider, Alert, Form } from 'antd';
import {
  SettingOutlined,
  BellOutlined,
  MoonOutlined,
  RobotOutlined,
  ClockOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { useSettingsStore } from '@/store';
import { colors, shadows, radii, spacing, typography, transitions } from '@/styles/design-tokens';

/**
 * Bento Grid 卡片容器
 */
interface BentoCardProps {
  title?: React.ReactNode;
  children: React.ReactNode;
  description?: string;
}

const BentoCard: React.FC<BentoCardProps> = ({ title, children, description }) => {
  return (
    <div
      style={{
        background: colors.dark.bgCard,
        borderRadius: radii.lg,
        border: `1px solid ${colors.dark.border}`,
        boxShadow: shadows.card,
        overflow: 'hidden',
        transition: `all ${transitions.durations.normal} ${transitions.timing.easeInOut}`,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = shadows.cardHover;
        e.currentTarget.style.borderColor = colors.primary[700];
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = shadows.card;
        e.currentTarget.style.borderColor = colors.dark.border;
      }}
    >
      {title && (
        <div
          style={{
            padding: `${spacing[4]} ${spacing[5]}`,
            borderBottom: `1px solid ${colors.dark.border}`,
            background: `linear-gradient(135deg, rgba(255,255,255,0.02) 0%, transparent 100%)`,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: parseInt(spacing[3]) }}>
            {title}
          </div>
          {description && (
            <p style={{
              color: colors.neutral[500],
              fontSize: typography.fontSize.sm,
              margin: `${spacing[2]} 0 0 0`,
            }}>
              {description}
            </p>
          )}
        </div>
      )}
      <div style={{ padding: `${spacing[5]} ${spacing[5]}` }}>
        {children}
      </div>
    </div>
  );
};

/**
 * 设置项容器
 */
interface SettingItemProps {
  label: string;
  description?: string;
  children: React.ReactNode;
  icon?: React.ReactNode;
}

const SettingItem: React.FC<SettingItemProps> = ({ label, description, children, icon }) => {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: `${spacing[4]} 0`,
      borderBottom: `1px solid ${colors.dark.border}`,
    }}
    style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: `${spacing[4]} 0`,
      borderBottom: `1px solid ${colors.dark.border}`,
    }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: parseInt(spacing[3]) }}>
        {icon && (
          <div style={{
            width: 36,
            height: 36,
            borderRadius: radii.md,
            background: `${colors.primary[700]}20`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: colors.primary[400],
            fontSize: 18,
          }}>
            {icon}
          </div>
        )}
        <div>
          <div style={{
            color: colors.neutral[100],
            fontWeight: 500,
            fontSize: typography.fontSize.base,
            marginBottom: spacing[1],
          }}>
            {label}
          </div>
          {description && (
            <div style={{
              color: colors.neutral[500],
              fontSize: typography.fontSize.sm,
            }}>
              {description}
            </div>
          )}
        </div>
      </div>
      <div style={{ flexShrink: 0, marginLeft: spacing[4] }}>
        {children}
      </div>
    </div>
  );
};

/**
 * 自定义 Switch 样式
 */
interface CustomSwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  checkedChildren?: string;
  unCheckedChildren?: string;
}

const CustomSwitch: React.FC<CustomSwitchProps> = ({
  checked,
  onChange,
  checkedChildren = '开',
  unCheckedChildren = '关',
}) => {
  return (
    <div
      onClick={() => onChange(!checked)}
      style={{
        width: 44,
        height: 24,
        borderRadius: radii.full,
        background: checked
          ? `linear-gradient(135deg, ${colors.primary[500]} 0%, ${colors.primary[700]} 100%)`
          : colors.dark.bgCardHover,
        border: `1px solid ${checked ? colors.primary[500] : colors.dark.border}`,
        cursor: 'pointer',
        position: 'relative',
        transition: `all ${transitions.durations.normal} ${transitions.timing.easeInOut}`,
        display: 'flex',
        alignItems: 'center',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'scale(1.05)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'scale(1)';
      }}
    >
      <div
        style={{
          position: 'absolute',
          left: checked ? 'auto' : spacing[1],
          right: checked ? spacing[1] : 'auto',
          width: 20,
          height: 20,
          borderRadius: '50%',
          background: '#fff',
          boxShadow: shadows.card,
          transition: `all ${transitions.durations.normal} ${transitions.timing.easeInOut}`,
        }}
      />
    </div>
  );
};

/**
 * 设置页面
 */
const SettingsPage: React.FC = () => {
  const {
    theme,
    setTheme,
    autoRefresh,
    setAutoRefresh,
    refreshInterval,
    setRefreshInterval,
    aiAutoExecute,
    setAiAutoExecute,
    notificationsEnabled,
    setNotificationsEnabled,
  } = useSettingsStore();

  return (
    <div style={{ animation: 'fadeIn 0.3s ease' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: spacing[6] }}>
        <h1 style={{
          fontSize: typography.fontSize['4xl'],
          fontWeight: 700,
          color: colors.neutral[100],
          margin: 0,
          display: 'flex',
          alignItems: 'center',
          gap: spacing[3],
        }}>
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: radii.lg,
              background: `linear-gradient(135deg, ${colors.neutral[600]} 0%, ${colors.neutral[800]} 100%)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <SettingOutlined style={{ color: '#fff', fontSize: 20 }} />
          </div>
          设置
        </h1>
        <p style={{
          color: colors.neutral[500],
          marginTop: spacing[2],
          fontSize: typography.fontSize.base,
        }}>
          配置 AI 运行态优化平台的首选项
        </p>
      </div>

      {/* Bento Grid 布局 */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
        gap: spacing[6],
      }}>
        {/* AI 设置 */}
        <BentoCard
          title={
            <>
              <RobotOutlined style={{ color: colors.semantic.accent }} />
              <span style={{ color: colors.neutral[100], fontWeight: 600, fontSize: typography.fontSize.base }}>
                AI 设置
              </span>
            </>
          }
          description="配置 AI 自动行为和决策阈值"
        >
          <SettingItem
            label="AI 自动执行"
            description="当 AI 置信度超过 90% 时，自动执行修复操作"
            icon={<RobotOutlined />}
          >
            <CustomSwitch
              checked={aiAutoExecute}
              onChange={setAiAutoExecute}
              checkedChildren="开"
              unCheckedChildren="关"
            />
          </SettingItem>
        </BentoCard>

        {/* 通知设置 */}
        <BentoCard
          title={
            <>
              <BellOutlined style={{ color: colors.semantic.warning }} />
              <span style={{ color: colors.neutral[100], fontWeight: 600, fontSize: typography.fontSize.base }}>
                通知设置
              </span>
            </>
          }
          description="管理通知和告警偏好"
        >
          <SettingItem
            label="启用通知"
            description="接收系统告警和 AI 建议通知"
            icon={<BellOutlined />}
          >
            <CustomSwitch
              checked={notificationsEnabled}
              onChange={setNotificationsEnabled}
              checkedChildren="开"
              unCheckedChildren="关"
            />
          </SettingItem>

          <div style={{ marginTop: spacing[4] }}>
            <Alert
              type="info"
              message={
                <div style={{ display: 'flex', alignItems: 'center', gap: spacing[2] }}>
                  <InfoCircleOutlined />
                  <span>通知功能需要后端 WebSocket 支持</span>
                </div>
              }
              style={{
                background: `${colors.semantic.info}10`,
                border: `1px solid ${colors.semantic.info}20`,
                color: colors.neutral[300],
                fontSize: typography.fontSize.sm,
              }}
              showIcon={false}
            />
          </div>
        </BentoCard>

        {/* 数据刷新设置 */}
        <BentoCard
          title={
            <>
              <ClockOutlined style={{ color: colors.semantic.info }} />
              <span style={{ color: colors.neutral[100], fontWeight: 600, fontSize: typography.fontSize.base }}>
                数据刷新
              </span>
            </>
          }
          description="配置数据自动刷新行为"
        >
          <SettingItem
            label="自动刷新"
            description="定期刷新仪表板数据"
            icon={<ClockOutlined />}
          >
            <CustomSwitch
              checked={autoRefresh}
              onChange={setAutoRefresh}
              checkedChildren="开"
              unCheckedChildren="关"
            />
          </SettingItem>

          <div style={{ marginTop: spacing[4] }}>
            <div style={{
              color: colors.neutral[400],
              fontSize: typography.fontSize.sm,
              fontWeight: 500,
              marginBottom: spacing[3],
            }}>
              刷新间隔（秒）
            </div>
            <Slider
              min={10}
              max={300}
              step={10}
              value={refreshInterval}
              onChange={setRefreshInterval}
              marks={{
                10: <span style={{ color: colors.neutral[500], fontSize: typography.fontSize.xs }}>10s</span>,
                60: <span style={{ color: colors.neutral[500], fontSize: typography.fontSize.xs }}>1m</span>,
                120: <span style={{ color: colors.neutral[500], fontSize: typography.fontSize.xs }}>2m</span>,
                300: <span style={{ color: colors.neutral[500], fontSize: typography.fontSize.xs }}>5m</span>,
              }}
              trackStyle={{
                background: `linear-gradient(135deg, ${colors.primary[500]} 0%, ${colors.primary[700]} 100%)`,
              }}
              handleStyle={{
                borderColor: colors.primary[500],
                backgroundColor: '#fff',
                boxShadow: shadows.card,
                cursor: 'pointer',
              }}
              railStyle={{
                background: colors.dark.bgCardHover,
                border: 'none',
              }}
              style={{ maxWidth: '100%' }}
            />
            <div style={{
              color: colors.neutral[400],
              fontSize: typography.fontSize.sm,
              marginTop: spacing[2],
              textAlign: 'center',
            }}>
              当前设置：<span style={{ color: colors.primary[400], fontWeight: 600 }}>{refreshInterval}</span> 秒
            </div>
          </div>
        </BentoCard>

        {/* 显示设置 */}
        <BentoCard
          title={
            <>
              <MoonOutlined style={{ color: colors.primary[400] }} />
              <span style={{ color: colors.neutral[100], fontWeight: 600, fontSize: typography.fontSize.base }}>
                显示设置
              </span>
            </>
          }
          description="自定义界面外观和主题"
        >
          <SettingItem
            label="深色模式"
            description="当前仅支持深色主题"
            icon={<MoonOutlined />}
          >
            <CustomSwitch
              checked={true}
              onChange={() => {}}
              checkedChildren="开"
              unCheckedChildren="关"
            />
          </SettingItem>

          <div style={{ marginTop: spacing[4] }}>
            <Alert
              type="info"
              message="浅色主题将在未来版本中提供"
              style={{
                background: `${colors.semantic.info}10`,
                border: `1px solid ${colors.semantic.info}20`,
                color: colors.neutral[400],
                fontSize: typography.fontSize.sm,
              }}
              showIcon={false}
            />
          </div>
        </BentoCard>
      </div>

      {/* 关于 - 全宽 */}
      <div style={{ marginTop: spacing[6] }}>
        <BentoCard
          title={
            <>
              <InfoCircleOutlined style={{ color: colors.semantic.info }} />
              <span style={{ color: colors.neutral[100], fontWeight: 600, fontSize: typography.fontSize.base }}>
                关于
              </span>
            </>
          }
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: spacing[3] }}>
            <div style={{
              color: colors.neutral[100],
              fontSize: typography.fontSize.lg,
              fontWeight: 600,
            }}>
              AI 运行态优化平台 v4.0 AI Native
            </div>
            <p style={{
              color: colors.neutral[400],
              fontSize: typography.fontSize.sm,
              lineHeight: typography.lineHeight.relaxed,
              margin: 0,
            }}>
              基于 DeerFlow 2.0 Agent 框架，提供 AI 驱动的性能监控、异常诊断、自主修复和优化建议。
              采用 Bento Grid 布局和 Monochromatic 配色方案，打造精致的 Linear.app 风格用户界面。
            </p>

            {/* 技术栈标签 */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: spacing[2], marginTop: spacing[3] }}>
              {['React', 'TypeScript', 'Ant Design', 'Tailwind CSS', 'Bento Grid', 'AI Native'].map((tech) => (
                <span
                  key={tech}
                  style={{
                    padding: `${spacing[1]} ${spacing[3]}`,
                    background: colors.dark.bgCardHover,
                    border: `1px solid ${colors.dark.border}`,
                    borderRadius: radii.full,
                    color: colors.neutral[300],
                    fontSize: typography.fontSize.xs,
                    fontWeight: 500,
                  }}
                >
                  {tech}
                </span>
              ))}
            </div>
          </div>
        </BentoCard>
      </div>
    </div>
  );
};

export default SettingsPage;
