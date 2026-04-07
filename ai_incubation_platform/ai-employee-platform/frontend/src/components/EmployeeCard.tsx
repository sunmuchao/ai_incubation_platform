/**
 * 员工卡片组件
 */
import React, { useState } from 'react';
import { Card, Avatar, Tag, Button, Space, Tooltip, Badge } from 'antd';
import {
  ClockCircleOutlined,
  DollarOutlined,
  StarOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import type { AIEmployee } from '@/types/employee';
import { formatCurrency } from '@/utils';

interface EmployeeCardProps {
  employee: AIEmployee;
  onHire?: (employee: AIEmployee) => void;
  onViewDetail?: (employee: AIEmployee) => void;
  showActions?: boolean;
}

export const EmployeeCard: React.FC<EmployeeCardProps> = ({
  employee,
  onHire,
  onViewDetail,
  showActions = true,
}) => {
  const [_hovered, setHovered] = useState(false);

  const getStatusColor = (status: string): string => {
    const colors: Record<string, string> = {
      available: 'green',
      busy: 'orange',
      unavailable: 'red',
      offline: 'default',
    };
    return colors[status] || 'default';
  };

  const getStatusText = (status: string): string => {
    const texts: Record<string, string> = {
      available: '可雇佣',
      busy: '工作中',
      unavailable: '不可用',
      offline: '离线',
    };
    return texts[status] || status;
  };

  const skillTags = Object.entries(employee.skills).slice(0, 5);

  return (
    <Card
      hoverable
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      cover={
        <div style={{ height: 160, background: '#f5f5f5', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Avatar
            src={employee.avatar_url}
            size={80}
            style={{ fontSize: 32 }}
          >
            {employee.name.charAt(0)}
          </Avatar>
        </div>
      }
      actions={showActions ? [
        <Button key="view" type="link" onClick={() => onViewDetail?.(employee)}>
          查看详情
        </Button>,
        employee.status === 'available' && (
          <Button
            key="hire"
            type="primary"
            onClick={() => onHire?.(employee)}
          >
            立即雇佣
          </Button>
        ),
      ].filter(Boolean) : undefined}
    >
      <Card.Meta
        title={
          <Space>
            <span>{employee.name}</span>
            <Badge
              count={getStatusText(employee.status)}
              style={{ backgroundColor: getStatusColor(employee.status) }}
            />
          </Space>
        }
        description={
          <div>
            <div style={{ color: '#999', marginBottom: 8, fontSize: 12 }}>
              {employee.description}
            </div>

            {/* 技能标签 */}
            <Space wrap style={{ marginBottom: 12 }}>
              {skillTags.map(([skill, _level]) => (
                <Tag key={skill} color="blue">
                  {skill}
                </Tag>
              ))}
            </Space>

            {/* 关键信息 */}
            <Space split={<span style={{ color: '#e8e8e8' }}>|</span>}>
              <Tooltip title="评分">
                <span>
                  <StarOutlined style={{ color: '#faad14', marginRight: 4 }} />
                  {employee.rating.toFixed(1)} ({employee.review_count})
                </span>
              </Tooltip>
              <Tooltip title="时薪">
                <span>
                  <DollarOutlined style={{ color: '#52c41a', marginRight: 4 }} />
                  {formatCurrency(employee.hourly_rate)}/小时
                </span>
              </Tooltip>
              <Tooltip title="总工作时长">
                <span>
                  <ClockCircleOutlined style={{ color: '#1890ff', marginRight: 4 }} />
                  {employee.total_hours_worked}h
                </span>
              </Tooltip>
            </Space>

            {/* 完成率 */}
            <div style={{ marginTop: 12, fontSize: 12, color: '#666' }}>
              <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 4 }} />
              完成率：{employee.completion_rate.toFixed(0)}%
            </div>
          </div>
        }
      />
    </Card>
  );
};

export default EmployeeCard;
