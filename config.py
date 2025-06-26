"""
配置模块 - 包含应用的所有配置项
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from loguru import logger
import sys


class Config(BaseSettings):
    """应用配置"""
    sv_thr: float = Field(0.42, description="Speaker verification threshold for diarization")
    chunk_size_ms: int = Field(300, description="Chunk size in milliseconds")
    sample_rate: int = Field(16000, description="Sample rate in Hz")
    bit_depth: int = Field(16, description="Bit depth")
    channels: int = Field(1, description="Number of audio channels")
    avg_logprob_thr: float = Field(-0.25, description="average logprob threshold")
    
    # 说话人识别相关配置
    min_audio_length_ms: int = Field(800, description="Minimum audio length for speaker verification in milliseconds")
    max_audio_length_ms: int = Field(5000, description="Maximum audio length for speaker verification in milliseconds")
    speaker_continuity_threshold: int = Field(3, description="Number of consecutive segments to confirm speaker identity")
    confidence_decay: float = Field(0.95, description="Confidence decay factor for speaker continuity")
    
    # VAD缓冲区管理配置
    vad_buffer_seconds: int = Field(15, description="VAD buffer size in seconds")  # 增加到15秒
    vad_buffer_cleanup_threshold: float = Field(0.8, description="VAD buffer cleanup threshold (0.0-1.0)")
    vad_buffer_cleanup_ratio: float = Field(0.3, description="Ratio of buffer to cleanup when threshold reached")
    silence_reset_seconds: int = Field(30, description="Reset VAD buffer after this many seconds of silence")
    keep_audio_seconds: int = Field(5, description="Seconds of audio to keep after silence reset")
    
    # 换行控制配置
    pause_threshold_ms: int = Field(1500, description="Pause threshold in milliseconds for line break detection")
    enable_smart_line_break: bool = Field(True, description="Enable smart line break based on speaker and pause detection")
    
    # 线程池配置
    thread_pool_max_workers: int = Field(4, description="Maximum number of threads in the thread pool")
    
    # 缓冲区配置
    audio_buffer_max_size: int = Field(100, description="Maximum size of audio buffer")
    vad_buffer_duration_seconds: int = Field(10, description="VAD buffer duration in seconds")


def setup_logging():
    """设置日志配置"""
    logger.remove()
    log_format = "{time:YYYY-MM-DD HH:mm:ss} [{level}] {file}:{line} - {message}"
    logger.add(sys.stdout, format=log_format, level="DEBUG", filter=lambda record: record["level"].no < 40)
    logger.add(sys.stderr, format=log_format, level="ERROR", filter=lambda record: record["level"].no >= 40)


# 全局配置实例
config = Config() 