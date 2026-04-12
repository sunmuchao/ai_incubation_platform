#!/bin/bash

# ==================== Her 项目停止脚本（DeerFlow 集成版） ====================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}       停止 Her + DeerFlow 服务${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# 停止 DeerFlow
echo -e "${BLUE}停止 DeerFlow Agent 运行时...${NC}"
if [ -f /tmp/deerflow.pid ]; then
    PID=$(cat /tmp/deerflow.pid)
    kill $PID 2>/dev/null && echo -e "${GREEN}✓ 已停止 DeerFlow (PID: $PID)${NC}" || echo "DeerFlow 进程不存在"
    rm -f /tmp/deerflow.pid
fi
# 停止 DeerFlow 相关进程
pkill -f "langgraph" 2>/dev/null
pkill -f "deerflow" 2>/dev/null
pkill -f "make dev" 2>/dev/null && echo -e "${GREEN}✓ 已停止 DeerFlow make 进程${NC}"

# 停止 Her 后端
echo -e "${YELLOW}停止 Her 后端服务...${NC}"
if [ -f /tmp/her_backend.pid ]; then
    PID=$(cat /tmp/her_backend.pid)
    kill $PID 2>/dev/null && echo -e "${GREEN}✓ 已停止 Her 后端 (PID: $PID)${NC}" || echo "后端进程不存在"
    rm -f /tmp/her_backend.pid
fi
pkill -f "uvicorn main:app" 2>/dev/null && echo -e "${GREEN}✓ 已停止 uvicorn 进程${NC}"

# 停止 Her 前端
echo -e "${YELLOW}停止 Her 前端服务...${NC}"
if [ -f /tmp/her_frontend.pid ]; then
    PID=$(cat /tmp/her_frontend.pid)
    kill $PID 2>/dev/null && echo -e "${GREEN}✓ 已停止 Her 前端 (PID: $PID)${NC}" || echo "前端进程不存在"
    rm -f /tmp/her_frontend.pid
fi
pkill -f "vite" 2>/dev/null && echo -e "${GREEN}✓ 已停止 vite 进程${NC}"

# 清理端口（确保端口被释放）
sleep 1
echo ""
echo -e "${YELLOW}检查端口状态...${NC}"
PORTS="8000 3005 2024 8001"
for PORT in $PORTS; do
    if lsof -i :$PORT > /dev/null 2>&1; then
        echo -e "${RED}端口 $PORT 仍被占用，强制清理...${NC}"
        lsof -ti :$PORT | xargs kill -9 2>/dev/null
    else
        echo -e "${GREEN}端口 $PORT 已释放${NC}"
    fi
done

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ 所有服务已停止${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}提示: 使用 './start.sh' 重新启动服务${NC}"