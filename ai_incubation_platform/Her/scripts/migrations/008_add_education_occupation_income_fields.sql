-- 迁移脚本 008: 添加学历、职业、收入字段
-- 创建日期：2026-04-12
-- 描述：为 users 表添加学历、职业、收入字段，支持 QuickStart 可选信息收集

-- 为 users 表添加学历字段
ALTER TABLE users ADD COLUMN education VARCHAR(50);
ALTER TABLE users ADD COLUMN occupation VARCHAR(50);
ALTER TABLE users ADD COLUMN income VARCHAR(50);

-- 创建索引（用于匹配查询优化）
CREATE INDEX IF NOT EXISTS idx_users_education ON users(education);
CREATE INDEX IF NOT EXISTS idx_users_occupation ON users(occupation);
CREATE INDEX IF NOT EXISTS idx_users_income ON users(income);