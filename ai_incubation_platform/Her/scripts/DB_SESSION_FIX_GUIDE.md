# 数据库会话管理修复指南

**创建时间**: 2026-04-09  
**状态**: 进行中

---

## 问题描述

多个服务文件使用不一致的数据库会话管理模式，可能导致连接泄漏：

```python
# 模式 1: 直接创建（可能忘记关闭）
db = SessionLocal()

# 模式 2: 条件创建（关闭逻辑不统一）
db = db_session if db_session else SessionLocal()

# 模式 3: 类初始化时创建（生命周期不明确）
def __init__(self):
    self._db = SessionLocal()
```

---

## 修复方案

### 方案 A: 使用上下文管理器（推荐）

```python
from utils.db_session import db_session_context

async def some_function():
    async with db_session_context() as db:
        # 自动 commit 和 close
        db.query(...)
```

### 方案 B: 使用装饰器

```python
from utils.db_session import with_async_db_session

@with_async_db_session
async def some_method(self, db: Session, ...):
    # 自动注入 db 并管理生命周期
    ...
```

### 方案 C: 使用工具函数（适合类方法）

```python
from utils.db_session import get_session_for_service, close_session_if_needed

def some_method(self, provided_db: Optional[Session] = None):
    db, should_close = get_session_for_service(provided_db)
    try:
        # 使用 db
        ...
    finally:
        close_session_if_needed(db, should_close)
```

### 方案 D: 类内部管理（适合服务类）

```python
class SomeService:
    def __init__(self, db: Optional[Session] = None):
        self._db = db
        self._should_close_db = db is None

    def _get_db(self) -> Session:
        if self._db is None:
            self._db = SessionLocal()
            self._should_close_db = True
        return self._db

    def close(self):
        if self._should_close_db and self._db is not None:
            self._db.commit()
            self._db.close()
            self._db = None
            self._should_close_db = False
```

---

## 已修复文件

| 文件 | 修复方案 | 状态 |
|------|----------|------|
| `behavior_event_emitter.py` | 上下文管理器 | ✅ |
| `adaptive_ui_service.py` | 方案 D | ✅ |
| `ai_feedback_service.py` | 方案 D | ✅ |

---

## 待修复文件

### 高优先级（直接创建 SessionLocal 且无关闭逻辑）

| 文件 | 行号 | 问题 | 建议方案 |
|------|------|------|----------|
| `date_suggestion_service.py` | 420, 479 | 直接创建无关闭 | 方案 C |
| `digital_twin_service.py` | 30 | 类初始化创建 | 方案 D |
| `behavior_credit_service.py` | 76 | 类初始化创建 | 方案 D |
| `ai_learning_service.py` | 31 | 类初始化创建 | 方案 D |
| `payment_service.py` | 899 | 直接创建无关闭 | 方案 C |
| `agent_intervention_service.py` | 95 | 类初始化创建 | 方案 D |

### 中优先级（条件创建但有潜在泄漏风险）

| 文件 | 行号 | 问题 |
|------|------|------|
| `p11_services.py` | 597, 669 | 条件创建 |
| `p12_behavior_lab_service.py` | 多处 | 条件创建 |
| `couple_game_service.py` | 多处 | 条件创建 |

---

## 修复检查清单

修复每个文件时遵循以下步骤：

1. [ ] 识别会话创建模式
2. [ ] 选择合适的修复方案 (A/B/C/D)
3. [ ] 添加 `try/finally` 确保关闭
4. [ ] 添加异常处理和回滚
5. [ ] 测试修复后的代码
6. [ ] 更新此文档

---

## 测试验证

修复后运行以下命令验证：

```bash
# 运行数据库相关测试
pytest tests/ -k "database or db or session" -v

# 检查连接泄漏（观察日志）
python -m src.main

# 压力测试（模拟高并发）
# 观察是否出现 "too many connections" 错误
```
