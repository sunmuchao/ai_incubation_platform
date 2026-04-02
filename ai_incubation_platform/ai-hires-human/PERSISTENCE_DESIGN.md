# 持久化存储方案设计

## 现状
当前版本使用内存存储，仅适用于演示和开发环境。生产环境需要切换到持久化存储方案。

## 技术选型
### 数据库选型
- **主数据库**: PostgreSQL 14+
  - 支持丰富的数据类型和JSONB字段，适合存储任务的动态属性
  - 支持ACID事务，保证支付结算数据一致性
  - 强大的查询能力，支持复杂的筛选和搜索
- **缓存**: Redis 6+
  - 存储热门任务搜索结果，提升查询性能
  - 分布式锁，防止任务重复接单
  - 会话存储和限流

## 表结构设计

### 1. 任务表 (tasks)
```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ai_employer_id VARCHAR(255) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    requirements TEXT[] DEFAULT '{}',
    interaction_type VARCHAR(20) NOT NULL DEFAULT 'digital',
    capability_gap TEXT NOT NULL DEFAULT '',
    acceptance_criteria TEXT[] DEFAULT '{}',
    location_hint TEXT,
    required_skills JSONB DEFAULT '{}',
    priority VARCHAR(20) NOT NULL DEFAULT 'medium',
    status VARCHAR(20) NOT NULL DEFAULT 'published',
    reward_amount DECIMAL(10,2) NOT NULL DEFAULT 0.0,
    reward_currency VARCHAR(3) NOT NULL DEFAULT 'CNY',
    deadline TIMESTAMPTZ,
    worker_id VARCHAR(255),
    delivery_content TEXT,
    delivery_attachments TEXT[] DEFAULT '{}',
    submitted_at TIMESTAMPTZ,
    callback_url TEXT,

    -- 人工兜底字段
    review_reason TEXT,
    reviewer_id VARCHAR(255),
    appeal_count INT NOT NULL DEFAULT 0,
    is_disputed BOOLEAN NOT NULL DEFAULT FALSE,

    -- 反作弊字段
    submission_count INT NOT NULL DEFAULT 0,
    last_submitted_at TIMESTAMPTZ,
    delivery_content_hash VARCHAR(64),
    cheating_flag BOOLEAN NOT NULL DEFAULT FALSE,
    cheating_reason TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_ai_employer_id ON tasks(ai_employer_id);
CREATE INDEX idx_tasks_worker_id ON tasks(worker_id);
CREATE INDEX idx_tasks_interaction_type ON tasks(interaction_type);
CREATE INDEX idx_tasks_reward_amount ON tasks(reward_amount);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
CREATE INDEX idx_tasks_required_skills ON tasks USING GIN (required_skills);
```

### 2. 支付交易表 (payment_transactions)
```sql
CREATE TABLE payment_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_type VARCHAR(50) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'CNY',
    payer_id VARCHAR(255),
    payee_id VARCHAR(255),
    task_id UUID REFERENCES tasks(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    payment_method VARCHAR(50),
    external_transaction_id VARCHAR(255),
    description TEXT,
    fee_amount DECIMAL(10,2) NOT NULL DEFAULT 0.0,
    completed_at TIMESTAMPTZ,
    failed_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_payment_tx_payer_id ON payment_transactions(payer_id);
CREATE INDEX idx_payment_tx_payee_id ON payment_transactions(payee_id);
CREATE INDEX idx_payment_tx_task_id ON payment_transactions(task_id);
CREATE INDEX idx_payment_tx_status ON payment_transactions(status);
CREATE INDEX idx_payment_tx_created_at ON payment_transactions(created_at DESC);
```

### 3. 用户钱包表 (wallets)
```sql
CREATE TABLE wallets (
    user_id VARCHAR(255) PRIMARY KEY,
    balance DECIMAL(10,2) NOT NULL DEFAULT 0.0,
    frozen_balance DECIMAL(10,2) NOT NULL DEFAULT 0.0,
    currency VARCHAR(3) NOT NULL DEFAULT 'CNY',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 4. 反作弊全局哈希表 (anti_cheat_hashes)
```sql
CREATE TABLE anti_cheat_hashes (
    content_hash VARCHAR(64) PRIMARY KEY,
    task_id UUID NOT NULL REFERENCES tasks(id),
    worker_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_anti_cheat_hashes_worker_id ON anti_cheat_hashes(worker_id);
CREATE INDEX idx_anti_cheat_hashes_created_at ON anti_cheat_hashes(created_at DESC);
```

### 5. 工人提交记录表 (worker_submissions)
```sql
CREATE TABLE worker_submissions (
    id SERIAL PRIMARY KEY,
    worker_id VARCHAR(255) NOT NULL,
    task_id UUID NOT NULL REFERENCES tasks(id),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_worker_submissions_worker_id ON worker_submissions(worker_id, submitted_at DESC);
```

## 迁移方案
### 阶段1：接口兼容层
- 保持现有TaskService接口不变，内部切换到数据库存储
- 新增Repository层，封装数据库操作
- 支持内存和数据库两种存储方式，通过配置切换

### 阶段2：数据迁移工具
- 提供内存数据导出到数据库的脚本
- 支持平滑迁移，无停机切换

### 阶段3：性能优化
- 对高频查询添加缓存
- 实现搜索结果分页
- 异步处理回调和非核心流程

## ORM选型
推荐使用SQLAlchemy 2.0+，理由：
- 类型安全，支持Python类型提示
- 与Pydantic集成良好
- 支持异步查询（asyncpg驱动）
- 迁移工具成熟（Alembic）

## 配置示例
```python
# 数据库连接配置
DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/ai_hires_human"

# Redis配置
REDIS_URL = "redis://localhost:6379/0"
```

## 事务边界设计
1. **任务接单**: 开启事务，检查任务状态 → 更新任务状态 → 提交
2. **提交交付物**: 反作弊检测 → 更新任务状态 → 提交
3. **任务支付**: 扣减雇主余额 → 记录交易 → 增加工人余额 → 提交（全部成功或全部失败）
4. **退款**: 查找原交易 → 创建退款交易 → 回滚余额 → 提交
