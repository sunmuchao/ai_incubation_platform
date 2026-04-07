// App 主组件
import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from '@components/Layout';
import Dashboard from '@pages/Dashboard';
import CodeMap from '@pages/CodeMap';
import CodeSearch from '@pages/CodeSearch';
import CodeQA from '@pages/CodeQA';
import CodeReview from '@pages/CodeReview';
import DocsCenter from '@pages/DocsCenter';
import KnowledgeGraph from '@pages/KnowledgeGraph';
import Settings from '@pages/Settings';

const App: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="code-map" element={<CodeMap />} />
        <Route path="code-search" element={<CodeSearch />} />
        <Route path="code-qa" element={<CodeQA />} />
        <Route path="code-review" element={<CodeReview />} />
        <Route path="docs" element={<DocsCenter />} />
        <Route path="knowledge-graph" element={<KnowledgeGraph />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  );
};

export default App;
