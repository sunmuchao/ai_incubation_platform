#!/bin/bash

# AI Incubation Platform - 启动所有前端服务
# 日期：2026-04-06

echo "=============================================="
echo "AI Incubation Platform - 启动所有前端服务"
echo "=============================================="
echo ""

# 创建日志目录
mkdir -p logs

# 前端项目配置：项目名：端口
declare -a FRONTENDS=(
    "ai-employee-platform:5004"
    "ai-hires-human:5003"
    "ai-community-buying:5005"
    "ai-code-understanding:5008"
    "data-agent-connector:5012"
    "ai-runtime-optimizer:5010"
    "ai-opportunity-miner:5009"
)

# 停止已有进程
echo "[准备] 停止已存在的 Vite 进程..."
pkill -f "vite" 2>/dev/null || true
sleep 2

# 启动前端函数
start_frontend() {
    local project=$1
    local port=$2
    local project_path="/Users/sunmuchao/Downloads/ai_incubation_platform/$project/frontend"
    local log_file="/Users/sunmuchao/Downloads/ai_incubation_platform/logs/frontend-${project}.log"

    # 检查项目目录是否存在
    if [ ! -d "$project_path" ]; then
        echo "[跳过] $project - 目录不存在"
        return 1
    fi

    # 检查是否有 node_modules
    if [ ! -d "$project_path/node_modules" ]; then
        echo "[跳过] $project - node_modules 未安装"
        return 1
    fi

    # 设置环境变量并启动
    cd "$project_path"
    export PORT=$port

    # 后台启动 vite
    nohup npm run dev -- --port $port --host 0.0.0.0 > "$log_file" 2>&1 &
    local pid=$!

    sleep 5

    # 检查进程是否还在运行
    if ps -p $pid > /dev/null; then
        echo "[成功] $project - 端口 $port - PID: $pid"
        return 0
    else
        echo "[失败] $project - 启动失败，请查看日志：$log_file"
        tail -10 "$log_file"
        return 1
    fi
}

# 启动所有前端
echo ""
echo "开始启动所有前端..."
echo ""

success_count=0
fail_count=0

for frontend_config in "${FRONTENDS[@]}"; do
    IFS=':' read -r project port <<< "$frontend_config"
    if start_frontend "$project" "$port"; then
        ((success_count++))
    else
        ((fail_count++))
    fi
    sleep 1
done

echo ""
echo "=============================================="
echo "启动完成!"
echo "=============================================="
echo ""
echo "成功：$success_count 个前端"
echo "失败：$fail_count 个前端"
echo ""
echo "前端访问地址:"
echo "----------------------------------------------"
echo "  ai-employee-platform:    http://localhost:5004"
echo "  ai-hires-human:          http://localhost:5003"
echo "  ai-community-buying:     http://localhost:5005"
echo "  ai-code-understanding:   http://localhost:5008"
echo "  data-agent-connector:    http://localhost:5012"
echo "  ai-runtime-optimizer:    http://localhost:5010"
echo "  ai-opportunity-miner:    http://localhost:5009"
echo "----------------------------------------------"
echo ""
echo "日志文件位置：logs/frontend-*.log"
echo ""
