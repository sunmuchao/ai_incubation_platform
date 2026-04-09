-- 迁移脚本 004: 添加举报系统相关表
-- 创建日期：2026-04-09
-- 描述：添加用户举报记录表，支持用户举报、安全审核、违规处理等功能

-- 用户举报记录表
CREATE TABLE IF NOT EXISTS user_reports (
    id VARCHAR(36) PRIMARY KEY,
    reporter_id VARCHAR(36) NOT NULL,
    reported_user_id VARCHAR(36) NOT NULL,
    report_type VARCHAR(50) NOT NULL,
    reason TEXT,
    description TEXT,
    conversation_id VARCHAR(36),
    message_id VARCHAR(36),
    date_id VARCHAR(36),
    evidence_urls TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    priority INTEGER DEFAULT 1,
    reviewed_by VARCHAR(36),
    reviewed_at DATETIME,
    review_notes TEXT,
    action_taken VARCHAR(100),
    action_details TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    FOREIGN KEY (reporter_id) REFERENCES users(id),
    FOREIGN KEY (reported_user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_user_reports_reporter_id ON user_reports(reporter_id);
CREATE INDEX IF NOT EXISTS idx_user_reports_reported_user_id ON user_reports(reported_user_id);
CREATE INDEX IF NOT EXISTS idx_user_reports_report_type ON user_reports(report_type);
CREATE INDEX IF NOT EXISTS idx_user_reports_status ON user_reports(status);
CREATE INDEX IF NOT EXISTS idx_user_reports_priority ON user_reports(priority);
CREATE INDEX IF NOT EXISTS idx_user_reports_reviewed_by ON user_reports(reviewed_by);
CREATE INDEX IF NOT EXISTS idx_user_reports_created_at ON user_reports(created_at);
CREATE INDEX IF NOT EXISTS idx_user_reports_conversation_id ON user_reports(conversation_id);

-- 说明：
-- report_type 枚举值：inappropriate_content (不当内容), harassment (骚扰), fake_profile (虚假资料), spam (垃圾信息), underage (未成年), other (其他)
-- status 枚举值：pending (待审核), under_review (审核中), approved (已确认), rejected (已拒绝), processed (已处理)
-- priority: 1-5，数字越大优先级越高
-- action_taken 枚举值：warning (警告), temporary_ban (临时封禁), permanent_ban (永久封禁), content_removal (删除内容), no_action (无需处理)
