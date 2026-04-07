/**
 * AI Diagnosis 页面 - AI 深度诊断
 * Bento Grid & Monochromatic 设计风格
 */

import React, { useState } from 'react';
import { Card, Button, Input, Space, Tag, Alert, Spin, Descriptions, Collapse } from 'antd';
import {
  ThunderboltOutlined,
  SearchOutlined,
  CheckCircleOutlined,
  BugOutlined,
  WarningOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import type { Diagnosis as DiagnosisType, AIDiagnoseResponse } from '@/types';
import { aiNativeApi } from '@/services/api';
import { useChatStore } from '@/store';
import { colors, shadows, radii, spacing, typography, transitions, bentoGrid } from '@/styles/design-tokens';

const { TextArea } = Input;
const { Panel } = Collapse;

/**
 * Bento Grid 卡片容器
 */
interface BentoCardProps {
  title?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  noPadding?: boolean;
  highlight?: boolean;
}

const BentoCard: React.FC<BentoCardProps> = ({
  title,
  children,
  noPadding = false,
  highlight = false,
}) => {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div
      className="bento-card"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        background: highlight
          ? `linear-gradient(135deg, ${colors.primary[900]} 0%, ${colors.dark.bgCard} 100%)`
          : colors.dark.bgCard,
        borderRadius: radii.lg,
        border: `1px solid ${highlight ? colors.primary[700] : colors.dark.border}`,
        boxShadow: isHovered ? shadows.cardHover : shadows.card,
        transition: `all ${transitions.durations.normal} ${transitions.timing.easeInOut}`,
        overflow: 'hidden',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {title && (
        <div
          style={{
            padding: spacing[4],
            borderBottom: `1px solid ${colors.dark.border}`,
            background: `linear-gradient(135deg, rgba(255,255,255,0.02) 0%, transparent 100%)`,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: parseInt(spacing[2]) }}>
            {title}
          </div>
        </div>
      )}
      <div style={{ padding: noPadding ? 0 : spacing[4], flex: 1 }}>
        {children}
      </div>
    </div>
  );
};

/**
 * 诊断输入表单 - Bento 风格
 */
interface DiagnosisFormProps {
  serviceName: string;
  setServiceName: (value: string) => void;
  symptoms: string;
  setSymptoms: (value: string) => void;
  onDiagnose: () => void;
  loading: boolean;
}

