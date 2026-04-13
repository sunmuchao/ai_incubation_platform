#!/bin/bash

# ==================== Her 项目启动脚本（DeerFlow 集成版） ====================
#
# 启动流程：
# 1. DeerFlow Agent 运行时（LangGraph Server + Gateway）
# 2. Her 后端 API（FastAPI）
# 3. Her 前端（Vite）
#
# 架构：
# - DeerFlow 是 Agent 运行时（意图识别、工具编排、状态管理）
# - Her 提供业务 Tools（匹配、关系分析、约会策划）
# - 前端通过 deerflowClient 调用 DeerFlow Agent

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="/Users/sunmuchao/Downloads/ai_incubation_platform/Her"
BACKEND_DIR="$PROJECT_ROOT/src"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
DEERFLOW_DIR="$PROJECT_ROOT/deerflow"
DEERFLOW_BACKEND_DIR="$DEERFLOW_DIR/backend"

# ==================== 环境变量配置 ====================

# Her 项目根目录（DeerFlow Tools 需要此变量）
export HER_PROJECT_ROOT="$PROJECT_ROOT"

# 模型配置
export OPENAI_API_KEY='sk-sp-5b3a4ac5243440b0b39372f84d543d4a'
export OPENAI_API_BASE='https://coding.dashscope.aliyuncs.com/v1'
export OPENAI_MODEL='glm-5'

# DeerFlow 配置路径
export DEER_FLOW_CONFIG_PATH="$DEERFLOW_DIR/config.yaml"
export DEER_FLOW_EXTENSIONS_CONFIG_PATH="$DEERFLOW_DIR/extensions_config.json"

# 端口配置（与 .env 保持一致）
HER_BACKEND_PORT=8002
HER_FRONTEND_PORT=3005
DEERFLOW_LANGGRAPH_PORT=2024
DEERFLOW_GATEWAY_PORT=8001

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}    Her + DeerFlow 启动脚本${NC}"
echo -e "${GREEN}    (AI Native 架构)${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# ==================== Step 1: 停止已有服务 ====================
echo -e "${YELLOW}[1/5] 停止已有服务...${NC}"
pkill -f "uvicorn main:app" 2>/dev/null
pkill -f "uvicorn src.main:app" 2>/dev/null
pkill -f "vite" 2>/dev/null
pkill -f "langgraph" 2>/dev/null
pkill -f "deerflow" 2>/dev/null
# 停止 pytest 测试进程，避免与后端资源冲突
pkill -f "pytest" 2>/dev/null
sleep 2
echo -e "${GREEN}✓ 已停止旧服务（包括 pytest 测试进程）${NC}"
echo ""

# ==================== Step 2: 启动 DeerFlow ====================
echo -e "${BLUE}[2/5] 启动 DeerFlow Agent 运行时...${NC}"

# 检查 DeerFlow 配置是否存在
if [ ! -f "$DEERFLOW_DIR/config.yaml" ]; then
    echo -e "${RED}✗ DeerFlow 配置文件不存在: $DEERFLOW_DIR/config.yaml${NC}"
    echo -e "${YELLOW}提示: 请检查 DeerFlow 是否正确安装${NC}"
    echo ""
    echo -e "${YELLOW}继续启动 Her（无 DeerFlow 集成）...${NC}"
    DEERFLOW_ENABLED=false
else
    DEERFLOW_ENABLED=true

    cd "$DEERFLOW_BACKEND_DIR"

    # 启动 DeerFlow（使用 make dev）
    # make dev 会同时启动 LangGraph Server (2024) 和 Gateway (8001)
    echo "启动 DeerFlow..."
    nohup make dev > /tmp/deerflow.log 2>&1 &
    DEERFLOW_PID=$!
    echo "DeerFlow PID: $DEERFLOW_PID"

    # 等待 DeerFlow 启动（最多等待30秒）
    # 注意：make dev 只启动 LangGraph Server (2024)，不启动 Gateway (8001)
    # Her 通过 DeerFlowClient（嵌入式客户端）直接调用 Agent，无需 Gateway
    echo "等待 DeerFlow LangGraph Server 启动..."
    MAX_WAIT=30
    WAIT_COUNT=0
    while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
        if curl -s "http://localhost:$DEERFLOW_LANGGRAPH_PORT/info" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ DeerFlow LangGraph Server 启动成功: http://localhost:$DEERFLOW_LANGGRAPH_PORT${NC}"
            break
        fi
        sleep 1
        WAIT_COUNT=$((WAIT_COUNT + 1))
        printf "\r启动中... %d/%d 秒" $WAIT_COUNT $MAX_WAIT
    done
    echo ""

    if [ $WAIT_COUNT -eq $MAX_WAIT ]; then
        echo -e "${YELLOW}⚠ DeerFlow 启动超时，继续启动 Her...${NC}"
        echo -e "${YELLOW}日志: /tmp/deerflow.log${NC}"
    fi
fi
echo ""

# ==================== Step 3: 启动 Her 后端 ====================
echo -e "${YELLOW}[3/5] 启动 Her 后端服务...${NC}"
cd "$PROJECT_ROOT"

