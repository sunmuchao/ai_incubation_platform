/**
 * AI Chat 页面 - 主页面
 */

import React from 'react';
import ChatInterface from '@/components/ChatInterface';

const ChatPage: React.FC = () => {
  return (
    <div style={{ height: 'calc(100vh - 188px)' }}>
      <ChatInterface />
    </div>
  );
};

export default ChatPage;
