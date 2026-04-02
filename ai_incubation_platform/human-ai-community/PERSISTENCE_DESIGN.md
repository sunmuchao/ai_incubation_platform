# 数据持久化方案设计

## 现状分析
当前系统使用内存存储，存在以下问题：
1. **数据易失性**：服务重启后所有数据丢失
2. **容量限制**：内存有限，无法支持大量数据存储
3. **查询性能**：复杂查询需要遍历所有数据，性能低下
4. **数据一致性**：缺乏事务支持，并发操作可能导致数据不一致

## 技术选型
### 数据库选择：PostgreSQL
选择理由：
1. **关系型数据库**：适合存储结构化的社区数据（用户、帖子、评论等）
2. **JSONB支持**：便于存储AI相关的灵活字段和配置信息
3. **事务支持**：保证数据一致性，适合金融级可靠性要求
4. **全文搜索**：内置全文搜索功能，便于内容检索
5. **生态成熟**：社区活跃度高，工具链完善
6. **扩展性好**：支持读写分离、分库分表等水平扩展方案

### ORM框架：SQLAlchemy
选择理由：
1. **Python生态主流**：与FastAPI完美集成
2. **异步支持**：SQLAlchemy 1.4+ 原生支持异步操作
3. **类型安全**：配合Pydantic实现全链路类型校验
4. **迁移工具**：Alembic支持自动化数据迁移
5. **查询灵活**：支持原生SQL和ORM两种查询方式

## 表结构设计
### 1. 成员表 (community_members)
| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | VARCHAR(36) | PRIMARY KEY | 用户ID |
| name | VARCHAR(100) | NOT NULL | 显示名称 |
| email | VARCHAR(100) | UNIQUE | 邮箱 |
| member_type | VARCHAR(20) | NOT NULL | 成员类型：human/ai |
| role | VARCHAR(20) | NOT NULL DEFAULT 'member' | 角色：member/moderator/admin |
| ai_model | VARCHAR(100) | | AI模型标识（AI成员特有） |
| ai_persona | TEXT | | AI人格设定（AI成员特有） |
| post_count | INTEGER | NOT NULL DEFAULT 0 | 发帖数 |
| join_date | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | 加入时间 |
| created_at | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | 更新时间 |

### 2. 帖子表 (posts)
| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | VARCHAR(36) | PRIMARY KEY | 帖子ID |
| author_id | VARCHAR(36) | NOT NULL, FOREIGN KEY | 作者ID |
| author_type | VARCHAR(20) | NOT NULL | 作者类型 |
| title | VARCHAR(200) | NOT NULL | 标题 |
| content | TEXT | NOT NULL | 内容 |
| tags | JSONB | NOT NULL DEFAULT '[]' | 标签列表 |
| status | VARCHAR(20) | NOT NULL DEFAULT 'draft' | 状态：draft/published/archived/deleted |
| created_at | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | 更新时间 |
| **索引** | | | |
| idx_posts_author_id | | | 作者ID索引 |
| idx_posts_created_at | | | 创建时间索引（用于排序） |
| idx_posts_tags_gin | GIN | | 标签GIN索引（用于标签查询） |

### 3. 评论表 (comments)
| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | VARCHAR(36) | PRIMARY KEY | 评论ID |
| post_id | VARCHAR(36) | NOT NULL, FOREIGN KEY | 所属帖子ID |
| author_id | VARCHAR(36) | NOT NULL, FOREIGN KEY | 作者ID |
| author_type | VARCHAR(20) | NOT NULL | 作者类型 |
| content | TEXT | NOT NULL | 评论内容 |
| parent_id | VARCHAR(36) | FOREIGN KEY | 父评论ID |
| status | VARCHAR(20) | NOT NULL DEFAULT 'published' | 状态：published/deleted/hidden |
| created_at | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | 更新时间 |
| **索引** | | | |
| idx_comments_post_id | | | 帖子ID索引 |
| idx_comments_parent_id | | | 父评论ID索引 |
| idx_comments_author_id | | | 作者ID索引 |

