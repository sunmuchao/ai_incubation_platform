/**
 * WebSocket Hook
 */
import { useEffect, useCallback, useState } from 'react';
import { wsService, type WSEventHandler } from '@/services/websocket';

export const useWebSocket = (autoConnect: boolean = true) => {
  const [connected, setConnected] = useState(false);

  // 连接
  const connect = useCallback(async (token?: string) => {
    try {
      await wsService.connect(token);
      setConnected(true);
    } catch (error) {
      console.error('WebSocket connection failed:', error);
      setConnected(false);
    }
  }, []);

  // 断开
  const disconnect = useCallback(() => {
    wsService.disconnect();
    setConnected(false);
  }, []);

  // 发送消息
  const send = useCallback((type: string, payload: unknown) => {
    wsService.send(type, payload);
  }, []);

  // 订阅事件
  const on = useCallback((event: string, handler: WSEventHandler) => {
    const unsubscribe = wsService.on(event, handler);
    return unsubscribe;
  }, []);

  // 检查连接状态
  const isConnected = useCallback(() => {
    return wsService.isConnected();
  }, []);

  // 自动连接
  useEffect(() => {
    if (autoConnect) {
      const token = localStorage.getItem('ai_employee_token');
      connect(token || undefined);
    }

    return () => {
      if (autoConnect) {
        disconnect();
      }
    };
  }, [autoConnect, connect, disconnect]);

  // 监听连接状态变化
  useEffect(() => {
    const checkConnection = () => {
      setConnected(wsService.isConnected());
    };

    const interval = setInterval(checkConnection, 5000);
    return () => clearInterval(interval);
  }, []);

  return {
    connected,
    connect,
    disconnect,
    send,
    on,
    isConnected,
  };
};
