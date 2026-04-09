#!/bin/bash
# AI 注册对话系统测试运行脚本

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "========================================"
echo "AI 注册对话系统测试套件"
echo "========================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试结果计数
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 函数：运行测试并统计结果
run_tests() {
    local test_name=$1
    local test_path=$2

    echo "----------------------------------------"
    echo "运行：$test_name"
    echo "----------------------------------------"

    if output=$(python -m pytest "$test_path" -v --tb=no 2>&1); then
        # 提取测试结果
        passed=$(echo "$output" | grep -oP '\d+(?= passed)' || echo "0")
        failed=$(echo "$output" | grep -oP '\d+(?= failed)' || echo "0")
        warnings=$(echo "$output" | grep -oP '\d+(?= warnings)' || echo "0")

        echo -e "${GREEN}✓ 通过: $passed${NC}"
        if [ "$failed" != "0" ]; then
            echo -e "${RED}✗ 失败: $failed${NC}"
        fi
        if [ "$warnings" != "0" ]; then
            echo -e "${YELLOW}⚠ 警告: $warnings${NC}"
        fi

        TOTAL_TESTS=$((TOTAL_TESTS + passed + failed))
        PASSED_TESTS=$((PASSED_TESTS + passed))
        FAILED_TESTS=$((FAILED_TESTS + failed))
    else
        echo -e "${RED}✗ 测试执行失败${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi

    echo ""
}

# 1. 运行 Service 层测试
run_tests "Service 层单元测试" "tests/test_registration_conversation_service.py"

# 2. 运行 API 层测试
run_tests "API 层集成测试" "tests/test_registration_conversation_api.py"

# 3. 运行端到端测试
run_tests "端到端集成测试" "tests/test_registration_conversation_e2e.py"

# 打印摘要
echo "========================================"
echo "测试摘要"
echo "========================================"
echo "总测试数：$TOTAL_TESTS"
echo -e "通过：${GREEN}$PASSED_TESTS${NC}"
echo -e "失败：${RED}$FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✓ 所有测试通过!${NC}"
    exit 0
else
    echo -e "${RED}✗ 有 $FAILED_TESTS 个测试失败${NC}"
    exit 1
fi