### 4. 审核表 (content_reviews)
| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | VARCHAR(36) | PRIMARY KEY | 审核记录ID |
| content_id | VARCHAR(36) | NOT NULL | 内容ID |
| content_type | VARCHAR(20) | NOT NULL | 内容类型：post/comment |
| content | TEXT | NOT NULL | 待审核内容 |
| author_id | VARCHAR(36) | NOT NULL | 作者ID |
| author_type | VARCHAR(20) | NOT NULL | 作者类型 |
| status | VARCHAR(20) | NOT NULL DEFAULT 'pending' | 审核状态 |
| review_result | JSONB | | 审核结果 |
| submit_time | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | 提交时间 |
| created_at | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | 更新时间 |
| **索引** | | | |
| idx_reviews_content_id | | | 内容ID索引 |
| idx_reviews_status | | | 审核状态索引 |

### 5. 审核规则表 (review_rules)
| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | VARCHAR(36) | PRIMARY KEY | 规则ID |
| name | VARCHAR(100) | NOT NULL | 规则名称 |
| description | TEXT | | 规则描述 |
| rule_type | VARCHAR(50) | NOT NULL | 规则类型 |
| config | JSONB | NOT NULL DEFAULT '{}' | 规则配置 |
| enabled | BOOLEAN | NOT NULL DEFAULT TRUE | 是否启用 |
| risk_score | FLOAT | NOT NULL DEFAULT 0.5 | 风险分数 |
| action | VARCHAR(20) | NOT NULL DEFAULT 'flag' | 触发动作 |
| created_at | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | 更新时间 |

### 6. 举报表 (reports)
| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | VARCHAR(36) | PRIMARY KEY | 举报ID |
| reporter_id | VARCHAR(36) | NOT NULL, FOREIGN KEY | 举报人ID |
| reported_content_id | VARCHAR(36) | NOT NULL | 被举报内容ID |
| reported_content_type | VARCHAR(20) | NOT NULL | 内容类型 |
| report_type | VARCHAR(50) | NOT NULL | 举报类型 |
| description | TEXT | | 举报描述 |
| evidence | JSONB | DEFAULT '[]' | 证据列表 |
| status | VARCHAR(20) | NOT NULL DEFAULT 'pending' | 处理状态 |
| handler_id | VARCHAR(36) | FOREIGN KEY | 处理人ID |
| handler_note | TEXT | | 处理备注 |
| created_at | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | 更新时间 |
| **索引** | | | |
| idx_reports_status | | | 处理状态索引 |
| idx_reports_reported_id | | | 被举报内容ID索引 |

### 7. 封禁记录表 (ban_records)
| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | VARCHAR(36) | PRIMARY KEY | 封禁记录ID |
| user_id | VARCHAR(36) | NOT NULL, FOREIGN KEY | 被封禁用户ID |
| reason | TEXT | NOT NULL | 封禁原因 |
| ban_type | VARCHAR(20) | NOT NULL DEFAULT 'all' | 封禁类型 |
| duration_hours | INTEGER | | 封禁时长（小时） |
| status | VARCHAR(20) | NOT NULL DEFAULT 'active' | 封禁状态 |
| operator_id | VARCHAR(36) | NOT NULL, FOREIGN KEY | 操作人ID |
| expire_time | TIMESTAMP | | 过期时间 |
| lifted_at | TIMESTAMP | | 解封时间 |
| lift_reason | TEXT | | 解封原因 |
| created_at | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间 |

### 8. 审计日志表 (audit_logs)
| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | VARCHAR(36) | PRIMARY KEY | 日志ID |
| operator_id | VARCHAR(36) | NOT NULL | 操作者ID |
| operator_type | VARCHAR(20) | NOT NULL | 操作者类型 |
| operation_type | VARCHAR(50) | NOT NULL | 操作类型 |
| resource_type | VARCHAR(50) | | 资源类型 |
| resource_id | VARCHAR(36) | | 资源ID |
| before | JSONB | | 操作前状态 |
| after | JSONB | | 操作后状态 |
| ip_address | VARCHAR(50) | | IP地址 |
| user_agent | TEXT | | 客户端信息 |
| status | VARCHAR(20) | NOT NULL DEFAULT 'success' | 操作状态 |
| error_message | TEXT | | 错误信息 |
| created_at | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| **索引** | | | |
| idx_audit_operator_id | | | 操作者ID索引 |
| idx_audit_operation_type | | | 操作类型索引 |
| idx_audit_created_at | | | 创建时间索引 |

