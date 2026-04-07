/**
 * 技能雷达图组件
 * 可视化展示技能分析结果
 */
import React from 'react';
import { Card, Row, Col, Progress, Tag, Typography, Space, Table } from 'antd';
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  RiseOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import './SkillRadar.less';

const { Title, Text } = Typography;

interface Skill {
  name: string;
  level: 'beginner' | 'intermediate' | 'advanced' | 'expert';
  score?: number;
  category?: string;
}

interface SkillRadarProps {
  data?: {
    skills?: Skill[];
    strengths?: string[];
    areas_for_improvement?: string[];
    profile_summary?: {
      total_skills: number;
      avg_level: string;
    };
    [key: string]: any;
  };
}

const SkillRadar: React.FC<SkillRadarProps> = ({ data }) => {
  const skills = data?.skills || [];
  const strengths = data?.strengths || [];
  const areasForImprovement = data?.areas_for_improvement || [];

  // 将技能水平转换为分数
  const getLevelScore = (level: string): number => {
    const scores: Record<string, number> = {
      beginner: 25,
      intermediate: 50,
      advanced: 75,
      expert: 100,
    };
    return scores[level] || 50;
  };

  const getLevelColor = (level: string): string => {
    const colors: Record<string, string> = {
      beginner: '#ff4d4f',
      intermediate: '#faad14',
      advanced: '#1890ff',
      expert: '#52c41a',
    };
    return colors[level] || '#d9d9d9';
  };

  const getLevelLabel = (level: string): string => {
    const labels: Record<string, string> = {
      beginner: '入门',
      intermediate: '中级',
      advanced: '高级',
      expert: '专家',
    };
    return labels[level] || level;
  };

  // 准备雷达图数据
  const radarData = skills.slice(0, 8).map((skill) => ({
    name: skill.name,
    value: getLevelScore(skill.level),
  }));

  const radarOption = {
    radar: {
      indicator: radarData.map((d) => ({ name: d.name, max: 100 })),
      shape: 'circle',
      splitNumber: 4,
      axisName: {
        color: '#666',
        fontSize: 12,
      },
      splitLine: {
        lineStyle: {
          color: '#e8e8e8',
        },
      },
      splitArea: {
        show: true,
        areaStyle: {
          color: ['rgba(114, 46, 209, 0.1)', 'rgba(114, 46, 209, 0.05)', 'rgba(114, 46, 209, 0.02)', 'rgba(114, 46, 209, 0.01)'],
        },
      },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: radarData.map((d) => d.value),
            name: '技能水平',
            areaStyle: {
              color: 'rgba(114, 46, 209, 0.5)',
            },
            lineStyle: {
              color: '#722ed1',
              width: 2,
            },
            itemStyle: {
              color: '#722ed1',
            },
          },
        ],
      },
    ],
    tooltip: {
      formatter: (params: any) => {
        return `${params.name}: ${params.value[0]}`;
      },
    },
  };

  // 技能表格数据
  const skillTableData = skills.map((skill, index) => ({
    key: index,
    name: skill.name,
    level: getLevelLabel(skill.level),
    score: getLevelScore(skill.level),
    category: skill.category || '通用',
  }));

  const columns = [
    {
      title: '技能名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '类别',
      dataIndex: 'category',
      key: 'category',
    },
    {
      title: '水平',
      dataIndex: 'level',
      key: 'level',
      render: (level: string, record: any) => (
        <Space>
          <Progress
            type="line"
            percent={record.score}
            size="small"
            strokeColor={getLevelColor(skills[record.key]?.level)}
            format={() => level}
          />
        </Space>
      ),
    },
  ];

  return (
    <div className="skill-radar-container">
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card size="small" className="radar-card">
            <Title level={5}>技能分布</Title>
            <ReactECharts option={radarOption} style={{ height: 300 }} />
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card size="small" className="skills-table-card">
            <Title level={5}>技能详情</Title>
            <Table
              columns={columns}
              dataSource={skillTableData}
              pagination={false}
              size="small"
              scroll={{ y: 300 }}
            />
          </Card>
        </Col>
      </Row>

      {(strengths.length > 0 || areasForImprovement.length > 0) && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          {strengths.length > 0 && (
            <Col xs={24} sm={12}>
              <Card size="small" className="strengths-card">
                <div className="card-header">
                  <CheckCircleOutlined className="strength-icon" />
                  <Title level={5}>优势技能</Title>
                </div>
                <Space wrap>
                  {strengths.map((strength, index) => (
                    <Tag key={index} color="green">
                      {strength}
                    </Tag>
                  ))}
                </Space>
              </Card>
            </Col>
          )}

          {areasForImprovement.length > 0 && (
            <Col xs={24} sm={12}>
              <Card size="small" className="improvement-card">
                <div className="card-header">
                  <ExclamationCircleOutlined className="improvement-icon" />
                  <Title level={5}>提升方向</Title>
                </div>
                <Space wrap>
                  {areasForImprovement.map((area, index) => (
                    <Tag key={index} color="orange">
                      <RiseOutlined /> {area}
                    </Tag>
                  ))}
                </Space>
              </Card>
            </Col>
          )}
        </Row>
      )}
    </div>
  );
};

export default SkillRadar;
