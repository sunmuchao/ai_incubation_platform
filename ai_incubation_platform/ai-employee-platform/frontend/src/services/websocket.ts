/**
 * WebSocket 服务
 */
import { env } from '@/config';

export type WSEventHandler = (data: unknown) => void;

export interface WSMessage {
  type: string;
  payload: unknown;
  timestamp: string;
}

class WebSocketService {
  private ws: WebSocket | null = null;
  private eventHandlers: Map<string, Set<WSEventHandler>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;
  private heartbeatInterval: number | null = null;

  // 连接到 WebSocket 服务器
  connect(token?: string): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        const wsUrl = `${env.WS_URL}?token=${token || localStorage.getItem(env.TOKEN_KEY)}`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log('[WS] Connected');
          this.reconnectAttempts = 0;
          this.startHeartbeat();
          resolve();
        };

        this.ws.onclose = (event) => {
          console.log('[WS] Disconnected', event);
          this.stopHeartbeat();
          this.handleReconnect();
        };

        this.ws.onerror = (error) => {
          console.error('[WS] Error', error);
          reject(error);
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event.data);
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  // 断开连接
  disconnect(): void {
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.eventHandlers.clear();
  }

  // 发送消息
  send(type: string, payload: unknown): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[WS] Not connected');
      return;
    }

    const message: WSMessage = {
      type,
      payload,
      timestamp: new Date().toISOString(),
    };

    this.ws.send(JSON.stringify(message));
  }

  // 订阅事件
  on(event: string, handler: WSEventHandler): () => void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set());
    }
    this.eventHandlers.get(event)!.add(handler);

    // 返回取消订阅函数
    return () => {
      this.eventHandlers.get(event)?.delete(handler);
    };
  }

  // 处理接收到的消息
  private handleMessage(data: string): void {
    try {
      const message: WSMessage = JSON.parse(data);
      const handlers = this.eventHandlers.get(message.type);
      if (handlers) {
        handlers.forEach((handler) => handler(message.payload));
      }
    } catch (error) {
      console.error('[WS] Failed to parse message', error);
    }
  }

  // 处理重连
  private handleReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`[WS] Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      setTimeout(() => this.connect(), this.reconnectDelay * this.reconnectAttempts);
    }
  }

  // 启动心跳
  private startHeartbeat(): void {
    this.heartbeatInterval = window.setInterval(() => {
      this.send('ping', { timestamp: Date.now() });
    }, 30000);
  }

  // 停止心跳
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  // 获取连接状态
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// 导出单例
export const wsService = new WebSocketService();
export default wsService;
