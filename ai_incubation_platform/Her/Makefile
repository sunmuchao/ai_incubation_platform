# Her + DeerFlow Makefile
#
# AI Native 架构：
# - DeerFlow 是 Agent 运行时（意图识别、工具编排、状态管理）
# - Her 提供业务 Tools（匹配、关系分析、约会策划）
# - 前端通过 deerflowClient 直接调用 DeerFlow

.PHONY: help dev dev-her dev-deerflow stop status logs test clean

# 与 README / start.sh 中 Her 后端默认一致（可覆盖：make dev-her HER_BACKEND_PORT=8000）
HER_BACKEND_PORT ?= 8002

# 默认目标：显示帮助
help:
	@echo ""
	@echo "Her + DeerFlow 启动命令"
	@echo ""
	@echo "  make dev          启动所有服务（DeerFlow + Her 后端 + Her 前端）"
	@echo "  make dev-her      只启动 Her（后端 + 前端）"
	@echo "  make dev-deerflow 只启动 DeerFlow Agent 运行时"
	@echo "  make stop         停止所有服务"
	@echo "  make status       检查服务状态"
	@echo "  make logs         查看日志"
	@echo "  make test         运行测试（DeerFlow: uv；Her: PYTHONPATH=src pytest）"
	@echo "  make clean        清理进程和日志"
	@echo ""
	@echo "端口说明："
	@echo "  DeerFlow LangGraph:  2024"
	@echo "  DeerFlow Gateway:    8001"
	@echo "  Her Backend:         $(HER_BACKEND_PORT)  (make dev-her / start.sh 默认与 README 一致)"
	@echo "  Her Frontend:        3005"
	@echo ""

# 启动所有服务（推荐）
dev:
	@./start.sh

# 只启动 Her（无 DeerFlow 集成）
dev-her:
	@echo "启动 Her（无 DeerFlow）..."
	@cd src && PYTHONPATH=. nohup uvicorn main:app --host 0.0.0.0 --port $(HER_BACKEND_PORT) > /tmp/her_backend.log 2>&1 &
	@cd frontend && nohup npm run dev > /tmp/her_frontend.log 2>&1 &
	@echo "Her 后端: http://localhost:$(HER_BACKEND_PORT)"
	@echo "Her 前端: http://localhost:3005"

# 只启动 DeerFlow
dev-deerflow:
	@echo "启动 DeerFlow Agent 运行时..."
	@export HER_PROJECT_ROOT=$(PWD)
	@cd deerflow/backend && nohup make dev > /tmp/deerflow.log 2>&1 &
	@echo "LangGraph: http://localhost:2024"
	@echo "Gateway:   http://localhost:8001"

# 停止所有服务
stop:
	@./stop.sh

# 检查服务状态
status:
	@echo ""
	@echo "服务状态检查："
	@echo ""
	@echo "DeerFlow LangGraph (2024):"
	@curl -s http://localhost:2024/ok > /dev/null 2>&1 && echo "  ✓ 运行中" || echo "  ✗ 未运行"
	@echo "DeerFlow Gateway (8001):"
	@curl -s http://localhost:8001/health > /dev/null 2>&1 && echo "  ✓ 运行中" || echo "  ✗ 未运行"
	@echo "Her Backend ($(HER_BACKEND_PORT)):"
	@curl -s http://localhost:$(HER_BACKEND_PORT)/docs > /dev/null 2>&1 && echo "  ✓ 运行中" || echo "  ✗ 未运行"
	@echo "Her Frontend (3005):"
	@curl -s http://localhost:3005 > /dev/null 2>&1 && echo "  ✓ 运行中" || echo "  ✗ 未运行"
	@echo "DeerFlow Integration:"
	@curl -s http://localhost:$(HER_BACKEND_PORT)/api/deerflow/status | python3 -m json.tool 2>/dev/null || echo "  ✗ API 未响应"
	@echo ""

# 查看日志
logs:
	@echo "日志文件位置："
	@echo "  DeerFlow:     /tmp/deerflow.log"
	@echo "  Her Backend:  src/logs/server.log"
	@echo "  Her Frontend: /tmp/her_frontend.log"
	@echo ""
	@echo "使用命令查看："
	@echo "  tail -f /tmp/deerflow.log"
	@echo "  tail -f src/logs/server.log"
	@echo "  tail -f /tmp/her_frontend.log"

# 运行测试：
# - DeerFlow：必须在 deerflow/backend 下用 uv（Python>=3.12），否则会误用上层 Her/pytest.ini 且 3.9 无法解析 harness 类型注解
# - Her：在仓库根目录 PYTHONPATH=src pytest tests
test:
	@echo "运行 DeerFlow 后端全量测试（deerflow/backend: uv run pytest）..."
	@$(MAKE) -C deerflow/backend test
	@echo ""
	@echo "运行 Her 后端测试（PYTHONPATH=src）..."
	@PYTHONPATH=src python3 -m pytest tests -v --tb=short

# 清理
clean:
	@echo "清理进程..."
	@pkill -f "uvicorn" 2>/dev/null
	@pkill -f "vite" 2>/dev/null
	@pkill -f "langgraph" 2>/dev/null
	@pkill -f "deerflow" 2>/dev/null
	@rm -f /tmp/her_backend.pid /tmp/her_frontend.pid /tmp/deerflow.pid
	@rm -f /tmp/her_backend.log /tmp/her_frontend.log /tmp/deerflow.log
	@echo "✓ 清理完成"

# 快速健康检查
health:
	@curl -s http://localhost:$(HER_BACKEND_PORT)/api/deerflow/status | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'DeerFlow: {d.get(\"available\", False)}'); print(f'Memory: {d.get(\"memory_enabled\", False)}')"