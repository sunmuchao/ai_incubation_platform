#!/bin/bash

# AI 社区团购前端 - 快速启动脚本

set -e

echo "========================================"
echo "  AI 社区团购前端 - 快速启动"
echo "========================================"

# 检查 Node.js 版本
echo ""
echo "检查 Node.js 版本..."
if ! command -v node &> /dev/null; then
    echo "错误：未检测到 Node.js，请先安装 Node.js >= 18"
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "错误：Node.js 版本过低，当前版本：$(node -v)，需要 >= 18"
    exit 1
fi

echo "Node.js 版本：$(node -v) ✓"

# 检查 npm
echo ""
echo "检查 npm..."
if ! command -v npm &> /dev/null; then
    echo "错误：未检测到 npm"
    exit 1
fi

echo "npm 版本：$(npm -v) ✓"

# 安装依赖
echo ""
echo "安装依赖..."
if [ ! -d "node_modules" ]; then
    npm install
    echo "依赖安装完成 ✓"
else
    echo "依赖已存在，跳过安装"
fi

# 检查环境变量
echo ""
echo "检查环境变量配置..."
if [ ! -f ".env" ]; then
    echo "创建 .env 文件..."
    cp .env.example .env
    echo ".env 文件创建完成"
fi

# 启动开发服务器
echo ""
echo "========================================"
echo "  启动开发服务器"
echo "========================================"
echo ""
echo "访问地址：http://localhost:3000"
echo "API 地址：http://localhost:8005"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

npm run dev
