#!/bin/bash

# 人AI共建社区启动脚本

echo "🚀 启动人AI共建社区服务"

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3，请先安装Python3"
    exit 1
fi

# 检查是否安装了依赖
echo "📦 检查依赖..."
cd "$(dirname "$0")"
if [ ! -d "venv" ]; then
    echo "🔧 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "🔧 安装依赖..."
pip install -r requirements.txt > /dev/null 2>&1

# 初始化演示数据
read -p "是否初始化演示数据? (y/n): " init_data
if [ "$init_data" = "y" ] || [ "$init_data" = "Y" ]; then
    echo "📊 初始化演示数据..."
    cd src
    python demo_data.py
    cd ..
fi

echo "🌐 启动服务..."
echo "📖 API文档地址: http://localhost:8007/docs"
echo "🏠 主页地址: http://localhost:8007"
echo "⏹️  按 Ctrl+C 停止服务"
echo ""

cd src
python main.py
