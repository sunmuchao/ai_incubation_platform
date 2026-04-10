#!/bin/bash

# 本地 CI 检查脚本
# 用于提交前验证代码质量

set -e

echo "========== 本地 CI 检查 =========="

cd "$(dirname "$0")/.."

echo ""
echo ">>> 1. 检查 API 注册..."
cd src
python3 -c "
from utils.api_checker import check_api_registration, get_api_checker_report

report = get_api_checker_report()
print(f'定义的路由: {report[\"total_defined\"]}')
print(f'已注册的路由: {report[\"total_registered\"]}')

if report['missing_routers']:
    print(f'❌ 缺失的路由: {report[\"missing_routers\"]}')
    exit(1)

print('✅ API 注册检查通过')
"

echo ""
echo ">>> 2. 检查 Skills 同步..."
python3 -c "
from utils.skills_checker import check_skills_sync, get_skills_sync_report

report = get_skills_sync_report()
print(f'后端 Skills: {report[\"backend_total\"]}')
print(f'前端 Skills: {report[\"frontend_total\"]}')

if report['frontend_only']:
    print(f'❌ 前端残留引用: {report[\"frontend_only\"]}')
    exit(1)

print('✅ Skills 同步检查通过')
"

cd ..

echo ""
echo ">>> 3. 检查前端构建..."
cd frontend
npm run build > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ 前端构建成功"
else
    echo "❌ 前端构建失败"
    exit 1
fi

cd ..

echo ""
echo "========== 检查完成 =========="
echo "✅ 所有检查通过，可以提交代码"