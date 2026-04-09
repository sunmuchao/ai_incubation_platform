#!/bin/bash

# ==================== Her 项目停止脚本 ====================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}       停止 Her 项目服务${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# 停止后端
echo -e "${YELLOW}停止后端服务...${NC}"
if [ -f /tmp/her_backend.pid ]; then
    PID=$(cat /tmp/her_backend.pid)
    kill $PID 2>/dev/null && echo -e "${GREEN}✓ 已停止后端 (PID: $PID)${NC}" || echo "后端进程不存在"
    rm -f /tmp/her_backend.pid
fi
pkill -f "uvicorn main:app" 2>/dev/null

# 停止前端
echo -e "${YELLOW}停止前端服务...${NC}"
if [ -f /tmp/her_frontend.pid ]; then
    PID=$(cat /tmp/her_frontend.pid)
    kill $PID 2>/dev/null && echo -e "${GREEN}✓ 已停止前端 (PID: $PID)${NC}" || echo "前端进程不存在"
    rm -f /tmp/her_frontend.pid
fi
pkill -f "vite" 2>/dev/null

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ 所有服务已停止${NC}"
echo -e "${GREEN}========================================${NC}"