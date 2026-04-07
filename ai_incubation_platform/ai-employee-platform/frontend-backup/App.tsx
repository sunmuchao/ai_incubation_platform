/**
 * 主应用组件
 */
import React from 'react';
import { useRoutes } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import routes from './routes';
import './App.less';

const App: React.FC = () => {
  const routing = useRoutes(routes);

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: '#1890ff',
          borderRadius: 6,
        },
      }}
    >
      <div className="app-container">
        {routing}
      </div>
    </ConfigProvider>
  );
};

export default App;
