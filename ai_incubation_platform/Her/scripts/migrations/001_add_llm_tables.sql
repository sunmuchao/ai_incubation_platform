-- 迁移脚本 001: 添加 LLM 深度集成相关表
-- 创建日期：2026-04-07
-- 描述：添加用户偏好、语义分析、LLM 指标、安全区域、可信联系人表

-- 用户偏好表
CREATE TABLE IF NOT EXISTS user_preferences (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL UNIQUE,
    preferred_age_range JSON DEFAULT '[18, 60]',
    preferred_location_range INTEGER DEFAULT 50,
    preferred_distance INTEGER DEFAULT 100,
    preferred_height_range JSON,
    preferred_education TEXT DEFAULT '',
    preferred_income_range JSON,
    preference_weights JSON DEFAULT '{"age": 0.2, "location": 0.2, "interests": 0.3, "values": 0.3}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);

-- 语义分析结果表
CREATE TABLE IF NOT EXISTS semantic_analyses (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    analysis_type VARCHAR(50) NOT NULL,
    result JSON NOT NULL,
    original_text_preview VARCHAR(500),
    overall_confidence FLOAT,
    llm_model VARCHAR(100),
    input_tokens INTEGER,
    output_tokens INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_semantic_analyses_user_id ON semantic_analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_semantic_analyses_type ON semantic_analyses(analysis_type);

-- LLM 调用指标表
CREATE TABLE IF NOT EXISTS llm_metrics (
    id VARCHAR(36) PRIMARY KEY,
    endpoint VARCHAR(100) NOT NULL,
    user_id VARCHAR(36),
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    estimated_cost FLOAT,
    response_status VARCHAR(20) DEFAULT 'success',
    error_message TEXT,
    response_time_ms INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_llm_metrics_user_id ON llm_metrics(user_id);
CREATE INDEX IF NOT EXISTS idx_llm_metrics_created_at ON llm_metrics(created_at);

-- 安全区域表
CREATE TABLE IF NOT EXISTS safety_zones (
    id VARCHAR(36) PRIMARY KEY,
    zone_type VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    radius INTEGER NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_safety_zones_type ON safety_zones(zone_type);
CREATE INDEX IF NOT EXISTS idx_safety_zones_active ON safety_zones(is_active);

-- 可信联系人表
CREATE TABLE IF NOT EXISTS trusted_contacts (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    relationship VARCHAR(50),
    can_view_location BOOLEAN DEFAULT TRUE,
    can_receive_emergency BOOLEAN DEFAULT TRUE,
    display_order INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_trusted_contacts_user_id ON trusted_contacts(user_id);

-- 插入默认安全区域数据（示例）
INSERT OR IGNORE INTO safety_zones (id, zone_type, name, latitude, longitude, radius, description)
VALUES
    ('zone_001', 'danger', '偏僻区域示例', 0.0, 0.0, 1000, '这是一个示例危险区域，实际使用中需要配置真实的危险区域坐标');
