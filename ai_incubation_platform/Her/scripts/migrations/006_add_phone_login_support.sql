-- 迁移脚本 006: 添加手机号登录支持
-- 创建日期：2026-04-09
-- 描述：为 users 表添加手机号字段，支持手机号登录

-- 为 users 表添加手机号字段
ALTER TABLE users ADD COLUMN phone VARCHAR(20);
ALTER TABLE users ADD COLUMN phone_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN phone_verification_code VARCHAR(6);
ALTER TABLE users ADD COLUMN phone_verification_expires_at DATETIME;

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
CREATE INDEX IF NOT EXISTS idx_users_phone_verified ON users(phone, phone_verified);

-- 说明：
-- phone: 用户手机号（加密存储）
-- phone_verified: 手机号是否已验证
-- phone_verification_code: 验证码（临时存储）
-- phone_verification_expires_at: 验证码过期时间
