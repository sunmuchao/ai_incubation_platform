import axios from 'axios';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8004';
export const chatService = {
    /**
     * 发送对话消息
     */
    async sendMessage(request) {
        const response = await axios.post(`${API_BASE_URL}/api/chat/`, {
            message: request.message,
            user_id: request.user_id,
            context: request.context,
        });
        const data = response.data;
        return {
            id: `msg_${Date.now()}`,
            role: 'assistant',
            content: data.message,
            action: data.action,
            data: data.data,
            suggestions: data.suggestions || [],
            timestamp: new Date(),
            confidence: data.data?.confidence,
            agentState: {
                thinking: false,
                executing: false,
                confidence: data.data?.confidence,
            },
        };
    },
    /**
     * 获取对话历史
     */
    async getHistory(userId) {
        const response = await axios.get(`${API_BASE_URL}/api/chat/history`, {
            params: { user_id: userId },
        });
        return response.data;
    },
    /**
     * 清除对话历史
     */
    async clearHistory(userId) {
        await axios.delete(`${API_BASE_URL}/api/chat/history`, {
            params: { user_id: userId },
        });
    },
    /**
     * 创建用户消息
     */
    createUserMessage(content) {
        return {
            id: `msg_${Date.now()}`,
            role: 'user',
            content,
            timestamp: new Date(),
        };
    },
    /**
     * 创建系统消息
     */
    createSystemMessage(content) {
        return {
            id: `msg_${Date.now()}`,
            role: 'system',
            content,
            timestamp: new Date(),
        };
    },
    /**
     * 创建思考中的消息
     */
    createThinkingMessage() {
        return {
            id: `msg_thinking_${Date.now()}`,
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            agentState: {
                thinking: true,
                executing: false,
            },
        };
    },
    /**
     * 创建执行中的消息
     */
    createExecutingMessage(workflow, step, totalSteps) {
        return {
            id: `msg_executing_${Date.now()}`,
            role: 'assistant',
            content: workflow ? `正在执行：${workflow}` : '正在执行...',
            timestamp: new Date(),
            agentState: {
                thinking: false,
                executing: true,
                workflow,
                step,
                totalSteps,
            },
        };
    },
};
