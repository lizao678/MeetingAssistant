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
    
    # 硬件配置
    use_gpu: bool = Field(True, description="Whether to use GPU for model inference")
    
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


class AudioProcessingConfig:
    """音频处理相关配置常量"""
    
    # VAD模拟处理配置
    CHUNK_DURATION = 3.0  # 基础chunk时长（秒）
    OVERLAP_DURATION = 0.5  # 重叠时长（秒）
    MIN_CHUNK_DURATION = 0.5  # 最小chunk时长（秒）
    
    # 细分处理配置
    MAX_SIMPLE_CHUNK_DURATION = 5.0  # 简单处理的最大时长（秒）
    MAX_SUB_DURATION = 4.0  # 细分时每个子段的最大时长（秒）
    MIN_PART_DURATION = 0.8  # 分割后最小部分时长（秒）
    
    # 音频质量检测
    MIN_ENERGY_THRESHOLD = 0.0001  # 最低能量阈值（降低以接受更多语音）
    MAX_ENERGY_THRESHOLD = 0.1  # 最高能量阈值
    SNR_THRESHOLD = 5.0  # 信噪比阈值（dB）（降低要求）
    ZERO_CROSSING_THRESHOLD = 0.30  # 零穿越率阈值（提高到0.30，允许更多语音通过）
    
    # 采样率配置
    TARGET_SAMPLE_RATE = 16000  # 目标采样率
    MIN_SAMPLE_RATE = 8000  # 最低支持采样率
    MAX_SAMPLE_RATE = 48000  # 最高支持采样率


class RecognitionQualityConfig:
    """识别质量相关配置常量"""
    
    # ASR置信度阈值
    MIN_ASR_CONFIDENCE = -0.5  # ASR最低置信度要求
    GOOD_ASR_CONFIDENCE = -0.2  # 良好ASR置信度
    
    # 说话人识别置信度
    MIN_SPEAKER_CONFIDENCE = 0.4  # 说话人识别最低置信度
    GOOD_SPEAKER_CONFIDENCE = 0.7  # 良好说话人识别置信度
    SPEAKER_THRESHOLD_BASE = 0.45  # 说话人识别基础阈值
    SPEAKER_THRESHOLD_RAISE = 0.02  # 当前说话人阈值提升值
    
    # 文本质量要求
    MIN_TEXT_LENGTH = 2  # 最小文本长度（字符）
    MIN_MEANINGFUL_CHARS = 2  # 最少有意义字符数
    MAX_PUNCTUATION_RATIO = 0.8  # 最大标点符号占比


class NumberConversionConfig:
    """数字转换相关配置常量"""
    
    # 数字识别阈值
    MAX_CONVERT_NUMBER = 10000  # 最大转换数字
    MIN_CONVERT_NUMBER = 0  # 最小转换数字
    
    # 转换规则
    CONVERT_YEAR_THRESHOLD = 1900  # 年份转换阈值
    CONVERT_TIME_FORMAT = True  # 是否转换时间格式
    PRESERVE_PHONE_NUMBERS = True  # 是否保留电话号码格式
    PRESERVE_ID_NUMBERS = True  # 是否保留身份证号格式


class SegmentationConfig:
    """分段处理相关配置常量"""
    
    # 智能断句配置
    SILENCE_THRESHOLD_MS = 1500  # 静音断句阈值（毫秒）
    MIN_SEGMENT_DURATION = 1.0  # 最小段落时长（秒）
    MAX_SEGMENT_DURATION = 30.0  # 最大段落时长（秒）
    
    # 说话人变更检测
    SPEAKER_CHANGE_MERGE_THRESHOLD = 2.0  # 说话人变更合并阈值（秒）
    MIN_SPEAKER_SEGMENT_DURATION = 0.5  # 最小说话人段落时长（秒）


