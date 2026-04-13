-- 迁移脚本 009: 添加 QuickStart 扩展字段和匹配偏好字段
-- 创建日期：2026-04-13
-- 描述：为 users 表添加 QuickStart 扩展字段（身高、车、住房）、一票否决维度（孩子、消费）、
--       核心价值观维度（家庭重要度、工作生活平衡）、迁移能力维度（迁移意愿、是否接受异地）、
--       生活方式维度（作息类型）以及匹配偏好设置（年龄范围、地点偏好）

-- ===== QuickStart 扩展字段 =====
ALTER TABLE users ADD COLUMN height INTEGER;
ALTER TABLE users ADD COLUMN has_car BOOLEAN;
ALTER TABLE users ADD COLUMN housing VARCHAR(20);

-- ===== 一票否决维度（最高优先级匹配条件）=====
ALTER TABLE users ADD COLUMN want_children VARCHAR(20);
ALTER TABLE users ADD COLUMN spending_style VARCHAR(20);

-- ===== 核心价值观维度 =====
ALTER TABLE users ADD COLUMN family_importance FLOAT;
ALTER TABLE users ADD COLUMN work_life_balance VARCHAR(20);

-- ===== 迁移能力维度 =====
ALTER TABLE users ADD COLUMN migration_willingness FLOAT;
ALTER TABLE users ADD COLUMN accept_remote VARCHAR(20);

-- ===== 生活方式维度 =====
ALTER TABLE users ADD COLUMN sleep_type VARCHAR(20);

-- ===== 偏好设置 =====
ALTER TABLE users ADD COLUMN preferred_age_min INTEGER DEFAULT 18;
ALTER TABLE users ADD COLUMN preferred_age_max INTEGER DEFAULT 60;
ALTER TABLE users ADD COLUMN preferred_location VARCHAR(200);

-- ===== 创建索引（用于匹配查询优化）=====
-- 一票否决维度索引
CREATE INDEX IF NOT EXISTS idx_users_want_children ON users(want_children);
CREATE INDEX IF NOT EXISTS idx_users_spending_style ON users(spending_style);

-- 迁移能力维度索引
CREATE INDEX IF NOT EXISTS idx_users_accept_remote ON users(accept_remote);

-- 偏好设置索引（用于匹配查询）
CREATE INDEX IF NOT EXISTS idx_users_preferred_location ON users(preferred_location);