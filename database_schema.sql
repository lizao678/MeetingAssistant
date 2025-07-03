-- 录音会话表
CREATE TABLE recordings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(255) NOT NULL DEFAULT '未命名录音',
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER NOT NULL,
    duration INTEGER NOT NULL, -- 毫秒
    format VARCHAR(20) NOT NULL DEFAULT 'webm',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'completed', -- processing, completed, failed
    user_id VARCHAR(100) DEFAULT 'default_user'
);

-- 发言人信息表
CREATE TABLE speakers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recording_id INTEGER NOT NULL,
    speaker_name VARCHAR(100) NOT NULL,
    speaker_order INTEGER NOT NULL, -- 发言人编号
    total_duration INTEGER DEFAULT 0, -- 总发言时长(毫秒)
    segment_count INTEGER DEFAULT 0, -- 发言段数
    confidence_avg DECIMAL(5,4) DEFAULT 0, -- 平均置信度
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE
);

-- 发言段落表
CREATE TABLE speech_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recording_id INTEGER NOT NULL,
    speaker_id INTEGER NOT NULL,
    start_time INTEGER NOT NULL, -- 开始时间(毫秒)
    end_time INTEGER NOT NULL, -- 结束时间(毫秒)
    original_text TEXT NOT NULL, -- 原始识别文本
    optimized_text TEXT, -- AI优化后文本
    confidence DECIMAL(5,4) DEFAULT 0, -- 置信度
    segment_order INTEGER NOT NULL, -- 段落顺序
    is_optimized BOOLEAN DEFAULT FALSE, -- 是否已优化
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE,
    FOREIGN KEY (speaker_id) REFERENCES speakers(id) ON DELETE CASCADE
);

-- 会议总结表
CREATE TABLE meeting_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recording_id INTEGER NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    keywords TEXT, -- JSON格式存储关键词
    summary TEXT NOT NULL, -- 会议总结
    key_points TEXT, -- JSON格式存储要点
    action_items TEXT, -- JSON格式存储行动项
    participants_count INTEGER DEFAULT 0,
    ai_model VARCHAR(50) DEFAULT 'gpt-3.5-turbo',
    processing_time INTEGER DEFAULT 0, -- 处理耗时(秒)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE
);

-- 发言人总结表
CREATE TABLE speaker_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    summary_id INTEGER NOT NULL,
    speaker_id INTEGER NOT NULL,
    speaker_summary TEXT NOT NULL, -- 该发言人的发言总结
    key_opinions TEXT, -- JSON格式存储主要观点
    speaking_time_ratio DECIMAL(5,4) DEFAULT 0, -- 发言时间占比
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (summary_id) REFERENCES meeting_summaries(id) ON DELETE CASCADE,
    FOREIGN KEY (speaker_id) REFERENCES speakers(id) ON DELETE CASCADE
);

-- 创建索引优化查询性能
CREATE INDEX idx_recordings_created_at ON recordings(created_at);
CREATE INDEX idx_recordings_status ON recordings(status);
CREATE INDEX idx_speech_segments_recording_id ON speech_segments(recording_id);
CREATE INDEX idx_speech_segments_speaker_id ON speech_segments(speaker_id);
CREATE INDEX idx_speech_segments_time ON speech_segments(start_time, end_time);
CREATE INDEX idx_speakers_recording_id ON speakers(recording_id);

-- 常用发言人表
CREATE TABLE frequent_speakers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    color VARCHAR(20) NOT NULL DEFAULT '#409eff',
    use_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(100) DEFAULT 'default_user'
);

-- 发言人设置日志表
CREATE TABLE speaker_settings_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recording_id INTEGER NOT NULL,
    speaker_id INTEGER NOT NULL,
    old_name VARCHAR(100),
    new_name VARCHAR(100) NOT NULL,
    setting_type VARCHAR(20) NOT NULL, -- 'single' or 'global'
    frequent_speaker_id INTEGER, -- 关联的常用发言人ID
    user_id VARCHAR(100) DEFAULT 'default_user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE,
    FOREIGN KEY (speaker_id) REFERENCES speakers(id) ON DELETE CASCADE,
    FOREIGN KEY (frequent_speaker_id) REFERENCES frequent_speakers(id) ON DELETE SET NULL
);

-- 创建新的索引
CREATE INDEX idx_frequent_speakers_user_id ON frequent_speakers(user_id);
CREATE INDEX idx_frequent_speakers_use_count ON frequent_speakers(use_count DESC);
CREATE INDEX idx_speaker_settings_log_recording_id ON speaker_settings_log(recording_id);
CREATE INDEX idx_speaker_settings_log_speaker_id ON speaker_settings_log(speaker_id);

-- 插入示例常用发言人数据
INSERT INTO frequent_speakers (name, color, use_count, last_used_at) VALUES
('主持人', '#ff6b6b', 15, CURRENT_TIMESTAMP),
('雷军', '#4ecdc4', 8, CURRENT_TIMESTAMP),
('张三', '#45b7d1', 5, CURRENT_TIMESTAMP),
('李四', '#f9ca24', 3, CURRENT_TIMESTAMP);

-- 插入示例录音数据
INSERT INTO recordings (title, file_path, file_size, duration, format) VALUES
('产品讨论会议', '/uploads/recordings/20250630_meeting_001.webm', 5242880, 1800000, 'webm'),
('团队周例会', '/uploads/recordings/20250630_meeting_002.webm', 3145728, 1200000, 'webm'); 