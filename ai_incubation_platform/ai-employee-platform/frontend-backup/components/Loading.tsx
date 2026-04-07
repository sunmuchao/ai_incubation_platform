/**
 * 加载组件
 */
import React from 'react';
import { Spin, Space } from 'antd';

interface LoadingProps {
  size?: 'small' | 'default' | 'large';
  fullScreen?: boolean;
  text?: string;
  style?: React.CSSProperties;
}

export const Loading: React.FC<LoadingProps> = ({
  size = 'default',
  fullScreen = false,
  text,
  style,
}) => {
  const content = (
    <Spin size={size} tip={text}>
      <Space style={{ padding: 20 }} />
    </Spin>
  );

  if (fullScreen) {
    return (
      <div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'rgba(255, 255, 255, 0.5)',
          zIndex: 1000,
          ...style,
        }}
      >
        {content}
      </div>
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 40,
        ...style,
      }}
    >
      {content}
    </div>
  );
};

export default Loading;
