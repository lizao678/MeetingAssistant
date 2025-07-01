"""
数据库模型定义
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from loguru import logger

Base = declarative_base()


class Recording(Base):
    """录音记录表"""
    __tablename__ = "recordings"
    
    id = Column(String, primary_key=True)
    title = Column(String(255), nullable=False)
    file_path = Column(String(500))
    duration = Column(Float)  # 时长(秒)
    speaker_count = Column(Integer)
    language = Column(String(10), default="zh")
    status = Column(String(20), default="processing")  # processing, completed, failed
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 处理选项
    options = Column(JSON)  # 存储处理选项 (智能标点、数字转换等)
    
    # 关联关系
    segments = relationship("SpeechSegment", back_populates="recording", cascade="all, delete-orphan")
    summaries = relationship("Summary", back_populates="recording", cascade="all, delete-orphan")
    keywords = relationship("Keyword", back_populates="recording", cascade="all, delete-orphan")


class SpeechSegment(Base):
    """发言段落表"""
    __tablename__ = "speech_segments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    recording_id = Column(String, ForeignKey("recordings.id"), nullable=False)
    speaker_id = Column(String(50))  # 发言人ID (发言人A, 发言人B等)
    speaker_name = Column(String(100))  # 发言人名称
    speaker_color = Column(String(10))  # 发言人显示颜色
    content = Column(Text, nullable=False)  # 发言内容
    start_time = Column(Float, nullable=False)  # 开始时间(秒)
    end_time = Column(Float, nullable=False)  # 结束时间(秒)
    confidence = Column(Float)  # 识别置信度
    create_time = Column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    recording = relationship("Recording", back_populates="segments")


class Summary(Base):
    """智能摘要表"""
    __tablename__ = "summaries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    recording_id = Column(String, ForeignKey("recordings.id"), nullable=False)
    summary_type = Column(String(20), default="meeting")  # meeting, interview, lecture
    content = Column(Text, nullable=False)
    quality = Column(Integer, default=3)  # 摘要质量评分 1-5
    word_count = Column(Integer)
    key_points = Column(JSON)  # 关键要点列表
    compression_ratio = Column(Float)  # 压缩比
    create_time = Column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    recording = relationship("Recording", back_populates="summaries")


class Keyword(Base):
    """关键词表"""
    __tablename__ = "keywords"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    recording_id = Column(String, ForeignKey("recordings.id"), nullable=False)
    keyword = Column(String(100), nullable=False)
    frequency = Column(Integer, default=1)  # 出现频次
    importance_score = Column(Float, default=0.0)  # 重要性评分
    source = Column(String(10), default="ai")  # ai, freq, manual
    create_time = Column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    recording = relationship("Recording", back_populates="keywords")


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "recordings.db"):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # 创建表
        Base.metadata.create_all(bind=self.engine)
        logger.info(f"数据库初始化完成: {db_path}")
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()
    
    def create_recording(self, recording_data: Dict[str, Any]) -> str:
        """创建录音记录"""
        try:
            with self.get_session() as session:
                recording = Recording(
                    id=recording_data["id"],
                    title=recording_data["title"],
                    file_path=recording_data.get("file_path"),
                    duration=recording_data.get("duration", 0),
                    speaker_count=recording_data.get("speaker_count", 0),
                    language=recording_data.get("language", "zh"),
                    status=recording_data.get("status", "processing"),
                    options=recording_data.get("options", {})
                )
                session.add(recording)
                session.commit()
                
                logger.info(f"创建录音记录: {recording.id}")
                return recording.id
                
        except Exception as e:
            logger.error(f"创建录音记录失败: {str(e)}")
            raise
    
    def update_recording_status(self, recording_id: str, status: str) -> bool:
        """更新录音状态"""
        try:
            with self.get_session() as session:
                recording = session.query(Recording).filter(Recording.id == recording_id).first()
                if recording:
                    recording.status = status
                    recording.update_time = datetime.utcnow()
                    session.commit()
                    return True
                return False
                
        except Exception as e:
            logger.error(f"更新录音状态失败: {str(e)}")
            return False
    
    def get_recording(self, recording_id: str) -> Optional[Dict[str, Any]]:
        """获取录音记录"""
        try:
            with self.get_session() as session:
                recording = session.query(Recording).filter(Recording.id == recording_id).first()
                if not recording:
                    return None
                
                return {
                    "id": recording.id,
                    "title": recording.title,
                    "filePath": recording.file_path,
                    "duration": recording.duration,
                    "speakerCount": recording.speaker_count,
                    "language": recording.language,
                    "status": recording.status,
                    "createTime": recording.create_time.isoformat() if recording.create_time else None,
                    "updateTime": recording.update_time.isoformat() if recording.update_time else None,
                    "options": recording.options or {}
                }
                
        except Exception as e:
            logger.error(f"获取录音记录失败: {str(e)}")
            return None
    
    def save_segments(self, recording_id: str, segments: List[Dict[str, Any]]) -> bool:
        """保存发言段落"""
        try:
            with self.get_session() as session:
                # 删除已存在的段落
                session.query(SpeechSegment).filter(SpeechSegment.recording_id == recording_id).delete()
                
                # 添加新段落
                for segment in segments:
                    speech_segment = SpeechSegment(
                        recording_id=recording_id,
                        speaker_id=segment.get("speaker_id"),
                        speaker_name=segment.get("speaker_name"),
                        speaker_color=segment.get("speaker_color"),
                        content=segment.get("content", ""),
                        start_time=segment.get("start_time", 0),
                        end_time=segment.get("end_time", 0),
                        confidence=segment.get("confidence", 0)
                    )
                    session.add(speech_segment)
                
                session.commit()
                logger.info(f"保存 {len(segments)} 个发言段落到录音 {recording_id}")
                return True
                
        except Exception as e:
            logger.error(f"保存发言段落失败: {str(e)}")
            return False
    
    def get_segments(self, recording_id: str) -> List[Dict[str, Any]]:
        """获取发言段落"""
        try:
            with self.get_session() as session:
                segments = session.query(SpeechSegment).filter(
                    SpeechSegment.recording_id == recording_id
                ).order_by(SpeechSegment.start_time).all()
                
                return [
                    {
                        "id": segment.id,
                        "speakerId": segment.speaker_id,
                        "speakerName": segment.speaker_name,
                        "speakerColor": segment.speaker_color,
                        "content": segment.content,
                        "startTime": segment.start_time,
                        "endTime": segment.end_time,
                        "confidence": segment.confidence
                    }
                    for segment in segments
                ]
                
        except Exception as e:
            logger.error(f"获取发言段落失败: {str(e)}")
            return []
    
    def save_summary(self, recording_id: str, summary_data: Dict[str, Any]) -> bool:
        """保存智能摘要"""
        try:
            with self.get_session() as session:
                # 删除已存在的摘要
                session.query(Summary).filter(Summary.recording_id == recording_id).delete()
                
                # 添加新摘要
                summary = Summary(
                    recording_id=recording_id,
                    summary_type=summary_data.get("summary_type", "meeting"),
                    content=summary_data.get("content", ""),
                    quality=summary_data.get("quality", 3),
                    word_count=summary_data.get("word_count", 0),
                    key_points=summary_data.get("key_points", []),
                    compression_ratio=summary_data.get("compression_ratio", 0)
                )
                session.add(summary)
                session.commit()
                
                logger.info(f"保存摘要到录音 {recording_id}")
                return True
                
        except Exception as e:
            logger.error(f"保存摘要失败: {str(e)}")
            return False
    
    def get_summary(self, recording_id: str) -> Optional[Dict[str, Any]]:
        """获取智能摘要"""
        try:
            with self.get_session() as session:
                summary = session.query(Summary).filter(Summary.recording_id == recording_id).first()
                if not summary:
                    return None
                
                return {
                    "content": summary.content,
                    "quality": summary.quality,
                    "wordCount": summary.word_count,
                    "keyPoints": summary.key_points or [],
                    "compressionRatio": summary.compression_ratio,
                    "summaryType": summary.summary_type,
                    "createTime": summary.create_time.isoformat() if summary.create_time else None
                }
                
        except Exception as e:
            logger.error(f"获取摘要失败: {str(e)}")
            return None
    
    def save_keywords(self, recording_id: str, keywords: List[Dict[str, Any]]) -> bool:
        """保存关键词"""
        try:
            with self.get_session() as session:
                # 删除已存在的关键词
                session.query(Keyword).filter(Keyword.recording_id == recording_id).delete()
                
                # 添加新关键词
                for kw in keywords:
                    keyword = Keyword(
                        recording_id=recording_id,
                        keyword=kw.get("word", ""),
                        frequency=kw.get("count", 1),
                        importance_score=kw.get("score", 0),
                        source=kw.get("source", "ai")
                    )
                    session.add(keyword)
                
                session.commit()
                logger.info(f"保存 {len(keywords)} 个关键词到录音 {recording_id}")
                return True
                
        except Exception as e:
            logger.error(f"保存关键词失败: {str(e)}")
            return False
    
    def get_keywords(self, recording_id: str) -> List[Dict[str, Any]]:
        """获取关键词"""
        try:
            with self.get_session() as session:
                keywords = session.query(Keyword).filter(
                    Keyword.recording_id == recording_id
                ).order_by(Keyword.importance_score.desc()).all()
                
                return [
                    {
                        "word": keyword.keyword,
                        "count": keyword.frequency,
                        "score": keyword.importance_score,
                        "source": keyword.source
                    }
                    for keyword in keywords
                ]
                
        except Exception as e:
            logger.error(f"获取关键词失败: {str(e)}")
            return []
    
    def get_recording_detail(self, recording_id: str) -> Optional[Dict[str, Any]]:
        """获取录音完整详情"""
        try:
            recording = self.get_recording(recording_id)
            if not recording:
                return None
            
            segments = self.get_segments(recording_id)
            summary = self.get_summary(recording_id)
            keywords = self.get_keywords(recording_id)
            
            return {
                "recording": recording,
                "segments": segments,
                "summary": summary,
                "keywords": keywords
            }
            
        except Exception as e:
            logger.error(f"获取录音详情失败: {str(e)}")
            return None
    
    def get_recordings_list(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取录音列表"""
        try:
            with self.get_session() as session:
                # 计算偏移量
                offset = (page - 1) * page_size
                
                # 查询录音列表
                recordings = session.query(Recording).order_by(
                    Recording.create_time.desc()
                ).offset(offset).limit(page_size).all()
                
                # 计算总数
                total = session.query(Recording).count()
                
                recording_list = []
                for recording in recordings:
                    # 获取基本统计信息
                    segment_count = session.query(SpeechSegment).filter(
                        SpeechSegment.recording_id == recording.id
                    ).count()
                    
                    has_summary = session.query(Summary).filter(
                        Summary.recording_id == recording.id
                    ).first() is not None
                    
                    has_keywords = session.query(Keyword).filter(
                        Keyword.recording_id == recording.id
                    ).count() > 0
                    
                    recording_list.append({
                        "id": recording.id,
                        "title": recording.title,
                        "duration": recording.duration,
                        "speakerCount": recording.speaker_count,
                        "language": recording.language,
                        "status": recording.status,
                        "createTime": recording.create_time.isoformat() if recording.create_time else None,
                        "segmentCount": segment_count,
                        "hasSummary": has_summary,
                        "hasKeywords": has_keywords
                    })
                
                return {
                    "recordings": recording_list,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size
                }
                
        except Exception as e:
            logger.error(f"获取录音列表失败: {str(e)}")
            return {"recordings": [], "total": 0, "page": 1, "page_size": page_size, "total_pages": 0}


# 全局数据库管理器实例
db_manager = DatabaseManager() 