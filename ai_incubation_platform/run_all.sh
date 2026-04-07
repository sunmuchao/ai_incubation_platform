#!/bin/bash

# AI Incubation Platform - 启动所有项目
# 用法：./run_all.sh

echo "=============================================="
echo "AI Incubation Platform - 启动所有项目"
echo "=============================================="
echo ""

# 创建日志目录
mkdir -p logs

# 停止已有进程
pkill -f "python.*main.py" 2>/dev/null
pkill -f "uvicorn" 2>/dev/null
sleep 2

# 设置通用环境变量
export DATABASE_URL="sqlite+aiosqlite:///./data/app.db"
export JWT_SECRET="dev-secret-key-for-development-only-12345"

# 项目配置数组 (项目名：端口)
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

echo "启动项目..."
echo ""

for project_config in "${PROJECTS[@]}"; do
    IFS=':' read -r project port <<< "$project_config"
    project_path="/Users/sunmuchao/Downloads/ai_incubation_platform/$project"
    log_file="/Users/sunmuchao/Downloads/ai_incubation_platform/logs/${project}.log"

    if [ ! -d "$project_path" ]; then
        echo "[跳过] $project - 目录不存在"
        continue
    fi

    if [ ! -f "$project_path/src/main.py" ]; then
        echo "[跳过] $project - 没有找到 src/main.py"
        continue
    fi

    # 设置端口环境变量
    export PORT=$port
    export AI_HIRES_HUMAN_PORT=$port
    export COMMUNITY_BUYING_PORT=$port

    # 启动项目
    cd "$project_path"
    nohup python3 src/main.py > "$log_file" 2>&1 &
    pid=$!

    sleep 2

    if ps -p $pid > /dev/null; then
        echo "[成功] $project (端口 $port) - PID: $pid"
    else
        echo "[失败] $project (端口 $port) - 启动失败"
    fi
done

echo ""
echo "=============================================="
echo "启动完成!"
echo "=============================================="
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
echo ""
echo "查看日志：tail -f logs/<project-name>.log"
echo ""