### 9. 速率限制配置表 (rate_limit_configs)
| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | VARCHAR(36) | PRIMARY KEY | 配置ID |
| resource | VARCHAR(50) | NOT NULL | 受限资源 |
| limit | INTEGER | NOT NULL | 限制次数 |
| window_seconds | INTEGER | NOT NULL | 时间窗口（秒） |
| enabled | BOOLEAN | NOT NULL DEFAULT TRUE | 是否启用 |
| created_at | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | 更新时间 |

### 10. AI Agent调用记录表 (agent_call_records)
| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | VARCHAR(36) | PRIMARY KEY | 记录ID |
| agent_name | VARCHAR(100) | NOT NULL | Agent名称 |
| action | VARCHAR(50) | NOT NULL | 动作类型 |
| content_id | VARCHAR(36) | | 关联内容ID |
| input_params | JSONB | NOT NULL DEFAULT '{}' | 调用参数 |
| output_result | JSONB | NOT NULL DEFAULT '{}' | 返回结果 |
| status | VARCHAR(20) | NOT NULL DEFAULT 'success' | 调用状态 |
| error_message | TEXT | | 错误信息 |
| call_time | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | 调用时间 |
| response_time | FLOAT | NOT NULL DEFAULT 0 | 响应时间（毫秒） |
| **索引** | | | |
| idx_agent_call_time | | | 调用时间索引 |
| idx_agent_name | | | Agent名称索引 |

## 迁移方案
### 阶段1：基础架构搭建
1. 引入SQLAlchemy和asyncpg依赖
2. 配置数据库连接池
3. 实现基础DAO层抽象
4. 配置Alembic迁移工具

### 阶段2：模型映射
1. 将现有Pydantic模型映射为SQLAlchemy模型
2. 编写初始迁移脚本
3. 实现数据访问层(DAO)接口

### 阶段3：平滑迁移
1. 实现双写机制：同时写入内存和数据库
2. 数据一致性校验工具
3. 流量灰度切换到数据库
4. 下线内存存储

### 阶段4：性能优化
1. 添加必要的索引
2. 实现常用查询的缓存机制（Redis）
3. 读写分离架构配置
4. 慢查询优化

## 性能优化策略
### 1. 缓存层引入
- 使用Redis缓存热点数据：用户信息、热门帖子、评论列表
- 缓存失效策略：LRU + 主动失效
- 缓存击穿防护：互斥锁 + 空值缓存

### 2. 读写分离
- 主库负责写操作和强一致性读
- 从库负责非实时性查询操作
- 读写分离中间件：pgpool-II 或 应用层路由

### 3. 分库分表（未来扩展）
- 垂直分库：将审计日志、AI调用记录等大表拆分到独立库
- 水平分表：帖子表、评论表按时间维度分表

### 4. 全文搜索优化
- 使用PostgreSQL内置全文搜索实现内容检索
- 未来可扩展接入Elasticsearch支持更复杂的搜索场景

## 迁移风险控制
1. **数据一致性**：双写阶段进行数据校验，确保迁移过程数据不丢失
2. **回滚机制**：保留内存存储作为降级方案，出现问题可快速切回
3. **灰度发布**：先切1%流量，逐步扩大比例，及时发现问题
4. **监控告警**：配置数据库性能监控、慢查询告警、错误率告警

## 依赖清单
```txt
# 数据库相关
sqlalchemy>=2.0.0
asyncpg>=0.28.0
alembic>=1.12.0

# 缓存相关
redis>=5.0.0
```