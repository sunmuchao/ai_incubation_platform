/**
 * 建议操作组件
 * 显示 AI 推荐的快捷操作
 */
import React from 'react';
import { Space, Button, Typography } from 'antd';
import { ThunderboltOutlined } from '@ant-design/icons';
import './SuggestedActions.less';

const { Text } = Typography;

interface SuggestedAction {
  action: string;
  label: string;
  available?: boolean;
}

interface SuggestedActionsProps {
  actions: SuggestedAction[];
  onSelect: (action: string) => void;
}

const SuggestedActions: React.FC<SuggestedActionsProps> = ({ actions, onSelect }) => {
  if (!actions || actions.length === 0) {
    return null;
  }

  return (
    <div className="suggested-actions-container">
      <div className="suggested-actions-header">
        <ThunderboltOutlined className="header-icon" />
        <Text type="secondary" className="header-text">建议操作</Text>
      </div>
      <Space wrap className="suggested-actions-list">
        {actions.map((item, index) => (
          <Button
            key={index}
            size="large"
            onClick={() => item.available !== false && onSelect(item.action)}
            disabled={item.available === false}
            className={`action-button ${item.action}`}
          >
            {item.label}
          </Button>
        ))}
      </Space>
    </div>
  );
};

export default SuggestedActions;
