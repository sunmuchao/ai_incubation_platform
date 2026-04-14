#!/bin/bash
#
# 临时文件清理脚本
#
# 清理项目中的临时文件，包括：
# - SQLite 内存数据库文件 (:memory:*)
# - Python 缓存 (__pycache__, .pytest_cache)
# - 测试数据库文件 (test_*.db)
# - 日志文件 (超过30天的)
#
# 使用方法：
#     ./scripts/cleanup_temp_files.sh
#     ./scripts/cleanup_temp_files.sh --dry-run  # 只显示不删除
#

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY_RUN=false

# 解析参数
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "=== DRY RUN MODE (不实际删除) ==="
fi

echo "=== Her 项目临时文件清理 ==="
echo "项目路径: $PROJECT_ROOT"
echo "清理时间: $(date)"
echo ""

# 统计函数
count_files() {
    find "$PROJECT_ROOT" -name "$1" -type f 2>/dev/null | wc -l | tr -d ' '
}

# 清理函数
cleanup_files() {
    local pattern="$1"
    local desc="$2"
    local count=$(count_files "$pattern")

    if [[ $count -gt 0 ]]; then
        echo "清理 $desc: $count 个文件"

        if [[ "$DRY_RUN" == "true" ]]; then
            find "$PROJECT_ROOT" -name "$pattern" -type f 2>/dev/null | head -10
        else
            find "$PROJECT_ROOT" -name "$pattern" -type f -delete 2>/dev/null || true
        fi
    else
        echo "$desc: 无需清理"
    fi
}

# 1. 清理 SQLite 内存数据库文件
cleanup_files ":memory:*" "SQLite 内存数据库"

# 2. 清理 Python 缓存目录
echo ""
echo "清理 Python 缓存目录..."
pycache_count=$(find "$PROJECT_ROOT" -type d -name "__pycache__" 2>/dev/null | wc -l | tr -d ' ')
pytest_count=$(find "$PROJECT_ROOT" -type d -name ".pytest_cache" 2>/dev/null | wc -l | tr -d ' ')

if [[ $pycache_count -gt 0 ]]; then
    echo "  __pycache__: $pycache_count 个目录"
    if [[ "$DRY_RUN" == "true" ]]; then
        find "$PROJECT_ROOT" -type d -name "__pycache__" 2>/dev/null | head -5
    else
        find "$PROJECT_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    fi
fi

if [[ $pytest_count -gt 0 ]]; then
    echo "  .pytest_cache: $pytest_count 个目录"
    if [[ "$DRY_RUN" == "true" ]]; then
        find "$PROJECT_ROOT" -type d -name ".pytest_cache" 2>/dev/null | head -5
    else
        find "$PROJECT_ROOT" -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    fi
fi

# 3. 清理测试数据库文件
echo ""
cleanup_files "test_*.db" "测试数据库"

# 4. 清理旧日志文件（超过30天）
echo ""
echo "清理旧日志文件..."
if [[ "$DRY_RUN" == "true" ]]; then
    find "$PROJECT_ROOT/logs" -name "*.log" -mtime +30 -type f 2>/dev/null | head -10
else
    deleted_logs=$(find "$PROJECT_ROOT/logs" -name "*.log" -mtime +30 -type f -delete -print 2>/dev/null | wc -l | tr -d ' ')
    echo "  已删除 $deleted_logs 个超过30天的日志文件"
fi

# 5. 清理临时数据库文件
echo ""
cleanup_files "*.db-journal" "SQLite journal 文件"
cleanup_files "*.db-wal" "SQLite WAL 文件"

# 总结
echo ""
echo "=== 清理完成 ==="
if [[ "$DRY_RUN" == "true" ]]; then
    echo "提示: 运行不带 --dry-run 参数来实际删除文件"
fi

# 显示项目大小
echo ""
echo "当前项目大小:"
du -sh "$PROJECT_ROOT" 2>/dev/null | cut -f1