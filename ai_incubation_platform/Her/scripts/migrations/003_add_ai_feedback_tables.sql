-- 迁移脚本 003: 添加 AI 反馈闭环相关表
-- 创建日期：2026-04-09
-- 描述：添加 AI 反馈记录表、反馈结果追踪表，支持 AI 建议采纳率分析和模型优化

-- AI 反馈记录表
CREATE TABLE IF NOT EXISTS ai_feedback (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    partner_id VARCHAR(36),
    suggestion_id VARCHAR(36) NOT NULL,
    feedback_type VARCHAR(20) NOT NULL,
    suggestion_content TEXT,
    suggestion_style VARCHAR(50),
    suggestion_category VARCHAR(50),
    user_actual_reply TEXT,
    reply_latency_ms INTEGER,
    metadata_json TEXT,
    session_id VARCHAR(36),
    conversation_round INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_ai_feedback_user_id ON ai_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_suggestion_id ON ai_feedback(suggestion_id);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_feedback_type ON ai_feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_user_partner ON ai_feedback(user_id, partner_id);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_created_at ON ai_feedback(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_type_created ON ai_feedback(feedback_type, created_at);

-- AI 反馈结果追踪表
CREATE TABLE IF NOT EXISTS ai_feedback_outcomes (
    id VARCHAR(36) PRIMARY KEY,
    feedback_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    outcome_type VARCHAR(20) NOT NULL,
    outcome_description TEXT,
    conversation_duration_min INTEGER,
    user_satisfaction_score FLOAT,
    follow_up_messages INTEGER DEFAULT 0,
    metadata_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_outcome_feedback_id ON ai_feedback_outcomes(feedback_id);
CREATE INDEX IF NOT EXISTS idx_outcome_user_id ON ai_feedback_outcomes(user_id);
CREATE INDEX IF NOT EXISTS idx_outcome_feedback_user ON ai_feedback_outcomes(feedback_id, user_id);
CREATE INDEX IF NOT EXISTS idx_outcome_created_at ON ai_feedback_outcomes(created_at);

-- 说明：
-- feedback_type 枚举值：adopted (采纳), ignored (忽略), modified (修改后发送), helpful (有用), not_helpful (无用)
-- outcome_type 枚举值：continued (对话继续), stopped (对话中断), warmed (关系升温), date_requested (邀约成功)
-- suggestion_style 枚举值：幽默，真诚，延续话题，破冰，深入，告别 等
-- suggestion_category 枚举值：破冰，深入交流，告别，邀约，安抚 等
