#!/bin/bash
# Her 系统评估一键执行脚本 - v3 增量版本
#
# 核心优化：
# 1. 断点续传：失败后重启，自动跳过已执行的用例
# 2. 增量写入：每个用例执行完立即保存结果
# 3. 容错机制：单个失败不影响其他用例
# 4. 依赖检查：自动安装缺失的 Python 依赖
#
# 用法：
#     ./run_eval.sh                    # 执行测试（增量模式）
#     ./run_eval.sh --force            # 强制重新执行所有用例
#     ./run_eval.sh --category happy_path  # 只执行指定分类
#     ./run_eval.sh --skip-judge       # 跳过 LLM Judge 评估
#     ./run_eval.sh --help             # 显示帮助

set -e

PROJECT_ROOT="/Users/sunmuchao/Downloads/ai_incubation_platform/Her"
cd "$PROJECT_ROOT"

# ============================================
# 帮助信息
# ============================================
show_help() {
    echo "========================================"
    echo "  Her 系统评估助手 (v3 增量版)"
    echo "========================================"
    echo ""
    echo "用法: ./run_eval.sh [选项]"
    echo ""
    echo "选项:"
    echo "  --force           强制重新执行所有用例（忽略已有结果）"
    echo "  --skip-judge      跳过 LLM-as-a-Judge 评估"
    echo "  --category <name> 只执行指定分类的用例"
    echo "  --mock            使用模拟 API（不需要后端服务）"
    echo "  --help            显示此帮助信息"
    echo ""
    echo "输出文件:"
    echo "  - JSON: tests/eval/evaluation_results.json"
    echo "  - HTML: tests/eval/evaluation_report.html"
    echo "  - Judge: tests/eval/judge_results.json"
    echo ""
    echo "特性:"
    echo "  ✅ 断点续传 - 失败后重启自动跳过已完成的用例"
    echo "  ✅ 增量写入 - 每个用例执行完立即保存结果"
    echo "  ✅ 容错机制 - 单个失败不影响其他用例"
    echo ""
}

if [[ "$1" == "--help" ]]; then
    show_help
    exit 0
fi

echo "========================================"
echo "  Her 系统评估助手 (v3 增量版)"
echo "========================================"

# ============================================
# 参数解析
# ============================================
SKIP_JUDGE=false
FORCE_RESTART=false
CATEGORY=""
USE_MOCK=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-judge)
            SKIP_JUDGE=true
            shift
            ;;
        --force)
            FORCE_RESTART=true
            shift
            ;;
        --category)
            CATEGORY="$2"
            shift 2
            ;;
        --mock)
            USE_MOCK=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            echo "使用 --help 查看帮助"
            exit 1
            ;;
    esac
done

# ============================================
# Phase 0: 环境检查与依赖安装
# ============================================
echo ""
echo "[Phase 0] 检查环境与依赖..."

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi
echo "✅ Python3 已安装"

# 检查关键依赖，缺失则安装
check_and_install_deps() {
    python3 -c "import requests" 2>/dev/null || {
        echo "⚠️ requests 未安装，正在安装..."
        pip install requests --quiet
    }

    python3 -c "import pythonjsonlogger" 2>/dev/null || {
        echo "⚠️ pythonjsonlogger 未安装，正在安装..."
        pip install python-json-logger --quiet
    }

    python3 -c "import llm" 2>/dev/null || {
        echo "⚠️ llm 模块未安装，正在检查..."
        # llm 模块在 src/llm 目录下，不需要安装
        echo "ℹ️ llm 模块使用本地 src/llm 目录"
    }
}

check_and_install_deps
echo "✅ Python 依赖检查完成"

# ============================================
# Phase 1: 服务检查（如果使用真实 API）
# ============================================
if [ "$USE_MOCK" = false ]; then
    echo ""
    echo "[Phase 1] 检查后端服务..."

    # 尝试多个端口
    BACKEND_RUNNING=false
    WORKING_PORT=""

    for PORT in 8000 8002 8001; do
        if curl -s --connect-timeout 3 "http://localhost:$PORT/health" > /dev/null 2>&1; then
            BACKEND_RUNNING=true
            WORKING_PORT=$PORT
            echo "✅ 后端服务运行正常 (端口 $PORT)"
            break
        fi
    done

    if [ "$BACKEND_RUNNING" = false ]; then
        echo "⚠️ 后端服务未运行"
        echo ""
        echo "请先启动后端服务:"
        echo "  cd Her/src && PYTHONPATH=. uvicorn main:app --port 8000"
        echo ""
        echo "或使用 --mock 参数使用模拟 API:"
        echo "  ./run_eval.sh --mock"
        echo ""
        exit 1
    fi
else
    echo ""
    echo "[Phase 1] 使用模拟 API（跳过服务检查）"
fi

# ============================================
# Phase 2: 执行测试（增量版本）
# ============================================
echo ""
echo "[Phase 2] 执行 Golden Dataset 测试 (增量版本)..."

# 构建参数
EVAL_ARGS="--real"
if [ "$USE_MOCK" = true ]; then
    EVAL_ARGS="--mock"
fi
if [ "$FORCE_RESTART" = true ]; then
    EVAL_ARGS="$EVAL_ARGS --force"
fi
if [ "$CATEGORY" != "" ]; then
    EVAL_ARGS="$EVAL_ARGS --category $CATEGORY"
fi

# 使用 v3 增量版本
python3 tests/eval/test_golden_dataset_v3.py $EVAL_ARGS

if [ ! -f "tests/eval/evaluation_results.json" ]; then
    echo "❌ 测试执行失败，未生成结果文件"
    exit 1
fi

echo "✅ 测试执行完成"

# ============================================
# Phase 3: LLM Judge 评估
# ============================================
if [ "$SKIP_JUDGE" = false ]; then
    echo ""
    echo "[Phase 3] LLM-as-a-Judge 评估..."

    # 检查 llm_judge.py 是否存在
    if [ -f "tests/eval/llm_judge.py" ]; then
        python3 tests/eval/llm_judge.py --input tests/eval/evaluation_results.json
        echo "✅ LLM Judge 评估完成"
    else
        echo "⚠️ llm_judge.py 未找到，跳过 LLM 评估"
    fi
fi

# ============================================
# Phase 4: 输出报告
# ============================================
echo ""
echo "========================================"
echo "  评估完成"
echo "========================================"
echo ""
echo "报告文件:"
echo "  - HTML: tests/eval/evaluation_report.html"
echo "  - JSON: tests/eval/evaluation_results.json"
if [ -f "tests/eval/judge_results.json" ]; then
    echo "  - Judge: tests/eval/judge_results.json"
fi
echo ""
echo "特性说明:"
echo "  ✅ 增量写入 - 每个用例执行完立即保存"
echo "  ✅ 断点续传 - 失败后重启自动跳过已完成用例"
echo "  ✅ 容错机制 - 单个失败不影响整体执行"
echo ""
echo "下一步:"
echo "  1. 查看报告: open tests/eval/evaluation_report.html"
echo "  2. 继续执行: ./run_eval.sh（自动跳过已完成的用例）"
echo "  3. 强制重跑: ./run_eval.sh --force"
echo ""