# 使用 DeerFlow 的虚拟环境启动 Her 后端
# 原因：Anaconda Python 的 langchain 版本太旧，缺少 create_agent
# DeerFlow 的 .venv 有完整的 langgraph/langchain 依赖
DEERFLOW_VENV="$DEERFLOW_BACKEND_DIR/.venv/bin/python"

# 添加 DeerFlow 路径到 PYTHONPATH（用于导入 deerflow 模块）
export PYTHONPATH="$BACKEND_DIR:$DEERFLOW_BACKEND_DIR/packages/harness"
export HER_PROJECT_ROOT="$PROJECT_ROOT"

nohup $DEERFLOW_VENV -m uvicorn src.main:app --host 0.0.0.0 --port $HER_BACKEND_PORT > /tmp/her_backend.log 2>&1 &
HER_BACKEND_PID=$!
echo "Her 后端 PID: $HER_BACKEND_PID (using DeerFlow venv)"

# 等待后端启动（最多等待30秒）
echo "等待 Her 后端启动..."
MAX_WAIT=30
WAIT_COUNT=0
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if curl -s "http://localhost:$HER_BACKEND_PORT/docs" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Her 后端启动成功: http://localhost:$HER_BACKEND_PORT${NC}"
        break
    fi
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
    printf "\r启动中... %d/%d 秒" $WAIT_COUNT $MAX_WAIT
done
echo ""

if [ $WAIT_COUNT -eq $MAX_WAIT ]; then
    echo -e "${RED}✗ Her 后端启动超时，请检查日志: /tmp/her_backend.log${NC}"
fi
echo ""

# ==================== Step 4: 启动 Her 前端 ====================
echo -e "${YELLOW}[4/5] 启动 Her 前端服务...${NC}"
cd "$FRONTEND_DIR"

nohup npm run dev > /tmp/her_frontend.log 2>&1 &
HER_FRONTEND_PID=$!
echo "Her 前端 PID: $HER_FRONTEND_PID"

# 等待前端启动（最多等待15秒）
echo "等待前端启动..."
MAX_WAIT=15
WAIT_COUNT=0
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if curl -s "http://localhost:$HER_FRONTEND_PORT" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Her 前端启动成功: http://localhost:$HER_FRONTEND_PORT${NC}"
        break
    fi
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
    printf "\r启动中... %d/%d 秒" $WAIT_COUNT $MAX_WAIT
done
echo ""

if [ $WAIT_COUNT -eq $MAX_WAIT ]; then
    echo -e "${RED}✗ Her 前端启动超时，请检查日志: /tmp/her_frontend.log${NC}"
fi
echo ""

# ==================== Step 5: 打印服务信息 ====================
echo -e "${GREEN}[5/5] 服务状态${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

if [ "$DEERFLOW_ENABLED" = true ]; then
    echo -e "${BLUE}DeerFlow Agent 运行时:${NC}"
    echo -e "  LangGraph Server:  http://localhost:$DEERFLOW_LANGGRAPH_PORT"
    echo -e "  LangGraph Info:    http://localhost:$DEERFLOW_LANGGRAPH_PORT/info"
    echo -e "  DeerFlow 状态:     http://localhost:$HER_BACKEND_PORT/api/deerflow/status"
    echo ""
fi

echo -e "${YELLOW}Her 后端 API:${NC}"
echo -e "  API 服务:          http://localhost:$HER_BACKEND_PORT"
echo -e "  API 文档:          http://localhost:$HER_BACKEND_PORT/docs"
echo -e "  DeerFlow 路由:     http://localhost:$HER_BACKEND_PORT/api/deerflow/chat"
echo ""

echo -e "${GREEN}Her 前端:${NC}"
echo -e "  前端页面:          http://localhost:$HER_FRONTEND_PORT"
echo ""

echo -e "${GREEN}========================================${NC}"
echo ""

echo -e "${BLUE}架构说明 (AI Native):${NC}"
echo -e "  DeerFlow 是 Agent 运行时（意图识别、工具编排、状态管理）"
echo -e "  Her 提供 7 个业务 Tools（匹配、关系、约会等）"
echo -e "  前端通过 deerflowClient 直接调用 DeerFlow"
echo ""

echo -e "${GREEN}模型配置:${NC}"
echo -e "  OPENAI_MODEL: $OPENAI_MODEL"
echo -e "  API_BASE:     $OPENAI_API_BASE"
echo ""

echo -e "${GREEN}日志位置:${NC}"
echo -e "  DeerFlow:     /tmp/deerflow.log"
echo -e "  Her 后端:     $BACKEND_DIR/logs/server.log"
echo -e "  Her 前端:     /tmp/her_frontend.log"
echo ""

# 保存 PID 到文件
echo "$HER_BACKEND_PID" > /tmp/her_backend.pid
echo "$HER_FRONTEND_PID" > /tmp/her_frontend.pid
if [ "$DEERFLOW_ENABLED" = true ]; then
    echo "$DEERFLOW_PID" > /tmp/deerflow.pid
fi

echo -e "${YELLOW}提示:${NC}"
echo -e "  停止服务:     ./stop.sh"
echo -e "  查看后端日志: tail -f $BACKEND_DIR/logs/server.log"
echo -e "  查看DeerFlow: tail -f /tmp/deerflow.log"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ 所有服务启动完成！${NC}"
echo -e "${GREEN}========================================${NC}"