const DiagnosisForm: React.FC<DiagnosisFormProps> = ({
  serviceName,
  setServiceName,
  symptoms,
  setSymptoms,
  onDiagnose,
  loading,
}) => {
  return (
    <BentoCard
      title={
        <>
          <BugOutlined style={{ color: colors.semantic.accent }} />
          <span style={{ color: colors.neutral[100], fontWeight: 600, fontSize: typography.fontSize.base }}>
            诊断配置
          </span>
        </>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: spacing[5] }}>
        {/* 服务名称输入 */}
        <div>
          <label style={{
            display: 'block',
            color: colors.neutral[400],
            fontSize: typography.fontSize.sm,
            fontWeight: 500,
            marginBottom: spacing[2],
          }}>
            服务名称（可选）
          </label>
          <Input
            placeholder="例如：payment-service"
            value={serviceName}
            onChange={(e) => setServiceName(e.target.value)}
            style={{
              background: colors.dark.bgCardHover,
              border: `1px solid ${colors.dark.border}`,
              color: colors.neutral[100],
              borderRadius: radii.md,
              padding: `${spacing[2]} ${spacing[3]}`,
              fontSize: typography.fontSize.base,
              transition: `all ${transitions.durations.fast}`,
            }}
            onFocus={(e) => {
              e.target.style.borderColor = colors.primary[600];
              e.target.style.boxShadow = `0 0 0 2px ${colors.primary[700]}40`;
            }}
            onBlur={(e) => {
              e.target.style.borderColor = colors.dark.border;
              e.target.style.boxShadow = 'none';
            }}
          />
        </div>

        {/* 症状描述输入 */}
        <div>
          <label style={{
            display: 'block',
            color: colors.neutral[400],
            fontSize: typography.fontSize.sm,
            fontWeight: 500,
            marginBottom: spacing[2],
          }}>
            症状描述（每行一个）
          </label>
          <TextArea
            placeholder="例如：&#10;API 响应超时&#10;错误率上升&#10;CPU 使用率高"
            rows={4}
            value={symptoms}
            onChange={(e) => setSymptoms(e.target.value)}
            style={{
              background: colors.dark.bgCardHover,
              border: `1px solid ${colors.dark.border}`,
              color: colors.neutral[100],
              borderRadius: radii.md,
              padding: `${spacing[2]} ${spacing[3]}`,
              fontSize: typography.fontSize.base,
              resize: 'none',
              transition: `all ${transitions.durations.fast}`,
            }}
            onFocus={(e) => {
              e.target.style.borderColor = colors.primary[600];
              e.target.style.boxShadow = `0 0 0 2px ${colors.primary[700]}40`;
            }}
            onBlur={(e) => {
              e.target.style.borderColor = colors.dark.border;
              e.target.style.boxShadow = 'none';
            }}
          />
        </div>

        {/* 诊断按钮 */}
        <Button
          type="primary"
          icon={<SearchOutlined />}
          onClick={onDiagnose}
          loading={loading}
          size="large"
          style={{
            background: `linear-gradient(135deg, ${colors.primary[600]} 0%, ${colors.primary[800]} 100%)`,
            border: 'none',
            borderRadius: radii.lg,
            padding: `${spacing[3]} ${spacing[6]}`,
            fontSize: typography.fontSize.base,
            fontWeight: 600,
            boxShadow: shadows.card,
            transition: `all ${transitions.durations.normal} ${transitions.timing.easeInOut}`,
            height: 'auto',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.boxShadow = `${shadows.cardHover}, 0 0 20px ${colors.primary[700]}60`;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = shadows.card;
          }}
        >
          {loading ? '正在诊断...' : '开始诊断'}
        </Button>
      </div>
    </BentoCard>
  );
};

/**
 * 诊断结果摘要 - Bento 风格
 */
const DiagnosisSummary: React.FC<{ diagnosis: DiagnosisType }> = ({ diagnosis }) => {
  const getConfidenceColor = (confidence: number) => {
    if (confidence > 0.8) return colors.semantic.success;
    if (confidence > 0.5) return colors.semantic.warning;
    return colors.semantic.error;
  };

  return (
    <BentoCard
      highlight
      title={
        <>
          <ThunderboltOutlined style={{ color: colors.semantic.accent }} />
          <span style={{ color: colors.neutral[100], fontWeight: 600, fontSize: typography.fontSize.base }}>
            诊断摘要
          </span>
        </>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: spacing[4] }}>
        {/* 根因 */}
        <div>
          <div style={{
            color: colors.neutral[400],
            fontSize: typography.fontSize.sm,
            fontWeight: 500,
            marginBottom: spacing[2],
          }}>
            根因
          </div>
          <div style={{
            background: colors.dark.bgCardHover,
            borderRadius: radii.md,
            padding: `${spacing[3]} ${spacing[4]}`,
            border: `1px solid ${colors.primary[700]}30`,
          }}>
            <span style={{
              color: colors.neutral[100],
              fontSize: typography.fontSize.base,
              fontWeight: 500,
            }}>
              {diagnosis.root_cause}
            </span>
          </div>
        </div>

        {/* 置信度和受影响服务 */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'auto 1fr',
          gap: spacing[4],
          alignItems: 'center',
        }}>
          <div>
            <div style={{
              color: colors.neutral[400],
              fontSize: typography.fontSize.sm,
              fontWeight: 500,
              marginBottom: spacing[2],
            }}>
              置信度
            </div>
            <Tag
              color={getConfidenceColor(diagnosis.confidence)}
              style={{
                borderRadius: radii.full,
                padding: `${spacing[2]} ${spacing[4]}`,
                fontSize: typography.fontSize.base,
                fontWeight: 600,
                border: `1px solid ${getConfidenceColor(diagnosis.confidence)}`,
                background: `${getConfidenceColor(diagnosis.confidence)}15`,
              }}
            >
              {(diagnosis.confidence * 100).toFixed(0)}%
            </Tag>
          </div>

          <div>
            <div style={{
              color: colors.neutral[400],
              fontSize: typography.fontSize.sm,
              fontWeight: 500,
              marginBottom: spacing[2],
            }}>
              受影响服务
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: spacing[2] }}>
              {diagnosis.impact_assessment.affected_services.map((s, i) => (
                <Tag
                  key={i}
                  style={{
                    borderRadius: radii.sm,
                    padding: `${spacing[1]} ${spacing[2]}`,
                    fontSize: typography.fontSize.xs,
                    background: colors.dark.bgCardHover,
                    border: `1px solid ${colors.dark.border}`,
                    color: colors.neutral[200],
                  }}
                >
                  {s}
                </Tag>
              ))}
            </div>
          </div>
        </div>
      </div>
    </BentoCard>
  );
};

