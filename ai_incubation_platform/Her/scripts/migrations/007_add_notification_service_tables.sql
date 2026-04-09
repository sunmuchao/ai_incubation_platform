-- 迁移脚本 007: 添加第三方通知服务支持
-- 创建日期：2026-04-09
-- 描述：添加紧急联系人通知、推送通知记录等表

-- 推送令牌表（如果不存在则创建）
CREATE TABLE IF NOT EXISTS push_tokens (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    push_token VARCHAR(500) NOT NULL,
    device_platform VARCHAR(20) NOT NULL,
    device_model VARCHAR(100),
    app_version VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    last_seen_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_push_tokens_user_id ON push_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_push_tokens_token ON push_tokens(push_token);
CREATE INDEX IF NOT EXISTS idx_push_tokens_active ON push_tokens(is_active);

-- 通知记录表（如果不存在则创建）
CREATE TABLE IF NOT EXISTS notifications (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    data JSON,
    is_read BOOLEAN DEFAULT FALSE,
    read_at DATETIME,
    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_unread ON notifications(user_id, is_read) WHERE is_read = FALSE;
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(sent_at);

-- 紧急联系人表（扩展 TrustedContactDB）
-- 注意：trusted_contacts 表已存在，这里添加新字段

-- 通知发送记录表（用于追踪第三方通知发送状态）
CREATE TABLE IF NOT EXISTS notification_delivery_records (
    id VARCHAR(36) PRIMARY KEY,
    notification_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    delivery_channel VARCHAR(20) NOT NULL,  -- push, sms, voice_call, email
    delivery_status VARCHAR(20) DEFAULT 'pending',  -- pending, sent, delivered, failed
    channel_response TEXT,  -- 第三方服务返回的响应
    retry_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    sent_at DATETIME,
    delivered_at DATETIME,
    FOREIGN KEY (notification_id) REFERENCES notifications(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_delivery_notification_id ON notification_delivery_records(notification_id);
CREATE INDEX IF NOT EXISTS idx_delivery_user_id ON notification_delivery_records(user_id);
CREATE INDEX IF NOT EXISTS idx_delivery_status ON notification_delivery_records(delivery_status);

-- 说明：
-- delivery_channel: 通知渠道
--   - push: 推送通知（极光推送等）
--   - sms: 短信（阿里云短信）
--   - voice_call: 语音电话（用于紧急通知）
--   - email: 邮件
-- delivery_status: 发送状态
--   - pending: 待发送
--   - sent: 已发送
--   - delivered: 已送达
--   - failed: 发送失败
