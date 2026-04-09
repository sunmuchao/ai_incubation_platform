# 日志系统使用指南

## 日志架构概述

本项目日志系统经过全面增强，提供以下核心能力：

| 能力 | 说明 |
|------|------|
| **链路追踪** | 通过 `trace_id` 和 `span_id` 实现跨模块调用链追踪 |
| **敏感数据脱敏** | 自动脱敏邮箱、手机号、JWT、密码等敏感信息 |
| **结构化输出** | 支持 JSON 和文本两种格式，便于日志分析系统解析 |
| **分层日志** | 按模块前缀分类，支持按级别过滤 |

## 日志模块结构

```
src/utils/logger.py
├── logger              # 全局日志实例
├── get_trace_id()      # 获取/创建链路追踪 ID
├── set_trace_id()      # 设置链路追踪 ID（接收上游请求）
├── get_span_id()       # 获取当前操作 Span ID
├── log_execution()     # 函数执行日志装饰器
└── log_api_call()      # API 调用日志装饰器
```

## 日志格式

### 文本格式（开发环境）
```
2026-04-09 12:00:00,000 - matchmaker-agent - INFO - [a1b2c3d4e5f6:12345678] - 📡 [API:SEND] START trace_id=a1b2c3d4e5f6
```

### JSON 格式（生产环境）
```json
{
  "asctime": "2026-04-09 12:00:00,000",
  "name": "matchmaker-agent",
  "levelname": "INFO",
  "message": "📡 [API:SEND] START",
  "trace_id": "a1b2c3d4e5f6",
  "span_id": "12345678",
  "module": "chat",
  "funcName": "send_message",
  "lineno": 100
}
```

## 日志级别使用规范

| 级别 | 使用场景 | 示例 |
|------|----------|------|
| `DEBUG` | 详细调试信息，生产环境关闭 | 方法入口参数、分支选择 |
| `INFO` | 关键业务节点 | API 请求开始/结束、状态变更 |
| `WARNING` | 可恢复的异常、降级 | 缓存未命中、API 降级 |
| `ERROR` | 不可恢复的错误 | 数据库异常、业务逻辑失败 |

## 日志装饰器使用

### 1. log_execution - 函数执行日志

```python
from utils.logger import logger, log_execution

@log_execution(
    logger=logger,
    log_level="INFO",
    log_inputs=True,      # 记录入参
    log_outputs=True,     # 记录返回值
    prefix="[UserService]"
)
def get_user(self, user_id: str) -> User:
    ...
```

**输出示例：**
```
▶️ ENTER [UserService]src.services.user_service.get_user(span=abc123) args=(...,), kwargs={'user_id': '123'}
✅ EXIT [UserService]src.services.user_service.get_user(span=abc123) elapsed=15.23ms result=User(...)
```

### 2. log_api_call - API 调用日志

```python
from utils.logger import logger, log_api_call, get_trace_id

@router.post("/send")
@log_api_call(logger=logger, endpoint_name="send_message")
async def send_message(request: MessageRequest):
    trace_id = get_trace_id()
    logger.info(f"📡 [API:SEND] START trace_id={trace_id}")
    ...
```

**输出示例：**
```
📡 API [send_message] START trace_id=a1b2c3d4e5f6 kwargs={'request': {...}}
📡 API [send_message] SUCCESS trace_id=a1b2c3d4e5f6 elapsed=45.67ms
```

## 模块日志前缀规范

| 模块 | 前缀 | 图标 |
|------|------|------|
| API 层 | `[API:*]` | 📡 |
| 服务层 | `[SERVICE:*]` | ⚙️ |
| 数据库层 | `[DB:*]` | 🗄️ |
| Agent 层 | `[AGENT:*]` | 🤖 |
| LLM 集成 | `[LLM:*]` | 🧠 |
| 聊天服务 | `[CHAT:*]` | 💬 |
| 匹配服务 | `[MATCH:*]` | ❤️ |

