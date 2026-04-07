/**
 * 机会卡片组件
 * 展示 AI 匹配的工作机会
 */
import React, { useState } from 'react';
import { Card, Row, Col, Tag, Button, Space, Typography, Progress, Modal, message } from 'antd';
import {
  ThunderboltOutlined,
  RiseOutlined,
  ProjectOutlined,
  RightOutlined,
  StarOutlined,
} from '@ant-design/icons';
import './OpportunityCards.less';

const { Title, Text, Paragraph } = Typography;

interface Opportunity {
  id: string;
  type: 'promotion' | 'transfer' | 'project';
  title: string;
  department?: string;
  match_score: number;
  description?: string;
  requirements?: string[];
  salary_range?: string;
}

interface OpportunityCardsProps {
  data?: {
    opportunities?: Opportunity[];
    [key: string]: any;
  };
}

const OpportunityCards: React.FC<OpportunityCardsProps> = ({ data }) => {
  const [selectedOpportunity, setSelectedOpportunity] = useState<Opportunity | null>(null);
  const [isModalVisible, setIsModalVisible] = useState(false);

  const opportunities = data?.opportunities || [];

  const getTypeConfig = (type: string) => {
    switch (type) {
      case 'promotion':
        return { icon: <RiseOutlined />, color: '#52c41a', label: '晋升机会' };
      case 'transfer':
        return { icon: <ThunderboltOutlined />, color: '#1890ff', label: '转岗机会' };
      case 'project':
        return { icon: <ProjectOutlined />, color: '#faad14', label: '项目机会' };
      default:
        return { icon: <ThunderboltOutlined />, color: '#722ed1', label: '机会' };
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return '#52c41a';
    if (score >= 0.6) return '#faad14';
    return '#ff4d4f';
  };

  const handleViewDetails = (opp: Opportunity) => {
    setSelectedOpportunity(opp);
    setIsModalVisible(true);
  };

  const handleApply = () => {
    message.success('申请已提交！AI 助手将协助您准备材料。');
    setIsModalVisible(false);
  };

  if (!opportunities || opportunities.length === 0) {
    return (
      <Card className="opportunity-empty" size="small">
        <Text type="secondary">暂无匹配的机会，请继续提升技能！</Text>
      </Card>
    );
  }

  return (
    <div className="opportunity-cards">
      <Row gutter={[16, 16]}>
        {opportunities.map((opp, index) => {
          const typeConfig = getTypeConfig(opp.type);
          return (
            <Col xs={24} sm={12} lg={8} key={opp.id || index}>
              <Card
                className="opportunity-card"
                size="small"
                hoverable
                onClick={() => handleViewDetails(opp)}
              >
                <div className="opportunity-header">
                  <div className="opportunity-type" style={{ color: typeConfig.color }}>
                    {typeConfig.icon}
                    <Text strong>{typeConfig.label}</Text>
                  </div>
                  <div className="match-score">
                    <Progress
                      type="circle"
                      percent={opp.match_score * 100}
                      size={40}
                      strokeColor={getScoreColor(opp.match_score)}
                      format={(percent) => `${percent}%`}
                    />
                  </div>
                </div>

                <Title level={5} className="opportunity-title">
                  {opp.title}
                </Title>

                {opp.department && (
                  <Text type="secondary" className="opportunity-department">
                    {opp.department}
                  </Text>
                )}

                <div className="opportunity-tags">
                  {opp.requirements?.slice(0, 3).map((req, idx) => (
                    <Tag key={idx} color="blue">
                      {req}
                    </Tag>
                  ))}
                </div>

                <div className="opportunity-footer">
                  <Button type="primary" block onClick={() => handleViewDetails(opp)}>
                    查看详情 <RightOutlined />
                  </Button>
                </div>
              </Card>
            </Col>
          );
        })}
      </Row>

      {/* 详情弹窗 */}
      <Modal
        title={selectedOpportunity?.title}
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setIsModalVisible(false)}>
            取消
          </Button>,
          <Button key="apply" type="primary" onClick={handleApply}>
            <StarOutlined /> 申请这个职位
          </Button>,
        ]}
      >
        {selectedOpportunity && (
          <div className="opportunity-detail">
            <div className="detail-score">
              <Text strong>匹配度：</Text>
              <Progress
                type="line"
                percent={selectedOpportunity.match_score * 100}
                strokeColor={getScoreColor(selectedOpportunity.match_score)}
              />
            </div>

            {selectedOpportunity.description && (
              <Paragraph className="detail-description">
                {selectedOpportunity.description}
              </Paragraph>
            )}

            {selectedOpportunity.requirements && (
              <div className="detail-requirements">
                <Text strong>任职要求：</Text>
                <ul>
                  {selectedOpportunity.requirements.map((req, idx) => (
                    <li key={idx}>{req}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default OpportunityCards;
