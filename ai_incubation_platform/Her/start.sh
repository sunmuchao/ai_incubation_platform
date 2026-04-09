#!/bin/bash

# ==================== Her 项目启动脚本 ====================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="/Users/sunmuchao/Downloads/ai_incubation_platform/Her"
BACKEND_DIR="$PROJECT_ROOT/src"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# 模型配置
export OPENAI_API_KEY='sk-sp-5b3a4ac5243440b0b39372f84d543d4a'
export OPENAI_API_BASE='https://coding.dashscope.aliyuncs.com/v1'
export OPENAI_MODEL='glm-5'

# 端口配置
BACKEND_PORT=8000
FRONTEND_PORT=3005

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}       Her 项目启动脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 停止已有进程
echo -e "${YELLOW}[1/4] 停止已有服务...${NC}"
pkill -f "uvicorn main:app" 2>/dev/null
pkill -f "vite" 2>/dev/null
sleep 2
echo -e "${GREEN}✓ 已停止旧服务${NC}"
echo ""

# 启动后端
echo -e "${YELLOW}[2/4] 启动后端服务...${NC}"
cd "$BACKEND_DIR"
PYTHONPATH=. nohup uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT > /tmp/her_backend.log 2>&1 &
BACKEND_PID=$!
echo "后端 PID: $BACKEND_PID"

# 等待后端启动（最多等待30秒）
echo "等待后端启动..."
MAX_WAIT=30
WAIT_COUNT=0
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if curl -s "http://localhost:$BACKEND_PORT/docs" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 后端启动成功: http://localhost:$BACKEND_PORT${NC}"
        break
    fi
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
    printf "\r启动中... %d/%d 秒" $WAIT_COUNT $MAX_WAIT
done
echo ""

if [ $WAIT_COUNT -eq $MAX_WAIT ]; then
    echo -e "${RED}✗ 后端启动超时，请检查日志: /tmp/her_backend.log${NC}"
fi
echo ""

# 启动前端
echo -e "${YELLOW}[3/4] 启动前端服务...${NC}"
cd "$FRONTEND_DIR"
nohup npm run dev > /tmp/her_frontend.log 2>&1 &
FRONTEND_PID=$!
echo "前端 PID: $FRONTEND_PID"

# 等待前端启动（最多等待15秒）
echo "等待前端启动..."
MAX_WAIT=15
WAIT_COUNT=0
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if curl -s "http://localhost:$FRONTEND_PORT" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 前端启动成功: http://localhost:$FRONTEND_PORT${NC}"
        break
    fi
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
    printf "\r启动中... %d/%d 秒" $WAIT_COUNT $MAX_WAIT
done
echo ""

if [ $WAIT_COUNT -eq $MAX_WAIT ]; then
    echo -e "${RED}✗ 前端启动超时，请检查日志: /tmp/her_frontend.log${NC}"
fi
echo ""

# 打印服务信息
echo -e "${GREEN}[4/4] 服务状态${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "  后端 API:    http://localhost:$BACKEND_PORT"
echo -e "  API 文档:    http://localhost:$BACKEND_PORT/docs"
echo -e "  前端页面:    http://localhost:$FRONTEND_PORT"
echo -e "  后端日志:    $BACKEND_DIR/logs/server.log"
echo -e "  前端日志:    /tmp/her_frontend.log"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "模型配置:"
echo -e "  OPENAI_MODEL: $OPENAI_MODEL"
echo -e "  API_BASE:     $OPENAI_API_BASE"
echo ""

# 保存 PID 到文件
echo "$BACKEND_PID" > /tmp/her_backend.pid
echo "$FRONTEND_PID" > /tmp/her_frontend.pid

echo -e "${YELLOW}提示: 使用 './stop.sh' 停止服务${NC}"
echo -e "${YELLOW}提示: 使用 'tail -f $BACKEND_DIR/logs/server.log' 查看后端日志${NC}"