/**
 * AI Native 主应用 - Bento Grid 风格
 */
import React from 'react';
import { useRoutes } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import routes from './routes';
import './styles/variables.css';
import './index.less';

const App: React.FC = () => {
  const routing = useRoutes(routes);

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          // 主色调 - 紫色强调色
          colorPrimary: '#7c3aed',
          // 圆角
          borderRadius: 10,
          // 字体
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial',
        },
        components: {
          Layout: {
            headerBg: '#ffffff',
            siderBg: '#001529',
          },
          Card: {
            borderRadiusLG: 12,
          },
          Menu: {
            borderRadius: 10,
          },
          Button: {
            borderRadius: 10,
          },
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
