#!/bin/bash

# AI Incubation Platform - 启动所有项目脚本
# 日期：2026-04-06

echo "=============================================="
echo "AI Incubation Platform - 启动所有项目"
echo "=============================================="
echo ""

# 创建日志目录
mkdir -p logs

# 停止已有进程
echo "[准备] 停止已存在的项目进程..."
pkill -f "python.*main.py" 2>/dev/null || true
pkill -f "python3.*main.py" 2>/dev/null || true
sleep 2

# 项目配置
declare -a PROJECTS=(
    "platform-portal:8002"
    "ai-hires-human:8003"
    "ai-employee-platform:8004"
    "ai-community-buying:8005"
    "human-ai-community:8006"
    "matchmaker-agent:8007"
    "ai-code-understanding:8008"
    "ai-opportunity-miner:8009"
    "ai-runtime-optimizer:8010"
    "ai-traffic-booster:8011"
    "data-agent-connector:8012"
)

# 启动项目函数
start_project() {
    local project=$1
    local port=$2
    local project_path="/Users/sunmuchao/Downloads/ai_incubation_platform/$project"
    local log_file="/Users/sunmuchao/Downloads/ai_incubation_platform/logs/${project}.log"
    local main_file="src/main.py"

    # 检查项目目录是否存在
    if [ ! -d "$project_path" ]; then
        echo "[跳过] $project - 目录不存在"
        return 1
    fi

    # 检查是否有 main 文件
    if [ ! -f "$project_path/$main_file" ]; then
        echo "[跳过] $project - 没有找到 $main_file"
        return 1
    fi

    # 设置环境变量并启动
    cd "$project_path"
    export PORT=$port

    # 后台启动
    nohup python3 $main_file > "$log_file" 2>&1 &
    local pid=$!

    sleep 3

    # 检查进程是否还在运行
    if ps -p $pid > /dev/null; then
        echo "[成功] $project (端口 $port) - PID: $pid"
        return 0
    else
        echo "[失败] $project - 启动失败，请查看日志：$log_file"
        tail -5 "$log_file"
        return 1
    fi
}

# 启动所有项目
echo ""
echo "开始启动所有项目..."
echo ""

success_count=0
fail_count=0

for project_config in "${PROJECTS[@]}"; do
    IFS=':' read -r project port <<< "$project_config"
    if start_project "$project" "$port"; then
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
echo "成功：$success_count 个项目"
echo "失败：$fail_count 个项目"
echo ""
echo "项目访问地址:"
echo "----------------------------------------------"
echo "  platform-portal:         http://localhost:8002"
echo "  ai-hires-human:          http://localhost:8003"
echo "  ai-employee-platform:    http://localhost:8004"
echo "  ai-community-buying:     http://localhost:8005"
echo "  human-ai-community:      http://localhost:8006"
echo "  matchmaker-agent:        http://localhost:8007"
echo "  ai-code-understanding:   http://localhost:8008"
echo "  ai-opportunity-miner:    http://localhost:8009"
echo "  ai-runtime-optimizer:    http://localhost:8010"
echo "  ai-traffic-booster:      http://localhost:8011"
echo "  data-agent-connector:    http://localhost:8012"
echo "----------------------------------------------"