/**
 * 自然语言报告 - Bento 风格
 */
const NaturalLanguageReport: React.FC<{ report: string }> = ({ report }) => {
  return (
    <BentoCard
      title={
        <>
          <InfoCircleOutlined style={{ color: colors.semantic.info }} />
          <span style={{ color: colors.neutral[100], fontWeight: 600, fontSize: typography.fontSize.base }}>
            诊断报告
          </span>
        </>
      }
    >
      <div style={{
        background: `${colors.semantic.success}10`,
        borderRadius: radii.md,
        padding: spacing[4],
        border: `1px solid ${colors.semantic.success}20`,
      }}>
        <div style={{
          color: colors.neutral[100],
          fontSize: typography.fontSize.base,
          lineHeight: typography.lineHeight.relaxed,
          whiteSpace: 'pre-wrap',
        }}>
          {report}
        </div>
      </div>
    </BentoCard>
  );
};

/**
 * 证据链 - Bento 风格折叠面板
 */
interface EvidenceChainProps {
  evidenceChain: DiagnosisType['evidence_chain'];
}

const EvidenceChain: React.FC<EvidenceChainProps> = ({ evidenceChain }) => {
  const getSeverityColor = (severity: string) => {
    const colorsMap: Record<string, string> = {
      low: colors.semantic.info,
      medium: colors.semantic.warning,
      high: '#f97316',
      critical: colors.semantic.error,
    };
    return colorsMap[severity] || colors.neutral[500];
  };

  return (
    <BentoCard
      title={
        <>
          <SearchOutlined style={{ color: colors.semantic.warning }} />
          <span style={{ color: colors.neutral[100], fontWeight: 600, fontSize: typography.fontSize.base }}>
            证据链
          </span>
        </>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: spacing[3] }}>
        {evidenceChain.map((evidence, index) => {
          const severityColor = getSeverityColor(evidence.severity);

          return (
            <div
              key={index}
              style={{
                background: colors.dark.bgCardHover,
                borderRadius: radii.lg,
                border: `1px solid ${colors.dark.border}`,
                overflow: 'hidden',
                transition: `all ${transitions.durations.fast}`,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = severityColor;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = colors.dark.border;
              }}
            >
              {/* 证据头部 */}
              <div
                style={{
                  padding: `${spacing[3]} ${spacing[4]}`,
                  background: `${severityColor}10`,
                  borderBottom: `1px solid ${colors.dark.border}`,
                  display: 'flex',
                  alignItems: 'center',
                  gap: spacing[3],
                }}
              >
                <Tag
                  color={severityColor}
                  style={{
                    borderRadius: radii.sm,
                    fontSize: typography.fontSize.xs,
                    fontWeight: 600,
                    padding: `0 ${spacing[2]}`,
                    background: `${severityColor}20`,
                    border: `1px solid ${severityColor}`,
                  }}
                >
                  {evidence.severity.toUpperCase()}
                </Tag>
                <span style={{
                  color: colors.neutral[100],
                  fontWeight: 500,
                  fontSize: typography.fontSize.sm,
                  flex: 1,
                }}>
                  {evidence.description}
                </span>
              </div>

              {/* 证据详情 */}
              <div style={{ padding: spacing[4] }}>
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'auto 1fr',
                  gap: `${spacing[2]} ${spacing[4]}`,
                  marginBottom: spacing[3],
                }}>
                  <span style={{ color: colors.neutral[500], fontSize: typography.fontSize.xs }}>类型</span>
                  <span style={{ color: colors.neutral[200], fontSize: typography.fontSize.sm }}>{evidence.type}</span>

                  <span style={{ color: colors.neutral[500], fontSize: typography.fontSize.xs }}>时间</span>
                  <span style={{ color: colors.neutral[200], fontSize: typography.fontSize.sm }}>
                    {new Date(evidence.timestamp).toLocaleString()}
                  </span>
                </div>

                {/* 数据展示 */}
                {evidence.data && (
                  <div>
                    <div style={{
                      color: colors.neutral[500],
                      fontSize: typography.fontSize.xs,
                      marginBottom: spacing[2],
                    }}>
                      数据
                    </div>
                    <pre style={{
                      background: colors.dark.bg,
                      borderRadius: radii.md,
                      padding: spacing[3],
                      color: colors.neutral[300],
                      fontSize: typography.fontSize.xs,
                      fontFamily: typography.fontFamily.mono,
                      overflow: 'auto',
                      maxHeight: 200,
                      margin: 0,
                    }}>
                      {JSON.stringify(evidence.data, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </BentoCard>
  );
};

/**
 * 推荐操作 - Bento 风格
 */
const RecommendedActions: React.FC<{ actions: DiagnosisType['recommended_actions'] }> = ({ actions }) => {
  const getRiskColor = (risk: string) => {
    const colorsMap: Record<string, string> = {
      low: colors.semantic.success,
      medium: colors.semantic.warning,
      high: colors.semantic.error,
    };
    return colorsMap[risk] || colors.neutral[500];
  };

  return (
    <BentoCard
      title={
        <>
          <CheckCircleOutlined style={{ color: colors.semantic.success }} />
          <span style={{ color: colors.neutral[100], fontWeight: 600, fontSize: typography.fontSize.base }}>
            推荐操作
          </span>
        </>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: spacing[3] }}>
        {actions.map((action, index) => {
          const riskColor = getRiskColor(action.risk_level);

          return (
            <div
              key={index}
              style={{
                padding: spacing[4],
                background: colors.dark.bgCardHover,
                borderRadius: radii.lg,
                border: `1px solid ${colors.dark.border}`,
                transition: `all ${transitions.durations.fast}`,
                position: 'relative',
                overflow: 'hidden',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = riskColor;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = colors.dark.border;
              }}
            >
              {/* 左侧强调条 */}
              <div
                style={{
                  position: 'absolute',
                  left: 0,
                  top: 0,
                  bottom: 0,
                  width: 3,
                  background: riskColor,
                }}
              />

              <div style={{ paddingLeft: spacing[3] }}>
                <div style={{
                  color: colors.neutral[100],
                  fontWeight: 600,
                  fontSize: typography.fontSize.base,
                  marginBottom: spacing[2],
                }}>
                  {action.name}
                </div>
                <div style={{
                  color: colors.neutral[400],
                  fontSize: typography.fontSize.sm,
                  lineHeight: typography.lineHeight.normal,
                  marginBottom: spacing[3],
                }}>
                  {action.description}
                </div>

                {/* 标签 */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: spacing[2] }}>
                  <Tag
                    color={riskColor}
                    style={{
                      borderRadius: radii.sm,
                      fontSize: typography.fontSize.xs,
                      padding: `0 ${spacing[2]}`,
                      background: `${riskColor}15`,
                      border: `1px solid ${riskColor}`,
                    }}
                  >
                    置信度 {(action.confidence * 100).toFixed(0)}%
                  </Tag>
                  <Tag
                    color={riskColor}
                    style={{
                      borderRadius: radii.sm,
                      fontSize: typography.fontSize.xs,
                      padding: `0 ${spacing[2]}`,
                      background: `${riskColor}15`,
                      border: `1px solid ${riskColor}`,
                    }}
                  >
                    风险：{action.risk_level}
                  </Tag>
                  {action.auto_executable && (
                    <Tag
                      color={colors.semantic.success}
                      style={{
                        borderRadius: radii.sm,
                        fontSize: typography.fontSize.xs,
                        padding: `0 ${spacing[2]}`,
                        background: `${colors.semantic.success}15`,
                        border: `1px solid ${colors.semantic.success}`,
                      }}
                    >
                      可自动执行
                    </Tag>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </BentoCard>
  );
};

/**
 * 加载状态 - Bento 风格
 */
const LoadingState: React.FC = () => {
  return (
    <BentoCard>
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: spacing[12],
      }}>
        <div
          style={{
            width: 64,
            height: 64,
            borderRadius: radii.xl,
            background: `linear-gradient(135deg, ${colors.primary[800]} 0%, ${colors.primary[900]} 100%)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: spacing[4],
            animation: 'pulse 2s ease-in-out infinite',
          }}
        >
          <SearchOutlined style={{ color: colors.primary[400], fontSize: 28 }} />
        </div>
        <div style={{
          color: colors.neutral[400],
          fontSize: typography.fontSize.lg,
          fontWeight: 500,
          marginBottom: spacing[2],
        }}>
          AI 正在分析系统状态
        </div>
        <div style={{
          color: colors.neutral[500],
          fontSize: typography.fontSize.sm,
        }}>
          构建证据链，定位根因...
        </div>
      </div>
    </BentoCard>
  );
};

/**
 * 主诊断页面
 */
const DiagnosisPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [serviceName, setServiceName] = useState('');
  const [symptoms, setSymptoms] = useState('');
  const [diagnosis, setDiagnosis] = useState<DiagnosisType | null>(null);
  const { addMessage } = useChatStore();

  const handleDiagnose = async () => {
    setLoading(true);
    try {
      const symptomsList = symptoms.split('\n').filter((s) => s.trim());
      const result: AIDiagnoseResponse = await aiNativeApi.diagnose(
        serviceName || undefined,
        symptomsList.length > 0 ? symptomsList : undefined,
        300
      );

      setDiagnosis({
        id: result.diagnosis_id,
        root_cause: result.root_cause,
        confidence: result.confidence,
        evidence_chain: result.evidence_chain,
        impact_assessment: result.impact_assessment,
        recommended_actions: result.recommended_actions,
        natural_language_report: result.natural_language_report,
        timestamp: new Date(),
      });

      // 添加到对话历史
      addMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content: `## 诊断报告\n\n${result.natural_language_report}`,
        timestamp: new Date(),
        confidence: result.confidence,
      });
    } catch (error) {
      console.error('Diagnosis failed:', error);
    } finally {
      setLoading(false);
    }
  };

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
              background: `linear-gradient(135deg, ${colors.semantic.accent} 0%, ${colors.primary[800]} 100%)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: shadows.glow,
            }}
          >
            <ThunderboltOutlined style={{ color: '#fff', fontSize: 20 }} />
          </div>
          AI 深度诊断
        </h1>
        <p style={{
          color: colors.neutral[500],
          marginTop: spacing[2],
          fontSize: typography.fontSize.base,
        }}>
          多 Agent 协同诊断，构建完整证据链，输出根因分析报告
        </p>
      </div>

      {/* Bento Grid 布局 */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
        gap: bentoGrid.gap.lg,
      }}>
        {/* 诊断输入表单 */}
        <div>
          <DiagnosisForm
            serviceName={serviceName}
            setServiceName={setServiceName}
            symptoms={symptoms}
            setSymptoms={setSymptoms}
            onDiagnose={handleDiagnose}
            loading={loading}
          />
        </div>

        {/* 诊断说明卡片 */}
        <div>
          <BentoCard
            title={
              <>
                <InfoCircleOutlined style={{ color: colors.semantic.info }} />
                <span style={{ color: colors.neutral[100], fontWeight: 600, fontSize: typography.fontSize.base }}>
                  诊断说明
                </span>
              </>
            }
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: spacing[3] }}>
              <div style={{
                display: 'flex',
                gap: spacing[3],
                padding: spacing[3],
                background: colors.dark.bgCardHover,
                borderRadius: radii.md,
              }}>
                <div style={{
                  width: 32,
                  height: 32,
                  borderRadius: radii.md,
                  background: `${colors.semantic.info}15`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: colors.semantic.info,
                  flexShrink: 0,
                }}>
                  1
                </div>
                <div>
                  <div style={{
                    color: colors.neutral[100],
                    fontWeight: 500,
                    fontSize: typography.fontSize.sm,
                    marginBottom: spacing[1],
                  }}>
                    输入服务名称
                  </div>
                  <div style={{
                    color: colors.neutral[400],
                    fontSize: typography.fontSize.xs,
                  }}>
                    指定需要诊断的服务（可选）
                  </div>
                </div>
              </div>

              <div style={{
                display: 'flex',
                gap: spacing[3],
                padding: spacing[3],
                background: colors.dark.bgCardHover,
                borderRadius: radii.md,
              }}>
                <div style={{
                  width: 32,
                  height: 32,
                  borderRadius: radii.md,
                  background: `${colors.semantic.warning}15`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: colors.semantic.warning,
                  flexShrink: 0,
                }}>
                  2
                </div>
                <div>
                  <div style={{
                    color: colors.neutral[100],
                    fontWeight: 500,
                    fontSize: typography.fontSize.sm,
                    marginBottom: spacing[1],
                  }}>
                    描述症状
                  </div>
                  <div style={{
                    color: colors.neutral[400],
                    fontSize: typography.fontSize.xs,
                  }}>
                    详细列出观察到的异常现象
                  </div>
                </div>
              </div>

              <div style={{
                display: 'flex',
                gap: spacing[3],
                padding: spacing[3],
                background: colors.dark.bgCardHover,
                borderRadius: radii.md,
              }}>
                <div style={{
                  width: 32,
                  height: 32,
                  borderRadius: radii.md,
                  background: `${colors.semantic.success}15`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: colors.semantic.success,
                  flexShrink: 0,
                }}>
                  3
                </div>
                <div>
                  <div style={{
                    color: colors.neutral[100],
                    fontWeight: 500,
                    fontSize: typography.fontSize.sm,
                    marginBottom: spacing[1],
                  }}>
                    获取诊断报告
                  </div>
                  <div style={{
                    color: colors.neutral[400],
                    fontSize: typography.fontSize.xs,
                  }}>
                    AI 分析并输出根因和建议
                  </div>
                </div>
              </div>
            </div>
          </BentoCard>
        </div>
      </div>

      {/* 诊断结果 */}
      {loading && (
        <div style={{ marginTop: spacing[6] }}>
          <LoadingState />
        </div>
      )}

      {diagnosis && !loading && (
        <div style={{ marginTop: spacing[6], display: 'flex', flexDirection: 'column', gap: spacing[6] }}>
          {/* 诊断摘要 */}
          <DiagnosisSummary diagnosis={diagnosis} />

          {/* 自然语言报告 */}
          <NaturalLanguageReport report={diagnosis.natural_language_report} />

          {/* 证据链 */}
          <EvidenceChain evidenceChain={diagnosis.evidence_chain} />

          {/* 推荐操作 */}
          <RecommendedActions actions={diagnosis.recommended_actions} />
        </div>
      )}
    </div>
  );
};

export default DiagnosisPage;
