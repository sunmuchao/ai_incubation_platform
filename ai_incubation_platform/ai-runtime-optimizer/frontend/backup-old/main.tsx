import React from 'react';
import ReactDOM from 'react-dom/client';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import App from './App';
import './styles/index.less';

const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error('Failed to find the root element');
}

const root = ReactDOM.createRoot(rootElement);

root.render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: undefined,
        token: {
          colorPrimary: '#1890ff',
          colorBgBase: '#000000',
          colorBgContainer: '#141414',
          colorText: 'rgba(255, 255, 255, 0.85)',
          colorTextSecondary: 'rgba(255, 255, 255, 0.45)',
          colorBorder: '#303030',
          borderRadius: 8,
        },
        components: {
          Layout: {
            bodyBg: '#000000',
            headerBg: '#141414',
            siderBg: '#141414',
            lightSiderBg: '#141414',
            lightTriggerBg: '#141414',
            triggerBg: '#141414',
          },
          Menu: {
            darkItemBg: '#141414',
            darkPopupBg: '#141414',
            darkItemSelectedBg: 'rgba(24, 144, 255, 0.15)',
            darkItemColor: 'rgba(255, 255, 255, 0.85)',
          },
          Card: {
            colorBgContainer: '#141414',
          },
          Table: {
            colorBgContainer: '#141414',
            headerBg: '#1f1f1f',
            rowHoverBg: '#1f1f1f',
          },
        },
      }}
    >
      <App />
    </ConfigProvider>
  </React.StrictMode>
);
