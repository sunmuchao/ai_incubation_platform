/**
 * 空状态组件
 */
import React from 'react';
import { Empty, Button, type EmptyProps } from 'antd';

interface CustomEmptyProps extends EmptyProps {
  title?: string;
  description?: string;
  action?: React.ReactNode;
  onRefresh?: () => void;
}

export const CustomEmpty: React.FC<CustomEmptyProps> = ({
  title,
  description = '暂无数据',
  action,
  onRefresh,
  image,
  ...restProps
}) => {
  return (
    <Empty
      image={image}
      description={description}
      {...restProps}
    >
      {(action || onRefresh) && (
        <div style={{ marginTop: 16 }}>
          {onRefresh && (
            <Button onClick={onRefresh} type="primary">
              刷新
            </Button>
          )}
          {action}
        </div>
      )}
    </Empty>
  );
};

export default CustomEmpty;
