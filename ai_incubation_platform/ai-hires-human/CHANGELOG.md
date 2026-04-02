# 更新日志

## v0.4.0 (2026-04-02)
### P1优先级功能实现
#### 1. 反作弊与重复交付检测功能 ✅
- **新增模块**: `src/services/anti_cheat_service.py`
- **核心功能**:
  - 提交频率限制：防止恶意刷屏，支持最小间隔和小时次数限制
  - 重复交付检测：基于内容哈希识别重复提交
  - 相似内容检测：基于Jaccard系数的文本相似度比对
  - 工人风险评分：基于历史行为计算风险等级
  - 作弊标记功能：支持管理员标记作弊任务
- **API新增**:
  - `POST /api/tasks/{task_id}/submit` 已集成反作弊检测
  - `GET /api/workers/{worker_id}/risk-score` 查询工人风险分数
  - `POST /api/tasks/{task_id}/mark-cheating` 标记作弊任务
- **模型扩展**: Task模型新增反作弊相关字段

#### 2. 支付/结算接口层（Mock实现）✅
- **新增模块**:
  - `src/models/payment.py` 支付相关数据模型
  - `src/services/payment_service.py` Mock支付服务实现
  - `src/api/payment.py` 支付相关API接口
- **核心功能**:
  - 钱包管理：余额查询、充值、提现
  - 任务支付：验收通过后自动结算，支持平台服务费扣除
  - 退款功能：任务取消/验收不通过时退款
  - 交易记录：用户交易明细、任务关联交易查询
- **API新增**:
  - `POST /api/payment/deposit` 账户充值
  - `POST /api/payment/payout` 工人提现
  - `POST /api/payment/task-payment` 处理任务支付
  - `POST /api/payment/refund/{task_id}` 任务退款
  - `GET /api/payment/wallets/{user_id}` 查询钱包余额
  - `GET /api/payment/transactions/{transaction_id}` 交易详情
  - `GET /api/payment/users/{user_id}/transactions` 用户交易记录
  - `GET /api/payment/tasks/{task_id}/transactions` 任务关联交易

#### 3. 多维度搜索与筛选功能增强 ✅
- **搜索接口升级**: `/api/tasks/search` 新增以下筛选参数：
  - `max_reward`: 最高报酬筛选
  - `location`: 地点模糊匹配
  - `priority`: 任务优先级筛选
  - `keyword`: 全文关键词搜索（标题、描述、需求等）
  - `sort_by`: 排序字段（created_at, reward, priority, deadline）
  - `sort_order`: 排序方向（asc/desc）
- **优化**: 搜索结果默认按创建时间倒序排列

#### 4. 持久化存储方案设计 ✅
- **新增文档**: `PERSISTENCE_DESIGN.md`
- **内容**:
  - 技术选型：PostgreSQL + Redis
  - 完整的表结构设计与索引规划
  - 分阶段迁移方案
  - ORM选型与事务边界设计
  - 配置示例

### 其他改进
- 版本号升级到v0.4.0
- 主入口注册支付API路由
- 根路径返回信息新增支付接口入口
- requirements.txt新增持久化相关依赖

## v0.3.0 (2026-03-xx)
### P0优先级功能完成
- ✅ 任务发布 → 投标/接单 → 交付 → 验收的端到端API与状态机
- ✅ AI决策与验收接口与人工兜底策略文档化
- ✅ callback_url与异步事件行为稳定
