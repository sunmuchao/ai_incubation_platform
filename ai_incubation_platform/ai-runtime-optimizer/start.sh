#!/bin/bash

# AI 运行态优化器启动脚本

echo "🚀 启动 AI 运行态优化器..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到python3，请先安装Python 3.9+"
    exit 1
fi

# 检查依赖
echo "📦 检查依赖..."
cd "$(dirname "$0")"
python3 -c "import fastapi, uvicorn, pydantic, dotenv" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  依赖未安装，正在安装..."
    pip3 install -r requirements.txt
fi

# 加载环境变量
if [ -f .env ]; then
    echo "🔧 加载环境变量..."
    export $(grep -v '^#' .env | xargs)
fi

# 启动服务
echo "🌐 服务启动中，监听端口: ${AI_OPTIMIZER_PORT:-8012}"
echo "📚 API文档: http://localhost:${AI_OPTIMIZER_PORT:-8012}/docs"
echo "❤️  健康检查: http://localhost:${AI_OPTIMIZER_PORT:-8012}/health"
echo ""
echo "按 Ctrl+C 停止服务"

python3 src/main.py