class UIConfig:
    """用户界面相关配置常量"""
    
    # 发言人颜色
    SPEAKER_COLORS = [
        "#1890ff", "#52c41a", "#fa8c16", "#eb2f96", 
        "#722ed1", "#13c2c2", "#faad14", "#f5222d",
        "#096dd9", "#389e0d", "#d4b106", "#c41d7f"
    ]
    
    # 分页配置
    DEFAULT_PAGE_SIZE = 10  # 默认页面大小
    MAX_PAGE_SIZE = 100  # 最大页面大小
    
    # 文件上传限制
    MAX_FILE_SIZE_MB = 200  # 最大文件大小（MB）
    SUPPORTED_AUDIO_FORMATS = ['.wav', '.mp3', '.m4a', '.flac', '.aac']


class ProcessingConfig:
    """处理流程相关配置常量"""
    
    # 异步处理配置
    MAX_CONCURRENT_TASKS = 3  # 最大并发任务数
    TASK_TIMEOUT_SECONDS = 3600  # 任务超时时间（秒）
    
    # AI分析配置
    MAX_TEXT_LENGTH_FOR_AI = 50000  # AI分析的最大文本长度
    AI_RETRY_ATTEMPTS = 3  # AI服务重试次数
    AI_TIMEOUT_SECONDS = 30  # AI服务超时时间
    
    # 缓存配置
    CACHE_EXPIRY_HOURS = 24  # 缓存过期时间（小时）
    MAX_CACHE_SIZE_MB = 500  # 最大缓存大小（MB）


class TextProcessingConfig:
    """文本处理相关配置常量"""
    
    # 基础停用词集合
    BASE_STOP_WORDS = {
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '什么', '这个', '那个', '里', '这里', '那里', '现在', '时候', '可以', '还', '把', '他', '她', '它', '我们', '你们', '他们', '她们', '它们', '这些', '那些', '但是', '然后', '因为', '所以', '如果', '虽然', '只是', '应该', '可能', '已经', '还是', '或者', '而且', '但', '然', '因', '所', '如', '虽', '只', '应', '可', '已', '还', '或', '而'
    }
    
    # 扩展停用词集合（用于关键词提取）
    EXTENDED_STOP_WORDS = {
        '情况', '时候', '方面', '问题', '东西', '地方', '时间', '样子', '事情',
        '方式', '过程', '结果', '原因', '因为', '所以', '然后', '现在', '这样',
        '那样', '一个', '这个', '那个', '什么', '怎么', '为什么', '如何',
        '基本', '主要', '重要', '一般', '特别', '比较', '非常', '一些',
        '很多', '少数', '全部', '部分', '大部分', '小部分', '左右', '左边', '右边'
    }
    
    # 无效文本模式
    INVALID_TEXT_PATTERNS = [
        r'^[。，！？；：]{1,3}$',  # 只有1-3个标点符号
        r'^[a-zA-Z]{1,2}$',       # 只有1-2个字母
        r'^[0-9]{1,2}$',          # 只有1-2个数字
        r'^[　\s]+$',             # 只有空格
        r'^呃+$',                 # 只有语气词
        r'^嗯+$',                 # 只有语气词
        r'^啊+$',                 # 只有语气词
        r'^哦+$',                 # 只有语气词
    ]
    
    # 保留词汇（数字转换时不处理）
    PRESERVE_WORDS = [
        '小米',  # 保留品牌名
        '一些', '一起', '一下', '一个', '一条', '一次',  # 保留常用搭配
        '三个', '两个',  # 保留量词搭配
        '十分', '九分',  # 保留程度副词
    ]
    
    @classmethod
    def get_all_stop_words(cls):
        """获取所有停用词（基础+扩展）"""
        return cls.BASE_STOP_WORDS | cls.EXTENDED_STOP_WORDS


# 配置管理器实例
audio_config = AudioProcessingConfig()
quality_config = RecognitionQualityConfig()
number_config = NumberConversionConfig()
segment_config = SegmentationConfig()
ui_config = UIConfig()
processing_config = ProcessingConfig()
text_config = TextProcessingConfig() 