#!/usr/bin/env python3
"""
数据库迁移脚本 - 添加发言人设置功能相关表
"""

import sqlite3
import os
from datetime import datetime
from loguru import logger

def migrate_speaker_tables():
    """迁移发言人相关数据表"""
    db_path = "recordings.db"
    
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return False
    
    try:
        # 连接到数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 创建常用发言人表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='frequent_speakers'")
        if not cursor.fetchone():
            cursor.execute('''
            CREATE TABLE frequent_speakers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL UNIQUE,
                color VARCHAR(20) NOT NULL DEFAULT '#409eff',
                use_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id VARCHAR(100) DEFAULT 'default_user'
            )
            ''')
            logger.info("✅ 创建 frequent_speakers 表")
        else:
            logger.info("ℹ️  frequent_speakers 表已存在")
        
        # 2. 创建发言人设置日志表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='speaker_settings_log'")
        if not cursor.fetchone():
            cursor.execute('''
            CREATE TABLE speaker_settings_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recording_id VARCHAR(255) NOT NULL,
                speaker_id VARCHAR(50) NOT NULL,
                old_name VARCHAR(100),
                new_name VARCHAR(100) NOT NULL,
                setting_type VARCHAR(20) NOT NULL,
                frequent_speaker_id INTEGER,
                user_id VARCHAR(100) DEFAULT 'default_user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE,
                FOREIGN KEY (frequent_speaker_id) REFERENCES frequent_speakers(id) ON DELETE SET NULL
            )
            ''')
            logger.info("✅ 创建 speaker_settings_log 表")
        else:
            logger.info("ℹ️  speaker_settings_log 表已存在")
        
        # 3. 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_frequent_speakers_user_id ON frequent_speakers(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_frequent_speakers_use_count ON frequent_speakers(use_count DESC)",
            "CREATE INDEX IF NOT EXISTS idx_speaker_settings_log_recording_id ON speaker_settings_log(recording_id)",
            "CREATE INDEX IF NOT EXISTS idx_speaker_settings_log_speaker_id ON speaker_settings_log(speaker_id)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        logger.info("✅ 创建数据库索引")
        
        # 4. 插入示例数据
        cursor.execute("SELECT COUNT(*) FROM frequent_speakers")
        count = cursor.fetchone()[0]
        if count == 0:
            sample_speakers = [
                ('主持人', '#ff6b6b', 15),
                ('雷军', '#4ecdc4', 8),
                ('张三', '#45b7d1', 5),
                ('李四', '#f9ca24', 3),
                ('王五', '#6c5ce7', 2),
                ('赵六', '#a29bfe', 1)
            ]
            
            for name, color, use_count in sample_speakers:
                cursor.execute('''
                INSERT INTO frequent_speakers (name, color, use_count, last_used_at) 
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (name, color, use_count))
            
            logger.info("✅ 插入示例常用发言人数据")
        else:
            logger.info("ℹ️  常用发言人数据已存在")
        
        # 5. 验证表结构
        cursor.execute("PRAGMA table_info(frequent_speakers)")
        fs_columns = [col[1] for col in cursor.fetchall()]
        logger.info(f"frequent_speakers 表字段: {fs_columns}")
        
        cursor.execute("PRAGMA table_info(speaker_settings_log)")
        ssl_columns = [col[1] for col in cursor.fetchall()]
        logger.info(f"speaker_settings_log 表字段: {ssl_columns}")
        
        # 6. 显示统计信息
        cursor.execute("SELECT COUNT(*) FROM frequent_speakers")
        fs_count = cursor.fetchone()[0]
        logger.info(f"常用发言人总数: {fs_count}")
        
        cursor.execute("SELECT COUNT(*) FROM speaker_settings_log")
        ssl_count = cursor.fetchone()[0]
        logger.info(f"发言人设置日志总数: {ssl_count}")
        
        conn.commit()
        conn.close()
        
        logger.success("🎉 数据库迁移完成!")
        return True
        
    except Exception as e:
        logger.error(f"数据库迁移失败: {str(e)}")
        return False

def test_speaker_apis():
    """测试发言人API相关的数据库操作"""
    try:
        from database import db_manager
        
        logger.info("开始测试发言人API...")
        
        # 测试获取常用发言人
        speakers = db_manager.get_frequent_speakers()
        logger.info(f"获取常用发言人: {len(speakers)} 个")
        
        # 测试添加常用发言人
        test_speaker = db_manager.add_frequent_speaker("测试发言人", "#ff0000")
        if test_speaker:
            logger.info(f"添加测试发言人成功: {test_speaker}")
            
            # 测试删除
            success = db_manager.delete_frequent_speaker(test_speaker['id'])
            if success:
                logger.info("删除测试发言人成功")
        
        logger.success("✅ 发言人API测试完成")
        return True
        
    except Exception as e:
        logger.error(f"发言人API测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    # 配置日志
    logger.add("migration.log", rotation="10 MB", level="INFO")
    
    logger.info("开始数据库迁移...")
    
    # 执行迁移
    if migrate_speaker_tables():
        logger.info("数据库迁移成功，开始测试...")
        test_speaker_apis()
    else:
        logger.error("数据库迁移失败") 