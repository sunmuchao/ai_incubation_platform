-- 候选人反馈表创建脚本
-- 版本：v1.0
-- 执行方式：在数据库中执行此 SQL

-- ============================================================
-- 表 1：candidate_feedbacks（候选人反馈记录）
-- ============================================================

CREATE TABLE IF NOT EXISTS candidate_feedbacks (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    candidate_id VARCHAR(36) NOT NULL,
    feedback_type VARCHAR(20) NOT NULL,
    dislike_reason VARCHAR(50),
    dislike_detail TEXT,
    query_request_id VARCHAR(36),
    recommendation_score INTEGER DEFAULT 0,
    user_preferences_snapshot JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 外键约束（如果 users 表存在）
    -- FOREIGN KEY (user_id) REFERENCES users(id),
    -- FOREIGN KEY (candidate_id) REFERENCES users(id),

    -- 索引
    INDEX ix_user_candidate_feedback (user_id, candidate_id),
    INDEX ix_feedback_type (feedback_type),
    INDEX ix_dislike_reason (dislike_reason),
    INDEX ix_query_request (query_request_id)
);

-- 唯一约束：同一用户对同一候选人只能反馈一次
CREATE UNIQUE INDEX IF NOT EXISTS ix_user_candidate_feedback_unique
ON candidate_feedbacks(user_id, candidate_id);

-- ============================================================
-- 表 2：feedback_statistics（反馈统计汇总）
-- ============================================================

CREATE TABLE IF NOT EXISTS feedback_statistics (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL UNIQUE,
    total_feedbacks INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    dislike_count INTEGER DEFAULT 0,
    neutral_count INTEGER DEFAULT 0,
    skip_count INTEGER DEFAULT 0,
    dislike_reason_distribution JSON,
    learned_preferences JSON,
    last_feedback_at TIMESTAMP,
    updated_at TIMESTAMP,

    -- 外键约束（如果 users 表存在）
    -- FOREIGN KEY (user_id) REFERENCES users(id),

    INDEX ix_user_id (user_id)
);

-- ============================================================
-- 验证
-- ============================================================

-- 查看表结构
DESCRIBE candidate_feedbacks;
DESCRIBE feedback_statistics;

-- 插入测试数据（可选）
-- INSERT INTO candidate_feedbacks (id, user_id, candidate_id, feedback_type, dislike_reason)
-- VALUES ('test-001', 'user-001', 'candidate-001', 'dislike', '年龄差距太大');