-- 迁移脚本 005: 添加用户违规计数字段
-- 创建日期：2026-04-09
-- 描述：为 users 表添加违规计数和封禁相关字段，支持举报系统

-- 为 users 表添加违规计数字段
ALTER TABLE users ADD COLUMN violation_count INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN ban_reason TEXT;
ALTER TABLE users ADD COLUMN is_permanently_banned BOOLEAN DEFAULT FALSE;

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_users_violation_count ON users(violation_count);