## 链路追踪使用

### 在 API 入口生成 trace_id

```python
from utils.logger import get_trace_id

@router.post("/send")
async def send_message(request: MessageRequest):
    trace_id = get_trace_id()  # 生成或获取 trace_id
    logger.info(f"📡 [API:SEND] START trace_id={trace_id}")

    # 调用服务层
    result = chat_service.send_message(...)
    return result
```

### 在异步任务中透传 trace_id

```python
from utils.logger import get_trace_id, set_trace_id
import asyncio

async def background_task(data: dict):
    # 如果需要延续上游 trace，可以传递 trace_id
    # 如果是新任务，会自动生成新的 trace_id
    trace_id = get_trace_id()
    logger.info(f"🤖 [AGENT:TASK] START trace_id={trace_id}")
    ...

# 在创建异步任务时
asyncio.create_task(background_task(data))
```

## 敏感数据自动脱敏

以下字段会自动脱敏：

| 类型 | 脱敏规则 | 示例 |
|------|----------|------|
| 邮箱 | `a***@example.com` | `zhang***@gmail.com` |
| 手机号 | `138****1234` | `138****5678` |
| JWT/Token | `[SENSITIVE_JWT]` | `[SENSITIVE_JWT]` |
| 密码 | `password=[SENSITIVE]` | `password=[SENSITIVE]` |
| 身份证 | `[SENSITIVE]` | `[SENSITIVE]` |

## 日志配置

通过环境变量配置日志行为：

```bash
# 日志级别
LOG_LEVEL=INFO  # DEBUG/INFO/WARNING/ERROR

# 日志格式
LOG_FORMAT=text  # text/json

# 日志清理
LOG_CLEANER_ENABLED=true
LOG_CLEANER_MAX_AGE_DAYS=7
LOG_CLEANER_MAX_SIZE_MB=50
LOG_CLEANER_MAX_FILES=20

# 日志备份
LOG_BACKUP_KEEP_COUNT=10
```

## 日志文件位置

```
Her/logs/
├── server.log          # 主日志文件
├── server.log.1        # 历史日志（滚动备份）
├── server.log.2
└── ...
```

## 日志查询示例

### 按 trace_id 查询完整调用链

```bash
# 查找特定 trace_id 的所有日志
grep "a1b2c3d4e5f6" logs/server.log

# 使用 jq 分析 JSON 日志
cat logs/server.log | jq 'select(.trace_id == "a1b2c3d4e5f6")'
```

### 按模块前缀过滤

```bash
# 查看 API 层日志
grep "📡 \[API:" logs/server.log

# 查看 Agent 层日志
grep "🤖 \[AGENT:" logs/server.log

# 查看错误日志
grep "ERROR" logs/server.log
```

### 按耗时分析慢调用

```bash
# 查找超过 1 秒的 API 调用
grep "elapsed=" logs/server.log | grep -E "elapsed=[0-9]{4,}"
```

## 最佳实践

1. **入口必打日志**：所有 API 入口、定时任务入口必须记录日志
2. **异常必打日志**：所有 `except` 块必须记录异常信息和堆栈
3. **耗时必记录**：关键业务操作必须记录 `elapsed=XXms`
4. **敏感不泄露**：禁止在日志中明文输出密码、token、手机号等
5. **链路可追踪**：跨模块调用确保 `trace_id` 透传
6. **日志有分级**：根据重要性选择合适的日志级别

## 常见问题

### Q: 为什么我的日志没有 trace_id？
A: 确保在调用日志前已经调用了 `get_trace_id()`，或者使用了日志装饰器。

### Q: 如何关闭生产环境的 DEBUG 日志？
A: 设置环境变量 `LOG_LEVEL=INFO`。

### Q: 如何查看异步任务的调用链？
A: 在异步任务创建时记录 `trace_id`，并在任务内部使用相同的 `trace_id`。
