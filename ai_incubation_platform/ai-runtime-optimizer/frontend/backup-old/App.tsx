import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from 'antd';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Dashboard from './pages/Dashboard';
import Monitoring from './pages/Monitoring';
import RootCause from './pages/RootCause';
import Predictive from './pages/Predictive';
import Remediation from './pages/Remediation';
import Optimization from './pages/Optimization';
import Observability from './pages/Observability';
import Automation from './pages/Automation';
import Alerts from './pages/Alerts';
import Settings from './pages/Settings';

const { Content } = Layout;

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Layout style={{ minHeight: '100vh' }}>
        <Sidebar />
        <Layout>
          <Header />
          <Content style={{ padding: '24px', overflow: 'initial' }}>
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/monitoring" element={<Monitoring />} />
              <Route path="/root-cause" element={<RootCause />} />
              <Route path="/predictive" element={<Predictive />} />
              <Route path="/remediation" element={<Remediation />} />
              <Route path="/optimization" element={<Optimization />} />
              <Route path="/observability" element={<Observability />} />
              <Route path="/automation" element={<Automation />} />
              <Route path="/alerts" element={<Alerts />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </BrowserRouter>
  );
};

export default App;
